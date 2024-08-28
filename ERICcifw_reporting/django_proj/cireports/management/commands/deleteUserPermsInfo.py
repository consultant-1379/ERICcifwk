from django.core.management.base import BaseCommand, CommandError
import sys
import logging
from django.contrib.auth.models import *
import json

from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        superUsersList = ["admin", "ejohmci", "emanjoh", "eavrbra", "lmirbe", "ericjef", "emarfah", "eeiccry"]
        allowedUserPerms = ["Can add component","Can add cdb types","Can delete document","Can add document type","Can change document type","Can add drop","Can change drop","Can add drop limited reason","Can add fem link","Can change fem link","Can add jira type exclusion","Can change jira type exclusion","Can delete jira type exclusion","Can add media artifact","Can add media artifact type","Can add non product email","Can add package","Can add product","Can add product drop to cdb type map","Can change product drop to cdb type map","Can add product email","Can change product email","Can add product set","Can add product set release","Can change product set release","Can add product set ver to cdb type map","Can change product set ver to cdb type map","Can add reasons for no kgb status","Can add release","Can change release","Can add product to server type mapping","Can change product to server type mapping","Can add service group unit"]

        super_users = User.objects.filter(is_superuser=1)
        for user in super_users:
            if user.username not in superUsersList:
                print "removing super from: " + user.username
                user.is_superuser=False
                user.save()

        all_users = User.objects.all()
        permUsersDict = {}
        for user in all_users:
            print "Processing permissions for user "+user.username
            userPerms = user.user_permissions
            for userPerm in userPerms.all():
                userPerm = str(userPerm).split(" | ")[2]
                userPermObj = Permission.objects.filter(name=userPerm)
                for perm in userPermObj:
                    user.user_permissions.remove(perm)

        groups = Group.objects.all()
        for group in groups:
            print "Processing permissions for group "+group.name
            groupPerms = group.permissions
            for groupPerm in groupPerms.all():
                groupPermName = str(groupPerm).split(" | ")[2]
                groupPermTable = str(groupPerm).split(" | ")[0]
                groupPermObj = Permission.objects.get(id=groupPerm.id)
                if groupPermObj.name in allowedUserPerms:
                    if "avs" in str(groupPerm):
                        print "Removing disallowed Permission"
                        group.permissions.remove(groupPermObj)
                    print "Ignoring approved Perm"
                    continue
                group.permissions.remove(groupPermObj)
                print "Removing disallowed Permission"
