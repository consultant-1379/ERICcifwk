import os,socket
import logging
logger = logging.getLogger(__name__)
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import excellence.utils 

class Command(BaseCommand):
    '''
    '''
    help = "Print out a Summary of All Responses of Excellence Models complete to a CSV file"
    option_list = BaseCommand.option_list  + (
            make_option('--fileName',
                dest='fileName',
                help='FileName for Summary and Path if required',
            ),
            )

    def handle(self, *args, **options):
        if options['fileName'] == None:
            raise CommandError("Please enter --fileName option with Path, eg: /tmp/john")

        fileName = options['fileName']    
        
        try:
            response = excellence.utils.ExcellenceResultsSummary(fileName)
            logger.info("Successfully returned Excellence Model Summary")
            return response
        except Exception as e:
            logger.error("Issue returning the Excellence Model Summary. Error: " +str(e))
