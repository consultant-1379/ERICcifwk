from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)
from dmt.serverUtilisation import serverUtilisationMain

class Command(BaseCommand):
    help = "Used to check the server utilisation for the deployments defined on the DE Axis Portal"
    option_list = BaseCommand.option_list  + (
            make_option('--testGroup',
                dest='testGroup',
                help='Optional Parameter: Can be used to specify a testgroup to check the server utilisation default will be all deployments'),
            )
    def handle(self, *args, **options):

        if options['testGroup'] == None:
            testGroup = None
        else:
            testGroup = options['testGroup']

        serverUtilisationMain(testGroup)
