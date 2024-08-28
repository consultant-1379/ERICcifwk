from optparse import make_option
from django.core.management.base import BaseCommand

from cireports.models import *
from django.core.cache import cache

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Update the Infrastructure status of Package"
    option_list = BaseCommand.option_list  + (
            make_option('--package',
                dest='package',
                help='Name of the package (e.g. ERICversant_CXP9030229)'),
            make_option('--infra',
                dest='infra',
                help='Setting the status to either true or false for this package'),
            )

    def handle(self, *args, **options):

        if options['package'] is None:
            return "ERROR: You need to provide a name for the package"
        if options['infra'] is None:
            return "ERROR: You need to provide a option for the infra flag (true/false)"

        package = str(options['package'])
        infraOption = str(options['infra'])


        if infraOption.lower() == 'true':
            infra = True
        elif infraOption.lower() == 'false':
            infra = False
        else:
            return "ERROR: The option passed to the infra flag must be either true or false"

        try:
            packageObj = Package.objects.get(name=package)
        except Exception as e:
            return "ERROR: The Package Name provided does not exist in the database - " + str(e)

        if PackageRevision.objects.filter(package=packageObj).exists():
            try:
                pkgRevs = PackageRevision.objects.filter(package=packageObj)
                for rev in pkgRevs:
                    rev.infra = infra
                    rev.save()

                # Clear the cache
                cache._cache.flush_all()
                return "SUCCESS: Infrastructure status has been set to " + str(infra) + " for " + str(package)
            except Exception as e:
                return "ERROR: Unable to set Infrastructure status to " + str(infra) + " for " + str(package) + "  " + str(e)
        else:
            return "ERROR: No package revisions for the package name provided (" + str(package) + ") exist in the database"
