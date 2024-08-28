#!/bin/bash
# Increment the r-state by one
. $(dirname $0)/db.env

PNUM=$1
DROP=$2
S_SET=$3
REV=$4

COMP=$5
UT=$6
IT=$7
SH=$8

SQL_CMD="mysql -u ${DBUSER} -p${DBPASS} --skip-column-names --batch ${DBNAME}"

PROD_ID=$(${SQL_CMD}  <<EOF
SELECT id FROM cireports_product WHERE product_number = "${PNUM}" LIMIT 1;
EOF
)

if [ -z "${PROD_ID}" ] ; then
    echo "ERROR: no such PNUM: ${PNUM}"
    exit 1
fi

#DROP_ID=$(${SQL_CMD} <<EOF
#SELECT id FROM cireports_drop WHERE name = "${DROP}" LIMIT 1;
#EOF
##)

#if [ -z "${DROP_ID}" ] ; then
#    echo "ERROR: no such drop: ${DROP}"
#    exit 1
#fi

S_SET_ID=$(${SQL_CMD} <<EOF
SELECT id FROM cireports_solutionset WHERE name = "${S_SET}";
EOF
)

if [ -z "${S_SET_ID}" ] ; then
    echo "ERROR: no such solution set: ${S_SET}"
    exit 1
fi

#cat <<EOF
#INSERT INTO cireports_productrevision (product_id,m2version,date_created,solution_set_id, compile, unit_test, integration_test) VALUES
#(${PROD_ID},${REV},"$(date "+%Y-%m-%d %H:%M:%S")",${S_SET_ID}, '${COMP}', '${UT}', '${IT}');
#EOF

${SQL_CMD} <<EOF
INSERT INTO cireports_productrevision (product_id,m2version,date_created,solution_set_id, compile, unit_test, integration_test) VALUES
(${PROD_ID},'${REV}',"$(date "+%Y-%m-%d %H:%M:%S")",${S_SET_ID}, '${COMP}', '${UT}', '${IT}');
EOF

