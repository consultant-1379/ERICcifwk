from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from dmt.models import *
import logging
from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)
import dmt.utils


class Command(BaseCommand):
    help = "Used to allow a registered User to set a version of the SED to be the master version"
    option_list = BaseCommand.option_list  + (
            make_option('--user',
                dest='user',
                help='The signam of an authorized user of the system, this needs to be a LDAP registered Signam eg: eabcdef'),
            make_option('--sedVersion',
                dest='sedVersion',
                help='The Version of the SED that the user requires to be set to the master Set eg: 1.0.1'),
            make_option('--registerUser',
                dest='registerUser',
                help='Register the given user, yes/no'),
            )

    def handle(self, *args, **options):

        if options['user'] == None:
            raise CommandError("User Required")
        else:
            sedUser = options['user']

        if options['sedVersion'] == None:
            raise CommandError("SED Version Required")
        else:
            sedVersion = options['sedVersion']

        idTag = config.get("DMT", "dmtra")

        if User.objects.filter(username=sedUser).exists():
            user = User.objects.get(username=sedUser)
        else:
            return "ERROR: User: " + str(sedUser) + " does not exist in the cifwk database"

        sedGroup = config.get("DMT", "sedgroup")
        if Group.objects.filter(name=sedGroup).exists():
            sedGroupObj = Group.objects.get(name=sedGroup)

        registerUser = options['registerUser']
        if registerUser and registerUser == "yes":
            try:
                user.groups.add(sedGroupObj)
                logger.debug("User: " +str(sedUser)+ " has been registered in the SED group")
            except Exception as error:
                return "ERROR: Issue registering user: " +str(sedUser)+ " in SED Group, please try again"

        if not user.groups.filter(name=sedGroup).exists():
            return "ERROR: User: " + str(sedUser) + " is not authorised to write to modify Master, please try again or register user"

        try:
            if Sed.objects.filter(version=sedVersion).exists():
                sedObj = Sed.objects.get(version=sedVersion)
            else:
                return "This Version of SED entered: " + str(sedVersion) + " does not exist in database, please try again"

            if SedMaster.objects.filter(sedMaster=sedObj).exists():
                return "This Version of SED is already set to Master, nothing to do"
            masterId = sedObj.id
            
            dmt.utils.setSedMaster(idTag,sedUser,masterId)
            return "SUCCESS: SED version: " + str(sedVersion) + " set to master SED"
        except Exception as error:
            return "ERROR: SED version: " + str(sedVersion) + " could not be set to master, Error thrown: " +str(error)
