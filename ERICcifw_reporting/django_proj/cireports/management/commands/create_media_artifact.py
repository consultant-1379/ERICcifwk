from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
config = CIConfig()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create the content for the ISO, will build up content for latest drop unless a drop is specified"
    option_list = BaseCommand.option_list  + (
            make_option('--name',
                dest='name',
                help=''),
            make_option('--number',
                dest='number',
                help=''),
            make_option('--desc',
                dest='desc',
                help=''),
            make_option('--type',
                dest='type',
                help=''),
            )

    def handle(self, *args, **options):
        name = options['name']
        number = options['number']
        desc = options['desc']
        type = options['type']
        try:
            deployTypeObj = MediaArtifactDeployType.objects.get(type="not_required")
            testware = False
            mediaCat = MediaArtifactCategory.objects.get(name="productware")
            if "testware" in str(type):
                mediaCat = MediaArtifactCategory.objects.get(name="testware")
                testware = True
            mediaArtifactObj = MediaArtifact(name=name,number=number,description=desc, testware=testware, category=mediaCat, deployType=deployTypeObj)
            mediaArtifactObj.save()
            return "OK"
        except Exception as e:
            return "Error: "+str(e)
