from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud
import time
import os
import logging
import sys
config = CIConfig()
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
            make_option('--remote',
                dest='remote',
                help='IP address of remote server'),
            )

    def handle(self, *args, **options):
        if options['appname'] == None:
            options['appname']=config.get("CIFWK_TEST_ENVIRONMENT", "appName")
        if options['tplname'] == None:
            options['tplname']=config.get("CIFWK_TEST_ENVIRONMENT", "templateName")
        if options['remote'] == None:
            options['remote']=config.get("CIFWK_TEST_ENVIRONMENT", "remote")
        print "running" +str(options['tplname']) +str(options['appname'])
        command = "/proj/lciadm100/cifwk/latest/bin/vapp_tunnel -t "+str(options['tplname'])+" -a "+str(options['appname'])+ " -f deploy"  
        result = os.system(command)
        if result  == 0:
            logger.info("Successfully deployed app template")
        else:
            raise CommandError("Could not instantiate " + options['tplname'] + " as " + options['appname'])


