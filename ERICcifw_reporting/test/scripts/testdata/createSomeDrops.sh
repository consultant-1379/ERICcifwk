#!/bin/bash

BD=$(dirname $0)

I=1
J=0
while [ ${I} -le 3 ] ; do
    ${BD}/createDrop.sh 1.0.${I} TOR1.${J}
    let I=${I}+1
done
K=4
M=1
while [ ${K} -le 6 ] ; do
    ${BD}/createDrop.sh 1.1.${K} TOR1.${M}
    let K=${K}+1
done
Y=7
T=2
while [ ${Y} -le 9 ] ; do
    ${BD}/createDrop.sh 1.2.${Y} TOR1.${T}
    let Y=${Y}+1
done
