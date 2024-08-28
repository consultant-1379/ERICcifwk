#!/bin/bash

SQL_CMD="mysql -u root -pciroot2"

${SQL_CMD} <<EOF
DROP DATABASE IF EXISTS cireports;
CREATE DATABASE IF NOT EXISTS cireports;
GRANT ALL PRIVILEGES ON cireports.* TO 'cireports'@'localhost' IDENTIFIED BY '_cirep';
GRANT ALL PRIVILEGES ON cireports.* TO 'cireports'@'%' IDENTIFIED BY '_cirep';
EOF

${SQL_CMD} cireports < /proj/lciadm100/cifwk/latest/sql/cifwk.sql
python $(dirname $0)/../../django_proj/manage.py syncdb
