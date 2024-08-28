from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *
from dmt.utils import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            mgmts =  ManagementServer.objects.all()
            username = "root"
            password = "12shroot"
            credType = "admin"
            credentialId = "116188"
            for mgmt in mgmts:
                if ManagementServerCredentialMapping.objects.filter(mgtServer=mgmt,credentials_id=credentialId).exists():
                    credMap = ManagementServerCredentialMapping.objects.get(mgtServer=mgmt,credentials=credentialId)
                    newCred = Credentials.objects.create(username=username, password=password, credentialType=credType)
                    credMap.credentials = newCred
                    credMap.save()
                    logger.info("ManagementServerCredentialMapping Updated: " + str(credMap))
        except Exception as e:
            raise CommandError("Error found - " + str(e))


