#!/bin/bash

BD=$(dirname $0)

#I=1
#while [ ${I} -le 10 ] ; do
#    ${BD}/createRelease.sh ${I}
#    let I=${I}+1
#done
${BD}/createRelease.sh TOR1.0
${BD}/createRelease.sh TOR1.1
${BD}/createRelease.sh TOR1.2
