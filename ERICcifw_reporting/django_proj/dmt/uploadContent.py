import dmt.models
import dmt.utils
import os, time, commands, socket, tempfile, logging, shutil, json

from ciconfig import CIConfig
from django.core.exceptions import ObjectDoesNotExist
from dmt.forms import *
from cireports.common_modules.common_functions import *
from datetime import datetime
from dmt.logUserActivity import logAction, logChange

logger = logging.getLogger(__name__)
config = CIConfig()

def errorExit(msg):
    logger.error(msg)
    raise Exception(msg)

def deleteExistingVirtualImage(clusterId):
    '''
    Used to delete all the virtual image info before a fresh upload
    '''
    resultMessage = []
    virtualImageItemsObj = VirtualImageItems.objects.only('name').values('name').all()
    for virtualImageItem in virtualImageItemsObj:
        if VirtualImage.objects.filter(name=virtualImageItem['name'],cluster_id=clusterId).exists():
            returnedValue,message = dmt.utils.deleteVirtualImage(clusterId, virtualImageItem['name'])
            if returnedValue == "1":
                resultMessage.append("ERROR: " + str(message))
                logger.error(message)
            else:
                message= "SUCCESS: Deleted : " + str(virtualImageItem['name'])
                resultMessage.append(str(message))
    if VirtualImage.objects.filter(cluster_id=clusterId).exists():
        virtualImageObject = VirtualImage.objects.objects.only('name').values('name').filter(cluster_id=clusterId)
        for item in virtualImageObject:
            returnedValue,message = dmt.utils.deleteVirtualImage(clusterId, item['name'])
            if returnedValue == "1":
                resultMessage.append("ERROR: " + str(message))
                logger.error(message)
            else:
                message= "SUCCESS: Deleted : " + str(item['name'])
                resultMessage.append(str(message))
    return resultMessage

def getHostName(address,clusterId):

    hostname = ""
    clusterObj = Cluster.objects.filter(id=clusterId)
    for cluster in clusterObj:
        dnsServer = cluster.management_server.server.dns_serverA
        if dnsServer:
            break
    status, output = commands.getstatusoutput("nslookup " + address + " " + dnsServer + " | grep name | sed -e 's/.*name = //g' -e 's/.*ame://g' -e 's/\.$//'")

    if output:
        (hostname, ath) = output.split('.')[:2]
    return hostname

def uploadVirtualImages(clusterId,uploadFile,hardwareType,userLogin,userList,ddServiceVmList,servicesToVmDict,populateDDorSED,task):

    resultMessage = []
    number = 1
    ipType = "Not needed"
    haproxyList = ["ha_proxy-sb", "int_ha_proxy", "haproxy"]

    if "cloud" in hardwareType:
        ipv4Identifier = ipv6Identifier = clusterId
    else:
        ipv4Identifier = ipv6Identifier = '1'

    virtualImageItemsObj = VirtualImageItems.objects.only('name').values('name').filter(active=1)
    for virtualImageItem in virtualImageItemsObj:
        if virtualImageItem['name'] == "ha_proxy-sb":
            virName = "haproxy-sb_"
        elif virtualImageItem['name'] == "int_ha_proxy":
            virName = "int_haproxy_"
        else:
            virName = virtualImageItem['name'] + "_"
        if not virName in open(uploadFile).read():
            continue
        allSedKeys = []
        for line in open(uploadFile):
            allSedKeys.append(line.split('=')[0])
            virtualImageIpType = hostname = address = virtualImageIpType = address = vmName = None
            if re.match(r'^' + str(virName) + '[a-zA-Z]+', line):
                # Check that the item being added is it in the deployment description if not continue not needed to deploy the system
                if "populatedd" in populateDDorSED.lower():
                    if ddServiceVmList is not None:
                        sedService = line.split('=')[0]
                        if sedService not in ddServiceVmList:
                            if "hostname" not in sedService and "password" not in sedService:
                                message = "INFO: " + str(sedService) + " is not within the Deployment Description specified. No need to register."
                                resultMessage.append(message)
                                continue
                            else:
                                continue
                if task.lower() != "verify":
                    # First need to create the item if not already
                    if virtualImageIpType == None:
                        if not VirtualImage.objects.filter(name=virtualImageItem['name'],cluster_id=clusterId).exists():
                            name = virtualImageItem['name']
                            if "populatedd" in populateDDorSED.lower() and servicesToVmDict and name not in haproxyList:
                                returnedValue, node = dmt.utils.findNodeForService(servicesToVmDict, name)
                                if returnedValue == "1":
                                    message = "Failed to find a node for " + name + " in deployment " + clusterId
                                    resultMessage.append(str(message))
                                    logger.info(message)
                                    continue
                            elif servicesToVmDict and name not in haproxyList:
                                returnedValue, node = dmt.utils.findNodeForService(servicesToVmDict, name)
                                if returnedValue == "1":
                                    message = "Failed to find a node for " + name + " in deployment " + clusterId
                                    resultMessage.append(str(message))
                                    logger.info(message)
                                    continue
                            else:
                                node = "SVC-1"
                            # Does this node type exist if not place all under SVC-1
                            if not ClusterServer.objects.filter(cluster=clusterId,node_type=node).exists() or node == "None":
                                node = "SVC-1"
                            taskUser = "add"
                            vmName = virtualImageItem['name']
                            returnedValue,message = dmt.utils.virtualImage(name,node,clusterId,taskUser,vmName)
                            if returnedValue == "1":
                                message = "ERROR: Failed to save the Virtual Image Information for " + virtualImageItem['name'] + ", line involved " + str(line) + " Exception: " + str(message)
                                resultMessage.append(str(message))
                                logger.error(message)
                            if userList != None:
                                for item in userList:
                                    userName = item.get('userName')
                                    password = item.get('userPassword')
                                    type = item.get('userType')
                                    returnedValue,message = dmt.utils.createVirtualImageCredentials(userName,password,type,virtualImageItem['name'],clusterId,userLogin)
                                    if returnedValue == "1":
                                        message = "WARNING: Issues with the saving of Service VM Credential Information for " + str(virtualImageItem['name']) + ". " + str(message)
                                        resultMessage.append(str(message))
                                        continue

                if "ipv6_internal=" in line:
                    address = line.split('=')[1]
                    address = address.rstrip()
                    if address:
                        virtualImageIpType = "ipv6Internal"
                        vmName = virtualImageItem['name']
                    else:
                        message = "WARNING: No information assigned to " + virtualImageItem['name'] + ", line involved " + str(line)
                        resultMessage.append(str(message))
                        continue
                elif "internal=" in line:
                    address = line.split('=')[1]
                    address = address.rstrip()
                    if address:
                        virtualImageIpType = "internal"
                        vmName = virtualImageItem['name']
                    else:
                        message = "WARNING: No information assigned to " + virtualImageItem['name'] + ", line involved " + str(line)
                        resultMessage.append(str(message))
                        continue
                elif "jgroups=" in line:
                    address = line.split('=')[1]
                    address = address.rstrip()
                    if address:
                        virtualImageIpType = "jgroup"
                        vmName = virtualImageItem['name']
                    else:
                        message = "WARNING: No information assigned to " + virtualImageItem['name'] + ", line involved " + str(line)
                        resultMessage.append(str(message))
                        continue
                elif "storage=" in line:
                    address = line.split('=')[1]
                    address = address.rstrip()
                    if address:
                        virtualImageIpType = "storage"
                        vmName = virtualImageItem['name']
                    else:
                        message = "WARNING: No information assigned to " + virtualImageItem['name'] + ", line involved " + str(line)
                        resultMessage.append(str(message))
                        continue
                elif "ipaddress=" in line:
                    address = line.split('=')[1]
                    address = address.rstrip()
                    if address:
                        virtualImageIpType = "public"
                        vmName = virtualImageItem['name']
                        if vmName == "haproxy":
                            hostnameEntry = "httpd_fqdn="
                        else:
                            hostnameEntry = vmName + "_hostname="
                        for entry in open(uploadFile):
                            if hostnameEntry in entry:
                                if "httpd_fqdn=" in entry:
                                    hostname = getHostName(address,clusterId)
                                else:
                                    hostname = entry.split('=')[1].split('.')[0]
                    else:
                        message = "WARNING: No information assigned to " + virtualImageItem['name'] + ", line involved " + str(line)
                        resultMessage.append(str(message))
                        continue
                elif "ipv6address=" in line:
                    address = line.split('=')[1]
                    address = address.rstrip()
                    if address:
                        virtualImageIpType = "ipv6Public"
                        vmName = virtualImageItem['name']
                        for entry in open(uploadFile):
                            if virtualImageItem['name'] + "_ipv6hostname=" in entry:
                                hostname = entry.split('=')[1]
                    else:
                        message = "WARNING: No information assigned to " + virtualImageItem['name'] + ", line involved " + str(line)
                        resultMessage.append(str(message))
                        continue
                else:
                    continue
                if virtualImageIpType == None:
                    message = "WARNING: Issue getting the IP type for this virtual image : " + str(virtualImageItem['name']) + ", SED line involved " + str(line)
                    resultMessage.append(str(message))
                    logger.error(message)
                    continue
                if task.lower() != "verify":
                    if virtualImageIpType == "public" or virtualImageIpType == "storage":
                        if IpAddress.objects.filter(address=address,ipv4UniqueIdentifier=ipv4Identifier).exists():
                            message = "ERROR: Duplicate IP address for " + str(virtualImageIpType) + " IP type info for virtual image : " + str(virtualImageItem['name']) + ", SED line involved " + str(line)
                            resultMessage.append(str(message))
                            logger.error(message)
                            continue
                        if virtualImageIpType == "public":
                            hostname = getHostName(address, clusterId)
                    if virtualImageIpType == "ipv6Public":
                        if IpAddress.objects.filter(ipv6_address=address,ipv6UniqueIdentifier=ipv6Identifier).exists():
                            message = "ERROR: Duplicate IP address for " + str(virtualImageIpType) + " IP type info for virtual image : " + str(virtualImageItem['name']) + ", SED line involved " + str(line)
                            resultMessage.append(str(message))
                            logger.error(message)
                            continue
                    if virtualImageIpType == "ipv6Internal":
                        if IpAddress.objects.filter(ipv6_address=address,ipv6UniqueIdentifier=clusterId).exists():
                            message = "ERROR: Duplicate IP address for " + str(virtualImageIpType) + " IP type info for virtual image : " + str(virtualImageItem['name']) + ", SED line involved " + str(line)
                            resultMessage.append(str(message))
                            logger.error(message)
                            continue
                    if virtualImageIpType == "internal" or virtualImageIpType == "jgroup":
                        if IpAddress.objects.filter(address=address,ipv4UniqueIdentifier=clusterId).exists():
                            message = "ERROR Duplicate IP address for " + str(virtualImageIpType) + " IP type info for virtual image : " + str(virtualImageItem['name']) + ", SED line involved " + str(line)
                            resultMessage.append(str(message))
                            logger.error(message)
                            continue
                    if address != None and virtualImageIpType != None:
                        address = address.rstrip()
                        if hostname != None:
                            hostname = hostname.rstrip()
                            hostnameInfo = str(hostname).rsplit(" ", 1)
                            if len(hostnameInfo) == 2:
                                if "directory" in str(hostnameInfo[1]):
                                    hostnameInfo[1] = str(hostnameInfo[1]).replace("directory", "")
                                hostname = str(hostnameInfo[1]).strip()
                        returnedValue,message = dmt.utils.createVirtualImageIp(address,ipType,number,str(hostname),clusterId,vmName,virtualImageIpType)
                        if returnedValue == "1":
                            message = "ERROR: Failed to add Virtual Image IP Information for " + str(virtualImageItem['name']) + " for IP Type " + str(virtualImageIpType) + ". SED line involved " + str(line) + ", Exception: " + str(message)
                            resultMessage.append(str(message))
                            logger.error(message)
                        else:
                            message = "SUCCESS: Added : " + str(virtualImageItem['name']) + ", SED line involved " + str(line)
                            resultMessage.append(str(message))
    if ddServiceVmList != None:
        allSedKeys = list(set(allSedKeys))
        for item in ddServiceVmList:
            if "password" in item or "uuid" in item or "image" in item or "_key" in item:
                continue
            if item not in allSedKeys:
                message = "ERROR: Mismatch between the SED version and the deployment description, entry " + str(item) + " is within the deployment description but not the SED file"
                resultMessage.append(str(message))
    return resultMessage

def uploadContentMain(clusterId,uploadFile,userLogin,userList,ddServiceVmList,servicesToVmDict,populateDDorSED,task):
    '''
    Main function to upload the SED info to UI interface
    '''
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
        hardwareType = clusterObj.management_server.server.hardware_type
    except Exception as e:
        message = "No such cluster: " + str(clusterId) + ", Exception :  " + str(e)
        logger.error(message)

    result = []
    if task.lower() != "verify":
        resultDeleteVirtualImage = deleteExistingVirtualImage(clusterId)
        result.extend(resultDeleteVirtualImage)
    resultAddVirtualImage = uploadVirtualImages(clusterId,uploadFile,hardwareType,userLogin,userList,ddServiceVmList,servicesToVmDict,populateDDorSED,task)
    result.extend(resultAddVirtualImage)
    resultUpdateVlanDetails = updateVlanDetailsUsingSed(clusterId, uploadFile)
    result.extend(resultUpdateVlanDetails)
    return result

def handleUploadedFileAsList(fileList, name, localInvDefDirectory):
    '''
    The handleUploadedFileAsList function takes in a list and output to a file
    '''
    try:
        destination = open(localInvDefDirectory+"/"+str(name), 'wb+')
    except Exception as e:
        logger.error("There was an issue handling uploaded file from UI Form: " +str(e))
        return 1
    for item in fileList:
        destination.write("%s\n" % item)
    destination.close()
    return 0

def getDeploymentDescriptFileForSedUpload(sedVersion,depDescVersion,depDescType,depDescFileName,depDescPackage,ddServiceVmList,tmpArea):
    '''
    Function used to download the deployment description if specified
    '''
    ddXmlFileName = None
    servicesToVmDict = {}
    # Download the deployment Description Package
    packageObject = dmt.cloud.getPackageObject(depDescPackage,depDescVersion,"None","no")
    if packageObject == None:
        message = "ERROR: Unable to Download the version of the deployment description package specified"
        return (1,message,ddServiceVmList)
    if depDescType == "rpm":
        artifactName = dmt.cloud.downloadArtifact(tmpArea,"None",packageObject,"ENM")
        if artifactName == 1:
            message = "ERROR: Unable to download the package " + str(depDescPackage)
            return (1,message,ddServiceVmList,servicesToVmDict)
        # Extract the package to list the DD files
        (ret,message) = dmt.utils.extractRpmFile(artifactName,tmpArea)
        if ret != 0:
            return (1,message,ddServiceVmList,servicesToVmDict)
    else:
        try:
            artifact = packageObject.artifactId
            group = packageObject.groupId
            secondGroup = config.get('DMT_AUTODEPLOY', 'secondSliceGroupId')
            secondArtifact = config.get('DMT_AUTODEPLOY', 'secondSliceArtifactId')
        except Exception as e:
            message = "ERROR: Unable to get the slice infomation for the deployment template version inputted. Exception: " + str(e)
            return (1,message,ddServiceVmList,servicesToVmDict)
        try:
            (ret,sliceOneDir) = dmt.utils.downloadSliceFile(depDescVersion,tmpArea,artifact,group)
            if ret != 0:
                return (1,sliceOneDir,ddServiceVmList,servicesToVmDict)
            (ret,message) = dmt.utils.unzipFile(sliceOneDir,tmpArea)
            if ret != 0:
                return (1,message,ddServiceVmList,servicesToVmDict)
        except Exception as e:
            message = "ERROR: Unable to get the snapshot file for artifact " + str(artifact) + " with version " + str(depDescVersion) + " for slice deployment description. Please ensure the snapshot exist in Nexus. Exception: " + str(e)
            return (1,message,ddServiceVmList,servicesToVmDict)
        try:
            (ret,sliceTwoDir) = dmt.utils.downloadSliceFile(depDescVersion,tmpArea,secondArtifact,secondGroup)
            if ret != 0:
                return (1,sliceTwoDir,ddServiceVmList,servicesToVmDict)
            (ret,message) = dmt.utils.unzipFile(sliceTwoDir,tmpArea)
            if ret != 0:
                return (1,message,ddServiceVmList,servicesToVmDict)
        except Exception as e:
            message = "ERROR: Unable to get the snapshot file for artifact " + str(secondArtifact) + " with version " + str(depDescVersion) + " for slice deployment description. Please ensure the snapshot exist in Nexus. Exception: " + str(e)
            return (1,message,ddServiceVmList,servicesToVmDict)

    try:
        deploymentDescriptionObj = DeploymentDescription.objects.get(name=depDescFileName, version__version=depDescVersion)
        ddXmlFileName = deploymentDescriptionObj.auto_deployment
        ddInfoFileName = deploymentDescriptionObj.sed_deployment
    except ObjectDoesNotExist as e:
        message = "ERROR: Unable to get Deployment Description object information"
        return (1,message,ddXmlFileName,ddServiceVmList)
    try:
        (ret,ddXmlFileName) = dmt.utils.findFile(tmpArea,ddXmlFileName)
        if ret != 0:
            message = "ERROR: Unable to find the deployment description info file within the deployment template package. Please ensure the artifact exists in Nexus."
            return (1,message,ddServiceVmList,servicesToVmDict)
        (ret,ddInfoFileName) = dmt.utils.findFile(tmpArea,ddInfoFileName)
        if ret != 0:
            message = "ERROR: Unable to find the deployment description info file within the deployment template package. Please ensure the artifact exists in Nexus."
            return (1,message,ddServiceVmList,servicesToVmDict)
    except Exception as e:
        message = "ERROR: Unable to find the specified slice file " + str(ddFileName) + ". Are you sure you have the correct name assigned for the slice file. Exception: " + str(e)
        return (1,message,ddServiceVmList,servicesToVmDict)
    (ret,ddServiceVmList) = dmt.utils.changeFileToList(ddXmlFileName)
    (ret,servicesToVmDict) = dmt.utils.parseDdInfoConfig(ddInfoFileName)
    if "esmon" in str(ddServiceVmList):
        servicesToVmDict["svc-1"].append("esmon")
    message = "SUCCESS"
    return (ret,message,ddServiceVmList,servicesToVmDict)

def updateVMServiceUsingSedVersion(sedVersion,depDescVersion,depDescType,depDescFileName,depDescPackage,ddServiceVmList,tmpArea,deploymentId,populateDDorSED,populateDnsorMan, resultMessage):
    '''
    Function used to calculate generate a sed file using a version and update with missing IP from range
    '''
    servicesToVmDict = {}
    if depDescVersion != "":
        (ret,message,ddServiceVmList,servicesToVmDict) = getDeploymentDescriptFileForSedUpload(sedVersion,depDescVersion,depDescType,depDescFileName,depDescPackage,ddServiceVmList,tmpArea)
        if ret != 0:
            return (1,message,ddServiceVmList,servicesToVmDict,resultMessage)
    cifwkPortalUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    sed = dmt.buildconfig.generateDBConfigFile(deploymentId,sedVersion)
    (ret,blankEntriesWithinSed) = dmt.utils.parseSedForUnassignedServiceIps(sed,ddServiceVmList,populateDDorSED)
    if ret != 0:
        message = "ERROR: Unable to calculate the missing service VM within the SED"
        return (1,message,ddServiceVmList,servicesToVmDict,resultMessage)
    if populateDnsorMan == "populateDNSIP":
        urlToGenerateServicesIpRanges = str(cifwkPortalUrl) + "/api/deployment/" + str(deploymentId) + "/vm/service/dns/ip/range/data/all/"
    else:
        urlToGenerateServicesIpRanges = str(cifwkPortalUrl) + "/api/deployment/" + str(deploymentId) + "/vm/service/ip/range/data/all/"
    (ret,generateServicesIpRangesJsonObj) = dmt.utils.getTheResponseFromARestCall(urlToGenerateServicesIpRanges)
    if ret != 0:
        message = "ERROR: Unable to execute Rest Call to get the Deployment ranges"
        return (1,message,ddServiceVmList,servicesToVmDict,resultMessage)
    (ret,generateServicesIpRangesJsonObj) = dmt.utils.addInternalAndJGroupRange(generateServicesIpRangesJsonObj,deploymentId)
    if ret != 0:
        message = "ERROR: Unable to add the internal and jgroup range to the range list"
        return (1,message,ddServiceVmList,servicesToVmDict,resultMessage)
    (ret,newSedEntries,resultMessage) = dmt.utils.getFreeServiceIPRange(generateServicesIpRangesJsonObj,blankEntriesWithinSed,deploymentId,resultMessage)
    if ret != 0:
        return (1,newSedEntries,ddServiceVmList,servicesToVmDict,resultMessage)
    (ret,fileList,resultMessage) = dmt.utils.updateSedWithMissingEntries(newSedEntries,sed,deploymentId,resultMessage)
    return (ret,fileList,ddServiceVmList,servicesToVmDict,resultMessage)

def updateDataVMServices(action,rawJson,task):
    '''
    Function used as the main function call to update the service vms to a deployment whether through rest of the views
    '''
    decodedJson = json.loads(rawJson)
    deploymentId = decodedJson['deploymentId']
    fileList = decodedJson['file']
    loginUser = decodedJson['loginUser']
    userList = decodedJson['users']
    sedVersion = decodedJson['sedVersion']
    depDescVersion = decodedJson['depDescVersion']
    depDescType = decodedJson['depDescType']
    depDescFileName = decodedJson['depDescFileName']
    depDescPackage = decodedJson['depDescPackage']
    populateDDorSED = decodedJson['populateDDorSED']
    populateDnsorMan = decodedJson['populateDnsorMan']
    resultMessage = []
    deploymentObj = Cluster.objects.get(id=deploymentId)
    ddBaseDir = str(config.get('DMT','ddBaseDir'))
    if not os.path.isdir(ddBaseDir):
        os.mkdir(ddBaseDir)
    tmpArea = tempfile.mkdtemp(dir=ddBaseDir)

    ddServiceVmList = None
    servicesToVmDict = dict()
    result = None
    if sedVersion != "":
        (ret,fileList,ddServiceVmList,servicesToVmDict,resultMessage) = updateVMServiceUsingSedVersion(sedVersion,depDescVersion,depDescType,depDescFileName,depDescPackage,ddServiceVmList,tmpArea,deploymentId,populateDDorSED,populateDnsorMan, resultMessage)
        if ret != 0:
            shutil.rmtree(tmpArea)
            return (1,fileList)
    if fileList != "":
        ret = handleUploadedFileAsList(fileList,'seduploadfile.txt',tmpArea)
        if ret != 0:
            shutil.rmtree(tmpArea)
            message = "ERROR: There was an issue handling generated SED file from the deployment"
            return (1,message)
    else:
        shutil.rmtree(tmpArea)
        message = "ERROR: There was an issue parsing the inputted data. Please contact an Administrator"
        return (1,message)
    result = uploadContentMain(deploymentId,str(tmpArea) + "/seduploadfile.txt",loginUser,userList,ddServiceVmList,servicesToVmDict,populateDDorSED,task)
    result.extend(resultMessage)
    if action != "verify":
        message = "Uploaded Pre-Populated SED File To update Service VM Info"
        logAction(loginUser, deploymentObj, action, message)
    shutil.rmtree(tmpArea)
    return (0,result)

def updateVlanDetailsUsingSed(clusterId, uploadFile):
    dpsPersistenceProvider = ''
    resultMessage = []
    for line in open(uploadFile):
        if 'dps_persistence_provider' in line:
            dpsPersistenceProvider = line.split('=')[1].rstrip()
            try:
                clusterObj = Cluster.objects.get(id=clusterId)
                deploymentDatabaseProviderObj = DeploymentDatabaseProvider.objects.get(cluster=clusterObj)
                if dpsPersistenceProvider != '':
                    deploymentDatabaseProviderObj.dpsPersistenceProvider = dpsPersistenceProvider
                    deploymentDatabaseProviderObj.save()
                    message = "SUCCESS: Updated dps provider to : " + str(dpsPersistenceProvider) + ", SED line involved " + str(line)
                    resultMessage.append(str(message))
            except Exception as e:
                message = "ERROR: Failed to update vlanDetails using sed with error: " + str(e) + " SED line involved " + str(line)
                resultMessage.append(str(message))
            break
    return resultMessage
