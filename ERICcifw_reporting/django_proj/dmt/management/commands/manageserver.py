from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *

import dmt.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Manage a server"
    option_list = BaseCommand.option_list  + (
            make_option('--quiet',
                dest='verbose', action='store_false', default=True,
                help='Stop all informational output'),
            make_option('--server',
                dest='server',
                help='name of the server to list'),
            make_option('--addnic',
                dest='addnic', action='store_true', default=False,
                help='Add a NIC to this node'),
            make_option('--listnics',
                dest='listnics', action='store_true', default=False,
                help='List NICs for this server')
            )


    def handle(self, *args, **options):
        if options['server'] == None:
            raise CommandError("You must supply the hostname of a server to manage")

        server = Server.objects.get(hostname=options['server'])
        print "Managing server " + str(server)

        if options['addnic']:
            print "Adding NIC"
            macAddress = dmt.utils.getLowestAvailableMacAddress()
            nic = NetworkInterface(server=server, mac_address=macAddress)
            nic.save()
        elif options['listnics']:
            print "Listing nics"
            nics = NetworkInterface.objects.filter(server=server)
            for nic in nics:
                print "MAC: " + nic.mac_address
