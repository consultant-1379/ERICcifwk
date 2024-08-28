#!/bin/bash -a
. $(dirname $0)/db.env

mysqldump --user=${DBUSER} -p${DBPASS} --skip-triggers --compact --no-create-info cireports cireports_productrevision cireports_productarea | sed -e 's/cireports_productarea/cireports_solutionset/g' > import_data.sql

    mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
DROP TABLE IF EXISTS cireports_productarea;
DROP TABLE IF EXISTS cireports_productrevision;

CREATE TABLE cireports_solutionset (
    id integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    name varchar(50) NOT NULL
)
;

CREATE TABLE cireports_productrevision (
    id integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    product_id integer NOT NULL,
    major integer NOT NULL,
    minor integer NOT NULL,
    patch integer NOT NULL,
    ec integer NOT NULL,
    date_created datetime NOT NULL,
    solution_set_id integer NOT NULL,
    published datetime,
    compile varchar(20) NOT NULL,
    unit_test varchar(20) NOT NULL,
    integration_test varchar(20) NOT NULL,
    correction bool NOT NULL,
    artifact_ref varchar(100),
    m2groupId varchar(100),
    m2artifactId varchar(100),
    m2version varchar(100),
    m2type varchar(100),
    m2qualifier varchar(100),
    last_update datetime
)
;
ALTER TABLE cireports_productrevision ADD CONSTRAINT product_id FOREIGN KEY (product_id) REFERENCES cireports_product (id);
ALTER TABLE cireports_productrevision ADD CONSTRAINT solution_set_id FOREIGN KEY (solution_set_id) REFERENCES cireports_solutionset (id);

COMMIT;
EOF

mysql --no-defaults -v -v -v -v -v --user=${DBUSER} -p${DBPASS} ${DBNAME} < import_data.sql
