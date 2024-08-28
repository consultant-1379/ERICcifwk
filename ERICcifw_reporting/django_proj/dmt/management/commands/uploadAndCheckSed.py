from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
import dmt.deploy
from dmt.models import *

from cireports.models import *

import sys, os, tempfile, shutil

import logging

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to used during testing to check can we upload a SED and
    Check is it uploaded successfully
    '''
    help = "Class to check the SED Template Upload"
    option_list = BaseCommand.option_list  + (
            make_option('--user',
                dest='user',
                help='The user that uploaded the SED'),
            make_option('--ver',
                dest='ver',
                help='The version of the SED template that is being uploaded'),
            make_option('--jiraNumber',
                dest='jiraNumber',
                help='The jira Number that caused the SED template to be uploaded'),
            make_option('--linkText',
                dest='linkText',
                help='The link Text for the ERIcoll link'),
            make_option('--link',
                dest='link',
                help='The link for the ERIcoll SED'),
            make_option('--iso',
                dest='iso',
                help='The ISO version'),
            make_option('--sedFile',
                dest='sedFile',
                help='The location of the SED Template that content should be uploaded'),
            make_option('--whatToDo',
                dest='whatToDo',
                help='Used to tell the script what needs to be done \
                        options \"upload\" - Used to upload a new SED to the DB \
                                \"checkUser\" - Used to check the user within the DB to ensure it was the same as uploaded \
                                \"checkVersion\" - Used to check the version within the DB to ensure it was the same as uploaded \
                                \"checkJiraNumber\" - Used to check the JIRA number within the DB to ensure it was the same as uploaded \
                                \"checkLinkText\" - Used to check the link text within the DB to ensure it was the same as uploaded \
                                \"checkLink\" - Used to check the link within the DB to ensure it was the same as uploaded \
                                \"checkISO\" - Used to check the ISO version within the DB to ensure it was the same as uploaded \
                                \"checkSed\" - Used to check the SED within the DB to ensure it was the same as uploaded'),
            )

    def handle(self, *args, **options):

        # Checks to ensure all required parameters are entered
        if options['user'] == None:
           raise CommandError("Specify a User. Please try Again....")
        else:
           user = options['user']
        if options['ver'] == None:
           raise CommandError("Specify a SED version. Please try Again....")
        else:
           ver = options['ver']

        if options['jiraNumber'] == None:
           raise CommandError("Specify a JIRA Number. Please try Again....")
        else:
           jiraNumber = options['jiraNumber'].upper()

        if options['linkText'] == None:
            raise CommandError("Specify link Text. Please try Again....")
        else:
            linkText = options['linkText']

        if options['link'] == None:
            raise CommandError("Specify a link. Please try Again....")
        else:
            link = options['link']

        if options['iso'] == None:
            raise CommandError("Specify a iso version. Please try Again....")
        else:
            iso = options['iso']

        if options['sedFile'] == None:
           raise CommandError("Specify a SED File. Please try Again....")
        else:
           sedFile = options['sedFile']

        if options['whatToDo'] == None:
           raise CommandError("Specify What you want to Do. Please try Again....")
        else:
           whatToDo = options['whatToDo']

        try:
            with open (sedFile, "r") as myfile:
                sed=myfile.read()
        except Exception as e:
            logger.error("Unable to read the flat file you have give please ensure the file name and path is correct " + str(e))
            return 1

        if whatToDo == "upload":
            try:
                iso = ISObuild.objects.get(version=iso, drop__release__product__name="ENM", mediaArtifact__testware=0, mediaArtifact__category__name="productware")
                returned = dmt.utils.uploadSedData(user,ver,sed,jiraNumber,iso,linkText,link)
                if returned == 1:
                    logger.info("Upload Unsuccessful for SED Version " + ver)
                    sys.exit(1)
                else:
                    logger.info("Upload Successful for SED Version " + ver + " Uploaded by User " + user)
                    sys.exit(0)
            except Exception as e:
                logger.error("Unable to upload the New SED Template Exception : " + str(e))
                sys.exit(1)
        elif whatToDo != "check" and "check" in whatToDo:
            try:
                returned = dmt.utils.uploadSedCheck(user,ver,sed,jiraNumber,iso,linkText,link,whatToDo)
                if returned == 1:
                    logger.info("Check was unsuccessful for " + whatToDo)
                    sys.exit(1)
                else:
                    logger.info("Check was successful for " + whatToDo)
                    sys.exit(0)
            except Exception as e:
                logger.error("Unable to check the uploaded SED Template with version Exception : " + str(e))
                sys.exit(1)
        else:
            logger.error("Something has gone wrong, unrecognised variable for \"--whatToDo\" parameter " + str(whatToDo) + "???")
            sys.exit(1)
