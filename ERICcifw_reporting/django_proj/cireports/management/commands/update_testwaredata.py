from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
config = CIConfig()
logger = logging.getLogger(__name__)


class Command(BaseCommand):

     def handle(self, *args, **options):
        packages = Package.objects.all()
        testwares = TestwareArtifact.objects.all()
        try:
            for testItem in testwares:
                logger.debug("Testware: " + str(testItem))
                pkgobj = None
                try:
                    if not Package.objects.filter(name=testItem.name).exists():
                       pkgObj = Package(name=testItem.name, package_number=testItem.artifact_number, description="testware", signum="axis", testware=True)
                       pkgObj.save()
                       logger.debug("New Package Saved: " + str(pkgObj))
                except Exception as e:
                     logger.error("Error in Saving Package:" + str(e))
                dropPkgMap = None
                try:
                    for package in packages:
                        if TestwarePackageMapping.objects.filter(testware_artifact=testItem, package=package).exists():
                            logger.debug("Package: " + str(package))
                            if DropPackageMapping.objects.filter(package_revision__package=package).exists():
                                dropPkgMap = DropPackageMapping.objects.filter(package_revision__package=package).order_by('-id')[0]
                                product = Product.objects.get(name=dropPkgMap.drop.release.product.name)
                                drop = Drop.objects.filter(release__product=product).order_by('-id')[0]
                                break
                except Exception as e:
                    logger.error("Error in getting autodrop: " + str(e))
                try:
                    if dropPkgMap != None:
                        logger.debug("autodrop: " + str(dropPkgMap.drop.release.product.name) + ":" + str(drop.name))
                        category = Categories.objects.get(name="testware")
                        testwareRevs = TestwareRevision.objects.filter(testware_artifact=testItem)
                        for testwareRev in testwareRevs:
                            if not PackageRevision.objects.filter(package__name=testwareRev.testware_artifact.name, version=testwareRev.version).exists():
                                pkgObj = Package.objects.get(name=testwareRev.testware_artifact.name)
                                pkgRevObj = PackageRevision(package=pkgObj, date_created=testwareRev.date_created, groupId=testwareRev.groupId, artifactId=testwareRev.artifactId, version=testwareRev.version, autodrop=str(product.name + ":" + drop.name), m2type="jar", arm_repo=str(dropPkgMap.package_revision.arm_repo), category=category)
                                pkgRevObj.save()
                                logger.debug("New Package Revision saved: " + str(pkgRevObj))
                except Exception as e:
                     logger.error("Error in Saving Package Revision:" + str(e))
                try:
                    if dropPkgMap != None:
                        pkg = Package.objects.get(name=testItem.name)
                        if not ProductPackageMapping.objects.filter(product=product, package=pkg).exists():
                            productPkgObj = ProductPackageMapping(product=product, package=pkg)
                            productPkgObj.save()
                            logger.debug("Mapped: " + str(product.name) + " to " + str(pkg))
                except Exception as e:
                    logger.error("Error in Saving Product to Package Mapping:" + str(e))
                try:
                    if dropPkgMap != None:
                        if product.name == "ENM":
                            if PackageRevision.objects.filter(package__name=testItem.name).exists():
                                pkgObj = Package.objects.get(name=testItem.name)
                                pkgRevObj = PackageRevision.objects.filter(package=pkgObj).order_by('-id')[0]
                                packageRevisonObj = PackageRevision.objects.filter(package=pkgObj)
                                for packageRevison in packageRevisonObj:
                                    if DropPackageMapping.objects.filter(package_revision=packageRevison, drop=drop).exists():
                                        dropPackageMappingObj = DropPackageMapping.objects.get(package_revision=packageRevison, drop=drop)
                                        if packageRevison == pkgRevObj:
                                            continue
                                        else:
                                            dropPackageMappingObj.released = False
                                            dropPackageMappingObj.save()
                                if not DropPackageMapping.objects.filter(package_revision=pkgRevObj, drop=drop).exists():
                                    dropPkgObj = DropPackageMapping(package_revision=pkgRevObj, drop=drop, released=True)
                                    dropPkgObj.save()
                                    logger.debug("New Delivery: " + str(dropPkgObj))
                except Exception as e:
                    logger.error("Error in Saving Drop Package Mapping: " + str(e)) 
            return 0 
        except Exception as e:
            logger.error("Error:" + str(e))
            return "Error"
