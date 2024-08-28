from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

import depmodel.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Get a list of imported packages from a file or files"
    option_list = BaseCommand.option_list  + (
            make_option('--file', action='store',
                dest='filename',
                help='name of the file to get the import list from'),
            make_option('--dir', action='store',
                dest='dirname',
                help='name of the directory to search for Java files'),
            )

    def handle(self, *args, **options):
        if (options['filename'] != None):
            print "File " + options['filename']
            print depmodel.utils.getImportedPackagesFromJavaFile(options['filename'])
        elif (options['dirname'] != None):
            print "directory " + options['dirname']
            depmodel.utils.getImportedPackagesFromJavaFiles(options['dirname'])
