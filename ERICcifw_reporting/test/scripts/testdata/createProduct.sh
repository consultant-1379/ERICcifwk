#!/bin/bash -a
. $(dirname $0)/db.env

PNAME=$1
PNUM=$2

mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
INSERT INTO cireports_product (name,product_number) VALUES("${PNAME}","${PNUM}");
EOF
