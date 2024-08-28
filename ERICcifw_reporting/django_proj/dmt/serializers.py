from rest_framework import serializers

from .models import *

class DeploymentBaselineSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeploymentBaseline
        fields = ('id','clusterName','clusterID','osDetails', 'litpVersion','mediaArtifact', 'fromISO', 'fromISODrop', 'patches','dropName','groupName','sedVersion','deploymentTemplates','tafVersion','masterBaseline','descriptionDetails','updatedAt','createdAt','success','upgradePerformancePercent','productset_id', 'deliveryGroup', 'status','rfaStagingResult', 'rfaResult', 'teAllureLogUrl', 'upgradeAvailabilityResult', 'availability', 'buildURL', 'upgradeTestingStatus', 'rfaPercent', 'shortLoopURL', 'installType', 'deploytime', 'comment', 'slot')
class DeploymentToInstallSerializer(serializers.ModelSerializer):
    clusterName = serializers.ReadOnlyField(source='cluster.name')
    groupName = serializers.ReadOnlyField(source='group.installGroup')

    class Meta:
        model = ClusterToInstallGroupMapping
        fields = ('clusterName','groupName')

class MapTestResultsToDeploymentSerializer(serializers.ModelSerializer):
    clusterName = serializers.ReadOnlyField(source='cluster.name')
    parentElementName = serializers.StringRelatedField(source='cluster.component')

    class Meta:
        model = MapTestResultsToDeployment
        fields = ('clusterName','parentElementName','testcase','testcase_description','result','testDate','testcaseOutput')

class DeploymentTestcaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeploymentTestcase
        fields = ('id','testcase_description','testcase','enabled')

        def create(self, validated_data):
            return DeploymentTestcase.objects.create(**validated_data)

class TestGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestGroup
        fields = ('testGroup','defaultGroup')

class MapTestGroupToDeploymentSerializer(serializers.ModelSerializer):
    cluster = serializers.SlugRelatedField(
            slug_field='name',
            queryset=Cluster.objects.all()
    )
    group = serializers.SlugRelatedField(
            slug_field='testGroup',
            queryset=TestGroup.objects.all()
    )
    class Meta:
        model = MapTestGroupToDeployment
        fields = ('cluster','group')

class ClusterSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Cluster
        fields = ('url','id','name',)

class IndividualClusterSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Cluster
        fields = ('url','id','name','description','tipc_address','dhcp_lifetime','mac_lowest','mac_highest',)

class GetServiceVMIpRangeItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VmServiceIpRangeItem
        fields = ('id','ipType','ipDescription',)

class GetServiceVMIpRangesSerializer(serializers.ModelSerializer):
    ipTypeName = serializers.ReadOnlyField(source='ipTypeId.ipType')
    class Meta:
        model = VmServiceIpRange
        fields = ('id','ipv4AddressStart','ipv4AddressEnd','ipv6AddressStart','ipv6AddressEnd','ipTypeId','ipTypeName')

class GetServiceVMDnsIpRangesSerializer(serializers.ModelSerializer):
    ipTypeName = serializers.ReadOnlyField(source='ipTypeId.ipType')
    class Meta:
        model = AutoVmServiceDnsIpRange
        fields = ('id','ipv4AddressStart','ipv4AddressEnd','ipv6AddressStart','ipv6AddressEnd','ipTypeId','ipTypeName')

class GetDMTIpAddressesSerializer(serializers.ModelSerializer):
    class Meta:
        model = IpAddress
        fields = ('address', 'ipv4UniqueIdentifier', 'bitmask', 'ipv6_address', 'ipv6UniqueIdentifier', 'ipv6_bitmask', 'ipv6_gateway', 'gateway_address', 'interface', 'netmask', 'nic', 'ipType', 'override')


class VirtualImageCredentialMappingSerializer(serializers.ModelSerializer):

    credentialsUserName = serializers.ReadOnlyField(source='credentials.username')
    credentialsUserPassword = serializers.ReadOnlyField(source='credentials.password')
    credentialsType = serializers.ReadOnlyField(source='credentials.credentialType')
    credentialsLoginScope = serializers.ReadOnlyField(source='credentials.loginScope')
    class Meta:
        model = VirtualImageCredentialMapping
        fields = ('signum','date_time','credentialsUserName','credentialsUserPassword','credentialsType','credentialsLoginScope',)

class VirtualImageInfoSerializer(serializers.ModelSerializer):
    ipv4Address = serializers.ReadOnlyField(source='ipMap.address')
    ipv6Address = serializers.ReadOnlyField(source='ipMap.ipv6_address')
    ipType = serializers.ReadOnlyField(source='ipMap.ipType')
    class Meta:
        model = VirtualImageInfoIp
        fields = ('number', 'hostname', 'ipv4Address','ipv6Address','ipType',)

class GetDeploymentDetailsForVirtualImageData(serializers.ModelSerializer):
    virtualImageInfoIp = VirtualImageInfoSerializer(many=True, read_only=True)
    virtualImageCredentialMappingToVirtualImage = VirtualImageCredentialMappingSerializer(many=True, read_only=True)
    clusterName = serializers.ReadOnlyField(source='cluster.name')
    class Meta:
        model = VirtualImage 
        fields = ('id','name','node_list','clusterName','virtualImageInfoIp','virtualImageCredentialMappingToVirtualImage',)

