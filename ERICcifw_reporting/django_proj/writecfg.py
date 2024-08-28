import ConfigParser
import os.path

config = ConfigParser.RawConfigParser()

# When adding sections or items, add them in the reverse order of
# how you want them to be displayed in the actual file.
# In addition, please note that using RawConfigParser's and the raw
# mode of ConfigParser's respective set functions, you can assign
# non-string values to keys internally, but will receive an error
# when attempting to write to a file or when you get it in non-raw
# mode. SafeConfigParser does not allow such assignments to take place.
config.add_section('LDAP')
config.set('LDAP', 'server_url', 'ldap://ecd.ericsson.se')
config.set('LDAP', 'bind_dn', 'uid=YOUR_SIGNUM,ou=Users,ou=Internal,o=ericsson')
config.set('LDAP', 'password', 'YOUR_PASSWORD')
config.set('LDAP', 'search_base', 'ou=Users,ou=Internal,o=ericsson')

config.add_section('DMT')
config.set('DMT', 'vcloud_host', 'your.vcloud.host')
config.set('DMT', 'vcloud_user', 'user@organisation')
config.set('DMT', 'vcloud_pass', 'yourpass')

# Writing our configuration file to 'example.cfg'
with open('../etc/cifwk.cfg', 'wb') as configfile:
    config.write(configfile)
