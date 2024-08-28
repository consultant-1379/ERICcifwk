import struct, socket
from dmt.models import *

import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()

def getAvailablePort(startPort,endPort,portDBName):
    '''
    Used to get the next available port according to inputs given
    '''
    # Get the info as a object whether from the port database or the mcast database
    if portDBName == "msgPort":
        mcasts = ClusterMulticast.objects.all().order_by('enm_messaging_port')
    elif portDBName == "udpPort":
        mcasts = ClusterMulticast.objects.all().order_by('udp_multicast_port')
    else:
        logger.error("Please contact the system Admin as the Port assignment has thrown an error")
        return "No Port Available"
        
    for m in mcasts:
        startPort = int(startPort) + 1
        if portDBName == "msgPort":
            oldPort = m.enm_messaging_port
        elif portDBName == "udpPort":
            oldPort = m.udp_multicast_port
        else:
            logger.error("Please contact the system Admin as the Port assignment has thrown an error")
            return "No Port Available"
        if oldPort > startPort:
            # Check to see does the value already exist in the database
            newPortCheck = portinDB(portDBName, startPort)
            if newPortCheck:
                continue
            logger.info("Got missing port " + str(startPort))
            return startPort
    
    breakOut = 1
    while breakOut == 1:
        startPort = int(startPort) + 1
        if startPort <= endPort:
            # Check to see does the value already exist in the database
            newPortCheck = portinDB(portDBName, startPort)
            if newPortCheck:
                continue
            logger.info("Got port number " + str(startPort))
            return startPort
        else:
            breakOut = 0
    # If we got here, all our ports are used up! 
    logger.error("All ports for this range are used : " + str(startPort) + " --> " + str(endPort))
    return "No Port Available"

def portinDB(portDBName, startPort):
    '''
    Used to check is the choosen port with the DB already 
    '''
    # Check to see does the value already exist in the database
    if portDBName == "msgPort":
        newPortCheck = ClusterMulticast.objects.filter(enm_messaging_port=startPort)
    elif portDBName == "udpPort":
        newPortCheck = ClusterMulticast.objects.filter(udp_multicast_port=startPort)
    return newPortCheck

def getAvailableMulticastPorts():
    '''
    Used to set the information for the Multicast Ports 
    '''
    data = {}

    startPort = "40001"
    endPort = "50001"
    portDBName = "udpPort"
    data['udpPort'] = getAvailablePort(startPort,endPort,portDBName)

    startPort = "31001"
    endPort = "32000"
    portDBName = "msgPort"
    data['msgPort'] = getAvailablePort(startPort,endPort,portDBName)

    return data
