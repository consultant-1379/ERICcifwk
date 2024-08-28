import logging
logger = logging.getLogger(__name__)

from avs.models import *
import avs.avs_modules.MmParser  as AvsValidator
import avs.avs_modules.JiraRest  as JiraRest
import avs.avs_modules.GenerateSkeleton as GenerateSkeleton
import traceback
import xml.etree.ElementTree as xml

def validateAvs(filename):
    myValidator = AvsValidator.AvsValidator()
    result = myValidator.validateAvs(filename)
    return result

def findAVSbyEpic(epicName):
    try:
        epic = Epic.objects.get(name=epicName)
        userStoryList = UserStory.objects.filter(epic=epic)
        for story in userStoryList:
            tcusObject = TestCaseUserStoryMapping.objects.filter(user_story=story)
            for tcusMappings in tcusObject: 
                testCaseList = TestCase.objects.filter(id=tcusMappings.test_case.id)
                result = (userStoryList,testCaseList)
        return result
    except:
        error = "Error in finding AVS by Epic"
        return { 'error': error }


def getUserStoryMindMap(storyName):
    logger.debug('Called method get US MM for US %s' %storyName)
    logger.debug('Fetching TC information for US %s' %storyName)
    try:
        storyInfo = UserStory.objects.filter(name=storyName).latest('version')
        tcusList = TestCaseUserStoryMapping.objects.filter(user_story=storyInfo).filter(test_case__archived='0')
        logger.debug('Calling Method to Create MM')
        mindMap = createUSMindMap(tcusList, storyInfo)
        return mindMap
    except:
        error = "Error in getting User Story MindMap"
        return { 'error': error }

def createUSMindMap(tcusList, storyInfo):
    logger.debug('Creating Map Node for MM, US %s' %storyInfo.name)
    try:
        mapNode = xml.Element('map')
        mapNode.attrib['version'] = "0.9.0"
        logger.debug('Creating Story Node for MM with value %s ' %storyInfo.name)
        rootNode = xml.Element('node')
        intStoryVersion = storyInfo.version
        stringStoryVersion = str(intStoryVersion)
        rootNode.attrib['TEXT'] = stringStoryVersion+": "+storyInfo.name
        mapNode.append(rootNode)
        for tcusObject in tcusList:
            tc = tcusObject.test_case
            testType =  tc.type 
            testTypeNodeName = getTypeNodeName(testType, tc)
            subElements = rootNode.getchildren()
            # Create the first test type node and add this test case to it
            if not subElements:
                logger.debug('No Sub-Elements Exist')
                testTypeNode = xml.Element('node')
                testTypeNode.attrib['TEXT'] = testTypeNodeName
                rootNode.append(testTypeNode)
                titleNode = appendtoTypeNode(tc)
                testTypeNode.append(titleNode)
            else:
                counter = 0
                for subElement in subElements:
                    # If the test type node is already there add this test case to it
                    if subElement.get('TEXT') == testTypeNodeName:
                        if counter == 0:
                            logger.debug('Sub-Element already exists')
                            titleNode = appendtoTypeNode(tc)
                            subElement.append(titleNode)
                    else:
                        exists=0
                        # Check to see if the test node type has been created previously
                        for testType in rootNode.getchildren():
                            if testType.get('TEXT') == testTypeNodeName:
                                exists=1
                        # Create the test node type if it's not there already
                        if exists == 0:
                            logger.debug('Sub-Element Needs to be created')
                            testTypeNode = xml.Element('node')
                            testTypeNode.attrib['TEXT'] = testTypeNodeName
                            rootNode.append(testTypeNode)
                            titleNode = appendtoTypeNode(tc)
                            testTypeNode.append(titleNode) 
                            counter = counter+1
    except Exception, error:
        result = "Error in creating a User Story Mind Map"
        return { 'error': error, 'result': result } 
    logger.info("Final XML: %s" %xml.tostring(mapNode))
    return xml.tostring(mapNode)

    
def appendtoTypeNode(tc):
    logger.debug('Appending to Test Type Node')
    # Add Title Node as an Element    
    tcID = tc.tcId
    title = tcID
    title += ": "
    title += tc.title
    titleNode = xml.Element('node')
    titleNode.attrib['TEXT'] = title
    titleNode.attrib['TC_ID'] = tcID
    # Add componentNode as an Element
    componentNode = xml.Element('node')
    component = tc.component.name 
    componentNode.attrib['TEXT'] = "COMPONENT: "+component
    # Add component Node as a sub-element to title node 
    titleNode.append(componentNode)
    # Add description Node as an Element
    descNode = xml.Element('node')
    desc = tc.desc 
    descNode.attrib['TEXT'] = "DESCRIPTION: "+desc
    # Add description Node as a sub-element to title node
    titleNode.append(descNode)
    # Add Priority Node as an Element
    priorityNode = xml.Element('node')
    priority = tc.priority 
    priorityNode.attrib['TEXT'] = "PRIORITY: "+priority
    # Append Title Node with priority node as a sub-element
    titleNode.append(priorityNode)
    # Add Group Node as an Element
    groupNode = xml.Element('node')
    group = tc.groups 
    groupNode.attrib['TEXT'] = "GROUP: "+group
    # Append Title Node with group node as a sub-element
    titleNode.append(groupNode)
    # Add Pre Node as an Element
    preNode = xml.Element('node')
    pre = tc.pre 
    preNode.attrib['TEXT'] = "PRE: "+pre
    # Append Title Node with pre node as a sub-element
    titleNode.append(preNode)
    # Create AP Node and attache VP items to it 
    logger.debug('Creating APs and attached VPs')
    actionPointList = ActionPoint.objects.filter(testCase=tc)
    for ap in actionPointList:
        apNode = createAPandVPNodes(ap)
        titleNode.append(apNode)         
    vUserNode = xml.Element('node')
    vuser = tc.vusers
    vUserNode.attrib['TEXT'] = "VUSERS: "+vuser
    titleNode.append(vUserNode)
    contextNode = xml.Element('node')
    context = tc.context
    contextNode.attrib['TEXT'] = "CONTEXT: "+context
    titleNode.append(contextNode)
    logger.debug('Finishing Creating the Title Node')
    return titleNode

def createAPandVPNodes(ap):
    logger.debug('In Create AP and VP Node Method')
    apNode = xml.Element('node')
    actionPointdesc = ap.desc     
    apNode.attrib['TEXT'] = "EXECUTE: "+actionPointdesc    
    verificationPointList = VerificationPoint.objects.filter(actionPoint=ap)
    for vp in verificationPointList:
        vpNode = xml.Element('node')
        vpDesc = vp.desc
        vpNode.attrib['TEXT'] = "VERIFY: "+vpDesc
        apNode.append(vpNode)
    return apNode

def getTypeNodeName(testType, testcase):
    for type in testcase.TEST_TYPES:
        if testType == type[0]:
            returnText = type[1]
    return returnText

#def formatTupletoStringKeyColumn(tupleValue):
#    modValue = str(tupleValue).strip('[u]')
#    modValue = modValue.replace("'","")
#    modValue = modValue.replace('"','')
#    modValue = modValue.replace('L',"")
#    return modValue


def getAllUSInformation(storyName):
    logger.debug('Fetching TC Information for the US')
    story = UserStory.objects.get(name=storyName)
    testCaseList = TestCase.objects.filter(userStory=story)
    return testCaseList

def importAvs(filename,user):
    logger.debug('Starting')
    myValidator = AvsValidator.AvsValidator()
    
    #Note: take these two line out for release
    #result = myValidator.importAvs(filename)
    #return result

    #Good from here for release
    result = myValidator.validateAvs(filename)
    if result['errors'] == 0:
        logger.debug('Validation was successful, starting import')
        result = myValidator.importAvs(filename,user)
        #logger.debug('Starting skeleton file generation')
        #fileMap = generateSkeletonClass(result['userStory'])
        #result['fileMap']=fileMap
        logger.debug('Returning result: %s' %result)
        return result
    else:
        logger.debug('Validation was NOT successful, starting import')
        return result 


    #Return a pass or fail
    
def getJiraIdDetails(issueId):
    myJiraRest = JiraRest.JiraRest()
    result = myJiraRest.getJiraIdDetails(issueId)
    return result

def generateSkeletonClass(userStoryId):
    myGenerateSkeleton = GenerateSkeleton.GenerateSkeleton()
    return myGenerateSkeleton.generateSkeleton(userStoryId)

def getTestCaseList(story):
    '''
    Populate a list of test cases according to their mapping to a story.
    '''
    tcusObject = TestCaseUserStoryMapping.objects.filter(user_story=story)
    testCaseList = ()
    for tcusMappings in tcusObject:
        testCaseList = TestCase.objects.filter(id=tcusMappings.test_case.id)
    return testCaseList
