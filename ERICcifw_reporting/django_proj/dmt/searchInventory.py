from dmt.models import *

import subprocess, os, sys, time, getpass, signal, urllib2, traceback, socket, logging, re, commands, copy

def searchInventory(valueEntered):

    '''
    Main function of the search inventory functionality input value to search
    '''
    defaultResultDict = {'serverId': None, 'serverType': None, 'identifier': None, 'clusterId': None, 'unitNumber': None, 'unitName': None, 'ipType': None}
    finalResults = []
    if Server.objects.filter(hostname=valueEntered).exists():
        foundObjects = Server.objects.only('id').values('id').filter(hostname=valueEntered)
        for foundObject in foundObjects:
            resultDict = copy.deepcopy(defaultResultDict)
            resultDict['serverId'] = foundObject['id']
            resultDict['ipType'] = "found"
            finalResults.append(resultDict)
    if NetworkInterface.objects.filter(mac_address=valueEntered).exists():
        foundObjects = NetworkInterface.objects.only('server_id').values('server_id').filter(mac_address=valueEntered)
        for foundObject in foundObjects:
            resultDict = copy.deepcopy(defaultResultDict)
            resultDict['serverId'] = foundObject['server_id']
            resultDict['ipType'] = "found"
            finalResults.append(resultDict)
    filterValues = ('id', 'nic_id', 'nic__server_id', 'ipType', 'address', 'ipv6_address')
    if IpAddress.objects.filter(address=valueEntered).exists():
        foundObjects = IpAddress.objects.only(filterValues).values(*filterValues).filter(address=valueEntered)
        for foundObject in foundObjects:
            resultDict = copy.deepcopy(defaultResultDict)
            resultDict['ipAddressObj'] = foundObject['address']
            resultDict['ipAddressId'] = foundObject['id']
            if foundObject['nic_id'] != None:
                if foundObject['nic__server_id'] != "":
                    resultDict['serverId'] = foundObject['nic__server_id']
                    resultDict['ipType'] = "found"
            elif "serviceUnit" in foundObject['ipType']:
                resultDict['ipType'] = "serviceUnit"
            elif "veritas" in foundObject['ipType']:
                resultDict['ipType'] = "veritas"
            elif "ilo" in foundObject['ipType']:
                resultDict['ipType'] = "ilo"
            elif "ulticast" in foundObject['ipType']:
                resultDict['ipType'] = "multicast"
            elif "virtualImage_public" in foundObject['ipType']:
                resultDict['ipType'] = "virtualImage_public"
            elif "virtualImage_storage" in foundObject['ipType']:
                resultDict['ipType'] = "virtualImage_storage"
            elif "virtualImage_internal" in foundObject['ipType']:
                resultDict['ipType'] = "virtualImage_internal"
            elif "virtualImage_jgroup" in foundObject['ipType']:
                resultDict['ipType'] = "virtualImage_jgroup"
            elif "lvsRouterVip" in foundObject['ipType']:
                resultDict['ipType'] = "lvsRouterVip"
            elif "hybridCloud" in foundObject['ipType']:
                resultDict['ipType'] = "hybridCloud"
            elif "databaseVip" in foundObject['ipType']:
                resultDict['ipType'] = "dataBaseVip"
            elif "dvmsInformation" in foundObject['ipType']:
                resultDict['ipType'] = "dvmsInformation"
            else:
                if StorageIPMapping.objects.filter(ipaddr_id=foundObject['id']).exists():
                    resultDict['ipType'] = "san"
                    ipSanObject = StorageIPMapping.objects.only('storage_id').values('storage_id').get(ipaddr_id=foundObject['id'])
                    resultDict['serverId'] = ipSanObject['storage_id']
                elif EnclosureIPMapping.objects.filter(ipaddr_id=foundObject['id']).exists():
                    resultDict['ipType'] = "enclosure"
                    ipEnclosureObject = EnclosureIPMapping.objects.only('enclosure_id').values('enclosure_id').get(ipaddr_id=foundObject['id'])
                    resultDict['serverId'] = ipEnclosureObject['enclosure_id']
            finalResults.append(resultDict)
    if IpAddress.objects.filter(ipv6_address=valueEntered).exists():
        foundObjects = IpAddress.objects.only(filterValues).values(*filterValues).filter(ipv6_address=valueEntered)
        for foundObject in foundObjects:
            resultDict = copy.deepcopy(defaultResultDict)
            resultDict['ipAddressObj'] = foundObject['ipv6_address']
            resultDict['ipAddressId'] = foundObject['id']
            if foundObject['nic_id'] != None:
                if foundObject['nic__server_id'] != "":
                    resultDict['serverId'] = foundObject['nic__server_id']
                    resultDict['ipType'] = "found"
            elif "virtualImage_ipv6Public" in foundObject['ipType']:
                resultDict['ipType'] = "virtualImage_ipv6Public"
            elif "virtualImage_ipv6Internal" in foundObject['ipType']:
                resultDict['ipType'] = "virtualImage_ipv6Internal"
            elif "lvsRouterVip" in foundObject['ipType']:
                resultDict['ipType'] = "lvsRouterVip"
            elif "databaseVip" in foundObject['ipType']:
                resultDict['ipType'] = "dataBaseVip"
            elif "dvmsInformation" in foundObject['ipType']:
                resultDict['ipType'] = "dvmsInformation"
            finalResults.append(resultDict)
    filterValues = ('hostname', 'id')
    if Storage.objects.filter(hostname=valueEntered).exists():
        foundObjects = storageObj = Storage.objects.only(filterValues).values(*filterValues).filter(hostname=valueEntered)
        for foundObject in foundObjects:
            resultDict = copy.deepcopy(defaultResultDict)
            resultDict['serverType'] = "SAN Server"
            resultDict['identifier'] = foundObject['hostname']
            resultDict['ipType'] = "found"
            resultDict['serverId'] = foundObject['id']
            finalResults.append(resultDict)
    if Enclosure.objects.filter(hostname=valueEntered).exists():
        foundObjects = Enclosure.objects.only(filterValues).values(*filterValues).filter(hostname=valueEntered)
        for foundObject in foundObjects:
            resultDict = copy.deepcopy(defaultResultDict)
            resultDict['serverType'] = "Enclosure"
            resultDict['identifier'] = foundObject['hostname']
            resultDict['ipType'] = "found"
            resultDict['serverId'] = foundObject['id']
            finalResults.append(resultDict)

    allResults = []
    extra_public_list = ['serviceUnit','veritas', 'ilo', 'multicast', 'virtualImage_public', 'virtualImage_ipv6Public', 'virtualImage_storage', 'virtualImage_internal', 'virtualImage_ipv6Internal', 'virtualImage_jgroup','lvsRouterVip', 'hybridCloud', 'dataBaseVip', 'dvmsInformation']
    for finalResult in finalResults:
        finalResultCopy = copy.deepcopy(finalResult)
        if finalResult['ipType'] != None:
            if finalResult['serverType'] == None:
                if finalResult['ipType'] in extra_public_list:
                    (finalResultCopy['serverType'],finalResultCopy['identifier'],finalResultCopy['clusterId'],finalResultCopy['unitName'],finalResultCopy['unitNumber'],finalResultCopy['serverId']) = searchInventoryExtraPublicDetails(finalResult['ipAddressId'],finalResult['ipType'])
                else:
                    (finalResultCopy['serverType'],finalResultCopy['identifier'],finalResultCopy['clusterId']) = searchInventoryServerDetails(finalResult['serverId'],finalResult['ipType'])
        if finalResultCopy['identifier'] != None:
            allResults.append(finalResultCopy)
    return allResults


def searchInventoryExtraPublicDetails(ipAddressId,ipType):
    '''
    Search Functionality used to get the generic information for the public ips for the views function searchInventory
    '''
    serviceInstanceObj = identifier = unitNumber = unitName = clusterId = serverId = None
    clusterValues = ('cluster_id', 'cluster__name')
    if ipType == "serviceUnit":
        serverType = "Service Unit"
        filterValues = ('name', 'service_group__name', 'service_group__service_cluster__cluster__name', 'service_group__service_cluster__cluster__id')
        if not ServiceGroupInstance.objects.filter(ipMap_id=ipAddressId).exists():
            if ServiceGroupInstanceInternal.objects.filter(ipMap_id=ipAddressId).exists():
               serviceInstanceObj = ServiceGroupInstanceInternal.objects.only(filterValues).values(*filterValues).get(ipMap_id=ipAddressId)
        else:
            serviceInstanceObj = ServiceGroupInstance.objects.get(ipMap_id=ipAddressId)
        if serviceInstanceObj:
            unitNumber = serviceInstanceObj['name']
            unitName = serviceInstanceObj['service_group__name']
            identifier = serviceInstanceObj['service_group__service_cluster__cluster__name']
            clusterId = serviceInstanceObj['service_group__service_cluster__cluster__id']
    elif ipType in ['virtualImage_public', 'virtualImage_ipv6Public', 'virtualImage_storage', 'virtualImage_internal', 'virtualImage_jgroup', 'virtualImage_ipv6Internal']:
        serverType = "Virtual Image"
        unitName = str(ipType).split('_')[1]
        unitNumber = None
        if VirtualImageInfoIp.objects.filter(ipMap_id=ipAddressId).exists():
            filterValues = ('virtual_image__name', 'virtual_image__cluster_id')
            virtualImageInfoIpObj = VirtualImageInfoIp.objects.only(filterValues).values(*filterValues).get(ipMap_id=ipAddressId)
            identifier = virtualImageInfoIpObj['virtual_image__name']
            clusterId = virtualImageInfoIpObj['virtual_image__cluster_id']
    elif ipType == "veritas":
        serverType = "Veritas"
        veritasObj = None
        dentifier = None
        clusterId = None
        unitName = None
        unitNumber = None
        if VeritasCluster.objects.filter(ipMapGCO_id=ipAddressId).exists():
            veritasObj = VeritasCluster.objects.only(clusterValues).values(*clusterValues).get(ipMapGCO_id=ipAddressId)
            unitName = "GCO"
        elif VeritasCluster.objects.filter(ipMapCSG_id=ipAddressId).exists():
            unitName = "CSG"
            veritasObj = VeritasCluster.objects.only(clusterValues).values(*clusterValues).get(ipMapCSG_id=ipAddressId)
        if veritasObj:
            identifier = veritasObj['cluster__name']
            clusterId = veritasObj['cluster_id']
            unitNumber = "NA"
    elif ipType == "ilo":
        filterValues = ('server__hostname', 'server_id', 'server__hardware_type')
        iloObj = Ilo.objects.only(filterValues).values(*filterValues).get(ipMapIloAddress_id=ipAddressId)
        serverType = "Server ILO"
        unitName = iloObj['server__hostname']
        unitNumber = iloObj['server__hardware_type']
        if ClusterServer.objects.filter(server_id=iloObj['server_id']).exists():
            storageLocObj = ClusterServer.objects.only(clusterValues).values(*clusterValues).get(server_id=iloObj['server_id'])
            identifier = storageLocObj['cluster__name']
            clusterId = storageLocObj['cluster_id']
        elif ManagementServer.objects.filter(server_id=iloObj['server_id']).exists():
            filterValues = ('server__hostname', 'server_id')
            storageLocObj = ManagementServer.objects.only(filterValues).values(*filterValues).get(server_id=iloObj['server_id'])
            identifier = storageLocObj['server__hostname']
            serverId = storageLocObj['server_id']
            serverType = "Management Server"
    elif ipType == "multicast":
        serverType = "Multicast Info"
        enmMulticastObj = None
        multicastObj = None
        filterValues = ('service_cluster__cluster_id', 'service_cluster__cluster__name')
        if Multicast.objects.filter(ipMapDefaultAddress_id=ipAddressId).exists():
            multicastObj = Multicast.objects.only(filterValues).values(*filterValues).get(ipMapDefaultAddress_id=ipAddressId)
            unitName = "Multicast Default Address"
        if Multicast.objects.filter(ipMapMessagingGroupAddress_id=ipAddressId).exists():
            multicastObj = Multicast.objects.only(filterValues).values(*filterValues).get(ipMapMessagingGroupAddress_id=ipAddressId)
            unitName = "Multicast Messaging Group Address"
        if Multicast.objects.filter(ipMapUdpMcastAddress_id=ipAddressId).exists():
            multicastObj = Multicast.objects.only(filterValues).values(*filterValues).get(ipMapUdpMcastAddress_id=ipAddressId)
            unitName = "Multicast UDP Address"
        if Multicast.objects.filter(ipMapMpingMcastAddress_id=ipAddressId).exists():
            multicastObj = Multicast.objects.only(filterValues).values(*filterValues).get(ipMapMpingMcastAddress_id=ipAddressId)
            unitName = "Multicast M-Ping Address"
        if ClusterMulticast.objects.filter(enm_messaging_address=ipAddressId).exists():
            enmMulticastObj = ClusterMulticast.objects.only(clusterValues).values(*clusterValues).get(enm_messaging_address=ipAddressId)
            unitName = "Messaging Address"
        if ClusterMulticast.objects.filter(udp_multicast_address=ipAddressId).exists():
            enmMulticastObj = ClusterMulticast.objects.only(clusterValues).values(*clusterValues).get(udp_multicast_address=ipAddressId)
            unitName = "UDP Multicast Address"

        if multicastObj != None:
            identifier = multicastObj['service_cluster__cluster__name']
            clusterId = multicastObj['service_cluster__cluster_id']
        elif enmMulticastObj != None:
            identifier = enmMulticastObj['cluster__name']
            clusterId = enmMulticastObj['cluster_id']
        unitNumber = "NA"
    elif ipType == "lvsRouterVip":
        serverType = "LVS Router"
        unitNumber = "NA"
        LVSRouterObj = None
        if LVSRouterVip.objects.filter(pm_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(pm_internal_id=ipAddressId)
            unitName = "LVS Router PM Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(pm_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(pm_external_id=ipAddressId)
            unitName = "LVS Router PM External IPV4 VIP"
        elif LVSRouterVip.objects.filter(fm_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(fm_internal_id=ipAddressId)
            unitName = "LVS Router FM Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(fm_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(fm_external_id=ipAddressId)
            unitName = "LVS Router FM External IPV4 VIP"
        elif LVSRouterVip.objects.filter(cm_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(cm_internal_id=ipAddressId)
            unitName = "LVS Router CM Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(cm_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(cm_external_id=ipAddressId)
            unitName = "LVS Router CM External IPV4 VIP"
        elif LVSRouterVip.objects.filter(msossfm_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(msossfm_external_id=ipAddressId)
            unitName = "LVS Router MSOSSFM External IPV4 VIP"
        elif LVSRouterVip.objects.filter(msossfm_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(msossfm_internal_id=ipAddressId)
            unitName = "LVS Router MSOSSFM Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(svc_pm_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(svc_pm_storage_id=ipAddressId)
            unitName = "LVS Router Service PM Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(svc_fm_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(svc_fm_storage_id=ipAddressId)
            unitName = "LVS Router Service FM Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(svc_cm_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(svc_cm_storage_id=ipAddressId)
            unitName = "LVS Router Service CM Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(svc_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(svc_storage_internal_id=ipAddressId)
            unitName = "LVS Router Service Storage Gateway Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(svc_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(svc_storage_id=ipAddressId)
            unitName = "LVS Router Service Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(scp_scp_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(scp_scp_internal_id=ipAddressId)
            unitName = "LVS Router Scripting SCP Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(scp_scp_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(scp_scp_external_id=ipAddressId)
            unitName = "LVS Router Scripting SCP External IPV4 VIP"
        elif LVSRouterVip.objects.filter(scp_scp_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(scp_scp_storage_id=ipAddressId)
            unitName = "LVS Router Scripting SCP Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(scp_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(scp_storage_internal_id=ipAddressId)
            unitName = "LVS Router Scripting Storage Gateway Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(scp_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(scp_storage_id=ipAddressId)
            unitName = "LVS Router Scripting Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(evt_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(evt_storage_internal_id=ipAddressId)
            unitName = "LVS Router Events Storage Gateway Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(evt_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(evt_storage_id=ipAddressId)
            unitName = "LVS Router Events Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(str_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_internal_id=ipAddressId)
            unitName = "LVS Router Streaming STR Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(str_str_internal_2_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_internal_2_id=ipAddressId)
            unitName = "LVS Router Streaming STR Internal IPV4 VIP 2"
        elif LVSRouterVip.objects.filter(str_str_internal_3_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_internal_3_id=ipAddressId)
            unitName = "LVS Router Streaming STR Internal IPV4 VIP 3"
        elif LVSRouterVip.objects.filter(str_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_external_id=ipAddressId)
            unitName = "LVS Router Streaming STR External IPV4 VIP"
        elif LVSRouterVip.objects.filter(str_str_external_2_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_external_2_id=ipAddressId)
            unitName = "LVS Router Streaming STR External IPV4 VIP 2"
        elif LVSRouterVip.objects.filter(str_str_external_3_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_external_3_id=ipAddressId)
            unitName = "LVS Router Streaming STR External IPV4 VIP 3"
        elif LVSRouterVip.objects.filter(str_str_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_storage_id=ipAddressId)
            unitName = "LVS Router Streaming STR Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(str_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_storage_internal_id=ipAddressId)
            unitName = "LVS Router Streaming Storage Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(str_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_storage_id=ipAddressId)
            unitName = "LVS Router Streaming Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(esn_str_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(esn_str_internal_id=ipAddressId)
            unitName = "LVS Router ESN ESN Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(esn_str_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(esn_str_external_id=ipAddressId)
            unitName = "LVS Router ESN ESN External IPV4 VIP"
        elif LVSRouterVip.objects.filter(esn_str_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(esn_str_storage_id=ipAddressId)
            unitName = "LVS Router ESN ESN Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(esn_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(esn_storage_internal_id=ipAddressId)
            unitName = "LVS Router ESN ESN Storage Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(ebs_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(ebs_storage_id=ipAddressId)
            unitName = "LVS Router EBS Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(ebs_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(ebs_storage_internal_id=ipAddressId)
            unitName = "LVS Router EBS Storage Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(asr_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(asr_storage_id=ipAddressId)
            unitName = "LVS Router ASR Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(asr_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(asr_storage_internal_id=ipAddressId)
            unitName = "LVS Router ASR Storage GateWay Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(asr_asr_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(asr_asr_storage_id=ipAddressId)
            unitName = "LVS Router ASR ASR Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(asr_asr_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(asr_asr_internal_id=ipAddressId)
            unitName = "LVS Router ASR ASR Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(asr_asr_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(asr_asr_external_id=ipAddressId)
            unitName = "LVS Router ASR ASR  External IPV4 VIP"
        elif LVSRouterVip.objects.filter(fm_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(fm_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router FM Internal IPV6 VIP"
        elif LVSRouterVip.objects.filter(fm_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(fm_external_ipv6_id=ipAddressId)
            unitName = "LVS Router FM External IPV6 VIP"
        elif LVSRouterVip.objects.filter(cm_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(cm_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router CM Internal IPV6 VIP"
        elif LVSRouterVip.objects.filter(cm_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(cm_external_ipv6_id=ipAddressId)
            unitName = "LVS Router CM External IPV6 VIP"
        elif LVSRouterVip.objects.filter(msossfm_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(msossfm_external_ipv6_id=ipAddressId)
            unitName = "LVS Router MSOSSFM External IPV6 VIP"
        elif LVSRouterVip.objects.filter(msossfm_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(msossfm_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router MSOSSFM Internal IPV6 VIP"
        elif LVSRouterVip.objects.filter(str_str_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router Streaming STR Internal IPV6 VIP"
        elif LVSRouterVip.objects.filter(str_str_internal_ipv6_2_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_internal_ipv6_2_id=ipAddressId)
            unitName = "LVS Router Streaming STR Internal IPV6 VIP 2"
        elif LVSRouterVip.objects.filter(str_str_internal_ipv6_2_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_internal_ipv6_2_id=ipAddressId)
            unitName = "LVS Router Streaming STR Internal IPV6 VIP 3"
        elif LVSRouterVip.objects.filter(str_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_external_ipv6_id=ipAddressId)
            unitName = "LVS Router Streaming STR External IPV6 VIP"
        elif LVSRouterVip.objects.filter(str_str_external_ipv6_2_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_external_ipv6_2_id=ipAddressId)
            unitName = "LVS Router Streaming STR External IPV6 VIP 2"
        elif LVSRouterVip.objects.filter(str_str_external_ipv6_3_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(str_str_external_ipv6_3_id=ipAddressId)
            unitName = "LVS Router Streaming STR External IPV6 VIP 3"
        elif LVSRouterVip.objects.filter(scp_scp_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(scp_scp_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router Scripting SCP Internal IPV6 VIP"
        elif LVSRouterVip.objects.filter(scp_scp_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(scp_scp_external_ipv6_id=ipAddressId)
            unitName = "LVS Router Scripting SCP External IPV6 VIP"
        elif LVSRouterVip.objects.filter(esn_str_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(esn_str_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router ESN ESN Internal IPV6 VIP"
        elif LVSRouterVip.objects.filter(esn_str_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(esn_str_external_ipv6_id=ipAddressId)
            unitName = "LVS Router Streaming STR External IPV6 VIP"
        elif LVSRouterVip.objects.filter(asr_asr_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(asr_asr_external_ipv6_id=ipAddressId)
            unitName = "LVS Router ASR ASR External IPV6 VIP"
        elif LVSRouterVip.objects.filter(eba_storage_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(eba_storage_id=ipAddressId)
            unitName = "LVS Router EBA Storage IPV4 VIP"
        elif LVSRouterVip.objects.filter(eba_storage_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(eba_storage_internal_id=ipAddressId)
            unitName = "LVS Router EBA Storage Internal IPV4 VIP"
        elif LVSRouterVip.objects.filter(ebs_str_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVip.objects.only(clusterValues).values(*clusterValues).get(ebs_str_external_ipv6__id=ipAddressId)
            unitName = "LVS Router EBS STR External IPV6 VIP"
        elif LVSRouterVipExtended.objects.filter(eba_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(eba_external_id=ipAddressId)
            unitName = "LVS Router EBA External IPV4 VIP"
        elif LVSRouterVipExtended.objects.filter(eba_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(eba_external_ipv6_id=ipAddressId)
            unitName = "LVS Router EBA External IPV6 VIP"
        elif LVSRouterVipExtended.objects.filter(eba_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(eba_internal_id=ipAddressId)
            unitName = "LVS Router EBA Internal IPV4 VIP"
        elif LVSRouterVipExtended.objects.filter(eba_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(eba_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router EBA Internal IPV6 VIP"
        elif LVSRouterVipExtended.objects.filter(svc_pm_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(svc_pm_ipv6_id=ipAddressId)
            unitName = "LVS Router PM External IPV6 VIP"
        elif LVSRouterVipExtended.objects.filter(oran_internal_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(oran_internal_id=ipAddressId)
            unitName = "LVS Router ORAN Internal IPV4 VIP"
        elif LVSRouterVipExtended.objects.filter(oran_internal_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(oran_internal_ipv6_id=ipAddressId)
            unitName = "LVS Router ORAN Internal IPV6 VIP"
        elif LVSRouterVipExtended.objects.filter(oran_external_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(oran_external_id=ipAddressId)
            unitName = "LVS Router ORAN External IPV4 VIP"
        elif LVSRouterVipExtended.objects.filter(oran_external_ipv6_id=ipAddressId).exists():
            LVSRouterObj =  LVSRouterVipExtended.objects.only(clusterValues).values(*clusterValues).get(oran_external_ipv6_id=ipAddressId)
            unitName = "LVS Router ORAN External IPV6 VIP"

        if LVSRouterObj != None:
            identifier = LVSRouterObj['cluster__name']
            clusterId = LVSRouterObj['cluster_id']
    elif ipType == "hybridCloud":
        serverType = "Hybrid Cloud"
        unitNumber = "NA"
        hybridCloudObj = None
        if HybridCloud.objects.filter(gateway_internal_id=ipAddressId).exists():
            hybridCloudObj = HybridCloud.objects.only(clusterValues).values(*clusterValues).get(gateway_internal_id=ipAddressId)
            unitName =  "Gateway Private IP IPV4"
        elif HybridCloud.objects.filter(gateway_external_id=ipAddressId).exists():
            hybridCloudObj = HybridCloud.objects.only(clusterValues).values(*clusterValues).get(gateway_external_id=ipAddressId)
            unitName =  "Gateway Public IP IPV4"
        elif HybridCloud.objects.filter(gateway_internal_ipv6_id=ipAddressId).exists():
            hybridCloudObj = HybridCloud.objects.only(clusterValues).values(*clusterValues).get(gateway_internal_ipv6_id=ipAddressId)
            unitName =  "Gateway Private IP IPV6"
        elif HybridCloud.objects.filter(gateway_external_ipv6_id=ipAddressId).exists():
            hybridCloudObj = HybridCloud.objects.only(clusterValues).values(*clusterValues).get(gateway_external_ipv6_id=ipAddressId)
            unitName =  "Gateway Public IP IPV6"
        if hybridCloudObj != None:
            identifier = hybridCloudObj['cluster__name']
            clusterId = hybridCloudObj['cluster_id']
            unitName =  str(serverType) +  " " + str(unitName)
    elif ipType == "dvmsInformation":
        serverType = "Dvms Information"
        unitNumber = "NA"
        dvmsInformationObj = None
        if DvmsInformation.objects.filter(external_ipv4_id=ipAddressId).exists():
            dvmsInformationObj = DvmsInformation.objects.only(clusterValues).values(*clusterValues).get(external_ipv4_id=ipAddressId)
            unitName =  "External IPv4"
        elif DvmsInformation.objects.filter(external_ipv6_id=ipAddressId).exists():
            dvmsInformationObj = DvmsInformation.objects.only(clusterValues).values(*clusterValues).get(external_ipv6_id=ipAddressId)
            unitName =  "External IPv6"
        elif DvmsInformation.objects.filter(internal_ipv4_id=ipAddressId).exists():
            dvmsInformationObj = DvmsInformation.objects.only(clusterValues).values(*clusterValues).get(internal_ipv4_id=ipAddressId)
            unitName =  "Internal IPv4"
        if dvmsInformationObj != None:
            identifier = dvmsInformationObj['cluster__name']
            clusterId = dvmsInformationObj['cluster_id']
            unitName =  str(serverType) +  " " + str(unitName)
    elif ipType == "dataBaseVip":
        serverType = "Database VIP"
        unitNumber = "NA"
        databaseVipObj = None
        if DatabaseVips.objects.filter(postgres_address_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(postgres_address_id=ipAddressId)
            unitName = "Database VIP Postgres Internal IPV4 VIP"
        elif DatabaseVips.objects.filter(versant_address_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(versant_address_id=ipAddressId)
            unitName = "Database VIP Versant Internal IPV4 VIP"
        elif DatabaseVips.objects.filter(mysql_address_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(mysql_address_id=ipAddressId)
            unitName = "Database VIP Mysql Internal IPV4 VIP"
        elif DatabaseVips.objects.filter(opendj_address_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(opendj_address_id=ipAddressId)
            unitName = "Database VIP OpenDj Internal IPV4 VIP"
        elif DatabaseVips.objects.filter(opendj_address2_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(opendj_address2_id=ipAddressId)
            unitName = "Database VIP OpenDj Internal IPV4 VIP2"
        elif DatabaseVips.objects.filter(jms_address_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(jms_address_id=ipAddressId)
            unitName = "Database VIP JMS Internal IPV4 VIP"
        elif DatabaseVips.objects.filter(eSearch_address_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(eSearch_address_id=ipAddressId)
            unitName = "Database VIP Elastic Search Internal IPV4 VIP"
        elif DatabaseVips.objects.filter(neo4j_address1_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(neo4j_address1_id=ipAddressId)
            unitName = "Database VIP NEO4J Internal IPV4 VIP"
        elif DatabaseVips.objects.filter(neo4j_address2_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(neo4j_address2_id=ipAddressId)
            unitName = "Database VIP NEO4J Internal IPV4 VIP2"
        elif DatabaseVips.objects.filter(neo4j_address3_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(neo4j_address3_id=ipAddressId)
            unitName = "Database VIP NEO4J Internal IPV4 VIP3"
        elif DatabaseVips.objects.filter(gossipRouter_address1_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(gossipRouter_address1_id=ipAddressId)
            unitName = "Database VIP Gossip Router Internal IPv4 VIP1"
        elif DatabaseVips.objects.filter(gossipRouter_address2_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(gossipRouter_address2_id=ipAddressId)
            unitName = "Database VIP Gossip Router Internal IPv4 VIP2"
        elif DatabaseVips.objects.filter(eshistory_address_id=ipAddressId).exists():
            databaseVipObj = DatabaseVips.objects.only(clusterValues).values(*clusterValues).get(eshistory_address_id=ipAddressId)
            unitName = "Database VIP Eshistory Internal IPv4 VIP"


        if databaseVipObj != None:
            identifier = databaseVipObj['cluster__name']
            clusterId = databaseVipObj['cluster_id']

    return serverType, identifier, clusterId, unitName, unitNumber, serverId

def searchInventoryServerDetails(serverId,ipType=None):
    '''
    Search Functionality used to get the server information for the views function searchInventory
    '''
    clusterId = None
    serverDetails = None
    serverType = None
    if ipType != "found":
        hostnameValue = ('hostname', )
        if ipType == "san":
            serverType = "SAN Server"
            serverDetails = Storage.objects.only(hostnameValue).values(*hostnameValue).get(id=serverId)
        if ipType == "enclosure":
            serverType = "Enclosure"
            serverDetails = Enclosure.objects.only(hostnameValue).values(*hostnameValue).get(id=serverId)
        if serverDetails != None:
            identifier=serverDetails['hostname']
        else:
            identifier = "Issue with Result"
    else:
        if ClusterServer.objects.filter(server_id=serverId).exists():
            filterValues = ('server__hostname', 'cluster_id')
            serverType = "Deployment Server"
            serverDetails = ClusterServer.objects.only(filterValues).values(*filterValues).get(server_id=serverId)
            clusterId = serverDetails['cluster_id']
        filterValue = ('server__hostname', )
        if ManagementServer.objects.filter(server_id=serverId).exists():
            serverType = "Management Server"
            serverDetails = ManagementServer.objects.only(filterValue).values(*filterValue).get(server_id=serverId)
        if NASServer.objects.filter(server_id=serverId).exists():
            serverType = "NAS Server"
            serverDetails = NASServer.objects.only(filterValue).values(*filterValue).filter(server_id=serverId)[1]
        if serverDetails != None:
            identifier = serverDetails['server__hostname']
        else:
            identifier = "Issue with Result"
    return serverType, identifier, clusterId
