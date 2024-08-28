"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase, Client
from cireports.models import *
from dmt.models import *
from datetime import datetime, timedelta
from django.contrib.auth.models import User, Permission, Group
import utils

"""
class SimpleTest(TestCase):
    def test_basic_addition(self):
        '''
        Tests that 1 + 1 always equals 2.
        '''
        self.assertEqual(1 + 1, 2)

class CreatePackages(TestCase):
    def test_create_packages(self):
        base_num = 1234567
        for i in range(0,100):
            p_num = base_num + i
            package = Package.objects.create(name="ERICapp" + str(i), package_number="CXP" + str(p_num), signum="emarfah")
        package_list = Package.objects.all()
        self.assertEqual(len(package_list), 100)

    def test_fail_create(self):
        package = Package.objects.create(name="ERICtestfail", package_number="CXP1234567")
        package_list = Package.objects.filter(name="ERICtestfail")
        self.assertEqual(len(package_list), 0)
"""


class BaseSetUpTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.categorySW = Categories.objects.create(name="sw")
        cls.categoryServ = Categories.objects.create(name="service")
        cls.categoryTest = Categories.objects.create(name="testware")
        cls.mediatypeISO = MediaArtifactType.objects.create(type="iso")
        cls.mediatypeTAR = MediaArtifactType.objects.create(type="tar.gz")
        cls.mediaCatProd = MediaArtifactCategory.objects.create(
            name="productware")
        cls.mediaCatTest = MediaArtifactCategory.objects.create(
            name="testware")
        cls.mediaDeployType = MediaArtifactDeployType.objects.create(
            type="not_required")
        cls.mediaDeployTypePlat = MediaArtifactDeployType.objects.create(
            type="it_platform")
        cls.mediaDeployTypeOS = MediaArtifactDeployType.objects.create(
            type="os")
        cls.mediaDeployTypePatch = MediaArtifactDeployType.objects.create(
            type="patches")

        group_name = "ENM_MainTrack_Guardians"
        group_name2 = "CI_EX_Admin"
        cls.group1 = Group(name=group_name)
        cls.group2 = Group(name=group_name2)
        cls.group1.save()
        cls.group2.save()

        cls.jiraTypeExclusion = JiraTypeExclusion.objects.create(
            jiraType="Support")
        cls.user = User.objects.create_user(
            username='testuser', password='12345')
        cls.user2 = User.objects.create_user(
            username='testuser2', password='12345')
        cls.package = Package.objects.create(name="ERICtest_CXP1234567")
        cls.package_revision = PackageRevision.objects.create(package=cls.package,
                                                              date_created=datetime.now(),
                                                              autodrop="latest.Maintrack",
                                                              last_update=datetime.now(),
                                                              category=cls.categorySW,
                                                              kgb_test="not_started",
                                                              version="1.12.3")
        buildDate = datetime.now() - timedelta(days=1)
        buildDate2 = datetime.now() + timedelta(days=1)
        freezeDate = datetime.now() + timedelta(days=1)
        # Product Set Drop Setup
        cls.productRHELMedia = Product.objects.create(name="RHEL-Media")
        cls.mediaArtifactRHELMedia = MediaArtifact.objects.create(
            name="RHEL-Media_CXP15151515", number="CXP15151515", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypeOS)
        cls.releaseRHELMedia = Release.objects.create(
            name="rhelRelease", track="rhelTrack", product=cls.productRHELMedia, masterArtifact=cls.mediaArtifactRHELMedia, created=datetime.now())
        cls.dropRHELMedia = Drop.objects.create(name="1.1", release=cls.releaseRHELMedia, systemInfo="test",
                                                planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildRHELMedia = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="RHEL-Media_CXP15151515", mediaArtifact=cls.mediaArtifactRHELMedia,
                                                        drop=cls.dropRHELMedia, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")

        cls.productRHELPatch = Product.objects.create(
            name="RHEL-OS-Patch-Set-ISO")
        cls.mediaArtifactRHELPatch = MediaArtifact.objects.create(
            name="RHEL_OS_Patch_Set_CXP9034997", number="CXP9034997", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypePatch)
        cls.releaseRHELPatch = Release.objects.create(name="rhelPatchRelease", track="rhelPatchTrack",
                                                      product=cls.productRHELPatch, masterArtifact=cls.mediaArtifactRHELPatch, created=datetime.now())
        cls.dropRHELPatch = Drop.objects.create(name="1.1", release=cls.releaseRHELPatch, systemInfo="test",
                                                planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildRHELPatch = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="RHEL_OS_Patch_Set_CXP9034997", mediaArtifact=cls.mediaArtifactRHELPatch,
                                                        drop=cls.dropRHELPatch, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")

        cls.productRHELPatch7 = Product.objects.create(
            name="RHEL-76-OS-Patch-Set-ISO")
        cls.mediaArtifactRHELPatch7 = MediaArtifact.objects.create(
            name="RHEL76_OS_Patch_Set_CXP9037739", number="CXP9037739", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypePatch)
        cls.releaseRHELPatch7 = Release.objects.create(name="rhelPatch76Release", track="rhelPatch76Track",
                                                       product=cls.productRHELPatch7, masterArtifact=cls.mediaArtifactRHELPatch7, created=datetime.now())
        cls.dropRHELPatch7 = Drop.objects.create(name="1.1", release=cls.releaseRHELPatch7, systemInfo="test",
                                                 planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildRHELPatch7 = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="RHEL76_OS_Patch_Set_CXP9037739", mediaArtifact=cls.mediaArtifactRHELPatch7,
                                                         drop=cls.dropRHELPatch7, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")

        cls.productLitp = Product.objects.create(name="LITP")
        cls.mediaArtifactLitp = MediaArtifact.objects.create(
            name="ERIClitp_CXP9024296", number="CXP9024296", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypeOS)
        cls.releaseLitp = Release.objects.create(
            name="litpRelease", track="litpTrack", product=cls.productLitp, masterArtifact=cls.mediaArtifactLitp, created=datetime.now())
        cls.dropLitp = Drop.objects.create(name="1.1", release=cls.releaseLitp, systemInfo="test",
                                           planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildLitp = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="ERIClitp_CXP9024296", mediaArtifact=cls.mediaArtifactLitp,
                                                   drop=cls.dropLitp, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")

        # Main Tests Setup
        cls.product = Product.objects.create(name="ENM")
        cls.mediaArtifact = MediaArtifact.objects.create(
            name="ERICtestiso_CXP1234567", number="CXP1234567", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployType)
        cls.mediaArtifactTestware = MediaArtifact.objects.create(
            name="ERICtestwareiso_CXP7654321", number="CXP7654321", description="test", mediaType="iso", testware=True, category=cls.mediaCatTest, deployType=cls.mediaDeployType)
        cls.release = Release.objects.create(
            name="enmRelease", track="enmTrack", product=cls.product, masterArtifact=cls.mediaArtifact, created=datetime.now())
        cls.release2 = Release.objects.create(
            name="ENM3.0", track="enmTrack", product=cls.product, masterArtifact=cls.mediaArtifact, created=datetime.now())
        cls.drop = Drop.objects.create(name="1.1", release=cls.release, systemInfo="test",
                                       planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.drop2 = Drop.objects.create(name="21.13", release=cls.release2, systemInfo="test",
                                        planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.dropCorrectional = Drop.objects.create(name="1.1.1", release=cls.release, systemInfo="test", planned_release_date=freezeDate,
                                                   actual_release_date=freezeDate, mediaFreezeDate=freezeDate, correctionalDrop=True)
        cls.state1 = States.objects.create(state="failed")
        cls.state2 = States.objects.create(state="passed")
        cls.state3 = States.objects.create(state="in_progress")
        cls.state4 = States.objects.create(state="not_started")

        cls.isoBuild1 = ISObuild.objects.create(version="1.26.9", groupId="com.ericsson.se", artifactId="ERICtestiso_CXP1234567", mediaArtifact=cls.mediaArtifact,
                                                drop=cls.drop, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")
        cls.isoBuild2 = ISObuild.objects.create(version="1.26.10", groupId="com.ericsson.se", artifactId="ERICtestiso_CXP1234567",
                                                mediaArtifact=cls.mediaArtifact, drop=cls.drop, build_date=datetime.now(), arm_repo="test", overall_status=cls.state3)
        cls.isoBuild3 = ISObuild.objects.create(version="1.26.11", groupId="com.ericsson.se", artifactId="ERICtestiso_CXP1234567", mediaArtifact=cls.mediaArtifact,
                                                drop=cls.drop, build_date=buildDate2, arm_repo="test", externally_released=True, externally_released_ip=True, externally_released_rstate="R1AG/0")

        cls.isoBuildTestware = ISObuild.objects.create(version="1.0.10", groupId="com.ericsson.se", artifactId="ERICtestwareiso_CXP7654321",
                                                       mediaArtifact=cls.mediaArtifactTestware, drop=cls.drop, build_date=datetime.now(), arm_repo="test")

        cls.mediaMapping = ProductTestwareMediaMapping.objects.create(
            productIsoVersion=cls.isoBuild1, testwareIsoVersion=cls.isoBuildTestware)
        cls.mediaMapping2 = ProductTestwareMediaMapping.objects.create(
            productIsoVersion=cls.isoBuild2, testwareIsoVersion=cls.isoBuildTestware)
        cls.mediaMapping3 = ProductTestwareMediaMapping.objects.create(
            productIsoVersion=cls.isoBuild3, testwareIsoVersion=cls.isoBuildTestware)

        cls.productSet1 = ProductSet.objects.create(name="ENM")
        cls.productSetRelease1 = ProductSetRelease.objects.create(
            name="1A", number="AOM111111", release=cls.release, productSet=cls.productSet1, masterArtifact=cls.mediaArtifact, updateMasterStatus=1)

        cls.cdbType1 = CDBTypes.objects.create(name="TST", sort_order=5)
        cls.productSetVersion1 = ProductSetVersion.objects.create(
            version="1.1.1", status=cls.state1, current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}", productSetRelease=cls.productSetRelease1, drop=cls.drop)
        cls.productSetVersion2 = ProductSetVersion.objects.create(
            version="1.1.2", status=cls.state2, current_status="{1: 'failed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}", productSetRelease=cls.productSetRelease1, drop=cls.drop)
        cls.productSetVersion3 = ProductSetVersion.objects.create(
            version="21.13.3", status=cls.state2, current_status="{1: 'failed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}", productSetRelease=cls.productSetRelease1, drop=cls.drop2)
        cls.productDropToCDBTypeMap1 = ProductDropToCDBTypeMap.objects.create(
            product=cls.product, drop=cls.drop, type=cls.cdbType1, overallStatusFailure=True, enabled=1)
        cls.productSetVerToCDBTypeMap1 = ProductSetVerToCDBTypeMap.objects.create(
            productSetVersion=cls.productSetVersion1, productCDBType=cls.productDropToCDBTypeMap1, runningStatus=False, override=False)
        cls.productSetVerToCDBTypeMap2 = ProductSetVerToCDBTypeMap.objects.create(
            productSetVersion=cls.productSetVersion2, productCDBType=cls.productDropToCDBTypeMap1, runningStatus=False, override=True)
        cls.productSetVerContent1 = ProductSetVersionContent.objects.create(
            productSetVersion=cls.productSetVersion1, mediaArtifactVersion=cls.isoBuild1, status=cls.state2)
        cls.productSetVerContent2 = ProductSetVersionContent.objects.create(
            productSetVersion=cls.productSetVersion2, mediaArtifactVersion=cls.isoBuild2, status=cls.state2)

        #---------------Product Set Drop Media content----------------#
        cls.productSetDropMediaMapRHELMedia = DropMediaArtifactMapping.objects.create(
            mediaArtifactVersion=cls.isoBuildRHELMedia, released=True, drop=cls.drop, dateCreated=buildDate)
        cls.productSetDropMediaMapRHELPatch = DropMediaArtifactMapping.objects.create(
            mediaArtifactVersion=cls.isoBuildRHELPatch, released=True, drop=cls.drop, dateCreated=buildDate)
        cls.productSetDropMediaMapRHELPatch7 = DropMediaArtifactMapping.objects.create(
            mediaArtifactVersion=cls.isoBuildRHELPatch7, released=True, drop=cls.drop, dateCreated=buildDate)
        cls.productSetDropMediaMapLitp = DropMediaArtifactMapping.objects.create(
            mediaArtifactVersion=cls.isoBuildLitp, released=True, drop=cls.drop, dateCreated=buildDate)

        #-------------------creating Teams and RA'S-------#
        cls.teamLabel = Label.objects.create(name="Team")
        cls.parentLabel = Label.objects.create(name="RA")
        cls.parentElementComp = Component.objects.create(
            element="PlanningAndConfiguration", product=cls.product, label=cls.parentLabel, dateCreated=datetime.now(), deprecated=False)
        cls.parentElementComp1 = Component.objects.create(
            element="AssuranceAndOptimisation", product=cls.product, label=cls.parentLabel, dateCreated=datetime.now(), deprecated=True)
        cls.parentElementComp2 = Component.objects.create(
            element="InactiveTeams", product=cls.product, label=cls.parentLabel, dateCreated=datetime.now(), deprecated=False)
        cls.team2 = Component.objects.create(element="Privileged", product=cls.product,
                                             parent=cls.parentElementComp, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=False)
        cls.team3 = Component.objects.create(element="Privileged1", product=cls.product,
                                             parent=cls.parentElementComp, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=True)
        cls.team4 = Component.objects.create(element="Privileged2", product=cls.product,
                                             parent=cls.parentElementComp1, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=False)
        cls.team5 = Component.objects.create(element="Privileged3", product=cls.product,
                                             parent=cls.parentElementComp1, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=True)
        cls.team6 = Component.objects.create(element="Privileged4", product=cls.product,
                                             parent=cls.parentElementComp2, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=True)
        cls.team7 = Component.objects.create(element="Privileged5", product=cls.product,
                                             parent=cls.parentElementComp2, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=False)

        cls.deliveryGroup1 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(
        ), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated=1)
        cls.deliveryGroup2 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(
        ), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated=1)
        cls.deliveryGroup3 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(
        ), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated=1)
        cls.deliveryGroup4 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(
        ), createdDate=datetime.now(), deliveredDate=datetime.now(), obsoleted=True, autoCreated=1)

        cls.subscriptions = DeliveryGroupSubscription.objects.create(
            user=cls.user, deliveryGroup=cls.deliveryGroup1)

        #---- Data for Delivery Group for KGB Check ----#
        cls.package1 = Package.objects.create(
            name="ERICtestpackage1_CXP7654321")
        cls.pkg1PkgRev1 = PackageRevision.objects.create(package=cls.package1,
                                                         groupId="com.ericsson.oss",
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="failed",
                                                         category=cls.categoryServ,
                                                         version="1.1.1",
                                                         artifactId="ERICtestpackage1_CXP7654321",
                                                         m2type="rpm")
        cls.pkg1PkgRev2 = PackageRevision.objects.create(package=cls.package1,
                                                         artifactId="ERICtestpackage1_CXP7654321",
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         category=cls.categoryServ,
                                                         version="1.1.2")
        cls.pkg1PkgRev3 = PackageRevision.objects.create(package=cls.package1,
                                                         artifactId="ERICtestpackage1_CXP7654321",
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         category=cls.categoryServ,
                                                         version="1.1.3", m2type="rpm")
        cls.package2 = Package.objects.create(
            name="ERICtestpackage2_CXP7654323")
        cls.pkg2PkgRev1 = PackageRevision.objects.create(package=cls.package2,
                                                         artifactId="ERICtestpackage2_CXP7654323",
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         category=cls.categoryServ,
                                                         version="1.1.1")
        cls.pkg2PkgRev2 = PackageRevision.objects.create(package=cls.package2,
                                                         artifactId="ERICtestpackage2_CXP7654323",
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         category=cls.categoryServ,
                                                         version="1.1.2",
                                                         m2type='rpm')
        cls.testware1 = Package.objects.create(
            name="ERICTAFtestpackage_CXP7654322", testware=True, includedInPriorityTestSuite=True)
        cls.testwareRev1 = PackageRevision.objects.create(package=cls.testware1,
                                                          artifactId="ERICTAFtestpackage_CXP7654322",
                                                          date_created=datetime.now(),
                                                          autodrop="latest.Maintrack",
                                                          last_update=datetime.now(),
                                                          category=cls.categoryTest,
                                                          version="1.1.1")
        cls.testwareRev2 = PackageRevision.objects.create(package=cls.testware1,
                                                          artifactId="ERICTAFtestpackage_CXP7654322",
                                                          date_created=datetime.now(),
                                                          autodrop="latest.Maintrack",
                                                          last_update=datetime.now(),
                                                          category=cls.categoryTest,
                                                          version="1.2.1")
        cls.testware2 = Package.objects.create(
            name="ERICTWtestpackage_CXP7654326", testware=True)
        cls.testware2Rev1 = PackageRevision.objects.create(package=cls.testware2,
                                                           artifactId="ERICTWtestpackage_CXP7654326",
                                                           date_created=datetime.now(),
                                                           autodrop="latest.Maintrack",
                                                           last_update=datetime.now(),
                                                           category=cls.categoryTest,
                                                           version="1.1.1")
        cls.testware2Rev2 = PackageRevision.objects.create(package=cls.testware2,
                                                           artifactId="ERICTWtestpackage_CXP7654326",
                                                           date_created=datetime.now(),
                                                           autodrop="latest.Maintrack",
                                                           last_update=datetime.now(),
                                                           category=cls.categoryTest,
                                                           version="1.2.1")

        cls.package3 = Package.objects.create(
            name="ERICtestpackage3_CXP7654324")
        cls.pkg3PkgRev1 = PackageRevision.objects.create(package=cls.package3,
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         artifactId="ERICtestpackage3_CXP7654324",
                                                         category=cls.categoryServ,
                                                         groupId="com.ericsson.oss",
                                                         arm_repo="releases",
                                                         m2type="rpm",
                                                         version="1.1.1")
        cls.pkg3PkgRev2 = PackageRevision.objects.create(package=cls.package3,
                                                         date_created=datetime.now(),
                                                         autodrop="ENM:Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         artifactId="ERICtestpackage3_CXP7654324",
                                                         category=cls.categoryServ,
                                                         groupId="com.ericsson.oss",
                                                         arm_repo="releases",
                                                         m2type="rpm",
                                                         team_running_kgb=cls.team2,
                                                         platform="None",
                                                         version="1.1.2")
        cls.package4 = Package.objects.create(
            name="ERICtestpackage4_CXP7654325")
        cls.pkg4PkgRev1 = PackageRevision.objects.create(package=cls.package4,
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         artifactId="ERICtestpackage4_CXP7654325",
                                                         category=cls.categoryServ,
                                                         groupId="com.ericsson.oss",
                                                         arm_repo="releases",
                                                         m2type="rpm",
                                                         version="1.1.1")
        cls.pkg4PkgRev2 = PackageRevision.objects.create(package=cls.package4,
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         artifactId="ERICtestpackage4_CXP7654325",
                                                         category=cls.categoryServ,
                                                         groupId="com.ericsson.oss",
                                                         arm_repo="releases",
                                                         m2type="rpm",
                                                         version="1.1.2")
        cls.package5 = Package.objects.create(
            name="ERICtestpackage5_CXP6654325")
        cls.pkg5PkgRev1 = PackageRevision.objects.create(package=cls.package5,
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="failed",
                                                         artifactId="ERICtestpackage5_CXP6654325",
                                                         category=cls.categoryServ,
                                                         groupId="com.ericsson.oss",
                                                         arm_repo="releases",
                                                         m2type="rpm",
                                                         version="1.1.1")
        cls.package6 = Package.objects.create(
            name="ERICenmsguiservice_CXP9031574", package_number="CXP9031574")
        cls.productPackageMap = ProductPackageMapping.objects.create(
            product=cls.product, package=cls.package6)

        cls.delGroupMap1 = DeliverytoPackageRevMapping.objects.create(
            deliveryGroup=cls.deliveryGroup1, packageRevision=cls.pkg1PkgRev1, team="Privileged")
        cls.delGroupMap2 = DeliverytoPackageRevMapping.objects.create(
            deliveryGroup=cls.deliveryGroup2, packageRevision=cls.pkg2PkgRev2, team="Privileged")
        cls.teamComp = Component.objects.create(
            element="Ninjas", product=cls.product, parent=cls.parentElementComp, label=cls.teamLabel, dateCreated=datetime.now())
        cls.reasonfornokgb_one = ReasonsForNoKGBStatus.objects.create(
            reason="No Environment at time of KGB", active=True)
        cls.reasonfornokgb_two = ReasonsForNoKGBStatus.objects.create(
            reason="No Jenkins Job for KGB Test", active=True)
        cls.reasonfornokgb_three = ReasonsForNoKGBStatus.objects.create(
            reason="Did not have time to run, i was advised to skip", active=False)
        cls.reasonfornokgb_four = ReasonsForNoKGBStatus.objects.create(
            reason="Other", active=True)
        cls.dropContent = DropPackageMapping.objects.create(drop=cls.drop, package_revision=cls.pkg3PkgRev1, released=True, date_created=datetime.now(
        ), delivery_info="test", kgb_test="passed", testReport="http")
        cls.dropContent2 = DropPackageMapping.objects.create(
            drop=cls.drop, package_revision=cls.pkg2PkgRev2, released=False, date_created=datetime.now(), delivery_info="test", kgb_test="passed")
        cls.isobuildmapping1 = ISObuildMapping.objects.create(
            iso=cls.isoBuild1, drop=cls.drop, package_revision=cls.pkg4PkgRev1)
        cls.isobuildmapping2 = ISObuildMapping.objects.create(
            iso=cls.isoBuild2, drop=cls.drop, package_revision=cls.pkg3PkgRev1)
        cls.isobuildmapping3 = ISObuildMapping.objects.create(
            iso=cls.isoBuild2, drop=cls.drop, package_revision=cls.pkg4PkgRev2)
        cls.isobuildmapping4 = ISObuildMapping.objects.create(
            iso=cls.isoBuild3, drop=cls.drop, package_revision=cls.pkg4PkgRev1)
        cls.isobuildmapping5 = ISObuildMapping.objects.create(
            iso=cls.isoBuild3, drop=cls.drop, package_revision=cls.pkg3PkgRev1)
        cls.isobuildmapping6 = ISObuildMapping.objects.create(
            iso=cls.isoBuild2, drop=cls.drop, package_revision=cls.pkg2PkgRev2)

        cls.isobuildmappingTestware = ISObuildMapping.objects.create(
            iso=cls.isoBuildTestware, drop=cls.drop, package_revision=cls.testwareRev1)
        cls.autoDeliverTeam = AutoDeliverTeam.objects.create(team=cls.team2)

        cls.vmServiceName = VmServiceName.objects.create(name="fakeVM")
        cls.vmServicePackageMapping = VmServicePackageMapping.objects.create(
            service=cls.vmServiceName, package=cls.package1)

        cls.testwareType1 = TestwareType.objects.create(type="RFA250")
        cls.testwareType2 = TestwareType.objects.create(type="RNL")
        cls.testwareTypeMapping = TestwareTypeMapping.objects.create(
            testware_type=cls.testwareType1, testware_artifact=cls.testware1)
        cls.testwareArtifact = TestwareArtifact.objects.create(
            name="ERICTAFkgb_CXP9030739", artifact_number="CXP9030739", description="test", signum="admin")
        cls.testwareRevision = TestwareRevision.objects.create(testware_artifact=cls.testwareArtifact, date_created=datetime.now(
        ), version="1.1.1", groupId="com.ericsson.oss", artifactId="ERICTAFkgb_CXP9030739")
        cls.testwarePackageMapping = TestwarePackageMapping.objects.create(
            testware_artifact=cls.testwareArtifact,  package=cls.package3)
        cls.testResult = TestResults.objects.create(
            testdate="2017-04-10T12:27:35", test_report_directory="http://oss-taf-logs.lmera.ericsson.se/82a8e095-39d6-4e4c-b743-da5102cc575f/")
        cls.testResultMapping = TestResultsToTestwareMap.objects.create(
            testware_revision=cls.testwareRevision, testware_artifact=cls.testwareArtifact, package_revision=cls.pkg3PkgRev2, package=cls.package3, testware_run=cls.testResult)

        cls.testwareArtifact2 = TestwareArtifact.objects.create(
            name="ERICTWkgb_CXP9030740", artifact_number="CXP9030740", description="test", signum="admin")
        cls.testwareRevision2 = TestwareRevision.objects.create(testware_artifact=cls.testwareArtifact2, date_created=datetime.now(
        ), version="1.1.1", groupId="com.ericsson.oss", artifactId="ERICTAFkgb_CXP9030740")
        cls.testwarePackageMapping2 = TestwarePackageMapping.objects.create(
            testware_artifact=cls.testwareArtifact,  package=cls.package4)
        cls.testResult2 = TestResults.objects.create(
            testdate="2017-04-10T12:27:35", test_report_directory="http://oss-taf-logs.lmera.ericsson.se/82a8e095-39d6-4e4c-b743-da5102cc575f/")
        cls.testResultMapping2 = TestResultsToTestwareMap.objects.create(
            testware_revision=cls.testwareRevision2, testware_artifact=cls.testwareArtifact2, package_revision=cls.pkg4PkgRev2, package=cls.package4, testware_run=cls.testResult2)

        # Cloud Native ENM Setup
        # --- cENM Admin
        cls.group3 = Group(name="CN_Delivery_Queue_Admin")
        cls.group3.save()
        cls.group4 = Group(name="cENM_Guards")
        cls.group4.save()
        cls.user3 = User.objects.create_user(
            username='ciadmin', email="ciadmin@ericsson.com", password='12345', first_name="CIadmin", last_name="CI")
        cls.user3.groups.add(cls.group3)
        cls.user3.groups.add(cls.group4)
        cls.user3.save()
        cls.user4 = User.objects.create_user(
            username='ciuser', email="ciuser@ericsson.com", password='12345', first_name="CIuser", last_name="CI")
        cls.user4.save()
        # --- create cnImage data ---
        cls.cnImage1 = CNImage.objects.create(
            image_name="enm-sg-testpackage-1", image_product_number="CXP7654321")
        cls.cnImage2 = CNImage.objects.create(
            image_name="enm-sg-testpackage-2", image_product_number="CXP1234567")
        cls.cnImage3 = CNImage.objects.create(
            image_name="enm-sg-testpackage-3", image_product_number="CXP1111111")
        cls.cnImage1Rev1 = CNImageRevision.objects.create(
            image=cls.cnImage1, created="2021-09-07T12:28:35")
        cls.cnImage2Rev1 = CNImageRevision.objects.create(
            image=cls.cnImage2, created="2021-09-07T12:29:35")
        cls.cnImage1Rev1Content1 = CNImageContent.objects.create(
            image_revision=cls.cnImage1Rev1, package_revision=cls.pkg1PkgRev1)
        cls.cnImage2Rev1Content1 = CNImageContent.objects.create(
            image_revision=cls.cnImage2Rev1, package_revision=cls.pkg2PkgRev1)
        # --- create cnHelmChart data ---
        cls.cnHelmChart1 = CNHelmChart.objects.create(
            helm_chart_name="helm-enm-sg-testpackage-1", helm_chart_product_number="CXP7654321")
        cls.cnHelmChart2 = CNHelmChart.objects.create(
            helm_chart_name="helm-enm-sg-testpackage-2", helm_chart_product_number="CXP1234567")
        cls.cnHelmChart1Rev1 = CNHelmChartRevision.objects.create(
            helm_chart=cls.cnHelmChart1, version="1.0.1-1", created="2021-09-07T13:28:35")
        cls.cnHelmChart2Rev1 = CNHelmChartRevision.objects.create(
            helm_chart=cls.cnHelmChart2, version="1.0.1-1", created="2021-09-07T13:28:35")
        cls.cnImageHelmChartMapping1 = CNImageHelmChartMapping.objects.create(
            image_revision=cls.cnImage1Rev1, helm_chart_revision=cls.cnHelmChart1Rev1)
        cls.cnImageHelmChartMapping2 = CNImageHelmChartMapping.objects.create(
            image_revision=cls.cnImage2Rev1, helm_chart_revision=cls.cnHelmChart2Rev1)
        # --- create cnProductSet/cnProduct data ---
        cls.cnProductSet = CNProductSet.objects.create(
            product_set_name="Cloud Native ENM")
        cls.cnProductType1 = CNProductType.objects.create(
            product_type_name="Integration Chart")
        cls.cnProductType2 = CNProductType.objects.create(
            product_type_name="Integration Value File")
        cls.cnProductType3 = CNProductType.objects.create(
            product_type_name="Deployment Utility")
        cls.cnProductType4 = CNProductType.objects.create(
            product_type_name="CSAR")
        cls.cnProductType5 = CNProductType.objects.create(
            product_type_name="Integration Value")
        cls.cnProductType6 = CNProductType.objects.create(
            product_type_name="Deployment Utility Detail")
        cls.cnProduct1 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="eric-enm-monitoring-integration", product_type=cls.cnProductType1, repo_name="OSS/com.ericsson.oss.containerisation/eric-enm-monitoring-integration", published_link="https://arm.epk.ericsson.se/artifactory/proj-enm-helm")
        cls.cnProduct2 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="eric-enm-infra-integration", product_type=cls.cnProductType1, repo_name="OSS/com.ericsson.oss.containerisation/eric-enm-infra-integration", published_link="https://arm.epk.ericsson.se/artifactory/proj-enm-helm")
        cls.cnProduct3 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="eric-enm-stateless-integration", product_type=cls.cnProductType1, repo_name="OSS/com.ericsson.oss.containerisation/eric-enm-stateless-integration", published_link="https://arm.epk.ericsson.se/artifactory/proj-enm-helm")
        cls.cnProduct4 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="eric-enm-integration", product_type=cls.cnProductType5, repo_name="none", published_link="none")
        cls.cnProduct5 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="eric-enm-pre-deploy-integration", product_type=cls.cnProductType1, repo_name="OSS/com.ericsson.oss.containerisation/eric-enm-pre-deploy-integration", published_link="https://arm.epk.ericsson.se/artifactory/proj-enm-helm")
        cls.cnProduct6 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="eric-enm-integration-production-values", product_type=cls.cnProductType2, repo_name="none", published_link="")
        cls.cnProduct7 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="eric-enm-integration-extra-large-production-values", product_type=cls.cnProductType2, repo_name="none", published_link="")
        cls.cnProduct8 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="enm-installation-package", product_type=cls.cnProductType4, repo_name="OSS/com.ericsson.oss.containerisation/eric-enm-csar-package", published_link="https://arm.epk.ericsson.se/artifactory/proj-enm-helm")
        cls.cnProduct9 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="deployUtil_1", product_type=cls.cnProductType3)
        cls.cnProduct10 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="deployUtil_2", product_type=cls.cnProductType3)
        cls.cnProduct11 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="deployUtil_3", product_type=cls.cnProductType3)
        cls.cnProduct12 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="deployUtil_4", product_type=cls.cnProductType3)
        cls.cnProduct13 = CNProduct.objects.create(
            product_set=cls.cnProductSet, product_name="cenm-deployment-utility", product_type=cls.cnProductType6)
        cls.cnProductSetVersion1 = CNProductSetVersion.objects.create(
            product_set_version="21.14.1", drop_version="21.14", status="{'cENM-Build-Integration-Charts': 'passed', 'cENM-Build-Images': 'passed', 'cENM-Deploy-II-Charts': 'failed', 'cENM-Build-CSAR': 'passed'}", overall_status=cls.state1)
        cls.cnProductSetversion2 = CNProductSetVersion.objects.create(
            product_set_version="21.13.2", drop_version="21.13", status="{}", overall_status=cls.state4)
        cls.cnProductSetversion3 = CNProductSetVersion.objects.create(
            product_set_version="21.13.3", drop_version="21.13", status="{}", overall_status=cls.state4)
        # --- create cn product revision data ---
        cls.cnProductRevision1 = CNProductRevision.objects.create(product=cls.cnProduct5, version="1.17.0-22", product_set_version=cls.cnProductSetversion3, size=40429, created="2022-01-13 17:47:07",
                                                                  gerrit_repo_sha="a29ff4ceb8bfb15f8751f0fd80332fdcc3ac7f90", dev_link="https://arm.epk.ericsson.se/artifactory/proj-enm-dev-internal-helm/eric-enm-pre-deploy-integration/eric-enm-pre-deploy-integration-1.17.0-22.tgz")
        cls.cnProductRevision2 = CNProductRevision.objects.create(product=cls.cnProduct8, version="1.17.0-27", product_set_version=cls.cnProductSetversion3, size=2254856, created="2022-01-13 20:00:20", gerrit_repo_sha="65d265f1c05b93f7c628d3d7ca19d3d7bd679571",
                                                                  dev_link="https://arm902-eiffel004.athtem.eei.ericsson.se:8443/nexus/content/repositories/releases/cENM/csar/enm-installation-package/1.17.0-27/enm-installation-package-1.17.0-27.csar")
        # --- create cn drop data ---
        cls.cnDrop1 = CNDrop.objects.create(
            name="21.13", cnProductSet=cls.cnProductSet, active_date="2020-09-07T00:00:00")
        cls.cnDrop2 = CNDrop.objects.create(
            name="21.14", cnProductSet=cls.cnProductSet, active_date="2122-09-07T00:00:00")
        # --- create cn state data ---
        cls.state4 = States.objects.create(state="not_obsoleted")
        cls.state5 = States.objects.create(state="reverted")
        cls.state6 = States.objects.create(state="not_reverted")
        cls.state7 = States.objects.create(state="conflicts")
        # --- create cn confidence level data ---
        cls.cnConfLevel1 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-Build-Images", required=True, include_baseline=False)
        cls.cnConfLevel2 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-Build-Integration-Charts", required=True, include_baseline=False)
        cls.cnConfLevel3 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-Build-CSAR", required=True, include_baseline=False)
        cls.cnConfLevel4 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-Deploy-II-Charts", required=False, include_baseline=False)
        cls.cnConfLevel5 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-Deploy-II-CSAR", required=False, include_baseline=False)
        cls.cnConfLevel6 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-Deploy-UG-Charts", required=True, include_baseline=False)
        cls.cnConfLevel7 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-UG-Availability", required=True, include_baseline=False)
        cls.cnConfLevel8 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="UG-Performance", required=True, include_baseline=False)
        cls.cnConfLevel9 = RequiredCNConfidenceLevel.objects.create(
            confidence_level_name="cENM-RFA", required=True, include_baseline=True)
        # --- create cn delivery queue sample data
        cls.deliveryGroup5 = DeliveryGroup.objects.create(drop=cls.drop, creator="eaxinta", component=cls.team2, modifiedDate=datetime.now(
        ), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated=1)
        cls.deliveryGroup6 = DeliveryGroup.objects.create(drop=cls.drop, creator="eaxinta", component=cls.team2, modifiedDate=datetime.now(
        ), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated=1)
        cls.deliveryGroup7 = DeliveryGroup.objects.create(drop=cls.drop, creator="eaxinta", component=cls.team2, modifiedDate=datetime.now(
        ), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated=1)
        cls.cnJiraIssue1 = CNJiraIssue.objects.create(
            jiraNumber="TORF-417818", issueType="Information")
        cls.cnJiraIssue2 = CNJiraIssue.objects.create(
            jiraNumber="TORF-417819", issueType="Information")
        cls.cnGerrit1 = CNGerrit.objects.create(gerrit_link="gerritlink1")
        cls.cnGerrit2 = CNGerrit.objects.create(gerrit_link="gerritlink2")
        cls.cnGerrit3 = CNGerrit.objects.create(gerrit_link="gerritlink3")
        cls.cnGerrit4 = CNGerrit.objects.create(gerrit_link="gerritlink4")
        cls.cnGerrit5 = CNGerrit.objects.create(gerrit_link="gerritlink5")
        cls.cnGerrit6 = CNGerrit.objects.create(gerrit_link="gerritlink6")
        cls.cnPipeline1 = CNPipeline.objects.create(pipeline_link="pipeline1")
        cls.cnPipeline2 = CNPipeline.objects.create(pipeline_link="pipeline2")
        cls.cnDeliveryGroup1 = CNDeliveryGroup.objects.create(
            cnDrop=cls.cnDrop2, queued=True, creator="ciadmin", component=cls.team2)
        cls.cnDeliveryGroup2 = CNDeliveryGroup.objects.create(
            cnDrop=cls.cnDrop2, delivered=True, creator="ciadmin", component=cls.team2)
        cls.cnDeliveryGroup3 = CNDeliveryGroup.objects.create(
            cnDrop=cls.cnDrop2, obsoleted=True, creator="ciadmin", component=cls.team2)
        cls.cnDeliveryGroup4 = CNDeliveryGroup.objects.create(
            cnDrop=cls.cnDrop2, deleted=True, creator="ciadmin", component=cls.team2)
        cls.cnDeliveryGroup5 = CNDeliveryGroup.objects.create(
            cnDrop=cls.cnDrop2, cnProductSetVersion=cls.cnProductSetVersion1, delivered=True, creator="ciadmin", component=cls.team2)
        cls.cnDeliveryGroup6 = CNDeliveryGroup.objects.create(
            cnDrop=cls.cnDrop1, deleted=True, creator="ciadmin", component=cls.team2)
        cls.cnDeliveryGroup7 = CNDeliveryGroup.objects.create(
            cnDrop=cls.cnDrop2, delivered=True, creator="ciadmin", component=cls.team2)
        cls.cnDGTocnImageMap1 = CNDGToCNImageToCNGerritMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnImage=cls.cnImage1, cnGerrit=cls.cnGerrit1, state = cls.state4)
        cls.cnDGTocnImageMap2 = CNDGToCNImageToCNGerritMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnImage=cls.cnImage2, cnGerrit=cls.cnGerrit2, state = cls.state4)
        cls.cnDGToInteMap1 = CNDGToCNProductToCNGerritMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnProduct=cls.cnProduct1, cnGerrit=cls.cnGerrit3)
        cls.cnDGToInteMap2 = CNDGToCNProductToCNGerritMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnProduct=cls.cnProduct2, cnGerrit=cls.cnGerrit4)
        cls.cnDGToPipelineMap1 = CNDGToCNPipelineToCNGerritMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnPipeline=cls.cnPipeline1, cnGerrit=cls.cnGerrit5)
        cls.cnDGToPipelineMap2 = CNDGToCNPipelineToCNGerritMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnPipeline=cls.cnPipeline2, cnGerrit=cls.cnGerrit6)
        cls.cnDGToDGMap1 = CNDGToDGMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, deliveryGroup=cls.deliveryGroup5)
        cls.cnDGToDGMap2 = CNDGToDGMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, deliveryGroup=cls.deliveryGroup6)
        cls.cnDgtoJiraMap1 = CNDGToCNJiraIssueMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnJiraIssue=cls.cnJiraIssue1)
        cls.cnDgtoJiraMap2 = CNDGToCNJiraIssueMap.objects.create(
            cnDeliveryGroup=cls.cnDeliveryGroup1, cnJiraIssue=cls.cnJiraIssue2)

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.package.delete()
        cls.categorySW.delete()
        cls.package_revision.delete()
        cls.product.delete()
        cls.mediaArtifact.delete()
        cls.drop.delete()
        cls.deliveryGroup1.delete()
        cls.subscriptions.delete()
        cls.reasonfornokgb_one.delete()
        cls.reasonfornokgb_two.delete()
        cls.reasonfornokgb_three.delete()
        cls.reasonfornokgb_four.delete()


class RestTest(BaseSetUpTest):
    def setUp(self):
        self.client_stub = Client()

    def test_subscriptions_get(self):
        self.client_stub.login(username='testuser', password='12345')
        response = self.client_stub.get('/api/deliverygroup/subscriptions/')
        self.assertEqual(response.status_code, 200)

    def test_subscriptions_post_success(self):
        self.client_stub.login(username='testuser', password='12345')
        response = self.client_stub.post('/api/deliverygroup/subscriptions/',
                                         data='{"deliveryGroup": '+str(self.deliveryGroup1.id)+'}', content_type="application/json")
        self.assertEqual(response.data, "success")
        self.assertEqual(response.status_code, 200)

    def test_subscriptions_post_failure(self):
        self.client_stub.login(username='testuser', password='12345')
        response = self.client_stub.post('/api/deliverygroup/subscriptions/',
                                         data='{"deliveryGroup": 342}', content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_get_artifact_version_data_success(self):
        response = self.client_stub.get(
            "/api/getartifactversiondata/artifact/ERICtest_CXP1234567/version/1.12.3/")
        self.assertEqual(str(response.data['kgb_test']), "not_started")
        self.assertEqual(response.status_code, 200)

    def test_get_artifact_version_data_failure(self):
        response = self.client_stub.get(
            "/api/getartifactversiondata/artifact/ERICtest_CXP1234567/version/1.12.4/")
        self.assertEqual(response.status_code, 404)

    def test_reason_for_no_kgb_active_true_in_list_success(self):
        response = self.client_stub.get(
            "/api/getreasonsfornokbgstatus/active/True")
        reasonList = []
        for item in response.data:
            reasonList.append(str(item['reason']))
        self.assertIn("Other", reasonList)
        self.assertIn("No Jenkins Job for KGB Test", reasonList)
        self.assertIn("No Environment at time of KGB", reasonList)
        self.assertEqual(response.status_code, 200)

    def test_reason_for_no_kgb_active_true_not_in_list_success(self):
        response = self.client_stub.get(
            "/api/getreasonsfornokbgstatus/active/True")
        reasonList = []
        for item in response.data:
            reasonList.append(str(item['reason']))
        self.assertNotIn(
            "Did not have time to run, i was advised to skip", reasonList)
        self.assertEqual(response.status_code, 200)

    def test_reason_for_no_kgb_active_false_in_list_success(self):
        response = self.client_stub.get(
            "/api/getreasonsfornokbgstatus/active/False")
        reasonList = []
        for item in response.data:
            reasonList.append(str(item['reason']))
        self.assertIn(
            "Did not have time to run, i was advised to skip", reasonList)
        self.assertEqual(response.status_code, 200)

    def test_reason_for_no_kgb_active_false_not_in_list_success(self):
        response = self.client_stub.get(
            "/api/getreasonsfornokbgstatus/active/False")
        reasonList = []
        for item in response.data:
            reasonList.append(str(item['reason']))
        self.assertNotIn("Other", reasonList)
        self.assertNotIn("No Jenkins Job for KGB Test", reasonList)
        self.assertNotIn("No Environment at time of KGB", reasonList)
        self.assertEqual(response.status_code, 200)

    def test_reason_for_no_kgb_active_wrong_parameter_failure(self):
        response = self.client_stub.get(
            "/api/getreasonsfornokbgstatus/active/john")
        self.assertEqual(response.status_code, 404)

    def test_validate_same_mediaArtifact_same_version_failure(self):
        response = self.client_stub.post(
            '/CIFWKMediaImport/', data='releaseRepoName=test&groupId=com.ericsson.se&name=ERICtestiso_CXP1234567&version=1.26.10&product=ENM&release=enmRelease&drop=1.1&platform=i386&mediaType=iso', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "1.26.10", status_code=400)

    def test_validate_different_mediaArtifact_failure(self):
        response = self.client_stub.post(
            '/CIFWKMediaImport/', data='releaseRepoName=test&groupId=com.ericsson.se&name=ERICtestiso_CXP9032968&version=1.26.10&product=ENM&release=enmRelease&drop=1.1&platform=i386&mediaType=iso', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response, "ERICtestiso_CXP1234567", status_code=404)

    def test_validate_same_mediaArtifact_different_version_success(self):
        response = self.client_stub.post(
            '/CIFWKMediaImport/', data='releaseRepoName=test&groupId=com.ericsson.se&name=ERICtestiso_CXP1234567&version=1.26.14&product=ENM&release=enmRelease&drop=1.1&platform=i386&mediaType=iso', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.26.14")

    def test_create_delivery_group_post_failure_KGB(self):
        data_expected = "Failure - Package Revision Validation"
        response = self.client_stub.post('/api/createDeliveryGroup/',
                                         data='{"creator": "testuser", "artifacts": "ERICtestpackage1_CXP7654321::1.1.1@@ERICtestpackage2_CXP7654323::1.1.1@@ERICTAFtestpackage_CXP7654322::1.1.1", "cenmDgList": "", "jiraIssues": "CIP-14500,CIP-12345,CIP-14400","missingDependencies": "True","team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data[0].get("result"), data_expected)

    def test01_create_delivery_group_post_success_KGB(self):
        data_expected = "Success - Delivery Group was Created"
        response = self.client_stub.post('/api/createDeliveryGroup/',
                                         data='{"creator": "testuser","artifacts": "ERICtestpackage1_CXP7654321::1.1.2@@ERICtestpackage2_CXP7654323::1.1.1@@ERICTAFtestpackage_CXP7654322::1.1.1", "cenmDgList": "", "jiraIssues": "CIP-14500,CIP-12345,CIP-14400","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data[0].get("result"), data_expected)

    def test02_check_delivery_group_package_rev_KGB_Results(self):
        responsePost = self.client_stub.post('/api/createDeliveryGroup/',
                                             data='{"creator": "testuser","artifacts": "ERICtestpackage1_CXP7654321::1.1.2@@ERICtestpackage2_CXP7654323::1.1.1@@ERICTAFtestpackage_CXP7654322::1.1.1", "cenmDgList": "", "jiraIssues": "CIP-14500,CIP-12345,CIP-14400","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        response = self.client_stub.get(
            "/api/deliveryGroup/9/artifact/ERICtestpackage1_CXP7654321/KGBresults/")
        kgbList = []
        for item in response.data:
            kgbList.append(str(item['kgb']))
        self.assertIn("passed", kgbList)
        self.assertEqual(response.status_code, 200)

    def test03_check_delivery_group_KGB_Results(self):
        responsePost = self.client_stub.post('/api/createDeliveryGroup/',
                                             data='{"creator": "testuser","artifacts": "ERICtestpackage1_CXP7654321::1.1.2@@ERICtestpackage2_CXP7654323::1.1.1@@ERICTAFtestpackage_CXP7654322::1.1.1", "cenmDgList": "", "jiraIssues": "CIP-14500,CIP-12345,CIP-14400","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        response = self.client_stub.get("/api/deliveryGroup/10/KGBresults/")
        kgbList = []
        for item in response.data:
            kgbList.append(str(item['kgb']))
        self.assertIn("passed", kgbList)
        self.assertEqual(response.status_code, 200)

    def test_check_drop_KGB_Results(self):
        response = self.client_stub.get(
            "/api/product/ENM/drop/1.1/KGBresults/")
        kgbList = []
        for item in response.data:
            kgbList.append(str(item['kgb']))
        self.assertIn("passed", kgbList)
        self.assertEqual(response.status_code, 200)

    def test_check_drop_package_rev_KGB_Results(self):
        response = self.client_stub.get(
            "/api/product/ENM/drop/1.1/artifact/ERICtestpackage3_CXP7654324/KGBresults/")
        kgbList = []
        for item in response.data:
            kgbList.append(str(item['kgb']))
        self.assertIn("passed", kgbList)
        self.assertEqual(response.status_code, 200)

    def test_check_media_artifact_KGB_Results(self):
        responseMApost = self.client_stub.post(
            '/CIFWKMediaImport/', data='releaseRepoName=test&groupId=com.ericsson.se&name=ERICtestiso_CXP1234567&version=1.1.1&product=ENM&release=enmRelease&drop=1.1&mediaType=iso', content_type="application/x-www-form-urlencoded")
        response = self.client_stub.get(
            "/api/mediaArtifact/ERICtestiso_CXP1234567/version/1.1.1/KGBresults/")
        kgbList = []
        for item in response.data:
            kgbList.append(str(item['kgb']))
        self.assertIn("passed", kgbList)
        self.assertEqual(response.status_code, 200)

    def test_check_media_artifact_package_rev_KGB_Results(self):
        responseMApost = self.client_stub.post(
            '/CIFWKMediaImport/', data='releaseRepoName=test&groupId=com.ericsson.se&name=ERICtestiso_CXP1234567&version=1.1.1&product=ENM&release=enmRelease&drop=1.1&mediaType=iso', content_type="application/x-www-form-urlencoded")
        response = self.client_stub.get(
            "/api/mediaArtifact/ERICtestiso_CXP1234567/version/1.1.1/artifact/ERICtestpackage3_CXP7654324/KGBresults/")
        kgbList = []
        for item in response.data:
            kgbList.append(str(item['kgb']))
        self.assertIn("passed", kgbList)
        self.assertEqual(response.status_code, 200)

    def test_create_delivery_group_with_artifact_not_in_product_baseline_success(self):
        data_expected = "Success - Delivery Group was Created"
        response = self.client_stub.post(
            '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICtestpackage1_CXP7654321::1.1.2", "cenmDgList": "", "jiraIssues": "CIP-14500","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data[0].get("result"), data_expected)

    def test_create_delivery_group_with_artifact_not_in_product_baseline_failure(self):
        data_expected = "Failure - Artifact In Baseline"
        response = self.client_stub.post(
            '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICtestpackage3_CXP7654324::1.1.1", "cenmDgList": "", "jiraIssues": "CIP-14500","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data[0].get("result"), data_expected)

    def test_create_delivery_group_with_testware_artifact_not_in_product_baseline_success(self):
        data_expected = "Success - Delivery Group was Created"
        response = self.client_stub.post(
            '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICTAFtestpackage_CXP7654322::1.2.1", "cenmDgList": "", "jiraIssues": "CIP-14500","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data[0].get("result"), data_expected)

    def test_create_delivery_group_with_twtestware_artifact_not_in_product_baseline_success(self):
        data_expected = "Success - Delivery Group was Created"
        response = self.client_stub.post(
            '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICTWtestpackage_CXP7654326::1.2.1", "cenmDgList": "", "jiraIssues": "CIP-14500","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data[0].get("result"), data_expected)

    def test_create_delivery_group_with_testware_artifact_not_in_product_baseline_failure(self):
        data_expected = "Failure - Artifact In Baseline"
        response = self.client_stub.post(
            '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICTAFtestpackage_CXP7654322::1.1.1", "cenmDgList": "", "jiraIssues": "CIP-14500","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data[0].get("result"), data_expected)

    # def test_jira_validation(self):
    #     data_expected = "WARNING: Current Jira type (Support) is not supported for delivery queue. Please change Jira Ticket number!"
    #     response = self.client_stub.get(
    #         "/api/tools/jiravalidation/issue/CIS-41992/")
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data[0].get("warning"), data_expected)

    # def test_create_delivery_group_with_invalid_jira_issue_type(self):
    #     data_expected = "Failure - Jira Issues Validation"
    #     response = self.client_stub.post(
    #         '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICtestpackage1_CXP7654321::1.1.2", "cenmDgList": "", "jiraIssues": "CIS-41992","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
    #     self.assertEqual(response.status_code, 404)
    #     self.assertEqual(response.data[0].get("result"), data_expected)

    def test_get_delivery_queued_artifacts_in_drop(self):
        response = self.client_stub.get(
            "/api/product/ENM/drop/1.1/deliveryqueue/queued/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("fakeVM", response.content)

    def test_get_diff_between_isos_updated_and_added(self):
        data_expected = '[{"groupId" : "com.ericsson.se","artifactId" : "ERICtestiso_CXP1234567","previousVersion" : "1.26.9","version" : "1.26.10","Updated":[{"category": "service", "previousVersion": "1.1.1", "version": "1.1.2", "downgrade": "false", "groupId": "com.ericsson.oss", "artifactId": "ERICtestpackage4_CXP7654325"}],"Added":[{"category": "service", "version": "1.1.1", "groupId": "com.ericsson.oss", "artifactId": "ERICtestpackage3_CXP7654324"},{"category": "service", "version": "1.1.2", "groupId": "None", "artifactId": "ERICtestpackage2_CXP7654323"}]}]'
        response = self.client_stub.get(
            "/getISOContentDelta/?previousISOVersion=1.26.9&isoVersion=1.26.10&product=ENM&drop=1.1&previousDrop=1.1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data_expected, response.content)

    def test_get_diff_between_isos_updated_and_added_using_groupId(self):
        data_expected = '[{"groupId" : "com.ericsson.se","artifactId" : "ERICtestiso_CXP1234567","previousVersion" : "1.26.9","version" : "1.26.10","Updated":[{"category": "service", "previousVersion": "1.1.1", "version": "1.1.2", "downgrade": "false", "groupId": "com.ericsson.oss", "artifactId": "ERICtestpackage4_CXP7654325"}],"Added":[{"category": "service", "version": "1.1.1", "groupId": "com.ericsson.oss", "artifactId": "ERICtestpackage3_CXP7654324"},{"category": "service", "version": "1.1.2", "groupId": "None", "artifactId": "ERICtestpackage2_CXP7654323"}]}]'
        response = self.client_stub.get(
            "/getISOContentDelta/?isoGroup=com.ericsson.se&isoArtifact=ERICtestiso_CXP1234567&isoVersion=1.26.10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data_expected, response.content)

    def test_get_diff_between_isos_rpm_version_downgraded(self):
        data_expected = '[{"groupId" : "com.ericsson.se","artifactId" : "ERICtestiso_CXP1234567","previousVersion" : "1.26.10","version" : "1.26.11","Obsoleted":[{"category": "service", "version": "1.1.2", "groupId": "None", "artifactId": "ERICtestpackage2_CXP7654323"}],"Updated":[{"category": "service", "previousVersion": "1.1.2", "version": "1.1.1", "downgrade": "true", "groupId": "com.ericsson.oss", "artifactId": "ERICtestpackage4_CXP7654325"}]}]'
        response = self.client_stub.get(
            "/getISOContentDelta/?previousISOVersion=1.26.10&isoVersion=1.26.11&product=ENM&drop=1.1&previousDrop=1.1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data_expected, response.content)

    def test_get_diff_between_isos_rpm_version_downgraded_using_groupId(self):
        data_expected = '[{"groupId" : "com.ericsson.se","artifactId" : "ERICtestiso_CXP1234567","previousVersion" : "1.26.10","version" : "1.26.11","Obsoleted":[{"category": "service", "version": "1.1.2", "groupId": "None", "artifactId": "ERICtestpackage2_CXP7654323"}],"Updated":[{"category": "service", "previousVersion": "1.1.2", "version": "1.1.1", "downgrade": "true", "groupId": "com.ericsson.oss", "artifactId": "ERICtestpackage4_CXP7654325"}]}]'
        response = self.client_stub.get(
            "/getISOContentDelta/?isoGroup=com.ericsson.se&isoArtifact=ERICtestiso_CXP1234567&isoVersion=1.26.11")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data_expected, response.content)

    def test_get_delivery_queue_delivered_artifacts_in_drop(self):
        response = self.client_stub.get(
            "/api/product/ENM/drop/1.1/deliveryqueue/delivered/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual("[]", response.content)

    def test_get_delivery_queue_queued_artifacts_in_drop(self):
        response = self.client_stub.get(
            "/api/product/ENM/drop/1.1/deliveryqueue/queued/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '"autoCreated":"True","bugOrTR":"False","parentElement":"PlanningAndConfiguration","creator":"edarbyr","artifacts":[{"category":"service","sprintVersionCheck":"None","artifact":"ERICtestpackage2', response.content)

    def test_create_delivery_group_with_unauthorised_snapshot(self):
        data_expected = "Unauthorised SNAPSHOT found - ERICenmconfiguration_CXP9031455::1.0.6-SNAPSHOT"
        response = self.client_stub.post(
            '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICTAFtestpackage_CXP7654322::1.2.1@@ERICenmconfiguration_CXP9031455::1.0.6-SNAPSHOT", "cenmDgList": "", "jiraIssues": "CIP-14500","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data[0].get("error"), data_expected)

    def test_create_delivery_group_with_authorised_snapshot(self):
        data_expected = "Success - Delivery Group was Created"
        response = self.client_stub.post(
            '/api/createDeliveryGroup/', data='{"creator": "testuser","artifacts": "ERICTAFtestpackage_CXP7654322::1.2.1@@ERICenmdeploymenttemplates_CXP9031758::1.0.6-SNAPSHOT", "cenmDgList": "", "jiraIssues": "CIP-14500","missingDependencies": "True", "team": "Ninjas","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data[0].get("result"), data_expected)

    def test_get_product_set_status(self):
        response = self.client_stub.get("/api/getProductSetStatus/ENM/1.1.1/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('{"status":"passed"}', response.content)

    def test_get_product_set_status_override(self):
        response = self.client_stub.get("/api/getProductSetStatus/ENM/1.1.2/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('{"status":"passed"}', response.content)

    def test_get_product_set_diff(self):
        data_expected = '[{"previousVersion" : "1.1.1","version" : "1.1.2","Updated":[{"product": "ENM", "previousDrop": "1.1", "drop": "1.1", "previousVersion": "1.26.9", "version": "1.26.10", "groupId": "com.ericsson.se", "artifactId": "ERICtestiso_CXP1234567"}]}]'
        response = self.client_stub.get(
            '/compareProductSets/?externalCall=true&product=ENM&current=1.1.2&drop=1.1&json=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_get_all_product_sets(self):
        data_expected = '{"productSets":[{"product":"ENM","name":"ENM"}]}'
        response = self.client_stub.get('/api/productSet/list/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_get_good_product_set_version(self):
        data_expected = "1.1.2"
        response = self.client_stub.get(
            "/getLastGoodProductSetVersion/?drop=1.1&productSet=ENM")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_get_good_product_set_version_confidenceLevel_successful(self):
        data_expected = "1.1.1"
        response = self.client_stub.get(
            "/getLastGoodProductSetVersion/?drop=1.1&productSet=ENM&confidenceLevel=TST")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_get_good_product_set_version_confidenceLevel_None(self):
        data_expected = "Issue getting Confidence Level"
        response = self.client_stub.get(
            "/getLastGoodProductSetVersion/?drop=1.1&productSet=ENM&confidenceLevel=MTE")
        self.assertEqual(response.status_code, 200)
        self.assertIn(data_expected, response.content)

    def test_artifactAssociation_all_successful(self):
        data_expected = '[{"artifacts":[],"parentElement":"InactiveTeams","team":"Privileged4"},{"artifacts":[],"parentElement":"InactiveTeams","team":"Privileged5"},{"artifacts":[],"parentElement":"PlanningAndConfiguration","team":"Privileged"},{"artifacts":[],"parentElement":"PlanningAndConfiguration","team":"Ninjas"}]'
        response = self.client_stub.get('/api/aam/label/all/lookup/all/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_artifactAssociation_RA_deprecated_successful(self):
        data_expected = '[{"artifacts":"","parentElement":"","team":""}]'
        response = self.client_stub.get(
            '/api/aam/label/parentElement/lookup/AssuranceAndOptimisation/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_artifactAssociation_RA_successful(self):
        data_expected = '[{"artifacts":[],"parentElement":"PlanningAndConfiguration","team":"Privileged"},{"artifacts":[],"parentElement":"PlanningAndConfiguration","team":"Ninjas"}]'
        response = self.client_stub.get(
            '/api/aam/label/parentElement/lookup/PlanningAndConfiguration/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_artifactAssociation_Team_deprecated_successful(self):
        data_expected = '[{"artifacts":"","parentElement":"","team":""}]'
        response = self.client_stub.get(
            '/api/aam/label/team/lookup/Privileged3/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_artifactAssociation_Team_successful(self):
        data_expected = '[{"artifacts":[],"parentElement":"PlanningAndConfiguration","team":"Privileged"}]'
        response = self.client_stub.get(
            '/api/aam/label/team/lookup/Privileged/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_artifactAssociation_InvalidTeamName_StatusCode_NotFound(self):
        data_expected = '[{"artifacts":"","parentElement":"","team":""}]'
        response = self.client_stub.get(
            '/api/aam/label/team/lookup/asdkfjaskfafas/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_artifactAssociation_InvalidRAName_StatusCode_NotFound(self):
        data_expected = '[{"artifacts":"","parentElement":"","team":""}]'
        response = self.client_stub.get(
            '/api/aam/label/parentElement/lookup/dgagsdagasg/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_get_latest_passed_kgb_for_artifact_success(self):
        data_expected = '{"artifactKGBdata":{"testResult":"passed","intendedDrop":"ENM:Maintrack","nexusURL":"https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/releases/com/ericsson/oss/ERICtestpackage3_CXP7654324/1.1.2/ERICtestpackage3_CXP7654324-1.1.2.rpm","m2Type":"rpm","number":"None","artifact":"ERICtestpackage3_CXP7654324","testReport":"http://oss-taf-logs.lmera.ericsson.se/82a8e095-39d6-4e4c-b743-da5102cc575f/","testReportDate":"2017-04-10T12:27:35","mediaCategory":"service","snapshotReport":"False","groupId":"com.ericsson.oss","testware":["ERICTAFkgb_CXP9030739"],"rState":"R1B02","platform":"None","version":"1.1.2","team":"PlanningAndConfiguration - Privileged","deliveryDrop":null}}'
        response = self.client_stub.get(
            "/api/artifact/ERICtestpackage3_CXP7654324/latestPassedKGB/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_get_latest_passed_kgb_for_artifact_failure_artifact_not_found(self):
        data_expected = '{"ERROR":"Issue getting Latest KGB Information: Package matching query does not exist."}'
        response = self.client_stub.get(
            "/api/artifact/ERICtest_CXP7654324/latestPassedKGB/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_get_latest_passed_kgb_for_artifact_failure_passed_kgb_not_found(self):
        data_expected = '{"ERROR":"Issue getting Latest KGB Information - No Passed KGB Found"}'
        response = self.client_stub.get(
            "/api/artifact/ERICtestpackage5_CXP6654325/latestPassedKGB/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_getHighLevelComponents_successful(self):
        data_expected = '{"Parent": [{"name": "InactiveTeams"}, {"name": "PlanningAndConfiguration"}]}'
        response = self.client_stub.get('/ENM/getHighLevelComponents/.json/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_childComponentsInParentComponent_successful(self):
        data_expected = '{"ChildComponents": ["Privileged4", "Privileged5"]}'
        response = self.client_stub.get(
            '/childComponentsInParentComponent/?product=ENM&parentComponent=InactiveTeams')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_childComponentsInParentComponent_failure(self):
        data_expected = '[{"error": "Component Inactive does not exist"}]'
        response = self.client_stub.get(
            '/childComponentsInParentComponent/?product=ENM&parentComponent=Inactive')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_packagesInComponent_successful(self):
        data_expected = '{"Componentpackages": ["None"]}'
        response = self.client_stub.get(
            '/packagesInComponent/?product=ENM&parentValue=PlanningAndConfiguration&childValue=Privileged')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_getProductLabels_successful(self):
        data_expected = '{"Label": [{"name": "RA"}]}'
        response = self.client_stub.get('/ENM/getProductLabels/.json/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_getProductLabels_failure(self):
        data_expected = '[{"error": "Product fsdf does not exist"}]'
        response = self.client_stub.get('/fsdf/getProductLabels/.json/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_getParentComponentsOfLabel_success(self):
        data_expected = '{"Parents": [{"name": "PlanningAndConfiguration"}, {"name": "InactiveTeams"}]}'
        response = self.client_stub.get(
            '/ENM/ra/getParentComponentsOfLabel/.json/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_getParentComponentsOfLabel_failure(self):
        data_expected = '[{"error": "Label ta does not exist"}]'
        response = self.client_stub.get(
            '/ENM/ta/getParentComponentsOfLabel/.json/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_updateTestStatus_success(self):
        data_expected = 'Privileged'
        utils.updateTestStatus('ERICtestpackage4_CXP7654325', '1.1.1', 'rpm', 'kgb', 'passed',
                               'None', 'sdadff', 'Privileged', 'PlanningAndConfiguration', 'com.ericsson.oss')
        teamInDB = PackageRevision.objects.get(
            artifactId='ERICtestpackage4_CXP7654325', version='1.1.1').team_running_kgb.element
        self.assertEqual(teamInDB, data_expected)
        data_expected = None
        utils.updateTestStatus('ERICtestpackage4_CXP7654325', '1.1.1', 'rpm', 'kgb', 'passed',
                               'None', 'sdadff', 'Privileged1', 'PlanningAndConfiguration', 'com.ericsson.oss')
        teamInDB = PackageRevision.objects.get(
            artifactId='ERICtestpackage4_CXP7654325', version='1.1.1').team_running_kgb
        self.assertEqual(teamInDB, data_expected)

    def test_updateTestStatus_deprecated_parent_Element_success(self):
        data_expected = None
        utils.updateTestStatus('ERICtestpackage4_CXP7654325', '1.1.1', 'rpm', 'kgb', 'passed',
                               'None', 'sdadff', 'Privileged2', 'AssuranceAndOptimisation', 'com.ericsson.oss')
        teamInDB = PackageRevision.objects.get(
            artifactId='ERICtestpackage4_CXP7654325', version='1.1.1').team_running_kgb
        self.assertEqual(teamInDB, data_expected)
        data_expected = None
        utils.updateTestStatus('ERICtestpackage4_CXP7654325', '1.1.1', 'rpm', 'kgb', 'passed',
                               'None', 'sdadff', 'Privileged3', 'AssuranceAndOptimisation', 'com.ericsson.oss')
        teamInDB = PackageRevision.objects.get(
            artifactId='ERICtestpackage4_CXP7654325', version='1.1.1').team_running_kgb
        self.assertEqual(teamInDB, data_expected)

    def test_historical_data_team_deprecation_success(self):
        data_expected = '{"artifactKGBdata":{"testResult":"passed","intendedDrop":"ENM:Maintrack","nexusURL":"https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/releases/com/ericsson/oss/ERICtestpackage3_CXP7654324/1.1.2/ERICtestpackage3_CXP7654324-1.1.2.rpm","m2Type":"rpm","number":"None","artifact":"ERICtestpackage3_CXP7654324","testReport":"http://oss-taf-logs.lmera.ericsson.se/82a8e095-39d6-4e4c-b743-da5102cc575f/","testReportDate":"2017-04-10T12:27:35","mediaCategory":"service","snapshotReport":"False","groupId":"com.ericsson.oss","testware":["ERICTAFkgb_CXP9030739"],"rState":"R1B02","platform":"None","version":"1.1.2","team":"PlanningAndConfiguration - Privileged","deliveryDrop":null}}'
        response = self.client_stub.get(
            '/api/artifact/ERICtestpackage3_CXP7654324/latestPassedKGB/')
        self.assertEqual(response.content, data_expected)
        teamValue = Component.objects.get(element='Privileged')
        teamValue.deprecated = True
        teamValue.save()
        response1 = self.client_stub.get(
            '/api/artifact/ERICtestpackage3_CXP7654324/latestPassedKGB/')
        self.assertEqual(response1.content, data_expected)
        teamValue.deprecated = False
        teamValue.save()

    def test_drop_contents_team_deprecation_success(self):
        data_expected = '[{"mediaPath": "None", "number": null, "kgb": "passed", "testReport": "http", "mediaCategory": "service", "group": "com.ericsson.oss", "name": "ERICtestpackage3_CXP7654324", "url": "https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/releases/com/ericsson/oss/ERICtestpackage3_CXP7654324/1.1.1/ERICtestpackage3_CXP7654324-1.1.1.rpm", "platform": "None", "version": "1.1.1", "kgbSnapshotReport": false, "deliveryDrop": "1.1", "type": "rpm"}]'
        response = self.client_stub.post(
            '/getDropContents/?drop=1.1&product=ENM')
        self.assertEqual(response.content, data_expected)
        teamValue = Component.objects.get(element='Privileged')
        teamValue.deprecated = True
        teamValue.save()
        response1 = self.client_stub.get(
            '/getDropContents/?drop=1.1&product=ENM')
        self.assertEqual(response1.content, data_expected)
        teamValue.deprecated = False
        teamValue.save()

    def test_create_delivery_group_deprecated_team(self):
        data_expected = '[{"result":"Failure - Team Validation","error":"The Team: Privileged1 is deprecated - Component matching query does not exist."}]'
        response = self.client_stub.post('/api/createDeliveryGroup/',
                                         data='{"creator": "testuser", "artifacts": "ERICtestpackage1_CXP7654321::1.1.2", "jiraIssues": "CIP-14500","missingDependencies": "True","team": "Privileged1","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, data_expected)

    def test_getArtifactSize_product_ENM_success(self):
        data_expected = '7536'
        artifactSize, statusCode = utils.getArtifactSize(
            'ERICenmsguiservice_CXP9031574', '1.10.4', 'com.ericsson.oss.servicegroupcontainers', 'rpm', 'releases')
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 200)

    def test_getArtifactSize_product_ENM_failure(self):
        data_expected = 'Issue getting Size of the artifact: https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/service/local/repo_groups/public/content/com/ericsson/oss/sroupcontainers/ERICenmsguiservice_CXP9031574/1.10.4/ERICenmsguiservice_CXP9031574-1.10.4.rpm?describe=info'
        artifactSize, statusCode = utils.getArtifactSize(
            'ERICenmsguiservice_CXP9031574', '1.10.4', 'com.ericsson.oss.sroupcontainers', 'rpm', 'releases')
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 404)

    def test_getArtifactSize_product_ENM_Missing_Value_failure(self):
        data_expected = 'Issue getting Size of the artifact: https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/service/local/repo_groups/public/content//ERICenmsguiservice_CXP9031574/1.10.4/ERICenmsguiservice_CXP9031574-1.10.4.rpm?describe=info'
        artifactSize, statusCode = utils.getArtifactSize(
            'ERICenmsguiservice_CXP9031574', '1.10.4', '', 'rpm', 'releases')
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 404)

    def test_cifwkPackageImport_product_ENM_success(self):
        data_expected = 'was imported on'
        response = self.client_stub.post(
            '/cifwkPackageImport/', data='packageName=ERICenmsguiservice_CXP9031574&version=1.10.4&groupId=com.ericsson.oss.servicegroupcontainers&signum=enapkaa&m2Type=rpm&intendedDrop=1.1&product=ENM&repository=releases&platform=none&mediaCategory=service', content_type="application/x-www-form-urlencoded")
        self.assertContains(response, data_expected)
        self.assertEqual(response.status_code, 200)

    def test_cifwkPackageImport_product_ENM_failure(self):
        data_expected = 'Issue getting Size of the artifact:'
        response = self.client_stub.post(
            '/cifwkPackageImport/', data='packageName=ERICenmsguiservice_CXP9031574&version=1.10.4&groupId=com.ericsson.oss.serainers&signum=enapkaa&m2Type=rpm&intendedDrop=1.1&product=ENM&repository=releases&platform=none&mediaCategory=service', content_type="application/x-www-form-urlencoded")
        self.assertContains(response, data_expected)

    def test_getMediaArtifactSize_product_ENM_success(self):
        data_expected = '18590838784'
        artifactSize, statusCode = utils.getMediaArtifactSize(
            'ERICenm_CXP9027091', '2.27.121', 'com.ericsson.oss', 'iso')
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 200)

    def test_getMediaArtifactSize_product_ENM_failure(self):
        data_expected = 'Issue getting Size of the artifact: https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/service/local/repositories/enm_iso_local/content/om/ericsson/oss/ERICenm_CXP9027091/1.40.9/ERICenm_CXP9027091-1.40.9.iso?describe=info'
        artifactSize, statusCode = utils.getMediaArtifactSize(
            'ERICenm_CXP9027091', '1.40.9', 'om.ericsson.oss', 'iso')
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 404)

    def test_getMediaArtifactSize_product_ENM_Missing_Value_failure(self):
        data_expected = 'Issue getting Size of the artifact: https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/service/local/repositories/enm_iso_local/content//ERICenm_CXP9027091/1.40.9/ERICenm_CXP9027091-1.40.9.iso?describe=info'
        artifactSize, statusCode = utils.getMediaArtifactSize(
            'ERICenm_CXP9027091', '1.40.9', '', 'iso')
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 404)

    def test_getMediaArtifactSize_product_ENM_Testware_success(self):
        data_expected = '627824640'
        artifactSize, statusCode = utils.getMediaArtifactSize(
            'ERICenmtestware_CXP9027746', '1.57.102', 'com.ericsson.oss', 'iso', True)
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 200)

    def test_getMediaArtifactSize_product_ENM_Testware_failure(self):
        data_expected = 'Issue getting Size of the artifact: https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/service/local/repo_groups/public/content/com/ericsson/oss/ERICenmtestware_CXP9027746/1.0.100/ERICenmtestware_CXP9027746-1.0.100.iso?describe=info'
        artifactSize, statusCode = utils.getMediaArtifactSize(
            'ERICenmtestware_CXP9027746', '1.0.100', 'com.ericsson.oss', 'iso', True)
        self.assertEqual(artifactSize, data_expected)
        self.assertEqual(statusCode, 404)

    def test_get_nexus_url(self):
        response = self.client_stub.get(
            '/api/artifact/ERICtestpackage1_CXP7654321/version/1.1.1/nexusUrl/')
        self.assertContains(response, "url")
        self.assertContains(response, "arm1s11")
        self.assertEqual(response.status_code, 200)

    def test_get_local_nexus_url(self):
        response = self.client_stub.get(
            '/api/artifact/ERICtestpackage1_CXP7654321/version/1.1.1/nexusUrl/?local=true')
        self.assertContains(response, "url")
        self.assertContains(response, "arm901")
        self.assertEqual(response.status_code, 200)

    def test_get_nexus_url_failure_package(self):
        response = self.client_stub.get(
            '/api/artifact/ERICtestpackage1_CXP76543/version/1.1.1/nexusUrl/')
        self.assertContains(response, "error", status_code=404)
        self.assertContains(
            response, "Package Revision with Given Artifact ID", status_code=404)
        self.assertEqual(response.status_code, 404)

    def test_get_nexus_url_failure_nexus_url(self):
        response = self.client_stub.get(
            '/api/artifact/ERICtestpackage2_CXP7654323/version/1.1.1/nexusUrl/')
        self.assertContains(response, "error", status_code=404)
        self.assertContains(
            response, "Nexus URL unavailable for given Artifact ID and Version", status_code=404)
        self.assertEqual(response.status_code, 404)

    def test_getProductwareToTestwareMediaMapping_success(self):
        data_expected = '{"productwareMediaArtifact":"ERICtestiso_CXP1234567","productwareMediaArtifactVersion":"1.26.10","testwareMediaArtifactVersions":["1.0.10"],"testwareMediaArtifact":"ERICtestwareiso_CXP7654321"}'
        response = self.client_stub.get(
            '/api/getProductwareToTestwareMediaMapping/mediaArtifact/ERICtestiso_CXP1234567/version/1.26.10/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_getProductwareToTestwareMediaMapping_failure(self):
        response = self.client_stub.get(
            '/api/getProductwareToTestwareMediaMapping/mediaArtifact/ERICtestiso_CXP1234567/version/1.0.99/')
        self.assertEqual(response.status_code, 404)

    def test_getProductwareToTestwareMediaMappingByDrop_success(self):
        data_expected = '{"mediaArtifactMappingData":[{"productwareMediaArtifact":"ERICtestiso_CXP1234567","productwareMediaArtifactVersion":"1.26.11","testwareMediaArtifactVersions":["1.0.10"],"testwareMediaArtifact":"ERICtestwareiso_CXP7654321"},{"productwareMediaArtifact":"ERICtestiso_CXP1234567","productwareMediaArtifactVersion":"1.26.10","testwareMediaArtifactVersions":["1.0.10"],"testwareMediaArtifact":"ERICtestwareiso_CXP7654321"},{"productwareMediaArtifact":"ERICtestiso_CXP1234567","productwareMediaArtifactVersion":"1.26.9","testwareMediaArtifactVersions":["1.0.10"],"testwareMediaArtifact":"ERICtestwareiso_CXP7654321"}]}'
        response = self.client_stub.get(
            '/api/getProductwareToTestwareMediaMapping/product/ENM/drop/1.1/mediaArtifact/ERICtestiso_CXP1234567/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, data_expected)

    def test_getProductwareToTestwareMediaMappingByDrop_failure(self):
        response = self.client_stub.get(
            '/api/getProductwareToTestwareMediaMapping/product/ENM/drop/1.1.99/mediaArtifact/ERICtestiso_CXP1234567/')
        self.assertEqual(response.status_code, 404)

    def test_get_media_artifact_from_hub_nexus_success(self):
        status, returnCode = utils.checkMediaArtifactVerInNexus(
            "ERICenm_CXP9027091", "1.94.116", "com.ericsson.oss", "iso")
        self.assertEqual(returnCode, 200)
        self.assertEqual(status, True)

    def test_get_media_artifact_from_hub_nexus_failure(self):
        status, returnCode = utils.checkMediaArtifactVerInNexus(
            "ERICenm_CXP9027091", "1.0.1", "com.ericsson.oss", "iso")
        self.assertEqual(returnCode, 200)
        self.assertEqual(status, False)

    def test_get_latest_drop_validatingDropForDeliveryGroupCreation_success(self):
        data_expected = "21.13"
        drop = utils.validatingDropForDeliveryGroupCreation(None, "ENM", None)
        self.assertEqual(drop['name'], data_expected)

    def test_mediaArtifact_delivery_to_latest_drop_success(self):
        data_expected = "Drop 1.1"
        response = self.client_stub.post(
            '/mediaDeliveryToDrop/', data='mediaArtifact=ERICtestiso_CXP1234567&version=1.26.9&productSet=ENM&productSetRelease=1A&drop=latest&product=ENM&signum=ewilwre&email=william.wren@ericsson.com', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, data_expected)

    def test_mediaArtifact_delivery_to_given_drop_success(self):
        data_expected = "Drop 1.1"
        response = self.client_stub.post(
            '/mediaDeliveryToDrop/', data='mediaArtifact=ERICtestiso_CXP1234567&version=1.26.10&productSet=ENM&productSetRelease=1A&drop=1.1&product=ENM&signum=ewilwre&email=william.wren@ericsson.com', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, data_expected)

    def test_setting_externally_released_media_artifact_version_success(self):
        data_expected = "Successfully updated, externally released Media Artifact"
        response = self.client_stub.post('/api/mediaArtifactVersionExternallyReleased/product/ENM/drop/1.1/',
                                         data='mediaArtifactVersion=1.26.9&mediaArtifactName=ERICtestiso_CXP1234567', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, data_expected)
        # IP
        response = self.client_stub.post('/api/mediaArtifactVersionExternallyReleased/product/ENM/drop/1.1/',
                                         data='mediaArtifactVersion=1.26.10&mediaArtifactName=ERICtestiso_CXP1234567', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, data_expected)

    def test_setting_externally_released_media_artifact_version_failure(self):
        response = self.client_stub.post('/api/mediaArtifactVersionExternallyReleased/product/ENM/drop/1.1.33/',
                                         data='mediaArtifactVersion=1.26.9&mediaArtifactName=ERICtestiso_CXP1234567', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 404)

    def test_getting_externally_released_media_artifact_versions_success(self):
        data_expected = "1.26.11"
        response = self.client_stub.get(
            '/api/mediaArtifactVersionExternallyReleased/product/ENM/drop/1.1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, data_expected)

    def test_getting_externally_released_media_artifact_versions_failure(self):
        response = self.client_stub.get(
            '/api/mediaArtifactVersionExternallyReleased/product/ENM/drop/1.1.111/')
        self.assertEqual(response.status_code, 404)

    def test_getting_productset_drop_data_success(self):
        response = self.client_stub.get(
            '/api/getProductSetDropData/productSet/ENM/drop/1.1/')
        self.assertEqual(response.status_code, 200)

    def test_getting_productset_drop_data_failure(self):
        response = self.client_stub.get(
            '/api/getProductSetDropData/productSet/ENM/drop/1.X/')
        self.assertEqual(response.status_code, 404)

    def test_getting_media_artifact_data_success(self):
        response = self.client_stub.get(
            '/api/getMediaArtifactVersionData/mediaArtifact/ERICtestiso_CXP1234567/version/1.26.9/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1")
        self.assertContains(response, "test")

    def test_getting_media_artifact_data_failure(self):
        response = self.client_stub.get(
            '/api/getMediaArtifactVersionData/mediaArtifact/ERICtestiso/version/1.26.10/')
        self.assertEqual(response.status_code, 404)

    def test_getting_latest_drop_name_success(self):
        response = self.client_stub.get('/api/product/ENM/latestdrop/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1")

    def test_getting_latest_drop_name_wrong_productname_failure(self):
        data_expected = '{"error": "Issue getting Drop Name: Drop matching query does not exist."}'
        response = self.client_stub.get('/api/product/ten/latestdrop/')
        self.assertEqual(response.status_code, 404)

    def test_getting_latest_correctional_drop_name_success(self):
        response = self.client_stub.get(
            '/api/product/ENM/latestdrop/?correctionalDrop=True')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1.1.1")

    def test_getting_includedinprioritytestsuite_success(self):
        response = self.client_stub.get(
            '/api/product/ENM/testwareartifacts/ERICTAFtestpackage_CXP7654322/includedinprioritytestsuite/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RFA250")
        self.assertContains(response, "true")

    def test_get_includedinprioritytestsuite_failure(self):
        response = self.client_stub.get(
            '/api/product/ENM/testwareartifacts/ERICTAFtestpackage_CXP/includedinprioritytestsuite/')
        self.assertEqual(response.status_code, 404)

    def test_get_includedinprioritytestsuite_false_success(self):
        response = self.client_stub.get(
            '/api/product/ENM/testwareartifacts/ERICtestpackage1_CXP7654321/includedinprioritytestsuite/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "false")

    def test_post_and_get_includedinprioritytestsuite_success(self):
        responsePost = self.client_stub.post('/api/product/ENM/testwareartifacts/ERICTAFtestpackage_CXP7654322:ERICTWtestpackage_CXP7654326/includedinprioritytestsuite/',
                                             data='testwareType=RNL', content_type="application/x-www-form-urlencoded")
        self.assertEqual(responsePost.status_code, 200)
        self.assertContains(responsePost, "success")
        responseGet = self.client_stub.get(
            '/api/product/ENM/testwareartifacts/ERICTAFtestpackage_CXP7654322/includedinprioritytestsuite/')
        self.assertEqual(responseGet.status_code, 200)
        self.assertContains(responseGet, "true")
        self.assertContains(responseGet, "RFA250")
        self.assertContains(responseGet, "RNL")
        responseGet = self.client_stub.get(
            '/api/product/ENM/testwareartifacts/ERICTWtestpackage_CXP7654326/includedinprioritytestsuite/')
        self.assertEqual(responseGet.status_code, 200)
        self.assertContains(responseGet, "true")
        self.assertContains(responseGet, "RNL")

    def test_post_includedinprioritytestsuite_failure(self):
        response = self.client_stub.post('/api/product/ENM/testwareartifacts/ERICTAFtestpackage_CXP7654322:ERICTW_CXP/includedinprioritytestsuite/',
                                         data='testwareType=RNL', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 404)

    def test_post_includedinprioritytestsuite_type_failure(self):
        response = self.client_stub.post('/api/product/ENM/testwareartifacts/ERICTAFtestpackage_CXP7654322:ERICTWtestpackage_CXP7654326/includedinprioritytestsuite/',
                                         data='testwareType=NO', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 404)

    def test_get_productSet_active_drops_success(self):
        response = self.client_stub.get('/api/productSet/ENM/activeDrops/')
        self.assertEqual(response.status_code, 200)

    def test_get_productSet_active_drops_failure(self):
        response = self.client_stub.get('/api/productSet/GO/activeDrops/')
        self.assertEqual(response.status_code, 404)

    def test_get_productSet_drop_deploy_mappings_success(self):
        response = self.client_stub.get(
            '/api/productSet/ENM/drop/1.1/mappings/')
        self.assertEqual(response.status_code, 200)

    def test_get_productSet_drop_deploy_mappings_productSet_failure(self):
        response = self.client_stub.get(
            '/api/productSet/GO/drop/1.1/mappings/')
        self.assertEqual(response.status_code, 404)

    def test_get_productSet_drop_deploy_mappings_drop_failure(self):
        response = self.client_stub.get(
            '/api/productSet/ENM/drop/9999.2/mappings/')
        self.assertEqual(response.status_code, 404)

    def test_obsoleteGroupDeliveries_forceOption_off_success(self):
        self.user.groups.add(self.group1)
        self.user.groups.add(self.group2)
        self.user.save()
        self.client_stub.login(username='testuser', password='12345')
        response = self.client_stub.post('/api/forceOption/False/product/ENM/drop/' + str(
            self.deliveryGroup3.drop.name) + '/obsoleteGroup/' + str(self.deliveryGroup3.id) + '/?user=testuser')
        self.assertEqual(response.status_code, 200)

    def test_obsoleteGroupDeliveries_forceOption_off_Failure(self):
        self.user.groups.add(self.group1)
        self.user.groups.add(self.group2)
        self.user.save()
        self.client_stub.login(username='testuser', password='12345')
        response = self.client_stub.post('/api/forceOption/False/product/ENM/drop/' + str(
            self.deliveryGroup2.drop.name) + '/obsoleteGroup/' + str(self.deliveryGroup2.id) + '/?user=testuser')
        self.assertEqual(response.status_code, 403)

    def test_obsoleteGroupDeliveries_forceOption_on_success(self):
        self.user.groups.add(self.group1)
        self.user.groups.add(self.group2)
        self.user.save()
        self.client_stub.login(username='testuser', password='12345')
        response = self.client_stub.post('/api/forceOption/True/product/ENM/drop/' + str(
            self.deliveryGroup2.drop.name) + '/obsoleteGroup/' + str(self.deliveryGroup2.id) + '/?user=testuser')
        self.assertEqual(response.status_code, 200)

    def test_obsoleteGroupDeliveries_rest_call_failure(self):
        response = self.client_stub.get('/api/forceOption/False/product/ENM/drop/' + str(
            self.deliveryGroup3.drop.name) + '/obsoleteGroup/' + str(self.deliveryGroup3.id) + '/?user=testuser')
        self.assertEqual(response.status_code, 405)

    def test_obsoleteGroupDeliveries_not_delivered_failure(self):
        self.user.groups.add(self.group1)
        self.user.groups.add(self.group2)
        self.user.save()
        self.client_stub.login(username='testuser', password='12345')
        response = self.client_stub.post('/api/forceOption/False/product/ENM/drop/' + str(
            self.deliveryGroup4.drop.name) + '/obsoleteGroup/' + str(self.deliveryGroup4.id) + '/?user=testuser')

        self.assertEqual(response.status_code, 403)

    def test_obsoleteGroupDeliveries_user_not_admin_failure(self):
        self.client_stub.login(username='testuser2', password='12345')
        response = self.client_stub.post('/api/forceOption/False/product/ENM/drop/' + str(
            self.deliveryGroup3.drop.name) + '/obsoleteGroup/' + str(self.deliveryGroup3.id) + '/?user=testuser2')
        self.assertEqual(response.status_code, 403)

    # Cloud Native Test
    # Cloud Native - Delivery Queue Test
    def test_cnDeliveryQueue_getCNImage_success(self):
        response = self.client_stub.get('/api/cloudNative/getCNImage/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_getIntegrationChart_success(self):
        productTypeName = "Integration Chart"
        response = self.client_stub.get(
            '/api/cloudNative/getCNProduct/' + productTypeName)
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_getTeam_success(self):
        response = self.client_stub.get('/api/cireports/component/ENM/Team/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_getServiceGroupInfoByDelieryGroupNumber_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/deliveryQueue/getServiceGroupInfo/' + str(self.cnDeliveryGroup1.id) + '/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_removeServiceGroup_success(self):
        sample_data = {
            'imageName': "enm-sg-testpackage-1",
            'gerritList': "gerritlink1"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editServiceGroup/' + str(
            self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_getIntegrationChartInfoByDelieryGroupNumber_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/deliveryQueue/getIntegrationChartInfo/' + str(self.cnDeliveryGroup1.id) + "/")
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_removeIntegrationChart_success(self):
        sample_data = {
            'integrationChartName': "eric-enm-monitoring-integration",
            'gerritList': "gerritlink3"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editIntegrationChart/' + str(
            self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_getJiraInfoByDeliveryGroupNumber_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/deliveryQueue/getJiraInfo/' + str(self.cnDeliveryGroup1.id) + '/')
        self.assertEqual(response.status_code, 200)

    # def test_cnDeliveryQueue_editJira_success(self):
    #     sample_data = {
    #         'data_beforeEdit': {
    #             'jiraList': [
    #                 "TORF-417818",
    #                 "TORF-417819"
    #             ]
    #         },
    #         'data_afterEdit': {
    #             'jiraList': [
    #                 "TORF-417818",
    #                 "ETTD-3401"
    #             ]
    #         }
    #     }
    #     self.client_stub.login(username='ciadmin', password='12345')
    #     response = self.client_stub.put('/api/cloudNative/deliveryQueue/editJira/' + str(
    #         self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
    #     self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_removeJira_success(self):
        sample_data = {
            'jiraNumber': 'TORF-417819'
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editJira/' + str(
            self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_getPipelineInfoByDeliveryGroupNumber_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/deliveryQueue/getPipelineInfo/' + str(self.cnDeliveryGroup1.id) + "/")
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_removePipeline_success(self):
        sample_data = {
            'pipelineName': "pipeline1",
            'gerritList': "gerritlink5"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editPipeline/' + str(
            self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_removeImpactedDeliveryGroup_success(self):
        sample_data = {
            'impactedDeliveryGroupNumber': self.deliveryGroup5.id,
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editImpactedDeliveryGroup/' + str(
            self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_updateMissingDependencies_success(self):
        sample_data = {
            "deliveryGroupNumber": self.deliveryGroup5.id,
            "missingDepValue": True,
            "missingDepReason": "missing dep found"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateMissingDependencies/' + str(
            self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_uncheckMissingDependencies_success(self):
        sample_data = {
            "deliveryGroupNumber": self.deliveryGroup5.id,
            "missingDepValue": False,
            "missingDepReason": ""
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateMissingDependencies/' + str(
            self.cnDeliveryGroup1.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    # def test_cnDeliveryQueue_deliverDeliveryGroup_success(self):
    #     sample_data = {
    #         'deliveryGroupNumber': self.cnDeliveryGroup1.id,
    #         'productSetVersion': "21.14.1",
    #     }
    #     self.client_stub.login(username='ciadmin', password='12345')
    #     response = self.client_stub.post(
    #         '/api/cloudNative/deliveryQueue/deliverCNDeliveryGroup/', sample_data)
    #     self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_obsoleteDeliveryGroup_success(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/obsoleteCNDeliveryGroup/' + str(self.cnDeliveryGroup2.id) + '/')
        self.assertEqual(response.status_code, 200)
    # ETTD-4030 : Introduced obseleting section for gerrit revert, requirement not finalised
    # def test_cnDeliveryQueue_obsoleteDeliveryGroup_success(self):
    #     self.client_stub.login(username='ciadmin', password='12345')
    #     response = self.client_stub.post('/api/cloudNative/deliveryQueue/obsoleteCNDeliveryGroup/'+ str(self.cnDeliveryGroup2.id) + '/')
    #     self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_restoreDeliveryGroup_success(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/restoreCNDeliveryGroup/' + str(self.cnDeliveryGroup3.id) + '/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_deleteDeliveryGroup_success(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/deleteCNDeliveryGroup/' + str(self.cnDeliveryGroup1.id) + '/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_deliverDeliveryGroup_permission_failure(self):
        sample_data = {
            'deliveryGroupNumber': self.deliveryGroup1.id,
            'productSetVersion': "21.13.2",
        }
        self.client_stub.login(username='ciuser', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/deliverCNDeliveryGroup/', sample_data, content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_cnDeliveryQueue_obsoleteDeliveryGroup_permission_failure(self):
        self.client_stub.login(username='ciuser', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/obsoleteCNDeliveryGroup/' + str(self.cnDeliveryGroup2.id) + '/')
        self.assertEqual(response.status_code, 401)

    def test_cnDeliveryQueue_restoreDeliveryGroup_permission_failure(self):
        self.client_stub.login(username='ciuser', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/restoreCNDeliveryGroup/' + str(self.cnDeliveryGroup3.id) + '/')
        self.assertEqual(response.status_code, 401)

    def test_cnDeliveryQueue_deleteDeliveryGroup_permission_failure(self):
        self.client_stub.login(username='ciuser', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/deleteCNDeliveryGroup/' + str(self.cnDeliveryGroup4.id) + '/')
        self.assertEqual(response.status_code, 401)

    def test_cnDeliveryQueue_deliverDeliveryGroup_wrongSection_failure(self):
        sample_data = {
            'deliveryGroupNumber': self.deliveryGroup3.id,
            'productSetVersion': "21.13.2",
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/deliverCNDeliveryGroup/', sample_data)
        self.assertEqual(response.status_code, 400)

    def test_cnDeliveryQueue_obsoleteDeliveryGroup_wrongSection_failure(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/obsoleteCNDeliveryGroup/' + str(self.cnDeliveryGroup1.id) + '/')
        self.assertEqual(response.status_code, 400)

    def test_cnDeliveryQueue_restoreDeliveryGroup_wrongSection_failure(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/restoreCNDeliveryGroup/' + str(self.cnDeliveryGroup7.id) + '/')
        self.assertEqual(response.status_code, 400)

    def test_cnDeliveryQueue_deleteDeliveryGroup_wrongSection_failure(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/deleteCNDeliveryGroup/' + str(self.cnDeliveryGroup2.id) + '/')
        self.assertEqual(response.status_code, 400)

    def test_cnDeliveryQueue_updateProductSetVersion_success(self):
        sample_data = {
            'deliveryGroupNumber': self.cnDeliveryGroup7.id,
            'productSetVersion': "21.14.1",
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateDeliveryGroupByCNProductSetVersion/',
                                        json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveryQueue_updateProductSetVersion_undelivered_failure(self):
        sample_data = {
            'deliveryGroupNumber': self.deliveryGroup3.id,
            'productSetVersion': "21.13.2",
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateDeliveryGroupByCNProductSetVersion/',
                                        json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_cnDeliveryQueue_updateProductSetVersion_permission_failure(self):
        sample_data = {
            'deliveryGroupNumber': self.deliveryGroup2.id,
            'productSetVersion': "21.13.2",
        }
        self.client_stub.login(username='ciuser', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateDeliveryGroupByCNProductSetVersion/',
                                        json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_cnDeliveryQueue_deliverDeliveryGroup_closedDrop_failure(self):
        sample_data = {
            'deliveryGroupNumber': self.cnDeliveryGroup6.id,
            'productSetVersion': "21.13.2",
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/deliverCNDeliveryGroup/', sample_data)
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_obsoleteDeliveryGroup_closedDrop_failure(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/obsoleteCNDeliveryGroup/' + str(self.cnDeliveryGroup6.id) + '/')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_restoreDeliveryGroup_closedDrop_failure(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/restoreCNDeliveryGroup/' + str(self.cnDeliveryGroup6.id) + '/')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_deleteDeliveryGroup_closedDrop_failure(self):
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/deleteCNDeliveryGroup/' + str(self.cnDeliveryGroup6.id) + '/')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_updateProductSetVersion_closedDrop_failure(self):
        sample_data = {
            'deliveryGroupNumber': self.deliveryGroup6.id,
            'productSetVersion': "21.13.2",
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateDeliveryGroupByCNProductSetVersion/',
                                        json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_createDeliveryGroup_closedDrop_failure(self):
        sample_data = {
            'cnImageList': [
                {'imageName': "enm-sg-testpackage-1", 'gerritList': [
                    "https://gerrit-gamma.gic.ericsson.se/10177395", "https://gerrit-gamma.gic.ericsson.se/10182799"]},
                {'imageName': "enm-sg-testpackage-2", 'gerritList': [
                    "https://gerrit-gamma.gic.ericsson.se/#/c/10130587/", "https://gerrit-gamma.gic.ericsson.se/#/c/10144859/"]}
            ],
            'integrationChartList': [
                {'integrationChartName': "eric-enm-monitoring-integration", 'gerritList': [
                    "https://gerrit-gamma.gic.ericsson.se/10177396", "https://gerrit-gamma.gic.ericsson.se/10182599"]},
                {'integrationChartName': "eric-enm-infra-integration", 'gerritList': [
                    "https://gerrit-gamma.gic.ericsson.se/#/c/10130588/", "https://gerrit-gamma.gic.ericsson.se/#/c/10144839/"]}
            ],
            'pipelineList': [
                {'pipelineName': "pipeline1", 'gerritList': [
                    "https://gerrit-gamma.gic.ericsson.se/#/c/10230588/", "https://gerrit-gamma.gic.ericsson.se/#/c/10544839/"]},
                {'pipelineName': "pipeline2", 'gerritList': [
                    "https://gerrit-gamma.gic.ericsson.se/#/c/11230588/", "https://gerrit-gamma.gic.ericsson.se/#/c/103344839/"]},
            ],
            'jiraTickets': ["ETTD-3401"],
            'dropName': "21.13",
            'teamName': "Privileged",
            'missingDep': "false",
            'missingDepReason': "",
            'impacted_delivery_group': [self.deliveryGroup5.id],
            'userName': self.user3.username,
            'productName': self.cnProductSet.product_set_name
        }
        response = self.client_stub.post(
            '/api/cloudNative/deliveryQueue/addCNDeliveryGroup/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_cnDeliveryQueue_removeServiceGroup_closedDrop_failure(self):
        sample_data = {
            'imageName': "enm-sg-testpackage-1",
            'gerritList': "gerritlink1"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editServiceGroup/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)


    def test_cnDeliveryQueue_removeIntegrationChart_closedDrop_failure(self):
        sample_data = {
            'integrationChartName': "eric-enm-monitoring-integration",
            'gerritList': "gerritlink3"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editIntegrationChart/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_editJira_closedDrop_failure(self):
        sample_data = {
            'data_beforeEdit': {
                'jiraList': [
                    "TORF-417818",
                    "TORF-417819"
                ]
            },
            'data_afterEdit': {
                'jiraList': [
                    "TORF-417818",
                    "ETTD-3401"
                ]
            }
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/editJira/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_removeJira_closedDrop_failure(self):
        sample_data = {
            'jiraNumber': 'TORF-417819'
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editJira/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_removePipeline_closedDrop_failure(self):
        sample_data = {
            'pipelineName': "pipeline1",
            'gerritList': "gerritlink5"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editPipeline/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_removeImpactedDeliveryGroup_closedDrop_failure(self):
        sample_data = {
            'impactedDeliveryGroupNumber': self.deliveryGroup5.id,
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.delete('/api/cloudNative/deliveryQueue/editImpactedDeliveryGroup/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_updateMissingDependencies_closedDrop_failure(self):
        sample_data = {
            "deliveryGroupNumber": self.deliveryGroup5.id,
            "missingDepValue": True,
            "missingDepReason": "missing dep found"
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateMissingDependencies/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveryQueue_uncheckMissingDependencies_closedDrop_failure(self):
        sample_data = {
            "deliveryGroupNumber": self.deliveryGroup5.id,
            "missingDepValue": False,
            "missingDepReason": ""
        }
        self.client_stub.login(username='ciadmin', password='12345')
        response = self.client_stub.put('/api/cloudNative/deliveryQueue/updateMissingDependencies/' + str(
            self.cnDeliveryGroup6.id) + '/', json.dumps(sample_data), content_type='application/json')
        self.assertEqual(response.status_code, 412)

    def test_cnDeliveyQueue_getCreatedDGs_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getCNDgCreatedDetails/drop/21.14/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveyQueue_getDeletedDGs_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getCNDgDeletedDetails/drop/21.14/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveyQueue_getDeliveredDGs_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getCNDgDeliveredDetails/drop/21.14/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveyQueue_getObsoletedDGs_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getCNDgObsoletedDetails/drop/21.14/')
        self.assertEqual(response.status_code, 200)

    def test_cnDeliveyQueue_getQueuedDGs_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getCNDgQueuedDetails/drop/21.14/')
        self.assertEqual(response.status_code, 200)

    # Cloud Native - cloud native flow Test
    def test_sendCnConfidenceLevel_passed_success(self):
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel1.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel1.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel2.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel2.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel3.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel3.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel4.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel4.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel6.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel6.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel7.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel7.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel8.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel8.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel9.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel9.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.get(
            '/api/cloudNative/getOverallWorkingBaseline/drop/21.13/')
        self.assertContains(response, "21.13.3")
        self.assertContains(response, "passed")

    def test_cnConfidenceLevel_in_progress_success(self):
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel1.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel1.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel2.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel2.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel3.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel3.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel4.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel4.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel6.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel6.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel7.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel7.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel8.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel8.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.get(
            '/api/cloudNative/getOverallWorkingBaseline/drop/21.13/')
        self.assertContains(response, "21.13.3")
        self.assertContains(response, "in_progress")

    def test_cnConfidenceLevel_failed_success(self):
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel1.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel1.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel2.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel2.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel3.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel3.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel4.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel4.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel6.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel6.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel7.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel7.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel8.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel8.confidence_level_name) + '/' + str(self.state2.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel9.confidence_level_name) + '/' + str(self.state3.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.post('/api/manageCNProductSet/' + str(
            self.cnProductSetversion3.product_set_version) + '/' + str(self.cnConfLevel9.confidence_level_name) + '/' + str(self.state1.state) + '/')
        self.assertContains(
            response, "SUCCESS")
        response = self.client_stub.get(
            '/api/cloudNative/getOverallWorkingBaseline/drop/21.13/')
        self.assertContains(response, "21.13.3")
        self.assertContains(response, "failed")

    def test_storeCNImageMetadata_success(self):
        metaData = [
            {
                "image_data": {
                    "cxc_number": "CXC 174 2014",
                    "image_version": "1.0.800-1",
                    "image_repo": "https://armdocker.rnd.ericsson.se/proj-enm",
                    "gerrit_repo_sha": "1237a33",
                    "image_name": "eric-enmsg-autoprovisioning-test",
                    "helm_chart_repo": "https://arm.epk.ericsson.se/artifactory/proj-enm-helm/eric-enmsg-autoprovisioning",
                    "helm_chart_name": "eric-enmsg-autoprovisioning-test",
                    "iso_version": "1.98.33",
                    "helm_chart_version": "1.0.800-1"
                }
            },
            {
                "rpm_data": [
                    {
                        "version": "1.1.1",
                        "rpm_name": "ERICtestpackage1_CXP7654321"
                    },
                    {
                        "version": "1.1.1",
                        "rpm_name": "ERICtestpackage2_CXP7654321"
                    },
                    {
                        "version": "1.1.1",
                        "rpm_name": "ERICtestpackage3_CXP7654321"
                    }
                ]
            },
            {
                "parent_data": {
                    "image_parent_repo": "armdocker.rnd.ericsson.se/proj-enm",
                    "image_parent_name": "eric-enm-rhel-jbossconfig",
                    "image_parent_version": "1.0.300-1"
                }
            }
        ]
        response = self.client_stub.post(
            '/api/storeCNMetadata/', json.dumps(metaData), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_storeCNIntegrationChartMetaData_success(self):
        metaData = [
            {
                "chart_data": {
                    "chart_name": "eric-enm-pre-deploy-integration",
                    "chart_version": "1.05.23",
                    "chart_repo": "https://arm.epk.ericsson.se/artifactory/proj-enm-dev-internal-helm/eric-enm-pre-deploy-integration",
                    "enm_iso_version": "1.96.107",
                    "product_set_version": "21.13.3",
                    "chart_size": "22406",
                    "gerrit_repo_sha": "91419082e534dee45c127460b73b3b59ab07db7f"
                }
            },
            {
                "dependent_charts": [
                    {
                        "name": "eric-enmsg-autoprovisioning-test",
                        "repository": "https://arm.epk.ericsson.se/artifactory/proj-enm-helm/",
                        "version": "1.0.800-1"
                    }
                ]
            }
        ]
        response = self.client_stub.post(
            '/api/storeCNMetadata/', json.dumps(metaData), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_storeCNIntegrationSyncMetaData_success(self):
        metaData = [
            {
                "sync_data": {
                    "enm_iso_version": "1.96.107",
                    "product_set_version": "21.13.3"
                }
            },
            {
                "integration_charts_data": [
                    {
                        "chart_name": "eric-enm-pre-deploy-integration",
                        "chart_version": "1.05.23",
                        "chart_repo": "https://arm.epk.ericsson.se/artifactory/proj-enm-dev-internal-helm/eric-enm-pre-deploy-integration"
                    }
                ]
            },
            {
                "integration_values_file": [
                    {
                        "values_file_name": "eric-enm-integration-production-values",
                        "values_file_version": "1.8.0-3",
                        "values_file_repo": "https://arm.epk.ericsson.se/artifactory/proj-enm-helm/eric-enm-integration-values/"
                    },
                    {
                        "values_file_name": "eric-enm-integration-extra-large-production-values",
                        "values_file_version": "1.8.0-2",
                        "values_file_repo": "https://arm.epk.ericsson.se/artifactory/proj-enm-helm/eric-enm-integration-extra-large-production-values/"
                    }
                ]
            }
        ]
        response = self.client_stub.post(
            '/api/storeCNMetadata/', json.dumps(metaData), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_storeCsarMetaData_success(self):
        metaData = [
            {
                "csar_details": {
                    "enm_installation_package_name": "enm-installation-package",
                    "enm_installation_package_version": "1.0.1",
                    "enm_installation_package_repo": "https://arm902-eiffel004.athtem.eei.ericsson.se:8443/nexus/content/repositories/releases/cENM/csar/enm-installation-package/1.0.159/",
                    "enm_installation_package_size": 15032388,
                    "gerrit_repo_sha": "7994437485db06868adb0febf7696e1a43f7ad69",
                    "enm_iso_version": "1.96.107",
                    "product_set_version": "21.13.3"
                }
            },
            {
                "list_charts_data": [
                    {
                        "chart_name": "eric-enm-pre-deploy-integration",
                        "chart_version": "1.05.23",
                        "chart_repo": "https://arm.epk.ericsson.se/artifactory/proj-enm-dev-internal-helm/eric-enm-pre-deploy-integration"
                    }
                ]
            },
            {
                "integration_values_file": []
            },
            {
                "dependent_docker_images": []
            }
        ]
        response = self.client_stub.post(
            '/api/storeCNMetadata/', json.dumps(metaData), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_storeDeploymentUtilitiesData_success(self):
        depUtilsData = {"deployUtil_1": "1.2.3", "deployUtil_2": "1.6.4",
                        "deployUtil_3": "1.35.4", "deployUtil_4": "1.863.4"}
        response = self.client_stub.post(
            '/api/cloudNative/postDeploymentUtilities/21.13.3/', json.dumps(depUtilsData), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_storeDeploymentUtilityDetailData_success(self):
        metaData = [
            {
                "deployment_utility_detail": {
                    "name": "cenm-deployment-utility",
                    "version": "1.05.23",
                    "repo": "https://arm.epk.ericsson.se/artifactory/proj-enm-dev-internal-helm/cenm-deployment-utility/",
                    "product_set_version": "21.13.3",
                    "size": "22406",
                    "gerrit_repo_sha": "91419082e534dee45c127460b73b3b59ab07db7f"
                }
            }
        ]
        response = self.client_stub.post(
            '/api/storeCNMetadata/', json.dumps(metaData), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_getCenmProductSetContent_success(self):
        response = self.client_stub.get(
            '/api/cloudnative/getCloudNativeProductSetContent/21.13/21.13.3/')
        self.assertEqual(response.status_code, 200)

    def test_getCenmProductSetVersion_by_enmProductSetVersion_success(self):
        data_expected = "21.13.3"
        response = self.client_stub.get(
            '/api/cloudNative/getLinkedCNProductSetVersion/21.13.3/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, data_expected)

    def test_getEnmProductSetVersion_by_cENMProductSetVersion_success(self):
        data_expected = "21.13.3"
        response = self.client_stub.get(
            '/api/cloudNative/getLinkedENMProductSetVersion/21.13.3/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, data_expected)

    def test_getCenmProductSetVersion_for_greenConfidenceLevels_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getConfidenceLevelVersion/')
        self.assertEqual(response.status_code, 200)

    def test_getLatestGreenCenmProductSet_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getGreenProductSetVersion/21.13/')
        self.assertEqual(response.status_code, 200)

    def test_getOverallWokringBaseline_success(self):
        response = self.client_stub.get(
            '/api/cloudNative/getOverallWorkingBaseline/drop/21.13/')
        self.assertEqual(response.status_code, 200)

    def test_updateCNProductSetVersionActiveness_success(self):
        response = self.client_stub.post(
            '/api/cloudNative/updateCNProductSetVersionActiveness/user/ciadmin/productSetVersion/21.13.3/isActive/False/')
        self.assertEqual(response.status_code, 200)
        response = self.client_stub.post(
            '/api/cloudNative/updateCNProductSetVersionActiveness/user/ciadmin/productSetVersion/21.13.3/isActive/True/')
        self.assertEqual(response.status_code, 200)

    def test_overwriteOverallConfidenceLevel_success(self):
        response = self.client_stub.post(
            '/api/cloudNative/updateCNProductSetVersionActiveness/user/ciadmin/productSetVersion/21.13.3/isActive/False/')
        self.assertEqual(response.status_code, 200)

        response = self.client_stub.post(
            '/api/cloudNative/updateCNProductSetVersionActiveness/user/ciadmin/productSetVersion/21.13.3/isActive/True/')
        self.assertEqual(response.status_code, 200)

    def test_overwriteOverallConfidenceLevel_failed(self):
        response = self.client_stub.post(
            '/api/cloudNative/updateCNProductSetVersionActiveness/user/ciuser/productSetVersion/21.13.3/isActive/False/')
        self.assertEqual(response.status_code, 403)

        response = self.client_stub.post(
            '/api/cloudNative/updateCNProductSetVersionActiveness/user/ciuser/productSetVersion/21.13.3/isActive/True/')
        self.assertEqual(response.status_code, 403)

    def test_publishVerfiedCsar_success(self):
        response = self.client_stub.post(
            '/api/cloudNative/publishVerifiedCNContent/21.13.3/enm-installation-package/1.17.0-27/')
        self.assertEqual(response.status_code, 200)

    def test_publishVerfiedIntegrationChart_success(self):
        response = self.client_stub.post(
            '/api/cloudNative/publishVerifiedCNContent/21.13.3/eric-enm-pre-deploy-integration/1.17.0-22/')
        self.assertEqual(response.status_code, 200)

    def test_unpublishVerfiedCsar_success(self):
        response = self.client_stub.post(
            '/api/cloudNative/unpublishVerifiedCNContent/21.13.3/enm-installation-package/1.17.0-27/')
        self.assertEqual(response.status_code, 200)

    def test_unpublishVerfiedIntegrationChart_success(self):
        response = self.client_stub.post(
            '/api/cloudNative/unpublishVerifiedCNContent/21.13.3/eric-enm-pre-deploy-integration/1.17.0-22/')
        self.assertEqual(response.status_code, 200)
