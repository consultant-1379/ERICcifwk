from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
import cireports.models
import cireports.utils

from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--package',
                dest='package',
                help='package'),
            make_option('--ver',
                dest='ver',
                help='version'),
            make_option('--type',
                dest='type',
                help='The Package Type (e.g rpm,zip,tar,pkg)'),
            make_option('--platform',
                dest='platform',
                help='platform'),
            make_option('--phase',
                dest='phase',
                help='phase'),
            make_option('--state',
                dest='state',
                help='state'),
            make_option('--list',
                dest='list',
                help='list'),
            make_option('--group',
                dest='group',
                help='group'),
            make_option('--veLog',
                dest='veLog',
                help='veLog'),
            make_option('--team',
                dest='team',
                help='team'),
            make_option('--parentElement',
                dest='parentElement',
                help='parentElement'),
            )

    def handle(self, *args, **options):
        if options['package'] == None and options['list'] == None:
            raise CommandError("Option required")
        elif options['package'] != None:
            package=options['package']
        if options['ver'] == None and options['package'] == None and options['list'] == None:
            raise CommandError("Option required")
        elif options['ver'] != None:
           ver=options['ver']
        if options['type'] == None:
            type = "rpm"
        else:
            type = options['type']
        if options['phase'] == None:
            raise CommandError("Option required")
        else:
            phase=options['phase']
        if options['state'] == None:
            raise CommandError("Option required")
        else:
            state=options['state']
        if options['platform'] == None:
            platform = "None"
        else:
            platform = options['platform']
        if options['team'] == None:
            team = None
        else:
            team = options['team']
        if options['parentElement'] == None:
            parentElement = None
        else:
            parentElement = options['parentElement']

        group=options['group']
        veLog=options['veLog']
        if options['list'] != None:
            packageList=options['list'].split(',')
            for item in packageList:
                package,ver=item.split(':')
                cireports.utils.updateTestStatus(package,ver,type,phase,state,platform,veLog,team,parentElement)
        else:
            cireports.utils.updateTestStatus(package,ver,type,phase,state,platform,veLog,team,parentElement,group)
