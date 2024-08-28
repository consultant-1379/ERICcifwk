#!/bin/bash

#
# This sample script for removing/cleaning up a configuration from previous
# attemps.
#
# For more details, please visit the documentation site here:
# https://team.ammeon.com/confluence/display/LITPExt/Landscape+Installation


#
# Clean up cobbler
#
for sysname in $(cobbler system list); do
	cobbler system remove --name "$sysname"
done

for distroname in $(cobbler distro list); do
	cobbler distro remove --name "$distroname"
done

#
# Stop all necessary services
#

service cobblerd stop
service dhcpd stop
service puppetmaster stop
service puppet stop
service landscaped stop

# Kill landscape if service didn't stop gracefully.
killall landscape_service.py

#
# Remove current puppet certificate for MS1. New ones will be created in the
# next attempt
#

puppetca --clean ms1

#
# Clean up all files created by last attempt
#
rm -rf /var/lib/puppet/ssl/*
rm -f /root/.ssh/known_hosts
rm -rf /var/puppet/inventory/*
rm -rf /opt/ericsson/nms/litp/etc/puppet/manifests/inventory/*
rm -rf /var/NASService/locks/*
rm -rf /exports/cluster/*

# Clean up. Remove any stored landscape config ...
rm -rf /var/lib/landscape/*

# SB only
rm -rf /var/lib/libvirt/qemu/save/*
rm -rf /etc/libvirt/qemu/*.xml
rm -rf /var/lib/libvirt/images/*

# Remove VMs if any
for vmname in $(virsh list --all 2>/dev/null | awk 'NR>2 && $2 ~ ".+" {print $2}'); do
	echo removing vm "$vmname"
	virsh destroy "$vmname"
	virsh undefine "$vmname"
done

for vmname in `virsh net-list --all | grep -v '^Name' | grep -v '^-------' |gawk '{print $1}'`; do
    virsh net-destroy $vmname
	virsh net-undefine "$vmname"
done
#
# Bring back up all stopped services
#

service landscaped start
service puppet start
service puppetmaster start
service dhcpd start
service cobblerd start

# Restart network
service network restart

# Sync cobbler
cobbler sync

# That should be it

exit 0
