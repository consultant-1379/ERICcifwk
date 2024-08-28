#!/bin/bash -a
. $(dirname $0)/db.env

    mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
DROP TABLE IF EXISTS cireports_shipment;
DROP TABLE IF EXISTS cireports_shipmentproductmapping;

CREATE TABLE cireports_drop (
    id integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    name varchar(50) NOT NULL,
    release_id integer NOT NULL,
    release_date datetime,
    designbase_id integer
)
;
ALTER TABLE cireports_drop ADD CONSTRAINT release_id FOREIGN KEY (release_id) REFERENCES cireports_release (id);
ALTER TABLE cireports_drop ADD CONSTRAINT designbase_id FOREIGN KEY (designbase_id) REFERENCES cireports_drop (id);
CREATE TABLE cireports_dropproductmapping (
    id integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    product_revision_id integer NOT NULL,
    drop_id integer NOT NULL,
    obsolete bool NOT NULL,
    released bool NOT NULL,
    date_created datetime NOT NULL
)
;
ALTER TABLE cireports_dropproductmapping ADD CONSTRAINT product_revision_id FOREIGN KEY (product_revision_id) REFERENCES cireports_productrevision (id);
ALTER TABLE cireports_dropproductmapping ADD CONSTRAINT drop_id FOREIGN KEY (drop_id) REFERENCES cireports_drop (id);
COMMIT;
EOF
