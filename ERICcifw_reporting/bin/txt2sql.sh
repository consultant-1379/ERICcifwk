#!/bin/bash

# Find my current dir
BASEDIR=$(/usr/bin/dirname $0)
# NOTE: This behaviour relies on shell builtins for cd and pwd
BASEDIR=$(cd ${BASEDIR}/.. ; pwd)
[ -f ${BASEDIR}/etc/global.env ] && . ${BASEDIR}/etc/global.env

INPUT_FILE=$1
GROUP=$2
ARTIFACT=$3
VERSION=$4
TYPE=$5
OUTPUT_DIR=$($_DIRNAME ${INPUT_FILE})
OUTPUT_FILE=${OUTPUT_DIR}/deplist.sql

$_ECHO "INSERT IGNORE INTO depmodel_artifact  (name) VALUES( '${ARTIFACT}');" > ${OUTPUT_FILE}
$_ECHO  "INSERT IGNORE INTO depmodel_artifactversion (artifact_id,groupname,version,m2type) VALUES ((SELECT id FROM depmodel_artifact WHERE name = \"${ARTIFACT}\" ), '${GROUP}','${VERSION}','${TYPE}');" >> ${OUTPUT_FILE}

while read LINE
do
    if [[ $LINE =~ ^[^The] ]]; then
        if [[ $LINE == "none" ]]; then
            continue
        fi
        IFS=':' ARRAY=( ${LINE} )
        DEP_GROUP=$($_ECHO ${ARRAY[0]}|$_TR -d ' ')
        DEP_ARTIFACT=${ARRAY[1]}
        DEP_VERSION=${ARRAY[3]}
        DEP_TYPE=${ARRAY[2]}
        DEP_SCOPE=${ARRAY[4]}
        $_ECHO "INSERT IGNORE INTO depmodel_artifact  (name) VALUES( '${DEP_ARTIFACT}');" >> ${OUTPUT_FILE}
        $_ECHO "INSERT IGNORE INTO depmodel_artifactversion (artifact_id,groupname,version,m2type) VALUES ((SELECT id FROM depmodel_artifact WHERE name = \"${DEP_ARTIFACT}\" ), '${DEP_GROUP}','${DEP_VERSION}','${DEP_TYPE}');" >> ${OUTPUT_FILE}
        $_ECHO "INSERT IGNORE INTO depmodel_mapping (artifact_main_version_id,artifact_dep_version_id,scope,build) VALUES ((SELECT id FROM depmodel_artifactversion WHERE artifact_id = (SELECT id FROM depmodel_artifact WHERE name = \"${ARTIFACT}\" ) AND version = \"${VERSION}\" AND groupname = \"${GROUP}\" AND m2type = \"${TYPE}\"),(SELECT id FROM depmodel_artifactversion WHERE artifact_id = (SELECT id FROM depmodel_artifact WHERE name = \"${DEP_ARTIFACT}\" ) AND version = \"${DEP_VERSION}\" AND groupname = \"${DEP_GROUP}\" AND m2type = \"${DEP_TYPE}\") ,'${DEP_SCOPE}', 'False');" >> ${OUTPUT_FILE}
    fi
done < ${INPUT_FILE} 

