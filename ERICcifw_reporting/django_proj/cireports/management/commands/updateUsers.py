from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import logging
import commands
import re
from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "LDAP lookup of User information and stored in the database Info stored is first name, last name and email address"

    def handle(self, *args, **options):
        firstName = surname = email = None
        updateUserDetailUrl = config.get("CIFWK", "updateUserDetailUrl")
        try:
            count = 0
            allUsers = User.objects.filter(email="")
            for usr in allUsers:
                logger.info("Updating information for User: " + str(usr.username))
                ldapSearchCmd = "ldapsearch -h ldap-egad.internal.ericsson.com -b dc=ericsson,dc=se -w GuWa3EpuBRUqAjAg -D ATVEGAD@ericsson.se 'sAMAccountName=" + str(usr.username)+ "' -p 3268 givenName sn mail"
                output = str(commands.getstatusoutput(ldapSearchCmd))
                firstNameSearch = re.search(r'givenName:\s*(\w+)', output)
                if firstNameSearch:
                    firstName = str(firstNameSearch.group(1))
                else:
                    firstName = str(usr.username)
                lastNameSearch = re.search(r'sn:\s*([a-zA-Z\'-]+)', output)
                if lastNameSearch:
                    surname = str(lastNameSearch.group(1))
                else:
                    surname = str(usr.username)
                emailSearch = re.search(r'mail:\s*([\w.]+@[\w.]+)', output)
                if emailSearch:
                    email = str(emailSearch.group(1))
                else:
                    email = str(usr.username)
                populateUserDataCmd = '/usr/bin/wget -q -O - --no-check-certificate --post-data="signum='+usr.username+'&first='+firstName+'&last='+surname+'&email='+email+ '" ' +updateUserDetailUrl
                commands.getstatusoutput(populateUserDataCmd)
                count = count + 1
            logger.info("Records updated " + str(count))
        except Exception as e:
            return "Error:" +str(e)
