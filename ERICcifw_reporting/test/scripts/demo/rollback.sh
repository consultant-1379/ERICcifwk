#!/bin/bash

STIME=5
CIFWK=/proj/lciadm100/cifwk/latest
TDIR=${CIFWK}/test/scripts/testdata
VNUM=$1

. ${TDIR}/db.env

${TDIR}/createLotsOfVersions.sh


