from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import dmt.sftp
import subprocess
import time

class Command(BaseCommand):
    help = "SFTP File transfer"
    option_list = BaseCommand.option_list  + (
            make_option('--node',
                dest='node',
                help='name of the node to connect to'),
            make_option('--port',
                 dest='port', type='int',
                 help='name of the port to connect through'),
            make_option('--user',
                dest='user',
                help='Log on id to use'),
            make_option('--password',
                dest='password',
                help='Password to use for Logon'),
            make_option('--remotefile',
                dest='remotefile',
                help='Directory structure and file name of file on a remote server i.e. /home/emanjoh/file.txt'),
            make_option('--localfile',
                dest='localfile',
                help='Directory structure and file name of file on a local server i.e. /home/emanjoh/file.txt'),
            make_option('--type',
                dest='type',
                help='set to put or get depending on what you want to do'),
            )

    def handle(self, *args, **options):
        dmt.sftp.sftp(options['node'], options['port'], options['user'], options['password'], options['remotefile'], options['localfile'], options['type'])
