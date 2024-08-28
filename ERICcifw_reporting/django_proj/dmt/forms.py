from dmt.models import *
from cireports.models import *
import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()

from django.forms.fields import DateField, ChoiceField, MultipleChoiceField
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple, TextInput
from django.forms.extras.widgets import SelectDateWidget


from fwk.forms import *

class ServerForm(forms.ModelForm):
    '''
    '''

    def __init__(self, *args, **kwargs):
        super(ServerForm, self).__init__(*args, **kwargs)
        self.fields['dns_serverA'].label = "DNS IP Address A"
        self.fields['dns_serverB'].label = "DNS IP Address B"
        self.fields['name'].label = "Machine Name"


    class Meta:
        fields =  ("name","hostname","domain_name","dns_serverA","dns_serverB","hardware_type")
        model = Server

class MgtServerForm(forms.ModelForm):
    class Meta:
        fields = ("description",)
        model = ManagementServer

class SsoDetailsForm(forms.ModelForm):
    ldapDomain = forms.CharField(label="LDAP Domain Component")
    ldapPassword = forms.CharField(label="LDAP Password")
    ossFsServer = forms.CharField(label="OSS ADMIN OSS-FS Server")
    citrixFarm = forms.CharField(label="OSS Citrix Farm Alias")
    brsadmPassword = forms.CharField(required=False, label="Brsadm Password")
    class Meta:
        fields = ("ldapDomain", "ldapPassword", "ossFsServer", "citrixFarm", "brsadmPassword", )
        model = SsoDetails

class SsoLdapDetailsForm(forms.ModelForm):
    ldapDomain = forms.CharField(label="LDAP Domain Component")
    ldapPassword = forms.CharField(label="LDAP Password")
    opendjAdminPassword = forms.CharField(label="Opendj Admin Password")
    openidmAdminPassword = forms.CharField(label="Openidm Admin Password")
    openidmMysqlPassword = forms.CharField(label="Openidm Mysql Password")
    securityAdminPassword = forms.CharField(label="Security Admin Password")
    hqDatabasePassword = forms.CharField(label="HQ Database Password")
    brsadmPassword = forms.CharField(required=False, label="Brsadm Password")
    class Meta:
        fields = ("ldapDomain", "ldapPassword", "opendjAdminPassword","openidmAdminPassword", "openidmMysqlPassword", "securityAdminPassword", "hqDatabasePassword", "brsadmPassword", )
        model = SsoDetails

class ClusterForm(forms.ModelForm):
    class Meta:
        fields = ("name", "description", "tipc_address", "management_server", "group", "layout", "enmDeploymentType", "ipVersion")
        model = Cluster
    def __init__(self, *args, **kwargs):
        super(ClusterForm, self).__init__(*args, **kwargs)
        self.fields["enmDeploymentType"] = forms.ModelChoiceField(queryset=EnmDeploymentType.objects.all(), required=False, label="ENM Deployment Type", help_text="Required for EDP")
        self.fields["ipVersion"] = forms.ModelChoiceField(queryset=IpVersion.objects.all(), required=False, label="IP Version", help_text="Required for EDP")
        self.fields["component"] = forms.ModelChoiceField(queryset=Component.objects.filter(label__name = "RA", deprecated=0), required=False, label="Select a RA")

class ClusterServerForm(forms.ModelForm):
    class Meta:
        fields = ("node_type", )
        model = ClusterServer

    def __init__(self, serverTypeList, *args, **kwargs):
        super(ClusterServerForm, self).__init__(*args, **kwargs)
        serverType = []
        serverType = serverType + [(serverTypeMapping.serverType, unicode(serverTypeMapping.serverType)) for serverTypeMapping in serverTypeList]
        self.fields['node_type'] = forms.CharField(widget=forms.Select(choices=serverType))

class ChangeClusterGroupOnClusterForm (forms.Form):
    group = forms.ModelChoiceField(queryset = Group.objects.all(), label="Select the New Group", required=False)

class ChangeClusterGroupForm (forms.Form):
    cluster = forms.ModelChoiceField(queryset = Cluster.objects.all(), label="Select a Cluster")
    group = forms.ModelChoiceField(queryset = Group.objects.all(), label="Select the New Group")

class ClusterMulticastForm(forms.ModelForm):
    enm_mes_address = forms.IPAddressField(label="IPV4 ENM Messaging Address")
    enm_mes_port = forms.CharField(label="ENM Messaging Port")
    udp_multi_address = forms.IPAddressField(label="IPv4 UDP Multicast Address")
    udp_multi_port = forms.CharField(label="UDP Multicast Port")
    class Meta:
        fields = ("enm_mes_address","enm_mes_port","udp_multi_address","udp_multi_port", )
        model = ClusterMulticast

class DatabaseVipForm(forms.ModelForm):
    postgresAddress = forms.IPAddressField(required=True,label="Postgres Service Ip Address",help_text="The VIP used by Applications to connect to the Postgres Service on the DB Cluster")
    versantAddress = forms.IPAddressField(required=True,label="Versant Service Ip Address",help_text="The VIP used by Applications to connect to the Versant Service on the DB Cluster")
    mysqlAddress = forms.IPAddressField(required=True,label="MySQL Service Ip Address",help_text="The VIP used by Applications to connect to the MySQL Service on the DB Cluster")
    opendjAddress = forms.IPAddressField(required=True,label="Opendj Service Ip Address 1",help_text="The VIP used by Applications to connect to the Opendj Service on the DB Cluster (HA)")
    opendjAddress2 = forms.IPAddressField(required=True,label="Opendj Service Ip Address 2",help_text="The VIP used by Applications to connect to the Opendj Service on the DB Cluster (HA)")
    jmsAddress = forms.IPAddressField(required=True,label="JMS Service Ip Address",help_text="The VIP used by Applications to connect to the JMS Service on the DB Cluster")
    eSearchAddress = forms.IPAddressField(required=True,label="Elastic Search Service Ip Address",help_text="The VIP used by Applications to connect to the elasticsearch Service on the DB Cluster")
    neo4jAddress1 = forms.IPAddressField(required=True,label="Neo4J Service Ip Address 1",help_text="The VIP1 used by Applications to connect to the NEO4J Service on the DB Cluster")
    neo4jAddress2 = forms.IPAddressField(required=True,label="Neo4J Service Ip Address 2",help_text="The VIP2 used by Applications to connect to the NEO4J Service on the DB Cluster")
    neo4jAddress3 = forms.IPAddressField(required=True,label="Neo4J Service Ip Address 3",help_text="The VIP3 used by Applications to connect to the NEO4J Service on the DB Cluster")
    gossipRouterAddress1  = forms.IPAddressField(required=True,label="Gossip Router Service Ip Address 1",help_text="The VIP1 used by Applications to connect to the gossiprouter Service on the DB Cluster")
    gossipRouterAddress2  = forms.IPAddressField(required=True,label="Gossip Router Service Ip Address 2",help_text="The VIP2 used by Applications to connect to the gossiprouter Service on the DB Cluster")
    eshistoryAddress = forms.IPAddressField(required=True,label="Eshistory Service Ip Address",help_text="The VIP used by Applications to connect to the Eshistory Service on the DB Cluster")

    class Meta:
        fields = ("postgresAddress","versantAddress","mysqlAddress","opendjAddress","opendjAddress2","jmsAddress","eSearchAddress","neo4jAddress1","neo4jAddress2","neo4jAddress3", "gossipRouterAddress1", "gossipRouterAddress2", "eshistoryAddress")
        model = DatabaseVips

class MulticastForm(forms.ModelForm):
    default_address = forms.IPAddressField(label="IPv4 Default Address")
    messaging_group_address = forms.IPAddressField(label="IPv4 Messaging Address")
    udp_mcast_address = forms.IPAddressField(label="IPv4 UDP Address")
    mping_mcast_address = forms.IPAddressField(label="IPv4 MPING Address")
    class Meta:
        fields = ("udp_mcast_port", "default_mcast_port", "mping_mcast_port", "messaging_group_port", "public_port_base", )
        model = Multicast

class ServiceGroupInstanceForm(forms.ModelForm):
    name = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="Name")
    hostname = forms.CharField(required=False,label="IP Hostname",help_text="Optional: Only required if IP is not registered in the DNS")
    address = forms.IPAddressField(required=True,label="Address (IPv4)")
    bitmask = forms.CharField(required=True,max_length=2,label="Bitmask")
    gateway = forms.IPAddressField(required=True,label="Gateway (IPv4)")
    class Meta:
        fields = ("name", )
        model = ServiceGroupInstance

class ServiceGroupInstanceFormInternal(forms.ModelForm):
    name = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="Name")
    address = forms.IPAddressField(required=True,label="Address (IPv4)")
    bitmask = forms.CharField(required=True,max_length=2,label="Bitmask")
    gateway = forms.IPAddressField(required=True,label="Gateway (IPv4)")
    class Meta:
        fields = ("name", )
        model = ServiceGroupInstance

class ServiceGroupSelectForm(forms.ModelForm):
    cluster_type = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}))
    class Meta:
        fields = ("name", "cluster_type", "node_list", )
        model = ServiceGroup

    def __init__(self, list,*args, **kwargs):
        super(ServiceGroupSelectForm, self).__init__(*args, **kwargs)
        self.fields['node_list'] = forms.CharField(widget=forms.CheckboxSelectMultiple(choices=list))
        self.group_names = []
        self.group_names = self.group_names + [(data.service_unit, unicode(data.service_unit)) for data in ServiceGroupUnit.objects.filter(group_type__group_type="JBOSS Service Cluster")]
        self.fields['name'] = forms.CharField(widget=forms.Select(choices=self.group_names))

class VlanAddressForm(forms.ModelForm):
    '''
    Class used to add vlans ip's to the IPAddress table
    '''
    address = forms.IPAddressField(required=False,label="IPv4 Address")
    bitmask = forms.CharField(max_length=4,required=False,label="IPv4 Bitmask")
    vlanTag = forms.CharField(max_length=4,required=False,label="Vlan Tag")
    class Meta:
        fields = ("address", "bitmask", )
        model = IpAddress

class VirtualImageForm(forms.ModelForm):
    class Meta:
        fields = ("name", "node_list", )
        model = VirtualImage
    def __init__(self, list, *args, **kwargs):
        super(VirtualImageForm, self).__init__(*args, **kwargs)
        self.fields['node_list'] = forms.CharField(widget=forms.RadioSelect(choices=list))
        self.virtualImages = []
        self.virtualImages = self.virtualImages + [(type, unicode(type)) for type in VirtualImageItems.objects.filter(active=1).order_by('name')]
        self.fields['name'] = forms.CharField(widget=forms.Select(choices=self.virtualImages))

class VirtualServerForm(forms.ModelForm):
    class Meta:
        fields = ("name", "node_list", )
        model = VirtualImage

class VirtualImageIpInfoForm(forms.ModelForm):
    number = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="Number")
    address = forms.IPAddressField(required=True,label="Address (IPv4)")
    class Meta:
        fields = ("number", )
        model = VirtualImageInfoIp

class VirtualImageSSHIpInfoForm(forms.ModelForm):
    number = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="Number")
    hostname = forms.CharField(required=True,label="IP Hostname")
    address = forms.IPAddressField(required=True,label="Address (IPv4)")
    class Meta:
        fields = ("number", )
        model = VirtualImageInfoIp

class VirtualImageIpv6InfoForm(forms.ModelForm):
    number = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="Number")
    hostname = forms.CharField(required=True,label="IP Hostname")
    address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=True,label="Address (IPv6)")
    class Meta:
        fields = ("number", )
        model = VirtualImageInfoIp

class VirtualImageIpv6InternalInfoForm(forms.ModelForm):
    number = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="Number")
    address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=True,label="Address (IPv6)")
    class Meta:
        fields = ("number", )
        model = VirtualImageInfoIp

class VirtualImageCredentialsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(VirtualImageCredentialsForm, self).__init__(*args, **kwargs)
        userTypesList = []
        userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]
        self.fields['username'] = forms.CharField(max_length=10,required=True,label="Username")
        self.fields['password'] = forms.CharField(max_length=50,required=True,label="Password")
        self.fields['credentialType'] = forms.CharField(widget=forms.Select(choices=userTypesList),required=True, label="Type")

class ServerCredentialsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ServerCredentialsForm, self).__init__(*args, **kwargs)
        userTypesList = []
        userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]
        self.fields['username'] = forms.CharField(max_length=10,required=True,label="Username")
        self.fields['password'] = forms.CharField(max_length=50,required=True,label="Password")
        self.fields['credentialType'] = forms.CharField(widget=forms.Select(choices=userTypesList),required=True, label="Type")

class ServiceGroupForm(forms.ModelForm):
    class Meta:
        fields = ("name", "cluster_type", "node_list", )
        model = ServiceGroup

class ServiceGroupCredentialsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ServiceGroupCredentialsForm, self).__init__(*args, **kwargs)
        userTypesList = []
        userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]
        self.fields['username'] = forms.CharField(max_length=10,required=True,label="Username")
        self.fields['password'] = forms.CharField(max_length=50,required=True,label="Password")
        self.fields['credentialType'] = forms.CharField(widget=forms.Select(choices=userTypesList),required=True, label="Type", initial="admin")


class UpdateServiceGroupCredentialsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        credentials = kwargs.pop('credentials')
        super(UpdateServiceGroupCredentialsForm, self).__init__(*args, **kwargs)
        counter = 1
        userTypesList = []
        userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]
        for cred in credentials:
            self.fields["Credentials " + str(counter)] = forms.CharField(required=False, widget=forms.CheckboxSelectMultiple(choices=[]))
            self.fields['username_' + str(counter)] = forms.CharField(max_length=10,required=True,label="Username", initial=cred.credentials.username)
            self.fields['password_' + str(counter)] = forms.CharField(max_length=50,required=True,label="Password", initial=cred.credentials.password)
            self.fields['credentialType_' + str(counter)] = forms.CharField(widget=forms.Select(choices=userTypesList), required=True, label="Type", initial=cred.credentials.credentialType)
            counter += 1

class DeleteServiceGroupCredentialsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        credentials = kwargs.pop('credentials')
        super(DeleteServiceGroupCredentialsForm, self).__init__(*args, **kwargs)
        counter = 1
        for cred in credentials:
            self.fields["Credentials " + str(counter)] = forms.CharField(required=False, widget=forms.CheckboxSelectMultiple(choices=[]))
            self.fields['username_' + str(counter)] = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}), label="Username", initial=cred.credentials.username)
            self.fields['password_' + str(counter)] = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}), label="Password", initial=cred.credentials.password)
            self.fields['credentialType_' + str(counter)] = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}), label="Type", initial=cred.credentials.credentialType)
            self.fields['delete_' + str(counter)] = forms.BooleanField(required=False, label='Delete Credentials ' +str(counter))
            counter += 1



class NasVipAddressForm(forms.Form):
    nasvip1 = forms.IPAddressField(required=True, label="NAS VIP1")
    nasvip2 = forms.IPAddressField(required=True, label="NAS VIP2")

class NasStorageDetailsForm(forms.ModelForm):
    poolFS1 = forms.CharField(max_length=7,required=True, label="NAS Pool Name")

    class Meta:
        fields = ("poolFS1", )
        model = NasStorageDetails

class NasStorageDetailsFormTor(forms.ModelForm):
    nasTypes = ( ( "unityxt", "unityxt" ), ( "veritas", "veritas" ),)
    sanPoolId = forms.CharField(max_length=10,required=True, label="SAN Pool ID")
    sanPoolName = forms.CharField(max_length=7,required=True, label="SAN Pool Name")
    sanRaidGroup = forms.CharField(required=True, label="SAN Raid Group",help_text="The Raid Group the fencing LUN is on")
    poolFS1 = forms.CharField(max_length=7,required=True, label="NAS Pool Name")
    fileSystem1 = forms.CharField(max_length=20,required=True, label="NAS Administrator FS")
    fileSystem2 = forms.CharField(max_length=20,required=True, label="NAS Observer FS")
    fileSystem3 = forms.CharField(max_length=20,required=True, label="NAS Cluster FS")
    nasType = forms.CharField(widget=forms.Select(choices=nasTypes), max_length=32,required=False, label="NAS Type")
    nasNdmpPassword = forms.CharField(max_length=20,required=False, label="NAS Ndmp Password")
    nasServerPrefix = forms.CharField(max_length=20,required=False, label="NAS Server Prefix")

    class Meta:
        fields = ("sanPoolId", "sanPoolName", "sanRaidGroup", "poolFS1", "fileSystem1", "fileSystem2", "fileSystem3", "nasType", "nasNdmpPassword", "nasServerPrefix",)
        model = NasStorageDetails

class NasStorageDetailsFormTorOnRack(NasStorageDetailsFormTor):
    fcSwitchesOpts = ( ( "None", None ), ( "True", True ), ( "False", False ),)
    fcSwitches = forms.CharField(widget=forms.Select(choices=fcSwitchesOpts),max_length=32,required=False,label="FC Switches")
    nasEthernetPorts = forms.CharField(max_length=20,required=True, label="NAS Ethernet Ports")
    sanPoolDiskCount = forms.IntegerField(required=True, label="SAN Pool Disk Count")

    class Meta(NasStorageDetailsFormTor.Meta):
        fields = ("sanPoolId", "sanPoolName", "sanRaidGroup", "poolFS1", "fileSystem1", "fileSystem2", "fileSystem3", "nasType", "nasNdmpPassword", "nasServerPrefix", "fcSwitches","sanPoolDiskCount","nasEthernetPorts")

class NasStorageDetailsFormOSS(forms.ModelForm):
    nasTypes = ( ( "unityxt", "unityxt" ), ( "veritas", "veritas" ),)
    sanPoolId = forms.CharField(max_length=10,required=False, label="SAN Pool ID")
    sanPoolName = forms.CharField(max_length=30,required=False, label="SAN Pool Name")
    poolFS1 = forms.CharField(max_length=20,required=True, label="NAS Segment One Pool Name")
    fileSystem1 = forms.CharField(max_length=20,required=True, label="NAS Segment One FS")
    poolFS2 = forms.CharField(max_length=20,required=True, label="NAS DDC Pool Name")
    fileSystem2 = forms.CharField(max_length=20,required=True, label="NAS DDC FS")
    poolFS3 = forms.CharField(max_length=20,required=True, label="NAS SGWCG Pool Name")
    fileSystem3 = forms.CharField(max_length=20,required=True, label="NAS SGWCG FS")
    nasType = forms.CharField(widget=forms.Select(choices=nasTypes), max_length=32,required=False, label="NAS Type")
    nasNdmpPassword = forms.CharField(max_length=20,required=False, label="NAS Ndmp Password")
    nasServerPrefix = forms.CharField(max_length=20,required=False, label="NAS Server Prefix")

    class Meta:
        fields = ("sanPoolId", "sanPoolName", "poolFS1", "fileSystem1", "poolFS2", "fileSystem2", "poolFS3", "fileSystem3", "nasType", "nasNdmpPassword", "nasServerPrefix",)
        model = NasStorageDetails

class NasStorageDetailsFormOSSOnRack(NasStorageDetailsFormOSS):
    fcSwitchesOpts = ( ( "None", None ), ( "True", True ), ( "False", False ),)
    fcSwitches = forms.CharField(widget=forms.Select(choices=fcSwitchesOpts),max_length=32,required=False,label="FC Switches")
    nasEthernetPorts = forms.CharField(max_length=20,required=True, label="NAS Ethernet Ports")
    sanPoolDiskCount = forms.IntegerField(required=True, label="SAN Pool Disk Count")

    class Meta(NasStorageDetailsFormOSS.Meta):
        fields = ("sanPoolId", "sanPoolName", "poolFS1", "fileSystem1", "poolFS2", "fileSystem2", "poolFS3", "fileSystem3", "nasType", "nasNdmpPassword", "nasServerPrefix", "fcSwitches", "sanPoolDiskCount", "nasEthernetPorts")

class AddVlanForm(forms.ModelForm):
    services_subnet = forms.CharField(required=True,label="Services Subnet",max_length=18,help_text="The subnet/netmask of the Services VLAN")
    services_gateway = forms.CharField(required=True,help_text="Services Gateway")
    services_ipv6_gateway = forms.CharField(required=False,label="Ipv6 Service Gateway",help_text="Optional: IPv6 gateway to route to the external NEs (e.g. EnodeBs) which are using IPv6.")
    services_ipv6_subnet = forms.CharField(required=False,label="Ipv6 Services Subnet",help_text="Optional: The IPv6 subnet/netmask of the ENM Services network")
    storage_subnet = forms.CharField(required=True,max_length=18,label="Storage Subnet",help_text="The subnet/netmask of the storage VLAN")
    storageGateway = forms.IPAddressField(required=False, label="Storage Gateway")
    backup_subnet = forms.CharField(required=True,max_length=18,label="Backup Subnet",help_text="The subnet/netmask of the backup VLAN")
    jgroups_subnet = forms.CharField(required=True,max_length=18,label="JGroups Subnet",help_text="The subnet/netmask of the jgroups VLAN")
    internal_subnet = forms.CharField(required=True,max_length=18,label="Internal Subnet",help_text="The subnet/netmask of the internal VLAN")
    internal_ipv6_subnet = forms.CharField(required=False,label="IPv6 Internal Subnet",help_text="The IPv6 subnet/netmask of the internal VLAN")
    storage_vlan = forms.CharField(required=False,max_length=5,label="Storage VLAN ID",help_text="The VLAN ID of the storage VLAN")
    backup_vlan = forms.CharField(required=False,max_length=5,label="Backup VLAN ID",help_text="The VLAN ID of the backup VLAN")
    jgroups_vlan = forms.CharField(required=False,max_length=5,label="JGroups VLAN ID",help_text="The VLAN ID of the jgroups VLAN")
    internal_vlan = forms.CharField(required=False,max_length=5,label="Internal VLAN ID",help_text="The VLAN ID of the internal VLAN")
    services_vlan = forms.CharField(required=False,max_length=5,label="Services VLAN ID",help_text="The VLAN ID of the services VLAN")
    management_vlan = forms.CharField(required=False,max_length=5,label="Management VLAN ID",help_text="The VLAN ID of the management VLAN")
    litpMList = (
        ('internal', 'internal'),
        ('services', 'services'))
    litp_management = forms.CharField(widget=forms.Select(choices=litpMList), required=True,help_text="Internal/External management",label="LITP Management")
    hbAVlan = forms.CharField(max_length=10,required=False,label="Heart Beat A VLAN ID", help_text="The VLAN ID of Heart Beat A VLAN, optional: Only required for Multi Enclosure deployments")
    hbBVlan = forms.CharField(max_length=10,required=False,label="Heart Beat B VLAN ID", help_text="The VLAN ID of Heart Beat B VLAN, optional: Only required for Multi Enclosure deployments")

    class Meta:
        fields = ("services_subnet", "services_gateway",
                "services_ipv6_gateway", "services_ipv6_subnet", "storage_subnet","storageGateway",
                "backup_subnet", "jgroups_subnet", "internal_subnet",  "internal_ipv6_subnet",
                "storage_vlan", "backup_vlan", "jgroups_vlan", "internal_vlan", "services_vlan", "management_vlan",
                "litp_management", "hbAVlan", "hbBVlan", )
        model = VlanDetails

class VirtualConnectNetworksForm(forms.ModelForm):
    sharedUplinkSetA = forms.CharField(max_length=50,required=True,label="Shared Uplink Set A")
    sharedUplinkSetB = forms.CharField(max_length=50,required=True,label="Shared Uplink Set B")
    servicesA = forms.CharField(max_length=50,required=True,label="Services A Network")
    servicesB = forms.CharField(max_length=50,required=True,label="Services B Network")
    storageA = forms.CharField(max_length=50,required=True,label="Storage A Network")
    storageB = forms.CharField(max_length=50,required=True,label="Storage B Network")
    backupA = forms.CharField(max_length=50,required=True,label="Backup A Network")
    backupB = forms.CharField(max_length=50,required=True,label="Backup B Network")
    jgroups = forms.CharField(max_length=50,required=True,label="JGroup Network")
    jgroupsA = forms.CharField(max_length=50,required=True,label="JGroups A Network")
    jgroupsB = forms.CharField(max_length=50,required=True,label="JGroups B Network")
    internalA = forms.CharField(max_length=50,required=True,label="Internal A Network")
    internalB = forms.CharField(max_length=50,required=True,label="Internal B Network")
    heartbeat1 = forms.CharField(max_length=50,required=True,label="Heartbeat1 Network", help_text="Optional: Only required for Single Enclosure deployments")
    heartbeat2 = forms.CharField(max_length=50,required=True,label="Heartbeat2 Network", help_text="Optional: Only required for Single Enclosure deployments")
    heartbeat1A = forms.CharField(max_length=50,required=True,label="Heartbeat1 A Network")
    heartbeat2B = forms.CharField(max_length=50,required=True,label="Heartbeat2 B Network")
    class Meta:
        fields = ("sharedUplinkSetA", "sharedUplinkSetB", )
        model = VirtualConnectNetworks

class ServiceIpRange(forms.Form):
    '''
    Used to give the facility for the user to be able to input service IP ranges, ipv4 or ipv6 addresses
    '''
    ipTypes = []
    ipTypes = ipTypes + [(rangeItem.ipType, unicode(rangeItem.ipType)) for rangeItem in VmServiceIpRangeItem.objects.all()]
    ipType = forms.CharField(widget=forms.Select(choices=ipTypes),label="IP Type")
    startIp = forms.GenericIPAddressField(required=True,label="Start Ip Range")
    endIp = forms.GenericIPAddressField(required=True,label="End Ip Range")

class DasTypeForm(forms.Form):
    '''
    Used to give a drop down menu when adding a DAS so you can choose which type of DAS to use
    '''
    dasList = (
        ('SAN', 'SAN'),
        ('NAS', 'NAS'))
    dasType = forms.CharField(widget=forms.Select(choices=dasList),label="DAS Type")

class ProductTypeForm(forms.Form):
    list = []
    list = list + [(product, unicode(product)) for product in Product.objects.all().exclude(name="LITP").exclude(name="None")]
    product = forms.CharField(widget=forms.Select(choices=list))

class LSBServiceForm (forms.ModelForm):
    cluster_type = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}))
    class Meta:
        fields = ("name", "cluster_type", "node_list",)
        model = ServiceGroup
    def __init__(self, list, *args, **kwargs):
        super(LSBServiceForm, self).__init__(*args, **kwargs)
        self.fields['node_list'] = forms.CharField(widget=forms.CheckboxSelectMultiple(choices=list))
        self.group_names = []
        self.group_names = self.group_names + [(data.service_unit, unicode(data.service_unit)) for data in ServiceGroupUnit.objects.filter(group_type__group_type="LSB Service Cluster")]
        self.fields['name'] = forms.CharField(widget=forms.Select(choices=self.group_names))


class ServiceGroupUpdateForm (forms.ModelForm):
    cluster_type = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}))
    class Meta:
        fields = ("name", "cluster_type", "node_list",)
        model = ServiceGroup
    def __init__(self, list,*args, **kwargs):
        super(ServiceGroupUpdateForm, self).__init__(*args, **kwargs)
        self.fields['name'] = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}))
        self.fields['node_list'] = forms.CharField(widget=forms.CheckboxSelectMultiple(choices=list))


class ServiceGroupPackageMappingSelectForm (forms.Form):
    package = forms.CharField()

    def __init__(self, list,*args, **kwargs):
        super(ServiceGroupPackageMappingSelectForm, self).__init__(*args, **kwargs)
        self.fields["package"] = forms.CharField(widget=forms.CheckboxSelectMultiple(choices=list))

class ServicesClusterForm (forms.ModelForm):
    '''
    '''
    class Meta:
        fields = ("cluster_type", "name", )
        model = ServicesCluster
        cluster_type = forms.CharField()
        name = forms.CharField()

    def __init__(self,*args, **kwargs):
        super(ServicesClusterForm, self).__init__(*args, **kwargs)
        self.fields['cluster_type'] = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}))
        self.fields['name'] = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}))

class JbossClusterForm (forms.ModelForm):
    '''
    '''
    class Meta:
        fields = ("cluster_type", "name", )
        model = ServicesCluster
        cluster_type = forms.CharField()
        name = forms.CharField()

    def __init__(self,*args, **kwargs):
        super(JbossClusterForm, self).__init__(*args, **kwargs)
        group_names = []
        group_names = group_names + [(data.name, unicode(data.name)) for data in JbossClusterServiceGroup.objects.all().order_by('id')]
        name = forms.CharField(widget=forms.Select(choices=group_names))
        self.fields['cluster_type'] = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}))
        self.fields['name'] = forms.ChoiceField(choices=group_names)

class VeritasClusterForm (forms.ModelForm):
    gcoIp = forms.IPAddressField(required=False,label="GCO IPv4 Address")
    gcoBitmask = forms.CharField(max_length=4,required=False,label="GCO IPv4 Bitmask")
    gcoNic = forms.CharField(max_length=10,label="GCO Network Interface")
    csgIp = forms.IPAddressField(required=False,label="CSG IPv4 Address")
    csgBitmask = forms.CharField(max_length=4,required=False,label="CSG IPv4 Bitmask")
    csgNic = forms.CharField(max_length=10,label="CSG Network Interface")
    lltLink1 = forms.CharField(max_length=10,label="Low Latency Transport Link 1")
    lltLink2 = forms.CharField(max_length=10,label="Low Latency Transport Link 2")
    lltLinkLowPri1 = forms.CharField(max_length=10,label="LLT Priority 1")

    class Meta:
        fields = ("csgNic", "gcoNic", "lltLink1", "lltLink2", "lltLinkLowPri1", )
        model = VeritasCluster

class NetworkInterfaceForm(forms.ModelForm):
    '''
    '''
    mac_address = forms.CharField(max_length=18, label="Mac Address (eth0)")
    def __init__(self,hardwareType,*args, **kwargs):
        super(NetworkInterfaceForm, self).__init__(*args, **kwargs)
        if hardwareType == "blade":
            list = []
            list = list + [(enclosure, unicode(enclosure)) for enclosure in Enclosure.objects.all()]

            self.fields['serial_number'] = forms.CharField()
            self.fields['vc_profile_name'] = forms.CharField()
            self.fields['enclosure'] = forms.CharField(widget=forms.Select(choices=list))
            self.fields['vlan_tag'] = forms.CharField()

    class Meta:
        fields = ("mac_address", )
        model = NetworkInterface

class IpAddressForm(forms.ModelForm):
    class Meta:
        fields = ("address", "bitmask", "gateway_address", )
        model = IpAddress

class IpAddressMsForm(forms.ModelForm):
    class Meta:
        fields = ("address", "bitmask", "gateway_address","interface" )
        model = IpAddress

class Ipv6AddressForm(forms.ModelForm):
    ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="IPv6 Host Address")
    ipv6_bitmask = forms.CharField(max_length=4,required=False,label="IPv6 Host Bitmask")
    ipv6_gateway = forms.GenericIPAddressField(required=False,label="IPv6 Host Gateway")
    class Meta:
        fields = ("ipv6_address", "ipv6_bitmask", "ipv6_gateway")
        model = IpAddress

class IloForm(forms.ModelForm):
    ilo_address = forms.IPAddressField(required=False,label="IPv4 ILO Address")
    username = forms.CharField(required=False,max_length=10,label="ILO Username")
    password = forms.CharField(required=False,max_length=50,label="ILO Password")
    class Meta:
        fields = ("username", "password", )
        model = Ilo

class UpdateMgtServerForm(forms.Form):
    '''
    '''
    userTypesList = []
    userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]

    productList = []
    productList = productList + [(product, unicode(product)) for product in Product.objects.all().exclude(name="LITP")]

    product = forms.CharField(widget=forms.Select(choices=productList))
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(required=True,help_text="The hostname as on the DNS of the Management Server",max_length=100)
    domain_name = forms.CharField(required=True,help_text="The fully qualified domain in which the Management Server resides",max_length=100)
    dns_serverA = forms.GenericIPAddressField(required=True,label="DNS IP Address A")
    dns_serverB = forms.GenericIPAddressField(required=True,label="DNS IP Address B")
    mac_address = forms.CharField(required=True,max_length=18,help_text="The eth0 mac address for the Management Server",label="MAC Address (eth0)")
    mac_address_eth1 = forms.CharField(required=False,max_length=18,help_text="The eth1 mac address for the Management Server",label="MAC Address (eth1)")
    mac_address_eth2 = forms.CharField(required=False,max_length=18,help_text="The eth2 mac address for the Management Server",label="MAC Address (eth2)")
    mac_address_eth3 = forms.CharField(required=False,max_length=18,help_text="The eth3 mac address for the Management Server",label="MAC Address (eth3)")
    external_ip_address = forms.IPAddressField(required=True,help_text="LITP Management Server IPv4 address",label="IPv4 Host Address")
    external_bitmask = forms.CharField(required=False,max_length=4,help_text="Used to Generate the subnet of the Services VLAN",label="IPv4 Host Bitmask")
    external_ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,help_text="LITP Management Server IPv6 Address (Optional: Please input ipv6 address WITHOUT postfix, e.g. /64))",label="IPv6 Host Address")
    storageIp = forms.IPAddressField(required=False,help_text="LITP Management Server storage IP address",label="IPv4 Storage Vlan Address")
    bckUpIp = forms.IPAddressField(required=False,help_text="LITP Management Server backup IP address",label="IPv4 Backup Vlan Address")
    lmsIpInternal = forms.IPAddressField(required=False,help_text="LITP Management Server Internal IP address",label="IPv4 Internal Vlan Address")
    ilo_ip_address = forms.GenericIPAddressField(required=False,help_text="The Management Server HP Ilo IP Address",label="Ilo IP Address")
    ilo_username = forms.CharField(required=False,help_text="The HP ILO User Name",label="Ilo Username")
    ilo_password = forms.CharField(required=False,help_text="The HP ILO User Password",label="Ilo Password")
    description = forms.CharField(required=True,help_text="Description of what this server will be used for and team details",widget=forms.Textarea)

class UpdateNASServerForm(forms.Form):
    def __init__(self, hardwareType, *args, **kwargs):
        super(UpdateNASServerForm, self).__init__(*args, **kwargs)
        self.fields['domain_name'] = forms.CharField(max_length=100)
        self.fields['name'] = forms.CharField(label="Machine Name", max_length=30)
        self.fields['hostname'] = forms.CharField(help_text="The hostname as on the DNS",required=True,max_length=100)
        self.fields['dns_serverA'] = forms.GenericIPAddressField(label="DNS IP Address A")
        self.fields['dns_serverB'] = forms.GenericIPAddressField(label="DNS IP Address B")
        self.fields['mac_address'] = forms.CharField(max_length=18)
        self.fields['ip_address'] = forms.GenericIPAddressField()
        self.fields['bitmask'] = forms.CharField(max_length=4)
        self.fields['gateway_address'] = forms.GenericIPAddressField()
        self.fields['nasvip1'] = forms.IPAddressField(required=False,label="NAS VIP1")
        self.fields['nasvip2'] = forms.IPAddressField(required=False,label="NAS VIP2")
        self.fields['nasinstallip1'] = forms.IPAddressField(required=False,label="NAS Install IP 1")
        self.fields['nasinstallip2'] = forms.IPAddressField(required=False,label="NAS Install IP 2")
        self.fields['masterUsername'] = forms.CharField(max_length=100,label="Master Username")
        self.fields['masterPassword'] = forms.CharField(max_length=100,label="Master Password")
        self.fields['supportUsername'] = forms.CharField(max_length=100,label="Support Username")
        self.fields['supportPassword'] = forms.CharField(max_length=100,label="Support Password")
        self.fields['nasInstallIloIp1Username'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 1 Username")
        self.fields['nasInstalIlolIp1Password'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 1 Password")
        self.fields['nasInstallIloIp2Username'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 2 Username")
        self.fields['nasInstalIlolIp2Password'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 2 Password")
        self.fields['sfsNode1Hostname'] = forms.CharField(help_text="The SFS Node 1 hostname",required=False,max_length=100, label="SFS Node 1 Hostname")
        self.fields['sfsNode2Hostname'] = forms.CharField(help_text="The SFS Node 2 hostname",required=False,max_length=100, label="SFS Node 2 Hostname")
        if hardwareType != 'virtual' and hardwareType != 'cloud':
            self.fields['nasInstalIlolIp1'] = forms.IPAddressField(required=False,label="Nas Install ILO Ip 1")
            self.fields['nasInstallIloIp1Username'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 1 Username")
            self.fields['nasInstalIlolIp1Password'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 1 Password")
            self.fields['masterIloUsername'] = forms.CharField(required=False,max_length=100,label="Master ILO Username")
            self.fields['masterIloPassword'] = forms.CharField(required=False,max_length=100,label="Master ILO Password")
            self.fields['nasInstalIlolIp2'] = forms.IPAddressField(required=False,label="Nas Install ILO Ip 2")
            self.fields['nasInstallIloIp2Username'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 2 Username")
            self.fields['nasInstalIlolIp2Password'] = forms.CharField(required=False,max_length=100,label="Nas Install ILO Ip 2 Password")
            self.fields['supportIloUsername'] = forms.CharField(required=False,max_length=100,label="Support ILO Username")
            self.fields['supportIloPassword'] = forms.CharField(required=False,max_length=100,label="Support ILO Password")


class UpdateStorageServerForm(forms.Form):
    vnxChoices = (
        ('5100(vnx1)', '5100(vnx1)'),
        ('5300(vnx1)', '5300(vnx1)'),
        ('5500(vnx1)', '5500(vnx1)'),
        ('5200(vnx2)', '5200(vnx2)'),
        ('5400(vnx2)', '5400(vnx2)'),
        ('5600(vnx2)', '5600(vnx2)'),
        ('450F(unity)', '450F(unity)'))
    name = forms.CharField(label="Machine Name", max_length=30)
    vnxType = forms.CharField(widget=forms.Select(choices=vnxChoices), label="VNX Type")
    domain_name = forms.CharField(max_length=100)
    serial_number = forms.CharField(max_length=18,required=True,help_text="Serial Number of the SAN")
    storage_ip1 = forms.GenericIPAddressField(label="SP-A IP Address")
    storage_ip2 = forms.GenericIPAddressField(label="SP-B IP Address")
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100)
    login_scope = forms.CharField(max_length=20)
    sanAdminPassword = forms.CharField(max_length=20,required=False, label="SAN Admin Password")
    sanServicePassword = forms.CharField(max_length=20,required=False, label="SAN Service Password")

class EnclosureMultipleIpForm(forms.Form):
    '''
    '''
    hostname = forms.CharField(required=True)
    domain_name = forms.CharField(required=True)
    vc_domain_name = forms.CharField(max_length=100,label="Virtual Connect Domain Name")
    rackName = forms.CharField(required=True,max_length=32,label="Rack Name")
    name = forms.CharField(required=True,max_length=32,label="Enclosure Name")
    # On Board Admin details
    IpAddress1 = forms.GenericIPAddressField(required=True,label="On Board Admin IP 1")
    IpAddress2 = forms.GenericIPAddressField(required=True,label="On Board Admin IP 2")
    username = forms.CharField(max_length=10,required=True,label="On Board Admin Login Username")
    password = forms.CharField(max_length=50,required=True,label="On Board Admin Login Password")
    # Virtual Connect Details
    vcIpAddress1 = forms.GenericIPAddressField(label="Virtual Connect IP 1")
    vcIpAddress2 = forms.GenericIPAddressField(label="Virtual Connect IP 2")
    vc_module_bay_1 = forms.CharField(max_length=2,required=False,help_text="The VC1 interconnect bay location",label="Virtual Connect 1 bay location")
    vc_module_bay_2 = forms.CharField(max_length=2,required=False,help_text="The VC2 interconnect bay location",label="Virtual Connect 2 bay location")
    vcUsername = forms.CharField(max_length=10,label="Virtual Connect Login Username")
    vcPassword = forms.CharField(max_length=50,label="Virtual Connect Login Password")
    sanSwIpAddress1 = forms.GenericIPAddressField(label="SAN Switch IP 1")
    sanSwIpAddress2 = forms.GenericIPAddressField(label="SAN Switch IP 2")
    san_sw_bay_1 = forms.CharField(max_length=2,required=False,help_text="The SAN switch 1 interconnect bay location",label="SAN Switch 1 bay location")
    san_sw_bay_2 = forms.CharField(max_length=2,required=False,help_text="The SAN switch 2 interconnect bay location",label="SAN Switch 2 bay location")
    sanSwUsername = forms.CharField(max_length=10,label="SAN Switch Login Username")
    sanSwPassword = forms.CharField(max_length=50,label="SAN Switch Login Password")
    uplink_A_port1 = forms.CharField(max_length=30,label="Uplink A Port 1")
    uplink_A_port2 = forms.CharField(max_length=30,label="Uplink A Port 2")
    uplink_B_port1 = forms.CharField(max_length=30,label="Uplink B Port 1")
    uplink_B_port2 = forms.CharField(max_length=30,label="Uplink B Port 2")

class UpdateEnclosureServerForm(forms.Form):
    domain_name = forms.CharField(max_length=100,label="Domain Name")
    vc_domain_name = forms.CharField(max_length=100,label="Virtual Connect Domain Name")
    rackName = forms.CharField(required=True,max_length=32,label="Rack Name")
    name = forms.CharField(required=True,max_length=32,label="Enclosure Name")
    enclosure_ip1 = forms.GenericIPAddressField(label="On Board Admin IP 1")
    enclosure_ip2 = forms.GenericIPAddressField(label="On Board Admin IP 2")
    username = forms.CharField(max_length=10,label="On Board Admin Login Username")
    password = forms.CharField(max_length=50,label="On Board Admin Login Password")
    vc_enclosure_ip1 = forms.GenericIPAddressField(label="Virtual Connect IP 1")
    vc_enclosure_ip2 = forms.GenericIPAddressField(label="Virtual Connect IP 2")
    vc_module_bay_1 = forms.CharField(max_length=2,required=False,help_text="The VC 1 interconnect bay location",label="Virtual Connect 1 bay location")
    vc_module_bay_2 = forms.CharField(max_length=2,required=False,help_text="The VC 2 interconnect bay location",label="Virtual Connect 2 bay location")
    vc_username = forms.CharField(max_length=10,label="Virtual Connect Login Username")
    vc_password = forms.CharField(max_length=50,label="Virtual Connect Login Password")
    sanSw_enclosure_ip1 = forms.GenericIPAddressField(label="SAN Switch IP 1")
    sanSw_enclosure_ip2 = forms.GenericIPAddressField(label="SAN Switch IP 2")
    san_sw_bay_1 = forms.CharField(max_length=2,required=False,help_text="The SAN switch 1 interconnect bay location",label="SAN Switch 1 bay location")
    san_sw_bay_2 = forms.CharField(max_length=2,required=False,help_text="The SAN switch 2 interconnect bay location",label="SAN Switch 2 bay location")
    sanSw_username = forms.CharField(max_length=10,label="SAN Switch Login Username")
    sanSw_password = forms.CharField(max_length=50,label="SAN Switch Login Password")
    uplink_A_port1 = forms.CharField(max_length=30,label="Uplink A Port 1")
    uplink_A_port2 = forms.CharField(max_length=30,label="Uplink A Port 2")
    uplink_B_port1 = forms.CharField(max_length=30,label="Uplink B Port 1")
    uplink_B_port2 = forms.CharField(max_length=30,label="Uplink B Port 2")

class RackProductionServerForm(forms.Form):
    '''
    Rack Production Server Form
    '''

    active = forms.BooleanField(required=False,help_text="Ticked - Active, Not Ticked - Passive",label="Server Status")
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(max_length=100,help_text="The hostname as on the DNS")
    domain_name = forms.CharField(max_length=100,help_text="The fully qualified domain in which Server resides")
    dns_serverA = forms.GenericIPAddressField(label="DNS IP Address A")
    dns_serverB = forms.GenericIPAddressField(label="DNS IP Address B")
    mac_address = forms.CharField(max_length=18,help_text="The eth0 mac address", label="MAC Address (eth0)")
    mac_address_eth1 = forms.CharField(required=True,max_length=18,help_text="The eth1 mac address",label="MAC Address (eth1)")
    mac_address_eth2 = forms.CharField(required=True,max_length=18,help_text="The eth2 mac address",label="MAC Address (eth2)")
    mac_address_eth3 = forms.CharField(required=True,max_length=18,help_text="The eth3 mac address",label="MAC Address (eth3)")
    mac_address_eth4 = forms.CharField(required=False,max_length=18,help_text="The eth4 mac address",label="MAC Address (eth4)")
    mac_address_eth5 = forms.CharField(required=False,max_length=18,help_text="The eth5 mac address",label="MAC Address (eth5)")
    mac_address_eth6 = forms.CharField(required=False,max_length=18,help_text="The eth6 mac address",label="MAC Address (eth6)")
    wwpnOne = forms.CharField(max_length=23,required=False,help_text="Optional: The WWPN of Port 1",label="WWPN 1")
    wwpnTwo = forms.CharField(max_length=23,required=False,help_text="Optional: The WWPN of Port 2",label="WWPN 2")
    bootdisk_uuid = forms.CharField(required=True,max_length=32,help_text="bootdisk uuid",label="Disk UUID")
    ip_address = forms.IPAddressField(required=True,label="IPv4 Host Address")
    ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,help_text="(Optional: Please input ipv6 address WITHOUT postfix, e.g. /64)",label="IPv6 Host Address")
    internalIp = forms.IPAddressField(required=True,label="IPv4 Internal Vlan Address")
    storageIp = forms.IPAddressField(required=True,help_text="Storage IP VLAN address",label="IPv4 Storage Vlan Address")
    bckUpIp = forms.IPAddressField(required=True,help_text="Server backup IP address",label="IPv4 Backup Vlan Address")
    jgroupIp = forms.IPAddressField(required=True,label="IPv4 JGroup Vlan Address")
    serial_number = forms.CharField(required=True,max_length=18,help_text="Serial number of the blade")
    ilo_address = forms.IPAddressField(required=True,help_text="The Server HP Ilo IP Address",label="IPv4 ILO Address")
    username = forms.CharField(required=True,max_length=10,help_text="The HP ILO User Name",label="ILO Username")
    password = forms.CharField(required=True,max_length=50,help_text="The HP ILO User Password",label="ILO Password")

class RackTestServerForm(forms.Form):
    '''
    Rack Test Server Form
    '''
    active = forms.BooleanField(required=False,help_text="Ticked - Active, Not Ticked - Passive",label="Server Status")
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(max_length=100,help_text="The hostname as on the DNS")
    domain_name = forms.CharField(max_length=100,help_text="The fully qualified domain in which Server resides")
    dns_serverA = forms.GenericIPAddressField(label="DNS IP Address A")
    dns_serverB = forms.GenericIPAddressField(label="DNS IP Address B")
    mac_address = forms.CharField(required=True, max_length=18,help_text="The eth0 mac address", label="MAC Address (eth0)")
    mac_address_eth1 = forms.CharField(required=True,max_length=18,help_text="The eth1 mac address",label="MAC Address (eth1)")
    mac_address_eth4 = forms.CharField(required=False,max_length=18,help_text="The eth4 mac address",label="MAC Address (eth4)")
    mac_address_eth5 = forms.CharField(required=False,max_length=18,help_text="The eth5 mac address",label="MAC Address (eth5)")
    mac_address_eth6 = forms.CharField(required=False,max_length=18,help_text="The eth6 mac address",label="MAC Address (eth6)")
    wwpnOne = forms.CharField(max_length=23,required=False,help_text="Optional: The WWPN of Port 1",label="WWPN 1")
    wwpnTwo = forms.CharField(max_length=23,required=False,help_text="Optional: The WWPN of Port 2",label="WWPN 2")
    bootdisk_uuid = forms.CharField(required=True,max_length=32,help_text="bootdisk uuid",label="Disk UUID")
    ip_address = forms.IPAddressField(required=True, label="IPv4 Host Address")
    ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,help_text="(Optional: Please input ipv6 address WITHOUT postfix, e.g. /64)",label="IPv6 Host Address")
    internalIp = forms.IPAddressField(required=True,label="IPv4 Internal Vlan Address")
    storageIp = forms.IPAddressField(required=True,help_text="Storage IP VLAN address",label="IPv4 Storage Vlan Address")
    bckUpIp = forms.IPAddressField(required=True,help_text="Server backup IP address",label="IPv4 Backup Vlan Address")
    jgroupIp = forms.IPAddressField(required=True,label="IPv4 JGroup Vlan Address")
    serial_number = forms.CharField(required=True,max_length=18,help_text="Serial number of the blade")
    ilo_address = forms.IPAddressField(required=True,help_text="The Server HP Ilo IP Address",label="IPv4 ILO Address")
    username = forms.CharField(required=True,max_length=10, help_text="The HP ILO User Name",label="ILO Username")
    password = forms.CharField(required=True,max_length=50, help_text="The HP ILO User Password",label="ILO Password")


class UpdateServerFormBlade(forms.Form):
    '''
    '''
    enclosureList = []
    enclosureList = enclosureList + [(enclosure, unicode(enclosure)) for enclosure in Enclosure.objects.all()]

    userTypesList = []
    userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]

    active = forms.BooleanField(required=False,help_text="Ticked - Active, Not Ticked - Passive",label="Server Status")
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(help_text="The hostname as on the DNS",max_length=100)
    domain_name = forms.CharField(help_text="The fully qualified domain in which the Server resides",max_length=100)
    dns_serverA = forms.GenericIPAddressField(label="DNS IP Address A")
    dns_serverB = forms.GenericIPAddressField(label="DNS IP Address B")
    mac_address = forms.CharField(required=True,help_text="The eth0 mac address for the Server",max_length=18,label="MAC Address (eth0)")
    ip_address = forms.IPAddressField(required=True,help_text="Server IP address",label="IPv4 Host Address")
    ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,help_text="The ipv6 Address of the Services network. (Optional: Please input ipv6 address WITHOUT postfix, e.g. /64)",label="IPv6 Host Address")
    internalIp = forms.IPAddressField(required=False,label="IPv4 Internal Vlan Address")
    storageIp = forms.IPAddressField(required=False,help_text="Storage IP VLAN address",label="IPv4 Storage Vlan Address")
    bckUpIp = forms.IPAddressField(required=False,help_text="Server backup IP address",label="IPv4 Backup Vlan Address")
    multicastIp = forms.IPAddressField(required=False,label="IPv4 Multicast Vlan Address")
    serial_number = forms.CharField(required=True,help_text="Serial number of the blade")
    vc_profile_name = forms.CharField(required=True)
    enclosure = forms.CharField(widget=forms.Select(choices=enclosureList))
    ilo_address = forms.IPAddressField(required=False,help_text="The Server HP Ilo IP Address",label="IPv4 ILO Address")
    username = forms.CharField(required=False,help_text="The HP ILO User Name",label="ILO Username")
    password = forms.CharField(required=False,help_text="The HP ILO User Password",label="ILO Password")

class UpdateServerForm(forms.Form):

    userTypesList = []
    userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]

    active = forms.BooleanField(required=False,help_text="Ticked - Active, Not Ticked - Passive",label="Server Status")
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(help_text="The hostname as on the DNS",max_length=100)
    domain_name = forms.CharField(help_text="The fully qualified domain in which the Server resides",max_length=100)
    dns_serverA = forms.GenericIPAddressField(label="DNS IP Address A")
    dns_serverB = forms.GenericIPAddressField(label="DNS IP Address B")
    mac_address = forms.CharField(required=True,help_text="The eth0 mac address for the Server",max_length=18,label="MAC Address (eth0)")
    ip_address = forms.IPAddressField(required=True,help_text="Server IP address",label="IPv4 Host Address")
    ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,help_text="The ipv6 IP Address of the Services network. (Optional: Please input ipv6 address WITHOUT postfix, e.g. /64)",label="IPv6 Host Address")
    internalIp = forms.IPAddressField(required=False,label="IPv4 Internal Vlan Address")
    storageIp = forms.IPAddressField(required=False,help_text="Storage IP VLAN address",label="IPv4 Storage Vlan Address")
    bckUpIp = forms.IPAddressField(required=False,help_text="Server backup IP address",label="IPv4 Backup Vlan Address")
    multicastIp = forms.IPAddressField(required=False,label="IPv4 Multicast Vlan Address")

class VCSServerForm(forms.Form):

    userTypesList = []
    userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]

    active = forms.BooleanField(required=False,help_text="Ticked - Active, Not Ticked - Passive",label="Server Status")
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(max_length=100,help_text="The hostname as on the DNS")
    domain_name = forms.CharField(max_length=100,help_text="The fully qualified domain in which VCS Server resides")
    dns_serverA = forms.GenericIPAddressField(label="DNS IP Address A")
    dns_serverB = forms.GenericIPAddressField(label="DNS IP Address B")
    mac_address = forms.CharField(max_length=18,help_text="The eth0 mac address for VCS Server", label="MAC Address (eth0)")
    mac_address_eth1 = forms.CharField(required=False,max_length=18,help_text="The eth1 mac address for VCS Server",label="MAC Address (eth1)")
    mac_address_eth2 = forms.CharField(required=False,max_length=18,help_text="The eth2 mac address for VCS Server",label="MAC Address (eth2)")
    mac_address_eth3 = forms.CharField(required=False,max_length=18,help_text="The eth3 mac address for VCS Server",label="MAC Address (eth3)")
    mac_address_eth4 = forms.CharField(required=False,max_length=18,help_text="The eth4 mac address for VCS Server",label="MAC Address (eth4)")
    mac_address_eth5 = forms.CharField(required=False,max_length=18,help_text="The eth5 mac address for VCS Server",label="MAC Address (eth5)")
    mac_address_eth6 = forms.CharField(required=False,max_length=18,help_text="The eth6 mac address for VCS Server",label="MAC Address (eth6)")
    mac_address_eth7 = forms.CharField(required=False,max_length=18,help_text="The eth7 mac address for VCS Server",label="MAC Address (eth7)")
    mac_address_eth8 = forms.CharField(required=False,max_length=18,help_text="The eth8 mac address for VCS Server",label="MAC Address (eth8)")
    wwpnOne = forms.CharField(max_length=23,required=False,help_text="The WWPN of Port 1 on VCS Server",label="WWPN 1")
    wwpnTwo = forms.CharField(max_length=23,required=False,help_text="The WWPN of Port 2 on VCS Server",label="WWPN 2")
    ip_address = forms.IPAddressField(label="IPv4 Host Address")
    ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,help_text="(Optional: Please input ipv6 address WITHOUT postfix, e.g. /64)",label="IPv6 Host Address")
    internalIp = forms.IPAddressField(required=False,label="IPv4 Internal Vlan Address")
    storageIp = forms.IPAddressField(required=False,help_text="The storage IP address for VCS Server",label="IPv4 Storage Vlan Address")
    bckUpIp = forms.IPAddressField(required=False,help_text="The backup IP address for VCS Server",label="IPv4 Backup Vlan Address")
    jgroupIp = forms.IPAddressField(required=False,label="IPv4 JGroup Vlan Address")

class VCSServerBladeForm(forms.Form):

    userTypesList = []
    userTypesList = userTypesList + [(type, unicode(type)) for type in UserTypes.objects.all()]

    enclosureList = []
    enclosureList = enclosureList + [(enclosure, unicode(enclosure)) for enclosure in Enclosure.objects.all()]

    active = forms.BooleanField(required=False,help_text="Ticked - Active, Not Ticked - Passive",label="Server Status")
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(max_length=100,help_text="The hostname as on the DNS")
    domain_name = forms.CharField(max_length=100,help_text="The fully qualified domain in which VCS Server resides")
    dns_serverA = forms.GenericIPAddressField(label="DNS IP Address A")
    dns_serverB = forms.GenericIPAddressField(label="DNS IP Address B")
    mac_address = forms.CharField(max_length=18,help_text="The eth0 mac address for VCS Server", label="MAC Address (eth0)")
    mac_address_eth1 = forms.CharField(required=False,max_length=18,help_text="The eth1 mac address for VCS Server",label="MAC Address (eth1)")
    mac_address_eth2 = forms.CharField(required=False,max_length=18,help_text="The eth2 mac address for VCS Server",label="MAC Address (eth2)")
    mac_address_eth3 = forms.CharField(required=False,max_length=18,help_text="The eth3 mac address for VCS Server",label="MAC Address (eth3)")
    wwpnOne = forms.CharField(max_length=23,required=False,help_text="The WWPN of Port 1 on VCS Server",label="WWPN 1")
    wwpnTwo = forms.CharField(max_length=23,required=False,help_text="The WWPN of Port 2 on VCS Server",label="WWPN 2")
    ip_address = forms.IPAddressField(label="IPv4 Host Address")
    ipv6_address = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,help_text="(Optional: Please input ipv6 address WITHOUT postfix, e.g. /64)",label="IPv6 Host Address")
    internalIp = forms.IPAddressField(required=False,label="IPv4 Internal Vlan Address")
    storageIp = forms.IPAddressField(required=False,help_text="The storage IP address forVCS Server",label="IPv4 Storage Vlan Address")
    bckUpIp = forms.IPAddressField(required=False,help_text="The backup IP address forVCS Server",label="IPv4 Backup Vlan Address")
    jgroupIp = forms.IPAddressField(required=False,label="IPv4 JGroup Vlan Address")
    enclosure = forms.CharField(widget=forms.Select(choices=enclosureList))
    serial_number = forms.CharField(required=True,help_text="Serial number of the blade")
    vc_profile_name = forms.CharField(required=True,help_text="Virtual Connect Profile Name")
    ilo_address = forms.IPAddressField(required=False,help_text="The ip address for HP iLO",label="IPv4 ILO Address")
    username = forms.CharField(required=False,help_text="The username for HP iLO",label="ILO Username")
    password = forms.CharField(required=False,help_text="The password for HP iLO",label="ILO Password")

class UpdateClusterForm(forms.ModelForm):
    def __init__(self, layouts, *args, **kwargs):
        super(UpdateClusterForm, self).__init__(*args, **kwargs)
        self.fields["enmDeploymentType"] = forms.ModelChoiceField(queryset=EnmDeploymentType.objects.all(), required=False, label="ENM Deployment Type", help_text="Required for EDP")
        self.fields["ipVersion"] = forms.ModelChoiceField(queryset=IpVersion.objects.all(), required=False, label="IP Version", help_text="Required for EDP")
        self.fields["component"] = forms.ModelChoiceField(queryset=Component.objects.filter(label__name = "RA", deprecated=0), required=False, label="Select a RA")
        if layouts:
            layoutList = []
            layoutList = layoutList + [(name, unicode(name)) for name in layouts]
            self.fields['layout'] = forms.CharField(widget=forms.Select(choices=layoutList), label="Deployment Layout")
    class Meta:
        fields = ("name","description", "tipc_address", "management_server", "enmDeploymentType", "ipVersion")
        model = Cluster

class UpdateClusterFormExtraLargeENM(UpdateClusterForm):
    compact_audit_logger_choices = (
        (True, 'True'),
        (False, 'False')
    )
    compact_audit_logger = forms.CharField(widget=forms.Select(choices=compact_audit_logger_choices),max_length=32,required=False,label="Compact Audit Logger")
    class Meta:
        fields = ("name","description", "tipc_address", "management_server", "compact_audit_logger", "enmDeploymentType", "ipVersion")
        model = Cluster

class EditDeploymentStatusForm(forms.ModelForm):
    '''
    Deployment Status Edit form
    '''

    description = forms.CharField(widget=forms.Textarea,required=False,label="Description")
    osDetails = forms.CharField(required=False,label="OS")
    litpVersion = forms.CharField(required=False,label="LITP")
    mediaArtifact = forms.CharField(required=False,label="ENM Artifact (ISO)")
    packages = forms.CharField(widget=forms.Textarea,required=False,label="KGB Packages")
    patches = forms.CharField(widget=forms.Textarea,required=False,label="Patches")

    class Meta:
        fields = ("status", "osDetails", "patches", "litpVersion", "mediaArtifact", "packages", "description")
        model = DeploymentStatus

class InstallGroupForm (forms.ModelForm):
    installGroup = forms.CharField(label="Install Group")

    class Meta:
        fields = ("installGroup",)
        model = InstallGroup

class ClusterToInstallGroupMappingForm (forms.ModelForm):
    class Meta:
        fields = ("cluster",)
        model = ClusterToInstallGroupMapping

class DataBaseLocationForm(forms.ModelForm):
    databaseChoice = (
        ('YES', 'YES'),
        ('NO', 'NO'))
    versantStandAlone = forms.CharField(widget=forms.Select(choices=databaseChoice),  label="Versant on VCS cluster")
    mysqlStandAlone = forms.CharField(widget=forms.Select(choices=databaseChoice),  label="MYSQL on VCS cluster")
    postgresStandAlone = forms.CharField(widget=forms.Select(choices=databaseChoice),  label="POSTGRES on VCS cluster")

    class Meta:
        fields = ("versantStandAlone", "mysqlStandAlone", "postgresStandAlone", )
        model = DataBaseLocation

class UpdateMulticastPortsForm(forms.ModelForm):
    class Meta:
        fields =  "__all__"
        model = ServiceGroupInstance

class deployServerForm(forms.Form):
    landscape_definition = forms.FileField()
    landscape_inventory = forms.FileField()

class BuildArtifact(forms.Form):
    '''
    The BuildArtifact class form builds up the Auto deploy Form
    '''
    def __init__(self, sedVersionList,*args, **kwargs):
        super(BuildArtifact, self).__init__(*args, **kwargs)
        self.fields["sedVersion"] = forms.CharField(widget=forms.Select(choices=sedVersionList), label="SED Version")

class NASServerForm(forms.Form):
    '''
    '''
    username = forms.CharField(required=True)
    password = forms.CharField(required=True)

class MultipleIpForm(forms.Form):
    '''
    '''
    vnxChoices = (
        ('5100(vnx1)', '5100(vnx1)'),
        ('5300(vnx1)', '5300(vnx1)'),
        ('5500(vnx1)', '5500(vnx1)'),
        ('5200(vnx2)', '5200(vnx2)'),
        ('5400(vnx2)', '5400(vnx2)'),
        ('5600(vnx2)', '5600(vnx2)'),
        ('450F(unity)', '450F(unity)'))
    name = forms.CharField(label="Machine Name", max_length=30)
    hostname = forms.CharField(required=True)
    domain_name = forms.CharField(required=True)
    vnxType = forms.CharField(widget=forms.Select(choices=vnxChoices), label="VNX Type")
    serial_number = forms.CharField(max_length=18,required=True,help_text="Serial Number of the SAN")
    IpAddress1 = forms.GenericIPAddressField(required=True, label="SP-A IP Address")
    IpAddress2 = forms.GenericIPAddressField(required=True, label="SP-B IP Address")
    username = forms.CharField(required=True)
    password = forms.CharField(required=True)
    sanAdminPassword = forms.CharField(max_length=20,required=False, label="SAN Admin Password")
    sanServicePassword = forms.CharField(max_length=20,required=False, label="SAN Service Password")

class SANForm(forms.Form):
    '''
    '''
    def __init__(self, *args, **kwargs):
        super(SANForm, self).__init__(*args, **kwargs)
        nasSvrsLst = NASServer.objects.values_list('server').distinct()
        nasSvrs = []
        for nasDetails in nasSvrsLst:
            nasSvrs.append(Server.objects.get(id=int(nasDetails[0])))

        naslist = []
        naslist = naslist + [(nas, unicode(nas)) for nas in nasSvrs]
        self.fields['nasServer'] = forms.CharField(widget=forms.Select(choices=naslist))

        storageList = []
        storageList = storageList + [(storage, unicode(storage)) for storage in Storage.objects.all()]
        self.fields['storage'] = forms.CharField(widget=forms.Select(choices=storageList))

class EditSanFormTor(forms.Form):
    '''
    '''
    def __init__(self, *args, **kwargs):
        nasTypes = ( ( "unityxt", "unityxt" ), ( "veritas", "veritas" ),)
        super(EditSanFormTor, self).__init__(*args, **kwargs)
        nasSvrsLst = NASServer.objects.values_list('server').distinct()
        nasSvrs = []
        for nasDetails in nasSvrsLst:
            nasSvrs.append(Server.objects.get(id=int(nasDetails[0])))

        naslist = []
        naslist = naslist + [(nas, unicode(nas)) for nas in nasSvrs]
        self.fields['nasServer'] = forms.CharField(widget=forms.Select(choices=naslist), label="NAS")

        storageList = []
        storageList = storageList + [(storage, unicode(storage)) for storage in Storage.objects.all()]
        self.fields['storage'] = forms.CharField(widget=forms.Select(choices=storageList), label="SAN")

        self.fields['sanPoolId'] = forms.CharField(max_length=10,required=True, label="SAN Pool ID")
        self.fields['sanPoolName'] = forms.CharField(max_length=7,required=True, label="SAN Pool Name")
        self.fields['sanRaidGroup'] = forms.CharField(required=True,label="SAN Raid Group",help_text="The Raid Group the fencing LUN is on")

        self.fields['poolFS1'] = forms.CharField(max_length=7,required=True, label="NAS Pool Name")
        self.fields['fileSystem1'] = forms.CharField(max_length=20,required=False, label="NAS Administrator FS")
        self.fields['fileSystem2'] = forms.CharField(max_length=20,required=False, label="NAS Observer FS")
        self.fields['fileSystem3'] = forms.CharField(max_length=20,required=False, label="NAS Cluster FS")
        self.fields['nasType'] = forms.CharField(widget=forms.Select(choices=nasTypes),max_length=32,required=False,label="NAS Type")
        self.fields['nasNdmpPassword'] = forms.CharField(max_length=20,required=False, label="NAS Ndmp Password")
        self.fields['nasServerPrefix'] = forms.CharField(max_length=20,required=False, label="NAS Server Prefix")

class EditSanFormTorOnRack(EditSanFormTor):
    '''
    '''
    def __init__(self, *args, **kwargs):
        fcSwitchesOpts = ( ( "None", None ), ( "True", True ), ( "False", False ),)
        super(EditSanFormTorOnRack, self).__init__(*args, **kwargs)
        self.fields['fcSwitches'] = forms.CharField(widget=forms.Select(choices=fcSwitchesOpts),required=False,label="FC Switches")
        self.fields['nasEthernetPorts'] = forms.CharField(max_length=20,required=True, label="NAS Ethernet Ports")
        self.fields['sanPoolDiskCount'] = forms.IntegerField(required=True, label="SAN Pool Disk Count")


class EditSanFormOSS(forms.Form):
    '''
    '''
    def __init__(self, *args, **kwargs):
        nasTypes = ( ( "unityxt", "unityxt" ), ( "veritas", "veritas" ),)
        super(EditSanFormOSS, self).__init__(*args, **kwargs)
        nasSvrsLst = NASServer.objects.values_list('server').distinct()
        nasSvrs = []
        for nasDetails in nasSvrsLst:
            nasSvrs.append(Server.objects.get(id=int(nasDetails[0])))

        naslist = []
        naslist = naslist + [(nas, unicode(nas)) for nas in nasSvrs]
        self.fields['nasServer'] = forms.CharField(widget=forms.Select(choices=naslist))

        storageList = []
        storageList = storageList + [(storage, unicode(storage)) for storage in Storage.objects.all()]
        self.fields['storage'] = forms.CharField(widget=forms.Select(choices=storageList))

        self.fields['sanPoolId'] = forms.CharField(max_length=10,required=False, label="SAN Pool ID")
        self.fields['sanPoolName'] = forms.CharField(max_length=30,required=False, label="SAN Pool Name")
        self.fields['poolFS1'] = forms.CharField(max_length=20,required=True, label="NAS Segment One Pool Name")
        self.fields['fileSystem1'] = forms.CharField(max_length=20,required=True, label="NAS Segment One FS")
        self.fields['poolFS2'] = forms.CharField(max_length=20,required=True, label="NAS DDC Pool Name")
        self.fields['fileSystem2'] = forms.CharField(max_length=20,required=True, label="NAS DDC FS")
        self.fields['poolFS3'] = forms.CharField(max_length=20,required=True, label="NAS SGWCG Pool Name")
        self.fields['fileSystem3'] = forms.CharField(max_length=20,required=True, label="NAS SGWCG FS")
        self.fields['nasType'] = forms.CharField(widget=forms.Select(choices=nasTypes),max_length=32,required=False,label="NAS Type")
        self.fields['nasNdmpPassword'] = forms.CharField(max_length=20,required=False, label="NAS Ndmp Password")
        self.fields['nasServerPrefix'] = forms.CharField(max_length=20,required=False, label="NAS Server Prefix")

class EditSanFormOSSOnRack(EditSanFormOSS):
    '''
    '''
    def __init__(self, *args, **kwargs):
        fcSwitchesOpts = ( ( "None", None ), ( "True", True ), ( "False", False ),)
        super(EditSanFormOSSOnRack, self).__init__(*args, **kwargs)
        self.fields['fcSwitches'] = forms.CharField(widget=forms.Select(choices=fcSwitchesOpts),required=False,label="FC Switches")
        self.fields['nasEthernetPorts'] = forms.CharField(max_length=20,required=True, label="NAS Ethernet Ports")
        self.fields['sanPoolDiskCount'] = forms.IntegerField(required=True, label="SAN Pool Disk Count")

class EditClusterOtherPropertiesForm(forms.Form):
    '''
    Used to be able to list all the Other Properties within the cluster
    '''
    ddp_hostname = forms.CharField(max_length=50, required=False, label="DDP Hostname")
    cron = forms.CharField(max_length=10, required=False, label="Cron")
    port = forms.CharField(max_length=4, required=False, label="Port")
    time = forms.CharField(max_length=2, required=False, label="Time", help_text="Nth minute of every hour e.g. 30")

class NASForm(forms.Form):
    '''
    Used to be able to list all the NAS within the system in the dropdown menu so can be
    choosen as a DAS server
    '''
    nasSvrsLst = NASServer.objects.values_list('server').distinct()
    nasSvrs = []
    for nasDetails in nasSvrsLst:
        nasSvrs.append(Server.objects.get(id=int(nasDetails[0])))

    naslist = []
    naslist = naslist + [(nas, unicode(nas)) for nas in nasSvrs]
    nasServer = forms.CharField(widget=forms.Select(choices=naslist))

class EditNASForm(forms.Form):
    '''
    Used to be able to list all the NAS within the system in the dropdown menu so can be
    choosen as a DAS server
    '''
    nasSvrsLst = NASServer.objects.values_list('server').distinct()
    nasSvrs = []
    for nasDetails in nasSvrsLst:
        nasSvrs.append(Server.objects.get(id=int(nasDetails[0])))

    naslist = []
    naslist = naslist + [(nas, unicode(nas)) for nas in nasSvrs]
    nasServer = forms.CharField(widget=forms.Select(choices=naslist))
    poolFS1 = forms.CharField(max_length=20,required=True, label="NAS Pool Name")

class DASForm(forms.Form):
    '''
    '''
    storageList = []
    storageList = storageList + [(storage, unicode(storage)) for storage in Storage.objects.all()]
    storage = forms.CharField(widget=forms.Select(choices=storageList))

class OSSRCForm(forms.Form):
    '''
    '''
    ossrcList = []
    ossrcList = ossrcList + [(ossrcCluster.name, unicode(ossrcCluster.name)) for ossrcCluster in Cluster.objects.filter(management_server__product__name='OSS-RC')]
    ossrcCluster = forms.CharField(widget=forms.Select(choices=ossrcList),label="OSSRC Cluster")

class SedForm(forms.ModelForm):
    '''
    Used to give what entries are displayed on the form
    '''
    user = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="Uploader")
    version = forms.CharField(widget = forms.TextInput(attrs={'readonly':'readonly'}),label="SED Version")
    jiraNumber = forms.CharField(max_length=20,required=True, label="JIRA Number")
    linkText = forms.CharField(max_length=15,required=False, label="ERIcoll SED Link Text")
    link = forms.URLField(label='ERIcoll SED Link')
    sed = forms.CharField(widget=forms.Textarea(attrs={'rows':30, 'cols':100}),label='SED Template')
    def __init__(self, *args, **kwargs):
        super(SedForm, self).__init__(*args, **kwargs)
        isoList = []
        isoList.append(("None","None"))
        isoList = isoList + [(iso.version, unicode(iso.version)) for iso in ISObuild.objects.filter(drop__release__product__name="ENM", mediaArtifact__testware=0, mediaArtifact__category__name="productware").order_by('-build_date')[:30]]
        self.fields["iso"] = forms.CharField(widget=forms.Select(choices=isoList), label="Media Artifact (ISO)")
    class Meta:
        fields = ("user","version","jiraNumber","iso", "linkText", "link", "sed")
        model = Sed

class SedEditForm(forms.ModelForm):
    '''
    Used to give what entries are displayed on the form
    '''
    jiraNumber = forms.CharField(max_length=20,required=True, label="JIRA Number")
    linkText = forms.CharField(max_length=15,required=False, label="ERIcoll SED Link Text")
    link = forms.URLField(label='ERIcoll SED Link')
    def __init__(self, *args, **kwargs):
        super(SedEditForm, self).__init__(*args, **kwargs)
        isoList = []
        isoList.append(("None","None"))
        isoList = isoList + [(iso.version, unicode(iso.version)) for iso in ISObuild.objects.filter(drop__release__product__name="ENM", mediaArtifact__testware=0, mediaArtifact__category__name="productware").order_by('-build_date')[:30]]
        self.fields["iso"] = forms.CharField(widget=forms.Select(choices=isoList), label="Media Artifact (ISO)")
    class Meta:
        fields = ("jiraNumber","iso", "linkText", "link")
        model = Sed


class UploadFileForm(forms.Form):
    clusterId = forms.CharField(max_length=50, label="Deployment ID")
    file = forms.FileField()

class UploadSnapshotForm(forms.Form):
    file = forms.FileField()

class LVSRouterVipForm(forms.ModelForm):
    '''
    Form for LVS Router Vip Information
    '''
    pmInternal = forms.IPAddressField(required=True,label="PM Internal IPv4 VIP",help_text="Internal IPv4 address used by PM applications to route traffic to LVS Router")
    pmExternal = forms.IPAddressField(required=True,label="PM External IPv4 VIP",help_text="External IPv4 address used by PM applications to communicate with the nodes")
    svcPmPublicIpv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="PM External IPv6 VIP",help_text="External IPv6 address used by PM applications to communicate with the nodes (Please input WITHOUT postfix, e.g. /64)")
    fmInternal = forms.IPAddressField(required=True,label="FM Internal IPv4 VIP",help_text="Internal IPv4 address used by FM applications to route traffic to LVS Router")
    fmExternal = forms.IPAddressField(required=True,label="FM External IPv4 VIP",help_text="External IPv4 address used by FM applications to communicate with the nodes")
    fmInternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="FM Internal IPv6 VIP",help_text="Internal IPv6 address used by FM applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    fmExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="FM External IPv6 VIP",help_text="External IPv6 address used by FM applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")

    cmInternal = forms.IPAddressField(required=True,label="CM Internal IPv4 VIP",help_text="Internal IPv4 address used by CM applications to route traffic to LVS Router")
    cmExternal = forms.IPAddressField(required=True,label="CM External IPv4 VIP",help_text="External IPv4 address used by CM applications to communicate with the nodes")
    cmInternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="CM Internal IPv6 VIP",help_text="Internal IPv6 address used by CM applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    cmExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="CM External IPv6 VIP",help_text="External IPv6 address used by CM applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")

    svcPMstorage = forms.IPAddressField(required=True,label="Service PM Storage IPv4",help_text="Storage IPv4 address used by service cluster for PM")
    svcFMstorage = forms.IPAddressField(required=True,label="Service FM Storage IPv4",help_text="Storage IPv4 address used by service cluster for FM")
    svcCMstorage = forms.IPAddressField(required=True,label="Service CM Storage IPv4",help_text="Storage IPv4 address used by service cluster for CM")

    svcStorageInternal = forms.IPAddressField(required=True,label="Service Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by service cluster to route traffic to storage")
    svcStorage = forms.IPAddressField(required=True,label="Service Storage IPv4",help_text="Storage IPv4 address used by service cluster")

    scpSCPinternal = forms.IPAddressField(required=False,label="Scripting SCP Internal IPv4 VIP",help_text="Internal IPv4 address used by SCP applications to route traffic to LVS Router")
    scpSCPexternal = forms.IPAddressField(required=False,label="Scripting SCP External IPv4 VIP",help_text="External IPv4 address used by SCP applications to communicate with the nodes")
    scpSCPinternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Scripting SCP Internal IPv6 VIP",help_text="Internal IPv6 address by SCP applications to route traffic to LVS Router (Optional: Please input WITHOUT postfix, e.g. /64)")
    scpSCPexternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Scripting SCP External IPv6 VIP",help_text="External IPv6 address used by SCP applications to route traffic to LVS Router (Optional: Please input WITHOUT postfix, e.g. /64)")
    scpSCPstorage = forms.IPAddressField(required=False,label="Scripting SCP Storage IPv4",help_text="Storage IPv4 address used by Scripting cluster vms using SCP vip")
    scpStorageInternal = forms.IPAddressField(required=False,label="Scripting Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by scripting cluster to route traffic to storage")
    scpStorage = forms.IPAddressField(required=False,label="Scripting Storage IPv4",help_text="Storage IPv4 address used by scripting cluster")

    evtStorageInternal = forms.IPAddressField(required=False,label="Events Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by event cluster to route traffic to storage")
    evtStorage = forms.IPAddressField(required=False,label="Events Storage IPv4",help_text="Storage IPv4 address used by event cluster")

    strSTRif = forms.CharField(max_length=100,required=False, label="Streaming STR Services Interface")
    strInternal = forms.IPAddressField(required=False,label="Streaming STR Internal IPv4 VIP",help_text="Internal IPv4 address used by STR applications to route traffic to LVS Router")
    strSTRinternal2 = forms.IPAddressField(required=False,label="Streaming STR Internal IPv4 VIP 2",help_text="Internal IPv4 address used by STR applications to route traffic to LVS Router")
    strSTRinternal3 = forms.IPAddressField(required=False,label="Streaming STR Internal IPv4 VIP 3",help_text="Internal IPv4 address used by STR applications to route traffic to LVS Router")
    strExternal = forms.IPAddressField(required=False,label="Streaming STR External IPv4 VIP",help_text="External IPv4 address used by STR applications to communicate with the nodes")
    strSTRexternal2 = forms.IPAddressField(required=False,label="Streaming STR External IPv4 VIP 2",help_text="External IPv4 address used by STR applications to communicate with the nodes")
    strSTRexternal3 = forms.IPAddressField(required=False,label="Streaming STR External IPv4 VIP 3",help_text="External IPv4 address used by STR applications to communicate with the nodes")
    strSTRinternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Streaming STR Internal IPv6 VIP",help_text="Internal IPv6 address used by STR applications to route traffic to LVS Router (Optional: Please input WITHOUT postfix, e.g. /64)")
    strSTRinternalIPv62 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Streaming STR Internal IPv6 VIP 2",help_text="Internal IPv6 address used by STR applications to route traffic to LVS Router (Optional: Please input WITHOUT postfix, e.g. /64)")
    strSTRinternalIPv63 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Streaming STR Internal IPv6 VIP 3",help_text="Internal IPv6 address used by STR applications to route traffic to LVS Router (Optional: Please input WITHOUT postfix, e.g. /64)")
    strExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Streaming STR External IPv6 VIP",help_text="External IPv6 address used by STR applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    strSTRexternalIPv62 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Streaming STR External IPv6 VIP 2",help_text="External IPv6 address used by STR applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    strSTRexternalIPv63 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Streaming STR External IPv6 VIP 3",help_text="External IPv6 address used by STR applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    strSTRstorage = forms.IPAddressField(required=False,label="Streaming STR Storage IPv4",help_text="Storage IPv4 address used by streaming cluster vms using STR vip")
    strStorageInternal = forms.IPAddressField(required=False,label="Streaming Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by streaming cluster to route traffic to storage")
    strStorage = forms.IPAddressField(required=False,label="Streaming Storage IPv4",help_text="Storage IPv4 address used by streaming cluster")

    esnSTRif = forms.CharField(max_length=100,required=False, label="ESN ESN Services Interface")
    esnSTRinternal = forms.IPAddressField(required=False,label="ESN ESN Internal IPv4 VIP",help_text="Internal IPv4 address used by ESN ESN applications to route traffic to LVS Router")
    esnSTRexternal = forms.IPAddressField(required=False,label="ESN ESN External IPv4 VIP",help_text="External IPv4 address used by ESN ESN applications to communicate with the nodes")
    esnSTRinternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="ESN ESN Internal IPv6 VIP",help_text="Internal IPv6 address used by ESN ESN applications to route traffic to LVS Router (Optional: Please input WITHOUT postfix, e.g. /64)")
    esnSTRexternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="ESN ESN External IPv6 VIP",help_text="External IPv6 address used by ESN ESN applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    esnSTRstorage = forms.IPAddressField(required=False,label="ESN ESN Storage IPv4",help_text="Storage IPv4 address used by ESN ESN cluster vms using ESN ESN vip")
    esnStorageInternal = forms.IPAddressField(required=False,label="ESN Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by ESN cluster to route traffic to storage")
    ebsStorage = forms.IPAddressField(required=False,label="EBS Storage IPv4",help_text="Storage IPv4 address used by EBS cluster vms using EBS vip")
    ebsStorageInternal = forms.IPAddressField(required=False,label="EBS Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by EBS cluster to route traffic to storage")
    ebsStrExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="EBS STR External IPv6 VIP",help_text="External IPv6 address used by EBS applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    asrStorage = forms.IPAddressField(required=False,label="ASR Storage IPv4",help_text="Storage IPv4 address used by ASR cluster vms using ASR vip")
    asrAsrStorage = forms.IPAddressField(required=False,label="ASR ASR Storage IPv4",help_text="Storage IPv4 address used by ASR ASR cluster vms using ASR ASR vip")
    asrStorageInternal = forms.IPAddressField(required=False,label="ASR Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by ASR cluster to route traffic to storage")
    asrAsrExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="ASR ASR External IPv6 VIP",help_text="External IPv6 address used by ASR ASR applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    asrAsrInternal = forms.IPAddressField(required=False,label="ASR ASR Internal IPv4 VIP",help_text="Internal IPv4 address used by ASR ASR applications to route traffic to LVS Router")
    asrAsrExternal = forms.IPAddressField(required=False,label="ASR ASR External IPv4 VIP",help_text="External IPv4 address used by ASR ASR  applications to communicate with the nodes")
    ebaStorage = forms.IPAddressField(required=False,label="EBA Storage IPv4",help_text="Storage IPv4 address used by EBA cluster vms using EBA vip")
    ebaStorageInternal = forms.IPAddressField(required=False,label="EBA Storage Gateway Internal IPv4",help_text="Internal IPv4 address used by EBA cluster to route traffic to storage")
    ebaInternal = forms.IPAddressField(required=False, label="EBA Internal IPv4 VIP:",help_text="Internal IPv4 address used by EBA cluster vms using EBA vip")
    ebaInternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False, label="EBA Internal IPv6 VIP:",help_text="Internal IPv6 address used by EBA cluster vms using EBA vip to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    ebaExternal = forms.IPAddressField(required=False, label="EBA External IPv4 VIP", help_text="External IPv4 address used by EBA cluster vms using EBA vip")
    ebaExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False, label="EBA External IPv6 VIP",help_text="External IPv6 address used by EBA cluster vms using EBA vip to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    msossfmInternal = forms.IPAddressField(required=False,label="MSOSSFM Internal IPv4 VIP",help_text="Internal IPv4 address used by MSOSSFM applications to route traffic to LVS Router")
    msossfmExternal = forms.IPAddressField(required=False,label="MSOSSFM External IPv4 VIP",help_text="External IPv4 address used by MSOSSFM applications to communicate with the nodes")
    msossfmInternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="MSOSSFM Internal IPv6 VIP",help_text="Internal IPv6 address used by MS OSSFM applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    msossfmExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="MSOSSFM External IPv6 VIP",help_text="External IPv6 address used by MS OSSFM applications to communicate with the nodes (Optional: Please input WITHOUT postfix, e.g. /64)")
    oranInternal = forms.IPAddressField(required=False, label="ORAN Internal IPv4 VIP", help_text="ORAN Internal IPv4 address")
    oranExternal = forms.IPAddressField(required=False, label="ORAN External IPv4 VIP", help_text="ORAN External IPv4 address")
    oranInternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False, label="ORAN Internal IPv6 VIP", help_text="ORAN Internal IPv6 address")
    oranExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False, label="ORAN External IPv6 VIP", help_text="ORAN External IPv6 address")

    class Meta:
        fields = ("pmInternal", "pmExternal","svcPmPublicIpv6",
                  "fmInternal","fmExternal",
                  "fmInternalIPv6","fmExternalIPv6",
                  "cmInternal","cmExternal",
                  "cmInternalIPv6", "cmExternalIPv6",
                  "svcPMstorage","svcFMstorage", "svcCMstorage",
                  "svcStorageInternal","svcStorage",
                  "scpSCPinternal","scpSCPexternal",
                  "scpSCPinternalIPv6","scpSCPexternalIPv6",
                  'scpSCPstorage',"scpStorageInternal","scpStorage",
                  "evtStorageInternal","evtStorage",
                  "strSTRif","strInternal", "strSTRinternal2", "strSTRinternal3",
                  "strExternal", "strSTRexternal2", "strSTRexternal3",
                  'strSTRinternalIPv6', "strSTRinternalIPv62", "strSTRinternalIPv63",
                  "strExternalIPv6", "strSTRexternalIPv62", "strSTRexternalIPv63",
                  'strSTRstorage', 'strStorageInternal', 'strStorage',
                  "esnSTRif", "esnSTRinternal", "esnSTRexternal",
                  "esnSTRinternalIPv6", "esnSTRexternalIPv6",
                  "esnSTRstorage", "esnStorageInternal",
                  "ebsStorage", "ebsStorageInternal","ebsStrExternalIPv6", "asrStorage",
                  "asrAsrStorage", "asrStorageInternal" ,"asrAsrExternalIPv6", "asrAsrInternal",
                  "asrAsrExternal","ebaStorage", "ebaStorageInternal",
                  "msossfmInternal", "msossfmExternal", "msossfmInternalIPv6", "msossfmExternalIPv6",
                  "ebaInternal","ebaInternalIPv6","ebaExternal","ebaExternalIPv6",
                  "oranInternal", "oranExternal", "oranInternalIPv6", "oranExternalIPv6")
        model = LVSRouterVip


class HybridCloudIPv4Form(forms.ModelForm):
    '''
    Hybrid Cloud for IPv4
    '''
    internal_subnet =  forms.CharField(max_length=18, required=False,label="Internal Subnet IPv4")
    gatewayInternal = forms.IPAddressField(required=False,label="Gateway Private IP IPv4")
    gatewayExternal = forms.IPAddressField(required=False,label="Gateway Public IP IPv4")

    class Meta:
        fields = ("internal_subnet", "gatewayInternal", "gatewayExternal")
        model = HybridCloud


class HybridCloudIPv6Form(forms.ModelForm):
    '''
    Hybrid Cloud for IPv6
    '''
    internal_subnet_ipv6 =  forms.CharField(max_length=42, required=False,label="Internal Subnet IPv6")
    gatewayInternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Gateway Private IP IPv6")
    gatewayExternalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="Gateway Public IP IPv6")

    class Meta:
        fields = ("internal_subnet_ipv6", "gatewayInternalIPv6", "gatewayExternalIPv6")
        model = HybridCloud

class DvmsInformationForm(forms.ModelForm):
    '''
    DVMS Information for Deployment
    '''
    externalIPv4 = forms.IPAddressField(required=True,label="External IPv4 Address")
    externalIPv6 = forms.CharField(validators=[validate_ipv6_address],max_length=60,required=False,label="External IPv6 Address",help_text="NOTE: IPv6 is not yet supported.")
    internalIPv4 = forms.IPAddressField(required=True,label="Internal IPv4 Address")

    class Meta:
        fields = ("externalIPv4", "externalIPv6", 'internalIPv4')
        model = DvmsInformation


class UploadDeploymentFileForm(forms.Form):
    '''
    For upload deployment file
    '''
    file = forms.FileField()


class DeploymentDatabaseProviderForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(DeploymentDatabaseProviderForm, self).__init__(*args, **kwargs)
        typesList = []
        typesList = typesList + [(type, type) for type in str(config.get("DMT", "database_providers")).split()]
        self.fields['dpsPersistenceProvider'] = forms.CharField(widget=forms.Select(choices=typesList),required=True, label="DPS Persistence Provider")
