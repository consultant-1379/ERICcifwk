import tempfile
import logging
import subprocess
import shlex
import zipfile
import tarfile
import json
from contextlib import closing
from functools import wraps
import shutil
from ciconfig import CIConfig
config = CIConfig()
from datetime import datetime
import uuid
import os
import sys
from HTMLParser import HTMLParser
import re
from ftplib import FTP
import time
import socket
import itertools
import csv
from foss.models import *
from django.db import connection, transaction, IntegrityError
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives


logger = logging.getLogger(__name__)

def repo_auditer(user_name, bazaar_token, bazaar_svl, gerrit_repos):
    '''
    This function checks for open sockets between Server and Bazaar,
        Generate scan version id
        Sends Gerrit Repos for Audit/Scanning
        Generate CSV report base on scan version id.
        Return scan status to Interface
    '''
    exit_value, err_msg = check_for_open_sockets()
    if exit_value != 0:
        return err_msg
    scan_version_id = create_scan_version_id()
    list_of_audit_ids, scanned_repos = audit_gerrit_repos(scan_version_id, user_name, bazaar_token, bazaar_svl, gerrit_repos)
    if list_of_audit_ids:
        check_scan_status(user_name, bazaar_token, "/tmp", list_of_audit_ids)
        generate_final_report(list_of_audit_ids, scanned_repos, bazaar_svl)
    audit_report = generate_csv_report(scan_version_id)
    update_scan_version(str(scan_version_id), audit_report, datetime.now())
    send_audit_report_emails(scan_version_id, audit_report)
    return 'Audit Report: %s' % audit_report


@transaction.atomic
def audit_gerrit_repos(scan_version_id, user_name, bazaar_token, bazaar_svl, gerrit_repos):
    '''
    This function audits/scans Gerrit Repos:
    Gets DB repos
    Gets gerrit projects from Gerrit
    clones each repo if revision has changed/Not found in matching against DB data
    Creates Audit Id
    Send each compressed tar.gz repo for scanning to Bazaar API, with a created Audit id
    Store record about auditing in Scan mapping table.
    '''
    list_of_audit_ids = []
    scanned_repos = []
    repos = get_list_of_repos(gerrit_repos)
    gerrit_projects = get_all_gerrit_projects()

    for repo_url in repos:
        logger.info("Checking repo %s for FOSS Scan.", repo_url['repo_name'])
        scan_status = "not found"
        audit_id = report_url = None
        start_time = datetime.now()
        if repo_url['repo_name'] in gerrit_projects.keys():
            scan_status = "no scan"
            revision = gerrit_projects[repo_url['repo_name']]
            if revision != repo_url['repo_revision']:
                temp_dir = get_temp_dir_path()
                directory_to_project, project_to_compress = clone_gerrit_repo(temp_dir, repo_url['repo_name'])
                audit_id = create_audit(user_name, bazaar_token, directory_to_project, bazaar_svl)
                list_of_audit_ids.append(audit_id[0])
                compressed_project = compress_to_tar_gz(project_to_compress, temp_dir, audit_id)
                send_tar_gz_for_scan(compressed_project, temp_dir)
                report_url, scan_status = get_result(audit_id[0], bazaar_svl, repo_url['repo_name'])
                remove_temp_dir_path(temp_dir)
                try:
                    with transaction.atomic():
                        save_project_revision(repo_url['id'], revision)
                except IntegrityError as e:
                    logger.error("Error: there was issue with saving new repo revision: %s", str(e))
                    logger.info(e.message)
                    logger.info(e.args)
                repo_url['repo_revision'] = revision
                scanned_repos.append(repo_url)
        try:
            with transaction.atomic():
                create_scan_mapping(scan_version_id, repo_url, start_time, scan_status, audit_id, bazaar_svl, report_url)
        except IntegrityError as e:
            logger.error("Error: there was issue with creating scan mapping: %s", str(e))
    return list_of_audit_ids, scanned_repos


def save_project_revision(id, revision):
    '''
    This function saves the repo's revision (sha1)
    '''
    try:
        gerrit_repo = GerritRepo.objects.get(id=id)
        gerrit_repo.repo_revision = revision
        gerrit_repo.save(force_update=True)
    except Exception as e:
        logger.error("Error: there was issue saving gerrit repo revision: %s", str(e))


def create_scan_mapping(scan_version_id, repo_url, start_time, scan_status, audit_id=None, bazaar_svl=None, report_url=None):
    '''
    This function creates scan mapping for scan report
    '''
    if not audit_id:
        audit_id = ""
        bazaar_svl=""
    else:
        audit_id = audit_id[0]

    if not report_url:
        report_url=""

    reason = ""
    if scan_status == "no scan":
        reason = "No change in repo since last scan"
    if scan_status == "not found":
        reason = "Repo not found in Gerrit"

    ScanMapping.objects.create(
            scan_version_id = str(scan_version_id),
            gerrit_repo_id = str(repo_url['id']),
            audit_id = str(audit_id),
            project_id = str(bazaar_svl),
            report_url = str(report_url),
            start_time = str(start_time),
            status = str(scan_status),
            reason = str(reason))


def update_scan_mapping(audit_id, status):
    '''
    This function update Scan mapping in DB with Status & Date Time
    '''
    try:
        reason = None
        end_time = None
        if status != "completed":
            reason = "Issue found when scanning: %s" % status
            status = "incomplete"
        else:
            end_time = datetime.now()
        ScanMapping.objects.filter(audit_id=audit_id).update(status=str(status), reason=reason, end_time=end_time)
    except Exception as e:
        logger.error("Error: there was issue with (updating scan mapping) " + str(e))
        logger.info(e.message)
        logger.info(e.args)


@transaction.atomic
def create_scan_version_id():
    '''
    This function creates Scan version in DB with timestamp & state,
        return scanve version id
    '''
    try:
        with transaction.atomic():
            return ScanVersion.objects.create()
    except IntegrityError as e:
        logger.error("Error: there was issue with (creating scan version id) " + str(e))
        logger.info(e.message)
        logger.info(e.args)


def update_scan_version(scan_version_id, audit_report_url, end_time):
    '''
    This function update Scan version in DB with state of completion
    '''
    try:
        scan_version = ScanVersion.objects.get(id=scan_version_id)
        scan_version.status = 1
        scan_version.audit_report_url = audit_report_url
        scan_version.end_time = end_time
        scan_version.save(force_update=True)
    except Exception as e:
        logger.error("Error: there was issue with (updating scan version id) " + str(e))
        logger.info(e.message)
        logger.info(e.args)


def generate_csv_report(scan_version_id):
    '''
    This function generates a report & export all scaned mappings from DB
        after all scanning is complete to CSV file
    '''
    audit_reports_directory = config.get('BAZAAR', 'audit_reports_directory')
    os.chdir(audit_reports_directory)
    list_of_mappings = get_list_of_mappings_by_svid(scan_version_id)
    report_date = datetime.now().date().isoformat()
    audit_report = "audit_report_%s_%s.csv" % (scan_version_id, report_date)
    audit_report_file = "%s%s" % (audit_reports_directory, audit_report)
    base_url =  config.get('BAZAAR', 'audit_reports_url')
    audit_reports_url =  "%s%s" % (base_url, audit_report)
    if list_of_mappings:
        try:
            with open(audit_report, 'w') as csv_file:
                headers=['Gerrit Repo', 'Gerrit Repo Revision', 'Gerrit Repo Owner', 'Audit ID', 'Project ID', 'Report URL', 'Start of Scan', 'End of Scan', 'Status', 'Reason']
                writer = csv.DictWriter(csv_file, fieldnames=headers, lineterminator='\n')
                writer.writer.writerow(headers)
                for mapping in list_of_mappings:
                    writer.writerow({
                        'Gerrit Repo':mapping['gerrit_repo__repo_name'],
                        'Gerrit Repo Revision':mapping['gerrit_repo__repo_revision'],
                        'Gerrit Repo Owner': mapping['gerrit_repo__owner'],
                        'Audit ID':mapping['audit_id'],
                        'Project ID':mapping['project_id'],
                        'Report URL':mapping['report_url'],
                        'Start of Scan': mapping['start_time'],
                        'End of Scan':mapping['end_time'],
                        'Status':mapping['status'],
                        'Reason': mapping['reason']
                    })
        except Exception as e:
            err_msg = "Error: there was issue with generating CSV report %s" % str(e)
            logger.error(err_msg)
            logger.info(e.message)
            logger.info(e.args)
            audit_reports_url = err_msg
    else:
        err_msg = "Error: there was issue with generating CSV report, No FOSS Scan Audit Content found"
        logger.error(err_msg)
        audit_reports_url = err_msg
    return audit_reports_url


def get_list_of_mappings_by_svid(scan_version_id):
    '''
    This function fetch all mapping objects from DB,
        return a list of mappings including their values for CSV reporting
    '''
    try:
        return ScanMapping.objects.filter(scan_version = scan_version_id).values(
                'gerrit_repo__repo_name',
                'gerrit_repo__repo_revision',
                'gerrit_repo__owner',
                'audit_id',
                'project_id',
                'report_url',
                'start_time',
                'end_time',
                'status',
                'reason')
    except Exception as e:
        logger.error("Error: there was issue with (getting a list of mapping by SVID): %s", str(e))
        logger.info(e.message)
        logger.info(e.args)


def get_all_gerrit_projects():
    '''
    This function for getting all gerrit projects master branch revision/sha1s,
        returns a list of gerrit projects(repos) and master revision/sha1s
    '''
    try:
        gerrit_port = str(config.get('GERRIT_SSH', 'gerrit_port'))
        gerrit_hostname = str(config.get('GERRIT_SSH', 'gerrit_hostname'))
        gerrit_username = str(config.get('GERRIT_SSH', 'gerrit_username'))
        command = "ssh -p %s %s@%s gerrit ls-projects --all -b master" % (gerrit_port, gerrit_username, gerrit_hostname)
        process = subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        output, exit_value = process.communicate()[0], process.returncode
        if not exit_value == 0:
            err_msg = "Issue getting the projects from gerrit: " + str(command)
            logger.error(err_msg)
            return err_msg
        gerrit_projects = dict()
        for item in str(output).split("\n"):
            if "OSS/" in item:
                value, key = str(item.strip()).split(' ')
                gerrit_projects[key] = value
        return gerrit_projects
    except Exception as e:
        logger.error("Error: there was issue with getting a list of gerrit project master branch sha1s: %s", str(e))


def get_list_of_repos(gerrit_repos=None):
    '''
    This function fetch all repo objects from DB,
        returns a list of Repo URLs and their IDs
    '''
    try:
        values = ('id', 'repo_name', 'repo_revision')
        gerrit_repos_list = list()
        if gerrit_repos:
            if "," in gerrit_repos:
                gerrit_repos_list = gerrit_repos.split(",")
            else:
                gerrit_repos_list.append(gerrit_repos)
            gerrit_repos_list = list(GerritRepo.objects.only(values).values(*values).filter(repo_name__in=gerrit_repos_list))
        else:
            gerrit_repos_list = list(GerritRepo.objects.filter(scan=1).only(values).values(*values))
        return gerrit_repos_list
    except Exception as e:
        logger.error("Error: there was issue with (getting list of repos) %s", str(e))
        logger.info(e.message)
        logger.info(e.args)


def clone_gerrit_repo(temp_dir, repo):
    '''
    This function clone a repo to temp folder & return cloned directory
    '''
    logger.info("Starting to clone repo %s to a temp directory", repo)
    try:
        gerrit_port = str(config.get('GERRIT_SSH', 'gerrit_port'))
        gerrit_mirror_hostname = str(config.get('GERRIT_SSH', 'gerrit_mirror_hostname'))
        gerrit_username = str(config.get('GERRIT_SSH', 'gerrit_username'))
        stripped_repo = repo.strip()
        directory_to_project = "%s/%s" % (temp_dir, stripped_repo.split("/")[-1])
        os.chdir(temp_dir)
        command = "git clone ssh://%s@%s:%s/%s " % (gerrit_username, gerrit_mirror_hostname, gerrit_port, repo)
        process = subprocess.Popen(command, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        output, exit_value = process.communicate()[0], process.returncode
        logger.info("Cloning output for %s: %s", repo, output)
        if not exit_value == 0:
           logger.error("Issue with cloning repo: %s", repo)
        project_to_compress = next(os.walk(temp_dir))[1][0]
        return (directory_to_project, project_to_compress)
    except Exception as e:
        logger.error("Error: there was issue with cloning repo %s: %s", repo, str(e))
        logger.info(e.message)
        logger.info(e.args)
        logger.info('Removing temp folder because of exception')
        remove_temp_dir_path(temp_dir)


def check_for_open_sockets():
    '''
    This function checks if https socket is open
    '''
    err_msg = ""
    papi_server = str(config.get('BAZAAR', 'papi_server'))
    papi_port = int(config.get('BAZAAR', 'papi_port'))
    ftp_server = str(config.get('BAZAAR', 'ftp_server'))
    ftp_port = int(config.get('BAZAAR', 'ftp_port'))
    logger.info('Checking for open Sockets to Bazaar')
    sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result=sock.connect_ex((papi_server, papi_port))
    if result == 0:
        sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result=sock.connect_ex((ftp_server, ftp_port))
        if result == 0:
            logger.info('Ports %s:%s and %s:%s is open.', papi_server, papi_port, ftp_server, ftp_port)
            logger.info('No Proxy needed. Checking is complete, back to the script execution.')
        else:
            err_msg = 'Error: Port %s:%s is closed! Request firewall change in zcms or via ITTE.ticket!' % (ftp_server, ftp_port)
            logger.error(err_msg)
            return 1, err_msg
    else:
        err_msg = 'Error: Port %s:%s is closed! Request firewall change in zcms or via ITTE.ticket!' % (papi_server, papi_port)
        logger.error(err_msg)
        return 1, err_msg
    return 0, err_msg


def create_audit(user_name, bazaar_token, local_proj_dir, svl_number):
    '''
    This function creates audit_id and checks for failed attempts
    '''
    logger.info('Starting creation for Audit ID')
    facility = 'FOSS_AUDIT'
    foss_audit_facility_command = 'create'
    logger.debug('User (esignum) = %s, local_proj_dir = %s, facility = %s, project = %s', user_name, local_proj_dir, facility, str(int(svl_number)))
    bazaar_audit_id, count_failed_attempts = curl_auditing_facility(user_name, bazaar_token, local_proj_dir, svl_number, facility, foss_audit_facility_command)
    return_value = []
    return_value.append(bazaar_audit_id)
    return_value.append(count_failed_attempts)
    logger.info('Audit created ' + str(return_value))
    return return_value


def check_scan_status(user_name, bazaar_token, local_proj_dir, list_of_audit_ids):
    '''
    This function checks for audit status
    '''
    logger.info('Starting scan for audit status')
    facility = 'FOSS_AUDIT'
    foss_audit_facility_command='status'
    os.chdir(local_proj_dir)
    for audit_id in list_of_audit_ids:
        logger.info('Checking status of audit --- BA-%s --- ', str(audit_id))
        curr_status = ''
        while curr_status != 'completed':
            scan_status, number_of_failed_attempts_due_to_bazaar = curl_auditing_facility(user_name, bazaar_token, local_proj_dir, audit_id, facility, foss_audit_facility_command)
            curr_status = scan_status
            if curr_status == '':
                curr_status = 'Preparing for Auditing'
            update_scan_mapping(audit_id, curr_status)
            audit_log(audit_id, curr_status)
            if number_of_failed_attempts_due_to_bazaar == 3:
                break
            time.sleep(10)


def audit_log(svl, curr_status):
    '''
    This function prints a LOG of Audit status to CLI
    '''
    logger.info('--------------------------------------------------------------------')
    logger.info('Current status for audit BA-' + str(svl) + ' is : ' + str(curr_status))
    logger.info('--------------------------------------------------------------------')


def curl_auditing_facility(user_name, bazaar_token, local_proj_dir, svl_number, facility, foss_audit_facility_command):
    '''
    This function run curl command towards Bazaar api,
        1.Trigger create command that creates Audit ID and return it with status of it.
        2.Trigger status command that return state of current scanning of package base on Audit ID.
        During execution, creates a report which consist of connection between Server and Bazaar API
    '''
    papi_server = str(config.get('BAZAAR', 'papi_server'))
    logger.info('Running and checking curl foss auditing facility')
    number_of_scan_attepts = 0
    expected_value = None
    number_of_failed_attempts_due_to_bazaar = 0
    if foss_audit_facility_command == 'create':
        foss_audit_facility_suffix = '"svl":"%s"' % str(int(svl_number))
        expected_key = 'audit_id'
        logger.info('Suffix created ' + str(foss_audit_facility_suffix))
    elif foss_audit_facility_command == 'status':
        foss_audit_facility_suffix = '"audit_id":"%s"' % str(int(svl_number))
        expected_key = "status"
        expected_audit_statuses = ['created','completed','','external FOSS check ongoing','external FOSS check completed','whitelisting','not analyzable marked','fingerprinting','checking file types']
    try:
        while number_of_scan_attepts < 3:
            query_data = '"username":"%s","token":"%s","facility":"%s","command":"%s",%s' % (user_name, bazaar_token, facility, foss_audit_facility_command, foss_audit_facility_suffix)
            request_log_file = "%s/traces_from_curl_%s_command__%s_%s.log" % (local_proj_dir, foss_audit_facility_command, str(datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')), str(uuid.uuid4()))
            command = "curl -L -k -sS --noproxy '*' 'https://%s?query=\{%s\}' --trace-ascii '%s'" % (papi_server, query_data, request_log_file)
            logger.debug('command: %s', command.replace(bazaar_token, "********"))
            logger.debug("Running curl command %s, attempt %s of possible max. 3.", str(foss_audit_facility_command), str(number_of_scan_attepts + 1))
            process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
            curl_answer, err = process.communicate()
            exit_value = process.returncode
            logger.debug("curl_answer(len=:%s): %s", str(len(curl_answer)), str(curl_answer))
            logger.debug("curl returncode: %s", str(exit_value))
            bazaar_response = check_response_from_bazaar(curl_answer, request_log_file, facility, foss_audit_facility_command)
            if bazaar_response == 'OK':
                json_curl_answer = json.loads(curl_answer)
                if ((foss_audit_facility_command=='create') or (foss_audit_facility_command=='status')):
                    if json_curl_answer.has_key(expected_key):
                        if foss_audit_facility_command == 'create':
                            if check_if_int(json_curl_answer[expected_key]):
                                expected_value = json_curl_answer[expected_key]
                                break
                        elif foss_audit_facility_command == 'status':
                            if json_curl_answer[expected_key] in expected_audit_statuses:
                                expected_value = json_curl_answer[expected_key]
                                break
            else:
                logger.warning("Response from bazaar is not OK (bazaar_response:%s).", bazaar_response)
                expected_value = bazaar_response
                number_of_failed_attempts_due_to_bazaar += 1
                number_of_scan_attepts += 1
    except Exception as e:
        logger.error("Error: %s audit subroutine crashed! Aborting script!, %s", str(foss_audit_facility_command), str(e))
        sys.exit(1)
    return expected_value, number_of_failed_attempts_due_to_bazaar


def check_response_from_bazaar(curl_answer, request_log_file, facility, foss_audit_facility_command):
    '''
    This function checks and return response about connectivity between Server and Bazaar
    '''
    logger.info("Run Check response from bazaar")
    if  len(curl_answer) > 0 and str(curl_answer) == '{"error":"USER_INVALID"}':
        logger.error("Error: USER_INVALID - Please correct your user name or Bazaar Token and run the script again!\n")
        sys.exit(1)
    elif len(curl_answer) > 0 and bool(re.match(str('<!DOCTYPE HTML PUBLIC'), str(curl_answer), re.I)):
        joined_curl_answer = '' #HTML data - check if it is internal server error - in case if rescan is necessary
        for element_of_curl_answer in curl_answer:
            joined_curl_answer = joined_curl_answer + "".join(element_of_curl_answer.strip('\n').strip())
            parser = TagParser()
            result = parser.feed(joined_curl_answer)
            if parser.rescan_due_to_internal_server_error:
                logger.warning('Curl command fail due to internal server error.')
                os.remove(str(request_log_file))
                return 'Internal Server Error'
            else:
                logger.warning('Unknown response from Bazaar.')
                return 'unknown problem with scan'
    elif len(curl_answer) > 0 and str(curl_answer).startswith('{"error":"FILE_MISSING"}'):
        logger.warning('Scan fail due to "FILE_MISSING".')
        return 'FILE_MISSING'
    elif len(curl_answer) > 0:
        json_curl_answer = json.loads(curl_answer)
        if ((foss_audit_facility_command == 'create') or (foss_audit_facility_command == 'status')):
            if type(json_curl_answer) is dict:
                os.remove(str(request_log_file))
                return 'OK'
            else:
                return 'curl_answer is not a dictionary'


def check_if_int(value_to_check):
    '''
    Checking if value passed is INT
    '''
    logger.info('Starting checking value for INT')
    if isinstance(value_to_check, basestring):
        if value_to_check.isdigit:
            try:
                int_value_to_check = int(value_to_check)
            except ValueError:
                return False
            except TypeError:
                return False
            try:
                float_value_to_check = float(value_to_check)
            except ValueError:
                return False
            except TypeError:
                return False
            if (float_value_to_check-int_value_to_check)==0:
                return True
        else:
            return False
    elif (type(value_to_check) is int) or (type(value_to_check) is long):
        return True
    else:
        return False


def get_result(audit_id, bazaar_svl, repo):
    '''
    This function return a url Report about auditing
        and repo name back to user
    '''
    report_url = "%s%s&auditid=%s" % (str(config.get('BAZAAR', 'bazaar_report_url')), str(bazaar_svl), str(audit_id))
    logger.info('-----------------------Reporting--------------------------')
    logger.info('Report URL: %s', report_url)
    logger.info('Repository: %s', str(repo.strip()))
    logger.info('-----------------------Finished---------------------------')
    return report_url, 'Preparing for Auditing'


def compress_to_tar_gz(project_to_compress, temp_dir, audit_id):
    '''
    This function compress pulled repo folder to TAR.GZ
    '''
    logger.info('Starting compressing local project to TAR.GZ')
    try:
        with closing(tarfile.open('BA-' + str(audit_id[0]) + '.tar.gz', 'w:gz')) as tar:
            tar.add(project_to_compress, arcname=project_to_compress)
            for file in os.listdir(temp_dir):
                if file.endswith('.tar.gz'):
                    compressed_project = next(os.walk(temp_dir))[2][0]
                    return compressed_project
    except Exception as e:
        logger.info(e.message)
        logger.info(e.args)
        remove_temp_dir_path(temp_dir)


def send_tar_gz_for_scan(compressed_project, temp_dir):
    '''
    This function send a prepared TAR.GZ to bazaar for scanning
    '''
    logger.info('Sending tar.gz to Bazaar FTP')
    try:
        SPAMLOGLEVEL = 1
        ftp_server = config.get('BAZAAR', 'ftp_server')
        ftp_user = config.get('BAZAAR', 'ftp_user')
        ftp_password = config.get('BAZAAR', 'ftp_password')
        if logger.isEnabledFor(SPAMLOGLEVEL):
            ftp_logging_level = 2
        else:
            ftp_logging_level = 0
        ftp = FTP(ftp_server)
        ftp.set_debuglevel(ftp_logging_level)
        ftp.login(user=ftp_user, passwd=ftp_password)
        tar_path = os.path.join(temp_dir, compressed_project)
        logger.info('Sending tar: ' + str(tar_path))
        tar_file_handle = open(os.path.realpath(tar_path), 'rb')
        logger.debug("%d ftp_server = %s, ftp_user = %s, ftp_password = %s, tar_name = %s", SPAMLOGLEVEL, str(ftp_server), str(ftp_user), str(ftp_password), str(compressed_project))
        ftp.storbinary('STOR '+compressed_project, tar_file_handle)
        ftp.quit()
        tar_file_handle.close()
    except Exception as e:
        logger.info(e.message)
        logger.info(e.args)
        logger.info('removing folder because of exception')
        remove_temp_dir_path(temp_dir)


def generate_final_report(list_of_audit_ids, list_of_repos, bazaar_svl):
    '''
    This function generates a final report at the end of scanning
    '''
    logger.info('-----------------------Final Report----------------------')
    for audit_id, repo in itertools.izip(list_of_audit_ids, list_of_repos):
        logger.info('--- BA-%s ---', str(audit_id))
        logger.info('Report URL: %s%s&auditid=%s', str(config.get('BAZAAR', 'bazaar_report_url')), str(bazaar_svl), str(audit_id))
        logger.info('Repository: %s', str(repo['repo_name'].strip()))


def get_temp_dir_path():
    '''
    This function create a temporary directory and return path.
    '''
    logger.info('Creating temporary Directory')
    return tempfile.mkdtemp()


def remove_temp_dir_path(temp_dir):
    '''
    This function remove a temporary directory
    '''
    try:
        logger.info('Deleting temporary Directory')
        shutil.rmtree(temp_dir)
    except:
        logger.debug("already Deleted")


def send_report_email(scan_version_id, audit_report_url, to_email=None, content=None):
    '''
    This function sends an e-mail
    '''

    mail_header = "FOSS Scan Audit Report No. %s  Date: %s " % (scan_version_id, datetime.now().date().isoformat())
    mail_content = ""
    if content:
       mail_content = content
    else:
        mail_content = "Dear Team, <br><br>"
    mail_content += 'Link to full report: <a href="%s">FOSS Scan Audit Report</a>' % audit_report_url
    mail_content += "<br><br>Kind Regards, <br>CI Portal Admin"

    to_emails = []
    from_email = config.get("CIFWK", "cifwkDistributionList")
    if to_email:
        to_emails.append(to_email)
    else:
        to_emails.append(from_email)
    msg = EmailMultiAlternatives(mail_header, mail_content, from_email, to_emails)
    msg.content_subtype = "html"
    msg.send()


def owner_email_content(scan_version_id, owner):
    '''
    This function creates the owner email content for audit report email
    '''
    values = ('gerrit_repo__repo_name', 'gerrit_repo__repo_revision', 'gerrit_repo__owner',
                'audit_id', 'project_id', 'report_url', 'start_time', 'end_time', 'status', 'reason')
    content = None
    scan_reports = ScanMapping.objects.only(values).filter(scan_version = scan_version_id, gerrit_repo__owner_email=owner['owner_email']).values(*values)
    table_headers = ['Gerrit Repo', 'Gerrit Repo Revision', 'Gerrit Repo Owner', 'Audit ID', 'Project ID', 'Report URL', 'Start of Scan', 'End of Scan', 'Status', 'Reason']
    if scan_reports:
        content = "Dear %s, <br><br>" % owner['owner']
        content += "Following FOSS Scan Report is on the repo(s) in which you are CNA for: <br><br>"
        content += "<table border='1'><tr>"
        for header in table_headers:
            content += "<th>%s</th>" % header
        content +="</tr>"
        for scan_report in scan_reports:
            table_content = [scan_report['gerrit_repo__repo_name'], scan_report['gerrit_repo__repo_revision'],
                             scan_report['gerrit_repo__owner'], scan_report['audit_id'], scan_report['project_id'],
                             scan_report['report_url'], scan_report['start_time'], scan_report['end_time'],
                             scan_report['status'], scan_report['reason']]
            content += "<tr>"
            for item in table_content:
                if not item or item == "None":
                    item = ""
                content += "<td>%s</td>" % item
            content += "</tr>"
        content +="</table><br>"
    return content


def send_audit_report_emails(scan_version_id, audit_report_url):
    '''
    This function is for sending FOSS Scan Audit Emails
    '''
    owners =  GerritRepo.objects.values('owner', 'owner_email').distinct()
    for owner in owners:
        content = owner_email_content(scan_version_id, owner)
        if content:
            send_report_email(scan_version_id, audit_report_url, owner['owner_email'], content)
    send_report_email(scan_version_id, audit_report_url)

