from datetime import datetime
import os
import re
from subprocess import *
import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()
import json
from cireports.models import *
import shutil
import glob
from distutils.version import LooseVersion


def createDynamicRepo(repoContents,addArtifacts,drop,product,isoObj=None):
    try:
        timeStamp = datetime.now().isoformat()
        timeStamp = timeStamp.replace('.','_')
        timeStamp = timeStamp.replace(':','_')
        timeStamp = timeStamp.replace('-','_')
        if isoObj:
            mediaName = isoObj.mediaArtifact.name
            mediaVersion = str(isoObj.version).replace('.','_')
            dropUnderscore = drop.replace('.','_')
            repoDirectory = str(product)+"_"+ str(dropUnderscore)+"_"+ str(mediaName)+"_"+str(mediaVersion)
            if addArtifacts:
                repoDirectory = repoDirectory+"_"+timeStamp
        else:
            dropUnderscore = drop.replace('.','_')
            repoDirectory = str(product)+"_"+ str(dropUnderscore)+"_"+timeStamp
        directoryBase = config.get("VIRTUAL", "directoryBase")
        nexusBase = config.get("VIRTUAL", "nexusBase")
        nexusReadOnly1 = config.get("VIRTUAL", "nexusReadOnly1")
        nexusReadOnly2 = config.get("VIRTUAL", "nexusReadOnly2")
        nexusReadOnly3 = config.get("VIRTUAL", "nexusReadOnly3")
        directory = directoryBase + repoDirectory
        os.makedirs(directory)
        tmpList = repoContents
        nameString = ""
        for item in repoContents:
            artifactName = str(item['name'])
            nameString =nameString +"#"+artifactName+"#"
        if addArtifacts:
            addArtifactsList = addArtifacts.split('#')
            for replaceArtifact in addArtifactsList:
                replaceName,replaceVer = replaceArtifact.split('::')
                if PackageRevision.objects.filter(package__name=replaceName,version=replaceVer,m2type='rpm').exists():
                    replaceObj =  PackageRevision.objects.get(package__name=replaceName,version=replaceVer,m2type='rpm')
                    replaceJson = [
                            {
                                "name":replaceObj.package.name,
                                "number":replaceObj.package.package_number,
                                "url":replaceObj.getNexusUrl(),
                                "mediaCategory":replaceObj.category.name,
                                "mediaPath":str(replaceObj.media_path),
                                "platform":replaceObj.platform,
                                "version":replaceObj.version,
                                "group":replaceObj.groupId,
                            }
                                  ]
                else:
                    logger.error("Artifact Does not exist: "+ str(replaceName)+":"+str(replaceVer))
                    deleteDynamicRepo(repoDirectory)
                    return "ERROR: Artifact Does not exist: "+ str(replaceName)+":"+str(replaceVer)
                if "#"+replaceName+"#" in nameString:
                    tmpList =   []
                    for tmpItem in repoContents:
                        if str(tmpItem['name']) == replaceName:
                            tmpList = tmpList + replaceJson
                        else:
                            tmpList = tmpList + [tmpItem]
                    repoContents = tmpList
                else:
                    repoContents = repoContents + replaceJson
        for item in repoContents:
            urlLocation = str(item['url'])
            fileName = urlLocation.split('/')[-1]
            fileLocation1 = urlLocation.replace(nexusBase,nexusReadOnly1)
            fileLocation2 = urlLocation.replace(nexusBase,nexusReadOnly2)
            fileLocation3 = urlLocation.replace(nexusBase,nexusReadOnly3)

            if os.path.isfile(fileLocation1):
                linkName = directory + '/' + fileName
                os.symlink(fileLocation1, linkName)
            elif os.path.isfile(fileLocation2):
                linkName = directory + '/' + fileName
                os.symlink(fileLocation2, linkName)
            elif os.path.isfile(fileLocation3):
                linkName = directory + '/' + fileName
                os.symlink(fileLocation3, linkName)
            else :
                logger.error("Issue creating Repo file does not exist: "+str(fileLocation1)+" and "+str(fileLocation2)+" and "+str(fileLocation3))
                deleteDynamicRepo(repoDirectory)
                return "ERROR: Issue creating Repo file does not exist: "+str(fileLocation1)+" and "+str(fileLocation2)+" and "+str(fileLocation3)
        createRepoResult = subprocess.check_call(["createrepo", directory], cwd="/tmp")
        if not createRepoResult == 0:
            logger.error("Issue creating Repo: "+str(directory))
            deleteDynamicRepo(repoDirectory)
            return "ERROR: Issue creating Repo: "+str(directory)
        return repoDirectory
    except Exception as e:
        logger.error("Issue creating Repo: "+str(e))
        return "Issue creating Repo: "+str(e)


def deleteDynamicRepo(repoDirectory):
    try:
        directoryBase = config.get("VIRTUAL", "directoryBase")
        directoryToDelete = directoryBase + str(repoDirectory)
        #check it exists
        directoryExists = os.path.exists(directoryToDelete)
        #check it has a ./repodata
        repoExists = os.path.exists(directoryToDelete+'/repodata')
        #check it's not the main dir
        notBaseDirectory = directoryBase != directoryToDelete
        #check no ..
        noDots = '..' not in directoryToDelete
        #check it contains the basedir
        startsWithBasedir = directoryToDelete.startswith(directoryBase)
        if directoryExists and repoExists and notBaseDirectory and noDots:
            deleteErrors = shutil.rmtree(directoryToDelete)
            if not deleteErrors:
                ret="OK"
            else:
                ret = "ERROR deleting repo"
        elif directoryExists:
            deleteErrors = shutil.rmtree(directoryToDelete)
            if not deleteErrors:
                ret="OK"
            else:
                ret = "ERROR deleting repo: "+str(repoDirectory)
        else:
            ret = "ERROR deleting repo: "+str(repoDirectory)
    except Exception as e:
        logger.debug("ERROR issue deleting repo "+str(repoDirectory)+str(e))
        ret = "ERROR issue deleting repo "+str(repoDirectory)+str(e)
    return ret

def createDynamicAPTRepo(repoContents,drop,product):
    try:
        dropUnderscore = drop.replace('.','_')
        repoDirectory = str(product)+"/"+ str(dropUnderscore)
        directoryBase = config.get("VIRTUAL", "staticDirectoryBase")
        nexusBase = config.get("VIRTUAL", "nexusBase")
        nexusReadOnly1 = config.get("VIRTUAL", "nexusReadOnly1")
        nexusReadOnly2 = config.get("VIRTUAL", "nexusReadOnly2")
        nexusReadOnly3 = config.get("VIRTUAL", "nexusReadOnly3")
        signKey = config.get("VIRTUAL", "gpgKey")
        repreproCommand = config.get("VIRTUAL", "repreproCommand")
        directory = directoryBase + repoDirectory
        if os.path.exists(directory):
            notBaseDirectory = directoryBase != directory
            noDots = '..' not in directory
            if notBaseDirectory and noDots:
                shutil.rmtree(directory)
        os.makedirs(directory)
        os.makedirs(directory+"/conf")
        distributionsFileObject = open(directory+"/conf/distributions", 'w')
        distributionsFileObject.write("Codename: trusty\n")
        distributionsFileObject.write("Components: main\n")
        distributionsFileObject.write("Architectures: i386 amd64\n")
        distributionsFileObject.write("SignWith: "+signKey+"\n")
        distributionsFileObject.close()
        tmpList = repoContents
        nameString = ""
        for item in repoContents:
            if not str(item['type']) == 'deb':
                continue
            urlLocation = str(item['url'])
            fileName = urlLocation.split('/')[-1]
            fileLocation1 = urlLocation.replace(nexusBase,nexusReadOnly1)
            fileLocation2 = urlLocation.replace(nexusBase,nexusReadOnly2)
            fileLocation3 = urlLocation.replace(nexusBase,nexusReadOnly3)

            if os.path.isfile(fileLocation1):
                linkName = directory + '/' + fileName
                os.symlink(fileLocation1, linkName)
            elif os.path.isfile(fileLocation2):
                linkName = directory + '/' + fileName
                os.symlink(fileLocation2, linkName)
            elif os.path.isfile(fileLocation3):
                linkName = directory + '/' + fileName
                os.symlink(fileLocation3, linkName)
            else :
                logger.error("Issue creating Repo file does not exist: "+str(fileLocation1)+" and "+str(fileLocation2)+" and "+str(fileLocation3))
                deleteDynamicRepo(repoDirectory)
                return "ERROR: Issue creating Repo file does not exist: "+str(fileLocation1)+" and "+str(fileLocation2)+" and "+str(fileLocation3)
        createRepoResult = subprocess.check_call("cd "+directory+";"+repreproCommand+" --gnupghome /home/lciadm100/.gnupg/ includedeb trusty *.deb", shell=True, cwd="/tmp")
        if not createRepoResult == 0:
            logger.error("Issue creating Repo: "+str(directory))
            deleteDynamicRepo(repoDirectory)
            return "ERROR: Issue creating Repo: "+str(directory)
        return repoDirectory
    except Exception as e:
        logger.error("Issue creating Repo: "+str(e))
        return "Issue creating Repo: "+str(e)

def deletePatchSetRepo(staticDirectoryBase, patchSetFile, directory):
    '''
    clean up for Patch Set Repo
    '''
    if os.path.exists(str(staticDirectoryBase) +"/"+ str(patchSetFile)):
        os.system("rm -rf " + str(staticDirectoryBase) +"/"+ str(patchSetFile))
    if os.path.isdir(str(directory)):
        os.system("rm -rf " + str(directory))

def createPatchSetRepo(artifact, artifactVersion, patchVersion, rhelVersion=None):
    '''
     Create Yum Repo for Patch Set
    '''
    group=None
    armRepo=None
    mediaType=None
    patchName=None
    mediaArtifactVer=None
    returnJson = {}
    patchName = getPatchName(artifact)
    if not patchName:
        errMsg = "Failed to get PatchName from artifact: Patch name is not valid"
        logger.error(errMsg)
        return errMsg, 404
    if rhelVersion:
        rhelVersion = patchName + str(rhelVersion)
    else:
        rhelVersion = patchName + "6.6"
    staticRepoBase =  config.get("VIRTUAL", "aptRepoBase")
    nexusUrlApi=config.get('DMT_AUTODEPLOY', 'nexus_url_api')
    staticDirectoryBase = config.get("VIRTUAL", "staticDirectoryBase")
    yumRepoIndexFileDirectory = config.get("VIRTUAL", "yumRepoIndexFileDirectory")
    yumRepoIndexFile = config.get("VIRTUAL", "yumRepoIndexFile")
    threePPDirectoryPath = config.get("VIRTUAL", "threePPDirectoryPath")
    try:
        artifactValues = ("groupId", "arm_repo", "artifactId", "mediaArtifact__mediaType")
        mediaArtifactVer = ISObuild.objects.only(artifactValues).values(*artifactValues).get(artifactId=artifact, version=artifactVersion)
        artifact = mediaArtifactVer['artifactId']
        group = mediaArtifactVer['groupId']
        armRepo = mediaArtifactVer['arm_repo']
        mediaType = mediaArtifactVer['mediaArtifact__mediaType']
        returnJson['artifact'] = str(artifact)
        returnJson['artifactVersion'] = str(artifactVersion)
        returnJson['groupId'] = str(group)
        if patchVersion is None:
            patchVersion = 'Unavailable'
        returnJson['patchVersion'] = str(patchVersion)
        returnJson['rhelVersion'] = str(rhelVersion)
    except Exception as e:
        errMsg = "Issue creating Repo, unable to get Media Artifact Information: "+str(e)
        logger.error(errMsg)
        return errMsg, 404

    (junk, patchSetName) = str(artifact).split("_", 1)
    patchSetFileName = str(rhelVersion) + "_" + str(patchSetName)
    patchSetFile = str(patchSetFileName) + "-" + str(artifactVersion) + "." + str(mediaType)
    patchSetDirectoryName = str(patchSetFileName) + "-" + str(artifactVersion)
    directory = str(staticDirectoryBase) + str(patchSetDirectoryName)

    try:
        deletePatchSetRepo(staticDirectoryBase, patchSetFile, directory)
        nexusCommand = "curl -f -o " + staticDirectoryBase + "/" + str(patchSetFile) + " -L -# \"" + str(nexusUrlApi) + "/artifact/maven/redirect?r=" + str(armRepo) + "&g=" + str(group) + "&a=" + str(artifact) + "&e=" + str(mediaType) + "&v=" + str(artifactVersion) + "\" > /dev/null 2>&1"
        process = subprocess.Popen(str(nexusCommand), stderr=STDOUT, stdout=PIPE, shell=True)
        streamdata, output = process.communicate()[0], process.returncode
        if not output == 0:
            errMsg = "Issue creating Repo could not download: " + patchSetFile
            logger.error(errMsg)
            return errMsg, 404
    except Exception as e:
        deletePatchSetRepo(staticDirectoryBase, patchSetFile, directory)
        errMsg = "Issue creating Repo could not download: "+str(e)
        logger.error(errMsg)
        return errMsg, 404

    try:
        if os.path.isdir(str(directory)):
            os.system("rm -rf " + str(directory))
        os.system("mkdir " + str(directory))
        if patchSetFile.endswith(".tar.gz"):
            os.system("tar -zxvf "+ str(staticDirectoryBase) +"/"+ str(patchSetFile) + " -C " + str(directory) + "> " + str(directory) +"/output.txt 2>&1")
            os.system("rm -rf " + str(staticDirectoryBase) +"/"+ str(patchSetFile))
        else:
            os.system(str(threePPDirectoryPath) + "extract_iso/bin/extract_iso.sh " + str(staticDirectoryBase) + "/" + str(patchSetFile) + " " + str(directory))
            os.system("rm -rf " + str(staticDirectoryBase) + "/" + str(patchSetFile))
            os.system("find " + str(directory) + " -type f > " + str(directory) + "/output.txt 2>&1")
    except Exception as e:
        deletePatchSetRepo(staticDirectoryBase, patchSetFile, directory)
        errMsg = "Issue creating Repo could not untar and remove file: "+str(e)
        logger.error(errMsg)
        return errMsg, 404

    try:
        searchVersion = str(patchSetFileName).split('.',1)[0]
        command = "grep -o -P '("+patchName+"/"+str(searchVersion)+").*(/packages/|/Packages/)' "+str(directory)+"/output.txt"
        process = subprocess.Popen(str(command), stdout=subprocess.PIPE, shell=True)
        output = process.communicate()[0]
        baseDirList = str(output).rstrip().split('\n')
        baseDirList = list(set(baseDirList))
        indexHeader = str(rhelVersion) + " Patch Version " + str(patchVersion)
        for baseDir in baseDirList:
            if requireRhel8Support(str(rhelVersion)):
                packageLoction = '/Packages/'.replace('/', '\/')
                baseDir = getRhel8PatchSetRepoBaseDir(str(baseDir), str(directory), str(rhelVersion))
                new_directory = str(directory) + '/' + str(baseDir).split('Packages/')[0]
            else:
                packageLoction = str("/"+str(baseDir)+"/").replace('/', '\/')
                new_directory = str(directory)
            os.system("cp "+ str(yumRepoIndexFileDirectory) + str(yumRepoIndexFile) + " " + str(new_directory))
            os.system("sed -i -- 's/PACKAGES/"+str(packageLoction)+"/g' " + str(new_directory) + "/"+ str(yumRepoIndexFile))
            os.system("sed -i -- 's/HEADER/"+str(indexHeader)+"/g' " + str(new_directory) + "/"+ str(yumRepoIndexFile))
            os.system("rm -rf " +str(directory) +"/output.txt")
    except Exception as e:
        errMsg = "Issue updating showYUMRepoIndex file: "+str(e)
        logger.error(errMsg)
        deletePatchSetRepo(staticDirectoryBase, patchSetFile, directory)
        return errMsg, 404
    try:
        if not requireRhel8Support(rhelVersion):
            createRepoResult = subprocess.check_call(["createrepo", directory], cwd="/tmp")
            if not createRepoResult == 0:
                errMsg = "Issue creating Repo: "+str(directory)
                logger.error(errMsg)
                deletePatchSetRepo(staticDirectoryBase, patchSetFile, directory)
                return errMsg, 404
    except Exception as e:
        errMsg = "Issue creating Repo: "+str(e)
        logger.error(errMsg)
        deletePatchSetRepo(staticDirectoryBase, patchSetFile, directory)
        return errMsg, 404
    yumRepo = str(staticRepoBase) + str(patchSetDirectoryName)
    returnJson['url'] = str(yumRepo)
    setLatest, outputExitcode = setLatestPatchSet(staticDirectoryBase, patchSetFileName, artifact, artifactVersion)
    if not outputExitcode == 0:
        returnJson['error'] = str(setLatest)
    return returnJson, 201


def setLatestPatchSet(staticDirectoryBase, patchSetFileName, artifact, artifactVersion):
    '''
    Setting Latest Patch Set
    '''
    (patchSetName, number) = patchSetFileName.rsplit('_', 1)
    latestDirectoryBase =  str(staticDirectoryBase) + patchSetName
    if not os.path.isdir(str(latestDirectoryBase)):
        os.system("mkdir " + str(latestDirectoryBase))
        os.system("touch " +  str(latestDirectoryBase) + "/yumRepoVersion.txt")
    latestPatchSetVersion = str(artifactVersion)
    patchSetSearch = str(staticDirectoryBase)+ str(patchSetFileName) +"-*"
    patchSetList = glob.glob(str(patchSetSearch))
    for patchSet in patchSetList:
        junk, patchSetVersion = str(patchSet).rsplit('-', 1)
        if LooseVersion(str(patchSetVersion)) > LooseVersion(str(latestPatchSetVersion)):
            latestPatchSetVersion = str(patchSetVersion)
    latestRepo = str(staticDirectoryBase) + str(patchSetFileName)+ "-"+str(latestPatchSetVersion)+ " " + str(latestDirectoryBase) +"/latest"
    command = 'ln -sfn ' + str(latestRepo)
    process = subprocess.Popen(str(command), stderr=STDOUT, stdout=PIPE, shell=True)
    streamdata, output = process.communicate()[0], process.returncode
    if not output == 0:
        errMsg = "Issue Setting Latest YumRepo for Patch Set: "+str(artifact + "-" + latestPatchSetVersion)
        logger.error(errMsg)
        return errMsg, output
    os.system("echo " + str(artifact + "-" + latestPatchSetVersion) + " > " + str(latestDirectoryBase) + "/yumRepoVersion.txt")
    successMsg = "Created symlink"
    logger.info(str(successMsg))
    return successMsg, 0

def createLatestYumRepoPath(yumRepo, productName):
    '''
    Moves product yum repo to staticRepos from dynamicRepos then creates product latest yum repo
    '''
    productName = str(productName).upper()
    staticDirectoryBase = config.get("VIRTUAL", "staticDirectoryBase")
    dynamicDirectoryBase = config.get("VIRTUAL", "directoryBase")
    latestDirectoryBase = str(staticDirectoryBase)+str(productName)
    if not os.path.isdir(str(latestDirectoryBase)):
        os.system("mkdir " + str(latestDirectoryBase))
        os.system("touch " +  str(latestDirectoryBase) + "/yumRepoVersion.txt")
    latestDirectory = str(staticDirectoryBase)+str(productName)+"/latest"
    latestRepoInput = str(staticDirectoryBase) + str(yumRepo)+ " " + str(latestDirectory)
    staticYumRepoPath = os.path.join(str(staticDirectoryBase) + str(yumRepo))
    if not os.path.exists(staticYumRepoPath):
        commands = ['mv ' + str(dynamicDirectoryBase) + str(yumRepo) + ' ' + str(staticDirectoryBase),
                    'ln -sfn ' + str(latestRepoInput),
                    'echo ' + str(yumRepo) + ' > ' + str(latestDirectoryBase) + '/yumRepoVersion.txt']
        for command in commands:
            process = subprocess.Popen(command, stderr=STDOUT, stdout=PIPE, shell=True)
            streamdata, output = process.communicate()[0], process.returncode
            if not output == 0:
                errMsg = "Issue creating latest yum Repo path - command: " + str(command)
                logger.error(errMsg)
                return errMsg, 404
    else:
        return "Static yum repo path already exists so skipped new directory creation", 201
    return "SUCCESS", 201

def getPatchName(artifact):
    '''
    Get patch name from artifact using regular expressions
    '''
    patchName = None
    match = re.match(r"([a-z]+)", artifact, re.I)
    if match:
        patchName = match.groups()[0]
    return patchName

def requireRhel8Support(rhelVersion):
    return str(rhelVersion).find('8.') != -1

def getRhel8PatchSetRepoBaseDir(baseDir, fullpath, osVersion):
    '''
    Remove redundant stream name for RHEL8 repo
    i.e. "RHEL8.8.eus_AppStream-1.2.1" -> "RHEL8.8_AppStream-1.2.1"
    '''
    repoDirName = baseDir.split('/')[1]
    osName, repoName = repoDirName.split('_')
    oldDirName = osName + "_" + repoName
    osName = osVersion
    newDirName = osName + '_' + repoName
    rhelDirName = baseDir.split('/')[0]
    oldDirPath = fullpath + '/' + rhelDirName + '/' + oldDirName
    newDirPath = fullpath + '/' + rhelDirName + '/' + newDirName
    if oldDirName != newDirName:
        renameDirectory(oldDirPath, newDirPath)
    return rhelDirName + '/' + osName + '_' + repoName

def renameDirectory(oldDirPath, newDirPath):
    '''
    change directory name using linux command
    i.e. "mv /proj/lciadm100/cifwk/latest/django_proj/cireports/static/staticRepos/RHEL8.8_OS_Patch_Set_CXP9043482-1.2.1/RHEL/RHEL8.8.eus_AppStream-1.2.1
    /proj/lciadm100/cifwk/latest/django_proj/cireports/static/staticRepos/RHEL8.8_OS_Patch_Set_CXP9043482-1.2.1/RHEL/RHEL8.8_AppStream-1.2.1"
    '''
    try:
        exitStatus = os.system("mv " + oldDirPath + " " + newDirPath)
        if exitStatus != 0:
            logger.error("Failed to rename the directory.")
    except Exception as e:
        logger.error("An error occurred while renaming the directory: " + str(e))