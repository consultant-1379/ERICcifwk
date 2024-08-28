#!/bin/bash

# Define executables
_ECHO=echo
_BASENAME=basename
_CAT=cat
_CURL=curl
SCRIPTNAME="$($_BASENAME $0)"

# Print usage instructions
function usage() {
    $_ECHO "Usage:"
    $_ECHO "${SCRIPTNAME} -sh <host> -dh <host> -t <template> [-r <repo>] [-j <jobname>] [-sa <authtoken>] [-da <authtoken>]"
    $_ECHO ""
    $_ECHO "Where:"
    $_ECHO "    -sh   - Source Jenkins host"
    $_ECHO "    -dh   - Destination Jenkins host"
    $_ECHO "    -t    - Template job name"
    $_ECHO "    -r    - Git repository"
    $_ECHO "    -j    - Jenkins job name"
    $_ECHO "    -sa   - Source Jenkins authentication token"
    $_ECHO "    -da   - Destination Jenkins authentication token"
    $_ECHO
    $_ECHO "    <host> is the base URL of the Jenkins instance to copy from/to"
    $_ECHO "        https://jenkins.lmera.ericsson.se/testjenkins"
    $_ECHO "    <template> is the name of the template job on the source Jenkins host"
    $_ECHO "    <repo> is the name of a gerrit project"
    $_ECHO "        The gerrit project names can be retrieved with the command:"
    $_ECHO "            ssh gerrit-gamma.gic.ericsson.se -p 29418 gerrit ls-projects"
    $_ECHO "        This replaces any occurance of '___REPO___' in the template job configuration."
    $_ECHO "    <jobname> is the name of the Jenkins job to create"
    $_ECHO "        By default the last part of the gerrit project is used to name the Jenkins job."
    $_ECHO "    <authtoken> is the Jenkins authentication token in the format <username>:<token>"
    $_ECHO "        By default no authentication is used"
    $_ECHO "        The API token is available in your personal configuration page."
    $_ECHO "        Click your name on the top right corner on every page,"
    $_ECHO "        then click \"Configure\" to see your API token."
    $_ECHO "        Example: esignum:0123456789abcdef0123456789abcdef"
    $_ECHO
    $_ECHO "Examples:"
    $_ECHO "    ${SCRIPTNAME} -sh http://eselivm2v553l.lmera.ericsson.se:8080/jenkins \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -dh http://jenkins1:8080/jenkins                        \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -t NewTemplate_Release                                  \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -r OSS/com.ericsson/testapp                             \ "
    $_ECHO
    $_ECHO "    ${SCRIPTNAME} -sh https://jenkins.lmera.ericsson.se/testjenkins \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -dh https://jenkins.lmera.ericsson.se/newjenkins  \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -t NewTemplate_PreCodeReview                      \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -r OSS/com.ericsson/testapp                       \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -j TestApp_PreCodeReview                          \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -sa esignum:0123456789abcdef0123456789abcdef      \ "
    $_ECHO "    ${SCRIPTNAME//?/ } -da esignum:fedcba9876543210fedcba9876543210      \ "
}

# Print error messages
function error() {
    ERR=$1
    shift
    case ${ERR} in
        1)
            $_ECHO "${SCRIPTNAME}: Unknown parameter $1"
            ;;
        2)
            $_ECHO "${SCRIPTNAME}: Missing parameter: $1"
            ;;
        3)
            $_ECHO "${SCRIPTNAME}: Invalid base URL: $1"
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
        "-sh"|"--source_host")
            SRCHOST=$2
            shift
            ;;
        "-dh"|"--dest_host")
            DESTHOST=$2
            shift
            ;;
        "-t"|"--template")
            TEMPLATE=$2
            shift
            ;;
        "-j"|"--job")
            JOB=$2
            shift
            ;;
        "-r"|"--repo")
            REPO=$2
            shift
            ;;
        "-sa"|"--source_authorization")
            SRCAUTH=$2
            shift
            ;;
        "-da"|"--dest_authorization")
            DESTAUTH=$2
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
if [[ -z "${SRCHOST}" ]]; then error 2 "Source Jenkins host"; fi
if [[ -z "${DESTHOST}" ]]; then error 2 "Destination Jenkins host"; fi
if [[ -z "${TEMPLATE}" ]]; then error 2 "Template name"; fi
if [[ -z "${REPO}${JOB}" ]]; then error 2 "Git repository or Job name is needed"; fi

# Process optional parameter values
if [ "${JOB}" == "" ]; then
    JOB=${REPO##*/}
fi
if [[ ! -z "${SRCAUTH}" ]]; then
    SRCAUTH="-u ${SRCAUTH}"
fi
if [[ ! -z "${DESTAUTH}" ]]; then
    DESTAUTH="-u ${DESTAUTH}"
fi

# Validate and construct Jenkins base URLs for REST
URLPATTERN='(https?|ftp|file)://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]'
if [[ ${SRCHOST} =~ ${URLPATTERN} ]]; then
    SRCURL="${SRCHOST}/job/${TEMPLATE}/config.xml"
else
    error 3 "${SRCHOST}"
fi
if [[ ${DESTHOST} =~ ${URLPATTERN} ]]; then
    DESTURL="${DESTHOST}/createItem?name=${JOB}"
else
    error 3 "${DESTHOST}"
fi

# Retrieve source job configuration
JOBCONFIG=$($_CURL -s ${SRCAUTH} ${SRCURL})

# Subsitute git repo name in job configuration
if [[ ! -z "${REPO}" ]]; then
    JOBCONFIG=$($_ECHO "${JOBCONFIG}" | sed "s#___REPO___#${REPO}#g")
fi

# Create destination job
$_CURL -s -X POST ${DESTAUTH} -H "Content-Type:application/xml" -d "${JOBCONFIG}" "${DESTURL}"
