from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Obsoleting of Package Revision from a Drop"
    option_list = BaseCommand.option_list  + (
            make_option('--product',
                dest='product',
                help='product of the package to Obsolete'),
            make_option('--package',
                dest='package',
                help='name of the package to Obsolete'),
            make_option('--platform',
                dest='platform',
                help='platform of the package to Obsolete'),
            make_option('--ver',
                dest='ver',
                help='version of the package to Obsolete'),
            make_option('--type',
                dest='type',
                help='type of the package to Obsolete'),
            make_option('--mediaCategory',
                dest='category',
                help='category type of the package to Obsolete'),
            make_option('--drop',
                dest='drop',
                help='drop of the package to Obsolete'),
            make_option('--signum',
                dest='signum',
                help='signum of the user performing the Obsolete'),
            make_option('--reason',
                dest='reason',
                help='reason for the Obsolete')
            )

    def handle(self, *args, **options):

        if options['product'] is None:
            raise CommandError("You need to specify the product")
        if options['package'] is None:
            raise CommandError("You need to provide a name for the package, in the form \"ERICxyz\"")
        if options['platform'] is None:
            raise CommandError("You need to specify the platform of the package")
        if options['ver'] is None:
            raise CommandError("You need to specify the version of the package to obsolete")
        if options['type'] is None:
            raise CommandError("You need to specify the type of the package to obsolete")
        if options['drop'] is None:
            raise CommandError("You need to specify the drop")
        if options['signum'] is None:
            raise CommandError("You need to specify the user's signum")
        if options['reason'] is None:
            raise CommandError("You need to specify the user's reason for obsoleting the RPM")
        category = cireports.utils.mediaCategoryCheck(options['category'])
        if "Error" in str(category):
            raise CommandError(category)
        try:
            pkgRev = PackageRevision.objects.get(package__name=str(options['package']), version=str(options['ver']), m2type=str(options['type']), category=category)
            drop = Drop.objects.get(name=str(options['drop']), release__product__name=str(options['product']))
            dpm = DropPackageMapping.objects.get(package_revision=pkgRev, drop=drop, released=1)
            cireports.utils.obsolete(dpm.id, str(pkgRev.package.name), str(pkgRev.platform), str(options['signum']), str(options['reason']), str(drop.name))
        except Exception as e:
            raise CommandError("Does Not Exist in Database - " + str(e))

