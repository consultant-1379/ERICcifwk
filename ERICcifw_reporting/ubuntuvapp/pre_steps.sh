#!/bin/bash
SFTPUSERNAME="root"
SFTPHOSTNAME="$1"
SFTPPWD="shroot"
WORKDIR="/proj/lciadm100"
MOUNTSERVERNAME="atclvm433"
USERNAME="lciadm100"
HOME="/home/$USERNAME"
CIFWKCONFIGDIR="$HOME/.cifwk"
VAPPSETUP="$WORKDIR/cifwk/latest/django_proj/cireports/static/setupvapp/config/lciadm100/config"
PYTHONRPMPATH="/tmp/python-libs-2.6.6.rpm"
OPENSSLRPMPATH="/tmp/openssl-1.0.rpm"
MYSQLRPMPATH="/tmp/mysql-libs-5.1.52.rpm"
EXTRACTDIRECTORY="/tmp/centos-packages"
PACKAGEPATH="/tmp/centos-packages/usr/lib64"
MYSQLPACKAGEPATH="/tmp/centos-packages/usr/lib64/mysql"
SYMLINKDIR="/lib/x86_64-linux-gnu"
PYTHONPATHDIR="$WORKDIR/cifwk/latest/lib/python/site-packages:$WORKDIR/cifwk/latest/lib/python"
HOSTNAME="atclvm433.athtem.eei.ericsson.se"

sshpass -p $SFTPPWD ssh -t -oStrictHostKeyChecking=no "$SFTPUSERNAME@$SFTPHOSTNAME" <<EOF
    sudo apt-get -y install unzip
    sudo apt-get -y install nfs-common
    sudo apt-get -y install expect
    sudo apt-get -y install autofs
    sudo apt-get -y install rpm2cpio
    sleep 5

    if [ -d "$WORKDIR" ]; then
        echo "Mount Point $WORKDIR Exists."
	      cd $WORKDIR
    else
        echo "Mount Point $WORKDIR Does Not Exists."
        sudo mkdir -p $WORKDIR
	      echo "Mount Point Created."
    fi

    if id "$USERNAME" &>/dev/null; then
        echo "User $USERNAME Found"
    else
        echo "User $USERNAME Not Found"
    fi

    su - $USERNAME
    echo "Switched To User $USERNAME"

    if ! grep 'PYTHONPATH' ~/.bashrc &> /dev/null; then
        echo "Add Python Path"
        echo 'export PYTHONPATH=$PYTHONPATH:$PYTHONPATHDIR' >> ~/.bashrc
      	echo 'export PYTHONPATH=$PYTHONPATH:$PYTHONPATHDIR' >> ~/.profile
      	source ~/.bashrc
      	source ~/.profile
    else
        echo "Python Path Exist"
    fi

    if [ -d "$CIFWKCONFIGDIR" ]; then
        echo "CIFWK Config Directory $CIFWKCONFIGDIR Exists."
    else
        echo "CIWFK Config Directory $CIFWKCONFIGDIR Does Not Exist, creating $DIFWKCONFIGDIR."
        sudo mkdir -p $CIFWKCONFIGDIR
      	sudo chown -R $USERNAME:$USERNAME $CIFWKCONFIGDIR
      	echo "CIFWK Config Directory Created"
    fi

    if [ -f "$CIFWKCONFIGDIR/config" ]; then
        echo "CIFWK Config File $CIFWKCONFIGDIR/config Exists"
    else
       	cp $VAPPSETUP $CIFWKCONFIGDIR/config
      	echo "CIFWK Config File $CIFWKCONFIGDIR/config Created"
    fi

    sudo su -
    echo "Switched to root"

    if [ -e $PYTHONRPMPATH ] && [ -e $OPENSSLRPMPATH ] && [ -e $MYSQLRPMPATH ]; then
        echo "Packages $PYTHONRPMPATH , $OPENSSLRPMPATH ,  $MYSQLRPMPATH Exist."
    else
        echo "Download from nexus to /tmp and extract packages"
        wget -c --retry-connrefused --tries=0 --timeout=5 -O $PYTHONRPMPATH https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/3pptools/com/ericsson/3ppinternal/python-libs/2.6.6/python-libs-2.6.6.rpm && rpm2cpio $PYTHONRPMPATH | cpio -D $EXTRACTDIRECTORY -idmv
        wget -c --retry-connrefused --tries=0 --timeout=5 -O $OPENSSLRPMPATH https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/3pptools/com/ericsson/3ppinternal/openssl/1.0/openssl-1.0.rpm && rpm2cpio $OPENSSLRPMPATH | cpio -D $EXTRACTDIRECTORY -idmv
        wget -c --retry-connrefused --tries=0 --timeout=5 -O $MYSQLRPMPATH https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/3pptools/com/ericsson/3ppinternal/mysql-libs/5.1.52/mysql-libs-5.1.52.rpm && rpm2cpio $MYSQLRPMPATH | cpio -D $EXTRACTDIRECTORY -idmv
        sleep 5
        echo "Download finished"
    fi

    echo "Setup MySQL Connector"

    if [ -d "$PACKAGEPATH" ]; then
        if [ ! -e $SYMLINKDIR/libssl.so.1.0.1e ] || [ ! -e $SYMLINKDIR/libcrypto.so.1.0.1e ] || [ ! -e $SYMLINKDIR/libpython2.6.so.1.0 ] || [ ! -e $SYMLINKDIR/libmysqlclient_r.so.16.0.0 ]; then
            echo "Copy packages"
            cp $PACKAGEPATH/libssl.so.1.0.1e $PACKAGEPATH/libcrypto.so.1.0.1e $PACKAGEPATH/libpython2.6.so.1.0 $MYSQLPACKAGEPATH/libmysqlclient_r.so.16.0.0 $SYMLINKDIR
        fi
    fi

    if [ ! -e $SYMLINKDIR/libssl.so.10 ] && [ ! -e $SYMLINKDIR/libcrypto.so.10 ] && [ ! -e $SYMLINKDIR/libmysqlclient_r.so.16 ]; then
        echo "Creating symbolic links"
        cd /lib/x86_64-linux-gnu
        ln -s libssl.so.1.0.1e libssl.so.10
      	ln -s libcrypto.so.1.0.1e libcrypto.so.10
      	ln -s libmysqlclient_r.so.16.0.0 libmysqlclient_r.so.16
        ldd /proj/lciadm100/cifwk/latest/lib/python/site-packages/_mysql.so
        sleep 5
    else
        echo "Symbolic link for MySQL Connector already created"
    fi

    echo "Performing Cleanup"
    if [ -d "$EXTRACTDIRECTORY" ]; then
        echo "Clean up $EXTRACTDIRECTORY"
        rm -rf $EXTRACTDIRECTORY
    fi
    if [ -e $PYTHONRPMPATH ] || [ -e $OPENSSLRPMPATH ] || [ -e $MYSQLRPMPATH ]; then
        echo "Clean up RPMs"
        rm -rf $PYTHONRPMPATH $OPENSSLRPMPATH $MYSQLRPMPATH
    fi
    echo "Cleanup finished"

    if [ ! -e /bin/gtar ]; then
        echo 'Creating symbolic link for gtar'
        cd /bin
        ln -s /bin/tar gtar
    else
        echo "Symbolic link for gtar already created"
    fi

    echo "Mount Jump Server Directory"
    if [ -d "/net" ]; then
        echo "/net Exists."
    else
        echo "/net Does Not Exist."
        mkdir -p /net
    fi

    echo "Editing Autofs config"
    if [ -f "/etc/auto.master" ]; then
        echo "Autofs Config File /etc/auto.master Exists"
        if grep '#/net' /etc/auto.master &> /dev/null; then
            echo "Uncomment /net"
            sed -i '/\/net/s/^#//g' /etc/auto.master
        else
            echo "Already uncommented /net"
        fi
        if ! grep '/export' /etc/auto.master &> /dev/null; then
            echo "Add /export/scripts config to /etc/auto.master"
            sed -i '/^\/net*/a /export/scripts /etc/auto.cite' /etc/auto.master
      	else
            echo "Line /export/scripts already added"
        fi

        if ! grep '/proj' /etc/auto.master &> /dev/null; then
            echo "Add /proj config to /etc/auto.master"
            sed -i '/^\/export*/a /proj /etc/auto.cifwk' /etc/auto.master
      	else
            echo "Line /proj already added"
        fi
    fi

    echo "Set up /etc/auto.cite"
    if [ -f "/etc/auto.cite" ]; then
        echo "/etc/auto.cite Exists."
    else
        echo "Creating /etc/auto.cite"
        touch /etc/auto.cite
        echo '* -fstype=nfs atmgtvm3.athtem.eei.ericsson.se:/export/scripts/&' > /etc/auto.cite
    fi

    echo "Set up /etc/auto.cifwk"
    if [ -f "/etc/auto.cifwk" ]; then
        echo "/etc/auto.cifwk Exists."
    else
        echo "Creating /etc/auto.cifwk"
        touch /etc/auto.cifwk
        echo 'lciadm100 -fstype=nfs,nfsvers=3 $HOSTNAME:/proj/lciadm100' | tee -a /etc/auto.cifwk >/dev/null
        echo 'tools -fstype=nfs,nfsvers=3 $HOSTNAME:/proj/tools' | tee -a /etc/auto.cifwk >/dev/null
        echo 'gitadm100 -fstype=nfs,nfsvers=3 $HOSTNAME:/proj/gitadm100' | tee -a /etc/auto.cifwk >/dev/null
    fi

    /etc/init.d/autofs restart

    su - $USERNAME
    echo "Switched to $USERNAME"
EOF
