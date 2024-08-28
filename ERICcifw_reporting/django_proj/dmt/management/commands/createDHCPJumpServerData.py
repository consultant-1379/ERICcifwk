from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        server_pw = "syr1an"
        try:
            details = DeploymentDhcpJumpServerDetails.objects.create(server_type="RhelJump", server_user="jumpadm", server_password=server_pw, ecn_ip="131.160.163.75", edn_ip="10.44.30.246", youlab_ip="10.42.32.21")
            logger.info("DHCP and Jump Details created: " + str(details.server_type))
            details = DeploymentDhcpJumpServerDetails.objects.create(server_type="DHCP", server_user="dhcpadm", server_password=server_pw, ecn_ip="131.160.163.74", edn_ip="10.44.30.245", youlab_ip="10.42.32.20")
            logger.info("DHCP and Jump Details created: " + str(details.server_type))
        except Exception as e:
            raise CommandError("Error found - " + str(e))
