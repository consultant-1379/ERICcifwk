#!/bin/bash

#
# This sample script contains the commands used for a LITP installation applying
# to the landscape the boot manager part for the following configuration:
#
# Type: Single-Blade
#
# Can be run in two modes, Interactive and Non-interactive
#
# Interactive mode pauses the execution waiting for the user to hit a key to
# continue, in order to allow the user to check the status of the system before
# next step.
#
# Non-interactive is enabled by providing '-i' as an argument to this script.
# In this mode the script doesn't pause, suitable when ran by an application.
#
# For more details, please visit the documentation site here:
# https://team.ammeon.com/confluence/display/LITPExt/Landscape+Installation
#

INTERACTIVE=On
# Parsing arguments to check for non-interactive mode. Ignoring unspecified
# arguments
while getopts :i opt; do
    case $opt in
        i)
            INTERACTIVE=Off
            ;;
    esac
done

# Helper function for debugging purpose.
# ----------------------------------------
# Reduces the clutter on the script's output while saving everything in
# landscape log file in the user's current directory. Can safely be removed
# if not needed.

STEP=0
LOGDIR="logs"
if [ ! -d "$LOGDIR" ]; then
    mkdir $LOGDIR
fi
LOGFILE="${LOGDIR}/landscape_bootmgr.log"
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

        command litp "$@" 2>&1 | tee -a "$LOGFILE"
        if [ "${PIPESTATUS[0]}" -gt 0 ]; then
                exit 1;
        fi
}

# Function to show elapsed time in human readable format (minutes:seconds)
function time_elapsed() {
	secs=$1

	mins=$(( $secs / 60 ))
	secs=$(( $secs % 60 ))

	printf "Time elapsed: %02d:%02d\r" $mins $secs
}

# pause function to allow for user confirmation in interactive mode
function pause() {
    case $INTERACTIVE in
        [Yy]es|[Oo]n|[Tt]rue)
            read -s -n 1 -p "Press any key to continue or Ctrl-C to abort."
            echo
            ;;
    esac
}

#
# A function that checks if cobbler is ready with a profile and distro
# before starting to create systems
#
function wait_for_cobbler() {
	c=0 # attempt timer
	TEMPO=1 # interval between checks

	echo
	echo "Waiting for cobbler distro/profile to be loaded..."

	time_elapsed $(( $c * $TEMPO ))
	while sleep $TEMPO; do
		let c++
		time_elapsed $(( $c * $TEMPO ))

		output=$(cobbler distro list)
		if [[ -n "$output" ]]; then
			output=$(cobbler profile list)
			if [[ -n "$output" ]]; then
				break
			fi
		fi
	done
	echo
	echo "Cobbler is now ready with a distro & profile."
	#pause
}

# A function that checks if dhcp is ready for distro import
# before starting to import distro
#
function wait_for_dhcp() {
	c=0 # attempt timer
	TEMPO=1 # interval between checks

	echo
	echo "Waiting for dhcp to be configured..."

	time_elapsed $(( $c * $TEMPO ))
	while sleep $TEMPO; do
		let c++
		time_elapsed $(( $c * $TEMPO ))

                grep -Eq  "puppet-agent.*File.*dhcp.*content.*changed" /var/log/messages*
                if [ $? -eq 0 ]; then
                    break
                fi
	done
	echo
	echo "Cobbler is now ready for distro import."
	#pause
}

# --------------------------------------------
# BOOT MANAGER STARTS HERE
# --------------------------------------------

# -------------------------------------------------------------
# APPLY CONFIGURATION TO COBBLER & START (BOOT) NODES
# -------------------------------------------------------------

#
# Cobbler must have been configured before running the following commands
# check /var/log/messages for next puppet iteration, 'cobbler sync' should not
# fail after this
#

# Cobbler's management interface
litp /bootmgr update server_url="http://127.0.0.1/cobbler_api" username="testing" password="testing"

#wait_for_dhcp

# Adding a distribution and a profile to cobbler
litp /bootmgr/distro1 create boot-distro arch='x86_64' breed='redhat' path='/profiles/node-iso/' name='node-iso-x86_64'

#
# We must wait a few seconds for profile and distro to be imported to cobbler
#

wait_for_cobbler

# Add profile to landscape
litp /bootmgr/distro1/profile1 create boot-profile name='node-iso-x86_64' distro='node-iso-x86_64' kopts='' kopts_post='console=ttyS0,115200'

#
# Now that Cobbler has imported the distro, we can create systems
#
litp /bootmgr boot scope=/inventory

# --------------------------------------------
# BOOT MANAGER ENDS HERE
# --------------------------------------------


#
# A function that checks if cobbler is ready with a profile and distro
# before starting to create systems
#
function wait_for_vm_stared() {
	c=0 # attempt timer
	TEMPO=2 # interval between checks
    started=0 #1 means vm sc1, sc2 are started

    #get ip address of ms1 - eth1
    ms1_last_oct=$(ip addr show eth1 | grep 'scope global' | awk '{print $2}' | sed  -e 's/\/..$//' | sed -E 's/.+\.([^.]+)/\1/')
    oct_len=$(expr length "${ms1_last_oct}")
    if test "${oct_len}" -eq 1; then
        mac_sc1eth1="DE:AD:BE:EF:0${ms1_last_oct}:11"
        mac_sc1eth2="DE:AD:BE:EF:0${ms1_last_oct}:12"
        mac_sc2eth1="DE:AD:BE:EF:0${ms1_last_oct}:21"
        mac_sc2eth2="DE:AD:BE:EF:0${ms1_last_oct}:22"
    elif test ${oct_len} -eq 2; then
        mac_sc1eth1="DE:AD:BE:EF:${ms1_last_oct}:11"
        mac_sc1eth2="DE:AD:BE:EF:${ms1_last_oct}:12"
        mac_sc2eth1="DE:AD:BE:EF:${ms1_last_oct}:21"
        mac_sc2eth2="DE:AD:BE:EF:${ms1_last_oct}:22"
    elif test ${oct_len} -eq 3; then
        mac_sc1eth1="DE:AD:BE:E${ms1_last_oct:0:1}:${ms1_last_oct:1}:11"
        mac_sc1eth2="DE:AD:BE:E${ms1_last_oct:0:1}:${ms1_last_oct:1}:12"
        mac_sc2eth1="DE:AD:BE:E${ms1_last_oct:0:1}:${ms1_last_oct:1}:21"
        mac_sc2eth2="DE:AD:BE:E${ms1_last_oct:0:1}:${ms1_last_oct:1}:22"
    else
        echo "Something went wrong with obtaingin last octet of ms1 ip address"
        echo "Abborting script, please check system settings or set the value of the last octet of ms1 ip address manually"
        exit 1
    fi

	echo "Waiting for vm: sc1 sc2 to be started ..."

	time_elapsed $(( $c * $TEMPO ))
	while sleep $TEMPO; do
		let c++
		time_elapsed $(( $c * $TEMPO ))

        #network interfaces can be attached only to running interfaces
        virsh list | grep sc1 | grep running && virsh list | grep sc2 | grep running && let started++

        #there may be problems with booting vm with multiple interfaces, give vm abot a minute after they are running before adding interfaces
		if [[ ${started} == 30 ]]; then
            #find full names of virtual machines
            vmsc1=$(virsh list | grep sc1 | awk '{print $2}')
            vmsc2=$(virsh list | grep sc2 | awk '{print $2}')

            file=$(mktemp -t llt.XXXXX.xml)

            #define a bridge not connected to any physical interface
            echo '
            <network>
            <name>vcs_llt</name>
            <bridge name="llt0" />
            </network>' > ${file}

            #for network setup see http://wiki.libvirt.org/page/Networking#NAT_forwarding_.28aka_.22virtual_networks.22.29
            virsh net-define ${file}

            rm ${file}

            #mark network for autostart
            virsh net-autostart vcs_llt
            #start it
            virsh net-start vcs_llt

            virsh attach-interface ${vmsc1} bridge llt0 --mac ${mac_sc1eth1} --persistent
            virsh attach-interface ${vmsc1} bridge llt0 --mac ${mac_sc1eth2} --persistent
            virsh attach-interface ${vmsc2} bridge llt0 --mac ${mac_sc2eth1} --persistent
            virsh attach-interface ${vmsc2} bridge llt0 --mac ${mac_sc2eth2} --persistent

            break
		fi
	done

	echo
	echo "eth1 and eth2 interfaces added to vm sc1 an sc2"
}

function configure_ebtables {
    ebtables=`which ebtables`
    if [[ $? == 1 ]]; then
        echo "Could not find ebtables executable on the syste. Is the ebtables package installed?"
        echo "ebtable firewall will not be confiugred ..."
        echo "You can try to configure it manually after installing ebtables package. Install rules:"
        echo "
        ebtables -t filter -A INPUT -p IPv4 -i eth0 --pkttype-type ! multicast -j ACCEPT
        ebtables -t filter -A INPUT -p ARP -i eth0 -j ACCEPT
        ebtables -t filter -A INPUT -i eth0 -j DROP
        ebtables -t filter -A FORWARD -p IPv4 -i eth0 --pkttype-type ! multicast -j ACCEPT
        ebtables -t filter -A FORWARD -p ARP -i eth0 -j ACCEPT
        ebtables -t filter -A FORWARD -p IPv4 -o eth0 --pkttype-type ! multicast -j ACCEPT
        ebtables -t filter -A FORWARD -p ARP -o eth0 -j ACCEPT
        ebtables -t filter -A FORWARD -i eth0 -j DROP
        ebtables -t filter -A FORWARD -o eth0 -j DROP
        ebtables -t filter -A OUTPUT -p IPv4 -o eth0 --pkttype-type ! multicast -j ACCEPT
        ebtables -t filter -A OUTPUT -p ARP -o eth0 -j ACCEPT
        ebtables -t filter -A OUTPUT -o eth0 -j DROP"
        echo

        return 1
    fi

    echo
    echo "Flushing current ebtables rules ..."
    ebtables -F

    echo "Blocking all but unicast IP and arp traffic on the eth0 interface"
    ebtables -t filter -P INPUT ACCEPT
    ebtables -t filter -P OUTPUT ACCEPT
    ebtables -t filter -P FORWARD ACCEPT
    ebtables -t filter -A INPUT -p IPv4 -i eth0 --pkttype-type ! multicast -j ACCEPT
    ebtables -t filter -A INPUT -p ARP -i eth0 -j ACCEPT
    ebtables -t filter -A INPUT -i eth0 -j DROP
    ebtables -t filter -A FORWARD -p IPv4 -i eth0 --pkttype-type ! multicast -j ACCEPT
    ebtables -t filter -A FORWARD -p ARP -i eth0 -j ACCEPT
    ebtables -t filter -A FORWARD -p IPv4 -o eth0 --pkttype-type ! multicast -j ACCEPT
    ebtables -t filter -A FORWARD -p ARP -o eth0 -j ACCEPT
    ebtables -t filter -A FORWARD -i eth0 -j DROP
    ebtables -t filter -A FORWARD -o eth0 -j DROP
    ebtables -t filter -A OUTPUT -p IPv4 -o eth0 --pkttype-type ! multicast -j ACCEPT
    ebtables -t filter -A OUTPUT -p ARP -o eth0 -j ACCEPT
    ebtables -t filter -A OUTPUT -o eth0 -j DROP

    echo
    echo "Making the rules permament between node reboots:"
    /etc/init.d/ebtables save
    echo
}

#configure ebtable firewall rules
configure_ebtables

#attach additional interfaces to the vm-s
wait_for_vm_stared

exit 0
