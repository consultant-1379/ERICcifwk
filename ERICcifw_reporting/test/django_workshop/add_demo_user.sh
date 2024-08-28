#!/bin/bash

U=$1
P=$2

echo "* adding user $U"
adduser $U
echo $U | passwd $U --stdin
echo "* creating DB"
mysql <<EOF
CREATE DATABASE cidb_$U;
CREATE USER '$U'@'localhost' IDENTIFIED BY '$U';
GRANT ALL PRIVILEGES ON cidb_$U.* TO '$U'@'localhost' IDENTIFIED BY '$U';
EOF
echo "* creating my.cnf for $U"
cat <<EOF > /home/$U/.my.cnf
[client]
user = $U
password = $U
EOF

echo "* cloning repo"
su - $U -c "git clone /var/tmp/django_workshop"
echo "* copying config files"
cp ~/.vimrc /home/$U/.vimrc
chown $U:$U /home/$U/.vimrc

su - $U -c 'echo export PYTHONPATH=~/django_workshop/lib/python:$PYTHONPATH >> .bashrc'
su - $U -c 'echo export PATH=~/django_workshop/lib/tools/django/latest/django/bin:$PATH >> .bashrc'
