

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import json
import sys
import urllib2
from fem.utils import getBuildStatus

class Command(BaseCommand):
    help = "Reports the status of a jenkins job, if job is queued the script will wait until the job \nhas moved out of the queue or the timeout entered has expired. If the timeout expires the job \nwill be removed from the queue"
    option_list = BaseCommand.option_list + (
        make_option('--jenkinsHost',
            dest='jenkinsHost',
            help='The Hostname of the target Jenkins'),
        make_option('--jobName',
            dest='jobName',
            help='The name of the job whose build status is wanted'),
        make_option('--buildSelector',
            dest='buildSelector',
            help='Search term for build which is being searched for ie: lastBuild, firstBuild, lastSuccessfulBuild, lastUnsuccessfulBuild, lastCompletedBuild, lastFailedBuild, lastStableBuild'),
        make_option('--timeout',
            dest='timeout',
            help='If job is in queue, the method will wait until the end of this timeout before removing the job from the queue')
        )


    def handle(self, *args, **options):
        '''
        '''
        if options['jenkinsHost']==None:
            raise CommandError("Hostname of Jenkins required")
        else:
            jenkinsHost=options['jenkinsHost']

        if options['jobName']==None:
            raise CommandError("Job Name required")
        else:
            jobName=options['jobName']

        if options['buildSelector']==None:
            raise CommandError("Build Selector required")
        else:
            buildSelector=options['buildSelector']

        if options['timeout']==None:
            raise CommandError("Timeout value required")
        else:
            timeout=int(options['timeout'])

        try:
            result = getBuildStatus(jenkinsHost, jobName, buildSelector, timeout)
            self.stdout.write(result)

        except Exception as e:
            raise CommandError(str(e))
