#!/bin/bash

BD=$(dirname $0)

#I=1
#while [ ${I} -le 10 ] ; do
#    ${BD}/createProdArea.sh ${I}
#    let I=${I}+1
#done
${BD}/createProdArea.sh platform
${BD}/createProdArea.sh apps
${BD}/createProdArea.sh ui
