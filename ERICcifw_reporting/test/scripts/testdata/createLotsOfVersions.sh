#!/bin/bash

BD=$(dirname $0)

. ${BD}/db.env

mysql -u root cireports <<EOF
TRUNCATE TABLE cireports_productrevision;
TRUNCATE TABLE cireports_dropproductmapping;
EOF

for i in 1 2 3 4 5 ; do
	${BD}/createVersion.sh CXP9021400 1.0.1 platform 1.0.${i}.0 passed passed failed
done
${BD}/createVersion.sh CXP9021400 1.0.1 platform 1.0.6.0 passed passed passed
python /proj/lciadm100/cifwk/latest/django_proj/manage.py cifwk_deliver ERICcobbler_CXP9021400 1.0.6 1.0.1
for i in 1 2 3 ; do
${BD}/createVersion.sh CXP9021401 1.0.1 apps 1.0.${i}.0 passed passed passed
done

for i in 1 2 ; do
${BD}/createVersion.sh CXP9021402 1.0.1 apps 1.0.${i}.0 passed passed passed
done

for i in 1 2 3 4 5 6 7 8 ; do
${BD}/createVersion.sh CXP9021403 1.0.1 apps 1.0.${i}.0 passed passed passed
done

${BD}/createVersion.sh CXP9021404 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021405 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021406 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021407 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021408 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021409 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021410 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021411 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021412 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021413 1.0.1 apps 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021415 1.0.1 ui 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021416 1.0.1 ui 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021417 1.0.1 ui 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021422 1.0.1 ui 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021420 1.0.1 platform 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021414 1.0.1 platform 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021418 1.0.1 platform 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021419 1.0.1 platform 1.0.1.0 passed passed passed
${BD}/createVersion.sh CXP9021421 1.0.1 platform 1.0.1.0 passed passed passed


