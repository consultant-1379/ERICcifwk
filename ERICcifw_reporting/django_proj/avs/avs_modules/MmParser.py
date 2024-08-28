from xml.etree.ElementTree import ElementTree, tostring
import re
from django.db import transaction
import avs.avs_utils
from avs.models import *
import logging, os
from time import gmtime, strftime
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import MultipleObjectsReturned

logger = logging.getLogger(__name__)

class AvsValidator:

    def __init__(self):
        #logger.info("Validator started")
        #ejohlyn: should be pulling these options from the cirreports db rather then creating a list manually"
        #self.testTypes = ["Feature Tests", "Integration Tests", "Load Tests", "Performance Tests", "Robustness", "Security Tests"]
        self.testTypes = {"Functional Tests":"Func", "Performance Tests":"Perf", "Workflow Tests":"Work", "High Availability Tests":"High", 
                          "Scalability Tests":"Scal", "Robustness Tests":"Robu", "Security Tests":"Secu"}
        self.nonBlankFields = ["description","component","priority"]
        self.mandatoryFields = ["atc","context"] + self.nonBlankFields
        self.__errors = 0
        self.__response =[]
    
    def validateAvs(self, fileName):
        try:
            self.__mmParser = MmParser()
            self.__mmParser.parse(fileName)
            story = self.__mmParser.tree.find("node")
            storyNodeText = self.__mmParser.getText(story)
            if ':' in storyNodeText:
                userStory = storyNodeText.split(':',1)[1].strip()
            else:
                userStory = storyNodeText
            logger.info("Checking '%s' as Story: %s" %(userStory, self.__checkStoryNameFormat(story)))
            self.__response.append("Checking '%s' as Story: %s" % (userStory, self.__checkStoryNameFormat(story)))
        except:
            self.__errors +=1
            self.__response.append("Error validating this File. Check the file extension and try again.")
            return {'errors':self.__errors,'response':self.__response}


        
        #Check the database for the User Story
        dbResult=False
        try: 
            userStoryList = UserStory.objects.get(name=userStory)
            dbResult = False
            #self.__errors +=1
        except ObjectDoesNotExist:
            logger.info("**** Object Does Not Exist ****")
            dbResult = True
        except MultipleObjectsReturned:
            logger.info("****Multiple Objects Exist****")
            dbResult = True
        logger.info("Checking '%s' is not already in the database: %s" %(userStory, dbResult))
        self.__response.append("Checking '%s' is not already in the database: %s" %(userStory, dbResult))
        
        
        #Check That the User Story is a valid story in JIRA
        jiraResult = True
        jiraMessage = ' - '
        try:
            jsonResponse = avs.avs_utils.getJiraIdDetails(userStory)         
            if 'errorMessage' in jsonResponse.keys():
                jiraResult = False
                self.__errors +=1
                #jiraMessage += '%s does not exist in Jira ' %userStory
                jiraMessage += jsonResponse.get('errorMessage')
            if jsonResponse['jiraIssueIdType'] <> 'Story':
                jiraResult = False
                self.__errors +=1
                jiraMessage += '%s is not a valid User Story in Jira ' %userStory
            if jsonResponse['jiraIssueIdParent'] is None:
                jiraResult = False
                self.__errors +=1
                jiraMessage += '%s does not have a parent Epic in Jira ' %userStory
            else:
                jiraResult = True
        except Exception, error:
            logger.debug(error)
            jiraResult = False
            self.__errors +=1
            self.__response.append("Checking '%s' is not a valid User Story in JIRA: %s, %s" %(userStory, jiraResult, error)) 
        logger.info("Checking '%s' is a valid User Story in JIRA: %s %s" %(userStory, jiraResult,jiraMessage))
        self.__response.append("Checking '%s' is a valid User Story in JIRA: %s %s" %(userStory, jiraResult,jiraMessage))      
        logger.info('Mind Map File: %s' %story.getchildren()) 
        types = self.__mmParser.getSubNodes(story) 
        for testType in types:
            logger.info("Checking '%s' as Test Type: %s" % (self.__mmParser.getText(testType),self.__checkTypeNameFormatAndSupport(testType)))
            self.__response.append("Checking '%s' as Test Type: %s" % (self.__mmParser.getText(testType),self.__checkTypeNameFormatAndSupport(testType)))
        for testType in types:
            for testCase in self.__mmParser.getSubNodes(testType):
                logger.info("Checking '%s'" % (self.__mmParser.getText(testCase).replace("\n", "<Enter>")))
                logger.info("Title: %s" % (self.__checkTestCaseTitle(testCase)))
                logger.info("Mandatory fields: %s" % (self.__checkTestCaseMandatoryFields(testCase)))
                logger.info("Action Point (at list one expected): %s" % (self.__checkTestCaseActionPoint(testCase)))
                self.__response.append("Checking '%s'" % (self.__mmParser.getText(testCase).replace("\n", "<Enter>")))
                self.__response.append("Title: %s" % (self.__checkTestCaseTitle(testCase)))
                self.__response.append("Mandatory fields: %s" % (self.__checkTestCaseMandatoryFields(testCase)))
                self.__response.append("Action Point (at list one expected): %s" % (self.__checkTestCaseActionPoint(testCase)))
        versionResult = True
        if ':' in storyNodeText:
            storyVersion = "0"
            usDbVersion = "0"
            try:
                logger.info("Checking if the correct Version of the user story %s", userStory)
                storyVersion = storyNodeText.split(':',1)[0].strip()
                usObDb = UserStory.objects.filter(name=userStory).latest('version')
                logger.info('US Object returned: %s', usObDb)
                logger.info('MM Story Version %s', storyVersion)
                usDbVersion = usObDb.version
                logger.info('DB Story Version %s', usDbVersion)
            except:
                self.__errors +=1
                self.__response.append(" DoesNotExist: User Story %s matching query does not exist" %(userStory))
            if int(storyVersion) != int(usDbVersion):
                logger.info('MM Version doesn\'t match the current DB Version. You\'re not updating the correct Mind Map')
                self.__errors +=1
                versionResult = False
            logger.info("Latest Version of MindMap %s", versionResult)
            self.__response.append('Latest Version of %s MindMap: %s' %(userStory, versionResult))        
        if (self.__errors == 0):
            logger.info("No errors detected while validating mindmap")
            return {'errors':self.__errors,'response':self.__response}
        else:
            logger.info("%d error(s) detected while validation mindmap. Please review message and correct the file." % (self.__errors))
            logger.debug('Errors = %s' %self.__errors)
            logger.debug('Response = %s' %self.__response)
            self.__response.append("%d error(s) detected while validation mindmap. Please review message and correct the file." % (self.__errors))
            return {'errors':self.__errors,'response':self.__response}

    def checkChangeinMMandDB(self, importFileName,user,userStoryOb, story):
        logger.info('Checking Change Between DB and MM!')
        isUserStoryUpdated = 0
        storyNodeText = self.__mmParser.getText(story)
        testTypes = self.__mmParser.getSubNodes(story) 
        mmVersion = storyNodeText.split(':',1)[0].strip()
        dbVersion = userStoryOb.version
        if mmVersion < dbVersion:
            logger.error("MM Version is less than DB Version. The MM is out of date.")
            self.__errors +=1
            self.__response.append("MM Version is less than DB Version. The MM is out of date. Please Download the latest MM and re-import with the changes.")
            return {'errors':self.__errors,'response':self.__response}
        mmtcList = []
        testCaseList = avs.avs_utils.getTestCaseList(userStoryOb)
        for testType in testTypes:
            for testCases in self.__mmParser.getSubNodes(testType):
                 testCaseText = self.__mmParser.getText(testCases).split(':',1)
                 logger.info ('Test Case Text: %s' %self.__mmParser.getText(testCases))
                 testCaseId = testCaseText[0].strip()
                 mmtcList.append(testCaseId)                 
                 logger.info('Checking to see if the TC <%s> exists in the DB' %testCaseId)
                 try:
                     tcObjectDb = TestCase.objects.get(tcId=testCaseId)
                     logger.info('TC Object exists')
                     logger.info('Checking if TC Object in DB and MM are the same')
                     changeBoolean = self.checkChangeinTestCase(tcObjectDb, testCases, testCaseText)
                     if changeBoolean == 1:
                         return changeBoolean
                 except ObjectDoesNotExist:
                     logger.info('TC Object does not exist in DB. It is a New TC for US %s' %userStoryOb.name)
                     changeBoolean = 1
                     return changeBoolean
                 except MultipleObjectsReturned:
                     logger.info('Multiple TC Objects exist in DB for TC %s' %testCaseId)
                     logger.info('Getting latest TC Object')
                     tcObjectDb = TestCase.objects.filter(tcId=testCaseId).latest('revision')
                     changeBoolean = self.checkChangeinTestCase(tcObjectDb, testCases, testCaseText)
                     if changeBoolean == 1:
                         return changeBoolean            
        for testcase in testCaseList:
            if testcase.tcId in mmtcList:
                logger.info("TC Object %s exists in DB and MM" %testcase.tcId)
            else:
                logger.info("TC Object %s exists in DB but not the MM" %testcase.tcId)
                changeBoolean = 1
                return changeBoolean
                """"testCaseId = testCaseText[0].strip()
                     changeBoolean = 0
                     logger.info("Test Case from DB: %s" %testcase.tcId)
                     logger.info("Test Case from MM: %s" %testCaseId)
                     if testCaseId == testcase.tcId:
                         changeBoolean = self.checkChangeinTestCase(testcase, testCases, testCaseText)
                         logger.info('Change Boolean Value for Test Case %s is %s', testCaseId, changeBoolean)
                         if changeBoolean == 1:
                            return changeBoolean                        
                     else:
                         logger.info('To be Complete')
                         logger.info('Checking to see if the TC %s exists in the DB' %testCaseId)
                         try:
                             tcObjectDb = TestCase.objects.get(tcId=testCaseId)"""
        return changeBoolean
                     

    def checkChangeinTestCase(self, testcase, testCases, testCaseText):
        logger.debug('Test Case %s Already exists in DB' %testcase.tcId)
        logger.debug('Check If Test Case %s Attributes Match' %testcase.tcId)
        testCaseTitle = testCaseText[1].strip()
        if testCaseTitle == testcase.title:
            logger.info('Test Case Title %s has not changed for Test Case %s' ,testCaseTitle, testcase.tcId)
        else:
            changeBoolean = 1
            logger.info('Change Boolean Value Updated to %s due to TC Title' %changeBoolean)
            return changeBoolean
        testCaseAttributes = {}
        for eachTestCaseAttribute in self.__mmParser.getSubNodes(testCases):                
            logger.debug('Iterating over test case attributes, attribute = %s' %(self.__mmParser.getText(eachTestCaseAttribute)))
            kv =  self.__mmParser.getText(eachTestCaseAttribute).split(':', 1)
            if len(kv) != 2:
                logger.error("Only got " + str(len(kv)) + " parameters in " + eachTestCaseAttribute)
                self.__errors +=1
                self.__response.append("Only got " + str(len(kv)) + " parameters in " + eachTestCaseAttribute)

            else:
                #logger.info(eachTestCaseAttribute)
                key = kv[0].strip()
                value = kv[1].strip()
                logger.info('Key: %s' %key)
                logger.info('Value: %s' %value)
                testCaseAttributes[key] = value
                if key == 'EXECUTE':
                    actionPointList = ActionPoint.objects.filter(testCase=testcase)
                    apExists = 0
                    vpExists = 0
                    for ap in actionPointList:
                        logger.info('*****AP From MM: %s' %value)
                        logger.info('*****AP From DB: %s' %ap.desc)
                        if value == ap.desc:
                            logger.info('Action Point value is the same')
                            apExists = 1    
                        else:
                            logger.info('AP Values are Not the Same for TC %s', testcase.tcId)
                            changeBoolean = 1
                            return changeBoolean
                        vpList = VerificationPoint.objects.filter(actionPoint=ap)
                        for vp in vpList:
                            for eachVP in  self.__mmParser.getSubNodes(eachTestCaseAttribute):
                                eachVPValue = self.__mmParser.getText(eachVP).split(':', 1)[1].strip()
                                logger.info('*****VP From MM: %s' %eachVPValue)
                                logger.info('*****VP From DB: %s' %vp.desc)
                                if eachVPValue == vp.desc:
                                    logger.info('Verification Point %s value is the same' %ap)
                                    vpExists = 1
                                else:
                                    changeBoolean = 1
                                    return changeBoolean
        logger.info('Test Casee Attributes Keys: ' %testCaseAttributes.keys())
        if 'DESCRIPTION' in testCaseAttributes.keys():
            logger.info('Description Value from MM: %s' %testCaseAttributes['DESCRIPTION'])
            logger.info('Description Value from DB: %s' %testcase.desc)
            if testCaseAttributes['DESCRIPTION'] == testcase.desc:
                logger.info('Description Values are the Same')
            else: 
                changeBoolean = 1
                return changeBoolean
        else:   
            if testcase.desc == '':
                logger.info('Description Values are the Same')
            else:
                changeBoolean = 1
                return changeBoolean
        if 'COMPONENT' in testCaseAttributes.keys():
            try:
                logger.info('Component Value from DB: %s' %testcase.component)
                componentObj = Component.objects.get(name=testCaseAttributes['COMPONENT'])
                logger.info('Component Value from MM: %s' %componentObj)
                if componentObj == testcase.component:
                    logger.info('Component Value is the same')
                else:
                    changeBoolean = 1
                    return changeBoolean
            except ObjectDoesNotExist:
                logger.info('Component Value Does Not Exist')
                changeBoolean = 1
                return changeBoolean
        if 'PRIORITY' in testCaseAttributes.keys():
            logger.info('Priority Value from MM: %s' %testCaseAttributes['PRIORITY'])
            logger.info('Priority Value from DB: %s' %testcase.priority)
            if testCaseAttributes['PRIORITY'] == testcase.priority:
                logger.info('Priority Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        else:
            if testcase.priority == '':
                logger.info('Priority Value is the same')
            else: 
                changeBoolean = 1
                return changeBoolean
        if 'GROUP' in testCaseAttributes.keys():
            logger.info('Group from DB: %s' %testcase.groups)
            logger.info('GROUP Value from MM: %s' %testCaseAttributes['GROUP'])
            if testCaseAttributes['GROUP'] == testcase.groups:
                logger.info('Groups Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        else:
            if testcase.groups == '':
                logger.info('Groups Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        if 'PRE' in testCaseAttributes.keys():
            logger.info('PRE Value from MM: %s' %testCaseAttributes['PRE'])
            logger.info('PRE Value from DB: %s' %testcase.pre)
            if testCaseAttributes['PRE'] == testcase.pre:
                logger.info('Pre Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        else:
            if testcase.pre == '':
                logger.info('Pre Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        if 'VUSERS' in testCaseAttributes.keys():
            logger.info('VUsers Value from DB: %s' %testcase.vusers)
            logger.info('VUSERS Value from MM: %s' %testCaseAttributes['VUSERS'])
            if testCaseAttributes['VUSERS'] == testcase.vusers:
                logger.info('Vusers Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        else:
            if testcase.vusers == '':
                logger.info('Vusers Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        if 'CONTEXT' in testCaseAttributes.keys():
            logger.info('CONTEXT Value from MM: %s' %testCaseAttributes['CONTEXT'])
            logger.info('Context Value from DB: %s' %testcase.context)
            context = self.__cleanString(testCaseAttributes['CONTEXT'],',').upper()
            if context == testcase.context:
                logger.info('Vusers Value is the same')
            else:
                changeBoolean = 1
                return changeBoolean
        else:
            if testcase.context == '':
               logger.info('Vusers Value is the same')
            else:
               changeBoolean = 1
               return changeBoolean


    def createNewUserStoryObject(self, usObject, usVersion):
        newUserStory = ''
        try:
            logger.info('Creating New User Story Object for Existing US %s' %usObject.name)
            usEpic = usObject.epic
            usTitle = usObject.title
            usName = usObject.name     
            logger.info('new US being created with information: Name = %s, Title= %s, Epic = %s and Version = %s ',usName,usTitle,usEpic,usVersion)
            newUserStory = UserStory.objects.create(name=usName, title=usTitle, epic=usEpic, version=usVersion)
            logger.info('Successfully created')
            return newUserStory
        except Exception, error:
            logger.error('Exception %s' ,error)
            self.__response.append("Error in creating New User Story Object")
            return {'errors': error,'response':self.__response}


    def updateUserStoryInformation(self, importFileName,user,userStory, story):
        logger.info("Updating User Story %s Information" %userStory)
        #Check Test Types for Test Cases
        testTypes = ""
        usChangeBoolean = ""
        newuserStoryObject = ""
        try:
            testTypes = self.__mmParser.getSubNodes(story) 
            usChangeBoolean = self.checkChangeinMMandDB(importFileName,user,userStory, story)
            newuserStoryObject = userStory
        except Exception, error:
            self.__errors +=1
            self.__response.append("Error: %s , in Check Test Types for Test Cases and check if there was a change"%(error))

        if usChangeBoolean == 1:
            usObject = userStory
            usVersion = usObject.version
            usVersion += 1
            with transaction.commit_on_success():
                newuserStoryObject = self.createNewUserStoryObject(usObject, usVersion)
                logger.info('New US Object created is %s' %newuserStoryObject)
                logger.info('Now to check if new Test Cases need to be created')
                testTypes = self.__mmParser.getSubNodes(story)
                testCaseList = avs.avs_utils.getTestCaseList(usObject)
                mmtcList = []
                for testType in testTypes:
                    archive = 0
                    for testCases in self.__mmParser.getSubNodes(testType):
                        testCaseText = self.__mmParser.getText(testCases).split(':',1)
                        testCaseId = testCaseText[0].strip()
                        mmtcList.append(testCaseId)
                        try:
                            tcObjectDb = TestCase.objects.get(tcId=testCaseId)
                            logger.info('TC Object exists')
                            changeBoolean = self.checkChangeinTestCase(tcObjectDb, testCases, testCaseText)
                            if changeBoolean == 1:
                                newTCObject = self.createNewTC(newuserStoryObject, testCases,archive,testType,testCaseId, tcObjectDb)
                                result = TestCaseUserStoryMapping.objects.create(
                                        user_story = newuserStoryObject,
                                        test_case = newTCObject
                                        )
                            else:
                                logger.info('Code to Map Existing TC to new US in USTCMapping Table')
                                try:
                                    result = TestCaseUserStoryMapping.objects.create(
                                            user_story = newuserStoryObject,
                                            test_case = tcObjectDb
                                            )
                                except Exception, error:
                                    self.__errors +=1
                                    logger.error('Uh Oh: %s', error)
                                    self.__response.append("Error: %s, in Mapping Existing TestCase Code to new User Story in USTCMapping Table" %(error))
                        except ObjectDoesNotExist:
                            logger.info('TC Object does not exist in DB. It is a New TC for US %s' %newuserStoryObject)
                            tempOb = ''
                            newTCObject = self.createNewTC(newuserStoryObject, testCases, archive,testType,tempOb, tempOb)
                            result = TestCaseUserStoryMapping.objects.create(
                                     user_story = newuserStoryObject,
                                     test_case = newTCObject
                                     )
                        except MultipleObjectsReturned:
                            logger.info('Multiple TC Objects exist in DB for TC %s' %testCaseId)
                            tcObjectDb = TestCase.objects.filter(tcId=testCaseId).latest('revision')
                            changeBoolean = self.checkChangeinTestCase(tcObjectDb, testCases, testCaseText)
                            if changeBoolean == 1:
                                newTCObject = self.createNewTC(newuserStoryObject, testCases, archive,testType, testCaseId, tcObjectDb)
                                result = TestCaseUserStoryMapping.objects.create(
                                        user_story = newuserStoryObject,
                                        test_case = newTCObject
                                        )
                            else:
                                logger.info('Code to Map Existing TC to new US in USTCMapping Table')
                                result = TestCaseUserStoryMapping.objects.create(
                                        user_story = newuserStoryObject,
                                        test_case = tcObjectDb
                                        )                                    
                for testcase in testCaseList:
                    if testcase.tcId in mmtcList:
                        logger.info("TC Object %s exists in DB and MM" %testcase.tcId)
                    else:                            
                        logger.info("TC Object %s exists in DB but not the MM" %testcase.tcId)
                        archive = 1
                        logger.info("Need to Update the TC and set Archive to 1")
                        TestCase.objects.select_related().filter(id=testcase.id).update(archived='1')
                        #result = self.createNewTC(newuserStoryObject, testCases, archive)
        else:
            logger.info('US Information is exactly the same as before')
        return {'errors':self.__errors,'response':self.__response,'userStory':newuserStoryObject} 


    def createNewTC(self,newuserStoryObject, testCases, archive, testType, testCaseId, tcObjectDb):
        #logger.debug('Just before iterating over list of test types')
        #with transaction.commit_on_success():
        #for testType in testTypes: 
        try:
            logger.info('Test Type = %s', self.__mmParser.getText(testType))
            dateCreated = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            logger.info('DateCreated : %s', dateCreated)
            lastUpdated = ""      
            logger.info('LastUpdated : %s', lastUpdated) 
            type = self.testTypes['%s' %self.__mmParser.getText(testType)]
            logger.info('Test Case Type: %s', type)
            if testCaseId == '':
                num = self.__getNextTestCaseNo(newuserStoryObject.name + '_' + type)
                tcId = newuserStoryObject.name + '_' + type + '_' + str(num)
                title  = self.__mmParser.getText(testCases)
                revision = 1
                dateCreated = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                lastUpdated = None
            else:
                tcId = testCaseId
                testCaseText = self.__mmParser.getText(testCases).split(':', 1)
                title = testCaseText[1].strip()
                revision = tcObjectDb.revision
                revision +=1
                dateCreated = tcObjectDb.dateCreated
                lastUpdated = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            logger.info('DateCreated : %s', dateCreated)
            logger.info('LastUpdated : %s', lastUpdated)
            logger.info('Test Case Id: %s', testCaseId)
            logger.info('Test Case Title: %s', title)
            logger.info('Test Case Revision: %s', str(revision))
            logger.info('Test Case UserStory: %s', newuserStoryObject)
            archived = 0
            logger.info('Test Case archived = %s', archived)
        except:
            self.__errors +=1
            self.__response.append("Error in importing this File: %s" %(newuserStoryObject))
            return {'errors':self.__errors,'response':self.__response}
        testCaseAttributes= {}
        for eachTestCaseAtrribute in self.__mmParser.getSubNodes(testCases):
            logger.debug('Iterating over test case attributes, attribute = %s' %(self.__mmParser.getText(eachTestCaseAtrribute)))
            kv =  self.__mmParser.getText(eachTestCaseAtrribute).split(':', 1)
            if len(kv) != 2:
                self.__errors +=1
                logger.error("Only got " + str(len(kv)) + " parameters in " + eachTestCaseAtrribute)
            else:
                #logger.info(eachTestCaseAtrribute)
                key = kv[0].strip()
                value = kv[1].strip()
                testCaseAttributes[key] = value
        if 'DESCRIPTION' in testCaseAttributes.keys():
            desc = testCaseAttributes['DESCRIPTION']
        else:
            desc = ''
        logger.info('Test Case Desc: %s', desc)
        if 'COMPONENT' in testCaseAttributes.keys():
            component = testCaseAttributes['COMPONENT']
        else:
            component = ''
        logger.info('Test Case Component: %s', component)
        if 'PRIORITY' in testCaseAttributes.keys():
            priority = testCaseAttributes['PRIORITY']
        else:
            priority = ''
        logger.info('Test Case Priority: %s', priority)
        if 'GROUP' in testCaseAttributes.keys():
            groups = testCaseAttributes['GROUP']
        else:
            groups = ''
        logger.info('Test Case Groups: %s', groups)
        if 'PRE' in testCaseAttributes.keys():
            pre = testCaseAttributes['PRE']
        else:
            pre = ''
        logger.info('Test Case Pre: %s', pre)
        if 'VUSERS' in testCaseAttributes.keys():
            vusers = testCaseAttributes['VUSERS']
        else:
            vusers = ''
        logger.info('Test Case Vusers: %s', vusers)
        if 'CONTEXT' in testCaseAttributes.keys():
            context = self.__cleanString(testCaseAttributes['CONTEXT'],',').upper()
        else:
            context = ''
        logger.info('Test Case Context: %s ', context)
        # save the component if required and get a reference to it
        compObj, created = Component.objects.get_or_create(name=component)
        #Save a new instance of a Test Case
        logger.debug('creating testcase %s' %tcId)
        newTestCase = TestCase.objects.create(
            dateCreated = dateCreated,
            lastUpdated = lastUpdated,
            type        = type,
            tcId        = tcId,
            title       = title,
            revision    = revision,
            desc = desc,
            component = compObj,
            priority = priority,
            groups = groups,
            pre = pre,
            vusers = vusers,
            context = context,
            archived = archived
            )
        logger.debug('looking at test case attribures')
        for eachTestCaseAtrribute in self.__mmParser.getSubNodes(testCases):
            logger.debug('attribute = %s' %eachTestCaseAtrribute)            
            key = self.__mmParser.getText(eachTestCaseAtrribute).split(':')[0]
            value = self.__mmParser.getText(eachTestCaseAtrribute).split(':', 1)[1].strip()
            if key == 'EXECUTE':
                newActionPoint = ActionPoint.objects.create(desc=value,testCase=newTestCase)
                for eachVerificationPoint in  self.__mmParser.getSubNodes(eachTestCaseAtrribute):
                    newVerificationPoint = VerificationPoint.objects.create(desc=self.__mmParser.getText(eachVerificationPoint).split(':', 1)[1].strip(),actionPoint=newActionPoint)
                    logger.debug('finished testCase = %s' %newTestCase)
                    logger.debug('finished testType = %s' %testType)
        return newTestCase            
    
    def importAvs(self,importFileName,user):
        logger.debug("Starting")
        try:
            self.__errors = 0
            self.__response =[]
            self.__mmParser = MmParser()
            self.__mmParser.parse(importFileName)
            story = self.__mmParser.tree.find("node")
            if ':' in self.__mmParser.getText(story):
                userStory =  self.__mmParser.getText(story).split(':',1)[1].strip()
            else:
                userStory =  self.__mmParser.getText(story).strip()
                # Additions as part of CIP-1030
            logger.info('Looking for User Story %s Entry in DB' %userStory)
        except:
            self.__errors +=1
            self.__response.append("Error in importing this File: %s" %(importFileName))
            return {'errors':self.__errors,'response':self.__response}

        #result = ''
        try:
            #userStoryDetails = UserStory.objects.filter(name=userStory)
            logger.info('In the TRY Block')
            userStoryId = UserStory.objects.get(name=userStory)
            logger.info('US Version %s' %userStoryId.version)
            #result = {'userStory':userStoryId,'errors':0 }
            logger.info('User Story Already exists')
            logger.info('Checking to Compare if User Story was updated')
            result = self.updateUserStoryInformation(importFileName,user,userStoryId,story)
            #logger.info('Epic Id:%s and UserStory Id:%s  were saved successfully',newEpic,newUserStory)
        except ObjectDoesNotExist:
            logger.info('User Story %s Does Not Exist and Will need to be created' %userStory)
            result = self.createNewUserStory(importFileName,user,userStory, story)
            #logger.info('Epic Id:%s and UserStory Id:%s  were saved successfully',newEpic,newUserStory)
        except MultipleObjectsReturned:
            logger.info('User Story %s has Multiple entries in DB' %userStory)
            #userStoryDetails = UserStory.objects.latest('version').filter(name=userStoryId)
            latestUSObject = UserStory.objects.filter(name=userStory).latest('version')
            result = self.updateUserStoryInformation(importFileName,user,latestUSObject,story)
            #logger.info('Returned US Version is %s' %result.version)
        return result
        
        
    def createNewUserStory(self, importFileName,user,userStory, story):
        logger.info('Importing details for UserStory: %s', userStory )
        logger.info ('Starting Transaction!')
        with transaction.commit_on_success():
            #Saving Epic and UserStory details
            try:
                result = self.__saveUserStoryAndEpic(userStory)
                newEpic = result['epic']
                newUserStory = result['userstory']
                logger.info('New Epic %s' %newEpic)
                logger.info('New US %s' %newUserStory)
            except:
                logger.debug(" Error in Saving Epic and User Story details" )
                self.__errors =+ 1
                self.__response.append(" Error in Saving Epic and User Story details" )
                
            #Save AVSFile
            try:
                newAVSFile = self.__saveAVS_File(importFileName.strip(),user)
            except:
                logger.debug(" Error in Saving AVS File")
                self.__errors =+ 1
                self.__response.append(" Error in Saving AVS File" )

            #Save AVS
            try:
                newAVS = self.__saveAVS(newAVSFile,userStory,user)
            except:
                logger.debug(" Error in Saving AVS")
                self.__errors =+ 1
                self.__response.append(" Error in Saving AVS" )

            #Check Test Types for Test Cases
            testTypes = self.__mmParser.getSubNodes(story) 
            logger.debug('Just before iterating over list of test types')
            for testType in testTypes:
                logger.debug('starting testType = %s' %testType)
                for testCase in self.__mmParser.getSubNodes(testType):
                    logger.debug('starting testCase = %s' %testCase)
                    logger.info('**************** New Test Case **********************')
                    logger.info('Test Type = %s', self.__mmParser.getText(testType))
                    logger.info('Test Case = %s', self.__mmParser.getText(testCase))
                    dateCreated = strftime("%Y-%m-%d %H:%M:%S", gmtime()) 
                    logger.info('DateCreated : %s', dateCreated)
                    lastUpdated = ""
                    logger.info('LastUpdated : %s', lastUpdated)
                    type        = self.testTypes['%s' %self.__mmParser.getText(testType)]
                    logger.info('Test Case Type: %s', type)
                    num = self.__getNextTestCaseNo(userStory + '_' + type)
                    tcId        = userStory + '_' + type + '_' + str(num) 
                    logger.info('Test Case Id: %s', tcId)
                    title       = self.__mmParser.getText(testCase).strip()
                    logger.info('Test Case Title: %s', title)
                    revision    = 1
                    logger.info('Test Case Revision: %s', str(revision))
                    newuserStory   = newUserStory
                    logger.info('Test Case UserStory: %s', newuserStory)
                    archived = 0
                    logger.info('Test Case archived: %s', archived)
                    testCaseAttributes= {}
                    for eachTestCaseAtrribute in self.__mmParser.getSubNodes(testCase):
                        logger.debug('Iterating over test case attributes, attribute = %s' %(self.__mmParser.getText(eachTestCaseAtrribute)))
                        kv =  self.__mmParser.getText(eachTestCaseAtrribute).split(':', 1)
                        if len(kv) != 2:
                            logger.error("Only got " + str(len(kv)) + " parameters in " + eachTestCaseAtrribute)
                            self.__errors =+ 1
                            self.__response.append("Only got " + str(len(kv)) + " parameters in " + eachTestCaseAtrribute )

                        else:
                            logger.info(eachTestCaseAtrribute)
                            key = kv[0].strip()
                            value = kv[1].strip()
                            testCaseAttributes[key] = value
     
                    if 'DESCRIPTION' in testCaseAttributes.keys():
                        desc = testCaseAttributes['DESCRIPTION']
                    else:
                        desc = ''
                    logger.info('Test Case Desc: %s', desc) 
               
                    if 'COMPONENT' in testCaseAttributes.keys():
                       component = testCaseAttributes['COMPONENT']
                    else:
                        component = ''
                    logger.info('Test Case Component: %s', component)
    
                    if 'PRIORITY' in testCaseAttributes.keys():
                        priority = testCaseAttributes['PRIORITY']
                    else:
                        priority = ''
                    logger.info('Test Case Priority: %s', priority)

                    if 'GROUP' in testCaseAttributes.keys():
                        groups = testCaseAttributes['GROUP']
                    else:
                        groups = ''
                    logger.info('Test Case Groups: %s', groups)
                    if 'PRE' in testCaseAttributes.keys():
                        pre = testCaseAttributes['PRE']
                    else:
                        pre = ''
                    logger.info('Test Case Pre: %s', pre)                
    
                    if 'VUSERS' in testCaseAttributes.keys():
                        vusers = testCaseAttributes['VUSERS']
                    else:
                        vusers = ''
                    logger.info('Test Case Vusers: %s', vusers)
        
                    if 'CONTEXT' in testCaseAttributes.keys():
                        context = self.__cleanString(testCaseAttributes['CONTEXT'],',').upper()
                    else:
                        context = ''
                    logger.info('Test Case Context: %s ', context)
                    # save the component if required and get a reference to it
                    compObj, created = Component.objects.get_or_create(name=component)
                    
                    #Save a new instance of a Test Case
                    logger.debug('creating testcase %s' %tcId)
                    newTestCase = TestCase.objects.create(
                        dateCreated = dateCreated,
                        #lastUpdated = "",
                        type        = type,
                        tcId        = tcId,
                        title       = title,
                        revision    = 1,                        
                        desc = desc,
                        component = compObj,
                        priority = priority,
                        groups = groups,
                        pre = pre,
                        vusers = vusers,
                        context = context,
                        archived = archived
                        )

                    logger.debug('looking at test case attribures')
                    for eachTestCaseAtrribute in self.__mmParser.getSubNodes(testCase):
                        logger.debug('attribute = %s' %eachTestCaseAtrribute)
                        key = self.__mmParser.getText(eachTestCaseAtrribute).split(':')[0]
                        value = self.__mmParser.getText(eachTestCaseAtrribute).split(':', 1)[1].strip()
                        if key == 'EXECUTE':
                            newActionPoint = ActionPoint.objects.create(desc=value,testCase=newTestCase)
                            for eachVerificationPoint in  self.__mmParser.getSubNodes(eachTestCaseAtrribute):
                               newVerificationPoint = VerificationPoint.objects.create(desc=self.__mmParser.getText(eachVerificationPoint).split(':', 1)[1].strip(),actionPoint=newActionPoint)
                    logger.debug('finished testCase = %s' %testCase)
                    newTCUSMapping =  TestCaseUserStoryMapping.objects.create(
                            user_story = newUserStory,
                            test_case = newTestCase
                            )
                logger.debug('finished testType = %s' %testType)
        return {'errors':self.__errors,'response':self.__response,'userStory':newUserStory}
    
    def saveUserStoryAndEpic(self,storyName):
        #Saving Epic and UserStory details 
        result = self.__saveUserStoryAndEpic(storyName)
        return result

    def __getNextTestCaseNo(self,searchstring):
        resultList = TestCase.objects.filter(tcId__startswith=searchstring)
        if len(resultList)>0:
            list = [] 
            for each in resultList:
                list.append(each.tcId)
            maxNum = 0
            for each in list:
                if int(each.split('_')[2]) > maxNum:
                    maxNum = int(each.split('_')[2])
            return maxNum + 1
        else:
            return 001
    
    def __saveUserStoryAndEpic(self,userStory): 
        logger.debug('Starting')
        result = avs.avs_utils.getJiraIdDetails(userStory)
            #{"jiraIssueId": jiraIssueId, "jiraIssueIdType":jiraIssueIdType, "jiraIssueIdTitle":jiraIssueIdTitle, "jiraIssueIdParent":jiraIssueIdParent}
            #result["jiraIssueId"]
            #logger.info(result)
        #logger.info(result)
        if 'errorMessage' in result.keys():
            logger.info('Error: %s', result['errorMessage'])
        else:
            userStoryId = result["jiraIssueId"]
            userStoryType = result["jiraIssueIdType"]
            userStoryTitle = result["jiraIssueIdTitle"]
            userStoryParentId = result["jiraIssueIdParent"]
            result = avs.avs_utils.getJiraIdDetails(userStoryParentId)
            userStoryPatenType = result["jiraIssueIdType"]
            userStoryParentTitle = result["jiraIssueIdTitle"]
            #Log info retrieved from JIRA to log file
            logger.info('UserStory Id: %s' % userStoryId)
            logger.info('Userstory Type: %s' % userStoryType)
            logger.info('UserStory Title: %s' % userStoryTitle)
            logger.info('UserStory Parent Id: %s' % userStoryParentId)
            logger.info('Userstory Parent Type: %s' % userStoryPatenType)
            logger.info('UserStory Parent Title:  %s' %userStoryParentTitle)
           
            try:
                logger.info('Saving Epic details')
                try:
                    newEpic = Epic.objects.get(name=userStoryParentId)
                except Epic.DoesNotExist:
                    logger.info('Epic not found in database, will create %s' %userStoryParentId)
                    newEpic = Epic(name=userStoryParentId, title = userStoryParentTitle)
                    newEpic.save()
                logger.info('Saving UserStory details')
                newUserStory = UserStory.objects.create(name=userStoryId, title=userStoryTitle, epic=newEpic, version=1)
                logger.info('Epic Id:%s and UserStory Id:%s  were saved successfully',newEpic,newUserStory)
            except Exception, error:
                logger.error('Exception: %s', error )
        return {'epic':newEpic,'userstory':newUserStory}

    def __saveAVS_File(self,importFileName,user): 
        logger.info('Saving AVSFile')
        try:
            logger.info('Reading file content')
            newfileContent = open(importFileName, 'r').read()
        except Exception, error:
            logger.info('Exception: %s', error)
        try:
            newAVSFile = AVSFile.objects.create(dateCreated = strftime("%Y-%m-%d %H:%M:%S", gmtime()),
                fileName=importFileName, fileContent= newfileContent, owner=user) 
        except Exception, error:
            logger.info('Exception: %s', error)
        logger.info('AVSFile ID:%s successfully created', newAVSFile)
        return newAVSFile
    
    def __saveAVS(self,newAVSFile,userStoryId,user): 
        logger.info('Saving AVS')
        newAVS = AVS.objects.create(dateCreated=strftime("%Y-%m-%d %H:%M:%S", gmtime()), avsId=userStoryId, owner=user,
                avsFile=newAVSFile, revision=1)
        logger.info('AVS Id:%s successfully saved', newAVS)
        return newAVS
        
    def __cleanString(self,strToBeCleaned,seperator):
        stringAsList = strToBeCleaned.split(seperator)
        stringAsCleanedList = []
        for each in stringAsList:
            stringAsCleanedList.append(each.strip())
        return seperator.join(stringAsCleanedList)   

    
    def __validateNode(self,node,rule,ignoreCase=0):
        return self.__mmParser.checkNodeWithRe(node, rule, ignoreCase)
            
   
    def __checkStoryNameFormat(self,story):  
        return self.__validateNode(story, ".*-[0-9]*") 
        
   
    def __checkTypeNameFormatAndSupport(self,testType):
        #return self.__validateNode(testType,".*\ Tests") and self.__mmParser.getText(testType) in self.testTypes   
        logger.debug(self.__mmParser.getText(testType))
        if self.__mmParser.getText(testType) in self.testTypes.keys():
            return True
        else:
            self.__errors += 1
            return False

    
    def __checkTestCaseTitle(self,testCase):
        incorrectResult = 0
        for incorrectBeggining in self.mandatoryFields:
            incorrectResult += self.__validateNode(testCase,"^"+incorrectBeggining , 1)
        self.__errors += incorrectResult
        return incorrectResult == 0
   

    def __checkTestCaseMandatoryFields(self,testCase):
        incorrectResult = 0
        for field in self.nonBlankFields:
            if (self.__mmParser.getSubNodeStartingWithText(testCase, field + ":", 1) == None):
                incorrectResult += 1
                logger.info("Test Case '" + self.__mmParser.getText(testCase) + "' does not contain mandatory field '" + field + "'")
        self.__errors += incorrectResult           
        return incorrectResult == 0
   

    def __checkTestCaseActionPoint(self,testCase):
        for field in self.__mmParser.getSubNodes(testCase):
            if (field.tag == "node"):
                for mandatoryField in self.mandatoryFields:
                    if (not self.__validateNode(field, "^"+mandatoryField, 1)):
                        return True
        self.__errors += 1
        return False



class MmParser:
    
    def parse(self,fileName):
        self.tree = ElementTree()
        self.tree.parse(fileName)
   

    def getText(self,node,nodeTag="node"):
        if node.tag == "arrowlink" or node.tag == "font":
            return ""
        if "TEXT" in node.attrib:
            return node.attrib["TEXT"]
        else: 
            delParsingTag = "TODELETEPARSINGTAG"
            if (node.tag != "richcontent"):
                richContent =  re.sub("<.*>",delParsingTag,tostring(node.find("richcontent")))
            else:
                richContent = re.sub("<.*>",delParsingTag,tostring(node))
            result = ""
            for i in richContent.splitlines():
                if (i.strip() != delParsingTag):
                    result += i.strip() +"\n"      
            return re.sub("\n$","",result)
   

    def getSubNodes(self,node):
        subs = []
        for n in node.getchildren():
            if n.tag != "node":
                logger.warning("Found invalid tag: " + n.tag)
            else:
                subs.append(n)
        return subs
   

    def checkNodeWithRe(self,node,rule,ignoreCase=0):
        logger.error("Checking " + self.getText(node) + " against rule " + rule)
        if ignoreCase:
            return re.match(rule, self.getText(node).lower()) != None 
        else:
            match = re.match(rule, self.getText(node))
            if match is not None:
                # TODO: what is the group for???
                return match.group() != None
            else:
                return False
         
    def getSubNodeStartingWithText(self,node,text,ignoreCase=0):
        for subNode in self.getSubNodes(node):
            if (self.checkNodeWithRe(subNode, "^"+text, ignoreCase)):
                return subNode 
