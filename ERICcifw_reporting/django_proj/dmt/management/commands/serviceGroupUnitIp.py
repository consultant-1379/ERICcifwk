from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from dmt.models import *
from dmt.utils import *
from dmt.mcast import *

import sys, os, tempfile, shutil

import logging

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to used during testing to check we Service unit data to the DB
    '''
    help = "Class to Save the Service Unit to DB"
    option_list = BaseCommand.option_list  + (
            make_option('--name',
                dest='name',
                help='The name of the cluster type'),
            make_option('--hostname',
                dest='hostname',
                help='The hostname'),
            make_option('--serviceGroup',
                dest='serviceGroup',
                help='The service group to add the service unit to'),
            make_option('--cluster',
                dest='cluster',
                help='The cluster id you wish to add the service unit to'),
            )

    def handle(self, *args, **options):

        # Checks to ensure all required parameters are entered
        if options['name'] == None:
           raise CommandError("Specify a Name. Please try Again....")
        else:
           name = options['name']

        if options['hostname'] == None:
           hostname = "None"
        else:
           hostname = options['hostname']

        if options['serviceGroup'] == None:
           raise CommandError("Specify a Service Group. Please try Again....")
        else:
           serviceGroup = options['serviceGroup']
        if options['cluster'] == None:
           raise CommandError("Specify a Cluster id. Please try Again....")
        else:
           cluster = options['cluster']

        try:
            serviceClr = ServicesCluster.objects.get(cluster_id=cluster,name=serviceGroup)
        except Exception as e:
            logger.error("Unable to get Service Cluster data " + str(e))

        try:
            serviceGroup = ServiceGroup.objects.get(service_cluster_id=serviceClr,name=name)
        except Exception as e:
            logger.info("Unable to get Service Group Data " + str(e))
            sys.exit(1)

        try:
            InstName = dmt.mcast.getAvailableServiceName(serviceGroup.id,False)
            cluster = Cluster.objects.get(id=cluster)
            instanceGateway,instanceIpAddress,instanceBitmask = dmt.utils.getServiceGroupInstanceIpAddress(cluster.id,False)
            ipType="serviceUnit_" + str(serviceGroup.id)
            returnedValue = dmt.utils.savedServiceGroupInstanceIp(instanceIpAddress,instanceBitmask,instanceGateway,ipType,InstName,hostname,serviceGroup)
            if returnedValue == 1:
                logger.info("Failed to add Service Unit Information for " + str(serviceGroup.name))
                sys.exit(1)
            else:
                logger.info("Success added Service Unit for " + str(serviceGroup.name))
                sys.exit(0)
        except Exception as e:
            logger.info("Unable to save Service Unit IP Data " + str(e))
            sys.exit(1)
