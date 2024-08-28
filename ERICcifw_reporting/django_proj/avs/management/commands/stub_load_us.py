from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import logging
import avs.avs_utils
import avs.avs_modules.MmParser  as AvsValidator

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "AVS: Stub to laod User Story / Epic data into databse"
    option_list = BaseCommand.option_list  + (
            make_option('--story',
                dest='storyName',
                help='The user story ID from Jira'),
            )

    def handle(self, *args, **options):
        if options['storyName']:
            myValidator = AvsValidator.AvsValidator()

                #Note: take these tow line out for release
                    #result = myValidator.importAvs(filename)
                        #return result

                            #Good from here for release
                                #result = myValidator.validateAvs(filename)

            result = myValidator.saveUserStoryAndEpic(options['storyName'])
            #avs.avs_utils.getJiraIdDetails(options['jiraId'])
            #{"jiraIssueId": jiraIssueId, "jiraIssueIdType":jiraIssueIdType, "jiraIssueIdTitle":jiraIssueIdTitle, "jiraIssueIdParent":jiraIssueIdParent}
            #result["jiraIssueId"]
            #logger.info(result)
            if 'errorMessage' in result.keys():
                print 'Error: ', result['errorMessage']
            else:
                print result
                print 'Done'
        else:    
            print "stub.py:  jiraId was not supplied does not exist"
          
