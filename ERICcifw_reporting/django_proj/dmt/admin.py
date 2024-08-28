from dmt.models import *
from django.contrib import admin
from django.contrib.admin.models import LogEntry

import logging
logger = logging.getLogger(__name__)

class ServerAdmin(admin.ModelAdmin):
    '''
    Admin View of the Server Model
    '''
    list_display = ('hostname', 'name', 'hardware_type')
    list_filter = ['hardware_type']
    search_fields = ['hostname', 'hardware_type', 'name']

class IpAddressAdmin(admin.ModelAdmin):
    '''
    Admin View of the IpAddress Model
    '''
    list_display = ('address', 'ipv4UniqueIdentifier', 'ipv6_address', 'ipv6UniqueIdentifier', 'ipType', 'nic')
    search_fields = ['address', 'ipv6_address', 'nic__mac_address', 'ipv4UniqueIdentifier', 'ipv6UniqueIdentifier', 'ipType']

class LogAdmin(admin.ModelAdmin):
    '''
    Admin View of the history/log table
    '''
    list_display = ('action_time','user','content_type','change_message','is_addition','is_change','is_deletion')
    #We don't want people changing this historical record:
    readonly_fields = [ 'user','content_type','object_id','object_repr','action_flag','change_message']
    list_filter = ['action_time','user','content_type']
    search_fields = ['action_time','user','content_type']
    ordering = ('-action_time',)
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        #returning false causes table to not show up in admin page :-(
        return True
    def has_delete_permission(self, request, obj=None):
        return False

class VlanDetailsAdmin(admin.ModelAdmin):
    '''
    Admin View of the VlanDetails Model
    '''
    search_fields = ['cluster__name']

class VlanMulticastTypeAdmin (admin.ModelAdmin):
    '''
    Admin View of the VlanMulticastType Model
    '''
    list_display = ('name','description')

class VlanMulticastAdmin (admin.ModelAdmin):
    '''
    Admin View of the VlanMulticast Model
    '''
    list_display = ('clusterServer', 'multicast_type')
    list_filter = ['multicast_type__name']
    search_fields = ['clusterServer__server__hostname','clusterServer__cluster__id']

class VirtualImageAdmin(admin.ModelAdmin):
    '''
    Admin View of the VirtualImage Model
    '''
    list_display = ('name', 'node_list', 'cluster')
    list_filter = ['name', 'node_list']
    search_fields = ['name', 'cluster__name']
    ordering = ('name',)


class VirtualImageItemAdmin(admin.ModelAdmin):
    '''
    Admin View of the VirtualImageItem Model
    '''
    list_display = ('name','type','layout','active')
    list_filter = ['active', 'type', 'layout']
    search_fields = ['name','type','layout']
    ordering = ('name',)

class VirtualImageInfoIpAdmin(admin.ModelAdmin):
    '''
    Admin View of the VirtualImageInfoIp Model
    '''
    list_display = ('number','hostname','virtual_image','ipMap')
    search_fields = ['ipMap__address', 'hostname']

class VirtualConnectNetworksAdmin(admin.ModelAdmin):
    '''
    Admin View of the VirtualConnectNetworks Model
    '''
    search_fields = ['vlanDetails__cluster__name']

class ManagementServerAdmin(admin.ModelAdmin):
    '''
    Admin View of the ManagementServer Model
    '''
    list_display = ('server', 'product')
    list_filter = ['product__name']
    search_fields = ['server__hostname', 'server__id', 'product__name']

class PackageRevisionServiceMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the PackageRevisionServiceMapping Model
    '''
    list_display = ('package_revision', 'service')
    search_fields = ['package_revision__package__name', 'service__name']

class MediaArtifactServiceScannedAdmin(admin.ModelAdmin):
    '''
    Admin View of the MediaArtifactServiceFlagAdmin Model
    '''
    list_display = ('media_artifact_version', 'scanned_date')

class ManagementServerCredentialMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ManagementServerCredentialMapping Model
    '''
    list_display = ('mgtServer', 'credentials', 'signum')
    list_filter = ['credentials__credentialType', 'credentials__username', 'signum']
    search_fields = ['mgtServer__server__hostname', 'signum', 'credentials__credentialType', 'credentials__username']

class ClusterAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cluster Model
    '''
    list_display = ('id', 'name', 'management_server', 'component', 'layout')
    list_filter = ['layout__name', 'component__element']
    search_fields = ['id', 'name', 'component__element', 'layout__name', 'management_server__server__hostname']

class ClusterServerAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterServer Model
    '''
    list_display = ('server', 'cluster', 'node_type', 'active')
    list_filter = ['node_type']
    search_fields = ['server__hostname', 'cluster__name', 'node_type']

class ClusterServerCredentialMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterServerCredentialMapping Model
    '''
    list_display = ('clusterServer', 'credentials', 'signum')
    list_filter = ['credentials__credentialType', 'credentials__username', 'signum']
    search_fields = ['clusterServer__server__hostname', 'signum', 'credentials__credentialType', 'credentials__username', 'clusterServer__cluster__name']

class DeploymentStatusAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeploymentStatus Model
    '''
    list_display = ('cluster', 'status')
    list_filter = ['status__status']
    search_fields = ['cluster__name', 'cluster__management_server__server__hostname', 'status__status']

class DeploymentBaselineAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeploymentBaseline Model
    '''
    list_display = ('clusterID', 'clusterName', 'sedVersion', 'mediaArtifact', 'success', 'masterBaseline')
    list_filter = ['success', 'masterBaseline']
    search_fields = ['clusterID', 'clusterName', 'sedVersion', 'mediaArtifact']

class ClusterToNASMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterToNASMapping Model
    '''
    list_display = ('cluster', 'nasServer')
    search_fields = ['cluster__name', 'nasServer__server__hostname']

class ClusterToDASNASMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterToDASNASMapping Model
    '''
    list_display = ('cluster', 'dasNasServer')
    search_fields = ['cluster__name', 'dasNasServer__hostname']

class InstallGroupAdmin(admin.ModelAdmin):
    '''
    Admin View of the InstallGroup Model
    '''
    search_fields = ['installGroup']

class ClusterToInstallGroupMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterToInstallGroupMapping Model
    '''
    list_display = ('cluster', 'group', 'status')
    list_filter = ['status__status__status']
    search_fields = ['cluster__name', 'group__installGroup', 'status__status__status']

class VeritasClusterAdmin(admin.ModelAdmin):
    '''
    Admin View of the VeritasCluster Model
    '''
    search_fields = ['cluster__name']

class MulticastAdmin(admin.ModelAdmin):
    '''
    Admin View of the Multicast Model
    '''
    search_fields = ['service_cluster__name', 'service_cluster__cluster__name']

class NasStorageDetailsAdmin(admin.ModelAdmin):
    '''
    Admin View of the NasStorageDetails Model
    '''
    search_fields = ['cluster__name']

class ServicesClusterAdmin(admin.ModelAdmin):
    '''
    Admin View of the ServicesCluster Model
    '''
    list_display = ('name', 'cluster', 'cluster_type')
    list_filter = ['cluster_type']
    search_fields = ['cluster__name', 'name', 'cluster_type']

class ServiceGroupAdmin(admin.ModelAdmin):
    '''
    Admin View of the ServiceGroup Model
    '''
    list_display = ('name', 'service_cluster', 'cluster_type')
    list_filter = ['cluster_type']
    search_fields = ['name', 'service_cluster__name', 'service_cluster__cluster__name', 'cluster_type']

class ServiceGroupInstanceAdmin(admin.ModelAdmin):
    '''
    Admin View of the ServiceGroupInstance Model
    '''
    list_display = ('name', 'hostname', 'service_group', 'ipMap')
    search_fields = ['name', 'service_group__service_cluster__name', 'service_group__service_cluster__cluster__name', 'ipMap__address']

class ServiceGroupPackageMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ServiceGroupPackageMapping Model
    '''
    list_display = ('serviceGroup', 'package')
    search_fields = ['serviceGroup__service_cluster__name', 'serviceGroup__service_cluster__cluster__name', 'package__name']

class ServiceGroupUnitAdmin(admin.ModelAdmin):
    '''
    Admin View of the ServiceGroupUnit Model
    '''
    list_display = ('service_unit', 'group_type')
    search_fields = ['service_unit', 'group_type__group_type']

class IloAdmin(admin.ModelAdmin):
    '''
    Admin View of the Ilo Model
    '''
    list_display = ('ipMapIloAddress', 'server')
    search_fields = ['ipMapIloAddress__address', 'server__hostname']

class TestGroupAdmin(admin.ModelAdmin):
    '''
    Admin View of the TestGroup Model
    '''
    search_fields = ['testGroup']

class MapTestGroupToDeploymentAdmin(admin.ModelAdmin):
    '''
    Admin View of the MapTestGroupToDeployment Model
    '''
    list_display = ('group', 'cluster')
    search_fields = ['group__testGroup', 'cluster__name']

class MapTestResultsToDeploymentAdmin(admin.ModelAdmin):
    '''
    Admin View of the MapTestResultsToDeployment Model
    '''
    list_display = ('cluster', 'testcase', 'testDate', 'result')
    list_filter = ['result', 'testDate']
    search_fields = ['cluster__name']

class EnclosureAdmin(admin.ModelAdmin):
    '''
    Admin View of the Enclosure Model
    '''
    search_fields = ['hostname']

class NetworkInterfaceAdmin(admin.ModelAdmin):
    '''
    Admin View of the NetworkInterface Model
    '''
    list_display = ('mac_address', 'server', 'interface')
    list_filter = ['interface']
    search_fields = ['mac_address', 'server__hostname', 'interface']

class ProductToServerTypeMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductToServerTypeMapping Model
    '''
    list_display = ('product', 'serverType')
    list_filter = ['product__name', 'serverType']
    search_fields = ['product__name', 'serverType']

class SedAdmin(admin.ModelAdmin):
    '''
    Admin View of the Sed Model
    '''
    list_display = ('version', 'dateInserted', 'jiraNumber', 'linkText', 'iso', 'user')
    list_filter = ['dateInserted']
    search_fields = ['version', 'jiraNumber', 'iso__version', 'user', 'linkText']

class UserTypesAdmin(admin.ModelAdmin):
    '''
    Admin View of the UserTypes Model
    '''
    search_fields = ['name']

class DeploymentStatusTypesAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeploymentStatusTypes Model
    '''
    search_fields = ['status']

class ClusterLayoutAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterLayout Model
    '''
    list_display = ('name', 'description')
    search_fields = ['name']

class DeploymentTestcaseAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeploymentTestcase Model
    '''
    list_display = ('testcase_description', 'testcase', 'enabled')
    list_filter = ['enabled']
    search_fields = ['testcase_description']

class DeployPackageExemptionListAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeployPackageExemptionList Model
    '''
    search_fields = ['packageName']

class IpRangeItemAdmin(admin.ModelAdmin):
    '''
    Admin View of the IpRangeItem Model
    '''
    search_fields = ['ip_range_item']

class IpRangeAdmin(admin.ModelAdmin):
    '''
    Admin View of the IpRange Model
    '''
    list_display = ('ip_range_item', 'start_ip', 'end_ip', 'bitmask', 'gateway')
    search_fields = ['ip_range_item__ip_range_item', 'start_ip', 'end_ip', 'gateway']

class JbossClusterServiceGroupAdmin(admin.ModelAdmin):
    '''
    Admin View of the JbossClusterServiceGroup Model
    '''
    search_fields = ['name']

class ClusterQueueAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterQueue Model
    '''
    list_display = ('clusterGroup', 'dateInserted')
    list_filter = ['dateInserted']
    search_fields =['clusterGroup']

class RedHatArtifactToVersionMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the RedHatArtifactToVersionMapping Model
    '''
    list_display = ('mediaArtifact', 'artifactReference')
    search_fields = ['mediaArtifact__name', 'artifactReference']

class DeployScriptMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeployScriptMapping Model
    '''
    list_display = ('reference', 'version')
    search_fields = ['version']

class IpmiVersionMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the IpmiVersionMapping Model
    '''
    list_display = ('reference', 'version')
    search_fields = ['version']

class RedfishVersionMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the RedfishVersionMapping Model
    '''
    list_display = ('reference', 'version')
    search_fields = ['version']

class VmServiceIpRangeItemAdmin(admin.ModelAdmin):
    '''
    Admin View for the VmServiceIpRangeItem
    '''
    list_display = ('ipType', 'ipDescription')

class LVSRouterAdmin(admin.ModelAdmin):
    '''
    Admin View for the LVS Router Model
    '''
    search_fields = ['cluster__name', 'cluster__id']

class LVSRouterVipExtendedAdmin(admin.ModelAdmin):
    '''
    Admin View for the LVS Router Vip Extended Model
    '''
    search_fields = ['cluster__name', 'cluster__id']

class DeploymentUtilitiesAdmin(admin.ModelAdmin):
    '''
    Admin View for Deployment Utilities
    '''
    list_display = ('utility',)
    search_fields = ['utility']

class DeploymentUtilitiesVersionAdmin(admin.ModelAdmin):
    '''
    Admin View for Deployment Utility Versions
    '''
    list_display = ('utility_name','utility_version',)
    search_fields = ['utility_name','utility_version']

class DeploymentUtilsToISOBuildAdmin(admin.ModelAdmin):
    '''
    Admin View for Deployment Utilities to ISO Build Mapping
    '''
    list_display = ('utility_version','iso_build','active',)
    search_fields = ['utility_version','iso_build']

class DeploymentUtilsToProductSetVersionAdmin(admin.ModelAdmin):
    '''
    Admin View for Deployment Utilities to Product Set Version
    '''
    list_display = ('utility_version','productSetVersion','active',)
    search_fields = ['utility_version','productSetVersion']

class ConsolidatedToConstituentMapAdmin(admin.ModelAdmin):
    '''
    Admin view for map of Consolidated Service Group types to Constituent Service Groups types
    '''
    list_display = ('consolidated', 'constituent')
    search_fields = ['consolidated', 'constituent']

class DeploymentDhcpJumpServerDetailsAdmin(admin.ModelAdmin):
    '''
    Admin View for Deployment Dhcp and Jump Server Details
    '''
    list_display = ('server_type', 'server_user', 'server_password', 'ecn_ip', 'edn_ip', 'youlab_ip', 'gtec_edn_ip', 'gtec_youlab_ip')
    search_fields = ('server_type', 'server_user', 'server_password', 'ecn_ip', 'edn_ip', 'youlab_ip', 'gtec_edn_ip', 'gtec_youlab_ip')

class VmServiceNameAdmin(admin.ModelAdmin):
    '''
    For the Services Names
    '''
    list_display = ("name",)
    search_fields = ['name']

class VmServicePackageMappingAdmin(admin.ModelAdmin):
    '''
    For the Package to VM Service mapping
    '''
    list_display = ("package", "service", "active",)
    list_filter = ['active']
    search_fields = ['service__name', 'package__name']

class HybridCloudAdmin(admin.ModelAdmin):
    '''
    Admin for Hybrid Cloud
    '''
    list_display = ("cluster", "ip_type",)
    search_fields = ['cluster__name', 'cluster__id']

class DvmsInformationAdmin(admin.ModelAdmin):
    '''
    Admin for DVMS Information
    '''
    list_display = ("cluster", )
    search_fields = ['cluster__name', 'cluster__id']

class DeploymentDescriptionTypeAdmin(admin.ModelAdmin):
    '''
    Admin for Deployment Description Type
    '''
    list_display = ["dd_type"]
    search_fields = ['dd_type']

class DeploymentDescriptionVersionAdmin(admin.ModelAdmin):
    '''
    Admin for Deployment Description Version
    '''
    list_display = ("version", "latest")
    search_fields = ['version']

class DeploymentDescriptionAdmin(admin.ModelAdmin):
    '''
    Admin for Deployment Description
    '''
    list_display = ("name", "capacity_type", "version", "dd_type", "auto_deployment", "sed_deployment")
    list_filter = ['dd_type__dd_type', 'capacity_type']
    search_fields = ['version__version', "name", "auto_deployment", "sed_deployment"]

class DDtoDeploymentMappingAdmin(admin.ModelAdmin):
    '''
    Admin for Deployment Description to Cluster/Deployment Mapping
    '''
    list_display = ("cluster", "deployment_description", "auto_update", "update_type", "iprange_type")
    list_filter = ['auto_update', 'update_type']
    search_fields = ['cluster__id', "cluster__name"]


class VlanClusterMulticastAdmin (admin.ModelAdmin):
    '''
    Admin View of the VlanClusterMulticast Model
    '''
    list_display = ('cluster', 'multicast_type')
    list_filter = ['multicast_type__name']
    search_fields = ['clusterServer__name','cluster__id']

class UpdatedDeploymentSummaryLogAdmin(admin.ModelAdmin):
    '''
    Admin View of the UpdatedDeploymentSummaryLog Model
    '''
    list_display = ("id","createdDate", "dd_version")
    search_fields = ['id','dd_version__version']

class UpdatedDeploymentLogAdmin(admin.ModelAdmin):
    '''
    Admin View of the UpdatedDeploymentLog Model
    '''
    list_display = ("id","createdDate", "summary_log", "cluster", "deployment_description", "status")
    list_filter = ['status']
    search_fields = ['id','cluster__id', "cluster__name", "status"]

class VirtualAutoBuildlogClustersAdmin(admin.ModelAdmin):
    '''
    Admin View of the UpdatedDeploymentLog Model
    '''
    list_display = ("id","name")
    search_fields = ['name']

class BladeHardwareDetailsAdmin(admin.ModelAdmin):
    '''
    Admin View of the BladeHardwareDetails Model
    '''
    list_display = ("mac_address", "serial_number")
    search_fields = ['mac_address__mac_address', 'serial_number']

class ClusterAdditionalInformationAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cluster Additional Information Model
    '''
    list_display = ('cluster', 'ddp_hostname', 'cron', 'port')
    search_fields = ['cluster__id', 'cluster__name', 'ddp_hostname', 'cron', 'port']

class EnmDeploymentTypeAdmin(admin.ModelAdmin):
    '''
    Admin View of the EnmDeploymentType Model
    '''
    search_fields = ['name']

class IpVersionAdmin(admin.ModelAdmin):
    '''
    Admin View of the ipVersion Model
    '''
    search_fields = ['name']

class ClusterMulticastAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClusterMulticast Model
    '''
    list_display = ('enm_messaging_address', 'enm_messaging_port', 'udp_multicast_address', 'udp_multicast_port', 'cluster')
    search_fields = ['enm_messaging_address__address', 'udp_multicast_address__address', 'cluster__name']

class ItamWebhookEndpointAdmin(admin.ModelAdmin):
      '''
      Admin View of the ItamWebhookEndpoint Model
      '''
      search_fields = ['endpoint']

admin.site.register(LogEntry,LogAdmin)
admin.site.register(Server,ServerAdmin)
admin.site.register(ManagementServer, ManagementServerAdmin)
admin.site.register(UserTypes, UserTypesAdmin)
admin.site.register(DeploymentStatusTypes, DeploymentStatusTypesAdmin)
admin.site.register(Cluster,ClusterAdmin)
admin.site.register(ClusterLayout, ClusterLayoutAdmin)
admin.site.register(ClusterServer, ClusterServerAdmin)
admin.site.register(ClusterServerCredentialMapping, ClusterServerCredentialMappingAdmin)
admin.site.register(NetworkInterface, NetworkInterfaceAdmin)
admin.site.register(IpAddress,IpAddressAdmin)
admin.site.register(ServicesCluster, ServicesClusterAdmin)
admin.site.register(Multicast,MulticastAdmin)
admin.site.register(ServiceGroup, ServiceGroupAdmin)
admin.site.register(JbossClusterServiceGroup, JbossClusterServiceGroupAdmin)
admin.site.register(ServiceGroupUnit, ServiceGroupUnitAdmin)
admin.site.register(ServiceGroupPackageMapping, ServiceGroupPackageMappingAdmin)
admin.site.register(ServiceGroupInstance, ServiceGroupInstanceAdmin)
admin.site.register(VmServiceName, VmServiceNameAdmin)
admin.site.register(VmServicePackageMapping, VmServicePackageMappingAdmin)
admin.site.register(VeritasCluster, VeritasClusterAdmin)
admin.site.register(Ilo, IloAdmin)
admin.site.register(ClusterQueue, ClusterQueueAdmin)
admin.site.register(ProductToServerTypeMapping, ProductToServerTypeMappingAdmin)
admin.site.register(ClusterToNASMapping, ClusterToNASMappingAdmin)
admin.site.register(ClusterToDASNASMapping, ClusterToDASNASMappingAdmin)
admin.site.register(NasStorageDetails, NasStorageDetailsAdmin)
admin.site.register(ClusterToInstallGroupMapping, ClusterToInstallGroupMappingAdmin)
admin.site.register(InstallGroup, InstallGroupAdmin)
admin.site.register(IpRangeItem, IpRangeItemAdmin)
admin.site.register(IpRange, IpRangeAdmin)
admin.site.register(Sed, SedAdmin)
admin.site.register(VirtualImage, VirtualImageAdmin)
admin.site.register(VirtualImageInfoIp, VirtualImageInfoIpAdmin)
admin.site.register(VirtualImageItems,VirtualImageItemAdmin)
admin.site.register(VirtualConnectNetworks, VirtualConnectNetworksAdmin)
admin.site.register(VlanDetails, VlanDetailsAdmin)
admin.site.register(VlanMulticastType, VlanMulticastTypeAdmin)
admin.site.register(VlanMulticast, VlanMulticastAdmin)
admin.site.register(DeployPackageExemptionList, DeployPackageExemptionListAdmin)
admin.site.register(DeploymentStatus, DeploymentStatusAdmin)
admin.site.register(DeploymentBaseline, DeploymentBaselineAdmin)
admin.site.register(redHatArtifactToVersionMapping, RedHatArtifactToVersionMappingAdmin)
admin.site.register(DeployScriptMapping, DeployScriptMappingAdmin)
admin.site.register(IpmiVersionMapping, IpmiVersionMappingAdmin)
admin.site.register(RedfishVersionMapping, RedfishVersionMappingAdmin)
admin.site.register(DeploymentTestcase, DeploymentTestcaseAdmin)
admin.site.register(TestGroup, TestGroupAdmin)
admin.site.register(MapTestResultsToDeployment, MapTestResultsToDeploymentAdmin)
admin.site.register(MapTestGroupToDeployment, MapTestGroupToDeploymentAdmin)
admin.site.register(Enclosure, EnclosureAdmin)
admin.site.register(VmServiceIpRangeItem, VmServiceIpRangeItemAdmin)
admin.site.register(LVSRouterVip, LVSRouterAdmin)
admin.site.register(LVSRouterVipExtended, LVSRouterVipExtendedAdmin)
admin.site.register(DeploymentUtilities, DeploymentUtilitiesAdmin)
admin.site.register(DeploymentUtilitiesVersion, DeploymentUtilitiesVersionAdmin)
admin.site.register(DeploymentUtilsToISOBuild, DeploymentUtilsToISOBuildAdmin)
admin.site.register(DeploymentUtilsToProductSetVersion, DeploymentUtilsToProductSetVersionAdmin)
admin.site.register(ConsolidatedToConstituentMap, ConsolidatedToConstituentMapAdmin)
admin.site.register(DeploymentDhcpJumpServerDetails, DeploymentDhcpJumpServerDetailsAdmin)
admin.site.register(HybridCloud, HybridCloudAdmin)
admin.site.register(DvmsInformation ,DvmsInformationAdmin)
admin.site.register(DeploymentDescriptionType, DeploymentDescriptionTypeAdmin)
admin.site.register(DeploymentDescriptionVersion, DeploymentDescriptionVersionAdmin)
admin.site.register(DeploymentDescription, DeploymentDescriptionAdmin)
admin.site.register(DDtoDeploymentMapping, DDtoDeploymentMappingAdmin)
admin.site.register(VlanClusterMulticast, VlanClusterMulticastAdmin)
admin.site.register(UpdatedDeploymentSummaryLog, UpdatedDeploymentSummaryLogAdmin)
admin.site.register(UpdatedDeploymentLog, UpdatedDeploymentLogAdmin)
admin.site.register(VirtualAutoBuildlogClusters, VirtualAutoBuildlogClustersAdmin)
admin.site.register(RackHardwareDetails)
admin.site.register(PackageRevisionServiceMapping, PackageRevisionServiceMappingAdmin)
admin.site.register(MediaArtifactServiceScanned, MediaArtifactServiceScannedAdmin)
admin.site.register(BladeHardwareDetails, BladeHardwareDetailsAdmin)
admin.site.register(ClusterAdditionalInformation, ClusterAdditionalInformationAdmin)
admin.site.register(EnmDeploymentType, EnmDeploymentTypeAdmin)
admin.site.register(IpVersion, IpVersionAdmin)
admin.site.register(ClusterMulticast, ClusterMulticastAdmin)
admin.site.register(ItamWebhookEndpoint, ItamWebhookEndpointAdmin)
