import os,socket
import logging
logger = logging.getLogger(__name__)
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import fwk.monitorLocalDiskUsage

class Command(BaseCommand):
    '''
    '''
    help = "\n\
            Monitor the amount of usage of a given Directory or Filesystem Mount.\n\
            With this option a size can be given and only directories or Files over\n\
            or equal to that size will be monitored\n\
           "
    option_list = BaseCommand.option_list  + (
            make_option('--filesystem [filesystem]',
                dest='filesystem',
                help='Enter the name of the fileSystem or directory to be monitored'),
            make_option('--monitorType [File] [Directory]',
                dest='monitorType',
                help='Please select Monitor Type as Detailed or Simple'),
            make_option('--sizeInBytes [INT in Bytes]',
                dest='sizeInBytes',
                help='The size of files or directories to monitor, this is in bytes.'),
            )

    def handle(self, *args, **options):
        if options['filesystem'] == None:
            raise CommandError("Please enter filesystem or directory of choice eg: '/', '/boot/, '/proj/lciadm100' etc...")
        if options['sizeInBytes'] == None:
           options['sizeInBytes'] = "1000" 
        if options['monitorType'] == None:
            raise CommandError("Please Select Monitor Type")

        fileSystem = options['filesystem']    
        sizeInBytes = options['sizeInBytes']
        monitorType = options['monitorType'].lower()
        sizeInBytes = int(sizeInBytes)
        hostname = socket.gethostname() 
        
        if monitorType == "file":
            try:
                fwk.monitorLocalDiskUsage.monitorFileOrDirectorySize(fileSystem,sizeInBytes)
                logger.info("Successfully returned the Monitor Storage Usage for: " +str(hostname))
            except Exception as e:
                logger.error("Issue returning the Storage Disk Usage for: " +str(hostname)+ ". Error: " +str(e))
        elif monitorType == "directory":
            try:
                fwk.monitorLocalDiskUsage.monitorFilesytemRootDirSize(fileSystem)
                logger.info("Successfully returned the Monitor Storage Usage for: " +str(hostname))
            except Exception as e:
                logger.error("Issue returning the Storage Disk Usage for: " +str(hostname)+ ". Error: " +str(e))                
        else:
            raise CommandError("Please Select a correct Value for monitorType and try again")

