import logging
logger = logging.getLogger(__name__)
from cireports.models import *
from depmodel.models import *
from depmodel.utils import *
from cireports.models import *
from django.shortcuts import render
from collections import defaultdict
from django.http import HttpResponse
import json
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import HttpResponse, Http404, HttpResponseRedirect
import utils
import threading
import multiprocessing
from ciconfig import CIConfig
config = CIConfig()

def dependencyTree(request,product,package,version):
    '''
    The dependencyTree function finds  all dependencies associated with a particular package and version
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"

    packageObj = Package.objects.get(name=package)

    dependencyList = {}
    list = []
    dependencyTree = []
    scopedDependencyList = {}
    artifactVersion = None
    indent = 3 
 
    if Artifact.objects.filter(name=package).exists():
        pkg = Artifact.objects.get(name=package)
        if ArtifactVersion.objects.filter(artifact=pkg,version=version).exists():
            artifactVersion = ArtifactVersion.objects.get(artifact=pkg,version=version)
            '''
            List all dependencies
            '''
            package = artifactVersion.id
            dependency(package,package,version,dependencyList,list)
            '''
            List all dependencies with associated scope
            '''
            dependencyScope(dependencyList,scopedDependencyList)
            if scopedDependencyList != {}:
                dependent = scopedDependencyList[package]
                '''
                Orders list with indent for dispalying on webpage
                '''
                dependencyTreeIndent(dependent,package,scopedDependencyList,dependencyTree,indent)
    return render(request, "depmodel/dependency_table.html",
            {
                'product': product,
                'femObj': femObj,
                'package': packageObj,
                'version': version,
                'dependencyTree': dependencyTree,
                'artifactVersion': artifactVersion,
            })

def dependency(parent,package,version,dependencyList,list):
    '''
    The dependency function finds all dependencies associated with an artifact and stores them in a dict
    '''
    artifactVersion = ArtifactVersion.objects.get(id=package)
    dependencyMapping = Mapping.objects.filter(artifact_main_version=artifactVersion.id)
    if parent in list:
        dependencyList[parent][package] = artifactVersion
    else:
        dependencyList[parent] = {package:artifactVersion}
        list.append(parent)

    for artifact in dependencyMapping:
        parent = artifact.artifact_main_version.id
        package = artifact.artifact_dep_version.id
        version = artifact.artifact_dep_version.version
        dependency(parent,package,version,dependencyList,list)


def dependencyTreeIndent(dependent,package,dependencyList,dependencyTree,indent):
    '''
    Function that adds information to dependencies to allow for indent
    '''
    for entry,value,scope,buildFlag in dependent:
        if entry != package:
            dependencyTree.append([value,scope,indent, buildFlag])
            if entry in dependencyList:
                dependencyTreeIndent(dependencyList[entry],entry,dependencyList,dependencyTree,indent+5)

def dependencyScope(dependencyList,scopedDependencyList):
    '''
    Function finds scopes associated with artifact and adds them to scopedDependencyList
    '''
    for parent,value in dependencyList.items():
        for package,artifactVersion in value.items():
            if parent != package:
                dependency = Mapping.objects.filter(artifact_main_version=parent,artifact_dep_version=package)
                for mapping in dependency:
                    if mapping.build is True:
                        buildFlag=True
                    else:
                        buildFlag=False

                    if parent in scopedDependencyList:
                        scopedDependencyList[parent].append([package,artifactVersion,mapping.scope,buildFlag])
                    else:
                        scopedDependencyList[parent] = []
                        scopedDependencyList[parent].append([package,artifactVersion,mapping.scope,buildFlag])            

def storeDependencyRest(request,package,version):
    ret = storeDependency(package,version)
    return HttpResponse(ret, content_type="application/json")

def returnDependencyRest(request,artifact,version):
    ret = returnDependency(artifact,version) 
    return HttpResponse(ret, content_type="application/json")

def returnCompleteDependencyRest(request,artifact,version):
    ret = returnCompleteDependency(artifact,version) 
    return HttpResponse(ret, content_type="application/json")

def showPackageDependenciesMap(request, package,version):
    '''
    Return package dependency map for artifact.
    '''
    return render(request,"depmodel/showPackageDependenciesMap.html", {'package': package, 'version': version})

def showPackageCompleteDependenciesMap(request, package,version):
    '''
    Return package dependency map for artifact.
    '''
    return render(request,"depmodel/showPackageCompleteDependenciesMap.html", {'package': package, 'version': version})


@csrf_exempt
def restProcessArtifactsList(request):
    '''
    The restProcessArtifactsList processes a list of artifacts for dependency mapping
    The format of the input is an encoded list, list contents are : seperated
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")

    if request.method == 'POST':
        artifacts = request.POST.get("artifacts")
        try:
           message =  utils.processAllBuildTimeArtifacts(artifacts)
        except Exception as e:
            logger.error("Issue in with processArtifactsList function: " +str(e))
            return HttpResponse("Issue in with processArtifactsList function: " +str(e) + "\n")
        if "Error" in message:
            return HttpResponse("ERROR: " +str(message) + "\n")
        else:
            return HttpResponse("Successfully Updated Artifact Mapping Table with Build Flag\n")

@csrf_exempt
def restProcessReleaseTimeDependencies(request):
    '''
    The restProcessReleaseTimeDependencies calls the storeDependency fuction which processes dep mapping at Artifact Level
    '''
    #Temp fix to stop overloading of http/mysql in portal
    return HttpResponse("Done")
    artifactName = version = None
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")

    if request.method == 'POST':
        artifactName = request.POST.get("packageName")
        version = request.POST.get("version")
        if not artifactName or artifactName == None:
            return HttpResponse("ERROR: Artifact Name does not Exist restProcessReleaseTimeDependencies failed")
        if not version or version == None:
            return HttpResponse("ERROR: Artifact Version does not Exist restProcessReleaseTimeDependencies failed")
    try:
        storeDependencyParentObj = threading.Thread(target=storeDependencyParent, args=(artifactName,version))
        storeDependencyParentObj.start()
        return HttpResponse("Done")
    except Exception as e:
        errorMessage = "Error: Issue in storeDependency function on Artifact Name: " + str(artifactName) + " Artifact Version: " + str(version) + " Error: " +str(e)
        logger.error(errorMessage)
        return HttpResponse(errorMessage)

def storeDependencyParent(artifactName,version):
    logger.info("Starting processing dependencies thread for: "+str(artifactName)+"_"+str(version))
    storeDependencyObj = multiprocessing.Process(target=storeDependency, args=(artifactName,version))
    storeDependencyObj.daemon=True
    storeDependencyObj.start()
    try:
        threadTimeout = int(config.get("CIFWK", "threadTimeout"))
        storeDependencyObj.join(threadTimeout)
    except Exception as e:
        logger.error("Issue processing dependencies thread for: "+str(artifactName)+"_"+str(version))

    # If thread is still active
    if storeDependencyObj.is_alive():
        logger.error("Timeout processing dependencies thread for: "+str(artifactName)+"_"+str(version))
        storeDependencyObj.terminate() 
    logger.info("Completed processing dependencies thread for: "+str(artifactName)+"_"+str(version))

def showDependencyStack(request, product, artifact, artifactVersion, artifactType):
    '''
    The showDependencyStack function calls the returnStackedDependencies from depmodels/utils
    which returns the dependent artifacts on this artifacts, Names, Build Jars and 3PP's.
    Theses are then displayed on the dependency Stack Chart on the UI
    '''
    artifactNameList = artifactBuildDict = artifactThirdPartyList = None
    doesNotExistFlag = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
     
    if Package.objects.filter(name=artifact).exists():
        artifactObj = Package.objects.get(name=artifact)
    else:
        doesNotExistFlag = "doesNotExist"

    if PackageRevision.objects.filter(package=artifactObj, version=artifactVersion, m2type=artifactType).exists():
        artifactVersionObj = PackageRevision.objects.get(package=artifactObj, version=artifactVersion, m2type=artifactType)
    else:
        doesNotExistFlag = "doesNotExist"
    if PackageDependencies.objects.filter(package=artifactVersionObj).exists():
        packageDependencyObj = PackageDependencies.objects.get(package=artifactVersionObj)
    else:
        doesNotExistFlag = "doesNotExist"

    if doesNotExistFlag == None:
        try:
            artifactNameList, artifactBuildDict, artifactThirdPartyList = returnStackedDependencies(artifactObj,artifactVersionObj,packageDependencyObj)
        except Exception as e:
            logger.error("Issue with returning dependencies for Artifact: " + str(artifact) + " With Error: " + str(e))
    return render(request, "depmodel/dependencyStack_table.html",
            {
                "doesNotExistFlag": doesNotExistFlag,
                "artifact": str(artifactObj) + "_" + str(artifactVersionObj.version),
                "artifactVersion": artifactVersion,
                "artifactNameList":artifactNameList,
                "artifactBuildDict" : artifactBuildDict,
                "artifactThirdPartyList": artifactThirdPartyList,
                "product": product,
                "femObj": femObj
            }
         )

def showPackageDependenciesStackISO(request, product, drop, ISOArtfactName, ISOArtifactVersion):
    '''
    The showPackageDependenciesStackISO function is used to return an ISO build dependencies which will be
    dispalyed on a D3 stack chart on the CIFWk UI. This function calls the depmodel utils returnStackISODependencies
    which which returns nodeString and edgeString strings which is turn returned to the Stack chart which displays the dependency data
    '''

    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"  
    try:
        doesNotExistFlag, nodeString, edgeString = returnStackISODependencies(drop, ISOArtfactName, ISOArtifactVersion)
    except Exception as error:
        logger.error("Error in building up ISO Stack Dependencies: " +str(error))

    return render(request, "depmodel/dependencyStackISO_table.html",
            {
                "doesNotExistFlag": doesNotExistFlag,
                "artifact": str(ISOArtfactName) + "_" + str(ISOArtifactVersion),
                "artifactVersion": ISOArtifactVersion,
                "nodeString":nodeString,
                "edgeString" : edgeString,
                "product": product,
                "femObj": femObj
            }
         ) 

