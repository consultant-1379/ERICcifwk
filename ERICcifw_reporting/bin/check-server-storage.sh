#!/bin/bash
# Find my current dir
BASEDIR=$(/usr/bin/dirname $0)
# NOTE: This behaviour relies on shell builtins for cd and pwd
BASEDIR=$(cd ${BASEDIR}/.. ; pwd)
[ -f ${BASEDIR}/etc/global.env ] && . ${BASEDIR}/etc/global.env

sendMail() {
    $_MAILX -S smtp=$SMTP_SERVER -s "CIFWK Server Disc Usage Warning" -r "CI-Framework@ericsson.com" -v ${DMT_EMAILS[@]}<<EOF
Warning:
Disc usage is $discUsage% on the host $(hostname).

Mount location: $mountPoint

Please remove unnecessary files.
EOF
}
discInfo=$(df -h /  | grep -vE '^Filesystem|tmpfs|cdrom')
mountPoint=$(echo $discInfo | awk '{ print $1 }')
discUsage=$(echo $discInfo | awk '{ print substr($5, 1, length($5)-1) }')
[[ $discUsage -gt 80 ]] && sendMail
