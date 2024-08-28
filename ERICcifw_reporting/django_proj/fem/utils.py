from urllib2 import urlopen
from json import loads
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()
from models import *
from cireports.models import *
from dmt.models import Sed, Cluster, DeploymentUtilities, DeploymentUtilitiesVersion, DeploymentUtilsToISOBuild
import cireports
import time
import subprocess
import re
import json
from django.core.management import call_command
from django.db import connection, transaction, IntegrityError
from cireports.common_modules.common_functions import *
import ast
from distutils.version import LooseVersion
import zipfile
import urllib
import httplib
import os, shutil
import base64
import urllib2
from os import listdir
import requests
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from dmt.utils import *

def readDataFromURL(url, femBase=None, depth=None, TTL=None):
    '''
    retrieve JSON info into a dict, checks first if url is cached.
    '''
    maxTTL = int(config.get("FEM", "maxTTL"))
    if TTL is None:
        TTL = int(config.get("FEM", "TTL"))
    if femBase is None:
        femBase = config.get("FEM", "femBase")
    if not url.startswith(femBase) and not url.startswith("http"):
        url = femBase + url
    url = url + "/api/json"
    if depth is not None:
        url = url + "?depth=" + str(depth)
    logger.debug("URL: " + url)

    # Replace any spaces in the view name with %20
    url = re.sub(r"\s+", '%20', url)

    timeNow = datetime.now()
    timeMinusTTL = datetime.now() - timedelta(seconds=maxTTL)
    #outOfDate=CacheTable.objects.filter(inserted__range!=(timeMinusTTL, timeNow))
    outOfDate=CacheTable.objects.exclude(inserted__range=(timeMinusTTL, timeNow))
    outOfDate.delete()
    #allEntries = CacheTable.objects.fetch(url=url)
    try:
        existing = CacheTable.objects.get(url=url)
        if (datetime.now() - existing.inserted) > timedelta (seconds = TTL):
            existing.delete()
            try:
                req = urlopen(url)
                res = req.read()
            except Exception as e:
                raise ValueError('url problem')
            urlInfo = CacheTable( url=url, data=res, inserted=datetime.now())
            urlInfo.save()
        else:
            res = existing.data

    except Exception as e:
        try:
            req = urlopen(url)
            res = req.read()
        except Exception as e:
            raise ValueError('url problem')
        urlInfo = CacheTable( url=url, data=res, inserted=datetime.now())
        try:
            urlInfo.save()
        except Exception as e:
            logger.error("Cache storage error URL: " + str(url))
    return loads(res)

def getJenkinsSlavesByLabel(label):
    '''
    get the list of slaves by label.
    '''
    data = readDataFromURL("/label/" + label)
    info = {}
    for node in data['nodes']:
        nodeData = readDataFromURL("/computer/" + node['nodeName'])
        info[node['nodeName']] = nodeData
    return info

def colorToBuildStatus(color):
    res = "unknown"
    if color == "blue":
        res = "success"
    elif color == "red":
        res = "failed"
    elif color == "aborted":
        res = "aborted"
    elif color == "yellow":
        res = "unstable"
    elif job["color"] == "disabled":
        res = "disabled"
    return res

def collectJobStatusInformation(maxBuildsPerJob=0):
    '''
    Collect information about configured jobs and store
    '''
    # Get the list of jobs
    try:
        data = readDataFromURL("/view/All/", depth=1)
    except Exception as e:
        logger.error("Problem reading from /view/All/ " )
        return
    if data is None:
        return
    #logger.debug(data)
    for job in data['jobs']:
        #logger.debug("JOB: " + job['url'])
        # do we have this job yet?
        jobObj, created = Job.objects.get_or_create(name=job['name'])
        nbuilds = 0
        for build in job['builds']:
            nbuilds = nbuilds + 1
            if nbuilds > maxBuildsPerJob:
                logger.warning("Disregarding older build data for " + job['name'])
                break
            buildObj, created = JobResult.objects.get_or_create(job=jobObj, buildId=build['number'])
            #logger.debug("\tbuild " + str(build['number']))
            if not created:
                #logger.debug("\tExisting build: " + str(build['number']))
                continue
            logger.debug("\tNew build: " + str(build['number']))
            try:
                buildInfo = readDataFromURL(build['url'])
            except Exception as e:
                logger.error("Problem reading url: " +str(build['url']))
                continue
            if buildInfo is None:
                continue
            buildObj.status = buildInfo['result']
            if buildInfo['result'] is None:
                logger.error("No build result for this job: " + str(buildInfo))
                continue
            logger.debug("Result: " + buildInfo['result'])
            if buildInfo['result'] == "SUCCESS":
                buildObj.passed = 1
            elif buildInfo['result'] == "FAILURE":
                buildObj.failed = 1
            elif buildInfo['result'] == "ABORTED":
                buildObj.aborted = 1
            elif buildInfo['result'] == "UNSTABLE":
                buildObj.unstable = 1
            buildObj.url = buildInfo['url']
            buildObj.duration = buildInfo['duration']
            buildObj.finished = datetime.fromtimestamp(buildInfo['timestamp'] / 1000)
            buildObj.finished_ts = buildInfo['timestamp']
            logger.debug("timestamp: " + str(buildInfo['timestamp']) + " ; datetime: " + str(buildObj.finished))
            buildObj.save()
            #for k in buildInfo.keys():
            #    logger.debug(k + " == " + str(buildInfo[k]))
    try:
        datav = readDataFromURL("", depth=0)
    except Exception as e:
        logger.error("Problem reading from root jenking api" )
        return
    for viewNameDict in datav['views']:
        viewName = viewNameDict['name']
        viewName = re.sub(r"\s+", '%20', viewName)
        if viewName is not None:
            logger.debug("looking for jobs with view " + viewName)
            # Get the view, and if it does not exist populdate it
            viewObj, created = View.objects.get_or_create(name=viewName)
            # retrieve the job names associated with this view and create the mappings
            logger.debug("Creating relevant job mappings@")
            jobInfo = readDataFromURL("/view/" + viewName + "/")
            for job in jobInfo['jobs']:
                try:
                    jobObj = Job.objects.get(name=job['name'])
                    exists = JobViewMapping.objects.filter(job=jobObj, view=viewObj).exists()
                    if not exists:
                        jvm = JobViewMapping(job=jobObj, view=viewObj)
                        jvm.save()
                        logger.debug("Mapped " + str(jvm))
                except:
                    # job has not been collected yet ...
                    continue

def prettyPrintJsonString(jsonString):
    data = json.loads(jsonString)
    return json.dumps(data, sort_keys=True, indent=4)

def determineOutcomeOfEventSuccessOrFailure(eventResult, eventSuccessMethod, eventFailureMethod):
     if eventResult == "SUCCESS":
            eventSuccessMethod()
     elif eventResult == "FAILURE":
            eventFailureMethod()

@transaction.atomic
def consumeEiffelArtifactModifiedMessage(message,debugFlag,latestVersion):
    '''
    This function consumes EiffelArtifactModified events and updates the code review, unit, acceptance and release
    test visualisations on a given package's page.
    '''

    if debugFlag == 1:
        logger.setLevel(logging.DEBUG)
    messageDict = json.loads(message)
    prettyFormat=prettyPrintJsonString(message)
    logger.debug("--> "+str(prettyFormat))
    '''Get the version, which will change over time, for use in extracting data below'''
    versionDict = messageDict["eiffelMessageVersions"]
    for value in versionDict:
        version = value
        if version.startswith(latestVersion):
            break

    artifactId = messageDict["eiffelMessageVersions"][version]["eventData"]["gav"]["artifactId"]
    artifactVersion = messageDict["eiffelMessageVersions"][version]["eventData"]["gav"]["version"]
    if "R" in artifactVersion:
        artifactVersion = convertRStateToVersion(artifactVersion)
    group = messageDict["eiffelMessageVersions"][version]["eventData"]["gav"]["groupId"]
    confidenceLevels = messageDict["eiffelMessageVersions"][version]["eventData"]["confidenceLevels"]
    eventDateTime= messageDict["eiffelMessageVersions"][version]["eventTime"]
    eventDate = eventDateTime.split("T", 1)[0]
    eventTime = eventDateTime.split("T", 1)[1].split(".", 1)[0]
    thisDateTime = str(eventDate) + " " + str(eventTime)
    finalEventDateTime = datetime.fromtimestamp(time.mktime(time.strptime(thisDateTime, "%Y-%m-%d %H:%M:%S")))
    autoDeliveryMail = eventType = eventResult = testwarePOM = TestResultReport = testware = hostProperties = m2type = kgbReady = cautionStatus = teAllureLogUrl = teTestWare= deployScript = sedVersion = mtUtilsVersion = deploymentUtilities = None
    skipAutoDeliver = False
    revertDeliveryOnFail = True
    try:
        testReport = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["testReportFile"]
    except Exception as e:
        testReport = None
    try:
        veLog = messageDict["eiffelMessageVersions"][version]["eventData"]["logReferences"]["velog"]["uri"]
    except:
        veLog = None
    try:
        tafExLog = messageDict["eiffelMessageVersions"][version]["eventData"]["logReferences"]["taflog"]["uri"]
    except:
        tafExLog = None

    for key, value in confidenceLevels.iteritems():
        if "COMPLETED" in key:
            try:
                TestResultReport = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["TestReportDirectory"]
                if TestResultReport == "None":
                    TestResultReport = None
            except Exception as e:
                logger.debug(str(e) + " parameter not defined, therefore testware run will not be reproduceable")
                TestResultReport = None
            try:
                testware = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["testware"]
                if testware == "None":
                    testware = None
            except Exception as e:
                logger.debug(str(e) + " parameter not defined, therefore testware run will not be reproduceable")
                testware = None
            try:
                testwarePOM = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["testwarePOM"]
                if testwarePOM == "None":
                    testwarePOM = None
            except Exception as e:
                logger.debug(str(e) + " parameter not defined, therefore testware run will not be reproduceable")
                testwarePOM = None
            try:
                hostProperties = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["hostProperties"]
                if hostProperties == "None":
                    hostProperties = None
            except Exception as e:
                logger.debug(str(e) + " parameter not defined, therefore testware run will not be reproduceable")
                hostProperties = None
            try:
                kgbReady = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["manualKGBreadyDetails"]
            except Exception as e:
                logger.debug(str(e) + " parameter not defined.")
                kgbReady = None
            try:
                cautionStatus = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["cautionStatusDetails"]
            except Exception as e:
                logger.debug(str(e) + " parameter not defined")
                cautionStatus = None
            try:
                teAllureLogUrl = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["teAllureLogUrl"]
                if teAllureLogUrl == "None":
                    teAllureLogUrl = None
            except Exception as e:
                logger.debug(str(e) + " parameter not defined, no info for teAllureLogUrl set to None")
                teAllureLogUrl = None
            try:
                teTestWare = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["teTestWare"]
                if teTestWare == "None":
                    teTestWare = None
            except Exception as e:
                logger.debug(str(e) + " parameter not defined, no info for teTestWare set to None")
                teTestWare = None
            try:
                autoDeliveryMailList = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["autoDeliveryMailList"]
                autoDeliveryMail = [autoDeliveryMailList]
            except:
                autoDeliveryMail = None
            try:
                revertDeliveryOnFailText = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["revertDeliveryOnFail"]
                if revertDeliveryOnFailText.lower() == 'false':
                    revertDeliveryOnFail = False
                else:
                    revertDeliveryOnFail = True
            except Exception as e:
                revertDeliveryOnFail = True
            try:
                skipAutoDeliverText = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["skipAutoDeliver"]
                if skipAutoDeliverText.lower() == 'true':
                    skipAutoDeliver = True
                else:
                    skipAutoDeliver = False
            except Exception as e:
                skipAutoDeliver = False
        try:
            deploymentUtilities = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["deploymentUtilities"]
            if deploymentUtilities == "None":
                deploymentUtilities = None
        except:
            logger.debug("Optional Parameter not defined, deploymentUtilities set to None")
            deploymentUtilities = None

        if deploymentUtilities == None:
            try:
                mtUtilsVersion = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["mtUtilsVersion"]
                if mtUtilsVersion == "None":
                    mtUtilsVersion = None
                elif not versionNumberCheck(mtUtilsVersion):
                    logger.error("mtUtilsVersion parameter does not contain a vaild version number, mtUtilsVersion is set to None")
                    mtUtilsVersion = None
            except Exception as e:
                logger.debug("mtUtilsVersion parameter not defined, no info for mtUtilsVersion set to None")
                mtUtilsVersion = None
            try:
                sedVersion = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["sedVersion"]
                if sedVersion == "None":
                    sedVersion = None
                elif not versionNumberCheck(sedVersion):
                    logger.error("sedVersion parameter does not contain a vaild version number, sedVersion is set to None")
                    sedVersion = None
            except Exception as e:
                logger.debug("sedVersion parameter not defined, no info for sedVersion set to None")
                sedVersion = None
            try:
                deployScript = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["deployScript"]
                if deployScript == "None":
                    deployScript = None
                elif not versionNumberCheck(deployScript):
                    logger.error("deployScript  parameter does not contain a vaild version number, deployScript is set to None")
                    deployScript = None
            except Exception as e:
                logger.debug("deployScript parameter not defined, no info for deployScript set to None")
                deployScript = None

        try:
            multipleArtifactList = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["artifactList"]
        except Exception as e:
            multipleArtifactList = None

        try:
            team = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["team"]
        except Exception as e:
            logger.debug(str(e) + " parameter not defined")
            team = None

        try:
            parentElement = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["ra"]
        except Exception as e:
            logger.debug(str(e) + " parameter not defined")
            parentElement = None

        eventType = key
        eventResult = value

    if eventType == "MULTI_KGB_TESTING_STARTED":
        try:
            gavList=multipleArtifactList.split("#")
            token = config.get('FEM', 'kgbFunctionalUserToken')
            auth_token = "Basic " + token
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", "Authorization": auth_token}
            developmentServer = ast.literal_eval(config.get("CIFWK", "testServer"))
            femBaseUrlTotalCount = FemKGBUrl.objects.filter().count()
            flow = getFlow(messageDict,version)
            inputEventIDsStr = getInputEventIDs(messageDict,version)

            if femBaseUrlTotalCount == 0:
                femBaseUrlTotalCount =1
        except Exception as e:
            logger.debug("issue with multiple update to start the job"+str(e))

        updateKGBsnapshotReport(gavList)
        for gav in gavList:
            skipSnapshotArtifact = False
            try:
                if gav != "":
                    artifactN,VersionN,groupN=gav.split("::")
                    if "-SNAPSHOT" in VersionN:
                        skipSnapshotArtifact = True
                    if skipSnapshotArtifact == False:
                        params = urllib.urlencode({
                            'group': groupN,
                            'artifact': artifactN,
                            'version': VersionN,
                            'inputIDs': inputEventIDsStr,
                            'team': team,
                            'ra': parentElement,
                            'flow': flow,
                            'delay': 0
                        })
                        for femBaseUrlCount in range(1, (femBaseUrlTotalCount+1)):
                            try:
                                femBaseUrlExists = FemKGBUrl.objects.filter(order=femBaseUrlCount).exists()
                                if developmentServer == 1 or not femBaseUrlExists:
                                    femBaseUrl = config.get("FEM", "femBaseUrl")
                                    kgbStarted = config.get("FEM", "kgbStarted")
                                    https = True
                                else:
                                    femBaseUrlObj = FemKGBUrl.objects.get(order=femBaseUrlCount)
                                    femBaseUrl = femBaseUrlObj.base
                                    kgbStarted = femBaseUrlObj.kgbStarted
                                    https = femBaseUrlObj.https
                                if https:
                                    conn = httplib.HTTPSConnection(femBaseUrl)
                                else:
                                    conn = httplib.HTTPConnection(femBaseUrl)
                                conn.request("POST", kgbStarted, params, headers)
                                connectionObj=conn.getresponse()
                                if connectionObj.status != 302 and connectionObj.status != 201 and connectionObj.status != 202:
                                    message = "KGB started job failed (Attempt "+str(femBaseUrlCount)+") HTTP return code:"+str(connectionObj.status)+":"+str(femBaseUrl)+str(kgbStarted)+"----"+str(groupN)+":"+str(artifactN)+":"+str(VersionN)
                                    sendFailMail(message)
                                    logger.error(message)
                                else:
                                    break
                            except Exception as e:
                                message = "KGB started job failed (Attempt "+str(femBaseUrlCount)+")"+str(e)+"--"+kgbStarted+"--"+str(groupN)+":"+str(artifactN)+":"+str(VersionN)
                                sendFailMail(message)
                                logger.error("Issue sending KGB started job" +str(e))
            except Exception as e:
                logger.debug("issue with multiple update to calculate the packages added for the start of the job "+str(e))

    elif eventType == "MULTI_KGB_TESTING_COMPLETED":
        try:
            gavList=multipleArtifactList.split("#")
            developmentServer = ast.literal_eval(config.get("CIFWK", "testServer"))
            femBaseUrlTotalCount = FemKGBUrl.objects.filter().count()
            if femBaseUrlTotalCount == 0:
                femBaseUrlTotalCount =1
        except:
            logger.debug("issue with multiple update to complete the job")

        flow = getFlow(messageDict,version)
        inputEventIDsStr = getInputEventIDs(messageDict,version)
        buildFailure = getBuildFailure(messageDict,version)

        deliveredList = []
        deliveryFault = False
        updateKGBsnapshotReport(gavList)
        for gav in gavList:
            skipSnapshotArtifact = False
            if gav != "":
                try:
                    artifactN,VersionN,groupN=gav.split("::")
                    if "-SNAPSHOT" in VersionN:
                        skipSnapshotArtifact = True
                    if skipSnapshotArtifact == False:
                        params = urllib.urlencode({
                            'group': groupN,
                            'artifact': artifactN,
                            'version': VersionN,
                            'TestReportDirectory': TestResultReport,
                            'testware': testware,
                            'teAllureLogUrl': teAllureLogUrl,
                            'teTestWare': teTestWare,
                            'testwarePOM': testwarePOM,
                            'hostProperties': hostProperties,
                            'result': eventResult,
                            'inputIDs': inputEventIDsStr,
                            'team': team,
                            'ra': parentElement,
                            'flow': flow,
                            'buildFailure': buildFailure,
                            'delay': 0
                        })
                        token = config.get('FEM', 'kgbFunctionalUserToken')
                        auth_token = "Basic " + token
                        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", "Authorization": auth_token}
                        for femBaseUrlCount in range(1, (femBaseUrlTotalCount+1)):
                            try:
                                femBaseUrlExists = FemKGBUrl.objects.filter(order=femBaseUrlCount).exists()
                                if developmentServer == 1 or not femBaseUrlExists:
                                    femBaseUrl = config.get("FEM", "femBaseUrl")
                                    kgbFinished = config.get("FEM", "kgbFinished")
                                    https = True
                                else:
                                    femBaseUrlObj = FemKGBUrl.objects.get(order=femBaseUrlCount)
                                    femBaseUrl = femBaseUrlObj.base
                                    kgbFinished = femBaseUrlObj.kgbFinished
                                    https = femBaseUrlObj.https
                                if https:
                                    conn = httplib.HTTPSConnection(femBaseUrl)
                                else:
                                    conn = httplib.HTTPConnection(femBaseUrl)
                                conn.request("POST", kgbFinished, params, headers)
                                connectionObj=conn.getresponse()
                                if connectionObj.status != 302 and connectionObj.status != 201 and connectionObj.status != 202:
                                    message = "KGB finished job failed (Attempt "+str(femBaseUrlCount)+") HTTP return code:"+str(connectionObj.status)+":"+str(femBaseUrl)+str(kgbFinished)+"----"+str(groupN)+":"+str(artifactN)+":"+str(VersionN)
                                    sendFailMail(message)
                                    logger.error(message)
                                else:
                                    break
                            except Exception as e:
                                message = "KGB finished job failed (Attempt "+str(femBaseUrlCount)+")"+str(e)+"----"+str(groupN)+":"+str(artifactN)+":"+str(VersionN)
                                sendFailMail(message)
                                logger.error("Issue sending KGB finished job" +str(e))
                except:
                    logger.debug("issue with multiple update to calculate the packages added for the start of the job")

        deliverySummary = "";
        if eventResult == 'SUCCESS':
            artifactSummary = ""
            for gav in gavList:
                if gav != "":

                    try:
                        artifactN,VersionN,groupN=gav.split("::")
                        if PackageRevision.objects.filter(package__name=artifactN,version=VersionN,m2type='rpm').exists():
                            m2type='rpm'
                        elif PackageRevision.objects.filter(package__name=artifactN,version=VersionN,m2type='pkg').exists():
                            m2type='pkg'
                        elif PackageRevision.objects.filter(package__name=artifactN,version=VersionN,m2type='zip').exists():
                            m2type='zip'
                        elif PackageRevision.objects.filter(package__name=artifactN,version=VersionN,m2type='jar').exists():
                            m2type='jar'
                        elif PackageRevision.objects.filter(package__name=artifactN,version=VersionN,m2type='tar').exists():
                            m2type='tar'
                        deliveredList,deliveryFault,deliverySummary,artifactSummary = autoDeliverOnKGB(artifactN,VersionN,m2type,revertDeliveryOnFail,deliveredList,deliveryFault,deliverySummary,artifactSummary)
                        if deliveryFault and revertDeliveryOnFail:
                            break
                    except Exception as e:
                        deliveryFault = True
        if deliverySummary != "" and autoDeliveryMail:
            sendAutoDeliveryMail(deliverySummary,autoDeliveryMail)
    elif eventType.startswith('BUILDLOG'):
        if ProductSetVersion.objects.filter(version=artifactVersion,productSetRelease__number=artifactId).exists():
            try:
                with transaction.atomic():
                    if ProductSetVersion.objects.filter(version=artifactVersion,productSetRelease__number=artifactId,productSetRelease__release__product__name='ENM').exists():
                        for key, value in confidenceLevels.iteritems():
                            if "STARTED" in key:
                                retrieveENMBuildData(messageDict,version,artifactId,dmt)
                            if "COMPLETED" in key:
                                retrieveENMBuildDataAfter(messageDict,version,artifactId,dmt)
            except IntegrityError as e:
                logger.error("Problem updating buildlog: "+str(e))
    elif eventType.startswith("CDB"):
        if ISObuild.objects.filter(version=artifactVersion, artifactId=artifactId, groupId=group).exists():
            if not "Rollback" in eventType and not "RFAStaging" in eventType:
                try:
                    with transaction.atomic():
                        updateISOStatus(artifactId,artifactVersion,group,eventType,finalEventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog,kgbReady,teAllureLogUrl,teTestWare,cautionStatus, sedVersion, deployScript, mtUtilsVersion, deploymentUtilities)
                except IntegrityError as e:
                    logger.error("Problem updating CDB status: "+str(e))
            try:
                installType = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["installType"]
                if installType == "None":
                    installType = None
            except Exception as e:
                logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
                installType = None
            if installType == 'rollback':
                try:
                    with transaction.atomic():
                        if ISObuild.objects.filter(version=artifactVersion, artifactId=artifactId, groupId=group).exists():
                            for key, value in confidenceLevels.iteritems():
                                if "STARTED" in key:
                                    retrieveENMBuildData(messageDict,version,artifactId,dmt)
                                if "COMPLETED" in key:
                                    retrieveENMBuildDataAfter(messageDict,version,artifactId,dmt)
                except IntegrityError as e:
                    logger.error("Problem updating buildlog for iso build: "+str(e))
        elif ProductSetVersion.objects.filter(version=artifactVersion,productSetRelease__number=artifactId).exists():
            if not "Rollback" in eventType and not "RFAStaging" in eventType:
                try:
                    with transaction.atomic():
                        flowContext = messageDict["eiffelMessageVersions"][version]["eventData"]["flowContext"]
                        updateProductSetStatus(artifactId,artifactVersion,group,eventType,finalEventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog,kgbReady,teAllureLogUrl,teTestWare,cautionStatus, sedVersion, deployScript, flowContext, mtUtilsVersion, deploymentUtilities)
                except IntegrityError as e:
                    logger.error("Problem updating CDB status: "+str(e))
            try:
                with transaction.atomic():
                    if ProductSetVersion.objects.filter(version=artifactVersion,productSetRelease__number=artifactId,productSetRelease__release__product__name='ENM').exists():
                        for key, value in confidenceLevels.iteritems():
                            if "STARTED" in key:
                                retrieveENMBuildData(messageDict,version,artifactId,dmt)
                            if "COMPLETED" in key:
                                retrieveENMBuildDataAfter(messageDict,version,artifactId,dmt)
            except IntegrityError as e:
                logger.error("Problem updating buildlog: "+str(e))
        else:
            logger.error("Problem updating CDB status: "+str(e))
    else:
        try:
            packageObj = Package.objects.get(name=artifactId)
            if PackageRevision.objects.filter(package__name=packageObj.name,version=artifactVersion,m2type='rpm').exists():
                m2type='rpm'
            elif PackageRevision.objects.filter(package__name=packageObj.name,version=artifactVersion,m2type='pkg').exists():
                m2type='pkg'
            elif PackageRevision.objects.filter(package__name=packageObj.name,version=artifactVersion,m2type='zip').exists():
                m2type='zip'
            elif PackageRevision.objects.filter(package__name=packageObj.name,version=artifactVersion,m2type='jar').exists():
                m2type='jar'
            elif PackageRevision.objects.filter(package__name=packageObj.name,version=artifactVersion,m2type='tar').exists():
                m2type='tar'
        except Exception as e:
            logger.error("Package doesn't exist: "+str(artifactId) +"--"+str(e))
            return 0
        try:
            with transaction.atomic():
                updatePackageStatus(packageObj,artifactVersion,group,eventType,finalEventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog,m2type,skipAutoDeliver,revertDeliveryOnFail,autoDeliveryMail,teAllureLogUrl,teTestWare,team,parentElement)
        except IntegrityError as e:
                logger.error("problem with CLUE update: " +str(packageObj) +"---"+str(artifactVersion)+"---"+str(group)+"---"+str(eventType)+"---"+str(eventResult)+"---"+str(e))

def retrieveENMBuildData(messageDict,version,artifactId,dmt):
    try:
        itemVersion = messageDict["eiffelMessageVersions"][version]["eventData"]["gav"]["version"]
        if itemVersion == "None":
            itemVersion = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        itemVersion = None
    try:
        confidenceLevel = messageDict["eiffelMessageVersions"][version]["eventData"]["confidenceLevels"]
        if confidenceLevel == "None":
            confidenceLevel = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        confidenceLevel = None
    try:
        clusterId = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["clusterId"]
        if clusterId == "None":
            clusterId = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        clusterId = None
    try:
        installType = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["installType"]
        if installType == "None":
            installType = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        installType = None
    try:
        buildURL = messageDict["eiffelMessageVersions"][version]["eventSource"]["url"]
        if buildURL == "None":
            buildURL = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        buildURL = None
    try:
        fromISO = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["fromISO"]
        if fromISO == "None":
            fromISO = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        fromISO = None
    try:
        testPhase = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["testPhase"]
        if testPhase == "None":
            testPhase = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        testPhase = None
    try:
        virtualAutoBuildlogClusters = VirtualAutoBuildlogClusters.objects.values('name').distinct()[::1]
        if str(clusterId) in str(virtualAutoBuildlogClusters):
            clusterName = clusterId
        else:
            clusterName = Cluster.objects.get(id=clusterId).name
    except Exception as e:
        logger.debug(str(e) + " unable to retrieve clusterName")
        clusterName = None
    if(installType != 'rollback'):
        requiredProdSetFields = "mediaArtifactVersion__version", "productSetVersion__drop__name", "mediaArtifactVersion__sed_build__version", "mediaArtifactVersion__deploy_script_version", "mediaArtifactVersion__drop__release__product__name"
        prodSetDetails = None
        mediaArtifactVersion = None
        dropName = None
        sedVersion = None
        deploymentTemplates = None
        litpVersion = None
        osDetails = None
        patchesVersion = None
        try:
            prodSetDetails = list(ProductSetVersionContent.objects.filter(productSetVersion__version=itemVersion,productSetVersion__productSetRelease__number=artifactId).only(requiredProdSetFields).values(*requiredProdSetFields))
            enmProductSet = config.get('DMT_AUTODEPLOY','enmProductName')
            litpProductSet = config.get('DMT_AUTODEPLOY','litpProductName')
            rhelMediaProductSet = config.get('DMT_AUTODEPLOY','rhelMediaProductName')
            rhelOsPatchSetProductSet = config.get('DMT_AUTODEPLOY','osPatchProductName')

            for iso in prodSetDetails:
                if enmProductSet == iso['mediaArtifactVersion__drop__release__product__name']:
                    mediaArtifactVersion = iso['mediaArtifactVersion__version']
                    dropName = iso['productSetVersion__drop__name']
                    sedVersion = iso['mediaArtifactVersion__sed_build__version']
                    deploymentTemplates = iso['mediaArtifactVersion__deploy_script_version']
                elif litpProductSet in iso['mediaArtifactVersion__drop__release__product__name']:
                    litpVersion = iso['mediaArtifactVersion__version']
                elif rhelMediaProductSet in iso['mediaArtifactVersion__drop__release__product__name']:
                    osDetails = iso['mediaArtifactVersion__version']
                elif rhelOsPatchSetProductSet in iso['mediaArtifactVersion__drop__release__product__name']:
                    patchesVersion = iso['mediaArtifactVersion__version']
        except Exception as e:
            logger.debug(str(e) + " unable to retrieve product set items")

    else:
        logger.info("Rollback in progress...")
        prodSetDetails = None
        enmISO = None
        mediaArtifactVersion = itemVersion
        try:
            enmISO = ISObuild.objects.get(version=itemVersion, artifactId=artifactId)
        except Exception as e:
            logger.debug(str(e) + " unable to retrieve enmISO")
        dropName = str(enmISO.drop.name)
        sedVersion = None
        deploymentTemplates = None
        litpVersion = None
        osDetails = None
        patchesVersion = None
        itemVersion = ''

    #variables in this call are representing clusterId, clusterName, osDetails,  litpVersion, mediaArtifact, fromISO, patches, dropName, groupName, sedVersion, deploymentTemplates, tafVersion, masterBaseline, descriptionDetails, success, upgradePerformancePercent, productset_id/isoversion(itemVersion), deliveryGroup, rfaStagingResult, sl1, sl2, allure, availability, buildURL, installType, deploytime, comment, slot, upgradeTestingStatus, rfaPercent, shortLoopURL, upgradeFlagData, testPhase, confidenceLevel
    if clusterName != None:
        dmt.utils.updateDeploymentBaseline(clusterId, clusterName, osDetails, litpVersion, mediaArtifactVersion, fromISO, patchesVersion, dropName, '', sedVersion, deploymentTemplates, 'tafVersionNone', '0', 'Just started', '0', '', itemVersion,'', '', '', '', '', 'BUSY', buildURL, installType, 'In Progress', '', 0,'','','',0, testPhase, confidenceLevel)

def retrieveENMBuildDataAfter(messageDict,version,artifactId,dmt):
    try:
        clusterId = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["clusterId"]
        if clusterId == "None":
            clusterId = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        clusterId = None
    try:
        teAllureLogUrl = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["teAllureLogUrl"]
        if teAllureLogUrl == "None":
            teAllureLogUrl = ''
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        teAllureLogUrl = ''
    try:
        testPhase = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["testPhase"]
        if testPhase == "None":
            testPhase = ''
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        testPhase = ''
    try:
        confidenceLevel = messageDict["eiffelMessageVersions"][version]["eventData"]["confidenceLevels"]
        if confidenceLevel == "None":
            confidenceLevel = None
    except Exception as e:
        logger.debug(str(e) + " parameter not defined therefore testware run will not be reproduceable")
        confidenceLevel = None
    try:
        virtualAutoBuildlogClusters = VirtualAutoBuildlogClusters.objects.values('name').distinct()[::1]
        if str(clusterId) in str(virtualAutoBuildlogClusters):
            clusterName = clusterId
        else:
            clusterName = Cluster.objects.get(id=clusterId).name
    except Exception as e:
        logger.debug(str(e) + " unable to retrieve clusterName")
        clusterName = None
    if clusterName != None:
        dmt.utils.updateDeploymentBaselineAfter(clusterId, clusterName,teAllureLogUrl, confidenceLevel, testPhase)

def updatePackageStatus(packageObj,artifactVersion,group,eventType,eventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog,m2type,skipAutoDeliver,revertDeliveryOnFail,autoDeliveryMail,teAllureLogUrl,teTestWare,team,parentElement):
    statusEventTypeMap={'CODE_REVIEW_STARTED':'in_progress','CODE_REVIEW_COMPLETED':'passed','UNIT_TESTING_STARTED':'in_progress','UNIT_TESTING_COMPLETED':'passed','ACCEPTANCE_TESTING_STARTED':'in_progress','ACCEPTANCE_TESTING_COMPLETED':'passed','RELEASE_BUILD_STARTED':'in_progress','RELEASE_BUILD_COMPLETED':'passed','KGB_TESTING_STARTED':'in_progress','KGB_TESTING_COMPLETED':'passed','CDB_TESTING_STARTED':'in_progress','CDB_TESTING_COMPLETED':'passed'}
    if eventResult == "SUCCESS":
        try:
            status =  statusEventTypeMap[eventType]
        except:
            logger.error("Unknown event" +str(eventType))
            return 1
    else:
        status = 'failed'
    if eventType == 'KGB_TESTING_STARTED':
        updateCLversion(packageObj,artifactVersion,eventType,status,'kgb',veLog,team,parentElement,group,m2type)
    elif eventType == 'CDB_TESTING_STARTED' or eventType == 'CDB_TESTING_COMPLETED':
        updateCLversion(packageObj,artifactVersion,eventType,status,'cdb',None,None,None,group,m2type)
    elif eventType == 'KGB_TESTING_COMPLETED':
        updateTestReport(packageObj,artifactVersion,'kgb',testReport,TestResultReport,testware,None,testwarePOM,hostProperties,tafExLog,m2type,teAllureLogUrl,teTestWare)
        updateCLversion(packageObj,artifactVersion,eventType,status,'kgb',veLog,team,parentElement,group,m2type)
    else:
        updateCL(packageObj,eventType,status,eventDateTime)

    if (eventType == 'KGB_TESTING_COMPLETED' or eventType == "MULTI_KGB_TESTING_COMPLETED") and eventResult == "SUCCESS" and teTestWare != None:
        testwareList = []
        try:
            decodedJson = json.loads(teTestWare)
            for item in decodedJson:
                for key,value in item.iteritems():
                    if str(key) == "artifactId":
                        teArtifactId=value
                    if str(key) == "version":
                        teVersion=value
                testwareList.extend([str(teArtifactId) + "-VER-" + str(teVersion)])
        except ValueError:
            logger.debug("teTestWare does not have valid JSON")
        packageMapNew = None
        for tw in testwareList:
            testwarename,testwareversion=tw.split("-VER-")
            try:
                testWareObj=TestwareRevision.objects.get(testware_artifact__name=testwarename,version=testwareversion)
                testWareObj.cdb_status = 1
                testWareObj.save()
            except Exception as e:
                logger.error("Error "+ str(e))
    if (eventType == 'KGB_TESTING_COMPLETED' or eventType == "MULTI_KGB_TESTING_COMPLETED") and eventResult == "SUCCESS" and testware != None:
        try:
            testwareList=testware.split("-BREAK-")
        except:
            testwareList=testware
        packageMapNew = None
        for tw in testwareList:
            try:
                testwarename,testwareversion=tw.split("-VER-")
                testWareObj=TestwareRevision.objects.get(testware_artifact__name=testwarename,version=testwareversion)
                testWareObj.cdb_status = 1
                testWareObj.save()
            except Exception as e:
                logger.error("Error "+ str(e))
    if (eventType == 'KGB_TESTING_COMPLETED' ) and eventResult == "SUCCESS" :
        if PackageRevision.objects.filter(package__name=packageObj.name,version=artifactVersion,m2type=m2type,autodeliver=1).exists():
            if not skipAutoDeliver:
                deliverySummary = ""
                artifactSummary = ""
                logger.debug("Attempting auto delivery")
                deliveredList = []
                deliveryFault = False
                dontCare,dontCare,deliverySummary,dontCare = autoDeliverOnKGB(packageObj.name,artifactVersion,m2type,revertDeliveryOnFail,deliveredList,deliveryFault,deliverySummary,artifactSummary)
                if deliverySummary != "" and autoDeliveryMail:
                    sendAutoDeliveryMail(deliverySummary,autoDeliveryMail)



def updateTestReport(packageObj,artifactVersion,phase,testReport,TestResultReport,testware,isoObj,testwarePOM,hostProperties,tafExLog,m2type,teAllureLogUrl,teTestWare):
    try:
        if TestResultReport !=None or tafExLog !=None or teAllureLogUrl !=None:
            storeTestReport("kgb",packageObj,artifactVersion,TestResultReport,testware,None,testwarePOM,hostProperties,None,tafExLog,None,m2type,teAllureLogUrl,teTestWare,None)
        else:
            call_command('update_test_report', package=packageObj,ver=artifactVersion,packagemap=testware,phase=phase,testReport=testReport,testResultReport=TestResultReport)
    except Exception as e:
        logger.error("Could not update test report: package="+str(packageObj)+",ver="+str(artifactVersion)+",packagemap="+str(testware)+",phase="+str(phase)+",testReport="+str(testReport)+",testResultReport="+str(TestResultReport)  + str(e))

def storeTestReport(testPhase,packageObj,artifactVersion,testResultReport,testware,isoObj,testwarePOM,hostProperties,productSetVersionObj,tafExLog,kgbReady,m2type,teAllureLogUrl,teTestWare,cautionStatus):
    testwarePOMLocationDB = None
    testwareHostPropertiesLocation = None
    try:
        ts=datetime.now().isoformat()
        filePath = config.get('REPORT', 'filePath')
        if testPhase=="cdb":
            directory ="cdb_"+str(ts)

        else:
            directory ="kgb_"+str(ts)
        fileDirectory = directory
        storePath = os.path.join(filePath,directory)
        tmpStoreFile = os.path.join('/tmp',str(ts))
        if tafExLog == None and teAllureLogUrl == None:
            if testResultReport != None:
                urllib.urlretrieve(testResultReport, tmpStoreFile)
            else:
                try:
                    if kgbReady:
                       url = urllib.urlretrieve(str(kgbReady), tmpStoreFile)
                    else:
                       url = urllib.urlretrieve(str(cautionStatus), tmpStoreFile)
                except Exception as e:
                    logger.error("Error when using url retrieve: " + str(e))
                    url = None

            try:
                file = zipfile.ZipFile(tmpStoreFile, "r")
            except Exception as e:
                logger.error("Error when unzipping the File: " + str(e))
                file = None

            fileList=file.namelist()
            file.extractall(storePath)
            os.remove(tmpStoreFile)
            try:
                fileListSplit=fileList[0].split('/')
                if kgbReady or cautionStatus:
                    directory=str(directory)+"/"+str(fileListSplit[0])+"/"+str(fileListSplit[1])
                elif len(fileListSplit) >0:
                    directory=str(directory)+"/"+str(fileListSplit[0])
            except Exception as e:
                directory=directory
        elif teAllureLogUrl != None:
            directory=teAllureLogUrl
        else:
            directory=tafExLog
        try:
            files = []
            if testwarePOM != None and testwarePOM != "None":
                files.append(testwarePOM)
            else:
                testwarePOMLocationDB = None
            if hostProperties != None and hostProperties != "None":
                files.append(hostProperties)
            else:
                testwareHostPropertiesLocation = None
            for file in files:
                    try:
                        fileName = os.path.basename(file)
                        if not os.path.isdir(storePath):
                            os.makedirs(storePath)
                        fileLocation = storePath+"/"+fileName
                        urllib.urlretrieve(file,fileLocation)
                        fileDBLocation = fileDirectory+"/"+fileName
                        if "pom" in file:
                            testwarePOMLocationDB = fileDBLocation
                        if "host" in file:
                            testwareHostPropertiesLocation = fileDBLocation
                    except Exception as e:
                       logger.error("ERROR: "+str(e))
        except Exception as e:
            logger.error("ERROR: "+str(e))

        try:
            testResultObj=TestResults.objects.create(failed=0,passed=0,total=0,tag=0,testdate=ts,phase=testPhase,test_report_directory=directory,testware_pom_directory=testwarePOMLocationDB,host_properties_file=testwareHostPropertiesLocation)
        except Exception as e:
            logger.error("ERROR: "+str(e))

        if testware != None or teTestWare != None:
            testwareList = []
            if testware != None:
                try:
                    testwareList=testware.split("-BREAK-")
                except:
                    testwareList=testware
            if teTestWare != None:
                try:
                    decodedJson = json.loads(teTestWare)
                    for item in decodedJson:
                        for key,value in item.iteritems():
                            if str(key) == "artifactId":
                                teArtifactId=value
                            if str(key) == "version":
                                teVersion=value
                        testwareList.extend([str(teArtifactId) + "-VER-" + str(teVersion)])
                except ValueError:
                    logger.debug("teTestWare does not have valid JSON")
            packageMapNew = None
            for tw in testwareList:
                try:
                    testwarename,testwareversion=tw.split("-VER-")
                    testWareObj=TestwareRevision.objects.get(testware_artifact__name=testwarename,version=testwareversion)
                    if not productSetVersionObj == None:
                        testResultiMapObj=PSTestResultsToTestwareMap.objects.create(testware_revision_id=testWareObj.id,product_set_version_id=productSetVersionObj.id,testware_artifact_id=testWareObj.testware_artifact.id,testware_run_id=testResultObj.id)
                    elif testPhase=="cdb":
                        testResultiMapObj=ISOTestResultsToTestwareMap.objects.create(testware_revision_id=testWareObj.id,isobuild_id=isoObj.id,testware_artifact_id=testWareObj.testware_artifact.id,testware_run_id=testResultObj.id)
                    else:
                        if m2type:
                            pkgObj=PackageRevision.objects.get(package__name=packageObj.name,version=artifactVersion,m2type=m2type)
                        else:
                            pkgObj=PackageRevision.objects.get(package__name=packageObj.name,version=artifactVersion)
                        try:
                            if TestsInProgress.objects.filter(package_revision=pkgObj).exists():
                                testObj = TestsInProgress.objects.get(package_revision=pkgObj)
                                test2VisEngineObj,created=TestResultsToVisEngineLinkMap.objects.get_or_create(testware_run=testResultObj)
                                test2VisEngineObj.veLog=testObj.veLog
                                test2VisEngineObj.save()
                        except Exception as e:
                            logger.error("issue with VE link"+str(e))
                        testResultiMapObj=TestResultsToTestwareMap(testware_revision_id=testWareObj.id,package_revision_id=pkgObj.id,testware_artifact_id=testWareObj.testware_artifact.id,package_id=pkgObj.package.id,testware_run_id=testResultObj.id)
                        testResultiMapObj.save()
                except Exception as e:
                    logger.error("Error: " +str(e))
        return testResultObj.id

    except Exception as e:
        return None
def updateCLversion(packageObj,artifactVersion,eventType,status,phase,veLog,team,parentElement,group,m2type):
    try:
        call_command('update_test_status', package=packageObj,ver=artifactVersion,phase=phase,state=status,veLog=veLog,team=team,parentElement=parentElement,group=group,type=m2type)
    except Exception as e:
        logger.error("issue with CLUE update:" +str(group) +str(e))

def updateCL(packageObj,eventType,status,eventDateTime):
    '''
    Update confidence level of artifact in Clue and cluetrend tables
    '''
    eventTypeMap={'CODE_REVIEW_STARTED':'codeReview','CODE_REVIEW_COMPLETED':'codeReview','UNIT_TESTING_STARTED':'unit','UNIT_TESTING_COMPLETED':'unit','ACCEPTANCE_TESTING_STARTED':'acceptance','ACCEPTANCE_TESTING_COMPLETED':'acceptance','RELEASE_BUILD_STARTED':'release','RELEASE_BUILD_COMPLETED':'release'}
    eventTrendTimeTypeMap={'CODE_REVIEW_STARTED':'codeReviewTimeStarted','CODE_REVIEW_COMPLETED':'codeReviewTimeFinished','UNIT_TESTING_STARTED':'unitTimeStarted','UNIT_TESTING_COMPLETED':'unitTimeFinished','ACCEPTANCE_TESTING_STARTED':'acceptanceTimeStarted','ACCEPTANCE_TESTING_COMPLETED':'acceptanceTimeFinished','RELEASE_BUILD_STARTED':'releaseTimeStarted','RELEASE_BUILD_COMPLETED':'releaseTimeFinished'}
    phase = eventTypeMap[eventType]
    trendTime = eventTrendTimeTypeMap[eventType]
    now = eventDateTime
    if phase == 'codeReview' and eventType=='CODE_REVIEW_STARTED':
        clueObj,created=Clue.objects.get_or_create(package=packageObj)
        if not created:
            clueObj.codeReview=status
            clueObj.codeReviewTime=now
            clueObj.unit='not_started'
            clueObj.unitTime=None
            clueObj.acceptance='not_started'
            clueObj.acceptanceTime=None
            clueObj.release='not_started'
            clueObj.releaseTime=None
            clueObj.save()
        else:
            clueObj.codeReview=status
            clueObj.codeReviewTime=now
            clueObj.save()

        ClueTrend.objects.create(package=packageObj,codeReview=status,codeReviewTimeStarted=now,lastUpdate=now)

    elif phase == 'unit' and eventType=='UNIT_TESTING_STARTED':
        clueObj,created=Clue.objects.get_or_create(package=packageObj)
        if not created:
            clueObj.unit=status
            clueObj.unitTime=now
            clueObj.acceptance='not_started'
            clueObj.acceptanceTime=None
            clueObj.release='not_started'
            clueObj.releaseTime=None
            clueObj.save()
        else:
            clueObj.unit=status
            clueObj.unitTime=now
            clueObj.save()

        ClueTrend.objects.create(package=packageObj,codeReview=status,codeReviewTimeStarted=now,lastUpdate=now)

    else:
        phaseTime=phase+"Time"
        trendPhaseTime=eventTrendTimeTypeMap[eventType]
        #entry should exist at this point but id someone didn't run CLUE at code review it won't
        clueObj,created=Clue.objects.get_or_create(package=packageObj)
        if created:
            clueObj.codeReviewTime=now
            clueObj.save()
        Clue.objects.filter(package=packageObj).update(**{phase:status,phaseTime:now})
        #Clue codeReviewTime must = clueTrend codeReviewTimeStarted or codeReviewTimeFinished, if not create entry
        if ClueTrend.objects.filter(package=packageObj,codeReviewTimeStarted=clueObj.codeReviewTime).exists():
            ClueTrend.objects.filter(package=packageObj,codeReviewTimeStarted=clueObj.codeReviewTime).update(**{phase:status,trendPhaseTime:now,'lastUpdate':now})
        elif ClueTrend.objects.filter(package=packageObj,codeReviewTimeFinished=clueObj.codeReviewTime).exists():
            ClueTrend.objects.filter(package=packageObj,codeReviewTimeFinished=clueObj.codeReviewTime).update(**{phase:status,trendPhaseTime:now,'lastUpdate':now})
        else:
            ClueTrend.objects.create(package=packageObj,codeReviewTimeStarted=now,lastUpdate=now)

def updateISOStatus(artifactId,artifactVersion,group,eventType,eventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog,kgbReady,teAllureLogUrl,teTestWare,cautionStatus, sedVersion=None, deployScript=None, mtUtilsVersion=None, deploymentUtilities=None):
    '''
    Update status of ISO under test
    '''
    timeF = None
    isoObj = allPreviousISO = previousISO = None
    try:
        isoObj = ISObuild.objects.get(version=artifactVersion, artifactId=artifactId, groupId=group)
    except Exception as e:
        logger.error("Issue getting Media Artifact " + str(artifactId) + "-" + str(artifactVersion) + "-" + str(group) + ", Error: " + str(e))
        return 0
    if deploymentUtilities != None:
        try:
           deploymentUtilitiesHandler(deploymentUtilities,isoObj)
        except Exception as error:
            logger.error("There was an issue adding deployment Utilities: " + str(deploymentUtilities) + " to the CI DB, error: " +str(error))
    else:
        try:
            if sedVersion != None:
                sedObj=Sed.objects.get(version=sedVersion)
                isoObj.sed_build = sedObj
            if deployScript != None:
                isoObj.deploy_script_version = deployScript
            if mtUtilsVersion != None:
                isoObj.mt_utils_version = mtUtilsVersion
        except Exception as e:
            logger.error("Issue adding the sedVersion " + str(sedVersion) + ", deployScript " + str(deployScript) + " and the Utils package version " + str(mtUtilsVersion) + " to the Media Artifact " + str(artifactId) + "-" + str(artifactVersion) + "-" + str(group) + ", Error: " + str(e))
    try:
        allPreviousISO=list(ISObuild.objects.filter(drop=isoObj.drop, mediaArtifact__category=isoObj.mediaArtifact.category).exclude(id__gte=isoObj.id))
        allPreviousISO.sort(key=lambda ver:LooseVersion(ver.version), reverse=True)
        if allPreviousISO:
            for tmpIso in allPreviousISO:
                try:
                    if tmpIso.overall_status == States.objects.get(state='passed'):
                        tmpState=tmpIso.overall_status
                        previousISO=tmpIso
                        break
                    else:
                        previousISO=None
                except:
                    previousISO=None
        else:
            previousISO=None

    except Exception as e:
        previousISO=None
    isoPackages=ISObuildMapping.objects.filter(iso=isoObj.id)
    dontCare,type,action=eventType.split("_")
    updateTimeF=""
    updateTimeS=""
    #jenkins states: [SUCCESS, UNSTABLE, FAILURE, NOT_BUILT, ABORTED, NOT_SET]
    if "KGB-Ready" in eventType:
        updateStatus="passed_manual"
        updateTimeF=eventDateTime
    elif "Caution" in eventType:
        updateStatus="caution"
        updateTimeF=eventDateTime
    elif action=="STARTED" and eventResult =="SUCCESS":
        updateStatus="in_progress"
        updateTimeS=eventDateTime
    elif action=="COMPLETED" and eventResult =="SUCCESS":
        updateStatus="passed"
        updateTimeF=eventDateTime
    elif eventResult =="UNSTABLE" or eventResult =="ABORTED":
        updateStatus="failed"
        updateTimeF=eventDateTime
    else:
        updateStatus="failed"
        updateTimeF=eventDateTime
    try:
        typObj=CDBTypes.objects.get(name=type)
    except:
        logger.error("Invalid CDB type")
        return 0
    currentStatusUni= isoObj.current_status
    if currentStatusUni == None or  currentStatusUni == "":
        if updateStatus == "passed_manual" or updateStatus == "caution":
            timeS=None
            timeF=updateTimeF
            testReport=storeTestReport('cdb',None,None,TestResultReport,testware,isoObj,testwarePOM,hostProperties,None,tafExLog,kgbReady,None,teAllureLogUrl,teTestWare,cautionStatus)
            newCurrentStatus={typObj.id:str(updateStatus)+"#"+str(timeS)+"#"+str(timeF)+"#"+str(testReport)+"#"+str(veLog)}
        else:
            newCurrentStatus={typObj.id:str(updateStatus)+"#"+str(updateTimeS)+"#"+str(updateTimeF)+"#None#"+str(veLog)}
        isoObj.current_status=newCurrentStatus
        isoObj.save()
    else:
        currentStatus = ast.literal_eval(currentStatusUni)
        try:
            status,timeS,timeF,testReport,veLogStored=currentStatus[typObj.id].split("#")
        except Exception as e:
            timeS=""
            veLogStored=None
        if veLog == None or veLog == " "  or veLog == "":
            veLog = veLogStored
        if updateStatus == "in_progress":
            timeS=updateTimeS
            timeF=""
        elif updateStatus == "passed" or updateStatus == "failed":
            timeF=updateTimeF
        elif updateStatus == "passed_manual" or updateStatus == "caution":
            timeF=updateTimeF


        testReport=storeTestReport('cdb',None,None,TestResultReport,testware,isoObj,testwarePOM,hostProperties,None,tafExLog,kgbReady,None,teAllureLogUrl,teTestWare,cautionStatus)
        currentStatus[typObj.id]=str(updateStatus)+"#"+str(timeS)+"#"+str(timeF)+"#"+str(testReport)+"#"+str(veLog)
        newCurrentStatus=currentStatus
        isoObj.current_status=newCurrentStatus
        isoObj.save()
    updateCDBStatus()
    if isoPackages:
        updateOverallStatus(isoPackages,previousISO)
    else:
        updateOverallStatus(isoPackages,previousISO, isoObj)

def updateProductSetStatus(artifactId,artifactVersion,group,eventType,eventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog,kgbReady,teAllureLogUrl,teTestWare,cautionStatus, sedVersion, deployScript, flowContext, mtUtilsVersion, deploymentUtilities):
    '''
    Update status of ISO under test
    '''
    timeF = None
    isoObj = allPreviousISO = previousISO = None
    try:
        productSetObj = ProductSetVersion.objects.get(version=artifactVersion,productSetRelease__number=artifactId)
    except Exception as e:
        logger.error("Product Set Version" + str(artifactId) + ":"+str(artifactVersion)+" Not Found In The Database For This Release" + str(e))
        return 0
    try:
        allPreviousPS=list(ProductSetVersion.objects.filter(productSetRelease=productSetObj.productSetRelease).exclude(id__gte=productSetObj.id))
        allPreviousPS.sort(key=lambda ver:LooseVersion(ver.version), reverse=True)
        if allPreviousPS:
            for tmpPS in allPreviousPS:
                try:
                    if tmpPS.status == States.objects.get(state='passed'):
                        previousPS=tmpPS
                        break
                    else:
                        previousPS=None
                except:
                    previousPS=None
        else:
            previousPS=None

    except Exception as e:
        previousPS=None
    productSetContents=ProductSetVersionContent.objects.filter(productSetVersion=productSetObj.id)
    dontCare,type,action=eventType.split("_")
    updateTimeF=""
    updateTimeS=""
    #jenkins states: [SUCCESS, UNSTABLE, FAILURE, NOT_BUILT, ABORTED, NOT_SET]
    if "KGB-Ready" in eventType:
        updateStatus="passed_manual"
        updateTimeF=eventDateTime
    elif "Caution" in eventType:
        updateStatus="caution"
        updateTimeF=eventDateTime
    elif action=="STARTED" and eventResult =="SUCCESS":
        updateStatus="in_progress"
        updateTimeS=eventDateTime
    elif action=="COMPLETED" and eventResult =="SUCCESS":
        updateStatus="passed"
        updateTimeF=eventDateTime
    elif eventResult =="UNSTABLE" or eventResult =="ABORTED":
        updateStatus="failed"
        updateTimeF=eventDateTime
    else:
        updateStatus="failed"
        updateTimeF=eventDateTime
    try:
        typObj=CDBTypes.objects.get(name=type)
    except:
        logger.error("Invalid CDB type")
        return 0

    currentStatusUni = productSetObj.current_status
    if currentStatusUni == None or  currentStatusUni == "":
        if updateStatus == "passed_manual" or updateStatus == "caution":
            timeS = None
            timeF=updateTimeF
            testReport=storeTestReport('cdb',None,None,TestResultReport,testware,isoObj,testwarePOM,hostProperties,None,tafExLog,kgbReady,None,teAllureLogUrl,teTestWare,cautionStatus)
            newCurrentStatus={typObj.id:str(updateStatus)+"#"+str(timeS)+"#"+str(timeF)+"#"+str(testReport)+"#"+str(veLog)}
        else:
            newCurrentStatus={typObj.id:str(updateStatus)+"#"+str(updateTimeS)+"#"+str(updateTimeF)+"#None#"+str(veLog)}
        productSetObj.current_status=newCurrentStatus
        productSetObj.save()
    else:
        currentStatus = ast.literal_eval(currentStatusUni)
        try:
            status,timeS,timeF,testReport,veLogStored=currentStatus[typObj.id].split("#")
        except:
            timeS=""
            veLogStored=None
        if veLog == None or veLog == " "  or veLog == "":
            veLog = veLogStored

        if updateStatus == "in_progress":
            timeS=updateTimeS
            timeF=""
        elif  updateStatus == "passed" or  updateStatus == "failed":
            timeF=updateTimeF
        elif  updateStatus == "passed_manual" or updateStatus == "caution":
            timeF=updateTimeF

        testReport=storeTestReport('cdb',None,None,TestResultReport,testware,isoObj,testwarePOM,hostProperties,productSetObj,tafExLog,kgbReady,None,teAllureLogUrl,teTestWare,cautionStatus)

        configurationFound = False
        if updateStatus == "failed" or updateStatus == "in_progress":
            configurationFound = updateOverallStatusBasedOnConfiguration(flowContext,type,configurationFound)

        newCurrentStatus=currentStatus
        currentStatus[typObj.id]=str(updateStatus)+"#"+str(timeS)+"#"+str(timeF)+"#"+str(testReport)+"#"+str(veLog)
        productSetObj.current_status=newCurrentStatus
        productSetObj.save()
    if deploymentUtilities != None:
        try:
           deploymentUtilitiesHandler(deploymentUtilities,productSetObj)
        except Exception as error:
            logger.error("There was an issue adding deployment Utilities: " + str(deploymentUtilities) + " to the CI DB, error: " +str(error))
    updateProductSetCDBStatus(testReport)
    updateProductSetOverallStatus(productSetContents,previousPS,newCurrentStatus,productSetObj.id,group,eventType,eventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog, kgbReady,teAllureLogUrl,teTestWare,cautionStatus, sedVersion, deployScript, mtUtilsVersion, deploymentUtilities)

def updateOverallStatusBasedOnConfiguration(flowContext,type,configurationFound):
    '''
    The updateOverallStatusBasedOnConfiguration checks if a ProductSet Overall Status Configuration is Set, if so then the configuration will be used to report overall status on ProductSetVersion
    '''
    if flowContext != None and flowContext != "":
        product,release,drop = flowContext.split("_")
        try:
            productDropCDBFailureCheck = ProductDropToCDBTypeMap.objects.get(product__name=product, drop__release__name=release, drop__name=drop, type__name=type)
            if productDropCDBFailureCheck.enabled == True and productDropCDBFailureCheck.overallStatusFailure == True:
                 return True
        except:
            return False

def updateOverallStatus(isoPackages,previousISO, isoObj=None):
    passedManual = ""
    currentPackages=[]
    for pkg in isoPackages:
        currentPackages.append(str(pkg.package_revision.id).replace("L",""))

    if isoObj:
        isoId = isoObj.id
    else:
        isoId = isoPackages[0].iso_id
        isoObj = ISObuild.objects.get(id=isoId)

    currentStatus = ast.literal_eval(str(isoObj.current_status))
    stateInProgress=False
    stateFailed=False
    atLeastOnePassed=False
    passedManual=False
    caution=False
    for type in currentStatus:
        '''
        if currentStatus[type] == 'in_progress':
            stateInProgress=True
        if currentStatus[type] == 'failed':
            stateFailed=True
        if currentStatus[type] == 'passed':
            atLeastOnePassed=True
        '''
        if 'in_progress' in currentStatus[type]:
            stateInProgress=True
        if 'failed' in currentStatus[type]:
            stateFailed=True
        if 'passed' in currentStatus[type]:
            atLeastOnePassed=True
        if 'passed_manual' in currentStatus[type]:
            passedManual=True
        if 'caution' in currentStatus[type]:
            caution=True


    #hierarchy of overall status logic
    #anything failed -- new pkgs = failed
    #anything failed -- previous pkgs = warning unless if previous state= warning of passed, else =failed
    #anything in prgress -- overall state is in_progress


    if caution==True:
        overallStatusNew='caution'
    elif passedManual==True:
       overallStatusNew='passed_manual'
    elif stateFailed==True:
        overallStatusNew='failed'
    elif stateInProgress==True:
        overallStatusNew='in_progress'
    elif  stateFailed==False and atLeastOnePassed==True:
        overallStatusNew='passed'
    else:
        overallStatusNew='failed'

    currentPackages=[]
    for pkg in isoPackages:
        currentPackages.append(str(pkg.package_revision.id).replace("L",""))

    if overallStatusNew=='in_progress' or overallStatusNew=='passed':
        for packageToUpdate in currentPackages:
            updateObj=ISObuildMapping.objects.get(iso_id=isoId,package_revision_id=packageToUpdate)
            updateObj.overall_status=States.objects.get(state=overallStatusNew)
            updateObj.save()
    elif overallStatusNew=='passed_manual' or overallStatusNew=='caution':
        for packageToUpdate in currentPackages:
            updateObj=ISObuildMapping.objects.get(iso_id=isoId,package_revision_id=packageToUpdate)
            updateObj.overall_status=States.objects.get(state=overallStatusNew)
            updateObj.save()
    elif overallStatusNew=='failed' or overallStatusNew=='warning':
        try:
            oldPackages=[]
            oldIsoPackages=ISObuildMapping.objects.filter(iso=previousISO.id)
            for oldPkg in oldIsoPackages:
                oldPackages.append(str(oldPkg.package_revision.id).replace("L",""))
            oldSet=set(oldPackages)
            newSet=set(currentPackages)
            newToBuild=newSet-oldSet
            commonOldAndNew=newSet&oldSet
            for packageToUpdate in newToBuild:
                updateObj=ISObuildMapping.objects.get(iso_id=isoId,package_revision_id=packageToUpdate)
                updateObj.overall_status=States.objects.get(state=overallStatusNew)
                updateObj.save()
            try:
                previousIsoObj=ISObuild.objects.get(id=previousISO.id)
                previousISOOverallState= previousIsoObj.overall_status_id
            except:
                previousISOOverallState=None
            if previousISOOverallState==None:
                overallStatusNewPrevious=overallStatusNew
            elif previousISOOverallState==States.objects.get(state='passed').id or previousISOOverallState==States.objects.get(state='warning').id:
                overallStatusNewPrevious=States.objects.get(state='warning')
            else:
                overallStatusNewPrevious=States.objects.get(state='failed')
            for packageToUpdate in commonOldAndNew:
                updateObj=ISObuildMapping.objects.get(iso_id=isoId,package_revision_id=packageToUpdate)
                updateObj.overall_status=States.objects.get(state=overallStatusNewPrevious)
                updateObj.save()
        except:
            for packageToUpdate in currentPackages:
                updateObj=ISObuildMapping.objects.get(iso_id=isoId,package_revision_id=packageToUpdate)
                updateObj.overall_status=States.objects.get(state=overallStatusNew)
                updateObj.save()

    else:
        for packageToUpdate in currentPackages:
            updateObj=ISObuildMapping.objects.get(iso_id=isoId,package_revision_id=packageToUpdate)
            updateObj.overall_status=States.objects.get(state=overallStatusNew)
            updateObj.save()
    isoObj.overall_status=States.objects.get(state=overallStatusNew)
    isoObj.save()

def updateCDBStatus():
    '''
    cleanup any tests in progress more than X hours
    '''
    maxTTL = int(config.get("TESTWARE", "maxTTL_cdb"))
    timeNow = datetime.now()
    timeMinusTTL = datetime.now() - timedelta(hours=maxTTL)
    isos = ISObuild.objects.filter(overall_status__state="in_progress")
    for iso in isos:
        try:
            currentStatusUni = iso.current_status
            currentStatus=ast.literal_eval(currentStatusUni)
            for item in currentStatus:
                typObj=CDBTypes.objects.get(id=item)
                type=typObj.name
                state,start,finish,testReport=currentStatus[item].split("#")
                if state == "in_progress" and not finish:
                    startTime = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
                    if not timeMinusTTL <= startTime <= timeNow:
                        state = "failed"
                        currentStatus = {typObj.id:str(state)+"#"+str(start)+"#"+str(finish)+"#"+str(testReport)}
                        iso.current_status = currentStatus
                        iso.overall_status = States.objects.get(state=state)
                        iso.save()
                        try:
                            allPreviousISO=list(ISObuild.objects.filter(drop=isoObj.drop, mediaArtifact__category=isoObj.mediaArtifact.category).exclude(id__gte=iso.id))
                            allPreviousISO.sort(key=lambda ver:LooseVersion(ver.version), reverse=True)
                            if allPreviousISO:
                                for tmpIso in allPreviousISO:
                                    try:
                                        previousISO=tmpIso
                                        break
                                    except:
                                        previousISO=None
                            else:
                                previousISO=None
                        except Exception as e:
                            previousISO=None
                        isoPackages=ISObuildMapping.objects.filter(iso=iso.id)
                        if isoPackages:
                            updateOverallStatus(isoPackages,previousISO)
                        else:
                            updateOverallStatus(isoPackages,previousISO, iso)
        except Exception as e:
            continue

def updateProductSetCDBStatus(testReport):
    '''
    cleanup any tests in progress more than X hours
    '''
    maxTTL = int(config.get("TESTWARE", "maxTTL_cdb"))
    timeNow = datetime.now()
    timeMinusTTL = datetime.now() - timedelta(hours=maxTTL)
    productSetVersions = ProductSetVersion.objects.filter(status__state="in_progress")
    for productSetVersion in productSetVersions:
        try:
            currentStatusUni = productSetVersion.current_status
            currentStatus=ast.literal_eval(currentStatusUni)
            for item in currentStatus:
                typObj=CDBTypes.objects.get(id=item)
                state,start,finish,testReport,veLog=currentStatus[item].split("#")
                if state == "in_progress" and not finish:
                    startTime = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
                    if not timeMinusTTL <= startTime <= timeNow:
                        state = "failed"
                        currentStatus = {typObj.id:str(state)+"#"+str(start)+"#"+str(finish)+"#"+str(testReport)+"#"+str(veLog)}
                        productSetVersion.current_status = currentStatus
                        productSetVersion.status = States.objects.get(state=state)
                        productSetVersion.save()
        except Exception as e:
            logger.error("Error: "+str(e))
            continue

def updateProductSetOverallStatus(productSetArtifacts,previousArtifacts,currentStatus,productSetVersionID,group,eventType,eventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog, kgbReady, teAllureLogUrl,teTestWare,cautionStatus, sedVersion, deployScript, mtUtilsVersion, deploymentUtilities):
    currentArtifacts=[]
    passedManual = ""
    productSetObj=ProductSetVersion.objects.get(id=productSetVersionID)
    for artifact in productSetArtifacts:
        currentArtifacts.append(str(artifact.mediaArtifactVersion.id).replace("L",""))
        if productSetObj.productSetRelease.updateMasterStatus == True:
            checkStr=str(productSetObj.productSetRelease.masterArtifact.name)
            if checkStr == str(artifact.mediaArtifactVersion.mediaArtifact.name):
                artifactId = artifact.mediaArtifactVersion.artifactId
                group = artifact.mediaArtifactVersion.groupId
                artifactVersion = artifact.mediaArtifactVersion.version
                updateISOStatus(artifactId,artifactVersion,group,eventType,eventDateTime,eventResult,testReport,TestResultReport,testware,testwarePOM,hostProperties,veLog,tafExLog,kgbReady,teAllureLogUrl,teTestWare,cautionStatus, sedVersion, deployScript, mtUtilsVersion, deploymentUtilities)

    stateInProgress=False
    stateFailed=False
    atLeastOnePassed=False
    passedManual=False
    caution=False
    for type in currentStatus:
        '''
        '''
        if 'in_progress' in currentStatus[type]:
            stateInProgress=True
        if 'failed' in currentStatus[type]:
            stateFailed=True
        if 'passed' in currentStatus[type]:
            atLeastOnePassed=True
        if 'passed_manual' in currentStatus[type]:
            passedManual=True
        if 'caution' in currentStatus[type]:
            caution=True


    #hierarchy of overall status logic
    #anything failed -- new pkgs = failed
    #anything failed -- previous pkgs = warning unless if previous state= warning of passed, else =failed
    #anything in prgress -- overall state is in_progress

    if caution == True:
        overallStatusNew='caution'
    elif passedManual == True:
        overallStatusNew='passed_manual'
    elif stateFailed==True:
        overallStatusNew='failed'
    elif stateInProgress==True:
        overallStatusNew='in_progress'
    elif  stateFailed==False and atLeastOnePassed==True:
        overallStatusNew='passed'
    else:
        overallStatusNew='failed'


    if overallStatusNew=='in_progress' or overallStatusNew=='passed':
        for artifactToUpdate in currentArtifacts:
            updateObj=ProductSetVersionContent.objects.get(productSetVersion=productSetVersionID,mediaArtifactVersion_id=artifactToUpdate)
            updateObj.status=States.objects.get(state=overallStatusNew)
            updateObj.save()
    elif overallStatusNew == 'passed_manual' or overallStatusNew == 'caution':
         for artifactToUpdate in currentArtifacts:
             updateObj=ProductSetVersionContent.objects.get(productSetVersion=productSetVersionID,mediaArtifactVersion_id=artifactToUpdate)
             updateObj.status=States.objects.get(state=overallStatusNew)
             updateObj.save()
    elif overallStatusNew=='failed' or overallStatusNew=='warning':
        try:
            oldArtifacts=[]
            if not previousArtifacts == None:
                oldPSArtifacts=ProductSetVersionContent.objects.filter(productSetVersion=previousArtifacts.id)
            else:
                oldPSArtifacts=[]
            for oldArtifact in oldPSArtifacts:
                oldArtifacts.append(str(oldArtifact.mediaArtifactVersion.id).replace("L",""))
            oldSet=set(oldArtifacts)
            newSet=set(currentArtifacts)
            newToBuild=newSet-oldSet
            commonOldAndNew=newSet&oldSet
            for artifactToUpdate in newToBuild:
                updateObj=ProductSetVersionContent.objects.get(productSetVersion=productSetVersionID,mediaArtifactVersion_id=artifactToUpdate)
                updateObj.status=States.objects.get(state=overallStatusNew)
                updateObj.save()
            try:
                previousProductSetObj=ProductSetVersion.objects.get(id=previousArtifacts.id)
                previousProductSetOverallState= previousProductSetObj.status
            except Exception as e:
                previousProductSetOverallState=None
            if previousProductSetOverallState==None:
                overallStatusNewPrevious=overallStatusNew
            elif str(previousProductSetOverallState)=='passed' or str(previousProductSetOverallState)=='warning':
                overallStatusNewPrevious=States.objects.get(state='warning')
            else:
                overallStatusNewPrevious=States.objects.get(state='failed')
            for artifactToUpdate in commonOldAndNew:
                updateObj=ProductSetVersionContent.objects.get(productSetVersion=productSetVersionID,mediaArtifactVersion_id=artifactToUpdate)
                updateObj.status=States.objects.get(state=overallStatusNewPrevious)
                updateObj.save()
        except Exception as e:
            logger.error("error: "+str(e))
            for artifactToUpdate in currentArtifacts:
                updateObj=ProductSetVersionContent.objects.get(productSetVersion=productSetVersionID,mediaArtifactVersion_id=artifactToUpdate)
                updateObj.status=States.objects.get(state=overallStatusNew)
                updateObj.save()
    else:
        for artifactToUpdate in currentArtifacts:
            updateObj=ProductSetVersionContent.objects.get(productSetVersion=productSetVersionID,mediaArtifactVersion_id=artifactToUpdate)
            updateObj.status=States.objects.get(state=overallStatusNew)
            updateObj.save()
    productSetObj=ProductSetVersion.objects.get(id=productSetVersionID)
    productSetObj.status=States.objects.get(state=overallStatusNew)
    productSetObj.save()
    if productSetObj.productSetRelease.productSet.name == "ENM":
        sendEiffelBaselineUpdatedMessage(productSetObj, False)


def collectJobStatusInfoMessageBus(job):
    '''
    Collect information about configured jobs and store using the Message Bus
    '''
    logger.debug("Job: " + job['eiffelData'][0]['jobInstance'])
    logger.debug("Result: " + job['eiffelData'][0]['resultCode'])
    logger.debug("Build ID: " +  job['eiffelData'][0]['jobExecutionNumber'])

    '''
    # Get job data
    jobObj, created = Job.objects.get_or_create(name=job['eiffelData'][0]['jobInstance'])
    buildObj, created = JobResult.objects.get_or_create(job=jobObj, buildId=job['eiffelData'][0]['jobExecutionNumber'])
    buildObj.status =  job['eiffelData'][0]['resultCode']
    logger.debug("Result: " + job['eiffelData'][0]['resultCode'])
    if job['eiffelData'][0]['resultCode']  == "SUCCESS":
        buildObj.passed = 1
    elif job['eiffelData'][0]['resultCode'] == "FAILURE":
        buildObj.failed = 1
    elif job['eiffelData'][0]['resultCode'] == "ABORTED":
        buildObj.aborted = 1
    elif job['eiffelData'][0]['resultCode'] == "UNSTABLE":
        buildObj.unstable = 1
    buildObj.url = "https://ci-portal.seli.wh.rnd.internal.ericsson.com/jenkins/job/" + str(job['eiffelData'][0]['jobInstance']) + "/" + str(job['eiffelData'][0]['jobExecutionNumber']) +"/"
    eventTime = str(job['eventTime']).replace("T", " ")
    event = eventTime.replace("Z", "")
    finished = int(datetime.strptime(event, '%Y-%m-%d %H:%M:%S.%f').strftime("%s"))
    buildObj.finished = datetime.fromtimestamp(finished)
    buildObj.finished_ts = finished
    logger.debug("timestamp: " + str(buildObj.finished_ts) + " ; datetime: " + str(buildObj.finished))
    buildObj.save()

    # Mapping the job to views in JobViewMapping table
    try:
        datav = readDataFromURL("", depth=0)
    except Exception as e:
        logger.error("Problem reading from root jenking api" )
        return
    for viewNameDict in datav['views']:
        viewName = viewNameDict['name']
        viewName = re.sub(r"\s+", '%20', viewName)
        if viewName is not None:
            logger.debug("looking for jobs with view " + viewName)
            # Get the view, and if it does not exist populdate it
            viewObj, created = View.objects.get_or_create(name=viewName)
            # retrieve the job names associated with this view and create the mappings
            logger.debug("Creating relevant job mappings@")
            jobInfo = readDataFromURL("/view/" + viewName + "/")
            for j in jobInfo['jobs']:
                try:
                    jobObj = Job.objects.get(name=j['name'])
                    exists = JobViewMapping.objects.filter(job=jobObj, view=viewObj).exists()
                    if not exists:
                        jvm = JobViewMapping(job=jobObj, view=viewObj)
                        jvm.save()
                        logger.debug("Mapped " + str(jvm))
                 except:
                        # job has not been collected yet ...
                        continue

        '''



def getFailingJobs(view,jobNameSearch):
    '''
    Interrogate Jenkins and get the list of jobs for a view that are currently
    failing. Note that this implementation uses readDataFromURL (and therefore
    makes a call to Jenkins) twice for each failed job - once for the last
    successful job and once for the last failed job. We probably want to try
    to get this information from the database first (it should be there if
    our periodic populating job has run) before resorting to talking to Jenkins.
    '''
    if view == "ALL":
        jobInfo = readDataFromURL("" , depth=1)
    else:
        jobInfo = readDataFromURL("/view/" + view + "/", depth=1)
    jl = []
    for job in jobInfo['jobs']:
        if job["color"] == "red" or job["color"] == "aborted" or job["color"] == "yellow":
            if jobNameSearch == "ALL" or jobNameSearch == job['name']:
                # assume never successful until we know different
                if job["color"] == "yellow":
                    failType = "unstable"
                else:
                    failType = "failed"
                successTime = 0
                failedTime = 0
                unstableTime = 0
                stableTime = 0
                lastSuccessJob = job['lastSuccessfulBuild']
                jobName = job['name']
                if lastSuccessJob is not None:
                    try:
                        buildId = lastSuccessJob['number']
                        existing = JobResult.objects.get(job__name=jobName, buildId=buildId)
                        successTime = existing.finished_ts
                    except:
                        # info on the last successful job
                        sji = readDataFromURL(lastSuccessJob['url'])
                        successTime = sji['timestamp']

                lastFailedJob = job['lastCompletedBuild']
                if lastFailedJob is not None:
                    try:
                        buildId = lastFailedJob['number']
                        existing = JobResult.objects.get(job__name=jobName, buildId=buildId)
                        failedTime = existing.finished_ts
                    except:
                        sji = readDataFromURL(lastFailedJob['url'])
                        failedTime = sji['timestamp']
                lastUnstableJob = job['lastUnstableBuild']
                if lastUnstableJob is not None:
                    try:
                        buildId = lastUnstableJob['number']
                        existing = JobResult.objects.get(job__name=jobName, buildId=buildId)
                        unstableTime = existing.finished_ts
                    except:
                        # info on the last unsuccessful job
                        sji = readDataFromURL(lastUnstableJob['url'])
                        unstableTime = sji['timestamp']

                lastStableJob = job['lastStableBuild']
                if lastStableJob is not None:
                    try:
                        buildId = lastStableJob['number']
                        existing = JobResult.objects.get(job__name=jobName, buildId=buildId)
                        stableTime = existing.finished_ts
                    except:
                        # info on the last successful job
                        sji = readDataFromURL(lastStableJob['url'])
                        stableTime = sji['timestamp']
                jd = {
                        "name": jobName,
                        "failType":failType,
                        "lastSuccess": successTime,
                        "lastFailure": failedTime,
                        "lastUnstable": unstableTime,
                        "lastStable": stableTime,
                     }
                jl.append(jd)
    return jl

def getJobTrend(jobName, viewName, granularity, start, end):
    '''
    get the job trend data between the supplied dates at the requested granularity

    We are using the fem_jobresult table as the seed to generate the dates from,
    but if this turns out in the future to be a bottleneck as the size grows we can use
    a table with only 10 rows in it as follows:
      CREATE TABLE datecounter a(int);
      insert into datecounter VALUES (1),(2),(3),(4),(5),(6),(7),(8),(9),(10);

    then our date list query will look like this:
      INSERT INTO res (day) select date(@tempDate := (date(@tempDate) + interval 1 day)) as theDate
      from datecounter p, datecounter q group by theDate having theDate  <= "2012-11-30" ON DUPLICATE KEY UPDATE day = day;

    for more than 100 (10 * 10) days we would need to do something like:
      from datecounter p, datecounter q, datecounter r
    '''

    # Set the correct DT formats based on the granularity
    if granularity == "day":
        format = "%Y-%m-%d"
        outputFormat = "%d %b"
        defaultEnd = (datetime.now() + timedelta(days=1)).strftime(format)
        if start == "":
            start = (datetime.now() - timedelta(days=10)).strftime(format)
        if end == "":
            end = defaultEnd
    elif granularity == "hour":
        format = "%Y-%m-%d %H:00"
        outputFormat = "%a %H:00"
        defaultEnd = (datetime.now() + timedelta(days=0)).strftime(format)
        if start == "":
            start = (datetime.now() - timedelta(days=1)).strftime(format)
        if end == "":
            end = defaultEnd
    elif granularity == "minute":
        format = "%Y-%m-%d %H:%I"
        outputFormat = "%a %H:%I"
        defaultEnd = datetime.now().strftime(format)
        if start == "":
            start = (datetime.now() - timedelta(minutes=60)).strftime(format)
        if end == "":
            end = defaultEnd
        format = "%Y-%m-%d %H:%i"
        outputFormat = "%a %H:%i"
    elif granularity == "week":
        format = "%Y-%m-%d"
        outputFormat = "%U"
        defaultEnd = datetime.now().strftime(format)
        if start == "":
            start = (datetime.now() - timedelta(days=60)).strftime(format)
        if end == "":
            end = defaultEnd
    elif granularity == "month":
        format = "%Y-%m-%d"
        outputFormat = "%b"
        defaultEnd = datetime.now().strftime(format)
        if start == "":
            start = (datetime.now() - timedelta(days=365)).strftime(format)
        if end == "":
            end = defaultEnd


    from django.db import connection, transaction

    cursor = connection.cursor()
    cursor.execute(
    '''
    set @tempDate = %s
    ''', [start])

    if jobName is None:
        if viewName is None:
            cursor.execute(
                '''
            CREATE TEMPORARY TABLE res AS
                SELECT TIMESTAMP(DATE_FORMAT(fem_jobresult.finished, %s)) AS datetime,
                SUM(fem_jobresult.passed) AS passed,
                SUM(fem_jobresult.unstable) AS unstable,
                SUM(fem_jobresult.failed) AS failed,
                SUM(fem_jobresult.aborted) AS aborted
                from fem_jobresult, fem_job
                WHERE fem_jobresult.finished BETWEEN %s AND %s
                AND fem_jobresult.job_id = fem_job.id
                group by datetime
                ''', [format, start, end])
        else:
            cursor.execute(
                '''
            CREATE TEMPORARY TABLE res AS
                SELECT TIMESTAMP(DATE_FORMAT(fem_jobresult.finished, %s)) AS datetime,
                SUM(fem_jobresult.passed) AS passed,
                SUM(fem_jobresult.unstable) AS unstable,
                SUM(fem_jobresult.failed) AS failed,
                SUM(fem_jobresult.aborted) AS aborted
                from fem_jobresult, fem_job, fem_jobviewmapping, fem_view
                WHERE fem_jobresult.job_id = fem_jobviewmapping.job_id
                AND fem_jobviewmapping.view_id = fem_view.id
                AND fem_view.name = %s
                AND fem_jobresult.job_id = fem_job.id
                AND fem_jobresult.finished BETWEEN %s AND %s
                group by datetime
                ''', [format, viewName, start, end])
    else:
        cursor.execute(
            '''
        CREATE TEMPORARY TABLE res AS
            SELECT TIMESTAMP(DATE_FORMAT(fem_jobresult.finished, %s)) AS datetime,
            SUM(fem_jobresult.passed) AS passed,
            SUM(fem_jobresult.unstable) AS unstable,
            SUM(fem_jobresult.failed) AS failed,
            SUM(fem_jobresult.aborted) AS aborted
            from fem_jobresult, fem_job
            WHERE fem_jobresult.finished BETWEEN %s AND %s
            AND fem_jobresult.job_id = fem_job.id
            AND fem_job.name = %s group by datetime
            ''', [format, start, end, jobName])

    cursor.execute('CREATE UNIQUE INDEX ri ON res(datetime)', [])

    cursor.execute(
        "INSERT INTO res (datetime, passed, unstable, failed, aborted) " +
            "select timestamp(@tempDate := (timestamp(@tempDate) + interval 1 " + granularity + ")) AS theDate, 0, 0, 0, 0 " +
            "FROM fem_jobresult p GROUP BY theDate HAVING theDate <= '" + end + "'" +
            "ON DUPLICATE KEY UPDATE datetime = datetime", [])

    cursor.execute('SELECT UNIX_TIMESTAMP(datetime) * 1000 AS dt, passed, unstable, failed, aborted FROM res ORDER BY datetime', [])
    #cursor.execute('SELECT UNIX_TIMESTAMP(datetime) AS datetime, passed, unstable, failed, aborted FROM res ORDER BY datetime', [])
    #cursor.execute('SELECT * FROM res ORDER BY datetime', [])

    desc = cursor.description
    data = [
            {"key": "Passed", "values": []},
            {"key": "Unstable", "values": []},
            {"key": "Failed", "values": []},
            {"key": "Aborted", "values": []}
            ]

    for row in cursor.fetchall():
        data[0]["values"].append([int(row[0]), int(row[1])])
        data[1]["values"].append([int(row[0]), int(row[2])])
        data[2]["values"].append([int(row[0]), int(row[3])])
        data[3]["values"].append([int(row[0]), int(row[4])])

    cursor.execute('DROP TABLE res', [])
    return data

def getJobTrend2(jobName, viewName, granularity, start, end):
    '''
    get the job trend data between the supplied dates at the requested granularity

    We are using the fem_jobresult table as the seed to generate the dates from,
    but if this turns out in the future to be a bottleneck as the size grows we can use
    a table with only 10 rows in it as follows:
      CREATE TABLE datecounter a(int);
      insert into datecounter VALUES (1),(2),(3),(4),(5),(6),(7),(8),(9),(10);

    then our date list query will look like this:
      INSERT INTO res (day) select date(@tempDate := (date(@tempDate) + interval 1 day)) as theDate
      from datecounter p, datecounter q group by theDate having theDate  <= "2012-11-30" ON DUPLICATE KEY UPDATE day = day;

    for more than 100 (10 * 10) days we would need to do something like:
      from datecounter p, datecounter q, datecounter r
    '''

    # Set the correct DT formats based on the granularity
    if granularity == "day":
        format = "%Y-%m-%d"
        outputFormat = "%d %b"
        defaultEnd = (datetime.now() + timedelta(days=1)).strftime(format)
    elif granularity == "hour":
        format = "%Y-%m-%d %H:00"
        outputFormat = "%a %H:00"
        defaultEnd = (datetime.now() + timedelta(hours=1)).strftime(format)
    elif granularity == "minute":
        format = "%Y-%m-%d %H:%i"
        outputFormat = "%a %H:%i"
        defaultEnd = datetime.now().strftime(format)
    elif granularity == "week":
        format = "%Y-%m-%d"
        outputFormat = "%U"
        defaultEnd = datetime.now().strftime(format)
    elif granularity == "month":
        format = "%Y-%m-%d"
        outputFormat = "%b"
        defaultEnd = datetime.now().strftime(format)

    if start == "":
        start = (datetime.now() - timedelta(days=10)).strftime(format)
    if end == "":
        end = defaultEnd

    from django.db import connection, transaction

    cursor = connection.cursor()
    cursor.execute(
    '''
    set @tempDate = %s
    ''', [start])

    if jobName is None:
        if viewName is None:
            cursor.execute(
                '''
            CREATE TEMPORARY TABLE res AS
                SELECT TIMESTAMP(DATE_FORMAT(fem_jobresult.finished, %s)) AS datetime,
                SUM(fem_jobresult.passed) AS passed,
                SUM(fem_jobresult.unstable) AS unstable,
                SUM(fem_jobresult.failed) AS failed,
                SUM(fem_jobresult.aborted) AS aborted
                from fem_jobresult, fem_job
                WHERE fem_jobresult.finished BETWEEN %s AND %s
                AND fem_jobresult.job_id = fem_job.id
                group by datetime
                ''', [format, start, end])
        else:
            cursor.execute(
                '''
            CREATE TEMPORARY TABLE res AS
                SELECT TIMESTAMP(DATE_FORMAT(fem_jobresult.finished, %s)) AS datetime,
                SUM(fem_jobresult.passed) AS passed,
                SUM(fem_jobresult.unstable) AS unstable,
                SUM(fem_jobresult.failed) AS failed,
                SUM(fem_jobresult.aborted) AS aborted
                from fem_jobresult, fem_job, fem_jobviewmapping, fem_view
                WHERE fem_jobresult.job_id = fem_jobviewmapping.job_id
                AND fem_jobviewmapping.view_id = fem_view.id
                AND fem_view.name = %s
                AND fem_jobresult.job_id = fem_job.id
                AND fem_jobresult.finished BETWEEN %s AND %s
                group by datetime
                ''', [format, viewName, start, end])
    else:
        cursor.execute(
            '''
        CREATE TEMPORARY TABLE res AS
            SELECT TIMESTAMP(DATE_FORMAT(fem_jobresult.finished, %s)) AS datetime,
            SUM(fem_jobresult.passed) AS passed,
            SUM(fem_jobresult.unstable) AS unstable,
            SUM(fem_jobresult.failed) AS failed,
            SUM(fem_jobresult.aborted) AS aborted
            from fem_jobresult, fem_job
            WHERE fem_jobresult.finished BETWEEN %s AND %s
            AND fem_jobresult.job_id = fem_job.id
            AND fem_job.name = %s group by datetime
            ''', [format, start, end, jobName])

    cursor.execute('CREATE UNIQUE INDEX ri ON res(datetime)', [])

    cursor.execute(
        "INSERT INTO res (datetime, passed, unstable, failed, aborted) " +
            "select timestamp(@tempDate := (timestamp(@tempDate) + interval 1 " + granularity + ")) AS theDate, 0, 0, 0, 0 " +
            "FROM fem_jobresult p GROUP BY theDate HAVING theDate <= '" + end + "'" +
            "ON DUPLICATE KEY UPDATE datetime = datetime", [])

    cursor.execute('SELECT UNIX_TIMESTAMP(datetime) * 1000 AS dt, passed, unstable, failed, aborted FROM res ORDER BY datetime', [])
    #cursor.execute('SELECT UNIX_TIMESTAMP(datetime) AS datetime, passed, unstable, failed, aborted FROM res ORDER BY datetime', [])
    #cursor.execute('SELECT * FROM res ORDER BY datetime', [])

    desc = cursor.description
    data = [
            {"key": "Passed", "values": []},
            {"key": "Unstable", "values": []},
            {"key": "Failed", "values": []},
            {"key": "Aborted", "values": []}
            ]

    for row in cursor.fetchall():
        #data[0]["values"].append([str(row[0]) +","+ str(row[1])])
        #data[0]["values"].append("{" + str(row[0]) +","+ str(row[1])+"}")
        data[0]["values"].extend([{"x":  (int(row[0])/1000),"y":  int(row[1]),},])
        data[1]["values"].extend([{"x":  (int(row[0])/1000),"y":  int(row[2]),},])
        data[2]["values"].extend([{"x":  (int(row[0])/1000),"y":  int(row[3]),},])
        data[3]["values"].extend([{"x":  (int(row[0])/1000),"y":  int(row[4]),},])

    cursor.execute('DROP TABLE res', [])
    return data

def getJobs():
    config = CIConfig()
    templateDir = config.get("FEM", "jobTemplates")
    jobs=[]
    for template in listdir(templateDir):
        jobs.append((template,template))
    return jobs


def sendCreateJob(jobs,repo,server,jobName,username,password,enable,buildBranch,pushBranch,node):
    config = CIConfig()
    templateDir = config.get("FEM", "jobTemplates")
    results = []
    for job in jobs:
        templateFH = open(templateDir+job)
        fileContents=templateFH.read()
        fileContents=fileContents.replace("__REPO__",repo)
        fileContents=fileContents.replace("__BUILDBRANCH__",buildBranch)
        fileContents=fileContents.replace("__PUSHBRANCH__",pushBranch)
        fileContents=fileContents.replace("__NODE__",node)
        fileContents=fileContents.replace("__NAMEPREFIX__",jobName)
        createJobUrl = str(server)+"createItem?name="+str(jobName)+"_"+str(job)
        req = urllib2.Request(createJobUrl, fileContents, {'Content-Type':'text/xml'})
        base64string = base64.encodestring('%s:%s' % (str(username), str(password))).replace('\n', '')
        req.add_header("Authorization", "Basic %s" % base64string)

        try:
            response  = urllib2.urlopen(req)
            if response.getcode() == 200:
                createResult = 'OK'
            else:
                createResult = response.getcode()

        except urllib2.URLError , e:
            createResult = str(e)
        result = {
                   'job':"Create: "+jobName+"_"+str(job),
                   'res':createResult
                  }
        results.append(result)
        if createResult == 'OK':
            if enable == True:
                data = urllib.urlencode({"null":"null"})
                enableJobUrl = str(server)+"/job/"+str(jobName)+"_"+str(job)+"/enable"
                req = urllib2.Request(enableJobUrl,data)
                base64string = base64.encodestring('%s:%s' % (str(username), str(password))).replace('\n', '')
                req.add_header("Authorization", "Basic %s" % base64string)

                try:
                    response  = urllib2.urlopen(req)
                    if response.getcode() == 200:
                        enableResult = 'OK'
                    else:
                        enableResult = response.getcode()

                except urllib2.URLError , e:
                    enableResult = str(e)
                result = {
                             'job':"Enable: "+jobName+"_"+str(job),
                             'res':enableResult
                        }
                results.append(result)
            else:
                data = urllib.urlencode({"null":"null"})
                disableJobUrl = str(server)+"/job/"+str(jobName)+"_"+str(job)+"/disable"
                req = urllib2.Request(disableJobUrl,data)
                base64string = base64.encodestring('%s:%s' % (str(username), str(password))).replace('\n', '')
                req.add_header("Authorization", "Basic %s" % base64string)

                try:
                    response  = urllib2.urlopen(req)
                    if response.getcode() == 200:
                        disableResult = 'OK'
                    else:
                        disableResult = response.getcode()

                except urllib2.URLError , e:
                    disableResult = str(e)
                result = {
                             'job':"Disable: "+jobName+"_"+str(job),
                             'res':disableResult
                        }
                results.append(result)

    return results


def getBuildStatus(jenkinsHost, jobName, buildSelector, timeout):
    '''
    Recieves paramters which define a specific jenkins build.
    Pulls json from the jenkins API.
    If job is queued it waits for a timeout specified by the user, while periodically checking to see if build is still in queue.
    if job is still in queue after timeout, the job is removed from the queue.
    '''

    try:
        urllib2.urlopen("http://"+jenkinsHost+"/jenkins/")
    except Exception as e:
        status="Not a jenkins machine: "+ str(e)
        logger.error(status)
        raise Exception(status)

    try:
        urllib2.urlopen("http://"+jenkinsHost+"/jenkins/job/"+jobName+"/")
    except Exception as e:
        status="Job does not exist: " + str(e)
        logger.error(status)
        raise Exception(status)

    try:
        jenkinsStream = urllib2.urlopen("http://"+jenkinsHost+"/jenkins/job/"+jobName+"/"+buildSelector+"/api/json")
    except Exception as e:
        status="Invalid Build Selector Entered: " + str(e)
        logger.error(status)
        raise Exception(status)

    try:
        buildStatusJson = json.load(jenkinsStream)
    except:
        status="Failed to parse json: " +str(e)
        logger.error(status)
        raise Exception(status)

    if inQueue(jenkinsHost, jobName):
        for a in range(timeout/5):
            time.sleep(10)
            if not inQueue(jenkinsHost, jobName):
                break
        if inQueue(jenkinsHost, jobName):
            queuedItem = json.load(urllib2.urlopen("http://"+jenkinsHost+"/jenkins/job/"+jobName+"/api/json"))
            queueID = queuedItem['queueItem']['id']
            result = "Job still in queue after timeout.\nAttepting to remove job from queue.."
            requests.post("http://"+jenkinsHost+"/jenkins/queue/cancelItem?id="+str(queueID))
            if inQueue(jenkinsHost, jobName):
                result += "\nFailed to remove job from queue!"
                return result
            else:
                result += "\nSuccessfully removed job from queue"
                return result
    if buildStatusJson["building"] == True:
        return"[" + jobName + "] Build status: In Progress\n [" + jobName + "] Estimated Build Time: " + str(buildStatusJson["estimatedDuration"])
    else:
        return "[" + jobName + "] Build status: " + buildStatusJson["result"]+"\n[" + jobName + "] Estimated Build Time: " + str(buildStatusJson["estimatedDuration"])+"\n[" + jobName + "] Actual build time: " + str(buildStatusJson["duration"])


def inQueue(jenkinsHost, job):
    '''
    returns true if job is queued, false if it is not
    '''
    queryQueueStatus = json.load(urllib2.urlopen("http://"+jenkinsHost+"/jenkins/job/"+job+"/api/json"))
    return queryQueueStatus["inQueue"]

def autoDeliverOnKGB(artifactN,VersionN,m2type,revertDeliveryOnFail,deliveredList,deliveryFault,deliverySummary,artifactSummary):
    if PackageRevision.objects.filter(package__name=artifactN,version=VersionN,m2type=m2type,autodeliver=1).exists():
        autoDeliverObj = PackageRevision.objects.get(package__name=artifactN,version=VersionN,m2type=m2type,autodeliver=1)
        logger.debug("Attempting auto delivery"+str(artifactN)+":"+str(VersionN)+":"+str(m2type))
        #DO NOT REMOVE IMPORT
        import cireports.utils
        intendedEntry = autoDeliverObj.autodrop
        autoDeliveryPlatform = autoDeliverObj.platform
        intendedEntryList = intendedEntry.split(',')
        intendedProductList = []
        try:
            for intended in intendedEntryList:
                intended = intended.replace(" ","")
                try:
                    intendedProductList.append(intended.split(':')[0])
                except:
                    logger.error("Invalid Intended drop entry")
            uniqueProducts = set(intendedProductList)
            for  intendedProduct in uniqueProducts:
                intendedProduct = intendedProduct.replace(" ","")
                deliveryStatus=cireports.utils.performDelivery2(str(artifactN), str(VersionN), m2type, 'auto', intendedProduct, 'automatedDelivery@ci-portal.seli.wh.rnd.internal.ericsson.com', autoDeliveryPlatform)
                if 'DELIVERED' in deliveryStatus:
                    deliveredList.append(deliveryStatus)
                    summaryString = "Successful"
                elif 'ERROR' in deliveryStatus:
                    deliveryFault = True
                    summaryString = "Failure"
                elif 'INDROP' in deliveryStatus:
                    deliveryFault = False
                    summaryString = "Already in Drop"
                elif 'NOTOPEN' in deliveryStatus:
                    deliveryFault = True
                    summaryString = "Drop is not Open"
                else:
                    deliveryFault = True
                    summaryString = "Failure"
                deliverySummary = deliverySummary+"<br>"+"Delivery of "+str(artifactN)+" "+str(VersionN)+" "+str(m2type) +":"+summaryString
                artifactSummary = artifactSummary +"<br>"+str(artifactN)+" "+str(VersionN)+" "+str(m2type)

        except Exception as e:
            logger.error("Issue with auto delivery "+str(e))
            deliveryFault = True
        if revertDeliveryOnFail and deliveryFault:
            deliverySummary = "Error delivering artifact, No deliveries made: <br>"+artifactSummary
            for returnedStatus in deliveredList:
                returnedStatusSplit = returnedStatus.split(',')
                for returnedStatusItem in returnedStatusSplit:
                    if 'DELIVERED' in returnedStatusItem:
                        dontCare,obsoleteArtifactId,obsoleteDropId = returnedStatusItem.split(':')
                        cireports.utils.obsolete2(obsoleteArtifactId,obsoleteDropId)

    return deliveredList,deliveryFault,deliverySummary,artifactSummary

def sendAutoDeliveryMail(deliverySummary,autoDeliveryMail):
    try:
        dm = config.get("CIFWK", "fromEmail")
        msg = EmailMessage(
                   'AutoDelivery Summary',
                   deliverySummary,
                   dm,
                   autoDeliveryMail
              )
        msg.content_subtype = "html"
        msg.send()
    except:
        logger.error("Issue sending auto delivery mail")

def sendFailMail(message):
    sender = config.get('CIFWK', 'cifwkDistributionList')
    subject = ("KGB slave job failed: Needs Action")
    message = (str(message))
    email = [config.get('CIFWK', 'upgrade_email')]
    try:
        send_mail(subject,message,sender,email, fail_silently=False)
    except Exception as e:
        logger.error("Issue sending email " + str(e))

def getPreviousArtifactNewEvent(groupId, artifactId, version):
    '''
    The getPreviousArtifactNewEvent functions gets the previous Artifact New Event from the Event Repo and returns this to be set as a Jenkins Environment Variable
    '''
    isoVersionList = []
    result = "ISOBUILD_PREVIOUS_ANE_ID= \nISOBUILD_PREVIOUS_BDE_ID=\n"
    completeArtifactNotFound = "Artifact " + str(groupId) + ":" + str(artifactId) + ":" + str(version) + " not found"
    ISOBuildObj = ISObuild.objects.filter(groupId=groupId, artifactId=artifactId).order_by('build_date')
    for isoBuild in ISOBuildObj:
        if isoBuild.version != version:
            isoVersionList.append(isoBuild.version)
        else:
            break
    if isoVersionList:
        version = isoVersionList[-1]
    else:
        logger.info("Previous " + completeArtifactNotFound)
        return result
    try:
        er101GetArtifactURL = config.get("FEM", "er101GetArtifactURL")
        getArtifactURL = er101GetArtifactURL + str(groupId) + "/" + str(artifactId) + "/" + str(version)
        artifactNewEventCommand = 'curl -k --url "' + getArtifactURL +'"'
        artifactNewEventRestCall = subprocess.Popen(artifactNewEventCommand, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd="/tmp")
        artifactNewEventRestCallResult = artifactNewEventRestCall.communicate()[0]
        if completeArtifactNotFound in artifactNewEventRestCallResult:
            logger.info(completeArtifactNotFound)
            return result
        artifactNewEventRestCallResult = json.loads(artifactNewEventRestCallResult)
        artifactNewEvent = list(artifactNewEventRestCallResult['artifactNewEvents'])[-1]
    except Exception as error:
        message = "Error: getting previous artifact new event from event Repo: " + str(error) + "\n"
        logger.error(message)
        return result
    result = "ISOBUILD_PREVIOUS_ANE_ID=" + str(artifactNewEvent) + "\n"
    result = getPreviousBaselineDefinedEvent(result,artifactNewEvent,completeArtifactNotFound)
    return result

def getPreviousBaselineDefinedEvent(result,artifactNewEvent,completeArtifactNotFound):
    '''
    The getPreviousArtifactNewEvent functions gets the previous Baseline Defined Event from the Event Repo and returns this to be set as a Jenkins Environment Variable
    '''
    try:
        er101GetEventURL = config.get("FEM", "er101GetEventURL")
        getBaselineDefinedEventURL = er101GetEventURL + str(artifactNewEvent)
        baselineDefinedEventCommand = 'curl -k --url "' + getBaselineDefinedEventURL +'"'
        baselineDefinedEventRestCall = subprocess.Popen(baselineDefinedEventCommand, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd="/tmp")
        baselineDefinedEventRestCallResult = baselineDefinedEventRestCall.communicate()[0]
        if completeArtifactNotFound in baselineDefinedEventRestCallResult:
            result = result + "ISOBUILD_PREVIOUS_BDE_ID=\n"
            logger.info(completeArtifactNotFound)
            return result
        baselineDefinedEventRestCallResult = json.loads(baselineDefinedEventRestCallResult)
        eiffelMessageLatestVersion = config.get("MESSAGE_BUS", "latestVersion")
        versionDict = baselineDefinedEventRestCallResult["eiffelMessageVersions"]
        version = ""
        for value in versionDict:
            version = value
            if version.startswith(eiffelMessageLatestVersion):
                break
        baselineDefinedEvent = baselineDefinedEventRestCallResult['eiffelMessageVersions'][version]
        for key,value in baselineDefinedEvent.items():
            if key == "eventData":
                baselineDefinedEventID = str(value['baselineId'])
    except Exception as error:
        result = result + "ISOBUILD_PREVIOUS_BDE_ID=\n"
        logger.error("Error: getting previous baseline defined event from event Repo: " +str(error) + "\n")
        return result
    return result + "ISOBUILD_PREVIOUS_BDE_ID=" + str(baselineDefinedEventID)


def getTeamParentElement(packageName):
    packageObj = Package.objects.get(name=packageName)
    teamList = []
    parentElementList = []
    if PackageComponentMapping.objects.filter(package=packageObj).exists():
        componentMappingObj=PackageComponentMapping.objects.only('component__element').filter(package=packageObj)
        for item in componentMappingObj:
            teamList.append(item.component.element)
        if item.component.parent.element:
            parentElementList.append(item.component.parent.element)
    team = ','.join(teamList)
    parentElement = ','.join(parentElementList)
    return team,parentElement

def getFlow(messageDict,version):
    try:
        flow = messageDict["eiffelMessageVersions"][version]["eventData"]["flowContext"]
    except:
        flow = None
    return flow

def getInputEventIDs(messageDict,version):
    inputEventIDsStr = ""
    try:
        inputEventIDs = messageDict["eiffelMessageVersions"][version]["inputEventIds"]
    except:
        inputEventIDs = None
    if inputEventIDs:
        inputEventIDsStr = ','.join(inputEventIDs)
    return inputEventIDsStr

def getBuildFailure(messageDict,version):
    try:
        buildFailure = messageDict["eiffelMessageVersions"][version]["eventData"]["optionalParameters"]["buildFailure"]
    except:
        buildFailure = None
    return buildFailure

def deploymentUtilitiesHandler(deploymentUtilities,itemObj):
    '''
    The deploymentUtilitiesHandler function is called when a event is received containing the optional parameter deploymentUtilities as a handler
    '''
    media = False
    if isinstance(itemObj, ISObuild):
        media = True
    if deploymentUtilities == None:
        logger.debug("Deployment Utilities set to: " + str(deploymentUtilities) + " as not defined, Updating the CI DB if needed.")
        deploymentUtilitiesHandlerCheck(itemObj)
    else:
        logger.debug("Attempting to add deployment Utilities: " + str(deploymentUtilities) + " to the CI DB, for: " + str(itemObj))
        deploymentUtilitiesItems = deploymentUtilities.split(",")
        for item in deploymentUtilitiesItems:
            label = ""
            itemCount = item.count("::")
            if itemCount == 1:
                utility,version = item.split("::")
            elif itemCount == 2:
                utility,version,label = item.split("::")
            else:
                logger.error("Please ensure that the deploymentUtilities optional parameter is structured correctly eg: 'utility::version::label' or 'utility::version', if in a list then this should be a ',' serperated list")
            if versionNumberCheck(version):
                if not DeploymentUtilities.objects.filter(utility=utility).exists():
                    deploymentUtility = DeploymentUtilities.objects.create(utility=str(utility))
                else:
                    deploymentUtility = DeploymentUtilities.objects.get(utility=utility)

                if media:
                    DeploymentUtilsToISOBuild.objects.filter(utility_version__utility_name=deploymentUtility,iso_build=itemObj).update(active=False)
                else:
                    DeploymentUtilsToProductSetVersion.objects.filter(utility_version__utility_name=deploymentUtility,productSetVersion=itemObj).update(active=False)

                if not DeploymentUtilitiesVersion.objects.filter(utility_name=deploymentUtility,utility_version=version).exists():
                    deploymentUtilityVersion = DeploymentUtilitiesVersion.objects.create(utility_name=deploymentUtility,utility_version=version,utility_label=label)
                else:
                    DeploymentUtilitiesVersion.objects.filter(utility_name=deploymentUtility,utility_version=version).update(utility_label=label)
                    deploymentUtilityVersion = DeploymentUtilitiesVersion.objects.get(utility_name=deploymentUtility,utility_version=version)

                if media:
                    if not DeploymentUtilsToISOBuild.objects.filter(utility_version=deploymentUtilityVersion,iso_build=itemObj).exists():
                        DeploymentUtilsToISOBuild.objects.create(utility_version=deploymentUtilityVersion,iso_build=itemObj,active=True)
                    else:
                        DeploymentUtilsToISOBuild.objects.filter(utility_version=deploymentUtilityVersion,iso_build=itemObj).update(active=True)
                else:
                    if not DeploymentUtilsToProductSetVersion.objects.filter(utility_version=deploymentUtilityVersion,productSetVersion=itemObj).exists():
                        DeploymentUtilsToProductSetVersion.objects.create(utility_version=deploymentUtilityVersion,productSetVersion=itemObj,active=True)
                    else:
                        DeploymentUtilsToProductSetVersion.objects.filter(utility_version=deploymentUtilityVersion,productSetVersion=itemObj).update(active=True)

            else:
                logger.error("Please ensure that the deploymentUtilities optional parameter contains vaild version: " + str(item))

def deploymentUtilitiesHandlerCheck(itemObj):
    '''
    The deploymentUtilitiesHandlerCheck function checks if there are defined utils for an ISO Object and disables them for this ISO as they are not part of the event
    '''
    media = False
    if isinstance(itemObj, ISObuild):
        media = True
    if media:
        if DeploymentUtilsToISOBuild.objects.filter(iso_build=itemObj).exists():
            DeploymentUtilsToISOBuild.objects.filter(iso_build=itemObj).update(active=False)
    else:
        if DeploymentUtilsToProductSetVersion.objects.filter(utility_version=deploymentUtilityVersion,productSetVersion=itemObj).exists():
            DeploymentUtilsToProductSetVersion.objects.filter(productSetVersion=itemObj).update(active=False)

def updateKGBsnapshotReport(gavList):
    '''
    Updating Package Revision kgb snapshot report
    '''
    authorisedSnapshots = config.get('CIFWK', 'authorisedSnapshots')
    logger.info(str(authorisedSnapshots))
    authorised = True
    for gav in gavList:
        if gav != "":
            artifact,version,group=gav.split("::")
            if "-SNAPSHOT" in version:
                if not str(artifact) in authorisedSnapshots:
                    authorised = False
    for gav in gavList:
        if gav != "":
            artifact,version,group=gav.split("::")
            if not "-SNAPSHOT" in version:
                try:
                    pkgRev = PackageRevision.objects.get(artifactId=artifact, version=version, groupId=group)
                    if "-SNAPSHOT" in str(gavList):
                        if not authorised:
                            pkgRev.kgb_snapshot_report = True
                    else:
                        pkgRev.kgb_snapshot_report = False
                    pkgRev.save()
                except Exception as error:
                    logger.error("Issue Updating Package Revision kgb_snapshot_report - " + str(gav))

def versionNumberCheck(version):
    '''
    Checking the version passed in by the message
    '''
    match = re.search(r'^([a-zA-Z\d]+)\.([a-zA-Z\d]+)|^([a-zA-Z\d]+)\.([a-zA-Z\d]+)\.([a-zA-Z\d]+)|^([a-zA-Z\d]+)\.([a-zA-Z\d]+)\.([a-zA-Z\d]+).([a-zA-Z\d]+)', version)
    if match:
        return True
    return False
