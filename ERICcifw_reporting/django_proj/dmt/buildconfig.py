from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from dmt.models import *

import dmt.utils
import fwk.utils
import dmt.infoforConfig
import sys, os, tempfile, shutil

import logging

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

def generateConfigFile(clusterId, torVersion, cfgTemplate=None, webRun=None, installType=None):
    '''
    The purpose of this class is to edit the inventory and definition XML files and validate against the
    XSD's stored in Nexus
    '''
    # Location of the templates we use to generate the overall landscape and inventory
    if torVersion is 'hostproperties':
        singleDeployTemplate = os.path.join(config.get('DMT_HOSTPROPERTIES', 'mavenHostPropertiesTemplate'))
    elif cfgTemplate != None:
        cfgTemplateDir = config.get('DMT_LANDSCAPE', 'cfgTemplateDir')
        torInstSed = config.get('DMT_LANDSCAPE', 'torInstSed')
        singleDeployTemplate = os.path.join(cfgTemplateDir,cfgTemplate + "_" + torInstSed)
    else:
        singleDeployTemplate = os.path.join(config.get('DMT_LANDSCAPE', 'autoConfigTemplate'))
    logger.info("Landscape File Auto Config Template: " +str(singleDeployTemplate))

    if not os.path.exists(singleDeployTemplate):
        raise CommandError("Could not find landscape files at " + singleDeployTemplate)

    # Location of cfg template
    #cfgFile = singleDeployTemplate + "cfgtemplate/cfgtemplate.txt"
    cfgFile = os.path.dirname(singleDeployTemplate)
    cfgName = os.path.basename(singleDeployTemplate)

    # Randomly generated directory with /tmp
    tmpArea = tempfile.mkdtemp()

    # START Service Group Build up
    #Is there Service Cluster/Group/Instances available to support this install
    try:
        sanityCheck = dmt.infoforConfig.ServiceInstCheck(tmpArea,clusterId)
    except Exception as e:
        # Remove local tmp Area if it exists
        dmt.infoforConfig.removeTmpArea(tmpArea)
        raise CommandError("Error with the Service Instances Check : " + str(e))

    #Copy the cfg to tmp Area to a tmp area for editing
    try:
        dmt.utils.copyFiles(cfgFile, tmpArea)
    except Exception as e:
        # Remove local tmp Area if it exists
        dmt.utils.dmtError("Error copying the cfg template : " + str(e))

    # Get enclosure information
    try:
        (enclosuredict, enclosureTypeList) = dmt.infoforConfig.getEnclosureInfo(clusterId)
    except Exception as e:
        # Remove local tmp Area if it exists
        dmt.infoforConfig.removeTmpArea(tmpArea)
        raise CommandError("Error with retrieving enclosure information: " + str(e))

    # Get Node information and a sorted list of the server type in this order SC's, Pl's, NFS, and MS
    try:
        (nodesdict, serverTypeList) = dmt.infoforConfig.getNodeInfo(clusterId, installType)
    except Exception as e:
        # Remove local tmp Area if it exists
        dmt.infoforConfig.removeTmpArea(tmpArea)
        raise CommandError("Error with retrieving Node information: " + str(e))

    # Get Node information for attached OSSRC Deployment and a sorted list of the server type
    try:
        (clusterToClusterdict, clusterToClusterList) = dmt.infoforConfig.clusterToClusterMapping(clusterId)
    except Exception as e:
        # Remove local tmp Area if it exists
        dmt.infoforConfig.removeTmpArea(tmpArea)
        raise CommandError("Error with retrieving Deployment to Deployment Mapping information: " + str(e))

    # Does the Service Group template directory exist if not exit
    if sanityCheck == "ClusterExist":
        # Get JBOSS Cluster information according to deployment information and add to a dict
        try:
            (jbossClusterDict, sortedJBOSSClusterList) = dmt.infoforConfig.getjbossClusterinfo(clusterId)
        except Exception as e:
            # Remove local tmp Area if it exists
            dmt.infoforConfig.removeTmpArea(tmpArea)
            raise CommandError("Error with retrieving JBOSS Cluster information: " + str(e))

        # Get Service group information according to deployment information and add to a dict
        try:
            (serviceGrpDict, sortedGrpList, sortedpkglist, serviceGrpInsDict, sortedGrpInslist) = dmt.infoforConfig.getServiceGroupInfo(clusterId)
        except Exception as e:
            # Remove local tmp Area if it exists
            dmt.infoforConfig.removeTmpArea(tmpArea)
            raise CommandError("Error with retrieving Service Group information: " + str(e))

        # Get Service instance information according to deployment information and add to a dict
        try:
            (serviceInstDict, sortedInstList) = dmt.infoforConfig.getServiceInstInfo(clusterId)
        except Exception as e:
            # Remove local tmp Area if it exists
            dmt.infoforConfig.removeTmpArea(tmpArea)
            raise CommandError("Error with retrieving Service Instance information: " + str(e))

        try:
            nasStorageClusterDict = dmt.infoforConfig.getNASStorageDetails(clusterId)
            logger.info("Successfully retreived NAS and Storage details")
        except Exception as e:
            logger.error("Issue get NAS and Storage details: " +str(e))
            return 1

        try:
            nasStorageOSSClusterDict = dmt.infoforConfig.getNASStorageDetailsOSS(clusterId)
            logger.info("Successfully retreived OSS-RC NAS and Storage details")
        except Exception as e:
            logger.error("Issue get OSS-RC NAS and Storage details: " +str(e))
            return 1

        try:
            multiNodeDict = dmt.infoforConfig.getMultiNodeDetails(clusterId)
            logger.info("Multi Node enclosure data executed with success")
        except Exception as e:
            logger.error("Multi Node enclosure data executed with error: " +str(e))
            return 1
    else:
        logger.info("INFO: Unable to find service group info for this deployment. Skipping.....")

    dictIterateList = nodesdict, multiNodeDict, enclosuredict, clusterToClusterdict, jbossClusterDict, serviceGrpDict, serviceGrpInsDict, serviceInstDict, nasStorageClusterDict, nasStorageOSSClusterDict
    for infoDict in dictIterateList:
        try:
            dmt.infoforConfig.createconfig(tmpArea, infoDict, cfgName)
        except Exception as e:
            # Remove local tmp Area if it exists
            dmt.infoforConfig.removeTmpArea(tmpArea)
            raise CommandError("Error with creating config file: " + str(e))

    try:
        dmt.infoforConfig.cleanUpFile(tmpArea, cfgName)
    except Exception as e:
        # Remove local tmp Area if it exists
        dmt.infoforConfig.removeTmpArea(tmpArea)
        raise CommandError("Error with the template clean-up function: " + str(e))
    if webRun != None:
        return tmpArea, cfgName
    else:
        # Remove local tmp Area if it exists
        #dmt.infoforConfig.removeTmpArea(tmpArea)
        return 0

def writeDBConfigToFile(sed, fileName, tmpArea):
    '''
    Function used to write a string to a file
    Inputs: The String to parse and the name of the file to create
    Output: The directory the file is stored in
    '''
    try:
        logger.info("Writing file to " + str(tmpArea))
        sed = sed.replace('\r','')
        textFile = open(tmpArea + "/" + fileName, "w")
        textFile.write(sed)
        textFile.close()
        return 0
    except Exception as e:
        logger.error("Problem creating the SED File " + str(e))
        dmt.utils.removeTmpArea(tmpArea)
        return 1

def saveSedFile(sed, fileName):
    '''
    Function used to write a string to a file
    Inputs: The String to parse and the name of the file to create
    Output: The URL to the file created
    '''
    try:
        uploadPath = path = config.get('DMT_AUTODEPLOY', 'sedUploadpath')
        sedUploadDir = os.path.join(uploadPath, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        try:
            os.makedirs(sedUploadDir)
        except OSError, e:
            if e.errno != 17:
                raise Exception
        logger.info("Writing file to " + str(sedUploadDir))
        sed = sed.replace('\r','')
        textFile = open(sedUploadDir + "/" + fileName, "w")
        textFile.write(sed)
        textFile.close()
        sedUrlFilePath =  "/static/tmpUploadSed/" + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + "/" + fileName
        return (0, sedUrlFilePath)
    except Exception as e:
        logger.error("Problem saving the SED File " + str(e))
        dmt.utils.removeSedUploadDir(sedUploadDir)
        return 1


def generateDBConfigFile(clusterId, sedVersion):
    '''
    Retrieves deployment information and populates SED template
    '''
    if not Cluster.objects.filter(id=clusterId).exists():
        logger.error("Deployment ID: "+str(clusterId)+" does not exist")
        return "Deployment ID: "+str(clusterId)+" does not exist"

    # Get enclosure information
    try:
        (enclosuredict, enclosureTypeList) = dmt.infoforConfig.getEnclosureInfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving enclosure information: " + str(e))

    # Get Node information and a sorted list of the server type in this order SC's, Pl's, NFS, and MS
    try:
        (nodesdict, serverTypeList) = dmt.infoforConfig.getNodeInfo(clusterId, "webRun")
    except Exception as e:
        raise CommandError("Error with retrieving Node information: " + str(e))

    # Get Node information for attached OSSRC Deployment and a sorted list of the server type
    try:
        (clusterToClusterdict, clusterToClusterList) = dmt.infoforConfig.clusterToClusterMapping(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving Deployment to Deployment Mapping information: " + str(e))

    # Get JBOSS Cluster information according to deployment information and add to a dict
    try:
        (jbossClusterDict, sortedJBOSSClusterList) = dmt.infoforConfig.getjbossClusterinfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving JBOSS Cluster information: " + str(e))

    try:
        (clusterMulticastDict, sortedclusterMulticastList) = dmt.infoforConfig.getClusterMulticastInfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving Cluster Multicast information: " + str(e))

    # Get VLAN Cluster Multicast information according to deployment
    try:
        vlanClusterMulticastDict = dmt.infoforConfig.getVlanClusterMulticastInfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving Vlan Cluster Multicast information: " + str(e))

    try:
        (databaseVipDict, sortedDatabaseVipList) = dmt.infoforConfig.getDatabaseVipInfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving the Database VIP information: " + str(e))

    # Get Service group information according to deployment information and add to a dict
    try:
        (serviceGrpDict, sortedGrpList, sortedpkglist, serviceGrpInsDict, sortedGrpInslist) = dmt.infoforConfig.getServiceGroupInfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving Service Group information: " + str(e))

    # Get Service instance information according to deployment information and add to a dict
    try:
        (serviceInstDict, sortedInstList) = dmt.infoforConfig.getServiceInstInfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving Service Instance information: " + str(e))

    try:
        (virtualImageDict, sortedVirtualImageList) = dmt.infoforConfig.getVirtualImageIpInfo(clusterId)
    except Exception as e:
        raise CommandError("Error with retrieving Service Instance information: " + str(e))

    try:
        nasStorageClusterDict = dmt.infoforConfig.getNASStorageDetails(clusterId)
        logger.info("Successfully retreived NAS and Storage details")
    except Exception as e:
        logger.error("Issue get NAS and Storage details: " +str(e))
        return 1

    try:
        nasStorageOSSClusterDict = dmt.infoforConfig.getNASStorageDetailsOSS(clusterId)
        logger.info("Successfully retreived OSS-RC NAS and Storage details")
    except Exception as e:
        logger.error("Issue get OSS-RC NAS and Storage details: " +str(e))
        return 1

    try:
        multiNodeDict = dmt.infoforConfig.getMultiNodeDetails(clusterId)
        logger.info("Multi Node enclosure data executed with success")
    except Exception as e:
        logger.error("Multi Node enclosure data executed with error: " +str(e))
        return 1

    try:
        lvsRouterVipDict = dmt.infoforConfig.getLVSRouterVipInfo(clusterId)
        logger.info("LVS Router data executed with success")
    except Exception as e:
        logger.error("LVS Router data executed with error: " +str(e))
        return 1
    try:
        hybridCloudDict = dmt.infoforConfig.getHybridCloudInfo(clusterId)
        logger.info("Hybrid Cloud data executed with success")
    except Exception as e:
        hybridCloudDict = {}
        logger.error("Hybrid Cloud data executed with error: " +str(e))
        return 1
    try:
        dvmsInformationDict = dmt.infoforConfig.getDvmsInformation(clusterId)
        logger.info("Dvms Information data executed with success")
    except Exception as e:
        dvmsInformationDict = {}
        logger.error("Dvms Information data executed with error: " +str(e))
        return 1

    if Sed.objects.filter(version=sedVersion).exists():
        sedVersionObj = Sed.objects.get(version=sedVersion)
        template= sedVersionObj.sed
    elif str(sedVersion) == "all":
        completeSedList = []
        sedList = []
        template = ""
        for sedObj in Sed.objects.all():
            sedList = str(sedObj.sed).split('\r')
            for item in sedList:
                if item not in completeSedList:
                    completeSedList.append(item)
        for line in completeSedList:
            template = template + str(line) + '\r'
    else:
        logger.error("SED version "+str(sedVersion)+" does not exist")
        return "SED Version "+str(sedVersion)+" does not exist"

    newTemplate = ""
    dictIterateList = vlanClusterMulticastDict, hybridCloudDict, dvmsInformationDict, lvsRouterVipDict, nodesdict, multiNodeDict, enclosuredict, clusterToClusterdict, jbossClusterDict, clusterMulticastDict, databaseVipDict, serviceGrpDict, serviceGrpInsDict, serviceInstDict, virtualImageDict,  nasStorageClusterDict, nasStorageOSSClusterDict
    for infoDict in dictIterateList:
        try:
            template = dmt.infoforConfig.createconfigDb(infoDict,template)
        except Exception as e:
            raise CommandError("Error with creating config file: " + str(e))
    #Append SED version to SED
    template = "#SED Template Version: "+str(sedVersion)+"\r\n"+template
    if "Hardware_Type=cloud" in template and "SVC" in str(serverTypeList):
        template = template + "\r\n"
        uuidBootvg = "uuid_bootvg_"
        kgbString = "=kgb\r\n"
        for serverType in serverTypeList:
            if "DB" in serverType:
                template = template + uuidBootvg + serverType + kgbString
            if "SVC" in serverType:
                svcString = uuidBootvg + serverType + kgbString
                svcString = svcString.replace('-','')
                template = template + svcString
            if "STR" in serverType:
                strString = uuidBootvg + serverType + kgbString
                strString = strString.replace('-','')
                template = template + strString
    template = dmt.infoforConfig.cleanUpFileDb(template)
    return template
