#!/bin/bash

#crontab backup script for rabbitmq backup
#python needed for rabbitmqadmin command to run

# Find my current dir
BASEDIR=$(/usr/bin/dirname $0)
# NOTE: This behaviour relies on shell builtins for cd and pwd
BASEDIR=$(cd ${BASEDIR}/.. ; pwd)
echo $BASEDIR
if [ -f ${BASEDIR}/etc/global.env ]; then
        . ${BASEDIR}/etc/global.env
else
    _ECHO=/bin/echo
    _WGET=/usr/bin/wget
    _DATE=/bin/date
    _PYTHON=/usr/bin/python
    _RM=/bin/rm
   _AWK=/bin/awk
   _LS=/bin/ls
fi

if [ ! -f "$HOME/rabbitmqadmin" ]; then
    $_ECHO "rabbitmqadmin file not found in home directory"
    $_ECHO "getting file from rabbitmq server on localhost"
    $_WGET http://localhost:15672/cli/rabbitmqadmin -P "$HOME"
fi


if [ -d "$1" ]
then
    $_ECHO "Backup Directory exists."
else
    $_ECHO "Error: Backup Directory $1 does not exists."
    $_ECHO "please create $1 directory."
    exit 1
fi

#create rabbitmq json backup file
$_PYTHON "$HOME"/rabbitmqadmin export $1/rabbit.config-$($_DATE "+%Y-%m-%d_%H:%M:%s")
#list all but last 7 configs
TF=$($_LS -t $1/rabbit* | $_AWK 'NR>7'-F)
#remove all but the last seven version of the json file
$_RM -f ${TF}
exit 0
