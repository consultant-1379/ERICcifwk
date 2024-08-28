INSERT INTO dmt_servicegrouptypes (group_type) VALUES ("JBOSS Service Cluster"),("LSB Service Cluster");
ALTER TABLE dmt_servicegroupunit DROP FOREIGN KEY servicegroupdata_2_servicegrouptypes;
INSERT INTO dmt_servicegroupunit (service_unit, group_type_id) VALUES ("FMPMServ", 1),("MSPM_ADD", 1),("MedCore", 1),("UI", 1),("FMPMCMServ", 1),("MSTLFM0", 1),("Serv", 1),("said", 1),("secserv", 1),("apserv", 1),("cmserv", 1),("fmserv", 1),("mscm", 1),("mspm", 1),("msfm", 1),("uiserv", 1),("shmserv", 1),("pmserv", 1),("impexserv", 1),("netex", 1),("wfs", 1),("sso", 1),("opendj", 2),("httpd", 2),("openidm", 2),("visinaming", 2),("visinotify", 2),("logstash", 2);
ALTER TABLE `dmt_servicegroupunit` ADD  CONSTRAINT `servicegroupdata_2_servicegrouptypes` FOREIGN KEY (`group_type_id`) REFERENCES `dmt_servicegrouptypes` (`id`);
INSERT INTO dmt_jbossclusterservicegroup (name) VALUES ("FMPMServ"), ("FMPMCMServ"), ("FMPMMS"), ("MSTLFM0"), ("MCUI"), ("SSO"), ("Serv");
