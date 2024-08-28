-- END 1.0.1
ALTER TABLE cireports_product ADD COLUMN `description` varchar(255) NOT NULL AFTER product_number;

ALTER TABLE cireports_productrevision CHANGE `date_created` `date_created` timestamp NOT NULL DEFAULT "2012-01-01 00:00:00";
ALTER TABLE cireports_productrevision CHANGE `last_update` `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE cireports_productrevision CHANGE `correction` `correction` bool NOT NULL DEFAULT 0;
ALTER TABLE cireports_productrevision CHANGE `compile` `compile` varchar(20) NOT NULL DEFAULT "not_started";
ALTER TABLE cireports_productrevision CHANGE `unit_test` `unit_test` varchar(20) NOT NULL DEFAULT "not_started";
ALTER TABLE cireports_productrevision CHANGE `integration_test` `integration_test` varchar(20) NOT NULL DEFAULT "not_started";

ALTER TABLE cireports_productrevision DROP FOREIGN KEY productrevision_2_solutionset;
ALTER TABLE cireports_productrevision DROP COLUMN solution_set_id;
DROP TABLE IF EXISTS `cireports_solutionset`;
CREATE TABLE `cireports_solutionset` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `product_number` varchar(12) NOT NULL
) ENGINE=InnoDB ;

CREATE TABLE `cireports_solutionsetrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `solution_set_id` SMALLINT UNSIGNED NOT NULL,
    `version` varchar(100) NOT NULL,
    CONSTRAINT `solutionsetrevision_2_solutionset` FOREIGN KEY (`solution_set_id`) REFERENCES `cireports_solutionset` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_solutionsetcontents` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `solution_set_rev_id` integer UNSIGNED NOT NULL,
    `productrevision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `solutionsetcontents_2_solutionsetrevision` FOREIGN KEY (`solution_set_rev_id`) REFERENCES `cireports_solutionsetrevision` (`id`),
    CONSTRAINT `solutionsetcontents_2_productrevision` FOREIGN KEY (`productrevision_id`) REFERENCES `cireports_productrevision` (`id`)
) ENGINE=InnoDB;

ALTER TABLE cireports_productrevision CHANGE m2version version varchar(100);
ALTER TABLE cireports_productrevision CHANGE m2groupId groupId varchar(100);
ALTER TABLE cireports_productrevision CHANGE m2artifactId artifactId varchar(100);
ALTER TABLE cireports_productrevision CHANGE unit_test kgb_test varchar(20) NOT NULL DEFAULT "not_started";
ALTER TABLE cireports_productrevision CHANGE integration_test rdc_test varchar(20) NOT NULL DEFAULT "not_started";

-- END 1.0.2

-- END 1.0.3

-- Dummy Table created to test upgrade
DROP TABLE IF EXISTS `cireports_marko`;
CREATE TABLE `cireports_marko` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL
) ENGINE=InnoDB ;

-- END 1.0.4

-- END 1.0.6

-- END 1.0.7

-- Removing Table to further test the upgrade script
DROP TABLE IF EXISTS `cireports_marko`;

-- END 1.0.8

-- Another test addition for Upgrade tests
ALTER TABLE cireports_team ADD COLUMN `logo` varchar(25) NOT NULL AFTER name;

-- END 1.0.9

-- Back out the changes made by previous test
ALTER TABLE cireports_team DROP COLUMN `logo`;

-- END 1.0.10

-- END 1.0.11

-- END 1.0.12

-- END 1.0.13

-- END 1.0.14

-- END 1.0.15

-- END 1.0.16

-- END 1.0.17

-- Need a unique index to allow products to be added programmatically
ALTER TABLE cireports_product ADD UNIQUE INDEX nameNumber (name, product_number);

-- END 1.0.18

-- Signum field too small to allow lciadm100 as a userid
ALTER TABLE cireports_product MODIFY COLUMN `signum` varchar(12) NOT NULL;

-- END 1.0.19

-- END 1.0.20

-- END 1.0.21

-- END 1.0.22

-- END 1.0.23

-- END 1.0.24

-- END 1.0.25

-- CLeanup for migration of fwk functionality to specific app
DROP TABLE IF EXISTS cireports_build;
RENAME TABLE cireports_team TO fwk_team;
RENAME TABLE cireports_urldisplay TO fwk_urldisplay;
RENAME TABLE cireports_tvinfomap TO fwk_tvinfomap;

-- change from product to package
ALTER TABLE cireports_productrevision DROP FOREIGN KEY productrevision_2_product;
ALTER TABLE cireports_dropproductmapping DROP FOREIGN KEY dropproductmapping_2_productrevision;
ALTER TABLE cireports_dropproductmapping DROP FOREIGN KEY dropproductmapping_2_drop;
ALTER TABLE dmt_kgbappinstance DROP FOREIGN KEY kgbappinstance_2_cireports_productrevision;

RENAME TABLE `cireports_product` TO `cireports_package`;
RENAME TABLE `cireports_productrevision` TO `cireports_packagerevision`;
RENAME TABLE `cireports_dropproductmapping` TO `cireports_droppackagemapping`;

ALTER TABLE cireports_packagerevision CHANGE product_id package_id smallint UNSIGNED NOT NULL;
ALTER TABLE cireports_droppackagemapping CHANGE product_revision_id package_revision_id integer UNSIGNED NOT NULL;

ALTER TABLE cireports_packagerevision ADD CONSTRAINT `packagerevision_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`);
ALTER TABLE cireports_droppackagemapping ADD CONSTRAINT `droppackagemapping_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`);
ALTER TABLE cireports_droppackagemapping ADD CONSTRAINT `droppackagemapping_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`);

ALTER TABLE avs_story DROP FOREIGN KEY story_2_cireports_product;
ALTER TABLE avs_story CHANGE product_id package_id smallint UNSIGNED NOT NULL;
ALTER TABLE avs_story ADD CONSTRAINT `story_2_cireports_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`);

ALTER TABLE dmt_kgbappinstance ADD CONSTRAINT `kgbappinstance_2_cireports_packagerevision` FOREIGN KEY (`aut_id`) REFERENCES `cireports_packagerevision` (`id`);


-- END 1.0.26

-- END 1.0.27

-- END 1.0.28

-- END 1.0.29

-- END 1.0.30

-- END 1.0.31

ALTER TABLE avs_story DROP FOREIGN KEY story_2_epic;
ALTER TABLE avs_story DROP FOREIGN KEY story_2_cireports_package;
ALTER TABLE avs_testcase DROP FOREIGN KEY testcase_2_story;
ALTER TABLE avs_testcase DROP FOREIGN KEY testcase_2_verificationpoint;
ALTER TABLE avs_testcase DROP FOREIGN KEY testcase_2_actionpoint;

DROP TABLE `avs_epic`;
DROP TABLE `avs_story`;
DROP TABLE `avs_vs`;
DROP TABLE `avs_actionpoint`;
DROP TABLE `avs_verificationpoint`;
DROP TABLE `avs_testcase`;

CREATE TABLE `avs_epic` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `epicId` varchar(20) NOT NULL,
    `title` varchar(200) NOT NULL
)
;
CREATE TABLE `avs_userstory` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `usId` varchar(20) NOT NULL,
    `title` varchar(200) NOT NULL,
    `epic_id` integer NOT NULL,
    CONSTRAINT `userstory_2_epic` FOREIGN KEY (`epic_id`) REFERENCES `avs_epic` (`id`)
)
;

CREATE TABLE `avs_avsfile` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateCreated` datetime,
    `fileName` varchar(50) NOT NULL,
    `fileContent` longtext,
    `owner` varchar(10) NOT NULL
)
;
CREATE TABLE `avs_avs` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateCreated` datetime,
    `lastUpdated` datetime,
    `avsId` varchar(20) NOT NULL,
    `owner` varchar(10) NOT NULL,
    `avsFile_id` integer unsigned NOT NULL,
    `revision` integer NOT NULL,
    CONSTRAINT `avs_2_file` FOREIGN KEY (`avsFile_id`) REFERENCES `avs_avsfile` (`id`)
)
;
CREATE TABLE `avs_testcase` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateCreated` datetime,
    `lastUpdated` datetime,
    `tcId` varchar(20) NOT NULL,
    `title` varchar(200) NOT NULL,
    `desc` longtext,
    `userStory_id` integer unsigned NOT NULL,
    `type` varchar(20) NOT NULL,
    `component` varchar(20) NOT NULL,
    `priority` varchar(20) NOT NULL,
    `groups` varchar(20),
    `pre` varchar(200),
    `vusers` varchar(50),
    `context` varchar(200),
    `revision` integer NOT NULL,
    CONSTRAINT `testcase_2_userstory` FOREIGN KEY (`userStory_id`) REFERENCES `avs_userstory` (`id`)
)
;
CREATE TABLE `avs_testresult` (
    `id` bigint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testCase_id` integer unsigned NOT NULL,
    `testResult` varchar(20) NOT NULL,
    `testDuration` integer NOT NULL,
    `testStart` varchar(20) NOT NULL,
    `testFinish` varchar(20) NOT NULL,
    `testFailString` longtext,
    CONSTRAINT `testresult_2_testcase` FOREIGN KEY (`testCase_id`) REFERENCES `avs_testcase` (`id`)
)
;
CREATE TABLE `avs_actionpoint` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `desc` longtext,
    `testCase_id` integer unsigned NOT NULL,
    CONSTRAINT `actionpoint_2_testcase` FOREIGN KEY (`testCase_id`) REFERENCES `avs_testcase` (`id`)
)
;
CREATE TABLE `avs_verificationpoint` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `desc` longtext,
    `actionPoint_id` integer unsigned NOT NULL,
    CONSTRAINT `verificationpoint_2_testcase` FOREIGN KEY (`actionPoint_id`) REFERENCES `avs_actionpoint` (`id`)
)
;

-- END 1.0.32

-- END 1.0.33

ALTER TABLE cireports_package CHANGE product_number package_number varchar(12) NOT NULL;
ALTER TABLE cireports_solutionset CHANGE product_number package_number varchar(12) NOT NULL;
ALTER TABLE cireports_droppackagemapping ADD COLUMN delivery_info longtext NOT NULL;

ALTER TABLE avs_testcase CHANGE COLUMN component component varchar(50) NOT NULL;

-- END 1.0.34

-- END 1.0.35

CREATE TABLE `dmt_managementserver` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ilo_Address` varchar(30) NOT NULL,
    `hostname` varchar(30) NOT NULL,
    `ipV4_Address` varchar(30) NOT NULL,
    `ipV6_Address` varchar(30),
    `mac_Address` varchar(30) NOT NULL,
    `netmask` varchar(30) NOT NULL,
    `default_Gateway` varchar(30) NOT NULL,
    `dns_Server` varchar(30) NOT NULL,
    `tipc_Address` varchar(30) NOT NULL
) ENGINE=InnoDB
;


-- END 1.0.36

-- END 1.0.37

DROP TABLE IF EXISTS dmt_managementserver;
RENAME TABLE dmt_ipaddress TO dmt_appipaddress;

CREATE TABLE `dmt_managementserver` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `dns_server` varchar(30) NOT NULL,
    `description` longtext
) ENGINE=InnoDB;

CREATE TABLE `dmt_cluster` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `description` longtext,
    `tipc_address` integer UNSIGNED NOT NULL UNIQUE,
    `dhcp_lifetime` datetime not null default "1970-01-01 00:00:00",
    `management_server_id` smallint unsigned NOT NULL,
    CONSTRAINT `cluster_2_managementserver` FOREIGN KEY (`management_server_id`) REFERENCES `dmt_managementserver` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_server` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `dns_server` varchar(30) NOT NULL,
    `type` varchar(20) NOT NULL,
    `hardware_type` varchar(20) NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `server_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_networkinterface` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mac_address` varchar(18) NOT NULL UNIQUE,
    `server_id` integer unsigned NOT NULL,
    CONSTRAINT `networkinterface_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_ipaddress` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `address` char(39) NOT NULL UNIQUE,
    `netmask` char(39) NOT NULL,
    `nic_id` integer unsigned NOT NULL,
    CONSTRAINT `ipaddress_2_networkinterface` FOREIGN KEY (`nic_id`) REFERENCES `dmt_networkinterface` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_ilo` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `address` varchar(50) NOT NULL,
    `server_id` integer unsigned NOT NULL UNIQUE,
    `username` varchar(10),
    `password` varchar(50),
    CONSTRAINT `ilo_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB;

-- END 1.0.38


-- END 1.0.39

ALTER TABLE dmt_managementserver ADD COLUMN `SSH_Host_RSA_Key` varchar(450) NOT NULL AFTER dns_server;

ALTER TABLE avs_userstory CHANGE `epic_id` `epic_id` SMALLINT NOT NULL;

-- END 1.0.40

-- END 1.0.41

-- END 1.0.42

-- END 1.0.43

-- END 1.0.44
ALTER TABLE cireports_packagerevision ADD COLUMN `non_proto_build` varchar(5) NOT NULL DEFAULT "true" AFTER correction;

-- END 1.0.45

CREATE TABLE `fwk_cifwkdevelopmentserver` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `vm_hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `ipAddress` varchar(30) NOT NULL UNIQUE,
    `bookingDate` datetime not null default "1970-01-01 00:00:00",
    `owner` varchar(30) NOT NULL UNIQUE,
    `description` longtext
) ENGINE=InnoDB;

ALTER TABLE dmt_cluster ADD COLUMN `cluster_Type` varchar(25) NOT NULL DEFAULT "true" AFTER tipc_address;

CREATE TABLE `dmt_cloudcluster` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `gateway_IPAddress` char(39) NOT NULL UNIQUE,
    `managementServer_IPAddress` char(39) NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `cluster_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

-- END 1.1.1

ALTER table dmt_server ADD COLUMN `node_type` varchar(5) NOT NULL AFTER hardware_type;

ALTER TABLE dmt_cluster DROP COLUMN cluster_Type;

DROP TABLE IF EXISTS `dmt_cloudcluster`;

DROP TABLE IF EXISTS `avs_verificationpoint`;
DROP TABLE IF EXISTS `avs_actionpoint`;
DROP TABLE IF EXISTS `avs_testresult`;
DROP TABLE IF EXISTS `avs_testcase`;
DROP TABLE IF EXISTS `avs_component`;
DROP TABLE IF EXISTS `avs_avs`;
DROP TABLE IF EXISTS `avs_avsfile`;
DROP TABLE IF EXISTS `avs_epicuserstorymapping`;
DROP TABLE IF EXISTS `avs_userstory`;
DROP TABLE IF EXISTS `avs_epic`;

-- AVS

CREATE TABLE `avs_epic` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL UNIQUE,
    `title` varchar(200) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `avs_userstory` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL UNIQUE,
    `title` varchar(200) NOT NULL,
    `epic_id` integer NOT NULL,
    CONSTRAINT `userstory_2_epic` FOREIGN KEY (`epic_id`) REFERENCES `avs_epic` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `avs_epicuserstorymapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `epic_id` integer NOT NULL,
    `user_story_id` integer NOT NULL,
    CONSTRAINT `epicuserstorymapping_2_epic` FOREIGN KEY (`epic_id`) REFERENCES `avs_epic` (`id`),
    CONSTRAINT `epicuserstorymapping_2_userstory` FOREIGN KEY (`user_story_id`) REFERENCES `avs_userstory` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `avs_avsfile` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateCreated` datetime,
    `fileName` varchar(50) NOT NULL UNIQUE,
    `fileContent` longtext,
    `owner` varchar(10) NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `avs_avs` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateCreated` datetime,
    `lastUpdated` datetime,
    `avsId` varchar(20) NOT NULL UNIQUE,
    `owner` varchar(10) NOT NULL,
    `avsFile_id` integer NOT NULL,
    `revision` integer NOT NULL,
    CONSTRAINT `avs_2_file` FOREIGN KEY (`avsFile_id`) REFERENCES `avs_avsfile` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `avs_component` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `avs_testcase` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateCreated` datetime,
    `lastUpdated` datetime,
    `tcId` varchar(20) NOT NULL UNIQUE,
    `title` varchar(200) NOT NULL,
    `desc` longtext,
    `userStory_id` integer NOT NULL,
    `type` varchar(4) NOT NULL,
    `component_id` integer NOT NULL,
    `priority` varchar(20) NOT NULL,
    `groups` varchar(20),
    `pre` varchar(200),
    `vusers` varchar(50),
    `context` varchar(200),
    `revision` integer NOT NULL,
    CONSTRAINT testcase_2_userstory FOREIGN KEY (`userStory_id`) REFERENCES `avs_userstory` (`id`),
    CONSTRAINT testcase_2_component FOREIGN KEY (`component_id`) REFERENCES `avs_component` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `avs_testresult` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testCase_id` integer NOT NULL,
    `testResult` varchar(20) NOT NULL,
    `testDuration` integer NOT NULL,
    `testStart` varchar(20) NOT NULL,
    `testFinish` varchar(20) NOT NULL,
    `testFailString` longtext,
    CONSTRAINT testresult_2_testcase FOREIGN KEY (`testCase_id`) REFERENCES `avs_testcase` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `avs_actionpoint` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `desc` longtext,
    `testCase_id` integer NOT NULL,
    CONSTRAINT `actionpoint_2_testcase` FOREIGN KEY (`testCase_id`) REFERENCES `avs_testcase` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `avs_verificationpoint` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `desc` longtext,
    `actionPoint_id` integer NOT NULL,
    CONSTRAINT `verificationpoint_2_testcase` FOREIGN KEY (`actionPoint_id`) REFERENCES `avs_actionpoint` (`id`)
) ENGINE=InnoDB
;

-- New DMT table

CREATE TABLE `dmt_multicast` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `messaging_group_address` char(39) NOT NULL UNIQUE,
    `messaging_group_port` integer UNSIGNED NOT NULL UNIQUE,
    `udp_mcast_address` char(39) NOT NULL UNIQUE,
    `udp_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `mping_mcast_address` char(39) NOT NULL UNIQUE,
    `mping_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `multicast_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

-- END 1.1.2

ALTER TABLE avs_userstory DROP INDEX name;
ALTER TABLE avs_userstory ADD COLUMN version int(11);
ALTER TABLE avs_testcase DROP INDEX tcId;
ALTER TABLE avs_testcase ADD COLUMN archived int(11);
ALTER TABLE avs_testcase MODIFY COLUMN archived int(11) NOT NULL;
ALTER TABLE avs_testcase DROP foreign key testcase_2_userstory;
ALTER TABLE avs_testcase DROP INDEX testcase_2_userstory;
ALTER TABLE avs_testcase DROP userStory_id;

CREATE TABLE `avs_testcaseuserstorymapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_story_id` integer NOT NULL,
    `test_case_id` integer NOT NULL,
    CONSTRAINT testcaseuserstorymapping_2_userstory FOREIGN KEY (`user_story_id`) REFERENCES `avs_userstory` (`id`),
    CONSTRAINT testcaseuserstorymapping_2_testcase FOREIGN KEY (`test_case_id`) REFERENCES `avs_testcase` (`id`)
) ENGINE=InnoDB ;

ALTER TABLE cireports_packagerevision ADD COLUMN `autodrop` varchar(100) NOT NULL AFTER version;

-- DMT refactor
DROP TABLE IF EXISTS dmt_apphostipmap;
DROP TABLE IF EXISTS dmt_apphost;
DROP TABLE IF EXISTS dmt_appipaddress;
DROP TABLE IF EXISTS dmt_kgbappinstance;
DROP TABLE IF EXISTS dmt_apptemplate;
DROP TABLE IF EXISTS dmt_clusterserver;
DROP TABLE IF EXISTS dmt_multicast;
DROP TABLE IF EXISTS dmt_ilo;
DROP TABLE IF EXISTS dmt_ipaddress;
DROP TABLE IF EXISTS dmt_networkinterface;
DROP TABLE IF EXISTS dmt_server;
DROP TABLE IF EXISTS dmt_cluster;
DROP TABLE IF EXISTS dmt_managementserver;

CREATE TABLE `dmt_server` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `dns_server` varchar(30) NOT NULL,
    `hardware_type` varchar(20) NOT NULL
) ENGINE=InnoDB;


CREATE TABLE `dmt_managementserver` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `SSH_Host_RSA_Key` varchar(450) NOT NULL,
    `description` longtext NOT NULL,
    `server_id` integer unsigned NOT NULL,
     CONSTRAINT `managementserver_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_cluster` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `description` longtext NOT NULL,
    `tipc_address` integer UNSIGNED NOT NULL UNIQUE,
    `dhcp_lifetime` datetime not null default "1970-01-01 00:00:00",
    `management_server_id` smallint unsigned NOT NULL,
    `mac_lowest` varchar(18) NOT NULL UNIQUE,
    `mac_highest` varchar(18) NOT NULL UNIQUE,
    CONSTRAINT `cluster_2_managementserver` FOREIGN KEY (`management_server_id`) REFERENCES `dmt_managementserver` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_networkinterface` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mac_address` varchar(18) NOT NULL UNIQUE,
    `server_id` integer unsigned NOT NULL,
    CONSTRAINT `networkinterface_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_ipaddress` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `address` char(39) NOT NULL UNIQUE,
    `netmask` char(39) NOT NULL,
    `gateway_address` varchar(20) NOT NULL,
    `nic_id` integer unsigned NOT NULL,
    CONSTRAINT `ipaddress_2_networkinterface` FOREIGN KEY (`nic_id`) REFERENCES `dmt_networkinterface` (`id`)
) ENGINE=InnoDB;


CREATE TABLE `dmt_clusterserver` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `node_type` varchar(5) NOT NULL,
    `server_id` integer unsigned NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `clusterserver_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`),
    CONSTRAINT `clusterserver_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_multicast` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `messaging_group_address` char(39) NOT NULL UNIQUE,
    `messaging_group_port` integer UNSIGNED NOT NULL UNIQUE,
    `udp_mcast_address` char(39) NOT NULL UNIQUE,
    `udp_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `mping_mcast_address` char(39) NOT NULL UNIQUE,
    `mping_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `multicast_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;


CREATE TABLE `dmt_ilo` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ilo_address` varchar(50) NOT NULL,
    `server_id` integer unsigned NOT NULL UNIQUE,
    `username` varchar(10),
    `password` varchar(50),
    CONSTRAINT `ilo_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_apptemplate` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `desc` longtext
) ENGINE=InnoDB;

CREATE TABLE `dmt_apphost` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `template_id` smallint UNSIGNED NOT NULL,
    `name` varchar(30) NOT NULL,
    `hostname` varchar(30) NOT NULL,
    `type` varchar(20) NOT NULL,
    CONSTRAINT `apphost_2_apptemplate` FOREIGN KEY (`template_id`) REFERENCES `dmt_apptemplate` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_appipaddress` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `value` varchar(30) NOT NULL,
    `mode` varchar(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_apphostipmap` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `apphost_id` smallint UNSIGNED NOT NULL,
    `ip_addr_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `apphostipmap_2_apphost` FOREIGN KEY (`apphost_id`) REFERENCES `dmt_apphost` (`id`),
    CONSTRAINT `apphostipmap_2_ipaddress` FOREIGN KEY (`ip_addr_id`) REFERENCES `dmt_appipaddress` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_kgbappinstance` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `template_id` smallint UNSIGNED NOT NULL,
    `aut_id` integer UNSIGNED NOT NULL,
    `state` varchar(20) NOT NULL,
    `comment` longtext,
    `vappid` varchar(100) NOT NULL,
    CONSTRAINT `kgbappinstance_2_apptemplate` FOREIGN KEY (`template_id`) REFERENCES `dmt_apptemplate` (`id`),
    CONSTRAINT `kgbappinstance_2_cireports_packagerevision` FOREIGN KEY (`aut_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB;

-- END 1.1.3

-- END 1.1.4

-- END 1.1.5

ALTER TABLE cireports_packagerevision CHANGE COLUMN `autodrop` `autodrop` varchar(100) default " " NOT NULL AFTER version;

-- END 1.1.6

-- END 1.1.7

CREATE TABLE `cireports_pri` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY ,
    `pkgver_id` integer  UNSIGNED NOT NULL ,
    `fault_id` varchar(50) NOT NULL ,
    `fault_desc` longtext NOT NULL,
    `fault_type` varchar(50) NOT NULL,
    `drop_id` smallint UNSIGNED,
    `status` varchar(50) NOT NULL,
    `priority` varchar(50) NOT NULL,
    `comment` varchar(500) NOT NULL,
    CONSTRAINT `package_2_pri` FOREIGN KEY (`pkgver_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `drop_2_pri` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_multicastports` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `container` integer UNSIGNED NOT NULL,
    `messaging_group_port` integer UNSIGNED NOT NULL,
    `management_port_base` integer UNSIGNED NOT NULL,
    `management_port_native` integer UNSIGNED NOT NULL,
    `public_port_base` integer UNSIGNED NOT NULL,
    `cluster_server_id` integer unsigned NOT NULL,
    CONSTRAINT `imulticastport_2_cluster_server` FOREIGN KEY (`cluster_server_id`) REFERENCES `dmt_clusterserver` (`id`)
) ENGINE=InnoDB;

ALTER TABLE dmt_multicast DROP messaging_group_port;

-- END 1.1.8

-- END 1.1.9

-- END 1.1.10

-- END 1.1.11

-- END 1.1.12

-- END 1.1.13
ALTER TABLE cireports_pri ADD COLUMN `first_pkgver_id` integer  UNSIGNED AFTER pkgver_id;
ALTER TABLE cireports_pri ADD CONSTRAINT `first_package_2_pri` FOREIGN KEY (`first_pkgver_id`) REFERENCES `cireports_packagerevision` (`id`);

-- END 1.1.14

-- END 1.1.15
-- Visualisation Tables (FEM)

CREATE TABLE `fem_job` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `fem_view` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `fem_jobviewmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `job_id` integer UNSIGNED NOT NULL,
    `view_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `job_2_fem` FOREIGN KEY (`job_id`) REFERENCES `fem_job` (`id`),
    CONSTRAINT `view_2_fem` FOREIGN KEY (`view_id`) REFERENCES `fem_view` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `fem_jobresult` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `job_id` integer UNSIGNED NOT NULL,
    `buildId` integer UNSIGNED NOT NULL,
    `status` varchar(10) NOT NULL,
    `passed` bool NOT NULL,
    `failed` bool NOT NULL,
    `unstable` bool NOT NULL,
    `aborted` bool NOT NULL,
    `url` varchar(200) NOT NULL,
    `info` varchar(100) NOT NULL,
    `finished` datetime,
    `finished_ts` bigint UNSIGNED ,
    CONSTRAINT `jobres_2_fem` FOREIGN KEY (`job_id`) REFERENCES `fem_job` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `fem_cachetable` (
    `url` varchar(255) NOT NULL PRIMARY KEY,
    `data` longtext NOT NULL,
    `inserted` datetime
) ENGINE=InnoDB
;

-- END 1.1.16

-- Move Tushar's column update
ALTER TABLE avs_testcase MODIFY COLUMN tcId varchar(35);

ALTER TABLE dmt_cluster ADD COLUMN `group_id` int(11) NOT NULL AFTER `dhcp_lifetime`;

-- END 1.1.17

-- END 1.1.18

-- END 1.1.19

-- END 1.1.20

-- END 1.1.21

-- END 1.1.22

-- END 1.1.23
ALTER TABLE fem_jobresult ADD COLUMN `duration` bigint UNSIGNED  AFTER `finished_ts`;
--Add new visualation tables for Widgets
CREATE TABLE `vis_widget` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `type` varchar(20) NOT NULL,
    `description` longtext,
    `url` varchar(255) NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `vis_widgetdefinition` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `description` longtext,
    `widget_id` integer UNSIGNED NOT NULL,
    `view_id` integer UNSIGNED NOT NULL,
    `refresh` smallint,
    `granularity` varchar(20) NOT NULL,
    CONSTRAINT `widget_2_widgetDefinition` FOREIGN KEY (`widget_id`) REFERENCES `vis_widget` (`id`),
    CONSTRAINT `widget_2_view` FOREIGN KEY (`view_id`) REFERENCES `fem_view` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `vis_widgetrender` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `description` longtext,
    `existing_Chart_Sequence` varchar(20) NOT NULL,
    `widgetDefinition` varchar(20) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `vis_widgetdefinitiontorendermapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `widgetdefinition_id` integer UNSIGNED NOT NULL,
    `widgetrender_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `widgetmapping_2_widgetdefinition` FOREIGN KEY (`widgetdefinition_id`) REFERENCES `vis_widgetdefinition` (`id`),
    CONSTRAINT `widgetmapping_2_widgetrender` FOREIGN KEY (`widgetrender_id`) REFERENCES `vis_widgetrender` (`id`)
) ENGINE=InnoDB
;
-- End addition of new visualation tables for Widgets

-- The following commands were run into the CIFWK Live Hub DB as schema to test during upgrade does not include Django Tables
-- ALTER TABLE auth_user ENGINE=InnoDB;
-- ALTER TABLE auth_group ENGINE=InnoDB;
-- ALTER TABLE auth_permission ENGINE=InnoDB;
-- ALTER TABLE auth_group_permissions ENGINE=InnoDB;
-- ALTER TABLE auth_user_groups ENGINE=InnoDB;
-- ALTER TABLE auth_user_user_permissions ENGINE=InnoDB;
-- ALTER TABLE guardian_groupobjectpermission ENGINE=InnoDB;
-- ALTER TABLE guardian_userobjectpermission ENGINE=InnoDB;

-- END 1.1.24

-- END 1.1.25

-- END 1.1.26

-- END 1.1.27

-- END 1.1.28

ALTER TABLE cireports_package ADD COLUMN `obsolete_after_id` smallint UNSIGNED AFTER `signum`;
ALTER TABLE `cireports_package` ADD CONSTRAINT `pkg_2_drop` FOREIGN KEY (`obsolete_after_id`) REFERENCES `cireports_drop` (`id`);

-- END 1.1.29
ALTER TABLE vis_widgetrender DROP COLUMN existing_chart_sequence;
ALTER TABLE vis_widgetrender DROP COLUMN widgetdefinition;

-- END 1.1.30

-- END 1.1.31

-- END 1.1.32

-- END 1.1.33

-- END 1.1.34

-- END 1.1.35

-- END 1.1.36

-- END 1.1.37

DROP TABLE IF EXISTS `dmt_multicast`;

DROP TABLE IF EXISTS `dmt_multicastports`;

CREATE TABLE `dmt_servicescluster` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_type` varchar(50),
    `name` varchar(50),
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `serviceCluster_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_multicast` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `default_address` char(39) NOT NULL UNIQUE,
    `messaging_group_address` char(39) NOT NULL UNIQUE,
    `udp_mcast_address` char(39) NOT NULL UNIQUE,
    `udp_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `mping_mcast_address` char(39) NOT NULL UNIQUE,
    `mping_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `messaging_group_port` integer UNSIGNED NOT NULL UNIQUE,
    `public_port_base` integer UNSIGNED NOT NULL,
    `service_cluster_id` integer NOT NULL,
    CONSTRAINT `mulicast_2_serviceCluster` FOREIGN KEY (`service_cluster_id`) REFERENCES `dmt_servicescluster` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_servicegroup` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `cluster_type` varchar(50) NOT NULL,
    `node_list` varchar(50) NOT NULL,
    `service_cluster_id` integer NOT NULL,
    CONSTRAINT `serviceGroup_2_servicesCluster` FOREIGN KEY (`service_cluster_id`) REFERENCES `dmt_servicescluster` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_servicegrouppackagemapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `serviceGroup_id` integer NOT NULL,
    `package_id` smallint unsigned NOT NULL,
    CONSTRAINT `serviceGroupPackageMapping_2_serviceGroup` FOREIGN KEY (`serviceGroup_id`) REFERENCES `dmt_servicegroup` (`id`),
    CONSTRAINT `serviceGroupPackageMapping_2_packagepackage` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_serviceinstance` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `service_group_id` integer NOT NULL,
    CONSTRAINT `serviceInstance_2_serviceGroup` FOREIGN KEY (`service_group_id`) REFERENCES `dmt_servicegroup` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_servicegroupinstance` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `service_group_id` integer NOT NULL,
    `Service_Instance_IP` char(39) NOT NULL UNIQUE,
    `netmask` char(39) NOT NULL,
    `gateway` char(39) NOT NULL,
    CONSTRAINT `serviceGroupInstance_2_ServiceGroup` FOREIGN KEY (`service_group_id`) REFERENCES `dmt_servicegroup` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_veritascluster` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `CSG_IP` char(39) NOT NULL UNIQUE,
    `CSG_Netmask` char(39) NOT NULL,
    `CSG_Nic` varchar(10) NOT NULL,
    `GCO_IP` char(39) NOT NULL UNIQUE,
    `GCO_Netmask` char(39) NOT NULL,
    `GCO_Nic` varchar(10) NOT NULL,
    `llt_link_1` varchar(10) NOT NULL,
    `llt_link_2` varchar(10) NOT NULL,
    `llt_link_low_pri_1` varchar(10) NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `veritasCluster_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

-- END 1.1.38
-- Frozen Drop
ALTER TABLE cireports_drop DROP COLUMN `release_date`;
ALTER TABLE cireports_drop ADD COLUMN `planned_release_date` smallint UNSIGNED AFTER `release_id`;
ALTER TABLE cireports_drop ADD COLUMN `actual_release_date` smallint UNSIGNED AFTER `planned_release_date`;

-- END 1.1.39

-- END 1.1.40

-- END 1.1.41

-- END 1.1.42

-- Fix for datetime fields in cireports_drop
ALTER TABLE cireports_drop MODIFY COLUMN `planned_release_date` DATETIME;
ALTER TABLE cireports_drop MODIFY COLUMN `actual_release_date` DATETIME;

-- END 1.1.43
ALTER TABLE cireports_package ADD COLUMN `hide` bool NOT NULL DEFAULT 0;

-- END 1.1.44

-- ISO Tables
CREATE TABLE `cireports_isobuild` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `version`  varchar(100),
    `drop_id` smallint UNSIGNED NOT NULL,
    `build_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT `isobuild_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_isobuildmapping` (
   `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
   `iso_id` smallint UNSIGNED NOT NULL,
   `package_revision_id` integer UNSIGNED NOT NULL,
   `drop_id` smallint UNSIGNED NOT NULL,
   CONSTRAINT `isobuildmapping_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
   CONSTRAINT `isobuildmapping_2_isobuild` FOREIGN KEY (`iso_id`) REFERENCES `cireports_isobuild` (`id`),
   CONSTRAINT `isobuildmapping_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB;


ALTER TABLE dmt_cluster ADD COLUMN `status` varchar(30) NOT NULL default "idle" AFTER `mac_highest`;
ALTER TABLE dmt_cluster ADD COLUMN `status_changed` DATETIME  NOT NULL DEFAULT 0 AFTER `status` ;

CREATE TABLE `dmt_clusterqueue` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateInserted` datetime,
     `clusterGroup` varchar(50)
) ENGINE=InnoDB
;

-- END 1.1.45

-- END 1.1.46
ALTER TABLE dmt_ipaddress ADD COLUMN `external_ip` bool NOT NULL DEFAULT 0;

CREATE TABLE `excellence_organisation` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL UNIQUE,
    `description` longtext,
    `owner` varchar(10) NOT NULL,
    `parent_id` integer UNSIGNED NOT NULL,
    `type` varchar(100) NOT NULL,
    CONSTRAINT `organistation_2_organisation` FOREIGN KEY (`parent_id`) REFERENCES `excellence_organisation` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `excellence_category` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL,
    `version` integer NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `excellence_question` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `question` varchar(1000) NOT NULL,
    `action` varchar(1000) NOT NULL,
    `category_id` integer UNSIGNED NOT NULL,
    `enable` bool NOT NULL,
    `low_level` double precision NOT NULL,
    CONSTRAINT `question_2_category` FOREIGN KEY (`category_id`) REFERENCES `excellence_category` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `excellence_answer` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `answer` varchar(30) NOT NULL,
    `value` integer NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `excellence_questionnaire` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL UNIQUE,
    `organisation_id` integer UNSIGNED NOT NULL,
    `version` integer NOT NULL,
    CONSTRAINT `questionnaire_2_organisation` FOREIGN KEY (`organisation_id`) REFERENCES `excellence_organisation` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `excellence_response` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `questionnaire_id` integer UNSIGNED NOT NULL,
    `dateAndTimeTaken` datetime NOT NULL,
    `takenBy` varchar(30) NOT NULL,
    `questionnairePart` integer NOT NULL,
    CONSTRAINT `response_2_questionnaire` FOREIGN KEY (`questionnaire_id`) REFERENCES `excellence_questionnaire` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `excellence_questionanswerresponsemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `question_id` integer UNSIGNED NOT NULL,
    `answer_id` integer UNSIGNED NOT NULL,
    `response_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `questionanswerresponsemapping_2_question` FOREIGN KEY (`question_id`) REFERENCES `excellence_question` (`id`),
    CONSTRAINT `questionanswerresponsemapping_2_answer` FOREIGN KEY (`answer_id`) REFERENCES `excellence_answer` (`id`),
    CONSTRAINT `questionanswerresponsemapping_2_response` FOREIGN KEY (`response_id`) REFERENCES `excellence_response` (`id`)
) ENGINE=InnoDB
;

-- END 1.1.47

-- END 1.1.48

ALTER TABLE excellence_organisation CHANGE parent_id parent_id integer UNSIGNED;

-- END 1.1.49

-- END 1.1.50

ALTER TABLE excellence_questionnaire CHANGE name questionnaire_Name varchar(30);


-- END 1.1.51

-- END 1.1.52

-- END 1.1.53

-- END 1.1.54

-- END 1.1.55

-- Bug Fix CIP-2409
ALTER TABLE avs_epic CHANGE COLUMN `title` `title` varchar(255) NOT NULL;
ALTER TABLE avs_userstory CHANGE COLUMN `title` `title` varchar(255) NOT NULL;
ALTER TABLE avs_testcase CHANGE COLUMN `title` `title` varchar(255) NOT NULL;

-- END 1.1.56

-- END 1.1.57

-- END 1.2.1
UPDATE dmt_servicescluster set name="LSB Service Cluster" WHERE name="Apache Service Cluster";
UPDATE dmt_servicegroup set cluster_type="LSB Service Cluster" WHERE cluster_type="Apache Service Cluster";
UPDATE dmt_servicegroup set name="httpd" WHERE name="Apache";

-- END 1.2.2

-- END 1.2.3

-- END 1.2.4

-- END 1.2.5

CREATE TABLE `dmt_credentials` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `username` varchar(10) NOT NULL,
    `password` varchar(50) NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `dmt_sfsserver` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `server_id` integer  UNSIGNED NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `sfsServer_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`),
    CONSTRAINT `sfsserver_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustertosfsmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `sfs_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clustertosfsmapping_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `clustertosfsmapping_2_sfsServer` FOREIGN KEY (`sfs_id`) REFERENCES `dmt_sfsserver` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clariion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clariion_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clariionipmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `clariion_id` integer UNSIGNED NOT NULL,
    `ipaddr_id` integer UNSIGNED NOT NULL,
    `ipnumber` integer UNSIGNED NOT NULL,
    CONSTRAINT `clariionipmapping_2_clariion` FOREIGN KEY (`clariion_id`) REFERENCES `dmt_clariion` (`id`),
    CONSTRAINT `clariionipmapping_2_ipaddr` FOREIGN KEY (`ipaddr_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustertoclariionmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `clariion_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clustertoclariionmapping_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `clustertoclariionmapping_2_clariion` FOREIGN KEY (`clariion_id`) REFERENCES `dmt_clariion` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clariiontosfsmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `clariion_id` integer UNSIGNED NOT NULL,
    `sfs_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clariiontosfsmapping_2_clariion` FOREIGN KEY (`clariion_id`) REFERENCES `dmt_clariion` (`id`),
    CONSTRAINT `clariiontosfsmapping_2_sfsServer` FOREIGN KEY (`sfs_id`) REFERENCES `dmt_sfsserver` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_enclosure` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `enclosure_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_enclosureipmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `enclosure_id` integer UNSIGNED NOT NULL,
    `ipaddr_id` integer UNSIGNED NOT NULL,
    `ipnumber` integer UNSIGNED NOT NULL,
    CONSTRAINT `enclosureipmapping_2_clariion` FOREIGN KEY (`enclosure_id`) REFERENCES `dmt_clariion` (`id`),
    CONSTRAINT `enclosureipmapping_2_ipaddr` FOREIGN KEY (`ipaddr_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_bladehardwaredetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mac_address_id` integer UNSIGNED NOT NULL,
    `serial_number` varchar(18) NOT NULL UNIQUE,
    `profile_name` varchar(100) NOT NULL UNIQUE,
    `enclosure_id` integer UNSIGNED NOT NULL,
    `vlan_tag` integer UNSIGNED NOT NULL,
    CONSTRAINT `bladehardwaredetails_2_mac_address` FOREIGN KEY (`mac_address_id`) REFERENCES `dmt_networkinterface` (`id`),
    CONSTRAINT `bladehardwaredetails_2_enclosure` FOREIGN KEY (`enclosure_id`) REFERENCES `dmt_enclosure` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE dmt_ipaddress CHANGE COLUMN `netmask` `netmask` char(39) NULL;
ALTER TABLE dmt_ipaddress CHANGE COLUMN `gateway_address` `gateway_address` varchar(20) NULL;
ALTER TABLE dmt_ipaddress CHANGE COLUMN `nic_id` `nic_id` integer unsigned NULL;
ALTER TABLE dmt_ipaddress CHANGE COLUMN `external_ip` `external_ip` bool NULL DEFAULT 0;

-- END 1.2.6

-- END 1.2.7

-- END 1.2.8

DROP TABLE IF EXISTS `dmt_clustertosfsmapping`;
DROP TABLE IF EXISTS `dmt_clariionipmapping`;
DROP TABLE IF EXISTS `dmt_clustertoclariionmapping`;
DROP TABLE IF EXISTS `dmt_clariiontosfsmapping`;
DROP TABLE IF EXISTS `dmt_enclosureipmapping`;
DROP TABLE IF EXISTS `dmt_sfsserver`;
DROP TABLE IF EXISTS `dmt_clariion`;


CREATE TABLE `dmt_nasserver` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `server_id` integer  UNSIGNED NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `nasServer_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`),
    CONSTRAINT `nasServer_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustertonasmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `nasServer_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clustertonasmapping_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `clustertonasmapping_2_nasServer` FOREIGN KEY (`nasServer_id`) REFERENCES `dmt_nasserver` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_storage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `storage_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_storageipmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `storage_id` integer UNSIGNED NOT NULL,
    `ipaddr_id` integer UNSIGNED NOT NULL,
    `ipnumber` integer UNSIGNED NOT NULL,
    CONSTRAINT `storageipmapping_2_storage` FOREIGN KEY (`storage_id`) REFERENCES `dmt_storage` (`id`),
    CONSTRAINT `storageipmapping_2_ipaddr` FOREIGN KEY (`ipaddr_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustertostoragemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `storage_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clustertostoragemapping_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `clustertostoragemapping_2_storage` FOREIGN KEY (`storage_id`) REFERENCES `dmt_storage` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_storagetonasmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `storage_id` integer UNSIGNED NOT NULL,
    `nasServer_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `storagetonasmapping_2_storage` FOREIGN KEY (`storage_id`) REFERENCES `dmt_storage` (`id`),
    CONSTRAINT `storagetonasmapping_2_nasServer` FOREIGN KEY (`nasServer_id`) REFERENCES `dmt_nasserver` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_enclosureipmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `enclosure_id` integer UNSIGNED NOT NULL,
    `ipaddr_id` integer UNSIGNED NOT NULL,
    `ipnumber` integer UNSIGNED NOT NULL,
    CONSTRAINT `enclosureipmapping_2_enclosure` FOREIGN KEY (`enclosure_id`) REFERENCES `dmt_enclosure` (`id`),
    CONSTRAINT `enclosureipmapping_2_ipaddr` FOREIGN KEY (`ipaddr_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustertodasmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `storage_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clustertodasmapping_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `clustertodasmapping_2_storage` FOREIGN KEY (`storage_id`) REFERENCES `dmt_storage` (`id`)
) ENGINE=InnoDB
;

-- END 1.2.9

CREATE TABLE `cireports_documenttype` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `type` varchar(100) NOT NULL UNIQUE,
    `description` longtext NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `cireports_document` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `document_type_id` integer UNSIGNED NOT NULL,
    `name` varchar(255) NOT NULL,
    `number` varchar(255) NOT NULL,
    `revision` varchar(5) NOT NULL,
    `drop_id` smallint UNSIGNED NOT NULL,
    `deliveryDate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `link` varchar(255) NOT NULL,
    `owner` varchar(50) NOT NULL,
    `comment` longtext,
    CONSTRAINT `document_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `document_2_documenttype` FOREIGN KEY (`document_type_id`) REFERENCES `cireports_documenttype` (`id`)
) ENGINE=InnoDB
;

UPDATE dmt_server set hardware_type='rackmounted' WHERE hostname LIKE 'atmws%' and hardware_type='physical';
UPDATE dmt_server set hardware_type='blade' WHERE hostname LIKE 'atrcxb%' and hardware_type='physical';
ALTER TABLE excellence_questionnaire DROP INDEX name;

-- END 1.2.10

-- END 1.2.11
-- Make the Product Name and Number Unique
ALTER IGNORE TABLE cireports_package ADD UNIQUE (name);
ALTER IGNORE TABLE cireports_package ADD UNIQUE (package_number);

-- END 1.2.12

-- END 1.2.13

-- END 1.2.14

-- END 1.2.15

CREATE TABLE `cireports_product` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL UNIQUE
) ENGINE=InnoDB
;

ALTER TABLE cireports_release ADD COLUMN `product_id` integer UNSIGNED NOT NULL default "1" AFTER `name`;
-- To Add the contstraint from Release tp Product the table id cannot be 0 or empty
INSERT INTO cireports_product(name) VALUES("TOR");
ALTER TABLE cireports_release ADD CONSTRAINT `release_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`);

CREATE TABLE `cireports_testwareartifact` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `artifact_number` varchar(12) NOT NULL UNIQUE,
    `description` varchar(255) NOT NULL,
    `signum` varchar(12) NOT NULL,
    UNIQUE INDEX nameNumber (name, artifact_number)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_testwarerevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testware_artifact_id` smallint UNSIGNED NOT NULL,
    `date_created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `version` varchar(100),
    `groupId` varchar(100),
    `artifactId` varchar(100),
    `obsolete` bool NOT NULL DEFAULT FALSE,
    CONSTRAINT `testware_artifact_revision_2_testware_artifact` FOREIGN KEY (`testware_artifact_id`) REFERENCES `cireports_testwareartifact` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_testwarepackagemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testware_artifact_id` smallint UNSIGNED NOT NULL,
    `package_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `testwarepackagemapping_2_testware_artifact` FOREIGN KEY (`testware_artifact_id`) REFERENCES `cireports_testwareartifact` (`id`),
    CONSTRAINT `testwarepackagemapping_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;


-- END 1.2.16

-- END 1.2.17

-- END 1.2.18

-- END 1.2.19
CREATE TABLE `dmt_nasstoragedetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `nasPoolName` varchar(30) NOT NULL,
    `storageAdministrator` varchar(20) NOT NULL,
    `storageObserver` varchar(20) NOT NULL,
    `storageCluster` varchar(20) NOT NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `nasstoragedetails_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

UPDATE dmt_servicegroupinstance set name='su_0' WHERE name LIKE 'si_0';
UPDATE dmt_servicegroupinstance set name='su_1' WHERE name LIKE 'si_1';
UPDATE dmt_servicegroupinstance set name='su_2' WHERE name LIKE 'si_2';
UPDATE dmt_servicegroupinstance set name='su_3' WHERE name LIKE 'si_3';
UPDATE dmt_servicescluster set name='MCUI' WHERE name LIKE 'jee_asgard';
UPDATE dmt_servicescluster set name='FMPMMS' WHERE name LIKE 'jee_tor';
UPDATE dmt_servicescluster set name='SSO' WHERE name LIKE 'jee_torSSO';
UPDATE dmt_servicegroup set name='MSFM' WHERE name LIKE 'FMMed';
UPDATE dmt_servicegroup set name='MSPM' WHERE name LIKE 'FMServ';
UPDATE dmt_servicegroup set name='MSPM_ADD' WHERE name LIKE 'PMMed';
UPDATE dmt_servicegroup set name='FMPMServ' WHERE name LIKE 'PMServ';
UPDATE dmt_servicegroup set name='UI' WHERE name LIKE 'UIServ';
UPDATE dmt_servicegroup set name='MedCore' WHERE name LIKE 'Asgard';
UPDATE dmt_servicegroup set name='SSO' WHERE name LIKE 'OpAm';
UPDATE dmt_servicegroup set cluster_type='FMPMMS' WHERE cluster_type LIKE 'jee_tor';
UPDATE dmt_servicegroup set cluster_type='MCUI' WHERE cluster_type LIKE 'jee_asgard';
UPDATE dmt_servicegroup set cluster_type='SSO' WHERE cluster_type LIKE 'jee_torSSO';
UPDATE dmt_servicegroup set cluster_type='MCUI' WHERE name LIKE 'UI';

-- END 1.2.20

-- END 1.2.21

-- dependency modelling tables
CREATE TABLE `depmodel_dependencytype` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `desc` longtext
)
;
CREATE TABLE `depmodel_dependency` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `packagerev_from_id` integer UNSIGNED NOT NULL,
    `package_to_id` smallint UNSIGNED NOT NULL,
    `packagerev_to_min_id` integer UNSIGNED,
    `packagerev_to_max_id` integer UNSIGNED,
    `type_id` integer NOT NULL,
    CONSTRAINT `packagerev_from_id_2_packagerevision` FOREIGN KEY (`packagerev_from_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `package_to_min_id_2_packagerevision` FOREIGN KEY (`packagerev_to_min_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `package_to_max_id_2_packagerevision` FOREIGN KEY (`packagerev_to_max_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `package_to_id_2_package` FOREIGN KEY (`package_to_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `type_id_2_type` FOREIGN KEY (`type_id`) REFERENCES `depmodel_dependencytype` (`id`)
)
;

CREATE TABLE `depmodel_javapackage` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_name` varchar(255) NOT NULL,
    `provided_by_id` smallint unsigned,
    CONSTRAINT `provided_by_id_2_package` FOREIGN KEY (`provided_by_id`) REFERENCES `cireports_package` (`id`)
)
;

CREATE TABLE `depmodel_staticdependency` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer unsigned NOT NULL,
    `java_package_id` integer NOT NULL,
    CONSTRAINT `package_revision_id_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `java_package_id_2-javapackage` FOREIGN KEY (`java_package_id`) REFERENCES `depmodel_javapackage` (`id`)
)
;

ALTER TABLE dmt_credentials ADD COLUMN `credentialType` char(20);
CREATE TABLE `excellence_discussionitems` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `comment` longtext
) ENGINE=InnoDB
;

ALTER TABLE excellence_questionanswerresponsemapping ADD COLUMN `comment_id` integer UNSIGNED NOT NULL default "1" AFTER `answer_id`;
INSERT INTO excellence_discussionitems(comment) VALUES("Initail Comment");
ALTER TABLE excellence_questionanswerresponsemapping ADD CONSTRAINT `questionanswerresponsemapping_2_comment` FOREIGN KEY (`comment_id`) REFERENCES `excellence_discussionitems` (`id`);

-- END 1.2.22
ALTER TABLE dmt_managementserver ADD COLUMN `product_id` integer UNSIGNED NOT NULL default "1";
ALTER TABLE dmt_managementserver ADD CONSTRAINT `product_2_managementserver` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`);

CREATE TABLE `dmt_producttoservertypemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `serverType` varchar(50) NOT NULL,
    CONSTRAINT `product_2_servertype` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE `dmt_clusterserver` MODIFY `node_type` varchar(50);

CREATE TABLE `dmt_ossrcclustertotorclustermapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `torCluster_id` smallint UNSIGNED NOT NULL,
    `ossCluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `ossrc_2_tor` FOREIGN KEY (`torcluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `tor_2_ossrc` FOREIGN KEY (`ossCluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

-- The following commands were run into the CIFWK Live Hub DB as schema to test during upgrade does not include live data
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'SC-1');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'SC-2');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'PL-3');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'PL-4');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'UAS1');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'UAS2');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'ADMIN1');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'ADMIN2');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'Admin Shared Cluster IPS');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'OMBS Backup Server');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'OAM Service Primary');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'OAM Service Secondary');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'OMSAS');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'NEDSS');
-- INSERT INTO dmt_producttoservertypemapping (product_id, serverType) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'EBAS');

CREATE TABLE `dmt_ssodetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `ldapDomain` varchar(100),
    `ldapPassword` varchar(100),
    `ossFsServer` varchar(100),
    CONSTRAINT `ssodetails_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE cireports_packagerevision CHANGE rdc_test cdb_test varchar(20) NOT NULL default "not_started";
ALTER TABLE cireports_packagerevision ADD COLUMN `cid_test` varchar(20) NOT NULL default "not_started" AFTER `cdb_test`;

-- END 1.3.1

-- END 1.3.2

ALTER TABLE dmt_bladehardwaredetails DROP INDEX profile_name;

CREATE TABLE `dmt_installgroup` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `installGroup` varchar(50) NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustertoinstallgroupmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `group_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cluster_2_installgroup` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `group_2_installgroup` FOREIGN KEY (`group_id`) REFERENCES `dmt_installgroup` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE avs_epic CHANGE COLUMN `title` `title` longtext NOT NULL;
ALTER TABLE avs_userstory CHANGE COLUMN `title` `title` longtext NOT NULL;
ALTER TABLE avs_testcase CHANGE COLUMN `title` `title` longtext NOT NULL;
ALTER TABLE avs_testcase CHANGE COLUMN `groups` `groups` longtext;
ALTER TABLE avs_testcase CHANGE COLUMN `pre` `pre` longtext;
ALTER TABLE avs_testcase CHANGE COLUMN `desc` `desc` longtext NOT NULL;

ALTER TABLE cireports_release ADD COLUMN `iso_artifact` varchar(50) AFTER `product_id`;

-- END 1.3.3

CREATE TABLE `fwk_glossary` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE,
    `description` longtext
) ENGINE=InnoDB
;

CREATE TABLE `cireports_femlink` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `name` varchar(50) NOT NULL,
    `fem_link` varchar(200) NOT NULL,
    CONSTRAINT `femlinks_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;

-- END 1.3.4
CREATE TABLE `cireports_testresults` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `passed` smallint UNSIGNED ,
    `failed` smallint UNSIGNED ,
    `total` smallint UNSIGNED ,
    `phase` varchar(20),
    `tag` varchar(100),
    `testdate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `test_report` longtext

) ENGINE=InnoDB
;

CREATE TABLE `cireports_testresultstotestwaremap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `package_id` smallint UNSIGNED NOT NULL,
    `testware_revision_id` integer UNSIGNED NOT NULL,
    `testware_artifact_id` smallint UNSIGNED NOT NULL,
    `testware_run_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `testmap_2_testware_artifact_revision` FOREIGN KEY (`testware_revision_id`) REFERENCES `cireports_testwarerevision` (`id`),
    CONSTRAINT `testmap_2_testware_artifact` FOREIGN KEY (`testware_artifact_id`) REFERENCES `cireports_testwareartifact` (`id`),
    CONSTRAINT `test_2_package_revision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `test_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `testmap_2_testware_results` FOREIGN KEY (`testware_run_id`) REFERENCES `cireports_testresults` (`id`)
) ENGINE=InnoDB
;

-- END 1.3.5

-- END 1.3.6
ALTER TABLE dmt_ipaddress change netmask bitmask varchar (15) NULL;
UPDATE dmt_ipaddress set bitmask='23' WHERE bitmask LIKE '255.255.254.0';
UPDATE dmt_ipaddress set bitmask='22' WHERE bitmask LIKE '255.255.252.0';
UPDATE dmt_ipaddress set bitmask='21' WHERE bitmask LIKE '255.255.248.0';
UPDATE dmt_ipaddress set bitmask='24' WHERE bitmask LIKE '255.255.255.0';
UPDATE dmt_ipaddress set bitmask='16' WHERE bitmask LIKE '255.255.0.0';
UPDATE dmt_ipaddress set bitmask='8' WHERE bitmask LIKE '255.0.0.0';
UPDATE dmt_ipaddress set bitmask='22' WHERE bitmask LIKE '10.45.236.1';
ALTER TABLE dmt_ipaddress change bitmask bitmask varchar (4) NULL;

ALTER TABLE dmt_ipaddress ADD COLUMN `ipv6_address` char(39) UNIQUE AFTER `bitmask`;
ALTER TABLE dmt_ipaddress ADD COLUMN `ipv6_bitmask` varchar(4) AFTER `ipv6_address`;

ALTER TABLE dmt_veritascluster change CSG_Netmask CSG_Bitmask varchar (15) NOT NULL;
UPDATE dmt_veritascluster set CSG_Bitmask='23' WHERE CSG_Bitmask LIKE '255.255.254.0';
UPDATE dmt_veritascluster set CSG_Bitmask='22' WHERE CSG_Bitmask LIKE '255.255.252.0';
UPDATE dmt_veritascluster set CSG_Bitmask='21' WHERE CSG_Bitmask LIKE '255.255.248.0';
UPDATE dmt_veritascluster set CSG_Bitmask='24' WHERE CSG_Bitmask LIKE '255.255.255.0';
UPDATE dmt_veritascluster set CSG_Bitmask='16' WHERE CSG_Bitmask LIKE '255.255.0.0';
UPDATE dmt_veritascluster set CSG_Bitmask='8' WHERE CSG_Bitmask LIKE '255.0.0.0';
ALTER TABLE dmt_veritascluster change CSG_Bitmask CSG_Bitmask integer UNSIGNED NOT NULL;

ALTER TABLE dmt_veritascluster change GCO_Netmask GCO_Bitmask varchar (15) NOT NULL;
UPDATE dmt_veritascluster set GCO_Bitmask='23' WHERE GCO_Bitmask LIKE '255.255.254.0';
UPDATE dmt_veritascluster set GCO_Bitmask='22' WHERE GCO_Bitmask LIKE '255.255.252.0';
UPDATE dmt_veritascluster set GCO_Bitmask='21' WHERE GCO_Bitmask LIKE '255.255.248.0';
UPDATE dmt_veritascluster set GCO_Bitmask='24' WHERE GCO_Bitmask LIKE '255.255.255.0';
UPDATE dmt_veritascluster set GCO_Bitmask='16' WHERE GCO_Bitmask LIKE '255.255.0.0';
UPDATE dmt_veritascluster set GCO_Bitmask='8' WHERE GCO_Bitmask LIKE '255.0.0.0';
ALTER TABLE dmt_veritascluster change GCO_Bitmask GCO_Bitmask integer UNSIGNED NOT NULL;

ALTER TABLE dmt_servicegroupinstance change netmask bitmask varchar (15) NOT NULL;
UPDATE dmt_servicegroupinstance set bitmask='23' WHERE bitmask LIKE '255.255.254.0';
UPDATE dmt_servicegroupinstance set bitmask='22' WHERE bitmask LIKE '255.255.252.0';
UPDATE dmt_servicegroupinstance set bitmask='22' WHERE bitmask LIKE '192.162.150.0';
UPDATE dmt_servicegroupinstance set bitmask='21' WHERE bitmask LIKE '255.255.248.0';
UPDATE dmt_servicegroupinstance set bitmask='24' WHERE bitmask LIKE '255.255.255.0';
UPDATE dmt_servicegroupinstance set bitmask='16' WHERE bitmask LIKE '255.255.0.0';
UPDATE dmt_servicegroupinstance set bitmask='8' WHERE bitmask LIKE '255.0.0.0';
ALTER TABLE dmt_servicegroupinstance change bitmask bitmask integer UNSIGNED NOT NULL;

ALTER TABLE dmt_nasstoragedetails ADD COLUMN `nasPoolId` varchar(10) NOT NULL AFTER `nasPoolName`;

-- END 1.3.7

-- END 1.3.8

ALTER TABLE cireports_pri ADD COLUMN `node_pri` bool NOT NULL DEFAULT 1 AFTER `priority`;
UPDATE cireports_pri SET node_pri=1;

ALTER TABLE dmt_ipaddress change external_ip ipType varchar (50) NULL;
UPDATE dmt_ipaddress set ipType='other' WHERE ipType='0';
UPDATE dmt_ipaddress set ipType='host' WHERE ipType='1';

ALTER TABLE dmt_nasstoragedetails change nasPoolName sanPoolName varchar (30) NOT NULL;
ALTER TABLE dmt_nasstoragedetails change nasPoolId sanPoolId varchar (10) NOT NULL AFTER `id`;
ALTER TABLE dmt_nasstoragedetails ADD COLUMN `poolFS1` varchar (20) NULL AFTER `sanPoolName`;
ALTER TABLE dmt_nasstoragedetails change storageAdministrator fileSystem1 varchar (20) NULL;
ALTER TABLE dmt_nasstoragedetails ADD COLUMN `poolFS2` varchar (20) NULL AFTER `fileSystem1`;
ALTER TABLE dmt_nasstoragedetails change storageObserver fileSystem2 varchar (20) NULL;
ALTER TABLE dmt_nasstoragedetails ADD COLUMN `poolFS3` varchar (20) NULL AFTER `fileSystem2`;
ALTER TABLE dmt_nasstoragedetails change storageCluster fileSystem3 varchar (20) NULL;

-- END 1.3.9

-- END 1.3.10
DROP TABLE IF EXISTS dmt_vlantoipmapping;
ALTER TABLE cireports_packagerevision ADD COLUMN `arm_repo` varchar(30) NOT NULL DEFAULT "releases";

-- END 1.3.11
CREATE TABLE `depmodel_artifact` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `depmodel_artifactversion` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifact_id` integer NOT NULL,
    `groupname` varchar(100) NOT NULL ,
    `version` varchar(100) NOT NULL,
    `m2type` varchar(30) NOT NULL,
    UNIQUE (artifact_id, groupname,version,m2type),
    CONSTRAINT `artifactversion_2_artifact` FOREIGN KEY (`artifact_id`) REFERENCES `depmodel_artifact` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `depmodel_mapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifact_main_version_id` integer NOT NULL,
    `artifact_dep_version_id` integer NOT NULL,
    `scope` varchar(60) NOT NULL,
    UNIQUE (artifact_main_version_id, artifact_dep_version_id,scope),
    CONSTRAINT `main_2_artifactversion` FOREIGN KEY (`artifact_main_version_id`) REFERENCES `depmodel_artifactversion` (`id`),
    CONSTRAINT `dep_2_artifactversion` FOREIGN KEY (`artifact_dep_version_id`) REFERENCES `depmodel_artifactversion` (`id`)
) ENGINE=InnoDB
;

-- END 1.3.12

-- END 1.3.13

CREATE TABLE `dmt_vlanipmapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `vlanTag` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `vlan_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

-- END 1.3.14

CREATE TABLE `cireports_clue` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint UNSIGNED NOT NULL,
    `codeReview` varchar(20) NOT NULL,
    `codeReviewTime` datetime NOT NULL,
    `unit` varchar(20) NOT NULL,
    `unitTime` datetime NOT NULL,
    `acceptance` varchar(20) NOT NULL,
    `acceptanceTime` datetime NOT NULL,
    `release` varchar(20) NOT NULL,
    `releaseTime` datetime NOT NULL,
    CONSTRAINT `clue_2_pkg` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_cluetrend` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint UNSIGNED NOT NULL,
    `codeReview` varchar(20) NOT NULL,
    `codeReviewTime` datetime NOT NULL,
    `unit` varchar(20) NOT NULL,
    `unitTime` datetime NOT NULL,
    `acceptance` varchar(20) NOT NULL,
    `acceptanceTime` datetime NOT NULL,
    `release` varchar(20) NOT NULL,
    `releaseTime` datetime NOT NULL,
    `lastUpdate` datetime NOT NULL,
    CONSTRAINT `cluetrend_2_pkg` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;


CREATE TABLE `cireports_testsinprogress` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `phase` varchar(20),
    `datestarted` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT `testsinprogress_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_hbvlandetails` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hbAVlan` integer NOT NULL,
    `hbBVlan` integer NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `cluster_2_vlanhbtag` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

-- END 1.3.15

-- END 1.3.16

-- END 1.3.17

ALTER TABLE cireports_packagerevision ADD UNIQUE INDEX grpArtVerArm (groupId, artifactId, version, arm_repo);

ALTER TABLE `cireports_clue` MODIFY COLUMN `codeReview` varchar(20) NULL;
ALTER TABLE `cireports_clue` MODIFY COLUMN `codeReviewTime` datetime NULL;
ALTER TABLE `cireports_clue` MODIFY COLUMN `unit` varchar(20) NULL;
ALTER TABLE `cireports_clue` MODIFY COLUMN `unitTime` datetime NULL;
ALTER TABLE `cireports_clue` MODIFY COLUMN `acceptance` varchar(20) NULL;
ALTER TABLE `cireports_clue` MODIFY COLUMN `acceptanceTime` datetime NULL;
ALTER TABLE `cireports_clue` MODIFY COLUMN `release` varchar(20) NULL;
ALTER TABLE `cireports_clue` MODIFY COLUMN `releaseTime` datetime NULL;

DROP TABLE IF EXISTS `cireports_cluetrend`;

CREATE TABLE `cireports_cluetrend` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint UNSIGNED NOT NULL,
    `codeReview` varchar(20) NULL,
    `codeReviewTimeStarted` datetime NULL,
    `codeReviewTimeFinished` datetime NULL,
    `unit` varchar(20) NULL,
    `unitTimeStarted` datetime NULL,
    `unitTimeFinished` datetime NULL,
    `acceptance` varchar(20) NULL,
    `acceptanceTimeStarted` datetime NULL,
    `acceptanceTimeFinished` datetime NULL,
    `release` varchar(20) NULL,
    `releaseTimeStarted` datetime NULL,
    `releaseTimeFinished` datetime NULL,
    `lastUpdate` datetime NULL,
    CONSTRAINT `cluetrend_2_pkg` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;

-- END 1.3.18

ALTER TABLE cireports_document ADD COLUMN `author` varchar(255) NOT NULL DEFAULT "";
ALTER TABLE cireports_document ADD COLUMN `cpi` bool NOT NULL DEFAULT FALSE;

ALTER TABLE cireports_release ADD COLUMN `track` varchar(20) NOT NULL AFTER `name`;
UPDATE cireports_release SET track="13B"  WHERE name="TOR1.0";
UPDATE cireports_release SET track="14A"  WHERE name="TOR2.0";
UPDATE cireports_release SET track="14B"  WHERE name="TOR3.0";

-- END 1.3.19

ALTER TABLE dmt_ipaddress ADD COLUMN `ipv6_gateway` char(39) NULL AFTER `ipv6_bitmask`;

-- END 1.3.20

-- END 1.3.21
CREATE TABLE `dmt_clustertodasnasmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `dasNasServer_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clustertodasnasmapping_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `clustertodasnasmapping_2_dasNasServer` FOREIGN KEY (`dasNasServer_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB
;

DROP TABLE IF EXISTS dmt_storagetonasmapping;

-- END 1.3.22

-- END 1.4.1

-- END 1.4.2

-- END 1.4.3

-- END 1.4.4

-- END 1.4.5

-- END 1.4.6

-- END 1.4.7

-- END 1.4.8

ALTER TABLE cireports_packagerevision ADD COLUMN `platform` varchar(30) NULL;

ALTER TABLE cireports_product ADD COLUMN `pkgName` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `pkgNumber` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `pkgVersion` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `pkgRState` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `platform` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `intendedDrop` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `deliveredTo` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `date` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `prototypeBuild` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `kgbTests` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `cidTests` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `cdbTests` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `isoIncludedIn` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `deliver` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `pri` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `obsolete` bool NOT NULL DEFAULT 1;
ALTER TABLE cireports_product ADD COLUMN `dependencies` bool NOT NULL DEFAULT 1;

-- END 1.4.9

-- END 1.4.10

-- END 1.4.11

ALTER TABLE cireports_packagerevision DROP INDEX grpArtVerArm;
ALTER TABLE cireports_packagerevision ADD UNIQUE INDEX grpArtVerPlatArm (groupId, artifactId, version, platform, arm_repo);

-- END 1.4.12

ALTER TABLE cireports_release ADD COLUMN `iso_groupId` varchar(100) NOT NULL DEFAULT "com.ericsson.nms";
ALTER TABLE cireports_release ADD COLUMN `iso_arm_repo` varchar(30) NOT NULL DEFAULT "releases";
ALTER TABLE cireports_isobuild ADD UNIQUE INDEX versionDrop (version, drop_id);

-- END 1.4.13

-- END 1.4.14

CREATE TABLE `cireports_testresultswithouttestware` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `package_id` smallint UNSIGNED NOT NULL,
    `testware_run_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `testresults_2_package_revision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `testresults_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `testresults_2_testware_results` FOREIGN KEY (`testware_run_id`) REFERENCES `cireports_testresults` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE cireports_testresults ADD COLUMN `test_report_directory` varchar(100) NULL;

CREATE TABLE `cireports_cdbtypes` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL UNIQUE
)ENGINE=InnoDB;

CREATE TABLE `cireports_cdb` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` smallint UNSIGNED NOT NULL,
    `type_id` smallint UNSIGNED NOT NULL,
    `status` varchar(20) NOT NULL,
    `started` datetime,
    `lastUpdated` datetime,
    `report` longtext,
    CONSTRAINT `cdb_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `cdb_2_cdbtype` FOREIGN KEY (`type_id`) REFERENCES `cireports_cdbtypes` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cdbhistory` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` smallint UNSIGNED NOT NULL,
    `type_id` smallint UNSIGNED NOT NULL,
    `status` varchar(20) NOT NULL,
    `started` datetime,
    `lastUpdated` datetime,
    `report` longtext,
    `parent_id` integer UNSIGNED,
    CONSTRAINT `cdbhistory_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `cdbhistory_2_cdbtype` FOREIGN KEY (`type_id`) REFERENCES `cireports_cdbtypes` (`id`),
    CONSTRAINT `cdbhistory_2_cdbhistory` FOREIGN KEY (`parent_id`) REFERENCES `cireports_cdbhistory` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cdbpkgmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cdbHist_id` integer UNSIGNED NOT NULL,
    `package_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cdbpkgmap_2_cdb` FOREIGN KEY (`cdbHist_id`) REFERENCES `cireports_cdbhistory` (`id`),
    CONSTRAINT `cdbpkgmap_2_pkgrev` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_iprangeitem` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ip_range_item` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_iprange` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ip_range_item_id` integer UNSIGNED NOT NULL,
    `start_ip` char(15) NOT NULL UNIQUE,
    `end_ip` char(15) NOT NULL UNIQUE,
    `gateway` char(15) NULL,
    `bitmask` varchar (2) NULL,
    CONSTRAINT `rangeItem_2_rangeIp` FOREIGN KEY (`ip_range_item_id`) REFERENCES `dmt_iprangeitem` (`id`)
) ENGINE=InnoDB
;

-- source /proj/lciadm100/cifwk/latest/sql/data_migrate/dmtIloDBMigrate.sql
-- source /proj/lciadm100/cifwk/latest/sql/data_migrate/dmtMulticastDBMigrate.sql
-- source /proj/lciadm100/cifwk/latest/sql/data_migrate/dmtServiceUnitDBMigrate.sql
-- source /proj/lciadm100/cifwk/latest/sql/data_migrate/dmtVeritasDBMigrate.sql

-- END 1.4.15

-- END 1.4.16

-- END 1.4.17

-- END 1.4.18


ALTER TABLE cireports_testwarerevision ADD COLUMN `execution_version`  varchar(50);
ALTER TABLE cireports_testwarerevision ADD COLUMN `execution_groupId`  varchar(100);
ALTER TABLE cireports_testwarerevision ADD COLUMN `execution_artifactId`  varchar(100);


CREATE TABLE `cireports_packagedependencymapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint UNSIGNED NOT NULL,
    `dependentPackage_id` smallint UNSIGNED NOT NULL,
    `installOrder` smallint UNSIGNED NOT NULL,
    CONSTRAINT `packagedependencymapping_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `packagedependencymapping_2_packagedependency` FOREIGN KEY (`dependentPackage_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE cireports_product ADD COLUMN `isoDownload` bool NOT NULL DEFAULT 1;

-- END 1.4.19

-- END 1.4.20

ALTER TABLE cireports_packagedependencymapping DROP FOREIGN KEY `packagedependencymapping_2_package`;
ALTER TABLE cireports_packagedependencymapping DROP INDEX `packagedependencymapping_2_package`;
ALTER TABLE cireports_packagedependencymapping DROP FOREIGN KEY `packagedependencymapping_2_packagedependency`;
ALTER TABLE cireports_packagedependencymapping DROP INDEX `packagedependencymapping_2_packagedependency`;
DROP TABLE cireports_packagedependencymapping;

CREATE TABLE `cireports_packagedependencymapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint UNSIGNED NOT NULL,
    `packageRevision_id` integer UNSIGNED NULL,
    `dependentPackage_id` smallint UNSIGNED NOT NULL,
    `dependentPackageRevision_id`  integer UNSIGNED NULL,
    `installOrder` smallint UNSIGNED NOT NULL,
    CONSTRAINT `packagedependencymapping_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `packagedependencymapping_2_packagerevision` FOREIGN KEY (`packageRevision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `packagedependencymapping_2_packagedependency` FOREIGN KEY (`dependentPackage_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `packagedependencymapping_2_packagedependencyrevision` FOREIGN KEY (`dependentPackageRevision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;

-- END 1.4.21
ALTER TABLE dmt_ssodetails ADD COLUMN `citrixFarm` varchar(100) NOT NULL default "MASTERSERVICE" AFTER ossFsServer;

-- END 1.4.22
CREATE TABLE `cireports_states` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `state` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;

ALTER TABLE cireports_isobuildmapping ADD COLUMN `overall_status_id`  smallint UNSIGNED ;
ALTER TABLE cireports_isobuildmapping  ADD CONSTRAINT `status_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`);
ALTER TABLE cireports_isobuild ADD COLUMN `current_status`  varchar(500);
ALTER TABLE cireports_isobuild ADD COLUMN `overall_status_id`  smallint UNSIGNED ;
ALTER TABLE cireports_isobuild  ADD CONSTRAINT `isostatus_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`);

CREATE TABLE `cireports_isotestresultstotestwaremap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `isobuild_id` smallint UNSIGNED NOT NULL,
    `testware_revision_id` integer UNSIGNED NOT NULL,
    `testware_artifact_id` smallint UNSIGNED NOT NULL,
    `testware_run_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `isotestmap_2_testware_artifact_revision` FOREIGN KEY (`testware_revision_id`) REFERENCES `cireports_testwarerevision` (`id`),
    CONSTRAINT `isotestmap_2_testware_artifact` FOREIGN KEY (`testware_artifact_id`) REFERENCES `cireports_testwareartifact` (`id`),
    CONSTRAINT `isotest_2_iso` FOREIGN KEY (`isobuild_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `isotestmap_2_testware_results` FOREIGN KEY (`testware_run_id`) REFERENCES `cireports_testresults` (`id`)
) ENGINE=InnoDB
;

INSERT INTO cireports_states (state) VALUES ("not_started");
INSERT INTO cireports_states (state) VALUES ("in_progress");
INSERT INTO cireports_states (state) VALUES ("passed");
INSERT INTO cireports_states (state) VALUES ("failed");
INSERT INTO cireports_states (state) VALUES ("warning");


-- END 1.4.23

-- END 1.4.24

-- END 1.4.25

-- END 1.4.26

ALTER TABLE cireports_testresults ADD COLUMN `testware_pom_directory` varchar(100);
ALTER TABLE cireports_packagerevision CHANGE `platform` `platform` varchar(30) NOT NULL DEFAULT "None";

-- END 1.4.27

-- END 1.4.28

-- END 1.4.29

ALTER TABLE dmt_multicast ADD COLUMN `default_mcast_port` integer UNSIGNED NULL UNIQUE AFTER ipMapMpingMcastAddress_id;

-- END 1.4.30

ALTER TABLE cireports_testresults ADD COLUMN `host_properties_file` varchar(100);

-- END 1.4.31

-- END 1.4.32

-- END 1.4.33

-- END 1.4.34


-- END 1.4.35

-- END 1.4.36

-- END 1.4.37

-- END 1.4.38

-- END 1.4.39

-- END 2.0.1

-- END 2.0.2

-- END 2.0.3

-- END 2.0.4
CREATE TABLE `cireports_obsoleteinfo` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dpm_id` integer UNSIGNED,
    `signum` varchar(12) NOT NULL,
    `reason` TEXT NOT NULL,
    `time_obsoleted` DATETIME,
    CONSTRAINT `obinfo_2_dpm` FOREIGN KEY (`dpm_id`) REFERENCES `cireports_droppackagemapping` (`id`)
) ENGINE=InnoDB
;


-- END 2.0.5

-- END 2.0.6
ALTER TABLE cireports_release ADD COLUMN `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP() AFTER iso_arm_repo;

-- END 2.0.7

-- END 2.0.8

-- END 2.0.9

-- END 2.0.10

-- END 2.0.11
ALTER TABLE cireports_testwarerevision ADD COLUMN `kgb_status` bool NOT NULL DEFAULT FALSE;
ALTER TABLE cireports_testwarerevision ADD COLUMN `cdb_status` bool NOT NULL DEFAULT FALSE AFTER kgb_status;

-- END 2.0.12
UPDATE cireports_testwarerevision SET kgb_status=1, cdb_status=1;

-- END 2.0.13

-- END 2.0.14

-- Following commands were to fix Bug: CIP-4670 (needed to change smallint to integer)
-- mysqldump cireports cireports_isobuildmapping > cireports_isobuildmapping.sql
-- vi cireports_isobuildmapping.sql
-- Removed the DROP TABLE and CREATE TABLE commands: leaving only the data, save and exit.
-- mysql cireports
-- DROP TABLE cireports_isobuildmapping;
-- CREATE TABLE `cireports_isobuildmapping` (
--   `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
--   `iso_id` smallint UNSIGNED NOT NULL,
--   `package_revision_id` integer UNSIGNED NOT NULL,
--   `drop_id` smallint UNSIGNED NOT NULL,
--   `overall_status_id`  smallint UNSIGNED,

--   CONSTRAINT `isobuildmapping_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
--   CONSTRAINT `isobuildmapping_2_isobuild` FOREIGN KEY (`iso_id`) REFERENCES `cireports_isobuild` (`id`),
--   CONSTRAINT `isobuildmapping_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
--   CONSTRAINT `status_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`)
-- ) ENGINE=InnoDB;
-- exit mysql
-- mysql cireports < cireports_isobuildmapping.sql
-- python /proj/lciadm100/cifwk/latest/django_proj/manage.py syncdb




ALTER TABLE cireports_product MODIFY name VARCHAR(50) NOT NULL UNIQUE;
ALTER TABLE cireports_release MODIFY name VARCHAR(50) NOT NULL;
ALTER TABLE cireports_release MODIFY iso_artifact VARCHAR(100);

-- END 2.0.15

ALTER TABLE cireports_product MODIFY name VARCHAR(50) NOT NULL UNIQUE;
ALTER TABLE cireports_release MODIFY name VARCHAR(50) NOT NULL;
ALTER TABLE cireports_release MODIFY iso_artifact VARCHAR(100);

-- END 2.0.16
ALTER TABLE depmodel_mapping ADD COLUMN `build` bool NOT NULL DEFAULT FALSE;

CREATE TABLE `depmodel_packagedependencies` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` integer UNSIGNED NOT NULL UNIQUE,
    `deppackage` varchar(1000),
    `all` varchar(5000),
   CONSTRAINT `packagedep_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.17

UPDATE cireports_testwarerevision SET execution_version = "NONE" where execution_version IS NULL;
UPDATE cireports_testwarerevision SET execution_groupId = "NONE" where execution_groupId IS NULL;
UPDATE cireports_testwarerevision SET execution_artifactId = "NONE" where execution_artifactId IS NULL;

ALTER TABLE cireports_testwarerevision MODIFY execution_version VARCHAR(50) NOT NULL;
ALTER TABLE cireports_testwarerevision MODIFY execution_groupId VARCHAR(100) NOT NULL;
ALTER TABLE cireports_testwarerevision MODIFY execution_artifactId VARCHAR(100) NOT NULL;

UPDATE cireports_testwarerevision SET obsolete = 1 where execution_version = "NONE";
UPDATE cireports_testwarerevision SET obsolete = 1 where execution_groupId = "NONE";
UPDATE cireports_testwarerevision SET obsolete = 1 where execution_artifactId  = "NONE";

-- END 2.0.18

-- END 2.0.19

-- END 2.0.20

-- END 2.0.21

-- END 2.0.22

-- END 2.0.23

-- END 2.0.24
ALTER TABLE depmodel_packagedependencies ADD COLUMN `jar_dependencies` varchar(5000);
ALTER TABLE depmodel_packagedependencies ADD COLUMN `third_party_dependencies` varchar(5000);

-- END 2.0.25

-- END 2.0.26
CREATE TABLE `cpi_cpisection` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `title` varchar(55) NOT NULL,
    `product_id` integer UNSIGNED NOT NULL,
    `description` varchar(255) NOT NULL,
    `parent_id` integer UNSIGNED,
    `lft` integer UNSIGNED NOT NULL,
    `rght` integer UNSIGNED NOT NULL,
    `tree_id` integer UNSIGNED NOT NULL,
    `level` integer UNSIGNED NOT NULL,
     UNIQUE (`title`,`product_id`),
     CONSTRAINT `cpisection_2_cireports_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`),
     CONSTRAINT `cpisection_2_cpisection` FOREIGN KEY (`parent_id`) REFERENCES `cpi_cpisection` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cpi_cpiidentity` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` smallint UNSIGNED NOT NULL,
    `cpidrop` varchar(50) NOT NULL,
    `title` varchar(100),
    `identity` varchar(50) NOT NULL,
    `rstate` varchar(5) NOT NULL,
    `status` varchar(20),
    `lastModified` datetime,
    `lastBuild` datetime,
    `owner` varchar(50) NOT NULL,
    `firstBuild` datetime,
    `endBuild` datetime,
    UNIQUE (`identity`, `rstate`),
    CONSTRAINT `cpiidentity_2_cireportsdrop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cpi_cpidocument` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `section_id` integer UNSIGNED NOT NULL,
    `docname` varchar(255) NOT NULL,
    `author` varchar(255) NOT NULL,
    `language` varchar(5) NOT NULL,
    `docnumber` varchar(50) NOT NULL,
    `revision` varchar(5) NOT NULL,
    `drop_id` smallint UNSIGNED NOT NULL,
    `cpidrop_id` integer UNSIGNED NOT NULL,
    `deliveryDate` datetime NOT NULL,
    `owner` varchar(50) NOT NULL,
    `comment` longtext,
    UNIQUE (`docnumber`, `drop_id`, `cpidrop_id`),
    CONSTRAINT `cpidocument_2_cpisection` FOREIGN KEY (`section_id`) REFERENCES `cpi_cpisection` (`id`),
    CONSTRAINT `cpidocument_2_cireports_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `cpidocument_2_cpiidentity` FOREIGN KEY (`cpidrop_id`) REFERENCES `cpi_cpiidentity` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.27

-- END 2.0.28

-- END 2.0.29

CREATE TABLE `fem_femurls` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `url` varchar(255) NOT NULL
) ENGINE=InnoDB;

-- END 2.0.30

-- END 2.0.31

-- END 2.0.32

-- END 2.0.33

-- END 2.0.34

-- END 2.0.35

-- END 2.0.36

-- END 2.0.37

-- END 2.0.38

-- END 2.0.39

-- END 2.0.40

-- END 2.0.41

-- END 2.0.42

-- END 2.0.43

-- END 2.0.44

ALTER TABLE depmodel_packagedependencies MODIFY `all` VARCHAR(50000);

CREATE TABLE `cireports_mediaartifact` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `number` varchar(12) NOT NULL UNIQUE,
    `description` varchar(255) NOT NULL,
    `obsoleteAfter_id` SMALLINT UNSIGNED,
    `hide` bool NOT NULL,
    CONSTRAINT `media_2_drop` FOREIGN KEY (`obsoleteAfter_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_productset` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `cireports_productsetrelease` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `number` varchar(12) NOT NULL UNIQUE,
    `release_id` SMALLINT UNSIGNED NOT NULL,
    `productSet_id` SMALLINT UNSIGNED NOT NULL,
    `masterArtifact_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `prodsetrelease_2_release` FOREIGN KEY (`release_id`) REFERENCES `cireports_release` (`id`),
    CONSTRAINT `prodsetrelease_2_prodset` FOREIGN KEY (`productSet_id`) REFERENCES `cireports_productset` (`id`),
    CONSTRAINT `prodsetrelease_2_mediaartifact` FOREIGN KEY (`masterArtifact_id`) REFERENCES `cireports_mediaartifact` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_productsetversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `version` varchar(50) NOT NULL,
    `status_id` SMALLINT UNSIGNED NOT NULL,
    `current_status` varchar(500) NOT NULL,
    `productSetRelease_id` SMALLINT UNSIGNED NOT NULL,
    UNIQUE INDEX verProdSetRel (`version`, `productSetRelease_id`),
    CONSTRAINT `productsetver_2__productsetrelease` FOREIGN KEY (`productSetRelease_id`) REFERENCES `cireports_productsetrelease` (`id`),
    CONSTRAINT `productsetver_2_states` FOREIGN KEY (`status_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_productsetversioncontent` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `productSetVersion_id` integer UNSIGNED NOT NULL,
    `mediaArtifactVersion_id` SMALLINT UNSIGNED NOT NULL,
    `status_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `productsetvercont_2_productsetver` FOREIGN KEY (`productSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`),
    CONSTRAINT `productsetvercont_2_states` FOREIGN KEY (`status_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB
;
ALTER TABLE `cireports_productsetversioncontent` ADD CONSTRAINT `productsetvercont_2_isobuildversion` FOREIGN KEY (`mediaArtifactVersion_id`) REFERENCES `cireports_isobuild` (`id`);

CREATE TABLE `cireports_dropmediaartifactmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mediaArtifactVersion_id` SMALLINT UNSIGNED NOT NULL,
    `drop_id` SMALLINT UNSIGNED NOT NULL,
    `obsolete` bool NOT NULL,
    `released` bool NOT NULL,
    `frozen` bool NOT NULL,
    `dateCreated` datetime NOT NULL,
    `deliveryInfo` longtext,
    CONSTRAINT `dropmediaartifactmapping_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE `cireports_dropmediaartifactmapping` ADD CONSTRAINT `dropmediaartifactmapping_2_isobuildversion` FOREIGN KEY (`mediaArtifactVersion_id`) REFERENCES `cireports_isobuild` (`id`);

ALTER TABLE `cireports_isobuild` ADD COLUMN `groupId` varchar(100) NOT NULL;
ALTER TABLE `cireports_isobuild` ADD COLUMN `arm_repo` varchar(50) NOT NULL;
ALTER TABLE `cireports_isobuild` ADD COLUMN `artifactId` varchar(100) NOT NULL;
ALTER TABLE `cireports_isobuild` ADD COLUMN `mediaArtifact_id` SMALLINT UNSIGNED;
ALTER TABLE `cireports_isobuild` CHANGE COLUMN `drop_id` `drop_id` SMALLINT UNSIGNED;
ALTER TABLE `cireports_isobuild` ADD CONSTRAINT `isobuild_2_mediaartifact` FOREIGN KEY (`mediaArtifact_id`) REFERENCES `cireports_mediaartifact` (`id`);
ALTER TABLE `cireports_isobuild` DROP INDEX versionDrop;
ALTER TABLE `cireports_isobuild` ADD UNIQUE INDEX verGrpArtDrop (version, groupId, artifactId, drop_id);

ALTER TABLE `cireports_release` ADD COLUMN `masterArtifact_id` smallint UNSIGNED AFTER `created`;
ALTER TABLE `cireports_release` ADD CONSTRAINT `release_2_mediaartifact` FOREIGN KEY (`masterArtifact_id`) REFERENCES `cireports_mediaartifact` (`id`);

ALTER TABLE cireports_drop ADD COLUMN `mediaFreezeDate` DATETIME AFTER `actual_release_date`;
ALTER TABLE cireports_productsetrelease ADD COLUMN `updateMasterStatus` boolean not null default 0;

CREATE TABLE `cireports_pstestresultstotestwaremap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_set_version_id` integer UNSIGNED NOT NULL,
    `testware_revision_id` integer UNSIGNED NOT NULL,
    `testware_artifact_id` smallint UNSIGNED NOT NULL,
    `testware_run_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `pstestmap_2_testware_artifact_revision` FOREIGN KEY (`testware_revision_id`) REFERENCES `cireports_testwarerevision` (`id`),
    CONSTRAINT `pstestmap_2_testware_artifact` FOREIGN KEY (`testware_artifact_id`) REFERENCES `cireports_testwareartifact` (`id`),
    CONSTRAINT `pstest_2_psver` FOREIGN KEY (`product_set_version_id`) REFERENCES `cireports_productsetversion` (`id`),
    CONSTRAINT `pstestmap_2_testware_results` FOREIGN KEY (`testware_run_id`) REFERENCES `cireports_testresults` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE cireports_release ADD UNIQUE INDEX releaseProduct (name, product_id);
ALTER TABLE cireports_drop ADD UNIQUE INDEX dropRelease (name, release_id);

ALTER TABLE `cireports_productsetversion` ADD COLUMN `drop_id` SMALLINT UNSIGNED;
ALTER TABLE `cireports_productsetversion` ADD  CONSTRAINT `productsetversion_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`);

CREATE TABLE `cireports_obsoletemediainfo` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dropMediaArtifactMapping_id` integer UNSIGNED,
    `signum` varchar(12) NOT NULL,
    `reason` TEXT NOT NULL,
    `time_obsoleted` DATETIME,
    CONSTRAINT `obinfo_2_dropmediaartifactmapping` FOREIGN KEY (`dropMediaArtifactMapping_id`) REFERENCES `cireports_dropmediaartifactmapping` (`id`)
) ENGINE=InnoDB;


-- END 2.0.45

ALTER TABLE depmodel_packagedependencies MODIFY `all` LONGTEXT;
UPDATE depmodel_mapping SET build=False;
TRUNCATE depmodel_packagedependencies;

-- END 2.0.46
ALTER TABLE cpi_cpiidentity CHANGE cpidrop cpiDrop varchar(50);
ALTER TABLE cpi_cpidocument CHANGE docname docName varchar(255);
ALTER TABLE cpi_cpidocument CHANGE docnumber docNumber varchar(50);

UPDATE depmodel_mapping SET build=False;

-- END 2.0.47

-- END 2.0.48

-- END 2.0.49
ALTER TABLE `cireports_testsinprogress` ADD COLUMN `veLog` varchar(1000) ;

CREATE TABLE `cireports_testresultstovisenginelinkmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `velog` varchar(1000),
    `testware_run_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `velog_2_testware_results` FOREIGN KEY (`testware_run_id`) REFERENCES `cireports_testresults` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE dmt_ssodetails ADD COLUMN `openidmAdminPassword` varchar(100) AFTER `ldapPassword`;
ALTER TABLE dmt_ssodetails ADD COLUMN `openidmMysqlPassword` varchar(100) AFTER `ldapPassword`;
ALTER TABLE dmt_ssodetails ADD COLUMN `securityAdminPassword` varchar(100) AFTER `ldapPassword`;

-- END 2.0.50

-- END 2.0.51

-- END 2.0.52

-- END 2.0.53

-- END 2.0.54

-- END 2.0.55

-- END 2.0.56

-- END 2.0.57

-- END 2.0.58


CREATE TABLE `cireports_nonproductemail` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `area` varchar(100) NOT NULL,
    `email` varchar(100) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `cireports_productemail` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `email` varchar(100) NOT NULL,
    CONSTRAINT `product_id_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;

-- The following block was run against the Live DB after upgrade to populate the cireports_productemail table with data
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="ENM-IP"), 'PDLUCTUREE@pdl.internal.ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'PDLUCTUREE@pdl.internal.ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'PDLMAGNUMC@pdl.internal.ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'PDLTORRVTO@ex1.eemea.ericsson.se');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'alan.lynam@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'shen.shen@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'fiachra.hanrahan@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="SON-PM"), 'john.edward.o.brien@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="SON-VIS"), 'john.edward.o.brien@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="OSS-RC"), 'PDLOSSRCCI@pdl.internal.ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'sinead.connolly@ammeon.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'ioannis.papaioannou@ammeon.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'fabio.astengo@ammeon.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'colin.wilkinson@ammeon.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'ana.tizon@ammeon.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'deirdre.dowling@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'karl.murphy@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="LITP"), 'kevin.griffin@ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="CI"), 'PDLCIAXISC@pdl.internal.ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="ENIQ-STATS"), 'PDLENIQDEL@ex1.eemea.ericsson.se');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="CSL-MEDIATION"), 'PDLASSUREC@ex1.eemea.ericsson.se');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="COMINF"), 'PDLSSRCINT@ex1.eemea.ericsson.se');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="SECURITY"), 'PDLSRCDESI@ex1.eemea.ericsson.se');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="OM"), 'PDLOSSRCCI@pdl.internal.ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="SOLARIS"), 'PDLMAGNUMC@pdl.internal.ericsson.com');
-- INSERT IGNORE INTO cireports_productemail (product_id, email) VALUES ((SELECT id FROM cireports_product WHERE name="TOR"), 'PDLUCTURED@ex1.eemea.ericsson.se');
-- INSERT IGNORE INTO cireports_nonproductemail (area, email) VALUES ('JIRA_ADMINS', 'arun.jose@ericsson.com');

ALTER TABLE cireports_droppackagemapping ADD COLUMN `deliverer_mail` varchar(100) AFTER `delivery_info`;
ALTER TABLE cireports_droppackagemapping ADD COLUMN `deliverer_name` varchar(50) AFTER `delivery_info`;

-- END 2.0.59

-- END 2.0.60

-- END 2.0.61

ALTER TABLE dmt_server CHANGE dns_server dns_serverA varchar(30);
ALTER TABLE dmt_server ADD COLUMN `dns_serverB` varchar(30) AFTER `dns_serverA`;

-- END 2.0.62
CREATE TABLE `dmt_internalipaddress` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `address` char(39) NOT NULL,
    `bitmask` varchar(4) NULL,
    `ipv6_address` char(39),
    `ipv6_bitmask` varchar(4) NULL,
    `ipv6_gateway` char(39) NULL,
    `gateway_address` varchar(20) NULL,
    `nic_id` integer unsigned  NULL,
    `ipType` varchar(50) NULL,
    CONSTRAINT `internal_ipaddress_2_networkinterface` FOREIGN KEY (`nic_id`) REFERENCES `dmt_networkinterface` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_internalservicegroupinstance` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `service_group_id` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `internalserviceGroupInstance_2_ServiceGroup` FOREIGN KEY (`service_group_id`) REFERENCES `dmt_servicegroup` (`id`),
    CONSTRAINT `internalservicegroupinstance_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_internalipaddress` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_internalvlanipmapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `vlanTag` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `internalvlan_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_internalipaddress` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.63

-- END 2.0.64

-- END 2.0.65

-- END 2.0.66

-- END 2.0.67

-- END 2.0.68

-- END 2.0.69
CREATE TABLE `cireports_primuser` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `signum` varchar(12) NOT NULL
) ENGINE=InnoDB
;


-- END 2.0.70

-- END 2.0.71

-- END 2.0.72

-- END 2.0.73
DROP TABLE `cireports_primuser`;

-- END 2.0.74
CREATE TABLE `dmt_servicegrouptypes` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `group_type` varchar(50) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `dmt_servicegroupunit` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `service_unit` varchar(50) NOT NULL UNIQUE,
    `group_type_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `servicegroupdata_2_servicegrouptypes` FOREIGN KEY (`group_type_id`) REFERENCES `dmt_servicegrouptypes` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_sed` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateInserted` datetime NOT NULL,
    `user` varchar(10) NOT NULL,
    `version` varchar(10) NOT NULL UNIQUE,
    `jiraNumber` varchar(10) NOT NULL,
    `sed` longtext
) ENGINE=InnoDB;

CREATE TABLE `dmt_jbossclusterservicegroup` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_sedmaster` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `identifer` varchar(10) NOT NULL UNIQUE,
    `sedmaster_id` smallint UNSIGNED ,
    `dateupdated` datetime ,
    `seduser` varchar(10) ,
    CONSTRAINT `sedmaster_to_sed` FOREIGN KEY (`sedmaster_id`) REFERENCES `dmt_sed` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.75

-- END 2.0.76

-- END 2.0.77
CREATE TABLE `dmt_databaselocation` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `versantStandAlone` varchar(3) NOT NULL,
    `mysqlStandAlone` varchar(3) NOT NULL,
    `postgresStandAlone` varchar(3) NOT NULL,
    `cluster_id` smallint UNSIGNED,
    CONSTRAINT `dataBaseLocation_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `event_type` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `eventTypeName` varchar(30) NOT NULL,
    `eventTypeDb` varchar(30) NOT NULL,
    `sed` longtext
) ENGINE=InnoDB;
-- END 2.0.78

-- END 2.0.79
INSERT INTO cireports_states (state) VALUES("passed_manual");
INSERT INTO cireports_cdbtypes (name) VALUES("KGB-Ready");

-- END 2.0.80

-- END 2.0.81
DROP TABLE IF EXISTS `event_type`;

CREATE TABLE `metrics_eventtype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `eventTypeName` varchar(50) NOT NULL,
    `eventTypeDb` varchar(50) NOT NULL,
    `description` longtext
) ENGINE=InnoDB;

-- END 2.0.82

-- END 2.0.83

-- END 2.0.84

ALTER TABLE cireports_packagerevision DROP INDEX grpArtVerPlatArm;
ALTER TABLE cireports_packagerevision ADD UNIQUE INDEX grpArtVerPlatArmType (groupId, artifactId, version, platform, arm_repo, m2type);
ALTER TABLE cireports_product ADD COLUMN `type` bool NOT NULL DEFAULT 1 AFTER pkgVersion;

CREATE TABLE `cireports_categories` (
      `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
      `name` varchar(30) NOT NULL UNIQUE
) ENGINE=InnoDB;

INSERT INTO `cireports_categories` (name) VALUES("application");
INSERT INTO `cireports_categories` (name) VALUES("3pp");
INSERT INTO `cireports_categories` (name) VALUES("plugin");

ALTER TABLE `cireports_packagerevision` ADD COLUMN `category_id` smallint UNSIGNED NULL;
ALTER TABLE `cireports_packagerevision` ADD COLUMN `media_path` varchar(250) NULL;
ALTER TABLE `cireports_packagerevision` ADD CONSTRAINT `packagerevision_2_categories` FOREIGN KEY (`category_id`) REFERENCES `cireports_categories` (`id`);

-- END 2.0.85

UPDATE `cireports_categories` SET name="sw" where name="application";
UPDATE `cireports_packagerevision` SET category_id=1;
ALTER TABLE `cireports_product` ADD COLUMN `category` bool NOT NULL DEFAULT 1 AFTER platform;

-- END 2.0.86

-- END 2.0.87

-- END 2.0.88

-- END 2.0.89
ALTER TABLE dmt_networkinterface ADD COLUMN `interface` varchar(5) NOT NULL default "eth0" AFTER mac_address;
ALTER TABLE dmt_ipaddress ADD COLUMN `interface` varchar(5) AFTER gateway_address;

CREATE TABLE `dmt_virtualmanagementserver` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `server_id` integer unsigned NOT NULL,
    `mgtserver_id` smallint unsigned NOT NULL,
    `product_id` integer UNSIGNED NOT NULL default "1",
    CONSTRAINT `virtualmanagementserver_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`),
    CONSTRAINT `virtualmanagementserver_2_managementserver` FOREIGN KEY (`mgtserver_id`) REFERENCES `dmt_managementserver` (`id`),
    CONSTRAINT `product_2_virtualmanagementserver` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE dmt_ipaddress ADD COLUMN `netmask` char(15) AFTER interface;

CREATE TABLE `dmt_hardwaredetails` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ram` varchar(10) NOT NULL,
    `diskSize` varchar(10) NOT NULL,
    `server_id` integer unsigned NOT NULL,
    CONSTRAINT `hardwaredetails_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_hardwareidentity` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `wwpn` varchar(23) NOT NULL,
    `ref` varchar(10) NOT NULL,
    `server_id` integer unsigned NOT NULL,
    CONSTRAINT `hardwareidentity_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.90

-- END 2.0.91
CREATE TABLE `cireports_configproducts` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `choice` varchar(50) NOT NULL,
    `num` smallint UNSIGNED,
    `order_id`  smallint UNSIGNED,
    `active` boolean not null default 1,
     CONSTRAINT `config_product_id` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.92

-- END 2.0.93
CREATE TABLE `dmt_servicegroupcredentialmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `service_group_id` integer NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    `signum` varchar(10) NOT NULL,
    `date_time` timestamp NOT NULL DEFAULT "2012-01-01 00:00:00",
    CONSTRAINT `serviceGroupCredentialMapping_2_serviceGroup` FOREIGN KEY (`service_group_id`) REFERENCES `dmt_servicegroup` (`id`),
    CONSTRAINT `serviceGroupCredentialMapping_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.94

-- END 2.0.95
ALTER TABLE cireports_packagerevision ADD COLUMN `autodeliver` boolean NOT NULL DEFAULT 0 AFTER autodrop;

CREATE TABLE `dmt_managementservercredentialmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mgtserver_id` smallint unsigned NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    `signum` varchar(10) NOT NULL,
    `date_time` timestamp NOT NULL DEFAULT "2012-01-01 00:00:00",
    CONSTRAINT `managementServerCredentialMapping_2_managementServer` FOREIGN KEY (`mgtserver_id`) REFERENCES `dmt_managementserver` (`id`),
    CONSTRAINT `managementServerCredentialMapping_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_virtualmscredentialmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `virtualmgtserver_id` smallint unsigned NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    `signum` varchar(10) NOT NULL,
    `date_time` timestamp NOT NULL DEFAULT "2012-01-01 00:00:00",
    CONSTRAINT `virtualMSCredentialMapping_2_virtualmgtServer` FOREIGN KEY (`virtualmgtserver_id`) REFERENCES `dmt_virtualmanagementserver` (`id`),
    CONSTRAINT `virtualMSCredentialMapping_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clusterservercredentialmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `clusterserver_id` integer unsigned NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    `signum` varchar(10) NOT NULL,
    `date_time` timestamp NOT NULL DEFAULT "2012-01-01 00:00:00",
    CONSTRAINT `clusterServerCredentialMapping_2_clusterserver` FOREIGN KEY (`clusterserver_id`) REFERENCES `dmt_clusterserver` (`id`),
    CONSTRAINT `clusterServerCredentialMapping_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_usertypes` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;

INSERT INTO `dmt_usertypes` (name) VALUES("admin");
INSERT INTO `dmt_usertypes` (name) VALUES("oper");

-- END 2.0.96

-- END 2.0.97
ALTER TABLE dmt_servicegroupinstance  ADD COLUMN `hostname` varchar(30) NULL AFTER name;

-- END 2.0.98

-- END 2.0.99

-- END 2.0.100

-- END 2.0.101

-- END 2.0.102

-- END 2.0.103
ALTER TABLE cireports_femlink ADD COLUMN `FemBaseKGBJobURL` bool NOT NULL DEFAULT 0;

ALTER TABLE cireports_packagerevision DROP FOREIGN KEY packagerevision_2_categories;
UPDATE cireports_packagerevision SET category_id=1 WHERE category_id=0;
UPDATE cireports_packagerevision SET category_id=1 where category_id is NULL;
ALTER TABLE cireports_packagerevision CHANGE category_id category_id smallint UNSIGNED NOT NULL DEFAULT 1;
ALTER TABLE `cireports_packagerevision` ADD CONSTRAINT `packagerevision_2_categories` FOREIGN KEY (`category_id`) REFERENCES `cireports_categories` (`id`);

-- END 2.0.104

-- END 2.0.105

-- END 2.0.106

-- END 2.0.107

-- END 2.0.108

-- END 2.0.109
ALTER TABLE cireports_drop ADD COLUMN `correctionalDrop` bool NOT NULL DEFAULT 0 AFTER `designbase_id`;

-- END 2.0.110

ALTER TABLE cireports_packagerevision ADD COLUMN `isoExclude` boolean NOT NULL DEFAULT 0 AFTER media_path;

INSERT INTO `cireports_categories` (name) VALUES("image");

-- END 2.0.111

-- END 2.0.112
CREATE TABLE `dmt_virtualimageitems` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

INSERT INTO `dmt_virtualimageitems` (name) VALUES("FMServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("PMServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("CMServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("SHMServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("NetEx");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("UIServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("SecServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("MSCM");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("MSFM");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("MSPM");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("WFS");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("SSO");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("SAID");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("ImpExpServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("KPIServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("APServ");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("httpd");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("logstash");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("visinaming");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("opendj");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("openidm");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("visinotify");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("medrouter");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("supervisionclient");
INSERT INTO `dmt_virtualimageitems` (name) VALUES("eventbasedclient");

CREATE TABLE `dmt_virtualimage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `node_list` varchar(50) NOT NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `virtualmachine_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_virtualimageipinfo` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `number` varchar(3) NOT NULL,
    `hostname` varchar(30) NULL,
    `virtual_image_id` integer UNSIGNED NOT NULL,
    `ipMap_id` integer UNSIGNED NULL,
    `ipMapInternal_id` integer UNSIGNED NULL,
    CONSTRAINT `virtualimageipinfo_2_virtualimage` FOREIGN KEY (`virtual_image_id`) REFERENCES `dmt_virtualimage` (`id`),
    CONSTRAINT `virtualimageipinfo_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `virtualimageipinfo_2_ipInternal` FOREIGN KEY (`ipMapInternal_id`) REFERENCES `dmt_internalipaddress` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE dmt_ipaddress CHANGE `address` `address` char(39) UNIQUE;

CREATE TABLE `dmt_virtualimagecredentialmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `signum` varchar(10) NOT NULL,
    `date_time` timestamp NOT NULL DEFAULT "2012-01-01 00:00:00",
    `virtualimage_id` integer UNSIGNED NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `virtualImageCredentialMapping_2_virtualImage` FOREIGN KEY (`virtualimage_id`) REFERENCES `dmt_virtualimage` (`id`),
    CONSTRAINT `vitualImageMapping_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustermulticast` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `enm_messaging_address_id` integer UNSIGNED NOT NULL,
    `udp_multicast_address_id` integer UNSIGNED NOT NULL,
    `enm_messaging_port` integer NOT NULL UNIQUE,
    `udp_multicast_port` integer NOT NULL UNIQUE,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `clustermulicast_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `enmMessagingAddress_2_ip` FOREIGN KEY (`enm_messaging_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `udpMulticastAddress_2_ip` FOREIGN KEY (`udp_multicast_address_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.113

-- END 2.0.114

ALTER TABLE dmt_enclosure ADD COLUMN `vc_credentials_id` integer UNSIGNED NULL;
ALTER TABLE dmt_enclosure ADD CONSTRAINT `vcenclosure_2_credentials` FOREIGN KEY (`vc_credentials_id`) REFERENCES `dmt_credentials` (`id`);

DROP TABLE `dmt_virtualimageitems`;

CREATE TABLE `dmt_virtualimageitems` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE,
    `type` VARCHAR(20) NOT NULL
) ENGINE=InnoDB
;

INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("FMServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("PMServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("CMServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SHMServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("NetEx_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("UIServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SecServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSCM_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSFM_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSPM_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("WFS_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SSO_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SAID_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("ImpExpServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("KPIServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("APServ_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("httpd_1","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("logstash_1","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("visinaming_1","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("opendj_1","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("openidm_1","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("visinotify_1","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("medrouter_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("supervisionclient_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("eventbasedclient_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("elasticsearch_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("FMServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("PMServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("CMServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SHMServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("NetEx_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("UIServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SecServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSCM_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSFM_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSPM_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("WFS_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SSO_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("SAID_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("ImpExpServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("KPIServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("APServ_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("opendj_2","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("openidm_2","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("visinotify_2","httpd");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("medrouter_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("supervisionclient_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("eventbasedclient_2","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSCM_3","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("MSCM_4","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("jms_1","jboss");
INSERT INTO `dmt_virtualimageitems` (name,type) VALUES("jms_2","jboss");

RENAME TABLE dmt_hbvlandetails TO dmt_vlandetails;
ALTER TABLE dmt_vlandetails ADD COLUMN `services_subnet` char(18) NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `services_gateway` char(15) NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `services_ipv6_gateway` char(39) NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `services_ipv6_subnet` varchar(42) NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `storage_subnet` varchar(18) NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `backup_subnet` varchar(18) NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `jgroups_subnet` varchar(18) NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `internal_subnet` varchar(18) NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `storage_vlan` integer NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `backup_vlan` integer NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `jgroups_vlan` integer NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `internal_vlan` integer NOT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `services_vlan` integer NOT NULL;
ALTER TABLE dmt_vlandetails CHANGE `hbAVlan` `hbAVlan` integer NULL;
ALTER TABLE dmt_vlandetails CHANGE `hbBVlan` `hbBVlan` integer NULL;

ALTER TABLE dmt_bladehardwaredetails CHANGE `vlan_tag` `vlan_tag` integer UNSIGNED NULL;

-- END 2.0.115

-- END 2.0.116

-- END 2.0.117
ALTER TABLE dmt_sedmaster CHANGE `identifer` `identifer` varchar(20) NOT NULL UNIQUE;
ALTER table `dmt_sedmaster` add column `sedmaster_virtual_id` smallint UNSIGNED;
ALTER table `dmt_sedmaster` add CONSTRAINT `sedmaster_virtual_to_sed` FOREIGN KEY (`sedmaster_virtual_id`) REFERENCES `dmt_sed` (`id`);

-- END 2.0.118

-- END 2.0.119

-- END 2.0.120

-- END 2.0.121

CREATE TABLE `dmt_virtualconnectnetworks` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `sharedUplinkSetA` varchar(50) NOT NULL default "OSS1_Shared_Uplink_A",
    `sharedUplinkSetB` varchar(50) NOT NULL default "OSS1_Shared_Uplink_B",
    `servicesA` varchar(50) NOT NULL default "ENM_services_A",
    `servicesB` varchar(50) NOT NULL default "ENM_services_B",
    `storageA` varchar(50) NOT NULL default "ENM_storage_A",
    `storageB` varchar(50) NOT NULL default "ENM_storage_B",
    `backupA` varchar(50) NOT NULL default "ENM_backup_A",
    `backupB` varchar(50) NOT NULL default "ENM_backup_B",
    `jgroupsA` varchar(50) NOT NULL default "ENM_jgroups_A",
    `jgroupsB` varchar(50) NOT NULL default "ENM_jgroups_B",
    `internalA` varchar(50) NOT NULL default "ENM_internal_A",
    `internalB` varchar(50) NOT NULL default "ENM_internal_B",
    `heartbeat1A` varchar(50) NOT NULL default "ENM_heartbeat1_A",
    `heartbeat2B` varchar(50) NOT NULL default "ENM_heartbeat2_B",
    `vlanDetails_id` integer NOT NULL,
    CONSTRAINT `virtualconnectnetworks_2_vlanDetails` FOREIGN KEY (`vlanDetails_id`) REFERENCES `dmt_vlandetails` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_imagecontent` (
    `id` INTEGER UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `packageRev_id` INTEGER UNSIGNED NOT NULL,
    `installedArtifacts` LONGTEXT,
    `installedDependencies` LONGTEXT,
    `dateCreated` DATETIME,
    `parent_id` INTEGER UNSIGNED,
    CONSTRAINT `imagecontent_2_pkgrevision` FOREIGN KEY (`packageRev_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `imagecontent_2_imagecontent` FOREIGN KEY (`parent_id`) REFERENCES `cireports_imagecontent` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_databasevip` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `postgres_address_id` integer UNSIGNED NOT NULL,
    `versant_address_id` integer UNSIGNED NOT NULL,
    `mysql_address_id` integer UNSIGNED NOT NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `postgresAddress_2_ip` FOREIGN KEY (`postgres_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `versantAddress_2_ip` FOREIGN KEY (`versant_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `mysqlAddress_2_ip` FOREIGN KEY (`mysql_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `databasevip_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

-- END 2.0.122

-- END 2.0.123

-- END 2.0.124

-- END 2.0.125

-- END 3.0.1

ALTER TABLE cireports_package MODIFY package_number VARCHAR(50);

-- END 3.0.2

-- END 3.0.3

CREATE TABLE `metrics_sppserver` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `url` varchar(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `fwk_tickertapeseverity` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `severity` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `fwk_tickertape` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `title` varchar(60) NOT NULL,
    `severity_id` smallint UNSIGNED NOT NULL,
    `summary` varchar(200) NOT NULL,
    `description` longtext NOT NULL,
    `hide` bool NOT NULL DEFAULT 0,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT `tickertape_2_tickertapeseverity` FOREIGN KEY (`severity_id`) REFERENCES `fwk_tickertapeseverity` (`id`)
) ENGINE=InnoDB
;

INSERT INTO `fwk_tickertapeseverity` (severity) VALUES("critical");
INSERT INTO `fwk_tickertapeseverity` (severity) VALUES("warning");
INSERT INTO `fwk_tickertapeseverity` (severity) VALUES("resolved");
INSERT INTO `fwk_tickertapeseverity` (severity) VALUES("info");

-- END 3.0.4

CREATE TABLE `cloud_gateway` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cloud_gatewaytosppmapping` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `gateway_id` smallint UNSIGNED NOT NULL,
    `spp_id` smallint UNSIGNED NOT NULL,
    `date` datetime NOT NULL,
    UNIQUE INDEX gatewaySpp (`gateway_id`, `spp_id`),
    CONSTRAINT `gatewaytosppmapping_2_gateway` FOREIGN KEY (`gateway_id`) REFERENCES `cloud_gateway` (`id`),
    CONSTRAINT `gatewaytosppmapping_2_spp` FOREIGN KEY (`spp_id`) REFERENCES `metrics_sppserver` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `fem_femkgburl` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `base` varchar(255) NOT NULL,
    `kgbstarted` varchar(255) NOT NULL,
    `kgbfinished` varchar(255) NOT NULL,
    `https` bool NOT NULL DEFAULT 0,
    `order` smallint UNSIGNED NOT NULL UNIQUE
) ENGINE=InnoDB
;

-- END 3.0.5
ALTER TABLE metrics_sppserver MODIFY name VARCHAR(50) NOT NULL UNIQUE;
ALTER TABLE metrics_sppserver MODIFY url VARCHAR(255) NOT NULL UNIQUE;

CREATE TABLE `dmt_clusterlayout` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `description` longtext NOT NULL
) ENGINE=InnoDB;

ALTER TABLE dmt_cluster ADD COLUMN `layout_id` SMALLINT UNSIGNED;
ALTER TABLE dmt_cluster ADD CONSTRAINT `cluster_2_clusterlayout` FOREIGN KEY (`layout_id`) REFERENCES `dmt_clusterlayout` (`id`);

INSERT INTO `dmt_clusterlayout` (name, description) VALUES("KVM", "Kernel-based Virtual Machine Deployment (LITP2 Vitualisation)");
INSERT INTO `dmt_clusterlayout` (name, description) VALUES("CMW", "Core Middleware Deploment (LITP1 Service Group/Unit)");
INSERT INTO `dmt_clusterlayout` (name, description) VALUES("OSS-RC Deployment", "Deployment for the OSS-RC Product");

-- END 3.0.6

ALTER TABLE dmt_databasevip ADD COLUMN `opendj_address_id` integer UNSIGNED;
ALTER TABLE dmt_databasevip ADD CONSTRAINT `opendjAddress_2_ip` FOREIGN KEY (`opendj_address_id`) REFERENCES `dmt_ipaddress` (`id`);

CREATE TABLE `cireports_component` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `parent_id` smallint unsigned,
    `element` varchar(100),
    `dateCreated` DATETIME,
    UNIQUE INDEX parentChild (`parent_id`, `element`),
    CONSTRAINT `component_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`),
    CONSTRAINT `component_2_component` FOREIGN KEY (`parent_id`) REFERENCES `cireports_component` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_packagecomponentmapping` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint unsigned NOT NULL,
    `component_id` smallint unsigned NOT NULL,
    UNIQUE INDEX packageComponent (`package_id`, `component_id`),
    CONSTRAINT `package_2_packagecomponentmapping` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `component_2_packagecomponentmapping` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`)
) ENGINE=InnoDB
;

-- END 3.0.7

-- END 3.0.8

-- END 3.0.9

ALTER TABLE `cireports_release` CHANGE COLUMN `masterArtifact_id` `masterArtifact_id` SMALLINT UNSIGNED NOT NULL;
ALTER TABLE `dmt_clusterserver` MODIFY `node_type` VARCHAR(50) NOT NULL;
ALTER TABLE `dmt_cluster` MODIFY `layout_id` SMALLINT UNSIGNED NOT NULL;
ALTER TABLE `dmt_server` MODIFY `dns_serverA` VARCHAR(30) NOT NULL;
ALTER TABLE `dmt_server` MODIFY `dns_serverB` VARCHAR(30) NOT NULL;

-- END 3.0.10

CREATE TABLE `cireports_label` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;

ALTER TABLE cireports_component ADD COLUMN `label_id` SMALLINT UNSIGNED;
ALTER TABLE cireports_component ADD CONSTRAINT `component_2_label` FOREIGN KEY (`label_id`) REFERENCES `cireports_label` (`id`);
ALTER TABLE cireports_component MODIFY `element` VARCHAR(100) NOT NULL;
ALTER TABLE cireports_component MODIFY `dateCreated` DATETIME NOT NULL;

ALTER TABLE dmt_managementserver DROP COLUMN `SSH_Host_RSA_Key`;
ALTER TABLE dmt_vlandetails CHANGE `services_vlan` `services_vlan` integer NULL;
ALTER TABLE dmt_vlandetails CHANGE `storage_vlan` `storage_vlan` integer NULL;
ALTER TABLE dmt_vlandetails CHANGE `backup_vlan` `backup_vlan` integer NULL;
ALTER TABLE dmt_vlandetails CHANGE `jgroups_vlan` `jgroups_vlan` integer NULL;
ALTER TABLE dmt_vlandetails CHANGE `internal_vlan` `internal_vlan` integer NULL;

-- END 3.0.11

-- END 3.0.12

-- END 3.0.13
ALTER TABLE `cireports_packagerevision` ADD COLUMN `infra` BOOLEAN NOT NULL DEFAULT 0 AFTER isoExclude;

DROP TABLE IF EXISTS `dmt_databasevip`;

CREATE TABLE `dmt_databasevip` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `postgres_address_id` integer UNSIGNED NOT NULL,
    `versant_address_id` integer UNSIGNED NOT NULL,
    `mysql_address_id` integer UNSIGNED NOT NULL,
    `opendj_address_id` integer UNSIGNED NOT NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `postgresAddress_2_ip` FOREIGN KEY (`postgres_address_id`) REFERENCES `dmt_internalipaddress` (`id`),
    CONSTRAINT `versantAddress_2_ip` FOREIGN KEY (`versant_address_id`) REFERENCES `dmt_internalipaddress` (`id`),
    CONSTRAINT `mysqlAddress_2_ip` FOREIGN KEY (`mysql_address_id`) REFERENCES `dmt_internalipaddress` (`id`),
    CONSTRAINT `opendjAddress_2_ip` FOREIGN KEY (`opendj_address_id`) REFERENCES `dmt_internalipaddress` (`id`),
    CONSTRAINT `databasevip_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

-- END 3.0.14

-- END 3.0.15

-- END 3.0.16

-- END 3.0.17

-- END 3.0.18

-- END 3.0.19

-- END 3.0.20

-- END 3.0.21

INSERT INTO cireports_states (state) VALUES("caution");
INSERT INTO cireports_cdbtypes (name) VALUES("Caution");

-- END 3.0.22

-- END 3.0.23

ALTER TABLE dmt_ipaddress CHANGE COLUMN `address` `address` char(39);
ALTER TABLE dmt_ipaddress CHANGE COLUMN `ipv6_address` `ipv6_address` char(39);
ALTER TABLE dmt_ipaddress DROP INDEX address;
ALTER TABLE dmt_ipaddress DROP INDEX address_2;
ALTER TABLE dmt_ipaddress DROP INDEX ipv6_address;

ALTER TABLE dmt_ipaddress ADD COLUMN `ipv6UniqueIdentifier` char(50) not null default "1";
ALTER TABLE dmt_ipaddress ADD COLUMN `ipv4UniqueIdentifier` char(50) not null default "1";
ALTER TABLE dmt_ipaddress ADD UNIQUE INDEX ipv6Identity (ipv6_address, ipv6UniqueIdentifier);
ALTER TABLE dmt_ipaddress ADD UNIQUE INDEX ipv4Identity (address, ipv4UniqueIdentifier);

ALTER TABLE dmt_networkinterface CHANGE COLUMN `mac_address` `mac_address` char(18);
ALTER TABLE dmt_networkinterface DROP INDEX mac_address;
ALTER TABLE dmt_networkinterface ADD COLUMN `nicIdentifier` char(50) not null default "1";
ALTER TABLE dmt_networkinterface ADD UNIQUE INDEX nicIdentity (mac_address, nicIdentifier);

ALTER TABLE dmt_server CHANGE COLUMN `hostname` `hostname` char(30);
ALTER TABLE dmt_server DROP INDEX hostname;
ALTER TABLE dmt_server ADD COLUMN `hostnameIdentifier` char(50) not null default "1";
ALTER TABLE dmt_server ADD UNIQUE INDEX hostnameIdentity (hostname, hostnameIdentifier);

CREATE TABLE `dmt_servicegroupinstanceinternal` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `service_group_id` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `serviceGroupInstanceInternal_2_ServiceGroup` FOREIGN KEY (`service_group_id`) REFERENCES `dmt_servicegroup` (`id`),
    CONSTRAINT `servicegroupinstanceInternal_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_virtualimageinfoip` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `number` varchar(3) NOT NULL,
    `hostname` varchar(30) NULL,
    `virtual_image_id` integer UNSIGNED NOT NULL,
    `ipMap_id` integer UNSIGNED NULL,
    CONSTRAINT `virtualimageinfoip_2_virtualimage` FOREIGN KEY (`virtual_image_id`) REFERENCES `dmt_virtualimage` (`id`),
    CONSTRAINT `virtualimageinfoip_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_databasevips` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `postgres_address_id` integer UNSIGNED NOT NULL,
    `versant_address_id` integer UNSIGNED NOT NULL,
    `mysql_address_id` integer UNSIGNED NOT NULL,
    `opendj_address_id` integer UNSIGNED NOT NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `postgres_2_ip` FOREIGN KEY (`postgres_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `versant_2_ip` FOREIGN KEY (`versant_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `mysql_2_ip` FOREIGN KEY (`mysql_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `opendj_2_ip` FOREIGN KEY (`opendj_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `databasevips_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

-- END 3.0.24

-- END 3.0.25

-- END 3.0.26

-- END 3.0.27

-- END 3.0.28

-- END 3.0.29

-- END 3.0.30

-- END 3.0.31

-- END 3.0.32

-- END 3.0.33

-- END 3.0.34

-- END 3.0.35

-- END 3.0.36

-- END 3.0.37

-- END 3.0.38

-- END 3.0.39

CREATE TABLE `dmt_deploymentstatustypes` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `status` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_deploymentstatus` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `status_id` SMALLINT UNSIGNED NOT NULL,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `status_changed` datetime NOT NULL default 0,
    `description` longtext NULL,
    `osDetails` varchar(100) NULL,
    `litpVersion` varchar(50) NULL,
    `mediaArtifact` varchar(100) NULL,
    `packages` longtext NULL,
    `patches` longtext NULL,
    CONSTRAINT `deploymentstatus_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `deploymentstatus_2_deploymentstatustypes` FOREIGN KEY (`status_id`) REFERENCES `dmt_deploymentstatustypes` (`id`)
) ENGINE=InnoDB
;

INSERT INTO dmt_deploymentstatustypes (status) VALUES("IDLE");
INSERT INTO dmt_deploymentstatustypes (status) VALUES("Infra_Busy");
INSERT INTO dmt_deploymentstatustypes (status) VALUES("Infra_Ready");
INSERT INTO dmt_deploymentstatustypes (status) VALUES("Infra_Failed");
INSERT INTO dmt_deploymentstatustypes (status) VALUES("KVM_Busy");
INSERT INTO dmt_deploymentstatustypes (status) VALUES("KVM_Completed");
INSERT INTO dmt_deploymentstatustypes (status) VALUES("KVM_Failed");

-- END 3.0.40

-- END 3.0.41

-- END 3.0.42

-- END 3.0.43

-- END 3.0.44

-- END 3.0.45

-- END 3.0.46

-- END 3.0.47

-- END 3.0.48

-- END 3.0.49

-- END 3.0.50

-- END 3.0.51

-- END 3.0.52

DROP TABLE IF EXISTS `dmt_clustertoinstallgroupmapping`;
DROP TABLE IF EXISTS `dmt_installgroup`;

CREATE TABLE `dmt_installgroup` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `installGroup` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_clustertoinstallgroupmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL UNIQUE,
    `group_id` smallint UNSIGNED NOT NULL,
    UNIQUE INDEX grouptoclustermap (cluster_id, group_id),
    CONSTRAINT `cluster_2_installgroup` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `group_2_installgroup` FOREIGN KEY (`group_id`) REFERENCES `dmt_installgroup` (`id`)
) ENGINE=InnoDB
;

ALTER TABLE dmt_nasstoragedetails ADD COLUMN `sanRaidGroup` integer UNSIGNED NOT NULL AFTER sanPoolName;
ALTER TABLE dmt_storage ADD COLUMN `vnxType` varchar(100) NOT NULL default "vnx1";

-- END 3.0.53

-- END 3.0.54

ALTER TABLE dmt_cluster DROP COLUMN status;
ALTER TABLE dmt_cluster DROP COLUMN status_changed;

ALTER TABLE dmt_clustertoinstallgroupmapping ADD COLUMN `status_id` smallint UNSIGNED NOT NULL;
ALTER TABLE dmt_clustertoinstallgroupmapping ADD CONSTRAINT `depstatus_2_installgroup` FOREIGN KEY (`status_id`) REFERENCES `dmt_deploymentstatus` (`id`);

-- END 3.0.55

-- END 3.0.56

-- END 3.0.57

-- END 3.0.58

-- END 3.0.59

-- END 3.0.60

ALTER TABLE dmt_enclosure ADD COLUMN `sanSw_credentials_id` integer UNSIGNED NULL;
ALTER TABLE dmt_enclosure ADD CONSTRAINT `sanSwenclosure_2_credentials` FOREIGN KEY (`sanSw_credentials_id`) REFERENCES `dmt_credentials` (`id`);

ALTER TABLE dmt_databasevips ADD COLUMN `opendj_address2_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `opendjAddress2_2_ip` FOREIGN KEY (`opendj_address2_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.0.61

ALTER TABLE `dmt_sed` ADD COLUMN `linkText` varchar(15) NULL;
ALTER TABLE `dmt_sed` ADD COLUMN `link` longtext;
ALTER TABLE `dmt_sed` ADD COLUMN `iso_id` smallint UNSIGNED NULL;
ALTER TABLE `dmt_sed` ADD CONSTRAINT `isobuild_2_sed` FOREIGN KEY (`iso_id`) REFERENCES `cireports_isobuild` (`id`);

ALTER TABLE dmt_nasstoragedetails CHANGE `sanRaidGroup` `sanRaidGroup` integer UNSIGNED NULL;

CREATE TABLE `dmt_deploypackageexemptionlist` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `packageName` varchar(250) NOT NULL UNIQUE
) ENGINE=InnoDB
;

-- END 3.0.62

-- END 3.0.63

-- END 3.0.64

-- END 3.0.65

-- END 3.0.66

-- END 3.0.67

-- END 3.0.68

-- END 3.0.69

CREATE TABLE `cireports_productpackagemapping` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `package_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `productpkgmapping_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`),
    CONSTRAINT `productpkgmapping_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    UNIQUE INDEX productpackagemap (product_id, package_id)
) ENGINE=InnoDB
;

ALTER TABLE dmt_databasevips ADD COLUMN `jms_address_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `jms_2_ip` FOREIGN KEY (`jms_address_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.0.70

-- END 3.0.71

-- END 3.0.72

-- END 3.0.73

-- END 3.0.74

ALTER TABLE cloud_gatewaytosppmapping CHANGE `id` `id` integer UNSIGNED AUTO_INCREMENT NOT NULL;

-- END 3.0.75

-- END 3.0.76

ALTER TABLE dmt_databasevips ADD COLUMN `eSearch_address_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `eSearch_2_ip` FOREIGN KEY (`eSearch_address_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.0.77

-- END 3.0.78

-- END 3.0.79

-- END 3.0.80

-- END 3.0.81

ALTER TABLE cireports_drop ADD COLUMN systemInfo varchar(100) NOT NULL DEFAULT "AOM Number and RSTATE required here";

-- END 3.0.82

-- END 3.0.83

-- END 3.0.84

-- END 3.0.85

-- END 3.0.86

-- END 3.0.87

-- END 3.0.88

-- END 3.0.89

-- END 3.0.90

-- END 3.0.91

-- END 3.0.92

-- END 3.0.93

-- END 3.0.94

ALTER TABLE dmt_vlandetails ADD COLUMN `litp_management` varchar(18) NOT NULL default 'services'  AFTER `services_vlan`;

ALTER TABLE dmt_ssodetails ADD COLUMN `opendjAdminPassword` varchar(100) AFTER `ldapPassword`;

-- END 3.0.95

-- END 3.0.96

-- END 3.0.97

-- END 3.0.98

-- END 3.0.99

-- END 3.0.100

-- END 3.0.101

-- END 3.0.102

-- END 3.0.103

-- END 3.0.104

-- END 3.0.105

-- END 3.0.106

-- END 3.0.107

-- END 3.0.108

-- END 3.0.109

ALTER TABLE cireports_drop ADD COLUMN `status` varchar(20) NOT NULL DEFAULT 'open' AFTER `systemInfo`;

CREATE TABLE `cireports_dropactivity` (
    `id`  smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` smallint UNSIGNED NOT NULL,
    `action` varchar(100) NOT NULL,
    `desc` longtext NOT NULL,
    `user` varchar(10) NOT NULL,
    `date` datetime NOT NULL,
    CONSTRAINT `dropactivity_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;

alter table cireports_package add `testware` bool not null default 0;
alter table cireports_mediaartifact add `testware` bool not null default 0;

CREATE TABLE `cireports_producttestwaremediamapping` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `productIsoVersion_id` smallint UNSIGNED NOT NULL,
    `testwareIsoVersion_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `productmediamapping_2_isobuild` FOREIGN KEY (`productIsoVersion_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `testwaremediamapping_2_isobuild` FOREIGN KEY (`testwareIsoVersion_id`) REFERENCES `cireports_isobuild` (`id`)
) ENGINE=InnoDB;

-- END 3.0.110

-- END 3.0.111

-- END 3.0.112

-- END 3.0.113

-- END 3.0.114

-- END 3.0.115

ALTER TABLE dmt_databasevips CHANGE `opendj_address2_id` `opendj_address2_id` integer UNSIGNED NULL;

-- END 3.0.116

-- END 3.0.117

-- END 3.0.118

-- END 3.0.119

-- END 3.0.120

-- END 3.0.121

-- END 3.0.122

-- END 3.0.123

-- END 3.0.124

ALTER TABLE dmt_ssodetails ADD COLUMN `hqDatabasePassword` varchar(100) AFTER `ldapPassword`;

-- END 3.0.125

-- END 3.0.126

-- END 3.0.127

-- END 3.0.128

-- END 3.0.129

-- END 3.0.130

-- END 3.0.131

-- END 3.0.132

-- END 3.0.133

-- END 3.0.134

CREATE TABLE `cireports_deliverygroup` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` SMALLINT UNSIGNED NOT NULL,
    `deleted` bool NOT NULL,
    `delivered` bool NOT NULL,
    `obsoleted` bool NOT NULL,
    CONSTRAINT `deliverygroup_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_deliverytopackagerevmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `packageRevision_id` integer UNSIGNED NOT NULL,
    UNIQUE (`deliveryGroup_id`, `packageRevision_id`),
    CONSTRAINT `deliverytopackagerevmapping_2_deliverygroup` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`),
    CONSTRAINT `deliverytopackagerevmapping_2_packagerevision` FOREIGN KEY (`packageRevision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_deliverygroupcomment` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `comment` longtext NOT NULL,
    CONSTRAINT `deliverygroupcomment_2_deliverygroup` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`)
) ENGINE=InnoDB
;

-- END 3.0.135
CREATE TABLE `dmt_deploymentbaseline` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `createdAt` datetime,
    `updatedAt` datetime,
    `clusterName` varchar(100) NOT NULL,
    `clusterID` varchar(100) NOT NULL,
    `osDetails` varchar(100) NOT NULL,
    `litpVersion` varchar(100) NOT NULL,
    `mediaArtifact` varchar(100) NOT NULL,
    `packages` longtext NULL,
    `patches` longtext NULL,
    `dropName` varchar(100) NOT NULL,
    `groupName` varchar(100) NOT NULL,
    `sedVersion` varchar(100) NOT NULL,
    `deploymentTemplates` varchar(100) NOT NULL,
    `tafVersion` varchar(100) NOT NULL,
    `masterBaseline` bool NOT NULL DEFAULT 0

) ENGINE=InnoDB;

-- END 3.0.136

-- END 3.0.137

-- END 3.0.138

-- END 3.0.139

-- END 3.0.140
ALTER TABLE dmt_deploymentbaseline ADD COLUMN `descriptionDetails` varchar(100) AFTER `tafVersion`;

-- END 3.0.141
ALTER TABLE cireports_droppackagemapping CHANGE `deliverer_name` `deliverer_name` varchar(100);

-- END 3.0.142

-- END 3.0.143

-- END 3.0.144

-- END 3.0.145

-- END 3.0.146

-- END 3.0.147

-- END 3.0.148

-- END 3.0.149

-- END 3.0.150

-- END 3.0.151
ALTER TABLE cireports_drop CHANGE systemInfo systemInfo varchar(100) NOT NULL;

-- END 3.0.152

-- END 3.0.153

-- END 3.0.154

-- END 3.0.155

-- END 3.0.156

-- END 3.0.157

-- END 3.0.158

-- END 3.0.159

-- END 3.0.160

-- END 3.0.161

-- END 3.0.162

-- END 3.0.163

-- END 3.0.164

-- END 3.0.165

-- END 3.0.166

-- END 3.0.167

-- END 3.0.168

-- END 3.0.169
-- END 3.0.170

-- END 3.0.171

-- END 3.0.172

-- END 3.0.173

-- END 3.0.174

-- END 3.0.175

-- END 3.0.176

-- END 3.0.177

-- END 3.0.178

-- END 3.0.179

-- END 3.0.180
ALTER TABLE cireports_isobuild ADD COLUMN `sed_build_id` smallint UNSIGNED;
ALTER TABLE cireports_isobuild ADD CONSTRAINT `iso_2_sed` FOREIGN KEY (`sed_build_id`) REFERENCES `dmt_sed` (`id`);
ALTER TABLE cireports_isobuild ADD COLUMN `deploy_script_version` varchar(100);

ALTER TABLE cireports_mediaartifact ADD COLUMN `mediaType` varchar(10) DEFAULT "iso" NOT NULL AFTER `obsoleteAfter_id`;

CREATE TABLE `dmt_redhatartifacttoversionmapping` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mediaArtifact_id` SMALLINT UNSIGNED NOT NULL,
    `artifactReference` varchar(100) NOT NULL UNIQUE,
    CONSTRAINT `mediaArtifact_id_2_mediaArtifact` FOREIGN KEY (`mediaArtifact_id`) REFERENCES `cireports_mediaartifact` (`id`)
) ENGINE=InnoDB;

-- END 3.0.181

-- END 3.0.182

-- END 3.0.183
CREATE TABLE `dmt_deployscriptmapping` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reference` varchar(20) NOT NULL UNIQUE,
    `version` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `dmt_ipmiversionmapping` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reference` varchar(20) NOT NULL UNIQUE,
    `version` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- END 3.0.184

-- END 3.0.185

-- END 3.0.186
ALTER TABLE `cireports_cdbtypes` ADD `sort_order` SMALLINT NOT NULL DEFAULT '0';

-- END 3.0.187

-- END 3.0.188

-- END 3.0.189

-- END 3.0.190

CREATE TABLE `dmt_deploymenttestcase` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testcase` varchar(255) NOT NULL,
    `enabled` bool NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_maptestresultstodeployment` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `testcase_id` SMALLINT UNSIGNED NOT NULL,
    `result` bool NOT NULL,
    `testcaseOutput` varchar(255),
    `testDate` datetime NOT NULL,
    CONSTRAINT `cluster_id_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `testcase_id_2_deploymentTestcase` FOREIGN KEY (`testcase_id`) REFERENCES `dmt_deploymenttestcase` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_testgroup` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testGroup` varchar(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_maptestgrouptodeployment` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `group_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `cluster_id_ref_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `group_id_2_testgroup` FOREIGN KEY (`group_id`) REFERENCES `dmt_testgroup` (`id`)
) ENGINE=InnoDB;

-- END 3.0.191

-- END 3.0.192

ALTER TABLE `cireports_deliverygroup` ADD COLUMN `creator` varchar(100);

-- END 3.0.193

-- END 3.0.194

-- END 3.0.195

ALTER TABLE dmt_maptestresultstodeployment change testcaseOutput testcaseOutput longtext;
ALTER TABLE dmt_maptestresultstodeployment change testcase_id testcase_id SMALLINT UNSIGNED NULL;
ALTER TABLE dmt_deploymenttestcase ADD COLUMN testcase_description varchar(255) NOT NULL AFTER id;

ALTER TABLE `cireports_deliverygroupcomment` ADD COLUMN `date` datetime;

-- END 3.0.196

-- END 3.0.197

-- END 3.0.198

-- END 3.0.199

-- END 3.0.200

-- END 3.0.201
DROP TABLE dmt_maptestresultstodeployment;
CREATE TABLE `dmt_maptestresultstodeployment` (
    `id` INT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `testcase_id` SMALLINT UNSIGNED NOT NULL,
    `result` bool NOT NULL,
    `testcaseOutput` longtext,
    `testDate` datetime NOT NULL,
    CONSTRAINT `cluster_id_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `testcase_id_2_deploymentTestcase` FOREIGN KEY (`testcase_id`) REFERENCES `dmt_deploymenttestcase` (`id`)
) ENGINE=InnoDB;

-- END 3.0.202

-- END 3.0.203

-- END 3.0.204
ALTER TABLE dmt_deploymentbaseline ADD `success` bool NOT NULL DEFAULT 1;

-- END 3.0.205

-- END 3.0.206

-- END 3.0.207

-- END 3.0.208

-- END 3.0.209

-- END 3.0.210

-- END 3.0.211

ALTER TABLE dmt_testgroup ADD `defaultGroup` bool DEFAULT 0;

-- END 3.0.212

-- END 3.0.213

-- END 3.0.214

-- END 3.0.215

-- END 3.0.216

-- END 3.0.217

-- END 3.0.218
ALTER TABLE cireports_deliverygroup ADD COLUMN `component_id` smallint UNSIGNED;
ALTER TABLE cireports_deliverygroup ADD CONSTRAINT `deliverygroup_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`);
ALTER TABLE cireports_package CHANGE COLUMN `name` `name` varchar(100) NOT NULL UNIQUE;
ALTER TABLE cireports_package MODIFY package_number VARCHAR(100);

-- END 3.0.219

-- END 3.0.220

-- END 3.0.221

-- END 3.0.222

-- END 3.0.223

-- END 3.0.224

-- END 3.0.225

-- END 3.0.226

-- END 3.0.227

-- END 3.0.228

-- END 3.0.229

-- END 3.0.230
ALTER TABLE dmt_cluster ADD COLUMN `component_id` smallint UNSIGNED;
ALTER TABLE dmt_cluster ADD CONSTRAINT `cluster_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`);

DROP TABLE dmt_maptestresultstodeployment;
CREATE TABLE `dmt_maptestresultstodeployment` (
    `id` INT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `testcase_description` varchar(255) NOT NULL,
    `testcase` varchar(255) NOT NULL,
    `result` bool NOT NULL,
    `testcaseOutput` longtext,
    `testDate` datetime NOT NULL,
    CONSTRAINT `cluster_id_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

-- END 3.0.231

-- END 3.0.232

-- END 3.0.233
ALTER TABLE dmt_maptestresultstodeployment CHANGE COLUMN `testcase` `testcase` longtext NOT NULL;
ALTER TABLE dmt_deploymenttestcase CHANGE COLUMN `testcase` `testcase` longtext NOT NULL;


-- END 3.0.234

-- END 3.0.235

-- END 3.0.236

-- END 3.0.237
ALTER TABLE dmt_credentials ADD COLUMN `loginScope` varchar(20);

-- END 3.0.238

-- END 3.0.239

-- END 3.0.240

-- END 3.0.241

-- END 3.0.242

-- END 3.0.243

-- END 3.0.244

-- END 3.0.245

-- END 3.0.246

-- END 3.0.247

-- END 3.0.248

-- END 3.0.249

-- END 3.0.250

-- END 3.0.251

-- END 3.0.252

-- END 3.0.253

-- END 3.0.254

-- END 3.0.255

-- END 3.0.256

-- END 3.0.257

-- END 3.0.258


-- END 3.0.259

-- END 3.0.260

-- END 3.0.261

-- END 3.0.262

-- END 3.0.263

-- END 3.0.264
ALTER TABLE cireports_deliverygroup ADD COLUMN `modifiedDate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- END 3.0.265

-- END 3.0.266

-- END 3.0.267

-- END 3.0.268

-- END 3.0.269

-- END 3.0.270
ALTER TABLE cireports_deliverytopackagerevmapping ADD COLUMN `team` varchar(500) NOT NULL DEFAULT "No Team Data";

-- END 3.0.271
ALTER TABLE dmt_virtualconnectnetworks ADD COLUMN jgroups varchar(50) NOT NULL AFTER backupB;
ALTER TABLE dmt_virtualconnectnetworks ADD COLUMN heartbeat1 varchar(50) NOT NULL AFTER internalB;
ALTER TABLE dmt_virtualconnectnetworks ADD COLUMN heartbeat2 varchar(50) NOT NULL AFTER heartbeat1;

ALTER TABLE dmt_enclosure ADD COLUMN vc_domain_name varchar(100) NOT NULL AFTER domain_name;
ALTER TABLE dmt_enclosure ADD COLUMN uplink_A_port1 varchar(30) NOT NULL AFTER sanSw_credentials_id;
ALTER TABLE dmt_enclosure ADD COLUMN uplink_A_port2 varchar(30) NOT NULL AFTER uplink_A_port1;
ALTER TABLE dmt_enclosure ADD COLUMN uplink_B_port1 varchar(30) NOT NULL AFTER uplink_A_port2;
ALTER TABLE dmt_enclosure ADD COLUMN uplink_B_port2 varchar(30) NOT NULL AFTER uplink_B_port1;

-- END 3.0.272

-- END 3.0.273

-- END 3.0.274
ALTER TABLE cireports_deliverygroup ADD COLUMN `missingDependencies` bool NOT NULL;

-- END 3.0.275

-- END 3.0.276

-- END 3.0.277

-- END 3.0.278

-- END 3.0.279

-- END 3.0.280

-- END 3.0.281

-- END 3.0.282

-- END 3.0.283

-- END 3.0.284

-- END 3.0.285

-- END 3.0.286

-- END 3.0.287

-- END 3.0.288

-- END 3.0.289

-- END 3.0.290
CREATE TABLE `cireports_jiraissue` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `jiraNumber` varchar(20) NOT NULL,
    `issueType` varchar(30) NOT NULL
) ENGINE=InnoDB;


CREATE TABLE `cireports_jiralabel` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_jiradeliverygroupmap` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `jiraIssue_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `jiradeliverygroupmap_2_deliverygroup` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`),
    CONSTRAINT `jiradeliverygroupmap_2_jiraissue` FOREIGN KEY (`jiraIssue_id`) REFERENCES `cireports_jiraissue` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_labeltojiraissuemap` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `jiraIssue_id` SMALLINT UNSIGNED NOT NULL,
    `jiraLabel_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `labeltojiraissuemap_2_jiraissue` FOREIGN KEY (`jiraIssue_id`) REFERENCES `cireports_jiraissue` (`id`),
    CONSTRAINT `labeltojiraissuemap_2_jiralabel` FOREIGN KEY (`jiraLabel_id`) REFERENCES `cireports_jiralabel` (`id`)
) ENGINE=InnoDB;

-- END 3.0.291
CREATE TABLE `cireports_packagenameexempt` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

INSERT INTO cireports_packagenameexempt(name) VALUES("ERICcommodelsr4.0_CXP9031458");
INSERT INTO cireports_packagenameexempt(name) VALUES("ERICcommodelsr3.3_CXP9031495");
INSERT INTO cireports_packagenameexempt(name) VALUES("ERICcommodelsr3.2_CXP9031496");
INSERT INTO cireports_packagenameexempt(name) VALUES("ERICcommodelsr5.0_CXP9031865");
INSERT INTO cireports_packagenameexempt(name) VALUES("ERICcommodelsr5.1_CXP9032416");

-- END 3.0.292

-- END 3.0.293
ALTER TABLE `dmt_virtualimageitems` ADD COLUMN `layout` VARCHAR(50);

-- END 3.0.294

-- END 3.0.295

-- END 3.0.296

-- END 3.0.297

ALTER TABLE `dmt_virtualimageitems` ADD COLUMN `active` bool NOT NULL DEFAULT 1;

-- END 3.0.298

-- END 3.0.299

-- END 3.0.300

-- END 3.0.301

-- END 3.0.302

-- END 3.0.303

-- END 3.0.304

-- END 3.0.305
ALTER TABLE dmt_cluster MODIFY `group_id` int(11) NULL;

-- END 3.0.306

-- END 3.0.307

-- END 3.0.308

-- END 3.0.309

-- END 3.0.310

-- END 3.0.311

CREATE TABLE `depmodel_artifactversiontopackagerevisionmapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifact_version_id` integer NOT NULL,
    `package_revision_id` integer unsigned NOT NULL,
    UNIQUE (artifact_version_id,package_revision_id),
    CONSTRAINT `artifactversion_2_packagerevision` FOREIGN KEY (`artifact_version_id`) REFERENCES `depmodel_artifactversion` (`id`),
    CONSTRAINT `packagerevision_2_artifactversion` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;

-- END 3.0.312

-- END 3.0.313

-- END 3.0.314

-- END 3.0.315

-- END 3.0.316

-- END 3.0.317

-- END 3.0.318

-- END 3.0.319

-- END 3.0.320
CREATE TABLE `depmodel_anomalyartifact` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `depmodel_anomalyartifactversion` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `anomalyartifact_id` integer NOT NULL,
    `groupname` varchar(100) NOT NULL ,
    `version` varchar(100) NOT NULL,
    `m2type` varchar(30) NOT NULL,
    UNIQUE (anomalyartifact_id,groupname,version,m2type),
    CONSTRAINT `anomalyartifactversion_2_anomalyartifact` FOREIGN KEY (`anomalyartifact_id`) REFERENCES `depmodel_anomalyartifact` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `depmodel_anomalyartifactversiontopackagerev` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `anomalyartifact_version_id` integer NOT NULL,
    `package_revision_id` integer unsigned NOT NULL,
    UNIQUE (anomalyartifact_version_id,package_revision_id),
    CONSTRAINT `anomalyartifactversion_2_packagerevision` FOREIGN KEY (`anomalyartifact_version_id`) REFERENCES `depmodel_anomalyartifactversion` (`id`),
    CONSTRAINT `packagerevision_2_anomalyartifactversion` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;

-- END 3.0.321

-- END 3.0.322

-- END 3.0.323

-- END 3.0.324

-- END 3.0.325
ALTER TABLE depmodel_anomalyartifactversiontopackagerev DROP FOREIGN KEY packagerevision_2_anomalyartifactversion;
ALTER TABLE depmodel_anomalyartifactversiontopackagerev DROP COLUMN package_revision_id;
ALTER TABLE depmodel_anomalyartifactversiontopackagerev ADD COLUMN package_revision varchar(255) NOT NULL AFTER anomalyartifact_version_id;

-- END 3.0.326

-- END 3.0.327

-- END 3.0.328

-- END 3.0.329

-- END 3.0.330

-- END 3.0.331

-- END 3.0.332

-- END 3.0.333

-- END 3.0.334

-- END 3.0.335

-- END 3.0.336

-- END 3.0.337

-- END 3.0.338

-- END 3.0.339

-- END 3.0.340

-- END 3.0.341

-- END 3.0.342

-- END 3.0.343

-- END 3.0.344

-- END 3.0.345

-- END 3.0.346
ALTER TABLE depmodel_artifactversion ADD COLUMN bomcreatedartifact bool DEFAULT 0 NOT NULL AFTER m2type;
ALTER TABLE depmodel_artifactversion ADD COLUMN bomversion varchar(30) AFTER bomcreatedartifact;
ALTER TABLE depmodel_artifactversion ADD UNIQUE INDEX artGrpVerM2BomCreatedBomVer (artifact_id, groupname,version,m2type,bomcreatedartifact,bomversion);
ALTER TABLE depmodel_artifactversion DROP INDEX artifact_id;

RENAME TABLE depmodel_artifactversiontopackagerevisionmapping TO depmodel_artverstopackrevtoisobuildmap;
ALTER TABLE depmodel_artverstopackrevtoisobuildmap ADD COLUMN isobuild_version_id smallint unsigned AFTER package_revision_id;
ALTER TABLE depmodel_artverstopackrevtoisobuildmap ADD UNIQUE INDEX artVerPackVerIsoBuild (artifact_version_id,package_revision_id,isobuild_version_id);
ALTER TABLE depmodel_artverstopackrevtoisobuildmap DROP INDEX artifact_version_id;
ALTER TABLE depmodel_artverstopackrevtoisobuildmap ADD CONSTRAINT `isobuildversion_2_artifactversion` FOREIGN KEY (`isobuild_version_id`) REFERENCES `cireports_isobuild` (`id`);
-- END 3.0.347

-- END 3.0.348

-- END 3.0.349
ALTER TABLE depmodel_artifactversion ADD COLUMN reponame varchar(30) AFTER bomversion;
ALTER TABLE depmodel_artifactversion ADD UNIQUE INDEX artGrpVerM2BomCreatedBomVerRepo (artifact_id, groupname,version,m2type,bomcreatedartifact,bomversion,reponame);
ALTER TABLE depmodel_artifactversion DROP INDEX artGrpVerM2BomCreatedBomVer;

RENAME TABLE depmodel_artverstopackrevtoisobuildmap TO depmodel_artverstopackagetoisobuildmap;
ALTER TABLE depmodel_artverstopackagetoisobuildmap DROP FOREIGN KEY artifactversion_2_packagerevision;
ALTER TABLE depmodel_artverstopackagetoisobuildmap DROP FOREIGN KEY packagerevision_2_artifactversion;
ALTER TABLE depmodel_artverstopackagetoisobuildmap DROP INDEX artVerPackVerIsoBuild;
ALTER TABLE depmodel_artverstopackagetoisobuildmap DROP COLUMN package_revision_id;
ALTER TABLE depmodel_artverstopackagetoisobuildmap ADD COLUMN package_id smallint unsigned;
ALTER TABLE depmodel_artverstopackagetoisobuildmap ADD UNIQUE INDEX artVerPackageIsoBuild (artifact_version_id,package_id,isobuild_version_id);
ALTER TABLE depmodel_artverstopackagetoisobuildmap ADD CONSTRAINT `artifactversion_2_package` FOREIGN KEY (`artifact_version_id`) REFERENCES `depmodel_artifactversion` (`id`);
ALTER TABLE depmodel_artverstopackagetoisobuildmap ADD CONSTRAINT `package_2_artifactversion` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`);

-- END 3.0.350

-- END 3.0.351

-- END 3.0.352
ALTER TABLE dmt_enclosure ADD COLUMN name varchar(32) NOT NULL AFTER domain_name;
ALTER TABLE dmt_enclosure ADD COLUMN rackName varchar(32) NOT NULL AFTER domain_name;

-- END 3.0.353

-- END 3.0.354

-- END 3.0.355

-- END 3.0.356
ALTER TABLE depmodel_artifactversion MODIFY m2type VARCHAR(30);
ALTER TABLE depmodel_artifactversion MODIFY reponame VARCHAR(255);
ALTER TABLE depmodel_anomalyartifactversiontopackagerev ADD UNIQUE INDEX anomalyArtifactToPackRev (anomalyartifact_version_id, package_revision);
ALTER TABLE depmodel_anomalyartifactversiontopackagerev DROP INDEX anomalyartifact_version_id;

-- END 3.0.357

-- END 3.0.358

-- END 3.0.359

-- END 3.0.360

-- END 3.0.361

-- END 3.0.362

-- END 3.0.363

-- END 3.1.1

-- END 3.1.2

-- END 3.1.3

-- END 3.1.4

-- END 3.1.5

-- END 3.1.6
CREATE TABLE `depmodel_dependencypluginartifact` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(200) NOT NULL UNIQUE,
    `property` varchar(200) NOT NULL
) ENGINE=InnoDB
;

-- END 3.1.7
ALTER TABLE cireports_productsetrelease DROP INDEX number;
ALTER TABLE cireports_productsetrelease ADD UNIQUE INDEX nameNumberProductSet (name, number, productSet_id);

-- END 3.1.8

-- END 3.1.9

-- END 3.1.10

-- END 3.1.11

-- END 3.1.12

-- END 3.1.13

-- END 3.1.14

-- END 3.1.15

-- END 3.1.16

-- END 3.1.17

-- END 3.1.18

-- END 3.1.19

-- END 3.1.20

-- END 3.1.21

-- END 3.1.22

-- END 3.1.23

-- END 3.1.24

-- END 3.1.25

-- END 3.1.26

-- END 3.1.27

-- END 3.1.28

-- END 3.1.29

-- END 3.1.30

-- END 3.1.31

-- END 3.1.32

-- END 3.1.33

-- END 3.1.34

-- END 3.1.35

-- END 3.1.36

-- END 3.1.37

-- END 3.1.38

-- END 3.1.39

-- END 3.1.40

-- END 3.1.41

-- END 3.1.42

-- END 3.1.43

-- END 3.1.44

-- END 3.1.45

-- END 3.1.46
UPDATE dmt_ipaddress SET ipType="nasvip1" where ipType="vipclog";
UPDATE dmt_ipaddress SET ipType="nasvip2" where ipType="viptor1";

-- END 3.1.47

-- END 3.1.48

-- END 3.1.49

-- END 3.1.50
ALTER TABLE cireports_jiralabel ADD COLUMN type varchar(30) NOT NULL;
UPDATE cireports_jiralabel SET type="label";

-- END 3.1.51

-- END 3.1.52

-- END 3.1.53

-- END 3.1.54

-- END 3.1.55

-- END 3.1.56

-- END 3.1.57

-- END 3.1.58

-- END 3.1.59

-- END 3.1.60

-- END 3.1.61

-- END 3.1.62

-- END 3.1.63

-- END 3.1.64

-- END 3.1.65
CREATE TABLE `cireports_productdroptocdbtypemap` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `drop_id` SMALLINT UNSIGNED NOT NULL,
    `type_id` smallint UNSIGNED NOT NULL,
    `overallStatusFailure` bool NOT NULL DEFAULT 1,
    `enabled` bool NOT NULL DEFAULT 0,
    UNIQUE (`product_id`, `drop_id`, `type_id`),
    CONSTRAINT `product_2_cdbtype` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`),
    CONSTRAINT `cdbtype_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `cdbtype_2_product` FOREIGN KEY (`type_id`) REFERENCES `cireports_cdbtypes` (`id`)
) ENGINE=InnoDB;

-- END 3.1.66

-- END 3.1.67

-- END 3.1.68

-- END 3.1.69

-- END 3.1.70

-- END 3.1.71

-- END 3.1.72

-- END 3.1.73

-- END 3.1.74

-- END 3.1.75

-- END 3.1.76
CREATE TABLE `dmt_vmserviceiprangeitem` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ipType` varchar(50) NOT NULL UNIQUE,
    `ipDescription` varchar(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_vmserviceiprange` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ipv4AddressStart` char(15),
    `ipv4AddressEnd` char(15),
    `ipv6AddressStart` char(39),
    `ipv6AddressEnd` char(39),
    `ipTypeId_id` smallint unsigned NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `ipTypeId_id_2_vmserviceiprangeitem` FOREIGN KEY (`ipTypeId_id`) REFERENCES `dmt_vmserviceiprangeitem` (`id`),
    CONSTRAINT `vmserviceiprange_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

INSERT INTO dmt_vmserviceiprangeitem(ipType,ipDescription) VALUES("IPv4 Public","Ipv4 Public address for the VM Services");
INSERT INTO dmt_vmserviceiprangeitem(ipType,ipDescription) VALUES("IPv4 Storage","Ipv4 Storage address for the VM Services");
INSERT INTO dmt_vmserviceiprangeitem(ipType,ipDescription) VALUES("IPv6 Public","Ipv6 Public address for the VM Services");

-- END 3.1.77

-- END 3.1.78
CREATE TABLE `cireports_mediaartifacttype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `type` varchar(10) NOT NULL UNIQUE
) ENGINE=InnoDB
;
INSERT INTO cireports_mediaartifacttype(type) VALUES("iso");
INSERT INTO cireports_mediaartifacttype(type) VALUES("tar.gz");

-- END 3.1.79

-- END 3.1.80

-- END 3.1.81

-- END 3.1.82

-- END 3.1.83
CREATE TABLE `dmt_lvsroutervip` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `pm_internal_id` integer UNSIGNED NOT NULL,
    `pm_external_id` integer UNSIGNED NOT NULL,
    `fm_internal_id` integer UNSIGNED NOT NULL,
    `fm_external_id` integer UNSIGNED NOT NULL,
    `cm_internal_id` integer UNSIGNED NOT NULL,
    `cm_external_id` integer UNSIGNED NOT NULL,
    `storage_internal_id` integer UNSIGNED NOT NULL,
    `scripting_internal_id` integer UNSIGNED NOT NULL,
    `events_internal_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `lvsroutervip_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `pminternal_2_ip` FOREIGN KEY (`pm_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `pmexternal_2_ip` FOREIGN KEY (`pm_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `fminternal_2_ip` FOREIGN KEY (`fm_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `fmexternal_2_ip` FOREIGN KEY (`fm_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `cminternal_2_ip` FOREIGN KEY (`cm_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `cmexternal_2_ip` FOREIGN KEY (`cm_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `storageinternal_2_ip` FOREIGN KEY (`storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scriptinginternal_2_ip` FOREIGN KEY (`scripting_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `eventsinternal_2_ip` FOREIGN KEY (`scripting_internal_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB;

-- END 3.1.84

-- END 3.1.85

-- END 3.1.86

-- END 3.1.87

ALTER TABLE cireports_package ADD COLUMN git_repo varchar(200) AFTER testware;
ALTER TABLE depmodel_artifact ADD COLUMN package_id smallint UNSIGNED;
ALTER TABLE depmodel_artifact ADD CONSTRAINT `artifact_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`);

-- END 3.1.88

-- END 3.1.89

-- END 3.1.90
ALTER TABLE cireports_deliverygroup ADD COLUMN `warning` bool NOT NULL;

-- END 3.1.91

-- END 3.1.92

-- END 3.1.93

-- END 3.1.94

-- END 3.1.95

-- END 3.1.96

-- END 3.1.97

-- END 3.1.98

-- END 3.1.99

-- END 3.1.100

ALTER TABLE cireports_deliverygroup ADD COLUMN `createdDate` timestamp NULL;
ALTER TABLE cireports_deliverygroup ADD COLUMN `deliveredDate` timestamp NULL;

-- END 3.1.101

ALTER TABLE dmt_lvsroutervip ADD COLUMN fm_external_ipv6_id int UNSIGNED NULL AFTER fm_external_id;
ALTER TABLE dmt_lvsroutervip ADD COLUMN cm_external_ipv6_id int UNSIGNED NULL AFTER cm_external_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `fmexternalipv6_2_ipv6` FOREIGN KEY (`fm_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `cmexternalipv6_2_ipv6` FOREIGN KEY (`cm_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.1.102

-- END 3.1.103

-- END 3.1.104

ALTER TABLE dmt_sed MODIFY jiraNumber VARCHAR(20) NOT NULL;

-- END 3.1.105

-- END 3.1.106

-- END 3.1.107

-- END 3.1.108

-- END 3.1.109

-- END 3.1.110

-- END 3.1.111

-- END 3.1.112

-- END 3.1.113

-- END 3.1.114

-- END 3.1.115

-- END 3.2.1

-- END 3.2.2

-- END 3.2.3

-- END 3.2.4

CREATE TABLE `cireports_isotodeliverygroupmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `iso_id` smallint UNSIGNED NOT NULL,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `deliveryGroup_status` varchar(20) NOT NULL,
    `modifiedDate` timestamp NOT NULL
) ENGINE=InnoDB;

-- END 3.2.5

-- END 3.2.6

-- END 3.2.7

-- END 3.2.8

-- END 3.2.9

-- END 3.2.10

-- END 3.2.11

-- END 3.2.12

-- END 3.2.13

-- END 3.2.14

-- END 3.2.15

-- END 3.2.16

-- END 3.2.17

-- END 3.2.18

-- END 3.2.19

-- END 3.2.20

-- END 3.2.21

-- END 3.2.22

-- END 3.2.23

-- END 3.2.24

-- END 3.2.25
ALTER TABLE cireports_packagerevision ADD COLUMN team_running_kgb_id smallint UNSIGNED AFTER kgb_test;
ALTER TABLE cireports_packagerevision ADD CONSTRAINT packagerevision_2_teamkgb FOREIGN KEY (`team_running_kgb_id`) REFERENCES `cireports_component` (`id`);
ALTER TABLE cireports_product ADD COLUMN teamRunningKgb bool NOT NULL DEFAULT 0 AFTER kgbTests;
CREATE TABLE `cireports_productsetvertocdbtypemap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `productSetVersion_id` integer UNSIGNED NOT NULL,
    `productCDBType_id` smallint UNSIGNED NOT NULL,
    `runningStatus` bool NOT NULL DEFAULT 0,
    `override` bool NOT NULL DEFAULT 0,
    UNIQUE (`productSetVersion_id`, `productCDBType_id`),
    CONSTRAINT `prodsetvermap_2_prodSetVer` FOREIGN KEY (`productSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`),
    CONSTRAINT `prodsetvermap_2_prodCDBType` FOREIGN KEY (`productCDBType_id`) REFERENCES `cireports_productdroptocdbtypemap` (`id`)
) ENGINE=InnoDB;

-- END 3.2.26

-- END 3.2.27

-- END 3.2.28

-- END 3.2.29

-- END 3.2.30

-- END 3.2.31

-- END 3.2.32
ALTER TABLE `cireports_testwarerevision` ADD COLUMN `validTestPom` bool NOT NULL DEFAULT 1 after execution_artifactId;

-- END 3.2.33
ALTER TABLE `cireports_testresults` MODIFY `test_report_directory` varchar(200);

-- END 3.2.34

-- END 3.2.35

-- END 3.2.36

-- END 3.2.37

-- END 3.2.38

-- END 3.2.39

-- END 3.2.40

-- END 3.2.41

-- END 3.2.42

-- END 3.2.43

-- END 3.2.44

-- END 3.2.45
ALTER TABLE `dmt_clusterserver` ADD COLUMN `active` bool NOT NULL DEFAULT 1;

-- END 3.2.46

-- END 3.2.47

-- END 3.2.48

-- END 3.2.49

-- END 3.2.50

-- END 3.2.51
ALTER TABLE `cireports_testwareartifact` ADD COLUMN `includedInPriorityTestSuite` bool NOT NULL DEFAULT 0;

-- END 3.2.52

-- END 3.2.53

-- END 3.2.54

-- END 3.2.55

-- END 3.2.56

-- END 3.2.57

-- END 3.2.58

-- END 3.2.59
ALTER TABLE cireports_isobuild ADD COLUMN `mt_utils_version` varchar(100);

-- END 3.2.60

-- END 3.2.61

-- END 3.2.62

-- END 3.3.1

-- END 3.3.2

-- END 3.3.3
ALTER TABLE dmt_deploymentbaseline ADD COLUMN productset_id varchar(50) NOT NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN deliveryGroup varchar(3000) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN jobOwner varchar(50) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN shortLoopAllureReport varchar(100) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN teAllureLogUrl varchar(100) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN allureReport varchar(100) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN availability varchar(50) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN buildURL varchar(100) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN deploytime varchar(50) NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN slot int NOT NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN installType varchar(100);
ALTER TABLE dmt_deploymentbaseline ADD COLUMN upgradeTestingStatus varchar(100);
ALTER TABLE dmt_deploymentbaseline ADD COLUMN upgradeTestingBuildURL varchar(100);
ALTER TABLE dmt_deploymentbaseline ADD COLUMN shortLoopURL varchar(100);
ALTER TABLE dmt_deploymentbaseline ADD COLUMN status varchar(50) NOT NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN comment longtext NULL;
ALTER TABLE dmt_deploymentbaseline ADD COLUMN fromISO varchar(100) NULL AFTER mediaArtifact;
TRUNCATE dmt_deploymentbaseline;

ALTER TABLE `dmt_ipaddress` MODIFY `ipv6_address` char(60);

-- END 3.3.4

-- END 3.3.5
ALTER TABLE cireports_deliverygroup ADD COLUMN `autoCreated` bool NOT NULL;

-- END 3.3.6

-- END 3.3.7

-- END 3.3.8

-- END 3.3.9

-- END 3.3.10

-- END 3.3.11
CREATE TABLE `cireports_deliverygroupsubscription` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    UNIQUE (`user_id`, `deliveryGroup_id`),
    CONSTRAINT `deliverygroup_subscription` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`)
) ENGINE=InnoDB;
ALTER TABLE `cireports_categories` MODIFY `name` varchar(100) NOT NULL UNIQUE;

-- END 3.3.12

-- END 3.3.13

-- END 3.3.14

-- END 3.3.15

-- END 3.3.16
CREATE TABLE `fastcommit_dockerimage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `fastcommit_dockerimageversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_id` integer UNSIGNED NOT NULL,
    `version`  varchar(25) NOT NULL,
    UNIQUE INDEX imageVersion (`image_id`, `version`),
    CONSTRAINT `dockerimageversion_2_image` FOREIGN KEY (`image_id`) REFERENCES `fastcommit_dockerimage` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `fastcommit_dockerimageversioncontents` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_version_id` integer UNSIGNED NOT NULL,
    `package_revision_id` integer UNSIGNED NOT NULL,
    UNIQUE INDEX imagePackage (`image_version_id`, `package_revision_id`),
    CONSTRAINT `dockerimageversioncontents_2_image_version` FOREIGN KEY (`image_version_id`) REFERENCES `fastcommit_dockerimageversion` (`id`),
    CONSTRAINT `dockerimageversioncontents_2_package_revision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;

-- END 3.4.1

-- END 3.4.2

-- END 3.4.3

-- END 3.4.4

-- END 3.4.5
ALTER TABLE `dmt_enclosure` ADD COLUMN `san_sw_bay_1` varchar(2);
ALTER TABLE `dmt_enclosure` ADD COLUMN `san_sw_bay_2` varchar(2);
ALTER TABLE `dmt_enclosure` ADD COLUMN `vc_module_bay_1` varchar(2);
ALTER TABLE `dmt_enclosure` ADD COLUMN `vc_module_bay_2` varchar(2);

-- END 3.4.6

-- END 3.4.7

-- END 3.4.8

-- END 3.4.9

-- END 3.4.10

-- END 3.4.11

-- END 3.4.12

-- END 3.4.13

-- END 3.4.14

-- END 3.4.15

-- END 3.4.16

-- END 3.4.17

-- END 3.4.18

-- END 3.4.19
ALTER TABLE `dmt_server` ADD COLUMN `name` varchar(30) NULL AFTER `id`;
UPDATE `dmt_server` set `name` = `hostname` where `name` is NULL;
ALTER TABLE `dmt_storage` ADD COLUMN `name` varchar(30) NULL AFTER `id`;
UPDATE `dmt_storage` set `name` = `hostname` where `name` is NULL;
ALTER TABLE dmt_lvsroutervip ADD COLUMN str_internal_id int UNSIGNED NULL AFTER events_internal_id;
ALTER TABLE dmt_lvsroutervip ADD COLUMN str_external_id int UNSIGNED NULL AFTER str_internal_id;
ALTER TABLE dmt_lvsroutervip ADD COLUMN str_external_ipv6_id int UNSIGNED NULL AFTER str_external_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strinternal_2_ip` FOREIGN KEY (`str_internal_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strexternal_2_ip` FOREIGN KEY (`str_external_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strexternalipv6_2_ipv6` FOREIGN KEY (`str_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);
CREATE TABLE `cireports_testcaseresult` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `passed` smallint UNSIGNED ,
    `failed` smallint UNSIGNED ,
    `skipped` smallint UNSIGNED
) ENGINE=InnoDB
;
CREATE TABLE `cireports_packagewithtestcaseresult` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testdate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `package_id` smallint UNSIGNED NOT NULL,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `drop_id` smallint UNSIGNED NOT NULL,
    `testcaseresult_id` integer UNSIGNED NOT NULL,
    `phase` varchar(20),
    CONSTRAINT `testcaseresult_1_package_revision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `testcaseresult_1_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `testcaseresult_1_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `testcaseresult_1_results` FOREIGN KEY (`testcaseresult_id`) REFERENCES `cireports_testcaseresult` (`id`)

) ENGINE=InnoDB
;

-- END 3.4.20

-- END 3.4.21

-- END 3.5.1

-- END 3.5.2

-- END 3.5.3

-- END 3.5.4

-- END 3.5.5

-- END 3.5.6
TRUNCATE dmt_deploymentbaseline;

-- END 3.5.7

-- END 3.5.8

-- END 3.5.9

-- END 3.5.10
ALTER TABLE `dmt_cluster` MODIFY `mac_lowest` varchar(18) NULL;
ALTER TABLE `dmt_cluster` MODIFY `mac_highest` varchar(18) NULL;

-- END 3.5.11

-- END 3.5.12

-- END 3.5.13

-- END 3.5.14
ALTER TABLE `dmt_iprange` MODIFY `start_ip` char(60) NOT NULL UNIQUE;
ALTER TABLE `dmt_iprange` MODIFY `end_ip` char(60) NOT NULL UNIQUE;
ALTER TABLE `dmt_iprange` MODIFY `gateway` char(60) NULL;

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `fm_internal_ipv6_id` int UNSIGNED NULL AFTER `fm_external_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `fminternalipv6_2_ipv6` FOREIGN KEY (`fm_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_vlandetails` ADD COLUMN `internal_ipv6_subnet` varchar(42) NULL AFTER `internal_subnet`;

CREATE TABLE `dmt_deploymentutilities` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `utility` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `dmt_deploymentutilitiesversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `utility_name_id` integer UNSIGNED NOT NULL,
    `utility_version` varchar(50) NOT NULL,
    `utility_label` varchar(50),
    UNIQUE (`utility_name_id`, `utility_version`),
    CONSTRAINT `utility_2_utilityversion` FOREIGN KEY (`utility_name_id`) REFERENCES `dmt_deploymentutilities` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_deploymentutilstoisobuild` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `utility_version_id` integer UNSIGNED NOT NULL,
    `iso_build_id` smallint UNSIGNED NOT NULL,
    `active` bool NOT NULL,
    CONSTRAINT `utilityversion_2_isobuild` FOREIGN KEY (`utility_version_id`) REFERENCES `dmt_deploymentutilitiesversion` (`id`),
    CONSTRAINT `isobuild_2_utilityversion` FOREIGN KEY (`iso_build_id`) REFERENCES `cireports_isobuild` (`id`)
) ENGINE=InnoDB;

-- END 3.5.15

-- END 3.5.16

-- END 3.5.17
ALTER TABLE `dmt_lvsroutervip` DROP FOREIGN KEY `storageinternal_2_ip`, CHANGE `storage_internal_id` `svc_storage_internal_id` integer UNSIGNED NOT NULL, ADD CONSTRAINT `svcstgint_2_ip` FOREIGN KEY (`svc_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE `dmt_lvsroutervip` DROP FOREIGN KEY `eventsinternal_2_ip`, DROP FOREIGN KEY `scriptinginternal_2_ip`, CHANGE `scripting_internal_id` `scp_storage_internal_id` integer UNSIGNED NOT NULL, CHANGE `events_internal_id` `evt_storage_internal_id` integer UNSIGNED NOT NULL, ADD CONSTRAINT `scpstgint_2_ip` FOREIGN KEY (`scp_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`), ADD CONSTRAINT `evtstgint_2_ip` FOREIGN KEY (`evt_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `svc_pm_storage_id` int UNSIGNED NULL AFTER `cm_external_ipv6_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `svcpmstg_2_ip` FOREIGN KEY (`svc_pm_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `svc_fm_storage_id` int UNSIGNED NULL AFTER `svc_pm_storage_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `svcfmstg_2_ip` FOREIGN KEY (`svc_fm_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `svc_cm_storage_id` int UNSIGNED NULL AFTER `svc_fm_storage_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `svccmstg_2_ip` FOREIGN KEY (`svc_cm_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `svc_storage_id` int UNSIGNED NULL AFTER `svc_storage_internal_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `svcstg_2_ip` FOREIGN KEY (`svc_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `scp_storage_id` int UNSIGNED NULL AFTER `scp_storage_internal_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `scpstg_2_ip` FOREIGN KEY (`scp_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `evt_storage_id` int UNSIGNED NULL AFTER `evt_storage_internal_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `evtstg_2_ip` FOREIGN KEY (`evt_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `str_str_storage_id` int UNSIGNED NULL AFTER `str_external_ipv6_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `strstrstg_2_ip` FOREIGN KEY (`str_str_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `str_storage_internal_id` int UNSIGNED NULL AFTER `str_str_storage_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `strstgint_2_ip` FOREIGN KEY (`str_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `str_storage_id` int UNSIGNED NULL AFTER `str_storage_internal_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `strstg_2_ip` FOREIGN KEY (`str_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.6.1

-- END 3.6.2

-- END 3.6.3

-- END 3.6.4
INSERT INTO cireports_categories (name) VALUES ("automation");

-- END 3.6.5
ALTER TABLE `dmt_lvsroutervip` MODIFY `scp_storage_internal_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `scp_storage_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `evt_storage_internal_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `evt_storage_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `str_internal_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `str_external_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `str_external_ipv6_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `str_str_storage_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `str_storage_internal_id` integer UNSIGNED NULL;
ALTER TABLE `dmt_lvsroutervip` MODIFY `str_storage_id` integer UNSIGNED NULL;

-- END 3.6.6

-- END 3.6.7

-- END 3.6.8

-- END 3.6.9

-- END 3.6.10

-- END 3.6.11

-- END 3.6.12

-- END 3.6.13

-- END 3.6.14

-- END 3.6.15

-- END 3.6.16

-- END 3.6.17
CREATE TABLE `cireports_reasonsfornokgbstatus` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reason` varchar(255) NOT NULL,
    `active` bool NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `cireports_groupscreatedwithoutpassedkgbtest` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `group_id` integer UNSIGNED,
    `reason` varchar(255) NOT NULL,
    `comment` longtext,
    CONSTRAINT `group_2_nopassedkgb` FOREIGN KEY (`group_id`) REFERENCES `cireports_deliverygroup` (`id`)
) ENGINE=InnoDB
;

-- END 3.6.18

-- END 3.6.19

-- END 3.6.20

-- END 3.6.21

-- END 3.6.22

-- END 3.7.1

-- END 3.7.2

-- END 3.7.3

-- END 3.7.4

-- END 3.7.5

-- END 3.7.6

-- END 3.7.7

-- END 3.7.8
ALTER TABLE `cireports_deliverytopackagerevmapping` ADD COLUMN `kgb_test` varchar(20) NULL;
ALTER TABLE `cireports_deliverytopackagerevmapping` ADD COLUMN  `testReport` longtext NULL;

ALTER TABLE `cireports_droppackagemapping` ADD COLUMN `kgb_test` varchar(20) NULL;
ALTER TABLE `cireports_droppackagemapping` ADD COLUMN  `testReport` longtext NULL;

-- END 3.7.9
ALTER TABLE `cireports_isobuildmapping` ADD COLUMN `kgb_test` varchar(20) NULL;
ALTER TABLE `cireports_isobuildmapping` ADD COLUMN `testReport` longtext NULL;

-- END 3.7.10

-- END 3.7.11

-- END 3.7.12

-- END 3.7.13

-- END 3.7.14

-- END 3.7.15

-- END 3.7.16

-- END 3.7.17

-- END 3.7.18
ALTER TABLE dmt_deploymentbaseline MODIFY jobOwner VARCHAR(2000);
ALTER TABLE `dmt_deploymentbaseline` CHANGE `jobOwner` `rfaStagingResult` VARCHAR(2000) NULL;
ALTER TABLE `dmt_deploymentbaseline` CHANGE `shortLoopAllureReport` `rfaResult` VARCHAR(2000) NULL;
ALTER TABLE `dmt_deploymentbaseline` CHANGE `upgradeTestingBuildURL` `rfaPercent` VARCHAR(5) NULL;
ALTER TABLE `dmt_deploymentbaseline` CHANGE `allureReport` `upgradeAvailabilityResult` VARCHAR(2000) NULL;
ALTER TABLE `dmt_deploymentbaseline` CHANGE `packages` `upgradePerformancePercent` VARCHAR(5) NULL;

-- END 3.7.19

-- END 3.7.20

-- END 3.7.21

-- END 3.7.22

-- END 3.7.23

-- END 3.7.24

-- END 3.8.1
CREATE TABLE `dmt_consolidatedtoconstituentmap` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `consolidated` varchar(50) NOT NULL,
    `constituent` varchar(50) NOT NULL
) ENGINE=InnoDB;

INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("presentation","lcmserv");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("presentation","netex");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("presentation","uiserv");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("presentation","wpserv");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("security","access-control");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("security","pkiraserv");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("security","secserv");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("medcore","comecimpolicy");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("medcore","eventbasedclient");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("medcore","medrouter");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("medcore","supervc");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("fm","fmalarmprocessing");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("fm","fmhistory");
INSERT INTO `dmt_consolidatedtoconstituentmap` (`consolidated`,`constituent`) VALUES ("fm","fmservice");

ALTER TABLE dmt_ipaddress DROP INDEX ipv4Identity;
ALTER TABLE dmt_ipaddress DROP INDEX ipv6Identity;

CREATE TABLE `dmt_vlanmulticasttype` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(10) NOT NULL UNIQUE,
    `description` longtext NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_vlanmulticast` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `clusterserver_id` integer unsigned NOT NULL,
    `multicast_type_id` smallint UNSIGNED NOT NULL,
    `multicast_snooping` varchar(1) NOT NULL,
    `multicast_querier`   varchar(1) NOT NULL,
    `multicast_router`   varchar(1) NOT NULL,
    `hash_max` varchar(20) NOT NULL,
    UNIQUE (`clusterserver_id`, `multicast_type_id`),
    CONSTRAINT `vlanmulticast_2_vlanmulticasttype` FOREIGN KEY (`multicast_type_id`) REFERENCES `dmt_vlanmulticasttype` (`id`),
    CONSTRAINT `vlanmulticast_2_clusterserver` FOREIGN KEY (`clusterserver_id`) REFERENCES `dmt_clusterserver` (`id`)
) ENGINE=InnoDB;


-- END 3.8.2

-- END 3.8.3

-- END 3.8.4

-- END 3.8.5

-- END 3.8.6

-- END 3.8.7
ALTER TABLE dmt_ipaddress ADD COLUMN `override` bool NOT NULL DEFAULT 0;

-- END 3.8.8

-- END 3.8.9

-- END 3.8.10

-- END 3.8.11

-- END 3.8.12

-- END 3.8.13

-- END 3.8.14
CREATE TABLE `dmt_vmservicename` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_vmservicepackagemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `service_id` smallint UNSIGNED NOT NULL,
    `package_id` smallint UNSIGNED NOT NULL,
    `active` bool NOT NULL,
    CONSTRAINT `vmservicepackagemapping_2_vmservicename` FOREIGN KEY (`service_id`) REFERENCES `dmt_vmservicename` (`id`),
    CONSTRAINT `vmservicepackagemapping_2_artifact` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB;

-- END 3.8.15

-- END 3.8.16

-- END 3.8.17

-- END 3.8.18

-- END 3.8.19
ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `cm_internal_ipv6_id` integer UNSIGNED NULL AFTER `cm_external_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `cminternalipv6_2_ipv6` FOREIGN KEY (`cm_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `scp_scp_internal_id` int UNSIGNED NULL AFTER `svc_storage_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `scpscpinternal_2_ip` FOREIGN KEY (`scp_scp_internal_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `scp_scp_external_id` int UNSIGNED NULL AFTER `scp_scp_internal_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `scpscpexternal_2_ip` FOREIGN KEY (`scp_scp_external_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `scp_scp_internal_ipv6_id` int UNSIGNED NULL AFTER `scp_scp_external_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `scpscpinternalipv6_2_ipv6` FOREIGN KEY (`scp_scp_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `scp_scp_external_ipv6_id` int UNSIGNED NULL AFTER `scp_scp_internal_ipv6_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `scpscpexternalipv6_2_ipv6` FOREIGN KEY (`scp_scp_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

CREATE TABLE `cireports_autodeliverteam` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `team_id` smallint UNSIGNED,
    CONSTRAINT `autodeliver_2_component` FOREIGN KEY (`team_id`) REFERENCES `cireports_component` (`id`)
) ENGINE=InnoDB;

-- END 3.8.20

-- END 3.8.21

-- END 3.8.22

-- END 3.8.23
CREATE TABLE `dmt_hybridcloud` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `ip_type` varchar(5) NULL,
    `internal_subnet` varchar(18) NULL,
    `gateway_internal_id` integer UNSIGNED NULL,
    `gateway_external_id` integer UNSIGNED NULL,
    `internal_subnet_ipv6` varchar(42) NULL,
    `gateway_internal_ipv6_id` integer UNSIGNED NULL,
    `gateway_external_ipv6_id` integer UNSIGNED NULL,

    CONSTRAINT `hybridcloud_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `hybridcloud_2_ipinternal` FOREIGN KEY (`gateway_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `hybridcloud_2_ipexternal` FOREIGN KEY (`gateway_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `hybridcloud_2_ipv6internal` FOREIGN KEY (`gateway_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `hybridcloud_2_ipv6external` FOREIGN KEY (`gateway_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB;

-- END 3.8.24

-- END 3.8.25

-- END 3.8.26

-- END 3.8.27

-- END 3.8.28

-- END 3.8.29
ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `str_str_internal_ipv6_id` int UNSIGNED NULL AFTER `str_external_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `strstrintipv6_2_ipv6` FOREIGN KEY (`str_str_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.8.30

-- END 3.8.31

-- END 3.8.32

-- END 3.8.33
CREATE TABLE `fwk_pagehitcount` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `page_object_id` integer UNSIGNED NULL,
    `page` varchar(100) NOT NULL,
    `hitcount` integer UNSIGNED NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `fwk_userpagehitcount` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `username_id` int(11) NOT NULL,
    `page_id` integer UNSIGNED NULL,
    `hitcount` integer UNSIGNED NOT NULL,
    CONSTRAINT `userpagehitcount_2_pagehitcount` FOREIGN KEY (`page_id`) REFERENCES `fwk_pagehitcount` (`id`)
) ENGINE=InnoDB
;

-- END 3.8.34

-- END 3.8.35
CREATE TABLE `dmt_deploymentdhcpjumpserverdetails` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `server_type` varchar(50) NOT NULL,
    `server_user` varchar(50) NOT NULL,
    `server_password` varchar(50) NOT NULL,
    `ecn_ip` char(39),
    `edn_ip` char(39),
    `youlab_ip` char(39)
) ENGINE=InnoDB;

-- END 3.8.36

-- END 3.8.37

-- END 3.8.38
CREATE TABLE `dmt_deploymentdescriptiontype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dd_type` varchar(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_deploymentdescriptionversion` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `version` varchar(100) NOT NULL,
    `latest` bool DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE `dmt_deploymentdescription` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `version_id` smallint UNSIGNED NOT NULL,
    `dd_type_id` smallint UNSIGNED NOT NULL,
    `name` varchar(200) NOT NULL,
    `auto_deployment` varchar(255) NOT NULL,
    `sed_deployment` varchar(255) NOT NULL,

    CONSTRAINT `dd_2_ddtype` FOREIGN KEY (`dd_type_id`) REFERENCES `dmt_deploymentdescriptiontype` (`id`),
    CONSTRAINT `dd_2_ddversion` FOREIGN KEY (`version_id`) REFERENCES `dmt_deploymentdescriptionversion` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_ddtodeploymentmapping` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deployment_description_id` integer UNSIGNED NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `auto_update` bool DEFAULT 0,

    CONSTRAINT `ddtodeploymentmap_2_dd` FOREIGN KEY (`deployment_description_id`) REFERENCES `dmt_deploymentdescription` (`id`),
    CONSTRAINT `ddtodeploymentmap_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

-- END 3.8.39
CREATE TABLE `dmt_vlanclustermulticast` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint unsigned NOT NULL,
    `multicast_type_id` smallint UNSIGNED NOT NULL,
    `multicast_snooping` varchar(1) NOT NULL,
    `multicast_querier`   varchar(1) NOT NULL,
    `multicast_router`   varchar(1) NOT NULL,
    `hash_max` varchar(20) NOT NULL,
    UNIQUE (`cluster_id`, `multicast_type_id`),
    CONSTRAINT `vlanclustermulticast_2_vlanmulticasttype` FOREIGN KEY (`multicast_type_id`) REFERENCES `dmt_vlanmulticasttype` (`id`),
    CONSTRAINT `vlanclustermulticast_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

-- END 3.8.40


-- END 3.8.41
ALTER TABLE `dmt_ddtodeploymentmapping` ADD COLUMN `update_type` varchar(20) NULL;

-- END 3.9.1

-- END 3.9.2

ALTER TABLE `cireports_deliverygroup` ADD COLUMN `consolidatedGroup` bool NOT NULL;


-- END 3.9.3

-- END 3.9.4

-- END 3.9.5

-- END 3.9.6

-- END 3.9.7

-- END 3.9.8

-- END 3.9.9

-- END 3.9.10

-- END 3.9.11

-- END 3.9.12

-- END 3.9.13

-- END 3.9.14

-- END 3.9.15

-- END 3.9.16

-- END 3.9.17

-- END 3.9.18

-- END 3.9.19

-- END 3.9.20
ALTER TABLE `cireports_packagerevision` ADD COLUMN  `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0 after `kgb_test`;
ALTER TABLE `cireports_deliverytopackagerevmapping` ADD COLUMN  `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE `cireports_droppackagemapping` ADD COLUMN  `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE `cireports_isobuildmapping` ADD COLUMN `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0;

-- END 3.10.1
ALTER TABLE `cireports_deliverygroup` ADD COLUMN `newArtifact` bool NOT NULL;

-- END 3.10.2
ALTER TABLE `cireports_deliverygroup` ADD COLUMN `ccbApproved` bool NOT NULL;

-- END 3.10.3

-- END 3.10.4

-- END 3.10.5

-- END 3.10.6

-- END 3.10.7
CREATE TABLE `dmt_updateddeploymentsummarylog` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `createdDate` datetime  NOT NULL,
    `dd_version_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `summarylog_2_ddversion` FOREIGN KEY (`dd_version_id`) REFERENCES `dmt_deploymentdescriptionversion` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_updateddeploymentlog` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `summary_log_id` integer UNSIGNED NULL,
    `cluster_id` smallint unsigned NOT NULL,
    `createdDate` datetime NOT NULL,
    `deployment_description_id` integer UNSIGNED NULL,
    `log` longtext NOT NULL,
    `status` varchar(10) NOT NULL,

    CONSTRAINT `updateddeploymentlog_2_summaryLog` FOREIGN KEY (`summary_log_id`) REFERENCES `dmt_updateddeploymentsummarylog` (`id`),
    CONSTRAINT `updateddeploymentlog_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `updateddeploymentlog_2_dd` FOREIGN KEY (`deployment_description_id`) REFERENCES `dmt_deploymentdescription` (`id`)
) ENGINE=InnoDB;

-- END 3.10.8
ALTER TABLE `cireports_deliverytopackagerevmapping` ADD COLUMN  `newArtifact` BOOLEAN NOT NULL DEFAULT 0;

-- END 3.10.9

-- END 3.10.10

-- END 3.10.11

-- END 3.10.12

-- END 3.10.13

-- END 3.10.14

-- END 3.10.15
ALTER TABLE dmt_deploymentbaseline ADD COLUMN `fromISODrop` varchar(100) AFTER `fromISO`;

-- END 3.11.1

-- END 3.11.2

-- END 3.11.3

-- END 3.11.4

-- END 3.11.5

-- END 3.11.6

-- END 3.11.7

-- END 3.11.8

-- END 3.11.9

-- END 3.11.10

-- END 3.11.11

-- END 3.11.12

-- END 3.11.13

-- END 3.11.14
CREATE TABLE `dmt_autovmservicednsiprange` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ipv4AddressStart` char(15),
    `ipv4AddressEnd` char(15),
    `ipv6AddressStart` char(39),
    `ipv6AddressEnd` char(39),
    `ipType_id` smallint unsigned NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `ipType_id_2_vmserviceiprangeitem` FOREIGN KEY (`ipType_id`) REFERENCES `dmt_vmserviceiprangeitem` (`id`),
    CONSTRAINT `autovmservicednsiprange_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

-- END 3.11.15

-- END 3.11.16

-- END 3.11.17

-- END 3.11.18

-- END 3.11.19

-- END 3.11.20

-- END 3.11.21
CREATE TABLE `cireports_droplimitedreason` (
    `id`  smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reason` varchar(100) NOT NULL
) ENGINE=InnoDB
;
ALTER TABLE `cireports_dropactivity` ADD COLUMN `limitedReason_id` smallint UNSIGNED NULL;
ALTER TABLE `cireports_dropactivity` ADD CONSTRAINT `dropactivity_2_limitedreason` FOREIGN KEY (`limitedReason_id`) REFERENCES `cireports_droplimitedreason` (`id`);

-- END 3.11.22

-- END 3.11.23

-- END 3.11.24

-- END 3.11.25

-- END 3.11.26

-- END 3.11.27

-- END 3.11.28

-- END 3.11.29

-- END 3.11.30

-- END 3.11.31

-- END 3.11.32

-- END 3.11.33

-- END 3.11.34

-- END 3.11.35

-- END 3.11.36

-- END 3.11.37
CREATE TABLE `dmt_virtualautobuildlogclusters` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;
INSERT INTO dmt_virtualautobuildlogclusters(name) VALUES("enmcloud11");
INSERT INTO dmt_virtualautobuildlogclusters(name) VALUES("enmcloud12");

-- END 3.11.38

-- END 3.11.39

-- END 3.11.40

-- END 3.11.41

-- END 3.11.42

-- END 3.11.43
ALTER TABLE dmt_autovmservicednsiprange drop foreign key ipType_id_2_vmserviceiprangeitem;
ALTER TABLE dmt_autovmservicednsiprange CHANGE ipType_id ipTypeId_id smallint unsigned NOT NULL;
ALTER TABLE dmt_autovmservicednsiprange ADD CONSTRAINT `ipType_id_2_vmserviceiprangeitem` FOREIGN KEY (`ipTypeId_id`) REFERENCES `dmt_vmserviceiprangeitem` (`id`);
ALTER TABLE `dmt_ddtodeploymentmapping` ADD COLUMN `iprange_type` varchar(20) NULL DEFAULT 'dns';

-- END 3.12.1

-- END 3.12.2

-- END 3.12.3

-- END 3.12.4

-- END 3.12.5

-- END 3.12.6

-- END 3.12.7

-- END 3.12.8

-- END 3.12.9

-- END 3.12.10
ALTER TABLE cireports_document ADD COLUMN `obsolete_after_id` smallint UNSIGNED AFTER `comment`;
ALTER TABLE cireports_document ADD CONSTRAINT `doc_2_drop` FOREIGN KEY (`obsolete_after_id`) REFERENCES `cireports_drop` (`id`);

-- END 3.12.11

-- END 3.12.12

-- END 3.12.13

-- END 3.12.14

-- END 3.13.1

-- END 3.13.2

-- END 3.13.3

-- END 3.13.4

-- END 3.13.5

-- END 3.13.6

-- END 3.13.7

-- END 3.13.8

-- END 3.13.9

-- END 3.13.10

-- END 3.13.11

-- END 3.13.12

-- END 3.13.13

-- END 3.13.14

-- END 3.13.15

-- END 3.13.16

-- END 3.13.17

-- END 3.13.18

-- END 3.13.19

-- END 3.13.20

-- END 3.13.21

-- END 3.13.22

-- END 3.14.1

-- END 3.14.2

-- END 3.14.3
CREATE TABLE `cireports_jiratypeexclusion` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `jiraType` varchar(30) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT INTO cireports_jiratypeexclusion(jiraType) VALUES("Support");
INSERT INTO cireports_jiratypeexclusion(jiraType) VALUES("Spike");

-- END 3.14.4

-- END 3.14.5

-- END 3.14.6

-- END 3.14.7
ALTER TABLE `dmt_deploymentdhcpjumpserverdetails` ADD COLUMN `gtec_youlab_ip` char(39);
ALTER TABLE `dmt_deploymentdhcpjumpserverdetails` ADD COLUMN `gtec_edn_ip` char(39);

-- END 3.14.8

-- END 3.14.9

-- END 3.14.10
ALTER TABLE `cireports_deliverygroup` ADD COLUMN `bugOrTR` bool NOT NULL;

-- END 3.14.11

-- END 3.14.12

-- END 3.14.13

-- END 3.14.14

-- END 3.14.15

-- END 3.14.16

-- END 3.14.17
ALTER TABLE `dmt_deploymentdescription` ADD COLUMN `capacity_type` varchar(12) NULL DEFAULT 'test' AFTER `name`;

-- END 3.14.18

-- END 3.14.19

-- END 3.14.20

-- END 3.14.21
CREATE TABLE `dmt_rackhardwaredetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `clusterserver_id` integer unsigned NOT NULL,
    `bootdisk_uuid` varchar(32) NOT NULL UNIQUE,
    `serial_number` varchar(18) NOT NULL UNIQUE,
    CONSTRAINT `rackhardwaredetails_2_clusterserver` FOREIGN KEY (`clusterserver_id`) REFERENCES `dmt_clusterserver` (`id`)
) ENGINE=InnoDB;


-- END 3.15.1

-- END 3.15.2


-- END 3.15.3

-- END 3.15.4

-- END 3.15.5

-- END 3.15.6

-- END 3.15.7

-- END 3.15.8

-- END 3.15.9

-- END 3.15.10

-- END 3.15.11

-- END 3.15.12

-- END 3.15.13

-- END 3.15.14
ALTER TABLE `cireports_component` ADD COLUMN `deprecated` bool NOT NULL DEFAULT 0;

-- END 3.15.15

-- END 3.15.16

-- END 3.15.17

-- END 3.15.18

-- END 3.15.19

-- END 3.15.20

-- END 3.15.21
CREATE TABLE `foss_gerritrepo` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `repo_name` VARCHAR(200) NOT NULL UNIQUE,
    `owner` VARCHAR(50) NOT NULL
) ENGINE = InnoDB;
CREATE TABLE `foss_scanversion` (
    `id` INTEGER UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `start_time` datetime not null default "1970-01-01 00:00:00",
    `status` BOOL NOT NULL DEFAULT "0"
) ENGINE = InnoDB;
CREATE TABLE `foss_scanmapping` (
    `id` INTEGER UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `scan_version_id` INTEGER  UNSIGNED NOT NULL,
    `gerrit_repo_id` SMALLINT UNSIGNED NOT NULL,
    `audit_id` VARCHAR(30) NOT NULL UNIQUE,
    `project_id` VARCHAR(10) NOT NULL,
    `report_url` VARCHAR(200) NOT NULL UNIQUE,
    `start_time` datetime not null default "1970-01-01 00:00:00",
    `end_time` datetime not null default "1970-01-01 00:00:00",
    CONSTRAINT `scanmapping_2_scanversion` FOREIGN KEY (`scan_version_id`) REFERENCES `foss_scanversion` (`id`),
    CONSTRAINT `scanmapping_2_gerritrepo` FOREIGN KEY (`gerrit_repo_id`) REFERENCES `foss_gerritrepo` (`id`)
) ENGINE = InnoDB;

-- END 3.15.22

-- END 3.15.23
ALTER TABLE `foss_scanmapping` MODIFY `end_time` datetime default "1970-01-01 00:00:00";
ALTER TABLE `foss_scanmapping` ADD COLUMN `status` VARCHAR(50) NOT NULL;

-- END 3.15.24

-- END 3.15.25

-- END 3.15.26

-- END 3.15.27

-- END 3.15.28

-- END 3.15.29

-- END 3.15.30

-- END 3.15.31

-- END 3.15.32

-- END 3.15.33

-- END 3.15.34

-- END 3.15.35
ALTER TABLE `cireports_packagerevision` ADD COLUMN `size` INTEGER UNSIGNED NOT NULL default 0;

-- END 3.15.36
ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `scp_scp_storage_id` int UNSIGNED NULL AFTER `scp_scp_external_ipv6_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `scpscpstg_2_ip` FOREIGN KEY (`scp_scp_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.15.37

-- END 3.15.38

-- END 3.15.39

-- END 3.15.40

-- END 3.15.41
ALTER TABLE `cireports_product` ADD COLUMN `size` bool NOT NULL default 1;

-- END 3.15.42

-- END 3.15.43

-- END 3.15.44

-- END 3.15.45

-- END 3.15.46

-- END 3.15.47

-- END 3.15.48

-- END 3.15.49
ALTER TABLE `cireports_isobuild` ADD COLUMN `size` BIGINT UNSIGNED NOT NULL default 0;

-- END 3.15.50

-- END 3.15.51

-- END 3.15.52

-- END 3.15.53

-- END 3.15.54

-- END 3.15.55

-- END 3.15.56

-- END 3.15.57

-- END 3.15.58

-- END 3.15.59

-- END 3.15.60

-- END 3.15.61

-- END 3.15.62

-- END 3.15.63

-- END 3.15.64

-- END 3.15.65

-- END 3.15.66

-- END 3.15.67

-- END 3.15.68

-- END 3.15.69

-- END 3.15.70

-- END 3.15.71

-- END 3.15.72

-- END 3.15.73

-- END 3.15.74

-- END 3.15.75

-- END 3.15.76

-- END 3.15.77

-- END 3.15.78

-- END 3.15.79

-- END 3.15.80

-- END 3.15.81

-- END 3.15.82

-- END 3.15.83

-- END 3.15.84

-- END 3.15.85

-- END 3.15.86

-- END 3.15.87

-- END 3.15.88

-- END 3.15.89

-- END 3.15.90

-- END 3.15.91

-- END 3.15.92

ALTER TABLE `cireports_productsetversion` MODIFY COLUMN  `current_status`  varchar(2000);
ALTER TABLE `cireports_isobuild` MODIFY COLUMN  `current_status`  varchar(2000);

-- END 3.15.93

-- END 3.15.94

-- END 3.15.95

ALTER TABLE cireports_isobuild ADD COLUMN `active` boolean NOT NULL default 1;

-- END 3.15.96

-- END 3.15.97

-- END 3.15.98

-- END 3.15.99

-- END 3.15.100

-- END 3.15.101

-- END 3.15.102

-- END 3.15.103

-- END 3.15.104

-- END 3.15.105

-- END 3.15.106

-- END 3.15.107

-- END 3.15.108
ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_if VARCHAR(100) NULL AFTER evt_storage_id;

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_internal_2_id int UNSIGNED NULL AFTER str_internal_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrinternal_2_2_ip` FOREIGN KEY (`str_str_internal_2_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_internal_3_id int UNSIGNED NULL AFTER str_str_internal_2_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrinternal_3_2_ip` FOREIGN KEY (`str_str_internal_3_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_external_2_id int UNSIGNED NULL AFTER str_external_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrexternal_2_2_ip` FOREIGN KEY (`str_str_external_2_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_external_3_id int UNSIGNED NULL AFTER str_str_external_2_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrexternal_3_2_ip` FOREIGN KEY (`str_str_external_3_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_internal_ipv6_2_id int UNSIGNED NULL AFTER str_str_internal_ipv6_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrintipv6_2_2_ipv6` FOREIGN KEY (`str_str_internal_ipv6_2_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_internal_ipv6_3_id int UNSIGNED NULL AFTER str_str_internal_ipv6_2_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrintipv6_3_2_ipv6` FOREIGN KEY (`str_str_internal_ipv6_3_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_external_ipv6_2_id int UNSIGNED NULL AFTER str_external_ipv6_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrexternalipv6_2_2_ipv6` FOREIGN KEY (`str_str_external_ipv6_2_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN str_str_external_ipv6_3_id int UNSIGNED NULL AFTER str_str_external_ipv6_2_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `strstrexternalipv6_3_2_ipv6` FOREIGN KEY (`str_str_external_ipv6_3_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN esn_str_if VARCHAR(100) NULL AFTER str_storage_id;

ALTER TABLE dmt_lvsroutervip ADD COLUMN esn_str_internal_id int UNSIGNED NULL AFTER esn_str_if;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `esnstrinternal_2_ip` FOREIGN KEY (`esn_str_internal_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN esn_str_external_id int UNSIGNED NULL AFTER esn_str_internal_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `esnstrexternal_2_ip` FOREIGN KEY (`esn_str_external_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN esn_str_internal_ipv6_id int UNSIGNED NULL AFTER esn_str_external_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `esnstrintipv6_2_ipv6` FOREIGN KEY (`esn_str_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN esn_str_external_ipv6_id int UNSIGNED NULL AFTER esn_str_internal_ipv6_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `esnstrexternalipv6_2_ipv6` FOREIGN KEY (`esn_str_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN esn_storage_internal_id int UNSIGNED NULL AFTER esn_str_external_ipv6_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `esnstgint_2_ip` FOREIGN KEY (`esn_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervip ADD COLUMN esn_str_storage_id int UNSIGNED NULL AFTER esn_storage_internal_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `esnstrstg_2_ip` FOREIGN KEY (`esn_str_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.15.109

-- END 3.15.110

-- END 3.15.111
ALTER TABLE dmt_autovmservicednsiprange MODIFY Id integer UNSIGNED AUTO_INCREMENT NOT NULL;

-- END 3.15.112

-- END 3.15.113

-- END 3.15.114

-- END 3.15.115

-- END 3.15.116

-- END 3.15.117
CREATE TABLE `dmt_deploymentutilstoproductsetversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `utility_version_id` integer UNSIGNED NOT NULL,
    `productSetVersion_id` integer UNSIGNED NOT NULL,
    `active` bool NOT NULL,
    CONSTRAINT `utilityversion_2_deploymentutils` FOREIGN KEY (`utility_version_id`) REFERENCES `dmt_deploymentutilitiesversion` (`id`),
    CONSTRAINT `productSetVersion_2_deploymentutils` FOREIGN KEY (`productSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`)
) ENGINE=InnoDB;

-- END 3.15.118

-- END 3.15.119

-- END 3.15.120

-- END 3.15.121

-- END 3.15.122

-- END 3.15.123

-- END 3.15.124

-- END 3.15.125

-- END 3.15.126

-- END 3.15.127

-- END 3.15.128

-- END 3.15.129

-- END 3.15.130

-- END 3.15.131

-- END 3.15.132

-- END 3.15.133

-- END 3.15.134

-- END 3.15.135

-- END 3.15.136

-- END 3.15.137

-- END 3.15.138

-- END 3.15.139

-- END 3.15.140

-- END 3.15.141

-- END 3.15.142

-- END 3.15.143

-- END 3.15.144

-- END 3.15.145

-- END 3.15.146

-- END 3.15.147

-- END 3.15.148

-- END 3.15.149

-- END 3.15.150

-- END 3.15.151

-- END 3.15.152

-- END 3.15.153

-- END 3.15.154

-- END 3.15.155

-- END 3.15.156

-- END 3.15.157

-- END 3.15.158

-- END 3.15.159

-- END 3.15.160

-- END 3.15.161

-- END 3.15.162
ALTER TABLE dmt_lvsroutervip ADD COLUMN ebs_storage_internal_id int UNSIGNED NULL AFTER esn_str_storage_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `ebsstgint_2_ip` FOREIGN KEY (`ebs_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN ebs_storage_id int UNSIGNED NULL AFTER ebs_storage_internal_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `ebsstg_2_ip` FOREIGN KEY (`ebs_storage_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN asr_storage_id int UNSIGNED NULL AFTER ebs_storage_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `asrstg_2_ip` FOREIGN KEY (`asr_storage_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN asr_asr_storage_id int UNSIGNED NULL AFTER asr_storage_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `asrasrstg_2_ip` FOREIGN KEY (`asr_asr_storage_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN asr_asr_external_ipv6_id int UNSIGNED NULL AFTER asr_asr_storage_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `asrasrexternalipv6_2_ipv6` FOREIGN KEY (`asr_asr_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN asr_asr_internal_id int UNSIGNED NULL AFTER asr_asr_external_ipv6_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `asrasrinternal_2_ip` FOREIGN KEY (`asr_asr_internal_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN asr_asr_external_id int UNSIGNED NULL AFTER asr_asr_internal_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `asrasrexternal_2_ip` FOREIGN KEY (`asr_asr_external_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN asr_storage_internal_id int UNSIGNED NULL AFTER asr_asr_external_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `asrstgint_2_ip` FOREIGN KEY (`asr_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.15.163

-- END 3.15.164

-- END 3.15.165

-- END 3.15.166

-- END 3.15.167

-- END 3.15.168

-- END 3.15.169

-- END 3.15.170

-- END 3.15.171

-- END 3.15.172

-- END 3.15.173

-- END 3.15.174

-- END 3.15.175

-- END 3.16.1

-- END 3.16.2

-- END 3.16.3

-- END 3.16.4

-- END 3.16.5

-- END 3.16.6

-- END 3.16.7

-- END 3.16.8
ALTER TABLE dmt_virtualimage ADD UNIQUE INDEX virtualimageCluster (name, cluster_id);

-- END 3.16.9


-- END 3.16.10

-- END 3.16.11

-- END 3.16.12

-- END 3.16.13

-- END 3.16.14

-- END 3.16.15

-- END 3.16.16

-- END 3.16.17


-- END 3.16.18

-- END 3.16.19

-- END 3.16.20

-- END 3.16.21


-- END 3.16.22

-- END 3.16.23


-- END 3.16.24


-- END 3.16.25

-- END 3.16.26


-- END 3.16.27

-- END 3.16.28

-- END 3.16.29

-- END 3.16.30

-- END 3.16.31


-- END 3.16.32

-- END 3.16.33



-- END 3.16.34

-- END 3.16.35

-- END 3.16.36

-- END 3.16.37


-- END 3.16.38

-- END 3.16.39


-- END 3.16.40

-- END 3.16.41

-- END 3.16.42

-- END 3.16.43

-- END 3.16.44

-- END 3.16.45

-- END 3.16.46

-- END 3.16.47

-- END 3.16.48

-- END 3.16.49

-- END 3.16.50

-- END 3.16.51

-- END 3.16.52

-- END 3.16.53

-- END 3.16.54

-- END 3.16.55
ALTER TABLE `foss_gerritrepo` ADD COLUMN `repo_revision` VARCHAR(40) NULL after `repo_name`;
ALTER TABLE `foss_gerritrepo` ADD COLUMN `owner_email` varchar(100) NOT NULL;
ALTER TABLE `foss_gerritrepo` ADD COLUMN `scan` BOOL NOT NULL DEFAULT "1";
ALTER TABLE `foss_scanversion` ADD COLUMN `end_time` datetime NULL after start_time;
ALTER TABLE `foss_scanversion` ADD COLUMN `audit_report_url` VARCHAR(200) NULL;

DROP TABLE `foss_scanmapping`;
CREATE TABLE `foss_scanmapping` (
    `id` INTEGER UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `scan_version_id` INTEGER  UNSIGNED NOT NULL,
    `gerrit_repo_id` SMALLINT UNSIGNED NOT NULL,
    `audit_id` VARCHAR(30) NULL,
    `project_id` VARCHAR(10) NULL,
    `report_url` VARCHAR(200) NULL,
    `start_time` datetime NULL,
    `end_time` datetime NULL,
    `status` VARCHAR(50) NOT NULL,
    `reason` VARCHAR(150) NULL,
    CONSTRAINT `scanmapping_2_scanversion` FOREIGN KEY (`scan_version_id`) REFERENCES `foss_scanversion` (`id`),
    CONSTRAINT `scanmapping_2_gerritrepo` FOREIGN KEY (`gerrit_repo_id`) REFERENCES `foss_gerritrepo` (`id`)
) ENGINE = InnoDB;

-- END 3.16.56

-- END 3.16.57

-- END 3.16.58

-- END 3.16.59

-- END 3.16.60

-- END 3.16.61

-- END 3.16.62

-- END 3.16.63

-- END 3.16.64


-- END 3.16.65

-- END 3.16.66

-- END 3.16.67

-- END 3.16.68

-- END 3.16.69


-- END 3.16.70

-- END 3.16.71

-- END 3.16.72

-- END 3.16.73

-- END 3.16.74


-- END 3.16.75

ALTER TABLE dmt_databasevips ADD COLUMN `neo4j_address1_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `neo4j_1_ip` FOREIGN KEY (`neo4j_address1_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_databasevips ADD COLUMN `neo4j_address2_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `neo4j_2_ip` FOREIGN KEY (`neo4j_address2_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_databasevips ADD COLUMN `neo4j_address3_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `neo5j_3_ip` FOREIGN KEY (`neo4j_address3_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.16.76

-- END 3.16.77

-- END 3.16.78

-- END 3.16.79

-- END 3.16.80

-- END 3.16.81

-- END 3.16.82

-- END 3.16.83

-- END 3.16.84

-- END 3.16.85

-- END 3.16.86

-- END 3.16.87

-- END 3.16.88

-- END 3.16.89

-- END 3.16.90

-- END 3.16.91

-- END 3.16.92

-- END 3.16.93

-- END 3.16.94

-- END 3.16.95

-- END 3.16.96
CREATE TABLE `cireports_mediaartifactcategory` (
      `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
      `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;
INSERT INTO cireports_mediaartifactcategory(name) VALUES("productware");
INSERT INTO cireports_mediaartifactcategory(name) VALUES("testware");

ALTER TABLE cireports_mediaartifact ADD COLUMN `category_id` smallint UNSIGNED NOT NULL DEFAULT 1;
ALTER TABLE cireports_mediaartifact ADD CONSTRAINT `mediaartfact_2_category` FOREIGN KEY (`category_id`) REFERENCES `cireports_mediaartifactcategory` (`id`);


-- END 3.16.97

-- END 3.16.98

-- END 3.16.99

-- END 3.16.100

-- END 3.16.101

-- END 3.16.102


-- END 3.16.103

-- END 3.16.104

-- END 3.16.105

-- END 3.16.106

-- END 3.16.107

-- END 3.16.108

-- END 3.16.109

-- END 3.16.110

-- END 3.16.111

-- END 3.16.112

-- END 3.16.113

-- END 3.16.114

-- END 3.16.115

-- END 3.16.116

-- END 3.16.117

-- END 3.16.118

-- END 3.16.119

-- END 3.16.120

-- END 3.16.121

-- END 3.16.122

-- END 3.16.123

-- END 3.16.124

-- END 3.16.125

-- END 3.16.126
CREATE TABLE `dmt_packagerevisionservicemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `service_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `packagerevisionservicemapping_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `packagerevisionservicemapping_2_vmservicename` FOREIGN KEY (`service_id`) REFERENCES `dmt_vmservicename` (`id`)
) ENGINE = InnoDB;
CREATE TABLE `dmt_mediaartifactservicescanned` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `media_artifact_version` varchar(15) NOT NULL UNIQUE,
    `scanned_date` datetime
) ENGINE = InnoDB;
ALTER TABLE cireports_deliverytopackagerevmapping ADD COLUMN `services` varchar(500) NOT NULL DEFAULT "No Services Data";

-- END 3.16.127

-- END 3.16.128

-- END 3.16.129

-- END 3.16.130

-- END 3.16.131

-- END 3.16.132

-- END 3.16.133

-- END 3.16.134

-- END 3.16.135

-- END 3.16.136

-- END 3.16.137

-- END 3.16.138

-- END 3.16.139

-- END 3.16.140

-- END 3.16.141

-- END 3.16.142

-- END 3.16.143

-- END 3.16.144

-- END 3.16.145

-- END 3.16.146

-- END 3.16.147

-- END 3.16.148


-- END 3.16.149

-- END 3.16.150

-- END 3.16.151

-- END 3.16.152

-- END 3.16.153


-- END 3.16.154

-- END 3.16.155

-- END 3.16.156

-- END 3.16.157

-- END 3.16.158


-- END 3.16.159

-- END 3.16.160

-- END 3.16.161

-- END 3.16.162

-- END 3.16.163

-- END 3.16.164

-- END 3.16.165

-- END 3.16.166

-- END 3.16.167

-- END 3.16.168

-- END 3.16.169

-- END 3.16.170

-- END 3.16.171

-- END 3.16.172

-- END 3.16.173

-- END 3.16.174

-- END 3.16.175

-- END 3.16.176

-- END 3.16.177

-- END 3.16.178

-- END 3.16.179

-- END 3.16.180

-- END 3.16.181

-- END 3.16.182

-- END 3.16.183

-- END 3.16.184

-- END 3.16.185

-- END 3.16.186

-- END 3.16.187

-- END 3.16.188

-- END 3.16.189

-- END 3.16.190

-- END 3.16.191

-- END 3.16.192

-- END 3.16.193

-- END 3.16.194

-- END 3.16.195

-- END 3.16.196

-- END 3.16.197

-- END 3.16.198

-- END 3.16.199

-- END 3.16.200

-- END 3.16.201
ALTER TABLE cireports_isobuild ADD COLUMN `externally_released` boolean NOT NULL default 0;
ALTER TABLE cireports_isobuild ADD COLUMN `externally_released_ip` boolean NOT NULL default 0;
ALTER TABLE cireports_isobuild ADD COLUMN `externally_released_rstate` varchar(15);

-- END 3.16.202

-- END 3.16.203

-- END 3.16.204

-- END 3.16.205

-- END 3.16.206

-- END 3.16.207

-- END 3.16.208

-- END 3.16.209

-- END 3.16.210

-- END 3.16.211

-- END 3.16.212

-- END 3.16.213

-- END 3.16.214

-- END 3.16.215

-- END 3.16.216

-- END 3.16.217

-- END 3.16.218

-- END 3.16.219

-- END 3.16.220

-- END 3.16.221

-- END 3.16.222

-- END 3.16.223

-- END 3.16.224

-- END 3.16.225

-- END 3.16.226

-- END 3.16.227

-- END 3.16.228

-- END 3.16.229


-- END 3.16.230

-- END 3.16.231

-- END 3.16.232

-- END 3.16.233

-- END 3.16.234

-- END 3.16.235

-- END 3.16.236

-- END 3.16.237

-- END 3.16.238

-- END 3.16.239

-- END 3.16.240

-- END 3.16.241

-- END 3.16.242

-- END 3.16.243
CREATE TABLE `cireports_testwaretype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `type` varchar(15) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_testwaretypemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testware_artifact_id` smallint UNSIGNED NOT NULL,
    `testware_type_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `testwaretypemapping_2_package` FOREIGN KEY (`testware_artifact_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `testwaretypemapping_2_testwaretype` FOREIGN KEY (`testware_type_id`) REFERENCES `cireports_testwaretype` (`id`),
    UNIQUE INDEX testwareArtifacTypeMap (testware_artifact_id, testware_type_id)
) ENGINE=InnoDB
;

INSERT INTO cireports_testwaretype(type) VALUES("RFA250");
INSERT INTO cireports_testwaretype(type) VALUES("RNL");
INSERT INTO cireports_testwaretype(type) VALUES("AGAT");

ALTER TABLE `cireports_package` ADD COLUMN `includedInPriorityTestSuite` bool NOT NULL DEFAULT 0;

-- END 3.16.244

-- END 3.16.245

-- END 3.16.246

-- END 3.16.247

-- END 3.16.248

-- END 3.16.249

-- END 3.16.250

-- END 3.16.251

-- END 3.16.252

-- END 3.16.253

-- END 3.16.254

-- END 3.16.255

-- END 3.16.256

-- END 3.16.257

-- END 3.16.258

-- END 3.16.259

-- END 3.16.260

-- END 3.16.261

-- END 3.16.262

-- END 3.16.263

-- END 3.16.264

-- END 3.16.265

-- END 3.16.266

-- END 3.16.267

-- END 3.16.268

-- END 3.16.269

-- END 3.16.270

-- END 3.16.271

-- END 3.16.272

-- END 3.16.273

-- END 3.16.274

-- END 3.16.275

-- END 3.16.276

-- END 3.17.1

-- END 3.17.2

-- END 3.17.3

-- END 3.17.4

-- END 3.17.5

-- END 3.17.6

-- END 3.17.7

-- END 3.17.8

-- END 3.17.9

-- END 3.17.10

-- END 3.17.11

-- END 3.17.12

-- END 3.17.13

-- END 3.17.14

-- END 3.17.15
CREATE TABLE `dmt_deploymentdatabaseprovider` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL UNIQUE,
    `dpsPersistenceProvider` varchar(50) NOT NULL default "versant",
    UNIQUE INDEX providertoclustermap (cluster_id, dpsPersistenceProvider),
    CONSTRAINT `cluster_2_databaseprovider` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

-- END 3.18.1

-- END 3.18.2

-- END 3.18.3


-- END 3.18.4

-- END 3.18.5

-- END 3.18.6

-- END 3.18.7

-- END 3.18.8

-- END 3.18.9

-- END 3.18.10

-- END 3.18.11

-- END 3.18.12

-- END 3.18.13

-- END 3.18.14

-- END 3.18.15
CREATE TABLE `cireports_dropmediadeploymapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dropMediaArtifactMap_id` integer UNSIGNED NOT NULL,
    `product_id` integer UNSIGNED NOT NULL,
    UNIQUE INDEX mediatoproductmap (dropMediaArtifactMap_id,product_id),
    CONSTRAINT `dropmediaartifactmap_2_drop` FOREIGN KEY (`dropMediaArtifactMap_id`) REFERENCES `cireports_dropmediaartifactmapping` (`id`),
    CONSTRAINT `dropmediaartifactmap_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_productsetversiondeploymapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mainMediaArtifactVersion_id` smallint UNSIGNED NOT NULL,
    `mediaArtifactVersion_id` smallint UNSIGNED NOT NULL,
    `productSetVersion_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `main_deploymap_2_isobuild` FOREIGN KEY (`mainMediaArtifactVersion_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `deploymap_2_isobuild` FOREIGN KEY (`mediaArtifactVersion_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `deploymap_2_productsetver` FOREIGN KEY (`productSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_mediaartifactdeploytype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `type` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;

INSERT INTO cireports_mediaartifactdeploytype(type) VALUES("not_required");
INSERT INTO cireports_mediaartifactdeploytype(type) VALUES("it_platform");
INSERT INTO cireports_mediaartifactdeploytype(type) VALUES("os");
INSERT INTO cireports_mediaartifactdeploytype(type) VALUES("patches");


ALTER TABLE cireports_mediaartifact ADD COLUMN `deployType_id` smallint UNSIGNED NOT NULL DEFAULT 1;
ALTER TABLE cireports_mediaartifact ADD CONSTRAINT `mediaartfact_2_deploytype` FOREIGN KEY (`deployType_id`) REFERENCES `cireports_mediaartifactdeploytype` (`id`);


-- END 3.18.16

-- END 3.18.17

-- END 3.18.18

-- END 3.18.19

-- END 3.18.20

-- END 3.18.21

-- END 3.18.22

-- END 3.18.23

-- END 3.18.24

-- END 3.18.25

-- END 3.18.26

-- END 3.18.27

-- END 3.19.1

-- END 3.19.2


-- END 3.19.3

-- END 3.19.4

-- END 3.19.5

-- END 3.19.6

-- END 3.19.7

-- END 3.19.8

-- END 3.19.9

-- END 3.19.10

-- END 3.19.11

-- END 3.19.12

-- END 3.19.13

-- END 3.19.14

-- END 3.19.15

-- END 3.19.16

-- END 3.19.17

-- END 3.19.18

-- END 3.19.19

-- END 3.19.20

-- END 3.19.21

-- END 3.19.22

-- END 3.19.23

-- END 3.19.24

-- END 3.19.25

-- END 3.19.26

-- END 3.19.27

-- END 3.19.28

-- END 3.19.29

-- END 3.19.30

-- END 3.20.1

-- END 3.20.2

-- END 3.20.3

-- END 3.20.4

-- END 3.20.5

-- END 3.20.6

-- END 3.20.7

-- END 3.20.8

-- END 3.20.9

-- END 3.20.10

-- END 3.20.11

ALTER TABLE `cireports_drop` ADD `stop_auto_delivery` bool DEFAULT false NULL;

-- END 3.20.12

-- END 3.20.13

-- END 3.20.14

-- END 3.20.15

-- END 3.20.16

-- END 3.20.17

-- END 3.20.18

-- END 3.20.19

-- END 3.20.20

-- END 3.20.21

-- END 3.20.22

-- END 3.20.23

-- END 3.21.1

-- END 3.21.2

-- END 3.21.3

-- END 3.21.4

-- END 3.21.5

-- END 3.21.6

-- END 3.21.7

-- END 3.21.8

-- END 3.21.9

-- END 3.21.10

-- END 3.21.11

-- END 3.21.12

-- END 3.21.13

-- END 3.21.14

-- END 3.21.15

-- END 3.21.16

-- END 3.21.17

-- END 3.21.18

-- END 3.21.19

-- END 3.21.20

-- END 3.21.21

-- END 3.21.22

-- END 3.21.23

-- END 3.21.24

-- END 3.21.25

-- END 3.21.26

-- END 3.21.27

-- END 3.21.28

-- END 3.21.29

-- END 3.21.30

-- END 3.21.31

-- END 3.21.32

-- END 3.21.33

-- END 3.21.34

-- END 3.21.35

-- END 3.21.36

-- END 3.21.37

-- END 3.21.38

-- END 3.21.39

-- END 3.21.40

-- END 3.21.41

-- END 3.21.42
ALTER TABLE dmt_lvsroutervip ADD COLUMN eba_storage_internal_id int UNSIGNED NULL AFTER asr_storage_internal_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `ebastgint_2_ip` FOREIGN KEY (`eba_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_lvsroutervip ADD COLUMN eba_storage_id int UNSIGNED NULL AFTER eba_storage_internal_id;
ALTER TABLE dmt_lvsroutervip ADD CONSTRAINT `ebastg_2_ip` FOREIGN KEY (`eba_storage_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.21.43

-- END 3.21.44

-- END 3.21.45

-- END 3.21.46

-- END 3.21.47

-- END 3.21.48

-- END 3.21.49

-- END 3.21.50

-- END 3.21.51

-- END 3.21.52

-- END 3.21.53

-- END 3.21.54

-- END 3.21.55

-- END 3.21.56

-- END 3.21.57

-- END 3.21.58

-- END 3.21.59

-- END 3.21.60

-- END 3.21.61

-- END 3.21.62

-- END 3.21.63

-- END 3.21.64

-- END 3.21.65
ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `msossfm_external_id` int UNSIGNED NULL AFTER `eba_storage_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `msossfmexternal_2_ip` FOREIGN KEY (`msossfm_external_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `msossfm_external_ipv6_id` int UNSIGNED NULL AFTER `msossfm_external_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `msossfmexternalipv6_2_ipv6` FOREIGN KEY (`msossfm_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `msossfm_internal_id` int UNSIGNED NULL AFTER `msossfm_external_ipv6_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `msossfminternal_2_ip` FOREIGN KEY (`msossfm_internal_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `msossfm_internal_ipv6_id` int UNSIGNED NULL AFTER `msossfm_internal_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `msossfminternalipv6_2_ipv6` FOREIGN KEY (`msossfm_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.21.66

-- END 3.21.67

-- END 3.21.68

-- END 3.21.69

-- END 3.21.70

-- END 3.21.71

-- END 3.21.72

-- END 3.21.73

-- END 3.21.74

-- END 3.21.75

-- END 3.21.76

-- END 3.21.77

-- END 3.21.78

-- END 3.21.79

-- END 3.21.80

-- END 3.21.81

-- END 3.21.82

-- END 3.21.83

-- END 3.21.84

-- END 3.21.85

-- END 3.21.86

-- END 3.21.87

-- END 3.21.88

-- END 3.21.89

-- END 3.21.90

-- END 3.21.91

-- END 3.21.92

-- END 3.21.93

-- END 3.21.94

-- END 3.21.95

-- END 3.21.96

-- END 3.21.97

-- END 3.21.98

ALTER TABLE cireports_jiradeliverygroupmap CHANGE `id` `id` integer UNSIGNED AUTO_INCREMENT NOT NULL;

-- END 3.21.99

-- END 3.21.100

-- END 3.21.101

-- END 3.21.102

-- END 3.21.103

-- END 3.21.104

-- END 3.21.105

-- END 3.21.106

-- END 3.21.107

-- END 3.21.108

-- END 3.21.109

-- END 3.21.110

-- END 3.21.111

-- END 3.21.112

-- END 3.21.113

-- END 3.21.114

-- END 3.21.115

-- END 3.21.116

-- END 3.21.117

-- END 3.21.118

-- END 3.21.119

-- END 3.21.120

-- END 3.21.121

-- END 3.21.122

-- END 3.21.123

-- END 3.21.124

-- END 3.21.125

-- END 3.21.126

-- END 3.21.127

CREATE TABLE `dmt_clusteradditionalinformation` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `ddp_hostname` varchar(50) NULL,
    `cron` varchar(50) NULL,
    `port` varchar(4) NULL,
    CONSTRAINT `ddpinformation_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

-- END 3.21.128

-- END 3.21.129

-- END 3.21.130

-- END 3.21.131

-- END 3.21.132

-- END 3.21.133

CREATE TABLE `dmt_lvsroutervipextended` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `eba_external_id` integer UNSIGNED NULL,
    `eba_external_ipv6_id` integer UNSIGNED NULL,
    `eba_internal_id` integer UNSIGNED NULL,
    `eba_internal_ipv6_id` integer UNSIGNED NULL,

    CONSTRAINT `lvsroutervipextended_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `ebaexternal_2_ip` FOREIGN KEY (`eba_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebaexternalipv6_2_ip` FOREIGN KEY (`eba_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebainternal_2_ip` FOREIGN KEY (`eba_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebainternalipv6_2_ip` FOREIGN KEY (`eba_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`)

) ENGINE=InnoDB;
-- END 3.21.134

-- END 3.21.135

-- END 3.21.136

-- END 3.21.137

-- END 3.21.138

-- END 3.21.139

-- END 3.21.140

-- END 3.21.141

-- END 3.21.142

-- END 3.21.143

-- END 3.21.144

-- END 3.21.145

-- END 3.21.146

-- END 3.21.147

-- END 3.21.148

-- END 3.21.149

-- END 3.21.150

-- END 3.21.151

-- END 3.21.152

-- END 3.21.153

-- END 3.21.154

-- END 3.21.155

-- END 3.21.156

-- END 3.21.157

-- END 3.21.158

-- END 3.21.159

-- END 3.21.160

-- END 3.21.161

-- END 3.21.162

-- END 3.21.163

-- END 3.21.164

-- END 3.21.165

-- END 3.21.166

-- END 3.21.167

-- END 3.21.168

-- END 3.21.169

-- END 3.21.170

-- END 3.21.171

-- END 3.21.172

-- END 3.21.173

-- END 3.21.174

-- END 3.21.175

-- END 3.21.176

-- END 3.21.177

-- END 3.21.178

-- END 3.21.179

-- END 3.21.180

-- END 3.21.181

-- END 3.21.182

-- END 3.21.183

-- END 3.21.184

-- END 3.21.185

-- END 3.21.186

-- END 3.21.187

-- END 3.21.188

-- END 3.21.189

-- END 3.21.190

-- END 3.21.191

-- END 3.21.192

-- END 3.21.193

-- END 3.21.194

-- END 3.21.195

-- END 3.21.196

-- END 3.21.197

-- END 3.21.198

-- END 3.21.199

-- END 3.21.200

-- END 3.21.201

-- END 3.21.202

-- END 3.21.203

-- END 3.21.204

-- END 3.21.205

-- END 3.21.206

-- END 3.21.207

-- END 3.21.208

-- END 3.21.209

-- END 3.21.210

-- END 3.21.211

-- END 3.21.212

-- END 3.21.213

-- END 3.21.214

-- END 3.21.215

-- END 3.21.216

-- END 3.21.217

-- END 3.21.218

-- END 3.21.219

-- END 3.21.220

-- END 3.21.221

-- END 3.21.222

-- END 3.21.223

-- END 3.21.224

-- END 3.21.225

-- END 3.21.226

-- END 3.21.227

-- END 3.21.228

-- END 3.21.229

-- END 3.21.230

-- END 3.21.231

-- END 3.21.232

-- END 3.21.233

-- END 3.21.234

-- END 3.21.235

-- END 3.21.236

-- END 3.21.237

-- END 3.21.238

-- END 3.21.239

-- END 3.21.240

-- END 3.21.241

-- END 3.21.242

-- END 3.21.243

-- END 3.21.244

-- END 3.21.245

-- END 3.21.246

-- END 3.21.247

-- END 3.21.248

-- END 3.21.249

-- END 3.21.250

-- END 3.21.251

-- END 3.21.252

-- END 3.21.253


-- END 3.21.254

-- END 3.21.255

-- END 3.21.256

-- END 3.21.257

-- END 3.21.258

-- END 3.21.259

-- END 3.21.260

-- END 3.21.261

-- END 3.21.262

-- END 3.21.263

-- END 3.21.264

-- END 3.21.265

-- END 3.21.266

-- END 3.21.267

-- END 3.21.268

-- END 3.21.269

-- END 3.21.270

-- END 3.21.271

-- END 3.21.272

-- END 3.21.273

-- END 3.21.274

-- END 3.21.275

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `ebs_str_external_ipv6_id` int UNSIGNED NULL AFTER `ebs_storage_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `ebsstrexternalipv6_2_ipv6` FOREIGN KEY (`ebs_str_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.21.276

-- END 3.21.277

-- END 3.21.278

-- END 3.21.279

-- END 3.21.280

-- END 3.21.281

-- END 3.21.282

-- END 3.21.283

-- END 3.21.284

-- END 3.21.285

-- END 3.21.286

-- END 3.21.287

-- END 3.21.288

-- END 3.21.289

-- END 3.21.290

-- END 3.21.291

-- END 3.21.292

-- END 3.21.293

-- END 3.21.294

-- END 3.21.295

-- END 3.21.296

-- END 3.21.297

-- END 3.21.298

-- END 3.21.299

-- END 3.21.300

-- END 3.21.301

-- END 3.21.302

-- END 3.21.303

-- END 3.21.304

-- END 3.21.305

-- END 3.21.306

-- END 3.21.307

-- END 3.21.308

-- END 3.21.309

-- END 3.21.310

-- END 3.21.311

-- END 3.21.312

-- END 3.21.313

-- END 3.21.314

-- END 3.21.315

-- END 3.21.316

-- END 3.21.317

-- END 3.21.318

-- END 3.21.319

-- END 3.21.320

-- END 3.21.321

-- END 3.21.322

ALTER TABLE dmt_lvsroutervipextended ADD COLUMN `lms_ipv6_id` int UNSIGNED NULL AFTER `eba_internal_ipv6_id`;
ALTER TABLE dmt_lvsroutervipextended ADD CONSTRAINT `lmsipv6_2_ipv6` FOREIGN KEY (`lms_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervipextended ADD COLUMN `svc_pm_ipv6_id` int UNSIGNED NULL AFTER `lms_ipv6_id`;
ALTER TABLE dmt_lvsroutervipextended ADD CONSTRAINT `svcpmipv6_2_ipv6` FOREIGN KEY (`svc_pm_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.21.323

-- END 3.21.324

-- END 3.21.325

-- END 3.21.326

-- END 3.21.327

-- END 3.21.328

-- END 3.21.329

-- END 3.21.330

-- END 3.21.331

-- END 3.21.332

-- END 3.21.333

-- END 3.21.334

-- END 3.21.335

-- END 3.21.336

-- END 3.21.337

-- END 3.21.338

-- END 3.21.339

-- END 3.21.340

-- END 3.21.341

-- END 3.21.342

-- END 3.21.343

-- END 3.21.344

-- END 3.21.345

-- END 3.21.346

-- END 3.21.347

-- END 3.21.348

-- END 3.21.349

-- END 3.21.350

-- END 3.21.351

-- END 3.21.352

-- END 3.21.353

-- END 3.21.354

-- END 3.21.355

-- END 3.21.356

-- END 3.21.357

-- END 3.21.358

-- END 3.21.359

-- END 3.21.360

-- END 3.21.361

-- END 3.21.362

-- END 3.21.363

-- END 3.21.364

-- END 3.21.365

-- END 3.21.366

-- END 3.21.367

-- END 3.21.368

-- END 3.21.369

-- END 3.21.370

-- END 3.21.371

-- END 3.21.372

-- END 3.21.373

-- END 3.21.374

-- END 3.21.375

ALTER TABLE dmt_clusteradditionalinformation ADD COLUMN `time` varchar(255) NULL AFTER port;

-- END 3.21.376

-- END 3.21.377

-- END 3.21.378

-- END 3.21.379

-- END 3.21.380

-- END 3.21.381

-- END 3.21.382

-- END 3.21.383

-- END 3.21.384

-- END 3.21.385

-- END 3.21.386

-- END 3.21.387

-- END 3.21.388

-- END 3.21.389

-- END 3.21.390

-- END 3.21.391

-- END 3.21.392

-- END 3.21.393

-- END 3.21.394

-- END 3.21.395

-- END 3.21.396

-- END 3.21.397

-- END 3.21.398

-- END 3.21.399

-- END 3.21.400

-- END 3.21.401

-- END 3.21.402

-- END 3.21.403

-- END 3.21.404

-- END 3.21.405

-- END 3.21.406

-- END 3.21.407

-- END 3.21.408

-- END 3.21.409

-- END 3.21.410

-- END 3.21.411

-- END 3.21.412

-- END 3.21.413

-- END 3.21.414

-- END 3.21.415

-- END 3.21.416

-- END 3.21.417

-- END 3.21.418

-- END 3.21.419

-- END 3.21.420

-- END 3.21.421

-- END 3.21.422

-- END 3.21.423

-- END 3.21.424

-- END 3.21.425

-- END 3.21.426

-- END 3.21.427

-- END 3.21.428

-- END 3.21.429

-- END 3.21.430

-- END 3.21.431

-- END 3.21.432

-- END 3.21.433

-- END 3.21.434

-- END 3.21.435

-- END 3.21.436

-- END 3.21.437

-- END 3.21.438

-- END 3.21.439

-- END 3.21.440

-- END 3.21.441

-- END 3.21.442

-- END 3.21.443

-- END 3.21.444

-- END 3.21.445

-- END 3.21.446

-- END 3.21.447

-- END 3.21.448

-- END 3.21.449

-- END 3.21.450

-- END 3.21.451

-- END 3.21.452

-- END 3.21.453

-- END 3.21.454

-- END 3.21.455

-- END 3.21.456

-- END 3.21.457

-- END 3.21.458

-- END 3.21.459

-- END 3.21.460

-- END 3.21.461

-- END 3.21.462

-- END 3.21.463

-- END 3.21.464

-- END 3.21.465

-- END 3.21.466

-- END 3.21.467

-- END 3.21.468

-- END 3.21.469

-- END 3.21.470

-- END 3.21.471

-- END 3.21.472

-- END 3.21.473

-- END 3.21.474

-- END 3.21.475

-- END 3.21.476

-- END 3.21.477

-- END 3.21.478

-- END 3.21.479

-- END 3.21.480

-- END 3.21.481

-- END 3.21.482

-- END 3.21.483

ALTER TABLE depmodel_staticdependency ENGINE=InnoDB;
ALTER TABLE depmodel_javapackage ENGINE=InnoDB;
ALTER TABLE depmodel_dependencytype  ENGINE=InnoDB;
ALTER TABLE depmodel_dependency ENGINE=InnoDB;

-- END 3.21.484

-- END 3.21.485

-- END 3.21.486

-- END 3.21.487

-- END 3.21.488

-- END 3.21.489

-- END 3.21.490

-- END 3.21.491
CREATE TABLE `cireports_cnintegrationchart` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `integration_chart_name` varchar(100) NOT NULL,
    CONSTRAINT `product_2_cnintegrationchart` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnhelmchart` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `helm_chart_name` varchar(100) NOT NULL UNIQUE,
    `helm_chart_product_number` varchar(20) NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnimage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_name` varchar(100) NOT NULL UNIQUE,
    `image_product_number` varchar(20) NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnimagerevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_id` integer UNSIGNED NOT NULL,
    `parent_id` integer UNSIGNED NULL,
    `version` varchar(20) NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` INTEGER UNSIGNED NULL,
    `gerrit_repo_sha` varchar(100) NULL,
    `build_for` varchar(30),
    CONSTRAINT `cnimage_2_cnimagerevision` FOREIGN KEY (`image_id`) REFERENCES `cireports_cnimage` (`id`),
    CONSTRAINT `cnimagerevision_2_cnimagerevision` FOREIGN KEY (`parent_id`) REFERENCES `cireports_cnimagerevision` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnhelmchartrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `helm_chart_id` integer UNSIGNED NOT NULL,
    `version` varchar(20) NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` INTEGER UNSIGNED NULL,
    `gerrit_repo_sha` varchar(100) NULL,
    `build_for` varchar(30),
    CONSTRAINT `cnhelmchart_2_cnhelmchartrevision` FOREIGN KEY (`helm_chart_id`) REFERENCES `cireports_cnhelmchart` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnintegrationchartrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `integration_chart_id` integer UNSIGNED NOT NULL,
    `version` varchar(20) NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` INTEGER UNSIGNED NULL,
    `gerrit_repo_sha` varchar(100) NULL,
    `build_for` varchar(30),
    CONSTRAINT `cnintegrationchart_2_cnintegrationchartrevision` FOREIGN KEY (`integration_chart_id`) REFERENCES `cireports_cnintegrationchart` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnimagecontent` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_revision_id` integer UNSIGNED NOT NULL,
    `package_id` smallint UNSIGNED NOT NULL,
    `version` varchar(20) NULL,
    CONSTRAINT `cnimagerevision_2_cnimagecontent` FOREIGN KEY (`image_revision_id`) REFERENCES `cireports_cnimagerevision` (`id`),
    CONSTRAINT `package_2_cnimagecontent` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnimagehelmchartmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_revision_id` integer UNSIGNED NOT NULL,
    `helm_chart_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cnimagerevision_2_cnimagehelmchartmapping` FOREIGN KEY (`image_revision_id`) REFERENCES `cireports_cnimagerevision` (`id`),
    CONSTRAINT `cnhelmchartrevision_2_cnimagehelmchartmapping` FOREIGN KEY (`helm_chart_revision_id`) REFERENCES `cireports_cnhelmchartrevision` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnhelmchartintegrationmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `helm_chart_revision_id` integer UNSIGNED NOT NULL,
    `integration_chart_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cnhelmchartrevision_2_cnhelmchartintegrationmapping` FOREIGN KEY (`helm_chart_revision_id`) REFERENCES `cireports_cnhelmchartrevision` (`id`),
    CONSTRAINT `cnintegrationchartrevision_2_cnhelmchartintegrationmapping` FOREIGN KEY (`integration_chart_revision_id`) REFERENCES `cireports_cnintegrationchartrevision` (`id`)
) ENGINE=InnoDB;

-- END 3.21.492

-- END 3.21.493

-- END 3.21.494

-- END 3.21.495

-- END 3.21.496

-- END 3.21.497

-- END 3.21.498

-- END 3.21.499

-- END 3.21.500

-- END 3.21.501

-- END 3.21.502

-- END 3.21.503

-- END 3.21.504
CREATE TABLE `cireports_test` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `test_id` integer UNSIGNED NOT NULL
) ENGINE=InnoDB;


-- END 3.21.505

-- END 3.21.506

-- END 3.21.507

-- END 3.21.508
ALTER TABLE cireports_cnintegrationchart DROP FOREIGN KEY product_2_cnintegrationchart;
ALTER TABLE cireports_cnintegrationchart DROP COLUMN product_id;
CREATE TABLE `cireports_cnproduct` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_name` varchar(100) NOT NULL UNIQUE,
    `product_number` varchar(10) NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproductset` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_set_version` varchar(20) NOT NULL,
    `status` varchar(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproductrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `version` varchar(20) NOT NULL,
    `product_set_version_id` integer UNSIGNED NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` INTEGER UNSIGNED NULL,
    `build_for` varchar(30),
    CONSTRAINT `cnproduct_2_cnproductrevision` FOREIGN KEY (`product_id`) REFERENCES `cireports_cnproduct` (`id`),
    CONSTRAINT `cnproductset_2_cnproductrevision` FOREIGN KEY (`product_set_version_id`) REFERENCES `cireports_cnproductset` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnintegrationproductmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `integration_chart_revision_id` integer UNSIGNED NOT NULL,
    `cnproduct_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cnintegrationchartrevision_2_cnintegrationproductmapping` FOREIGN KEY (`integration_chart_revision_id`) REFERENCES `cireports_cnintegrationchartrevision` (`id`),
    CONSTRAINT `cnproductrevision_2_cnintegrationproductmapping` FOREIGN KEY (`cnproduct_revision_id`) REFERENCES `cireports_cnproductrevision` (`id`)
) ENGINE=InnoDB;

ALTER TABLE cireports_cnintegrationchartrevision ADD COLUMN `product_set_version_id` integer UNSIGNED NOT NULL;
ALTER TABLE cireports_cnintegrationchartrevision ADD CONSTRAINT `cnproductset_2_cnintegrationchartrevision` FOREIGN KEY (`product_set_version_id`) REFERENCES `cireports_cnproductset` (`id`);
-- END 3.21.508
ALTER TABLE cireports_cnproductrevision ADD COLUMN `values_file_version` varchar(20) NULL;
ALTER TABLE cireports_cnproductset MODIFY COLUMN `status` varchar(200) NOT NULL;
ALTER TABLE cireports_cnproductset ADD COLUMN `drop_version` varchar(20) NOT NULL;
ALTER TABLE cireports_cnimagecontent DROP COLUMN `version`;
ALTER TABLE cireports_cnimagecontent DROP FOREIGN KEY `package_2_cnimagecontent`;
ALTER TABLE cireports_cnimagecontent CHANGE COLUMN `package_id` `package_revision_id` INT(10) UNSIGNED NULL DEFAULT NULL ;
ALTER TABLE cireports_cnimagecontent ADD CONSTRAINT `package_2_cnimagecontent` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`);

DROP TABLE IF EXISTS cireports_cnimagecontent;
DROP TABLE IF EXISTS cireports_cnimagehelmchartmapping;
DROP TABLE IF EXISTS cireports_cnhelmchartintegrationmapping;
DROP TABLE IF EXISTS cireports_cnintegrationproductmapping;
DROP TABLE IF EXISTS cireports_cnimagerevision;
DROP TABLE IF EXISTS cireports_cnhelmchartrevision;
DROP TABLE IF EXISTS cireports_cnintegrationchartrevision;
DROP TABLE IF EXISTS cireports_cnproductrevision;
DROP TABLE IF EXISTS cireports_cnproductset;
DROP TABLE IF EXISTS cireports_cnintegrationchart;
DROP TABLE IF EXISTS cireports_cnimage;
DROP TABLE IF EXISTS cireports_cnhelmchart;
DROP TABLE IF EXISTS cireports_cnproduct;

CREATE TABLE `cireports_cnimage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_name` varchar(100) NOT NULL UNIQUE,
    `image_product_number` varchar(20) NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnimagerevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_id` integer UNSIGNED NOT NULL,
    `parent_id` integer UNSIGNED NULL,
    `version` varchar(20) NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` BIGINT(1) UNSIGNED NULL,
    `gerrit_repo_sha` varchar(100) NULL,
    CONSTRAINT `cnimage_2_cnimagerevision` FOREIGN KEY (`image_id`) REFERENCES `cireports_cnimage` (`id`),
    CONSTRAINT `cnimagerevision_2_cnimagerevision` FOREIGN KEY (`parent_id`) REFERENCES `cireports_cnimagerevision` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnimagecontent` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_revision_id` integer UNSIGNED NOT NULL,
    `package_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cnimagerevision_2_cnimagecontent` FOREIGN KEY (`image_revision_id`) REFERENCES `cireports_cnimagerevision` (`id`),
    CONSTRAINT `packagerevision_2_cnimagecontent` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnhelmchart` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `helm_chart_name` varchar(100) NOT NULL UNIQUE,
    `helm_chart_product_number` varchar(20) NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnhelmchartrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `helm_chart_id` integer UNSIGNED NOT NULL,
    `version` varchar(20) NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` BIGINT(1) UNSIGNED NULL,
    `gerrit_repo_sha` varchar(100) NULL,
    CONSTRAINT `cnhelmchart_2_cnhelmchartrevision` FOREIGN KEY (`helm_chart_id`) REFERENCES `cireports_cnhelmchart` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnimagehelmchartmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_revision_id` integer UNSIGNED NOT NULL,
    `helm_chart_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cnimagerevision_2_cnimagehelmchartmapping` FOREIGN KEY (`image_revision_id`) REFERENCES `cireports_cnimagerevision` (`id`),
    CONSTRAINT `cnhelmchartrevision_2_cnimagehelmchartmapping` FOREIGN KEY (`helm_chart_revision_id`) REFERENCES `cireports_cnhelmchartrevision` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproductset` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_set_name` varchar(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproduct` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_set_id` integer UNSIGNED NOT NULL,
    `product_name` varchar(100) NOT NULL UNIQUE,
    CONSTRAINT `cnproductset_2_cnproduct` FOREIGN KEY (`product_set_id`) REFERENCES `cireports_cnproductset` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproductsetversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_set_version` varchar(20) NOT NULL,
    `status` varchar(254) NOT NULL,
    `drop_version` varchar(20) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproductrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `version` varchar(20) NOT NULL,
    `gerrit_repo_sha` varchar(100) NULL,
    `product_set_version_id` integer UNSIGNED NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` BIGINT(1) UNSIGNED NULL,
    `values_file_version` varchar(20) NULL,
    CONSTRAINT `cnproduct_2_cnproductrevision` FOREIGN KEY (`product_id`) REFERENCES `cireports_cnproduct` (`id`),
    CONSTRAINT `cnproductsetversion_2_cnproductrevision` FOREIGN KEY (`product_set_version_id`) REFERENCES `cireports_cnproductsetversion` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnhelmchartproductmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_revision_id` integer UNSIGNED NOT NULL,
    `helm_chart_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cnproductrevision_2_cnhelmchartproductmapping` FOREIGN KEY (`product_revision_id`) REFERENCES `cireports_cnproductrevision` (`id`),
    CONSTRAINT `cnhelmchartrevision_2_cnhelmchartproductmapping` FOREIGN KEY (`helm_chart_revision_id`) REFERENCES `cireports_cnhelmchartrevision` (`id`)
) ENGINE=InnoDB;

-- END 3.21.509

-- END 3.21.510

-- END 3.21.511

-- END 3.21.512
CREATE TABLE `dmt_enmdeploymenttype` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(40) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `dmt_ipversion` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(15) NOT NULL UNIQUE
) ENGINE=InnoDB;

ALTER TABLE dmt_cluster ADD COLUMN `enmDeploymentType_id` SMALLINT UNSIGNED NULL;
ALTER TABLE dmt_cluster ADD CONSTRAINT `cluster_2_enmdeploymenttype` FOREIGN KEY (`enmDeploymentType_id`) REFERENCES `dmt_enmdeploymenttype` (`id`);

ALTER TABLE dmt_cluster ADD COLUMN `ipVersion_id` SMALLINT UNSIGNED NULL;
ALTER TABLE dmt_cluster ADD CONSTRAINT `cluster_2_ipversion` FOREIGN KEY (`ipVersion_id`) REFERENCES `dmt_ipversion` (`id`);

-- END 3.21.513

-- END 3.21.514

-- END 3.21.515

-- END 3.21.516

-- END 3.21.517

-- END 3.21.518

-- END 3.21.519

-- END 3.21.520

-- END 3.21.521

-- END 3.21.522

-- END 3.21.523

-- END 3.21.524

-- END 3.21.525
ALTER TABLE cireports_cnproductrevision ADD COLUMN `values_file_name` varchar(100) NULL;
ALTER TABLE cireports_cnproductrevision ADD COLUMN `verified` bool NOT NULL DEFAULT FALSE;
-- END 3.21.526

-- END 3.21.527

-- END 3.21.528

-- END 3.21.529

-- END 3.21.530

-- END 3.21.531
ALTER TABLE dmt_databasevips ADD COLUMN `gossipRouter_address1_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `gossipRouter_1_ip` FOREIGN KEY (`gossipRouter_address1_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_databasevips ADD COLUMN `gossipRouter_address2_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `gossipRouter_2_ip` FOREIGN KEY (`gossipRouter_address2_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.21.532

-- END 3.21.533

-- END 3.21.534

-- END 3.21.535

-- END 3.21.536

-- END 3.21.537

-- END 3.21.538
CREATE TABLE `dmt_redfishversionmapping` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reference` varchar(20) NOT NULL UNIQUE,
    `version` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- END 3.21.539

-- END 3.21.540

-- END 3.21.541

-- END 3.21.542

-- END 3.21.543
CREATE TABLE `dmt_dvmsinformation` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `external_ipv4_id` integer UNSIGNED NULL,
    `external_ipv6_id` integer UNSIGNED NULL,
    `internal_ipv4_id` integer UNSIGNED NULL,
    CONSTRAINT `dvmsinformation_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `dvmsinformation_2_ipaddress` FOREIGN KEY (`external_ipv4_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `dvmsinformation_2_ipv6address` FOREIGN KEY (`external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `dvmsinformation_2_ipinternal` FOREIGN KEY (`internal_ipv4_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB;

-- END 3.21.544

-- END 3.21.545

-- END 3.21.546

ALTER TABLE `cireports_cnproductsetversion` ADD COLUMN `overall_status_id` SMALLINT UNSIGNED;
ALTER TABLE `cireports_cnproductsetversion` ADD CONSTRAINT `cnproductsetversion_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`);

CREATE TABLE `cireports_requiredcnconfidencelevel` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `confidence_level_name` varchar(100) NOT NULL UNIQUE,
    `required` bool NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;

INSERT INTO cireports_requiredcnconfidencelevel(confidence_level_name) values('cENM-Build-Integration-Charts');
INSERT INTO cireports_requiredcnconfidencelevel(confidence_level_name) values('cENM-Deploy-II-Charts');
INSERT INTO cireports_requiredcnconfidencelevel(confidence_level_name) values('cENM-RFA');
INSERT INTO cireports_requiredcnconfidencelevel(confidence_level_name) values('cENM-Build-CSAR');
INSERT INTO cireports_requiredcnconfidencelevel(confidence_level_name) values('cENM-Build-Images');

-- END 3.21.552

-- END 3.21.553

-- END 3.21.554

-- END 3.21.555

-- END 3.21.556

-- END 3.21.557

-- END 3.21.558

-- END 3.21.559

-- END 3.21.560

-- END 3.21.561

-- END 3.21.562

-- END 3.21.563

-- END 3.21.564

-- END 3.21.565

-- END 3.21.566

-- END 3.21.567

-- END 3.21.568

-- END 3.21.569

-- END 3.21.570

-- END 3.21.571

-- END 3.21.572

-- END 3.21.573

-- END 3.21.574

-- END 3.21.575

-- END 3.21.576

-- END 3.21.577

-- END 3.21.578

-- END 3.21.579

-- END 3.21.580

-- END 3.21.581

-- END 3.21.582

-- END 3.21.583

-- END 3.21.584

-- END 3.21.585

-- END 3.21.586

-- END 3.21.587

-- END 3.21.588

-- END 3.21.589

-- END 3.21.590

-- END 3.21.591

-- END 3.21.592

-- END 3.21.593

-- END 3.21.594

-- END 3.21.595

-- END 3.21.596

-- END 3.21.597

-- END 3.21.603

-- END 3.21.604

-- END 3.21.605

-- END 3.21.606

-- END 3.21.607

-- END 3.21.608

-- END 3.21.609

-- END 3.21.610

-- END 3.21.611

-- END 3.21.612

-- END 3.21.613

-- END 3.21.614

-- END 3.21.615

-- END 3.21.616

-- END 3.21.617

-- END 3.21.618

-- END 3.21.619

-- END 3.21.620

-- END 3.21.621

-- END 3.21.622

-- END 3.21.623

-- END 3.21.624

-- END 3.21.625

-- END 3.21.626

-- END 3.21.627

-- END 3.21.628

-- END 3.21.629

-- END 3.21.630

-- END 3.21.631

-- END 3.21.632

-- END 3.21.633

-- END 3.21.634

-- END 3.21.635

-- END 3.21.636

-- END 3.21.637

-- END 3.21.638

-- END 3.21.639

-- END 3.21.640

-- END 3.21.641

ALTER TABLE dmt_deploymentbaseline MODIFY `teAllureLogUrl` varchar(200) NULL;

-- END 3.21.642

-- END 3.21.643

-- END 3.21.644

-- END 3.21.645

-- END 3.21.646

-- END 3.21.647

-- END 3.21.648

-- END 3.21.649

-- END 3.21.650

-- END 3.21.651

-- END 3.21.652

-- END 3.21.653

-- END 3.21.654

-- END 3.21.655

-- END 3.21.656

-- END 3.21.657

-- END 3.21.658

-- END 3.21.659

-- END 3.21.660

-- END 3.21.661

-- END 3.21.662


-- END 3.21.663

-- END 3.21.664

-- END 3.21.665

-- END 3.21.666

-- END 3.21.667

-- END 3.21.668

-- END 3.21.669

-- END 3.21.670

-- END 3.21.671

-- END 3.21.672

-- END 3.21.673

-- END 3.21.674

-- END 3.21.675

-- END 3.21.676

-- END 3.21.677

-- END 3.21.678

-- END 3.21.679

-- END 3.21.680

-- END 3.21.681

-- END 3.21.682

-- END 3.21.683

-- END 3.21.684

-- END 3.21.685

-- END 3.21.686

-- END 3.21.687

-- END 3.21.688

-- END 3.21.689

-- END 3.21.690

-- END 3.21.691

-- END 3.21.692

-- END 3.21.693

-- END 3.21.694

-- END 3.21.695

-- END 3.21.696

-- END 3.21.697

-- END 3.21.698

-- END 3.21.699

-- END 3.21.700

-- END 3.21.701

-- END 3.21.702

-- END 3.21.703

-- END 3.21.704

-- END 3.21.705

-- END 3.21.706

-- END 3.21.707

-- END 3.21.708

-- END 3.21.709

-- END 3.21.710

-- END 3.21.711

-- END 3.21.712

-- END 3.21.713

-- END 3.21.714

-- END 3.21.715

-- END 3.21.716

-- END 3.21.717

-- END 3.21.718

-- END 3.21.719

-- END 3.21.720

-- END 3.21.721

-- END 3.21.722

-- END 3.21.723

-- END 3.21.724

-- END 3.21.725

-- END 3.21.726

-- END 3.21.727

-- END 3.21.728

-- END 3.21.729

-- END 3.21.730

-- END 3.21.731

-- END 3.21.732

-- END 3.21.733

-- END 3.21.734

-- END 3.21.735

-- END 3.21.736

-- END 3.21.737

-- END 3.21.738

-- END 3.21.739

-- END 3.21.740

-- END 3.21.741

-- END 3.21.742

-- END 3.21.743

-- END 3.21.744

-- END 3.21.745

-- END 3.21.746

-- END 3.21.747

-- END 3.21.748

-- END 3.21.749

-- END 3.21.750

-- END 3.21.751

-- END 3.21.752

-- END 3.21.753

-- END 3.21.754

-- END 3.21.755

-- END 3.21.756

-- END 3.21.757

-- END 3.21.758

-- END 3.21.759

-- END 3.21.760

-- END 3.21.761

-- END 3.21.762

-- END 3.21.763

-- END 3.21.764

-- END 3.21.765

-- END 3.21.766

-- END 3.21.767

-- END 3.21.768

-- END 3.21.769

-- END 3.21.770

-- END 3.21.771

ALTER TABLE dmt_lvsroutervipextended DROP FOREIGN KEY `lmsipv6_2_ipv6`;
ALTER TABLE dmt_lvsroutervipextended DROP INDEX `lmsipv6_2_ipv6`;
ALTER TABLE dmt_lvsroutervipextended DROP COLUMN `lms_ipv6_id`;

-- END 3.21.772

-- END 3.21.773

-- END 3.21.774

CREATE TABLE `cireports_cnproducttype` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_type_name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

INSERT INTO cireports_cnproducttype(product_type_name) VALUES ("Undefined");
INSERT INTO cireports_cnproducttype(product_type_name) VALUES ("CSAR");
INSERT INTO cireports_cnproducttype(product_type_name) VALUES ("Integration Chart");
INSERT INTO cireports_cnproducttype(product_type_name) VALUES ("Deployment Utility");

ALTER TABLE cireports_cnproduct ADD COLUMN `product_type_id` integer UNSIGNED NOT NULL DEFAULT 1;
ALTER TABLE cireports_cnproduct ADD CONSTRAINT `cnproducttype_2_cnproduct` FOREIGN KEY (`product_type_id`) REFERENCES `cireports_cnproducttype` (`id`);

-- END 3.21.775

-- END 3.21.776

-- END 3.21.777

-- END 3.21.778

-- END 3.21.779

-- END 3.21.780

-- END 3.21.781

-- END 3.21.782

-- END 3.21.783

-- END 3.21.784

-- END 3.21.785

-- END 3.21.786

-- END 3.21.787

-- END 3.21.788

ALTER TABLE dmt_ssodetails ADD COLUMN `brsadm_password` varchar(100) AFTER citrixFarm;

CREATE TABLE `cireports_requiredramapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `team_inventory_ra_name` varchar(100) NOT NULL UNIQUE,
    `component_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `requiredramapping_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`)
) ENGINE=InnoDB;

-- END 3.21.789

-- END 3.21.790

-- END 3.21.791

-- END 3.21.792

ALTER TABLE cireports_requiredcnconfidencelevel ADD COLUMN `include_baseline` bool NOT NULL DEFAULT FALSE;

ALTER TABLE cireports_cnproductsetversion MODIFY COLUMN `status` varchar(500) NOT NULL;

-- END 3.21.793

-- END 3.21.794

-- END 3.21.795

-- END 3.21.796

-- END 3.21.797

-- END 3.21.798

-- END 3.21.799

-- END 3.21.800

-- END 3.21.801

-- END 3.21.802

-- END 3.21.803

-- END 3.21.804

-- END 3.21.805

-- END 3.21.806

-- END 3.21.807

-- END 3.21.808

-- END 3.21.809

-- END 3.21.810
ALTER TABLE dmt_databasevips ADD COLUMN `eshistory_address_id` integer UNSIGNED;
ALTER TABLE dmt_databasevips ADD CONSTRAINT `eshistory_2_ip` FOREIGN KEY (`eshistory_address_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.21.811

-- END 3.21.812

-- END 3.21.813

-- END 3.21.814

-- END 3.21.815

-- END 3.21.816

ALTER TABLE dmt_virtualimageinfoip MODIFY hostname longtext NULL;
ALTER TABLE cireports_cnproductsetversion ADD COLUMN `active` bool NOT NULL DEFAULT TRUE;
ALTER TABLE cireports_cnproduct ADD COLUMN `repo_name` varchar(100) NULL;

-- END 3.21.817



-- END 3.21.818

-- END 3.21.819

-- END 3.21.820

-- END 3.21.821

-- END 3.21.822

-- END 3.21.823

-- END 3.21.824

-- END 3.21.825

-- END 3.21.826

-- END 3.21.827

-- END 3.21.828

-- END 3.21.829

-- END 3.21.830

-- END 3.21.831

-- END 3.21.832

-- END 3.21.833

-- END 3.21.834

-- END 3.21.835

-- END 3.21.836

CREATE TABLE `cireports_cndrop` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `cnProductSet_id` integer UNSIGNED NOT NULL,
    `active_date` DATETIME NOT NULL,
    `reopen`  BOOLEAN NOT NULL DEFAULT 0,
    `designbase_id` smallint UNSIGNED,
    CONSTRAINT `cnDrop_2_cnProductSet` FOREIGN KEY (`cnProductSet_id`) REFERENCES `cireports_cnproductset` (`id`),
    CONSTRAINT `cnDrop_2_cnDrop` FOREIGN KEY (`designbase_id`) REFERENCES `cireports_cndrop` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndeliverygroup` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cndrop_id` SMALLINT UNSIGNED NOT NULL,
    `cnProductSetVersion_id` INT(10) UNSIGNED,
    `queued` bool NOT NULL,
    `delivered` bool NOT NULL,
    `obsoleted` bool NOT NULL,
    `deleted` bool NOT NULL,
    `creator` varchar(100),
    `component_id` SMALLINT UNSIGNED,
    `modifiedDate` timestamp NULL,
    `createdDate` timestamp NULL,
    `deliveredDate` timestamp NULL,
    `missingDependencies` bool NOT NULL,
    `readinessCheck` bool NOT NULL,
    `bugOrTR` bool NOT NULL,
    CONSTRAINT `cndeliverygroup_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`),
    CONSTRAINT `cndeliverygroup_2_cndrop` FOREIGN KEY (`cndrop_id`) REFERENCES `cireports_cndrop` (`id`),
    CONSTRAINT `cndeliverygroup_2_cnproductsetversion` FOREIGN KEY (`cnProductSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndeliverygroupcomment` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `comment` longtext NOT NULL,
    `date` datetime,
    CONSTRAINT `cndeliverygroupcomment_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnjiraissue` (
    `id` INT(10) UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `jiraNumber` varchar(20) NOT NULL,
    `issueType` varchar(30) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cngerrit` (
    `id` INT(10) UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `gerrit_link` varchar(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnpipeline` (
    `id` INT(10) UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `pipeline_link` varchar(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndgtocnimagetocngerritmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL UNIQUE PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `cnImage_id` integer UNSIGNED NOT NULL,
    `cnGerrit_id` integer UNSIGNED NULL,
    CONSTRAINT `cndgtocnimagetocngerritmap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtocnimagetocngerritmap_2_cnimage` FOREIGN KEY (`cnImage_id`) REFERENCES `cireports_cnimage` (`id`),
    CONSTRAINT `cndgtocnimagetocngerritmap_2_cngerrit` FOREIGN KEY (`cnGerrit_id`) REFERENCES `cireports_cngerrit` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndgtocnproducttocngerritmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `cnProduct_id` integer UNSIGNED NOT NULL,
    `cnGerrit_id` integer UNSIGNED NULL,
    CONSTRAINT `cndgtocnproducttocngerritmap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtocnproducttocngerritmap_2_cnProduct` FOREIGN KEY (`cnProduct_id`) REFERENCES `cireports_cnproduct` (`id`),
    CONSTRAINT `cndgtocnproducttocngerritmap_2_cngerrit` FOREIGN KEY (`cnGerrit_id`) REFERENCES `cireports_cngerrit` (`id`)
) ENGINE=InnoDB;


CREATE TABLE `cireports_cndgtocnpipelinetocngerritmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `cnPipeline_id` integer UNSIGNED NOT NULL,
    `cnGerrit_id` integer UNSIGNED NULL,
    CONSTRAINT `cndgtocnpipelinetocngerritmap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtocnpipelinetocngerritmap_2_cnPipeline` FOREIGN KEY (`cnPipeline_id`) REFERENCES `cireports_cnpipeline` (`id`),
    CONSTRAINT `cndgtocnpipelinetocngerritmap_2_cngerrit` FOREIGN KEY (`cnGerrit_id`) REFERENCES `cireports_cngerrit` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndgtodgmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cndgtodgmap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtodgmap_2_deliverygroup` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndgtocnjiraissuemap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `cnJiraIssue_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cndgtocnjiraissuemap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtocnjiraissuemap_2_cnjiraissue` FOREIGN KEY (`cnJiraIssue_id`) REFERENCES `cireports_cnjiraissue` (`id`)
) ENGINE=InnoDB;

-- END 3.21.837

-- END 3.21.838

-- END 3.21.839

-- END 3.21.840

-- END 3.21.841

-- END 3.21.842

-- END 3.21.843


-- END 3.21.844

-- END 3.21.845

-- END 3.21.846

-- END 3.21.847

-- END 3.21.848

-- END 3.21.849

ALTER TABLE `cireports_cndeliverygroup` ADD COLUMN `teamEmail` varchar(100) NULL AFTER creator;

-- END 3.21.850

-- END 3.21.851

-- END 3.21.852

-- END 3.21.853

-- END 3.21.854

-- END 3.21.855

-- END 3.21.856

-- END 3.21.857

-- END 3.21.858

-- END 3.21.859

-- END 3.21.860

ALTER TABLE dmt_nasstoragedetails ADD COLUMN `nasType` varchar(32) NULL AFTER fileSystem3;

ALTER TABLE dmt_storage ADD COLUMN `serial_number` varchar(18) NULL UNIQUE AFTER domain_name;

ALTER TABLE dmt_vlandetails ADD COLUMN `management_vlan` integer NULL AFTER services_vlan;

-- END 3.21.861

-- END 3.21.862

-- END 3.21.863

-- END 3.21.864

-- END 3.21.865

-- END 3.21.866

-- END 3.21.867

-- END 3.21.868

ALTER TABLE `cireports_cndeliverygroup` DROP FOREIGN KEY `cndeliverygroup_2_cnproductsetversion`;
ALTER TABLE `cireports_cndeliverygroup` ADD CONSTRAINT `cndeliverygroup_2_cnproductsetversion` FOREIGN KEY (`cnProductSetVersion_id`) REFERENCES `cireports_cnproductsetversion` (`id`);

-- END 3.21.869

-- END 3.21.870

-- END 3.21.871

-- END 3.21.872

ALTER TABLE `cireports_cnproductrevision` ADD COLUMN `dev_link` varchar(500) NULL AFTER size;

ALTER TABLE `cireports_cnproduct` ADD COLUMN `published_link` varchar(500) NULL AFTER repo_name;

UPDATE `cireports_cnproduct` SET `published_link` = "https://arm.epk.ericsson.se/artifactory/proj-enm-helm" WHERE `product_name` IN ("eric-enm-infra-integration","eric-enm-stateless-integration","eric-enm-bro-integration","eric-enm-pre-deploy-integration","eric-enm-monitoring-integration","enm-installation-package");

ALTER TABLE `cireports_cnimage` ADD COLUMN `repo_name` varchar(100) NULL AFTER image_product_number;

-- END 3.21.873

ALTER TABLE dmt_nasstoragedetails ADD COLUMN `nasNdmpPassword` varchar(100) NULL AFTER nasType;
ALTER TABLE dmt_nasstoragedetails ADD COLUMN `nasServerPrefix` varchar(50) NULL AFTER nasNdmpPassword;

ALTER TABLE dmt_storage ADD COLUMN `nasEthernetPorts` varchar(30) NOT NULL DEFAULT "0,2";
ALTER TABLE dmt_storage ADD COLUMN `sanAdminPassword` varchar(100) NULL;
ALTER TABLE dmt_storage ADD COLUMN `sanPoolDiskCount` integer UNSIGNED NOT NULL DEFAULT 15;
ALTER TABLE dmt_storage ADD COLUMN `sanServicePassword` varchar(100) NULL;

-- END 3.21.874

ALTER TABLE `cireports_cndeliverygroup` ADD COLUMN `obsoletedDate` timestamp NULL AFTER deliveredDate;
ALTER TABLE `cireports_cndeliverygroup` ADD COLUMN `deletedDate` timestamp NULL AFTER obsoletedDate;

-- END 3.21.875

-- END 3.21.876

-- END 3.21.877

-- END 3.21.878

-- END 3.21.879

-- END 3.21.880

-- END 3.21.881

-- END 3.21.882

-- END 3.21.883

-- END 3.21.884

ALTER TABLE dmt_deploymentstatus MODIFY COLUMN status_changed datetime NOT NULL default CURRENT_TIMESTAMP;



-- END 3.21.885

-- END 3.21.886

-- END 3.21.887

-- END 3.21.888

-- END 3.21.889

CREATE TABLE `cireports_cnbuildlog` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop` varchar(50) NOT NULL,
    `fromCnProductSetVersion_id` integer UNSIGNED,
    `toCnProductSetVersion_id` integer UNSIGNED,
    `overall_status_id` smallint UNSIGNED,
    `deploymentName` varchar(100) NULL,
    `active` bool NOT NULL,
    CONSTRAINT `cnbuildlog_2_fromcnproductsetversion` FOREIGN KEY (`fromCnProductSetVersion_id`) REFERENCES `cireports_cnproductsetversion` (`id`),
    CONSTRAINT `cnbuildlog_2_tocnproductsetversion` FOREIGN KEY (`toCnProductSetVersion_id`) REFERENCES `cireports_cnproductsetversion` (`id`),
    CONSTRAINT `cnbuildlog_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnconfidencelevelrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnConfidenceLevel_id` integer UNSIGNED,
    `status_id` smallint UNSIGNED,
    `cnBuildLog_id` integer UNSIGNED,
    `createdDate` datetime,
    `updatedDate` datetime,
    `reportLink` longtext NULL,
    `buildJobLink` longtext NULL,
    `percentage` varchar(10) NULL,
    `buildDate` datetime,
    CONSTRAINT `cnconfidencelevelrevision_2_requiredcnconfidencelevel` FOREIGN KEY (`cnConfidenceLevel_id`) REFERENCES `cireports_requiredcnconfidencelevel` (`id`),
    CONSTRAINT `cnconfidencelevelrevision_2_states` FOREIGN KEY (`status_id`) REFERENCES `cireports_states` (`id`),
    CONSTRAINT `cnconfidencelevelrevision_2_cnbuildlog` FOREIGN KEY (`cnBuildLog_id`) REFERENCES `cireports_cnbuildlog` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnbuildlogcomment` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnBuildLog_id` integer UNSIGNED NOT NULL,
    `cnJiraIssue_id` integer UNSIGNED NULL,
    `comment` longtext NULL,
    CONSTRAINT `cnbuildlogcomment_2_cnbuildlog` FOREIGN KEY (`cnBuildLog_id`) REFERENCES `cireports_cnbuildlog` (`id`),
    CONSTRAINT `cnbuildlogcomment_2_cnjiraissue` FOREIGN KEY (`cnJiraIssue_id`) REFERENCES `cireports_cnjiraissue` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnconfidenceleveltype` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `confidenceLevelTypeName` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

ALTER TABLE `cireports_requiredcnconfidencelevel` ADD COLUMN `requireBuildLogId` bool NOT NULL AFTER include_baseline;
ALTER TABLE `cireports_requiredcnconfidencelevel` ADD COLUMN `confidenceLevelType_id` integer UNSIGNED AFTER confidence_level_name;
ALTER TABLE `cireports_requiredcnconfidencelevel` ADD CONSTRAINT `requiredcnconfidencelevel_2_cnconfidenceleveltype` FOREIGN KEY (`confidenceLevelType_id`) REFERENCES `cireports_cnconfidenceleveltype` (`id`);

-- END 3.21.890

-- END 3.21.891
ALTER TABLE dmt_nasstoragedetails ADD COLUMN `fcSwitches` boolean NULL DEFAULT NULL;
ALTER TABLE dmt_vlandetails ADD COLUMN `storage_gateway` varchar(15) NULL;

-- END 3.21.892

-- END 3.21.893

-- END 3.21.894

-- END 3.21.895

-- END 3.21.896

ALTER TABLE `cireports_cnbuildlog` ADD COLUMN `testPhase` varchar(50) NULL AFTER `drop`;

-- END 3.21.897

ALTER TABLE dmt_vlandetails DROP COLUMN `storage_gateway`;
ALTER TABLE dmt_vlandetails ADD COLUMN `storage_gateway_id` integer UNSIGNED NULL;
ALTER TABLE dmt_vlandetails ADD CONSTRAINT `storage_gateway_2_ip` FOREIGN KEY (`storage_gateway_id`) REFERENCES `dmt_ipaddress` (`id`);

-- END 3.21.898

-- END 3.21.899

-- END 3.21.900

-- END 3.21.901

-- END 3.21.902

-- END 3.21.903

-- END 3.21.904

-- END 3.21.905

-- END 3.21.906

-- END 3.21.907

-- END 3.21.908

-- END 3.21.909

-- END 3.21.910

ALTER TABLE dmt_nasstoragedetails ADD COLUMN `sanPoolDiskCount` integer UNSIGNED NOT NULL DEFAULT 15;
ALTER TABLE dmt_nasstoragedetails ADD COLUMN `nasEthernetPorts` varchar(30) NOT NULL DEFAULT "0,2";
UPDATE dmt_nasstoragedetails n JOIN dmt_clustertostoragemapping c ON n.cluster_id = c.cluster_id JOIN dmt_storage s ON c.storage_id = s.id SET n.sanPoolDiskCount = s.sanPoolDiskCount, n.nasEthernetPorts = s.nasEthernetPorts;
ALTER TABLE dmt_storage DROP COLUMN `nasEthernetPorts`;
ALTER TABLE dmt_storage DROP COLUMN `sanPoolDiskCount`;



-- END 3.21.911

-- END 3.21.912

-- END 3.21.913

-- END 3.21.914

-- END 3.21.915

-- END 3.21.916

-- END 3.21.917

-- END 3.21.918

ALTER TABLE dmt_cluster ADD COLUMN `compact_audit_logger` boolean NULL DEFAULT NULL;
UPDATE dmt_cluster
SET compact_audit_logger = CASE
    WHEN EXISTS (SELECT * FROM dmt_ddtodeploymentmapping
                  INNER JOIN dmt_deploymentdescription ON dmt_ddtodeploymentmapping.deployment_description_id = dmt_deploymentdescription.id
                  WHERE dmt_ddtodeploymentmapping.cluster_id = dmt_cluster.id
                        AND (dmt_deploymentdescription.name LIKE '%extraLarge%' OR dmt_deploymentdescription.name LIKE '%large_transport_only%')
                 ) THEN true
    ELSE null
END;

-- END 3.21.919

-- END 3.21.920

-- END 3.21.921

-- END 3.21.922

ALTER TABLE cireports_cndgtocnimagetocngerritmap ADD COLUMN `state_id` smallint UNSIGNED NULL;

ALTER TABLE cireports_cndgtocnimagetocngerritmap ADD CONSTRAINT `cndgtocnimagetocngerritmap_2_states` FOREIGN KEY (`state_id`) REFERENCES `cireports_states` (`id`);

ALTER TABLE cireports_cndgtocnimagetocngerritmap ADD COLUMN `revert_change_id` varchar(255) NULL;

ALTER TABLE cireports_cndgtocnproducttocngerritmap ADD COLUMN `state_id` smallint UNSIGNED NULL;

ALTER TABLE cireports_cndgtocnproducttocngerritmap ADD CONSTRAINT `cndgtocnproducttocngerritmap_2_states` FOREIGN KEY (`state_id`) REFERENCES `cireports_states` (`id`);

ALTER TABLE cireports_cndgtocnproducttocngerritmap ADD COLUMN `revert_change_id` varchar(255) NULL;

ALTER TABLE cireports_cndgtocnpipelinetocngerritmap ADD COLUMN `state_id` smallint UNSIGNED NULL;

ALTER TABLE cireports_cndgtocnpipelinetocngerritmap ADD CONSTRAINT `cndgtocnpipelinetocngerritmap_2_states` FOREIGN KEY (`state_id`) REFERENCES `cireports_states` (`id`);

ALTER TABLE cireports_cndgtocnpipelinetocngerritmap ADD COLUMN `revert_change_id` varchar(255) NULL;

INSERT INTO cireports_states (state) VALUES ("not_obsoleted"),("reverted"),("not_reverted"),("conflicts");

-- END 3.21.923

-- END 3.21.924

ALTER TABLE dmt_deploymentbaseline MODIFY `buildURL` varchar(200);

CREATE TABLE `cireports_jiraprojectexception` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `projectName` varchar(45) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT INTO cireports_jiraprojectexception(projectName) VALUES("Continuous Integration Services");
INSERT INTO cireports_jiraprojectexception(projectName) VALUES("CI_FrameworkTeam_PDUOSS");



-- END 3.21.925

-- END 3.21.926

-- END 3.21.927

-- END 3.21.928

ALTER TABLE `cireports_cndeliverygroup` DROP COLUMN `readinessCheck`;
ALTER TABLE cireports_cndeliverygroup ADD COLUMN `cnProductSetVersionSet` boolean NOT NULL DEFAULT 0 AFTER `cnProductSetVersion_id`;
UPDATE cireports_cndeliverygroup SET `cnProductSetVersionSet` = 1 WHERE `delivered` = 1 OR `obsoleted` = 1;
-- END 3.21.929

-- END 3.21.930

-- END 3.21.931

-- END 3.21.932

CREATE TABLE `cireports_cndeliverygroupsubscription` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    UNIQUE (`user_id`, `cnDeliveryGroup_id`),
    CONSTRAINT `cndeliverygroup_subscription` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`)
) ENGINE=InnoDB;

-- END 3.21.933

-- END 3.21.934

-- END 3.21.935

-- END 3.21.936

-- END 3.21.937

-- END 3.21.938

-- END 3.21.939

-- END 3.21.940
CREATE TABLE `cireports_versionsupportmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifactId` varchar(150) NULL,
    `version` varchar(15) NULL,
    `feature` varchar(100) NULL
) ENGINE=InnoDB;
INSERT INTO cireports_versionsupportmapping(artifactId,version,feature) VALUES("ERICautodeploy_CXP9038326","2.34.8","mrrnSha512");

-- END 3.21.941

-- END 3.21.942

-- END 3.21.943

-- END 3.21.944

CREATE TABLE `dmt_itamwebhookendpoint` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `endpoint` varchar(200) NULL UNIQUE
) ENGINE=InnoDB;

-- END 3.21.945

-- END 3.21.946

-- END 3.21.947

-- END 3.21.948

-- END 3.21.949

-- END 3.21.950

-- END 3.21.951

CREATE TABLE `cireports_jiramigrationproject` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `projectKeyName` varchar(15) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- END 3.21.952

-- END 3.21.953

-- END 3.21.954

-- END 3.21.955

-- END 3.21.956

-- END 3.21.957

-- END 3.21.958

-- END 3.21.959
ALTER TABLE cireports_isobuild ADD COLUMN `systemInfo` varchar(100) NULL;

-- END 3.21.960

-- END 3.21.961

-- END 3.21.962
ALTER TABLE dmt_lvsroutervipextended ADD COLUMN oran_internal_id INT UNSIGNED NULL AFTER `svc_pm_ipv6_id`;
ALTER TABLE dmt_lvsroutervipextended ADD CONSTRAINT `oraninternal_2_ip` FOREIGN KEY (`oran_internal_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervipextended ADD COLUMN oran_internal_ipv6_id INT UNSIGNED NULL AFTER `oran_internal_id`;
ALTER TABLE dmt_lvsroutervipextended ADD CONSTRAINT `oraninternalipv6_2_ipv6` FOREIGN KEY (`oran_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervipextended ADD COLUMN oran_external_id INT UNSIGNED NULL AFTER `oran_internal_ipv6_id`;
ALTER TABLE dmt_lvsroutervipextended ADD CONSTRAINT `oranexternal_2_ip` FOREIGN KEY (`oran_external_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_lvsroutervipextended ADD COLUMN oran_external_ipv6_id INT UNSIGNED NULL AFTER `oran_external_id`;
ALTER TABLE dmt_lvsroutervipextended ADD CONSTRAINT `oranexternalipv6_2_ipv6` FOREIGN KEY (`oran_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);
-- END 3.21.963

-- END 3.21.964

-- END 3.21.965

-- END 3.21.966

-- END 3.21.967

-- END 3.21.968
UPDATE cireports_cngerrit SET gerrit_link = REPLACE(gerrit_link, 'https://gerrit.ericsson.se', 'https://gerrit-gamma.gic.ericsson.se');
-- END 3.21.969

-- END 3.21.970

-- END 3.21.971
ALTER TABLE dmt_nasserver ADD COLUMN `sfs_node1_hostname` varchar(45) NULL AFTER `credentials_id`;
ALTER TABLE dmt_nasserver ADD COLUMN `sfs_node2_hostname` varchar(45) NULL AFTER `sfs_node1_hostname`;
-- END 3.21.972
