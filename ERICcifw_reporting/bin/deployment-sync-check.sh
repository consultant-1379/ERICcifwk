#!/bin/bash -a

BASEDIR=$(/usr/bin/dirname $0)
# NOTE: This behaviour relies on shell builtins for cd and pwd
BASEDIR=$(cd ${BASEDIR}/.. ; pwd)
[ -f ${BASEDIR}/etc/global.env ] && . ${BASEDIR}/etc/global.env

sendMail() {
    $_MAILX -S smtp=$SMTP_SERVER -s "Deployment Slave Sync terminated" -r "CI-Framework@ericsson.com" ${DMT_EMAILS[@]}<<EOF

Deployment Slave Sync has been terminated as it was running for over 3 hours.
Please re run

EOF
}

# Exit if deployment sync script has been running for a long time
PID=$($_PIDOF -x deployment-sync.sh)
if [ ${PID} ]; then
    TIMELAPSED=$($_PS -p ${PID} -o etime= | $_SED -e 's/://g' -e 's/^[ \t]*//' -e 's/^0*//')
    echo ${TIMELAPSED}
    if [ ${TIMELAPSED} -gt 30000 ]; then
        $_KILL ${PID}
        sendMail
    fi
fi
