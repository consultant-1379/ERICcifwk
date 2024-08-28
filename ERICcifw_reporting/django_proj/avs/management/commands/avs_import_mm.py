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
        logger.info("AVS: Import starting")
        if options['file']:
            try:
                result = avs.avs_utils.importAvs(options['file'],'JJ')
                logger.debug('after call to avs.avs_utils.importAvs ')
                if result['errors'] ==0:
                    logger.info("AVS: Import was successful")
                else:
                    logger.info("AVS: Import failed - please check AVS logs for more information")
            #except:
            #    raise CommandError("AVS: Supplied file does not exist")
            except:
                raise CommandError("AVS: Import failed - please check AVS logs for more information")
        else:    
            logger.info("AVS: No file option supplied")
        
        logger.info("AVS: Import finished")
