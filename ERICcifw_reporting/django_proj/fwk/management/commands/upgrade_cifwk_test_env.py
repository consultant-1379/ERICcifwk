from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud
import logging
logger = logging.getLogger(__name__)
import os, sys, time, signal,logging, re
import paramiko
from urllib2 import urlopen
import dmt.sshtunnel
import subprocess
import time
import getpass
import pexpect
import fwk.utils
from ciconfig import CIConfig
config = CIConfig()
DEFAULT_PORT = 4000

class Command(BaseCommand):
    help = "Install CIFWK"
    option_list = BaseCommand.option_list  + (
            make_option('--ciVersion',
                dest='ciVersion',
                help='version of CI to be installed'),
     )


    def handle(self, *args, **options):
        if options['ciVersion'] == None:
            req = urlopen('https://ci-portal.seli.wh.rnd.internal.ericsson.com/getlatestbuild/')
            options['ciVersion'] =  req.read()
            print "---"
            print options['ciVersion']


        ciFwkVer =  options['ciVersion']
        print "Installing version :" +str(ciFwkVer)
        sshCommand = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@192.168.0.42"
        serverLogonSpawn = pexpect.spawn(sshCommand, timeout=300)
        serverLogonSpawn.logfile = sys.stdout
        serverLogonSpawn.expect ('password:')
        serverLogonSpawn.sendline ('12shroot')
        serverLogonSpawn.expect ('#')
        serverLogonSpawn.sendline ('pwd')
        serverLogonSpawn.expect ('#')
        serverLogonSpawn.sendline ('su - lciadm100')
        serverLogonSpawn.expect (' ~]\$')
        ugCommand = "python /proj/lciadm100/cifwk/latest/django_proj/manage.py cifwk_upgrade "+str(ciFwkVer)
        serverLogonSpawn.sendline (ugCommand)
        i = serverLogonSpawn.expect(['The following content types are stale and need to be deleted','CIFWK has completed Upgrade to new version'])
        if i == 0:
            serverLogonSpawn.sendline ('yes')
            serverLogonSpawn.expect ('CIFWK has completed Upgrade to new version')
        if i == 1:
            print "upgrade complete"

