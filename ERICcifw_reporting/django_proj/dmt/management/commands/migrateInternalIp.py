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
        logger.info("Migrating IP Data from the Internal IP address to the IP address")
        for mgtServer in mgtServers:
            #if mgtServer.server.hostname != "attorlms3":
            #    continue
            servers = []
            logger.info("Migration Data for Management Server " + str(mgtServer.server.hostname))
            nodeServerObject = Server.objects.get(hostname=mgtServer.server.hostname)
            serverObject =  ManagementServer.objects.get(server=nodeServerObject)
            try:
                networkObject = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth0")
                nic = networkObject.mac_address
            except Exception as e:
                logger.error("Issue with getting the NIC info for Management Server " + str(mgtServer.server.hostname) + ", Exception: " +str(e))
                continue

            if Cluster.objects.filter(management_server__server__hostname=mgtServer.server.hostname).exists():
                clusters = Cluster.objects.filter(management_server__server__hostname=mgtServer.server.hostname)
                for cluster in clusters:
                    logger.info("Deployment Layout for cluster id " + str(cluster.id) + " is " + str(cluster.layout.name))
                    hardwareType = cluster.management_server.server.hardware_type
                    if ClusterServer.objects.filter(cluster=cluster).exists():
                        clustersvrs = ClusterServer.objects.filter(cluster=cluster)
                    else:
                        logger.error("No Server Assigned to the cluster id " + str(cluster.id))
                    for cs in clustersvrs:
                        ipv4Identifier = ipv6Identifier = cluster.id
                        serverObj = Server.objects.get(id=cs.server.id)
                        try:
                            networkObject = NetworkInterface.objects.get(server=serverObj.id, interface="eth0")
                            nic = networkObject.mac_address
                        except:
                            logger.error("Issue with getting the NIC info for Cluster Server " + str(cs.server.hostname) + " attached to Management Server ")

                        # Move the internal IP's
                        try:
                            if InternalIpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                                internalIPObject = InternalIpAddress.objects.get(nic=networkObject.id,ipType="internal")
                                internalIp = internalIPObject.address
                                if not IpAddress.objects.filter(nic=networkObject,ipType="internal",address=internalIp,ipv4UniqueIdentifier=ipv4Identifier).exists():
                                    internalIPObject = IpAddress.objects.create(nic=networkObject,ipType="internal",address=internalIp,ipv4UniqueIdentifier=ipv4Identifier)
                                    internalIPObject.save(force_update=True)
                                    #InternalIpAddress.objects.get(nic=networkObject.id,ipType="internal").delete()
                                else:
                                    logger.error("Unable to transfer internal address " + str(internalIp) + " for cluster id " + str(cluster.id) + " Ip Already Exists within the IP Table. Search nic id " + (networkObject.id) + " ipv4UniqueIdentifier " + str(ipv4Identifier))
                        except Exception as e:
                            logger.error("Error with the Transfer of the Data for IP's for " + str(serverObj.hostname) + " for cluster id " + str(cluster.id) + ", Exception: " + str(e))

                        # Move the jgroup IP's
                        try:
                            if InternalIpAddress.objects.filter(nic=networkObject.id,ipType="jgroup").exists():
                                jgroupIpObject = InternalIpAddress.objects.get(nic=networkObject.id,ipType="jgroup")
                                jgroupIp = jgroupIpObject.address
                                if not IpAddress.objects.filter(nic=networkObject,ipType="jgroup",address=jgroupIp,ipv4UniqueIdentifier=ipv4Identifier).exists():
                                    jgroupIpObject = IpAddress.objects.create(nic=networkObject,ipType="jgroup",address=jgroupIp,ipv4UniqueIdentifier=ipv4Identifier)
                                    jgroupIpObject.save(force_update=True)
                                    #InternalIpAddress.objects.get(nic=networkObject.id,ipType="jgroup").delete()
                                else:
                                    logger.error("Unable to transfer jgroup address " + str(jgroupIp) + " for cluster id " + str(cluster.id)+ " Ip Already Exists within the IP Table. Search nic id " + (networkObject.id) + " ipv4UniqueIdentifier " + str(ipv4Identifier))
                        except Exception as e:
                            logger.error("Error with the Transfer of the Data for IP's for " + str(serverObj.hostname) + " for cluster id " + str(cluster.id) + ", Exception: " + str(e))

                        # Move the multicast IP's
                        try:
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                                multicastIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                                multicastIp = multicastIpObject.address
                            elif InternalIpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                                multicastIpObject = InternalIpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                                multicastIp = multicastIpObject.address
                            else:
                                multicastIpObject = None
                                multicastIp = ""
                            if multicastIpObject != None:
                                if not IpAddress.objects.filter(nic=networkObject,ipType="multicast",address=multicastIp,ipv4UniqueIdentifier=ipv4Identifier).exists():
                                    multicastIpObject = IpAddress.objects.create(nic=networkObject,ipType="multicast",address=multicastIp,ipv4UniqueIdentifier=ipv4Identifier)
                                    multicastIpObject.save(force_update=True)
                                    #InternalIpAddress.objects.get(nic=networkObject.id,ipType="multicast").delete()
                                else:
                                    logger.error("Unable to transfer multicast address " + str(multicastIp) + " for cluster id " + str(cluster.id)+ " Ip Already Exists within the IP Table. Search nic id " + (networkObject.id) + " ipv4UniqueIdentifier " + str(ipv4Identifier))
                        except Exception as e:
                            logger.error("Error with the Transfer of the Data for IP's for " + str(serverObj.hostname) + " for cluster id " + str(cluster.id) + ", Exception: " + str(e))
                    if cluster.layout_id == 2:
                        ServicesClr = ServicesCluster.objects.filter(cluster_id=cluster.id)
                        for servClr in ServicesClr:
                            serviceGroup = ServiceGroup.objects.filter(service_cluster_id=servClr.id)
                            for obj in serviceGroup:
                                if InternalServiceGroupInstance.objects.filter(service_group=obj).exists():
                                    instIpMapObj = InternalServiceGroupInstance.objects.filter(service_group=obj)
                                    for serviceInstance in instIpMapObj:
                                        instIpObj = InternalIpAddress.objects.get(id=serviceInstance.ipMap_id)
                                        if not IpAddress.objects.filter(address=instIpObj.address,ipv4UniqueIdentifier=ipv4Identifier).exists():
                                            instanceIpObj = IpAddress.objects.create(address=instIpObj.address,bitmask=instIpObj.bitmask,gateway_address=instIpObj.gateway_address,ipType="serviceUnit_" + str(obj.id),ipv4UniqueIdentifier=ipv4Identifier)
                                            instIpMapObj2 = ServiceGroupInstanceInternal.objects.create(name=serviceInstance.name,service_group=obj,ipMap=instanceIpObj)
                                            #InternalIpAddress.objects.get(id=serviceInstance.ipMap_id).delete()
                                        else:
                                            logger.error("Unable to transfer address " + str(instIpObj.address) + " for cluster id " + str(cluster.id) + " Ip Already Exists within the IP Table.")

                    else:
                        if VirtualImage.objects.filter(cluster_id=cluster.id):
                            virtualImage = VirtualImage.objects.filter(cluster_id=cluster.id).order_by('name')
                            for virtualImageObj in virtualImage:
                                #if virtualImageObj.name != "SSO_1":
                                #    continue
                                if VirtualImageIPInfo.objects.filter(virtual_image=virtualImageObj.id).exists():
                                    virtualImgObjs = VirtualImageIPInfo.objects.filter(virtual_image=virtualImageObj.id)
                                    for virtualImgObj in virtualImgObjs:
                                        number = virtualImgObj.number
                                        hostname = virtualImgObj.hostname
                                        if virtualImgObj.ipMapInternal_id != None:
                                            ipAddressObj = InternalIpAddress.objects.get(id=virtualImgObj.ipMapInternal_id)
                                            address = ipAddressObj.address
                                            ipType = ipAddressObj.ipType
                                        else:
                                            if virtualImgObj.ipMap.address != None:
                                                ipAddressObj = IpAddress.objects.get(id=virtualImgObj.ipMap_id)
                                                address = ipAddressObj.address
                                                ipType = ipAddressObj.ipType
                                            else:
                                                ipAddressObj = IpAddress.objects.get(id=virtualImgObj.ipMap_id)
                                                address = ipAddressObj.ipv6_address
                                                ipType = ipAddressObj.ipType
                                                address = virtualImgObj.ipMap.ipv6_address
                                                ipType = address.ipType
                                        if "cloud" in hardwareType:
                                            ipv4Identifier = ipv6Identifier = cluster.id
                                        else:
                                            ipv4Identifier = ipv6Identifier = '1'
                                        try:
                                            if "internal" in ipType:
                                                virtualImageIpObj = IpAddress.objects.create(address=address,ipType=ipType,ipv4UniqueIdentifier=cluster.id)
                                                virtualImageMapObj = VirtualImageInfoIp.objects.create(number=number,hostname=hostname,virtual_image=virtualImageObj,ipMap=virtualImageIpObj)
                                                #InternalIpAddress.objects.get(id=virtualImgObj.ipMapInternal_id).delete()
                                            elif "jgroup" in ipType:
                                                virtualImageIpObj = IpAddress.objects.create(address=address,ipType=ipType,ipv4UniqueIdentifier=cluster.id)
                                                virtualImageMapObj = VirtualImageInfoIp.objects.create(number=number,hostname=hostname,virtual_image=virtualImageObj,ipMap=virtualImageIpObj)
                                                #InternalIpAddress.objects.get(id=virtualImgObj.ipMapInternal_id).delete()
                                            else:
                                                if "ipv6Public" in ipType:
                                                    virtualImageIpObj = IpAddress.objects.get(ipv6_address=address,ipType=ipType,ipv6UniqueIdentifier=ipv6Identifier)
                                                else:
                                                    if "ipv6Public" in ipType:
                                                        virtualImageIpObj = IpAddress.objects.get(ipv6_address=address,ipType=ipType,ipv6UniqueIdentifier=ipv6Identifier)
                                                    else:
                                                        virtualImageIpObj = IpAddress.objects.get(address=address,ipType=ipType,ipv4UniqueIdentifier=ipv4Identifier)
                                                virtualImageMapObj = VirtualImageInfoIp.objects.create(number=number,hostname=hostname,virtual_image=virtualImageObj,ipMap=virtualImageIpObj)
                                        except Exception as e:
                                            message = "There was an issue with the saving of the Virtual Image IP (" + str(virtualImgObj.virtual_image.name) + ") data for cluster id " + str(cluster.id) + " Exception:  " + str(e)
                                            logger.error(message)
                        if DatabaseVip.objects.filter(cluster_id=cluster.id).exists():
                            databaseVipObj = DatabaseVip.objects.get(cluster_id=cluster.id)
                            postgresAddress = str(databaseVipObj.postgres_address.address)
                            versantAddress = str(databaseVipObj.versant_address.address)
                            mysqlAddress = str(databaseVipObj.mysql_address.address)
                            opendjAddress = str(databaseVipObj.opendj_address.address)
                            try:
                                postgresAddressObj = IpAddress.objects.create(\
                                        address=str(postgresAddress),\
                                        ipType="databaseVip_" + str(cluster.id),\
                                        ipv4UniqueIdentifier=cluster.id)
                                versantAddressObj = IpAddress.objects.create(\
                                        address=str(versantAddress),\
                                        ipType="databaseVip_" + str(cluster.id),\
                                        ipv4UniqueIdentifier=cluster.id)
                                mysqlAddressObj = IpAddress.objects.create(\
                                        address=str(mysqlAddress),\
                                        ipType="databaseVip_" + str(cluster.id),\
                                        ipv4UniqueIdentifier=cluster.id)
                                opendjAddressObj = IpAddress.objects.create(\
                                        address=str(opendjAddress),\
                                        ipType="databaseVip_" + str(cluster.id),\
                                        ipv4UniqueIdentifier=cluster.id)
                                databaseVipObj = DatabaseVips.objects.create(\
                                    postgres_address=postgresAddressObj,\
                                    versant_address=versantAddressObj,\
                                    mysql_address=mysqlAddressObj,\
                                    opendj_address=opendjAddressObj,\
                                    cluster=cluster)
                                #InternalIpAddress.objects.get(address=postgresAddress,ipType="databaseVip_" + str(cluster.id)).delete()
                                #InternalIpAddress.objects.get(address=versantAddressObj,ipType="databaseVip_" + str(cluster.id)).delete()
                                #InternalIpAddress.objects.get(address=mysqlAddressObj,ipType="databaseVip_" + str(cluster.id)).delete()
                                #InternalIpAddress.objects.get(address=opendjAddressObj,ipType="databaseVip_" + str(cluster.id)).delete()
                            except Exception as e:
                                message = "There was an issue saving the database VIP information to the cluster. Exception: " + str(e)
                                logger.error(message)

            else:
                logger.info("No Cluster Information for Management Server: " + str(mgtServer.server.hostname))
