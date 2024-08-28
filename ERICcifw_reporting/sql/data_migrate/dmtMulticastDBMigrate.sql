DROP PROCEDURE IF EXISTS dmtMulticastMigrate;
DROP TABLE IF EXISTS dmt_multicast_orig;
-- Create a copy of the dmt_servicegroupinstance DB
CREATE TABLE dmt_multicast_orig LIKE dmt_multicast; 
INSERT dmt_multicast_orig SELECT * FROM dmt_multicast;

-- Update the dmt table with the new Column
ALTER TABLE dmt_multicast ADD COLUMN `ipMapMpingMcastAddress_id` integer UNSIGNED NOT NULL AFTER id; 
ALTER TABLE dmt_multicast ADD COLUMN `ipMapUdpMcastAddress_id` integer UNSIGNED NOT NULL AFTER id; 
ALTER TABLE dmt_multicast ADD COLUMN `ipMapMessagingGroupAddress_id` integer UNSIGNED NOT NULL AFTER id; 
ALTER TABLE dmt_multicast ADD COLUMN `ipMapDefaultAddress_id` integer UNSIGNED NOT NULL AFTER id; 

DELIMITER $$
CREATE PROCEDURE dmtMulticastMigrate()
    BEGIN
      DECLARE ipMapMpingAddress, ipMapUdpAddress,ipMapMessagingAddress,ipMapDefaultAddress char(39);
      DECLARE serviceClsId int(10);
      DECLARE done INT DEFAULT FALSE;
     
      -- declare cursor
      DECLARE cur1 CURSOR FOR SELECT mping_mcast_address, udp_mcast_address, messaging_group_address, default_address, service_cluster_id 
      FROM dmt_multicast_orig;
     
      -- declare handle 
      DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
     
      -- open cursor
      OPEN cur1;
     
      -- starts the loop
      the_loop: LOOP
     
        -- get the values of each column into our variables
        FETCH cur1 INTO ipMapMpingAddress, ipMapUdpAddress,ipMapMessagingAddress,ipMapDefaultAddress,serviceClsId;
        IF done THEN
          LEAVE the_loop;
        END IF;

        -- MPing Addresses
        SET @entry := ipMapMpingAddress;
        SET @list = (SELECT address FROM dmt_ipaddress WHERE address = @entry);

        IF @list IS NULL THEN
            INSERT INTO dmt_ipaddress (address,ipType)
            VALUES (ipMapMpingAddress,serviceClsId); 
            UPDATE dmt_ipaddress set ipType=concat('multicast_',ipType) where address=ipMapMpingAddress;
            -- Now update the ipMap_id with the id from the dmt_ipaddress table
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = ipMapMpingAddress);
            UPDATE dmt_multicast SET ipMapMpingMcastAddress_id = @id WHERE mping_mcast_address = ipMapMpingAddress; 
        END IF;

        -- UDP Addresses
        SET @entry := ipMapUdpAddress;
        SET @list = (SELECT address FROM dmt_ipaddress WHERE address = @entry);

        IF @list IS NULL THEN
            INSERT INTO dmt_ipaddress (address,ipType)
            VALUES (ipMapUdpAddress,serviceClsId); 
            UPDATE dmt_ipaddress set ipType=concat('multicast_',ipType) where address=ipMapUdpAddress;
            -- Now update the ipMap_id with the id from the dmt_ipaddress table
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = ipMapUdpAddress);
            UPDATE dmt_multicast SET ipMapUdpMcastAddress_id = @id WHERE udp_mcast_address = ipMapUdpAddress; 
        END IF;

        -- Messaging Addresses
        SET @entry := ipMapMessagingAddress;
        SET @list = (SELECT address FROM dmt_ipaddress WHERE address = @entry);

        IF @list IS NULL THEN
            INSERT INTO dmt_ipaddress (address,ipType)
            VALUES (ipMapMessagingAddress,serviceClsId); 
            UPDATE dmt_ipaddress set ipType=concat('multicast_',ipType) where address=ipMapMessagingAddress;
            -- Now update the ipMap_id with the id from the dmt_ipaddress table
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = ipMapMessagingAddress);
            UPDATE dmt_multicast SET ipMapMessagingGroupAddress_id = @id WHERE messaging_group_address = ipMapMessagingAddress; 
        END IF;

        -- Default Addresses
        SET @entry := ipMapDefaultAddress;
        SET @list = (SELECT address FROM dmt_ipaddress WHERE address = @entry);

        IF @list IS NULL THEN
            INSERT INTO dmt_ipaddress (address,ipType)
            VALUES (ipMapDefaultAddress,serviceClsId); 
            UPDATE dmt_ipaddress set ipType=concat('multicast_',ipType) where address=ipMapDefaultAddress;
            -- Now update the ipMap_id with the id from the dmt_ipaddress table
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = ipMapDefaultAddress);
            UPDATE dmt_multicast SET ipMapDefaultAddress_id = @id WHERE default_address = ipMapDefaultAddress; 
        END IF;
      END LOOP the_loop;
     
      CLOSE cur1;
END $$
Delimiter ;
call dmtMulticastMigrate();
-- Delete anything that wasnt given a value would not have a value as it is a duplicate already in the ipaddress table
DELETE FROM dmt_multicast WHERE ipMapMpingMcastAddress_id = 0;
DELETE FROM dmt_multicast WHERE ipMapUdpMcastAddress_id = 0;
DELETE FROM dmt_multicast WHERE ipMapMessagingGroupAddress_id = 0;
DELETE FROM dmt_multicast WHERE ipMapDefaultAddress_id = 0;
-- Drop the unwanted ip address table
ALTER TABLE dmt_multicast DROP mping_mcast_address;
ALTER TABLE dmt_multicast DROP udp_mcast_address;
ALTER TABLE dmt_multicast DROP messaging_group_address;
ALTER TABLE dmt_multicast DROP default_address;
-- Add the foreign key constraint
ALTER TABLE dmt_multicast ADD CONSTRAINT `defaultAddress_2_ip` FOREIGN KEY (`ipMapDefaultAddress_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_multicast ADD CONSTRAINT `messagingAddress_2_ip` FOREIGN KEY (`ipMapMessagingGroupAddress_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_multicast ADD CONSTRAINT `udpAddress_2_ip` FOREIGN KEY (`ipMapUdpMcastAddress_id`) REFERENCES `dmt_ipaddress` (`id`);
ALTER TABLE dmt_multicast ADD CONSTRAINT `mpingAddress_2_ip` FOREIGN KEY (`ipMapMpingMcastAddress_id`) REFERENCES `dmt_ipaddress` (`id`);
DROP TABLE IF EXISTS dmt_multicast_orig;
DROP PROCEDURE IF EXISTS dmtMulticastMigrate;
