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

def getDeploymentDescriptionFile(depDescVersion,depDescPackage):
    '''
    Function used to download and parse the Deployment description for updates to clusters
    '''

    ddBaseDir = str(config.get('DMT','ddBaseDir'))
    if not os.path.isdir(ddBaseDir):
        os.mkdir(ddBaseDir)
    tmpArea = tempfile.mkdtemp(dir=ddBaseDir)
    # Download the Deployment Description Package
    packageObject = dmt.cloud.getPackageObject(depDescPackage,depDescVersion,"None","no")
    if packageObject == None:
        message = "ERROR: Unable to Download the version of the Deployment description package specified"
        return (1,message,depDescPackage)

    artifactName = dmt.cloud.downloadArtifact(tmpArea,"None",packageObject,"ENM")
    if artifactName == 1:
        message = "ERROR: Unable to download the package " + str(depDescPackage)
        return (1,message,depDescPackage)
    # Extract the package to list the DD files
    (ret,message) = dmt.utils.extractRpmFile(artifactName,tmpArea)
    if ret != 0:
        return (1,message,depDescPackage)

    try:
        artifact = packageObject.artifactId
        group = packageObject.groupId
        secondGroup = config.get('DMT_AUTODEPLOY', 'secondSliceGroupId')
        secondArtifact = config.get('DMT_AUTODEPLOY', 'secondSliceArtifactId')
    except Exception as e:
        message = "ERROR: Unable to get the slice infomation for the Deployment template version inputted. Exception: " + str(e)
        return (1,message,depDescPackage)
    try:
        (ret,sliceOneDir) = dmt.utils.downloadSliceFile(depDescVersion,tmpArea,artifact,group)
        if ret != 0:
            return (1,sliceOneDir,depDescPackage)
        (ret,message) = dmt.utils.unzipFile(sliceOneDir,tmpArea)
        if ret != 0:
            return (1,message,depDescPackage)
    except Exception as e:
        message = "ERROR: Unable to get the snapshot file for artifact " + str(artifact) + " with version " + str(depDescVersion) + " for slice Deployment Description. Please ensure the snapshot exist in Nexus. Exception: " + str(e)
        return (1,message,depDescPackage)
    try:
        (ret,sliceTwoDir) = dmt.utils.downloadSliceFile(depDescVersion,tmpArea,secondArtifact,secondGroup)
        if ret != 0:
            return (1,sliceTwoDir,depDescPackage)
        (ret,message) = dmt.utils.unzipFile(sliceTwoDir,tmpArea)
        if ret != 0:
            return (1,message,depDescPackage)
    except Exception as e:
        message = "ERROR: Unable to get the snapshot file for artifact " + str(secondArtifact) + " with version " + str(depDescVersion) + " for slice Deployment Description. Please ensure the snapshot exist in Nexus. Exception: " + str(e)
        return (1,message,depDescPackage)

    return (ret,message,tmpArea)

def parseDeploymentDescriptionFile(depDescVersion,depDescType,depDescFileName,depDescPackage,tmpArea):
    '''
    Function to parse Virtual Image infomation from DD Info and Xml file and save in lists
    '''
    ddServiceVmList = []
    servicesToVmList = []
    try:
        if DeploymentDescription.objects.filter(name=depDescFileName, dd_type__dd_type=depDescType, version__version=depDescVersion).exists():
            deploymentDescriptionObj = DeploymentDescription.objects.get(name=depDescFileName, dd_type__dd_type=depDescType, version__version=depDescVersion)
            ddXmlFileName = deploymentDescriptionObj.auto_deployment
            ddInfoFileName = deploymentDescriptionObj.sed_deployment
        (ret,ddXmlFileName) = dmt.utils.findFile(tmpArea,ddXmlFileName)
        if ret != 0:
            message = "ERROR: Unable to find the Deployment description xml file within the Deployment template package. Please ensure the artifact exists in Nexus."
            logger.error(message)
            return (1,ddXmlFileName,ddServiceVmList, servicesToVmList)
        ret,ddInfoFileName = dmt.utils.findFile(tmpArea,ddInfoFileName)
        if ret != 0:
            message = "ERROR: Unable to find the Deployment description info file within the Deployment template package. Please ensure the artifact exists in Nexus."
            logger.error(message)
            return (1,ddInfoFileName,ddServiceVmList, servicesToVmList)
    except Exception as e:
        message = "ERROR: Unable to find the specified slice file " + str(depDescFileName) + ". Are you sure you have the correct name assigned for the slice file. Exception: " + str(e)
        logger.error(message)
        return (1,message,ddServiceVmList, servicesToVmList)
    (ret,ddServiceVmList) = dmt.utils.changeFileToList(ddXmlFileName)
    (ret,servicesToVmList) = dmt.utils.parseDdInfoConfig(ddInfoFileName)
    if "esmon" in str(ddServiceVmList):
        servicesToVmList["svc-1"].append("esmon")
    message = "SUCCESS"
    return (ret,message,ddServiceVmList,servicesToVmList)

def addVirtualImages(clusterId, ddServicesXmlList, ddServicesInfoList):
    '''
    Add active Deployment Description Virtual Images to cluster if not already present
    '''
    listOfServicesAdded = []
    listOfIpTypeAdded = []
    task = "add"
    virtualImageItemsObj = VirtualImageItems.objects.filter(active=1)
    logData = []
    try:
        # handle haproxies seperately as they dont appear in the DD info.txt file
        for virtualImageItem in virtualImageItemsObj:
            virtualImageName = virtualImageItem.name
            serviceIsInDDXml = dmt.utils.checkForServiceInDDXml(ddServicesXmlList, virtualImageName)
            serviceIsInDDInfo = dmt.utils.checkForServiceInDDInfo(ddServicesInfoList, virtualImageName)
            if serviceIsInDDInfo and serviceIsInDDXml:
                returnedValue, node = dmt.utils.findNodeForService(ddServicesInfoList, virtualImageName)
                if returnedValue == "1":
                    logMsg = "INFO: Failed to find a node for " + str(virtualImageName) + " in Deployment " + str(clusterId)
                    logger.info(logMsg)
                    logData.append(logMsg)
                    continue
                else:
                    clusterServerExists = ClusterServer.objects.filter(node_type=node,cluster_id=clusterId).exists()
                    virtualImageExists = VirtualImage.objects.filter(name=virtualImageName,cluster_id=clusterId).exists()
                    if clusterServerExists:
                        if not virtualImageExists:
                            returnedValue,message = dmt.utils.virtualImage(virtualImageName,node,clusterId,task,virtualImageName)
                            if returnedValue == "1":
                                logMsg = "ERROR: Failed to save the Service Information for " + virtualImageItem.name + " in Deployment " + str(clusterId) + ", Exception: " + str(message)
                                logger.error(logMsg)
                                logData.append(logMsg)
                                return (2, listOfServicesAdded, logData)
                            logMsg = "INFO: Added " + str(virtualImageName) + " to Node: " + str(node) + " on Deployment " + str(clusterId)
                            logger.info(logMsg)
                            logData.append(logMsg)
                            listOfServicesAdded.append(virtualImageName)
                        else:
                            logger.info("INFO: " + virtualImageItem.name + " already exists in Deployment " + str(clusterId))
                            logger.info("INFO: Checking ip Type of  " + virtualImageName)
                            existIpType = dmt.utils.getVirtualImageDetails(clusterId, virtualImageName)
                            serviceIpTypeInDDXml = dmt.utils.getServiceIpTypeInDDXml(virtualImageName, ddServicesXmlList)
                            ipTypeAdded = [x for x in serviceIpTypeInDDXml if x not in existIpType]
                            if ipTypeAdded:
                                logMsg = "INFO: " + virtualImageItem.name + " needs to auto update ip type " + str(ipTypeAdded)
                                listOfIpTypeAdded += ipTypeAdded
                                logger.info(logMsg)
                                logData.append(logMsg)
                    else:
                        logMsg = "INFO: The following cluster server " + str(node) + " does not exist for updates on Deployment " + str(clusterId)
                        logger.info(logMsg)
                        logData.append(logMsg)

        return (0, listOfServicesAdded, listOfIpTypeAdded, logData)
    except Exception as e:
        logMsg = "ERROR: Updating Deployment " + str(clusterId) + " with Services, Exception: " + str(e)
        logger.error(logMsg)
        logData.append(logMsg)
        return (1, listOfServicesAdded, listOfIpTypeAdded, logData)

def addVirtualImageIpInfo(clusterId, hardwareType, ddServicesXmlList, listOfServicesAdded, listOfIpTypeAdded):
    '''
    Add IP info to newly created Virtual Image based on the Deployment Description Xml
    '''
    number = 1
    ipType = "Not needed"
    ipTypeId = "Not needed"
    allDeploymentIps = []
    duplicatePublicIps = []
    logData = []
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "ERROR: Unable to get Deployment " + str(clusterId) + "to update virtual Image IP addresses, Exception: " +str(e)
        logger.error(str(message))
        logData.append(message)
        return 0, logData

    if "cloud" in hardwareType:
        ipv4Identifier = ipv6Identifier = clusterId
    else:
        ipv4Identifier = ipv6Identifier = '1'

    try:
        allDeploymentIps=dmt.utils.getAllIPsInCluster(clusterObj)
    except Exception as e:
        message = "ERROR: Unable to get all Deployment IP's for Deployment " + str(clusterId) + " , Exception: " + str(e)
        logger.error("ERROR: Unable to get all Deployment IP's for Deployment " + str(clusterId) + " , Exception: " + str(e))
    try:
        ddToDeploymentMappingObj = DDtoDeploymentMapping.objects.get(cluster__id=clusterId)
        ipRangeType = ddToDeploymentMappingObj.iprange_type
    except Exception as e:
        message = "ERROR: Unable to get Deployment Description to Deployment Mapping details for " + str(clusterId) + " to update virtual Image IP addresses, Exception: " +str(e)
        logger.error(message)
        logData.append(message)
        return 0, logData
    if ipRangeType == 'manual':
        try:
            vmServiceIpv4RangeList = VmServiceIpRange.objects.filter(cluster__id=clusterId,ipTypeId__ipType="IPv4 Public")
            vmServiceIpv6RangeList = VmServiceIpRange.objects.filter(cluster__id=clusterId,ipTypeId__ipType="IPv6 Public")
            vmServiceIpv4StorageRangeList = VmServiceIpRange.objects.filter(cluster__id=clusterId,ipTypeId__ipType="IPv4 Storage")
        except Exception as e:
            message = "ERROR: Unable to get IP range information for Deployment " + str(clusterId) + " , Exception: " + str(e)
            logger.error(message)
            logData.append(message)

    elif ipRangeType =='dns' or ipRangeType == 'None':
        try:
            vmServiceIpv4RangeList = AutoVmServiceDnsIpRange.objects.filter(cluster__id=clusterId,ipTypeId__ipType="IPv4 Public")
            vmServiceIpv6RangeList = AutoVmServiceDnsIpRange.objects.filter(cluster__id=clusterId,ipTypeId__ipType="IPv6 Public")
            vmServiceIpv4StorageRangeList = AutoVmServiceDnsIpRange.objects.filter(cluster__id=clusterId,ipTypeId__ipType="IPv4 Storage")
        except Exception as e:
            message = "ERROR: Unable to get IP range information for Deployment " + str(clusterId) + " , Exception: " + str(e)
            logger.error(message)
            logData.append(message)
    else:
        message = "ERROR: Unable to get IP range information for Deployment " + str(clusterId)
        logger.error(message)
        logData.append(message)

    try:
        for service in listOfServicesAdded:
            virtualImageName = service
            for serviceInfo in ddServicesXmlList:
                parsedService = dmt.utils.parseServiceInfo(serviceInfo)
                if virtualImageName == parsedService:
                    allDeploymentIps, duplicatePublicIps, logData = createVirtualImageInfoIp(virtualImageName, serviceInfo, clusterId, clusterObj, vmServiceIpv4RangeList, vmServiceIpv6RangeList, ipv4Identifier, ipv6Identifier, vmServiceIpv4StorageRangeList, allDeploymentIps, duplicatePublicIps, ipType, number, logData)
        if listOfIpTypeAdded:
            for serviceIpType in listOfIpTypeAdded:
                virtualImageName = dmt.utils.parseServiceInfo(serviceIpType)
                allDeploymentIps, duplicatePublicIps, logData = createVirtualImageInfoIp(virtualImageName, serviceIpType, clusterId, clusterObj, vmServiceIpv4RangeList, vmServiceIpv6RangeList, ipv4Identifier, ipv6Identifier, vmServiceIpv4StorageRangeList, allDeploymentIps, duplicatePublicIps, ipType, number, logData)
    except Exception as e:
        errorMsg = "ERROR: Issue adding Virtual Image IP's to Deployment " + str(virtualImageName) + ", Exception: " + str(e)
        logger.error(errorMsg)
        logData.append(errorMsg)
        return 1 , logData
    return 0, logData

def createVirtualImageInfoIp(virtualImageName, serviceInfo, clusterId, clusterObj, vmServiceIpv4RangeList, vmServiceIpv6RangeList, ipv4Identifier, ipv6Identifier, vmServiceIpv4StorageRangeList, allDeploymentIps, duplicatePublicIps, ipType, number, logData):
    '''
    Add ip info for virtual images
    '''
    hostname = "Not Assigned"
    if "ipaddress" in serviceInfo:
        virtualImageIpType = "public"
        if vmServiceIpv4RangeList:
            ret, imageIpAddress = dmt.utils.getPublicAddress(vmServiceIpv4RangeList, virtualImageIpType, ipv4Identifier, allDeploymentIps, virtualImageName, duplicatePublicIps)
            if ret != 0:
                logMsg = "WARNING: No available " + str(virtualImageIpType) + " IP Address found for Deployment " + str(clusterId) + " on service " + str(virtualImageName) + ", add more IP Addresses to the IPv4 Public IP Range."
                logger.info(logMsg)
                logData.append(logMsg)
                duplicatePublicIps.append(imageIpAddress)
                return allDeploymentIps, duplicatePublicIps, logData
            hostname = dmt.uploadContent.getHostName(imageIpAddress, clusterId)
        else:
            logMsg = "INFO: No IPv4 range found for Deployment " + str(clusterId) + " to assign to service " + str(virtualImageName)
            logger.info(logMsg)
            logData.append(logMsg)
            return allDeploymentIps, duplicatePublicIps, logData
    elif "ipv6address" in serviceInfo:
        virtualImageIpType = "ipv6Public"
        if vmServiceIpv6RangeList:
            ret, imageIpAddress = dmt.utils.getPublicAddress(vmServiceIpv6RangeList, virtualImageIpType, ipv6Identifier, allDeploymentIps, virtualImageName, duplicatePublicIps)
            if ret != 0:
                logMsg = "WARNING: No available " + str(virtualImageIpType) + " IP Address found for Deployment " + str(clusterId) + " on service " + str(virtualImageName) + ", add more IP Addresses to the IPv6 Public IP Range."
                logger.info(logMsg)
                logData.append(logMsg)
                duplicatePublicIps.append(imageIpAddress)
                return allDeploymentIps, duplicatePublicIps, logData
        else:
            logMsg = "INFO: No IPv6 range found for Deployment " + str(clusterId) + " to assign to service " + str(virtualImageName)
            logger.info(logMsg)
            logData.append(logMsg)
            return allDeploymentIps, duplicatePublicIps, logData
    elif "ipv6_internal" in serviceInfo:
        virtualImageIpType = "ipv6Internal"
        if clusterObj.layout.name == "KVM":
            instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"ClusterId_" + str(clusterId), allDeploymentIps)
        else:
            instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_virtualImageInternalIPv6", allDeploymentIps)
        if dmt.utils.checkAddressIsUnique(virtualImageIpType, imageIpAddress, clusterId):
            logMsg = "INFO: Duplicate IP Address " + str(imageIpAddress) + ", for ipv6 internal IP type info for virtual image, overwriting  : " + str(virtualImageName)
            logger.error(logMsg)
            logData.append(logMsg)
            IpAddress.objects.get(ipv6_address=imageIpAddress,ipv6UniqueIdentifier=clusterId).delete()
    elif "jgroups" in serviceInfo:
        virtualImageIpType = "jgroup"
        instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv_virtualImageInternalJgroup", allDeploymentIps)
        if dmt.utils.checkAddressIsUnique(virtualImageIpType, imageIpAddress, clusterId):
            logMsg = "INFO: Duplicate IP Address " + str(imageIpAddress) + ", for jGroup IP type info for virtual image, overwriting: " + str(virtualImageName)
            logger.error(logMsg)
            logData.append(logMsg)
            IpAddress.objects.get(address=imageIpAddress,ipv4UniqueIdentifier=clusterId).delete()
    elif "storage" in serviceInfo:
        virtualImageIpType = "storage"
        if vmServiceIpv4StorageRangeList:
            ret, imageIpAddress = dmt.utils.getPublicAddress(vmServiceIpv4StorageRangeList, virtualImageIpType, ipv4Identifier, allDeploymentIps, virtualImageName, duplicatePublicIps)
            if ret != 0:
                logMsg = "WARNING: No available " + str(virtualImageIpType) + " IP Address found for Deployment " + str(clusterId) + " on service " + str(virtualImageName) + ", add more IP Addresses to the IPv4 Storage IP Range."
                logger.info(logMsg)
                logData.append(logMsg)
                return allDeploymentIps, duplicatePublicIps, logData
            if dmt.utils.checkAddressIsUnique(virtualImageIpType, imageIpAddress, ipv4Identifier):
                logMsg = "INFO: Duplicate IP Address " + str(imageIpAddress) + ", for Storage internal IP type info for virtual image, overwriting : " + str(virtualImageName)
                logger.error(logMsg)
                logData.append(logMsg)
                IpAddress.objects.get(address=imageIpAddress,ipv4UniqueIdentifier=clusterId).delete()
        else:
            logMsg = "INFO: No IPv4 Storage range found for Deployment " + str(clusterId) + " to assign to service " + str(virtualImageName)
            logger.info(logMsg)
            logData.append(logMsg)
            return allDeploymentIps, duplicatePublicIps, logData
    elif "internal" in serviceInfo:
        virtualImageIpType = "internal"
        instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj, ["PDU-Priv-2_virtualImageInternal", "PDU-Priv-2_virtualImageInternal_2"], allDeploymentIps)
        if dmt.utils.checkAddressIsUnique(virtualImageIpType, imageIpAddress, clusterId):
            logMsg = "INFO: Duplicate IP address " + str(imageIpAddress) + ", for Internal IP type info for virtual image, overwriting : " + str(virtualImageName)
            logger.error(logMsg)
            logData.append(logMsg)
            IpAddress.objects.get(address=imageIpAddress,ipv4UniqueIdentifier=clusterId).delete()
    if imageIpAddress:
        ret,message = dmt.utils.createVirtualImageIp(imageIpAddress,ipType,number,str(hostname),clusterId,virtualImageName,virtualImageIpType)
        allDeploymentIps += ":" + str(imageIpAddress)
        logMsg = "INFO: Added " + str(virtualImageIpType) + " IP Address " + str(imageIpAddress) + ", on Deployment " + str(clusterId) + " to service " + str(virtualImageName)
        logger.info(logMsg)
    else:
        logMsg = "WARNING: No available " + str(virtualImageIpType) + " IP Address found for Deployment " + str(clusterId) + " on service " + str(virtualImageName)
        logger.info(logMsg)
    logData.append(logMsg)
    return allDeploymentIps, duplicatePublicIps, logData

def deleteExistingVirtualImages(clusterId):
    '''
    Used to delete all the virtual image info before a upload from DD
    '''
    haproxyList = ["ha_proxy-sb", "int_ha_proxy", "haproxy"]
    virtualImageItemsList = VirtualImageItems.objects.all()
    for virtualImageItem in virtualImageItemsList:
        if VirtualImage.objects.filter(name=virtualImageItem.name,cluster_id=clusterId).exists():
            dmt.utils.deleteClusterItems(virtualImageItem.name, haproxyList, clusterId)
        if VirtualImage.objects.filter(cluster_id=clusterId).exists():
            virtualImageObject = VirtualImage.objects.filter(cluster_id=clusterId)
            for item in virtualImageObject:
                dmt.utils.deleteClusterItems(item.name, haproxyList, clusterId)

def mapCredentialsToVirtualImages(listOfServicesAdded,clusterId):
    '''
    Function to map existing credentials to new Virtual Images
    '''
    user="auto"
    result = ""
    logData = []
    try:
        virtualImageObj = VirtualImage.objects.get(name="haproxy",cluster_id=clusterId)
    except ObjectDoesNotExist as e:
        logMsg = "ERROR: haproxy object does not exist to get credentials on cluster " + str(clusterId) + ", Exception: " + str(e)
        logger.error(logMsg)
        logData.append(logMsg)
        return (1, "ERROR", logData)

    virtualImageCredentials = VirtualImageCredentialMapping.objects.filter(virtualimage=virtualImageObj).first()

    try:
        if virtualImageCredentials:
            virtualImageUsername = virtualImageCredentials.credentials.username
            virtualImagePassword = virtualImageCredentials.credentials.password
            virtualImageCredType = virtualImageCredentials.credentials.credentialType
        else:
            logMsg = "ERROR: No Service credentials in list for Deployment " + str(clusterId)
            logger.error(logMsg)
            logData.append(logMsg)
            return (1, "ERROR", logData)

        credential = Credentials.objects.filter(username=virtualImageUsername, password=virtualImagePassword, credentialType=virtualImageCredType).first()
        if credential:
            for service in listOfServicesAdded:
                try:
                    virtualImageObj = VirtualImage.objects.get(name=service,cluster=clusterId)
                except ObjectDoesNotExist as e:
                    logMsg = "ERROR: " + str(service) + " does not exist, Exception: " + str(e)
                    logger.error(logMsg)
                    logData.append(logMsg)
                    return (1, "ERROR", logData)
                try:
                    dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    virtualImageCredMap = VirtualImageCredentialMapping.objects.create(virtualimage=virtualImageObj, credentials=credential, signum=user, date_time=dateTime)
                    logMsg = "INFO: Adding credential information to Service " + str(service)
                    logger.info(logMsg)
                    logData.append(logMsg)
                except Exception as e:
                    logMsg = "ERROR: Failed to create Mapping for Service " + str(service) + " in Deployment: " + str(clusterId) + " ,Exception: " + str(e)
                    logger.info(logMsg)
                    logData.append(logMsg)
                    return (1, "FAILED", logData)

        return (0,"SUCCESS", logData)
    except Exception as e:
        logMsg = "ERROR: There was an issue saving the Services credentials, Exception: " + str(e)
        logger.error(logMsg)
        logData.append(logMsg)
        return (1,"ERROR", logData)

def rollbackClusterUsingSED(clusterId, filePath, tmpArea):
    '''
    Function to rolback cluster to previous state
    '''
    logger.info("INFO: Implementing rollback of cluster: " + str(clusterId))
    user = "auto"
    userList = []
    ddServiceVmList = None
    servicesToVmDict = {}
    populateDDorSED = ""
    task = "populate"
    logMsg = ""
    try:
        with open(filePath) as f:
            fileList = f.read().splitlines()
    except Exception as e:
        logMsg = "ERROR: Unable to read file to rollback Deployment, Exception: " + str(e)
        logger.error(logMsg)
        return (1,logMsg)

    ret = dmt.uploadContent.handleUploadedFileAsList(fileList,'seduploadfile.txt',tmpArea)
    if ret != 0:
        logMsg = "ERROR: There was an issue handling generated SED file from the Deployment"
        logger.error(logMsg)
        return (1,logMsg)

    result = dmt.uploadContent.uploadContentMain(clusterId,str(tmpArea) + "/seduploadfile.txt",user,userList,ddServiceVmList,servicesToVmDict,populateDDorSED,task)
    if result:
        logMsg = "INFO: Upload Content: <br /> " + str("<br /> ".join(result))
    try:
        os.remove(str(tmpArea) + "/seduploadfile.txt")
    except Exception as e:
        logMsg = "ERROR: Unable to remove backed up SED file while updating cluster " + str(clusterId) + ", Exception: " +str(e)
        logger.error(logMsg)
        return (1,logMsg)
    return (0,logMsg)
