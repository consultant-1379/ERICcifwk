DROP PROCEDURE IF EXISTS dmtServiceUnitMigrate;
DROP TABLE IF EXISTS dmt_servicegroupinstance_orig;
-- Delete Unwanted IP Addresses that should be used
-- DELETE FROM dmt_servicegroupinstance WHERE Service_Instance_IP LIKE '10.0.%';
UPDATE dmt_servicegroupinstance SET Service_Instance_IP = replace(Service_Instance_IP, '10.0.0', '10.250.244'), bitmask = "22", gateway = "10.250.244.1" WHERE Service_Instance_IP LIKE '10.0.0%';
UPDATE dmt_servicegroupinstance SET Service_Instance_IP = replace(Service_Instance_IP, '10.0.1', '10.250.245'), bitmask = "22", gateway = "10.250.244.1" WHERE Service_Instance_IP LIKE '10.0.1%';
-- DELETE FROM dmt_servicegroupinstance WHERE Service_Instance_IP LIKE '10.0.%';
-- Create a copy of the dmt_servicegroupinstance DB
CREATE TABLE dmt_servicegroupinstance_orig LIKE dmt_servicegroupinstance; 
INSERT dmt_servicegroupinstance_orig SELECT * FROM dmt_servicegroupinstance;

-- Update the dmt table with the new Column
ALTER TABLE dmt_servicegroupinstance ADD COLUMN `ipMap_id` integer UNSIGNED NOT NULL AFTER service_group_id; 

DELIMITER $$
CREATE PROCEDURE dmtServiceUnitMigrate()
    BEGIN
      DECLARE ipAddress, ipGateway char(39);
      DECLARE ipBitmask, serviceGrpId int(10);
      DECLARE done INT DEFAULT FALSE;
     
      -- declare cursor
      DECLARE cur1 CURSOR FOR SELECT Service_Instance_IP, bitmask, gateway, service_group_id
      FROM dmt_servicegroupinstance_orig;
     
      -- declare handle 
      DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
     
      -- open cursor
      OPEN cur1;
     
      -- starts the loop
      the_loop: LOOP
     
        -- get the values of each column into our variables
        FETCH cur1 INTO ipAddress, ipBitmask, ipGateway, serviceGrpId;
        IF done THEN
          LEAVE the_loop;
        END IF;

        SET @entry := ipAddress;
        SET @list = (SELECT address FROM dmt_ipaddress WHERE address = @entry);

        IF @list IS NULL THEN
            INSERT INTO dmt_ipaddress (address,bitmask,gateway_address,ipType)
            VALUES (ipAddress, ipBitmask, ipGateway, serviceGrpId); 
            UPDATE dmt_ipaddress set ipType=concat('serviceUnit_',ipType) where address=ipAddress;
            -- Now update the ipMap_id with the id from the dmt_ipaddress table
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = ipAddress);
            UPDATE dmt_servicegroupinstance SET ipMap_id = @id WHERE Service_Instance_IP = ipAddress; 
        END IF;
         
      END LOOP the_loop;
     
      CLOSE cur1;
END $$
Delimiter ;
call dmtServiceUnitMigrate();
-- Delete anything that wasnt given a value would not have a value as it is a duplicate already in the ipaddress table
DELETE FROM dmt_servicegroupinstance WHERE ipMap_id = 0;
-- Drop the unwanted ip address table
ALTER TABLE dmt_servicegroupinstance DROP Service_Instance_IP;
ALTER TABLE dmt_servicegroupinstance DROP bitmask;
ALTER TABLE dmt_servicegroupinstance DROP gateway;
-- Add the foreign key constraint
ALTER TABLE dmt_servicegroupinstance ADD CONSTRAINT `servicegroupinstance_2_ip` FOREIGN KEY (`ipMap_id`) REFERENCES `dmt_ipaddress` (`id`);
DROP TABLE IF EXISTS dmt_servicegroupinstance_orig;
DROP PROCEDURE IF EXISTS dmtServiceUnitMigrate;
