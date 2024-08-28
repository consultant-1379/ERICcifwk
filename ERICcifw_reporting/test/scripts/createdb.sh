#!/bin/bash

SQL_CMD="mysql -u root -p"

${SQL_CMD} <<EOF
CREATE DATABASE IF NOT EXISTS cireports;
GRANT ALL PRIVILEGES ON cireports.* TO 'cireports'@'localhost' IDENTIFIED BY '_cirep';
GRANT ALL PRIVILEGES ON cireports.* TO 'cireports'@'%' IDENTIFIED BY '_cirep';
EOF
