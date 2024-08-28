from dmt.utils import handlingError
from ciconfig import CIConfig

import pexpect
import subprocess, os, sys, time, getpass
import logging


logger = logging.getLogger(__name__)
config = CIConfig()


class RemoteCmd:
    ssh = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ServerAliveInterval=30 "
    tty_ssh = "ssh -q -t -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ServerAliveInterval=30 "
    child = None

    def __init__(self, user, hostname):
        self.ssh = self.ssh + user + "@" + hostname
        self.tty_ssh = self.tty_ssh + user + "@" + hostname

    def runCmdGetOutput(self, cmd, type=None, timeout=600):
        sshType = self.ssh
        if type:
            sshType = self.tty_ssh
        logger.info("Running command " + sshType + " " + cmd + ", with a " + str(timeout) + " seconds timeout")
        (command_output, exitstatus) = pexpect.run(sshType + " " + cmd, timeout=timeout, withexitstatus=1)
        filtered_output = command_output.replace("This computer system is for authorized use only.", "")

        time.sleep(2)
        return exitstatus, filtered_output

    def runScriptGetOutput(self, tempScript, timeout=600):
        logger.info("Running command " + self.ssh + " 'bash -s' < " + tempScript)
        (command_output, exitstatus) = pexpect.run(self.ssh + " 'bash -s' < " + tempScript, timeout=timeout, withexitstatus=1)
        time.sleep(2)
        return exitstatus, command_output

    def runCmd(self, cmd, timeout=600):
        logger.info("Running command " + self.ssh + " " + cmd)
        (command_output, exitstatus) = pexpect.run(self.ssh + " " + cmd, timeout=timeout, withexitstatus=1)
        time.sleep(2)
        return exitstatus

    def runCmdTty(self, cmd, timeout=600):
        logger.info("Running command " + self.tty_ssh + " " + cmd)
        (command_output, exitstatus) = pexpect.run(self.tty_ssh + " " + cmd, timeout=timeout, withexitstatus=1)
        time.sleep(2)
        return exitstatus

    def spawnMSChild(self):
        """
        This function spawn and creates ssh connection to MS then returns child
        """
        try:
            child = pexpect.spawn(self.ssh)
            logger.info("Running command " + self.ssh)
            child.delaybeforesend = 0.3
            return child, 0
        except Exception as e:
            return "ERROR: Timeout issue during ssh to MS.", 1

    def expectChild(self, child, expect_in, ssh_newkey_message = None, user = None, host = None, password = None, timeout = 30):
        """
        This function send commands and expect for output in given child.
        """
        try:
            expect_in.append(pexpect.TIMEOUT)
            child.timeout = timeout
            if ssh_newkey_message != None:
                ssh_to_unknown_host_cmd = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -l " + str(user) + " " + str(host)
                self.expectChildSendCmd(child, ssh_to_unknown_host_cmd)
                expect_out = child.expect(expect_in)
                if expect_out == expect_in.index(expect_in[-1]):
                    return "ERROR: Timeout exception.", 1
                if expect_out == expect_in.index(expect_in[1]):
                    self.expectChildSendCmd(child, 'yes')
                    expect_out = child.expect(expect_in)
                    if expect_out == expect_in.index(expect_in[0]):
                        self.expectChildSendCmd(child, password)
                        return "SUCCESS", 0
                else:
                    self.expectChildSendCmd(child, password)
                return "SUCCESS", 0
            else:
                expect_out = child.expect(expect_in)
                if expect_out == expect_in.index(expect_in[-1]):
                    return "ERROR: Timeout exception.", 1
                return "SUCCESS", 0
        except pexpect.TIMEOUT:
            return errorMsg, 1
        except pexpect.EOF:
            return "End of file exception", 1

    def expectChildSendCmd(self, child, cmd):
        try:
            logger.info("Running command " + self.ssh + " " + cmd)
            child.sendline(cmd)
            return child, 0
        except Exception as e:
            logger.info(e.message)
            return 'Error message', 1

    def runChild(self, cmd, success, failure, type=None, timeout=600):
        if type:
            sshType = self.tty_ssh
        else:
            sshType = self.ssh
        logger.info("Running command " + sshType + " " + cmd)
        child = pexpect.spawn(sshType + " " + cmd)
        child.logfile = sys.stdout
        index = child.expect([success, failure, pexpect.EOF], 6000000)
        # index is the index of the patterns passed that matched. We can use this as
        # a return code with the side-effect of success matching 0
        child.close()
        logger.info("Got a return value " + str(index))
        return index

    def runCmdSimple(self, cmd, type=None, timeout=None):
        """
        This function allows running of a remote command, and just expects the command to complete itself or timeout
        It doesn't expect any particular strings to be seen, just looks for EOF or TIMEOUT
        """
        sshType = self.ssh
        if type:
            sshType = self.tty_ssh

        logMsg = "Running command " + sshType + " " + cmd
        if timeout:
            logMsg = "Running command " + sshType + " " + cmd + ", with a " + str(timeout) + " seconds timeout"

        logger.info(logMsg)

        # Kick off the command given
        child = pexpect.spawn(sshType + " " + cmd)

        # Make sure the comamnds output appears on standard out as it runs
        child.logfile = sys.stdout

        # Expect either the command to complete itself (EOF) or for it to hit the timeout value
        index = child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout)
        child.close()

        # Index of 0 would mean it completed normally, 1 would mean it must have timed out
        if index == 0:
            logger.info("Command completed with a return value " + str(child.exitstatus))
        elif index == 1:
            logger.error("Command timed out after " + str(timeout) + " seconds, sending return value " + str(child.exitstatus))

        # Return the return code of the command. If it timed out the return code would be 255
        return child.exitstatus

    def close(self):
        return 0

