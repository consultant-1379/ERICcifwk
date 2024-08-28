import dmt.dhcpConfiguration
import dmt.createSshConnection
import dmt.jumpFromNetwork
import dmt.utils
import dmt.autoDeployUtils
import fwk.utils
import os, time, calendar, commands, socket, sys, re
import dmt.remotecmd
import dmt.buildconfig
import tempfile
import dmt.infoforConfig
import paramiko
import logging
import shutil
import commands
import urllib2
import signal
import glob
import getpass
import json
import cireports
import threading
import thread
import pexpect
import math

from subprocess import *
from distutils.version import LooseVersion
from ciconfig import CIConfig
from random import randint
from cireports.common_modules.common_functions import *
from datetime import datetime
from django.core.files.move import file_move_safe
from django.db.models import Q
from cireports.models import *
from dmt.models import *
from ast import literal_eval

config = CIConfig()
logger = logging.getLogger(__name__)
env = setStatusUpdate = ""

def identifyPatches(mediaName):
    version = mediaName.split("-")[1]
    if version.startswith("7") and version != "79":
        return 7
    elif version == "OS":
        return 6

def handler(signum, frame):
    logger.info("Captured Key Stroke")
    descriptionDetails = "Caught Ctrl-C Command, Cleaned up the system"
    try:
        insertTS.delete()
    except:
        logger.debug("Not using global insertTS")
    try:
        jumpServerIp = dmt.utils.getJumpServerIp(networkGlobal)
        ret = checkCloudLock(cloudLockFileName,cloudQueueFileName,jumpServerIp)
        if ret == 1:
            removeCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp)
        if setStatusUpdate == "no":
            if getEnvironment(clusterIdGlobal) == "cloud":
                state = "IDLE"
            else:
                state = "FAILED"
        updateDeploymentStatus(clusterIdGlobal,state,None,None,None,None,None,None,None,descriptionDetails)
        if tmpArea != None or remoteConnection != None:
            dmt.utils.dmtError(descriptionDetails, clusterIdGlobal, tmpArea, remoteConnection)
    except Exception as e:
        dmt.utils.dmtError(descriptionDetails)

def errorExit(msg):
    logger.error(msg)
    raise Exception(msg)

def getFreeCluster(clusterGroup, newStatus):
    '''
    Checking for free Deployment
    '''
    recheckWait = int(config.get('DMT', 'recheckWait'))
    recheckCount = int(config.get('DMT', 'recheckCount'))
    maxFailed = int(config.get("DMT", "maxFailed"))
    queueWaitTime =  int(config.get("DMT", "queueWaitTime"))
    queueWaitTimeMax =  int(config.get("DMT", "queueWaitTimeMax"))
    global insertTS, installGroup
    insertTS = None
    wait = ""
    installGroup = clusterGroup
    allDeploymentField = ('cluster__name', 'id', 'cluster__name', 'status__status__status', )
    allDeployments = ClusterToInstallGroupMapping.objects.only(allDeploymentField).values(*allDeploymentField).filter(group__installGroup=installGroup)
    totalDeployments = len(allDeployments)
    allIdle, totalIdle, allFailed, totalFailed, allBusy, totalBusy, allQuarantine, totalQuarantine = getInstallGroupStatusInfo(installGroup)

    if totalDeployments == 0:
        return "Error: No Deployments in install group"

    deploymentStatusInfo(allDeployments)
    deleteOldRequestfromQueue(installGroup, queueWaitTimeMax)
    insertTS, wait = addAndCheckRequestQueue(installGroup, wait, totalIdle)
    while wait == "True":
        #wait until cluster frees up
        logger.info("Waiting for free Deployment: Total:<"+str(totalDeployments) + "> Available:<"+str(totalIdle)+ "> Busy:<"+str(totalBusy)+  "> Failed:<"+str(totalFailed) + "> Quarantined:<"+str(totalQuarantine) + ">")
        if totalFailed != 0 :
            #free up failed if older than specified hours
            checkingFailedDeploymentStatus(allFailed, maxFailed)
        time.sleep(recheckWait)
        allIdle, totalIdle, allFailed, totalFailed, allBusy, totalBusy, allQuarantine, totalQuarantine = getInstallGroupStatusInfo(installGroup)
        try:
            wait = overAllCheckRequestQueue(installGroup, insertTS, wait, totalIdle, queueWaitTime, recheckWait)
            if "Error" in wait:
                return wait
        except Exception as e:
            errorMsg = "Error in Checking Request Queue: " + str(e)
            logger.error(errorMsg)
            return errorMsg

    if insertTS != None:
       insertTS.delete()

    return getfreeDeploymentId(allIdle, newStatus)

def getfreeDeploymentId(allIdle, newStatus):
    '''
    Getting the ID for free the Deployment
    '''

    freeCluster=allIdle[:1]
    free = ""
    for free in freeCluster:
        if getEnvironment(free['cluster__id']) == "cloud":
            newStatus = "IDLE"
        dmt.utils.setClusterStatus(free['cluster__id'], newStatus)
        logger.info("Selected Deployment: " +str(free['cluster__name']))
    if free:
        return str(free['cluster__id'])
    else:
        return "Error with install group: "


def deploymentStatusInfo(allDeployments):
    '''
    Log information on deployment Status in install group
    '''
    logger.info("Deployments\t\tStatus")
    logger.info("########################################")
    for server in allDeployments:
        logger.info(server['cluster__name'] + "\t" + server['status__status__status'])
    logger.info("########################################")


def deleteOldRequestfromQueue(installGroup, queueWaitTimeMax):
    '''
    Deleting old request in Request Queue
    '''
    timeThreshold = datetime.now() - timedelta(hours = queueWaitTimeMax)
    ClusterQueue.objects.filter(dateInserted__lt=timeThreshold).delete()


def addAndCheckRequestQueue(installGroup, wait, totalIdle):
    '''
    Adding and Checking Request Queue for free Deployment
    '''
    insertTS = ClusterQueue(clusterGroup=installGroup,dateInserted=datetime.now())
    insertTS.save()
    longestWaiting = ClusterQueue.objects.only('id').values('id').filter(clusterGroup=installGroup).order_by('dateInserted')[0]
    if longestWaiting['id'] != insertTS.id:
        wait = "True"
        logger.info("Other Request Entry for Free Deployment ahead in the Queue")
    elif totalIdle == 0:
        wait = "True"
        logger.info("First Request Entry in Queue")
    else:
        wait == "False"

    return insertTS, wait

def checkRequestQueue(longestWaiting, wait, totalIdle, queueWaitTime):
    '''
    Checking Request Queue to see if needs to deleted or is first in the Queue
    '''
    message = ""

    logger.info("First Request Entry in Queue")
    if totalIdle == 0:
        if datetime.now() - timedelta(hours = queueWaitTime) > longestWaiting['dateInserted']:
            logger.info("Deleting Deployment Request Entry from Queue")
            ClusterQueue.objects.get(id=longestWaiting['id']).delete()
            message = "Error: Timeout of "+ str(queueWaitTime) +" hours has been reached, no free Deployments in install group"
    else:
        wait = "False"
    return message, wait

def overAllCheckRequestQueue(installGroup, insertTS, wait, totalIdle, queueWaitTime, recheckWait):
    '''
    The Overall Request Queue Check
    '''
    longestWaitingField = ('id', 'dateInserted',)
    longestWaiting = ClusterQueue.objects.only(longestWaitingField).values(*longestWaitingField).filter(clusterGroup=installGroup).order_by('dateInserted')[0]
    if longestWaiting['id'] == insertTS.id:
        message, wait = checkRequestQueue(longestWaiting, wait, totalIdle, queueWaitTime)
        if "Error" in message:
            return message
    else:
        while longestWaiting['id'] != insertTS.id:
            time.sleep(recheckWait)
            logger.info("Other Request Entry for Free Deployment ahead in the Queue")
            longestWaiting = ClusterQueue.objects.only(longestWaitingField).values(*longestWaitingField).filter(clusterGroup=installGroup).order_by('dateInserted')[0]
            logger.info("This Request Entry ID: " + str(insertTS.id) + ". The First Request Entry ID: " + str(longestWaiting['id']))
            if longestWaiting['id'] == insertTS.id:
                message, wait = checkRequestQueue(longestWaiting, wait, totalIdle, queueWaitTime)
                if "Error" in message:
                    return message
    return wait

def getInstallGroupStatusInfo(installGroup):
    '''
    Getting all informtion on the Install group for the free deployment
    '''
    idleField = ('id', 'cluster__id', 'cluster__name',)
    allIdle = ClusterToInstallGroupMapping.objects.only(idleField).values(*idleField).filter(group__installGroup=installGroup,status__status__status__in=['IDLE'])
    totalIdle = len(allIdle)
    failedField = ('id', 'status__status_changed', 'cluster__id', 'cluster__name',)
    allFailed = ClusterToInstallGroupMapping.objects.only(failedField).values(*failedField).filter(group__installGroup=installGroup,status__status__status__in=['FAILED']).order_by('status__status_changed')
    totalFailed = len(allFailed)
    allBusy = ClusterToInstallGroupMapping.objects.only('id').values('id').filter(group__installGroup=installGroup,status__status__status__in=['BUSY'])
    totalBusy = len(allBusy)
    allQuarantine = ClusterToInstallGroupMapping.objects.only('id').values('id').filter(group__installGroup=installGroup,status__status__status__in=['QUARANTINE'])
    totalQuarantine = len(allQuarantine)

    return allIdle, totalIdle, allFailed, totalFailed, allBusy, totalBusy, allQuarantine, totalQuarantine

def checkingFailedDeploymentStatus(failedDeploymentList, maxFailed):
    '''
    Checking and changing failed Deployment Status
    '''
    longestInFailed=failedDeploymentList[:1]
    for failed in longestInFailed:
        if datetime.now() - timedelta(hours = maxFailed) > failed['status__status_changed']:
            dmt.utils.setClusterStatus(failed['cluster__id'],"IDLE")
            logger.info("Changing "+str(failed['cluster__name']) + " status to IDLE")

def getEnvironment(clusterId):
    '''
    Function used to get the environment of the deployment i.e. cloud or physical
    '''
    if Cluster.objects.filter(id = clusterId).exists():
        cluster = Cluster.objects.get(id = clusterId)
    else:
        logger.error("Ensure that the cluster/deployment ID defined is registered on the portal")
        return "error"
    clusterName = cluster.name
    mgtServer = cluster.management_server
    environment = mgtServer.server.hardware_type
    if environment != "cloud":
        environment = "physical"
    return environment

def getIpmiVersion(drop):
    '''
    Function used to calculate the ipmi version according to the drop if one specified
    '''
    drop = drop.split("::")[0]
    ipmiVersionMappingObj = None
    if IpmiVersionMapping.objects.filter(reference=drop).exists():
        logger.info("Getting IPMI version from DB for drop specified")
        ipmiVersionMappingObj = IpmiVersionMapping.objects.get(reference=drop)
    elif IpmiVersionMapping.objects.filter(reference='master').exists():
        logger.info("Getting IPMI version from DB specified as master")
        ipmiVersionMappingObj = IpmiVersionMapping.objects.get(reference='master')
    if ipmiVersionMappingObj != None:
        ipmiVersion = ipmiVersionMappingObj.version
    else:
        ipmiVersion = None
    return ipmiVersion

def getRedfishVersion(drop):
    '''
    Function used to calculate the redfish version according to the drop if one specified
    '''
    drop = drop.split("::")[0]
    redfishVersionMappingObj = None
    if RedfishVersionMapping.objects.filter(reference=drop).exists():
        logger.info("Getting Redfish version from DB for drop specified")
        redfishVersionMappingObj = RedfishVersionMapping.objects.get(reference=drop)
    elif RedfishVersionMapping.objects.filter(reference='master').exists():
        logger.info("Getting Redfish version from DB specified as master")
        redfishVersionMappingObj = RedfishVersionMapping.objects.get(reference='master')
    if redfishVersionMappingObj != None:
        redfishVersion = redfishVersionMappingObj.version
    else:
        redfishVersion = None
    return redfishVersion

def getProductDropInfo(productSet,product):
    '''
    Function used to retrieve the deployment artifact information given product Set information
    '''
    otherUtilities = []
    drop = litpDrop = osVersion = osVersion8 = osRhel6PatchDrop = osRhel7PatchDrop = osRhel79PatchDrop = osRhel88PatchDrop = nasConfig = nasRhelPatch = sedVersion = deployScript = cdbName = mtUtilsVersion = version= None
    productSetVersionObj = None
    cifwkUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    baseUrl = "wget -q -O - --no-check-certificate "  +cifwkUrl
    if "::" in productSet:
        (productDrop,version,notRequired) = setDropIsoVersion(productSet)
    else:
        version = "LATEST"
        productDrop = productSet
    try:
        productSetObj = ProductSet.objects.get(name=str(product))
        productSetRelObj = ProductSetRelease.objects.filter(productSet=productSetObj)[0]
        dropObj = Drop.objects.get(name=str(productDrop), release__product=productSetRelObj.release.product)
        allVersions = ProductSetVersion.objects.filter(drop_id=dropObj.id,productSetRelease__release=dropObj.release).order_by('-id')
    except Exception as e:
        logger.error("Issue getting Product Set Versions " + str(e))
        return drop,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,nasConfig,nasRhelPatch,sedVersion,deployScript,mtUtilsVersion,otherUtilities,version

    if "GREEN" in version:
        if "::" in version:
            (exists, cdbName, notRequired) = setDropIsoVersion(version)
        found = False
        for item in allVersions:
            if "::" in version:
                statuses = cireports.utils.getProductSetCDBStatus(item)
                tryAgain = True
                for status in statuses:
                    cdbType = status["type"].upper()
                    if cdbName == cdbType:
                        if status['state'] == 'passed' or status['state'] == 'passed_manual':
                            version = str(item.version)
                            found = True
                            tryAgain = False
                            break
                if tryAgain:
                    continue
            if not found:
                if (item.getOverallWeigthedStatus() == 'passed' or item.status.state == 'passed_manual'):
                    version = str(item.version)
                    break
    elif "LATEST" in version:
        for item in allVersions:
            version = str(item.version)
            break
    logger.info("Using Product Set " + str(productDrop) + " version " + str(version))
    try:
        productSetObj = ProductSet.objects.get(name=product)
        prod = ProductSetRelease.objects.filter(productSet=productSetObj)[0].release.product
        dropObj = Drop.objects.get(name=productDrop, release__product=prod)
        productSetRelObj = ProductSetRelease.objects.get(productSet=productSetObj,release=dropObj.release)
        productSetVersionObj = ProductSetVersion.objects.get(version=version,productSetRelease=productSetRelObj)
        contentValues = ("mediaArtifactVersion__id", "mediaArtifactVersion__sed_build__version", "mediaArtifactVersion__mt_utils_version", "mediaArtifactVersion__deploy_script_version", "mediaArtifactVersion__mediaArtifact__id", "mediaArtifactVersion__drop__release__product__name", "mediaArtifactVersion__drop__name", "mediaArtifactVersion__version")
        contents = ProductSetVersionContent.objects.only(contentValues).values(*contentValues).filter(productSetVersion=productSetVersionObj, mediaArtifactVersion__mediaArtifact__category__name="productware")
        nasConfig, nasRhelPatch = dmt.utils.getNasConfigArtifacts(contents)
        inactive = ProductSetVersionContent.objects.filter(productSetVersion=productSetVersionObj, mediaArtifactVersion__active=0)
        if inactive:
            errMsg = "Error: There was an issue with the product set entered content, it contains a media artifact no longer available to download from Nexus"
            logger.error(errMsg)
            return errMsg,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,nasConfig,nasRhelPatch,sedVersion,deployScript,mtUtilsVersion,otherUtilities,version
    except Exception as e:
        logger.error("Error: There was an issue getting the info for the product Set entered " + str(e))
        return drop,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,nasConfig,nasRhelPatch,sedVersion,deployScript,mtUtilsVersion,otherUtilities,version
    if ProductSetVersionDeployMapping.objects.filter(productSetVersion=productSetVersionObj).exists():
        (drop,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,sedVersion,deployScript,mtUtilsVersion,otherUtilities) = getProductSetVersionDeployMapping(productSetVersionObj)
    else:
        (drop,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,sedVersion,deployScript,mtUtilsVersion,otherUtilities) = getContentInfoFromProductDrop(contents, productSetVersionObj)
    return drop,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,nasConfig,nasRhelPatch,sedVersion,deployScript,mtUtilsVersion,otherUtilities,version


def getProductSetVersionDeployMapping(productSetVersionObj):
    '''
    Getting ProductSet Version Deploy Mapping Data
    '''
    logger.info("###############################################################")
    logger.info("# Auto Deployment Mappings found for this Product Set Version #")
    logger.info("###############################################################")

    drop = litpDrop = osVersion = osVersion8 = osRhel6PatchDrop = osRhel7PatchDrop = osRhel79PatchDrop = osRhel88PatchDrop = sedVersion = deployScript = mtUtilsVersion = None
    otherUtilities = []
    deploymentUtils = None
    os79PatchName = config.get('DMT_AUTODEPLOY', 'osRhel79PatchProductName')
    os88PatchName = config.get('DMT_AUTODEPLOY', 'osRhel88PatchProductName')

    if DeploymentUtilsToProductSetVersion.objects.filter(productSetVersion=productSetVersionObj,active=True).exists():
        deploymentUtils = DeploymentUtilsToProductSetVersion.objects.filter(productSetVersion=productSetVersionObj,active=True)
        (sedVersion, deployScript, mtUtilsVersion, otherUtilities) = getDeploymentUtils(deploymentUtils)

    contentValues = ('mainMediaArtifactVersion__version', 'mainMediaArtifactVersion__drop__name', 'mainMediaArtifactVersion__drop__release__product__name', 'mediaArtifactVersion__mediaArtifact__id', 'mediaArtifactVersion__version', 'mediaArtifactVersion__mediaArtifact__deployType__type', 'mediaArtifactVersion__drop__name', 'mediaArtifactVersion__drop__release__product__name',)
    mappingsData = ProductSetVersionDeployMapping.objects.only(contentValues).values(*contentValues).filter(productSetVersion=productSetVersionObj).order_by('mediaArtifactVersion__mediaArtifact__id')
    drop = str(mappingsData[0]['mainMediaArtifactVersion__drop__name']) + "::" + str(mappingsData[0]['mainMediaArtifactVersion__version']) + "::" + str(mappingsData[0]['mainMediaArtifactVersion__drop__release__product__name'])
    for item in mappingsData:
        dropNameAndVersion = str(item['mediaArtifactVersion__drop__name']) + "::" + str(item['mediaArtifactVersion__version']) + "::" + str(item['mediaArtifactVersion__drop__release__product__name'])
        if str(item['mediaArtifactVersion__mediaArtifact__deployType__type']) == "it_platform":
            litpDrop = dropNameAndVersion
            continue
        elif str(item['mediaArtifactVersion__mediaArtifact__deployType__type']) == "os":
            if redHatArtifactToVersionMapping.objects.filter(mediaArtifact__id=item['mediaArtifactVersion__mediaArtifact__id']).exists():
                imageReferenceObj=redHatArtifactToVersionMapping.objects.get(mediaArtifact=item['mediaArtifactVersion__mediaArtifact__id'])
                if str(item['mediaArtifactVersion__drop__release__product__name']) == "RHEL-88-MEDIA":
                    osVersion8 = imageReferenceObj.artifactReference + "::" + dropNameAndVersion
                else:
                    osVersion = imageReferenceObj.artifactReference + "::" + dropNameAndVersion
            continue
        elif str(item['mediaArtifactVersion__mediaArtifact__deployType__type']) == "patches":
            if identifyPatches(str(item['mediaArtifactVersion__drop__release__product__name'])) == 6:
                osRhel6PatchDrop = dropNameAndVersion
            elif identifyPatches(str(item['mediaArtifactVersion__drop__release__product__name'])) == 7:
                osRhel7PatchDrop = dropNameAndVersion
            elif str(item['mediaArtifactVersion__drop__release__product__name']) == os79PatchName:
                osRhel79PatchDrop = dropNameAndVersion
            elif str(item['mediaArtifactVersion__drop__release__product__name']) == os88PatchName:
                osRhel88PatchDrop = dropNameAndVersion
            continue
    return drop,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,sedVersion,deployScript,mtUtilsVersion,otherUtilities


def getEnmInstInfo(enmMedia, version):
    '''
    Getting the version of enmInst from ENM Media Artifact Version
    '''
    enmMediaName,junk = enmMedia.split('-', 1)
    enmInstArifactId = config.get('DMT_AUTODEPLOY','enmInstPackage')
    enmInstVersion = None
    try:
        mediaArt = ISObuildMapping.objects.only('package_revision__version').values('package_revision__version').get(iso__artifactId=enmMediaName, iso__version=version, package_revision__artifactId=enmInstArifactId)
        enmInstVersion = mediaArt['package_revision__version']
    except Exception as e:
        logger.error("Error: There was an issue getting the version for " + str(enmInstArifactId) + ", " + str(e))
    return enmInstVersion

def getEnmInstVersionByENMmedia(dropVersion, product):
    '''
    Getting the the version of enmInst from ENM Media Artifact Version
    '''
    ( drop, isoVersion, notRequired) = setDropIsoVersion(dropVersion)
    ( isoName, isoVersion, isoUrl, hubIsoUrl, message ) = getIsoName(drop,isoVersion,product)
    enmInstVersion = getEnmInstInfo(isoName, isoVersion)
    return enmInstVersion

def getDeploymentUtils(deploymentUtils):
    '''
    Getting values from deploymentUtils items
    '''
    otherUtilities = []
    sedVersion = None
    deployScript = None
    mtUtilsVersion = None
    for utility in deploymentUtils:
        utilityName = str(utility.utility_version.utility_name.utility)
        utilityVersion = str(utility.utility_version.utility_version)
        if utilityName == "sedVersion":
            sedVersion = utilityVersion
        elif utilityName == "deployScript":
            deployScript = utilityVersion
        elif utilityName == "mtUtilsVersion":
            mtUtilsVersion = utilityVersion
        else:
            otherUtilities.append(utilityName + "::" + utilityVersion)
    return sedVersion, deployScript, mtUtilsVersion, otherUtilities

def getContentInfoFromProductDrop(contents, productSetVersionObj=None):
    '''
    Return the info on the different media in the correct structure to be used within the auto deployment
    '''
    drop = litpDrop = osVersion =osVersion8 = osRhel6PatchDrop = osRhel7PatchDrop = osRhel79PatchDrop = osRhel88PatchDrop = sedVersion = deployScript = mtUtilsVersion = None
    otherUtilities = []
    deploymentUtils = None
    enmInstVersion = None

    enmProductSet = config.get('DMT_AUTODEPLOY','enmProductName')
    litpProductSet = config.get('DMT_AUTODEPLOY','litpProductName')
    rhelMediaProductSet = config.get('DMT_AUTODEPLOY','rhelMediaProductName')
    enmInstRHELPatchISO = config.get('DMT_AUTODEPLOY','enmInstRHELPatchISO')
    rhel6OsPatchSetProductSet = config.get('DMT_AUTODEPLOY','osRhel6PatchProductName')
    rhel7OsPatchSetProductSet = config.get('DMT_AUTODEPLOY','osRhel7PatchProductName')
    rhel79PatchSetProductSet = config.get('DMT_AUTODEPLOY','osRhel79PatchProductName')
    rhel88PatchSetProductSet = config.get('DMT_AUTODEPLOY','osRhel88PatchProductName')

    if productSetVersionObj:
        if DeploymentUtilsToProductSetVersion.objects.filter(productSetVersion=productSetVersionObj,active=True).exists():
            deploymentUtils = DeploymentUtilsToProductSetVersion.objects.filter(productSetVersion=productSetVersionObj,active=True)
            (sedVersion, deployScript, mtUtilsVersion, otherUtilities) = getDeploymentUtils(deploymentUtils)

    for item in contents:
        mediaArtifactId = item['mediaArtifactVersion__mediaArtifact__id']
        product = str(item['mediaArtifactVersion__drop__release__product__name'])
        dropNameAndVersion = str(item['mediaArtifactVersion__drop__name']) + "::" + str(item['mediaArtifactVersion__version']) + "::" + str(item['mediaArtifactVersion__drop__release__product__name'])
        if enmProductSet == product:
            if not deploymentUtils:
                deploymentUtils= DeploymentUtilsToISOBuild.objects.filter(iso_build__id=item['mediaArtifactVersion__id'],active=True)
                if deploymentUtils:
                    (sedVersion, deployScript, mtUtilsVersion, otherUtilities) = getDeploymentUtils(deploymentUtils)
                else:
                    if item['mediaArtifactVersion__sed_build__version']:
                        sedVersion = item['mediaArtifactVersion__sed_build__version']
                    if item['mediaArtifactVersion__deploy_script_version']:
                        deployScript = item['mediaArtifactVersion__deploy_script_version']
                    if item['mediaArtifactVersion__mt_utils_version']:
                        mtUtilsVersion = item['mediaArtifactVersion__mt_utils_version']
            drop = dropNameAndVersion
            enmInstVersion = getEnmInstVersionByENMmedia(drop, product)
        elif litpProductSet == product:
            litpDrop = dropNameAndVersion
        elif rhelMediaProductSet == product:
            if redHatArtifactToVersionMapping.objects.filter(mediaArtifact=mediaArtifactId).exists():
                imageReferenceObj=redHatArtifactToVersionMapping.objects.get(mediaArtifact=mediaArtifactId)
                if str(item['mediaArtifactVersion__drop__release__product__name']) == "RHEL-88-MEDIA":
                    osVersion8 = imageReferenceObj.artifactReference
                else:
                    osVersion = imageReferenceObj.artifactReference
        elif rhel6OsPatchSetProductSet == product:
            osRhel6PatchDrop = dropNameAndVersion
        elif rhel7OsPatchSetProductSet == product:
            osRhel7PatchDrop = dropNameAndVersion
        elif rhel79PatchSetProductSet == product:
            osRhel79PatchDrop = dropNameAndVersion
        elif rhel88PatchSetProductSet == product:
            osRhel88PatchDrop = dropNameAndVersion

    if enmInstVersion and (LooseVersion(enmInstRHELPatchISO) <= LooseVersion(enmInstVersion)):
        logger.info("###############################################################################")
        logger.info("# Based on ENMInst Version: %s , getting RHEL OS Patch Sets media type iso", str(enmInstVersion))
        logger.info("###############################################################################")
        rhel6OsPatchSetProductSet = config.get('DMT_AUTODEPLOY','osPatchISOProductName')
        rhel7OsPatchSetProductSet = config.get('DMT_AUTODEPLOY','osRhel7PatchISOProductName')
        for item in contents:
            product = str(item['mediaArtifactVersion__drop__release__product__name'])
            dropNameAndVersion = str(item['mediaArtifactVersion__drop__name']) + "::" + str(item['mediaArtifactVersion__version']) + "::" + str(item['mediaArtifactVersion__drop__release__product__name'])
            if rhel6OsPatchSetProductSet == product:
                osRhel6PatchDrop = dropNameAndVersion
            elif rhel7OsPatchSetProductSet == product:
                osRhel7PatchDrop = dropNameAndVersion
    return drop,litpDrop,osVersion,osVersion8,osRhel6PatchDrop,osRhel7PatchDrop,osRhel79PatchDrop,osRhel88PatchDrop,sedVersion,deployScript,mtUtilsVersion,otherUtilities

def deployModelScriptsToMgtServer(remoteConnection, mgtServer, lmsUploadDir, tmpArea, product):
    modelScriptNexusRepo = config.get('DMT_AUTODEPLOY', 'modelScriptNexusRepo')
    deployModelScriptVersion = config.get('DMT_AUTODEPLOY', 'model_script_version')
    modelScriptsRpm = config.get('DMT_AUTODEPLOY', 'modelScriptsRpm')
    modelScriptFile = modelScriptsRpm + "-" + deployModelScriptVersion + ".rpm"
    url = config.get('DMT_AUTODEPLOY', str(product) + '_nexus_url') + modelScriptNexusRepo + modelScriptsRpm + "/" + deployModelScriptVersion + "/" + modelScriptFile
    testurl = config.get('DMT_AUTODEPLOY', 'ENM_nexus_url')
    try:
        resp = urllib2.urlopen(testurl, timeout=10)
    except urllib2.URLError:
        logger.info("Nexus Proxy server not responding " + testurl + "Moving to download from Hub Nexus")
        url = config.get('DMT_AUTODEPLOY', 'nexus_url') + modelScriptNexusRepo + deployModelScriptVersion + "/" + modelScriptFile
    logger.info("Downloading Model Scripts from nexus: " + url)
    ret = fwk.utils.downloadFile(url, tmpArea)
    if (ret != 0):
        return ret

    target = config.get('DMT_AUTODEPLOY', 'modelScriptsDirectory')

    # Upload the scripts to MS
    logger.info("Uploading Model scripts to management server")
    ret = dmt.utils.paramikoSftp(
            mgtServer.server.hostname + "." + mgtServer.server.domain_name,
            "root",
            lmsUploadDir+ "/" + modelScriptFile,
            tmpArea + "/" + modelScriptFile,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "put")
    if (ret != 0):
        return ret
    logger.info("Removing any old Model Scripts")
    remoteConnection.runCmd("rm -rf " + target)
    remoteConnection.runCmd("mkdir -p " + target)
    logger.info("Extracting new Model Scripts")
    ret, errMsg = remoteConnection.runCmdGetOutput("cd " + target + ";rpm2cpio " + lmsUploadDir + "/" + modelScriptFile + " | cpio -idmv")
    if (ret != 0):
        logger.info("ERROR MESSAGE: "+errMsg)
        return ret
    return 0

def deployScriptsToMgtServer(remoteConnection, mgtServer, deployScriptVersion, deployRelease, lmsUploadDir, tmpArea,product,scriptFile):
    if deployRelease != "None":
        url = config.get('DMT_AUTODEPLOY', str(product) + '_nexus_url') + "/com/ericsson/tor/DeploymentScripts/" + deployScriptVersion + "/" + scriptFile
        testurl = config.get('DMT_AUTODEPLOY', 'ENM_nexus_url')
        try:
            resp = urllib2.urlopen(testurl, timeout=10)
        except urllib2.URLError:
            logger.info("Nexus Proxy server not responding " + testurl + "Moving to download from Hub Nexus")
            url = config.get('DMT_AUTODEPLOY', 'nexus_url') + "/releases/com/ericsson/tor/DeploymentScripts/" + deployScriptVersion + "/" + scriptFile

    else:
        url = config.get('DMT_AUTODEPLOY', str(product) + '_nexus_url') + "/com/ericsson/tor/DeploymentScripts_" + deployRelease + "/" + deployScriptVersion + "/" + scriptFile
        testurl = config.get('DMT_AUTODEPLOY', 'ENM_nexus_url')
        try:
            resp = urllib2.urlopen(testurl, timeout=10)
        except urllib2.URLError:
            logger.info("Nexus Proxy server not responding " + testurl + "Moving to download from Hub Nexus")
            url = config.get('DMT_AUTODEPLOY', 'nexus_url') + "/releases/com/ericsson/tor/DeploymentScripts_" + deployRelease + "/" + deployScriptVersion + "/" + scriptFile
    logger.info("Downloading RV Scripts from nexus: " + url)
    ret = fwk.utils.downloadFile(url, tmpArea)
    if (ret != 0):
        return ret

    target = lmsUploadDir + "/deploy"

    # Upload the scripts to /var/tmp
    logger.info("Uploading RV scripts to management server")
    ret = dmt.utils.paramikoSftp(
            mgtServer.server.hostname + "." + mgtServer.server.domain_name,
            "root",
            lmsUploadDir + "/" + scriptFile,
            tmpArea + "/" + scriptFile,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "put")
    if (ret != 0):
        return ret
    if os.path.exists(tmpArea + "/" + scriptFile):
        # Extract the deployment tar file so it can be used at a later stage to stop the peer nodes
        cmd = "gtar -xf " + tmpArea + "/" + scriptFile + " -C " + tmpArea
        logger.info("Running Command " + str(cmd))
        ret = subprocess.call(cmd, shell=True)
        if (ret != 0):
            return ret
    logger.info("Removing any old RV Scripts")
    remoteConnection.runCmd("rm -rf " + target)
    remoteConnection.runCmd("mkdir -p " + target)
    logger.info("Extracting new RV Scripts")
    ret = remoteConnection.runCmd("tar --directory=" + target + " -xzvf " + lmsUploadDir + "/" + scriptFile)
    if (ret != 0):
       return ret
    return 0

def cslConfigsToMgtServer(remoteConnection, mgtServer, lmsUploadDir, tmpArea, targetCfgDir, siteEngineeringFilesVersion):
    """
    This function downloads a collection of hardcoded site engineering files, one of which will be used during the csl install
    This is an interrim solution until these site engineering files can be generated from the database on the fly
    """
    # Define the filename in nexus containing the files and the full nexus url to download them from
    configsFileName = "siteEngineeringFiles-" + siteEngineeringFilesVersion + ".gz"
    try:
        configsFileNexusUrl = config.get('CIFWK', 'CSL-Mediation_nexus_url') + config.get('DMT_AUTODEPLOY', 'cslSiteEngineeringFiles') + siteEngineeringFilesVersion  + "/" + configsFileName
    except Exception as e:
        logger.error ("There was an exception creating the url to the CSL Site Engineering Files in Nexus: " + str(e))
        return 1

    # Download the files locally first
    logger.info("Downloading csl config files from nexus: " + configsFileNexusUrl)
    ret = fwk.utils.downloadFile(configsFileNexusUrl, tmpArea)
    if (ret != 0):
        return ret

    # Upload the files to the ms
    logger.info("Uploading csl config files to management server")
    ret = dmt.utils.paramikoSftp(
            mgtServer.server.hostname + "." + mgtServer.server.domain_name,
            "root",
            lmsUploadDir + "/" + configsFileName,
            tmpArea + "/" + configsFileName,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "put")
    if (ret != 0):
        return ret
    if os.path.exists(tmpArea + "/" + configsFileName):
        os.remove(tmpArea + "/" + configsFileName)

    # Cleanup any previously extracted directories
    logger.info("Removing any old csl config files")
    remoteConnection.runCmd("rm -rf " + targetCfgDir)
    remoteConnection.runCmd("mkdir -p " + targetCfgDir)

    # Extract the configs to the target directory
    logger.info("Extracting new csl configs")
    ret = remoteConnection.runCmd("tar --directory=" + targetCfgDir + " -xzvf " + lmsUploadDir + "/" + configsFileName)
    if (ret != 0):
       return ret
    return 0

def getIsoName(drop,isoVersion,product):
    # function used to get the ISO name
    errorMsg = ""
    isoName = isoUrl = hubIsoUrl = None
    try:
        fields = ("id","name","release__product","release__iso_artifact","release__masterArtifact__mediaType")
        dropObj = Drop.objects.only(fields).values(*fields).get(name=drop,release__product__name=product)
    except:
        errorMsg = "Error finding Drop entered: '" + str(drop) + "' in database, please try again."
        logger.error(errorMsg)
        return 1,1,1,1,errorMsg
    try:
        requiredIsoFields= 'id','overall_status__state','version','mediaArtifact__name','build_date', 'mediaArtifact__mediaType'
        isoObjs = list(ISObuild.objects.filter(drop__id=dropObj['id'],mediaArtifact__testware=0, mediaArtifact__category__name="productware", active=1).only(requiredIsoFields).values(*requiredIsoFields).order_by('-build_date'))
        if isoVersion == "LATEST":
            iso = isoObjs[0]
        elif "GREEN" in isoVersion:
            if "::" in isoVersion:
                (dntNeed,cdbName,notRequired) = setDropIsoVersion(isoVersion)
                breakLoop = False
                for iso in isoObjs:
                    statuses = ISObuild.objects.get(id=iso['id']).getCurrentCDBStatuses()
                    for status in statuses:
                        cdbType = status["cdb_type_name"].upper()
                        if cdbName == cdbType:
                            if status['status'] == 'passed' or status['status'] == 'passed_manual':
                                breakLoop = True
                                break
                    if breakLoop:
                        break
                if not breakLoop:
                    errorMsg = "Unable to find a Passed iso for "+cdbName + " in " + str(drop)
                    logger.error(errorMsg)
                    return 1,1,1,1,errorMsg
            else:
                for iso in isoObjs:
                    if ISObuild.objects.get(id=iso['id']).getOverallWeigthedStatus() == 'passed' or iso['overall_status__state'] == 'passed_manual':
                        break
                    elif isoObjs.index(iso)+1 == len(isoObjs):
                        errorMsg = "Unable to find a Passed iso version for drop " + str(drop)
                        logger.error(errorMsg)
                        return 1,1,1,1,errorMsg
        else:
            iso = ISObuild.objects.filter(drop__id=dropObj['id'],version=isoVersion,mediaArtifact__testware=0, mediaArtifact__category__name="productware", active=1).only(requiredIsoFields).values(*requiredIsoFields).order_by('-build_date')[0]
        isoName = str(iso['mediaArtifact__name']) + "-" + iso['version'] + "." + iso['mediaArtifact__mediaType']
        isoVersion = str(iso['version'])
        isoUrl = str(ISObuild.objects.get(id=iso['id']).getHubIsoDeployUrl(product)) + "/" + str(iso['mediaArtifact__name']) + "/" + isoVersion  + "/" + isoName
        hubIsoUrl = str(ISObuild.objects.get(id=iso['id']).getHubIsoDeployBackupUrl(product)) + "/" + str(iso['mediaArtifact__name']) + "/" + isoVersion  + "/" + isoName
    except Exception as error:
        errorMsg = "Issue retrieving iso information for drop " + str(drop) + " with iso version " + str(isoVersion) + ", version could be deleted from Nexus: " +str(error)
        logger.error(errorMsg)
        return 1,1,1,1,errorMsg
    return isoName, isoVersion, isoUrl, hubIsoUrl,errorMsg

def downloadIsoToMgtServer(remoteConnection, mgtServer, isoName, lmsUploadDir,tmpArea,isoUrl):
    '''
    Function used by the legacy CMW due to issues with the firewalls
    '''
    logger.info("Checking if the ISO is already present")
    if (remoteConnection.runCmd("ls " + lmsUploadDir + "/" + isoName) != 0):
        url = isoUrl
        logger.info("Retrieving ISO from Nexus: " + url)
        ret = fwk.utils.downloadFile(url, tmpArea)
        if (ret != 0):
            return 1
        logger.info("Uploading ISO to management server")
        ret = dmt.utils.paramikoSftp(
                mgtServer.server.hostname + "." + mgtServer.server.domain_name,
                "root",
                lmsUploadDir + "/" + isoName,
                tmpArea + "/" + isoName,
                int(config.get('DMT_AUTODEPLOY', 'port')),
                config.get('DMT_AUTODEPLOY', 'key'),
                "put")
        if (ret != 0):
            remoteConnection.close()
            return ret
    if os.path.exists(tmpArea + "/" + isoName):
        os.remove(tmpArea + "/" + isoName)
    return 0

def downloadToMgtServer(remoteConnection, mgtServer, isoName, lmsUploadDir,tmpArea,isoUrl, hubIsoUrl):
    '''
    function used to download the iso directly to the MS
    '''
    softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    if "/var/tmp" in lmsUploadDir:
        if (remoteConnection.runCmd("ls " + softwareDir + "/" + isoName) == 0):
            ret = remoteConnection.runCmd("mv " + softwareDir + "/" + isoName + " " + lmsUploadDir + "/" + isoName)
            if (ret != 0):
                logger.error("Issue with the moving of the " + isoName + " from " + softwareDir + " to " + lmsUploadDir + " please ensure there is enough space available.")
                return ret
    logger.info("Checking if the artifact is already present")
    if (remoteConnection.runCmd("ls " + lmsUploadDir + "/" + isoName) != 0):
        url = isoUrl
        try:
            testurl = isoUrl.rsplit('/',1)[0]
            logger.info('Testing Nexus Proxy Server ' + testurl)
            resp = urllib2.urlopen(testurl, timeout=10)
        except (urllib2.URLError, urllib2.HTTPError) as e:
            logger.info("Nexus Proxy server not responding to " + str(isoName) + ", Moving to download from Hub Nexus")
            url = hubIsoUrl
        logger.info("Retrieving ISO from Nexus and Upload to Management Server: " + url)
        cmd = "if [ ! -d " + lmsUploadDir + " ]; then mkdir -p " + lmsUploadDir + "; fi; cd " + lmsUploadDir + " ;curl -f -O " + url
        ret = remoteConnection.runCmdSimple(cmd)
        if (ret != 0):
            remoteConnection.close()
            return ret
    if os.path.exists(tmpArea + "/" + isoName):
        os.remove(tmpArea + "/" + isoName)
    return 0

def checkIsoMd5Sum(remoteConnection,mgtServer,isoName,lmsUploadDir,tmpArea,isoUrl,hubIsoUrl):
    '''
    function used to check md5 checkSums
    '''
    logger.info("Checking if Md5 matches on Iso and .md5 file")
    try:
        if (remoteConnection.runCmd("ls " + lmsUploadDir + "/" + isoName) == 0):
            try:
                testurl = isoUrl.rsplit('/',1)[0]
                logger.info('Testing Nexus Proxy Server ' + testurl)
                resp = urllib2.urlopen(testurl, timeout=60)
            except (urllib2.URLError, urllib2.HTTPError) as e:
                logger.info("Nexus Proxy server not responding to " + str(isoName) + ", Moving to download from Hub Nexus")
                isoUrl = hubIsoUrl
            md5File = isoUrl + ".md5"
            logger.info("Checking md5 of artifact with md5 file: " + str(md5File))
            cmd = "cd " + lmsUploadDir + " ;curl -O " + md5File
            ret = remoteConnection.runCmd(cmd)
            if (ret != 0):
                remoteConnection.close()
                return ret
            cmd = "cd " + lmsUploadDir +";cat " + isoName + ".md5"
            ret,output = remoteConnection.runCmdGetOutput(cmd)
            if (ret != 0):
                remoteConnection.close()
                return ret
            output = output + "  " + isoName
            parseLength = len(isoName) + 34 ;
            output = output[-parseLength:]
            cmd = "cd " + lmsUploadDir + ";/usr/bin/md5sum " + isoName
            ret, output2 = remoteConnection.runCmdGetOutput(cmd)
            if (ret != 0):
                remoteConnection.close()
                return ret
            output2 = output2.rstrip()[-parseLength:]
            if(output == output2):
                logger.info("The artifact md5 value matches the .md5 file so not corrupted")
            else:
                logger.error("This ISO md5 value do not match, please investigate")
                return 1
        if os.path.exists(tmpArea + "/" + isoName):
            os.remove(tmpArea + "/" + isoName)
        return 0
    except Exception as e:
        logger.error("Exception occured in checkIsoMd5Sum: " + str(e))
        return 1

def mountIsoToMgtServer(remoteConnection, mgtServer, isoName, lmsUploadDir,productSpecified=None):
    if (productSpecified == None):
        mediaArea = "/media"
    else:
        mediaArea = "/media/" + str(productSpecified)
    logger.info("Mounting ISO on " + str(mediaArea))
    remoteConnection.runCmd("umount " + str(mediaArea))
    # ENM mounts in /media and if the previous install failed within enminst this media is left mounted
    if (productSpecified != None):
        remoteConnection.runCmd("umount /media")
    remoteConnection.runCmd("mkdir -p " + str(mediaArea))
    ret = remoteConnection.runCmd("mount -o loop " + lmsUploadDir + "/" + isoName + " " + str(mediaArea))
    return 0

def unmountIso(remoteConnection,mgtServer,productSpecified):
    logger.info("Unmounting ISO off /media/" + productSpecified)
    remoteConnection.runCmd("umount /media/" + productSpecified)
    # Log message to check if the iso has successfully unmounted
    getMountStatusCommands = ['mount', 'df -hm /software', 'du -sch /software', 'cd /software && losetup -a']
    dfFeeSpaceGB = None
    duFreeSpaceGB = None
    try:
        for cmd in getMountStatusCommands:
            ret,output = remoteConnection.runCmdGetOutput(cmd)
            logger.info(str(output))
            if "df" in cmd:
                for row in output.split('\n'):
                    if "/software" in row:
                        freeSpace = [ele for ele in row.split('\t')[0].strip().split(' ') if ele is not ''][1]
                        dfFeeSpaceGB = float(math.ceil(int(freeSpace) / 1028))
                        logger.info(dfFeeSpaceGB)
            elif "du" in cmd:
                for row in output.split('\n'):
                    if '/software' in row:
                        value = row.split('\t')[0].strip().replace('G', '')
                        duFreeSpaceGB = float(value)
                        logger.info(duFreeSpaceGB)

            if dfFeeSpaceGB != None and duFreeSpaceGB != None:
                diff = abs(dfFeeSpaceGB - duFreeSpaceGB)
                logger.info('Difference in dfFreeSpaceGB and duFreeSpaceGB is  : ' + str(diff))
                if diff < 8.0 :
                    logger.info('No issue with ENM ISO umount')
                    break
                else:
                    logger.info('Issue with ENM ISO umount')
                    delLoop0DevCmd = 'cd /software && losetup -d /dev/loop0'
                    if delLoop0DevCmd not in getMountStatusCommands and cmd is not delLoop0DevCmd:
                        logger.info('Adding ' + str(delLoop0DevCmd) + '  to list of commands')
                        getMountStatusCommands.append(delLoop0DevCmd)
    except Exception as e:
        logger.error('Exception occurred while unmounting ISO. Error message: ' + str(e))
    return 0

def removeLocalCslIsoContentsDir(remoteConnection, cslIsoContentsDir):
    """
    This function removes any previous contents in the directory containing the copy of the iso contents
    """
    logger.info("Removing old contents of " + cslIsoContentsDir)
    ret = remoteConnection.runCmd("rm -rf " + cslIsoContentsDir)
    return ret

def populateLocalCslIsoContentsDir(remoteConnection, localCslIsoContentsSubDir):
    """
    This function copies the contents of the csl iso, to a local directory on the ms
    """
    logger.info("Copying contents of the mounted iso to " + localCslIsoContentsSubDir)
    remoteConnection.runCmd("mkdir -p " + localCslIsoContentsSubDir)
    ret = remoteConnection.runCmd("cp -r /media/* " + localCslIsoContentsSubDir)
    return ret

def cleanOutOldEnmIso(remoteConnection, mgtServer, isoName, uploadDir):
    '''
    Function to remove the ENM iso when running a KGB job as the ISO has been recreated
    '''
    logger.info("Removing ENM ISO " + str(isoName) + " as new ISO recreated with new package content. Needs to be removed to save space within uploaded directory")
    ret = remoteConnection.runCmd("rm " + uploadDir + "/" + isoName)
    if (ret != 0):
        logger.error("There was an issue removing the unwanted ENM ISO " + str(isoName))
        return ret
    return ret

def cleanOutIsoContentTmpArea(remoteConnection,mgtServer,isoRebuildlocation):
    logger.info("Clean out tmp Area " + isoRebuildlocation)
    ret = remoteConnection.runCmd("( rm -rf " + isoRebuildlocation + " && mkdir " + isoRebuildlocation + " )")
    if (ret != 0):
        logger.error("There was an issue cleaning up the temp location " + isoRebuildlocation)
        return ret
    return ret

def copyContent(remoteConnection,source,destination):
    '''
    Default function used to copy a source file to the destination
    '''
    logger.info("Copying " + str(source) + " to " + str(destination))
    ret = remoteConnection.runCmd("cp -r " + str(source) + " " + str(destination))
    return ret

def copyIsoContentToTmpArea(remoteConnection,mgtServer,isoRebuildlocation,mountMediaLocation,mediaName,product):
    date = datetime.now()
    date = date.strftime("%Y%m%d%H%M%S")
    logger.info("Copying content from mount iso location /media/" + str(product) + " to " + isoRebuildlocation)
    ret = remoteConnection.runCmd("( rm -rf " + isoRebuildlocation + " && mkdir " + isoRebuildlocation + " )")
    if (ret != 0):
        logger.error("There was an issue cleaning up the temp location " + isoRebuildlocation)
        return ret,mediaName
    ret = remoteConnection.runCmd("(cd /media/" + str(product) + " && tar cfp - .) | (cd " + isoRebuildlocation + " && tar xfpv -)")
    if (ret != 0):
        logger.error("There was an issue copy the mount iso in " + mountMediaLocation + " into the temp location " + isoRebuildlocation)
        return ret,mediaName
    ret = checkIfProductTorExists(remoteConnection,isoRebuildlocation)
    if ret == "yes":
        # Move the repo to a new unique name
        ret = remoteConnection.runCmd("mv " + isoRebuildlocation + "/products/TOR/" + mediaName + " " + isoRebuildlocation + "/products/TOR/" + mediaName + "_" + date)
        if (ret != 0):
            logger.error("There was an issue renaming the Repo to: " + isoRebuildlocation + "/products/"+ str(product) + "/" + mediaName + "_" + date)
        return ret,mediaName + "_" + date
    elif ret == "no":
        return 0,mediaName
    else:
        logger.error("There was an issue renaming the Repo")
        return 1,mediaName + "_" + date

def buildNewIso(remoteConnection, mgtServer, lmsUploadDir,reCreatedIsoName,isoRebuildlocation):
    logger.info("Recreating the iso")
    # return code seems to be random from the commands below even do the command succeeds
    ret = remoteConnection.runCmd("mkisofs -R -J -o " + lmsUploadDir + "/" + reCreatedIsoName + " " + isoRebuildlocation)
    return 0

def installCslMedInstRpm(remoteConnection):
    """
    This function installs the ERICcslmedinst rpm as per documentation using yum install
    It then umounts the mounted iso file
    """
    logger.info("Yum installing the ERICcslmedinst rpm")
    cmd = "yum remove -y ERICcslmedinst_*;yum install -y /media/products/CSL-Mediation/ERICcslmedinst_*.rpm"
    ret = remoteConnection.runCmdSimple(cmd)
    if (ret != 0):
        logger.error("There was an issue yum installing the ERICcslmedinst rpm, please investigate")
        return ret
    logger.info("Unmounting ISO from /media")
    remoteConnection.runCmd("umount /media")
    return 0

def lastIsoImportedIndicator(remoteConnection, mgtServer, lmsUploadDir, mediaArtifactList, lastIsoImported):
    logger.info("Creating file " + lmsUploadDir + "/" + lastIsoImported + " to indicate to the upgrade which version of the media to use for upgrade")
    remoteConnection.runCmd("touch " + lmsUploadDir + "/" + lastIsoImported)
    for media in mediaArtifactList:
        if 'autoDeploy' in media or 'DoNotDelete' in media:
            continue
        remoteConnection.runCmd("echo " + media + " >> " + lmsUploadDir + "/" + lastIsoImported)
    return 0

def uploadServicePatches(remoteConnection, mgtServer, servicePatchVersion, lmsUploadDir,tmpArea):
    # get the Service Patch file given
    logger.info("Checking if the Service Patches LITPServicePack-" + servicePatchVersion + ".tar.gz is already present")
    if (remoteConnection.runCmd("ls " + lmsUploadDir + "/LITPServicePack-" + servicePatchVersion + ".tar.gz") != 0):
        url = config.get('CIFWK', 'local_nexus_url') + "/iso/com/ericsson/nms/litp/LITPServicePack/" + servicePatchVersion + "/LITPServicePack-" + servicePatchVersion + ".tar.gz"
        logger.info("Retrieving OS Patch Tar from Nexus: " + url)
        ret = fwk.utils.downloadFile(url, tmpArea)
        if (ret != 0):
            return ret
        logger.info("Uploading Service Patches Tar to management server")
        ret = dmt.utils.paramikoSftp(
                mgtServer.server.hostname + "." + mgtServer.server.domain_name,
                "root",
                lmsUploadDir + "/LITPServicePack-" + servicePatchVersion + ".tar.gz",
                tmpArea + "/LITPServicePack-" + servicePatchVersion + ".tar.gz",
                int(config.get('DMT_AUTODEPLOY', 'port')),
                config.get('DMT_AUTODEPLOY', 'key'),
                "put")
        if (ret != 0):
            return ret
    if os.path.exists(tmpArea + "/LITPServicePack-" + servicePatchVersion + ".tar.gz"):
        os.remove(tmpArea + "/LITPServicePack-" + servicePatchVersion + ".tar.gz")
    return 0

def downloadFileFromUrl(url,mgtServer,lmsUploadDir,tmpArea):
    '''
    Function used to download a specified file with a url and upload to /var/tmp/ on the MS
    '''
    cfgName = url.split('/')[-1]
    ret = fwk.utils.downloadFile(url,tmpArea)
    if (ret != 0):
        return ret
    logger.info("Uploading file: " + str(cfgName))
    ret = dmt.utils.paramikoSftp(
            mgtServer.server.hostname + "." + mgtServer.server.domain_name,
            "root",
            lmsUploadDir + "/" + cfgName,
            tmpArea + "/" + cfgName,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "put")
    if (ret != 0):
        return ret
    logger.info("Copied " + cfgName + " to node")
    if os.path.exists(tmpArea + "/" + cfgName):
        os.remove(tmpArea + "/" + cfgName)
    return lmsUploadDir + "/" + cfgName

def generateConfig(cluster, mgtServer, cfgTemplate, drop, isoName, osRhel6PatchDrop, osRhel7PatchDrop, osRhel79PatchDrop, osRhel88PatchDrop, servicePatchVersion, lmsUploadDir, installType, reCreatedIsoName, deployProduct, tmpArea, osRhel6PatchFileName, osRhel7PatchFileName, osRhel79PatchFileName, osRhel88PatchFileName, skipPatchInstall, litpisopath, enmInstRHEL7Patch, enmInstRHEL79Patch, enmInstRHEL88Patch, enmInstVersion):
    '''
    Function used to generate the SED file, add extra data.
    Output: SED cfg filename.
    '''
    logger.info("Generating config file")
    if cfgTemplate == "MASTER":
        if deployProduct == "LITP2":
            sedVersion = dmt.utils.getVirtualMasterSedVersion()
        else:
            sedVersion = dmt.utils.getMasterSedVersion()
        cfgName = "MASTER_siteEngineering.txt"
    elif "http" in cfgTemplate:
        cfgName = cfgTemplate.split('/')[-1]
        ret = fwk.utils.downloadFile(cfgTemplate,tmpArea)
        if (ret != 0):
            return ret
    else:
        sedVersion = cfgTemplate
        cfgName = sedVersion + "_siteEngineering.txt"
    if not "http" in cfgTemplate:
        sed = dmt.buildconfig.generateDBConfigFile(cluster.id,sedVersion)
        ret = dmt.buildconfig.writeDBConfigToFile(sed,cfgName,tmpArea)
        if (ret == 1):
            return ret

    # Update the Configuration file with specific auto Deployment Requirements for Tor Inst
    # Generate a dict of the info in the correct format
    installData = {}
    installData["site_eng_doc_path"]={}
    installData["site_eng_doc_path"]=lmsUploadDir + "/" + cfgName

    rhel6PatchPath = rhel7PatchPath = rhel79PatchPath = rhel88PatchPath = ""
    installData["patches_archive_path"]=""
    if skipPatchInstall != "YES":
        if osRhel6PatchFileName and skipPatchInstall != "RHEL6":
            rhel6PatchPath = lmsUploadDir + "/" + osRhel6PatchFileName
        if osRhel7PatchFileName and skipPatchInstall != "RHEL7":
            if LooseVersion(enmInstRHEL7Patch) <= LooseVersion(enmInstVersion):
                rhel7PatchPath = lmsUploadDir + "/" + osRhel7PatchFileName
        if osRhel79PatchFileName and skipPatchInstall != "RHEL79":
            if LooseVersion(enmInstRHEL79Patch) <= LooseVersion(enmInstVersion):
                rhel79PatchPath = lmsUploadDir + "/" + osRhel79PatchFileName
        if osRhel88PatchFileName and skipPatchInstall != "RHEL88":
            if LooseVersion(enmInstRHEL88Patch) <= LooseVersion(enmInstVersion):
                rhel88PatchPath = lmsUploadDir + "/" + osRhel88PatchFileName
        installData["patches_archive_path"]='"' + rhel6PatchPath + ' ' + rhel7PatchPath + ' ' + rhel79PatchPath + ' ' + rhel88PatchPath + '"'

    if (servicePatchVersion != None):
        installData["litp_service_pack_path"]={}
        installData["litp_service_pack_path"]=lmsUploadDir + "/LITPServicePack-" + servicePatchVersion + ".tar.gz"
    if (isoName != None):
        installData["tor_iso_path"]={}
        if installType == "upgrade_install":
            installData["tor_iso_path"]=lmsUploadDir + "/" + reCreatedIsoName
        else:
            installData["tor_iso_path"]=lmsUploadDir + "/" + isoName

    installData["litp_iso_path"]={}
    installData["litp_iso_path"]=litpisopath

    logger.info("Adding Extra parameter for Product Inst Auto Deployment")
    dmt.infoforConfig.appendToConfig(tmpArea, installData, cfgName)
    return cfgName


def lmsUploadConfig(mgtServer, tmpArea, lmsUploadDir, cfgName):
    '''
    Function to upload Config file to lms upload directory.
    Output: Location of SED on LMS.
    '''
    logger.info("Uploading config file")
    ret = dmt.utils.paramikoSftp(
            mgtServer.server.hostname + "." + mgtServer.server.domain_name,
            "root",
            lmsUploadDir + "/" + cfgName,
            tmpArea + "/" + cfgName,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "put")
    if (ret != 0):
        return ret
    logger.info("Copied " + cfgName + " to node")
    return lmsUploadDir + "/" + cfgName


def checkCategory(packageListDict,allSkippedPackageList):
    '''
    Function to check the category of a package for software update functionality
    '''
    packageObject = None
    modelPackageList = []
    msPackageList = []
    servicePackageList = []
    dbPackageList = []
    scriptPackageList = []
    streamingPackageList = []
    eventsPackageList = []
    for package, version in packageListDict.items():
        found = False
        category = None
        if "__" in version:
            category = version.split("__")[1]
            version = version.split("__")[0]
        if version.lower() is "latest":
            version = "None"
            latest = "yes"
        elif "http" in version.lower():
            version = "None"
            latest = "no"
        else:
            latest = "no"
        completeArtifactURL = None
        packageObject = dmt.cloud.getPackageObject(package,version,completeArtifactURL,latest)
        if packageObject == None:
            logger.error("This package " + package + ", looks to be new, the software update does not support this")
            return (1,modelPackageList,servicePackageList,dbPackageList)
        category = packageObject.category.name
        if "ms" in category:
            msPackageList.append(package)
            found = True
        if "service" in category:
            servicePackageList.append(package)
            found = True
        if "model" in category:
            modelPackageList.append(package)
            found = True
        if env == "cloud":
            if "db" in category:
                dbPackageList.append(package)
                found = True
        if "scripting" in category:
            scriptPackageList.append(package)
            found = True
        if "streaming" in category:
            streamingPackageList.append(package)
            found = True
        if "events" in category:
            eventsPackageList.append(package)
            found = True
        if not found:
            if env == "cloud":
                allSkippedPackageList.append(str(package) + "(Not Part of the appropriate categories " + config.get('DMT_AUTODEPLOY', 'cloudSoftwareUpdateCategories') + ")")
            else:
                allSkippedPackageList.append(str(package) + "(Not Part of the appropriate categories " + config.get('DMT_AUTODEPLOY', 'physicalSoftwareUpdateCategories') + ")")
    modelPackages = '__'.join(modelPackageList)
    servicePackages = '__'.join(servicePackageList)
    dbPackages = '__'.join(dbPackageList)
    scriptPackages = '__'.join(scriptPackageList)
    msPackages = '__'.join(msPackageList)
    streamingPackages = '__'.join(streamingPackageList)
    eventsPackages = '__'.join(eventsPackageList)
    return (0,modelPackages,servicePackages,dbPackages,scriptPackages,msPackages,eventsPackages,streamingPackages,allSkippedPackageList)

def redeployVMServices(remoteConnection,packageList,lmsUploadDir,type,ignoreHa,check=None):
    '''
    Used to execute the softwareUpdate.bsh script which is included in the deploy tar file
    '''
    redeployScript = "softwareUpdate.bsh"
    successComment = "SOFTWARE UPDATE"
    errorComment = "ERROR:: "
    packageString = '__'.join(packageList)
    if check != None:
        cmd = lmsUploadDir + "/deploy/bin/" + str(redeployScript) + " -p " + str(packageString) + " -c " + str(check)
    else:
        cmd = lmsUploadDir + "/deploy/bin/" + str(redeployScript) + " -p " + str(packageString) + " -i " + str(ignoreHa)
    logger.info("Running " + cmd)
    type = "softwareUpdate"
    ret = remoteConnection.runChild(cmd, successComment, errorComment, type)
    if (ret != 0):
        logger.error("Could not redeploy the VM services: return code " + str(ret))
        return ret
    return ret

def execDeploy(remoteConnection, mgtServer, lmsUploadDir, cfgloc, stage, installType, successComment, errorComment, reInstallInstllScript, reStartFromStage, featTest, stopAtStage, skipStage, extraParameter,isoDirName, deployProduct,isoName,product,xmlFile, type, secondRunSkipPatches, osMedia, hcInclude, deployScriptVersion, enmInstVersion, skipOsInstall):
    '''
    The execDeploy function runs the deploy.sh script on the Management Server which installs ENM INST and ENM UTILITIES
    The deploy.sh script sources the global.env file, which stores the variables passed to this function.
    Both of these files are stored in the DeploymentScripts repo.
    The cfgloc parameter is a Config File which also contains other variables. These parameters are also made available
    to the deploy.sh script when it sources it.
    '''
    if deployProduct == "LITP2":
        deployScript = "deployLitp2.sh"
    else:
        deployScript = "deploy.sh"

    cmd = lmsUploadDir + "/deploy/bin/" + deployScript + " -C -c " + cfgloc + " -s " + stage + " -n " + installType + " -t " + reInstallInstllScript + " -g " + reStartFromStage + " -f " + featTest + " -p " + stopAtStage + " -k " + skipStage + " -o " + extraParameter + " -m " + lmsUploadDir + "/" + isoName + " -r " + product
    if isoDirName:
        cmd = cmd + " -a " + isoDirName
    if xmlFile:
        cmd = cmd + " -x " + xmlFile
    if secondRunSkipPatches:
        cmd = cmd + " -b"
    if "upgrade" in installType and osMedia != None and skipOsInstall != "YES":
        cmd = cmd + " -z " + osMedia
    if "upgrade" in installType and hcInclude == 'multipath_active_healthcheck' and LooseVersion(deployScriptVersion) >= LooseVersion("2.0.163") and LooseVersion(enmInstVersion) >= LooseVersion("2.10.8"):
        cmd = cmd + " -y " + hcInclude
    logger.info("Running " + cmd)
    if ( installType == "initial_install"):
        ret = remoteConnection.runChild(cmd, successComment, errorComment, type)
    else:
        ret = runCommand(remoteConnection,cmd,type)
    if (ret != 0):
        logger.error("Could not deploy: return code " + str(ret))
        return ret
    return ret

def execDeployCsl(remoteConnection, localCslIsoContentsSubDir, cfgLoc):
    """
    This function kicks off the csl med inst installer, with the relevant site engineerign file and path to the iso
    """
    cmd = "cd /opt/ericsson/cslmedinst/bin/;./cslmedinst.bsh --site " + cfgLoc + " --sw_iso " + localCslIsoContentsSubDir
    ret = remoteConnection.runCmdSimple(cmd)
    if (ret != 0):
        logger.error("Could not deploy: return code " + str(ret))
        return ret
    return ret

def execDeployEdp(deploymentId, productSet, mediaList, xmlFile, cfgLoc, edpVersion, edpProfileList, edpPackageList, extraParameter, hcInclude, ignoreUpgradePrecheck, deployScriptVersion, isoName, litpIsoName, kickstartFileUrl, skipNasPatchInstall, install_type=None, packageList=None, litpPackageList=None):
    """
    This function kicks off the enm edp runner python script, used for EDP
    """
    softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    edpDeployScript = config.get('DMT_AUTODEPLOY', 'edpDeployScript')
    if hcInclude == 'multipath_active_healthcheck':
       hcInclude = "NO"
    if mediaList:
        for media in mediaList:
            if "enm" in media and "autoDeploy.iso" in media:
                mediaList.remove(isoName)
            if "litp" in media and "autoDeploy.iso" in media:
                mediaList.remove(litpIsoName)
    mediaList = '@@'.join(mediaList)
    cmd = "/usr/bin/python " + softwareDir + edpDeployScript + " --deployment-id " + deploymentId + " --product-set-version " + productSet + " --xml-file " + xmlFile + " --ci-media-list " + mediaList + " --ci-media-path " + softwareDir + " --sed-filepath " + cfgLoc + " --vm-private-key-path " + softwareDir + "/vm_private_key" + " --hc-include " + hcInclude

    if edpVersion:
        cmd += " --edp-version " + edpVersion
    if edpProfileList:
        cmd += " --edp-profile-list " + edpProfileList
    if edpPackageList:
        cmd += " --edp-package-list " + edpPackageList
    if extraParameter != "NO":
        cmd += " --enm-inst-parameters " + extraParameter
    if ignoreUpgradePrecheck != "NO":
        cmd += " --ignore-upgrade-precheck " + ignoreUpgradePrecheck
    if install_type is not None:
        cmd += " --install-type " + install_type
    if packageList is not None:
        cmd += " --deployEnmPackage " + packageList
    if litpPackageList is not None:
        cmd += " --deployLitpPackage " + litpPackageList
    if kickstartFileUrl is not None:
        cmd += "--kickstart-file-url " + kickstartFileUrl
    if skipNasPatchInstall is not None:
        cmd += " --skip-nas-patch-install " + str(skipNasPatchInstall)
    result, ret = executeCmd(cmd, None, True)
    if (ret != 0):
        logger.error("Could not deploy: return code " + str(ret))
    return ret

def execEdpIISupportCheck(productSet, edpVersion, deployScriptVersion):
    """
    This function kicks off a check to see if product set provided, is EDP Initial Install Supported
    """
    tmpAreaEdp = tempfile.mkdtemp()
    isEdpIISupported = False
    softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    edpScript = config.get('DMT_AUTODEPLOY', 'edpDeployScript')

    edpIIDeployScriptVersion = config.get('DMT_AUTODEPLOY', 'edpIIDeployScriptVersion')
    if LooseVersion(edpIIDeployScriptVersion) > LooseVersion(deployScriptVersion):
        logger.info("============EDP II NOT SUPPORTED===========")
        return isEdpIISupported

    result, ret = downloadDeployScripts(deployScriptVersion, tmpAreaEdp)
    if not os.path.exists(softwareDir + edpScript):
        logger.info("============EDP II NOT SUPPORTED===========")
        result, ret = executeCmd("sudo rm -rf " + tmpAreaEdp)
        return isEdpIISupported

    cmd = "/usr/bin/python " + softwareDir + edpScript + " --check-edp-install-support --product-set-version " + productSet

    if edpVersion:
        cmd += " --edp-version " + edpVersion

    result, ret = executeCmd(cmd, None, True)
    if (ret == 0):
        logger.info("============EDP II SUPPORTED==========")
        isEdpIISupported = True
    else:
        logger.info("============EDP II NOT SUPPORTED==========")
        logger.info("EDP II not supported: " + result + ", return code " + str(ret))

    result, ret = executeCmd("sudo rm -rf " + tmpAreaEdp)
    return isEdpIISupported


def execEdpSupportedCheck(productSet, edpVersion, deployScriptVersion):
    """
    This function kicks off a check to see if product set provided, is EDP supported
    """
    tmpAreaEdp = tempfile.mkdtemp()
    isEdpSupported = False
    softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    edpScript = config.get('DMT_AUTODEPLOY', 'edpDeployScript')

    result, ret = downloadDeployScripts(deployScriptVersion, tmpAreaEdp)
    if not os.path.exists(softwareDir + edpScript):
        logger.info("============EDP UG NOT SUPPORTED==========")
        result, ret = executeCmd("sudo rm -rf " + tmpAreaEdp)
        return isEdpSupported

    cmd = "/usr/bin/python " + softwareDir + edpScript + " --check-edp-support --product-set-version " + productSet

    if edpVersion:
        cmd += " --edp-version " + edpVersion

    result, ret = executeCmd(cmd, None, True)
    if (ret == 0):
        logger.info("============EDP UG SUPPORTED==========")
        isEdpSupported = True
    else:
        logger.info("============EDP UG NOT SUPPORTED==========")
        logger.info("EDP UG not supported: " + result + ", return code " + str(ret))

    result, ret = executeCmd("sudo rm -rf " + tmpAreaEdp)
    return isEdpSupported

def runCommand(remoteConnection,cmd,type=None,timeout=None):
    '''
    This function kicks off a command on the server connection specified
    '''
    ret = remoteConnection.runCmdSimple(cmd,type,timeout)
    if (ret != 0):
        logger.error("Could not run command " + str(cmd) + " Exception: " + str(ret))
        return ret
    return ret

def execUpgradePrecheck(remoteConnection, script_name, isoDirName):
    '''
    This function checks if script available to kick off the prechecks.
    '''
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    findFileCmd = "find " + enmInstDir + " | grep '" + str(script_name) + "'"
    logger.info("Running " + findFileCmd)
    (ret, output) = remoteConnection.runCmdGetOutput(findFileCmd)
    if int(ret) == 0:
        if script_name == "enm_upgrade_prechecks.sh":
            executeScriptCmd = enmInstDir + str(script_name) + " --action upgrade_prerequisites_check --assumeyes --verbose"
        else:
            executeScriptCmd = enmInstDir + str(script_name) + " " + str(isoDirName)
        logger.info("Running " + executeScriptCmd)
        ret = runCommand(remoteConnection, executeScriptCmd, "tty-ssh")
    else:
        logger.info(str(script_name) + " not found, continue executing of UG.")
        ret = 0
    return ret

def runCommandGetOutput(remoteConnection,cmd,type=None):
    '''
    Used to recreate a repo once the new packages have been added
    '''
    commandOutput = None
    (ret, commandOutput) = remoteConnection.runCmdGetOutput(cmd,type)
    if (ret != 0):
        logger.error("Could not run command " + str(cmd) + " Exception: " + str(ret))
        return ret, commandOutput
    return ret, commandOutput

def findPackageInPackageList(packageList,searchPackage):
    '''
    Used to find a specific package and version in the packageList
    '''
    package = None
    version = None
    qualifier1 = "@@"
    qualifier2 = "::"
    list = packageList.split(qualifier1)
    for item in list:
        package = item.split(qualifier2)[0]
        version = item.split(qualifier2)[1]
        if package == searchPackage:
            return (package,version)
    return (package,version)

def buildPackageDict(packageList):
    '''
    Used to generate a Dict from a list given
    '''
    qualifier1 = "@@"
    qualifier2 = "::"
    isoLoc = None
    removeArtifact = False
    packageListDict = {}
    list = packageList.split(qualifier1)
    for item in list:
        numberOfStrings = item.count("::")
        package = item.split(qualifier2)[0]
        version = item.split(qualifier2)[1]
        if numberOfStrings == 3:
            removeArtifact = item.split(qualifier2)[3]
        elif numberOfStrings == 2:
            isoLoc = item.split(qualifier2)[2]
        if removeArtifact:
            packageListDict[str(package)] = "removeArtifact"
        elif isoLoc != None:
            packageListDict[str(package)] = str(version) + "__" + isoLoc
        else:
            packageListDict[str(package)] = str(version)
        removeArtifact = False
        isoLoc = None
    return packageListDict

def setDropIsoVersion(dropVersion):
    '''
    Used to split the drop and iso version if inputted ie. Drop::isoVersion
    '''
    product = None
    qualifier = "::"
    drop = dropVersion.split(qualifier)[0]
    isoVersion = dropVersion.split(qualifier)[1]
    isoVersion = isoVersion.upper()
    if len(dropVersion.split(qualifier)) == 3:
        product = dropVersion.split(qualifier)[2]
    return (drop, isoVersion, product)


def downloadExtraPackages(clusterId,packageListDict,packagesDir,product=None):
    '''
    Used to Download the Extra Packages
    '''
    downloadPackageList=[]
    downloadPackageCategoryList=[]
    try:
        for package, version in packageListDict.items():
            category = None
            if "removeArtifact" in str(version):
                continue
            if "__" in version:
                category = version.split("__")[1]
                version = version.split("__")[0]
            if version.lower() is "latest":
                version = "None"
                completeArtifactURL = "None"
                latest = "yes"
            elif "http" in version.lower():
                completeArtifactURL = version
                version = "None"
                latest = "no"
            else:
                completeArtifactURL = "None"
                latest = "no"
            packageObject = dmt.cloud.getPackageObject(package,version,completeArtifactURL,latest)
            if category == None and packageObject == None:
                logger.error("This package " + package + ", looks to be new, please add a media category and try again")
                return 1,downloadPackageCategoryList
            if category == None:
                category = packageObject.category.name
            artifactName = dmt.cloud.downloadArtifact(packagesDir,completeArtifactURL,packageObject,product)
            if artifactName == 1:
                logger.info("Unable to download extra package " + str(package))
                return 1,downloadPackageCategoryList
            downloadPackageList.append(artifactName)
            downloadPackageCategoryList.append(category)
        return downloadPackageList,downloadPackageCategoryList
    except Exception as e:
        logger.info("Unable to download extra packages")
        return 1,downloadPackageCategoryList

def checkIfProductTorExists(remoteConnection,isoRebuildlocation):
    '''
    Function used to check if the product ENM directory exists
    '''
    # Check if this is the old ISO Structure or New ISO Structure
    productTor = isoRebuildlocation + config.get('DMT_AUTODEPLOY', 'productTor')
    ret = remoteConnection.runCmd("ls " + productTor)
    if (ret != 0):
        productTorExists = "no"
    else:
        productTorExists = "yes"
    return productTorExists

def checkIsoStructure(remoteConnection,isoRebuildlocation):
    '''
    Function used to check which type of ISO is being used
    '''
    # Check if this is the old ISO Structure or New ISO Structure
    oldLocation = isoRebuildlocation + config.get('DMT_AUTODEPLOY', 'sw_dir')
    ret = remoteConnection.runCmd("ls " + oldLocation)
    if (ret != 0):
        commonIsoLocation = isoRebuildlocation + config.get('DMT_AUTODEPLOY', 'service_repo')
        structure = "new"
        deploymentPackageLocation = config.get('DMT_AUTODEPLOY', 'ms_repo')
    else:
        commonIsoLocation = isoRebuildlocation + config.get('DMT_AUTODEPLOY', 'sw_dir')
        structure = "old"
        deploymentPackageLocation = config.get('DMT_AUTODEPLOY', 'sw_dir')
    return (commonIsoLocation,structure,deploymentPackageLocation)

def getLocationAndPackage(remoteConnection,isoLocation,package,stringOnly=None):
    '''
    Used to get the version of a package on the ISO
    '''
    commandOutput = None
    if stringOnly:
        (ret, commandOutput) = remoteConnection.runCmdGetOutput("find " + isoLocation + " -regex \'/.*/"+ package + "\'")
    else:
        (ret, commandOutput) = remoteConnection.runCmdGetOutput("find " + isoLocation + " -regex \'/.*/"+ package + "-[0-9].*\'")
    if ret != 0 or commandOutput == None:
        return (1,commandOutput)
    commandOutputList = commandOutput.rsplit('\r')
    commandOutputList = list(map(str.strip,commandOutputList))
    commandOutputList = filter(None, commandOutputList)
    return (ret,commandOutputList)


def doesPackageExistInDirectory(remoteConnection,directory,package):
    '''
    Used to check if part of a package string exists in a given directory
    '''
    (ret, commandOutput) = remoteConnection.runCmdGetOutput("find " + directory + " -name '" + package + "*'")
    logger.info("------- Find result: " + str(commandOutput))
    if not package in str(commandOutput):
        return 1
    return ret

def getSlicesSnapFilesInfo(remoteConnection,isoLocation):
    '''
    Function used to get the required slice informaion
    '''
    artifact = packageVersion = group = message = None
    package=config.get('DMT_AUTODEPLOY', 'deploymentTemplatePackage')
    # Get the package name & version from the iso
    (ret,commandOutput) = getLocationAndPackage(remoteConnection,isoLocation,package)
    if ret != 0:
        message = "Issue getting the package information for " + str(package)
        return (artifact,group,message)
    for item in commandOutput:
        if package in item:
            package = os.path.basename(str(item))
            packageName = package.split("-")[0]
            packageVersion = package.split("-")[1]
            packageVersion = packageVersion.replace(".rpm","")
            #Incase the package in the iso is already a snapshot
            packageVersion = packageVersion.split("-")[0]
            break
    try:
        packageObj = Package.objects.get(name=str(packageName))
        packageVersionObj = PackageRevision.objects.get(package=packageObj,version=str(packageVersion))
    except Exception as e:
        message = "Issue getting the package information for " + str(package) + ", version:" + str(packageVersion) +". Exception: " + str(e)
        return (artifact,group,message)
    artifact = packageVersionObj.artifactId
    group = packageVersionObj.groupId
    secondGroup = config.get('DMT_AUTODEPLOY', 'secondSliceGroupId')
    secondArtifact = config.get('DMT_AUTODEPLOY', 'secondSliceArtifactId')
    return (artifact,group,secondArtifact,secondGroup,packageVersion)

def getSliceXmlFromSliceFile(remoteConnection,locationToSearch,searchString):
    '''
    Function used to get the slice from the unzipped file
    '''
    xmlFile = None
    stringOnly = "YES"
    (ret,commandOutput) = getLocationAndPackage(remoteConnection,locationToSearch,searchString,stringOnly)
    if ret != 0:
        return (1,xmlFile)
    for item in commandOutput:
        if searchString in item:
            xmlFile = item
            break
    return (0,xmlFile)

def downloadSlices(remoteConnection,artifact,group,packageVersion,lmsUploadDir):
    '''
    Function used to download and unzip the slice file
    '''
    snapVersion = None
    # Get the Nexus API link
    nexusUrlApi=config.get('DMT_AUTODEPLOY', 'nexus_url_api')
    snapVersion = packageVersion + "-SNAPSHOT"
    # Download the Zip file to the MS add to /var/tmp/
    cmd = "\'curl -f -o " + lmsUploadDir + "/" + str(artifact) + "-" + str(snapVersion) + ".zip -L -# \"" + str(nexusUrlApi) + "/artifact/maven/redirect?r=snapshots&g=" + str(group) + "&a=" + str(artifact) + "&e=zip&v=" + str(snapVersion) + "\"\'"
    ret = runCommand(remoteConnection,cmd)
    if (ret != 0):
        return (1, snapVersion)
    return (0, snapVersion)

def yumInstallApp(remoteConnection,app):
    '''
    Function used to yum install an app
    '''
    cmd = "yum install -y " + str(app)
    ret = runCommand(remoteConnection,cmd)
    if (ret != 0):
        return 1
    return 0

def unzipFile(remoteConnection,file,unzipLocation):
    '''
    Function used to unzip a file
    '''
    cmd = "unzip -o " + str(file) + " -d " + str(unzipLocation)
    ret = runCommand(remoteConnection,cmd)
    if (ret != 0):
        return 1
    return 0

def recreateReposUpdated(remoteConnection,repoList):
    '''
    Function used to rebuild the repos once a new packages has been added
    '''
    try:
        for item in repoList:
            cmd = "createrepo " + str(item) +"; yum clean all"
            ret = runCommand(remoteConnection,cmd)
            if (ret != 0):
                return 1
    except:
        return 1
    return 0

def replacePackages(packageListDict,remoteConnection,mgtServer,isoLocation,downloadPackageList,packagesDir,isoRebuildlocation,isoPath,installType):
    '''
    Used to replace the extra packages from the ISO
    '''
    repoList = []
    try:
        if installType != "softwareupdateonly":
            # Check if this is the old ISO Structure or New ISO Structure
            (commonIsoLocation,structure,deploymentPackageLocation) = checkIsoStructure(remoteConnection,isoRebuildlocation)
        replacedPackage = False
        packageList = []
        installedPackageList = []
        removeArtifactList = []
        skippedPackageList = []
        ret = 0
        for package, version in packageListDict.items():
            if "removeArtifact" in str(version):
                removeArtifactList.append(package)
            packageExists = False
            category = None
            (ret, commandOutput) = remoteConnection.runCmdGetOutput("find " + isoLocation + " -regex \'/.*/"+ package + "-[0-9].*\'")
            logger.info("Find result: " + commandOutput)
            if installType == "softwareupdateonly":
                # Check is the same package already included
                for pkg in downloadPackageList:
                    if str(pkg) in commandOutput:
                        logger.info("Package " + str(pkg) + " already included.. Skipping")
                        packageExists = True
                        skippedPackageList.append(str(pkg) + "(Found within " + isoLocation + ")")
                        break
                    else:
                        commandOutputList = commandOutput.split("\r");
                        commandOutputList = list(map(str.strip,commandOutputList))
                        commandOutputList = filter(None, commandOutputList)
                        for item in commandOutputList:
                            if (str(package) in item):
                                installedPackageList.append(os.path.basename(item) + "(" + isoLocation + ")")
                                break
                if packageExists: continue
            if "__" in version:
                version,category = version.split("__")
            # Did we find packages in the ISO
            if (str(isoLocation) in commandOutput):
                packageList.append(package)
                replacedPackage = True
                # Split the String into a List
                commandOutputList = commandOutput.split( )
                for item in commandOutputList:
                    #Item is what is found on the ISO
                    if (str(isoLocation) in item):
                        baseName = os.path.basename(item)
                        packageName = re.split(r'-(\d+\.\d.*)', baseName)[0]
                        ENMIsoLocation = os.path.dirname(item)
                        for artifact in removeArtifactList:
                            if str(artifact) == str(packageName):
                                ret = remoteConnection.runCmd("rm " + str(item))
                                if (ret != 0):
                                    return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                        for pkg in downloadPackageList:
                            localPackage = re.sub(r'-(\d+\.\d.*)','', pkg)
                            if str(packageName) != str(localPackage):
                                continue
                            logger.info("Package match found...")
                            ret = remoteConnection.runCmd("rm " + str(item))
                            if (ret != 0):
                                return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                            elif "removeArtifact" in str(version):
                                continue
                            if installType != "softwareupdateonly":
                                if category != None:
                                    categories = category.split(",")
                                    for category in categories:
                                        if config.has_option('DMT_AUTODEPLOY', str(category) + '_repo'):
                                            ENMIsoLocation = isoRebuildlocation + "/" + config.get('DMT_AUTODEPLOY', str(category) + '_repo')
                                        else:
                                            ENMIsoLocation = commonIsoLocation
                                        logger.info("Updating the Package " + str(pkg) + " within " + str(ENMIsoLocation) + " with Media Category: " + str(category))
                                        ret = uploadPackage(mgtServer,packagesDir,pkg,ENMIsoLocation)
                                        if (ret != 0):
                                            return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                                    category = None
                                else:
                                    logger.info("Updating the Package " + str(pkg) + " within " + str(ENMIsoLocation))
                                    ret = uploadPackage(mgtServer,packagesDir,pkg,ENMIsoLocation)
                                    if (ret != 0):
                                        return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                            else:
                                logger.info("Updating the Package " + str(pkg) + " within " + str(ENMIsoLocation + " using software update."))
                                ret = uploadPackage(mgtServer,packagesDir,pkg,ENMIsoLocation)
                                if (ret != 0):
                                    return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                                if ENMIsoLocation not in repoList:
                                    repoList.append(ENMIsoLocation)
                                    continue
                            if pkg.endswith('.qcow2'):
                                ret = handleQCOW2Artifacts(ENMIsoLocation,pkg,remoteConnection)
                                if (ret != 0):
                                    return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                            continue
            else:
                # No entry found in ISO
                logger.info("Package " + str(package) + " never delivered before")
                if installType == "softwareupdateonly":
                    skippedPackageList.append(str(pkg) + "(Not Found within " + str(isoLocation) +")")
                    continue
                packageList.append(package)
                # we will use the category, if no category then they will default to the common area
                if category == None:
                    if "http" in version:
                        version = None
                        completeArtifactURL = version
                    else:
                        completeArtifactURL = None
                    packageObject = dmt.cloud.getPackageObject(package,version,completeArtifactURL,"no")
                    if packageObject != None:
                        category = packageObject.category.name
                    else:
                        logger.info("No Category can be found defaulting to the common category on the ISO")
                        category = "service"
                categories = category.split(",")
                for category in categories:
                    if config.has_option('DMT_AUTODEPLOY', str(category) + '_repo'):
                        ENMIsoLocation = isoRebuildlocation + "/" + config.get('DMT_AUTODEPLOY', str(category) + '_repo')
                    else:
                        logger.info("No Repo found in local config defaulting to common area")
                        ENMIsoLocation = commonIsoLocation
                    for pkg in downloadPackageList:
                        if str(package) not in pkg:
                            continue
                        ret = uploadPackage(mgtServer,packagesDir,pkg,ENMIsoLocation)
                        if (ret != 0):
                            return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                        if pkg.endswith('.qcow2'):
                            ret = handleQCOW2Artifacts(ENMIsoLocation,pkg,remoteConnection)
                            if (ret != 0):
                                return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                        continue
                # Check does the old products directory structure still exist
                oldProductLocation = isoRebuildlocation + "/" + isoPath
                ret = remoteConnection.runCmd("ls " + oldProductLocation)
                if (ret == 0):
                    for pkg in downloadPackageList:
                        if str(package) not in pkg:
                            continue
                        ret = uploadPackage(mgtServer,packagesDir,pkg,oldProductLocation)
                        if (ret != 0):
                            return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
                category = None
        if installType == "softwareupdateonly":
            if replacedPackage == False:
                return (0,replacedPackage,packageList,installedPackageList,skippedPackageList)
            if len(repoList) != 0:
                ret = recreateReposUpdated(remoteConnection,repoList)
                if (ret != 0):
                    logger.info("Issue with recreating the Repo(s)")
                    return (ret,replacedPackage,packageList,installedPackageList,skippedPackageList)
        return (0,replacedPackage,packageList,installedPackageList,skippedPackageList)
    except Exception as e:
        logger.error("Issue Removing files from mounted iso: " + str(e))
        return (1,replacedPackage,packageList,installedPackageList,skippedPackageList)

def handleQCOW2Artifacts(ENMIsoLocation,pkg,remoteConnection):
    '''
    The handleQCOW2Artifacts function is a helper function for replacePackes to handles qcow2 artifacts
    '''
    command = "/usr/bin/md5sum " + str(ENMIsoLocation) + "/" + pkg
    (ret,commandOutput) = runCommandGetOutput(remoteConnection,command)
    if (ret != 0):
        return ret
    commandOutputList = commandOutput.split("\r");
    commandOutputList = list(map(str.strip,commandOutputList))
    commandOutputList = filter(None, commandOutputList)
    for item in commandOutputList:
        if (str(pkg) in item):
            commandOutput = item.split(" ")[0]
            command = "echo " + str(commandOutput) + " > " + str(ENMIsoLocation) + "/" + pkg + ".md5"
            ret = runCommand(remoteConnection,command)
            if (ret != 0):
                return ret
    return 0

def uploadPackage(mgtServer,packagesDir,package,isoLocation):
    '''
    Used to Upload the Package to the ISO
    '''
    logger.info("Uploading " + packagesDir + "/" + package + " to " + isoLocation + "/" + package)
    ret = dmt.utils.paramikoSftp(
            mgtServer.server.hostname + "." + mgtServer.server.domain_name,
            "root",
            isoLocation + "/" + package,
            packagesDir + "/" + package,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "put")
    if (ret != 0):
        return ret
    return 0

def removeExtraPackage(packageListDict,remoteConnection,mgtServer,isoLocation):
    '''
    Used to Remove the extra packages from the iso upload
    '''
    try:
        for package, version in packageListDict.items():
            ret = remoteConnection.runCmd("find " + isoLocation + " -regex \'/.*/"+ package + "-[0-9].*\'  | while read oldPkg; do rm ${oldPkg}; done")
        return 0
    except Exception as e:
        logger.error("Issue Removing files from mounted iso: " + str(e))
        return 1

def uploadExtraPackages(downloadPackageList,mgtServer,packagesDir,isoLocation):
    '''
    Used to Upload the Extra Packages
    '''
    for package in downloadPackageList:
        logger.info("Uploading " + packagesDir + "/" + package + " to " + isoLocation + package)
        ret = dmt.utils.paramikoSftp(
                mgtServer.server.hostname + "." + mgtServer.server.domain_name,
                "root",
                isoLocation + "/" + package,
                packagesDir + "/" + package,
                int(config.get('DMT_AUTODEPLOY', 'port')),
                config.get('DMT_AUTODEPLOY', 'key'),
                "put")
        if (ret != 0):
            return ret
    return 0

def getLastUploadedIso(remoteConnection,mgtServer,lmsUploadDir,lastIsoImportedFile):
    '''
    Used to recreate a repo once the new packages have been added
    '''
    logger.info("Getting last ISO version imported")
    (ret, command_output) = remoteConnection.runCmdGetOutput("cat " + lmsUploadDir + "/" + lastIsoImportedFile)
    return ret, command_output

def cleanDownVMS(remoteConnection,mgtServer):
    '''
    Used to clean down the Virtual Management Server on a Litp 2 System
    '''
    ###TODO
    try:
        logger.info("Running: \"This needs to be implemented to clean down the VMS\"")
        ret = remoteConnection.runCmd("echo \" This needs to be implemented to clean down the VMS\"")
        if (ret != 0):
            return ret
        return 0
    except Exception as e:
        logger.error("Unable to to clean down the virtual MS system: " + str(e))
        return 1

def searchFileForString(remoteConnection,fileName,listOfItemsToSearch,initial_wait=None,interval=None,retries=None):
    '''
    Function used to search a specific file for a list of strings
    '''
    # Set default values
    if initial_wait == None:
        initial_wait=10
    if interval == None:
        interval=20
    if retries == None:
        retries=60

    logger.info("Starting the check for string in file " + str(fileName) + " in " + str(initial_wait) + "  seconds")
    time.sleep(initial_wait)
    logger.info("Checking for String in file" + str(fileName))
    count = 1
    command = " cat " + str(fileName)
    for x in range(retries):
        notFound = 1
        logger.info("Try " + str(count) + " of " + str(retries))
        count += 1
        try:
            (ret,commandOutput) = runCommandGetOutput(remoteConnection,command)
            for item in listOfItemsToSearch:
                if (str(item) not in commandOutput):
                    logger.info("Search String \"" + str(item) + "\" Not Found. Sleeping " + str(interval) + " before retry... ")
                    time.sleep(interval)
                    notFound = 1
                    break
                else:
                    logger.info("Search String \"" + str(item) + "\" Found.")
                    notFound = 0
                    continue
        except Exception as e:
            logger.error("Issue with the String Search, Exception: " + str(e))
            return 1
        if (notFound == 1):
            continue
        else:
            return 0
    return 1

def createKickstartFile(mgtServer, tmpArea, osVersion, drop, jumpServerIp):
    if NetworkInterface.objects.filter(server=mgtServer.server_id, interface="eth0").exists():
        networkObject = NetworkInterface.objects.get(server=mgtServer.server_id, interface="eth0")
        if IpAddress.objects.filter(nic=networkObject.id,ipType="host").exists():
            ipAddressObj = IpAddress.objects.get(nic=networkObject.id,ipType="host")
            ipAddress = ipAddressObj.address
        else:
            logger.error("Could not get the server Ip or network address for management server " + str(mgtServer.server.hostname))
            return 1
    else:
        logger.error("Could not get the server MAC Address")
        return 1
    newFile = mgtServer.server.hostname + "-" + ipAddress + "_ms-ks-jumpstart.cfg"
    # Check do we have a kickstart with the drop appended if we do then use that one else use the latest kickstart file
    ret, output = commands.getstatusoutput("ls /net/" + str(jumpServerIp) + config.get('DMT_AUTODEPLOY', 'rhelDir') + "/" + osVersion + config.get('DMT_AUTODEPLOY', 'rhelKickstartTemplate') + "_" + drop)
    if ( "No such file" in output):
        logger.info("Using latest stored Kickstart File for ENM Drop " + drop)
        shutil.copy("/net/" + str(jumpServerIp) + config.get('DMT_AUTODEPLOY', 'rhelDir') + "/" + osVersion + config.get('DMT_AUTODEPLOY', 'rhelKickstartTemplate'), tmpArea + "/" + newFile)
    else:
        logger.info("Using Specific Kickstart File for ENM Drop " + drop)
        shutil.copy("/net/" + str(jumpServerIp) + config.get('DMT_AUTODEPLOY', 'rhelDir') + "/" + osVersion + config.get('DMT_AUTODEPLOY', 'rhelKickstartTemplate') + "_" + drop, tmpArea + "/" + newFile)
    nodesdict={}
    nodesdict["kickConfig"]={}
    nodesdict["kickConfig"]["<HOSTNAME>"] = mgtServer.server.hostname
    nodesdict["kickConfig"]["<JUMPSERVERIP>"] = jumpServerIp
    dmt.infoforConfig.createconfig(tmpArea, nodesdict, newFile)
    ret, output = commands.getstatusoutput("rm /net/" + str(jumpServerIp) + config.get('DMT_AUTODEPLOY', 'rhelDir') + "/" + osVersion + config.get('DMT_AUTODEPLOY', 'rhelKickstartFileDir') + newFile)
    if (ret != 0  and "No such file" not in output):
        logger.error("Error: The removal of the kickstart file failed, Output : " + str(output))
        return "error"
    shutil.move(tmpArea + "/" + newFile, "/net/" + str(jumpServerIp) + config.get('DMT_AUTODEPLOY', 'rhelDir') + "/" + osVersion + config.get('DMT_AUTODEPLOY', 'rhelKickstartFileDir') + newFile)

    os.chmod("/net/" + str(jumpServerIp) + config.get('DMT_AUTODEPLOY', 'rhelDir') + "/" + osVersion + config.get('DMT_AUTODEPLOY', 'rhelKickstartFileDir') + newFile, 0777)
    return os.path.splitext(newFile)[0]

def jumpPhysical(mgtServer,clusterId,tmpArea,step,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList):
    '''
    Function used to boot the physical server from the Network by changing the boot order
    '''
    logger.info("Changing Boot Order to boot from Network")
    dmt.jumpFromNetwork.configureBoot(mgtServer,"network") == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not change the boot order on the MS server to boot from Network",tmpArea)
    checkStep(step)
    logger.info("Restarting the server from the ilo")
    dmt.jumpFromNetwork.configureBoot(mgtServer,"reset") == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not change the boot the MS through the ilo",tmpArea)
    checkStep(step)
    logger.info("Waiting 300 seconds for the server to boot from the Network")
    time.sleep(300)
    logger.info("Changing Boot Order to boot from the disk")
    dmt.jumpFromNetwork.configureBoot(mgtServer,"disk") == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not change the boot order on the MS server to boot from disk",tmpArea)
    checkStep(step)
    return 0

def checkCloudLock(cloudLockFileName,cloudQueueFileName,jumpServerIp):
    '''
    Function used if CTRL-C is hit to ensure it deletes it's own cloud Lock
    '''
    rhelDir = config.get('DMT_AUTODEPLOY', 'rhelDir')
    logger.info("Checking Lock file \"" + rhelDir + "/cloudLock/" + cloudLockFileName)
    lockLocation = "/net/" + jumpServerIp + rhelDir + "/cloudLock/"
    cloudLockFile = lockLocation + cloudLockFileName
    # Get Queue Reference
    ret = 0
    if os.path.isfile(cloudLockFile):
        queueFile = open(os.path.expanduser(cloudLockFile), "r")
        queueFile.seek(0)
        queueFileRef = queueFile.readline()
        if cloudQueueFileName == queueFileRef:
            return 1
        if os.path.isfile(lockLocation + cloudQueueFileName):
            ret, output = commands.getstatusoutput("rm " + lockLocation + queueFileRef)
            if (ret != 0  and "No such file" not in output):
                logger.error("Error thrown during the removal of the cloud queue file, Output : " + str(output))
                return ret
    elif os.path.isfile(lockLocation + cloudQueueFileName):
        ret, output = commands.getstatusoutput("rm " + lockLocation + cloudQueueFileName)
        if (ret != 0  and "No such file" not in output):
            logger.error("Error thrown during the removal of the cloud queue file, Output : " + str(output))
            return ret
    else:
        logger.info("Lock does not exist")
        return ret
    return ret


def removeCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp):
    '''
    Function used to remove the cloud lock file
    '''
    rhelDir = config.get('DMT_AUTODEPLOY', 'rhelDir')
    logger.info("Removing Lock file \"" + rhelDir + "/cloudLock/" + cloudLockFileName)
    lockLocation = "/net/" + jumpServerIp + rhelDir + "/cloudLock/"
    cloudLockFile = lockLocation + cloudLockFileName
    # Get Queue Reference
    ret = 0
    if os.path.isfile(cloudLockFile):
        queueFile = open(os.path.expanduser(cloudLockFile), "r")
        queueFile.seek(0)
        queueFileRef = queueFile.readline()
        if os.path.isfile(lockLocation + queueFileRef):
            ret, output = commands.getstatusoutput("rm " + lockLocation + queueFileRef)
            if (ret != 0  and "No such file" not in output):
                logger.error("Error thrown during the removal of the cloud queue file, Output : " + str(output))
                return ret
        ret, output = commands.getstatusoutput("rm " + str(cloudLockFile))
        if (ret != 0  and "No such file" in output):
            return 0
        elif (ret != 0):
            logger.error("Thrown an error during the removal of the cloud lock file, Output : " + str(output))
            return ret
    elif os.path.isfile(lockLocation + cloudQueueFileName):
        ret, output = commands.getstatusoutput("rm " + lockLocation + cloudQueueFileName)
        if (ret != 0  and "No such file" not in output):
            logger.error("Error thrown during the removal of the cloud queue file, Output : " + str(output))
            return ret
    else:
        logger.info("Lock does not exist")
    return ret

def checkCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp):
    '''
    Check the lock file for the cloud deployment
    '''
    rhelDir = config.get('DMT_AUTODEPLOY', 'rhelDir')

    logger.info("Checking cloud Lock file \"" + rhelDir + "/cloudLock/" + cloudLockFileName + "\" for MS on Jump Server")
    waitTime = 900
    totalWait = 3600
    searchDir = "/net/" + jumpServerIp + rhelDir + "/cloudLock/"
    lockFile = searchDir + cloudLockFileName
    queueFile = searchDir + cloudQueueFileName
    hostName = socket.gethostbyaddr(socket.gethostname())[0]
    createCloudQueueFile(cloudQueueFileName,jumpServerIp)
    runAgain = 0
    totalAheadOrig = 5000
    while (totalWait > 0):
        ret, output = commands.getstatusoutput("find " + lockFile + " -mmin +15")
        if (output != "" and "No such file" not in output):
            logger.error("Lock File older that 15 minutes deleting")
            ret = removeCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp)
            if (ret != 0 ):
                logger.error("Issue removing the cloud Lock file")
                return 1
        # Find all the current queue files
        files = filter(os.path.isfile, glob.glob(searchDir + "*_QueueFile.txt"))
        for file in files:
            if cloudQueueFileName in file:
                continue
            ret, output = commands.getstatusoutput("find " + file + " -mmin +15")
            if (output != "" and "No such file" not in output):
                logger.error("Queue File older that 15 minutes deleting")
                ret, output = commands.getstatusoutput("rm " + file)
                if (ret != 0  and "No such file" not in output):
                    logger.error("Error thrown during the removal of the cloud queue file, Output : " + str(output))
                    return ret
        #Get the list of queue files again incase some have been deleted
        files = filter(os.path.isfile, glob.glob(searchDir + "*_QueueFile.txt"))
        files.sort(key=lambda x: os.path.getmtime(x))
        totalAhead = len(files) - 1
        if totalAhead < totalAheadOrig:
            runAgain = 0
            totalAheadOrig = totalAhead
        if not files:
            break
        # If our queue is first in the list then we are next
        if cloudQueueFileName == os.path.basename(files[0]):
            break
        # Give 15 minutes per deployment ahead of this one
        if runAgain != 1:
            totalWait = ( 60 * 15 ) * totalAheadOrig
            runAgain = 1
        if totalAhead > 0:
            logger.info("There is " + str(totalAheadOrig) + " cloud deployment(s) performing an OS install ahead of this one please wait")
            minutes = int(totalWait / 60)
            secondsRem = int(totalWait % 60)
            if (secondsRem < 10):
                timeLeft = str(minutes) + " Minutes 0" + str(secondsRem) + " Seconds"
            else:
                timeLeft = str(minutes) + " Minutes " + str(secondsRem) + " Seconds"
            logger.info("Waiting 30 seconds before retry, maximum wait time " + str(timeLeft))
            time.sleep(30)
            totalWait = totalWait - 30
        else:
            break
    while (waitTime > 0):
        ret, output = commands.getstatusoutput("find " + lockFile + " -mmin +15")
        if (ret != 0  and "No such file" in output):
            logger.info("No Lock file exists")
            return 0
        elif (ret != 0):
            logger.error("Issue finding the cloud lock file")
            return 1
        if (output != ""):
            logger.error("Lock File older that 15 minutes deleting")
            ret = removeCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp)
            if (ret != 0 ):
                logger.error("Issue removing the cloud Lock file")
                return 1
            return 0
        minutes = int(waitTime / 60)
        secondsRem = int(waitTime % 60)
        if (secondsRem < 10):
            timeLeft = str(minutes) + " Minutes 0" + str(secondsRem) + " Seconds"
        else:
            timeLeft = str(minutes) + " Minutes " + str(secondsRem) + " Seconds"

        logger.info("Lock file exists Waiting 30 seconds before retry, maximum wait time " + str(timeLeft))
        time.sleep(30)
        waitTime = waitTime - 30
    # If we have gotten this far we have waited enough time so delete the lockfile to continue the installation
    logger.error("Lock File older that 15 minutes deleting")
    ret = removeCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp)
    if (ret != 0 ):
        logger.error("Issue removing the cloud Lock file")
        return 1
    return 0

def createCloudQueueFile(cloudQueueFileName,jumpServerIp):
    '''
    Create a queue file for the cloud deployment
    '''
    rhelDir = config.get('DMT_AUTODEPLOY', 'rhelDir')

    logger.info("Creating cloud queue file \"" + rhelDir + "/cloudLock/" + cloudQueueFileName + "\" for MS on Jump Server")
    ret, output = commands.getstatusoutput("touch /net/" + jumpServerIp + rhelDir + "/cloudLock/" + cloudQueueFileName)
    if (ret != 0 ):
        logger.error("Issue creating cloud Lock file. Please investigate")
        return ret
    return ret

def createCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp):
    '''
    Create a lock for the cloud deployment
    '''
    rhelDir = config.get('DMT_AUTODEPLOY', 'rhelDir')

    lockFile = "/net/" + jumpServerIp + rhelDir + "/cloudLock/" + cloudLockFileName
    logger.info("Creating Cloud Jump Lock file: " +str(lockFile))
    ret, output = commands.getstatusoutput("touch " + str(lockFile))
    if (ret != 0 ):
        logger.error("Issue creating cloud Lock file. Please investigate")
        return ret
    updateFile = open(os.path.expanduser(lockFile), "w")
    updateFile.write(cloudQueueFileName)
    updateFile.close()
    return ret

def jumpCloud(mgtServer,clusterId,step,hostname):
    '''
    Function used to boot the cloud Virtual server from the Network by changing the boot order
    '''
    hostName = socket.gethostbyaddr(socket.gethostname())[0]
    cifwkUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    url = "curl --insecure -s "  +cifwkUrl + "/getSpp/?gateway=" +str(hostName)
    ret, cloudUrl = commands.getstatusoutput(str(url))
    if (ret != 0 or "Stack trace" in cloudUrl ):
        logger.error("Issue running the command to return SPP. Please investigate")
        return 1

    # power on check
    cloudPowerOn = config.get('DMT_AUTODEPLOY', 'cloudPowerOn')
    cloudPowerOnCommand = "curl --insecure " + str(cloudUrl) + str(cloudPowerOn) + str(hostname) + ".xml"
    logger.info("Ensuring the " + hostname + " is powered on")
    ret, output = commands.getstatusoutput(str(cloudPowerOnCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue running the command \"" + str(cloudPowerOnCommand) + "\" from the gateway. Please investigate")
        return 1

    # from network
    cloudBootFromNetwork = config.get('DMT_AUTODEPLOY', 'cloudBootFromNetwork')
    cloudBootFromNetworkCommand = "curl --insecure " + str(cloudUrl) + str(cloudBootFromNetwork) + str(hostname) + ".xml"
    logger.info("Changing Boot Order to boot from Network")
    ret, output = commands.getstatusoutput(str(cloudBootFromNetworkCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue running the command \"" + str(cloudBootFromNetworkCommand) + "\" from the gateway. Please investigate")
        return 1
    checkStep(step)


    # reset
    cloudBootReset = config.get('DMT_AUTODEPLOY', 'cloudBootReset')
    cloudBootResetCommand = "curl --insecure " + str(cloudUrl) + str(cloudBootReset) + str(hostname) + ".xml"
    logger.info("Restarting the VM")
    ret, output = commands.getstatusoutput(str(cloudBootResetCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue run the command \"" + str(cloudBootResetCommand) + "\" from the gateway. Please investigate")
        return 1
    checkStep(step)

    # wait
    logger.info("Waiting 300 seconds for the server to boot from the Network")
    time.sleep(300)

    # from disk
    cloudBootFromDisk = config.get('DMT_AUTODEPLOY', 'cloudBootFromDisk')
    cloudBootFromDiskCommand = "curl --insecure " + str(cloudUrl) + str(cloudBootFromDisk) + str(hostname) + ".xml"
    logger.info("Changing Boot Order to boot from Disk")
    ret, output = commands.getstatusoutput(str(cloudBootFromDiskCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue runnning the command \"" + str(cloudBootFromDiskCommand) + "\" from the gateway. Please investigate")
        return 1
    checkStep(step)

    return 0

def jumpVirtual(mgtServer,clusterId,tmpArea,step,hostname):
    '''
    Function used to boot the Virtual server from the Network by changing the boot order
    '''
    # The vmName is the same as the hostname put drop all from the "-" within the hostname
    vmName = mgtServer.server.hostname.split("-")[0]
    virtualPowerCommand = config.get('DMT_AUTODEPLOY', 'virtualPowerCommand')
    virtualBootOrderCommand = config.get('DMT_AUTODEPLOY', 'virtualBootOrderCommand')
    virtualVCenter = config.get('DMT_AUTODEPLOY', 'virtualVCenter')
    virtualVCenterCoordinator = config.get('DMT_AUTODEPLOY', 'virtualVCenterCoordinator')

    # power on check
    virtualPowerOnCommand = "sudo " + str(virtualVCenterCoordinator) + " -r \"" + str(virtualPowerCommand) + " --op poweronvm --vm " + str(vmName) + "\" -v " + str(virtualVCenter)
    logger.info("Ensuring the virtual machine with vm name " + str(vmName) + " is powered on")
    ret, output = commands.getstatusoutput(str(virtualPowerOnCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue running the command \"" + str(virtualPowerOnCommand) + "\" from the gateway. Please investigate")
        return 1

    # from network
    virtualBootFromNetworkCommand = "sudo " + str(virtualVCenterCoordinator) + " -r \"" + str(virtualBootOrderCommand) + " --vmname " + str(vmName) + " --bootWith allow:net\" -v " + str(virtualVCenter)
    logger.info("Changing Boot Order to boot from Network for Virtual VM")
    ret, output = commands.getstatusoutput(str(virtualBootFromNetworkCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue running the command \"" + str(virtualBootFromNetworkCommand) + "\" from the gateway. Please investigate")
        return 1
    checkStep(step)

    # reset
    virtualBootResetCommand = "sudo " + str(virtualVCenterCoordinator) + " -r \"" + str(virtualPowerCommand) + " --op resetvm --vm " + str(vmName) + "\" -v " + str(virtualVCenter)
    logger.info("Restarting the Virtual VM")
    ret, output = commands.getstatusoutput(str(virtualBootResetCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue run the command \"" + str(virtualBootResetCommand) + "\" from the gateway. Please investigate")
        return 1
    checkStep(step)

    # wait
    logger.info("Waiting 180 second for the vm server to boot from the Network")
    time.sleep(180)

    # from disk
    virtualBootFromDiskCommand = "sudo " + str(virtualVCenterCoordinator) + " -r \"" + str(virtualBootOrderCommand) + " --vmname " + str(vmName) + " --bootWith allow:hd,net\" -v " + str(virtualVCenter)
    logger.info("Changing Boot Order to boot from Disk for Virtual VM")
    ret, output = commands.getstatusoutput(str(virtualBootFromDiskCommand))
    if (ret != 0 or "Stack trace" in output ):
        logger.error("Issue runnning the command \"" + str(virtualBootFromDiskCommand) + "\" from the gateway. Please investigate")
        return 1
    checkStep(step)
    return 0

def yumUpdate(remoteConnection,package):
    '''
    Function used to perform a yum update on a give package on the MS
    '''
    yumUpdateCommand = "yum update -y " + str(package)
    ret = runCommand(remoteConnection, yumUpdateCommand)
    if (ret != 0):
        logger.error("Could not run the command " + str(yumUpdateCommand) + " on the MS to install the package")
        return 1
    return 0

def yumUpdateDB(remoteConnection,packageStr,lmsUploadDir,node):
    '''
    Function used to perform a yum update on a give package on a given node
    '''
    # Can we ping the server
    cmd = "ping -c1 " + str(node) + " > /dev/null"
    ret = runCommand(remoteConnection, cmd)
    if (ret == 0):
        yumUpdateCommand = str(lmsUploadDir) + "/deploy/etc/softwareUpdate/yumUpdateNodePackage.sh litp-admin " + str(node) + " \\\"" + str(packageStr) + "\\\""
        ret = runCommand(remoteConnection,yumUpdateCommand)
        if (ret != 0):
            logger.error("Could not run the command " + str(yumUpdateCommand) + " on the DB Node " + str(node) + ", to install the package(s) " + str(packageStr))
            return 1
    else:
        logger.info("Node is not pingable " + str(node))
    return 0

def yumRemoveInstall(remoteConnection,package,uploadDir,artifactName):
    '''
    Function used to install a given package using yum
    '''
    getInstalledPackage = "yum search " + str(package)
    (ret,commandOutput) = runCommandGetOutput(remoteConnection,getInstalledPackage)
    if ("No matches found" not in commandOutput):
        logger.info("Removing the pre installed package: " + str(commandOutput))
        removePackage = "yum remove -y " + str(package)
        ret = runCommand(remoteConnection,removePackage)
        if (ret != 0):
            logger.error("Could not run the command to remove the package " + removePackage + " from the MS")
            return 1
    else:
        logger.info("No " + str(package) + " pre installed on the MS. Skipping...")

    installInstCommand = "yum install -y " + uploadDir + "/" + artifactName
    ret = runCommand(remoteConnection, installInstCommand)
    if (ret != 0):
        logger.error("Could not run the command " + installInstCommand + " on the MS to install the package")
        return 1
    return 0

def yumUpdateArtifact(remoteConnection,uploadDir,artifactName):
    '''
    Function used to upgrade a given artifactName using yum
    '''
    yumCmdTimeout = int(config.get('DMT_AUTODEPLOY', 'yumCmdTimeout'))
    installInstCommand = "yum upgrade -y " + uploadDir + "/" + artifactName
    ret, command_output = remoteConnection.runCmdGetOutput(installInstCommand, None, yumCmdTimeout)
    if (ret != 0):
        logger.error("Could not run the command " + installInstCommand + " on the MS to install the package")
        return 1
    logger.info(command_output)
    return ret, command_output

def executeLitpUpgrade(remoteConnection):
    '''
    Function to Upgrade litp for DB Packages
    '''
    logger.info("Executing LITP Upgrade")
    litpUpgrade = config.get('DMT_AUTODEPLOY', 'litpUpgrade')
    logger.info("Executing command: " + str(litpUpgrade))
    (ret,commandOutput) = runCommandGetOutput(remoteConnection,litpUpgrade)
    errMsg = "Error: Upgrading LITP - " + str(commandOutput)
    if ret != 0:
        return (ret,errMsg)
    return (0,"Success")

def executeLitpPlan(remoteConnection):
    '''
    Function to create and run the litp plan
    '''
    litpCreatePlan=config.get('DMT_AUTODEPLOY', 'litpCreatePlan')
    litpRunPlan=config.get('DMT_AUTODEPLOY', 'litpRunPlan')
    logger.info("Executing command: " + str(litpCreatePlan))
    errMsg = "Error: Creating the Litp Plan"
    (ret,commandOutput) = runCommandGetOutput(remoteConnection,litpCreatePlan)
    if "no tasks were generated" not in commandOutput:
        if ret != 0:
            return (ret,errMsg)
        logger.info("Executing command: " + str(litpRunPlan))
        errMsg = "Error: Executing the Litp run plan command"
        ret = runCommand(remoteConnection,litpRunPlan)
        if ret != 0:
            return (ret,errMsg)
        litpPlanStatus=config.get('DMT_AUTODEPLOY', 'litpPlanStatus')
        count = 0
        attempts = 241
        sleepTime = 30
        while (count < attempts):
            count = count + 1
            logger.info("Check Plan Status, Executing Command \"" + str(litpPlanStatus) + "\"")
            ret,output = remoteConnection.runCmdGetOutput(litpPlanStatus)
            logger.info(str(output))
            if (ret != 0):
                errMsg="Error: Issue checking the status of the plan"
                return (ret,errMsg)
            if "Plan Status: Successful" in output:
                break
            elif "Plan Status: Failed" in output:
                errMsg="Error: Plan status is failed please investigate"
                return (1,errMsg)
            elif "Plan Status: Stopped" in output:
                errMsg="Error: Plan status is stopped please investigate"
                return (1,errMsg)
            if count == attempts:
                errMsg="Error: Plan is not completed in the given time, 2 hrs. Exiting...."
                return (1,errMsg)
            logger.info("Sleeping " + str(sleepTime) + " seconds before retry")
            time.sleep(sleepTime)
    return (0,"Success")

def buildnewPackagesDict(packageList,packageListDict):
    '''
    Function used to rebuild a dictionary of the packages dictionary if the package is included in a list given
    '''
    packageListDictSingleRepo = {}
    for package, version in packageListDict.iteritems():
        if str(package) in packageList:
            packageListDictSingleRepo[str(package)] = str(version)
    return packageListDictSingleRepo

def downloadReplacePackagesSoftwareUpdateOnly(clusterId,packageListDict,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,repoLocation):
    '''
    Function used to download the replace the given packages within the given directory
    '''
    packageList = []
    downloadPackageList = []
    installedPackageList = []
    skippedPackageList = []
    logger.info("Downloading Extra Packages")
    downloadPackageList,downloadPackageCategoryList = downloadExtraPackages(clusterId, packageListDict, packagesDir, product)
    if (downloadPackageList == 1):
        errMsg="Error: Unable to download extra Packages"
        return (1,errMsg,downloadPackageList,packageList,installedPackageList,skippedPackageList)
    errMsg = "Error: Issue Replacing the packages in the REPO"
    (ret,value,packageList,installedPackageList,skippedPackageList) = replacePackages(packageListDict,remoteConnection,mgtServer,repoLocation,downloadPackageList,packagesDir,isoRebuildlocation,isoPath,installType)
    if ret != 0:
        errMsg="Error: Replacing the packages"
        return (1,errMsg,packageList,downloadPackageList,installedPackageList,skippedPackageList)
    if value == False:
        return (0,"NO CHANGE",packageList,downloadPackageList,installedPackageList,skippedPackageList)
    return (0,"SUCCESS",packageList,downloadPackageList,installedPackageList,skippedPackageList)

def packageSkipMessage(type):
    '''
    Function to print a simple message
    '''
    logger.info("############################################################################################################")
    logger.info("############################################################################################################")
    logger.info("The " + str(type) + " Package(s) entered is already within the Repo or never delivered before. Skipping " + str(type) + " Update.")
    logger.info("############################################################################################################")
    logger.info("############################################################################################################")

def summaryOfPackagesInstalled(packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList):
    '''
    Function used to display a summary of the packages updated on the system
    '''
    skippedPkgDict = {}
    installedPkgDict = {}
    packagesInstalledSet = set(packagesToBeInstalledList)
    packagesToBeInstalledList = list(packagesInstalledSet)
    packagesToBeInstalledList = sorted(packagesToBeInstalledList)
    currentlyInstalledList = sorted(currentlyInstalledList)
    logger.info("Software Update Summary")
    logger.info("############################################################################################################")
    if packagesToBeInstalledList:
        display = False
        for item in packagesToBeInstalledList:
            if not any(item in currentPackage for currentPackage in currentlyInstalledList) and not any(item in skippedPackage for skippedPackage in allSkippedPackageList):
                display = True
                break
        if display:
            logger.info("Updated Package VS Previous Installed Package")
            logger.info("============================================================================================================")
            for item in packagesToBeInstalledList:
                if any(item in currentPackage for currentPackage in currentlyInstalledList) or any(item in skippedPackage for skippedPackage in allSkippedPackageList):
                    continue
                packageName = item.split('-')[0]
                for currentPackage in currentlyInstalledList:
                    if packageName in currentPackage:
                        currentPackageName = currentPackage
                        logger.info("Updated ::: " + str(item) + " (Previously installed ::: " + str(currentPackageName) + ")")
                        break
            logger.info("============================================================================================================")
    if allSkippedPackageList:
        logger.info("Skipped Packages (Already installed on the system or not found on the system)")
        logger.info("============================================================================================================")
        for item in allSkippedPackageList:
            logger.info(str(item))
        logger.info("============================================================================================================")
    logger.info("############################################################################################################")

def downloadReplaceBuildSummaryData(clusterId,packageListDict,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,repoLocation,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList):
    '''
    Function to call the download and replace package per repo and build summary
    '''
    toBeInstalledPackageList=[]
    installedPackageList=[]
    skippedPackageList=[]
    (ret,errMsg,packageList,toBeInstalledPackageList,installedPackageList,skippedPackageList) = downloadReplacePackagesSoftwareUpdateOnly(clusterId,packageListDict,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,repoLocation)
    if ret != 0:
        return (ret,errMsg,packageList,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList)
    if toBeInstalledPackageList:
        packagesToBeInstalledList.extend(toBeInstalledPackageList)
    if installedPackageList:
        currentlyInstalledList.extend(installedPackageList)
    if skippedPackageList:
        allSkippedPackageList.extend(skippedPackageList)
    return (ret,errMsg,packageList,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList)

def installMsDbAndModelPackages(remoteConnection,lmsUploadDir,enmRepo,nodeSrv,packageModel,packageDB,packageMs,packagesToBeInstalledList,masterUserPassword):
    '''
    Function used to Install the DB And Model Packages
    '''
    uniquePackagesToBeInstalledList = list(set(packagesToBeInstalledList))
    # Perform a yum update of the ms packages
    if packageMs:
        packages = list(set(packageMs))
        for package in packages:
            ret = yumUpdate(remoteConnection,package)
            if ret != 0:
                errMsg="Error: Unable to update the ms package using yum"

    # Perform a yum update of the model packages
    if packageModel or packageMs:
        packages = list(set(packageModel))
        for package in packages:
            ret = yumUpdate(remoteConnection,package)
            if ret != 0:
                errMsg="Error: Unable to update the model package using yum"
                return (ret,errMsg)

    if "physical" == env:
        if packageModel:
            packages = list(set(packageModel))
            ret,errMsg = installMsOnPhysical(remoteConnection,packages,nodeSrv,masterUserPassword)
            if ret != 0:
                return (ret,errMsg)

    dbRepo = config.get('DMT_AUTODEPLOY', 'dbRepo')
    # Check redhat release version
    ret, output = runCommandGetOutput(remoteConnection, " cat " + config.get('DMT_AUTODEPLOY', 'rhelVersionFile'))
    logger.info(str(output))
    if ret != 0:
        logger.info("Failed to get RHEL version, using default repo naming convention.")
    else:
        if "release" in output:
            output = str(output).split("release")[1]
            logger.info(str(output))
        if " 7." in output:
            dbRepo = config.get('DMT_AUTODEPLOY', 'dbRepoRhel7')
        if " 8." in output:
            dbRepo = config.get('DMT_AUTODEPLOY', 'dbRepoRhel8')
    if packageDB:
        for dbPackage in packageDB:
            for tobeInstalledDbPackage in uniquePackagesToBeInstalledList:
                if dbPackage in tobeInstalledDbPackage:
                    cmd = lmsUploadDir + "/deploy/bin/modelUpdate.bsh -p " + str(tobeInstalledDbPackage) + " -r " + str(enmRepo) + "/" + dbRepo
                    errMsg = "Error, with the db package, " + str(tobeInstalledDbPackage) + ", issue with the check for new db script"
                    ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
                    if ret != 0:
                        errMsg="Error: Unable to update the db package using yum"
                        return (ret,errMsg)
        #Perform update of the DB packages on the DB nodes
        (ret,errMsg) = executeLitpUpgrade(remoteConnection)
        if ret != 0:
            return (ret,errMsg)
    if "physical" not in env:
        (ret,errMsg) = executeLitpPlan(remoteConnection)
        if ret != 0:
            return (ret,errMsg)
        return (0,'SUCCESS')
    else:
        return (0,'SUCCESS')

def installMsOnPhysical(remoteConnection, packages,nodeSrv,masterUserPassword):
    for package in packages:
        createModelLayoutScript = config.get('DMT_AUTODEPLOY', 'createModelLayoutScript')
        cmd = createModelLayoutScript
        ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
        if ret != 0:
           errMsg="Error: Unable to Model Directory Structure"
           return (ret,errMsg)
        cmd = config.get('DMT_AUTODEPLOY', 'scriptToFindOnlineVersant')
        logger.info("Getting DB cluster with ONLINE Versant service")
        (ret, dbServer) = remoteConnection.runCmdGetOutput(cmd,"tty-ssh")
        if ret != 0:
            errMsg="Could not find online Versant in DB servers"
            return (ret,errMsg)
        for srv in nodeSrv:
           if srv.server.hostname in dbServer:
               dbServerWithOnlineVersant = str(srv.server.hostname)
               break
        logger.info("Connecting to DB cluster with ONLINE Versant at: " + dbServerWithOnlineVersant)
        litpUsername = config.get('DMT_AUTODEPLOY', 'litpUsername')
        loginToDbRunCommand = config.get('DMT_AUTODEPLOY', 'loginToDbRunCommand')
        invokeMdtScript = config.get('DMT_AUTODEPLOY', 'invokeMdtScript')
        cmd = loginToDbRunCommand + " " + dbServerWithOnlineVersant + " " + litpUsername + " " + masterUserPassword + " " + invokeMdtScript
        logger.info("Running invokeMDT script, this may take up to 10 minutes")
        ret = remoteConnection.runCmdSimple(cmd)
        if (ret != 0):
            errMsg="Error: Error encountered while running invokeMDT.sh script"
            return (ret,errMsg)
        else:
            modelJarFilesDir = config.get('DMT_AUTODEPLOY', 'modelJarFilesDir')
            logger.info("Removing jar files from " + modelJarFilesDir)
            cmd = "rm -rf " + modelJarFilesDir
            remoteConnection.runCmdSimple(cmd)
    return (0,"OK")

def processPackageInfo(enmRepo,type,categoryPackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList, rhelType):
    '''
    Function used to gather the package information
    '''

    repoLocation = str(enmRepo) + "/" + config.get('DMT_AUTODEPLOY', str(type) + 'Repo' + str(rhelType))
    packageListDictCategory = buildnewPackagesDict(categoryPackageList,packageListDict)
    (ret,errMsg,packageCategory,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = downloadReplaceBuildSummaryData(clusterId,packageListDictCategory,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,repoLocation,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList)
    if errMsg == "NO CHANGE":
        packageSkipMessage(str(type))
    return (ret,errMsg,packageCategory,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList)

def deploySoftwareUpdateOnly(remoteConnection,clusterId,mgtServer,packageList,commandType,packagesDir,product,fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment,tmpArea,isoRebuildlocation,installType,deployScriptVersion,deployRelease,scriptFile,ignoreHa):
    '''
    Function used to install the software on a deployment only
    '''
    # Open the ssh connection to the specified server
    isoPath = ""
    packageListDict = buildPackageDict(packageList)
    currentlyInstalledList=[]
    packagesToBeInstalledList=[]
    toBeInstalledPackageList=[]
    allSkippedPackageList=[]
    installedPackageList=[]
    packageListModel = []
    packageListDB = []
    packageModel = []
    packageDB = []
    packageMs = []
    packageService = []
    packageScripting = []
    packageStreaming = []
    packageEvents = []
    enmRepo = config.get('DMT_AUTODEPLOY', 'enmRepo')
    repoData = config.get('DMT_AUTODEPLOY', 'repoData')
    serviceRepo = config.get('DMT_AUTODEPLOY', 'serviceRepo')
    msRepo = config.get('DMT_AUTODEPLOY', 'msRepo')
    scriptingRepo = config.get('DMT_AUTODEPLOY', 'scriptingRepo')
    streamingRepo = config.get('DMT_AUTODEPLOY', 'streamingRepo')
    eventsRepo = config.get('DMT_AUTODEPLOY', 'eventsRepo')
    rhelType = ""

    # Check redhat release version
    ret, output = runCommandGetOutput(remoteConnection, " cat " + config.get('DMT_AUTODEPLOY', 'rhelVersionFile'))
    logger.info(str(output))
    if ret != 0:
        logger.info("Failed to get RHEL version, using default repo naming convention.")
    else:
        if "release" in output:
            output = str(output).split("release")[1]
            logger.info(str(output))
        if " 7." in output:
            serviceRepo = config.get('DMT_AUTODEPLOY', 'serviceRepoRhel7')
            msRepo = config.get('DMT_AUTODEPLOY', 'msRepoRhel7')
            scriptingRepo = config.get('DMT_AUTODEPLOY', 'scriptingRepoRhel7')
            streamingRepo = config.get('DMT_AUTODEPLOY', 'streamingRepoRhel7')
            eventsRepo = config.get('DMT_AUTODEPLOY', 'eventsRepoRhel7')
            rhelType = "Rhel7"
        if " 8." in output:
            serviceRepo = config.get('DMT_AUTODEPLOY', 'serviceRepoRhel8')
            msRepo = config.get('DMT_AUTODEPLOY', 'msRepoRhel8')
            scriptingRepo = config.get('DMT_AUTODEPLOY', 'scriptingRepoRhel8')
            streamingRepo = config.get('DMT_AUTODEPLOY', 'streamingRepoRhel8')
            eventsRepo = config.get('DMT_AUTODEPLOY', 'eventsRepoRhel8')
            rhelType = "Rhel8"
    cluster = Cluster.objects.get(id=clusterId)
    (ret,nodeSrv) = getListOfNodesInDeployment(cluster)
    if ret != 0:
        errMsg="Could not get the node data from the deployment"
        return (ret,errMsg)

    (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
    if (ret != 0):
        errMsg="Error: Could not create ssh connection to MS during"
        return (ret,errMsg)

    # Set the lmsUploadDir by checking does the software directory exist already if it does use it
    (ret, lmsUploadDir) = setUploadDirectory(remoteConnection,installType,deployScriptVersion)
    if (ret != 0):
        errMsg="Could not set the Upload Directory for the artifacts"
        return (ret,errMsg)

    logger.info("Uploading Deployment Scripts to management server")

    ret = deployScriptsToMgtServer(remoteConnection, mgtServer, deployScriptVersion, deployRelease, lmsUploadDir,tmpArea,product,scriptFile)
    if ret != 0:
        errMsg="Could not Upload Deployment Scripts"
        return (ret,errMsg)

    ret,modelPackageList,servicePackageList,dbPackageList,scriptPackageList,msPackageList,eventsPackageList,streamingPackageList,allSkippedPackageList = checkCategory(packageListDict,allSkippedPackageList)
    if (ret != 0):
        errMsg="Error: Unable to check what category the package is from"
        return (ret,errMsg)

    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    enmHealthCheckSystemServices = config.get('DMT_AUTODEPLOY', 'enmHealthCheckSystemServices')
    cmd = str(enmInstDir) + str(enmHealthCheckSystemServices)
    ret = executeLoopServiceCheck(remoteConnection,cmd)
    if ret != 0:
        return int(ret,"Error not all Services are online")

    initial_wait = 1
    interval = 30
    retries = 60
    ret = executeLoopServiceGroupCheck(remoteConnection,lmsUploadDir,initial_wait,interval,retries)
    if ret != 0:
        return (ret,"Issue with the Service Groups")

    if "cloud" in environment:
        serviceRepoBackup = config.get('DMT_AUTODEPLOY', 'serviceRepoBackup')
        for item in str(serviceRepo), str(scriptingRepo), str(streamingRepo), str(eventsRepo):
            ret = remoteConnection.runCmd("mkdir -p " + str(serviceRepoBackup) + "/" + str(item))
            if ret != 0:
                return (ret,"Issue with the creation of the " + str(serviceRepoBackup) + "/" + str(item) + " directory")
            ret = copyContent(remoteConnection,str(enmRepo) + "/" + str(item) + "/" + str(repoData),serviceRepoBackup + "/" + str(item))
            if ret != 0:
                return (ret,"Issue with the backup of the service repodate directory")

    # Process the MS package(s)
    if msPackageList:
        (ret,errMsg,packageMs,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = processPackageInfo(enmRepo,'ms',msPackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList,rhelType)
        if ret != 0:
            return (ret,errMsg)

    # Process the Model package(s)
    if modelPackageList:
        (ret,errMsg,packageModel,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = processPackageInfo(enmRepo,'model',modelPackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList,rhelType)
        if ret != 0:
            return (ret,errMsg)

    if environment == "cloud":
        # Process the DB package(s)
        if dbPackageList:
            (ret,errMsg,packageDB,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = processPackageInfo(enmRepo,'db',dbPackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList,rhelType)
            if ret != 0:
                return (ret,errMsg)

    # Install the DB, MS And Model Packages
    if packageModel or packageDB or packageMs:
        if "physical" in environment:
            ret = deployModelScriptsToMgtServer(remoteConnection, mgtServer, lmsUploadDir, tmpArea, product)
            if ret != 0:
                errMsg="Could not Upload Model Scripts"
                return (ret,errMsg)
        (ret,errMsg) = installMsDbAndModelPackages(remoteConnection,lmsUploadDir,enmRepo,nodeSrv,packageModel,packageDB,packageMs,packagesToBeInstalledList,masterUserPassword)
        if ret != 0:
            return (ret,errMsg)

    # Process the Service Packages
    if servicePackageList:
        (ret,errMsg,packageService,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = processPackageInfo(enmRepo,'service',servicePackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList,rhelType)
        if ret != 0:
            return (ret,errMsg)

    # Process the Scripting Packages
    if scriptPackageList:
        (ret,errMsg,packageScripting,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = processPackageInfo(enmRepo,'scripting',scriptPackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList,rhelType)
        if ret != 0:
            return (ret,errMsg)

    # Process the Events Packages
    if eventsPackageList:
        (ret,errMsg,packageEvents,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = processPackageInfo(enmRepo,'events',eventsPackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList,rhelType)
        if ret != 0:
            return (ret,errMsg)

    # Process the Streaming Packages
    if streamingPackageList:
        (ret,errMsg,packageStreaming,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList) = processPackageInfo(enmRepo,'streaming',streamingPackageList,packageListDict,clusterId,packagesDir,product,remoteConnection,isoRebuildlocation,isoPath,installType,mgtServer,packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList,rhelType)
        if ret != 0:
            return (ret,errMsg)

    # Install the Service Packages
    if packageService or packageScripting or packageStreaming or packageEvents:
        allServicePackages = packageService + packageScripting + packageStreaming + packageEvents
        ret = redeployVMServices(remoteConnection,allServicePackages,lmsUploadDir,commandType,ignoreHa)
        if ret != 0:
            errMsg="Error: Issue with the redeploy of the VM"
            return (ret,errMsg)

    if "cloud" in environment:
        # Copy the repo xml file back, so the update can run again on the same server
        for item in str(serviceRepo), str(scriptingRepo), str(streamingRepo), str(eventsRepo):
            ret = copyContent(remoteConnection,serviceRepoBackup + "/" + str(item) + "/" + str(repoData),str(enmRepo) + "/" + str(item))
            if ret != 0:
                return (ret,"Issue with the restore, of the backup service repodata directory")
            ret = remoteConnection.runCmd("rm -rf " + serviceRepoBackup + "/" + str(item))
            if ret != 0:
                return (ret,"Issue with the removal of the backup of the service repodata directory")
    summaryOfPackagesInstalled(packagesToBeInstalledList,currentlyInstalledList,allSkippedPackageList)
    return (0,"SUCCESS")

class downloadToMgmtServerThread (threading.Thread):
    def __init__(self, threadID, name, *args):
        self._stop = threading.Event()
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.args = args
    def run(self):
        remoteConnection = self.args[0]
        mgtServer = self.args[1]
        artifact = self.args[2]
        lmsUploadDir = self.args[3]
        tmpArea = self.args[4]
        try:
            logger.info("Starting Thread " +self.name)
            if self.name.startswith('nas-'):
                returnCode = dmt.utils.downloadTarGzToMgtServer(remoteConnection, mgtServer, artifact, lmsUploadDir, tmpArea)
            else:
                returnCode = downloadToMgtServer(self.args[0],self.args[1],self.args[2], self.args[3],self.args[4],self.args[5],self.args[6])
            if returnCode != 0:
                raise Exception("Thread " + self.name + " could not download the ISO to the MS")
            logger.info("Exiting Thread " +self.name)
        except Exception as e:
            logger.error("Interrupting main program from thread....." + str(e))
            thread.interrupt_main()

def cleanUpAfterSuccessfullInitialInstall(remoteConnection,mgtServer,lmsUploadDir,softwareDir,mediaArtifactList):
    '''
    Function used to clean out the /var/tmp directory of all large media files to free up space
    '''
    baseSoftwareDir = os.path.dirname(softwareDir)
    if (remoteConnection.runCmd("ls " + str(baseSoftwareDir)) == 0):
        if (remoteConnection.runCmd("ls " + str(softwareDir)) != 0):
            ret = remoteConnection.runCmd("mkdir " + str(softwareDir))
            if ret != 0:
                message = "Issue with the creation of " + str(softwareDir)
                return (ret,message)
        for media in mediaArtifactList:
            if (remoteConnection.runCmd("ls " + str(lmsUploadDir) + "/" + str(media)) == 0):
                logger.info("Moving " + str(lmsUploadDir) + "/" + str(media) + " to the " + str(softwareDir) + "/" + str(media))
                ret = remoteConnection.runCmd("\mv " + str(lmsUploadDir) + "/" + str(media) + " " + str(softwareDir) + "/" + str(media))
                if ret != 0:
                    message = "Issue with the moving of the media " + str(media) + " to the software directory"
                    return (ret,message)
                logger.info("Removing Media MD5 file if it exists (" + str(media) + ".md5)")
                ret = remoteConnection.runCmd("rm " + str(lmsUploadDir) + "/" + str(media) + ".md5")
            else:
                logger.info("Skipping the Moving of " + str(media) + " Not existing within " + str(lmsUploadDir))
        logger.info("Removing deployment script related files for " + str(lmsUploadDir))
        ret = remoteConnection.runCmd("rm -rf " + str(lmsUploadDir) + "/deploy; rm " + str(lmsUploadDir) + "/DeploymentScripts-*")
    else:
        message = "The " + str(baseSoftwareDir) + " directory does not exist skipping moving of the media file from /var/tmp"
        return (1,message)
    return (0,"SUCCESS")

def downloadAllToMgmtServer(remoteConnection, mgtServer, productSet, litpIsoName, isoName, lmsUploadDir, tmpArea, litpIsoUrl, litpHubIsoUrl, osRhel6PatchFileName, osRhel6PatchFileUrl, osRhel6PatchFileHubUrl, osRhel7PatchFileName, osRhel7PatchFileUrl, osRhel7PatchFileHubUrl, osRhel79PatchFileName, osRhel79PatchFileUrl, osRhel79PatchFileHubUrl, osRhel88PatchFileName, osRhel88PatchFileUrl, osRhel88PatchFileHubUrl, isoUrl, hubIsoUrl, skipLitpInstall, skipPatchInstall, skipEnmInstall, enmInstRHEL7Patch, enmInstRHEL79Patch, enmInstRHEL88Patch, enmInstVersion, osIsoName, osIsoVersion, osIsoUrl, osIsoHubUrl, osMedia, osIsoName8, osIsoVersion8, osIsoUrl8, osIsoHubUrl8, osMedia8, nasConfig, nasRhelPatch):
    # create array to hold thread ids of downloaded artifacts
    artifacts = [ ]

    # Create new threads
    # LITP ISO
    litpThread = "SKIP"
    if "YES" not in str(skipLitpInstall):
        litpThread = "litp-1"
    thread1 = downloadToMgmtServerThread(1, str(litpThread), remoteConnection, mgtServer, litpIsoName, lmsUploadDir,tmpArea,litpIsoUrl,litpHubIsoUrl)
    thread1.daemon= True
    artifacts.append(thread1)

    # ENM ISO
    enmThread = "SKIP"
    if "YES" not in str(skipEnmInstall) or "YES" not in str(skipPatchInstall):
        enmThread = "enm-2"
    thread2 = downloadToMgmtServerThread(2, str(enmThread), remoteConnection, mgtServer, isoName, lmsUploadDir,tmpArea,isoUrl,hubIsoUrl)
    thread2.daemon = True
    artifacts.append(thread2)

    # OS RHEL Patches
    patch6Thread = "ospatch-3"
    patch7Thread = "ospatch-4"
    patch79Thread = "ospatch-5"
    patch88Thread= "ospatch-6"
    if "NO" not in str(skipPatchInstall):
        if "RHEL6" in str(skipPatchInstall):
            patch6Thread = "SKIP"
        elif "RHEL79" in str(skipPatchInstall):
            patch79Thread = "SKIP"
        elif "RHEL7" in str(skipPatchInstall):
            patch7Thread = "SKIP"
        elif "RHEL88" in str(skipPatchInstall):
            patch88Thread = "SKIP"
        else:
            patch6Thread = "SKIP"
            patch7Thread = "SKIP"
            patch79Thread = "SKIP"
            patch88Thread = "SKIP"

    # RHEL 6 OS Patch
    if (osRhel6PatchFileName != ""):
        thread3 = downloadToMgmtServerThread(3, str(patch6Thread), remoteConnection, mgtServer, osRhel6PatchFileName, lmsUploadDir,tmpArea, osRhel6PatchFileUrl, osRhel6PatchFileHubUrl)
        thread3.daemon = True
        artifacts.append(thread3)
    # RHEL 7 OS Patch
    if (osRhel7PatchFileName != "" and (LooseVersion(enmInstRHEL7Patch) <= LooseVersion(enmInstVersion))):
        thread4 = downloadToMgmtServerThread(4, str(patch7Thread), remoteConnection, mgtServer, osRhel7PatchFileName, lmsUploadDir,tmpArea, osRhel7PatchFileUrl, osRhel7PatchFileHubUrl)
        thread4.daemon = True
        artifacts.append(thread4)
    # RHEL 7.9 OS Patch
    if (osRhel79PatchFileName != "" and (LooseVersion(enmInstRHEL79Patch) <= LooseVersion(enmInstVersion))):
        thread5 = downloadToMgmtServerThread(5, str(patch79Thread), remoteConnection, mgtServer, osRhel79PatchFileName, lmsUploadDir,tmpArea, osRhel79PatchFileUrl, osRhel79PatchFileHubUrl)
        thread5.daemon = True
        artifacts.append(thread5)
    # RHEL 8.8 OS Patch
    if (osRhel88PatchFileName != "" and (LooseVersion(enmInstRHEL88Patch) <= LooseVersion(enmInstVersion))):
        thread6 = downloadToMgmtServerThread(6, str(patch88Thread), remoteConnection, mgtServer, osRhel88PatchFileName, lmsUploadDir,tmpArea, osRhel88PatchFileUrl, osRhel88PatchFileHubUrl)
        thread6.daemon = True
        artifacts.append(thread6)

    # First OS Media
    if osMedia != None:
        thread7 = downloadToMgmtServerThread(7, "os-7", remoteConnection, mgtServer, osIsoName, lmsUploadDir, tmpArea, osIsoUrl, osIsoHubUrl)
        thread7.daemon = True
        artifacts.append(thread7)

    # Second OS Media (8.8 this should only be a thing for now before completely uplifted from 7.9 to 8.8)
    if osMedia8 != None:
        thread8 = downloadToMgmtServerThread(8, "os-8", remoteConnection, mgtServer, osIsoName8, lmsUploadDir, tmpArea, osIsoUrl8, osIsoHubUrl8)
        thread8.daemon = True
        artifacts.append(thread8)

    if nasConfig is not None:
        thread9 = downloadToMgmtServerThread(9, "nas-config", remoteConnection, mgtServer, nasConfig, lmsUploadDir, tmpArea, osIsoUrl, osIsoHubUrl)
        thread9.daemon = True
        artifacts.append(thread9)

    if nasRhelPatch is not None:
        thread10 = downloadToMgmtServerThread(10, "nas-rhel-patch", remoteConnection, mgtServer, nasRhelPatch, lmsUploadDir, tmpArea, osIsoUrl, osIsoHubUrl)
        thread10.daemon = True
        artifacts.append(thread10)

    # Start threads if required
    if thread1.getName() != "SKIP":
        thread1.start()

    if thread2.getName() != "SKIP":
        thread2.start()

    if (osRhel6PatchFileName != ""):
        if thread3.getName() != "SKIP":
            thread3.start()

    if (osRhel7PatchFileName != "" and (LooseVersion(enmInstRHEL7Patch) <= LooseVersion(enmInstVersion))):
        if thread4.getName() != "SKIP":
            thread4.start()

    if (osRhel79PatchFileName != "" and (LooseVersion(enmInstRHEL79Patch) <= LooseVersion(enmInstVersion))):
        if thread5.getName() != "SKIP":
            thread5.start()

    if (osRhel88PatchFileName != "" and (LooseVersion(enmInstRHEL88Patch) <= LooseVersion(enmInstVersion))):
        if thread6.getName() != "SKIP":
            thread6.start()

    if osMedia != None:
        thread7.start()

    if osMedia8 != None:
        thread8.start()

    if nasConfig is not None:
        thread9.start()

    if nasRhelPatch is not None:
        thread10.start()
    return artifacts

def getSedVersion(cfgTemplate):
    '''
    Function to get the sed version
    '''
    if cfgTemplate == "MASTER":
        sedVersion = dmt.utils.getVirtualMasterSedVersion()
    elif "http" in cfgTemplate:
        logger.info("The user has inputted their own SED unable to compare this version it needs to be officially delivered to the Portal.")
        logger.info("Continuing with the installation...")
        return (0,"CONTINUE")
    else:
        sedVersion = cfgTemplate
    return (0,sedVersion)

def getXmlFileInfo(xmlFile):
    '''
    Function to get back the deployment description type (slice/official) and the deployment description file name
    '''
    if "::" in xmlFile:
        ddType = "slice"
        ddFile = xmlFile.split('::')[1]
    elif "http" in xmlFile:
        logger.info("The user has inputted their own Deployment description xml file, only valid delivered version can be validated.")
        logger.info("Continuing with the installation...")
        return (0,"CONTINUE","CONTINUE")
    else:
        ddType = "official"
        ddFile = xmlFile
    return (0,ddType,ddFile)

def getPackageInformation(packageList,searchPackage,isoName,isoVersion):
    '''
    Function used to get the version of a given package either from the deployPackage parameter or from the iso
    '''
    depDescVersion = None
    if packageList:
        if searchPackage in packageList:
            (package,version) = findPackageInPackageList(packageList,searchPackage)
            if package != None:
                category = None
                if "__" in version:
                    version = version.split("__")[0]
                if version.lower() is "latest":
                    version = "None"
                    completeArtifactURL = "None"
                    latest = "yes"
                elif "http" in version.lower():
                    logger.info("The user has inputted their own Deployment description package, only delivered versions can be validated.")
                    logger.info("Continuing with the installation...")
                    return (0,"CONTINUE")
                else:
                    completeArtifactURL = "None"
                    latest = "no"
                packageObject = dmt.cloud.getPackageObject(package,version,completeArtifactURL,latest)
                depDescVersion = packageObject.version
    # If we didn't get a deployment description version we need to find the version on the ISO
    if depDescVersion == None:
        isoName = isoName.split('-')[0]
        isoObj = ISObuild.objects.get(artifactId=isoName, version=isoVersion)
        mediaArtifactObj = ISObuildMapping.objects.get(iso=isoObj,package_revision__package__name=searchPackage)
        depDescVersion = mediaArtifactObj.package_revision.version
    return (0,depDescVersion)

def runVerifyServiceVMs(ddFile,searchPackage,ddType,depDescVersion,sedVersion,clusterId):
    '''
    Function to execute the service vm verify against the deployment description and SED
    '''
    cifwkPortalUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    logger.info("Validating Deployment Description(DD) xml file, " + ddFile + ", within " + searchPackage + "(" + str(ddType) + ") version " + str(depDescVersion) + " against SED File Version " + str(sedVersion))
    url = str(cifwkPortalUrl) + "/api/deployment/verify/" + str(clusterId) + "/sedVersion/" + str(sedVersion) + "/?depDescFileName=" + str(ddFile) + "&depDescType=" + str(ddType) + "&depDescVersion=" + str(depDescVersion)
    (ret,dataList) = dmt.utils.getTheResponseFromARestCall(url)
    if ret != 0:
         message = "Unable to execute Rest Call to verify the deployment description and SED file against the Service VM within the deployment"
         return (1,message)
    if dataList:
        for data in dataList:
            if "error:" in data.lower():
                logger.error(data)
                ret = 1
            else:
                logger.info(data)
    if ret != 0:
         message = "There was errors found between the deployment description and the generated SED from the deployment.\nPlease investigate before proceeding any further with the installation"
         return (1,message)
    return (0,"SUCCESS")

def getDeploymentDescriptionInfo(xmlFile):
    '''
    Getting Deployment Description Information, using the given xmlFile
    '''
    xmlFileName = None
    ddType = None
    if "http" in xmlFile:
        logger.info("The user has inputted their own Deployment description xml file, only valid delivered version can be validated.")
        logger.info("Continuing with the installation...")
        return (0,"CONTINUE","CONTINUE")

    if '::' in xmlFile:
        (ddType,xmlFileName) = xmlFile.split('::')
        logger.info("Deployment Description xml file: " + xmlFileName)
        if DeploymentDescription.objects.filter(auto_deployment=xmlFileName, dd_type__dd_type__endswith="slice").exists():
            deploymentDescriptionObj = DeploymentDescription.objects.only('name', 'dd_type__dd_type').values('name', 'dd_type__dd_type').filter(auto_deployment=xmlFileName, dd_type__dd_type__endswith="slice")[0]
            logger.info("Deployment Description Type: " + deploymentDescriptionObj['dd_type__dd_type'])
            return (0, deploymentDescriptionObj['dd_type__dd_type'], deploymentDescriptionObj['name'])
    else:
        ddType = "rpm"
        (junk, xmlFileName) = xmlFile.rsplit('/', 1)
        logger.info("Deployment Description xml file: " + xmlFileName)
        if DeploymentDescription.objects.filter(auto_deployment=xmlFileName, dd_type__dd_type=ddType).exists():
            deploymentDescriptionObj = DeploymentDescription.objects.only('name').values('name').filter(auto_deployment=xmlFileName)[0]
            logger.info("Deployment Description Type: " + ddType)
            return (0, ddType, deploymentDescriptionObj['name'])
    logger.info("Deployment Description Type: " + ddType)
    return (1,"Unable find deployment description in the CI Portal database, Exiting..","CONTINUE")


def verifySEDvsDeploymentDescription(clusterId,cfgTemplate,xmlFile,packageList,isoName,isoVersion):
    '''
    Function used to verify the inputted SED against the deployment description file to be used
    '''
    logger.info("Gathering Info to validate the deployment description")
    searchPackage = config.get('DMT_AUTODEPLOY', 'deploymentTemplatePackage')
    # Get the SED Version
    (ret,sedVersion) = getSedVersion(cfgTemplate)
    if ret != 0:
        message = "Unable to get the sed version.. Exiting.."
        return (ret,message)
    if sedVersion == "CONTINUE":
        return (0,"SUCCESS")
    # Get the XMLFile
    try:
        (ret,ddType,ddFile) = getDeploymentDescriptionInfo(xmlFile)
        if ret != 0:
            return (ret,ddType)
        if ddType == "CONTINUE":
            return (0,"SUCCESS")
    except Exception as e:
        return (1, "Unable to get the deployment description information: " + str(e))
    # Get the DD package version
    (ret,depDescVersion) = getPackageInformation(packageList,searchPackage,isoName,isoVersion)
    if ret != 0:
        message = "Unable to get the deployment description package information.. Exiting.."
        return (ret,message)
    if depDescVersion == "CONTINUE":
        return (0,"SUCCESS")
    # Execute the verify functionality
    (ret,message) = runVerifyServiceVMs(ddFile,searchPackage,ddType,depDescVersion,sedVersion,clusterId)
    return (ret,message)

def setUploadDirectory(remoteConnection,installType,deployScriptVersion):
    '''
    Function used to set the upload directory for the media artifacts by checking does the /software directory exist if so then use it else revert to /var
    for older initial install system since 16.6::16.6.64
    '''
    softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    baseSoftwareDir = os.path.dirname(softwareDir)
    cmd = "ls " + str(baseSoftwareDir)
    ret = runCommand(remoteConnection,cmd)
    if ret != 0:
        if ( installType == "IGNORE" or installType == "initial_install" or LooseVersion(deployScriptVersion) < LooseVersion(config.get('DMT_AUTODEPLOY', 'deploymentScriptVersionNum'))):
            lmsUploadDir = config.get('DMT_AUTODEPLOY', 'lmsUploadDir')
        else:
            lmsUploadDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    else:
        lmsUploadDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    return (0, lmsUploadDir)


def getCalculatedCrackedIsoWeight(isoName, isoVersion, listOfPackages):
    '''
    Function will calculate and predict future cracked ISO weight so the proper partitian can be found for physical download and manipulation.
    '''
    try:
        bufferSize = 1000000000
        totalPack = totalDepl = 0
        iso = ISObuild.objects.only('id', 'size').values('id', 'size').get(version=isoVersion, mediaArtifact__name=isoName)
        totalIsoWeight = int(iso['size'])
        packageListDict = buildPackageDict(listOfPackages)
        for packageName, packageVersion in packageListDict.items():
            totalPack += int(getTotalISOPackageWeight(packageName, iso['id']))
            totalDepl += int(getTotalDeployPackageWeight(packageName, packageVersion))
        totalIsoWeight = int(totalIsoWeight) - int(totalPack) + int(totalDepl) + int(bufferSize)
        logger.info("Size of cracked ISO with buffer of 1GB equals to: " + str(totalIsoWeight))
        return totalIsoWeight
    except Exception as e:
        logger.error("Error: There was an issue with getting the Calculated Cracked ISO Weight: " + str(e))
    return None


def getTotalISOPackageWeight(packageName, isoId):
    '''
    Function used to find out a weight of packages within original ISO.
    '''
    isoPackageWeight = 0
    try:
        isoPackageWeight = ISObuildMapping.objects.only('package_revision__size').values('package_revision__size').get(iso__id=isoId, package_revision__artifactId=packageName)
        isoPackageWeight = int(isoPackageWeight['package_revision__size'])
    except ISObuildMapping.DoesNotExist:
        logger.info("Package " + str(packageName) + " not found in ENM ISO")
    return isoPackageWeight


def getArtifactSizeFromUrl(packageVersion):
    '''
    Function used to execute curl -sI0 command to find out size of Package from upload area.
    '''
    result = None
    try:
        cmd = "curl -sI0 '" + str(packageVersion) + "'" + " | grep 'Content-Length'"
        result = subprocess.Popen(cmd, stdout=PIPE, shell=True).communicate()[0]
        result = result.split(":")[1].strip()
    except Exception as e:
        logger.error("Error: There was an issue with getting the size, using " + str(packageVersion) + ": " + str(e))
    return result


def getTotalDeployPackageWeight(packageName, packageVersion):
    '''
    Function used to find out a weight of Deployment packages provided by --depoloyPackage command.
    '''
    deployPackageWeight = 0
    logger.info("Getting size for package: " + str(packageName))
    if packageVersion.lower() == "latest":
        packageObject = dmt.cloud.getPackageObject(packageName, packageVersion, "None", "yes")
        packageVersion = packageObject.version
    if "http" in packageVersion.lower():
        deployPackageWeight = getArtifactSizeFromUrl(packageVersion.split("__")[0])
        return deployPackageWeight
    deployPackageWeight = PackageRevision.objects.only('id', 'size').values('id', 'size').get(package__name=packageName, version=packageVersion)
    return int(deployPackageWeight['size'])


def findRebuildLocation(remoteConnection, totalIsoWeight):
    '''
    Function used to find out available space in management server to store ENM ISO content for cracking.
    '''
    findAvailabilityCmd = "df -B1"
    fileSystem = None
    (ret, commandOutput) = runCommandGetOutput(remoteConnection, findAvailabilityCmd, "tty")
    commandOutputList = commandOutput.split('\n')
    try:
        for fileSystemObj in commandOutputList[1:-1]:
            fileSystemValuesList = fileSystemObj.split(" ")
            fileSystemValuesList = filter(None, fileSystemValuesList)
            if len(fileSystemValuesList) > 2:
                if int(fileSystemValuesList[-3]) > int(totalIsoWeight):
                    fileSystem = str(fileSystemValuesList[-1])
                    if str(fileSystem.strip()) == "/software":
                        doubledIsoWeight = totalIsoWeight + totalIsoWeight
                        if int(fileSystemValuesList[-3]) > int(doubledIsoWeight):
                            break
                        continue
                    break
    except Exception as e:
        logger.error("Error: There was an issue with connection to Management Server " + str(e))
    logger.info("Filesystem directory for cracking ISO is: " + str(fileSystem))
    return str(fileSystem)

def uploadLunExpansionScriptToMS(mgtServer, lmsUploadDir):
    try:
        logger.info("Uploading Lun Expansion file")
        cfgName = config.get('DMT_AUTODEPLOY', 'lunExpansionCheckScript')
        logger.info('location of lun in local dir: '+str(cfgName))
        ret = dmt.utils.paramikoSftp(
                mgtServer.server.hostname + "." + mgtServer.server.domain_name,
                "root",
                lmsUploadDir + "/" + cfgName.split('/')[-1],
                cfgName,
                int(config.get('DMT_AUTODEPLOY', 'port')),
                config.get('DMT_AUTODEPLOY', 'key'),
                "put")
        if (ret != 0):
            return 1, "Could not upload LunExpansionCheck script to MS"
        logger.info("Copied " + cfgName + " to node")
        return ret, lmsUploadDir + "/" + cfgName.split('/')[-1]
    except:
        return 1, 'Exception raised: Not able to upload LunExpansionCheck script to MS'

def setFileLookupServiceTrue(remoteConnection, mgtServer):
    '''
    Function used to stop writing to the Postgres File Lookup Service (FLS) database by changing the stopAllOperationOnFlsDB PIB parameter to true.
    '''
    logger.info("Disabling FLS")
    cmdBackup = "/bin/bash /ericsson/fls_postgres/db/fls/fls_maintenance.sh --action backup_fls_snapshot"
    cmdSetAllOperationOnFlsDB = "/ericsson/pib-scripts/etc/config.py update --app_server_address pmserv-1-internal:8080 --name=stopAllOperationOnFlsDB --value=true"
    logger.info("Setting File Lookup Service to true using command: " + str(cmdSetAllOperationOnFlsDB))
    return_code = runCommand(remoteConnection, cmdSetAllOperationOnFlsDB)
    if(return_code != 0):
        logger.error("Error in Execution of: " + str(cmdSetAllOperationOnFlsDB))
        return return_code
    status, return_code = jumpToNodePostgreSQL(remoteConnection, cmdBackup, mgtServer)
    if (return_code != 0):
        logger.error(status)
        return return_code
    return return_code

def setFileLookupServiceFalse(remoteConnection, drop, mgtServer):
    '''
    Function used to start writing to the Postgress File Lookup Service (FLS) database by changing the stopAllOperationOnFlsDB PIB parameter to false.
    '''
    logger.info("Enabling FLS")
    oldflsScriptPath = "/ericsson/fls_postgres/db/fls/fls_restore.sh"
    flsScriptPath = "/ericsson/tor/no_rollback/fls/fls_restore.sh"
    if LooseVersion(drop) >= LooseVersion("18.03"):
        cmdBackup = "/bin/bash " + str(oldflsScriptPath)
    else:
        cmdBackup = "su - postgres -c " + str(oldflsScriptPath)

    fileCheck = "[ -f " + str(flsScriptPath) + " ]"
    status, fileCheckReturnCode = jumpToNodePostgreSQL(remoteConnection, fileCheck, mgtServer)
    if (fileCheckReturnCode == 0):
        cmdBackup = "/bin/bash " + str(flsScriptPath)

    logger.info("Executing fls_restore.sh: " + str(cmdBackup))

    status, return_code = jumpToNodePostgreSQL(remoteConnection, cmdBackup, mgtServer)
    if (return_code != 0):
        logger.error("Error in Execution of: " + str(status))
        return return_code

    if (fileCheckReturnCode == 0):
        logger.info("Removing: " + str(flsScriptPath))
        removeFile = "/bin/rm -f " + str(flsScriptPath)
        status, return_code = jumpToNodePostgreSQL(remoteConnection, removeFile, mgtServer)

    cmdSetAllOperationOnFlsDB = "/ericsson/pib-scripts/etc/config.py update --app_server_address pmserv-1-internal:8080 --name=stopAllOperationOnFlsDB --value=false"
    logger.info("Setting File Lookup Service to false using command: " + str(cmdSetAllOperationOnFlsDB))
    return_code = runCommand(remoteConnection, cmdSetAllOperationOnFlsDB)
    if(return_code != 0):
        logger.error("Error in Execution of: " + str(cmdSetAllOperationOnFlsDB))
        return return_code
    return return_code

def jumpToNodePostgreSQL(remoteConnection, command, mgtServer):
    '''
    Function used to ssh to MS, postgresql nodes and execute shell script.
    '''
    listOfExpects = []
    user = "litp-admin"
    host = "postgresql01"
    ssh_newkey = "Are you sure you want to continue connecting (yes/no)?"
    password = "12shroot"

    logger.info("INFO: Openning connection to MS host.")
    child, return_code = remoteConnection.spawnMSChild()
    if return_code != 0:
        return child, return_code
    listOfExpects = ["root@"+str(mgtServer.server.hostname)]
    result, return_code = remoteConnection.expectChild(child, listOfExpects, None, None, None, None)
    if return_code != 0:
        return result, return_code
    logger.info("INFO: Connection with MS host has been established.")

    logger.info("INFO: Openning connection to PostgreSQL host.")
    listOfExpects = ["litp-admin@postgresql01's password: ", ssh_newkey]
    result, return_code = remoteConnection.expectChild(child, listOfExpects, ssh_newkey, user, host, password)
    if return_code == 1:
        return result, return_code
    listOfExpects = [r'litp-admin(.*?)\$']
    result, return_code = remoteConnection.expectChild(child, listOfExpects, None, None, None, None)
    if return_code != 0:
        return result, return_code
    logger.info("INFO: Connection with PostgreSQL host has been established")

    logger.info("INFO: Changing user from litp-admin to root")
    rootUserCmd = "su - root"
    result, return_code = remoteConnection.expectChildSendCmd(child, rootUserCmd)
    if return_code != 0:
        return result, return_code
    listOfExpects = ["Password: "]
    result, return_code = remoteConnection.expectChild(child, listOfExpects, None, None, None, None)
    if return_code != 0:
        return result, return_code
    result, return_code = remoteConnection.expectChildSendCmd(child, password)
    if return_code != 0:
        return result, return_code
    listOfExpects = [r'root(.*?)#']
    result, return_code = remoteConnection.expectChild(child, listOfExpects, None, None, None, None)
    if return_code != 0:
        return result, return_code
    logger.info("INFO: User has been changed successfully")

    logger.info("INFO: Executing next command " + str(command))
    result, return_code = remoteConnection.expectChildSendCmd(child, str(command))
    child.logfile = sys.stdout
    if return_code != 0:
        return result, return_code

    listOfExpects = [r'root(.*?)#']
    result, return_code = remoteConnection.expectChild(child, listOfExpects, None, None, None, None, 600)
    if return_code != 0:
        return result, return_code

    # file check output
    if "[ -f" in str(command):
        result, return_code = remoteConnection.expectChildSendCmd(child, 'echo $?')
        if return_code != 0:
            return result, return_code
        listOfExpects = ['0\r']
        result, return_code = remoteConnection.expectChild(child, listOfExpects, None, None, None, None, 5)
        logger.info("INFO: command return: " + str(return_code))
        if return_code != 0:
            logger.info("INFO: File Doesn't Exist")
            return "Doesn't Exist", 1

    logger.info("INFO: Command executed successfully")
    return "SUCCESS", 0

def getIsoLayout(newISOLayout, isoName, isoVersion, drop):
    """
    This function returns ISO Layout.
    """
    if newISOLayout.lower() == "true":
        cxpNumber = re.sub('-(\d+\\.)?(\d+\\.)?(\d+\\.)?(\d+\\.)?iso$','',isoName)
        cxpNumber = re.sub('^\w+_','',cxpNumber)
        rstate = convertVersionToRState(isoVersion)
        isoDirName = str(cxpNumber) + "_" + str(rstate)
        mediaName = isoDirName
        return mediaName, isoDirName
    else:
        mediaName = drop
        return mediaName, ""

def yumUpgradeLitpPackages(remoteConnection, packageListDict, isoLitpRebuild):
    """
    This function search for replaced files and perform yum upgrade.
    """
    for package, version in packageListDict.items():
        return_code, commandOutput = runFindCommand(remoteConnection, isoLitpRebuild, package)
        if return_code != 0:
            logger.error(str(commandOutput))
            return return_code
        if (str(isoLitpRebuild) in commandOutput):
            commandOutputList = commandOutput.split( )
            for item in commandOutputList:
                if (str(isoLitpRebuild) in item):
                    baseName = os.path.basename(item)
                    packageDirectory = os.path.dirname(item)
                    logger.info("Next package will be upgraded..: " + str(baseName))
                    return_code, output = yumUpdateArtifact(remoteConnection, packageDirectory, baseName)
                    if return_code != 0:
                        logger.error("Error: Couldn't run yum upgrade on the package " + str(baseName))
                        return return_code
                    logger.info("Success: Package been successfuly upgraded.")
                    logger.info("Next package will be imported to litp repo..: " + str(baseName))
                    return_code, status = importLitpPackage(remoteConnection, packageDirectory, baseName)
                    if return_code != 0:
                        logger.error(str(status))
                        return return_code
                    logger.info(str(status))
        else:
            logger.error("Error: "+str(package)+" hasn't been found in litp rebuild location " + str(isoLitpRebuild))
            return 1
    return 0

def runFindCommand(remoteConnection, location, item):
    """
    This function executes find commnad of specific item in given directory and returns output
    """
    cmd = "find " + location + " -regex \'/.*/" + item + "-[0-9].*\'"
    (return_code, commandOutput) = remoteConnection.runCmdGetOutput(cmd)
    if return_code != 0:
        errorMsg = "Error in execution command " + str(cmd)
        return return_code, errorMsg
    return return_code, commandOutput

def importLitpPackage(remoteConnection, packageDirectory, baseName):
    """
    This function import litp package to a litp directory of MS server.
    """
    litpImportRepoLocation = "/var/www/html/"
    package = packageDirectory + "/" + baseName
    return_code, commandOutput = runFindCommand(remoteConnection, litpImportRepoLocation, baseName.split('-')[0])
    if return_code != 0:
        errorMsg = str(commandOutput)
        return 1, errorMsg
    if (str(litpImportRepoLocation) in commandOutput):
        commandOutputList = commandOutput.split( )
        for item in commandOutputList:
            if (str(litpImportRepoLocation) in item):
                directoryToImport = item.rsplit('/', 1)[0]
                importLitpCommand = "litp import " + package + " " + directoryToImport
                logger.info("Command Execution: " + str(importLitpCommand))
                return_code, command_output = remoteConnection.runCmdGetOutput(importLitpCommand)
                if return_code != 0:
                    errorMsg = "Error: Couldn't litp import RPM into LITP repo location."
                    return 1, errorMsg
                return 0, "Success, Package has been successfuly imported into LITP repo."
    else:
        logger.warning("Warning: there no such packages been found in LITP repo location.")
        if baseName.startswith("ERIClitp"):
            logger.info("Adding package into litp repo location.")
            return_code, command_output = remoteConnection.runCmdGetOutput("litp import " + str(package) + " " + str(litpImportRepoLocation) + "litp/")
            if return_code != 0:
                errorMsg = "Error: Couldn't import RPM into LITP repo location."
                return 1, errorMsg
        else:
            logger.info("Adding package into 3pp repo location.")
            return_code, command_output = remoteConnection.runCmdGetOutput("litp import " + str(package) + " " + str(litpImportRepoLocation) + "3pp/")
            if return_code != 0:
                errorMsg = "Error: Couldn't import RPM into 3PP repo location."
                return 1, errorMsg
    return 0, "Success: Package has been imported"

def updateConfigValues(host, filePath, fileName, localFilePath, configName, newValue):
    '''
    To update config values in environment file
    '''
    ret = dmt.utils.paramikoSftp(
            host.server.hostname + "." + host.server.domain_name,
            "root",
            filePath + "/" + fileName,
            localFilePath + "/" + fileName,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "get")
    if ret != 0:
        return ret, 'Something went wrong while fetching the file '+ str(fileName) + ' from remote server ' + str(host.server.hostname)
    try:
        with open(localFilePath + "/" + fileName, 'r+') as fr:
            lines = fr.readlines()
            for i in range(len(lines)):
                if configName in lines[i]:
                    logger.info('Found the config')
                    lines[i] = str(configName) + '=' + str(newValue) + '\n'
            fr.truncate(0)
            fr.seek(0)
            lines.append('\n')
            fr.writelines(lines)
            fr.close()
    except Exception as e:
        logger.info('Exception with ' + str(e))
        return 1, e
    ret = dmt.utils.paramikoSftp(
            host.server.hostname + "." + host.server.domain_name,
            "root",
            filePath + "/" + fileName,
            localFilePath + "/" + fileName,
            int(config.get('DMT_AUTODEPLOY', 'port')),
            config.get('DMT_AUTODEPLOY', 'key'),
            "put")
    return ret, 'Something went wrong while uploading the file ' + str(fileName) + ' to remote server ' + str(host.server.hostname) if ret else 'Updated successfully with ' + str(configName) + '=' + str(newValue)


def execUpdatePasswordScript(remoteConnection,mgtServer,litpPwd, rootPwd):
    '''
    To update login details for peer nodes in deployment
    '''
    ret = 0
    logger.info("INFO: Openning connection to MS host.")
    child, ret = remoteConnection.spawnMSChild()
    child.logfile = sys.stdout
    if ret != 0:
        return child, ret
    listOfExpects = ["root@" + str(mgtServer.server.hostname), "Enter new password for litp-admin:", "Retype new password for litp-admin:", "Enter new password for root:",  "Retype new password for root:", "root@" + str(mgtServer.server.hostname) ]
    listOfCommands = ['/opt/ericsson/enminst/bin/update_initial_passwords.sh', litpPwd, litpPwd, rootPwd, rootPwd, "\r" ]
    errorMsg = ""
    for expect, command in zip(listOfExpects, listOfCommands):
        result, ret = remoteConnection.expectChild(child, [expect], None, None, None, None)
        if ret != 0:
            return result, ret
        result, ret = remoteConnection.expectChildSendCmd(child, command)
        if ret != 0:
            return result, ret

    return 'Script to update password for the litp-admin and root user executed successfully' , int(ret)


def downloadUnzipSlicesDD(xmlFile, tmpArea, package, version, groupId):
    '''
    Downloading and running unzip on .zip DD slices packages
    '''
    logger.info("Getting DD Slices Package: " + package + "-" + version + "-SNAPSHOT.zip...")
    (ret, sliceDir) = dmt.utils.downloadSliceFile(version, tmpArea, package, groupId)
    if ret != 0:
        logger.error("Issue downloading DD Slices Package: " + package + "-" + version + "-SNAPSHOT.zip...")
        return ret
    (ret, message) = dmt.utils.unzipFile(sliceDir,tmpArea)
    if ret != 0:
        logger.error("Issue unzipping DD Slices Package: " + package + "-" + version + "-SNAPSHOT.zip, error:" + str(message))
        return ret
    return ret


def getSliceDD(xmlFile, tmpArea, isoName, isoVersion):
    '''
    Getting the slice DD XML File for EDP II
    '''
    ret = 0
    try:
        logger.info("Getting DD Slice xml: " + xmlFile)
        if "::" in xmlFile:
            xmlFile = xmlFile.split("::")[1]
        if ".iso" in isoName:
            isoName = isoName.split("-")[0]
        depDescPackage = config.get("DMT_AUTODEPLOY", "deploymentTemplatePackage")
        packageMap = ISObuildMapping.objects.get(iso__mediaArtifact__name=isoName, iso__version=isoVersion, package_revision__artifactId=depDescPackage)
        packageGroup = packageMap.package_revision.groupId
        packageVer = packageMap.package_revision.version
        secondGroup = config.get('DMT_AUTODEPLOY', 'secondSliceGroupId')
        secondArtifact = config.get('DMT_AUTODEPLOY', 'secondSliceArtifactId')
        cmd = "find " + tmpArea + " -regex \'/.*/" + xmlFile  + "\'"
        # Download First Slices Package
        ret = downloadUnzipSlicesDD(xmlFile, tmpArea, depDescPackage, packageVer, packageGroup)
        if ret != 0:
            return ret, xmlFile
        (output, ret) = executeCmd(cmd)
        if ret != 0 or not "slices" in str(output):
            logger.info(str(output))
            logger.info("DD Slice xml wasn't found yet, trying DD Slices Package: " + secondArtifact)
            # Wasn't found downloading Second Slice package
            ret = downloadUnzipSlicesDD(xmlFile, tmpArea, secondArtifact, packageVer, secondGroup)
            if ret != 0:
               return ret, xmlFile
            (output, ret) = executeCmd(cmd)
        if not "slices" in str(output):
            logger.info(str(output))
            logger.error("Issue getting DD Slice: " + xmlFile + ", make sure it's valid DD Slice xml file name.")
            return 1, xmlFile
        xmlFile = str(output).strip()
        logger.info("DD Slice xml found: " + xmlFile)
    except Exception as e:
        logger.error("Issue getting DD Slice: " + xmlFile + ", Error: " +  str(e))
        return 1, xmlFile
    return ret, xmlFile


def deployMainTor(clusterId, drop, product, environment, packageList, litpPackageList, deployScriptVersion,
    deployRelease, cfgTemplate, osRhel6PatchDrop, osRhel7PatchDrop, osRhel79PatchDrop, osRhel88PatchDrop, servicePatchVersion, installType, reInstallInstllScript,
    reStartFromStage, featTest, stopAtStage, mountIsoAgain, setClusterStatus, skipStage, extraParameter,
    newISOLayout, deployProduct, litpDrop, reDeployVMS, step, osVersion, osVersion8, skipOsInstall,
    skipLitpInstall, skipPatchInstall, skipEnmInstall, ipmiVersion, redfishVersion, performSnapshot, stageOne, stageTwo, xmlFile,
    exitAfterISORebuild, skipTearDown, ignoreHa, verifyServices, updateServiceGroups, network, hcInclude, ignoreUpgradePrecheck,
    productSet, psVersion, edpProfileList, edpVersion, edpPackageList, kickstartFileUrl, skipNasPatchInstall, nasConfig, nasRhelPatch, failOnSedValidationFailure):
    signal.signal(signal.SIGINT, handler)
    # Check the user
    userName = getpass.getuser()
    logger.info("Current User Logged in " + str(userName))
    if str(userName) != "lciadm100":
        logger.error("ERROR ::: Please Ensure you are logged in as the lciadm100 user")
        sys.exit(1)
    isoDirName = ""
    commandType=""
    litpisopath=""
    cloudDownLoadDir = config.get('DMT_AUTODEPLOY', 'cloudDownLoadDir')
    secondRunSkipPatches = False
    errorStage = "ERROR : Stages"
    hostName = socket.gethostbyaddr(socket.gethostname())[0]
    logger.info("Execution CI-AXIS Commands on " + hostName)

    global cloudQueueFileName,processId,clusterIdGlobal,env,setStatusUpdate,cloudLockFileName,tmpArea,remoteConnection,networkGlobal

    env = environment
    setStatusUpdate = setClusterStatus
    networkGlobal = network
    cloudLockFileName = "cloud_LockFile.txt"
    cloudQueueFileName = "cloud_Queue.txt"
    remoteConnection = None
    tmpArea = None
    litpProduct = None
    osRhel6PatchProduct = osRhel6PatchVersion = None
    osRhel7PatchProduct = osRhel7PatchVersion = None
    osRhel79PatchProduct = osRhel79PatchVersion = None
    osRhel88PatchProduct = osRhel88PatchVersion = None
    osDrop = osIsoVersion = osProduct = osMedia = None
    osDrop8 = osIsoVersion8 = osProduct8 = osMedia8 = None

    clusterIdGlobal = clusterId
    processId = os.getpid()
    mediaArtifactList = ["lastIsoImportedDoNotDelete"]

    # Set the defaults for the deployment status
    busyDepStatus="BUSY"
    failDepStatus="FAILED"
    endDepStatus="IDLE"
    if osVersion != None:
        if "::" in osVersion:
            (osVersion, osDrop, osIsoVersion, osProduct) = osVersion.split('::')
    if osVersion8 != None:
        if "::" in osVersion8:
            (osVersion8, osDrop8, osIsoVersion8, osProduct8) = osVersion8.split('::')
    if "::" in drop:
        ( drop, isoVersion, enmProduct) = setDropIsoVersion(drop)
    else:
        isoVersion = "LATEST"
    # get the Litp Drop and ISO version
    if (litpDrop != None):
        if "::" in litpDrop:
            ( litpDrop, litpIsoVersion, litpProduct) = setDropIsoVersion(litpDrop)
        else:
            litpIsoVersion = "LATEST"
    else:
        litpIsoVersion = "None"
    # get the OS Patches Drop and ISO version
    if osRhel6PatchDrop != None:
        if "::" in osRhel6PatchDrop:
            ( osRhel6PatchDrop, osRhel6PatchVersion, osRhel6PatchProduct) = setDropIsoVersion(osRhel6PatchDrop)

    if osRhel7PatchDrop != None:
        if "::" in osRhel7PatchDrop:
            ( osRhel7PatchDrop, osRhel7PatchVersion, osRhel7PatchProduct ) = setDropIsoVersion(osRhel7PatchDrop)

    if osRhel79PatchDrop != None:
        if "::" in osRhel79PatchDrop:
            ( osRhel79PatchDrop, osRhel79PatchVersion, osRhel79PatchProduct ) = setDropIsoVersion(osRhel79PatchDrop)

    if osRhel88PatchDrop != None:
        if "::" in osRhel88PatchDrop:
            (osRhel88PatchDrop, osRhel88PatchVersion, osRhel88PatchProduct) = setDropIsoVersion(osRhel88PatchDrop)

    if "cloud" in environment:
        if ( installType == "initial_install"):
            torinstDeployParameter = "install_cloud"
        else:
            torinstDeployParameter = "upgrade_cloud"
    else:
        if ( installType == "initial_install"):
            torinstDeployParameter = "install"
        else:
            torinstDeployParameter = "upgrade"

    if not litpProduct:
        litpProduct = config.get('DMT_AUTODEPLOY','litpProductName')
    enmInstRHEL7Patch = config.get('DMT_AUTODEPLOY', 'enmInstRHEL7Patch')
    enmInstRHEL79Patch = config.get('DMT_AUTODEPLOY', 'enmInstRHEL79Patch')
    enmInstRHEL88Patch = config.get('DMT_AUTODEPLOY', 'enmInstRHEL88Patch')
    enmInstRHELPatchISO = config.get('DMT_AUTODEPLOY', 'enmInstRHELPatchISO')
    isoRebuildlocation = config.get('DMT_AUTODEPLOY', 'lmsIsoRecreateLoc')
    lastIsoImportedFile = config.get('DMT_AUTODEPLOY', 'lastIsoImported')
    mountMediaLocation = config.get('DMT_AUTODEPLOY', 'mountMediaLocation')
    mediaDirStructure = config.get('DMT_AUTODEPLOY','mediaDirStructure')
    user=config.get('DMT_AUTODEPLOY', 'user')
    masterUserPassword = config.get('DMT_AUTODEPLOY', 'masterPasswordCloudMS1')
    keyFileName=config.get('DMT_AUTODEPLOY', 'key')
    litpPassword=config.get('DMT_AUTODEPLOY', 'litpPassword')
    litpUsername=config.get('DMT_AUTODEPLOY', 'litpUsername')
    maxUpTime=config.get('DMT_AUTODEPLOY', 'maxMsUpTime')
    scriptFile = "DeploymentScripts-" + deployScriptVersion + ".tar.gz"
    upgradeOSVersions = str(config.get('DMT_AUTODEPLOY', 'upgradeOSVersions')).split(",")

    cluster = Cluster.objects.get(id = clusterId)
    clusterName = cluster.name
    mgtServer = cluster.management_server
    fqdnMgtServer = mgtServer.server.hostname + "." + mgtServer.server.domain_name

    if not os.path.exists(cloudDownLoadDir):
        # Randomly generated directory with /tmp
        tmpArea = tempfile.mkdtemp()
    else:
        # For cloud there is a specific area to use /export/data
        random = randint(2,9000)
        tmpArea = cloudDownLoadDir + "/temp" + str(random)
        retCode = dmt.utils.cleanOutDirectoryArea(cloudDownLoadDir,0,"temp")
        os.makedirs(cloudDownLoadDir + "/temp" + str(random))
    # Randomly generated directory with /tmp
    # make a packages directory with the created tmp directory

    packagesDir = os.path.join(tmpArea, "packages")
    os.makedirs(packagesDir)
    jumpServerIp = dmt.utils.getJumpServerIp(network)
    #EDP Support
    isEdpSupported = False
    if installType == 'upgrade_install' and environment == "physical":
        isEdpSupported = execEdpSupportedCheck(productSet, edpVersion, deployScriptVersion)
        if isEdpSupported and skipEnmInstall == "YES":
            logger.warning("====EDP Requires ENM Media: '--skipEnmInstall YES' is not supported with EDP===")
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Warning: EDP Requires ENM Media",tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    kernelVerBeforeDeploy = None
    if installType == 'upgrade_install' and environment == "cloud":
        (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
        ret, kernelVerBeforeDeploy = runCommandGetOutput(remoteConnection, " uname -r")
        logger.info("*** Kernel check Before UG ***")
        logger.info(kernelVerBeforeDeploy)
    #EDP II Support
    isEdpIISupported = False
    if installType == 'initial_install' and environment == "physical":
        logger.info("===Checking if EDP II supported===")
        isEdpIISupported = execEdpIISupportCheck(productSet, edpVersion, deployScriptVersion)

    try:
        if NetworkInterface.objects.filter(server=mgtServer.server_id, interface="eth0").exists():
            networkObject = NetworkInterface.objects.get(server=mgtServer.server_id, interface="eth0")
            nic = networkObject.mac_address
            editedNic = nic.replace(":", "").upper()
            cloudLockFileName = editedNic + "_LockFile.txt"
            cloudQueueFileName = str(processId) + "_QueueFile.txt"
        else:
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not get the server MAC Address",tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    except Exception as e:
        errMsg = "Error: Could not get the server MAC Address, Exception : " + str(e)
        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

    if updateServiceGroups != "NO":
        updateServiceGroupsAuto(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,tmpArea,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

    if installType == "softwareupdateonly":
        if skipEnmInstall != "YES":
            # Open the ssh connection to the specified server
            (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
            if (ret != 0):
                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS during snapshot creation",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            (ret,errMsg) = deploySoftwareUpdateOnly(remoteConnection,clusterId,mgtServer,packageList,commandType,packagesDir,product,fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment,tmpArea,isoRebuildlocation,installType,deployScriptVersion,deployRelease,scriptFile,ignoreHa)
            if ret != 0:
                # Clean up the server
                enmRepo = config.get('DMT_AUTODEPLOY', 'enmRepo')
                repoData = config.get('DMT_AUTODEPLOY', 'repoData')
                serviceRepoBackup = config.get('DMT_AUTODEPLOY', 'serviceRepoBackup')
                serviceRepo = config.get('DMT_AUTODEPLOY', 'serviceRepo')
                scriptingRepo = config.get('DMT_AUTODEPLOY', 'scriptingRepo')
                streamingRepo = config.get('DMT_AUTODEPLOY', 'streamingRepo')
                eventsRepo = config.get('DMT_AUTODEPLOY', 'eventsRepo')
                # Check redhat release version
                ret, output = runCommandGetOutput(remoteConnection, " cat " + config.get('DMT_AUTODEPLOY', 'rhelVersionFile'))
                logger.info(str(output))
                if ret != 0:
                    logger.info("Failed to get RHEL version, using default repo naming convention.")
                else:
                    if "release" in output:
                        output = str(output).split("release")[1]
                        logger.info(str(output))
                    if " 7." in output:
                        serviceRepo = config.get('DMT_AUTODEPLOY', 'serviceRepoRhel7')
                        scriptingRepo = config.get('DMT_AUTODEPLOY', 'scriptingRepoRhel7')
                        streamingRepo = config.get('DMT_AUTODEPLOY', 'streamingRepoRhel7')
                        eventsRepo = config.get('DMT_AUTODEPLOY', 'eventsRepoRhel7')
                    if " 8." in output:
                        serviceRepo = config.get('DMT_AUTODEPLOY', 'serviceRepoRhel8')
                        scriptingRepo = config.get('DMT_AUTODEPLOY', 'scriptingRepoRhel8')
                        streamingRepo = config.get('DMT_AUTODEPLOY', 'streamingRepoRhel8')
                        eventsRepo = config.get('DMT_AUTODEPLOY', 'eventsRepoRhel8')
                if "cloud" in environment:
                    # Check does the backups exist
                    for item in str(serviceRepo), str(scriptingRepo), str(streamingRepo), str(eventsRepo):
                        ret = remoteConnection.runCmd("ls " + str(serviceRepoBackup) + "/" + str(item) + "/" + str(repoData))
                        if ret == 0:
                            # Copy the repo xml file back, so the update can run again on the same server
                            ret = copyContent(remoteConnection,str(serviceRepoBackup) + "/" + str(item) + "/" + str(repoData),str(enmRepo) + "/" + str(item))
                            if ret != 0:
                                logger.info("Issue with the restore, of the backup repodata directory " + str(serviceRepoBackup) + "/" + str(item) + "/" + str(repoData) + " to " + str(enmRepo) + "/" + str(item))
                            ret = remoteConnection.runCmd("rm -rf " + str(serviceRepoBackup) + "/" + str(item))
                            if ret != 0:
                                logger.error("Issue with the removal of the backup of the repodata directory " + str(serviceRepoBackup) + "/" + str(item) + "/" + str(repoData))
                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                logger.info("Software Update Completed with Errors")
                return 1
            logger.info("Software Update Completed")
        else:
            logger.info("Software Update Skipped")
            exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        return 0
    if performSnapshot != None:
        if "::" in performSnapshot:
            qualifier = "::"
            option = performSnapshot.split(qualifier)[0]
            snapShotName = performSnapshot.split(qualifier)[1]
        else:
            option = performSnapshot
            snapShotName = ""
        # Open the ssh connection to the specified server
        (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
        if (ret != 0):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS during snapshot creation",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        if "restore_snapshot" in option:
            logger.info("============================================================================================================")
            logger.info("====================== Beginning FLS Data Collection Workaround - Pre Rollback Steps =======================")
            ret = setFileLookupServiceTrue(remoteConnection, mgtServer)
            logger.info("====================== Completed FLS Data Collection Workaround - Pre Rollback Steps =======================")
        # Set the lmsUploadDir by checking does the software directory exist already if it does use it
        (ret, lmsUploadDir) = setUploadDirectory(remoteConnection,installType,deployScriptVersion)
        if (ret != 0):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        deployScriptsToMgtServer(remoteConnection, mgtServer, deployScriptVersion, deployRelease, lmsUploadDir,tmpArea,product,scriptFile) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not Upload Deployment Scripts",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        logger.info("Executing the snapping procedure on the server, executing: " + str(performSnapshot) + " snapshot")
        deployReturn = execStageOnePostInstall(remoteConnection,lmsUploadDir,snapShotName,environment,mgtServer,option)
        if (deployReturn != 0):
            errMsg = "Error: Could not execute the snap procedure on the server, while executing: " + str(performSnapshot) + " snapshot"
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        logger.info("Snap Processes a Success")
        logger.info('--------------Updating the watermark value from 81 to 84----------------')
        filePath =  config.get('DMT_AUTODEPLOY','enmInstEtc')
        fileName = 'enminst_cfg.ini'
        localFilePath = tmpArea
        configName = 'SAN_POOL_USAGE_NS'
        newValue = 84
        ret, output = updateConfigValues(mgtServer, filePath, fileName, localFilePath,  configName, newValue)
        if ret != 0:
            logger.info('--------------Update of watermark value failed----------------')
            logger.warning(output)
        else:
            logger.info('--------------Update of watermark value completed with success----------------')
        if "restore_snapshot" in option:
            logger.info("============================================================================================================")
            logger.info("==================== Beginning FLS Data Collection Workaround - Post Rollback Steps ========================")
            ret = setFileLookupServiceFalse(remoteConnection, drop, mgtServer)
            logger.info("==================== Completed FLS Data Collection Workaround - Post Rollback Steps ========================")
        exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Snap Processes Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        return 0

    logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(product), str(drop), str(isoVersion))
    ( isoName, isoVersion, isoUrl, hubIsoUrl, message ) = getIsoName(drop,isoVersion,product)
    if (packageList != None and isEdpIISupported is False):
        (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
        totalIsoWeight = getCalculatedCrackedIsoWeight(isoName.split("-")[0], isoVersion, packageList)
        if totalIsoWeight is None:
            exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Unable to get the Calculated Cracked ISO Weight",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        isoRebuild = findRebuildLocation(remoteConnection, totalIsoWeight)
        if isoRebuild == "None":
            exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: There is not enough available space on any partition to download ENM ISO and perform package(s) replacement!",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    errMsg = "Error: Could not get the iso version or URL for product " + str(product)
    if (isoName == 1):
        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    mediaArtifactList.append(isoName)
    originalEnmIsoName = isoName
    reCreatedIsoName = isoName.replace(".iso", "-autoDeploy.iso")
    if (packageList != None):
        mediaArtifactList.append(reCreatedIsoName)

    # Before we continue we need to verify the SED matches with the deployment description in the installation
    if verifyServices != "NO" and skipEnmInstall != "YES":
        (ret,message) = verifySEDvsDeploymentDescription(clusterId,cfgTemplate,xmlFile,packageList,isoName,isoVersion)
        if ret != 0:
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

    # Get the Litp information
    originalLitpIsoName = ""
    litpIsoName = litpIsoUrl = litpHubIsoUrl = ""
    if (litpDrop != None and skipLitpInstall != "YES"):
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(litpProduct), str(litpDrop), str(litpIsoVersion))
        ( litpIsoName, litpIsoVersion, litpIsoUrl, litpHubIsoUrl, message ) = getIsoName(litpDrop,litpIsoVersion,litpProduct)
        if (litpIsoName == 1):
            errMsg = "Error: Could not get the iso version or URL for product " + str(litpProduct)
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        if (litpPackageList != None and isEdpIISupported is False):
            (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
            totalIsoWeight = getCalculatedCrackedIsoWeight(litpIsoName.split("-")[0], litpIsoVersion, litpPackageList)
            if totalIsoWeight is None:
                exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Unable to get the Calculated Cracked ISO Weight",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            isoLitpRebuild = findRebuildLocation(remoteConnection, totalIsoWeight)
            if isoLitpRebuild == "None":
                exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: There is not enough available space on any partition to download LITP ISO and perform package(s) replacement!",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        mediaArtifactList.append(litpIsoName)
        originalLitpIsoName = litpIsoName
        reCreatedLitpIsoName = litpIsoName.replace(".iso", "-autoDeploy.iso")
        if (litpPackageList != None):
            mediaArtifactList.append(reCreatedLitpIsoName)


    # Get the ENMinst information version from ENM ISO
    enmInstVersion = getEnmInstInfo(isoName, isoVersion)

    # Get the Rhel6 OS Patch Set information
    osRhel6PatchFileName = osRhel6PatchFileVersion = osRhel6PatchFileUrl = osRhel6PatchFileHubUrl = ""
    if (osRhel6PatchDrop != None) and (skipPatchInstall != "YES" and skipPatchInstall != "RHEL6"):
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(osRhel6PatchProduct), str(osRhel6PatchDrop), str(osRhel6PatchVersion))
        ( osRhel6PatchFileName, osRhel6PatchFileVersion, osRhel6PatchFileUrl, osRhel6PatchFileHubUrl, message ) = getIsoName(osRhel6PatchDrop,osRhel6PatchVersion,osRhel6PatchProduct)
        if (osRhel6PatchFileName == 1):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        mediaArtifactList.append(osRhel6PatchFileName)

    # Get the Rhel7 OS Patch Set information
    osRhel7PatchFileName = osRhel7PatchFileVersion = osRhel7PatchFileUrl = osRhel7PatchFileHubUrl = ""
    if osRhel7PatchDrop != None and (LooseVersion(enmInstRHEL7Patch) <= LooseVersion(enmInstVersion)) and (skipPatchInstall != "YES" and skipPatchInstall != "RHEL7"):
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(osRhel7PatchProduct), str(osRhel7PatchDrop), str(osRhel7PatchVersion))
        ( osRhel7PatchFileName, osRhel7PatchFileVersion, osRhel7PatchFileUrl, osRhel7PatchFileHubUrl, message ) = getIsoName(osRhel7PatchDrop,osRhel7PatchVersion,osRhel7PatchProduct)
        if (osRhel7PatchFileName == 1):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        mediaArtifactList.append(osRhel7PatchFileName)

    # Get the 2nd Rhel7 OS Patch Set information
    osRhel79PatchFileName = osRhel79PatchFileVersion = osRhel79PatchFileUrl = osRhel79PatchFileHubUrl = ""
    if osRhel79PatchDrop != None and (LooseVersion(enmInstRHEL79Patch) <= LooseVersion(enmInstVersion)) and (skipPatchInstall != "YES" and skipPatchInstall != "RHEL79"):
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(osRhel79PatchProduct), str(osRhel79PatchDrop), str(osRhel79PatchVersion))
        ( osRhel79PatchFileName, osRhel79PatchFileVersion, osRhel79PatchFileUrl, osRhel79PatchFileHubUrl, message ) = getIsoName(osRhel79PatchDrop, osRhel79PatchVersion, osRhel79PatchProduct)
        if (osRhel79PatchFileName == 1):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        mediaArtifactList.append(osRhel79PatchFileName)

    # Get the Rhel8 OS Patch Set information
    osRhel88PatchFileName = osRhel88PatchFileVersion = osRhel88PatchFileUrl = osRhel88PatchFileHubUrl = ""
    if osRhel88PatchDrop != None and (LooseVersion(enmInstRHEL88Patch) <= LooseVersion(enmInstVersion)) and (skipPatchInstall != "YES" and skipPatchInstall != "RHEL88"):
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(osRhel88PatchProduct), str(osRhel88PatchDrop), str(osRhel88PatchVersion))
        ( osRhel88PatchFileName, osRhel88PatchFileVersion, osRhel88PatchFileUrl, osRhel88PatchFileHubUrl, message ) = getIsoName(osRhel88PatchDrop, osRhel88PatchVersion, osRhel88PatchProduct)
        if (osRhel88PatchFileName == 1):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        mediaArtifactList.append(osRhel88PatchFileName)

    # Get the OS Media information
    osIsoName = osIsoUrl = osIsoHubUrl = ""
    if osVersion != None and ("upgrade" in installType) and (osVersion in upgradeOSVersions) and (skipOsInstall != "YES"):
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(osProduct), str(osDrop), str(osIsoVersion))
        ( osIsoName, osIsoVersion, osIsoUrl, osIsoHubUrl, message ) = getIsoName(osDrop,osIsoVersion,osProduct)
        if (osIsoName == 1):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
        osMedia = softwareDir + "/" + osIsoName
        mediaArtifactList.append(osIsoName)
    elif installType == "initial_install" and isEdpIISupported:
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(osProduct), str(osDrop), str(osIsoVersion))
        ( osIsoName, osIsoVersion, osIsoUrl, osIsoHubUrl, message ) = getIsoName(osDrop,osIsoVersion,osProduct)
        if (osIsoName == 1):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg + ", " + str(message),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
        osMedia = softwareDir + "/" + osIsoName
        mediaArtifactList.append(osIsoName)
    if osVersion8 != None:
        logger.info("Getting the %s Media Artifact information based on the following: Drop: %s, Version: %s", str(osProduct8), str(osDrop8), str(osIsoVersion8))
        ( osIsoName8, osIsoVersion8, osIsoUrl8, osIsoHubUrl8, message8 ) = getIsoName(osDrop8,osIsoVersion8,osProduct8)
        softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
        osMedia8 = softwareDir + "/" + osIsoName8
        mediaArtifactList.append(osIsoName8)
    else:
        osIsoName8 = osIsoVersion8 = osIsoUrl8 = osIsoHubUrl8 = message8=None
    if environment == "physical":
        nasConfigMedia = dmt.utils.getNasMediaArtifact(nasConfig)
        nasRhelPatchMedia = dmt.utils.getNasMediaArtifact(nasRhelPatch)
        if nasConfigMedia is not None:
            mediaArtifactList.append(nasConfigMedia)
        if nasRhelPatchMedia is not None:
            mediaArtifactList.append(nasRhelPatchMedia)


    initialWait=1
    interval=2
    retries=3
    finishWait=0

    # Initial Install
    if (osVersion != None):
        if (skipOsInstall != "YES" and installType == 'initial_install'):
            if ( "cloud" in environment ):
                errMsg = "Error: Could not create the ms lock file. Exiting"
                checkCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                createCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
            elif ( skipTearDown == "no" ):
                logger.info("Tearing down the system before a new installation")
                errMsg = "Error: Unable to clean out the known host file for " + mgtServer.server.hostname
                dmt.createSshConnection.cleanKnowHostFile(mgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # Open the ssh connection to the specified server
                (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
                if (ret != 0):
                    logger.info("Unable to make a connection to the server, assuming ssh not available, teardown.sh script not executed, performing initial install now")
                else:
                    # Set the lmsUploadDir by checking does the software directory exist already if it does use it
                    (ret, lmsUploadDir) = setUploadDirectory(remoteConnection,installType,deployScriptVersion)
                    if (ret != 0):
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    cfgName = generateConfig(cluster, mgtServer, cfgTemplate, drop, isoName, osRhel6PatchDrop, osRhel7PatchDrop, osRhel79PatchDrop, osRhel88PatchDrop, servicePatchVersion, lmsUploadDir, installType, reCreatedIsoName, deployProduct,tmpArea, osRhel6PatchFileName, osRhel7PatchFileName, osRhel79PatchFileName, osRhel88PatchFileName, skipPatchInstall, litpisopath, enmInstRHEL7Patch, enmInstRHEL79Patch, enmInstRHEL88Patch, enmInstVersion)
                    if environment == "physical":
                        isSedValid = dmt.autoDeployUtils.validateSedFile(
                                cluster,
                                cfgName,
                                tmpArea,
                                product,
                                installType,
                                productSet)
                        if failOnSedValidationFailure and not isSedValid:
                            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"SED Validation Failed",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    if (cfgName == "1"):
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not generate cfg file for cluster",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)
                    cfgLoc = lmsUploadConfig(mgtServer, tmpArea, lmsUploadDir, cfgName)
                    if (cfgLoc == "1"):
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not upload cfg file.",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    enmInstBin=config.get('DMT_AUTODEPLOY', 'enmInstBin')
                    enminstTearDownSh=config.get('DMT_AUTODEPLOY', 'enminstTearDownSh')
                    (ret, commandOutput) = remoteConnection.runCmdGetOutput("ls " + str(enmInstBin) + str(enminstTearDownSh))
                    comment = "No such file or directory"
                    if str(comment) not in commandOutput:
                        # Does the teardown have the user interaction parameter
                        enmInstLib=config.get('DMT_AUTODEPLOY', 'enmInstLib')
                        enminstTearDownPy=config.get('DMT_AUTODEPLOY', 'enminstTearDownPy')
                        interactiveCheck = "grep -q assumeyes " + str(enmInstLib) + str(enminstTearDownPy)
                        ret = runCommand(remoteConnection,interactiveCheck)
                        if ret != 0:
                            tearDownDeployment = str(enmInstBin) + str(enminstTearDownSh) + " --sed " + str(cfgLoc) + " --command=clean_all"
                        else:
                            tearDownDeployment = str(enmInstBin) + str(enminstTearDownSh) + " --sed " + str(cfgLoc) + " --command=clean_all --assumeyes"
                        errMsg = "Error: Unable to clean down the deployment with MS, " + mgtServer.server.hostname
                        ret = runCommand(remoteConnection,tearDownDeployment,"tty-ssh")
                        if ret != 0:
                            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                        checkStep(step)
                    else:
                        logger.info("Unable to locate teardown.sh script on the MS, exiting deployment")
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            # Run EDP II profile if supported
            if isEdpIISupported:
                lmsUploadDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
                logger.info("-----------------------------GENERATE SED FILE--------------------------------")
                cfgName = generateConfig(cluster, mgtServer, cfgTemplate, drop, isoName, osRhel6PatchDrop, osRhel7PatchDrop, osRhel79PatchDrop, osRhel88PatchDrop, servicePatchVersion, lmsUploadDir, installType, reCreatedIsoName, deployProduct,tmpArea, osRhel6PatchFileName, osRhel7PatchFileName, osRhel79PatchFileName, osRhel88PatchFileName, skipPatchInstall, litpisopath, enmInstRHEL7Patch, enmInstRHEL79Patch, enmInstRHEL88Patch, enmInstVersion)
                if environment == "physical":
                    isSedValid = dmt.autoDeployUtils.validateSedFile(
                            cluster,
                            cfgName,
                            tmpArea,
                            product,
                            installType,
                            productSet)
                    if failOnSedValidationFailure and not isSedValid:
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"SED Validation Failed",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                if (cfgName == "1"):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not generate cfg file for cluster",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                edpCfgLoc = tmpArea + "/" + cfgName

                if "slice::" in str(xmlFile).lower():
                    ret, xmlFile = getSliceDD(xmlFile, tmpArea, isoName, isoVersion)
                    if ret != 0:
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Issue getting DD slice xml file",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

                logger.info('Executing EDP II profiles')
                deployReturn = execDeployEdp(clusterId, productSet, mediaArtifactList, xmlFile, edpCfgLoc, edpVersion, edpProfileList, edpPackageList, extraParameter, hcInclude, ignoreUpgradePrecheck, deployScriptVersion, originalEnmIsoName, originalLitpIsoName, kickstartFileUrl, skipNasPatchInstall, installType, packageList, litpPackageList)
                if (deployReturn != 0):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not complete stage 1 of the deployment",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

                if "Rack_Servers" in str(cluster.enmDeploymentType):
                    logger.info("SYSTEM DEPLOYED SUCCESSFULLY")
                    if remoteConnection:
                        copyPrivateKey(remoteConnection)
                        # This Ensures that all the peer nodes are up to ensure we can reset the password
                        logger.info("Waiting 10 minutes for the system to initialise")
                        time.sleep(600)
                        ret = reSetPeerNodePassword(remoteConnection,mgtServer)
                        if ret != 0:
                            logger.info("Error Resetting the Peer Nodes login details")
                            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error running post install commands",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                        # Clean up
                        softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
                        (ret,message) = cleanSoftwareDirectory(remoteConnection, softwareDir, lastIsoImportedFile, mediaArtifactList)
                        # This section only needs to be executed for older deployments that are still using /var/tmp/ as the upload directory
                        if ( "var" in lmsUploadDir ):
                            (ret,message) = cleanUpAfterSuccessfullInitialInstall(remoteConnection,mgtServer,lmsUploadDir,softwareDir,mediaArtifactList)
                            if (ret != 0):
                                logger.info(message)
                        diagnosticDataPresentation(remoteConnection, clusterId)
                        if not MediaArtifactServiceScanned.objects.filter(media_artifact_version=isoVersion).exists():
                            associatingVmServicesWithPackages(remoteConnection, clusterId, isoVersion)
                        exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                        if remoteConnection:
                            remoteConnection.close()
                    return 0

                # Setup for the rest of II for ENM Other Deployment Types
                cfgLoc = lmsUploadDir + "/" + cfgName
                if not str(xmlFile).startswith(config.get('DMT_AUTODEPLOY', 'defaultXmlFileDirectory')):
                    xmlFile = lmsUploadDir + "/" + os.path.basename(str(xmlFile))

                if (packageList != None):
                    isoName = isoName.replace(".iso", "-autoDeploy.iso")

                if (litpPackageList != None):
                    litpIsoName = litpIsoName.replace(".iso", "-autoDeploy.iso")

            if remoteConnection:
                remoteConnection.close()

            # Jumpstart configuration to install the Red Hat OS
            if not isEdpIISupported:
                logger.info("Configure DHCP Connection")
                jumpServerConnection = None
                pxeBootFile = None
                kickstartFile = createKickstartFile(mgtServer, tmpArea, osVersion, drop, jumpServerIp)
                if (kickstartFile == "error" ):
                    errMsg = "Error: Could not generate a new kickstart file for the deployment"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,jumpServerConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                (ret,commandOutput) = dmt.dhcpConfiguration.addClient(mgtServer,hostName,osVersion,kickstartFile,network)
                pxeBootFile = commandOutput[commandOutput.index("bootfile="):].replace("\n", "")
                if (ret != 0  and "bootfile=" in pxeBootFile ):
                    errMsg = "Error: Could not add the management server as a client to the jump server"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,jumpServerConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # DHCP Configuration
                errMsg = "Error: Could not clean down the management server from the DHCP client"
                dmt.dhcpConfiguration.setupDhcp(mgtServer,hostName,"clean",network) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,jumpServerConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                dmt.dhcpConfiguration.setupDhcp(mgtServer,hostName,"add",network,pxeBootFile) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,jumpServerConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                if ( "cloud" in environment ):
                    dmt.dhcpConfiguration.setupCloudDhcp(mgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,jumpServerConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)

            # kick off the install
            errMsg = "Error: Could not jump the server"
            if not isEdpIISupported:
                if ( "physical" in environment and mgtServer.server.hardware_type != "virtual" ):
                    jumpPhysical(mgtServer,clusterId,tmpArea,step,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                elif ( "cloud" in environment ):
                    jumpCloud(mgtServer,clusterId,step,mgtServer.server.hostname) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)
                elif ( "physical" in environment and mgtServer.server.hardware_type == "virtual"):
                    jumpVirtual(mgtServer,clusterId,tmpArea,step,mgtServer.server.hostname) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)
                else:
                    errMsg = "Error: The environment, \"" + str(environment) + "\" is not supported"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

            initialWait=120
            interval=30
            retries=80
            finishWait=0
        errMsg = "Error: Unable to clean out the known host file for " + mgtServer.server.hostname
        dmt.createSshConnection.cleanKnowHostFile(mgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        checkStep(step)
        # Check do we have an ssh connect wait if not then Open the ssh connection to the specified server
        if (skipOsInstall != "YES" and installType == 'initial_install'):
            if ( "cloud" in environment ):
                removeCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not remove the lock file",tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            errMsg = "Could not get an ssh connection to the MS, \"" + str(fqdnMgtServer)
            dmt.createSshConnection.checkSSHConnectForPassword(fqdnMgtServer,user,initialWait,interval,retries,finishWait) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            # Rhel 7 deployment forced password change on first login, login to LMS to hadle it if root enforced password reset
            if not isEdpIISupported:
                logger.info('Checking connection to LMS: First login post jump start')
                ret = dmt.createSshConnection.loginToLMS(fqdnMgtServer,user,masterUserPassword,hostName)
                if ret !=0:
                    logger.error('Checking connection to LMS: Failed to login')
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not login to LMS, root enforced password reset.",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

        (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
        if (ret != 0):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        if (skipOsInstall != "YES" and installType == 'initial_install'):
            checkServerUpTime(remoteConnection,maxUpTime) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: MS Server did not initial install, Please investigate",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    else:
        errMsg = "Error: Unable to clean out the known host file for " + mgtServer.server.hostname
        dmt.createSshConnection.cleanKnowHostFile(mgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        checkStep(step)
        # Open the ssh connection to the specified server
        (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
        if (ret != 0):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

    # Set the lmsUploadDir by checking does the software directory exist already if it does use it
    if not isEdpIISupported:
        logger.info('Setup upload directory, clean software directory and download media')
        (ret, lmsUploadDir) = setUploadDirectory(remoteConnection,installType,deployScriptVersion)
        if (ret != 0):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        (ret,message) = cleanSoftwareDirectory(remoteConnection, lmsUploadDir, lastIsoImportedFile, mediaArtifactList)
        # Start downloading all required media using threads
        try:
            threads = downloadAllToMgmtServer(remoteConnection, mgtServer, psVersion, litpIsoName,isoName,lmsUploadDir,tmpArea,litpIsoUrl,litpHubIsoUrl,osRhel6PatchFileName, osRhel6PatchFileUrl, osRhel6PatchFileHubUrl,osRhel7PatchFileName, osRhel7PatchFileUrl, osRhel7PatchFileHubUrl, osRhel79PatchFileName, osRhel79PatchFileUrl, osRhel79PatchFileHubUrl, osRhel88PatchFileName, osRhel88PatchFileUrl, osRhel88PatchFileHubUrl, isoUrl, hubIsoUrl, skipLitpInstall, skipPatchInstall, skipEnmInstall, enmInstRHEL7Patch, enmInstRHEL79Patch, enmInstRHEL88Patch, enmInstVersion, osIsoName, osIsoVersion, osIsoUrl, osIsoHubUrl, osMedia, osIsoName8, osIsoVersion8, osIsoUrl8, osIsoHubUrl8, osMedia8, nasConfig, nasRhelPatch)
        except Exception as e:
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error in ISO/Patches download Thread. Exception " + str(e),tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

    # LITP Deployment
    if not isEdpIISupported:
        if (deployProduct == "LITP2" and skipLitpInstall != "YES" and skipLitpInstall != None and litpDrop != None):
            errMsg = "Error: Could not download " + str(litpIsoName) + " to the management server"

            while threads[0].is_alive():
                logger.info ("Artifact " + str(litpIsoName) + " still downloading, please wait...")
                time.sleep(5)
            logger.info("Artifact " + str(litpIsoName) + " download is complete proceeding with litp installation...")
            checkStep(step)
            checkIsoMd5Sum(remoteConnection, mgtServer, litpIsoName, lmsUploadDir,tmpArea,litpIsoUrl,litpHubIsoUrl) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Md5 did not match",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            checkStep(step)
            litpisopath = lmsUploadDir + "/" + litpIsoName;
            if "upgrade" not in installType:
                litpProductLower = litpProduct.lower()
                errMsg = "Error: Could not mount the " + str(litpProduct) + " iso onto the management server"
                mountIsoToMgtServer(remoteConnection,mgtServer,litpIsoName,lmsUploadDir,litpProductLower) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # Install the Litp 2 iso onto the MS
                installLitp2Command = "sh /media/" + litpProductLower + "/install/installer.sh"
                errMsg = "Error: Could not run the command " + installLitp2Command + " on the MS to install the litp iso"
                runCommand(remoteConnection,installLitp2Command) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                errMsg = "Error: Could not unmount the " + str(litpProduct) + " iso on the management server"
                unmountIso(remoteConnection,mgtServer,litpProductLower) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # Set the Litp-admin User Password
                setLitpAdminPassword ="'echo -e \"" + str(litpPassword) + "\n" + str(litpPassword) + "\" | passwd " + str(litpUsername) + "'"
                errMsg = "Error: Could not set the password for the litp-admin user"
                runCommand(remoteConnection,setLitpAdminPassword) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # Configure the root user for the Litp installation
                setupRootLitpCliUser = "'echo -e \"[litp-client]\nusername = " + str(litpUsername) + "\npassword = " + str(litpPassword) + "\n\" > /root/.litprc; chmod 600 /root/.litprc'"
                errMsg = "Error: Could not run the command " + setupRootLitpCliUser + " on the MS to configure Litp root user"
                runCommand(remoteConnection,setupRootLitpCliUser) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # Configure the litp user for the Litp installation
                setupLitpCliUser = "'echo -e \"[litp-client]\nusername = " + str(litpUsername) + "\npassword = " + str(litpPassword) + "\n\" > /home/" + str(litpUsername) + "/.litprc; chmod 600 /home/" + str(litpUsername) + "/.litprc'"
                errMsg = "Error: Could not run the command " + setupLitpCliUser + " on the MS to configure " + str(litpUsername) + " user"
                runCommand(remoteConnection,setupLitpCliUser) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # Update the ownership of the file
                changeOwnership = "'chown " + str(litpUsername) + ":" + str(litpUsername) + " /home/" + str(litpUsername) + "/.litprc'"
                errMsg = "Error: Could not set the ownership on the litprc file for user " + str(litpUsername)
                runCommand(remoteConnection,changeOwnership) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                # Check the Litp installation
                checkInstall = "litp show -p /"
                (ret,commandOutput) = runCommandGetOutput(remoteConnection,checkInstall)
                if (ret != 0):
                    errMsg = "Error: Could not run the command " + checkInstall + " on the MS to check the Litp install"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                logger.info("Output from Litp Command \"litp show -p\"")
                logger.info(str(commandOutput))
                checkStep(step)

                # Check the Litp Version
                printLitpVersion = "litp version"
                (ret,commandOutput) = runCommandGetOutput(remoteConnection,printLitpVersion)
                if (ret != 0):
                    errMsg = "Error: Could not run the command \"" + str(printLitpVersion) + "\" on the MS to print out the Litp version installed"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                logger.info("Output from Litp Command \"" + str(printLitpVersion) + "\"")
                logger.info(str(commandOutput))
                checkStep(step)

            if (litpPackageList != None):
                logger.info("Downloading Extra Packages for Product: " + str(litpProduct))
                packageListDict = buildPackageDict(litpPackageList)
                if str(isoLitpRebuild.strip()) == "/":
                    isoLitpRebuild = isoRebuildlocation
                else:
                    isoLitpRebuild = isoLitpRebuild.strip() + "/autoIsoBuild"
                downloadPackageList,downloadPackageCategoryList = downloadExtraPackages(clusterId, packageListDict, packagesDir, litpProduct)
                if (downloadPackageList == 1):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Unable to download extra Packages",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                litpProductLower = litpProduct.lower()
                mountIsoToMgtServer(remoteConnection,mgtServer,litpIsoName,lmsUploadDir,litpProductLower) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
                cleanOutOldEnmIso(remoteConnection,mgtServer,litpIsoName,softwareDir)
                litpMediaName, isoDirName = getIsoLayout(newISOLayout, litpIsoName, litpIsoVersion, drop)
                (ret,newIsoBaseName) = copyIsoContentToTmpArea(remoteConnection,mgtServer,isoLitpRebuild,mountMediaLocation,litpMediaName,litpProductLower)
                isoPath = mediaDirStructure + "/TOR/" + newIsoBaseName + "/"
                unmountIso(remoteConnection,mgtServer,litpProductLower) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not unmount iso on the management server",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                (ret,value,litpPackageList,installedPackageList,skippedPackageList) = replacePackages(packageListDict,remoteConnection,mgtServer,isoLitpRebuild,downloadPackageList,packagesDir,isoLitpRebuild,isoPath,installType)
                if ret != 0:
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Issue Replacing the packages in the mounted ISO",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                if installType == "initial_install":
                    return_code = yumUpgradeLitpPackages(remoteConnection, packageListDict, isoLitpRebuild)
                    if return_code != 0:
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not unmount iso on the management server",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                buildNewIso(remoteConnection, mgtServer, lmsUploadDir,reCreatedLitpIsoName,isoLitpRebuild) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Issue Building New Iso",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                litpIsoName = reCreatedLitpIsoName
                litpisopath = lmsUploadDir + "/" + litpIsoName
                cleanOutIsoContentTmpArea(remoteConnection,mgtServer,isoLitpRebuild) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not copy content of iso from mount point to temp area",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

    if (skipPatchInstall == "YES" and skipEnmInstall == "YES"):
        logger.info("CLUSTER DEPLOYED SUCCESSFULLY")
        exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        return 0

    # Check redhat release version
    ret, redhatReleaseVersion = runCommandGetOutput(remoteConnection, " cat " + config.get('DMT_AUTODEPLOY', 'rhelVersionFile'))

    if (deployProduct == "LITP2" and not isEdpIISupported and ' 7.' not in redhatReleaseVersion and "cloud" not in environment):
        # Install navisphere
        logger.info("---------------------------INSTALL NAVISPHERE ----------------------------")
        installNaviSphere = "yum install -y NaviCLI-Linux-64-x86-en_US"
        logger.info("Running cmd: %s", installNaviSphere)
        errMsg = "Error: Could not run the command " + installNaviSphere + " on the MS to install Navisphere"
        runCommand(remoteConnection,installNaviSphere) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        checkTheNaviSphereInstall = "ls /opt/Navisphere/"
        (ret,commandOutput) = runCommandGetOutput(remoteConnection,checkTheNaviSphereInstall)
        if (ret != 0 and "No such file or directory" in commandOutput):
            errMsg = "Error: Could not run the command " + checkTheNaviSphereInstall + " on the MS to check the Navi Sphere install"
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        checkStep(step)

        # Install unisphere
        logger.info("---------------------------INSTALL UNISPHERE -----------------------------")
        cmdCheckFileInDir = "ls /var/www/html/3pp/ | grep -i uemcli"
        logger.info("Running cmd: %s", cmdCheckFileInDir)
        return_code, command_output = remoteConnection.runCmdGetOutput(cmdCheckFileInDir)
        logger.info("Command output is: %s", str(command_output))
        if return_code == 0:
            installUniSphere = "yum install -y UnisphereCLI-Linux-64-x86-en_US"
            errMsg = "Error: Could not run the command " + installUniSphere + " on the MS to install Unisphere"
            logger.info("Running cmd: %s", installUniSphere)
            runCommand(remoteConnection,installUniSphere) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            checkTheUniSphereInstall = "ls /opt/emc/"
            logger.info("Running cmd: %s", checkTheUniSphereInstall)
            (ret,commandOutput) = runCommandGetOutput(remoteConnection,checkTheUniSphereInstall)
            if (ret != 0 and "No such file or directory" in commandOutput):
                errMsg = "Error: Could not run the command " + checkTheUniSphereInstall + " on the MS to check the Uni Sphere install"
                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        else:
            logger.info("File 'UnisphereCLI-Linux-64-x86-en_US' Not Found In 3pp Directory On MS for Installing UniSphereCLI.")

    if (deployProduct == "LITP2" and not isEdpIISupported):
        logger.info("*** Acquiring iso layout ***")
        mediaName, isoDirName = getIsoLayout(newISOLayout, isoName, isoVersion, drop)
        isoLocation = isoRebuildlocation + "/" + mediaDirStructure + "/TOR/" + mediaName + "/"
        isoPath = mediaDirStructure + "/TOR/" + mediaName + "/"
        checkStep(step)

    # Generate the SED file
    if not isEdpIISupported:
        logger.info("-----------------------------GENERATE SED FILE--------------------------------")
        cfgName = generateConfig(cluster, mgtServer, cfgTemplate, drop, isoName, osRhel6PatchDrop, osRhel7PatchDrop, osRhel79PatchDrop, osRhel88PatchDrop, servicePatchVersion, lmsUploadDir, installType, reCreatedIsoName, deployProduct,tmpArea, osRhel6PatchFileName, osRhel7PatchFileName, osRhel79PatchFileName, osRhel88PatchFileName, skipPatchInstall, litpisopath, enmInstRHEL7Patch, enmInstRHEL79Patch, enmInstRHEL88Patch, enmInstVersion)
        if environment == "physical":
            isSedValid = dmt.autoDeployUtils.validateSedFile(
                    cluster,
                    cfgName,
                    tmpArea,
                    product,
                    installType,
                    productSet)
            if failOnSedValidationFailure and not isSedValid:
                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"SED Validation Failed",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        if (cfgName == "1"):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not generate cfg file for cluster",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        checkStep(step)
        cfgLoc = lmsUploadConfig(mgtServer, tmpArea, lmsUploadDir, cfgName)
        if (cfgLoc == "1"):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not upload cfg file.",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        mediaArtifactList.append(os.path.basename(cfgLoc))
    # Wait for Luns to get optimized
    if installType == 'upgrade_install' and environment == "physical":
        lunExpansionFailSafeSwitch = config.get('DMT_AUTODEPLOY', 'lunExpansionFailSafeSwitch')
        logger.info('Fail safe switch is :' + str(lunExpansionFailSafeSwitch))
        # 1. scp getLunsExpanding script to MS
        (ret, lunExpnLoc) = uploadLunExpansionScriptToMS(mgtServer, lmsUploadDir)
        if ret != 0:
            logger.info("Failed to upload lun expansion check script to MS. Due to this failure, skipping Lun Expansion check.")
            #need to decide if we would fail the deployment or not
            if not int(lunExpansionFailSafeSwitch):
                exitDeployment(clusterId, failDepStatus, osVersion, osRhel6PatchVersion, osRhel7PatchVersion, osRhel79PatchVersion, osRhel88PatchVersion, litpIsoVersion,
                               isoVersion, packageList, "Error: Could not upload the getLunExpansion script to MS", tmpArea,
                               remoteConnection, clusterName, drop, cfgTemplate, xmlFile, deployProduct)
        else:
            # 2. Generate SED, copy to MS and store location in remote server
            logger.info('path to sed is ' + str(cfgLoc))

            # 3. Use location of xml file provided in deployment command

            if "http" in xmlFile:
                xmlFilePath = downloadFileFromUrl(xmlFile, mgtServer, lmsUploadDir, tmpArea)
            else:
                xmlFilePath = xmlFile
            logger.info('path to deployment is ' + str(xmlFilePath))

            # 4. Execute getLunExpansion script in remote MS, it should return list of name of luns that expanded
            command = 'python ' + lunExpnLoc + ' --sed ' + cfgLoc + ' --xml ' + xmlFilePath
            (ret, commandOutput) = runCommandGetOutput(remoteConnection, command)
            if ret != 0:
                # Either warn or stop execution
                logger.info('Error: Failed to check status of LUNS')
                if not int(lunExpansionFailSafeSwitch):
                    exitDeployment(clusterId, failDepStatus, osVersion, osRhel6PatchVersion, osRhel7PatchVersion, osRhel79PatchVersion, osRhel88PatchVersion,  litpIsoVersion,
                                   isoVersion, packageList, "Error: Filed to run command: " + str(command), tmpArea,
                                   remoteConnection, clusterName, drop, cfgTemplate, xmlFile, deployProduct)
            else:
                # 5. Loop through the list and wait execute logic for upto 90 tries until Lun is returned as optimized
                # 5.1# Parse the lun names output form the command output
                output = ''
                for item in commandOutput.splitlines():
                    if '[' in item and ']' in item:
                        output = item
                        break
                if output.strip('][') != '':
                    expandedLunsList = output.strip('][').split(', ')
                else:
                    expandedLunsList = []
                logger.info('Luns that are expanded as part of this upgrade : ' + str(expandedLunsList))

                # 5.2 Loop through all the luns that are expanding and wait for each to be optimized
                if len(expandedLunsList) > 0:
                    # 5.2.1 Retrieve SpIpaddress (SAN Ip) from Dmt to make navicli command
                    if ClusterToStorageMapping.objects.filter(cluster_id=clusterId).exists():
                        clusterStorageMapObj = ClusterToStorageMapping.objects.get(cluster_id=cluster.id)
                        storageSvr = Storage.objects.get(id=clusterStorageMapObj.storage_id)
                        if StorageIPMapping.objects.filter(storage=storageSvr.id, ipnumber="1").exists():
                            ipIdOneObject = StorageIPMapping.objects.get(storage=storageSvr.id, ipnumber="1")
                        else:
                            ipIdOneObject = None
                        if ipIdOneObject != None:
                            ipOneObject = IpAddress.objects.get(id=ipIdOneObject.ipaddr_id)
                        else:
                            ipOneObject = None
                        if ipOneObject != None:
                            SpIpAddress = ipOneObject.address
                            logger.info("Sp ip address is :" + str(SpIpAddress))
                        else:
                            logger.info("Error: Sp can't be none, please check DMT for the same")
                            # In case we are not exiting deployment, this list need to be emptied so that for loop would not run as SpIpAddress is not set
                            expandedLunsList = []
                            if not int(lunExpansionFailSafeSwitch):
                                exitDeployment(clusterId, failDepStatus, osVersion, osRhel6PatchVersion, osRhel7PatchVersion, osRhel79PatchVersion, osRhel88PatchVersion,
                                               litpIsoVersion,
                                               isoVersion, packageList, "Error: Sp Ip Address can't be none, please check DMT for the same ", tmpArea,
                                               remoteConnection, clusterName, drop, cfgTemplate, xmlFile, deployProduct)

                    for lun in expandedLunsList:
                        logger.info('Lun name is :' + str(lun))
                        # 5.3.1 Write helper function to make repetative remote call to check the status of selected LUN until Lun get optimized
                        return_code, return_output = checkLunStatus(remoteConnection,SpIpAddress, lun)
                        if return_code != 0 and return_code != 2:
                            logger.info('Error:' + str(return_output))
                            if not int(lunExpansionFailSafeSwitch):
                                exitDeployment(clusterId, failDepStatus, osVersion, osRhel6PatchVersion, osRhel7PatchVersion, osRhel79PatchVersion, osRhel88PatchVersion,
                                               litpIsoVersion,
                                               isoVersion, packageList,
                                               "Error: Something went wrong while waiting for lun to be optimized ", tmpArea,
                                               remoteConnection, clusterName, drop, cfgTemplate, xmlFile, deployProduct)
                        elif return_output == 2:
                            # Tip: Decide whether to exit deployment or not if timeout
                            logger.info('Timeout: ' + str(return_output))
                            if not int(lunExpansionFailSafeSwitch):
                                exitDeployment(clusterId, failDepStatus, osVersion, osRhel6PatchVersion, osRhel7PatchVersion, osRhel79PatchVersion, osRhel88PatchVersion,
                                               litpIsoVersion,
                                               isoVersion, packageList,
                                               "Error: Timeout: Lun" + str(lun) + " Could not be optimized within given time.", tmpArea,
                                               remoteConnection, clusterName, drop, cfgTemplate, xmlFile, deployProduct)
                        else:
                            logger.info('Lun: ' + str(lun) + ' is optimised, we can continue and check others :) ')
                else:
                    logger.info('No LUN is expanding during this upgrade')

    if ( reStartFromStage == "no"):
        logger.info("Deploying " + str(cluster) + " from management server " + str(mgtServer))
        deployScriptsToMgtServer(remoteConnection, mgtServer, deployScriptVersion, deployRelease, lmsUploadDir,tmpArea,product,scriptFile) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not Upload Deployment Scripts",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        if "cloud" in env:
            ret = placeCloudUuidUpdateScript(remoteConnection, lmsUploadDir)
            if ret != 0:
                errMsg = "Error: Issue placing the Cloud UUID Update Script"
                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
        if not isEdpIISupported:
            if ( mountIsoAgain == "yes" ):
                errIso = "Could not download the iso to the management server"
                errMd5 = "Md5 did not match"
                if (deployProduct == "LITP2"):
                    while threads[1].isAlive():
                        logger.info("Artifact " + str(isoName) + " still downloading, please wait...")
                        time.sleep(5)
                    logger.info("Artifact " + str(isoName) + " download is complete proceeding with installation...")
                    checkStep(step)
                    checkIsoMd5Sum(remoteConnection, mgtServer, isoName, lmsUploadDir,tmpArea,isoUrl,hubIsoUrl) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMd5,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)
                else:
                    downloadIsoToMgtServer(remoteConnection, mgtServer, isoName, lmsUploadDir,tmpArea,isoUrl) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errIso,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                lastIsoImportedIndicator(remoteConnection, mgtServer, lmsUploadDir, mediaArtifactList, lastIsoImportedFile) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not create last iso imported file",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
            else:
                # get the last iso imported
                (ret,command_output) = getLastUploadedIso(remoteConnection,mgtServer,lmsUploadDir,lastIsoImportedFile)
                commandOutput = command_output[command_output.index("ERICenm"):].replace("\n", "")
                if (ret != 0):
                    errMsg = "Error: Issue with retrieving the last uploaded ISO version please ensure there is a entry with the file " + lmsUploadDir + "/" + lastIsoImportedFile + " else let the scipt upload an iso version"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                else:
                    isoName = commandOutput
                checkStep(step)
            if ( installType == "initial_install" or "upgrade" in installType):
                #RHEL 6 Patches
                if (osRhel6PatchDrop != None):
                    if deployProduct == "LITP2" and (skipPatchInstall == "NO" and skipPatchInstall != "RHEL6"):
                        errMsg = "Error: Could not download the " + str(osRhel6PatchFileName) + " file to the management server"
                        while threads[2].isAlive():
                            logger.info("Artifact " + str(osRhel6PatchFileName) + " still downloading, please wait...")
                            time.sleep(5)
                        logger.info("Artifact " + str(osRhel6PatchFileName) + " download complete proceeding with installtion...")
                        checkStep(step)
                        checkIsoMd5Sum(remoteConnection, mgtServer, osRhel6PatchFileName, lmsUploadDir, tmpArea, osRhel6PatchFileUrl, osRhel6PatchFileHubUrl) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Md5 did not match",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                        checkStep(step)
                    checkStep(step)

                # Service Patches
                if (servicePatchVersion != None):
                    uploadServicePatches(remoteConnection, mgtServer, servicePatchVersion, lmsUploadDir,tmpArea) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not upload the Service Patches to management server",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)

                # RHEL 7 Patches
                if osRhel7PatchDrop != None and (LooseVersion(enmInstRHEL7Patch) <= LooseVersion(enmInstVersion)):
                    if deployProduct == "LITP2" and (skipPatchInstall == "NO" and skipPatchInstall != "RHEL7"):
                        errMsg = "Error: Could not download " + str(osRhel7PatchFileName) + " file to the management server"
                        if len(threads) > 3:
                            while threads[3].isAlive():
                                logger.info("Artifact " + str(osRhel7PatchFileName) + " still downloading, please wait...")
                                time.sleep(5)
                            logger.info("Artifact " + str(osRhel7PatchFileName) + " download complete proceeding with installtion...")
                            checkStep(step)
                            checkIsoMd5Sum(remoteConnection, mgtServer, osRhel7PatchFileName, lmsUploadDir,tmpArea, osRhel7PatchFileUrl, osRhel7PatchFileHubUrl) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Md5 did not match",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)

                # RHEL 7.9 Patches
                if osRhel79PatchDrop != None and (LooseVersion(enmInstRHEL79Patch) <= LooseVersion(enmInstVersion)):
                    if deployProduct == "LITP2" and (skipPatchInstall == "NO" and skipPatchInstall != "RHEL79"):
                        errMsg = "Error: Could not download " + str(osRhel79PatchFileName) + " file to the management server"
                        if len(threads) > 4:
                            while threads[4].isAlive():
                                logger.info("Artifact " + str(osRhel79PatchFileName) + " still downloading, please wait...")
                                time.sleep(5)
                            logger.info("Artifact " + str(osRhel79PatchFileName) + " download complete proceeding with installtion...")
                            checkStep(step)
                            checkIsoMd5Sum(remoteConnection, mgtServer, osRhel79PatchFileName, lmsUploadDir,tmpArea, osRhel79PatchFileUrl, osRhel79PatchFileHubUrl) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Md5 did not match",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                            checkStep(step)

                # RHEL 8.8 Patches
                if osRhel88PatchDrop != None and (LooseVersion(enmInstRHEL88Patch) <= LooseVersion(enmInstVersion)):
                    if deployProduct == "LITP2" and (skipPatchInstall == "NO" and skipPatchInstall != "RHEL88"):
                        errMsg = "Error: Could not download " + str(osRhel88PatchFileName) + " file to the management server"
                        if len(threads) > 5:
                            while threads[5].isAlive():
                                logger.info("Artifact " + str(osRhel88PatchFileName) + " still downloading, please wait...")
                                time.sleep(5)
                            logger.info("Artifact " + str(osRhel88PatchFileName) + " download complete proceeding with installtion...")
                            checkStep(step)
                            checkIsoMd5Sum(remoteConnection, mgtServer, osRhel88PatchFileName, lmsUploadDir,tmpArea, osRhel88PatchFileUrl, osRhel88PatchFileHubUrl) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Md5 did not match",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                            checkStep(step)

            if environment == "physical" and not isEdpIISupported:
                if nasConfig is not None and nasRhelPatch is not None:
                    checkStep(step)
                    nasConfigThread = threads[-2]
                    nasRhelPatchThread = threads[-1]
                    dmt.utils.waitForNasArtifactsToDownload(nasConfigThread, nasRhelPatchThread)
                    checkStep(step)
            if (packageList != None):
                logger.info("Downloading Extra Packages for Product: " + str(product))
                packageListDict = buildPackageDict(packageList)
                if str(isoRebuild.strip()) == "/":
                    isoRebuild = isoRebuildlocation
                else:
                    isoRebuild = isoRebuild.strip() + "/autoIsoBuild"
                downloadPackageList,downloadPackageCategoryList = downloadExtraPackages(clusterId, packageListDict, packagesDir, product)
                if (downloadPackageList == 1):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Unable to download extra Packages",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                mountIsoToMgtServer(remoteConnection,mgtServer,isoName,lmsUploadDir,product) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not mount iso onto the management server",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
                cleanOutOldEnmIso(remoteConnection,mgtServer,isoName,softwareDir)
                checkStep(step)
                (ret,newIsoBaseName) = copyIsoContentToTmpArea(remoteConnection,mgtServer,isoRebuild,mountMediaLocation,mediaName,product)
                checkStep(step)
                if (ret != 0):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not copy content of iso from mount point to temp area",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                isoLocation = isoRebuild + "/" + mediaDirStructure + "/TOR/" + newIsoBaseName + "/"
                isoPath = mediaDirStructure + "/TOR/" + newIsoBaseName + "/"
                isoDirName = newIsoBaseName
                unmountIso(remoteConnection,mgtServer,product) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not unmount iso on the management server",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                errMsg = "Error: Issue Replacing the packages in the mounted ISO"
                (ret,value,packageList,installedPackageList,skippedPackageList) = replacePackages(packageListDict,remoteConnection,mgtServer,isoRebuild,downloadPackageList,packagesDir,isoRebuild,isoPath,installType)
                if ret != 0:
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                buildNewIso(remoteConnection, mgtServer, lmsUploadDir,reCreatedIsoName,isoRebuild) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Issue Building New Iso",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                isoName = reCreatedIsoName
                cleanOutIsoContentTmpArea(remoteConnection,mgtServer,isoRebuild) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not copy content of iso from mount point to temp area",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                if exitAfterISORebuild:
                    return 0
        #install the required ERICenminst package the deployment descriptor package
        if (deployProduct == "LITP2" and reInstallInstllScript != "no" and (not isEdpSupported and not isEdpIISupported)):
            logger.info("---------------------------INSTALL ERICenminst package and other packages---------------------------")
            # Mount the ENM iso and install the install package
            errMsg = "Error: Could not mount the " + str(product) + " iso onto the management server to install the installer package"
            mountIsoToMgtServer(remoteConnection,mgtServer,isoName,lmsUploadDir,product) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            checkStep(step)
            instPackage=[config.get('DMT_AUTODEPLOY', 'enmFcapsHealthcheck'),config.get('DMT_AUTODEPLOY', 'enmInstPackage'),config.get('DMT_AUTODEPLOY', 'deploymentTemplatePackage'),config.get('DMT_AUTODEPLOY', 'enmDSTUtilitiesPackage'),config.get('DMT_AUTODEPLOY', 'enmlitpSanEmcPackage')]
            # Check the structure of the iso what type have we
            (commonIsoLocation,structure,deploymentPackageLocation) = checkIsoStructure(remoteConnection,"/media/" + product + "/")
            logger.info("---------- The instPackage list for yum install/upgrade: " + str(instPackage))
            for package in instPackage:
                logger.info("Package to be installed now is: %s", str(package))
                errMsg = "Error: Issue with the adding of the package " + package + " to the MS"
                mediaDir = "/media/" + product + "/" + deploymentPackageLocation
                if str(package) == str(config.get('DMT_AUTODEPLOY', 'enmlitpSanEmcPackage')):
                    mediaDir = "/media/" + product  + "/" + "/repos/ENM/db/"
                logger.info("---------- Listing the directory content:")
                cmdListFilesInDir = "ls -alt " + str(mediaDir)
                return_code, command_output = remoteConnection.runCmdGetOutput(cmdListFilesInDir)
                logger.info("---------- Directory content: " + str(command_output))
                logger.info("mediaDir parameter value is: %s", str(mediaDir))
                ret = doesPackageExistInDirectory(remoteConnection,mediaDir,package)
                logger.info("---------- Return value from (doesPackageExistsInDirectory) for [" + str(package) + "] - " + str(ret))
                if ret == 0:
                    if "upgrade" in torinstDeployParameter:
                        logger.info("---------- Next package for yum upgrade: " + str(package + "*"))
                        ret, output = yumUpdateArtifact(remoteConnection,mediaDir,package + "*")
                        logger.info("---------- Output of yum upgrade: " + str(output))
                        logger.info("---------- Return command from yum upgrade: " + str(ret))
                        if ret != 0:
                            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                        packageNotInstalledString = "Package " + str(package) + " not installed"
                        if packageNotInstalledString in output:
                            logger.info("---------- Package not installed : " + str(ret))
                            yumRemoveInstall(remoteConnection,package,mediaDir,package + "*") == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    else:
                        yumRemoveInstall(remoteConnection,package,mediaDir,package + "*") == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                else:
                    logger.warning("Package: '" + str(package) + "' was not found in local ISO Mount: '" + str(mediaDir) + "', therefore will not be installed or updated.")
                checkStep(step)
            if "cloud" not in env:
                logger.info("Executing the sync_puppet_check on the server to check puppet status")
                sync_puppet_check(remoteConnection, "status")
                logger.info("Executing the sync_puppet_check on the server to allow puppet-agent files to re-sync")
                sync_puppet_result = sync_puppet_check(remoteConnection, "sync", int(config.get('DMT','puppetTimeout')))
                if (sync_puppet_result != 0):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: There is an Issue with Puppet on this system, existing",tmpArea,remoteConnection)
                logger.info("Executing the sync_puppet_check on the server to check puppet status")
                sync_puppet_check(remoteConnection, "status")

            #Update the watermark value back to 84 from 81
            logger.info('--------------Updating the watermark value from 81 to 84----------------')
            filePath =  config.get('DMT_AUTODEPLOY','enmInstEtc')
            fileName = 'enminst_cfg.ini'
            localFilePath = tmpArea
            configName = 'SAN_POOL_USAGE_NS'
            newValue = 84
            ret, output = updateConfigValues(mgtServer, filePath, fileName, localFilePath,  configName, newValue)
            if ret != 0:
                logger.info('--------------Update of watermark value failed----------------')
                logger.warning(output)
            else:
                logger.info('--------------Update of watermark value completed with success----------------')
            errMsg = "Error: Could not unmount the " + str(product) + " iso on the management server"
            unmountIso(remoteConnection,mgtServer,product) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            checkStep(step)
            reInstallInstllScript = "no"

        if ( "upgrade" in installType and not isEdpSupported):
            (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
            ret = execUpgradePrecheck(remoteConnection, "enm_upgrade_prechecks.sh", None)
            if int(ret) != 0:
                logger.error("Error: There was an system/environment error detected whilst running the enm_upgrade_prechecks.sh script, please Investigate.")
                """This change have to be +2 but not submited to master before clarified with MT, investigation on HC script is ongoing."""
                if ignoreUpgradePrecheck == "NO":
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: enm_upgrade_prechecks.sh script has been failed, exiting",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
            isoPathName = str(softwareDir) + "/" + str(isoName)
            ret = execUpgradePrecheck(remoteConnection, "pre_upgrade_rpms.sh", isoPathName)
            if int(ret) != 0:
                logger.error("Error: There was an system/environment error detected whilst running the enm_upgrade_prechecks.sh script, please Investigate.")
                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: enm_upgrade.sh script has been failed, exiting",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
        #Below is run for UG and Snap as defualt torinstDeployParameter for Sanpshot is UG
        if ("upgrade" in torinstDeployParameter and not isEdpSupported):
            commandType="upgrade"
            (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
            if (ret != 0):
                 exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not create ssh connection to MS during snapshot creation",tmpArea,remoteConnection)
            ret = removeMsPatchFile(remoteConnection, mgtServer)
            if ret != 0:
                logger.info("Issue removing MS Patched File from ENMInst Runtime")
            logger.info("Executing the vcs_check before snapping procedure on the server")
            vcs_check_groups_result = vcs_check(remoteConnection, "groups")
            vcs_check_systems_result = vcs_check(remoteConnection, "systems")
            deployed_system_artifact_result = deployed_system_artifact_check(remoteConnection)
            ret = verifyDiskRedundancyOnDbNodesWorkaround(remoteConnection, cluster, masterUserPassword)
            if ret != 0:
                logger.error("Error encountered while applying workaround. See jira CIS-42100")
        if ( deployProduct == "LITP2" ):
            if ( xmlFile == None ):
                if ( "physical" in environment ):
                    xmlFile=config.get('DMT_AUTODEPLOY', 'physicalXmlFile')
                elif ( "cloud" in environment ):
                    xmlFile=config.get('DMT_AUTODEPLOY', 'cloudXmlFile')
            elif ( "http" in xmlFile ):
                xmlFile = downloadFileFromUrl(xmlFile,mgtServer,lmsUploadDir,tmpArea)
                if( lmsUploadDir not in xmlFile):
                    errMsg = "Error: Could not download the specified file : " + str(xmlFile)
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
            elif ( "::" in xmlFile ):
                qualifier = "::"
                slice = xmlFile.split(qualifier)[0]
                xmlSliceName = xmlFile.split(qualifier)[1]
                if slice.lower() == "slice":
                    # Mount the ENM iso and install the install package
                    errMsg = "Error: Could not mount the " + str(product) + " iso onto the management server to get the version of DeploymentTemplate package within the ISO"
                    mountIsoToMgtServer(remoteConnection,mgtServer,isoName,lmsUploadDir,product) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection)
                    checkStep(step)
                    # Get the version of the snapshot from the iso and download snap to MS in /var/tmp
                    (artifact,group,secondArtifact,secondGroup,packageVersion) = getSlicesSnapFilesInfo(remoteConnection,"/media/" + product + "/",)
                    if artifact == None or group == None or secondArtifact == None or secondGroup == None or packageVersion == None:
                        errMsg = "Error: Issue getting the information for the slice zip files"
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
                    checkStep(step)
                    (ret, snapVersion) = downloadSlices(remoteConnection,artifact,group,packageVersion,lmsUploadDir)
                    if ret != 0 or snapVersion == None:
                        errMsg = "Error: Issue downloading the first slices file from Nexus"
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
                    (ret, secondSnapVersion) = downloadSlices(remoteConnection,secondArtifact,secondGroup,packageVersion,lmsUploadDir)
                    if ret != 0 or secondSnapVersion == None:
                        secondSliceFileExists = False
                        warningMsg = "Warning: Issue downloading the second slices file from Nexus"
                        logger.info(str(warningMsg))
                    else:
                        secondSliceFileExists = True
                    checkStep(step)
                    zipFileName = lmsUploadDir + "/" + str(artifact) + "-" + str(snapVersion) + ".zip"
                    ret = yumInstallApp(remoteConnection,"unzip")
                    if ret != 0:
                        errMsg = "Error: Issue installing the unzip application"
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
                    checkStep(step)
                    # Ensure the old slices have been removed
                    ret = runCommand(remoteConnection,"rm -rf " + lmsUploadDir + "/slices")
                    checkStep(step)
                    ret = unzipFile(remoteConnection,zipFileName,lmsUploadDir)
                    if ret != 0:
                        errMsg = "Error: Issue unzipping the first slices zip file within " + str(lmsUploadDir)
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
                    if secondSliceFileExists:
                        secondZipFileName = lmsUploadDir + "/" + str(secondArtifact) + "-" + str(secondSnapVersion) + ".zip"
                        ret = unzipFile(remoteConnection,secondZipFileName,lmsUploadDir)
                        if ret != 0:
                            errMsg = "Error: Issue unzipping the second slices zip file within " + str(lmsUploadDir)
                            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
                    (ret,xmlFile) = getSliceXmlFromSliceFile(remoteConnection,lmsUploadDir + "/slices/",xmlSliceName)
                    if ret != 0 or xmlFile == None:
                        errMsg = "Error: Unable to get the xmlfile entered within the slices zip file"
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
                    errMsg = "Could not unmount the " + str(product) + " iso on the management server"
                    unmountIso(remoteConnection,mgtServer,product) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection)
                    checkStep(step)
                else:
                    errMsg = "Error: The entries for xmlFile parameter are not supported if entering a slice then it needs to be in the form --xmlFile slice::<sliceName>"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea)
        patchInstall = True
        if skipPatchInstall != "NO":
            patchInstall = False
        # Patch the Server
        patch88 = None
        if not isEdpIISupported:
            rhelPatchFileNames = [osRhel6PatchFileName,osRhel7PatchFileName,osRhel79PatchFileName,osRhel88PatchFileName]
            installPatches = []
            if (deployProduct == "LITP2" and patchInstall == True and skipPatchInstall != None and "upgrade" not in installType):
                patchesInstallScript = config.get('DMT_AUTODEPLOY', 'patchesInstallScript')
                installPatchesCmd = str(patchesInstallScript) + " -p "
                for filename in rhelPatchFileNames:
                    if filename != "" and filename != None:
                        installPatches.append(lmsUploadDir + "/" + filename)
                installPatchesCmd += ", ".join(installPatches)
                installPatchesCmd += " -v"
                logger.info("Running " + str(installPatchesCmd))
                successCommentPatches = "After the reboot"
                errorCommentPatches = "Enminst Exiting"
                ret = remoteConnection.runChild(installPatchesCmd, successCommentPatches, errorCommentPatches)
                if (ret != 0):
                    errMsg = "Error: Could not install the Patches Successfully: return code " + str(ret)
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                dmt.createSshConnection.checkSSHConnection(fqdnMgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Issue re-establishing Connection to Management Server",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
                patchesInstallLogFile=config.get('DMT_AUTODEPLOY', 'patchesInstallLogFile')
                listOfItemsToSearch = ["RHEL patching successfully executed","Cleaning up"]
                errMsg = "Error: Could not find the item within the file, \"" + str(patchesInstallLogFile)
                searchFileForString(remoteConnection,patchesInstallLogFile,listOfItemsToSearch) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                if (skipEnmInstall == "YES"):
                    logger.info("CLUSTER DEPLOYED SUCCESSFULLY")
                    exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    return 0

        if (deployProduct == "LITP2" and environment == "cloud"):
            redfishEnmIsoVersion = config.get('DMT_AUTODEPLOY', 'redfishEnmIsoVersion')
            ipmiRemovedEnmIsoVersion = config.get('DMT_AUTODEPLOY', 'ipmiRemovedEnmIsoVersion')
            if ipmiVersion != None and (LooseVersion(ipmiRemovedEnmIsoVersion) > LooseVersion(isoVersion)):
                logger.info("---------------------INSTALL IPMI---------------------")
                ipmiLocation = config.get('DMT_AUTODEPLOY', 'ipmiLocation')
                ipmiName = config.get('DMT_AUTODEPLOY', 'ipmiName')
                errMsg = "Error: Issue with the adding of the package " + ipmiName + " to the MS"
                completeArtifactURL = ipmiLocation + "/" + ipmiVersion + "/" + ipmiName + "-" + ipmiVersion + ".rpm"
                artifactName = dmt.cloud.downloadArtifact(packagesDir,completeArtifactURL)
                if type(artifactName) == int:
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                downloadPackageList = [artifactName]
                uploadExtraPackages(downloadPackageList,mgtServer,packagesDir,lmsUploadDir) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Issue Uploading the ipmi package for cloud pxe booting",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                yumRemoveInstall(remoteConnection,ipmiName,lmsUploadDir,artifactName) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
            if redfishVersion != None and (LooseVersion(redfishEnmIsoVersion) <= LooseVersion(isoVersion)):
                logger.info("---------------------INSTALL REDFISH---------------------")
                redfishLocation = config.get('DMT_AUTODEPLOY', 'redfishLocation')
                redfishName = config.get('DMT_AUTODEPLOY', 'redfishName')
                errMsg = "Error: Issue with the adding of the package " + redfishName + " to the MS"
                completeArtifactURL = redfishLocation + "/" + redfishVersion + "/" + redfishName + "-" + redfishVersion + ".rpm"
                artifactName = dmt.cloud.downloadArtifact(packagesDir,completeArtifactURL)
                if type(artifactName) == int:
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                downloadPackageList = [artifactName]
                uploadExtraPackages(downloadPackageList,mgtServer,packagesDir,lmsUploadDir) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion, packageList,"Issue Uploading the redfish package for cloud pxe booting",tmpArea,remoteConnection, clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                yumRemoveInstall(remoteConnection,redfishName,lmsUploadDir,artifactName) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                checkStep(step)
        # Depending on the type of install we want to either clean down the system for initial install
        # or recreate the iso for upgrade
        cleanPatches = True
        if skipPatchInstall == "YES":
            cleanPatches = False
        if (skipEnmInstall != "YES" or cleanPatches == True):
            if installType == "upgrade_install":
                if environment == "physical":
                    exitStage="System successfully upgraded"
                else:
                    exitStage="Deployment for upgrade_app complete"
            elif deployProduct == "LITP2":
                exitStage="All functions completed"
            else:
                exitStage="Exiting stage - apply_ms_patches"
                if deployProduct == "LITP2" and reDeployVMS != "NO":
                    if (cleanDownVMS(remoteConnection,mgtServer) != 0):
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,None,"Error: Issue cleaning down the Virtual MS",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    checkStep(step)

            if stageOne != "false":
                try:
                    if ( installType == "initial_install" or LooseVersion(deployScriptVersion) < LooseVersion(config.get('DMT_AUTODEPLOY', 'deploymentScriptVersionNum'))):
                        tempModelXML = config.get('DMT_AUTODEPLOY', 'tempModelXML')
                    else:
                        tempModelXML = config.get('DMT_AUTODEPLOY', 'upgradeTempModelXML')
                except Exception as e:
                    dmt.utils.dmtError("There was an exception getting the temporary Model XML from DMT_AUTODEPLOY config " + str(e))
                logger.info("Executing pre install steps for Infra Stage 1")
                exitDeployment(clusterId,busyDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Executing pre install steps for Infra Stage 1",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                deployReturn = execStageOnePreInstall(remoteConnection, lmsUploadDir, xmlFile, tempModelXML)
                if (deployReturn != 0):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not complete stage 1 of the deployment",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                xmlFile = tempModelXML
            elif stageTwo != "false":
                logger.info("Executing Stage 2 - Applications")
                deployReturn = execStageTwo(remoteConnection, lmsUploadDir, isoName, xmlFile, cfgLoc)
                if (deployReturn != 0):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not complete stage 2 of the deployment",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                logger.info("CLUSTER DEPLOYED SUCCESSFULLY")
                exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Completed Successfully",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                return 0
            # Execute the deployment based on whatever XML has been generated from above (infra install or full install)
            if isEdpSupported:
                deployReturn = execDeployEdp(clusterId, productSet, mediaArtifactList, xmlFile, cfgLoc, edpVersion, edpProfileList, edpPackageList, extraParameter, hcInclude, ignoreUpgradePrecheck, deployScriptVersion, originalEnmIsoName, originalLitpIsoName, kickstartFileUrl, skipNasPatchInstall)
            else:
                deployReturn = execDeploy(remoteConnection, mgtServer,lmsUploadDir,cfgLoc,"1",torinstDeployParameter,exitStage,errorStage,reInstallInstllScript,reStartFromStage,featTest,stopAtStage,skipStage,extraParameter,isoDirName,deployProduct,isoName,product,xmlFile,commandType,secondRunSkipPatches, osMedia, hcInclude, deployScriptVersion, enmInstVersion, skipOsInstall)
            if (deployReturn != 0):
                errMsg = "Error: Issue running the deployment"
                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            # If patches were deployed with the upgrade then the patches are added and the MS reboot on the next iteration in the if below we load the litp and enm appliction omitting the patches
            if installType == "upgrade_install" and cleanPatches == True:
                ret = executeSshConnectionCheckOnMs(remoteConnection,mgtServer,60)
                if ret != 0:
                    errMsg = "Error: Could not get a connection to the MS Server"
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

                # Check if Deployment Scripts is required to be downloaded
                deployScriptsDir = lmsUploadDir + "/deploy"
                (ret, commandOutput) = remoteConnection.runCmdGetOutput('[ -d '+ str(deployScriptsDir) +' ] && echo "Directory exist" || echo "Directory does not exist"')
                logger.info(commandOutput)
                if "Directory does not exist" in str(commandOutput):
                    # Set the lmsUploadDir by checking does the software directory exist already if it does use it
                    (ret, lmsUploadDir) = setUploadDirectory(remoteConnection,installType,deployScriptVersion)
                    if ret != 0:
                        errMsg = "Error: Could not create ssh connection to MS"
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    deployScriptsToMgtServer(remoteConnection, mgtServer, deployScriptVersion, deployRelease, lmsUploadDir,tmpArea,product,scriptFile) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not Upload Deployment Scripts",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

                if not isEdpSupported:
                    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
                    enmHealthCheckSystemServices = config.get('DMT_AUTODEPLOY', 'enmHealthCheckSystemServices')
                    cmd = str(enmInstDir) + str(enmHealthCheckSystemServices)
                    ret = executeLoopServiceCheck(remoteConnection,cmd)
                    if ret != 0:
                        errMsg = "Error: All Services have not come online. Please investigate.."
                        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                ret = executeLoopServiceGroupCheck(remoteConnection,lmsUploadDir)
                if ret != 0:
                    errMsg = "Error: All Service Group have not come online. Please investigate.."
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                if LooseVersion(deployScriptVersion) < LooseVersion(config.get('DMT_AUTODEPLOY', 'deploymentScriptVersionNum2')):
                    secondRunSkipPatches = True
                else:
                    secondRunSkipPatches = False
                if (skipEnmInstall != "YES"):
                    if not isEdpSupported:
                        kernelVerAfterDeploy = None
                        ret, kernelVerAfterDeploy = runCommandGetOutput(remoteConnection, " uname -r")
                        logger.info("*** Kernel check After UG ***")
                        logger.info(kernelVerAfterDeploy)
                        if kernelVerBeforeDeploy and kernelVerBeforeDeploy != kernelVerAfterDeploy:
                            deployReturn = execDeploy(remoteConnection, mgtServer,lmsUploadDir,cfgLoc,"1",torinstDeployParameter,exitStage,errorStage,reInstallInstllScript,reStartFromStage,featTest,stopAtStage,skipStage,extraParameter,isoDirName,deployProduct,isoName,product,xmlFile,commandType,secondRunSkipPatches, osMedia, hcInclude, deployScriptVersion, enmInstVersion, skipOsInstall)
                            if (deployReturn != 0):
                                errMsg = "Error: Issue running the deployment"
                                exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not deploy stage 1 of the cluster",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                else:
                    logger.info("ENM Deployment Skipped")
                    logger.info("CLUSTER DEPLOYED SUCCESSFULLY")
                    exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    return 0
            if stageOne != "false":
                logger.info("Executing post install steps for Infra Stage 1")
                deployReturn = execStageOnePostInstall(remoteConnection,lmsUploadDir,cfgLoc,environment,mgtServer,"create")
                if (deployReturn != 0):
                    exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not complete post install steps for Infra stage 1",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            # If we are running a Litp2 install we can exit at this point
            if deployProduct == "LITP2":
                logger.info("SYSTEM DEPLOYED SUCCESSFULLY")
                copyPrivateKey(remoteConnection)
                ###############################
                if "upgrade" not in installType:
                    # This Ensures that all the peer nodes are up to ensure we can reset the password
                    logger.info("Waiting 10 minutes for the system to initialise")
                    time.sleep(600)
                    #offline neo4j - temp fix to be removed in future - lmirbe
                    if ( installType == "initial_install" and skipEnmInstall != "YES" and environment == "physical"):
                        logger.info("Attempting to Offline Neo4J.")
                        enmInstLibDir = config.get('DMT_AUTODEPLOY', 'enmInstLib')
                        enmInstOfflineNeo4J = config.get('DMT_AUTODEPLOY', 'enmInstOfflineNeo4J')
                        cmd = ". " + str(enmInstLibDir) + str(enmInstOfflineNeo4J)
                        ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
                        if ret != 0:
                            errMsg = "Error: Neo4J Script return non zero exit code, it returned " + str(ret) + ". Please investigate.."
                        logger.info("Neo4J Service offline script return code: " + str(ret))
                        #offline neo4j - end of workaround
                        ###############################
                        #switch_db_groups
                        logger.info("Attempting to switch db groups.")
                        switchDbGroups = config.get('DMT_AUTODEPLOY', 'switchDbGroups')
                        cmd = "\"cd " + str(enmInstLibDir) + str(switchDbGroups) + "\""
                        ret = remoteConnection.runCmdSimple(cmd, "tty-ssh")
                        if ret != 0:
                            errMsg = "Error: SwitchDbGroups Script return non zero exit code, it returned " + str(ret) + ". Please investigate.."
                        logger.info("Switch db groups script return code: " + str(ret))
                        ###############################
                    if stageOne != "false":
                        if environment == "cloud":
                            cloudPostInstallCommands(remoteConnection,cluster,lmsUploadDir,user,litpUsername,masterUserPassword,cfgLoc,tmpArea,mgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error running cloud post install commands",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                            powerCyclePeerNodes(remoteConnection,lmsUploadDir,"offline",cfgLoc,tmpArea,user,masterUserPassword) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error offlining the Peer Nodes",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    else:
                        if environment == "cloud":
                            cloudPostInstallCommands(remoteConnection,cluster,lmsUploadDir,user,litpUsername,masterUserPassword,cfgLoc,tmpArea,mgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error running post install commands",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                        else:
                            physicalPostInstallCommands(remoteConnection,cluster,lmsUploadDir,user,litpUsername,masterUserPassword,cfgLoc,tmpArea,mgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error running post install commands",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                    # Clean up
                    softwareDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
                    (ret,message) = cleanSoftwareDirectory(remoteConnection, softwareDir, lastIsoImportedFile, mediaArtifactList)
                    # This section only needs to be executed for older deployments that are still using /var/tmp/ as the upload directory
                    if ( "var" in lmsUploadDir ):
                        (ret,message) = cleanUpAfterSuccessfullInitialInstall(remoteConnection,mgtServer,lmsUploadDir,softwareDir,mediaArtifactList)
                        if (ret != 0):
                            logger.info(message)
                if environment == "physical":
                    diagnosticDataPresentation(remoteConnection, clusterId)

                if not MediaArtifactServiceScanned.objects.filter(media_artifact_version=isoVersion).exists():
                    associatingVmServicesWithPackages(remoteConnection, clusterId, isoVersion)

                exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                return 0
            if installType == "upgrade_install":
                if environment == "cloud":
                    exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
                return 0
        else:
            logger.info("ENM Deployment Skipped")
            logger.info("CLUSTER DEPLOYED SUCCESSFULLY")
            exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
            return 0

    else:
        # This section is depricated for the new ENMinst installer package
        logger.info("Re-Starting Deployment from " + str(reStartFromStage) + " for " + str(cluster) + " from management server " + str(mgtServer))
        if installType == "upgrade_install":
            if environment == "physical":
                exitStage="Deployment for upgrade complete"
            else:
                exitStage="Deployment for upgrade_app complete"
        else:
            exitStage="Exiting stage - apply_ms_patches"
        deployReturn = execDeploy(remoteConnection, mgtServer,lmsUploadDir,cfgLoc,"1",torinstDeployParameter,exitStage,errorStage,reInstallInstllScript,reStartFromStage,featTest,stopAtStage,skipStage,extraParameter,isoDirName,deployProduct,isoName,product,xmlFile,commandType,secondRunSkipPatches, osMedia, hcInclude, deployScriptVersion, enmInstVersion, skipOsInstall)
        if (deployReturn != 0):
            exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Error: Could not complete stage 1 of the deployment",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

    # Section below is only used for initial install after the rebot of the MS node
    dmt.createSshConnection.checkSSHConnection(fqdnMgtServer) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Issue re-establishing Connection to Management Server",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    reStartFromStage = "no"
    if installType == "initial_install":
        if environment == "physical":
            exitStage = "Deployment for install complete"
        else:
            exitStage = "Deployment for install_cloud complete"
    if (stopAtStage != "NO"):
        exitStage="WARNING : Stopping at stage"
    execDeploy(remoteConnection, mgtServer,lmsUploadDir,cfgLoc,"2",torinstDeployParameter,exitStage,errorStage,reInstallInstllScript,reStartFromStage,featTest,stopAtStage,skipStage,extraParameter,isoDirName,deployProduct,isoName,product,xmlFile,commandType,secondRunSkipPatches,osMedia,hcInclude,deployScriptVersion,enmInstVersion,skipOsInstall) == 0 or exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Could not complete stage 2 of the deployment",tmpArea,remoteConnection,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    logger.info("CLUSTER DEPLOYED SUCCESSFULLY")
    exitDeployment(clusterId,endDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,"Deployment Successful",None,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)
    return 0

def checkLunStatus(remoteConnection, SpIpAddress, lun):
    response_code = 0
    response_message = ''
    retries = 0
    time.sleep(10)
    naviCliCommand = '/opt/Navisphere/bin/naviseccli -h ' + str(SpIpAddress) + ' -user admin -password password -scope 0 lun -list -name ' + str(lun)
    while (retries != 120):
        logger.info('Waiting for lun ' + str(lun) + 'to get optimized | TRY : ' + str(retries + 1) + '/120')
        (ret, commandOutput) = runCommandGetOutput(remoteConnection, naviCliCommand)
        if ret != 0:
            logger.info('Failed to execute command ' + str(naviCliCommand) + 'with error output ' + str(commandOutput))
            response_code, response_message = ret, commandOutput
            break
        if 'Current Operation:  None' in commandOutput:
            response_code, response_message = ret, 'Lun: ' + str(
                lun) + ' is optimised, we can continue and check others :) '
            break
        time.sleep(30)
        retries += 1
        continue

    if retries == 120:
        response_code, response_message = 2, 'Timeout while waiting for lun ' +str(lun)+ 'to get optimized'

    return response_code, response_message

def deployMainCsl(clusterId, drop, product, environment, packageList, cfgTemplate, siteEngineeringFilesVersion):
    """
    This function kicks off the csl installation on the system under test, with the iso relating to the drop given
    """

    hostName = socket.gethostbyaddr(socket.gethostname())[0]

    # Define where to download files to temporarily if on a vApp
    try:
        cloudDownLoadDir = config.get('DMT_AUTODEPLOY', 'cloudDownLoadDir')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the cloudDownloadDir variable from the DMT_AUTODEPLOY config " + str(e))

    # Define where to store the site engineering files on the ms, and the full path to the actual site engineering file to use
    try:
        targetCfgDir = config.get('DMT_AUTODEPLOY', 'cslSiteEngineeringFilesDirectory')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the cslSiteEngineeringFilesDirectory variable from the DMT_AUTODEPLOY config " + str(e))

    cfgLoc = targetCfgDir + "/" + cfgTemplate

    if "::" in drop:
        ( drop, isoVersion, notRequired ) = setDropIsoVersion(drop)
    else:
        isoVersion = "LATEST"

    if not os.path.exists(cloudDownLoadDir):
        # Randomly generated directory with /tmp
        tmpArea = tempfile.mkdtemp()
    else:
        # For cloud there is a specific area to use /export/data
        random = randint(2,9000)
        os.makedirs(cloudDownLoadDir + "/temp" + str(random))
        tmpArea = cloudDownLoadDir + "/temp" + str(random)

    packagesDir = os.path.join(tmpArea, "packages")
    os.makedirs(packagesDir)

    # Get details of the ms from the database, based on the clusterId
    try:
        cluster = Cluster.objects.get(id = clusterId)
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the deployment details for deployment id " + clusterId + ": " + str(e))
    mgtServer = cluster.management_server
    ( isoName, isoVersion, isoUrl, hubIsoUrl, message ) = getIsoName(drop,isoVersion,product)

    # Define where to upload files to on the ms
    try:
        lmsUploadDir = config.get('DMT_AUTODEPLOY', 'lmsUploadDir')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the lmsUploadDir variable from the DMT_AUTODEPLOY config " + str(e))

    # Check if we can make a connection to the ms
    fqdnMgtServer = mgtServer.server.hostname + "." + mgtServer.server.domain_name
    user=config.get('DMT_AUTODEPLOY', 'user')
    masterUserPassword = config.get('DMT_AUTODEPLOY', 'masterPasswordCloudMS1CSL')
    keyFileName=config.get('DMT_AUTODEPLOY', 'key')
    remoteConnection = None
    (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
    if (ret != 0):
        dmt.utils.dmtError("Could not create ssh connection to MS", clusterId, tmpArea, remoteConnection)

    logger.info("Deploying " + str(cluster) + " from management server " + str(mgtServer))
    ret = downloadIsoToMgtServer(remoteConnection, mgtServer, isoName, lmsUploadDir,tmpArea,isoUrl)
    if (ret != 0):
        dmt.utils.dmtError("Could not download the iso to the management server", clusterId, tmpArea, remoteConnection)

    ret = mountIsoToMgtServer(remoteConnection,mgtServer,isoName,lmsUploadDir)
    if (ret != 0):
        dmt.utils.dmtError("Could not mount iso onto the management server", clusterId, tmpArea, remoteConnection)

    try:
        localCslIsoContentsDir = config.get('DMT_AUTODEPLOY', 'localCslIsoContentsDir')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the localCslIsoContentsDir variable from the DMT_AUTODEPLOY config " + str(e))

    localCslIsoContentsSubDir = localCslIsoContentsDir + os.path.basename(isoName)
    localCslIsoContentsPackageDir = localCslIsoContentsSubDir + "/products/CSL-Mediation/"

    ret = removeLocalCslIsoContentsDir(remoteConnection, localCslIsoContentsDir)
    if (ret != 0):
        dmt.utils.dmtError("Count not remove the local csl iso contents directory " + localCslIsoContentsDir, clusterId, tmpArea, remoteConnection)

    ret = populateLocalCslIsoContentsDir(remoteConnection, localCslIsoContentsSubDir)
    if (ret != 0):
        dmt.utils.dmtError("Could not copy files to the local csl iso contents directory from the mounted iso", clusterId, tmpArea, remoteConnection)

    if (packageList != None):
        logger.info("Downloading Extra Packages")
        packageListDict = buildPackageDict(packageList)
        downloadPackageList,downloadPackageCategoryList = downloadExtraPackages(clusterId, packageListDict, packagesDir, product)
        if (downloadPackageList == 1):
            dmt.utils.dmtError("Unable to download extra Packages", clusterId, tmpArea, remoteConnection)

        ret = removeExtraPackage(packageListDict,remoteConnection,mgtServer, localCslIsoContentsPackageDir)
        if (ret != 0):
            dmt.utils.dmtError("Could not remove the extra packages from the ms", clusterId, tmpArea, remoteConnection)

        ret = uploadExtraPackages(downloadPackageList, mgtServer, packagesDir, localCslIsoContentsPackageDir)
        if (ret != 0):
            dmt.utils.dmtError("Could not upload the extra packages to the ms", clusterId, tmpArea, remoteConnection)

    ret = installCslMedInstRpm(remoteConnection)
    if (ret != 0):
        dmt.utils.dmtError("Could not yum install the ERICcslmedinst rpm onto the management server", clusterId, tmpArea, remoteConnection)

    ret = cslConfigsToMgtServer(remoteConnection, mgtServer, lmsUploadDir,tmpArea,targetCfgDir, siteEngineeringFilesVersion)
    if (ret != 0):
        dmt.utils.dmtError("Could not download the csl configs onto the management server", clusterId, tmpArea, remoteConnection)

    deployReturn = execDeployCsl(remoteConnection, localCslIsoContentsSubDir, cfgLoc)
    if (deployReturn != 0):
        dmt.utils.dmtError("Could not deploy ", clusterId, tmpArea, remoteConnection)

    logger.info("CLUSTER DEPLOYED SUCCESSFULLY")
    return 0

def cloudPostInstallCommands(remoteConnection,cluster,lmsUploadDir,user,litpUsername,masterUserPassword,cfgLoc,tmpArea, mgtServer):
    '''
    Function used to call the cloud post install commands
    '''
    (ret,nodeSrv) = getListOfNodesInDeployment(cluster)
    if ret != 0:
        logger.info("Could not get the node data from the deployment")
        return ret
    ret = reSetPeerNodePassword(remoteConnection, mgtServer)
    if ret != 0:
        logger.info("Error Resetting the Peer Nodes login details")
        return ret
    logger.info("Checking if Vmware Tools is required to be installed based on RHEL version...")
    installTools = True
    # Check redhat release version
    ret, output = runCommandGetOutput(remoteConnection, " cat /etc/redhat-release")
    logger.info(str(output))
    if ret != 0:
        logger.info("Failed to get RHEL version, installing VMware Tools by default...")
    else:
        if "release" in output:
            output = str(output).split("release")[1]
            logger.info(str(output))
        if " 6." not in output:
            installTools = False
            logger.info("VMware Tools will not to be installed, open-vm-tools are already installed with this RHEL OS version.")
    if installTools:
        ret = installVmWareTools(remoteConnection,lmsUploadDir,nodeSrv,user,litpUsername)
        if ret != 0:
            logger.info("Error installing VMware on the Peer Nodes")
            return ret
    ret = versantDatabaseUsageThresholds(remoteConnection)
    if ret != 0:
        logger.error("Unable to adjust the VersantDB usage thresholds")
        return ret
    return 0

def applyCPUSettings(remoteConnection):
    '''
    Function used to apply cpu settings for RHEL6 only as the one for RHEL7 is already done by EDP.
    '''
    try:
        return_code = 0
        litpUsername = config.get('DMT_AUTODEPLOY', 'litpUsername')
        nodePassword = config.get('DMT_AUTODEPLOY', 'peerNodePassword')
        deployLibPath = config.get('DMT_AUTODEPLOY', 'deployLibPath')
        scriptName = config.get('DMT_AUTODEPLOY', 'applyCPUSettingsScript')
        scriptFullPath = deployLibPath + "/" + scriptName
        scriptExecCmd = "python " + scriptFullPath + " --user=" + litpUsername + " --password=" + nodePassword
        findFileCmd = "find " + deployLibPath + " | grep '" + str(scriptName) + "'"
        (ret, output) = remoteConnection.runCmdGetOutput(findFileCmd)
        if int(ret) == 0:
            return_code = runCommand(remoteConnection, scriptExecCmd)
            if(return_code != 0):
                logger.error("Error in Execution of: " + str(scriptExecCmd))
                return return_code
    except Exception as e:
        logger.error("Unexpected error in execution of applying CPU settings" + str(e))
        return 1
    return return_code

def physicalPostInstallCommands(remoteConnection,cluster,lmsUploadDir,user,litpUsername,masterUserPassword,cfgLoc,tmpArea, mgtServer):
    '''
    Function used to call the physical post install commands
    '''
    ret = reSetPeerNodePassword(remoteConnection,mgtServer)
    if ret != 0:
        logger.info("Error Resetting the Peer Nodes login details")
        return ret
    ret = versantDatabaseUsageThresholds(remoteConnection)
    if ret != 0:
        logger.error("Unable to adjust the Versant database usage thresholds")
        return ret
    ret, output = runCommandGetOutput(remoteConnection, " cat " + config.get('DMT_AUTODEPLOY', 'rhelVersionFile'))
    if ret != 0:
        logger.error("Failed to get RHEL version before applying CPU settings.")
        return ret
    if " 6." in output:
        ret = applyCPUSettings(remoteConnection)
        if ret != 0:
            logger.error("Unable to apply CPU Settings")
    return 0

def checkStep(step):
    if ( step != None ):
        raw_input("Press Enter to continue...")

def execStageOnePreInstall(remoteConnection, lmsUploadDir, fullXML, modelOut):
    '''
    Function used to call the pre install steps required for stage one infra only
    '''
    try:
        enmInstBin = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the ENMinst bin directory from DMT_AUTODEPLOY config " + str(e))

    # Healthcheck - from ENMinst rpm package
    logger.info("Run the litp_healthcheck to validate the state of the server before installation")
    ret = execBaseHealthcheck(remoteConnection, enmInstBin)
    if (ret != 0):
        logger.error("Could not complete litp_healthcheck: return code " + str(ret))
        return ret

    # XML splitter
    logger.info("Splitting the XML, " + str(fullXML) + " out to " + str(modelOut) + " removing the services")
    ret = execXMLSplitter(remoteConnection,lmsUploadDir,fullXML,modelOut)
    if (ret != 0):
        logger.error("Could not complete extraction of infra rpms: return code " + str(ret))
        return ret
    return 0

def execStageOnePostInstall(remoteConnection,lmsUploadDir,snapShotName,environment,mgtServerObj,snapOption):
    '''
    Function used to call the post stage 1 test case for the infra installation
    '''
    try:
        enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the ENMinst bin directory from DMT_AUTODEPLOY config " + str(e))

    # Infra health checks
    ret = execInfraHealthcheck(remoteConnection,enmInstDir)
    if (ret != 0):
        logger.error("Could not complete infrastructure_healthcheck: return code " + str(ret))
        return ret

    if "physical" in environment:
        ret = snap(remoteConnection,snapShotName,snapOption,mgtServerObj,lmsUploadDir)
        if (ret != 0):
            logger.error("Could not complete snapshot creation: return code " + str(ret))
            return ret
    return 0

def execStageTwo(remoteConnection, lmsUploadDir, isoName, xmlFile, SED):
    '''
    Function used to deployment the App on the server only
    '''
    try:
        enmInstBin = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the ENMinst bin directory from DMT_AUTODEPLOY config " + str(e))
    try:
        enmInstLib = config.get('DMT_AUTODEPLOY', 'enmInstLib')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the ENMinst lib directory from DMT_AUTODEPLOY config " + str(e))
    try:
        deploymentKvmXml = config.get('DMT_AUTODEPLOY', 'deploymentKvmXml')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the ENMinst KVM Deployment XML from DMT_AUTODEPLOY config " + str(e))
    try:
        tmpPasswordEncryptFile = config.get('DMT_AUTODEPLOY', 'tmpPasswordEncryptFile')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the temporary file for the encrypted passwords from DMT_AUTODEPLOY config " + str(e))

    # Healthcheck - Base
    ret = execBaseHealthcheck(remoteConnection,enmInstBin)
    if (ret != 0):
        logger.error("Could not complete litp_healthcheck: return code " + str(ret))
        return ret

    # Healthcheck - Infrastructure
    ret = execInfraHealthcheck(remoteConnection,enmInstBin)
    if (ret != 0):
        logger.error("Could not complete infrastructure_healthcheck: return code " + str(ret))
        return ret

    # Deploy ENM Apps from deployment scripts
    ret = deployStageTwo(remoteConnection,lmsUploadDir,isoName,enmInstLib)
    if (ret != 0):
        logger.error("Could not complete application deployment (Stage Two) of System: return code " + str(ret))
        return ret

    # Encrypt the password with the SED to pass to the substitue Paramater script
    ret = encryptPasswords(remoteConnection,enmInstBin,SED,tmpPasswordEncryptFile)
    if (ret != 0):
        logger.error("Could not complete encrytion of the passwords within the SED: return code " + str(ret))
        return ret

    # Get the UUID to pass to the substitue Paramater script
    ret = getUuid(remoteConnection,enmInstBin)
    if (ret != 0):
        logger.error("Could not get the UUID for the XML substitution: return code " + str(ret))
        return ret

    # Substitute Parameters
    ret = subParams(remoteConnection,enmInstBin,xmlFile,SED,tmpPasswordEncryptFile)
    if (ret != 0):
        logger.error("Could not complete substitution of parameters: return code " + str(ret))
        return ret

    # Deploy KVMs
    ret = deployKvms(remoteConnection,enmInstBin,deploymentKvmXml,SED)
    if (ret != 0):
        logger.error("Could not complete deployment of KVMs: return code " + str(ret))
        return ret
    return ret

def execBaseHealthcheck(remoteConnection,enmInstBin):
    # Healthcheck - from ENMinst rpm package
    cmd = enmInstBin + "litp_healthcheck.sh"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def execXMLSplitter(remoteConnection,lmsUploadDir,xml,model):
    # XML Splitter to remove services and leave only infra items in the deployment xml file - From the deployment tar file
    cmd = lmsUploadDir + "/deploy/bin/enm_xml_splitter.bsh --input " + xml + " --output " + model + " --remove_services"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def deployStageOne(remoteConnection,enmInstDir,installType,SED,model,lmsUploadDir,isoName):
    # Deploy system - from ENMinst rpm package
    cmd = enmInstDir + "deploy_enm.sh -t " + installType + " -s " + SED + " -m " + model + " -e " + lmsUploadDir + "/" + isoName + " -v"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def execInfraHealthcheck(remoteConnection,enmInstDir):
    # Infrastructure Healthcheck - from ENMinst rpm package
    #cmd = enmInstDir + "infrastructure_healthcheck.sh"
    cmd = "echo 'The infrastructure_healthcheck.sh should be ran here once available'"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd, "tty-ssh")
    return int(ret)

def executeValidateSnapshot(remoteConnection):
    '''
    Function to execute the snapshot validation on the system
    '''
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    # Validate the snapshot
    cmd = enmInstDir + "enm_snapshots.bsh --action validate_snapshot"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd, "tty-ssh")
    if ret != 0:
        return int(ret)
    return 0

def executeSshConnectionCheckOnMs(remoteConnection,mgtServerObj,initial_wait=None,interval=None,retries=None):
    '''
    Function to check the ssh connection on the MS
    '''
    if initial_wait == None:
        initial_wait=90
    if interval == None:
        interval=10
    if retries == None:
        retries=60
    fqdnMgtServer = mgtServerObj.server.hostname + "." + mgtServerObj.server.domain_name
    ret = dmt.createSshConnection.checkSSHConnection(fqdnMgtServer,initial_wait,interval,retries)
    if ret != 0:
        return int(ret)
    return 0

def executeRestoreSnapshot(remoteConnection,snapShotName,option,mgtServerObj):
    '''
    Function to execute the restore of a snapshot on the system
    '''
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    fqdnMgtServer = mgtServerObj.server.hostname + "." + mgtServerObj.server.domain_name
    # Restore the snapshot
    if snapShotName:
        cmd = enmInstDir + "enm_snapshots.bsh --action " + option + " --snap-prefix " + snapShotName
    else:
        cmd = enmInstDir + "enm_snapshots.bsh --action " + option
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd, "tty-ssh")
    if ret != 0:
        return int(ret)
    return 0

def checkServiceGroup(remoteConnection,lmsUploadDir):
    '''
    Function used to check all the services on the system to ensure they are up
    '''
    cmd = lmsUploadDir + "/deploy/bin/serviceCheck.bsh"
    ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
    if (ret != 0):
        return ret
    return ret

def placeCloudUuidUpdateScript(remoteConnection, lmsUploadDir):
    '''
    Function used to place the cloud uuid updater script in the /etc/init.d/ directory on the ms
    '''
    logger.info("Placing the cloud UUID Update Script in /etc/init.d/updatelitpuuid")
    cmd = "ls " + lmsUploadDir + "/deploy/bin/updatelitpuuid"
    ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
    if (ret != 0):
        logger.info("Couldn't find the uuid update script in the deploy scripts, not going to copy it")
        return 0

    cmd = "/bin/cp " + lmsUploadDir + "/deploy/bin/updatelitpuuid /etc/init.d/updatelitpuuid"
    ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
    if (ret != 0):
        return ret

    cmd = "chmod +x /etc/init.d/updatelitpuuid"
    ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
    if (ret != 0):
        return ret

    cmd = "chkconfig --add updatelitpuuid"
    ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
    if (ret != 0):
        return ret

    cmd = "chkconfig --level 2345 updatelitpuuid on"
    ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
    return ret

def executeLoopServiceCheck(remoteConnection,cmd,initial_wait=None,interval=None,retries=None):
    '''
    Function used to loop through the service a number of times specified until either all service are onlinei/faulted state or timeout
    '''
    # Set default values
    if initial_wait == None:
        initial_wait=1
    if interval == None:
        interval=30
    if retries == None:
        retries=20
    logger.info("Starting the check to see if all services are online, in " + str(initial_wait) + "  seconds")
    time.sleep(initial_wait)
    count = 1
    for x in range(retries):
        logger.info("Try " + str(count) + " of " + str(retries))
        count += 1
        ret = remoteConnection.runCmdSimple(cmd,"tty-ssh")
        if (ret != 0):
            logger.info("All Services are not online.. Waiting...")
            time.sleep(interval)
            continue
        return 0
    return 1

def executeLoopServiceGroupCheck(remoteConnection,lmsUploadDir,initial_wait=None,interval=None,retries=None):
    '''
    Function used to loop through the service a number of times specified until either all service are onlinei/faulted state or timeout
    '''
    # Set default values
    if initial_wait == None:
        initial_wait=1
    if interval == None:
        interval=30
    if retries == None:
        retries=120
    logger.info("Starting the check to see if all service groups are online, in " + str(initial_wait) + "  seconds")
    time.sleep(initial_wait)
    count = 1
    for x in range(retries):
        logger.info("Try " + str(count) + " of " + str(retries))
        count += 1
        ret = checkServiceGroup(remoteConnection,lmsUploadDir)
        if (ret != 0):
            if (ret == 31):
                logger.info("All Services Groups are not in an OK state.. Waiting...")
                time.sleep(interval)
                continue
            else:
                break
        return 0
    return 1

def snap(remoteConnection,snapShotName,option,mgtServerObj,lmsUploadDir):
    '''
    Function to create/delete/restore a snapshot on the system
    '''
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    enmInstSnapBugVersion = config.get('DMT_AUTODEPLOY', 'enmInstSnapBugVersion')
    if option == "restore_snapshot":
        ret = executeValidateSnapshot(remoteConnection)
        if ret != 0:
            return int(ret)
        ret = executeRestoreSnapshot(remoteConnection,snapShotName,option,mgtServerObj)
        if ret != 0:
            return int(ret)
        ret = executeSshConnectionCheckOnMs(remoteConnection,mgtServerObj)
        if ret != 0:
            return int(ret)
        enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
        enmHealthCheckSystemServices = config.get('DMT_AUTODEPLOY', 'enmHealthCheckSystemServices')
        cmd = str(enmInstDir) + str(enmHealthCheckSystemServices)
        ret = executeLoopServiceCheck(remoteConnection,cmd)
        if ret != 0:
            return int(ret)
        ret = executeLoopServiceGroupCheck(remoteConnection,lmsUploadDir)
        if ret != 0:
            return int(ret)
        ret = snap(remoteConnection,snapShotName,"remove_snapshot",mgtServerObj,lmsUploadDir)
        if ret != 0:
            return int(ret)
    else:
        if snapShotName:
            cmd = enmInstDir + "enm_snapshots.bsh --action " + option + " --snap-prefix " + snapShotName
        else:
            cmd = "rpm -qa | grep ERICenminst_CXP9030877"
            (return_code, return_output) = runCommandGetOutput(remoteConnection, cmd, "tty")
            enm_inst_deployment_version = return_output.split("-")[1]
            if LooseVersion(enmInstSnapBugVersion) <= LooseVersion(enm_inst_deployment_version):
                if option == "create_snapshot":
                    cmd = enmInstDir + "enm_snapshots.bsh --action " + option
                else:
                    cmd = enmInstDir + "enm_snapshots.bsh --action " + option + " --snap_type=all"
            else:
                cmd = enmInstDir + "enm_snapshots.bsh --action " + option
        logger.info("Running " + cmd)
        ret = runCommand(remoteConnection, cmd, "tty-ssh")
        if ret != 0:
            return int(ret)
    return 0

def deployed_system_artifact_check(remoteConnection):
    # Check deployed system for deployed artifacts and version, usefull for logging
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    cmd = enmInstDir + "enm_version.sh"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def vcs_check(remoteConnection, parameter):
    # VCS check to ensure that all servoces required for are active, healt check
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    cmd = enmInstDir + "vcs.bsh --" + str(parameter)
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd, "tty-ssh")
    return int(ret)

def sync_puppet_check(remoteConnection, parameter, timeout=None):
    #After Package install of required pre install/upgrade packages puppet needs to be re synced on ms
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    cmd = enmInstDir + "puppet.bsh --" + str(parameter)
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd, "tty-ssh", timeout)
    return int(ret)

def deployStageTwo(remoteConnection,lmsUploadDir,isoName,enmInstLib):
    # Deploy system applications - from ENMinst rpm package
    cmd = "/usr/bin/python " + enmInstLib + "/import_iso.py --iso " + lmsUploadDir + "/" + isoName + " --v"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd, "tty-ssh")
    return int(ret)


def encryptPasswords(remoteConnection,enmInstBin,SED,tmpPasswordEncryptFile):
    # Encrypt the password with the SED to pass to the substitue Paramater script
    cmd = "/usr/bin/python " + enmInstBin + "../lib/encrypt_passwords.py -v --sed " + SED + " --passwords_store " + tmpPasswordEncryptFile
    cmdRm = "rm " + tmpPasswordEncryptFile
    logger.info("Ensuring no old encryption file exists (" + tmpPasswordEncryptFile + ")")
    ret = runCommand(remoteConnection, cmdRm)
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def getUuid(remoteConnection,enmInstBin):
    # Function to run the uuid script from ENMinst to get the uui to populate the SED
    cmd = "/usr/bin/python " + enmInstBin + "../lib/ms_uuid.py"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def subParams(remoteConnection,enmInstBin,xmlFile,SED,tmpPasswordEncryptFile):
    # Substitute parameters in the deployment xml - from ENMinst rpm package
    cmd = enmInstBin + "substituteParams.sh --xml_template=" + xmlFile + " --sed=" + SED + " --propertyfile=" + tmpPasswordEncryptFile
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def deployKvms(remoteConnection,enmInstBin,model,SED):
    # Deploy the kvms - from ENMinst rpm package
    cmd = enmInstBin + "load_run_plan.sh --model_xml " + model + " --sed " + SED + " --v"
    logger.info("Running " + cmd)
    ret = runCommand(remoteConnection, cmd)
    return int(ret)

def reSetPeerNodePassword(remoteConnection, mgtServer):
    '''
    Function used to reset the password of peer nodes after the installation
    '''
    ret = 0
    litpPwd = config.get('DMT_AUTODEPLOY', 'peerNodePassword')
    rootPwd = config.get('DMT_AUTODEPLOY', 'peerNodePassword')
    # Execute password update script
    logger.info("Updating the initial passwords for users litp-admin and root")
    outcome, ret = execUpdatePasswordScript(remoteConnection, mgtServer, litpPwd, rootPwd)
    if(ret != 0):
        logger.error("Error with the resetting of the password for the litp-admin and root user")
    return int(ret)


def getTimeInEpoch(remoteConnection,command,searchString):
    '''
    Function used to calculate the time and return epoch value (number of seconds since 1970/1/1)
    '''
    try:
        (ret,commandOutput) = runCommandGetOutput(remoteConnection,command,"tty")
        if (ret != 0):
            return (1, "ERROR")
        returnedOutput = commandOutput[commandOutput.index(searchString):].split('\n', 1)[0].replace('\r',"").replace(searchString,"").lstrip()
        epochServerStartTime = calendar.timegm(time.strptime(str(returnedOutput), '%a %b %d %H:%M:%S %Y'))
        return (0, epochServerStartTime)
    except Exception as error:
        return (1, "ERROR")

def calculateUpTime(currentTimeInEpoch,installTimeInEpoch):
    '''
    Given 2 Epoch values calculate how long it is running
    '''
    try:
        uptimeSeconds = currentTimeInEpoch - installTimeInEpoch
        seconds = uptimeSeconds
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24
        logger.info("Server Up Time:: %02d Days %02d Hours %02d Minutes %02d Seconds" % (days, hours % 24, minutes % 60, seconds % 60))
        return (0, uptimeSeconds)
    except Exception as error:
        return (1, "ERROR")

def checkServerUpTime(remoteConnection,maxUpTime):
    '''
    Function used to check the MS to ensure it has initial installed within the maxUpTime value passed in
    '''
    try:
        command = "awk {'print\$1'} /proc/uptime"
        (ret,uptimeSeconds) = runCommandGetOutput(remoteConnection,command,"tty")
        if (ret != 0):
            return 1
        if int(float(uptimeSeconds.rstrip())) > int(maxUpTime):
            maxUpTimeMinutes = int(maxUpTime) // 60
            logger.error("The OS initial install seems to have failed on the MS as the filesystem is older than expected, i.e. " + str(maxUpTimeMinutes) + " Minutes")
            return 1
        return 0
    except Exception as error:
        logger.error(str(error))
        return 1

def installVmWareTools(remoteConnection,lmsUploadDir,nodeSrv,rootUser,litpUser):
    '''
    Function used to install the VM Tools onto a given Node
    '''
    ret = 0
    servers = config.get('DMT_AUTODEPLOY', 'servers')
    serverList = servers.split()
    for server in nodeSrv:
        if isinstance(server, ClusterServer):
            (ret, nodeTypeCheck) = dmt.utils.getNodeType(server.node_type)
            if(ret != 0):
                logger.error(nodeTypeCheck)
                return int(ret)
            if ( nodeTypeCheck in serverList ):
                user = litpUser
                hostname = server.server.hostname
                cmd = lmsUploadDir + "/deploy/etc/vmwaretools/install/password_wrapper.sh " + user + " " + hostname
            else:
                continue
        elif isinstance(server, ManagementServer):
            user = rootUser
            cmd = lmsUploadDir + "/deploy/etc/vmwaretools/install/inst_vmtools.bsh"
            hostname = server.server.hostname
        else:
            continue
        # Can we ping the server
        ret = subprocess.call("ping -c1 " + hostname + " > /dev/null", shell=True)
        if (ret == 0):
            logger.info("Installing VMWare on node " + str(hostname))
            logger.info("Running " + cmd)
            ret = runCommand(remoteConnection, cmd)
            if(ret != 0):
                logger.error("Error with the install on vmware tools on node " + str(hostname))
                return int(ret)
        else:
            logger.info("Node is not pingable " + str(hostname))
            ret = 0
    return int(ret)

def versantDatabaseUsageThresholds(remoteConnection):
    '''
    Function used to adjust the Versant database usage thresholds
    '''
    cmdCmServNode = "grep -e -cmserv /etc/hosts | head -1"
    ret,output = remoteConnection.runCmdGetOutput(cmdCmServNode)
    if ( ret == 0 and "cmserv" in output ):
        for line in output.split('\n'):
            if "-cmserv" in line:
                cmServNode = line.split('\t')[1]
            else:
                continue
    else:
        logger.error("There is an issue getting the cmserv hostVm from /etc/hosts file")
        return int(ret)
    cmdCheck = "/ericsson/pib-scripts/etc/config.py read --name=databaseSpaceCriticalThreshold --app_server_address=" + str(cmServNode) +":8080 --scope=GLOBAL"
    cmdExecute = "/ericsson/pib-scripts/etc/config.py update --app_server_address=" +str(cmServNode) + ":8080 --name=databaseSpaceCriticalThreshold --value=1000 --scope=GLOBAL"
    comment = "Did not find configuration parameter"

    logger.info("Executing Workaround on cloud systems to allow Versant database usage thresholds to be altered")
    logger.info("Checking the App Server address to ensure it is accessable, \"" +str(cmServNode) + ":8080\"")
    ret,output = remoteConnection.runCmdGetOutput(cmdCheck)
    if ( ret == 0 and comment not in output ):
        logger.info("Executing Versant Threshold re-configuration")
        ret = runCommand(remoteConnection, cmdExecute)
        if(ret != 0):
            logger.error("Error Executing: " + str(cmdExecute))
            return int(ret)
    else:
        logger.info("Skipping Versant Database Threshold configuration, see command output below")
        logger.info(output)
    return 0

def showDirectoryStorage(remoteConnection, dirName):
    cmdList = ['du -sh ', 'df -hT ']
    for command in cmdList:
        runCommand(remoteConnection, command + str(dirName))

def removeRedundantMount(remoteConnection, mountInfo, mediaArtifactList):
    products = ast.literal_eval(config.get('DMT_AUTODEPLOY', 'mediaDirProductList'))
    for media in mediaArtifactList:
        if 'autoDeploy' in media:
            continue
        mediaShort = media.split('-')[0]
        if mediaShort in mountInfo:
            logger.info('Media ' + str(media) + ' already mounted, removing device')
            umountMedia(remoteConnection, products)
            (ret, mountInfo) = runCommandGetOutput(remoteConnection, 'losetup -a')
            if 'loop0' in mountInfo:
                ret = runCommand(remoteConnection, 'losetup -d /dev/loop0')

def umountMedia(remoteConnection, products):
    for product in products:
        runCommand(remoteConnection, 'umount /media/'+str(product))

def cleanSoftwareDirectory(remoteConnection, lmsUploadDir, lastIsoImportedFile, mediaArtifactList):
    '''
    This function cleans old ENM ISOs from the /software/autoDeploy directory of the ms.
    '''
    products = ast.literal_eval(config.get('DMT_AUTODEPLOY', 'mediaDirProductList'))
    # Show software directory storage using both df and du commands
    logger.info('Software directory storage info before clean up')
    showDirectoryStorage(remoteConnection, '/software')

    # Let's umount both ENM and litp media mount before clean up of old iso
    logger.info('Unmount media mounts if any for both ENM and LITP before clean up')
    umountMedia(remoteConnection, products)

    # Remove old iso form the software directory
    logger.info('Clean up old mediaArtifacts')
    for media in mediaArtifactList:
        if 'autoDeploy' in media:
            continue
        mediaShort = re.split('-(\d+\.*)', media)[0]
        cmd = "find " + lmsUploadDir + " -name '" + mediaShort + "*' ! -name '" + media + "' -delete"
        ret = runCommand(remoteConnection, cmd)
        if(ret != 0):
            message = "Unable to clean up the media " + str(media) + " from within " + str(lmsUploadDir)
            logger.info(message)

    # Show software directory storage using both df and du commands
    logger.info('Software directory storage info post clean up')
    showDirectoryStorage(remoteConnection, '/software')

    # Run set of commands to check if any of the iso removed from above steps left mounted
    logger.info('Check if any dead mount present')
    cmdList = ['losetup -a','ls -l /software/autoDeploy/']
    for command in cmdList:
        if 'losetup -a' in command:
            (ret, mountInfo) = runCommandGetOutput(remoteConnection,command)
        ret = runCommand(remoteConnection, command)

    if '/dev/loop' in mountInfo:
        logger.info('loop device mount exist!')
        removeRedundantMount(remoteConnection, mountInfo, mediaArtifactList)
    else:
        logger.info('No loop device left mounted after clean-up')

    logger.info('Software directory storage info before giving control back to main program')
    showDirectoryStorage(remoteConnection, '/software')
    return (0,"SUCCESS")

def getListOfNodesInDeployment(cluster):
    '''
    Function used to get the list of nodes in the deployment
    '''
    cluster = Cluster.objects.get(id=cluster.id)
    mgtServer = cluster.management_server
    clusterSvrs = ClusterServer.objects.filter(cluster=cluster)
    # Append all Server objects together
    nodesrv = []
    for x in clusterSvrs:
        nodesrv.append(x)
    nodesrv.append(mgtServer)
    return (0,nodesrv)

def powerCyclePeerNodes(remoteConnection,lmsUploadDir,action,sed,tmpArea,lmsUsername,lmsCloudPassword):
    '''
    Function used to stop/start the peer nodes
    '''
    logger.info("Ensuring the required python modules are installed on the Gateway server to stop the peer nodes")
    cmd = "sudo " + tmpArea + "/bin/install_py_modules.bsh"
    logger.info("Running " + cmd)
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        logger.info("Running " + cmd + " due to issue")
        ret = subprocess.call(cmd, shell=True)
        if ret != 0:
            return int(ret)
    logger.info("Stopping the Peer Nodes.. This can take sometime please wait....")
    sedFile = sed.split("/")[-1]
    enmInstDir = config.get('DMT_AUTODEPLOY', 'enmInstBin')
    cmd = "sudo " + enmInstDir + "enm_snapshots.bsh  --action " + action + " --snap-prefix ClOULDSNAP"
    logger.info("Running " + cmd)
    ret = subprocess.call(cmd, shell=True)
    return int(ret)

def updateDeploymentStatus(clusterId, state=None, osDetails=None, rhel6PatchDetails=None, rhel7PatchDetails=None, rhel79PatchDetails=None, rhel88PatchDetails=None, litpDetails=None, artifactDetails=None, pkgsDetails=None, descriptionDetails=None):
    '''
    Used to set relevant information regarding the Deployment
    Only run on Physical deployments
    '''
    logger.info("Start Update Deployment Status Procedure.")
    if "cloud" not in env:
        cifwkUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
        clusterIdData = "clusterId="+str(clusterId)
        statusData = "status="+str(state)
        osData = "os="+str(osDetails)
        patchesDatas = []
        patchesData = 'patches="'
        if rhel6PatchDetails:
            patchesDatas.append('RHEL 6 OS Patch Version: ' + str(rhel6PatchDetails))
        if rhel7PatchDetails:
            patchesDatas.append('RHEL 7 OS Patch Version: ' + str(rhel7PatchDetails))
        if rhel79PatchDetails:
            patchesDatas.append('RHEL 79 OS Patch Version: ' + str(rhel79PatchDetails))
        if rhel88PatchDetails:
            patchesDatas.append('RHEL 88 OS Patch Version: ' + str(rhel88PatchDetails))
        patchesData += ", ".join(patchesDatas)
        patchesData += '"'
        litpData = "litp="+str(litpDetails)
        artifactData = "artifact="+str(artifactDetails)
        pkgsData = "packages="+str(pkgsDetails)
        descData = "description="+str(descriptionDetails)

        url = "curl --request POST --insecure -s "  +cifwkUrl + "/deploymentStatus/ " + " --data '" + clusterIdData + "' --data '" + statusData + "' --data '" + osData + "' --data '" + patchesData + "' --data '" + litpData + "' --data '" + artifactData + "' --data '" + pkgsData + "' --data '" + str(descData) + "'"
        logger.info("Started running Restful POST Endpoint to update deployment Status in DMT. " +str(url))
        ret, status = commands.getstatusoutput(str(url))
        logger.info("Ended running Restful POST Endpoint to update deployment Status in DMT. " +str(url))
        if (ret != 0 or "Stack trace" in status ):
            logger.error("Issue running the command to update the deployment status information. Please investigate")

    logger.info("End Update Deployment Status Procedure.")

def diagnosticDataPresentation(remoteConnection, clusterId):
    '''
    Configuring DDP (Diagnostic Data Presentation) for Physical Environment
    '''
    ignoreInstallGroups = str(config.get('DMT_AUTODEPLOY', 'ignoreInstallGroupForDDP')).split(",")
    for installGroupName in ignoreInstallGroups:
        if ClusterToInstallGroupMapping.objects.filter(group__installGroup=installGroupName, cluster__id=clusterId).exists():
            return

    errMsg = "Error Configuring DDP (Diagnostic Data Presentation) to active"
    try:
        checkCronTab = str("sudo crontab -l")
        # Check if cron job already exist:
        ret, output = remoteConnection.runCmdGetOutput(str(checkCronTab), "tty-ssh")
        logger.info("Checked if a DDP cron job already exists, output: " + str(output))
        if "-d ddp" in str(output):
            logger.info("DDP cron job already exists, skipping adding one.")
            return
        elif not "no crontab" in str(output) and ret != 0:
            logger.error(str(errMsg) + " - Cmd(" + str(checkCronTab) + ") - " + str(output))
            return

        logger.info("Setting up the DDP cron job:")

        # Setting up parameters
        crontabTmpFile = config.get('DMT_AUTODEPLOY', 'crontabTmpFile')
        crontabDDP = config.get('DMT_AUTODEPLOY', 'crontabDDP')
        ddpFile = config.get('DMT_AUTODEPLOY', 'ddpFile')
        ddcDataUploadPath = config.get('DMT_AUTODEPLOY', 'ddcDataUploadPath')
        checkDDCdataUpload = str("[ ! -d " + ddcDataUploadPath + "] && exit 1 || exit 0")
        copyCrontab = str("sudo crontab -l > " + crontabTmpFile)
        removeLineFromTmp = str("sed -i '/ddcDataUpload/d' " + crontabTmpFile)
        addToCrontab = str("sudo crontab < " + crontabTmpFile)
        removeTmp  = str("sudo rm " + crontabTmpFile)
        checkDPPfile = str("[ ! -f " + ddpFile + "  ] && exit 1 || exit 0")
        clearDPPfile = str("sudo cat /dev/null > " + ddpFile)
        addToddpFile = str("sudo echo 'lmi_ENM" + str(clusterId) + "'  >> " + ddpFile)
        createCrontabTmpFile = str("sudo touch " + crontabTmpFile)

        # Check DB for Cluster Additional Information
        if ClusterAdditionalInformation.objects.filter(cluster__id=clusterId).exists():
            logger.info("Other Properties (DDP) information exists for this Deployment, fetching from DB...")
            clusterAdditionalInformation  = dmt.utils.getClusterAdditionalProps(clusterId)
            logger.info('Deployment Other Properties (DDP) information object is ' + str(clusterAdditionalInformation))
            if all(x in clusterAdditionalInformation.keys() for x in  ['ddp_hostname', 'cron', 'time']):
                ddpHostname = clusterAdditionalInformation['ddp_hostname']
                cron = clusterAdditionalInformation['cron']
                time = clusterAdditionalInformation['time']
                if ddpHostname != '' and cron != '':
                    nthMinute = str(time if time else 30)
                    crontabDDP = nthMinute + ' ' + cron + ' \* \* \* ' + ddcDataUploadPath + ' -d ' + ddpHostname + ' -s ENM'
                    logger.info('Custom cron command for the Deployment is: ' + str(crontabDDP))
                else:
                    logger.info('Unable to find DDP hosname or/and Cron command in the Deployment, using default i.e. ' + str(crontabDDP))
            elif "warning" in clusterAdditionalInformation.keys():
                logger.info(clusterAdditionalInformation['warning'] + ", using default crontab i.e." + str(crontabDDP))
            elif "error" in clusterAdditionalInformation.keys():
                logger.info(clusterAdditionalInformation['error'] + ", using default crontab i.e." + str(crontabDDP))

        addLineToTmp = str("sudo echo '"+ crontabDDP + str(clusterId) + "'  >> " + crontabTmpFile)

        # Running DDP cron setup commands
        commandList = [checkDDCdataUpload, copyCrontab, removeLineFromTmp, addLineToTmp, addToCrontab, removeTmp, checkDPPfile, clearDPPfile, addToddpFile]
        for command in commandList:
            ret, output = remoteConnection.runCmdGetOutput(str(command), "tty-ssh")
            if "no crontab" in str(output):
                logger.info("No crontab found: creating tmp file curcronfile.txt")
                ret, output = remoteConnection.runCmdGetOutput(str(createCrontabTmpFile), "tty-ssh")
            if ret != 0:
                logger.error(str(errMsg) + " - Cmd(" + str(command) + ") - " + str(output))
                return

        # Check cron job exist:
        ret, output = remoteConnection.runCmdGetOutput(str(checkCronTab), "tty-ssh")
        logger.info("Check for DDP cron job, output: " + str(output))
        logger.info("DDP (Diagnostic Data Presentation) was set to active")
    except Exception as e:
        logger.error(str(errMsg) + ": " + str(e))


def associatingVmServicesWithPackages(remoteConnection, clusterId, isoVersion):
    '''
    Associating Vm Services With Packages in DB
    '''
    try:
        installGroups = str(config.get('DMT_AUTODEPLOY', 'vmServicesInfoInstallGroup'))
        command = config.get('DMT_AUTODEPLOY', 'vmServicesInfo') + " " + config.get('DMT_AUTODEPLOY', 'vmServicesInfoFormatCmd')
        logger.info("Starting Associating VM Services with Packages for Install Group : MainTrack deployments")
        (ret,commandOutput) = runCommandGetOutput(remoteConnection,command,"tty")
        vmServices = str(commandOutput).split("VM___service___:___")

        if ClusterToInstallGroupMapping.objects.filter(group__installGroup=installGroups, cluster__id=clusterId).exists():
            for vmServiceData in vmServices:
                vmService, artifactsData = str(vmServiceData).split("___", 1)
                vmService = str(vmService).replace(" ", "")
                if not "Warning:" in str(vmService):
                   vmService, created = VmServiceName.objects.get_or_create(name=vmService)
                artifactsList = str(artifactsData).split(" ")
                for artifactItem in artifactsList:
                    artifactItemList = str(artifactItem).split("\r\n")
                    artifactItemList = filter(None, artifactItemList)
                    for artifactItemValue in artifactItemList:
                        if 'None' in artifactItemValue:
                            continue

                        artifactInfoList = str(artifactItemValue).split("___")[:2]
                        artifactId = artifactInfoList[0]
                        artifactVersion = artifactInfoList[1]
                        if not PackageRevisionServiceMapping.objects.filter(package_revision__artifactId=artifactId, package_revision__version=artifactVersion, service=vmService).exists():
                            try:
                                package_rev_id = PackageRevision.objects.get(package__name=artifactId, version=artifactVersion)
                                PackageRevisionServiceMapping.objects.create(package_revision=package_rev_id, service=vmService)
                            except Exception:
                                pass
            MediaArtifactServiceScanned.objects.create(media_artifact_version=isoVersion, scanned_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as error:
        logger.error("Error Associating Vm Services With Artifacts - " + str(error))
    logger.info("Ending Associating VM Services with Packages for Install Groups.")

def exitDeployment(clusterId, state=None, osDetails=None, rhel6PatchDetails=None, rhel7PatchDetails=None, rhel79PatchDetails=None, rhel88PatchDetails=None, litpDetails=None, artifactDetails=None, pkgsDetails=None, descriptionDetails="", tmpArea=None, remoteConnection=None,clusterName=None,drop=None,cfgTemplate=None,deploymentTemplate=None,deployProduct=None):
    '''
    Used to set relevant information regarding the Deployment
    '''
    logger.info("Start Exit Deployment Procedure.")
    jumpServerIp = dmt.utils.getJumpServerIp(networkGlobal)
    if setStatusUpdate == "no":
        state = "IDLE"
    if "cloud" not in env and "snap" not in descriptionDetails.lower() and "error" not in descriptionDetails.lower():
        updateDeploymentStatus(clusterId,state,osDetails,rhel6PatchDetails,rhel7PatchDetails,rhel79PatchDetails,rhel88PatchDetails,litpDetails,artifactDetails,pkgsDetails,descriptionDetails)
        logger.info("Auto-Deployment has been Successful")
        itamWebhookEndpointObject = ItamWebhookEndpoint.objects.first()
        if itamWebhookEndpointObject:
            dmt.utils.triggerJenkinsWebhook(itamWebhookEndpointObject.endpoint, {"deployment_id": clusterId})

    if "cloud" not in env and "snap" not in descriptionDetails.lower() and "error" in descriptionDetails.lower():
        updateDeploymentStatus(clusterId,state,osDetails,rhel6PatchDetails,rhel7PatchDetails,rhel79PatchDetails,rhel88PatchDetails,litpDetails,artifactDetails,pkgsDetails,descriptionDetails)
        logger.info("Auto-Deployment has not been Successful")

    if "cloud" not in env and "snap" in descriptionDetails.lower() and "error" not in descriptionDetails.lower():
        updateDeploymentStatus(clusterId,state,osDetails,rhel6PatchDetails,rhel7PatchDetails,rhel79PatchDetails,rhel88PatchDetails,litpDetails,artifactDetails,pkgsDetails,descriptionDetails)
        logger.info("Auto-Deployment Snapshot / Rollback Process Complete")

    logger.info("Start Remove Jump Lock Procedure.")
    removeCloudJumpLock(cloudLockFileName,cloudQueueFileName,jumpServerIp)
    logger.info("End Remove Jump Lock Procedure.")

    if tmpArea != None or remoteConnection != None:
        logger.info("Start Remove Tmp Area Procedure.")
        dmt.utils.dmtError(descriptionDetails, clusterId, tmpArea, remoteConnection)
        logger.info("End Remove Tmp Area Procedure.")

    logger.info("End Exit Deployment Procedure.")

def updateServiceGroupsAuto(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,tmpArea,clusterName,drop,cfgTemplate,xmlFile,deployProduct):
    try:
        if  DDtoDeploymentMapping.objects.filter(cluster__id=clusterId).exists():
            ddToDeploymentMappingObj = DDtoDeploymentMapping.objects.get(cluster__id=clusterId)
        else:
            raise Exception ("Error: Deployment does not have a Deployment Description to Deployment mapping set DMT")
        depDescNameObj = ddToDeploymentMappingObj.deployment_description.name
        if os.path.isabs(xmlFile) or "http" in xmlFile:
            raise Exception("The xmlfile is a path or http address. FileName only expected")
        else:
            qualifier = "::"
            if qualifier in xmlFile:
                xmlSliceNameXml = xmlFile.split(qualifier)[1]
                xmlSliceName = xmlSliceNameXml.rsplit('.', 1)[0]
                if xmlSliceName == depDescNameObj:
                    logger.info("Starting Automatic Update to Service Groups for Cluster based on latest Deployment Description")
                    ret = dmt.utils.updateClustersServicesWithDD(clusterId)
                    if ret != "SUCCESS":
                        raise Exception ("Error: Update Cluster Service With Deployment Description error")
                else:
                    raise Exception("The xmlFile parameter is not the Deployment Description set for this Cluster in DMT")

            else:
                xmlSliceName = xmlFile.rsplit('.', 1)[0]
                if xmlSliceName == depDescNameObj:
                    logger.info("Starting Automatic Update to Service Groups for Cluster based on latest Deployment Description")
                    ret = dmt.utils.updateClustersServicesWithDD(clusterId)
                    if ret != "SUCCESS":
                        raise Exception ("Error: Update Cluster Service With Deployment Description error")
                else:
                    raise Exception("The xmlFile parameter is not the Deployment Description set for this Cluster in DMT")

    except Exception as e:
        errMsg = "Error: Could not run Auto-Update of Service Groups Information for Cluster: " + str(e)
        exitDeployment(clusterId,failDepStatus,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpIsoVersion,isoVersion,packageList,errMsg,tmpArea,None,clusterName,drop,cfgTemplate,xmlFile,deployProduct)

def copyPrivateKey(remoteConnection):
    cmd = " /bin/cp /root/.ssh/vm_private_key /software/autoDeploy/"
    logger.info("Copying Private Key to /Software")
    ret,output = remoteConnection.runCmdGetOutput(cmd)
    if ( ret == 0 ):
        logger.info("Private Key copied")
    else:
        logger.error("Issue Copying Priavte Key to /software")
    return 0

def removeMsPatchFile(remoteConnection, mgtServer):
    enmInstRuntime = config.get('DMT_AUTODEPLOY', 'enmInstRuntime')
    ms_patched_done_file = os.path.join(str(enmInstRuntime), 'ms_os_patched')
    cmd = "test -f " +str(ms_patched_done_file)
    ret,output = remoteConnection.runCmdGetOutput(cmd)
    if ret == 0:
        logger.info("Removing MS Patched File from ENMInst Runtime")
        cmd = "rm -rf " +str(ms_patched_done_file)
        ret,output = remoteConnection.runCmdGetOutput(cmd)
        if ret != 0:
            logger.error("There was an issue removing the MS Patched File from ENMInst Runtime")
            return
    else:
        logger.info("There is no MS Patched File in ENMInst Runtime to remove")
    return 0

def verifyDiskRedundancyOnDbNodesWorkaround(remoteConnection, cluster, masterUserPassword):
    (ret,nodeSrv) = getListOfNodesInDeployment(cluster)
    if ret != 0:
        errMsg="Could not get the node data from the deployment"
        return (ret,errMsg)

    (ret, errMsg) = createDBWorkaroundsFolder()
    if (ret != 0):
        return (ret,errMsg)
    cmd = "cp /software/autoDeploy/deploy/bin/devSdWorkaround.bsh /etc/opt/ericsson/ERICmodeldeployment/workaroundScripts/"
    ret = remoteConnection.runCmdSimple(cmd)
    if (ret != 0):
        deleteDBWorkaroundsFolder()
        errMsg="Error: Failed to copy devSdWorkaround.bsh script to directory mounted on DB node"
        return (ret,errMsg)
    cmd = "/opt/ericsson/enminst/bin/vcs.bsh --groups -gGrp_CS_db_cluster_versant_clustered_service"
    logger.info("Getting all DB cluster hostnames")
    (ret, dbServers) = remoteConnection.runCmdGetOutput(cmd,"tty-ssh")
    if ret != 0:
        deleteDBWorkaroundsFolder()
        errMsg="Could not find any DB servers"
        return (ret,errMsg)
    dbHostnames = []
    for srv in nodeSrv:
        if srv.server.hostname in dbServers:
            dbHostnames.append(str(srv.server.hostname))
    litpUsername = config.get('DMT_AUTODEPLOY', 'litpUsername')
    loginToDbRunCommand = config.get('DMT_AUTODEPLOY', 'loginToDbRunCommand')
    devSdWorkaroundScript = config.get('DMT_AUTODEPLOY', 'devSdWorkaroundScript')
    for srv in dbHostnames:
        logger.info("Connecting to DB cluster at: " + srv)
        cmd = loginToDbRunCommand + " " + srv + " " + litpUsername + " " + masterUserPassword + " " + devSdWorkaroundScript
        ret = remoteConnection.runCmdSimple(cmd)
        if (ret != 0):
            deleteDBWorkaroundsFolder()
            errMsg="Error: Error encountered while running devSdWorkaround.bsh script"
            return (ret,errMsg)
        logger.info("Applied Workaround described in Jira CIS-42100 to DB server at: " + srv)
    deleteDBWorkaroundsFolder()
    return 0

def createDBWorkaroundsFolder():
    cmd = "mkdir -p /etc/opt/ericsson/ERICmodeldeployment/workaroundScripts"
    ret = remoteConnection.runCmdSimple(cmd)
    if (ret != 0):
        errMsg="Error: Failed to create workaroundScripts folder in /etc/opt/ericsson/ERICmodeldeployment"
        return (ret,errMsg)
    return (0,"OK")

def deleteDBWorkaroundsFolder():
    cmd = "rm -rf /etc/opt/ericsson/ERICmodeldeployment/workaroundScripts"
    ret = remoteConnection.runCmdSimple(cmd)
    if (ret != 0):
        errMsg="Error: Failed to delete workaroundScripts folder in /etc/opt/ericsson/ERICmodeldeployment"

def downloadDeployScripts(deployScriptVersion, tmpArea):
    '''
    Downloading Deployment Scripts to the Gateway"
    '''

    lmsUploadDir = config.get('DMT_AUTODEPLOY', 'upgradeLmsUploadDir')
    scriptFile = "DeploymentScripts-" + deployScriptVersion + ".tar.gz"
    url = config.get('DMT_AUTODEPLOY', 'ENM_nexus_url') + "/com/ericsson/tor/DeploymentScripts/" + deployScriptVersion + "/" + scriptFile
    testurl = config.get('DMT_AUTODEPLOY', 'ENM_nexus_url') + "/com/ericsson/tor/DeploymentScripts/" + deployScriptVersion
    try:
        resp = urllib2.urlopen(testurl, timeout=10)
    except (urllib2.URLError, urllib2.HTTPError) as e:
        logger.info("Nexus Proxy server not responding Deployment Scripts with version " + deployScriptVersion + ", Moving to download from Hub Nexus")
        url = config.get('DMT_AUTODEPLOY', 'nexus_url') + "/releases/com/ericsson/tor/DeploymentScripts/" + deployScriptVersion + "/" + scriptFile

    logger.info("Downloading RV Scripts from nexus: " + url)
    returnCode = fwk.utils.downloadFile(url, tmpArea)
    if (returnCode != 0):
        return "Issue downloading Deployment Scripts", returnCode

    target = lmsUploadDir + "/deploy"
    commandList = ["sudo gtar -xf " + tmpArea + "/" + scriptFile + " -C " + tmpArea,
                "sudo rm -rf " + target,
                "sudo mkdir -p " + target,
                "sudo tar --directory=" + target + " -xzvf " + tmpArea+ "/" + scriptFile]

    for command in commandList:
        result, returnCode = executeCmd(command)
        if not returnCode == 0:
            return result, returnCode
    logger.info("Successfully Downloaded Deployment Scripts")
    return "success", 0


def deploymentAttachedNASserverData(deploymentId):
    '''
    Getting NAS Server data from a Deployment
    '''
    nasServer = None
    errorMsg = "Error: No Attached NAS Found for this DeploymentId " +str(deploymentId)
    nasUsername = config.get('DMT_AUTODEPLOY', 'nasUsername')
    nasPassword = None
    nasData = {}
    try:
        if ClusterToNASMapping.objects.filter(cluster__id=deploymentId).exists():
            fields = ('nasServer__id','nasServer__server__id', 'nasServer__server__hostname', 'nasServer__server__domain_name')
            nasMap = ClusterToNASMapping.objects.only(fields).values(*fields).filter(cluster__id=deploymentId)[0]
            nasPassword = NASServer.objects.only('credentials__password').values('credentials__password').get(server=nasMap['nasServer__server__id'], credentials__username=nasUsername) # TODO: add one more param in where clause e.g. credential type as ilo and nas credentials might conflict with each other which may give two nas server instance instead one
            serverId = nasMap['nasServer__server__id']
            nasData['hostname'] = nasMap['nasServer__server__hostname']
            nasData['domain_name'] = nasMap['nasServer__server__domain_name']
        elif ClusterToDASNASMapping.objects.filter(cluster__id=deploymentId).exists():
            fields = ('dasNasServer__id', 'dasNasServer__hostname', 'dasNasServer__domain_name')
            nasMap = ClusterToDASNASMapping.objects.only(fields).values(*fields).get(cluster__id=deploymentId)
            nasPassword = NASServer.objects.only('credentials__password').values('credentials__password').get(server=nasMap['dasNasServer__id'], credentials__username=nasUsername)
            serverId = nasMap['dasNasServer__id']
            nasData['hostname'] = nasMap['dasNasServer__hostname']
            nasData['domain_name'] = nasMap['dasNasServer__domain_name']
        if nasData == {}:
            logger.error(errorMsg)
            return errorMsg, 1
        nic = NetworkInterface.objects.only('id').values('id').get(server__id=serverId)
        ipaddrs = IpAddress.objects.get(nic=nic['id'], ipType="nas")
        nasData['ipAddress'] = ipaddrs
        nasData['nasUsername'] = nasUsername
        nasData['nasPassword'] = nasPassword['credentials__password']
        return nasData, 0
    except Exception as error:
        errorMsg = str(errorMsg) + ":" + str(error)
        logger.error(errorMsg)
        return errorMsg, 1

def deploymentAttachedILOserverData(nasData, deploymentId):
    '''
    Getting NAS Server iLo data from a physical Deployment
    '''
    nas_command = 'vxclustadm nidmap'
    errorMsg = "Error: No Attached NAS iLO Found for this DeploymentId " + str(deploymentId)
    nasMasterNnode = ''
    iloData={}
    nasNodeData = {}
    outputData = {}

    result, returnCode = runServerCommand(nas_command, str(nasData['ipAddress']), nasData['nasUsername'], nasData['nasPassword'])
    if returnCode != 0:
        return result, returnCode

    nasMasterNnode, returnCode = findNASMasterNode(result)
    if returnCode !=0 or nasMasterNnode == '':
        return nasMasterNnode, retrunCode
    logger.info('NAS master node is ' + str(nasMasterNnode))
    masterNodeNumber = ""
    if '-' in str(nasMasterNnode):
        masterNodeNumber = nasMasterNnode.split('-')[-1]
    else:
        masterNodeNumber = nasMasterNnode.split('_')[-1]
    if masterNodeNumber == '01':
        nasCredType = 'support'
        nasIloCredType = 'masterIlo'
        nasIloIpType = 'nasInstalIlolIp1'
    else:
        nasCredType = 'support'
        nasIloCredType = 'supportIlo'
        nasIloIpType = 'nasInstalIlolIp2'
    try:
        if ClusterToNASMapping.objects.filter(cluster__id=deploymentId).exists():
            fields = ('nasServer__id', 'nasServer__server__id')
            nasMap = ClusterToNASMapping.objects.only(fields).values(*fields).filter(cluster__id=deploymentId)[0]
            serverId = nasMap['nasServer__server__id']
        elif ClusterToDASNASMapping.objects.filter(cluster__id=deploymentId).exists():
            fields = ('dasNasServer__id', 'dasNasServer__hostname', 'dasNasServer__domain_name')
            nasMap = ClusterToDASNASMapping.objects.only(fields).values(*fields).get(cluster__id=deploymentId)
            serverId = nasMap['dasNasServer__id']

        nasNodeDetails = NASServer.objects.only('credentials__username', 'credentials__password').values(
            'credentials__username', 'credentials__password').get(server=serverId,
                                                                  credentials__credentialType=nasCredType)  # TODO: add one more param in where clause e.g. credential type as ilo and nas credentials might conflict with each other which may give two nas server instance instead one
        nasIloDetails = NASServer.objects.only('credentials__username', 'credentials__password').values(
            'credentials__username', 'credentials__password').get(server=serverId,
                                                                  credentials__credentialType=nasIloCredType)  # TODO: add one more param in where clause e.g. credential type as ilo and nas credentials might conflict with each other which may give two nas server instance instead one
        nodeServerObject = Server.objects.get(id=serverId)
        hardwareType = nodeServerObject.hardware_type
        if "cloud" in hardwareType:
            macIdentifier = ipv4Identifier = ipv6Identifier = nodeServerObject.id
        else:
            macIdentifier = ipv4Identifier = ipv6Identifier = '1'

        networkObject = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth0",
                                                     nicIdentifier=macIdentifier)
        ipAddrObjNasIlo = IpAddress.objects.get(nic_id=networkObject.id, ipType=nasIloIpType,
                                                ipv4UniqueIdentifier=ipv4Identifier)
        iloData['hostname'] = ipAddrObjNasIlo.address
        iloData['username'] = nasIloDetails['credentials__username']
        iloData['password'] = nasIloDetails['credentials__password']
        nasNodeData['nasMasterNode'] = nasMasterNnode
        nasNodeData['username'] = nasNodeDetails['credentials__username']
        nasNodeData['password'] = nasNodeDetails['credentials__password']
        outputData['nasNodeDetails'] = nasNodeData
        outputData['nasIloDetails'] = iloData
        if outputData == {} or iloData == {} or nasNodeData == {}:
            logger.error(errorMsg)
            return errorMsg, 1
        return outputData, 0
    except Exception as error:
        errorMsg = str(errorMsg) + ":" + str(error)
        logger.error(errorMsg)
        return errorMsg, 1

def getNASconfigFromPS(productSetVer, nasConfigVer):
    '''
    Getting the NAS Config info from Product Set
    '''
    productSetVersion = None
    nasConfigProduct = config.get('DMT_AUTODEPLOY','nasConfigProduct')
    nasConfigData = {}
    try:
        productSetVersion = ProductSetVersion.objects.only('id').values('id').get(version=productSetVer, productSetRelease__productSet__name="ENM")
    except Exception as error:
        errorMsg = "Issue getting value for Product Set Version"+ str(productSetVer) + ": " + str(error)
        logger.error(errorMsg)
        return errorMsg, 1
    try:
        if nasConfigVer:
            fields = ('mediaArtifact__name', 'mediaArtifact__mediaType', 'version', 'groupId', 'arm_repo')
            nasConfig = ISObuild.objects.only(fields).values(*fields).get(drop__release__product__name=nasConfigProduct, version=nasConfigVer)
            nasConfigData['artifactId'] = nasConfig['mediaArtifact__name']
            nasConfigData['mediaType'] = nasConfig['mediaArtifact__mediaType']
            nasConfigData['version'] = nasConfig['version']
            nasConfigData['groupId'] = nasConfig['groupId']
            nasConfigData['arm_repo'] =  nasConfig['arm_repo']
        else:
            fields = ('mediaArtifactVersion__mediaArtifact__name', 'mediaArtifactVersion__mediaArtifact__mediaType', 'mediaArtifactVersion__version', 'mediaArtifactVersion__groupId', 'mediaArtifactVersion__arm_repo')
            psMap = ProductSetVersionContent.objects.only(fields).values(*fields).get(productSetVersion__id=productSetVersion['id'], mediaArtifactVersion__drop__release__product__name=nasConfigProduct)
            nasConfigData['artifactId'] = psMap['mediaArtifactVersion__mediaArtifact__name']
            nasConfigData['mediaType'] = psMap['mediaArtifactVersion__mediaArtifact__mediaType']
            nasConfigData['version'] = psMap['mediaArtifactVersion__version']
            nasConfigData['groupId'] = psMap['mediaArtifactVersion__groupId']
            nasConfigData['arm_repo'] =  psMap['mediaArtifactVersion__arm_repo']
    except Exception as error:
        errorMsg = "Issue getting value for NAS Configuration Kit: " + str(error)
        logger.error(errorMsg)
        return errorMsg, 1
    return nasConfigData, 0

def checkNASconfigVerison(nasConfig, baseLogin, nasData, slaveLogin):
    '''
    Checking the installed NAS Configuration Kit to see if install/downgrade is required
    '''
    newVer = nasConfig['version']
    result, returnCode = executeCmd("rpm -q " + str(nasConfig['artifactId']), baseLogin)
    if (returnCode != 0):
        return result, returnCode
    artifactDetail = re.findall(r'ERIC(.*?)noarch',str(result))
    if artifactDetail is None:
        return "No NAS Config Version Found, exiting updating NAS Server process.", 200
    (artifactVersion, junk) = str("".join(artifactDetail)).rsplit("-", 1)
    (artifact, oldVer) = str(artifactVersion).split("-")
    if slaveLogin is not None:
        logger.info("Retreiving NAS salve node details")
        slaveResult, returnCode = executeCmd("sshpass -p " + nasData['nasPassword'] + " ssh " + nasData['nasUsername'] + "@" + slaveLogin + " rpm -q " + str(nasConfig['artifactId']), baseLogin)
        slaveArtifactDetail = re.findall(r'ERIC(.*?)noarch',str(slaveResult))
        if slaveArtifactDetail is None:
            return "No slave NAS Config Version Found, exiting updating NAS Server process.", 200
        (slaveArtifactVersion, junk) = str("".join(slaveArtifactDetail)).rsplit("-", 1)
        (slaveArtifact, slaveOldVer) = str(slaveArtifactVersion).split("-")
        if slaveOldVer != oldVer:
            return "NAS Config version mismatch between master and slave: " + str(oldVer) + ", " + str(slaveOldVer), 1
    else:
        logger.info("NAS Slave node not present")
    if LooseVersion(newVer) == LooseVersion(oldVer):
        return "This version " +str(newVer) + " of " + str(nasConfig['artifactId']) + " is already installed on the NAS Server", 200
    elif LooseVersion(oldVer) <  LooseVersion(newVer):
        return "install", 0
    return "This version " + str(newVer) + " of " + str(nasConfig['artifactId']) + " is older that the installed one i.e. " + str(oldVer) + " on the NAS Server. Nas downgrade is not supported anymore.", 200

def nasRebootCheck(nasServer, baseLogin, extras = None):
    '''
    Checking if Reboot is happening
    '''
    response = 1
    retries = 0
    time.sleep(120)
    while (retries != 90):
        if extras == None:
            response = int(os.system("ping -c 1 -w2 " + nasServer + " > /dev/null 2>&1"))
            if response == 0:
                time.sleep(90)
                break
        else:
            result, response = executeCmd(str(extras['command']), baseLogin)
            if str(extras['nasHostName']) + '_01' in result and str(extras['nasHostName']) + '_02' in result:
                logger.info('Both nodes are up and joined the cluster')
                break
        retries += 1
        time.sleep(30)
    if response != 0:
        return "Reboot Failed", response
    return "Reboot Finished", 0

def downloadNASmedia(nasMedia, nexusUrl, tmpArea, nasSnapshotUrl):
    '''
    Downloading NAS Media Artifacts
    '''
    url = ''
    if nasSnapshotUrl:
        splitUrlList = nasSnapshotUrl.split('/')
        artifact = [item for item in splitUrlList if 'tar.gz' in item][0] # Make sure there is no / char in name of the file and tar.gz is not present in any other part of the url
        url = nasSnapshotUrl
    else:
        artifact = str(nasMedia['artifactId']) + "-" + str(nasMedia['version']) + "." + str(nasMedia['mediaType'])
        nasMediaUrl = "/" + nasMedia['arm_repo'] + "/" + str(nasMedia['groupId']).replace(".", "/") + "/" + str(nasMedia['artifactId']) + "/" + str(nasMedia['version']) + "/" + str(artifact)
        url = nexusUrl + nasMediaUrl
    logger.info('Downloading NAS media artifacts from: '+ str(url))
    returnCode = fwk.utils.downloadFile(url, tmpArea)
    if (returnCode != 0):
        errorMsg = ""
        if nasSnapshotUrl:
            errorMsg = "Issue downloading: " + str(nasMedia['artifactId']) + "-" + " from Snapshot Url: " + str(url)
        else:
            errorMsg = "Issue downloading: " + str(nasMedia['artifactId']) + "-" + str(nasMedia['version']) + " from Nexus Url: " + str(url)
        return errorMsg, None, returnCode
    return artifact, nasMedia['mediaType'], 0

def nasFileCheck(command, baseLogin):
    '''
    Checking for file on the NAS Server
    '''
    result, returnCode = executeCmd('[ -f '+str(command)+' ] && echo "Found" || echo "Not found"', baseLogin)
    if (returnCode != 0):
        return result, returnCode
    junk, result = str(result).split("assword:")
    result = str(result).split()
    if "Found" in str(result):
        result = "Found"
    else:
        result = "Not found"
    return result, 0

def nasLockfileWait(command, baseLogin):
    '''
    Waiting for the NAS Server to be free update
    '''
    logger.info("Lockfile found. Waiting for NAS Server, currently NAS Server being updated by another User")
    retries = 0
    time.sleep(30)
    while (retries != 90):
        result, returnCode = nasFileCheck(command, baseLogin)
        if "Not found" in str(result):
           return result, returnCode
        retries += 1
        time.sleep(30)
    return "Wait timeout, currently NAS Server being updated by another User", 1

def executeCmd(command, baseLogin=None, realTime=False):
    '''
    Used to execute commands
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
    if realTime:
        while True:
            line = process.stdout.readline()
            logger.info(str(line))
            if line == '' and process.poll() != None:
                break
    outputData, returnCode = process.communicate()[0], process.returncode
    if not realTime:
        logger.info(outputData)
    if not returnCode == 0:
        errMsg = "Issue with command: " + str(command) + ", output: " + str(outputData)
        return errMsg, returnCode
    return outputData, 0

def nasCleanUp(tmpArea, nasLockfile, baseLogin):
    '''
    Clean Up tmp/lockfile
    '''
    executeCmd("sudo rm -rf " + str(tmpArea))
    executeCmd('sudo /opt/VRTS/bin/hacli -cmd "rm -rf '+ str(nasLockfile) + '"', baseLogin)

def findNASMasterNode(stdout):
    '''
    Find Nas Master Node
    '''
    for line in stdout:
        if 'Master' not in line:
            continue
        else:
            return line.split()[0], 0
    return 'Master Node not found in results', 1

def findNASSlaveNode(stdout):
    '''
    Find NAS Slave Node
    '''
    for line in stdout:
        if 'Slave' not in line:
            continue
        else:
            return line.split()[0], 0
    return 'Slave Node not found in results', 1

def runServerCommand(command, hostname, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logger.info('shh connect to '+str(hostname))
    client.connect(hostname=hostname, username=username, password=password)
    try:
        logger.info('executing command '+str(command))
        _stdin, stdout, _stderr = client.exec_command(
            command
        )

        stdout = stdout.readlines()
        client.close()
        logger.info('connection closed with host : '+ str(hostname))
        return stdout, 0

    except Exception as e:
        errMsg = "Error: Could not run the command into nas server with error : " + str(e)
        return errMsg, 1

def ssh_command(user, host, password):
    ssh_newkey = 'Are you sure you want to continue connecting (yes/no)?'
    child = pexpect.spawn('ssh -l %s %s'%(user, host))
    child.logfile = sys.stdout
    i = child.expect([pexpect.TIMEOUT, ssh_newkey, 'password: '])
    if i == 0: # Timeout
        logger.info('ERROR!')
        errorMsg = 'ERROR: SSH could not login. Here is what SSH said:'
        return errorMsg, 1
    if i == 1: # SSH does not have the public key. Just accept it.
        child.sendline ('yes')
        # child.expect ('password: ')
        i = child.expect([pexpect.TIMEOUT, 'password: '])
        if i == 0: # Timeout
            logger.info('ERROR!')
            errorMsg = 'ERROR: SSH could not login. Here is what SSH said:'
            return errorMsg, 1
    child.sendline(password)
    try:
        child.expect('</>hpiLO->', timeout=60)
        return child, 0
    except pexpect.TIMEOUT:
        errorMsg = 'ERROR: Could not connect to the NAS iLO'
        return errorMsg, 1


def iloRunCMD(nasIloData, command):
    '''
    Run command in NAS node through iLO
    '''
    iloData = nasIloData['nasIloDetails']
    nasNodeData = nasIloData['nasNodeDetails']
    nas_master_node = nasNodeData['nasMasterNode']

    result, returnCode = ssh_command(iloData['username'], iloData['hostname'], iloData['password'])
    if returnCode != 0:
        return result, returnCode
    child = result
    child.logfile = sys.stdout
    child.sendline('stop /system1/oemhp_vsp1')
    child.expect('</>hpiLO->', timeout=60)
    child.sendline('vsp')

    try:
        response = child.expect([str(nas_master_node)+' login: ', 'root@'+str(nas_master_node)+' ~]# ', str(nas_master_node)+':~ # ','Password: '],timeout=60)
        if response == 0:
            child.sendline(nasNodeData['username']) # these values must be generated from db
            child.expect('Password: ',timeout=60)
            child.sendline(nasNodeData['password'])
            child.expect(['root@' + str(nas_master_node) + ' ~]# ', str(nas_master_node) + ':~ # '], timeout=60)
        elif response == 3:
            child.sendline(nasNodeData['password'])
            child.expect(['root@' + str(nas_master_node) + ' ~]# ', str(nas_master_node) + ':~ # '], timeout=60)
        child.sendline(command)
        response = child.expect(['root@' + str(nas_master_node) + ' ~]# ', str(nas_master_node) + ':~ # ','Starting replication daemon disabled', 'Starting VCS: \[  OK  \]'], timeout=2800)
        if response == 2 or response == 3:
            logger.info('Sending enter key press')
            child.sendline('\r')
            response = child.expect([str(nas_master_node)+' login: ', 'root@'+str(nas_master_node)+' ~]# ', str(nas_master_node)+':~ # ','Password: '],timeout=60)
            if response == 0:
                child.sendline(nasNodeData['username']) # these values must be generated from db
                child.expect('Password: ',timeout=60)
                child.sendline(nasNodeData['password'])
                child.expect(['root@' + str(nas_master_node) + ' ~]# ', str(nas_master_node) + ':~ # '], timeout=60)
            elif response == 3:
                child.sendline(nasNodeData['password'])
                child.expect(['root@' + str(nas_master_node) + ' ~]# ', str(nas_master_node) + ':~ # '], timeout=60)
        child.sendline('exit')
        logger.info('connection closed')
        child.close()
        return child.before, 0
    except pexpect.TIMEOUT:
        logger.info('Exception: Timeout')
        child.sendline('exit')
        logger.info('connection closed')
        child.close()
        return 'failed result of ilo run command with timeout', 1
    except pexpect.EOF:
        logger.info('EOF')
        child.sendline('exit')
        logger.info('close the connection after exit from nas console via iLO')
        child.close()
        return 'failed result of ilo run command with end of file exception', 1

def getHardWareType(clusterId):
    '''
    Function used to get the environment of the deployment i.e. cloud or physical
    '''
    try:
        if Cluster.objects.filter(id=clusterId).exists():
            cluster = Cluster.objects.get(id=clusterId)
        else:
            logger.error("Ensure that the cluster/deployment ID defined is registered on the portal")
            return "Ensure that the cluster/deployment ID defined is registered on the portal", 1

        mgtServer = cluster.management_server
        environment = mgtServer.server.hardware_type
        return environment, 0

    except Exception as e:
        return e.message, 1


def nasWhitelistingSetup(baseLogin, user, nasServer, tmpArea):
    '''
    NAS Whitelisting IP Addresses Setup
    '''

    vlanDetailsFile = config.get('DMT_AUTODEPLOY', 'nasVlanDetailsFile')
    vlanDetailsFileUrl = config.get('DMT_AUTODEPLOY', 'nasVlanDetailsFileUrl')
    vlanDetailsFileTmp = str(tmpArea) + "/" + str(vlanDetailsFile)
    whitelistingFileDir = config.get('DMT_AUTODEPLOY', 'nasWhitelistingFileDir')
    whitelistingFile = config.get('DMT_AUTODEPLOY', 'nasWhitelistingFile')
    nasWhitelistingFile = str(whitelistingFileDir) + str(whitelistingFile)

    logger.info("Starting Whitelisting IP Addresses Setup...")
    logger.info("Getting IP Addresses for Whitelisting Setup...")
    logger.info("Downloading IP Addresses file: " + vlanDetailsFileUrl)
    cmd = 'curl -f -o ' + str(vlanDetailsFileTmp) + ' -L -# "' + str(vlanDetailsFileUrl) + '"'
    result, returnCode = executeCmd(cmd)
    if (returnCode != 0):
        errorMsg = "Issue downloading: " + str(vlanDetailsFile) +  " from Nexus Url: " + str(vlanDetailsFileUrl)
        return errorMsg, returnCode

    whitelistingCmds = ["scp " + str(vlanDetailsFileTmp) + " " +  user + "@" + str(nasServer)+ ":" + str(whitelistingFileDir),
                        'sed $"s/[^[:print:]\t]//g" ' + str(whitelistingFileDir) + str(vlanDetailsFile) + " >> " +  str(nasWhitelistingFile),
                        "cat " + str(nasWhitelistingFile),
                        "rm -f " + str(whitelistingFileDir) + str(vlanDetailsFile)]

    for cmd in whitelistingCmds:
        result, returnCode = executeCmd(cmd, baseLogin)
        if returnCode != 0:
            return result, returnCode
    msg = "Finished Whitelisting IP Addresses Setup.."
    logger.info(msg)
    return msg, 0


def checkNASType(deploymentId):
    '''
    Checking the NAS Type for the Deployment
    '''
    msg = ""
    skip = False
    fields = ('nasType',)
    logger.info("Checking NAS Type for this DeploymentId: " + str(deploymentId))
    try:
        if NasStorageDetails.objects.filter(cluster__id=deploymentId).exists():
            nasStorage = NasStorageDetails.objects.only(fields).values(*fields).get(cluster__id=deploymentId)
            if str(nasStorage['nasType']) == "unityxt":
                skip = True
                msg = "Skipping functionlity due to NAS Type being unityxt"
        else:
            msg = "Continue updating NAS config for this DeploymentId: " + str(deploymentId)
    except Exception as error:
        errorMsg = "Error: Issue getting Storage Attached Network Details for this DeploymentId " + str(deploymentId) + ":" + str(error)
        logger.error(errorMsg)
        skip = True
        return skip, errorMsg, 1
    return skip, msg, 0


def updatingNASconfig(productSetVer, deploymentId, nasConfigVer, deployScriptVersion, installType, nasSnapshotUrl):
    '''
    For Upgrading/Downgrading NAS Server's NAS Configuration Kit
    '''
    checkResult, msg, returnCode = checkNASType(deploymentId)
    if checkResult:
        return msg, returnCode

    nasDeployScriptVersion = config.get('DMT_AUTODEPLOY', 'nasDeployScriptVersion')
    if LooseVersion(nasDeployScriptVersion) > LooseVersion(deployScriptVersion):
        return "Deploy script version entered is not compatible to use update NAS functionality", 200

    cloudDownLoadDir = config.get('DMT_AUTODEPLOY', 'cloudDownLoadDir')
    tmpArea = None
    if not os.path.exists(cloudDownLoadDir):
        # Randomly generated directory with /tmp
        tmpArea = tempfile.mkdtemp()
    else:
        # For cloud there is a specific area to use /export/data
        random = randint(2,9000)
        tmpArea = cloudDownLoadDir + "/temp" + str(random)
        retCode = dmt.utils.cleanOutDirectoryArea(cloudDownLoadDir,0,"temp")
        os.makedirs(cloudDownLoadDir + "/temp" + str(random))
    nexusUrl= config.get('DMT_AUTODEPLOY', 'nexus_url')
    keyFileName=config.get('DMT_AUTODEPLOY', 'key')
    nasMediaConfigDir = config.get('DMT_AUTODEPLOY', 'nasMediaConfigDir')
    nasConfigInstall = config.get('DMT_AUTODEPLOY', 'nasConfigInstall')
    nasConfigAudit = config.get('DMT_AUTODEPLOY', 'nasConfigAudit')
    nasHardwareClock = config.get('DMT_AUTODEPLOY', 'nasHardwareClock')
    loginToRunCommand = config.get('DMT_AUTODEPLOY', 'loginToNASrunCommand')
    nasVAfiles = ast.literal_eval(config.get('DMT_AUTODEPLOY', 'nasVAfile'))
    nasLockfile = config.get('DMT_AUTODEPLOY', 'nasLockfile')
    nasWhitelistingVersion = config.get('DMT_AUTODEPLOY', 'nasWhitelistingVersion')
    nasIloData = {}
    hardWareType = ''

    hardWareType, returnCode = getHardWareType(deploymentId)
    if returnCode != 0:
        return hardWareType, returnCode


    nasData, returnCode = deploymentAttachedNASserverData(deploymentId)
    if returnCode != 0:
        executeCmd("sudo rm -rf " + str(tmpArea))
        return nasData, returnCode
    logger.info("Starting the update of NAS Config version process, on NAS Server: " + str(nasData['hostname']))

    nasServer = str(nasData['ipAddress'])
    user = nasData['nasUsername']
    result, returnCode = downloadDeployScripts(deployScriptVersion, tmpArea)
    if returnCode != 0:
        logger.error(result)
        return result, returnCode

    baseLogin = loginToRunCommand + " " + nasServer + " " + user + " " + nasData['nasPassword']
    if hardWareType == 'cloud':
        nasData['ipAddress'] = dmt.utils.getNasPhysicalIp(baseLogin)
        baseLogin = loginToRunCommand + " " + str(nasData['ipAddress']) + " " + user + " " + nasData['nasPassword']

    nasConfig, returnCode = getNASconfigFromPS(productSetVer, nasConfigVer)
    if returnCode != 0:
        executeCmd("sudo rm -rf " + str(tmpArea))
        return nasConfig, returnCode

    for nasVAfile in nasVAfiles:
        result, returnCode = nasFileCheck(str(nasVAfile), baseLogin)
        if returnCode != 0:
            executeCmd("sudo rm -rf " + str(tmpArea))
            return result, returnCode
        if result == "Not found":
            continue
        else:
            break
    if result == "Not found":
        executeCmd("sudo rm -rf " + str(tmpArea))
        return "Not VA installed NAS Server, not updating the NAS Config version", 200

    result, returnCode = nasFileCheck(str(nasMediaConfigDir)+ str(nasLockfile), baseLogin)
    if returnCode != 0:
        executeCmd("sudo rm -rf " + str(tmpArea))
        return result, returnCode
    if result == "Found":
        result, returnCode = nasLockfileWait(str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
        if returnCode != 0:
            executeCmd("sudo rm -rf " + str(tmpArea))
            return result, returnCode

    nasSlaveNode, returnCode = dmt.utils.parseNASCommandForSlaveNode(nasData)
    yumAction = ""
    if nasSnapshotUrl:
        yumAction = "install"
    else:
        result, returnCode = checkNASconfigVerison(nasConfig, baseLogin, nasData, nasSlaveNode)
        if returnCode != 0:
            executeCmd("sudo rm -rf " + str(tmpArea))
            return result, returnCode
        yumAction = result

    result, returnCode = executeCmd(str(nasConfigAudit), baseLogin)
    if returnCode != 0:
        if returnCode == 3:
            logger.warning("First NAS Config Audit run failed with warnings only, check the audit report on the NAS Server. Continuing the update of NAS Config version process.")
        else:
            executeCmd("sudo rm -rf " + str(tmpArea))
            if "NAS_AUDIT_TASKS_INFO" in str(result):
                return "NAS Config Audit Failed, check the audit report on the NAS Server.", 200
            else:
                return "Issue running NAS Config Audit.", returnCode

    result, returnCode = executeCmd("rm -rf " +str(nasMediaConfigDir)+"*", baseLogin)
    if returnCode != 0:
        executeCmd("sudo rm -rf " + str(tmpArea))
        return result, returnCode

    result, returnCode = executeCmd("mkdir -p " + str(nasMediaConfigDir) , baseLogin)
    if returnCode != 0:
        executeCmd("sudo rm -rf " + str(tmpArea))
        return result, returnCode

    result, returnCode = executeCmd("touch " + str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
    if returnCode != 0:
        executeCmd("sudo rm -rf " + str(tmpArea))
        return result, returnCode

    nasConfigArtifact, mediaType, returnCode = downloadNASmedia(nasConfig, nexusUrl, tmpArea, nasSnapshotUrl)
    if returnCode != 0:
        nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
        return nasConfigArtifact, returnCode

    if hardWareType != 'cloud' and hardWareType != 'virtual':
        installCommands = ["scp " +str(tmpArea) +"/" + str(nasConfigArtifact)+ " " + user+"@"+str(nasServer)+":"+str(nasMediaConfigDir),
                           "tar zxvf " + str(nasMediaConfigDir) + str(nasConfigArtifact)  + " -C " +str(nasMediaConfigDir),
                           "yum -y " + str(yumAction) + " " + str(nasMediaConfigDir) + str(nasConfigArtifact).replace(mediaType, "rpm")]
    else:
        installCommands = ["scp " + str(tmpArea) + "/" + str(nasConfigArtifact) + " " + user + "@" + str(nasServer) + ":" + str(nasMediaConfigDir),
                           "tar zxvf " + str(nasMediaConfigDir) + str(nasConfigArtifact) + " -C " + str(nasMediaConfigDir),
                           "yum -y " + str(yumAction) + " " + str(nasMediaConfigDir) + str(nasConfigArtifact).replace(mediaType, "rpm"),
                           str(nasMediaConfigDir) + str(nasConfigInstall)]

    for command in installCommands:
        result, returnCode = executeCmd(command, baseLogin)
        if returnCode != 0:
            nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
            return result, returnCode
        if "Reboot required" in str(result) or 'master will be rebooted' in str(result).lower():
            logger.info('Reboot : required')
            result, returnCode = nasRebootCheck(nasServer, baseLogin)
            logger.info(result)
            if returnCode != 0:
                nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                return result, returnCode

    #NAS Whitelisting Setup
    if LooseVersion(nasWhitelistingVersion) <= LooseVersion(nasConfig['version']):
        result, returnCode = nasWhitelistingSetup(baseLogin, user, nasServer, tmpArea)
        if returnCode != 0:
            nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
            return result, returnCode

    if hardWareType != 'cloud' and hardWareType != 'virtual':
        logger.info('Updating Nas.....')
        logger.info('Fetching the attached iLO data')
        nasIloData, returnCode = deploymentAttachedILOserverData(nasData, deploymentId)
        if returnCode != 0:
            executeCmd("sudo rm -rf " + str(tmpArea))
            return nasIloData, returnCode
        result, returnCode = iloRunCMD(nasIloData, str(nasMediaConfigDir) + str(nasConfigInstall))
        if returnCode != 0:
            executeCmd("sudo rm -rf " + str(tmpArea))
            nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
            return result, returnCode

        if "Reboot required" in str(result) or 'master will be rebooted' in str(result).lower():
            logger.info('Reboot : required')
            result, returnCode = nasRebootCheck(nasServer, baseLogin)
            if returnCode != 0:
                nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                return result, returnCode
            else:
                logger.info('Waiting Nas nodes to join the cluster')
                command = "/opt/SYMCsnas/scripts/net/net_ipconfig.sh show | grep Virtual | grep -v 'Con IP' | awk '{print $4}' "
                extras = {}
                extras['command'] = command
                extras['nasHostName'] = nasIloData['nasNodeDetails']['nasMasterNode'].split('_')[0]
                result, returnCode = nasRebootCheck(nasServer, baseLogin, extras)
                if returnCode != 0:
                    nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                    return result, returnCode

        if (installType == "initial_install"):
            logger.info('Fetching the attached iLO data')
            nasIloData, returnCode = deploymentAttachedILOserverData(nasData, deploymentId)
            if returnCode != 0:
                executeCmd("sudo rm -rf " + str(tmpArea))
                return nasIloData, returnCode
            result, returnCode = iloRunCMD(nasIloData, str(nasMediaConfigDir) + str(nasConfigInstall))
            if returnCode != 0:
                nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                return result, returnCode

        if "Reboot required" in str(result) or 'master will be rebooted' in str(result).lower():
            logger.info('Second Reboot : required')
            result, returnCode = nasRebootCheck(nasServer, baseLogin)
            logger.info(result)
            if returnCode != 0:
                nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                return result, returnCode
            else:
                logger.info('Waiting Nas nodes to join the cluster')
                command = "/opt/SYMCsnas/scripts/net/net_ipconfig.sh show | grep Virtual | grep -v 'Con IP' | awk '{print $4}' "
                extras = {}
                extras['command'] = command
                extras['nasHostName'] = nasIloData['nasNodeDetails']['nasMasterNode'].split('_')[0]
                result, returnCode = nasRebootCheck(nasServer, baseLogin, extras)
                if returnCode != 0:
                    nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                    return result, returnCode

    else:
        if "Reboot required" in str(result) or 'master will be rebooted' in str(result).lower():
            logger.info('Reboot : required')
            result, returnCode = nasRebootCheck(nasServer, baseLogin)
            logger.info(result)
            if returnCode != 0:
                nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                return result, returnCode

        if (installType == "initial_install"):
            result, returnCode = executeCmd(str(nasMediaConfigDir) + str(nasConfigInstall), baseLogin)
            if returnCode != 0:
                nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                return result, returnCode

        if "Reboot required" in str(result) or 'master will be rebooted' in str(result).lower():
            logger.info('rebooting: required')
            result, returnCode = nasRebootCheck(nasServer, baseLogin)
            logger.info(result)
            if returnCode != 0:
                nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
                return result, returnCode

    result, returnCode = executeCmd(str(nasHardwareClock), baseLogin)
    if returnCode != 0:
        nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
        return result, returnCode

    result, returnCode = executeCmd(str(nasConfigAudit), baseLogin)
    if returnCode != 0:
        nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
        if returnCode == 3:
            return "Successfully Updated but NAS Config Audit Failed due to warnings only, check the audit report on the NAS Server.", 200
        else:
            return "NAS Config Audit Failed, check the audit report on the NAS Server.", 200

    nasCleanUp(tmpArea, str(nasMediaConfigDir) + str(nasLockfile), baseLogin)
    nasVersionMessage = ''
    if nasSnapshotUrl:
        nasVersionMessage = str(nasSnapshotUrl)
    else:
        nasVersionMessage = str(nasConfig['version'])
    return "Successfully Updated the NAS Config on the NAS Server with version " + str(nasVersionMessage), 0
