from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from dmt.models import *
from dmt.utils import *

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
            make_option('--clustetType',
                dest='clusterType',
                help='The Type of Cluster it is LSB or JBOSS'),
            make_option('--selectedNodes',
                dest='selectedNodes',
                help='The Node the service unit can apply to e.g SC-1,SC-2'),
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

        if options['selectedNodes'] == None:
           raise CommandError("Specify Selected Nodes. Please try Again....") 
        else:
           selectedNodes = options['selectedNodes'].upper()

        if options['serviceGroup'] == None:
           raise CommandError("Specify a Service Group. Please try Again....") 
        else:
           serviceGroup = options['serviceGroup']
        if options['cluster'] == None:
           raise CommandError("Specify a Cluster id. Please try Again....") 
        else:
           cluster = options['cluster']

        if options['clusterType'] == None:
           raise CommandError("Specify a Cluster Type. Please try Again....") 
        else:
            if options['clusterType'] == "LSB":
                clusterType = "LSB Service Cluster"
            elif options['clusterType'] == "JBOSS":
                clusterType = serviceGroup
            else:
                raise CommandError("Specify a valid Cluster Type JBOSS or LSB. Please try Again....")

        serviceClr = ServicesCluster.objects.get(cluster_id=cluster,name=serviceGroup)
        serviceGroup = ServiceGroup.objects.filter(service_cluster_id=serviceClr,name=name)
        if not serviceGroup:
            returnedValue = dmt.utils.savedServiceGroupInstance(name,clusterType,selectedNodes,serviceClr)
            if returnedValue == 1:
                logger.info("ERROR: Service Unit did not save correctly")
                sys.exit(1)
            else:
                logger.info("Success added " + name)
                sys.exit(0)
        else:
            logger.info("Service unit already added to DB for cluster id " + cluster)
            sys.exit(1)


