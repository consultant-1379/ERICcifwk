#!/bin/bash

STIME=7
CIFWK=/proj/lciadm100/cifwk/latest
TDIR=${CIFWK}/test/scripts/testdata
VNUM=$1

. ${TDIR}/db.env

promote() {
    prod=$1
    level=$2
    state=$3
    maj=$4
    min=$5
    patch=$6
    mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
UPDATE cireports_productrevision,cireports_product SET $level = "$state" WHERE
cireports_productrevision.product_id = cireports_product.id AND
cireports_product.name = "$prod" AND
cireports_productrevision.major = $maj AND
cireports_productrevision.minor = $min AND
cireports_productrevision.patch = $patch ;
EOF
}

echo "Creating product version"
${TDIR}/createVersion.sh CXP9021400 1.0.1 platform 1 0 ${VNUM} 0 not_started not_started not_started
sleep ${STIME}
echo "Promoting version to compile - in progress"
promote ERICcobbler_CXP9021400 compile in_progress 1 0 ${VNUM} 0
sleep ${STIME}
promote ERICcobbler_CXP9021400 compile passed 1 0 ${VNUM} 0
promote ERICcobbler_CXP9021400 unit_test in_progress 1 0 ${VNUM} 0
sleep ${STIME}
promote ERICcobbler_CXP9021400 unit_test passed 1 0 ${VNUM} 0
promote ERICcobbler_CXP9021400 integration_test in_progress 1 0 ${VNUM} 0
sleep ${STIME}
promote ERICcobbler_CXP9021400 integration_test passed 1 0 ${VNUM} 0
sleep 1
python ${CIFWK}/django_proj/manage.py cifwk_deliver ERICcobbler_CXP9021400 1.0.${VNUM} $2
exit 0
