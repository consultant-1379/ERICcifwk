from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
import avs.avs_utils

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "AVS: Command line validation of mind map"
    option_list = BaseCommand.option_list  + (
            make_option('--file',
                dest='file',
                help='The path to the file to be validated'),
            )

    def handle(self, *args, **options):
        logger.info("AVS: Validation starting")
        if options['file']:
            try:
                result = avs.avs_utils.validateAvs(options['file'])
                if result[0] ==0:
                    logger.info("AVS: Validation was successful")
                else:
                    logger.info("AVS: Validation failed - please check AVS log for more information")
            except:
                raise CommandError("AVS: Supplied file does not exist")
        else:    
            logger.info("AVS: No file option supplied")
        
        logger.info("AVS: Validation finished")
