from optparse import OptionParser 
#from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *

import logging
logger = logging.getLogger(__name__)

class vlanClusterMulticastUpdate():
    '''
    This Class is used to update MultiCast Snooping, Querier, Routers and Hash Max values for a Cluster for BR0, BR1, BR3
    BR0, BR1 and BR3 paramters are accepted, delimited by a space for each value above.

    '''

    def main():
        parser = OptionParser()
        parser.add_option('--br0', help='BR0 multiple arguments, space delimiter', dest='br0multi', type = "int", action='store', metavar='<ARG1> <ARG2> <ARG3> <ARG4>', nargs=4)
        parser.add_option('--br1', help='BR1 multiple arguments, space delimiter', dest='br1multi', type = "int", action='store', metavar='<ARG1> <ARG2> <ARG3> <ARG4>', nargs=4)
        parser.add_option('--br3', help='BR3 multiple arguments, space delimiter', dest='br3multi', type = "int", action='store', metavar='<ARG1> <ARG2> <ARG3> <ARG4>', nargs=4)
        (options, args) = parser.parse_args()

        if options.br0multi == None:
            br0multicastSnooping = "1"
            br0multicastQuerier = "1"
            br0multicastRouter ="2"
            br0hashMax ="4096"
        elif options.br0multi != None:
            br0multicastSnooping = options.br0multi[0]
            br0multicastQuerier = options.br0multi[1]
            br0multicastRouter = options.br0multi[2]
            br0hashMax = options.br0multi[3]

        if options.br1multi == None:
            br1multicastSnooping = "1"
            br1multicastQuerier = "0"
            br1multicastRouter ="1"
            br1hashMax ="512"
        elif options.br1multi != None:
            br1multicastSnooping = options.br1multi[0]
            br1multicastQuerier = options.br1multi[1]
            br1multicastRouter = options.br1multi[2]
            br1hashMax = options.br1multi[3]

        if options.br3multi == None:
            br3multicastSnooping = "0"
            br3multicastQuerier = "0"
            br3multicastRouter ="1"
            br3hashMax ="512"
        elif options.br3multi != None:
            br3multicastSnooping = options.br3multi[0]
            br3multicastQuerier = options.br3multi[1]
            br3multicastRouter = options.br3multi[2]
            br3hashMax = options.br3multi[3]
        try:
            multicastTypesDict = { "BR0": "SVC VLAN", "BR1": "Internal VLAN", "BR3":"JGroups VLAN" }
            clusters = Cluster.objects.filter(layout__name="KVM")
            for k, v in multicastTypesDict.iteritems():
                if not VlanMulticastType.objects.filter(name=str(k)).exists():
                    multicastType = VlanMulticastType.objects.create(name=str(k), description=str(v))
                    logger.info("Vlan Multicast Type Created: " + str(multicastType))
            multicastTypesList = VlanMulticastType.objects.all()
            for deployment in clusters:
                logger.info("Cluster: " +  str(deployment.name))
                for item in multicastTypesList:
                    if "BR0" in str(item.name):

                        if VlanClusterMulticast.objects.filter(cluster=deployment, multicast_type=item.id).exists():
                            VlanClusterMulticast.objects.get(cluster=deployment, multicast_type=item).delete()
                            logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " deleted.")
                        VlanClusterMulticast.objects.create(cluster=deployment, multicast_type=item, multicast_snooping=br0multicastSnooping, multicast_querier=br0multicastQuerier, multicast_router=br0multicastRouter, hash_max=br0hashMax)
                        logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " Snooping " +str(br0multicastSnooping) + " , Querier " +str(br0multicastQuerier) + ", Router" +str(br0multicastRouter) + " and hash_max " +str(br0hashMax)+ ".")

                    elif "BR1" in str(item.name):
                        if VlanClusterMulticast.objects.filter(cluster=deployment, multicast_type=item.id).exists():
                            VlanClusterMulticast.objects.get(cluster=deployment, multicast_type=item).delete()
                            logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " deleted.")
                        VlanClusterMulticast.objects.create(cluster=deployment, multicast_type=item, multicast_snooping=br1multicastSnooping, multicast_querier=br1multicastQuerier, multicast_router=br1multicastRouter, hash_max=br1hashMax)
                        logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " Snooping " +str(br1multicastSnooping) + " , Querier " +str(br1multicastQuerier) + ", Router" +str(br1multicastRouter) + " and hash_max " +str(br1hashMax) + ".")

                    elif "BR3" in str(item.name):
                        if VlanClusterMulticast.objects.filter(cluster=deployment, multicast_type=item.id).exists():
                            VlanClusterMulticast.objects.get(cluster=deployment, multicast_type=item).delete()
                            logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " deleted.")
                        VlanClusterMulticast.objects.create(cluster=deployment, multicast_type=item, multicast_snooping=br3multicastSnooping, multicast_querier=br3multicastQuerier, multicast_router=br3multicastRouter, hash_max=br3hashMax)
                        logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " Snooping " +str(br3multicastSnooping) + " , Querier " +str(br3multicastQuerier) + ", Router" +str(br3multicastRouter) +" and hash_max " +str(br3hashMax) + ".")

                logger.info("Vlan Cluster Multicasts Created: " + str(VlanClusterMulticast.objects.filter(cluster=deployment)))
        except Exception as e:
            raise CommandError("Error found - " + str(e))

        try:
            multicastTypesDict = { "BR0": "SVC VLAN", "BR3":"JGroups VLAN" }
            clusterServers = ClusterServer.objects.filter(node_type__startswith="SVC")
            for k, v in multicastTypesDict.iteritems():
                if not VlanMulticastType.objects.filter(name=str(k)).exists():
                    multicastType = VlanMulticastType.objects.create(name=str(k), description=str(v))
                    logger.info("Vlan Multicast Type Created: " + str(multicastType))
            multicastTypesList = VlanMulticastType.objects.all()
            for clustSer in clusterServers:
                logger.info("Cluster Server: " + str(clustSer.server.hostname))
                for item in multicastTypesList:
                    if "BR0" in str(item.name):
                        if VlanMulticast.objects.filter(clusterServer=clustSer, multicast_type=item).exists():
                            VlanMulticast.objects.get(clusterServer=clustSer, multicast_type=item).delete()
                            logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " deleted.")
                        VlanClusterMulticast.objects.create(cluster=deployment, multicast_type=item, multicast_snooping=br0multicastSnooping, multicast_querier=br0multicastQuerier, multicast_router=br0multicastRouter, hash_max=br0hashMax)
                        logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " Snooping " +str(br0multicastSnooping)  +" , Querier " +str(br0multicastQuerier)  +", Router" +str(br0multicastRouter)  +" and hash_max " +str(br0hashMax)  +".")

                    elif "BR3" in str(item.name):
                        if VlanMulticast.objects.filter(clusterServer=clustSer, multicast_type=item).exists():
                            VlanMulticast.objects.get(clusterServer=clustSer, multicast_type=item).delete()
                            logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " deleted.")
                        VlanClusterMulticast.objects.create(cluster=deployment, multicast_type=item, multicast_snooping=br3multicastSnooping, multicast_querier=br3multicastQuerier, multicast_router=br3multicastRouter, hash_max=br3hashMax)
                        logger.info("Cluster: " + str(deployment) + " Multicast: " + str(item) + " Snooping " +str(br3multicastSnooping)  +" , Querier " +str(br3multicastQuerier)  +", Router" +str(br3multicastRouter)  +" and hash_max " +str(br3hashMax) +".")
                logger.info("Vlan Multicasts Created: " + str(VlanMulticast.objects.filter(clusterServer=clustSer)))
        except Exception as e:
            raise CommandError("Error found - " + str(e))

    main()
