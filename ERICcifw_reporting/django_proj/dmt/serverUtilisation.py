from dmt.models import *
from ciconfig import CIConfig
from dmt.deploy import getEnvironment, runCommandGetOutput
import tempfile
from dmt.createSshConnection import *
from dmt.utils import closeRemoteConnectionObject, paramikoSftp

config = CIConfig()
import subprocess

def exitUtilisationTest(descriptionDetails,clusterId,tmpArea,remoteConnection):
    '''
    Function used to exit the testing if a critical Error is hit
    '''
    dmt.utils.dmtError(descriptionDetails,clusterId,tmpArea,remoteConnection)

def executeTestCase(remoteConnection,deploymentTestcaseObj,clusterObj,testItemObj,dateTime,managementServerObj):
    '''
    Function used to execute the test case on the deployment
    '''
    try:
        for testItemObj in deploymentTestcaseObj:
            retCommandValue = 0
            cmd = testItemObj.testcase
            tempScript = tempfile.NamedTemporaryFile(delete=False)
            tempScript.write(cmd)
            tempScript.close()

            logger.info("Uploading " + tempScript.name + " to " + tempScript.name)
            retValue = dmt.utils.paramikoSftp(
                managementServerObj.server.hostname + "." + managementServerObj.server.domain_name,
                "root",
                tempScript.name,
                tempScript.name,
                int(config.get('DMT_AUTODEPLOY', 'port')),
                config.get('DMT_AUTODEPLOY', 'key'),
                "put")
            if (retValue != 0):
                logger.error("Return Code: " + str(retValue))
                commandOutput = "Unable to transfer Testcase Script to MS from Gateway"
                retCommandLogging = testResultMapping(clusterObj,testItemObj,dateTime,0,commandOutput)
                continue
            (retValue, commandOutput) = remoteConnection.runScriptGetOutput(tempScript.name)
            os.remove(tempScript.name)

            # Since true is referenced as 1 within the DB then a error returned needs to be swapped around
            if retValue != 0:
                retValue = 0
            else:
                retValue = 1
            retCommandLogging = testResultMapping(clusterObj,testItemObj,dateTime,retValue,commandOutput)
            if retCommandLogging != 0:
                return retCommandLogging
    except Exception as e:
        return 1
    return 0

def testResultMapping(clusterObj,testItemObj,dateTime,retValue,commandOutput): 
    '''
    Function used to log the test results for each deployment 
    '''
    try:
        if "Permanently added" in commandOutput:
            commandOutput = commandOutput.split('to the list of known hosts.')[1];
        #change string elemt to a list
        commandOutput = commandOutput.rsplit('\r')
        # Remove all \n from the list
        commandOutput = list(map(str.strip,commandOutput))
        # Remove all blank elements from the list
        commandOutput = filter(None, commandOutput)
        # Change the list back to a string element
        commandOutput = '\n'.join(commandOutput)
        if testItemObj == None:
            testGroupMapping = MapTestResultsToDeployment.objects.create(cluster=clusterObj,testDate=dateTime,result=retValue,testcaseOutput=commandOutput)
        else:
            logger.info("Testware Result to Cluster Mapping : cluster " + str(clusterObj) + " testcase " +str(testItemObj) + " testcase Description " + str(testItemObj.testcase_description) + " testDate " + str(dateTime) + " result " + str(retValue) + " testcaseOutput " + str(commandOutput))
            testGroupMapping = MapTestResultsToDeployment.objects.create(cluster=clusterObj,testcase=testItemObj.testcase,testcase_description=testItemObj.testcase_description,testDate=dateTime,result=retValue,testcaseOutput=commandOutput)
    except Exception as e:
        logger.error("Issue saving data within MapTestResultsToDeployment database. Exception: " + str(e))
        return 1
    return 0

def getConfigurtationDetails(serverObj,managementServerObj,testItemObject,clusterObj,dateTime,clusterId,tmpArea,remoteConnection):
    '''
    function used to get the generic configuration  details for a server defined
    '''
    ipAdressObj = credentialDetailsObj = None
    retValue = 0
    if NetworkInterface.objects.filter(server=serverObj.id,interface="eth0").exists():
        networkInterfaceObj = NetworkInterface.objects.get(server=serverObj.id,interface="eth0")
    else:
        commandOutput = "Unable to find NIC information for Management Server"
        testResultMapping(clusterObj,testItemObject,dateTime,retValue,commandOutput) == 0 or exitUtilisationTest(commandOutput,clusterId,tmpArea,remoteConnection)
        return (None,None)
    if IpAddress.objects.filter(nic=networkInterfaceObj.id,ipType="host").exists():
        ipAdressObj = IpAddress.objects.get(nic=networkInterfaceObj.id,ipType="host")
    else:
        commandOutput = "Unable to find IP information for Management Server"
        testResultMapping(clusterObj,testItemObject,dateTime,retValue,commandOutput) == 0 or exitUtilisationTest(commandOutput,clusterId,tmpArea,remoteConnection)
        return (None,None)
    if ManagementServerCredentialMapping.objects.filter(mgtServer_id=managementServerObj.id).exists():
        credentialDetailsObj = ManagementServerCredentialMapping.objects.get(mgtServer_id=managementServerObj.id)
    else:
        commandOutput = "Unable to find Credential Information for Management Server"
        testResultMapping(clusterObj,testItemObject,dateTime,retValue,commandOutput) == 0 or exitUtilisationTest(commandOutput,clusterId,tmpArea,remoteConnection)
        return (None,None)
    return (ipAdressObj,credentialDetailsObj)

def serverUtilisationMain(testGroupEntered):
    '''
    Main Function to call the server utilisation check
    Inputs:
        testGroupEntered: This is the test group set-up by the user to check their deployment(s) group 
        testGroupEntered could also be, "None", if so then the default is set to all deployments
    '''
    clusterId = testItemObject = tmpArea = remoteConnection = None
    dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if DeploymentTestcase.objects.filter(testcase="None",enabled=0).exists():
        defaultTestCaseObj = DeploymentTestcase.objects.get(testcase="None",enabled=0)
    else:
        descriptionDetails = "Default Testcase Not available"
        exitUtilisationTest(descriptionDetails,clusterId,tmpArea,remoteConnection)
    # Get Deployment Information
    clusterObjs = []
    if testGroupEntered == None:
        clusterObjs = Cluster.objects.all()
    else:    
        if TestGroup.objects.filter(testGroup=testGroupEntered).exists():
            testGroupObject = TestGroup.objects.get(testGroup=testGroupEntered)
            if MapTestGroupToDeployment.objects.filter(group=testGroupObject).exists():
                deploymentTestGroupObj = MapTestGroupToDeployment.objects.filter(group=testGroupObject)
                for item in deploymentTestGroupObj: 
                    clusterObjs += Cluster.objects.filter(id=item.cluster.id)
            else:        
                descriptionDetails = "Test group entered does not have deployments defined"
                exitUtilisationTest(descriptionDetails,clusterId,tmpArea,remoteConnection)
        else:    
            descriptionDetails = "Test group entered not available"
            exitUtilisationTest(descriptionDetails,clusterId,tmpArea,remoteConnection)
    retValue = 0
    for item in clusterObjs:
        if item.management_server.server.hardware_type != 'cloud':
            # Configuration Details
            user=config.get('DMT_AUTODEPLOY', 'user')
            masterUserPassword = config.get('DMT_AUTODEPLOY', 'masterPasswordCloudMS1')
            keyFileName = config.get('DMT_AUTODEPLOY', 'key')
            hostName = socket.gethostbyaddr(socket.gethostname())[0]

            clusterObj = item
            managementServerObj = item.management_server
            serverObj = item.management_server.server
            fqdnMgtServer = managementServerObj.server.hostname + "." + managementServerObj.server.domain_name
            environment = dmt.deploy.getEnvironment(item.id)

            # Get NetworkInterface,IP adddresses and Crediantial objects
            (ipAdressObj,credentialDetailsObj) = getConfigurtationDetails(serverObj,managementServerObj,defaultTestCaseObj,item,dateTime,clusterId,tmpArea,remoteConnection)
            if ipAdressObj == None or credentialDetailsObj == None:
                continue
            ipAddress = ipAdressObj.address
            username = credentialDetailsObj.credentials.username
            password = credentialDetailsObj.credentials.password
            # Can we ping the server
            ret = subprocess.call("ping -c1 " + fqdnMgtServer + " > /dev/null", shell=True)
            if (ret != 0):
                commandOutput = "Unable to ping the MS from the gateway"
                testResultMapping(clusterObj,defaultTestCaseObj,dateTime,retValue,commandOutput) == 0 or exitUtilisationTest(commandOutput,clusterId,tmpArea,remoteConnection)
                continue
            # Ensure the known host file is clean incase the server was re-installed since the last run 
            ret = dmt.createSshConnection.cleanKnowHostFile(managementServerObj)
            if ret != 0:
                descriptionDetails = "Unable to clean out known host file within gateway"
                exitUtilisationTest(descriptionDetails,clusterId,tmpArea,remoteConnection)
            # Open the ssh connection to the specified server
            (ret, remoteConnection) = dmt.createSshConnection.setRemoteConnection(fqdnMgtServer,user,masterUserPassword,hostName,keyFileName,environment)
            if (ret != 0):
                commandOutput = "Unable to get connection to Management Server either password is incorrect within DMT or the password has expired"
                testResultMapping(clusterObj,defaultTestCaseObj,dateTime,retValue,commandOutput) == 0 or exitUtilisationTest(commandOutput,clusterId,tmpArea,remoteConnection)
                continue
            if DeploymentTestcase.objects.filter(enabled=1).exists():
                deploymentTestcaseObj = DeploymentTestcase.objects.filter(enabled=1)
            else:
                descriptionDetails = "No Enabled Tests can be found"
                exitUtilisationTest(descriptionDetails,clusterId,tmpArea,remoteConnection)
            descriptionDetails = "Issue with test case on management server, \"" + str(fqdnMgtServer) + "\""
            executeTestCase(remoteConnection,deploymentTestcaseObj,item,testItemObject,dateTime,managementServerObj) == 0 or exitUtilisationTest(descriptionDetails,clusterId,tmpArea,remoteConnection)
            closeRemoteConnectionObject(remoteConnection)
        else:
            continue

