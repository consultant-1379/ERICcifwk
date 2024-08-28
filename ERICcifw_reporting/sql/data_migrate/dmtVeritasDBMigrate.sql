DROP PROCEDURE IF EXISTS dmtVeritasMigrate;
DROP TABLE IF EXISTS dmt_veritascluster_orig;
-- Delete Unwanted IP Addresses that should be used
-- DELETE FROM dmt_veritascluster WHERE CSG_IP LIKE '10.0.%';
-- DELETE FROM dmt_veritascluster WHERE CSG_IP LIKE '10.0.%';
UPDATE dmt_veritascluster SET CSG_IP = replace(CSG_IP, '10.0.127', '10.247.244'), CSG_Bitmask = "22" WHERE CSG_IP LIKE '10.0.127%';
UPDATE dmt_veritascluster SET GCO_IP = replace(GCO_IP, '10.0.127', '10.247.244'), GCO_Bitmask = "22" WHERE GCO_IP LIKE '10.0.127%';

-- Create a copy of the dmt_veritascluster DB
CREATE TABLE dmt_veritascluster_orig LIKE dmt_veritascluster; 
INSERT dmt_veritascluster_orig SELECT * FROM dmt_veritascluster;

-- Update the dmt table with the new Column
ALTER TABLE dmt_veritascluster ADD COLUMN `ipMapCSG_id` integer UNSIGNED NOT NULL AFTER id; 
ALTER TABLE dmt_veritascluster ADD COLUMN `ipMapGCO_id` integer UNSIGNED NOT NULL AFTER CSG_Nic; 

DELIMITER $$
CREATE PROCEDURE dmtVeritasMigrate()
    BEGIN
      DECLARE csgAddress, gcoAddress char(39);
      DECLARE csgBitmask, gcoBitmask, clusterId int(10);
      DECLARE done INT DEFAULT FALSE;
     
      -- declare cursor
      DECLARE cur1 CURSOR FOR SELECT CSG_IP, CSG_Bitmask, GCO_IP, GCO_Bitmask, cluster_id
      FROM dmt_veritascluster_orig;
     
      -- declare handle 
      DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
     
      -- open cursor
      OPEN cur1;
     
      -- starts the loop
      the_loop: LOOP
     
        -- get the values of each column into our variables
        FETCH cur1 INTO csgAddress, csgBitmask, gcoAddress, gcoBitmask, clusterId;
        IF done THEN
          LEAVE the_loop;
        END IF;

        SET @csgEntry := csgAddress;
        SET @csgList = (SELECT address FROM dmt_ipaddress WHERE address = @csgEntry);
        SET @gcoEntry := gcoAddress;
        SET @gcoList = (SELECT address FROM dmt_ipaddress WHERE address = @gcoEntry);

        IF @csgList IS NULL AND @gcoList IS NULL THEN
            INSERT INTO dmt_ipaddress (address,bitmask,ipType)
            VALUES (csgAddress,csgBitmask,clusterId);  
            UPDATE dmt_ipaddress set ipType=concat('veritas_',ipType) where address=csgAddress;
            --  Now update the ipMapCSG_id with the id from the dmt_ipaddress table
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = csgAddress);
            UPDATE dmt_veritascluster SET ipMapCSG_id = @id WHERE CSG_IP = csgAddress AND CSG_Bitmask = csgBitmask; 

            -- Repeate for the second instance
            INSERT INTO dmt_ipaddress (address,bitmask,ipType)
            VALUES (gcoAddress,gcoBitmask,clusterId);  
            UPDATE dmt_ipaddress set ipType=concat('veritas_',ipType) where address=gcoAddress;
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = gcoAddress);
            UPDATE dmt_veritascluster SET ipMapGCO_id = @id WHERE GCO_IP = gcoAddress AND GCO_Bitmask = gcoBitmask; 
        END IF;
         
      END LOOP the_loop;
     
      CLOSE cur1;
END $$
DELIMITER ;
call dmtVeritasMigrate();
-- Delete anything that wasnt given a value, would not have a value as it is a duplicate already in the ipaddress table
DELETE FROM dmt_veritascluster WHERE ipMapGCO_id = 0;
-- Drop the unwanted ip address table
ALTER TABLE dmt_veritascluster DROP CSG_IP;
ALTER TABLE dmt_veritascluster DROP CSG_Bitmask;
ALTER TABLE dmt_veritascluster DROP GCO_IP;
ALTER TABLE dmt_veritascluster DROP GCO_Bitmask;
-- Alter some of the MENU title to use camel case
ALTER TABLE dmt_veritascluster CHANGE CSG_Nic csgNic varchar(10) NOT NULL;
ALTER TABLE dmt_veritascluster CHANGE GCO_Nic gcoNic varchar(10) NOT NULL;
ALTER TABLE dmt_veritascluster CHANGE llt_link_1 lltLink1 varchar(10) NOT NULL;
ALTER TABLE dmt_veritascluster CHANGE llt_link_2 lltLink2 varchar(10) NOT NULL;
ALTER TABLE dmt_veritascluster CHANGE llt_link_low_pri_1 lltLinkLowPri1 varchar(10) NOT NULL;
-- Add the foreign key constraint
ALTER TABLE dmt_veritascluster ADD CONSTRAINT `veritasclsCSG_2_ip` FOREIGN KEY (`ipMapCSG_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_veritascluster ADD CONSTRAINT `veritasclsGCO_2_ip` FOREIGN KEY (`ipMapGCO_id`) REFERENCES `dmt_ipaddress` (`id`);
DROP TABLE IF EXISTS dmt_veritascluster_orig;
DROP PROCEDURE IF EXISTS dmtVeritasMigrate;
