import logging
logger = logging.getLogger(__name__)
from django.core.management.base import BaseCommand, CommandError
import os
import re
from metrics.models import SPPServer
from fwk.models import *
import urllib2
import shutil
import dmt.utils
from distutils.version import LooseVersion
from cireports.models import *

from ciconfig import CIConfig
config = CIConfig()

def getCifwkVersion():
    """
    Get the version of the currently installed Framework (we just look at the
    name of the parent directory)
    """
    return os.path.basename(os.path.realpath(getCIFwkBase() + "/latest"))

def getCIFwkBase():
    '''
    Get the base directory of the installation of the CI Framework
    '''
    return os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../../../")

def getTickerTapeMessage():
    """
    Getting the message(s) from database for Ticker Tape
    """
    infoList = []
    information = None
    try:
        allMessages = TickerTape.objects.filter(hide=False).order_by('severity__id')
        if allMessages:
            infoList.append('<div align="center" class="tickerTape"><a href="/TickerTapeHistory" title="Ticker Tape History" style="color: inherit;"><marquee behavior="scroll" direction="left" scrollamount="3">')
            for message in allMessages:
                infoList.append("<img src='/static/images/" + str(message.severity.severity) + ".png' alt='" + str(message.severity.severity) + "' width='28' height='28' class='tickerTapeIcon' /> <span class='tickerTapeText'>" +  message.title + " : " + message.summary + "&nbsp;&nbsp;&nbsp;</span>")
            infoList.append('</marquee></a></div>')
            information = '    '.join(infoList)
    except Exception as e:
        logger.error("Issue getting ticker tape messages" +str(e))
    return information

def getSPPLinks():
    '''
    Get a list of SPP Portal links to be displayed on Portal Main page using django template tag.
    '''
    serverList = []
    serverListPageUpdate = ""
    try:
        sppServers = SPPServer.objects.all()
        if sppServers:
            for server in sppServers:
                serverList.append('<li><a href="' + str(server.url) + '/users/login">' + str(server.name) + '</a></li>')
        serverListPageUpdate = '    '.join(serverList)
    except Exception as e:
        logger.error("Issue getting SPP Servers links" +str(e))
    return serverListPageUpdate

def downloadFile(src, dst):
    try:
        file_name = src.split('/')[-1]
        try:
            u = urllib2.urlopen(src)
        except Exception as error:
            logger.error("Issue opening given Source URL, this URL may not Exist : " + str(src) + " Error Thrown: " + str(error))
            return 1
        try:
            f = open(dst + "/" + file_name, 'wb')
        except Exception as e:
            logger.error("Issue with opening destination with file name: " +str(file_name))
            dmt.utils.handlingError(str(e))
        meta = u.info()
        fileSize = int(meta.getheaders("Content-Length")[0])
        fileSizeDownloaded = 0
        blockSize = 8388608
        while True:
            buffer = u.read(blockSize)
            if not buffer:
                break
            fileSizeDownloaded += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (fileSizeDownloaded, fileSizeDownloaded * 100. / fileSize)
            status = status + chr(8)*(len(status)+1)
            logger.info(status)
        f.close()
        return 0
    except Exception as e:
        logger.error("Issue downloading file: " +str(e))
        return 1

def diffVersions(currVer, ciFwkVer):
    '''
    Check if the current version installed is greater than the version to upgrade to
    Return True / False
    '''
    return LooseVersion(str(currVer)) > LooseVersion(str(ciFwkVer))

def performUpgrade(ciFwkVer, runTests=False, fork=True):
    # Check the current Version that is installed and return if the version to upgrade to is the same
    currVer = getCifwkVersion()
    base = getCIFwkBase() + "/"
    logger.info("Current CI Framework version installed is %s", currVer)
    logger.info("Attempting to Upgrade to version %s", ciFwkVer)
    if (diffVersions(currVer, ciFwkVer)):
        logger.info( "You are attempting to downgrade from " + currVer + " to " + ciFwkVer + ", that's not supported")
        return "You are attempting to downgrade from " + currVer + " to " + ciFwkVer + ", that's not supported"
    elif (currVer == ciFwkVer):
        logger.info( "This is the current version installed - Nothing to do")
        return "This is the current version installed - Nothing to do"

    # Parse the info passed to the function
    groupId = re.sub('\.','/', config.get("CIFWK", "groupId"))
    artifactId = config.get("CIFWK", "artifactId")
    dwnldName = artifactId + "-" + str(ciFwkVer) + ".zip"
    dwnldLoc = "/var/tmp/"

    check = os.path.isdir(base + "/" + str(ciFwkVer))
    if check:
        logger.info("Version " + ciFwkVer + " has been previously downloaded, Backing up the directory to " + ciFwkVer + "_bckup" )
        os.rename(base + "/" + ciFwkVer, base + "/" + ciFwkVer + "_bckup")

    logger.info("Downloading version " + ciFwkVer)
    # Get the artifact down from nexus
    fileToGet = config.get("CIFWK", "nexus_url") + "/releases/" + groupId + "/" + artifactId + "/" + ciFwkVer + "/" + dwnldName
    try:
        downloadFile(fileToGet, dwnldLoc)
    except Exception as e:
        logger.error("Got an exception retrieving " + fileToGet + ": " + str(e))
        return "There was a problem trying to download this version, please contact your Administrator"

    # Unzip the file
    extract = "unzip -q " + dwnldLoc + dwnldName + " -d " + base
    returncode = os.system(extract)
    if (returncode != 0):
        try:
            os.remove(dwnldLoc + dwnldName)
        except:
            pass
        return "There was a problem trying to download this version, please contact your Administrator"

    # Run the install script
    cmd = base + ciFwkVer + "/bin/cifwk-install -v " + ciFwkVer + " -r " + base + " -d " + config.get("CIFWK", "cifwkdb")
    if fork:
        cmd = cmd + " -f true -e " + config.get("CIFWK", "upgrade_email") + " -g " + config.get("CIFWK", "group_upgrade_email")
    logger.info("Running the following Upgrade command : %s", cmd)
    upgradeRtrn = os.system(cmd) # Update this to execute this in the background
    if (upgradeRtrn != 0):
        try:
            os.remove(dwnldLoc + dwnldName)
            shutil.rmtree(base + ciFwkVer)
        except:
            pass
        return "There was a problem trying to upgrade to this version, please contact your Administrator"
    else:
        bkup_check = os.path.isdir(base + "/" + ciFwkVer + "_bckup" )
        if bkup_check:
            logger.info("Removing previously downloaded and backed up directory : " + base + "/" + ciFwkVer + "_bckup" )
            shutil.rmtree(base + ciFwkVer + "_bckup" )
        try:
            os.remove(dwnldLoc + dwnldName)
        except:
            pass
            return "Upgrade was a success, However, there was a problem removing the downloaded file at " + dwnldLoc + dwnldName
        try:
            logger.info('Cleaning up older versions of cifwk')
            requiredISOBuildFields=('package_revision__version', 'package_revision__date_created')
            dropPkgMap = DropPackageMapping.objects.filter(package_revision__package__name='ERICCIFWKPORTAL_CXP9030099').order_by('-drop').only(requiredISOBuildFields).values(*requiredISOBuildFields)
            dropPkgMapFiltered = filter(lambda pkg : pkg['package_revision__version'] not in [ciFwkVer, currVer], dropPkgMap)
            for pkg in dropPkgMapFiltered:
                if os.path.isdir(base + "/" + pkg['package_revision__version'] ):
                    logger.info('Removing cifwk version: ' + str(pkg['package_revision__version']))
                    shutil.rmtree(base + pkg['package_revision__version'])
        except:
            return "Upgrade was a success, However, there was a problem removing older versions"

    try:
        if runTests:
           # Gather information needed for job to create new CI ISO
            package = PackageRevision.objects.only('id').values('id').get(package__name=artifactId, version=ciFwkVer)
            requiredDpmFields = 'drop__id', 'drop__name', 'drop__release__name', 'drop__release__product__name'
            dpm = DropPackageMapping.objects.only(requiredDpmFields).values(*requiredDpmFields).get(package_revision_id = package['id'])
            dropId = dpm['drop__id']
            drop = dpm['drop__name']
            release = dpm['drop__release__name']
            product = dpm['drop__release__product__name']
            isoId = config.get("CIFWK", "mediaArtifactId")
            if ISObuild.objects.filter(artifactId = isoId, drop=dropId).exists():
                latestIsoVer = ISObuild.objects.filter(artifactId = isoId, drop=dropId).only('version').values('version').order_by('-build_date')[0]['version']
                newIsoVer = drop + '.'+str(int(latestIsoVer.split('.')[-1])+1)
            else:
                newIsoVer = drop + ".1"
           # kicking off Jenkins job to run TAF Smoke Tests
            url = config.get("FEM","femBasePlus")+"/job/ADD_CI_MEDIA_ARTIFACT_TO_CI_PORTAL/buildWithParameters?token=triggerBuild&DROP="+drop+"&PRODUCT="+product+"&RELEASE="+release+"&MEDIANAME="+isoId+"&VERSION="+newIsoVer
            req = urllib2.Request(url)
            resp = urllib2.urlopen(req)
    except Exception as e:
        pass
        message = "Upgrade was a success, However, there was a problem in kicking off the ISO Build and SmokeTest Jenkins jobs."
        logger.error(message + " ERROR: "+str(e))
        return message + " ERROR: "+str(e)
    return "Upgrade started. An email detailing the result will be sent to " + config.get("CIFWK", "upgrade_email")

def performUpgradeE2C(ciFwkVer, runTests=False, fork=True):
    # Check the current Version that is installed and return if the version to upgrade to is the same
    currVer = getCifwkVersion()
    base = getCIFwkBase() + "/"
    logger.info("Current CI Framework version installed is %s", currVer)
    logger.info("Attempting to Upgrade to version %s", ciFwkVer)
    if (diffVersions(currVer, ciFwkVer)):
        logger.info( "You are attempting to downgrade from " + currVer + " to " + ciFwkVer + ", that's not supported")
        return "You are attempting to downgrade from " + currVer + " to " + ciFwkVer + ", that's not supported"
    elif (currVer == ciFwkVer):
        logger.info( "This is the current version installed - Nothing to do")
        return "This is the current version installed - Nothing to do"

    # Parse the info passed to the function
    groupId = re.sub('\.','/', config.get("CIFWK", "groupId"))
    artifactId = config.get("CIFWK", "artifactId")
    dwnldName = artifactId + "-" + str(ciFwkVer) + ".zip"
    dwnldLoc = "/var/tmp/"

    check = os.path.isdir(base + "/" + str(ciFwkVer))
    if check:
        logger.info("Version " + ciFwkVer + " has been previously downloaded, Backing up the directory to " + ciFwkVer + "_bckup" )
        os.rename(base + "/" + ciFwkVer, base + "/" + ciFwkVer + "_bckup")

    logger.info("Downloading version " + ciFwkVer)
    # Get the artifact down from nexus
    fileToGet = config.get("CIFWK", "nexus_url") + "/releases/" + groupId + "/" + artifactId + "/" + ciFwkVer + "/" + dwnldName
    try:
        downloadFile(fileToGet, dwnldLoc)
    except Exception as e:
        logger.error("Got an exception retrieving " + fileToGet + ": " + str(e))
        return "There was a problem trying to download this version, please contact your Administrator"

    # Unzip the file
    extract = "unzip -q " + dwnldLoc + dwnldName + " -d " + base
    returncode = os.system(extract)
    if (returncode != 0):
        try:
            os.remove(dwnldLoc + dwnldName)
        except:
            pass
        return "There was a problem trying to download this version, please contact your Administrator"
    cmd = base + ciFwkVer + "/bin/cifwk-install-e2c -v " + ciFwkVer + " -r " + base + " -d " + config.get("CIFWK", "cifwkdb") + " -h " + config.get("CIFWK", "dbHost") + " -o " + config.get("CIFWK", "dbPort") + " -p " + config.get("CIFWK", "dbPassword")
    if fork:
        cmd = cmd + " -f true -e " + config.get("CIFWK", "upgrade_email") + " -g " + config.get("CIFWK", "group_upgrade_email")
    logger.info("Running the following Upgrade command : %s", cmd)
    upgradeRtrn = os.system(cmd) # Update this to execute this in the background
    logger.info("Finished execution of upgrade command with return code "+ str(upgradeRtrn))
    if (upgradeRtrn != 0):
        try:
            os.remove(dwnldLoc + dwnldName)
            shutil.rmtree(base + ciFwkVer)
        except:
            pass
        return "There was a problem trying to upgrade to this version, please contact your Administrator"
    else:
        logger.info('Portal upgrade was successful')

        bkup_check = os.path.isdir(base + "/" + ciFwkVer + "_bckup" )
        if bkup_check:
            logger.info("Removing previously downloaded and backed up directory : " + base + "/" + ciFwkVer + "_bckup" )
            shutil.rmtree(base + ciFwkVer + "_bckup" )
        try:
            os.remove(dwnldLoc + dwnldName)
        except:
            pass
            return "Upgrade was a success, However, there was a problem removing the downloaded file at " + dwnldLoc + dwnldName
    try:
        if runTests:
           # Gather information needed for job to create new CI ISO
            package = PackageRevision.objects.only('id').values('id').get(package__name=artifactId, version=ciFwkVer)
            requiredDpmFields = 'drop__id', 'drop__name', 'drop__release__name', 'drop__release__product__name'
            dpm = DropPackageMapping.objects.only(requiredDpmFields).values(*requiredDpmFields).get(package_revision_id = package['id'])
            dropId = dpm['drop__id']
            drop = dpm['drop__name']
            release = dpm['drop__release__name']
            product = dpm['drop__release__product__name']
            isoId = config.get("CIFWK", "mediaArtifactId")
            if ISObuild.objects.filter(artifactId = isoId, drop=dropId).exists():
                latestIsoVer = ISObuild.objects.filter(artifactId = isoId, drop=dropId).only('version').values('version').order_by('-build_date')[0]['version']
                newIsoVer = drop + '.'+str(int(latestIsoVer.split('.')[-1])+1)
            else:
                newIsoVer = drop + ".1"
           # kicking off Jenkins job to run TAF Smoke Tests
            url = config.get("FEM","femBasePlus")+"/job/ADD_CI_MEDIA_ARTIFACT_TO_CI_PORTAL/buildWithParameters?token=triggerBuild&DROP="+drop+"&PRODUCT="+product+"&RELEASE="+release+"&MEDIANAME="+isoId+"&VERSION="+newIsoVer
            req = urllib2.Request(url)
            resp = urllib2.urlopen(req)
    except Exception as e:
        pass
        message = "Upgrade was a success, However, there was a problem in kicking off the ISO Build and SmokeTest Jenkins jobs."
        logger.error(message + " ERROR: "+str(e))
        return message + " ERROR: "+str(e)
    return "Upgrade started. An email detailing the result will be sent to " + config.get("CIFWK", "upgrade_email")

def showServerUpdateForm(option,server):
    if "edit" in option:
        title = "Update Server Form for: " +str(server)
        serverObject = CIFWKDevelopmentServer.objects.get(vm_hostname=server)
        domainName = serverObject.domain_name
        ipAddress = serverObject.ipAddress
        user = serverObject.owner
        description = serverObject.description
        form = DevelopmentServer(initial={'vm_hostname':server, 'domain_name': domainName, 'ipAddress': ipAddress, 'owner': user, 'description': description})
        return dmt.views.processForm(request, form, title, button="Update..")

    elif "delete" in option:
        try:
            CIFWKDevelopmentServer.objects.filter(vm_hostname=server).delete()
            cursor = connection.cursor()
            logger.info("Server " +str(server)+ " deleted from database")
        except Exception as e:
            raise CommandError("There was an issue deleting server " +str(server)+ " from database: " +str(e))
        return HttpResponseRedirect("/fwk/devServers/list/")


def getSPPNewMenuLinks():
    '''
    Get a list of SPP Portal links and names for the Portal Main menu using django template tag.
    '''
    serverList = []
    serverListPageUpdate = ""
    try:
        sppServers = SPPServer.objects.all()
        if sppServers:
            for server in sppServers:
                serverList.append(", {\nname: '" + str(server.name) + "',\nicon: 'fa fa-cloud',\nlink: '" + str(server.url) + "/users/login'\n}")
        serverListPageUpdate = '    '.join(serverList)
    except Exception as e:
        logger.error("Issue getting SPP Servers links" +str(e))
    return serverListPageUpdate

def pageHitCounter(page, objId=None, username=None):
    '''
    Adding Page Hit Count
    '''
    try:
        if objId:
            if PageHitCount.objects.filter(page=page, page_object_id=objId).exists():
                page = PageHitCount.objects.get(page=page, page_object_id=objId)
            else:
                page = PageHitCount.objects.create(page=page, page_object_id=objId)
        else:
            if PageHitCount.objects.filter(page=page).exists():
                page = PageHitCount.objects.get(page=page)
            else:
                page = PageHitCount.objects.create(page=page)
        page.hitcount = page.hitcount + 1
        page.save()
        if username and str(username) != "AnonymousUser":
            userObj = User.objects.get(username=str(username))
            if UserPageHitCount.objects.filter(username=userObj, page=page).exists():
                pageUser = UserPageHitCount.objects.get(username=userObj, page=page)
                pageUser.hitcount = pageUser.hitcount + 1
                pageUser.save()
            else:
                UserPageHitCount.objects.create(username=userObj, page=page, hitcount=1)
    except Exception as error:
        logger.error("Issue Saving Hit Count for Page - " +str(page) + " with Id -" +str(objId) + ": " +str(error))
