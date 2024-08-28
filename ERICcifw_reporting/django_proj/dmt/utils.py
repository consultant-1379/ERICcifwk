from ConfigParser import SafeConfigParser
from cireports.models import *
from dmt.models import *
from ciconfig import CIConfig
from django.core.management.base import BaseCommand, CommandError
from django.http import HttpResponse, Http404, HttpResponseRedirect
from netaddr import IPNetwork, IPAddress
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry

import ast
import dmt.sshtunnel
import dmt.sftp
import fwk.utils
import dmt.cloud
import subprocess, os, sys, time, getpass, signal, urllib2, traceback, socket, logging, re, commands
import random, pexpect, paramiko, tempfile, shutil, struct, io
import tarfile, iptools
import distutils.dir_util
import os.path
import logging
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User, Group
from guardian.conf import settings as guardian_settings
from guardian.exceptions import GuardianError
from guardian.shortcuts import get_perms, assign_perm,remove_perm
from guardian.core import ObjectPermissionChecker
from datetime import datetime, timedelta, date
from posix import *
import json
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from collections import defaultdict
from django.db.models import Q
from distutils import version
import os
from subprocess import *
import requests
from django.utils.encoding import smart_str
from dmt.logUserActivity import logAction, logChange

paramiko.util.log_to_file('/tmp/paramiko.log')

logger = logging.getLogger(__name__)
config = CIConfig()

def permissionRequest(requestUser, object, option=None):
    '''
    The permissionRequest function covers the checking of permission on the user if admin
    else it checks by user which be part of group with permissions. Doing this by taking in the user, the object and
    option that could be i.e. edit or delete for now
    '''
    user = User.objects.get(username=str(requestUser))
    if user == User.objects.get(username='admin'):
        logger.debug("User is : " + str(user))
        return True
    elif option != None and user != User.objects.get(username='admin'):
        checker = ObjectPermissionChecker(user)
        if "edit" in option:
            logger.debug(str(object))
            if checker.has_perm('change_cluster_guardian', object):
                return True
            else:
                return False
        elif "delete" in option:
            if checker.has_perm('delete_cluster_guardian', object):
                return True
            else:
                return False
    elif user != User.objects.get(username='admin'):
        checker = ObjectPermissionChecker(user)
        if checker.has_perm('change_cluster_guardian', object):
            return True
        else:
            return False

def getLowestAvailableTIPCAddress():
    '''
    return the next available TIPC address.
    '''
    clusters = Cluster.objects.all().order_by('tipc_address')
    tipc_lowest = 1000
    for c in clusters:
        tipc_lowest = tipc_lowest + 1
        if c.tipc_address > tipc_lowest:
            logger.error("Got " + str(c.tipc_address) + " > " + str(tipc_lowest))
            return tipc_lowest
    logger.error("Fallen off the end, with " + str(tipc_lowest + 1))
    return tipc_lowest + 1

def randomMacAddress():
    '''
    The randomMacAddress function generated a random mac address for virtual servers
    '''
    mac = [ 0x00, 0x16, 0x3e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))

def getLowestAvailableMacAddress(cluster_id):
    '''
    retrieve the next available MAC address from the DB
    '''
    # we will most likely eventually need multiple prefixes
    # the first two were originally allocated to CI and RV. The CI
    # prefix should never have been used so won't have been used in
    # existing clusters
    if cluster_id == None:
        macLowest = config.get('DMT_MGMT','macLowest')
        macHighest = config.get('DMT_MGMT','macHighest')
    else:
        cluster = Cluster.objects.get(id=cluster_id)
        macLowest = cluster.mac_lowest
        macHighest = cluster.mac_highest

    prefixList = macLowest.split(":", 4)
    prefix = prefixList[0] + ":" + prefixList[1] + ":" + prefixList[2] + ":" + prefixList[3]

    lowpostfix = macLowest.rsplit(":", 2)
    lowest = int("0x" + lowpostfix[1] + lowpostfix[2], base=16)
    maxpostfix = macHighest.rsplit(":", 2)
    maxint = int("0x" + maxpostfix[1] + maxpostfix[2], base=16)
    intpost = 0
    nics = NetworkInterface.objects.filter(mac_address__startswith=prefix).order_by('mac_address')
    for nic in nics:
        # strip down to last two tuples
        postfix = nic.mac_address.rsplit(":", 2)
        intpost = int("0x" + postfix[1] + postfix[2], base=16)
        if intpost > lowest:
            # found a hole in the range
            strmac = hex(lowest).rsplit("0x")[-1]
            # prefix 0 for all missing characters
            if lowest < 16:
                strmac = "000" + strmac
            elif lowest < 256:
                strmac = "00" + strmac
            elif lowest < 4096:
                strmac = "0" + strmac
            # join on the prefix and interpolate a ":" in the last four characters
            strmaclist = list(strmac)
            strmaclist.insert(2, ":")
            strmac = prefix + ":" + "".join(strmaclist)
            logger.error("Got MAC " + strmac + " from " + str(lowest))
            return strmac
        lowest = lowest + 1
    # Reached the end of the defined MACs, do we have a "lowest" which is lover than maxint
    logger.error("Got the lowest: " + str(lowest) + " compared to " + str(intpost))
    if lowest <= maxint:
        strmac = hex(lowest).rsplit("0x")[-1]
        # prefix 0 for all missing characters
        if lowest < 16:
            strmac = "000" + strmac
        elif lowest < 256:
            strmac = "00" + strmac
        elif lowest < 4096:
            strmac = "0" + strmac
        # join on the prefix and interpolate a ":" in the last four characters
        strmaclist = list(strmac)
        strmaclist.insert(2, ":")
        strmac = prefix + ":" + "".join(strmaclist)
        logger.error("Got MAC " + strmac + " from " + str(lowest))
        return strmac
    lowest = lowest + 1
    # If we got here, all our MAC addresses are used up!
    return CommandError("No more MACS available")

def getLowestStartEndMacAddress():
    '''
    retrieve the next available Start and end MAC address for the cluster from the DB
    '''
    # we will most likely eventually need multiple prefixes
    # the first two were originally allocated to CI and RV. The CI
    # prefix should never have been used so won't have been used in
    # existing clusters
    allowedPrefixes = (
            'CA:22:50',
            'DE:AD:BE',
            'FA:DE:2B',
            'EE:CB:1D',
            'BE:EF:FE',
            'FA:BB:EE',
            '26:EF:01',
            )

    maxint = int("FF", base=16)
    StarEndMacList = []
    for prefix in allowedPrefixes:
        lowest = 0
        intpost = 0
        clusters = Cluster.objects.filter(mac_lowest__startswith=prefix).order_by('mac_lowest')
        for cluster in clusters:
            lowest = lowest + 1
            # strip down to last three tuples
            postfix = cluster.mac_lowest.rsplit(":", 3)
            intpost = int(postfix[1], base=16)
            if intpost > lowest:
                strmac = hex(lowest).rsplit("0x")[-1]
                # prefix 0 for all missing characters
                if lowest < 16:
                    strmac = "0" + strmac
                # join on the prefix and interpolate a ":" in the last four characters
                strmaclist = list(strmac)
                # found a hole in the range
                strmac = prefix + ":" + "".join(strmaclist) + ":00:00"
                finmac = prefix + ":" + "".join(strmaclist) + ":FF:FF"
                logger.error("Got MAC " + strmac + " from " + str(lowest))
                StarEndMacList.append(str(strmac))
                StarEndMacList.append(str(finmac))
                return StarEndMacList
        # Reached the end of the defined MACs, do we have a "lowest" which is lover than maxint
        lowest = lowest + 1
        logger.error("Got the lowest: " + str(lowest) + " compared to " + str(intpost))
        if lowest <= maxint:
            strmac = hex(lowest).rsplit("0x")[-1]
            # prefix 0 for all missing characters
            if lowest < 16:
                strmac = "0" + strmac
            # join on the prefix and interpolate a ":" in the last four characters
            strmaclist = list(strmac)
            strmac = prefix + ":" + "".join(strmaclist) + ":00:00"
            finmac = prefix + ":" + "".join(strmaclist) + ":FF:FF"
            logger.error("Got MAC " + strmac + " from " + str(lowest))
            StarEndMacList.append(str(strmac))
            StarEndMacList.append(str(finmac))
            return StarEndMacList
        # If we got here, all our MAC addresses are used up!
        return CommandError("No more MACS available")

def genDHCPConfig(hostname, macAddress, fixedAddress, dnsServerA, dnsServerB, domainName, mgmtServerFqdn):
    '''
    The genDHCPConfig function generates a local cifwk.config file with all
    servers that are in a cluster thats dhcp lifetime is in date
    '''
    sftpDHCPLocalFile = config.get('DMT_DHCP_SFTP', 'sftpDHCPLocalFile')
    try:
        mgmtServerIpAddress = socket.gethostbyname(mgmtServerFqdn)
    except Exception as e:
        logger.error("Unable to get the IP address of the LMS:")
        handlingError(str(e))
    generatedDHCPFile = open(sftpDHCPLocalFile,'ab')
    generatedDHCPFile.write("host " + str(hostname) + " {\n")
    generatedDHCPFile.write("hardware ethernet " + str(macAddress) + ";\n")
    generatedDHCPFile.write("fixed-address " + str(fixedAddress) + ";\n")
    generatedDHCPFile.write("option domain-name-servers " + str(dnsServerA) + ";\n")
    generatedDHCPFile.write("option domain-name-servers " + str(dnsServerB) + ";\n")
    generatedDHCPFile.write("option domain-name \"" + str(domainName) + "\";\n")
    generatedDHCPFile.write("next-server " + mgmtServerIpAddress + ";\n")
    generatedDHCPFile.write("}\n\n")
    generatedDHCPFile.close()

def sftpDHCPFile(localFile):
    '''
    The sftpDHCPFile function should use the  to sftp files
    '''
    sftpDHCPNode = config.get('DMT_DHCP_SFTP', 'sftpDHCPNode')
    sftpDHCPUser = config.get('DMT_DHCP_SFTP', 'sftpDHCPUser')
    sftpDHCPRemoteFile = config.get('DMT_DHCP_SFTP', 'sftpDHCPRemoteFile')
    sftpDHCPPort = int(config.get('DMT_DHCP_SFTP', 'sftpDHCPPort'))
    sftpDHCPPrivateKeyFile = config.get('DMT_DHCP_SFTP', 'sftpDHCPPrivateKeyFile')
    try:
        paramikoSftp(sftpDHCPNode,sftpDHCPUser,sftpDHCPRemoteFile,localFile,sftpDHCPPort,sftpDHCPPrivateKeyFile)
    except Exception as e:
        logger.error("Unable to call the paramiko sftp function with all arguments: ")
        handlingError(str(e))
    try:
        dhcpServiceRestartCommand = "ssh -l " +sftpDHCPUser+ " " +sftpDHCPNode+ " sudo service dhcpd restart"
        os.system(dhcpServiceRestartCommand)
        logger.info("Restart DHCP Service was a success ")
    except Exception as e:
        logger.error("Restart DHCP Service was a Failure: ")
        handlingError(str(e))

def paramikoSftp(node, user, remoteFile, localFile, port, key, type="put"):
    privatekeyfile = os.path.expanduser(key)
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    baseDir = os.path.dirname(remoteFile)
    try:
        transport = paramiko.Transport((node, port))
    except Exception as e:
        logger.error("Problem establishing transport connect to SFTP Server")
        handlingErrorReturnCode(str(e))
        return 1
    try:
        transport.connect(username = user, pkey = mykey)
    except Exception as e:
        logger.error("There was an issue connecting to SFTP server using private key")
        handlingErrorReturnCode(str(e))
        return 1
    try:
        sftp = paramiko.SFTPClient.from_transport(transport)
    except Exception as e:
        logger.error("There was an issue setting up SFTP Client")
        handlingErrorReturnCode(str(e))
        return 1
    if type == "put":
        try:
            sftp.mkdir(baseDir)
        except IOError:
            logger.info("Directory Already Exists " + str(baseDir))
        try:
            sftp.put(localFile,remoteFile)
        except Exception as e:
            logger.error("There was an issue sftp'n the local file to the SFTP Server localFile: " + str(localFile) + " remote File: " + str(remoteFile))
            handlingErrorReturnCode(str(e))
            return 1
    else:
        try:
            sftp.get(str(remoteFile),localFile)
        except Exception as e:
            logger.error("There was an issue sftp'n the remote file to the SFTP Server remote File: " + str(remoteFile) + " localFile: " + str(localFile))
            handlingErrorReturnCode(str(e))
            return 1
    try:
        sftp.close()
    except Exception as e:
        logger.error("The was an issue closing the client on the sftp server: ")
        handlingErrorReturnCode(str(e))
        return 1
    try:
        transport.close()
    except Exception as e:
        logger.error("The was an issue closing the transport tunnell to the sftp server: ")
        handlingErrorReturnCode(str(e))
        return 1
    return 0

def updateDHCPServer():
    '''
    The updateDHCPServer function updates the cifwk.config file on the dhcp server
    with all servers in all cluters where their dhcp lifetime is not old then 24 hours
    '''
    clusters = Cluster.objects.all()
    localDhcpFile = config.get('DMT_DHCP_SFTP', 'sftpDHCPLocalFile')
    for cluster in clusters:
        clusterName = cluster.name
        logger.debug("Currently in cluster:"+str(clusterName))
        mgmtServerName = str(cluster.management_server.server.hostname)
        logger.debug("Management Server for this cluster is: " +str(mgmtServerName))
        mgmtServerObject = ManagementServer.objects.get(server__hostname = cluster.management_server)
        mgmtServerDomain = str(mgmtServerObject.server.domain_name)
        mgmtServerFqdn = mgmtServerName + "." + mgmtServerDomain
        logger.debug("The FQDN of the LMS for this cluster is: " +mgmtServerFqdn)
        clusterDHCPLifetime = cluster.dhcp_lifetime
        yesterday = default=datetime.now()-timedelta(days=0)
        if clusterDHCPLifetime < yesterday:
            logger.debug("The Deployment: " +str(clusterName)+ " DHCP Lifetime is out of date")
        elif clusterDHCPLifetime > yesterday:
            logger.debug("The Deployment: " +str(clusterName)+ " DHCP Lifetime is not out of date")
            servers = ClusterServer.objects.filter(cluster=cluster)
            for s in servers:
                try:
                    serverObject = Server.objects.get(hostname=s.server.hostname)
                    dnsServerA = serverObject.dns_serverA
                    dnsServerB = serverObject.dns_serverB
                    domainName = serverObject.domain_name
                    networkObject = NetworkInterface.objects.get(server=s.server.id)
                    nic =  str(networkObject)
                    ipAddrObject = IpAddress.objects.get(nic=networkObject.id)
                    ipAddress = str(ipAddrObject)
                    logger.info("Server Information retreived from DB with Success")
                except Exception as e:
                    #remove local cifwk.conf file if it exists
                    if (os.path.exists(localDhcpFile)):
                        os.unlink(localDhcpFile)
                    raise CommandError("Each Server Registered needs a Hostname, IP, MAC, DNS and domain name, you are getting this error as some registered servers are not complete")
                    handlingError(str(e))
                try:
                    logger.info("Attempting to generated cifwk.conf file")
                    genDHCPConfig(s, nic, ipAddress, dnsServerA, dnsServerB, domainName, mgmtServerFqdn)
                except Exception as e:
                    logger.error("Unable to generate local cifwk.conf file: ")
                    handlingError(str(e))
    #Attempt to scp the local cifwk.conf file to dhcp server
    try:
        sftpDHCPFile(localDhcpFile)
    except Exception as e:
        logger.error("There was an issue called the SFTP DHCP file Function: ")
        handlingError(str(e))
    if (os.path.exists(localDhcpFile)):
        os.unlink(localDhcpFile)

def runLitpCommands(mgmtServerUser, lms, artifactDict, litpCommands):
    '''
    The runLitpCommands function uses the pyton expect module to run command on the LITP
    management server
    '''
    litpcommandDir ={}

    now = default=datetime.now()
    dmtLogFileLoc = config.get('DMT_LOG', 'dmtLogFileLoc')
    #bootMgrScript = config.get('DMT_LOG', 'bootMgrScript')
    logFilesuffix = now.strftime("%Y%m%d-%H%M%S")
    cluster = "autoMediationDeploy"
    installLogFile = dmtLogFileLoc + 'cluster-' + cluster + "install" + logFilesuffix + '.log'
    logger.info("Mediation Install log can be found here: " +str(installLogFile))

    mediationDeploy = config.get('DEPLOY', 'mediationTemplate')

    sshCommand = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no " + mgmtServerUser + "@" + lms

    try:
        child = pexpect.spawn (sshCommand)
    except Exception as e:
        logger.error("There was a problem spawning of to LITP MS: ")
        handlingError(str(e))
    try:
        sshOut = file(installLogFile,'w')
        child.logfile = sshOut
    except Exception as e:
        logger.error("There was a problem setting up the install log file: ")
        handlingError(str(e))

    #Make a backup of IMM DB and XML Files on SC's pre install
    backupDir = "IMM_CIFWK_BKUP-" + str(logFilesuffix)
    sclist = ['SC-1','SC-2']
    for sc in sclist:
        child.expect([pexpect.TIMEOUT, '#'], timeout=600)
        child.sendline ('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@'+str(sc))
        child.expect([pexpect.TIMEOUT, '#'], timeout=600)
        child.sendline ('mkdir -p ' +str(backupDir))
        child.expect([pexpect.TIMEOUT, '#'], timeout=600)
        child.sendline ('cp /cluster/storage/clear/coremw/etc/imm.db ' + str(backupDir))
        child.expect([pexpect.TIMEOUT, '#'], timeout=600)
        child.sendline ('cp /cluster/storage/clear/coremw/etc/imm_basic.xml ' + str(backupDir))
        child.expect([pexpect.TIMEOUT, '#'], timeout=600)
        child.sendline ('exit')

    #Need to find the max campain number and count from there and update litp Commands to reflect this
    child.expect([pexpect.TIMEOUT, '#'], timeout=600)
    child.sendline ('litp /definition/cmw_installer/ show -rl' + "\n")
    child.expect([pexpect.TIMEOUT, '#'], timeout=600)
    campignInfoReturn = child.before
    campignInfoReturn = re.findall(r'[0-9]+', campignInfoReturn)
    campignInfoReturn = map(int,campignInfoReturn)
    maxCampaignMuber =  max(campignInfoReturn)

    updatedCommandList = []
    count = maxCampaignMuber+1
    for item in litpCommands:
        if "MedCore" in item:
            item = re.sub('camp1','camp'+str(count),item)
            mediationCoreCommand = item
        else:
            item = re.sub('camp1','camp'+str(count),item)
            updatedCommandList.append(item)
        count = count+1
    # MedCore needs to be installed first therefiore first in the list
    updatedCommandList.insert(0,mediationCoreCommand)

    for item in updatedCommandList:
        #child.expect('#')
        try:
            child.sendline (item.format(**litpcommandDir) + "\n")
            child.expect([pexpect.TIMEOUT, '#'], timeout=600)
            logger.info("Command " +str(item.format(**litpcommandDir))+ " ran with success ")
        except Exception as e:
            logger.error("Command " +str(item.format(**litpcommandDir)))
            handlingError(str(e))

    localfile = open(mediationDeploy,'r')
    try:
        for line in localfile:
            if not line.startswith("#"):
                child.expect('#')
                try:
                    child.sendline (line.format(**litpcommandDir))
                    child.expect([pexpect.TIMEOUT, '#'], timeout=600)
                    logger.info("Command " +str(line.format(**litpcommandDir))+ " ran with success ")
                except Exception as e:
                    logger.error("Command " +str(line.format(**litpcommandDir)))
                    handlingError(str(e))
    except Exception as e:
        logger.error("There was an issue running through the command template file: "
                +str(localfile))
        handlingError(str(e))
    try:
        autoDeployCommitCheck(child,artifactDict)
        logger.info("Succesfully Ran through the Auto Deployment Campaign Commit Function")
    except Exception as e:
        logger.error("There was an Issue Running through the Auto Deployment Campaign Commit Function: ")
        handlingError(str(e))
    try:
        child.close()
        logger.info("The ssh spawn was closed with success")
    except Exception as e:
        logger.error("There was a problem closing the ssh spawn ")
        handlingError(str(e))
    return 0

def autoDeployCommitCheck(child,artifactDict):
    '''
    The autoDeployCommitCheck logs onto the SC-1 node of the cluster and checks if modules commit
    '''
    child.expect('#')
    child.sendline ('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@SC-1')
    installTimeout = 1200
    for artifactType,artifacts in artifactDict.items():
        if artifactType == "sdp":
            for artifact,version in artifacts.items():
                try:
                    sdptime = 0
                    while sdptime < installTimeout:
                        child.expect([pexpect.TIMEOUT, '#'], timeout=30)
                        checkArtifactCommitted = ("cmw-repository-list --campaign|xargs cmw-campaign-status | grep -i " + str(artifact) + " | egrep -i 'committed|failed' ")
                        logger.info("Starting check to determine if " +str(artifact) + " has committed")
                        child.sendline (checkArtifactCommitted)
                        child.expect([pexpect.TIMEOUT, '#'], timeout=30)
                        artifactCommittedMessage = str(artifact) + "=COMMITTED"
                        artifactFailedMessage = str(artifact) + "=FAILED"
                        commandOutput = child.before
                        if artifactFailedMessage in commandOutput:
                            handlingError("The Campaign: "+str(artifact)+ " Failed to installed exiting")
                        elif artifactCommittedMessage in commandOutput:
                            logger.info("The Campaign: " +str(artifact)+ " is committed ")
                            break
                        elif artifactCommittedMessage not in commandOutput:
                            logger.info("The Campaign: " +str(artifact)+ " is not yet committed waiting 60 seconds for retry")
                            time.sleep(60)
                            sdptime = sdptime+60
                            if sdptime == installTimeout:
                                handlingError("The Campaign: " +str(artifact)+" has failed to commit in the required time: " +str(installTimeout)+ " seconds")

                except Exception as e:
                    logger.error("The Campaign: " + str(artifact)+
                                 " is not committed exiting: ")
                    handlingError(str(e))

def updateKnownHosts(key, mgmtServerFqdn):
    '''
    The updateKnownHosts function takes in one argument which is enetered into the UI, the
    server key, this is then appended to the end of the local known hosts file so when
    connection is needed to the remote server the local server already knows about it.
    '''
    mgmtServerIpAddress = socket.gethostbyname(mgmtServerFqdn)
    mgmtKnownHostFile = config.get('DMT_MGMT', 'mgmtKnownHostFile')
    try:
        knownHostFile = open(mgmtKnownHostFile,'ab')
        knownHostFile.write(mgmtServerFqdn + "," + mgmtServerIpAddress + " " + key + "\n")
        logger.info("Successfully added the Key to the local Known Hosts file")
    except Exception as e:
        logger.error("There was a issue adding the Key to the local Known Hosts file")
        handlingError(str(e))
    try:
        knownHostFile.close()
    except Exception as e:
        logger.error("There was a issue closing connection with local known hosts file:")
        handlingError(str(e))

def editFile(tmpArea, configfile, chgVARDict, chgFILEdict=None):
    '''
    This Function is used to edit a template file

    It takes in a destination directory, a file name within that destination directory
    and a dictionary of variable to change within that file
    '''
    logger.info("Editing " + configfile + " within " + tmpArea)
    for key, value in chgVARDict.items():
        oldConfig = open(tmpArea + "/" + configfile)
        newConfig = open(tmpArea + "/" + configfile + "_new","ab")
        while 1:
            line = oldConfig.readline()
            if not line:
                break
            line = line.replace(str(key),str(value))
            # If the line is = to #JBossConfigDirname= take the Directory location/Filename and store in a Dict
            # Disregard the line from the Temp file
            # This is for JBOSS Config file specific
            if "#JBossConfigDirname=" in line:
                dirFile = line.split("=")[-1]
                # Remove the \n
                dirFile = dirFile.replace("\n","")
                chgFILEdict[configfile + ":" + tmpArea] = dirFile
                continue
            newConfig.write(line)
        newConfig.close()
        new_file_name = configfile + '_new'
        os.rename( os.path.join(tmpArea, new_file_name), os.path.join(tmpArea, configfile))
    if chgFILEdict is not None:
        return chgFILEdict

def copyFiles(configFiles, tmpArea):
    '''
    Copy files from the src destination to a specified destination is the destination
    is not created it creates it on the fly
    '''
    logger.info("Copying contents of " + configFiles + " to " + tmpArea)
    try:
        distutils.dir_util.copy_tree(configFiles, tmpArea)
        return 0
    except Exception as e:
        logger.error("Could not copying contents of " + configFiles + " to " + tmpArea)
        handlingError(str(e))

def getIPSCNodes(nodeIpAddress,cluster):
    '''
    Generate the dict of all Cluster information
    Generate a list of files with the tmpArea and update with information within the Dict
    '''
    mcasts = Multicast.objects.filter(cluster=cluster)
    logger.info("Populating JBOSS COnfig Files")
    chgVARDict = dict([("<BIND_ADR_MGT>", '0.0.0.0')])
    # Add the server information to the dict
    chgVARDict["<BIND_ADR>"] = nodeIpAddress
    chgVARDict["<GRP_BIND_ADR>"] = nodeIpAddress
    #TODO: Need to get these values some way from the database
    for m in mcasts:
        chgVARDict["<MSG_GRP_ADR>"] = m.messaging_group_address
        chgVARDict["<MSG_GRP_PORT>"] = m.messaging_group_port
        chgVARDict["<UDPMLTCST_ADR>"] = m.udp_mcast_address
        chgVARDict["<UDPMULTCST_PORT>"] = m.udp_mcast_port
        chgVARDict["<PINGMULTCSP_ADR>"] = m.mping_mcast_address
        chgVARDict["<PINGMULTCSP_PORT>"] = m.mping_mcast_port
        return chgVARDict

def uploadJbossFiles(nodeIpAddress,serverType,chgFILEdict):
    '''
    Used to get a list of files within a specified Directory
    and upload these files to the appropriate directory on the Service Controller nodes
    '''
    logger.info("Uploading files to Service Controller Node: " + nodeIpAddress)
    sftpPassword = config.get('DMT_SFTP', 'sftpSCPLpassword')

    # Get list of PM Mediation Config files and place in a dict
    templateArea = config.get('DMT_JBOSS', 'templatesJBOSS')
    pmConfigdir = templateArea + "/pm_config"
    remotePmLoc = "/tmp/pm_config"

    pmFileList=os.listdir(pmConfigdir)
    pmDict = {}
    for file in pmFileList:
        pmDict[file + ":" + pmConfigdir] = remotePmLoc + "/" + file

    # Add the two Dicts together for uploading
    jbossFileDict = dict(pmDict.items() + chgFILEdict.items())

    # Upload the edited JBOSS Config files i& PM Mediation files to the Service Controller Nodes
    for key, value in jbossFileDict.items():
        fileArea = key.split(":",1)
        fileName = fileArea[0]
        localArea = fileArea[1]
        remoteDirectory = os.path.dirname(value)
        newfileName = os.path.basename(value)
        # if the node is physical then we need to upload using parimiko sftp
        #user = config.get('DMT_DHCP_SFTP', 'sftpDHCPUser')
        user = config.get('DMT_MGMT', 'mgmtServerUser')
        port = int(config.get('DMT_DHCP_SFTP', 'sftpDHCPPort'))
        key = config.get('DMT_DHCP_SFTP', 'sftpDHCPPrivateKeyFile')
        localFile = localArea + "/" + fileName
        remoteFile = remoteDirectory + "/" + newfileName
        paramikoSftp(nodeIpAddress, user, remoteFile, localFile, port, key)

def runCommands(nodeIpAddress,appType=None,installCommandsFile=None):
    '''
    The runLitpCommands function uses the pyton expect module to run command on the LITP
    management server
    '''
    sftpUser = config.get('DMT_SFTP', 'sftpUser')
    sftpPassword = config.get('DMT_SFTP', 'sftpSCPLpassword')
    sftpPort = config.get('DMT_SFTP', 'sftpPort')
    sftpNode = config.get('DMT_SFTP', 'sftpNode')

    # Set-up a log file to gather the information of the commands ran through pexpect
    LogFileLoc = config.get('DMT_LOG', 'dmtLogFileLoc')
    dmtLogFileLoc = LogFileLoc + "dmt/"
    now = default=datetime.now()
    if not os.path.exists(dmtLogFileLoc):
        os.makedirs(dmtLogFileLoc)
    logFiledate = now.strftime("%Y%m%d-%H%M%S")

    if appType == "LitpAutoInstall":
        cmdFile = installCommandsFile
        installLogFile = dmtLogFileLoc + 'LITP_AUTO_DEPLOY-' + nodeIpAddress + '-' + logFiledate + '.log'
    else:
        templateArea = config.get('DMT_JBOSS', 'templatesJBOSS')
        cmdFile = templateArea + "/jboss_commands"
        installLogFile = dmtLogFileLoc + 'JBOSS_DEPLOY-' + nodeIpAddress + '-' + logFiledate + '.log'

    sshCommand = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no " + sftpUser + "@" + nodeIpAddress

    try:
        child = pexpect.spawn (sshCommand)
        logger.info("Spawned off to LITP MS Server")
    except Exception as e:
        logger.error("There was a problem spawning of to LITP MS: ")
        handlingError(str(e))
    try:
        sshOut = file(installLogFile,'w')
        child.logfile = sshOut
        logger.info("Successfully set up install log file and writing to this file " +str(installLogFile))
    except Exception as e:
        logger.error("There was a problem setting up the install log file: ")
        handlingError(str(e))

    commandList = open(cmdFile,'r')
    child.expect([pexpect.TIMEOUT, '#'], timeout=600)
    try:
        for line in commandList:
            # Ignore lines if beginning with #
            match = re.match('^#', line)
            if match is not None:
                continue
            # split the input command at the :
            cmdComments = line.split(" : ", 3)
            # cmdComments[0] = Command to Run; cmdComments[1] = Expected output ; cmdComments[2] = Successful output; cmdComments[3] = Error Message
            expectOut = cmdComments[1]
            if "\\" in expectOut:
                expectOut = re.sub(r'\\','',expectOut)
            try:
                logger.info(cmdComments[2])
                child.sendline (cmdComments[0])
                child.expect([pexpect.TIMEOUT, expectOut], timeout=180)
                logger.info("Success....")
            except Exception as e:
                logger.error("Running command " + cmdComments[0])
                handlingError(str(e))
    except Exception as e:
        logger.error("There was an issue running through the command template file: "
                +str(cmdFile))
        handlingError(str(e))
    commandList.close()

def buildArtifactList(artifactList, sdpList):
    '''
    The buildArtifactList is used to buid a dict of dict of RPM's and SDP's
    when the user wants to install PM Mediation with arbitrary versions
    of artifcats called be the auto mediation command
    '''
    rpmDict = {}
    sdpDict = {}
    if artifactList != "False":
        artifacts = artifactList
    else:
        artifacts = sdpList

    artifactListupdate = artifacts.split(",")
    try:
        for artifact in artifactListupdate:
            bareName = re.sub(r'\..{3}$','',artifact)
            artifactName = re.sub(r'-[0-9].*','',bareName)
            artifactVersion = re.sub(r'.*-','',bareName)
            if "rpm" in artifact:
                rpmDict[artifactName] = artifactVersion
            else:
                sdpDict[artifactName] = artifactVersion

        if artifactList != "False":
            artifactDict = {'rpm':rpmDict,'sdp':sdpDict}
        elif sdpList != "False":
            artifactDict = {'sdp':sdpDict}
        return artifactDict

    except Exception as e:
        handlingError(str(e))

def handlingErrorReturnCode(error):
    '''
    The handlingErrorReturnCode function is used if an exception is
    thrown, logging the exception and returning a error code
    '''
    logger.error("There was problem, that needs the program to be Exited: " +str(error))
    return 1

def handlingError(error):
    '''
    The handlingError function is a generic fuction called if an exception is
    thrown logging the exception and exiting the script
    '''
    logger.error("There was problem, that needs the program to be Exited: " +str(error))
    raise

def handlingErrorExit(error):
    '''
    The handlingError function is a generic fuction called if an exception is
    thrown logging the exception and exiting the script
    '''
    logger.error("There was problem, that needs the program to be Exited: ")
    raise SystemExit("ERROR MESSAGE: " +str(error))


def getDropList(DropList=None):
    '''
    Populate Web Form with Drop and Litp Sprint Lists for User Selection call be buildClusterArtifact function
    '''
    list = ()
    dropList = ""
    sprintList = ""
    if DropList != "None":
        for drop in DropList:
            list = list + ("[\""+str(drop.name)+"\", \""+str(drop.name)+"\"]",)
            dropList = re.sub(r'\'', '', str(list))
            dropList = eval(dropList)
        return dropList
    else:
        landscapeFiles = os.path.join(config.get('DMT_LANDSCAPE', 'landscapeTemplates'))
        files = sorted(os.listdir(landscapeFiles),reverse=True)
        for file in files:
            if file.startswith("sp"):
                list = list + ("[\""+str(file)+"\", \""+str(file)+"\"]",)
                sprintList = re.sub(r'\'', '', str(list))
                sprintList = eval(sprintList)
        return sprintList

def checkFailedDeploymentsInInstallGroups():
    '''
    checking Failed Deployments in Install Groups
    '''
    maxFailed = int(config.get("DMT", "maxFailed"))
    timeThreshold = datetime.now() - timedelta(hours = maxFailed)
    failedField = ('cluster__id', 'cluster__name', 'group__installGroup',)
    allFailed = ClusterToInstallGroupMapping.objects.only(failedField).values(*failedField).filter(status__status__status__in=['FAILED'], status__status_changed__lt=timeThreshold).order_by('status__status_changed')
    result = {}
    deploymentList = []
    if allFailed:
        for failed in allFailed:
            idleDeployments = {}
            setClusterStatus(failed['cluster__id'],"IDLE")
            logger.info("Changing "+str(failed['cluster__name']) + " status to IDLE")
            idleDeployments['installGroup'] = failed['group__installGroup']
            idleDeployments['name'] = failed['cluster__name']
            idleDeployments['id'] = failed['cluster__id']
            idleDeployments['status'] = "IDLE"
            deploymentList.append(idleDeployments)
        result['Deployments'] = deploymentList
    return result

def setClusterStatus(clusterId, newStatus):
    '''
    Setting Deployment status and status_changed
    '''
    statusType = ""
    try:
        statusType = DeploymentStatusTypes.objects.get(status=newStatus)
    except Exception as e:
        errMsg = "Error when setting the Deployment Status for Deployment ID " + str(clusterId)  + ": this Status " + str(newStatus) + " is invalid, "+ str(e)
        logger.error(errMsg)
        return errMsg
    try:
        update = DeploymentStatus.objects.only('status', 'status_changed').get(cluster__id=clusterId)
        update.status = statusType
        update.status_changed = datetime.now()
        update.save()
    except Exception as e:
        errMsg = "Error when setting the Deployment Status for Deployment: this ID " + str(clusterId)  + " is invalid, " + str(e)
        logger.error(errMsg)
        return errMsg
    return 0

def dmtError(Message, clusterID=None, tmpArea=None, remoteConnection=None):
    if tmpArea != None:
        removeTmpArea(tmpArea)
    if remoteConnection != None:
        closeRemoteConnectionObject(remoteConnection)
    raise CommandError(Message)

def dmtRaiseError(Message):
    logger.error("There was problem, that needs the program to be Exited: ")
    logger.error(str(Message))
    raise

def removeTmpArea(tmpArea):
    '''
    Function used to removed a given directory
    '''
    try:
        if (os.path.exists(tmpArea)):
            shutil.rmtree(tmpArea)
            logger.info("Successfully Removed the " + str(tmpArea))
    except Exception as e:
        raise CommandError("There was a problem removing the tmpArea "  + str(tmpArea))

def removeSedUploadDir(sedUploadDir):
    '''
    Function used to removed a Sed directory on CI Portal
    '''
    try:
        if (os.path.exists(sedUploadDir)):
            shutil.rmtree(sedUploadDir)
            logger.info("Successfully Removed the " + str(sedUploadDir))
    except Exception as e:
        raise CommandError("There was a problem removing the Sed Upload Directory "  + str(sedUploadDir))

def closeRemoteConnectionObject(remoteConnection):
    '''
    Used to close the remote connected used during ssh pexpect
    '''
    try:
        remoteConnection.close()
        logger.info("Successfully closed remote connection")
    except Exception as e:
        raise CommandError("There was a problem closing the remote SSH connection "  + str(tmpArea))

def getVeritasIpAdresses():
    '''
    The getVeritasIpAdresses function get available ip addresses from a specified range
    that do not exist in the database a passes these values back to the user
    '''
    if IpRangeItem.objects.filter(ip_range_item="PDU-Priv_veritasIP").exists():
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv_veritasIP")
    else:
        logger.error("There was an issue generating an IP address for the Veritas Cluster")
        return 1
    if IpRange.objects.filter(ip_range_item=ipRangeItemObj).exists():
        ipRange = IpRange.objects.filter(ip_range_item=ipRangeItemObj).order_by('start_ip')
    csgAddress = None
    gcoAddress = None
    try:
        for ip in ipRange:
            range = iptools.IpRange(ip.start_ip,ip.end_ip)
            try:
                for ipCheck in range:
                    if IpAddress.objects.filter(address=ipCheck).exists():
                        continue
                    elif csgAddress is None:
                        csgAddress = ipCheck
                        csgBitMask = ip.bitmask
                        continue
                    elif gcoAddress is None:
                        gcoAddress = ipCheck
                        gcoBitMask = ip.bitmask
                        continue
                if csgAddress is None or gcoAddress is None:
                    continue
                else:
                    return csgAddress,csgBitMask,gcoAddress,gcoBitMask
            except Exception as e:
                logger.error("No ip addresses found in range for veritas cluster")
    except Exception as e:
        logger.error("There was an issue generating Veritas IP addresses, Exception: " +str(e))
        return 1

def getSubnetDetails(type,clusterId=None):
    '''
    To get the subnet info for a specific range
    '''
    if type == "internal":
        if IpRangeItem.objects.filter(ip_range_item="PDU-Priv-2_virtualImageInternal").exists():
            ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv-2_virtualImageInternal")
        else:
            logger.error("There was an issue generating an IP address for the \"PDU-Priv-2_virtualImageInternal\"")
            return 1
    elif type == "jgroup":
        if IpRangeItem.objects.filter(ip_range_item="PDU-Priv_virtualImageInternalJgroup").exists():
            ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv_virtualImageInternalJgroup")
        else:
            logger.error("There was an issue generating an IP address for the \"PDU-Priv_virtualImageInternalJgroup\"")
            return 1
    elif type == "internalIPv6":
        if IpRangeItem.objects.filter(ip_range_item="clusterId_"+str(clusterId)).exists():
            ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="clusterId_"+str(clusterId))
        else:
            logger.error("There was an issue generating an IP address for the clusterId_\" " + str(clusterId) + "\"")
            return 1
    else:
        logger.error("There was an issue generating an IP address for the Service Group Instance")
        return 1

    ipRangeObj = IpRange.objects.get(ip_range_item=ipRangeItemObj)
    ipInfo = IPNetwork(ipRangeObj.start_ip + "/" + str(ipRangeObj.bitmask))
    subnet = str(ipInfo.network) + "/" + str(ipInfo.prefixlen)
    return subnet


def getServiceGroupInstanceIpAddress(clusterId,internal=False,type=None,allIPs=None):
    '''
    The getServiceGroupInstanceIpAddress function is used to get an IP address for the Service Group Instance
    within a specified range that is not used and does not exist within the db
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        logger.error("No such cluster: " + str(clusterId) + ", Exception :  " + str(e))
        return 1
    if internal:
        if IpRangeItem.objects.filter(ip_range_item="PDU-Priv-2_virtualImageInternal").exists():
            ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv-2_virtualImageInternal")
        else:
            logger.error("There was an issue generating an IP address for the \"PDU-Priv-2_virtualImageInternal\"")
            return 1
    elif type == "multicast":
        if IpRangeItem.objects.filter(ip_range_item="PDU-Priv_nodeInternalJgroup").exists():
            ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv_nodeInternalJgroup")
        else:
            logger.error("There was an issue generating an IP address for the \"PDU-Priv_nodeInternalJgroup\"")
            return 1
    elif type == "jgroup":
        if IpRangeItem.objects.filter(ip_range_item="PDU-Priv_virtualImageInternalJgroup").exists():
            ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv_virtualImageInternalJgroup")
        else:
            logger.error("There was an issue generating an IP address for the \"PDU-Priv_virtualImageInternalJgroup\"")
            return 1
    elif IpRangeItem.objects.filter(ip_range_item="serviceUnit").exists():
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="serviceUnit")
    elif IpRangeItem.objects.filter(ip_range_item="PDU-Priv_veritasIP").exists():
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv_veritasIP")
    else:
        logger.error("There was an issue generating an IP address for the Service Group Instance")
        return 1

    if IpRange.objects.filter(ip_range_item=ipRangeItemObj).exists():
        ipRangeValues = ("start_ip", "end_ip", "gateway", "bitmask")
        ipRange = IpRange.objects.filter(ip_range_item=ipRangeItemObj).only(ipRangeValues).values(*ipRangeValues).order_by('start_ip')
    try:
        if allIPs is not None:
            allIPs=allIPs
        else:
            allIPs=getAllIPsInCluster(clusterObj)
        allAddresses = IpAddress.objects.all().only("address").values_list("address", flat = True)
        for ip in ipRange:
            ipRangeList = iptools.IpRange(ip["start_ip"],ip["end_ip"])
            try:
                for ipCheck in ipRangeList:
                    if internal:
                        if ipCheck in allIPs:
                            continue
                        else:
                            instanceIpAddress = ipCheck
                            instanceGateway = ip["gateway"]
                            instanceBitmask = ip["bitmask"]
                            break
                    elif type == "multicast":
                        if ipCheck in allAddresses:
                            continue
                        else:
                            instanceIpAddress = ipCheck
                            instanceGateway = ip["gateway"]
                            instanceBitmask = ip["bitmask"]
                            break
                    else:
                        if ipCheck in allAddresses:
                            continue
                        else:
                            instanceIpAddress = ipCheck
                            instanceGateway = ip["gateway"]
                            instanceBitmask = ip["bitmask"]
                            break
                return instanceGateway,instanceIpAddress,instanceBitmask
            except Exception as e:
                logger.error("No ip addresses found in range Exception : " +str(e))
    except Exception as e:
        logger.error("There was an issue generating an IP address for the Service Group Instance: " +str(e))
        return 1

def checkServiceGroupInstanceIpAddress(checkIp):
    '''
    The checkServiceGroupInstanceIpAddress function is used to check is a given IP in a certain range
    '''
    if IpRangeItem.objects.filter(ip_range_item="PDU-Priv_veritasIP").exists():
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="PDU-Priv_veritasIP")
    else:
        logger.error("There was an issue checking an IP address for the Service Group Instance")
        return 1

    if IpRange.objects.filter(ip_range_item=ipRangeItemObj).exists():
        ipRange = IpRange.objects.filter(ip_range_item=ipRangeItemObj).order_by('start_ip')
    try:
        for ip in ipRange:
            ipRangeList = iptools.IpRange(ip.start_ip,ip.end_ip)
            for ipCheck in ipRangeList:
                if checkIp == ipCheck:
                    return "found"
                else:
                    returnFlag = "notfound"
        return returnFlag
    except Exception as e:
        logger.error("There was an issue checking the IP address for the Service Group Instance: " +str(e))
        return 1

def getMulticastIpAddress(type):
    '''
    The getServiceGroupInstanceIpAddress function is used to get an IP address for the Service Group Instance
    within a specified range that is not used and does not exist within the db
    '''
    #mcastIPInformation has the form mcaststart:[mcastEnd]
    if type is "defaultAddress":
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="defaultMcastRange")
    elif type is "messagingAddress":
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="messagingMcastRange")
    elif type is "udpAddress":
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="udpMcastRange")
    elif type is "mpingAddress":
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item="mpingMcastRange")
    else:
        logger.error("There was an issue generating an IP address for Multicast Address")
        return 1
    if IpRange.objects.filter(ip_range_item=ipRangeItemObj).exists():
        ipRange = IpRange.objects.filter(ip_range_item=ipRangeItemObj).order_by('start_ip')
    address = None
    try:
        for ip in ipRange:
            ipRangeList = iptools.IpRange(ip.start_ip,ip.end_ip)
            try:
                for ipCheck in ipRangeList:
                    if IpAddress.objects.filter(address=ipCheck).exists():
                        continue
                    elif address is None:
                        address = ipCheck
                        break
                if address is None:
                    continue
                else:
                    return address
            except Exception as e:
                logger.error("No Mcast ip addresses found for mcast type " + str(type) + ", exception : "  + str(e))
    except Exception as e:
        logger.error("There was an issue generating Mcast IP addresses: " +str(e))
        return 1

def getHostProperties(clusterId):
    '''
    Returns details about cluster
    '''
    retString = ""
    buildDir = ""
    clusterObj = dmt.models.Cluster.objects.get(id=clusterId)
    try:
        logger.info("Running Config Build.....")
        webRun = "NO"
        installType = "webRun"
        buildDir,buildName = dmt.buildconfig.generateConfigFile(clusterId, 'hostproperties', None, webRun, installType)
        newCompleteBuildName = os.path.join(buildDir,buildName)
        newCompleteBuildNameZipped = os.path.join(buildDir, clusterObj.name + "-config.cfg")
        logger.info("Renaming........")
        rename = os.rename(newCompleteBuildName,newCompleteBuildNameZipped)
        logger.info("Downloading.......")
        retString=newCompleteBuildNameZipped
        logger.info("Removing " + str(buildDir))
    except Exception as e:
        logger.error("Error getting host information: " +str(e))
    return retString,buildDir

def getIPinformation(IP):
    '''
    Returns information associated with IP
    '''
    ret={'ip':IP,'mac':"---",'server':"---",'type':"---",'hwtype':"---",'serviceinst':"---",'cluster':"---"}
    try:
        ipObj= IpAddress.objects.get(address=IP)
    except Exception as e:
        logger.error("IP doesn't exist " +str(e))
    try:
        ret['mac']=ipObj.nic.mac_address
    except:
        logger.info("No mac address assoicated with IP")
    try:
        ret['server']=ipObj.nic.server.hostname
    except:
        logger.info("No mac address assoicated with IP")
    try:
        ret['hwtype']=ipObj.nic.server.hardware_type
    except:
        logger.info("No hwtype assoicated with IP")
    try:
        siObj=ServiceGroupInstance.objects.get(Service_Instance_IP=IP)
        ret['serviceinst']=siObj.service_group.name
        ret['cluster']=siObj.service_group.service_cluster.cluster.name
    except:
        logger.info("No Service Instance assoicated with IP")
    return ret

def buildUpTAFHostPropertiesNodesList(clusterId):
    '''
    The buildUpTAFHostPropertiesNodesList function builds up the TAF Host poperties File for peer nodes including MS
    '''
    propertiesTemplate = config.get('DMT_HOSTPROPERTIES', 'hostPropertiesTemplate')
    nodeList = []
    peerNodeType = "<NODE_TYPE>"
    peerNodeIP = "<NODE_IP>"
    mgmtServerName = "<MS_NAME>"
    mgmtServerIP = "<MS_NODE_IP>"
    try:
        cluster = Cluster.objects.get(id=clusterId)
        mgmtServerIPQuery = IpAddress.objects.get(nic__server_id=cluster.management_server.server_id, ipType="host").address
    except Exception as e:
        return HttpResponse("Error: " +str(e))
    clusterServers = ClusterServer.objects.filter(cluster_id=clusterId)
    for clusterServer in clusterServers:
        if not clusterServer.active:
            continue
        hostpropertiesFH = io.open(propertiesTemplate,'r')
        try:
            clusterServerIP = IpAddress.objects.get(nic__server_id=clusterServer.server_id, ipType="other").address
        except Exception as e:
            return HttpResponse("Error: " +str(e))
            hostpropertiesFH.close()
        try:
            for line in hostpropertiesFH:
                if peerNodeType in line:
                    line = re.sub(peerNodeType, clusterServer.node_type.lower(), str(line))
                if peerNodeIP in line:
                    line = re.sub(peerNodeIP, clusterServerIP, str(line))
                if mgmtServerName in line:
                    line = re.sub(mgmtServerName, "ms1", str(line))
                if mgmtServerIP in line:
                     line = re.sub(mgmtServerIP, mgmtServerIPQuery, str(line))
                if line not in nodeList:
                    nodeList.append(line)
        except Exception as e:
            logger.error("Error in building List1: " +str(e))
            hostpropertiesFH.close()
        hostpropertiesFH.close()
    propertiesList = buildUpTAFHostPropertiesMulticastList(clusterId, nodeList)
    return propertiesList

def buildUpTAFHostPropertiesMulticastList(clusterId, nodeList):
    '''
    The buildUpTAFHostPropertiesMulticastList builds up host properties for multicast info
    '''
    serviceClusters = ServicesCluster.objects.filter(cluster_id=clusterId, cluster_type="JBOSS Cluster")
    multicastList = []
    propertiesList = []
    jbossInstanceName = "<JBOSS_NAME>"
    jbossInstanceServiceUnitIP = "<SU0_IP1>"
    try:
        for serviceCluster in serviceClusters:
            serviceInstanceSU0 = ServiceGroupInstance.objects.filter(service_group__service_cluster=serviceCluster)[0].ipMap
            try:
                for item in nodeList:
                    if jbossInstanceName in item:
                        item = re.sub(jbossInstanceName, serviceCluster.name, str(item))
                    if jbossInstanceServiceUnitIP in item:
                        item = re.sub(jbossInstanceServiceUnitIP, str(serviceInstanceSU0), str(item))
                    if item not in multicastList:
                        multicastList.append(item)
            except Exception as e:
                logger.error("Error: " +str(e))
    except Exception as e:
        logger.error("Error: " +str(e))

    propertiesList = buildUpTAFHostPropertiesServiceGroup(clusterId, multicastList)
    return propertiesList

def buildUpTAFHostPropertiesServiceGroup(clusterId, nodeList):
    '''
    The buildUpTAFHostPropertiesServiceGroup returns the LSB Service group data to the host.properties
    '''
    serviceGroupName = "<SERVICE_GROUP>"
    serviceGroupServiceUnitIP = "<SERVICE_GROUP_SU0_IP1>"
    serviceClusterList  = []
    propertiesList = []
    if ServicesCluster.objects.filter(cluster_id=clusterId, cluster_type="Service Cluster", name="LSB Service Cluster").exists():
        serviceCluster = ServicesCluster.objects.get(cluster_id=clusterId, cluster_type="Service Cluster", name="LSB Service Cluster")
        if ServiceGroup.objects.filter(service_cluster=serviceCluster).exists():
            serviceGroupObj = ServiceGroup.objects.filter(service_cluster=serviceCluster)
            for serviceGroup in serviceGroupObj:
                serviceClusterSU0 = ServiceGroupInstance.objects.filter(service_group=serviceGroup)[0].ipMap
                try:
                    for item in nodeList:
                        if serviceGroupName in item:
                            item = re.sub(serviceGroupName, serviceGroup.name, str(item))
                        if serviceGroupServiceUnitIP in item:
                            item = re.sub(serviceGroupServiceUnitIP, str(serviceClusterSU0), str(item))
                        if item not in serviceClusterList:
                            serviceClusterList.append(item)
                except Exception as e:
                    logger.error("Error: Build Service Cluster Details List" +str(e))
    #remove items that are still in template form ie: not supported tagged lines etc
    templateReg = re.compile('(<[A-Z0-9]*_)*>')
    for item in serviceClusterList:
        if not templateReg.findall(item):
            propertiesList.append(item)
    return propertiesList

def buildUpTAFHostPropertiesUsingCITERestCall(citeHostPropertiesFile, propertiesList):
    '''
    The buildUpTAFHostPropertiesUsingCITERestCall function calls the CITE Rest and return host properities
    for deployments that are not stored in the CIFWK DB
    '''
    citeRestCall = config.get('DMT_HOSTPROPERTIES', 'citeRestCall')
    try:
        for file in citeHostPropertiesFile:
            citeRestCall += ":" +str(file)
    except Exception as e:
        return HttpResponse("Error: Building Up CITE REST Call data " +str(e))

    try:
        command = 'wget -q -O - --no-check-certificate --post-data="" ' +str(citeRestCall)
        runCiteRestCall = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd="/tmp")
        runCiteRestCall.wait()
        citeRestCallReturnedList = runCiteRestCall.stdout.readlines()[0].split('<br>')
    except Exception as e:
        return HttpResponse("Error: Building Up CITE REST Call host property output; " +str(e))

    for item in citeRestCallReturnedList:
        if item+"\n" not in propertiesList:
            propertiesList.append(item+"\n")

    propertiesList.sort()
    return propertiesList

def buildTAFHostPropertiesAndReturnInJSON(clusterId,tunnel=False,tunnelNetsim=False,allNetsims=False,iloDetails=False):
    '''
    The buildTAFHostPropertiesAndReturnInJSON is called by the views function generateTAFHostPropertiesJSON
    and returns the TAF host properties in json format
    '''
    mgtSerDictDefault = {"username": "root", "password": config.get('DMT_AUTODEPLOY', 'masterPasswordCloudMS1'), "type": "admin"}
    clsSerDictDefault  = {"username": "root", "password": config.get('DMT_AUTODEPLOY', 'ServContNodePassword'), "type": "admin"}
    svcSerDictDefault  = {"username": "litp-admin", "password": config.get('DMT_AUTODEPLOY', 'svcNodePassword'), "type": "admin"}
    rootSerDictDefault  = {"username": "root", "password": config.get('DMT_AUTODEPLOY', 'svcNodePassword'), "type": "admin"}
    sshPortDict = {"ssh":22}
    managementServerDict = {}
    virtualManagementServerDict = {}
    jsonReturn = []
    mgmtServCreds = []
    vMgmtServCreds = []
    clusterServCreds = []
    mgmtServCreds = managementServerIP = clusterServCreds = clusterServerIP = vmInfo = tunnelCount = netsimDict = virtualImageInfo = []
    managementServerIPv6 = None
    vMgmtServCreds = []
    jbossDict = {}

    if clusterId == "000":
        return jsonReturn
    try:
        try:
            virtualImageInfo = clusterDetailsVirtualimagedata(clusterId)
        except Exception as e:
            errorMsg ="Issue getting Deployment Details Virtual Image Data for Deployment Id (" + str(clusterId) + "), Error: " +str(e)
            logger.error(errorMsg)
            raise Exception(errorMsg)
        clusterObj = Cluster.objects.get(id=clusterId)
        msHostname = "ms1"
        if virtualImageInfo == []:
            if IpAddress.objects.filter(nic__server__id=clusterObj.management_server.server.id, ipType="host").exists():
                try:
                    mgmtServCreds = getMgmtServerCredentials(clusterObj.management_server.id)
                except Exception as e:
                    errorMsg = "Issue getting Credentials for Management Server " + str(clusterObj.management_server.server) + " , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)
                try:
                    managementServerIP = IpAddress.objects.get(nic__server__id=clusterObj.management_server.server.id, ipType="host").address
                except Exception as e:
                    errorMsg = "Issue getting IpAddress for Management Server " + str(clusterObj.management_server.server) + " , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)
                if IpAddress.objects.filter(nic__server__id=clusterObj.management_server.server.id,ipType="ipv6_host").exists():
                    managementServerIPv6 = IpAddress.objects.get(nic__server__id=clusterObj.management_server.server.id, ipType="ipv6_host").ipv6_address

                managementServerDict["ports"] = sshPortDict
                if not mgmtServCreds:
                    managementServerDict["users"] = [mgtSerDictDefault]
                else:
                    managementServerDict["users"] = mgmtServCreds
                managementServerDict["type"] = "ms"
                managementServerDict["ip"] = str(managementServerIP)
                managementServerDict["ipv6"] = str(managementServerIPv6)
                managementServerDict["hostname"] = str(msHostname)
                if tunnelNetsim:
                    try:
                        netsimDict,tunnelCount = getNetsim(clusterId,True,allNetsims)
                    except Exception as e:
                        errorMsg = "Issue getting Netsim for Deployment Id (" + str(clusterId) + "), Error: " +str(e)
                        logger.error(errorMsg)
                        raise Exception(errorMsg)
                    managementServerDict["nodes"] = netsimDict
                jsonReturn.append(dict(managementServerDict))
                #VMS
                if VirtualManagementServer.objects.filter(mgtServer_id=clusterObj.management_server_id).exists():
                    virtualMgtObj = VirtualManagementServer.objects.get(mgtServer_id=clusterObj.management_server_id)
                    if IpAddress.objects.filter(nic__server__id=virtualMgtObj.server_id, ipType="virtualMShost").exists():
                        try:
                            vMgmtServCreds = getVMgmtServerCredentials(virtualMgtObj.id)
                        except Exception as e:
                            errorMsg = "Issue getting Credentials for Virtual Management Server " + str(clusterObj.management_server) + " , Error: " +str(e)
                            logger.error(errorMsg)
                            raise Exception(errorMsg)
                        virtualManagementServerIP = IpAddress.objects.get(nic__server__id=virtualMgtObj.server_id, ipType="virtualMShost").address
                        virtualManagementServerDict["ports"] = sshPortDict
                        if not vMgmtServCreds:
                            virtualManagementServerDict["users"] = [mgtSerDictDefault]
                        else:
                            virtualManagementServerDict["users"] = vMgmtServCreds
                        virtualManagementServerDict["type"] = "vms"
                        virtualManagementServerDict["ip"] = str(virtualManagementServerIP)
                        virtualManagementServerDict["hostname"] = "vms1"
                        jsonReturn.append(dict(virtualManagementServerDict))
            clusterSC1ServerDict = {}
            otherServerDict = {}
            try:
                jbossDict = getJbossJson(clusterId,tunnel)
            except Exception as e:
                errorMsg = "Issue getting Jboss for Deployment Id (" + str(clusterId) + "), Error: " +str(e)
                logger.error(errorMsg)
                raise Exception(errorMsg)
            clusterServers = ClusterServer.objects.filter(cluster_id=clusterId)
            for clusterServer in clusterServers:
                if not clusterServer.active:
                    continue
                try:
                    clusterServCreds = getClusterServerCredentials(clusterServer.id)
                except Exception as e:
                    errorMsg = "Issue getting Credentials for Deployment Server " + str(clusterServer.server) + " , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)
                if "SC-1" in clusterServer.node_type:
                    try:
                        clusterServerIP = str(IpAddress.objects.get(nic__server_id=clusterServer.server_id, ipType="other").address)
                    except Exception as e:
                        errorMsg = "Issue getting IpAddress for Deployment Server " + str(clusterServer.server) + " , Error: " +str(e)
                        logger.error(errorMsg)
                        raise Exception(errorMsg)
                    serverName =  str(re.sub(r"-", "", clusterServer.node_type.lower()))
                    clusterSC1ServerDict["ports"] = sshPortDict
                    clusterSC1ServerDict["nodes"] = jbossDict
                    if not clusterServCreds:
                        clusterSC1ServerDict["users"] = [clsSerDictDefault]
                    else:
                        clusterSC1ServerDict["users"] = clusterServCreds
                    clusterSC1ServerDict["type"] = serverName
                    clusterSC1ServerDict["ip"] = clusterServerIP
                    clusterSC1ServerDict["hostname"] = serverName
                    jsonReturn.append(dict(clusterSC1ServerDict))
                    continue
                else:
                    try:
                        clusterServerIP = str(IpAddress.objects.get(nic__server_id=clusterServer.server_id, ipType="other").address)
                    except Exception as e:
                        errorMsg = "Issue getting IpAddress for Deployment Server " + str(clusterServer.server) + " , Error: " +str(e)
                        logger.error(errorMsg)
                        raise Exception(errorMsg)
                    serverName =  str(re.sub(r"-", "", clusterServer.node_type.lower()))
                    if str(serverName.lower()) != "netsim":
                        otherServerDict["ports"] = sshPortDict
                        if not clusterServCreds:
                            otherServerDict["users"] = [clsSerDictDefault]
                        else:
                            otherServerDict["users"] = clusterServCreds
                        otherServerDict["type"] = serverName
                        otherServerDict["ip"] = clusterServerIP
                        otherServerDict["hostname"] = serverName
                        jsonReturn.append(dict(otherServerDict))
                        continue
        else:
            tunnelCount = 1
            if IpAddress.objects.filter(nic__server__id=clusterObj.management_server.server.id, ipType="host").exists():
                try:
                    mgmtServCreds = getMgmtServerCredentials(clusterObj.management_server.id)
                except Exception as e:
                    errorMsg = "Issue getting Credentials for Management Server " + str(clusterObj.management_server.server) + " , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)
                try:
                    managementServerIP = IpAddress.objects.get(nic__server__id=clusterObj.management_server.server.id, ipType="host").address
                except Exception as e:
                    errorMsg = "Issue getting IpAddress for Management Server " + str(clusterObj.management_server.server) + " , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)
                if IpAddress.objects.filter(nic__server__id=clusterObj.management_server.server.id,ipType="ipv6_host").exists():
                    managementServerIPv6 = IpAddress.objects.get(nic__server__id=clusterObj.management_server.server.id, ipType="ipv6_host").ipv6_address
                try:
                    mgmtIloInfo = getIloInfo(clusterObj.management_server.server.id, str(msHostname))
                except Exception as e:
                    errorMsg = "Issue getting Ilo Info for Management Server " + str(clusterObj.management_server.server) + " , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)

                managementServerDict["ports"] = sshPortDict
                if not mgmtServCreds:
                    managementServerDict["users"] = [mgtSerDictDefault]
                else:
                    managementServerDict["users"] = mgmtServCreds
                managementServerDict["type"] = "ms"
                if iloDetails:
                    managementServerDict["iloInfo"] = mgmtIloInfo
                managementServerDict["ip"] = str(managementServerIP)
                managementServerDict["ipv6"] = str(managementServerIPv6)
                managementServerDict["hostname"] = str(msHostname)
                if tunnelNetsim:
                    try:
                        netsimDict,tunnelCount = getNetsim(clusterId,True,allNetsims)
                    except Exception as e:
                        errorMsg = "Issue getting Netsim for Deployment Id (" + str(clusterId) + "), Error: " +str(e)
                        logger.error(errorMsg)
                        raise Exception(errorMsg)
                    managementServerDict["nodes"] = netsimDict
                jsonReturn.append(dict(managementServerDict))
            clusterSC1ServerDict = {}
            otherServerDict = {}

            clusterServers = ClusterServer.objects.filter(cluster_id=clusterId).only('id','server_id','cluster_id','node_type','active','server__hostname').values('id','server_id','cluster_id','node_type','active','server__hostname')

            try:
                clusterServersInterfaces = getInterfaces(clusterServers)
            except Exception as e:
                errorMsg = "Issue getting Interfaces for Deployment Servers, Error: " +str(e)
                logger.error(errorMsg)
                raise Exception(errorMsg)

            try:
                clusterServersCredentials = getManyClusterServerCredentials(clusterServers)
            except Exception as e:
                errorMsg = "Issue getting Credentials for Deployment Server, Error: " +str(e)
                logger.error(errorMsg)
                raise Exception(errorMsg)

            for clusterServer in clusterServers:
                if not clusterServer['active']:
                    continue
                serverName =  str(re.sub(r"-", "", clusterServer['node_type'].lower()))
                if serverName == 'netsim':
                    continue
                clusterServCreds = clusterServersCredentials[clusterServer['id']]
                interfaces = clusterServersInterfaces[clusterServer['server_id']]
                otherServerDict["ports"] = sshPortDict

                try:
                    clusterServerIloInfo = getIloInfo(clusterServer['server_id'], serverName)
                except Exception as e:
                    errorMsg = "Issue getting Ilo Info for Cluster Server " + str(clusterServer) + " , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)

                try:
                    vmInfo,tunnelCount = getVMInfo(clusterId,tunnel,tunnelCount,clusterServer['node_type'])
                except Exception as e:
                    errorMsg = "Issue getting VMInfo for Deployment Id (" + str(clusterId) + ") with Node Type " + str(clusterServer['node_type']) +" , Error: " +str(e)
                    logger.error(errorMsg)
                    raise Exception(errorMsg)
                otherServerDict["nodes"] = vmInfo
                if not clusterServCreds:
                    defaultUsers = []
                    defaultUsers.append(svcSerDictDefault)
                    defaultUsers.append(rootSerDictDefault)
                    otherServerDict["users"] = defaultUsers
                else:
                    otherServerDict["users"] = clusterServCreds
                otherServerDict["type"] = serverName
                otherServerDict["interfaces"] = interfaces
                if iloDetails:
                    otherServerDict["iloInfo"] = clusterServerIloInfo
                if "workload" in serverName:
                    otherServerDict["hostname"] = clusterServer['server__hostname']
                else:
                    otherServerDict["hostname"] = serverName
                jsonReturn.append(dict(otherServerDict))

        if not tunnelNetsim:
            try:
                netsimList = getNetsim(clusterId,tunnelNetsim,allNetsims)
            except Exception as e:
                errorMsg = "Issue getting Netsim for Deployment Id (" + str(clusterId) + "), Error: " +str(e)
                logger.error(errorMsg)
                raise Exception(errorMsg)
            for netsimDict in netsimList:
                jsonReturn.append(netsimDict)

        if LVSRouterVip.objects.filter(cluster_id=clusterObj.id).exists():
            userList = []
            userList.append(svcSerDictDefault)
            type = "LVS_Router"
            lvsRouterVipList = ['PM', 'FM', 'CM', 'STR', 'SCP', "ESN", "ASR", "EBS", "EBA", "MSOSSFM",
                                'SVC_Storage', 'SCP_Storage', 'EVT_Storage', 'STR_Storage', 'ESN_Storage' 'ASR_Storage', 'EBS_Storage', 'EBA_Storage']

            fields = ("pm_internal__address", "pm_external__address",
                    "fm_internal__address", "fm_external__address", "fm_internal_ipv6__ipv6_address", "fm_external_ipv6__ipv6_address",
                    "cm_internal__address", "cm_external__address", "cm_internal_ipv6__ipv6_address", "cm_external_ipv6__ipv6_address",
                    "svc_pm_storage__address", "svc_fm_storage__address", "svc_cm_storage__address",
                    "svc_storage_internal__address", "svc_storage__address",
                    "scp_scp_internal__address", "scp_scp_external__address", "scp_scp_internal_ipv6__ipv6_address", "scp_scp_external_ipv6__ipv6_address",
                    "scp_scp_storage__address", "scp_storage_internal__address", "scp_storage__address",
                    "evt_storage_internal__address", "evt_storage__address",
                    "str_str_if", "str_internal__address", "str_str_internal_2__address", "str_str_internal_3__address",
                    "str_external__address", "str_str_external_2__address", "str_str_external_3__address",
                    "str_str_internal_ipv6__ipv6_address", "str_str_internal_ipv6_2__ipv6_address", "str_str_internal_ipv6_3__ipv6_address",
                    "str_external_ipv6__ipv6_address", "str_str_external_ipv6_2__ipv6_address", "str_str_external_ipv6_3__ipv6_address",
                    "str_str_storage__address", "str_storage_internal__address", "str_storage__address",
                    "esn_str_if", "esn_str_internal__address", "esn_str_external__address", "esn_str_internal_ipv6__ipv6_address",
                    "esn_str_external_ipv6__ipv6_address", "esn_str_storage__address", "esn_storage_internal__address",
                    "ebs_storage_internal__address", "ebs_storage__address", "asr_storage_internal__address", "asr_asr_external__address",
                    "asr_asr_internal__address", "asr_asr_external_ipv6__ipv6_address", "asr_storage__address","asr_asr_storage__address",
                    "eba_storage_internal__address", "eba_storage__address",
                    "msossfm_internal__address", "msossfm_external__address", "msossfm_internal_ipv6__ipv6_address", "msossfm_external_ipv6__ipv6_address")
            lvsRouterVipObj = LVSRouterVip.objects.only(fields).values(*fields).get(cluster_id=clusterObj.id)
            for key in lvsRouterVipList:
                lvsRouterVipDict = {}
                lvsRouterVipDict["hostname"] = type+"_"+key
                if key == 'PM':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["pm_external__address"],
                                                                 lvsRouterVipObj["pm_internal__address"], None, None,
                                                                 lvsRouterVipObj["svc_pm_storage__address"])
                elif key == 'FM':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["fm_external__address"],
                                                                 lvsRouterVipObj["fm_internal__address"],
                                                                 lvsRouterVipObj["fm_external_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["fm_internal_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["svc_fm_storage__address"])
                elif key == 'CM':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["cm_external__address"],
                                                                 lvsRouterVipObj["cm_internal__address"],
                                                                 lvsRouterVipObj["cm_external_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["cm_internal_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["svc_cm_storage__address"])
                elif key == 'STR':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["str_external__address"],
                                                                 lvsRouterVipObj["str_internal__address"],
                                                                 lvsRouterVipObj["str_external_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["str_str_internal_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["str_str_storage__address"],
                                                                 lvsRouterVipObj["str_str_external_3__address"],
                                                                 lvsRouterVipObj["str_str_external_3__address"],
                                                                 lvsRouterVipObj["str_str_internal_2__address"],
                                                                 lvsRouterVipObj["str_str_internal_3__address"],
                                                                 lvsRouterVipObj["str_str_external_ipv6_2__ipv6_address"],
                                                                 lvsRouterVipObj["str_str_external_ipv6_3__ipv6_address"],
                                                                 lvsRouterVipObj["str_str_internal_ipv6_2__ipv6_address"],
                                                                 lvsRouterVipObj["str_str_internal_ipv6_3__ipv6_address"])
                elif key == 'SCP':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["scp_scp_external__address"],
                                                                 lvsRouterVipObj["scp_scp_internal__address"],
                                                                 lvsRouterVipObj["scp_scp_external_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["scp_scp_internal_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["scp_scp_storage__address"])
                elif key == 'ESN':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["esn_str_external__address"],
                                                                 lvsRouterVipObj["esn_str_internal__address"],
                                                                 lvsRouterVipObj["esn_str_external_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["esn_str_internal_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["esn_str_storage__address"])
                elif key == 'EBS':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["ebs_storage_internal__address"],
                                                                 lvsRouterVipObj["ebs_storage__address"])
                elif key == 'ASR':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["asr_storage_internal__address"],
                                                                 lvsRouterVipObj["asr_asr_external__address"],
                                                                 lvsRouterVipObj["asr_asr_internal__address"],
                                                                 lvsRouterVipObj["asr_asr_external_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["asr_asr_storage__address"],
                                                                 lvsRouterVipObj["asr_storage__address"])
                elif key == 'EBA':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["eba_storage_internal__address"],
                                                                 lvsRouterVipObj["eba_storage__address"])
                elif key == 'MSOSSFM':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(lvsRouterVipObj["msossfm_external__address"],
                                                                 lvsRouterVipObj["msossfm_internal__address"],
                                                                 lvsRouterVipObj["msossfm_external_ipv6__ipv6_address"],
                                                                 lvsRouterVipObj["msossfm_internal_ipv6__ipv6_address"])
                elif key == 'SVC_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None,lvsRouterVipObj["svc_storage_internal__address"],None,None,lvsRouterVipObj["svc_storage__address"])
                elif key == 'SCP_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None,lvsRouterVipObj["scp_storage_internal__address"], None,None,lvsRouterVipObj["scp_storage__address"])
                elif key == 'EVT_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None,lvsRouterVipObj["evt_storage_internal__address"], None,None,lvsRouterVipObj["evt_storage__address"])
                elif key == 'STR_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None, lvsRouterVipObj["str_storage_internal__address"], None,None, lvsRouterVipObj["str_storage__address"])
                elif key == 'ESN_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None, lvsRouterVipObj["esn_storage_internal__address"], None,None,None)
                elif key == 'EBS_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None, lvsRouterVipObj["ebs_storage_internal__address"], None,None,lvsRouterVipObj["ebs_storage__address"])
                elif key == 'ASR_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None, lvsRouterVipObj["asr_storage_internal__address"], None,None,lvsRouterVipObj["asr_storage__address"])
                elif key == 'EBA_Storage':
                    lvsRouterVipData = getLVSRouterVIPInterfaces(None, lvsRouterVipObj["eba_storage_internal__address"], None,None,lvsRouterVipObj["eba_storage__address"])

                lvsRouterVipDict["interfaces"] = lvsRouterVipData
                lvsRouterVipDict["ports"] = sshPortDict
                lvsRouterVipDict["type"] = type
                lvsRouterVipDict["users"] = userList
                jsonReturn.append(lvsRouterVipDict)

        sanDict = getSANDetails(clusterObj.id,sshPortDict)
        if sanDict:
            jsonReturn.append(sanDict)

    except Exception as e:
        errorMsg = "Issue getting the Host Properties for this Deployment Id (" + str(clusterId) + "), Error: " +str(e)
        logger.error(errorMsg)
        raise Exception(errorMsg)

    return jsonReturn

def getSANDetails(clusterId,sshPortDict):
    '''
    The getSANDetails function returns the NAS defined network details in JSON format for a given cluster id
    '''
    sanDict = {}
    userList = []
    userDict = {}
    try:
        clusterToStorageObj = ClusterToStorageMapping.objects.filter(cluster_id=clusterId)
        for clusterToStorage in clusterToStorageObj:
            storageObj = Storage.objects.get(id=clusterToStorage.storage_id)
            storageIPMapping = StorageIPMapping.objects.get(storage=storageObj,ipnumber="1")
            sanDict["hostname"] = storageObj.hostname
            sanDict["ports"] = sshPortDict
            sanDict["ip"] = storageIPMapping.ipaddr.address
            sanDict["type"] = "san"
            userDict["username"] = storageObj.credentials.username
            userDict["password"] = storageObj.credentials.password
            userDict["type"] = "admin"
            userList.append(userDict)
            sanDict["users"] = userList
        return sanDict
    except ClusterToStorageMapping.DoesNotExist:
        logger.debug("There is no SAN Networks associated with cluster ID : " +str(clusterId))
        return {}

def getNetsim(clusterId, tunnel=False, allNetsims=False):
    '''
    Function gets netsim info for host properties
    '''
    netsimDictDefault  = {"username": "netsim", "password": config.get('DMT_AUTODEPLOY', 'netsimNodePassword'), "type": "admin"}
    try:
        clusterServers = ClusterServer.objects.filter(cluster_id=clusterId)
        tunnelCount = 1
        jsonReturn = []
        netsimDict = {}
        sshPortDict = {"ssh":22}
        for clusterServer in clusterServers:
            if not allNetsims:
                if not clusterServer.active:
                    continue
            serverName =  str(re.sub(r"-", "", clusterServer.node_type.lower()))
            if not serverName == 'netsim':
                continue
            netsimDict = {}
            clusterServCreds = getClusterServerCredentials(clusterServer.id)
            clusterServerIP = str(IpAddress.objects.get(nic__server_id=clusterServer.server_id, ipType="other").address)
            netsimDict["ports"] = sshPortDict
            if not clusterServCreds:
                netsimDict["users"] = [netsimDictDefault]
            else:
                netsimDict["users"] = clusterServCreds
            if allNetsims:
                if clusterServer.active:
                    netsimDict["status"] = "active"
                else:
                    netsimDict["status"] = "passive"
            netsimDict["type"] = serverName
            netsimDict["hostname"] = clusterServer.server.hostname
            netsimDict["ip"] = clusterServerIP
            if tunnel:
                netsimDict["tunnel"] = tunnelCount
                tunnelCount += 1
            jsonReturn.append(dict(netsimDict))
        if tunnel:
            ret = jsonReturn,tunnelCount
        else:
            ret = jsonReturn
    except Exception as e:
        logger.error("issue getting netsim info: " +str(e))
        ret = []
    return ret

def getLVSRouterVIPInterfaces(ipv4Public, ipv4Internal, ipv6Public=None, ipv6Internal=None, ipv4Storage=None, ipv4Public2=None, ipv4Public3=None, ipv4Internal2=None, ipv4Internal3=None, ipv6Public2=None, ipv6Public3=None, ipv6Internal2=None, ipv6Internal3=None):
    '''
    Adding LVS Router VIP Interface Data
    '''
    ipTypes = ["public","internal","storage"]
    ports = {"http": 8080,
            "https": 443,
            "jboss_management": 9999,
            "jmx": 9999,
            "rmi": 4447,
            "ssh": 22}

    interfacesDict = {}
    interfaces = []
    for key in ipTypes:
        interface = {}
        if key == "public":
            interface["ipv4"] = ipv4Public
            if ipv4Public2:
               interface["ipv4_2"] = ipv4Public2
            if ipv4Public3:
               interface["ipv4_3"] = ipv4Public3
            interface["ipv6"] = ipv6Public
            if ipv6Public2:
               interface["ipv6_2"] = ipv6Public2
            if ipv6Public3:
               interface["ipv6_3"] = ipv6Public3
        elif key == "internal":
            interface["ipv4"] = ipv4Internal
            if ipv4Internal2:
               interface["ipv4_2"] = ipv4Internal2
            if ipv4Internal3:
               interface["ipv4_3"] = ipv4Internal3
            interface["ipv6"] = ipv6Internal
            if ipv6Internal2:
               interface["ipv6_2"] = ipv6Internal2
            if ipv6Internal3:
               interface["ipv6_3"] = ipv6Internal3
        else:
            interface["ipv4"] = ipv4Storage
            interface["ipv6"] = None
        interface["type"] = key
        interface["ports"] = ports
        interface["hostname"] = None
        interfaces.append(interface)
    interfacesDict = interfaces
    return interfacesDict

def getInterfaces(clusterServers):
    ipTypes = ["other","internal","backup","multicast","jgroup"]
    clusterServerIds = []
    clusterId = None
    for clusterServer in clusterServers:
        if not clusterServer['active']:
            continue
        clusterId = clusterServer['cluster_id']
        break
    for clusterServer in clusterServers:
        clusterServerIds.append(clusterServer['server_id'])

    IpAddressObjs = IpAddress.objects.filter(nic__server_id__in=clusterServerIds, ipType__in=ipTypes).only('address','ipv6_address','nic__server_id','ipType').values('address','ipv6_address','nic__server_id','ipType')
    VlanDetailsObjs = VlanDetails.objects.filter(cluster_id=clusterId).only('litp_management').values('litp_management')

    foundVlanDetailsObj = False
    for VlanDetailsObj in VlanDetailsObjs:
        foundVlanDetailsObj = True
        vlanType = VlanDetailsObj['litp_management']
        break

    if not foundVlanDetailsObj:
        raise Exception("Unable to get Vlan details to determine is this is a cluster on the services vlan or on the internal vlan")

    ports = { "ssh": 22}
    interfacesDict = {}
    for clusterServer in clusterServers:
        clusterServerID = clusterServer['server_id']
        interfacesDict[clusterServerID] = []
        interfaces = []

        foundPublicIpAddress=False
        try:
            for ipType in ipTypes:
                foundIpAddressObj=False
                for IpAddressObj in IpAddressObjs:
                    if IpAddressObj['nic__server_id'] == clusterServerID and IpAddressObj['ipType'] == ipType:
                        foundIpAddressObj = True
                        interface = {
                            "ipv4": str(IpAddressObj['address']),
                            "ipv6": str(IpAddressObj['ipv6_address']),
                            "type": IpAddressObj['ipType'],
                            "ports": ports,
                            "hostname": None
                        }
                        if IpAddressObj['ipType'] == 'other':
                            interface['type'] = 'public'
                            foundPublicIpAddress=True
                            if "DB" in clusterServer['node_type'] and "internal" in vlanType.lower():
                                interface['ipv4'] = None
                                interface['ipv6'] = None
                        interfaces.append(interface)
                if not foundIpAddressObj:
                    interface = {
                            "ipv4": None,
                            "ipv6": None,
                            "type": ipType,
                            "ports": ports,
                            "hostname": None
                    }
                    interfaces.append(interface)

            interfacesDict[clusterServerID] = interfaces
        except Exception as e:
            logger.error("Issue processing interface information :"+str(e))

        if not foundPublicIpAddress:
            problemServer = Server.objects.get(id=clusterServerID)
            raise Exception("Unable to find a public ip address for cluster server " + str(problemServer))

    return interfacesDict

def getIloInfo(serverId,hostname):
    '''
    Get the Ilo Info for a Server and return JSON
    '''
    ports = { "ssh": 22}
    iloInfoDict = {}

    try:
        if Ilo.objects.filter(server__id=serverId).exists():
            iloInfoObject = Ilo.objects.get(server__id=serverId)
            iloUserInfo = {"username": iloInfoObject.username, "password": iloInfoObject.password}
            iloInfoDict["ports"] = ports
            iloInfoDict["ip"] = str(iloInfoObject.ipMapIloAddress)
            iloInfoDict["hostname"] = hostname + "-ilo"
            iloInfoDict["type"] = "ilo"
            iloInfoDict["users"] = [iloUserInfo]
    except Exception as e:
        message = "There was an issue getting Ilo Info " + str(e)
        logger.error(message)

    return iloInfoDict

def getJbossJson(clusterId,tunnel):
    jbossReturn = []
    servGrpCreds = []
    serviceClsDictDefault = {"username": "root", "password": config.get('DMT_AUTODEPLOY', 'ServiceGroupPassword'), "type": "admin"}
    httpdServiceClsDictDefault = {"username": "administrator", "password": config.get('DMT_AUTODEPLOY', 'HttpdServiceGroupPassword'), "type": "admin"}

    jbossExtraUsersDict = {"username": "guest", "password": "guestp", "type": "oper"}
    jbossExtraUsersList = [serviceClsDictDefault]
    jbossExtraUsersList.append(jbossExtraUsersDict)

    jbossPortsDict = { "http": 8080, "rmi": 4447, "jmx": 9999, "jboss_management": 9999 }
    jbossPortsList = [jbossPortsDict]

    jbossPortsDictTunnel = {}
    lsbClusterPortsDictTunnel = {}
    lsbClusterPortsDict = { "http": 8080 }
    httpdPortsDict = { "http": 80, "https": 443 }

    lsbClusterPortsList = [lsbClusterPortsDict]
    serviceClusterDict = {}
    tunnelCount = 1
    serviceClusters = ServicesCluster.objects.filter(cluster_id=clusterId).only('id','cluster_type').values('id','cluster_type')
    serviceClusterIds = []
    for serviceCluster in serviceClusters:
        serviceClusterIds.append(serviceCluster['id'])

    serviceGroupIds = []
    serviceGroups = ServiceGroup.objects.filter(service_cluster_id__in=serviceClusterIds).only('id','name','service_cluster_id').values('id','name','service_cluster_id')
    for serviceGroup in serviceGroups:
        serviceGroupIds.append(serviceGroup['id'])

    manyServGrpCreds = getManyServGrpCredentials(serviceGroupIds)

    serviceGroupInstances = ServiceGroupInstance.objects.filter(service_group_id__in=serviceGroupIds).only('name','ipMap__address','service_group_id').values('name','ipMap__address','service_group_id')
    serviceGroupInstanceInternals = ServiceGroupInstanceInternal.objects.filter(service_group_id__in=serviceGroupIds).only('name','ipMap__address','service_group_id').values('name','ipMap__address','service_group_id')

    for serviceCluster in serviceClusters:
        for serviceGroup in serviceGroups:
            if (serviceGroup['service_cluster_id'] == serviceCluster['id']):
                servGrpCreds = manyServGrpCreds[serviceGroup['id']]
                for serviceGroupInstance in serviceGroupInstances:
                    if serviceGroupInstance['service_group_id'] == serviceGroup['id']:
                        if "JBOSS" in serviceCluster['cluster_type']:
                            serviceClusterDict["ports"] = jbossPortsDict
                            if not servGrpCreds:
                                serviceClusterDict["users"] = jbossExtraUsersList
                            else:
                                serviceClusterDict["users"] = servGrpCreds
                            serviceClusterDict["type"] = "jboss"
                        else:
                            if str(serviceGroup['name']) == "httpd" or str(serviceGroup['name']) == "haproxy":
                                serviceClusterDict["ports"] = httpdPortsDict
                                if not servGrpCreds:
                                    serviceClusterDict["users"] = [httpdServiceClsDictDefault]
                                else:
                                    serviceClusterDict["users"] = servGrpCreds
                            else:
                                serviceClusterDict["ports"] = lsbClusterPortsDict
                                if not servGrpCreds:
                                    serviceClusterDict["users"] = [serviceClsDictDefault]
                                else:
                                    serviceClusterDict["users"] = servGrpCreds
                            serviceClusterDict["type"] = "http"
                        serviceClusterDict["group"] = str(serviceGroup['name'])
                        serviceClusterDict["ip"] = str(serviceGroupInstance['ipMap__address'])
                        serviceClusterDict["hostname"] = str(serviceGroup['name']) + "_" + re.sub(r"_", "", str(serviceGroupInstance['name']))
                        jbossReturn.append(dict(serviceClusterDict))
                        serviceClusterDict = {}
                for serviceGroupInstance in serviceGroupInstanceInternals:
                    if serviceGroupInstance['service_group_id'] == serviceGroup['id']:
                        if tunnel:
                            if "JBOSS" in serviceCluster['cluster_type']:
                                serviceClusterDict["ports"] = jbossPortsDict
                                serviceClusterDict["tunnel"] = tunnelCount
                                if not servGrpCreds:
                                    serviceClusterDict["users"] = jbossExtraUsersList
                                else:
                                    serviceClusterDict["users"] = servGrpCreds
                                serviceClusterDict["type"] = "jboss"
                            else:
                                if str(serviceGroup['name']) == "httpd" or str(serviceGroup['name']) == "haproxy":
                                    serviceClusterDict["ports"] = httpdPortsDict
                                else:
                                    serviceClusterDict["ports"] = lsbClusterPortsDict
                                serviceClusterDict["tunnel"] = tunnelCount
                                if not servGrpCreds:
                                    serviceClusterDict["users"] = [serviceClsDictDefault]
                                else:
                                    serviceClusterDict["users"] = servGrpCreds
                                serviceClusterDict["type"] = "http"
                            tunnelCount += 1
                        else:
                            if "JBOSS" in serviceCluster['cluster_type']:
                                serviceClusterDict["ports"] = jbossPortsDict
                                if not servGrpCreds:
                                    serviceClusterDict["users"] = jbossExtraUsersList
                                else:
                                    serviceClusterDict["users"] = servGrpCreds
                                serviceClusterDict["type"] = "jboss"
                            else:
                                if str(serviceGroup['name']) == "httpd" or str(serviceGroup['name']) == "haproxy":
                                    serviceClusterDict["ports"] = httpdPortsDict
                                else:
                                    serviceClusterDict["ports"] = lsbClusterPortsDict
                                if not servGrpCreds:
                                    serviceClusterDict["users"] = [serviceClsDictDefault]
                                else:
                                    serviceClusterDict["users"] = servGrpCreds
                                serviceClusterDict["type"] = "http"
                        serviceClusterDict["group"] = "internal_"+str(serviceGroup['name'])
                        serviceClusterDict["ip"] = str(serviceGroupInstance['ipMap__address'])
                        serviceClusterDict["hostname"] = "internal_"+str(serviceGroup['name']) + "_" + re.sub(r"_", "", str(serviceGroupInstance['name']))
                        jbossReturn.append(dict(serviceClusterDict))
                        serviceClusterDict = {}
                        jbossPortsDictTunnel = {}
                        lsbClusterPortsDictTunnel = {}
    return jbossReturn

def getVMInfo(clusterId,tunnel,tunnelCount,nodeType):
    virtualImageInfoAll = []
    jbossPortsDict = { "https": 443, "http": 8080, "rmi": 4447, "jmx": 9999, "jboss_management": 9999 , "ssh": 22}
    httpdPortsDict = { "http": 80, "https": 443 }
    vmPorts = { "ssh": 22}
    defaultUserList  = [{"username": "root", "password": config.get('DMT_AUTODEPLOY', 'kvmPassword'), "type": "admin"}]

    try:
        if VirtualImage.objects.filter(cluster_id=clusterId):
            virtualImageObjs = VirtualImage.objects.filter(cluster_id=clusterId,node_list=nodeType).only('name','id').values('name','id')
            virtualImageIds = []
            virtualImageNames = []
            for virtualImage in virtualImageObjs:
                virtualImageIds.append(virtualImage['id'])
                virtualImageNames.append(virtualImage['name'])
            VirtualImageItemObjs = VirtualImageItems.objects.filter(name__in=virtualImageNames).only('name','type').values('name','type')
            ipv4Values = ('hostname','ipMap__address','virtual_image_id',)
            ipv6Values = ('hostname','ipMap__ipv6_address','virtual_image_id',)
            vmServerCredsValues = ('virtualimage_id','credentials__username','credentials__password','credentials__credentialType',)
            vmIpPublicObjs = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds,ipMap__ipType__startswith="virtualImage_public",number="1").only(ipv4Values).values(*ipv4Values)
            vmIpPublicIpv6Objs = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds,ipMap__ipType__startswith="virtualImage_ipv6Public",number="1").only(ipv6Values).values(*ipv6Values)
            vmIpStorageObjs = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds,ipMap__ipType__startswith="virtualImage_storage",number="1").only(ipv4Values).values(*ipv4Values)
            vmIpInternalObjs = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds,ipMap__ipType__startswith="virtualImage_internal",number="1").only(ipv4Values).values(*ipv4Values)
            vmIpInternalIpv6Objs = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds,ipMap__ipType__startswith="virtualImage_ipv6Internal",number="1").only(ipv6Values).values(*ipv6Values)
            vmIpJGroupObjs = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds,ipMap__ipType__startswith="virtualImage_jgroup",number="1").only(ipv4Values).values(*ipv4Values)
            vmServerCredsObjs = VirtualImageCredentialMapping.objects.filter(virtualimage_id__in=virtualImageIds).only(vmServerCredsValues).values(*vmServerCredsValues)

            for virtualImageObj in virtualImageObjs:
                vmIpPublicObj = None
                vmIpPublicIpv6Obj = None
                vmIpStorageObj = None
                vmIpInternalObj = None
                vmIpJGroupObj = None
                ipv4Public = None
                ipv6Public = None
                hostnamePublic = None
                ipv4Internal = None
                ipv6Internal = None
                hostnameInternal = None
                ipv4Storage = None
                ipv6Storage = None
                hostnameStorage = None
                ipv4JGroup = None
                ipv6JGroup = None
                hostnameJGroup = None
                pkgList = []
                interfaces = []
                group,unit = getGroupUnit(virtualImageObj['name'])

                vmType = "jboss"
                for VirtualImageItemObj in VirtualImageItemObjs:
                    if VirtualImageItemObj['name'] == virtualImageObj['name']:
                        vmType = VirtualImageItemObj['type']
                        break

                if vmType == 'jboss':
                    ports = jbossPortsDict
                else:
                    ports = httpdPortsDict

                for vmIpPublicObj in vmIpPublicObjs:
                    if vmIpPublicObj['virtual_image_id'] == virtualImageObj['id']:
                        hostnamePublic = vmIpPublicObj['hostname']
                        if 'httpd' in virtualImageObj['name'] or 'haproxy' in virtualImageObj['name']:
                            ipv4Public = hostnamePublic+"."+config.get('DMT_SERVER', 'domain')
                        else:
                            ipv4Public = vmIpPublicObj['ipMap__address']
                        break

                for vmIpPublicIpv6Obj in vmIpPublicIpv6Objs:
                    if vmIpPublicIpv6Obj['virtual_image_id'] == virtualImageObj['id']:
                        ipv6Public = vmIpPublicIpv6Obj['ipMap__ipv6_address']
                        break

                interface = {
                    "ipv4": ipv4Public,
                    "ipv6": ipv6Public,
                    "type": "public",
                    "ports": ports,
                    "hostname": hostnamePublic
                }
                interfaces.append(interface)

                for vmIpStorageObj in vmIpStorageObjs:
                    if vmIpStorageObj['virtual_image_id'] == virtualImageObj['id']:
                        ipv4Storage = vmIpStorageObj['ipMap__address']
                        hostnameStorage = vmIpStorageObj['hostname']
                        break

                interface = {
                                "ipv4": ipv4Storage,
                                "ipv6": ipv6Storage,
                                "type": "storage",
                                "ports": ports,
                                "hostname": hostnameStorage
                             }
                interfaces.append(interface)

                for vmIpInternalObj in vmIpInternalObjs:
                    if vmIpInternalObj['virtual_image_id'] == virtualImageObj['id']:
                        ipv4Internal = vmIpInternalObj['ipMap__address']
                        hostnameInternal = vmIpInternalObj['hostname']
                        break

                for vmIpInternalIpv6Obj in vmIpInternalIpv6Objs:
                    if vmIpInternalIpv6Obj['virtual_image_id'] == virtualImageObj['id']:
                        ipv6Internal = vmIpInternalIpv6Obj['ipMap__ipv6_address']
                        hostnameInternal = vmIpInternalIpv6Obj['hostname']
                        break

                interface = {
                                "ipv4": ipv4Internal,
                                "ipv6": ipv6Internal,
                                "type": "internal",
                                "ports": ports,
                                "hostname": hostnameInternal
                             }
                if tunnel:
                    interface['tunnel'] = int(tunnelCount)
                    tunnelCount += 1
                interfaces.append(interface)

                for vmIpJGroupObj in vmIpJGroupObjs:
                    if vmIpJGroupObj['virtual_image_id'] == virtualImageObj['id']:
                       ipv4JGroup = vmIpJGroupObj['ipMap__address']
                       hostnameJGroup = vmIpJGroupObj['hostname']
                       break

                interface = {
                                "ipv4": ipv4JGroup,
                                "ipv6": ipv6JGroup,
                                "type": "jgroup",
                                "ports": ports,
                                "hostname": hostnameJGroup
                            }
                interfaces.append(interface)

                vmServCreds = []
                for vmServerCredsObj in vmServerCredsObjs:
                    if vmServerCredsObj['virtualimage_id'] == virtualImageObj['id']:
                        userDict={}
                        userDict["username"] = vmServerCredsObj['credentials__username']
                        userDict["password"] = vmServerCredsObj['credentials__password']
                        userDict["type"] = vmServerCredsObj['credentials__credentialType']
                        vmServCreds.append(userDict)

                if not vmServCreds:
                    vmServCreds  = defaultUserList
                virtualImageInfo =  {
                                    "group": group,
                                    "unit": unit,
                                    "type": vmType,
                                    "interfaces": interfaces,
                                    "users": vmServCreds,
                                    "hostname": group+"_"+str(unit),
                                    "ports": vmPorts
                                    }
                virtualImageInfoAll.append(virtualImageInfo)
    except Exception as e:
            logger.error("Issue processing VM information :"+str(e))
    return virtualImageInfoAll,tunnelCount

def getGroupUnit(virtualImageName):
    try:
        if virtualImageName[-1].isdigit():
            group,unit = virtualImageName.rsplit("_", 1)
            group = group.lower()
            unit = int(unit)
        else:
            group = virtualImageName
            unit =0
    except Exception as e:
        logger.error("Issue with processing VM name, naming convention violation '"+str(virtualImageName)+"': "+str(e))
        group = virtualImageName
        unit =0
    return  group,unit

def buildUpTAFHostPropertiesJSONUsingCITERestCall(citeHostPropertiesFile, line):
    '''
    The buildUpTAFHostPropertiesJSONUsingCITERestCall function calls the CITE Rest and return host properities
    for deployments that are not stored in the CIFWK DB, these are appended to the CIFWK host properties JSON.
    '''
    citeRestCall = config.get('DMT_HOSTPROPERTIES', 'citeJSONRestCall')
    wgetCommand = config.get('COMMANDS', 'wget')
    try:
        for file in citeHostPropertiesFile:
            citeRestCall += ":" +str(file)
    except Exception as e:
        return HttpResponse("Error: Building Up CITE REST Call data " +str(e))
    try:
        command =  wgetCommand + " " + citeRestCall
        runCiteRestCall = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd="/tmp")
        runCiteRestCall.wait()
        citeRestCallReturnedList = runCiteRestCall.stdout.readlines()
    except Exception as e:
        return HttpResponse("Error: Building Up CITE REST Call host property output; " +str(e))

    for citeRestCallReturned in citeRestCallReturnedList:
        citeRestCallReturnedStripped = citeRestCallReturned[1:-1]
        citeRestDict = ast.literal_eval(citeRestCallReturnedStripped)
        for item in citeRestDict:
            line.append(item)
    return line

def findIpInClusterSerivces(cluster, ipAddress):
    '''
    Find IP Address in Cluster's Serivces
    '''
    allIPs=""
    try:
        if VirtualImage.objects.filter(cluster_id=cluster.id).exists():
            ipTypesIPv4List = ["virtualImage_public", "virtualImage_storage", "virtualImage_jgroup", "virtualImage_internal", "virtualImage_ipv6Public", "virtualImage_ipv6Internal"]
            ipMapAddrVal = ("ipMap__address", "ipMap__ipv6_address",)
            virtualImage = VirtualImage.objects.only('id').values('id').filter(cluster_id=cluster.id)
            for virtualImageObj in virtualImage:
                vmIpObj = None
                for ipType in ipTypesIPv4List:
                    if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj['id'],ipMap__ipType__startswith=ipType).exists():
                        vmIpObj = VirtualImageInfoIp.objects.only(ipMapAddrVal).values(*ipMapAddrVal).filter(virtual_image=virtualImageObj['id'],ipMap__ipType__startswith=ipType)
                        for ip in vmIpObj:
                            if ip['ipMap__ipv6_address'] != None:
                                ipv6Address = dmt.utils.normalizedIpv6Postfix(str(ip['ipMap__ipv6_address']))
                                if int(IPAddress(ipAddress)) == int(IPAddress(ipv6Address)):
                                    return True
                            else:
                                if ipAddress == str(ip['ipMap__address']):
                                    return True
        return False
    except Exception as e:
        logger.error("Error getting IP info for cluster id:"+str(cluster.id)+" "+str(e))
        return False

def getAllIPsInCluster(cluster):
    allIPs=""
    servers = []
    ipaddrs = []
    ipAddrVal = ("address", "ipv6_address",)
    try:
        ServicesClr = ServicesCluster.objects.filter(cluster_id=cluster.id)
        clustersvrs = ClusterServer.objects.filter(cluster=cluster)
        managementServer = cluster.management_server
        for cs in clustersvrs:
            servers += Server.objects.filter(id=cs.server.id)
            nics = []
            ilos = []
            for server in servers:
                nics += NetworkInterface.objects.filter(server=server.id)
                ilos += Ilo.objects.filter(server=server.id)
            bladeExtraDetails = []
            for nic in nics:
                if IpAddress.objects.filter(nic=nic.id).exists():
                    ipaddrs += IpAddress.objects.only(ipAddrVal).values(*ipAddrVal).filter(nic=nic.id)
                try:
                    if BladeHardwareDetails.objects.filter(mac_address=nic).exists():
                        bladeExtraDetails += BladeHardwareDetails.objects.filter(mac_address=nic)
                except Exception as e:
                   logger.error(e)

        for publicIPObj in ipaddrs:
            allIPs=allIPs+":"+str(publicIPObj['address'])
            if publicIPObj['ipv6_address'] != None:
                allIPs=allIPs+":"+str(publicIPObj['ipv6_address'])
        ipv4AddrVal = ("ipMap__address",)
        for servClr in ServicesClr:
            serviceGroup = ServiceGroup.objects.filter(service_cluster_id=servClr.id)
            for obj in serviceGroup:
                jbossInternalServiceInstances = None
                jbossServiceInstances = None
                if ServiceGroupInstanceInternal.objects.filter(service_group=obj).exists():
                    jbossInternalServiceInstances = ServiceGroupInstanceInternal.objects.only(ipv4AddrVal).values(*ipv4AddrVal).filter(service_group=obj)
                if ServiceGroupInstance.objects.filter(service_group=obj).exists():
                    jbossServiceInstances = ServiceGroupInstance.objects.only(ipv4AddrVal).values(*ipv4AddrVal).filter(service_group=obj)
                if jbossServiceInstances:
                    for serviceInstance in  jbossServiceInstances:
                        allIPs=allIPs+":"+str(serviceInstance['ipMap__address'])
                if jbossInternalServiceInstances:
                    for serviceInstance in  jbossInternalServiceInstances:
                        allIPs=allIPs+":"+str(serviceInstance['ipMap__address'])

        if VirtualImage.objects.filter(cluster_id=cluster.id).exists():
            ipTypesIPv4List = ["virtualImage_public", "virtualImage_storage", "virtualImage_jgroup", "virtualImage_internal", "virtualImage_ipv6Public", "virtualImage_ipv6Internal"]
            ipMapAddrVal = ("ipMap__address", "ipMap__ipv6_address",)
            virtualImage = VirtualImage.objects.only('id').values('id').filter(cluster_id=cluster.id)
            for virtualImageObj in virtualImage:
                vmIpObj = None
                for ipType in ipTypesIPv4List:
                    if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj['id'],ipMap__ipType__startswith=ipType).exists():
                        vmIpObj = VirtualImageInfoIp.objects.only(ipMapAddrVal).values(*ipMapAddrVal).filter(virtual_image=virtualImageObj['id'],ipMap__ipType__startswith=ipType)
                        for ip in vmIpObj:
                            if ip['ipMap__ipv6_address'] != None:
                                allIPs=allIPs+":"+str(ip['ipMap__ipv6_address'])
                            else:
                                allIPs=allIPs+":"+str(ip['ipMap__address'])
        # Database Vips
        if DatabaseVips.objects.filter(cluster_id=cluster.id).exists():
            fields = ("postgres_address__address","versant_address__address",
                      "mysql_address__address","opendj_address__address","opendj_address2__address",
                      "jms_address__address","eSearch_address__address","neo4j_address1__address",
                      "neo4j_address2__address","neo4j_address3__address","gossipRouter_address1__address",
                      "gossipRouter_address2__address","eshistory_address__address")
            DatabaseVipsObj = DatabaseVips.objects.only(fields).values(*fields).get(cluster_id=cluster.id)
            for ip in DatabaseVipsObj:
                allIPs=allIPs + ":" + str(DatabaseVipsObj[ip])
        # LVS Router Vips
        if LVSRouterVip.objects.filter(cluster_id=cluster.id).exists():
            fields = ("pm_internal__address", "pm_external__address",
                    "fm_internal__address", "fm_external__address", "fm_internal_ipv6__ipv6_address", "fm_external_ipv6__ipv6_address",
                    "cm_internal__address", "cm_external__address", "cm_internal_ipv6__ipv6_address", "cm_external_ipv6__ipv6_address",
                    "svc_pm_storage__address", "svc_fm_storage__address", "svc_cm_storage__address",
                    "svc_storage_internal__address", "svc_storage__address",
                    "scp_scp_internal__address", "scp_scp_external__address", "scp_scp_internal_ipv6__ipv6_address", "scp_scp_external_ipv6__ipv6_address",
                    "scp_scp_storage__address", "scp_storage_internal__address", "scp_storage__address",
                    "evt_storage_internal__address", "evt_storage__address",
                    "str_internal__address", "str_str_internal_2__address", "str_str_internal_3__address",
                    "str_external__address", "str_str_external_2__address", "str_str_external_3__address",
                    "str_str_internal_ipv6__ipv6_address", "str_str_internal_ipv6_2__ipv6_address", "str_str_internal_ipv6_3__ipv6_address",
                    "str_external_ipv6__ipv6_address", "str_str_external_ipv6_2__ipv6_address", "str_str_external_ipv6_3__ipv6_address",
                    "str_str_storage__address", "str_storage_internal__address", "str_storage__address",
                    "esn_str_internal__address", "esn_str_external__address", "esn_str_internal_ipv6__ipv6_address",
                    "esn_str_external_ipv6__ipv6_address", "esn_str_storage__address", "esn_storage_internal__address",
                    "ebs_storage_internal__address", "ebs_storage__address", "asr_storage_internal__address", "asr_asr_external__address",
                    "asr_asr_internal__address", "asr_asr_external_ipv6__ipv6_address", "asr_storage__address","asr_asr_storage__address",
                    "eba_storage_internal__address", "eba_storage__address",
                    "msossfm_internal__address", "msossfm_external__address", "msossfm_internal_ipv6__ipv6_address", "msossfm_external_ipv6__ipv6_address")
            lvsRouterVipObj = LVSRouterVip.objects.only(fields).values(*fields).get(cluster_id=cluster.id)
            for ip in lvsRouterVipObj:
                allIPs=allIPs + ":" + str(lvsRouterVipObj[ip])
        if LVSRouterVipExtended.objects.filter(cluster_id=cluster.id).exists():
            fields_extras = ("eba_external__address", "eba_external_ipv6__ipv6_address", "eba_internal__address", "eba_internal_ipv6__ipv6_address",
                             "svc_pm_ipv6__ipv6_address", "oran_internal__address", "oran_internal_ipv6__ipv6_address", "oran_external__address", "oran_external_ipv6__ipv6_address")
            lvsRouterVipExtendedObj = LVSRouterVipExtended.objects.only(fields_extras).values(*fields_extras).get(cluster_id=cluster.id)
            for ip in lvsRouterVipExtendedObj:
                allIPs=allIPs + ":" + str(lvsRouterVipExtendedObj[ip])
        # Hybrid Cloud
        if HybridCloud.objects.filter(cluster_id=cluster.id).exists():
            fields = ("gateway_internal__address",
                      "gateway_external__address",
                      "gateway_internal_ipv6__ipv6_address",
                      "gateway_external_ipv6__ipv6_address",)
            hybridCloudObj = HybridCloud.objects.only(fields).values(*fields).get(cluster_id=cluster.id)
            for ip in hybridCloudObj:
                allIPs=allIPs + ":" + str(hybridCloudObj[ip])
        # DVMS Information
        if DvmsInformation.objects.filter(cluster_id=cluster.id).exists():
            fields = ("external_ipv4__address",
                      "external_ipv6__ipv6_address",
                      "internal_ipv4__address",)
            dvmsInformationObj = DvmsInformation.objects.only(fields).values(*fields).get(cluster_id=cluster.id)
            for ip in dvmsInformationObj:
                allIPs=allIPs + ":" + str(dvmsInformationObj[ip])

        if managementServer.server:
            internalMSAllIps = getAllIPsInManagementServer(managementServer.server,'internal')
            if internalMSAllIps != "":
                allIPs=allIPs+internalMSAllIps
        return allIPs
    except Exception as e:
        logger.error("Error getting IP info for cluster id:"+str(cluster.id)+" "+str(e))
        return ""

def getAllIPsInManagementServer(managementServer,ipType=None):
    allIPs=""
    ipaddrs = []
    ipAddrVal = ("address", "ipv6_address",)
    try:
        nics = []
        ilos = []
        nics += NetworkInterface.objects.filter(server=managementServer.id)
        ilos += Ilo.objects.filter(server=managementServer.id)
        for nic in nics:
            if IpAddress.objects.filter(nic=nic.id).exists():
                if ipType:
                    if IpAddress.objects.only(ipAddrVal).values(*ipAddrVal).filter(nic=nic.id,ipType=ipType):
                        ipaddrs += IpAddress.objects.only(ipAddrVal).values(*ipAddrVal).filter(nic=nic.id,ipType=ipType)
                else:
                    ipaddrs += IpAddress.objects.filter(nic=nic.id)
        for iPObj in ipaddrs:
            allIPs=allIPs+":"+str(iPObj['address'])
            if iPObj['ipv6_address'] != None:
                allIPs=allIPs+":"+str(iPObj['ipv6_address'])
    except Exception as e:
        logger.error("Error getting IP info for Management id:"+str(managementServer.id)+" "+str(e))
    return allIPs

def getNextFreeInternalIP(cluster, searchType=None, allIPs=None):
    IpRangeItems = []
    rangeType = ""
    if searchType is not None:
        if isinstance(searchType, list):
            rangeType = searchType
        else:
            rangeType = [searchType]
    else:
        rangeType = ["PDU-Priv-2_nodeInternal"]

    for item in rangeType:
        if IpRangeItem.objects.filter(ip_range_item=item).exists():
            ipRangeItemObj = IpRangeItem.objects.get(ip_range_item=item)
            IpRangeItems.append(ipRangeItemObj)
        else:
            logger.error("There was an issue generating an auto generated IP address")
            return "","",""

    instanceIpAddress = ""
    instanceGateway = ""
    instanceBitmask = ""
    ipRangeObjs = []
    ipRangeList = []
    try:
        for ipRangeItemObj in IpRangeItems:
            if IpRange.objects.filter(ip_range_item=ipRangeItemObj).exists():
                ipRange = IpRange.objects.get(ip_range_item=ipRangeItemObj)
                ipRangeObjs.append(ipRange)
        if allIPs is not None:
            allIPs=allIPs
        else:
            allIPs=getAllIPsInCluster(cluster)
        for ipRange in ipRangeObjs:
            ipRangeList = iptools.IpRange(ipRange.start_ip, ipRange.end_ip)
            try:
                for ipCheck in ipRangeList:
                    if ipCheck in allIPs:
                        if ipCheck != ipRange.end_ip:
                            continue
                        else:
                            break
                    elif doNotUseIpCheck(ipCheck):
                        continue
                    else:
                        instanceIpAddress = ipCheck
                        instanceGateway = ipRange.gateway
                        instanceBitmask = ipRange.bitmask
                        return instanceGateway,instanceIpAddress,instanceBitmask
            except Exception as e:
                logger.error("issue with getting next free ip" +str(e))
        return "","",""
    except:
        return "","",""

def getNextFreeInternalIPManagementServer(managementServer, searchType=None):
    if searchType != None:
        rangeType = searchType
    else:
        rangeType = "PDU-Priv-2_nodeInternal"
    if IpRangeItem.objects.filter(ip_range_item=rangeType).exists():
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item=rangeType)
    else:
        logger.error("There was an issue generating an auto generated IP address")
        return "","",""

    instanceIpAddress = ""
    instanceGateway = ""
    instanceBitmask = ""

    if IpRange.objects.filter(ip_range_item=ipRangeItemObj).exists():
        ipRange = IpRange.objects.filter(ip_range_item=ipRangeItemObj).order_by('start_ip')
    try:
        allIPs=getAllIPsInManagementServer(managementServer)
        msServerObj = ManagementServer.objects.get(server=managementServer)
        clusterObjs=Cluster.objects.filter(management_server=msServerObj)
        for clusterObj in clusterObjs:
            allIPsCluster=getAllIPsInCluster(clusterObj)
            allIPs=allIPs+allIPsCluster
        for ip in ipRange:
            ipRangeList = iptools.IpRange(ip.start_ip,ip.end_ip)
            try:
                for ipCheck in ipRangeList:
                    if ipCheck in allIPs:
                        continue
                    elif doNotUseIpCheck(ipCheck):
                        continue
                    else:
                        instanceIpAddress = ipCheck
                        instanceGateway = ip.gateway
                        instanceBitmask = ip.bitmask
                        break
                return instanceGateway,instanceIpAddress,instanceBitmask
            except Exception as e:
                logger.error("issue with getting next free ip" +str(e))
    except:
        return "","",""


def uploadSedData(user,version,sed,jiraNumber, iso, linkText, link):
    '''
    Function used to upload the SED to the DB used by the UI and the TAF testware
    '''
    try:
        uploadSed = Sed.objects.create(user=user,version=version,sed=sed,jiraNumber=jiraNumber, iso=iso, linkText=linkText, link=link)
    except Exception as e:
        logger.error("There was an issue with the update of the SED data within the utils file see function uploadSedData")
        return 1

def uploadSedCheck(user,version,sed,jiraNumber,iso,linkText,link,whatToDo):
    '''
    Function used to check what was uploaded was actually upload to the DB using for TAF testing
    '''
    try:
        uploadSed = Sed.objects.get(version=version)
        if whatToDo == "checkUser":
            if user != uploadSed.user:
                return 1
        if whatToDo == "checkVersion":
            if version != uploadSed.version:
                return 1
        if whatToDo == "checkJiraNumber":
            if jiraNumber != uploadSed.jiraNumber:
                return 1
        if whatToDo == "checkISO":
            if iso != uploadSed.iso.version:
                return 1
        if whatToDo == "checkLinkText":
            if linkText != uploadSed.linkText:
                return 1
        if whatToDo == "checkLink":
            if link != uploadSed.link:
                return 1
        if whatToDo == "checkSed":
            if sed.strip() != uploadSed.sed.strip():
                return 1
    except Exception as e:
        logger.error("There was an issue unable to find entry for SED Version " + str(version))
        return 1

def savedServiceGroupInstance(name,cluster_type,node_list,serviceClr):
    '''
    Function used to save the Service group instance to the DB used by the UI and the TAF testware
    This can be depricated once the KVM is up and running
    '''
    try:
        savedGroup = ServiceGroup.objects.create(name=name,cluster_type=cluster_type,node_list=node_list,service_cluster=serviceClr)
    except Exception as e:
        logger.error("There was an issue with the saving of the Service group instance data. Exception " + str(e))
        return 1

def savedServiceGroupInstanceIp(address,bitmask,gateway,ipType,name,hostname,serviceGroupId):
    '''
    Function used to save the Service group instance IP Addresses to the DB used by the UI and the TAF testware
    '''
    try:
        instanceIpObj = IpAddress.objects.create(address=address,bitmask=bitmask,gateway_address=gateway,ipType=ipType)
        instIpMapObj = ServiceGroupInstance.objects.create(name=name,hostname=hostname,service_group=serviceGroupId,ipMap=instanceIpObj)
    except Exception as e:
        logger.error("There was an issue with the saving of the Service group instance IP data. Exception " + str(e))
        return 1

def setSedMaster(idTag,sedUser,masterId):
    '''
    The setSedMaster function is used to set a version of the SED to SED master
    '''
    try:
        sedMasterObject, created = SedMaster.objects.get_or_create(identifer=idTag)
        sedMasterObject.sedMaster_id = masterId
        sedMasterObject.dateUpdated = datetime.now()
        sedMasterObject.sedUser = sedUser
        sedMasterObject.save()
        logger.debug("Setting "+str(masterId) +" to Master SED. Set by "+str(sedUser))
    except Exception as error:
        logger.error("There is an issue setting the Master SED within the utils file see function SedMasterData. " + str(error))
def getMasterSedVersion():
    try:
        idTag = config.get("DMT", "dmtra")
        if SedMaster.objects.filter(identifer=idTag).exists():
            sedMasterObject = SedMaster.objects.get(identifer=idTag)
            sedVerObj  = Sed.objects.get(id=sedMasterObject.sedMaster.id)
            sedVer = sedVerObj.version
        else:
            sedVer = None
    except Exception as e:
        logger.error("Issue getting Master SED version" +str(e))
        sedVer = None
    return sedVer

def setVirtualSedMaster(idTag,sedUser,virtualMasterId):
    '''
    The setVirtualSedMaster function is used to set a version of the SED to SED master for Virtual ENM
    '''
    try:
        sedObject = Sed.objects.get(id=virtualMasterId)
        sedMasterObject, created = SedMaster.objects.get_or_create(identifer=idTag)
        sedMasterObject.sedMaster_virtual = sedObject
        sedMasterObject.dateUpdated = datetime.now()
        sedMasterObject.sedUser = sedUser
        sedMasterObject.save()
        logger.debug("Setting "+str(virtualMasterId) +" to Master SED. Set by "+str(sedUser))
    except Exception as error:
        logger.error("There is an issue setting the Master SED within the utils file see function SedVirtualMasterData. " + str(error))

def getVirtualMasterSedVersion():
    try:
        idTag = config.get("DMT", "dmtravirtual")
        if SedMaster.objects.filter(identifer=idTag).exists():
            sedMasterObject = SedMaster.objects.get(identifer=idTag)
            sedVerObj  = Sed.objects.get(id=sedMasterObject.sedMaster_virtual_id)
            sedVer = sedVerObj.version
        else:
            sedVer = None
    except Exception as e:
        logger.error("Issue getting Master SED version" +str(e))
        sedVer = None
    return sedVer


def nameCheck(name):
    '''
    This function is used to check the name entered to ensure it is valid
    '''
    contains = config.get('DMT_MGMT', 'checkForName')
    message = "OK"
    for item in contains:
        if name.count(item):
            message="No Special Characters of type " + str(contains) + ", Allowed in name given. Remove and Try Again"
    return message

def hostNameCheck(hostname):
    '''
    This function is used to check the hostname entered to ensure it is valid
    '''
    contains = config.get('DMT_MGMT', 'checkFor')
    message = "OK"
    for item in contains:
        if hostname.count(item):
            message="No Special Characters of type " + str(contains) + ", Allowed in Hostname. Remove and Try Again"
    if not hostname.islower():
       message="Hostname Should be Lowercase, Remove and Try Again"
    return message

def getServGrpCredentials(serviceGroupId):
    '''
    This function is used to get credentials (username/password/type) associated with a service group
    '''
    servGrpUsersList = []
    try:
        mappings = ServiceGroupCredentialMapping.objects.filter(service_group__id=serviceGroupId)
        servGrpUsersList = getCredentials(mappings)
    except Exception as error:
        logger.error("There is an issue getting credentials for Service Group ID: " + serviceGroupId + " - " + str(error))
    return servGrpUsersList

def getManyServGrpCredentials(serviceGroupIds):
    manyServGrpCredentials = defaultdict(list)

    credentialsObjs = ServiceGroupCredentialMapping.objects.filter(service_group_id__in=serviceGroupIds).only('service_group_id','credentials__username','credentials__password','credentials__credentialType').values('service_group_id', 'credentials__username','credentials__password','credentials__credentialType')
    for credentialsObj in credentialsObjs:
        userDict={}
        userDict["username"] = credentialsObj['credentials__username']
        userDict["password"] = credentialsObj['credentials__password']
        userDict["type"] = credentialsObj['credentials__credentialType']
        manyClusterServerCredentials[credentialsObj['service_group_id']].append(userDict)
    return manyServGrpCredentials

def getMgmtServerCredentials(mgmtServerId):
    '''
    This function is used to get credentials (username/password/type) associated with a Management Server
    '''
    mgmtServerUsersList = []
    try:
        mappings = ManagementServerCredentialMapping.objects.filter(mgtServer__id=mgmtServerId)
        mgmtServerUsersList = getCredentials(mappings)
    except Exception as error:
        logger.error("There is an issue getting credentials for Management Server ID: " + mgmtServerId + " - " + str(error))
    return mgmtServerUsersList

def getVMgmtServerCredentials(vMgmtServerId):
    '''
    This function is used to get credentials (username/password/type) associated with a Virtual Management Server
    '''
    vMgmtServerUsersList = []
    try:
        mappings = VirtualMSCredentialMapping.objects.filter(virtualMgtServer__id=vMgmtServerId)
        vMgmtServerUsersList = getCredentials(mappings)
    except Exception as error:
        logger.error("There is an issue getting credentials for Management Server ID: " + mgmtServerId + " - " + str(error))
    return vMgmtServerUsersList

def getClusterServerCredentials(clusterServerId):
    '''
    This function is used to get credentials (username/password/type) associated with a Cluster Server
    '''
    clusterServUsersList = []
    try:
        mappings = ClusterServerCredentialMapping.objects.filter(clusterServer__id=clusterServerId)
        clusterServUsersList = getCredentials(mappings)
    except Exception as error:
        logger.error("There is an issue getting credentials for Cluster Server ID: " + clusterServerId + " - " + str(error))
    return clusterServUsersList


def getVMServerCredentials(vmServerId):
    '''
    This function is used to get credentials (username/password/type) associated with a Cluster Server
    '''
    vmServUsersList = []
    try:
        mappings = VirtualImageCredentialMapping.objects.filter(virtualimage__id=vmServerId)
        vmServUsersList = getCredentials(mappings)
    except Exception as error:
        logger.error("There is an issue getting credentials for Cluster Server ID: " + vmServerId + " - " + str(error))
    return vmServUsersList

def getManyClusterServerCredentials(clusterServers):
    manyClusterServerCredentials = defaultdict(list)

    clusterIds = []
    for clusterServer in clusterServers:
        if not clusterServer['active']:
            continue
        clusterIds.append(clusterServer['id'])

    credentialsObjs = ClusterServerCredentialMapping.objects.filter(clusterServer__id__in=clusterIds).only('clusterServer__id','credentials__username','credentials__password','credentials__credentialType').values('clusterServer__id', 'credentials__username','credentials__password','credentials__credentialType')
    for credentialsObj in credentialsObjs:
        userDict={}
        userDict["username"] = credentialsObj['credentials__username']
        userDict["password"] = credentialsObj['credentials__password']
        userDict["type"] = credentialsObj['credentials__credentialType']
        manyClusterServerCredentials[credentialsObj['clusterServer__id']].append(userDict)
    return manyClusterServerCredentials

def getCredentials(mappings):
    '''
    This function take an object and returns a list of Credentials found in the DB associated with it
    '''
    usersList = []
    try:
        # For each mapping get the credentials and add it to the cluster server users list object
        mappingsCredentialsIds = mappings.only('credentials_id').values_list('credentials_id',flat=True)
        credentialsObjs = Credentials.objects.filter(id__in=mappingsCredentialsIds).only('username','password','credentialType').values('username','password','credentialType')
        for credentialsObj in credentialsObjs:
            userDict={}
            userDict["username"] = credentialsObj['username']
            userDict["password"] = credentialsObj['password']
            userDict["type"] = credentialsObj['credentialType']
            usersList.append(userDict)
    except Exception as error:
        logger.error("There is an issue looking up credentials for the mappings provided - " + str(error))
    return usersList

def virtualImage(name,node_list,clusterId,task,origName):
    '''
    Function used to save the Virtual Image to the DB used by the UI and the TAF testware
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such cluster: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(message)
    try:
        if task == "edit":
            if VirtualImage.objects.filter(name=origName,cluster=clusterObj.id).exists():
                virtualImageObj = VirtualImage.objects.get(name=origName,cluster=clusterObj.id)
            else:
                message = "There was an issue with the editing the Virtual image data unable to find Virtual image. Exception " + str(e)
                logger.error(message)
                return ("1",message)
            virtualImageObj.name = name
            virtualImageObj.node_list = node_list
            virtualImageObj.save(force_update=True)
        else:
            virtualImageObj = VirtualImage.objects.create(name=name,node_list=node_list,cluster=clusterObj)
    except Exception as e:
        message = "There was an issue with the saving the Virtual image data. Exception " + str(e)
        logger.error(message)
        return ("1",message)
    return ("0","Success")

def getVirtualImageData(virtualImageId):
    '''
    Function used to get the info back for the virtual image
    '''
    if VirtualImageInfoIp.objects.filter(id=virtualImageId).exists():
        virtualImgObj = VirtualImageInfoIp.objects.get(id=virtualImageId)
        number = virtualImgObj.number
        hostname = virtualImgObj.hostname
        if hostname == None:
            hostname = ""
        if virtualImgObj.ipMap.address != None:
            address = virtualImgObj.ipMap.address
        else:
            address = virtualImgObj.ipMap.ipv6_address
    return (number,hostname,address)

def createInstallGroupDeployment(clusterId,installGroupId):
    '''
    Function to add a new install group Deployment
    '''
    try:
        installGroupObj = InstallGroup.objects.get(id=installGroupId)
        clusterObj = Cluster.objects.get(id=clusterId)
        statusObj = DeploymentStatus.objects.get(cluster=clusterObj)
        installGroupDeploymentObj = ClusterToInstallGroupMapping.objects.create(group=installGroupObj,cluster=clusterObj,status=statusObj)
    except Exception as e:
        message = str(e)
        logger.error("Unable to add the new Deployment to the install Group, Exception : " + str(message))
        return ("1",message)
    return ("0","Success")

def editInstallGroupDeployment(clusterId,installGroupId):
    '''
    Function to edit a install group deployment
    '''
    try:
        installGroupDeploymentObj = ClusterToInstallGroupMapping.objects.get(group=installGroupId)
        clusterObj = Cluster.objects.get(id=clusterId)
        installGroupDeploymentObj.cluster = clusterObj
        installGroupDeploymentObj.save(force_update=True)
    except Exception as e:
        message = str(e)
        logger.error("Unable to edit the deployment on the install Group, Exception : " + str(message))
        return ("1",message)
    return ("0","Success")

def createInstallGroup(installGroup):
    '''
    Function to add a new install group
    '''
    try:
        installGroupObj = InstallGroup.objects.create(installGroup=installGroup)
    except Exception as e:
        message = str(e)
        logger.error("Unable to add the new install Group " + str(installGroup) + ", Exception :  " + str(message))
        return ("1",message)
    return ("0","Success")

def editInstallGroup(installGroup,installGroupId):
    '''
    Function to edit a install group
    '''
    try:
        installGroupObj = InstallGroup.objects.get(id=installGroupId)
        installGroupObj.installGroup = installGroup
        installGroupObj.save(force_update=True)
    except Exception as e:
        message = str(e)
        logger.error("Unable to edit the install Group " + str(installGroup) + ", Exception :  " + str(message))
        return ("1",message)
    return ("0","Success")

def createVirtualImageIp(address,ipType,number,hostname,cluster_id,vmName,virtualImageIpType):
    '''
    Function used to save the Virtual Image IP Addresses to the DB used by the UI and the TAF testware
    Inputs address,ipType,number,hostname this is the data for saving
    cluster_id,vmName is used to set the virtualImageObj
    virtualImageIpType used to tell which type of IP it is internal ipv6 etc.

    '''
    try:
        clusterObj = Cluster.objects.get(id=cluster_id)
        hardwareType = clusterObj.management_server.server.hardware_type
    except Exception as e:
        message = "No such cluster: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(message)
        return ("1",message)

    if "cloud" in hardwareType:
        ipv4Identifier = ipv6Identifier = clusterObj.id
    else:
        ipv4Identifier = ipv6Identifier = '1'

    try:
        virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterObj.id)
        ipType="virtualImage_" + str(virtualImageIpType) + "_" + str(virtualImageObj.id)
    except Exception as e:
        message = "Issue getting Virtual Image information for " + str(vmName) + " within utils, Exception :  " + str(e)
        logger.error(message)
        return ("1",message)
    try:
        if virtualImageIpType == "internal" or virtualImageIpType == "jgroup" or virtualImageIpType == "ipv6Internal":
            ipv4Identifier = ipv6Identifier = clusterObj.id

        override = checkForDuplicateVirtualImageIpInfo(virtualImageIpType, address, ipv4Identifier, ipv6Identifier, virtualImageObj, cluster_id)
        virtualImageIpObj = None
        foundInSerivcesIps = findIpInClusterSerivces(clusterObj, address)
        if not override and foundInSerivcesIps:
            message = "There was an issue with the saving the IP address: " + str(address) + " - could be already in use. Please check and try again"
            logger.error(message)
            return ("1",message)
        try:
            if virtualImageIpType == "internal":
                virtualImageIpObj = IpAddress.objects.create(override=override, address=address,ipType=ipType,ipv4UniqueIdentifier=clusterObj.id)
            elif virtualImageIpType == "jgroup":
                virtualImageIpObj = IpAddress.objects.create(override=override, address=address,ipType=ipType,ipv4UniqueIdentifier=clusterObj.id)
            elif virtualImageIpType == "ipv6Public":
                virtualImageIpObj = IpAddress.objects.create(override=override, ipv6_address=address,ipType=ipType,ipv6UniqueIdentifier=ipv6Identifier)
            elif virtualImageIpType == "ipv6Internal":
                virtualImageIpObj = IpAddress.objects.create(override=override, ipv6_address=address,ipType=ipType,ipv6UniqueIdentifier=clusterObj.id)
            else:
                virtualImageIpObj = IpAddress.objects.create(override=override, address=address,ipType=ipType,ipv4UniqueIdentifier=ipv4Identifier)
        except Exception as e:
            message = "There was an issue with the saving the IP address: " + str(address) + " - could be already in use. Please check and try again, Exception: " + str(e)
            logger.error(message)
            return ("1",message)
        virtualImageMapObj = VirtualImageInfoIp.objects.create(number=number,hostname=hostname,virtual_image=virtualImageObj,ipMap=virtualImageIpObj)
    except Exception as e:
        message = "There was an issue with the saving the IP address "+ str(address) + " - " + str(e)
        logger.error(message)
        return ("1",message)
    return ("0","Success")

def editVirtualImageIp(address,ipType,number,hostname,cluster_id,virtualImageIpMapObj,virtualImageIpType):
    '''
    Function used to update the Virtual Image IP Addresses to the DB used by the UI and the TAF testware
    '''
    try:
        clusterObj = Cluster.objects.get(id=cluster_id)
        hardwareType = clusterObj.management_server.server.hardware_type
    except Exception as e:
        message = "No such cluster: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(message)
        return ("1",message)

    if "cloud" in hardwareType:
        ipv4Identifier = ipv6Identifier = clusterObj.id
    else:
        ipv4Identifier = ipv6Identifier = '1'

    try:
        message = "There was an issue with the saving the IP address: " + str(address) + " - could be already in use. Please check and try again"
        if virtualImageIpType == "internal" or virtualImageIpType == "jgroup" or virtualImageIpType == "ipv6Internal":
            ipv4Identifier = ipv6Identifier = clusterObj.id
        foundInSerivcesIps = findIpInClusterSerivces(clusterObj, address)
        override = checkForDuplicateVirtualImageIpInfo(virtualImageIpType, address, ipv4Identifier, ipv6Identifier, virtualImageIpMapObj.virtual_image, cluster_id)
        if VirtualImageInfoIp.objects.filter(id=virtualImageIpMapObj.id).exists():
            virtualImgIpObj = VirtualImageInfoIp.objects.get(id=virtualImageIpMapObj.id)
            virtualImgIpObj.hostname = hostname

            if IpAddress.objects.filter(id=virtualImgIpObj.ipMap_id).exists():
                ipObj = IpAddress.objects.get(id=virtualImgIpObj.ipMap_id)
                ipObj.override = override
                if "ipv6" in virtualImageIpType:
                    if not override and (int(IPAddress(address)) != int(IPAddress(dmt.utils.normalizedIpv6Postfix(ipObj.ipv6_address)))) and foundInSerivcesIps:
                        logger.error(message)
                        return ("1",message)
                    ipObj.ipv6_address = address
                else:
                    if not override and (address != ipObj.address) and foundInSerivcesIps:
                        logger.error(message)
                        return ("1",message)
                    ipObj.address = address
            else:
                if not override and foundInSerivcesIps:
                    logger.error(message)
                    return ("1",message)
                if "ipv6" in virtualImageIpType:
                    ipObj = IpAddress.objects.create(override=override,ipv6_address=address,ipType=ipType,ipv6UniqueIdentifier=ipv6Identifier)
                else:
                    ipObj = IpAddress.objects.create(override=override,address=address,ipType=ipType,ipv4UniqueIdentifier=ipv4Identifier)
            ipObj.save(force_update=True)
            virtualImgIpObj.save(force_update=True)
            return ("0","Success")
        else:
            message = "There was an issue with the saving of the Virtual Image IP unable to find mapping for Virtual Machine"
            logger.error(message)
            return ("1",message)
    except Exception as e:
        message = "There was an issue with the saving of the Virtual Image IP data within the utils file see function editVirtualImageIp " + str(e)
        logger.error(message)
        return ("1",message)

def getAvailableVirtualImageIPNumber(cluster_id,vmName,ipType):
    '''
    Function used to assign the next available number to the ip assigned
    Inputs the Cluster_id and the VM Name e.g. APSERV
    '''
    try:
        clusterObj = Cluster.objects.get(id=cluster_id)
    except Exception as e:
        message = "No such cluster: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(message)
    try:
        virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterObj.id)
    except Exception as e:
        message = "Issue getting Virtual Image information for " + str(vmName) + " within utils, Exception :  " + str(e)
        logger.error(message)
    if ipType == "public":
        virtualImageNumbers = VirtualImageInfoIp.objects.filter(virtual_image_id=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_public").order_by('number')
    elif ipType == "ipv6Public":
        virtualImageNumbers = VirtualImageInfoIp.objects.filter(virtual_image_id=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_ipv6Public").order_by('number')
    elif ipType == "storage":
        virtualImageNumbers = VirtualImageInfoIp.objects.filter(virtual_image_id=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_storage").order_by('number')
    elif ipType == "internal":
        virtualImageNumbers = VirtualImageInfoIp.objects.filter(virtual_image_id=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_internal").order_by('number')
    elif ipType == "ipv6Internal":
        virtualImageNumbers = VirtualImageInfoIp.objects.filter(virtual_image_id=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_ipv6Internal").order_by('number')
    elif ipType == "jgroup":
        virtualImageNumbers = VirtualImageInfoIp.objects.filter(virtual_image_id=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_jgroup").order_by('number')
    x = 1
    for item in virtualImageNumbers:
        number = item.number
        if int(number) != int(x):
            number = str(x)
            return number
        x = x +1
    number = str(x)
    return number

def clusterDetailsVirtualimagedata(clusterId):
    '''
    Function to gather the virtual image info for the cluster
    '''
    virtualImageInfo = []
    requiredVirtualImageFields = ('id', 'name', 'node_list')
    virtualImages = VirtualImage.objects.filter(cluster_id=clusterId).order_by('name').only(requiredVirtualImageFields).values(*requiredVirtualImageFields)

    requiredVirtualImageItemFields = ('id', 'name', 'layout')
    virtualImageItems = VirtualImageItems.objects.all().only(requiredVirtualImageItemFields).values(*requiredVirtualImageItemFields)

    virtualImageIds=[]
    for virtualImage in virtualImages:
        virtualImageIds.append(virtualImage['id'])

    requiredVirtualImageInfoIpFields = ('id', 'number', 'hostname', 'ipMap__address', 'ipMap__ipv6_address', 'virtual_image_id')
    allIpPublicItems = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds, ipMap__ipType__startswith="virtualImage_public").only(requiredVirtualImageInfoIpFields).values(*requiredVirtualImageInfoIpFields)

    allIpPublicIpv6Items = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds, ipMap__ipType__startswith="virtualImage_ipv6Public").only(requiredVirtualImageInfoIpFields).values(*requiredVirtualImageInfoIpFields)

    allIpStorageItems = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds, ipMap__ipType__startswith="virtualImage_storage").only(requiredVirtualImageInfoIpFields).values(*requiredVirtualImageInfoIpFields)

    allIpInternalItems = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds, ipMap__ipType__startswith="virtualImage_internal").only(requiredVirtualImageInfoIpFields).values(*requiredVirtualImageInfoIpFields)

    allIpInternalIpv6Items = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds, ipMap__ipType__startswith="virtualImage_ipv6Internal").only(requiredVirtualImageInfoIpFields).values(*requiredVirtualImageInfoIpFields)

    allIpJGroupItems = VirtualImageInfoIp.objects.filter(virtual_image_id__in=virtualImageIds, ipMap__ipType__startswith="virtualImage_jgroup").only(requiredVirtualImageInfoIpFields).values(*requiredVirtualImageInfoIpFields)

    requiredCredentialMappingFields = ('id', 'virtualimage_id', 'credentials__id', 'credentials__username', 'credentials__password','credentials__credentialType')
    allCredentialsItems = VirtualImageCredentialMapping.objects.filter(virtualimage_id__in=virtualImageIds).only(requiredCredentialMappingFields).values(*requiredCredentialMappingFields)

    for virtualImage in virtualImages:
        for virtualImageItem in virtualImageItems:
            if virtualImageItem['name'] == virtualImage['name']:
                virtualImageType = virtualImageItem['layout']
                break

        vmIpPublicItems = []
        for ipPublicItem in allIpPublicItems:
            if ipPublicItem['virtual_image_id'] == virtualImage['id']:
                vmIpPublicItems.append(ipPublicItem)

        vmIpPublicIpv6Items = []
        for ipPublicIpv6Item in allIpPublicIpv6Items:
            if ipPublicIpv6Item['virtual_image_id'] == virtualImage['id']:
                vmIpPublicIpv6Items.append(ipPublicIpv6Item)

        vmIpStorageItems = []
        for ipStorageItem in allIpStorageItems:
            if ipStorageItem['virtual_image_id'] == virtualImage['id']:
                vmIpStorageItems.append(ipStorageItem)

        vmIpInternalItems = []
        for ipInternalItem in allIpInternalItems:
            if ipInternalItem['virtual_image_id'] == virtualImage['id']:
                vmIpInternalItems.append(ipInternalItem)

        vmIpInternalIpv6Items = []
        for ipInternalIpv6Item in allIpInternalIpv6Items:
            if ipInternalIpv6Item['virtual_image_id'] == virtualImage['id']:
                vmIpInternalIpv6Items.append(ipInternalIpv6Item)

        vmIpJGroupItems = []
        for ipJGroupItem in allIpJGroupItems:
            if ipJGroupItem['virtual_image_id'] == virtualImage['id']:
                vmIpJGroupItems.append(ipJGroupItem)

        vmCredentialsItems = []
        for vmCredentialsItem in allCredentialsItems:
            if vmCredentialsItem['virtualimage_id'] == virtualImage['id']:
                vmCredentialsItems.append(vmCredentialsItem)

        data = {
            'virtualImage': virtualImage,
            'virtualImageType': virtualImageType,
            'vmIpPublicObj': vmIpPublicItems,
            'vmIpPublicIpv6Obj': vmIpPublicIpv6Items,
            'vmIpStorageObj': vmIpStorageItems,
            'vmIpInternalObj': vmIpInternalItems,
            'vmIpInternalIpv6Obj': vmIpInternalIpv6Items,
            'vmIpJGroupObj': vmIpJGroupItems,
            "credentialsList": vmCredentialsItems
        }
        virtualImageInfo.append(data)
    return virtualImageInfo

def editServerCredentials(username,password,credType,serverId,credentialId):
    '''
    Function to edit the server credentials
    '''
    try:
        userExists = False
        mappings = ClusterServerCredentialMapping.objects.filter(clusterServer__id=serverId)
        for map in mappings:
            if int(map.credentials.id) != int(credentialId) and map.credentials.username == username:
                userExists = True
        if userExists:
            message = "User already exists, please use another user name."
            logger.error(message)
            return ("1",message)
    except Exception as e:
        message = "Unable to check user names. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

    try:
        credentialObj = Credentials.objects.get(id=credentialId)
    except Exception as e:
        message = "Unable to find the specified server credentials within the DB"
        logger.error(message + ', Error: ' + str(e))
        return ("1",message)
    try:
        credentialObj.username = username
        credentialObj.password = password
        credentialObj.type = credType
        credentialObj.save(force_update=True)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue editing the server credentials Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def createServerCredentials(username,password,credType,clusterServerId,user):
    '''
    Function to create the server credentials
    '''
    try:
        try:
            clusterServerObj = ClusterServer.objects.get(id=int(clusterServerId))
        except Exception as e:
            message = "Unable to find the cluster server specified within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        try:
            userExists = False
            mappings = ClusterServerCredentialMapping.objects.filter(clusterServer=clusterServerObj)
            for map in mappings:
                if map.credentials.username == username:
                    userExists = True
            if userExists:
                message = "User already exists, please use another user name."
                logger.error(message)
                return ("1",message)
        except Exception as e:
            message = "Unable to check user names. Exception: " + str(e)
            logger.error(message)
            return ("1",message)

        credential = Credentials.objects.create(username=username, password=password, credentialType=credType)
        dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clusterServerCredMap = ClusterServerCredentialMapping.objects.create(clusterServer=clusterServerObj, credentials=credential, signum=user, date_time=dateTime)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the server credentials Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def editMgmtServerCredentials(username,password,credType,mgmtServerObjId,credentialId):
    '''
    Function to edit the server credentials
    '''
    try:
        userExists = False
        mappings = ManagementServerCredentialMapping.objects.filter(mgtServer__id=mgmtServerObjId)
        for map in mappings:
            if int(map.credentials.id) != int(credentialId) and map.credentials.username == username:
                userExists = True
        if userExists:
            message = "User already exists, please use another user name."
            logger.error(message)
            return ("1",message)
    except Exception as e:
        message = "Unable to check user names. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

    try:
        credentialObj = Credentials.objects.get(id=credentialId)
    except Exception as e:
        message = "Unable to find the specified server credentials within the DB"
        logger.error(message + ', Error: ' + str(e))
        return ("1",message)
    try:
        credentialObj.username = username
        credentialObj.password = password
        credentialObj.type = credType
        credentialObj.save(force_update=True)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue editing the server credentials Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def createMgmtServerCredentials(username,password,credType,mgmtServerId,user):
    '''
    Function to create the server credentials
    '''
    try:
        try:
            mgmtServerObj = ManagementServer.objects.get(id=mgmtServerId)
        except Exception as e:
            message = "Unable to find the management server specified within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        try:
            userExists = False
            mappings = ManagementServerCredentialMapping.objects.filter(mgtServer=mgmtServerObj)
            for map in mappings:
                if map.credentials.username == username:
                    userExists = True
            if userExists:
                message = "User already exists, please use another user name."
                logger.error(message)
                return ("1",message)
        except Exception as e:
            message = "Unable to check user names. Exception: " + str(e)
            logger.error(message)
            return ("1",message)

        credential = Credentials.objects.create(username=username, password=password, credentialType=credType)
        dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mgmtServerCredMap = ManagementServerCredentialMapping.objects.create(mgtServer=mgmtServerObj, credentials=credential, signum=user, date_time=dateTime)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the management server credentials, Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def editVirtualImageCredentials(username,password,credType,vmName,clusterId,credentialId):
    '''
    Function to edit the virtual image credentials
    Inputs:
        username, password, credType
        vmname and clusterObj.id is used to get the virtual Image map object
        credentialId used to get the credentials with the credential table
    '''
    try:
        if VirtualImage.objects.filter(name=vmName,cluster=clusterId).exists():
            virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterId)
        else:
            message = "Unable to find the virtual image specified within the DB"
            logger.error(message)
            return ("1",message)
        if VirtualImageCredentialMapping.objects.filter(virtualimage=virtualImageObj,credentials=credentialId).exists():
            virtualImageCredMapObj = VirtualImageCredentialMapping.objects.get(virtualimage=virtualImageObj,credentials=credentialId)
            if Credentials.objects.filter(id=virtualImageCredMapObj.credentials_id).exists():
                credentialObj = Credentials.objects.get(id=virtualImageCredMapObj.credentials_id)
            else:
                message = "Unable to find the virtual image credentials mapping to credentials within the DB"
                logger.error(message)
                return ("1",message)
        else:
            message = "Unable to find the virtual image credentials specified within the DB"
            logger.error(message)
            return ("1",message)
        credentialObj.username = username
        credentialObj.password = password
        credentialObj.type = credType
        credentialObj.save(force_update=True)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue editing the virtual image credentials Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def createVirtualImageCredentials(username,password,credType,vmName,clusterId,user):
    '''
    Function to create the virtual image credentials
    Inputs:
        username, password, credType
        vmname and clusterObj.id is used to get the virtual Image map object
        and the user to get the signum of the current user
    '''
    try:
        if VirtualImage.objects.filter(name=vmName,cluster=clusterId).exists():
            virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterId)
        else:
            message = "Unable to find the virtual image specified within the DB"
            logger.error(message)
            return ("1",message)
        credential = Credentials.objects.create(username=username, password=password, credentialType=credType)
        dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        virtualImageCredMap = VirtualImageCredentialMapping.objects.create(virtualimage=virtualImageObj, credentials=credential, signum=user, date_time=dateTime)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the virtual image credentials Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def findNodeForService(vmToServices, virtualImageName):
    '''
    Function to find node service belongs to based on info from DD info.txt file
    '''
    listOfNodes = []
    try:
        if "_" in virtualImageName:
            splitService = virtualImageName.rsplit('_', 1)
            checkService = splitService[0]
            checkServiceNumber = int((splitService)[1])
            listOfNodes = cycleInfoDictForNodes(vmToServices, checkService, "list")
            listOfNodes = sort_alphanumeric_list(listOfNodes)
            nodeFound = listOfNodes[checkServiceNumber-1]
            return ("0", nodeFound.upper())
        else:
            nodeFound = cycleInfoDictForNodes(vmToServices, virtualImageName, "node")
            return ("0", nodeFound.upper())
        return ("1", "None")
    except Exception as e:
        logger.error("There was an issue finding the node for service " + virtualImageName + " Exception: " + str(e))
        return ("1", "None")

def cycleInfoDictForNodes(dict, checkService, returnType):
    '''
    Function to cycle through dict for DD info xml and find node(s)
    '''
    listOfNodes = []
    for node, services in dict.iteritems():
        for service in services:
            vimage = re.sub('[^A-Za-z0-9-]+', '', service)
            if checkService == vimage:
                if returnType is "list":
                    listOfNodes.append(node)
                else:
                    return node
    return listOfNodes

def checkForServiceInDDInfo(servicesToVmList, virtualImageName):
    '''
    Function to find node service exists based on info from DD info.txt file
    '''
    if "_" in virtualImageName:
        checkService = virtualImageName.rsplit('_', 1)[0]
    else:
        checkService = virtualImageName

    for node, services in servicesToVmList.iteritems():
        for service in services:
            vimage = re.sub('[^A-Za-z0-9-]+', '', service)
            if checkService == vimage:
                return True

    return False

def checkForServiceInDDXml(ddServicesXmlList, virtualImageName):
    '''
    Function to find node service exists based on info from DD xml file
    '''
    serviceIsInDDXml = False

    for service in ddServicesXmlList:
        service = service.rsplit('_', 2)[0]
        if virtualImageName == service:
            serviceIsInDDXml = True
            break

    return serviceIsInDDXml

def sort_alphanumeric_list(list):
    '''
    Function to sort a list of alphanumeric values in a list based on the number
    '''
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(list, key = alphanum_key)

def editClusterMulticast(enmMesAddress,udpMultiAddress,enmMesPort,udpMultiPort,clusterId):
    '''
    Function to add the multicast information to the cluster
    '''
    try:
        if Cluster.objects.filter(id=clusterId).exists():
            clusterObj = Cluster.objects.get(id=clusterId)
            hardwareType = clusterObj.management_server.server.hardware_type
        else:
            message = "No such cluster ID can be found when editing the cluster multicast info : " + str(clusterId)
            logger.error(message)
            return ("1",message)

        if "cloud" in hardwareType:
            ipv4Identifier = ipv6Identifier = clusterObj.id
        else:
            ipv4Identifier = ipv6Identifier = '1'

        if ClusterMulticast.objects.filter(cluster_id=clusterObj.id).exists():
            clusterMulticast = ClusterMulticast.objects.get(cluster_id=clusterObj.id)
        else:
            message = "No Multicast Information can be found for saving, contact Admin if the issue persists"
            logger.error(message)
            return ("1",message)

        if IpAddress.objects.filter(id=clusterMulticast.enm_messaging_address_id).exists():
            enmMesAddressObj = IpAddress.objects.get(id=clusterMulticast.enm_messaging_address_id)
        else:
            message = "No Multicast Information can be found for ENM Messaging Address, contact Admin if the issue persists"
            logger.error(message)
            return ("1",message)

        if IpAddress.objects.filter(id=clusterMulticast.udp_multicast_address_id).exists():
            udpAddressObj = IpAddress.objects.get(id=clusterMulticast.udp_multicast_address_id)
        else:
            message = "No Multicast Information can be found for UDP Multicast Address, contact Admin if the issue persists"
            logger.error(message)
            return ("1",message)

        enmMesAddressObj.address = enmMesAddress
        udpAddressObj.address = udpMultiAddress
        clusterMulticast.enm_messaging_port = enmMesPort
        clusterMulticast.udp_multicast_port = udpMultiPort

        enmMesAddressObj.save(force_update=True)
        udpAddressObj.save(force_update=True)
        clusterMulticast.save(force_update=True)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue editing the multicast information for the cluster. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def createClusterMulticast(enmMesAddress,udpMultiAddress,enmMesPort,udpMultiPort,clusterId):
    '''
    Function to add the multicast information to the cluster
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
        hardwareType = clusterObj.management_server.server.hardware_type
    except Exception as e:
        message = "No such cluster ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return ("1",message)

    try:
        if ClusterMulticast.objects.filter(cluster=clusterObj).exists():
            message = "No duplicate multicast info allowed."
            logger.error(message)
            return ("1",message)
    except Exception as e:
        message = "Failed to check duplicate Cluster Multicast: " + str(e)
        logger.error(message)
        return ("1",message)

    if "cloud" in hardwareType:
        ipv4Identifier = ipv6Identifier = clusterObj.id
    else:
        ipv4Identifier = ipv6Identifier = '1'

    try:
        enmMessagingAddressObj = IpAddress.objects.create(\
                address=str(enmMesAddress),\
                ipType="clusterMulticast_" + str(clusterObj.id),ipv4UniqueIdentifier=ipv4Identifier)
        udpAddressObj = IpAddress.objects.create(\
                address=str(udpMultiAddress),\
                ipType="clusterMulticast_" + str(clusterObj.id),ipv4UniqueIdentifier=ipv4Identifier)

        multicastObj = ClusterMulticast.objects.create(\
            enm_messaging_address=enmMessagingAddressObj,\
            enm_messaging_port=str(enmMesPort),\
            udp_multicast_address=udpAddressObj,\
            udp_multicast_port=str(udpMultiPort),\
            cluster=clusterObj)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the multicast information to the cluster. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def editDatabaseVip(postgresAddress,versantAddress,mysqlAddress,opendjAddress,opendjAddress2,jmsAddress,eSearchAddress,neo4jAddress1,neo4jAddress2,neo4jAddress3,gossipRouterAddress1,gossipRouterAddress2,eshistoryAddress,clusterId):
    '''
    Function to edit the Database VIP Address information to the cluster
    '''
    try:
        if Cluster.objects.filter(id=clusterId).exists():
            clusterObj = Cluster.objects.get(id=clusterId)
        else:
            message = "No such cluster ID can be found when editing the database VIP address info : " + str(clusterId)
            logger.error(message)
            return ("1",message)

        databaseVipObj,created = DatabaseVips.objects.get_or_create(cluster_id=clusterObj.id)

        if IpAddress.objects.filter(id=databaseVipObj.postgres_address_id).exists():
            postgresAddressObj = IpAddress.objects.get(id=databaseVipObj.postgres_address_id)
            postgresAddressObj.address = postgresAddress
            postgresAddressObj.save(force_update=True)
        else:
            postgresAddressObj = IpAddress.objects.create(address=str(postgresAddress),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.postgres_address_id=postgresAddressObj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.versant_address_id).exists():
            versantAddressObj = IpAddress.objects.get(id=databaseVipObj.versant_address_id)
            versantAddressObj.address = versantAddress
            versantAddressObj.save(force_update=True)
        else:
            versantAddressObj = IpAddress.objects.create(address=str(versantAddress),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.versant_address_id=versantAddressObj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.mysql_address_id).exists():
            mysqlAddressObj = IpAddress.objects.get(id=databaseVipObj.mysql_address_id)
            mysqlAddressObj.address = mysqlAddress
            mysqlAddressObj.save(force_update=True)
        else:
            mysqlAddressObj = IpAddress.objects.create(address=str(mysqlAddress),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.mysql_address_id=mysqlAddressObj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.opendj_address_id).exists():
            opendjAddressObj = IpAddress.objects.get(id=databaseVipObj.opendj_address_id)
            opendjAddressObj.address = opendjAddress
            opendjAddressObj.save(force_update=True)
        else:
            opendjAddressObj = IpAddress.objects.create(address=str(opendjAddress),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.opendj_address_id=opendjAddressObj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.opendj_address2_id).exists():
            opendjAddress2Obj = IpAddress.objects.get(id=databaseVipObj.opendj_address2_id)
            opendjAddress2Obj.address = opendjAddress2
            opendjAddress2Obj.save(force_update=True)
        else:
            opendjAddress2Obj = IpAddress.objects.create(address=str(opendjAddress2),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.opendj_address2_id=opendjAddress2Obj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.jms_address_id).exists():
            jmsAddressObj = IpAddress.objects.get(id=databaseVipObj.jms_address_id)
            jmsAddressObj.address = jmsAddress
            jmsAddressObj.save(force_update=True)
        else:
            jmsAddressObj = IpAddress.objects.create(address=str(jmsAddress),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.jms_address_id=jmsAddressObj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.eSearch_address_id).exists():
            eSearchAddressObj = IpAddress.objects.get(id=databaseVipObj.eSearch_address_id)
            eSearchAddressObj.address = eSearchAddress
            eSearchAddressObj.save(force_update=True)
        else:
            eSearchAddressObj = IpAddress.objects.create(address=str(eSearchAddress),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.eSearch_address_id=eSearchAddressObj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.neo4j_address1_id).exists():
            neo4jAddress1Obj = IpAddress.objects.get(id=databaseVipObj.neo4j_address1_id)
            neo4jAddress1Obj.address = neo4jAddress1
            neo4jAddress1Obj.save(force_update=True)
        else:
            neo4jAddress1Obj = IpAddress.objects.create(address=str(neo4jAddress1),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.neo4j_address1_id=neo4jAddress1Obj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.neo4j_address2_id).exists():
            neo4jAddress2Obj = IpAddress.objects.get(id=databaseVipObj.neo4j_address2_id)
            neo4jAddress2Obj.address = neo4jAddress2
            neo4jAddress2Obj.save(force_update=True)
        else:
            neo4jAddress2Obj = IpAddress.objects.create(address=str(neo4jAddress2),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.neo4j_address2_id=neo4jAddress2Obj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.neo4j_address3_id).exists():
            neo4jAddress3Obj = IpAddress.objects.get(id=databaseVipObj.neo4j_address3_id)
            neo4jAddress3Obj.address = neo4jAddress3
            neo4jAddress3Obj.save(force_update=True)
        else:
            neo4jAddress3Obj = IpAddress.objects.create(address=str(neo4jAddress3),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.neo4j_address3_id=neo4jAddress3Obj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.gossipRouter_address1_id).exists():
            gossipRouterAddress1Obj = IpAddress.objects.get(id=databaseVipObj.gossipRouter_address1_id)
            gossipRouterAddress1Obj.address = gossipRouterAddress1
            gossipRouterAddress1Obj.save(force_update=True)
        else:
            gossipRouterAddress1Obj = IpAddress.objects.create(address=str(gossipRouterAddress1),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.gossipRouter_address1_id=gossipRouterAddress1Obj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.gossipRouter_address2_id).exists():
            gossipRouterAddress2Obj = IpAddress.objects.get(id=databaseVipObj.gossipRouter_address2_id)
            gossipRouterAddress2Obj.address = gossipRouterAddress2
            gossipRouterAddress2Obj.save(force_update=True)
        else:
            gossipRouterAddress2Obj = IpAddress.objects.create(address=str(gossipRouterAddress2),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.gossipRouter_address2_id=gossipRouterAddress2Obj.id
            databaseVipObj.save(force_update=True)

        if IpAddress.objects.filter(id=databaseVipObj.eshistory_address_id).exists():
            eshistoryAddressObj = IpAddress.objects.get(id=databaseVipObj.eshistory_address_id)
            eshistoryAddressObj.address = eshistoryAddress
            eshistoryAddressObj.save(force_update=True)
        else:
            eshistoryAddressObj = IpAddress.objects.create(address=str(eshistoryAddress),ipType="databaseVip_" + str(clusterObj.id),ipv4UniqueIdentifier=clusterObj.id)
            databaseVipObj.eshistory_address_id=eshistoryAddressObj.id
            databaseVipObj.save(force_update=True)

        return ("0","Success")
    except Exception as e:
        message = "There was an issue editing the Database VIP information for the cluster. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def createDatabaseVip(postgresAddress,versantAddress,mysqlAddress,opendjAddress,opendjAddress2,jmsAddress,eSearchAddress,neo4jAddress1,neo4jAddress2,neo4jAddress3,gossipRouterAddress1,gossipRouterAddress2,eshistoryAddress,clusterId):
    '''
    Function to add the database VIP information to the cluster
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such cluster ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return ("1",message)
    try:
        postgresAddressObj = IpAddress.objects.create(\
                address=str(postgresAddress),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        versantAddressObj = IpAddress.objects.create(\
                address=str(versantAddress),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        mysqlAddressObj = IpAddress.objects.create(\
                address=str(mysqlAddress),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        opendjAddressObj = IpAddress.objects.create(\
                address=str(opendjAddress),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        if opendjAddress2:
            opendjAddressObj2 = IpAddress.objects.create(\
                    address=str(opendjAddress2),\
                    ipType="databaseVip_" + str(clusterObj.id),\
                    ipv4UniqueIdentifier=clusterObj.id)
        else:
            opendjAddressObj2 = None
        jmsAddressObj = IpAddress.objects.create(\
                address=str(jmsAddress),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        eSearchAddressObj = IpAddress.objects.create(\
                address=str(eSearchAddress),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        neo4jAddress1Obj = IpAddress.objects.create(\
                address=str(neo4jAddress1),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        neo4jAddress2Obj = IpAddress.objects.create(\
                address=str(neo4jAddress2),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        neo4jAddress3Obj = IpAddress.objects.create(\
                address=str(neo4jAddress3),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        gossipRouterAddress1Obj = IpAddress.objects.create(\
                address=str(gossipRouterAddress1),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        gossipRouterAddress2Obj = IpAddress.objects.create(\
                address=str(gossipRouterAddress2),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        eshistoryAddressObj = IpAddress.objects.create(\
                address=str(eshistoryAddress),\
                ipType="databaseVip_" + str(clusterObj.id),\
                ipv4UniqueIdentifier=clusterObj.id)
        databaseVipObj = DatabaseVips.objects.create(\
            postgres_address=postgresAddressObj,\
            versant_address=versantAddressObj,\
            mysql_address=mysqlAddressObj,\
            opendj_address=opendjAddressObj,\
            opendj_address2=opendjAddressObj2,\
            jms_address=jmsAddressObj,\
            eSearch_address=eSearchAddressObj,\
            neo4j_address1=neo4jAddress1Obj,\
            neo4j_address2=neo4jAddress2Obj,\
            neo4j_address3=neo4jAddress3Obj,\
            gossipRouter_address1=gossipRouterAddress1Obj,\
            gossipRouter_address2=gossipRouterAddress2Obj,\
            eshistory_address=eshistoryAddressObj,\
            cluster=clusterObj)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the database VIP information to the cluster. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def addEnclosure(hostname,domain_name,vc_domain_name,username,password,ip1,ip2,vcUsername,vcPassword,vcIp1,vcIp2,sanSwUsername,sanSwPassword,sanSwIp1,sanSwIp2,uplink_A_port1,uplink_A_port2,uplink_B_port1,uplink_B_port2,rackName,name,san_sw_bay_1,san_sw_bay_2,vc_module_bay_1,vc_module_bay_2):
    '''
    Function used to add the onboard admin and the virtual connect info for a blade enclosure
    '''
    try:
        vcCredentialsObj = None
        #Create IP addresses of Onboard Administrator IPAddress Table
        ipaddr1 = IpAddress.objects.create(address=ip1,ipType="enclosure")
        ipaddr2 = IpAddress.objects.create(address=ip2,ipType="enclosure")
        #Create Credentials
        credentials = Credentials.objects.create(username=username, password=password)
        #Create IP addresses of Onboard Administrator IPAddress Table
        if vcIp1 != None:
            vcIp1Obj = IpAddress.objects.create(address=vcIp1,ipType="vc_enclosure")
        if vcIp2 != None:
            vcIp2Obj = IpAddress.objects.create(address=vcIp2,ipType="vc_enclosure")
        #Create Credentials
        if vcUsername != None and vcPassword != None:
            vcCredentialsObj = Credentials.objects.create(username=vcUsername, password=vcPassword)
        #Create IP addresses for SAN SW
        if sanSwIp1 != None:
            sanSwIp1Obj = IpAddress.objects.create(address=sanSwIp1,ipType="sanSw_enclosure")
        if sanSwIp2 != None:
            sanSwIp2Obj = IpAddress.objects.create(address=sanSwIp2,ipType="sanSw_enclosure")
        #Create Credentials
        if sanSwUsername != None and sanSwPassword != None:
            sanSwCredentialsObj = Credentials.objects.create(username=sanSwUsername, password=sanSwPassword)
        #Create Entry for Enclosure
        enclosure = Enclosure.objects.create(hostname=hostname,domain_name=domain_name,vc_domain_name=vc_domain_name,rackName=rackName,name=name,credentials=credentials,vc_credentials=vcCredentialsObj,sanSw_credentials=sanSwCredentialsObj,uplink_A_port1=uplink_A_port1,uplink_A_port2=uplink_A_port2,uplink_B_port1=uplink_B_port1,uplink_B_port2=uplink_B_port2,san_sw_bay_1=san_sw_bay_1,san_sw_bay_2=san_sw_bay_2,vc_module_bay_1=vc_module_bay_1,vc_module_bay_2=vc_module_bay_2)
        #Add mapping of Clraiion ip addresses to ipaddress table entry
        map1 = EnclosureIPMapping.objects.create(enclosure=enclosure, ipaddr=ipaddr1, ipnumber=1)
        map2 = EnclosureIPMapping.objects.create(enclosure=enclosure, ipaddr=ipaddr2, ipnumber=2)
        if vcIp1 != None:
            map3 = EnclosureIPMapping.objects.create(enclosure=enclosure, ipaddr=vcIp1Obj, ipnumber=3)
        if vcIp2 != None:
            map4 = EnclosureIPMapping.objects.create(enclosure=enclosure, ipaddr=vcIp2Obj, ipnumber=4)
        if sanSwIp1 != None:
            map5 = EnclosureIPMapping.objects.create(enclosure=enclosure, ipaddr=sanSwIp1Obj, ipnumber=5)
        if sanSwIp2 != None:
            map6 = EnclosureIPMapping.objects.create(enclosure=enclosure, ipaddr=sanSwIp2Obj, ipnumber=6)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the enclosure information. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def createVlanDetails(clusterId,task, vlanDetailsValues):
    '''
    function to create the vlan details
    '''
    if Cluster.objects.filter(id=clusterId).exists():
        clusterObj = Cluster.objects.get(id=clusterId)
    else:
        message = "No such cluster ID: " + str(clusterId)
        logger.error(message)
        return ("1",message)
    layoutName = clusterObj.layout
    layoutObj = ClusterLayout.objects.get(name=layoutName)
    serviceSubnet = vlanDetailsValues['serviceSubnet']
    servicesGateway = vlanDetailsValues['servicesGateway']
    serviceIpv6Gateway=vlanDetailsValues['serviceIpv6Gateway']
    serviceIpv6Subnet=vlanDetailsValues['serviceIpv6Subnet']
    storageSubnet = vlanDetailsValues['storageSubnet']
    returnMessage, storageGateway = createStorageGateway(str(vlanDetailsValues['storageGateway']))
    if returnMessage != "Success":
        return ("1",returnMessage)
    backupSubnet =vlanDetailsValues['backupSubnet']
    jgroupsSubnet =vlanDetailsValues['jgroupsSubnet']
    internalSubnet=vlanDetailsValues['internalSubnet']
    internalIPv6Subnet = None if vlanDetailsValues['internalIPv6Subnet'] == None or vlanDetailsValues['internalIPv6Subnet'] == "" else vlanDetailsValues['internalIPv6Subnet']
    hbaVlan = None if vlanDetailsValues['hbaVlan'] == "" or vlanDetailsValues['hbaVlan'] == None else vlanDetailsValues['hbaVlan']
    hbbVlan = None if vlanDetailsValues['hbbVlan'] == "" or vlanDetailsValues['hbbVlan'] == None else vlanDetailsValues['hbbVlan']
    storageVlan= None if vlanDetailsValues['storageVlan'] == "" or vlanDetailsValues['storageVlan'] == None else vlanDetailsValues['storageVlan']
    backupVlan= None if vlanDetailsValues['backupVlan'] == "" or vlanDetailsValues['backupVlan'] == None else vlanDetailsValues['backupVlan']
    jgroupsVlan= None if vlanDetailsValues['jgroupsVlan'] == "" or vlanDetailsValues['jgroupsVlan'] == None else vlanDetailsValues['jgroupsVlan']
    internalVlan= None if vlanDetailsValues['internalVlan'] == "" or vlanDetailsValues['internalVlan'] == None else vlanDetailsValues['internalVlan']
    servicesVlan= None if vlanDetailsValues['servicesVlan'] == "" or vlanDetailsValues['servicesVlan'] == None else vlanDetailsValues['servicesVlan']
    managementVlan= None if vlanDetailsValues['managementVlan'] == "" or vlanDetailsValues['managementVlan'] == None else vlanDetailsValues['managementVlan']
    litpManagement= None if vlanDetailsValues['litpManagement'] == "" or vlanDetailsValues['litpManagement'] == None else vlanDetailsValues['litpManagement']
    vlanObj = VlanDetails.objects.create(cluster=clusterObj, hbAVlan=hbaVlan, hbBVlan=hbbVlan,
        services_subnet=serviceSubnet, services_gateway=servicesGateway,
        services_ipv6_gateway=serviceIpv6Gateway, services_ipv6_subnet=serviceIpv6Subnet,
        storage_subnet=storageSubnet, backup_subnet=backupSubnet,
        jgroups_subnet=jgroupsSubnet, internal_subnet=internalSubnet,
        internal_ipv6_subnet=internalIPv6Subnet, storage_vlan=storageVlan,
        backup_vlan=backupVlan, jgroups_vlan=jgroupsVlan,
        internal_vlan=internalVlan, services_vlan=servicesVlan,
        management_vlan=managementVlan, litp_management=litpManagement,
        storage_gateway=storageGateway
    )
    if layoutObj.id == 1:
        virtualConnectNetworksObj = VirtualConnectNetworks.objects.create(vlanDetails=vlanObj)
    return ("0","Success")

def editVlanDetails(clusterId,task,vlanDetailsValues):
    '''
    function to edit the vlan details
    '''
    if Cluster.objects.filter(id=clusterId).exists():
        clusterObj = Cluster.objects.get(id=clusterId)
    else:
        message = "No such cluster ID: " + str(clusterId)
        logger.error(message)
        return ("1",message)
    layoutName = clusterObj.layout
    layoutObj = ClusterLayout.objects.get(name=layoutName)
    if VlanDetails.objects.filter(cluster_id=clusterObj.id).exists():
        vlanObj = VlanDetails.objects.get(cluster_id=clusterObj.id)
    else:
        message = "There was an issue editing the vlan Details. Exception: " + str(e)
        logger.error(message)
        return ("1",message)
    returnMessage, storageGateway = editStorageGateway(vlanObj, str(vlanDetailsValues['storageGateway']))
    if returnMessage != "Success":
        return ("1", returnMessage)
    vlanObj.services_subnet=vlanDetailsValues['serviceSubnet']
    vlanObj.services_gateway=vlanDetailsValues['servicesGateway']
    vlanObj.services_ipv6_gateway=vlanDetailsValues['serviceIpv6Gateway']
    vlanObj.services_ipv6_subnet=vlanDetailsValues['serviceIpv6Subnet']
    vlanObj.storage_subnet=vlanDetailsValues['storageSubnet']
    vlanObj.storage_gateway=storageGateway
    vlanObj.backup_subnet=vlanDetailsValues['backupSubnet']
    vlanObj.jgroups_subnet=vlanDetailsValues['jgroupsSubnet']
    vlanObj.internal_subnet=vlanDetailsValues['internalSubnet']
    vlanObj.internal_ipv6_subnet = None if vlanDetailsValues['internalIPv6Subnet'] == None or vlanDetailsValues['internalIPv6Subnet'] == "" else vlanDetailsValues['internalIPv6Subnet']
    vlanObj.hbAVlan = None if vlanDetailsValues['hbaVlan'] == "" or vlanDetailsValues['hbaVlan'] == None else vlanDetailsValues['hbaVlan']
    vlanObj.hbBVlan = None if vlanDetailsValues['hbbVlan'] == "" or vlanDetailsValues['hbbVlan'] == None else vlanDetailsValues['hbbVlan']
    vlanObj.storage_vlan = None if vlanDetailsValues['storageVlan'] == "" or vlanDetailsValues['storageVlan'] == None else vlanDetailsValues['storageVlan']
    vlanObj.backup_vlan = None if vlanDetailsValues['backupVlan'] == "" or vlanDetailsValues['backupVlan'] == None else vlanDetailsValues['backupVlan']
    vlanObj.jgroups_vlan = None if vlanDetailsValues['jgroupsVlan'] == "" or vlanDetailsValues['jgroupsVlan'] == None else vlanDetailsValues['jgroupsVlan']
    vlanObj.internal_vlan = None if vlanDetailsValues['internalVlan'] == "" or vlanDetailsValues['internalVlan'] == None else vlanDetailsValues['internalVlan']
    vlanObj.services_vlan = None if vlanDetailsValues['servicesVlan'] == "" or vlanDetailsValues['servicesVlan'] == None else vlanDetailsValues['servicesVlan']
    vlanObj.management_vlan = None if vlanDetailsValues['managementVlan'] == "" or vlanDetailsValues['managementVlan'] == None else vlanDetailsValues['managementVlan']
    vlanObj.litp_management= None if vlanDetailsValues['litpManagement'] == "" or vlanDetailsValues['litpManagement'] == None else vlanDetailsValues['litpManagement']
    vlanObj.save(force_update=True)
    if layoutObj.id == 1:
        if not VirtualConnectNetworks.objects.filter(vlanDetails=vlanObj).exists():
            virtualConnectNetworksObj = VirtualConnectNetworks.objects.create(vlanDetails=vlanObj)
    return ("0","Success")

def createStorageGateway(storageGateway):
    storageGateway = storageGateway.strip()
    if storageGateway == '':
        return "Success", None
    isIpAddrNotUnique = checkAddressIsUnique("public", storageGateway, 1)
    if isIpAddrNotUnique:
        return "Storage gateway of " + storageGateway + " is not unique, please ensure public IP adresses are unique.", None
    return "Success", IpAddress.objects.create(address=storageGateway, ipType="storage_gateway", ipv4UniqueIdentifier=1)

def editStorageGateway(vlanObj, newStorageGateway):
    '''
        Function used to edit or create a VLAN IP object that must be unique
    '''
    newStorageGateway = newStorageGateway.strip()
    if newStorageGateway == '':
        deleteStorageGatewayObjIfExists(vlanObj)
        return "Success", None

    if IpAddress.objects.filter(id=vlanObj.storage_gateway_id).exists():
        oldStorageGateway = IpAddress.objects.get(id=vlanObj.storage_gateway_id)
    else:
        oldStorageGateway = None

    storageGatewayChanged = True if str(oldStorageGateway) != str(newStorageGateway) else False
    if not storageGatewayChanged:
        return "Success", oldStorageGateway

    isIpAddrNotUnique = checkAddressIsUnique("public", newStorageGateway, 1)
    if isIpAddrNotUnique:
        return "Storage gateway of " + newStorageGateway + " is not unique, please ensure public IP adresses are unique.", None

    if IpAddress.objects.filter(id=vlanObj.storage_gateway_id).exists():
        oldStorageGateway.address = newStorageGateway
        oldStorageGateway.save(force_update=True)
        return "Success", oldStorageGateway
    else:
        return "Success", IpAddress.objects.create(address=newStorageGateway, ipType="storage_gateway", ipv4UniqueIdentifier=1)

def deleteStorageGatewayObjIfExists(vlanObj):
    '''
        Function used to delete storage gateway object if it exists
    '''
    if IpAddress.objects.filter(id=vlanObj.storage_gateway_id).exists():
        storageGateway = IpAddress.objects.get(id=vlanObj.storage_gateway_id)
        logger.info("Deleting storage gateway: " + str(storageGateway))
        storageGateway.delete()
        vlanObj.storage_gateway = None
        vlanObj.save()


def editServiceIpRange(task,startIp,endIp,ipType,rangeId):
    '''
    Function used to edit the VM Service IP Ranges to the DB
    '''
    try:
        vmServiceIpRangeItemObj = VmServiceIpRangeItem.objects.get(ipType=ipType)
    except Exception as e:
        message = "No such VM Service Range Item: " + str(ipType) + ". Exception: " + str(e)
        logger.error(message)
        return ("1",message)
    try:
        if VmServiceIpRange.objects.filter(id=rangeId).exists():
            VmServiceIpRangeObj = VmServiceIpRange.objects.get(id=rangeId)
            if "ipv6" in ipType.lower():
                VmServiceIpRangeObj.ipv6AddressStart = startIp
                VmServiceIpRangeObj.ipv6AddressEnd = endIp
            else:
                VmServiceIpRangeObj.ipv4AddressStart = startIp
                VmServiceIpRangeObj.ipv4AddressEnd = endIp
            VmServiceIpRangeObj.ipTypeId = vmServiceIpRangeItemObj
            VmServiceIpRangeObj.save(force_update=True)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the edited vm service ip range details. Exception: " + str(e)
        return ("1","Error")

def addServiceIpRange(clusterId,task,startIp,endIp,ipType):
    '''
    Function used to add the VM Service IP Ranges to the DB
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such cluster ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return ("1",message)
    try:
        vmServiceIpRangeItemObj = VmServiceIpRangeItem.objects.get(ipType=ipType)
    except Exception as e:
        message = "No such VM Service Range Item: " + str(ipType) + ". Exception: " + str(e)
        logger.error(message)
        return ("1",message)
    try:
        if "ipv6" in ipType.lower():
            ipRangeObj = VmServiceIpRange.objects.create(
                ipv6AddressStart=startIp,
                ipv6AddressEnd=endIp,
                ipTypeId=vmServiceIpRangeItemObj,
                cluster=clusterObj
            )
        else:
            ipRangeObj = VmServiceIpRange.objects.create(
                ipv4AddressStart=startIp,
                ipv4AddressEnd=endIp,
                ipTypeId=vmServiceIpRangeItemObj,
                cluster=clusterObj
            )
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the added vm service ip range details. Exception: " + str(e)
        return ("1",message)

def createVirtualConnectDetails(clusterId,sharedUplinkSetA,sharedUplinkSetB,servicesA,servicesB,storageA,storageB,backupA,backupB,jgroups,jgroupsA,jgroupsB,internalA,internalB,heartbeat1,heartbeat2,heartbeat1A,heartbeat2B):
    '''
    function to edit the virtual connect details
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such cluster ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return ("1",message)
    try:
        if VlanDetails.objects.filter(cluster_id=clusterObj.id).exists():
            vlanObj = VlanDetails.objects.get(cluster_id=clusterObj.id)
            virtualConnectObj = VirtualConnectNetworks.objects.create(
                vlanDetails=vlanObj,
                sharedUplinkSetA = sharedUplinkSetA,
                sharedUplinkSetB = sharedUplinkSetB,
                servicesA = servicesA,
                servicesB = servicesB,
                storageA = storageA,
                storageB = storageB,
                backupA = backupA,
                backupB = backupB,
                jgroups = jgroups,
                jgroupsA = jgroupsA,
                jgroupsB = jgroupsB,
                internalA = internalA,
                internalB = internalB,
                heartbeat1 = heartbeat1,
                heartbeat2 = heartbeat2,
                heartbeat1A = heartbeat1A,
                heartbeat2B = heartbeat2B
            )
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the vlan Details. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def editVirtualConnectDetails(clusterId,sharedUplinkSetA,sharedUplinkSetB,servicesA,servicesB,storageA,storageB,backupA,backupB,jgroups,jgroupsA,jgroupsB,internalA,internalB,heartbeat1,heartbeat2,heartbeat1A,heartbeat2B):
    '''
    function to edit the virtual connect details
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such cluster ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return ("1",message)
    try:
        if VlanDetails.objects.filter(cluster_id=clusterObj.id).exists():
            vlanObj = VlanDetails.objects.get(cluster_id=clusterObj.id)
            if VirtualConnectNetworks.objects.filter(vlanDetails_id=vlanObj.id).exists():
                virtualConnectObj = VirtualConnectNetworks.objects.get(vlanDetails_id=vlanObj.id)
                virtualConnectObj.sharedUplinkSetA = sharedUplinkSetA
                virtualConnectObj.sharedUplinkSetB = sharedUplinkSetB
                virtualConnectObj.servicesA = servicesA
                virtualConnectObj.servicesB = servicesB
                virtualConnectObj.storageA = storageA
                virtualConnectObj.storageB = storageB
                virtualConnectObj.backupA = backupA
                virtualConnectObj.backupB = backupB
                virtualConnectObj.jgroups = jgroups
                virtualConnectObj.jgroupsA = jgroupsA
                virtualConnectObj.jgroupsB = jgroupsB
                virtualConnectObj.internalA = internalA
                virtualConnectObj.internalB = internalB
                virtualConnectObj.heartbeat1 = heartbeat1
                virtualConnectObj.heartbeat2 = heartbeat2
                virtualConnectObj.heartbeat1A = heartbeat1A
                virtualConnectObj.heartbeat2B = heartbeat2B
                virtualConnectObj.save(force_update=True)
                return ("0","Success")
            else:
                message = "There was an issue editing the vlan Details. Exception: " + str(e)
                logger.error(message)
                return ("1",message)
        else:
            message = "There was an issue editing the vlan Details. Exception: " + str(e)
            logger.error(message)
            return ("1",message)
    except Exception as e:
        message = "There was an issue editing the vlan Details. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def deleteVirtualImage(clusterId, vmName):
    '''
    Deletes the specified virtual image and associated info attached
    '''
    virtualImageCredMapObj = None
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such cluster: " + str(clusterId) + ", Exception :  " + str(e)
        return("1",message)
    try:
        virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterObj.id)
    except Exception as e:
        message = "Issue getting Virtual Image information for " + str(vmName) + " Exception :  " + str(e)
        return("1",message)
    try:
        virtualImageIpObj = VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id)
    except Exception as e:
        message = "Issue getting Virtual Image Ip information for " + str(vmName) + " within utils, Exception :  " + str(e)
        return("1",message)
    try:
        if VirtualImageCredentialMapping.objects.filter(virtualimage=virtualImageObj).exists():
            virtualImageCredMapObj = VirtualImageCredentialMapping.objects.filter(virtualimage=virtualImageObj)
            # Get a list of all the vm credentails according to the cred mapping
            vmCredObj = []
            for credMap in virtualImageCredMapObj:
                vmCredObj += Credentials.objects.filter(id=credMap.credentials_id)
    except Exception as e:
        message = "Issue getting Virtual Image Credentials information for " + str(vmName) + " Exception :  " + str(e)
        return("1",message)

    # Get a list of all the vm ips according to the vm ip mapping
    vmIpObj = []
    for ipMap in virtualImageIpObj:
        vmIpObj += IpAddress.objects.filter(id=ipMap.ipMap_id)
    try:
        if virtualImageCredMapObj != None:
            virtualImageCredMapObj.delete()
            for vmCred in vmCredObj:
                vmCred.delete()
        for vmMap in virtualImageIpObj:
            vmMap.delete()
        for ip in vmIpObj:
            ip.delete()
        virtualImageObj.delete()
        return("0","SUCCESS")
    except Exception as e:
        message = "Issue deleting some of the virtual image data for " + str(vmName) + " Exception :  " + str(e)
        return("1",message)

def obsoleteFunctionNotifier(message):
    sender = config.get('CIFWK', 'cifwkDistributionList')
    subject = ("Notification of usage of obsolete function: Needs Action")
    message = (str(message))
    email = [config.get('CIFWK', 'upgrade_email')]
    try:
        send_mail(subject,message,sender,email, fail_silently=False)
    except Exception as e:
        logger.error("Issue sending email " + str(e))

def getServerTypes(productType, layout):

    '''
    Getting the Node/ServerTypes
    '''
    nodeList = []

    prodServTypes = ProductToServerTypeMapping.objects.filter(product__name=productType)
    if productType != "OSS-RC":
        for type in prodServTypes:
            if layout.id == 1:
                if not ("SC-" in str(type.serverType) or "PL-" in str(type.serverType)):
                    nodeList.append(type)
            elif layout.id == 2:
                if not ("SVC" in str(type.serverType) or "DB" in str(type.serverType) or "SCP" in str(type.serverType)):
                    nodeList.append(type)
    else:
        nodeList = ProductToServerTypeMapping.objects.filter(product__name=productType)
    nodeList.sort(key = lambda x: x.serverType)
    return nodeList

def getDeployScriptVersion(drop, osVersion=None):
    '''
    Function used to calculate the deployment script version according to the drop or OS if one specified
    '''
    deployScriptMappingObj = None
    if osVersion != None:
        osVersion = osVersion.split("::")[0]
        if DeployScriptMapping.objects.filter(reference=osVersion).exists():
            logger.info("Getting deploy script version from DB for OS specified")
            deployScriptMappingObj = DeployScriptMapping.objects.get(reference=osVersion)
    if drop != None:
        drop = drop.split("::")[0]
        if DeployScriptMapping.objects.filter(reference=drop).exists():
            logger.info("Getting deploy script version from DB for drop specified")
            deployScriptMappingObj = DeployScriptMapping.objects.get(reference=drop)
        elif deployScriptMappingObj == None and Drop.objects.filter(release__product__name='ENM',name=drop).exists():
                dropInfo = Drop.objects.get(release__product__name='ENM',name=drop)
                mediaArtifacts =  cireports.utils.getMediaBaseline(dropInfo.id)
                dropMediaDeployMaps = cireports.utils.getDropMediaDeployMappings(mediaArtifacts)
                for mapping in dropMediaDeployMaps:
                    if mapping['deployType'] == 'os':
                        if redHatArtifactToVersionMapping.objects.filter(mediaArtifact__name=mapping['mediaArtifact']).exists():
                            osInfo = redHatArtifactToVersionMapping.objects.get(mediaArtifact__name=mapping['mediaArtifact'])
                            if DeployScriptMapping.objects.filter(reference=osInfo.artifactReference).exists():
                                logger.info("Getting deploy script version from DB for drop's OS")
                                deployScriptMappingObj = DeployScriptMapping.objects.get(reference=osInfo.artifactReference)
                                break
        if DeployScriptMapping.objects.filter(reference='master').exists() and deployScriptMappingObj == None:
            logger.info("Getting deploy script version from DB specified as master")
            deployScriptMappingObj = DeployScriptMapping.objects.get(reference='master')
    else:
        if DeployScriptMapping.objects.filter(reference='master').exists() and deployScriptMappingObj == None:
            logger.info("Getting deploy script version from DB specified as master")
            deployScriptMappingObj = DeployScriptMapping.objects.get(reference='master')
    if deployScriptMappingObj != None:
        version = deployScriptMappingObj.version
    else:
        version = None
    return version

def addSanInfoToTAFHostPropertiesJSON(clusterId,line):
    '''
    This function creates a dictionary to be added to TAF Host properties Json
    '''
    if Cluster.objects.filter(id=clusterId).exists():
        clusterObj = Cluster.objects.get(id=clusterId)
        if ClusterToStorageMapping.objects.filter(cluster=clusterObj).exists():
            sanServerDict = {}
            sanStorage=ClusterToStorageMapping.objects.get(cluster=clusterObj).storage
            sanCreds = sanStorage.credentials
            sanServerDict["jgroups"] = "<JGROUPS>"
            sanServerDict["heartbeat1"] = "<HEARTBEAT1>"
            sanServerDict["heartbeat2"] = "<HEARTBEAT2>"
            sanServerDict["san_systemName"] = "<STORAGE_HOSTNAME>"
            sanServerDict["san_spaIP"] = "<STORAGE_IPADRESS_1>"
            sanServerDict["san_spbIP"] = "<STORAGE_IPADRESS_2>"
            sanServerDict["san_user"] = "<STORAGE_USERNAME>"
            sanServerDict["san_password"] = "<STORAGE_PASSWORD>"
            sanServerDict["san_type"] = "<STORAGE_VNXTYPE>"
            sanServerDict["san_serial"] = "<SAN_SERIAL_NUMBER>"
            sanServerDict["san_loginScope"] = sanCreds.loginScope
            sanServerDict["san_fenRGID"] = "<STORAGE_POOL_RAID_GROUP>"
            sanServerDict["san_siteId"] = "<STORAGE_POOL_NAME>"
            sanServerDict["san_poolId"] = "<STORAGE_POOL_ID>"
            sanServerDict["san_poolName"] = "<STORAGE_POOL_NAME>"
            sanServerDict["sfs_console_IP"] = "<NAS_IP_ADDRESS>"
            sanServerDict["sfs_console_username"] = "<NAS_MASTER_USERNAME>"
            sanServerDict["sfs_console_password"] = "<NAS_MASTER_PASSWORD>"
            sanServerDict["sfssetup_hostname"] = "<NAS_HOSTNAME>"
            sanServerDict["sfssetup_username"] = "<NAS_SUPPORT_USERNAME>"
            sanServerDict["sfssetup_password"] = "<NAS_SUPPORT_PASSWORD>"
            sanServerDict["ENM_sfs_storage_pool_name"] = "<NAS_STORAGE_POOL>"
            sanServerDict["nas_vip_pm"] = "<NAS_VIP_SEG1>"
            sanServerDict["nas_vip_enm_"] = "<NAS_VIP_CLOG>"
            sanServerDict["nas_vip_enm_2"] = "<NAS_VIP_TOR1>"
            sanServerDict["nas_type"] = "<STORAGE_NAS_TYPE>"
            sanServerDict["enclosure1_OAIP1"] = "<ENCLOSURE1_IP1>"
            sanServerDict["enclosure1_OAIP2"] = "<ENCLOSURE1_IP2>"
            sanServerDict["enclosure1_username"] = "<ENCLOSURE1_USERNAME>"
            sanServerDict["enclosure1_password"] = "<ENCLOSURE1_PASSWORD>"
            sanServerDict["enclosure1_uplink_A_port1"] = "<ENCLOSURE1_UPLINK_A_PORT_1>"
            sanServerDict["enclosure1_uplink_A_port2"] = "<ENCLOSURE1_UPLINK_A_PORT_2>"
            sanServerDict["enclosure1_uplink_B_port1"] = "<ENCLOSURE1_UPLINK_B_PORT_1>"
            sanServerDict["enclosure1_uplink_B_port2"] = "<ENCLOSURE1_UPLINK_B_PORT_2>"
            sanServerDict["enclosure2_OAIP1"] = "<ENCLOSURE2_IP1>"
            sanServerDict["enclosure2_OAIP2"]="<ENCLOSURE2_IP2>"
            sanServerDict["enclosure2_username"]="<ENCLOSURE2_USERNAME>"
            sanServerDict["enclosure2_password"]="<ENCLOSURE2_PASSWORD>"
            sanServerDict["enclosure2_uplink_A_port1"] = "<ENCLOSURE2_UPLINK_A_PORT_1>"
            sanServerDict["enclosure2_uplink_A_port2"] = "<ENCLOSURE2_UPLINK_A_PORT_2>"
            sanServerDict["enclosure2_uplink_B_port1"] = "<ENCLOSURE2_UPLINK_B_PORT_1>"
            sanServerDict["enclosure2_uplink_B_port2"] = "<ENCLOSURE2_UPLINK_B_PORT_2>"

            sanServerDict["enclosure1_VC_IP1"]="<ENCLOSURE1_VC_IP1>"
            sanServerDict["enclosure1_VC_IP2"]="<ENCLOSURE1_VC_IP2>"
            sanServerDict["enclosure1_VC_username"]="<ENCLOSURE1_VC_USERNAME>"
            sanServerDict["enclosure1_VC_password"]="<ENCLOSURE1_VC_PASSWORD>"
            sanServerDict["enclosure1_VC_domain"]="<ENCLOSURE1_VC_DOMAIN>"
            sanServerDict["enclosure2_VC_IP1"]="<ENCLOSURE2_VC_IP1>"
            sanServerDict["enclosure2_VC_IP2"]="<ENCLOSURE2_VC_IP2>"
            sanServerDict["enclosure2_VC_username"]="<ENCLOSURE2_VC_USERNAME>"
            sanServerDict["enclosure2_VC_password"]="<ENCLOSURE2_VC_PASSWORD>"
            sanServerDict["enclosure2_VC_domain"]="<ENCLOSURE2_VC_DOMAIN>"

            sanServerDict["enclosure1_SANSW_IP1"]="<ENCLOSURE1_SANSW_IP1>"
            sanServerDict["enclosure1_SANSW_IP2"]="<ENCLOSURE1_SANSW_IP2>"
            sanServerDict["enclosure1_SANSW_username"]="<ENCLOSURE1_SANSW_USERNAME>"
            sanServerDict["enclosure1_SANSW_password"]="<ENCLOSURE1_SANSW_PASSWORD>"
            sanServerDict["enclosure2_SANSW_IP1"]="<ENCLOSURE2_SANSW_IP1>"
            sanServerDict["enclosure2_SANSW_IP2"]="<ENCLOSURE2_SANSW_IP2>"
            sanServerDict["enclosure2_SANSW_username"]="<ENCLOSURE2_SANSW_USERNAME>"
            sanServerDict["enclosure2_SANSW_password"]="<ENCLOSURE2_SANSW_PASSWORD>"

            line.append(dict(sanServerDict))
    else:
        raise Exception("Cluster Id "+clusterId+" does not exist")
    return line


def ipCheckClusterAndMgtServer(mgtServer, cluster):
    '''
    Checking IP address on the mgtServer and cluster for validation
    '''
    mgtServerIPs = set()
    clusterSerIPs = set()
    sameIP = ""
    mgtServerObj = mgtServer.server
    warning = ""
    try:
        if NetworkInterface.objects.filter(server=mgtServerObj).exists():
            mgtserverNics = NetworkInterface.objects.only("server__id").filter(server__id=mgtServerObj.id)
            for nic in mgtserverNics:
                if IpAddress.objects.filter(nic__id=nic.id).exists():
                    ipAddrs = IpAddress.objects.filter(nic__id=nic.id)
                    for ip in ipAddrs:
                        mgtServerIPs.add(ip.address)
        if ClusterServer.objects.filter(cluster=cluster).exists():
            clusterSers = ClusterServer.objects.filter(cluster__id=cluster.id)
            for clusterServerObj in clusterSers:
                if NetworkInterface.objects.filter(server__id=clusterServerObj.server.id).exists():
                    clusterServerNics = NetworkInterface.objects.only("server__id").filter(server__id=clusterServerObj.server.id)
                    for nic in clusterServerNics:
                        if IpAddress.objects.filter(nic__id=nic.id).exists():
                           ipAddrs = IpAddress.objects.filter(nic__id=nic.id)
                           for ip in ipAddrs:
                               clusterSerIPs.add(ip.address)
        for mgtSerIP in mgtServerIPs:
            if mgtSerIP in clusterSerIPs:
                sameIP = str(mgtSerIP)
                break
    except Exception as e:
        logger.error("Issue Checking IP addresses: " + str(e))
    if sameIP:
        warning = "Warning: Duplicate Internal IP Address " + sameIP + " found in the Management Server and Deployment."
    return warning

def cleanOutDirectoryArea(areaToClean, deleteAfterTime, searchString=None):
    '''
    This is used to clean out a certain area on the file system if the content is over a certain amount of days
    inputs:
        areaToClean: Area to Clean
        timeAfterTime: Remove files older that X days
        searchString: Directories to delete start with e.g. /tmp/temp*
            If searchString Not give everything is deleted in the given areaToClean
    '''
    today = date.today()
    for root, dirs, files in os.walk(areaToClean):
        for name in dirs:
            delete = None
            fileDate = date.fromtimestamp(os.path.getmtime(os.path.join(root, name)))
            if searchString != None:
                if searchString in name:
                    if (today - fileDate).days >= deleteAfterTime:
                        delete = os.path.join(areaToClean, name)
            else:
                if (today - fileDate).days >= deleteAfterTime:
                    delete = os.path.join(areaToClean, name)
            if delete != None:
                try:
                    shutil.rmtree(delete)
                    logger.info("Temp Directory: " + str(delete) + " Deleted")
                except Exception as e:
                    process = subprocess.Popen("sudo rm -rf " + str(delete), stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
                    outputData, returnCode = process.communicate()[0], process.returncode
                    logger.info("Temp Directory: " + str(delete) + " Deleted")
                    if not returnCode == 0:
                        logger.error("Issue with deleting: " + str(delete) + ", output: " +str(outputData))
                        return 1
        break
    return 0

def getChangeLogSort(dateSort, contentType, id=None):
    '''
    Sorting the Change Log Data
    '''
    dateInfo = datetime.now()

    if dateSort == "All":
       if id:
           return LogEntry.objects.select_related('id').filter(content_type=contentType, object_id=id).order_by('-action_time')
       else:
           return  LogEntry.objects.select_related('id').filter(content_type=contentType).order_by('-action_time')
    elif dateSort == "Today":
        if id:
            return  LogEntry.objects.select_related('id').filter(content_type=contentType, object_id=id, action_time__year=dateInfo.year, action_time__month=dateInfo.month, action_time__day=dateInfo.day).order_by('-action_time')
        else:
            return  LogEntry.objects.select_related('id').filter(content_type=contentType, action_time__year=dateInfo.year, action_time__month=dateInfo.month, action_time__day=dateInfo.day).order_by('-action_time')
    elif dateSort == "Week":
        if id:
            return  LogEntry.objects.select_related('id').filter(content_type=contentType, object_id=id, action_time__gte=dateInfo-timedelta(days=7)).order_by('-action_time')
        else:
            return  LogEntry.objects.select_related('id').filter(content_type=contentType, action_time__gte=dateInfo-timedelta(days=7)).order_by('-action_time')
    elif dateSort == "Month":
        if id:
            return LogEntry.objects.select_related('id').filter(content_type=contentType, object_id=id, action_time__gte=dateInfo-timedelta(days=31)).order_by('-action_time')
        else:
            return LogEntry.objects.select_related('id').filter(content_type=contentType,  action_time__gte=dateInfo-timedelta(days=31)).order_by('-action_time')


def getChangeLogDetails(type, dateSort, id):
    '''
    Function used to get the change Log information
    '''
    sorting = ""

    logDetails = []
    logs = []

    if type == "deploymentserver":
        clusterObj = Cluster.objects.get(id=id)
        displayName = "Change Log for Deployment \"" + str(clusterObj.name) + "\" Details"
        # Gat all the deployment general infomation for the Deployment
        contentTypeObj = ContentType.objects.get(model="cluster")
        contentType = contentTypeObj.id
        logDetails += getChangeLogSort(dateSort, contentType, id)
        # Get all the server infomation for the deployment
        clusterServerObject = ClusterServer.objects.filter(cluster_id=id)
        contentTypeObj = ContentType.objects.get(model="clusterserver")
        contentType = contentTypeObj.id
        for item in clusterServerObject:
            logDetails += getChangeLogSort(dateSort, contentType, item.id)
        # Get all the Virtual image information for the deployment
        virtualImageObj = VirtualImage.objects.filter(cluster_id=id)
        contentTypeObj = ContentType.objects.get(model="virtualimage")
        contentType = contentTypeObj.id
        for item in virtualImageObj:
            logDetails += getChangeLogSort(dateSort, contentType, item.id)
        logDetails.sort(key=lambda item: item.action_time, reverse=True)
    else:
        if type == "managementserver":
            displayName = "Change Log for Management Server Area"
        elif type == "nasserver":
            displayName = "Change Log for NAS Server Area"
        elif type == "storage":
            displayName = "Change Log for Storage Server Area"
        elif type == "enclosure":
            displayName = "Change Log for the Enclosure Area"
        elif type == "sed":
            displayName = "Change Log for SED Templates"
        contentTypeObj = ContentType.objects.get(model=type)
        contentType = contentTypeObj.id
        logDetails += getChangeLogSort(dateSort, contentType)

    data = {
            "logDetails": logDetails,
    }
    logs.append(data)

    return (logs,displayName)

def removePermissions(oldGroup,clusterObj):
    '''
    Function used to remove the permissions from the django guardian
    '''
    remove_perm('change_cluster_guardian', oldGroup, clusterObj)
    remove_perm('delete_cluster_guardian', oldGroup, clusterObj)

def addPermissons(newGroup,clusterObj):
    '''
    Function used to add permissions to the django guardian
    '''
    assign_perm('change_cluster_guardian', newGroup, clusterObj)
    assign_perm('delete_cluster_guardian', newGroup, clusterObj)

def retrieveDeploymentSystemInfo(clusterId,environment):
    '''
    Function used to retrieve the deployment information from the specified server
    '''
    drop="latest"
    cluster = Cluster.objects.get(id = clusterId)
    clusterName = cluster.name
    mgtServer = cluster.management_server
    fqdnMgtServer = mgtServer.server.hostname + "." + mgtServer.server.domain_name

    user=config.get('DMT_AUTODEPLOY', 'user')
    masterUserPassword = config.get('DMT_AUTODEPLOY', 'masterPasswordCloudMS1')
    keyFileName=config.get('DMT_AUTODEPLOY', 'key')

    hostName = socket.gethostbyaddr(socket.gethostname())[0]

    errMsg = "Error: Unable to clean out the known host file for " + mgtServer.server.hostname
    ret = dmt.createSshConnection.cleanKnowHostFile(mgtServer)
    if ret != 0:
        return (ret,drop,errMsg)
    errMsg = "Unable to make a connection to the server"
    (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
    if (ret != 0):
        return (ret,drop,errMsg)
    errMsg = "Unable to get the pre installed ENM version"
    preInstalledVersion=config.get('DMT_AUTODEPLOY', 'preInstalledEnmVersionFile')
    (ret, commandOutput) = remoteConnection.runCmdGetOutput("cat " + str(preInstalledVersion))
    if (ret != 0):
        return (ret,drop,errMsg)
    commandOutputList = commandOutput.rsplit('\r')
    commandOutputList = list(map(str.strip,commandOutputList))
    commandOutputList = filter(None, commandOutputList)
    for item in commandOutputList:
        if "ENM" in item:
            preVersionList = item.split(' ')
            drop = preVersionList[1] + "::" + preVersionList[4]
            drop = drop.replace(")", "")
    return (0,drop,"SUCCESS")

def getFreeClusterInInstallGroupAndSetStatus(result):
    '''
    The getFreeClusterInInstallGroupAndSetStatus is a helper function for the GetFreeClusterFromGroupAndSetStatus Rest Call to return IDLE cluster ID and set cluster status to BUSY.
    '''
    deployment = {}
    response = {}
    if "error" not in str(result.lower()):
        deployment['clusterId'] = result
    else:
        deployment['error'] = result
    response['InstallGroupIDLECluster'] = deployment
    return response

def getTheResponseFromARestCall(url):
    '''
    Function used to execute a restcall and return the response
    '''
    try:
        response = urllib2.urlopen(url)
        responseString = response.read().decode('utf-8')
        jsonObj = json.loads(responseString)
        return (0,jsonObj)
    except Exception as e:
        logger.error("Unable to get the responce the rest call " + str(url))
        return (1,None)

def getReferenceIndexFromListObj(listObj,value):
    '''
    Function used to get the reference of an item in a list
    '''
    for listRef,lst in enumerate(listObj):
        for listItemRef,item in enumerate(lst):
            if item == value:
                return (0,listRef)
    return (1,None)

def packageFromISOJsonDiff(jsonObj,searchValue,listRef):
    '''
    Function used to get back the list of packages from the ISO diff rest according to search parameter given
    '''
    try:
        jsonData = jsonObj[listRef][searchValue]
        deployPackage = ""
        for item in jsonData:
            if deployPackage != "":
                deployPackage += "@@"
            deployPackage += item.get("artifactId") + "::" + item.get("version")
        return (0,str(deployPackage))
    except Exception as e:
        logger.error("Unable to retrieve deploy package information for the search paramater " + str(searchValue) + "from ISO Diff Rest call")
        return (1,None)

def getNodeType(nodeType):
    '''
    Function used to get the short name of the node type i.e. nodetype SCP-1 returns SCP
    '''
    try:
        if "-" in nodeType:
            nodeTypeCheck,number = nodeType.split("-")
        else:
            if (any(char.isdigit() for char in nodeType)):
                nodeTypeCheck = re.sub(r'[0-9]*', "", nodeType)
            else:
                nodeTypeCheck = nodeType
        return (0,nodeTypeCheck)
    except Exception as e:
        message = "Unable to get the short name for node type " + str(nodeType)
        return (1,message)

def ipRangeTypeCheck(startIp,endIp,ipType):
    '''
    Function used to check a given range of IP's to ensure the type of IP entered match
    '''
    try:
        if "ipv6" in ipType.lower():
            if ":" not in startIp or ":" not in endIp:
                message = "Error: The Ip Type choosen is IPv6 yet the inputted IP address do not seem to be IPv6"
                return (1,message)
        else:
            if "." not in startIp or "." not in endIp:
                message = "Error: The Ip Type choosen is IPv4 yet the inputted IP address do not seem to be IPv4"
                return (1,message)
        return (0,"SUCCESS")
    except Exception as e:
        message = "Issue execution the IP Range Type Check. Exception: " + str(e)
        return (1,message)

def ipRangeCheckStartLessThanEnd(startIp,endIp):
    '''
    Function used to ensure the start of a IP range is less than the end of the ip range, supports IPv4 and IPv6
    '''
    try:
        if int(IPAddress(startIp)) > int(IPAddress(endIp)):
            message = "Error: The Start Range seems to be higher than the End Range, Please investigate.."
            return (1,message)
        return (0,"SUCCESS")
    except Exception as e:
        message = "Issue execution the IP Range Check To Ensure Start IP is Less than End IP. Exception: " + str(e)
        return (1,message)

def parseSedForUnassignedServiceIps(sed,ddServiceVmList,populateDDorSED):
    '''
    Function used to get back the missing service VM entries with a generated sed from that deployment
    '''
    ipAddress = []
    ipv6Address = []
    storage = []
    internal = []
    jgroups = []
    ipv6Internal = []
    lines = sed.split('\n')
    virtualImageList = []
    fields = ("name",)
    virtualImageObj = VirtualImageItems.objects.only(fields).values(*fields).all()
    for item in virtualImageObj:
        for key, value in item.iteritems():
            virtualImageList.append(value)
    for virtualImageItem in virtualImageList:
        for line in lines:
            if not line.startswith(str(virtualImageItem) + "_"):
                continue
            if not ''.join(line.split('=')[1].split()) == "":
                continue
            if "ipaddress" in line and value not in ipAddress:
                value = parseSedLineForMissingIp(line,ddServiceVmList,populateDDorSED)
                if value != "None":
                    ipAddress.append(value)
                continue
            elif "ipv6_internal" in line:
                value = parseSedLineForMissingIp(line,ddServiceVmList,populateDDorSED)
                if value != "None" and value not in ipv6Internal:
                    ipv6Internal.append(value)
                    continue
            elif "internal" in line:
                value = parseSedLineForMissingIp(line,ddServiceVmList,populateDDorSED)
                if value != "None" and value not in internal:
                    internal.append(value)
                continue
            elif "storage" in line:
                value = parseSedLineForMissingIp(line,ddServiceVmList,populateDDorSED)
                if value != "None" and value not in storage:
                    storage.append(value)
                continue
            elif "jgroups" in line:
                value = parseSedLineForMissingIp(line,ddServiceVmList,populateDDorSED)
                if value != "None" and value not in jgroups:
                    jgroups.append(value)
                continue
            elif "ipv6address" in line:
                value = parseSedLineForMissingIp(line,ddServiceVmList,populateDDorSED)
                if value != "None" and value not in ipv6Address:
                    ipv6Address.append(value)
                continue
    result = {"IPv4 Public":ipAddress,"internal":internal,"IPv4 Storage":storage,"jgroups":jgroups,"IPv6 Public":ipv6Address, "IPv6 Internal": ipv6Internal}
    return (0,result)

def parseSedLineForMissingIp (line,ddServiceVmList,populateDDorSED):
    splitString = line.split('=')
    if ddServiceVmList != None:
        if "populatedd" in populateDDorSED.lower():
            if splitString[0] in ddServiceVmList:
                return splitString[0]
            else:
                return "None"
        else:
            return splitString[0]
    else:
        return splitString[0]

def createLVSRouterIP(lVSRouterValue, ipType, uniqueIdentifier, ipVer):
    '''
    Create IP address
    '''
    ipObj = None
    if ipVer == "ipv4":
      ipObj = None if lVSRouterValue == None or lVSRouterValue == "" else IpAddress.objects.create(address=str(lVSRouterValue), ipType=ipType, ipv4UniqueIdentifier=uniqueIdentifier)
    else:
      ipObj = None if lVSRouterValue == None or lVSRouterValue == "" else IpAddress.objects.create(ipv6_address=str(lVSRouterValue), ipType=ipType, ipv6UniqueIdentifier=uniqueIdentifier)
    return ipObj


def createLVSRouterVip(lVSRouterValues,clusterObj):
    '''
    Function to add the LVS Router VIP information to the cluster
    '''
    try:
        identifier = clusterObj.management_server.server.hardware_type
        if identifier == "cloud":
            publicIdentifier = clusterObj.id
        else:
            publicIdentifier = "1"

        ipType = "lvsRouterVip_" + str(clusterObj.id)
        ret, message = checkIfLVSRouterIPAddressAssigned(lVSRouterValues,clusterObj.id,publicIdentifier)
        if ret != 0:
            logger.error(message)
            return ("1",message)
        addressList = filter(None,lVSRouterValues.values())
        duplicates = getDuplicatesInList(addressList)
        if len(duplicates) > 0:
            raise Exception("Duplicate IP Info "+str(duplicates))

        #LVS Router VIP Addresses
        pmInternalObj = IpAddress.objects.create(address=str(lVSRouterValues['pmInternal']), ipType=ipType, ipv4UniqueIdentifier=clusterObj.id)
        pmExternalObj = IpAddress.objects.create(address=str(lVSRouterValues['pmExternal']), ipType=ipType, ipv4UniqueIdentifier=publicIdentifier)

        fmInternalObj = IpAddress.objects.create(address=str(lVSRouterValues['fmInternal']), ipType=ipType, ipv4UniqueIdentifier=clusterObj.id)
        fmExternalObj = IpAddress.objects.create(address=str(lVSRouterValues['fmExternal']), ipType=ipType, ipv4UniqueIdentifier=publicIdentifier)
        fmInternalIPv6Obj = createLVSRouterIP(lVSRouterValues['fmInternalIPv6'], ipType, clusterObj.id, "ipv6")
        fmExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['fmExternalIPv6'], ipType, publicIdentifier, "ipv6")

        cmInternalObj = IpAddress.objects.create(address=str(lVSRouterValues['cmInternal']), ipType=ipType, ipv4UniqueIdentifier=clusterObj.id)
        cmExternalObj = IpAddress.objects.create(address=str(lVSRouterValues['cmExternal']), ipType=ipType, ipv4UniqueIdentifier=publicIdentifier)
        cmInternalIPv6Obj = createLVSRouterIP(lVSRouterValues['cmInternalIPv6'], ipType, clusterObj.id, "ipv6")
        cmExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['cmExternalIPv6'], ipType, publicIdentifier, "ipv6")

        svcPMstorageObj = IpAddress.objects.create(address=str(lVSRouterValues['svcPMstorage']), ipType=ipType, ipv4UniqueIdentifier=publicIdentifier)
        svcFMstorageObj = IpAddress.objects.create(address=str(lVSRouterValues['svcFMstorage']), ipType=ipType, ipv4UniqueIdentifier=publicIdentifier)
        svcCMstorageObj = IpAddress.objects.create(address=str(lVSRouterValues['svcCMstorage']), ipType=ipType, ipv4UniqueIdentifier=publicIdentifier)
        svcStorageInternalObj = IpAddress.objects.create(address=str(lVSRouterValues['svcStorageInternal']), ipType=ipType, ipv4UniqueIdentifier=clusterObj.id)
        svcStorageObj = IpAddress.objects.create(address=str(lVSRouterValues['svcStorage']), ipType=ipType, ipv4UniqueIdentifier=publicIdentifier)

        scpSCPinternalObj = createLVSRouterIP(lVSRouterValues['scpSCPinternal'], ipType, clusterObj.id, "ipv4")
        scpSCPexternalObj = createLVSRouterIP(lVSRouterValues['scpSCPexternal'], ipType, publicIdentifier, "ipv4")
        scpSCPinternalIPv6Obj = createLVSRouterIP(lVSRouterValues['scpSCPinternalIPv6'], ipType, clusterObj.id, "ipv6")
        scpSCPexternalIPv6Obj = createLVSRouterIP(lVSRouterValues['scpSCPexternalIPv6'], ipType, publicIdentifier, "ipv6")
        scpSCPstorageObj = createLVSRouterIP(lVSRouterValues['scpSCPstorage'], ipType, publicIdentifier, "ipv4")
        scpStorageInternalObj = createLVSRouterIP(lVSRouterValues['scpStorageInternal'], ipType, clusterObj.id, "ipv4")
        scpStorageObj = createLVSRouterIP(lVSRouterValues['scpStorage'], ipType, publicIdentifier, "ipv4")

        evtStorageInternalObj = createLVSRouterIP(lVSRouterValues['evtStorageInternal'], ipType, clusterObj.id, "ipv4")
        evtStorageObj = createLVSRouterIP(lVSRouterValues['evtStorage'], ipType, publicIdentifier, "ipv4")

        strInternalObj = createLVSRouterIP(lVSRouterValues['strInternal'], ipType, clusterObj.id, "ipv4")
        strSTRinternal2Obj = createLVSRouterIP(lVSRouterValues['strSTRinternal2'], ipType, clusterObj.id, "ipv4")
        strSTRinternal3Obj = createLVSRouterIP(lVSRouterValues['strSTRinternal3'], ipType, clusterObj.id, "ipv4")

        strExternalObj = createLVSRouterIP(lVSRouterValues['strExternal'], ipType, publicIdentifier, "ipv4")
        strSTRexternal2Obj = createLVSRouterIP(lVSRouterValues['strSTRexternal2'], ipType, publicIdentifier, "ipv4")
        strSTRexternal3Obj = createLVSRouterIP(lVSRouterValues['strSTRexternal3'], ipType, publicIdentifier, "ipv4")

        strSTRinternalIPv6Obj = createLVSRouterIP(lVSRouterValues['strSTRinternalIPv6'], ipType, clusterObj.id, "ipv6")
        strSTRinternalIPv62Obj = createLVSRouterIP(lVSRouterValues['strSTRinternalIPv62'], ipType, clusterObj.id, "ipv6")
        strSTRinternalIPv63Obj = createLVSRouterIP(lVSRouterValues['strSTRinternalIPv63'], ipType, clusterObj.id, "ipv6")

        strExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['strExternalIPv6'], ipType, publicIdentifier, "ipv6")
        strSTRexternalIPv62Obj = createLVSRouterIP(lVSRouterValues['strSTRexternalIPv62'], ipType, publicIdentifier, "ipv6")
        strSTRexternalIPv63Obj = createLVSRouterIP(lVSRouterValues['strSTRexternalIPv63'], ipType, publicIdentifier, "ipv6")

        strSTRstorageObj = createLVSRouterIP(lVSRouterValues['strSTRstorage'], ipType, publicIdentifier, "ipv4")
        strStorageInternalObj = createLVSRouterIP(lVSRouterValues['strStorageInternal'], ipType, clusterObj.id, "ipv4")
        strStorageObj = createLVSRouterIP(lVSRouterValues['strStorage'], ipType, publicIdentifier, "ipv4")

        esnSTRinternalObj = createLVSRouterIP(lVSRouterValues['esnSTRinternal'], ipType, clusterObj.id, "ipv4")
        esnSTRexternalObj = createLVSRouterIP(lVSRouterValues['esnSTRexternal'], ipType, publicIdentifier, "ipv4")
        esSTRinternalIPv6Obj = createLVSRouterIP(lVSRouterValues['esnSTRinternalIPv6'], ipType, clusterObj.id, "ipv6")
        esnSTRexternalIPv6Obj = createLVSRouterIP(lVSRouterValues['esnSTRexternalIPv6'], ipType, publicIdentifier, "ipv6")

        esnSTRstorageObj = createLVSRouterIP(lVSRouterValues['esnSTRstorage'], ipType, publicIdentifier, "ipv4")
        esnStorageInternalObj = createLVSRouterIP(lVSRouterValues['esnStorageInternal'], ipType, clusterObj.id, "ipv4")

        ebsStorageObj = createLVSRouterIP(lVSRouterValues['ebsStorage'], ipType, publicIdentifier, "ipv4")
        ebsStorageInternalObj = createLVSRouterIP(lVSRouterValues['ebsStorageInternal'], ipType, clusterObj.id, "ipv4")
        ebsSTRExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['ebsStrExternalIPv6'], ipType, publicIdentifier, "ipv6")

        asrStorageInternalObj = createLVSRouterIP(lVSRouterValues['asrStorageInternal'], ipType, clusterObj.id, "ipv4")
        asrAsrExternalObj = createLVSRouterIP(lVSRouterValues['asrAsrExternal'], ipType, publicIdentifier, "ipv4")
        asrAsrInternalObj = createLVSRouterIP(lVSRouterValues['asrAsrInternal'], ipType, clusterObj.id, "ipv4")
        asrAsrExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['asrAsrExternalIPv6'], ipType, publicIdentifier, "ipv6")
        asrStorageObj = createLVSRouterIP(lVSRouterValues['asrStorage'], ipType, publicIdentifier, "ipv4")
        asrAsrStorageObj = createLVSRouterIP(lVSRouterValues['asrAsrStorage'], ipType, publicIdentifier, "ipv4")

        ebaStorageObj = createLVSRouterIP(lVSRouterValues['ebaStorage'], ipType, publicIdentifier, "ipv4")
        ebaStorageInternalObj = createLVSRouterIP(lVSRouterValues['ebaStorageInternal'], ipType, clusterObj.id, "ipv4")

        msossfmInternalObj = createLVSRouterIP(lVSRouterValues['msossfmInternal'], ipType, clusterObj.id, "ipv4")
        msossfmExternalObj = createLVSRouterIP(lVSRouterValues['msossfmExternal'], ipType, publicIdentifier, "ipv4")
        msossfmInternalIPv6Obj = createLVSRouterIP(lVSRouterValues['msossfmInternalIPv6'], ipType, clusterObj.id, "ipv6")
        msossfmExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['msossfmExternalIPv6'], ipType, publicIdentifier, "ipv6")

        #LVS Router VIP Extended Addresses
        ebaInternalObj = createLVSRouterIP(lVSRouterValues['ebaInternal'], ipType, clusterObj.id, "ipv4")
        ebaExternalObj = createLVSRouterIP(lVSRouterValues['ebaExternal'], ipType, publicIdentifier, "ipv4")
        ebaInternalIPv6Obj = createLVSRouterIP(lVSRouterValues['ebaInternalIPv6'], ipType, clusterObj.id, "ipv6")
        ebaExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['ebaExternalIPv6'], ipType, publicIdentifier, "ipv6")

        pmExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['svcPmPublicIpv6'], ipType, publicIdentifier, "ipv6")

        oranInternalObj = createLVSRouterIP(lVSRouterValues['oranInternal'], ipType, clusterObj.id, "ipv4")
        oranInternalIPv6Obj = createLVSRouterIP(lVSRouterValues['oranInternalIPv6'], ipType, clusterObj.id, "ipv6")
        oranExternalObj = createLVSRouterIP(lVSRouterValues['oranExternal'], ipType, publicIdentifier, "ipv4")
        oranExternalIPv6Obj = createLVSRouterIP(lVSRouterValues['oranExternalIPv6'], ipType, publicIdentifier, "ipv6")
        #Create LSV Router VIP
        LVSRouterVip.objects.create(cluster=clusterObj, pm_internal=pmInternalObj, pm_external=pmExternalObj,
            fm_internal=fmInternalObj, fm_external=fmExternalObj,
            fm_internal_ipv6=fmInternalIPv6Obj, fm_external_ipv6=fmExternalIPv6Obj,
            cm_internal=cmInternalObj, cm_external=cmExternalObj,
            cm_internal_ipv6=cmInternalIPv6Obj, cm_external_ipv6=cmExternalIPv6Obj,
            svc_pm_storage=svcPMstorageObj,
            svc_fm_storage=svcFMstorageObj,
            svc_cm_storage=svcCMstorageObj,
            svc_storage_internal=svcStorageInternalObj,
            svc_storage=svcStorageObj,
            scp_scp_internal=scpSCPinternalObj, scp_scp_external=scpSCPexternalObj,
            scp_scp_internal_ipv6=scpSCPinternalIPv6Obj, scp_scp_external_ipv6=scpSCPexternalIPv6Obj,
            scp_scp_storage=scpSCPstorageObj,
            scp_storage_internal=scpStorageInternalObj,
            scp_storage=scpStorageObj,
            evt_storage_internal=evtStorageInternalObj,
            evt_storage=evtStorageObj,
            str_str_if=lVSRouterValues['strSTRif'],
            str_internal=strInternalObj,
            str_str_internal_2=strSTRinternal2Obj,
            str_str_internal_3=strSTRinternal3Obj,
            str_external=strExternalObj,
            str_str_external_2=strSTRexternal2Obj,
            str_str_external_3=strSTRexternal3Obj,
            str_str_internal_ipv6=strSTRinternalIPv6Obj,
            str_str_internal_ipv6_2=strSTRinternalIPv62Obj,
            str_str_internal_ipv6_3=strSTRinternalIPv63Obj,
            str_external_ipv6=strExternalIPv6Obj,
            str_str_external_ipv6_2=strSTRexternalIPv62Obj,
            str_str_external_ipv6_3=strSTRexternalIPv63Obj,
            str_str_storage=strSTRstorageObj,
            str_storage_internal=strStorageInternalObj,
            str_storage=strStorageObj,
            esn_str_if=lVSRouterValues['esnSTRif'],
            esn_str_internal=esnSTRinternalObj,
            esn_str_external=esnSTRexternalObj,
            esn_str_internal_ipv6=esSTRinternalIPv6Obj,
            esn_str_external_ipv6=esnSTRexternalIPv6Obj,
            esn_str_storage=esnSTRstorageObj,
            esn_storage_internal=esnStorageInternalObj,
            ebs_storage=ebsStorageObj,
            ebs_storage_internal=ebsStorageInternalObj,
            ebs_str_external_ipv6=ebsSTRExternalIPv6Obj,
            asr_storage_internal=asrStorageInternalObj,
            asr_asr_external=asrAsrExternalObj,
            asr_asr_internal=asrAsrInternalObj,
            asr_asr_external_ipv6=asrAsrExternalIPv6Obj,
            asr_storage=asrStorageObj,
            asr_asr_storage=asrAsrStorageObj,
            eba_storage=ebaStorageObj,
            eba_storage_internal=ebaStorageInternalObj,
            msossfm_internal=msossfmInternalObj,
            msossfm_external=msossfmExternalObj,
            msossfm_internal_ipv6=msossfmInternalIPv6Obj,
            msossfm_external_ipv6=msossfmExternalIPv6Obj)
        #Create LVS Router VIP Extended
        LVSRouterVipExtended.objects.create(cluster=clusterObj,
                eba_external=ebaExternalObj,
                eba_external_ipv6=ebaExternalIPv6Obj,
                eba_internal=ebaInternalObj,
                eba_internal_ipv6=ebaInternalIPv6Obj,
                svc_pm_ipv6=pmExternalIPv6Obj,
                oran_internal = oranInternalObj,
                oran_internal_ipv6 = oranInternalIPv6Obj,
                oran_external= oranExternalObj,
                oran_external_ipv6 = oranExternalIPv6Obj)

        return ("0","Success")
    except Exception as error:
        message = "There was an issue saving the LVS Router information to the cluster. Exception: " + str(error)
        logger.error(message)
        return ("1",message)

def updateLVSRouterVip(lVSRouterValues,clusterObj,action):
    '''
    Function to edit the LVS Router VIP Address information to the cluster
    '''
    try:
        type ="lvsRouterVip_"
        if action == "delete":
            try:
                LVSRouterVip.objects.get(cluster_id=clusterObj.id).delete()
                if LVSRouterVipExtended.objects.filter(cluster_id=clusterObj.id).exists():
                    LVSRouterVipExtended.objects.get(cluster_id=clusterObj.id).delete()
                IpAddress.objects.filter(ipType=str(type) + str(clusterObj.id)).delete()
            except Exception as error:
                message = "Issue Deleting LVS Router Information for this Deployment: " + str(clusterObj.id)
                logger.error(message)
                return ("1",message)
        else:
            fields = ("cluster__id", "pm_internal__address", "pm_external__address",
                    "fm_internal__address", "fm_external__address", "fm_internal_ipv6__ipv6_address", "fm_external_ipv6__ipv6_address",
                    "cm_internal__address", "cm_external__address", "cm_internal_ipv6__ipv6_address", "cm_external_ipv6__ipv6_address",
                    "svc_pm_storage__address", "svc_fm_storage__address", "svc_cm_storage__address",
                    "svc_storage_internal__address", "svc_storage__address",
                    "scp_scp_internal__address", "scp_scp_external__address", "scp_scp_internal_ipv6__ipv6_address", "scp_scp_external_ipv6__ipv6_address",
                    "scp_scp_storage__address", "scp_storage_internal__address", "scp_storage__address",
                    "evt_storage_internal__address", "evt_storage__address",
                    "str_internal__address", "str_str_internal_2__address", "str_str_internal_3__address",
                    "str_external__address", "str_str_external_2__address", "str_str_external_3__address",
                    "str_str_internal_ipv6__ipv6_address", "str_str_internal_ipv6_2__ipv6_address", "str_str_internal_ipv6_3__ipv6_address",
                    "str_external_ipv6__ipv6_address", "str_str_external_ipv6_2__ipv6_address", "str_str_external_ipv6_3__ipv6_address",
                    "str_str_storage__address", "str_storage_internal__address", "str_storage__address",
                    "esn_str_internal__address", "esn_str_external__address", "esn_str_internal_ipv6__ipv6_address",
                    "esn_str_external_ipv6__ipv6_address", "esn_str_storage__address", "esn_storage_internal__address",
                    "ebs_storage_internal__address", "ebs_storage__address", "ebs_str_external_ipv6__ipv6_address", "asr_storage_internal__address", "asr_asr_external__address",
                    "asr_asr_internal__address", "asr_asr_external_ipv6__ipv6_address", "asr_storage__address","asr_asr_storage__address",
                    "eba_storage_internal__address", "eba_storage__address",
                    "msossfm_internal__address", "msossfm_external__address", "msossfm_internal_ipv6__ipv6_address", "msossfm_external_ipv6__ipv6_address")
            addressList = filter(None,lVSRouterValues.values())
            duplicates = getDuplicatesInList(addressList)
            if len(duplicates) > 0:
                raise Exception("Duplicate IP Info "+str(duplicates))
            LVSRouterVipObj = LVSRouterVip.objects.only(fields).values(*fields).get(cluster_id=clusterObj.id)
            if not LVSRouterVipExtended.objects.filter(cluster_id=clusterObj.id).exists():
                LVSRouterVipExtended.objects.create(cluster_id=clusterObj.id)
            fields_extras = (
            "cluster_id", "eba_external__address", "eba_external_ipv6__ipv6_address", "eba_internal__address",
            "eba_internal_ipv6__ipv6_address", "svc_pm_ipv6__ipv6_address","oran_internal__address","oran_internal_ipv6__ipv6_address", "oran_external__address", "oran_external_ipv6__ipv6_address")
            LVSRouterVipObjExtended = LVSRouterVipExtended.objects.only(fields_extras).values(*fields_extras).get(cluster_id=clusterObj.id)
            updateIpaddressObj(clusterObj,LVSRouterVipObj["pm_internal__address"],type,lVSRouterValues['pmInternal'],"internal", field="pm_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["pm_external__address"],type,lVSRouterValues['pmExternal'],"ipv4", field="pm_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["fm_internal__address"],type,lVSRouterValues['fmInternal'],"internal", field="fm_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["fm_external__address"],type,lVSRouterValues['fmExternal'],"ipv4", field="fm_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["fm_internal_ipv6__ipv6_address"],type,lVSRouterValues['fmInternalIPv6'],"internal_ipv6",field="fm_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["fm_external_ipv6__ipv6_address"],type,lVSRouterValues['fmExternalIPv6'],"ipv6",field="fm_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["cm_internal__address"],type,lVSRouterValues['cmInternal'],"internal", field="cm_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["cm_external__address"],type,lVSRouterValues['cmExternal'],"ipv4", field="cm_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["cm_internal_ipv6__ipv6_address"],type,lVSRouterValues['cmInternalIPv6'],"internal_ipv6",field="cm_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["cm_external_ipv6__ipv6_address"],type,lVSRouterValues['cmExternalIPv6'],"ipv6",field="cm_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["svc_pm_storage__address"],type,lVSRouterValues['svcPMstorage'],"ipv4", field="svc_pm_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["svc_fm_storage__address"],type,lVSRouterValues['svcFMstorage'],"ipv4", field="svc_fm_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["svc_cm_storage__address"],type,lVSRouterValues['svcCMstorage'],"ipv4", field="svc_cm_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["svc_storage_internal__address"],type,lVSRouterValues['svcStorageInternal'],"internal", field="svc_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["svc_storage__address"],type,lVSRouterValues['svcStorage'],"ipv4", field="svc_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["scp_scp_internal__address"],type,lVSRouterValues['scpSCPinternal'],"internal", field="scp_scp_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["scp_scp_external__address"],type,lVSRouterValues['scpSCPexternal'],"ipv4", field="scp_scp_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["scp_scp_internal_ipv6__ipv6_address"],type,lVSRouterValues['scpSCPinternalIPv6'],"internal_ipv6",field="scp_scp_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["scp_scp_external_ipv6__ipv6_address"],type,lVSRouterValues['scpSCPexternalIPv6'],"ipv6",field="scp_scp_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["scp_scp_storage__address"],type,lVSRouterValues['scpSCPstorage'],"ipv4", field="scp_scp_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["scp_storage_internal__address"],type,lVSRouterValues['scpStorageInternal'],"internal", field="scp_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["scp_storage__address"],type,lVSRouterValues['scpStorage'],"ipv4", field="scp_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["evt_storage_internal__address"],type,lVSRouterValues['evtStorageInternal'],"internal", field="evt_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["evt_storage__address"],type,lVSRouterValues['evtStorage'],"ipv4", field="evt_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_internal__address"],type,lVSRouterValues['strInternal'],"internal", field="str_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_internal_2__address"],type,lVSRouterValues['strSTRinternal2'],"internal", field="str_str_internal_2")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_internal_3__address"],type,lVSRouterValues['strSTRinternal3'],"internal", field="str_str_internal_3")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_external__address"],type,lVSRouterValues['strExternal'],"ipv4", field="str_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_external_2__address"],type,lVSRouterValues['strSTRexternal2'],"ipv4", field="str_str_external_2")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_external_3__address"],type,lVSRouterValues['strSTRexternal3'],"ipv4", field="str_str_external_3")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_internal_ipv6__ipv6_address"],type,lVSRouterValues['strSTRinternalIPv6'],"internal_ipv6",field="str_str_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_internal_ipv6_2__ipv6_address"],type,lVSRouterValues['strSTRinternalIPv62'],"internal_ipv6",field="str_str_internal_ipv6_2")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_internal_ipv6_3__ipv6_address"],type,lVSRouterValues['strSTRinternalIPv63'],"internal_ipv6",field="str_str_internal_ipv6_3")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_external_ipv6__ipv6_address"],type,lVSRouterValues['strExternalIPv6'],"ipv6",field="str_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_external_ipv6_2__ipv6_address"],type,lVSRouterValues['strSTRexternalIPv62'],"ipv6",field="str_str_external_ipv6_2")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_external_ipv6_3__ipv6_address"],type,lVSRouterValues['strSTRexternalIPv63'],"ipv6",field="str_str_external_ipv6_3")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_str_storage__address"],type,lVSRouterValues['strSTRstorage'],"ipv4", field="str_str_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_storage_internal__address"],type,lVSRouterValues['strStorageInternal'],"internal", field="str_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["str_storage__address"],type,lVSRouterValues['strStorage'],"ipv4", field="str_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["esn_str_internal__address"],type,lVSRouterValues['esnSTRinternal'],"internal", field="esn_str_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["esn_str_external__address"],type,lVSRouterValues['esnSTRexternal'],"ipv4", field="esn_str_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["esn_str_internal_ipv6__ipv6_address"],type,lVSRouterValues['esnSTRinternalIPv6'],"internal_ipv6",field="esn_str_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["esn_str_external_ipv6__ipv6_address"],type,lVSRouterValues['esnSTRexternalIPv6'],"ipv6",field="esn_str_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["esn_str_storage__address"],type,lVSRouterValues['esnSTRstorage'],"ipv4", field="esn_str_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["esn_storage_internal__address"],type,lVSRouterValues['esnStorageInternal'],"internal", field="esn_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["ebs_storage__address"],type,lVSRouterValues['ebsStorage'],"ipv4", field="ebs_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["ebs_storage_internal__address"],type,lVSRouterValues['ebsStorageInternal'],"internal", field="ebs_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["ebs_str_external_ipv6__ipv6_address"],type,lVSRouterValues['ebsStrExternalIPv6'],"ipv6", field="ebs_str_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["asr_storage__address"],type,lVSRouterValues['asrStorage'],"ipv4", field="asr_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["asr_storage_internal__address"],type,lVSRouterValues['asrStorageInternal'],"internal", field="asr_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["asr_asr_external__address"],type,lVSRouterValues['asrAsrExternal'],"ipv4", field="asr_asr_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["asr_asr_internal__address"],type,lVSRouterValues['asrAsrInternal'],"internal", field="asr_asr_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["asr_asr_external_ipv6__ipv6_address"],type,lVSRouterValues['asrAsrExternalIPv6'],"ipv6",field="asr_asr_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["asr_asr_storage__address"],type,lVSRouterValues['asrAsrStorage'],"ipv4", field="asr_asr_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["eba_storage__address"],type,lVSRouterValues['ebaStorage'],"ipv4", field="eba_storage")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["eba_storage_internal__address"],type,lVSRouterValues['ebaStorageInternal'],"internal", field="eba_storage_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["msossfm_internal__address"],type,lVSRouterValues['msossfmInternal'],"internal", field="msossfm_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["msossfm_external__address"],type,lVSRouterValues['msossfmExternal'],"ipv4", field="msossfm_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["msossfm_internal_ipv6__ipv6_address"],type,lVSRouterValues['msossfmInternalIPv6'],"internal_ipv6",field="msossfm_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObj["msossfm_external_ipv6__ipv6_address"],type,lVSRouterValues['msossfmExternalIPv6'],"ipv6",field="msossfm_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["eba_external__address"],type,lVSRouterValues['ebaExternal'],"ipv4",field="eba_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["eba_external_ipv6__ipv6_address"],type,lVSRouterValues['ebaExternalIPv6'],"ipv6",field="eba_external_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["eba_internal__address"],type,lVSRouterValues['ebaInternal'],"internal",field="eba_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["eba_internal_ipv6__ipv6_address"],type,lVSRouterValues['ebaInternalIPv6'],"internal_ipv6",field="eba_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["svc_pm_ipv6__ipv6_address"],type,lVSRouterValues['svcPmPublicIpv6'],"ipv6",field="svc_pm_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["oran_internal__address"],type,lVSRouterValues['oranInternal'],"internal",field="oran_internal")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["oran_internal_ipv6__ipv6_address"],type,lVSRouterValues['oranInternalIPv6'],"internal_ipv6",field="oran_internal_ipv6")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["oran_external__address"],type,lVSRouterValues['oranExternal'],"ipv4",field="oran_external")
            updateIpaddressObj(clusterObj,LVSRouterVipObjExtended["oran_external_ipv6__ipv6_address"],type,lVSRouterValues['oranExternalIPv6'],"ipv6",field="oran_external_ipv6")

            #Updating Interfaces
            lvsrouterObj = LVSRouterVip.objects.get(cluster_id=clusterObj.id)
            lvsrouterObj.str_str_if = lVSRouterValues['strSTRif']
            lvsrouterObj.esn_str_if = lVSRouterValues['esnSTRif']
            lvsrouterObj.save(force_update=True)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue editing the LVS Router VIP information for the cluster. Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def updateIpaddressObj(clusterObj,queryString,type,update,extraDetail,field=None):
    '''
    The updateIpaddressObj is a helper function for editLVSRouterVip for updating the IpAddress Model when LVS Router IP's are updated by users
    '''
    ipDeleted = False
    identifier = clusterObj.management_server.server.hardware_type
    if identifier == "cloud" or extraDetail == "internal" or extraDetail == "internal_ipv6":
        identifierValue = str(clusterObj.id)
    else:
        identifierValue = "1"
    lvsrouterObj = LVSRouterVip.objects.get(cluster_id=clusterObj.id)
    lvsrouterObjExtended = LVSRouterVipExtended.objects.get(cluster_id=clusterObj.id)
    if extraDetail == "ipv4" or extraDetail == "internal":
        if queryString is not None and update != "":
            if IpAddress.objects.filter(address=str(queryString), ipType=str(type) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue).exists():
                result = IpAddress.objects.get(address=str(queryString), ipType=str(type) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue)
                result.address = str(update)
                result.save(force_update=True)
                return
        elif queryString is None and update != "":
            if not IpAddress.objects.filter(address=str(update), ipv4UniqueIdentifier=identifierValue).exists():
                result = IpAddress.objects.create(address=update, ipType=str(type) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue)
                if field == "svc_pm_storage":  lvsrouterObj.svc_pm_storage = result
                elif field == "svc_fm_storage":  lvsrouterObj.svc_fm_storage = result
                elif field == "svc_cm_storage":  lvsrouterObj.svc_cm_storage = result
                elif field == "svc_storage":  lvsrouterObj.svc_storage = result
                elif field == "scp_scp_internal": lvsrouterObj.scp_scp_internal = result
                elif field == "scp_scp_external": lvsrouterObj.scp_scp_external = result
                elif field == "scp_scp_storage":  lvsrouterObj.scp_scp_storage = result
                elif field == "scp_storage":  lvsrouterObj.scp_storage = result
                elif field == "scp_storage_internal":  lvsrouterObj.scp_storage_internal = result
                elif field == "evt_storage":  lvsrouterObj.evt_storage = result
                elif field == "evt_storage_internal":  lvsrouterObj.evt_storage_internal = result
                elif field == "str_internal": lvsrouterObj.str_internal = result
                elif field == "str_str_internal_2": lvsrouterObj.str_str_internal_2 = result
                elif field == "str_str_internal_3": lvsrouterObj.str_str_internal_3 = result
                elif field == "str_external": lvsrouterObj.str_external = result
                elif field == "str_str_external_2": lvsrouterObj.str_str_external_2 = result
                elif field == "str_str_external_3": lvsrouterObj.str_str_external_3 = result
                elif field == "str_str_storage":  lvsrouterObj.str_str_storage = result
                elif field == "str_storage_internal":  lvsrouterObj.str_storage_internal = result
                elif field == "str_storage":  lvsrouterObj.str_storage = result
                elif field == "esn_str_internal": lvsrouterObj.esn_str_internal = result
                elif field == "esn_str_external": lvsrouterObj.esn_str_external = result
                elif field == "esn_str_storage":  lvsrouterObj.esn_str_storage = result
                elif field == "esn_storage_internal":  lvsrouterObj.esn_storage_internal = result
                elif field == "ebs_storage":  lvsrouterObj.ebs_storage = result
                elif field == "ebs_storage_internal":  lvsrouterObj.ebs_storage_internal = result
                elif field == "asr_asr_internal": lvsrouterObj.asr_asr_internal = result
                elif field == "asr_asr_external": lvsrouterObj.asr_asr_external = result
                elif field == "asr_storage":  lvsrouterObj.asr_storage = result
                elif field == "asr_storage_internal":  lvsrouterObj.asr_storage_internal = result
                elif field == "asr_asr_storage":  lvsrouterObj.asr_asr_storage = result
                elif field == "eba_storage":  lvsrouterObj.eba_storage = result
                elif field == "eba_storage_internal":  lvsrouterObj.eba_storage_internal = result
                elif field == "msossfm_internal":  lvsrouterObj.msossfm_internal = result
                elif field == "msossfm_external":  lvsrouterObj.msossfm_external = result
                elif field == "eba_external": lvsrouterObjExtended.eba_external  = result
                elif field == "eba_internal": lvsrouterObjExtended.eba_internal  = result
                elif field == "oran_internal": lvsrouterObjExtended.oran_internal  = result
                elif field == "oran_external": lvsrouterObjExtended.oran_external  = result
                lvsrouterObjExtended.save(force_update=True)
                lvsrouterObj.save(force_update=True)
                return
            else:
                raise ValueError("IP Address: " + str(update) + " is already in use in this or another cluster")
        elif queryString is not None and update == "":
            if IpAddress.objects.filter(address=str(queryString), ipType=str(type) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue).exists():
                result = IpAddress.objects.get(address=str(queryString), ipType=str(type) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue)
                if field == "scp_storage":  lvsrouterObj.scp_storage = None
                elif field == "scp_storage_internal":  lvsrouterObj.scp_storage_internal = None
                elif field == "scp_scp_internal": lvsrouterObj.scp_scp_internal = None
                elif field == "scp_scp_external": lvsrouterObj.scp_scp_external = None
                elif field == "scp_scp_storage":  lvsrouterObj.scp_scp_storage = None
                elif field == "evt_storage":  lvsrouterObj.evt_storage = None
                elif field == "evt_storage_internal":  lvsrouterObj.evt_storage_internal = None
                elif field == "str_internal": lvsrouterObj.str_internal = None
                elif field == "str_str_internal_2": lvsrouterObj.str_str_internal_2 = None
                elif field == "str_str_internal_3": lvsrouterObj.str_str_internal_3 = None
                elif field == "str_external": lvsrouterObj.str_external = None
                elif field == "str_str_external_2": lvsrouterObj.str_str_external_2 = None
                elif field == "str_str_external_3": lvsrouterObj.str_str_external_3 = None
                elif field == "str_str_storage":  lvsrouterObj.str_str_storage = None
                elif field == "str_storage_internal":  lvsrouterObj.str_storage_internal = None
                elif field == "str_storage":  lvsrouterObj.str_storage = None
                elif field == "esn_str_internal": lvsrouterObj.esn_str_internal = None
                elif field == "esn_str_external": lvsrouterObj.esn_str_external = None
                elif field == "esn_str_storage":  lvsrouterObj.esn_str_storage = None
                elif field == "esn_storage_internal":  lvsrouterObj.esn_storage_internal = None
                elif field == "ebs_storage":  lvsrouterObj.ebs_storage = None
                elif field == "ebs_storage_internal":  lvsrouterObj.ebs_storage_internal = None
                elif field == "asr_asr_internal": lvsrouterObj.asr_asr_internal = None
                elif field == "asr_asr_external": lvsrouterObj.asr_asr_external = None
                elif field == "asr_storage":  lvsrouterObj.asr_storage = None
                elif field == "asr_storage_internal":  lvsrouterObj.asr_storage_internal = None
                elif field == "asr_asr_storage":  lvsrouterObj.asr_asr_storage = None
                elif field == "eba_storage":  lvsrouterObj.eba_storage = None
                elif field == "eba_storage_internal":  lvsrouterObj.eba_storage_internal = None
                elif field == "msossfm_internal":  lvsrouterObj.msossfm_internal = None
                elif field == "msossfm_external":  lvsrouterObj.msossfm_external = None
                elif field == "eba_external": lvsrouterObjExtended.eba_external  = None
                elif field == "eba_internal": lvsrouterObjExtended.eba_internal  = None
                elif field == "oran_internal": lvsrouterObjExtended.oran_internal  = None
                elif field == "oran_external": lvsrouterObjExtended.oran_external  = None
                lvsrouterObjExtended.save(force_update=True)
                lvsrouterObj.save(force_update=True)
                result.delete()

    if queryString is None and update == "":
        return
    if queryString is None and update != "":
        if not IpAddress.objects.filter(ipv6_address=str(update), ipv6UniqueIdentifier=identifierValue).exists():
            result = IpAddress.objects.create(ipv6_address=update, ipType=str(type) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue)
            if field == "cm_external_ipv6":  lvsrouterObj.cm_external_ipv6 = result
            elif field == "cm_internal_ipv6":  lvsrouterObj.cm_internal_ipv6 = result
            elif field == "str_external_ipv6": lvsrouterObj.str_external_ipv6 = result
            elif field == "str_str_external_ipv6_2": lvsrouterObj.str_str_external_ipv6_2 = result
            elif field == "str_str_external_ipv6_3": lvsrouterObj.str_str_external_ipv6_3 = result
            elif field == "fm_internal_ipv6":  lvsrouterObj.fm_internal_ipv6 = result
            elif field == "fm_external_ipv6":  lvsrouterObj.fm_external_ipv6 = result
            elif field == "scp_scp_internal_ipv6":  lvsrouterObj.scp_scp_internal_ipv6 = result
            elif field == "scp_scp_external_ipv6":  lvsrouterObj.scp_scp_external_ipv6 = result
            elif field == "str_str_internal_ipv6":  lvsrouterObj.str_str_internal_ipv6 = result
            elif field == "str_str_internal_ipv6_2":  lvsrouterObj.str_str_internal_ipv6_2 = result
            elif field == "str_str_internal_ipv6_3":  lvsrouterObj.str_str_internal_ipv6_3 = result
            elif field == "esn_str_internal_ipv6":  lvsrouterObj.esn_str_internal_ipv6 = result
            elif field == "esn_str_external_ipv6": lvsrouterObj.esn_str_external_ipv6 = result
            elif field == "ebs_str_external_ipv6":lvsrouterObj.ebs_str_external_ipv6 = result
            elif field == "asr_asr_external_ipv6": lvsrouterObj.asr_asr_external_ipv6 = result
            elif field == "msossfm_internal_ipv6":  lvsrouterObj.msossfm_internal_ipv6 = result
            elif field == "msossfm_external_ipv6":  lvsrouterObj.msossfm_external_ipv6 = result
            elif field == "eba_external_ipv6": lvsrouterObjExtended.eba_external_ipv6 = result
            elif field == "eba_internal_ipv6": lvsrouterObjExtended.eba_internal_ipv6 = result
            elif field == "svc_pm_ipv6": lvsrouterObjExtended.svc_pm_ipv6 = result
            elif field == "oran_internal_ipv6": lvsrouterObjExtended.oran_internal_ipv6 = result
            elif field == "oran_external_ipv6": lvsrouterObjExtended.oran_external_ipv6 = result
            lvsrouterObjExtended.save(force_update=True)
            lvsrouterObj.save(force_update=True)
            return
        else:
            raise ValueError("IP Address: " + str(update) + " is already in use in this or another cluster")

    try:
        if IpAddress.objects.filter(ipv6_address=queryString, address=None, ipType=str(type) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue).exists():
            result = IpAddress.objects.get(ipv6_address=queryString, address=None, ipType=str(type) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue)
            if update == "":
                if field == "cm_external_ipv6":  lvsrouterObj.cm_external_ipv6 = None
                elif field == "cm_internal_ipv6":  lvsrouterObj.cm_internal_ipv6 = None
                elif field == "str_external_ipv6": lvsrouterObj.str_external_ipv6 = None
                elif field == "str_str_external_ipv6_2": lvsrouterObj.str_str_external_ipv6_2 = None
                elif field == "str_str_external_ipv6_3": lvsrouterObj.str_str_external_ipv6_3 = None
                elif field == "fm_internal_ipv6":  lvsrouterObj.fm_internal_ipv6 = None
                elif field == "fm_external_ipv6":  lvsrouterObj.fm_external_ipv6 = None
                elif field == "scp_scp_internal_ipv6":  lvsrouterObj.scp_scp_internal_ipv6 = None
                elif field == "scp_scp_external_ipv6":  lvsrouterObj.scp_scp_external_ipv6 = None
                elif field == "str_str_internal_ipv6":  lvsrouterObj.str_str_internal_ipv6 = None
                elif field == "str_str_internal_ipv6_2":  lvsrouterObj.str_str_internal_ipv6_2 = None
                elif field == "str_str_internal_ipv6_3":  lvsrouterObj.str_str_internal_ipv6_3 = None
                elif field == "esn_str_internal_ipv6":  lvsrouterObj.esn_str_internal_ipv6 = None
                elif field == "esn_str_external_ipv6": lvsrouterObj.esn_str_external_ipv6 = None
                elif field == "ebs_str_external_ipv6": lvsrouterObj.ebs_str_external_ipv6 = None
                elif field == "asr_asr_external_ipv6": lvsrouterObj.asr_asr_external_ipv6 = None
                elif field == "msossfm_internal_ipv6":  lvsrouterObj.msossfm_internal_ipv6 = None
                elif field == "msossfm_external_ipv6":  lvsrouterObj.msossfm_external_ipv6 = None
                elif field == "eba_external_ipv6": lvsrouterObjExtended.eba_external_ipv6 = None
                elif field == "eba_internal_ipv6": lvsrouterObjExtended.eba_internal_ipv6 = None
                elif field == "svc_pm_ipv6": lvsrouterObjExtended.svc_pm_ipv6 = None
                elif field == "oran_internal_ipv6": lvsrouterObjExtended.oran_internal_ipv6 = None
                elif field == "oran_external_ipv6": lvsrouterObjExtended.oran_external_ipv6 = None
                lvsrouterObjExtended.save(force_update=True)
                lvsrouterObj.save(force_update=True)
                result.delete()
                ipDeleted = True
            if ipDeleted == False:
                result.ipv6_address = str(update)
                result.save(force_update=True)
        return
    except IpAddress.DoesNotExist:
        return
    return

def getLVSRouterValues(clusterObj,action):
    '''
    The getLVSRouterValues function is a helper funtion that returns all ipaddress associated with e given LVS Router Object for a cluster
    '''
    oldValues = []
    editValues = {}
    addValues = {}
    lVSRouterValues = {}
    allDeploymentIps=getAllIPsInCluster(clusterObj)
    try:
        if action != "add":
            fields = ("cluster__id", "pm_internal__address", "pm_external__address",
                    "fm_internal__address", "fm_external__address", "fm_internal_ipv6__ipv6_address", "fm_external_ipv6__ipv6_address",
                    "cm_internal__address", "cm_external__address", "cm_internal_ipv6__ipv6_address", "cm_external_ipv6__ipv6_address",
                    "svc_pm_storage__address", "svc_fm_storage__address", "svc_cm_storage__address",
                    "svc_storage_internal__address", "svc_storage__address",
                    "scp_scp_internal__address", "scp_scp_external__address", "scp_scp_internal_ipv6__ipv6_address", "scp_scp_external_ipv6__ipv6_address",
                    "scp_scp_storage__address", "scp_storage_internal__address", "scp_storage__address",
                    "evt_storage_internal__address", "evt_storage__address",
                    "str_str_if", "str_internal__address", "str_str_internal_2__address", "str_str_internal_3__address",
                    "str_external__address", "str_str_external_2__address", "str_str_external_3__address",
                    "str_str_internal_ipv6__ipv6_address", "str_str_internal_ipv6_2__ipv6_address", "str_str_internal_ipv6_3__ipv6_address",
                    "str_external_ipv6__ipv6_address", "str_str_external_ipv6_2__ipv6_address", "str_str_external_ipv6_3__ipv6_address",
                    "str_str_storage__address", "str_storage_internal__address", "str_storage__address",
                    "esn_str_if", "esn_str_internal__address", "esn_str_external__address", "esn_str_internal_ipv6__ipv6_address",
                    "esn_str_external_ipv6__ipv6_address", "esn_str_storage__address", "esn_storage_internal__address",
                    "ebs_storage_internal__address", "ebs_storage__address", "ebs_str_external_ipv6__ipv6_address", "asr_storage_internal__address", "asr_asr_external__address",
                    "asr_asr_internal__address", "asr_asr_external_ipv6__ipv6_address", "asr_storage__address","asr_asr_storage__address",
                    "eba_storage_internal__address", "eba_storage__address",
                    "msossfm_internal__address", "msossfm_external__address", "msossfm_internal_ipv6__ipv6_address", "msossfm_external_ipv6__ipv6_address")
            LVSRouterVipObj = LVSRouterVip.objects.only(fields).values(*fields).get(cluster_id=clusterObj.id)
            LVSRouterVipObjExtended = None
            if LVSRouterVipExtended.objects.filter(cluster_id = clusterObj.id).exists():
                fields_extras = (
                    "cluster_id", "eba_external__address", "eba_external_ipv6__ipv6_address", "eba_internal__address",
                    "eba_internal_ipv6__ipv6_address", "svc_pm_ipv6__ipv6_address",
                    "oran_internal__address","oran_internal_ipv6__ipv6_address", "oran_external__address", "oran_external_ipv6__ipv6_address")
                LVSRouterVipObjExtended = LVSRouterVipExtended.objects.only(fields_extras).values(*fields_extras).get(cluster_id=clusterObj.id)

            lVSRouterValues['pmInternal'] = LVSRouterVipObj["pm_internal__address"]
            lVSRouterValues['pmExternal'] = LVSRouterVipObj["pm_external__address"]
            lVSRouterValues['fmInternal'] = LVSRouterVipObj["fm_internal__address"]
            lVSRouterValues['fmExternal'] = LVSRouterVipObj["fm_external__address"]
            lVSRouterValues['fmInternalIPv6'] = "" if LVSRouterVipObj["fm_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["fm_internal_ipv6__ipv6_address"]
            lVSRouterValues['fmExternalIPv6'] = "" if LVSRouterVipObj["fm_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["fm_external_ipv6__ipv6_address"]
            lVSRouterValues['cmInternal'] = LVSRouterVipObj["cm_internal__address"]
            lVSRouterValues['cmExternal'] = LVSRouterVipObj["cm_external__address"]
            lVSRouterValues['cmInternalIPv6'] = "" if LVSRouterVipObj["cm_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["cm_internal_ipv6__ipv6_address"]
            lVSRouterValues['cmExternalIPv6'] = "" if LVSRouterVipObj["cm_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["cm_external_ipv6__ipv6_address"]
            lVSRouterValues['svcFMstorage'] = "" if LVSRouterVipObj["svc_fm_storage__address"] == None else LVSRouterVipObj["svc_fm_storage__address"]
            lVSRouterValues['svcPMstorage'] = "" if LVSRouterVipObj["svc_pm_storage__address"] == None else LVSRouterVipObj["svc_pm_storage__address"]
            lVSRouterValues['svcCMstorage'] = "" if LVSRouterVipObj["svc_cm_storage__address"] == None else LVSRouterVipObj["svc_cm_storage__address"]
            lVSRouterValues['svcStorageInternal'] = LVSRouterVipObj["svc_storage_internal__address"]
            lVSRouterValues['svcStorage'] = "" if LVSRouterVipObj["svc_storage__address"] == None else LVSRouterVipObj["svc_storage__address"]
            if  LVSRouterVipObj["scp_scp_internal__address"] == None:
                scpSCPinternalGateway,scpSCPinternalAdd,scpSCPinternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterScriptingSCPInternal",allDeploymentIps)
                lVSRouterValues['scpSCPinternal'] = scpSCPinternalAdd
            else:
                lVSRouterValues['scpSCPinternal'] = LVSRouterVipObj["scp_scp_internal__address"]
            lVSRouterValues['scpSCPexternal'] = "" if LVSRouterVipObj["scp_scp_external__address"] == None else LVSRouterVipObj["scp_scp_external__address"]
            lVSRouterValues['scpSCPinternalIPv6'] = "" if LVSRouterVipObj["scp_scp_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["scp_scp_internal_ipv6__ipv6_address"]
            lVSRouterValues['scpSCPexternalIPv6'] = "" if LVSRouterVipObj["scp_scp_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["scp_scp_external_ipv6__ipv6_address"]
            lVSRouterValues['scpSCPstorage'] = "" if LVSRouterVipObj["scp_scp_storage__address"] == None else LVSRouterVipObj["scp_scp_storage__address"]
            if LVSRouterVipObj["scp_storage_internal__address"] == None:
                scpStorageInternalGateway,scpStorageInternalAdd,scpStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterScriptingInternal",allDeploymentIps)
                lVSRouterValues['scpStorageInternal'] = scpStorageInternalAdd
            else:
                lVSRouterValues['scpStorageInternal'] = LVSRouterVipObj["scp_storage_internal__address"]
            lVSRouterValues['scpStorage'] = "" if LVSRouterVipObj["scp_storage__address"] == None else LVSRouterVipObj["scp_storage__address"]
            if LVSRouterVipObj["evt_storage_internal__address"] == None:
                evtStorageInternalGateway,evtStorageInternalAdd,evtStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEventsInternal",allDeploymentIps)
                lVSRouterValues['evtStorageInternal'] = evtStorageInternalAdd
            else:
                lVSRouterValues['evtStorageInternal'] = LVSRouterVipObj["evt_storage_internal__address"]
            lVSRouterValues['evtStorage'] = "" if LVSRouterVipObj["evt_storage__address"] == None else LVSRouterVipObj["evt_storage__address"]

            lVSRouterValues['strSTRif'] = "" if LVSRouterVipObj["str_str_if"] == None else LVSRouterVipObj["str_str_if"]
            if LVSRouterVipObj["str_internal__address"] == None:
                strInternalGateway,strInternalAdd,strInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRInternal",allDeploymentIps)
                lVSRouterValues['strInternal'] = strInternalAdd
                allDeploymentIps = allDeploymentIps + ":" +str(strInternalAdd)
            else:
                lVSRouterValues['strInternal'] = LVSRouterVipObj["str_internal__address"]

            if LVSRouterVipObj["str_str_internal_2__address"] == None:
                strInternalGateway,strInternalAdd2,strInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRInternal",allDeploymentIps)
                lVSRouterValues['strSTRinternal2'] = strInternalAdd2
                allDeploymentIps = allDeploymentIps + ":" +str(strInternalAdd2)
            else:
                lVSRouterValues['strSTRinternal2'] = LVSRouterVipObj["str_str_internal_2__address"]

            if LVSRouterVipObj["str_str_internal_3__address"] == None:
                strInternalGateway,strInternalAdd3,strInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRInternal",allDeploymentIps)
                lVSRouterValues['strSTRinternal3'] = strInternalAdd3
            else:
                lVSRouterValues['strSTRinternal3'] = LVSRouterVipObj["str_str_internal_3__address"]

            lVSRouterValues['strExternal'] = "" if LVSRouterVipObj["str_external__address"] == None else LVSRouterVipObj["str_external__address"]
            lVSRouterValues['strSTRexternal2'] = "" if LVSRouterVipObj["str_str_external_2__address"] == None else LVSRouterVipObj["str_str_external_2__address"]
            lVSRouterValues['strSTRexternal3'] = "" if LVSRouterVipObj["str_str_external_3__address"] == None else LVSRouterVipObj["str_str_external_3__address"]
            lVSRouterValues['strSTRinternalIPv6'] = "" if LVSRouterVipObj["str_str_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["str_str_internal_ipv6__ipv6_address"]
            lVSRouterValues['strSTRinternalIPv62'] = "" if LVSRouterVipObj["str_str_internal_ipv6_2__ipv6_address"] == None else LVSRouterVipObj["str_str_internal_ipv6_2__ipv6_address"]
            lVSRouterValues['strSTRinternalIPv63'] = "" if LVSRouterVipObj["str_str_internal_ipv6_3__ipv6_address"] == None else LVSRouterVipObj["str_str_internal_ipv6_3__ipv6_address"]
            lVSRouterValues['strExternalIPv6'] = "" if LVSRouterVipObj["str_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["str_external_ipv6__ipv6_address"]
            lVSRouterValues['strSTRexternalIPv62'] = "" if LVSRouterVipObj["str_str_external_ipv6_2__ipv6_address"] == None else LVSRouterVipObj["str_str_external_ipv6_2__ipv6_address"]
            lVSRouterValues['strSTRexternalIPv63'] = "" if LVSRouterVipObj["str_str_external_ipv6_3__ipv6_address"] == None else LVSRouterVipObj["str_str_external_ipv6_3__ipv6_address"]
            lVSRouterValues['strSTRstorage'] = "" if LVSRouterVipObj["str_str_storage__address"] == None else LVSRouterVipObj["str_str_storage__address"]
            if LVSRouterVipObj["str_storage_internal__address"] == None:
                strStorageInternalGateway,strStorageInternalAdd,strStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRStorageInternal",allDeploymentIps)
                lVSRouterValues['strStorageInternal'] = strStorageInternalAdd
            else:
                lVSRouterValues['strStorageInternal'] = LVSRouterVipObj["str_storage_internal__address"]
            lVSRouterValues['strStorage'] = "" if LVSRouterVipObj["str_storage__address"] == None else LVSRouterVipObj["str_storage__address"]

            lVSRouterValues['esnSTRif'] = "" if LVSRouterVipObj["esn_str_if"] == None else LVSRouterVipObj["esn_str_if"]
            if  LVSRouterVipObj["esn_str_internal__address"] == None:
                esnStrInternalGateway,esnStrInternalAdd,esnStrInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterESNSTRInternal",allDeploymentIps)
                lVSRouterValues['esnSTRinternal'] = esnStrInternalAdd
            else:
                lVSRouterValues['esnSTRinternal'] = LVSRouterVipObj["esn_str_internal__address"]

            lVSRouterValues['esnSTRexternal'] = "" if LVSRouterVipObj["esn_str_external__address"] == None else LVSRouterVipObj["esn_str_external__address"]
            lVSRouterValues['esnSTRinternalIPv6'] = "" if LVSRouterVipObj["esn_str_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["esn_str_internal_ipv6__ipv6_address"]
            lVSRouterValues['esnSTRexternalIPv6'] = "" if LVSRouterVipObj["esn_str_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["esn_str_external_ipv6__ipv6_address"]
            if LVSRouterVipObj["esn_storage_internal__address"] == None:
                strStorageInternalGateway,strStorageInternalAdd,strStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterESNStorageInternal",allDeploymentIps)
                lVSRouterValues['esnStorageInternal'] = strStorageInternalAdd
            else:
                lVSRouterValues['esnStorageInternal'] = LVSRouterVipObj["esn_storage_internal__address"]
            lVSRouterValues['esnSTRstorage'] = "" if LVSRouterVipObj["esn_str_storage__address"] == None else LVSRouterVipObj["esn_str_storage__address"]

            if LVSRouterVipObj["ebs_storage_internal__address"] == None:
                ebsStorageInternalGateway,ebsStorageInternalAdd,ebsStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEBSStorageInternal",allDeploymentIps)
                lVSRouterValues['ebsStorageInternal'] = ebsStorageInternalAdd
            else:
                lVSRouterValues['ebsStorageInternal'] = LVSRouterVipObj["ebs_storage_internal__address"]
            lVSRouterValues['ebsStorage'] = "" if LVSRouterVipObj["ebs_storage__address"] == None else LVSRouterVipObj["ebs_storage__address"]
            lVSRouterValues['ebsStrExternalIPv6'] = "" if LVSRouterVipObj["ebs_str_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["ebs_str_external_ipv6__ipv6_address"]
            if  LVSRouterVipObj["asr_asr_internal__address"] == None:
                asrAsrInternalGateway,asrAsrInternalAdd,asrAsrInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterASRASRInternal",allDeploymentIps)
                lVSRouterValues['asrAsrInternal'] = asrAsrInternalAdd
            else:
                lVSRouterValues['asrAsrInternal'] = LVSRouterVipObj["asr_asr_internal__address"]
            lVSRouterValues['asrAsrExternal'] = "" if LVSRouterVipObj["asr_asr_external__address"] == None else LVSRouterVipObj["asr_asr_external__address"]
            lVSRouterValues['asrAsrExternalIPv6'] = "" if LVSRouterVipObj["asr_asr_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["asr_asr_external_ipv6__ipv6_address"]
            if LVSRouterVipObj["asr_storage_internal__address"] == None:
                asrStorageInternalGateway,asrStorageInternalAdd,asrStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterASRStorageInternal",allDeploymentIps)
                lVSRouterValues['asrStorageInternal'] = asrStorageInternalAdd
            else:
                lVSRouterValues['asrStorageInternal'] = LVSRouterVipObj["asr_storage_internal__address"]
            lVSRouterValues['asrStorage'] = "" if LVSRouterVipObj["asr_storage__address"] == None else LVSRouterVipObj["asr_storage__address"]
            lVSRouterValues['asrAsrStorage'] = "" if LVSRouterVipObj["asr_asr_storage__address"] == None else LVSRouterVipObj["asr_asr_storage__address"]

            if LVSRouterVipObj["eba_storage_internal__address"] == None:
                ebaStorageInternalGateway,ebaStorageInternalAdd,ebaStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEBAStorageInternal",allDeploymentIps)
                lVSRouterValues['ebaStorageInternal'] = ebaStorageInternalAdd
            else:
                lVSRouterValues['ebaStorageInternal'] = LVSRouterVipObj["eba_storage_internal__address"]
            lVSRouterValues['ebaStorage'] = "" if LVSRouterVipObj["eba_storage__address"] == None else LVSRouterVipObj["eba_storage__address"]

            if  LVSRouterVipObj["msossfm_internal__address"] == None:
                msossfmInternalGateway,msossfmInternalAdd,msossfmInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterMSOSSFMInternal",allDeploymentIps)
                lVSRouterValues['msossfmInternal'] = msossfmInternalAdd
            else:
                lVSRouterValues['msossfmInternal'] = LVSRouterVipObj["msossfm_internal__address"]
            lVSRouterValues['msossfmExternal'] = LVSRouterVipObj["msossfm_external__address"]
            lVSRouterValues['msossfmInternalIPv6'] = "" if LVSRouterVipObj["msossfm_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["msossfm_internal_ipv6__ipv6_address"]
            lVSRouterValues['msossfmExternalIPv6'] = "" if LVSRouterVipObj["msossfm_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["msossfm_external_ipv6__ipv6_address"]

            if LVSRouterVipObjExtended != None:
                if  LVSRouterVipObjExtended["eba_internal__address"] == None:
                    ebaInternalGateway,ebaInternalAdd,ebaInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEBAInternal",allDeploymentIps)
                    lVSRouterValues['ebaInternal'] = ebaInternalAdd
                else:
                    lVSRouterValues['ebaInternal'] = LVSRouterVipObjExtended["eba_internal__address"]
                lVSRouterValues['ebaExternal'] = "" if LVSRouterVipObjExtended["eba_external__address"] == None else LVSRouterVipObjExtended["eba_external__address"]
                lVSRouterValues['ebaInternalIPv6'] = "" if LVSRouterVipObjExtended["eba_internal_ipv6__ipv6_address"] == None else LVSRouterVipObjExtended["eba_internal_ipv6__ipv6_address"]
                lVSRouterValues['ebaExternalIPv6'] = "" if LVSRouterVipObjExtended["eba_external_ipv6__ipv6_address"] == None else LVSRouterVipObjExtended["eba_external_ipv6__ipv6_address"]
                lVSRouterValues['svcPmPublicIpv6'] = "" if LVSRouterVipObjExtended["svc_pm_ipv6__ipv6_address"] == None else LVSRouterVipObjExtended["svc_pm_ipv6__ipv6_address"]
                lVSRouterValues['oranInternal'] = "" if LVSRouterVipObjExtended["oran_internal__address"] == None else LVSRouterVipObjExtended["oran_internal__address"]
                lVSRouterValues['oranInternalIPv6'] = "" if LVSRouterVipObjExtended["oran_internal_ipv6__ipv6_address"] == None else LVSRouterVipObjExtended["oran_internal_ipv6__ipv6_address"]
                lVSRouterValues['oranExternal'] = "" if LVSRouterVipObjExtended["oran_external__address"] == None else LVSRouterVipObjExtended["oran_external__address"]
                lVSRouterValues['oranExternalIPv6'] = "" if LVSRouterVipObjExtended["oran_external_ipv6__ipv6_address"] == None else LVSRouterVipObjExtended["oran_external_ipv6__ipv6_address"]

            oldValues.extend([str(lVSRouterValues['pmInternal']) + "##PM Internal Address", str(lVSRouterValues['pmExternal']) + "##PM External Address",
                    str(lVSRouterValues['fmInternal']) + "##FM Internal Address", str(lVSRouterValues['fmExternal']) + "##FM External Address",
                    str(lVSRouterValues['fmInternalIPv6']) + "##FM Internal IPv6 Address", str(lVSRouterValues['fmExternalIPv6']) + "##FM External IPv6 Address",
                    str(lVSRouterValues['cmInternal']) + "##CM Internal Address", str(lVSRouterValues['cmExternal']) + "##CM External Address",
                    str(lVSRouterValues['cmInternalIPv6']) + "##CM Internal IPv6 Address", str(lVSRouterValues['cmExternalIPv6']) + "##CM External IPv6 Address",
                    str(lVSRouterValues['svcPMstorage']) + "##Service PM Storage Address", str(lVSRouterValues['svcFMstorage']) + "##Service FM Storage Address",
                    str(lVSRouterValues['svcCMstorage']) + "##Service CM Storage Address",
                    str(lVSRouterValues['svcStorageInternal']) + "##Service Storage Internal Address",  str(lVSRouterValues['svcStorage']) + "##Service Storage Address",
                    str(lVSRouterValues['scpSCPinternal']) + "##Scripting SCP Internal Address", str(lVSRouterValues['scpSCPexternal']) + "##Scripting SCP External Address",
                    str(lVSRouterValues['scpSCPinternalIPv6']) + "##Scripting SCP Internal IPv6 Address", str(lVSRouterValues['scpSCPexternalIPv6']) + "##Scripting SCP External IPv6 Address",
                    str(lVSRouterValues['scpSCPstorage']) + "##Scripting SCP Storage Address",
                    str(lVSRouterValues['scpStorageInternal']) + "##Scripting Storage Internal Address", str(lVSRouterValues['scpStorage']) + "##Scripting Storage Address",
                    str(lVSRouterValues['evtStorageInternal']) + "##Events Storage Internal Address", str(lVSRouterValues['evtStorage']) + "##Events Storage Address",
                    str(lVSRouterValues['strSTRif']) + "##Streaming STR Services Interface", str(lVSRouterValues['strInternal']) + "##Streaming Internal Address",
                    str(lVSRouterValues['strSTRinternal2']) + "##Streaming STR Internal Address 2", str(lVSRouterValues['strSTRinternal3']) + "##Streaming STR Internal Address 3",
                    str(lVSRouterValues['strExternal']) + "##Streaming External Address", str(lVSRouterValues['strSTRexternal2']) + "##Streaming STR External Address 2",
                    str(lVSRouterValues['strSTRexternal3']) + "##Streaming STR External Address 3", str(lVSRouterValues['strSTRinternalIPv6']) + "##Streaming STR Internal IPv6 Address",
                    str(lVSRouterValues['strSTRinternalIPv62']) + "##Streaming STR Internal IPv6 Address 2", str(lVSRouterValues['strSTRinternalIPv63']) + "##Streaming STR Internal IPv6 Address 3",
                    str(lVSRouterValues['strExternalIPv6']) + "##Streaming external IPv6 Address",  str(lVSRouterValues['strSTRexternalIPv62']) + "##Streaming STR external IPv6 Address 2",
                    str(lVSRouterValues['strSTRexternalIPv63']) + "##Streaming STR external IPv6 Address 3", str(lVSRouterValues['strSTRstorage']) + "##Streaming STR Storage Address",
                    str(lVSRouterValues['strStorageInternal']) + "##Streaming Storage Internal Address", str(lVSRouterValues['strStorage']) + "##Streaming Storage Address",
                    str(lVSRouterValues['esnSTRif']) + "##ESN STR Services Interface", str(lVSRouterValues['esnSTRinternal']) + "##ESN STR Internal Address",
                    str(lVSRouterValues['esnSTRexternal']) + "##ESN STR External Address", str(lVSRouterValues['esnSTRinternalIPv6']) + "##ESN STR Internal IPv6 Address",
                    str(lVSRouterValues['esnSTRexternalIPv6']) + "##ESN STR external IPv6 Address", str(lVSRouterValues['esnStorageInternal']) + "##ESN Storage Internal Address",
                    str(lVSRouterValues['esnSTRstorage']) + "##ESN STR Storage Address", str(lVSRouterValues['ebsStorageInternal']) + "##EBS Storage Internal Address",
                    str(lVSRouterValues['ebsStorage']) + "##EBS Storage Address", str(lVSRouterValues['ebsStrExternalIPv6']) + "##EBS STR External IPv6 Address",
                    str(lVSRouterValues['asrStorage']) + "##ASR Storage Address", str(lVSRouterValues['asrStorageInternal']) + "##ASR Storage Internal Address",
                    str(lVSRouterValues['asrAsrStorage']) + "##ASR ASR Storage Address", str(lVSRouterValues['asrAsrExternalIPv6']) + "##ASR ASR external IPv6 Address",
                    str(lVSRouterValues['asrAsrInternal']) + "##ASR ASR Internal Address", str(lVSRouterValues['asrAsrExternal']) + "##ASR ASR External Address",
                    str(lVSRouterValues['ebaStorageInternal']) + "##EBA Storage Internal Address", str(lVSRouterValues['ebaStorage']) + "##EBA Storage Address",
                    str(lVSRouterValues['msossfmInternal']) + "##MSOSSFM Internal Address", str(lVSRouterValues['msossfmExternal']) + "##MSOSSFM External Address",
                    str(lVSRouterValues['msossfmInternalIPv6']) + "##MSOSSFM Internal IPv6 Address", str(lVSRouterValues['msossfmExternalIPv6']) + "##MSOSSFM External IPv6 Address"])

            if LVSRouterVipObjExtended != None:
                oldValues.extend([str(lVSRouterValues['ebaInternal']) + "##EBA Internal Address",
                                  str(lVSRouterValues['ebaExternal']) + "##EBA External Address",
                                  str(lVSRouterValues['ebaInternalIPv6']) + "##EBA Internal IPv6 Address",
                                  str(lVSRouterValues['ebaExternalIPv6']) + "##EBA External IPv6 Address",
                                  str(lVSRouterValues['svcPmPublicIpv6']) + "##PM External IPv6 Address",
                                  str(lVSRouterValues['oranInternal']) + "##ORAN Internal Address",
                                  str(lVSRouterValues['oranInternalIPv6']) + "##ORAN Internal IPv6 Address",
                                  str(lVSRouterValues['oranExternal']) + "##ORAN External Address",
                                  str(lVSRouterValues['oranExternalIPv6']) + "##ORAN External IPv6 Address"],
                                )

            editValues = lVSRouterValues
        elif action == "add":
            pmInternalGateway,pmInternalAdd,pmInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterPMInternal",allDeploymentIps)
            fmInternalGateway,fmInternalAdd,fmInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterFMInternal",allDeploymentIps)
            cmInternalGateway,cmInternalAdd,cmInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterCMInternal",allDeploymentIps)
            svcStorageInternalGateway,svcStorageInternalAdd,svcStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterStorageInternal",allDeploymentIps)
            scpSCPinternalGateway,scpSCPinternalAdd,scpSCPinternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterScriptingSCPInternal",allDeploymentIps)
            scpStorageInternalGateway,scpStorageInternalAdd,scpStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterScriptingInternal",allDeploymentIps)
            evtStorageInternalGateway,evtStorageInternalAdd,evtStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEventsInternal",allDeploymentIps)
            strInternalGateway,strInternalAdd,strInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRInternal",allDeploymentIps)
            allDeploymentIps = allDeploymentIps + ":" +str(strInternalAdd)
            strInternalGateway2,strInternalAdd2,strInternalBitmask2 = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRInternal",allDeploymentIps)
            allDeploymentIps = allDeploymentIps + ":" +str(strInternalAdd2)
            strInternalGateway3,strInternalAdd3,strInternalBitmask3 = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRInternal",allDeploymentIps)
            strStorageInternalGateway,strStorageInternalAdd,strStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterSTRStorageInternal",allDeploymentIps)
            esnStrInternalGateway,esnStrInternalAdd,esnStrInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterESNSTRInternal",allDeploymentIps)
            esnStorageInternalGateway,esnStorageInternalAdd,esnStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterESNStorageInternal",allDeploymentIps)
            asrStorageInternalGateway,asrStorageInternalAdd,asrStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterASRStorageInternal",allDeploymentIps)
            asrAsrInternalGateway,asrAsrInternalAdd,asrAsrInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterASRASRInternal",allDeploymentIps)
            ebaStorageInternalGateway,ebaStorageInternalAdd,ebaStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEBAStorageInternal",allDeploymentIps)
            ebsStorageInternalGateway,ebsStorageInternalAdd,ebsStorageInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEBSStorageInternal",allDeploymentIps)
            msossfmInternalGateway,msossfmInternalAdd,msossfmInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterMSOSSFMInternal",allDeploymentIps)
            ebaInternalGateway,ebaInternalAdd,ebaInternalBitmask = getNextFreeInternalIP(clusterObj,"PDU-Priv_LSVRouterEBAInternal",allDeploymentIps)

            addValues = {'pmInternal': str(pmInternalAdd), 'fmInternal': str(fmInternalAdd),
                         'cmInternal': str(cmInternalAdd), 'svcStorageInternal': str(svcStorageInternalAdd),
                         'scpSCPinternal': str(scpSCPinternalAdd), 'scpStorageInternal': str(scpStorageInternalAdd),
                         'evtStorageInternal': str(evtStorageInternalAdd), 'strInternal': str(strInternalAdd),
                         'strSTRinternal2': str(strInternalAdd2), 'strSTRinternal3': str(strInternalAdd3),
                         'strStorageInternal': str(strStorageInternalAdd), 'esnSTRinternal': str(esnStrInternalAdd),
                         'esnStorageInternal': str(esnStorageInternalAdd), 'asrStorageInternal': str(asrStorageInternalAdd),
                         'asrAsrInternal': str(asrAsrInternalAdd), 'ebsStorageInternal': str(ebsStorageInternalAdd),
                         'ebaStorageInternal': str(ebaStorageInternalAdd), 'msossfmInternal': str(msossfmInternalAdd),
                         'ebaInternal': str(ebaInternalAdd)
                        }
    except Exception as error:
        logger.error("LSV Router Object not found for cluster: " + str(clusterObj.name) + " or unable to build up LVS Router Values. " + str(error))
    return oldValues,addValues,editValues,lVSRouterValues

def checkIfLVSRouterIPAddressAssigned(lVSRouterValues,clusterId,publicIdentifier):
    '''
    The checkIfIPAdressAssigned function checks if IP addresses are already in use before creating any
    '''
    checkipv4 = [lVSRouterValues['pmExternal'], lVSRouterValues['fmExternal'],
                 lVSRouterValues['cmExternal'], lVSRouterValues['svcPMstorage'],
                 lVSRouterValues['svcFMstorage'], lVSRouterValues['svcCMstorage'],
                 lVSRouterValues['svcStorage'], lVSRouterValues['scpSCPstorage'], lVSRouterValues['scpStorage'],
                 lVSRouterValues['scpSCPexternal'], lVSRouterValues['evtStorage'],
                 lVSRouterValues['strExternal'], lVSRouterValues['strSTRexternal2'], lVSRouterValues['strSTRexternal3'],
                 lVSRouterValues['strSTRstorage'], lVSRouterValues['strStorage'],
                 lVSRouterValues['esnSTRstorage'], lVSRouterValues['esnSTRinternal'],
                 lVSRouterValues['ebsStorage'], lVSRouterValues['asrAsrExternal'],
                 lVSRouterValues['asrAsrInternal'], lVSRouterValues['ebaStorage'],
                 lVSRouterValues['msossfmExternal']]

    checkipv6 = [lVSRouterValues['fmExternalIPv6'], lVSRouterValues['cmExternalIPv6'], lVSRouterValues['esnSTRexternalIPv6'],
                 lVSRouterValues['strExternalIPv6'], lVSRouterValues['strSTRexternalIPv62'], lVSRouterValues['strSTRexternalIPv63'],
                 lVSRouterValues['asrAsrExternalIPv6'], lVSRouterValues['msossfmExternalIPv6']]

    checkInternalIPv4 = [lVSRouterValues['pmInternal'], lVSRouterValues['fmInternal'], lVSRouterValues['cmInternal'], lVSRouterValues['svcStorageInternal'],
                         lVSRouterValues['scpSCPinternal'], lVSRouterValues['scpStorageInternal'], lVSRouterValues['evtStorageInternal'],
                         lVSRouterValues['strInternal'], lVSRouterValues['strSTRinternal2'], lVSRouterValues['strSTRinternal3'],
                         lVSRouterValues['strStorageInternal'], lVSRouterValues['esnSTRinternal'], lVSRouterValues['esnStorageInternal'],
                         lVSRouterValues['ebsStorageInternal'], lVSRouterValues['asrStorageInternal'], lVSRouterValues['ebaStorageInternal'],
                         lVSRouterValues['msossfmInternal']]

    checkInternalIPv6 = [lVSRouterValues['fmInternalIPv6'], lVSRouterValues['cmInternalIPv6'], lVSRouterValues['scpSCPinternalIPv6'],
                         lVSRouterValues['strSTRinternalIPv6'], lVSRouterValues['strSTRinternalIPv62'], lVSRouterValues['strSTRinternalIPv63'],
                         lVSRouterValues['esnSTRinternalIPv6'], lVSRouterValues['msossfmInternalIPv6']]
    for item in checkInternalIPv4:
        if IpAddress.objects.filter(address=str(item), ipv4UniqueIdentifier=clusterId).exists():
            return (1,"Internal IPaddress: " + str(item) + " already in use in this cluster")
    for item in checkInternalIPv6:
        if IpAddress.objects.filter(ipv6_address=str(item), ipv6UniqueIdentifier=clusterId).exists():
            return (1,"Internal IPv6  IPaddress: " + str(item) + " already in use in this cluster")
    for item in checkipv4:
        if IpAddress.objects.filter(address=str(item), ipv4UniqueIdentifier=publicIdentifier).exists():
            return (1,"Public IPaddress: " + str(item) + " already in use in this or another cluster")
    for item in checkipv6:
        if IpAddress.objects.filter(ipv6_address=item, ipv6UniqueIdentifier=publicIdentifier).exists():
            return (1,"Public IPaddress: " + str(item) + " already in use in this or another cluster")
    return 0, "All OK"

def getFreeServiceIPRange(generateServicesIpRangesJsonObj,blankEntriesWithinSed,deploymentId,resultMessage):
    '''
    Function used to calculate the next available IP from a given Range
    '''
    try:
        # Get All the IP's in the Deployment
        deploymentObj = Cluster.objects.get(id=deploymentId)
        allDeploymentIps=getAllIPsInCluster(deploymentObj)
    except Exception as e:
        message = "ERROR: Unable to get the deployment information using deployment id " + str(deploymentId) + " Exception: " + str(e)
        return (1,message,resultMessage)
    numberOfIpRequired = 0
    try:
        serviceAndIpList = []
        for ipType,serviceVms in blankEntriesWithinSed.items():
            if "ipv6" in ipType.lower():
                value = "ipv6"
            else:
                value = "ipv4"
            numberOfIpRequired = len(serviceVms)
            ipFinalList = []
            for ipRangeValues in generateServicesIpRangesJsonObj:
                ipList = []
                startIp = ""
                endIp = ""
                if str(ipType) in ipRangeValues.values():
                    startIp = ipRangeValues.get(str(value) + 'AddressStart')
                    endIp = ipRangeValues.get(str(value) + 'AddressEnd')
                    (ret,ipList,count) = CheckForIPInRange(allDeploymentIps,startIp,endIp,ipList,numberOfIpRequired)
                    if (ret != 0):
                        return (0,IPAddress)
                    # Get we get all the IP's we need or do we need to go to the Next Range
                    ipFinalList.extend(ipList)
                    if count < numberOfIpRequired:
                        numberOfIpRequired = numberOfIpRequired - count
                    else:
                        numberOfIpRequired = 0
                        break
                else:
                    continue
            if numberOfIpRequired != 0:
                message= "WARNING: Unable to auto assign IP for " + str(ipType) + ", please ensure there is an range assigned in the deployment or that the range already registered is not exhausted"
                resultMessage.append(str(message))
            serviceAndIpList.append(zip(serviceVms,ipFinalList))
        return (0,serviceAndIpList,resultMessage)
    except Exception as e:
        message = "ERROR: Unable to calculate the next available IP address from the ranges. Exception " + str(e)
        logger.error(str(message))
        return (1,message,resultMessage)

def CheckForIPInRange(allDeploymentIps,startIp,endIp,ipList,numberOfIpRequired=None):
    '''
    Function used to get the next available IP within a range and ensure the IP is not already used within the system
    '''
    count = 0
    if numberOfIpRequired == None:
        numberOfIpRequired = 1
    ipRangeList = iptools.IpRange(startIp,endIp)
    try:
        count = 0
        for ipCheck in ipRangeList:
            if ipCheck in allDeploymentIps:
                continue
            else:
                ipList.append(ipCheck)
                count += 1
            if count > numberOfIpRequired:
                break
        return (0,ipList,count)
    except Exception as e:
        message = "ERROR: Getting Next Free IP From Range " + str(startIp) + " To " + str(startEnd) + ".\n Exception: " + str(e)
        logger.error(str(message))
        return (1,message,count)

def getNextAvailableIPInRange(allDeploymentIps, startIp, endIp, duplicatePublicIps=None):
    '''
    Function used to get the next available IP within a range to assign to a service and ensure the IP is not already used within the system
    '''
    ipRangeList = iptools.IpRange(startIp,endIp)
    try:
        for ipCheck in ipRangeList:
            logger.info('checking ' + str(ipCheck))
            if ipCheck in allDeploymentIps:
                logger.info('ip already used in deployment')
                continue
            elif doNotUseIpCheck(ipCheck):
                continue
            elif duplicatePublicIps is not None and ipCheck in duplicatePublicIps:
                logger.info('Ip' + str(ipCheck) + ' is used, getting next free IP from range.')
                continue
            else:
                return (0, ipCheck)
        return (1, ipCheck)
    except Exception as e:
        message = "ERROR: Getting Next Free IP From Range " + str(startIp) + " To " + str(startEnd) + ".\n Exception: " + str(e)
        logger.error(str(message))
        return (1,message)

def changeFileToList(ddXmlFileName):
    '''
    Function to create a str of a complete file for easier parsing of the file
    '''
    try:
        ddServiceVmList = []
        with io.open(ddXmlFileName, 'r') as myFile:
            myFile = myFile.readlines()
        for line in myFile:
            ddSedItem = re.findall(r"%%(.*?)%%", line)
            if ddSedItem:
                for item in ddSedItem:
                    cleanItem = item.replace("%%","")
                    if "," in cleanItem:
                        cleanItem = cleanItem.split(",")
                        for item in cleanItem:
                            ddServiceVmList.append(str(item))
                    else:
                        ddServiceVmList.append(str(cleanItem))
        ddServiceVmList = list(set(ddServiceVmList))
        return (0,ddServiceVmList)
    except Exception as e:
        message = "ERROR: Unable to parse the Deployment description xml file, Exception: " + str(e)
        return (1,message)

def parseDdInfoConfig(ddInfoFileName):
    '''
    Function to parse the Deployment Description info text for service to vm mapping
    '''
    servicesToVmList = dict()
    try:
        with io.open(ddInfoFileName, 'r') as myFile:
            for line in myFile:
                if '[Deployment Services Layout]' in line:
                    break
            for line in myFile:
                if line in ['\n', '\r\n']:
                    break
                key = line.split(':')[0]
                values = line.split(':')[1]
                servicesToVmList[key] = values.lstrip("u' ['").strip().rstrip("']").split(", ")

        return (0,servicesToVmList)
    except Exception as e:
        message = "ERROR: Unable to parse the Deployment description Info file, Exception: " + str(e)
        return (1,message)

def updateSedWithMissingEntries(newSedEntries,sed,deploymentId,resultMessage):
    '''
    Function to add the missing service vm info into the SED str
    '''
    cluster = Cluster.objects.get(id=deploymentId)
    # Get info for the MgtServer dns IP address
    dns = cluster.management_server.server.dns_serverA
    try:
        for serviceInfo in newSedEntries:
            for individualServiceInfo in serviceInfo:
                serviceName = "=".join(individualServiceInfo)
                sed = re.sub("(?m)^" + individualServiceInfo[0] + "=", serviceName, sed)
                if "_ipaddress" in individualServiceInfo[0]:
                    individualServiceHostname = individualServiceInfo[0].replace("_ipaddress","_hostname")
                    # Does it require a hostname
                    if re.findall("(?m)^" + individualServiceHostname, sed):
                        if "192.168.0." in str(individualServiceInfo[1]):
                            output = "node" + str(individualServiceInfo[1]).split(".")[3] + ".vts.com"
                        else:
                            status, output = commands.getstatusoutput("nslookup " + individualServiceInfo[1] + " " + dns + " | grep name | sed -e 's/.*name = //g' -e 's/.*ame://g' -e 's/\.$//'")
                        if output != "":
                            # changes atrcxbxxx.athtem.eei.ericsson.se to atrcxbxxx
                            (hostname, ath) = output.split('.')[:2]
                            sed = re.sub("(?m)^" + individualServiceHostname + "=", individualServiceHostname + "=" + hostname, sed)
                        else:
                            message = "WARNING: Unable to set the hostname for IP Address " + str(individualServiceInfo[1]) + " assigned to service VM " + str(individualServiceInfo[0]).replace('\n', '')
                            resultMessage.append(str(message))
        sedList = sed.split()
        return (0,sedList,resultMessage)
    except Exception as e:
        message = "ERROR: Unable to update the SED with the new entries. Exception: " + str(e)
        return (1,message,resultMessage)

def addInternalAndJGroupRange(generateServicesIpRangesJsonObj,deploymentId=None):
    '''
    Function used to attach the internal and jgroup ranges to the range list
    '''
    if deploymentId is None:
        internalList = ["PDU-Priv_virtualImageInternalJgroup","PDU-Priv-2_virtualImageInternal","PDU-Priv-2_virtualImageInternalIPv6"]
    else:
        internalList = ["PDU-Priv_virtualImageInternalJgroup","PDU-Priv-2_virtualImageInternal", "ClusterId_" + str(deploymentId)]
    for rangeItem in internalList:
        if rangeItem == "PDU-Priv_virtualImageInternalJgroup":
            ipTypeName = "jgroups"
        elif rangeItem == "PDU-Priv-2_virtualImageInternal":
            ipTypeName = "internal"
        elif rangeItem == "ClusterId_" + str(deploymentId):
            ipTypeName = "IPv6 Internal"
        elif rangeItem == "PDU-Priv-2_virtualImageInternalIPv6":
            ipTypeName = "IPv6 Internal"
        ipRangeItemObj = IpRangeItem.objects.get(ip_range_item=rangeItem)
        ipRange = IpRange.objects.filter(ip_range_item=ipRangeItemObj).order_by('start_ip')
        for ip in ipRange:
            rangeDict = {}
            rangeDict["ipTypeName"] = ipTypeName
            if ipTypeName == "IPv6 Internal":
               rangeDict["ipv4AddressStart"] = None
               rangeDict["ipv4AddressEnd"] = None
               rangeDict["ipv6AddressStart"] = ip.start_ip
               rangeDict["ipv6AddressEnd"] = ip.end_ip
            else:
               rangeDict["ipv4AddressStart"] = ip.start_ip
               rangeDict["ipv4AddressEnd"] = ip.end_ip
               rangeDict["ipv6AddressStart"] = None
               rangeDict["ipv6AddressEnd"] = None
            rangeDict["ipTypeId"] = 1110 + ip.id
            rangeDict["id"] = 1110 + ip.id
            generateServicesIpRangesJsonObj.append(rangeDict)
    return (0,generateServicesIpRangesJsonObj)

def extractRpmFile(artifactName,tmpArea):
    '''
    Function used to extract an rpm without installing it into a specified directory
    '''
    try:
        os.chdir(tmpArea)
        os.system("rpm2cpio " + str(artifactName) + " | cpio -idmv > /dev/null 2>&1")
        return (0, "SUCCESS")
    except Exception as e:
        message = "ERROR: Unable to extract the deployment description package. Exception: " + str(e)
        return (1,message)

def findFile(tmpArea,depDescFileName):
    '''
    Function used to find a file in a given directory structure and return the full directory structure to the file
    '''
    try:
        for root, dirs, files in os.walk(tmpArea):
            if depDescFileName in files:
                return (0,os.path.join(root, depDescFileName))
        message = "ERROR: Unable to find the deployment description xml file within the deployment template package. Please ensure the artifact exists in Nexus."
        return (1,message)
    except Exception as e:
        message = "ERROR: Unable to find the deployment description xml file within the deployment template package. Please ensure the artifact exists in Nexus. Exception: " + str(e)
        return (1,message)

def findItemBetweenTwoKeys(searchStr, firstKey, lastKey ):
    '''
    Function used to search for a string between two keys
    '''
    try:
        start = searchStr.index( firstKey ) + len( lastKey )
        end = searchStr.index( firstKey, lastKey )
        return (0,searchStr[start:end])
    except Exception as e:
        message = "ERROR: Unable to parse the deployment descripttion to return all keys, issue with line " + str(searchStr) + ", Exception: " + str(e)
        return (1,message)

def downloadSliceFile(version, tmpArea, artifact, group):
    '''
    Function used to download the slices to a tmpArea
    '''
    try:
        snapVersion = version + "-SNAPSHOT"
        nexusUrlApi=config.get('DMT_AUTODEPLOY', 'nexus_url_api')
        os.system("curl -f -o " + tmpArea + "/" + str(artifact) + "-" + str(snapVersion) + ".zip -L -# \"" + str(nexusUrlApi) + "/artifact/maven/redirect?r=snapshots&g=" + str(group) + "&a=" + str(artifact) + "&e=zip&v=" + str(snapVersion) + "\" > /dev/null 2>&1")
        return (0, str(tmpArea) + "/" + str(artifact) + "-" + str(snapVersion) + ".zip")
    except Exception as e:
        message = "ERROR: Unable to downloaded the slice version defined. Exception: " + str(e)
        return (1,message)

def unzipFile(file,tmpArea):
    '''
    Function used to unzip a file to a given location
    '''
    try:
        os.system("unzip -o " + str(file) + " -d " + str(tmpArea) + " > /dev/null 2>&1")
        return (0,"SUCCESS")
    except Exception as e:
        message = "ERROR: Unable to unzip the snapshot deployment description package. Exception: " + str(e)
        return (1,message)

def getJumpServerIp(network):
    '''
    This function is used to set the jumpserver IP according to the network inputted
    '''
    jumpServerDetailsObj = DeploymentDhcpJumpServerDetails.objects.get(server_type="RhelJump")

    if network == "edn":
        jumpServerIp = jumpServerDetailsObj.edn_ip
    elif network == "youlab":
        jumpServerIp = jumpServerDetailsObj.youlab_ip
    elif network == "gtec_edn":
        jumpServerIp = jumpServerDetailsObj.gtec_edn_ip
    elif network == "gtec_youlab":
        jumpServerIp = jumpServerDetailsObj.gtec_youlab_ip
    else:
        jumpServerIp = jumpServerDetailsObj.ecn_ip
    return jumpServerIp

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(ComplexEncoder, obj).default(obj)
        except TypeError:
            return str(obj)

def updateDeploymentBaseline(clusterId=None,clusterName=None,osDetails=None,litpVersion=None,mediaArtifact=None,fromISO=None,patches=None,dropName=None,groupName=None,sedVersion=None,deploymentTemplates=None,tafVersion=None,masterBaseline=None,descriptionDetails=None,success=None,upgradePerformancePercent=None,productset_id=None,deliveryGroup=None,rfaStagingResult=None,rfaResult=None,teAllureLogUrl=None,upgradeAvailabilityResult=None,availability=None,buildURL=None,installType=None,deploytime=None,comment=None,slot=None,upgradeTestingStatus="OK",rfaPercent=None,shortLoopURL=None,upgradeFlagData=None, testPhase=None, confidenceLevel=None):
    '''
    Used to update the deploymentbaseline table on deployment initialization
    '''
    logger.debug("Updating Baseline Information")
    cifwkUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    clusterNameData = str(clusterName)
    clusterIDData = str(clusterId)
    osDetailsData = str(osDetails)
    litpVersionData = str(litpVersion)
    mediaArtifactData = str(mediaArtifact)
    fromISO = str(fromISO)
    patchesData = str(patches)
    dropNameData = str(dropName)
    tafVersionData = "None"
    masterBaselineData = "False"
    descriptionDetailsData = str(descriptionDetails)
    successData = "False"
    upgradePerformancePercentData = str(upgradePerformancePercent)
    productset_idData = str(productset_id)
    rfaStagingResultData = str(rfaStagingResult)
    rfaResultData = str(rfaResult)
    teAllureLogUrlData = str(teAllureLogUrl)
    upgradeAvailabilityResultData = str(upgradeAvailabilityResult)
    availabilityData = str(availability)
    buildURLData = str(buildURL)
    deploytimeData = str(deploytime)
    commentData = str(comment)
    upgradeTestingStatus = str(upgradeTestingStatus)
    rfaPercent = str(rfaPercent)
    shortLoopURL = str(shortLoopURL)
    installTypeData = str(installType)
    testPhaseData = str(testPhase)
    requiredServers = []
    delGroupList = []
    rollbackDetected = False
    fromISODrop = ''

    if deploymentTemplates != None:
        deploymentTemplatesData = deploymentTemplates.split('/')
        fullDeploymentData = "deploymentTemplates="+str(deploymentTemplatesData[len(deploymentTemplatesData)-1])
    else:
        deploymentTemplates = "deploymentTemplates="
        deploymentTemplatesData = "deploymentTemplates="
        fullDeploymentData = "deploymentTemplates="
    try:
        supportedBuildLogInstallGroups = config.get("CIFWK", "supportedBuildLogInstallGroups")
        supportedBuildLogInstallGroups = supportedBuildLogInstallGroups.split(", ")
        for supportedBuildLogInstallGroup in supportedBuildLogInstallGroups:
            clusterGroupListObjects = ClusterToInstallGroupMapping.objects.filter(group__installGroup__contains=supportedBuildLogInstallGroup)
            for itemObj in clusterGroupListObjects:
                requiredServers.append(str(itemObj.cluster.id))
        try:
            virtualAutoBuildlogClusters = VirtualAutoBuildlogClusters.objects.values('name')
            for virtualAutoBuildlogCluster in virtualAutoBuildlogClusters:
                requiredServers.append(str(virtualAutoBuildlogCluster['name']))
        except Exception as e:
            logger.debug("Error getting virtualAutoBuildlogClusters " + str(e))
    except Exception as e:
            logger.debug("Error getting supportedBuildLogInstallGroups " + str(e))
    sedVersionData = getSEDVersion(sedVersion)
    groupNameData = getInstallGroupData(cifwkUrl,clusterName)
    slotData = getSlotData(clusterId,requiredServers,installType)
    deliveryGroup = ''

    #If its an upgrade, get the ISO previously installed on the system and delivery group delta
    if DeploymentBaseline.objects.exists():
        defaultArtifact = config.get("FEM", "defaultArtifact")
        if installType == 'upgrade' or installType == 'softwareUpdateOnly':
            if fromISO:
                try:
                    fromISODrop = ISObuild.objects.get(version=fromISO,artifactId=defaultArtifact).drop.name
                except Exception as e:
                    logger.debug("Error getting fromISO drop details " + str(e))
            if testPhase != 'CDL':
                try:
                    deliveryGroup = getDeliveryGroupsDataForBuildlog(mediaArtifact, defaultArtifact, dropName, deliveryGroup)
                except Exception as e:
                    logger.debug("Error getting delivery groups " + str(e))
            else:
                deliveryGroup = ''
        elif(installType=='rollback'):
            logger.debug('Beginning parsing for rollback')
        else:
            #In the case of initial install get delivery group delta based on previous ISO version
            if testPhase != 'CDL':
                try:
                    deliveryGroup = getDeliveryGroupsDataForBuildlog(mediaArtifact, defaultArtifact, dropName, deliveryGroup)
                except Exception as e:
                    logger.debug("Error getting delivery groups " + str(e))
            else:
                deliveryGroup = ''
    if deliveryGroup!='':
        deliveryGroup = deliveryGroup[:-1]
    deliveryGroupData = deliveryGroup

    #Send update to the django rest interface if its a maintrack server
    if str(clusterId) in requiredServers:
        for key, value in confidenceLevel.iteritems():
            if "Deploy" in key:
                statusData = ''
                if "ENM-II" in key or "Micro" in key:
                    statusData = "BUSY DEPLOY II"
                elif "ENM-UG" in key or "SWUpdate" in key:
                    statusData = "BUSY DEPLOY UG"
                statusData += checkForTestPhase(testPhase)
                statusData += checkForInstallType(key)
                try:
                    DeploymentBaseline.objects.create(deploymentTemplates=deploymentTemplatesData,clusterName=clusterNameData,clusterID=clusterIDData,osDetails=osDetailsData,litpVersion=litpVersionData,mediaArtifact=mediaArtifactData,fromISO=fromISO,fromISODrop=fromISODrop,upgradePerformancePercent=upgradePerformancePercentData,patches=patchesData,dropName=dropNameData,groupName=groupNameData,sedVersion=sedVersionData,tafVersion=tafVersionData,descriptionDetails=descriptionDetailsData,masterBaseline=masterBaselineData,productset_id=productset_idData,deliveryGroup=deliveryGroupData,status=statusData,rfaStagingResult=rfaStagingResultData,rfaResult=rfaResultData,teAllureLogUrl=teAllureLogUrlData,upgradeAvailabilityResult=upgradeAvailabilityResultData,availability=availabilityData,buildURL=buildURLData,installType=installTypeData,deploytime=deploytimeData,comment=commentData,slot=slotData,rfaPercent=rfaPercent,upgradeTestingStatus=upgradeTestingStatus,shortLoopURL=shortLoopURL)
                except Exception as e:
                    logger.debug("Error updating Auto buildlog Deploy," + str(e))
            elif "Rollback" in key:
                statusData = "BUSY ROLLBACK"
                rollbackDetected = True
                statusData += checkForTestPhase(testPhase)
                try:
                    idToUpdate = DeploymentBaseline.objects.exclude(status='PASSED ROLLBACK').exclude(status='FAILED ROLLBACK').exclude(status='BUSY ROLLBACK').filter(clusterID=clusterId).values('id','fromISO').reverse().order_by('createdAt')[0:1].get()
                except Exception as e:
                    logger.debug("No idToUpdate exists for a rollback," + str(e))
                    idToUpdate = None
                try:
                    DeploymentBaseline.objects.create(deploymentTemplates=deploymentTemplatesData, clusterName=clusterNameData,clusterID=clusterIDData,osDetails=osDetailsData,litpVersion=litpVersionData,mediaArtifact=mediaArtifactData,fromISO=fromISO,fromISODrop=fromISODrop,upgradePerformancePercent=upgradePerformancePercentData,patches=patchesData,dropName=dropNameData,groupName=groupNameData,sedVersion=sedVersionData,tafVersion=tafVersionData,descriptionDetails=descriptionDetailsData,masterBaseline=masterBaselineData,productset_id=productset_idData,deliveryGroup=deliveryGroupData,status=statusData,rfaStagingResult=rfaStagingResultData,rfaResult=rfaResultData,teAllureLogUrl=teAllureLogUrlData,upgradeAvailabilityResult=upgradeAvailabilityResultData,availability=availabilityData,buildURL=buildURLData,installType=installTypeData,deploytime=deploytimeData,comment=commentData,slot=slotData,rfaPercent=rfaPercent,upgradeTestingStatus=upgradeTestingStatus,shortLoopURL=shortLoopURL)
                except Exception as e:
                    logger.debug("Error updating Auto buildlog Rollback," + str(e))
            elif "UG-Availability" in key:
                continue
            else:
                if "RFA" in key:
                    statusData = "BUSY RFA250"
                elif "UG-Performance" in key:
                    statusData = "BUSY UG PERF"
                if not "UG-Availability" in key:
                    statusData += checkForTestPhase(testPhase)
                    statusData += checkForInstallType(key)
                try:
                    idToUpdate = DeploymentBaseline.objects.filter(clusterID=clusterId).values('id').reverse().order_by('createdAt')[0:1].get()
                    idToUpdate = str(idToUpdate.get('id'))
                    rowToUpdate = DeploymentBaseline.objects.get(id=idToUpdate)
                    rowToUpdate.status = statusData
                    rowToUpdate.availability = availabilityData
                    rowToUpdate.save()
                except Exception as e:
                    logger.debug("No idToUpdate exists for test loop," + str(e))
                    idToUpdate = None
    else:
        logger.debug("Server is not part of supportedBuildLogInstallGroups, skipping persistance to the DB...")

def checkForTestPhase(testPhase):
    '''
    Used to append the testPhase to status for auto buildlog
    '''
    if testPhase == "DROPBACK":
        return "(DB)"
    elif testPhase == "CDL":
        return "(CDL)"
    elif testPhase == "PLM":
        return "(PLM)"
    elif testPhase == "MTE":
        return "(MTE)"
    elif testPhase == "LongLoop":
        return "(LL)"
    else:
        return ""

def checkForInstallType(key):
    '''
    Used to append the installType if (Software Update) to status for auto buildlog
    '''
    if "SWUpdate" in key:
        return "(SWUpdate)"
    if "Micro" in key:
        return "(Micro)"
    else:
        return ""

def getDeliveryGroups(result,deliveryGroup):
    '''
    Used to format the delivery groups
    '''
    if not str(result['deliveryGroup__id']) in str(deliveryGroup):
        if(result['deliveryGroup_status']=='delivered'):
            deliveryGroup = deliveryGroup + str(result['deliveryGroup__id'])
        else:
            deliveryGroup = deliveryGroup + '-' + str(result['deliveryGroup__id'])
        artifactCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=result.get('deliveryGroup__id')).exclude(packageRevision__category__name='testware').count()
        testwareCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=result.get('deliveryGroup__id'),packageRevision__category__name='testware').count()
        if artifactCount == 0 and testwareCount > 0:
            deliveryGroup = deliveryGroup+'(tw)'
        deliveryGroup = deliveryGroup + ','
    return deliveryGroup

def getDeliveryGroupsDataForBuildlog(mediaArtifact, defaultArtifact, dropName, deliveryGroup):
    '''
    Getting the delivery Group Data for Productware ISO and the Testware ISOs that is mapped to it.
    '''
    try:
        mediaIds = []
        jsonFields = ('iso__id','iso__version','iso__mediaArtifact__name','deliveryGroup__id','deliveryGroup_status')
        mediaArtifactObj = ISObuild.objects.only('id').values('id').get(version=mediaArtifact,artifactId=defaultArtifact)
        try:
            prodTWmediaMap = ProductTestwareMediaMapping.objects.filter(productIsoVersion__id=mediaArtifactObj['id']).only('testwareIsoVersion__id').values('testwareIsoVersion__id').order_by('-id')[0]
            mediaIds.append(prodTWmediaMap['testwareIsoVersion__id'])
        except:
            logger.debug("No Testware Media Artifact Version Mapped to this Productware Media Artifact Version")
        mediaIds.append(mediaArtifactObj['id'])
        results = list(IsotoDeliveryGroupMapping.objects.only(jsonFields).filter(iso__drop__release__product__name ='ENM',iso__drop__name=dropName, iso__id__in=mediaIds).order_by('-iso__build_date','-modifiedDate').values(*jsonFields))
        for result in results:
            deliveryGroup = getDeliveryGroups(result,deliveryGroup)
    except Exception as e:
        logger.debug("Error getting delivery groups " + str(e))
    return deliveryGroup

def getSEDVersion(sedVersion):
    '''
    Used to get the sed used for the deployment
    '''
    if sedVersion == "MASTER":
        if deployProduct == "LITP2":
            sedVersion = dmt.utils.getVirtualMasterSedVersion()
        else:
            sedVersion = dmt.utils.getMasterSedVersion()
    sedVersionData = str(sedVersion)
    return sedVersionData

def getInstallGroupData(cifwkUrl,clusterName):
    '''
    Used to get the install group data
    '''
    url = cifwkUrl + "/api/deployment/clustertogroup/" + clusterName
    groupNameData= ""
    response = None
    try:
        response = urllib2.urlopen(url)
        if "groupName" in str(response.read()):
            data = json.loads(response.read())
            jsonData = data[0]
            groupNameData= str(jsonData['groupName'])
        else:
            groupNameData= "No Install group found"
    except urllib2.URLError:
        groupNameData= "No Install group found"
        logger.debug("Url Error with: " + str(url) + " cluster name: " + str(clusterName))
    except Exception as e:
        groupNameData= "No Install group found"
        logger.debug("Error getting a Install group for "+ str(clusterName) +": " + str(e))
    finally:
        if response:
            response.close()
    if "No" in groupNameData:
        try:
            groupNameData = str(installGroup)
        except:
            logger.debug("installGroup not used")
    return groupNameData

def getSlotData(clusterId,requiredServers,installType):
    '''
    Generate the data for the slot based on whether it occurs on the same day
    '''
    createdAtData = datetime.now()
    fields = ('createdAt','slot')

    if DeploymentBaseline.objects.exists():
        previous = DeploymentBaseline.objects.order_by('-createdAt').values(*fields)[0]
        previousCreatedAt = previous['createdAt']
        previousSlotNumber = previous['slot']

        #Only increase the slot for maintrack servers
        if clusterId in requiredServers and installType != 'rollback':
            if(previousCreatedAt.date() == createdAtData.date()):
                slot = int(previousSlotNumber)+1
            else:
                slot = 1
        else:
            slot = previousSlotNumber
        slotData = str(slot)
        return slotData
    else:
        return "1"

def checkUpgradeTestsPassed(clusterId):
    '''
        Used after each test loop to check if parrallel loops have finished, updates the cluster status based on results
    '''
    try:
        row = DeploymentBaseline.objects.filter(clusterID=clusterId).values('id','rfaPercent','upgradeTestingStatus','upgradePerformancePercent').reverse().order_by('createdAt')[0:1].get()
        idToUpdate = str(row.get('id'))
        rfaPercentReturned = str(row.get('rfaPercent'))
        rfaStagingPercentReturned = str(row.get('upgradeTestingStatus'))
        upgradePerformancePercentReturned = str(row.get('upgradePerformancePercent'))
    except Exception as e:
        logger.debug("Error getting idToUpdate " + str(e))
        idToUpdate = None
        rfaPercentReturned = None
        rfaStagingPercentReturned = None
        upgradePerformancePercentReturned = None

    if rfaPercentReturned == "" or upgradePerformancePercentReturned == "":
        logger.warn('There are other loops that are NOT finished yet.')
    else:
        updateDeploymentStatusInPortal(clusterId, "IDLE")

def updateDeploymentStatusInPortal(clusterId, status):
    cifwkUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    req = 'curl -X POST --insecure --data "clusterId=' + clusterId + '&status=' + status + '" ' + cifwkUrl + '/deploymentStatus/deploymentStatus/'
    logger.debug(req)
    ret, statusOutput = commands.getstatusoutput(str(req))
    logger.debug("Return value: " + str(ret) + " status: " + str(statusOutput))

def updateDeploymentBaselineAfter(clusterId, clusterName=None, testURL=None,confidenceLevel=None,testPhase=None):
    '''
    Used to update the deploymentbaseline table post loop
    '''
    deployDetected = False
    rollbackDetected = False
    rfa250Detected = False
    rfa250StagingDetected = False
    upgradeAvailabilityDetected = False
    upgradePerformanceDetected = False
    response = None

    try:
        cifwkUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    except Exception as e:
        logger.debug("Error getting data from config " + str(e))

    for key, value in confidenceLevel.iteritems():
        if "RFAStaging" in key:
            rfa250StagingDetected = True
            url = testURL + '/data/total.json'
            try:
                response = urllib2.urlopen(url)
                data = json.load(response)
                clevelFinal = (int(data['statistic']['passed']) * 100) / int(data['statistic']['total'])
                upgradeTestingStatus = str(clevelFinal) + '%'
            except urllib2.URLError:
                logger.debug("Url Error with: " + str(url) + " cluster name: " + str(clusterName))
                upgradeTestingStatus = ''
            finally:
                if response:
                    response.close()
            testURL = str(testURL)
            if "SUCCESS" in value:
                availability = "IDLE"
                status = "PASSED RFA250"
            elif "FAILURE" or "ABORTED" in value:
                status = "FAILED RFA250"
                availability = "QUARANTINE"
            else:
                availability = None
                status = None
        elif "RFA" in key:
            rfa250Detected = True
            url = testURL + '/data/total.json'
            try:
                response = urllib2.urlopen(url)
                data = json.load(response)
                clevelFinal = (int(data['statistic']['passed']) * 100) / int(data['statistic']['total'])
                rfaPercent = str(clevelFinal) + '%'
            except urllib2.URLError:
                logger.debug("Url Error with: " + str(url) + " cluster name: " + str(clusterName))
                rfaPercent = ''
            finally:
                if response:
                    response.close()
            testURL = str(testURL)
            if "SUCCESS" in value:
                availability = "IDLE"
                status = "PASSED RFA250"
            elif "FAILURE" or "ABORTED" in value:
                status = "FAILED RFA250"
                availability = "QUARANTINE"
            else:
                availability = None
                status = None
        elif "UG-Performance" in key:
            upgradePerformanceDetected = True
            if "apt.seli.wh.rnd.internal.ericsson.com" in testURL:
                url = testURL.replace('/index.html','') + '/data/total.json'
            else:
                url = testURL + '/data/total.json'
            try:
                response = urllib2.urlopen(url)
                data = json.load(response)
                clevelFinal = (int(data['statistic']['passed']) * 100) / int(data['statistic']['total'])
                upgradePerformancePercent = str(clevelFinal) + '%'
            except urllib2.URLError:
                logger.debug("Url Error with: " + str(url) + " cluster name: " + str(clusterName))
                upgradePerformancePercent = ''
            finally:
                if response:
                    response.close()
            testURL = str(testURL)
            if "SUCCESS" in value:
                availability = "IDLE"
                status = "PASSED UG PERF"
            elif "FAILURE" or "ABORTED" in value:
                status = "FAILED UG PERF"
                availability = "QUARANTINE"
            else:
                availability = None
                status = None
        elif "UG-Availability" in key:
            upgradeAvailabilityDetected = True
            url = testURL + '/data/total.json'
            try:
                response = urllib2.urlopen(url)
                data = json.load(response)
                clevelFinal = (int(data['statistic']['passed']) * 100) / int(data['statistic']['total'])
                if clevelFinal == 100:
                    success='True'
                else:
                    success='False'
            except urllib2.URLError:
                logger.debug("Url Error with: " + str(url) + " cluster name: " + str(clusterName))
                upgradeAvailabilityResult = ''
            finally:
                if response:
                    response.close()
            testURL = str(testURL)
        elif "Rollback" in key:
            rollbackDetected = True
            if "SUCCESS" in value:
                availability = "IDLE"
                status = "PASSED ROLLBACK"
            elif "FAILURE" or "ABORTED" in value:
                availability = "QUARANTINE"
                status = "FAILED ROLLBACK"
            else:
                availability = None
                status = None
        else:
            testURL=''
            deployDetected = True
            if "SUCCESS" in value:
                if "ENM-II" in key or "Micro" in key:
                    availability = "IDLE"
                    status = "PASSED II"
                else:
                    availability = "IDLE"
                    status = "PASSED UG"
            elif "FAILURE" or "ABORTED" in value:
                if "ENM-II" in key or "Micro" in key:
                    status = "FAILED II"
                    availability = "QUARANTINE"
                else:
                    availability = "QUARANTINE"
                    status = "FAILED UG"
            else:
                availability = None
                status = None

    if not "UG-Availability" in key:
        status += checkForTestPhase(testPhase)
        status += checkForInstallType(key)

    requiredServers = []
    deploytime = ''
    try:
        idToUpdate = DeploymentBaseline.objects.filter(clusterID=clusterId).values('id','createdAt').reverse().order_by('createdAt')[0:1].get()
        previousTimestamp = idToUpdate.get('createdAt')
        idToUpdate = str(idToUpdate.get('id'))
        if deployDetected:
            timeDelta = datetime.now() - previousTimestamp
            timeDelta = timeDelta - timedelta(microseconds=timeDelta.microseconds)
            deploytime = str(timeDelta)
    except Exception as e:
        logger.debug("Error getting idToUpdate " + str(e))
        idToUpdate = None
        diff = None
        deploytime = None
    try:
        supportedBuildLogInstallGroups = config.get("CIFWK", "supportedBuildLogInstallGroups")
        supportedBuildLogInstallGroups = supportedBuildLogInstallGroups.split(", ")
        for supportedBuildLogInstallGroup in supportedBuildLogInstallGroups:
            clusterGroupListObjects = ClusterToInstallGroupMapping.objects.filter(group__installGroup__contains=supportedBuildLogInstallGroup)
            for itemObj in clusterGroupListObjects:
                requiredServers.append(str(itemObj.cluster.id))
        try:
            virtualAutoBuildlogClusters = VirtualAutoBuildlogClusters.objects.values('name')
            for virtualAutoBuildlogCluster in virtualAutoBuildlogClusters:
                requiredServers.append(str(virtualAutoBuildlogCluster['name']))
        except Exception as e:
            logger.debug("Error getting virtualAutoBuildlogClusters " + str(e))
    except Exception as e:
            logger.debug("Error getting supportedBuildLogInstallGroups " + str(e))

    if (str(clusterId) in requiredServers):
        rowToUpdate = DeploymentBaseline.objects.get(id=idToUpdate)
        if not upgradeAvailabilityDetected:
            rowToUpdate.status = status
            rowToUpdate.availability = availability
        if (deployDetected or rollbackDetected):
            rowToUpdate.deploytime = deploytime
        elif (rfa250StagingDetected):
            rowToUpdate.rfaStagingResult = testURL
            rowToUpdate.upgradeTestingStatus = upgradeTestingStatus
        elif (upgradeAvailabilityDetected):
            rowToUpdate.upgradeAvailabilityResult = testURL
            rowToUpdate.success = success
        elif (upgradePerformanceDetected):
            rowToUpdate.teAllureLogUrl = testURL
            rowToUpdate.upgradePerformancePercent = upgradePerformancePercent
        else:
            rowToUpdate.rfaResult = testURL
            rowToUpdate.rfaPercent = rfaPercent
        rowToUpdate.save()
    else:
        logger.debug("Server is not part of supportedBuildLogInstallGroups, skipping persistance to the DB...")
    if (rfa250StagingDetected or rfa250Detected or upgradePerformanceDetected):
        checkUpgradeTestsPassed(clusterId)

def getDeploymentInfo(product,productType,productDrop,version):
    '''
    Function used to return the deployment information, deploy script, sed version and mt utils package which is attached to an ENM ISO
    '''
    result = {}
    if version != None:
        productVersionCombined = productDrop + "::" + version
    else:
        productVersionCombined = productDrop + "::LATEST"
        version = "LATEST"
    if productType == "productset":
        (drop,litpDrop,osVersion,osVersion8,osPatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,nasConfig,nasRhelPatch,cfgTemplate,deployScriptVersion,mtUtilsVersion,otherUtilities,psVersion) = dmt.deploy.getProductDropInfo(productVersionCombined,product)
        if drop == None:
            message = "Error finding information for product set data entered, please try again."
            return (1,message)
        elif "Error" in str(drop):
            return (1,drop)
    elif productType == "drop":
        (isoName,isoVersion,isoUrl,hubIsoUrl,message) = dmt.deploy.getIsoName(productDrop,version,product)
        if isoName == 1:
            return (1,message)
        (drop,cfgTemplate,deployScriptVersion,mtUtilsVersion,message,otherUtilities) = dmt.utils.getDeploymentInfoFromIso(productDrop,isoVersion,product)
        if drop == 1:
            return (1,message)
    else:
        message = "Please ensure the product type entered is of type productset or drop"
        return (1,message)
    result[product + 'IsoInfo']={}
    result[product + 'IsoInfo']['drop']=drop.split("::")[0]
    result[product + 'IsoInfo']['isoVersion']={}
    result[product + 'IsoInfo']['isoVersion']=drop.split("::")[1]
    result[product + 'IsoInfo']['isoVersionDeploymentInfo']={}
    result[product + 'IsoInfo']['isoVersionDeploymentInfo']['sedFileVersion']=cfgTemplate
    result[product + 'IsoInfo']['isoVersionDeploymentInfo']['deployScriptVersion'] = deployScriptVersion
    if mtUtilsVersion:
        result[product + 'IsoInfo']['isoVersionDeploymentInfo']['mtUtilsVersion'] = mtUtilsVersion
    if otherUtilities:
        for utility in otherUtilities:
            utilityName,utilityVersion = utility.split("::")
            result[product + 'IsoInfo']['isoVersionDeploymentInfo'][utilityName] = utilityVersion
    return (0,result)

def getDeploymentInfoFromIso(productDrop,version,product):
    '''
    Function used to get the miscellaneous information for a deployment for an iso version inputted
    '''
    errorMsg = ""
    otherUtilities = []
    drop = productDrop + "::" + version
    cfgTemplate = deployScriptVersion = mtUtilsVersion = None
    try:
        fields = ("id","name","release__product","release__iso_artifact","release__masterArtifact__mediaType")
        dropObj = Drop.objects.only(fields).values(*fields).get(name=productDrop,release__product__name=product)
    except:
        errorMsg = "Error finding Drop entered: '" + str(productDrop) + "' in database, please try again."
        logger.error(errorMsg)
        return 1,1,1,1,errorMsg
    try:
        requiredIsoFields= 'id','version','mediaArtifact__name','build_date','sed_build__version','deploy_script_version','mt_utils_version'
        iso = ISObuild.objects.filter(drop__id=dropObj['id'],version=version,mediaArtifact__testware=0, mediaArtifact__category__name="productware").only(requiredIsoFields).values(*requiredIsoFields).order_by('-build_date')[0]
    except:
        errorMsg = "Error finding ISO information for: '" + str(product) + " " + str(productDrop) + " ISO Version " + str(version) + "' in database, please try again."
        logger.error(errorMsg)
        return 1,1,1,1,errorMsg

    deploymentUtils = DeploymentUtilsToISOBuild.objects.filter(iso_build__drop__id=dropObj['id'],iso_build__version=iso['version'],active=True)
    if deploymentUtils:
        for utility in deploymentUtils:
            utilityName = str(utility.utility_version.utility_name.utility)
            utilityVersion = str(utility.utility_version.utility_version)
            if utilityName == "sedVersion":
                cfgTemplate = utilityVersion
            elif utilityName == "deployScript":
                deployScriptVersion = utilityVersion
            else:
                otherUtilities.append(utilityName + "::" + utilityVersion)
    else:
        if str(iso['sed_build__version']) != "None":
            cfgTemplate = str(iso['sed_build__version'])
        if str(iso['deploy_script_version']) != "None":
            deployScriptVersion = str(iso['deploy_script_version'])
        if str(iso['mt_utils_version']) != "None":
            mtUtilsVersion = str(iso['mt_utils_version'])

    return (drop,cfgTemplate,deployScriptVersion,mtUtilsVersion,errorMsg,otherUtilities)

def validateAutoDeployPackages(artifactList):
    '''
    The validateAutoDeployPackages function is a helper method for the validateAutoDeployPackages GET Rest Service
    '''
    message = "[{'success':'All Artifacts are valid'}]"
    artifactCategory = False
    for artifact in artifactList.split('@@'):
        if artifact.count("::") == 3:
            artifactName,artifactVersion,artifactCategory,remove = artifact.split("::")
        elif artifact.count("::") == 2:
            artifactName,artifactVersion,artifactCategory = artifact.split("::")
        else:
            artifactName,artifactVersion = artifact.split("::")

        if artifactCategory:
            try:
                Categories.objects.get(name=artifactCategory)
            except Exception as error:
                message = "[{'error':'Artifact " + str(artifact) + " media Category was not found, please try again'}]"
                logger.error(message)
                return message

        if "http" in artifactVersion:
            if not "://" in str(artifactVersion):
                artifactVersion = str(artifactVersion).replace(":/", "://")
            try:
                urllib2.urlopen(artifactVersion)
            except:
                message = "[{'error':'Artifact " + str(artifact) + " URL was not found, please try again'}]"
                logger.error(message)
                return message
        else:
            try:
                packageObj = Package.objects.get(name=artifactName)
                if "latest" not in artifactVersion.lower():
                    PackageRevision.objects.get(package=packageObj,version=artifactVersion)
                elif not PackageRevision.objects.filter(package=packageObj).exists():
                    message = "[{'error':'Artifact " + str(artifact) + " no versions of Artifact found for latest, please try again " + str(error) + "'}]"
                    logger.error(message)
                    return message
            except Exception as error:
                message = "[{'error':'Artifact " + str(artifact) + " Package Revison was not found, please try again " + str(error) + "'}]"
                logger.error(message)
                return message
    return message

def getLatestVersion(artifactList):
    '''
    The getLatestVersion function is a helper method for the getLatestVersion GET Rest Service
    '''
    latestVersion=""
    message=""
    for artifact in artifactList.split('@@'):
        if artifact.count("::")== 2:
            artifactName,artifactVersion,artifactCategory=artifact.split("::")
        else:
            artifactName,artifactVersion=artifact.split("::")
        if "latest" in artifactVersion.lower():
            try:
                packageObject = PackageRevision.objects.exclude(platform='sparc').filter(package__name=artifactName).order_by('version').latest('date_created')
                artifact= artifact.replace("Latest",packageObject.version).replace("latest",packageObject.version)
                latestVersion=latestVersion+"@@"+str(artifact)
            except Exception as error:
                message = "ERROR: Artifact Package Revison was not found, please try again"
                logger.error(message)
                return message
        else:
            if artifactVersion.count(".")==2:
                latestVersion=latestVersion+"@@"+str(artifact)
            elif "http" in artifactVersion.lower():
                latestVersion = "ERROR: Artifact cannot use snapshot version. It must contain keyword 'latest' or valid value for versions of an Artifact, please try again "
                break
            else:
                latestVersion = "ERROR: Artifact cannot be empty and must be valid value for versions of an Artifact, please try again"
                break
    if latestVersion.startswith("@"):
        latestVersion=latestVersion[2:]
    return latestVersion

def checkDhcpJumpSudoRequired(serverIp):
    '''
    Set the sudo command based on using the old DHCP Server or old Jump Server, sudo only required for the new servers
    '''
    oldJumpServerEcnIp = config.get('DMT_AUTODEPLOY', 'rhelJumpServer')
    oldJumpServerEdnIp = config.get('DMT_AUTODEPLOY', 'rhelJumpServerEdn')
    oldJumpServerYoulabIp = config.get('DMT_AUTODEPLOY', 'rhelJumpServerYouLab')

    oldDhcpServerEcnIp = config.get('DMT_AUTODEPLOY', 'dhcpServer')
    oldDhcpServerEdnIp = config.get('DMT_AUTODEPLOY', 'dhcpServerEdn')
    oldDhcpServerYoulabIp = config.get('DMT_AUTODEPLOY', 'dhcpServerYouLab')
    oldDhcpJumpServerList = [oldJumpServerEcnIp, oldJumpServerEdnIp, oldJumpServerYoulabIp, oldDhcpServerEcnIp, oldDhcpServerEdnIp, oldDhcpServerYoulabIp]

    sudo = "/usr/local/bin/sudo "

    if serverIp in oldDhcpJumpServerList:
        sudo = ""
    return sudo

def updateOrCreateClusterAdditionalProps(user, clusterId, ddp_hostname, cron, port, time):
    '''
    This function updates/creates Other Properties (DDP) for Deployment.
    '''
    response = ""
    action = "edit"
    try:
        if not Cluster.objects.filter(id=clusterId).exists():
            return "Given deployment ID does not exist."
        clusterObj = Cluster.objects.get(id=clusterId)
        if ClusterAdditionalInformation.objects.filter(cluster_id=clusterId).exists():
            ddpPropObj = ClusterAdditionalInformation.objects.get(cluster_id=clusterId)
            oldValues = [str(ddpPropObj.ddp_hostname) + "##DDP Hostname", str(ddpPropObj.cron) + "##Cron", str(ddpPropObj.port) + "##Port", str(ddpPropObj.time) + "##Time"]
            ddpPropObj.ddp_hostname=ddp_hostname
            ddpPropObj.cron=cron
            ddpPropObj.port=port
            ddpPropObj.time=time
            ddpPropObj.save(force_update=True)
            newValues = [str(ddpPropObj.ddp_hostname), str(ddpPropObj.cron), str(ddpPropObj.port), str(ddpPropObj.time)]
            changedContent = logChange(oldValues,newValues)
            message = "Edited Other Properties (DDP), " + str(changedContent)
            response = { "success" : "Additional Properties successfully been updated for cluster " + str(clusterId)}
        else:
            action = "add"
            message = "Added Other Properties (DDP)"
            ClusterAdditionalInformation.objects.create(cluster=clusterObj, ddp_hostname=ddp_hostname, cron=cron, port=port).save(force_update=True)
            response = { "success" : "Additional Properties successfully been created for cluster " + str(clusterId)}
        logAction(user, clusterObj, action, message)
    except Exception as e:
        errMsg = "Issue getting Cluster additional properties: "+str(e)
        logger.error(errMsg)
        return errMsg
    return response

def getClusterAdditionalProps(clusterId):
    '''
    This function gets addtional properties from given cluster and return warning message if cluster doesn't have any properties.
    '''
    valuesFields = "ddp_hostname", "cron", "port", "time"
    response = ""
    try:
        if ClusterAdditionalInformation.objects.filter(cluster__id=clusterId).exists():
            clusterAdditionalData = ClusterAdditionalInformation.objects.only(valuesFields).values(*valuesFields).get(cluster__id=clusterId)
            response = clusterAdditionalData
        else:
            response = { "warning" : "No additional information been found for cluster. - " + str(clusterId) }
    except Exception as e:
        errMsg = "Issue getting Cluster additional data: "+str(e)
        logger.error(errMsg)
        return errMsg
    return response

def checkForDuplicateVirtualImageIpInfo(virtualImageIpType, address, ipv4Identifier, ipv6Identifier, virtualImage, cluster_id):
    '''
    This function checks IpAddresses about to be saved to to DB. If they are duplicates then the value will only be saved if both Virtual Machines are members of the same consolidated group
    '''
    if "ipv6" in virtualImageIpType:
        if not IpAddress.objects.filter(ipv6_address=address, ipv6UniqueIdentifier=ipv6Identifier).exists() or not IpAddress.objects.filter(ipv6_address=address+'/64', ipv6UniqueIdentifier=ipv6Identifier).exists():
                return False
    else:
        if not IpAddress.objects.filter(address=address, ipv4UniqueIdentifier=ipv4Identifier).exists():
            return False
    groupList = getConsolidatorsAndConstituents(virtualImage, cluster_id)
    for virtualImage in groupList:
        if "ipv6" in virtualImageIpType:
            if VirtualImageInfoIp.objects.filter(ipMap__ipv6_address=address, ipMap__ipv6UniqueIdentifier=ipv6Identifier, virtual_image=virtualImage).exists() or not VirtualImageInfoIp.objects.filter(ipv6_address=address+'/64', ipv6UniqueIdentifier=ipv6Identifier).exists():
                    break
        else:
            if VirtualImageInfoIp.objects.filter(ipMap__address=address, ipMap__ipv4UniqueIdentifier=ipv4Identifier, virtual_image=virtualImage).exists():
                break
        if virtualImage == groupList[-1]:
            return False
    if len(groupList) < 1:
        return False
    return True

def getConsolidatorsAndConstituents(virtualImage, cluster_id):
    '''
    The getConsolidatorsAndConstituents function compiles a list of all associated constituents and their consolidator. Will only return list if the consolidator is present
    '''
    groupList = []
    vmName = virtualImage.name
    vmName = vmName.split('_',1)[0]
    nodeName = virtualImage.node_list
    if ConsolidatedToConstituentMap.objects.filter(consolidated__contains = vmName).exists():
        fields = ('constituent')
        constituents = ConsolidatedToConstituentMap.objects.filter(consolidated__contains = vmName).only(fields).values(fields)
        groupList.append(virtualImage)

    else:
        fields = ('consolidated')
        if ConsolidatedToConstituentMap.objects.filter(constituent__contains = vmName).exists():
            consolidator = ConsolidatedToConstituentMap.objects.only(fields).values(fields).get(constituent__contains = vmName)
            if not VirtualImage.objects.filter(name__contains = consolidator['consolidated'], node_list=nodeName, cluster_id=cluster_id).exists():
                return groupList
            groupList.append(VirtualImage.objects.filter(name__contains = consolidator['consolidated'], node_list=nodeName, cluster_id=cluster_id))
            fields = ('constituent')
            constituents = ConsolidatedToConstituentMap.objects.filter(consolidated = consolidator['consolidated']).only(fields).values(fields)
        else:
            return groupList

    for constituent in constituents:
        if VirtualImage.objects.filter(name__contains = constituent['constituent'], node_list=nodeName, cluster_id=cluster_id).exists():
            groupList.append(VirtualImage.objects.filter(name__contains = constituent['constituent'], node_list=nodeName, cluster_id=cluster_id))

    return groupList

def getDuplicatesInList(list):
    uniqueList=set(list)
    duplicateList=[]
    for x in list:
        if x in uniqueList:
            uniqueList.remove(x)
        else:
            duplicateList.append(x)
    return duplicateList

def getInstallGroups(installGroup,status=None):
    '''
    The getInstallGroups is an helper function to get Deployment Install groups
    '''
    installList = []
    try:
        installGroupList = InstallGroup.objects.get(installGroup=installGroup)
        clusterInstallGroups = ClusterToInstallGroupMapping.objects.filter(group=installGroupList)
        for clusterInstallGroup in clusterInstallGroups:
            statusDict = {}
            clusterDict = {}
            try:
                if status == None:
                    deploymentStatus = DeploymentStatus.objects.get(cluster=clusterInstallGroup.cluster.id)
                else:
                    try:
                        deploymentStatus = DeploymentStatus.objects.get(cluster=clusterInstallGroup.cluster.id,status__status=status)
                    except:
                        continue
                statusDict["status"] = str(deploymentStatus.status.status)
                statusDict["os"] = str(deploymentStatus.osDetails)
                statusDict["patches"] = str(deploymentStatus.patches)
                statusDict["litp"] = str(deploymentStatus.litpVersion)
                statusDict["mediaArtifact"] = str(deploymentStatus.mediaArtifact)
                statusDict["kgbpackages"] = str(deploymentStatus.packages)
                statusDict["description"] = str(deploymentStatus.description)
                clusterDict[str(clusterInstallGroup.cluster.name)] = statusDict
            except Exception as error:
                errMsg = {"ERROR" : "There was an issue finding deployemt status data defined for cluster : " + str(clusterInstallGroup.cluster.name) + ", Error: " + str(error)}
                logger.error(errMsg)
                return errMsg
            installList.append(clusterDict)
    except Exception as error:
        errMsg = {"ERROR" : "There was an issue finding clusters defined install Group: " + str(installGroup) + ", Error: " + str(error)}
        logger.error(errMsg)
        return errMsg
    return installList

def getHybridCloudValues(clusterObj, ipType):
    '''
    Getting the Hybrid Cloud Values
    '''
    editValues = []
    oldValues = []
    hybridCloudValues = {}

    fields = ('ip_type', 'internal_subnet','gateway_internal__address','gateway_external__address', 'internal_subnet_ipv6','gateway_internal_ipv6__ipv6_address','gateway_external_ipv6__ipv6_address')
    hybridCloudObj = HybridCloud.objects.only(fields).values(*fields).get(cluster=clusterObj)
    hybridCloudValues['ip_type'] = hybridCloudObj['ip_type']
    hybridCloudValues['internal_subnet'] = hybridCloudObj['internal_subnet']
    hybridCloudValues['gateway_internal__address'] = hybridCloudObj['gateway_internal__address']
    hybridCloudValues['gateway_external__address'] = hybridCloudObj['gateway_external__address']
    hybridCloudValues['internal_subnet_ipv6'] = hybridCloudObj['internal_subnet_ipv6']
    hybridCloudValues['gateway_internal_ipv6__ipv6_address'] = hybridCloudObj['gateway_internal_ipv6__ipv6_address']
    hybridCloudValues['gateway_external_ipv6__ipv6_address'] = hybridCloudObj['gateway_external_ipv6__ipv6_address']

    for ip in hybridCloudValues:
        if hybridCloudValues[ip] == None:
            hybridCloudValues[ip] = ""

    editValues = {'internal_subnet': str(hybridCloudValues['internal_subnet']),
                  'gatewayInternal': str(hybridCloudValues['gateway_internal__address']),
                  'gatewayExternal': str(hybridCloudValues['gateway_external__address']),
                  'internal_subnet_ipv6': str(hybridCloudValues['internal_subnet_ipv6']),
                  'gatewayInternalIPv6': str(hybridCloudValues['gateway_internal_ipv6__ipv6_address']),
                  'gatewayExternalIPv6': str(hybridCloudValues['gateway_external_ipv6__ipv6_address'])
                 }

    oldValues = [str(hybridCloudValues['ip_type']) + "##Active IP Version",
                     str(hybridCloudValues['internal_subnet']) + "##Internal Subnet IPv4",
                     str(hybridCloudValues['gateway_internal__address']) + "##Gateway Private IP IPv4",
                     str(hybridCloudValues['gateway_external__address']) + "##Gateway Public IP IPv4",
                     str(hybridCloudValues['internal_subnet_ipv6']) + "##Internal Subnet IPv6",
                     str(hybridCloudValues['gateway_internal_ipv6__ipv6_address']) + "##Gateway Private IP IPv6",
                     str(hybridCloudValues['gateway_external_ipv6__ipv6_address']) + "##Gateway Public IP IPv6"]
    return editValues, oldValues

def addHybridCloudValues(clusterObj, ipType, hybridCloudValues):
    '''
    add Hybrid Cloud
    '''
    try:
        identifier = clusterObj.management_server.server.hardware_type
        if identifier == "cloud":
            publicIdentifier = clusterObj.id
        else:
            publicIdentifier = "1"
        ret, message = checkIPsHybridCloudValues(clusterObj,ipType,hybridCloudValues,publicIdentifier)
        if ret != 0:
            logger.error(message)
            return ("1",message)
        addressList = filter(None,hybridCloudValues.values())
        duplicates = getDuplicatesInList(addressList)
        if len(duplicates) > 0:
            raise Exception("Duplicate IP Info "+str(duplicates))

        ipAddressType = "hybridCloud_" + str(clusterObj.id)
        if ipType == "ipv4":
            gatewayInternal = None if hybridCloudValues['gatewayInternal'] == None or str(hybridCloudValues['gatewayInternal']) == "" else IpAddress.objects.create(address=str(hybridCloudValues['gatewayInternal']), ipType=ipAddressType, ipv4UniqueIdentifier=clusterObj.id)
            gatewayExternal = None if hybridCloudValues['gatewayExternal'] == None or str(hybridCloudValues['gatewayExternal']) == "" else IpAddress.objects.create(address=str(hybridCloudValues['gatewayExternal']), ipType=ipAddressType, ipv4UniqueIdentifier=publicIdentifier)
            HybridCloud.objects.create(cluster=clusterObj, ip_type=ipType, internal_subnet=str(hybridCloudValues['internalSubnet']),
                                      gateway_internal=gatewayInternal, gateway_external=gatewayExternal)
        else:
            gatewayInternalIPv6 = None if hybridCloudValues['gatewayInternalIPv6'] == None or hybridCloudValues['gatewayInternalIPv6'] == "" else IpAddress.objects.create(ipv6_address=str(hybridCloudValues['gatewayInternalIPv6']), ipType=ipAddressType, ipv6UniqueIdentifier=clusterObj.id)
            gatewayExternalIPv6 = None if hybridCloudValues['gatewayExternalIPv6'] == None or hybridCloudValues['gatewayExternalIPv6'] == "" else IpAddress.objects.create(ipv6_address=str(hybridCloudValues['gatewayExternalIPv6']), ipType=ipAddressType, ipv6UniqueIdentifier=publicIdentifier)

            HybridCloud.objects.create(cluster=clusterObj, ip_type=ipType, internal_subnet_ipv6=str(hybridCloudValues['internalSubnetIPv6']),
                                      gateway_internal_ipv6=gatewayInternalIPv6, gateway_external_ipv6=gatewayExternalIPv6)
        return ("0","Success")
    except Exception as error:
        message = "There was an issue saving the Hybrid Cloud information to the Deployment. Exception: " + str(error)
        logger.error(message)
        return ("1",message)

def checkIPsHybridCloudValues(clusterObj,ipType,hybridCloudValues, publicIdentifier):
    '''
    checking IP Hybrid Cloud Values
    '''
    if ipType == "ipv4":
        if IpAddress.objects.filter(address=str(hybridCloudValues['gatewayInternal']), ipv4UniqueIdentifier=clusterObj.id).exists():
            return (1,"Internal IPaddress: " + str(hybridCloudValues['gatewayInternal']) + " already in use in this cluster")
        if IpAddress.objects.filter(address=str(hybridCloudValues['gatewayExternal']), ipv4UniqueIdentifier=publicIdentifier).exists():
            return (1,"Public IPaddress: " + str(hybridCloudValues['gatewayExternal']) + " already in use in this or another cluster")
    else:
        if IpAddress.objects.filter(ipv6_address=str(hybridCloudValues['gatewayInternalIPv6']), ipv6UniqueIdentifier=clusterObj.id).exists():
            return (1,"Internal IPv6  IPaddress: " + str(hybridCloudValues['gatewayExternal']) + " already in use in this cluster")
        if IpAddress.objects.filter(ipv6_address=str(hybridCloudValues['gatewayExternalIPv6']), ipv6UniqueIdentifier=publicIdentifier).exists():
            return (1,"Public IPaddress: " + str(hybridCloudValues['gatewayExternal']) + " already in use in this or another cluster")
    return 0, "All OK"

def editHybridCloudValues(clusterObj, ipType, hybridCloudValues):
    '''
    edit Hybrid Cloud
    '''
    try:
        addressList = filter(None,hybridCloudValues.values())
        duplicates = getDuplicatesInList(addressList)
        if len(duplicates) > 0:
            raise Exception("Duplicate IP Info "+str(duplicates))
        ipAddressType = "hybridCloud_" + str(clusterObj.id)
        hybridCloudObj = HybridCloud.objects.get(cluster=clusterObj)
        hybridCloudObj.ip_type = ipType
        if ipType == "ipv4":
            hybridCloudObj.internal_subnet = str(hybridCloudValues['internalSubnet'])
            hybridCloudObj.save(force_update=True)
            updateHybridCloudAddress(hybridCloudObj,hybridCloudObj.gateway_internal,ipAddressType,hybridCloudValues['gatewayInternal'],"internal",field="gateway_internal")
            updateHybridCloudAddress(hybridCloudObj,hybridCloudObj.gateway_external,ipAddressType,hybridCloudValues['gatewayExternal'],"ipv4",field="gateway_external")
        else:
            hybridCloudObj.internal_subnet_ipv6 = str(hybridCloudValues['internalSubnetIPv6'])
            hybridCloudObj.save(force_update=True)
            updateHybridCloudAddress(hybridCloudObj,hybridCloudObj.gateway_internal_ipv6,ipAddressType,hybridCloudValues['gatewayInternalIPv6'],"internal_ipv6",field="gateway_internal_ipv6")
            updateHybridCloudAddress(hybridCloudObj,hybridCloudObj.gateway_external_ipv6,ipAddressType,hybridCloudValues['gatewayExternalIPv6'],"ipv6",field="gateway_external_ipv6")
        return ("0","Success")
    except Exception as error:
        message = "There was an issue saving the Hybrid Cloud information to the Deployment. Exception: " + str(error)
        logger.error(message)
        return ("1",message)

def updateHybridCloudAddress(hybridCloudObj,queryString,type,update,extraDetail,field=None):

    ipDeleted = False
    identifier = hybridCloudObj.cluster.management_server.server.hardware_type
    if identifier == "cloud" or extraDetail == "internal" or extraDetail == "internal_ipv6":
        identifierValue = str(hybridCloudObj.cluster.id)
    else:
        identifierValue = "1"

    if extraDetail == "ipv4" or extraDetail == "internal":
        if queryString is not None and  update != "":
            if IpAddress.objects.filter(address=str(queryString), ipType=str(type), ipv4UniqueIdentifier=identifierValue).exists():
                result = IpAddress.objects.get(address=str(queryString), ipType=str(type), ipv4UniqueIdentifier=identifierValue)
                result.address = str(update)
                result.save(force_update=True)
                return
        elif queryString is None and update != "":
            if not IpAddress.objects.filter(address=str(update), ipv4UniqueIdentifier=identifierValue).exists():
                result = IpAddress.objects.create(address=update, ipType=str(type), ipv4UniqueIdentifier=identifierValue)
                if field == "gateway_internal":
                    hybridCloudObj.gateway_internal = result
                else:
                    hybridCloudObj.gateway_external = result
                hybridCloudObj.save(force_update=True)
                return
            else:
                raise ValueError("IP Address: " + str(update) + " is already in use in this or another cluster")
        elif queryString is not None and update == "":
             if IpAddress.objects.filter(address=str(queryString), ipType=str(type), ipv4UniqueIdentifier=identifierValue).exists():
                result = IpAddress.objects.get(address=str(queryString), ipType=str(type), ipv4UniqueIdentifier=identifierValue)
                if field == "gateway_internal":
                    hybridCloudObj.gateway_internal = result
                else:
                    hybridCloudObj.gateway_external = result
                hybridCloudObj.save(force_update=True)
                result.delete()

    if queryString is None and update == "":
        return

    if queryString is None and update != "":
        if not IpAddress.objects.filter(ipv6_address=str(update), ipv6UniqueIdentifier=identifierValue).exists():
            result = IpAddress.objects.create(ipv6_address=update, ipType=str(type), ipv6UniqueIdentifier=identifierValue)
            if field == "gateway_internal_ipv6":
                hybridCloudObj.gateway_internal_ipv6 = result
            else:
                hybridCloudObj.gateway_external_ipv6 = result

            hybridCloudObj.save(force_update=True)
            return
        else:
            raise ValueError("IP Address: " + str(update) + " is already in use in this or another cluster")

    try:
        if IpAddress.objects.filter(ipv6_address=str(queryString), address=None, ipType=str(type), ipv6UniqueIdentifier=identifierValue).exists():
            result = IpAddress.objects.get(ipv6_address=str(queryString), address=None, ipType=str(type), ipv6UniqueIdentifier=identifierValue)
            if update == "":
                if field == "gateway_internal_ipv6":
                    hybridCloudObj.gateway_internal_ipv6 = None
                else:
                    hybridCloudObj.gateway_external_ipv6 = None
                hybridCloudObj.save(force_update=True)
                result.delete()
                ipDeleted = True
            if ipDeleted == False:
                result.ipv6_address = str(update)
                result.save(force_update=True)
        return
    except IpAddress.DoesNotExist:
        return
    return

def getDeploymentUtilitiesWithProductSet(productSet, productSetVersion=None, mediaArtifactName=None):
    '''
    Getting Deployment Utilities With Product Set
    '''
    deploymentUtilitiesDict = {}
    mediaArtifact = None
    if productSetVersion is None:
        allVersions = ProductSetVersion.objects.filter(productSetRelease__productSet__name=productSet,drop__correctionalDrop=False).exclude(drop__release__name__icontains="test").order_by('-id')
        for item in allVersions:
            if item.getOverallWeigthedStatus() == 'passed' or item.status.state == 'passed_manual':
                if item.status.state != 'caution':
                    productSetVersion = item
                    break
    try:
        contentFields = ('mediaArtifactVersion__id', 'mediaArtifactVersion__mediaArtifact__name', 'mediaArtifactVersion__version')
        if mediaArtifactName is None:
            if productSet == "ENM":
                productSetVersionContent = ProductSetVersionContent.objects.only(contentFields).values(*contentFields).get(productSetVersion=productSetVersion, mediaArtifactVersion__drop__release__product__name=productSet)
            else:
                productSetVersionContent = ProductSetVersionContent.objects.only(contentFields).values(*contentFields).get(productSetVersion=productSetVersion, mediaArtifactVersion__drop__release__product__name=productSetVersion.productSetRelease.release.product.name)
        else:
            productSetVersionContent = ProductSetVersionContent.objects.only(contentFields).values(*contentFields).get(productSetVersion=productSetVersion, mediaArtifactVersion__mediaArtifact__name=mediaArtifactName)
        deploymentUtilitiesDict['mediaArtifact'] = productSetVersionContent['mediaArtifactVersion__mediaArtifact__name']
        deploymentUtilitiesDict['mediaArtifactVersion'] = productSetVersionContent['mediaArtifactVersion__version']
    except Exception as error:
        errMsg = "ERROR: Issues getting Product Set Version Content using Version: " + str(productSetVersion) + ", " + str(error)
        logger.error(errMsg)
        return errMsg

    try:
        fields = ('utility_version__utility_version', 'utility_version__utility_name__utility')
        if DeploymentUtilsToProductSetVersion.objects.only(fields).values(*fields).filter(productSetVersion=productSetVersion).exists():
            deploymentUtilities = DeploymentUtilsToProductSetVersion.objects.only(fields).values(*fields).filter(productSetVersion=productSetVersion, active=True)
        else:
            deploymentUtilities = DeploymentUtilsToISOBuild.objects.only(fields).values(*fields).filter(iso_build__id=productSetVersionContent['mediaArtifactVersion__id'], active=True)
        for deploymentUtility in deploymentUtilities:
            deploymentUtilitiesDict[deploymentUtility['utility_version__utility_name__utility']] = deploymentUtility['utility_version__utility_version']
    except Exception as error:
        errMsg = "ERROR: Issues getting Deployment Utilities for Product Set Version " + str(productSetVersion) +", " + str(error)
        logger.error(errMsg)
        return errMsg
    return deploymentUtilitiesDict

def getDeploymentTemplatesWithProductSet(productSet, productSetVersion=None):
    '''
    Gets latest passed deployment templates otherwise get version given in Product Set Version
    '''
    deploymentTemplatesPackage = config.get("DMT_AUTODEPLOY", "deploymentTemplatePackage")
    deploymentTemplatesInfoDict = {}
    if productSetVersion is None:
        allVersions = ProductSetVersion.objects.filter(productSetRelease__productSet__name=productSet,drop__correctionalDrop=False).exclude(drop__release__name__icontains="test").order_by('-id')
        for item in allVersions:
            if item.getOverallWeigthedStatus() == 'passed' or item.status.state == 'passed_manual':
                if item.status.state != 'caution':
                    productSetVersion = item
                    break
    try:
        fields = ('mediaArtifactVersion__id','mediaArtifactVersion__mediaArtifact__name', 'mediaArtifactVersion__version')
        productSetVersionContent = ProductSetVersionContent.objects.only(fields).values(*fields).get(productSetVersion=productSetVersion, mediaArtifactVersion__drop__release__product__name="ENM")
        deploymentTemplatesInfoDict['mediaArtifact'] = productSetVersionContent['mediaArtifactVersion__mediaArtifact__name']
        deploymentTemplatesInfoDict['mediaArtifactVersion'] = productSetVersionContent['mediaArtifactVersion__version']
    except Exception as error:
        errMsg = "ERROR: Issues getting Product Set Version Content using Version-" + str(productSetVersion) + ", " + str(error)
        logger.error(errMsg)
        return errMsg

    try:
        deploymentTemplates = ISObuildMapping.objects.only('package_revision__version').values('package_revision__version').get(iso__id=productSetVersionContent['mediaArtifactVersion__id'], package_revision__package__name=deploymentTemplatesPackage)
        deploymentTemplatesInfoDict['deploymentTemplatesName'] = deploymentTemplatesPackage
        deploymentTemplatesInfoDict['deploymentTemplatesVersion'] = deploymentTemplates['package_revision__version']
    except Exception as error:
        errMsg = "ERROR: Issues getting Deployment Templates Version using MediaArtifact-" + str(productSetVersionContent['mediaArtifactVersion__mediaArtifact__name']) + " Version-"+str(productSetVersionContent['mediaArtifactVersion__version']) +", " + str(error)
        logger.error(errMsg)
        return errMsg
    return deploymentTemplatesInfoDict

def updateDeploymentDescriptionAndMappings(version, ddType, fileName, folderName):
    '''
    Update Deployment Description List and update Deployment Mappings
    '''
    message = None
    try:
        autoDeploy = fileName+"_dd.xml"
        sedDeploy = fileName+"_info.txt"
        if folderName == "test" or "test" in fileName or "cloud" in fileName:
            capacityType = "test"
        else:
            capacityType = "production"

        deploymentDescription, created = DeploymentDescription.objects.get_or_create(version=version, dd_type=ddType, name=fileName, capacity_type=capacityType, auto_deployment=autoDeploy, sed_deployment=sedDeploy)
        allDeploymentMappings = DDtoDeploymentMapping.objects.filter(deployment_description__dd_type=ddType, deployment_description__name=fileName, auto_update=True)
        if allDeploymentMappings:
            for deploymentMapping in allDeploymentMappings:
                deploymentMapping.deployment_description = deploymentDescription
                deploymentMapping.save()
        return (0,message)
    except Exception as error:
        message = "There was an issue saving the information to the Deployment Description and Mappings. Exception: " + str(error)
        logger.error(message)
        return (1,message)

def getFileNamesAndUpdateDDdata(tmpArea, ddType, version):
    '''
    Getting File names for DD
    '''
    filesList = []
    message = None
    try:
        for root, folders, files in os.walk(tmpArea):
            folderName = root.split('/')[-1]
            for fileName in files:
                dictOfFiles = {}
                if "_dd.xml" in str(fileName) or "_info.txt" in str(fileName):
                    name,endType = str(fileName).rsplit('_',1)
                    if not name in filesList:
                        dictOfFiles[folderName] = name
                        filesList.append(dictOfFiles)
    except Exception as e:
        message = "ERROR: Unable to get files for deployment description with Type - " + str(ddType) +". Exception: " + str(e)
        return (1,message)
    if filesList:
        for name in filesList:
            for folderName, fileName in name.items():
                (ret,message) = updateDeploymentDescriptionAndMappings(version, ddType, fileName, folderName)
                if ret != 0:
                    return (ret,message)
    return (0,message)

def updateDeploymentDescriptionsData(depDescVersion, setLatest=None):
    '''
    Updating DB with give version's Deployment Descriptions
    '''
    if str(setLatest).lower() == "false":
        setLatest = False
    else:
        setLatest = True
    depDescPackage = config.get("DMT_AUTODEPLOY", "deploymentTemplatePackage")
    mainTmpArea = config.get("DMT_AUTODEPLOY", "tmpDDcontentArea")
    ddTypesList = DeploymentDescriptionType.objects.all()
    # Download the deployment Description Package
    packageObject = dmt.cloud.getPackageObject(depDescPackage,depDescVersion,"None","no")
    if packageObject == None:
        message = "ERROR: Unable to Download the version of the deployment description package specified"
        return message

    latestVersion = None
    if DeploymentDescriptionVersion.objects.filter(latest=True).exists():
        latestVersion = DeploymentDescriptionVersion.objects.get(latest=True)

    version, created = DeploymentDescriptionVersion.objects.get_or_create(version=depDescVersion)
    if latestVersion:
        if not str(latestVersion.version) == str(depDescVersion):
            if setLatest:
                latestVersion.latest = False
                latestVersion.save()
                version.latest = True
            else:
                version.latest = False
    else:
        version.latest = True
    version.save()
    for ddType in ddTypesList:
        tmpArea = mainTmpArea + ddType.dd_type
        if not os.path.exists(tmpArea):
            os.makedirs(tmpArea)
        if ddType.dd_type == "rpm":
            artifactName = dmt.cloud.downloadArtifact(tmpArea,"None",packageObject,"ENM")
            if artifactName == 1:
                message = "ERROR: Unable to download the package " + str(depDescPackage)
                shutil.rmtree(mainTmpArea)
                return message
            #Extract the package to list the DD files
            (ret,message) = dmt.utils.extractRpmFile(artifactName,tmpArea)
            if ret != 0:
                shutil.rmtree(mainTmpArea)
                return message
            tmpArea = tmpArea+"/ericsson"
        else:
            try:
                artifact = packageObject.artifactId
                group = packageObject.groupId
                secondGroup = config.get('DMT_AUTODEPLOY', 'secondSliceGroupId')
                secondArtifact = config.get('DMT_AUTODEPLOY', 'secondSliceArtifactId')
            except Exception as e:
                message = "ERROR: Unable to get the slice infomation for the deployment template version inputted. Exception: " + str(e)
                shutil.rmtree(mainTmpArea)
                return message
            try:
                if ddType.dd_type == "critical-slice":
                    (ret,sliceDir) = dmt.utils.downloadSliceFile(depDescVersion,tmpArea,secondArtifact,secondGroup)
                else:
                    (ret,sliceDir) = dmt.utils.downloadSliceFile(depDescVersion,tmpArea,artifact,group)
                if ret != 0:
                    shutil.rmtree(mainTmpArea)
                    return sliceDir
                (ret,message) = dmt.utils.unzipFile(sliceDir,tmpArea)
                if ret != 0:
                    shutil.rmtree(mainTmpArea)
                    return message
            except Exception as e:
                message = "ERROR: Unable to get the snapshot file for artifact "
                if ddType.dd_type == "critical-slice":
                    message = message  + str(secondArtifact) + " with version " + str(depDescVersion) + " for critical-slice"
                else:
                    message = message + str(artifact) + " with version " + str(depDescVersion) + " for team-slice"
                message = message + " deployment description. Please ensure the snapshot exist in Nexus. Exception: " + str(e)
                shutil.rmtree(mainTmpArea)
                return message
            if ddType.dd_type == "critical-slice":
                if os.path.exists(tmpArea + "/critical-slices"):
                    tmpArea = tmpArea + "/critical-slices"
                else:
                    tmpArea = tmpArea + "/slices"
            elif ddType.dd_type == "team-slice":
                if os.path.exists(tmpArea + "/team-slice"):
                    tmpArea = tmpArea + "/team-slice"
                else:
                    tmpArea = tmpArea + "/slices"
        (ret,message) = getFileNamesAndUpdateDDdata(tmpArea, ddType, version)
        if ret != 0:
            shutil.rmtree(mainTmpArea)
            return message
        tmpArea = ""
        shutil.rmtree(mainTmpArea)
    message = "SUCCESS"
    return message

def getDeploymentDescriptionData(version, ddType, capacityType=None):
    '''
    Getting the DD for a given version and type
    '''
    ddData = {}
    ddData['deploymentDescription'] = []
    try:
        if capacityType:
            ddData['deploymentDescription'] = DeploymentDescription.objects.only('name').values('name').filter(version__version=version, dd_type__dd_type=ddType, capacity_type=capacityType)
        else:
            ddData['deploymentDescription'] =  DeploymentDescription.objects.only('name').values('name').filter(version__version=version, dd_type__dd_type=ddType)
    except Exception as e:
        errMsg = "Unable to get Deployment Descriptions using Version:" + str(version) + " and Type: " + str(ddType) + ". Exception: " + str(e)
        message = { "error": str(errMsg)}
        return message
    if not ddData['deploymentDescription']:
        errMsg ='No deployment description data in the DB for the given values'
        message = { "error": str(errMsg)}
        return message
    return ddData

def updateClustersServicesWithDD(clusterId=None):
    '''
    Perform a complete or partial update of services based on DD for all Clusters with Auto Update selected
    '''
    import dmt.clusterServicesUpdate
    depDescPackage = config.get("DMT_AUTODEPLOY", "deploymentTemplatePackage")
    depDescVersion = None
    try:
        if clusterId:
            message = "ERROR: Could not find a Deployment Description: " + str(clusterId) + ", Exception :  "
            dDMapping = DDtoDeploymentMapping.objects.get(cluster = clusterId)
            depDescVersionObj = dDMapping.deployment_description.version
        else:
            message = "ERROR: Could not get the latest Deployment Description: " + str(clusterId) + ", Exception :  "
            depDescVersionObj = DeploymentDescriptionVersion.objects.get(latest=True)
        depDescVersion = depDescVersionObj.version
    except Exception as e:
        message = message + str(e)
        logger.error(message)

    # Download the DD rpm
    (ret,message,tmpArea) = dmt.clusterServicesUpdate.getDeploymentDescriptionFile(depDescVersion,depDescPackage)
    if ret != 0:
        return "FAILED"

    if clusterId:
        message = autoUpdateClusterServicesWithDD(clusterId, depDescPackage, depDescVersion, tmpArea)
    else:
        summaryLog = UpdatedDeploymentSummaryLog.objects.create(dd_version=depDescVersionObj)
        try:
            ddToDeploymentMappingList = DDtoDeploymentMapping.objects.filter(auto_update=True)
            for ddToDeploymentMapping in ddToDeploymentMappingList:
                clusterId = ddToDeploymentMapping.cluster.id
                autoUpdateClusterServicesWithDD(clusterId, depDescPackage, depDescVersion, tmpArea, summaryLog)
            message = "SUCCESS"
        except Exception as e:
            message = "FAILED"
            dmt.infoforConfig.removeTmpArea(tmpArea)
        sendReportMail(summaryLog.id)
    dmt.infoforConfig.removeTmpArea(tmpArea)
    return message

def autoUpdateClusterServicesWithDD(clusterId, depDescPackage, depDescVersion, tmpArea, summaryLog=None):
    '''
    Perform a complete or partial update of services based on DD for a Cluster
    '''
    logger.info("INFO: Begining update of cluster " + str(clusterId))
    import dmt.clusterServicesUpdate

    deploymentLog = ""
    status = None
    message = ""
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
        hardwareType = clusterObj.management_server.server.hardware_type
        deploymentLog = "INFO: Started Update on Deployment: " + str(clusterObj.name) + ", ID: "+ str(clusterId) + ". <br /> "
    except Exception as e:
        message = "ERROR: Could not get cluster: " + str(clusterId) + ", Exception :  " + str(e)
        logger.error(message)
        return message
    deploymentLogObj = UpdatedDeploymentLog.objects.create(cluster=clusterObj)
    if summaryLog:
        deploymentLogObj.summary_log=summaryLog
    updateDeploymentLog(deploymentLogObj, deploymentLog)
    try:
        # back up sed for rollback
        sedVersion = getVirtualMasterSedVersion()
        try:
            sed = dmt.buildconfig.generateDBConfigFile(clusterId, sedVersion)
            deploymentLog += "INFO: Generated Database Config File Successfully. <br />"
            updateDeploymentLog(deploymentLogObj, deploymentLog)
        except Exception as e:
            message = "ERROR: Unable to generate SED, Exception: " + str(e)
            logger.error(message)
            deploymentLog += message + " <br> Failed to Update Deployment"
            updateDeploymentLog(deploymentLogObj, deploymentLog, "failed")
            return message

        fileName=str(clusterObj.name)+"-config.cfg"
        try:
            ret = dmt.buildconfig.writeDBConfigToFile(sed, fileName, tmpArea)
            deploymentLog += "INFO: Writing Database Config To File Successfully. <br />"
        except Exception as e:
            message = "ERROR: Unable to write SED to file, Exception: " + str(e)
            logger.error(message)
            deploymentLog += message + " <br /> Failed to Update Deployment."
            updateDeploymentLog(deploymentLogObj, deploymentLog, "failed")
            return message

        try:
            ret, sedUrlFilePath = dmt.buildconfig.saveSedFile(sed, fileName)
            deploymentLog += "INFO: Writing Database Config To Central Area Successfully. <br />"
            deploymentLog += "INFO: Link to Current Sed File:"' <a href="' + str(sedUrlFilePath) +' ">Sed File </a>'
            updateDeploymentLog(deploymentLogObj, deploymentLog)
        except Exception as e:
            message = "ERROR: Unable to write SED file to temporary Central Area , Exception: " + str(e)
            logger.error(message)
            deploymentLog += message + " <br /> Failed to Update Deployment."
            updateDeploymentLog(deploymentLogObj, deploymentLog, "failed")
            return message

        try:
            ddToDeploymentMappingObj = DDtoDeploymentMapping.objects.get(cluster__id=clusterId)
            depDescType = ddToDeploymentMappingObj.deployment_description.dd_type.dd_type
            depDescFileName = ddToDeploymentMappingObj.deployment_description.name
            updateType = ddToDeploymentMappingObj.update_type
            ipRangeType = ddToDeploymentMappingObj.iprange_type
            deploymentLogObj.deployment_description = ddToDeploymentMappingObj.deployment_description
            deploymentLog += "<br /> INFO: This is a " + str(updateType) + " update. Deployment Description Used: "+ str(depDescFileName) +", Type: " + str(depDescType) + ", IpRange Type: "+str(ipRangeType)  +" <br />"
            updateDeploymentLog(deploymentLogObj, deploymentLog)
        except Exception as e:
            message = "ERROR: Could not the latest Deployment Description: " + str(clusterId) + ", Exception :  " + str(e)
            logger.error(message)
            deploymentLog += str(message) + " <br /> Failed to Update."
            updateDeploymentLog(deploymentLogObj, deploymentLog, "failed")
            return message

        # Parse the required information from the DD
        ret,message,ddServicesXmlList,ddServicesInfoList = dmt.clusterServicesUpdate.parseDeploymentDescriptionFile(depDescVersion,depDescType,depDescFileName,depDescPackage,tmpArea)
        if ret != 0:
            logger.error(message)
            deploymentLog += str(message) + " <br /> Failed to Update Deployment."
            updateDeploymentLog(deploymentLogObj, deploymentLog, "failed")
            return message
        else:
            deploymentLog += "INFO: Parsed Deployment Description File Successfully. <br />"
            updateDeploymentLog(deploymentLogObj, deploymentLog)

        # Delete Virtual Images in cluster with complete update selected
        if updateType != "partial":
            resultDeleteVirtualImage = dmt.clusterServicesUpdate.deleteExistingVirtualImages(clusterId)
            deploymentLog += "INFO: Deleted Services. <br />"
            updateDeploymentLog(deploymentLogObj, deploymentLog)
        # Add Virtual Images based on DD information
        ret,listOfServicesAdded, listOfIpTypeAdded, logData = dmt.clusterServicesUpdate.addVirtualImages(clusterId, ddServicesXmlList, ddServicesInfoList)
        if ret == 2:
            logDataInfo = "<br /> ".join(logData)
            message = "ERROR: Issue Adding Services, Rollback Deployment. <br /> Info: " + str(logDataInfo) +". <br />"
            status = "failed"
            listOfServicesAdded = []
            filePath = tmpArea+"/"+fileName
            ret, logData = dmt.clusterServicesUpdate.rollbackClusterUsingSED(clusterId, filePath, tmpArea)
            if ret == 1:
                message += logData + "<br />"
                message += "ERROR: Failed Rollback Deployment " + str(clusterId) + ". <br />"
            else:
                message += logData + "<br />"
                message += "INFO: Deployment " + str(clusterId) + " Rollback Successfully. <br />"
        elif ret == 1:
            logDataInfo = "<br /> ".join(logData)
            message = logDataInfo + "<br />"
            status = "failed"
        else:
            if listOfServicesAdded or listOfIpTypeAdded:
                servicesAdded = "<br /> ".join(logData)
                # Add IP and Credential information to added Virtual Images
                if listOfServicesAdded:
                    message += "INFO: Added Services Successfully. Services Information: <br /> " + str(servicesAdded) + " <br />"
                elif listOfIpTypeAdded:
                    message += "INFO: Services IP Type infomation: <br /> " + str(servicesAdded) + " <br />"
            else:
                message = "INFO: No Services Added <br />"
        deploymentLog += message
        updateDeploymentLog(deploymentLogObj, deploymentLog, status)
        if listOfServicesAdded or listOfIpTypeAdded:
            result, logData = dmt.clusterServicesUpdate.addVirtualImageIpInfo(clusterId, hardwareType, ddServicesXmlList, listOfServicesAdded, listOfIpTypeAdded)
            if result == 1:
               message = "ERROR: Issue Adding IP Info for the Services. <br />"
            else:
                if logData:
                    servicesIPinfoAdded = "<br /> ".join(logData)
                    message = "INFO: Added IP Info for the Services Successfully. IP Addresses Information: <br /> " + str(servicesIPinfoAdded) + " <br />"
                else:
                    message = "INFO: Added IP Info for the Services Successfully. <br />"
            deploymentLog += message
            updateDeploymentLog(deploymentLogObj, deploymentLog)
            result, message, logData = dmt.clusterServicesUpdate.mapCredentialsToVirtualImages(listOfServicesAdded, clusterId)
            if result == 1:
                if logData:
                    servicesCredentials = "<br /> ".join(logData)
                    message = "ERROR: Issue mapping Credentials to the Services. Credentials Information: <br /> " + str(servicesCredentials) + " <br />"
                else:
                    message = "ERROR: Issue mapping Credentials to the Services. <br />"
            else:
                if logData:
                    servicesCredentialsAdded = "<br /> ".join(logData)
                    message = "INFO: Mapping Credentials to the Services Successfully. Credentials Information: <br /> " + str(servicesCredentialsAdded) + " <br />"
                else:
                    message = "INFO: Mapping Credentials to the Services Successfully. <br />"
            deploymentLog += message
            updateDeploymentLog(deploymentLogObj, deploymentLog)
        deploymentLog += "INFO: Finished Updating the Deployment."
    except Exception as e:
        message = "ERROR: Unable to update Deployment " + str(clusterId) + " with services from DD, Exception: " + str(e)
        logger.error(message)
        deploymentLog += str(message) + " <br /> Failed to Update Deployment."
        updateDeploymentLog(deploymentLogObj, deploymentLog, "failed")
        return message
    if not status:
       status = "successful"
    updateDeploymentLog(deploymentLogObj, deploymentLog, status)
    return "SUCCESS"

def getVirtualImageDetails(clusterId, serviceName):
    '''
    Getting ip type of existing service
    '''
    existIpType = []
    if VirtualImageInfoIp.objects.filter(virtual_image__name=serviceName, virtual_image__cluster_id=clusterId).exists():
        vmInfoIpObjs = VirtualImageInfoIp.objects.filter(virtual_image__name=serviceName, virtual_image__cluster_id=clusterId)
        for vmInfoIpObj in vmInfoIpObjs:
            ipType = vmInfoIpObj.ipMap.ipType
            type = ipType.split('_')[1]
            checkService = ""
            if "public" in type:
                checkService = serviceName + '_ipaddress'
            elif "ipv6Public" in type:
                checkService = serviceName + '_ipv6address'
            elif "ipv6Internal" in type:
                checkService = serviceName + '_ipv6_internal'
            elif "internal" in type:
                if '_' in serviceName or serviceName == 'esmon':
                    checkService = serviceName + '_ip_internal'
                else:
                    checkService = serviceName + '_internal'
            elif "storage" in type:
                if '_' in serviceName or serviceName == 'esmon':
                    checkService = serviceName + '_ip_storage'
                else:
                    checkService = serviceName + '_storage'
            elif "jgroup" in type:
                if '_' in serviceName or serviceName == 'esmon':
                    checkService = serviceName + '_ip_jgroups'
                else:
                    checkService = serviceName + '_jgroups'
            logger.info('Checking: ' + str(checkService))
            existIpType.append(checkService)
    return existIpType

def getServiceIpTypeInDDXml(serviceName, ddServicesXmlList):
    '''
    Getting all required service ip types from dd
    '''
    serviceIpTypeInDDXml = []

    for serviceIpType in ddServicesXmlList:
        ddservice = parseServiceInfo(serviceIpType)
        if ddservice == serviceName:
            serviceIpTypeInDDXml.append(serviceIpType)
    return serviceIpTypeInDDXml

def updateDeploymentLog(deploymentLogObj, log, status=None):
    '''
    Updating log for Report
    '''
    try:
        if status:
           deploymentLogObj.status = status
        deploymentLogObj.log = log
        deploymentLogObj.save()
    except Exception as e:
        logger.error("ERROR: Issue Saving Log Data - " + str(e))


def checkAddressIsUnique(virtualImageIpType, address, ipIdentifier):
    '''
    Function to check if an IPAddress is unique for a cluster
    '''
    if virtualImageIpType == "public" or virtualImageIpType == "storage":
        return IpAddress.objects.filter(address=address,ipv4UniqueIdentifier=ipIdentifier).exists()
    elif virtualImageIpType == "ipv6Public":
        return IpAddress.objects.filter(ipv6_address=address,ipv6UniqueIdentifier=ipIdentifier).exists()
    elif virtualImageIpType == "ipv6Internal":
        return IpAddress.objects.filter(ipv6_address=address,ipv6UniqueIdentifier=ipIdentifier).exists()
    elif virtualImageIpType == "internal" or virtualImageIpType == "jgroup":
        return IpAddress.objects.filter(address=address,ipv4UniqueIdentifier=ipIdentifier).exists()

def getPublicAddress(VmServiceIpRangeList, virtualImageIpType, ipIdentifier, allDeploymentIps, virtualImageName, duplicatePublicIps=None):
    '''
    Function to get Public ip address based on a IP range list
    '''
    for VmServiceIpRange in VmServiceIpRangeList:
        if virtualImageIpType == "public" or virtualImageIpType == "storage":
            startIp = VmServiceIpRange.ipv4AddressStart
            endIp = VmServiceIpRange.ipv4AddressEnd
        else:
            startIp = VmServiceIpRange.ipv6AddressStart
            endIp = VmServiceIpRange.ipv6AddressEnd
        logger.info(VmServiceIpRangeList)
        logger.info((virtualImageName, virtualImageIpType))
        logger.info((startIp, endIp))
        if duplicatePublicIps is not None:
            ret, ipAddress = getNextAvailableIPInRange(allDeploymentIps,startIp,endIp,duplicatePublicIps)
        else:
            ret, ipAddress = getNextAvailableIPInRange(allDeploymentIps,startIp,endIp)
        if ret != 0:
            continue
        else:
            if dmt.utils.checkAddressIsUnique(virtualImageIpType, ipAddress, ipIdentifier):
                logger.error("ERROR: Duplicate IP address for " + str(virtualImageIpType) + " info for virtual image : " + str(virtualImageName))
                continue
            return (0, ipAddress)

    return (1,ipAddress)

def deleteClusterItems(itemName, exceptionList, clusterId):
    if itemName not in exceptionList:
        returnedValue,message = dmt.utils.deleteVirtualImage(clusterId, itemName)
        if returnedValue == "1":
            logger.error("ERROR: " + str(message))
        else:
            logger.info("SUCCESS: Deleted : " + str(itemName))

def sendReportMail(reportId):
    '''
    Sends an e-mail to Depolyment User once new Report has been created
    '''
    fields = 'cluster__name', 'cluster__id', 'status', "deployment_description__name"
    deploymentLogList = UpdatedDeploymentLog.objects.only(fields).values(*fields).filter(summary_log__id=reportId)
    mailHeader = "Summary Report " + str(reportId) + " has been created."
    mainUrl = config.get("DMT_AUTODEPLOY", "cifwk_portal_url")
    mailContent = "<p>Hi Deployment User, <br><br>"
    if deploymentLogList:
        mailContent += "Following Deployment(s) are part of the Report:<br>"
        mailContent += "<ul>"
        for deploymentMap in deploymentLogList:
            mailContent += "<li>"
            if deploymentMap['status'] == "successful":
                mailContent += "<span style='color: green'>"
            else:
                mailContent += "<span style='color: red'>"
            mailContent += str(deploymentMap['cluster__name']) + " - ID: " + str(deploymentMap['cluster__id']) + ". DD: " + str(deploymentMap['deployment_description__name']) + " - Update Status: " + deploymentMap['status'] +"</span></li>"
        mailContent += "</ul><br>"
    else:
        mailContent = "There was issue updating the Deployment(s) or No Deployment(s) updated.<br>"
    mailContent += "Here is the link to " '<a href="'+str(mainUrl)+'/dmt/deploymentsUpdatedReport/'+str(reportId)+'/">Summary Report</a> for the Deployments that were Updated.'
    mailContent += "<br><br>Kind Regards, <br>CI Portal Admin</p>"
    emailRecipients = None
    try:
        emailRecipients = ast.literal_eval(config.get("DMT", "deploymentDistributionList"))
    except Exception as e:
        emailRecipients = None
        logger.error("Email Recipient deploymentDistributionList available" + str(e))
    toEmail = []
    if emailRecipients != None:
        for delEmail in emailRecipients:
            toEmail.append(delEmail)
    fromEmail = config.get("CIFWK", "cifwkDistributionList")
    msg = EmailMultiAlternatives(mailHeader, mailContent, fromEmail, toEmail)
    msg.content_subtype = "html"
    msg.send()

def setDeploymentServersStatus(userId, clusterId, status, serverHostnameList):
    '''
    Updates Cluster Servers ACTIVE/PASSIVE status for a list of server hostnames
    '''
    action = "edit"
    changedHostnames = ""

    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        return "ERROR: Could not find cluster: " + str(clusterId) + ", Exception :  " + str(e)

    serverHostnames = serverHostnameList.split(",")
    try:
        with transaction.atomic():
            for serverHostname in serverHostnames:
                if ClusterServer.objects.filter(server__hostname=serverHostname, cluster__id=clusterId).exists():
                    clusterServerObj = ClusterServer.objects.get(server__hostname=serverHostname, cluster__id=clusterId)
                    changedHostnames += serverHostname + " "
                    if status.lower() == "active":
                        clusterServerObj.active = True
                    elif status.lower() == "passive":
                        clusterServerObj.active = False
                    clusterServerObj.save()

    except IntegrityError as error:
        return "ERROR: Dealing with transactions to database: " + str(error) + "\n"
    if changedHostnames:
        message = "Edited Deployment Server(s) Status, Servers " + changedHostnames + " set to \"" + status.upper() + "\""
        logAction(userId, clusterObj, action, message)
        return "SUCCESS: Clusters Server(s) status changed\n"
    else:
        return "WARNING: No Cluster Server(s) status were changed\n"

def parseServiceInfo(serviceInfo):
    '''
    Function to parse the service from the serviceInfo fetched from the DD xml
    '''
    if "_ipaddress" in serviceInfo:
        return re.sub('_ipaddress', '', serviceInfo)
    elif "_ipv6address" in serviceInfo:
        return re.sub('_ipv6address', '', serviceInfo)
    elif "_ipv6_internal" in serviceInfo:
        return re.sub('_ipv6_internal', '', serviceInfo)
    elif "_ip_jgroups" in serviceInfo:
        return re.sub('_ip_jgroups', '', serviceInfo)
    elif "_ip_storage" in serviceInfo:
        return re.sub('_ip_storage', '', serviceInfo)
    elif "_ip_internal" in serviceInfo:
        return re.sub('_ip_internal', '', serviceInfo)
    elif "_internal" in serviceInfo:
        return re.sub('_internal', '', serviceInfo)
    elif "_storage" in serviceInfo:
        return re.sub('_storage', '', serviceInfo)
    elif "_jgroups" in serviceInfo:
        return re.sub('_jgroups', '', serviceInfo)
    else:
        return ""

def updateClusterIPRanges(user, clusterId=None):
    '''
    Function to update cluster(s) IP Ranges based on DNS dump
    '''
    try:
        if clusterId:
            if Cluster.objects.filter(id=clusterId).exists():
                message = updateClusterDnsIPRanges(user, clusterId)
            else:
                return "ERROR: Not a valid Cluster Id"
        else:
            clusterIdList = Cluster.objects.filter(layout__name="KVM").only("id").values_list("id", flat = True)
            for clusterId in clusterIdList:
                message = updateClusterDnsIPRanges(user, clusterId)
    except Exception as e:
        message = "ERROR: Issue updating cluster IP ranges from DNS, Exception: " + str(e)
        logger.error(message)
        return message
    return message

def updateClusterDnsIPRanges(user, clusterId):
    '''
    Function to parse DNS dump and update a clusters IPv4, IPv6 and Storage Ranges if the information is present
    '''
    dnsIpHostsDumpFile = config.get('DMT','dns_ip_hosts_file')
    ipMatch = "ieatenm5" + str(clusterId)
    ipv4Search = '^('+ipMatch+')\-[0-9]+\s'
    storageSearch = '^('+ipMatch+')\-str[0-9]+\s'
    ipv6Search = '^('+ipMatch+')\-[0-9]+\s|^('+ipMatch+')\-v6\-[0-9]+\s'
    ipv4RangeList = []
    storageRangeList = []
    ipv6RangeList = []
    logContent = ""
    logMessage = ""

    try:
        ipv4RangeList = parseServiceDnsIpRangeFromFile(dnsIpHostsDumpFile, ipv4Search, ipAddrType="IPv4")
        storageRangeList = parseServiceDnsIpRangeFromFile(dnsIpHostsDumpFile, storageSearch, ipAddrType="IPv4")
        ipv6RangeList = parseServiceDnsIpRangeFromFile(dnsIpHostsDumpFile, ipv6Search, ipAddrType="IPv6")

        if ipv4RangeList:
            ipType = "IPv4 Public"
            message = removeExistingAutoIPRanges(ipType, clusterId)
            if message == "Success":
                for ipv4Range in ipv4RangeList:
                    message = addAutoServiceDnsIpRange(clusterId, ipv4Range, ipType)
                    if "Success" in message:
                        logContent += " " + message.replace("Success ", "")
        if storageRangeList:
            ipType = "IPv4 Storage"
            message = removeExistingAutoIPRanges(ipType, clusterId)
            if message == "Success":
                for storageRange in storageRangeList:
                    message = addAutoServiceDnsIpRange(clusterId, storageRange, ipType)
                    if "Success" in message:
                        logContent += " " + message.replace("Success ", "")
        if ipv6RangeList:
            ipType = "IPv6 Public"
            message = removeExistingAutoIPRanges(ipType, clusterId)
            if message == "Success":
                for ipv6Range in ipv6RangeList:
                    message = addAutoServiceDnsIpRange(clusterId, ipv6Range, ipType)
                    if "Success" in message:
                        logContent += " " + message.replace("Success ", "")
        if logContent:
            logMessage = "Auto Generated DNS IP Ranges Updated: " + logContent
            clusterObj = Cluster.objects.get(id=clusterId)
            logAction(user, clusterObj, "edit", logMessage)

    except Exception as e:
        message = "ERROR: Issue updating cluster " + str(clusterId) + " IP Ranges from DNS, Exception: " + str(e)
        logger.error(message)
        return message
    return "Success"

def parseServiceDnsIpRangeFromFile(dumpFile, ipSearch, ipAddrType):
    '''
    Parses the DNS Dump File for a Cluster to build a list of IP Ranges
    '''
    addressList = []
    rangeList = []
    typeSearch = '^((?!aaaa).)*$'
    try:
        with io.open(dumpFile, mode="r", encoding="utf-8") as dnsDump:
            for line in dnsDump:
                if ((re.search(r''+ipSearch+'', line.lower())) and (re.search(r'(aaaa)', line.lower())) and ipAddrType == "IPv6"):
                    addressList.append((line.split(" ")[-1]).strip())
                elif ((re.search(r''+ipSearch+'', line.lower())) and (re.search(r''+typeSearch+'', line.lower())) and ipAddrType == "IPv4"):
                    addressList.append((line.split(" ")[-1]).strip())
                elif addressList:
                    rangeList.append(addressList)
                    addressList = []
    except Exception as e:
        logger.error("ERROR: Issue parsing Hosts file " + dumpFile + ", Exception: " + str(e))
        return []
    return rangeList

def removeExistingAutoIPRanges(ipTypeName, clusterId):
    '''
    Deletes existing IP Ranges of a certain type for a Cluster so new ranges can be added
    '''
    try:
        autoVmServiceDnsIpRanges = AutoVmServiceDnsIpRange.objects.filter(ipTypeId__ipType=ipTypeName, cluster__id=clusterId)
        if autoVmServiceDnsIpRanges:
            for autoVmServiceDnsIpRange in autoVmServiceDnsIpRanges:
                autoVmServiceDnsIpRange.delete()
    except Exception as e:
        message = "ERROR: Issue removing existing IP Ranges for Cluster " + str(clusterId) + ", Exception: " + str(e)
        logger.error(message)
        return message
    return "Success"

def validateServiceIpRange(ipRangeList):
    '''
    Validates IP Range List before adding it to the DB
    '''
    try:
        if len(ipRangeList) > 1:
            startIp = ipRangeList[0]
            endIp = ipRangeList[-1]
            ret, message = ipRangeCheckStartLessThanEnd(startIp, endIp)
            if ret == 0:
                return True
        elif len(ipRangeList) == 1:
            return True
    except Exception as e:
        logger.error("ERROR: Issue validating IP ranges, Exception: " + str(e))
        return False
    return False

def addAutoServiceDnsIpRange(clusterId, ipRangeList, ipTypeName):
    '''
    Function used to add the VM Service IP Ranges to the DB
    '''
    message = ""
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such cluster ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return message
    try:
        vmServiceIpRangeItemObj = VmServiceIpRangeItem.objects.get(ipType=ipTypeName)
    except Exception as e:
        message = "No such VM Service Range Item: " + str(ipType) + ". Exception: " + str(e)
        logger.error(message)
        return message
    try:
        if validateServiceIpRange(ipRangeList):
            if len(ipRangeList) > 1:
                startIp = ipRangeList[0]
                endIp = ipRangeList[-1]
            else:
                startIp = ipRangeList[0]
                endIp = ipRangeList[0]
            if "ipv6" in ipTypeName.lower():
                autoVmServiceDnsIpRangeObj = AutoVmServiceDnsIpRange.objects.create(
                    ipv6AddressStart=startIp,
                    ipv6AddressEnd=endIp,
                    ipTypeId=vmServiceIpRangeItemObj,
                    cluster=clusterObj
                )
            else:
                autoVmServiceDnsIpRangeObj = AutoVmServiceDnsIpRange.objects.create(
                    ipv4AddressStart=startIp,
                    ipv4AddressEnd=endIp,
                    ipTypeId=vmServiceIpRangeItemObj,
                    cluster=clusterObj
                )
            message = str(ipTypeName) + ": " + str(startIp) + " - " + str(endIp)
    except Exception as e:
        message = "There was an issue saving the auto generated vm service dns ip ranges details for Cluster : " + str(clusterId) + ", Exception: " + str(e)
        logger.error(message)
        return message
    return "Success " + message

def getDeploymentServerPOSTFormValues(fh, serverList, nodeTypeCheck, hardwareType, capacityType):
    '''
    POST Form values for address list and change log
    '''
    addressList = [str(fh.form.cleaned_data['mac_address']),str(fh.form.cleaned_data['ip_address']),str(fh.form.cleaned_data['ipv6_address']),str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['internalIp'])]
    newValues = [str(fh.form.cleaned_data['name']),str(fh.form.cleaned_data['hostname']),str(fh.form.cleaned_data['domain_name']),str(fh.form.cleaned_data['dns_serverA']),str(fh.form.cleaned_data['dns_serverB']),str(fh.form.cleaned_data['mac_address'])]

    if hardwareType == "rack":
        addressList.extend([str(fh.form.cleaned_data['mac_address_eth1']), str(fh.form.cleaned_data['mac_address_eth4']),str(fh.form.cleaned_data['mac_address_eth5']), str(fh.form.cleaned_data['mac_address_eth6']), str(fh.form.cleaned_data['jgroupIp']), ])
        newValues.extend([str(fh.form.cleaned_data['mac_address_eth1'])])
        if capacityType == "production":
            newValues.extend([str(fh.form.cleaned_data['mac_address_eth2']),str(fh.form.cleaned_data['mac_address_eth3'])])
            addressList.extend([str(fh.form.cleaned_data['mac_address_eth2']), str(fh.form.cleaned_data['mac_address_eth3'])])
        newValues.extend([str(fh.form.cleaned_data['mac_address_eth4']), str(fh.form.cleaned_data['mac_address_eth5']), str(fh.form.cleaned_data['mac_address_eth6']),str(fh.form.cleaned_data['wwpnOne']),str(fh.form.cleaned_data['wwpnTwo']),str(fh.form.cleaned_data['bootdisk_uuid']), str(fh.form.cleaned_data['ip_address']),str(fh.form.cleaned_data['ipv6_address']), str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['jgroupIp']), str(fh.form.cleaned_data['internalIp']),str(fh.form.cleaned_data['serial_number']),str(fh.form.cleaned_data['ilo_address']),str(fh.form.cleaned_data['username']),str(fh.form.cleaned_data['password'])])
    elif nodeTypeCheck in serverList:
        newValues.extend([str(fh.form.cleaned_data['mac_address_eth1']),str(fh.form.cleaned_data['mac_address_eth2']),str(fh.form.cleaned_data['mac_address_eth3'])])
        addressList.extend([str(fh.form.cleaned_data['mac_address_eth1']),str(fh.form.cleaned_data['mac_address_eth2']),str(fh.form.cleaned_data['mac_address_eth3']), str(fh.form.cleaned_data['wwpnOne']),str(fh.form.cleaned_data['wwpnTwo']),str(fh.form.cleaned_data['jgroupIp'])])
        if hardwareType != "blade":
            newValues.extend([str(fh.form.cleaned_data['mac_address_eth4']),str(fh.form.cleaned_data['mac_address_eth5']),str(fh.form.cleaned_data['mac_address_eth6']),str(fh.form.cleaned_data['mac_address_eth7']),str(fh.form.cleaned_data['mac_address_eth8']),str(fh.form.cleaned_data['wwpnOne']),str(fh.form.cleaned_data['wwpnTwo']),str(fh.form.cleaned_data['ip_address']),str(fh.form.cleaned_data['ipv6_address']),str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['jgroupIp']),str(fh.form.cleaned_data['internalIp'])])
            addressList.extend([str(fh.form.cleaned_data['mac_address_eth4']),str(fh.form.cleaned_data['mac_address_eth5']),str(fh.form.cleaned_data['mac_address_eth6']),str(fh.form.cleaned_data['mac_address_eth7']),str(fh.form.cleaned_data['mac_address_eth8'])])
        else:
            newValues.extend([str(fh.form.cleaned_data['wwpnOne']),str(fh.form.cleaned_data['wwpnTwo']),str(fh.form.cleaned_data['ip_address']),str(fh.form.cleaned_data['ipv6_address']),str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['jgroupIp']), str(fh.form.cleaned_data['jgroupIp']) ,str(fh.form.cleaned_data['internalIp']),str(fh.form.cleaned_data['enclosure']),str(fh.form.cleaned_data['serial_number']),str(fh.form.cleaned_data['vc_profile_name']),str(fh.form.cleaned_data['ilo_address']),str(fh.form.cleaned_data['username']),str(fh.form.cleaned_data['password'])])
            addressList.extend([str(fh.form.cleaned_data['ilo_address'])])
    elif hardwareType == "blade":
        newValues.extend([str(fh.form.cleaned_data['ip_address']),str(fh.form.cleaned_data['ipv6_address']),str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['internalIp']),str(fh.form.cleaned_data['multicastIp']),str(fh.form.cleaned_data['serial_number']),str(fh.form.cleaned_data['vc_profile_name']),str(fh.form.cleaned_data['enclosure']),str(fh.form.cleaned_data['ilo_address']),str(fh.form.cleaned_data['username']),str(fh.form.cleaned_data['password'])])
        addressList.extend([str(fh.form.cleaned_data['multicastIp']),str(fh.form.cleaned_data['ilo_address'])])
    else:
        newValues.extend([str(fh.form.cleaned_data['ip_address']),str(fh.form.cleaned_data['ipv6_address']),str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['internalIp']),str(fh.form.cleaned_data['multicastIp'])])
        addressList.extend([str(fh.form.cleaned_data['multicastIp'])])
    newValues.extend([str(fh.form.cleaned_data['active'])])
    return addressList, newValues

def doNotUseIpCheck(ipCheck):
    '''
    Check that this IP Address is not be used base on given list
    '''
    doNotUseIp = str(config.get("DMT", "doNotUseIp")).split()
    if '.' in ipCheck:
        (notNeed, lastNum) = ipCheck.rsplit('.', 1)
    else:
        (notNeed, lastNum) = ipCheck.rsplit(':', 1)
    if lastNum in doNotUseIp:
        return True
    return False

def deploymentArtifactInstalled(fileNameLocation):
    '''
    Checking against the ENM ISO Version found in the Version File
    '''
    deploymentArtifacts = set()
    deploymentArtifactsSize = 0
    notDeploymentArtifacts = set()
    notDeploymentArtifactsSize = 0
    mediaVersion, mediaArtifactContent = getENMmediaContentInfo(fileNameLocation)
    returnValue, dataResults = getProductRoleMatrixData()
    if returnValue == 1:
        os.system("rm " + fileNameLocation)
        return returnValue, dataResults, deploymentArtifactsSizeTotal,  notDeploymentArtifacts, notDeploymentArtifactsSizeTotal
    with io.open(fileNameLocation, 'r') as fileData:
        for line in fileData:
            artifactData = artifactName = artifactSize = None
            for artifact in mediaArtifactContent:
                if str(artifact['package_revision__artifactId']) in str(line):
                    artifactName = artifactNameWithcxpNumberAudit(line)
                elif str(artifact['package_revision__package__package_number']) in str(line):
                    artifactName = artifactNameWithoutcxpNumberAudit(line)
                if artifactName:
                    artifactSize = artifact['package_revision__size']
                    artifactData = str(artifactName)+"##"+str(artifactSize)
                    found = filter(lambda x: x.startswith(str(artifactName)+"##"), deploymentArtifacts)
                    if (str(artifact['package_revision__artifactId']) == str(artifactName) and not found):
                        finalArtifactData = getRPMinfoFromProductRoleMatrixData(dataResults, artifactName, artifactData)
                        deploymentArtifactsSize = deploymentArtifactsSize + artifactSize
                        deploymentArtifacts.add(finalArtifactData)
                        artifactData = artifactName = artifactSize = None
                    break
    for artifact in mediaArtifactContent:
        artifactSize = artifact['package_revision__size']
        artifactName = artifact['package_revision__artifactId']
        artifactData = str(artifactName) + "##"+ str(artifactSize)
        found = filter(lambda x: x.startswith(str(artifactName)+"##"), deploymentArtifacts)
        if not found:
            finalArtifactData = getRPMinfoFromProductRoleMatrixData(dataResults, artifactName, artifactData)
            notDeploymentArtifactsSize = notDeploymentArtifactsSize + artifactSize
            notDeploymentArtifacts.add(finalArtifactData)
    deploymentArtifactsSizeTotal = deploymentArtifactsSize
    notDeploymentArtifactsSizeTotal = notDeploymentArtifactsSize
    os.system("rm " + fileNameLocation)
    return mediaVersion, deploymentArtifacts, deploymentArtifactsSizeTotal,  notDeploymentArtifacts, notDeploymentArtifactsSizeTotal


def getENMmediaContentInfo(fileNameLocation):
    '''
    Getting the Media Artifact Information for ENM ISO
    '''
    enmVersion = None
    enmDrop = None
    with io.open(fileNameLocation, 'r') as fileData:
        for line in fileData:
            if "ENM Version info" in str(line):
                enmDrop = str(line).split(": ")[1]
                enmDrop = str(enmDrop).split(" ")[1]
                enmVersion = str(line).split(": ")[2]
                enmVersion = str(enmVersion).split(")")[0]
                break
    enmMediaArtifactContent = ISObuildMapping.objects.only('package_revision__package__package_number', 'package_revision__artifactId', 'package_revision__size').values('package_revision__package__package_number', 'package_revision__artifactId', 'package_revision__size').filter(iso__version=enmVersion, iso__drop__name=enmDrop, iso__mediaArtifact__category__name="productware")
    return enmVersion, enmMediaArtifactContent


def getProductRoleMatrixData():
    '''
    Getting Product Role Matrix Data using the REST API
    '''
    productRoleMatrixUrl = config.get('DMT', 'product_role_matrix_url')
    headers = {"Content-Type":"application/json"}

    apiCommand = requests.get(productRoleMatrixUrl, headers=headers, verify=False)
    if apiCommand.status_code != 200:
        errMsg = "Issue getting Product Role Matrix Data: %s - Error: %s " %(productRoleMatrixUrl, dataResults)
        return 1, errMsg
    dataResults = json.loads(str(apiCommand.content))
    return 0, dataResults


def getRPMinfoFromProductRoleMatrixData(prmData, artifactName, artifactData):
    '''
    Getting rpm information from ProductRoleMatrixData
    '''
    respLineMang = None
    cnaResp = None
    finalArtifactData = str(artifactData)+"##"+str(respLineMang)+"##"+str(cnaResp)
    for dataResult in prmData:
        if 'cras' in dataResult:
            for cras in dataResult['cras']:
                if 'cnas' in cras:
                    for cnas in cras['cnas']:
                        if 'responsibleLineManager' in cnas or 'cnaFunctResp' in cnas:
                            if 'cxps' in cnas:
                                if any(cxp.get('rpm', None) == str(artifactName) for cxp in cnas['cxps']):
                                    if 'responsibleLineManager' in cnas:
                                        respLineMang = smart_str(cnas['responsibleLineManager'])
                                    if 'cnaFunctResp' in cnas:
                                        cnaResp = smart_str(cnas['cnaFunctResp'])
                                    finalArtifactData = str(artifactData)+"##"+str(respLineMang)+"##"+str(cnaResp)
                                    return finalArtifactData
                            else:
                                return finalArtifactData
                        else:
                            return finalArtifactData
                else:
                    return finalArtifactData
        else:
            return finalArtifactData
    return finalArtifactData


def artifactNameWithcxpNumberAudit(line):
    '''
    Getting Artifact Data for line that contains artifact name with cxp number
    '''
    artifactName = None
    (artifactNameInfo, lineInfo)  = str(str(line).lstrip()).split(" ", 1)
    if "vm-package" in str(artifactNameInfo):
        artifactName = str(lineInfo.replace(":", "")).split(" ")[1]
    else:
        artifactName = artifactNameInfo
    return artifactName


def artifactNameWithoutcxpNumberAudit(line):
    '''
    Getting Artifact Data for line under added packages
    '''
    lineInfo = str(str(line).lstrip()).replace(": ", " ").split(" ")
    artifactName = str(lineInfo[0])+"_"+str(lineInfo[2])
    return artifactName


def getTranslationsfromDeployment(clusterId):
    '''
    Function to gather translation data from cluster
    '''
    try:
        if clusterId:
            if Cluster.objects.filter(id=clusterId).exists():
                message = tanslationData(clusterId)
            else:
                return "ERROR: Not a valid Cluster Id"
        else:
            message = "No Cluster Id given.  Please give a Cluster Id "
    except Exception as e:
        message = "ERROR: Issue gathering translation data from httpd service on Cluser " +str(e)
        logger.error(message)
        return message
    return message


def tanslationData(clusterId,product):
    '''
    Function to gather, zip and store Translation Data
    '''
    lmsUploadDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    target = lmsUploadDir + "/deploy"

    clusterValues = ('management_server__server__hostname', 'management_server__server__domain_name', 'management_server__server__hardware_type')
    cluster = Cluster.objects.only(clusterValues).values(*clusterValues).get(id = clusterId)
    fqdnMgtServer = cluster['management_server__server__hostname']  + "." + cluster['management_server__server__domain_name']
    user=config.get('DMT_AUTODEPLOY', 'user')
    masterUserPassword = config.get('DMT_AUTODEPLOY', 'masterPasswordCloudMS1')
    keyFileName=config.get('DMT_AUTODEPLOY', 'key')
    hostName = socket.gethostbyaddr(socket.gethostname())[0]
    environment = cluster['management_server__server__hardware_type']
    remoteConnection = None
    (result, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
    if (result != 0):
        logger.error("Could not create ssh connection to MS")
        return result
    (result,version) = getTranslationVersionData(remoteConnection,lmsUploadDir)
    if (result != 0):
        logger.error("Could not return version of ENM ISO from Deployment")
        return result
    last_line = version.split("\n")[-2]
    version = last_line.split(" ")[1]
    version = version.strip()
    drop = last_line.split(" ")[0]
    translationFile = config.get('DMT_AUTODEPLOY', 'translationFile')
    translationFileTarWithVersion = str(translationFile) + '-'+str(version) + '.tar'
    translationFileWithVersion = str(translationFile) + '-'+str(version) + '.tar.zip'
    translationFileLocation = config.get('DMT_AUTODEPLOY', 'translationFileLocation')
    (result, httpd) = getTranslationHttpdData(remoteConnection,lmsUploadDir)
    if (result != 0):
        logger.error("Could not return the SVC that the httpd service is running on for Deployment")
        return result
    httpd = httpd.strip()
    cmd = ("ssh -i /root/.ssh/vm_private_key cloud-user@"+str(httpd)+ " sudo tar cvf " + str(translationFileLocation) +str(translationFileTarWithVersion) + " /var/www/html/locales/en-us /var/www/html/help/en-us /var/www/html/login/locales/ /var/www/html/login/passwordmanager/locales/ /var/www/html/login/successfullogon/locales/ /ericsson/tor/data/apps/*/locales/en-us;ssh -i /root/.ssh/vm_private_key cloud-user@"+str(httpd)+ " sudo zip " +str(translationFileLocation)+str(translationFileWithVersion) +" " +str(translationFileLocation)+str(translationFileTarWithVersion))
    logger.info("Collecting Translation Files from " +str(httpd) + ".")
    ret = remoteConnection.runCmdSimple(cmd)

    if (ret != 0):
        deleteTranslationFile(remoteConnection,translationFileLocation,translationFileWithVersion)
        logger.error("Error encountered while running command to collect Translation Data")
        return ret
    logger.info("Successfully collected Translation Data")
    translationFileLocation = config.get('DMT_AUTODEPLOY', 'translationFileLocation')
    loginToTranslationrunCommand = config.get('DMT_AUTODEPLOY', 'loginToTranslationrunCommand')
    baseLogin = loginToTranslationrunCommand + " " + fqdnMgtServer + " " + user + " " + masterUserPassword
    user = 'root'
    copyCommandToMs =(str(baseLogin)+  " \\' scp -i /root/.ssh/vm_private_key cloud-user@"+str(httpd)+ ":"+str(translationFileLocation)+str(translationFileWithVersion) +" /tmp \\'")
    logger.info("Copying the translation file from the SVC to the MS")
    returnCode = remoteConnection.runCmdSimple(copyCommandToMs)
    if returnCode != 0:
        deleteTranslationFile(remoteConnection,translationFileLocation,translationFileWithVersion)
        return returnCode
    else:
        translationFileLocation = config.get('DMT_AUTODEPLOY', 'translationFileLocation')
        gateWayServer = str(hostName) + '.athtem.eei.ericsson.se'
        gateWayPassword = config.get('DMT_AUTODEPLOY', 'gateWayPassword')
        loginToTranslationrunCommand = config.get('DMT_AUTODEPLOY', 'loginToTranslationrunCommand')
        baseLogin = loginToTranslationrunCommand + " " + gateWayServer + " " + user + " " + gateWayPassword
        user = 'root'
        copyCommand =(str(baseLogin) + " \\'scp " + user+"@"+str(fqdnMgtServer)+":"+str(translationFileLocation)+str(translationFileWithVersion)+" " +str(translationFileLocation)+"\\'")
        logger.info("Copying the translation file from the MS to the Gateway.")
        returnCode = remoteConnection.runCmdSimple(copyCommand)
        if returnCode != 0:
            deleteTranslationFile(remoteConnection,translationFileLocation,translationFileWithVersion)
            return returnCode
        else:
            if ISObuild.objects.filter(artifactId=translationFile, version=version).exists():
                logger.error("The Translation File already exist for artifact version" +str(version))
                return 1
            else:
                mediaArtifact = MediaArtifact.objects.get(name=translationFile)
                mediaType = mediaArtifact.mediaType
                mediaCategory = mediaArtifact.category.name
                transactionGroupId = config.get('DMT_AUTODEPLOY', 'translationGroupId')
                artifactSize, statusCode = cireports.utils.getMediaArtifactSize(translationFile, version, transactionGroupId, mediaType,mediaCategory)
                if statusCode == 200:
                    logger.info("Translation Data artifact with version " +str(version) + " already exists in nexus")
                else:
                    returnCode = uploadTranslationFileToNexus(version,translationFile,translationFileLocation,translationFileWithVersion)
                    if returnCode != 0:
                        logger.error("There was an issue deploying the Translation Data Artifact to Nexus")
                        return returnCode
                returnCode = uploadTranslationFileToPortal(user,version,translationFile,drop,product)
                if returnCode != 0:
                    logger.error("There was an issue deploying the Translation Data Artifact to the CI Portal")
                    return returnCode
        logger.info("Successfully collected Translatable Data and deployed to Nexus and the CI Portal")
        deleteTranslationFile(remoteConnection,translationFileLocation,translationFileWithVersion)
        return 0


def deleteTranslationFile(remoteConnection,translationFileLocation,translationFileWithVersion):
    '''
    Function to Delete Translation File if it exists
    '''
    translationFilefullpath = str(translationFileLocation) +str(translationFileWithVersion)
    if os.path.isfile(translationFilefullpath):
        cmd = "rm -rf " +str(translationFilefullpath)
        ret = remoteConnection.runCmdSimple(cmd)
        if (ret != 0):
            logger.error("Error: Failed to delete Translation File from " +str(lmsUploadDir))
    else:
        logger.info("No Translation File exists to remove")

def translationRunCmd(command, baseLogin=None):
    '''
    Used to run commands on the Management and Gateway Server
    '''
    if "scp " in str(command):
        cmdType = "fileTransfer"
    else:
        cmdType = "runCmd"
    if baseLogin:
        fullCmd = baseLogin + " '" + command + "' "+str(cmdType)
    else:
        fullCmd = command
    logger.info(str(fullCmd))
    process = subprocess.Popen(fullCmd, stderr=STDOUT,stdout=PIPE, shell=True)
    outputData, returnCode = process.communicate()[0], process.returncode
    logger.info(outputData)
    if not returnCode == 0:
        errMsg = "Issue with command: " + str(command) + ", output: " +str(outputData)
        return errMsg, returnCode
    return outputData, 0

def manageDeploymentServerValidation(key, value):
    '''
    This function validate passed values from JSON object (empty, none, incorrect format, etc...)
    '''
    hardwareTypesList = ["cloud","virtual","rack","blade"]
    nodeTypesList = ["netsim","workload"]
    ipv4KeysList = ["dnsA","dnsB","ipv4HostAddr","ipv4InterAddr","ipv4StorgAddr","ipv4BackpAddr","ipv4MultiVlanAddr"]

    if key == "machineName" and value == "" or value.lower() == "none":
        raise ValueError('Value of machine name "' + str(value) + '" has not been specified.')
    if key == "hostName" and value == "" or value.lower() == "none":
        raise ValueError('Value of host name "' + str(value) + '" has not been specified.')
    if key == "hardwareType" and value.lower() not in hardwareTypesList:
        raise ValueError('Value "' + str(value) + '" is incorrect. Make sure it is equals to eny of those types (cloud, virtual, rack, blade)')
    if key == "nodeType" and value.lower() not in nodeTypesList:
        raise ValueError('Value "' + str(value) + '" is incorrect. Make sure it is eqauls to eny of those types (NETSIM, WORKLOAD)')
    if any(key in ipv4 for ipv4 in ipv4KeysList):
        if value != "":
            try:
                socket.inet_pton(socket.AF_INET, value)
            except socket.error:
                raise ValueError('Invalid IPv4 format of a key ' + str(key) + ', make sure format it is correct - "' + str(value) + '".')
        if key == "ipv4HostAddr" and value == "":
            raise ValueError('IPv4 Host Address not provided.')
    if key == "ipv6HostAddr":
        if value != "":
            try:
                socket.inet_pton(socket.AF_INET6, value)
            except socket.error:
                raise ValueError('Invalid IPv6 format of a key ' + str(key) + ', make sure format it is correct - "' + str(value) + '".')
    if key == "macAddr" and value != "":
        if not re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", value.lower()):
            raise ValueError('Invalid MAC format of a key ' + str(key) + ', make sure format it is correct - "' + str(value) + '".')

def manageDeploymentServerDeletion(receivedJsonData, clusterId):
    '''
    This function manage deployment server deletion restcall
    '''
    message = "success"
    hostName = receivedJsonData['hostName'].strip()
    try:
        if ClusterServer.objects.get(server__hostname = hostName, cluster = clusterId):
            Server.objects.filter(hostname = hostName, hostnameIdentifier = clusterId).delete()
    except Exception as e:
        message = "error: There issue with removing a server from cluster " + clusterId + ": " + str(e)
        logger.error(message)
        return message
    return message

def manageDeploymentServerCreation(receivedJsonData, clusterId):
    '''
    This function manage deployment server creation restcall, calls validation of parameters function and add a new server into given cluster.
    '''
    message = "server successfuly created"

    try:
        cluster = Cluster.objects.get(id = clusterId)
    except Exception as e:
        message = "Error 404: Issue getting the Deployment Id - " + str(clusterId) + " : " + str(e)
        logger.error(message)
        return message

    try:
        for key, value in receivedJsonData.iteritems():
            manageDeploymentServerValidation(key, value.strip())

        machineName  = receivedJsonData['machineName'].strip()
        hostName     = receivedJsonData['hostName'].strip()
        domainName   = receivedJsonData['domainName'].strip()
        dnsA         = receivedJsonData['dnsA'].strip()
        dnsB         = receivedJsonData['dnsB'].strip()
        hardwareType = receivedJsonData['hardwareType'].strip()
        nodeType     = receivedJsonData['nodeType'].strip()
        serverStatus = receivedJsonData['serverStatus'].strip()
        macAddr      = receivedJsonData['macAddr'].strip()
        ipv4HostAddr = receivedJsonData['ipv4HostAddr'].strip()

        if macAddr == "" and hardwareType == "cloud":
            raise ValueError('MAC Address not provided.')
        if domainName == "" or domainName.lower() == "none":
            domainName = config.get('DMT_SERVER', 'domain')
        if dnsA == "" or dnsA.lower() == "none":
            dnsA = config.get('DMT_SERVER', 'dns1')
        if dnsB == "" or dnsB.lower() == "none":
            dnsB = config.get('DMT_SERVER', 'dns2')
        if serverStatus.lower() == "false":
            serverStatus = False
        else:
            serverStatus = True

        if "cloud" in hardwareType:
            identifier = macIdentifier = ipv4Identifier = ipv6Identifier = clusterId
        else:
            identifier = macIdentifier = ipv4Identifier = ipv6Identifier = "1"
    except Exception as e:
        message = "Error 412: There was an issue with information given: " + str(e)
        logger.error(message)
        return message

    try:
        with transaction.atomic():
            if not nodeType.lower() == 'netsim':
                if ClusterServer.objects.filter(cluster = cluster, node_type = nodeType):
                    raise ValueError('This server ' + str(nodeType) + ' is already defined.')
            serverObject = Server.objects.create(name = machineName, hardware_type = hardwareType, hostname = hostName, hostnameIdentifier = clusterId, domain_name = domainName, dns_serverA = dnsA, dns_serverB = dnsB)
            clusterInfo = ClusterServer(server_id = serverObject.id, cluster_id = clusterId, node_type = nodeType.upper(), active = serverStatus)
            clusterInfo.save()
            if not NetworkInterface.objects.filter(server_id=serverObject.id).exists():
                if hardwareType == "virtual" and macAddr == "":
                    networkObject, created = NetworkInterface.objects.get_or_create(server = serverObject)
                    networkObject.mac_address = getLowestAvailableMacAddress(clusterId)
                    networkObject.server = serverObject
                    networkObject.save()
                    try:
                        networkObject = NetworkInterface.objects.get(server=serverObject.id, interface="eth0")
                        macAddr = networkObject.mac_address
                    except:
                        macAddr = ""
                else:
                    networkObject = NetworkInterface.objects.create(server = serverObject, mac_address = macAddr, nicIdentifier = macIdentifier)

            if not IpAddress.objects.filter(nic = networkObject.id, ipType = "other").exists():
                if 'ipv6HostAddr' in receivedJsonData:
                    ipv6HostAddr = receivedJsonData['ipv6HostAddr'].strip()
                    ipAddrObject = IpAddress.objects.create(nic = networkObject, ipType = "other", address = ipv4HostAddr, ipv6_address = ipv6HostAddr, ipv4UniqueIdentifier = ipv4Identifier, ipv6UniqueIdentifier = ipv6Identifier)
                else:
                    ipAddrObject = IpAddress.objects.create(nic = networkObject, ipType = "other", address = ipv4HostAddr, ipv4UniqueIdentifier = ipv4Identifier)

            if nodeType.lower() == 'workload':
                if 'ipv4MultiVlanAddr' not in receivedJsonData or receivedJsonData['ipv4MultiVlanAddr'].strip() == "":
                    multicastGateway, multicastIp, multicastBitmask = getNextFreeInternalIP(cluster, "PDU-Priv_nodeInternalJgroup")
                    if not IpAddress.objects.filter(nic = networkObject.id, ipType = "multicast").exists():
                        multicastIpObject = IpAddress.objects.create(nic = networkObject, ipType = "multicast", address = multicastIp, ipv4UniqueIdentifier = clusterId)
                if 'ipv4InterAddr' not in receivedJsonData or receivedJsonData['ipv4InterAddr'].strip() == "":
                    internalGW, internalIp, internalBitmask = getNextFreeInternalIP(cluster)
                    if not IpAddress.objects.filter(nic = networkObject.id, ipType = "internal").exists():
                        internalIPObject = IpAddress.objects.create(nic = networkObject, ipType = "internal", address = internalIp, ipv4UniqueIdentifier = clusterId)

            if 'ipv4InterAddr' in receivedJsonData:
                ipv4InterAddr = receivedJsonData['ipv4InterAddr'].strip()
                if not IpAddress.objects.filter(nic = networkObject.id, ipType = "internal").exists():
                    internalIPObject = IpAddress.objects.create(nic = networkObject, ipType = "internal", address = ipv4InterAddr, ipv4UniqueIdentifier = clusterId)
            if 'ipv4StorgAddr' in receivedJsonData:
                ipv4StorgAddr = receivedJsonData['ipv4StorgAddr'].strip()
                if not IpAddress.objects.filter(nic = networkObject.id, ipType = "storage").exists():
                    storageIpObject = IpAddress.objects.create(nic = networkObject, ipType = "storage", address = ipv4StorgAddr, ipv4UniqueIdentifier = ipv4Identifier)
            if 'ipv4BackpAddr' in receivedJsonData:
                ipv4BackpAddr = receivedJsonData['ipv4BackpAddr'].strip()
                if not IpAddress.objects.filter(nic = networkObject.id, ipType = "backup").exists():
                    bckUpIpObject = IpAddress.objects.create(nic = networkObject, ipType = "backup", address = ipv4BackpAddr, ipv4UniqueIdentifier = ipv4Identifier)
            if 'ipv4MultiVlanAddr' in receivedJsonData:
                ipv4MultiVlanAddr = receivedJsonData['ipv4MultiVlanAddr'].strip()
                if not IpAddress.objects.filter(nic = networkObject.id, ipType = "multicast").exists():
                    multicastIpObject = IpAddress.objects.create(nic = networkObject, ipType = "multicast", address = ipv4MultiVlanAddr, ipv4UniqueIdentifier = clusterId)
    except Exception as e:
        message = "Error 412: There issue with adding a server to cluster " + clusterId + ": " + str(e)
        logger.error(message)
        return message
    return message

def getTranslationVersionData(remoteConnection,lmsUploadDir):
    '''
    Function used to check all the services on the system to ensure they are up
    '''
    lmsUploadDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    cmd = lmsUploadDir + "/deploy/bin/getTranslationVersionData.bsh"
    logger.info("Finding the ISO version and Drop for the Translation File")
    ret,output = remoteConnection.runCmdGetOutput(cmd)
    if ret == 0:
        logger.info("Gathering Verison Data for Translation File")
    else:
        logger.error("There was an issue gathering the Version Data")
    return ret, output

def getTranslationHttpdData(remoteConnection,lmsUploadDir):
    '''
    Function used to check all the services on the system to ensure they are up
    '''
    lmsUploadDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    cmd = lmsUploadDir + "/deploy/bin/getTranslationhttpdService.bsh"
    logger.info("Finding which svc the httpd service is running on")
    ret,output = remoteConnection.runCmdGetOutput(cmd,"tty-ssh")
    if ret == 0:
        logger.info("Finding http service")
    else:
        logger.error("There was an issue getting information about the httpd service")
    return ret, output

def uploadTranslationFileToPortal(user,version,translationFile,drop,product):
    '''
    Function used to upload the SED to the DB used by the UI and the TAF testware
    '''
    translationArmRepo = config.get('DMT_AUTODEPLOY', 'translationArmRepo')
    transactionGroupId = config.get('DMT_AUTODEPLOY', 'translationGroupId')
    dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mediaArtifact = MediaArtifact.objects.get(name=translationFile)
    mediaType = mediaArtifact.mediaType
    mediaCategory = mediaArtifact.category.name
    drop=Drop.objects.get(name=drop, release__product__name=product)
    artifactSize, statusCode = cireports.utils.getMediaArtifactSize(translationFile, version, transactionGroupId, mediaType,mediaCategory)
    if statusCode == 200:
        artifactSize = int(artifactSize)
    else:
        logger.debug("Error: There was an issue creating a new Media Revision Size entry in the CIFWK DB, Artifact Size is set to 0.  Error: " +str(artifactSize))
        artifactSize=0
    try:
        ISOBuildObj = ISObuild.objects.create(version=version, groupId=transactionGroupId, artifactId=translationFile, mediaArtifact=mediaArtifact, drop=drop, build_date=dateCreated, arm_repo=translationArmRepo, size=artifactSize)
        logger.info("New Translation Data Build Object Created based on Data Entered, as does not already exist: %s: %s: %s" %(translationFile, version, drop))
        return 0
    except Exception as e:
        logger.error("There was an issue with the update of the Translation File within the utils file see function uploadTranslationFile" +str(e))
        return 1

def uploadTranslationFileToNexus(version,translationFile,translationFileLocation,translationFileWithVersion):
    '''
    Function used to upload the SED to the DB used by the UI and the TAF testware
    '''
    nexusUrl = config.get('DMT_AUTODEPLOY', 'nexus_url')
    translationArmRepo = config.get('DMT_AUTODEPLOY', 'translationArmRepo')
    transactionGroupId = config.get('DMT_AUTODEPLOY', 'translationGroupId')
    cmd = ("mvn deploy:deploy-file -DgroupId="+str(transactionGroupId)+ " -DartifactId="+str(translationFile) +" -Dversion="+str(version)+ " -DgeneratePom=true -Dpackaging=tar.zip -DrepositoryId=nexus -Durl="+str(nexusUrl)+"/" +str(translationArmRepo)+ ' -Dfile=' +str(translationFileLocation)+str(translationFileWithVersion))
    logger.info("Deploying Artifact to Nexus")
    try:
        os.system(cmd)
        return 0
    except Exception as e:
        logger.error("There was an issue deploying the Translation File to Nexus" +str(e))
        return 1


def getDeploymentDDdata(clusterId):
    '''
    Getting Deployment's Deployment Description Data
    '''
    ddDataDict = {}
    statusCode = 200
    try:
        ddDataValues = "deployment_description__name", "deployment_description__dd_type__dd_type", "deployment_description__version__version", \
                       "deployment_description__capacity_type", "deployment_description__auto_deployment", "deployment_description__sed_deployment", \
                       "auto_update", "update_type", "iprange_type"
        ddData = DDtoDeploymentMapping.objects.only(ddDataValues).values(*ddDataValues).get(cluster__id=clusterId)
        ddDataDict["deployment_description_data"] = { "name": str(ddData["deployment_description__name"]),
                                                      "type": str(ddData["deployment_description__dd_type__dd_type"]),
                                                      "version": str(ddData["deployment_description__version__version"]),
                                                      "capacity_type": str(ddData["deployment_description__capacity_type"]),
                                                      "auto_deployment": str(ddData["deployment_description__auto_deployment"]),
                                                      "sed_deployment": str(ddData["deployment_description__sed_deployment"]),
                                                      "auto_update": str(ddData["auto_update"]),
                                                      "update_type": str(ddData["update_type"]),
                                                      "ip_range_source": str(ddData["iprange_type"])
                                                    }
    except DDtoDeploymentMapping.DoesNotExist:
        errMsg = "Issue getting the Deployment Description data for Deployment, Does Not Exist for this ID: " + str(clusterId)
        logger.error(str(errMsg))
        ddDataDict = errMsg
        statusCode = 404

    return ddDataDict, statusCode

def updateDeploymentWithDDFile(user, clusterId, ddName):
    '''
    Update Deployment's Deployment Description file
    '''
    try:
        # Getting Deployment Description Mapping
        if DDtoDeploymentMapping.objects.filter(cluster__id=clusterId).exists():
            ddMapping = DDtoDeploymentMapping.objects.get(cluster__id=clusterId)
        else:
            return "No Deployment Description Mapping associated with this Deployment, please add one manually.", 404

        if DeploymentDescription.objects.only('name', 'version').values('name', 'version').filter(name=ddName).exists():
            ddNameObj = DeploymentDescription.objects.filter(name=ddName).order_by('-version')[0]
            ddMapping = DDtoDeploymentMapping.objects.get(cluster__id=clusterId)
            # Old Values
            oldValues = [str(ddMapping.deployment_description.name) + "##Deployment Description", str(ddMapping.deployment_description.version.version) + "##Version", str(ddMapping.deployment_description.dd_type.dd_type) + "##DD Type", str(ddMapping.deployment_description.capacity_type) + "##Capacity Type", str(ddMapping.auto_update) + "##Auto Update", str(ddMapping.update_type) + "##Update Type", str(ddMapping.iprange_type) + "##IpRange Type"]
            # Saving Object
            ddMapping.deployment_description = ddNameObj
            ddMapping.save(force_update=True)
            # New Values
            newValues = [str(ddMapping.deployment_description.name), str(ddMapping.deployment_description.version.version), str(ddMapping.deployment_description.dd_type.dd_type), str(ddMapping.deployment_description.capacity_type), str(ddMapping.auto_update), str(ddMapping.update_type), str(ddMapping.iprange_type)]
            # Saving Logs
            changedContent = logChange(oldValues, newValues)
            logMessage = "Edited Deployment Description Mapping: " + str(changedContent)
            logAction(user, ddMapping.cluster, "edit", logMessage)
            return "SUCCESS", 200

        return "Issue given Deployment Description File is not in DB, please try again with different file name.", 404
    except Exception as e:
        return "Issue updating Deployment's Deployment Description. " + str(e), 500

def normalizedIpv6Postfix(ipv6Address):
    if '/' in ipv6Address:
        ipv6Address = ipv6Address.split('/')[0]
    return ipv6Address


def getNasInformation(input):
    '''
    Getting NAS information from DB either using hostname of the NAS or the Cluster/Deployment Id
    '''
    try:
        mapping = ""
        nasSvr = ""
        hostname = input
        if input.isdigit():
            mapping = ClusterToDASNASMapping.objects.filter(cluster__id=int(input))
        else:
            mapping = ClusterToDASNASMapping.objects.filter(dasNasServer__hostname=hostname)
        if mapping:
            nasSvrs = NASServer.objects.filter(server__hostname=mapping[0].dasNasServer.hostname)
            if nasSvrs:
                nasSvr = nasSvrs[0]
        if not nasSvr:
            if input.isdigit():
                mapping = ClusterToNASMapping.objects.filter(cluster__id=int(input))
            else:
                mapping = ClusterToNASMapping.objects.filter(nasServer__server__hostname=hostname)
        if mapping:
            nasSvr = mapping[0].nasServer
        if not nasSvr:
            nasSvrs = NASServer.objects.filter(server__hostname=hostname)
            if nasSvrs:
                nasSvr = nasSvrs[0]
        if not nasSvr:
            return "NAS Details Not Found", 404

        nasHostname = nasSvr.server.hostname
        ipAddress = ""
        nasType = ""
        if mapping:
            clusterObj = mapping[0].cluster
            if NasStorageDetails.objects.filter(cluster=clusterObj).exists():
                nasType = NasStorageDetails.objects.get(cluster=clusterObj).nasType
                if str(nasType) == "unityxt":
                    if ClusterToStorageMapping.objects.filter(cluster=clusterObj).exists():
                        clsStorageMapObj = ClusterToStorageMapping.objects.get(cluster=clusterObj)
                        storageIpMapList = StorageIPMapping.objects.filter(storage=clsStorageMapObj.storage)
                        for storageIp in storageIpMapList:
                            nasHostname = storageIp.storage.hostname
                            if storageIp.ipnumber == 1:
                                ipAddress = storageIp.ipaddr

        nic = NetworkInterface.objects.get(server=nasSvr.server)
        nasDetails = {
                "machineName": str(nasSvr.server.hostname),
                "hostname": str(nasHostname),
                "hardwareType": str(nasSvr.server.hardware_type),
                "domainName": str(nasSvr.server.domain_name),
                "dnsIpAddressA": str(nasSvr.server.dns_serverA),
                "dnsIpAddressB": str(nasSvr.server.dns_serverB),
                "primaryNic": str(nic.mac_address),
                "ipAddress": "",
                "bitmask": "",
                "gateway": "",
                "nasVip1": "",
                "nasVip2": "",
                "nasInstallIp1": "",
                "nasInstallIp2": "",
                "nasInstallIloIp1": "",
                "nasInstallIloIp2": "",
                "nasType": str(nasType)
            }

        ipaddrs = []
        ipaddrs += IpAddress.objects.filter(nic=nic.id)
        for ipaddr in ipaddrs:
            if ipaddr.ipType == "nas":
                nasDetails["ipAddress"] = str(ipaddr.address) if not ipAddress else str(ipAddress)
                nasDetails["bitmask"] = str(ipaddr.bitmask)
                nasDetails["gateway"] = str(ipaddr.gateway_address)
            if ipaddr.ipType == "nasvip1":
                nasDetails["nasVip1"] = str(ipaddr.address)
            if ipaddr.ipType == "nasvip2":
                nasDetails["nasVip2"] = str(ipaddr.address)
            if ipaddr.ipType == "nasinstallip1":
                nasDetails["nasInstallIp1"] = str(ipaddr.address)
            if ipaddr.ipType == "nasinstallip2":
                nasDetails["nasInstallIp2"] = str(ipaddr.address)
            if ipaddr.ipType == "nasInstalIlolIp1":
                nasDetails["nasInstallIloIp1"] = str(ipaddr.address)
            if ipaddr.ipType == "nasInstalIlolIp2":
                nasDetails["nasInstallIloIp2"] = str(ipaddr.address)
        return nasDetails, 200
    except Exception as e:
        return "Issue getting NAS Details from the DB. " + str(e), 404

def getNasConfigArtifacts(contents):
    logger.info('Getting nas config artifacts')
    nasConfig = nasRhelPatch = None
    for item in contents:
        if item['mediaArtifactVersion__drop__release__product__name'] == config.get('DMT_AUTODEPLOY', 'nasConfigProductName'):
            nasConfig = item
        if item['mediaArtifactVersion__drop__release__product__name'] == config.get('DMT_AUTODEPLOY', 'nasRhel79PatchProductName'):
            nasRhelPatch = item
        if item['mediaArtifactVersion__drop__release__product__name'] == config.get('DMT_AUTODEPLOY', 'nasRhel88PatchProductName'):
            nasRhelPatch = item
    return nasConfig, nasRhelPatch

def getNexusUrlForNasMedia(mediaName, version):
    media = mediaName.rsplit('-', 1)[0]
    url = config.get('DMT_AUTODEPLOY', 'nexus_url') + '/' + config.get('DMT_AUTODEPLOY', 'nas_nexus_media_location') + '/' + media + '/' \
        + version + '/' + mediaName
    hubUrl = config.get('DMT_AUTODEPLOY', 'nexus_proxy_url') + '/' + config.get('DMT_AUTODEPLOY', 'nas_nexus_media_location') + '/' + media + '/' \
        + version + '/' + mediaName
    return url, hubUrl

def downloadTarGzToMgtServer(remoteConnection, mgtServer, artifact, lmsUploadDir, tmpArea):
    ret = 0
    version = artifact['mediaArtifactVersion__version']
    mediaArtifact = getNasMediaArtifact(artifact)
    mediaName = getMediaArtifactName(artifact)
    logger.info("Checking if the " + str(mediaArtifact) + " artifact is already present")
    if (remoteConnection.runCmd("ls " + lmsUploadDir + "/" + mediaArtifact) != 0):
        url, proxyUrl = getNexusUrlForNasMedia(mediaArtifact, version)
        logger.info('Downloading ' + str(mediaArtifact) + ' to ' + str(tmpArea))
        ret = fwk.utils.downloadFile(proxyUrl, tmpArea)
        if (ret != 0):
            return ret
        logger.info("Transferring " + mediaArtifact + " to " + str(mgtServer))
        ret = paramikoSftp(
                mgtServer.server.hostname + "." + mgtServer.server.domain_name,
                "root",
                lmsUploadDir + "/" + mediaArtifact,
                tmpArea + "/" + mediaArtifact,
                int(config.get('DMT_AUTODEPLOY', 'port')),
                config.get('DMT_AUTODEPLOY', 'key'),
                "put")
        if (ret != 0):
            remoteConnection.close()
            return ret
        logger.info('Copying ' + str(mediaName) + ' to ' + str(config.get('DMT_AUTODEPLOY', 'nasArtifactDirectory')))
        cleanAndCopyNasMediaArtifact(remoteConnection, lmsUploadDir, mediaName, mediaArtifact)
        ret = dmt.deploy.checkIsoMd5Sum(remoteConnection, mgtServer, mediaArtifact, lmsUploadDir, tmpArea, proxyUrl, url)
    else:
        logger.info(str(mediaName) + ' was previously downloaded, copying to ' + str(config.get('DMT_AUTODEPLOY', 'nasArtifactDirectory')))
        cleanAndCopyNasMediaArtifact(remoteConnection, lmsUploadDir, mediaName, mediaArtifact)
    if os.path.exists(tmpArea + "/" + mediaArtifact):
        logger.info('Removing file: ' + str(tmpArea + "/" + mediaArtifact))
        os.remove(tmpArea + "/" + mediaArtifact)
    return ret

def cleanAndCopyNasMediaArtifact(remoteConnection, lmsUploadDir, mediaName, mediaArtifact):
    # Make NAS Artifact Directory if it does not already exist
    remoteConnection.runCmd('sudo mkdir ' + config.get('DMT_AUTODEPLOY', 'nasArtifactDirectory'))
    remoteConnection.runCmd('sudo rm -f ' + config.get('DMT_AUTODEPLOY', 'nasArtifactDirectory') + '/' + str(mediaName) + '*')
    remoteConnection.runCmd('sudo cp ' + lmsUploadDir + '/' + str(mediaArtifact) + ' ' + config.get('DMT_AUTODEPLOY', 'nasArtifactDirectory'))

def getNasMediaArtifact(artifact):
    if artifact is None:
        return None
    media = cireports.models.MediaArtifact.objects.filter(id=artifact['mediaArtifactVersion__mediaArtifact__id'])
    if len(media) > 0:
        media = media[0]
    else:
        return None
    version = artifact['mediaArtifactVersion__version']
    mediaName = media.name + '-' + version + '.' + media.mediaType
    return mediaName

def getMediaArtifactName(artifact):
    artifactName = None
    artifact = cireports.models.MediaArtifact.objects.filter(id=artifact['mediaArtifactVersion__mediaArtifact__id'])
    if len(artifact) > 0:
        artifact = artifact[0]
    if artifact is not None:
        artifactName = artifact.name
    return artifactName

def waitForNasArtifactsToDownload(nasConfigThread, nasRhelPatchThread):
    while nasConfigThread.isAlive():
        logger.info("Artifact " + str(nasConfigThread.name) + " still downloading, please wait...")
        time.sleep(5)
    logger.info("Artifact " + str(nasConfigThread.name) + " download complete proceeding with installtion...")

    while nasRhelPatchThread.isAlive():
        logger.info("Artifact " + nasRhelPatchThread.name + " still downloading, please wait...")
        time.sleep(5)
    logger.info("Artifact " + str(nasRhelPatchThread.name) + " download complete proceeding with installtion...")

def isEnmRackDeployment(enmDeploymentType):
    '''
    Check if ENM is deployed on rack
    '''
    if enmDeploymentType is not None:
        if "Rack" in str(enmDeploymentType.name):
            return True
    return False


def convertStrToBool(string):
    '''
    Convert a given string to boolean
    '''
    if string == "True":
        return True
    elif string == "False":
        return False
    else:
        return None


def resetFcSwitches(clusterId):
    '''
    Reset FC Switches to None for a given cluster
    '''
    if NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
        nasStorageDetailsObj = NasStorageDetails.objects.get(cluster_id=clusterId)
        nasStorageDetailsObj.fcSwitches = None
        nasStorageDetailsObj.save()

def checkIncludeCompactAuditLogger(clusterId, ddName=None):
    if ddName:
        for depType in config.get('DMT', 'compact_audit_logger_supported_deployments').split(','):
            if depType in ddName:
                return True
        return False
    if DDtoDeploymentMapping.objects.filter(cluster=clusterId).exists():
        ddToDepMapping = DDtoDeploymentMapping.objects.get(cluster=clusterId)
        deploymentDesciption = ddToDepMapping.deployment_description.name
        for depType in config.get('DMT', 'compact_audit_logger_supported_deployments').split(','):
            if depType in deploymentDesciption:
                return True
    return False

def createOrEditMgmtServerCredentials(password, credType, lmsHostname, user, signum):
    try:
        server = Server.objects.get(hostname=str(lmsHostname))
        lms = ManagementServer.objects.get(server_id=server.id)
        mgtServerCredMapping = ManagementServerCredentialMapping.objects.filter(mgtServer=lms.id)
        for mapping in mgtServerCredMapping:
            credential = Credentials.objects.get(id=mapping.credentials_id)
            if credential.username == user:
                editMgmtServerCredential(user, password, credType, credential)
                message = 'Password successfully changed for: ' + str(user)
                logger.info(message)
                return True, message
        returnCode, outcome = createMgmtServerCredential(user, password, credType, lms, signum)
        if returnCode == '1':
            return False, outcome
        message = 'Password successfully created for: ' + str(user)
        logger.info(message)
        return True, message
    except Exception as e:
        message = 'Failed to handle mgt server password generation: '
        logger.error(message + str(e))
        return False, message

def getLmsUserPassword(lmsHostname, user):
    try:
        server = Server.objects.get(hostname=lmsHostname)
        lms = ManagementServer.objects.get(server_id=server.id)
        mgtServerCredMapping = ManagementServerCredentialMapping.objects.filter(mgtServer=lms.id)
        for mapping in mgtServerCredMapping:
            credential = Credentials.objects.get(id=mapping.credentials_id)
            if credential.username == user:
                return credential.password
    except Exception as e:
        logger.error("Unable to retreive strong password for " + user + "@" + lmsHostname + ": " + str(e))

def lmsPasswordGenerator(lmsHostname):
    functionalUsersRequired = config.get('DMT', 'rhelUsernames')
    credType = config.get('DMT', 'rhelUserType')
    signum = config.get('DMT', 'functionalSignum')
    for user in functionalUsersRequired.split(','):
        password = generateRandomPassword()
        createOrEditMgmtServerCredentials(password, credType, lmsHostname, user, signum)

def generateRandomPassword(length=16, charset='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()'):
    randomBytes = os.urandom(length)
    lenCharset = len(charset)
    indices = [int(lenCharset * (ord(byte) / 256.0)) for byte in randomBytes]
    return "".join([charset[index] for index in indices])

def checkUserAccessToLmsPasswords(signum, hostname):
    try:
        server = Server.objects.get(hostname=hostname)
        managementServer = ManagementServer.objects.get(server_id=server.id)
        cluster = Cluster.objects.get(management_server_id=managementServer.id)
    except Exception as e:
        logger.error(e)
        return False, "Management server does not exist or is not mapped to a cluster"
    try:
        user = User.objects.get(username=signum)
        groups = user.groups.all()
        for group in groups:
            if group == cluster.group:
                return True, "Success"
        return False, "Unauthorized. Please ensure you have been added to this deployments user group."
    except Exception as e:
        logger.error(e)
        return False, "Signum not found. Please ensure you are registered on DMT."

def editMgmtServerCredential(username, password, credType, credentialObj):
    '''
    Function to edit the server credentials
    '''
    try:
        credentialObj.username = username
        credentialObj.password = password
        credentialObj.type = credType
        credentialObj.save(force_update=True)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue editing the server credentials Exception: " + str(e)
        logger.error(message)
        return ("1",message)

def createMgmtServerCredential(username, password, credType, mgmtServerObj, signum):
    '''
    Function to create the server credentials
    '''
    try:
        credential = Credentials.objects.create(username=username, password=password, credentialType=credType)
        dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ManagementServerCredentialMapping.objects.create(mgtServer=mgmtServerObj, credentials=credential, signum=signum, date_time=dateTime)
        return ("0","Success")
    except Exception as e:
        message = "There was an issue saving the management server credentials, Exception: " + str(e)
        logger.error(message)
        return ("1",message)


def getNasPhysicalIp(baseLogin):
    '''
    Function to get the first Physical NAS node for VAPP only.
    Note: result is a string containing output from the ssh command.
    It contains up to 3 irelevant IP addresses (IP of the machine in
    which we run the command) in the output, the IP we need, only appears
    once so we pick the IP where the count is 1.
    '''
    nasGetPhysicalIpCommand = config.get(
            'DMT_AUTODEPLOY', 'nasGetPhysicalIpCommand')
    result, returnCode = dmt.deploy.executeCmd(
            nasGetPhysicalIpCommand, baseLogin)
    ipPattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipAddresses = re.findall(ipPattern, result)
    physicalIp = None
    for ip in ipAddresses:
        if ipAddresses.count(ip) == 1:
            physicalIp = ip
    return physicalIp

def parseNASCommandForSlaveNode(nasData):
    '''
    Getting NAS Server iLo data from a physical Deployment
    '''
    nasCommand = 'vxclustadm nidmap'
    result, returnCode = dmt.deploy.runServerCommand(nasCommand, str(nasData['ipAddress']), nasData['nasUsername'], nasData['nasPassword'])
    if returnCode != 0:
        return (result, returnCode)

    nasSlaveNode, returnCode = dmt.deploy.findNASSlaveNode(result)
    if "Slave Node not found in results" in nasSlaveNode:
        nasSlaveNode = None
    logger.info('NAS slave node:  ' + str(nasSlaveNode))
    return (nasSlaveNode, returnCode)

def triggerJenkinsWebhook(webhook, parameters):
    '''
    Trigger given Jenkins webhook with given parameters.
    '''
    try:
        response = requests.post(webhook, data=parameters, timeout=10, verify=False)
        logger.info("Jenkins webhook initiation status: " + str(response.status_code) + " - " + str(response.json().get("message")))
    except Exception as e:
        logger.info('Jenkins webhook trigger did not succeed: ' + str(e))
