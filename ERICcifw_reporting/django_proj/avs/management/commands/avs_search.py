from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
import avs.avs_utils

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "AVS: Search AVS database and return details for a given Epic"
    option_list = BaseCommand.option_list  + (
            make_option('--epic',
                dest='epic',
                help='The Epic to search the database with'),
            )

    def handle(self, *args, **options):
        logger.info("AVS: Search starting")
        if options['epic']:
            #try:
            result = avs.avs_utils.searchAvs(options['epic'])
            print result
        else:    
            logger.info("AVS: No Epic supplied")
        
        logger.info("AVS: Search finished")
