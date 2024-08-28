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
            Monitor Disk usage of CI FWK System\n\
            Get Usage of Mounted FileSystems and in turn receive an alert if a\n\
                given threshold is reached\n\
           "
    option_list = BaseCommand.option_list  + (
            make_option('--filesystem [all] [filesystem] [comma seperated list]',
                dest='filesystem',
                help='Enter the name of the file System(s) to be monitored or all, if multiple file system need to be monitored please enter a comma seperated list eg /,/boot/,/proc etc ....'),
            make_option('--alerts [Yes | No]',
                dest='alerts',
                help='please select Yes/No here if you select Yes then an email address needs to be provided'),
            make_option('--email [valid email address] [COMMA SEPERATED LIST]',
                dest='email',
                help='If you have chosen Yes to alerts then an email address is required, a list of comma seperated email addresses can be given eg: a@a.com,b@b.com, etc ...'),
            make_option('--threshold [VALUE]',
                dest='threshold',
                help="The threshold value should be the percentage value in which you want to recieve notifications, this is the same for all filesystems, if alerts are selected this value is required"),
            )

    def handle(self, *args, **options):
        if options['filesystem'] == None:
            raise CommandError("Please enter filesystem choice eg: '/', '/boot/, 'all' etc...")
        if options['alerts'] == None:
            raise CommandError("Please select weather you wish to receive an alert")
        if options['alerts'] == "Yes" and (options['email'] == None or options['threshold'] == None):
            raise CommandError("Please ensure Email Address(s) and Threshold Value are entered as Alters has been selected")
        if options['email'] != None:
            email = options['email'].split(",")
            for mail in email:
                try:
                    validate_email(mail)
                except ValidationError as e:
                    raise CommandError("Please enter a Valid Email Address(es), Validation Error: " +str(e))
        filesystem = options['filesystem']    
        alerts = options['alerts'].lower()
        threshold = options['threshold']
        email = options['email']
        hostname = socket.gethostname() 
        
        try:
            response = fwk.monitorLocalDiskUsage.monitorDiskUsage(filesystem,alerts,threshold,email,hostname)
            logger.info("Successfully returned the Monitor Disk Usage for: " +str(hostname))
            return response
        except Exception as e:
            logger.error("Issue returning the Monitor Disk Usage for: " +str(hostname)+ ". Error: " +str(e))
