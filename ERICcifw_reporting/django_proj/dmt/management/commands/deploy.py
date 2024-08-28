from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

import dmt.cloud
import sys, os, tempfile

import logging

logger = logging.getLogger(__name__)

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to open an SSH Tunnel, then pull down rpm's from Nexus
    Once the rpms are down in a local directory, these rpmS will be SFTP's over the
    SSH tunnel to the LITP LMS, once complete the SSH Tunnel should be killed.
    '''
    help = "Class to get rpmS from NEXUS and SFTP to LMS"
    option_list = BaseCommand.option_list  + (
            make_option('--remotedir',
                dest='remoteDirectory',
                help='Remote Directory that rpm(s) will be uploaded to from local Directory'),
            make_option('--lmsip',
                dest='lmsip',
                help='IP Address of LMS Server'),
            make_option('--gwip',
                dest='gwip',
                help='IP Address of the LITP Gateway Server'),
            make_option('--rpmver',
                dest='rpmver',
                help='The ENM Drop ie: 1.1.1, 2.1.3, 3.1.1'),
            make_option('--rpmname',
                dest='rpmname',
                help='The name of the RPM to retrieve'),
            )
    tunnelPid = 0
    rpmLocalDirectory = None

    def handle(self, *args, **options):
        if options['remoteDirectory'] == None:
            raise CommandError("To run this option you need to specify the Remote LMS LITP Directory and this directory needs to exist")
        if options['lmsip'] == None:
            raise CommandError("To run this option you need to specify the LITP LMS IP address")
        if options['gwip'] == None:
            raise CommandError("To run this option you need to specify the LITP Gateway IP Address")
        if options['rpmver'] == None:
            raise CommandError("To run this option you need to specify the version of the rpm to deploy")
        if options['rpmname'] == None:
            raise CommandError("To run this option you need to specify an RPM to deploy")
        
        #Get the LMS and GW IP addresses and pas to the SSH Tunnel
        lmsIpAddress = options['lmsip']
        lgwIpAddress = options['gwip']
        #Get the SSH Tunnel process ID to allow Killing later and Open SSH Tunnel
        self.tunnelPid = dmt.cloud.createSSHTunnel(lmsIpAddress,lgwIpAddress)
        if ( not self.tunnelPid or self.tunnelPid == 0 ):
            #Raise an exception if there are any problems opening the SSH Tunnel
            raise CommandError("Failed to open SSH Tunnel therefore it may not be possible to SFTP rpm's")

        try:
            #Download the rpmS from Nexus and store in the given directory
            rpmver = options['rpmver']
            rpmname = options['rpmname']
            #Create Temp Local Directory
            self.rpmLocalDirectory = tempfile.mkdtemp()
            if ( not dmt.cloud.downloadArtifact(self.rpmLocalDirectory, rpmname, rpmver)):
                #Raise an Exception if there are problems with downloading the rpm(s)
                self.errorExit("Failed to start RPM Download from Nexus")

            #Get Remote Directory that rpmS will be uploaded to on LITP LMS
            rpmRemoteDirectory = options['remoteDirectory']
            #Initialise an empty list for the contents of the rpm directry
            rpmList = []
            #Add contents of directory into list
            rpmList = os.listdir(self.rpmLocalDirectory)
            print rpmList
            #For each entry in the list upload rpm to the LITPMS
            for rpm in rpmList:
                rpmName = rpm
                if ( not dmt.cloud.uploadArtifactToNode(rpmName,self.rpmLocalDirectory,rpmRemoteDirectory)):
                    #Rasie and exception is there are any problems with SFTP
                    self.errorExit("Failed to Uplaod rpm(s) to LITP LMS")

            #Remove Local Temp Directory and local Files
            for file in os.listdir(self.rpmLocalDirectory):
                filePath = os.path.join(self.rpmLocalDirectory, file)
                try:
                    if os.path.isfile(filePath):
                        os.unlink(filePath)
                        logger.info("Deleted local Temp File: " 
                                +str(filePath) + " with Success")
                except Exception as e:
                    logger.error("There was an issue Deleting File: "
                        +str(filePath) + " Error Thrown: " +str(e))
            try:
                os.removedirs(self.rpmLocalDirectory)
                logger.info("Temp Directory: " + str(self.rpmLocalDirectory) + " Deleted")
            except Exception as e:
                logger.error("Unable to deleted Temp Dir: "
                        +str(self.rpmLocalDirectory)+ " Error Thrown: " + str(e))
        except Exception as e:
            self.errorExit("Error uploading RPM: " + str(e))

        #Once SFTP'n of rpm(s) is complete kill teh SSH Tunnel PID
        if (not dmt.cloud.destroySSHTunnel(self.tunnelPid)):
            #Raise an exception is there is any issues with killing SSH Tunnell PID
            raise CommandError("Failed to shut down SSH Tunnel")

    def errorExit(self, error):
        if (not dmt.cloud.destroySSHTunnel(self.tunnelPid)):
            logger.error("Could not shut down SSH tunnel - PID: " + tunnelPid)
        raise CommandError(error)
