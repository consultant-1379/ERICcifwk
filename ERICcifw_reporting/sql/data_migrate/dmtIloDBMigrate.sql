DROP PROCEDURE IF EXISTS dmtIloAddresMigrate;
DROP TABLE IF EXISTS dmt_ilo_orig;
-- Remove the http from the ip address in the dmt_ilo_orig
UPDATE dmt_ilo
SET ilo_address = REPLACE(ilo_address, 'https://', '');
UPDATE dmt_ilo
SET ilo_address = REPLACE(ilo_address, 'http://', '');
UPDATE dmt_ilo
SET ilo_address = REPLACE(ilo_address, 'http:', '');
UPDATE dmt_ilo
SET ilo_address = REPLACE(ilo_address, '/', '');
UPDATE dmt_ilo
SET ilo_address = REPLACE(ilo_address, 'drc2fram.htm', '');

-- Create a copy of the dmt_ilo DB
CREATE TABLE dmt_ilo_orig LIKE dmt_ilo; 
INSERT dmt_ilo_orig SELECT * FROM dmt_ilo;

-- Update the dmt table with the new Column
ALTER TABLE dmt_ilo ADD COLUMN `ipMapIloAddress_id` integer UNSIGNED NOT NULL AFTER id; 

DELIMITER $$
CREATE PROCEDURE dmtIloAddresMigrate()
    BEGIN
      DECLARE ipAddress char(39);
      DECLARE serverId int(10);
      DECLARE done INT DEFAULT FALSE;
     
      -- declare cursor
      DECLARE cur1 CURSOR FOR SELECT ilo_address,server_id
      FROM dmt_ilo_orig;
     
      -- declare handle 
      DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
     
      -- open cursor
      OPEN cur1;
     
      -- starts the loop
      the_loop: LOOP
     
        -- get the values of each column into our variables
        FETCH cur1 INTO ipAddress, serverId;
        IF done THEN
          LEAVE the_loop;
        END IF;
        
        SET @entry := ipAddress;
        SET @list = (SELECT address FROM dmt_ipaddress WHERE address = @entry);
        
        IF @list IS NULL THEN
            INSERT INTO dmt_ipaddress (address,ipType)
            VALUES (ipAddress,serverId);  
            UPDATE dmt_ipaddress set ipType=concat('ILO_',ipType) where address=ipAddress;
            -- Now update the ipMapIloAddress_id with the id from the dmt_ipaddress table
            -- First check for a duplicate entry
            SET @id = (SELECT id FROM dmt_ipaddress WHERE address = @entry);
            SET @idCheck = (SELECT id FROM dmt_ilo WHERE ipMapIloAddress_id = @id);
            IF @idCheck IS NULL THEN
                UPDATE dmt_ilo SET ipMapIloAddress_id = @id WHERE ilo_address = @entry AND server_id = serverId; 
            END IF;
        END IF;
     
      END LOOP the_loop;
     
      CLOSE cur1;
END $$
DELIMITER ;
call dmtIloAddresMigrate();
-- Delete anything that wasnt given a value, would not have a value as it is a duplicate already in the ipaddress table
DELETE FROM dmt_ilo WHERE ipMapIloAddress_id = 0;
-- Drop the unwanted ip address table
ALTER TABLE dmt_ilo DROP ilo_address;
-- Add the foreign key constraint
ALTER TABLE dmt_ilo ADD CONSTRAINT `iloAddress_2_ip` FOREIGN KEY (`ipMapIloAddress_id`) REFERENCES `dmt_ipaddress` (`id`);
DROP TABLE IF EXISTS dmt_ilo_orig;
DROP PROCEDURE IF EXISTS dmtIloAddresMigrate;
