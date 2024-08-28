import datetime
from socket import timeout
import MySQLdb
from django.db import transaction
from cireports.models import *
from distutils.version import LooseVersion
import logging
from logging.handlers import RotatingFileHandler
import requests
import json
from ciconfig import CIConfig
from requests.auth import HTTPBasicAuth
from threading import Lock
from cireports.utils import jiraValidation
from itertools import chain

config = CIConfig()
logDir = config.get('CIFWK', 'buildLogDir')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = RotatingFileHandler(logDir + "cnbuildlog.log", mode='a',
                              maxBytes=200000000, backupCount=7, encoding='utf-8', delay=0)
handler.setFormatter(formatter)
logger.addHandler(handler)

cnBuildlog_lock = Lock()
mergeCNDG_lock = Lock()
revertCNDG_lock = Lock()

@transaction.atomic
def createCNBuildLogData(metadata_content):
    '''
    create Build log data and post to DB.
    '''
    cnBuildlog_lock.acquire()
    errorMsg = None
    fromCnProductSetVersionObj = None
    toCnProductSetVersionObj = None
    allurePercentage = None
    builddate = None
    resultMap = {}
    confidenceLevelName = metadata_content["confidencelevel"]["confidence_level_name"]
    try:
        sid = transaction.savepoint()
        logger.info("Posting CN Buildlog Data Started")
        logger.info(json.dumps(metadata_content, sort_keys=True, indent=4))
        try:
            confidenceLevelObj = RequiredCNConfidenceLevel.objects.get(
                confidence_level_name=confidenceLevelName)
        except Exception as e:
            errorMsg = "ERROR: Failed to add build log data. Confidence level name does not exist. Please investigate: " + str(e)
            logger.error(errorMsg)
            cnBuildlog_lock.release()
            return 1, errorMsg
        fromCnProductSetVersionObj, toCnProductSetVersionObj, errorMsg = validateProductSetVersion(
            metadata_content["from_ps"], metadata_content["to_ps"])
        if errorMsg != None:
            cnBuildlog_lock.release()
            return 1, errorMsg
        overallStateObj, confidenceLevelStateObj, errorMsg = getStateObject(
            metadata_content["overall_status"], metadata_content["confidencelevel"]["status"])
        if errorMsg != None:
            cnBuildlog_lock.release()
            return 1, errorMsg
        if not metadata_content["drop"]:
            errorMsg = "Failed to add build log data. Drop should not be empty."
            logger.error(errorMsg)
            cnBuildlog_lock.release()
            return 1, errorMsg
        if not metadata_content["test_phase"]:
            errorMsg = "Failed to add build log data. Test Phase should not be empty."
            logger.error(errorMsg)
            cnBuildlog_lock.release()
            return 1, errorMsg
        if metadata_content["confidencelevel"]["timestamp"] != "":
            timestamp = int(metadata_content["confidencelevel"]["timestamp"])
            builddate = datetime.fromtimestamp(timestamp)
        if metadata_content["confidencelevel"]["report_link"] != "":
            allurePercentage, errorMsg = calculateAllurePercentage(
                metadata_content["confidencelevel"]["report_link"])
            if errorMsg != None:
                cnBuildlog_lock.release()
                return 1, errorMsg
        if metadata_content["build_log_id"] == "":
            resultMap, errorMsg = createCNBuildLogObject(confidenceLevelName, metadata_content, fromCnProductSetVersionObj,
                                                         toCnProductSetVersionObj, overallStateObj, confidenceLevelObj, confidenceLevelStateObj, allurePercentage, builddate)
            if errorMsg != None:
                transaction.savepoint_rollback(sid)
                cnBuildlog_lock.release()
                return 1, errorMsg
        else:
            resultMap, errorMsg = updateCNBuildLogData(metadata_content, fromCnProductSetVersionObj, toCnProductSetVersionObj,
                                                       overallStateObj, confidenceLevelObj, confidenceLevelStateObj, allurePercentage, builddate)
            if errorMsg != None:
                transaction.savepoint_rollback(sid)
                cnBuildlog_lock.release()
                return 1, errorMsg
        logger.info("Posting CN Buildlog Data Finished")
        logger.info(json.dumps(resultMap, sort_keys=True, indent=4))
        cnBuildlog_lock.release()
    except Exception as e:
        errorMsg = "Posting CN Build log data has failed! Please investigate the error: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
        cnBuildlog_lock.release()
    return resultMap, errorMsg

def createCNBuildLogObject(confidenceLevelName, metadata_content, fromCnProductSetVersionObj, toCnProductSetVersionObj, overallStateObj, confidenceLevelObj, confidenceLevelStateObj, allurePercentage, builddate):
    '''
    Create Build log object and its corresponding Confidence Level objects and post to DB.
    '''
    errorMsg = None
    resultMap = {}
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not RequiredCNConfidenceLevel.objects.filter(confidence_level_name=confidenceLevelName, requireBuildLogId=False).exists():
            errorMsg = "Failed to add build log data. Build log id should not be empty for this confidence level."
            logger.error(errorMsg)
            return 1, errorMsg
        try:
            cnBuildLogObj = CNBuildLog.objects.create(drop=metadata_content["drop"], testPhase=metadata_content["test_phase"], fromCnProductSetVersion=fromCnProductSetVersionObj,
                                                      toCnProductSetVersion=toCnProductSetVersionObj, overall_status=overallStateObj, deploymentName=metadata_content["deployment"])
        except Exception as e:
            errorMsg = "Posting CN Build log data has failed! Please investigate the error: " + str(e)
            logger.error(errorMsg)
            return 1, errorMsg
        try:
            CNConfidenceLevelRevision.objects.create(cnConfidenceLevel=confidenceLevelObj, status=confidenceLevelStateObj, cnBuildLog=cnBuildLogObj, createdDate=now, updatedDate=now,
                                                     reportLink=metadata_content["confidencelevel"]["report_link"], buildJobLink=metadata_content["confidencelevel"]["job_link"], percentage=allurePercentage, buildDate=builddate)
        except Exception as e:
            errorMsg = "Posting CN Build log data has failed while creating the confidence level revision. Please investigate the error: " + str(e)
            logger.error(errorMsg)
            return 1, errorMsg
        resultMap["build_log_id"] = cnBuildLogObj.id
        resultMap["status"] = "SUCCESS"
        resultMap["build_log_status"] = "created"
    except Exception as e:
        errorMsg = "ERROR: Failed to create build log data. Please investigate the error" + str(e)
        logger.error(errorMsg)
    return resultMap, errorMsg

def updateCNBuildLogData(metadata_content, fromCnProductSetVersionObj, toCnProductSetVersionObj, overallStateObj, confidenceLevelObj, confidenceLevelStateObj, allurePercentage, builddate):
    '''
    Update existing Build log data and post to DB.
    '''
    errorMsg = None
    resultMap = {}
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cnBuildLogObj = CNBuildLog.objects.get(
                id=metadata_content["build_log_id"])
        except Exception as e:
            errorMsg = "ERROR: Failed to update build log data. Build log id does not exist. Please investigate: " + str(e)
            logger.error(errorMsg)
            return 1, errorMsg
        CNBuildLog.objects.filter(id=metadata_content["build_log_id"]).update(drop=metadata_content["drop"], testPhase=metadata_content["test_phase"], fromCnProductSetVersion=fromCnProductSetVersionObj,
                                                                              toCnProductSetVersion=toCnProductSetVersionObj, overall_status=overallStateObj, deploymentName=metadata_content["deployment"])
        if CNConfidenceLevelRevision.objects.filter(cnConfidenceLevel__confidence_level_name=metadata_content["confidencelevel"]["confidence_level_name"], cnBuildLog__id=cnBuildLogObj.id).exists():
            CNConfidenceLevelRevision.objects.filter(cnConfidenceLevel__confidence_level_name=metadata_content["confidencelevel"]["confidence_level_name"], cnBuildLog__id=cnBuildLogObj.id).update(
                status=confidenceLevelStateObj, updatedDate=now, reportLink=metadata_content["confidencelevel"]["report_link"], buildJobLink=metadata_content["confidencelevel"]["job_link"], percentage=allurePercentage, buildDate=builddate)
        else:
            CNConfidenceLevelRevision.objects.create(cnConfidenceLevel=confidenceLevelObj, status=confidenceLevelStateObj, cnBuildLog=cnBuildLogObj, createdDate=now, updatedDate=now,
                                                     reportLink=metadata_content["confidencelevel"]["report_link"], buildJobLink=metadata_content["confidencelevel"]["job_link"], percentage=allurePercentage, buildDate=builddate)
        resultMap["build_log_id"] = cnBuildLogObj.id
        resultMap["status"] = "SUCCESS"
        resultMap["build_log_status"] = "updated"
    except Exception as e:
        errorMsg = "ERROR: Failed to update build log data. Please investigate the error" + str(e)
        logger.error(errorMsg)
    return resultMap, errorMsg

def validateProductSetVersion(fromPs, toPs):
    '''
    Validating PS Version for the build log.
    '''
    errorMsg = None
    fromCnProductSetVersionObj = None
    toCnProductSetVersionObj = None
    try:
        if fromPs != "":
            try:
                fromCnProductSetVersionObj = CNProductSetVersion.objects.get(
                    product_set_version=fromPs)
            except Exception as e:
                errorMsg = "ERROR: Failed to add build log data. From Product set version does not exist."
                logger.error(errorMsg)
                return fromCnProductSetVersionObj, toCnProductSetVersionObj, errorMsg
        try:
            toCnProductSetVersionObj = CNProductSetVersion.objects.get(
                product_set_version=toPs)
        except Exception as e:
            errorMsg = "ERROR: Failed to add build log data. To Product set version does not exist."
            logger.error(errorMsg)
            return fromCnProductSetVersionObj, toCnProductSetVersionObj, errorMsg
    except Exception as e:
        errorMsg = "ERROR: Failed to add build log data while validating the product set version. Please investigate:" + str(e)
        logger.error(errorMsg)
    return fromCnProductSetVersionObj, toCnProductSetVersionObj, errorMsg

def getStateObject(overallStatus, status):
    '''
    Getting state object for status and overall status.
    '''
    errorMsg = None
    overallStateObj = None
    confidenceLevelStateObj = None
    try:
        overallStateObj = States.objects.get(state=overallStatus)
        confidenceLevelStateObj = States.objects.get(state=status)
    except Exception as e:
        errorMsg = "ERROR: Failed to add build log data. Status does not exist."
        logger.error(errorMsg)
    return overallStateObj, confidenceLevelStateObj, errorMsg

def calculateAllurePercentage(allure):
    '''
    Calculate allure percentage from allure link.
    '''
    errorMsg = None
    allurePercentage = None
    try:
        allureLink = allure.split("index.html")
        allureLinkDetails = allureLink[0] + "data/total.json"
        ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
        userName = config.get('CIFWK', 'functionalUser')
        password = config.get('CIFWK', 'functionalUserPassword')
        response = requests.get(allureLinkDetails, auth=(
            userName, password), verify=ssl_certs, timeout=60)
        data = (response.content).decode("utf-8").replace(")]}\'", "")
        allureStatistics = json.loads(data)
        passed = allureStatistics["statistic"]["passed"]
        total = allureStatistics["statistic"]["total"]
        percentage = (passed*100)/float(total)
        allurePercentage = "{:.2f}".format(percentage)
    except Exception as e:
        errorMsg = "ERROR: Failed to add build log data while calculating allure pass percentage from allure link. Please investigate:" + str(e)
        logger.error(errorMsg)
    return allurePercentage, errorMsg

def getCNBuildLogDataByDrop(dropNumber):
    '''
    This function is to get cloud native build log data for a given drop.
    '''
    errorMsg = None
    result = None
    try:
        # get a list of cn buildlog data objects
        cnBuildLogDataObjs, errorMsg = getCnBuildLogObjectsByDrop(dropNumber)
        if errorMsg != None:
            return result, errorMsg
        # get mapping data for each of the cn buildlog id
        for cnBuildLog in cnBuildLogDataObjs:
            # get confidence levels for each build log
            cnBuildLog, errorMsg = getCnConfidenceLevels(cnBuildLog)
            if errorMsg != None:
                return result, errorMsg
            # get comment and jira for each build log
            cnBuildLog, errorMsg = getCnBuildLogComments(cnBuildLog)
            if errorMsg != None:
                return result, errorMsg
        result = cnBuildLogDataObjs
    except Exception as e:
        errorMsg = "ERROR: Failed to get build log data. Please investigate the error" + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def getCnBuildLogObjectsByDrop(dropNumber):
    '''
    This function is to get cloud native build log objects for a given drop.
    '''
    errorMsg = None
    cnBuildLogDataObjs = None
    try:
        cnBuildLogFields = ('id', 'drop', 'testPhase', 'fromCnProductSetVersion__product_set_version',
                            'toCnProductSetVersion__product_set_version', 'overall_status__state', 'deploymentName')
        cnBuildLogDataObjs = CNBuildLog.objects.select_related('fromCnProductSetVersion', 'toCnProductSetVersion', 'overall_status').filter(
            drop=dropNumber, active=1).order_by('-id').only(cnBuildLogFields).values(*cnBuildLogFields)
    except Exception as e:
        errorMsg = "ERROR: Failed to get buildlog data from the db for the drop. Please investigate: " + str(e)
        logger.error(errorMsg)
    return cnBuildLogDataObjs, errorMsg

def getCnConfidenceLevels(cnBuildLog):
    '''
    This function is to get confidence levels for each buildlog object.
    '''
    errorMsg = None
    cnConfidenceLevelRevisionObjs = None
    cnConfidenceLevelTypeList = []
    try:
        cnConfidenceLevelTypeObj = CNConfidenceLevelType.objects.all()
    except Exception as e:
        errorMsg = "ERROR: Failed to get confidence level type. Please investigate: " + str(e)
        logger.error(errorMsg)
        return cnBuildLog, errorMsg
    for cnConfidenceLevelType in cnConfidenceLevelTypeObj:
        cnConfidenceLevelTypeList.append(cnConfidenceLevelType.confidenceLevelTypeName)
    cnConfidenceLevelRevisionFields = ('cnBuildLog__id', 'cnConfidenceLevel__confidence_level_name',
                                       'status__state', 'reportLink', 'buildJobLink', 'percentage', 'buildDate')
    try:
        cnConfidenceLevelRevisionObjs = CNConfidenceLevelRevision.objects.select_related('cnBuildLog', 'cnConfidenceLevel', 'status').filter(
            cnBuildLog__id=cnBuildLog['id']).only(cnConfidenceLevelRevisionFields).values(*cnConfidenceLevelRevisionFields)
        for cnConfidenceLevelRevision in cnConfidenceLevelRevisionObjs:
            buildlogConfidenceLevel = cnConfidenceLevelRevision.get('cnConfidenceLevel__confidence_level_name')
            confidenceLevelObj = RequiredCNConfidenceLevel.objects.get(confidence_level_name = buildlogConfidenceLevel)
            cnBuildLog[confidenceLevelObj.confidenceLevelType.confidenceLevelTypeName] = cnConfidenceLevelRevision
    except Exception as e:
        errorMsg = "ERROR: Failed to get confidence level for build log id : " + str(cnBuildLog['id']) + ". Please investigate: " + str(e)
        logger.error(errorMsg)
        return cnBuildLog, errorMsg
    for confidenceLevel in cnConfidenceLevelTypeList:
        if confidenceLevel not in cnBuildLog:
            cnBuildLog[confidenceLevel] = None
    return cnBuildLog, errorMsg

def getCnBuildLogComments(cnBuildLog):
    '''
    This function is to get comments for each buildlog object.
    '''
    errorMsg = None
    cnBuildLogCommentFields = ('id', 'comment', 'cnJiraIssue__jiraNumber')
    cnBuildLogCommentResult = []
    try:
        cnBuildlogCommentObj = CNBuildLogComment.objects.select_related('cnBuildLog', 'cnJiraIssue').filter(
            cnBuildLog__id=cnBuildLog['id']).only(cnBuildLogCommentFields).values(*cnBuildLogCommentFields)
        if len(cnBuildlogCommentObj) > 0:
            for cnBuildlogComment in cnBuildlogCommentObj:
                cnBuildLogCommentResult.append(cnBuildlogComment)
            cnBuildLog['comments'] = cnBuildLogCommentResult
        else:
            cnBuildLog['comments'] = None
    except Exception as e:
        errorMsg = "ERROR: Failed to get comment and Jira for build log id : " + str(cnBuildLog['id']) + ". Please investigate: " + str(e)
        logger.error(errorMsg)
    return cnBuildLog, errorMsg

def getCNBuildLogId(dropNumber, toPs, confidenceLevel, deployment):
    '''
    This function is to get cloud native build log id for a given to_ps, confidenceLevel and deployment name.
    '''
    errorMsg = None
    resultMap = {}
    try:
        cnBuildlogIdMap = CNBuildLog.objects.filter(
            drop=dropNumber, toCnProductSetVersion__product_set_version=toPs, deploymentName=deployment, active=1).values('id')
        for cnBuildlogIds in cnBuildlogIdMap:
            if CNConfidenceLevelRevision.objects.filter(cnConfidenceLevel__confidence_level_name=confidenceLevel, cnBuildLog__id=cnBuildlogIds['id']).exists():
                resultMap["build_log_id"] = cnBuildlogIds['id']
    except Exception as e:
        errorMsg = "ERROR: Failed to get build log id. Please investigate the error" + str(e)
        logger.error(errorMsg)
    return resultMap, errorMsg

@transaction.atomic
def createCNBuildLogComment(cnBuildlogId, comment, jira):
    '''
    This function post comment and jira for the particular cloud native build log id.
    '''
    errorMsg = None
    result = None
    cnJiraIssueObj = None
    try:
        sid = transaction.savepoint()
        if jira != "":
            cnJiraIssueObj, errorMsg = createJiraComment(jira, cnBuildlogId)
            if errorMsg != None:
                transaction.savepoint_rollback(sid)
                return 1, errorMsg
        cnBuildlogObj, errorMsg = getCnBuildlogObject(cnBuildlogId)
        if errorMsg != None:
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
        CNBuildLogComment.objects.create(
            cnBuildLog=cnBuildlogObj, cnJiraIssue=cnJiraIssueObj, comment=comment)
        result = "SUCCESS"
    except Exception as e:
        errorMsg = "ERROR: Failed to add comment/jira for the buildlog id : " + str(cnBuildlogId) + ". Please investigate the error: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
    return result, errorMsg

@transaction.atomic
def editCNBuildLogComment(commentId, editComment):
    '''
    This function edits a particular comment for the particular cloud native build log.
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        if CNBuildLogComment.objects.filter(id=commentId).exists():
            cnBuildlogCommentObj = CNBuildLogComment.objects.get(id=commentId)
            cnBuildlogCommentObj.comment = editComment
            cnBuildlogCommentObj.save(force_update=True)
        result = "SUCCESS"
    except Exception as e:
        errorMsg = "ERROR: Failed to edit comment for the buildlog comment id : " + str(commentId) + ". Please investigate the error: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
    return result, errorMsg

@transaction.atomic
def deleteCNBuildLogComment(commentId):
    '''
    This function deletes a comment for a specified cloud native build log.
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        if CNBuildLogComment.objects.filter(id=commentId).exists():
            cnBuildlogCommentObj = CNBuildLogComment.objects.get(id=commentId)
            if cnBuildlogCommentObj.cnJiraIssue_id != None:
                cnBuildlogCommentObj.comment = ""
                cnBuildlogCommentObj.save(force_update=True)
            else:
                cnBuildlogCommentObj.delete()
        result = "SUCCESS"
    except Exception as e:
        errorMsg = "ERROR: Failed to delete comment for the buildlog comment id : " + str(commentId) + ". Please investigate the error: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
    return result, errorMsg

@transaction.atomic
def deleteCNBuildLogJira(commentId):
    '''
    This function deletes a jira for a specified cloud native build log.
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        if CNBuildLogComment.objects.filter(id=commentId).exists():
            cnBuildlogCommentObj = CNBuildLogComment.objects.get(id=commentId)
            if cnBuildlogCommentObj.comment != "":
                cnBuildlogCommentObj.cnJiraIssue_id = None
                cnBuildlogCommentObj.save(force_update=True)
            else:
                cnBuildlogCommentObj.delete()
        result = "SUCCESS"
    except Exception as e:
        errorMsg = "ERROR: Failed to delete jira for the buildlog comment id : " + str(commentId) + ". Please investigate the error: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
    return result, errorMsg

def createJiraComment(jira, cnBuildlogId):
    '''
    This function post jira for the particular cloud native build log id.
    '''
    errorMsg = None
    cnJiraIssueObj = None
    try:
        if CNJiraIssue.objects.filter(jiraNumber=jira).exists():
            cnJiraIssueObj = CNJiraIssue.objects.get(jiraNumber=jira)
        else:
            jsonObj, statusCode = jiraValidation(jira)
            if statusCode == "200":
                cnJiraIssueObj = CNJiraIssue.objects.create(
                    jiraNumber=jira, issueType=jsonObj['fields']['issuetype']['name'])
            else:
                errorMsg = "Failed to add jira while validating the Jira Ticket for the buildlog id : " + str(cnBuildlogId) + ". Invalid Jira ticket"
                logger.error(errorMsg)
    except Exception as e:
        errorMsg = "Failed to add jira for the buildlog id : " + str(cnBuildlogId) + ". Please investigate the error: " + str(e)
        logger.error(errorMsg)
    return cnJiraIssueObj, errorMsg

def getCnBuildlogObject(cnBuildlogId):
    '''
    This function get cn buildlog log object for the particular cloud native build log id.
    '''
    errorMsg = None
    cnBuildlogObj = None
    try:
        if CNBuildLog.objects.filter(id=cnBuildlogId).exists():
            cnBuildlogObj = CNBuildLog.objects.get(id=cnBuildlogId)
        else:
            errorMsg = "Failed to add jira for the buildlog id : " + str(cnBuildlogId) + " .Invalid Buildlog Id"
            logger.error(errorMsg)
    except Exception as e:
        errorMsg = "Failed to add jira for the buildlog id : " + str(cnBuildlogId) + ", while getting the BuildLog object. Please investigate the error: " + str(e)
        logger.error(errorMsg)
    return cnBuildlogObj, errorMsg

def updateCNBuildLogOverallStatus(cnBuildlogId,overallStatus):
    '''
    This function updates the Buildlog overall status for the particular cloud native build log id given.
    '''
    errorMsg = None
    cnBuildlogObj = None
    try:
        if CNBuildLog.objects.filter(id=cnBuildlogId).exists():
            cnBuildlogObj = CNBuildLog.objects.get(id=cnBuildlogId)
        else:
            errorMsg = "Failed to update the overall status for the buildlog id : " + str(cnBuildlogId) + " .Invalid Buildlog Id"
            logger.error(errorMsg)
            return 1,errorMsg
        try:
            overallStateObj = States.objects.get(state=overallStatus)
        except Exception as e:
            errorMsg = "Failed to update the overall status for the buildlog id : " + str(cnBuildlogId) + ". Invalid status"
            logger.error(errorMsg)
            return 1,errorMsg
        cnBuildlogObj.overall_status = overallStateObj
        cnBuildlogObj.save(force_update=True)
    except Exception as e:
        errorMsg = "Unexpected error while updating overall status for the buildlog id " + str(cnBuildlogId) + ". Please investigate the error: " + str(e)
        logger.error(errorMsg)
        return 1,errorMsg
    return "Overall status updated successfully for the buildlog id : " + str(cnBuildlogId) , errorMsg

def revertCNDeliveryGroupContent(deliveryGroupNumber, comment):
    '''
    This function is to revert code changes for all the contents in a delivery group.
    '''
    revertCNDG_lock.acquire()
    errorMsg = None
    result = None
    revCount = 0
    try:
        cnImageContentList = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber)
        cnProductContentList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber)
        cnPipelineContentList = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber)
        dgContentList = list(chain(cnImageContentList, cnProductContentList, cnPipelineContentList))
        # Creating reverted patchset for all gerrit links
        result, comment, errorMsg = revertCNdgContentGerritList(dgContentList, comment)
        if errorMsg:
            revertCNDG_lock.release()
            return result, comment, errorMsg
        # Validating all reverted dg contents before merging
        result, comment, errorMsg = validateRevertedCNdgContentGerritList(dgContentList, comment)
        if errorMsg:
            revertCNDG_lock.release()
            return result, comment, errorMsg
        # Merging all the revered patchsets
        result, revCount, comment, errorMsg = mergeRevertedCNdgContentGerritList(dgContentList, comment)
        if errorMsg:
            revertCNDG_lock.release()
            return result, comment, errorMsg
        if revCount == len(dgContentList):
            result = "obsoleted"
        else:
            result = "delivered"
        revertCNDG_lock.release()
    except Exception as e:
        errorMsg = "<br /> UNEXPECTED ERROR: Failed to revert code changes for this delivery group. Please investigate: " + str(e) + " <br />"
        logger.error(errorMsg)
        comment += errorMsg
        revertCNDG_lock.release()
        return 'FAILED', comment, errorMsg
    return result, comment, errorMsg

@transaction.atomic
def revertCNdgContentGerritList(cndgContentList, comment):
    '''
    This function is to create reverted patchset for all gerrit links and update the db with reverted change id.
    '''
    errorMsg = None
    result = None
    gerritUserName = config.get('CIFWK', 'cENMfunctionalUser')
    gerritPassword = config.get('CIFWK', 'cENMfunctionalUserPassword')
    gerritHostName = config.get('GERRIT_SSH', 'gerrit_hostname')
    try:
        for dgContentObj in cndgContentList:
            sid = transaction.savepoint()
            gerritLink = dgContentObj.cnGerrit.gerrit_link
            changeNum = gerritLink.split("/c/")[-1].replace("/", "")
            if not dgContentObj.revert_change_id:
                try:
                    changeId = getChangeId(changeNum, gerritUserName, gerritPassword, gerritHostName)
                except Exception as e:
                    changeIdErrorMsg = "<br /> ERROR: Failed to get changeId for " + gerritLink + " Please investigate: " + str(e) + " <br />"
                    logger.error(changeIdErrorMsg)
                    comment += changeIdErrorMsg
                    return 'FAILED', comment, changeIdErrorMsg
                try:
                    revertedChangeId, revStatusCode, revertedChangeIdErrorMsg = createRevertedPatchSet(str(changeId), gerritUserName, gerritPassword, gerritHostName)
                    if revStatusCode != "200":
                        logger.error(revertedChangeIdErrorMsg)
                        comment += revertedChangeIdErrorMsg
                        return 'FAILED', comment, revertedChangeIdErrorMsg
                except Exception as e:
                    revertedChangeIdErrorMsg = "<br /> ERROR: Failed to create reverted patch set for " + gerritLink + " Please investigate: " + str(e) + " <br />"
                    logger.error(revertedChangeIdErrorMsg)
                    comment += revertedChangeIdErrorMsg
                    return 'FAILED', comment, revertedChangeIdErrorMsg
                try:
                    updateRevertedChangeId(str(revertedChangeId), dgContentObj)
                except Exception as e:
                    updatedErrorMsg = "<br /> ERROR: Failed to update DB with change id for " + gerritLink + " with new changeId " + str(revertedChangeId) + " in CI Portal Please investigate: " + str(e) + " <br />"
                    logger.error(updatedErrorMsg)
                    comment += updatedErrorMsg
                    transaction.savepoint_rollback(sid)
                    return 'FAILED', comment, updatedErrorMsg
    except Exception as e:
        errorMsg = "<br /> UNEXPECTED ERROR: Failed to revert code changes for this delivery group. Please investigate: " + str(e) + " <br />"
        logger.error(errorMsg)
        comment += errorMsg
        transaction.savepoint_rollback(sid)
        return 'FAILED', comment, errorMsg
    return result, comment, errorMsg

def validateRevertedCNdgContentGerritList(cndgContentList, comment):
    '''
    This function is to validating all reverted dg contents before merging and to submit code review.
    '''
    errorMsg = None
    result = None
    gerritUserName = config.get('CIFWK', 'cENMfunctionalUser')
    gerritPassword = config.get('CIFWK', 'cENMfunctionalUserPassword')
    gerritHostName = config.get('GERRIT_SSH', 'gerrit_hostname')
    try:
        for dgContentObj in cndgContentList:
            revertedChangeId = dgContentObj.revert_change_id
            gerritLink = dgContentObj.cnGerrit.gerrit_link
            try:
                revisionId = getRevisionId(str(revertedChangeId), gerritUserName, gerritPassword, gerritHostName)
            except Exception as e:
                updatedErrorMsg = "<br /> ERROR: Failed to get revision id for " + gerritLink + " with new changeId " + str(revertedChangeId) + " in CI Portal Please investigate: " + str(e) + " <br />"
                logger.error(updatedErrorMsg)
                comment += updatedErrorMsg
                return 'FAILED', comment, updatedErrorMsg
            try:
                statusCode, codeReviewErrorMsg = submitCodeReview(str(revertedChangeId), revisionId, gerritUserName, gerritPassword, gerritHostName)
                if statusCode != "200":
                    logger.error(codeReviewErrorMsg)
                    comment += codeReviewErrorMsg
                    return 'FAILED', comment, codeReviewErrorMsg
            except Exception as e:
                updatedErrorMsg = "<br /> ERROR: Failed to submit code review with change id for " + gerritLink + " with new changeId " + str(revertedChangeId) + " in CI Portal Please investigate: " + str(e) + " <br />"
                logger.error(updatedErrorMsg)
                comment += updatedErrorMsg
                return 'FAILED', comment, updatedErrorMsg
            try:
                mergeable = getMergeable(str(revertedChangeId), str(revisionId), gerritUserName, gerritPassword, gerritHostName)
            except Exception as e:
                updatedErrorMsg = "<br /> ERROR: Failed to get review details for " + gerritLink + " in CI Portal Please investigate: " + str(e) + " <br />"
                logger.error(updatedErrorMsg)
                comment += updatedErrorMsg
                return 'FAILED', comment, updatedErrorMsg
            if not mergeable:
                try:
                    statusCode, comment = rebaseChange(str(revertedChangeId), comment, gerritUserName, gerritPassword, gerritHostName)
                    if statusCode != "200":
                        errorMsg = "ERROR: Reverted gerritLink for " + gerritLink + " can't be rebased. Please check the commit for more info."
                        logger.error(errorMsg)
                        comment += errorMsg
                        return 'FAILED', comment, errorMsg
                except Exception as e:
                    errorMsg = "<br /> ERROR: Reverted gerritLink for " + gerritLink + " can't be rebased. Please investigate: " + str(e) + " <br />"
                    logger.error(errorMsg)
                    comment += errorMsg
                    return 'FAILED', comment, errorMsg
    except Exception as e:
        errorMsg = "<br /> UNEXPECTED ERROR: Failed to revert code changes for this delivery group. Please investigate: " + str(e) + " <br />"
        logger.error(errorMsg)
        comment += errorMsg
        return 'FAILED', comment, errorMsg
    return result, comment, errorMsg

@transaction.atomic
def mergeRevertedCNdgContentGerritList(cndgContentList, comment):
    '''
    This function is to merge all the revered patchsets.
    '''
    errorMsg = None
    result = None
    revCount = 0
    gerritUserName = config.get('CIFWK', 'cENMfunctionalUser')
    gerritPassword = config.get('CIFWK', 'cENMfunctionalUserPassword')
    gerritHostName = config.get('GERRIT_SSH', 'gerrit_hostname')
    try:
        for dgContentObj in cndgContentList:
            sid = transaction.savepoint()
            revertedChangeId = dgContentObj.revert_change_id
            gerritLink = dgContentObj.cnGerrit.gerrit_link
            try:
                newRevisionId = getRevisionId(str(revertedChangeId), gerritUserName, gerritPassword, gerritHostName)
            except Exception as e:
                updatedErrorMsg = "<br /> ERROR: Failed to get revision id for " + gerritLink + " after rebasing the change. Please investigate: " + str(e) + " <br />"
                logger.error(updatedErrorMsg)
                comment += updatedErrorMsg
                return 'FAILED', revCount, comment, updatedErrorMsg
            try:
                statusCode, codeReviewErrorMsg = submitCodeReview(str(revertedChangeId), newRevisionId, gerritUserName, gerritPassword, gerritHostName)
                if statusCode != "200":
                    logger.error(codeReviewErrorMsg)
                    comment += codeReviewErrorMsg
                    return 'FAILED', revCount, comment, codeReviewErrorMsg
            except Exception as e:
                updatedErrorMsg = "<br /> ERROR: Failed to submit code review for reveted gerrit link of " + gerritLink + " in CI Portal Please investigate: " + str(e) + " <br />"
                logger.error(updatedErrorMsg)
                comment += updatedErrorMsg
                return 'FAILED', revCount, comment, updatedErrorMsg
            try:
                statusCodeSubmit, comment = submitChanges(str(revertedChangeId), comment, gerritUserName, gerritPassword, gerritHostName)
            except Exception as e:
                submissionErrorMsg = "<br /> ERROR: Failed to submit reverted patch set for " + gerritLink + " with new changeId " + str(revertedChangeId) + " in Gerrit. Please investigate: " + str(e) + " <br />"
                logger.error(submissionErrorMsg)
                comment += submissionErrorMsg
                return 'FAILED', revCount, comment, submissionErrorMsg
            try:
                revResult = updatePatchSetStatus(statusCodeSubmit, dgContentObj)
            except Exception as e:
                updatedErrorMsg = "<br /> ERROR: Failed to update reverted patch set for " + gerritLink + " with new changeId " + str(revertedChangeId) + " in CI Portal. Please investigate: " + str(e) + " <br />"
                logger.error(updatedErrorMsg)
                comment += updatedErrorMsg
                transaction.savepoint_rollback(sid)
                return 'FAILED', revCount, comment, updatedErrorMsg
            if revResult == "REVERTED":
                revCount += 1
    except Exception as e:
        errorMsg = "<br /> UNEXPECTED ERROR: Failed to submit reverted code changes for this delivery group. Please investigate: " + str(e) + " <br />"
        logger.error(errorMsg)
        comment += errorMsg
        transaction.savepoint_rollback(sid)
        return 'FAILED', revCount, comment, errorMsg
    return result, revCount, comment, errorMsg

def getChangeId(changeNum, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is get change Id from the change number in an existing gerrit link.
    '''
    response = None
    gerritUrl = "https://" + gerritHostName + "/a/changes/?q=change:" + changeNum
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.get(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    decodedJsonData = (response.content).decode("utf-8").replace(")]}\'", "")
    data = json.loads(decodedJsonData)
    changeId = data[0].get('change_id')
    return changeId

def getBranch(changeNum, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is get the branch from the change number in an existing gerrit link.
    '''
    response = None
    gerritUrl = "https://" + gerritHostName + "/a/changes/?q=change:" + changeNum
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.get(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    decodedJsonData = (response.content).decode("utf-8").replace(")]}\'", "")
    data = json.loads(decodedJsonData)
    branch = data[0].get('branch')
    return branch

def createRevertedPatchSet(changeId, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is to create a new patch set for reverted code changes by changeId for a content in a DG.
    '''
    patchSetId = None
    errorMsg = None
    statusCode = None
    response = None
    gerritUrl = "https://" + gerritHostName + "/a/changes/" + changeId + "/revert"
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.post(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    statusCode = str(response.status_code)
    if statusCode != "200":
        errorMsg = "<br />ERROR: This content can't be reverted. Error message from Gerrit: " + response.content + " <br />"
        return patchSetId, statusCode, errorMsg
    decodedJsonData = (response.content).decode("utf-8").replace(")]}\'", "")
    data = json.loads(decodedJsonData)
    patchSetId = data.get('change_id')
    return patchSetId, statusCode, errorMsg

def updateRevertedChangeId(changeId, mappingObj):
    '''
    This function is update database with new revert change id for reverted cn dg content.
    '''
    mappingObj.revert_change_id = changeId
    mappingObj.save(force_update=True)

def getRevisionId(changeId, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is to get revision id for the reverted patchset.
    '''
    response = None
    gerritUrl = "https://" + gerritHostName + "/a/changes/?q=change:" + changeId +"&o=CURRENT_REVISION"
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.get(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    decodedJsonData = (response.content).decode("utf-8").replace(")]}\'", "")
    data = json.loads(decodedJsonData)
    revisionId = data[0].get('current_revision')
    return revisionId

def submitCodeReview(changeId, revisionId, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is to submit code review and verified for the reverted patchset.
    '''
    response = None
    errorMsg = None
    statusCode = None
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    gerritUrl = "https://" + gerritHostName + "/a/changes/" + changeId +"/revisions/" + revisionId + "/review"
    myData = {
        "labels" : {
            "Verified" : 1,
            "Code-Review" : 2
        }
    }
    header = {'content-type': 'application/json'}
    jsonData = json.dumps(myData)
    response = requests.post(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, data=jsonData, headers = header, timeout=120)
    statusCode = str(response.status_code)
    if statusCode != "200":
        errorMsg = "<br />Error posting code review. Error message from Gerrit: " + response.content + " <br />"
    return statusCode, errorMsg

def updatePatchSetStatus(statusCode, mappingObj):
    '''
    This function is update database with new revert change id and status for reverted cn dg content.
    '''
    result = "NOT_REVERTED"
    if statusCode == "200":
        reverted_state = States.objects.get(state = "reverted")
        result = "REVERTED"
    elif statusCode == "409":
        reverted_state = States.objects.get(state = "conflicts")
    else:
        reverted_state = States.objects.get(state = "not_reverted")
    mappingObj.state = reverted_state
    mappingObj.save(force_update=True)
    return result

def submitChanges(changeId, comment, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is submit code changes by changeId for a content in a DG.
    '''
    gerritUrl = "https://" + gerritHostName + "/a/changes/" + changeId + "/submit"
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.post(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    statusCode = str(response.status_code)
    if statusCode == "409":
        comment += "<br />WARNING: This content can't be submitted. <br />" + response.content + " <br />"
    if statusCode != "409" and statusCode != "200":
        comment += "<br />ERROR: This content can't be submitted due to unexpected issue. Please investigate." + "Error code from Gerrit: " + statusCode + " <br />"
    return statusCode, comment

@transaction.atomic
def mergeCNDeliveryGroupContent(deliveryGroupNumber, comment):
    '''
    This function is to merge code changes for all the contents in a delivery group.
    '''
    mergeCNDG_lock.acquire()
    errorMsg = None
    result = None
    try:
        cnImageContentList = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber)
        cnProductContentList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber)
        cnPipelineContentList = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber)
        cndgContentList = list(chain(cnImageContentList, cnProductContentList, cnPipelineContentList))
        # validating all dg contents before merging
        result, comment, errorMsg = validateCNdgContentGerritList(cndgContentList, comment)
        if errorMsg:
            mergeCNDG_lock.release()
            return result, comment, errorMsg
        # Merging all dg contents
        result, count, comment, errorMsg = mergeCNdgContentGerritList(cndgContentList, comment)
        if errorMsg:
            mergeCNDG_lock.release()
            return result, comment, errorMsg
        if count == len(cndgContentList):
            result = "delivered"
        else:
            result = "queued"
        mergeCNDG_lock.release()
    except Exception as e:
        errorMsg = "<br /> UNEXPECTED ERROR: Failed to merge code changes for this delivery group. Please investigate: " + str(e) + " <br />"
        logger.error(errorMsg)
        comment += errorMsg
        mergeCNDG_lock.release()
        return 'FAILED', comment, errorMsg
    return result, comment, errorMsg

def validateCNdgContentGerritList(cndgContentList, comment):
    '''
    This function is validate all the contents of DG before merging.
    '''
    errorMsg = None
    result = None
    gerritUserName = config.get('CIFWK', 'cENMfunctionalUser')
    gerritPassword = config.get('CIFWK', 'cENMfunctionalUserPassword')
    gerritHostName = config.get('GERRIT_SSH', 'gerrit_hostname')
    for cndgContentObj in cndgContentList:
        cnGerritLink = cndgContentObj.cnGerrit.gerrit_link
        changeNum = cnGerritLink.split("/c/")[-1].replace("/", "")
        try:
            changeId = getChangeId(changeNum, gerritUserName, gerritPassword, gerritHostName)
        except Exception as e:
            changeIdErrorMsg = "<br /> ERROR: Failed to get changeId for " + cnGerritLink + " Please investigate: " + str(e) + " <br />"
            logger.error(changeIdErrorMsg)
            comment += changeIdErrorMsg
            return 'FAILED', comment, changeIdErrorMsg
        try:
            revisionId = getRevisionId(str(changeId), gerritUserName, gerritPassword, gerritHostName)
        except Exception as e:
            updatedErrorMsg = "<br /> ERROR: Failed to get revision id for " + cnGerritLink + " in CI Portal Please investigate: " + str(e) + " <br />"
            logger.error(updatedErrorMsg)
            comment += updatedErrorMsg
            return 'FAILED', comment, updatedErrorMsg
        try:
            verified, codeReview = getReview(str(changeId), str(revisionId), gerritUserName, gerritPassword, gerritHostName)
        except Exception as e:
            updatedErrorMsg = "<br /> ERROR: Failed to get review details for " + cnGerritLink + " in CI Portal Please investigate: " + str(e) + " <br />"
            logger.error(updatedErrorMsg)
            comment += updatedErrorMsg
            return 'FAILED', comment, updatedErrorMsg
        if not verified or not codeReview:
            errorMsg = "ERROR: GerritLink " + cnGerritLink + " is either not having +1 verified or +2 code-review"
            logger.error(errorMsg)
            comment += errorMsg
            return 'FAILED', comment, errorMsg
        try:
            mergeable = getMergeable(str(changeId), str(revisionId), gerritUserName, gerritPassword, gerritHostName)
        except Exception as e:
            updatedErrorMsg = "<br /> ERROR: Failed to get mergeable details for " + cnGerritLink + " in CI Portal Please investigate: " + str(e) + " <br />"
            logger.error(updatedErrorMsg)
            comment += updatedErrorMsg
            return 'FAILED', comment, updatedErrorMsg
        if not mergeable:
            try:
                statusCode, comment = rebaseChange(str(changeId), comment, gerritUserName, gerritPassword, gerritHostName)
                if statusCode != "200":
                    errorMsg = "ERROR: GerritLink " + cnGerritLink + " is not mergeable. Please check the comment for more info."
                    logger.error(errorMsg)
                    comment += errorMsg
                    return 'FAILED', comment, errorMsg
            except Exception as e:
                errorMsg = "<br /> ERROR: Failed to rebase gerrit : " + cnGerritLink + " in Gerrit. Please investigate: " + str(e) + " <br />"
                logger.error(errorMsg)
                comment += errorMsg
                return 'FAILED', comment, errorMsg
    return result, comment, errorMsg

def mergeCNdgContentGerritList(cndgContentList, comment):
    '''
    This function is to merging all the contents of the DG
    '''
    errorMsg = None
    result = None
    count = 0
    gerritUserName = config.get('CIFWK', 'cENMfunctionalUser')
    gerritPassword = config.get('CIFWK', 'cENMfunctionalUserPassword')
    gerritHostName = config.get('GERRIT_SSH', 'gerrit_hostname')
    commentCheckValue = "needs Verified; needs Code-Review"
    for cndgContentObj in cndgContentList:
        cnGerritLink = cndgContentObj.cnGerrit.gerrit_link
        changeNum = cnGerritLink.split("/c/")[-1].replace("/", "")
        try:
            changeId = getChangeId(changeNum, gerritUserName, gerritPassword, gerritHostName)
        except Exception as e:
            changeIdErrorMsg = "<br /> ERROR: Failed to get changeId for " + cnGerritLink + " Please investigate: " + str(e) + " <br />"
            changeId = None
            logger.error(changeIdErrorMsg)
            comment += changeIdErrorMsg
            return 'FAILED', count, comment, changeIdErrorMsg
        try:
            revisionId = getRevisionId(str(changeId), gerritUserName, gerritPassword, gerritHostName)
        except Exception as e:
            updatedErrorMsg = "<br /> ERROR: Failed to get revision id for " + cnGerritLink + " after rebasing the change. Please investigate: " + str(e) + " <br />"
            logger.error(updatedErrorMsg)
            comment += updatedErrorMsg
            return 'FAILED', count, comment, updatedErrorMsg
        try:
            statusCode, codeReviewErrorMsg = submitCodeReview(str(changeId), revisionId, gerritUserName, gerritPassword, gerritHostName)
            if statusCode != "200":
                logger.error(codeReviewErrorMsg)
                comment += codeReviewErrorMsg
                return 'FAILED', count, comment, codeReviewErrorMsg
        except Exception as e:
            updatedErrorMsg = "<br /> ERROR: Failed to submit code review with change id for " + cnGerritLink + " in CI Portal Please investigate: " + str(e) + " <br />"
            logger.error(updatedErrorMsg)
            comment += updatedErrorMsg
            return 'FAILED', count, comment, updatedErrorMsg
        try:
            statusCode, comment = submitChanges(str(changeId), comment, gerritUserName, gerritPassword, gerritHostName)
            if statusCode == "200":
                count += 1
            elif statusCode == "409" and commentCheckValue in comment:
                try:
                    statusCode, codeReviewErrorMsg = submitCodeReview(str(changeId), revisionId, gerritUserName, gerritPassword, gerritHostName)
                    if statusCode != "200":
                        logger.error(codeReviewErrorMsg)
                        comment += codeReviewErrorMsg
                        return 'FAILED', count, comment, codeReviewErrorMsg
                except Exception as e:
                    updatedErrorMsg = "<br /> ERROR: Failed to submit code review with change id for " + cnGerritLink + " in CI Portal Please investigate: " + str(e) + " <br />"
                    logger.error(updatedErrorMsg)
                    comment += updatedErrorMsg
                    return 'FAILED', count, comment, updatedErrorMsg
                try:
                    statusCode, comment = submitChanges(str(changeId), comment, gerritUserName, gerritPassword, gerritHostName)
                except Exception as e:
                    submissionErrorMsg = "<br /> ERROR: Failed to submit changes for " + cnGerritLink + " in Gerrit. Please investigate: " + str(e) + " <br />"
                    logger.error(submissionErrorMsg)
                    comment += submissionErrorMsg
                    return 'FAILED', count, comment, submissionErrorMsg
                if statusCode == "200":
                    count += 1
                else:
                    updatedErrorMsg = "<br /> ERROR: Failed to submit changes for " + cnGerritLink + " in CI Portal."
                    logger.error(updatedErrorMsg)
                    comment += updatedErrorMsg
                    return 'FAILED', count, comment, updatedErrorMsg
            else:
                updatedErrorMsg = "<br /> ERROR: Failed to submit changes for " + cnGerritLink + " in CI Portal."
                logger.error(updatedErrorMsg)
                comment += updatedErrorMsg
                return 'FAILED', count, comment, updatedErrorMsg
        except Exception as e:
            submissionErrorMsg = "<br /> ERROR: Failed to submit changes for " + cnGerritLink + " in Gerrit. Please investigate: " + str(e) + " <br />"
            logger.error(submissionErrorMsg)
            comment += submissionErrorMsg
            return 'FAILED', count, comment, submissionErrorMsg
    return result, count, comment, errorMsg

def getReview(changeId, revisionId, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is get if the commit is reviewed or not.
    '''
    verified = codeReview = False
    gerritUrl = "https://" + gerritHostName + "/a/changes/" + changeId + "/revisions/" + revisionId + "/review"
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.get(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    decodedJsonData = (response.content).decode("utf-8").replace(")]}\'", "")
    data = json.loads(decodedJsonData)
    verifiedAll =  data.get('labels').get('Verified').get('all')
    for verifiedValue in verifiedAll:
        if verifiedValue.get('value') == 1:
            verified = True
            break
    codeReviewAll =  data.get('labels').get('Code-Review').get('all')
    for codeReviewValue in codeReviewAll:
        if codeReviewValue.get('value') == 2:
            codeReview = True
            break
    return verified, codeReview

def getMergeable(changeId, revisionId, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is get if the commit is mergeable or not.
    '''
    gerritUrl = "https://" + gerritHostName + "/a/changes/" + changeId + "/revisions/" + revisionId + "/mergeable"
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.get(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    decodedJsonData = (response.content).decode("utf-8").replace(")]}\'", "")
    data = json.loads(decodedJsonData)
    mergeable = data.get('mergeable')
    return mergeable

def rebaseChange(changeId, comment, gerritUserName, gerritPassword, gerritHostName):
    '''
    This function is to rebase changes by changeId for a content in a DG.
    '''
    gerritUrl = "https://" + gerritHostName + "/a/changes/" + changeId + "/rebase"
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    response = requests.post(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword), verify=ssl_certs, timeout=120)
    statusCode = str(response.status_code)
    if statusCode == "409":
        comment += "<br />WARNING: This content can't be rebased. <br />" + response.content + " <br />"
    if statusCode != "409" and statusCode != "200":
        comment += "<br />ERROR: This content can't be rebased due to unexpected issue. Please investigate." + "error code from Gerrit: " + statusCode + " <br />"
    return statusCode, comment

def hideCNBuildLog(cnBuildlogId):
    '''
    This function updates the Buildlog active status for the particular cloud native build log id given.
    '''
    errorMsg = None
    try:
        try:
            cnBuildlogObj = CNBuildLog.objects.get(id=cnBuildlogId)
        except Exception as e:
            errorMsg = "Failed to update the active status for the buildlog id : " + str(cnBuildlogId) + ". Invalid Id"
            logger.error(errorMsg)
            return 1,errorMsg
        cnBuildlogObj.active = 0
        cnBuildlogObj.save(force_update=True)
    except Exception as e:
        errorMsg = "Unexpected error while updating active status for the buildlog id " + str(cnBuildlogId) + ". Please investigate the error: " + str(e)
        logger.error(errorMsg)
        return 1,errorMsg
    return "Active status updated successfully for the buildlog id : " + str(cnBuildlogId) , errorMsg
