from avs.models import *
from ciconfig import CIConfig
import avs.avs_utils

from django.core import serializers
import urllib

config = CIConfig()

import logging
logger = logging.getLogger(__name__)

def formatBlock(block, fileType):
    logger.debug('Block for writing BEFORE file type check: %s' %block)
    copyBlock = block
    if fileType == 'groovy':
        logger.debug('Writing to a groovy file' )
        copyBlock = block.replace(';','')
        if copyBlock.strip().startswith('@'):
            copyBlock = copyBlock.replace('{','[').replace('}',']')
    return copyBlock

def exportTestcasesToXML(storyName):
    logger.info("XML Export for Story Name: %s", storyName)
    userStory = UserStory.objects.filter(name=storyName).latest('version')
    logger.info("Story Version is: %s", userStory.version)
    XMLSerializer = serializers.get_serializer("xml")
    xml_serializer = XMLSerializer()
    response = []
    tcusObject = TestCaseUserStoryMapping.objects.filter(user_story=userStory).filter(test_case__archived='0')
    for tcusOb in tcusObject:
        response.append(tcusOb.test_case)
        logger.info("TC appended is: %s", tcusOb.test_case.id)
        actionPointList = ActionPoint.objects.filter(testCase=tcusOb.test_case).order_by('id')
        for actionPoint in actionPointList:
            logger.debug("Adding a AP from the AP list ..")
            response.append(actionPoint)            
            verificationPointList = VerificationPoint.objects.filter(actionPoint=actionPoint.id).order_by('id')
            for verificationPoint in verificationPointList:
                logger.debug("Adding a VP from the VP list ..")
                response.append(verificationPoint)
    componentList = Component.objects.filter().order_by('id')
    for component in componentList:
        response.append(component)
    return xml_serializer.serialize(response)

def getSkeletonFromAVS(packageName, storyName):
    url = config.get("AVS", "rest_url")
    logger.info("Rest Url: %s" %url)
    # curl -i -X POST -d packagename="com.ericsson.cifwk.example" -d xmlfile="<lame/>" http://atrcx1933vm9.athtem.eei.ericsson.se:8080/avs-rest-service-0.1/skeleton      

    # xmlfile = exportTestcasesToXML(storyName)

    xmlfile = avs.avs_utils.getUserStoryMindMap(storyName)

    logger.info("Attempting to export XML as Java: " + xmlfile)
    params = urllib.urlencode({
       'packagename' : packageName,
       'xmlfile': xmlfile
       })

    data = urllib.urlopen(url, params)
    if data.getcode() == 200:
        return data.read()
    elif data.getcode() == 500:
        return "Internal server error on AVS REST service. Please contact the administrator."
    return "ERROR: " + str(data.getcode())


def generateSkeleton(storyName, fileType):
    logger.debug("Got an unknown file type: " + fileType)
    if fileType == "zip":
        return getSkeletonFromAVS("com.ericsson.sut", storyName)
    elif fileType == "mm":
        return avs.avs_utils.getUserStoryMindMap(storyName)
    else:
        logger.info("Got an unknown file type: " + fileType)
        userStory = UserStory.objects.filter(name=storyName).latest('version')        
        testCaseList = TestCaseUserStoryMapping.objects.filter(user_story=userStory).filter(test_case__archived='0')
 #//TODO - need to sort this out to cater for more that one component on an AVS
        component = testCaseList[0].test_case.component
        output = ""
        importFiles = [
             "org.testng.annotations.Test",
             "se.ericsson.jcat.fw.annotations.Setup",
             "com.ericsson.cifwk.taf.TorTestCaseHelper",
             "com.ericsson.cifwk.taf.exceptions.*",
             "com.ericsson.cifwk.taf.tal.*",
             "com.ericsson.cifwk.taf.exceptions.TestCaseNotImplementedException"
             ]
        for f in importFiles:
            output += formatBlock("\nimport " + f, fileType)
        output += formatBlock("\n\nclass %s extends TorTestCaseHelper {\n\n" %component, fileType)
        for tc in testCaseList:
            testCase = tc.test_case
            if testCase.pre:
                output += formatBlock('\tvoid prepareTestCaseFor%s(){' %testCase.title.replace(' ','_'), fileType)
                output += formatBlock('\n\t\t//TODO %s' %testCase.pre, fileType)
                output += formatBlock('\n\t}\n\n', fileType)
            output += formatBlock('\t/**\n', fileType)
            output += formatBlock('\t * %s\n' %testCase.title, fileType)
            output += formatBlock('\t * @DESCRIPTION %s\n' %testCase.desc, fileType)
            output += formatBlock('\t * @PRE %s\n' %testCase.pre, fileType)
            output += formatBlock('\t * @PRIORITY %s\n' %testCase.priority, fileType)
            output += formatBlock('\t */\n', fileType)
            if testCase.context:
                contextList = testCase.context.split(',')
                newlist=[]
                for each in contextList:
                    newlist.append('Context.' + each)
                newstring=','.join(newlist)
                output += formatBlock('\t@Context(context={%s})\n' %newstring, fileType)
            if testCase.vusers:
                output += formatBlock('\t@VUsers(vusers={%s})\n' %testCase.vusers, fileType)
            output += formatBlock('\t@Test(groups={"%s"})\n' %testCase.groups, fileType)
            #(groups = { "functest", "checkintest" })
            output += formatBlock('\tvoid %s(){\n' %testCase.title.replace(' ','_').replace('(','').replace(')',''), fileType)
            if testCase.pre:
                output += formatBlock('\n\t\tprepareTestCaseFor%s();\n\n' %testCase.title.replace(' ','_'), fileType)
            output += formatBlock('\t\tsetTestCase("%s","%s");\n\n' %(testCase.tcId,testCase.title), fileType)
            actionPointList = ActionPoint.objects.filter(testCase=testCase.id).order_by('id')
            for actionPoint in actionPointList:
                output += formatBlock('\t\tsetTestStep("Execute %s");\n' %(actionPoint.desc), fileType)
                output += formatBlock('\t\t//TODO %s\n\n' %(actionPoint.desc), fileType)
                verificationPointList = VerificationPoint.objects.filter(actionPoint=actionPoint.id).order_by('id')
                for verificationPoint in verificationPointList:
                    output += formatBlock('\t\tsetTestStep("Verify %s");\n' %(verificationPoint.desc), fileType)
                    output += formatBlock('\t\t//TODO %s\n\n' %(verificationPoint.desc), fileType)
            output += formatBlock('\t\tthrow new TestCaseNotImplementedException();\n', fileType)
            output += formatBlock('\t}\n\n', fileType)
        output += formatBlock('}\n', fileType)
        return output

