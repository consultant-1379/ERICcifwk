"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase, Client, TransactionTestCase
from cireports.models import *
from dmt.models import *
from datetime import datetime, timedelta
from django.contrib.auth.models import User, Permission, Group
from cireports.tests import BaseSetUpTest
import utils

class FakeTestData(object):
    @classmethod
    def create(cls):
        cls.categorySW = Categories.objects.create(name="sw")
        cls.categoryServ = Categories.objects.create(name="service")
        cls.categoryTest = Categories.objects.create(name="testware")
        cls.mediatypeISO = MediaArtifactType.objects.create(type="iso")
        cls.mediatypeTAR = MediaArtifactType.objects.create(type="tar.gz")
        cls.mediaCatProd = MediaArtifactCategory.objects.create(name="productware")
        cls.mediaCatTest = MediaArtifactCategory.objects.create(name="testware")
        cls.mediaDeployType = MediaArtifactDeployType.objects.create(type="not_required")
        cls.mediaDeployTypePlat = MediaArtifactDeployType.objects.create(type="it_platform")
        cls.mediaDeployTypeOS = MediaArtifactDeployType.objects.create(type="os")
        cls.mediaDeployTypePatch = MediaArtifactDeployType.objects.create(type="patches")

        group_name = "ENM_MainTrack_Guardians"
        group_name2 = "CI_EX_Admin"
        cls.group1 = Group(name=group_name)
        cls.group2 = Group(name=group_name2)
        cls.group1.save()
        cls.group2.save()

        cls.jiraTypeExclusion = JiraTypeExclusion.objects.create(jiraType="Support")
        cls.user = User.objects.create_user(username='testuser', password='12345')
        cls.user2 = User.objects.create_user(username='testuser2', password='12345')
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
        ########## Product Set Drop Setup
        cls.productRHELMedia = Product.objects.create(name="RHEL-Media")
        cls.mediaArtifactRHELMedia = MediaArtifact.objects.create(name="RHEL-Media_CXP15151515", number="CXP15151515", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypeOS)
        cls.releaseRHELMedia = Release.objects.create(name="rhelRelease", track="rhelTrack", product=cls.productRHELMedia, masterArtifact=cls.mediaArtifactRHELMedia, created=datetime.now())
        cls.dropRHELMedia = Drop.objects.create(name="1.1", release=cls.releaseRHELMedia, systemInfo="test", planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildRHELMedia = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="RHEL-Media_CXP15151515", mediaArtifact=cls.mediaArtifactRHELMedia, drop=cls.dropRHELMedia, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")

        cls.productRHELPatch = Product.objects.create(name="RHEL-OS-Patch-Set-ISO")
        cls.mediaArtifactRHELPatch = MediaArtifact.objects.create(name="RHEL_OS_Patch_Set_CXP9034997", number="CXP9034997", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypePatch)
        cls.releaseRHELPatch = Release.objects.create(name="rhelPatchRelease", track="rhelPatchTrack", product=cls.productRHELPatch, masterArtifact=cls.mediaArtifactRHELPatch, created=datetime.now())
        cls.dropRHELPatch = Drop.objects.create(name="1.1", release=cls.releaseRHELPatch, systemInfo="test", planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildRHELPatch = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="RHEL_OS_Patch_Set_CXP9034997", mediaArtifact=cls.mediaArtifactRHELPatch, drop=cls.dropRHELPatch, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")

        cls.productRHELPatch7 = Product.objects.create(name="RHEL-76-OS-Patch-Set-ISO")
        cls.mediaArtifactRHELPatch7 = MediaArtifact.objects.create(name="RHEL76_OS_Patch_Set_CXP9037739", number="CXP9037739", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypePatch)
        cls.releaseRHELPatch7 = Release.objects.create(name="rhelPatch76Release", track="rhelPatch76Track", product=cls.productRHELPatch7, masterArtifact=cls.mediaArtifactRHELPatch7, created=datetime.now())
        cls.dropRHELPatch7 = Drop.objects.create(name="1.1", release=cls.releaseRHELPatch7, systemInfo="test", planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildRHELPatch7 = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="RHEL76_OS_Patch_Set_CXP9037739", mediaArtifact=cls.mediaArtifactRHELPatch7, drop=cls.dropRHELPatch7, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")

        cls.productLitp = Product.objects.create(name="LITP")
        cls.mediaArtifactLitp = MediaArtifact.objects.create(name="ERIClitp_CXP9024296", number="CXP9024296", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployTypeOS)
        cls.releaseLitp = Release.objects.create(name="litpRelease", track="litpTrack", product=cls.productLitp, masterArtifact=cls.mediaArtifactLitp, created=datetime.now())
        cls.dropLitp = Drop.objects.create(name="1.1", release=cls.releaseLitp, systemInfo="test", planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.isoBuildLitp = ISObuild.objects.create(version="1.1.1", groupId="com.ericsson.se", artifactId="ERIClitp_CXP9024296", mediaArtifact=cls.mediaArtifactLitp, drop=cls.dropLitp, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")


        ######### Main Tests Setup
        cls.product = Product.objects.create(name="ENM")
        cls.mediaArtifact = MediaArtifact.objects.create(name="ERICtestiso_CXP1234567", number="CXP1234567", description="test", mediaType="iso", category=cls.mediaCatProd, deployType=cls.mediaDeployType)
        cls.mediaArtifactTestware = MediaArtifact.objects.create(name="ERICtestwareiso_CXP7654321", number="CXP7654321", description="test", mediaType="iso", testware=True, category=cls.mediaCatTest, deployType=cls.mediaDeployType)
        cls.release = Release.objects.create(name="enmRelease", track="enmTrack", product=cls.product, masterArtifact=cls.mediaArtifact, created=datetime.now())
        cls.drop = Drop.objects.create(name="1.1", release=cls.release, systemInfo="test", planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate)
        cls.dropCorrectional = Drop.objects.create(name="1.1.1", release=cls.release, systemInfo="test", planned_release_date=freezeDate, actual_release_date=freezeDate, mediaFreezeDate=freezeDate, correctionalDrop=True)
        cls.state1 = States.objects.create(state="failed")
        cls.state2 = States.objects.create(state="passed")
        cls.state3 = States.objects.create(state="in_progress")


        cls.isoBuild1 = ISObuild.objects.create(version="1.26.9", groupId="com.ericsson.se", artifactId="ERICtestiso_CXP1234567", mediaArtifact=cls.mediaArtifact, drop=cls.drop, build_date=buildDate, arm_repo="test", current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}")
        cls.isoBuild2 = ISObuild.objects.create(version="1.26.10", groupId="com.ericsson.se", artifactId="ERICtestiso_CXP1234567", mediaArtifact=cls.mediaArtifact, drop=cls.drop, build_date=datetime.now(), arm_repo="test", overall_status=cls.state3)
        cls.isoBuild3 = ISObuild.objects.create(version="1.26.11", groupId="com.ericsson.se", artifactId="ERICtestiso_CXP1234567", mediaArtifact=cls.mediaArtifact, drop=cls.drop, build_date=buildDate2, arm_repo="test", externally_released=True, externally_released_ip=True, externally_released_rstate="R1AG/0")

        cls.isoBuildTestware = ISObuild.objects.create(version="1.0.10", groupId="com.ericsson.se", artifactId="ERICtestwareiso_CXP7654321", mediaArtifact=cls.mediaArtifactTestware, drop=cls.drop, build_date=datetime.now(), arm_repo="test")

        cls.mediaMapping = ProductTestwareMediaMapping.objects.create(productIsoVersion=cls.isoBuild1, testwareIsoVersion=cls.isoBuildTestware)
        cls.mediaMapping2 = ProductTestwareMediaMapping.objects.create(productIsoVersion=cls.isoBuild2, testwareIsoVersion=cls.isoBuildTestware)
        cls.mediaMapping3 = ProductTestwareMediaMapping.objects.create(productIsoVersion=cls.isoBuild3, testwareIsoVersion=cls.isoBuildTestware)

        cls.productSet1 = ProductSet.objects.create(name="ENM")
        cls.productSetRelease1 = ProductSetRelease.objects.create(name="1A", number="AOM111111",release=cls.release,productSet=cls.productSet1,masterArtifact=cls.mediaArtifact,updateMasterStatus=1)
        cls.state1 = States.objects.create(state="failed")
        cls.state2 = States.objects.create(state="passed")
        cls.cdbType1 = CDBTypes.objects.create(name="TST",sort_order=5)
        cls.productSetVersion1 = ProductSetVersion.objects.create(version="1.1.1",status=cls.state1,current_status="{1: 'passed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}",productSetRelease=cls.productSetRelease1,drop=cls.drop)
        cls.productSetVersion2 = ProductSetVersion.objects.create(version="1.1.2",status=cls.state2,current_status="{1: 'failed#2016-10-22 05:42:49#2016-10-22 17:15:45#1#None'}",productSetRelease=cls.productSetRelease1,drop=cls.drop)
        cls.productDropToCDBTypeMap1 = ProductDropToCDBTypeMap.objects.create(product=cls.product, drop=cls.drop, type=cls.cdbType1, overallStatusFailure=True, enabled=1)
        cls.productSetVerToCDBTypeMap1 = ProductSetVerToCDBTypeMap.objects.create(productSetVersion=cls.productSetVersion1, productCDBType=cls.productDropToCDBTypeMap1, runningStatus=False, override=False)
        cls.productSetVerToCDBTypeMap2 = ProductSetVerToCDBTypeMap.objects.create(productSetVersion=cls.productSetVersion2, productCDBType=cls.productDropToCDBTypeMap1, runningStatus=False, override=True)
        cls.productSetVerContent1 = ProductSetVersionContent.objects.create(productSetVersion=cls.productSetVersion1, mediaArtifactVersion=cls.isoBuild1, status=cls.state2)
        cls.productSetVerContent2 = ProductSetVersionContent.objects.create(productSetVersion=cls.productSetVersion2, mediaArtifactVersion=cls.isoBuild2, status=cls.state2)

        #---------------Product Set Drop Media content----------------#
        cls.productSetDropMediaMapRHELMedia = DropMediaArtifactMapping.objects.create(mediaArtifactVersion=cls.isoBuildRHELMedia, released=True, drop=cls.drop, dateCreated=buildDate)
        cls.productSetDropMediaMapRHELPatch = DropMediaArtifactMapping.objects.create(mediaArtifactVersion=cls.isoBuildRHELPatch, released=True, drop=cls.drop, dateCreated=buildDate)
        cls.productSetDropMediaMapRHELPatch7 = DropMediaArtifactMapping.objects.create(mediaArtifactVersion=cls.isoBuildRHELPatch7, released=True, drop=cls.drop, dateCreated=buildDate)
        cls.productSetDropMediaMapLitp = DropMediaArtifactMapping.objects.create(mediaArtifactVersion=cls.isoBuildLitp, released=True, drop=cls.drop, dateCreated=buildDate)


        #-------------------creating Teams and RA'S-------#
        cls.teamLabel = Label.objects.create(name="Team")
        cls.parentLabel = Label.objects.create(name="RA")
        cls.parentElementComp = Component.objects.create(element="PlanningAndConfiguration", product=cls.product, label=cls.parentLabel, dateCreated=datetime.now(), deprecated=False)
        cls.parentElementComp1 = Component.objects.create(element="AssuranceAndOptimisation", product=cls.product, label=cls.parentLabel, dateCreated=datetime.now(), deprecated=True)
        cls.parentElementComp2 = Component.objects.create(element="InactiveTeams", product=cls.product, label=cls.parentLabel, dateCreated=datetime.now(), deprecated=False)
        cls.team2 = Component.objects.create(element="Privileged", product=cls.product, parent=cls.parentElementComp, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=False)
        cls.team3 = Component.objects.create(element="Privileged1", product=cls.product, parent=cls.parentElementComp, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=True)
        cls.team4 = Component.objects.create(element="Privileged2", product=cls.product, parent=cls.parentElementComp1, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=False)
        cls.team5 = Component.objects.create(element="Privileged3", product=cls.product, parent=cls.parentElementComp1, label=cls.teamLabel, dateCreated=datetime.now(),deprecated=True)
        cls.team6 = Component.objects.create(element="Privileged4", product=cls.product, parent=cls.parentElementComp2, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=True)
        cls.team7 = Component.objects.create(element="Privileged5", product=cls.product, parent=cls.parentElementComp2, label=cls.teamLabel, dateCreated=datetime.now(), deprecated=False)

        cls.deliveryGroup1 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated = 1)
        cls.deliveryGroup2 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated = 1)
        cls.deliveryGroup3 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(), createdDate=datetime.now(), deliveredDate=datetime.now(), autoCreated = 1)
        cls.deliveryGroup4 = DeliveryGroup.objects.create(drop=cls.drop, creator="edarbyr", component=cls.team2, modifiedDate=datetime.now(), createdDate=datetime.now(), deliveredDate=datetime.now(), obsoleted = True, autoCreated = 1)

        cls.subscriptions = DeliveryGroupSubscription.objects.create(user=cls.user, deliveryGroup=cls.deliveryGroup1)

        #---- Data for Delivery Group for KGB Check ----#
        cls.package1 = Package.objects.create(name="ERICtestpackage1_CXP7654321")
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
                                                         artifactId = "ERICtestpackage1_CXP7654321",
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         category=cls.categoryServ,
                                                         version="1.1.2")
        cls.pkg1PkgRev3 = PackageRevision.objects.create(package=cls.package1,
                                                         artifactId = "ERICtestpackage1_CXP7654321",
                                                         date_created=datetime.now(),
                                                         autodrop="latest.Maintrack",
                                                         last_update=datetime.now(),
                                                         kgb_test="passed",
                                                         category=cls.categoryServ,
                                                         version="1.1.3",m2type="rpm")
        cls.package2 = Package.objects.create(name="ERICtestpackage2_CXP7654323")
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
        cls.testware1 = Package.objects.create(name="ERICTAFtestpackage_CXP7654322", testware=True, includedInPriorityTestSuite=True)
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
        cls.testware2 = Package.objects.create(name="ERICTWtestpackage_CXP7654326", testware=True)
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


        cls.package3 = Package.objects.create(name="ERICtestpackage3_CXP7654324")
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
        cls.package4 = Package.objects.create(name="ERICtestpackage4_CXP7654325")
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
        cls.package5 = Package.objects.create(name="ERICtestpackage5_CXP6654325")
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
        cls.package6 = Package.objects.create(name="ERICenmsguiservice_CXP9031574",package_number="CXP9031574")
        cls.productPackageMap =  ProductPackageMapping.objects.create(product=cls.product,package=cls.package6)

        cls.delGroupMap1 = DeliverytoPackageRevMapping.objects.create(deliveryGroup=cls.deliveryGroup1, packageRevision=cls.pkg1PkgRev1,team="Privileged")
        cls.delGroupMap2 = DeliverytoPackageRevMapping.objects.create(deliveryGroup=cls.deliveryGroup2, packageRevision=cls.pkg2PkgRev2,team="Privileged")
        cls.teamComp = Component.objects.create(element="Ninjas", product=cls.product, parent=cls.parentElementComp, label=cls.teamLabel, dateCreated=datetime.now())
        cls.reasonfornokgb_one = ReasonsForNoKGBStatus.objects.create(reason="No Environment at time of KGB", active=True)
        cls.reasonfornokgb_two = ReasonsForNoKGBStatus.objects.create(reason="No Jenkins Job for KGB Test", active=True)
        cls.reasonfornokgb_three = ReasonsForNoKGBStatus.objects.create(reason="Did not have time to run, i was advised to skip", active=False)
        cls.reasonfornokgb_four = ReasonsForNoKGBStatus.objects.create(reason="Other", active=True)
        cls.dropContent =  DropPackageMapping.objects.create(drop=cls.drop, package_revision=cls.pkg3PkgRev1, released=True, date_created=datetime.now(), delivery_info="test", kgb_test="passed", testReport="http")
        cls.dropContent2 =  DropPackageMapping.objects.create(drop=cls.drop, package_revision=cls.pkg2PkgRev2, released=False, date_created=datetime.now(), delivery_info="test", kgb_test="passed")
        cls.isobuildmapping1 = ISObuildMapping.objects.create(iso=cls.isoBuild1, drop=cls.drop, package_revision=cls.pkg4PkgRev1)
        cls.isobuildmapping2 = ISObuildMapping.objects.create(iso=cls.isoBuild2, drop=cls.drop, package_revision=cls.pkg3PkgRev1)
        cls.isobuildmapping3 = ISObuildMapping.objects.create(iso=cls.isoBuild2, drop=cls.drop, package_revision=cls.pkg4PkgRev2)
        cls.isobuildmapping4 = ISObuildMapping.objects.create(iso=cls.isoBuild3, drop=cls.drop, package_revision=cls.pkg4PkgRev1)
        cls.isobuildmapping5 = ISObuildMapping.objects.create(iso=cls.isoBuild3, drop=cls.drop, package_revision=cls.pkg3PkgRev1)
        cls.isobuildmapping6 = ISObuildMapping.objects.create(iso=cls.isoBuild2, drop=cls.drop, package_revision=cls.pkg2PkgRev2)

        cls.isobuildmappingTestware = ISObuildMapping.objects.create(iso=cls.isoBuildTestware, drop=cls.drop, package_revision=cls.testwareRev1)
        cls.autoDeliverTeam = AutoDeliverTeam.objects.create(team=cls.team2)

        cls.vmServiceName = VmServiceName.objects.create(name = "fakeVM")
        cls.vmServicePackageMapping = VmServicePackageMapping.objects.create(service=cls.vmServiceName, package=cls.package1)

        cls.testwareType1 = TestwareType.objects.create(type="RFA250")
        cls.testwareType2 = TestwareType.objects.create(type="RNL")
        cls.testwareTypeMapping = TestwareTypeMapping.objects.create(testware_type=cls.testwareType1, testware_artifact=cls.testware1)
        cls.testwareArtifact = TestwareArtifact.objects.create(name="ERICTAFkgb_CXP9030739", artifact_number="CXP9030739", description="test", signum="admin")
        cls.testwareRevision = TestwareRevision.objects.create(testware_artifact=cls.testwareArtifact, date_created=datetime.now(), version="1.1.1", groupId="com.ericsson.oss", artifactId="ERICTAFkgb_CXP9030739")
        cls.testwarePackageMapping = TestwarePackageMapping.objects.create(testware_artifact=cls.testwareArtifact,  package=cls.package3)
        cls.testResult = TestResults.objects.create(testdate="2017-04-10T12:27:35",test_report_directory="http://oss-taf-logs.lmera.ericsson.se/82a8e095-39d6-4e4c-b743-da5102cc575f/")
        cls.testResultMapping = TestResultsToTestwareMap.objects.create(testware_revision=cls.testwareRevision, testware_artifact=cls.testwareArtifact, package_revision=cls.pkg3PkgRev2, package=cls.package3, testware_run=cls.testResult)

        cls.testwareArtifact2 = TestwareArtifact.objects.create(name="ERICTWkgb_CXP9030740", artifact_number="CXP9030740", description="test", signum="admin")
        cls.testwareRevision2 = TestwareRevision.objects.create(testware_artifact=cls.testwareArtifact2, date_created=datetime.now(), version="1.1.1", groupId="com.ericsson.oss", artifactId="ERICTAFkgb_CXP9030740")
        cls.testwarePackageMapping2 = TestwarePackageMapping.objects.create(testware_artifact=cls.testwareArtifact,  package=cls.package4)
        cls.testResult2 = TestResults.objects.create(testdate="2017-04-10T12:27:35",test_report_directory="http://oss-taf-logs.lmera.ericsson.se/82a8e095-39d6-4e4c-b743-da5102cc575f/")
        cls.testResultMapping2 = TestResultsToTestwareMap.objects.create(testware_revision=cls.testwareRevision2, testware_artifact=cls.testwareArtifact2, package_revision=cls.pkg4PkgRev2, package=cls.package4, testware_run=cls.testResult2)

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

class BaseSetUpTest_multithreading(TransactionTestCase, FakeTestData):
    @classmethod
    def setUpClass(cls):
        '''
        Generate some fake data.
        '''
	cls.create()

class RestTest_multithreading(BaseSetUpTest_multithreading):

    def setUp(self):
        self.client_stub = Client()

    def test_post_deliver_auto_created_groups(self):
        data_expected = '"SUCCESS: All groups delivered(1, 2, 3)"'
        response = self.client_stub.post('/api/deliverAutoCreated/ENM/1.1/', data='user=testuser', content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.content, data_expected)


class RestTest_multithreading_2(BaseSetUpTest_multithreading):

    def setUp(self):
        self.client_stub = Client()

    def test_auto_create_and_deliver_group_to_drop_success(self):
        data_expected = "Success - Delivery Group was Created and Delivered to the Drop"
        response = self.client_stub.post('/api/createDeliveryGroup/',data='{"creator": "testuser", "product":"ENM","artifacts": "ERICtestpackage1_CXP7654321::1.1.3", "jiraIssues": "CIP-14500","missingDependencies": "False", "team": "Privileged","validateOnly": "false"}', content_type="application/json")
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data[0].get("result"), data_expected)
