UPDATE dmt_virtualimageitems set layout="Bare Metal Image" WHERE type="lsb";
UPDATE dmt_virtualimageitems set layout="Bare Metal Image" WHERE type="httpd";
UPDATE dmt_virtualimageitems set layout="Virtual Machine" WHERE type LIKE "%boss";
