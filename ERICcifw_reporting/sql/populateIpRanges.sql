-- Record of Private IP Ranges

-- 10.247.244.0/22 --> 10.247.244.1 to 10.247.247.254 (PDU-Priv)

-- Address:   10.247.244.0          00001010.11110111.111101 00.00000000
-- Netmask:   255.255.252.0 = 22    11111111.11111111.111111 00.00000000
-- Wildcard:  0.0.3.255             00000000.00000000.000000 11.11111111
-- Network:   10.247.244.0/22       00001010.11110111.111101 00.00000000 (Class A)
-- Broadcast: 10.247.247.255        00001010.11110111.111101 11.11111111
-- HostMin:   10.247.244.1          00001010.11110111.111101 00.00000001
-- HostMax:   10.247.247.254        00001010.11110111.111101 11.11111110
-- Hosts/Net: 1022                  (Private Internet)

-- 10.250.244.0/22 --> 10.250.244.1 to 10.250.247.254 (PDU-Priv-2)

-- Address:   10.250.244.0          00001010.11111010.111101 00.00000000
-- Netmask:   255.255.252.0 = 22    11111111.11111111.111111 00.00000000
-- Wildcard:  0.0.3.255             00000000.00000000.000000 11.11111111
-- Network:   10.250.244.0/22       00001010.11111010.111101 00.00000000 (Class A)
-- Broadcast: 10.250.247.255        00001010.11111010.111101 11.11111111
-- HostMin:   10.250.244.1          00001010.11111010.111101 00.00000001
-- HostMax:   10.250.247.254        00001010.11111010.111101 11.11111110
-- Hosts/Net: 1022                  (Private Internet)



-- internalVirtualJGroupMulticast  -->   PDU-Priv_virtualImageInternalJgroup
-- Used for the virtual images within the KVM deployment to auto assign ips to jgroups (Range 460 IP’s)
-- internalJGroupMulticast     -->   PDU-Priv_nodeInternalJgroup
-- Used to assign the Internal jgroup IP to a Node (Range 48 IP’s)

-- internalServiceUnit     -->   PDU-Priv-2_nodeInternal
-- Used to assign the Internal IP to a Node (Range 48 IP’s)
-- Added New               PDU-Priv-2_virtualImageInternal
-- Used for the virtual images within the KVM deployment to auto assign ips to internal ip’s (Range 460 IP’s)
-- sharedVeritasServiceUnit    -->   PDU-Priv_VeritasIP

UPDATE dmt_iprangeitem set ip_range_item='PDU-Priv_virtualImageInternalJgroup' WHERE ip_range_item='internalVirtualJGroupMulticast';
UPDATE dmt_iprangeitem set ip_range_item='PDU-Priv_nodeInternalJgroup' WHERE ip_range_item='internalJGroupMulticast';
UPDATE dmt_iprangeitem set ip_range_item='PDU-Priv-2_nodeInternal' WHERE ip_range_item='internalServiceUnit';
UPDATE dmt_iprangeitem set ip_range_item='PDU-Priv_VeritasIP' WHERE ip_range_item='sharedVeritasServiceUnit';
INSERT INTO dmt_iprangeitem (ip_range_item) VALUES ('PDU-Priv-2_virtualImageInternal');
INSERT INTO dmt_iprangeitem (ip_range_item) VALUES ('PDU-Priv-2_Free');
DELETE FROM dmt_iprange WHERE start_ip='228.0.0.3';
DELETE FROM dmt_iprange WHERE start_ip='229.0.0.3';
DELETE FROM dmt_iprange WHERE start_ip='230.0.0.3';
UPDATE dmt_iprange set start_ip='228.0.0.3',end_ip='228.0.10.254' WHERE ip_range_item_id='3';
DELETE FROM dmt_iprange WHERE start_ip='237.0.0.3';
DELETE FROM dmt_iprange WHERE start_ip='238.0.0.3';
UPDATE dmt_iprange set start_ip='237.0.0.3',end_ip='237.0.10.254' WHERE ip_range_item_id='2';
DELETE FROM dmt_iprange WHERE start_ip='234.0.0.3';
DELETE FROM dmt_iprange WHERE start_ip='236.0.0.3';
UPDATE dmt_iprange set start_ip='234.0.0.3',end_ip='234.0.10.254' WHERE ip_range_item_id='5';
DELETE FROM dmt_iprange WHERE start_ip='224.0.0.3';
DELETE FROM dmt_iprange WHERE start_ip='225.0.0.3';
DELETE FROM dmt_iprange WHERE start_ip='226.0.0.3';
UPDATE dmt_iprange set start_ip='224.0.0.3',end_ip='224.0.10.254' WHERE ip_range_item_id='4';
DELETE FROM dmt_iprange WHERE start_ip='10.247.244.2';
UPDATE dmt_iprange set start_ip='10.250.244.2',end_ip='10.250.245.254' WHERE ip_range_item_id='1';
UPDATE dmt_iprange set start_ip='10.247.246.51',end_ip='10.247.247.254' WHERE ip_range_item_id='9';
UPDATE dmt_iprange set start_ip='10.247.246.2',end_ip='10.247.246.50' WHERE ip_range_item_id='6';
UPDATE dmt_iprange set start_ip='10.250.246.51',end_ip='10.247.246.254' WHERE ip_range_item_id='8';
INSERT INTO dmt_iprange (ip_range_item_id,start_ip,end_ip,gateway,bitmask) VALUES ((SELECT id FROM dmt_iprangeitem WHERE ip_range_item="PDU-Priv-2_virtualImageInternal"), '10.247.246.51','10.247.247.254','10.247.244.1','22');

