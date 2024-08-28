#!/bin/bash -a
. $(dirname $0)/db.env
BASEDIR=$(cd $(dirname $0) ; pwd)
MGT="python $(dirname $(dirname $(dirname ${BASEDIR})))/django_proj/manage.py"

# Create Products
${MGT} cifwk_createproduct --product ERIC

ERICpmmedcore_CXP9030102    CXP9030102  eeicjon
ERICpmmedcom_CXP9030103     CXP9030103  eeicjon
ERICpmservice_CXP9030101    CXP9030101  eeicjon
ERICtopserv_CXP9030160  CXP9030160  eeicjon
ERICcpppmmed_CXP9030107     CXP9030107  eeicjon
ERICcomecimpmmed_CXP9030108     CXP9030108  eeicjon
