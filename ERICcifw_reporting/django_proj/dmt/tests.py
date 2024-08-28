from django.test import TestCase, Client
from cireports.models import *
from dmt.models import *
from datetime import datetime
from ciconfig import CIConfig
from dmt.utils import editVlanDetails, createVlanDetails
import logging
logger = logging.getLogger(__name__)
config = CIConfig()

class BaseSetUpTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = User.objects.create_user(username='testuser', password='12345')
        cls.userAdmin = User.objects.create_user(username='admin', password='12345')
        cls.deployScript = DeployScriptMapping.objects.create(reference='master', version='1.1.1')
        cls.deployScript2 = DeployScriptMapping.objects.create(reference='1.1', version='1.1.2')
        cls.deployScript3 = DeployScriptMapping.objects.create(reference='6.10_x86', version='1.1.3')
        cls.package = Package.objects.create(name="ERICtest_CXP1234567")
        cls.category = Categories.objects.create(name="sw")
        cls.mediaCatProd = MediaArtifactCategory.objects.create(name="productware")
        cls.mediaCatTest = MediaArtifactCategory.objects.create(name="testware")
        cls.mediaDeployType = MediaArtifactDeployType.objects.create(type="not_required")

        cls.package_revision = PackageRevision.objects.create(package=cls.package,
                                                              date_created=datetime.now(),
                                                              autodrop="latest.Maintrack",
                                                              last_update=datetime.now(),
                                                              category=cls.category,
                                                              version="1.12.4")
        cls.package_revision1 = PackageRevision.objects.create(package=cls.package,
                                                              date_created=datetime.now(),
                                                              autodrop="latest.Maintrack",
                                                              last_update=datetime.now(),
                                                              category=cls.category,
                                                              version="1.12.3")

        cls.package2 = Package.objects.create(name="ERICtest2_CXP8910111")
        cls.category2 = Categories.objects.create(name="model")
        cls.package_revision2 = PackageRevision.objects.create(package=cls.package2,
                                                              date_created=datetime.now(),
                                                              autodrop="latest.Maintrack",
                                                              last_update=datetime.now(),
                                                              category=cls.category2,
                                                              version="1.12.5")
        cls.package_revision3 = PackageRevision.objects.create(package=cls.package2,
                                                              date_created=datetime.now(),
                                                              autodrop="latest.Maintrack",
                                                              last_update=datetime.now(),
                                                              category=cls.category2,
                                                              version="1.12.4")
        cls.package3 = Package.objects.create(name=config.get("DMT_AUTODEPLOY", "deploymentTemplatePackage"))
        cls.package3_revision1 = PackageRevision.objects.create(package=cls.package3,
                                                                date_created=datetime.now(),
                                                                autodrop="latest.Maintrack",
                                                                last_update=datetime.now(),
                                                                category=cls.category2,
                                                                version="1.2.1")
        cls.package3_revision2 = PackageRevision.objects.create(package=cls.package3,
                                                                date_created=datetime.now(),
                                                                autodrop="latest.Maintrack",
                                                                last_update=datetime.now(),
                                                                category=cls.category2,
                                                                version="1.2.2")
        cls.product = Product.objects.create(name="ENM")
        cls.mediaArtifact = MediaArtifact.objects.create(name="test",
                                                         number="CXP123456",
                                                         description="test",
                                                         mediaType="iso",
                                                         category=cls.mediaCatProd,
                                                         deployType=cls.mediaDeployType)
        cls.release = Release.objects.create(name="enmRelease",
                                             track="enmTrack",
                                             product=cls.product,
                                             masterArtifact=cls.mediaArtifact,
                                             created="2014-05-19 21:55:08")
        cls.drop = Drop.objects.create(name="test",
                                       release=cls.release,
                                       systemInfo="test")

        cls.isoBuild = ISObuild.objects.create(version="1.26.10",
                                               groupId="com.ericsson.se",
                                               artifactId="ERICtestiso_CXP123456",
                                               mediaArtifact=cls.mediaArtifact,
                                               drop=cls.drop,
                                               build_date="2014-05-19 21:55:08",
                                               arm_repo="test")
        cls.isoBuildContentDT1 = ISObuildMapping.objects.create(iso=cls.isoBuild,
                                                                package_revision=cls.package3_revision1,
                                                                drop=cls.drop)
        cls.isoBuildTwo = ISObuild.objects.create(version="1.26.20",
                                               groupId="com.ericsson.se",
                                               artifactId="ERICtestiso_CXP123456",
                                               mediaArtifact=cls.mediaArtifact,
                                               drop=cls.drop,
                                               build_date="2014-05-19 21:55:08",
                                               arm_repo="test")
        cls.isoBuildContentDT2 = ISObuildMapping.objects.create(iso=cls.isoBuildTwo,
                                                                package_revision=cls.package3_revision2,
                                                                drop=cls.drop)
        cls.isoBuildThree = ISObuild.objects.create(version="1.26.30",
                                                groupId="com.ericsson.se",
                                                artifactId="ERICtestiso_CXP123456",
                                                mediaArtifact=cls.mediaArtifact,
                                                drop=cls.drop,
                                                build_date="2014-05-19 21:55:08",
                                                arm_repo="test")
        cls.statusPassed = States.objects.create(state="passed")
        cls.statusFailed = States.objects.create(state="failed")
        cls.productSet = ProductSet.objects.create(name="ENM")
        cls.cdbType =  CDBTypes.objects.create(name="CDB")
        cls.productSetRelease = ProductSetRelease.objects.create(name="ENM-15B",
                                                                 number="AOM901151",
                                                                 release=cls.release,
                                                                 productSet=cls.productSet,
                                                                 masterArtifact=cls.mediaArtifact)
        cls.productSetVersion = ProductSetVersion.objects.create(version="1.0.1",
                                                                 status=cls.statusPassed,
                                                                 productSetRelease=cls.productSetRelease,
                                                                 current_status = "{1: 'passed#2016-10-12 04:35:38#2016-10-12 07:06:53#None#None'}",
                                                                 drop=cls.drop)
        cls.productSetVersionContent = ProductSetVersionContent.objects.create(productSetVersion=cls.productSetVersion,
                                                                               status=cls.statusPassed,
                                                                               mediaArtifactVersion=cls.isoBuild)
        cls.productSetVersionTwo = ProductSetVersion.objects.create(version="1.0.2",
                                                                 status=cls.statusPassed,
                                                                 productSetRelease=cls.productSetRelease,
                                                                 current_status = "{1: 'passed#2016-10-12 04:35:38#2016-10-12 07:06:53#None#None'}",
                                                                 drop=cls.drop)
        cls.productSetVersionContentTwo = ProductSetVersionContent.objects.create(productSetVersion=cls.productSetVersionTwo,
                                                                               status=cls.statusPassed,
                                                                               mediaArtifactVersion=cls.isoBuildTwo)
        cls.depUtil = DeploymentUtilities.objects.create(utility="deployScript")
        cls.depUtilVersion = DeploymentUtilitiesVersion.objects.create(utility_name=cls.depUtil,
                                                                       utility_version="1.1.1",
                                                                       utility_label="Deployment Script")
        cls.depUtilMedia = DeploymentUtilsToISOBuild.objects.create(utility_version=cls.depUtilVersion, iso_build=cls.isoBuild)
        cls.depUtilVersionTwo = DeploymentUtilitiesVersion.objects.create(utility_name=cls.depUtil,
                                                                       utility_version="1.1.2",
                                                                       utility_label="Deployment Script")
        cls.depUtilMediaTwo = DeploymentUtilsToISOBuild.objects.create(utility_version=cls.depUtilVersionTwo, iso_build=cls.isoBuildTwo)
        cls.depUtilVersionThree = DeploymentUtilitiesVersion.objects.create(utility_name=cls.depUtil,
                                                                       utility_version="1.1.3",
                                                                       utility_label="Deployment Script")
        cls.productSetVersionThree = ProductSetVersion.objects.create(version="1.0.3",
                                                                    status=cls.statusFailed,
                                                                    productSetRelease=cls.productSetRelease,
                                                                    current_status = "{1: 'failed#2016-10-12 04:35:38#2016-10-12 07:06:53#None#None'}",
                                                                    drop=cls.drop)
        cls.productSetVersionContentThree = ProductSetVersionContent.objects.create(productSetVersion=cls.productSetVersionThree,
                                                                                  status=cls.statusFailed,
                                                                                  mediaArtifactVersion=cls.isoBuildThree)
        cls.depUtilPSV = DeploymentUtilsToProductSetVersion.objects.create(utility_version=cls.depUtilVersionThree, productSetVersion=cls.productSetVersionThree)

        ## DD setup
        cls.ddType = DeploymentDescriptionType.objects.create(dd_type="rpm")
        cls.ddVersion = DeploymentDescriptionVersion.objects.create(version="1.0.1")
        cls.dd = DeploymentDescription.objects.create(dd_type=cls.ddType, version=cls.ddVersion, name="6svc_3scp_3evt_enm_ipv6_physical_production")
        cls.dd2 = DeploymentDescription.objects.create(version=cls.ddVersion, dd_type=cls.ddType,
                                                       name="5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test",
                                                       capacity_type="test",
                                                       auto_deployment="5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test_dd.xml",
                                                       sed_deployment="5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test_info_txt")

        #Deployment Setup
        ###MgtServer###
        cls.mgtServerServer = Server.objects.create(name = "ieatlms6362",
                                                    hostname = "ieatlms6362",
                                                    hostnameIdentifier="1",
                                                    domain_name = "athtem.eei.ericsson.se",
                                                    dns_serverA = "159.107.173.3",
                                                    dns_serverB = "159.107.173.12",
                                                    hardware_type = "rackmounted")
        cls.mgtServer = ManagementServer.objects.create(server=cls.mgtServerServer,
                                                        description="Test Mgt Server",
                                                        product=cls.product)
        cls.mgtNetworkObjEth0 = NetworkInterface.objects.create(server=cls.mgtServerServer,
                                                               mac_address="00:11:0A:6B:7D:38",
                                                               nicIdentifier="1",
                                                               interface="eth0")
        cls.mgtNetworkObjEth1 = NetworkInterface.objects.create(server=cls.mgtServerServer,
                                                                mac_address="00:11:0A:6B:7D:39",
                                                                nicIdentifier="1",
                                                               interface="eth1")
        cls.mgtNetworkObjEth2 = NetworkInterface.objects.create(server=cls.mgtServerServer,
                                                                mac_address="00:11:0A:6B:7B:64",
                                                                nicIdentifier="1",
                                                                interface="eth2")
        cls.mgtNetworkObjEth3 = NetworkInterface.objects.create(server=cls.mgtServerServer,
                                                                mac_address="00:11:0A:6B:7B:65",
                                                                nicIdentifier="1",
                                                                interface="eth3")
        cls.mgtIpAddressHost = IpAddress.objects.create(nic=cls.mgtNetworkObjEth0,
                                                        address = "131.160.169.30" ,
                                                        ipv4UniqueIdentifier = '1',
                                                        bitmask = "21",
                                                        ipv6UniqueIdentifier = "1",
                                                        ipType = "host")
        cls.mgtIpAddressStorage = IpAddress.objects.create(nic=cls.mgtNetworkObjEth0,
                                                        address = "10.149.3.110" ,
                                                        ipv4UniqueIdentifier = '1',
                                                        ipv6UniqueIdentifier = "1",
                                                        ipType = "storage")
        cls.mgtIpAddressBackup = IpAddress.objects.create(nic=cls.mgtNetworkObjEth0,
                                                           address = "10.149.16.68" ,
                                                           ipv4UniqueIdentifier = '1',
                                                           ipv6UniqueIdentifier = "1",
                                                           ipType = "backup")
        cls.mgtIpAddressInternal = IpAddress.objects.create(nic=cls.mgtNetworkObjEth0,
                                                          address = "10.247.246.2",
                                                          ipv4UniqueIdentifier = '1',
                                                          ipv6UniqueIdentifier = "1",
                                                          ipType = "internal")
        cls.iloIpObj = IpAddress.objects.create(address="10.151.62.57",ipType="ilo_" + str(cls.mgtServerServer.id))
        cls.iloObj = Ilo.objects.create(ipMapIloAddress=cls.iloIpObj,server=cls.mgtServerServer,username="root",password="shroot2")
        ###Cluster###
        cls.credentials = Credentials.objects.create(username = "litp-admin",
                                                     password = "12shroot",
                                                     credentialType = "admin",
                                                     loginScope = "")
        cls.clusterLayout = ClusterLayout.objects.create(name="KVM", description ="Test Deployment Layout")
        cls.clusterObj = Cluster.objects.create(name="Deployment-51",
                                                description = "Test Deployment",
                                                tipc_address = "1241",
                                                management_server = cls.mgtServer,
                                                mac_lowest = "CA:22:50:fc:00:00",
                                                mac_highest = "CA:22:50:fc:FF:FF",
                                                dhcp_lifetime = datetime.now(),
                                                layout = cls.clusterLayout)
        cls.deploymentStatusType = DeploymentStatusTypes.objects.create(status="IDLE")
        cls.deploymentStatusType2 = DeploymentStatusTypes.objects.create(status="QUARANTINE")
        cls.deploymentStatus = DeploymentStatus.objects.create(status = cls.deploymentStatusType,
                                                               cluster = cls.clusterObj,
                                                               status_changed = datetime.now(),
                                                               description = "Error: Issue running the deployment",
                                                               osDetails =  "6.6_x86",
                                                               litpVersion = "2.43.8",
                                                               mediaArtifact = "1.26.36",
                                                               packages = "[ERICebsmflow_CXP9031856, ERICenmsgebsm_CXP9031896]",
                                                               patches = "1.14.1")
        cls.vlanDetails = VlanDetails.objects.create(services_subnet = "131.160.168.0/21",
                                                     services_gateway = "131.160.168.1",
                                                     storage_gateway = IpAddress.objects.create(address='1.1.1.1', ipType="storage_gateway", ipv4UniqueIdentifier=1),
                                                     services_ipv6_gateway = "2001:1b70:6207::707:0:1",
                                                     services_ipv6_subnet = "2001:1b70:6207:0000::/64",
                                                     storage_subnet = "10.149.0.0/20",
                                                     backup_subnet = "10.149.16.0/23",
                                                     jgroups_subnet = "10.250.244.0/22",
                                                     internal_subnet = "10.247.244.0/22",
                                                     storage_vlan = "731",
                                                     backup_vlan = "732",
                                                     jgroups_vlan = "721",
                                                     internal_vlan = "718",
                                                     services_vlan = "707",
                                                     litp_management = "internal",
                                                     hbAVlan = "714",
                                                     hbBVlan= "715",
                                                     cluster = cls.clusterObj)
        ###Cluster -- DD Mapping##
        cls.ddToDeploymentMap = DDtoDeploymentMapping.objects.create(deployment_description=cls.dd, cluster=cls.clusterObj, auto_update=True, update_type="complete", iprange_type="dns")
        ###IP Range###
        cls.ipRangeItemJgroup = IpRangeItem.objects.create(ip_range_item = "PDU-Priv_nodeInternalJgroup")
        cls.ipRangeItemInternal = IpRangeItem.objects.create(ip_range_item = "PDU-Priv-2_nodeInternal")
        cls.ipRange = IpRange.objects.create(ip_range_item = cls.ipRangeItemJgroup,
                start_ip = "10.250.246.2",
                end_ip = "10.250.246.50",
                bitmask = "22",
                gateway = "10.250.244.1")
        cls.ipRange = IpRange.objects.create(ip_range_item = cls.ipRangeItemInternal,
                start_ip = "10.247.246.2",
                end_ip = "10.247.246.50",
                bitmask = "22",
                gateway = "10.247.244.1")
        ###ClusterServer -- SVC-1###
        cls.virtualImageItems = VirtualImageItems.objects.create(name = "amos_1",
                                                                 type = "jboss",
                                                                 layout = "Virtual Machine",
                                                                 active = 1)
        cls.clusterServServSvc1 = Server.objects.create(name = "ieatrcxb6230",
                                                      hostname = "ieatrcxb6230",
                                                      hostnameIdentifier="1",
                                                      domain_name = "athtem.eei.ericsson.se",
                                                      dns_serverA = "159.107.173.3",
                                                      dns_serverB = "159.107.173.12",
                                                      hardware_type = "blade")
        cls.clusterServSvc1 = ClusterServer.objects.create(server = cls.clusterServServSvc1,
                                                           node_type = "SVC-1",
                                                           cluster = cls.clusterObj,
                                                           active = True)
        cls.clusterServrCredMapSvc1 = ClusterServerCredentialMapping.objects.create(clusterServer = cls.clusterServSvc1,
                                                                                    credentials = cls.credentials,
                                                                                    signum = "test",
                                                                                    date_time = datetime.now())
        cls.networkObjEth0Svc1 = NetworkInterface.objects.create(server=cls.clusterServServSvc1,
                                                                 mac_address="58:20:B1:E6:29:20",
                                                                 nicIdentifier="1",
                                                                 interface="eth0")
        cls.networkObjEth1Svc1 = NetworkInterface.objects.create(server=cls.clusterServServSvc1,
                                                                 mac_address="58:20:B1:E6:29:28",
                                                                 nicIdentifier="1",
                                                                 interface="eth1")
        cls.networkObjEth2Svc1 = NetworkInterface.objects.create(server=cls.clusterServServSvc1,
                                                                 mac_address="58:20:B1:E6:29:21",
                                                                 nicIdentifier="1",
                                                                 interface="eth2")
        cls.networkObjEth3Svc1 = NetworkInterface.objects.create(server=cls.clusterServServSvc1,
                                                                 mac_address="58:20:B1:E6:29:29",
                                                                 nicIdentifier="1",
                                                                 interface="eth3")
        cls.ipAddressJgroupSvc1 = IpAddress.objects.create(nic=cls.networkObjEth0Svc1,
                                                           address = "10.250.246.2",
                                                           ipv4UniqueIdentifier = '1',
                                                           ipv6UniqueIdentifier = "1",
                                                           ipType = "jgroup")
        cls.ipAddressStorageSvc1 = IpAddress.objects.create(nic=cls.networkObjEth0Svc1,
                                                           address = "10.149.3.84",
                                                           ipv4UniqueIdentifier = '1',
                                                           ipv6UniqueIdentifier = "1",
                                                           ipType = "storage")
        cls.ipAddressBackupSvc1 = IpAddress.objects.create(nic=cls.networkObjEth0Svc1,
                                                           address = "10.149.16.42",
                                                           ipv4UniqueIdentifier = '1',
                                                           ipv6UniqueIdentifier = "1",
                                                           ipType = "backup")
        cls.ipAddressInternalSvc1 = IpAddress.objects.create(nic=cls.networkObjEth0Svc1,
                                                             address = "10.247.246.3",
                                                             ipv4UniqueIdentifier = '1',
                                                             ipv6UniqueIdentifier = "1",
                                                             ipType = "internal")
        cls.ipAddressHostSvc1 = IpAddress.objects.create(nic=cls.networkObjEth0Svc1,
                                                             address = "131.160.169.4",
                                                             ipv4UniqueIdentifier = '1',
                                                             ipv6_address = "2001:1b70:6207::707:5433:1",
                                                             ipv6UniqueIdentifier = "1",
                                                             ipType = "other")
        cls.virtualImageSvc1 = VirtualImage.objects.create(name = "amos_1",
                                                           node_list = "SVC-1",
                                                           cluster = cls.clusterObj)
        cls.virtImSvc1IpPubIpv4 = IpAddress.objects.create(address = "131.160.169.31",
                                                          ipv4UniqueIdentifier = '1',
                                                          ipv6UniqueIdentifier = "1",
                                                          ipType = "virtualImage_public_1")
        cls.virtImInfoIpSvc1PubIpv4 = VirtualImageInfoIp.objects.create(number = "1",
                                                                   hostname = "ieatENM5433-1",
                                                                   virtual_image = cls.virtualImageSvc1,
                                                                   ipMap = cls.virtImSvc1IpPubIpv4)
        cls.virtImSvc1IpPubIpv6 = IpAddress.objects.create(ipv6_address = "2001:1b70:6207::707:5433:1b",
                                                          ipv4UniqueIdentifier = '1',
                                                          ipv6UniqueIdentifier = "1",
                                                          ipType = "virtualImage_ipv6Public_1")
        cls.virtImInfoIpSvc1PubIpv6 = VirtualImageInfoIp.objects.create(number = "1",
                                                                   virtual_image = cls.virtualImageSvc1,
                                                                   ipMap = cls.virtImSvc1IpPubIpv6)
        cls.virtImSvc1IpStgIpv4 = IpAddress.objects.create(address = "10.149.3.118",
                                                          ipv4UniqueIdentifier = '1',
                                                          ipv6UniqueIdentifier = "1",
                                                          ipType = "virtualImage_storage_1")
        cls.virtImInfoIpSvc1StgIpv4 = VirtualImageInfoIp.objects.create(number = "1",
                                                                        virtual_image = cls.virtualImageSvc1,
                                                                        ipMap = cls.virtImSvc1IpStgIpv4)
        cls.virtImSvc1IpIntIpv4 = IpAddress.objects.create(address = "10.247.246.53",
                                                          ipv4UniqueIdentifier = '1',
                                                          ipv6UniqueIdentifier = "1",
                                                          ipType = "virtualImage_internal_1")
        cls.virtImInfoIpSvc1IntIpv4 = VirtualImageInfoIp.objects.create(number = "1",
                                                                        virtual_image = cls.virtualImageSvc1,
                                                                        ipMap = cls.virtImSvc1IpIntIpv4)
        cls.virtImSvc1JgrpIpIpv4 = IpAddress.objects.create(address = "10.250.246.53",
                                                          ipv4UniqueIdentifier = '1',
                                                          ipv6UniqueIdentifier = "1",
                                                          ipType = "virtualImage_jgroup_1")
        cls.virtImInfoIpSvc1JgrpIpv4 = VirtualImageInfoIp.objects.create(number = "1",
                                                                        virtual_image = cls.virtualImageSvc1,
                                                                        ipMap = cls.virtImSvc1JgrpIpIpv4)

        ###ClusterServer -- NETSIM -- Active###
        cls.credentialNetsim = Credentials.objects.create(username = "netsim",
                                                     password = "netsim",
                                                     credentialType = "admin",
                                                     loginScope = "")
        cls.clServServNetsim1 = Server.objects.create(name = "ieatnetsimv7005-01",
                                                      hostname = "ieatnetsimv7005-01",
                                                      hostnameIdentifier="1",
                                                      domain_name = "athtem.eei.ericsson.se",
                                                      dns_serverA = "159.107.173.3",
                                                      dns_serverB = "159.107.173.12",
                                                      hardware_type = "cloud")
        cls.clServNetsim1 = ClusterServer.objects.create(server = cls.clServServNetsim1,
                                                           node_type = "NETSIM",
                                                           cluster = cls.clusterObj,
                                                           active = True)
        cls.clServrCredMapNetsim1 = ClusterServerCredentialMapping.objects.create(clusterServer = cls.clServNetsim1,
                                                                                  credentials = cls.credentials,
                                                                                  signum = "test",
                                                                                  date_time = datetime.now())
        cls.networkObjEth0Netsim1 = NetworkInterface.objects.create(server=cls.clServServNetsim1,
                                                                    mac_address="00:50:56:3f:02:3c",
                                                                    nicIdentifier="1",
                                                                    interface="eth0")
        cls.ipAddressHostNetsim1 = IpAddress.objects.create(nic=cls.networkObjEth0Netsim1,
                                                             address = "10.149.20.140",
                                                             ipv4UniqueIdentifier = '1',
                                                             ipv6UniqueIdentifier = "1",
                                                             ipType = "other")
        ###ClusterServer -- NETSIM -- Active ###
        cls.credentialNetsim3 = Credentials.objects.create(username = "netsim",
                password = "netsim",
                credentialType = "admin",
                loginScope = "")
        cls.clServServNetsim3 = Server.objects.create(name = "ieatnetsimv7005-01",
                hostname = "ieatnetsimv7005-01-test-delete",
                hostnameIdentifier="1",
                domain_name = "athtem.eei.ericsson.se",
                dns_serverA = "159.107.173.3",
                dns_serverB = "159.107.173.12",
                hardware_type = "cloud")
        cls.clServNetsim3 = ClusterServer.objects.create(server = cls.clServServNetsim3,
                node_type = "NETSIM",
                cluster = cls.clusterObj,
                active = True)
        cls.clServrCredMapNetsim3 = ClusterServerCredentialMapping.objects.create(clusterServer = cls.clServNetsim3,
                credentials = cls.credentials,
                signum = "test",
                date_time = datetime.now())
        cls.networkObjEth0Netsim3 = NetworkInterface.objects.create(server=cls.clServServNetsim3,
                mac_address="00:50:56:3f:02:3f",
                nicIdentifier="1",
                interface="eth0")
        cls.ipAddressHostNetsim3 = IpAddress.objects.create(nic=cls.networkObjEth0Netsim3,
                address = "10.149.20.142",
                ipv4UniqueIdentifier = '1',
                ipv6UniqueIdentifier = "1",
                ipType = "other")

        ###ClusterServer -- NETSIM -- Passive ###
        cls.clServServNetsim2 = Server.objects.create(name = "ieatnetsimv7005-02",
                                                      hostname = "ieatnetsimv7005-02",
                                                      hostnameIdentifier="1",
                                                      domain_name = "athtem.eei.ericsson.se",
                                                      dns_serverA = "159.107.173.3",
                                                      dns_serverB = "159.107.173.12",
                                                      hardware_type = "cloud")
        cls.clServNetsim2 = ClusterServer.objects.create(server = cls.clServServNetsim2,
                                                           node_type = "NETSIM",
                                                           cluster = cls.clusterObj,
                                                           active = False)
        cls.clServrCredMapNetsim2 = ClusterServerCredentialMapping.objects.create(clusterServer = cls.clServNetsim2,
                                                                                  credentials = cls.credentials,
                                                                                  signum = "test",
                                                                                  date_time = datetime.now())
        cls.networkObjEth0Netsim2 = NetworkInterface.objects.create(server=cls.clServServNetsim2,
                                                                    mac_address="00:50:56:3f:02:46",
                                                                    nicIdentifier="1",
                                                                    interface="eth0")
        cls.ipAddressHostNetsim2 = IpAddress.objects.create(nic=cls.networkObjEth0Netsim2,
                                                             address = "10.149.20.141",
                                                             ipv4UniqueIdentifier = '1',
                                                             ipv6UniqueIdentifier = "1",
                                                             ipType = "other")

        cls.deploymentStatusType1 = DeploymentStatusTypes.objects.create(status="BUSY")

        cls.installGroup1 = InstallGroup.objects.create(installGroup="Maintrack")

        cls.clusterInstallGroupMap1 =  ClusterToInstallGroupMapping.objects.create(cluster=cls.clusterObj,
                                                                                group=cls.installGroup1,
                                                                                status=cls.deploymentStatus)
        ###Cluster -- Additional Properties
        cls.clAdditionalProps = ClusterAdditionalInformation.objects.create(cluster=cls.clusterObj, ddp_hostname="test_hostname_1", cron="test_cron", port="1111")

        ###NAS Server
        cls.nasSer = Server.objects.create(name = "ieatrcxb-nas-mgt",
                                           hostname = "ieatrcxb-nas-mgt",
                                           hostnameIdentifier="1",
                                           domain_name = "athtem.eei.ericsson.se",
                                           dns_serverA = "159.107.173.3",
                                           dns_serverB = "159.107.173.12",
                                           hardware_type = "rack")
        cls.networkObjEth0Nas = NetworkInterface.objects.create(server=cls.nasSer,
                                                                    mac_address="00:50:56:3f:01:50",
                                                                    nicIdentifier="1",
                                                                    interface="eth0")
        cls.ipAddressNas = IpAddress.objects.create(nic=cls.networkObjEth0Nas,
                                                     address= "10.149.50.150",
                                                     ipv4UniqueIdentifier= '1',
                                                     ipv6UniqueIdentifier= "1",
                                                     gateway_address= "10.149.0.1",
                                                     bitmask = "23",
                                                     ipType = "nas")
        cls.ipAddressNasVip1 = IpAddress.objects.create(nic=cls.networkObjEth0Nas,
                                                     address= "10.149.50.151",
                                                     ipv4UniqueIdentifier= '1',
                                                     ipv6UniqueIdentifier= "1",
                                                     ipType = "nasvip1")
        cls.ipAddressNasVip2 = IpAddress.objects.create(nic=cls.networkObjEth0Nas,
                                                     address= "10.149.50.152",
                                                     ipv4UniqueIdentifier= '1',
                                                     ipv6UniqueIdentifier= "1",
                                                     ipType = "nasvip2")
        cls.ipAddressNasInstallIp1 = IpAddress.objects.create(nic=cls.networkObjEth0Nas,
                                                     address= "10.149.50.153",
                                                     ipv4UniqueIdentifier= '1',
                                                     ipv6UniqueIdentifier= "1",
                                                     ipType = "nasinstallip1")
        cls.ipAddressNasInstallIp2 = IpAddress.objects.create(nic=cls.networkObjEth0Nas,
                                                     address= "10.149.50.154",
                                                     ipv4UniqueIdentifier= '1',
                                                     ipv6UniqueIdentifier= "1",
                                                     ipType = "nasinstallip2")
        cls.ipAddressNasIlo1 = IpAddress.objects.create(nic=cls.networkObjEth0Nas,
                                                     address= "10.149.50.155",
                                                     ipv4UniqueIdentifier= '1',
                                                     ipv6UniqueIdentifier= "1",
                                                     ipType = "nasInstalIlolIp1")
        cls.ipAddressNasIlo2 = IpAddress.objects.create(nic=cls.networkObjEth0Nas,
                                                     address= "10.149.50.156",
                                                     ipv4UniqueIdentifier= '1',
                                                     ipv6UniqueIdentifier= "1",
                                                     ipType = "nasInstalIlolIp2")
        cls.credentialNasMaster = Credentials.objects.create(username = "master",
                                                     password = "master",
                                                     credentialType = "admin",
                                                     loginScope = "")
        cls.nas = NASServer.objects.create(server=cls.nasSer,
                                           credentials=cls.credentialNasMaster)
        cls.nasClusterMap = ClusterToNASMapping.objects.create(cluster=cls.clusterObj,
                                                               nasServer=cls.nas)

        ###SAN Server
        cls.credentialSan = Credentials.objects.create(username="admin",
                                               password="Password1234#",
                                               credentialType="admin",
                                               loginScope="global")
        cls.storageObj = Storage.objects.create(name="ieatunity-36",
                                        hostname="ieatunity-36",
                                        domain_name="athtem.eei.ericsson.se",
                                        serial_number="CRK00214902799",
                                        credentials=cls.credentialSan)
        cls.ipAddressStor1 = IpAddress.objects.create(address="10.149.50.160",
                                             ipv4UniqueIdentifier= "1",
                                             ipv6UniqueIdentifier= "1",
                                             ipType="san")
        cls.ipAddressStor2 = IpAddress.objects.create(address="10.149.50.161",
                                                     ipv4UniqueIdentifier="1",
                                                     ipv6UniqueIdentifier="1",
                                                     ipType="san")
        cls.storageIpMap1 = StorageIPMapping.objects.create(storage=cls.storageObj,
                                                            ipaddr=cls.ipAddressStor1,
                                                            ipnumber="1")
        cls.storageIpMap1 = StorageIPMapping.objects.create(storage=cls.storageObj,
                                                            ipaddr=cls.ipAddressStor2,
                                                            ipnumber="2")
        cls.clusterObj2 = Cluster.objects.create(name="Deployment-52",
                                                 description="Test Deployment 2",
                                                 tipc_address="1242",
                                                 management_server=cls.mgtServer,
                                                 mac_lowest="CA:22:50:fd:00:00",
                                                 mac_highest="CA:22:50:fd:FF:FF",
                                                 dhcp_lifetime=datetime.now(),
                                                 layout=cls.clusterLayout)
        cls.storageMap = ClusterToStorageMapping.objects.create(cluster=cls.clusterObj2,storage=cls.storageObj)
        cls.nasClusterMap2 = ClusterToNASMapping.objects.create(cluster=cls.clusterObj2,nasServer=cls.nas)
        cls.nasStorDetails = NasStorageDetails.objects.create(sanPoolId="0", sanPoolName="ENM1077",
                                                              sanRaidGroup="0",
                                                              poolFS1="ENM1077",
                                                              fileSystem1="ENM1077-storadm",
                                                              fileSystem2="ENM1077-storobs",
                                                              fileSystem3="ENM1077-intcls",
                                                              nasType="unityxt",
                                                              cluster=cls.clusterObj2)

    @classmethod
    def tearDownClass(cls):
        cls.package.delete()
        cls.category.delete()
        cls.package_revision.delete()
        cls.package2.delete()
        cls.category2.delete()
        cls.package_revision2.delete()
        cls.isoBuild.delete()
        cls.drop.delete()
        cls.release.delete()
        cls.mediaArtifact.delete()
        cls.product.delete()

class ViewTest(BaseSetUpTest):
    def setUp(self):
        self.client_stub = Client()


    def test_create_netsim_server_in_cluster_success(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsimTestName", "hostName":"ieatnetsimTestHost", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"NetSim", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:59", "ipv4HostAddr":"10.144.37.118"}', content_type="application/json")
        self.assertEqual(response.data, "server successfuly created")
        self.assertEqual(response.status_code, 201)


    def test_create_netsim_server_in_cluster_without_mac_provided_success(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsim2TestName", "hostName":"ieatnetsim2TestHost", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"virtual", "nodeType":"netsim", "serverStatus":"true", "macAddr":"", "ipv4HostAddr":"10.144.37.119"}', content_type="application/json")
        self.assertEqual(response.data, "server successfuly created")
        self.assertEqual(response.status_code, 201)


    def test_create_workload_server_in_cluster_success(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatworkloadv1TestName", "hostName":"ieatworkloadTestHost", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"workload", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:60", "ipv4HostAddr":"10.144.37.200"}', content_type="application/json")
        self.assertEqual(response.data, "server successfuly created")
        self.assertEqual(response.status_code, 201)


    def test_create_workload_server_in_cluster_without_mac_provided_success(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatworkload2TestName", "hostName":"ieatworkload2TestHost", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"virtual", "nodeType":"workload", "serverStatus":"true", "macAddr":"", "ipv4HostAddr":"10.144.37.201"}', content_type="application/json")
        self.assertEqual(response.data, "server successfuly created")
        self.assertEqual(response.status_code, 201)


    def test_create_server_in_cluster_invalid_cluster_id_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/10/', data='{"machineName":"ieatworkloadvTestName", "hostName":"ieatworkloadvTestHost", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"workload", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:60", "ipv4HostAddr":"10.144.37.200"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)


    def test_create_server_in_cluster_invalid_mac_address_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsimvTestName1", "hostName":"ieatnetsimvTestHost1", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"NetSim", "serverStatus":"true", "macAddr":"00:50:56:AB:DD", "ipv4HostAddr":"10.144.37.121"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_server_in_cluster_invalid_ipv6_address_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsimvTestName2", "hostName":"ieatnetsimvTestHost2", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"NetSim", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:62", "ipv4HostAddr":"10.144.37.122", "ipv6HostAddr":"2001:1b70:82a1:145:0:606:540"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_server_in_cluster_invalid_ipv4_address_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsimvTestName3", "hostName":"ieatnetsimvTestHost3", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"NetSim", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:63", "ipv4HostAddr":"10.144.37"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_server_in_cluster_invalid_nodeType_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsimvTestName4", "hostName":"ieatnetsimvTestHost4", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"SVC-DB", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:64", "ipv4HostAddr":"10.144.37.124"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_server_in_cluster_invalid_hardware_type_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsimvTestName5", "hostName":"ieatnetsimvTestHost5", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"hw-2000", "nodeType":"netsim", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:65", "ipv4HostAddr":"10.144.37.125"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_server_in_cluster_hostname_notspecified_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"ieatnetsimvTestName6", "hostName":"", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"netsim", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:66", "ipv4HostAddr":"10.144.37.126"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_server_in_cluster_machinename_notspecified_failure(self):
        response = self.client_stub.post('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"machineName":"", "hostName":"ieatnetsimvTestHost7", "domainName":"athtem.eei.ericsson.se", "dnsA":"159.107.173.3", "dnsB":"159.107.173.12", "hardwareType":"cloud", "nodeType":"netsim", "serverStatus":"true", "macAddr":"00:50:56:AB:DD:67", "ipv4HostAddr":"10.144.37.127"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_additional_properties_in_cluster_success(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"test_hostname", "cron":"test_cron", "port":"1111", "time": "30", "signum": "testuser"}', content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "success")
        response = self.client_stub.get('/api/deployment/getClusterAdditionalProperties/clusterId/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "30")
        self.assertContains(response, "test_hostname")
        self.assertContains(response, "test_cron")
        self.assertContains(response, "1111")


    def test_create_additional_properties_in_cluster_empty_field_success(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"", "cron":"test_cron", "port":"1111", "time": "30", "signum": "testuser"}', content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "success")


    def test_create_additional_properties_in_cluster_does_not_exist_deployment_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/10000/', data='{"ddp_hostname":"", "cron":"test_cron", "port":"1111", "time": "", "signum": "testuser"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)


    def test_create_additional_properties_in_cluster_port_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"test_hostname", "cron":"test_cron", "port":"1777777777111", "time": "30", "signum": "testuser"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_additional_properties_in_cluster_port_not_digit_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"test_hostname", "cron":"test_cron", "port":"uyuiuiu", "time": "30", "signum": "testuser"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_additional_properties_in_cluster_time_not_over_60_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"test_hostname", "cron":"test_cron", "port":"1111", "time": "100", "signum": "testuser"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_additional_properties_in_cluster_time_not_digit_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"test_hostname", "cron":"test_cron", "port":"1111", "time": "aaaaa", "signum": "testuser"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_create_additional_properties_in_cluster_signum_required_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"test_hostname", "cron":"test_cron", "port":"1111", "time": "30"}', content_type="application/json")
        self.assertEqual(response.status_code, 428)


    def test_create_additional_properties_in_cluster_does_not_exist_user_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterAdditionalProperties/clusterId/1/', data='{"ddp_hostname":"test_hostname", "cron":"test_cron", "port":"1111", "time": "30", "signum": "dsdsdsd"}', content_type="application/json")
        self.assertEqual(response.status_code, 428)


    def test_get_additional_properties_from_cluster_success(self):
        response = self.client_stub.get('/api/deployment/getClusterAdditionalProperties/clusterId/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1111")
        self.assertContains(response, "test_cron")


    def test_get_additional_properties_from_cluster_failure(self):
        response = self.client_stub.get('/api/deployment/getClusterAdditionalProperties/clusterId/10000/')
        self.assertEqual(response.status_code, 404)


    def test_delete_server_from_cluster_success(self):
        response = self.client_stub.delete('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"hostName":"ieatnetsimv7005-01-test-delete"}', content_type="application/json")
        self.assertEqual(response.data, "success")
        self.assertEqual(response.status_code, 200)


    def test_delete_server_from_cluster_failure(self):
        response = self.client_stub.delete('/api/deployment/manageDeploymentServer/clusterId/1/', data='{"hostName":"wrong_host_name_provided"}', content_type="application/json")
        self.assertEqual(response.status_code, 412)


    def test_delete_server_from_cluster_wrong_cluster_id_failure(self):
        response = self.client_stub.delete('/api/deployment/manageDeploymentServer/clusterId/10/', data='{"hostName":"ieatnetsimv7005-01-test-delete"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)


    def test_validate_artifact_latest_version_success(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICtest_CXP1234567::latest::sw@@ERICtest2_CXP8910111::1.12.4::model/')
        self.assertEqual(response.status_code, 200)


    def test_validate_remote_artifact_success(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICtest_CXP1234567::https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/releases/com/ericsson/nms/security/ERICidenmgmtopendj_CXP9030738/1.23.2/ERICidenmgmtopendj_CXP9030738-1.23.2.rpm::sw/')
        self.assertEqual(response.status_code, 200)


    def test_validate_remote_artifact_not_in_database(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICenmsgcomecimmscm_CXP9032233::https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/releases/com/ericsson/nms/security/ERICidenmgmtopendj_CXP9030738/1.23.2/ERICidenmgmtopendj_CXP9030738-1.23.2.rpm::sw/')
        self.assertEqual(response.status_code, 200)


    def test_validate_artifact_version_success(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICtest_CXP1234567::1.12.3::sw/')
        self.assertEqual(response.status_code, 200)


    def test_validate_invalid_artifact_name_failure(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICtestt_CXP1234567::latest::service/')
        self.assertEqual(response.status_code, 412)


    def test_validate_invalid_artifact_category_failure(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICtestt_CXP1234567::latest::services/')
        self.assertEqual(response.status_code, 412)


    def test_validate_invalid_artifact_version_failure(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICtest_CXP1234567::latest::sw@@ERICtest_CXP1234567::1.12.45::services/')
        self.assertEqual(response.status_code, 412)


    def test_validate_invalid_remote_artifact_url_failure(self):
        response = self.client_stub.get('/api/deployment/validate/autodeploy/artifacts/ERICtest_CXP1234567::https://ci-portal.seli.wh.rnd.internal.ericsson.com/static/tmpUploadSnapshot/2016-06-13_10-34-14/ERICenmsgcomecimmscm_CXP9032233-1.11.2200-SNAPSHOT20160613085904.noarch.rpm::services/')
        self.assertEqual(response.status_code, 412)


    def test_deploymentutilities_success(self):
        response = self.client_stub.post('/api/deployment/deploymentutilities/product/ENM/isobuildversion/1.26.10/utilities/sedVersion::1.0.119::SED Version,deployScript::2.0.143,mtUtilsVersion::1.2.3::Main Track Utils/')
        self.assertEqual(response.data, "success")
        self.assertEqual(response.status_code, 200)


    def test_deploymentutilities_failure_in_isoversion(self):
        response = self.client_stub.post('/api/deployment/deploymentutilities/product/ENM/isobuildversion/1.26.11/utilities/sedVersion::1.0.119::SED Version,deployScript::2.0.143,mtUtilsVersion::1.2.3::Main Track Utils/')
        self.assertEqual(response.status_code, 428)


    def test_deploymentutilities_failure_in_productname(self):
        response = self.client_stub.post('/api/deployment/deploymentutilities/product/ABC/isobuildversion/1.26.10/utilities/sedVersion::1.0.119::SED Version,deployScript::2.0.143,mtUtilsVersion::1.2.3::Main Track Utils/')
        self.assertEqual(response.status_code, 428)


    def test_generateTAFHostPropertiesJSON_onlyActiveNetsim(self):
        response = self.client_stub.get('/generateTAFHostPropertiesJSON/?clusterId=1&pretty=true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ieatENM5433-1")
        self.assertContains(response, "ieatnetsimv7005-01")
        self.assertNotContains(response, "ieatnetsimv7005-02")


    def test_generateTAFHostPropertiesJSON_allNetsims(self):
        response = self.client_stub.get('/generateTAFHostPropertiesJSON/?clusterId=1&pretty=true&allNetsims=true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ieatENM5433-1")
        self.assertContains(response, "ieatnetsimv7005-01")
        self.assertContains(response, "ieatnetsimv7005-02")


    def test_generateTAFHostPropertiesJSON_returnIloInfo(self):
        response = self.client_stub.get('/generateTAFHostPropertiesJSON/?clusterId=1&pretty=true&allNetsims=true&iloDetails=true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iloInfo")
        self.assertContains(response, "ms1-ilo")
        self.assertContains(response, "10.151.62.57")
        self.assertContains(response, "shroot2")


    def test_generateTAFHostPropertiesJSON_getJGroup(self):
        response = self.client_stub.get('/generateTAFHostPropertiesJSON/?clusterId=1&pretty=true&allNetsims=true&iloDetails=true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10.250.246.53")
        self.assertContains(response, "jgroup")


    def test_validate_latest_artifact_version_failure(self):
        response = self.client_stub.get('/api/deployment/getlatestartifactversion/?artifacts=ERICaddnodebootstraphandlers_CXP9031419::Latest@@ERICactivityserviceui_CXP9031439::Latest/')
        self.assertEqual(response.status_code, 412)


    def test_validate_latest_artifact_version_success(self):
        response = self.client_stub.get('/api/deployment/getlatestartifactversion/?artifacts=ERICtest_CXP1234567::latest:sw@@ERICtest2_CXP8910111::latest::model/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.12.4")
        self.assertContains(response, "1.12.5")


    def test_installGroup_success(self):
        response = self.client_stub.get('/api/deployment/installGroup/?installGroup=Maintrack')
        self.assertEqual(response.status_code, 200)


    def test_installGroup_with_status_success(self):
        response = self.client_stub.get('/api/deployment/installGroup/?installGroup=Maintrack&status=idle')
        self.assertEqual(response.status_code, 200)


    def test_installGroup_failure(self):
        response = self.client_stub.get('/api/deployment/installGroup/?installGroup=Maintrack1')
        self.assertEqual(response.status_code, 412)


    def test_installGroup_with_status_success(self):
        response = self.client_stub.get('/api/deployment/installGroup/?installGroup=Maintrack&status=notidle')
        self.assertEqual(response.status_code, 412)


    def test_getDeploymentUtilitiesWithProductSet_success(self):
        response = self.client_stub.get('/api/deployment/deploymentutilities/productSet/ENM/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.2")


    def test_getDeploymentUtilitiesWithProductSet_failure(self):
        response = self.client_stub.get('/api/deployment/deploymentutilities/productSet/HH/')
        self.assertEqual(response.status_code, 404)


    def test_getDeploymentUtilitiesWithProductSetVersion_success(self):
        response = self.client_stub.get('/api/deployment/deploymentutilities/productSet/ENM/version/1.0.1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.1")


    def test_getDeploymentUtilitiesWithProductSetVersion_failure(self):
        response = self.client_stub.get('/api/deployment/deploymentutilities/productSet/ENM/version/1./')
        self.assertEqual(response.status_code, 412)


    def test_getDeploymentTemplatesWithProductSet_success(self):
        response = self.client_stub.get('/api/deployment/deploymentTemplates/productSet/ENM/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.2.2")


    def test_getDeploymentTemplatesWithProductSet_failure(self):
        response = self.client_stub.get('/api/deployment/deploymentTemplates/productSet/HH/')
        self.assertEqual(response.status_code, 404)


    def test_getDeploymentTemplatesWithProductSetVersion_success(self):
        response = self.client_stub.get('/api/deployment/deploymentTemplates/productSet/ENM/version/1.0.1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.2.1")


    def test_getDeploymentTemplatesWithProductSetVersion_failure(self):
        response = self.client_stub.get('/api/deployment/deploymentTemplates/productSet/ENM/version/1./')
        self.assertEqual(response.status_code, 412)


    def test_getDeploymentDescriptions_success(self):
        response = self.client_stub.get('/api/deployment/deploymentDescriptions/version/1.0.1/type/rpm/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "6svc_3scp_3evt_enm_ipv6_physical_production")


    def test_getDeploymentDescriptions_version_failure(self):
        response = self.client_stub.get('/api/deployment/deploymentDescriptions/version/1.1.1/type/rpm/')
        self.assertEqual(response.status_code, 404)


    def test_getDeploymentDescriptions_type_failure(self):
        response = self.client_stub.get('/api/deployment/deploymentDescriptions/version/1.0.1/type/fdsfsdf/')
        self.assertEqual(response.status_code, 404)


    def test_setDeploymentServersStatus_success(self):
        response = self.client_stub.post('/api/setDeploymentServersStatus/', data='signum=testuser&status=ACTIVE&clusterId=1&hostnameList=ieatrcxb6230,ieatnetsimv7005-02', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SUCCESS")


    def test_setDeploymentServersStatus_success(self):
        response = self.client_stub.post('/api/setDeploymentServersStatus/', data='signum=testuser&status=passive&clusterId=1&hostnameList=ieatrcxb6230,ieatnetsimv7005-02', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SUCCESS")


    def test_setDeploymentServersStatus_cluster_failure(self):
        response = self.client_stub.post('/api/setDeploymentServersStatus/', data='signum=testuser&status=ACTIVE&clusterId=77851&hostnameList=ieatrcxb6230,ieatnetsimv7005-02', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 404)


    def test_setDeploymentServersStatus_missing_parameter_failure(self):
        response = self.client_stub.post('/api/setDeploymentServersStatus/', data='signum=testuser&status=&clusterId=1&hostnameList=ieatrcxb6230,ieatnetsimv7005-02', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 428)


    def test_updateClusterIPRanges_all_success(self):
        response = self.client_stub.post('/api/deployment/updateClusterIPRanges/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Success")


    def test_updateClusterIPRanges_cluster_success(self):
        response = self.client_stub.post('/api/deployment/updateClusterIPRanges/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Success")


    def test_updateClusterIPRanges_failure(self):
        response = self.client_stub.post('/api/deployment/updateClusterIPRanges/99/')
        self.assertEqual(response.status_code, 404)


    def test_getDeploymentStatus_success(self):
        response = self.client_stub.get('/api/deployment/1/status/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IDLE")


    def test_getDeploymentStatus_failure(self):
        response = self.client_stub.get('/api/deployment/2/status/')
        self.assertEqual(response.status_code, 404)


    def test_setDeploymentStatus_success(self):
        responsePost = self.client_stub.post('/api/deployment/1/status/', data='setStatus=QUARANTINE', content_type="application/x-www-form-urlencoded")
        self.assertEqual(responsePost.status_code, 200)
        response = self.client_stub.get('/api/deployment/1/status/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QUARANTINE")


    def test_setDeploymentStatus_failure_on_id(self):
        responsePost = self.client_stub.post('/api/deployment/2/status/', data='setStatus=QUARANTINE', content_type="application/x-www-form-urlencoded")
        self.assertEqual(responsePost.status_code, 404)


    def test_setDeploymentStatus_failure_on_status(self):
        responsePost = self.client_stub.post('/api/deployment/1/status/', data='setStatus=Done', content_type="application/x-www-form-urlencoded")
        self.assertEqual(responsePost.status_code, 404)


    def test_setDeploymentStatus_failure_on_status_not_given(self):
        responsePost = self.client_stub.post('/api/deployment/1/status/', data='', content_type="application/x-www-form-urlencoded")
        self.assertEqual(responsePost.status_code, 428)


    def test_get_content_attached_to_iso_version_drop_success(self):
        response = self.client_stub.get('/api/deployment/info/ENM/drop/test/1.26.10/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.1")


    def test_get_content_attached_to_iso_version_drop_failure(self):
        response = self.client_stub.get('/api/deployment/info/ENM/drop/test/125/')
        self.assertEqual(response.status_code, 404)


    def test_get_content_attached_to_iso_version_productSet_success(self):
        response = self.client_stub.get('/api/deployment/info/ENM/productset/test/1.0.2/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.2")


    def test_get_content_attached_to_iso_version_productSet_failure(self):
        response = self.client_stub.get('/api/deployment/info/ENM/productset/test/111/')
        self.assertEqual(response.status_code, 404)


    def test_get_content_attached_to_productSet_version_success(self):
        response = self.client_stub.get('/api/deployment/info/ENM/productset/test/1.0.3/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.3")


    def test_get_deployment_dd_success(self):
        response = self.client_stub.get('/api/deployment/deploymentDescription/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.0.1")
        self.assertContains(response, "complete")
        self.assertContains(response, "dns")
        self.assertContains(response, "6svc_3scp_3evt_enm_ipv6_physical_production")
        self.assertContains(response, "rpm")


    def test_get_deployment_dd_failure(self):
        response = self.client_stub.get('/api/deployment/deploymentDescription/2/')
        self.assertEqual(response.status_code, 404)


    def test_update_dd_on_deployment_success(self):
        response = self.client_stub.post('/api/deployment/updateDeploymentDescription/1/5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test/', data='signum=testuser', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SUCCESS")
        response = self.client_stub.get('/api/deployment/deploymentDescription/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test")


    def test_update_dd_on_deployment_does_not_exist_deployment_failure(self):
        response = self.client_stub.post('/api/deployment/updateDeploymentDescription/10/5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test/', data='signum=testuser', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 404)


    def test_update_dd_on_deployment_does_not_exist_dd_failure(self):
        response = self.client_stub.post('/api/deployment/updateDeploymentDescription/1/88svc_1str_enm-full-cdb-ssgid/', data='signum=testuser', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 404)


    def test_update_dd_on_deployment_does_not_exist_user_failure(self):
        response = self.client_stub.post('/api/deployment/updateDeploymentDescription/1/5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test/', data='signum=usernot', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 428)


    def test_update_dd_on_deployment_no_signum_provided_failure(self):
        response = self.client_stub.post('/api/deployment/updateDeploymentDescription/1/5svc_1str_enm-full-cdb-ssgid-deployment_ipv6_cloud_test/', data='', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 428)


    def test_get_deployment_scripts_master_version_success(self):
        response = self.client_stub.get('/getDeployScriptVersion/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.1")


    def test_get_deployment_scripts_master_version_when_drop_not_found_success(self):
        response = self.client_stub.get('/getDeployScriptVersion/?drop=1.0')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.1")


    def test_get_deployment_scripts_master_version_when_os_not_found_success(self):
        response = self.client_stub.get('/getDeployScriptVersion/?osVersion=1.0')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.1")


    def test_get_deployment_scripts_drop_version_success(self):
        response = self.client_stub.get('/getDeployScriptVersion/?drop=1.1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.2")


    def test_get_deployment_scripts_os_version_success(self):
        response = self.client_stub.get('/getDeployScriptVersion/?osVersion=6.10_x86')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.3")


    def test_get_nas_details_using_hostname_success(self):
        response = self.client_stub.get('/api/deployment/getNasDetails/ieatrcxb-nas-mgt/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ieatrcxb-nas-mgt")
        self.assertContains(response, "rack")
        self.assertContains(response, "23")
        self.assertContains(response, "10.149.0.1")
        self.assertContains(response, "10.149.50.150")
        self.assertContains(response, "10.149.50.151")
        self.assertContains(response, "10.149.50.152")
        self.assertContains(response, "10.149.50.153")
        self.assertContains(response, "10.149.50.154")
        self.assertContains(response, "10.149.50.155")
        self.assertContains(response, "10.149.50.156")


    def test_get_nas_details_using_hostname_failure(self):
        response = self.client_stub.get('/api/deployment/getNasDetails/gdsdfgt/')
        self.assertEqual(response.status_code, 404)


    def test_get_nas_details_using_clusterId_success(self):
        response = self.client_stub.get('/api/deployment/getNasDetails/1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ieatrcxb-nas-mgt")
        self.assertContains(response, "rack")
        self.assertContains(response, "23")
        self.assertContains(response, "10.149.0.1")
        self.assertContains(response, "10.149.50.150")
        self.assertContains(response, "10.149.50.151")
        self.assertContains(response, "10.149.50.152")
        self.assertContains(response, "10.149.50.153")
        self.assertContains(response, "10.149.50.154")
        self.assertContains(response, "10.149.50.155")
        self.assertContains(response, "10.149.50.156")


    def test_get_nas_details_using_clusterId_unityxt_success(self):
        response = self.client_stub.get('/api/deployment/getNasDetails/2/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ieatunity-36")
        self.assertContains(response, "rack")
        self.assertContains(response, "23")
        self.assertContains(response, "10.149.0.1")
        self.assertContains(response, "10.149.50.160")
        self.assertContains(response, "10.149.50.151")
        self.assertContains(response, "10.149.50.152")
        self.assertContains(response, "10.149.50.153")
        self.assertContains(response, "10.149.50.154")
        self.assertContains(response, "10.149.50.155")
        self.assertContains(response, "10.149.50.156")


    def test_get_nas_details_using_clusterId_failure(self):
        response = self.client_stub.get('/api/deployment/getNasDetails/555/')
        self.assertEqual(response.status_code, 404)


    def test_storage_gateway_successful_unsuccessful_operation(self):
        clusterId = 2
        vlanDetailsValues = \
                {
                    'hbaVlan' : '528',
                    'hbbVlan' : '563',
                    'serviceSubnet' : '10.150.98.0/24',
                    'servicesGateway' : '10.150.98.1',
                    'serviceIpv6Gateway' : '2001:1b70:82b9:194::1',
                    'serviceIpv6Subnet' : '2001:1b70:82b9:0194:0000:0000:0000:0001/64',
                    'storageSubnet' : '10.150.100.0/23',
                    'storageGateway' : '',
                    'backupSubnet' : '10.150.104.0/24',
                    'jgroupsSubnet' : '10.250.244.0/22',
                    'internalSubnet' : '10.247.244.0/22',
                    'internalIPv6Subnet' : 'fd5b:1fd5:8295:5340:0000:0000:0000:0000/64',
                    'storageVlan' : '565',
                    'backupVlan' : '572',
                    'jgroupsVlan' : '527',
                    'internalVlan' : '526',
                    'servicesVlan' : '564',
                    'managementVlan' : '',
                    'litpManagement' : 'internal',
                }

        outcome, message = createVlanDetails(clusterId,'create',vlanDetailsValues)
        self.assertEqual(outcome, '0')
        self.assertEqual(message, 'Success')

        vlanDetailsValues['storageGateway'] = '1.1.1.1'
        outcome, message = editVlanDetails(clusterId,'edit',vlanDetailsValues)
        self.assertEqual(outcome, '1')
        self.assertEqual(message, 'Storage gateway of 1.1.1.1 is not unique, please ensure public IP adresses are unique.')

        vlanDetailsValues['storageGateway'] = '230.100.180.2'
        outcome, message = editVlanDetails(clusterId,'edit',vlanDetailsValues)
        self.assertEqual(outcome, '0')
        self.assertEqual(message, 'Success')
        ipCountBefore = IpAddress.objects.all().count()

        vlanDetailsValues['storageGateway'] = ''
        outcome, message = editVlanDetails(clusterId,'edit',vlanDetailsValues)
        self.assertEqual(outcome, '0')
        self.assertEqual(message, 'Success')

        ipCountAfter = IpAddress.objects.all().count()
        self.assertEqual(ipCountBefore - 1, ipCountAfter)
