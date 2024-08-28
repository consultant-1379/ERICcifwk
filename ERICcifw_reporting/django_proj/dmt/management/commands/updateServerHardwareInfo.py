from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from dmt.utils import *
from dmt.models import *
from cireports.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Add Netork info to DB about VAPP"
    option_list = BaseCommand.option_list  + (
            make_option('--newHardware',
                dest='newHardware',
                help='name of new hardware'),
            make_option('--oldHardware',
                dest='oldHardware',
                help='name of old hardware'),
            )

    def handle(self, *args, **options):
        try:
            serverList = Server.objects.filter(hardware_type=options['oldHardware'])
            for server in serverList:
                server.hardware_type=options['newHardware']
                server.save()
        except Exception as e:
            raise CommandError("Error found - " + str(e))


