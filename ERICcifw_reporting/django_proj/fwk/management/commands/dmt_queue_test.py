from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group
import os, sys,time


import logging
logger = logging.getLogger(__name__)

from ciconfig import CIConfig
config = CIConfig()
import pexpect



DEFAULT_PORT = 4000


class Command(BaseCommand):
    help = "Install CIFWK"
    option_list = BaseCommand.option_list  + (
            make_option('--ciVersion',
                dest='ciVersion',
                help='version of CI to be installed'),
     )


    def handle(self, *args, **options):
       import pexpect
       p = pexpect.spawn('python /proj/lciadm100/cifwk/latest/django_proj/manage.py litp_tor_deployment --clustergroup pool --litp_ver sp21 --drop 1.0.12 --no-deploy xml_only &', timeout=300)
       p.logfile = sys.stdout
       p.expect ('Selected cluster')
       p.expect ('$')
       p1 = pexpect.spawn('python /proj/lciadm100/cifwk/latest/django_proj/manage.py litp_tor_deployment --clustergroup pool --litp_ver sp21 --drop 1.0.12 --no-deploy xml_only ', timeout=300)
       p1.logfile = sys.stdout
       p1.expect ('$')
       p1.expect ('just created tar file')
       time.sleep(30)
 
