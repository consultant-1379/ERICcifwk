import fwk.utils
import sys, os, tempfile, logging, tarfile, subprocess

logger = logging.getLogger(__name__)

from ciconfig import CIConfig
config = CIConfig()

def getOAMArtifact(localTmpDirectory,artifactName,artifactVersion):
    '''
    The getOAMArtifact function gets the O&M tar ball from nexus based on the artifact Name and Version and stores in a tmp dir
    '''
    nexusReleaseUrl = config.get('CIFWK', 'nexus_url')

    completeArtifactName = (str(nexusReleaseUrl) +
                           "/releases" +
                           "/com/ericsson/nms/infrastructure/" +
                           str(artifactName) + "/" +
                           str(artifactVersion) +
                           "/" + str(artifactName) + "-" +
                           str(artifactVersion) + ".gz")
    logger.info("Complete Download Nexus URL: " +str(completeArtifactName))

    try:
        fwk.utils.downloadFile(completeArtifactName, localTmpDirectory)
        logger.info("Downloaded Artifact with Success: " )
    except Exception as e:
        logger.error("There was an issue with downloading artifact: " +str(e))
        return 1

def updateOAMArtifact(artifactName,artifactVersion):
    '''
    The updateOAMArtifact function updates the tmp area to include a ISO base directory and om ERICJump dependent hidden file, hardcoded
    as no version control info work done on LITP OAM software by CIFWK
    '''
    localTmpDirectory = tempfile.mkdtemp()
    logger.info("Local Temp Directory created: " +str(localTmpDirectory))

    updateDir = localTmpDirectory + "/om_linux"
    try:
        os.makedirs(updateDir)
        logger.info("Base Media directory created with success")
    except Exception as e:
        logger.error("Issue creating Base Media directory: " +str(e))
        return 1

    try:
        hiddenMediaFile = localTmpDirectory + "/.om_linux"
        hiddenFile = open(hiddenMediaFile,'ab')
        hiddenFile.write("media_label=om_linux\n")
        hiddenFile.write("media_desc=OM_LINUX\n")
        hiddenFile.write("media_prefix=19089\n")
        hiddenFile.write("media_number=CXP9022633\n")
        hiddenFile.write("media_rev=A1\n")
        hiddenFile.write("media_arch=common\n")
        hiddenFile.write("media_dir=OM_LINUX_O13_0/13.0.10\n")
        hiddenFile.close()
        logger.info("Hidden O&M Media File Created with Success")
        return localTmpDirectory,updateDir
    except Exception as e:
        logger.error("There was a issue creating the OM Media hidden media file: " +str(e))
        return 1

def unpackOAMArtifcat(localTmpDirectory,updatedLocalTmpDir,artifactName,artifactVersion):
    '''
    The unpackOAMArtifcat function upacks the OAM tar ball downloaded from Nexus and then deletes this tar ball per ISO build
    '''
    try:
        tarFile = updatedLocalTmpDir + "/" + str(artifactName) + "-" + str(artifactVersion) + ".gz"
        uppackLocation = updatedLocalTmpDir + "/"
        tar = tarfile.open(tarFile)
        tar.extractall(uppackLocation)
        tar.close()
        os.remove(tarFile)
        logger.info("Unpacked O&M tar file: " + str(tarFile) + " with success and deleted")
    except Exception as e:
        logger.error("Issue with extracting tar file; " +str(e))
        return 1

def createOAMISO(localTmpDirectory,artifactName,artifactVersion):
    '''
    The createOAMISO function created the O&M ISO using the mkisfs linux command via the subprocess django plugin
    '''
    try:
        command = 'mkisofs -J -l -R -V "om_media" -o ' +str(localTmpDirectory) + "/" + str(artifactName) + "-" + str(artifactVersion) + ".iso "  + str(localTmpDirectory)
        logger.info(command)
        process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd="/tmp")
        process.communicate()
        logger.info("OAM ISO created with success")
    except Exception as e:
        logger.error("Issue with creating OAM media: " +str(e))
        return 1

