#!/bin/bash

# Define executables
_ECHO=echo
_BASENAME=basename
_CAT=cat
_CURL=curl

# Print usage instructions
function usage() {
    $_ECHO "Usage:"
    $_ECHO "$($_BASENAME $0) -t <template> -h <host> -r <reponame> -j <jobname> -a <authtoken>"
    $_ECHO ""
    $_ECHO "Where:"
    $_ECHO "    <template> is the file name of a project template"
    $_ECHO "    <host> is the jenkins base URL"
    $_ECHO "        https://jenkins.lmera.ericsson.se/testjenkins"
    $_ECHO "    <reponame> is the name of a gerrit project"
    $_ECHO "        The gerrit project names can be retrieved with the command:"
    $_ECHO "            ssh gerrit-gamma.gic.ericsson.se -p 29418 gerrit ls-projects"
    $_ECHO "    <jobname> is the name of the Jenkins job to create"
    $_ECHO "        By default the last part of the gerrit project is used to name the Jenkins job."
    $_ECHO "    <authtoken> is the Jenkins authentication token in the format <username>:<token>"
    $_ECHO "        By default no authentication is used"
    $_ECHO "        The API token is available in your personal configuration page."
    $_ECHO "        Click your name on the top right corner on every page,"
    $_ECHO "        then click \"Configure\" to see your API token."
    $_ECHO "        Example: esignum:0123456789abcdef0123456789abcdef"
}

# Print debug values
function debug() {
    $_ECHO "Template = ${TEMPLATE}"
    $_ECHO "Host     = ${HOST}"
    $_ECHO "Repo     = ${REPO}"
    $_ECHO "Job name = ${JOB}"
    $_ECHO "Auth     = ${AUTH}"
    $_ECHO "REST URL = ${RESTURL}"
}

# Print error messages
function error() {
    ERR=$1
    shift
    case ${ERR} in
        1)
            $_ECHO "$($_BASENAME $0): Unknown parameter $1"
            ;;
        2)
            $_ECHO "$($_BASENAME $0): Missing parameter: $1"
            ;;
        3)
            $_ECHO "$($_BASENAME $0): Invalid base URL: $1"
            ;;
        4)
            $_ECHO "$($_BASENAME $0): Template file ($1) missing"
            ;;
        *)
            $_ECHO "Unknown error"
            $_ECHO ${ERR}
            $_ECHO $*
            ;;
    esac
    $_ECHO
    usage
    exit ${ERR}
}

# Process parameters
while [ "$1" != "" ]; do
    case ${1,,} in
        "-t"|"--template")
            TEMPLATE=$2
            shift
            ;;
        "-h"|"--host")
            HOST=$2
            shift
            ;;
        "-r"|"--repo")
            REPO=$2
            shift
            ;;
        "-j"|"--job")
            JOB=$2
            shift
            ;;
        "-a"|"--authorization")
            AUTH=$2
            shift
            ;;
        "-?"|"-h"|"--help")
            usage
            exit
            ;;
        *)
            error 1 $1
            exit -1
            ;;
    esac
    shift
done

# Test required parameter values
if [ "${TEMPLATE}" == "" ]; then error 2 "Template"; fi
if [ "${HOST}" == "" ]; then error 2 "Jenkins host"; fi
if [ "${REPO}" == "" ]; then error 2 "Git repository"; fi

# Process optional parameter values
if [ "${JOB}" == "" ]; then
    JOB=${REPO##*/}
fi

# Create and validate Jenkins base URL for REST
URLPATTERN='(https?|ftp|file)://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]'
if [[ ${HOST} =~ ${URLPATTERN} ]]; then
    RESTURL="${HOST}/createItem?name=${JOB}"
else
    error 3 "${HOST}"
fi

# Validate the template file
if [[ ! -e ${TEMPLATE} ]]; then
    error 4 "${TEMPLATE}"
fi

if [[ ! -z "${AUTH}" ]]; then
    AUTH="-u ${AUTH}"
fi

# Process job template
JOBCONFIG=$($_CAT ${TEMPLATE} | sed "s#__REPO__#${REPO}#")

# Issue the REST call
$_CURL -X POST ${AUTH} -H "Content-Type:application/xml" -d "${JOBCONFIG}" "${RESTURL}" 
