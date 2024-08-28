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
        super_users = User.objects.filter(is_superuser=1)
        for user in super_users:
            print user.username + " is a superuser"

        all_users = User.objects.all()
        permUsersDict = {}
        groupUsersDict = {}
        for user in all_users:
            userGroups = user.groups.all()
            for group in userGroups:
                if group.name not in groupUsersDict.keys():
                    groupUsersDict[group.name] = {"Users": [], "Perms" : []}
                groupUsersDict[group.name]["Users"].append(user.username)
                groupPerms = group.permissions
                for groupPerm in groupPerms.all():
                    groupPerm = str(groupPerm).split(" | ")[2]
                    if groupPerm not in groupUsersDict[group.name]["Perms"]:
                        groupUsersDict[group.name]["Perms"].append(groupPerm)
            userPerms = user.user_permissions
            for userPerm in userPerms.all():
                userPerm = str(userPerm).split(" | ")[2]
                if userPerm not in permUsersDict.keys():
                    permUsersDict[userPerm] = []
                permUsersDict[userPerm].append(user.username)

        print json.dumps(permUsersDict, indent=4, sort_keys=True)

        print json.dumps(groupUsersDict, indent=4, sort_keys=True)


