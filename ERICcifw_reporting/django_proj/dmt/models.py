from django.db import models
from django import forms
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from cireports.models import ISObuild, ProductSetVersion
import re
from netaddr import IPNetwork, IPAddress
# Create your models here.
# By default, Django gives each model the following field: id = models.AutoField(primary_key=True)
# This is an auto-incrementing primary key, which sets the id to an Integer Field.
# TODO: Update when Django AutoField supports multiple int types

import logging
logger = logging.getLogger(__name__)

#used to remove leading and trailing whitespace
def clean_up(self):
    for field in self._meta.fields:
        if isinstance(field, (models.CharField, models.TextField)):
            current_field = getattr(self, field.name)
            if current_field:
                setattr(self, field.name, current_field.strip())

def validate_domain(domain):
    if domain[-1:] == ".": # A single trailing dot is legal
        domain = domain[:-1] # strip exactly one dot from the right, if present
    if domain[-1:] == ".": # Multiple trailing dots are illegal
        raise ValidationError("Error: Domain name seems to be ending with multiple \".\"" )
    # Regular Expression
        # contains at least one character and a maximum of 63 characters
        # consists only of allowed characters
        # doesn't begin or end with a hyphen
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    for x in domain.split("."):
        if not allowed.match(x):
            raise ValidationError("Error: Character length has exceeded 63 characters or illegal character inputted for :" + str(x))
            break


def validate_ipv6_address(ipaddress):
    '''
    '''
    if ipaddress == "":
        return
    ipv6_address_cidr = re.compile('^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(([0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4})*)?)::(([0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4})*)?))/(\d|\d\d|1[0-1]\d|12[0-8])$')
    ipv6_address = re.compile('^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(([0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4})*)?)::(([0-9A-Fa-f]{1,4}(:[0-9A-Fa-f]{1,4})*)?))$')
    ipv6_validation = re.match(ipv6_address,ipaddress)
    ipv6_cidr_validation = re.match(ipv6_address_cidr,ipaddress)

    if ipv6_validation != None or ipv6_cidr_validation != None:
        return
    else:
        raise ValidationError("Error: Please Enter a Valid IPV6 address")

class Credentials (models.Model):
    # id field  = unsigned integer
    username = models.CharField(max_length=10)
    password = models.CharField(max_length=50)
    credentialType = models.CharField(max_length=20, null=True, blank=True)
    loginScope = models.CharField(max_length=20, null=True, blank=True)

    def __unicode__(self):
        return str(self.username) + " --> " + str(self.credentialType)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(Credentials, self).save(*args, **kwargs)

class Server (models.Model):
    # id field  = unsigned integer
    HWTYPES = ( ( "cloud", "cloud" ), ( "virtual", "virtual" ), ("rack", "rack"), ("blade", "blade"),)
    name = models.CharField(max_length=30)
    hostname = models.CharField(max_length=30)
    hostnameIdentifier = models.CharField(max_length=50,default='1')
    domain_name = models.CharField(validators=[validate_domain], max_length=100)
    dns_serverA = models.GenericIPAddressField()
    dns_serverB = models.GenericIPAddressField()
    hardware_type = models.CharField(max_length=20, choices=HWTYPES)

    class Meta:
        unique_together = (
                ('hostname', 'hostnameIdentifier'),)

    def __unicode__(self):
        return str(self.hostname) + " (id: " + str(self.id) + ")"

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(Server, self).save(*args, **kwargs)

class ManagementServer (models.Model):
    '''
    Class representing a management server, which is responsible for managing
    one or more clusters.
    '''
    # id field  = unsigned smallint
    server = models.OneToOneField(Server)
    description = models.TextField()
    product = models.ForeignKey('cireports.Product')

    def __unicode__(self):
        return str(self.server.hostname) + " (id: " + str(self.id) + ")"

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(ManagementServer, self).save(*args, **kwargs)

class VirtualManagementServer (models.Model):
    '''
    Class representing a virtual management server mapping to MgtServer.
    '''
    # id field  = unsigned smallint
    server = models.OneToOneField(Server)
    mgtServer = models.OneToOneField(ManagementServer)
    product = models.ForeignKey('cireports.Product')

    def __unicode__(self):
        return "Virtual Mgt Server " + str(self.server) + " Mapped to " + str(self.mgtServer)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(VirtualManagementServer, self).save(*args, **kwargs)

class HardwareDetails (models.Model):
    '''
    Class used to associate hardware size details to a server
    '''
    # id field  = unsigned smallint
    ram = models.CharField(max_length=10)
    diskSize = models.CharField(max_length=10)
    server = models.OneToOneField(Server)

    def __unicode__(self):
        return "Server " + str(server) + " Ram: " + str(ram) + " Disk Size " + str(diskSize)

class HardwareIdentity (models.Model):
    '''
    Class used to associate hardware identity number to a server
    '''
    # id field  = unsigned smallint
    wwpn = models.CharField(max_length=23)
    ref = models.CharField(max_length=5)
    server = models.OneToOneField(Server)

    def __unicode__(self):
        return "Server " + str(server) + " WWPN: " + str(wwpn)

class ProductToServerTypeMapping (models.Model):
    '''
    Class used to register new Server types per Project
    '''
    # id field  = unsigned integer
    product = models.ForeignKey('cireports.Product')
    serverType = models.CharField(max_length=50)

    def __unicode__(self):
        return str(self.product) + " (" + str(self.serverType) + ")"

class DeploymentStatusTypes (models.Model):
    '''
    Class representing a deployment Status Types.
    '''
    # id field  = unsigned smallint
    status = models.CharField(max_length=20, unique=True)

    def __unicode__(self):
        return str(self.status)

    class Meta:
        verbose_name_plural="Deployment Status Types"

class ClusterLayout (models.Model):
    '''
    Class representing a cluster Layouts.
    '''
    # id field  = unsigned smallint
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()

    def __unicode__(self):
        return str(self.name)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(ClusterLayout, self).save(*args, **kwargs)

class EnmDeploymentType (models.Model):
    '''
    Class representing ENM Deployment Type.
    '''
    # id field  = unsigned smallint
    name = models.CharField(max_length=40, unique=True)

    def __unicode__(self):
        return str(self.name)

class IpVersion (models.Model):
    '''
    Class representing ip versions.
    '''
    # id field  = unsigned smallint
    name = models.CharField(max_length=15, unique=True)

    def __unicode__(self):
        return str(self.name)

class Cluster (models.Model):
    '''
    Class representing a cluster of nodes.
    '''
    # id field  = unsigned smallint
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    tipc_address = models.PositiveIntegerField(unique=True)
    management_server = models.ForeignKey(ManagementServer)
    compact_audit_logger = models.NullBooleanField(default=None, null=True)
    dhcp_lifetime = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group, blank=True, null=True)
    # Low and high values for MAC addresses for virtual nodes
    # in this cluster
    mac_lowest = models.CharField(max_length=18, blank=True, null=True)
    mac_highest = models.CharField(max_length=18, blank=True, null=True)
    layout = models.ForeignKey(ClusterLayout)
    component = models.ForeignKey('cireports.Component', blank=True, null = True)
    enmDeploymentType = models.ForeignKey(EnmDeploymentType, blank=True, null=True)
    ipVersion = models.ForeignKey(IpVersion, blank=True, null=True)

    class Meta:
        permissions = (
                ('change_cluster_guardian', 'Change cluster_guardian'),
                ('delete_cluster_guardian', 'Delete cluster_guardian'),
                )

    def __unicode__(self):
        return str(self.name) + " (" + str(self.management_server) + ")"

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(Cluster, self).save(*args, **kwargs)

class DeploymentStatus (models.Model):
    '''
    Class representing a Deployment Status of Cluster.
    '''
    # id field  = unsigned smallint
    status = models.ForeignKey(DeploymentStatusTypes)
    cluster = models.OneToOneField(Cluster)
    status_changed = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    osDetails =  models.CharField(max_length=100, null=True, blank=True)
    litpVersion =  models.CharField(max_length=50, null=True, blank=True)
    mediaArtifact = models.CharField(max_length=100, null=True, blank=True)
    packages = models.TextField(null=True, blank=True)
    patches = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return str(self.cluster) + " (" + str(self.status) + ")"

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(DeploymentStatus, self).save(*args, **kwargs)

class ClusterServer (models.Model):
    '''
    Class representing a node, or server.
    '''
    # id field  = unsigned integer
    server = models.OneToOneField(Server)
    node_type = models.CharField(max_length=50)
    cluster = models.ForeignKey(Cluster)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return str(self.server.hostname) + " (" + str(self.cluster) + ")"

class DataBaseLocation (models.Model):
    '''
    Class used to model the required options to decide where to put the Databases on the system.
    '''
    # id field  = unsigned smallint
    versantStandAlone = models.CharField(max_length=3, default="YES")
    mysqlStandAlone = models.CharField(max_length=3, default="YES")
    postgresStandAlone = models.CharField(max_length=3, default="YES")
    cluster = models.ForeignKey(Cluster, null=True, blank=True)

    def __unicode__(self):
        return "Database Location For " + str(self.cluster)

class IpRangeItem (models.Model):
    '''
    Class used to register an install ip range item
    '''
    # id field  = unsigned integer
    ip_range_item = models.CharField(max_length=50,unique=True)

    def __unicode__(self):
        return str(self.ip_range_item)

class IpRange (models.Model):
    '''
    Class used to group your ip ranges
    '''
    # id field  = unsigned integer
    ip_range_item = models.ForeignKey(IpRangeItem)
    start_ip = models.GenericIPAddressField(unique=True)
    end_ip = models.GenericIPAddressField(unique=True)
    bitmask = models.CharField(max_length=2, null=True, blank=True)
    gateway = models.GenericIPAddressField(null=True, blank=True)

    def __unicode__(self):
        return "Item : " + str(self.ip_range_item) + ". Start  Ip (" + str(self.start_ip) + ") End Ip (" + str(self.end_ip) + ")"

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        if self.bitmask and "/" in self.bitmask:
            self.bitmask = self.bitmask.replace("/","")
        else:
            self.bitmask = self.bitmask
        super(IpRange, self).save(*args, **kwargs)

class InstallGroup (models.Model):
    '''
    Class used to register an install Group
    '''
    # id field  = unsigned smallint
    installGroup = models.CharField(max_length=50)

    def __unicode__(self):
        return str(self.installGroup)

class ClusterToInstallGroupMapping (models.Model):
    '''
    Class used to group your cluster into a certain group for installation
    '''
    # id field  = unsigned smallint
    cluster = models.ForeignKey(Cluster, unique=True, verbose_name='Attach Deployment')
    group = models.ForeignKey(InstallGroup)
    status = models.ForeignKey(DeploymentStatus)

    class Meta:
        unique_together = (('cluster', 'group'),)

    def __unicode__(self):
        return str(self.cluster) + " (" + str(self.group) + ")"

class NASServer (models.Model):
    # id field  = unsigned integer
    server = models.OneToOneField(Server)
    credentials = models.ForeignKey(Credentials)
    sfs_node1_hostname = models.CharField(max_length=100)
    sfs_node2_hostname = models.CharField(max_length=100)

    def __unicode__(self):
        return str(self.server)

class ClusterToDASNASMapping (models.Model):
    '''
    Table to be able to map DAS for a NAS to a cluster
    '''
    # id field  = unsigned integer
    cluster = models.ForeignKey(Cluster)
    dasNasServer = models.ForeignKey(Server)

    def __unicode__(self):
        return "Cluster: " +str(self.cluster)+ " to NAS: " +str(self.dasNasServer)+ " Mapping."

class ClusterToNASMapping (models.Model):
    # id field  = unsigned integer
    cluster = models.ForeignKey(Cluster)
    nasServer = models.ForeignKey(NASServer)

    def __unicode__(self):
        return "Cluster: " +str(self.cluster)+ " to NAS: " +str(self.nasServer)+ " Mapping."

class NasStorageDetails (models.Model):
    # id field  = unsigned integer
    NASTYPES = ( ( "unityxt", "unityxt" ), ( "veritas", "veritas" ),)
    sanPoolId = models.CharField(max_length=10)
    sanPoolName = models.CharField(max_length=30)
    sanRaidGroup = models.PositiveIntegerField(null=True, blank=True)
    poolFS1 = models.CharField(max_length=20, null=True, blank=True)
    fileSystem1 = models.CharField(max_length=20, null=True, blank=True)
    poolFS2 = models.CharField(max_length=20, null=True, blank=True)
    fileSystem2 = models.CharField(max_length=20, null=True, blank=True)
    poolFS3 = models.CharField(max_length=20, null=True, blank=True)
    fileSystem3 = models.CharField(max_length=20, null=True, blank=True)
    nasType = models.CharField(max_length=32, null=True, blank=True, choices=NASTYPES)
    nasNdmpPassword = models.CharField(max_length=100, null=True, blank=True)
    nasServerPrefix = models.CharField(max_length=50, null=True, blank=True)
    fcSwitches = models.NullBooleanField(null=True, blank=True)
    nasEthernetPorts = models.CharField(max_length=30,default="0,2")
    sanPoolDiskCount = models.PositiveIntegerField(max_length=10,default=15)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return str(self.cluster)

    class Meta:
        verbose_name_plural="Nas Storage Details"

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(NasStorageDetails, self).save(*args, **kwargs)


class DeploymentDatabaseProvider (models.Model):
    '''
    class used to add Database Provider to Deployment
    '''
    # id field  = unsigned integer
    cluster = models.ForeignKey(Cluster)
    dpsPersistenceProvider =  models.CharField(max_length=50, default="versant")

    def __unicode__(self):
        return str(self.cluster) + "- DPS Persistence Provider: " + str(self.dpsPersistenceProvider)

    class Meta:
        unique_together = ( ('cluster', 'dpsPersistenceProvider'),)


class VlanMulticastType (models.Model):
    '''
    Types of Vlan Multicast
    '''
    name = models.CharField(max_length=10, unique=True)
    description = models.TextField()

    def __unicode__(self):
        return str(self.name) + " --> "  + str(self.description)

class VlanMulticast (models.Model):
    '''
    VLAN Multicast
    '''
    values = ( ( "0", "0" ), ( "1", "1" ),)
    routerValues = ( ( "0", "0" ), ( "1", "1" ), ("2", "2"),)
    hashValues = ( ( "512", "512" ), ( "1024", "1024" ), ("2048", "2048"), ("4096", "4096"), ("8192", "8192"),)
    # id field  = unsigned integer
    clusterServer = models.ForeignKey(ClusterServer)
    multicast_type = models.ForeignKey(VlanMulticastType)
    multicast_snooping = models.CharField(max_length=1, choices=values)
    multicast_querier = models.CharField(max_length=1, choices=values)
    multicast_router = models.CharField(max_length=1, choices=routerValues)
    hash_max = models.CharField(max_length=20, choices=hashValues)

    class Meta:
        unique_together = ( ('clusterServer', 'multicast_type'),)

    def __unicode__(self):
        return "DepolymentServer: " +str(self.clusterServer) + " --> Type: " +str(self.multicast_type)

class VlanClusterMulticast (models.Model):
    '''
    VLAN Multicast Details for Cluster
    '''
    values = ( ( "0", "0" ), ( "1", "1" ),)
    routerValues = ( ( "0", "0" ), ( "1", "1" ), ("2", "2"),)
    hashValues = ( ( "512", "512" ), ( "1024", "1024" ), ("2048", "2048"), ("4096", "4096"), ("8192", "8192"),)
    # id field  = unsigned integer
    cluster = models.ForeignKey(Cluster)
    multicast_type = models.ForeignKey(VlanMulticastType)
    multicast_snooping = models.CharField(max_length=1, choices=values)
    multicast_querier = models.CharField(max_length=1, choices=values)
    multicast_router = models.CharField(max_length=1, choices=routerValues)
    hash_max = models.CharField(max_length=20, choices=hashValues)

    class Meta:
        unique_together = ( ('cluster', 'multicast_type'),)

    def __unicode__(self):
        return "Deployment: " +str(self.cluster) + " --> Type: " +str(self.multicast_type)

class NetworkInterface (models.Model):
    # id field  = unsigned integer
    mac_address = models.CharField(max_length=18, unique=True)
    interface = models.CharField(max_length=5, default="eth0")
    nicIdentifier = models.CharField(max_length=50,default='1')
    server = models.ForeignKey(Server)

    class Meta:
        unique_together = (
                ('mac_address', 'nicIdentifier'),)

    def __unicode__(self):
        return self.mac_address

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(NetworkInterface, self).save(*args, **kwargs)

class VmServiceIpRangeItem (models.Model):
    # id field = unsigned integer
    ipType = models.CharField(max_length=50,unique=True)
    ipDescription = models.CharField(max_length=255)

    def __unicode__(self):
        return str(self.ipType)+ ", Description " + str(self.ipDescription)

class VmServiceIpRange (models.Model):
    # id field = unsigned integer
    ipv4AddressStart=models.IPAddressField(null=True, blank=True)
    ipv4AddressEnd=models.IPAddressField(null=True, blank=True)
    ipv6AddressStart = models.GenericIPAddressField(null=True, blank=True)
    ipv6AddressEnd = models.GenericIPAddressField(null=True, blank=True)
    ipTypeId = models.ForeignKey(VmServiceIpRangeItem)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return "Cluster: " +str(self.cluster)+ ", Ip Range for " + str(self.ipTypeId) +"."

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(VmServiceIpRange, self).save(*args, **kwargs)

class AutoVmServiceDnsIpRange (models.Model):
    # id field = unsigned integer
    ipv4AddressStart=models.IPAddressField(null=True, blank=True)
    ipv4AddressEnd=models.IPAddressField(null=True, blank=True)
    ipv6AddressStart = models.GenericIPAddressField(null=True, blank=True)
    ipv6AddressEnd = models.GenericIPAddressField(null=True, blank=True)
    ipTypeId = models.ForeignKey(VmServiceIpRangeItem)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return "Cluster: " +str(self.cluster)+ ", Ip Range for " + str(self.ipTypeId) +"."

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(AutoVmServiceDnsIpRange, self).save(*args, **kwargs)

class IpAddress (models.Model):
    # id field = unsigned integer
    address = models.IPAddressField(null=True, blank=True)
    ipv4UniqueIdentifier = models.CharField(max_length=50,default='1')
    bitmask = models.CharField(max_length=4,default=None, null=True, blank=True)
    ipv6_address = models.GenericIPAddressField(null=True, blank=True)
    ipv6UniqueIdentifier = models.CharField(max_length=50,default='1')
    ipv6_bitmask = models.CharField(max_length=4,default=None, null=True, blank=True)
    ipv6_gateway = models.GenericIPAddressField(null=True, blank=True)
    gateway_address = models.GenericIPAddressField(null=True, blank=True)
    interface =  models.CharField(max_length=5, null=True, blank=True)
    netmask = models.IPAddressField(null=True, blank=True)
    nic = models.ForeignKey(NetworkInterface, null=True, blank=True)
    ipType = models.CharField(max_length=50,default=None, null=True, blank=True)
    override = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural="Ip addresses"

    def __unicode__(self):
        if self.address:
            return self.address
        if self.ipv6_address:
            return self.ipv6_address

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        if self.ipv6_address and '/' in self.ipv6_address:
            self.ipv6_address = self.ipv6_address.split('/')[0]
        if self.bitmask and "/" in self.bitmask:
            self.bitmask = self.bitmask.replace("/","")
        else:
            self.bitmask = self.bitmask
        if self.ipv6_bitmask and "/" in self.ipv6_bitmask:
            self.ipv6_bitmask = self.ipv6_bitmask.replace("/","")
        else:
            self.ipv6_bitmask = self.ipv6_bitmask
        if self.checkForDuplicateIpInfo():
            if not self.override:
                if self.address:
                    raise Exception("Duplicate IP Entry '"+self.address+"'")
                else:
                    raise Exception("Duplicate IP Entry '"+self.ipv6_address+"'")

        super(IpAddress, self).save(*args, **kwargs)

    def checkForDuplicateIpInfo(self):
        '''
        This function checks IpAddresses about to be saved to to DB. If they are duplicates then the value will only be saved if both Virtual Machines are members of the same consolidated group
        '''
        id = self.id
        if id is not None:
            currentIp = IpAddress.objects.get(id=id)
            if self.address:
                if self.address != currentIp.address:
                    if IpAddress.objects.filter(address=self.address, ipv4UniqueIdentifier=self.ipv4UniqueIdentifier).exists():
                        return True
                elif IpAddress.objects.filter(address=self.address, ipv4UniqueIdentifier=self.ipv4UniqueIdentifier).count()>1:
                    return True
            else:
                if currentIp.ipv6_address and '/' in currentIp.ipv6_address:
                    currentIp.ipv6_address = currentIp.ipv6_address.split('/')[0]
                else:
                    currentIp.ipv6_address = currentIp.ipv6_address
                if int(IPAddress(self.ipv6_address)) != int(IPAddress(currentIp.ipv6_address)):
                    if IpAddress.objects.filter(ipv6_address=self.ipv6_address, ipv6UniqueIdentifier=self.ipv6UniqueIdentifier).exists():
                        return True
                elif IpAddress.objects.filter(ipv6_address=self.ipv6_address, ipv6UniqueIdentifier=self.ipv6UniqueIdentifier).count()>1:
                    return True
        else:
            if self.address:
                if IpAddress.objects.filter(address=self.address, ipv4UniqueIdentifier=self.ipv4UniqueIdentifier).exists():
                    return True
            else:
                if IpAddress.objects.filter(ipv6_address=self.ipv6_address, ipv6UniqueIdentifier=self.ipv6UniqueIdentifier).exists():
                    return True
        return False

class InternalIpAddress (models.Model):
    # id field = unsigned integer
    address = models.IPAddressField(unique=False)
    bitmask = models.CharField(max_length=4,default=None, null=True, blank=True)
    ipv6_address = models.GenericIPAddressField(unique=False, null=True, blank=True)
    ipv6_bitmask = models.CharField(max_length=4,default=None, null=True, blank=True)
    ipv6_gateway = models.GenericIPAddressField(null=True, blank=True)
    gateway_address = models.GenericIPAddressField(null=True, blank=True)
    nic = models.ForeignKey(NetworkInterface, null=True, blank=True)
    ipType = models.CharField(max_length=50,default=None, null=True, blank=True)

    def __unicode__(self):
        return self.address

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        if self.bitmask and "/" in self.bitmask:
            self.bitmask = self.bitmask.replace("/","")
        else:
            self.bitmask = self.bitmask
        if self.ipv6_bitmask and "/" in self.ipv6_bitmask:
            self.ipv6_bitmask = self.ipv6_bitmask.replace("/","")
        else:
            self.ipv6_bitmask = self.ipv6_bitmask
        super(InternalIpAddress, self).save(*args, **kwargs)


class VlanDetails (models.Model):
    '''
    class used to add the Heart Beat Vlan Tag for systems across two enclosures
    '''
    # id field  = unsigned integer
    services_subnet = models.CharField(max_length=18)
    services_gateway = models.IPAddressField()
    services_ipv6_gateway = models.GenericIPAddressField(null=True, blank=True)
    services_ipv6_subnet = models.CharField(max_length=42, null=True, blank=True)
    storage_subnet = models.CharField(max_length=18)
    storage_gateway = models.ForeignKey(IpAddress,related_name='storage_gateway', null=True)
    backup_subnet = models.CharField(max_length=18)
    jgroups_subnet = models.CharField(max_length=18)
    internal_subnet = models.CharField(max_length=18)
    internal_ipv6_subnet = models.CharField(max_length=42, null=True, blank=True)
    storage_vlan = models.IntegerField(null=True, blank=True)
    backup_vlan = models.IntegerField(null=True, blank=True)
    jgroups_vlan = models.IntegerField(null=True, blank=True)
    internal_vlan = models.IntegerField(null=True, blank=True)
    services_vlan = models.IntegerField(null=True, blank=True)
    management_vlan = models.IntegerField(null=True, blank=True)
    litp_management = models.CharField(max_length=18)
    hbAVlan = models.IntegerField(null=True, blank=True)
    hbBVlan= models.IntegerField(null=True, blank=True)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return "Cluster: " +str(self.cluster)+ " Vlan Details."

    def clean(self):
        logger.info('cleaning form...')
        clean_up(self)

    def save(self, *args, **kwargs):
        super(VlanDetails, self).save(*args, **kwargs)

class VirtualConnectNetworks (models.Model):
    '''
    class Used to set the Virtual Connect data
    '''
    # id field  = unsigned smallint
    sharedUplinkSetA = models.CharField(max_length=50, default="OSS1_Shared_Uplink_A")
    sharedUplinkSetB = models.CharField(max_length=50, default="OSS1_Shared_Uplink_B")
    servicesA = models.CharField(max_length=50, default="ENM_services_A")
    servicesB = models.CharField(max_length=50, default="ENM_services_B")
    storageA = models.CharField(max_length=50, default="ENM_storage_A")
    storageB = models.CharField(max_length=50, default="ENM_storage_B")
    backupA = models.CharField(max_length=50, default="ENM_backup_A")
    backupB = models.CharField(max_length=50, default="ENM_backup_B")
    jgroups = models.CharField(max_length=50, default="ENM_jgroups")
    jgroupsA = models.CharField(max_length=50, default="ENM_jgroups_A")
    jgroupsB = models.CharField(max_length=50, default="ENM_jgroups_B")
    internalA = models.CharField(max_length=50, default="ENM_internal_A")
    internalB = models.CharField(max_length=50, default="ENM_internal_B")
    heartbeat1 = models.CharField(max_length=50, default="ENM_heartbeat1")
    heartbeat2 = models.CharField(max_length=50, default="ENM_heartbeat2")
    heartbeat1A = models.CharField(max_length=50, default="ENM_heartbeat1_A")
    heartbeat2B = models.CharField(max_length=50, default="ENM_heartbeat2_B")
    vlanDetails = models.ForeignKey(VlanDetails)

    def __unicode__(self):
        return "VlanDetails: " +str(self.vlanDetails)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(VirtualConnectNetworks, self).save(*args, **kwargs)


class VlanIPMapping (models.Model):
    '''
    class used to map the vlan tag to an IP within the Ip Address table
    '''
    # id field = unsigned integer
    vlanTag = models.PositiveIntegerField(max_length=10)
    ipMap= models.ForeignKey(IpAddress)

    def __unicode__(self):
        return "Vlan Tag: " +str(self.vlanTag)+ " to Ip: " +str(self.ipMap) + " Mapping."

class InternalVlanIPMapping (models.Model):
    '''
    class used to map the vlan tag to an IP within the Ip Address table
    '''
    # id field = unsigned integer
    vlanTag = models.PositiveIntegerField(max_length=10)
    ipMap= models.ForeignKey(InternalIpAddress)

    def __unicode__(self):
        return "Vlan Tag: " +str(self.vlanTag)+ " to Ip: " +str(self.ipMap) + " Mapping."

class Storage (models.Model):
    # id field = unsigned integer
    name = models.CharField(max_length=30)
    hostname = models.CharField(max_length=30, unique=True)
    domain_name = models.CharField(validators=[validate_domain], max_length=100)
    serial_number = models.CharField(max_length=18, unique=True)
    vnxType = models.CharField(max_length=100,default="vnx1")
    credentials = models.ForeignKey(Credentials)
    sanAdminPassword = models.CharField(max_length=100,null=True,blank=True)
    sanServicePassword = models.CharField(max_length=100,null=True,blank=True)

    def __unicode__(self):
        return str(self.hostname)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(Storage, self).save(*args, **kwargs)

class StorageIPMapping (models.Model):
    # id field = unsigned integer
    storage = models.ForeignKey(Storage)
    ipaddr = models.ForeignKey(IpAddress)
    ipnumber = models.IntegerField()

class Enclosure (models.Model):
    '''
    The Enclosure form allows a db entry for blade enclouse data.
    An Enclosure houses the pyhsicial blades/servers
    '''
    # id field = unsigned integer
    hostname = models.CharField(max_length=30, unique=True)
    domain_name = models.CharField(validators=[validate_domain], max_length=100)
    vc_domain_name = models.CharField(validators=[validate_domain], max_length=100)
    rackName = models.CharField(max_length=32)
    name = models.CharField(max_length=32)
    credentials = models.ForeignKey(Credentials,related_name='enclosure')
    vc_credentials = models.ForeignKey(Credentials,related_name='vcenclosure', null=True, blank=True)
    uplink_A_port1 = models.CharField(max_length=30)
    uplink_A_port2 = models.CharField(max_length=30)
    uplink_B_port1 = models.CharField(max_length=30)
    uplink_B_port2 = models.CharField(max_length=30)
    san_sw_bay_1 = models.CharField(max_length=2,null=True,blank=True)
    san_sw_bay_2 = models.CharField(max_length=2,null=True,blank=True)
    vc_module_bay_1 = models.CharField(max_length=2,null=True,blank=True)
    vc_module_bay_2 = models.CharField(max_length=2,null=True,blank=True)
    sanSw_credentials = models.ForeignKey(Credentials,related_name='sanSwenclosure', null=True, blank=True)

    def __unicode__(self):
        return str(self.hostname)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(Enclosure, self).save(*args, **kwargs)

class EnclosureIPMapping (models.Model):
    # id field = unsigned integer
    enclosure = models.ForeignKey(Enclosure)
    ipaddr = models.ForeignKey(IpAddress)
    ipnumber = models.IntegerField()

class ClusterToStorageMapping (models.Model):
    # id field = unsigned integer
    cluster = models.ForeignKey(Cluster)
    storage = models.ForeignKey(Storage)

    def __unicode__(self):
        return "Cluster: " +str(self.cluster)+ " to Storage: " +str(self.storage)+ " Mapping."

class OssrcClusterToTorClusterMapping (models.Model):
    # id field = unsigned integer
    ossCluster = models.ForeignKey(Cluster)
    torCluster = models.ForeignKey(Cluster,related_name='+')

    def __unicode__(self):
        return "OSSRC Cluster: " +str(self.ossCluster)+ " to ENM Cluster: " +str(self.torCluster)+ " Mapping."

class ClusterToDASMapping (models.Model):
    # id field = unsigned integer
    cluster = models.ForeignKey(Cluster)
    storage = models.ForeignKey(Storage)

    def __unicode__(self):
        return "Cluster: " +str(self.cluster)+ " to Storage: " +str(self.storage)+ " Mapping."

class SsoDetails (models.Model):
    '''
    Used to gather the Extra SSO information
    '''
    # id field = unsigned integer
    cluster = models.ForeignKey(Cluster)
    ldapDomain = models.CharField(max_length=100, null=True, blank=True)
    ldapPassword = models.CharField(max_length=100, null=True, blank=True)
    opendjAdminPassword = models.CharField(max_length=100, null=True, blank=True)
    openidmAdminPassword = models.CharField(max_length=100, null=True, blank=True)
    openidmMysqlPassword = models.CharField(max_length=100, null=True, blank=True)
    securityAdminPassword = models.CharField(max_length=100, null=True, blank=True)
    hqDatabasePassword = models.CharField(max_length=100, null=True, blank=True)
    ossFsServer = models.CharField(max_length=100, null=True, blank=True)
    citrixFarm = models.CharField(max_length=100)
    brsadm_password = models.CharField(max_length=100, null=True, blank=True)

    def __unicode__(self):
        return "Cluster " +str(self.cluster)+ " SSO info " + str(self.ldapDomain)


class BladeHardwareDetails (models.Model):
    '''
    The BladeHardwareDetails class allows extra blade information required to be added to the db
    '''
    # id field = unsigned integer
    mac_address = models.ForeignKey(NetworkInterface)
    serial_number = models.CharField(max_length=18, unique=True)
    profile_name = models.CharField(max_length=100)
    enclosure = models.ForeignKey(Enclosure)
    vlan_tag = models.PositiveIntegerField(null=True, blank=True, max_length=10)

    def __unicode__(self):
        return str(self.mac_address)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(BladeHardwareDetails, self).save(*args, **kwargs)

class RackHardwareDetails (models.Model):
    '''
    The RackHardwareDetails class allows extra rack information required to be added to the db
    '''
    # id field = unsigned integer
    clusterServer = models.ForeignKey(ClusterServer)
    serial_number = models.CharField(max_length=18, unique=True)
    bootdisk_uuid = models.CharField(max_length=32, unique=True)

    def __unicode__(self):
        return str(self.clusterServer)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(RackHardwareDetails, self).save(*args, **kwargs)

class ServicesCluster (models.Model):
    # id field = integer
    cluster_type = models.CharField(max_length=50,null=True)
    name = models.CharField(max_length=50,null=True)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return str(self.cluster)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(ServicesCluster, self).save(*args, **kwargs)

class Multicast (models.Model):
    '''
    Multicast addresses are used for JBoss clustering among other
    things.

    Multicast addresses are defined per cluster here, but in generating
    the XML they go into the JEE container definition.
    '''
    # id field = integer
    ipMapDefaultAddress = models.ForeignKey(IpAddress,related_name='defaultAddress')
    ipMapMessagingGroupAddress = models.ForeignKey(IpAddress,related_name='messagingAddress')
    ipMapUdpMcastAddress = models.ForeignKey(IpAddress,related_name='udpAddress')
    udp_mcast_port = models.PositiveIntegerField(max_length=5, unique=True)
    ipMapMpingMcastAddress = models.ForeignKey(IpAddress,related_name='mpingAddress')
    default_mcast_port = models.PositiveIntegerField(max_length=5, unique=True, null=True, blank=True)
    mping_mcast_port = models.PositiveIntegerField(max_length=5, unique=True)
    messaging_group_port = models.PositiveIntegerField(max_length=5, unique=True)
    public_port_base = models.PositiveIntegerField(max_length=5)
    service_cluster = models.ForeignKey(ServicesCluster)

    def __unicode__(self):
        return str(self.service_cluster)

class ClusterMulticast (models.Model):
    '''
    Multicast addresses are used for JBoss clustering among other
    things.
    '''
    # id field = integer
    enm_messaging_address = models.ForeignKey(IpAddress,related_name='enmMessagingAddress')
    enm_messaging_port = models.PositiveIntegerField(max_length=5,unique=True)
    udp_multicast_address = models.ForeignKey(IpAddress,related_name='UdpMulticastAddress')
    udp_multicast_port = models.PositiveIntegerField(max_length=5,unique=True)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return str(self.cluster.name)

class DatabaseVips (models.Model):
    '''
    Vip addresses are used for the application to talk to the db's
    '''
    # id field = unsigned smallint
    postgres_address = models.ForeignKey(IpAddress,related_name='postgresAddress')
    versant_address = models.ForeignKey(IpAddress,related_name='versantAddress')
    mysql_address = models.ForeignKey(IpAddress,related_name='mysqlAddress')
    opendj_address = models.ForeignKey(IpAddress,related_name='opendjAddress')
    opendj_address2 = models.ForeignKey(IpAddress,related_name='opendjAddress2', null=True)
    jms_address = models.ForeignKey(IpAddress,related_name='jmsAddress', null=True, blank=True)
    eSearch_address = models.ForeignKey(IpAddress,related_name='eSearchAddress', null=True, blank=True)
    neo4j_address1 = models.ForeignKey(IpAddress,related_name='neo4jAddress1', null=True)
    neo4j_address2 = models.ForeignKey(IpAddress,related_name='neo4jAddress2', null=True)
    neo4j_address3 = models.ForeignKey(IpAddress,related_name='neo4jAddress3', null=True)
    gossipRouter_address1 = models.ForeignKey(IpAddress,related_name='gossipRouterAddress1', null=True)
    gossipRouter_address2 = models.ForeignKey(IpAddress,related_name='gossipRouterAddress2', null=True)
    eshistory_address = models.ForeignKey(IpAddress,related_name='eshistoryAddress', null=True)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return str(self.cluster.name)

class DatabaseVip (models.Model):
    '''
    Vip addresses are used for the application to talk to the db's
    Depreciated new table created DatabaseVips
    '''
    # id field = unsigned smallint
    postgres_address = models.ForeignKey(InternalIpAddress,related_name='postgresAddress')
    versant_address = models.ForeignKey(InternalIpAddress,related_name='versantAddress')
    mysql_address = models.ForeignKey(InternalIpAddress,related_name='mysqlAddress')
    opendj_address = models.ForeignKey(InternalIpAddress,related_name='opendjAddress')
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return str(self.cluster.name)

class VirtualImage (models.Model):
    '''
    VirtualImage for defining number of virtual machines within the cluster
    '''
    # id field = unsigned integer
    name = models.CharField(max_length=50)
    node_list = models.CharField(max_length=50)
    cluster = models.ForeignKey(Cluster)

    class Meta:
        #To stop Duplicate entries
        unique_together = ('name', 'cluster')

    def __unicode__(self):
        return str(self.name) + " --> " + str(self.node_list) + " --> " + str(self.cluster)

class VirtualImageItems (models.Model):
    '''
    VirtualImageItems used to be able to add new Virtual images through the admin
    '''
    # id field = unsigned smallint
    values = ( ( "jboss", "jboss" ), ( "httpd", "httpd" ), )
    choicesLayout = ( ( "Virtual Machine", "Virtual Machine" ), ( "Bare Metal Image", "Bare Metal Image" ), )
    name = models.CharField(max_length=50,unique=True)
    type = models.CharField(max_length=20,choices=values)
    layout = models.CharField(max_length=50,choices=choicesLayout)
    active = models.BooleanField(default=1)

    def __unicode__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural="Virtual Image Items"

class VirtualImageInfoIp (models.Model):
    '''
    Function used to map the ip addresses to the virtual machine
    '''
    # id field = unsigned integer
    number = models.CharField(max_length=50)
    hostname = models.TextField(null=True, blank=False)
    virtual_image = models.ForeignKey(VirtualImage, related_name='virtualImageInfoIp')
    ipMap = models.ForeignKey(IpAddress, null=True, blank=False, related_name='virtualImageInfoIpAddress')

    def __unicode__(self):
        return str(self.number) + " --> " + str(self.virtual_image)

class VirtualImageIPInfo (models.Model):
    '''
    Function used to map the ip addresses to the virtual machine
    Depreciated new table created VirtualImageInfoIp
    '''
    # id field = integer
    number = models.CharField(max_length=50)
    hostname = models.CharField(max_length=30, null=True, blank=False)
    virtual_image = models.ForeignKey(VirtualImage)
    ipMap = models.ForeignKey(IpAddress, null=True, blank=False)
    ipMapInternal = models.ForeignKey(InternalIpAddress, null=True, blank=False)

    def __unicode__(self):
        return str(self.number) + " --> " + str(self.virtual_image)

class VirtualImageCredentialMapping (models.Model):
    '''
    Mapping to allow Users and Passwords to Virtual Image
    '''
    # id field = unsigned integer
    virtualimage = models.ForeignKey(VirtualImage, related_name='virtualImageCredentialMappingToVirtualImage')
    credentials = models.ForeignKey(Credentials, related_name='virtualImageCredentialMappingToCredentials')
    signum = models.CharField(max_length=10)
    date_time  = models.DateTimeField()

    def __unicode__(self):
        return "Virtual Image: --> " + str(self.virtualimage) + " Credentials " + str(self.credentials)


class ServiceGroup (models.Model):
    '''
    Service Group for defining number of service instance
    '''
    # id field = integer
    name = models.CharField(max_length=50)
    cluster_type = models.CharField(max_length=50)
    node_list = models.CharField(max_length=50)
    service_cluster = models.ForeignKey(ServicesCluster)

    def __unicode__(self):
        return str(self.service_cluster)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(ServiceGroup, self).save(*args, **kwargs)

class ServiceGroupTypes (models.Model):
    # id field = unsigned smallint
    group_type = models.CharField(max_length=50)

    def __unicode__(self):
        return str(self.group_type)

class ServiceGroupUnit (models.Model):
    # id field = unsigned smallint
    service_unit = models.CharField(max_length=50,unique=True)
    group_type = models.ForeignKey(ServiceGroupTypes)

    def __unicode__(self):
        return str(self.service_unit) + " --> " + str(self.group_type.group_type)

class JbossClusterServiceGroup (models.Model):
    # id field = unsigned smallint
    name = models.CharField(max_length=50,unique=True)

    def __unicode__(self):
        return str(self.name)

class ServiceGroupPackageMapping (models.Model):
    # id field = integer
    serviceGroup = models.ForeignKey(ServiceGroup)
    package = models.ForeignKey('cireports.Package')

    def __unicode__(self):
        return str(self.serviceGroup) + " --> " + str(self.package)

class ServiceInstance (models.Model):
    '''
    An instance of a CMW service that is not a JBoss Service Instance.
    in the ATT / ENM 1.0 release, Apache will be supported. further types
    will be introduced in the future.
    '''
    # id field = integer
    name = models.CharField(max_length=50)
    service_group = models.ForeignKey(ServiceGroup)

    def __unicode__(self):
        return str(self.name) + " --> " + str(self.type)

class ServiceGroupInstance (models.Model):
    '''
    An instance of a JBoss Container modelled as a CMW Service Instance.
    MulticastPorts are used for JBoss clustering among other things.
    '''
    # id field = integer
    name = models.CharField(max_length=50)
    hostname = models.CharField(max_length=30, null=True, blank=False)
    service_group = models.ForeignKey(ServiceGroup)
    ipMap = models.ForeignKey(IpAddress)

    def __unicode__(self):
        return str(self.service_group)

class ServiceGroupInstanceInternal (models.Model):
    '''
    An instance of a JBoss Container modelled as a CMW Service Instance.
    MulticastPorts are used for JBoss clustering among other things.
    '''
    # id field = unsigned integer
    name = models.CharField(max_length=50)
    service_group = models.ForeignKey(ServiceGroup)
    ipMap = models.ForeignKey(IpAddress)

    def __unicode__(self):
        return str(self.service_group)

class InternalServiceGroupInstance (models.Model):
    '''
    An instance of a JBoss Container modelled as a CMW Service Instance.
    MulticastPorts are used for JBoss clustering among other things.
    Depreciated new table created ServiceGroupInstanceInternal
    '''
    # id field = integer
    name = models.CharField(max_length=50)
    service_group = models.ForeignKey(ServiceGroup)
    ipMap = models.ForeignKey(InternalIpAddress)

    def __unicode__(self):
        return str(self.service_group)

class ServiceGroupCredentialMapping (models.Model):
    '''
    Mapping to allow Users add Users and Passwords to Service Unit
    '''
    # id field = unsigned integer
    service_group = models.ForeignKey(ServiceGroup)
    credentials = models.ForeignKey(Credentials)
    signum = models.CharField(max_length=10)
    date_time  = models.DateTimeField()

    def __unicode__(self):
        return u'Cluster: %s --> Service Group Name: %s --> Username: %s --> Type: %s'%(str(self.service_group),str(self.service_group.name),str(self.credentials.username),str(self.credentials.credentialType))


class VeritasCluster (models.Model):
    # id field = integer
    ipMapCSG = models.ForeignKey(IpAddress,related_name='CSG')
    csgNic = models.CharField(max_length=10)
    ipMapGCO = models.ForeignKey(IpAddress,related_name='GCO')
    gcoNic = models.CharField(max_length=10)
    lltLink1 = models.CharField(max_length=10)
    lltLink2 = models.CharField(max_length=10)
    lltLinkLowPri1 = models.CharField(max_length=10)
    cluster = models.ForeignKey(Cluster)

    def __unicode__(self):
        return str(self.cluster)

class Ilo (models.Model):
    '''
    A physical server may have an ILO (Integrated Lights Out)
    '''
    # id field = unsigned integer
    ipMapIloAddress = models.ForeignKey(IpAddress)
    server = models.ForeignKey(Server, unique=True)
    username = models.CharField(max_length=10, null=True, blank=True)
    password = models.CharField(max_length=50, null=True, blank=True)

    def __unicode__(self):
        return str(self.ipMapIloAddress) + " Ilo Address for server " + str(self.server)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(Ilo, self).save(*args, **kwargs)

### VM RELATED

# Create your models here.
class AppTemplate (models.Model):
    # id field = unsigned smallint
    name = models.CharField(max_length=30)
    desc = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.name

class AppHost (models.Model):
    # id field = unsigned smallint
    VALUES = ( ( "gateway", "gateway" ), ( "generic", "generic" ), )
    template = models.ForeignKey(AppTemplate)
    name     = models.CharField(max_length=30)
    hostname = models.CharField(max_length=30)
    type     = models.CharField(max_length=20, choices=VALUES)

    def __unicode__(self):
        return self.name + ": " + self.type

class AppIpAddress (models.Model):
    # id field = unsigned smallint
    VALUES = ( ('ipv4', 'ipv4'), ('ipv6', 'ipv6'),)
    value = models.CharField(max_length=30)
    mode = models.CharField(max_length=20, choices=VALUES)

    def __unicode__(self):
        return self.value

    class Meta:
        verbose_name_plural="App ip addresses"

class AppHostIpMap (models.Model):
    # id field = unsigned smallint
    apphost = models.ForeignKey (AppHost)
    ip_addr = models.ForeignKey (AppIpAddress)
    def __unicode__(self):
        return self.apphost.name + " - " + self.ip_addr.value

class KGBAppInstance (models.Model):
    # id field = unsigned integer
    STATES = ( ( 'live', 'live' ), ( 'quarantined', 'quarantined' ), ( 'destroyed', 'destroyed' ), )
    template = models.ForeignKey(AppTemplate)
    aut      = models.ForeignKey('cireports.PackageRevision')
    state    = models.CharField(max_length=20, choices=STATES)
    comment  = models.TextField(null=True, blank=True)
    vappid   = models.CharField(max_length=100)
    def __unicode__(self):
        return self.template.name + ": " + str(self.aut) + " - " + self.state

class ClusterQueue (models.Model):
    # id field = integer (The Default)
    dateInserted = models.DateTimeField(null=True, blank=False)
    clusterGroup = models.CharField(max_length=50, null=True, blank=False)
    def __unicode__(self):
        return unicode(self.dateInserted)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(ClusterQueue, self).save(*args, **kwargs)

class Sed (models.Model):
    # id field = unsigned INT(10)
    dateInserted = models.DateTimeField(default=timezone.now)
    user = models.CharField(max_length=10)
    version = models.CharField(max_length=10,unique=True)
    jiraNumber = models.CharField(max_length=20)
    sed = models.TextField(null=True, blank=False)
    linkText = models.CharField(max_length=15)
    link = models.TextField()
    iso  = models.ForeignKey('cireports.ISObuild', blank=True, null=True)
    def __unicode__(self):
        return self.version + " Created : " + str(self.dateInserted)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(Sed, self).save(*args, **kwargs)

class SedMaster (models.Model):
    # id field = unsigned smallint
    identifer = models.CharField(max_length=20)
    sedMaster  = models.ForeignKey (Sed,related_name='sedmaster_to_sed')
    sedMaster_virtual  = models.ForeignKey (Sed,related_name='sedmaster_virtual_to_sed')
    dateUpdated = models.DateTimeField(default=timezone.now, null=True, blank=False)
    sedUser = models.CharField(max_length=10, null=True, blank=False)
    def __unicode__(self):
        return self.identifer + " : " + str(self.sedMaster.version) + ":" + str(self.sedMaster_virtual.version)

    def clean(self):
        clean_up(self)

class ManagementServerCredentialMapping (models.Model):
    '''
    Mapping to allow Users add Users and Passwords to management server
    '''
    # id field = unsigned integer
    mgtServer = models.ForeignKey(ManagementServer)
    credentials = models.ForeignKey(Credentials)
    signum = models.CharField(max_length=10)
    date_time  = models.DateTimeField()

    def __unicode__(self):
        return u'Management Server: %s -->  Username: %s --> Type: %s'%(str(self.mgtServer.server.hostname),str(self.credentials.username),str(self.credentials.credentialType))

class VirtualMSCredentialMapping (models.Model):
    '''
    Mapping to allow Users add Users and Passwords to management server
    '''
    # id field = unsigned integer
    virtualMgtServer = models.ForeignKey(VirtualManagementServer)
    credentials = models.ForeignKey(Credentials)
    signum = models.CharField(max_length=10)
    date_time  = models.DateTimeField(null=True)

    def __unicode__(self):
        return u'Management Server: %s --> Virtual Management Server: %s -->  Username: %s --> Type: %s'%(str(self.virtualMgtServer.mgtServer.server.hostname), str(self.virtualMgtServer.server.hostname),str(self.credentials.username),str(self.credentials.credentialType))

class ClusterServerCredentialMapping (models.Model):
    '''
    Mapping to allow Users add Users and Passwords to Cluster Server
    '''
    # id field = unsigned integer
    clusterServer = models.ForeignKey(ClusterServer)
    credentials = models.ForeignKey(Credentials)
    signum = models.CharField(max_length=10)
    date_time  = models.DateTimeField()

    def __unicode__(self):
        return u'Cluster: %s --> Cluster Server: %s -->  Username: %s --> Type: %s'%(str(self.clusterServer.cluster),str(self.clusterServer.server.hostname),str(self.credentials.username),str(self.credentials.credentialType))


class UserTypes (models.Model):
    '''
    User Types for Credentials
    '''
    # id field = unsigned smallint
    name = models.CharField(max_length=20,unique=True)

    def __unicode__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural="User Types"

class DeployPackageExemptionList (models.Model):
    '''
    Table used through the admin page to add packages, that are allowed to be kgb using a snapshot package.
    '''
    # id field = unsigned smallint
    packageName = models.CharField(max_length=250,unique=True)

    def __unicode__(self):
        return str(self.packageName)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(DeployPackageExemptionList, self).save(*args, **kwargs)

class VirtualAutoBuildlogClusters (models.Model):
    '''
    Table used to catologue the autobuildlog virtual clusters.
    '''
    name = models.CharField(max_length=50, null=False, blank=True)

    def __unicode__(self):
        return str(self.name)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        super(VirtualAutoBuildlogClusters, self).save(*args, **kwargs)

class DeploymentBaseline(models.Model):
    '''
    Class representing a Deployment Baseline model
    '''
    createdAt = models.DateTimeField(default=datetime.now, editable=False, blank=True)
    updatedAt = models.DateTimeField(auto_now=True)
    clusterName = models.CharField(max_length=100, null=True, blank=True)
    clusterID = models.CharField(max_length=100, null=True, blank=True)
    osDetails =  models.CharField(max_length=100, null=True, blank=True)
    litpVersion =  models.CharField(max_length=50, null=True, blank=True)
    mediaArtifact = models.CharField(max_length=100, null=True, blank=True)
    fromISO = models.CharField(max_length=100, null=True, blank=True)
    fromISODrop = models.CharField(max_length=100, null=True, blank=True)
    upgradePerformancePercent = models.CharField(max_length=5, null=True, blank=True)
    patches = models.TextField(null=True, blank=True)
    dropName = models.CharField(max_length=100, null=True, blank=True)
    groupName = models.CharField(max_length=100, null=True, blank=True)
    sedVersion = models.CharField(max_length=100, null=True, blank=True)
    deploymentTemplates = models.CharField(max_length=100, null=True, blank=True)
    tafVersion = models.CharField(max_length=100, null=True, blank=True)
    descriptionDetails = models.CharField(max_length=100, null=True, blank=True)
    masterBaseline  = models.BooleanField(default=False)
    success  = models.BooleanField(default=True)
    productset_id = models.CharField(max_length=50, null=False, blank=True)
    deliveryGroup = models.CharField(max_length=3000, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    rfaStagingResult = models.CharField(max_length=2000, null=True, blank=True)
    rfaResult = models.CharField(max_length=2000, null=True, blank=True)
    teAllureLogUrl = models.CharField(max_length=200, null=True, blank=True)
    upgradeAvailabilityResult = models.CharField(max_length=2000, null=True, blank=True)
    availability = models.CharField(max_length=50, null=True, blank=True)
    buildURL = models.CharField(max_length=200, null=True, blank=True)
    upgradeTestingStatus = models.CharField(max_length=100, null=True, blank=True)
    rfaPercent = models.CharField(max_length=5, null=True, blank=True)
    shortLoopURL = models.CharField(max_length=100, null=True, blank=True)
    installType = models.CharField(max_length=100, null=False, blank=True)
    deploytime = models.CharField(max_length=50, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    slot = models.IntegerField(default=0)

    def __unicode__(self):
        return str(self.clusterName)

    def clean(self):
        clean_up(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        super(DeploymentBaseline, self).save(*args, **kwargs)

class IpmiVersionMapping(models.Model):
    '''
    Class used to map the deployscript version to a drop or else use the master
    '''
    reference = models.CharField(max_length=20,unique=True)
    version = models.CharField(max_length=20,unique=True)

    def __unicode__(self):
        return "IPMI Version " + str(self.version) + " mapped to " + str(self.reference)

class RedfishVersionMapping(models.Model):
    '''
    Class used to map the deployscript version to a drop or else use the master
    '''
    reference = models.CharField(max_length=20,unique=True)
    version = models.CharField(max_length=20,unique=True)

    def __unicode__(self):
        return "Redfish Version " + str(self.version) + " mapped to " + str(self.reference)

class DeployScriptMapping(models.Model):
    '''
    Class used to map the deployscript version to a drop or else use the master
    '''
    reference = models.CharField(max_length=20,unique=True)
    version = models.CharField(max_length=20,unique=True)

    def __unicode__(self):
        return "Deployment Script " + str(self.version) + " mapped to " + str(self.reference)

class redHatArtifactToVersionMapping(models.Model):
    '''
    Class used to be able to map the Red Hat media artifacts to a version (6.6_x86 etc)
    '''
    mediaArtifact = models.ForeignKey('cireports.MediaArtifact')
    artifactReference = models.CharField(max_length=100,unique=True)

    def __unicode__(self):
        return str(self.mediaArtifact) + " mapped to " + str(self.artifactReference)

class DeploymentTestcase(models.Model):
    '''
    Class used to input in testcase to be ran against a deployment to check the server utilization
    '''
    # id field  = unsigned smallint
    testcase_description = models.CharField(max_length=255,null=True,blank=False)
    testcase = models.TextField()
    enabled = models.BooleanField(default=False)

    def __unicode__(self):
        return "Description: " + str(self.testcase_description) + ", Is Enabled: " + str(self.enabled)

class MapTestResultsToDeployment(models.Model):
    '''
    Class used to map the test results to the deployment
    '''
    # id field  = unsigned int
    cluster = models.ForeignKey(Cluster)
    testcase_description = models.CharField(max_length=255,null=True,blank=False)
    testcase = models.TextField()
    result = models.BooleanField(default=False)
    testDate = models.DateTimeField(null=True, blank=False)
    testcaseOutput = models.TextField(null=True, blank=False)
    def __unicode__(self):
        return str(self.cluster) + " " + str(self.testcase) + " (Passed " + str(self.result) + ") on " + str(self.testDate)

class TestGroup (models.Model):
    '''
    Class used to register an install Group
    '''
    # id field  = unsigned smallint
    defaultGroup = models.BooleanField(default=False)
    testGroup = models.CharField(max_length=50)

    def __unicode__(self):
        return str(self.testGroup)

    def save(self, *args, **kwargs):
        if self.defaultGroup:
            try:
                temp = TestGroup.objects.get(defaultGroup=True)
                if self != temp:
                    temp.defaultGroup = False
                    temp.save()
            except TestGroup.DoesNotExist:
                pass
        super(TestGroup, self).save(*args, **kwargs)

class MapTestGroupToDeployment(models.Model):
    '''
    Class used to map a test Group to Deployments
    '''
    # id field  = unsigned smallint
    cluster = models.ForeignKey(Cluster)
    group = models.ForeignKey(TestGroup)

    def __unicode__(self):
        return str(self.group) + " mapped to Deployment " + str(self.cluster)

class LVSRouterVip (models.Model):
    '''
    LVSRouter VIP addresses are used for routing FM, CM and PM traffic across the cluster
    '''

    # id field = unsigned smallint
    cluster = models.ForeignKey(Cluster)
    pm_internal = models.ForeignKey(IpAddress,related_name='pmInternal')
    pm_external = models.ForeignKey(IpAddress,related_name='pmExternal')
    fm_internal = models.ForeignKey(IpAddress,related_name='fmInternal')
    fm_external = models.ForeignKey(IpAddress,related_name='fmExternal')
    fm_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='fmInternalIPv6')
    fm_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='fmExternalIPv6')
    cm_internal = models.ForeignKey(IpAddress,related_name='cmInternal')
    cm_external = models.ForeignKey(IpAddress,related_name='cmExternal')
    cm_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='cmInternalIPv6')
    cm_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='cmExternalIPv6')
    svc_pm_storage = models.ForeignKey(IpAddress,related_name='svcPMstorage')
    svc_fm_storage = models.ForeignKey(IpAddress,related_name='svcFMstorage')
    svc_cm_storage = models.ForeignKey(IpAddress,related_name='svcCMstorage')
    svc_storage_internal = models.ForeignKey(IpAddress,related_name='svcStorageInternal')
    svc_storage = models.ForeignKey(IpAddress,related_name='svcStorage')
    scp_scp_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='scpSCPinternal')
    scp_scp_external = models.ForeignKey(IpAddress,null=True,blank=True,related_name='scpSCPexternal')
    scp_scp_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='scpSCPinternalIPv6')
    scp_scp_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='scpSCPexternalIPv6')
    scp_scp_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='scpSCPstorage')
    scp_storage_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='scpStorageInternal')
    scp_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='scpStorage')
    evt_storage_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='evtStorageInternal')
    evt_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='evtStorage')
    str_str_if = models.CharField(max_length=100, null=True,blank=True)
    str_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strInternal')
    str_str_internal_2 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRInternal2')
    str_str_internal_3 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRInternal3')
    str_external = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strExternal')
    str_str_external_2 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRExternal2')
    str_str_external_3 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRExternal3')
    str_str_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRinternalIPv6')
    str_str_internal_ipv6_2 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRinternalIPv62')
    str_str_internal_ipv6_3 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRinternalIPv63')
    str_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strExternalIPv6')
    str_str_external_ipv6_2 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRexternalIPv62')
    str_str_external_ipv6_3 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRexternalIPv63')
    str_str_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strSTRstorage')
    str_storage_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strStorageInternal')
    str_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='strStorage')
    esn_str_if = models.CharField(max_length=100, null=True,blank=True)
    esn_str_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='esnSTRInternal')
    esn_str_external = models.ForeignKey(IpAddress,null=True,blank=True,related_name='esnSTRExternal')
    esn_str_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='esnSTRinternalIPv6')
    esn_str_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='esnSTRexternalIPv6')
    esn_str_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='esnSTRstorage')
    esn_storage_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='esnStorageInternal')
    ebs_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebsStorage')
    ebs_storage_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebsStorageInternal')
    ebs_str_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebsStrExternalIPv6')
    asr_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='asrStorage')
    asr_storage_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='asrStorageInternal')
    asr_asr_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='asrAsrStorage')
    asr_asr_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='asrAsrExternalIPv6')
    asr_asr_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='asrAsrInternal')
    asr_asr_external = models.ForeignKey(IpAddress,null=True,blank=True,related_name='asrAsrExternal')
    eba_storage = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebaStorage')
    eba_storage_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebaStorageInternal')
    msossfm_external = models.ForeignKey(IpAddress,null=True,blank=True,related_name='msossfmExternal')
    msossfm_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='msossfmExternalIPv6')
    msossfm_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='msossfmInternal')
    msossfm_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='msossfmInternalIPv6')

    def __unicode__(self):
        return str(self.cluster.name)

class LVSRouterVipExtended (models.Model):
    '''
    LVSRouter VIP addresses are used for routing FM, CM and PM traffic across the cluster
    '''
    # id field = unsigned smallint
    cluster = models.ForeignKey(Cluster)
    eba_external = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebaExternal')
    eba_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebaExternalIPv6')
    eba_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebaInternal')
    eba_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='ebaInternalIPv6')
    svc_pm_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='svcPmPublicIpv6')
    oran_internal = models.ForeignKey(IpAddress,null=True,blank=True,related_name='oranInternal')
    oran_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='oranInternalIPv6')
    oran_external = models.ForeignKey(IpAddress,null=True,blank=True,related_name='oranExternal')
    oran_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True,related_name='oranExternalIPv6')

    def __unicode__(self):
        return str(self.cluster.name)

class DeploymentUtilities (models.Model):
    '''
    The DeploymentUtilities Model represents the Utilities that are associated with a Product Set that are not part of the Product Set an example would be the autodeploy SED
    '''
    utility = models.CharField(max_length=50, unique=True)

    def __unicode__(self):
        return str(self.utility)

class DeploymentUtilitiesVersion (models.Model):
    '''
    The DeploymentUtilitiesVersion Model represents the version of the DeploymentUtility and an optional Label which is used to Represent the Utility Visually
    '''
    utility_name = models.ForeignKey(DeploymentUtilities)
    utility_version = models.CharField(max_length=50)
    utility_label = models.CharField(max_length=50,null=True,blank=True)

    class Meta:
        unique_together = ('utility_name', 'utility_version',)

    def __unicode__(self):
        return str(self.utility_name) + " " + str(self.utility_version)

class DeploymentUtilsToISOBuild (models.Model):
    '''
    The DeploymentUtilsToISOBuild Model Mapping table represents the utilities that are contained within an ISOBuild
    '''
    # id field = unsigned INT(10)
    utility_version = models.ForeignKey(DeploymentUtilitiesVersion)
    iso_build       = models.ForeignKey(ISObuild)
    active          = models.BooleanField(default=True)

    def __unicode__(self):
        return str(self.iso_build) + " " + str(self.utility_version) + " " + str(self.active)

class DeploymentUtilsToProductSetVersion (models.Model):
    '''
    The DeploymentUtilsToProductSetVersion Model Mapping table represents the utilities that are contained within an Product Set
    '''

    utility_version    = models.ForeignKey(DeploymentUtilitiesVersion)
    productSetVersion  = models.ForeignKey(ProductSetVersion)
    active             = models.BooleanField(default=True)

    def __unicode__(self):
        return str(self.productSetVersion) + " " + str(self.utility_version) + " " + str(self.active)

class DeploymentDhcpJumpServerDetails (models.Model):
    '''
    The DeploymentDhcpJumpServerDetails Model table repersents the details of the DHCP and Jump Servers used for Deployments
    '''
    server_type = models.CharField(max_length=50)
    server_user = models.CharField(max_length=50)
    server_password = models.CharField(max_length=50)
    ecn_ip = models.IPAddressField(null=True, blank=True)
    edn_ip = models.IPAddressField(null=True, blank=True)
    youlab_ip = models.IPAddressField(null=True, blank=True)
    gtec_edn_ip = models.IPAddressField(null=True, blank=True)
    gtec_youlab_ip = models.IPAddressField(null=True, blank=True)

class ConsolidatedToConstituentMap(models.Model):
    '''
    Class used to map Consolidated Service Group types to Constituent Service Groups types
    '''
    # id field  = unsigned smallint
    consolidated = models.CharField(max_length=50)
    constituent = models.CharField(max_length=50)

class VmServiceName(models.Model):
    '''
    Name of Service only
    '''
    # id field  = unsigned smallint
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return str(self.name)

class VmServicePackageMapping(models.Model):
    '''
    Service Package Mapping
    '''
    # id field  = unsigned int
    service = models.ForeignKey(VmServiceName)
    package = models.ForeignKey('cireports.Package')
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return str(self.service) + " - " + str(self.package) + " --> " + str(self.active)

class PackageRevisionServiceMapping (models.Model):
    # id field = unsigned integer
    package_revision        = models.ForeignKey('cireports.PackageRevision')
    service                 = models.ForeignKey(VmServiceName)

    def __unicod__(self):
        return str(self.package_revision) + ": " + str(self.service)

class MediaArtifactServiceScanned (models.Model):
    # id field = unsigned integer
    media_artifact_version  = models.CharField(max_length=15, unique=True)
    scanned_date = models.DateTimeField(default=datetime.now)

    def __unicod__(self):
        return str(self.media_artifact_version) + ": " + str(self.scanned_date)

class HybridCloud(models.Model):
    '''
    Hybrid  Cloud
    '''
    IPTYPES = ( ( 'ipv4', 'ipv4' ), ( 'ipv6', 'ipv6' ), )
    # id field  = unsigned smallint
    cluster = models.ForeignKey(Cluster)
    ip_type = models.CharField(max_length=5, choices=IPTYPES)
    internal_subnet = models.CharField(max_length=18, null=True,blank=True)
    gateway_internal = models.ForeignKey(IpAddress,null=True,blank=True, related_name='gatewayInternal')
    gateway_external = models.ForeignKey(IpAddress,null=True,blank=True, related_name='gatewayExternal')
    internal_subnet_ipv6 = models.CharField(max_length=42, null=True, blank=True)
    gateway_internal_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True, related_name='gatewayInternalIPv6')
    gateway_external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True, related_name='gatewayExternalIPv6')

    def __unicode__(self):
        return str(self.cluster) + " --> " + str(self.ip_type)

class DvmsInformation(models.Model):
    '''
    Dvms Information
    '''
    # id field  = unsigned smallint
    cluster = models.ForeignKey(Cluster)
    external_ipv4 = models.ForeignKey(IpAddress,null=True,blank=True, related_name='externalIPv4')
    external_ipv6 = models.ForeignKey(IpAddress,null=True,blank=True, related_name='externalIPv6')
    internal_ipv4 = models.ForeignKey(IpAddress,null=True,blank=True, related_name='internalIPv4')

    def __unicode__(self):
        return str(self.cluster) + " --> " + str(self.external_ipv4) + " " + str(self.external_ipv6) + " " + str(self.internal_ipv4)


class DeploymentDescriptionType(models.Model):
    '''
    Deployment Description Type
    '''
    # id field  = unsigned smallint
    dd_type = models.CharField(max_length=20)

    def __unicode__(self):
        return str(self.dd_type)

class DeploymentDescriptionVersion(models.Model):
    '''
    Deployment Description version
    '''
    # id field  = unsigned smallint
    version = models.CharField(max_length=100)
    latest = models.BooleanField(default=True)

    def __unicode__(self):
        return str(self.version) + "--> Latest: " + str(self.latest)

class DeploymentDescription(models.Model):
    '''
    Deployment Description
    '''
    # id field  = unsigned int
    CATACITYTYPES = ( ( 'test', 'test' ), ( 'production', 'production' ), )
    version = models.ForeignKey(DeploymentDescriptionVersion)
    dd_type = models.ForeignKey(DeploymentDescriptionType)
    name = models.CharField(max_length=200)
    capacity_type =  models.CharField(default="test", max_length=12, null=True,blank=True, choices=CATACITYTYPES)
    auto_deployment = models.CharField(max_length=255)
    sed_deployment = models.CharField(max_length=255)

    def __unicode__(self):
        return str(self.name) + " --> " +str(self.version) + " --> " + str(self.dd_type) + " --> Auto: " + str(self.auto_deployment) + " --> SED: " + str(self.sed_deployment)

class DDtoDeploymentMapping(models.Model):
    '''
    Deployment Description to Cluster/Deployment Mapping
    '''
    UPDATETYPES = ( ( 'complete', 'complete' ), ( 'partial', 'partial' ), )
    IPRANGETYPES = ( ( 'dns', 'dns' ), ( 'manual', 'manual' ), )
    # id field  = unsigned smallint
    deployment_description = models.ForeignKey(DeploymentDescription)
    cluster = models.ForeignKey(Cluster)
    auto_update = models.BooleanField(default=False)
    update_type = models.CharField(max_length=20, null=True,blank=True, choices=UPDATETYPES)
    iprange_type =  models.CharField(default="dns", max_length=20, null=True,blank=True, choices=IPRANGETYPES)

    def __unicode__(self):
        return str(self.cluster) + " --> " + str(self.deployment_description) + " --> AutoUpdate: " + str(self.auto_update) + " --> IpRangeType: " +str(self.iprange_type)

class UpdatedDeploymentSummaryLog(models.Model):
    '''
    Summary Log for Updated Deployments
    '''
    createdDate = models.DateTimeField(default=datetime.now)
    dd_version = models.ForeignKey(DeploymentDescriptionVersion)

    def __unicode__(self):
        return str(self.createdDate) + " --> " +str(self.dd_version)

class UpdatedDeploymentLog(models.Model):
    '''
    Log for Updated Deployment
    '''
    STATUSTYPES = ( ( 'successful', 'successful' ), ( 'failed', 'failed' ), )
    summary_log = models.ForeignKey(UpdatedDeploymentSummaryLog, null=True, blank=True)
    cluster = models.ForeignKey(Cluster)
    createdDate = models.DateTimeField(default=datetime.now)
    deployment_description = models.ForeignKey(DeploymentDescription)
    log = models.TextField()
    status = models.CharField(max_length=20, choices=STATUSTYPES)

    def __unicode__(self):
        return str(self.createdDate) + " --> " + str(self.cluster) + " --> " + str(self.deployment_description) + "--> Summary: " + str(self.summary_log)

class ClusterAdditionalInformation(models.Model):
    '''
    Cluster DPP Mapping
    '''
    # id field = unsigned smallint
    cluster                 = models.ForeignKey(Cluster)
    ddp_hostname            = models.CharField(max_length=50)
    cron                    = models.CharField(max_length=50)
    port                    = models.CharField(max_length=4)
    time                    = models.CharField(max_length=2)

    def __unicode__(self):
        return str(self.cluster) + " --> " + str(self.ddp_hostname) + " --> " + str(self.cron) + " --> " + str(self.port)

class ItamWebhookEndpoint(models.Model):
     '''
     ITAM Webhook Endpoint
     '''

     endpoint = models.CharField(max_length=200, null=True, unique=True)

     def __unicode__(self):
         return "ITAM Webhook Endpoint " + str(self.endpoint)
