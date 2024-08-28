from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
import avs.avs_utils

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "AVS: Create the test class for a given user story"
    option_list = BaseCommand.option_list  + (
            make_option('--userstory',
                dest='userstory',
                help='The userstory to create the test skeleton for'),
            )

    def handle(self, *args, **options):
        logger.info("AVS: Skeleton creation starting")
        if options['userstory']:
            #try:
            avs.avs_utils.generateSkeletonClass(options['userstory'])        
        else:    
            logger.info("AVS: No UserStory supplied")
        
        logger.info("AVS: Skeleton creation finished")