import dmt.models
import dmt.utils
import dmt.deploy
import pexpect
import os, time, commands, socket
import logging
import shutil

from dmt.forms import *
from cireports.common_modules.common_functions import *
from datetime import datetime

logger = logging.getLogger(__name__)

def findBootSource(mgtServer,searchString):
    '''
    Depending on the type of server, the boot order maybe different we need to find the correct one before changing it
    '''
    # Open the ssh connection to the specified server
    try:
        if Ilo.objects.filter(server=mgtServer.server.id).exists():
            iloObj = Ilo.objects.get(server=mgtServer.server.id)
            iloAddress = iloObj.ipMapIloAddress.address
            iloUsername = iloObj.username
            iloPassword = iloObj.password
        else:
            logger.error("The ilo information doesn't seem to exist for management server " + mgtServer.server.hostname + "." + mgtServer.server.domain_name)
            return 1
    except Exception as e:
        logger.error("There was an exception getting the dhcpServer variable from the DMT_AUTODEPLOY config " + str(e))
        return 1

    bootSourceList = ['bootsource5','bootsource4','bootsource3','bootsource2','bootsource1']
    for bootSource in bootSourceList: 
        sshPromptEntry = 'Are you sure you want to continue connecting'
        spawn=pexpect.spawn('ssh ' + iloUsername + '@' + iloAddress + ' show /system1/bootconfig1/' + str(bootSource))
        output=spawn.expect([sshPromptEntry,'assword:',pexpect.EOF])
        if output==0:
            spawn.sendline("yes")
            output=spawn.expect([sshPromptEntry,'assword:',pexpect.EOF])
        if output==1:
            spawn.sendline(iloPassword)
            spawn.expect(pexpect.EOF)
        elif output==2:
            pass
        if searchString in spawn.before:
            spawn.close()
            return str(bootSource)
        spawn.close()
    logger.error("There was an exception getting the boot order from the MS ilo")
    return 1

def configureBoot(mgtServer,bootFrom):
    '''
    Function used to change the boot order on a server
    '''
    # Open the ssh connection to the specified server
    try:
        if Ilo.objects.filter(server=mgtServer.server.id).exists():
            iloObj = Ilo.objects.get(server=mgtServer.server.id)
            iloAddress = iloObj.ipMapIloAddress.address
            iloUsername = iloObj.username
            iloPassword = iloObj.password
        else:
            logger.error("The ilo information doesn't seem to exist for management server " + mgtServer.server.hostname + "." + mgtServer.server.domain_name)
            return 1
    except Exception as e:
        logger.error("There was an exception getting the dhcpServer variable from the DMT_AUTODEPLOY config " + str(e))
        return 1

    # log onto the MS ILO and add change the boot order or boot the server
    sshPromptEntry = 'Are you sure you want to continue connecting'
    if (bootFrom == "network"):
        # Find which boot source has the BootFmNetwork 
        bootSource = findBootSource(mgtServer,"BootFmNetwork") 
        logger.info("Bootsource Returned " + str(bootSource))
        if "bootsource" not in str(bootSource):
            logger.info("Using the default bootsource for booting from network, bootsource5")
            bootSource = "bootsource5"
        spawn=pexpect.spawn('ssh ' + iloUsername + '@' + iloAddress + ' set /system1/bootconfig1/' + str(bootSource) + ' bootorder=1')
    elif (bootFrom == "disk"):
        # Find which boot source has the BootFmDisk
        bootSource = findBootSource(mgtServer,"BootFmDisk") 
        if "bootsource" not in str(bootSource):
            logger.info("Using the default bootsource for booting from Disc, bootsource3")
            bootSource = "bootsource3"
        spawn=pexpect.spawn('ssh ' + iloUsername + '@' + iloAddress + ' set /system1/bootconfig1/' + str(bootSource) + ' bootorder=1')
    elif (bootFrom == "reset"):
        spawn=pexpect.spawn('ssh ' + iloUsername + '@' + iloAddress + ' reset /system1')
    else:
        logger.error("Not a support bootFrom type please investigate")
        return 1
    output=spawn.expect([sshPromptEntry,'assword:',pexpect.EOF])
    if output==0:
        spawn.sendline("yes")
        output=spawn.expect([sshPromptEntry,'assword:',pexpect.EOF])
    if output==1:
        spawn.sendline(iloPassword)
        spawn.expect(pexpect.EOF)
    elif output==2:
        pass
    spawn.close()
    return 0 
