from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create a package"
    option_list = BaseCommand.option_list  + (
            make_option('--name',
                dest='package',
                help='name of the package to create'),
            make_option('--repo',
                dest='repo',
                help=''),
            make_option('--group',
                dest='group',
                help=''),
            make_option('--ver',
                dest='ver',
                help=''),
            make_option('--category',
                dest='category',
                help=''),
            make_option('--packaging',
                dest='packaging',
                help=''),
            make_option('--autoDrop',
                dest='autoDrop',
                help=''),
            make_option('--justPackage',
                dest='justPackage',
                help=''),
            )

    def handle(self, *args, **options):
        if options['package'] is None:
            raise CommandError("You need to provide a name for the package, in the form \"ERICxyz\"")
        if options['justPackage'] is None:
            if options['repo'] is None:
                raise CommandError("missing repo")
            if options['group'] is None:
                raise CommandError("missing group")
            if options['ver'] is None:
                raise CommandError("missing ver")
            if options['category'] is None:
                raise CommandError("missing category")
            if options['packaging'] is None:
                raise CommandError("missing packaging")
            if options['autoDrop'] is None:
                raise CommandError("missing autoDrop")
            

            try:
                if (PackageRevision.objects.filter(groupId=options['group'],artifactId=options['package'],version=options['ver'],autodrop=options['autoDrop'],m2type=options['packaging'],arm_repo=options['repo'],category__name=options['category']).exists()):
                    ret = "OK"
                else:
                    ret = "ERROR"            
            except:
                ret = "ERROR"

        else:
            try:
                if (Package.objects.filter(name=options['package']).exists()):
                    ret = "OK"
                else:
                    ret = "ERROR"
            except:
                ret = "ERROR"

        return ret
