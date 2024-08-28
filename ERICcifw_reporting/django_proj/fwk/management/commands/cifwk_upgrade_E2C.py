from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

import fwk.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    args = "<version"
    help = "Upgrade the CI Framework"
    option_list = BaseCommand.option_list  + (
            make_option('--runTests',
                dest='runTests',
                help='When this option is included, Post upgrade tests will be run'),
            )

    def handle(self, *args, **options):
        if options['runTests'] is None:
            runTests = False
        else:
            runTests = options['runTests']
            if runTests.lower() == 'true':
                runTests = True
            elif runTests.lower() == 'false':
                runTests = False
            else:
                raise CommandError('if --runTests is included it must be equal to TRUE or FALSE')
        if (len(args) != 1):
            raise CommandError('You must supply a version to upgrade to')
        ver = args[0]
        try:
            retStr = fwk.utils.performUpgradeE2C(ver, runTests, True)
            #print "Upgrade: " + retStr
        except Exception as e:
            raise CommandError("Error upgrading to " + ver + ": " + str(e))