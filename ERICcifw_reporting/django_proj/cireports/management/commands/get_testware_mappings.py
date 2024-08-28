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
            make_option('--list',
                dest='list',
                help='list'),
            )


    def handle(self, *args, **options):
        if options['package'] == None and options['list'] == None:
            raise CommandError("Option required")
        else:
            package=options['package']
        if options['ver'] == None and options['list'] == None:
            raise CommandError("Option required")
        
        if  options['list'] != None:
                packageList=options['list'].split(',')
                ret=cireports.utils.packageTestwareMapUnique(packageList)
        else:
            ver=options['ver']
            data = cireports.utils.packageTestwareMap(package,ver)
            ret=str(data)
        return ret 
