from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
from cireports.utils import getPackageBaseline, getArtifactSize
from ciconfig import CIConfig
from django.db import transaction
config = CIConfig()

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--drop',
                        dest='drop',
                        help='The Drop'),
            )

    def handle(self, *args, **options):
        '''
        '''
        if options['drop'] == None:
            raise CommandError("Drop required")
        else:
            dropName=options['drop']

        try:
            drop = Drop.objects.get(name=dropName, release__product__name="ENM")
        except Exception as e:
            return "ERROR: Getting Product " + str("ENM") + ". \n" + str(e)

        dropMaps = getPackageBaseline(drop)
        requiredFields = ("package_revision__id")
        packRevIds = dropMaps.filter(package_revision__size=0).only(requiredFields).values_list(requiredFields, flat=True)
        packRevs = PackageRevision.objects.filter(id__in=packRevIds).only("size","artifactId","version","groupId","m2type","arm_repo")
        try:
            with transaction.atomic():
                for packRev in packRevs:
                    size, responseCode = getArtifactSize(packRev.artifactId, packRev.version, packRev.groupId, packRev.m2type, packRev.arm_repo)
                    if responseCode != 200:
                        raise Exception("Failed to get artifact size from nexus: " + "Package: " + packRev.artifactId + " Version: " + packRev.version)
                    packRev.size=size
                    packRev.save()
        except Exception as e:
            print "ERROR: Unable to save size to Database: "+str(e)
