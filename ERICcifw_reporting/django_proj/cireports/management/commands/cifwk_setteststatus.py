from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Set the specified package revision to the specified status for the specified test phase"
    option_list = BaseCommand.option_list  + (
            make_option('--package', action='store',
                dest='package',
                help='name of the package to set the status on'),
            make_option('--pkgver',
                dest='version',
                help='version of the package to set the status on'),
            make_option('--type',
                dest='type',
                help='The Package Type, multiple formats supported.. rpm, zip, pkg etc'),
            make_option('--phase',
                dest='phase',
                help='test phase to set the status on'),
            make_option('--status',
                dest='status',
                help='status to set (not_started|in_progress|failed|passed)'),
            )

    def handle(self, *args, **options):
        verparts = options['version'].split(".")
        if (len(verparts) < 3):
            raise CommandError('You must supply a version string of the form N.N.N or N.N.N.N, where N is a positive integer')
        if (len(verparts) < 4):
            verparts.append('0')
        if options['type'] == None:
            type = "rpm"
        else:
            type = options['type']

        try:
            pv = PackageRevision.objects.get(package__name=options['package'], major=int(verparts[0]), minor=int(verparts[1]), patch=int(verparts[2]), ec=int(verparts[3]), m2type=type)
            # TODO: sort out all this hard coding!
            if options['phase'] == 'compile':
                pv.compile = options['status']
            elif options['phase'] == 'unit_test':
                pv.unit_test = options['status']
            elif options['phase'] == 'integration_test':
                pv.integration_test = options['status']
            else:
                raise CommandError("Phase " + options['phase'] + " does not exist")
            pv.save()
            print options['package'] + " ver. " + options['version'] + " phase " + options['phase'] + " set to " + options['status']
        except PackageRevision.DoesNotExist:
            raise CommandError("PackageRevision " + pv + " ver " + ver + " does not exist")

