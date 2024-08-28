from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from optparse import make_option
import sys
import os
import logging
import cireports.models
import cireports.utils
import ast
import socket
from django.core.mail import send_mail
import settings
from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def cleanUp():
        # deletes the temporary file
        os.system('rm cireportscopy.txt')

    def handle(self, *args, **options):
        # filters through settings.py and adds appnames
        apps = ""
        for app in settings.INSTALLED_APPS:
            if not "django" in app:
                apps = apps+" "+app

        # Create a cmd variable to hold the system call 
        cmd = "python manage.py sql " +apps+ " > cireportscopy.txt"
        cursor = connection.cursor()
        os.system(cmd)
        # accesses the temporary file to read the list of models
        file = open('cireportscopy.txt','r')
        threshold = 0
        go = 'false'
        emailContent = ''
        field = ''
        # Run through each model
        for line in file.read().split('\n'):
            if 'CREATE TABLE' in line:
                line = line.split(' ')[2]
                name = line[1:-1:]
                cursor.execute("SHOW FIELDS FROM "+name+" where Field = 'id';")
                field = str(cursor.fetchall())
                go = 'true'
            # Determine limits for databases based on id types
            if "int" in field and go == 'true':
                threshold = 2147483647
                if "unsigned" in field:
                    threshold = 4294967295
            if "tinyint" in field and go == 'true':
                threshold = 127
                if "unsigned" in field:
                    threshold = 255
            if "mediumint" in field and go == 'true':
                threshold = 8388607
                if "unsigned" in field:
                    threshold = 16777215
            if "smallint" in field and go == 'true':
                threshold = 32767
                if "unsigned" in field:
                    threshold = 65535
            if "bigint" in field and go == 'true':
                threshold = 9223372036854775807
                if "unsigned" in field:
                    threshold = 18446744073709551615
            # stops reading over the model and checks threshold
            if line == ';':
                go = 'false'
                hostname = socket.gethostname()
                cursor.execute("SELECT COUNT(*) FROM " + name + ";")
                theCount = int(cursor.fetchone()[0])
                # e-mail content
                warningHeader = "Database threshold report by "+str(hostname)
                emailWarning = "\n\n"+name+" has exceeded 80% of its current threshold. It currently has "+str(theCount)+" entries out of its threshold of "+str(threshold)+" entries.\n"\
                +"It is "+str(int(threshold)-int(theCount))+" entries away from exceeding the threshold."
                emailAlert = "\n\n"+name+" has exceeded its threshold of "+str(threshold)+" entries. It currently has "+str(theCount)+" entries.\n"\
                +"It is "+str(int(theCount)-int(threshold))+" entries ahead of its threshold."
                developmentServer = ast.literal_eval(config.get("CIFWK", "testServer"))
                if developmentServer == 1:
                    try:
                        emailRecipients = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", "CI"))
                    except Exception as e:
                        logger.error("Email Recipient CI not available" + str(e))
                else:
                    try:
                        product = cireports.models.Product.objects.get(name="CI")
                        productEmail = cireports.models.ProductEmail.objects.filter(product=product.id)
                        emailRecipients = []
                        if productEmail != None:
                            for delEmail in productEmail:
                                emailRecipients.append(delEmail.email)
                    except Exception as e:
                        logger.error("Email Recipient CI not available" + str(e))
                if theCount > (int(threshold) * 0.80) and theCount < int(threshold):
                    emailContent+=emailWarning
                elif theCount > int(threshold):
                    emailContent+=emailAlert
        # if any thresholds are crossed, the e-mail will have content, which will allow it be sent.
        if emailContent != '':
            emailContent+="\n\nReported from "+hostname
            send_mail(warningHeader,emailContent,hostname,emailRecipients,fail_silently=False)
            self.cleanUp
            return 'Failed'
        # command passes in the event that an e-mail is not sent. i.e. no thresholds have been crossed
        else:
            self.cleanUp
            return 'Passed'
