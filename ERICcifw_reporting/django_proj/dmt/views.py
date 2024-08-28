from dmt.models import *
from cireports.models import *
from dmt.cloud import *
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.context_processors import csrf
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.core.management.base import BaseCommand, CommandError
import sys, os, os.path, tempfile, zipfile
from ciconfig import CIConfig
from django.db import connection
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
import os
import datetime
import time
from datetime import datetime, timedelta, date
from distutils.version import LooseVersion
import logging
import commands
logger = logging.getLogger(__name__)
config = CIConfig()
import csv
import dmt.utils
import dmt.uploadContent
import dmt.searchInventory
import dmt.buildconfig
import dmt.cloud
import dmt.mcast
import dmt.virtualMCast
import ast
import subprocess
import json, re
import itertools
from dmt.forms import *
from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from dmt.logUserActivity import logAction, logChange
from django.core.management import call_command
from django.utils.encoding import force_unicode
from guardian.decorators import permission_required, permission_required_or_403
from guardian.conf import settings as guardian_settings
from guardian.exceptions import GuardianError
from django.core.exceptions import ObjectDoesNotExist
from guardian.shortcuts import assign_perm, get_perms, remove_perm
from guardian.core import ObjectPermissionChecker
from fwk.utils import pageHitCounter
from django.views.generic import TemplateView
from django.views.decorators.gzip import gzip_page

def showMgtServers(request, selected=None):
    mgtsvrs = ManagementServer.objects.all()
    clusters = None
    mgtsvr = None
    nic = None
    credentialDetails = None
    allNics = []
    ipaddrs = []
    bladeExtraDetails = None
    iloAddress = None
    iloObj = None
    ipAddressesInfo = {}
    mgmtServCredMaps = []
    if selected is not None:
        serverObj = mgtsvr = None
        try:
            mgtsvr = ManagementServer.objects.get(server__id=selected)
            serverObj = Server.objects.get(id=selected)
        except Exception as e:
            return render_to_response("dmt/dmt_error.html", {'error': "Issue getting the Management Server: " + str(e)})
        allNics += NetworkInterface.objects.filter(server__id=selected)
        try:
            nic = NetworkInterface.objects.get(server__id=selected,interface="eth0")
        except:
            return HttpResponseRedirect("/dmt/editmgtsvr/" + str(selected))
        ipaddrs += IpAddress.objects.filter(nic=nic.id)
        for ip in ipaddrs:
            if ip.ipType == "host":
                ipAddressesInfo['ipv4_host_address'] = ip.address
                ipAddressesInfo['ipv4_host_bitmask'] = ip.bitmask
            if ip.ipType == "ipv6_host":
                ipAddressesInfo['ipv6_host_address'] = ip.ipv6_address
            if ip.ipType == "storage":
                ipAddressesInfo['storage_address'] = ip.address
            if ip.ipType == "backup":
                ipAddressesInfo['backup_address'] = ip.address
            if ip.ipType == "internal":
                ipAddressesInfo['internal_address'] = ip.address
        bladeExtraDetails = BladeHardwareDetails.objects.filter(mac_address=nic)
        if Ilo.objects.filter(server=serverObj).exists():
            iloObj = Ilo.objects.get(server=serverObj)
            iloAddress = iloObj.ipMapIloAddress.address
        else:
            iloAddress = "None"
        if ManagementServerCredentialMapping.objects.filter(mgtServer_id=mgtsvr.id).exists():
            mgmtServCredMaps = list(ManagementServerCredentialMapping.objects.filter(mgtServer_id=mgtsvr.id))
        clusters = Cluster.objects.filter(management_server__server__id=selected)
    else:
        pageHitCounter("ManagementServers", None, str(request.user))
    return render(request, "dmt/mgt_servers.html",
            {
                "mgtservers": mgtsvrs,
                "mgtserver": mgtsvr,
                'nic': nic,
                'ipAddressesInfo': ipAddressesInfo,
                'allNics': allNics,
                "selected": selected,
                "clusters": clusters,
                "mgmtServCredMaps":mgmtServCredMaps,
                "bladeExtraDetails": bladeExtraDetails,
                "ilo": iloObj,
                "iloAddress": iloAddress
            }
         )

def showNASServers(request, selected=None):
    nasSvrsLst = NASServer.objects.values_list('server').distinct()
    nasSvrs = []
    for nasDetails in nasSvrsLst:
        nasSvrs.append(Server.objects.get(id=int(nasDetails[0])))
    clusters = None
    nasSvr = None
    nics = None
    ipaddrs = None
    serverObj = None
    if selected is not None:
        try:
            serverObj = Server.objects.get(id=selected)
        except Exception as e:
            return render_to_response("dmt/dmt_error.html", {'error': "Issue getting the NAS Server: " + str(e)})
        nics = []
        nics += NetworkInterface.objects.filter(server=serverObj)
        ipaddrs = []
        for nic in nics:
            ipaddrs += IpAddress.objects.filter(nic=nic.id)
        clusters = []
        clusters += ClusterToNASMapping.objects.filter(nasServer__server=serverObj)
        clusters += ClusterToDASNASMapping.objects.filter(dasNasServer=serverObj)
    else:
        pageHitCounter("NAS", None, str(request.user))
    return render(request, "dmt/nas_servers.html",
            {
                "nasServers": nasSvrs,
                "server": serverObj,
                'nics': nics,
                'ipaddrs': ipaddrs,
                "selected": selected,
                "clusters": clusters
            }
         )

def showStorageServers(request, selected=None):
    storageSvrs = Storage.objects.all()
    storageSvr = None
    ipOneObject = None
    ipTwoObject = None
    if selected is not None:
        try:
            storageSvr = Storage.objects.get(id=selected)
        except Exception as e:
            return render_to_response("dmt/dmt_error.html", {'error': "Issue getting the Storage Server: " + str(e)})
        if StorageIPMapping.objects.filter(storage=storageSvr.id,ipnumber="1").exists():
            ipIdOneObject = StorageIPMapping.objects.get(storage=storageSvr.id,ipnumber="1")
        else:
            ipIdOneObject = None
        if StorageIPMapping.objects.filter(storage=storageSvr.id,ipnumber="2").exists():
            ipIdTwoObject = StorageIPMapping.objects.get(storage=storageSvr.id,ipnumber="2")
        else:
            ipIdTwoObject = None
        if ipIdOneObject != None:
            ipOneObject = IpAddress.objects.get(id=ipIdOneObject.ipaddr_id)
        else:
            ipOneObject = None
        if ipIdTwoObject != None:
            ipTwoObject = IpAddress.objects.get(id=ipIdTwoObject.ipaddr_id)
        else:
            ipTwoObject = None
    else:
        pageHitCounter("SAN", None, str(request.user))
    clusters = []
    clusters += ClusterToStorageMapping.objects.filter(storage__id=selected)
    clusters += ClusterToDASMapping.objects.filter(storage__id=selected)
    return render(request, "dmt/storage_servers.html",
            {
                "storageServers": storageSvrs,
                "storageServer": storageSvr,
                "ipOneObject" : ipOneObject,
                "ipTwoObject" : ipTwoObject,
                "selected": selected,
                "clusters" : clusters,
            }
         )

def showEnclosureServers(request, selected=None):
    enclosureSvrs = Enclosure.objects.all()
    enclosureSvr = None
    ipOneObject = None
    ipTwoObject = None
    ipThreeObject = None
    ipFourObject = None
    ipFiveObject = None
    ipSixObject = None
    clusters = []
    if selected is not None:
        try:
            enclosureSvr = Enclosure.objects.get(id=selected)
        except Exception as e:
            return render_to_response("dmt/dmt_error.html", {'error': "Issue getting the Enclosure Server: " + str(e)})
        ipIdOneObject = EnclosureIPMapping.objects.get(enclosure=enclosureSvr.id,ipnumber="1")
        ipIdTwoObject = EnclosureIPMapping.objects.get(enclosure=enclosureSvr.id,ipnumber="2")
        ipOneObject = IpAddress.objects.get(id=ipIdOneObject.ipaddr_id)
        ipTwoObject = IpAddress.objects.get(id=ipIdTwoObject.ipaddr_id)
        if EnclosureIPMapping.objects.filter(enclosure=enclosureSvr.id,ipnumber="3").exists():
            ipIdThreeObject = EnclosureIPMapping.objects.get(enclosure=enclosureSvr.id,ipnumber="3")
            ipThreeObject = IpAddress.objects.get(id=ipIdThreeObject.ipaddr_id)
        if EnclosureIPMapping.objects.filter(enclosure=enclosureSvr.id,ipnumber="4").exists():
            ipIdFourObject = EnclosureIPMapping.objects.get(enclosure=enclosureSvr.id,ipnumber="4")
            ipFourObject = IpAddress.objects.get(id=ipIdFourObject.ipaddr_id)
        if EnclosureIPMapping.objects.filter(enclosure=enclosureSvr.id,ipnumber="5").exists():
            ipIdFiveObject = EnclosureIPMapping.objects.get(enclosure=enclosureSvr.id,ipnumber="5")
            ipFiveObject = IpAddress.objects.get(id=ipIdFiveObject.ipaddr_id)
        if EnclosureIPMapping.objects.filter(enclosure=enclosureSvr.id,ipnumber="6").exists():
            ipIdSixObject = EnclosureIPMapping.objects.get(enclosure=enclosureSvr.id,ipnumber="6")
            ipSixObject = IpAddress.objects.get(id=ipIdSixObject.ipaddr_id)
        if BladeHardwareDetails.objects.filter(enclosure=enclosureSvr.id).exists():
            bladeObj = BladeHardwareDetails.objects.filter(enclosure=enclosureSvr.id)
            for bladeItems in bladeObj:
                if ClusterServer.objects.filter(server=bladeItems.mac_address.server.id).exists():
                    clusters += ClusterServer.objects.filter(server=bladeItems.mac_address.server.id)
    else:
        pageHitCounter("Enclosures", None, str(request.user))
    return render(request, "dmt/enclosure_servers.html",
            {
                "enclosureServers": enclosureSvrs,
                "enclosureServer": enclosureSvr,
                "ipOneObject" : ipOneObject,
                "ipTwoObject" : ipTwoObject,
                "ipThreeObject" : ipThreeObject,
                "ipFourObject" : ipFourObject,
                "ipFiveObject" : ipFiveObject,
                "ipSixObject" : ipSixObject,
                "clusters" : clusters,
                "selected": selected,
            }
         )

@gzip_page
def showClusters(request, selected=None, details=None):
    logger.debug(str(request.user))
    user = User.objects.get(username=str(request.user))
    accessGroup = config.get("CIFWK", "adminGroup")
    userPerms = False
    if user.groups.filter(name=accessGroup).exists() or user.is_superuser:
        userPermsAdmin = True
    else:
        userPermsAdmin = False
    if selected != None:
        cluster = None
        try:
            cluster = Cluster.objects.get(id=selected)
        except Exception as e:
            return render_to_response("dmt/dmt_error.html", {'error': "Issue getting the Deployment: " + str(e)})
        try:
            if cluster.group != None:
                if dmt.utils.permissionRequest(request.user, cluster) or user.is_superuser:
                    userPerms = True
                else:
                    userPerms = False
            else:
                userPerms = True
            deployStatus = []
            if DeploymentStatus.objects.filter(cluster=cluster).exists():
                deployStatus = DeploymentStatus.objects.get(cluster=cluster)
            ServicesClr = ServicesCluster.objects.filter(cluster_id=selected)
            mcasts = []
            requiredClusterServerFields = ('id','node_type','active','server__dns_serverA','server__dns_serverB','server__domain_name','server__hardware_type','server__hostname','server__name','server_id')
            clustersvrs = ClusterServer.objects.filter(cluster=cluster).only(requiredClusterServerFields).values(*requiredClusterServerFields)
            serviceGroupPackagesdict = {}
            serviceGroupInfo = []
            virtualImageInfo = []
            pkgList = []
            bladeExtraDetails = []
            clusServCredMaps = []
            credentialsList = []
            clusterMulticast = []
            databaseVip = []
            ossrcClusterObj = ""
            ssoDetails = ""
            databaseLocationObj = ""
            virtualConnectNetworksObj = ""
            vlanTagObj = ""
            dasObject = ""
            dasNasObject = ""
            jbossServiceInstances = None
            jbossInternalServiceInstances = None
            vmServiceIpRange = None
            autoVmServiceDnsIpRange = None
            hybridCloud = []
            vlanMulticast = []
            vlanClusterMulticast = []
            deploymentDescription = []
            deploymentReport = False
            showServicesNodeList = []
            servicesNodeTypeList = str(config.get("DMT", "servicesNodeTypes")).split()
            databaseProvider = []
            clusterAdditionalInformation = []
            dvmsInformation = []
            # Get Service group/service unit data
            # This is depreciated once the KVM is fully released
            if UpdatedDeploymentLog.objects.filter(cluster=cluster).exists():
                deploymentReport = True
            if DDtoDeploymentMapping.objects.filter(cluster=cluster).exists():
                ddMappingFields = ('deployment_description__name', 'deployment_description__version__version', 'deployment_description__dd_type__dd_type', 'deployment_description__capacity_type', 'auto_update', 'update_type', 'iprange_type')
                deploymentDescription = DDtoDeploymentMapping.objects.only(ddMappingFields).values(*ddMappingFields).get(cluster=cluster)
            clusterServerIds = []
            serverIds = []
            for clusterServer in clustersvrs:
                for allowedType in servicesNodeTypeList:
                    if allowedType in str(clusterServer['node_type']):
                        showServicesNodeList.append(str(clusterServer['node_type']))
                clusterServerIds.append(clusterServer['id'])
                serverIds.append(clusterServer['server_id'])
            requiredClusterServerCredentialMappingFields = ('clusterServer_id', 'credentials__username', 'credentials_id', 'credentials__password', 'credentials__credentialType')
            clusServCredMaps = ClusterServerCredentialMapping.objects.filter(clusterServer_id__in=clusterServerIds).only(requiredClusterServerCredentialMappingFields).values(*requiredClusterServerCredentialMappingFields)
            requiredRackHardwareFields = ('serial_number', 'bootdisk_uuid', 'clusterServer_id')
            rackExtraDetails = RackHardwareDetails.objects.filter(clusterServer__cluster=cluster).only(requiredRackHardwareFields).values(*requiredRackHardwareFields)
            for servClr in ServicesClr:
                serviceGroup = ServiceGroup.objects.filter(service_cluster_id=servClr.id)
                mcasts += Multicast.objects.filter(service_cluster_id=servClr.id)
                for obj in serviceGroup:
                    jbossServiceInstances = None
                    jbossInternalServiceInstances = None
                    # TODO: Only get this info if details != none
                    serviceGroupPackagesList = ServiceGroupPackageMapping.objects.filter(serviceGroup=obj.id)
                    pkgList = []
                    for i in serviceGroupPackagesList:
                        pkgList.append(Package.objects.get(name=i.package.name))
                    if ServiceGroupInstanceInternal.objects.filter(service_group=obj).exists():
                        jbossInternalServiceInstances = ServiceGroupInstanceInternal.objects.filter(service_group=obj)
                    #else:
                    if ServiceGroupInstance.objects.filter(service_group=obj).exists():
                        jbossServiceInstances = ServiceGroupInstance.objects.filter(service_group=obj)
                    if ServiceGroupCredentialMapping.objects.filter(service_group=obj).exists():
                        credentialsList = ServiceGroupCredentialMapping.objects.filter(service_group=obj)
                    data = {
                           "sg": obj,
                            "packages": pkgList,
                            "jbossServiceInstances": jbossServiceInstances,
                            "jbossInternalServiceInstances": jbossInternalServiceInstances,
                            "credentialsList": credentialsList,
                            }
                    serviceGroupInfo.append(data)
            # Get related Service Data
            if VlanMulticast.objects.filter(clusterServer__cluster=cluster).exists():
                fields = ('clusterServer__id', 'multicast_type__name', 'multicast_type__description', 'multicast_snooping', 'multicast_querier', 'multicast_router', 'hash_max',)
                vlanMulticast = VlanMulticast.objects.only(fields).values(*fields).filter(clusterServer__cluster=cluster)
            if VlanClusterMulticast.objects.filter(cluster=cluster).exists():
                fields = ('cluster__id', 'multicast_type__name', 'multicast_type__description', 'multicast_snooping', 'multicast_querier', 'multicast_router', 'hash_max',)
                vlanClusterMulticast = VlanClusterMulticast.objects.only(fields).values(*fields).filter(cluster=cluster)
            if HybridCloud.objects.filter(cluster_id=cluster.id).exists():
               hybridCloud += HybridCloud.objects.filter(cluster_id=cluster.id)
            virtualImageInfo = dmt.utils.clusterDetailsVirtualimagedata(cluster.id)
            if ClusterMulticast.objects.filter(cluster_id=cluster.id).exists():
                clusterMulticast += ClusterMulticast.objects.filter(cluster_id=cluster.id)

            requiredDatabaseVipsFields = ('postgres_address__address', 'versant_address__address', 'mysql_address__address', 'opendj_address__address', 'opendj_address2__address', 'jms_address__address', 'eSearch_address__address', 'neo4j_address1__address', 'neo4j_address2__address', 'neo4j_address3__address', 'gossipRouter_address1__address', 'gossipRouter_address2__address', 'eshistory_address__address')
            databaseVip = DatabaseVips.objects.filter(cluster_id=cluster.id).only(requiredDatabaseVipsFields).values(*requiredDatabaseVipsFields)

            requiredLvsrouterVipFields = ("pm_internal__address", "pm_external__address",
                    "fm_internal__address", "fm_external__address", "fm_internal_ipv6__ipv6_address", "fm_external_ipv6__ipv6_address",
                    "cm_internal__address", "cm_external__address", "cm_internal_ipv6__ipv6_address", "cm_external_ipv6__ipv6_address",
                    "svc_pm_storage__address", "svc_fm_storage__address", "svc_cm_storage__address",
                    "svc_storage_internal__address", "svc_storage__address",
                    "scp_scp_internal__address", "scp_scp_external__address", "scp_scp_internal_ipv6__ipv6_address", "scp_scp_external_ipv6__ipv6_address",
                    "scp_scp_storage__address", "scp_storage_internal__address", "scp_storage__address",
                    "evt_storage_internal__address", "evt_storage__address", "str_str_if", "str_internal__address", "str_str_internal_2__address", "str_str_internal_3__address",
                    "str_external__address", "str_str_external_2__address", "str_str_external_3__address",
                    "str_str_internal_ipv6__ipv6_address", "str_str_internal_ipv6_2__ipv6_address", "str_str_internal_ipv6_3__ipv6_address",
                    "str_external_ipv6__ipv6_address", "str_str_external_ipv6_2__ipv6_address", "str_str_external_ipv6_3__ipv6_address",
                    "str_str_storage__address", "str_storage_internal__address", "str_storage__address",
                    "esn_str_if", "esn_str_internal__address", "esn_str_external__address", "esn_str_internal_ipv6__ipv6_address",
                    "esn_str_external_ipv6__ipv6_address", "esn_str_storage__address", "esn_storage_internal__address",
                    "ebs_storage_internal__address", "ebs_storage__address", "ebs_str_external_ipv6__ipv6_address", "asr_storage_internal__address", "asr_asr_external__address",
                    "asr_asr_internal__address", "asr_asr_external_ipv6__ipv6_address", "asr_storage__address","asr_asr_storage__address",
                    "eba_storage_internal__address", "eba_storage__address",
                    "msossfm_internal__address", "msossfm_external__address", "msossfm_internal_ipv6__ipv6_address", "msossfm_external_ipv6__ipv6_address")

            lvsRouterVipExtended = {}
            lvsrouterVip = LVSRouterVip.objects.filter(cluster_id=cluster.id).only(requiredLvsrouterVipFields).values(*requiredLvsrouterVipFields)
            if LVSRouterVipExtended.objects.filter(cluster_id=cluster.id).exists():
                requiredLvsrouterVipExtendedFields = ("eba_external__address", "eba_external_ipv6__ipv6_address", "eba_internal__address", "eba_internal_ipv6__ipv6_address", "svc_pm_ipv6__ipv6_address", "oran_internal__address", "oran_internal_ipv6__ipv6_address", "oran_external__address", "oran_external_ipv6__ipv6_address")
                lvsRouterVipExtended = LVSRouterVipExtended.objects.only(requiredLvsrouterVipExtendedFields).values(*requiredLvsrouterVipExtendedFields).get(cluster_id=cluster.id)
            else:
                lvsRouterVipExtended['eba_external__address'] = None
                lvsRouterVipExtended['eba_external_ipv6__ipv6_address'] = None
                lvsRouterVipExtended['eba_internal__address'] = None
                lvsRouterVipExtended['eba_internal_ipv6__ipv6_address'] = None
                lvsRouterVipExtended['svc_pm_ipv6__ipv6_address'] = None
                lvsRouterVipExtended['oran_internal__address'] = None
                lvsRouterVipExtended['oran_internal_ipv6__ipv6_address'] = None
                lvsRouterVipExtended['oran_external__address'] = None
                lvsRouterVipExtended['oran_external_ipv6__ipv6_address'] = None
            if len(lvsrouterVip) > 0:
                lvsRouterVipExtended.update(lvsrouterVip[0])
                lvsRouterVipExtendedView = [lvsRouterVipExtended]
            else:
                lvsRouterVipExtendedView = lvsrouterVip
            veritas = VeritasCluster.objects.filter(cluster=cluster)
            if OssrcClusterToTorClusterMapping.objects.filter(torCluster=cluster.id).exists():
                ossrcClusterObj = OssrcClusterToTorClusterMapping.objects.filter(torCluster=cluster)

            if SsoDetails.objects.filter(cluster=cluster.id).exists():
                ssoDetails = SsoDetails.objects.filter(cluster=cluster.id)
            if VlanDetails.objects.filter(cluster=cluster.id).exists():
                vlanTagObj =  VlanDetails.objects.filter(cluster=cluster.id)
                if VirtualConnectNetworks.objects.filter(vlanDetails=vlanTagObj).exists():
                    virtualConnectNetworksObj = VirtualConnectNetworks.objects.get(vlanDetails=vlanTagObj)
            if DataBaseLocation.objects.filter(cluster=cluster.id).exists():
                databaseLocationObj = DataBaseLocation.objects.get(cluster=cluster.id)
            if VmServiceIpRange.objects.filter(cluster=cluster.id).exists():
                vmServiceIpRange = VmServiceIpRange.objects.filter(cluster=cluster.id)
            if AutoVmServiceDnsIpRange.objects.filter(cluster=cluster.id).exists():
                autoVmServiceDnsIpRange = AutoVmServiceDnsIpRange.objects.filter(cluster=cluster.id)

            requiredHardwareIdentityFields = ('wwpn', 'ref', 'server__hostname')
            hardwareIdentity = HardwareIdentity.objects.filter(server_id__in=serverIds).only(requiredHardwareIdentityFields).values(*requiredHardwareIdentityFields)

            requiredIloFields = ('username', 'password', 'ipMapIloAddress__address', 'server__hostname')
            ilos = Ilo.objects.filter(server_id__in=serverIds).only(requiredIloFields).values(*requiredIloFields)

            requiredNicFields = ('id', 'interface', 'mac_address', 'server__hostname', 'server__hardware_type')
            allNics = NetworkInterface.objects.filter(server_id__in=serverIds).only(requiredNicFields).values(*requiredNicFields)

            nicIds = []
            for nic in allNics:
                nicIds.append(nic['id'])

            requiredIpAddressFields = ('address', 'nic__mac_address', 'ipType', 'ipv6_address')
            ipaddrs = IpAddress.objects.filter(nic_id__in=nicIds).only(requiredIpAddressFields).values(*requiredIpAddressFields)

            requiredBladeHardwareFields = ('mac_address__mac_address', 'serial_number', 'profile_name', 'enclosure__id', 'enclosure__hostname')
            bladeExtraDetails = BladeHardwareDetails.objects.filter(mac_address_id__in=nicIds).only().values(*requiredBladeHardwareFields)

            user = None
            # viewing
            nasStorageDtlsObj = ""
            if ClusterToDASMapping.objects.filter(cluster=cluster.id).exists():
                dasObject = ClusterToDASMapping.objects.filter(cluster=cluster.id)
            if ClusterToDASNASMapping.objects.filter(cluster=cluster.id).exists():
                dasNasObject = ClusterToDASNASMapping.objects.filter(cluster=cluster.id)
                if NasStorageDetails.objects.filter(cluster=cluster).exists():
                    nasStorageDtlsObj = NasStorageDetails.objects.filter(cluster=cluster)

            # Build up NAS to SAN info if it exists
            clusterToNASMapObj = ""
            NASServerObj = ""
            storageObj = ""
            if ClusterToNASMapping.objects.filter(cluster = cluster.id).exists():
                clusterToNASMapObj = ClusterToNASMapping.objects.get(cluster = cluster.id)
                if NASServer.objects.filter(id = clusterToNASMapObj.nasServer_id).exists():
                    NASObj = NASServer.objects.get(id = clusterToNASMapObj.nasServer_id)
                    if Server.objects.filter(id = NASObj.server_id).exists():
                        NASServerObj = Server.objects.get(id = NASObj.server_id)
                        nasStorageDtlsObj = NasStorageDetails.objects.filter(cluster=cluster)
                        if ClusterToStorageMapping.objects.filter(cluster_id=cluster.id).exists():
                            clusterStorageMapObj = ClusterToStorageMapping.objects.get(cluster_id=cluster.id)
                            storageObj = Storage.objects.get(id=clusterStorageMapObj.storage_id)
            if DeploymentDatabaseProvider.objects.filter(cluster = cluster.id).exists():
                databaseProvider = DeploymentDatabaseProvider.objects.only('dpsPersistenceProvider').values('dpsPersistenceProvider').get(cluster=cluster.id)
            if ClusterAdditionalInformation.objects.filter(cluster__id=cluster.id).exists():
                valuesFields = "ddp_hostname", "cron", "port", "time"
                clusterAdditionalInformation = ClusterAdditionalInformation.objects.only(valuesFields).values(*valuesFields).get(cluster=cluster.id)
            if DvmsInformation.objects.filter(cluster__id=cluster.id).exists():
                valuesDvmsFields = "external_ipv4__address", "external_ipv6__ipv6_address", "internal_ipv4__address"
                dvmsInformation = DvmsInformation.objects.only(valuesDvmsFields).values(*valuesDvmsFields).get(cluster=cluster.id)
            if str(request.user) != "AnonymousUser":
                requestUser = str(request.user)
                user = User.objects.get(username=requestUser)
            deploymentData = {}
            deploymentData['user'] = user
            deploymentData['userPermsAdmin'] = userPermsAdmin
            deploymentData['userPerms'] = userPerms
            deploymentData['cluster'] = cluster
            deploymentData['deployStatus'] = deployStatus
            deploymentData['clustersvrs'] = clustersvrs
            deploymentData['bladeExtraDetails'] = bladeExtraDetails
            deploymentData['allNics'] = allNics
            deploymentData['ipaddrs'] = ipaddrs
            deploymentData['ilos'] =  ilos
            deploymentData['mcasts'] = mcasts
            deploymentData['clusterMulticast'] = clusterMulticast
            deploymentData['databaseVip'] = databaseVip
            deploymentData['ServicesClr'] = ServicesClr
            deploymentData['serviceGroupInfo'] = serviceGroupInfo
            deploymentData['virtualImageInfo'] = virtualImageInfo
            deploymentData['veritas'] = veritas
            deploymentData['dasObject'] = dasObject
            deploymentData['dasNasObject'] =  dasNasObject
            deploymentData['clusterToNASMapObj'] = clusterToNASMapObj
            deploymentData['NASServerObj'] = NASServerObj
            deploymentData['nasStorageDtlsObj'] = nasStorageDtlsObj
            deploymentData['storageObj'] = storageObj
            deploymentData['ossrcClusterObj'] = ossrcClusterObj
            deploymentData['ssoDetails'] = ssoDetails
            deploymentData['vlanTagObj'] = vlanTagObj
            deploymentData['virtualConnectNetworksObj'] = virtualConnectNetworksObj
            deploymentData['databaseLocationObj'] = databaseLocationObj
            deploymentData['hardwareIdentity'] = hardwareIdentity
            deploymentData['vmServiceIpRange'] = vmServiceIpRange
            deploymentData['autoVmServiceDnsIpRange'] = autoVmServiceDnsIpRange
            deploymentData['lvsrouterVip'] = lvsRouterVipExtendedView
            deploymentData['hybridCloud'] = hybridCloud
            deploymentData['vlanMulticast'] = vlanMulticast
            deploymentData['vlanClusterMulticast'] = vlanClusterMulticast
            deploymentData['deploymentDescription'] = deploymentDescription
            deploymentData['deploymentReport'] = deploymentReport
            deploymentData['clusServCredMaps'] = clusServCredMaps
            deploymentData['rackExtraDetails'] = rackExtraDetails
            deploymentData['showServicesNodeList'] = showServicesNodeList
            deploymentData['databaseProvider'] = databaseProvider
            deploymentData['clusterAdditionalInformation'] = clusterAdditionalInformation
            deploymentData['dvmsInformation'] = dvmsInformation
            if details != None or virtualImageInfo !=[] or cluster.layout.id == 1:
                deploymentData['details'] = 'details'
                return render_to_response("dmt/clusters.html", deploymentData)
            else:
                return render_to_response("dmt/clusters.html", deploymentData)
        except Exception as error:
            errMsg =  "There was an issue getting the Deployment Data for ID:" + str(selected) + " - " + str(error)
            logger.error(str(errMsg))
            return render_to_response("dmt/dmt_error.html",{ 'error': str(errMsg) })

    else:
        pageHitCounter("Depolyments", None, str(request.user))
        clusterFields = ('id','name','component__id','component__element','component__product__name','description','layout__name')
        clusters = Cluster.objects.all().only(clusterFields).values(*clusterFields)
        statusFields = ('status__status','cluster__id')
        statuses =  DeploymentStatus.objects.all().only(statusFields).values(*statusFields)

        for cluster in clusters:
            for status in statuses:
                if status['cluster__id'] == cluster['id']:
                    cluster['status'] = status['status__status']
                    break

        return render(request, "dmt/clusters.html", {"clusters": clusters, "userPerms": userPerms})

def changeLog(request, type, id=None):
    '''
    Function used to display the change log per area specified
    '''
    dateSort = request.GET.get("dateSort")
    if not dateSort:
        dateSort = "Week"
    else:
       dateSort = str(dateSort)

    (logs,displayName) = dmt.utils.getChangeLogDetails(type, dateSort, id)
    useHtml = "dmt/changeLog.html"
    return render_to_response (
        useHtml,
        {
            'displayName':displayName,
            'logs':logs,
            'type': type,
            'id': id,
            'dateSort': dateSort,
        }
        , context_instance =  RequestContext(request),
        )

def searchInstallGroup(request, dashboard=None):
    '''
    Function used to show all the clusters assigned to an install group
    '''
    pageHitCounter("DepolymentInstallGroup", None, str(request.user))
    iterator=itertools.count()
    installGroupList = InstallGroup.objects.all()
    installGroupObj = installGroupList
    returnedResults = ClusterToInstallGroupMapping.objects.all()
    if dashboard != None:
        useHtml = "dmt/dashboardInstallGroup.html"
        displayDashBoard = "yes"
        if InstallGroup.objects.filter(id=dashboard).exists():
            installGroupObj = InstallGroup.objects.filter(id=dashboard)
            for item in installGroupObj:
                returnedResults = ClusterToInstallGroupMapping.objects.filter(group=item.id)
        else:
            returnedResults = None
    else:
        displayDashBoard = "no"
        useHtml = "dmt/searchInstallGroup.html"
    # Get the deployment status
    deployStatus = []
    if returnedResults:
        for item in returnedResults:
            if DeploymentStatus.objects.filter(cluster=item.cluster).exists():
                deployStatus += DeploymentStatus.objects.filter(cluster=item.cluster_id)
    return render_to_response (
            useHtml,
            {
                'displayDashBoard':displayDashBoard,
                'iterator':iterator,
                'value':"2",
                'installGroupList':installGroupList,
                'installGroupObj':installGroupObj,
                'deployStatus':deployStatus,
                'results':returnedResults
            }
            , context_instance =  RequestContext(request),
            )

@login_required
def dasType(request,clusterId):
    '''
    function used to declare which poroject this server is used for
    '''
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to register a DAS system to this Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.title = "Choose a Direct Attach storage type"
    fh.button = "Next"
    fh.request = request
    fh.form = DasTypeForm()
    if request.method =='POST':
        dasType = request.POST.get('dasType')
        fh.redirectTarget = "/dmt/addDAS/" + clusterId + "/" + dasType + "/"
        return fh.success()
    else:
        try:
            return fh.display()
        except Exception as e:
            logger.info("Issue loading DAS Type Form, Error thrown: " +str(e))
            return fh.failure()

@login_required
def dataBaseLocation(request,clusterId):
    '''
    function used to store where this deployment will install the databases on
    '''
    cluster = Cluster.objects.get(id=clusterId)
    databaseLocObj, created = DataBaseLocation.objects.get_or_create(cluster_id=cluster.id)
    fh = FormHandle()
    fh.title = "Can the following Database(s) be stored on the VCS Cluster"
    fh.button = "Submit..."
    fh.request = request
    fh.form = DataBaseLocationForm(initial={'versantStandAlone':databaseLocObj.versantStandAlone,'mysqlStandAlone':databaseLocObj.mysqlStandAlone,'postgresStandAlone':databaseLocObj.postgresStandAlone} )
    if request.method =='POST':
        fh.form = DataBaseLocationForm(request.POST)
        versantStandAlone = request.POST.get('versantStandAlone')
        mysqlStandAlone = request.POST.get('mysqlStandAlone')
        postgresStandAlone = request.POST.get('postgresStandAlone')
        fh.redirectTarget = "/dmt/clusters/" + clusterId + "/details/"
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    DataBaseLocation.objects.filter(cluster_id=cluster.id).update(versantStandAlone=versantStandAlone,mysqlStandAlone=mysqlStandAlone,postgresStandAlone=postgresStandAlone)
                    return fh.success()
            except IntegrityError as e:
                message="Failed to save database location options for deployment for " + str(clusterId) + " Exception : " + str(e)
                fh.message=str(message)
                logger.error=str(message)
                return fh.display()
    else:
        try:
            return fh.display()
        except Exception as e:
            logger.error("Issue loading Database location options, Exception: " +str(e))
            return fh.failure()

@login_required
def productType(request,product,serverType):
    '''
    function used to declare which poroject this server is used for
    '''
    fh = FormHandle()
    fh.title = "Choose a Product this " + serverType + " Server is used for"
    fh.button = "Save and Continue"
    fh.button2 = "Cancel"
    fh.request = request
    fh.redirectTarget = "/dmt/mgtsvrs/"
    #serverTypeUnique = getuniqueProducts()
    fh.form = ProductTypeForm()
    if request.method =='POST':
        if "Cancel" in request.POST:
            return fh.success()
        product = request.POST.get('product')
        fh.redirectTarget = "/dmt/addsvr/None/None/" + product + "/"
        return fh.success()
    else:
        try:
            return fh.display()
        except Exception as e:
            logger.info("Issue loading Product Type Form, Error thrown: " +str(e))
            return fh.failure()

@login_required
@transaction.atomic
def addServer(request, cluster_id=None, message=None, productType=None):
    '''
    Add  generic server to the database. If it is associated with
    a deployment, proceed to create a deployment server reference as well.
    '''
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    domainName = config.get('DMT_SERVER', 'domain')
    dns1 = config.get('DMT_SERVER', 'dns1')
    dns2 = config.get('DMT_SERVER', 'dns2')
    fh.form = ServerForm(initial={'domain_name': str(domainName),'dns_serverA':dns1,'dns_serverB':dns2})
    fh.request = request
    fh.button = "Save & Continue ..."
    fh.button2 = "Cancel"
    userId = request.user.pk
    action = "add"
    logObj = None
    if cluster_id != "None":
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Exception as error:
            errMsg = "Issue getting the Deployment Id - " + str(cluster_id) + " : " + str(error)
            return render_to_response("dmt/dmt_error.html", {'error': errMsg})
        cluster_id = str(cluster.id)
        if cluster.group != None:
            if not dmt.utils.permissionRequest(request.user, cluster):
                error = "You do not have permission to add Deployment Server for " + str(cluster.name)
                return render_to_response("dmt/dmt_error.html", {'error': error})
        tipc_address = str(cluster.tipc_address)
        title = "Register a Deployment Server"
        if message == "True":
            fh.message = ("No Nodes Defined for Deployment: '"
                         + str(cluster.name) + "' Please Add Server before Adding Group")
        fh.redirectTarget = "/dmt/clusters/" + str(cluster_id)
    elif productType != "nas":
        title = "Register a Managment Server with the CI Framework for " + productType
        productObj = None
        try:
            productObj = Product.objects.get(name=productType)
        except Exception as error:
            errMsg = "Issue getting the product Type - " + str(productType) + " : " + str(error)
            return render_to_response("dmt/dmt_error.html", {'error': errMsg})
        fh.redirectTarget = "/dmt/mgtsvrs/"
    else:
        title = "Register a Network Attached Storage Server with the CI Framework"
        fh.redirectTarget = "/dmt/nassvrs/"
    fh.title = title

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = ServerForm(request.POST)
        name = request.POST.get('name')
        hardware_type = request.POST.get('hardware_type')
        hostname = request.POST.get('hostname')
        time = datetime.now()
        if "cloud" in hardware_type:
            if cluster_id != "None":
                hostnameIdentifier = cluster_id
            else:
                hostnameIdentifier = time
        else:
            hostnameIdentifier = '1'
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        if fh.form.is_valid():
            message = dmt.utils.hostNameCheck(fh.form.cleaned_data['hostname'])
            if message != "OK":
                fh.message=message
                return fh.display()
            try:
                with transaction.atomic():
                    data = Server.objects.create(name=name,hardware_type=hardware_type,hostname=hostname,hostnameIdentifier=hostnameIdentifier,domain_name=request.POST.get('domain_name'),dns_serverA=request.POST.get('dns_serverA'),dns_serverB=request.POST.get('dns_serverB'))
                    if cluster_id != "None":
                        clusterInfo=ClusterServer(server_id=data.id,cluster_id=cluster_id)
                        clusterInfo.save()
                        if ClusterServer.objects.filter(server_id=data.id,cluster_id=cluster_id).exists():
                            logObj = ClusterServer.objects.get(server_id=data.id,cluster_id=cluster_id)
                    elif productType != "nas":
                        msinfo=ManagementServer(server_id=data.id,product=productObj)
                        msinfo.save()
                        if ManagementServer.objects.filter(server_id=data.id,product=productObj).exists():
                            logObj = ManagementServer.objects.get(server_id=data.id,product=productObj)
                    else:
                        creinfo=Credentials(username='',password='',credentialType='master')
                        creinfo.save()
                        nasinfo=NASServer(server_id=data.id,credentials_id=creinfo.id)
                        nasinfo.save()

                        creinfo=Credentials(username='',password='',credentialType='support')
                        creinfo.save()
                        nasinfo=NASServer(server_id=data.id,credentials_id=creinfo.id)
                        nasinfo.save()
                        if NASServer.objects.filter(server_id=data.id,credentials_id=creinfo.id).exists():
                            logObj = NASServer.objects.get(server_id=data.id,credentials_id=creinfo.id)
                    if logObj != None:
                        message = "Added Server Configuration (Stage 1)"
                        logAction(userId, logObj, action, message)
                    else:
                        logger.error("There was an issue adding the logging infomation for activities within the addServer function")
            except IntegrityError as e:
                fh.message="Failed to Update the Management Server DB " + str(e)
                return fh.display()
            try:
                try:
                    serv = Server.objects.get(hostname=hostname,hostnameIdentifier=hostnameIdentifier)
                except Exception as error:
                    errMsg = "Issue getting the Server with hostname - " + str(hostname)  + " and hostnameIdentifier - " + str(hostnameIdentifier) + " : " + str(error)
                    return render_to_response("dmt/dmt_error.html", {'error': errMsg})

                if hardware_type == "virtual" and cluster_id != "None":
                    try:
                        # Do not redirect to MAC Address form (auto populate it and move on to adding IP information)
                        try:
                            macAdd = autoAddNetworkInterface(request, serv, cluster_id)
                        except Exception as e:
                            logger.error("Virtual with Deployment unable to auto add Network Interface:" +str(e))
                        # Redirect to attachClsServer
                        fh.redirectTarget = "/dmt/attachClsServer/" + str(serv.id) + "/" + str(cluster_id)
                    except Exception as e:
                        logger.error("Virtual with Deployment ID Redirect Error: " +str(e))
                else:
                    if cluster_id != "None":
                        try:
                            # Redirect to attachClusterServer
                            fh.redirectTarget = "/dmt/attachClsServer/" + str(serv.id) + "/" + str(cluster_id)
                        except Exception as e:
                            logger.error("Issue with Deployment redirect: " +str(e))
                    elif productType != "nas":
                        try:
                            # Redirect to MAC Address form for a Management Server
                            fh.redirectTarget = "/dmt/editmgtsvr/" + str(serv.id)
                        except Exception as e:
                            logger.error("Issue when type is not equal to NAS redirect: " +str(e))
                    else:
                        try:
                            # Do not redirect to MAC Address form (auto populate it and move on to adding IP information)
                            try:
                                macAdd = autoAddNetworkInterface(request, serv)
                            except Exception as e:
                                logger.error("Nas unable to auto add Network Interface:" +str(e))
                            fh.redirectTarget = "/dmt/editnassvr/" + str(serv.id) + "/add"
                        except Exception as e:
                            logger.error("Issue with else redirect: " +str(e))
            except Exception as e:
                logger.error("There was an issue getting redirect whils't added LMS, error thrown : " +str(e))
                return 1

            return fh.success()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def attachClusterServer(request, server_id, cluster_id, editNodeType=None):
    '''
    Create a server associated with a deployment
    '''
    userId = request.user.pk
    if editNodeType == "edit":
        action = editNodeType
        if ClusterServer.objects.filter(cluster_id=cluster_id, server__id=server_id).exists():
            clusterServerNode = ClusterServer.objects.only('node_type').get(cluster_id=cluster_id, server__id=server_id).node_type
        else:
            clusterServerNode = ""
    else:
        action = "add"
    cluster = Cluster.objects.get(id=cluster_id)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to edit the node type for Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    server = Server.objects.get(id=server_id)

    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.title = "Adding Deployment Server Information"
    fh.request = request
    nodeList = []
    productType = cluster.management_server.product.name
    layout = cluster.layout
    nodeList = dmt.utils.getServerTypes(productType, layout)
    if editNodeType == "edit":
        if clusterServerNode != "":
            fh.form = ClusterServerForm(nodeList, initial={'node_type' : clusterServerNode,})
        else:
            fh.form = ClusterServerForm(nodeList)
    else:
        fh.form = ClusterServerForm(nodeList)
    fh.button = "Save & Continue ..."
    fh.button2 = "Cancel"

    if request.method == 'POST':
        fh.redirectTarget = "/dmt/clusters/" + str(cluster_id)
        if "Cancel" in request.POST:
            return fh.success()

        fh.form = ClusterServerForm(nodeList,request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        try:
            if fh.form.is_valid():
                nodeType = str(request.POST.get("node_type"))
                if not nodeType == 'NETSIM':
                    if ClusterServer.objects.filter(cluster=cluster, node_type=nodeType):
                       fh.message = ("Node Type: " + nodeType + ", On Deployment: " +str(cluster.name)+ " is already defined, please try again")
                       return fh.display()
                # Redirect to updateClusterServer form
                if editNodeType != None:
                    fh.redirectTarget = "/dmt/clusters/" + str(cluster_id)
                else:
                    fh.redirectTarget = "/dmt/editserver/" + str(cluster_id) + "/" + str(server.id) + "/add"
                try:
                    with transaction.atomic():
                        cs = fh.form.save(commit=False)
                        existing = ClusterServer.objects.get(server_id=server_id, cluster_id=cluster_id)
                        cs.server = server
                        cs.cluster = cluster
                        cs.id=existing.id
                        cs.save()
                        if action == "edit":
                            if VirtualImage.objects.filter(node_list = clusterServerNode, cluster = cluster_id).exists():
                                virtualImageNames = VirtualImage.objects.filter(node_list = clusterServerNode, cluster = cluster_id).values_list("name", flat=True)
                                for vmName in virtualImageNames:
                                    returnedValueVM,VmMessage = dmt.utils.deleteVirtualImage(cluster_id, vmName)
                            message = "Edited Deployment Node Type was \"" + str(clusterServerNode) + "\" now \"" + str(nodeType) + "\""
                        else:
                            message = "Added Deployment Server Configuration (Stage 2)"
                        logAction(userId, existing, action, message)
                        return fh.success()
                except IntegrityError:
                    return fh.failure()
            else:
                fh.message = "Form is invalid please try again!!!"
                return fh.display()
        except Exception as e:
            fh.message = "Issue with the Node List " + str(e)
            return fh.display()
    else:
        return fh.display()

@login_required
@transaction.atomic
def autoAddNetworkInterface(request, server, cluster_id=None):
    '''
    Automatically add a network interface to a server
    Request object required to check if user has access to use this function
    '''
    try:
        with transaction.atomic():
            networkObject, created = NetworkInterface.objects.get_or_create(server=server)
            networkObject.mac_address = dmt.utils.getLowestAvailableMacAddress(cluster_id)
            networkObject.server = server
            networkObject.save()
    except IntegrityError as e:
        # Delete newly created NIC Object
        dmt.utils.handlingError(str(e))

@login_required
@transaction.atomic
def addSsoInfo(request,clusterId):
    '''
    Used to gather the SSO Extra information for an OSSRC System
    '''
    userId = request.user.pk
    action = "add"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to register LDAP and password details for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh = FormHandle()
    fh.title = "Register Extra Information"
    fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/"
    fh.button = "Finish"
    ossFsServer = None
    citrixFarm = "MASTERSERVICE"
    fh.request = request
    if clusterObj.layout.id != 3:
        fh.form = SsoLdapDetailsForm()
    else:
       fh.form = SsoDetailsForm(initial={'citrixFarm' : "MASTERSERVICE",})
    if request.method =='POST':
        if clusterObj.layout.id != 3:
            fh.form = SsoLdapDetailsForm(request.POST)
        else:
            fh.form = SsoDetailsForm(request.POST)
        if fh.form.is_valid():
            ldapDomain = request.POST.get('ldapDomain')
            ldapPassword = request.POST.get('ldapPassword')
            if clusterObj.layout.id != 3:
                opendjAdminPassword = request.POST.get('opendjAdminPassword')
                openidmAdminPassword = request.POST.get('openidmAdminPassword')
                openidmMysqlPassword = request.POST.get('openidmMysqlPassword')
                securityAdminPassword = request.POST.get('securityAdminPassword')
                hqDatabasePassword = request.POST.get('hqDatabasePassword')
                brsadmPassword = request.POST.get('brsadmPassword')
            if clusterObj.layout.id == 3:
                ossFsServer = request.POST.get('ossFsServer')
                citrixFarm = request.POST.get('citrixFarm')
                brsadmPassword = request.POST.get('brsadmPassword')
            #Check if Domain is unique if not tell user
            try:
                if SsoDetails.objects.filter(cluster=clusterObj).exists():
                    logger.info("Extra Info already registered for this deployment: " +str(clusterObj.name))
                    fh.message = ("Extra Info already registered for this deployment: " +str(clusterObj.name))
                    return fh.display()
                else:
                    with transaction.atomic():
                        if clusterObj.layout.id != 3:
                            ssoInfoObj = SsoDetails.objects.create(cluster=clusterObj,ldapDomain=ldapDomain,ldapPassword=ldapPassword,openidmAdminPassword=openidmAdminPassword,openidmMysqlPassword=openidmMysqlPassword,securityAdminPassword=securityAdminPassword,ossFsServer=ossFsServer,citrixFarm=citrixFarm,opendjAdminPassword=opendjAdminPassword,hqDatabasePassword=hqDatabasePassword,brsadm_password=brsadmPassword)
                        else:
                            ssoInfoObj = SsoDetails.objects.create(cluster=clusterObj,ldapDomain=ldapDomain,ldapPassword=ldapPassword,ossFsServer=ossFsServer,citrixFarm=citrixFarm,brsadm_password=brsadmPassword)
                        message = "Added Extra SSO Information"
                        logAction(userId, clusterObj, action, message)
                        return fh.success()
            except IntegrityError as e:
                logger.error("Extra info not added: " +str(e))
                fh.message = ("Extra info not added: " +str(e))
                return fh.display()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addStorageDetails(request):
    '''
    The AddStorageDetails function is used to add details of the storage to allow full NAS to SAN set up
    '''
    userId = request.user.pk
    action = "add"
    fh = FormHandle()
    fh.title = "Register Network Attached Storage Information"
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    domainName = config.get('DMT_SERVER', 'domain')
    fh.form = MultipleIpForm(initial={'domain_name': str(domainName)})
    fh.request = request
    fh.redirectTarget = "/dmt/storage/"
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        for key,value in request.POST.items():
            if key != 'sanAdminPassword' and key != 'sanServicePassword':
                if value == "":
                    fh.message = ("Please Ensure all fields are filled in before attempting to Register")
                    return fh.failure()
        #Get form values from request
        name = request.POST.get('name')
        hostname = request.POST.get('hostname')
        vnxType = request.POST.get('vnxType')
        domain_name = request.POST.get('domain_name')
        serial_number = request.POST.get('serial_number')
        username = request.POST.get('username')
        password = request.POST.get('password')
        ip1 = request.POST.get('IpAddress1')
        ip2 = request.POST.get('IpAddress2')
        sanAdminPassword = request.POST.get('sanAdminPassword')
        sanServicePassword = request.POST.get('sanServicePassword')
        #Check if hostname is unique if not tell user so
        storageObj = Storage.objects.filter(hostname=hostname)
        if storageObj:
            fh.message = ("SAN hostname: " +str(hostname)+ " is already registered, please try again")
            return fh.display()
        #Check if IP's are unique if not tell user so
        ipList = [ip1,ip2]
        try:
            for ip in ipList:
                ipAddressObj = IpAddress.objects.filter(address=ip,ipv4UniqueIdentifier="1")
                if ipAddressObj:
                    fh.message = ("IPaddress: " + str(ip) + " is already registered, please try again")
                    return fh.display()
            addressList = filter(None,[ip1,ip2])
            duplicates = dmt.utils.getDuplicatesInList(addressList)
            if len(duplicates) > 0:
                fh.message = "Duplicate IP Address: " + str(duplicates[0]) + ", please try again"
                return fh.display()
        except Exception as e:
            logger.error("Issue saving IP details to db: " + str(e))
            return fh.failure()
        try:
            with transaction.atomic():
                #Create IP addresses of Storage in IPAddress Table
                ipaddr1 = IpAddress.objects.create(address=ip1,ipType="san")
                ipaddr2 = IpAddress.objects.create(address=ip2,ipType="san")
                #Create Storage Credentials
                credentials = Credentials.objects.create(username=username, password=password, credentialType="admin", loginScope="global")
                #Create Entry for Storage
                storage = Storage.objects.create(name=name,hostname=hostname,domain_name=domain_name,credentials=credentials,vnxType=vnxType,serial_number=serial_number,sanAdminPassword=sanAdminPassword,sanServicePassword=sanServicePassword)
                #Add mapping of Clraiion ip addresses to ipaddress table entry
                map1 = StorageIPMapping.objects.create(storage=storage, ipaddr=ipaddr1, ipnumber=1)
                map2 = StorageIPMapping.objects.create(storage=storage, ipaddr=ipaddr2, ipnumber=2)
                message = "Added Network Attached Storage Information"
                logAction(userId, storage, action, message)
                return fh.success()
        except IntegrityError as e:
            message = "Issue adding storage details to database: " +str(e)
            logger.error(message)
            fh.message = message
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addEnclosureDetails(request):
    '''
    The addEnclosureDetails function is used to add details of the blade enclosure to be added to db
    When adding a blade the blade needs to be associated with an enclosure
    '''
    userId = request.user.pk
    action = "add"
    vcCredentialsObj = None
    vcUsername = None
    vcPassword = None
    vcIp1 = None
    vcIp2 = None
    fh = FormHandle()
    fh.title = "Register On-Board Admin and Virtual Connect info for Blade Enclosure"
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    domainName = config.get('DMT_SERVER', 'domain')
    fh.form = EnclosureMultipleIpForm(initial={'domain_name': str(domainName)})
    fh.request = request
    fh.redirectTarget = "/dmt/enclosure/"
    if request.method == 'POST':
        fh.form = EnclosureMultipleIpForm(request.POST)
        if "Cancel" in request.POST:
            return fh.success()
        if fh.form.is_valid():
            hostname = request.POST.get('hostname')
            domain_name = request.POST.get('domain_name')
            vc_domain_name = request.POST.get('vc_domain_name')
            rackName = request.POST.get('rackName')
            name = request.POST.get('name')
            username = request.POST.get('username')
            password = request.POST.get('password')
            ip1 = request.POST.get('IpAddress1')
            ip2 = request.POST.get('IpAddress2')
            vcUsername = request.POST.get('vcUsername')
            vcPassword = request.POST.get('vcPassword')
            vcIp1 = request.POST.get('vcIpAddress1')
            vcIp2 = request.POST.get('vcIpAddress2')
            sanSwUsername = request.POST.get('sanSwUsername')
            sanSwPassword = request.POST.get('sanSwPassword')
            sanSwIp1 = request.POST.get('sanSwIpAddress1')
            sanSwIp2 = request.POST.get('sanSwIpAddress2')
            uplink_A_port1 = request.POST.get('uplink_A_port1')
            uplink_A_port2 = request.POST.get('uplink_A_port2')
            uplink_B_port1 = request.POST.get('uplink_B_port1')
            uplink_B_port2 = request.POST.get('uplink_B_port2')
            san_sw_bay_1 = request.POST.get('san_sw_bay_1')
            san_sw_bay_2 = request.POST.get('san_sw_bay_2')
            vc_module_bay_1 = request.POST.get('vc_module_bay_1')
            vc_module_bay_2 = request.POST.get('vc_module_bay_2')

            #Check if hostname is unique if not tell user so
            enclosureObj = Enclosure.objects.filter(hostname=hostname)
            if enclosureObj:
                message = "Enclosure hostname: " +str(hostname)+ " is already registered, please try again"
                fh.message = (message)
                return fh.display()
            #Check if IP's are unique if not tell user so
            ipList = [ip1,ip2,vcIp1,vcIp2,sanSwIp1,sanSwIp2]
            try:
                for ip in ipList:
                    ipAddressObj = IpAddress.objects.filter(address=ip,ipv4UniqueIdentifier="1")
                    if ipAddressObj:
                        fh.message = ("IPaddress: " + str(ip) + " is already registered, please try again")
                        return fh.display()
            except Exception as e:
                message = "Issue saving IP details to db: " + str(e)
                logger.error(message)
                fh.message(message)
                return fh.failure()
            try:
                with transaction.atomic():
                    returnedValue,message = dmt.utils.addEnclosure(hostname,domain_name,vc_domain_name,username,password,ip1,ip2,vcUsername,vcPassword,vcIp1,vcIp2,sanSwUsername,sanSwPassword,sanSwIp1,sanSwIp2,uplink_A_port1,uplink_A_port2,uplink_B_port1,uplink_B_port2,rackName,name,san_sw_bay_1,san_sw_bay_2,vc_module_bay_1,vc_module_bay_2)
                    if returnedValue == "1":
                        fh.message = "Error: " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        message = "Added Enclosure Information"
                        enclosureObj = Enclosure.objects.get(hostname=hostname)
                        logAction(userId, enclosureObj, action, message)
                    return fh.success()
            except IntegrityError as e:
                message = "Issue adding enclosure details to db: " +str(e)
                logger.error(message)
                fh.message = message
                return fh.display()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addExtraNasStorageDetails(request,clusterId):
    '''
    The addExtraNasStorageDetails function is used to add the Nas storage pool name created by the user.
    '''
    userId = request.user.pk
    action = "add"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)

    fh.title = "Register Extra NAS Storage Details for DAS Configuration"
    fh.button = "Finish"
    fh.button2 = "Cancel"
    fh.request = request
    fh.form = NasStorageDetailsForm()
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method =='POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = NasStorageDetailsForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    NasStorageDetails = fh.form.save(commit=False)
                    NasStorageDetails.poolFS1 = request.POST.get('poolFS1')
                    NasStorageDetails.cluster_id = str(clusterObj.id)
                    NasStorageDetails.save()
                    message = "Added NAS Storage Details (DAS - Stage 2)"
                    logAction(userId, clusterObj, action, message)
                    return fh.success()
            except IntegrityError as e:
                logger.error("Issue adding NAS Extra info to DB: " +str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addNasStorageDetailsTor(request,clusterId):
    '''
    The addNasStorageDetailsTor function is used to add the Nas storage pool name created by the user and
    define what the user want to call the shared storage areas for Tor
    '''
    userId = request.user.pk
    action = "add"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    isRackDeployment = dmt.utils.isEnmRackDeployment(clusterObj.enmDeploymentType)

    fh.title = "Register NAS Storage Details"
    fh.button = "Finish"
    fh.button2 = "Cancel"
    fh.request = request
    fh.form = NasStorageDetailsFormTorOnRack() if isRackDeployment else NasStorageDetailsFormTor()
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method =='POST':
        if "Cancel" in request.POST:
            return fh.success()
        if dmt.models.NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
            return fh.success()
        fh.form = NasStorageDetailsFormTorOnRack(request.POST) if isRackDeployment else NasStorageDetailsFormTor(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    NasStorageDetails = fh.form.save(commit=False)
                    NasStorageDetails.sanPoolName = request.POST.get('sanPoolName')
                    NasStorageDetails.sanPoolId = request.POST.get('sanPoolId')
                    NasStorageDetails.sanRaidGroup = request.POST.get('sanRaidGroup')
                    NasStorageDetails.poolFS1 = request.POST.get('poolFS1')
                    NasStorageDetails.fileSystem1 = request.POST.get('fileSystem1')
                    NasStorageDetails.fileSystem2 = request.POST.get('fileSystem2')
                    NasStorageDetails.fileSystem3 = request.POST.get('fileSystem3')
                    NasStorageDetails.nasType = request.POST.get('nasType')
                    NasStorageDetails.nasNdmpPassword = request.POST.get('nasNdmpPassword')
                    NasStorageDetails.nasServerPrefix = request.POST.get('nasServerPrefix')
                    NasStorageDetails.fcSwitches = dmt.utils.convertStrToBool(request.POST.get('fcSwitches'))
                    NasStorageDetails.nasEthernetPorts = request.POST.get('nasEthernetPorts', "")
                    NasStorageDetails.sanPoolDiskCount = request.POST.get('sanPoolDiskCount', 0)
                    NasStorageDetails.cluster_id = str(clusterObj.id)
                    NasStorageDetails.save()
                    message = "Added SAN/NAS Information (Stage 2 Register Storage Details)"
                    logAction(userId, clusterObj, action, message)
                    return fh.success()
            except IntegrityError as e:
                logger.error("Issue adding NAS Extra info to DB: " +str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        if dmt.models.NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
            message = "Storage Already mapped to Cluster"
            logger.error(message)
            fh.message = message
            return fh.display()
        else:
            return fh.display()

@login_required
@transaction.atomic
def addNasStorageDetailsOSS(request,clusterId):
    '''
    The addNasStorageDetailsOSS function is used to add the Nas storage pool name created by the user and
    define what the user want to call the shared storage areas for OSS
    '''
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    isRackDeployment = dmt.utils.isEnmRackDeployment(clusterObj.enmDeploymentType)

    fh.title = "Register NAS Storage Details"
    fh.button = "Finish"
    fh.request = request
    fh.form = NasStorageDetailsFormOSSOnRack() if isRackDeployment else NasStorageDetailsFormOSS()
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method =='POST':
        fh.form = NasStorageDetailsFormOSSOnRack(request.POST) if isRackDeployment else NasStorageDetailsFormOSS(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    NasStorageDetails = fh.form.save(commit=False)
                    NasStorageDetails.sanPoolName = request.POST.get('sanPoolName')
                    NasStorageDetails.sanPoolId = request.POST.get('sanPoolId')
                    NasStorageDetails.poolFS1 = request.POST.get('poolFS1')
                    NasStorageDetails.fileSystem1 = request.POST.get('fileSystem1')
                    NasStorageDetails.poolFS2 = request.POST.get('poolFS2')
                    NasStorageDetails.fileSystem2 = request.POST.get('fileSystem2')
                    NasStorageDetails.poolFS3 = request.POST.get('poolFS3')
                    NasStorageDetails.fileSystem3 = request.POST.get('fileSystem3')
                    NasStorageDetails.nasType = request.POST.get('nasType')
                    NasStorageDetails.nasNdmpPassword = request.POST.get('nasNdmpPassword')
                    NasStorageDetails.nasServerPrefix = request.POST.get('nasServerPrefix')
                    NasStorageDetails.fcSwitches = dmt.utils.convertStrToBool(request.POST.get('fcSwitches'))
                    NasStorageDetails.nasEthernetPorts = request.POST.get('nasEthernetPorts')
                    NasStorageDetails.sanPoolDiskCount = request.POST.get('sanPoolDiskCount')
                    NasStorageDetails.cluster_id = str(clusterObj.id)
                    NasStorageDetails.save()
                    return fh.success()
            except IntegrityError as e:
                logger.error("Issue adding NAS Extra info to DB: " +str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addStorageAttachedNetwork(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "add"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to add Storage Attached Network for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh.title = "Register Network Attached Storage Information for Deployment: " +str(clusterObj.name)
    fh.button = "Next..."
    fh.form = SANForm()
    fh.request = request
    if str(clusterObj.layout.id) != 3:
        fh.redirectTarget = "/dmt/" +str(clusterObj.id)+ "/nasStorage/details/Tor/"
    else:
        fh.redirectTarget = "/dmt/" +str(clusterObj.id)+ "/nasStorage/details/OSS/"
    if request.method == 'POST':
        nasServer = request.POST.get("nasServer")
        nasServer = str(nasServer).split("(id: ")
        nasServer = nasServer[1]
        nasServer = nasServer.replace(')','')
        nasServerObject = Server.objects.get(id=nasServer)
        nasObject = NASServer.objects.filter(server=nasServerObject)[0]

        storage = request.POST.get("storage")
        storageObj = Storage.objects.get(hostname=storage)
        try:
            with transaction.atomic():
                if ClusterToNASMapping.objects.filter(cluster=clusterObj,nasServer=nasObject).exists():
                    logger.info("Deployment to NAS Mapping already exists")
                else:
                    nastoClusterMapping = ClusterToNASMapping.objects.create(cluster=clusterObj,nasServer=nasObject)
                if ClusterToStorageMapping.objects.filter(cluster=clusterObj,storage=storageObj).exists():
                    logger.info("Deployment to Storage Mapping Already exists")
                else:
                    clustertoStorageMapping = ClusterToStorageMapping.objects.create(cluster=clusterObj,storage=storageObj)
                message = "Added SAN/NAS Information (Stage 1)"
                logAction(userId, clusterObj, action, message)
                return fh.success()
        except IntegrityError as e:
            logger.error("Unable to update NAS to Deployment and NAS to Storage Mapping Tables: " +str(e))
            return fh.failure()
    else:
        if ClusterToNASMapping.objects.filter(cluster=clusterObj).exists():
            message = "Storage Already mapped to Cluster"
            logger.error(message)
            fh.message = message
            return fh.display()
        return fh.display()

@login_required
def editStorageAttachedNetworkTor(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "edit"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    isRackDeployment = dmt.utils.isEnmRackDeployment(clusterObj.enmDeploymentType)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Delete Service Group for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh.title = "Edit Network Attached Storage Information: " +str(clusterObj.name)
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    if ClusterToNASMapping.objects.filter(cluster=clusterObj.id).exists():
        clusterNASMapObj = ClusterToNASMapping.objects.get(cluster=clusterObj.id)
        clustetToSanMapObj = ClusterToStorageMapping.objects.get(cluster_id=clusterId)
        nasStorageDtlsObj = sanPoolName = sanPoolId = sanRaidGroup = poolFS1 = fileSystem1 = ""
        fileSystem2 = fileSystem3 = nasType = nasNdmpPassword = nasServerPrefix = fcSwitches = ""
        nasEthernetPorts = sanPoolDiskCount = ""
        if NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
            nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=clusterObj.id)
            sanPoolName = nasStorageDtlsObj.sanPoolName
            sanPoolId = nasStorageDtlsObj.sanPoolId
            sanRaidGroup = nasStorageDtlsObj.sanRaidGroup
            poolFS1 =  nasStorageDtlsObj.poolFS1
            fileSystem1 = nasStorageDtlsObj.fileSystem1
            fileSystem2 = nasStorageDtlsObj.fileSystem2
            fileSystem3 = nasStorageDtlsObj.fileSystem3
            nasType = nasStorageDtlsObj.nasType
            nasNdmpPassword = nasStorageDtlsObj.nasNdmpPassword
            nasServerPrefix = nasStorageDtlsObj.nasServerPrefix
            fcSwitches = nasStorageDtlsObj.fcSwitches
            nasEthernetPorts = nasStorageDtlsObj.nasEthernetPorts
            sanPoolDiskCount = nasStorageDtlsObj.sanPoolDiskCount
        fh.form = EditSanFormTor(
                initial={
                    'storage' : clustetToSanMapObj.storage,
                    'nasServer' : clusterNASMapObj.nasServer,
                    'sanPoolName' : sanPoolName,
                    'sanPoolId' : sanPoolId,
                    'sanRaidGroup' : sanRaidGroup,
                    'poolFS1' : poolFS1,
                    'fileSystem1' : fileSystem1,
                    'fileSystem2' : fileSystem2,
                    'fileSystem3' : fileSystem3,
                    'nasType': nasType,
                    'nasNdmpPassword': nasNdmpPassword,
                    'nasServerPrefix': nasServerPrefix
                    })
        # Create a list of the old Values
        oldValues = [str(clustetToSanMapObj.storage) + "##SAN Details" ,str(clusterNASMapObj.nasServer) + "##NAS Details",str(sanPoolName) + "##SAN Pool Name",str(sanPoolId) + "##SAN Pool Id",str(sanRaidGroup) + "##SAN Raid Group",str(poolFS1) + "##NAS Pool Name",str(fileSystem1) + "##NAS Admin FS",str(fileSystem2) + "##NAS OBServer FS",str(fileSystem3) + "##NAS Cluster FS",str(nasType) + "##NAS Type",str(nasNdmpPassword) + "##NAS Ndmp Password",str(nasServerPrefix) + "##NAS Server Prefix"]
        if isRackDeployment:
            oldValues.append(str(fcSwitches) + "##FC Switches" + str(nasEthernetPorts) + "##NAS Ethernet Ports" + str(sanPoolDiskCount) + "##SAN Pool Disk Count")
            fh.form = EditSanFormTorOnRack(initial = fh.form.initial)
            fh.form.initial['fcSwitches'] = fcSwitches
            fh.form.initial['nasEthernetPorts'] = nasEthernetPorts
            fh.form.initial['sanPoolDiskCount'] = sanPoolDiskCount
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        storage = request.POST.get("storage")
        nas = request.POST.get("nasServer")
        nas = str(nas).split("(id: ")
        nas = nas[1]
        nas = nas.replace(')','')
        storageObj = Storage.objects.get(hostname=storage)
        serverObj = Server.objects.get(id=nas)
        nasObj = NASServer.objects.filter(server=serverObj)[0]
        sanPoolName = request.POST.get("sanPoolName")
        sanPoolId = request.POST.get("sanPoolId")
        sanRaidGroup = request.POST.get("sanRaidGroup")
        poolFS1 = request.POST.get("poolFS1")
        fileSystem1 = request.POST.get("fileSystem1")
        fileSystem2 = request.POST.get("fileSystem2")
        fileSystem3 = request.POST.get("fileSystem3")
        nasType = request.POST.get("nasType")

        if nasType == "unityxt" and clusterNASMapObj.nasServer.server.hardware_type == "rack":
            nasNdmpPassword = request.POST.get("nasNdmpPassword")
            nasServerPrefix = request.POST.get("nasServerPrefix")
        else:
            nasNdmpPassword = nasServerPrefix = ""
        # Create a list of the new values
        newValues = [str(storage),str(request.POST.get("nasServer")),str(sanPoolName),str(sanPoolId),str(sanRaidGroup),str(poolFS1),str(fileSystem1),str(fileSystem2),str(fileSystem3),str(nasType),str(nasNdmpPassword),str(nasServerPrefix)]
        if isRackDeployment:
            newValues.append(str(fcSwitches))
            newValues.append(str(nasEthernetPorts))
            newValues.append(str(sanPoolDiskCount))
            fcSwitches = dmt.utils.convertStrToBool(request.POST.get("fcSwitches"))
            nasEthernetPorts = request.POST.get("nasEthernetPorts")
            sanPoolDiskCount = request.POST.get("sanPoolDiskCount")
            fh.form = EditSanFormTorOnRack(request.POST)
        else:
            fh.form = EditSanFormTor(request.POST)
        changedContent = logChange(oldValues,newValues)
        if fh.form.is_valid():
            try:
                try:
                    nastoClusterMapping = ClusterToNASMapping.objects.filter(cluster=clusterObj).update(nasServer=nasObj)
                except Exception as e:
                    logger.error("Unable to edit SAN Server " +str(e))
                    fh.message = "Unable to edit SAN Server"
                    return fh.display()
                try:
                    storagetoClusterMapping = ClusterToStorageMapping.objects.filter(cluster=clusterObj).update(storage=storageObj)
                except Exception as e:
                    logger.error("Unable to edit SAN Storage Mapping " +str(e))
                    fh.message = "Unable to edit SAN Storage Mapping"
                    return fh.display()
                try:
                    if NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
                        NasStorageDetails.objects.filter(cluster=clusterObj.id).update(sanPoolName=sanPoolName,sanPoolId=sanPoolId,sanRaidGroup=sanRaidGroup,poolFS1=poolFS1,fileSystem1=fileSystem1,fileSystem2=fileSystem2,fileSystem3=fileSystem3,nasType=nasType,nasNdmpPassword=nasNdmpPassword,nasServerPrefix=nasServerPrefix,fcSwitches=fcSwitches,nasEthernetPorts=nasEthernetPorts,sanPoolDiskCount=sanPoolDiskCount)
                    else:
                        NasStorageDetails.objects.create(cluster_id=clusterObj.id,sanPoolName=sanPoolName,sanRaidGroup=sanRaidGroup,sanPoolId=sanPoolId,poolFS1=poolFS1,fileSystem1=fileSystem1,fileSystem2=fileSystem2,fileSystem3=fileSystem3,nasType=nasType,nasNdmpPassword=nasNdmpPassword,nasServerPrefix=nasServerPrefix,fcSwitches=fcSwitches,nasEthernetPorts=nasEthernetPorts or "",sanPoolDiskCount=sanPoolDiskCount or 0).save(force_update=True)
                except Exception as e:
                    logger.error("Unable to edit NAS Storage Details " +str(e))
                    fh.message = "Unable to edit NAS Storage Details "
                    return fh.display()
                message = "Edited SAN/NAS Information, " + str(changedContent)
                logAction(userId, clusterObj, action, message)
                return fh.success()
            except Exception as e:
                logger.error("Unable to edit deployment to storage and SAN mapping: " +str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
def editClusterOtherProperties(request,clusterId,action):
    '''
    This function is used for allowing users to make modifications of Other Properties in the Cluster.
    '''
    userId = request.user.pk
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to edit Other Properties for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh = FormHandle()
    fh.title = str(action).capitalize() + " Other Properties (DDP) of Depolyment: " + str(clusterObj.name)
    fh.request = request
    fh.button = "Save & Exit"
    fh.button2 = "Cancel"
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    oldValues = []
    if not action == "delete":
        # Add Setup
        ddp_hostname = ""
        cron = ""
        port = ""
        time = ""
        # Edit Setup
        if ClusterAdditionalInformation.objects.filter(cluster_id=clusterId).exists():
            clusterData = ClusterAdditionalInformation.objects.get(cluster_id=clusterId)
            ddp_hostname = str(clusterData.ddp_hostname)
            cron = str(clusterData.cron)
            port = str(clusterData.port)
            time = str(clusterData.time)
            # Old Values
            oldValues = [ddp_hostname + "##DDP Hostname", cron + "##Cron", port + "##Port", time + "##Time"]
        fh.form = EditClusterOtherPropertiesForm(initial={
            'ddp_hostname' : ddp_hostname,
            'cron' : cron,
            'port' : port,
            'time' : time,
            })
    else:
        # Delete
        try:
            clusterData = ClusterAdditionalInformation.objects.get(cluster_id=clusterId)
            clusterData.delete()
            message = "Deleted Other Properties (DDP) of the Deployment"
            logAction(userId, clusterObj, action, message)
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        except:
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = EditClusterOtherPropertiesForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    ddp_hostname = request.POST.get('ddp_hostname')
                    cron = request.POST.get('cron')
                    port = request.POST.get('port')
                    time = request.POST.get('time')
                    if port and not port.isdigit():
                        fh.message = "Failed to add a port number, make sure it contains only numbers. E.g (8080)."
                        logger.error(fh.message)
                        return fh.display()
                    if time and not time.isdigit():
                        fh.message = "Failed to add a time number, make sure it contains only numbers. E.g (30)."
                        logger.error(fh.message)
                        return fh.display()
                    if time and time.isdigit() and int(time) > 60:
                        fh.message = "Failed to add a time number, make sure it's value is no greater than 60. E.g (30)."
                        logger.error(fh.message)
                        return fh.display()

                    ddpPropObj = None
                    if ClusterAdditionalInformation.objects.filter(cluster_id=clusterId).exists():
                        # Edit
                        ddpPropObj = ClusterAdditionalInformation.objects.get(cluster_id=clusterId)
                        ddpPropObj.ddp_hostname=ddp_hostname
                        ddpPropObj.cron=cron
                        ddpPropObj.port=port
                        ddpPropObj.time=time
                        ddpPropObj.save(force_update=True)
                    else:
                        # Add
                        ClusterAdditionalInformation.objects.create(cluster=clusterObj, ddp_hostname=ddp_hostname, cron=cron, port=port, time=time).save(force_update=True)
                    if action == "edit":
                        # New Values
                        newValues = [str(ddpPropObj.ddp_hostname), str(ddpPropObj.cron), str(ddpPropObj.port), str(ddpPropObj.time)]
                        # Checking what has changed
                        changedContent = logChange(oldValues, newValues)
                        message = "Edited Other Properties (DDP), " + str(changedContent)
                    else:
                        message = "Added Other Properties (DDP)"
                    logAction(userId, clusterObj, action, message)
                    return fh.success()
            except Exception as e:
                logger.error("Unable to Edit Other Properties (DDP) of the Deployment")
                return fh.failure()
        else:
            fh.message = "Form is invalid please try again!!!"
            return fh.failure()
    return fh.display()

@login_required
def dvmsInformation(request,clusterId,action):
    '''
    This function is used for DVMS Information.
    '''
    userId = request.user.pk
    clusterObj = Cluster.objects.get(id=clusterId)
    allDeploymentIPs = dmt.utils.getAllIPsInCluster(clusterObj)
    ipType = "dvmsInformation_"
    identifier = clusterObj.management_server.server.hardware_type
    externalIpv4Obj = externalIpv6Obj = internalIpv4Obj = None

    if identifier == "cloud":
        identifierValue = str(clusterObj.id)
    else:
        identifierValue = "1"

    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to edit DVMS Information for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh = FormHandle()
    fh.title = str(action).capitalize() + " DVMS Information for Deployment: " + str(clusterObj.name)
    fh.request = request
    fh.button = "Save & Exit"
    fh.button2 = "Cancel"
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    fh.docLink = "/display/CIOSS/Add+DVMS+Information"

    if action == "add":
        internalGateway,internalAdd,internalBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv_DvmsInfoInternal",allDeploymentIPs)
        fh.form = DvmsInformationForm(initial={
            'internalIPv4' : internalAdd
            })
    elif action == "edit":
        if DvmsInformation.objects.filter(cluster_id=clusterId).exists():
            dvmsInformationObj = DvmsInformation.objects.get(cluster_id=clusterId)

            externalIPv4 = str(dvmsInformationObj.external_ipv4)
            externalIPv6 = str(dvmsInformationObj.external_ipv6)
            internalIPv4 = str(dvmsInformationObj.internal_ipv4)
            if str(dvmsInformationObj.external_ipv6) == "None":
                externalIPv6 = ""
            # Old Values
            oldValues = [str(dvmsInformationObj.external_ipv4.address) + "##External IP4", str(dvmsInformationObj.external_ipv6.ipv6_address) + "##External IPv6", str(dvmsInformationObj.internal_ipv4.address) + "##Internal IPv4"]
            fh.form = DvmsInformationForm(initial={
                'externalIPv4' : externalIPv4,
                'externalIPv6' : externalIPv6,
                'internalIPv4' : internalIPv4
                })

    elif action == "delete":
        # Delete
        try:
            IpAddress.objects.filter(ipType=str(ipType) + str(clusterObj.id)).delete()
            DvmsInformation.objects.get(cluster_id=clusterId).delete()
            message = "Deleted DVMS Information of the Deployment"
            logAction(userId, clusterObj, action, message)
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        except:
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = DvmsInformationForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    if action == "add":
                        externalIpv4Obj = IpAddress.objects.create(address=str(fh.form.cleaned_data['externalIPv4']), ipType=str(ipType) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue)
                        if fh.form.cleaned_data['externalIPv6'] != "":
                            externalIpv6Obj = IpAddress.objects.create(ipv6_address=str(fh.form.cleaned_data['externalIPv6']), ipType=str(ipType) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue)
                        internalIpv4Obj = IpAddress.objects.create(address=str(fh.form.cleaned_data['internalIPv4']), ipType=str(ipType) + str(clusterObj.id), ipv4UniqueIdentifier=str(clusterObj.id))
                        DvmsInformation.objects.create(cluster=clusterObj, external_ipv4=externalIpv4Obj, external_ipv6=externalIpv6Obj, internal_ipv4=internalIpv4Obj)
                        message = "Added DVMS Information of the Deployment"
                        logAction(userId, clusterObj, action, message)

                    if action == 'edit':
                        dvmsInfoObj = DvmsInformation.objects.get(cluster_id=clusterObj.id)
                        forceInsert = False

                        #ipv4 external
                        if IpAddress.objects.filter(address=str(dvmsInfoObj.external_ipv4.address), ipType=str(ipType) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue).exists():
                            externalIpv4Obj = IpAddress.objects.get(address=str(dvmsInfoObj.external_ipv4.address), ipType=str(ipType) + str(clusterObj.id), ipv4UniqueIdentifier=identifierValue)
                            externalIpv4Obj.address = str(fh.form.cleaned_data['externalIPv4'])
                            externalIpv4Obj.save(force_update=True)

                        #ipv6 ext not mandatory field
                        if str(fh.form.cleaned_data['externalIPv6']) is not "":
                            if str(dvmsInfoObj.external_ipv6) != "None" and IpAddress.objects.filter(ipv6_address=str(dvmsInfoObj.external_ipv6.ipv6_address), ipType=str(ipType) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue).exists():
                                externalIpv6Obj = IpAddress.objects.get(ipv6_address=str(dvmsInfoObj.external_ipv6.ipv6_address), ipType=str(ipType) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue)
                                externalIpv6Obj.ipv6_address = str(fh.form.cleaned_data['externalIPv6'])
                                externalIpv6Obj.save(force_update=True)
                            else:
                                externalIpv6Obj = IpAddress.objects.create(ipv6_address=str(fh.form.cleaned_data['externalIPv6']), ipType=str(ipType) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue)
                        else:
                            # if ipv6 has value, delete old one
                            if str(dvmsInfoObj.external_ipv6) != "None" and str(dvmsInfoObj.external_ipv6) != "":
                                IpAddress.objects.filter(ipv6_address=str(dvmsInfoObj.external_ipv6), ipType=str(ipType) + str(clusterObj.id), ipv6UniqueIdentifier=identifierValue).delete()
                                forceInsert = True

                        #ipv4 internal
                        if IpAddress.objects.filter(address=str(dvmsInfoObj.internal_ipv4.address), ipType=str(ipType) + str(clusterObj.id), ipv4UniqueIdentifier=str(clusterObj.id)).exists():
                            internalIpv4Obj = IpAddress.objects.get(address=str(dvmsInfoObj.internal_ipv4.address), ipType=str(ipType) + str(clusterObj.id), ipv4UniqueIdentifier=str(clusterObj.id))
                            internalIpv4Obj.address = str(fh.form.cleaned_data['internalIPv4'])
                            internalIpv4Obj.save(force_update=True)
                        # save
                        dvmsInfoObj.external_ipv4 = externalIpv4Obj
                        dvmsInfoObj.external_ipv6 = externalIpv6Obj
                        dvmsInfoObj.internal_ipv4 = internalIpv4Obj
                        if forceInsert is True:
                            dvmsInfoObj.save(force_insert = True)
                        else:
                            dvmsInfoObj.save(force_update = True)
                        # New Values
                        newValues = [str(fh.form.cleaned_data['externalIPv4']), str(fh.form.cleaned_data['externalIPv6']), str(fh.form.cleaned_data['internalIPv4'])]
                        changedContent = logChange(oldValues, newValues)
                        message = "Edited DVMS Information of the Deployment, " + str(changedContent)
                        logAction(userId, clusterObj, action, message)
                    return fh.success()
            except Exception as e:
                logger.error("Unable to Edit DVMS Information of the Deployment")
                fh.failMessage = "Form is invalid: " + str(e)
                return fh.failure()
        else:
            return fh.failure()
    return fh.display()

@login_required
def editStorageAttachedNetworkOSS(request,clusterId):
    '''
    '''
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    isRackDeployment = dmt.utils.isEnmRackDeployment(clusterObj.enmDeploymentType)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to edit Storage Attached Network for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.title = "Edit Network Attached Storage Information: " +str(clusterObj.name)
    fh.button = "Submit"
    if ClusterToNASMapping.objects.filter(cluster=clusterObj.id).exists():
        clusterNASMapObj = ClusterToNASMapping.objects.get(cluster=clusterObj.id)
        clustetToSanMapObj = ClusterToStorageMapping.objects.get(cluster_id=clusterId)
        nasStorageDtlsObj = sanPoolName = sanPoolId = poolFS1 = fileSystem1 = poolFS2 = ""
        fileSystem2 = poolFS3 = fileSystem3 = nasType = nasNdmpPassword = nasServerPrefix = ""
        nasEthernetPorts = sanPoolDiskCount = fcSwitches = ""
        if NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
            nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=clusterObj.id)
            sanPoolName = nasStorageDtlsObj.sanPoolName
            sanPoolId = nasStorageDtlsObj.sanPoolId
            poolFS1 = nasStorageDtlsObj.poolFS1
            fileSystem1 = nasStorageDtlsObj.fileSystem1
            poolFS2 = nasStorageDtlsObj.poolFS2
            fileSystem2 = nasStorageDtlsObj.fileSystem2
            poolFS3 = nasStorageDtlsObj.poolFS3
            fileSystem3 = nasStorageDtlsObj.fileSystem3
            nasType = nasStorageDtlsObj.nasType
            nasNdmpPassword = nasStorageDtlsObj.nasNdmpPassword
            nasServerPrefix = nasStorageDtlsObj.nasServerPrefix
            fcSwitches = nasStorageDtlsObj.fcSwitches
            nasEthernetPorts = nasStorageDtlsObj.nasEthernetPorts
            sanPoolDiskCount = nasStorageDtlsObj.sanPoolDiskCount
        fh.form = EditSanFormOSS(
                initial={
                    'storage' : clustetToSanMapObj.storage,
                    'nasServer' : clusterNASMapObj.nasServer,
                    'sanPoolName' : sanPoolName,
                    'sanPoolId' : sanPoolId,
                    'poolFS1' : poolFS1,
                    'fileSystem1' : fileSystem1,
                    'poolFS2' : poolFS2,
                    'fileSystem2' : fileSystem2,
                    'poolFS3' : poolFS3,
                    'fileSystem3' : fileSystem3,
                    'nasType': nasType,
                    'nasNdmpPassword': nasNdmpPassword,
                    'nasServerPrefix': nasServerPrefix
                    })
        if NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
            if isRackDeployment:
                fh.form = EditSanFormOSSOnRack(initial = fh.form.initial)
                fh.form.initial['fcSwitches'] = fcSwitches
                fh.form.initial['nasEthernetPorts'] = nasEthernetPorts
                fh.form.initial['sanPoolDiskCount'] = sanPoolDiskCount
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        storage = request.POST.get("storage")
        storageObj = Storage.objects.get(hostname=storage)
        nas = request.POST.get("nasServer")
        nas = str(nas).split("(id: ")
        nas = nas[1]
        nas = nas.replace(')','')
        serverObj = Server.objects.get(id=nas)
        nasObj = NASServer.objects.filter(server=serverObj)[0]
        sanPoolName = request.POST.get("sanPoolName")
        sanPoolId = request.POST.get("sanPoolId")
        poolFS1 = request.POST.get("poolFS1")
        fileSystem1 = request.POST.get("fileSystem1")
        poolFS2 = request.POST.get("poolFS2")
        fileSystem2 = request.POST.get("fileSystem2")
        poolFS3 = request.POST.get("poolFS3")
        fileSystem3 = request.POST.get("fileSystem3")
        nasType = request.POST.get("nasType")
        if nasType == "unityxt" and clusterNASMapObj.nasServer.server.hardware_type == "rack":
            nasNdmpPassword = request.POST.get("nasNdmpPassword")
            nasServerPrefix = request.POST.get("nasServerPrefix")
        else:
            nasNdmpPassword = nasServerPrefix = ""

        if isRackDeployment:
            fcSwitches = dmt.utils.convertStrToBool(request.POST.get("fcSwitches"))
            nasEthernetPorts = request.POST.get("nasEthernetPorts")
            sanPoolDiskCount = request.POST.get("sanPoolDiskCount")
            fh.form = EditSanFormOSSOnRack(request.POST)
        else:
            fh.form = EditSanFormOSS(request.POST)
        if fh.form.is_valid():
            try:
                try:
                    nastoClusterMapping = ClusterToNASMapping.objects.filter(cluster=clusterObj).update(nasServer=nasObj)
                except Exception as e:
                    logger.error("Unable to edit NAS Server " +str(e))
                    fh.message = "Unable to edit NAS Server"
                    return fh.display()
                try:
                    clustertoStorageMapping = ClusterToStorageMapping.objects.filter(cluster=clusterObj).update(storage=storageObj)
                except Exception as e:
                    logger.error("Unable to edit SAN Server " +str(e))
                    fh.message = "Unable to edit SAN Server"
                    return fh.display()
                try:
                    if NasStorageDetails.objects.filter(cluster_id=clusterId).exists():
                        NasStorageDetails.objects.filter(cluster=clusterObj.id).update(sanPoolName = sanPoolName, sanPoolId = sanPoolId, poolFS1 = poolFS1, fileSystem1 = fileSystem1, poolFS2 = poolFS2, fileSystem2 = fileSystem2, poolFS3 = poolFS3, fileSystem3 = fileSystem3, nasType = nasType, nasNdmpPassword=nasNdmpPassword, nasServerPrefix=nasServerPrefix, fcSwitches=fcSwitches,nasEthernetPorts=nasEthernetPorts,sanPoolDiskCount=sanPoolDiskCount)
                    else:
                        NasStorageDetails.objects.create(cluster_id=clusterObj.id,sanPoolName = sanPoolName, sanPoolId = sanPoolId, poolFS1 = poolFS1, fileSystem1 = fileSystem1, poolFS2 = poolFS2, fileSystem2 = fileSystem2, poolFS3 = poolFS3, fileSystem3 = fileSystem3, nasType = nasType, nasNdmpPassword=nasNdmpPassword, nasServerPrefix=nasServerPrefix, fcSwitches=fcSwitches,nasEthernetPorts=nasEthernetPorts,sanPoolDiskCount=sanPoolDiskCount).save(force_update=True)
                except Exception as e:
                    logger.error("Unable to edit NAS Storage Details " +str(e))
                    fh.message = "Unable to edit NAS Storage Details "
                    return fh.display()
                return fh.success()
            except Exception as e:
                logger.error("Unable to edit deployment to storage and SAN mapping: " +str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
def deleteStorageAttachedNetwork(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete Storage Attached Network for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    if ClusterToNASMapping.objects.filter(cluster=clusterObj).exists():
        clusterNASMapObj = ClusterToNASMapping.objects.get(cluster=clusterObj)
        if ClusterToStorageMapping.objects.filter(cluster=clusterObj).exists():
            clusterToSanMapObj = ClusterToStorageMapping.objects.get(cluster=clusterObj)
        if NasStorageDetails.objects.filter(cluster=clusterObj).exists():
            nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=clusterObj)
    try:
        if clusterNASMapObj:
            clusterNASMapObj.delete()
            if clusterToSanMapObj:
                clusterToSanMapObj.delete()
            if nasStorageDtlsObj:
                nasStorageDtlsObj.delete()
        cursor = connection.cursor()
        message = "Deleted SAN/NAS Storage Information"
        logAction(userId, clusterObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def addDirectAttachedStorageNAS(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "add"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Add Direct Attached Storage for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh.title = "Register Network Attached Storage Information: " +str(clusterObj.name)
    fh.button = "Register"
    fh.form = NASForm()
    fh.request = request
    fh.redirectTarget = "/dmt/" +str(clusterObj.id)+ "/extraNasStorage/details/"
    if request.method == 'POST':
        nasServer = request.POST.get("nasServer")
        nasServer = str(nasServer).split("(id: ")
        nasServer = nasServer[1]
        nasServer = nasServer.replace(')','')
        nasServerObj = Server.objects.get(id=nasServer)
        try:
            with transaction.atomic():
                if ClusterToDASNASMapping.objects.filter(cluster=clusterObj,dasNasServer=nasServerObj).exists():
                    logger.info("Deployment to NAS DAS Mapping Already exists")
                else:
                    clusterToDasMap = ClusterToDASNASMapping.objects.create(cluster=clusterObj,dasNasServer=nasServerObj)
                message = "Added NAS Storage Details (DAS - Stage 1)"
                logAction(userId, clusterObj, action, message)
                return fh.success()
        except IntegrityError as e:
            logger.error("Unable to add deployment to NAS DAS mapping: " +str(e))
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addDirectAttachedStorageSAN(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "add"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to add Direct Attached Storage SAN for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh.title = "Register Network Attached Storage Information: " +str(clusterObj.name)
    fh.button = "Register"
    fh.form = DASForm()
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        storage = request.POST.get("storage")
        storageObj = Storage.objects.get(hostname=storage)
        try:
            with transaction.atomic():
                if ClusterToDASMapping.objects.filter(cluster=clusterObj,storage=storageObj).exists():
                    logger.info("Deployment to Storage Mapping Already exists")
                else:
                    clusterToDasMap = ClusterToDASMapping.objects.create(cluster=clusterObj,storage=storageObj)
                message = "Added SAN Storage Details"
                logAction(userId, clusterObj, action, message)
                return fh.success()
        except IntegrityError as e:
            logger.error("Unable to add deployment to storage mapping: " +str(e))
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def serviceIpRange(request,clusterId,rangeId,task):
    '''
    '''
    userId = request.user.pk
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"
    taskTitle = task.title()
    fh.title = str(taskTitle) + " VM Service IP Range to deployment : " +str(clusterObj.name)
    fh.button = "Save & Exit"
    fh.button2 = "Cancel"
    fh.form = ServiceIpRange()
    fh.request = request
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = ServiceIpRange(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    startIp = request.POST.get('startIp')
                    endIp = request.POST.get('endIp')
                    ipType = request.POST.get('ipType')
                    (returnedValue,message) = dmt.utils.ipRangeTypeCheck(startIp,endIp,ipType)
                    if returnedValue == 1:
                        fh.message = message
                        return fh.display()
                    (returnedValue,message) = dmt.utils.ipRangeCheckStartLessThanEnd(startIp,endIp)
                    if returnedValue == 1:
                        fh.message = message
                        return fh.display()
                    if task == "edit":
                        vmServiceIpRangeFields = ('ipv4AddressStart', 'ipv4AddressEnd', 'ipv6AddressStart','ipv6AddressEnd','ipTypeId__ipType')
                        VmServiceIpRangeObj = VmServiceIpRange.objects.only(vmServiceIpRangeFields).values(*vmServiceIpRangeFields).get(id=rangeId)
                        oldValues = [str(VmServiceIpRangeObj['ipv4AddressStart']) + "##IPV4 Start Address",
                                str(VmServiceIpRangeObj['ipv4AddressEnd']) + "##IPV4 End Address",
                                str(VmServiceIpRangeObj['ipv6AddressStart']) + "##IPV6 Start Address",
                                str(VmServiceIpRangeObj['ipv6AddressEnd']) + "##IPV6 End Address",
                                str(VmServiceIpRangeObj['ipTypeId__ipType']) + "##IP Type"]
                        ipv4Start = ipv4End = ipv6Start = ipv6End = None
                        if "ipv6" in ipType.lower():
                            ipv6Start = startIp
                            ipv6End = endIp
                        else:
                            ipv4Start = startIp
                            ipv4End = endIp
                        newValues = [str(ipv4Start),str(ipv4End),str(ipv6Start),str(ipv6End),str(ipType)]
                        changedContent = logChange(oldValues,newValues)
                    if task == "add":
                        returnedValue,message = dmt.utils.addServiceIpRange(clusterId,task,startIp,endIp,ipType)
                    else:
                        returnedValue,message = dmt.utils.editServiceIpRange(task,startIp,endIp,ipType,rangeId)
                    if returnedValue == "1":
                        fh.message = "Error: " + str(message)
                        return fh.display()
                    else:
                        if task == "edit":
                            message = "Edited VM Service IP Range, " + str(changedContent)
                        else:
                            message = "Added VM Service IP Range, start of range " + str(startIp) +", end of range " + str(endIp)
                        logAction(userId, clusterObj, task, message)
                        return fh.success()
            except Exception as e:
                logger.error("Unable to register VM Service IP Range for Deployment: " + clusterObj.name + " Exception : " +str(e))
                return fh.failure()
        else:
            fh.message = "Form is invalid please try again!!!"
            return fh.display()
    else:
        if task == "edit" or task == "delete":
            if VmServiceIpRange.objects.filter(id=rangeId).exists():
                vmServiceIpRangeFields = ('id', 'ipv4AddressStart', 'ipv4AddressEnd', 'ipv6AddressStart','ipv6AddressEnd','ipTypeId__ipType')
                VmServiceIpRangeObj = VmServiceIpRange.objects.only(vmServiceIpRangeFields).values(*vmServiceIpRangeFields).get(id=rangeId)
                if "ipv6" in VmServiceIpRangeObj['ipTypeId__ipType'].lower():
                    startIp = VmServiceIpRangeObj['ipv6AddressStart']
                    endIp = VmServiceIpRangeObj['ipv6AddressEnd']
                else:
                    startIp = VmServiceIpRangeObj['ipv4AddressStart']
                    endIp = VmServiceIpRangeObj['ipv4AddressEnd']
                ipType = VmServiceIpRangeObj['ipTypeId__ipType']
                if task == "edit":
                    fh.form = ServiceIpRange(initial=
                        {
                            'ipType' : ipType,
                            'startIp' : startIp,
                            'endIp' : endIp
                        })
                else:
                    VmServiceIpRange.objects.get(id=rangeId).delete()
                    cursor = connection.cursor()
                    message = "Deleted VM Service Range Details, start range: " + str(startIp) + ", end Range: " + str(endIp) + ", of type " + str(ipType)
                    logAction(userId, clusterObj, task, message)
                    return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        return fh.display()

@login_required
@transaction.atomic
def vlanDetails(request,clusterId,task):
    '''
    Add a Heart Beat Vlan info to the Deployment
    '''
    userId = request.user.pk
    action = task
    hbaVlan = None
    hbbVlan = None
    if VlanDetails.objects.filter(cluster=clusterId).exists():
        vlanTagObj =  VlanDetails.objects.filter(cluster=clusterId)
        if VirtualConnectNetworks.objects.filter(vlanDetails=vlanTagObj).exists():
            task = "edit"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    user = User.objects.get(username=str(request.user))
    if not user.is_superuser:
        if not config.get("DMT", "ciAdmin") in request.user.groups.values_list('name',flat=True):
            error = "You do not have permission to add HB Vlan for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    taskTitle = task.title()
    fh.title = str(taskTitle) + " VLAN Details for Deployment : " +str(clusterObj.name)
    fh.button = "Save & Exit"
    fh.button2 = "Cancel"
    fh.form = AddVlanForm()
    fh.request = request
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = AddVlanForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    vlanDetailsValues = {}
                    vlanDetailsValues['hbaVlan'] = request.POST.get('hbAVlan')
                    vlanDetailsValues['hbbVlan'] = request.POST.get('hbBVlan')
                    vlanDetailsValues['serviceSubnet'] = request.POST.get('services_subnet')
                    vlanDetailsValues['servicesGateway'] = request.POST.get('services_gateway')
                    vlanDetailsValues['serviceIpv6Gateway'] = request.POST.get('services_ipv6_gateway')
                    vlanDetailsValues['serviceIpv6Subnet'] = request.POST.get('services_ipv6_subnet')
                    vlanDetailsValues['storageSubnet'] = request.POST.get('storage_subnet')
                    vlanDetailsValues['storageGateway'] = request.POST.get('storageGateway')
                    vlanDetailsValues['backupSubnet'] = request.POST.get('backup_subnet')
                    vlanDetailsValues['jgroupsSubnet'] = request.POST.get('jgroups_subnet')
                    vlanDetailsValues['internalSubnet'] = request.POST.get('internal_subnet')
                    vlanDetailsValues['internalIPv6Subnet'] = request.POST.get('internal_ipv6_subnet')
                    vlanDetailsValues['storageVlan'] = request.POST.get('storage_vlan')
                    vlanDetailsValues['backupVlan'] = request.POST.get('backup_vlan')
                    vlanDetailsValues['jgroupsVlan'] = request.POST.get('jgroups_vlan')
                    vlanDetailsValues['internalVlan'] = request.POST.get('internal_vlan')
                    vlanDetailsValues['servicesVlan'] = request.POST.get('services_vlan')
                    vlanDetailsValues['managementVlan'] = request.POST.get('management_vlan')
                    vlanDetailsValues['litpManagement'] = request.POST.get('litp_management')
                    addressList = filter(None,[str(vlanDetailsValues['serviceSubnet']),str(vlanDetailsValues['servicesGateway']),str(vlanDetailsValues['serviceIpv6Gateway']),str(vlanDetailsValues['serviceIpv6Subnet']),str(vlanDetailsValues['storageSubnet']),str(vlanDetailsValues['storageGateway']),str(vlanDetailsValues['backupSubnet']),str(vlanDetailsValues['jgroupsSubnet']),str(vlanDetailsValues['internalSubnet']),str(vlanDetailsValues['internalIPv6Subnet'])])
                    duplicates = dmt.utils.getDuplicatesInList(addressList)
                    if len(duplicates) > 0:
                        raise Exception("Duplicate IP Info "+str(duplicates))
                    if task == "edit":
                        HbVlanObj = VlanDetails.objects.get(cluster=clusterObj.id)
                        oldValues = [str(HbVlanObj.hbAVlan) + "##HBA VLAN",
                                str(HbVlanObj.hbBVlan) + "##HBB VLAN",
                                str(HbVlanObj.services_subnet) + "##Service Subnet",
                                str(HbVlanObj.services_gateway) + "##Service Gateway",
                                str(HbVlanObj.services_ipv6_gateway) + "##Service IPV6 Gateway",
                                str(HbVlanObj.services_ipv6_subnet) + "##Service IPV6 Subnet",
                                str(HbVlanObj.storage_subnet) + "##Storage Subnet",
                                str(HbVlanObj.storage_gateway) + "##Storage Gateway",
                                str(HbVlanObj.backup_subnet) + "##Backup Subnet",
                                str(HbVlanObj.jgroups_subnet) + "##JGroups Subnet",
                                str(HbVlanObj.internal_subnet) + "##Internal Subnet",
                                str(HbVlanObj.internal_ipv6_subnet) + "##Internal IPV6 Subnet",
                                str(HbVlanObj.storage_vlan) + "##Storage VLAN ID",
                                str(HbVlanObj.backup_vlan) + "##Backup VLAN ID",
                                str(HbVlanObj.jgroups_vlan) + "##JGroups VLAN ID",
                                str(HbVlanObj.internal_vlan) + "##Internal VLAN ID",
                                str(HbVlanObj.services_vlan) + "##Services VLAN ID",
                                str(HbVlanObj.management_vlan) + "##Management VLAN ID",
                                str(HbVlanObj.litp_management) + "##LITP Management"]
                        newValues = [str(vlanDetailsValues['hbaVlan']),str(vlanDetailsValues['hbbVlan']),
                                     str(vlanDetailsValues['serviceSubnet']),str(vlanDetailsValues['servicesGateway']),
                                     str(vlanDetailsValues['serviceIpv6Gateway']),str(vlanDetailsValues['serviceIpv6Subnet']),
                                     str(vlanDetailsValues['storageSubnet']),str(vlanDetailsValues['storageGateway']),
                                     str(vlanDetailsValues['backupSubnet']),str(vlanDetailsValues['jgroupsSubnet']),
                                     str(vlanDetailsValues['internalSubnet']),str(vlanDetailsValues['internalIPv6Subnet']),
                                     str(vlanDetailsValues['storageVlan']),str(vlanDetailsValues['backupVlan']),
                                     str(vlanDetailsValues['jgroupsVlan']),str(vlanDetailsValues['internalVlan']),
                                     str(vlanDetailsValues['servicesVlan']),str(vlanDetailsValues['managementVlan']),
                                     str(vlanDetailsValues['litpManagement'])]
                        changedContent = logChange(oldValues,newValues)
                        returnedValue,message = dmt.utils.editVlanDetails(clusterId,task,vlanDetailsValues)
                    else:
                        returnedValue,message = dmt.utils.createVlanDetails(clusterId,task,vlanDetailsValues)
                    if returnedValue == "1":
                        fh.message = "Error: " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if action == "edit":
                            message = "Edited VLAN Configuration (Section 1), " + str(changedContent)
                        else:
                            message = "Added VLAN Configuration (Section 1)"
                        logAction(userId, clusterObj, action, message)
                        return fh.success()
            except Exception as e:
                logger.error("Unable to register Vlan Data to Deployment: " + clusterObj.name + " Exception : " +str(e))
                return fh.failure()
        else:
            fh.message = "Form is invalid please try again!!!"
            return fh.display()
    else:
        internalIPv6Subnet = dmt.utils.getSubnetDetails("internalIPv6")
        if clusterObj.layout.name == "KVM":
            internalIPv6Subnet = dmt.utils.getSubnetDetails("internalIPv6",clusterObj.id)

        if task == "edit":
            if VlanDetails.objects.filter(cluster=clusterObj.id).exists():
                HbVlanObj = VlanDetails.objects.get(cluster=clusterObj.id)
                if HbVlanObj.internal_ipv6_subnet is None:
                    internal_ipv6_subnet = internalIPv6Subnet
                else:
                    internal_ipv6_subnet = HbVlanObj.internal_ipv6_subnet
                fh.form = AddVlanForm(initial=
                    {
                        'hbAVlan' : HbVlanObj.hbAVlan,
                        'hbBVlan' : HbVlanObj.hbBVlan,
                        'services_subnet' : HbVlanObj.services_subnet,
                        'services_gateway' : HbVlanObj.services_gateway,
                        'services_ipv6_gateway' : HbVlanObj.services_ipv6_gateway,
                        'services_ipv6_subnet' : HbVlanObj.services_ipv6_subnet,
                        'storage_subnet' : HbVlanObj.storage_subnet,
                        'storageGateway' : HbVlanObj.storage_gateway,
                        'backup_subnet' : HbVlanObj.backup_subnet,
                        'jgroups_subnet' : HbVlanObj.jgroups_subnet,
                        'internal_subnet' : HbVlanObj.internal_subnet,
                        'internal_ipv6_subnet' : internal_ipv6_subnet,
                        'storage_vlan' : HbVlanObj.storage_vlan,
                        'backup_vlan' : HbVlanObj.backup_vlan,
                        'jgroups_vlan' : HbVlanObj.jgroups_vlan,
                        'internal_vlan' : HbVlanObj.internal_vlan,
                        'services_vlan' : HbVlanObj.services_vlan,
                        'management_vlan' : HbVlanObj.management_vlan,
                        'litp_management' : HbVlanObj.litp_management,
                    })
        else:
            jgroupSubnet = dmt.utils.getSubnetDetails("jgroup")
            if jgroupSubnet == 1:
                jgroupSubnet = ""
            internalSubnet = dmt.utils.getSubnetDetails("internal")
            if internalSubnet == 1:
                internalSubnet = ""
            if internalIPv6Subnet == 1:
                internalIPv6Subnet = ""
            fh.form = AddVlanForm(initial=
                {
                    'jgroups_subnet' : jgroupSubnet,
                    'internal_subnet' : internalSubnet,
                    'internal_ipv6_subnet' : internalIPv6Subnet
                })
        return fh.display()

@login_required
@transaction.atomic
def virtualConnectNetworks(request,vlanDetailsId,task):
    '''
    Edit the Virtual Connect Networks
    '''
    fh = FormHandle()
    userId = request.user.pk
    action = task
    vlanDetailsObj = VlanDetails.objects.get(id=vlanDetailsId)
    clusterObj = Cluster.objects.get(id=vlanDetailsObj.cluster_id)

    user = User.objects.get(username=str(request.user))
    if not user.is_superuser:
        if not config.get("DMT", "ciAdmin") in request.user.groups.values_list('name',flat=True):
            error = "You do not have permission to add HB Vlan for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    taskTitle = task.title()
    fh.title = str(taskTitle) + " Virtual Connect Info for Deployment: " +str(clusterObj.name)
    fh.button = "Save & Exit"
    fh.button2 = "Cancel"
    fh.form = VirtualConnectNetworksForm()
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = VirtualConnectNetworksForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    sharedUplinkSetA = request.POST.get('sharedUplinkSetA')
                    sharedUplinkSetB = request.POST.get('sharedUplinkSetB')
                    servicesA = request.POST.get('servicesA')
                    servicesB = request.POST.get('servicesB')
                    storageA = request.POST.get('storageA')
                    storageB = request.POST.get('storageB')
                    backupA = request.POST.get('backupA')
                    backupB = request.POST.get('backupB')
                    jgroups = request.POST.get('jgroups')
                    jgroupsA = request.POST.get('jgroupsA')
                    jgroupsB = request.POST.get('jgroupsB')
                    internalA = request.POST.get('internalA')
                    internalB = request.POST.get('internalB')
                    heartbeat1 = request.POST.get('heartbeat1')
                    heartbeat2 = request.POST.get('heartbeat2')
                    heartbeat1A = request.POST.get('heartbeat1A')
                    heartbeat2B = request.POST.get('heartbeat2B')
                    if task == "edit":
                        virtualConnectObj = VirtualConnectNetworks.objects.get(vlanDetails_id=vlanDetailsId)
                        oldValues = [str(virtualConnectObj.sharedUplinkSetA) + "##Shared Uplink",
                            str(virtualConnectObj.sharedUplinkSetB) + "##Shared Uplink B",
                            str(virtualConnectObj.servicesA) + "##Services A",
                            str(virtualConnectObj.servicesB) + "##Services B",
                            str(virtualConnectObj.storageA) + "##Storage A",
                            str(virtualConnectObj.storageB) + "##Storage B",
                            str(virtualConnectObj.backupA) + "##Backup A",
                            str(virtualConnectObj.backupB) + "##Backup B",
                            str(virtualConnectObj.jgroups) + "##JGroups",
                            str(virtualConnectObj.jgroupsA) + "##JGroups A",
                            str(virtualConnectObj.jgroupsB) + "##JGroups B",
                            str(virtualConnectObj.internalA) + "##Internal A",
                            str(virtualConnectObj.internalB) + "##Internal B",
                            str(virtualConnectObj.heartbeat1) + "##HeartBeat1",
                            str(virtualConnectObj.heartbeat2) + "##HeartBeat2",
                            str(virtualConnectObj.heartbeat1A) + "##HeartBeat1A",
                            str(virtualConnectObj.heartbeat2B) + "##HeartBeat2B"]
                        newValues = [str(sharedUplinkSetA),str(sharedUplinkSetB),str(servicesA),str(servicesB),str(storageA),str(storageB),str(backupA),str(backupB),str(jgroups),str(jgroupsA),str(jgroupsB),str(internalA),str(internalB),str(heartbeat1),str(heartbeat2),str(heartbeat1A),str(heartbeat2B)]
                        changedContent = logChange(oldValues,newValues)
                        returnedValue,message = dmt.utils.editVirtualConnectDetails(clusterObj.id,sharedUplinkSetA,sharedUplinkSetB,servicesA,servicesB,storageA,storageB,backupA,backupB,jgroups,jgroupsA,jgroupsB,internalA,internalB,heartbeat1,heartbeat2,heartbeat1A,heartbeat2B)
                    else:
                        returnedValue,message = dmt.utils.createVirtualConnectDetails(clusterObj.id,sharedUplinkSetA,sharedUplinkSetB,servicesA,servicesB,storageA,storageB,backupA,backupB,jgroups,jgroupsA,jgroupsB,internalA,internalB,heartbeat1,heartbeat2,heartbeat1A,heartbeat2B)
                    if returnedValue == "1":
                        fh.message = "Error: " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if action == "edit":
                            message = "Edited VLAN Configuration (Section 2), " + str(changedContent)
                        else:
                            message = "Added VLAN Configuration (Section 2)"
                        logAction(userId, clusterObj, action, message)
                        return fh.success()
            except Exception as e:
                logger.error("Unable to register Virtual Connect to Deployment: " + clusterObj.name + " Exception : " +str(e))
                return fh.failure()
        else:
            fh.message = "Form is invalid please try again!!!"
            return fh.display()
    else:
        if task == "edit":
            if VirtualConnectNetworks.objects.filter(vlanDetails_id=vlanDetailsId).exists():
                virtualConnectObj = VirtualConnectNetworks.objects.get(vlanDetails_id=vlanDetailsId)
                fh.form = VirtualConnectNetworksForm(initial=
                    {
                        'sharedUplinkSetA' : virtualConnectObj.sharedUplinkSetA,
                        'sharedUplinkSetB' : virtualConnectObj.sharedUplinkSetB,
                        'servicesA' : virtualConnectObj.servicesA,
                        'servicesB' : virtualConnectObj.servicesB,
                        'storageA' : virtualConnectObj.storageA,
                        'storageB' : virtualConnectObj.storageB,
                        'backupA' : virtualConnectObj.backupA,
                        'backupB' : virtualConnectObj.backupB,
                        'jgroups' : virtualConnectObj.jgroups,
                        'jgroupsA' : virtualConnectObj.jgroupsA,
                        'jgroupsB' : virtualConnectObj.jgroupsB,
                        'internalA' : virtualConnectObj.internalA,
                        'internalB' : virtualConnectObj.internalB,
                        'heartbeat1' : virtualConnectObj.heartbeat1,
                        'heartbeat2' : virtualConnectObj.heartbeat2,
                        'heartbeat1A' : virtualConnectObj.heartbeat1A,
                        'heartbeat2B' : virtualConnectObj.heartbeat2B,
                    })
        return fh.display()

@login_required
def deleteHBVlan(request,clusterId):
    '''
    Used to delete the Registered Heart Beat Vlan data attached to the Deployment
    '''
    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    virtualConnectNetworksObj = None
    vlanDetails = None

    user = User.objects.get(username=str(request.user))
    if not user.is_superuser:
        if not config.get("DMT", "ciAdmin") in request.user.groups.values_list('name',flat=True):
            error = "You do not have permission to delete HB Vlan for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    if VlanDetails.objects.filter(cluster=clusterObj.id).exists():
        vlanDetails = VlanDetails.objects.get(cluster=clusterObj.id)
        if VirtualConnectNetworks.objects.filter(vlanDetails=vlanDetails).exists():
            virtualConnectNetworksObj = VirtualConnectNetworks.objects.get(vlanDetails=vlanDetails)
    try:
        if virtualConnectNetworksObj != None:
            virtualConnectNetworksObj.delete()
        if vlanDetails != None:
            dmt.utils.deleteStorageGatewayObjIfExists(vlanDetails)
            vlanDetails.delete()
        cursor = connection.cursor()
        message = "Deleted VLAN Details"
        logAction(userId, clusterObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def addOSSRCCluster(request,clusterId):
    '''
    Add a new OSSRC Deployment
    '''
    userId = request.user.pk
    action = "add"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to register an OSSRC System to this Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.title = "Register OSSRC Deployment Information: " +str(clusterObj.name)
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    fh.form = OSSRCForm()
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        ossrcCluster = request.POST.get("ossrcCluster")
        ossrcClusterObj = Cluster.objects.get(name=ossrcCluster)
        try:
            with transaction.atomic():
                if OssrcClusterToTorClusterMapping.objects.filter(torCluster=clusterObj,ossCluster=ossrcClusterObj).exists():
                    logger.info("OSSRC Deployment to ENM Deployment Mapping Already exists")
                    fh.message = ("OSSRC Deployment to ENM Deployment Mapping Already exists")
                    return fh.display()
                else:
                    ossrcClusterToTorCluster = OssrcClusterToTorClusterMapping.objects.create(torCluster=clusterObj,ossCluster=ossrcClusterObj)
                    message = "Added OSSRC System to Deployment"
                    logAction(userId, clusterObj, action, message)
                    return fh.success()
        except IntegrityError as e:
            logger.error("Unable to register OSSRC Deployment to ENM Deployment: " +str(e))
            return fh.failure()
    else:
        return fh.display()

@login_required
def editSsoInfo(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "edit"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to this section for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.title = "Edit SSO/LDAP Extra Information on Deployment: " +str(clusterObj.name)
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    if SsoDetails.objects.filter(cluster=clusterObj.id).exists():
        ssoObj = SsoDetails.objects.get(cluster=clusterObj.id)
        if clusterObj.layout.id != 3:
            fh.form = SsoLdapDetailsForm(initial={'ldapDomain' : ssoObj.ldapDomain, 'ldapPassword' : ssoObj.ldapPassword, 'openidmAdminPassword' : ssoObj.openidmAdminPassword, 'openidmMysqlPassword' : ssoObj.openidmMysqlPassword, 'securityAdminPassword' : ssoObj.securityAdminPassword, 'opendjAdminPassword' : ssoObj.opendjAdminPassword, 'hqDatabasePassword' : ssoObj.hqDatabasePassword,'brsadmPassword' : ssoObj.brsadm_password,})
        else:
            fh.form = SsoDetailsForm(initial={'ldapDomain' : ssoObj.ldapDomain, 'ldapPassword' : ssoObj.ldapPassword, 'ossFsServer' : ssoObj.ossFsServer, 'citrixFarm' : ssoObj.citrixFarm,'brsadmPassword' : ssoObj.brsadm_password,})
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        ldapDomain = request.POST.get('ldapDomain')
        ldapPassword = request.POST.get('ldapPassword')
        oldValues = [str(ssoObj.ldapDomain) + "##LDAP Domain",str(ssoObj.ldapPassword) + "##LDAP Password"]
        newValues = [str(ldapDomain),str(ldapPassword)]
        if clusterObj.layout.id != 3:
            opendjAdminPassword = request.POST.get('opendjAdminPassword')
            openidmAdminPassword = request.POST.get('openidmAdminPassword')
            openidmMysqlPassword = request.POST.get('openidmMysqlPassword')
            securityAdminPassword = request.POST.get('securityAdminPassword')
            hqDatabasePassword = request.POST.get('hqDatabasePassword')
            brsadmPassword = request.POST.get('brsadmPassword')
            ossFsServer = ssoObj.ossFsServer
            citrixFarm = ssoObj.citrixFarm
            oldValues.extend([str(ssoObj.opendjAdminPassword) + "##Opendj Admin Password",
                str(ssoObj.openidmAdminPassword) + "##Openidm Admin Password",
                str(ssoObj.openidmMysqlPassword) + "##Openidm MySQL Password",
                str(ssoObj.securityAdminPassword) + "##Security Admin Password",
                str(ssoObj.hqDatabasePassword) + "##HQ DB Password",
                str(ossFsServer) + "##OSSFS Server",
                str(citrixFarm) + "##CITRIX Farm",
                str(ssoObj.brsadm_password) + "##Brsadm Password"])
            newValues.extend([str(opendjAdminPassword),str(openidmAdminPassword),str(openidmMysqlPassword),str(securityAdminPassword),str(hqDatabasePassword),str(ossFsServer),str(citrixFarm),str(brsadmPassword)])
        else:
            ossFsServer = request.POST.get('ossFsServer')
            citrixFarm = request.POST.get('citrixFarm')
            brsadmPassword = request.POST.get('brsadmPassword')
            oldValues.extend([str(ssoObj.ossFsServer) + "##OSSFS Server",
                str(ssoObj.citrixFarm) + "##Citrix Farm",
                str(ssoObj.brsadm_password) + "##Brsadm Password"])
            newValues.extend([str(ossFsServer),str(citrixFarm),str(brsadmPassword)])
        changedContent = logChange(oldValues,newValues)
        if clusterObj.layout.id != 3:
            fh.form = SsoLdapDetailsForm(request.POST)
        else:
            fh.form = SsoDetailsForm(request.POST)
        if fh.form.is_valid():
            try:
                if clusterObj.layout.id != 3:
                    ssoDetails = SsoDetails.objects.filter(cluster=clusterObj).update(cluster=clusterObj,ldapDomain=ldapDomain,ldapPassword=ldapPassword,openidmAdminPassword=openidmAdminPassword,openidmMysqlPassword=openidmMysqlPassword,securityAdminPassword=securityAdminPassword,ossFsServer=ossFsServer,citrixFarm=citrixFarm,opendjAdminPassword=opendjAdminPassword,hqDatabasePassword=hqDatabasePassword,brsadm_password=brsadmPassword)
                else:
                    ssoDetails = SsoDetails.objects.filter(cluster=clusterObj).update(cluster=clusterObj,ldapDomain=ldapDomain,ldapPassword=ldapPassword,ossFsServer=ossFsServer,citrixFarm=citrixFarm,brsadm_password=brsadmPassword)
                message = "Edited Extra SSO Information, " + str(changedContent)
                logAction(userId, clusterObj, action, message)
                return fh.success()
            except Exception as e:
                logger.error("Unable to edit the SSO/LDAP Extra Details: " +str(e))
                return fh.failure()
        else:
            fh.message = "Form is invalid please try again!!!"
            return fh.display()

    else:
        return fh.display()

@login_required
def deleteSsoInfo(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "add"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete Ldap and Password Details for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    if SsoDetails.objects.filter(cluster=clusterObj.id).exists():
        ssoObj = SsoDetails.objects.get(cluster=clusterObj.id)
    try:
        ssoObj.delete()
        cursor = connection.cursor()
        message = "Deleted Extra SSO Information"
        logAction(userId, clusterObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def editTorToOSSRCCluster(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "edit"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to edit the OSSRC Attached to this Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.title = "Edit OSSRC Deployment to ENM Deployment Mapping for: " +str(clusterObj.name)
    fh.button = "Edit"
    if OssrcClusterToTorClusterMapping.objects.filter(torCluster=clusterObj.id).exists():
        clsMapObj = OssrcClusterToTorClusterMapping.objects.get(torCluster=clusterObj.id)
        fh.form = OSSRCForm(initial={'ossrcCluster' : clsMapObj.ossCluster.name,})
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        ossrcCluster = request.POST.get("ossrcCluster")
        ossrcClusterObj = Cluster.objects.get(name=ossrcCluster)
        fh.form = OSSRCForm(request.POST)
        if fh.form.is_valid():
            oldValues = [str(clsMapObj.ossCluster.name) + "##OSSRC System"]
            newValues = [str(fh.form.cleaned_data['ossrcCluster'])]
            changedContent = logChange(oldValues,newValues)
            try:
                OSSRCToTorMap = OssrcClusterToTorClusterMapping.objects.filter(torCluster=clusterObj).update(ossCluster=ossrcClusterObj)
                message = "Edited Attached OSSRC System, " + str(changedContent)
                logAction(userId, clusterObj, action, message)
                return fh.success()
            except Exception as e:
                logger.error("Unable to edit OSSRC to ENM Deployment mapping: " +str(e))
                return fh.failure()
    else:
        return fh.display()

@login_required
def deleteTorToOSSRCCluster(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Delete Tor To OSSRC Deployment for a Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    if OssrcClusterToTorClusterMapping.objects.filter(torCluster=clusterObj.id).exists():
        clsMapObj = OssrcClusterToTorClusterMapping.objects.get(torCluster=clusterObj.id)
    try:
        clsMapObj.delete()
        cursor = connection.cursor()
        message = "Deleted Attached OSSRC System"
        logAction(userId, clusterObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def editDirectAttachedStorageNas(request,clusterId):
    '''
    Used to edit the NAS attached Direct Attached storage for a deployment
    '''
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to edit Direct Attached Storage Nas for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    poolFS1 = ""

    fh.title = "Edit Direct Attached Storage Information: " +str(clusterObj.name)
    fh.button = "Edit"
    if ClusterToDASNASMapping.objects.filter(cluster=clusterObj.id).exists():
        dasNasObject = ClusterToDASNASMapping.objects.get(cluster=clusterObj.id)
        if NasStorageDetails.objects.filter(cluster=clusterId).exists():
            nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=clusterId)
            poolFS1 = str(nasStorageDtlsObj.poolFS1)
        fh.form = EditNASForm(initial={
            'nasServer' : dasNasObject.dasNasServer,
            'poolFS1' : str(poolFS1),
            })
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        nasServer = request.POST.get("nasServer")
        nasServer = str(nasServer).split("(id: ")
        nasServer = nasServer[1]
        nasServer = nasServer.replace(')','')
        nasServerObj = Server.objects.get(id=nasServer)
        fh.form = NASForm(request.POST)
        if fh.form.is_valid():
            try:
                clusterToDasNasMap = ClusterToDASNASMapping.objects.filter(cluster=clusterObj).update(dasNasServer=nasServerObj)
                poolFilesystem = NasStorageDetails.objects.filter(cluster=clusterId).update(poolFS1=request.POST.get("poolFS1"))
                return fh.success()
            except Exception as e:
                logger.error("Unable to edit deployment to NAS mapping: " +str(e))
                return fh.failure()
    else:
        return fh.display()

@login_required
def editDirectAttachedStorageSan(request,clusterId):
    '''
    '''
    userId = request.user.pk
    action = "edit"
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to edit Direct Attached Storage SAN for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.title = "Edit Network Attached Storage Information: " +str(clusterObj.name)
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    if ClusterToDASMapping.objects.filter(cluster=clusterObj.id).exists():
        dasObject = ClusterToDASMapping.objects.get(cluster=clusterObj.id)
        fh.form = DASForm(initial={
            'storage' : dasObject.storage,
            })
    fh.request = request
    fh.redirectTarget = "/dmt/clusters/" +str(clusterObj.id)+ "/details/"
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        storage = request.POST.get("storage")
        oldValues = [str(dasObject.storage) + "##SAN Storage"]
        newValues = [str(storage)]
        changedContent = logChange(oldValues,newValues)
        storageObj = Storage.objects.get(hostname=storage)
        fh.form = DASForm(request.POST)
        if fh.form.is_valid():
            try:
                clusterToStorageMap = ClusterToDASMapping.objects.filter(cluster=clusterObj).update(storage=storageObj)
                message = "Edited SAN Storage Information, " + str(changedContent)
                logAction(userId, clusterObj, action, message)
                return fh.success()
            except Exception as e:
                logger.error("Unable to edit deployment to storage mapping: " +str(e))
                return fh.failure()
    else:
        return fh.display()

@login_required
def deleteDirectAttachedStorageNas(request,clusterId):
    '''
    Used to delete the NAS applied DAS for a deployment
    '''
    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Delete the Direct Attached Storage NAS for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    dictDeletedInfo = {}
    dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(clusterObj).pk
    dictDeletedInfo["objectId"] = clusterObj.pk
    dictDeletedInfo["objectRep"] = force_unicode(clusterObj)

    if ClusterToDASNASMapping.objects.filter(cluster=clusterObj).exists():
        if ClusterToDASNASMapping.objects.filter(cluster=clusterObj).exists():
            dasNasObject = ClusterToDASNASMapping.objects.get(cluster=clusterObj)
        else:
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    if NasStorageDetails.objects.filter(cluster=clusterObj).exists():
        if NasStorageDetails.objects.filter(cluster=clusterObj).exists():
            nasStorageDtlsObj = NasStorageDetails.objects.get(cluster=clusterObj)
        else:
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    try:
        if nasStorageDtlsObj:
            nasStorageDtlsObj.delete()
        if dasNasObject:
            dasNasObject.delete()
        cursor = connection.cursor()
        message = "Deleted NAS (DAS) Storage Information"
        logAction(userId, clusterObj, action, message, dictDeletedInfo)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def deleteDirectAttachedStorageSan(request,clusterId):
    '''
     Used to delete the SAN applied DAS for a deployment
    '''
    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Delete Direct Attached Storage SAN for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    dictDeletedInfo = {}
    dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(clusterObj).pk
    dictDeletedInfo["objectId"] = clusterObj.pk
    dictDeletedInfo["objectRep"] = force_unicode(clusterObj)

    if ClusterToDASMapping.objects.filter(cluster=clusterObj).exists():
        dasObject = ClusterToDASMapping.objects.get(cluster=clusterObj)

    try:
        if dasObject:
            dasObject.delete()
        cursor = connection.cursor()
        message = "Deleted SAN Storage Information"
        logAction(userId, clusterObj, action, message, dictDeletedInfo)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

def getuniqueProducts():
    uniqueServerTypeList = ProductToServerTypeMapping.objects.values_list('product').distinct()

    productList = ()
    for type in uniqueServerTypeList:
        productList = productList + ("[\""+str(type[0])+"\", \""+str(type[0])+"\"]",)
    uniqueList = re.sub(r'\'', '', str(productList))
    uniqueList = eval(uniqueList)
    if uniqueList:
        return uniqueList
    else:
        return None

def getserverTypeInfo(searchString):
    serverTypeList = ProductToServerTypeMapping.objects.filter(product=searchString)
    list = ()
    for type in serverTypeList:
        list = list + ("[\""+str(type.serverType)+"\", \""+str(type.serverType)+"\"]",)
    typeList = re.sub(r'\'', '', str(list))
    typeList = eval(typeList)
    if typeList:
        return typeList
    else:
        return None

@login_required
@transaction.atomic
def addClusterServer(request, server_id,  macAddress, cluster_id):
    '''
    Create a server associated with a deployment
    '''
    cluster = Cluster.objects.get(id=cluster_id)
    server = Server.objects.get(id=server_id)

    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.title = "Adding Deployment Server Information"
    fh.request = request
    productType = cluster.management_server.product.name
    fh.form = ClusterServerForm(productType)
    # If the server is blade then supply an option to Add ILO
    if server.hardware_type == "blade":
        fh.button = "Next ..."
    else:
        fh.button = "Finish ..."

    if request.method == 'POST':
        fh.form = ClusterServerForm(productType,request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        try:
            if fh.form.is_valid():
                nodeType = str(request.POST.get("node_type"))
                if ClusterServer.objects.filter(cluster=cluster, node_type=nodeType):
                   fh.message = ("Node Type: " + nodeType + ", On Deployment: " +str(cluster.name)+ " is already defined, please try again")
                   return fh.display()
                if "Next ..." in request.POST:
                    # redirect to the ILO form
                    fh.redirectTarget = "/dmt/addsvr/" + str(cluster_id) + "/ilo/" + server.hostname
                if "Finish ..." in request.POST:
                    # redirect to the deployment page
                    fh.redirectTarget = "/dmt/clusters/" + str(cluster_id) + "/"
                try:
                    with transaction.atomic():
                        cs = fh.form.save(commit=False)
                        existing = ClusterServer.objects.get(server_id=server_id, cluster_id=cluster_id)
                        cs.server = server
                        cs.cluster = cluster
                        cs.id=existing.id
                        cs.save()
                        return fh.success()
                except IntegrityError:
                    return fh.failure()
            else:
                fh.message = "Form is invalid please try again!!!"
                return fh.display()
        except Exception as e:
            fh.message = "Issue with the Node List " + str(e)
            return fh.display()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addMgtServer(request, svr_id):
    '''
    The addMgtServer is used to add LITP Management Server information to the CIFWK DB
    using the CIFWK UI as input
    '''
    server = Server.objects.get(id=svr_id)

    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.form = MgtServerForm()
    fh.title = "Complete Management Server Information"
    fh.request = request
    fh.button = "Finish ..."

    if request.method == 'POST':
        fh.form = MgtServerForm(request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        if fh.form.is_valid():
            fh.redirectTarget = "/dmt/mgtsvrs/"
            try:
                with transaction.atomic():
                    ms = fh.form.save(commit=False)
                    existing = ManagementServer.objects.get(server_id=svr_id)
                    ms.server = server
                    ms.product = existing.product
                    ms.id=existing.id
                    ms.save()
                    return fh.success()
            except IntegrityError:
                return fh.failure()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addCluster(request):
    '''
    The addCluster function is used to add a deployment to the CIFWK DB using the CIFWK UI
    This function calls the getLowestAvailableTIPCAddress function in utils which
    increments the deployment tipc address by 1
    '''
    user = User.objects.get(username=str(request.user))
    tipc_addr = dmt.utils.getLowestAvailableTIPCAddress()

    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.form = ClusterForm(
            initial={
                'tipc_address': str(tipc_addr),
                'name': "Deployment-" + str(tipc_addr)})

    fh.form.fields["group"].queryset = user.groups.filter(user=user.id)
    fh.title = "Register a Deployment with a Management Server"
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    fh.redirectTarget = "/dmt/mgtsvrs/"
    cluster = None
    status = DeploymentStatusTypes.objects.get(status="IDLE")
    action = "add"
    message = "Added Deployment"
    userId = request.user.pk

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = ClusterForm(request.POST)
        fh.form.fields["group"].queryset = user.groups.filter(user=user.id)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    group = fh.form.cleaned_data['group']
                    cluster = fh.form.save(commit=False)
                    timePlus24Hours = datetime.now()+timedelta(days=1)
                    cluster.dhcp_lifetime = timePlus24Hours
                    mgtServerId = fh.form.cleaned_data['management_server']
                    mgtServerId = str(mgtServerId).split("(id: ")
                    mgtServerId = mgtServerId[1]
                    mgtServerId = mgtServerId.replace(')','')
                    mgtServer = ManagementServer.objects.get(id=mgtServerId)
                    if mgtServer.product.name == "OSS-RC":
                        layout = ClusterLayout.objects.get(name=fh.form.cleaned_data['layout'])
                        if layout.id != 3:
                            fh.message = "You must chose OSS-RC Deployment layout if you are using OSS-RC Management Server"
                            logger.error(fh.message)
                            return fh.display()

                    component = fh.form.cleaned_data['component']
                    cluster.component = component
                    # Set the CAL parameter to None as it is dependant on a DD later being added to this Deployment
                    cluster.compact_audit_logger = None
                    cluster.save()
                    if cluster.layout.name == "KVM":
                        multicastTypes = VlanMulticastType.objects.all()
                        for item in multicastTypes:
                            if "BR0" in str(item.name):
                                VlanClusterMulticast.objects.create(cluster=cluster, multicast_type=item, multicast_snooping="1", multicast_querier="1", multicast_router="2", hash_max="2048")
                            elif "BR1" in str(item.name):
                                VlanClusterMulticast.objects.create(cluster=cluster, multicast_type=item, multicast_snooping="1", multicast_querier="1", multicast_router="2", hash_max="2048")
                            elif "BR3" in str(item.name):
                                VlanClusterMulticast.objects.create(cluster=cluster, multicast_type=item, multicast_snooping="0", multicast_querier="0", multicast_router="1", hash_max="512")
                    DeploymentDatabaseProvider.objects.create(cluster=cluster)
                    fh.redirectTarget = "/dmt/clusters/" + str(cluster.id) + "/"
                    if group != None:
                        assign_perm('change_cluster_guardian', group, cluster)
                        assign_perm('delete_cluster_guardian', group, cluster)
            except IntegrityError:
                return fh.failure()
            try:
                DeploymentStatus.objects.create(cluster=cluster, status=status)
            except Exception as e:
                logger.error("Issue with adding Deployment Status to a deployment: " +str(e))
                return fh.failure()
            logAction(userId, cluster, action, message)
            call_command('create_cluster_ip_ranges')
            return fh.success()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def editDeploymentStatus (request, clusterId, StatusId, location=None):
    '''
    edit Deployment Status for a deployment
    '''
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to edit the deployment status for " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    action = "edit"
    userId = request.user.pk
    try:
        status = DeploymentStatus.objects.get(id=StatusId, cluster__id=clusterId)
    except Exception as error:
        errMsg = "Issue getting the Deployment Status with Deployment Id " + str(clusterId) + " - Error: " + str(error)
        return render_to_response("dmt/dmt_error.html", {'error': errMsg})
    fh = FormHandle()
    fh.form = EditDeploymentStatusForm(
            initial={
                'status': status.status,
                'description': status.description,
                'osDetails': status.osDetails,
                'litpVersion': status.litpVersion,
                'mediaArtifact': status.mediaArtifact,
                'packages': status.packages,
                'patches': status.patches
                })
    fh.title = "Edit Deployment Status"
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    if location != None:
        fh.redirectTarget = "/dmt/searchInstallGroup/"
    else:
        fh.redirectTarget = "/dmt/clusters/" + str(cluster.id) + "/"
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = EditDeploymentStatusForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    oldValues = [str(status.status) + "##Status",
                        str(status.description) + "##Description",
                        str(status.osDetails) + "##OS Details",
                        str(status.litpVersion) + "##LITP Version",
                        str(status.mediaArtifact) + "##ENM Version",
                        str(status.packages) + "##Packages Delivered",
                        str(status.patches) + "##OS Patches"]
                    newValues = [str(fh.form.cleaned_data['status']),str(fh.form.cleaned_data['description']),str(fh.form.cleaned_data['osDetails']),str(fh.form.cleaned_data['litpVersion']),str(fh.form.cleaned_data['mediaArtifact']),str(fh.form.cleaned_data['packages']),str(fh.form.cleaned_data['patches'])]
                    changedContent = logChange(oldValues,newValues)
                    status.status = fh.form.cleaned_data['status']
                    status.status_changed = datetime.now()
                    status.description = fh.form.cleaned_data['description']
                    status.osDetails = fh.form.cleaned_data['osDetails']
                    status.litpVersion = fh.form.cleaned_data['litpVersion']
                    status.mediaArtifact = fh.form.cleaned_data['mediaArtifact']
                    status.packages = fh.form.cleaned_data['packages']
                    status.patches = fh.form.cleaned_data['patches']
                    status.save()
            except IntegrityError:
                return fh.failure()
            message = "Edited Deployment Status, " + str(changedContent)
            logAction(userId, cluster, action, message)
            return fh.success()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def changeClusterGroupOnCluster(request, clusterId):
    '''
    The changeClusterGroup function is used to change owner of a Deployment for Permissions.
    '''
    userId = request.user.pk
    action = "edit"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to change the group on the deployment Server for " + str(clusterObj.name)
            return render(request, "dmt/dmt_error.html", {'error': error})
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.form = ChangeClusterGroupOnClusterForm()
    fh.title = "Change Group for Deployment " + str(clusterObj)
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    fh.redirectTarget = "/dmt/clusters/"

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = ChangeClusterGroupOnClusterForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    group = fh.form.cleaned_data['group']
                    oldGroup=clusterObj.group
                    if oldGroup != None:
                        dmt.utils.removePermissions(oldGroup,clusterObj)
                    if group != None:
                        dmt.utils.addPermissons(group,clusterObj)
                        clusterObj.group = group
                    else:
                        clusterObj.group = None
                    clusterObj.save(force_update=True)
                    fh.redirectTarget = "/dmt/clusters/" + str(clusterObj.id) + "/"
                    message = "Edited Group Permissions (Cluster), was \"" + str(oldGroup) + "\" now \"" + str(group) + "\""
                    logAction(userId, clusterObj, action, message)
                    return fh.success()
            except Exception as e:
                fh.message = "There was an issue changing the group on this deployment " + str(clusterObj) + ", Exception : " +str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def changeClusterGroup(request):
    '''
    The changeClusterGroup function is used to change owner of a Deployment for Permissions.
    '''
    userId = request.user.pk
    action = "edit"
    user = User.objects.get(username=str(request.user))
    ciAdmin = config.get("DMT", "ciAdmin")
    if not user.groups.filter(name=ciAdmin).exists() and not user.is_superuser:
        return render_to_response("dmt/dmt_error.html", {'error': "User not authorised to change a deployment's group, please contact CI Ex Team"})

    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.form = ChangeClusterGroupForm()
    fh.title = "Change a Deployment's Group Permissions"
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    fh.redirectTarget = "/dmt/clusters/"

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = ChangeClusterGroupForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    group = fh.form.cleaned_data['group']
                    cluster = fh.form.cleaned_data['cluster']
                    oldGroup=cluster.group
                    if oldGroup != None:
                        dmt.utils.removePermissions(oldGroup,cluster)
                    dmt.utils.addPermissons(group,cluster)
                    cluster.group = group
                    cluster.save(force_update=True)
                    fh.redirectTarget = "/dmt/clusters/" + str(cluster.id) + "/"
                    message = "Edited Group Permissions (Admin), was \"" + str(oldGroup) + "\" now \"" + str(group) + "\""
                    logAction(userId, cluster, action, message)
                    return fh.success()
            except Exception as e:
                fh.message = "There was an issue changing the group on this deployment " + str(fh.form.cleaned_data['cluster']) + ", Exception : " +str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            return fh.failure()
    else:
        pageHitCounter("ChangeClusterGroup", None, str(request.user))
        return fh.display()

@login_required
@transaction.atomic
def deleteClusterMulticasts(request, clusterId, task):
    '''
    The deleteClusterMulticasts is called to delete the Multicasts information from the deployment.
    '''
    userId = request.user.pk
    action = "delete"
    ### TODO need to investigate message popup to handle exception on deleting from template
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such deployment ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete multicast information for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    if ClusterMulticast.objects.filter(cluster_id=clusterObj.id).exists():
        clusterMulticast = ClusterMulticast.objects.get(cluster_id=clusterObj.id)
    else:
        message = "No Multicast Information can be found for saving, contact Admin if the issue persists"
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

    if IpAddress.objects.filter(id=clusterMulticast.enm_messaging_address_id).exists():
        enmMesAddressObj = IpAddress.objects.get(id=clusterMulticast.enm_messaging_address_id)
    else:
        message = "No Multicast Information can be found for ENM Messaging Address, contact Admin if the issue persists"
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

    if IpAddress.objects.filter(id=clusterMulticast.udp_multicast_address_id).exists():
        udpAddressObj = IpAddress.objects.get(id=clusterMulticast.udp_multicast_address_id)
    else:
        message = "No Multicast Information can be found for UDP Multicast Address, contact Admin if the issue persists"
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    try:
        clusterMulticast.delete()
        enmMesAddressObj.delete()
        udpAddressObj.delete()
        cursor = connection.cursor()
        message = "Deleted Multicast Information"
        logAction(userId, clusterObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        message = "Issue deleting some of the multicast info for Deployment " + str(clusterObj.name) + " Exception :  " + str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def clusterMulticasts(request, clusterId, task, populate):
    '''
    The clusterMulticasts is called to add the Multicasts information to the deployment.
    '''
    # Create a FormHandle to handle form post-processing
    userId = request.user.pk
    action = task
    fh = FormHandle()
    taskTitle = task.title()
    fh.title = str(taskTitle) + " Multicasts Information to Deployment"
    fh.request = request
    fh.button = "Save & Exit ..."
    if task != "edit":
        if populate == "no":
            fh.button3 = "Auto Populate"
        else:
            fh.button3 = "Clear all Fields"
    fh.button4 = "Cancel..."
    fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such deployment ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        fh.message = message
        return fh.display()
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to update Multicast information for Deployment: " +str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    if task == "edit":
        if ClusterMulticast.objects.filter(cluster_id=clusterId).exists():
            clusterMulticastObj = ClusterMulticast.objects.get(cluster_id=clusterId)
        else:
            message = "No Multicast Info Assigned to deployment: " + str(clusterId) + ". Exception: " + str(e)
            logger.error(message)
            fh.message = message
            return fh.display()

    if request.method == 'POST':
        if "Cancel..." in request.POST:
            return fh.success()
        if "Auto Populate" in request.POST:
            return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/multicast/add/yes/")
        if "Clear all Fields" in request.POST:
             return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/multicast/add/no/")

        fh.form = ClusterMulticastForm(request.POST)
        fh.redirectTarget = "/dmt/clusters/" + str(clusterObj.id) + "/details/"
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested multicasts and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    if task == "edit":
                        clusterMulticastObj = ClusterMulticast.objects.get(cluster_id=clusterId)
                        oldValues = [str(clusterMulticastObj.enm_messaging_address.address) + "##ENM Messaging Address",
                            str(clusterMulticastObj.udp_multicast_address.address) + "##UDP Multi Address",
                            str(clusterMulticastObj.enm_messaging_port) + "##ENM Messaging Port",
                            str(clusterMulticastObj.udp_multicast_port) + "##UDP Multi Port"]
                    enmMesAddress = fh.form.cleaned_data['enm_mes_address']
                    udpMultiAddress = fh.form.cleaned_data['udp_multi_address']
                    enmMesPort = fh.form.cleaned_data['enm_mes_port']
                    udpMultiPort = fh.form.cleaned_data['udp_multi_port']
                    if task == "edit":
                        clusterMulticastObj = ClusterMulticast.objects.get(cluster_id=clusterId)
                        oldValues = [str(clusterMulticastObj.enm_messaging_address.address) + "##ENM Messaging Address",
                            str(clusterMulticastObj.udp_multicast_address.address) + "##UDP Multi Address",
                            str(clusterMulticastObj.enm_messaging_port) + "##ENM Messaging Port",
                            str(clusterMulticastObj.udp_multicast_port) + "##UDP Multi Port"]
                        newValues = [str(enmMesAddress),str(udpMultiAddress),str(enmMesPort),str(udpMultiPort)]
                        changedContent = logChange(oldValues,newValues)
                        returnedValue,message = dmt.utils.editClusterMulticast(enmMesAddress,udpMultiAddress,enmMesPort,udpMultiPort,clusterId)
                    else:
                        returnedValue,message = dmt.utils.createClusterMulticast(enmMesAddress,udpMultiAddress,enmMesPort,udpMultiPort,clusterId)
                    if returnedValue == "1":
                        fh.message = "Error: " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if action == "edit":
                            message = "Edited Multicast Information, " + str(changedContent)
                        else:
                            message = "Added Multicast Information"
                        logAction(userId, clusterObj, action, message)
                        return fh.success()
            except IntegrityError as e:
                fh.message = "Failed to add multicast addresses to the deployment " + str(clusterObj.name) + ". Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Failed to add multicast information to deployment"
            logger.error(fh.message)
            return fh.display()
    else:
        if task == "edit":
            enmMessagingAddress = clusterMulticastObj.enm_messaging_address.address
            udpMulticastAddress = clusterMulticastObj.udp_multicast_address.address
            enmMessagingGroupPort = clusterMulticastObj.enm_messaging_port
            udpMulticastPort = clusterMulticastObj.udp_multicast_port
        else:
            try:
                enmMessagingAddress = dmt.utils.getMulticastIpAddress("messagingAddress")
                udpMulticastAddress = dmt.utils.getMulticastIpAddress("udpAddress")
                mcasts = dmt.virtualMCast.getAvailableMulticastPorts()
                enmMessagingGroupPort = mcasts['msgPort']
                udpMulticastPort = mcasts['udpPort']
            except Exception as e:
                fh.message = "There was an issue generating an IP address for the multicast addresses, Exception : " +str(e)
                logger.error(fh.message)
                return fh.display()

        if populate == "yes":
            fh.form = ClusterMulticastForm(
                    initial={
                        'enm_mes_address': str(enmMessagingAddress),
                        'enm_mes_port': str(enmMessagingGroupPort),
                        'udp_multi_address':str(udpMulticastAddress),
                        'udp_multi_port': str(udpMulticastPort),
                        }
                    )
        else:
            fh.form = ClusterMulticastForm()
        return fh.display()

@login_required
@transaction.atomic
def databaseVip(request, clusterId, task):
    '''
    The databaseVip is called to add the database ip information to the deployment.
    '''
    userId = request.user.pk
    action = task
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    taskTitle = task.title()
    fh.title = str(taskTitle) + " Database VIP Information"
    fh.request = request
    fh.button = "Save & Exit ..."
    fh.button4 = "Cancel..."
    fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such deployment ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        fh.message = message
        return fh.display()
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Update Database VIP Information for this Deployment: " +str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    if task == "edit":
        if DatabaseVips.objects.filter(cluster_id=clusterId).exists():
            databaseVipObj = DatabaseVips.objects.get(cluster_id=clusterId)
        else:
            message = "No Vip Info Assigned to deployment: " + str(clusterId) + ". Exception: " + str(e)
            logger.error(message)
            fh.message = message
            return fh.display()

    if request.method == 'POST':
        if "Cancel..." in request.POST:
            return fh.success()
        fh.form = DatabaseVipForm(request.POST)
        fh.redirectTarget = "/dmt/clusters/" + str(clusterObj.id) + "/details/"
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested multicasts and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    postgresAddress = fh.form.cleaned_data['postgresAddress']
                    versantAddress = fh.form.cleaned_data['versantAddress']
                    mysqlAddress = fh.form.cleaned_data['mysqlAddress']
                    opendjAddress = fh.form.cleaned_data['opendjAddress']
                    opendjAddress2 = fh.form.cleaned_data['opendjAddress2']
                    if opendjAddress2 == '':
                        opendjAddress2 = None
                    jmsAddress = fh.form.cleaned_data['jmsAddress']
                    eSearchAddress = fh.form.cleaned_data['eSearchAddress']
                    neo4jAddress1 = fh.form.cleaned_data['neo4jAddress1']
                    neo4jAddress2 = fh.form.cleaned_data['neo4jAddress2']
                    neo4jAddress3 = fh.form.cleaned_data['neo4jAddress3']
                    gossipRouterAddress1 = fh.form.cleaned_data['gossipRouterAddress1']
                    gossipRouterAddress2 = fh.form.cleaned_data['gossipRouterAddress2']
                    eshistoryAddress = fh.form.cleaned_data['eshistoryAddress']
                    if task == "edit":
                        oldPostgresAddress = oldVersantAddress = oldMysqlAddress = "NOT SET"
                        oldOpendjAddress = oldOpendjAddress2 = oldJmsAddress = "NOT SET"
                        oldESearchAddress = oldNeo4jAddress1 = "NOT SET"
                        oldNeo4jAddress2 = oldNeo4jAddress3 = "NOT SET"
                        oldGossipRouterAddress1 = oldGossipRouterAddress2 = "NOT SET"
                        oldEshistoryAddress = "NOT SET"

                        databaseVipObj = DatabaseVips.objects.get(cluster_id=clusterId)

                        if not databaseVipObj.postgres_address == None:
                            oldPostgresAddress = str(databaseVipObj.postgres_address.address)

                        if not databaseVipObj.versant_address == None:
                            oldVersantAddress = str(databaseVipObj.versant_address.address)

                        if not databaseVipObj.mysql_address == None:
                            oldMysqlAddress = str(databaseVipObj.mysql_address.address)

                        if not databaseVipObj.opendj_address.address == None:
                            oldOpendjAddress = str(databaseVipObj.opendj_address.address)

                        if not databaseVipObj.opendj_address2 == None:
                            oldOpendjAddress2 = str(databaseVipObj.opendj_address2.address)

                        if not databaseVipObj.jms_address.address == None:
                            oldJmsAddress = str(databaseVipObj.jms_address.address)

                        if not databaseVipObj.eSearch_address.address == None:
                            oldESearchAddress = str(databaseVipObj.eSearch_address.address)

                        if not databaseVipObj.neo4j_address1 == None:
                            oldNeo4jAddress1 = str(databaseVipObj.neo4j_address1.address)

                        if not databaseVipObj.neo4j_address2 == None:
                            oldNeo4jAddress2 = str(databaseVipObj.neo4j_address2.address)

                        if not databaseVipObj.neo4j_address3 == None:
                            oldNeo4jAddress3 = str(databaseVipObj.neo4j_address3.address)

                        if not databaseVipObj.gossipRouter_address1 == None:
                            oldGossipRouterAddress1 = str(databaseVipObj.gossipRouter_address1.address)

                        if not databaseVipObj.gossipRouter_address2 == None:
                            oldGossipRouterAddress2 = str(databaseVipObj.gossipRouter_address2.address)

                        if not databaseVipObj.eshistory_address == None:
                            eshistoryAddress = databaseVipObj.eshistory_address.address

                        oldValues = [oldPostgresAddress + "##Postgres Address",
                            oldVersantAddress + "##Versant Address",
                            oldMysqlAddress + "##MySQL Address",
                            oldOpendjAddress + "##Opendj Address 1",
                            oldOpendjAddress2 + "##Opendj Address 2",
                            oldJmsAddress + "##JMS Address Address",
                            oldESearchAddress + "##ESearch Address",
                            oldNeo4jAddress1 + "##Neo4j Address 1",
                            oldNeo4jAddress2 + "##Neo4j Address 2",
                            oldNeo4jAddress3 + "##Neo4j Address 3",
                            oldGossipRouterAddress1 + "##Gossip Router Address 1",
                            oldGossipRouterAddress2 + "##Gossip Router Address 2",
                            oldEshistoryAddress + "##Eshistory Address"]
                        newValues = [str(postgresAddress),str(versantAddress),str(mysqlAddress),str(opendjAddress),str(opendjAddress2),str(jmsAddress),str(eSearchAddress),str(neo4jAddress1),str(neo4jAddress2),str(neo4jAddress3),str(gossipRouterAddress1),str(gossipRouterAddress2),str(eshistoryAddress)]
                        addressList = filter(None,newValues)
                        duplicates = dmt.utils.getDuplicatesInList(addressList)
                        if len(duplicates) > 0:
                            raise Exception("Duplicate IP Info "+str(duplicates))
                        changedContent = logChange(oldValues,newValues)
                        returnedValue,message = dmt.utils.editDatabaseVip(postgresAddress,versantAddress,mysqlAddress,opendjAddress,opendjAddress2,jmsAddress,eSearchAddress,neo4jAddress1,neo4jAddress2,neo4jAddress3,gossipRouterAddress1,gossipRouterAddress2,eshistoryAddress,clusterId)
                    else:
                        returnedValue,message = dmt.utils.createDatabaseVip(postgresAddress,versantAddress,mysqlAddress,opendjAddress,opendjAddress2,jmsAddress,eSearchAddress,neo4jAddress1,neo4jAddress2,neo4jAddress3,gossipRouterAddress1,gossipRouterAddress2,eshistoryAddress,clusterId)
                    if returnedValue == "1":
                        fh.message = "Error: " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if action == "edit":
                            message = "Edited Database VIP Information, " + str(changedContent)
                        else:
                            message = "Added Database VIP Information"
                        logAction(userId, clusterObj, action, message)
                        return fh.success()
            except Exception as e:
                fh.message = "Failed to add database VIP address to deployment " + str(clusterObj.name) + ". Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Failed to add database VIP address information to deployment"
            logger.error(fh.message)
            return fh.display()
    else:
        if task == "edit":
            postgresAddress = str(databaseVipObj.postgres_address.address)
            versantAddress = str(databaseVipObj.versant_address.address)
            mysqlAddress = str(databaseVipObj.mysql_address.address)
            if ( databaseVipObj.opendj_address_id != None ):
                opendjAddress = str(databaseVipObj.opendj_address.address)
            else:
                opendjGateway,opendjAddress,opendjBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipOpendj")

            if ( databaseVipObj.opendj_address2_id != None ):
                opendjAddress2 = str(databaseVipObj.opendj_address2.address)
            else:
                opendjGateway2,opendjAddress2,opendjBitmask2 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipOpendj2")

            if ( databaseVipObj.jms_address_id != None ):
                jmsAddress = str(databaseVipObj.jms_address.address)
            else:
                jmsGateway,jmsAddress,jmsBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipJms")

            if ( databaseVipObj.eSearch_address_id != None ):
                eSearchAddress = str(databaseVipObj.eSearch_address.address)
            else:
                eSearchGateway,eSearchAddress,eSearchBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipElasticSearch")

            if ( databaseVipObj.neo4j_address1_id != None ):
                neo4jAddress1 = str(databaseVipObj.neo4j_address1.address)
            else:
                neo4jGateway1,neo4jAddress1,neo4jBitmask1 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipNeo4j1")

            if ( databaseVipObj.neo4j_address2_id != None ):
                neo4jAddress2 = str(databaseVipObj.neo4j_address2.address)
            else:
                 neo4jGateway2,neo4jAddress2,neo4jBitmask2 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipNeo4j2")

            if ( databaseVipObj.neo4j_address3_id != None ):
                neo4jAddress3 = str(databaseVipObj.neo4j_address3.address)
            else:
                neo4jGateway3,neo4jAddress3,neo4jBitmask3 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipNeo4j3")

            if ( databaseVipObj.gossipRouter_address1_id != None ):
                gossipRouterAddress1 = str(databaseVipObj.gossipRouter_address1.address)
            else:
                gossipRouterGateway1,gossipRouterAddress1,gossipRouterBitmask1 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipGossipRouter1")

            if ( databaseVipObj.gossipRouter_address2_id != None ):
                gossipRouterAddress2 = str(databaseVipObj.gossipRouter_address2.address)
            else:
                gossipRouterGateway2,gossipRouterAddress2,gossipRouterBitmask2 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipGossipRouter2")

            if ( databaseVipObj.eshistory_address_id != None ):
                eshistoryAddress = str(databaseVipObj.eshistory_address.address)
            else:
                eshistoryGateway,eshistoryAddress,eshistoryBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipEshistory")

            fh.form = DatabaseVipForm(
                    initial={
                        'postgresAddress': str(postgresAddress),
                        'versantAddress': str(versantAddress),
                        'mysqlAddress': str(mysqlAddress),
                        'opendjAddress': str(opendjAddress),
                        'opendjAddress2': str(opendjAddress2),
                        'jmsAddress': str(jmsAddress),
                        'eSearchAddress': str(eSearchAddress),
                        'neo4jAddress1': str(neo4jAddress1),
                        'neo4jAddress2': str(neo4jAddress2),
                        'neo4jAddress3': str(neo4jAddress3),
                        'gossipRouterAddress1': str(gossipRouterAddress1),
                        'gossipRouterAddress2': str(gossipRouterAddress2),
                        'eshistoryAddress': str(eshistoryAddress),
                        }
                    )
        else:
            postgresGateway,postgresAddress,postgresBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipPostgres")
            versantGateway,versantAddress,versantBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipVersant")
            mysqlGateway,mysqlAddress,mysqlBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipMysql")
            opendjGateway,opendjAddress,opendjBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipOpendj")
            opendjGateway2,opendjAddress2,opendjBitmask2 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipOpendj2")
            jmsGateway,jmsAddress,jmsBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipJms")
            eSearchGateway,eSearchAddress,eSearchBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipElasticSearch")
            neo4jGateway1,neo4jAddress1,neo4jBitmask1 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipNeo4j1")
            neo4jGateway2,neo4jAddress2,neo4jBitmask2 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipNeo4j2")
            neo4jGateway3,neo4jAddress3,neo4jBitmask3 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipNeo4j3")
            gossipRouterGateway1,gossipRouterAddress1,gossipRouterBitmask1 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipGossipRouter1")
            gossipRouterGateway2,gossipRouterAddress2,gossipRouterBitmask2 = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipGossipRouter2")
            eshistoryGateway,eshistoryAddress,eshistoryBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_DBVipEshistory")
            fh.form = DatabaseVipForm(
                    initial={
                        'postgresAddress': str(postgresAddress),
                        'versantAddress': str(versantAddress),
                        'mysqlAddress': str(mysqlAddress),
                        'opendjAddress': str(opendjAddress),
                        'opendjAddress2': str(opendjAddress2),
                        'jmsAddress': str(jmsAddress),
                        'eSearchAddress': str(eSearchAddress),
                        'neo4jAddress1': str(neo4jAddress1),
                        'neo4jAddress2': str(neo4jAddress2),
                        'neo4jAddress3': str(neo4jAddress3),
                        'gossipRouterAddress1': str(gossipRouterAddress1),
                        'gossipRouterAddress2': str(gossipRouterAddress2),
                        'eshistoryAddress': str(eshistoryAddress),
                        }
                    )
        return fh.display()

@login_required
@transaction.atomic
def deleteDatabaseVip(request, clusterId, task):
    '''
    The deleteClusterMulticasts is called to delete the Multicasts information from the deployment.
    '''
    ### TODO need to investigate message popup to handle exception on deleting from template
    userId = request.user.pk
    action = "delete"
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "No such deployment ID: " + str(clusterId) + ". Exception: " + str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete database VIP information from Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    if DatabaseVips.objects.filter(cluster_id=clusterObj.id).exists():
        databaseVipObj = DatabaseVips.objects.get(cluster_id=clusterObj.id)
    else:
        message = "No database Vip address Information can be found for saving, contact Admin if the issue persists"
        logger.error(message)
        return ("1",message)

    if IpAddress.objects.filter(id=databaseVipObj.postgres_address_id).exists():
       postgresAddressObj = IpAddress.objects.get(id=databaseVipObj.postgres_address_id)
    else:
        postgresAddressObj = None

    if IpAddress.objects.filter(id=databaseVipObj.versant_address_id).exists():
        versantAddressObj = IpAddress.objects.get(id=databaseVipObj.versant_address_id)
    else:
        versantAddressObj = None

    if IpAddress.objects.filter(id=databaseVipObj.mysql_address_id).exists():
        mysqlAddressObj = IpAddress.objects.get(id=databaseVipObj.mysql_address_id)
    else:
        mysqlAddressObj = None

    if IpAddress.objects.filter(id=databaseVipObj.opendj_address_id).exists():
        opendjAddressObj = IpAddress.objects.get(id=databaseVipObj.opendj_address_id)
    else:
        opendjAddressObj = None

    if IpAddress.objects.filter(id=databaseVipObj.opendj_address2_id).exists():
        opendjAddressObj2 = IpAddress.objects.get(id=databaseVipObj.opendj_address2_id)
    else:
        opendjAddressObj2 = None

    if IpAddress.objects.filter(id=databaseVipObj.jms_address_id).exists():
        jmsAddressObj = IpAddress.objects.get(id=databaseVipObj.jms_address_id)
    else:
        jmsAddressObj = None

    if IpAddress.objects.filter(id=databaseVipObj.eSearch_address_id).exists():
        eSearchAddressObj = IpAddress.objects.get(id=databaseVipObj.eSearch_address_id)
    else:
        eSearchAddressObj = None

    if IpAddress.objects.filter(id=databaseVipObj.neo4j_address1_id).exists():
        neo4jAddress1Obj = IpAddress.objects.get(id=databaseVipObj.neo4j_address1_id)
    else:
        neo4jAddress1Obj = None

    if IpAddress.objects.filter(id=databaseVipObj.neo4j_address2_id).exists():
        neo4jAddress2Obj = IpAddress.objects.get(id=databaseVipObj.neo4j_address2_id)
    else:
        neo4jAddress2Obj = None

    if IpAddress.objects.filter(id=databaseVipObj.neo4j_address3_id).exists():
        neo4jAddress3Obj = IpAddress.objects.get(id=databaseVipObj.neo4j_address3_id)
    else:
        neo4jAddress3Obj = None

    if IpAddress.objects.filter(id=databaseVipObj.gossipRouter_address1_id).exists():
        gossipRouterAddress1Obj = IpAddress.objects.get(id=databaseVipObj.gossipRouter_address1_id)
    else:
        gossipRouterAddress1Obj = None

    if IpAddress.objects.filter(id=databaseVipObj.gossipRouter_address2_id).exists():
        gossipRouterAddress2Obj = IpAddress.objects.get(id=databaseVipObj.gossipRouter_address2_id)
    else:
        gossipRouterAddress2Obj = None

    if IpAddress.objects.filter(id=databaseVipObj.eshistory_address_id).exists():
        eshistoryAddressObj = IpAddress.objects.get(id=databaseVipObj.eshistory_address_id)
    else:
        eshistoryAddressObj = None

    try:
        databaseVipObj.delete()
        if postgresAddressObj != None:
            postgresAddressObj.delete()
        if versantAddressObj != None:
            versantAddressObj.delete()
        if mysqlAddressObj != None:
            mysqlAddressObj.delete()
        if opendjAddressObj != None:
            opendjAddressObj.delete()
        if opendjAddressObj2 != None:
            opendjAddressObj2.delete()
        if jmsAddressObj != None:
            jmsAddressObj.delete()
        if eSearchAddressObj != None:
            eSearchAddressObj.delete()
        if neo4jAddress1Obj != None:
            neo4jAddress1Obj.delete()
        if neo4jAddress2Obj != None:
            neo4jAddress2Obj.delete()
        if neo4jAddress3Obj != None:
            neo4jAddress3Obj.delete()
        if gossipRouterAddress1Obj != None:
            gossipRouterAddress1Obj.delete()
        if gossipRouterAddress2Obj != None:
            gossipRouterAddress2Obj.delete()
        if eshistoryAddressObj != None:
            eshistoryAddressObj.delete()

        cursor = connection.cursor()
        message = "Delete Database VIP Information"
        logAction(userId, clusterObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        message = "Issue deleting some of the Database VIP info for Deployment " + str(clusterObj.name) + " Exception :  " + str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def addMulticasts(request, ServicesClusterId):
    '''
    The addMulticasts is called to add the Multicasts information to the deployment.
    '''
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.title = "Add Messaging Group and Multicasts Information to Deployment"
    fh.request = request
    fh.button = "Submit ..."
    try:
        ServiceCls = ServicesCluster.objects.get(id=ServicesClusterId)
    except Exception as e:
        logger.error("No such deployment ID: " + ServicesClusterId + " ; " + str(e))
        fh.failMessage = "No such deployment Id: " + ServicesClusterId
        return fh.failure()

    if request.method == 'POST':
        fh.form = MulticastForm(request.POST)
        fh.redirectTarget = "/dmt/clusters/"+str(ServiceCls.cluster_id)+"/details/"
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested multicasts and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    defaultAddressIpObj = IpAddress.objects.create(\
                            address=fh.form.cleaned_data['default_address'],\
                            ipType="multicast_" + str(ServicesClusterId))
                    messagingAddressIpObj = IpAddress.objects.create(\
                            address=fh.form.cleaned_data['messaging_group_address'],\
                            ipType="multicast_" + str(ServicesClusterId))
                    udpAddressIpObj =  IpAddress.objects.create(\
                            address=fh.form.cleaned_data['udp_mcast_address'],\
                            ipType="multicast_" + str(ServicesClusterId))
                    mpingAddressIpObj = IpAddress.objects.create(\
                            address=fh.form.cleaned_data['mping_mcast_address'],\
                            ipType="multicast_" + str(ServicesClusterId))
                    multicastObj = Multicast.objects.create(\
                        ipMapDefaultAddress=defaultAddressIpObj,\
                        ipMapMessagingGroupAddress=messagingAddressIpObj,\
                        ipMapUdpMcastAddress=udpAddressIpObj,\
                        udp_mcast_port=fh.form.cleaned_data['udp_mcast_port'],\
                        ipMapMpingMcastAddress=mpingAddressIpObj,\
                        mping_mcast_port=fh.form.cleaned_data['mping_mcast_port'],\
                        default_mcast_port=fh.form.cleaned_data['default_mcast_port'],\
                        messaging_group_port=fh.form.cleaned_data['messaging_group_port'],\
                        public_port_base=fh.form.cleaned_data['public_port_base'],\
                        service_cluster=ServiceCls)
                    return fh.success()
            except IntegrityError as e:
                fh.message = "Failed to add multicast addresses to JBOSS cluster " + str(ServicesClusterId) + " Exception : " + str(e)
                logger.error(fh.failMessage)
                return fh.display()
        else:
            fh.message = "Failed to add multicast information"
            logger.error(fh.failMessage)
            return fh.display()
    else:
        try:
            defaultAddress = dmt.utils.getMulticastIpAddress("defaultAddress")
            messagingAddress = dmt.utils.getMulticastIpAddress("messagingAddress")
            udpAddress = dmt.utils.getMulticastIpAddress("udpAddress")
            mpingAddress = dmt.utils.getMulticastIpAddress("mpingAddress")
            mcasts = dmt.mcast.getAvailableMulticasts()
        except Exception as e:
            fh.message = "There was an issue generating an IP address for the multicast addresses, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
        fh.form = MulticastForm(
                initial={
                    'default_address': str(defaultAddress),
                    'messaging_group_address': str(messagingAddress),
                    'udp_mcast_address': str(udpAddress),
                    'udp_mcast_port': str(mcasts['udp_mcast_port']),
                    'mping_mcast_address': str(mpingAddress),
                    'default_mcast_port':str(mcasts['default_mcast_port']),
                    'mping_mcast_port': str(mcasts['mping_mcast_port']),
                    'messaging_group_port': str(mcasts['messaging_group_port']),
                    'public_port_base': str(mcasts['public_port_base']),
                    }
                )
        return fh.display()

@login_required
def deleteMulticasts(request, ServicesClusterId):
    '''
    Used to delete the Multicast information according to the Service ClusterId Given
    Parameter:
        ServicesClusterId = id of the deployment which is attached to the Multicast information
    '''
    multicastObj = Multicast.objects.get(service_cluster_id=ServicesClusterId)
    defaultAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapDefaultAddress_id)
    messagingAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapMessagingGroupAddress_id)
    udpAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapUdpMcastAddress_id)
    mpingAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapMpingMcastAddress_id)
    clusterId = multicastObj.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Delete the Multicast info on this deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    try:
        defaultAddressIpObj.delete()
        messagingAddressIpObj.delete()
        udpAddressIpObj.delete()
        mpingAddressIpObj.delete()
        multicastObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

def getNodeListOfCluster(clusterId, serverString=None):
    '''
    The getNodeListOfCluster Function is used to build up a node list using the deployment id
    in from of a tuple for use be the CheckboxSelectMultiple choices widget
    This function is called by the add service and update service Group functions
    '''
    if serverString:
        nodeList = ClusterServer.objects.filter(cluster_id=clusterId,node_type__contains=serverString)
    else:
        nodeList = ClusterServer.objects.filter(cluster_id=clusterId)
    list = ()
    for node in nodeList:
        if "FS" not in node.node_type:
             list = list + ("[\""+str(node.node_type)+"\", \""+str(node.node_type)+"\"]",)
    nodeList = re.sub(r'\'', '', str(list))
    nodeList = eval(nodeList)
    if nodeList:
        return nodeList
    else:
        return None

def getPackageList(serviceGroup,edit):
    '''
    The getPackageList function builds up the tuple thats need to display choices on the web form
    '''
    if edit == True:
        serviceGroupPackageMap = ServiceGroupPackageMapping.objects.filter(serviceGroup=serviceGroup)
        packageList = []
        for sg in serviceGroupPackageMap:
            packageList.append(sg.package)
    else:
        packageList = Package.objects.all().exclude(hide=True)
    list = ()
    for package in packageList:
        if "ERICtest" not in package.name:
            list = list + ("[\""+str(package.name)+"\", \""+str(package.name)+"\"]",)
            packageList = re.sub(r'\'', '', str(list))
            packageList = eval(packageList)
    if packageList:
        return packageList
    else:
        return None

@login_required
@transaction.atomic
def addServiceGroup(request, clusterId, serviceClusterId):
    '''
    The addServerGroup is called to add the group to the deployment
    Note this section can be depricated once KVM is up and running
    '''

    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to add a Service Group for " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.title = "Add Service Unit to the Group"
    fh.request = request
    fh.button = "Next ..."
    fh.redirectTarget = "/dmt/clusters/"+str(clusterId)+"/details/"
    serviceClr = ServicesCluster.objects.get(id=serviceClusterId)
    nodeList = getNodeListOfCluster(clusterId)
    if nodeList == None:
        message = "True"
        fh.redirectTarget = ("/dmt/addsvr/" + str(cluster.id) + "/" + str(message))
        return fh.success()

    def updateForm(request,fh,serviceClr,nodeList):
        '''
        This inner def is called multiple time with the outer def
        '''
        if serviceClr.name == "LSB Service Cluster":
            fh.form = LSBServiceForm(nodeList,initial={'cluster_type': str(serviceClr.name), })
        else:
            fh.form = ServiceGroupSelectForm(nodeList,initial={'cluster_type': str(serviceClr.name), })
        return fh.display()

    if request.method == 'POST':
        fh.form = ServiceGroupForm(request.POST)
        serviceGroup = ServiceGroup.objects.filter(service_cluster_id=serviceClr,name=request.POST.get('name'))
        if not serviceGroup:
            '''Service Group Name does not exist continue'''
            # validate the form so that the cleaned_data gets populated, then we can get the
            # requested name and define our redirect URL
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        nodesSelected = request.POST.getlist('node_list')
                        nodesSelected = nodesSelected[::-1]
                        node_list = ""
                        for node in nodesSelected:
                            if node_list == "":
                                node_list = str(node)
                            else:
                                node_list = str(node) + "," + node_list
                        name = request.POST.get("name")
                        cluster_type = request.POST.get("cluster_type")
                        returnedValue = dmt.utils.savedServiceGroupInstance(name,cluster_type,node_list,serviceClr)
                        if returnedValue == 1:
                            fh.form = ServiceGroupSelectForm(nodeList)
                            fh.message = ("There was an issue saving the form, Please Try again")
                            return fh.display()
                        else:
                            return fh.success()
                except IntegrityError as e:
                    fh.form = ServiceGroupSelectForm(nodeList)
                    fh.message = ("There was an issue saving the form, Please Try again")
                    return fh.display()
            else:
                respose = updateForm(request,fh,serviceClr,nodeList)
                return fh.failure()
        else:
            fh.message = ("The Service Group Name: " + str(request.POST.get('name')) +
                           " is already assigned to this deployment, please choose again ")
            respose = updateForm(request,fh,serviceClr,nodeList)
            return respose
    else:
        respose = updateForm(request,fh,serviceClr,nodeList)
        return respose

@login_required
@transaction.atomic
def updateServiceGroup(request, groupName, groupId):
    '''
    The updateServiceGroup updates the Service Group table via the UI
    '''
    fh = FormHandle()
    fh.title = "Update Cluster Service Group"
    fh.request = request
    fh.button = "Finish..."

    serviceGroup = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroup.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Update Service Group for Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    if request.method == 'POST':
        fh.form = ServiceGroupForm(request.POST, instance=serviceGroup)
        if fh.form.is_valid():
            fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"
            try:
                with transaction.atomic():
                    serviceGroup.node_list = request.POST.getlist('node_list')
                    serviceGroup.node_list = serviceGroup.node_list[::-1]
                    node_list = ""
                    for node in serviceGroup.node_list:
                        if node_list == "":
                            node_list = str(node)
                        else:
                            node_list = str(node) + "," + node_list
                    serviceGroup.node_list = node_list
                    serviceGroup.save(force_update=True)
                    return fh.success()
            except IntegrityError:
                return fh.failure()
        else:
            return fh.failure()
    else:
        nodeList = getNodeListOfCluster(clusterId)
        fh.form = ServiceGroupUpdateForm(nodeList,initial={'name': serviceGroup.name, 'cluster_type': serviceGroup.cluster_type,})
        return fh.display()



@login_required
@transaction.atomic
def addServiceGroupCredentials(request, groupName, groupId):
    '''
    The addServiceGroupCredentials: adds Credentials to the Service Group table via the UI
    '''
    fh = FormHandle()
    fh.title = "Add Cluster Service Group Credentials: " + str(groupName)
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Save & Add Another"

    serviceGroup = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroup.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to add Service Group Credentials for Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    if request.method == 'POST':
        fh.form = ServiceGroupCredentialsForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    username=fh.form.cleaned_data['username']
                    password=fh.form.cleaned_data['password']
                    type=fh.form.cleaned_data['credentialType']
                    credential = Credentials.objects.create(username=username, password=password, credentialType=type)
                    dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ServGrpCredMap = ServiceGroupCredentialMapping.objects.create(service_group=serviceGroup, credentials=credential, signum=str(request.user), date_time=dateTime)
            except Exception as e:
                logger.error("Error with Adding ServiceGroupCredentialsMapping " + str(e))
                return fh.failure()
            if "Save & Exit..." in request.POST:
                return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
            else:
                return HttpResponseRedirect("/dmt/addServiceGroupCredentials/" + str(groupName) + "/"+ str(groupId) +"/")
        else:
            return fh.failure()
    else:
        fh.form = ServiceGroupCredentialsForm()
        return fh.display()


@login_required
@transaction.atomic
def updateServiceGroupCredentials(request, groupName, groupId):
    '''
    The updateServiceGroupCredentials: updates the Service Group Credentials table via the UI
    '''
    ServGrpCredMapList = []
    fh = FormHandle()
    fh.title = "Update Cluster Service Group Credentials: " + str(groupName)
    fh.request = request
    fh.button = "Finish"
    fh.button2 = "Cancel"

    serviceGroup = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroup.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Update Service Group Credentials for Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    ServGrpCredMapList = ServiceGroupCredentialMapping.objects.filter(service_group__id=serviceGroup.id)

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        fh.form = UpdateServiceGroupCredentialsForm(request.POST, credentials=ServGrpCredMapList)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    counter = 1
                    for cred in ServGrpCredMapList:
                        username=fh.form.cleaned_data['username_' + str(counter)]
                        password=fh.form.cleaned_data['password_' + str(counter)]
                        type=fh.form.cleaned_data['credentialType_' + str(counter)]
                        credential = Credentials.objects.get(id=cred.credentials.id)
                        if str(username) != str(credential.username) or str(password) != str(credential.password) or str(type) != str(credential.credentialType):
                            credential.username = username
                            credential.password = password
                            credential.credentialType = type
                            credential.save(force_update=True)
                            dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ServGrpCredMap = ServiceGroupCredentialMapping.objects.get(service_group__id=serviceGroup.id, credentials__id=credential.id)
                            ServGrpCredMap.signum = str(request.user)
                            ServGrpCredMap.date_time = str(dateTime)
                            ServGrpCredMap.save(force_update=True)
                        counter += 1
            except Exception as e:
                logger.error("Error with Updating ServiceGroupCredentialsMapping " + str(e))
                return fh.failure()
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        else:
            return fh.failure()
    else:
        fh.form = UpdateServiceGroupCredentialsForm(credentials=ServGrpCredMapList)
        return fh.display()

@login_required
@transaction.atomic
def deleteServiceGroupCredentials(request, groupName, groupId):
    '''
    The deleteServiceGroupCredentials: deletes the Service Group Credentials table via the UI
    '''
    ServGrpCredMapList = []
    fh = FormHandle()
    fh.title = "Delete Cluster Service Group Credentials: " + str(groupName)
    fh.request = request
    fh.button = "Finish"
    fh.button2 = "Cancel"

    serviceGroup = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroup.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Delete Service Group Credentials for Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    ServGrpCredMapList = ServiceGroupCredentialMapping.objects.filter(service_group__id=serviceGroup.id)

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        fh.form = DeleteServiceGroupCredentialsForm(request.POST, credentials=ServGrpCredMapList)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    counter = 1
                    for cred in ServGrpCredMapList:
                        delete = fh.form.cleaned_data['delete_' + str(counter)]
                        credential = Credentials.objects.get(id=cred.credentials.id)
                        if delete:
                           ServGrpCredMap = ServiceGroupCredentialMapping.objects.get(service_group__id=serviceGroup.id, credentials__id=credential.id)
                           ServGrpCredMap.delete()
                           credential.delete()
                        counter += 1

            except Exception as e:
                logger.error("Error with Deleting ServiceGroupCredentialsMapping " + str(e))
                return fh.failure()
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        else:
            return fh.failure()
    else:
        fh.form = DeleteServiceGroupCredentialsForm(credentials=ServGrpCredMapList)
        return fh.display()


@login_required
def deleteVeritasCluster(request, clusterId):
    '''
    Used to delete the Veritas Cluster information according to the Clusterid Given
    '''
    veritas = VeritasCluster.objects.get(cluster=clusterId)
    gcoIpObj = IpAddress.objects.get(id=veritas.ipMapGCO_id)
    csgIpObj = IpAddress.objects.get(id=veritas.ipMapCSG_id)
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Delete Veritas Cluster for Deployment: " +str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    if DataBaseLocation.objects.filter(cluster=cluster.id).exists():
        databaseLocationObj = DataBaseLocation.objects.get(cluster=cluster.id)

    try:
        if DataBaseLocation.objects.filter(cluster=cluster.id).exists():
            databaseLocationObj.delete()
        gcoIpObj.delete()
        csgIpObj.delete()
        veritas.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def deleteServicesCluster(request,clusterId,ServiceClusterId):
    '''
    Used to delete the Services Cluster information dependent on the deployment id given
    '''
    serviceInstance = []
    instIpObj = []
    ServicesClr = ServicesCluster.objects.get(id=ServiceClusterId)
    if Multicast.objects.filter(service_cluster_id=ServicesClr).exists():
        multicastObj = Multicast.objects.get(service_cluster_id=ServicesClr)
        defaultAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapDefaultAddress_id)
        messagingAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapMessagingGroupAddress_id)
        udpAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapUdpMcastAddress_id)
        mpingAddressIpObj = IpAddress.objects.get(id=multicastObj.ipMapMpingMcastAddress_id)
    serviceGroup = ServiceGroup.objects.filter(service_cluster=ServicesClr)
    for srvgrp in serviceGroup:
        for srvInst1 in ServiceGroupInstance.objects.filter(service_group=srvgrp.id):
            instIpObj += IpAddress.objects.filter(id=srvInst1.ipMap.id)
        serviceInstance += ServiceGroupInstance.objects.filter(service_group=srvgrp.id)
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
         if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Delete: " +str(ServicesClr.name)+ " for Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        for serviceUnitIPAddress in serviceInstance:
            serviceUnitIPAddress.delete()
        for serviceUnitIPObj in instIpObj:
            serviceUnitIPObj.delete()
        for serviceGrp in serviceGroup:
            serviceGrp.delete()
        if Multicast.objects.filter(service_cluster_id=ServicesClr).exists():
            defaultAddressIpObj.delete()
            messagingAddressIpObj.delete()
            udpAddressIpObj.delete()
            mpingAddressIpObj.delete()
            multicastObj.delete()
        ServicesClr.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def deleteServiceGroup(request, groupName, groupId):
    '''
    Used to delete the Service group according to the Service Group id Given
    '''
    serviceInstance = []
    instIpObj = []
    serviceGroup = ServiceGroup.objects.filter(id=groupId)
    for srvgrp in serviceGroup:
        clusterId = srvgrp.service_cluster.cluster.id
        for srvInst1 in ServiceGroupInstance.objects.filter(service_group=srvgrp.id):
            instIpObj += IpAddress.objects.filter(id=srvInst1.ipMap.id)
        serviceInstance += ServiceGroupInstance.objects.filter(service_group=srvgrp.id)
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Delete Service Group for Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        for serviceUnitIPAddress in serviceInstance:
            serviceUnitIPAddress.delete()
        for serviceUnitIPObj in instIpObj:
            serviceUnitIPObj.delete()
        serviceGroup.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def addPackageToServiceGroup(request, serviceGroupId):
    '''
    The addPackageToServiceGroup is used to assocaite pacakages to service group
    '''
    fh = FormHandle()
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    serviceGroup = ServiceGroup.objects.get(id=serviceGroupId)
    clusterId = serviceGroup.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to add Packages to a Service Group for " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.redirectTarget = "/dmt/clusters/"+str(clusterId)+"/details/"

    fh.title = "Add Package to Service Group: " +str(serviceGroup.name)
    packageList = getPackageList(serviceGroup=None,edit=False)
    if packageList == None:
        fh.message = "DataBase contains no Packages please add Packages and try again"
        return fh.display()

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        '''Check that there is no packages associated with this SG already'''
        serviceGroupPackageMap = ServiceGroupPackageMapping.objects.filter(serviceGroup=serviceGroup)
        fh.form = ServiceGroupPackageMappingSelectForm(request.POST)
        # redirect to details page
        clusterId = serviceGroup.service_cluster.cluster.id
        try:
            with transaction.atomic():
                # retrieve the selected packages from the form
                packages = request.POST.getlist('package')
                if packages:
                    validPackages = []
                    # Check all packages are valid
                    for package in packages:
                        # TODO: explicitly handle absence of package in database
                        pkgObj = Package.objects.get(name=str(package))
                        try:
                            sgpm, created = ServiceGroupPackageMapping.objects.get_or_create(package=pkgObj, serviceGroup=serviceGroup)
                        except Exception as e:
                            logger.error("Issue with updating Service Group to Package Mapping: "  +str(e))
                            return fh.failure()
                    # check if a mapping has been removed
                    selected = False
                    for sgpm in serviceGroupPackageMap:
                        for package in packages:
                            try:
                                if sgpm.package.name == package:
                                    selected = True
                                    break
                            except Exception as e:
                                logger.error("Package Selection Error: " +str(e))
                                return fh.failure()
                    return fh.success()
                else:
                    fh.form = ServiceGroupPackageMappingSelectForm(packageList)
                    fh.message = ("Please Ensure you select at least One Package")
                    return fh.display()
        except IntegrityError as e:
            fh.form = ServiceGroupPackageMappingSelectForm(packageList)
            fh.message = ("There was an issue adding Packages to: "
                    + str(serviceGroup.name) + ". Please Try again " + str(e))
            return fh.display()
    else:
        fh.form = ServiceGroupPackageMappingSelectForm(packageList)
        return fh.display()

@login_required
def updatePackageToServiceGroup(request, serviceGroupId):
    '''
    The updatePackageToServiceGroup updates the Service Group table via the UI
    '''
    serviceGroup = ServiceGroup.objects.get(id=serviceGroupId)
    clusterId = serviceGroup.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to edit Packages to a Service Group for " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh = FormHandle()
    fh.title = "Please Select Packages to Delete from Service Group: " +str(serviceGroup.name)
    fh.request = request
    fh.button = "Delete"
    fh.redirectTarget = "/dmt/clusters/"+str(clusterId)+"/details/"

    packageList = getPackageList(serviceGroup,edit=True)

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        packages = request.POST.getlist('package')
        if packages:
            for pkg in packages:
                packageObj = Package.objects.get(name=pkg)
                serviceGroupPackageMap = ServiceGroupPackageMapping.objects.filter(serviceGroup=serviceGroup, package=packageObj)
                try:
                    serviceGroupPackageMap.delete()
                except Exception as e:
                    logger.error("Issue deleting Service to Pkg Mapping ID: " +str(e))
            return fh.success()

        else:
            fh.form = ServiceGroupPackageMappingSelectForm(packageList)
            fh.message = ("Please Ensure you select at least One Package")
            return fh.display()
    else:
        if packageList != None:
            fh.form = ServiceGroupPackageMappingSelectForm(packageList)
            return fh.display()
        else:
            fh.message = ("There are no packages associated with Group: " +str(serviceGroup.name)+ ".Please Cancel")
            fh.button = "Cancel"
            return fh.display()

@login_required
def deletedPackageFromServiceGroup(request, sgId):
    '''
    '''
    serviceGroup = ServiceGroup.objects.get(id=sgId)
    clusterId = serviceGroup.service_cluster.cluster.id
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to delete Packages to a Service Group for " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.title = "Delete Package(s) to Service Group: " +str(serviceGroup.name)
    map = ServiceGroupPackageMapping.objects.filter(serviceGroup=serviceGroup)
    try:
        for m in map:
            m.delete()
        return HttpResponseRedirect("/dmt/clusters/" +str(clusterId)+ "/details/")
    except:
        return HttpResponseRedirect("/dmt/clusters/" +str(clusterId)+ "/details/")

@login_required
@transaction.atomic
def addServicesCluster(request,clusterId):
    '''
    '''
    fh = FormHandle()
    fh.title = "Add Service Cluster Info"
    fh.request = request
    fh.button = "Cancel"
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to add A Service Cluster to Deployment: " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    if request.method == 'POST':
        if "Cancel" in request.POST:
            fh.redirectTarget = ("/dmt/clusters/"+str(clusterId)+"/details")
            return fh.success()

    #Check to insure that Service Type to name to cluster does not already exist
    serviceClusterObject = ServicesCluster.objects.filter(cluster_type="Service Cluster", name="LSB Service Cluster", cluster=cluster.id)
    if serviceClusterObject:
        fh.form = ServicesClusterForm(initial={'cluster_type':"Service Cluster", 'name':"LSB Service Cluster"})
        fh.message = ("Service Cluster has aleady been defined in this deployment: " +str(cluster.name))
        return fh.display()
    else:
        try:
            #Check if deployment Servers are defined on a deployment if not redirect
            clusterServerExists = ClusterServer.objects.filter(cluster=cluster.id)
            if clusterServerExists:
                try:
                    with transaction.atomic():
                        servicesCluster, created = ServicesCluster.objects.get_or_create(cluster_type="Service Cluster",name="LSB Service Cluster",cluster=cluster)
                        ServCls = ServicesCluster.objects.get(name="LSB Service Cluster",cluster_id=cluster.id)
                        fh.redirectTarget = "/dmt/addcluster/"+str(clusterId)+"/"+str(ServCls.id)+"/addServiceGroup/"
                        return fh.success()
                except IntegrityError as e:
                    logger.error("Unable to add Service Cluster to Database, Error: " +str(e))
                    return fh.failure()
            else:
                message = True
                fh.redirectTarget = ("/dmt/addsvr/" + str(cluster.id) + "/" + str(message))
                return fh.success()
        except Exception as e:
            logger.error("Issue with adding service group to deployment: " +str(cluster.name)+ " Error: " +str(e))
            return fh.failure()

@login_required
@transaction.atomic
def addJbossCluster(request,clusterId):
    '''
    The addJbossCluster def allows a user to add a JBOSS Cluster to a deployment using the UI
    '''
    fh = FormHandle()
    fh.title = "Add JBOSS Cluster Info"
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to add A JBOSS Service Cluster for " + str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    fh.redirectTarget = "/dmt/clusters/"+str(clusterId)+"/details/"

    fh.form = JbossClusterForm(initial={'cluster_type':"JBOSS Cluster"})
    if request.method == 'POST':
        if "Cancel" in request.POST:
            fh.redirectTarget = ("/dmt/clusters/"+str(clusterId)+"/details")
            return fh.success()
        clusterType = request.POST.get('cluster_type')
        clusterName = request.POST.get('name')
        #Check to insure that Service Type to name to deployment does not already exist
        serviceClusterObject = ServicesCluster.objects.filter(cluster_type=clusterType, name=clusterName, cluster=clusterId)

        if serviceClusterObject:
            fh.message = ("Cluster Type: " +str(clusterType)+
                       " ,with Cluster Name: " +str(clusterName)+
                       " ,On Deployment: " +str(cluster.name)+ " is already defined, please try again")
            return fh.display()
        else:
            fh.form = JbossClusterForm(request.POST)
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        servicesCluster = fh.form.save(commit=False)
                        servicesCluster.cluster = cluster
                        servicesCluster.save()
                        return fh.success()
                except IntegrityError:
                    return fh.failure()

            else:
                logger.error("Invalid form please try again")
                return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def addVeritasCluster(request,clusterId):
    fh = FormHandle()
    fh.title = "Add Veritas Cluster Info"
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    fh.redirectTarget = ("/dmt/clusters/"+str(clusterId)+"/details")
    cluster = Cluster.objects.get(id=clusterId)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Add Veritas Cluster for Deployment: " +str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    veritasClusterObj = VeritasCluster.objects.filter(cluster_id=cluster.id)
    if request.method == 'POST':
        fh.form = VeritasClusterForm(request.POST)
        if "Cancel" in request.POST:
            return fh.success()
        if veritasClusterObj:
            fh.message = ("Vertias cluster already exists")
            return fh.display()
        else:
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        veritasCsgIpObj = IpAddress.objects.create(address=fh.form.cleaned_data['csgIp'],bitmask=fh.form.cleaned_data['csgBitmask'],ipType="veritas_" + str(cluster.id))
                        veritasGcoIpObj =  IpAddress.objects.create(address=fh.form.cleaned_data['gcoIp'],bitmask=fh.form.cleaned_data['gcoBitmask'],ipType="veritas_" + str(cluster.id))
                        veritasServer = VeritasCluster.objects.create(ipMapCSG=veritasCsgIpObj,csgNic=fh.form.cleaned_data['csgNic'],ipMapGCO=veritasGcoIpObj,gcoNic=fh.form.cleaned_data['gcoNic'],lltLink1=fh.form.cleaned_data['lltLink1'],lltLink2=fh.form.cleaned_data['lltLink2'],lltLinkLowPri1=fh.form.cleaned_data['lltLinkLowPri1'],cluster=cluster)
                        databaseLocObj = DataBaseLocation.objects.create(cluster=cluster)
                        return fh.success()
                except IntegrityError as e:
                    fh.message = ("There was an issue saving the veritas information, Exception : " + str(e))
                    logger.error(fh.message)
                    return fh.display()
            else:
                fh.message = ("There was an issue saving the veritas information, Exception : " + str(e))
                logger.error(fh.message)
                return fh.display()
    else:
        #Get an address in the defined range that is not used and does not already exist in table
        try:
            csgAddress,csgBitMask,gcoAddress,gcoBitMask = dmt.utils.getVeritasIpAdresses()
        except Exception as e:
            fh.message = ("There was an issue generating Veritas IP addresses, Exception : " + str(e))
            logger.error(fh.message)
            return fh.display()
        fh.form = VeritasClusterForm(
                initial={
                    'csgIp': csgAddress,
                    'csgBitmask': csgBitMask,
                    'csgNic': "eth0",
                    'gcoIp': gcoAddress,
                    'gcoBitmask': gcoBitMask,
                    'gcoNic': "eth0",
                    'lltLink1': "eth1",
                    'lltLink2': "eth2",
                    'lltLinkLowPri1': "eth0",
                    }
                )
        if veritasClusterObj:
            fh.message = ("Vertias cluster already exists")
            return fh.display()
        return fh.display()

@login_required
@transaction.atomic
def virtualImage(request, task, clusterId, vmName=None):
    '''
    The virtualImage is called to add/edit the VM to the cluster
    inputs: task what to do edit/add
    clusterId id of the cluster the virtual image is attached
    '''
    userId = request.user.pk
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to add a Virtual Machine to " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    taskTitle = task.title()
    fh.title = str(taskTitle) + " Service"
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button4 = "Cancel..."
    if task != "edit":
        fh.button2 = "Save & Add Another"
        fh.button5 = "Save & Add IP Info"
    fh.redirectTarget = "/dmt/clusters/"+str(clusterObj.id)+"/details/"
    if task != "edit":
        if vmName != None:
            if "virtualImageType_" in vmName:
                searchString = vmName.replace("virtualImageType_","")
            elif VirtualImage.objects.filter(cluster_id=clusterObj.id,name=vmName).exists():
                virtualImage = VirtualImage.objects.get(cluster_id=clusterObj.id,name=vmName)
                searchString = virtualImage.node_list
            else:
                searchString = 'SVC'
        else:
            searchString = 'SVC'
    else:
        searchString = 'SVC'

    nodeList = getNodeListOfCluster(clusterObj.id,searchString)
    if nodeList == None:
        message = "True"
        fh.redirectTarget = ("/dmt/addsvr/" + str(clusterObj.id) + "/" + str(message))
        return fh.success()

    def updateForm(request,fh,nodeList,vmName):
        '''
        This inner def is called multiple time with the outer def
        '''
        if task == "edit":
            fh.form = VirtualImageForm(nodeList,initial={'name': vmName,})
        else:
            fh.form = VirtualImageForm(nodeList)
        return fh.display()

    if request.method == 'POST':
        if "Cancel..." in request.POST:
            return fh.success()
        if task == "edit":
            oldValues = [str(vmName)+ "##Service Name"]
        fh.form = VirtualServerForm(request.POST)
        virtualImage = ""
        if vmName != request.POST.get('name'):
            virtualImage = VirtualImage.objects.filter(cluster_id=clusterObj.id,name=request.POST.get('name'))
        if not virtualImage:
            # validate the form so that the cleaned_data gets populated, then we can get the
            # requested name and define our redirect URL
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        nodesSelected = request.POST.getlist('node_list')
                        nodesSelected = nodesSelected[::-1]
                        node_list = ""
                        for node in nodesSelected:
                            if node_list == "":
                                node_list = str(node)
                            else:
                                node_list = str(node) + "," + node_list
                        name = request.POST.get("name")
                        returnedValue,message = dmt.utils.virtualImage(name,node_list,clusterObj.id,task,vmName)
                        if returnedValue == "1":
                            response = updateForm(request,fh,nodeList,vmName)
                            fh.message = "Failed to save the Service Information Exception " + str(message)
                            logger.error(fh.message)
                            return fh.display()
                        else:
                            if task == "edit":
                                newValues = [str(name)]
                                changedContent = logChange(oldValues,newValues)
                                message = "Edited Service Instance, " + str(changedContent)
                            else:
                                message = "Added Service Instance"
                            virtualImageObj = VirtualImage.objects.get(cluster_id=clusterObj.id,name=name)
                            logAction(userId, virtualImageObj, task, message)
                            if "Save & Add Another" in request.POST:
                                if "virtualImageType_" in vmName:
                                    return HttpResponseRedirect("/dmt/add/virtualImage/" + str(clusterObj.id) + "/" + str(vmName))
                                else:
                                    return HttpResponseRedirect("/dmt/add/virtualImage/" + str(clusterObj.id))
                            if "Save & Add IP Info" in request.POST:
                                virtualImageObj = VirtualImage.objects.get(cluster_id=clusterObj.id,name=name)
                                return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/virtualImage/" + str(virtualImageObj.name) + "/" + str(virtualImageObj.id) + "/add/public/no/")
                            else:
                                return fh.success()
                except IntegrityError as e:
                    response = updateForm(request,fh,nodeList,vmName)
                    fh.message = ("There was an issue saving the form, Please Try again. Exception: " + str(e))
                    return fh.display()
            else:
                response = updateForm(request,fh,nodeList,vmName)
                fh.message = ("There was an issue saving the form, Please ensure all fields are selected, Try again")
                return fh.display()
        else:
            fh.message = ("The Service with Name: " + str(request.POST.get('name')) +
                           " is already assigned to this deployment, please choose again ")
            response = updateForm(request,fh,nodeList,vmName)
            return response
    else:
        response = updateForm(request,fh,nodeList,vmName)
        return response

@login_required
@transaction.atomic
def updateMgmtServerCredentials(request, serverId, task, credentialId=None):
    '''
    updateServerCredentials add/edit credentials to the server group table via the UI
    '''

    try:
        mgmtServerObj = ManagementServer.objects.get(server__id=serverId)
    except Exception as e:
        fh.message = "Issue getting Management Server information, Exception :  " + str(e)
        logger.error(fh.message)
        return fh.display()

    fh = FormHandle()
    fh.title = "Add Management Server Credentials for " + str(mgmtServerObj.server.hostname) + ' (id:'  + str(mgmtServerObj.id) + ')'
    fh.request = request
    fh.redirectTarget = ("/dmt/mgtsvrs/" + str(serverId))
    fh.button = "Save & Exit"
    if task != "edit":
        fh.button2 = "Save & Add Another"
    fh.button4 = "Cancel"

    try:
        if task == "edit":
            mgmtServerCredMapObj = ManagementServerCredentialMapping.objects.get(mgtServer=mgmtServerObj,credentials=credentialId)
    except Exception as e:
        fh.message = "Issue getting Management Server Credentials Mapping information, Exception : " + str(e)
        logger.error(fh.message)
        return fh.display()

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()

        fh.form = ServerCredentialsForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    username=fh.form.cleaned_data['username']
                    password=fh.form.cleaned_data['password']
                    type=fh.form.cleaned_data['credentialType']
                    if task == "edit":
                        oldValues = [str(mgmtServerCredMapObj.credentials.username) + "##Server Credential Username",str(mgmtServerCredMapObj.credentials.password)+ "##Server Credential Password",str(mgmtServerCredMapObj.credentials.credentialType) + "##Credential Type"]
                        newValues = [str(username),str(password),str(type)]
                        changedContent = logChange(oldValues,newValues)
                        messageLog = "Edit Management Server Credentials, " + str(changedContent)
                        returnedValue,message = dmt.utils.editMgmtServerCredentials(username,password,type,mgmtServerObj.id,credentialId)
                    else:
                        messageLog = "Add Server Credentials"
                        returnedValue,message = dmt.utils.createMgmtServerCredentials(username,password,type,mgmtServerObj.id,str(request.user))
                    if returnedValue == "1":
                        fh.message = "Failed to save management server credential information for " + str(mgmtServerObj.server.hostname) + ' (id:'  + str(mgmtServerObj.id) + ')' + ". " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        logAction(request.user.pk, mgmtServerObj, task, messageLog)
                        if "Save & Add Another" in request.POST:
                            return HttpResponseRedirect("/dmt/mgtsvr/" + str(serverId) + "/" + str(task) + "/credential/")
                        else:
                            return HttpResponseRedirect("/dmt/mgtsvrs/" + str(serverId))
            except Exception as e:
                logger.error("Error with Adding ManagementServerCredentialMapping, " + str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        if task == "edit":
            fh.form = ServerCredentialsForm(
                    initial={
                        'username': str(mgmtServerCredMapObj.credentials.username),
                        'password': str(mgmtServerCredMapObj.credentials.password),
                        'credentialType': str(mgmtServerCredMapObj.credentials.credentialType),
                        }
                   )
        else:
            fh.form = ServerCredentialsForm()
        return fh.display()

@login_required
@transaction.atomic
def deleteMgmtServerCredentials(request, serverId, credentialId):
    '''
    The deleteMgmtServerCredentials is called to delete management server credentials.
    '''

    action = "delete"
    try:
        try:
            mgmtServerObj = ManagementServer.objects.get(server__id=serverId)
            dictDeletedInfo = {}
            dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(mgmtServerObj).pk
            dictDeletedInfo["objectId"] = mgmtServerObj.pk
            dictDeletedInfo["objectRep"] = force_unicode(mgmtServerObj)
        except Exception as e:
            message = "Unable to find the management server specified within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        try:
            mgmtServerCredMapObj = ManagementServerCredentialMapping.objects.get(mgtServer=mgmtServerObj,credentials=credentialId)
        except Exception as e:
            message = "Unable to find the management server to credentials mapping within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        try:
            credentialObj = Credentials.objects.get(id=credentialId)
        except Exception as e:
            message = "Unable to find the server credentials specified within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        mgmtServerCredMapObj.delete()
        credentialObj.delete()
        message = "Deleted Server Credential"
        logAction(userId, mgmtServerObj, action, message, dictDeletedInfo)
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/mgtsvrs/" + str(serverId))
    except Exception as e:
        message = "There was an issue deleting the management server credentials information for the Service, Exception : " +str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/mgtsvrs/" + str(serverId))

@login_required
@transaction.atomic
def updateServerCredentials(request, cluster_id, serverName, nodeType, serverId, task, credentialId=None):
    '''
    updateServerCredentials add/edit credentials to the server group table via the UI
    '''
    userId = request.user.pk
    fh = FormHandle()
    fh.title = "Add Server Credentials for " + str(serverName) + ' ('  + str(nodeType) + ')'
    fh.request = request
    fh.redirectTarget = ("/dmt/clusters/" + str(cluster_id) + "/details/")
    fh.button = "Save & Exit"
    if task != "edit":
        fh.button2 = "Save & Add Another"
    fh.button4 = "Cancel"

    try:
        clusterObj = Cluster.objects.get(id=cluster_id)
    except Exception as e:
        fh.message = "No such deployment: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(fh.message)
        return fh.display()
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to add Service Credentials for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        clusterServerObj = ClusterServer.objects.get(id=serverId)
        if task == "edit":
            clusterServerCredMapObj = ClusterServerCredentialMapping.objects.get(clusterServer=clusterServerObj,credentials=credentialId)
    except Exception as e:
        fh.message = "Issue getting Server information, Exception : " + str(e)
        logger.error(fh.message)
        return fh.display()

    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()

        fh.form = ServerCredentialsForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    username=fh.form.cleaned_data['username']
                    password=fh.form.cleaned_data['password']
                    type=fh.form.cleaned_data['credentialType']
                    if task == "edit":
                        oldValues = [str(clusterServerCredMapObj.credentials.username) + "##Server Credential Username",str(clusterServerCredMapObj.credentials.password)+ "##Server Credential Password",str(clusterServerCredMapObj.credentials.credentialType) + "##Credential Type"]
                        newValues = [str(username),str(password),str(type)]
                        changedContent = logChange(oldValues,newValues)
                        messageLog = "Edit Server Credentials, " + str(changedContent)
                        returnedValue,message = dmt.utils.editServerCredentials(username,password,type,serverId,credentialId)
                    else:
                        messageLog = "Add Server Credentials"
                        returnedValue,message = dmt.utils.createServerCredentials(username,password,type,serverId,str(request.user))
                    if returnedValue == "1":
                        fh.message = "Failed to save server credential information for " + str(serverName) + ' ('  + str(nodeType) + ')' + ". " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        logAction(userId, clusterServerObj, task, messageLog)
                        if "Save & Add Another" in request.POST:
                            return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/server/" + str(serverName) + "/" + str(nodeType) + "/" + str(serverId) + "/" + str(task) + "/credential/")
                        else:
                            return HttpResponseRedirect("/dmt/clusters/" + str(clusterObj.id) + "/details/")
            except Exception as e:
                logger.error("Error with Adding ClusterServerCredentialMapping, " + str(e))
                return fh.failure()
        else:
            return fh.failure()
    else:
        if task == "edit":
            fh.form = ServerCredentialsForm(
                    initial={
                        'username': str(clusterServerCredMapObj.credentials.username),
                        'password': str(clusterServerCredMapObj.credentials.password),
                        'credentialType': str(clusterServerCredMapObj.credentials.credentialType),
                        }
                   )
        else:
            fh.form = ServerCredentialsForm()
        return fh.display()

@login_required
@transaction.atomic
def deleteServerCredentials(request, clusterId, serverName, nodeType, serverId, credentialId):
    '''
    The deleteServerCredentials is called to delete credentials from the server group.
    '''

    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete server credentials for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        try:
            clusterServerObj = ClusterServer.objects.get(id=serverId)
            dictDeletedInfo = {}
            dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(clusterServerObj).pk
            dictDeletedInfo["objectId"] = clusterServerObj.pk
            dictDeletedInfo["objectRep"] = force_unicode(clusterServerObj)
        except Exception as e:
            message = "Unable to find the server specified within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        try:
            clusterServerCredMapObj = ClusterServerCredentialMapping.objects.get(clusterServer=clusterServerObj,credentials=credentialId)
        except Exception as e:
            message = "Unable to find the server to credentials mapping within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        try:
            credentialObj = Credentials.objects.get(id=credentialId)
        except Exception as e:
            message = "Unable to find the server credentials specified within the DB"
            logger.error(message + ", Error: " + str(e))
            return ("1",message)
        clusterServerCredMapObj.delete()
        credentialObj.delete()
        message = "Deleted Server Credential"
        logAction(userId, clusterServerObj, action, message, dictDeletedInfo)
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except Exception as e:
        message = "There was an issue deleting the server credentials information for the Service, Exception : " +str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def virtualImageCredentials(request, cluster_id, vmName, virtualImageId, task, credentialId=None):
    '''
    The virtualImageCredentials adds Credentials to the virtual group table via the UI
    '''
    userId = request.user.pk
    fh = FormHandle()
    fh.title = "Add Virtual image Credentials for " + str(vmName)
    fh.request = request
    fh.redirectTarget = ("/dmt/clusters/" + str(cluster_id) + "/details/")
    fh.button = "Save & Exit..."
    if task != "edit":
        fh.button2 = "Save & Add Another"
    fh.button4 = "Cancel..."

    try:
        clusterObj = Cluster.objects.get(id=cluster_id)
    except Exception as e:
        fh.message = "No such deployment: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(fh.message)
        return fh.display()
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to add Service Credentials for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterObj.id)
        if task == "edit":
            virtualImageCredMapObj = VirtualImageCredentialMapping.objects.get(virtualimage=virtualImageObj,credentials=credentialId)
    except Exception as e:
        fh.message = "Issue getting Service information, Exception : " + str(e)
        logger.error(fh.message)
        return fh.display()

    if request.method == 'POST':
        if "Cancel..." in request.POST:
            return fh.success()

        fh.form = VirtualImageCredentialsForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    username=fh.form.cleaned_data['username']
                    password=fh.form.cleaned_data['password']
                    type=fh.form.cleaned_data['credentialType']
                    if task == "edit":
                        oldValues = [str(virtualImageCredMapObj.credentials.username) + "##Service Credential Username",str(virtualImageCredMapObj.credentials.password)+ "##Service Credential Password",str(virtualImageCredMapObj.credentials.credentialType) + "##Credential Type"]
                        newValues = [str(username),str(password),str(type)]
                        changedContent = logChange(oldValues,newValues)
                        messageLog = "Edit Service Instance Credentials, " + str(changedContent)
                        returnedValue,message = dmt.utils.editVirtualImageCredentials(username,password,type,vmName,clusterObj.id,credentialId)
                    else:
                        messageLog = "Add Service Instance Credentials"
                        returnedValue,message = dmt.utils.createVirtualImageCredentials(username,password,type,vmName,clusterObj.id,str(request.user))
                    if returnedValue == "1":
                        fh.message = "Failed to save Service Credential Information for " + str(virtualImageObj.name) + ". " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        logAction(userId, virtualImageObj, task, messageLog)
                        if "Save & Add Another" in request.POST:
                            return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/virtualImage/" + str(vmName) + "/" + str(virtualImageId) + "/" + str(task) + "/credential/")
                        else:
                            return HttpResponseRedirect("/dmt/clusters/" + str(clusterObj.id) + "/details/")
            except Exception as e:
                logger.error("Error with Adding VirtualImageCredentialsMapping " + str(e))
                return fh.failure()
            if "Save & Exit..." in request.POST:
                return HttpResponseRedirect("/dmt/clusters/" + str(clusterObj.id) + "/details/")
            else:

                return HttpResponseRedirect("/dmt/{{ clusterObj.id }}/virtualImage/{{ vmName }}/{{ virtualImageId }}/{{ task }}/credential/")
        else:
            return fh.failure()
    else:
        if task == "edit":
            fh.form = VirtualImageCredentialsForm(
                    initial={
                        'username': str(virtualImageCredMapObj.credentials.username),
                        'password': str(virtualImageCredMapObj.credentials.password),
                        'credentialType': str(virtualImageCredMapObj.credentials.credentialType),
                        }
                   )
        else:
            fh.form = VirtualImageCredentialsForm()
        return fh.display()

@login_required
@transaction.atomic
def deleteVirtualImageCredentials(request, clusterId, vmName, virtualImageId, credentialId):
    '''
    The deleteVirtualImageIpInfo is called to delete ip address info from the virtual image.
    Inputs: clusterId vmname get the virtual image Object
    credentialId gets the virtual image credentials map obj and credentials object for deleting
    '''

    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete virtual image credentials for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        if VirtualImage.objects.filter(name=vmName,cluster=clusterId).exists():
            virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterId)
            dictDeletedInfo = {}
            dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(virtualImageObj).pk
            dictDeletedInfo["objectId"] = virtualImageObj.pk
            dictDeletedInfo["objectRep"] = force_unicode(virtualImageObj)
        else:
            message = "Unable to find the virtual image specified within the DB"
            logger.error(message)
            return ("1",message)
        if VirtualImageCredentialMapping.objects.filter(virtualimage=virtualImageObj,credentials=credentialId).exists():
            virtualImageCredMapObj = VirtualImageCredentialMapping.objects.get(virtualimage=virtualImageObj,credentials=credentialId)
            if Credentials.objects.filter(id=virtualImageCredMapObj.credentials_id).exists():
                credentialObj = Credentials.objects.get(id=virtualImageCredMapObj.credentials_id)
            else:
                message = "Unable to find the virtual image credentials mapping to credentials within the DB for " + str(task)
                logger.error(message)
                return ("1",message)
        else:
            message = "Unable to find the virtual image credentials specified within the DB for " + str(task)
            logger.error(message)
            return ("1",message)
        virtualImageCredMapObj.delete()
        credentialObj.delete()
        message = "Deleted Virtual Image Credential"
        logAction(userId, virtualImageObj, action, message, dictDeletedInfo)
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except Exception as e:
        message = "There was an issue deleting the virtual image credentials information for the Service, Exception : " +str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def deleteVirtualImage(request, clusterId, vmName):
    '''
    Used to delete the Service group according to the Service Group id Given
    '''
    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete virtual image for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        virtualImageObj = VirtualImage.objects.get(name=vmName,cluster=clusterId)
        nodeType = str(virtualImageObj.node_list)
        clusterServerObject = ClusterServer.objects.only('server__hostname').values('server__hostname').get(cluster__id=clusterId, node_type=nodeType)
        logMsg = "Deleted Service Instance: " + str(virtualImageObj.name) + " from " + str(clusterServerObject['server__hostname']) + " (" + str(nodeType) +")"
        dictDeletedInfo = {}
        dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(clusterObj).pk
        dictDeletedInfo["objectId"] = clusterObj.pk
        dictDeletedInfo["objectRep"] = force_unicode(clusterObj)
        returnedValue,message = dmt.utils.deleteVirtualImage(clusterId, vmName)
        if returnedValue == "1":
            logger.error(message)
        logAction(userId, clusterObj, action, logMsg, dictDeletedInfo)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except Exception as e:
        message = "Issue deleting some of the virtual image data for " + str(vmName) + " Exception :  " + str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def deleteVirtualImageIpInfo(request, clusterId, virtualImageIpMapId, virtualImageIpType):
    '''
    The deleteVirtualImageIpInfo is called to delete ip address info from the virtual image.
    '''
    userId = request.user.pk
    action = "delete"
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete virtual image Ip for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        virtualImageIpMapObj = VirtualImageInfoIp.objects.get(id=virtualImageIpMapId)
        virtualImageObj = VirtualImage.objects.get(name=virtualImageIpMapObj.virtual_image.name,cluster=clusterId)
        dictDeletedInfo = {}
        dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(virtualImageObj).pk
        dictDeletedInfo["objectId"] = virtualImageObj.pk
        dictDeletedInfo["objectRep"] = force_unicode(virtualImageObj)
        virtualImageIpMapObj = VirtualImageInfoIp.objects.get(id=virtualImageIpMapId)
        virtualImageIpObj = IpAddress.objects.get(id=virtualImageIpMapObj.ipMap_id)
        virtualImageIpMapObj.delete()
        virtualImageIpObj.delete()
        cursor = connection.cursor()
        message = "Deleted Service Instance IP Info"
        logAction(userId, virtualImageObj, action, message, dictDeletedInfo)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except Exception as e:
        message = "There was an issue deleting the IP information for the Service, Exception : " +str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def installGroupDelete(request,installGroupId):
    '''
    The installGroupDeloymentdElete is called to delete a deployment from an install group
    '''
    try:
        allInstallGroupDeploymentsObj = ClusterToInstallGroupMapping.objects.filter(group=installGroupId)
        for item in allInstallGroupDeploymentsObj:
            installGroupDeploymentsObj = ClusterToInstallGroupMapping.objects.get(cluster=item.cluster,group=item.group)
            installGroupDeploymentsObj.delete()
        installGroupObj = InstallGroup.objects.get(id=installGroupId)
        installGroupObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/searchInstallGroup/")
    except Exception as e:
        message = "There was an issue deleting the install group, Exception : " +str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/searchInstallGroup/")

@login_required
def installGroupDeploymentDelete(request,clusterId,installGroupId):
    '''
    The installGroupDeloymentdElete is called to delete a deployment from an install group
    '''
    try:
        installGroupObj = ClusterToInstallGroupMapping.objects.get(cluster=clusterId,group=installGroupId)
        installGroupObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/searchInstallGroup/")
    except Exception as e:
        message = "There was an issue deleting the deployment from the install group, Exception : " +str(e)
        logger.error(message)
        return HttpResponseRedirect("/dmt/searchInstallGroup/")

@login_required
def installGroupDeployments(request, task, installGroupId):
    '''
    The installGroupDeloyments is called to add/edit a deployment onto a deployment
    '''
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.request = request
    fh.redirectTarget = ("/dmt/searchInstallGroup/")
    fh.button = "Save & Exit"
    fh.button2 = "Save & Add Another"
    fh.button4 = "Cancel..."
    fh.form = ClusterToInstallGroupMappingForm()
    installGroupObj = InstallGroup.objects.get(id=installGroupId)
    taskTitle = task.title()
    fh.title = str(taskTitle) + " A deployment to the install group: " + str(installGroupObj.installGroup)

    if request.method == 'POST':
        if "Cancel..." in request.POST:
             return fh.success()
        fh.form = ClusterToInstallGroupMappingForm(request.POST)
        if fh.form.is_valid():
            try:
                clusterRef=fh.form.cleaned_data['cluster']
                clusterRefName = str(clusterRef).split(" ")
                clusterRefName = clusterRefName[0]
                clusterObj = Cluster.objects.get(name=clusterRefName)
                clusterId = clusterObj.id
                if task == "edit":
                    returnedValue,message = dmt.utils.editInstallGroupDeployment(clusterId,installGroupId)
                else:
                    returnedValue,message = dmt.utils.createInstallGroupDeployment(clusterId,installGroupId)
                if returnedValue == "1":
                    if "Duplicate" in message:
                        message = "Duplicate Entry for " + str(clusterRef) + " installgroup already has deployment assigned"
                    fh.message = "Failed to " + str(task) + " deployment to install group, Exception " + str(message)
                    logger.error(fh.message)
                    return fh.display()
                else:
                    if "Save & Add Another" in request.POST:
                        return HttpResponseRedirect("/dmt/installGroupDeployment/add/" + str(installGroupId))
                    else:
                        return HttpResponseRedirect("/dmt/searchInstallGroup/")
            except IntegrityError as e:
                fh.message = "Failed to " + str(task) + " install group deployment, Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the install group deployment form"
            logger.error(fh.message)
            return fh.display()
    if task == "edit":
        installGroupDeploymentObj = ClusterToInstallGroupMapping.objects.get(group=installGroupId)
        fh.form = ClusterToInstallGroupMappingForm(initial={'cluster': str(installGroupDeploymentObj.cluster),})
    return fh.display()

@login_required
@transaction.atomic
def installGroup(request, task, installGroupId):
    '''
    The installGroup is called to add/edit an install group.
    '''
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.request = request
    fh.redirectTarget = ("/dmt/searchInstallGroup/")
    fh.button = "Save & Exit"
    fh.button2 = "Save & Add Deployment"
    fh.button4 = "Cancel..."
    fh.form = InstallGroupForm()
    taskTitle = task.title()
    fh.title = str(taskTitle) + " Install Group"

    if request.method == 'POST':
        if "Cancel..." in request.POST:
             return fh.success()
        fh.form = InstallGroupForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    installGroup=fh.form.cleaned_data['installGroup']
                    message = dmt.utils.nameCheck(installGroup)
                    if message != "OK":
                        fh.message=message
                        return fh.display()
                    if task == "edit":
                        installGroupObj = InstallGroup.objects.get(id=installGroupId)
                        if installGroup != installGroupObj.installGroup:
                            returnedValue,message = dmt.utils.editInstallGroup(installGroup,installGroupId)
                        else:
                            returnedValue = "0"
                    else:
                        returnedValue,message = dmt.utils.createInstallGroup(installGroup)
                    if returnedValue == "1":
                        fh.message = "Failed to " + str(task) + " install group"
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if "Save & Add Deployment" in request.POST:
                            installGroupObj = InstallGroup.objects.get(installGroup=installGroup)
                            return HttpResponseRedirect("/dmt/installGroupDeployment/add/" + str(installGroupObj.id))
                        else:
                            return HttpResponseRedirect("/dmt/searchInstallGroup/")
            except IntegrityError as e:
                fh.message = "Failed to " + str(task) + " install group, Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the install group form"
            logger.error(fh.message)
            return fh.display()
    if task == "edit":
        installGroupObj = InstallGroup.objects.get(id=installGroupId)
        fh.form = InstallGroupForm(initial={'installGroup': str(installGroupObj.installGroup),})
    return fh.display()

@login_required
@transaction.atomic
def virtualImageIpInfo(request, cluster_id, vmName, virtualImageId, task, virtualImageIpType, populate):
    '''
    The VirtualImageIpInfo is called to add/edit an ip address to the virtual image.
    '''
    userId = request.user.pk
    clusterObj = Cluster.objects.get(id=cluster_id)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to edit Virtual Image Information for Deployment:" + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    # Create a FormHandle to handle form post-processing
    nextIPType = None
    number = ""
    hostname = ""
    imageIpAddress = ""
    fh = FormHandle()
    fh.request = request
    fh.redirectTarget = ("/dmt/clusters/" + str(cluster_id) + "/details/")
    fh.button = "Save & Exit"

    if task != "edit":
        hasPublic = False
        hasPublicv6 = False
        hasStorage = False
        hasInternal = False
        hasInternalv6 = False
        hasMulticast = False
        if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageId,ipMap__ipType__startswith="virtualImage_public").exists():
            hasPublic = True
        if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageId,ipMap__ipType__startswith="virtualImage_ipv6Public").exists():
            hasPublicv6 = True
        if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageId,ipMap__ipType__startswith="virtualImage_ipv6Internal").exists():
            hasInternalv6 = True
        if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageId,ipMap__ipType__startswith="virtualImage_storage").exists():
            hasStorage = True
        if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageId,ipMap__ipType__startswith="virtualImage_internal").exists():
            hasInternal = True
        if VirtualImageInfoIp.objects.filter(virtual_image=virtualImageId,ipMap__ipType__startswith="virtualImage_jgroup").exists():
            hasMulticast = True

        if str(virtualImageIpType) == 'public':
            if not hasPublicv6:
                nextIPType = 'ipv6Public'
            elif not hasStorage:
                nextIPType = 'storage'
            elif not hasInternal:
                nextIPType = 'internal'
            elif not hasMulticast:
                populate = 'yes'
                nextIPType = 'jgroup'
            else:
                nextIPType = None
        elif str(virtualImageIpType) == 'ipv6Public':
            if not hasStorage:
                nextIPType = 'storage'
            elif not hasInternal:
                nextIPType = 'internal'
            elif not hasMulticast:
                populate = 'yes'
                nextIPType = 'jgroup'
            else:
                nextIPType = None
        elif str(virtualImageIpType) == 'storage':
            if not hasInternal:
                nextIPType = 'internal'
            elif not hasMulticast:
                populate = 'yes'
                nextIPType = 'jgroup'
            else:
                nextIPType = None
        elif str(virtualImageIpType) == 'internal':
            if not hasMulticast:
                populate = 'yes'
                nextIPType = 'jgroup'
            else:
                nextIPType = None
        else:
            nextIPType = None

        if nextIPType:
            fh.button2 = "Save & Add "+str(nextIPType) +" IP"
            fh.button5 = "Skip"

        if virtualImageIpType != "ipv6Public" and virtualImageIpType != "public" and virtualImageIpType != "storage":
            if populate == "no":
                fh.button3 = "Auto Populate"
            else:
                fh.button3 = "Clear all Fields"

    fh.button4 = "Cancel..."
    if virtualImageIpType == "ipv6Public":
        fh.form = VirtualImageIpv6InfoForm()
    elif virtualImageIpType =="ipv6Internal":
        fh.form = VirtualImageIpv6InternalInfoForm()
    elif virtualImageIpType == "public":
        fh.form = VirtualImageSSHIpInfoForm()
    else:
        fh.form = VirtualImageIpInfoForm()
    try:
        clusterObj = Cluster.objects.get(id=cluster_id)
    except Exception as e:
        fh.message = "No such deployment: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(fh.message)
        return fh.display()
    try:
        virtualImageObj = VirtualImage.objects.get(name=vmName,cluster_id=clusterObj.id)
        if task != "add":
            virtualImageIpObj = VirtualImageInfoIp.objects.get(id=virtualImageId)
    except Exception as e:
        fh.message = "Issue getting Service information, Exception : " + str(e)
        logger.error(fh.message)
        return fh.display()

    taskTitle = task.title()
    virtualImageIpTypeTitle = virtualImageIpType.title()
    fh.title = str(taskTitle) + " " + str(virtualImageIpTypeTitle) + " Service IP Information for : " + str(virtualImageObj.name)

    if request.method == 'POST':
        if "Cancel..." in request.POST:
             return fh.success()
        if "Skip" in request.POST:
             return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/virtualImage/" + str(vmName) + "/" + str(virtualImageId) + "/" + str(task) + "/" + str(nextIPType) + "/" + str(populate) + "/")

        if "Auto Populate" in request.POST:
             return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/virtualImage/" + str(vmName) + "/" + str(virtualImageId) + "/" + str(task) + "/" + str(virtualImageIpType) + "/yes/")
        if "Clear all Fields" in request.POST:
             return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/virtualImage/" + str(vmName) + "/" + str(virtualImageId) + "/" + str(task) + "/" + str(virtualImageIpType) + "/no/")
        if virtualImageIpType == "ipv6Public":
            fh.form = VirtualImageIpv6InfoForm(request.POST)
        elif virtualImageIpType =="ipv6Internal":
            fh.form = VirtualImageIpv6InternalInfoForm(request.POST)
        elif virtualImageIpType == "public":
            fh.form = VirtualImageSSHIpInfoForm(request.POST)
        else:
            fh.form = VirtualImageIpInfoForm(request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested jgroups and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    address=dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['address'])
                    ipType="virtualImage_" + str(virtualImageIpType) + "_" + str(virtualImageObj.id)
                    number=fh.form.cleaned_data['number']
                    if virtualImageIpType == "ipv6Public" or virtualImageIpType == "public":
                        if fh.form.cleaned_data['hostname'] != "":
                            hostname=fh.form.cleaned_data['hostname']
                        else:
                            hostname=None
                    else:
                        hostname=None
                    if task == "edit":
                        numberLog,hostnameLog,imageIpAddressLog = dmt.utils.getVirtualImageData(virtualImageId)
                        oldValues = [str(numberLog)+ "##IP Reference Number",str(imageIpAddressLog) + "## IP Address",str(hostnameLog) + "##IP Hostname"]
                        newValues = [str(number),str(address),str(hostname)]
                        changedContent = logChange(oldValues,newValues)
                        returnedValue,message = dmt.utils.editVirtualImageIp(address,ipType,number,hostname,clusterObj.id,virtualImageIpObj,virtualImageIpType)
                    else:
                        returnedValue,message = dmt.utils.createVirtualImageIp(address,ipType,number,hostname,clusterObj.id,virtualImageObj.name,virtualImageIpType)
                    if returnedValue == "1":
                        fh.message = "Failed to add Service IP Information for " + str(virtualImageObj.name) + ". " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if task == "edit":
                          message = "Edited Service Instance (" + str(virtualImageIpType) + "), " + str(changedContent)
                        else:
                          message = "Added Service Instance IP (" + str(virtualImageIpType) + ")"
                        logAction(userId, virtualImageObj, task, message)
                        if "Save & Add "+str(nextIPType) +" IP" in request.POST:
                            return HttpResponseRedirect("/dmt/" + str(clusterObj.id) + "/virtualImage/" + str(vmName) + "/" + str(virtualImageId) + "/" + str(task) + "/" + str(nextIPType) + "/" + str(populate) + "/")
                        else:
                            return HttpResponseRedirect("/dmt/clusters/" + str(clusterObj.id) + "/details/")
            except IntegrityError as e:
                fh.message = "Failed to add Service IP Information for " + str(virtualImageObj.name) + ", Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the Service IP Information for image type " + str(virtualImageIpType)
            logger.error(fh.message)
            return fh.display()
    elif task == "edit":
        try:
            number,hostname,imageIpAddress = dmt.utils.getVirtualImageData(virtualImageId)
        except Exception as e:
            fh.message = "There was an issue getting the IP information for the Service, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
    else:
        number = dmt.utils.getAvailableVirtualImageIPNumber(clusterObj.id, virtualImageObj.name,virtualImageIpType)
        #Get an address in the defined range that is not used and does not already exist in table
        try:
            if virtualImageIpType == "internal":
                instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj, ["PDU-Priv-2_virtualImageInternal", "PDU-Priv-2_virtualImageInternal_2"])
            elif virtualImageIpType == "jgroup":
                instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv_virtualImageInternalJgroup")
            elif virtualImageIpType == "ipv6Internal":
                if clusterObj.layout.name == "KVM":
                    instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"ClusterId_" + str(clusterObj.id))
                else:
                    instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getNextFreeInternalIP(clusterObj,"PDU-Priv-2_virtualImageInternalIPv6")
            elif virtualImageIpType == "ipv6Public":
                imageIpAddress = ""
            else:
                instanceGateway,imageIpAddress,instanceBitmask = dmt.utils.getServiceGroupInstanceIpAddress(clusterObj.id,False,virtualImageIpType)
        except Exception as e:
            fh.message = "There was an issue generating an IP address for the Service, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
    if virtualImageIpType == "ipv6Public" or populate == "yes":
        if virtualImageIpType == "ipv6Public":
            fh.form = VirtualImageIpv6InfoForm(
                    initial={
                        'number': str(number),
                        'hostname': str(hostname),
                        'address': str(imageIpAddress),
                        }
                   )
        elif virtualImageIpType == "ipv6Internal":
            fh.form = VirtualImageIpv6InternalInfoForm(
                    initial={
                        'number': str(number),
                        'address': str(imageIpAddress),
                        }
                    )
        elif virtualImageIpType == "public":
            fh.form = VirtualImageSSHIpInfoForm(
                    initial={
                        'number': str(number),
                        'hostname': str(hostname),
                        'address': str(imageIpAddress),
                        }
                   )
        else:
            fh.form = VirtualImageIpInfoForm(
                    initial={
                        'number': str(number),
                        'address': str(imageIpAddress),
                        }
                   )
    else:
        if virtualImageIpType == "ipv6Public":
            fh.form = VirtualImageIpv6InfoForm(initial={'number': str(number),})
        elif virtualImageIpType == "ipv6Internal":
            fh.form = VirtualImageIpv6InternalInfoForm(initial={'number': str(number),})
        elif virtualImageIpType == "public":
            fh.form = VirtualImageSSHIpInfoForm(initial={'number': str(number),})
        else:
            fh.form = VirtualImageIpInfoForm(initial={'number': str(number),})
    return fh.display()

@login_required
@transaction.atomic
def addServiceGroupInstance(request, cluster_id, serviceGroupId):
    '''
    The ServiceGroupInstance is called to add the nstance to the Service Group.
    '''
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.request = request
    fh.button = "Save & Exit"
    fh.button2 = "Save & Add Another"
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        serviceGroupId = ServiceGroup.objects.get(id=serviceGroupId)
    except Exception as e:
        fh.message = "No such deployment: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(fh.message)
        return fh.display()

    fh.title = "Add Service Unit IP Information for Service Group Unit : " + str(serviceGroupId.name)

    if request.method == 'POST':
        fh.form = ServiceGroupInstanceForm(request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested multicasts and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    address=fh.form.cleaned_data['address']
                    bitmask=fh.form.cleaned_data['bitmask']
                    gateway=fh.form.cleaned_data['gateway']
                    ipType="serviceUnit_" + str(serviceGroupId.id)
                    name=fh.form.cleaned_data['name']
                    if fh.form.cleaned_data['hostname'] != "":
                        hostname=fh.form.cleaned_data['hostname']
                    else:
                        hostname=None
                    returnedValue = dmt.utils.savedServiceGroupInstanceIp(address,bitmask,gateway,ipType,name,hostname,serviceGroupId)
                    if returnedValue == 1:
                        fh.message = "Failed to add Service Unit Information for " + str(serviceGroupId.name)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if "Save & Add Another" in request.POST:
                            return HttpResponseRedirect("/dmt/" + str(cluster_id) + "/serviceGroup/" + str(serviceGroupId.id) + "/addInstance/")
                        else:
                            return HttpResponseRedirect("/dmt/clusters/" + str(cluster_id) + "/details/")
            except IntegrityError as e:
                fh.message = "Failed to add Service Unit Information for " + str(serviceGroupId.name) + ", Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the Service Unit Information, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
    else:
        InstName = dmt.mcast.getAvailableServiceName(serviceGroupId.id,False)
        #Get an address in the defined range that is not used and does not already exist in table
        try:
            instanceGateway,instanceIpAddress,instanceBitmask = dmt.utils.getServiceGroupInstanceIpAddress(cluster.id,False)
        except Exception as e:
            fh.message = "There was an issue generating an IP address for the Service Group Instance, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
        fh.form = ServiceGroupInstanceForm(
                initial={
                    'name': str(InstName),
                    'address': str(instanceIpAddress),
                    'bitmask': instanceBitmask,
                    'gateway': instanceGateway,
                    }
               )
        return fh.display()

@login_required
@transaction.atomic
def addInternalServiceGroupInstance(request, cluster_id, serviceGroupId):
    '''
    The ServiceGroupInstance is called to add the nstance to the Service Group.
    '''
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.request = request
    fh.button = "Save & Exit"
    fh.button2 = "Save & Add Another"

    try:
        cluster = Cluster.objects.get(id=cluster_id)
        serviceGroupId = ServiceGroup.objects.get(id=serviceGroupId)
    except Exception as e:
        fh.message = "No such deployment: " + str(cluster_id) + ", Exception :  " + str(e)
        logger.error(fh.message)
        return fh.display()

    fh.title = "Add Service Unit Information for Service Group: " + str(serviceGroupId.name)


    if request.method == 'POST':
        fh.form = ServiceGroupInstanceForm(request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested multicasts and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    instanceIpObj = IpAddress.objects.create(address=fh.form.cleaned_data['address'],bitmask=fh.form.cleaned_data['bitmask'],gateway_address=fh.form.cleaned_data['gateway'],ipType="serviceUnit_" + str(serviceGroupId.id),ipv4UniqueIdentifier=cluster_id)
                    instIpMapObj = ServiceGroupInstanceInternal.objects.create(name=fh.form.cleaned_data['name'],service_group=serviceGroupId,ipMap=instanceIpObj)
                    if "Save & Add Another" in request.POST:
                        return HttpResponseRedirect("/dmt/" + str(cluster_id) + "/serviceGroup/" + str(serviceGroupId.id) + "/addInternalInstance/")
                    else:
                        return HttpResponseRedirect("/dmt/clusters/" + str(cluster_id) + "/details/")
                    #return fh.success()
            except IntegrityError as e:
                fh.message = "Failed to add Service Unit Information for " + str(serviceGroupId.name) + ", Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the Service Unit Information, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
    else:
        InstName = dmt.mcast.getAvailableServiceName(serviceGroupId.id,True)
        #Get an address in the defined range that is not used and does not already exist in table
        try:
            instanceGateway,instanceIpAddress,instanceBitmask = dmt.utils.getServiceGroupInstanceIpAddress(cluster.id,True)
        except Exception as e:
            fh.message = "There was an issue generating an IP address for the Service Group Instance, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()

        fh.form = ServiceGroupInstanceFormInternal(
                initial={
                    'name': str(InstName),
                    'address': str(instanceIpAddress),
                    'bitmask': instanceBitmask,
                    'gateway': instanceGateway,
                    }
               )
        return fh.display()

@login_required
@transaction.atomic
def updateServiceGroupInstance(request, groupName, instanceId):
    '''
    The updateServiceGroup updates the Service Group table via the UI
    '''
    fh = FormHandle()
    fh.title = "Update JBOSS Cluster Service Unit"
    fh.request = request
    fh.button = "Save & Exit.."
    fh.button2 = "Cancel"
    serviceInstance = ServiceGroupInstance.objects.get(id=instanceId)
    instIpObj = IpAddress.objects.get(id=serviceInstance.ipMap_id)
    groupId = serviceInstance.service_group_id
    serviceGroupObj = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroupObj.service_cluster.cluster.id
    fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"

    fh.form = ServiceGroupInstanceForm(
                initial={
                    'name': serviceInstance.name,
                    'hostname': serviceInstance.hostname,
                    'address': serviceInstance.ipMap.address,
                    'bitmask': serviceInstance.ipMap.bitmask,
                    'gateway': serviceInstance.ipMap.gateway_address})
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = ServiceGroupInstanceForm(request.POST, instance=serviceInstance)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    serviceInstance.name = fh.form.cleaned_data['name']
                    if fh.form.cleaned_data['hostname'] != "":
                        serviceInstance.hostname = fh.form.cleaned_data['hostname']
                    else:
                        serviceInstance.hostname = None
                    instIpObj.address = fh.form.cleaned_data['address']
                    instIpObj.bitmask = fh.form.cleaned_data['bitmask']
                    instIpObj.gateway_address = fh.form.cleaned_data['gateway']
                    serviceInstance.save(force_update=True)
                    instIpObj.save(force_update=True)
                    return fh.success()
            except Exception as e:
                fh.message = "Failed to add Service Unit Information. Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the Service Unit Information, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
    else:
        return fh.display()

@login_required
@transaction.atomic
def updateInternalServiceGroupInstance(request, groupName, instanceId):
    '''
    The updateServiceGroup updates the Service Group table via the UI
    '''
    fh = FormHandle()
    fh.title = "Update JBOSS Cluster Service Unit"
    fh.request = request
    fh.button = "Save & Exit.."
    fh.button2 = "Cancel"

    serviceInstance = ServiceGroupInstanceInternal.objects.get(id=instanceId)
    instIpObj = IpAddress.objects.get(id=serviceInstance.ipMap_id)
    groupId = serviceInstance.service_group_id
    serviceGroupObj = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroupObj.service_cluster.cluster.id
    fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"

    fh.form = ServiceGroupInstanceFormInternal(
                initial={
                    'name': serviceInstance.name,
                    'address': serviceInstance.ipMap.address,
                    'bitmask': serviceInstance.ipMap.bitmask,
                    'gateway': serviceInstance.ipMap.gateway_address})
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        fh.form = ServiceGroupInstanceFormInternal(request.POST, instance=serviceInstance)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    serviceInstance.name = fh.form.cleaned_data['name']
                    instIpObj.address = fh.form.cleaned_data['address']
                    instIpObj.bitmask = fh.form.cleaned_data['bitmask']
                    instIpObj.gateway_address = fh.form.cleaned_data['gateway']
                    serviceInstance.save(force_update=True)
                    instIpObj.save(force_update=True)
                    return fh.success()
            except Exception as e:
                fh.message = "Failed to add Service Unit Information. Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the Service Unit Information, Exception : " +str(e)
            logger.error(fh.message)
            return fh.display()
    else:
        return fh.display()


@login_required
def deleteServiceGroupInstance(request, groupName, instanceId):
    '''
    Used to delete the Service instance according to the instanceId given
    '''
    serviceInstance = ServiceGroupInstance.objects.get(id=instanceId)
    instIpObj = IpAddress.objects.get(id=serviceInstance.ipMap_id)
    groupId = serviceInstance.service_group_id
    serviceGroupName = serviceInstance.service_group
    serviceGroupObj = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroupObj.service_cluster.cluster.id
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete Service Group for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        serviceInstance.delete()
        instIpObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except Exception as e:
        logger.error("Unable to delete jboss instance on service group: " + str(serviceGroupName) + " exception thrown: " + str(e))
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
def deleteInternalServiceGroupInstance(request, groupName, instanceId):
    '''
    Used to delete the Service instance according to the instanceId given
    '''

    serviceInstance = ServiceGroupInstanceInternal.objects.get(id=instanceId)
    instIpObj = IpAddress.objects.get(id=serviceInstance.ipMap_id)
    groupId = serviceInstance.service_group_id
    serviceGroupName = serviceInstance.service_group
    serviceGroupObj = ServiceGroup.objects.get(id=groupId)
    clusterId = serviceGroupObj.service_cluster.cluster.id
    clusterObj = Cluster.objects.get(id=clusterId)
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to delete Internal Service Group for Deployment: " + str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        serviceInstance.delete()
        instIpObj.delete()
        cursor = connection.cursor()
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    except Exception as e:
        logger.error("Unable to delete jboss instance on service group: " + str(serviceGroupName) + " exception thrown: " + str(e))
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")

@login_required
@transaction.atomic
def updateMgtServer(request, serverId):
    '''
    The updateMgtServer function is used to populate the edit MgtServer form
    '''
    nodeServerObject = Server.objects.get(id=serverId)
    mgtServer = nodeServerObject.hostname
    serverObject =  ManagementServer.objects.get(server=nodeServerObject)
    name = nodeServerObject.name
    domainName = nodeServerObject.domain_name
    hostname = nodeServerObject.hostname
    dnsServerA = nodeServerObject.dns_serverA
    dnsServerB = nodeServerObject.dns_serverB
    hardwareType = nodeServerObject.hardware_type
    userId = request.user.pk

    try:
        networkObject = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth0")
        nic = networkObject.mac_address
        action = "edit"
    except:
        networkObject = None
        nic = ""
        action = "add"
    try:
        networkObjectEth1 = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth1")
        nic_eth1 = networkObjectEth1.mac_address
    except:
        networkObjectEth1 = None
        nic_eth1 = ""
    try:
        networkObjectEth2 = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth2")
        nic_eth2 = networkObjectEth2.mac_address
    except:
        networkObjectEth2 = None
        nic_eth2 = ""
    try:
        networkObjectEth3 = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth3")
        nic_eth3 = networkObjectEth3.mac_address
    except:
        networkObjectEth3 = None
        nic_eth3 = ""

    if Ilo.objects.filter(server=nodeServerObject).exists():
        iloObject = Ilo.objects.get(server=nodeServerObject)
        iloIpObj = IpAddress.objects.get(id=iloObject.ipMapIloAddress_id)
        iloIpAddress = iloIpObj.address
        iloUsername = iloObject.username
        iloPassword = iloObject.password
    else:
        iloUsername = config.get('DMT_AUTODEPLOY', 'iloUsername')
        iloPassword = config.get('DMT_AUTODEPLOY', 'iloPassword')
        iloObject = "None"
        iloIpObj = "None"
        iloIpAddress = ""
        iloUsername = str(iloUsername)
        iloPassword = str(iloPassword)

    description = serverObject.description
    product = serverObject.product
    storageIpObject = bckUpIpObject = exIpAddrObject = None
    storageIp = bckUpIp = lmsIpInternal = exIpAddress = exBitmask = ""
    exIpv6AddrObject = None
    exIpv6Address = ""

    if networkObject != None:
        # IP address Info
        if IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
            storageIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="storage")
            storageIp = storageIpObject.address
        if IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
            bckUpIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="backup")
            bckUpIp = bckUpIpObject.address
        if IpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
            internalIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="internal")
            lmsIpInternal = internalIpObject.address
        else:
            internalGW,lmsIpInternal,internalBitmask=dmt.utils.getNextFreeInternalIPManagementServer(nodeServerObject)
        # This is the ip address of the server you would ssh in as
        if IpAddress.objects.filter(nic=networkObject.id,ipType="host").exists():
            exIpAddrObject = IpAddress.objects.get(nic=networkObject.id,ipType="host")
            exIpAddress = exIpAddrObject.address
            exBitmask = exIpAddrObject.bitmask
        if IpAddress.objects.filter(nic=networkObject.id,ipType="ipv6_host").exists():
            exIpv6AddrObject = IpAddress.objects.get(nic=networkObject.id,ipType="ipv6_host")
            exIpv6Address = exIpv6AddrObject.ipv6_address
    else:
        internalGW,lmsIpInternal,internalBitmask=dmt.utils.getNextFreeInternalIPManagementServer(nodeServerObject)

    try:
        enclosure = enclosureObject.hostname
    except:
        enclosure = Enclosure.objects.all()
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.form = UpdateMgtServerForm(
                initial={
                    'name': name,
                    'description': description,
                    'product': product,
                    'hostname': hostname,
                    'domain_name': domainName,
                    'dns_serverA': dnsServerA,
                    'dns_serverB': dnsServerB,
                    'mac_address': nic,
                    'mac_address_eth1': nic_eth1,
                    'mac_address_eth2': nic_eth2,
                    'mac_address_eth3': nic_eth3,
                    'external_ip_address' :exIpAddress,
                    'external_bitmask': exBitmask,
                    'external_ipv6_address': exIpv6Address,
                    'storageIp': storageIp,
                    'bckUpIp': bckUpIp,
                    'lmsIpInternal': lmsIpInternal,
                    'ilo_ip_address' : iloIpAddress,
                    'ilo_username' : iloUsername,
                    'ilo_password' : iloPassword
                    })
    fh.title = "Required Information for " + str(hardwareType) + " Management Server Form for: " + str(mgtServer)
    fh.request = request
    fh.button = "Save & Exit ..."
    fh.button2 = "Cancel"

    if request.method == 'POST':
        # redirect to Management Servers page
        fh.redirectTarget = "/dmt/mgtsvrs/" + str(serverId) + "/"
        if "Cancel" in request.POST:
            return fh.success()
        time = datetime.now()
        internalIpv4Identifier = str(hostname) + "-" + str(nodeServerObject.id)
        if "cloud" in hardwareType:
            hostnameIdentifier = macIdentifier = ipIdentifier = str(hostname) + "-" + str(nodeServerObject.id)
        else:
            hostnameIdentifier = macIdentifier = ipIdentifier = '1'
        fh.form = UpdateMgtServerForm(request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    message = dmt.utils.hostNameCheck(fh.form.cleaned_data['hostname'])
                    if message != "OK":
                        fh.message=message
                        return fh.display()

                    newValues = [str(fh.form.cleaned_data['name']),str(fh.form.cleaned_data['product']),str(fh.form.cleaned_data['hostname']),str(fh.form.cleaned_data['domain_name']),str(fh.form.cleaned_data['dns_serverA']),str(fh.form.cleaned_data['dns_serverB']),str(fh.form.cleaned_data['mac_address']),str(fh.form.cleaned_data['mac_address_eth1']),str(fh.form.cleaned_data['mac_address_eth2']),str(fh.form.cleaned_data['mac_address_eth3']),str(fh.form.cleaned_data['external_ip_address']),str(fh.form.cleaned_data['external_bitmask']),str(fh.form.cleaned_data['external_ipv6_address']),str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['lmsIpInternal']),str(fh.form.cleaned_data['ilo_ip_address']),str(fh.form.cleaned_data['ilo_username']),str(fh.form.cleaned_data['ilo_password']),str(fh.form.cleaned_data['description'])]
                    addressList = filter(None, [str(fh.form.cleaned_data['mac_address']),str(fh.form.cleaned_data['mac_address_eth1']),str(fh.form.cleaned_data['mac_address_eth2']),str(fh.form.cleaned_data['mac_address_eth3']),str(fh.form.cleaned_data['external_ip_address']),str(fh.form.cleaned_data['external_ipv6_address']),str(fh.form.cleaned_data['storageIp']),str(fh.form.cleaned_data['bckUpIp']),str(fh.form.cleaned_data['lmsIpInternal']),str(fh.form.cleaned_data['ilo_ip_address'])])
                    duplicates = dmt.utils.getDuplicatesInList(addressList)
                    if len(duplicates) > 0:
                        raise Exception("Duplicate IP Info "+str(duplicates))
                    #Checking for NIC, if doesn't exists it creates one.
                    macAddresses = NetworkInterface.objects.filter(server=nodeServerObject.id)
                    for networkInterface in macAddresses:
                        if not networkInterface.interface == "eth0":
                            networkInterface.delete()
                    if networkObject != None:
                        networkObject.mac_address = fh.form.cleaned_data['mac_address']
                        networkObject.nicIdentifier = macIdentifier
                    else:
                        networkObject=NetworkInterface.objects.create(server=nodeServerObject,mac_address = fh.form.cleaned_data['mac_address'],nicIdentifier=macIdentifier)
                    networkObject.save(force_update=True)
                    # Check the posted content to see has it changed
                    if str(action) == "edit":
                        oldValues = [str(name) + "##Machine Name",
                                str(product) + "##Product",
                                str(hostname) + "##Hostname",
                                str(domainName) + "##Domain Name",
                                str(dnsServerA) + "##DNS Server A",
                                str(dnsServerB) + "##DNS Server B",
                                str(nic) + "##Mac Aaddress (eth0)",
                                str(nic_eth1) + "##Mac Address (eth1)",
                                str(nic_eth2) + "##Mac Address (eth2)",
                                str(nic_eth3) + "##Mac Address(eth3)",
                                str(exIpAddress) + "##IPV4 IP Address",
                                str(exBitmask) + "##IPV4 Bitmask",
                                str(exIpv6Address) + "##IPV6 IP Address",
                                str(storageIp) + "##Storage IP",
                                str(bckUpIp) + "##Backup IP",
                                str(lmsIpInternal) + "##MS Internal IP",
                                str(iloIpAddress) + "##ILO IP Address",
                                str(iloUsername) + "##ILO Username",
                                str(iloPassword) + "##ILO Password",
                                str(description) + "##Description"]
                        changedContent = logChange(oldValues,newValues)
                    #checking if Ip Address are already in the database, delete them to allow switch of ip addresses on one update
                    if IpAddress.objects.filter(nic=networkObject,ipType="host",address = fh.form.cleaned_data['external_ip_address']).exists():
                        IpAddress.objects.filter(nic=networkObject,ipType="host",address = fh.form.cleaned_data['external_ip_address']).delete()
                    exIpv6AddrInput = dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['external_ipv6_address'])
                    if IpAddress.objects.filter(nic=networkObject,ipType="ipv6_host",ipv6_address = exIpv6AddrInput).exists():
                        IpAddress.objects.filter(nic=networkObject,ipType="ipv6_host",ipv6_address = exIpv6AddrInput).delete()
                    if IpAddress.objects.filter(nic=networkObject,ipType="storage",address = fh.form.cleaned_data['storageIp']).exists():
                        IpAddress.objects.filter(nic=networkObject,ipType="storage",address = fh.form.cleaned_data['storageIp']).delete()
                    if IpAddress.objects.filter(nic=networkObject,ipType="backup",address = fh.form.cleaned_data['bckUpIp']).exists():
                        IpAddress.objects.filter(nic=networkObject,ipType="backup",address = fh.form.cleaned_data['bckUpIp']).delete()
                    if IpAddress.objects.filter(nic=networkObject,ipType="internal",address = fh.form.cleaned_data['lmsIpInternal']).exists():
                        IpAddress.objects.filter(nic=networkObject,ipType="internal",address = fh.form.cleaned_data['lmsIpInternal']).delete()

                    if fh.form.cleaned_data['mac_address_eth1'] != "":
                        exists = NetworkInterface.objects.filter(server_id=nodeServerObject.id,interface="eth1",nicIdentifier=macIdentifier).exists()
                        if exists:
                            exists.mac_address = fh.form.cleaned_data['mac_address_eth1']
                            exists.save(force_update=True)
                            networkObjectEth1 = NetworkInterface.objects.filter(server_id=nodeServerObject.id,interface="eth1",nicIdentifier=macIdentifier)
                        else:
                            networkObjectEth1=NetworkInterface.objects.create(server=nodeServerObject,interface="eth1",mac_address = fh.form.cleaned_data['mac_address_eth1'],nicIdentifier=macIdentifier)
                    if fh.form.cleaned_data['mac_address_eth2'] != "":
                        exists = NetworkInterface.objects.filter(server_id=nodeServerObject.id,interface="eth2",nicIdentifier=macIdentifier).exists()
                        if exists:
                            exists.mac_address = fh.form.cleaned_data['mac_address_eth2']
                            exists.save(force_update=True)
                            networkObjectEth2 = NetworkInterface.objects.filter(server_id=nodeServerObject.id,interface="eth2",nicIdentifier=macIdentifier)
                        else:
                            networkObjectEth2=NetworkInterface.objects.create(server=nodeServerObject,interface="eth2",mac_address = fh.form.cleaned_data['mac_address_eth2'],nicIdentifier=macIdentifier)

                    if fh.form.cleaned_data['mac_address_eth3'] != "":
                        exists = NetworkInterface.objects.filter(server_id=nodeServerObject.id,interface="eth3",nicIdentifier=macIdentifier).exists()
                        if exists:
                            exists.mac_address = fh.form.cleaned_data['mac_address_eth3']
                            exists.save(force_update=True)
                            networkObjectEth3 = NetworkInterface.objects.filter(server_id=nodeServerObject.id,interface="eth3",nicIdentifier=macIdentifier)
                        else:
                            networkObjectEth3=NetworkInterface.objects.create(server=nodeServerObject,interface="eth3",mac_address = fh.form.cleaned_data['mac_address_eth3'],nicIdentifier=macIdentifier)
                    # Update the Management Server Model
                    nodeServerObject.name = fh.form.cleaned_data['name']
                    nodeServerObject.hostname = fh.form.cleaned_data['hostname']
                    nodeServerObject.hostnameIdentifier = hostnameIdentifier
                    nodeServerObject.domain_name = fh.form.cleaned_data['domain_name']
                    nodeServerObject.dns_serverA = fh.form.cleaned_data['dns_serverA']
                    nodeServerObject.dns_serverB = fh.form.cleaned_data['dns_serverB']

                    # IPv4 Host Address
                    if fh.form.cleaned_data['external_ip_address'] != "":
                        if hardwareType != "cloud":
                            if fh.form.cleaned_data['external_bitmask'] == "":
                                fh.message = "WARNING : Please ensure you add a bitmask for the IPv4 Host Address"
                                logger.error(fh.message)
                                return fh.display()
                        if not IpAddress.objects.filter(nic=networkObject.id,ipType="host").exists():
                            exIpAddrObject = IpAddress.objects.create(nic=networkObject,ipType="host",ipv4UniqueIdentifier=ipIdentifier,address=fh.form.cleaned_data['external_ip_address'],bitmask=fh.form.cleaned_data['external_bitmask'])
                        exIpAddrObject.address = fh.form.cleaned_data['external_ip_address']
                        exIpAddrObject.ipv4UniqueIdentifier = ipIdentifier
                        exIpAddrObject.bitmask = fh.form.cleaned_data['external_bitmask']
                        exIpAddrObject.save(force_update=True)

                    # Need the else state below to remove the entry if they wish to remove reference to below IP addresses as the address field is unique
                    # and we can't have multiple blank addresses within the address field

                    # IPv6 Host Address
                    if fh.form.cleaned_data['external_ipv6_address'] != "":
                        if not IpAddress.objects.filter(nic=networkObject.id,ipType="ipv6_host").exists():
                            exIpv6AddrObject = IpAddress.objects.create(nic=networkObject,ipType="ipv6_host",ipv6UniqueIdentifier=ipIdentifier,ipv6_address=fh.form.cleaned_data['external_ipv6_address'])
                        exIpv6AddrObject.ipv6_address = fh.form.cleaned_data['external_ipv6_address']
                        exIpv6AddrObject.ipv6UniqueIdentifier = ipIdentifier
                        exIpv6AddrObject.save(force_update=True)
                    elif IpAddress.objects.filter(nic=networkObject.id,ipType="ipv6_host").exists():
                        IpAddress.objects.filter(nic=networkObject,ipType="ipv6_host").delete()

                    # IPv4 Storage Address
                    if fh.form.cleaned_data['storageIp'] != "":
                        if not IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
                            storageIpObject = IpAddress.objects.create(nic=networkObject,ipType="storage",ipv4UniqueIdentifier=ipIdentifier,address=fh.form.cleaned_data['storageIp'])
                        storageIpObject.address = fh.form.cleaned_data['storageIp']
                        storageIpObject.ipv4UniqueIdentifier = ipIdentifier
                        storageIpObject.save(force_update=True)
                    elif IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
                        IpAddress.objects.filter(nic=networkObject.id,ipType="storage").delete()

                    # IPv4 Backup Address
                    if fh.form.cleaned_data['bckUpIp'] != "":
                        if not IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
                            bckUpIpObject = IpAddress.objects.create(nic=networkObject,ipType="backup",ipv4UniqueIdentifier=ipIdentifier,address=fh.form.cleaned_data['bckUpIp'])
                        bckUpIpObject.address = fh.form.cleaned_data['bckUpIp']
                        bckUpIpObject.ipv4UniqueIdentifier = ipIdentifier
                        bckUpIpObject.save(force_update=True)
                    elif IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
                        IpAddress.objects.filter(nic=networkObject.id,ipType="backup").delete()

                    # IPv4 Internal Address
                    if fh.form.cleaned_data['lmsIpInternal'] != "":
                        if not IpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                            internalIpObject = IpAddress.objects.create(nic=networkObject,ipType="internal",ipv4UniqueIdentifier=internalIpv4Identifier,address=fh.form.cleaned_data['lmsIpInternal'])
                        internalIpObject.address = fh.form.cleaned_data['lmsIpInternal']
                        internalIpObject.ipv4UniqueIdentifier = internalIpv4Identifier
                        internalIpObject.save(force_update=True)
                    elif IpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                        IpAddress.objects.filter(nic=networkObject.id,ipType="internal").delete()

                    # Edit Mgmt Server ILO option and add if Ilo does not exist
                    if hardwareType != "cloud":
                        if fh.form.cleaned_data['ilo_ip_address'] != "" and ( fh.form.cleaned_data['ilo_username'] == "" or fh.form.cleaned_data['ilo_password'] == "" ):
                            fh.message = "WARNING : Please ensure ILO information is filled in entirely. Alternatively you can leave all ILO fields blank"
                            logger.error(fh.message)
                            return fh.display()
                        if fh.form.cleaned_data['ilo_ip_address'] != "" and fh.form.cleaned_data['ilo_username'] != "" and fh.form.cleaned_data['ilo_password'] != "":
                            iloAdd = fh.form.cleaned_data['ilo_ip_address']
                            iloUnE = fh.form.cleaned_data['ilo_username']
                            iloPwd = fh.form.cleaned_data['ilo_password']
                            if iloObject != "None":
                                iloIpObj.address = iloAdd
                                iloObject.username = iloUnE
                                iloObject.password = iloPwd
                                iloIpObj.save(force_update=True)
                                iloObject.ipMapIloAddress = iloIpObj
                                iloObject.save(force_update=True)
                            else:
                                try:
                                    iloIpObj = IpAddress.objects.create(address=iloAdd,ipType="ilo_" + str(nodeServerObject.id))
                                    iloObj = Ilo.objects.create(ipMapIloAddress=iloIpObj,server=nodeServerObject,username=iloUnE,password=iloPwd)
                                    iloIpObj.save(force_update=True)
                                    iloObj.save(force_update=True)
                                except Exception as e:
                                    errMsg = "Issue Adding update ILO Address information to DB: " +str(e)
                                    logger.error(errMsg)
                                    fh.message = errMsg
                                    return fh.display()
                        else:
                            if iloObject != "None":
                                if iloIpObj != "None":
                                    iloIpObj.delete()
                                iloObject.delete()

                    product = fh.form.cleaned_data['product']
                    productObj = Product.objects.get(name=product)
                    serverObject.product = productObj
                    serverObject.description = fh.form.cleaned_data['description']
                    nodeServerObject.save(force_update=True)
                    serverObject.save(force_update=True)
                    networkObject.save(force_update=True)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if action == "edit":
                        message = "Edited Server Configuration, " + str(changedContent)
                    else:
                        message = "Added Server Configuration (Stage 2)"
                    logAction(userId, serverObject, action, message)
                    return fh.success()
            except IntegrityError as e:
                message = "Problem updating Management Server " +str(mgtServer)+ " in the database, Exception : " + str(e)
                logger.warn(message)
                fh.message = message + " -- Please Try Again"
                return fh.display()
            except Exception as e:
                message = "Problem updating Management Server " +str(mgtServer)+ " in the database, Exception : " + str(e)
                logger.warn(message)
                fh.message = message + " -- Please Try Again"
                return fh.display()
        else:
            fh.message = "Form is invalid - Please try Again"
            logger.warn(fh.message)
            return fh.display()
    else:
        return fh.display()

@login_required
def deleteMgtServer(request, serverId):
    '''
    The deleteMgtServer function is used to delete the selected Management Server
    '''
    # Deleting the selected Management Server
    nodeServerObject = Server.objects.get(id=serverId)
    mgtServer = nodeServerObject.hostname
    serverObject =  ManagementServer.objects.get(server=nodeServerObject)
    try:
        networkObject = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth0")
    except:
        logger.info("Management Server " +str(mgtServer)+ " has no NICs defined")
    clusters = Cluster.objects.filter(management_server=serverObject)
    # Info Required for the logging User Activity
    dictDeletedInfo = {}
    dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(serverObject).pk
    dictDeletedInfo["objectId"] = serverObject.pk
    dictDeletedInfo["objectRep"] = force_unicode(serverObject)
    userId = request.user.pk
    action = "delete"
    message = "Deleted"
    if not clusters:
        try:
            try:
                if IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
                    bckUpIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="backup")
                if IpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                    internalIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="internal")
                if IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                    multicastIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                if IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
                    storageIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="storage")
            except:
                logger.info("Management Server " +str(mgtServer)+ " has no NICs defined")
            try:
                if Ilo.objects.filter(server=nodeServerObject).exists():
                    iloObject = Ilo.objects.get(server=nodeServerObject)
                    iloIpObj = iloObject.ipMapIloAddress
                    iloIpObj.delete()
                    iloObject.delete()
            except:
                logger.info("No ilo Info defined for Management Server " + str(mgtServer))
            if ManagementServerCredentialMapping.objects.filter(mgtServer_id=serverObject.id).exists():
                mgtServCredMap= ManagementServerCredentialMapping.objects.get(mgtServer_id=serverObject.id)
                credentials =  Credentials.objects.get(id=mgtServCredMap.credentials.id)
                credentials.delete()
                mgtServCredMap.delete()
            ManagementServer.objects.filter(server=nodeServerObject).delete()
            Server.objects.filter(id=serverId).delete()
            try:
                NetworkInterface.objects.filter(server=nodeServerObject.id).delete()
            except:
                logger.info("Management Server " +str(mgtServer)+ " has no NICs defined")
            try:
                IpAddress.objects.filter(nic=networkObject.id).delete()
            except:
                logger.info("Management Server " +str(mgtServer)+ " has no IPs defined")
            cursor = connection.cursor()
        except Exception as e:
            raise CommandError("There was an issue deleting managment server " +str(mgtServer)+ " from database: " +str(e))
        logAction(userId, serverObject, action, message, dictDeletedInfo)
        return HttpResponseRedirect("/dmt/mgtsvrs/")
    else:
        logger.error("There was an issue deleting " +str(mgtServer)+ " from database : it has deployments" )
        error = "There was an issue deleting " + str(mgtServer) + ", it  has deployment(s): All deployment(s) must be deleted before Management Server can be deleted."
        return render(request, "dmt/dmt_error.html", {'error': error})

@login_required
@transaction.atomic
def updateNASServer(request, nasServerId, option):
    '''
    The updateNASServer function is used to populate the edit MgtServer form
    '''
    userId = request.user.pk
    nodeServerObject = Server.objects.get(id=nasServerId)
    serverObject = NASServer.objects.filter(server=nodeServerObject.id)
    for item in serverObject:
        nasServerObject = NASServer.objects.get(id=item.id)
        break
    hardwareType = nodeServerObject.hardware_type
    if "cloud" in hardwareType:
        hostnameIdentifier = macIdentifier = ipv4Identifier = ipv6Identifier = nodeServerObject.id
    else:
        hostnameIdentifier = macIdentifier = ipv4Identifier = ipv6Identifier = '1'

    if "edit" in option or "add" in option:
        credentials = []
        try:
            networkObject = NetworkInterface.objects.get(server=nodeServerObject.id,interface="eth0",nicIdentifier=macIdentifier)
            mac = networkObject.mac_address
        except:
            mac = ""
        try:
            ipAddrObject = IpAddress.objects.get(nic_id=networkObject.id,ipType="nas",ipv4UniqueIdentifier=ipv4Identifier)
            ipAddress = ipAddrObject.address
            bitmask = ipAddrObject.bitmask
            gateway = ipAddrObject.gateway_address
        except:
            ipAddress = ""
            bitmask = ""
            gateway = ""
        try:
            ipAddrObjectNASVIP1 = IpAddress.objects.get(nic_id=networkObject.id,ipType="nasvip1",ipv4UniqueIdentifier=ipv4Identifier)
            nasvip1 = ipAddrObjectNASVIP1.address
        except:
            nasvip1 = ""

        try:
            ipAddrObjectNASVIP2 = IpAddress.objects.get(nic_id=networkObject.id,ipType="nasvip2",ipv4UniqueIdentifier=ipv4Identifier)
            nasvip2 = ipAddrObjectNASVIP2.address
        except:
            nasvip2 = ""

        try:
            ipAddrObjNasInstallIp1 = IpAddress.objects.get(nic_id=networkObject.id,ipType="nasinstallip1",ipv4UniqueIdentifier=ipv4Identifier)
            nasInstallIp1 = ipAddrObjNasInstallIp1.address
        except:
            nasInstallIp1 = ""

        try:
            ipAddrObjNasInstallIp2 = IpAddress.objects.get(nic_id=networkObject.id,ipType="nasinstallip2",ipv4UniqueIdentifier=ipv4Identifier)
            nasInstallIp2 = ipAddrObjNasInstallIp2.address
        except:
            nasInstallIp2 = ""

        try:
            ipAddrObjNasIloInstallIp1 = IpAddress.objects.get(nic_id=networkObject.id, ipType="nasInstalIlolIp1", ipv4UniqueIdentifier=ipv4Identifier)
            nasInstalIlolIp1 = ipAddrObjNasIloInstallIp1.address
        except:
            nasInstalIlolIp1 = ""

        try:
            ipAddrObjNasIloInstallIp2 = IpAddress.objects.get(nic_id=networkObject.id, ipType="nasInstalIlolIp2", ipv4UniqueIdentifier=ipv4Identifier)
            nasInstalIlolIp2 = ipAddrObjNasIloInstallIp2.address
        except:
            nasInstalIlolIp2 = ""

        for obj in serverObject:
            credentials += Credentials.objects.filter(id=obj.credentials_id)

        masterIloUsername = ''
        masterIloPassword = ''
        supportIloUsername = ''
        supportIloPassword = ''
        nasInstallIloIp1Username = ''
        nasInstalIlolIp1Password = ''
        nasInstallIloIp2Username = ''
        nasInstalIlolIp2Password = ''

        masterIloCredentialsObj = None
        supportIloCredentialsObj= None
        nasInstallIloIp1CredentialsObj= None
        nasInstallIloIp2CredentialsObj= None
        sfsNode1Hostname = ''
        sfsNode2Hostname= ''

        for item in credentials:
            if item.credentialType == 'master':
                masterUsername=item.username
                masterPassword=item.password
                masterCredentialsObj = Credentials.objects.get(id=item.id)
            elif item.credentialType == 'support':
                supportUsername=item.username
                supportPassword=item.password
                supportCredentialsObj = Credentials.objects.get(id=item.id)
            elif item.credentialType == 'masterIlo':
                masterIloUsername = item.username
                masterIloPassword = item.password
                masterIloCredentialsObj = Credentials.objects.get(id = item.id)
            elif item.credentialType == 'supportIlo':
                supportIloUsername = item.username
                supportIloPassword = item.password
                supportIloCredentialsObj = Credentials.objects.get(id = item.id)
            elif item.credentialType == 'nasInstalIlolIp1':
                nasInstallIloIp1Username = item.username
                nasInstalIlolIp1Password = item.password
                nasInstallIloIp1CredentialsObj = Credentials.objects.get(id = item.id)
            elif item.credentialType == 'nasInstalIlolIp2':
                nasInstallIloIp2Username = item.username
                nasInstalIlolIp2Password = item.password
                nasInstallIloIp2CredentialsObj = Credentials.objects.get(id = item.id)

        # Create a FormHandle to handle form post-processing
        fh = FormHandle()
        fh.form = UpdateNASServerForm(hardwareType,
                initial={
                    'name': nodeServerObject.name,
                    'domain_name': nodeServerObject.domain_name,
                    'hostname': nodeServerObject.hostname,
                    'dns_serverA': nodeServerObject.dns_serverA,
                    'dns_serverB': nodeServerObject.dns_serverB,
                    'mac_address': mac,
                    'ip_address' : ipAddress,
                    'bitmask': bitmask,
                    'gateway_address': gateway,
                    'nasvip1': nasvip1,
                    'nasvip2': nasvip2,
                    'nasinstallip1': nasInstallIp1,
                    'nasinstallip2': nasInstallIp2,
                    'masterUsername': masterUsername,
                    'masterPassword': masterPassword,
                    'supportUsername': supportUsername,
                    'supportPassword': supportPassword,
                    'nasInstalIlolIp1': nasInstalIlolIp1,
                    'nasInstallIloIp1Username': nasInstallIloIp1Username,
                    'nasInstalIlolIp1Password': nasInstalIlolIp1Password,
                    'masterIloUsername': masterIloUsername,
                    'masterIloPassword': masterIloPassword,
                    'nasInstalIlolIp2': nasInstalIlolIp2,
                    'nasInstallIloIp2Username': nasInstallIloIp2Username,
                    'nasInstalIlolIp2Password': nasInstalIlolIp2Password,
                    'supportIloUsername': supportIloUsername,
                    'supportIloPassword': supportIloPassword,
                    'sfsNode1Hostname': nasServerObject.sfs_node1_hostname,
                    'sfsNode2Hostname': nasServerObject.sfs_node2_hostname
                })
        fh.title = "Update NAS Server Form for: " + str(nodeServerObject.hostname)
        fh.request = request
        fh.button = "Save & Exit..."
        fh.button2 = "Cancel"
        fh.redirectTarget = "/dmt/nassvrs/"

        if request.method == 'POST':
            if "Cancel" in request.POST:
                return fh.success()
            fh.form = UpdateNASServerForm(hardwareType, request.POST)
            # validate the form so that the cleaned_data gets populated, then we can get the
            # requested name and define our redirect URL
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        if hardwareType != 'virtual' and hardwareType != 'cloud':
                            oldValues = [str(nodeServerObject.name) + "##Machine Name",
                                str(nodeServerObject.domain_name) + "##Domain Name",
                                str(nodeServerObject.hostname) + "##Hostname",
                                str(nodeServerObject.dns_serverA) + "##DNS Server A",
                                str(nodeServerObject.dns_serverB) + "##DNS Server B",
                                str(mac) + "##MAC Address",
                                str(ipAddress) + "##IPv4 Address",
                                str(bitmask) + "##Bitmask",
                                str(gateway) + "##Gateway",
                                str(nasvip1) + "##NAS VIP1 Address",
                                str(nasvip2) + "##NAS VIP2 Address",
                                str(nasInstallIp1) + "##NAS INSTALL 1 Address",
                                str(nasInstallIp2) + "##NAS INSTALL 2 Address",
                                str(masterUsername) + "##Username (master)",
                                str(masterPassword) + "##Password (master)",
                                str(supportUsername) + "##Username (support)",
                                str(supportPassword) + "##Password (support)",
                                str(nasInstalIlolIp1) + "##NAS INSTALL ILO 1 Address",
                                str(nasInstalIlolIp2) + "##NAS INSTALL ILO 2 Address",
                                str(masterIloUsername) + "##Username (master ilo)",
                                str(masterIloPassword) + "##Password (master ilo)",
                                str(supportIloUsername) + "##Username (support ilo)",
                                str(supportIloPassword) + "##Password (support ilo)",
                                str(nasInstallIloIp1Username) + "##Username (nasInstalIlolIp1)",
                                str(nasInstalIlolIp1Password) + "##Password (nasInstalIlolIp1)",
                                str(nasInstallIloIp2Username) + "##Username (nasInstalIlolIp2)",
                                str(nasInstalIlolIp2Password) + "##Password (nasInstalIlolIp2)",
                                str(sfsNode1Hostname) + "##SFS Node 1 Hostname",
                                str(sfsNode2Hostname) + "##SFS Node 2 Hostname"]
                            newValues = [str(fh.form.cleaned_data['name']), str(fh.form.cleaned_data['domain_name']),
                                         str(fh.form.cleaned_data['hostname']),
                                         str(fh.form.cleaned_data['dns_serverA']),
                                         str(fh.form.cleaned_data['dns_serverB']),
                                         str(fh.form.cleaned_data['mac_address']),
                                         str(fh.form.cleaned_data['ip_address']), str(fh.form.cleaned_data['bitmask']),
                                         str(fh.form.cleaned_data['gateway_address']),
                                         str(fh.form.cleaned_data['nasvip1']), str(fh.form.cleaned_data['nasvip2']),
                                         str(fh.form.cleaned_data['nasinstallip1']),
                                         str(fh.form.cleaned_data['nasinstallip2']),
                                         str(fh.form.cleaned_data['masterUsername']),
                                         str(fh.form.cleaned_data['masterPassword']),
                                         str(fh.form.cleaned_data['supportUsername']),
                                         str(fh.form.cleaned_data['supportPassword']),
                                         str(fh.form.cleaned_data['nasInstalIlolIp1']),
                                         str(fh.form.cleaned_data['nasInstalIlolIp2']),
                                         str(fh.form.cleaned_data['masterIloUsername']),
                                         str(fh.form.cleaned_data['masterIloPassword']),
                                         str(fh.form.cleaned_data['supportIloUsername']),
                                         str(fh.form.cleaned_data['supportIloPassword']),
                                         str(fh.form.cleaned_data['nasInstallIloIp1Username']),
                                         str(fh.form.cleaned_data['nasInstalIlolIp1Password']),
                                         str(fh.form.cleaned_data['nasInstallIloIp2Username']),
                                         str(fh.form.cleaned_data['nasInstalIlolIp2Password']),
                                         str(fh.form.cleaned_data['sfsNode1Hostname']),
                                         str(fh.form.cleaned_data['sfsNode2Hostname'])]
                            addressList = filter(None, [str(fh.form.cleaned_data['mac_address']),
                                                        str(fh.form.cleaned_data['ip_address']),
                                                        str(fh.form.cleaned_data['gateway_address']),
                                                        str(fh.form.cleaned_data['nasvip1']),
                                                        str(fh.form.cleaned_data['nasvip2']),
                                                        str(fh.form.cleaned_data['nasinstallip1']),
                                                        str(fh.form.cleaned_data['nasinstallip2']),
                                                        str(fh.form.cleaned_data['nasInstalIlolIp1']),
                                                        str(fh.form.cleaned_data['nasInstalIlolIp2'])])
                        else:
                            oldValues = [str(nodeServerObject.name) + "##Machine Name",
                                         str(nodeServerObject.domain_name) + "##Domain Name",
                                         str(nodeServerObject.hostname) + "##Hostname",
                                         str(nodeServerObject.dns_serverA) + "##DNS Server A",
                                         str(nodeServerObject.dns_serverB) + "##DNS Server B",
                                         str(mac) + "##MAC Address",
                                         str(ipAddress) + "##IPv4 Address",
                                         str(bitmask) + "##Bitmask",
                                         str(gateway) + "##Gateway",
                                         str(nasvip1) + "##NAS VIP1 Address",
                                         str(nasvip2) + "##NAS VIP2 Address",
                                         str(nasInstallIp1) + "##NAS INSTALL 1 Address",
                                         str(nasInstallIp2) + "##NAS INSTALL 2 Address",
                                         str(masterUsername) + "##Username (master)",
                                         str(masterPassword) + "##Password (master)",
                                         str(supportUsername) + "##Username (support)",
                                         str(supportPassword) + "##Password (support)",
                                         str(nasInstallIloIp1Username) + "##Username (nasInstalIlolIp1)",
                                         str(nasInstalIlolIp1Password) + "##Password (nasInstalIlolIp1)",
                                         str(nasInstallIloIp2Username) + "##Username (nasInstalIlolIp2)",
                                         str(nasInstalIlolIp2Password) + "##Password (nasInstalIlolIp2)",
                                         str(sfsNode1Hostname) + "##SFS Node 1 Hostname",
                                         str(sfsNode2Hostname) + "##SFS Node 2 Hostname"]
                            newValues = [str(fh.form.cleaned_data['name']), str(fh.form.cleaned_data['domain_name']),
                                         str(fh.form.cleaned_data['hostname']),
                                         str(fh.form.cleaned_data['dns_serverA']),
                                         str(fh.form.cleaned_data['dns_serverB']),
                                         str(fh.form.cleaned_data['mac_address']),
                                         str(fh.form.cleaned_data['ip_address']), str(fh.form.cleaned_data['bitmask']),
                                         str(fh.form.cleaned_data['gateway_address']),
                                         str(fh.form.cleaned_data['nasvip1']), str(fh.form.cleaned_data['nasvip2']),
                                         str(fh.form.cleaned_data['nasinstallip1']),
                                         str(fh.form.cleaned_data['nasinstallip2']),
                                         str(fh.form.cleaned_data['masterUsername']),
                                         str(fh.form.cleaned_data['masterPassword']),
                                         str(fh.form.cleaned_data['supportUsername']),
                                         str(fh.form.cleaned_data['supportPassword']),
                                         str(fh.form.cleaned_data['nasInstallIloIp1Username']),
                                         str(fh.form.cleaned_data['nasInstalIlolIp1Password']),
                                         str(fh.form.cleaned_data['nasInstallIloIp2Username']),
                                         str(fh.form.cleaned_data['nasInstalIlolIp2Password']),
                                         str(fh.form.cleaned_data['sfsNode1Hostname']),
                                         str(fh.form.cleaned_data['sfsNode2Hostname'])]
                            addressList = filter(None, [str(fh.form.cleaned_data['mac_address']),
                                                        str(fh.form.cleaned_data['ip_address']),
                                                        str(fh.form.cleaned_data['gateway_address']),
                                                        str(fh.form.cleaned_data['nasvip1']),
                                                        str(fh.form.cleaned_data['nasvip2']),
                                                        str(fh.form.cleaned_data['nasinstallip1']),
                                                        str(fh.form.cleaned_data['nasinstallip2'])])

                        duplicates = dmt.utils.getDuplicatesInList(addressList)
                        if len(duplicates) > 0:
                            raise Exception("Duplicate IP Info "+str(duplicates))
                        changedContent = logChange(oldValues,newValues)
                        # Update the Management Server Model
                        nodeServerObject.name = fh.form.cleaned_data['name']
                        nodeServerObject.hostname = fh.form.cleaned_data['hostname']
                        nodeServerObject.domain_name = fh.form.cleaned_data['domain_name']
                        nodeServerObject.dns_serverA = fh.form.cleaned_data['dns_serverA']
                        nodeServerObject.dns_serverB = fh.form.cleaned_data['dns_serverB']
                        nodeServerObject.hostnameIdentifier = hostnameIdentifier
                        nasServerObject.sfs_node1_hostname = fh.form.cleaned_data['sfsNode1Hostname']
                        nasServerObject.sfs_node2_hostname = fh.form.cleaned_data['sfsNode2Hostname']

                        if not NetworkInterface.objects.filter(server_id=nodeServerObject.id,nicIdentifier=macIdentifier).exists():
                            networkObject=NetworkInterface.objects.create(server=nodeServerObject,mac_address = fh.form.cleaned_data['mac_address'],nicIdentifier=macIdentifier)

                        networkObject.mac_address = fh.form.cleaned_data['mac_address']
                        networkObject.nicIdentifier=macIdentifier

                        if not IpAddress.objects.filter(nic=networkObject.id,ipType="nas",ipv4UniqueIdentifier=ipv4Identifier).exists():
                            ipAddrObject = IpAddress.objects.create(nic=networkObject,ipType="nas",address = fh.form.cleaned_data['ip_address'],bitmask=fh.form.cleaned_data['bitmask'], gateway_address = fh.form.cleaned_data['gateway_address'],ipv4UniqueIdentifier=ipv4Identifier)
                        ipAddrObject.address = fh.form.cleaned_data['ip_address']
                        ipAddrObject.bitmask = fh.form.cleaned_data['bitmask']
                        ipAddrObject.gateway_address = fh.form.cleaned_data['gateway_address']
                        ipAddrObject.ipType = "nas"
                        ipAddrObject.ipv4UniqueIdentifier=ipv4Identifier

                        if fh.form.cleaned_data['nasvip1'] == "":
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="nasvip1",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                IpAddress.objects.filter(nic=networkObject.id,ipType="nasvip1",ipv4UniqueIdentifier=ipv4Identifier).delete()
                        else:
                            if not IpAddress.objects.filter(nic=networkObject.id,ipType="nasvip1",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                ipAddrObjectNASVIP1 = IpAddress.objects.create(nic=networkObject,ipType="nasvip1",address = fh.form.cleaned_data['nasvip1'],ipv4UniqueIdentifier=ipv4Identifier)

                        if fh.form.cleaned_data['nasvip2'] == "":
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="nasvip2",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                IpAddress.objects.filter(nic=networkObject.id,ipType="nasvip2",ipv4UniqueIdentifier=ipv4Identifier).delete()
                        else:
                            if not IpAddress.objects.filter(nic=networkObject.id,ipType="nasvip2",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                ipAddrObjectNASVIP2 = IpAddress.objects.create(nic=networkObject,ipType="nasvip2",address = fh.form.cleaned_data['nasvip2'],ipv4UniqueIdentifier=ipv4Identifier)

                        if fh.form.cleaned_data['nasinstallip1'] == "":
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="nasinstallip1",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                IpAddress.objects.filter(nic=networkObject.id,ipType="nasinstallip1",ipv4UniqueIdentifier=ipv4Identifier).delete()
                        else:
                            if not IpAddress.objects.filter(nic=networkObject.id,ipType="nasinstallip1",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                ipAddrObjNasInstallIp1 = IpAddress.objects.create(nic=networkObject,ipType="nasinstallip1",address = fh.form.cleaned_data['nasinstallip1'],ipv4UniqueIdentifier=ipv4Identifier)

                        if fh.form.cleaned_data['nasinstallip2'] == "":
                            if IpAddress.objects.filter(nic=networkObject.id,ipType="nasinstallip2",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                IpAddress.objects.filter(nic=networkObject.id,ipType="nasinstallip2",ipv4UniqueIdentifier=ipv4Identifier).delete()
                        else:
                            if not IpAddress.objects.filter(nic=networkObject.id,ipType="nasinstallip2",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                ipAddrObjNasInstallIp2 = IpAddress.objects.create(nic=networkObject,ipType="nasinstallip2",address = fh.form.cleaned_data['nasinstallip2'],ipv4UniqueIdentifier=ipv4Identifier)

                        masterCredentialsObj.username = fh.form.cleaned_data['masterUsername']
                        masterCredentialsObj.password = fh.form.cleaned_data['masterPassword']

                        supportCredentialsObj.username = fh.form.cleaned_data['supportUsername']
                        supportCredentialsObj.password = fh.form.cleaned_data['supportPassword']

                        nodeServerObject.save(force_update=True)
                        nasServerObject.save(force_update=True)
                        networkObject.save(force_update=True)
                        ipAddrObject.save(force_update=True)
                        masterCredentialsObj.save(force_update=True)
                        supportCredentialsObj.save(force_update=True)

                        if fh.form.cleaned_data['nasvip1'] != "":
                            ipAddrObjectNASVIP1.address = fh.form.cleaned_data['nasvip1']
                            ipAddrObjectNASVIP1.ipv4UniqueIdentifier = ipv4Identifier
                            ipAddrObjectNASVIP1.save(force_update=True)
                        if fh.form.cleaned_data['nasvip2'] != "":
                            ipAddrObjectNASVIP2.address = fh.form.cleaned_data['nasvip2']
                            ipAddrObjectNASVIP2.ipv4UniqueIdentifier = ipv4Identifier
                            ipAddrObjectNASVIP2.save(force_update=True)
                        if fh.form.cleaned_data['nasinstallip1'] != "":
                            ipAddrObjNasInstallIp1.address = fh.form.cleaned_data['nasinstallip1']
                            ipAddrObjNasInstallIp1.ipv4UniqueIdentifier = ipv4Identifier
                            ipAddrObjNasInstallIp1.save(force_update=True)
                        if fh.form.cleaned_data['nasinstallip2'] != "":
                            ipAddrObjNasInstallIp2.address = fh.form.cleaned_data['nasinstallip2']
                            ipAddrObjNasInstallIp2.ipv4UniqueIdentifier = ipv4Identifier
                            ipAddrObjNasInstallIp2.save(force_update=True)

                        if hardwareType != 'virtual' and hardwareType != 'cloud':
                            if fh.form.cleaned_data['nasInstalIlolIp1'] == "":
                                if IpAddress.objects.filter(nic=networkObject.id, ipType="nasInstalIlolIp1",
                                                            ipv4UniqueIdentifier=ipv4Identifier).exists():
                                    IpAddress.objects.filter(nic=networkObject.id, ipType="nasInstalIlolIp1",
                                                             ipv4UniqueIdentifier=ipv4Identifier).delete()
                            else:
                                if not IpAddress.objects.filter(nic=networkObject.id, ipType="nasInstalIlolIp1",
                                                                ipv4UniqueIdentifier=ipv4Identifier).exists():
                                    ipAddrObjNasIloInstallIp1 = IpAddress.objects.create(nic=networkObject,
                                                                                         ipType="nasInstalIlolIp1",
                                                                                         address=fh.form.cleaned_data[
                                                                                             'nasInstalIlolIp1'],
                                                                                         ipv4UniqueIdentifier=ipv4Identifier)
                            if fh.form.cleaned_data['nasInstalIlolIp2'] == "":
                                if IpAddress.objects.filter(nic=networkObject.id,ipType="nasInstalIlolIp2",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                    IpAddress.objects.filter(nic=networkObject.id,ipType="nasInstalIlolIp2",ipv4UniqueIdentifier=ipv4Identifier).delete()
                            else:
                                if not IpAddress.objects.filter(nic=networkObject.id,ipType="nasInstalIlolIp2",ipv4UniqueIdentifier=ipv4Identifier).exists():
                                    ipAddrObjNasIloInstallIp2 = IpAddress.objects.create(nic=networkObject,ipType="nasInstalIlolIp2",address = fh.form.cleaned_data['nasInstalIlolIp2'],ipv4UniqueIdentifier=ipv4Identifier)

                            credentialTypes = [credential.credentialType for credential in credentials]

                            if 'masterIlo' in credentialTypes:
                                masterIloCredentialsObj.username = fh.form.cleaned_data['masterIloUsername']
                                masterIloCredentialsObj.password = fh.form.cleaned_data['masterIloPassword']
                                masterIloCredentialsObj.save(force_update=True)
                            else:
                                try:
                                    masterIloCredentialsObj = Credentials.objects.create(
                                        username=fh.form.cleaned_data['masterIloUsername'],
                                        password=fh.form.cleaned_data['masterIloPassword'], credentialType='masterIlo')
                                    NASServer.objects.create(server=nodeServerObject, credentials=masterIloCredentialsObj)
                                except Exception as e:
                                    logger.info('Error creating new ilo credentials')

                            if 'supportIlo' in credentialTypes:
                                supportIloCredentialsObj.username = fh.form.cleaned_data['supportIloUsername']
                                supportIloCredentialsObj.password = fh.form.cleaned_data['supportIloPassword']
                                supportIloCredentialsObj.save(force_update=True)

                            else:
                                try:
                                    supportIloCredentialsObj = Credentials.objects.create(
                                        username=fh.form.cleaned_data['supportIloUsername'],
                                        password=fh.form.cleaned_data['supportIloPassword'], credentialType='supportIlo')
                                    NASServer.objects.create(server=nodeServerObject, credentials=supportIloCredentialsObj)
                                except Exception as e:
                                    logger.info('Error creating new ilo credentials')

                            if 'nasInstalIlolIp1' in credentialTypes:
                                nasInstallIloIp1CredentialsObj.username = fh.form.cleaned_data['nasInstallIloIp1Username']
                                nasInstallIloIp1CredentialsObj.password = fh.form.cleaned_data['nasInstalIlolIp1Password']
                                nasInstallIloIp1CredentialsObj.save(force_update=True)
                            else:
                                try:
                                    nasInstallIloIp1CredentialsObj = Credentials.objects.create(
                                        username=fh.form.cleaned_data['nasInstallIloIp1Username'],
                                        password=fh.form.cleaned_data['nasInstalIlolIp1Password'], credentialType='nasInstalIlolIp1')
                                    NASServer.objects.create(server=nodeServerObject, credentials=nasInstallIloIp1CredentialsObj)
                                except Exception as e:
                                    logger.info('Error creating new nasInstalIlolIp1 credentials')

                            if 'nasInstalIlolIp2' in credentialTypes:
                                nasInstallIloIp2CredentialsObj.username = fh.form.cleaned_data['nasInstallIloIp2Username']
                                nasInstallIloIp2CredentialsObj.password = fh.form.cleaned_data['nasInstalIlolIp2Password']
                                nasInstallIloIp2CredentialsObj.save(force_update=True)
                            else:
                                try:
                                    nasInstallIloIp2CredentialsObj = Credentials.objects.create(
                                        username=fh.form.cleaned_data['nasInstallIloIp2Username'],
                                        password=fh.form.cleaned_data['nasInstalIlolIp2Password'], credentialType='nasInstalIlolIp2')
                                    NASServer.objects.create(server=nodeServerObject, credentials=nasInstallIloIp2CredentialsObj)
                                except Exception as e:
                                    logger.info('Error creating new nasInstalIlolIp2 credentials')


                            if fh.form.cleaned_data['nasInstalIlolIp1'] != "":
                                ipAddrObjNasIloInstallIp1.address = fh.form.cleaned_data['nasInstalIlolIp1']
                                ipAddrObjNasIloInstallIp1.ipv4UniqueIdentifier=ipv4Identifier
                                ipAddrObjNasIloInstallIp1.save(force_update=True)
                            if fh.form.cleaned_data['nasInstalIlolIp2'] != "":
                                ipAddrObjNasIloInstallIp2.address = fh.form.cleaned_data['nasInstalIlolIp2']
                                ipAddrObjNasIloInstallIp2.ipv4UniqueIdentifier=ipv4Identifier
                                ipAddrObjNasIloInstallIp2.save(force_update=True)

                        if option == "edit":
                            message = "Edited Server Configuration, " + str(changedContent)
                        else:
                            message = "Added Server Configuration (Stage2)"
                        logAction(userId, nasServerObject, option, message)
                        return HttpResponseRedirect("/dmt/nassvrs/" + str(nodeServerObject.id))
                except IntegrityError  as e:
                    logger.warn("Problem updating NAS Server " +str(nodeServerObject.hostname)+ " in the database, Exception : " + str(e))
                    fh.message = "Problem updating NAS Server " +str(nodeServerObject.hostname)+ " in the database, Exception : " + str(e)
                    return fh.display()
            else:
                return fh.failure()
        else:
            return fh.display()

    elif "delete" in option:
        dictDeletedInfo = {}
        dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(nasServerObject).pk
        dictDeletedInfo["objectId"] = nasServerObject.pk
        dictDeletedInfo["objectRep"] = force_unicode(nasServerObject)
        # Delete the selected Management Server
        cnm = ClusterToNASMapping.objects.filter(nasServer__server=nodeServerObject)
        if cnm:
            cnmList = []
            for c in cnm:
                cnmList.append(str(c.cluster.name))
            error = "Cannot Delete, the Following Deployments require " + str(nodeServerObject) + ": " + str(cnmList)
            return render(request, "dmt/dmt_error.html", {'error': error})

        credentials = []
        try:
            networkObject = NetworkInterface.objects.get(server=nodeServerObject.id, interface="eth0",nicIdentifier=macIdentifier)
        except:
            logger.info("no NIC defined for " +str(nodeServerObject.hostname))
        for obj in serverObject:
            try:
                credentials += Credentials.objects.filter(id=obj.credentials_id)
            except:
                logger.info("no Credentials defined for " +str(nodeServerObject.hostname))
        try:
            NASServer.objects.filter(server=nodeServerObject).delete()
            Server.objects.filter(id=nasServerId).delete()
            try:
                NetworkInterface.objects.filter(server=nodeServerObject.id).delete()
            except:
                logger.info("no NIC defined for " +str(nodeServerObject.hostname))
            try:
                IpAddress.objects.filter(nic=networkObject.id).delete()
            except:
                logger.info("no IPs defined for " +str(nodeServerObject.hostname))
            try:
                for item in credentials:
                    if item.credentialType == 'master':
                        masterCredentialsObj = Credentials.objects.get(id=item.id).delete()
                    else:
                        supportCredentialsObj = Credentials.objects.get(id=item.id).delete()
            except:
                logger.info("no Credentials defined for " +str(nodeServerObject.hostname))
            message = "Deleted Server Configuration"
            logAction(userId, nasServerObject, option, message, dictDeletedInfo)
            cursor = connection.cursor()
        except Exception as e:
            raise CommandError("There was an issue deleting NAS server " +str(nodeServerObject.hostname)+ " from database: " +str(e))
        return HttpResponseRedirect("/dmt/nassvrs/")

@login_required
@transaction.atomic
def updateStorageServer(request, storageServer, option):
    '''
    The updateClarriionserver function is used to populate the edit MgtServer form
    '''
    userId = request.user.pk
    if "edit" in option:
        serverObject =  Storage.objects.get(id=storageServer)
        if StorageIPMapping.objects.filter(storage=serverObject.id,ipnumber="1").exists():
            ipIdOneObject = StorageIPMapping.objects.get(storage=serverObject.id,ipnumber="1")
        else:
            ipIdOneObject = None
        if StorageIPMapping.objects.filter(storage=serverObject.id,ipnumber="2").exists():
            ipIdTwoObject = StorageIPMapping.objects.get(storage=serverObject.id,ipnumber="2")
        else:
            ipIdTwoObject = None
        if ipIdOneObject != None:
            ipOneObject = IpAddress.objects.get(id=ipIdOneObject.ipaddr_id)
            ipOneObjectAddress = ipOneObject.address
        else:
            ipOneObject = None
            ipOneObjectAddress = None
        if ipIdTwoObject != None:
            ipTwoObject = IpAddress.objects.get(id=ipIdTwoObject.ipaddr_id)
            ipTwoObjectAddress = ipTwoObject.address
        else:
            ipTwoObject = None
            ipTwoObjectAddress = None
        credentialObject = Credentials.objects.get(id=serverObject.credentials_id)

        # Create a FormHandle to handle form post-processing
        fh = FormHandle()
        fh.form = UpdateStorageServerForm(
                initial={
                    'name': serverObject.name,
                    'vnxType': serverObject.vnxType,
                    'domain_name': serverObject.domain_name,
                    'serial_number': serverObject.serial_number,
                    'storage_ip1': ipOneObjectAddress,
                    'storage_ip2': ipTwoObjectAddress,
                    'username': credentialObject.username,
                    'password': credentialObject.password,
                    'login_scope': credentialObject.loginScope,
                    'sanAdminPassword': serverObject.sanAdminPassword,
                    'sanServicePassword': serverObject.sanServicePassword})
        fh.title = "Update Network Attached Storage Server Form for: " + str(serverObject.hostname)
        fh.request = request
        fh.button = "Save & Exit..."
        fh.button2 = "Cancel"
        fh.redirectTarget = "/dmt/storage/"

        if request.method == 'POST':
            if "Cancel" in request.POST:
                return fh.success()
            fh.form = UpdateStorageServerForm(request.POST)
            # validate the form so that the cleaned_data gets populated, then we can get the
            # requested name and define our redirect URL
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        oldValues = [str(serverObject.name) + "##Machine Name", str(serverObject.vnxType) + "##VNX Type",str(serverObject.domain_name) + "##Domain Name", str(serverObject.serial_number) + "##Serial Number", str(ipOneObjectAddress) + "##Storage IP Address (1)",str(ipTwoObjectAddress) + "##Storage IP Address (2)",str(credentialObject.username) + "##Username",str(credentialObject.password) + "##Password",str(credentialObject.loginScope) + "##Login Scope"]
                        oldValues += [str(serverObject.sanAdminPassword) + "##SAN Admin Password",str(serverObject.sanServicePassword) + "##SAN Service Password"]
                        newValues = [str(fh.form.cleaned_data['name']),str(fh.form.cleaned_data['vnxType']),str(fh.form.cleaned_data['domain_name']),str(fh.form.cleaned_data['serial_number']),str(fh.form.cleaned_data['storage_ip1']),str(fh.form.cleaned_data['storage_ip2']),str(fh.form.cleaned_data['username']),str(fh.form.cleaned_data['password']),str(fh.form.cleaned_data['login_scope'])]
                        newValues += [str(fh.form.cleaned_data['sanAdminPassword']),str(fh.form.cleaned_data['sanServicePassword'])]
                        addressList = filter(None, [str(fh.form.cleaned_data['storage_ip1']),str(fh.form.cleaned_data['storage_ip2'])])
                        duplicates = dmt.utils.getDuplicatesInList(addressList)
                        if len(duplicates) > 0:
                            fh.message = "Duplicate IP Address: " + str(duplicates[0]) + ", please try again"
                            return fh.display()
                        changedContent = logChange(oldValues,newValues)
                        # Need to delete the two ip to ensure we can change both at the same time
                        if StorageIPMapping.objects.filter(storage=serverObject.id,ipnumber="1").exists():
                            StorageIPMapping.objects.get(storage=serverObject.id,ipnumber="1").delete()
                        if StorageIPMapping.objects.filter(storage=serverObject.id,ipnumber="2").exists():
                            StorageIPMapping.objects.get(storage=serverObject.id,ipnumber="2").delete()
                        if ipOneObject != None:
                            IpAddress.objects.get(id=ipOneObject.id).delete()
                        if ipTwoObject != None:
                            IpAddress.objects.get(id=ipTwoObject.id).delete()
                        #Check if IP's are unique if not tell user so
                        storageIp1 = fh.form.cleaned_data['storage_ip1']
                        storageIp2 = fh.form.cleaned_data['storage_ip2']
                        ipList = [storageIp1,storageIp2]
                        try:
                            for ip in ipList:
                                ipAddressObj = IpAddress.objects.filter(address=ip,ipv4UniqueIdentifier="1")
                                if ipAddressObj:
                                    fh.message = ("IPaddress: " + str(ip) + " is already registered, please try again")
                                    return fh.display()
                        except Exception as e:
                            message = "Issue saving IP details to db: " + str(e)
                            logger.error(message)
                            fh.message = message
                            return fh.display()
                        if storageIp1 == storageIp2:
                            message = "Issue saving IP details to db, ip's are the same"
                            logger.error(message)
                            fh.message = message
                            return fh.display()

                        ipOneObject = IpAddress.objects.create(address=storageIp1,ipType="san")
                        ipTwoObject = IpAddress.objects.create(address=storageIp2,ipType="san")
                        serverObject.name = fh.form.cleaned_data['name']
                        serverObject.vnxType = fh.form.cleaned_data['vnxType']
                        serverObject.domain_name = fh.form.cleaned_data['domain_name']
                        serverObject.serial_number = fh.form.cleaned_data['serial_number']
                        credentialObject.username = fh.form.cleaned_data['username']
                        credentialObject.password = fh.form.cleaned_data['password']
                        credentialObject.loginScope = fh.form.cleaned_data['login_scope']

                        serverObject.sanAdminPassword = fh.form.cleaned_data['sanAdminPassword']
                        serverObject.sanServicePassword = fh.form.cleaned_data['sanServicePassword']

                        map1 = StorageIPMapping.objects.create(storage=serverObject, ipaddr=ipOneObject, ipnumber=1)
                        map2 = StorageIPMapping.objects.create(storage=serverObject, ipaddr=ipTwoObject, ipnumber=2)
                        serverObject.save(force_update=True)
                        credentialObject.save(force_update=True)
                        message = "Edited Network Attached Storage Information, " + str(changedContent)
                        logAction(userId, serverObject, option, message)
                        return fh.success()
                except IntegrityError as e:
                    message = "Problem updating Storage Server " +str(serverObject.hostname)+ " in the database, Exception : " + str(e)
                    logger.error(message)
                    fh.message = message
                    return fh.failure()
            else:
                return fh.failure()
        else:
            return fh.display()

    elif "delete" in option:
        # Delete the selected Management Server
        serverObject =  Storage.objects.get(id=storageServer)
        dictDeletedInfo = {}
        dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(serverObject).pk
        dictDeletedInfo["objectId"] = serverObject.pk
        dictDeletedInfo["objectRep"] = force_unicode(serverObject)
        cdm = ClusterToDASMapping.objects.filter(storage=serverObject)
        if cdm:
            cdmList = []
            for c in cdm:
                cdmList.append(str(c.cluster.name))
            error = "Can not Delete, the Following Deployments require " + str(serverObject.hostname) + ": " + str(cdmList)
            return render(request, "dmt/dmt_error.html", {'error': error})
        csm = ClusterToStorageMapping.objects.filter(storage=serverObject)
        if csm:
            csmList = []
            for c in csm:
                csmList.append(str(c.cluster.name))
                error = "Can not Delete, the Following Deployments require " + str(serverObject.hostname) + ": " + str(csmList)
                return render(request, "dmt/dmt_error.html", {'error': error})
        ipIdOneObject = StorageIPMapping.objects.get(storage=serverObject.id,ipnumber="1")
        ipIdTwoObject = StorageIPMapping.objects.get(storage=serverObject.id,ipnumber="2")
        try:
            StorageIPMapping.objects.filter(storage=serverObject.id,ipnumber="1").delete()
            StorageIPMapping.objects.get(storage=serverObject.id,ipnumber="2").delete()
            IpAddress.objects.get(id=ipIdOneObject.ipaddr_id).delete()
            IpAddress.objects.get(id=ipIdTwoObject.ipaddr_id).delete()
            Credentials.objects.filter(id=serverObject.credentials_id).delete()
            message = "Deleted Network Attached Storage Information"
            logAction(userId, serverObject, option, message, dictDeletedInfo)
            cursor = connection.cursor()
        except Exception as e:
            raise CommandError("There was an issue deleting Storage server " +str(serverObject.hostname)+ " from database: " +str(e))
        return HttpResponseRedirect("/dmt/storage/")

@login_required
@transaction.atomic
def updateEnclosureServer(request, enclosureServer, option):
    '''
    Used to populate the edit Enclosure form
    '''
    userId = request.user.pk
    if "edit" in option:
        ipIdThreeObject = None
        ipThree = None
        ipIdFourObject = None
        ipFour = None
        ipIdFiveObject = None
        ipFive = None
        ipIdSixObject = None
        ipSix = None
        serverObject =  Enclosure.objects.get(id=enclosureServer)
        ipIdOneObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="1")
        ipIdTwoObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="2")
        ipOneObject = IpAddress.objects.get(id=ipIdOneObject.ipaddr_id)
        ipTwoObject = IpAddress.objects.get(id=ipIdTwoObject.ipaddr_id)
        credentialObject = Credentials.objects.get(id=serverObject.credentials_id)

        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="3").exists():
            ipIdThreeObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="3")
            if IpAddress.objects.filter(id=ipIdThreeObject.ipaddr_id).exists():
                ipThreeObject = IpAddress.objects.get(id=ipIdThreeObject.ipaddr_id)
                ipThree = ipThreeObject.address
            else:
                ipThreeObject = None
                ipThree = None
        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="4").exists():
            ipIdFourObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="4")
            if IpAddress.objects.filter(id=ipIdFourObject.ipaddr_id).exists():
                ipFourObject = IpAddress.objects.get(id=ipIdFourObject.ipaddr_id)
                ipFour = ipFourObject.address
            else:
                ipFourObject = None
                ipFour = None
        if Credentials.objects.filter(id=serverObject.vc_credentials_id).exists():
            vcCredentialObject = Credentials.objects.get(id=serverObject.vc_credentials_id)
            vcCredentialUsername = vcCredentialObject.username
            vcCredentialPassword = vcCredentialObject.password
        else:
            vcCredentialObject = None
            vcCredentialUsername = None
            vcCredentialPassword = None
        # SAN Switch
        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="5").exists():
            ipIdFiveObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="5")
            if IpAddress.objects.filter(id=ipIdFiveObject.ipaddr_id).exists():
                ipFiveObject = IpAddress.objects.get(id=ipIdFiveObject.ipaddr_id)
                ipFive = ipFiveObject.address
            else:
                ipFiveObject = None
                ipFive = None
        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="6").exists():
            ipIdSixObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="6")
            if IpAddress.objects.filter(id=ipIdSixObject.ipaddr_id).exists():
                ipSixObject = IpAddress.objects.get(id=ipIdSixObject.ipaddr_id)
                ipSix = ipSixObject.address
            else:
                ipSixObject = None
                ipSix = None
        if Credentials.objects.filter(id=serverObject.sanSw_credentials_id).exists():
            sanSwCredentialObject = Credentials.objects.get(id=serverObject.sanSw_credentials_id)
            sanSwCredentialUsername = sanSwCredentialObject.username
            sanSwCredentialPassword = sanSwCredentialObject.password
        else:
            sanSwCredentialObject = None
            sanSwCredentialUsername = None
            sanSwCredentialPassword = None

        # Create a FormHandle to handle form post-processing
        fh = FormHandle()
        fh.form = UpdateEnclosureServerForm(
                initial={
                    'domain_name': serverObject.domain_name,
                    'vc_domain_name': serverObject.vc_domain_name,
                    'rackName': serverObject.rackName,
                    'name': serverObject.name,
                    'enclosure_ip1': ipOneObject.address,
                    'enclosure_ip2': ipTwoObject.address,
                    'username': credentialObject.username,
                    'password': credentialObject.password,
                    'vc_enclosure_ip1': ipThree,
                    'vc_enclosure_ip2': ipFour,
                    'vc_module_bay_1': serverObject.vc_module_bay_1,
                    'vc_module_bay_2': serverObject.vc_module_bay_2,
                    'vc_username': vcCredentialUsername,
                    'vc_password': vcCredentialPassword,
                    'sanSw_enclosure_ip1': ipFive,
                    'sanSw_enclosure_ip2': ipSix,
                    'san_sw_bay_1': serverObject.san_sw_bay_1,
                    'san_sw_bay_2': serverObject.san_sw_bay_2,
                    'sanSw_username': sanSwCredentialUsername,
                    'sanSw_password': sanSwCredentialPassword,
                    'uplink_A_port1' : serverObject.uplink_A_port1,
                    'uplink_A_port2' : serverObject.uplink_A_port2,
                    'uplink_B_port1' : serverObject.uplink_B_port1,
                    'uplink_B_port2' : serverObject.uplink_B_port2 })
        fh.title = "Update On-Board Admin and Virtual Connect info for Blade Enclosure: " + str(serverObject.hostname)
        fh.request = request
        fh.button = "Save & Exit..."
        fh.button2 = "Cancel"
        # redirect to Management Servers page
        fh.redirectTarget = "/dmt/enclosure/"

        if request.method == 'POST':
            fh.form = UpdateEnclosureServerForm(request.POST)
            if "Cancel" in request.POST:
                return fh.success()
            # validate the form so that the cleaned_data gets populated, then we can get the
            # requested name and define our redirect URL
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        oldValues = [str(serverObject.domain_name) + "##Domain Name",str(serverObject.vc_domain_name) + "##Virtual Connect Domain Name",str(serverObject.rackName) + "##Rack Name",str(serverObject.name) + "##Enclosure Name",str(ipOneObject.address) + "##On Board Admin IP 1",str(ipTwoObject.address) + "##On Board Admin IP 2",str(credentialObject.username) + "##On Board Admin Login Username",str(credentialObject.password) + "##On Board Admin Login Password",str(ipThree) + "##Virtual Connect IP 1",str(ipFour) + "##Virtual Connect IP 2",str(serverObject.vc_module_bay_1) + "##VC 1 interconnect bay location",str(serverObject.vc_module_bay_2) + "##VC 2 interconnect bay location",str(vcCredentialUsername) + "##Virtual Connect Login Username",str(vcCredentialPassword) + "##Virtual Connect Login Password",str(ipFive) + "##SAN Switch IP 1",str(ipSix) + "##SAN Switch IP 2",str(serverObject.san_sw_bay_1) + "##SAN switch 1 interconnect bay location",str(serverObject.san_sw_bay_2) + "##SAN switch 2 interconnect bay location",str(sanSwCredentialUsername) + "##SAN Switch Login Username",str(sanSwCredentialPassword) + "##SAN Switch Login Password",str(serverObject.uplink_A_port1) + "##Uplink A Port 1",str(serverObject.uplink_A_port2) + "##Uplink A Port 2",str(serverObject.uplink_B_port1) + "##Uplink B Port 1",str(serverObject.uplink_B_port2) + "##Uplink B Port 2"]
                        newValues = [str(fh.form.cleaned_data['domain_name']),str(fh.form.cleaned_data['vc_domain_name']),str(fh.form.cleaned_data['rackName']),str(fh.form.cleaned_data['name']),str(fh.form.cleaned_data['enclosure_ip1']),str(fh.form.cleaned_data['enclosure_ip2']),str(fh.form.cleaned_data['username']),str(fh.form.cleaned_data['password']),str(fh.form.cleaned_data['vc_enclosure_ip1']),str(fh.form.cleaned_data['vc_enclosure_ip2']),str(fh.form.cleaned_data['vc_module_bay_1']),str(fh.form.cleaned_data['vc_module_bay_2']),str(fh.form.cleaned_data['vc_username']),str(fh.form.cleaned_data['vc_password']),str(fh.form.cleaned_data['sanSw_enclosure_ip1']),str(fh.form.cleaned_data['sanSw_enclosure_ip2']),str(fh.form.cleaned_data['san_sw_bay_1']),str(fh.form.cleaned_data['san_sw_bay_2']),str(fh.form.cleaned_data['sanSw_username']),str(fh.form.cleaned_data['sanSw_password']),str(fh.form.cleaned_data['uplink_A_port1']),str(fh.form.cleaned_data['uplink_A_port2']),str(fh.form.cleaned_data['uplink_B_port1']),str(fh.form.cleaned_data['uplink_B_port2'])]

                        addressList = filter(None, [str(fh.form.cleaned_data['enclosure_ip1']),str(fh.form.cleaned_data['enclosure_ip2']),str(fh.form.cleaned_data['vc_enclosure_ip1']),str(fh.form.cleaned_data['vc_enclosure_ip2']),str(fh.form.cleaned_data['sanSw_enclosure_ip1']),str(fh.form.cleaned_data['sanSw_enclosure_ip2'])])
                        duplicates = dmt.utils.getDuplicatesInList(addressList)
                        if len(duplicates) > 0:
                            raise Exception("Duplicate IP Info "+str(duplicates))
                        changedContent = logChange(oldValues,newValues)
                        # Update the Management Server Model
                        serverObject.domain_name = fh.form.cleaned_data['domain_name']
                        serverObject.vc_domain_name = fh.form.cleaned_data['vc_domain_name']
                        serverObject.rackName = fh.form.cleaned_data['rackName']
                        serverObject.name = fh.form.cleaned_data['name']
                        ipOneObject.address = fh.form.cleaned_data['enclosure_ip1']
                        ipOneObject.ipType = "enclosure"
                        ipTwoObject.address = fh.form.cleaned_data['enclosure_ip2']
                        ipTwoObject.ipType = "enclosure"
                        credentialObject.username = fh.form.cleaned_data['username']
                        credentialObject.password = fh.form.cleaned_data['password']
                        ipOneObject.save(force_update=True)
                        ipTwoObject.save(force_update=True)
                        credentialObject.save(force_update=True)
                        serverObject.san_sw_bay_1 = fh.form.cleaned_data['san_sw_bay_1']
                        serverObject.san_sw_bay_2 = fh.form.cleaned_data['san_sw_bay_2']
                        serverObject.vc_module_bay_1 = fh.form.cleaned_data['vc_module_bay_1']
                        serverObject.vc_module_bay_2 = fh.form.cleaned_data['vc_module_bay_2']

                        serverObject.uplink_A_port1 = fh.form.cleaned_data['uplink_A_port1']
                        serverObject.uplink_A_port2 = fh.form.cleaned_data['uplink_A_port2']
                        serverObject.uplink_B_port1 = fh.form.cleaned_data['uplink_B_port1']
                        serverObject.uplink_B_port2 = fh.form.cleaned_data['uplink_B_port2']

                        if ipIdThreeObject != None:
                            ipThreeObject.address = fh.form.cleaned_data['vc_enclosure_ip1']
                            ipThreeObject.ipType = "vc_enclosure"
                        else:
                            ipThreeObject = IpAddress.objects.create(address=fh.form.cleaned_data['vc_enclosure_ip1'],ipType="vc_enclosure")
                            map3 = EnclosureIPMapping.objects.create(enclosure=serverObject, ipaddr=ipThreeObject, ipnumber=3)
                        if ipIdFourObject != None:
                            ipFourObject.address = fh.form.cleaned_data['vc_enclosure_ip2']
                            ipFourObject.ipType = "vc_enclosure"
                        else:
                            ipFourObject = IpAddress.objects.create(address=fh.form.cleaned_data['vc_enclosure_ip2'],ipType="vc_enclosure")
                            map4 = EnclosureIPMapping.objects.create(enclosure=serverObject, ipaddr=ipFourObject, ipnumber=4)
                        if vcCredentialObject != None:
                            vcCredentialObject.username = fh.form.cleaned_data['vc_username']
                            vcCredentialObject.password = fh.form.cleaned_data['vc_password']
                        else:
                            vcCredentialObject = Credentials.objects.create(username=fh.form.cleaned_data['vc_username'], password=fh.form.cleaned_data['vc_password'])
                            serverObject.vc_credentials = vcCredentialObject
                        # SAN SW
                        if ipIdFiveObject != None:
                            ipFiveObject.address = fh.form.cleaned_data['sanSw_enclosure_ip1']
                            ipFiveObject.ipType = "sanSw_enclosure"
                        else:
                            ipFiveObject = IpAddress.objects.create(address=fh.form.cleaned_data['sanSw_enclosure_ip1'],ipType="sanSw_enclosure")
                            map5 = EnclosureIPMapping.objects.create(enclosure=serverObject, ipaddr=ipFiveObject, ipnumber=5)
                        if ipIdSixObject != None:
                            ipSixObject.address = fh.form.cleaned_data['sanSw_enclosure_ip2']
                            ipSixObject.ipType = "sanSw_enclosure"
                        else:
                            ipSixObject = IpAddress.objects.create(address=fh.form.cleaned_data['sanSw_enclosure_ip2'],ipType="sanSw_enclosure")
                            map6 = EnclosureIPMapping.objects.create(enclosure=serverObject, ipaddr=ipSixObject, ipnumber=6)
                        if sanSwCredentialObject != None:
                            sanSwCredentialObject.username = fh.form.cleaned_data['sanSw_username']
                            sanSwCredentialObject.password = fh.form.cleaned_data['sanSw_password']
                        else:
                            sanSwCredentialObject = Credentials.objects.create(username=fh.form.cleaned_data['sanSw_username'], password=fh.form.cleaned_data['sanSw_password'])
                            serverObject.sanSw_credentials = sanSwCredentialObject
                        ipThreeObject.save(force_update=True)
                        ipFourObject.save(force_update=True)
                        vcCredentialObject.save(force_update=True)
                        ipFiveObject.save(force_update=True)
                        ipSixObject.save(force_update=True)
                        sanSwCredentialObject.save(force_update=True)
                        serverObject.save(force_update=True)
                        message = "Edited Enclosure Information, " + str(changedContent)
                        logAction(userId, serverObject, option, message)
                        return fh.success()
                except IntegrityError as e:
                    logger.warn("Problem updating Enclosure " +str(serverObject.hostname)+ " in the database, Exception : " + str(e))
                    return fh.failure()
            else:
                return fh.failure()
        else:
            return fh.display()

    elif "delete" in option:
        ipIdThreeObject = None
        ipIdFourObject = None
        ipIdFiveObject = None
        ipIdSixObject = None
        # Delete the selected Enclosure
        serverObject =  Enclosure.objects.get(id=enclosureServer)
        bhd = BladeHardwareDetails.objects.filter(enclosure=serverObject)
        if bhd:
            bhdList = []
            for b in bhd:
               bhdList.append(str(b.profile_name))
            error = "Can not Delete the Following BladeHardwareDetails require " + str(serverObject.hostname) + ": " + str(bhdList)
            return render(request, "dmt/dmt_error.html", {'error': error})
        ipIdOneObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="1")
        ipIdTwoObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="2")
        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="3").exists():
            ipIdThreeObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="3")
        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="4").exists():
            ipIdFourObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="4")
        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="5").exists():
            ipIdFiveObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="5")
        if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="6").exists():
            ipIdSixObject = EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="6")
        try:
            EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="1").delete()
            EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="2").delete()
            IpAddress.objects.get(id=ipIdOneObject.ipaddr_id).delete()
            IpAddress.objects.get(id=ipIdTwoObject.ipaddr_id).delete()
            if ipIdThreeObject != None:
                if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="3").exists():
                    EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="3").delete()
                    if IpAddress.objects.filter(id=ipIdThreeObject.ipaddr_id).exists():
                        IpAddress.objects.get(id=ipIdThreeObject.ipaddr_id).delete()
            if ipIdFourObject != None:
                if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="4").exists():
                    EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="4").delete()
                    if IpAddress.objects.filter(id=ipIdFourObject.ipaddr_id).exists():
                        IpAddress.objects.get(id=ipIdFourObject.ipaddr_id).delete()
            if ipIdFiveObject != None:
                if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="5").exists():
                    EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="5").delete()
                    if IpAddress.objects.filter(id=ipIdFiveObject.ipaddr_id).exists():
                        IpAddress.objects.get(id=ipIdFiveObject.ipaddr_id).delete()
            if ipIdSixObject != None:
                if EnclosureIPMapping.objects.filter(enclosure=serverObject.id,ipnumber="6").exists():
                    EnclosureIPMapping.objects.get(enclosure=serverObject.id,ipnumber="6").delete()
                    if IpAddress.objects.filter(id=ipIdSixObject.ipaddr_id).exists():
                        IpAddress.objects.get(id=ipIdSixObject.ipaddr_id).delete()
            Enclosure.objects.filter(id=enclosureServer).delete()
            Credentials.objects.filter(id=serverObject.credentials_id).delete()
            if Credentials.objects.filter(id=serverObject.vc_credentials_id).exists():
                Credentials.objects.filter(id=serverObject.vc_credentials_id).delete()
            if Credentials.objects.filter(id=serverObject.sanSw_credentials_id).exists():
                Credentials.objects.filter(id=serverObject.sanSw_credentials_id).delete()
            message = "Deleted Enclosure Information"
            logAction(userId, serverObject, option, message)
            cursor = connection.cursor()
        except Exception as e:
            raise CommandError("There was an issue deleting Enclosure " +str(serverObject.hostname)+ " from database: " +str(e))
        return HttpResponseRedirect("/dmt/enclosure/")

@login_required
def updateDHCPLifetime(request, cluster_id):
    '''
    The updateDHCPLifetime function updates the deployment dhcp_lifetime by 24 hours
    '''
    cluster = Cluster.objects.get(id=cluster_id)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to updateDHCPLifetime for " + str(cluster.name)
            return render(request, "dmt/dmt_error.html", {'error': error})
    timePlus24Hours = datetime.now()+timedelta(days=1)
    cluster.dhcp_lifetime = timePlus24Hours
    cluster.save()
    try:
        dmt.utils.updateDHCPServer()
    except Exception as e:
        logger.error("This was an issue calling the DHCP Server function: " +str(e))
        return HttpResponseRedirect("/dmt/clusters/" + str(cluster_id))

@login_required
@transaction.atomic
def updateCluster(request, cluster_id, option):
    '''
       The updateCluster function is used to populate the edit Cluster form for editing and delete the Deployment
    '''
    clusterObject = Cluster.objects.get(id=cluster_id)
    if clusterObject.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObject, option):
            error = "You do not have permission to "+ option + " "+str(clusterObject.name)
            return render(request, "dmt/dmt_error.html", {'error': error})
    includeCompactAuditLogger = dmt.utils.checkIncludeCompactAuditLogger(cluster_id)

    userId = request.user.pk
    if "edit" in option:
        action = "edit"
        name = description = clusterObject.name
        description = clusterObject.description
        tipc_address = clusterObject.tipc_address
        managementServer = clusterObject.management_server
        if includeCompactAuditLogger:
            compact_audit_logger = clusterObject.compact_audit_logger
        layout = clusterObject.layout
        component = clusterObject.component
        enmDeploymentType = clusterObject.enmDeploymentType
        ipVersion = clusterObject.ipVersion
        layouts = []
        if clusterObject.management_server.product.name == "OSS-RC":
            layouts = []
        else:
            layouts = ClusterLayout.objects.all().exclude(id=3)
        fh = FormHandle()
        fh.form = UpdateClusterFormExtraLargeENM(layouts) if includeCompactAuditLogger else UpdateClusterForm(layouts)
        fh.form.initial = {'name': name, 'description': description, 'tipc_address': tipc_address, 'layout': layout, 'management_server': managementServer, 'component': component, 'enmDeploymentType': enmDeploymentType, 'ipVersion': ipVersion}
        if includeCompactAuditLogger:
            fh.form.initial['compact_audit_logger'] = compact_audit_logger
        fh.title = "Update Deployment for: " + str(clusterObject.name)
        fh.request = request
        fh.button = "Save & Exit..."
        fh.button2 = "Cancel"
        fh.redirectTarget = "/dmt/clusters/" + str(cluster_id)
        if request.method == 'POST':
            if "Cancel" in request.POST:
                return fh.success()
            fh.form = UpdateClusterFormExtraLargeENM(layouts, request.POST, instance=clusterObject) if includeCompactAuditLogger else UpdateClusterForm(layouts, request.POST, instance=clusterObject)
            if fh.form.is_valid():
                try:
                    with transaction.atomic():
                        oldValues = [str(name) + "##Name",
                                str(description) + "##Description",
                                str(tipc_address) + "##TIPC",
                                str(layout) + "##Layout",
                                str(managementServer) + "##Management Server",
                                str(component) + "##Component",
                                str(enmDeploymentType) + "##ENM Deployment Type",
                                str(ipVersion) + "##IP Version"]
                        if includeCompactAuditLogger:
                            oldValues.append(str(compact_audit_logger) + "##Management Server")
                            newValues = [str(fh.form.cleaned_data['name']),str(fh.form.cleaned_data['description']),str(fh.form.cleaned_data['tipc_address']),str(fh.form.cleaned_data['layout']),str(fh.form.cleaned_data['management_server']),str(fh.form.cleaned_data['compact_audit_logger']),str(fh.form.cleaned_data['component']), str(fh.form.cleaned_data['enmDeploymentType']), str(fh.form.cleaned_data['ipVersion'])]
                        else:
                            newValues = [str(fh.form.cleaned_data['name']),str(fh.form.cleaned_data['description']),str(fh.form.cleaned_data['tipc_address']),str(fh.form.cleaned_data['layout']),str(fh.form.cleaned_data['management_server']),str(fh.form.cleaned_data['component']), str(fh.form.cleaned_data['enmDeploymentType']), str(fh.form.cleaned_data['ipVersion'])]
                        changedContent = logChange(oldValues,newValues)
                        clusterObject.name = fh.form.cleaned_data['name']
                        clusterObject.description = fh.form.cleaned_data['description']
                        clusterObject.tipc_address = fh.form.cleaned_data['tipc_address']
                        component = fh.form.cleaned_data['component']
                        if clusterObject.management_server.product.name != "OSS-RC":
                            layout = ClusterLayout.objects.get(name=fh.form.cleaned_data['layout'])
                            if layout == ClusterLayout.objects.get(id=2):
                                if VirtualImage.objects.filter(cluster=clusterObject).exists():
                                    fh.message = "To Use CMW Layout you Must delete all Virtual Machines (KVM Images)"
                                    logger.error(fh.message)
                                    return fh.display()
                            elif layout == ClusterLayout.objects.get(id=1):
                                if ServiceGroup.objects.filter(service_cluster__cluster=clusterObject):
                                    fh.message = "To Use KVM Layout you must delete all CMW Service Groups/Units"
                                    logger.error(fh.message)
                                    return fh.display()
                            clusterObject.layout = layout
                        mgtServerName = fh.form.cleaned_data['management_server']
                        mgtServerId = str(mgtServerName).split("(id: ")
                        mgtServerId = mgtServerId[1]
                        mgtServerId = mgtServerId.replace(')','')
                        if ManagementServer.objects.filter(id=mgtServerId).exists():
                            mgtServerObj = ManagementServer.objects.get(id=mgtServerId)
                            ipCheck = dmt.utils.ipCheckClusterAndMgtServer(mgtServerObj, clusterObject)
                            if "Warning" in ipCheck:
                                fh.message = ipCheck
                                logger.error(fh.message)
                                return fh.display()
                            if mgtServerObj.product.name == "OSS-RC":
                                layout = ClusterLayout.objects.get(name=layout)
                                if layout.id != 3:
                                    fh.message = "Please choose a different Management server, this is an OSS-RC Management Server"
                                    logger.error(fh.message)
                                    return fh.display()
                            clusterObject.management_server = mgtServerObj
                        else:
                            fh.message = "There was an issue getting the info for the choosen Management Server, please try again..."
                            logger.error(fh.message)
                            return fh.display()
                        clusterObject.component = component
                        clusterObject.enmDeploymentType = fh.form.cleaned_data['enmDeploymentType']
                        if includeCompactAuditLogger:
                            clusterObject.compact_audit_logger = dmt.utils.convertStrToBool(fh.form.cleaned_data['compact_audit_logger'])
                        isRackDeployment = dmt.utils.isEnmRackDeployment(clusterObject.enmDeploymentType)
                        if not isRackDeployment:
                            dmt.utils.resetFcSwitches(cluster_id)
                        clusterObject.ipVersion = fh.form.cleaned_data['ipVersion']
                        clusterObject.save(force_update=True)
                        message = "Edited Deployment Configuration, " + str(changedContent)
                        logAction(userId, clusterObject, action, message)
                        return fh.success()
                except IntegrityError:
                    return fh.failure()
            else:
                return fh.failure()
        else:
            return fh.display()

    elif "delete" in option:
        action = "delete"
        if not config.get("DMT", "ciAdmin") in request.user.groups.values_list('name',flat=True):
            error = "You do not have permission to "+ action + " "+str(clusterObject.name)
            return render(request, "dmt/dmt_error.html", {'error': error})

        #Delete the selected deployment
        cluster = Cluster.objects.get(id=cluster_id)
        servers = ClusterServer.objects.filter(cluster=cluster)
        message = "Deleted Deployment"
        dictDeletedInfo = {}
        dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(cluster).pk
        dictDeletedInfo["objectId"] = cluster.pk
        dictDeletedInfo["objectRep"] = force_unicode(cluster)
        if VlanClusterMulticast.objects.filter(cluster=cluster).exists():
            try:
                VlanClusterMulticast.objects.filter(cluster=cluster).delete()
            except Exception as e:
                raise CommandError("Issue deleting the Vlan Cluster Multicast details for deployment " + str(cluster.name) + "from database: " + str(e))
        if not servers:
            try:
                DeploymentDatabaseProvider.objects.filter(id=cluster_id).delete()
                DeploymentStatus.objects.filter(id=cluster_id).delete()
                Cluster.objects.filter(id=cluster_id).delete()
                cursor = connection.cursor()
            except Exception as e:
                raise CommandError("There was an issue deleting deployment " +str(cluster.name)+ " from database: " +str(e))
            logAction(userId, cluster, action, message, dictDeletedInfo)
            return HttpResponseRedirect("/dmt/clusters/")
        else:
            logger.error("There was an issue deleting " +str(cluster.name)+ " from database : it has server(s)" )
            error = "There was an issue deleting " + str(cluster.name) + ", it has server(s): All Servers  must be deleted before Deployment can be deleted."
            return render(request, "dmt/dmt_error.html", {'error': error})

@login_required
@transaction.atomic
def updateMulticast(request, cluster_id, servicecluster):
     '''
     The updateMulticast function is used to populate the edit Multicast form for editing
     '''
     try:
        multicastObject = Multicast.objects.get(service_cluster_id=servicecluster)
        defaultAddressIpObj = IpAddress.objects.get(id=multicastObject.ipMapDefaultAddress_id)
        messagingAddressIpObj = IpAddress.objects.get(id=multicastObject.ipMapMessagingGroupAddress_id)
        udpAddressIpObj = IpAddress.objects.get(id=multicastObject.ipMapUdpMcastAddress_id)
        mpingAddressIpObj = IpAddress.objects.get(id=multicastObject.ipMapMpingMcastAddress_id)
     except:
         return HttpResponseRedirect("/dmt/addcluster/"+str(servicecluster)+"/mcasts")

     clusterObject = Cluster.objects.get(id=cluster_id)
     if clusterObject.group != None:
         if not dmt.utils.permissionRequest(request.user, clusterObject):
             error = "You do not have permission to edit Multicasts for " + str(clusterObject.name)
             return render(request, "dmt/dmt_error.html", {'error': error})

     fh = FormHandle()
     fh.form = MulticastForm(
             initial={
                 'default_address': multicastObject.ipMapDefaultAddress.address,
                 'messaging_group_address': multicastObject.ipMapMessagingGroupAddress.address,
                 'udp_mcast_address': multicastObject.ipMapUdpMcastAddress.address,
                 'default_mcast_port': multicastObject.default_mcast_port,
                 'udp_mcast_port': multicastObject.udp_mcast_port,
                 'mping_mcast_address': multicastObject.ipMapMpingMcastAddress.address,
                 'mping_mcast_port': multicastObject.mping_mcast_port,
                 'messaging_group_port' : multicastObject.messaging_group_port,
                 'public_port_base' : multicastObject.public_port_base
                 }
             )
     fh.title = "Update Multicast Form for: " + str(clusterObject.name)
     fh.request = request
     fh.redirectTarget= "/dmt/clusters/" + str(cluster_id)+ "/details/"
     fh.button = "Save & Exit..."
     fh.button2 = "Cancel"
     if request.method == 'POST':
         if "Cancel" in request.POST:
             return fh.success()
         fh.form = MulticastForm(request.POST, instance=multicastObject)
         if fh.form.is_valid():
             #redirect to the Deployment page with mcast list showing
             try:
                 with transaction.atomic():
                     #Update the Multicast Model
                     defaultAddressIpObj.address = fh.form.cleaned_data['default_address']
                     messagingAddressIpObj.address = fh.form.cleaned_data['messaging_group_address']
                     udpAddressIpObj.address = fh.form.cleaned_data['udp_mcast_address']
                     mpingAddressIpObj.address = fh.form.cleaned_data['mping_mcast_address']
                     multicastObject.default_mcast_port = fh.form.cleaned_data['default_mcast_port']
                     multicastObject.udp_mcast_port = fh.form.cleaned_data['udp_mcast_port']
                     multicastObject.mping_mcast_port = fh.form.cleaned_data['mping_mcast_port']
                     multicastObject.messaging_group_port = fh.form.cleaned_data['messaging_group_port']
                     multicastObject.public_port_base = fh.form.cleaned_data['public_port_base']
                     defaultAddressIpObj.save(force_update=True)
                     messagingAddressIpObj.save(force_update=True)
                     udpAddressIpObj.save(force_update=True)
                     mpingAddressIpObj.save(force_update=True)
                     multicastObject.save(force_update=True)
                     return fh.success()
             except IntegrityError as e:
                 fh.message = "Issue updating the multicast information, Exception : " + str(e)
                 logger.error(fh.message)
             return fh.display()
         else:
              fh.message = "Issue validating the multicast information"
              logger.error(fh.message)
              return fh.display()
     else:
        return fh.display()

@login_required
@transaction.atomic
def updateVeriatasClusterDetails(request,cluster_id):
    '''
    The updateVeriatasClusterDetails def is used to populate an edit form and allow user to edit Vertias Cluster.
    '''
    veritasCluster = VeritasCluster.objects.get(cluster=cluster_id)
    gcoIpObj = IpAddress.objects.get(id=veritasCluster.ipMapGCO_id)
    csgIpObj = IpAddress.objects.get(id=veritasCluster.ipMapCSG_id)
    cluster = Cluster.objects.get(id=cluster_id)
    if cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, cluster):
            error = "You do not have permission to Update  Veritas Cluster for Deployment: " +str(cluster.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})

    fh = FormHandle()
    fh.form = VeritasClusterForm(
            initial={
                'csgIp': veritasCluster.ipMapCSG.address,
                'gcoIp': veritasCluster.ipMapGCO.address,
                'csgBitmask': veritasCluster.ipMapCSG.bitmask,
                'gcoBitmask': veritasCluster.ipMapGCO.bitmask,
                'csgNic': veritasCluster.csgNic,
                'gcoNic': veritasCluster.gcoNic,
                'lltLink1': veritasCluster.lltLink1,
                'lltLink2': veritasCluster.lltLink2,
                'lltLinkLowPri1': veritasCluster.lltLinkLowPri1,
                }
            )
    fh.title = "Update Veritas Cluster for deployment: " +str(cluster_id)
    fh.request = request
    fh.button = "Save & Exit..."
    fh.button2 = "Cancel"
    fh.redirectTarget= "/dmt/clusters/" + str(cluster_id)+ "/details/"
    if request.method == 'POST':
        fh.form = VeritasClusterForm(request.POST, instance=veritasCluster)
        if "Cancel" in request.POST:
            return fh.success()
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    csgIpObj.address = fh.form.cleaned_data['csgIp']
                    csgIpObj.bitmask = fh.form.cleaned_data['csgBitmask']
                    gcoIpObj.address = fh.form.cleaned_data['gcoIp']
                    gcoIpObj.bitmask = fh.form.cleaned_data['gcoBitmask']
                    veritasCluster.csgNic = fh.form.cleaned_data['csgNic']
                    veritasCluster.gcoNic = fh.form.cleaned_data['gcoNic']
                    veritasCluster.lltLink1 = fh.form.cleaned_data['lltLink1']
                    veritasCluster.lltLink2 = fh.form.cleaned_data['lltLink2']
                    veritasCluster.lltLinkLowPri_1 = fh.form.cleaned_data['lltLinkLowPri1']
                    veritasCluster.save(force_update=True)
                    gcoIpObj.save(force_update=True)
                    csgIpObj.save(force_update=True)
                    return fh.success()
            except IntegrityError as e:
                fh.message = "Issue updating the veritas information, Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Issue validating the veritas information, Exception : " + str(e)
            logger.error(fh.message)
            return fh.display()
    else:
        return fh.display()

@login_required
@transaction.atomic
def updateClusterServer(request, cluster_id, serverId, option):
    '''
    The updateClusterServer function is used to populate the edit server form
    or delete a server that exists in a cluster
    '''
    userId = request.user.pk
    clusterObject = Cluster.objects.get(id=cluster_id)
    serverObject = Server.objects.get(id=serverId)
    server = serverObject.hostname
    clusterServerObject = ClusterServer.objects.get(server=serverObject)
    nodeType = clusterServerObject.node_type
    activeStatus = clusterServerObject.active
    servers = config.get('DMT_AUTODEPLOY', 'servers')
    serverList = servers.split()
    if "-" in nodeType:
        nodeTypeCheck,number = nodeType.split("-")
    else:
        if (any(char.isdigit() for char in nodeType)):
            nodeTypeCheck = re.sub(r'[0-9]*', "", nodeType)
        else:
            nodeTypeCheck = nodeType
    if clusterObject.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObject):
            error = "You do not have permission to " +option+ " the deployment Server " + str(server) + " for " + str(clusterObject.name)
            return render(request, "dmt/dmt_error.html", {'error': error})
    if "edit" in option or "add" in option:
        name = serverObject.name
        hostname = serverObject.hostname
        hardwareType = serverObject.hardware_type
        domainName = serverObject.domain_name
        dnsServerA = serverObject.dns_serverA
        dnsServerB = serverObject.dns_serverB
        networkObjectEth1 = None
        networkObjectEth2 = None
        networkObjectEth3 = None
        networkObjectEth4 = None
        networkObjectEth5 = None
        networkObjectEth6 = None
        networkObjectEth7 = None
        networkObjectEth8 = None
        networkObjectEth9 = None
        networkObjectEth10 = None
        networkObjectEth11 = None
        eth1 = ""
        eth2 = ""
        eth3 = ""
        eth4 = ""
        eth5 = ""
        eth6 = ""
        eth7 = ""
        eth8 = ""

        try:
            networkObject = NetworkInterface.objects.get(server=serverObject.id, interface="eth0")
            nic = networkObject.mac_address
        except:
            nic=""
        try:
            extraNetworkObject = NetworkInterface.objects.filter(server=serverObject.id)
            for item in extraNetworkObject:
                if item.interface == 'eth1':
                    eth1 = item.mac_address
                if item.interface == 'eth2':
                    eth2 = item.mac_address
                if item.interface == 'eth3':
                    eth3 = item.mac_address
                if item.interface == 'eth4':
                    eth4 = item.mac_address
                if item.interface == 'eth5':
                    eth5 = item.mac_address
                if item.interface == 'eth6':
                    eth6 = item.mac_address
                if item.interface == 'eth7':
                    eth7 = item.mac_address
                if item.interface == 'eth8':
                    eth8 = item.mac_address
        except:
            extraNetworkObject = None
        try:
            wwpnOne = ""
            wwpnTwo = ""
            if HardwareIdentity.objects.filter(server=serverObject.id).exists():
                hardwareIdentityObj = HardwareIdentity.objects.filter(server=serverObject.id)
                for item in hardwareIdentityObj:
                    if item.ref == '1':
                        wwpnOne = item.wwpn
                    if item.ref == '2':
                        wwpnTwo = item.wwpn
        except:
            wwpnOne = ""
            wwpnTwo = ""
        try:
            ipAddrObject = IpAddress.objects.get(nic=networkObject.id,ipType="other")
            ipAddress = ipAddrObject.address
            ipv6Address = ipAddrObject.ipv6_address
        except:
            ipAddress = ""
            ipv6Address = ""
        try:
            storageIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="storage")
            storageIp = storageIpObject.address
        except:
            storageIpObject = None
            storageIp = ""
        try:
            bckUpIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="backup")
            bckUpIp = bckUpIpObject.address
        except:
            bckUpIpObject = None
            bckUpIp = ""
        try:
            jgroupIpObject = None
            jgroupIp = ""
            if IpAddress.objects.filter(nic=networkObject.id,ipType="jgroup").exists():
                jgroupIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="jgroup")
                jgroupIp = jgroupIpObject.address
        except:
            jgroupIpObject = None
            jgroupIp = ""
        try:
            multicastIpObject = None
            multicastIp = ""
            if IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                multicastIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="multicast")
                multicastIp = multicastIpObject.address
        except:
            multicastIpObject = None
            multicastIp = ""

        try:
            capacityType = str(DDtoDeploymentMapping.objects.only('deployment_description__capacity_type').get(cluster=clusterObject).deployment_description.capacity_type)
        except:
            capacityType = "test"

        if multicastIp == "" and not "NETSIM" in nodeType:
            multicastGateway,multicastIp,multicastBitmask=dmt.utils.getNextFreeInternalIP(clusterObject, "PDU-Priv_nodeInternalJgroup")
        if jgroupIp == "" and not "NETSIM" in nodeType:
            jgroupGateway,jgroupIp,jgroupBitmask=dmt.utils.getNextFreeInternalIP(clusterObject, "PDU-Priv_nodeInternalJgroup")
        try:
            internalIPObject = None
            internalIp = ""
            if IpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                internalIPObject = IpAddress.objects.get(nic=networkObject.id,ipType="internal")
                internalIp = internalIPObject.address
        except Exception as e:
            internalIPObject = None
            internalIp = ""
        if internalIp == "" and not "NETSIM" in nodeType:
            internalGW,internalIp,internalBitmask=dmt.utils.getNextFreeInternalIP(clusterObject)
            internalIPObject = None
        try:
            bladeExtraDetailsObject = BladeHardwareDetails.objects.get(mac_address=networkObject.id)
            enclosureObject = Enclosure.objects.get(id=bladeExtraDetailsObject.enclosure_id)
            serial_number = bladeExtraDetailsObject.serial_number
            vc_profile_name = bladeExtraDetailsObject.profile_name
        except:
            bladeExtraDetailsObject = None
            serial_number = ""
            vc_profile_name = ""
        try:
            rackExtraDetailsObject = RackHardwareDetails.objects.get(clusterServer=clusterServerObject)
            serial_number = rackExtraDetailsObject.serial_number
            uuid = rackExtraDetailsObject.bootdisk_uuid
        except:
            rackExtraDetailsObject = None
            if bladeExtraDetailsObject is None:
               serial_number = ""
            uuid = ""
        try:
            enclosure = enclosureObject.hostname
        except:
            enclosure = Enclosure.objects.all()
        try:
            iloObject = Ilo.objects.get(server=serverObject.id)
            iloIpObj = IpAddress.objects.get(id=iloObject.ipMapIloAddress_id)
            ilo_address = iloIpObj.address
            username = iloObject.username
            password = iloObject.password
        except:
            iloUsername = config.get('DMT_AUTODEPLOY', 'iloUsername')
            iloPassword = config.get('DMT_AUTODEPLOY', 'iloPassword')
            iloObject = None
            iloIpObj = None
            ilo_address = ""
            username = str(iloUsername)
            password = str(iloPassword)
        # Create a FormHandle to handle form post-processing
        fh = FormHandle()
        productType = clusterObject.management_server.product.name
        formValues = {
                      'name': name,
                      'hostname': hostname,
                      'domain_name': domainName,
                      'dns_serverA': dnsServerA,
                      'dns_serverB': dnsServerB,
                      'mac_address': nic,
                      'mac_address_eth1': eth1,
                      'mac_address_eth2': eth2,
                      'mac_address_eth3': eth3,
                      'mac_address_eth4': eth4,
                      'mac_address_eth5': eth5,
                      'mac_address_eth6': eth6,
                      'mac_address_eth7': eth7,
                      'mac_address_eth8': eth8,
                      'wwpnOne' : wwpnOne,
                      'wwpnTwo' : wwpnTwo,
                      'ip_address' :ipAddress,
                      'ipv6_address' :ipv6Address,
                      'storageIp': storageIp,
                      'bckUpIp': bckUpIp,
                      'jgroupIp': jgroupIp,
                      'internalIp': internalIp,
                      'multicastIp': multicastIp,
                      'serial_number' : serial_number,
                      'vc_profile_name' : vc_profile_name,
                      'enclosure' : enclosure,
                      'bootdisk_uuid': uuid,
                      'ilo_address' : ilo_address,
                      'username' : username,
                      'password' : password,
                      'active' : activeStatus }
        oldValues = [str(formValues['name']) + "##Machine Name", str(formValues['hostname']) + "##Hostname", str(formValues['domain_name']) + "##Domain Name",str(formValues['dns_serverA']) + "##DNS Server A",str(formValues['dns_serverB']) + "##DNS Server B",str(formValues['mac_address']) + "##Mac Address (eth0)"]
        if hardwareType == "rack":
            if capacityType == "production":
                fh.form = RackProductionServerForm()
                oldValues.extend([str(formValues['mac_address_eth1']) + "##Mac Address (eth1)",str(formValues['mac_address_eth2']) + "##Mac Address (eth2)",str(formValues['mac_address_eth3']) + "##Mac Address (eth3)",str(formValues['mac_address_eth4']) + "##Mac Address (eth4)",str(formValues['mac_address_eth5']) + "##Mac Address (eth5)",str(formValues['mac_address_eth6']) + "##Mac Address (eth6)"])
            else:
                fh.form = RackTestServerForm()
                oldValues.extend([str(formValues['mac_address_eth1']) + "##Mac Address (eth1)",str(formValues['mac_address_eth4']) + "##Mac Address (eth4)",str(formValues['mac_address_eth5']) + "##Mac Address (eth5)",str(formValues['mac_address_eth6']) + "##Mac Address (eth6)"])
            oldValues.extend([str(formValues['wwpnOne']) + "##WWPN 1",str(formValues['wwpnTwo']) + "##WWPN 2",str(formValues['bootdisk_uuid']) + "##Disk UUID", str(formValues['ip_address']) + "##IPv4 Host Address",str(formValues['ipv6_address']) + "##IPv6 Host Address",str(formValues['storageIp']) + "##Storage IP",str(formValues['bckUpIp']) + "##Backup Ip",str(formValues['jgroupIp']) + "##JGroup Ip", str(formValues['internalIp']) + "##Internal Ip", str(formValues['serial_number']) + "##Serial Number", str(formValues['ilo_address']) + "##ILO Address",str(formValues['username']) + "##ILO Usernmae",str(formValues['password']) + "##ILO Password"])
        elif nodeTypeCheck in serverList:
            if hardwareType != "blade":
                fh.form = VCSServerForm()
                if hardwareType != "cloud" and "VCS" not in nodeType:
                    fh.form.fields['mac_address_eth4'] = forms.CharField(widget=forms.widgets.HiddenInput())
                    fh.form.fields['mac_address_eth5'] = forms.CharField(widget=forms.widgets.HiddenInput())
                    fh.form.fields['mac_address_eth6'] = forms.CharField(widget=forms.widgets.HiddenInput())
                    fh.form.fields['mac_address_eth7'] = forms.CharField(widget=forms.widgets.HiddenInput())
                    fh.form.fields['mac_address_eth8'] = forms.CharField(widget=forms.widgets.HiddenInput())
                oldValues.extend([str(formValues['mac_address_eth1']) + "##Mac Address (eth1)", str(formValues['mac_address_eth2']) + "##Mac Address (eth2)", str(formValues['mac_address_eth3']) + "##Mac Address (eth3)", str(formValues['mac_address_eth4']) + "##Mac Address (eth4)", str(formValues['mac_address_eth5']) + "##Mac Address (eth5)", str(formValues['mac_address_eth6']) + "##Mac Address (eth6)",str(formValues['mac_address_eth7']) + "##Mac Address (eth7)", str(formValues['mac_address_eth8']) + "##Mac Address (eth8)", str(formValues['wwpnOne']) + "##WWPN 1", str(formValues['wwpnTwo']) + "##WWPN 2", str(formValues['ip_address']) + "##IPv4 Host Address", str(formValues['ipv6_address']) + "##IPv6 Host Address", str(formValues['storageIp']) + "##Storage IP", str(formValues['bckUpIp']) + "##Backup Ip", str(formValues['jgroupIp']) + "##JGroup Ip", str(formValues['internalIp']) + "##Internal Ip"])
            else:
                fh.form = VCSServerBladeForm()
                oldValues.extend([str(formValues['mac_address_eth1']) + "##Mac Address (eth1)",str(formValues['mac_address_eth2']) + "##Mac Address (eth2)",str(formValues['mac_address_eth3']) + "##Mac Address (eth3)",str(formValues['wwpnOne']) + "##WWPN 1",str(formValues['wwpnTwo']) + "##WWPN 2", str(formValues['ip_address']) + "##IPv4 Host Address",str(formValues['ipv6_address']) + "##IPv6 Host Address",str(formValues['storageIp']) + "##Storage IP",str(formValues['bckUpIp']) + "##Backup Ip",str(formValues['jgroupIp']) + "##JGroup Ip", str(formValues['internalIp']) + "##Internal Ip", str(formValues['enclosure']) + "##Enclosure",str(formValues['serial_number']) + "##Serial Number",str(formValues['vc_profile_name']) + "##VC Profile", str(formValues['ilo_address']) + "##ILO Address",str(formValues['username']) + "##ILO Usernmae",str(formValues['password']) + "##ILO Password"])
        elif hardwareType == "blade":
            fh.form = UpdateServerFormBlade()
            oldValues.extend([str(formValues['ip_address']) + "##IPv4 Host Address",str(formValues['ipv6_address']) + "##IPv6 Host Address",str(formValues['storageIp']) + "##Storage IP",str(formValues['bckUpIp']) + "##Backup Ip", str(formValues['internalIp']) + "##Internal Ip",str(formValues['multicastIp']) + "##Multicast Ip",str(formValues['serial_number']) + "##Serial Number",str(formValues['vc_profile_name']) + "##VC Profile",str(formValues['enclosure']) + "##Enclosure",str(formValues['ilo_address']) + "##ILO Address",str(formValues['username']) + "##ILO Usernmae",str(formValues['password']) + "##ILO Password"])
        else:
            fh.form = UpdateServerForm()
            oldValues.extend([str(ipAddress) + "##IPv4 Host Address",str(ipv6Address) + "##IPv6 Host Address",str(storageIp) + "##Storage IP",str(bckUpIp) + "##Backup Ip",str(internalIp) + "##Internal Ip",str(multicastIp) + "##Multicast Ip"])
        oldValues.extend([str(formValues['active']) + "##Server Status"])
        fh.title = "Required Information for " + str(hardwareType) + " Deployment Server : " +str(server) +" (" +nodeType+ ")"
        fh.request = request
        fh.button = "Save & Exit..."
        fh.button2 = "Cancel"
        fh.form.initial=formValues
        fh.redirectTarget = "/dmt/clusters/" + str(cluster_id)
        if "cloud" in hardwareType:
            hostnameIdentifier = macIdentifier = ipv4Identifier = ipv6Identifier = clusterObject.id
        else:
            hostnameIdentifier = macIdentifier = ipv4Identifier = ipv6Identifier = '1'

        if request.method == 'POST':
            if "Cancel" in request.POST:
                return fh.success()
            if hardwareType == "rack":
                if capacityType == "production":
                    fh.form = RackProductionServerForm(request.POST)
                else:
                    fh.form = RackTestServerForm(request.POST)
            elif nodeTypeCheck in serverList:
                if hardwareType != "blade":
                    fh.form = VCSServerForm(request.POST)
                else:
                    fh.form = VCSServerBladeForm(request.POST)
            elif hardwareType == "blade":
                fh.form = UpdateServerFormBlade(request.POST)
            else:
                fh.form = UpdateServerForm(request.POST)
            # validate the form so that the cleaned_data gets populated, then we can get the
            # requested name and define our redirect URL
            if fh.form.is_valid():
                # redirect to Management Servers page
                fh.redirectTarget = "/dmt/clusters/" + str(cluster_id)
                try:
                    with transaction.atomic():
                        hostnameCheck = fh.form.cleaned_data['hostname']
                        message = dmt.utils.hostNameCheck(fh.form.cleaned_data['hostname'])
                        if message != "OK":
                            fh.message=message
                            return fh.display()
                        addressList = newValues = []
                        addressList, newValues = dmt.utils.getDeploymentServerPOSTFormValues(fh, serverList, nodeTypeCheck, hardwareType, capacityType)
                        addressList = filter(None,addressList)
                        duplicates = dmt.utils.getDuplicatesInList(addressList)
                        if len(duplicates) > 0:
                            raise Exception("Duplicate IP Info "+str(duplicates))
                        changedContent = logChange(oldValues,newValues)
                        if bool(fh.form.cleaned_data['active']) is not clusterServerObject.active:
                            clusterServerObject.active = bool(fh.form.cleaned_data['active'])
                            clusterServerObject.save(force_update=True)
                        #Checking for NIC, otherwise one is created with given MAC_ADDRESS from the form
                        macAddresses = NetworkInterface.objects.filter(server=serverObject.id)
                        for networkInterface in macAddresses:
                            if not networkInterface.interface == "eth0":
                                networkInterface.delete()
                        exists =  NetworkInterface.objects.filter(server_id=serverObject.id).exists()
                        if not exists:
                            networkObject=NetworkInterface.objects.create(server=serverObject,mac_address = fh.form.cleaned_data['mac_address'],nicIdentifier=macIdentifier)
                        networkObject.mac_address = fh.form.cleaned_data['mac_address']
                        networkObject.nicIdentifier = macIdentifier
                        networkObject.save(force_update=True)
                        macAddressEth = ['eth1', 'eth2', 'eth3', 'eth4', 'eth5', 'eth6', 'eth7', 'eth8']
                        if nodeTypeCheck in serverList:
                            for eth in macAddressEth:
                                # Add the extra Nic info
                                # eth
                                try:
                                    ethFormValue = fh.form.cleaned_data['mac_address_'+str(eth)]
                                except:
                                    ethFormValue = ""
                                if ethFormValue != "":
                                    if NetworkInterface.objects.filter(server_id=serverObject.id,interface=str(eth)).exists():
                                        networkObjectEth=NetworkInterface.objects.get(server=serverObject,interface=str(eth))
                                        networkObjectEth.mac_address = ethFormValue
                                        networkObjectEth.nicIdentifier = macIdentifier
                                        networkObjectEth.save(force_update=True)
                                    else:
                                        networkObjectEth=NetworkInterface.objects.create(server=serverObject,mac_address=ethFormValue,interface=str(eth),nicIdentifier=macIdentifier)
                        #Update the Cluster Server Information
                        serverObject.name = fh.form.cleaned_data['name']
                        serverObject.hostname = fh.form.cleaned_data['hostname']
                        serverObject.hostnameIdentifier = hostnameIdentifier
                        serverObject.domain_name = fh.form.cleaned_data['domain_name']
                        serverObject.dns_serverA = fh.form.cleaned_data['dns_serverA']
                        serverObject.dns_serverB = fh.form.cleaned_data['dns_serverB']
                        serverObject.hardware_type = hardwareType
                        # Multicast/jgroup address can be handled the same as a internal ip
                        # so it can be removed from the overall IP table if it exists
                        # and added to the internalIPAddress table CIP-6571
                        if nodeTypeCheck not in serverList:
                            if fh.form.cleaned_data['multicastIp'] != "":
                                if not IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                                    multicastIpObject = IpAddress.objects.create(nic=networkObject,ipType="multicast",address = fh.form.cleaned_data['multicastIp'],ipv4UniqueIdentifier=clusterObject.id)
                                else:
                                    multicastIpObject.address = fh.form.cleaned_data['multicastIp']
                                    multicastIpObject.save(force_update=True)
                            else:
                                IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").delete()

                        elif nodeTypeCheck in serverList:
                            if fh.form.cleaned_data['jgroupIp'] != "":
                                if not IpAddress.objects.filter(nic=networkObject.id,ipType="jgroup").exists():
                                    jgroupIpObject = IpAddress.objects.create(nic=networkObject,ipType="jgroup",address = fh.form.cleaned_data['jgroupIp'],ipv4UniqueIdentifier=clusterObject.id)
                                else:
                                    jgroupIpObject.address = fh.form.cleaned_data['jgroupIp']
                                    jgroupIpObject.save(force_update=True)
                            else:
                                IpAddress.objects.filter(nic=networkObject.id,ipType="jgroup").delete()
                            if fh.form.cleaned_data['wwpnOne'] != "":
                                if not HardwareIdentity.objects.filter(server_id=serverObject.id,ref='1').exists():
                                    hardwareIdentityObjOne = HardwareIdentity.objects.create(server_id=serverObject.id,wwpn=fh.form.cleaned_data['wwpnOne'],ref='1')
                                else:
                                    hardwareIdentityObjOne = HardwareIdentity.objects.get(server_id=serverObject.id,ref='1')
                                    hardwareIdentityObjOne.wwpn = fh.form.cleaned_data['wwpnOne']
                                    hardwareIdentityObjOne.save(force_update=True)
                            else:
                                if HardwareIdentity.objects.filter(server_id=serverObject.id,ref='1').exists():
                                    HardwareIdentity.objects.filter(server_id=serverObject.id,ref='1').delete()

                            if fh.form.cleaned_data['wwpnTwo'] != "":
                                if not HardwareIdentity.objects.filter(server_id=serverObject.id,ref='2').exists():
                                    hardwareIdentityObjTwo = HardwareIdentity.objects.create(server_id=serverObject.id,wwpn=fh.form.cleaned_data['wwpnTwo'],ref='2')
                                else:
                                    hardwareIdentityObjTwo = HardwareIdentity.objects.get(server_id=serverObject.id,ref='2')
                                    hardwareIdentityObjTwo.wwpn = fh.form.cleaned_data['wwpnTwo']
                                    hardwareIdentityObjTwo.save(force_update=True)
                            else:
                                if HardwareIdentity.objects.filter(server_id=serverObject.id,ref='2').exists():
                                    HardwareIdentity.objects.filter(server_id=serverObject.id,ref='2').delete()
                            # If the storage IP address doesn't exist already create it as long as an Storage IP is given
                            if fh.form.cleaned_data['storageIp'] != "":
                                if not IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
                                    storageIpObject = IpAddress.objects.create(nic=networkObject,ipType="storage",address = fh.form.cleaned_data['storageIp'],ipv4UniqueIdentifier = ipv4Identifier)
                                else:
                                    storageIpObject.address = fh.form.cleaned_data['storageIp']
                                    storageIpObject.ipv4UniqueIdentifier = ipv4Identifier
                                    storageIpObject.save(force_update=True)
                            else:
                                IpAddress.objects.filter(nic=networkObject.id,ipType="storage").delete()
                            if fh.form.cleaned_data['bckUpIp'] != "":
                                if not IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
                                    bckUpIpObject = IpAddress.objects.create(nic=networkObject,ipType="backup",address = fh.form.cleaned_data['bckUpIp'],ipv4UniqueIdentifier = ipv4Identifier)
                                else:
                                    bckUpIpObject.address = fh.form.cleaned_data['bckUpIp']
                                    bckUpIpObject.ipv4UniqueIdentifier = ipv4Identifier
                                    bckUpIpObject.save(force_update=True)
                            else:
                                IpAddress.objects.filter(nic=networkObject.id,ipType="backup").delete()
                            if fh.form.cleaned_data['internalIp'] != "":
                                if not IpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                                    internalIPObject = IpAddress.objects.create(nic=networkObject,ipType="internal",address = fh.form.cleaned_data['internalIp'],ipv4UniqueIdentifier=clusterObject.id)
                                else:
                                    internalIPObject.address = fh.form.cleaned_data['internalIp']
                                    internalIPObject.save(force_update=True)
                            else:
                                IpAddress.objects.filter(nic=networkObject.id,ipType="internal").delete()
                        # Need the else state below to remove the entry if they wish to remove reference to storae IP as the address field is unique
                        # and we can't have multiple blank addresses within the address field
                        if "SVC" in str(nodeType) and "add" in str(option):
                            multicastTypes = VlanMulticastType.objects.all()
                            for item in multicastTypes:
                                if "BR0" in str(item.name):
                                    VlanMulticast.objects.create(clusterServer=clusterServerObject, multicast_type=item, multicast_snooping="1", multicast_querier="1", multicast_router="2", hash_max="2048")
                                elif "BR3" in str(item.name):
                                    VlanMulticast.objects.create(clusterServer=clusterServerObject, multicast_type=item, multicast_snooping="0", multicast_querier="0", multicast_router="1", hash_max="512")
                        ipv6Address = dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['ipv6_address'])
                        if not IpAddress.objects.filter(nic=networkObject.id,ipType="other").exists():
                            ipAddrObject = IpAddress.objects.create(nic=networkObject,ipType="other",address = fh.form.cleaned_data['ip_address'],ipv6_address = ipv6Address,ipv4UniqueIdentifier=ipv4Identifier,ipv6UniqueIdentifier=ipv6Identifier)
                        ipAddrObject.address = fh.form.cleaned_data['ip_address']
                        ipAddrObject.ipv4UniqueIdentifier = ipv4Identifier
                        ipAddrObject.ipv6_address = ipv6Address
                        ipAddrObject.ipv6UniqueIdentifier = ipv6Identifier
                        serverObject.save(force_update=True)
                        clusterServerObject.node_type = nodeType
                        clusterServerObject.save(force_update=True)
                        networkObject.save(force_update=True)
                        ipAddrObject.save(force_update=True)
                        if hardwareType == "blade" or hardwareType == "rack":
                            if hardwareType == "blade":
                                enclosureObj = Enclosure.objects.get(hostname=fh.form.cleaned_data['enclosure'])
                                if fh.form.cleaned_data['serial_number'] != "" and fh.form.cleaned_data['vc_profile_name'] != "":
                                    if bladeExtraDetailsObject is None:
                                        bladeExtraDetailsObject =  BladeHardwareDetails.objects.create(mac_address_id=networkObject.id,enclosure_id=enclosureObj.id,serial_number=fh.form.cleaned_data['serial_number'],profile_name=fh.form.cleaned_data['vc_profile_name'])
                                    else:
                                        bladeExtraDetailsObject.serial_number = fh.form.cleaned_data['serial_number']
                                        bladeExtraDetailsObject.profile_name = fh.form.cleaned_data['vc_profile_name']
                                        bladeExtraDetailsObject.enclosure = enclosureObj
                                        bladeExtraDetailsObject.save(force_update=True)
                                else:
                                    fh.message = "ERROR : Blank Server Serial Number or VC Profile Fields. Please update..."
                                    logger.error(fh.message)
                                    return fh.display()
                            if hardwareType == "rack":
                                if fh.form.cleaned_data['serial_number'] != "" and fh.form.cleaned_data['bootdisk_uuid'] != "":
                                    if rackExtraDetailsObject is None:
                                        rackExtraDetailsObject =  RackHardwareDetails.objects.create(clusterServer=clusterServerObject,bootdisk_uuid=fh.form.cleaned_data['bootdisk_uuid'],serial_number=str(fh.form.cleaned_data['serial_number']))
                                    else:
                                        rackExtraDetailsObject.bootdisk_uuid = fh.form.cleaned_data['bootdisk_uuid']
                                        rackExtraDetailsObject.serial_number = str(fh.form.cleaned_data['serial_number'])
                                        rackExtraDetailsObject.save(force_update=True)
                            if fh.form.cleaned_data['ilo_address'] == "" and ( fh.form.cleaned_data['username'] != "" or fh.form.cleaned_data['password'] != "" ):
                                fh.message = "WARNING : Please ensure ILO information is filled in entirely. Alternatively you can leave all ILO fields blank"
                                logger.error(fh.message)
                                return fh.display()
                            if fh.form.cleaned_data['ilo_address'] != "" and ( fh.form.cleaned_data['username'] == "" or fh.form.cleaned_data['password'] == "" ):
                                fh.message = "WARNING : Please ensure ILO information is filled in entirely. Alternatively you can leave all ILO fields blank"
                                logger.error(fh.message)
                                return fh.display()
                            if fh.form.cleaned_data['ilo_address'] != "" and fh.form.cleaned_data['username'] != "" and fh.form.cleaned_data['password'] != "":
                                iloAdd = fh.form.cleaned_data['ilo_address']
                                iloUnE = fh.form.cleaned_data['username']
                                iloPwd = fh.form.cleaned_data['password']
                                if iloObject != None:
                                    iloIpObj.address = iloAdd
                                    iloIpObj.ipv4UniqueIdentifier = ipv4Identifier
                                    iloObject.username = iloUnE
                                    iloObject.password = iloPwd
                                    iloIpObj.save(force_update=True)
                                    iloObject.ipMapIloAddress = iloIpObj
                                    iloObject.save(force_update=True)
                                else:
                                    try:
                                        iloIpObj = IpAddress.objects.create(address=iloAdd,ipType="ilo_" + str(serverObject.id))
                                        iloObj = Ilo.objects.create(ipMapIloAddress=iloIpObj,server=serverObject,username=iloUnE,password=iloPwd)
                                        iloIpObj.save(force_update=True)
                                        iloObj.save(force_update=True)
                                    except Exception as e:
                                        fh.message = "Issue Adding update ILO Address information to DB: " +str(e)
                                        logger.error(fh.message)
                                        return fh.display()
                            else:
                                if iloObject != None:
                                    if iloIpObj != None:
                                        iloIpObj.delete()
                                    iloObject.delete()
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if option == "edit":
                            message = "Edited Deployment Server Configuration, " + str(changedContent)
                        else:
                            message = "Added Deployment Server Configuration (Stage 3)"
                        logAction(userId, clusterServerObject, option, message)
                        return fh.success()
                except IntegrityError as e:
                    fh.message = "Problem updating Deployment Server " +str(server)+" in the database, Exception : " + str(e) + " -- Please Try Again"
                    logger.warn(fh.message)
                    return fh.display()
                except Exception as e:
                    fh.message = "Problem updating Deployment Server " +str(server)+" in the database, Exception : " + str(e) + " -- Please Try Again"
                    logger.warn(fh.message)
                    return fh.display()
            else:
                fh.message = "Form is not valid, -- Please Try Again"
                logger.warn(fh.message)
                return fh.display()
        else:
            return fh.display()

@login_required
@transaction.atomic
def deleteClusterServer(request, cluster_id, serverId):
    '''
    Deleting Cluster Server
    '''
    userId = request.user.pk
    clusterObject = Cluster.objects.get(id=cluster_id)
    serverObject = Server.objects.get(id=serverId)
    server = serverObject.hostname
    clusterServerObject = ClusterServer.objects.get(server=serverObject)
    nodeType = clusterServerObject.node_type
    if clusterObject.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObject):
            error = "You do not have permission to Delete the deployment Server " + str(server) + " for " + str(clusterObject.name)
            return render(request, "dmt/dmt_error.html", {'error': error})
    dictDeletedInfo = {}
    dictDeletedInfo["contentTypeId"] = ContentType.objects.get_for_model(clusterObject).pk
    dictDeletedInfo["objectId"] = clusterObject.pk
    dictDeletedInfo["objectRep"] = force_unicode(clusterObject)
    try:
        with transaction.atomic():
            try:
                message = "Deleted Deployment Server Configuration: " + str(server) + " ("+ str(clusterServerObject.node_type) +")"
                networkObject = NetworkInterface.objects.get(server=serverObject.id, interface="eth0")
                try:
                    if HardwareIdentity.objects.filter(server_id=serverObject.id).exists():
                        HardwareIdentity.objects.filter(server_id=serverObject.id).delete()
                    if IpAddress.objects.filter(nic=networkObject.id,ipType="backup").exists():
                        bckUpIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="backup").delete()
                    # This info is now part of the internalIPAddress table
                    if IpAddress.objects.filter(nic=networkObject.id,ipType="multicast").exists():
                        multicastIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="multicast").delete()
                    if IpAddress.objects.filter(nic=networkObject.id,ipType="storage").exists():
                        storageIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="storage").delete()
                    if IpAddress.objects.filter(nic=networkObject.id,ipType="internal").exists():
                        internalIpObject = IpAddress.objects.get(nic=networkObject.id,ipType="internal").delete()
                    if VlanMulticast.objects.filter(clusterServer=clusterServerObject).exists():
                        VlanMulticast.objects.filter(clusterServer=clusterServerObject).delete()
                    try:
                        iloObj = Ilo.objects.get(server=serverObject.id)
                        iloIpObj = IpAddress.objects.get(id=iloObj.ipMapIloAddress_id)
                        iloIpObj.delete()
                        iloObj.delete()
                    except:
                        logger.info("No ILO defined on "+str(server))
                    Server.objects.filter(id=serverId).delete()
                    if RackHardwareDetails.objects.filter(clusterServer=clusterServerObject).exists():
                        RackHardwareDetails.objects.filter(clusterServer=clusterServerObject).delete()
                    ClusterServer.objects.filter(server=serverObject).delete()
                    try:
                        NetworkInterface.objects.filter(server=serverObject.id).delete()
                    except:
                        logger.info("No NIC defined on "+str(server))
                    try:
                        IpAddress.objects.filter(nic=networkObject.id).delete()
                    except:
                        logger.info("No IPs defined on "+str(server))
                    try:
                        IpAddress.objects.filter(nic=networkObject.id).delete()
                    except:
                        logger.info("No Internal IPs defined on "+str(server))
                    cursor = connection.cursor()
                except Exception as e:
                    raise CommandError("There was an issue deleting server " +str(server)+ " from database: " +str(e))
            except:
                logger.info("No NIC defined on "+str(server))
            try:
                Server.objects.filter(id=serverId).delete()
                message = "Deleted Deployment Server Configuration: " + str(server) + " ("+ str(clusterServerObject.node_type) +")"
            except:
                logger.info("No Server Data could be found for : "+str(server))
            if VirtualImage.objects.filter(node_list = nodeType, cluster = cluster_id).exists():
                virtualImageNames = VirtualImage.objects.filter(node_list = nodeType, cluster = cluster_id).values_list("name", flat=True)
                for vmName in virtualImageNames:
                    returnedValueVM,VmMessage = dmt.utils.deleteVirtualImage(cluster_id, vmName)
            logAction(userId,clusterObject,"delete",message,dictDeletedInfo)
    except Exception as e:
        raise CommandError("There was an issue deleting server " +str(server)+ " from database: " +str(e))
    return HttpResponseRedirect("/dmt/clusters/" + str(cluster_id))

def sshKey(request):
    '''
    the sshKey function is to read in the public SSH Key from the ciconfig file
    '''
    pageHitCounter("SSHKey", None, str(request.user))
    jenkinsSSHkey = config.get('DMT_SERVER', 'jenkinsSSHkey')
    cloudJenkinsSSHkey = config.get('DMT_SERVER', 'cloudJenkinsSSHkey')
    return render(request, "dmt/ssh_info.html", {"ssh_key": jenkinsSSHkey, "cloudSSHKey": cloudJenkinsSSHkey})

@login_required
@csrf_exempt
def populateOrVerifyDeployment(request, task, deploymentId=None):
    '''
    This function is used to populate the info within the populateDeployment.html or verifyDeployment.html file
    '''
    pageHitCounter("UploadPre-PopulatedSED", None, str(request.user))
    userId = request.user.pk
    deploymentTemplatePackage = config.get('DMT_AUTODEPLOY', 'deploymentTemplatePackage')
    fieldSedTemplate = ('version',)
    sedTemplateVersions = Sed.objects.only(fieldSedTemplate).values(*fieldSedTemplate).order_by('-id')
    sedMasterObj = SedMaster.objects.get(identifer='ENM-Virtual')
    version = sedMasterObj.sedMaster_virtual.version
    sedVersionList = []
    allDDtypes = DeploymentDescriptionType.objects.all()
    allVersions = []
    allVersions = allVersions + [item.version for item in DeploymentDescriptionVersion.objects.all()]
    allVersions.sort(key=LooseVersion)
    allVersions.reverse()
    latestDDversion = None
    try:
        latestDDversion = DeploymentDescriptionVersion.objects.get(latest=True).version
    except ObjectDoesNotExist as e:
        message = "Issue getting Latest Deployment Description Version: " + str(e)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    formValues = {}
    for item in sedTemplateVersions:
        if item['version'] == version:
            sedVersionList.append(item['version'] + " (Maintrack Master Sed)")
        else:
            sedVersionList.append(item['version'])
    fieldType = ('name',)
    userTypes = UserTypes.objects.only(fieldType).values(*fieldType)
    formValues["loginUser"] = userId
    formValues["deploymentTemplatePackage"] = deploymentTemplatePackage
    formValues["sedTemplateVersions"] = sedVersionList
    formValues["userTypes"] = userTypes
    formValues["task"] = task
    formValues["deploymentId"] = deploymentId
    formValues["ddVersions"] = allVersions
    formValues["latestVersion"] = latestDDversion
    formValues["ddTypes"] = allDDtypes
    if task == "verify":
        return render(request, "dmt/verifyDeployment.html", formValues)
    else:
        return render(request, "dmt/populateDeployment.html", formValues)

@login_required
@csrf_exempt
def executePopulateOrVerifyDeployment(request, task):
    '''
    This function is used to either execute the population of the deployment or verify the vm Service information with the info from the populateDeployment.html/verifyDeployment.html
    '''
    action = "Edit"
    config = CIConfig()
    if request.method == 'POST':
        rawJson = request.body
        decodedJson = json.loads(rawJson)
        deploymentId = decodedJson['deploymentId']
        if Cluster.objects.filter(id=deploymentId).exists():
            deploymentObj = Cluster.objects.get(id=deploymentId)
        else:
            return HttpResponse(json.dumps({"ERROR":"ERROR: Please ensure the deployment ID referenced is correct."}),content_type="application/json")
        if task.lower() != "verify":
            htmlResponce = "dmt/populatedDeploymentResults.html"
            if deploymentObj.group != None:
                if Group.objects.filter(id=deploymentObj.group_id).exists():
                    deploymentGroup = Group.objects.get(id=deploymentObj.group_id)
                else:
                    return HttpResponse(json.dumps({"ERROR":"ERROR: Unable to find the group associated to this deployment. Please contact an Administrator."}),content_type="application/json")
                if User.objects.filter(username=str(request.user)).exists():
                    userCheck = User.objects.get(username=str(request.user))
                else:
                    return HttpResponse(json.dumps({"ERROR":"ERROR: Unable to find your user information. Please ensure you are logged in."}),content_type="application/json")
                if userCheck.groups.filter(name=deploymentGroup.name).exists() or userCheck.is_superuser:
                    permission = True
                else:
                    permission = False
            else:
                permission = True
        else:
            htmlResponce = "dmt/verifiedDeploymentResults.html"
            permission = True
        if permission == True:
            (ret,result) = dmt.uploadContent.updateDataVMServices(action,rawJson,task)
            if ret != 0:
                return HttpResponse(json.dumps({"ERROR":result}),content_type="application/json")
            return render(request, htmlResponce,{"result":result,"clusterDetails":deploymentObj,})
        else:
            return HttpResponse(json.dumps({"ERROR":"ERROR: User not authorised to execute this functionality against this deployment deployment " + str(deploymentId) + ". If you should have access to this deployment, please contact your Administrator."}),content_type="application/json")
    else:
        return HttpResponse(json.dumps({"ERROR":"ERROR: This interface accepts HTTP POST requests only."}),content_type="application/json")

@login_required
@csrf_exempt
def upload_file(request):
    '''
    Function used to upload a SED to create the deployment information
    '''
    userId = request.user.pk
    action = "Edit"
    fh = FormHandle()
    fh.form = UploadFileForm()
    fh.title = "Upload the Pre-Populated SED"
    fh.request = request
    fh.button = "Upload ..."
    result = None
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_uploaded_file(request.FILES['file'],'seduploadfile.txt','/tmp')
            str(request.POST.get("node_type"))
            clusterId = str(request.POST.get('clusterId'))
            clusterObj = Cluster.objects.get(id=clusterId)
            if clusterObj.group != None:
                clusterGroup = Group.objects.get(id=clusterObj.group_id)
                userCheck = User.objects.get(username=str(request.user))
                if userCheck.groups.filter(name=clusterGroup.name).exists() or userCheck.is_superuser:
                    permission = True
                else:
                    permission = False
            else:
                permission = True
            if permission == True:
                populatedSedLoc = config.get('DMT_MGMT', 'populatedSedLocation')
                managementObj = ManagementServer.objects.get(id=clusterObj.management_server.id)
                result = dmt.uploadContent.uploadContentMain(clusterId, populatedSedLoc)
                message = "Uploaded Pre-Populated SED File"
                logAction(userId, clusterObj, action, message)
                return render(request, "dmt/uploadPopulateSed.html",{"result":result,"clusterDetails":clusterObj,})
            else:
                return render(request, "dmt/dmt_error.html",{'error':'User not authorised to Upload a Pre-Populated SED to Cluster '+ clusterId +'. If you should have access to this deployment, please contact ENM TE Service and Support.'})
    else:
        form = UploadFileForm()
    return fh.display()

@login_required
def deployCluster(request,cluster):
    '''
    The deployCluster function is used to deploy a deployment to the LITP Management server
    It expects to take in a landscape definition and inventory file as imputs, then
    deploys these files to the Management server and in turn calls forks of the LITP install    by envoking the runLitpCommands function
    '''
    clusterObject = Cluster.objects.get(id=cluster)
    mgmtServer = clusterObject.management_server

    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.form = deployServerForm()
    fh.title = "LITP Auto Deploy Deployment"+str(cluster)+" on LMS "+str(mgmtServer)
    fh.request = request
    fh.button = "Deploy ..."

    if request.method == 'POST':
        fh.form = deployServerForm(request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        if fh.form.is_valid():
            # redirect to the deployment page
            fh.redirectTarget = "/dmt/clusters/" + str(cluster)
            try:
                startClusterDeployment(fh.request,cluster)
                return fh.success()
            except:
                return fh.failure()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
@transaction.atomic
def uploadSed(request):
    '''
    Function used to upload a New SED template into the DB to be used for auto deployment
    '''
    userId = request.user.pk
    action = "add"
    userCheck = User.objects.get(username=str(request.user))
    sedGroup = config.get("DMT", "sedgroup")
    if not userCheck.groups.filter(name=sedGroup).exists():
        return render(request, "dmt/sed_error.html",{'error':'User not authorised to Upload SED Versions'})

    fh = FormHandle()
    fh.request = request
    fh.title = "Upload a new System Environment Description"
    fh.button = "Submit"
    fh.button2 = "Cancel"
    emptyDbCheck = Sed.objects.annotate(Count('id'))
    if len(emptyDbCheck) != 0:
        try:
            versionLatest = Sed.objects.latest('dateInserted').version
        except Exception as e:
            logInfo="Unable to get the latest SED version from the DB: " + str(e)
            logger.error(logInfo)
            fh.message = logInfo
            return fh.display()
        try:
            splitversion = versionLatest.split(".")
            versionThirdOctet = int(splitversion[2]) + 1
            versionThirdOctet = splitversion[0] + "." + splitversion[1] + "." + str(versionThirdOctet)
        except Exception as e:
            logInfo="Unable to get the latest SED version from the DB: " + str(e)
            logger.error(logInfo)
            fh.message = logInfo
            return fh.display()
    else:
        versionThirdOctet = "1.0.1"
    fh.form = SedForm(initial={'version': str(versionThirdOctet),'user': str(request.user)})

    if request.method == 'POST':
        fh.form = SedForm(request.POST)
        fh.redirectTarget = "/dmt/ViewUploadSED/"
        if "Cancel" in request.POST:
           return fh.success()
        try:
            version = request.POST.get("version")
            sed = request.POST.get("sed")
            user = request.POST.get("user")
            linkText = request.POST.get("linkText")
            link = request.POST.get("link")
            iso = request.POST.get("iso")
            jiraNumber = request.POST.get("jiraNumber")
            if not str(sed):
                logInfo="Enter a SED otherwise press Cancel"
                fh.message = logInfo
                logger.error(logInfo)
                return fh.display()
            if not str(linkText) and str(link):
                logInfo="Enter Text for the link otherwise leave both ERIcoll SED fields blank"
                fh.message = logInfo
                logger.error(logInfo)
                return fh.display()
            elif not str(link) and str(linkText):
                logInfo="Enter a link otherwise leave both ERIcoll SED fields blank"
                fh.message = logInfo
                logger.error(logInfo)
                return fh.display()
        except Exception as e:
            logger.error("Issue with upload SED form data")
            return fh.display()
        try:
            if "None" in str(iso):
                iso = None
            else:
                iso = str(iso).replace("u", "").replace("'","")
                iso = ISObuild.objects.get(version=str(iso), drop__release__product__name="ENM", mediaArtifact__testware=0, mediaArtifact__category__name="productware")
            returnedValue = dmt.utils.uploadSedData(user,version,sed,jiraNumber,iso,linkText,link)
            if returnedValue == 1:
                logInfo="Unable to save data into the DB"
                logger.error(logInfo)
                fh.message = logInfo
                return fh.display()
            else:
                message = "Added New SED Version: " + str(version)
                sedObj = Sed.objects.get(version=version)
                logAction(userId, sedObj, action, message)
                return fh.success()
        except Exception as e:
            logInfo="Unable to save data into the DB : " + str(e)
            logger.error(logInfo)
            fh.message = logInfo
            return fh.display()
    else:
        return fh.display()

@login_required
def editSED(request, version):
    '''
    Edit SED for Link, JIRA and ISO version
    '''
    userId = request.user.pk
    action = "edit"
    userCheck = User.objects.get(username=str(request.user))
    sedGroup = config.get("DMT", "sedgroup")
    if not userCheck.groups.filter(name=sedGroup).exists():
        return render(request, "dmt/sed_error.html",{'error':'User not authorised to Edit SED Versions'})

    fh = FormHandle()
    fh.request = request
    fh.title = "Edit System Environment Description"
    fh.button = "Submit"
    fh.button2 = "Cancel"
    sed = Sed.objects.get(version=version)
    try:
        fh.form = SedEditForm(initial={'jiraNumber':str(sed.jiraNumber), 'iso': str(sed.iso.version), 'linkText': str(sed.linkText), 'link': str(sed.link)})
    except Exception as e:
        fh.form = SedEditForm(initial={'jiraNumber':str(sed.jiraNumber), 'linkText': str(sed.linkText), 'link': str(sed.link)})

    if request.method == 'POST':
        fh.form = SedEditForm(request.POST)
        fh.redirectTarget = "/dmt/ViewUploadSED/"
        if "Cancel" in request.POST:
           return fh.success()
        try:
            if sed.iso == None:
                sedVersionLog = ""
            else:
                sedVersionLog = str(sed.iso.version)
            if request.POST.get("iso") == None or request.POST.get("iso") == "None":
                sedVersionUpdatedLog = ""
            else:
                sedVersionUpdatedLog = str(request.POST.get("iso"))
            oldValues = [str(sedVersionLog) + "## SED Version",str(sed.linkText) + "##ERIcoll SED Link Text",str(sed.link) + "##ERIcoll SED Link",str(sed.jiraNumber) + "##Jira Number"]
            newValues = [str(sedVersionUpdatedLog),str(request.POST.get("linkText")),str(request.POST.get("link")),str(request.POST.get("jiraNumber"))]
            changedContent = logChange(oldValues,newValues)
            linkText = request.POST.get("linkText")
            link = request.POST.get("link")
            iso = request.POST.get("iso")
            jiraNumber = request.POST.get("jiraNumber")
            if not str(linkText) and str(link):
                logInfo="Enter Text for the link otherwise leave both ERIcoll SED fields blank"
                fh.message = logInfo
                logger.error(logInfo)
                return fh.display()
            elif not str(link) and str(linkText):
                logInfo="Enter a the link otherwise leave both ERIcoll SED fields blank"
                fh.message = logInfo
                logger.error(logInfo)
                return fh.display()
        except Exception as e:
            logger.error("Issue with Edit SED form data")
            return fh.display()
        try:
            sed = Sed.objects.get(version=version)
            if not "None" in str(iso):
                iso = str(iso).replace("u", "").replace("'","")
                iso = ISObuild.objects.get(version=str(iso), drop__release__product__name="ENM", mediaArtifact__testware=0, mediaArtifact__category__name="productware")
            else:
                iso = None
            sed.iso = iso
            sed.linkText = str(linkText)
            sed.link = str(link)
            sed.jiraNumber = str(jiraNumber)
            sed.save()
            message = "Edited SED details, " + str(changedContent)
            logAction(userId, sed, action, message)
            return fh.success()
        except Exception as e:
            logInfo="Unable to save data into the DB : " + str(e)
            logger.error(logInfo)
            fh.message = logInfo
            return fh.display()
    else:
        return fh.display()

@transaction.atomic
def viewUploadSed(request):
    '''
    '''
    pageHitCounter("SED", None, str(request.user))
    # Create a FormHandle to handle form post-processing
    try:
        allSedData = Sed.objects.all().order_by('-id')[:50]
    except Exception as e:
        logInfo="Unable to get the Sed objects : " + str(e)
        logger.error(logInfo)
    idTag = config.get("DMT", "dmtra")
    idTagVirt = config.get("DMT", "dmtravirtual")
    masterId = None
    VirtualMasterId = None
    if idTag == 'ENM':
        if SedMaster.objects.filter(identifer=idTag).exists():
            sedMasterObject = SedMaster.objects.get(identifer=idTag)
            masterId = sedMasterObject.sedMaster_id

    if idTagVirt == 'ENM-Virtual':
        if SedMaster.objects.filter(identifer=idTagVirt).exists():
            sedMasterObject = SedMaster.objects.get(identifer=idTagVirt)
            virtualMasterId = sedMasterObject.sedMaster_virtual_id
        else:
            virtualMasterId = masterId

    return render(request, "dmt/sedData.html",
            {
                "allSedData": allSedData,
                "masterId": masterId,
                "virtualMasterId": virtualMasterId,
            }
         )

def searchInventory(request, entry=None):
    '''
    Function used to search through the deployment inventory information for anything that may through a duplicate error
    '''
    valueEntered = None
    allResults = None
    if 'entry' in request.POST:
        valueEntered = request.POST['entry']
        if valueEntered != "":
            allResults = dmt.searchInventory.searchInventory(valueEntered)
    else:
        pageHitCounter("SearchInventory", None, str(request.user))
    return render(request, "dmt/searchInventory.html",
                {
                    "valueEntered":valueEntered,
                    "allResults":allResults
                }
            )

def displayDeploymentData(request):
    '''
    The displayDeploymentData function is used to return drops and versions from the database
    '''
    pageHitCounter("DefaultAutodeploymentVersions", None, str(request.user))
    ipmiVersionObj = IpmiVersionMapping.objects.all()
    redfishVersionObj = RedfishVersionMapping.objects.all()
    deployScriptObj = DeployScriptMapping.objects.all()
    sedObj = SedMaster.objects.all()

    return render(request, "dmt/displayDeploymentData.html",
            {
                "ipmiVersionObj":ipmiVersionObj,
                "redfishVersionObj":redfishVersionObj,
                "deployScriptObj":deployScriptObj,
                "sedObj":sedObj,
            }
        )

@login_required
def mapVirtualSed(request, version):
    '''
    The mapVirtualSed function is used to Map a SED version to the Master SED by calling the Utils setVirtualSedMaster Function.
    '''
    # Create a FormHandle to handle form post-processing
    userId = request.user.pk
    action = "edit"
    idTag = config.get("DMT", "dmtravirtual")
    sed = Sed.objects.get(version=version)
    virtualMasterId = sed.id
    sedUser = str(request.user)
    user = User.objects.get(username=sedUser)
    sedGroup = config.get("DMT", "sedgroup")
    if not user.groups.filter(name=sedGroup).exists():
        return render(request, "dmt/sed_error.html",{'error':'User not authorised to write to modify Master'})
    try:
        sed = Sed.objects.get(id=virtualMasterId)
        if sed.link:
            dmt.utils.setVirtualSedMaster(idTag,sedUser,virtualMasterId)
        else:
            return render(request, "dmt/sed_error.html",{'error':'Requires ERIcoll SED Link Before you can set it to Master'})
    except Exception as e:
        logInfo="Unable to get the Sed objects : " + str(e)
        logger.error(logInfo)
    message = "Edited SED details, set SED version " + str(sed.version) + " as master"
    logAction(userId, sed, action, message)
    return HttpResponseRedirect("/dmt/ViewUploadSED/")

def handle_uploaded_file(file, name, localInvDefDirectory):
    '''
    The handle_uploaded_file function handles the files uploaded using the CIFWK UI Forms
    '''
    try:
        destination = open(localInvDefDirectory+"/"+str(name), 'wb+')
    except Exception as e:
        logger.error("There was an issue handling uploaded file from UI Form: " +str(e))
    for chunk in file.chunks():
        destination.write(chunk)
    destination.close()

def startClusterDeployment(request,cluster):
    '''
    The startClusterDeployment validates the LITP deployemnt file input and then
    handles these file and scp's them over to the LITP management server and then
    fork of the deployment of the LITP deployment on the management server
    '''
    localInvDefDirectory = tempfile.mkdtemp()
    form = deployServerForm(request.POST, request.FILES)
    if form.is_valid():
        fileList = []
        landscapeDefinition = str(form.cleaned_data['landscape_definition'])
        handle_uploaded_file(request.FILES['landscape_definition'], landscapeDefinition, localInvDefDirectory)
        fileList.append(landscapeDefinition)
        landscapeInventory = str(form.cleaned_data['landscape_inventory'])
        handle_uploaded_file(request.FILES['landscape_inventory'], landscapeInventory, localInvDefDirectory)
        fileList.append(landscapeInventory)
        try:
            dmt.utils.clusterDeploymentSetup(fileList,cluster,landscapeDefinition,landscapeInventory, localInvDefDirectory)
        except Exception as e:
            logger.error("Unable to call the paramiko sftp function:  " +str(e))
        try:
            dmt.utils.paramikoSftp(mgmtServerFqdn, mgmtServerUser, mgmtServerMultiDir+landscapeInventory, "/tmp/"+landscapeInventory, mgmtServerPort, mgmtServerPrivateKeyfile)
        except Exception as e:
            logger.error("Unable to call the paramiko sftp function:  " +str(e))
        os.unlink("/tmp/"+landscapeDefinition)
        os.unlink("/tmp/"+landscapeInventory)

        #Fork off LITP install on a seperate thread so web page can continue to be used
        child_pid = os.fork()
        if child_pid == 0:
            try:
                dmt.utils.runLitpCommands(mgmtServerUser, mgmtServerFqdn, mgmtServerMultiDir,landscapeDefinition, landscapeInventory, cluster)
                logger.info("DEPLOY LITP forked off on process: " + str(os.getpid()))
            except Exception as e:
                logger.error("DEPLOY LITP fork Failed: " + str(e))
        time.sleep(5)
    else:
       logger.error("FORM not Valid")

#@login_required
# Application Templates - cloud stuff
#
def appTemplates(request):
    return render(request, "dmt/app_templates.html", {'templates': AppTemplate.objects.all()})

def appTemplate(request, template):
    tpl = AppTemplate.objects.get(name=template)
    vms = AppHost.objects.filter(template=tpl)
    vmInfo = dict()
    for vm in vms:
        vmData = dict()
        vmData['hostname'] = vm.hostname
        # get IPS OF THIS HOST
        ipMap = AppHostIpMap.objects.filter(apphost=vm)
        ipAddr = []
        for ip in ipMap:
            ipAddr.append(ip.ip_addr.value)
        vmData['ipaddresses'] = ipAddr
        vmData['type'] = vm.type
        vmInfo[vm.name] = vmData

    return render(request, "dmt/app_template.html", {'template': tpl, 'vmInfo': vmInfo})

def startApp(request, template):
    tpl = None
    try:
        tpl = AppTemplate.objects.get(name=template)
    except AppTemplate.DoesNotExist:
        return render(request, "dmt/dmt_error.html",
                {"error": "A template named " + template + " does not exist in the CI DB"} )
    vms = AppHost.objects.filter(template=tpl)
    appName = template + "_CIFWK_" + time.strftime("%Y-%m-%d_%H:%M:%S")
    try:
        driver = dmt.cloud.auth()
        rt = dmt.cloud.startApp(driver, template, appName)
        if (rt != 0):
            errstr = "An error occurred deploying the provided template"
            if (rt == 1):
                errstr = errstr + ": the provided template does not exist"
            else:
                errstr = errstr + ": please refer to the server logs for details"
            return render(request, "dmt/dmt_error.html",
                    {"error": errstr})
    except Exception as e:
        return render(request, "dmt/dmt_error.html",
                {"error": "We got an error trying to instantiate " + template + ": " +
                    str(e)})
    return render(request, "dmt/app_template.html", {'template': tpl, 'vms': vms})

def appHost(request, apptemplate, vmtemplate):
    app_tpl = AppTemplate.objects.get(name=apptemplate)
    vm_tpl = AppTemplate.objects.get(name=vmtemplate,template=app_tpl)
    return render(request, "dmt/vm_template.html", {'template': app_tpl, 'vm': vm_tpl})

@login_required
def buildClusterArtifact(request, clusterId):
    '''
    '''
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    clusterObj = Cluster.objects.get(id=clusterId)
    managementObj = ManagementServer.objects.get(id=clusterObj.management_server.id)
    theProduct = Product.objects.get(name=managementObj.product.name)
    cfg_template="rvDeploy"
    fh.title = "Download Install Configuration file for " +str(theProduct.name)+" Deployment: " +str(clusterObj.name)
    fh.request = request
    fh.button = "Download SED File"
    fh.button2 = "Cancel"
    fh.redirectTarget= "/dmt/clusters/" + str(clusterId)
    if request.method == 'POST':
        if "Cancel" in request.POST:
            return fh.success()
        sedVersion = request.POST.get('sedVersion')
        try:
            sed = dmt.buildconfig.generateDBConfigFile(clusterId,sedVersion)
            fileName=str(clusterObj.name)+"-config.cfg"
            response = HttpResponse(sed, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename='+fileName
            return response
        except Exception as e:
            logger.error("Issue with artifact Build " +str(e))
            return fh.failure()

    else:
        try:
            sedObj = Sed.objects.all().order_by('-id')
            sedVersionOptionList = []
            sedVersion = dmt.utils.getMasterSedVersion()
            masterList = []
            masterList.append(sedVersion)
            masterList.append('Master (CMW)')
            sedVersion = dmt.utils.getVirtualMasterSedVersion()
            masterListEnm = []
            masterListEnm.append(sedVersion)
            masterListEnm.append('Master (KVM)')
            sedVersionOptionList.append(masterListEnm)
            sedVersionOptionList.append(masterList)
            for item in sedObj:
                tmpList=[]
                tmpList.append(str(item.version))
                tmpList.append(str(item.version))
                sedVersionOptionList.append(tmpList)

            if sedVersionOptionList == []:
                fh.message = "DataBase contains no Sed versions Information and try again"
                return fh.display()
            fh.form = BuildArtifact(sedVersionOptionList)
            return fh.display()
        except Exception as e:
            logger.error("Oops there was a problem with displaying form: " + str(e))
            return fh.failure()

def getHostProperties(request,clusterId):
    '''
    Return host properties info
    '''
    try:
        message="Rest call dmt/getHostProperties was called for deployment ID: "+str(clusterId)+"\n\nThis rest call is obsolete and should no longer be used"
        dmt.utils.obsoleteFunctionNotifier(message)
        ret,buildDir = dmt.utils.getHostProperties(clusterId)
        hostpropertiesFH = open(ret)
        retString=hostpropertiesFH.read()
        hostpropertiesFH.close()
        dmt.utils.removeTmpArea(buildDir)
        retString=retString.replace("\n"," ")
        retString=retString.replace("\r","")
        return HttpResponse(retString, content_type="text/plain")
    except Exception as e:
        logger.error("There was a problem displaying the information : " + str(e))
        return HttpResponse("There was a problem displaying the information: check that the deployment has all information required then please try again.", content_type="text/plain")

@csrf_exempt
def generateTAFHostProperties(request):
    '''
    The generateTAFHostProperties function is a REST call to generate a list of host properties for
    the TAF SUT host.properties file, using CIFWK db entries and CITE REST call
    '''
    if request.method == 'GET':
        clusterId = request.GET.get('clusterId')
        format = request.GET.get('format')
        citeHostPropertiesFile = request.GET.get('citeHostPropertiesFile')
        if citeHostPropertiesFile is not None:
            citeHostPropertiesFile = citeHostPropertiesFile.split(',')
    if request.method == 'POST':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")
    if clusterId is None:
        return HttpResponse("Error: Deployment ID is Required\n")
    try:
        propertiesList = dmt.utils.buildUpTAFHostPropertiesNodesList(clusterId)
    except Exception as e:
        return HttpResponse("Error: Building host properties List with CIFWK DB Info" +str(e))
    try:
        if citeHostPropertiesFile is not None:
            propertiesList = dmt.utils.buildUpTAFHostPropertiesUsingCITERestCall(citeHostPropertiesFile, propertiesList)
    except Exception as e:
        return HttpResponse("Error: Build hosting properties List using CITE REST" +str(e))
    if format == "mvn":
        tmpList = ""
        for tmpProp in propertiesList:
            tmpProp = tmpProp.replace("\n","")
            tmpProp = tmpProp.replace("\r","")
            if str(tmpProp) == " " or str(tmpProp) == "" :
                logger.info("No value")
            else:
                tmpList = tmpList+" -D"+str(tmpProp)
        propertiesList=tmpList
        propertiesList = propertiesList.replace("ms-1","ms1")
        propertiesList = propertiesList.replace("ms-2","ms2")
        propertiesList = propertiesList.replace("sc-1","sc1")
        propertiesList = propertiesList.replace("sc-2","sc2")
    return HttpResponse(propertiesList)

def getPackageInfo(request):
    '''
    Function used to return the associated package according to the version information entered
    '''
    if request.method == 'POST':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")
    package = request.GET.get('package')
    if package == "" or not Package.objects.filter(name=package).exists():
        return HttpResponse("Error: Package is an required input, eg: ERICenmsgmspm_CXP9031582, please also ensure that this a valid package name\n")
    version = request.GET.get('version',"latest")
    if str(version.lower()) == "latest":
        version = "None"
        completeArtifactURL = "None"
        latest = "yes"
    elif "http" in version.lower():
        return HttpResponse("Error: Need to input a version\nVersion can be inputted as an optional extra. version=1.1.1\nor version=1.1.Latest\n")
    else:
        if not PackageRevision.objects.filter(package__name=package,version=version).exists():
            return HttpResponse("Error: Package: " + str(package) + " with version: " +str(version) + " does not exist.\n")
        completeArtifactURL = "None"
        latest = "no"
    packageObject = getPackageObject(package,version,completeArtifactURL,latest)
    return HttpResponse(packageObject.version + "::" + packageObject.groupId)

@csrf_exempt
@gzip_page
def generateTAFHostPropertiesJSON(request):
    '''
    The generateTAFHostPropertiesJSON returns the data of a defined deployment id in JSON format
    There is also an option to hook into the CITE host details but defining a citeHostPropertiesFile or many comma seperated.
    '''
    clusterId = None
    if request.method == 'GET':
        clusterId = request.GET.get('clusterId')
        citeHostPropertiesFile = request.GET.get('citeHostPropertiesFile')
        tunnel = request.GET.get('tunnel')
        pretty = request.GET.get('pretty')
        tunnelNetsim = request.GET.get('tunnelNetsim')
        sanInfo = request.GET.get('sanInfo',False)
        allNetsims = request.GET.get('allNetsims')
        iloDetails = request.GET.get('iloDetails')
        if pretty != None:
            if pretty.lower() == "false":
                pretty = False
            elif pretty.lower() == "true":
                pretty = True
        else:
            pretty = False

        if tunnel != None:
            if tunnel.lower() == "false":
                tunnel = False
            elif tunnel.lower() == "true":
                tunnel = True
        else:
            tunnel = False

        if iloDetails != None:
            if iloDetails.lower() == "false":
                iloDetails = False
            elif  iloDetails.lower() == "true":
                iloDetails = True
        else:
            iloDetails = False

        if tunnelNetsim != None:
            if tunnelNetsim.lower() == "false":
                tunnelNetsim = False
            elif tunnelNetsim.lower() == "true":
                tunnelNetsim = True
        else:
            tunnelNetsim = False

        if type(sanInfo) != bool:
            if sanInfo.lower() == "true":
                sanInfo = True
            else:
                sanInfo = False

        if allNetsims != None:
           if allNetsims.lower() == "false":
               allNetsims = False
           elif allNetsims.lower() == "true":
               allNetsims = True


    if request.method == 'POST':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")
    if clusterId is None or not clusterId or clusterId == "None":
        return HttpResponse("Error: Deployment ID is Required\n")
    if citeHostPropertiesFile is not None:
        citeHostPropertiesFile = citeHostPropertiesFile.split(',')
    try:
        line = dmt.utils.buildTAFHostPropertiesAndReturnInJSON(clusterId,tunnel,tunnelNetsim, allNetsims, iloDetails)
    except Exception as e:
        logger.error("There was an issue build host properties: " +str(e))
        return HttpResponse("Error: There was an issue build host properties: " +str(e))
    try:
        if citeHostPropertiesFile is not None:
            line = dmt.utils.buildUpTAFHostPropertiesJSONUsingCITERestCall(citeHostPropertiesFile, line)
    except Exception as e:
        return HttpResponse("Error: Build hosting properties List using CITE REST" +str(e))
    try:
        if sanInfo:
            sanData = dmt.utils.addSanInfoToTAFHostPropertiesJSON(clusterId,[])
            try:
                enclosureInfo = dmt.infoforConfig.getEnclosureInfo(clusterId)[0]
            except Exception as e:
                return HttpResponse("Error with retrieving enclosure information: " + str(e))
            try:
                nasInfo = dmt.infoforConfig.getNASStorageDetails(clusterId)
            except Exception as e:
                return HttpResponse("Issue get OSS-RC NAS and Storage details: " +str(e))
            dictList = enclosureInfo, nasInfo
            for infoDict in dictList:
                if type(infoDict) == dict:
                    sanData = dmt.infoforConfig.createconfigDb(infoDict, str(sanData))
            if type(sanData) == str:
                sanData = sanData.replace("u'", "\"").replace("'", "\"").replace("None","\"\"")
                sanData = re.sub(r'<\w+>', "", sanData)
                line.append(json.loads(sanData)[0])

    except Exception as e:
        return HttpResponse("Error: Unable to collect SAN properties: "+str(e))
    if pretty:
        ret = json.dumps(line, sort_keys=True, indent=4)
    else:
        ret = json.dumps(line)

    return HttpResponse(ret,content_type="application/json")

def generateSED(request):
    sedVersion = request.GET.get('version',None)
    clusterId  = request.GET.get('clusterId')
    drop  = request.GET.get('drop','None')
    if sedVersion == None :
        sedVersion = dmt.utils.getMasterSedVersion()
        if sedVersion == None:
            return HttpResponse("Error", content_type='text/plain')
    sed = dmt.buildconfig.generateDBConfigFile(clusterId,sedVersion)
    return HttpResponse(sed, content_type='text/plain')

@csrf_exempt
@transaction.atomic
def deploymentStatus(request):
    '''
    POST and GET for a Deployment Status
    '''
    results = status = osDetails = patches = litp = artifact = pkgs = description = deployStatus = None
    if request.method == 'GET':
        clusterId = request.GET.get('clusterId')
        try:
            deployStatus = DeploymentStatus.objects.get(cluster__id=clusterId)
        except Exception as e:
            logger.error("Issue getting Deployment Status for Deployment ID " + str(clusterId) +",  Error: " +str(e))
            results = json.dumps([{"ERROR":"ERROR"}])
            return HttpResponse(results,content_type="application/json")

    if request.method == 'POST':
        clusterId = request.POST.get('clusterId')
        status = request.POST.get('status')
        osDetails = request.POST.get('os')
        patches = request.POST.get('patches')
        litp = request.POST.get('litp')
        artifact = request.POST.get('artifact')
        pkgs = request.POST.get('packages')
        description = request.POST.get('description')
        try:
            deployStatus = DeploymentStatus.objects.get(cluster__id=clusterId)
            if status:
                status = DeploymentStatusTypes.objects.get(status=str(status))
                deployStatus.status = status
            if osDetails:
                deployStatus.osDetails = osDetails
            if patches:
                deployStatus.patches = patches
            if litp:
                deployStatus.litpVersion = litp
            if artifact:
                deployStatus.mediaArtifact = artifact
            if pkgs:
                pkgs = str(pkgs).replace("::", "-")
                pkgs = str(pkgs).replace("@@", ", ")
                deployStatus.packages = pkgs
            if description:
                deployStatus.description = description
            deployStatus.status_changed = datetime.now()
            try:
                with transaction.atomic():
                    deployStatus.save()
            except IntegrityError as e:
                logger.error("There was an Issue updating Deployment Status for Deployment ID " + str(clusterId) + ", Error: " +str(e))
                results = json.dumps([{"ERROR":"ERROR"}])
                return HttpResponse(results,content_type="application/json")
        except Exception as e:
            logger.error("Issue with updating Deployment Status for Deployment ID " + str(clusterId) + ",  Error: " +str(e))
            results = json.dumps([{"ERROR":"ERROR"}])
            return HttpResponse(results,content_type="application/json")
    try:
        status = str(deployStatus.status)
        osDetails = str(deployStatus.osDetails)
        patches = str(deployStatus.patches)
        litp = str(deployStatus.litpVersion)
        artifact = str(deployStatus.mediaArtifact)
        pkgs = str(deployStatus.packages)
        description = str(deployStatus.description)
        results = json.dumps([{"Status": status,
                           "OS" : osDetails,
                           "Patches" : patches,
                           "LITP" : litp,
                           "ENMartifact": artifact,
                           "KGBpackages": pkgs,
                           "Description": description}])
    except Exception as e:
        logger.error("Issue getting Deployment Status for Deployment ID into a json return,  Error: " +str(e))
        results = json.dumps([{"ERROR":"ERROR"}])
    return HttpResponse(results,content_type="application/json")


@login_required
@csrf_exempt
def uploadSnapshotRpmRest(request, file =None):
    '''
    POST files to temporary http area using curl cli
    '''
    fh = FormHandle()
    fh.form = UploadSnapshotForm()
    fh.title = "Upload required file to Http server"
    fh.request = request
    fh.button = "Upload"
    result = None

    form = UploadSnapshotForm(request.POST, request.FILES)
    if form.is_valid():
            fileObj = request.FILES['file']
            fileName = request.FILES['file'].name
            dateTimeNow = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            path = config.get('DMT_AUTODEPLOY', 'uploadpath')
            command = "cd "  + path + " ; find . -type f -printf \"%T@ %p\n\" | sort -nr | cut -d\  -f2-"
            dirList = commands.getoutput(command )
            dirList = dirList.split()
            uploadUrl = config.get('DMT_AUTODEPLOY', 'uploadUrl')
            handleUploadedSnapshot(fileObj)
            return HttpResponse("\n Success: 'file' uploaded to " + uploadUrl + dateTimeNow + "/" + str(fileName))
    return fh.display()

@csrf_exempt
def uploadSnapshotRpm(request, file =None):
    '''
    POST files to temporary http area through UI
    '''
    try:
        pageHitCounter("Pre-CommitStagingArea", None, str(request.user))
        result = None
        dateTimeNow = ""
        fileName = ""
        path = config.get('DMT_AUTODEPLOY', 'uploadpath')
        command = "cd " + path  +" ; find . -type f -printf \"%T@ %p\n\" | sort -nr | cut -d\  -f2-"
        dirList = commands.getoutput(command)
        dirList = dirList.split()
        uploadUrl = config.get('DMT_AUTODEPLOY', 'uploadUrl')
        if "file" in request.FILES:
            file = request.FILES['file']
            if file !="":
                fileObj = request.FILES['file']
                fileName = request.FILES['file'].name
                dateTimeNow = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                handleUploadedSnapshot(fileObj)
                return render(request, "dmt/fileupload.html",{"uploadUrl":uploadUrl, "dateTimeNow":dateTimeNow,"fileName":fileName, "file":file, "dirList":dirList})
        return render(request, "dmt/fileupload.html",
                {
                    "file":file, "dirList":dirList, "dateTimeNow":dateTimeNow,"fileName":fileName
                }
            )
    except Exception as error:
        errMsg = "Issue Uploading Snapshot: " + str(error)
        logger.error(errMsg)
        return render_to_response("dmt/dmt_error.html", {'error': errMsg})

def handleUploadedSnapshot(fileName):
    '''
    Function to upload files to the Directory
    '''
    path = config.get('DMT_AUTODEPLOY', 'uploadpath')
    myDir = os.path.join('/proj/lciadm100/tmpUploadSnapshot/', datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    try:
        os.makedirs(myDir)
    except OSError, e:
        if e.errno != 17:
            raise # This was not a "directory exist" error..
    with open(os.path.join(myDir, str(fileName)), 'w') as destination:
        for chunk in fileName.chunks():
            destination.write(chunk)

def getMasterSedVersion(request):
    '''
    Return SED version for Master Sed
    '''
    version = "None"
    try:
        sedMasterObj = SedMaster.objects.get(identifer='ENM-Virtual')
        version = sedMasterObj.sedMaster_virtual.version
    except Exception as e:
        logger.error("Issue getting SED Versions. Exception: "+str(e))
        version = "None"
    return HttpResponse(version,content_type="text/plain")

def getDeployScriptMapping(request,drop=None,osVersion=None):
    '''
    Rerurns the deploy script version
    '''
    version = "None"
    try:
        drop = request.GET.get('drop')
        osVersion = request.GET.get('osVersion')
        version = dmt.utils.getDeployScriptVersion(drop, osVersion)
    except Exception as e:
        logger.error("Issue getting deploy Script version. Exception: "+str(e))
        version = "None"
    return HttpResponse(version,content_type="text/plain")

class ServerUtilizationView(TemplateView):
    template_name = "dmt/serverUtilization.html"

@login_required
@transaction.atomic
def lvsRouterVip(request, clusterId, action):
    '''
    The lvsRouter is called to add the lvsRouter ip information to the deployment.
    '''
    lVSRouterValues = {}
    oldValues = []
    editValues = {}
    addValues = {}
    userId = request.user.pk
    fh = FormHandle()
    taskTitle = action.title()
    fh.title = str(taskTitle) + " LVS Router VIP Information"
    fh.request = request
    fh.button = "Save & Exit ..."
    fh.button4 = "Cancel..."
    fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"
    clusterObj = Cluster.objects.get(id=clusterId)

    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Update LVS Router Cluster for Deployment: " +str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    try:
        oldValues,addValues,editValues,lVSRouterValues = dmt.utils.getLVSRouterValues(clusterObj,action)
    except Exception as error:
        message = "No Vip Info Assigned to deployment: " + str(clusterId) + ". Exception: " + str(error)
        logger.error(message)
        fh.message = message
        return fh.display()

    if request.method == 'POST':
        if "Cancel..." in request.POST:
            return fh.success()
        fh.form = LVSRouterVipForm(request.POST)
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    lVSRouterValues = { 'pmInternal': fh.form.cleaned_data['pmInternal'], 'pmExternal': fh.form.cleaned_data['pmExternal'],
                                        'fmInternal': fh.form.cleaned_data['fmInternal'], 'fmExternal': fh.form.cleaned_data['fmExternal'],
                                        'fmInternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['fmInternalIPv6']), 'fmExternalIPv6':dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['fmExternalIPv6']),
                                        'cmInternal': fh.form.cleaned_data['cmInternal'], 'cmExternal': fh.form.cleaned_data['cmExternal'],
                                        'cmInternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['cmInternalIPv6']), 'cmExternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['cmExternalIPv6']),
                                        'svcPMstorage': fh.form.cleaned_data['svcPMstorage'], 'svcFMstorage': fh.form.cleaned_data['svcFMstorage'],
                                        'svcCMstorage': fh.form.cleaned_data['svcCMstorage'], 'svcStorageInternal': fh.form.cleaned_data['svcStorageInternal'],
                                        'svcStorage': fh.form.cleaned_data['svcStorage'], 'scpSCPinternal': fh.form.cleaned_data['scpSCPinternal'],
                                        'scpSCPexternal': fh.form.cleaned_data['scpSCPexternal'], 'scpSCPinternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['scpSCPinternalIPv6']),
                                        'scpSCPexternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['scpSCPexternalIPv6']), 'scpSCPstorage': fh.form.cleaned_data['scpSCPstorage'],
                                        'scpStorageInternal': fh.form.cleaned_data['scpStorageInternal'], 'scpStorage': fh.form.cleaned_data['scpStorage'],
                                        'evtStorageInternal': fh.form.cleaned_data['evtStorageInternal'], 'evtStorage': fh.form.cleaned_data['evtStorage'],
                                        'strSTRif': fh.form.cleaned_data['strSTRif'], 'strInternal': fh.form.cleaned_data['strInternal'],
                                        'strSTRinternal2': fh.form.cleaned_data['strSTRinternal2'], 'strSTRinternal3': fh.form.cleaned_data['strSTRinternal3'],
                                        'strExternal': fh.form.cleaned_data['strExternal'], 'strSTRexternal2': fh.form.cleaned_data['strSTRexternal2'],
                                        'strSTRexternal3': fh.form.cleaned_data['strSTRexternal3'], 'strSTRinternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['strSTRinternalIPv6']),
                                        'strSTRinternalIPv62': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['strSTRinternalIPv62']), 'strSTRinternalIPv63': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['strSTRinternalIPv63']),
                                        'strExternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['strExternalIPv6']), 'strSTRexternalIPv62': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['strSTRexternalIPv62']),
                                        'strSTRexternalIPv63': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['strSTRexternalIPv63']), 'strSTRstorage': fh.form.cleaned_data['strSTRstorage'],
                                        'strStorageInternal': fh.form.cleaned_data['strStorageInternal'], 'strStorage': fh.form.cleaned_data['strStorage'],
                                        'esnSTRif': fh.form.cleaned_data['esnSTRif'], 'esnSTRinternal': fh.form.cleaned_data['esnSTRinternal'],
                                        'esnSTRexternal': fh.form.cleaned_data['esnSTRexternal'], 'esnSTRinternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['esnSTRinternalIPv6']),
                                        'esnSTRexternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['esnSTRexternalIPv6']), 'esnStorageInternal': fh.form.cleaned_data['esnStorageInternal'],
                                        'esnSTRstorage': fh.form.cleaned_data['esnSTRstorage'], 'ebsStorageInternal': fh.form.cleaned_data['ebsStorageInternal'],
                                        'ebsStrExternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['ebsStrExternalIPv6']),
                                        'asrStorageInternal': fh.form.cleaned_data['asrStorageInternal'], 'ebsStorage': fh.form.cleaned_data['ebsStorage'],
                                        'asrStorage': fh.form.cleaned_data['asrStorage'], 'asrAsrStorage': fh.form.cleaned_data['asrAsrStorage'],
                                        'asrAsrExternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['asrAsrExternalIPv6']), 'asrAsrInternal': fh.form.cleaned_data['asrAsrInternal'],
                                        'asrAsrExternal': fh.form.cleaned_data['asrAsrExternal'], 'ebaStorageInternal': fh.form.cleaned_data['ebaStorageInternal'],
                                        'ebaStorage': fh.form.cleaned_data['ebaStorage'], 'msossfmInternal': fh.form.cleaned_data['msossfmInternal'],
                                        'msossfmExternal': fh.form.cleaned_data['msossfmExternal'], 'msossfmInternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['msossfmInternalIPv6']),
                                        'msossfmExternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['msossfmExternalIPv6']),
                                        'ebaInternal': fh.form.cleaned_data['ebaInternal'],
                                        'ebaInternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['ebaInternalIPv6']),
                                        'ebaExternal': fh.form.cleaned_data['ebaExternal'],
                                        'ebaExternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['ebaExternalIPv6']),
                                        'svcPmPublicIpv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['svcPmPublicIpv6']),
                                        'oranInternal':  fh.form.cleaned_data['oranInternal'],
                                        'oranInternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['oranInternalIPv6']),
                                        'oranExternal':  fh.form.cleaned_data['oranExternal'],
                                        'oranExternalIPv6': dmt.utils.normalizedIpv6Postfix(fh.form.cleaned_data['oranExternalIPv6']),
                                      }
                    if action == "edit":
                        returnedValue,message = dmt.utils.updateLVSRouterVip(lVSRouterValues,clusterObj,action)
                        newValues = [str(lVSRouterValues['pmInternal']), str(lVSRouterValues['pmExternal']),
                                     str(lVSRouterValues['fmInternal']), str(lVSRouterValues['fmExternal']),
                                     str(lVSRouterValues['fmInternalIPv6']), str(lVSRouterValues['fmExternalIPv6']),
                                     str(lVSRouterValues['cmInternal']), str(lVSRouterValues['cmExternal']),
                                     str(lVSRouterValues['cmInternalIPv6']), str(lVSRouterValues['cmExternalIPv6']),
                                     str(lVSRouterValues['svcPMstorage']), str(lVSRouterValues['svcFMstorage']), str(lVSRouterValues['svcCMstorage']),
                                     str(lVSRouterValues['svcStorageInternal']), str(lVSRouterValues['svcStorage']),
                                     str(lVSRouterValues['scpSCPinternal']), str(lVSRouterValues['scpSCPexternal']),
                                     str(lVSRouterValues['scpSCPinternalIPv6']), str(lVSRouterValues['scpSCPexternalIPv6']), str(lVSRouterValues['scpSCPstorage']),
                                     str(lVSRouterValues['scpStorageInternal']), str(lVSRouterValues['scpStorage']),
                                     str(lVSRouterValues['evtStorageInternal']), str(lVSRouterValues['evtStorage']),
                                     str(lVSRouterValues['strSTRif']), str(lVSRouterValues['strInternal']), str(lVSRouterValues['strSTRinternal2']), str(lVSRouterValues['strSTRinternal3']),
                                     str(lVSRouterValues['strExternal']), str(lVSRouterValues['strSTRexternal2']), str(lVSRouterValues['strSTRexternal3']),
                                     str(lVSRouterValues['strSTRinternalIPv6']), str(lVSRouterValues['strSTRinternalIPv62']), str(lVSRouterValues['strSTRinternalIPv63']),
                                     str(lVSRouterValues['strExternalIPv6']), str(lVSRouterValues['strSTRexternalIPv62']),  str(lVSRouterValues['strSTRexternalIPv63']),
                                     str(lVSRouterValues['strSTRstorage']), str(lVSRouterValues['strStorageInternal']), str(lVSRouterValues['strStorage']),
                                     str(lVSRouterValues['esnSTRif']), str(lVSRouterValues['esnSTRinternal']), str(lVSRouterValues['esnSTRexternal']),
                                     str(lVSRouterValues['esnSTRinternalIPv6']), str(lVSRouterValues['esnSTRexternalIPv6']),
                                     str(lVSRouterValues['esnStorageInternal']), str(lVSRouterValues['esnSTRstorage']),
                                     str(lVSRouterValues['ebsStorageInternal']), str(lVSRouterValues['ebsStorage']), str(lVSRouterValues['ebsStrExternalIPv6']),
                                     str(lVSRouterValues['asrStorage']), str(lVSRouterValues['asrStorageInternal']),
                                     str(lVSRouterValues['asrAsrStorage']), str(lVSRouterValues['asrAsrExternalIPv6']), str(lVSRouterValues['asrAsrInternal']),
                                     str(lVSRouterValues['asrAsrExternal']),
                                     str(lVSRouterValues['ebaStorageInternal']), str(lVSRouterValues['ebaStorage']),
                                     str(lVSRouterValues['msossfmInternal']), str(lVSRouterValues['msossfmExternal']),
                                     str(lVSRouterValues['msossfmInternalIPv6']), str(lVSRouterValues['msossfmExternalIPv6'])]

                        if LVSRouterVipExtended.objects.filter(cluster_id = clusterObj.id).exists():
                            newValues.extend([str(lVSRouterValues['ebaInternal']), str(lVSRouterValues['ebaExternal']),
                                              str(lVSRouterValues['ebaInternalIPv6']), str(lVSRouterValues['ebaExternalIPv6']),
                                              str(lVSRouterValues['svcPmPublicIpv6']), str(lVSRouterValues['oranInternal']), str(lVSRouterValues['oranInternalIPv6']), str(lVSRouterValues['oranExternal']), str(lVSRouterValues['oranExternalIPv6'])])

                        changedContent = logChange(oldValues,newValues)
                    else:
                        returnedValue,message = dmt.utils.createLVSRouterVip(lVSRouterValues,clusterObj)
                    if returnedValue == "1":
                        fh.message = "Error: " + str(message)
                        logger.error(fh.message)
                        return fh.display()
                    else:
                        if action == "edit":
                            message = "Edited LVS Router VIP Information, " + str(changedContent)
                        else:
                            message = "Added LVS Router VIP Information"
                        logAction(userId, clusterObj, action, message)
                        return fh.success()
            except Exception as e:
                fh.message = "Failed to add LVS Router VIP address to deployment " + str(clusterObj.name) + ". Exception : " + str(e)
                logger.error(fh.message)
                return fh.display()
        else:
            fh.message = "Failed to add LSV Router VIP address information to deployment"
            logger.error(fh.message)
            return fh.display()
    else:
        if action == "add":
            fh.form = LVSRouterVipForm(initial=addValues)
        elif action == "edit":
            fh.form = LVSRouterVipForm(initial=editValues)
        elif action == "delete":
            returnedValue,message = dmt.utils.updateLVSRouterVip(lVSRouterValues,clusterObj,action)
            message = "Deleted LVS Router Information"
            logAction(userId, clusterObj, action, message)
            return fh.success()
        return fh.display()

@login_required
@transaction.atomic
def vlanMulticast(request,serverId,action):
    '''
    form data for vlanMulticast
    '''
    userId = request.user.pk
    clusterServerObj = clusterId = vlanMulticastObj = None
    try:
        clusterServerObj = ClusterServer.objects.get(id=serverId)
        clusterId = clusterServerObj.cluster.id
    except Exception as e:
        message = "Failed to get Deployment Server. Exception: " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    oldValues = []
    newValues = []
    message = None

    if clusterServerObj.cluster.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterServerObj.cluster):
            error = "You do not have permission to Update VLAN Multicast for Deployment Server: " +str(clusterServerObj.server.hostname)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    typesOptions = VlanMulticastType.objects.all()
    hashMaxOptions = str(config.get("DMT", "hashMax")).split()

    if request.method == 'POST':
        snooping= str(request.POST.get('multicast_snooping'))
        querier = str(request.POST.get('multicast_querier'))
        router = str(request.POST.get('multicast_router'))
        hashMax = str(request.POST.get('hash_max'))
        if action == "add":
            try:
                typeName = str(request.POST.get('multicast_type'))
                multicastType = VlanMulticastType.objects.get(name=typeName)
                try:
                    with transaction.atomic():
                        vlanMulticastObj = VlanMulticast.objects.create(clusterServer=clusterServerObj, multicast_type=multicastType, multicast_snooping=snooping, multicast_querier=querier, multicast_router=router, hash_max=hashMax)
                except IntegrityError as e:
                    message = "Failed to Save VLAN Multicast to Deployment Server: " + str(clusterServerObj.server.hostname) + ". Exception : " + str(e)
            except Exception as e:
                message = "Failed to add VLAN Multicast to Deployment Server: " + str(clusterServerObj.server.hostname) + ". Exception : " + str(e)
            if message:
                logger.error(message)
                return render(request, "dmt/vlanMulticastForm.html",{
                    "message": message,
                    "action": action,
                    "serverId": serverId,
                    "typesOptions": typesOptions,
                    "hashMaxOptions": hashMaxOptions,
                    "clusterId" : clusterId,
                    })
        elif action == "edit":
            try:
                typeName = str(request.GET.get('multicast_type'))
                vlanMulticastObj = VlanMulticast.objects.get(clusterServer=clusterServerObj, multicast_type__name=typeName)
            except Exception as e:
                message = "Failed to Update VLAN Multicast to Deployment Server: " + str(clusterServerObj.server.hostname) + ". Exception : " + str(e)
                logger.error(message)
                return render_to_response("dmt/dmt_error.html", {'error': message})
            oldValues = [str(vlanMulticastObj.multicast_type.name) + "##Type",
                         str(vlanMulticastObj.multicast_snooping) + "##Multicast Snooping",
                         str(vlanMulticastObj.multicast_querier) + "##Multicast Querier",
                         str(vlanMulticastObj.multicast_router) + "##Multicast Router",
                         str(vlanMulticastObj.hash_max) + "##Hash Max"]
            vlanMulticastObj.multicast_snooping = snooping
            vlanMulticastObj.multicast_querier = querier
            vlanMulticastObj.multicast_router = router
            vlanMulticastObj.hash_max = hashMax
            try:
                with transaction.atomic():
                    vlanMulticastObj.save()
            except IntegrityError as e:
                message = "Failed to Update VLAN Multicast to Deployment Server: " + str(clusterServerObj.server.hostname) + ". Exception : " + str(e)
                logger.error(message)
                return render(request, "dmt/vlanMulticastForm.html",{
                    "message": message,
                    "vlanMulticastObj": vlanMulticastObj,
                    "action": action,
                    "serverId": serverId,
                    "typesOptions": typesOptions,
                    "hashMaxOptions": hashMaxOptions,
                    "clusterId" : clusterId,
                    "multicast_type": typeName,
                   })

        newValues = [str(vlanMulticastObj.multicast_type.name), str(vlanMulticastObj.multicast_snooping), str(vlanMulticastObj.multicast_querier),
                     str(vlanMulticastObj.multicast_router), str(vlanMulticastObj.hash_max)]
        if action == "edit":
            changedContent = logChange(oldValues,newValues)
            message = "Edited VLAN Multicast Information: " + str(vlanMulticastObj.multicast_type.name) + " - " + str(vlanMulticastObj.multicast_type.description) + ": " + str(changedContent)
        else:
            message = "Added VLAN Multicast Information: " + str(vlanMulticastObj.multicast_type.name) + " - " + str(vlanMulticastObj.multicast_type.description)
        logAction(userId, clusterServerObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    else:
        if action == "add":
            return render(request, "dmt/vlanMulticastForm.html",{
                        "action": action,
                        "serverId": serverId,
                        "typesOptions": typesOptions,
                        "hashMaxOptions": hashMaxOptions,
                        "clusterId" : clusterId,
                      }
                   )
        else:
            try:
                typeName = str(request.GET.get('multicast_type'))
                vlanMulticastObj = VlanMulticast.objects.get(clusterServer=clusterServerObj, multicast_type__name=typeName)
            except Exception as e:
                message = "Failed to Get VLAN Multicast Information for Deployment Server: " + str(clusterServerObj.server.hostname) + ". Exception : " + str(e)
                logger.error(message)
                return render_to_response("dmt/dmt_error.html", {'error': message})
            return render(request, "dmt/vlanMulticastForm.html",
                      {
                          "vlanMulticastObj": vlanMulticastObj,
                          "action": action,
                          "serverId": serverId,
                          "type": typeName,
                          "typesOptions": typesOptions,
                          "hashMaxOptions": hashMaxOptions,
                          "clusterId" : clusterId,
                          "multicast_type": typeName,
                      }
                    )
@login_required
@transaction.atomic
def hybridCloud(request, clusterId, action):
    '''
    Hybrid Cloud function
    '''
    userId = request.user.pk
    hybridCloudValues = {}
    editValues = {}
    oldValues = []
    formValues = {}
    formValues['clusterId'] = clusterId
    formValues['action'] = action
    try:
        try:
            ipType = str(request.GET.get('ipType'))
        except:
            ipType = None
        formValues['ipType'] = ipType
        clusterObj = Cluster.objects.get(id=clusterId)
        if clusterObj.group != None:
            if not dmt.utils.permissionRequest(request.user, clusterObj):
               error = "You do not have permission to Update Hybrid Cloud Information for Deployment: " +str(clusterObj.name)
               return render_to_response("dmt/dmt_error.html", {'error': error})
        if action == "edit":
            editValues, oldValues = dmt.utils.getHybridCloudValues(clusterObj, ipType)
        if request.method == 'POST':
            try:
                ipType = str(request.POST.get('ipType'))
            except:
                ipType = None
            formValues['ipType'] = ipType
            if request.POST['form-type'] == "ipv4-form":
                form = HybridCloudIPv4Form(request.POST)
            else:
                form = HybridCloudIPv6Form(request.POST)
            if form.is_valid():
                if ipType == "ipv4":
                    hybridCloudValues['internalSubnet'] = str(form.cleaned_data['internal_subnet'])
                    hybridCloudValues['gatewayInternal'] = str(form.cleaned_data['gatewayInternal'])
                    hybridCloudValues['gatewayExternal'] = str(form.cleaned_data['gatewayExternal'])
                    values = {'internal_subnet': str(hybridCloudValues['internalSubnet']),
                             'gatewayInternal': str(hybridCloudValues['gatewayInternal']),
                             'gatewayExternal': str(hybridCloudValues['gatewayExternal']),
                             'internal_subnet_ipv6': str(),
                             'gatewayInternalIPv6': str(),
                             'gatewayExternalIPv6': str()
                            }
                    formValues['ipv4_form'] = HybridCloudIPv4Form(initial=values)
                    if action == "add":
                        formValues['ipv6_form'] = HybridCloudIPv6Form()
                    else:
                        HybridCloudIPv6Form(initial=editValues)
                else:
                    hybridCloudValues['internalSubnetIPv6'] = str(form.cleaned_data['internal_subnet_ipv6'])
                    hybridCloudValues['gatewayInternalIPv6'] = str(form.cleaned_data['gatewayInternalIPv6'])
                    hybridCloudValues['gatewayExternalIPv6'] = str(form.cleaned_data['gatewayExternalIPv6'])
                    values = {'internal_subnet_ipv6': str(hybridCloudValues['internalSubnetIPv6']),
                              'gatewayInternalIPv6': str(hybridCloudValues['gatewayInternalIPv6']),
                              'gatewayExternalIPv6': str(hybridCloudValues['gatewayExternalIPv6']),
                              'internal_subnet': str(),
                              'gatewayInternal': str(),
                              'gatewayExternal': str()
                             }
                    if action == "add":
                        formValues['ipv4_form'] = HybridCloudIPv4Form()
                    else:
                        formValues['ipv4_form'] = HybridCloudIPv4Form(initial=editValues)
                    formValues['ipv6_form'] = HybridCloudIPv6Form(initial=values)
                try:
                    with transaction.atomic():
                        if action == "add":
                            returnedValue, message = dmt.utils.addHybridCloudValues(clusterObj, ipType, hybridCloudValues)
                        else:
                            returnedValue, message = dmt.utils.editHybridCloudValues(clusterObj, ipType, hybridCloudValues)
                        if returnedValue == "1":
                            message = "Error: " + str(message)
                            logger.error(message)
                            formValues['error'] = str(message)
                            return render_to_response('dmt/hybridCloudForm.html', formValues, context_instance=RequestContext(request))
                except IntegrityError as e:
                    message = "Error: " + str(message)
                    logger.error(message)
                    formValues['error'] = str(message)
                    return render_to_response('dmt/hybridCloudForm.html', formValues, context_instance=RequestContext(request))
            else:
                message = "Error: See Form"
                logger.error(message)
                formValues['error'] = str(message)
                if ipType == "ipv4":
                    formValues['ipv4_form'] = form
                    formValues['ipv6_form'] = HybridCloudIPv6Form(initial=editValues)
                else:
                    formValues['ipv4_form'] = HybridCloudIPv4Form(initial=editValues)
                    formValues['ipv6_form'] = form
                return render_to_response('dmt/hybridCloudForm.html', formValues, context_instance=RequestContext(request))
            if action == "edit":
                if ipType == "ipv4":
                    newValues = [str(ipType), str(hybridCloudValues['internalSubnet']), str(hybridCloudValues['gatewayInternal']), str(hybridCloudValues['gatewayExternal']),
                            str(editValues['internal_subnet_ipv6']), str(editValues['gatewayInternalIPv6']), str(editValues['gatewayExternalIPv6'])]
                else:
                    newValues = [str(ipType), str(editValues['internal_subnet']), str(editValues['gatewayInternal']), str(editValues['gatewayExternal']),
                            str(hybridCloudValues['internalSubnetIPv6']), str(hybridCloudValues['gatewayInternalIPv6']), str(hybridCloudValues['gatewayExternalIPv6'])]
                changedContent = logChange(oldValues,newValues)
                message = "Edited Hybrid Cloud Information: " + str(changedContent)
            else:
                message = "Added Hybrid Cloud Information: IP Version - "  + str(ipType)
            logAction(userId, clusterObj, action, message)
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        else:
            if action == "edit":
                formValues['ipv4_form'] = HybridCloudIPv4Form(initial=editValues)
                formValues['ipv6_form'] = HybridCloudIPv6Form(initial=editValues)
            elif action == "delete":
                try:
                    HybridCloud.objects.get(cluster=clusterObj).delete()
                    IpAddress.objects.filter(ipType="hybridCloud_" + str(clusterObj.id)).delete()
                    logAction(userId, clusterObj, action, "Deleted Hybrid Cloud Information")
                    return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
                except Exception as e:
                    message = "Failed to Delete Hybrid Cloud Information for Deployment : " + str(clusterObj) + ". Exception : " + str(e)
                    logger.error(message)
                    return render_to_response("dmt/dmt_error.html", {'error': message})
            else:
                formValues['ipv4_form'] = HybridCloudIPv4Form()
                formValues['ipv6_form'] = HybridCloudIPv6Form()
            return render_to_response('dmt/hybridCloudForm.html', formValues, context_instance=RequestContext(request))
    except Exception as e:
        message = "Failed to Get Hybrid Cloud Form for Deployment. Exception : " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})

@login_required
@transaction.atomic
def vlanClusterMulticast(request,clusterId,action):
    '''
    form data for vlanClusterMulticast
    '''
    userId = request.user.pk
    clusterObj = vlanClusterMulticastObj = None
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "Failed to get Deployment Server. Exception: " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    oldValues = []
    newValues = []
    message = None

    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to Update VLAN Multicast for Deployment: " +str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    typesOptions = VlanMulticastType.objects.all()
    hashMaxOptions = str(config.get("DMT", "hashMax")).split()

    if request.method == 'POST':
        snooping= str(request.POST.get('multicast_snooping'))
        querier = str(request.POST.get('multicast_querier'))
        router = str(request.POST.get('multicast_router'))
        hashMax = str(request.POST.get('hash_max'))
        if action == "add":
            try:
                typeName = str(request.POST.get('multicast_type'))
                multicastType = VlanMulticastType.objects.get(name=typeName)
                try:
                    with transaction.atomic():
                        vlanClusterMulticastObj = VlanClusterMulticast.objects.create(cluster=clusterObj, multicast_type=multicastType, multicast_snooping=snooping, multicast_querier=querier, multicast_router=router, hash_max=hashMax)
                except IntegrityError as e:
                    message = "Failed to Save VLAN Multicast to Deployment: " + str(clusterObj.name) + ". Exception : " + str(e)
            except Exception as e:
                message = "Failed to add VLAN Multicast to Deployment: " + str(clusterObj.name) + ". Exception : " + str(e)
            if message:
                logger.error(message)
                return render(request, "dmt/vlanClusterMulticastForm.html",{
                    "message": message,
                    "action": action,
                    "typesOptions": typesOptions,
                    "hashMaxOptions": hashMaxOptions,
                    "clusterId" : clusterId,
                    })
        elif action == "edit":
            try:
                typeName = str(request.GET.get('multicast_type'))
                vlanClusterMulticastObj = VlanClusterMulticast.objects.get(cluster=clusterObj, multicast_type__name=typeName)
            except Exception as e:
                message = "Failed to Update VLAN Multicast to Deployment: " + str(clusterObj.name) + ". Exception : " + str(e)
                logger.error(message)
                return render_to_response("dmt/dmt_error.html", {'error': message})
            oldValues = [str(vlanClusterMulticastObj.multicast_type.name) + "##Type",
                         str(vlanClusterMulticastObj.multicast_snooping) + "##Multicast Snooping",
                         str(vlanClusterMulticastObj.multicast_querier) + "##Multicast Querier",
                         str(vlanClusterMulticastObj.multicast_router) + "##Multicast Router",
                         str(vlanClusterMulticastObj.hash_max) + "##Hash Max"]
            vlanClusterMulticastObj.multicast_snooping = snooping
            vlanClusterMulticastObj.multicast_querier = querier
            vlanClusterMulticastObj.multicast_router = router
            vlanClusterMulticastObj.hash_max = hashMax
            try:
                with transaction.atomic():
                    vlanClusterMulticastObj.save()
            except IntegrityError as e:
                message = "Failed to Update VLAN Multicast to Deployment: " + str(clusterObj.name) + ". Exception : " + str(e)
                logger.error(message)
                return render(request, "dmt/vlanClusterMulticastForm.html",{
                    "message": message,
                    "vlanMulticastObj": vlanClusterMulticastObj,
                    "action": action,
                    "typesOptions": typesOptions,
                    "hashMaxOptions": hashMaxOptions,
                    "clusterId" : clusterId,
                    "multicast_type": typeName,
                   })

        newValues = [str(vlanClusterMulticastObj.multicast_type.name), str(vlanClusterMulticastObj.multicast_snooping), str(vlanClusterMulticastObj.multicast_querier),
                     str(vlanClusterMulticastObj.multicast_router), str(vlanClusterMulticastObj.hash_max)]
        if action == "edit":
            changedContent = logChange(oldValues,newValues)
            message = "Edited VLAN Cluster Multicast Information: " + str(vlanClusterMulticastObj.multicast_type.name) + " - " + str(vlanClusterMulticastObj.multicast_type.description) + ": " + str(changedContent)
        elif action == "add":
            message = "Added VLAN Cluster Multicast Information: " + str(vlanClusterMulticastObj.multicast_type.name) + " - " + str(vlanClusterMulticastObj.multicast_type.description)
        logAction(userId, clusterObj, action, message)
        return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
    else:
        if action == "add":
            return render(request, "dmt/vlanClusterMulticastForm.html",{
                        "action": action,
                        "typesOptions": typesOptions,
                        "hashMaxOptions": hashMaxOptions,
                        "clusterId" : clusterId,
                      }
                   )
        elif action == "delete":
            if VlanClusterMulticast.objects.filter(cluster=clusterObj).exists():
                try:
                    VlanClusterMulticast.objects.filter(cluster=clusterObj).delete()
                    logAction(userId, clusterObj, action, "Deleted VLAN Cluster Multicast Details")
                    return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
                except Exception as e:
                    message = "Failed to delete VLAN Cluster Multicast for Deployment " + str(clusterObj.name) + "with Exception: " + str(e)
                    logger.error(message)
                    return render_to_response("dmt/dmt_error.html", {'error': message})

        else:
            try:
                typeName = str(request.GET.get('multicast_type'))
                vlanClusterMulticastObj = VlanClusterMulticast.objects.get(cluster=clusterObj, multicast_type__name=typeName)
            except Exception as e:
                message = "Failed to Get VLAN Multicast Information for Deployment: " + str(clusterObj.name) + ". Exception : " + str(e)
                logger.error(message)
                return render_to_response("dmt/dmt_error.html", {'error': message})
            return render(request, "dmt/vlanClusterMulticastForm.html",
                      {
                          "vlanClusterMulticastObj": vlanClusterMulticastObj,
                          "action": action,
                          "type": typeName,
                          "typesOptions": typesOptions,
                          "hashMaxOptions": hashMaxOptions,
                          "clusterId" : clusterId,
                          "multicast_type": typeName,
                      }
                    )

def deploymentDescriptionDeploymentMapping(request, clusterId, action):
    '''
    Deployment Description to Deployment Mapping function
    '''
    ddMapping = {}
    clusterObj = None
    message = None
    userId = request.user.pk
    allVersions = [item.version for item in DeploymentDescriptionVersion.objects.all()]
    allVersions.sort(key=LooseVersion)
    allVersions.reverse()
    latestVersion = None
    try:
        latestVersion = DeploymentDescriptionVersion.objects.get(latest=True).version
    except Exception as e:
        message = "Issue getting Latest Deployment Description Version: " + str(e)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    allDDtypes = DeploymentDescriptionType.objects.all()
    formValues = {}
    formValues["message"] = message
    formValues["clusterId"] = clusterId
    formValues["action"] = action
    formValues["allDDtypes"] = allDDtypes
    formValues["allVersions"] = allVersions
    formValues["latestVersion"] = latestVersion
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
    except Exception as e:
        message = "Issue getting Deployment: " + str(e)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            error = "You do not have permission to alter Deployment Description Mapping for Deployment: " +str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': error})
    if action == "edit":
        try:
            ddMappingFields = ('deployment_description__name', 'deployment_description__version__version', 'deployment_description__dd_type__dd_type', 'deployment_description__capacity_type', 'auto_update', 'update_type', 'iprange_type')
            ddMapping = DDtoDeploymentMapping.objects.only(ddMappingFields).values(*ddMappingFields).get(cluster=clusterObj)
            formValues["ddMapping"] = ddMapping
            oldValues = [str(ddMapping['deployment_description__name']) + "##Deployment Description",str(ddMapping['deployment_description__version__version']) + "##Version",
                         str(ddMapping['deployment_description__dd_type__dd_type']) + "##DD Type",   str(ddMapping['deployment_description__capacity_type']) + "##Capacity Type",
                         str(ddMapping['auto_update']) + "##Auto Update", str(ddMapping['update_type']) + "##Update Type", str(ddMapping['iprange_type']) + "##IpRange Type"]
        except Exception as e:
            message = "Issue getting Deployment Description: " + str(e)
            return render_to_response("dmt/dmt_error.html", {'error': message})
    if request.method == 'POST':
        try:
            updateNow = bool(int(request.POST.get('updateNow')))
            deploymentDescription = str(request.POST.get('deploymentDescription'))
            version = str(request.POST.get('version'))
            ddType = str(request.POST.get('ddType'))
            capacityType = str(request.POST.get('capacityType'))
            autoUpdate = str(request.POST.get('autoUpdate'))
            updateType = str(request.POST.get('updateType'))
            ipRangeType = str(request.POST.get('ipRangeType'))
            ddMapping['deployment_description__name'] = deploymentDescription
            ddMapping['deployment_description__version__version'] = version
            ddMapping['deployment_description__dd_type__dd_type'] = ddType
            ddMapping['deployment_description__capacity_type'] = capacityType
            if str(autoUpdate) == "None":
                autoUpdate = False
            else:
                autoUpdate = True
            ddMapping['auto_update'] = autoUpdate
            ddMapping['update_type'] = updateType
            ddMapping['iprange_type'] = ipRangeType
            formValues["ddMapping"] = ddMapping
            if str(updateType) == "None":
                message = "Update Type Required, please choose a Update Type"
                formValues["message"] = message
                return render(request, "dmt/ddToDeploymentMappingForm.html", formValues)
            ddTypeObj = DeploymentDescriptionType.objects.get(dd_type=ddType)
            ddVersionObj = DeploymentDescriptionVersion.objects.get(version=version)
            deploymentDescriptionObj = DeploymentDescription.objects.get(name=deploymentDescription, dd_type=ddTypeObj, version=ddVersionObj)
            if ipRangeType == "dns":
                if not AutoVmServiceDnsIpRange.objects.filter(cluster=clusterObj).exists():
                    message = "This Deployment doesn't have Dns Ip Range Source, select Manual Ip Range Source if exists"
                    formValues["message"] = message
                    return render(request, "dmt/ddToDeploymentMappingForm.html", formValues)
            else:
                if not VmServiceIpRange.objects.filter(cluster=clusterObj).exists():
                    message = "This Deployment doesn't have Manual Ip Range Source"
                    formValues["message"] = message
                    return render(request, "dmt/ddToDeploymentMappingForm.html", formValues)
            try:
                with transaction.atomic():
                    ddMapping, created = DDtoDeploymentMapping.objects.get_or_create(cluster=clusterObj)
                    ddMapping.deployment_description=deploymentDescriptionObj
                    if dmt.utils.checkIncludeCompactAuditLogger(clusterId, deploymentDescriptionObj.name):
                        if clusterObj.compact_audit_logger is None:
                            clusterObj.compact_audit_logger = True
                    else:
                        clusterObj.compact_audit_logger = None
                    clusterObj.save()
                    ddMapping.auto_update = autoUpdate
                    ddMapping.update_type = updateType
                    ddMapping.iprange_type = ipRangeType
                    ddMapping.save()
            except IntegrityError as e:
                message = "Failed to "+ str(action) + " Deployment Description To Deployment Mapping: " + str(clusterObj.name) + ". Exception : " + str(e)
                logger.error(message)
                return render(request, "dmt/ddToDeploymentMappingForm.html",formValues)
            newValues = [str(ddMapping.deployment_description.name),str(ddMapping.deployment_description.version.version), str(ddMapping.deployment_description.dd_type.dd_type), str(ddMapping.deployment_description.capacity_type), str(ddMapping.auto_update), str(ddMapping.update_type), str(ddMapping.iprange_type)]
            if action == "edit":
                changedContent = logChange(oldValues,newValues)
                message = "Edited Deployment Description Mapping: " + str(changedContent)
            else:
                message = "Added Deployment Description Mapping: " + str(ddMapping)
            logAction(userId, clusterObj, action, message)
            if updateNow:
                dmt.utils.updateClustersServicesWithDD(clusterId)
                return HttpResponseRedirect("/dmt/deploymentUpdatedReport/"+clusterId+"/")
            else:
                return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        except Exception as e:
            message = "Issue getting saving: " + str(e)
            return render_to_response("dmt/dmt_error.html", {'error': message})
    if action == "add":
        return render(request, "dmt/ddToDeploymentMappingForm.html",formValues)
    elif action == "edit":
        return render(request, "dmt/ddToDeploymentMappingForm.html",formValues)
    else:
        try:
            DDtoDeploymentMapping.objects.get(cluster=clusterObj).delete()
            clusterObj.compact_audit_logger = None
            clusterObj.save()
            logAction(userId, clusterObj, action, "Deleted Deployment Description Mapping")
            return HttpResponseRedirect("/dmt/clusters/" + str(clusterId) + "/details/")
        except Exception as e:
            message = "Failed to Delete Deployment Description for Deployment : " + str(clusterObj) + ". Exception : " + str(e)
            logger.error(message)
            return render_to_response("dmt/dmt_error.html", {'error': message})

@gzip_page
def deploymentsUpdatedSummaryReports(request):
    '''
    Summary Reports Index
    '''
    try:
        fields = "id", "createdDate", "dd_version__version"
        reports = UpdatedDeploymentSummaryLog.objects.only(fields).values(*fields).all().order_by('-createdDate')
        if len(reports) > 30:
            reports = reports[:30]
    except Exception as e:
        message = "Issue getting Summary Reports for Deployments Updated: " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    return render(request, "dmt/summaryReport_index.html",  {'summaryReports': reports} )

@gzip_page
def deploymentsUpdatedReport(request, reportId):
    '''
    Displaying the Report for the Deployments that were updated with new DD version
    '''
    reportObj = None
    try:
        fields = "createdDate", "dd_version__version"
        reportObj = UpdatedDeploymentSummaryLog.objects.only(fields).values(*fields).get(id=reportId)
    except Exception as e:
        message = "Issue getting Summary Report for Deployments Updated: " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    try:
        fields = "createdDate", "cluster__name", "cluster__id", "log", "status", "deployment_description__name"
        deploymentsReportObj = UpdatedDeploymentLog.objects.only(fields).values(*fields).filter(summary_log__id=reportId)
    except Exception as e:
        message = "Issue getting the List Deployments Updated Report: " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    return render(request, "dmt/summaryReport.html",  {'report': reportObj, 'deploymentsReport': deploymentsReportObj} )

@gzip_page
def deploymentUpdatedReport(request, clusterId):
    '''
    Displaying the Reports for the Deployment that Updated
    '''
    clusterName = None
    try:
        clusterName = Cluster.objects.get(id=clusterId).name
    except Exception as e:
        message = "Issue getting Deployment: " + str(e)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    try:
        fields = "createdDate", "log", "status", "deployment_description__version__version", "deployment_description__name"
        deploymentsReportObj = UpdatedDeploymentLog.objects.only(fields).values(*fields).filter(cluster__id=clusterId).order_by('-createdDate')
        if len(deploymentsReportObj) > 30:
            deploymentsReportObj = deploymentsReportObj[:30]
    except Exception as e:
        message = "Issue getting the List Deployment's Reports: " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    return render(request, "dmt/updatedDeploymentReport.html",  {'clusterId':clusterId, 'clusterName': clusterName, 'deploymentReport': deploymentsReportObj} )

@csrf_exempt
def deploymentArtifactsInstalledAudit(request):
    '''
    For checking the artifacts that have install based on the ENM Version file
    '''

    fh = FormHandle()
    fh.form = UploadDeploymentFileForm()
    fh.title = "Deployment: Artifacts Installed Audit"
    fh.subTitle = "Upload ENM Version file for auditing. This will check what Artifacts are installed and not installed from the ENM ISO version used for the Deployment Installation."
    fh.request = request
    fh.button = "Upload File & Download Audit Report"
    fh.docLink = "/display/CIOSS/Deployment+Version+Artifacts+Installed+Audit"

    if request.method == 'POST':
        form = UploadDeploymentFileForm(request.POST, request.FILES)
        if form.is_valid():
            fileNameLocation = ""
            try:
                fileName = str(request.FILES['file'].name)
                location = '/tmp'
                handle_uploaded_file(request.FILES['file'], fileName, location)
                fileNameLocation = '/tmp/' + fileName
                mediaArtifact, deploymentArtifacts, deploymentArtifactsSize, notFoundArtifacts, notFoundArtifactsSize = dmt.utils.deploymentArtifactInstalled(fileNameLocation)
                if mediaArtifact == 1:
                    logger.error(deploymentArtifacts)
                    return render_to_response("dmt/dmt_error.html", {'error': deploymentArtifacts})
                response = HttpResponse(content_type='text/csv')
                versionFileName = str(fileName).replace(".txt", "")
                response['Content-Disposition'] = 'attachment; filename=' + str(versionFileName) + '_ENM_ISO_Version_' + str(mediaArtifact) + '_artifacts_audit_report.csv'
                csvFile = csv.writer(response)
                deploymentArtifactsSize = "Total Size (Bytes): " + str(deploymentArtifactsSize)
                notFoundArtifactsSize = "Total Size (Bytes):  " + str(notFoundArtifactsSize)
                deploymentFileArtifact = str(versionFileName) + ": Artifacts Found (" + str(len(deploymentArtifacts)) + ")"
                mediaArtifactTitle = "ENM ISO Version " + str(mediaArtifact) + ": Artifacts Not Found (" + str(len(notFoundArtifacts)) + ")"
                csvFile.writerow([deploymentFileArtifact, deploymentArtifactsSize, "CNA Responsible Line Manager", "CNA Responsible", mediaArtifactTitle, notFoundArtifactsSize, "CNA Responsible Line Manager", "CNA Responsible"])
                for deploymentArtifactInfo, notFoundArtifactInfo in map(None,deploymentArtifacts, notFoundArtifacts):
                    (deploymentArtifact, sizeV1, respLineMang1, cnaResp1) = str(deploymentArtifactInfo).split("##")
                    notFoundArtifact = sizeV2 = respLineMang2 = cnaResp2 = None
                    if notFoundArtifactInfo:
                        (notFoundArtifact, sizeV2, respLineMang2, cnaResp2) = str(notFoundArtifactInfo).split("##")
                    csvFile.writerow([deploymentArtifact, sizeV1, respLineMang1, cnaResp1, notFoundArtifact, sizeV2, respLineMang2, cnaResp2])
                return response
            except Exception as e:
                os.system("rm " + fileNameLocation)
                message = "Failed to get information on Artifacts in the Deployment version file. Exception : " + str(e)
                logger.error(message)
                return render_to_response("dmt/dmt_error.html", {'error': message})
        else:
            return fh.failure()
    return fh.display()


@login_required
@transaction.atomic
def deploymentDatabaseProvider(request, clusterId):
    '''
    For Editing Deployment's Database Provider
    '''
    userId = request.user.pk
    clusterObj = deploymentDatabaseProviderObj = None
    try:
        clusterObj = Cluster.objects.get(id=clusterId)
        deploymentDatabaseProviderObj = DeploymentDatabaseProvider.objects.get(cluster=clusterObj)
    except Exception as e:
        message = "Failed to get Deployment information. Exception: " + str(e)
        logger.error(message)
        return render_to_response("dmt/dmt_error.html", {'error': message})
    oldValues = []
    newValues = []
    message = None
    if clusterObj.group != None:
        if not dmt.utils.permissionRequest(request.user, clusterObj):
            message = "You do not have permission to Update Database Provider for Deployment: " +str(clusterObj.name)
            return render_to_response("dmt/dmt_error.html", {'error': message})
    fh = FormHandle()
    fh.request = request
    fh.title = "Edit Deployment Database Provider"
    fh.button = "Save"
    fh.button2 = "Cancel"
    oldValues = ["DPS Persistence Provider##"+str(deploymentDatabaseProviderObj.dpsPersistenceProvider)]
    fh.form = DeploymentDatabaseProviderForm(initial={'dpsPersistenceProvider':str(deploymentDatabaseProviderObj.dpsPersistenceProvider)})
    if request.method == 'POST':
        fh.form = DeploymentDatabaseProviderForm(request.POST)
        fh.redirectTarget = "/dmt/clusters/" + str(clusterId) + "/details/"
        if "Cancel" in request.POST:
            return fh.success()
        if fh.form.is_valid():
            try:
                with transaction.atomic():
                    deploymentDatabaseProviderObj.dpsPersistenceProvider = str(fh.form.cleaned_data['dpsPersistenceProvider'])
                    deploymentDatabaseProviderObj.save()
                    newValues = [str(fh.form.cleaned_data['dpsPersistenceProvider'])]
            except IntegrityError as e:
                message = "Failed to Update Deployment's Database Provider: " + str(clusterObj.server.hostname) + ". Exception : " + str(e)
                logger.error(message)
                return render_to_response("dmt/dmt_error.html", {'error': message})
            changedContent = logChange(oldValues,newValues)
            message = "Edited Database Provider: " + str(changedContent)
            logAction(userId, clusterObj, "edit", message)
            return fh.success()
        else:
            return fh.failure()
    return fh.display()
