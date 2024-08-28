<INCLUDE NODE: MS >
#!/bin/bash

# 
# Helper function for debugging purpose. 
# ----------------------------------------
# Reduces the clutter on the script's output while saving everything in 
# landscape.log file in the user's current directory. Can safely be removed 
# if not needed.

STEP=0
LOGDIR="logs"
if [ ! -d "$LOGDIR" ]; then
    mkdir $LOGDIR
fi
LOGFILE="${LOGDIR}/landscape_inventory.log"
if [ -f "${LOGFILE}" ]; then
    mod_date=$(date +%Y%m%d_%H%M%S -r "$LOGFILE")
    NEWLOG="${LOGFILE%.log}-${mod_date}.log"

    if [ -f "${NEWLOG}" ]; then  # in case ntp has reset time and log exists
        NEWLOG="${LOGFILE%.log}-${mod_date}_1.log"
    fi
    cp "$LOGFILE" "${NEWLOG}"
fi

> "$LOGFILE"
function litp() {
        STEP=$(( ${STEP} + 1 ))
        printf "Step %03d: litp %s\n" $STEP "$*" | tee -a "$LOGFILE"
        
        result=$(command litp "$@" | tee -a "$LOGFILE")
        if echo "$result" | grep -i error; then
                exit 1;
        fi
}

# --------------------------------------------
# INVENTORY STARTS HERE
# --------------------------------------------

# Enable the MS1 IP address and blade (SND applicable)
litp /inventory/site1/network/<NODE_IP_UNSCORE>/ enable
litp /inventory/site1/systems/blade enable

# Enable the VM IP and TIPC pools (SND applicable)
<Append Here File: tipcrange-address-all>

# Run materialise to create a .shell. for inventory placeholders:
litp /definition/ materialise

# ---------------------------------------------
# UPDATE NFS SERVER DETAILS
# ---------------------------------------------

# "SFS" driver is used for NAS storage device and "RHEL" for when an extra RHEL
# Linux node is used.
# password is only needed if ssh keys have not been setup up ( ie in case of SFS )
litp /inventory/site1/ms1/ms_node/sfs/export1 update driver="RHEL" user="root" password="cobbler" server="NFS-1" path="/exports/cluster"

# ---------------------------------------------
# ADD THE PHYSICAL SERVERS
# ---------------------------------------------

litp /inventory/site1/systems/blade update bridge_enabled=True

# ---------------------------------------------
# ADD THE VIRTUAL NODES
# ---------------------------------------------
litp /inventory/site1/systems/vm_pool update path='/var/lib/libvirt/images'

# ---------------------------------------------
# ADD YUM REPOSITORIES  
# ---------------------------------------------

#
# YUM repositories reside on the Management Server, with hostname MS1
#

# Update the user's passwords
# The user's passwords must be encrypted, the encryption method is Python's 2.6.6
# crypt function. The following is an example for encrypting the phrase 'passw0rd'
#
# [cmd_prompt]$ python
# Python 2.6.6 (r266:84292, May 20 2011, 16:42:11) 
# [GCC 4.4.5 20110214 (Red Hat 4.4.5-6)] on linux2
# Type "help", "copyright", "credits" or "license" for more information.
# >>> import crypt
# >>> crypt.crypt("passw0rd")
# '$6$VbIEnv1XppQpNHel$/ikRQIa5i/cNJR2BYucNkTjHmO/HBzHdvDbsXa7fprXILrGYa.xMOPI9b.y5HrfqWHfVyfXK7AffI9DrkUBWJ.'
#
# Symbol '$' is a shell metacharacter and needs to be "escaped" with '\\\'
#
litp /inventory/site1/ms1/ms_node/users/litp_admin update password=\\\$6\\\$VbIEnv1XppQpNHel\\\$/ikRQIa5i/cNJR2BYucNkTjHmO/HBzHdvDbsXa7fprXILrGYa.xMOPI9b.y5HrfqWHfVyfXK7AffI9DrkUBWJ.
litp /inventory/site1/ms1/ms_node/users/litp_user update password=\\\$6\\\$VbIEnv1XppQpNHel\\\$/ikRQIa5i/cNJR2BYucNkTjHmO/HBzHdvDbsXa7fprXILrGYa.xMOPI9b.y5HrfqWHfVyfXK7AffI9DrkUBWJ.
<Append Here File: password-encryp-all>

# ---------------------------------------------
# CONFIGURE & ALLOCATE THE RESOURCES
# ---------------------------------------------

#
# Set MySQL Password
#
litp /inventory/site1/ms1/ms_node/mysqlserver/config update password="ammeon101"

#
# Set Hyperic username and password for the GUI
#
litp /inventory/site1/ms1/ms_node/hypericserver/hyserver update username="hqadmin" password="ammeon101"

# MS to allocate first.
litp /inventory/site1/ms1 allocate

<Append Here File: range-address-all>

# "secure" the blade hw for this node.
litp /inventory/site1 allocate

# ------------------------------------------------------------
# SET THIS PROPERTY FOR ALL SYSTEMS NOT TO BE ADDED TO COBBLER
# ------------------------------------------------------------
litp /inventory/site1/ms1 update add_to_cobbler="False"

# Updating hostnames of the systems.
<Append Here File: update-hostname-all>

# Allocate some more h/w resources for VMs, by modifying default values.
# RAM size in Megabytes, disk size in Gigabytes
<Append Here File: hardware-resources-all>

# Update kiskstart information. Convention for kickstart filenames is node's 
# hostname with a "ks" extension
<Append Here File: kickstart-info-all>

# Update the verify user to root. Workaround, user litp_verify doesn't exist yet
# Issue LITP-XXX (or User Story?)
litp /inventory/site1/ms1 update verify_user="root"
<Append Here File: verify-user-all>

# Allocate the complete site
litp /inventory/site1 allocate

# --------------------------------------
# APPLY CONFIGURATION TO PUPPET
# --------------------------------------

# This is an intermediate step before applying the configuration to puppet
litp /inventory/site1 configure


# --------------------------------------
# VALIDATE INVENTORY CONFIGURATION
# --------------------------------------

litp /inventory validate

# --------------------------------------
# APPLY CONFIGURATION TO PUPPET
# --------------------------------------

# Configuration's Manager (Puppet) manifests for the inventory will be created
# after this
litp /cfgmgr apply scope=/inventory

# (check for puppet errors -> "grep puppet /var/log/messages")
# (use "service puppet restart" to force configuration now)

# --------------------------------------------
# INVENTORY ENDS HERE
# --------------------------------------------

echo "Inventory addition has completed"
echo "Please wait for puppet to configure cobbler. This should take about 3 minutes"

exit 0
