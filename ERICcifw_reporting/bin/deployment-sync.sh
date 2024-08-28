#!/bin/bash -a

# Find my current dir
BASEDIR=$(/usr/bin/dirname $0)
# NOTE: This behaviour relies on shell builtins for cd and pwd
BASEDIR=$(cd ${BASEDIR}/.. ; pwd)
[ -f ${BASEDIR}/etc/global.env ] && . ${BASEDIR}/etc/global.env

#Runs Rsync if cifwk version on live site doesn't match local version
#Override check by adding option 'nocheck'

GET_VER_REST="https://ci-portal.seli.wh.rnd.internal.ericsson.com/getver/"
CHECKDIR="/proj/lciadm100/cifwk/latest"
HOST=$(hostname)
NOCHECK=$1

checkIfSyncNeeded() {
    FWK_CURRENT_VERSION=$($_WGET -q -O - --no-check-certificate ${GET_VER_REST})
    LOCAL_INSTALLED_VERSION=$($_READLINK ${CHECKDIR})
    if [ -z  ${FWK_CURRENT_VERSION}  ] ; then
        SYNCNEEDED="ERROR"
    elif [ ${FWK_CURRENT_VERSION} == ${LOCAL_INSTALLED_VERSION} ] ; then
        SYNCNEEDED="NO"
    else
        SYNCNEEDED="YES"
    fi
}

runRsync() {
    RUNSYNC="Successful"
    SYNCDIRS="tools/java tools/apache-maven-3.0.4 tools/django tools/django-auth-ldap tools/jdk1.6.0_31 cifwk"
    GITSYNCDIRS="tools/git tools/jdk tools/python"

    $_RSYNC -auvz seliius01817.seli.gic.ericsson.se:/proj/lciadm100/cifwk/${FWK_CURRENT_VERSION}/ /proj/lciadm100/cifwk/${FWK_CURRENT_VERSION}/
    if [ $? -ne 0 ] ; then
        RUNSYNC="ERROR"
    fi


    for dir in ${SYNCDIRS} ; do
        $_RSYNC -auvz seliius01817.seli.gic.ericsson.se:/proj/lciadm100/$dir/ /proj/lciadm100/$dir/
        if [ $? -ne 0 ] ; then
            RUNSYNC="ERROR"
        fi
    done

    for dir in ${GITSYNCDIRS} ; do
        $_RSYNC -auvz seliius01817.seli.gic.ericsson.se:/proj/gitadm100/$dir/ /proj/gitadm100/$dir/
        if [ $? -ne 0 ] ; then
            RUNSYNC="ERROR"
        fi
    done
    NEW_LOCAL_INSTALLED_VERSION=$(readlink ${CHECKDIR})
}


sendMail() {
    $_MAILX -S smtp=$SMTP_SERVER -s "Deployment Slave Sync ${HOST} ${RESULT}" -r "CI-Framework@ericsson.com" -v ${DMT_EMAILS[@]}<<EOF

Deployment Slave Sync run on ${HOST}

RSYNC result: ${RUNSYNC}
CIFWK portal version: ${FWK_CURRENT_VERSION}
Previous local version: ${LOCAL_INSTALLED_VERSION}
New local version: ${NEW_LOCAL_INSTALLED_VERSION}


EOF
}

#exit if another instance of script is running
if [ $($_PIDOF -x deployment-sync.sh| $_WC -w) -gt 2 ]; then
    exit
fi

checkIfSyncNeeded
if [[ ${SYNCNEEDED} == "YES" || ${NOCHECK} == "nocheck" ]]; then
    runRsync
fi

if [[ ${SYNCNEEDED} == "ERROR" || ${RUNSYNC} == "ERROR" ]]; then
    RESULT="ERROR"
else
    RESULT=""
fi

if [[ ${SYNCNEEDED} == "NO" && ${NOCHECK} != "nocheck" ]]; then
    SEND="NOT NEEDED"
else
    sendMail
fi

