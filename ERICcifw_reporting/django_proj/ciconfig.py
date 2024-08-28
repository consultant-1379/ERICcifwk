from ConfigParser import ConfigParser
import os
import pwd

import logging
logger = logging.getLogger(__name__)

class CIConfig(ConfigParser):
    """
    Generic configuration for CI Reporting. Heirarchy is the local file in ../etc/cifwk.cfg, overridden by
    values in the user's home directory: ~/.cifwk/config
    """
    base_config = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'etc/cifwk.cfg').replace('\\','/')
    home_dir = pwd.getpwuid( os.getuid() ).pw_dir
    user_config = str(home_dir) + "/.cifwk/config"
    def __init__(self):
        ConfigParser.__init__(self)
        self.read(self.base_config)
        logger.debug("Checking " + self.user_config)
        if (os.path.exists(self.user_config)):
            logger.debug("Reading " + self.user_config)
            self.read(self.user_config)



    @staticmethod
    def generateDefaultConfig(outfile):
        config = CIConfig()

        config.add_section('CIFWK') 
        config.set('CIFWK', 'email_host', 'mailhost')
       

        config.add_section('LDAP')
        config.set('LDAP', 'server_url', 'ldap://ecd.ericsson.se')
        config.set('LDAP', 'bind_dn', 'uid=YOUR_SIGNUM_HERE,ou=Users,ou=Internal,o=ericsson')
        config.set('LDAP', 'password', 'NO_PASS')
        config.set('LDAP', 'search_base', 'ou=Users,ou=Internal,o=ericsson')

        config.add_section('DMT')
        config.set('DMT', 'vcloud_user', 'clouduser@organisation')
        config.set('DMT', 'vcloud_pass', 'NO_PASS')
        config.set('DMT', 'vcloud_host', 'atvcd1.athtem.eei.ericsson.se')

        with open(outfile, 'wb') as configfile:
            config.write(configfile)

