from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
from cireports.models import *

from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        testwareTypeObj = TestwareType.objects.get(type="RFA250")
        testwareArtifacts = TestwareArtifact.objects.filter(includedInPriorityTestSuite=True)

        for testwareArtifact in testwareArtifacts:
            if Package.objects.filter(name=testwareArtifact.name).exists():
                package = Package.objects.get(name=testwareArtifact.name)
                package.includedInPriorityTestSuite = True
                package.save()
                TestwareTypeMapping.objects.create(testware_artifact=package, testware_type=testwareTypeObj)
                logger.info(str(testwareArtifact.name))
