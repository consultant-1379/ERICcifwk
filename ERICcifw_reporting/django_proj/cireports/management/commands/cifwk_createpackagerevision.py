from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create a new version of this package"
    option_list = BaseCommand.option_list  + (
            make_option('--name',
                dest='package',
                help='name of the package to create'),
            make_option('--number',
                dest='number',
                help='product number (CXP1234567'),
            make_option('--ver',
                dest='ver',
                help='product version to create'),
            make_option('--groupid',
                dest='gid',
                help='package groupId'),
            make_option('--type',
                dest='type',
                help='Package type to be created'),
            make_option('--intendedDrop',
                dest='intendedDrop',
                help='Package intended Drop'),
            make_option('--product',
                dest='product',
                help='product'),
            make_option('--autoDeliver',
                dest='autoDeliver',
                help='Package auto deliver Flag'),
            make_option('--mediaCategory',
                dest='category',
                help='Package Category to be created'),
            make_option('--mediaPath',
                dest='mediaPath',
                help='Package Media Path to be created'),
            )

    def handle(self, *args, **options):
        intendedDrop = None
        mediaPath = None
        autoDeliver = False
        if options['package'] is None:
            raise CommandError("You need to provide a name for the package, in the form \"ERICxyz_CXP1234567\"")
        if options['ver'] is None:
            raise CommandError("You need to specify the version to create")
        if options['type'] is None:
            raise CommandError("You need to specify the type of package to create")
        if options['mediaPath'] != None:
           mediaPath = options['mediaPath']
        category = cireports.utils.mediaCategoryCheck(options['category'])
        if "Error" in str(category):
            raise CommandError(category)
        if options['intendedDrop'] != None:
            if options['product'] is None:
                raise CommandError("You need to specify product if you using intended Drop")
            intendedDropInfo =  cireports.utils.getIntendedDropInfo(options['intendedDrop'], options['product'])
            if "error" in intendedDropInfo:
                raise CommandError("Problem While Requiring Intended Drop Information - "+ str(intendedDropInfo)+"\n")
            intendedDrop = intendedDropInfo
        else:
            intendedDrop = "latest"
        if options['autoDeliver'] != None:
           autoDeliver = True
        else:
           autoDeliver = False           
        

        try:
            cireports.utils.createPackageRevision(options['package'], options['ver'], options['type'], options['gid'], options['package'], category, options['mediaPath'], intendedDrop, autoDeliver)
        except cireports.utils.AlreadyExists as e:
            raise CommandError("Package revision already exists - " + str(e))
        return "OK"
