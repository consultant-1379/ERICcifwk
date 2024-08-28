#!/bin/bash -a
. $(dirname $0)/db.env
DATE=$(date "+%Y-%m-%d %T")

deliver() {
    prodrev=$1
    drop=$2
    obsol=$3
    rel=$4
    date=$5
    mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
INSERT INTO cireports_dropproductmapping (product_revision_id,drop_id,obsolete,released,date_created) VALUES
($prodrev,$drop,$obsol,$rel,"$(date "+%Y-%m-%d %T")");
EOF
}

promote() {
    prod="ERICdemotest_CXP1234567"
    level=$2
    state=$3
    maj=$4
    min=$5
    patch=$6
    mysql -u ${DBUSER} -p${DBPASS} ${DBNAME} <<EOF
UPDATE cireports_productrevision,cireports_product SET $level = "$state" WHERE
cireports_productrevision.product_id = cireports_product.id AND
cireports_product.name = "$prod" AND
cireports_productrevision.major = $maj AND
cireports_productrevision.minor = $min AND
cireports_productrevision.patch = $patch ;
EOF
}

deliver 34 3 0 1 ${DATE}
promote ERICsfwk_CXC9011234 compile not_started 1 0 1
promote ERICsfwk_CXC9011234 unit_test not_started 1 0 1
promote ERICsfwk_CXC9011234 integration_test not_started 1 0 1
promote ERICsfwk_CXC9011234 compile in_progress 1 0 1
sleep 15
promote ERICsfwk_CXC9011234 compile passed 1 0 1
sleep 1
promote ERICsfwk_CXC9011234 unit_test in_progress 1 0 1
sleep 15
promote ERICsfwk_CXC9011234 unit_test passed 1 0 1
sleep 1
promote ERICsfwk_CXC9011234 integration_test in_progress 1 0 1
sleep 20
promote ERICsfwk_CXC9011234 integration_test passed 1 0 1
