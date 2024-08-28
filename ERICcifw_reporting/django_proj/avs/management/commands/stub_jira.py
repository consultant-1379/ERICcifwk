from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
import avs.avs_utils

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "AVS: Command line validation of mind map"
    option_list = BaseCommand.option_list  + (
            make_option('--jiraId',
                dest='jiraId',
                help='The issue Id in JIRA'),
            )

    def handle(self, *args, **options):
        if options['jiraId']:
            result = avs.avs_utils.getJiraIdDetails(options['jiraId'])
            #{"jiraIssueId": jiraIssueId, "jiraIssueIdType":jiraIssueIdType, "jiraIssueIdTitle":jiraIssueIdTitle, "jiraIssueIdParent":jiraIssueIdParent}
            #result["jiraIssueId"]
            #logger.info(result)
            if 'errorMessage' in result.keys():
                print 'Error: ', result['errorMessage']
            else:
                userStoryId = result["jiraIssueId"]
                userStoryType = result["jiraIssueIdType"]
                userStoryTitle = result["jiraIssueIdTitle"]
                userStoryParentId = result["jiraIssueIdParent"]
                result = avs.avs_utils.getJiraIdDetails(userStoryParentId)
                userStoryPatenType = result["jiraIssueIdType"]
                userStoryParentTitle = result["jiraIssueIdTitle"]

                logger.info('UserStory Id: %s' % userStoryId)
                logger.info('Userstory Type: %s' % userStoryType) 
                logger.info('UserStory Title: %s' % userStoryTitle) 
                logger.info('UserStory Parent Id: %s' % userStoryParentId)
                logger.info('Userstory Parent Type: %s' % userStoryPatenType)
                logger.info('UserStory Parent Title:  %s' %userStoryParentTitle)
                print 'Done'
        else:    
            print "stub.py:  jiraId was not supplied does not exist"
          
