import dmt.models
import dmt.utils
import dmt.deploy
import pexpect
import os, time, commands, socket
import logging
import shutil
import paramiko
import sys

from dmt.forms import *
from cireports.common_modules.common_functions import *
from datetime import datetime

logger = logging.getLogger(__name__)

def createSshConnection(fqdn,user):
    try:
        connection = dmt.remotecmd.RemoteCmd(user, fqdn)
    except Exception as e:
        logger.error("Issue with the creation of the connection to the Server " + str(fqdn) + ", Exception : " + str(e))
        return 1
    return connection

def setNewSSHKey(fqdn, user, keyFile):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    logger.info("Checking ssh connection to " + str(fqdn))
    try:
        ssh.connect(fqdn, username=user, key_filename=keyFile)
        logger.info("Success ssh connection established to : " + str(fqdn))
        return 0
    except Exception as e:
        logger.info("Unable to established Connection to : " + str(fqdn))
        return "No Connection"

def setAuthorisedKeys(type,fqdn,masterUser,masterUserPassword):
    '''
    Used to put the cloud gateway ssh keys onto the MS Node
    '''
    if "cloud" in type:
        SSHLocation = config.get('DMT_AUTODEPLOY', 'cloudSSHLocation')
    else:
        logger.error("Type not Supported")
        return 1

    userList = ["lciadm100","root"]

    for user in userList:
        if user == "root":
            sshCommand = "sudo ssh"
            catCommand = "sudo cat /root"
        else:
            sshCommand = "ssh"
            catCommand = "cat /home/lciadm100"

        #get the rsa.pub key this is need to add to the authorised keys on the MS server
        try:
            command = (catCommand + '/' + str(SSHLocation) + '/id_rsa.pub')
            rsaPub = commands.getoutput(command)
        except Exception as e:
            logger.error("There was an issue getting public rsa key from the gateway: Exception: " +str(e))
            return 1

        logger.info("Adding " + str(user) + " id_rsa.pub key from Gateway to MS Server")
        # log onto the MS1 and add the rsa key to the authorised keys
        sshPromptEntry = 'Are you sure you want to continue connecting'
        spawn=pexpect.spawn(sshCommand + ' -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ServerAliveInterval=30 ' + masterUser + '@' + fqdn + ' \' if [ ! -d ~/' + str(SSHLocation) + ' ]; then ssh-keygen -N "" -f ~/' + str(SSHLocation) + '/id_rsa -t rsa > /dev/null 2>&1; fi; echo ' + str(rsaPub) + ' >> ~/' + str(SSHLocation) + '/authorized_keys; chmod 600 ~/' + str(SSHLocation) + '/authorized_keys;\'')
        output=spawn.expect([sshPromptEntry,'assword:',pexpect.EOF])
        #Based on output 3 possibilities , one may request machine to be added to known hosts (no) if machine is known password is requested else there is an issue
        if output==0:
            spawn.sendline("yes")
            output=spawn.expect([sshPromptEntry,'assword:',pexpect.EOF])
        if output==1:
            spawn.sendline(masterUserPassword)
            output=spawn.expect(['Permission denied, please try again.','(current) UNIX password','Your password has expired',pexpect.EOF])
            if output==0 or output==1 or output==2:
                spawn.close()
                return 1
        elif output==2:
            pass
        spawn.close()
    return 0

def setRemoteConnection(fqdn,user,password,hostName,keyFile,environment):
    '''
    Main function used to open the ssh connection  to the specified server
    '''
    # create the connection object
    logger.info("Creating ssh connection to " + str(fqdn))
    remoteConnection = None
    connectionError = setNewSSHKey(fqdn,user,keyFile)
    if ( connectionError == "No Connection" ):
        try:
            ret = setAuthorisedKeys("cloud",fqdn,user,password)
            if ret != 0:
                return 1, remoteConnection
        except Exception as e:
            logger.error("Could not generate a new ssh key for the cloud deployment")
            return 1, remoteConnection
        remoteConnection = createSshConnection(fqdn,user)
        if (remoteConnection == "1" or remoteConnection == None ):
            logger.error("Could not create ssh connection on " + str(fqdn))
            return 1, remoteConnection
    else:
        remoteConnection = createSshConnection(fqdn,user)
        if (remoteConnection == "1" or remoteConnection == None ):
            logger.error("Could not create ssh connection on " + str(fqdn))
            return 1, remoteConnection
    return 0, remoteConnection

def checkSSHConnection(fqdn, initial_wait=None, interval=None, retries=None):
    # Set default values
    if initial_wait == None:
        initial_wait=90
    if interval == None:
        interval=10
    if retries == None:
        retries=60
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    logger.info("Starting the check for ssh connection to " + str(fqdn) + " in " + str(initial_wait) + "  seconds")
    time.sleep(initial_wait)
    logger.info("Checking ssh connection to " + str(fqdn))
    count = 1
    for x in range(retries):
        logger.info("Try " + str(count) + " of " + str(retries))
        count += 1
        try:
            ssh.connect(fqdn, username=config.get('DMT_AUTODEPLOY', 'user'), key_filename=config.get('DMT_AUTODEPLOY', 'key'))
            logger.info("Success ssh connection established to : " + str(fqdn))
            logger.info("Waiting for applicaions to start. Waiting " + str(initial_wait) + " seconds")
            time.sleep(initial_wait)
            return 0
        except Exception as e:
            logger.info("Unable to established Connection to : " + str(fqdn) + ". Sleeping for " + str(interval) + " seconds before retry...")
            time.sleep(interval)
    return 1

def checkSSHConnectForPassword(fqdn, user, initial_wait=None, interval=None, retries=None, finishWait=None):
    # Set default values
    if initial_wait == None:
        initial_wait=90
    if interval == None:
        interval=10
    if retries == None:
        retries=60
    if finishWait == None:
        finishWait = initial_wait
    logger.info("Starting the check for ssh connection to " + str(fqdn) + " in " + str(initial_wait) + "  seconds")
    time.sleep(initial_wait)
    logger.info("Checking ssh connection to " + str(fqdn))
    count = 1
    logger.info("Running Command: \"ssh -o PasswordAuthentication=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no " + str(user) + "@" + str(fqdn) + " exit 0\"")
    for x in range(retries):
        logger.info("Try " + str(count) + " of " + str(retries))
        count += 1
        try:
            ret,out = commands.getstatusoutput("ssh -o PasswordAuthentication=no -o ConnectTimeout=10 -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no " + str(user) + "@" + str(fqdn) + " exit 0")
            if (ret == 0 or "Permission denied" in out):
                logger.info("Success ssh connection available for : " + str(fqdn))
                if finishWait != 0:
                    logger.info("Waiting for applicaions to start. Waiting " + str(finishWait) + " seconds")
                    time.sleep(finishWait)
                return 0
            else:
                logger.info("Unable to established an available connection through port 22 : " + str(fqdn) + ". Sleeping for " + str(interval) + " seconds before retry...")
                time.sleep(interval)
        except Exception as e:
            logger.info("Issue with with checking the ssh connection")
            return 1
    return 1

def cleanKnowHostFile(mgtServer):
    '''
    Function used to clean out the known host file
    '''
    logger.info("Cleaning Out Known Host file")
    if NetworkInterface.objects.filter(server=mgtServer.server_id, interface="eth0").exists():
        networkObject = NetworkInterface.objects.get(server=mgtServer.server_id, interface="eth0")
        if IpAddress.objects.filter(nic=networkObject.id,ipType="host").exists():
            ipAddressObj = IpAddress.objects.get(nic=networkObject.id,ipType="host")
            ipAddress = ipAddressObj.address
        else:
            logger.error("Could not get the server Ip or network address for management server " + str(mgtServer.server.hostname))
            return 1
    else:
        logger.error("Could not get the server MAC Address")
        return 1

    hostList = [mgtServer.server.hostname,mgtServer.server.hostname + "." + mgtServer.server.domain_name,ipAddress]
    userList = ["lciadm100","root"]

    try:
        for user in userList:
            if user == "root":
                knownHosts=config.get('DMT_AUTODEPLOY', 'rootKnownHosts')
                ret,output = commands.getstatusoutput("sudo " + knownHosts)
                if ("No such file or directory" in output and ret != 0):
                    continue
                sshCommand = "sudo ssh-keygen -R"
            else:
                knownHosts=config.get('DMT_AUTODEPLOY', 'lciadmKnownHosts')
                if not os.path.isfile(knownHosts):
                    continue
                sshCommand = "ssh-keygen -R"
            for item in hostList:
                ret,output = commands.getstatusoutput(sshCommand + " " + str(item))
                if ("No such file or directory" not in output):
                    if (ret != 0):
                        logger.error("Unable to clean out know host file for item " + str(item))
                        logger.error("Exemption:")
                        logger.error(output)
                        return 1
    except Exception as e:
        logger.info("Issue cleaning out the known host file, Exception: " +str(e))
        return 1
    return 0

def changePassword(child, current_password, new_password, cmd=None):
    expectList = ['[Nn]ew [Pp]assword', '[Rr]etype', pexpect.EOF]
    # Send the current password
    if cmd is not None:
        child.sendline(cmd)
    else:
        child.sendline(current_password)
    # Expect new password prompt
    i = child.expect(expectList)
    if i != 0:
        return 1
    # Send new password
    child.sendline(new_password)

    #Expect retype new password prompt
    i = child.expect(expectList)
    if i != 1:
        return 1
    # Send retype new password
    child.sendline(new_password)

    return 0

def loginToLMS(fqdnMgtServer,user,masterUserPassword,hostName):
    COMMAND_PROMPT = '[$#] '
    SSH_NEWKEY = r'Are you sure you want to continue connecting \(yes/no\)\?'
    complexPassword = config.get('DMT_AUTODEPLOY', 'peerNodeComplexPassword')

    child = pexpect.spawn('ssh -l %s %s'%(user, fqdnMgtServer))
    child.logfile = sys.stdout
    i = child.expect([pexpect.TIMEOUT, SSH_NEWKEY, '[Pp]assword: ', COMMAND_PROMPT])

    if i == 0: # Timeout
        logger.error('Pexpect timeout on login to LMS')
        return 1

    if i == 1: # SSH does not have the public key. Just accept it.
        child.sendline ('yes')
        child.expect ('[Pp]assword: ')
    child.sendline(masterUserPassword)

    i = child.expect(['Permission denied','.current.*password', 'Your password has expired', COMMAND_PROMPT, pexpect.EOF ])

    if i == 0 or i == 2:
        logger.error('Failed to login to LMS')
        return 1

    elif i == 1: # root enforced password change
        logger.info('Password reset enforced by root, changing to complex password')

        ret = changePassword(child, masterUserPassword, complexPassword)
        if ret != 0:
            logger.error('Failed to change password on LMS')
            return ret
        child.expect(COMMAND_PROMPT)

        logger.info('Password change back to simple password')
        ret = changePassword(child, complexPassword, masterUserPassword, 'passwd')
        if ret !=0:
            logger.error('Failed to change password on LMS')
            return ret
        child.expect(COMMAND_PROMPT)

    elif i==3:
        logger.info('Password reset was not enforced')
        pass

    return 0
