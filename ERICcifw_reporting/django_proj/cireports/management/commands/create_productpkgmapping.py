from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
config = CIConfig()
logger = logging.getLogger(__name__)


class Command(BaseCommand):

     def handle(self, *args, **options):
        products = Product.objects.all()
        try:
            for product in products:
                drpPkgMaps = DropPackageMapping.objects.filter(drop__release__product=product).exclude(package_revision__platform="sparc")
                for drpPkgMap in drpPkgMaps:
                    try:
                        if not ProductPackageMapping.objects.filter(product=product, package=drpPkgMap.package_revision.package).exists():
                            productPkgObj = ProductPackageMapping(product=product, package=drpPkgMap.package_revision.package)
                            productPkgObj.save()
                            logger.info("Mapped: " + str(product.name) + " to " + str(drpPkgMap.package_revision.package.name))
                    except:
                        logger.error("already Mapped: " + str(product.name) + " to " + str(drpPkgMap.package_revision.package.name))
            return "OK"
        except:
            return "Error"
