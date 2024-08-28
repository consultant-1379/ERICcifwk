from libcloud.compute.types import NodeState
from dmt.evcloud import EVCloudNodeDriver
from ConfigParser import SafeConfigParser
from cireports.models import *
from dmt.models import *
from ciconfig import CIConfig
import libcloud.security
import dmt.sshtunnel
import dmt.sftp
import dmt.utils
import fwk.utils
import os, sys, time, signal,logging, re
from django.db import connection

logger = logging.getLogger(__name__)
config = CIConfig()

gatewayName = ""
gatewayIP = ""

child_pid = 0

def auth():
    libcloud.security.VERIFY_SSL_CERT = False
    libcloud.security.VERIFY_SSL_DISABLED_MSG = "Cloud team need to get a properly signed cert!!"
    #vcloud = get_driver(Provider.VCLOUD)

    driver = EVCloudNodeDriver(
            config.get("DMT","vcloud_user"),
            config.get("DMT","vcloud_pass"),
            host=config.get("DMT", "vcloud_host"),
            api_version='1.5')
    return driver

def getNode(driver, node):
    if node == None:
        return
    nodes = driver.list_nodes()
    for n in nodes:
        if n.name == node:
            return n
    return None

def startApp(driver, tplName, appName):

    '''
    Starts an instance of the defined template, using the provided name.

    Returns:
    0: Success
    1: No such image in the cloud
    2: There was an error deploying the vApp template
    '''
    try:
        logger.info("Getting list of available images")
        images = driver.list_images()
        image = None
        try:
            image = [i for i in images if i.name == tplName][0]
        except Exception as e:
            logger.error("No such vApp template: " + tplName)
            dmt.utils.handlingError(str(e))
        if image is None:
            dmt.utils.handlingError("No such vApp template: " + appName)
        logger.info("Instantiating node instance of " + tplName + " as " + appName)
        node = driver.create_node(name=appName, image=image, ex_deploy=False)
        logger.info("Resetting MAC address on Gateway node")
        updateType = "macUpdate"
        gatewayName = getGatewayInfo(driver,appName,updateType)
        logger.info("Successfully received Gateway Name: "
                     + str(gatewayName))
        driver.reset_mac(appName, gatewayName, 0)
        logger.info("Deploying node")
        driver.ex_deploy_node(node)
        return 0
    except Exception as e:
        logger.error("Got an exception: " + str(e))
        dmt.utils.handlingError(str(e))

def getGatewayInfo(driver, appName, updateType):
    try:
        node = getNode(driver, appName)
        logger.info("vApp Name: " +str(appName))
        if (node == None):
            return ""
        for k, v in node.extra.items():
            for vm in v:
                # is this our vm?
                if "gateway" in vm.get('name'):
                    logger.info("VM: " + vm.get('name'))
                    for name, item in vm.items():
                        if updateType == "macUpdate":
                            if str(name) == "name":
                                gatewayName = item
                                logger.info("The LITP Gateway Name is: " + str(gatewayName))
                                return gatewayName
                        else:
                            if str(name) == "public_ips":
                                gatewayIp = item[0]
                                logger.info("The LITP Gateway IP Address is: " + str(gatewayIp))
                                return gatewayIp
    except Exception as e:
        raise CommandError("There was an Issue with getting LITP Gateway Information "
            + str(e) + "Please also ensure that your Vapp is powered on")
        dmt.utils.handlingError(str(e))

def storeCloudTemplateInfo(comment,node):
    logger.info("Node Name: " + str(node.name))
    description = str(comment)
    #Adding new VApp instance to dmt_apptemplate table
    doesVappExistinDB =  AppTemplate.objects.filter(name=node.name)
    if doesVappExistinDB:
        logger.error("Sorry " + str(node.name) + "already exists therefore cannot add again")
        logger.error("Please delete " + str(node.name) + " from the DB and retry")
        # TODO: implement "delete" functionality
        return False
    logger.info("Adding " +
            str(node.name) + " With Description " + str(description) +
            " to CI Fwk DB")
    description = str(comment)
    newAppTemplate = AppTemplate(name=node.name, desc=description)
    newAppTemplate.save()

    # When the VM info is returned thisis contained in a dict,
    # inside the dict is a list and then inside the list is
    # another dict hense the below for loops
    logger.info("Adding VAPP hosts and IP to db tables ")
    for key1, value1 in node.extra.items():
        for value in value1:
            for key2, value2 in value.items():
                if key2 == "name":

                    if "generic" in value2:
                        serverType = "generic"
                    else:
                        serverType = "gateway"
                    newHost = AppHost(template=newAppTemplate,
                            name=value2,
                            hostname=value2,
                            type=serverType)
                    logger.debug("Server type: " + serverType)
                    newHost.save()

                if key2 == "public_ips":
                    iplist = ','.join(value2)
                    newIP = AppIpAddress(value=str(iplist),mode="ipv4")
                    newIP.save()
            logger.debug("Updating Hostname key to the dmt_apphostipmap table")
            newMap = AppHostIpMap(apphost=newHost,ip_addr=newIP)
            newMap.save()
    return 0

def createSSHTunnel(LMSIP,GWIP):
    '''
    This Function is used to set up an SSH Tunnel to the LMS (LITP Management Station).

    The Function takes in a number of parameters from the cifwk or local config file
    to establish connection to the LMS

    These parameters are feed to the local sshtunnel python script which holds the
    logic to connect using the paramiko plugin
    '''

    sshtunnelVerboses = None
    sshtunnelPort = int(config.get('DMT_SSHTunnel', 'sshtunnelPort'))
    sshtunnelUser = config.get('DMT_SSHTunnel', 'sshtunnelUser')
    sshtunnelKeyfile = None
    sshtunnelLook_for_keys = True
    sshtunnelPassword = config.get('DMT_SSHTunnel', 'sshtunnelPassword')
    sshtunnelRemote = str(LMSIP)
    sshtunnelLocal = str(GWIP)

    logger.info("Instantiating SSH Tunnel")

    child_pid = os.fork()
    if child_pid == 0:
        logger.info("SSH Tunnel Running on Process ID: " + str(os.getpid()))
        try:
            dmt.sshtunnel.main(sshtunnelVerboses, sshtunnelPort, sshtunnelUser, sshtunnelKeyfile, sshtunnelLook_for_keys, sshtunnelPassword, sshtunnelRemote, sshtunnelLocal)
            logger.info("SSH Tunnell Running on Process ID: " + str(os.getpid()))
        except Exception as e:
            logger.error("SSH Tunnel Failed to start with Error: ")
            dmt.utils.handlingError(str(e))
    time.sleep(5)
    return child_pid

def getPackageObject(artifact, version, completeArtifactURL, latest):
    '''
    The getPackageObject function get the package object according to the version information given in
    '''
    packageObject = None
    notFoundError = "The Artifact " + str(artifact) + " was not found in CIFWK DB."
    if completeArtifactURL == "None":
        try:
            if latest == "no":
                logger.info("Getting Artifact " + artifact + " version " + version)
                errorMessage = "The Artifact: " + str(artifact)+ " with version: " + str(version) + " was not found in CIFWK DB."
                if "latest" in version.lower():
                    version = version.lower();
                    version = version.replace("latest", "");
                    try:
                        packageObject = PackageRevision.objects.exclude(platform='sparc').filter(version__startswith=version, package__name=artifact).order_by('version').latest('date_created')
                    except Exception as e:
                        logger.error(str(errorMessage) + " Exception: " + str(e))
                        dmt.utils.handlingError(str(errorMessage) + " Exception: " + str(e))
                        return packageObject
                else:
                    try:
                        packageObject = PackageRevision.objects.exclude(platform='sparc').get(version=version, package__name=artifact)
                    except Exception as e:
                        logger.error(str(errorMessage) + " Exception: " + str(e))
                        dmt.utils.handlingError(str(errorMessage) + " Exception: " + str(e))
                        return packageObject
                latestArtifact = PackageRevision.objects.exclude(platform='sparc').filter(package__name=artifact)
                if str(packageObject) != str(latestArtifact.latest('date_created')):
                    logger.warning("The Artifact: "+str(packageObject)+ " is not the latest Artifact. The Latest Artifact is: " +str(latestArtifact.latest('date_created')))
                else:
                    logger.info("The latest Artifact will be downloaded from Nexus: " + str(packageObject))
            else:
                logger.info("Getting Artifact " + artifact)
                try:
                    packageObject = PackageRevision.objects.exclude(platform='sparc').filter(package__name=artifact).latest('date_created')
                except Exception as e:
                    logger.error(str(notFoundError) + " Exception: " + str(e))
                    dmt.utils.handlingError(str(notFoundError) + " Exception: " + str(e))
                    return packageObject
            return packageObject
        except Exception as e:
            logger.error(str(notFoundError) + " Exception: " + str(e))
            dmt.utils.handlingError(str(notFoundError) + " Exception: " + str(e))
            return packageObject
    else:
        try:
            packageObject = PackageRevision.objects.exclude(platform='sparc').filter(package__name=artifact).latest('date_created')
        except Exception as e:
            logger.error(str(notFoundError) + " Exception: " + str(e))
            packageObject = None
        return packageObject

def downloadArtifact(artifactLocalDirectory,completeArtifactURL,packageObject=None,product=None):
    '''
    The downloadArtifact function generates the complete artifact url and calls the
    fwk.utils.downloadFile to downlaod artifact from nexus to local dir
    '''
    artifactName = ""
    if completeArtifactURL == "None":
        try:
            artifactName =  packageObject.package.name + "-" + packageObject.version + "." + packageObject.m2type
            if product != None:
                completeArtifactURL = packageObject.getNexusDeployUrl(product)
            else:
                completeArtifactURL = packageObject.getNexusDeployUrl()
            logger.info("Nexus URL: " + completeArtifactURL)
        except Exception as e:
            logger.error("Issue making the complete Artifact URL using DB")
            dmt.utils.handlingError(str(e))
    else:
        if "http" in completeArtifactURL:
            artifactName = os.path.basename(completeArtifactURL)
    try:
        ret = fwk.utils.downloadFile(completeArtifactURL,artifactLocalDirectory)
        if (ret != 0):
            return 1
        logger.info("Successfully downloaded Artifact: " +str(artifactName) + " from Nexus")
        if packageObject:
            if packageObject.category.name == 'image':
                fwk.utils.downloadFile(completeArtifactURL+'.md5',artifactLocalDirectory)
                logger.info("Successfully downloaded MD5 Sum for Artifact: " +str(artifactName) + " from Nexus")
        return artifactName
    except Exception as e:
        logger.error("Could not download " + str(artifactName) + " " + str(e))
        dmt.utils.handlingError(str(e))
    return 0

def uploadArtifactToNode(artifactName,artifactLocalDirectory,artifactRemoteDirectory,sftpPassword=None,newartifactName=None,serverName=None):
    '''
    This Function is used to upload the Artifacts downloaded from NEXUS to the LMS.

    The main call used in this function is made on the sftp module which takes the
    arguments provided and proforms the SFTP over an SSH Tunnell to the LITP LMS
    '''
    if newartifactName == None:
        newartifactName = artifactName
    if serverName == None:
        serverName = "LMS"

    sftpNode = config.get('DMT_SFTP', 'sftpNode')
    sftpPort = int(config.get('DMT_SFTP', 'sftpPort'))
    sftpUser = config.get('DMT_SFTP', 'sftpUser')
    if sftpPassword == None:
        sftpPassword = config.get('DMT_SFTP', 'sftpPassword')
    sftpLocalFile = artifactLocalDirectory + "/" + artifactName
    sftpRemoteFile = artifactRemoteDirectory + "/" + newartifactName
    sftpType = "put"

    logger.info("Starting to SFTP the downloaded Artifacts to LITP " + serverName)

    try:
        dmt.sftp.sftp(sftpNode, sftpPort, sftpUser, sftpPassword, sftpLocalFile, sftpRemoteFile,sftpType)
    except Exception as e:
        logger.error("Artifact(s) have not successfully uploaded to LITP " + serverName + " giving Error " +str(e))
        dmt.utils.handlingError(str(e))
    return 0

def destroySSHTunnel(child_pid):
    '''
    This Function is used to ensure that the SSH Tunnel is closed once all Artifact's
    have been uploaded to the LITP LMS
    '''
    logger.info("All SFTP Activity now complete shutting down SSH Tunnel")
    try:
        os.kill(child_pid, signal.SIGKILL)
        logger.info("Successfully shut down SSH Tunnel")
    except Exception as e:
        logger.error("Failed to shut down SSH Tunnel giving Error:")
        dmt.utils.handlingError(str(e))
    return 0

def resetGatewayMac(driver, appName, nicId):
    logger.info("Attempting to Reset MAC Adress(es) of Gateway of vApp: " +str(appName))
    updateType = "macUpdate"
    gatewayName = getGatewayInfo(driver,appName,updateType)
    logger.info("Successfully received Gateway Name: "
            + str(gatewayName))
    driver.reset_mac(appName, gatewayName, nicId)
