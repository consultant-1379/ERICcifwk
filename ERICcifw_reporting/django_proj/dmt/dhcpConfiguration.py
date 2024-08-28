import dmt.models
import dmt.createSshConnection
import dmt.utils
import dmt.deploy
import os, time, commands, socket
import logging
import shutil

from dmt.forms import *
from cireports.common_modules.common_functions import *
from datetime import datetime
from netaddr import IPNetwork

logger = logging.getLogger(__name__)

def setupCloudDhcp(mgtServer):
    '''
    Function used to add the special file for cloud deployment
    '''
    logger.info("Adding special Cloud DHCP file for cloud deployment")
    commandOutput = None
    if NetworkInterface.objects.filter(server=mgtServer.server_id, interface="eth0").exists():
        networkObject = NetworkInterface.objects.get(server=mgtServer.server_id, interface="eth0")
        nic = networkObject.mac_address
        if IpAddress.objects.filter(nic=networkObject.id,ipType="host").exists():
            ipAddressObj = IpAddress.objects.get(nic=networkObject.id,ipType="host")
            ipAddress = ipAddressObj.address
    else:
        logger.error("Could not get the server MAC Address")
        return 1, commandOutput
    rmDhcpFile = "[ -d /etc/dhcp_js/ ] && sudo rm -rf /etc/dhcp_js/"
    ret, output = commands.getstatusoutput(str(rmDhcpFile))
    cloudBootSpecial = "sudo bash /root/js.bsh " + mgtServer.server.hostname + " " + str(ipAddress) + " " + str(nic)
    ret, output = commands.getstatusoutput(str(cloudBootSpecial))
    if (ret != 0 ):
        logger.error("Issue run the command \"" + str(cloudBootSpecial) + "\" from the gateway. Please investigate")
        return 1
    return 0

def addClient(mgtServer,hostName,osVersion,kickStartFile,network):
    '''
    Function used to add the server to the jumpstart server
    '''
    logger.info("Adding Client to JumpServer for pxeboot")
    commandOutput = None
    jumpServerDetailsObj = DeploymentDhcpJumpServerDetails.objects.get(server_type="RhelJump")
    if NetworkInterface.objects.filter(server=mgtServer.server_id, interface="eth0").exists():
        networkObject = NetworkInterface.objects.get(server=mgtServer.server_id, interface="eth0")
        nic = networkObject.mac_address
    else:
        logger.error("Could not get the server MAC Address")
        return 1, commandOutput

    try:
        rhelJumpClientLoc = config.get('DMT_AUTODEPLOY', 'rhelDir')
        rhelJumpClientLoc = rhelJumpClientLoc + "/" + str(osVersion) + "/install"
    except Exception as e:
        logger.error("There was an exception getting the rhelDir variable from the DMT_AUTODEPLOY config " + str(e))
        return 1, commandOutput
    try:
        rhelJumpClientAddFile = config.get('DMT_AUTODEPLOY', 'addClient')
    except Exception as e:
        logger.error("There was an exception getting the addClient variable from the DMT_AUTODEPLOY config " + str(e))
        return 1, commandOutput
    try:
        jumpServerIp = dmt.utils.getJumpServerIp(network)
    except Exception as e:
        logger.error("There was an exception getting the rhel Jump Server variable from DeploymentDhcpJumpServerDetails  " + str(e))
        return 1, commandOutput
    try:
        jumpServerUser = jumpServerDetailsObj.server_user
    except Exception as e:
        logger.error("There was an exception getting the rhelJumpServerUser variable from DeploymentDhcpJumpServerDetails " + str(e))
        return 1, commandOutput
    try:
        jumpServerUserPassword = jumpServerDetailsObj.server_password
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the rhelJumpServerUserPassword variable from DeploymentDhcpJumpServerDetails " + str(e))
        return 1, commandOutput

    # Open the ssh connection to the specified server
    fqdnMgtServer = mgtServer.server.hostname + "." + mgtServer.server.domain_name
    user=config.get('DMT_AUTODEPLOY', 'user')
    masterUserPassword = config.get('DMT_AUTODEPLOY', 'masterPasswordCloudMS1')
    keyFileName=config.get('DMT_AUTODEPLOY', 'key')
    jumpServerConnection = None
    (ret, jumpServerConnection) = dmt.createSshConnection.setRemoteConnection(jumpServerIp,jumpServerUser,jumpServerUserPassword,hostName,keyFileName,"cloud")
    if (ret != 0):
        logger.error("Could not create ssh connection to Jumpserver, " + jumpServerIp)
        return 1, commandOutput

    sudo = dmt.utils.checkDhcpJumpSudoRequired(jumpServerIp)
    cmd = sudo + str(rhelJumpClientLoc) + "/" + str(rhelJumpClientAddFile) + " " + str(mgtServer.server.hostname) + " " + str(nic) + " " + str(kickStartFile) + " " + network
    commandOutput = None
    (ret, commandOutput) = jumpServerConnection.runCmdGetOutput(cmd)
    if (ret != 0):
        logger.error("Could not add server configuration to jump server: Return code " + str(ret))
        return ret, commandOutput
    jumpServerConnection.close()
    return 0, commandOutput

def setupDhcp(mgtServer,hostName,type,networkType,pxeBootFile=None):
    '''
    Function used to confige the DHCP server for the Red Hat base install
    '''
    dhcpServerDetailsObj = DeploymentDhcpJumpServerDetails.objects.get(server_type="DHCP")
    if NetworkInterface.objects.filter(server=mgtServer.server_id, interface="eth0").exists():
        networkObject = NetworkInterface.objects.get(server=mgtServer.server_id, interface="eth0")
        nic = networkObject.mac_address
        editedNic = nic.replace(":", "").upper()
        if IpAddress.objects.filter(nic=networkObject.id,ipType="host").exists():
            ipAddressObj = IpAddress.objects.get(nic=networkObject.id,ipType="host")
            ipAddress = ipAddressObj.address
            bitmask = ipAddressObj.bitmask
            IpInfo = IPNetwork(ipAddress + "/" + str(bitmask))
            network = IpInfo.network
        else:
            logger.error("Could not get the server Ip or network address for management server " + str(mgtServer.server.hostname))
            return 1
    else:
        logger.error("Could not get the server MAC Address")
        return 1

    try:
        dhcpServerIp = dhcpServerDetailsObj.ecn_ip
    except Exception as e:
        logger.error("There was an exception getting the dhcpServer variable from DeploymentDhcpJumpServerDetails " + str(e))
        return 1
    try:
        dhcpServerUser = dhcpServerDetailsObj.server_user
    except Exception as e:
        logger.error("There was an exception getting the dhcpServerUser variable from DeploymentDhcpJumpServerDetails " + str(e))
        return 1
    try:
        dhcpUserPassword = dhcpServerDetailsObj.server_password
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the dhcpServerUserPassword variable from DeploymentDhcpJumpServerDetails " + str(e))
        return 1
    try:
        dhtadm = config.get('DMT_AUTODEPLOY', 'dhtadm')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the dhtadm variable from the DMT_AUTODEPLOY config " + str(e))
        return 1
    try:
        pntadm = config.get('DMT_AUTODEPLOY', 'pntadm')
    except Exception as e:
        dmt.utils.dmtError("There was an exception getting the pntadm variable from the DMT_AUTODEPLOY config " + str(e))
        return 1
    try:
        jumpServerIp = dmt.utils.getJumpServerIp(networkType)
    except Exception as e:
        logger.error("There was an exception getting the rhel Jump Server variable from DeploymentDhcpJumpServerDetails " + str(e))
        return 1, commandOutput

    dhcpServerConnection = None
    keyFileName=config.get('DMT_AUTODEPLOY', 'key')
    (ret, dhcpServerConnection) = dmt.createSshConnection.setRemoteConnection(dhcpServerIp,dhcpServerUser,dhcpUserPassword,hostName,keyFileName,"cloud")
    if (ret != 0):
        logger.error("Could not create ssh connection to dhcp server, " + dhcpServerIp)
        return 1

    if (type == "clean"):
        ret = cleanDownDhcpServer(dhcpServerConnection,dhtadm,pntadm,editedNic,ipAddress,network,dhcpServerIp)
        if (ret != 0):
            logger.error("Could not delete configuration from dhtadm command: Return code " + str(ret))
            return ret
    elif(type == "add"):
        ret = addEntriesToDhcpServer(dhcpServerConnection,dhtadm,pntadm,pxeBootFile,editedNic,jumpServerIp,ipAddress,mgtServer,network,dhcpServerIp)
        if (ret != 0):
            logger.error("Could not configuration the dhtadm:  Return code " + str(ret))
            return ret
    else:
        logger.error("Not a support type to configure the DHCP server type support are clean or add")
        return 1
    dhcpServerConnection.close()
    return 0

def addEntriesToDhcpServer(dhcpServerConnection,dhtadm,pntadm,pxeBootFile,editedNic,jumpServerIp,ipAddress,mgtServer,network,dhcpServerIp):
    '''
    function to add the new server details to the DHCP server for pxe boot
    '''

    # configure dhtadm
    pxeBootFile=pxeBootFile.replace("bootfile=","BootFile=")
    sudo = dmt.utils.checkDhcpJumpSudoRequired(dhcpServerIp)
    cmd = sudo + str(dhtadm) + " -g -A -m 01" + str(editedNic) + " -d ':BootSrvA=" + str(jumpServerIp) + ":" + str(pxeBootFile) + ":'"
    dhcpConfig = cmd.replace('\r','')
    commandOutput = None

    ret = dhcpServerConnection.runCmdTty(dhcpConfig)
    if (ret != 0):
        logger.error("Could not configuration the dhtadm:  Return code " + str(ret))
        return ret
    # Configure pntadm
    cmd = sudo + str(pntadm) + " -A " + str(ipAddress) + " -h " + str(mgtServer.server.hostname) + " -c " + str(mgtServer.server.hostname) + " -f PERMANENT -i 01" + str(editedNic) + " -m 01" + str(editedNic) + " -y " + str(network)
    commandOutput = None
    ret = dhcpServerConnection.runCmdTty(cmd)
    if (ret != 0):
        logger.error("Could not configuration the pntadm: Return code " + str(ret))
        return ret
    return 0

def cleanDownDhcpServer(dhcpServerConnection,dhtadm,pntadm,editedNic,ipAddress,network,dhcpServerIp):
    '''
    Function to clean down the DHCP Server to ensure it can take the new configuration for the server
    '''

    # Clean out entry within dhtadm file
    sudo = dmt.utils.checkDhcpJumpSudoRequired(dhcpServerIp)
    cmd = sudo + str(dhtadm) + " -D -m 01" + str(editedNic)
    commandOutput = None
    (ret, commandOutput) = dhcpServerConnection.runCmdGetOutput(cmd)
    if (ret != 0 and str(editedNic) + "does not exist" in commandOutput):
        logger.error("Could not delete configuration from dhtadm command: Return code " + str(ret))
        return ret

    # Clean out the pntadm file
    cmd = sudo + str(pntadm) + " -D " + str(ipAddress) + " -y " + str(network)
    commandOutput = None
    (ret, commandOutput) = dhcpServerConnection.runCmdGetOutput(cmd)
    if (ret != 0 and str(ipAddress) + "does not exist" in commandOutput):
        logger.error("Could not delete configuration from pntadm command: Return code " + str(ret))
        return ret
    return 0
