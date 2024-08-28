from ConfigParser import SafeConfigParser
from cireports.models import *
from dmt.models import *
from ciconfig import CIConfig
from django.core.management.base import BaseCommand, CommandError
from django.http import HttpResponse, Http404, HttpResponseRedirect
from netaddr import IPNetwork
from lxml import etree
from sets import Set

import ast
import commands
import cireports.utils
import subprocess
import urllib2
import gzip
import dmt.sshtunnel
import dmt.sftp
import fwk.utils
import dmt.cloud
import subprocess, os, sys, time, getpass, signal, urllib2, traceback, socket, logging, re
import random, pexpect, paramiko, tempfile, shutil, struct
import tarfile
import distutils.dir_util
import os.path
import zipfile
import shutil
from dmt.utils import handlingError, copyFiles, checkServiceGroupInstanceIpAddress
from django.core.servers.basehttp import FileWrapper
from django.conf import settings
import mimetypes

paramiko.util.log_to_file('/tmp/paramiko.log')

logger = logging.getLogger(__name__)
config = CIConfig()

def grep(patt,file):
    '''
    Finds pattern in file - pattiern is a compiled regex
    returns all lines that match pattern

    Parameters taken in is the pattern and a file to search through
    '''
    matchlines = []
    for line in file:
        match = patt.search(line)
        if match:
            matchline = match.group()
            matchlines.append(matchline)
    results = '\n '.join(matchlines)
    if results:
        return results
    else:
        return None

def removeTmpArea(tmpArea):
    '''
    Function used to removed a given directory
    '''
    try:
        if (os.path.exists(tmpArea)):
            shutil.rmtree(tmpArea)
            logger.info("Successfully Removed the " + str(tmpArea))
    except Exception as e:
        raise CommandError("There was a problem removing the tmpArea "  + str(tmpArea))

def ServiceInstCheck(tmpArea,clusterId):
    '''
    Class used to ensure the required resources are allocated
    '''
    ServicesClr = ServicesCluster.objects.filter(cluster_id=clusterId)
    if not ServicesClr:
        return "NoCluster"
    else:
        for servClr in ServicesClr:
            serviceGrps = ServiceGroup.objects.filter(service_cluster_id=servClr.id)
            if servClr.name == "Apache Service Cluster":
                runClustersection = "ClusterExist"
                continue
            logger.info("Check Service Groups and instances for Deployment :" + str(servClr.name))
            if len(serviceGrps) < 1:
                removeTmpArea(tmpArea)
                handlingError("\nWarning no groups assigned to " + str(servClr.name) +". Please assign group(s)")
            for serviceGroup in serviceGrps:
                serviceInst = ServiceGroupInstance.objects.filter(service_group=serviceGroup.id)
                if len(serviceInst) < 1:
                    removeTmpArea(tmpArea)
                    handlingError("\nWarning no service instances assigned to " + str(serviceGroup.name) + " within deployment " + str(servClr.name))
                return "ClusterExist"
        return runClustersection

def ServiceInstCheckDb(clusterId):
    '''
    Class used to ensure the required resources are allocated
    '''
    ServicesClr = ServicesCluster.objects.filter(cluster_id=clusterId)
    if not ServicesClr:
        return "NoCluster"
    else:
        for servClr in ServicesClr:
            serviceGrps = ServiceGroup.objects.filter(service_cluster_id=servClr.id)
            if servClr.name == "Apache Service Cluster":
                runClustersection = "ClusterExist"
                continue
            logger.info("Check Service Groups and instances for Deployment :" + str(servClr.name))
            if len(serviceGrps) < 1:
                handlingError("\nWarning no groups assigned to " + str(servClr.name) +". Please assign group(s)")
            for serviceGroup in serviceGrps:
                serviceInst = ServiceGroupInstance.objects.filter(service_group=serviceGroup.id)
                if len(serviceInst) < 1:
                    handlingError("\nWarning no service instances assigned to " + str(serviceGroup.name) + " within deployment " + str(servClr.name))
                return "ClusterExist"
        return runClustersection


def createconfig(tmpArea, nodeTypevalue, configfile):
    '''
    Function used to edit the file with the information from within the Dict

    Parameters Taken in tmp file location, nodeTypevalue entries from the dict according to the type i.e jee{1,2,3}
    configfile file to read and the newConfigData the new file name to create
    '''
    for nodeKey, nodeValue in nodeTypevalue.items():
        for Key, Value in nodeValue.items():
            oldConfig = open(tmpArea + "/" + configfile,  "rb")
            newConfig = open(tmpArea + "/" + configfile + "_out", "ab")
            while 1:
                line = oldConfig.readline()
                if not line:
                    break
                if str(Key) in line:
                    line = line.replace(str(Key),str(Value))
                newConfig.write(line)
                # Set the output file to the new file for the next iteration
            new_file_name = configfile
            updated_file_name = configfile + '_out'
            os.rename(os.path.join(tmpArea, updated_file_name), os.path.join(tmpArea, new_file_name))
            oldConfig.close()
            newConfig.close()

def createconfigDb(nodeTypeValue,template):
    '''
    Function used to populate template with information from within the Dict
    '''
    for nodeKey, nodeValue in nodeTypeValue.items():
        for Key, Value in nodeValue.items():
            template = template.replace(str(Key),str(Value))
    return template


def appendToConfig(tmpArea, value, configfile):
    '''
    Function used to edit the file with the information from within the Dict

    Parameters Taken in tmp file location, value entries from the dict according to the type i.e jee{1,2,3}
    and the config file to read
    '''
    for key, value in value.items():
        config = open(tmpArea + "/" + configfile,  "ab")
        config.write(key + "=" + value +"\n")
        config.write
    config.close()

def cleanUpFile(tmpArea, configfile):
    oldConfig = open(tmpArea + "/" + configfile,  "rb")
    newConfig = open(tmpArea + "/" + configfile + "_out", "ab")
    while 1:
        line = oldConfig.readline()
        line.rstrip()
        if not line:
            break
        if "<" in line:
            if 'node' in line:
                continue
            else:
               line = re.sub('<.*>', '', line)
        newConfig.write(line)
        # Set the output file to the new file for the next iteration
    new_file_name = configfile
    updated_file_name = configfile + '_out'
    os.rename(os.path.join(tmpArea, updated_file_name), os.path.join(tmpArea, new_file_name))
    oldConfig.close()
    newConfig.close()


def cleanUpFileDb(sedFile):
    '''
    Removes unwanted content from Sed file
    '''
    lineList = sedFile.split('\n')
    newSed = ""
    for line  in lineList :
        if "<" in line:
            if '_node' in line:
                continue
            else:
               line = re.sub('<.*>', '', line)
        line.rstrip()
        newSed=newSed+str(line)+"\n"
    return newSed

def getVlanClusterMulticastInfo(clusterId):
    '''
    Class used to get the Vlan Cluster Multicast information according to the deployment id
    '''
    vlanClusterMulticastDict = {}
    clusterObject = Cluster.objects.get(id=clusterId)
    # Get vlan cluster multicast according to Deployment id
    if VlanClusterMulticast.objects.filter(cluster=clusterObject).exists():
        fields = ("multicast_type__name", "multicast_snooping", "multicast_querier", "multicast_router", "hash_max",)
        name = "VLAN CLUSTER MULTICAST"
        vlanClusterMulticastDict[name] = {}
        vlanClusterMulticasts = VlanClusterMulticast.objects.only(fields).values(*fields).filter(cluster=clusterObject)
        for vlanClusterMulticast in vlanClusterMulticasts:
            vlanClusterMulticastDict[name]["<" + vlanClusterMulticast["multicast_type__name"] + "_MULTICAST_SNOOPING>"] = vlanClusterMulticast["multicast_snooping"]
            vlanClusterMulticastDict[name]["<" + vlanClusterMulticast["multicast_type__name"] + "_MULTICAST_QUERIER>"] = vlanClusterMulticast["multicast_querier"]
            vlanClusterMulticastDict[name]["<" + vlanClusterMulticast["multicast_type__name"] + "_MULTICAST_ROUTER>"] = vlanClusterMulticast["multicast_router"]
            vlanClusterMulticastDict[name]["<" + vlanClusterMulticast["multicast_type__name"] + "_HASH_MAX>"] = vlanClusterMulticast["hash_max"]
    return vlanClusterMulticastDict

def getClusterMulticastInfo(clusterId):
    '''
    Class used to get the Cluster Multicast information according to the deployment id
    '''
    clusterMulticastDict = {}
    sortedClusterMulticastList = []
    # Get cluster multicast according to Deployment id
    if ClusterMulticast.objects.filter(cluster_id=clusterId).exists():
        multicast = ClusterMulticast.objects.get(cluster_id=clusterId)
        name = "CLUSTER_MULTICAST"
        sortedClusterMulticastList.append(name)
        clusterMulticastDict[name]={}
        # Add multicast info
        clusterMulticastDict[name]["<" + name + "_MESSAGE_ADDRESS>"] = multicast.enm_messaging_address.address
        clusterMulticastDict[name]["<" + name + "_MESSAGE_PORT>"] = multicast.enm_messaging_port
        clusterMulticastDict[name]["<" + name + "_UDP_ADDRESS>"] = multicast.udp_multicast_address.address
        clusterMulticastDict[name]["<" + name + "_UDP_PORT>"] = multicast.udp_multicast_port
    # Sort the list of ip-address id's
    sortedClusterMulticastList.sort()
    return (clusterMulticastDict, sortedClusterMulticastList)

def getDatabaseVipInfo(clusterId):
    '''
    Class used to get the Database VIP information according to the deploymentid
    '''
    databaseVipDict = {}
    sortedDatabaseVipList = []
    # Get cluster multicast according to Deployment id
    if DatabaseVips.objects.filter(cluster_id=clusterId).exists():
        databaseVipObj = DatabaseVips.objects.get(cluster_id=clusterId)
        name = "DATABASE_VIP"
        sortedDatabaseVipList.append(name)
        databaseVipDict[name]={}
        # Add vip info
        if DatabaseVips.objects.filter(cluster_id=clusterId,postgres_address_id__isnull=False).exists():
            databaseVipDict[name]["<POSTGRES_VIP>"] = databaseVipObj.postgres_address.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,versant_address_id__isnull=False).exists():
            databaseVipDict[name]["<VERSANT_VIP>"] = databaseVipObj.versant_address.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,mysql_address_id__isnull=False).exists():
            databaseVipDict[name]["<MYSQL_VIP>"] = databaseVipObj.mysql_address.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,opendj_address_id__isnull=False).exists():
            databaseVipDict[name]["<OPENDJ_VIP>"] = databaseVipObj.opendj_address.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,opendj_address2_id__isnull=False).exists():
            databaseVipDict[name]["<OPENDJ_VIP2>"] = databaseVipObj.opendj_address2.address
        elif DatabaseVips.objects.filter(cluster_id=clusterId,opendj_address_id__isnull=False).exists():
            databaseVipDict[name]["<OPENDJ_VIP2>"] = databaseVipObj.opendj_address.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,jms_address_id__isnull=False).exists():
            databaseVipDict[name]["<JMS_VIP>"] = databaseVipObj.jms_address.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,eSearch_address_id__isnull=False).exists():
            databaseVipDict[name]["<ELASTICSEARCH_VIP>"] = databaseVipObj.eSearch_address.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,neo4j_address1_id__isnull=False).exists():
            databaseVipDict[name]["<NEO4J_VIP1>"] = databaseVipObj.neo4j_address1.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,neo4j_address2_id__isnull=False).exists():
            databaseVipDict[name]["<NEO4J_VIP2>"] = databaseVipObj.neo4j_address2.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,neo4j_address3_id__isnull=False).exists():
            databaseVipDict[name]["<NEO4J_VIP3>"] = databaseVipObj.neo4j_address3.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,gossipRouter_address1_id__isnull=False).exists():
            databaseVipDict[name]["<GOSSIPROUTER_VIP1>"] = databaseVipObj.gossipRouter_address1.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,gossipRouter_address2_id__isnull=False).exists():
            databaseVipDict[name]["<GOSSIPROUTER_VIP2>"] = databaseVipObj.gossipRouter_address2.address
        if DatabaseVips.objects.filter(cluster_id=clusterId,eshistory_address_id__isnull=False).exists():
            databaseVipDict[name]["<ESHISTORY_VIP>"] = databaseVipObj.eshistory_address.address
    # Sort the list of ip-address id's
    sortedDatabaseVipList.sort()
    return (databaseVipDict, sortedDatabaseVipList)

def getjbossClusterinfo(clusterId):
    '''
    Class used to get the jboss Cluster information according to the deploymentid
    '''
    jbossClusterDict = {}
    sortedJBOSSClusterList = []
    # Get Services deployment according to Deployment id
    ServicesClr = ServicesCluster.objects.filter(cluster_id=clusterId)
    for servClr in ServicesClr:
        if "LSB" in servClr.name:
            continue
        # Get Service Groups according to Deployment ID
        jeename = servClr.name
        jbossname = re.sub('jee','jboss', jeename)
        jeespace = re.sub('_',' ', jeename)
        if jeename == "LSB Service Cluster":
            continue
        if Multicast.objects.filter(service_cluster_id=servClr.id).exists():
            multicast = Multicast.objects.get(service_cluster_id=servClr.id)

            sortedJBOSSClusterList.append(jeename)
            jbossClusterDict[jeename]={}
            # Add multicast info per jee container
            jbossClusterDict[jeename]["<" + jeename + "_JBOSS_CLUSTER>"] = str(jeename)
            jbossClusterDict[jeename]["<" + jeename + "_JBOSSNAME_CLUSTER>"] = str(jbossname)
            jbossClusterDict[jeename]["<" + jeename + "_JBOSS_ID_NO_UND>"] = str(jeespace)
            jbossClusterDict[jeename]["<" + jeename + "_DEFAULT_MCAST_ADDRESS>"] = multicast.ipMapDefaultAddress.address
            jbossClusterDict[jeename]["<" + jeename + "_DEFAULT_MCAST_PORT>"] = multicast.default_mcast_port
            jbossClusterDict[jeename]["<" + jeename + "_MESSAGING_GROUP_ADDRESS>"] = multicast.ipMapMessagingGroupAddress.address
            jbossClusterDict[jeename]["<" + jeename + "_UDP_MCAST_ADDRESS>"] = multicast.ipMapUdpMcastAddress.address
            jbossClusterDict[jeename]["<" + jeename + "_UDP_MCAST_PORT>"] = multicast.udp_mcast_port
            jbossClusterDict[jeename]["<" + jeename + "_GROUP_MPING_ADDRESS>"] = multicast.ipMapMpingMcastAddress.address
            jbossClusterDict[jeename]["<" + jeename + "_GROUP_MPING_PORT>"] = multicast.mping_mcast_port
            jbossClusterDict[jeename]["<" + jeename + "_MESSAGING_GROUP_PORT>"] = multicast.messaging_group_port
            jbossClusterDict[jeename]["<" + jeename + "_PUBLIC_PORT_BASE>"] = multicast.public_port_base
    # Sort the list of ip-address id's
    sortedJBOSSClusterList.sort()
    return (jbossClusterDict, sortedJBOSSClusterList)

def getNASStorageDetails(clusterId):
    '''
    The getNASDetails function populates the config file with NAS details
    '''
    nasStorageClusterDict = {}
    sortedNASStorageClusterList = []

    nasIpAddress = ""
    nasHostname = ""
    sanPoolName = ""
    sanPoolId = ""
    sanRaidGroup = ""
    nasGateway = ""
    nasBitmask = ""
    nasNic = ""
    storageHostname = ""
    vnxType = ""
    storageSerialNum = ""
    storage_IP_1 = ""
    storage_IP_2 = ""
    storageUser = ""
    storagePassword = ""
    poolFS1 = ""
    poolFS2 = ""
    poolFS3 = ""
    vipSeg1Address = ""
    nasVIP1Address = ""
    nasVIP2Address = ""
    nasInstallIp1 = ""
    nasInstallIp2 = ""

    fileSystem1 = ""
    fileSystem2 = ""
    fileSystem3 = ""
    nasMasterUsername = ""
    nasMasterPassword = ""
    nasSupportUsername = ""
    nasSupportPassword = ""
    nasMasterIloUsername = ""
    nasMasterIloPassword = ""
    nasSupportIloUsername = ""
    nasSupportIloPassword = ""
    nasInstallIloIp1Username = ""
    nasInstalIlolIp1Password = ""
    nasInstallIloIp2Username = ""
    nasInstalIlolIp2Password = ""
    nasInstalIlolIp1 = ""
    nasInstalIlolIp2 = ""
    sfsNode1Hostname = ""
    sfsNode2Hostname = ""
    nasType = ""
    nasNdmpPassword = ""
    nasServerPrefix = ""
    fcSwitches = ""

    nasEthernetPorts = ""
    sanAdminPassword = ""
    sanPoolDiskCount = ""
    sanServicePassword = ""

    try:
        if ClusterToNASMapping.objects.filter(cluster_id=clusterId).exists():
            clusterToNasMapObj = ClusterToNASMapping.objects.get(cluster_id=clusterId)
            if NASServer.objects.filter(id=clusterToNasMapObj.nasServer_id).exists():
                nasServerObj = NASServer.objects.get(id=clusterToNasMapObj.nasServer_id)
                sfsNode1Hostname = nasServerObj.sfs_node1_hostname
                sfsNode2Hostname = nasServerObj.sfs_node2_hostname
                nasStorageDtlsObj = NasStorageDetails.objects.get(cluster_id=clusterId)
                if NasStorageDetails.objects.filter(cluster=clusterId).exists():
                    nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=clusterId)
                    sanPoolName = str(nasStorageDtlsObj.sanPoolName)
                    sanPoolId = str(nasStorageDtlsObj.sanPoolId)
                    sanRaidGroup = str(nasStorageDtlsObj.sanRaidGroup)
                    poolFS1 =  str(nasStorageDtlsObj.poolFS1)
                    fileSystem1 = str(nasStorageDtlsObj.fileSystem1)
                    poolFS2 =  str(nasStorageDtlsObj.poolFS2)
                    fileSystem2 = str(nasStorageDtlsObj.fileSystem2)
                    poolFS3 =  str(nasStorageDtlsObj.poolFS3)
                    fileSystem3 = str(nasStorageDtlsObj.fileSystem3)
                    nasType = "" if nasStorageDtlsObj.nasType == None else str(nasStorageDtlsObj.nasType)
                    nasNdmpPassword = "" if nasStorageDtlsObj.nasNdmpPassword == None else str(nasStorageDtlsObj.nasNdmpPassword)
                    nasServerPrefix = "" if nasStorageDtlsObj.nasServerPrefix == None else str(nasStorageDtlsObj.nasServerPrefix)
                    fcSwitches = "" if nasStorageDtlsObj.fcSwitches == None else str(nasStorageDtlsObj.fcSwitches).lower()
                    nasEthernetPorts = str(nasStorageDtlsObj.nasEthernetPorts)
                    sanPoolDiskCount = str(nasStorageDtlsObj.sanPoolDiskCount)
                serverObject = NASServer.objects.filter(server=nasServerObj.server_id)
                credentials = []
                for obj in serverObject:
                    credentials += Credentials.objects.filter(id=obj.credentials_id)

                for item in credentials:
                    if item.credentialType == 'master':
                        nasMasterUsername=item.username
                        nasMasterPassword=item.password
                    elif item.credentialType == 'support':
                        nasSupportUsername = item.username
                        nasSupportPassword = item.password
                    elif item.credentialType == 'masterIlo':
                        nasMasterIloUsername = item.username
                        nasMasterIloPassword = item.password
                    elif item.credentialType == 'supportIlo':
                        nasSupportIloUsername = item.username
                        nasSupportIloPassword = item.password
                    elif item.credentialType == 'nasInstalIlolIp1':
                        nasInstallIloIp1Username = item.username
                        nasInstalIlolIp1Password = item.password
                    elif item.credentialType == 'nasInstalIlolIp2':
                        nasInstallIloIp2Username = item.username
                        nasInstalIlolIp2Password = item.password
                if Server.objects.filter(id=nasServerObj.server_id).exists():
                    serverObj = Server.objects.get(id=nasServerObj.server_id)
                    nasHostname = serverObj.hostname
                    if NetworkInterface.objects.filter(server=serverObj).exists():
                        nicObj = NetworkInterface.objects.get(server=serverObj)
                        nasNic = nicObj.mac_address
                        if IpAddress.objects.filter(nic=nicObj,ipType="nas").exists():
                            ipAddrObjecthost = IpAddress.objects.get(nic=nicObj,ipType="nas")
                            nasIpAddress = ipAddrObjecthost.address
                            nasBitmask = ipAddrObjecthost.bitmask
                            nasGateway = ipAddrObjecthost.gateway_address

                        if IpAddress.objects.filter(nic=nicObj,ipType="vipseg1").exists():
                            ipAddrObjectSeg1 = IpAddress.objects.get(nic=nicObj,ipType="vipseg1")
                            vipSeg1Address = ipAddrObjectSeg1.address
                        else:
                            vipSeg1Address = ""

                        if IpAddress.objects.filter(nic=nicObj,ipType="nasvip1").exists():
                            ipAddrObjectNASVIP1 = IpAddress.objects.get(nic=nicObj,ipType="nasvip1")
                            nasVIP1Address = ipAddrObjectNASVIP1.address
                        else:
                            nasVIP1Address = ""

                        if IpAddress.objects.filter(nic=nicObj,ipType="nasvip2").exists():
                            ipAddrObjectNASVIP2 = IpAddress.objects.get(nic=nicObj,ipType="nasvip2")
                            nasVIP2Address = ipAddrObjectNASVIP2.address
                        else:
                            nasVIP2Address = ""

                        if IpAddress.objects.filter(nic=nicObj,ipType="nasinstallip1").exists():
                            ipAddrObjNasInstallIp1 = IpAddress.objects.get(nic=nicObj,ipType="nasinstallip1")
                            nasInstallIp1 = ipAddrObjNasInstallIp1.address
                        else:
                            nasInstallIp1 = ""

                        if IpAddress.objects.filter(nic=nicObj,ipType="nasinstallip2").exists():
                            ipAddrObjNasInstallIp2 = IpAddress.objects.get(nic=nicObj,ipType="nasinstallip2")
                            nasInstallIp2 = ipAddrObjNasInstallIp2.address
                        else:
                            nasInstallIp2 = ""

                        if IpAddress.objects.filter(nic=nicObj,ipType="nasinstalilolip1").exists():
                            ipAddrObjNasInstallIloIp1 = IpAddress.objects.get(nic=nicObj,ipType="nasinstalilolip1")
                            nasInstalIlolIp1 = ipAddrObjNasInstallIloIp1.address
                        else:
                            nasInstalIlolIp1 = ""

                        if IpAddress.objects.filter(nic=nicObj,ipType="nasinstalilolip2").exists():
                            ipAddrObjNasInstallIloIp2 = IpAddress.objects.get(nic=nicObj,ipType="nasinstalilolip2")
                            nasInstalIlolIp2 = ipAddrObjNasInstallIloIp2.address
                        else:
                            nasInstalIlolIp2 = ""

                if ClusterToStorageMapping.objects.filter(cluster_id=clusterId).exists():
                    clsNasMapObj = ClusterToStorageMapping.objects.get(cluster_id=clusterId)
                    storageIpMapList = StorageIPMapping.objects.filter(storage=clsNasMapObj.storage)
                    for storageIp in storageIpMapList:
                        storageHostname = storageIp.storage.hostname
                        storageSerialNum = "" if storageIp.storage.serial_number == None else storageIp.storage.serial_number
                        vnxType = storageIp.storage.vnxType
                        sanAdminPassword = "" if storageIp.storage.sanAdminPassword == None else storageIp.storage.sanAdminPassword
                        sanServicePassword = "" if storageIp.storage.sanServicePassword == None else storageIp.storage.sanServicePassword
                        if "(" in vnxType:
                            vnxType = str(vnxType).split("(")
                            vnxType = vnxType[1]
                            vnxType = vnxType.replace(')','')
                        storageUser = storageIp.storage.credentials.username
                        storagePassword = storageIp.storage.credentials.password
                        if storageIp.ipnumber == 1:
                            storage_IP_1 = storageIp.ipaddr
                        elif storageIp.ipnumber == 2:
                            storage_IP_2 = storageIp.ipaddr
            logger.info("NAS and Storage data retreived from DB")
        elif ClusterToDASNASMapping.objects.filter(cluster_id=clusterId).exists():
            clusterToNasDasMapObj = ClusterToDASNASMapping.objects.get(cluster_id=clusterId)
            if Server.objects.filter(id=clusterToNasDasMapObj.dasNasServer_id).exists():
                serverObj = Server.objects.get(id=clusterToNasDasMapObj.dasNasServer_id)
                nasServerObject = NASServer.objects.filter(server=serverObj)
                credentials = []
                for obj in nasServerObject:
                    credentials += Credentials.objects.filter(id=obj.credentials_id)
                for item in credentials:
                    if item.credentialType == 'master':
                        nasMasterUsername=item.username
                        nasMasterPassword=item.password
                    elif item.credentialType == 'support':
                        nasSupportUsername = item.username
                        nasSupportPassword = item.password
                    elif item.credentialType == 'masterIlo':
                        nasMasterIloUsername = item.username
                        nasMasterIloPassword = item.password
                    elif item.credentialType == 'supportIlo':
                        nasSupportIloUsername = item.username
                        nasSupportIloPassword = item.password
                    elif item.credentialType == 'nasInstalIlolIp1':
                        nasInstallIloIp1Username = item.username
                        nasInstalIlolIp1Password = item.password
                    elif item.credentialType == 'nasInstalIlolIp2':
                        nasInstallIloIp2Username = item.username
                        nasInstalIlolIp2Password = item.password
                if NasStorageDetails.objects.filter(cluster=clusterId).exists():
                    nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=clusterId)
                    poolFS1 =  str(nasStorageDtlsObj.poolFS1)
                nasHostname = serverObj.hostname
                if NetworkInterface.objects.filter(server=serverObj).exists():
                    nicObj = NetworkInterface.objects.get(server=serverObj)
                    nasNic = nicObj.mac_address
                    if IpAddress.objects.filter(nic=nicObj,ipType="nas").exists():
                        ipAddrObjecthost = IpAddress.objects.get(nic=nicObj,ipType="nas")
                        nasIpAddress = ipAddrObjecthost.address
                        nasBitmask = ipAddrObjecthost.bitmask
                        nasGateway = ipAddrObjecthost.gateway_address

                    if IpAddress.objects.filter(nic=nicObj,ipType="vipseg1").exists():
                        ipAddrObjectSeg1 = IpAddress.objects.get(nic=nicObj,ipType="vipseg1")
                        vipSeg1Address = ipAddrObjectSeg1.address
                    else:
                        vipSeg1Address = ""

                    if IpAddress.objects.filter(nic=nicObj,ipType="nasvip1").exists():
                        ipAddrObjectNASVIP1 = IpAddress.objects.get(nic=nicObj,ipType="nasvip1")
                        nasVIP1Address = ipAddrObjectNASVIP1.address
                    else:
                        nasVIP1Address = ""

                    if IpAddress.objects.filter(nic=nicObj,ipType="nasvip2").exists():
                        ipAddrObjectNASVIP2 = IpAddress.objects.get(nic=nicObj,ipType="nasvip2")
                        nasVIP2Address = ipAddrObjectNASVIP2.address
                    else:
                        nasVIP2Address = ""

                    if IpAddress.objects.filter(nic=nicObj,ipType="nasinstallip1").exists():
                        ipAddrObjNasInstallIp1 = IpAddress.objects.get(nic=nicObj,ipType="nasinstallip1")
                        nasInstallIp1 = ipAddrObjNasInstallIp1.address
                    else:
                        nasInstallIp1 = ""

                    if IpAddress.objects.filter(nic=nicObj,ipType="nasinstallip2").exists():
                        ipAddrObjNasInstallIp2 = IpAddress.objects.get(nic=nicObj,ipType="nasinstallip2")
                        nasInstallIp2 = ipAddrObjNasInstallIp2.address
                    else:
                        nasInstallIp2 = ""

                    if IpAddress.objects.filter(nic=nicObj,ipType="nasinstalilolip1").exists():
                        ipAddrObjNasInstallIloIp1 = IpAddress.objects.get(nic=nicObj,ipType="nasinstalilolip1")
                        nasInstalIlolIp1 = ipAddrObjNasInstallIloIp1.address
                    else:
                        nasInstalIlolIp1 = ""

                    if IpAddress.objects.filter(nic=nicObj,ipType="nasinstalilolip2").exists():
                        ipAddrObjNasInstallIloIp2 = IpAddress.objects.get(nic=nicObj,ipType="nasinstalilolip2")
                        nasInstalIlolIp2 = ipAddrObjNasInstallIloIp2.address
                    else:
                        nasInstalIlolIp2 = ""

                logger.info("Direct Attached Storage data retreived from DB")
    except Exception as e:
        logger.error("Problem retrieving NAS and Storage data from DB: " +str(e))
        return 1
    try:
        name = "nasStorageDetails"
        sortedNASStorageClusterList.append(name)
        nasStorageClusterDict[name]={}
        # Get ip information according to id addresss and Bitmask inputted
        if nasIpAddress != "":
            ipInfo = IPNetwork(nasIpAddress + "/" + str(nasBitmask))
            nasStorageClusterDict[name]["<NAS_SUBNET>"] = str(ipInfo.network) + "/" + str(ipInfo.prefixlen)
        else:
            nasStorageClusterDict[name]["<NAS_SUBNET>"] = ""
        # Hostname is used as the SYS ID which can only have alphanumeric values
        editedNasHostname = re.sub(r'\W+', '', nasHostname)
        nasStorageClusterDict[name]["<NAS_SYS_ID>"] = editedNasHostname + str(clusterId)
        nasStorageClusterDict[name]["<NAS_HOSTNAME>"] = nasHostname
        nasStorageClusterDict[name]["<NAS_IP_ADDRESS>"] = nasIpAddress

        if "unityxt" == str(nasType):
            editedStorageHostname = re.sub(r'\W+', '', storageHostname)
            nasStorageClusterDict[name]["<NAS_SYS_ID>"] = editedStorageHostname + str(clusterId)
            nasStorageClusterDict[name]["<NAS_HOSTNAME>"] = storageHostname
            nasStorageClusterDict[name]["<NAS_IP_ADDRESS>"] = storage_IP_1
        nasStorageClusterDict[name]["<NAS_VIP_SEG1>"] = vipSeg1Address
        nasStorageClusterDict[name]["<NAS_VIP_CLOG>"] = nasVIP1Address
        nasStorageClusterDict[name]["<NAS_VIP_TOR1>"] = nasVIP2Address
        nasStorageClusterDict[name]["<STORAGE_VLAN_IP1>"] = nasInstallIp1
        nasStorageClusterDict[name]["<STORAGE_VLAN_IP2>"] = nasInstallIp2
        nasStorageClusterDict[name]["<NAS_UNIQUE_LUN_ID>"] = str(clusterId)
        nasStorageClusterDict[name]["<NAS_POOL>"] = sanPoolName
        nasStorageClusterDict[name]["<NAS_GATEWAY>"] = nasGateway
        nasStorageClusterDict[name]["<NAS_MAC>"] = nasNic
        nasStorageClusterDict[name]["<NAS_MASTER_USERNAME>"] = nasMasterUsername
        nasStorageClusterDict[name]["<NAS_MASTER_PASSWORD>"] = nasMasterPassword
        nasStorageClusterDict[name]["<NAS_SUPPORT_USERNAME>"] = nasSupportUsername
        nasStorageClusterDict[name]["<NAS_SUPPORT_PASSWORD>"] = nasSupportPassword
        nasStorageClusterDict[name]["<SFS_1ST_PHYSICAL_IP>"] = nasInstallIp1
        nasStorageClusterDict[name]["<SFS_2ND_PHYSICAL_IP>"] = nasInstallIp2
        nasStorageClusterDict[name]["<SFS_NODE1_ILO_IP>"] = nasInstalIlolIp1
        nasStorageClusterDict[name]["<SFS_NODE2_ILO_IP>"] = nasInstalIlolIp2
        nasStorageClusterDict[name]["<SFS_NODE1_ILO_HOSTNAME>"] = sfsNode1Hostname
        nasStorageClusterDict[name]["<SFS_NODE2_ILO_HOSTNAME>"] = sfsNode2Hostname
        nasStorageClusterDict[name]["<SFS_NODE1_ILO_USERNAME>"] = nasInstallIloIp1Username
        nasStorageClusterDict[name]["<SFS_NODE1_ILO_PASSWORD>"] = nasInstalIlolIp1Password
        nasStorageClusterDict[name]["<SFS_NODE2_ILO_USERNAME>"] = nasInstallIloIp2Username
        nasStorageClusterDict[name]["<SFS_NODE2_ILO_PASSWORD>"] = nasInstalIlolIp2Password
        nasStorageClusterDict[name]["<SAN_POOLNAME2>"] = sanPoolName
        nasStorageClusterDict[name]["<STORAGE_HOSTNAME>"] = storageHostname
        nasStorageClusterDict[name]["<STORAGE_VNXTYPE>"] = vnxType
        nasStorageClusterDict[name]["<SAN_SERIAL_NUMBER>"] = storageSerialNum
        nasStorageClusterDict[name]["<STORAGE_IPADRESS_1>"] = storage_IP_1
        nasStorageClusterDict[name]["<STORAGE_IPADRESS_2>"] = storage_IP_2
        nasStorageClusterDict[name]["<STORAGE_USERNAME>"] = storageUser
        nasStorageClusterDict[name]["<STORAGE_PASSWORD>"] = storagePassword
        nasStorageClusterDict[name]["<STORAGE_POOL_ID>"] = sanPoolId
        nasStorageClusterDict[name]["<STORAGE_POOL_NAME>"] = sanPoolName
        nasStorageClusterDict[name]["<STORAGE_POOL_RAID_GROUP>"] = sanRaidGroup
        nasStorageClusterDict[name]["<STORAGE_POOL_UNIQUE_ID>"] = clusterId
        nasStorageClusterDict[name]["<NAS_STORAGE_POOL>"] = poolFS1
        nasStorageClusterDict[name]["<STORAGE_ADMIN>"] = fileSystem1
        nasStorageClusterDict[name]["<STORAGE_OBS>"] = fileSystem2
        nasStorageClusterDict[name]["<STORAGE_CLS>"] = fileSystem3
        nasStorageClusterDict[name]["<STORAGE_NAS_TYPE>"] = nasType

        nasStorageClusterDict[name]["<NAS_NDMP_PASSWORD>"] = nasNdmpPassword
        nasStorageClusterDict[name]["<PREFIX_FOR_NAS_SERVER_NAME>"] = nasServerPrefix
        nasStorageClusterDict[name]["<FC_SWITCHES>"] = fcSwitches

        nasStorageClusterDict[name]["<NAS_PORTS>"] = nasEthernetPorts
        nasStorageClusterDict[name]["<SAN_ADMIN_PASSWORD>"] = sanAdminPassword
        nasStorageClusterDict[name]["<TOTAL_DISKS_FOR_POOL>"] = sanPoolDiskCount
        nasStorageClusterDict[name]["<SAN_SERVICE_PASSWORD>"] = sanServicePassword

        logger.info("Build up NAS data in config file")
        return nasStorageClusterDict
    except Exception as e:
        logger.error("Issue building up NAS part of config file: " +str(e))
        return 1

def getServiceGroupInfo(clusterId):
    '''
    Class used to gather the Service group information according to the deployment id
    '''
    # Create an empty dict to store all node information within a dict of dicts
    logger.info("Getting Service group information for Deployment id " + str(clusterId))
    serviceGrpDict={}
    sortedGrpList = []
    serviceGrpInsDict={}
    sortedGrpInslist = []
    # Need to get a list of the packages within the Deployment so we don't download the unwanted packages
    sortedpkglist =[]
    # Get Deployment according to Deployment id
    ServicesClr = ServicesCluster.objects.filter(cluster_id=clusterId)
    for servClr in ServicesClr:
        # Get Service Groups according to JBOSS/Services Cluster ID
        serviceGrps = ServiceGroup.objects.filter(service_cluster_id=servClr.id)
        for serviceGroup in serviceGrps:
            # Get the info for the packages associated to a Service Group
            pkgMap = ServiceGroupPackageMapping.objects.filter(serviceGroup_id=serviceGroup.id)
            pkgList = ""
            delim = ""
            for pm in pkgMap:
                logger.info("TOR Packages to Download according to UI Inputs ::::: " + str(pm.package.name))
                pkgname = re.sub('.*ERIC', '', pm.package.name)
                pkgname = re.sub('_CXP.*', '', pkgname)
                sortedpkglist.append(pkgname)
                pkgList = pkgList + delim + pm.package.name
                delim = ","
            # No need to info for deployment if it's a service cluster
            nodelist = re.sub('-', '', serviceGroup.node_list)
            serviceGrpDict[serviceGroup.name]={}
            serviceGrpDict[serviceGroup.name]["<" + serviceGroup.name + "_SERVICE_GROUP_ID>"] = serviceGroup.name
            serviceGrpDict[serviceGroup.name]["<" + serviceGroup.name + "_SERVICE_GROUP_ID_LWR>"] = serviceGroup.name.lower()
            serviceGrpDict[serviceGroup.name]["<" + serviceGroup.name + "_NODE_LIST>"] = nodelist.lower()
            serviceGrpDict[serviceGroup.name]["<" + serviceGroup.name + "_JBOSS_CLUSTER>"] = serviceGroup.cluster_type
            serviceGrpDict[serviceGroup.name]["<" + serviceGroup.name + "_PACKAGES>"] = pkgList
            serviceInst = ServiceGroupInstance.objects.filter(service_group=serviceGroup.id)
            for inst in serviceInst:
                # This is a second Dict and sorted list for the edit of the service group instance info within the inventory install script
                sortedGrpInslist.append(serviceGroup.name + "_" + inst.name)
                serviceGrpInsDict[serviceGroup.name + "_" + inst.name]={}
                serviceGrpInsDict[serviceGroup.name + "_" + inst.name]["<" + serviceGroup.name + "_SERVICE_GROUP_ID>"] = serviceGroup.name
                serviceGrpInsDict[serviceGroup.name + "_" + inst.name]["<" + serviceGroup.name + "_INSTANCE_NAME>"] = inst.name
                serviceGrpInsDict[serviceGroup.name + "_" + inst.name]["<" + serviceGroup.name + "_INSTANCE_BIND_ADD>"] = inst.ipMap.address
            # Number of instances associated to the object
            activeCount = len(serviceInst)
            serviceGrpDict[serviceGroup.name]["<" + serviceGroup.name + "_ACTIVE-COUNT>"] = str(activeCount)
            #serviceGrpDict[serviceGroup.name]["<ACTIVE-COUNT>"] = "2"
            sortedGrpList.append(serviceGroup.name)
    # Sort the list
    sortedGrpList.sort()
    sortedpkglist.sort()
    sortedGrpInslist.sort()
    # Remove Duplicates
    sortedpkglistset = Set(sortedpkglist)
    sortedpkglist=list(sortedpkglistset)
    return (serviceGrpDict, sortedGrpList, sortedpkglist, serviceGrpInsDict, sortedGrpInslist)

def getServiceInstInfo(clusterId):
    '''
    Class used to gather the Service Instance information according to the deployment id
    '''
    # Create an empty dict to store all node information within a dict of dicts
    logger.info("Getting Service Instance information for Deployment id " + str(clusterId))
    serviceInstDict={}
    sortedInstList = []
    cluster = Cluster.objects.get(id=clusterId)
    # Get info for the MgtServer dns IP address
    dns = cluster.management_server.server.dns_serverA
    # Get Services cluster according to deployment id
    ServicesClr = ServicesCluster.objects.filter(cluster_id=clusterId)
    for servClr in ServicesClr:
        # Get Service Groups according to Deployment ID
        serviceGrps = ServiceGroup.objects.filter(service_cluster_id=servClr.id)
        for serviceGroup in serviceGrps:
            output = ""
            # Get all instances information that corresponds to the serviceGroup.id
            serviceInst = None
            serviceInternalInst = None

            if ServiceGroupInstanceInternal.objects.filter(service_group=serviceGroup.id).exists():
                serviceInternalInst = ServiceGroupInstanceInternal.objects.filter(service_group=serviceGroup.id)
            if ServiceGroupInstance.objects.filter(service_group=serviceGroup.id).exists():
                serviceInst = ServiceGroupInstance.objects.filter(service_group=serviceGroup.id)
            if serviceInst:
                for inst in serviceInst:
                    instName = "ip_" + serviceGroup.name + "_" + str(inst.name) ## ip_PMMed_si_2
                    instNo = re.sub(r'_', '-', str(inst.name))
                    instHostBckUp = serviceGroup.name + "-" + str(instNo) + "-host" ## PMMed_si_2-host
                    sortedInstList.append(instName)
                    serviceInstDict[instName]={}
                    serviceInstDict[instName]["<" + instName + "_NODE_IP>"] = inst.ipMap.address
                    serviceInstDict[instName]["<" + instName + "_NODE_IP_UNSCORE>"] = str(instName)
                    serviceInstDict[instName]["<" + instName + "_NODE_GATEWAY>"] = inst.ipMap.gateway_address
                    serviceInstDict[instName]["<" + instName + "_NODE_NETMASK>"] = inst.ipMap.bitmask
                    if inst.hostname != None:
                        serviceInstDict[instName]["<" + instName + "_UNIT_HOSTNAME>"] = inst.hostname
                        cloudApacheIP = config.get('DMT_AUTODEPLOY', 'cloudApacheIP')
                        if inst.ipMap.address == cloudApacheIP:
                            output = config.get('DMT_AUTODEPLOY', 'cloudDnsFqdn')
                        else:
                            output = inst.hostname + "." + config.get('DMT_SERVER', 'domain')
                    else:
                        ipCheck = checkServiceGroupInstanceIpAddress(inst.ipMap.address)
                        if ipCheck == "notfound":
                            status, output = commands.getstatusoutput("nslookup " + inst.ipMap.address + " " + dns + " | grep name | sed -e 's/.*name = //g' -e 's/.*ame://g' -e 's/\.$//'")
                            if output == "":
                                cloudApacheIP = config.get('DMT_AUTODEPLOY', 'cloudApacheIP')
                                serviceInstDict[instName]["<" + instName + "_UNIT_HOSTNAME>"] = instHostBckUp
                                if inst.ipMap.address == cloudApacheIP:
                                    output = config.get('DMT_AUTODEPLOY', 'cloudDnsFqdn')
                                else:
                                    output = instHostBckUp + "." + config.get('DMT_SERVER', 'domain')
                            else:
                                # changes atrcxbxxx.athtem.eei.ericsson.se to atrcxbxxx
                                (hostname, ath) = output.split('.')[:2]
                                serviceInstDict[instName]["<" + instName + "_UNIT_HOSTNAME>"] = str(hostname)
                        else:
                            serviceInstDict[instName]["<" + instName + "_UNIT_HOSTNAME>"] = instHostBckUp
                            cloudApacheIP = config.get('DMT_AUTODEPLOY', 'cloudApacheIP')
                            if inst.ipMap.address == cloudApacheIP:
                                output = config.get('DMT_AUTODEPLOY', 'cloudDnsFqdn')
                            else:
                                output = instHostBckUp + "." + config.get('DMT_SERVER', 'domain')
                    serviceInstDict[instName]["<" + instName + "_APACHE_FQDN>"] = output
                    # changes atrcxbxxx.athtem.eei.ericsson.se to ericsson se
                    (secondlast, last) = output.split('.')[-2:]
                    serviceInstDict[instName]["<" + instName + "_COOKIE_DOMAIN>"] = "." +str(secondlast)+ "." +str(last)
                    # Get ip information according to id addresss and bitmask inputted
                    ipInfo = IPNetwork(inst.ipMap.address + "/" + str(inst.ipMap.bitmask))
                    serviceInstDict[instName]["<" + instName + "_NODE_NETMASK>"] = str(ipInfo.netmask)
                    serviceInstDict[instName]["<" + instName + "_NODE_NETWORK>"] = str(ipInfo.network)
                    serviceInstDict[instName]["<" + instName + "_NODE_SUBNET>"] = str(ipInfo.network) + "/" + str(ipInfo.prefixlen)
                    serviceInstDict[instName]["<" + instName + "_NODE_CIADDR>"] = str(ipInfo.network) + "/" + str(ipInfo.prefixlen)
                    serviceInstDict[instName]["<" + instName + "_<NODE_BROADCAST>"] = str(ipInfo.broadcast)

            if serviceInternalInst:
                for inst in serviceInternalInst:
                    instName = "ip_" + serviceGroup.name + "_" + str(inst.name)+"_internal" ## ip_PMMed_si_2
                    instNo = re.sub(r'_', '-', str(inst.name))
                    instHostBckUp = serviceGroup.name + "-" + str(instNo) + "-host" ## PMMed_si_2-host
                    sortedInstList.append(instName)
                    serviceInstDict[instName]={}
                    serviceInstDict[instName]["<" + instName + "_NODE_IP>"] = inst.ipMap.address
                    serviceInstDict[instName]["<" + instName + "_NODE_IP_UNSCORE>"] = str(instName)
                    serviceInstDict[instName]["<" + instName + "_NODE_GATEWAY>"] = inst.ipMap.gateway_address
                    serviceInstDict[instName]["<" + instName + "_NODE_NETMASK>"] = inst.ipMap.bitmask
                    serviceInstDict[instName]["<" + instName + "_UNIT_HOSTNAME>"] = instHostBckUp
                    # Get ip information according to id addresss and bitmask inputted
                    ipInfo = IPNetwork(inst.ipMap.address + "/" + str(inst.ipMap.bitmask))
                    serviceInstDict[instName]["<" + instName + "_NODE_NETMASK>"] = str(ipInfo.netmask)
                    serviceInstDict[instName]["<" + instName + "_NODE_NETWORK>"] = str(ipInfo.network)
                    serviceInstDict[instName]["<" + instName + "_NODE_SUBNET>"] = str(ipInfo.network) + "/" + str(ipInfo.prefixlen)
                    serviceInstDict[instName]["<" + instName + "_NODE_CIADDR>"] = str(ipInfo.network) + "/" + str(ipInfo.prefixlen)
                    serviceInstDict[instName]["<" + instName + "_<NODE_BROADCAST>"] = str(ipInfo.broadcast)


    # Sort the list of ip-address id's
    sortedInstList.sort()
    return (serviceInstDict, sortedInstList)

def getVirtualImageIpInfo(clusterId):
    '''
    Class used to gather the Virtual Image Ip Information according to the deployment id
    '''
    # Create an empty dict to store all node information within a dict of dicts
    logger.info("Getting Virtual Image information for Deployment id " + str(clusterId))
    virtualImageDict={}
    sortedVirtualImageList = []
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "Issue getting deployment data, Exception : " + str(e)
        logger.error(message)
        return 1
    try:
        virtualImage = VirtualImage.objects.filter(cluster_id=clusterObj.id)
    except Exception as e:
        message = "Issue getting Virtual Image information, Exception : " + str(e)
        logger.error(message)
        return 1
    # Get info for the MgtServer dns IP address
    dns = clusterObj.management_server.server.dns_serverA

    clusterSvrs = ClusterServer.objects.filter(cluster_id=clusterId, active=True)
    # Append all node types together
    nodeSrvTypes = []
    for nodeSrv in clusterSvrs:
        if nodeSrv.node_type not in nodeSrvTypes:
            nodeSrvTypes.append(nodeSrv.node_type)

    virtualImageInfo = []

    if VirtualImage.objects.filter(cluster_id=clusterId):
        virtualImage = VirtualImage.objects.filter(cluster_id=clusterId, node_list__in=nodeSrvTypes)
        for virtualImageObj in virtualImage:
            vmIpPublicObj = None
            vmIpPublicIpv6Obj = None
            vmIpStorageObj = None
            vmIpInternalObj = None

            vmName = virtualImageObj.name
            virtualImageDict[vmName]={}
            sortedVirtualImageList.append(vmName)

            if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_public").exists():
                vmIpPublicObj = VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_public")
                if vmIpPublicObj != None:
                    for vm in vmIpPublicObj:
                        number = vm.number
                        virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_public_ip>"] = vm.ipMap.address
                        if vm.hostname != None:
                            virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_public_hostname>"] = vm.hostname
                            output = vm.hostname + "." + config.get('DMT_SERVER', 'domain')
                            if "httpd" in vmName or "haproxy" in vmName:
                                virtualImageDict[vmName]["<" + vmName + "_APACHE_FQDN>"] = output
                            else:
                                virtualImageDict[vmName]["<" + vmName + "_public_fqdn>"] = output
                            # changes atrcxbxxx.athtem.eei.ericsson.se to ericsson se
                            (secondlast, last) = output.split('.')[-2:]
                            virtualImageDict[vmName]["<" + vmName + "_COOKIE_DOMAIN>"] = "." +str(secondlast)+ "." +str(last)
            if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_ipv6Public").exists():
                vmIpPublicIpv6Obj = VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_ipv6Public")
                if vmIpPublicIpv6Obj != None:
                    for vm in vmIpPublicIpv6Obj:
                        number = vm.number
                        virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_public_ipv6_ip>"] = vm.ipMap.ipv6_address
                        if vm.hostname != None:
                            virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_public_ipv6_hostname>"] = vm.hostname

            if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_storage").exists():
                vmIpStorageObj = VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_storage")
                if vmIpStorageObj != None:
                    for vm in vmIpStorageObj:
                        number = vm.number
                        virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_storage_ip>"] = vm.ipMap.address
                        if vm.hostname != None:
                            virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_storage_hostname>"] = vm.hostname

            if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_internal").exists():
                vmIpInternalObj = VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_internal")
                if vmIpInternalObj != None:
                    for vm in vmIpInternalObj:
                        number = vm.number
                        virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_internal_ip>"] = vm.ipMap.address
                        if vm.hostname != None:
                            virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_internal_hostname>"] = vm.hostname

            if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_ipv6Internal").exists():
                vmIpInternalIpv6Obj = VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_ipv6Internal")
                if vmIpInternalIpv6Obj != None:
                    for vm in vmIpInternalIpv6Obj:
                        number = vm.number
                        virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_internal_ipv6_ip>"] = vm.ipMap.ipv6_address
                        if vm.hostname != None:
                            virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_internal_ipv6_hostname>"] = vm.hostname

            if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_jgroup").exists():
                vmIpInternalObj = VirtualImageInfoIp.objects.filter(virtual_image=virtualImageObj.id,ipMap__ipType__startswith="virtualImage_jgroup")
                if vmIpInternalObj != None:
                    for vm in vmIpInternalObj:
                        number = vm.number
                        virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_jgroup_ip>"] = vm.ipMap.address
                        if vm.hostname != None:
                            virtualImageDict[vmName]["<" + str(vmName) + "_" + str(number) + "_jgroup_hostname>"] = vm.hostname
    # Sort the list of ip-address id's
    sortedVirtualImageList.sort()
    return (virtualImageDict, sortedVirtualImageList)

def clusterToClusterMapping(clusterId):
    '''
    Class used to gatched the deployment to deployment information if exists
    '''
    clusterObj = Cluster.objects.get(id=clusterId)
    serverTypeList = []
    nodesdict={}
    if OssrcClusterToTorClusterMapping.objects.filter(torCluster=clusterObj.id).exists():
        clsMapObj = OssrcClusterToTorClusterMapping.objects.get(torCluster=clusterObj.id)
        clusterObj = Cluster.objects.get(id=clsMapObj.ossCluster.id)

        # Get info for Deployment Server(s) according to Deployment ID
        clusterSvrs = ClusterServer.objects.filter(cluster=clusterObj)
        # Append both object together
        nodesrv = []
        for x in clusterSvrs:
            nodesrv.append(x)
        # Get all Node IP, NIC etc information
        servers = []
        for cs in nodesrv:
            servers += Server.objects.filter(id=cs.server.id)
        nics = []
        for server in servers:
            nics += NetworkInterface.objects.filter(server=server.id)
        ipaddrs = []
        for nic in nics:
            ipaddrs += IpAddress.objects.filter(nic=nic.id)
        for server in nodesrv:
            serverType = str(server.node_type)
            serverType = re.sub(r' ', '_', serverType)
            nodesdict[serverType]={}
            serverTypeList.append(str(serverType))
            for nic in nics:
                if nic.server.hostname == server.server.hostname:
                    for ip in ipaddrs:
                        if ip.nic.mac_address == nic.mac_address:
                            if str(ip.ipType) == "other":
                                # Add node info according to info within the DB
                                nodesdict[serverType]["<" + serverType + '_NODE_DOMAIN>'] = server.server.domain_name
                                nodesdict[serverType]["<" + serverType + '_NODE_HOSTNAME>'] = server.server.hostname
                                nodesdict[serverType]["<" + serverType + '_NODE_MAC>'] = nic.mac_address
                                nodesdict[serverType]["<" + serverType + '_NODE_IP>'] = ip.address
                                nodesdict[serverType]["<" + serverType + '_NODE_GATEWAY>'] = ip.gateway_address
            # Check if the data is already defined in the ENMdeployment
            if SsoDetails.objects.filter(cluster=clusterId).exists():
                nodesdict["SSO"]={}
                ssoInfoObj = SsoDetails.objects.filter(cluster=clusterId)
                for item in ssoInfoObj:
                    nodesdict["SSO"]["<SSO_LDAP_DOMAIN>"] = item.ldapDomain
                    nodesdict["SSO"]["<SSO_LDAP_DOMAIN_FULL>"] = "dc=" +str(item.ldapDomain+ ",dc=com")
                    nodesdict["SSO"]["<SSO_LDAP_PASSWORD>"] = item.ldapPassword
                    nodesdict["SSO"]["<SECURITY_ADMIN_PASSWORD>"] = item.securityAdminPassword
                    nodesdict["SSO"]["<OPENIDM_MYSQL_PASSWORD>"] = item.openidmMysqlPassword
                    nodesdict["SSO"]["<OPENIDM_ADMIN_PASSWORD>"] = item.openidmAdminPassword
                    nodesdict["SSO"]["<OPENDJ_ADMIN_PASSWORD>"] = item.opendjAdminPassword
                    nodesdict["SSO"]["<HQ_DATABASE_PASSWORD>"] = item.hqDatabasePassword
                    nodesdict["SSO"]["<SSO_ADMIN_OSS_FS>"] = item.ossFsServer
                    nodesdict["SSO"]["<SSO_CITRIX_FARM>"] = item.citrixFarm
                    nodesdict["SSO"]["<SSO_BRSADM_PASSWORD>"] = item.brsadm_password
            elif SsoDetails.objects.filter(cluster=clusterObj).exists():
                    nodesdict["SSO"]={}
                    ssoInfoObj = SsoDetails.objects.filter(cluster=clusterObj)
                    for item in ssoInfoObj:
                        nodesdict["SSO"]["<SSO_LDAP_DOMAIN>"] = item.ldapDomain
                        nodesdict["SSO"]["<SSO_LDAP_DOMAIN_FULL>"] = "dc=" +str(item.ldapDomain+ ",dc=com")
                        nodesdict["SSO"]["<SSO_LDAP_PASSWORD>"] = item.ldapPassword
                        nodesdict["SSO"]["<SECURITY_ADMIN_PASSWORD>"] = item.securityAdminPassword
                        nodesdict["SSO"]["<OPENIDM_MYSQL_PASSWORD>"] = item.openidmMysqlPassword
                        nodesdict["SSO"]["<OPENIDM_ADMIN_PASSWORD>"] = item.openidmAdminPassword
                        nodesdict["SSO"]["<OPENDJ_ADMIN_PASSWORD>"] = item.opendjAdminPassword
                        nodesdict["SSO"]["<HQ_DATABASE_PASSWORD>"] = item.hqDatabasePassword
                        nodesdict["SSO"]["<SSO_ADMIN_OSS_FS>"] = item.ossFsServer
                        nodesdict["SSO"]["<SSO_CITRIX_FARM>"] = item.citrixFarm
                        nodesdict["SSO"]["<SSO_BRSADM_PASSWORD>"] = item.brsadm_password
    else:
        if SsoDetails.objects.filter(cluster=clusterObj).exists():
            nodesdict["SSO"]={}
            ssoInfoObj = SsoDetails.objects.filter(cluster=clusterObj)
            for item in ssoInfoObj:
                if item.ldapDomain:
                    nodesdict["SSO"]["<SSO_LDAP_DOMAIN>"] = item.ldapDomain
                    nodesdict["SSO"]["<SSO_LDAP_DOMAIN_FULL>"] = "dc=" +str(item.ldapDomain+ ",dc=com")
                if item.ldapPassword:
                    nodesdict["SSO"]["<SSO_LDAP_PASSWORD>"] = item.ldapPassword
                if item.securityAdminPassword:
                    nodesdict["SSO"]["<SECURITY_ADMIN_PASSWORD>"] = item.securityAdminPassword
                if item.openidmMysqlPassword:
                    nodesdict["SSO"]["<OPENIDM_MYSQL_PASSWORD>"] = item.openidmMysqlPassword
                if item.openidmAdminPassword:
                    nodesdict["SSO"]["<OPENIDM_ADMIN_PASSWORD>"] = item.openidmAdminPassword
                if item.opendjAdminPassword:
                    nodesdict["SSO"]["<OPENDJ_ADMIN_PASSWORD>"] = item.opendjAdminPassword
                if item.hqDatabasePassword:
                    nodesdict["SSO"]["<HQ_DATABASE_PASSWORD>"] = item.hqDatabasePassword
                if item.ossFsServer:
                    nodesdict["SSO"]["<SSO_ADMIN_OSS_FS>"] = item.ossFsServer
                if item.citrixFarm:
                    nodesdict["SSO"]["<SSO_CITRIX_FARM>"] = item.citrixFarm
                if item.brsadm_password:
                    nodesdict["SSO"]["<SSO_BRSADM_PASSWORD>"] = item.brsadm_password
    serverTypeList.sort()
    return (nodesdict, serverTypeList)

def getNASStorageDetailsOSS(clusterId):
    '''
    The getNASDetails function populates the config file with NAS details
    '''
    nasStorageClusterDict = {}
    sortedNASStorageClusterList = []

    poolFS1 = ""
    poolFS2 = ""
    poolFS3 = ""
    fileSystem1 = ""
    fileSystem2 = ""
    fileSystem3 = ""

    clusterObj = Cluster.objects.get(id=clusterId)
    try:
        if OssrcClusterToTorClusterMapping.objects.filter(torCluster=clusterObj.id).exists():
            clsMapObj = OssrcClusterToTorClusterMapping.objects.get(torCluster=clusterObj.id)
            ossclsId = clsMapObj.ossCluster_id
            if NasStorageDetails.objects.filter(cluster=ossclsId).exists():
                nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=ossclsId)
                sanPoolName = str(nasStorageDtlsObj.sanPoolName)
                sanPoolId = str(nasStorageDtlsObj.sanPoolId)
                poolFS1 =  str(nasStorageDtlsObj.poolFS1)
                fileSystem1 = str(nasStorageDtlsObj.fileSystem1)
                poolFS2 =  str(nasStorageDtlsObj.poolFS2)
                fileSystem2 = str(nasStorageDtlsObj.fileSystem2)
                poolFS3 =  str(nasStorageDtlsObj.poolFS3)
                fileSystem3 = str(nasStorageDtlsObj.fileSystem3)
        logger.info("NAS and Storage data retreived from OSS-RC DB")
    except Exception as e:
        logger.error("Problem retrieving NAS and Storage data from OSS-RC DB: " +str(e))
        return 1
    try:
        name = "nasStorageDetailsOSS"
        sortedNASStorageClusterList.append(name)
        nasStorageClusterDict[name]={}
        nasStorageClusterDict[name]["<NAS_SEGMENT_1_POOL>"] = poolFS1
        nasStorageClusterDict[name]["<NAS_SEGMENT_1_FS>"] = fileSystem1
        nasStorageClusterDict[name]["<NAS_DDC_POOL>"] = poolFS2
        nasStorageClusterDict[name]["<NAS_DDC_FS>"] = fileSystem2
        nasStorageClusterDict[name]["<NAS_SGWCG_1_POOL>"] = poolFS3
        nasStorageClusterDict[name]["<NAS_SGWCG_1_FS>"] = fileSystem3

        logger.info("Build up NAS OSS-RC data in config file")
        return nasStorageClusterDict
    except Exception as e:
        logger.error("Issue building up NAS OSS-RC part of config file: " +str(e))
        return 1

def getMultiNodeDetails(clusterId):
    '''
    Class used to the get the specific information for a multi Enclosure system
    '''
    logger.info("Getting Multi Enclosure Information for cluster id : " + str(clusterId))
    multiNodeDict={}
    multiNodeDict["vlan"]={}
    cluster = Cluster.objects.get(id=clusterId)
    if DeploymentDatabaseProvider.objects.filter(cluster=cluster).exists():
        deploymentDatabaseProviderObj = DeploymentDatabaseProvider.objects.only('dpsPersistenceProvider').values('dpsPersistenceProvider').get(cluster=cluster)
        multiNodeDict["vlan"]["<DPS_PERSISTENT_PROVIDER>"] = str(deploymentDatabaseProviderObj['dpsPersistenceProvider'])
    if VlanDetails.objects.filter(cluster=cluster.id).exists():
        vlanTagObj =  VlanDetails.objects.get(cluster=cluster.id)
        if vlanTagObj.hbAVlan:
            multiNodeDict["vlan"]["<HBA_VLAN_TAG>"] = str(vlanTagObj.hbAVlan)
        if vlanTagObj.hbBVlan:
            multiNodeDict["vlan"]["<HBB_VLAN_TAG>"] = str(vlanTagObj.hbBVlan)
        if vlanTagObj.litp_management:
            multiNodeDict["vlan"]["<LITP_MANAGEMENT>"] = str(vlanTagObj.litp_management)
        if vlanTagObj.services_subnet:
            multiNodeDict["vlan"]["<SERVICES_SUBNET>"] = str(vlanTagObj.services_subnet)
        if vlanTagObj.services_gateway:
            multiNodeDict["vlan"]["<SERVICES_GATEWAY>"] = str(vlanTagObj.services_gateway)
        if vlanTagObj.services_ipv6_gateway:
            multiNodeDict["vlan"]["<SERVICE_IPV6_GATEWAY>"] = str(vlanTagObj.services_ipv6_gateway)
        if vlanTagObj.services_ipv6_subnet:
            multiNodeDict["vlan"]["<SERVICES_IPV6_SUBNET>"] = str(vlanTagObj.services_ipv6_subnet)
        if vlanTagObj.storage_subnet:
            multiNodeDict["vlan"]["<STORAGE_SUBNET>"] = str(vlanTagObj.storage_subnet)
        if vlanTagObj.storage_gateway:
            multiNodeDict["vlan"]["<STORAGE_GATEWAY>"] = str(vlanTagObj.storage_gateway)
        if vlanTagObj.backup_subnet:
            multiNodeDict["vlan"]["<BACKUP_SUBNET>"] = str(vlanTagObj.backup_subnet)
        if vlanTagObj.jgroups_subnet:
            multiNodeDict["vlan"]["<JGROUPS_SUBNET>"] = str(vlanTagObj.jgroups_subnet)
        if vlanTagObj.internal_subnet:
            multiNodeDict["vlan"]["<INTERNAL_SUBNET>"] = str(vlanTagObj.internal_subnet)
        if vlanTagObj.internal_ipv6_subnet:
            multiNodeDict["vlan"]["<INTERNAL_SUBNET_IPV6>"] = str(vlanTagObj.internal_ipv6_subnet)
        if vlanTagObj.storage_vlan:
            multiNodeDict["vlan"]["<STORAGE_VLAN>"] = str(vlanTagObj.storage_vlan)
        if vlanTagObj.backup_vlan:
            multiNodeDict["vlan"]["<BACKUP_VLAN>"] = str(vlanTagObj.backup_vlan)
        if vlanTagObj.jgroups_vlan:
            multiNodeDict["vlan"]["<JGROUPS_VLAN>"] = str(vlanTagObj.jgroups_vlan)
        if vlanTagObj.internal_vlan:
            multiNodeDict["vlan"]["<INTERNAL_VLAN>"] = str(vlanTagObj.internal_vlan)
        if vlanTagObj.services_vlan:
            multiNodeDict["vlan"]["<SERVICES_VLAN>"] = str(vlanTagObj.services_vlan)
        if vlanTagObj.management_vlan:
            multiNodeDict["vlan"]["<MANAGEMENT_VLAN_ID>"] = str(vlanTagObj.management_vlan)
        if VirtualConnectNetworks.objects.filter(vlanDetails_id=vlanTagObj.id).exists():
                virtualConnectObj = VirtualConnectNetworks.objects.get(vlanDetails_id=vlanTagObj.id)
                multiNodeDict["vlan"]["<SHARED_UP_LINK_SET_A>"] = str(virtualConnectObj.sharedUplinkSetA)
                multiNodeDict["vlan"]["<SHARED_UP_LINK_SET_B>"] = str(virtualConnectObj.sharedUplinkSetB)
                multiNodeDict["vlan"]["<SERVICES_A>"] = str(virtualConnectObj.servicesA)
                multiNodeDict["vlan"]["<SERVICES_B>"] = str(virtualConnectObj.servicesB)
                multiNodeDict["vlan"]["<STORAGE_A>"] = str(virtualConnectObj.storageA)
                multiNodeDict["vlan"]["<STORAGE_B>"] = str(virtualConnectObj.storageB)
                multiNodeDict["vlan"]["<BACKUP_A>"] = str(virtualConnectObj.backupA)
                multiNodeDict["vlan"]["<BACKUP_B>"] = str(virtualConnectObj.backupB)
                multiNodeDict["vlan"]["<JGROUPS>"] = str(virtualConnectObj.jgroups)
                multiNodeDict["vlan"]["<JGROUPS_A>"] = str(virtualConnectObj.jgroupsA)
                multiNodeDict["vlan"]["<JGROUPS_B>"] = str(virtualConnectObj.jgroupsB)
                multiNodeDict["vlan"]["<INTERNAL_A>"] = str(virtualConnectObj.internalA)
                multiNodeDict["vlan"]["<INTERNAL_B>"] = str(virtualConnectObj.internalB)
                multiNodeDict["vlan"]["<HEARTBEAT1>"] = str(virtualConnectObj.heartbeat1)
                multiNodeDict["vlan"]["<HEARTBEAT2>"] = str(virtualConnectObj.heartbeat2)
                multiNodeDict["vlan"]["<HEARTBEAT1_A>"] = str(virtualConnectObj.heartbeat1A)
                multiNodeDict["vlan"]["<HEARTBEAT2_B>"] = str(virtualConnectObj.heartbeat2B)
    return multiNodeDict

def getEnclosureInfo(clusterId):
    '''
    Class used to Gather all the enclosure info according to the deploymentId given
    '''
    # Create an empty dict to store all enclosure information within a dict of dicts
    logger.info("Getting enclosure info for Deployment id " + str(clusterId))
    enclosuredict={}
    enclosuredict["enclosure"]={}
    cluster = Cluster.objects.get(id=clusterId)
    # Get info for MgtServer according to deployment
    mgtServer = cluster.management_server
    # Get info for Deployment Server(s) according to Deployment ID
    clusterSvrs = ClusterServer.objects.filter(cluster=cluster)
    # Append both object together
    nodesrv = []
    for x in clusterSvrs:
        nodesrv.append(x)
    nodesrv.append(mgtServer)
    # Get all Node IP, NIC etc information
    servers = []
    for cs in nodesrv:
        servers += Server.objects.filter(id=cs.server.id)
    nics = []
    for server in servers:
        nics += NetworkInterface.objects.filter(server=server.id)
    ipaddrs = []
    for nic in nics:
        ipaddrs += IpAddress.objects.filter(nic=nic.id)
    incno = 1
    for server in nodesrv:
        for nic in nics:
            if nic.server.hostname == server.server.hostname:
                for ip in ipaddrs:
                    if ip.nic.mac_address == nic.mac_address:
                        # Gather Extra Blade Information
                        if BladeHardwareDetails.objects.filter(mac_address=nic.id):
                            extraHWDetailsObj = BladeHardwareDetails.objects.get(mac_address=nic.id)
                            vlanTag = extraHWDetailsObj.vlan_tag
                            if Enclosure.objects.filter(id=extraHWDetailsObj.enclosure_id).exists():
                                enclosureObj = Enclosure.objects.get(id=extraHWDetailsObj.enclosure_id)
                                enclosureIpList = EnclosureIPMapping.objects.filter(enclosure=enclosureObj)
                                for enclosureIP in enclosureIpList:
                                    exist = "NO"
                                    if enclosureIP.ipnumber == 1:
                                        increment = "NO"
                                        enclosure_IP1 = enclosureIP.ipaddr
                                        # Check to see does the the IP in the DB the same as the last iteration
                                        # If yes then set the Enclousre to 1 else increment and increment by 1
                                        for nodeKey, nodeValue in enclosuredict.items():
                                            if exist != "YES":
                                                for key, value in nodeValue.items():
                                                    if str(enclosure_IP1) == value:
                                                        exist = "YES"
                                                        break
                                            else:
                                                break
                                        if exist != "YES":
                                            # Needed for old RV deployment script
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_IP1>"] = str(enclosure_IP1)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_USERNAME>"] = enclosureObj.credentials.username
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_PASSWORD>"] = enclosureObj.credentials.password
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_UPLINK_A_PORT_1>"] = str(enclosureObj.uplink_A_port1)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_UPLINK_A_PORT_2>"] = str(enclosureObj.uplink_A_port2)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_UPLINK_B_PORT_1>"] = str(enclosureObj.uplink_B_port1)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_UPLINK_B_PORT_2>"] = str(enclosureObj.uplink_B_port2)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_RACK_NAME>"] = str(enclosureObj.rackName)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_ENCLOSURE_NAME>"] = str(enclosureObj.name)
                                            if enclosureObj.vc_module_bay_1 != None:
                                                enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VC_BAY_LOCATION1>"] = str(enclosureObj.vc_module_bay_1)
                                            if enclosureObj.vc_module_bay_2 != None:
                                                enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VC_BAY_LOCATION2>"] = str(enclosureObj.vc_module_bay_2)
                                            if enclosureObj.san_sw_bay_1 != None:
                                                enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_SANSW_BAY_LOCATION1>"] = str(enclosureObj.san_sw_bay_1)
                                            if enclosureObj.san_sw_bay_2 != None:
                                                enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_SANSW_BAY_LOCATION2>"] = str(enclosureObj.san_sw_bay_2)
                                            #enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VLAN_TAG>"] = str(vlanTag)
                                            increment = "YES"
                                    elif enclosureIP.ipnumber == 2:
                                        enclosure_IP2 = enclosureIP.ipaddr
                                        # Check to see does the the IP in the DB the same as the last iteration
                                        # If yes then set the Enclousre to 1 else increment and increment by 1
                                        existIP2 = "NO"
                                        for nodeKey, nodeValue in enclosuredict.items():
                                            if existIP2 != "YES":
                                                for key, value in nodeValue.items():
                                                    if str(enclosure_IP2) == value:
                                                        existIP2 = "YES"
                                            else:
                                                break
                                        if existIP2 != "YES":
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_IP2>"] = str(enclosure_IP2)
                                    elif enclosureIP.ipnumber == 3:
                                        enclosure_IP3 = enclosureIP.ipaddr
                                        existIP3 = "NO"
                                        for nodeKey, nodeValue in enclosuredict.items():
                                            if existIP3 != "YES":
                                                for key, value in nodeValue.items():
                                                    if str(enclosure_IP3) == value:
                                                        existIP3 = "YES"
                                            else:
                                                break
                                        if existIP3 != "YES":
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VC_IP1>"] = str(enclosure_IP3)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VC_USERNAME>"] = enclosureObj.vc_credentials.username
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VC_PASSWORD>"] = enclosureObj.vc_credentials.password
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VC_DOMAIN>"] = enclosureObj.vc_domain_name

                                    elif enclosureIP.ipnumber == 4:
                                        enclosure_IP4 = enclosureIP.ipaddr
                                        existIP4 = "NO"
                                        for nodeKey, nodeValue in enclosuredict.items():
                                            if existIP4 != "YES":
                                                for key, value in nodeValue.items():
                                                    if str(enclosure_IP4) == value:
                                                        existIP4 = "YES"
                                            else:
                                                break
                                        if existIP4 != "YES":
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_VC_IP2>"] = str(enclosure_IP4)
                                    elif enclosureIP.ipnumber == 5:
                                        enclosure_IP5 = enclosureIP.ipaddr
                                        existIP5 = "NO"
                                        for nodeKey, nodeValue in enclosuredict.items():
                                            if existIP5 != "YES":
                                                for key, value in nodeValue.items():
                                                    if str(enclosure_IP5) == value:
                                                        existIP5 = "YES"
                                            else:
                                                break
                                        if existIP5 != "YES":
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_SANSW_IP1>"] = str(enclosure_IP5)
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_SANSW_USERNAME>"] = enclosureObj.sanSw_credentials.username
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_SANSW_PASSWORD>"] = enclosureObj.sanSw_credentials.password
                                    elif enclosureIP.ipnumber == 6:
                                        enclosure_IP6 = enclosureIP.ipaddr
                                        existIP6 = "NO"
                                        for nodeKey, nodeValue in enclosuredict.items():
                                            if existIP6 != "YES":
                                                for key, value in nodeValue.items():
                                                    if str(enclosure_IP6) == value:
                                                        existIP6 = "YES"
                                            else:
                                                break
                                        if existIP6 != "YES":
                                            enclosuredict["enclosure"]["<ENCLOSURE"+str(incno)+"_SANSW_IP2>"] = str(enclosure_IP6)
                                # Increment because there was something different found
                                if increment == "YES":
                                    incno += 1
    return (enclosuredict, "enclosure")

def getNodeInfo(clusterId, installType):
    '''
    Class used to Gather all the info within the DB for either a deployment nodes or a MGT node
    parameters taken in is the deploymentid
    '''
    # Set default variables for Extra Blade info as system mat be virtual
    bladeSerial = ""
    bladeProfile = ""
    vlanTag = ""
    virtualMgtObj = None

    # Create an empty dict to store all node information within a dict of dicts
    logger.info("Getting node information for Deployment id " + str(clusterId))
    nodesdict={}
    cluster = Cluster.objects.get(id=clusterId)
    # Get info for MgtServer according to deployment
    mgtServer = cluster.management_server
    if VirtualManagementServer.objects.filter(mgtServer_id=mgtServer).exists():
        virtualMgtObj = VirtualManagementServer.objects.filter(mgtServer_id=mgtServer)
    # Get info for Deployment Server(s) according to Deployment ID
    clusterSvrs = ClusterServer.objects.filter(cluster=cluster, active=True)
    # Append all Server objects together
    nodesrv = []
    for x in clusterSvrs:
        nodesrv.append(x)
    nodesrv.append(mgtServer)

    if virtualMgtObj != None:
        for server in virtualMgtObj:
            nodesrv.append(server)

    # Get all Node IP, NIC etc information
    servers = []
    for cs in nodesrv:
        servers += Server.objects.filter(id=cs.server.id)
    nics = []
    allNics = []
    ilos = []
    hardwareIdentity = []
    for server in servers:
        allNics += NetworkInterface.objects.filter(server=server.id)
        nics += NetworkInterface.objects.filter(server=server.id,interface="eth0")
        ilos += Ilo.objects.filter(server=server.id)
        if HardwareIdentity.objects.filter(server=server.id).exists():
            hardwareIdentity += HardwareIdentity.objects.filter(server=server.id)
    ipaddrs = []
    for nic in nics:
        if IpAddress.objects.filter(nic=nic.id).exists():
            ipaddrs += IpAddress.objects.filter(nic=nic.id)

    try:
        veritas = VeritasCluster.objects.get(cluster=clusterId)
    except Exception as e:
        veritas = None
    if DataBaseLocation.objects.filter(cluster=clusterId).exists():
        databaseLocationObj = DataBaseLocation.objects.get(cluster=clusterId)
        versantStandAlone = databaseLocationObj.versantStandAlone
        mysqlStandAlone = databaseLocationObj.mysqlStandAlone
        postgresStandAlone = databaseLocationObj.postgresStandAlone
    else:
        versantStandAlone = "NO"
        mysqlStandAlone = "NO"
        postgresStandAlone = "NO"
    foundNtp = ""
    hardwareType = ""
    tipcNo = 0
    numberOfNodes = 0
    serverTypeList = []
    for server in nodesrv:
        # Check to see are we on the mgt Server info as mgt doesn't have node_type
        if isinstance(server, ClusterServer):
            serverType = str(server.node_type)
            noChgServerType = serverType
            if not serverType == 'NETSIM':
                numberOfNodes += 1
        elif isinstance(server, ManagementServer):
            serverType = "MS"
            noChgServerType = "ms1"
        serverTypeList.append(str(serverType))
        nodesdict[serverType]={}
        if cluster.compact_audit_logger is not None:
            nodesdict[serverType]["<compact_audit_logger>"] = str(cluster.compact_audit_logger).lower()
        for nic in nics:
            if nic.server.hostname == server.server.hostname:
                for ip in ipaddrs:
                    if ip.nic.mac_address == nic.mac_address:
                        # Remove foreign character from the hostname i.e. [^\w] will match anything that's not alphanumeric or underscore
                        serverTypeAmend = re.sub(r'[^\w]', '', noChgServerType)
                        lwrServerTypeAmend = serverTypeAmend.lower()
                        lwrnoChgServerType = noChgServerType.lower()
                        uprnoChgServerType = noChgServerType.upper()
                        nodeNumber = serverTypeAmend[-1:]
                        # Create System Name id and append Tipc info for SC's and PL's
                        if "MS" in serverType:
                            # For EDP Deployment Parameters
                            nodesdict[serverType]["<DEPLOYMENT_ID>"] = str(cluster.name)
                            if cluster.enmDeploymentType:
                                nodesdict[serverType]["<ENM_DEPLOYMENT_TYPE>"] = str(cluster.enmDeploymentType.name)
                            if cluster.ipVersion:
                                nodesdict[serverType]["<IP_VERSION>"] = str(cluster.ipVersion.name)
                            # Rest of MS Data
                            nodeSystemName = "NULL"
                            nodesdict[serverType]["<" + serverType + "_VERSANT_STANDALONE>"] =  str(versantStandAlone)
                            nodesdict[serverType]["<" + serverType + "_MYSQL_STANDALONE>"] =  str(mysqlStandAlone)
                            nodesdict[serverType]["<" + serverType + "_POSTGRES_STANDALONE>"] =  str(postgresStandAlone)
                            if veritas != None:
                                mask_length = int(veritas.ipMapCSG.bitmask)
                                mask = (1<<32) - (1<<32>>mask_length)
                                csgNetmask = socket.inet_ntoa(struct.pack(">L", mask))
                                mask_length = int(veritas.ipMapGCO.bitmask)
                                mask = (1<<32) - (1<<32>>mask_length)
                                gcoNetmask = socket.inet_ntoa(struct.pack(">L", mask))
                                nodesdict[serverType]["<" + serverType + "_VCS_NETID>"] =  str(cluster.tipc_address)
                                nodesdict[serverType]["<" + serverType + "_CSG_IP>"] =  str(veritas.ipMapCSG.address)
                                nodesdict[serverType]["<" + serverType + "_CSG_NIC>"] =  str(veritas.csgNic)
                                nodesdict[serverType]["<" + serverType + "_CSG_NETMASK>"] =  str(csgNetmask)
                                nodesdict[serverType]["<" + serverType + "_GCO_IP>"] =  str(veritas.ipMapGCO.address)
                                nodesdict[serverType]["<" + serverType + "_GCO_NIC>"] =  str(veritas.gcoNic)
                                nodesdict[serverType]["<" + serverType + "_GCO_NETMASK>"] =  str(gcoNetmask)
                                nodesdict[serverType]["<" + serverType + "_LLT_LOW_PRI>"] =  str(veritas.lltLinkLowPri1)
                                nodesdict[serverType]["<" + serverType + "_LLT_LINK1>"] =  str(veritas.lltLink1)
                                nodesdict[serverType]["<" + serverType + "_LLT_LINK2>"] =  str(veritas.lltLink2)
                            if str(ip.ipType) == "host":
                                # External IPv4 information for the MS
                                nodesdict[serverType]["<" + serverType + '_EXTERNAL_NODE_IP>'] = ip.address
                            if str(ip.ipType) == "ipv6_host":
                                # External IPv6 information for the MS
                                nodesdict[serverType]["<" + serverType + '_EXTERNAL_IPV6_NODE_IP>'] = ip.ipv6_address
                        if not serverType == 'NETSIM':
                            if hardwareType == "":
                                hardwareType = nic.server.hardware_type
                            elif hardwareType != nic.server.hardware_type:
                                hardwareType = "mixed"
                        # Add node info according to info within the DB
                        number = cluster.tipc_address
                        nodesdict[serverType]["<" + serverType + "_NODE_NETID>"] = str(cluster.tipc_address)
                        nodesdict[serverType]["<" + serverType + "_SCRIPTINGCLUSTERID>"] = int(number) + 10000
                        nodesdict[serverType]["<" + serverType + "_DBCLUSTERID>"] = int(number) + 20000
                        nodesdict[serverType]["<" + serverType + "_SERVICESCLUSTERID>"] = int(number) + 30000
                        nodesdict[serverType]["<" + serverType + "_EVENTCLUSTERID>"] = int(number) + 40000
                        nodesdict[serverType]["<" + serverType + "_STREAMINGCLUSTERID>"] = int(number) + 50000
                        nodesdict[serverType]["<" + serverType + "_AUTOMATIONCLUSTERID>"] = int(number) + 60000
                        nodesdict[serverType]["<" + serverType + "_ESNCLUSTERID>"] = int(number) + 15000
                        nodesdict[serverType]["<" + serverType + "_ASRCLUSTERID>"] = int(number) + 25000
                        nodesdict[serverType]["<" + serverType + "_EBSCLUSTERID>"] = int(number) + 35000
                        nodesdict[serverType]["<" + serverType + "_EBACLUSTERID>"] = int(number) + 45000
                        nodesdict[serverType]["<" + serverType + '_NODE_HOSTNAME>'] = server.server.hostname
                        nodesdict[serverType]["<" + serverType + '_NODE_DOMAIN>'] = server.server.domain_name
                        nodesdict[serverType]["<" + serverType + '_NODE_HOSTNAME_LWR>'] = lwrnoChgServerType
                        nodesdict[serverType]["<" + serverType + '_NODE_NTP_IPADDRESS>'] = server.server.dns_serverA
                        nodesdict[serverType]["<" + serverType + '_NODE_INF>'] = server.server.hardware_type
                        # DNS Servers
                        nodesdict[serverType]["<" + serverType + '_NTP_IPADDRESS>'] = server.server.dns_serverA
                        nodesdict[serverType]["<" + serverType + '_NTP1_IPADDRESS>'] = server.server.dns_serverB
                        nodesdict[serverType]["<" + serverType + '_NODE_MAC>'] = nic.mac_address
                        nodesdict[serverType]["<" + serverType + '_NODE_HARDWARE_TYPE>'] = server.server.hardware_type

                        if NetworkInterface.objects.filter(server=server.server.id).exists():
                            extraNetworkObject = NetworkInterface.objects.filter(server=server.server.id)
                            for item in extraNetworkObject:
                                nodesdict[serverType]["<" + serverType + '_NODE_MAC_'+item.interface.upper()+'>'] = item.mac_address
                        if HardwareIdentity.objects.filter(server=server.server.id).exists():
                            hardwareIdentityObj = HardwareIdentity.objects.filter(server=server.server.id)
                            for item in hardwareIdentityObj:
                                if item.ref == '1':
                                    nodesdict[serverType]["<" + serverType + '_NODE_WWPN1>'] = item.wwpn
                                if item.ref == '2':
                                    nodesdict[serverType]["<" + serverType + '_NODE_WWPN2>'] = item.wwpn
                        if HardwareDetails.objects.filter(server=server.server.id).exists():
                            details = HardwareDetails.objects.get(server=server.server.id)
                            nodesdict[serverType]["<" + serverType + '_NODE_RAM>'] = details.ram
                            nodesdict[serverType]["<" + serverType + '_NODE_DISK_SIZE>'] = details.diskSize

                        if str(ip.ipType) == "storage":
                            nodesdict[serverType]["<" + serverType + '_STORAGE_NODE_IP>'] = ip.address
                        if str(ip.ipType) == "backup":
                            nodesdict[serverType]["<" + serverType + '_BACKUP_NODE_IP>'] = ip.address
                        if str(ip.ipType) == "multicast":
                            nodesdict[serverType]["<" + serverType + '_MULTICAST_NODE_IP>'] = ip.address
                        if str(ip.ipType) == "jgroup":
                            nodesdict[serverType]["<" + serverType + '_JGROUP_NODE_IP>'] = ip.address
                        if str(ip.ipType) == "internal":
                            nodesdict[serverType]["<" + serverType + '_INTERNAL_NODE_IP>'] = ip.address
                        if str(ip.ipType) == "other":
                            if ip.ipv6_address != None:
                                nodesdict[serverType]["<" + serverType + '_IPV6_NODE_IP>'] = ip.ipv6_address
                            nodesdict[serverType]["<" + serverType + '_NODE_IP>'] = ip.address
                            if 'cloud' in hardwareType:
                                iloUsername = config.get('DMT_AUTODEPLOY', 'iloUsername')
                                iloPassword = config.get('DMT_AUTODEPLOY', 'iloPassword')
                                nodesdict[serverType]["<" + serverType + "_ILOIP>"] = ip.address
                                nodesdict[serverType]["<" + serverType + "_ILOUSERNAME>"] = str(iloUsername)
                                nodesdict[serverType]["<" + serverType + "_ILOPASSWORD>"] = str(iloPassword)

                        # Gather Extra Blade Information
                        if BladeHardwareDetails.objects.filter(mac_address=nic.id).exists():
                            extraHWDetailsObj = BladeHardwareDetails.objects.get(mac_address=nic.id)
                            bladeSerial = extraHWDetailsObj.serial_number
                            bladeProfile = extraHWDetailsObj.profile_name
                            nodesdict[serverType]["<" + serverType + "_SERIAL_NUMBER>"] = str(bladeSerial)
                            nodesdict[serverType]["<" + serverType + "_PROFILE_TAG>"] = str(bladeProfile)
                            if Enclosure.objects.filter(id=extraHWDetailsObj.enclosure_id).exists():
                                enclosureObj = Enclosure.objects.get(id=extraHWDetailsObj.enclosure_id)
                                # Only allow alphanumeric characters for the enclosure Hostname as it is used for the storage identification variable
                                enclosureIpList = EnclosureIPMapping.objects.filter(enclosure=enclosureObj)
                                nodesdict[serverType]["<" + serverType + "_ENCLOSURE_HOSTNAME>"] = re.sub(r'\W+', '', enclosureObj.hostname)
                                nodesdict[serverType]["<" + serverType + "_ENCLOSURE_USERNAME>"] = enclosureObj.credentials.username
                                nodesdict[serverType]["<" + serverType + "_ENCLOSURE_PASSWORD>"] = enclosureObj.credentials.password

                                for enclosureIP in enclosureIpList:
                                    if enclosureIP.ipnumber == 1:
                                        enclosure_IP1 = enclosureIP.ipaddr
                                        # Need to set the initial value to check
                                        # Needed for old RV deployment script
                                        nodesdict[serverType]["<" + serverType + "_ENCLOSURE_IP1>"] = str(enclosure_IP1)
                                    else:
                                        enclosure_IP2 = enclosureIP.ipaddr
                                        nodesdict[serverType]["<" + serverType + "_ENCLOSURE_IP2>"] = str(enclosure_IP2)
                        if RackHardwareDetails.objects.filter(clusterServer=server).exists():
                            extraHWDetailsObj = RackHardwareDetails.objects.get(clusterServer=server)
                            nodesdict[serverType]["<" + serverType + '_NODE_BOOTDISK_UUID>'] = str(extraHWDetailsObj.bootdisk_uuid)
                            nodesdict[serverType]["<" + serverType + "_SERIAL_NUMBER>"] = str(extraHWDetailsObj.serial_number)
                        for i in ilos:
                            if i.server.hostname == server.server.hostname:
                                iloIp = re.sub(r'.*//([0-9.]+).*', r'\1', i.ipMapIloAddress.address)
                                nodesdict[serverType]["<" + serverType + "_ILOIP>"] = iloIp
                                nodesdict[serverType]["<" + serverType + "_ILOUSERNAME>"] = i.username
                                nodesdict[serverType]["<" + serverType + "_ILOPASSWORD>"] = i.password
                        if VlanMulticast.objects.filter(clusterServer=server).exists():
                            fields = ("multicast_type__name", "multicast_snooping", "multicast_querier", "multicast_router", "hash_max",)
                            vlanMulticasts = VlanMulticast.objects.only(fields).values(*fields).filter(clusterServer=server)
                            for vlanMulticast in vlanMulticasts:
                                nodesdict[serverType]["<" + serverType + "_NODE_" + vlanMulticast["multicast_type__name"] + "_MULTICAST_SNOOPING>"] = vlanMulticast["multicast_snooping"]
                                nodesdict[serverType]["<" + serverType + "_NODE_" + vlanMulticast["multicast_type__name"] + "_MULTICAST_QUERIER>"] = vlanMulticast["multicast_querier"]
                                nodesdict[serverType]["<" + serverType + "_NODE_" + vlanMulticast["multicast_type__name"] + "_MULTICAST_ROUTER>"] = vlanMulticast["multicast_router"]
                                nodesdict[serverType]["<" + serverType + "_NODE_" + vlanMulticast["multicast_type__name"] + "_HASH_MAX>"] = vlanMulticast["hash_max"]
    nodesdict['MS']["<MS_HARDWARE_TYPE>"] = hardwareType
    nodesdict['MS']["<NUMBER_OF_NODES>"] = numberOfNodes
    if 'cloud' in hardwareType:
        if 'PL-3' in nodesdict:
            nodesdict["PL-3"]["<DEPLOYMENT_TYPE>"] = "CloudEnm4Node"
        elif 'VCS-1' in nodesdict:
            nodesdict["VCS-1"]["<DEPLOYMENT_TYPE>"] = "CloudEnm4Node"
        elif 'SC-1' in nodesdict:
            nodesdict["SC-1"]["<DEPLOYMENT_TYPE>"] = "CloudEnm"
    else:
        if 'PL-3' in nodesdict or 'VCS' in nodesdict:
            nodesdict["PL-3"]["<DEPLOYMENT_TYPE>"] = "Enm4Node"
        elif 'VCS-1' in nodesdict:
            nodesdict["VCS-1"]["<DEPLOYMENT_TYPE>"] = "Enm4Node"
        elif 'SC-1' in nodesdict:
            nodesdict["SC-1"]["<DEPLOYMENT_TYPE>"] = "TOR"

    # Sort the list so we can use this to append information to the install directory in the correct order
    serverTypeList.sort()
    return (nodesdict, serverTypeList)

def getLVSRouterVipInfo(clusterId):
    '''
    This function is used to get the LVS Router VIP information for a given clusterID
    '''
    lvsRouterVipDict = {}
    try:
        fields = ("pm_internal__address", "pm_external__address",
                    "fm_internal__address", "fm_external__address", "fm_internal_ipv6__ipv6_address", "fm_external_ipv6__ipv6_address",
                    "cm_internal__address", "cm_external__address", "cm_internal_ipv6__ipv6_address", "cm_external_ipv6__ipv6_address",
                    "svc_pm_storage__address", "svc_fm_storage__address", "svc_cm_storage__address",
                    "svc_storage_internal__address", "svc_storage__address",
                    "scp_scp_internal__address", "scp_scp_external__address", "scp_scp_internal_ipv6__ipv6_address", "scp_scp_external_ipv6__ipv6_address",
                    "scp_scp_storage__address", "scp_storage_internal__address", "scp_storage__address",
                    "evt_storage_internal__address", "evt_storage__address",
                    "str_str_if", "str_internal__address", "str_str_internal_2__address", "str_str_internal_3__address",
                    "str_external__address", "str_str_external_2__address", "str_str_external_3__address",
                    "str_str_internal_ipv6__ipv6_address", "str_str_internal_ipv6_2__ipv6_address", "str_str_internal_ipv6_3__ipv6_address",
                    "str_external_ipv6__ipv6_address", "str_str_external_ipv6_2__ipv6_address", "str_str_external_ipv6_3__ipv6_address",
                    "str_str_storage__address", "str_storage_internal__address", "str_storage__address",
                    "esn_str_if", "esn_str_internal__address", "esn_str_external__address", "esn_str_internal_ipv6__ipv6_address",
                    "esn_str_external_ipv6__ipv6_address", "esn_str_storage__address", "esn_storage_internal__address",
                    "ebs_storage_internal__address", "ebs_storage__address", "ebs_str_external_ipv6__ipv6_address", "asr_storage_internal__address", "asr_asr_external__address",
                    "asr_asr_internal__address", "asr_asr_external_ipv6__ipv6_address", "asr_storage__address","asr_asr_storage__address",
                    "eba_storage_internal__address", "eba_storage__address",
                    "msossfm_external__address", "msossfm_external_ipv6__ipv6_address", "msossfm_internal__address", "msossfm_internal_ipv6__ipv6_address")
        LVSRouterVipObj = LVSRouterVip.objects.only(fields).values(*fields).get(cluster_id=clusterId)
        if LVSRouterVipExtended.objects.filter(cluster_id=clusterId).exists():
            requiredLvsrouterVipExtendedFields = (
            "eba_external__address", "eba_external_ipv6__ipv6_address", "eba_internal__address",
            "eba_internal_ipv6__ipv6_address", "svc_pm_ipv6__ipv6_address", "oran_internal__address", "oran_internal_ipv6__ipv6_address", "oran_external__address", "oran_external_ipv6__ipv6_address")
            lvsRouterVipExtended = LVSRouterVipExtended.objects.only(requiredLvsrouterVipExtendedFields).values(*requiredLvsrouterVipExtendedFields).get(cluster_id=clusterId)
            LVSRouterVipObj.update(lvsRouterVipExtended)
        else:
            LVSRouterVipObj['eba_external__address'] = None
            LVSRouterVipObj['eba_external_ipv6__ipv6_address'] = None
            LVSRouterVipObj['eba_internal__address'] = None
            LVSRouterVipObj['eba_internal_ipv6__ipv6_address'] = None
            LVSRouterVipObj['svc_pm_ipv6__ipv6_address'] = None
            LVSRouterVipObj['oran_internal__address'] = None
            LVSRouterVipObj['oran_external__address'] = None
            LVSRouterVipObj['oran_internal_ipv6__ipv6_address'] = None
            LVSRouterVipObj['oran_external_ipv6__ipv6_address'] = None
        name = "LVSROUTER_VIP"
        lvsRouterVipDict[name]={}
        lvsRouterVipDict[name]["<SVC_PM_VIP_INTERNAL_IPV4>"] = LVSRouterVipObj["pm_internal__address"]
        lvsRouterVipDict[name]["<SVC_PM_VIP_PUBLIC_IPV4>"] = LVSRouterVipObj["pm_external__address"]
        lvsRouterVipDict[name]["<SVC_PM_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["svc_pm_storage__address"] == None else LVSRouterVipObj["svc_pm_storage__address"]

        lvsRouterVipDict[name]["<SVC_FM_VIP_INTERNAL_IPV4>"] = LVSRouterVipObj["fm_internal__address"]
        lvsRouterVipDict[name]["<SVC_FM_VIP_PUBLIC_IPV4>"] = LVSRouterVipObj["fm_external__address"]

        lvsRouterVipDict[name]["<SVC_PM_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["svc_pm_ipv6__ipv6_address"] == None else LVSRouterVipObj["svc_pm_ipv6__ipv6_address"]

        lvsRouterVipDict[name]["<SVC_FM_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["fm_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["fm_internal_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SVC_FM_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["fm_external_ipv6__ipv6_address"] == None else  LVSRouterVipObj["fm_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SVC_FM_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["svc_fm_storage__address"] == None else LVSRouterVipObj["svc_fm_storage__address"]

        lvsRouterVipDict[name]["<SVC_CM_VIP_INTERNAL_IPV4>"] = LVSRouterVipObj["cm_internal__address"]
        lvsRouterVipDict[name]["<SVC_CM_VIP_PUBLIC_IPV4>"] = LVSRouterVipObj["cm_external__address"]
        lvsRouterVipDict[name]["<SVC_CM_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["cm_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["cm_internal_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SVC_CM_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["cm_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["cm_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SVC_CM_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["svc_cm_storage__address"] == None else LVSRouterVipObj["svc_cm_storage__address"]

        lvsRouterVipDict[name]["<SVC_STORAGE_GATEWAY_INTERNAL_IPV4>"] = LVSRouterVipObj["svc_storage_internal__address"]
        lvsRouterVipDict[name]["<SVC_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["svc_storage__address"] == None else LVSRouterVipObj["svc_storage__address"]

        lvsRouterVipDict[name]["<SCP_SCP_VIP_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["scp_scp_internal__address"] == None else LVSRouterVipObj["scp_scp_internal__address"]
        lvsRouterVipDict[name]["<SCP_SCP_VIP_PUBLIC_IPV4>"] = "" if LVSRouterVipObj["scp_scp_external__address"] == None else LVSRouterVipObj["scp_scp_external__address"]
        lvsRouterVipDict[name]["<SCP_SCP_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["scp_scp_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["scp_scp_internal_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SCP_SCP_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["scp_scp_external_ipv6__ipv6_address"] == None else  LVSRouterVipObj["scp_scp_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SCP_SCP_VIP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["scp_scp_storage__address"] == None else LVSRouterVipObj["scp_scp_storage__address"]

        lvsRouterVipDict[name]["<SCP_STORAGE_GATEWAY_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["scp_storage_internal__address"] == None else LVSRouterVipObj["scp_storage_internal__address"]
        lvsRouterVipDict[name]["<SCP_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["scp_storage__address"] == None else LVSRouterVipObj["scp_storage__address"]

        lvsRouterVipDict[name]["<EVT_STORAGE_GATEWAY_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["evt_storage_internal__address"] == None  else LVSRouterVipObj["evt_storage_internal__address"]
        lvsRouterVipDict[name]["<EVT_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["evt_storage__address"] == None else LVSRouterVipObj["evt_storage__address"]

        lvsRouterVipDict[name]["<STR_STR_IF>"] = "" if LVSRouterVipObj["str_str_if"] == None else LVSRouterVipObj["str_str_if"]
        lvsRouterVipDict[name]["<str_STR_vip_1_internal_ip>"] = "" if LVSRouterVipObj["str_internal__address"] == None else LVSRouterVipObj["str_internal__address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_INTERNAL_IPV4_2>"] = "" if LVSRouterVipObj["str_str_internal_2__address"] == None else LVSRouterVipObj["str_str_internal_2__address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_INTERNAL_IPV4_3>"] = "" if LVSRouterVipObj["str_str_internal_3__address"] == None else LVSRouterVipObj["str_str_internal_3__address"]
        lvsRouterVipDict[name]["<str_STR_vip_1_public_ip>"] = "" if LVSRouterVipObj["str_external__address"] == None else LVSRouterVipObj["str_external__address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_PUBLIC_IPV4_2>"] = "" if LVSRouterVipObj["str_str_external_2__address"] == None else LVSRouterVipObj["str_str_external_2__address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_PUBLIC_IPV4_3>"] = "" if LVSRouterVipObj["str_str_external_3__address"] == None else LVSRouterVipObj["str_str_external_3__address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["str_str_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["str_str_internal_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_INTERNAL_IPV6_2>"] = "" if LVSRouterVipObj["str_str_internal_ipv6_2__ipv6_address"] == None else LVSRouterVipObj["str_str_internal_ipv6_2__ipv6_address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_INTERNAL_IPV6_3>"] = "" if LVSRouterVipObj["str_str_internal_ipv6_3__ipv6_address"] == None else LVSRouterVipObj["str_str_internal_ipv6_3__ipv6_address"]
        lvsRouterVipDict[name]["<str_STR_vip_1_public_ipv6_ip>"] = "" if LVSRouterVipObj["str_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["str_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_PUBLIC_IPV6_2>"] = "" if LVSRouterVipObj["str_str_external_ipv6_2__ipv6_address"] == None else LVSRouterVipObj["str_str_external_ipv6_2__ipv6_address"]
        lvsRouterVipDict[name]["<STR_STR_VIP_PUBLIC_IPV6_3>"] = "" if LVSRouterVipObj["str_str_external_ipv6_3__ipv6_address"] == None else LVSRouterVipObj["str_str_external_ipv6_3__ipv6_address"]
        lvsRouterVipDict[name]["<STR_STR_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["str_str_storage__address"] == None else LVSRouterVipObj["str_str_storage__address"]
        lvsRouterVipDict[name]["<str_storage_gateway_1_internal_ip>"] = "" if LVSRouterVipObj["str_storage_internal__address"] == None else LVSRouterVipObj["str_storage_internal__address"]
        lvsRouterVipDict[name]["<STR_IP_STORAGE_IPV4>"] = "" if  LVSRouterVipObj["str_storage__address"] == None else LVSRouterVipObj["str_storage__address"]

        lvsRouterVipDict[name]["<ESN_STR_IF>"] = "" if LVSRouterVipObj["esn_str_if"] == None else LVSRouterVipObj["esn_str_if"]
        lvsRouterVipDict[name]["<ESN_STR_VIP_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["esn_str_internal__address"] == None else LVSRouterVipObj["esn_str_internal__address"]
        lvsRouterVipDict[name]["<ESN_STR_VIP_PUBLIC_IPV4>"] = "" if LVSRouterVipObj["esn_str_external__address"] == None else LVSRouterVipObj["esn_str_external__address"]
        lvsRouterVipDict[name]["<ESN_STR_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["esn_str_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["esn_str_internal_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<ESN_STR_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["esn_str_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["esn_str_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<ESN_STR_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["esn_str_storage__address"] == None else LVSRouterVipObj["esn_str_storage__address"]
        lvsRouterVipDict[name]["<ESN_STORAGE_GATEWAY_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["esn_storage_internal__address"] == None else LVSRouterVipObj["esn_storage_internal__address"]
        lvsRouterVipDict[name]["<EBS_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["ebs_storage__address"] == None else LVSRouterVipObj["ebs_storage__address"]
        lvsRouterVipDict[name]["<EBS_STORAGE_GATEWAY_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["ebs_storage_internal__address"] == None else LVSRouterVipObj["ebs_storage_internal__address"]
        lvsRouterVipDict[name]["<STR_EBS_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["ebs_str_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["ebs_str_external_ipv6__ipv6_address"]

        lvsRouterVipDict[name]["<ASR_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["asr_storage__address"] == None else LVSRouterVipObj["asr_storage__address"]
        lvsRouterVipDict[name]["<ASR_STORAGE_GATEWAY_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["asr_storage_internal__address"] == None else LVSRouterVipObj["asr_storage_internal__address"]
        lvsRouterVipDict[name]["<ASR_ASR_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["asr_asr_storage__address"] == None else LVSRouterVipObj["asr_asr_storage__address"]
        lvsRouterVipDict[name]["<STR_ASR_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["asr_asr_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["asr_asr_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<ASR_ASR_VIP_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["asr_asr_internal__address"] == None else LVSRouterVipObj["asr_asr_internal__address"]
        lvsRouterVipDict[name]["<ASR_ASR_VIP_PUBLIC_IPV4>"] = "" if LVSRouterVipObj["asr_asr_external__address"] == None else LVSRouterVipObj["asr_asr_external__address"]
        lvsRouterVipDict[name]["<EBA_IP_STORAGE_IPV4>"] = "" if LVSRouterVipObj["eba_storage__address"] == None else LVSRouterVipObj["eba_storage__address"]
        lvsRouterVipDict[name]["<EBA_STORAGE_GATEWAY_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["eba_storage_internal__address"] == None else LVSRouterVipObj["eba_storage_internal__address"]
        lvsRouterVipDict[name]["<SVC_MS_OSSFM_VIP_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["msossfm_internal__address"] == None else LVSRouterVipObj["msossfm_internal__address"]
        lvsRouterVipDict[name]["<SVC_MS_OSSFM_VIP_PUBLIC_IPV4>"] = "" if LVSRouterVipObj["msossfm_external__address"] == None else LVSRouterVipObj["msossfm_external__address"]
        lvsRouterVipDict[name]["<SVC_MS_OSSFM_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["msossfm_internal_ipv6__ipv6_address"] == None else  LVSRouterVipObj["msossfm_internal_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SVC_MS_OSSFM_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["msossfm_external_ipv6__ipv6_address"] == None else  LVSRouterVipObj["msossfm_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<EBA_VIP_PUBLIC_IPV4>"] = "" if LVSRouterVipObj["eba_external__address"] == None else LVSRouterVipObj["eba_external__address"]
        lvsRouterVipDict[name]["<EBA_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["eba_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["eba_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<EBA_VIP_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["eba_internal__address"] == None else LVSRouterVipObj["eba_internal__address"]
        lvsRouterVipDict[name]["<EBA_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["eba_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["eba_internal_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SVC_ORAN_VIP_PUBLIC_IPV4>"] = "" if LVSRouterVipObj["oran_external__address"] == None else LVSRouterVipObj["oran_external__address"]
        lvsRouterVipDict[name]["<SVC_ORAN_VIP_PUBLIC_IPV6>"] = "" if LVSRouterVipObj["oran_external_ipv6__ipv6_address"] == None else LVSRouterVipObj["oran_external_ipv6__ipv6_address"]
        lvsRouterVipDict[name]["<SVC_ORAN_VIP_INTERNAL_IPV4>"] = "" if LVSRouterVipObj["oran_internal__address"] == None else LVSRouterVipObj["oran_internal__address"]
        lvsRouterVipDict[name]["<SVC_ORAN_VIP_INTERNAL_IPV6>"] = "" if LVSRouterVipObj["oran_internal_ipv6__ipv6_address"] == None else LVSRouterVipObj["oran_internal_ipv6__ipv6_address"]

    except LVSRouterVip.DoesNotExist:
        logger.warning("There was no LSV Router Data found for this Cluster ID " + str(clusterId))
    return lvsRouterVipDict

def getHybridCloudInfo(clusterId):
    '''
    This function is used to get the Hybrid Cloud information for a given clusterID
    '''
    hybridCloudDict = {}
    try:
        fields = ("ip_type", "internal_subnet",
                  "gateway_internal__address", "gateway_external__address",
                  "internal_subnet_ipv6", "gateway_internal_ipv6__ipv6_address",
                  "gateway_external_ipv6__ipv6_address",)
        hybridCloudObj = HybridCloud.objects.only(fields).values(*fields).get(cluster_id=clusterId)
        name = "HYBRID_CLOUD"
        hybridCloudDict[name]={}
        if str(hybridCloudObj["ip_type"]) == "ipv4":
            hybridCloudDict[name]["<HYBRID_CLOUD_INTERNAL_SUBNET>"] = "" if hybridCloudObj["internal_subnet"] == None else hybridCloudObj["internal_subnet"]
            hybridCloudDict[name]["<HYBRID_CLOUD_GATEWAY_PRIVATE>"] = "" if hybridCloudObj["gateway_internal__address"] == None else hybridCloudObj["gateway_internal__address"]
            hybridCloudDict[name]["<HYBRID_CLOUD_GATEWAY_PUBLIC>"] = ""  if hybridCloudObj["gateway_external__address"] == None else hybridCloudObj["gateway_external__address"]
        else:
            hybridCloudDict[name]["<HYBRID_CLOUD_INTERNAL_SUBNET>"] = "" if hybridCloudObj["internal_subnet_ipv6"] == None else hybridCloudObj["internal_subnet_ipv6"]
            hybridCloudDict[name]["<HYBRID_CLOUD_GATEWAY_PRIVATE>"] = "" if hybridCloudObj["gateway_internal_ipv6__ipv6_address"] == None else hybridCloudObj["gateway_internal_ipv6__ipv6_address"]
            hybridCloudDict[name]["<HYBRID_CLOUD_GATEWAY_PUBLIC>"] = ""  if hybridCloudObj["gateway_external_ipv6__ipv6_address"] == None else hybridCloudObj["gateway_external_ipv6__ipv6_address"]
    except HybridCloud.DoesNotExist:
        logger.warning("There was no Hybrid Cloud Data found for this Cluster ID " + str(clusterId))
    return hybridCloudDict

def getDvmsInformation(clusterId):
    '''
    This function is used to get the Dvms information for a given clusterID
    '''
    dvmsInformationDict = {}
    try:
        fields = "external_ipv4__address", "external_ipv6__ipv6_address", "internal_ipv4__address"
        dvmsInformationObj = DvmsInformation.objects.only(fields).values(*fields).get(cluster_id=clusterId)
        name = "DVMS_INFO"
        dvmsInformationDict[name] = {}

        dvmsInformationDict[name]["<DVMS_PUBLIC_IPV4>"] = "" if dvmsInformationObj["external_ipv4__address"] == None else dvmsInformationObj["external_ipv4__address"]
        dvmsInformationDict[name]["<DVMS_PUBLIC_IPV6>"] = "" if dvmsInformationObj["external_ipv6__ipv6_address"] == None else dvmsInformationObj["external_ipv6__ipv6_address"]
        dvmsInformationDict[name]["<DVMS_INTERNAL_IPV4>"] = ""  if dvmsInformationObj["internal_ipv4__address"] == None else dvmsInformationObj["internal_ipv4__address"]

    except DvmsInformation.DoesNotExist:
        logger.warning("There was no Dvms Information Data found for this Cluster ID " + str(clusterId))
    return dvmsInformationDict
