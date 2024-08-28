from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
config = CIConfig()
logger = logging.getLogger(__name__)


class Command(BaseCommand):

     def handle(self, *args, **options):
        testwarePackageRevisionInDrops = DropPackageMapping.objects.select_related('package_revision__package').filter(package_revision__package__testware=1).delete()
