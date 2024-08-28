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
            req = urlopen('https://ci-portal.seli.wh.rnd.internal.ericsson.com/getver/')
            options['ciVersion'] =  req.read()
            print "---"
            print options['ciVersion']
        ciFwkVer =  options['ciVersion']
        print "Installing version :" +str(ciFwkVer)
        groupId = re.sub('\.','/', config.get("CIFWK", "groupId"))
        artifactId = config.get("CIFWK", "artifactId")
        base = config.get("CIFWK_TEST_ENVIRONMENT", "installBase")
        dwnldName = artifactId + "-" + str(ciFwkVer) + ".zip"
        dwnldLoc = "/var/tmp/"
        logger.info("Downloading version " + ciFwkVer)
        # Get the artifact down from nexus
        fileToGet = config.get("CIFWK", "nexus_url") + "/releases/" + groupId + "/" + artifactId + "/" + ciFwkVer + "/" + dwnldName
        try:
            logger.info("filetoget :" + str(fileToGet))
            logger.info("dwnldLoc :" + str(dwnldLoc))
            fwk.utils.downloadFile(fileToGet, dwnldLoc)
        except Exception as e:
            logger.error("Got an exception retrieving " + fileToGet + ": " + str(e))
            return "There was a problem trying to download this version, please contact your Administrator"

        sftpNode = "192.168.0.42"
        sftpPort = 22
        sftpUser = config.get('DMT_SFTP', 'sftpUser')
        sftpPassword = config.get('DMT_SFTP', 'sftpPassword')
        sftpLocalFile = "/var/tmp/"+str(dwnldName)
        sftpRemoteFile = "/var/tmp/"+str(dwnldName)
        sftpType= "put"
        try:
            dmt.sftp.sftp(sftpNode, sftpPort, sftpUser, sftpPassword, sftpLocalFile, sftpRemoteFile,sftpType)
        except Exception as e:
            logger.info("ftp gives error due to current tunnel method")
        sshCommand = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@192.168.0.42"

        serverLogonSpawn = pexpect.spawn(sshCommand)
        serverLogonSpawn.logfile = sys.stdout
        serverLogonSpawn.expect ('password:')
        serverLogonSpawn.sendline ('12shroot')
        serverLogonSpawn.expect ('#')
        serverLogonSpawn.sendline ('pwd')
        serverLogonSpawn.expect ('#')
        serverLogonSpawn.sendline ('su - lciadm100')
        serverLogonSpawn.expect (' ~]\$')
        serverLogonSpawn.sendline ('cd /proj/lciadm100/cifwk/')
        serverLogonSpawn.expect (']\$')
        extract = "unzip -q " + dwnldLoc + dwnldName + " -d " + base
        serverLogonSpawn.sendline (extract)
        serverLogonSpawn.expect (']\$')
        ln_command="ln -s "+str(ciFwkVer)+" latest"
        serverLogonSpawn.sendline (ln_command)
        serverLogonSpawn.expect (']\$')
        serverLogonSpawn.sendline ('/proj/lciadm100/cifwk/latest/test/scripts/createdb.sh')
        serverLogonSpawn.expect ('Enter password:')
        serverLogonSpawn.sendline ('12shroot')
        serverLogonSpawn.expect (']\$')
        serverLogonSpawn.sendline ('mysql --no-defaults -v -v -v -v -v --user=root -p cireports < /proj/lciadm100/cifwk/latest/sql/cifwk.sql')
        serverLogonSpawn.expect ('Enter password:')
        serverLogonSpawn.sendline ('12shroot')
        serverLogonSpawn.expect (']\$')
        serverLogonSpawn.sendline ('python /proj/lciadm100/cifwk/latest/django_proj/manage.py syncdb')
        serverLogonSpawn.expect ('Would you like to create one now?')
        serverLogonSpawn.sendline ('yes')
        serverLogonSpawn.expect ('Username')
        serverLogonSpawn.sendline ('admin')
        serverLogonSpawn.expect ('E-mail address:')
        serverLogonSpawn.sendline ('admin@localhost.com')
        serverLogonSpawn.expect ('Password:')
        serverLogonSpawn.sendline ('admin')
        serverLogonSpawn.expect ('again')
        serverLogonSpawn.sendline ('admin')
        serverLogonSpawn.expect ('Superuser created successfully')
        serverLogonSpawn.expect (']\$')
        serverLogonSpawn.sendline ('/proj/lciadm100/cifwk/latest/etc/init.d/cifwk-httpd start')
        serverLogonSpawn.expect ('\[0;32m  OK  ')
        print serverLogonSpawn.before

