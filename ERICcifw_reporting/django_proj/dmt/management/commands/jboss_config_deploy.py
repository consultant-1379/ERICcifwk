from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from dmt.models import *

import dmt.utils
import sys, os, tempfile, shutil

import logging

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class to open an ssh tunnel, edit the JBOSS Config files, send the config files 
    to the appropriate location on physical and virtual hardware and run the jboss configuration 
    commands to start jboss successfully
    '''
    help = "Class to get JBOSS Configuration files, SFTP to the Nodes and run the JBOSS Configuration script"
    option_list = BaseCommand.option_list  + (
            make_option('--clusterid',
                dest='clusterId',
                help='ID of the Cluster to be configured'),
            )

    def handle(self, *args, **options):
        if options['clusterId'] == None:
            raise CommandError("To run this option you need to specify the ID of the Cluster to configure")

        clusterId = options['clusterId']
        configFiles = "/proj/lciadm100/cifwk/ERICcifw_reporting/etc/deploy/commands/templates/jboss_config"
        chgVARDict = {}
        tmpArea = tempfile.mkdtemp()

        # Get the Node IPs & Server Name per SC Node 
        cluster = Cluster.objects.get(id=clusterId)
        servers = Server.objects.filter(cluster=cluster)
        serverNameIp = {}

        for server in servers:

            serverName = server.hostname
            serverType = server.node_type
            # We only want to get the info for the Service Controller Nodes
            if not "SC" in serverType: continue

            #Copy the JBOSS Config File to a tmp area for editing
            try:
                dmt.utils.copyFiles(configFiles, tmpArea)
            except Exception as e:
                raise CommandError(str(e))
                return 1

            # Create a list of all files within tmpArea
            fileList=os.listdir(tmpArea)
            nics = []
            # Create an empty dict for gathering the Filename and the directory location to store the files on the node
            # which is gathered from the temp files during editing
            chgVARDict = {}
            server = Server.objects.get(hostname=serverName)
            nic = NetworkInterface.objects.filter(server=server)[:1][0]
            ip = IpAddress.objects.filter(nic=nic)[:1][0]

            # Get IP Address from SC Nodes 
            try:
                chgVARDict = dmt.utils.getIPSCNodes(ip.address,cluster)
            except Exception as e:
                raise CommandError(str(e))
                return 1

            # Create an empty dict for gathering the Filename and the directory location to store the files on the node
            # which is gathered from the temp files during editing
            chgFILEdict = {}

            for file in fileList:
            # Edit the Files with the IP Information
                if "sc" in file:
                    lwrServerType = serverType.lower()
                    # Skip if the filename does not contain the Node type
                    if not lwrServerType in file: continue
                try:
                    chgFILEdict = dmt.utils.editFile(tmpArea, file, chgVARDict, chgFILEdict)
                except Exception as e:
                    raise CommandError(str(e))
                    return 1
                # Upload the Edited files to the SC Nodes
            try:
                dmt.utils.uploadJbossFiles(ip.address,serverType,chgFILEdict)
            except Exception as e:
                raise CommandError(str(e))
                return 1
            # Start the Services per Node
            try:
                dmt.utils.runCommands(ip.address)
            except Exception as e:
                raise CommandError(str(e))
                return 1

        #Remove local tmp Area if it exists
        if (os.path.exists(tmpArea)):
            shutil.rmtree(tmpArea)
        return 0
