from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
from cireports.models import *
from distutils.version import LooseVersion

from cireports.utils import *

from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--package',
                dest='package',
                help='package'),
            make_option('--product',
                dest='product',
                help='product'),
            make_option('--drop',
                dest='drop',
                help='drop'),
            )

    def handle(self, *args, **options):
        if options['package'] == None:
            raise CommandError("Option required")
        else:
            package=options['package']
        if options['product'] == None:
           raise CommandError("Option required")
 
        if options['drop'] == None:
            drop = 'latest'
        else:
            drop=options['drop']
        if drop == "latest":
            drops = Drop.objects.filter(release__product__name=options['product'], correctionalDrop=False)
            dropList = list(drops)
            dropList.sort(key=lambda drop:LooseVersion(drop.name))
            dropList.reverse()
            dropId=dropList[0].id
            dropObj=Drop.objects.get(id=dropId)
        else:
            dropObj=Drop.objects.get(name=drop)
        packages = getPackageBaseline(dropObj)
        for item in packages:
            if item.package_revision.package.name == package:
                return item.package_revision.version
