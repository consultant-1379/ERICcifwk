#!/bin/bash

# Define executables
_ECHO=echo
_BASENAME=basename
_SSH=ssh
_GIT=git

# Print usage instructions
function usage() {
    $_ECHO "Usage:"
    $_ECHO "    $($_BASENAME $0) -p <project> -u <user> [-d <directory>]"
    $_ECHO ""
    $_ECHO "Where:"
    $_ECHO "    <project> is the gerrit project name"
    $_ECHO "    <user> is a Gerrit Central username (signum)"
    $_ECHO "    <directory> is the local repository name"
    $_ECHO ""
    $_ECHO "Note:"
    $_ECHO "    The ssh key from here (~/.ssh/id_rsa.pub) needs"
    $_ECHO "    to be added to the specified Gerrit Central user."
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
        "-p"|"--project")
            PROJECT=$2
            shift
            ;;
        "-d"|"--directory")
            DIR=$2
            shift
            ;;
        "-u"|"--user")
            USER=$2
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

# Check for required parameters
if [ "${PROJECT}" == "" ]; then error 2 "Project"; fi
if [ "${USER}" == "" ]; then error 2 "User"; fi

# Set defaults for optional parameters
if [ "${DIR}" == "" ]; then
    DIR=${PROJECT##*/}
fi

$_GIT clone ssh://${USER}@gerrit-gamma-read.seli.gic.ericsson.se:29418/${PROJECT} ${DIR}

pushd ${DIR}

$_SSH gerrit1 -p 29418 gerrit create-project -n ${PROJECT} -p All-Projects

$_GIT remote set-url origin ssh://gerrit1:29418/${PROJECT}

$_GIT push --mirror origin

popd
