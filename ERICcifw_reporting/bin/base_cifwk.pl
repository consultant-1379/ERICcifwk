#!/usr/bin/perl
my $updateMacAddress;
my $vmIpddress;
my $netmask;
my $gateway;
my $dnsServer;
my @ifcfgEth0;
my $option;

print "Please Enter your vm setup option --> slave/master/cifwk/network: ";
$option = <>;
$option = lc($option);
chomp($option);

sub network
{
        print "Setting up Network for this VM\n";

        print "Please Enter the IP address of this VM: ";
        $vmIpddress=<>;
        chomp($vmIpddress);

        print "Please Enter the Netmask address of this VM: ";
        $netmask=<>;
        chomp($netmask);

        print "Please Enter the Gateway address of this VM: ";
        $gateway=<>;
        chomp($gateway);

        print "Please Enter the DNS Server address of this VM: ";
        $dnsServer=<>;
        chomp($dnsServer);

        open(FH,"/etc/sysconfig/network-scripts/ifcfg-eth0");
        @ifcfgEth0=<FH>;
        close(FH);
        my @ifcfgEth0Grep = grep(/IPADDR/,@ifcfgEth0);
        my $ifcfgEth0Grep = "@ifcfgEth0Grep";
	my @macAddress = grep(/HWADDR/,@ifcfgEth0);
	my $macAddress = "@macAddress";
	chomp($macAddress);
        chomp($ifcfgEth0Grep);
        if(! $ifcfgEth0Grep)
        {
                print "\nNetwork Details will be updated in ifcfg-eth0\n";
                open(FILE,">/etc/sysconfig/network-scripts/ifcfg-eth0");
		print FILE "DEVICE=eth0\n";
                print FILE "BOOTPROTO=static\n";
                print FILE "DHCPCLASS=\n";
                print FILE "IPADDR=${vmIpddress}\n";
                print FILE "NETMASK=${netmask}\n";
		print FILE "$macAddress\n";
		print FILE "NM_CONTROLLED=yes\n";
		print FILE "ONBOOT=yes\n";

                close(FILE);
        }
        elsif($ifcfgEth0Grep)
        {
                print "\nIP Address Setting \"$ifcfgEth0Grep\" already exists in ifcfg-eth0 therefore no updated required in ifcfg-eth0 file\n\n";
        }

        open(FH,"/etc/sysconfig/network");
        my @gateway=<FH>;
        close(FH);
        my @gatewayGrep = grep(/GATEWAY/, @gateway);
        my $gatewayGrep = ("@gatewayGrep");
        chomp($gatewayGrep);
		if(! $gatewayGrep)
        {
                print "Network update with Gateway Ip will now be made\n";
                open(FILE,">>/etc/sysconfig/network");
                print FILE "GATEWAY=${gateway}\n";
                close(FILE);
        }
        elsif($gatewayGrep)
        {
                print "Gateway IP address \"$gatewayGrep\" is already defined in the network config file therefore no update will be made\n\n";
        }

        open(FILE,">/etc/resolv.conf");
        print FILE "nameserver ${dnsServer}\n";
        close(FILE);

        system("/etc/init.d/network restart");
}


sub base_os
{
	open(FH,">>/root/.bash_profile");
	print FH "export http_proxy\=http://www-proxy.ericsson.se:8080\n";
	close(FH);
	qx(source /root/.bash_profile);
	qx(useradd lciadm100);
	qx(useradd gitadm100);
	qx(mkdir -p /repos/6 /repos/61);

	open(FH,">>/etc/fstab");
	print FH "atloaner50.athtem.eei.ericsson.se:/jump/SW/OS/RHEL/6_1 /repos/61 nfs user 0 0\n";
	print FH "atloaner50.athtem.eei.ericsson.se:/jump/SW/OS/RHEL/6 /repos/6 nfs user 0 0\n";
	close(FH);
	qx(mount -a);


	open(FH,">/etc/yum.repos.d/eric_RHEL.repo");
	print FH "[RHEL6]\n";
	print FH "name=RHEL6\n";
	print FH "baseurl=file:///repos/6/\n";
	print FH "enabled=1\n";
	print FH "gpgcheck=0\n";
	print FH "[RHEL61]\n";
	print FH "name=RHEL6_1\n";
	print FH "baseurl=file:///repos/61/\n";
	print FH "enabled=1\n";
	print FH "gpgcheck=0\n";
	close(FH);

	qx(mkdir /mnt/CI_FWK_Install_Files);
	open(FH,">>/etc/fstab");
	print FH "159.107.177.22:/CIShare/CI_sw /mnt/CI_FWK_Install_Files nfs defaults 0 0\n";
	close(FH);
	qx(mount -a);

	open(FH,">>/etc/yum.conf");
	print FH "proxy=http://www-proxy.ericsson.se:8080\n";
	close(FH);

	system("yum install -y git createrepo rpm-build rpm-python mcompress");

	system("yum install -y Django mock pigz python-cherrypy2 python-httplib2 python-IPy python-minimock python-pep8 python-pip python-unittest2 compat-readline5");

	system("rpm -iv /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/tanukiwrapper /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/activemq /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/ruby-libs /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/ruby /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/ruby-irb /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/ruby-rdoc /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/rubygems /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/rubygem-stomp /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/mcollective-common /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/mcollective /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/mcollective-client");

	open(FH,">/etc/sysconfig/iptables");
	print FH "
\# Firewall configuration written by system-config-firewall
\# Manual customization of this file is not recommended.\n
\*filter\n
\:INPUT ACCEPT [0\:0]\n
\:FORWARD ACCEPT [0\:0]\n
\:OUTPUT ACCEPT [0\:0]\n
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT\n
-A INPUT -p icmp -j ACCEPT\n
-A INPUT -i lo -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 3306 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8080 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8081 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8888 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 8000 -j ACCEPT\n
-A INPUT -m state --state NEW -m tcp -p tcp --dport 29418 -j ACCEPT\n
-A INPUT -j REJECT --reject-with icmp-host-prohibited\n
-A FORWARD -j REJECT --reject-with icmp-host-prohibited\n
COMMIT\n";

	system("service iptables restart");
}

sub jdk 
{
	system("/mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/jdk -noregister");
	qx(alternatives --install /usr/bin/java java /usr/java/latest/bin/java 20000 --slave /usr/bin/keytool keytool /usr/java/latest/bin/keytool --slave /usr/bin/orbd orbd /usr/java/latest/bin/orbd --slave /usr/bin/pack200 pack200 /usr/java/latest/bin/pack200 --slave /usr/bin/rmid rmid /usr/java/latest/bin/rmid --slave /usr/bin/rmiregistry rmiregistry /usr/java/latest/bin/rmiregistry --slave /usr/bin/servertool servertool /usr/java/latest/bin/servertool --slave /usr/bin/tnameserv tnameserv /usr/java/latest/bin/tnameserv --slave /usr/bin/unpack200 unpack200 /usr/java/latest/bin/unpack200 --slave /usr/lib/jvm/jre jre /usr/java/latest/jre);
}


sub mysql 
{
	print "Starting Mysql Stage\n\n";
	system("yum -y install mysql-server mysql");
	system("yum -y install mysql-connector-java.x86_64 MySQL-python");
	qx(chkconfig mysqld on);
	qx(service mysqld start);
	qx(mysqladmin -u root password cifwk23);
	print "Finishing Mysql Stage\n\n";
}

sub apache
{
	print "Starting Apache Stage\n\n";
	system("yum install httpd mod_wsgi -y");
	print "Finishing Apache Stage\n\n";
}

sub nexus
{
        print "Starting Nexus Stage\n\n";
        qx(sudo -u gitadm100 mkdir /home/gitadm100/nexus);
        qx(sudo -u gitadm100 cp /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/nexus /home/gitadm100/nexus/nexus.tar.gz);
        system("sudo -u gitadm100 tar -xvf /home/gitadm100/nexus/nexus.tar.gz -C /home/gitadm100/nexus");
        system("sudo -u gitadm100 /home/gitadm100/nexus/nexus-oss-webapp-1.9.2.4/bin/jsw/linux-x86-64/nexus start");
        print "Finishing Nexus Stage\n\n";
}

sub maven
{
	print "Starting Maven Stage\n\n";
	qx(sudo -u gitadm100 mkdir /home/gitadm100/maven);
	qx(sudo -u gitadm100 cp /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/maven /home/gitadm100/maven/maven.tar.gz);
	system("sudo -u gitadm100 tar -xvf /home/gitadm100/maven/maven.tar.gz -C /home/gitadm100/maven");

	open(FH,">>/home/gitadm100/.bash_profile");
	print FH "
export JAVA_HOME\=/usr/java/jdk1.6.0_30
export M2_HOME\=/home/gitadm100/maven/apache-maven-3.0.4
export PATH\=\$JAVA_HOME/bin:\$M2_HOME/bin:\$PATH\n";
	close(FH);
	system("ohown gitadm100:gitadm100 /home/gitadm100/.bash_profile");

	qx(sudo -u gitadm100 source /home/gitadm100/.bash_profile);
	print "Finishing Maven Stage\n\n";
}

sub gerrit
{
	system("rpm -iv /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/gitweb");
	my $local_hostname = qx(hostname);
	chomp($local_hostname);
	print "The hostname is set to $local_hostname\n";

	qx(sudo -u gitadm100 mkdir -p /home/gitadm100/${local_hostname}/gerrit);
	qx(sudo -u gitadm100 cp /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/gerrit.war /home/gitadm100/${local_hostname}/gerrit);
	system("sudo -u gitadm100 java -jar /home/gitadm100/${local_hostname}/gerrit/gerrit.war init --batch -d /home/gitadm100/${local_hostname}/gerrit/review_site");
	system("sudo -u gitadm100 /home/gitadm100/${local_hostname}/gerrit/review_site/bin/gerrit.sh stop");

	open(FH,">>/home/gitadm100/.bashrc");
	print FH "export GERRIT_SITE=/home/gitadm100/\$HOSTNAME/gerrit/review_site\n";
	close(FH);
	system("ohown gitadm100:gitadm100 /home/gitadm100/.bashrc");
	qx(sudo -u gitadm100 source /home/gitadm100/.bashrc);

	open(FH,">>/home/gitadm100/${local_hostname}/gerrit/review_site/etc/secure.config");
print FH "[ldap]
	password = zx12\$RFV\!qaz
	hostname = ecd.ericsson.se
	username = uid=LDAPKBEN,ou=Users,ou=Internal,o=ericsson
";
	system("chown -R gitadm100:gitadm100 /home/gitadm100/${local_hostname}/gerrit/review_site/etc/secure.config");
	open(FH,">/home/gitadm100/${local_hostname}/gerrit/review_site/etc/gerrit.config"); 
print FH "[gerrit]
       basePath = git
[database]
       type = H2
       database = db/ReviewDB
[auth]
       type = LDAP
[ldap]
       server = ldaps://ecd.ericsson.se:636
       username = uid=gitadm100,ou=Users,ou=Internal,o=ericsson
       accountBase = o=ericsson
       accountPattern = uid=\${username}
       accountSshUserName = \${uid.toLowerCase}
       accountFullName = displayName
       accountEmailAddress = \${mail.toLowerCase}
[sendemail]
       smtpServer = malmen.ericsson.se
       smtpServerPort = 25
       smtpUser = gitadm1000
[container]
       user = gitadm100
       javaHome = /usr/java/default
       heapLimit = 1g
[sshd]
       listenAddress = *:29418
       threads = 4
[httpd]
       listenUrl = http://*:8888/
[cache]
       directory = cache
[gitweb]
       cgi = /var/www/git/gitweb.cgi
";
close(FH);
	system("chown -R gitadm100:gitadm100 /home/gitadm100/${local_hostname}/gerrit/review_site/etc/gerrit.config");
	system("sudo -u gitadm100 /home/gitadm100/${local_hostname}/gerrit/review_site/bin/gerrit.sh start");
	print "Finished main Gerrit steps now starting gerrit up \n\n";
}

sub tomcat
{
	print "Starting Tomcat Step\n\n";
	qx(sudo -u lciadm100 mkdir /home/lciadm100/tomcat);
	qx(sudo -u lciadm100 cp /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/tomcat /home/lciadm100/tomcat/tomcat.tar.gz);
	system("sudo -u lciadm100 tar -xvf /home/lciadm100/tomcat/tomcat.tar.gz -C /home/lciadm100/tomcat/");
	system("sudo -u lciadm100 /home/lciadm100/tomcat/apache-tomcat-6.0.35/bin/startup.sh");

	print "Finished Tomcat Stage\n";
}

sub jenkins
{
	print "Starting Jenkins Step\n";
	qx(sudo -u lciadm100 mkdir /home/lciadm100/jenkins);

	open(FH,">>/home/lciadm100/.bash_profile");
	print FH "export JENKINS_HOME=/build/admin/jenkins\n";
	close(FH);
	system("chown lciadm100:lciadm100 /home/lciadm100/.bash_profile");

	qx(sudo -u lciadm100 cp /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/jenkins /home/lciadm100/tomcat/apache-tomcat-6.0.35/webapps/jenkins.war);
	print "Finished Jenkins Stage\n";
}

sub django
{
	print "Starting setting up Django\n";
	
	system("rpm -qa | grep -i django");
	system("rpm -qa | grep -i mod_wsgi");
	system("yum install mod_wsgi.x86_64");
	qx(sudo -u lciadm100 mkdir -p /proj/lciadm100/tools/django);
	qx(sudo -u lciadm100 chmod 777 /proj/lciadm100/tools/django);
	
	system("sudo -u lciadm100 tar xvf /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/Django-1.4.tar.gz -C /proj/lciadm100/tools/django");
	system("sudo -u lciadm100 ln -s /proj/lciadm100/tools/django/Django-1.4 /proj/lciadm100/tools/django/latest");
	print "Finished setting up Django\n";
	
}

sub ldap
{
	print "Setting up LDAP part\n";
	
	qx(sudo -u lciadm100 mkdir -p /proj/lciadm100/tools/django-auth-ldap);
	system("sudo -u lciadm100 tar xvf /mnt/CI_FWK_Install_Files/CI_FWK_0.1_Install_Media/django-auth-ldap-1.1.tar.gz -C /proj/lciadm100/tools/django-auth-ldap");
	system("sudo -u lciadm100 ln -s /proj/lciadm100/tools/django-auth-ldap/django-auth-ldap-1.1 /proj/lciadm100/tools/django-auth-ldap/latest");
	print "Finishing up LDAP part\n";
}

sub git
{
	print "Setting up git directories\n";
	
	qx(sudo -u lciadm100 mkdir -p /proj/lciadm100/cifwk);
	qx(sudo -u lciadm100 mkdir -p /proj/lciadm100/cifwk/var/run);
	qx(sudo -u lciadm100 mkdir -p /proj/lciadm100/cifwk/logs);
	print "******************************************************\n";
	print "NOTE NOTE ********************************** NOTE NOTE\n";
	print "****************** MANUAL STEP ***********************\n";
	print "As user lciadm100 following SSH Key GIT Setup  \"http://atrclin2.athtem.eei.ericsson.se/wiki/index.php/Setting_up_Git#Generate_a_public_SSH_key\"\n";
	print "Then change directory to \"/proj/lciadm100/cifwk\" and user to lciadm100 \"su -l lciadm100\"\n";
	print "Then Run:\n";
	print "1.\"git clone ssh://<user>@eselivm2v238l.lmera.ericsson.se:29418/com.ericsson.cifwk/ERICcifw_reporting\"\n";
	print "2.\"ln -s ERICcifw_reporting latest\"\n";
	print "3.\"proj/lciadm100/cifwk/ERICcifw_reporting/test/scripts/createdb.sh\"\n";
	print "4.\"Enter password:<password of MySQL root user>\"n";
	print "5.\"python /proj/lciadm100/cifwk/ERICcifw_reporting/django_proj/manage.py syncdb\"\n";
	print "6.\"/proj/lciadm100/cifwk/latest/etc/init.d/cifwk-httpd start\"\n";
	
	print "Finished up git directories\n";

	
}
if($option eq "master")
{
	base_os();
	jdk();
	mysql();
	apache();
	nexus();
	maven();
	tomcat();
	jenkins();
}
elsif($option eq "slave")
{
	base_os();
	jdk();
	mysql();
}
elsif($option eq "cifwk")
{
	base_os();
	jdk();
	mysql();
	apache();
	nexus();
	maven();
	gerrit();
	tomcat();
	jenkins();
	django();
	ldap();
	git();
}
elsif($option eq "network")
{
	network();
}
else
{
        print "INVALID OPTION ENTERED EXITING SCRIPT\n\n";
        exit 1;
}

