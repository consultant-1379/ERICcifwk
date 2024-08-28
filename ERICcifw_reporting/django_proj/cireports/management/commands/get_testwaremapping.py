from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Get Testware Mapping"
    option_list = BaseCommand.option_list  + (
            make_option('--testware',
                dest='testware',
                help='name of the testware'),
            make_option('--package',
                dest='package',
                help='name of the package'),
            )

    def handle(self, *args, **options):

        if options['testware'] is None:
            raise CommandError("You need to provide a name for the testware, in the form \"ERICTAFxyz or ERICTWxyz\"")
        if options['package'] is None:
            raise CommandError("You need to provide a name for the package, in the form \"ERICxyz\"")

        package = str(options['package'])
        testware = str(options['testware'])
        try:
            packageObj = Package.objects.get(name=package)
        except Exception as e:
            raise CommandError("Package Does Not Exist in Database - " + str(e))
        try:
            testwareObj = TestwareArtifact.objects.get(name=testware)
        except Exception as e:
            raise CommandError("Testware Does Not Exist in Database - " + str(e))
        try:
            mapping = TestwarePackageMapping.objects.get(testware_artifact=testwareObj,package=packageObj)
            return " There is Mapping between Package: " + str(packageObj.name) + " and Testware: " + str(testwareObj.name)
        except Exception as e:
                raise CommandError("Does Not Exists in Database - " + str(e))

