from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *

import dmt.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):


    def handle(self, *args, **options):
        servers = Server.objects.all()
        try:
            for server in servers:
                logger.info(str(server))
                if "159.107.173.3" == str(server.dns_serverA):
                    server.dns_serverB = "159.107.173.12"
                    server.save()
                else:
                    server.dns_serverB = "159.107.173.3"
                    server.save()
        except Exception as e:
            logger.error("Error with Server Details:  " + str(e))
            
