from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils
from django.contrib.auth.models import User, Group

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Command to create user, create group and add user to group"
    option_list = BaseCommand.option_list  + (
            make_option('--signum',
                dest='signum',
                help='signum'),
            make_option('--password',
                dest='password',
                help='password'),
            make_option('--group',
                dest='group',
                help='group to create or add user to'),
            )

    def handle(self, *args, **options):
        if options['signum'] is None:
            raise CommandError("You need to provide a signum")
        if options['password'] is None:
            raise CommandError("You need provide a password")


        try:
            user=User.objects.create_user(username=options['signum'], email="",  password=options['password'])
            if not options['group'] is None: 
                group,created=Group.objects.get_or_create(name=str(options['group']))
                user.groups.add(group)        
            return "OK"
        except Exception as e:
            raise CommandError("Error during User creation - " + str(e))
