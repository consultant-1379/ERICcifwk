# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distrubuted in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

"""
Sample script showing how to do local port forwarding over paramiko.

This script connects to the requested SSH server and sets up local port
forwarding (the openssh -L option) from a local port through a tunneled
connection to a destination reachable from the SSH server machine.
"""
import os, socket, select, SocketServer, sys, paramiko, logging
logger = logging.getLogger(__name__)

SSH_PORT = 22

verbose = True

class ForwardServer (SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
    logger.info("Server Fowarded extending SocketServer.ThreadingTCPServer parmiko class") 
    

class Handler (SocketServer.BaseRequestHandler):

    def handle(self):
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip',
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
            logger.info("Incoming request %s:%d was a Success" % (self.chain_host,self.chain_port))
        except Exception, e:
            logger.error('Incoming request to %s:%d failed: %s' % (self.chain_host,
                                                              self.chain_port,
                                                              repr(e)))
            return False
        if chan is None:
            logger.error('Incoming request to %s:%d was rejected by the SSH server.' %
                    (self.chain_host, self.chain_port))
            return False

        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        try:
            chan.close()
            logger.info("Incoming Request Channel closed with Success")
        except Exception as e:
            logger.error("There was a problem closing the incoming request channel, Error Thrown: " 
                    + str(e))
            return False
        try:
            self.request.close()
            logger.info('Tunnel closed from %r' % (self.request.getpeername(),))
        except Exception as e:
            logger.error("There was an issue closing the SSH Tunnel, Error Thrown: "
                    + str(e))
            return False


def forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object.  (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHander (Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport
    try:
        ForwardServer(('', local_port), SubHander).serve_forever()
        logger.info("Handler set up with Success")
    except Exception as e:
        logger.error("Unable to set up Handler and Error thrown" +str(e))
        raise CommandError("Unable to set up Handler") 
        return False


def verbose(s):
    if g_verbose:
        logger.info(s)


HELP = """\
Set up a forward tunnel across an SSH server, using paramiko. A local port
(given with -p) is forwarded across an SSH session to an address:port from
the SSH server. This is similar to the openssh -L option.
"""


def get_host_port(spec, default_port):
    try:
        "parse 'hostname:22' into a host and port, with the port optional"
        args = (spec.split(':', 1) + [default_port])[:2]
        args[1] = int(args[1])
        logger.info("Parsed hostname:port into a host and port, with the port optional")
        return args[0], args[1]
    except Exception as e:
        logger.error("Unable to parse hostname:port into a host and port, with the port optional")
        return False
def main(verboses, port, user, keyfile, look_for_keys, password, remote, local):
    global g_verbose
    g_verbose = verboses

    server_host, server_port = get_host_port(local, SSH_PORT)
    remote_host, remote_port = get_host_port(remote, SSH_PORT)
    server, remote = (server_host, server_port), (remote_host, remote_port)
    
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    logger.info('Connecting to ssh host %s:%d ...' % (server[0], server[1]))
    try:
        client.connect(server[0], server[1], username=user, key_filename=keyfile,
                       look_for_keys=look_for_keys, password=password)
        logger.info('Connected to %s:%d: ...' % (server[0], server[1]))
    except Exception, e:
        logger.error('Failed to connect to %s:%d: %r' % (server[0], server[1], e))
        return False

    logger.info('Now forwarding port %d to %s:%d ...' % (port, remote[0], remote[1]))

    try:
        forward_tunnel(port, remote[0], remote[1], client.get_transport())
        logger.info('Forwarding port %d to %s:%d ...' % (port, remote[0], remote[1]))
    except KeyboardInterrupt:
        logger.error('C-c: Port forwarding stopped.')
        return False


if __name__ == '__main__':
    main()
