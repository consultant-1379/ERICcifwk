from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create and start an instance of an app template"
    option_list = BaseCommand.option_list  + (
            make_option('--app',
                dest='appname',
                help='name of the app template to start an instance of'),
            make_option('--tpl',
                dest='tplname',
                help='name of the app you want to create'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        if options['appname'] == None:
            raise CommandError("To Run this option you need to specify the Vapp Name")
        if options['tplname'] == None:
            raise CommandError("To Run this option you need to specify the Template Name")

        if (dmt.cloud.startApp(driver, options['tplname'], options['appname']) == 0):
            logger.info("Successfully deployed app template")
        else:
            raise CommandError("Could not instantiate " + options['tplname'] + " as " + options['appname'])

