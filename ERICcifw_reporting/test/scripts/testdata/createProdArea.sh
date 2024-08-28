#!/bin/bash -a
. $(dirname $0)/db.env

NAME=$1

mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
INSERT INTO cireports_productarea (name) VALUES("${NAME}");
EOF
