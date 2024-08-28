#!/bin/bash

CIFWK_URL=$1

rm -f /home/lciadm100/.m2/settings.xml
rm -f /home/lciadm100/.m2/settings-security.xml
rm -f /home/ossrcdm/.m2/settings-security.xml

curl -L -f --insecure $CIFWK_URL/static/setupvapp/maven_settings/lciadm100/settings.xml -o /home/lciadm100/.m2/settings.xml
curl -L -f --insecure $CIFWK_URL/static/setupvapp/maven_settings/lciadm100/settings-security.xml -o /home/lciadm100/.m2/settings-security.xml
curl -L -f --insecure $CIFWK_URL/static/setupvapp/maven_settings/ossrcdm/settings.xml -o /home/ossrcdm/.m2/settings.xml

chown lciadm100:lciadm100 /home/lciadm100/.m2/settings.xml
chown lciadm100:lciadm100 /home/lciadm100/.m2/settings-security.xml
chown ossrcdm:ossrcdm /home/ossrcdm/.m2/settings.xml

# Set the Local Config file on the VAPP Gateway
rm -f /home/lciadm100/.cifwk/config

curl -L -f --insecure $CIFWK_URL/static/setupvapp/config/lciadm100/config -o /home/lciadm100/.cifwk/config

chown lciadm100:lciadm100 /home/lciadm100/.cifwk/config

# Disable StrictHostKeyChecking in ~/.ssh/config
users="lciadm100 ossrcdm"
for u in ${users}; do
    if [ -e /home/${u}/.ssh/known_hosts ]; then
        grep -q StrictHostKeyChecking /home/${u}/.ssh/config 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "Host *" >>/home/${u}/.ssh/config
            echo "   StrictHostKeyChecking no" >>/home/${u}/.ssh/config
            echo "   UserKnownHostsFile=/dev/null" >>/home/${u}/.ssh/config
        fi
        chown ${u}:${u} /home/${u}/.ssh/config
    fi
done

if [ -e /root/.ssh/known_hosts ]; then
    grep -q StrictHostKeyChecking /root/.ssh/config 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "Host *" >>/root/.ssh/config
        echo "   StrictHostKeyChecking no" >>/root/.ssh/config
        echo "   UserKnownHostsFile=/dev/null" >>/root/.ssh/config
    fi
    chown root:root /root/.ssh/config
fi

# Update the ipsec configuration to keep vpn connections alive longer
curl -L -f --insecure $CIFWK_URL/static/setupvapp/gateway_settings/ipsec.conf -o /usr/local/etc/ipsec.conf
/usr/local/sbin/ipsec reload

# Avoid ssh host verification for all users
if [ ! $(grep "UserKnownHostsFile=/dev/null"  /etc/ssh/ssh_config) ]; then
    echo ""
    echo "# Avoid ssh host verification for all users" >>/etc/ssh/ssh_config
    echo "Host *" >>/etc/ssh/ssh_config
    echo "   StrictHostKeyChecking no" >>/etc/ssh/ssh_config
    echo "   UserKnownHostsFile=/dev/null" >>/etc/ssh/ssh_config
fi
