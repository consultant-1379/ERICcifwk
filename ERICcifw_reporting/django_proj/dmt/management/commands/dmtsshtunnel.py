from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import dmt.sshtunnel
import subprocess
import time
import getpass

DEFAULT_PORT = 4000

class Command(BaseCommand):
    help = "Used to create a ssh tunnel"
    option_list = BaseCommand.option_list  + (
            make_option('--quiet',
                dest='verboses', action='store_false', default=True,
                help='Stop all informational output'),
            make_option('--local-port',
                 action='store', type='int', dest='port',default=DEFAULT_PORT,
                 help='local port to forward (default: %d)' % DEFAULT_PORT),
            make_option('--user',
                action='store', type='string', dest='user', default=getpass.getuser(),
                help='username for SSH authentication (default: %s)' % getpass.getuser()),
            make_option('--key',
                action='store', type='string', dest='keyfile', default=None,
                help='private key file to use for SSH authentication'),
            make_option('--no-key',
                action='store_false', dest='look_for_keys', default=True,
                help='don\'t look for or use a private key file'),
            make_option('--password', 
                action='store', type='string', dest='password',
                help='Give password as an input for remote host'),
            make_option('--remote',
                action='store', type='string', dest='remote', default=None, metavar='host:port',
                help='remote host and port to forward to'),
            make_option('--local',
                action='store', type='string', dest='local', default=None, metavar='host:port',
                help='local host and port to pass through'),
            )

    def handle(self, *args, **options):        
        dmt.sshtunnel.main(options['verboses'], options['port'], options['user'], options['keyfile'], options['look_for_keys'] , options['password'], options['remote'], options['local'])
