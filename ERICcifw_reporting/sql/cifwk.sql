-- --------------------------------------------------------------------------------------- --
-- Please ensure that any table you add to this script is put in the correct location
-- Each Section Matches a django application area
-- The current list of Sections are
--
-- FWK
-- CIREPORTS
-- DMT
-- AVS
-- FEM
-- VIS
-- EXCELLENCE
-- DEPMODEL
-- CPI
-- METRICS
-- CLOUD
-- FASTCOMMIT
-- --------------------------------------------------------------------------------------- --
-- ----------------- --
-- FWK SECTION START --
-- ----------------- --
CREATE TABLE `fwk_team` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `desc` longtext
) ENGINE=InnoDB
;
CREATE TABLE `fwk_urldisplay` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `url` varchar(450) NOT NULL,
    `title` varchar(50) NOT NULL,
    `desc` longtext
) ENGINE=InnoDB
;
CREATE TABLE `fwk_tvinfomap` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `team_id` smallint UNSIGNED NOT NULL,
    `url_id` smallint UNSIGNED NOT NULL,
    `time` integer UNSIGNED NOT NULL,
    `sequence` integer UNSIGNED NOT NULL,
    CONSTRAINT `tvinfomap_2_team` FOREIGN KEY (`team_id`) REFERENCES `fwk_team` (`id`),
    CONSTRAINT `tvinfomap_2_urldisplay` FOREIGN KEY (`url_id`) REFERENCES `fwk_urldisplay` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `fwk_cifwkdevelopmentserver` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `vm_hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `ipAddress` varchar(30) NOT NULL UNIQUE,
    `bookingDate` datetime not null default "1970-01-01 00:00:00",
    `owner` varchar(30) NOT NULL UNIQUE,
    `description` longtext
) ENGINE=InnoDB
;
CREATE TABLE `fwk_glossary` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE,
    `description` longtext
) ENGINE=InnoDB
;
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

-- --------------- --
-- FWK SECTION END --
-- --------------- --

-- ----------------------- --
-- CIREPORTS SECTION START --
-- ----------------------- --
CREATE TABLE `cireports_solutionset` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_number` varchar(12) NOT NULL,
    `name` varchar(50) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `cireports_product` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `pkgName` bool NOT NULL DEFAULT 1,
    `pkgNumber` bool NOT NULL DEFAULT 1,
    `pkgVersion` bool NOT NULL DEFAULT 1,
    `type` bool NOT NULL DEFAULT 1,
    `pkgRState` bool NOT NULL DEFAULT 1,
    `platform` bool NOT NULL DEFAULT 1,
    `category` bool NOT NULL DEFAULT 1,
    `intendedDrop` bool NOT NULL DEFAULT 1,
    `deliveredTo` bool NOT NULL DEFAULT 1,
    `date` bool NOT NULL DEFAULT 1,
    `prototypeBuild` bool NOT NULL DEFAULT 1,
    `kgbTests` bool NOT NULL DEFAULT 1,
    `teamRunningKgb` bool NOT NULL DEFAULT 0,
    `cidTests` bool NOT NULL DEFAULT 1,
    `cdbTests` bool NOT NULL DEFAULT 1,
    `isoIncludedIn` bool NOT NULL DEFAULT 1,
    `deliver` bool NOT NULL DEFAULT 1,
    `pri` bool NOT NULL DEFAULT 1,
    `obsolete` bool NOT NULL DEFAULT 1,
    `dependencies` bool NOT NULL DEFAULT 1,
    `isoDownload` bool NOT NULL DEFAULT 1,
    `size` bool NOT NULL DEFAULT 1
) ENGINE=InnoDB
;
CREATE TABLE `cireports_release` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `track` varchar(20) NOT NULL,
    `product_id` integer UNSIGNED NOT NULL,
    `iso_artifact` varchar(100),
    `iso_groupId` varchar(100) NOT NULL DEFAULT "com.ericsson.nms",
    `iso_arm_repo` varchar(30) NOT NULL DEFAULT "releases",
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `masterArtifact_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `release_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`),
    UNIQUE INDEX releaseProduct (name, product_id)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_drop` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `release_id` smallint UNSIGNED NOT NULL,
    `planned_release_date` DATETIME,
    `actual_release_date` DATETIME,
    `mediaFreezeDate` DATETIME,
    `designbase_id` smallint UNSIGNED,
    `correctionalDrop` bool NOT NULL DEFAULT 0,
    `systemInfo` varchar(100) NOT NULL,
    `status` varchar(20) NOT NULL DEFAULT 'open',
    CONSTRAINT `drop_2_release` FOREIGN KEY (`release_id`) REFERENCES `cireports_release` (`id`),
    CONSTRAINT `drop_2_drop` FOREIGN KEY (`designbase_id`) REFERENCES `cireports_drop` (`id`),
    UNIQUE INDEX dropRelease (name, release_id)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_phasestate` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(15) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `cireports_categories` (
  `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_testwaretype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `type` varchar(15) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_package` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE,
    `package_number` varchar(100) NOT NULL UNIQUE,
    `description` varchar(255) NOT NULL,
    `signum` varchar(12) NOT NULL,
    `obsolete_after_id` smallint UNSIGNED,
    `hide` bool NOT NULL DEFAULT 0,
    `testware` bool NOT NULL DEFAULT 0,
    `git_repo` varchar(200),
    `includedInPriorityTestSuite` bool NOT NULL DEFAULT FALSE,
    CONSTRAINT `pkg_2_drop` FOREIGN KEY (`obsolete_after_id`) REFERENCES `cireports_drop` (`id`),
    UNIQUE INDEX nameNumber (name, package_number)
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
CREATE TABLE `cireports_productpackagemapping` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `package_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `productpkgmapping_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`),
    CONSTRAINT `productpkgmapping_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    UNIQUE INDEX productpackagemap (product_id, package_id)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_packagerevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint UNSIGNED NOT NULL,
    `date_created` timestamp NOT NULL DEFAULT "2012-01-01 00:00:00",
    `published` datetime,
    `kgb_test` varchar(20) NOT NULL DEFAULT "not_started",
    `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0,
    `team_running_kgb_id` smallint UNSIGNED,
    `cid_test` varchar(20) NOT NULL DEFAULT "not_started",
    `cdb_test` varchar(20) NOT NULL DEFAULT "not_started",
    `correction` bool NOT NULL DEFAULT 0,
    `non_proto_build` varchar(5) NOT NULL DEFAULT "true",
    `artifact_ref` varchar(100),
    `groupId` varchar(100),
    `artifactId` varchar(100),
    `version` varchar(100),
    `autodrop` varchar(100),
    `autodeliver` boolean NOT NULL DEFAULT 0,
    `m2type` varchar(100),
    `m2qualifier` varchar(100),
    `last_update` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `arm_repo` varchar(30) NOT NULL DEFAULT "releases",
    `platform` varchar(30) NOT NULL DEFAULT "None",
    `category_id` smallint UNSIGNED NOT NULL DEFAULT 1,
    `media_path` varchar(250) NULL,
    `isoExclude` boolean NOT NULL DEFAULT 0,
    `infra` BOOLEAN NOT NULL DEFAULT 0,
    `size` INTEGER UNSIGNED NOT NULL default 0,
    CONSTRAINT `packagerevision_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `packagerevision_2_categories` FOREIGN KEY (`category_id`) REFERENCES `cireports_categories` (`id`),
    UNIQUE INDEX grpArtVerPlatArmType (groupId, artifactId, version, platform, arm_repo, m2type)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_droppackagemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `drop_id` smallint UNSIGNED NOT NULL,
    `obsolete` bool NOT NULL,
    `released` bool NOT NULL,
    `date_created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `delivery_info` longtext NOT NULL,
    `deliverer_mail` varchar(100),
    `deliverer_name` varchar(100),
    `kgb_test` varchar(20) NULL,
    `testReport` longtext NULL,
    `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0,
    CONSTRAINT `droppackagemapping_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `droppackagemapping_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_obsoleteinfo` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dpm_id` integer UNSIGNED,
    `signum` varchar(12) NOT NULL,
    `reason` TEXT NOT NULL,
    `time_obsoleted` DATETIME,
    CONSTRAINT `obinfo_2_dpm` FOREIGN KEY (`dpm_id`) REFERENCES `cireports_droppackagemapping` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_solutionsetrevision` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `solution_set_id` SMALLINT UNSIGNED NOT NULL,
    `version` varchar(100) NOT NULL,
    CONSTRAINT `solutionsetrevision_2_solutionset` FOREIGN KEY (`solution_set_id`) REFERENCES `cireports_solutionset` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_solutionsetcontents` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `solution_set_rev_id` integer unsigned NOT NULL,
    `packagerevision_id` integer unsigned NOT NULL,
    CONSTRAINT `solutionsetcontents_2_solutionsetrevision` FOREIGN KEY (`solution_set_rev_id`) REFERENCES `cireports_solutionsetrevision` (`id`),
    CONSTRAINT `solutionsetcontents_2_packagerevision` FOREIGN KEY (`packagerevision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_states` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `state` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_mediaartifacttype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `type` varchar(10) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_mediaartifactcategory` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_mediaartifactdeploytype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `type` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_mediaartifact` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `number` varchar(12) NOT NULL UNIQUE,
    `description` varchar(255) NOT NULL,
    `obsoleteAfter_id` SMALLINT UNSIGNED,
    `mediaType` varchar(10) DEFAULT "iso" NOT NULL,
    `hide` bool NOT NULL,
    `testware` bool NOT NULL DEFAULT 0,
    `category_id` smallint UNSIGNED NOT NULL DEFAULT 1,
    `deployType_id` smallint UNSIGNED NOT NULL DEFAULT 1,
    CONSTRAINT `media_2_drop` FOREIGN KEY (`obsoleteAfter_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `mediaartfact_2_category` FOREIGN KEY (`category_id`) REFERENCES `cireports_mediaartifactcategory` (`id`),
    CONSTRAINT `mediaartfact_2_deploytype` FOREIGN KEY (`deployType_id`) REFERENCES `cireports_mediaartifactdeploytype` (`id`)
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
    `number` varchar(12) NOT NULL,
    `release_id` SMALLINT UNSIGNED NOT NULL,
    `productSet_id` SMALLINT UNSIGNED NOT NULL,
    `masterArtifact_id` SMALLINT UNSIGNED NOT NULL,
    `updateMasterStatus` boolean not null default 0,
    CONSTRAINT `prodsetrelease_2_release` FOREIGN KEY (`release_id`) REFERENCES `cireports_release` (`id`),
    CONSTRAINT `prodsetrelease_2_prodset` FOREIGN KEY (`productSet_id`) REFERENCES `cireports_productset` (`id`),
    CONSTRAINT `prodsetrelease_2_mediaartifact` FOREIGN KEY (`masterArtifact_id`) REFERENCES `cireports_mediaartifact` (`id`),
    UNIQUE INDEX nameNumberProductSet (name, number, productSet_id)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_productsetversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `version` varchar(50) NOT NULL,
    `status_id` SMALLINT UNSIGNED NOT NULL,
    `current_status` varchar(2000) NOT NULL,
    `productSetRelease_id` SMALLINT UNSIGNED NOT NULL,
    `drop_id` SMALLINT UNSIGNED,
    UNIQUE INDEX verProdSetRel (`version`, `productSetRelease_id`),
    CONSTRAINT `productsetver_2__productsetrelease` FOREIGN KEY (`productSetRelease_id`) REFERENCES `cireports_productsetrelease` (`id`),
    CONSTRAINT `productsetver_2_states` FOREIGN KEY (`status_id`) REFERENCES `cireports_states` (`id`),
    CONSTRAINT `productsetversion_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_productsetversioncontent` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `productSetVersion_id` integer UNSIGNED NOT NULL,
    `mediaArtifactVersion_id` INT(10) UNSIGNED NOT NULL,
    `status_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `productsetvercont_2_productsetver` FOREIGN KEY (`productSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`),
    CONSTRAINT `productsetvercont_2_states` FOREIGN KEY (`status_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_dropmediaartifactmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mediaArtifactVersion_id` INT(10) UNSIGNED NOT NULL,
    `drop_id` SMALLINT UNSIGNED NOT NULL,
    `obsolete` bool NOT NULL,
    `released` bool NOT NULL,
    `frozen` bool NOT NULL,
    `dateCreated` datetime NOT NULL,
    `deliveryInfo` longtext,
    CONSTRAINT `dropmediaartifactmapping_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_obsoletemediainfo` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dropMediaArtifactMapping_id` integer UNSIGNED,
    `signum` varchar(12) NOT NULL,
    `reason` TEXT NOT NULL,
    `time_obsoleted` DATETIME,
    CONSTRAINT `obinfo_2_dropmediaartifactmapping` FOREIGN KEY (`dropMediaArtifactMapping_id`) REFERENCES `cireports_dropmediaartifactmapping` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_isobuild` (
    `id` INT(10) UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `version`  varchar(100),
    `groupId` varchar(100) NOT NULL,
    `artifactId` varchar(100) NOT NULL,
    `mediaArtifact_id` SMALLINT UNSIGNED NOT NULL,
    `drop_id` smallint UNSIGNED,
    `build_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `current_status`  varchar(2000),
    `overall_status_id`  smallint UNSIGNED,
    `arm_repo` varchar(50) NOT NULL,
    `sed_build_id` smallint UNSIGNED,
    `deploy_script_version` varchar(100),
    `mt_utils_version` varchar(100),
    `size` bigint UNSIGNED NOT NULL default 0,
    `active` boolean NOT NULL default 1,
    `externally_released` boolean NOT NULL default 0,
    `externally_released_ip` boolean NOT NULL default 0,
    `externally_released_rstate` varchar(15),
    `systemInfo` varchar(100) NULL,
    CONSTRAINT `isobuild_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `isostatus_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`),
    CONSTRAINT `isobuild_2_mediaartifact` FOREIGN KEY (`mediaArtifact_id`) REFERENCES `cireports_mediaartifact` (`id`),
    UNIQUE INDEX verGrpArtDrop (version, groupId, artifactId, drop_id)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_isobuildmapping` (
   `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
   `iso_id` INT(10) UNSIGNED NOT NULL,
   `package_revision_id` integer UNSIGNED NOT NULL,
   `drop_id` smallint UNSIGNED NOT NULL,
   `overall_status_id`  smallint UNSIGNED,
   `kgb_test` varchar(20) NULL DEFAULT "not_started",
   `testReport` longtext NULL,
   `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0,
   CONSTRAINT `isobuildmapping_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
   CONSTRAINT `isobuildmapping_2_isobuild` FOREIGN KEY (`iso_id`) REFERENCES `cireports_isobuild` (`id`),
   CONSTRAINT `isobuildmapping_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
   CONSTRAINT `status_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_producttestwaremediamapping` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `productIsoVersion_id` INT(10) UNSIGNED NOT NULL,
    `testwareIsoVersion_id` INT(10) UNSIGNED NOT NULL,
    CONSTRAINT `productmediamapping_2_isobuild` FOREIGN KEY (`productIsoVersion_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `testwaremediamapping_2_isobuild` FOREIGN KEY (`testwareIsoVersion_id`) REFERENCES `cireports_isobuild` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_cdbtypes` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL UNIQUE,
    `sort_order` SMALLINT NOT NULL DEFAULT '0'
)ENGINE=InnoDB
;
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
) ENGINE=InnoDB
;
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
) ENGINE=InnoDB
;
CREATE TABLE `cireports_cdbpkgmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cdb_id` integer UNSIGNED NOT NULL,
    `package_revision_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `cdbpkgmap_2_cdb` FOREIGN KEY (`cdb_id`) REFERENCES `cireports_cdb` (`id`),
    CONSTRAINT `cdbpkgmap_2_pkgrev` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_pri` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY ,
    `pkgver_id` integer  UNSIGNED NOT NULL ,
    `first_pkgver_id` integer  UNSIGNED ,
    `fault_id` varchar(50) NOT NULL ,
    `fault_desc` longtext NOT NULL,
    `fault_type` varchar(50) NOT NULL,
    `drop_id` smallint UNSIGNED,
    `status` varchar(50) NOT NULL,
    `priority` varchar(50) NOT NULL,
    `node_pri` bool NULL DEFAULT 1,
    `comment` varchar(500) NOT NULL,
    CONSTRAINT `package_2_pri` FOREIGN KEY (`pkgver_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `first_package_2_pri` FOREIGN KEY (`first_pkgver_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `drop_2_pri` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;
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
    `author` varchar(255) NOT NULL,
    `number` varchar(255) NOT NULL,
    `revision` varchar(5) NOT NULL,
    `drop_id` smallint UNSIGNED NOT NULL,
    `deliveryDate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `link` varchar(255) NOT NULL,
    `cpi` bool NOT NULL DEFAULT FALSE,
    `owner` varchar(50) NOT NULL,
    `comment` longtext,
    `obsolete_after_id` smallint UNSIGNED,
    CONSTRAINT `doc_2_drop` FOREIGN KEY (`obsolete_after_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `document_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `document_2_documenttype` FOREIGN KEY (`document_type_id`) REFERENCES `cireports_documenttype` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_testwareartifact` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `artifact_number` varchar(12) NOT NULL UNIQUE,
    `description` varchar(255) NOT NULL,
    `signum` varchar(12) NOT NULL,
    `includedInPriorityTestSuite` bool NOT NULL DEFAULT FALSE,
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
    `execution_version` varchar(50) NOT NULL,
    `execution_groupId` varchar(100) NOT NULL,
    `execution_artifactId` varchar(100) NOT NULL,
    `validTestPom` bool NOT NULL DEFAULT TRUE,
    `kgb_status` bool NOT NULL DEFAULT FALSE,
    `cdb_status` bool NOT NULL DEFAULT FALSE,
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
CREATE TABLE `cireports_femlink` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `name` varchar(50) NOT NULL,
    `fem_link` varchar(200) NOT NULL,
    `FemBaseKGBJobURL` bool NOT NULL DEFAULT 0,
    CONSTRAINT `femlinks_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_testresults` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `passed` smallint UNSIGNED ,
    `failed` smallint UNSIGNED ,
    `total` smallint UNSIGNED ,
    `phase` varchar(20),
    `tag` varchar(100),
    `testdate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `test_report` longtext,
    `test_report_directory` varchar(200),
    `testware_pom_directory` varchar(100),
    `host_properties_file` varchar(100)
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
CREATE TABLE `cireports_clue` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` smallint UNSIGNED NOT NULL,
    `codeReview` varchar(20) NULL,
    `codeReviewTime` datetime NULL,
    `unit` varchar(20) NULL,
    `unitTime` datetime NULL,
    `acceptance` varchar(20) NULL,
    `acceptanceTime` datetime NULL,
    `release` varchar(20) NULL,
    `releaseTime` datetime NULL,
    CONSTRAINT `clue_2_pkg` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;
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
CREATE TABLE `cireports_testsinprogress` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `phase` varchar(20),
    `datestarted` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `veLog` varchar(1000),
    CONSTRAINT `testsinprogress_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
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
CREATE TABLE `cireports_isotestresultstotestwaremap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `isobuild_id` INT(10) UNSIGNED NOT NULL,
    `testware_revision_id` integer UNSIGNED NOT NULL,
    `testware_artifact_id` smallint UNSIGNED NOT NULL,
    `testware_run_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `isotestmap_2_testware_artifact_revision` FOREIGN KEY (`testware_revision_id`) REFERENCES `cireports_testwarerevision` (`id`),
    CONSTRAINT `isotestmap_2_testware_artifact` FOREIGN KEY (`testware_artifact_id`) REFERENCES `cireports_testwareartifact` (`id`),
    CONSTRAINT `isotest_2_iso` FOREIGN KEY (`isobuild_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `isotestmap_2_testware_results` FOREIGN KEY (`testware_run_id`) REFERENCES `cireports_testresults` (`id`)
) ENGINE=InnoDB
;
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
CREATE TABLE `cireports_testresultstovisenginelinkmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `velog` varchar(1000),
    `testware_run_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `velog_2_testware_results` FOREIGN KEY (`testware_run_id`) REFERENCES `cireports_testresults` (`id`)
) ENGINE=InnoDB
;
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
CREATE TABLE `cireports_label` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `cireports_component` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `parent_id` smallint unsigned,
    `label_id` smallint unsigned,
    `element` varchar(100) NOT NULL,
    `dateCreated` DATETIME NOT NULL,
    `deprecated` bool NOT NULL default 0,
    UNIQUE INDEX parentChild (`parent_id`, `element`),
    CONSTRAINT `component_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`),
    CONSTRAINT `component_2_component` FOREIGN KEY (`parent_id`) REFERENCES `cireports_component` (`id`),
    CONSTRAINT `component_2_label` FOREIGN KEY (`label_id`) REFERENCES `cireports_label` (`id`)
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
CREATE TABLE `cireports_droplimitedreason` (
    `id`  smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reason` varchar(100) NOT NULL
) ENGINE=InnoDB
;

CREATE TABLE `cireports_dropactivity` (
    `id`  smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` smallint UNSIGNED NOT NULL,
    `action` varchar(100) NOT NULL,
    `desc` longtext NOT NULL,
    `user` varchar(10) NOT NULL,
    `date` datetime NOT NULL,
    `limitedReason_id` smallint UNSIGNED NULL,
    CONSTRAINT `dropactivity_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`),
    CONSTRAINT `dropactivity_2_limitedreason` FOREIGN KEY (`limitedReason_id`) REFERENCES `cireports_droplimitedreason` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_deliverygroup` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` SMALLINT UNSIGNED NOT NULL,
    `deleted` bool NOT NULL,
    `delivered` bool NOT NULL,
    `obsoleted` bool NOT NULL,
    `creator` varchar(100),
    `component_id` SMALLINT UNSIGNED,
    `modifiedDate` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `missingDependencies` bool NOT NULL,
    `warning` bool NOT NULL,
    `createdDate` timestamp NULL,
    `deliveredDate` timestamp NULL,
    `autoCreated` bool NOT NULL,
    `consolidatedGroup` bool NOT NULL,
    `newArtifact` bool NOT NULL,
    `ccdApproved` bool NOT NULL,
    `bugOrTR` bool NOT NULL,
    CONSTRAINT `deliverygroup_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`),
    CONSTRAINT `deliverygroup_2_drop` FOREIGN KEY (`drop_id`) REFERENCES `cireports_drop` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_deliverytopackagerevmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `packageRevision_id` integer UNSIGNED NOT NULL,
    `team` varchar(500) NOT NULL DEFAULT "No Team Data",
    `kgb_test` varchar(20) NULL,
    `testReport` longtext NULL,
    `kgb_snapshot_report` BOOLEAN NOT NULL DEFAULT 0,
    `newArtifact` BOOLEAN NOT NULL DEFAULT 0,
    `services` varchar(500) NOT NULL DEFAULT "No Services Data",
    UNIQUE (`deliveryGroup_id`, `packageRevision_id`),
    CONSTRAINT `deliverytopackagerevmapping_2_deliverygroup` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`),
    CONSTRAINT `deliverytopackagerevmapping_2_packagerevision` FOREIGN KEY (`packageRevision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_deliverygroupcomment` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `comment` longtext NOT NULL,
    `date` datetime,
    CONSTRAINT `deliverygroupcomment_2_deliverygroup` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `cireports_jiraissue` (
    `id` INT(10) UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `jiraNumber` varchar(20) NOT NULL,
    `issueType` varchar(30) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_jiratypeexclusion` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `jiraType` varchar(30) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `cireports_jiralabel` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `type` varchar(30) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_jiraprojectexception` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `projectName` varchar(45) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `cireports_jiradeliverygroupmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `jiraIssue_id` INT(10) UNSIGNED NOT NULL,
    CONSTRAINT `jiradeliverygroupmap_2_deliverygroup` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`),
    CONSTRAINT `jiradeliverygroupmap_2_jiraissue` FOREIGN KEY (`jiraIssue_id`) REFERENCES `cireports_jiraissue` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_labeltojiraissuemap` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `jiraIssue_id` INT(10) UNSIGNED NOT NULL,
    `jiraLabel_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `labeltojiraissuemap_2_jiraissue` FOREIGN KEY (`jiraIssue_id`) REFERENCES `cireports_jiraissue` (`id`),
    CONSTRAINT `labeltojiraissuemap_2_jiralabel` FOREIGN KEY (`jiraLabel_id`) REFERENCES `cireports_jiralabel` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_packagenameexempt` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

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

CREATE TABLE `cireports_isotodeliverygroupmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `iso_id` INT(10) UNSIGNED NOT NULL,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    `deliveryGroup_status` varchar(20) NOT NULL,
    `modifiedDate` timestamp NOT NULL
) ENGINE=InnoDB;

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

CREATE TABLE `cireports_deliverygroupsubscription` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL,
    `deliveryGroup_id` integer UNSIGNED NOT NULL,
    UNIQUE (`user_id`, `deliveryGroup_id`),
    CONSTRAINT `deliverygroup_subscription` FOREIGN KEY (`deliveryGroup_id`) REFERENCES `cireports_deliverygroup` (`id`)
) ENGINE=InnoDB;

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

CREATE TABLE `cireports_autodeliverteam` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `team_id` smallint UNSIGNED,
    CONSTRAINT `autodeliver_2_component` FOREIGN KEY (`team_id`) REFERENCES `cireports_component` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_dropmediadeploymapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dropMediaArtifactMap_id` integer UNSIGNED NOT NULL,
    `product_id` integer UNSIGNED NOT NULL,
    UNIQUE INDEX mediatoproductmap(dropMediaArtifactMap_id, product_id),
    CONSTRAINT `dropmediaartifactmap_2_drop` FOREIGN KEY (`dropMediaArtifactMap_id`) REFERENCES `cireports_dropmediaartifactmapping` (`id`),
    CONSTRAINT `dropmediaartifactmap_2_product` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `cireports_productsetversiondeploymapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mainMediaArtifactVersion_id` INT(10) UNSIGNED NOT NULL,
    `mediaArtifactVersion_id` INT(10) UNSIGNED NOT NULL,
    `productSetVersion_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `main_deploymap_2_isobuild` FOREIGN KEY (`mainMediaArtifactVersion_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `deploymap_2_isobuild` FOREIGN KEY (`mediaArtifactVersion_id`) REFERENCES `cireports_isobuild` (`id`),
    CONSTRAINT `deploymap_2_productsetver` FOREIGN KEY (`productSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`)
) ENGINE=InnoDB
;

-- -------------------- --
-- CLOUD NATIVE PRODUCT --
-- -------------------- --
-- First stack
CREATE TABLE `cireports_cnimage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_name` varchar(100) NOT NULL UNIQUE,
    `image_product_number` varchar(20) NULL,
    `repo_name` varchar(100) NULL
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

CREATE TABLE `cireports_cnproducttype` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_type_name` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproduct` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_set_id` integer UNSIGNED NOT NULL,
    `product_name` varchar(100) NOT NULL UNIQUE,
    `product_type_id` integer UNSIGNED NOT NULL DEFAULT 1,
    `repo_name` varchar(100) NULL,
    `published_link` varchar(500) NULL,
    CONSTRAINT `cnproductset_2_cnproduct` FOREIGN KEY (`product_set_id`) REFERENCES `cireports_cnproductset` (`id`),
    CONSTRAINT `cnproducttype_2_cnproduct` FOREIGN KEY (`product_type_id`) REFERENCES `cireports_cnproducttype` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproductsetversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_set_version` varchar(20) NOT NULL,
    `status` varchar(500) NOT NULL,
    `overall_status_id` SMALLINT UNSIGNED,
    `drop_version` varchar(20) NOT NULL,
    `active` bool NOT NULL DEFAULT TRUE,
    CONSTRAINT `cnproductsetversion_2_states` FOREIGN KEY (`overall_status_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnproductrevision` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `version` varchar(20) NOT NULL,
    `gerrit_repo_sha` varchar(100) NULL,
    `product_set_version_id` integer UNSIGNED NOT NULL,
    `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    `size` BIGINT(1) UNSIGNED NULL,
    `dev_link` varchar(500) NULL,
    `values_file_version` varchar(20) NULL,
    `values_file_name` varchar(100) NULL,
    `verified` bool NOT NULL DEFAULT FALSE,
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

CREATE TABLE `cireports_cnconfidenceleveltype` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `confidenceLevelTypeName` varchar(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `cireports_requiredcnconfidencelevel` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `confidence_level_name` varchar(100) NOT NULL UNIQUE,
    `confidenceLevelType_id` integer UNSIGNED,
    `required` bool NOT NULL DEFAULT TRUE,
    `include_baseline` bool NOT NULL DEFAULT FALSE,
    `requireBuildLogId` bool NOT NULL DEFAULT FALSE,
    CONSTRAINT `requiredcnconfidencelevel_2_cnconfidenceleveltype` FOREIGN KEY (`confidenceLevelType_id`) REFERENCES `cireports_cnconfidenceleveltype` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_requiredramapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `team_inventory_ra_name` varchar(100) NOT NULL UNIQUE,
    `component_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `requiredramapping_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndrop` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `cnProductSet_id` integer UNSIGNED NOT NULL,
    `active_date` DATETIME NOT NULL,
    `reopen`  BOOLEAN NOT NULL DEFAULT 0,
    `designbase_id` smallint UNSIGNED,
    CONSTRAINT `cnDrop_2_cnProductSet` FOREIGN KEY (`cnProductSet_id`) REFERENCES `cireports_cnproductset` (`id`),
    CONSTRAINT `cnDrop_2_cnDrop` FOREIGN KEY (`designbase_id`) REFERENCES `cireports_cndrop` (`id`),
    UNIQUE INDEX dropCNProductSet (name, cnProductSet_id)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndeliverygroup` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cndrop_id` SMALLINT UNSIGNED NOT NULL,
    `cnProductSetVersion_id` INT(10) UNSIGNED,
    `cnProductSetVersionSet` bool NOT NULL,
    `queued` bool NOT NULL,
    `delivered` bool NOT NULL,
    `obsoleted` bool NOT NULL,
    `deleted` bool NOT NULL,
    `creator` varchar(100),
    `teamEmail` varchar(100) NULL,
    `component_id` SMALLINT UNSIGNED,
    `modifiedDate` timestamp NULL,
    `createdDate` timestamp NULL,
    `deliveredDate` timestamp NULL,
    `obsoletedDate` timestamp NULL,
    `deletedDate` timestamp NULL,
    `missingDependencies` bool NOT NULL,
    `bugOrTR` bool NOT NULL,
    CONSTRAINT `cndeliverygroup_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`),
    CONSTRAINT `cndeliverygroup_2_cndrop` FOREIGN KEY (`cndrop_id`) REFERENCES `cireports_cndrop` (`id`),
    CONSTRAINT `cndeliverygroup_2_cnproductsetversion` FOREIGN KEY (`cnProductSetVersion_id`) REFERENCES `cireports_cnproductsetversion` (`id`)
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
    `state_id` smallint UNSIGNED NULL,
    `revert_change_id` varchar(255) NULL,
    CONSTRAINT `cndgtocnimagetocngerritmap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtocnimagetocngerritmap_2_cnimage` FOREIGN KEY (`cnImage_id`) REFERENCES `cireports_cnimage` (`id`),
    CONSTRAINT `cndgtocnimagetocngerritmap_2_cngerrit` FOREIGN KEY (`cnGerrit_id`) REFERENCES `cireports_cngerrit` (`id`),
    CONSTRAINT `cndgtocnimagetocngerritmap_2_states` FOREIGN KEY (`state_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndgtocnproducttocngerritmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `cnProduct_id` integer UNSIGNED NOT NULL,
    `cnGerrit_id` integer UNSIGNED NULL,
    `state_id` smallint UNSIGNED NULL,
    `revert_change_id` varchar(255) NULL,
    CONSTRAINT `cndgtocnproducttocngerritmap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtocnproducttocngerritmap_2_cnProduct` FOREIGN KEY (`cnProduct_id`) REFERENCES `cireports_cnproduct` (`id`),
    CONSTRAINT `cndgtocnproducttocngerritmap_2_cngerrit` FOREIGN KEY (`cnGerrit_id`) REFERENCES `cireports_cngerrit` (`id`),
    CONSTRAINT `cndgtocnproducttocngerritmap_2_states` FOREIGN KEY (`state_id`) REFERENCES `cireports_states` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_cndgtocnpipelinetocngerritmap` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    `cnPipeline_id` integer UNSIGNED NOT NULL,
    `cnGerrit_id` integer UNSIGNED NULL,
    `state_id` smallint UNSIGNED NULL,
    `revert_change_id` varchar(255) NULL,
    CONSTRAINT `cndgtocnpipelinetocngerritmap_2_cndeliverygroup` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`),
    CONSTRAINT `cndgtocnpipelinetocngerritmap_2_cnPipeline` FOREIGN KEY (`cnPipeline_id`) REFERENCES `cireports_cnpipeline` (`id`),
    CONSTRAINT `cndgtocnpipelinetocngerritmap_2_cngerrit` FOREIGN KEY (`cnGerrit_id`) REFERENCES `cireports_cngerrit` (`id`),
    CONSTRAINT `cndgtocnpipelinetocngerritmap_2_states` FOREIGN KEY (`state_id`) REFERENCES `cireports_states` (`id`)
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

CREATE TABLE `cireports_cndeliverygroupsubscription` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_id` integer NOT NULL,
    `cnDeliveryGroup_id` integer UNSIGNED NOT NULL,
    UNIQUE (`user_id`, `cnDeliveryGroup_id`),
    CONSTRAINT `cndeliverygroup_subscription` FOREIGN KEY (`cnDeliveryGroup_id`) REFERENCES `cireports_cndeliverygroup` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `cireports_test` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `test_id` integer UNSIGNED NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_cnbuildlog` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop` varchar(50) NOT NULL,
    `testPhase` varchar(50) NULL,
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

CREATE TABLE `cireports_versionsupportmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifactId` varchar(150) NULL,
    `version` varchar(15) NULL,
    `feature` varchar(100) NULL
) ENGINE=InnoDB;

CREATE TABLE `cireports_jiramigrationproject` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `projectKeyName` varchar(15) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- --------------------- --
-- CIREPORTS SECTION END --
-- --------------------- --

-- ----------------- --
-- DMT SECTION START --
-- ----------------- --
CREATE TABLE `dmt_sed` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateInserted` datetime NOT NULL,
    `user` varchar(10) NOT NULL,
    `version` varchar(10) NOT NULL UNIQUE,
    `jiraNumber` varchar(20) NOT NULL,
    `sed` longtext,
    `linkText` varchar(15) NULL,
    `link` longtext,
    `iso_id` INT(10) UNSIGNED NULL,
    CONSTRAINT `isobuild_2_sed` FOREIGN KEY (`iso_id`) REFERENCES `cireports_isobuild` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_server` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NULL,
    `hostname` varchar(30) NOT NULL,
    `domain_name` varchar(100) NOT NULL,
    `dns_serverA` varchar(30) NOT NULL,
    `dns_serverB` varchar(30) NOT NULL,
    `hardware_type` varchar(20) NOT NULL,
    `hostnameIdentifier` char(50) not null default "1",
    UNIQUE INDEX hostnameIdentity (hostname, hostnameIdentifier)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_managementserver` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `SSH_Host_RSA_Key` varchar(450) NOT NULL,
    `description` longtext NOT NULL,
    `server_id` integer unsigned NOT NULL,
    `product_id` integer UNSIGNED NOT NULL default "1",
    CONSTRAINT `managementserver_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`),
    CONSTRAINT `product_2_managementserver` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;
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
CREATE TABLE `dmt_deploymentstatustypes` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `status` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `dmt_clusterlayout` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `description` longtext NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `dmt_enmdeploymenttype` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(40) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `dmt_ipversion` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(15) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `dmt_cluster` (
    `id` smallint unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `description` longtext NOT NULL,
    `tipc_address` integer UNSIGNED NOT NULL UNIQUE,
    `dhcp_lifetime` datetime not null default "1970-01-01 00:00:00",
    `group_id` int(11) NULL,
    `management_server_id` smallint unsigned NOT NULL,
    `compact_audit_logger` BOOLEAN NULL DEFAULT NULL,
    `mac_lowest` varchar(18) NOT NULL,
    `mac_highest` varchar(18) NOT NULL,
    `layout_id` SMALLINT UNSIGNED NOT NULL,
    `component_id` SMALLINT UNSIGNED NULL,
    `enmDeploymentType_id` SMALLINT UNSIGNED NULL,
    `ipVersion_id` SMALLINT UNSIGNED,
    CONSTRAINT `cluster_2_managementserver` FOREIGN KEY (`management_server_id`) REFERENCES `dmt_managementserver` (`id`),
    CONSTRAINT `cluster_2_clusterlayout` FOREIGN KEY (`layout_id`) REFERENCES `dmt_clusterlayout` (`id`),
    CONSTRAINT `cluster_2_component` FOREIGN KEY (`component_id`) REFERENCES `cireports_component` (`id`),
    CONSTRAINT `cluster_2_enmdeploymenttype` FOREIGN KEY (`enmDeploymentType_id`) REFERENCES `dmt_enmdeploymenttype` (`id`),
    CONSTRAINT `cluster_2_ipversion` FOREIGN KEY (`ipVersion_id`) REFERENCES `dmt_ipversion` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_deploymentstatus` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `status_id` SMALLINT UNSIGNED NOT NULL,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `status_changed` datetime NOT NULL default CURRENT_TIMESTAMP,
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
CREATE TABLE `dmt_networkinterface` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mac_address` varchar(18) NOT NULL,
    `interface` varchar(5) NOT NULL default "eth0",
    `server_id` integer unsigned NOT NULL,
    `nicIdentifier` char(50) not null default "1",
    UNIQUE INDEX nicIdentity (mac_address, nicIdentifier),
    CONSTRAINT `networkinterface_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_ipaddress` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `address` char(39),
    `bitmask` varchar(4) NULL,
    `ipv6_address` char(60),
    `ipv6_bitmask` varchar(4) NULL,
    `ipv6_gateway` char(39) NULL,
    `gateway_address` varchar(20) NULL,
    `interface` varchar(5),
    `netmask` char(15),
    `nic_id` integer unsigned NULL,
    `ipType` varchar(50) NULL,
    `ipv6UniqueIdentifier` char(50) not null default "1",
    `ipv4UniqueIdentifier` char(50) not null default "1",
    `override` bool NOT NULL DEFAULT 0,
    CONSTRAINT `ipaddress_2_networkinterface` FOREIGN KEY (`nic_id`) REFERENCES `dmt_networkinterface` (`id`)
) ENGINE=InnoDB
;
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
) ENGINE=InnoDB
;
CREATE TABLE `dmt_clusterserver` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `node_type` varchar(50) NOT NULL,
    `server_id` integer unsigned NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    `active` bool NOT NULL DEFAULT 1,
    CONSTRAINT `clusterserver_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`),
    CONSTRAINT `clusterserver_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_ilo` (
    `id` integer unsigned AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ipMapIloAddress_id` integer UNSIGNED NOT NULL,
    `server_id` integer unsigned NOT NULL UNIQUE,
    `username` varchar(10),
    `password` varchar(50),
    CONSTRAINT `iloAddress_2_ip` FOREIGN KEY (`ipMapIloAddress_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ilo_2_server` FOREIGN KEY (`server_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_apptemplate` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `desc` longtext
) ENGINE=InnoDB
;
CREATE TABLE `dmt_apphost` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `template_id` smallint UNSIGNED NOT NULL,
    `name` varchar(30) NOT NULL,
    `hostname` varchar(30) NOT NULL,
    `type` varchar(20) NOT NULL,
    CONSTRAINT `apphost_2_apptemplate` FOREIGN KEY (`template_id`) REFERENCES `dmt_apptemplate` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_appipaddress` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `value` varchar(30) NOT NULL,
    `mode` varchar(20) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `dmt_apphostipmap` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `apphost_id` smallint UNSIGNED NOT NULL,
    `ip_addr_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `apphostipmap_2_apphost` FOREIGN KEY (`apphost_id`) REFERENCES `dmt_apphost` (`id`),
    CONSTRAINT `apphostipmap_2_ipaddress` FOREIGN KEY (`ip_addr_id`) REFERENCES `dmt_appipaddress` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_kgbappinstance` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `template_id` smallint UNSIGNED NOT NULL,
    `aut_id` integer UNSIGNED NOT NULL,
    `state` varchar(20) NOT NULL,
    `comment` longtext,
    `vappid` varchar(100) NOT NULL,
    CONSTRAINT `kgbappinstance_2_apptemplate` FOREIGN KEY (`template_id`) REFERENCES `dmt_apptemplate` (`id`),
    CONSTRAINT `kgbappinstance_2_cireports_packagerevision` FOREIGN KEY (`aut_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_databaselocation` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `versantStandAlone` varchar(3) NOT NULL,
    `mysqlStandAlone` varchar(3) NOT NULL,
    `postgresStandAlone` varchar(3) NOT NULL,
    `cluster_id` smallint UNSIGNED,
    CONSTRAINT `dataBaseLocation_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_virtualimageitems` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE,
    `type` VARCHAR(50) NOT NULL,
    `layout` VARCHAR(50),
    `active` bool NOT NULL DEFAULT 1
) ENGINE=InnoDB
;
CREATE TABLE `dmt_virtualimage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `node_list` varchar(50) NOT NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `virtualmachine_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    UNIQUE INDEX virtualimageCluster (name, cluster_id)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_virtualimageipinfo` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
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
CREATE TABLE `dmt_clustermulticast` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
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
    `ipMapDefaultAddress_id` integer UNSIGNED NOT NULL,
    `ipMapMessagingGroupAddress_id` integer UNSIGNED NOT NULL,
    `ipMapUdpMcastAddress_id` integer UNSIGNED NOT NULL,
    `udp_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `ipMapMpingMcastAddress_id` integer UNSIGNED NOT NULL,
    `default_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `mping_mcast_port` integer UNSIGNED NOT NULL UNIQUE,
    `messaging_group_port` integer UNSIGNED NOT NULL UNIQUE,
    `public_port_base` integer UNSIGNED NOT NULL,
    `service_cluster_id` integer NOT NULL,
    CONSTRAINT `mulicast_2_serviceCluster` FOREIGN KEY (`service_cluster_id`) REFERENCES `dmt_servicescluster` (`id`),
    CONSTRAINT `defaultAddress_2_ip` FOREIGN KEY (`ipMapDefaultAddress_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `messagingAddress_2_ip` FOREIGN KEY (`ipMapMessagingGroupAddress_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `udpAddress_2_ip` FOREIGN KEY (`ipMapUdpMcastAddress_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `mpingAddress_2_ip` FOREIGN KEY (`ipMapMpingMcastAddress_id`) REFERENCES `dmt_ipaddress` (`id`)
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
    `hostname` varchar(30) NULL,
    `service_group_id` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `serviceGroupInstance_2_ServiceGroup` FOREIGN KEY (`service_group_id`) REFERENCES `dmt_servicegroup` (`id`),
    CONSTRAINT `servicegroupinstance_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_internalservicegroupinstance` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `service_group_id` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `internalserviceGroupInstance_2_ServiceGroup` FOREIGN KEY (`service_group_id`) REFERENCES `dmt_servicegroup` (`id`),
    CONSTRAINT `internalservicegroupinstance_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_internalipaddress` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_veritascluster` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ipMapCSG_id` integer UNSIGNED NOT NULL,
    `csgNic` varchar(10) NOT NULL,
    `ipMapGCO_id` integer UNSIGNED NOT NULL,
    `gcoNic` varchar(10) NOT NULL,
    `lltLink1` varchar(10) NOT NULL,
    `lltLink2` varchar(10) NOT NULL,
    `lltLinkLowPri1` varchar(10) NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `veritasCluster_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `veritasclsCSG_2_ip` FOREIGN KEY (`ipMapCSG_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `veritasclsGCO_2_ip` FOREIGN KEY (`ipMapGCO_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_clusterqueue` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `dateInserted` datetime,
    `clusterGroup` varchar(50)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_credentials` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `username` varchar(10) NOT NULL,
    `password` varchar(50) NOT NULL,
    `credentialType` char(20),
    `loginScope` varchar(20)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_nasserver` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `server_id` integer  UNSIGNED NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    `sfs_node1_hostname` varchar(45) NULL,
    `sfs_node2_hostname` varchar(45) NULL,
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
    `name` varchar(30) NULL,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `vnxType` varchar(100) NOT NULL default "vnx1",
    `domain_name` varchar(100) NOT NULL,
    `serial_number` varchar(18) NULL UNIQUE,
    `credentials_id` integer UNSIGNED NOT NULL,
    `sanAdminPassword` varchar(100) NULL,
    `sanServicePassword` varchar(100) NULL,
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
CREATE TABLE `dmt_enclosure` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hostname` varchar(30) NOT NULL UNIQUE,
    `domain_name` varchar(100) NOT NULL,
    `name` varchar(32) NOT NULL,
    `rackName` varchar(32) NOT NULL,
    `vc_domain_name` varchar(100) NOT NULL,
    `credentials_id` integer UNSIGNED NOT NULL,
    `vc_credentials_id` integer UNSIGNED NULL,
    `sanSw_credentials_id` integer UNSIGNED NULL,
    `uplink_A_port1` varchar(30) NOT NULL,
    `uplink_A_port2` varchar(30) NOT NULL,
    `uplink_B_port1` varchar(30) NOT NULL,
    `uplink_B_port2` varchar(30) NOT NULL,
    `san_sw_bay_1` varchar(2),
    `san_sw_bay_2` varchar(2),
    `vc_module_bay_1` varchar(2),
    `vc_module_bay_2` varchar(2),
    CONSTRAINT `enclosure_2_credentials` FOREIGN KEY (`credentials_id`) REFERENCES `dmt_credentials` (`id`),
    CONSTRAINT `vcenclosure_2_credentials` FOREIGN KEY (`vc_credentials_id`) REFERENCES `dmt_credentials` (`id`),
    CONSTRAINT `sanSwenclosure_2_credentials` FOREIGN KEY (`sanSw_credentials_id`) REFERENCES `dmt_credentials` (`id`)
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
CREATE TABLE `dmt_bladehardwaredetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `mac_address_id` integer UNSIGNED NOT NULL,
    `serial_number` varchar(18) NOT NULL UNIQUE,
    `profile_name` varchar(100) NOT NULL,
    `enclosure_id` integer UNSIGNED NOT NULL,
    `vlan_tag` integer UNSIGNED NULL,
    CONSTRAINT `bladehardwaredetails_2_mac_address` FOREIGN KEY (`mac_address_id`) REFERENCES `dmt_networkinterface` (`id`),
    CONSTRAINT `bladehardwaredetails_2_enclosure` FOREIGN KEY (`enclosure_id`) REFERENCES `dmt_enclosure` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_rackhardwaredetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `clusterserver_id` integer unsigned NOT NULL,
    `bootdisk_uuid` varchar(32) NOT NULL UNIQUE,
    `serial_number` varchar(18) NOT NULL UNIQUE,
     CONSTRAINT `rackhardwaredetails_2_clusterserver` FOREIGN KEY (`clusterserver_id`) REFERENCES `dmt_clusterserver` (`id`)
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
CREATE TABLE `dmt_nasstoragedetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `sanPoolName` varchar(30) NOT NULL,
    `sanPoolId` varchar(10) NOT NULL,
    `sanRaidGroup` integer UNSIGNED NULL,
    `poolFS1` varchar(20) NULL,
    `fileSystem1` varchar(20) NULL,
    `poolFS2` varchar(20) NULL,
    `fileSystem2` varchar(20) NULL,
    `poolFS3` varchar(20) NULL,
    `fileSystem3` varchar(20) NULL,
    `nasType` varchar(32) NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `nasNdmpPassword` varchar(100) NULL,
    `nasServerPrefix` varchar(50) NULL,
    `fcSwitches`  BOOLEAN NULL DEFAULT NULL,
    `nasEthernetPorts` varchar(30) NOT NULL DEFAULT "0,2",
    `sanPoolDiskCount` integer UNSIGNED NOT NULL DEFAULT 15,
    CONSTRAINT `nasstoragedetails_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_producttoservertypemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `product_id` integer UNSIGNED NOT NULL,
    `serverType` varchar(50) NOT NULL,
    CONSTRAINT `product_2_servertype` FOREIGN KEY (`product_id`) REFERENCES `cireports_product` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_ossrcclustertotorclustermapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `torCluster_id` smallint UNSIGNED NOT NULL,
    `ossCluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `ossrc_2_tor` FOREIGN KEY (`torcluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `tor_2_ossrc` FOREIGN KEY (`ossCluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_ssodetails` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `ldapDomain` varchar(100),
    `ldapPassword` varchar(100),
    `opendjAdminPassword` varchar(100),
    `openidmAdminPassword` varchar(100),
    `openidmMysqlPassword` varchar(100),
    `securityAdminPassword` varchar(100),
    `hqDatabasePassword` varchar(100),
    `ossFsServer` varchar(100),
    `citrixFarm` varchar(100) NOT NULL default "MASTERSERVICE",
    CONSTRAINT `ssodetails_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_installgroup` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `installGroup` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `dmt_clustertoinstallgroupmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL UNIQUE,
    `group_id` smallint UNSIGNED NOT NULL,
    `status_id` smallint UNSIGNED NOT NULL,
    UNIQUE INDEX grouptoclustermap (cluster_id, group_id),
    CONSTRAINT `cluster_2_installgroup` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `group_2_installgroup` FOREIGN KEY (`group_id`) REFERENCES `dmt_installgroup` (`id`),
    CONSTRAINT `depstatus_2_installgroup` FOREIGN KEY (`status_id`) REFERENCES `dmt_deploymentstatus` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_deploymentdatabaseprovider` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL UNIQUE,
    `dpsPersistenceProvider` varchar(50) NOT NULL default "versant",
    UNIQUE INDEX providertoclustermap (cluster_id, dpsPersistenceProvider),
    CONSTRAINT `cluster_2_databaseprovider` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;

CREATE TABLE `dmt_vlanipmapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `vlanTag` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `vlan_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_internalvlanipmapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `vlanTag` integer NOT NULL,
    `ipMap_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `internalvlan_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_internalipaddress` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_vlandetails` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `services_subnet` varchar(18) NOT NULL,
    `services_gateway` char(15) NOT NULL,
    `services_ipv6_gateway` char(39) NULL,
    `services_ipv6_subnet` varchar(42) NULL,
    `storage_subnet` varchar(18) NOT NULL,
    `storage_gateway_id` integer UNSIGNED NULL,
    `backup_subnet` varchar(18) NOT NULL,
    `jgroups_subnet` varchar(18) NOT NULL,
    `internal_subnet` varchar(18) NOT NULL,
    `internal_ipv6_subnet` varchar(42) NULL,
    `storage_vlan` integer NULL,
    `backup_vlan` integer NULL,
    `jgroups_vlan` integer NULL,
    `internal_vlan` integer NULL,
    `services_vlan` integer NULL,
    `management_vlan` integer NULL,
    `litp_management` varchar(18) NOT NULL default 'services',
    `hbAVlan` integer NULL,
    `hbBVlan` integer NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `cluster_2_vlanhbtag` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `storage_gateway_2_ip` FOREIGN KEY (`storage_gateway_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_clustertodasnasmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `dasNasServer_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `clustertodasnasmapping_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `clustertodasnasmapping_2_dasNasServer` FOREIGN KEY (`dasNasServer_id`) REFERENCES `dmt_server` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_iprangeitem` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ip_range_item` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `dmt_iprange` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ip_range_item_id` integer UNSIGNED NOT NULL,
    `start_ip` char(60) NOT NULL UNIQUE,
    `end_ip` char(60) NOT NULL UNIQUE,
    `gateway` char(60) NULL,
    `bitmask` varchar (2) NULL,
    CONSTRAINT `rangeItem_2_rangeIp` FOREIGN KEY (`ip_range_item_id`) REFERENCES `dmt_iprangeitem` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_servicegrouptypes` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `group_type` varchar(50) NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `dmt_servicegroupunit` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `service_unit` varchar(50) NOT NULL UNIQUE,
    `group_type_id` smallint UNSIGNED  NOT NULL,
    CONSTRAINT `servicegroupdata_2_servicegrouptypes` FOREIGN KEY (`group_type_id`) REFERENCES `dmt_servicegrouptypes` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_jbossclusterservicegroup` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;
CREATE TABLE `dmt_sedmaster` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `identifer` varchar(20) NOT NULL UNIQUE,
    `sedmaster_id` smallint UNSIGNED ,
    `sedmaster_virtual_id` smallint UNSIGNED ,
    `dateupdated` datetime ,
    `seduser` varchar(10) ,
    CONSTRAINT `sedmaster_to_sed` FOREIGN KEY (`sedmaster_id`) REFERENCES `dmt_sed` (`id`),
    CONSTRAINT `sedmaster_virtual_to_sed` FOREIGN KEY (`sedmaster_virtual_id`) REFERENCES `dmt_sed` (`id`)
) ENGINE=InnoDB
;
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
    `jgroups` varchar(50) NOT NULL default "ENM_jgroups",
    `jgroupsA` varchar(50) NOT NULL default "ENM_jgroups_A",
    `jgroupsB` varchar(50) NOT NULL default "ENM_jgroups_B",
    `internalA` varchar(50) NOT NULL default "ENM_internal_A",
    `internalB` varchar(50) NOT NULL default "ENM_internal_B",
    `heartbeat1` varchar(50) NOT NULL default "ENM_heartbeat1",
    `heartbeat2` varchar(50) NOT NULL default "ENM_heartbeat2",
    `heartbeat1A` varchar(50) NOT NULL default "ENM_heartbeat1_A",
    `heartbeat2B` varchar(50) NOT NULL default "ENM_heartbeat2_B",
    `vlanDetails_id` integer NOT NULL,
    CONSTRAINT `virtualconnectnetworks_2_vlanDetails` FOREIGN KEY (`vlanDetails_id`) REFERENCES `dmt_vlandetails` (`id`)
) ENGINE=InnoDB
;
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
    `hostname` longtext NULL,
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
    `opendj_address2_id` integer UNSIGNED NULL,
    `jms_address_id` integer UNSIGNED,
    `eSearch_address_id` integer UNSIGNED,
    `neo4j_address1_id` integer UNSIGNED NULL,
    `neo4j_address2_id` integer UNSIGNED NULL,
    `neo4j_address3_id` integer UNSIGNED NULL,
    `gossipRouter_address1_id` integer UNSIGNED NULL,
    `gossipRouter_address2_id` integer UNSIGNED NULL,
    `eshistory_address_id` integer UNSIGNED NULL,
    `cluster_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `postgres_2_ip` FOREIGN KEY (`postgres_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `versant_2_ip` FOREIGN KEY (`versant_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `mysql_2_ip` FOREIGN KEY (`mysql_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `opendj_2_ip` FOREIGN KEY (`opendj_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `opendj2_2_ip` FOREIGN KEY (`opendj_address2_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `jms_2_ip` FOREIGN KEY (`jms_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `eSearch_2_ip` FOREIGN KEY (`eSearch_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `neo4j_1_ip` FOREIGN KEY (`neo4j_address1_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `neo4j_2_ip` FOREIGN KEY (`neo4j_address2_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `neo4j_3_ip` FOREIGN KEY (`neo4j_address3_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `gossipRouter_1_ip` FOREIGN KEY (`gossipRouter_address1_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `gossipRouter_2_ip` FOREIGN KEY (`gossipRouter_address2_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `eshistory_2_ip` FOREIGN KEY (`eshistory_address_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `databasevips_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `dmt_deploypackageexemptionlist` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `packageName` varchar(250) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_deploymentbaseline` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `createdAt` datetime,
    `updatedAt` datetime,
    `clusterName` varchar(100) NOT NULL,
    `clusterID` varchar(100) NOT NULL,
    `osDetails` varchar(100) NOT NULL,
    `litpVersion` varchar(100) NOT NULL,
    `mediaArtifact` varchar(100) NOT NULL,
    `fromISO` varchar(100) NULL,
    `upgradePerformancePercent` varchar(5) NULL,
    `patches` longtext NULL,
    `dropName` varchar(100) NOT NULL,
    `fromISODrop` varchar(100) NOT NULL,
    `groupName` varchar(100) NOT NULL,
    `sedVersion` varchar(100) NOT NULL,
    `deploymentTemplates` varchar(100) NOT NULL,
    `tafVersion` varchar(100) NOT NULL,
    `descriptionDetails` varchar(100) NULL,
    `masterBaseline` bool NOT NULL DEFAULT 0,
    `success` bool NOT NULL DEFAULT 0,
    `productset_id` varchar(50) NOT NULL,
    `deliveryGroup` varchar(3000) NULL,
    `status` varchar(50) NOT NULL,
    `rfaStagingResult` varchar(2000) NULL,
    `rfaResult` varchar(2000) NULL,
    `teAllureLogUrl` varchar(200) NULL,
    `upgradeAvailabilityResult` varchar(2000) NULL,
    `availability` varchar(50) NULL,
    `buildURL` varchar(200) NULL,
    `deploytime` varchar(50) NULL,
    `comment` longtext NULL,
    `slot` int NOT NULL,
    `installType` varchar(100) NULL,
    `upgradeTestingStatus` varchar(100) NULL,
    `rfaPercent` varchar(5) NULL,
    `shortLoopURL` varchar(100) NULL
) ENGINE=InnoDB
;

CREATE TABLE `dmt_virtualautobuildlogclusters` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_deployscriptmapping` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reference` varchar(20) NOT NULL UNIQUE,
    `version` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_ipmiversionmapping` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reference` varchar(20) NOT NULL UNIQUE,
    `version` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_redfishversionmapping` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `reference` varchar(20) NOT NULL UNIQUE,
    `version` varchar(20) NOT NULL UNIQUE
) ENGINE=InnoDB
;

CREATE TABLE `dmt_deploymenttestcase` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `testcase_description` varchar(255) NOT NULL,
    `testcase` longtext NOT NULL,
    `enabled` bool NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_maptestresultstodeployment` (
    `id` INT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `testcase_description` varchar(255) NOT NULL,
    `testcase` longtext NOT NULL,
    `result` bool NOT NULL,
    `testcaseOutput` longtext,
    `testDate` datetime NOT NULL,
    CONSTRAINT `cluster_id_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_testgroup` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `defaultGroup` bool DEFAULT 0,
    `testGroup` varchar(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_maptestgrouptodeployment` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` SMALLINT UNSIGNED NOT NULL,
    `group_id` SMALLINT UNSIGNED NOT NULL,
    CONSTRAINT `cluster_id_ref_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `group_id_2_testgroup` FOREIGN KEY (`group_id`) REFERENCES `dmt_testgroup` (`id`)
) ENGINE=InnoDB;

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

CREATE TABLE `dmt_autovmservicednsiprange` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ipv4AddressStart` char(15),
    `ipv4AddressEnd` char(15),
    `ipv6AddressStart` char(39),
    `ipv6AddressEnd` char(39),
    `ipTypeId_id` smallint unsigned NOT NULL,
    `cluster_id` smallint unsigned NOT NULL,
    CONSTRAINT `ipType_id_2_vmserviceiprangeitem` FOREIGN KEY (`ipTypeId_id`) REFERENCES `dmt_vmserviceiprangeitem` (`id`),
    CONSTRAINT `autovmservicednsiprange_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_lvsroutervip` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `pm_internal_id` integer UNSIGNED NOT NULL,
    `pm_external_id` integer UNSIGNED NOT NULL,
    `fm_internal_id` integer UNSIGNED NOT NULL,
    `fm_external_id` integer UNSIGNED NOT NULL,
    `fm_internal_ipv6_id` integer UNSIGNED,
    `fm_external_ipv6_id` integer UNSIGNED,
    `cm_internal_id` integer UNSIGNED NOT NULL,
    `cm_external_id` integer UNSIGNED NOT NULL,
    `cm_internal_ipv6_id` integer UNSIGNED NULL,
    `cm_external_ipv6_id` integer UNSIGNED,
    `svc_pm_storage_id` integer UNSIGNED NOT NULL,
    `svc_fm_storage_id` integer UNSIGNED NOT NULL,
    `svc_cm_storage_id` integer UNSIGNED NOT NULL,
    `svc_storage_internal_id` integer UNSIGNED NOT NULL,
    `svc_storage_id` integer UNSIGNED NOT NULL,
    `scp_scp_internal_id` integer UNSIGNED NULL,
    `scp_scp_external_id` integer UNSIGNED NULL,
    `scp_scp_internal_ipv6_id` integer UNSIGNED NULL,
    `scp_scp_external_ipv6_id` integer UNSIGNED NULL,
    `scp_scp_storage_id` integer UNSIGNED NULL,
    `scp_storage_internal_id` integer UNSIGNED NULL,
    `scp_storage_id` integer UNSIGNED NULL,
    `evt_storage_internal_id` integer UNSIGNED NULL,
    `evt_storage_id` integer UNSIGNED NULL,
    `str_str_if` varchar(100) NULL,
    `str_internal_id` integer UNSIGNED NULL,
    `str_str_internal_2_id` integer UNSIGNED NULL,
    `str_str_internal_3_id` integer UNSIGNED NULL,
    `str_external_id` integer UNSIGNED NULL,
    `str_str_external_2_id` integer UNSIGNED NULL,
    `str_str_external_3_id` integer UNSIGNED NULL,
    `str_str_internal_ipv6_id` integer UNSIGNED NULL,
    `str_str_internal_ipv6_2_id` integer UNSIGNED NULL,
    `str_str_internal_ipv6_3_id` integer UNSIGNED NULL,
    `str_external_ipv6_id` integer UNSIGNED NULL,
    `str_str_external_ipv6_2_id` integer UNSIGNED NULL,
    `str_str_external_ipv6_3_id` integer UNSIGNED NULL,
    `str_str_storage_id` integer UNSIGNED NULL,
    `str_storage_internal_id` integer UNSIGNED NULL,
    `str_storage_id` integer UNSIGNED NULL,
    `esn_str_if` varchar(100) NULL,
    `esn_str_internal_id` integer UNSIGNED NULL,
    `esn_str_external_id` integer UNSIGNED NULL,
    `esn_str_internal_ipv6_id` integer UNSIGNED NULL,
    `esn_str_external_ipv6_id` integer UNSIGNED NULL,
    `esn_storage_internal_id` integer UNSIGNED NULL,
    `esn_str_storage_id` integer UNSIGNED NULL,
    `ebs_storage_internal_id` integer UNSIGNED NULL,
    `ebs_storage_id` integer UNSIGNED NULL,
    `asr_storage_id` integer UNSIGNED NULL,
    `asr_asr_storage_id` integer UNSIGNED NULL,
    `asr_asr_external_ipv6_id` integer UNSIGNED NULL,
    `asr_asr_internal_id` integer UNSIGNED NULL,
    `asr_asr_external_id` integer UNSIGNED NULL,
    `asr_storage_internal_id` integer UNSIGNED NULL,
    `eba_storage_internal_id` integer UNSIGNED NULL,
    `eba_storage_id` integer UNSIGNED NULL,
    `msossfm_external_id` integer UNSIGNED NOT NULL,
    `msossfm_external_ipv6_id` integer UNSIGNED NOT NULL,
    `msossfm_internal_id` integer UNSIGNED NOT NULL,
    `msossfm_internal_ipv6_id` integer UNSIGNED NOT NULL,


    CONSTRAINT `lvsroutervip_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `pminternal_2_ip` FOREIGN KEY (`pm_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `pmexternal_2_ip` FOREIGN KEY (`pm_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `fminternal_2_ip` FOREIGN KEY (`fm_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `fmexternal_2_ip` FOREIGN KEY (`fm_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `fminternalipv6_2_ipv6` FOREIGN KEY (`fm_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `fmexternalipv6_2_ipv6` FOREIGN KEY (`fm_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `cminternal_2_ip` FOREIGN KEY (`cm_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `cmexternal_2_ip` FOREIGN KEY (`cm_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `cminternalipv6_2_ipv6` FOREIGN KEY (`cm_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `cmexternalipv6_2_ipv6` FOREIGN KEY (`cm_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `svcpmstg_2_ip` FOREIGN KEY (`svc_pm_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `svcfmstg_2_ip` FOREIGN KEY (`svc_fm_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `svccmstg_2_ip` FOREIGN KEY (`svc_cm_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `svcstgint_2_ip` FOREIGN KEY (`svc_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `svcstg_2_ip` FOREIGN KEY (`svc_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scpscpinternal_2_ip` FOREIGN KEY (`scp_scp_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scpscpexternal_2_ip` FOREIGN KEY (`scp_scp_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scpscpinternalipv6_2_ipv6` FOREIGN KEY (`scp_scp_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scpscpexternalipv6_2_ipv6` FOREIGN KEY (`scp_scp_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scpscpstg_2_ip` FOREIGN KEY (`scp_scp_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scpstgint_2_ip` FOREIGN KEY (`scp_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `scpstg_2_ip` FOREIGN KEY (`scp_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `evtstgint_2_ip` FOREIGN KEY (`evt_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `evtstg_2_ip` FOREIGN KEY (`evt_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strinternal_2_ip` FOREIGN KEY (`str_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrinternal_2_2_ip` FOREIGN KEY (`str_str_internal_2_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrinternal_3_2_ip` FOREIGN KEY (`str_str_internal_3_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strexternal_2_ip` FOREIGN KEY (`str_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrexternal_2_2_ip` FOREIGN KEY (`str_str_external_2_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrexternal_3_2_ip` FOREIGN KEY (`str_str_external_3_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrintipv6_2_ipv6` FOREIGN KEY (`str_str_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrintipv6_2_2_ipv6` FOREIGN KEY (`str_str_internal_ipv6_2_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrintipv6_3_2_ipv6` FOREIGN KEY (`str_str_internal_ipv6_3_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strexternalipv6_2_ipv6` FOREIGN KEY (`str_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrexternalipv6_2_2_ipv6` FOREIGN KEY (`str_str_external_ipv6_2_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrexternalipv6_3_2_ipv6` FOREIGN KEY (`str_str_external_ipv6_3_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstrstg_2_ip` FOREIGN KEY (`str_str_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstgint_2_ip` FOREIGN KEY (`str_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `strstg_2_ip` FOREIGN KEY (`str_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `esnstrinternal_2_ip` FOREIGN KEY (`esn_str_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `esnstrexternal_2_ip` FOREIGN KEY (`esn_str_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `esnstrintipv6_2_ipv6` FOREIGN KEY (`esn_str_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `esnstrexternalipv6_2_ipv6` FOREIGN KEY (`esn_str_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `esnstgint_2_ip` FOREIGN KEY (`esn_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `esnstrstg_2_ip` FOREIGN KEY (`esn_str_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebsstgint_2_ip` FOREIGN KEY (`ebs_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebsstg_2_ip` FOREIGN KEY (`ebs_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `asrstgint_2_ip` FOREIGN KEY (`asr_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `asrasrexternal_2_ip` FOREIGN KEY (`asr_asr_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `asrasrinternal_2_ip` FOREIGN KEY (`asr_asr_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `asrasrexternalipv6_2_ipv6` FOREIGN KEY (`asr_asr_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `asrstg_2_ip` FOREIGN KEY (`asr_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `asrasrstg_2_ip` FOREIGN KEY (`asr_asr_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebastgint_2_ip` FOREIGN KEY (`eba_storage_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebastg_2_ip` FOREIGN KEY (`eba_storage_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `msossfmexternal_2_ip` FOREIGN KEY (`msossfm_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `msossfmexternalipv6_2_ipv6` FOREIGN KEY (`msossfm_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `msossfminternal_2_ip` FOREIGN KEY (`msossfm_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `msossfminternalipv6_2_ipv6` FOREIGN KEY (`msossfm_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`)

) ENGINE=InnoDB;

CREATE TABLE `dmt_lvsroutervipextended` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `eba_external_id` integer UNSIGNED NULL,
    `eba_external_ipv6_id` integer UNSIGNED NULL,
    `eba_internal_id` integer UNSIGNED NULL,
    `eba_internal_ipv6_id` integer UNSIGNED NULL,
    `svc_pm_ipv6_id` int UNSIGNED NULL,
    `oran_internal_id` int UNSIGNED NULL,
    `oran_internal_ipv6_id` int UNSIGNED NULL,
    `oran_external_id` int UNSIGNED NULL,
    `oran_external_ipv6_id` int UNSIGNED NULL,
    CONSTRAINT `lvsroutervipextended_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`),
    CONSTRAINT `ebaexternal_2_ip` FOREIGN KEY (`eba_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebaexternalipv6_2_ip` FOREIGN KEY (`eba_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebainternal_2_ip` FOREIGN KEY (`eba_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `ebainternalipv6_2_ip` FOREIGN KEY (`eba_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `svcpmipv6_2_ipv6` FOREIGN KEY (`svc_pm_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `oraninternal_2_ip` FOREIGN KEY (`oran_internal_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `oraninternalipv6_2_ipv6` FOREIGN KEY (`oran_internal_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `oranexternal_2_ip` FOREIGN KEY (`oran_external_id`) REFERENCES `dmt_ipaddress` (`id`),
    CONSTRAINT `oranexternalipv6_2_ipv6` FOREIGN KEY (`oran_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`)
) ENGINE=InnoDB;


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
    `iso_build_id` INT(10) UNSIGNED NOT NULL,
    `active` bool NOT NULL,
    CONSTRAINT `utilityversion_2_isobuild` FOREIGN KEY (`utility_version_id`) REFERENCES `dmt_deploymentutilitiesversion` (`id`),
    CONSTRAINT `isobuild_2_utilityversion` FOREIGN KEY (`iso_build_id`) REFERENCES `cireports_isobuild` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_deploymentutilstoproductsetversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `utility_version_id` integer UNSIGNED NOT NULL,
    `productSetVersion_id` integer UNSIGNED NOT NULL,
    `active` bool NOT NULL,
    CONSTRAINT `utilityversion_2_deploymentutils` FOREIGN KEY (`utility_version_id`) REFERENCES `dmt_deploymentutilitiesversion` (`id`),
    CONSTRAINT `productSetVersion_2_deploymentutils` FOREIGN KEY (`productSetVersion_id`) REFERENCES `cireports_productsetversion` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_consolidatedtoconstituentmap` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cosolidated` varchar(50) NOT NULL,
    `constituent` varchar(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `dmt_deploymentdhcpjumpserverdetails` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `server_type` varchar(50) NOT NULL,
    `server_user` varchar(50) NOT NULL,
    `server_password` varchar(50) NOT NULL,
    `ecn_ip` char(39),
    `edn_ip` char(39),
    `youlab_ip` char(39),
    `gtec_edn_ip` char(39),
    `gtec_youlab_ip` char(39)
) ENGINE=InnoDB;

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
    `capacity_type` varchar(12) NULL DEFAULT 'test',
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
    `update_type` varchar(20) NULL,
    `iprange_type` varchar(20) NULL DEFAULT 'dns',

    CONSTRAINT `ddtodeploymentmap_2_dd` FOREIGN KEY (`deployment_description_id`) REFERENCES `dmt_deploymentdescription` (`id`),
    CONSTRAINT `ddtodeploymentmap_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

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

CREATE TABLE `dmt_packagerevisionservicemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer UNSIGNED NOT NULL,
    `service_id` smallint UNSIGNED NOT NULL,
    CONSTRAINT `packagerevisionservicemapping_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `packagerevisionservicemapping_2_vmservicename` FOREIGN KEY (`service_id`) REFERENCES `dmt_vmservicename` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `dmt_mediaartifactservicescanned` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `media_artifact_version` varchar(15) NOT NULL UNIQUE,
    `scanned_date` datetime
) ENGINE=InnoDB;

CREATE TABLE `dmt_clusteradditionalinformation` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `cluster_id` smallint UNSIGNED NOT NULL,
    `ddp_hostname` varchar(50) NULL,
    `cron` varchar(50) NULL,
    `port` varchar(4) NULL,
    CONSTRAINT `additionalinformation_2_cluster` FOREIGN KEY (`cluster_id`) REFERENCES `dmt_cluster` (`id`)
) ENGINE=InnoDB;

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

CREATE TABLE `dmt_itamwebhookendpoint` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `endpoint` varchar(200) NULL UNIQUE
) ENGINE=InnoDB;

-- --------------- --
-- DMT SECTION END --
-- --------------- --

-- ----------------- --
-- AVS SECTION START --
-- ----------------- --
CREATE TABLE `avs_epic` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL UNIQUE,
    `title` longtext NOT NULL
) ENGINE=InnoDB
;
CREATE TABLE `avs_userstory` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(20) NOT NULL,
    `title` longtext NOT NULL,
    `epic_id` integer NOT NULL,
    `version` integer NOT NULL,
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
    `tcId` varchar(35) NOT NULL,
    `title` longtext NOT NULL,
    `desc` longtext NOT NULL,
    `type` varchar(4) NOT NULL,
    `component_id` integer NOT NULL,
    `priority` varchar(20) NOT NULL,
    `groups` longtext,
    `pre` longtext,
    `vusers` varchar(50),
    `context` varchar(200),
    `revision` integer NOT NULL,
    `archived` integer NOT NULL,
    CONSTRAINT testcase_2_component FOREIGN KEY (`component_id`) REFERENCES `avs_component` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `avs_testcaseuserstorymapping` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `user_story_id` integer NOT NULL,
    `test_case_id` integer NOT NULL,
    CONSTRAINT testcaseuserstorymapping_2_userstory FOREIGN KEY (`user_story_id`) REFERENCES `avs_userstory` (`id`),
    CONSTRAINT testcaseuserstorymapping_2_testcase FOREIGN KEY (`test_case_id`) REFERENCES `avs_testcase` (`id`)
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
-- --------------- --
-- AVS SECTION END --
-- --------------- --

-- ----------------- --
-- FEM SECTION START --
-- ----------------- --
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
    `duration` bigint UNSIGNED ,
    CONSTRAINT `jobres_2_fem` FOREIGN KEY (`job_id`) REFERENCES `fem_job` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `fem_cachetable` (
    `url` varchar(255) NOT NULL PRIMARY KEY,
    `data` longtext NOT NULL,
    `inserted` datetime
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
CREATE TABLE `fem_femurls` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `url` varchar(255) NOT NULL
) ENGINE=InnoDB
;
-- --------------- --
-- FEM SECTION END --
-- --------------- --

-- ----------------- --
-- VIS SECTION START --
-- ----------------- --
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
    `description` longtext
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
-- --------------- --
-- VIS SECTION END --
-- --------------- --

-- ------------------------ --
-- EXCELLENCE SECTION START --
-- ------------------------ --
CREATE TABLE `excellence_organisation` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL UNIQUE,
    `description` longtext,
    `owner` varchar(10) NOT NULL,
    `parent_id` integer UNSIGNED,
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
    `questionnaire_Name` varchar(30) NOT NULL,
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
CREATE TABLE `excellence_discussionitems` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `comment` longtext
) ENGINE=InnoDB
;
CREATE TABLE `excellence_questionanswerresponsemapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `question_id` integer UNSIGNED NOT NULL,
    `answer_id` integer UNSIGNED NOT NULL,
    `comment_id` integer UNSIGNED NOT NULL,
    `response_id` integer UNSIGNED NOT NULL,
    CONSTRAINT `questionanswerresponsemapping_2_question` FOREIGN KEY (`question_id`) REFERENCES `excellence_question` (`id`),
    CONSTRAINT `questionanswerresponsemapping_2_answer` FOREIGN KEY (`answer_id`) REFERENCES `excellence_answer` (`id`),
    CONSTRAINT `questionanswerresponsemapping_2_comment` FOREIGN KEY (`comment_id`) REFERENCES `excellence_discussionitems` (`id`),
    CONSTRAINT `questionanswerresponsemapping_2_response` FOREIGN KEY (`response_id`) REFERENCES `excellence_response` (`id`)
) ENGINE=InnoDB
;
-- ---------------------- --
-- EXCELLENCE SECTION END --
-- ---------------------- --

-- ---------------------- --
-- DEPMODEL SECTION START --
-- ---------------------- --
CREATE TABLE `depmodel_dependencytype` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `desc` longtext
) ENGINE=InnoDB
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
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_javapackage` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_name` varchar(255) NOT NULL,
    `provided_by_id` smallint unsigned,
    CONSTRAINT `provided_by_id_2_package` FOREIGN KEY (`provided_by_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_staticdependency` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_revision_id` integer unsigned NOT NULL,
    `java_package_id` integer NOT NULL,
    CONSTRAINT `package_revision_id_2_packagerevision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`),
    CONSTRAINT `java_package_id_2-javapackage` FOREIGN KEY (`java_package_id`) REFERENCES `depmodel_javapackage` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_artifact` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(100) NOT NULL UNIQUE,
    `package_id` smallint UNSIGNED,
    CONSTRAINT `artifact_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_artifactversion` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifact_id` integer NOT NULL,
    `groupname` varchar(100) NOT NULL ,
    `version` varchar(100) NOT NULL,
    `m2type` varchar(30),
    `bomcreatedartifact` bool DEFAULT 0 NOT NULL,
    `bomversion` varchar(30),
    `reponame` varchar(255),
    UNIQUE (artifact_id, groupname,version,m2type,bomcreatedartifact,bomversion,reponame),
    CONSTRAINT `artifactversion_2_artifact` FOREIGN KEY (`artifact_id`) REFERENCES `depmodel_artifact` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_artverstopackagetoisobuildmap` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifact_version_id` integer NOT NULL,
    `package_id` smallint UNSIGNED,
    `isobuild_version_id` INT(10) UNSIGNED,
    UNIQUE (artifact_version_id,package_id,isobuild_version_id),
    CONSTRAINT `artifactversion_2_package` FOREIGN KEY (`artifact_version_id`) REFERENCES `depmodel_artifactversion` (`id`),
    CONSTRAINT `package_2_artifactversion` FOREIGN KEY (`package_id`) REFERENCES `cireports_package` (`id`),
    CONSTRAINT `isobuildversion_2_artifactversion` FOREIGN KEY (`isobuild_version_id`) REFERENCES `cireports_isobuild` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_mapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `artifact_main_version_id` integer NOT NULL,
    `artifact_dep_version_id` integer NOT NULL,
    `scope` varchar(60) NOT NULL,
    `build` bool NOT NULL DEFAULT FALSE,
    UNIQUE (artifact_main_version_id, artifact_dep_version_id,scope),
    CONSTRAINT `main_2_artifactversion` FOREIGN KEY (`artifact_main_version_id`) REFERENCES `depmodel_artifactversion` (`id`),
    CONSTRAINT `dep_2_artifactversion` FOREIGN KEY (`artifact_dep_version_id`) REFERENCES `depmodel_artifactversion` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_packagedependencies` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `package_id` integer UNSIGNED NOT NULL UNIQUE,
    `deppackage` varchar(1000),
    `all` longtext,
    `jar_dependencies` varchar(5000),
    `third_party_dependencies` varchar(5000),
   CONSTRAINT `packagedep_2_package` FOREIGN KEY (`package_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB
;
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
    `package_revision` varchar(255) NOT NULL,
    UNIQUE (anomalyartifact_version_id,package_revision),
    CONSTRAINT `anomalyartifactversion_2_packagerevision` FOREIGN KEY (`anomalyartifact_version_id`) REFERENCES `depmodel_anomalyartifactversion` (`id`)
) ENGINE=InnoDB
;
CREATE TABLE `depmodel_dependencypluginartifact` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(200) NOT NULL UNIQUE,
    `property` varchar(200) NOT NULL
) ENGINE=InnoDB
;
-- -------------------- --
-- DEPMODEL SECTION END --
-- -------------------- --

-- ----------------- --
-- CPI SECTION START --
-- ----------------- --
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
) ENGINE=InnoDB;

CREATE TABLE `cpi_cpiidentity` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `drop_id` smallint UNSIGNED NOT NULL,
    `cpiDrop` varchar(50) NOT NULL,
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
) ENGINE=InnoDB;

CREATE TABLE `cpi_cpidocument` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `section_id` integer UNSIGNED NOT NULL,
    `docName` varchar(255) NOT NULL,
    `author` varchar(255) NOT NULL,
    `language` varchar(5) NOT NULL,
    `docNumber` varchar(50) NOT NULL,
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
) ENGINE=InnoDB;
-- --------------- --
-- CPI SECTION END --
-- --------------- --

-- --------------------- --
-- METRICS SECTION START --
-- --------------------- --
CREATE TABLE `metrics_eventtype` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `eventTypeName` varchar(50) NOT NULL,
    `eventTypeDb` varchar(50) NOT NULL,
    `description` longtext
) ENGINE=InnoDB;

CREATE TABLE `metrics_sppserver` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE,
    `url` varchar(255) NOT NULL UNIQUE
) ENGINE=InnoDB;
-- ------------------- --
-- METRICS SECTION END --
-- ------------------- --

-- ------------------- --
-- CLOUD SECTION START --
-- ------------------- --
CREATE TABLE `cloud_gateway` (
    `id` smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `cloud_gatewaytosppmapping` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `gateway_id` smallint UNSIGNED NOT NULL,
    `spp_id` smallint UNSIGNED NOT NULL,
    `date` datetime NOT NULL,
    UNIQUE INDEX gatewaySpp (`gateway_id`, `spp_id`),
    CONSTRAINT `gatewaytosppmapping_2_gateway` FOREIGN KEY (`gateway_id`) REFERENCES `cloud_gateway` (`id`),
    CONSTRAINT `gatewaytosppmapping_2_spp` FOREIGN KEY (`spp_id`) REFERENCES `metrics_sppserver` (`id`)
) ENGINE=InnoDB;
-- ----------------- --
-- CLOUD SECTION END --
-- ----------------- --

-- ------------------- --
-- FASTCOMMIT SECTION START --
-- ------------------- --
CREATE TABLE `fastcommit_dockerimage` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE `fastcommit_dockerimageversion` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_id` integer UNSIGNED NOT NULL,
    `version`  varchar(25) NOT NULL,
    UNIQUE INDEX imageVersion (`image_id`, `version`),
    CONSTRAINT `dockerimageversion_2_image` FOREIGN KEY (`image_id`) REFERENCES `fastcommit_dockerimage` (`id`)
) ENGINE=InnoDB;

CREATE TABLE `fastcommit_dockerimageversioncontents` (
    `id` integer UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `image_version_id` integer UNSIGNED NOT NULL,
    `package_revision_id` integer UNSIGNED NOT NULL,
    UNIQUE INDEX imagePackage (`image_version_id`, `package_revision_id`),
    CONSTRAINT `dockerimageversioncontents_2_image_version` FOREIGN KEY (`image_version_id`) REFERENCES `fastcommit_dockerimageversion` (`id`),
    CONSTRAINT `dockerimageversioncontents_2_package_revision` FOREIGN KEY (`package_revision_id`) REFERENCES `cireports_packagerevision` (`id`)
) ENGINE=InnoDB;
-- ----------------- --
-- FASTCOMMIT SECTION END --
-- ----------------- --

-- ----------------- --
-- FOSS SECTION START --
-- ----------------- --
CREATE TABLE `foss_gerritrepo` (
    `id` SMALLINT UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `repo_name` VARCHAR(200) NOT NULL UNIQUE,
    `repo_revision` VARCHAR(40) NULL,
    `owner` VARCHAR(50) NOT NULL,
    `owner_email` varchar(100) NOT NULL,
    `scan` BOOL NOT NULL DEFAULT "1"
) ENGINE = InnoDB;

CREATE TABLE `foss_scanversion` (
    `id` INTEGER UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `start_time` datetime not null default "1970-01-01 00:00:00",
    `end_time` datetime NULL,
    `status` BOOL NOT NULL DEFAULT "0",
    `audit_report_url` VARCHAR(200) NULL
) ENGINE = InnoDB;

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
-- ----------------- --
-- FOSS SECTION END --
-- ----------------- --

-- -------------------------------- --
-- EXTRA FOREIGN KEYS SECTION START --
-- -------------------------------- --
ALTER TABLE `cireports_release` ADD CONSTRAINT `release_2_mediaartifact` FOREIGN KEY (`masterArtifact_id`) REFERENCES `cireports_mediaartifact` (`id`);
ALTER TABLE `cireports_dropmediaartifactmapping` ADD CONSTRAINT `dropmediaartifactmapping_2_isobuildversion` FOREIGN KEY (`mediaArtifactVersion_id`) REFERENCES `cireports_isobuild`
 (`id`);
ALTER TABLE `cireports_productsetversioncontent` ADD CONSTRAINT `productsetvercont_2_isobuildversion` FOREIGN KEY (`mediaArtifactVersion_id`) REFERENCES `cireports_isobuild` (`id`);
ALTER TABLE `cireports_isobuild` ADD CONSTRAINT `iso_2_sed` FOREIGN KEY (`sed_build_id`) REFERENCES `dmt_sed` (`id`);
ALTER TABLE `cireports_packagerevision` ADD CONSTRAINT `packagerevision_2_teamrunningkgb` FOREIGN KEY (`team_running_kgb_id`) REFERENCES `cireports_component` (`id`);
-- ------------------------------ --
-- EXTRA FOREIGN KEYS SECTION END --
-- ------------------------------ --

ALTER TABLE `cireports_drop` ADD `stop_auto_delivery` bool DEFAULT false NULL;

ALTER TABLE `dmt_lvsroutervip` ADD COLUMN `ebs_str_external_ipv6_id` int UNSIGNED NULL AFTER `ebs_storage_id`;
ALTER TABLE `dmt_lvsroutervip` ADD CONSTRAINT `ebsstrexternalipv6_2_ipv6` FOREIGN KEY (`ebs_str_external_ipv6_id`) REFERENCES `dmt_ipaddress` (`id`);

ALTER TABLE dmt_clusteradditionalinformation ADD COLUMN `time` varchar(255) NULL AFTER port;
ALTER TABLE dmt_ssodetails ADD COLUMN `brsadm_password` varchar(100) AFTER citrixFarm;
