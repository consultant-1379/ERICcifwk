#!/bin/bash
#set -xv

username=eatools
password=T0000ls!@2023T0000ls!@2023
mb_url=https://mb1s11-eiffel004.eiffel.gic.ericsson.se:8443
script=$0
server=`hostname`

queues=(eiffel004.ext.eatools.DE-AXIS-CIPortal)

error_found=false
output=""
limit=10
unack_limit=5

for queue in ${queues[*]}
    do
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
    done

if [[ ${error_found} == "true" ]]; then
    output=${output}\\nscript:${script}
    output=${output}\\nserver:${server}
    echo $queue_len
fi
