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
    if portDBName == "msg_group_prt_ports":
        mcasts = Multicast.objects.all().order_by('messaging_group_port')
    elif portDBName == "public_port_base":
        mcasts = Multicast.objects.all().order_by('public_port_base')
    elif portDBName == "udp_mcast_prt":
        mcasts = Multicast.objects.all().order_by('udp_mcast_port')
    elif portDBName == "default_mcast_prt":
        mcasts = Multicast.objects.all().order_by('default_mcast_port')
    elif portDBName == "mping_mcast_prt":
        mcasts = Multicast.objects.all().order_by('mping_mcast_port')
    else:
        logger.error("Please contact the system Admin as the Port assignment has thrown an error")
        return "No Port Available"
        
    for m in mcasts:
        startPort = int(startPort) + 1
        if portDBName == "msg_group_prt_ports":
            oldPort = m.messaging_group_port
        elif portDBName == "udp_mcast_prt":
            oldPort = m.udp_mcast_port
        elif portDBName == "default_mcast_prt":
            oldPort = m.default_mcast_port
        elif portDBName =="public_port_base":
            oldPort = m.public_port_base
        else:
            oldPort = m.mping_mcast_port
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
    if portDBName == "msg_group_prt_ports":
        newPortCheck = Multicast.objects.filter(messaging_group_port=startPort)
    elif portDBName == "udp_mcast_prt":
        newPortCheck = Multicast.objects.filter(udp_mcast_port=startPort)
    elif portDBName =="default_mcast_prt":
        newPortCheck = Multicast.objects.filter(default_mcast_port=startPort)
    elif portDBName =="public_port_base":
        newPortCheck = Multicast.objects.filter(public_port_base=startPort)
    else:
        newPortCheck = Multicast.objects.filter(mping_mcast_port=startPort)
    return newPortCheck

def getAvailableServiceName(serviceGroupId, internal=False):
    # Deprecated after KVM is released
    if internal:
        instancesNames = ServiceGroupInstanceInternal.objects.filter(service_group_id=serviceGroupId).order_by('name')
    else:
        instancesNames = ServiceGroupInstance.objects.filter(service_group_id=serviceGroupId).order_by('name')
    x = 0
    for nameNumber in instancesNames:
        number = re.sub(r'.*_', '', nameNumber.name)
        if int(number) != int(x):
            instanName = "su_" + str(x)
            return instanName
        x = x +1
    instanName = "su_" + str(x)
    return instanName

def getAvailableMulticasts():
    '''
    Used to set the information for the Multicast Ports 
    '''
    data = {}
    startPort = "30001"
    endPort = "31000"
    portDBName = "default_mcast_prt"
    data['default_mcast_port'] = getAvailablePort(startPort,endPort,portDBName)

    startPort = "40001"
    endPort = "50001"
    portDBName = "udp_mcast_prt"
    data['udp_mcast_port'] = getAvailablePort(startPort,endPort,portDBName)

    startPort = "50002"
    endPort = "60002"
    portDBName = "mping_mcast_prt"
    data['mping_mcast_port'] = getAvailablePort(startPort,endPort,portDBName)

    startPort = "31001"
    endPort = "32000"
    portDBName = "msg_group_prt_ports"
    data['messaging_group_port'] = getAvailablePort(startPort,endPort,portDBName)

    startPort = "11001"
    endPort = "12000"
    portDBName = "public_port_base"
    data['public_port_base'] = "8080"
    return data

