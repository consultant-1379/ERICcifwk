#!/bin/bash

U=$1

echo "* removing user $U"
userdel $U
echo "* removing user information from DB"
mysql <<EOF
DROP DATABASE cidb_$U;
DROP USER '$U'@'localhost';
EOF
echo "* removing home area for $U"
/bin/rm -rf /home/$U/
