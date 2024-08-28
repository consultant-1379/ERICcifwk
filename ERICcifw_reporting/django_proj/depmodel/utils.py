from django.http import HttpResponse, Http404, HttpResponseRedirect
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, transaction, IntegrityError
import re
import os
#import sets
import logging
logger = logging.getLogger(__name__)
import json
from depmodel.models import *
from cireports.models import *
from cireports.utils import getIntendedDropInfo

def getImportedPackagesFromJavaFile(file):
    '''
    We open the file, look for "import ..." and strip the trailing classname and semicolon
    from the import. Return a list of imports.
    '''
    # TODO: use a dict and store as keys for indexing
    imports = set()
    f = open(file, 'r')

    for line in f:
        # exit when we hit the class definition
        if (re.match("class [a-zA-Z0-9]", line) != None):
            break
        if (re.match("^\W*import ", line) != None):
            importedPackage = re.sub("\.[0-9a-zA-Z]+\W*$", "", re.sub("^\W*import\W+", "", line))
            imports.add(importedPackage)
    f.close()
    return imports

def getImportedPackagesFromJavaFiles(dir):
    '''
    Recursively find all Java files in a directory and for each one find the imports.
    returns a list of all imports in all java classes in the directory
    '''
    for root, subFolders, files in os.walk(dir):
        for file in files:
            if (re.match(".*\.java$", file) != None):
                print os.path.join(root, file) + ":"
                print getImportedPackagesFromJavaFile(os.path.join(root, file))
        for folder in subFolders:
            getImportedPackagesFromJavaFiles(folder)

def storeDependency(package,version):
    try:
        artifactVersionObj = ArtifactVersion.objects.get(version=version,artifact__name=package,m2type='rpm')
    except Exception as e:
        logger.error("Issue getting Artifact Version for Artifact: " + str(package) + " Version: " + str(version) + " Error: " +str(e))
    overall = []
    try:
        getem(artifactVersionObj.id,"",overall)
    except Exception as e:
        logger.error("Error running getem function with Artifact Version ID for Package: " + str(package) + " Error: " +str(e))
    try:
        ret,complete,jarStr,tppStr = findRelatedArtifact(overall)
    except Exception as e:
        logger.error("Error running findRelatedArtifact function, Error: " +str(e))
    try:
        artifactVersionPkgObj = PackageRevision.objects.get(version=version,package__name=package,m2type='rpm')
    except Exception as e:
        logger.error("Error getting Package Revision for Artifact: " + str(package) + " Version: " + str(version) + " Error: " +str(e))
    try:
        if not PackageDependencies.objects.filter(package=artifactVersionPkgObj,deppackage=ret).exists():
            depObj=PackageDependencies(package=artifactVersionPkgObj,deppackage=ret,all=complete,jar_dependencies=jarStr,third_party_dependencies=tppStr)
            depObj.save()
    except Exception as e:
        logger.error("Error: with storing Dependency Artifact for Package: " + str(package) + " Version: " + str(version) +" Error: "+str(e))
        ret = []
    return ret

def returnDependency(artifact,version):
    try:
        data = []
        artifactList = []
        data2=[]
        data1 = []
        importList = []
        namesString = ""
        if cireports.models.ISObuild.objects.filter(version=version, drop__release__iso_artifact=artifact).exists():
            isoObj = ISObuild.objects.get(version=version, drop__release__iso_artifact=artifact)
            isoPackages=ISObuildMapping.objects.filter(iso=isoObj.id)
            for pkg in isoPackages:
                artifactVersionObj=cireports.models.PackageRevision.objects.get(id=pkg.package_revision_id)
                artifactList.append(artifactVersionObj)

        else:
            artifactVersionObj = cireports.models.PackageRevision.objects.get(version=version,package__name=artifact,m2type='rpm')
            artifactList.append(artifactVersionObj)

        for artifactVersionPkgObj in artifactList:
            if PackageDependencies.objects.filter(package=artifactVersionPkgObj).exists():
                imports = []
                deps=PackageDependencies.objects.get(package=artifactVersionPkgObj)
                ver=artifactVersionPkgObj.version
                ver=ver.replace(".","_")
                name=artifactVersionPkgObj.package.name
                group=artifactVersionPkgObj.groupId
                depsList = deps.deppackage.split(',')
                for dep in depsList:
                    gDep,aDep,vDep = dep.split('##')
                    depString = gDep+"."+aDep+"_"+vDep.replace('.','_')
                    importList.append(depString)
                    imports.append(depString)
                    namesString= namesString+group +"."+name+"_"+ver
                data2 = [{
                        "imports":imports,
                        "name":group +"."+name+"_"+ver,
                    }]
            data=data+data2
    except Exception as e:
        logger.error("issue fetching dependency:"+str(e))
        data = []
    for item in importList:
        if item not in namesString:
            data=data+[{"name":item}]
    ret =  json.dumps(data)
    return ret

def returnCompleteDependency(artifact,version):
    try:
        data = []
        artifactList = []
        data2=[]
        data1 = []
        importList = []
        namesString = ""
        if cireports.models.ISObuild.objects.filter(version=version, drop__release__iso_artifact=artifact).exists():
            isoObj = ISObuild.objects.get(version=version, drop__release__iso_artifact=artifact)
            isoPackages=ISObuildMapping.objects.filter(iso=isoObj.id)
            for pkg in isoPackages:
                artifactVersionObj=cireports.models.PackageRevision.objects.get(id=pkg.package_revision_id)
                artifactList.append(artifactVersionObj)

        else:
            artifactVersionObj = cireports.models.PackageRevision.objects.get(version=version,package__name=artifact,m2type='rpm')
            artifactList.append(artifactVersionObj)

        for artifactVersionPkgObj in artifactList:
            if PackageDependencies.objects.filter(package=artifactVersionPkgObj).exists():
                imports = []
                deps=PackageDependencies.objects.get(package=artifactVersionPkgObj)
                ver=artifactVersionPkgObj.version
                ver=ver.replace(".","_")
                name=artifactVersionPkgObj.package.name
                group=artifactVersionPkgObj.groupId
                depsList = deps.all.split(',')
                for dep in depsList:
                    depTo = dep.split('##')
                    len1 = len(depTo)
                    count =0
                    while (count < len1-1):
                        imports = []
                        artifactDepObj=ArtifactVersion.objects.get(id=depTo[count])
                        ver1 = artifactDepObj.version.replace('.','_')
                        depStringName=artifactDepObj.groupname+"."+artifactDepObj.artifact.name+"_"+ver1
                        artifactDepObj=ArtifactVersion.objects.get(id=depTo[count+1])
                        ver2 = artifactDepObj.version.replace('.','_')
                        depStringImports=artifactDepObj.groupname+"."+artifactDepObj.artifact.name+"_"+ver2
                        namesString= namesString+depStringName
                        importList.append(depStringImports)
                        imports.append(depStringImports)
                        if depStringName != depStringImports:
                            data2 = [{
                                "imports":imports,
                                "name":depStringName,
                                    }]
                            data=data+data2

                        count = count + 1
    except Exception as e:
        logger.error("issue fetching dependency:"+str(e))
        data = []
    for item in importList:
        if item not in namesString:
            data=data+[{"name":item}]
    ret =  json.dumps(data)
    return ret

def getem(id,parent,overall):
    deps =  Mapping.objects.filter(artifact_main_version=id)
    for dep in deps:
        if parent == "":
            parentNew = str(dep.artifact_main_version_id)
        else:
            parentNew = parent+"##"+str(dep.artifact_main_version_id)
        getem(dep.artifact_dep_version_id,parentNew,overall)
        add = str(dep.artifact_dep_version_id)
        overall.append(parentNew+"##"+add)

def findRelatedArtifact(overall):
    matchedPair = []
    unmatched = []
    matched = []
    jarList = []
    tppList = []
    completeDep =""
    for depString in overall:
        gavList = depString.split('##')
        gavListComplete = depString.split('##')
        mainArtifactID=gavList[0]
        gavList.pop(0)
        for gavID in gavList:
            pathToDep = [mainArtifactID]
            gavObj=ArtifactVersion.objects.get(id=gavID)
            pathToDep.append(gavID)
            if Mapping.objects.filter(artifact_dep_version_id=gavID,build=True).exists():
                pathFromDep = [gavID]
                pathFromDep = findRelatedPath(gavID,pathFromDep)
                artifactDepId=pathFromDep[-1]
                artifactMatchedList=ArtifactVersion.objects.filter(id=artifactDepId)
                for artifactDepObj in artifactMatchedList:
                    jarDepId=pathFromDep[0]
                    jarList.append(str(jarDepId)+"##"+str(artifactDepId))
                    depString=artifactDepObj.groupname+"##"+artifactDepObj.artifact.name+"##"+artifactDepObj.version
                    completeStr =""
                    for item in gavListComplete:
                        if completeStr == "":
                            completeStr = str(item)
                        else:
                            completeStr += "##"+str(item)
                    for item in pathFromDep:
                        if completeStr == "":
                            completeStr = str(item)
                        else:
                            completeStr += "##"+str(item)

                    if completeDep == "":
                        completeDep = completeStr
                    else:
                        completeDep = completeDep +","+completeStr
                    matched.append(depString)
            else:
                qq=ArtifactVersion.objects.get(id=gavID)
                tppList.append(gavID)

    mainArtifactObj = ArtifactVersion.objects.get(id=mainArtifactID)
    mainArtifact = mainArtifactObj.artifact.name
    mainArtifactVersion = mainArtifactObj.version
    matched = list(set(matched))
    jarList = list(set(jarList))
    tppList = list(set(tppList))
    imports = ""
    for dep in matched:
        if imports=="":
            imports = dep
        else:
            imports = imports+","+dep
    jarStr = ""
    for jarDep in jarList:
        if jarStr=="":
            jarStr = jarDep
        else:
            jarStr = jarStr+","+jarDep
    tppStr = ""
    for tppDep in tppList:
        if tppStr=="":
            tppStr = tppDep
        else:
            tppStr = tppStr+","+tppDep
    return imports,completeDep,jarStr,tppStr


def findRelatedPath(gavID,pathFromDep):
    if  Mapping.objects.filter(artifact_dep_version_id=gavID,build=True).exists():
        #artifactObj=Mapping.objects.filter(artifact_dep_version_id=gavID,build=True)[0]
        try:
            artifactObj=Mapping.objects.get(artifact_dep_version_id=gavID,build=True)
        except Exception as e:
            logger.error("Error: Issue with MApping TAble Query with Dep Version: " +str(gavID)+ " with Flag set to True.")
        parentGavID = artifactObj.artifact_main_version_id
        pathFromDep.append(str(parentGavID))
        findRelatedPath(parentGavID,pathFromDep)
    return pathFromDep

def processParticalBuildTimeArtifacts(artifacts):
    '''
    The processParticalBuildTimeArtifacts function gets all artifacts that an artifact build is building
    and includes in main build artifact eg: RPM
    '''
    artifacts = [entry.encode('utf-8') for entry in artifacts.strip('[]').split(',')]

    artifactNameObj = artifactVersionObj = artifactMappingObjList = None
    artifactGroupNameInnerObj = artifactVersionInnerObj = artifactM2TypeInnerObj = artifactNameInner = None
    artifactGroupNameInnerInnerObj = artifactVersionInnerInnerObj = artifactNameInnerInner = None
    artifactInnerVersionObj =  artifactMappingInnerObjList = None
    rpmArtifactName = rpmEntry = artifactInnerInnerVersionObj = artifactM2TypeInnerInnerObj = None

    artifactList = []
    for artifact in artifacts:
        (groupId, artifactName, packaging, version) = artifact.split(":")
        if "rpm" in packaging.lower():
            rpmEntry = str(groupId.lstrip()) + " " + str(artifactName) + " " + str(packaging) + " " + str(version)
        elif "bom" in artifactName.lower():
            continue
        else:
            entry = str(groupId.lstrip()) + " " + str(artifactName) + " " + str(packaging) + " " + str(version)
            artifactList.append(entry)
    if rpmEntry == None:
        return HttpResponse("No RPM in List, nothing to do, Continue")
    (rpmGroupId, rpmArtifactName, rpmPackaging, rpmVersion) =  rpmEntry.split(" ")
    try:
        artifactNameObj = Artifact.objects.get(name=rpmArtifactName)
    except Exception as e:
        logger.error("DB Query Error Building Artifact: " +str(e))
        return HttpResponse("DB Query Error Building Artifact: " +str(e))
    try:
        artifactVersionObj = ArtifactVersion.objects.get(artifact_id=artifactNameObj.id, groupname=rpmGroupId, version=rpmVersion, m2type=rpmPackaging)
    except Exception as e:
        logger.error("DB Query Error Building Artifact Dep Version: " + str(e))
        return HttpResponse("Query Error Building Artifact Dep Version: " + str(e))

    if Mapping.objects.filter(artifact_main_version_id=artifactVersionObj.id).exists():
        artifactMappingObjList = Mapping.objects.filter(artifact_main_version_id=artifactVersionObj.id)
        for artifactMappingObj in artifactMappingObjList:
            try:
                artifactVersionInnerObj = ArtifactVersion.objects.filter(id=artifactMappingObj.artifact_dep_version_id)
            except Exception as e:
                logger.error("DB Query Error Building Artifact Dep Version for Dep Mapping : " + str(e))
                return HttpResponse("DB Query Error Building Artifact Dep Version for Dep Mapping : " + str(e))

            for artifactVersionInner in artifactVersionInnerObj:
                try:
                    artifactGroupNameInnerObj = str(artifactVersionInner.groupname)
                    artifactInnerVersionObj = str(artifactVersionInner.version)
                    artifactM2TypeInnerObj = str(artifactVersionInner.m2type)
                    artifactNameInner = str(Artifact.objects.get(id=artifactVersionInner.artifact_id).name)
                except Exception as e:
                    logger.error("DB Query Error Building Artifact Dep GAV: " +str(e))
                    return HttpResponse("DB Query Error Building Artifact Dep GAV: " +str(e))

                for artifact in artifactList:
                    (groupId, artifactName, packaging, version) = artifact.split(" ")
                    if (artifactGroupNameInnerObj == str(groupId)) and (artifactM2TypeInnerObj == str(packaging)) and (artifactInnerVersionObj == str(version)) and (artifactNameInner == str(artifactName)):

                        try:
                            if (artifactMappingObj.build) is False:
                                artifactMappingObj.build = True
                                artifactMappingObj.save(update_fields=["build"])
                        except Exception as e:
                            logger.error("Issue Updating Database with Build info: " +str(e))
                            return HttpResponse("Issue Updating Database with Build info: " +str(e))
                        if Mapping.objects.filter(artifact_main_version_id=artifactVersionInner.id).exists():
                            artifactMappingInnerObjList = Mapping.objects.filter(artifact_main_version_id=artifactVersionInner.id)
                            for artifactMappingInnerObj in artifactMappingInnerObjList:
                                try:
                                    artifactVersionInnerInnerObj = ArtifactVersion.objects.filter(id=artifactMappingInnerObj.artifact_dep_version_id)
                                except Exception as e:
                                    logger.error("DB Query Error Building Artifact Dep Version for Dep Inner Mapping : " + str(e))
                                    return HttpResponse("DB Query Error Building Artifact Dep Version for Dep Inner Mapping : " + str(e))
                                for artifactVersionInnerInner in artifactVersionInnerInnerObj:
                                    try:
                                        artifactGroupNameInnerInnerObj = str(artifactVersionInnerInner.groupname)
                                        artifactInnerInnerVersionObj = str(artifactVersionInnerInner.version)
                                        artifactM2TypeInnerInnerObj = str(artifactVersionInnerInner.m2type)
                                        artifactNameInnerInner = str(Artifact.objects.get(id=artifactVersionInnerInner.artifact_id).name)
                                    except Exception as e:
                                        logger.error("DB Query Error Building Artifact Dep GAV Inner: " +str(e))
                                        return HttpResponse("DB Query Error Building Artifact Dep GAV Inner: " +str(e))

                                    for artifact in artifactList:
                                        (groupId, artifactName, packaging, version) = artifact.split(" ")
                                        if (artifactGroupNameInnerInnerObj == str(groupId)) and (artifactM2TypeInnerInnerObj == str(packaging)) and (artifactInnerInnerVersionObj == str(version)) and (artifactNameInnerInner == str(artifactName)):

                                            try:
                                                if (artifactMappingInnerObj.build) is False:
                                                    artifactMappingInnerObj.build = True
                                                    artifactMappingInnerObj.save(update_fields=["build"])
                                            except Exception as e:
                                                logger.error("Issue Updating Database with Build info: " +str(e))
                                                return HttpResponse("Issue Updating Database with Build info: " +str(e))
def processAllBuildTimeArtifacts(artifacts):
    '''
    The processAllBuildTimeArtifacts gets all the artifacts a artifact builds at build time and updates build
    flag in depmodel_mapping table this includes all build time artifacts including test jars, provided
    jars and poms, at the moment bom pom are exclueded as these artifact are not getting wrote to the artifacts table
    This Function is currently not in use as at the time of writing there was a descision point that all
    build artifacts where not yet needed.
    '''
    artifacts = [entry.encode('utf-8') for entry in artifacts.strip('[]').split(',')]
    artifactNameObj = artifactVersionObj = artifactMappingObj = None
    message = "Success"
    rpmArtifactList = []
    newArtifactList = []
    completeArtifactList = []
    updateDict = {}
    artifactsList = [artifact.strip(' ') for artifact in artifacts]

    #Filter out unwanted build Artifacts and build up newArtifactList with this data
    for artifact in artifactsList:
        (groupId, artifactName, packaging, version) = artifact.split(":")
        if "pom" in packaging:
            continue
        elif "bom" in artifactName.lower():
            continue
        elif "test" in artifactName.lower():
            continue
        elif "rpm" in packaging.lower():
            rpmArtifactList.append(artifact)

        newArtifactList.append(artifact)

    #Append the Artifact Data and Artifact Verision Id to completeArtifactList
    for artifact in newArtifactList:
        (groupId, artifactName, packaging, version) = artifact.split(":")
        try:
            artifactNameObj = Artifact.objects.get(name=artifactName)
        except Exception as error:
            logger.error("DB Query Error Building Artifact: " + str(artifactName) + " " +str(error))
            message=("Error: DB Query Error Building Artifact: " + str(artifactName) + " " +str(error))
            return message
        try:
            artifactVersionObj = ArtifactVersion.objects.get(artifact_id=artifactNameObj.id, groupname=groupId, version=version, m2type=packaging)
            completeArtifactList.append(artifact + "###" + str(artifactVersionObj.id))
        except Exception as error:
            logger.error("DB Query Error Building Artifact Dep Version: Artifact Name: " + str(artifactName) + " Version: " + str(version) + " Error: " + str(error))
            message=("Error: DB Query Error Building Artifact Dep Version: Artifact Name: " + str(artifactName) + " Version: " + str(version) + " Error: " + str(error))


    #Split out the Artifact Version, get the Artifact Mapping for each item as main and compare adding results into updateDict
    for artifact in completeArtifactList:
        (artifact,artifactVersion) = artifact.split('###')
        artifactMappingObj = Mapping.objects.filter(artifact_main_version_id=artifactVersion)
        for artif in completeArtifactList:
            (artif,artifactVers) = artif.split('###')
            for artifactMapping in artifactMappingObj:
                if str(artifactMapping.scope) == "provided":
                    continue
                if str(artifactMapping.artifact_dep_version_id) == artifactVers:
                    updateDict[artifactMapping.artifact_dep_version_id] = artifactVersion
                    break

    #Iterate Through updateDict and update Build Status
    for dep,main in updateDict.items():
        if Mapping.objects.filter(artifact_main_version_id=main, artifact_dep_version_id=dep).exists():
            if not Mapping.objects.filter(artifact_dep_version_id=dep, build=True).exists():
                try:
                    artifactMappingObj = Mapping.objects.get(artifact_main_version_id=main, artifact_dep_version_id=dep)
                    artifactMappingObj.build = True
                    artifactMappingObj.save(update_fields=["build"])
                except Exception as error:
                    logger.error("Error: Updating Build status on Mapping Main Id: " + str(main) + " Dep Id: " + str(dep) + " Error: " +str(error))
                    message=("Error: Updating Build status on Mapping Main Id: " + str(main) + " Dep Id: " + str(dep) + " Error: " +str(error))
                    return message
    return message

def returnStackedDependencies(artifactObj,artifactVersionObj,packageDependencyObj):
    '''
    The returnStackedDependencies function returns dependencies to showDependencyStack view
    '''
    artifactNameList = []
    artifactBuildDict = {}
    artifactThirdPartyList = []
    try:
        dependendentPackageList = packageDependencyObj.deppackage.split(',')
        for dependendentPackage in dependendentPackageList:
            gav,artifact,version = dependendentPackage.split("##")
            if artifact not in artifactNameList:
                artifactNameList.append(artifact + "_" + version)
    except Exception as error:
        logger.error("Issue with Building Artifact Dependency List: " +str(error))

    try:
        dependendentPackageBuildList = packageDependencyObj.jar_dependencies.split(',')
        for artifactBuild in dependendentPackageBuildList:
            dependentArtifact,artifact = artifactBuild.split("##")
            artifactVersionObj = ArtifactVersion.objects.get(id=artifact)
            artifactName = Artifact.objects.get(id=artifactVersionObj.artifact_id).name
            dependentArtifactVersionObj=ArtifactVersion.objects.get(id=dependentArtifact)
            dependentArtifactName = Artifact.objects.get(id=dependentArtifactVersionObj.artifact_id).name
            artifactBuildDict[artifactName + "_" + artifactVersionObj.version] = dependentArtifactName + "_" + dependentArtifactVersionObj.version + "_" + dependentArtifactVersionObj.m2type
    except Exception as error:
        logger.error("Issue with Building Artifact Build Dependency Dict: " +str(error))

    try:
        dependendentArtifactThirdPartyList = packageDependencyObj.third_party_dependencies.split(',')
        for dependendentArtifactThirdParty in dependendentArtifactThirdPartyList:
            artifactVersionObj = ArtifactVersion.objects.get(id=dependendentArtifactThirdParty)
            artifactName = Artifact.objects.get(id=artifactVersionObj.artifact_id).name
            artifactThirdPartyList.append(artifactName + "_" + artifactVersionObj.version + "_" + artifactVersionObj.m2type)
    except Exception as error:
        logger.error("Issue with Building Artifact Third Party Dependency List: " +str(error))
    return artifactNameList, artifactBuildDict, artifactThirdPartyList

def returnStackISODependencies(drop, ISOArtfactName, ISOArtifactVersion):
    '''
    The returnStackISODependencies function returns all iso level dependencies to the
    showPackageDependenciesStackISO view for Stack View on UI
    The functions primary returns are nodeString and edgeString which is turn returned to
    the Stack chart which displays the dependency data
    '''
    artifactDepDict = {}
    artifactNameList = []
    doesNotExistFlag = None
    isoBuildObj = ISObuild.objects.get(drop__name=str(drop), version=ISOArtifactVersion);
    isoBuildMapping = ISObuildMapping.objects.filter(iso=isoBuildObj)
    for mapping in isoBuildMapping:
        if PackageDependencies.objects.filter(package=mapping.package_revision.id).exists():
            packageDependencyObj = PackageDependencies.objects.get(package=mapping.package_revision.id)
            try:
                dependendentPackageList = packageDependencyObj.deppackage.split(',')
                for dependendentPackage in dependendentPackageList:
                    gav,artifact,version = dependendentPackage.split("##")
                    if artifact not in artifactNameList:
                        artifactNameList.append(str(artifact + "_" + version))
                artifactDepDict[mapping.package_revision.package.name + "_" + mapping.package_revision.version] = artifactNameList
                artifactNameList = []
            except Exception as error:
                logger.error("Issue with Building Artifact Dependency List: " +str(error))

    if not artifactDepDict:
        doesNotExistFlag = "doesNotExist"

    nodeString = ""
    edgeString = ""
    artifactList = []
    artifactListComplete = []
    count=0
    for artifactName,artifactNameList in artifactDepDict.items():
        if artifactName not in artifactList:
            nodeString = nodeString + "g.addNode(" + str(count) + ",  { label: \"" + str(artifactName) + "\", nodeclass: \"\" });\n"
            artifactListComplete.append(artifactName + "," + str(count))
            artifactList.append(artifactName)
            count = count+1
            for artifact in artifactNameList:
                if artifact not in artifactList:
                   nodeString = nodeString + "g.addNode(" + str(count) + ",  { label: \"" + str(artifact) + "\", nodeclass: \"\" });\n"

                   artifactListComplete.append(artifact + "," + str(count))
                   artifactList.append(artifact)
                   count = count+1

    for artifactName,artifactNameList in artifactDepDict.items():
        parentEntry = filter(lambda item: artifactName in item,artifactListComplete)
        for parent in parentEntry:
            if parentEntry:
                parentArtifactName,parentNumber = parent.split(',')
            for artifact in artifactNameList:
                childEntry = filter(lambda item: artifact in item,artifactListComplete)
                for child in childEntry:
                    if childEntry:
                        childArtifactName,childNumber = child.split(',')
                        edgeString = edgeString + "g.addEdge(null," + str(parentNumber) + "," + str(childNumber) + ");\n"

    return doesNotExistFlag, nodeString, edgeString

def processAnomalyList(anomalyList):
    '''
    The processAnomalyList function is called from the processAnomalies post.
    It checks if anomalies exist in the database and if not it adds them and returns a SUCCESS string
    '''
    anomalies = anomalyList.split(",")
    for anomaly in anomalies:
        groupId = anomaly.split(":")[0]
        artifactId = anomaly.split(":")[1]
        type = anomaly.split(":")[2]
        version = anomaly.split(":")[3]
        try:
            with transaction.atomic():
                if not AnomalyArtifact.objects.filter(name=artifactId).exists():
                    anomalyArtifact = AnomalyArtifact(name=artifactId)
                    anomalyArtifact.save()
                else:
                    anomalyArtifact = AnomalyArtifact.objects.get(name=artifactId)

                if not AnomalyArtifactVersion.objects.filter(anomalyartifact=anomalyArtifact,groupname=groupId,version=version,m2type=type).exists():
                    AnomalyArtifactVersion.objects.create(anomalyartifact=anomalyArtifact, groupname=groupId,version=version,m2type=type)
        except IntegrityError as error:
            return "ERROR: Dealing with transactions to database: " + str(error) + "\n"
    return "SUCCESS: Anomalies created successfully\n"

def processAnomalyPackageRevisionMappingList(mappingList):
    '''
    The processRPMToAnomalyMapping function is called from the ProcessRPMAnomalyMapping post
    It maps a specific rpm version to a specific anomaly version
    '''
    mappings = mappingList.split(",")
    for mapping in mappings:
        anomalyVersion, packageRevision = mapping.split("#")
        groupId,artifactId,type,version = anomalyVersion.split(":")
        try:
            with transaction.atomic():
                anomolyArtifactVersion = AnomalyArtifactVersion.objects.get(anomalyartifact__name=artifactId, groupname=groupId, version=version, m2type=type)
                if not AnomalyArtifactVersionToPackageRev.objects.filter(anomalyartifact_version=anomolyArtifactVersion, package_revision=packageRevision).exists():
                    AnomalyArtifactVersionToPackageRev.objects.create(anomalyartifact_version=anomolyArtifactVersion, package_revision=packageRevision)

        except IntegrityError as error:
            return "ERROR: Dealing with transactions to database: " + str(error) + "\n"
    return "SUCCESS: Mappings created successfully\n"

def processMismatchList(mismatchList):
    '''
    This function posts version mismatches between artifacts and the latest iso bom to the DB
    It ensures a mapping table is kept updated to only contain the latest mismatches overwriting
    any that are from previous boms.
    '''
    supportedBOMProduct = config.get('DEPMODEL', 'supported_bom_products')
    mismatches = mismatchList.split(",")
    for mismatch in mismatches:
        try:
            groupId,artifactId,resolvedVersion,correctVersion,package,product,intendedDrop,repoName = mismatch.split(":")
        except Exception as error:
            errMsg = "Issue with spliting mismatch: " +str(error)
            logger.error(str(errMsg))
            return "ERROR: " + errMsg  + " \n"
        if str(product) == str(supportedBOMProduct):
            isoObject = getISOBuildFromProductSet(intendedDrop,product)
            if isoObject == None:
                return "WARNING: Cannot Find Passed Media Artifact Version From '" + str(product) + "' Product Set for intended Drop '" + str(intendedDrop) +"' .\n"
        else:
            return "WARNING: This service does not support the selected product: '" + str(product) + "'.\n"
        try:
            with transaction.atomic():
                try:
                    artifact = Artifact.objects.get(name=artifactId)
                except:
                    artifact = Artifact(name=artifactId)
                    artifact.save()

                try:
                    artifactVersion = ArtifactVersion.objects.only('version','bomversion').get(artifact=artifact, groupname=groupId, bomcreatedartifact=True)
                    artifactVersion.version = resolvedVersion
                    artifactVersion.bomversion = correctVersion
                    artifactVersion.save()
                except:
                    artifactVersion = ArtifactVersion(artifact=artifact, groupname=groupId, version=resolvedVersion, bomcreatedartifact=True, bomversion=correctVersion, reponame=repoName)
                    artifactVersion.save()

                try:
                    requiredPackageObjField = ('id',)
                    packageObj = Package.objects.only(requiredPackageObjField).values(*requiredPackageObjField).get(name=package)
                    try:
                        mapping = ArtVersToPackageToISOBuildMap.objects.only('isobuild_version').get(artifact_version=artifactVersion, package_id=packageObj['id'])
                        mapping.isobuild_version = isoObject
                        mapping.save()
                    except:
                        ArtVersToPackageToISOBuildMap.objects.create(artifact_version=artifactVersion, package_id=packageObj['id'], isobuild_version=isoObject)
                except:
                    if not ArtVersToPackageToISOBuildMap.objects.filter(artifact_version=artifactVersion, isobuild_version=isoObject).exists():
                        ArtVersToPackageToISOBuildMap(artifact_version=artifactVersion, isobuild_version=isoObject).save()

        except IntegrityError as error:
            return "ERROR: Dealing with transactions to database: " + str(error) + "\n"
    return "SUCCESS: Mismatches created successfully\n"

def processEmptyList(emptyList):
    '''
    This function cleans artifacts from both the mapping table and the artifact version table when the rest call
    is passed a list containing just the repo & package as this means that their are no dependency mismatches in that
    repo for the latest bom
    '''
    supportedBOMProduct = config.get('DEPMODEL', 'supported_bom_products')
    emptyItems = emptyList.split(",")
    for emptyItem in emptyItems:
        try:
            product, intendedDrop, repoName, package = emptyItem.split(':')
        except Exception as error:
            errMsg = "Issue with spliting emptyList: " +str(error)
            logger.error(str(errMsg))
            return "ERROR: " + errMsg  + " \n"
        if str(product) == str(supportedBOMProduct):
            isoObject = getISOBuildFromProductSet(intendedDrop,product)
            if isoObject == None:
                return "WARNING: Cannot Find Passed Media Artifact Version From '" + str(product) + "' Product Set for intended Drop '" + str(intendedDrop) +"' .\n"
        else:
            return "WARNING: This service does not support the selected product: '" + str(product) + "'.\n"
        try:
            with transaction.atomic():
                if not package:
                    ArtVersToPackageToISOBuildMap.objects.filter(artifact_version__bomcreatedartifact=True, artifact_version__reponame=repoName).delete()
                    ArtifactVersion.objects.filter(bomcreatedartifact=True, reponame=repoName).delete()
                else:
                    ArtVersToPackageToISOBuildMap.objects.filter(artifact_version__bomcreatedartifact=True, artifact_version__reponame=repoName, package__name=package).delete()
                    ArtifactVersion.objects.filter(bomcreatedartifact=True, reponame=repoName).delete()
        except IntegrityError as error:
            return "ERROR: Dealing with transactions to database: " + str(error) + "\n"
    return "SUCCESS: Mismatches removed successfully\n"

def getISOBuildFromProductSet(intendedDrop,product):
    '''
    This function returns the latest iso version in a given drop and product
    '''
    requiredproductSetObjField = ('id',)
    requiredDropObjField = ('id','release__id',)
    requiredAllVersionsField = ('status__state','version',)
    requiredContentFields = ('mediaArtifactVersion__mediaArtifact__name','mediaArtifactVersion__version',)
    lastPassed = None
    isoObject = []
    try:
        (returnProduct,drop) = str(getIntendedDropInfo(intendedDrop, product)).split(":")
        productSetObj = ProductSet.objects.only(requiredproductSetObjField).values(*requiredproductSetObjField).get(name=product)
        product = ProductSetRelease.objects.prefetch_related('release__product').filter(productSet_id=productSetObj['id'])[0].release.product
        dropObj = Drop.objects.only(requiredDropObjField).values(*requiredDropObjField).get(name=drop, release__product=product)
        allVersions = ProductSetVersion.objects.only(requiredAllVersionsField).values(*requiredAllVersionsField).filter(drop_id=dropObj['id'],productSetRelease__release_id=dropObj['release__id']).order_by('-id')
        for item in allVersions:
            if item['status__state'] == 'passed' or item['status__state'] == 'passed_manual':
                lastPassed = str(item['version'])
                break

        productSetRelObj = ProductSetRelease.objects.only(requiredproductSetObjField).values(*requiredproductSetObjField).get(productSet_id=productSetObj['id'],release_id=dropObj['release__id'])
        productSetVersionObj = ProductSetVersion.objects.only(requiredproductSetObjField).values(*requiredproductSetObjField).get(version=lastPassed,productSetRelease_id=productSetRelObj['id'])
        contents = ProductSetVersionContent.objects.only(requiredContentFields).values(*requiredContentFields).filter(productSetVersion_id=productSetVersionObj['id'])
        for item in contents:
            if "ericenm" in str(item['mediaArtifactVersion__mediaArtifact__name']).lower():
                isoObject = ISObuild.objects.get(mediaArtifact__name=item['mediaArtifactVersion__mediaArtifact__name'], version=item['mediaArtifactVersion__version'])
                break
    except Exception as error:
        logger.error("ERROR: Issue with getting Media Artifact Version From Product Set - " +str(error))
        isoObject = None
    return isoObject

def createPackageArtifactMapping(repo, rpms):
    """
    This function creates mappings between Package, Artifacts and Repo
    """
    for rpm in rpms:
        if Package.objects.filter(name=rpm['name']).exists():
            pkg = Package.objects.get(name=rpm['name'])
            pkgId = pkg.id
            if pkg.git_repo != repo:
                pkg.git_repo = repo
        else:
            result = "Error: Package name does not exist"
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        for artifact in rpm['artifacts']:
            if Artifact.objects.filter(name=artifact['name']).exists():
                artifact = Artifact.objects.get(name=artifact['name'])
                if artifact.package_id != pkgId:
                    artifact.package_id = pkgId
                    artifact.save()
            else:
                Artifact.objects.create(name=artifact['name'], package_id=pkgId)
        pkg.save()
    result = "Success: Mappings created successfully"
    return Response(result, status=status.HTTP_201_CREATED)
