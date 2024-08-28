import logging
from avs.models import *

logger = logging.getLogger(__name__)

class GenerateSkeleton:
    
    """Python class to generate the groovy & java test case classes for a given user story id
    
    Takes in a UserStory id (as a string) and generates the corresponding skeleton groovy & java test classes
    """
    
    def __init__(self):
        self.__fileMap = {"groovy" : '', "java":''}
        self.__IMPORT_FILES = [
        "import org.testng.annotations.Test",
        "import se.ericsson.jcat.fw.annotations.Setup",
        "import com.ericsson.cifwk.taf.TorTestCaseHelper",
        "import com.ericsson.cifwk.taf.exceptions.*",
        "import com.ericsson.cifwk.taf.tal.*",
        "import com.ericsson.cifwk.taf.exceptions.TestCaseNotImplementedException"
        ]
            
    def createFile(self,fileName):          
        for eachFileType in self.__fileMap:
            logger.debug('Creating %s skeleton file' %eachFileType)
            newFileName = '/tmp/%s.%s' %(fileName,eachFileType)
            logger.debug('%s skeleton filename = %s' %(eachFileType,newFileName))
            lineEnd = ''
            self.__fileMap['%s' %eachFileType]= newFileName
            logger.debug('Contents of fileMap: %s' %self.__fileMap)
            with open(newFileName, 'wb+') as destination:
                logger.debug ('Creating file %s for writing to, filename: %s' %(eachFileType,fileName))
                if eachFileType == 'java':
                    lineEnd =';'
                    logger.debug('This file will be a java file' )   
                destination.write('package com.ericsson.??%s \t\t//TODO Complete package\n\n' %lineEnd)
                for eachImport in self.__IMPORT_FILES:
                    destination.write('%s%s' %(eachImport,lineEnd))
                    destination.write('\n')
                destination.write("""\n/**\n *\t\t//TODO Add class javadoc\n */\n""")
        logger.debug('Exiting')
            
    def writeToFile(self, block):
        logger.debug('Contents of fileMap: %s' %self.__fileMap)
        for eachFileType in self.__fileMap:
            logger.debug('Writing to File Type: %s' %eachFileType)
            logger.debug('Block for writing BEFORE file type check: %s' %block)
            if eachFileType == 'groovy':
                logger.debug('Writing to a groovy file' ) 
                copyBlock = block.replace(';','')
                if copyBlock.strip().startswith('@'):
                    copyBlock = copyBlock.replace('{','[').replace('}',']')
            else: 
                copyBlock = block          
            newFileName = self.__fileMap['%s' %eachFileType]
            logger.debug('Writing to file: %s' %newFileName)
            logger.debug('Block for writing AFTER file type check: %s' %copyBlock)
            with open(newFileName, 'a') as destination:
                destination.write(copyBlock)
        logger.debug('Exiting')

             
    def generateSkeleton(self, storyName):
        userStory = UserStory.objects.get(name=storyName)
        testCaseList = TestCase.objects.filter(userStory=userStory.id).order_by('id')
        #//TODO - need to sort this out to cater for more that one component on an AVS
        component = testCaseList[0].component
        self.createFile(component)
        self.writeToFile("\nclass %s extends TorTestCaseHelper {\n\n" %component)
        for testCase in testCaseList:
            if testCase.pre:
                self.writeToFile('\tvoid prepareTestCaseFor%s(){' %testCase.title.replace(' ','_'))
                self.writeToFile('\n\t\t//TODO %s' %testCase.pre)
                self.writeToFile('\n\t}\n\n')
            self.writeToFile('\t/**\n')
            self.writeToFile('\t * %s\n' %testCase.title)
            self.writeToFile('\t * @DESCRIPTION %s\n' %testCase.desc)
            self.writeToFile('\t * @PRE %s\n' %testCase.pre)
            self.writeToFile('\t * @PRIORITY %s\n' %testCase.priority)
            self.writeToFile('\t */\n')
            if testCase.context:
                contextList = testCase.context.split(',')
                newlist=[]
                for each in contextList:
                    newlist.append('Context.' + each)
                newstring=','.join(newlist)
                self.writeToFile('\t@Context(context={%s})\n' %newstring)
            if testCase.vusers:
                self.writeToFile('\t@VUsers(vusers={%s})\n' %testCase.vusers)
            self.writeToFile('\t@Test(groups={"%s"})\n' %testCase.groups)
            #(groups = { "functest", "checkintest" })
            self.writeToFile('\tvoid %s(){\n' %testCase.title.replace(' ','_').replace('(','').replace(')',''))
            if testCase.pre:
                self.writeToFile('\n\t\tprepareTestCaseFor%s();\n\n' %testCase.title.replace(' ','_'))
            self.writeToFile('\t\tsetTestCase("%s","%s");\n\n' %(testCase.tcId,testCase.title))
            actionPointList = ActionPoint.objects.filter(testCase=testCase.id).order_by('id')
            for actionPoint in actionPointList:
                self.writeToFile('\t\tsetTestStep("Execute %s");\n' %(actionPoint.desc))
                self.writeToFile('\t\t//TODO %s\n\n' %(actionPoint.desc))
                verificationPointList = VerificationPoint.objects.filter(actionPoint=actionPoint.id).order_by('id')
                for verificationPoint in verificationPointList:
                    self.writeToFile('\t\tsetTestStep("Verify %s");\n' %(verificationPoint.desc))
                    self.writeToFile('\t\t//TODO %s\n\n' %(verificationPoint.desc))
            self.writeToFile('\t\tthrow new TestCaseNotImplementedException();\n')
            self.writeToFile('\t}\n\n')
        self.writeToFile('}\n')
        
        logger.debug('FileMap BEFORE translation: %s' %self.__fileMap)
        for eachFileType in self.__fileMap:
            self.__fileMap['%s' %eachFileType]= self.__fileMap['%s' %eachFileType].replace('/tmp/','')
        logger.debug('FileMap AFTER translation: %s' %self.__fileMap)
        return self.__fileMap

      
      
            
