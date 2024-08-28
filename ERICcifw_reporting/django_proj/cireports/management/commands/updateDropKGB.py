from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
import cireports.utils
from ciconfig import CIConfig
config = CIConfig()

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--product',
                        dest='product',
                        help='The Product'),
            make_option('--drop',
                        dest='drop',
                        help='The Drop'),
            )

    def handle(self, *args, **options):
        '''
        '''
        if options['drop'] == None:
            raise CommandError("Drop required")
        else:
            drop=options['drop']

        if options['product'] == None:
            raise CommandError("Product required")
        else:
            product = options['product']

        try:
            product = Product.objects.get(name=product)
        except Exception as e:
            return "ERROR: Getting Product " + str(product) + ". \n" + str(e)

        try:
            drop = Drop.objects.get(name=drop, release__product=product)
        except Exception as e:
            return "ERROR: Getting Drop " + str(drop) + ". \n" + str(e)

        try:
            dropKgb = cireports.utils.getPackageBaseline(drop)
            if "ERROR:" in dropKgb:
                return status
            else:
                for kgb in dropKgb:
                    kgb.kgb_test = kgb.package_revision.kgb_test
                    kgb.testReport = cireports.utils.getPkgRevKgbReport(kgb.package_revision)
                    kgb.save(force_update=True)
                    logger.info(str(kgb.package_revision) +" - KGB: " +  str(kgb.kgb_test) + ", Test Report: " + str(kgb.testReport))
        except Exception as e:
            raise CommandError("Exception Thrown in updating Drop KGB Results: " +str(e))
