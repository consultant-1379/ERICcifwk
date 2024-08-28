from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *
from netaddr import IPNetwork

import logging
import dmt.utils
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        mgtServers = ManagementServer.objects.all()
        for mgtServer in mgtServers:
            servers = []
            logger.info("Migration Vlan details for " + str(mgtServer.server.hostname))
            nodeServerObject = Server.objects.get(hostname=mgtServer.server.hostname)
            serverObject =  ManagementServer.objects.get(server=nodeServerObject)
            try:
                networkObject = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth0")
                nic = networkObject.mac_address
            except Exception as e:
                logger.error("Issue with getting the NIC info for Management Server " + str(mgtServer.server.hostname))
                continue

            if IpAddress.objects.filter(nic_id=networkObject.id,ipType="host").exists():
                ipAddrObject = IpAddress.objects.get(nic_id=networkObject.id,ipType="host")
                ipv4Gateway = ipAddrObject.gateway_address
                ipv4Address = ipAddrObject.address
                ipv4Bitmask = ipAddrObject.bitmask
            else:
                ipv4Gateway = ""
                ipv4Address = ""
                ipv4Bitmask = ""

            if IpAddress.objects.filter(nic_id=networkObject.id,ipType="other").exists():
                ipv6AddrObject = IpAddress.objects.get(nic_id=networkObject.id,ipType="other")
                ipv6Address = ipv6AddrObject.ipv6_address
                ipv6Bitmask = ipv6AddrObject.ipv6_bitmask
                ipv6Gateway = ipv6AddrObject.ipv6_gateway
            else:
                ipv6Address = ""
                ipv6Bitmask = ""
                ipv6Gateway = ""

            if IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
                storageIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="storage")
                storageIp = storageIpObject.address
                storageBitmask = storageIpObject.bitmask
                if VlanIPMapping.objects.filter(ipMap=storageIpObject.id).exists():
                    strVlanTagObj = VlanIPMapping.objects.get(ipMap=storageIpObject.id)
                    strVlanTag = strVlanTagObj.vlanTag
                else:
                    strVlanTag = ""
            else:
                strVlanTag = ""
                storageIp = ""
                storageBitmask = ""

            if IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
                bckUpIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="backup")
                bckUpIp = bckUpIpObject.address
                bckUpBitmask = bckUpIpObject.bitmask
                if VlanIPMapping.objects.filter(ipMap=bckUpIpObject.id).exists():
                    bckUpVlanTagObj = VlanIPMapping.objects.get(ipMap=bckUpIpObject.id)
                    bckUpVlanTag = bckUpVlanTagObj.vlanTag
                else:
                    bckUpVlanTag = ""
            else:
                bckUpVlanTag = ""
                bckUpIp = ""
                bckUpBitmask = ""

            if Cluster.objects.filter(management_server__server__hostname=mgtServer.server.hostname).exists():
                clusters = Cluster.objects.filter(management_server__server__hostname=mgtServer.server.hostname)
                for cluster in clusters:
                    multicastIp = ""
                    internalIp = ""
                    if cluster.layout_id == 2:
                        clustersvrs = ClusterServer.objects.filter(cluster=cluster)
                        for cs in clustersvrs:
                            if cs.node_type == "SC-1" or cs.node_type == "SVC-1":
                                serverObj = Server.objects.get(id=cs.server.id)
                                try:
                                    networkObject = NetworkInterface.objects.get(server=serverObj.id, interface="eth0")
                                    nic = networkObject.mac_address
                                except:
                                    logger.error("Issue with getting the NIC info for Cluster Server " + str(cs.server.hostname) + " attached to Management Server ")
                                    continue
                                if InternalIpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                                    internalIPObject = InternalIpAddress.objects.get(nic=networkObject.id,ipType="internal")
                                    internalIp = internalIPObject.address
                                    internalBitmask = internalIPObject.bitmask
                                    if InternalVlanIPMapping.objects.filter(ipMap=internalIPObject.id).exists():
                                        internalVlanTagObj = InternalVlanIPMapping.objects.get(ipMap=internalIPObject.id)
                                        internalVlanTag = internalVlanTagObj.vlanTag
                                    else:
                                        internalIp = ""
                                        internalBitmask = ""
                                        internalVlanTag = ""
                                else:
                                    internalIp = ""
                                    internalBitmask = ""
                                    internalVlanTag = ""

                                if IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                                    multicastIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                                    multicastIp = multicastIpObject.address
                                    multicastBitmask = multicastIpObject.bitmask
                                    if VlanIPMapping.objects.filter(ipMap=multicastIpObject.id).exists():
                                        multicastVlanTagObj = VlanIPMapping.objects.get(ipMap=multicastIpObject.id)
                                        multicastVlanTag = multicastVlanTagObj.vlanTag
                                    else:
                                        multicastVlanTag = ""
                                elif InternalIpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                                    multicastIpObject = InternalIpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                                    multicastIp = multicastIpObject.address
                                    multicastBitmask = multicastIpObject.bitmask
                                    if InternalVlanIPMapping.objects.filter(ipMap=multicastIpObject.id).exists():
                                        multicastVlanTagObj = InternalVlanIPMapping.objects.get(ipMap=multicastIpObject.id)
                                        multicastVlanTag = multicastVlanTagObj.vlanTag
                                    else:
                                        multicastIp = ""
                                        multicastBitmask = ""
                                        multicastVlanTag = ""
                                else:
                                    multicastIp = ""
                                    multicastBitmask = ""
                                    multicastVlanTag = ""
                        if ipv6Address != None and ipv6Bitmask != None:
                            ipv6Subnet = str(ipv6Address) + "/" + str(ipv6Bitmask)
                        else:
                            ipv6Subnet = None
                            ipv6Gateway = None
                        if bckUpIp != "" and bckUpBitmask != "":
                            if bckUpVlanTag == "":
                                bckUpVlanTag = None
                            bckUpBitmask = bckUpBitmask.replace('/','')
                            bckUpIpInfo = IPNetwork(bckUpIp + "/" + str(bckUpBitmask))
                            bckUpSubnet = str(bckUpIpInfo.network) + "/" + str(bckUpIpInfo.prefixlen)
                        else:
                            logger.error("No Backup Info Attached")
                            continue
                        if storageIp != "" and storageBitmask != "":
                            if strVlanTag == "":
                                strVlanTag = None
                            storageBitmask = storageBitmask.replace('/','')
                            storageIpInfo = IPNetwork(storageIp + "/" + str(storageBitmask))
                            storageSubnet = str(storageIpInfo.network) + "/" + str(storageIpInfo.prefixlen)
                        else:
                            logger.error("No Storage Info Attached")
                            continue
                        if ipv4Address != "" and ipv4Bitmask != "":
                            ipv4Bitmask = ipv4Bitmask.replace('/','')
                            externalIpInfo = IPNetwork(ipv4Address + "/" + str(ipv4Bitmask))
                            externalSubnet = str(externalIpInfo.network) + "/" + str(externalIpInfo.prefixlen)
                        else:
                            logger.error("No Service ipv4 Info Attached")
                            continue
                        if multicastIp != "" and multicastBitmask != "":
                            multicastBitmask = multicastBitmask.replace('/','')
                            multicastIpInfo = IPNetwork(multicastIp + "/" + str(multicastBitmask))
                            multicastSubnet = str(multicastIpInfo.network) + "/" + str(multicastIpInfo.prefixlen)
                        else:
                            multicastSubnet = dmt.utils.getSubnetDetails("jgroup")
                            multicastVlanTag = None
                        if internalIp != "" and internalBitmask != "":
                            internalBitmask = internalBitmask.replace('/','')
                            internalIpInfo = IPNetwork(internalIp + "/" + str(internalBitmask))
                            internalSubnet = str(internalIpInfo.network) + "/" + str(internalIpInfo.prefixlen)
                        else:
                            internalSubnet = dmt.utils.getSubnetDetails("internal")
                            internalVlanTag = None
                        logger.info("Updating Vlan info for Management Server : " + str(mgtServer.server.hostname) + " within cluster " + str(cluster.name))
                        if VlanDetails.objects.filter(cluster=cluster.id).exists():
                            HbVlanObj = VlanDetails.objects.get(cluster=cluster.id)
                            hbaVlan = HbVlanObj.hbAVlan
                            hbbVlan = HbVlanObj.hbBVlan
                            servicesVlan = None
                            returnedValue,message = dmt.utils.editVlanDetails(cluster.id,'edit',hbaVlan,hbbVlan,externalSubnet,ipv4Gateway,ipv6Gateway,ipv6Subnet,storageSubnet,bckUpSubnet,multicastSubnet,internalSubnet,strVlanTag,bckUpVlanTag,multicastVlanTag,internalVlanTag,servicesVlan)
                        else:
                            hbaVlan = None
                            hbbVlan = None
                            servicesVlan = None
                            returnedValue,message = dmt.utils.createVlanDetails(cluster.id,'add',hbaVlan,hbbVlan,externalSubnet,ipv4Gateway,ipv6Gateway,ipv6Subnet,storageSubnet,bckUpSubnet,multicastSubnet,internalSubnet,strVlanTag,bckUpVlanTag,multicastVlanTag,internalVlanTag,servicesVlan)
                        if returnedValue == "1":
                            message = "Error: " + str(message)
                            logger.error(message)
                        else:
                            logger.info("Success")
                    else:
                        logger.error("Cluster Layout is not CMW")
                        continue
            else:
                logger.error("No Cluster Assigned to Management Server")
                continue
        logger.info("Deleting unwanted information after the MS clean-up")
        mgtServers = ManagementServer.objects.all()
        for mgtServer in mgtServers:
            servers = []
            nodeServerObject = Server.objects.get(hostname=mgtServer.server.hostname)
            serverObject =  ManagementServer.objects.get(server=nodeServerObject)
            try:
                networkObject = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth0")
                nic = networkObject.mac_address
            except Exception as e:
                continue

            # With the cleanout of the MS info old info should that could cause issue with duplicate IP should be removed if exists
            try:
                if Ilo.objects.filter(server=nodeServerObject).exists():
                    iloObject = Ilo.objects.get(server=nodeServerObject)
                    iloIpObj = IpAddress.objects.get(id=iloObject.ipMapIloAddress_id)
                    iloIpObj.delete()
                    iloObject.delete()
            except Exceptioin as e:
                logger.error("Issue deleting the ilo info for Management Server " + str(mgtServer))
                continue

            if IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                multicastIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                if VlanIPMapping.objects.filter(ipMap=multicastIpObject).exists():
                    VlanIPMapping.objects.filter(ipMap=multicastIpObject).delete()
                if VlanIPMapping.objects.filter(ipMap=multicastIpObject).exists():
                    VlanIPMapping.objects.filter(ipMap=multicastIpObject).delete()
                IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").delete()

            if BladeHardwareDetails.objects.filter(mac_address=networkObject.id).exists():
                BladeHardwareDetails.objects.filter(mac_address=networkObject.id).delete()

            if IpAddress.objects.filter(nic_id=networkObject.id,ipType="other").exists():
                IpAddress.objects.filter(nic=networkObject.id,ipType="other").delete()

            if VirtualManagementServer.objects.filter(mgtServer_id=serverObject.id).exists():
                virtualMgtObj = VirtualManagementServer.objects.get(mgtServer_id=serverObject.id)
                if VirtualMSCredentialMapping.objects.filter(virtualMgtServer=virtualMgtObj).exists():
                    virtualMgtServCredMap = VirtualMSCredentialMapping.objects.get(virtualMgtServer=virtualMgtObj)
                    credentials =  Credentials.objects.get(id=virtualMgtServCredMap.credentials.id)
                    credentials.delete()
                    virtualMgtServCredMap.delete()
                if Server.objects.filter(id=virtualMgtObj.server_id).exists():
                    virtualMgtServer = Server.objects.get(id=virtualMgtObj.server_id)
                else:
                    virtualMgtServer = None
                # Deleting the selected Virtual Management Server
                if Server.objects.filter(hostname=virtualMgtServer.hostname).exists():
                    virtualNodeServerObject = Server.objects.get(hostname=virtualMgtServer.hostname)
                else:
                    virtualNodeServerObject = None
                try:
                    if virtualNodeServerObject != None:
                        if HardwareDetails.objects.filter(server=virtualNodeServerObject).exists():
                            HardwareDetails.objects.filter(server=virtualNodeServerObject).delete()
                        if VirtualManagementServer.objects.filter(server=virtualNodeServerObject).exists():
                            VirtualManagementServer.objects.filter(server=virtualNodeServerObject).delete()
                    if virtualMgtServer != None:
                        if Server.objects.filter(hostname=virtualMgtServer.hostname).exists():
                            Server.objects.filter(hostname=virtualMgtServer.hostname).delete()
                    if virtualNodeServerObject != None:
                        if NetworkInterface.objects.filter(server=virtualNodeServerObject.id).exists():
                            NetworkInterface.objects.filter(server=virtualNodeServerObject.id).delete()
                        if NetworkInterface.objects.filter(server=virtualNodeServerObject.id, interface="eth0").exists():
                            virtualNetworkObject = NetworkInterface.objects.get(server=virtualNodeServerObject.id, interface="eth0")
                            if IpAddress.objects.filter(nic=virtualNetworkObject.id).exists():
                                IpAddress.objects.filter(nic=virtualNetworkObject.id).delete()
                except Exception as e:
                    logger.error("There was an issue deleting the virtual managment server " +str(virtualMgtServer.hostname)+ " from database: " +str(e))
                    continue
            if Cluster.objects.filter(management_server__server__hostname=mgtServer.server.hostname).exists():
                clusters = Cluster.objects.filter(management_server__server__hostname=mgtServer.server.hostname)
                for cluster in clusters:
                    if cluster.layout_id == 2:
                        clustersvrs = ClusterServer.objects.filter(cluster=cluster)
                        for cs in clustersvrs:
                            serverObj = Server.objects.get(id=cs.server.id)
                            try:
                                networkObject = NetworkInterface.objects.get(server=serverObj.id, interface="eth0")
                                nic = networkObject.mac_address
                            except:
                                continue
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
                                storageIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="storage")
                                if VlanIPMapping.objects.filter(ipMap=storageIpObject.id).exists():
                                    VlanIPMapping.objects.filter(ipMap=storageIpObject.id).delete()
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
                                bckUpIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="backup")
                                if VlanIPMapping.objects.filter(ipMap=bckUpIpObject.id).exists():
                                    VlanIPMapping.objects.filter(ipMap=bckUpIpObject.id).delete()
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                                multicastIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                                if VlanIPMapping.objects.filter(ipMap=multicastIpObject.id).exists():
                                    VlanIPMapping.objects.filter(ipMap=multicastIpObject.id).delete()
                            elif InternalIpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                                multicastIpObject = InternalIpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                                if InternalVlanIPMapping.objects.filter(ipMap=multicastIpObject.id).exists():
                                    InternalVlanIPMapping.objects.filter(ipMap=multicastIpObject.id).delete()
                            if InternalIpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                                internalIPObject = InternalIpAddress.objects.get(nic=networkObject.id,ipType="internal")
                                if InternalVlanIPMapping.objects.filter(ipMap=internalIPObject.id).exists():
                                    InternalVlanIPMapping.objects.filter(ipMap=internalIPObject.id).delete()
