#!/bin/bash -a
. $(dirname $0)/db.env

PNAME=$1
REL=$2
DATE=$3

SQL_CMD="mysql -u ${DBUSER} -p${DBPASS} --skip-column-names --batch ${DBNAME}"

REL_ID=$(${SQL_CMD} <<EOF
SELECT id FROM cireports_release WHERE name = "${REL}" LIMIT 1;
EOF
)

if [ -z "${REL_ID}" ] ; then
    echo "ERROR: no such release: ${REL}"
    exit 1
fi


mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
INSERT INTO cireports_drop (name,release_id,release_date) VALUES("${PNAME}",${REL_ID},"$(date "+%Y-%m-%d %H:%M:%S")");
EOF


