#!/bin/bash
#set -xv

# Find my current dir
BASEDIR=$(/usr/bin/dirname $0)
# NOTE: This behaviour relies on shell builtins for cd and pwd
BASEDIR=$(cd ${BASEDIR}/.. ; pwd)
[ -f ${BASEDIR}/etc/global.env ] && . ${BASEDIR}/etc/global.env

mail_list="arun.jose@ericsson.com,catherine.egan@ericsson.com,nayana.ponnasamudra.boraiah@ericsson.com,richard.da.silva@ericsson.com,xiangkai.tang@ericsson.com,jithin.raju@ericsson.com,william.wren@ericsson.com"
username=eatools
password=T0000ls!@2023T0000ls!@2023
mb_url=https://mb1s11-eiffel004.eiffel.gic.ericsson.se:8443
script=$0
server=`hostname`
queue=(eiffel004.ext.eatools.DE-AXIS-CIPortal)

error_found=false
output=""
limit=10
unack_limit=5

queue_len=$(curl -k -s -i -u ${username}:${password} ${mb_url}/api/queues/%2f/${queue} |grep -Po '"messages_ready":.*?[^\\],' |  sed 's/messages_ready//g;s/://g;s/"//g;s/,//g')
unack_len=$(curl -k -s -i -u ${username}:${password} ${mb_url}/api/queues/%2f/${queue} |grep -Po '"messages_unacknowledged":.*?[^\\],' |  sed 's/messages_unacknowledged//g;s/://g;s/"//g;s/,//g')

if [[ ${queue_len} == "" ]]; then
    error_found=true
        output=${output}\\n${queue}"__READY____NO LENGTH"
elif [ "${queue_len}" -gt "${limit}" ]; then
    error_found=true
    output=${output}\\n${queue}__READY____${queue_len}
else
    output=${output}\\n${queue}__READY____${queue_len}
fi
if [[ ${unack_len} == "" ]]; then
    error_found=true
        output=${output}\\n${queue}"__UNACKED____NO LENGTH"
elif [ "${unack_len}" -gt "${unack_limit}" ]; then
    error_found=true
    output=${output}\\n${queue}__UNACKED____${unack_len}
else
    output=${output}\\n${queue}__UNACKED____${unack_len}
fi

if [[ ${error_found} == "true" ]]; then
    output=${output}\\nscript:${script}
    output=${output}\\nserver:${server}
    /bin/echo -e ${output} | mailx -r "CI-Framework@ericsson.com" -S smtp=$SMTP_SERVER -s "CI Portal: Message bus queue E2C exceeding limit" $mail_list
fi

