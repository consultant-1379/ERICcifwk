from distutils.version import LooseVersion
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import RequestContext
from django.core.validators import validate_email
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Min, Q
from django.db import connection,transaction, IntegrityError
from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ciconfig import CIConfig
from django.utils.datastructures import SortedDict


config = CIConfig()
import json
from django.shortcuts import render
import datetime
import ast
import re
import os
import tarfile
import urllib
import urllib2
from threading import Thread
from cireports.models import *
from avs.models import *
import logging
logger = logging.getLogger(__name__)
import cireports.prim
from cireports.common_modules.common_functions import getVersion
from cireports.common_modules.common_functions import convertRStateToVersion as convertRStateToVersion
import utils
from django.core.mail import send_mail
from datetime import datetime
from cireports.forms import *
from django.contrib.auth.models import User, Group
from guardian.decorators import permission_required, permission_required_or_403
from guardian.conf import settings as guardian_settings
from guardian.exceptions import GuardianError
from guardian.shortcuts import assign
from guardian.shortcuts import get_perms
from guardian.core import ObjectPermissionChecker
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.core.management import call_command
from StringIO import StringIO
from django.core.cache import cache
import hashlib
from django.utils.http import urlquote
import lockfile
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.gzip import gzip_page
import csv
from django.utils.encoding import smart_str
from dmt.models import DeploymentUtilsToISOBuild, DeploymentUtilsToProductSetVersion
from fwk.utils import pageHitCounter
import requests
import time
from cireports.DGThread import DGThread
from cireports.cloudNativeUtils import getCNBuildLogDataByDrop



@csrf_exempt
def makeRestDeliveryToDrop(request):
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        packageName = request.POST.get("packageName")
        version = request.POST.get('version')
        drop = request.POST.get('drop')
        email = request.POST.get('email')
        product = request.POST.get('product')
        platform = request.POST.get('platform')
        m2type = request.POST.get('type')
        dropName = "NONE"

    dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if packageName is None or not packageName or packageName == "None":
        return HttpResponse("Error: Package name required.\n")
    if version is None or not version or version == "None":
        return HttpResponse("Error: Version required.\n")
    if drop is None or not drop or drop == "None":
        return HttpResponse("Error: Drop required.\n")
    if email is None or not email or email == "None":
        return HttpResponse("Error: Email address required.\n")
    if product is None or not product or product == "None":
        return HttpResponse("Error: product required.\n")
    if platform is None or not platform or platform == "None":
        if product == "OSS-RC":
            return HttpResponse("Error: Package Platform is required\n.")
        else:
            platform = "None"

    versionAsString = str(version)
    if "R" in versionAsString:
         version = convertRStateToVersion(versionAsString)

    if product.lower() == "enm":
        return HttpResponse("Product: " +str(product)+ " is not permitted to use this service.")

    if not PackageRevision.objects.filter(artifactId=packageName, version=version, platform=platform).exists():
        return HttpResponse(packageName + " version " + version + " does not exist. Check package details and ensure package is in CI-Fwk DB.\n")
    if not Product.objects.filter(name=product).exists():
        return HttpResponse("Error: Product " + product + " does not exist.\n")

    try:
        productObj = Product.objects.get(name=product)
        if "auto" not in drop:
            if "latest" in drop:
                delivery = "true"
                dropInfo =  utils.getIntendedDropInfo(drop, productObj.name, delivery)
                if "error" in dropInfo:
                    return HttpResponse("Error: While requiring Latest Drop using " + str(drop) + " - " + str(dropInfo) + "\n")
                dropObj = Drop.objects.get(name=dropInfo,release__product=productObj)
            else:
                dropObj = Drop.objects.get(name=drop,release__product=productObj)
            dropName = str(dropObj.name)
        else:
            dropName = "auto"
    except Drop.DoesNotExist:
        return HttpResponse("Error: Drop " + drop + " does not exist for " + product + ".\n")
    try:
        if m2type == None:
            #get defaults
            defaults = {'TOR':'rpm','OSS-RC':'pkg','LITP':'rpm','CI':'zip','CSL-MEDIATION':'rpm','OM':'pkg','SECURITY':'zip','COMINF':'zip'}
            try:
                type=defaults[str(product).upper()]
            except:
                logger.error("no default for product")
                type='rpm';
        else:
            type=m2type
        deliveryResult = utils.performDelivery2(str(packageName), str(version), type, dropName, str(product), str(email), str(platform))
        resultSummary = "Delivery Summary for artifact " + packageName + " version: " + version + " on platform "+ platform
        try:
            deliveryResultList=deliveryResult.split(",")
            for result in deliveryResultList:
                if result == "":
                    continue
                if "ERROR" in result:
                    resultSummary = resultSummary +"\n ERROR: Unspecified delivery failure "+str(result)
                if "INDROP" in result:
                    resultDrop = result.replace("INDROP","")
                    resultSummary = resultSummary +"\n ERROR: Artifact already in drop "+str(resultDrop)
                if "FROZEN" in result:
                    resultDrop = result.replace("FROZEN","")
                    resultSummary = resultSummary +"\n ERROR: Attempt to deliver to frozen drop "+str(resultDrop)
                if "NOTOPEN" in result:
                    resultDrop = result.replace("NOTOPEN","")
                    resultSummary = resultSummary +"\n ERROR: Attempt to deliver to drop that is not open "+str(resultDrop)
                if "DELIVERED" in result:
                    dontCare,dontCare,resultDropId = result.split(":")
                    dropObj = Drop.objects.get(id=resultDropId)
                    resultDrop = str(dropObj.name)
                    resultSummary = resultSummary +"\n SUCCESS: artifact delivered to drop "+str(resultDrop)
        except Exception as e:
            logger.error("issue with artifact delivery " +str(e))
            resultSummary = resultSummary +"\n ERROR: Unspecified delivery failure: "+str(e)
        return HttpResponse(str(resultSummary))


    except Exception as e:
        logger.error("There was and issue delivering package: " +str(packageName)+ " version: " +str(version)+ " with platform: " +str(platform)+ " to drop: " +str(dropName)+ " Error thrown: " +str(e))
        return HttpResponse("There was and issue delivering package: " +str(packageName)+ " version: " +str(version)+ " with platform: " +str(platform)+ " to drop: " +str(dropName)+ " Error thrown: " +str(e))

@csrf_exempt
@transaction.atomic
def restImportTestwareToCiFwk(request):
    '''
    REST call to add a testware artifact and testware revision to the Database
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        taName          = request.POST.get("testwareArtifact")
        desc            = request.POST.get("description")
        version         = request.POST.get('version')
        groupId         = request.POST.get('groupId')
        signum          = request.POST.get('signum')
        execVer         = request.POST.get('execVer')
        execGroupId     = request.POST.get('execGroupId')
        execArtifactId  = request.POST.get('execArtifactId')
    dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if taName is None or not taName or taName == "None":
        return HttpResponse("Error: Testware Artifact Name required\n")
    if version is None or not version or version == "None":
        return HttpResponse("Error: Version number required\n")
    if groupId is None or not groupId or groupId == "None":
        return HttpResponse("Error: Group ID required\n")
    if signum is None or not signum or signum == "None":
        return HttpResponse("Error: Signum required\n")
    if execVer is None or not execVer or execVer == "None":
        return HttpResponse("Error: Execution Version required\n")
    if execGroupId is None or not execGroupId or execGroupId == "None":
        return HttpResponse("Error: Execution Group Id required\n")
    if execArtifactId is None or not execArtifactId or execArtifactId == "None":
        return HttpResponse("Error: Execution Artifact Id required\n")
    taNumber = taName.split("_")[-1]
    versionAsString = str(version)
    if "-SNAPSHOT" in versionAsString:
            return HttpResponse("Snapshot Versions are not stored in the Database \n")
    if "R" in versionAsString:
        version = convertRStateToVersion(versionAsString)
    if not TestwareArtifact.objects.filter(name=taName, artifact_number=taNumber).exists():
        if TestwareArtifact.objects.filter(artifact_number=taNumber).exists():
            return HttpResponse("Error: A Test Artifact with the number " + taNumber + " already exists under a different name\n")
        if not re.match(r'^ERICTAF[a-zA-Z0-9\-]+_[A-Z]{3}[0-9]{7}$|^ERICTW[a-zA-Z0-9\-]+_[A-Z]{3}[0-9]{7}$',taName):
            return HttpResponse("Testware Name is Incorrect. It should be in the format: Testware Artifact Name,  upper case letters (ERICTAF or ERICTW), upper or lower case letters, Underscore (_), 3 upper case letters (CXP) and seven digits. \nExample: ERICTAFpackageName_CXP1234567 or ERICTWFpackageName_CXP1234567. \nPlease update packageName and try again.\n")

        try:
            with transaction.atomic():
                newTa = TestwareArtifact(name=taName, artifact_number=taNumber, description=desc, signum=signum)
                newTa.save()
                taId = newTa.id
        except IntegrityError as e:
            logger.error(str(e))
    else:
        existingTa = TestwareArtifact.objects.get(name=taName, artifact_number=taNumber)
        taId = existingTa.id
    if TestwareRevision.objects.filter(testware_artifact__name=taName, version=version).exists():
        return HttpResponse("Error: Testware Revision : " + taName + " version: " + version +" already exists\n")
    else:
        try:
            with transaction.atomic():
                testwareRevision = TestwareRevision(testware_artifact_id=taId, artifactId=taName, version=version, date_created=dateCreated, groupId=groupId, execution_version=execVer, execution_groupId=execGroupId, execution_artifactId=execArtifactId, kgb_status=1)
                testwareRevision.save()
                return HttpResponse("Testware revision " + taName + " version " + version + " was imported on " + dateCreated + "\n")
        except IntegrityError as e:
            logger.error("There was an issue creating a new testware revision entry in the CIFWK DB, Error: " +str(e))
            return HttpResponse("Testware revision " + taName + " version " + version + " was not added to the CIFWK Database, Error thrown: " +str(e))

def testwareStatus(request, product, ID):
    product = Product.objects.get(name=product)
    obj= TestwareRevision.objects.get(id=ID)
    if obj.cdb_status == 1:
        obj.cdb_status = 0
    else:
        obj.cdb_status = 1
    obj.save()
    artifact = TestwareArtifact.objects.get(name=obj.testware_artifact.name)
    return HttpResponseRedirect("/"+str(product.name)+"/testware/showall/"+str(artifact))

@csrf_exempt
@transaction.atomic
def restImportPackageToCiFwk(request):
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        packageName = request.POST.get("packageName")
        version = request.POST.get('version')
        groupId = request.POST.get('groupId')
        signum = request.POST.get('signum')
        m2Type = request.POST.get('m2Type')
        intendedDrop = request.POST.get('intendedDrop')
        product = request.POST.get('product')
        repository = request.POST.get('repository')
        platform = request.POST.get('platform')
        category = request.POST.get('mediaCategory')
        mediaPath = request.POST.get('mediaPath')
        nonProtoBuild = request.POST.get('nonProtoBuild')
        autoDeliver = request.POST.get('autoDeliver')
        isoExclude = request.POST.get('isoExclude')
        imageContentJSON = request.POST.get('imageContentJSON')
        infraPkg = request.POST.get('infra')
        type3pp = request.POST.get('type3pp')

    if str(type3pp).lower() == 'true':
        type3pp = True
    dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if packageName is None or not packageName or packageName == "None":
        return HttpResponse("Error: Package name required\n")
    if "testware" in str(category):
        if not re.match(r'^ERICTAF[a-zA-Z0-9\-]+_[A-Z]{3}[0-9]{7}$|^ERICTW[a-zA-Z0-9\-]+_[A-Z]{3}[0-9]{7}$', packageName):
            return HttpResponse("Testware Name is Incorrect. It should be in the format: Testware Artifact Name, upper case letters (ERICTAF or ERICTW), upper or lower case letters, Underscore (_), 3 upper case letters (CXP) and seven digits. \nExample: ERICTAFpackageName_CXP1234567 or ERICTWpackageName_CXP1234567. \nPlease update packageName and try again.\n")
        if len(packageName) > 50:
            return HttpResponse("Testware name length should not be more than 50 characters.\nPlease update testware name and try again.\n")
        tafPackagingType = str(config.get("CIFWK", "tafPackagingType"))
        if ("ERICTAF" in str(packageName)) and (tafPackagingType != str(m2Type)):
            m2Type = tafPackagingType
    elif "3pp" not in str(category) and type3pp != True:
        if PackageNameExempt.objects.filter(name=packageName).exists():
            if not re.match(r'^[a-zA-Z0-9\.\-]+_(?:[A-Z]{3}[0-9]{7}|APR901[0-9]{3})$', packageName):
                return HttpResponse("Package Name is Incorrect. It should be in the format: Artifact Name upper or lower case letters, Underscore (_), 4 upper case letters, and seven digits. \nExample: packageName_APR1234569 or ERICpackageName_CXP1234567.\nFor older APR901 artifacts six digits at end of packageName is allowed eg: ERICpackageName_APR901123. \nPlease update packageName and try again.\n")
        elif not re.match(r'^[a-zA-Z0-9\-]+_(?:[A-Z]{3}[0-9]{7}|APR901[0-9]{3})$', packageName):
            return HttpResponse("Package Name is Incorrect. It should be in the format: Artifact Name upper or lower case letters, Underscore (_), 4 upper case letters, and seven digits. \nExample: packageName_APR1234569 or ERICpackageName_CXP1234567.\nFor older APR901 artifacts six digits at end of packageName is allowed eg: ERICpackageName_APR901123. \nPlease update packageName and try again.\n")
        if len(packageName) > 50:
            return HttpResponse("Package name length should not be more than 50 characters.\nPlease update package name and try again.\n")
    if version is None or not version or version == "None":
        return HttpResponse("Error: Version number required\n")
    if groupId is None or not groupId or groupId == "None":
        return HttpResponse("Error: Group ID required\n")
    if signum is None or not signum or signum == "None":
        return HttpResponse("Error: Signum required\n")
    if m2Type is None or not m2Type or m2Type == "None":
        return HttpResponse("Error: M2 Type required\n")
    if intendedDrop is None or not intendedDrop or intendedDrop == "None":
        return HttpResponse("Error: Intended Drop required\n")
    if product is None or not product or product == "None":
        return HttpResponse("Error: Product required\n")
    if repository is None or not repository or repository == "None":
        return HttpResponse("Error: Nexus Repository is required\n")
    if mediaPath is None or not mediaPath or mediaPath == "None":
       mediaPath = None;
    if isoExclude is None or not isoExclude or isoExclude == "None":
       isoExclude = False
    elif isoExclude.lower() == 'true':
       isoExclude = True
    else:
       isoExclude = False
    if platform is None or not platform or platform == "None":
        if product == "OSS-RC" and "testware" != str(category):
            return HttpResponse("Error: Package Platform is required\n.")
        else:
            platform = "None"
    else:
        platform = platform.lower()

    if autoDeliver is None or not autoDeliver or autoDeliver == "None":
        autoDeliver = False
    elif autoDeliver.lower() == "true":
        autoDeliver = True
    else:
        autoDeliver = False

    if nonProtoBuild is None or not nonProtoBuild or nonProtoBuild == "None":
        nonProtoBuild = "true"

    if infraPkg is None or not infraPkg or infraPkg == "None":
       infraPkg = False
    elif infraPkg.lower() == 'true':
       infraPkg = True
    else:
       infraPkg = False

    validPackagingTypes = config.get("CIFWK", "validPackagingTypes")
    if not m2Type in validPackagingTypes:
        return HttpResponse("Error: Invalid m2Type.  Valid packaging types are: " +str(validPackagingTypes)+ "\n")

    category = utils.mediaCategoryCheck(category)
    if "Error" in str(category):
        return HttpResponse(category)

    intendedDropInfo =  utils.getIntendedDropInfo(intendedDrop, product)
    if "error" in intendedDropInfo:
        return HttpResponse("Error: Problem While Requiring Intended Drop Information - "+ str(intendedDropInfo)+"\n")

    if "3pp" in str(category):
        packageNumber = packageName
    else:
        packageNumber = packageName.split("_")[-1]
    versionAsString = str(version)
    if "-SNAPSHOT" in versionAsString:
        return HttpResponse("Warning: Snapshot Versions are not stored in the Database \n")
    if "R" in versionAsString:
        version = convertRStateToVersion(versionAsString)
    if not Package.objects.filter(name=packageName, package_number=packageNumber).exists():
        if Package.objects.filter(package_number=packageNumber).exists():
            return HttpResponse("Error: A package with the number " + packageNumber + " already exists under a different name\n")
        if product == "ENM":
            return HttpResponse("Error: No package " + packageName + " with the number " + packageNumber + " exists for ENM.\nPlease create package.\n")
        try:
            with transaction.atomic():
                if "testware" in str(category):
                    newPackage = Package(name=packageName, package_number=packageNumber, signum=signum, testware=True)
                else:
                    newPackage = Package(name=packageName, package_number=packageNumber, signum=signum)
                newPackage.save()
                utils.mapProductToPackage(intendedDropInfo,newPackage)
                utils.sendPackageMail(packageName)
        except IntegrityError as e:
            logger.error(str(e))
        packageId = newPackage.id
    else:
        existingPackage = Package.objects.get(name=packageName, package_number=packageNumber)
        packageId = existingPackage.id

    if PackageRevision.objects.filter(package__name=packageName, version=version, platform=platform, m2type=m2Type, category=category).exists():
        return HttpResponse("Error: Package revision: " + packageName + " version: " + version +" type: " +str(m2Type) +" category type: " + str(category) + " already exists\n")
    else:
        artifactSizeProducts = config.get("CIFWK", "artifactSizeProducts")
        artifactSize = 0
        if product in artifactSizeProducts:
            artifactSize, statusCode = utils.getArtifactSize(packageName, version, groupId, m2Type, repository)
            if statusCode == 200:
                artifactSize = int(artifactSize)
            else:
                logger.error("Error: There was an issue creating a new package Revision entry in the CIFWK DB, Error: " +str(artifactSize))
                return HttpResponse("Package revision " + packageName + " version " + version + " with the platform "+ platform + " was not imported, Error thrown: " +str(artifactSize))
        try:
            with transaction.atomic():
                packageRevision = PackageRevision(package_id=packageId, artifactId=packageName, version=version, date_created=dateCreated, groupId=groupId, m2type=m2Type, non_proto_build=nonProtoBuild, autodrop=intendedDropInfo, arm_repo=repository, platform=platform, category=category, media_path=mediaPath, autodeliver=autoDeliver, isoExclude=isoExclude,infra=infraPkg,size=artifactSize)
                packageRevision.save()
                if imageContentJSON is not None and imageContentJSON != "None":
                    storeImageContents(packageRevision.id, imageContentJSON)
                return HttpResponse("Package: " + packageName + " Version: " + version + " Type: " +str(m2Type) + " with Platform: "+ platform + " (Auto deliver after KGB: "+ str(autoDeliver) + ") was imported on " + dateCreated + "\n")
        except IntegrityError as e:
            logger.error("Error: There was an issue creating a new package Revision entry in the CIFWK DB, Error: " +str(e))
            return HttpResponse("Package revision " + packageName + " version " + version + " with the platform "+ platform + " was not imported, Error thrown: " +str(e))

@csrf_exempt
def restISOcontentOnly(request):
    '''
    ISO content Only REST interface
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        drop = request.POST.get('drop')
        release = request.POST.get('release')
        product = request.POST.get('product')
        grpId = request.POST.get('groupId')
        artId = request.POST.get('artifactId')
        repoName = request.POST.get('repo')
        platform = request.POST.get('platform')
        logger.info("Information Given: drop - "+str(drop)+ " release - " +str(release) + " product - " + str(product)+ "  platform - " +str(platform))

        if release is None or not release or release == "None":
            logger.error("Error: Release required.\n")
            return HttpResponse("Error: Release required.\n")
        if product is None or not product or product == "None":
            logger.error("Error: Product required.\n")
            return HttpResponse("Error: Product required.\n")

        creatingISOcontentResult = utils.createISOcontentListInDB(str(drop), str(product), str(release), str(platform))
        if "Error" in creatingISOcontentResult:
            logger.error("There was an issue creating a record of the ISO Content in the CIFWK DB: " +str(creatingISOcontentResult))
            return HttpResponse("Product " + str(product)  + " Release " + str(release) + " for Drop "+ str(drop) + " ISO content was not created in the CI Fwk DB:\n " +str(creatingISOcontentResult))
        else:
            return HttpResponse("For Product " + str(product) + " | Release " + str(release) + " | Drop " + str(drop) + " : " + str(creatingISOcontentResult))

@csrf_exempt
def restDeleteISOcontentOnly(request):
    '''
       To Delete ISO content Only REST interface when job Fails
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        drop = request.POST.get('drop')
        release = request.POST.get('release')
        product = request.POST.get('product')
        logger.info("Information Given: drop - "+str(drop)+ " release - " +str(release) + " product - " + str(product))

        if release is None or not release or release == "None":
            logger.error("Error: Release required.\n")
            return HttpResponse("Error: Release required.\n")
        if product is None or not product or product == "None":
            logger.error("Error: Product required.\n")
            return HttpResponse("Error: Product required.\n")
        if drop is None or not drop or drop == "None":
            logger.error("Error: Drop required.\n")
            return HttpResponse("Error: Drop required.\n")

        try:
            deleteISOcontentResult = utils.deleteISOcontentFromDB(str(drop), str(product), str(release))
        except Exception as e:
            logger.error("There was an issue deleting ISO content entry in the CIFWK DB, Error: " +str(e))
            return HttpResponse("There was an issue deleting ISO content entry in the CIFWK DB, Error thrown: " +str(e))

        return HttpResponse("ISO Build Job Failure: checked if needed to delete an ISO Content Entry in Database, in case of ISO wasn't uploaded to Nexus\n")

@csrf_exempt
def restCIFWKMediaImport(request):
    '''
    The restPublishISOAndUpdateCIFWKDB rest function delivers and Artifact (ISO) to Nexus
    then updates the CIFWK DB and in turn the artifact data is presented on the CIFWK UI
    Updates to the CIFWK DB include: Media Artifact, ISO Build and ISO Build mapping updates
    '''
    if request.method == 'GET':
        return HttpResponse("\n Error: This interface accepts HTTP POST requests only.\n")

    if request.method == 'POST':

        dropObj = newMediaArtifactObj = ISOBuildObj = None
        sortedPackages = []
        infoString = ""

        armRepo = request.POST.get('releaseRepoName')
        groupId = request.POST.get('groupId')
        name = request.POST.get('name')
        version = request.POST.get('version')
        product = request.POST.get('product')
        release = request.POST.get('release')
        drop = request.POST.get('drop')
        platform = request.POST.get('platform')
        mediaType = request.POST.get('mediaType')
        category = request.POST.get('category')
        deployType = request.POST.get('deployType')

        if (mediaType == None or mediaType is None or mediaType == "None"):
            mediaType = "iso"

        if mediaType:
            validMediaTypes = [m.type for m in MediaArtifactType.objects.all()]
            if not mediaType in str(validMediaTypes):
                return HttpResponse("\n Error: only accepts 'mediaType' from the following - " + ", ".join(validMediaTypes) + ". Please try again.\n")

        if (category == None or category is None or category == "None"):
           category = "productware"

        if category:
            validMediaCategories = [cat.name for cat in MediaArtifactCategory.objects.all()]
            if not category in str(validMediaCategories):
                return HttpResponse("\n Error: only accepts 'category' from the following - " + ", ".join(validMediaCategories) + ". Please try again.\n")

        if (deployType == None or deployType is None or deployType == "None"):
            deployType = "not_required"

        if deployType:
            validMediaDeployTypes = [dType.type for dType in MediaArtifactDeployType.objects.all()]
            if not deployType in str(validMediaDeployTypes):
                return HttpResponse("\n Error: only accepts 'deployType' from the following - " + ", ".join(validMediaDeployTypes) + ". Please try again.\n")

        if armRepo is None or not armRepo or armRepo == "None":
            return HttpResponse("\n Error: 'armRepo' is required, please try again\n")
        if groupId is None or not groupId or groupId == "None":
            return HttpResponse("\n Error: 'groupId' is required, please try again\n")
        if name is None or not name or name == "None":
            return HttpResponse("\n Error: 'name' is required, please try again\n")
        if version is None or not version or version == "None":
            return HttpResponse("\n Error: 'version' is required, please try again\n")
        if product is None or not product or product == "None":
            return HttpResponse("\n Error: 'product' is required, please try again\n")
        if release is None or not release or release == "None":
            return HttpResponse("\n Error: 'release' is required, please try again\n")
        if drop is None or not drop or drop == "None":
            return HttpResponse("\n Error: 'drop' is required, please try again\n")

        try:
            number = name.split("_")[-1]
        except:
            number = name

        dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        versionAsString = str(version)
        if "R" in str(version):
            version = convertRStateToVersion(versionAsString)
        else:
            version = versionAsString

        try:
            if Drop.objects.filter(name=drop, release__name=release, release__product__name=product).exists():
                dropObj = Drop.objects.get(name=drop, release__name=release, release__product__name=product)
                infoString = infoString + "\n Found Drop Object based on Data Entered " +str(product)+ ":" +str(release)+ ":" +str(drop)+ "\n"
            else:
                return HttpResponse("\n Error: " +str(product)+ ":" +str(release)+ ":" +str(drop)+ " is not Valid, please try again\n")

            categoryObj = MediaArtifactCategory.objects.get(name=category)
            testware = False
            if category == "testware":
                testware = True

            if not MediaArtifact.objects.filter(name=name, number=number).exists():
                deployTypeObj = MediaArtifactDeployType.objects.get(type=deployType)
                newMediaArtifactObj = MediaArtifact.objects.create(name=name, number=number, description="AUTO GENERATED", hide=0, mediaType=mediaType, category=categoryObj, testware=testware, deployType=deployTypeObj)
                infoString = infoString + "\n New Media Artifact Object Created based on Data Entered, as does not already exist: " +str(name)+ "\n"
            else:
                newMediaArtifactObj = MediaArtifact.objects.get(name=name, number=number, category=categoryObj, testware=testware)
                logger.info("Existing Media Object found for: " +str(name))
                infoString = infoString + "\n Existing Media Artifact Object found for: " +str(name)+ "\n"
        except Exception as error:
            logger.error("Error: Thrown in DB Queries New Media Artifact: " +str(error))
            return HttpResponse("\nError: Thrown in DB Queries New Media Artifact: " +str(error)+ "\n")

        try:
            if not ISObuild.objects.filter(version=version, artifactId=name, mediaArtifact=newMediaArtifactObj, groupId=groupId).exists():
                flag=False
                artifactSize=0
                try:
                    checkDropObject=ISObuild.objects.filter(drop=dropObj,mediaArtifact__testware=newMediaArtifactObj.testware, mediaArtifact__category__name=category)[0]
                except:
                    checkDropObject = None
                if checkDropObject is not None:
                    if newMediaArtifactObj==checkDropObject.mediaArtifact:
                        flag=True
                else:
                    flag=True
                if flag==False:
                    infoString = "Existing MediaArtifact: %s not matching with new MediaArtifact: %s . please try again." %(checkDropObject.mediaArtifact, newMediaArtifactObj)
                    logger.info(infoString)
                    return HttpResponse("\n\n"+infoString,status=404)
                else:
                    if product == "ENM":
                        artifact = name
                        mediaArtifact = MediaArtifact.objects.get(name=name)
                        mediaType = mediaArtifact.mediaType
                        artifactSize, statusCode = cireports.utils.getMediaArtifactSize(artifact, version, groupId, mediaType)
                        if statusCode == 200:
                            artifactSize = int(artifactSize)
                        else:
                            logger.debug("Error: There was an issue creating a new Media Revision Size entry in the CIFWK DB, Artifact Size is set to 0.  Error: " +str(artifactSize))
                            artifactSize=0
                    ISOBuildObj = ISObuild.objects.create(version=version, groupId=groupId, artifactId=name, mediaArtifact=newMediaArtifactObj, drop=dropObj, build_date=dateCreated, current_status=None, arm_repo=armRepo, size=artifactSize)
                    infoString = infoString + "\n New ISO Build Object Created based on Data Entered, as does not already exist: %s: %s: %s: \n" %(name, version, drop)
            else:
                logger.info("Existing Media Build Object found for: %s: %s: %s: Exiting Rest Call" %(name, version, drop))
                infoString = infoString + "\n Existing Media Build Object found for: %s: %s: %s: Exiting Rest Call \n" %(name, version, drop)
                return HttpResponse("\n\n Media CIFWK REST Service Status\n" + infoString + "\n",status=400)
        except Exception as error:
            logger.error("Error: Thrown in DB Queries new ISO Build Entry: " +str(error))
            return HttpResponse(" \nError: Thrown in DB Queries new ISO Build Entry: " +str(error)+ "\n")

        try:
            sortedPackages = cireports.utils.getPackageBaseline(dropObj)
            for sortedPackage in sortedPackages:
                if ISOBuildObj is not None and sortedPackage.package_revision.platform != "sparc":
                    if not ISObuildMapping.objects.filter(iso=ISOBuildObj, drop=sortedPackage.drop, package_revision=sortedPackage.package_revision).exists():
                        if category == "productware" and sortedPackage.package_revision.category.name != "testware":
                            utils.createMediaArtifactVersionToArtifactMapping(product,ISOBuildObj,sortedPackage.drop,sortedPackage.package_revision)
                            infoString = infoString + "\n ISO Build Mapping Created for: " + str(sortedPackage) + "\n"
                        elif sortedPackage.package_revision.category.name == category:
                            utils.createMediaArtifactVersionToArtifactMapping(product,ISOBuildObj,sortedPackage.drop,sortedPackage.package_revision)
                            infoString = infoString + "\n ISO Build Mapping Created for: " + str(sortedPackage) + "\n"
                    else:
                        infoString = infoString + "\n ISO Build Mapping aleady exists for: " + str(sortedPackage) + "\n"

        except Exception as error:
            logger.error("Error: Thrown in DB Queries new ISO Build Mapping Entry: " +str(error))
            return HttpResponse("\n Error: Thrown in DB Queries new ISO Build Mapping Entry: " +str(error))

        return HttpResponse("\n\n Media CIFWK REST Service Status\n" + infoString + "\n")

@csrf_exempt
def restDeliveryMediaArtifactToProductSet(request, deliveryUI=None):
    '''
       REST Deliver Media to Product Set
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        drop = request.POST.get('drop')
        mediaName = request.POST.get('mediaArtifact')
        mediaVer = request.POST.get('version')
        product = request.POST.get('product')
        productRel = request.POST.get('productRelease')
        productSetName = request.POST.get('productSet')
        productSetRelName = request.POST.get('productSetRelease')
        productList = request.POST.get('deployProductList')
        signum = request.POST.get('signum')
        email = request.POST.get('email')
        logger.info("Information Given: Media Artifact Name - " + str(mediaName) + " Media Artifact Version - " + str(mediaVer) + " drop - " + str(drop) + " Product Set - " +  str(productSetName) )

        versionAsString = str(mediaVer)
        if "R" in str(versionAsString):
            version = convertRStateToVersion(versionAsString)
        else:
            version = versionAsString

        if mediaName is None or not mediaName or mediaName == "None":
            logger.error("Error: Media Artifact required.\n")
            return HttpResponse("Error: Media Artifact required.\n")

        if mediaVer is None or not mediaVer or mediaVer == "None":
            logger.error("Error: version required.\n")
            return HttpResponse("Error: version required.\n")

        if drop is None or not drop or drop == "None":
            drop = "latest"

        if product is None or not product or product == "None":
            logger.error("Error: Product required.\n")
            return HttpResponse("Error: Product required.\n")

        if product =="ENM":
            if productList is None or not productList or productList == "None":
                productList = str(config.get('DMT', 'defaultDeployProductMaps')).split(' ')
            else:
                productList = str(productList).split(",")
        else:
            productList = None

        if productSetRelName is None or not productSetRelName or productSetRelName == "None":
            productSetRelName = None

        if productSetName is None or not productSetName or productSetName == "None":
            logger.error("Error: Product Set required.\n")
            return HttpResponse("Error: Product Set required.\n")

        if signum is None or not signum or signum == "None":
            logger.error("Error: Signum required.\n")
            return HttpResponse("Error: Signum required.\n")

        if email is None or not email or email == "None":
            if deliveryUI:
                info = "ERROR: Email required for Delivery"
                return render(request, "cireports/media_delivery_error.html",
                        {
                            'info': info,
                            'product': "None",
                            'femObj': "None",
                        })
            else:
                email = None

        if not ISObuild.objects.filter(version=version, mediaArtifact__name=mediaName).exists():
            logger.error("Error: Media Artifact " + str(mediaName) + str(version) +  " does not exist.\n")
            return HttpResponse("Error: Media Artifact " + str(mediaName) + str(version) +  " does not exist.\n")

        if not ProductSet.objects.filter(name=productSetName).exists():
            logger.error("Error: Product Set " + str(productSetName) + " does not exist.\n")
            return HttpResponse("Error: Product Set " + str(productSetName) + " does not exist.\n")

        if not deliveryUI and productSetRelName != None:
            if not ProductSetRelease.objects.filter(name=productSetRelName, productSet__name=productSetName).exists():
                logger.error("Error: Product Set Release " + str(productSetRelName) + " does not exist.\n")
                return HttpResponse("Error: Product Set Release " + str(productSetRelName) + " does not exist.\n")
        try:
            deliveryResults = utils.mediaDelivery(productSetName, productSetRelName, drop, product, mediaName, version, signum, email, productList)
            if "ERROR" in deliveryResults:
                if deliveryUI:
                  return render(request, "cireports/media_delivery_error.html",
                          {
                              'info': deliveryResults,
                              'productSet': productSetName,
                              'product': "None",
                              'femObj': "None",
                          })
                else:
                    logger.error(deliveryResults)
                    return HttpResponse(deliveryResults)
        except Exception as e:
              if deliveryUI:
                  logger.error("Issue with Delivering Media Artifact to Product Set, Error: " +str(e))
                  info = "Issue with Delivering Media Artifact to Product Set, Error: " +str(e)
                  return render(request, "cireports/media_delivery_error.html",
                               {
                                   'info': info,
                                   'productSet': productSetName,
                                   'product': "None",
                                   'femObj': "None",
                                })
              else:
                  logger.error("Issue with Delivering Media Artifact to Product Set, Error: " +str(e))
                  return HttpResponse("Issue with Delivering Media Artifact to Product Set,  Error thrown: " +str(e))
        if deliveryUI:
             mediaArtifact = ISObuild.objects.get(version=version, mediaArtifact__name=mediaName)
             prodSetRel = ProductSetRelease.objects.filter(productSet__name=productSetName)[0]
             drop = Drop.objects.get(name=drop, release__product=prodSetRel.release.product)
             productSetRelease = ProductSetRelease.objects.get(release=drop.release)

             return render(request, "cireports/media_delivery_result.html",
                        {
                            'media': mediaArtifact,
                            'version': mediaArtifact.version,
                            'drop': drop.name,
                            'productSet': productSetName,
                            'productSetRel': productSetRelease.name,
                            'product': "None",
                            'femObj': "None",
                        })
        else:
            logger.info(deliveryResults)
            return HttpResponse(deliveryResults)

@login_required
def makeNewMediaDelivery(request, mediaName, mediaVer):
    '''
     This is for selecting Product set.
    '''
    form = DeliverNewMediaForm()
    if request.method == "GET":
          return render(request, "cireports/select_productSet_delivery_form.html",
                  {
                      'form': form,
                      'mediaArtifact': mediaName,
                      'version': mediaVer,
                      'product': "None",
                      'femObj': "None",
                      })

    if request.method == 'POST':
        productSet = request.POST.get("productSet")
        return HttpResponseRedirect("/mediaDeliveryProductSet/"+ str(productSet) + "/" + str(mediaName) + "/"+ str(mediaVer) )




@login_required
def makeMediaDelivery(request, productSet, mediaName, mediaVer):
    '''
     MakeMediaDelivery function is used to delivery Media Revision Version into a Drop
    '''
    productSetRelease = ProductSetRelease.objects.filter(productSet__name=productSet)
    product = productSetRelease[0].release.product.name
    if "ENM" in product:
        user = User.objects.get(username=str(request.user))
        maintrackGuards = config.get("CIFWK", "mtgGuards")
        if not user.groups.filter(name=maintrackGuards).exists():
            info = "ERROR: Only Maintrack Guardians are authorized to deliver to an ENM Product Set drop. Please contact Maintrack about this delivery."
            return render(request, "cireports/media_delivery_error.html",
                {
                    'info': info,
                    'product': product,
                    'femObj': "None",
                })
    form = MediaDeliveryForm(product)
    media = ISObuild.objects.get(version=mediaVer, mediaArtifact__name=mediaName)
    timeNow = datetime.now()
    drops = Drop.objects.filter(mediaFreezeDate__gt=timeNow)
    if "ENM" == str(media.drop.release.product.name):
        return render(request, "cireports/media_delivery_form_deploy.html",
                {
                    'media': media,
                    'productSet': productSet,
                    'drops' : drops,
                    'signum' : str(request.user),
                    'product': "None",
                    'femObj': "None",
                })
    return render(request, "cireports/media_delivery_form.html",
                {
                    'form': form,
                    'media': media,
                    'productSet': productSet,
                    'drops' : drops,
                    'signum' : str(request.user),
                    'product': "None",
                    'femObj': "None",
                })


@login_required
def configureSummary(request, product=None):
    '''
        The configureSummary function allows users with the correct access to choose the 4 drops
        that will appear on the Summary pages for Products and Product Sets.
    '''
    user = User.objects.get(username=str(request.user))
    configSumGroup = config.get("CIFWK", "configSumGroup")
    if not user.groups.filter(name=configSumGroup).exists():
        return render(request, "cireports/configsumm_error.html",{'error':'User not authorised to edit the Product and Product Set Summary page'})


    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        return render(request, "cireports/configsumm_error.html",{'error': 'Invalid product'})

    list = [1,2,3,4]
    productId =product.id
    pageHitCounter("ConfigureSummary", productId, str(request.user))

    allSumData = ConfigProducts.objects.filter(product=product, active=1).order_by('order_id')

    try:
         allRelease=Release.objects.filter(product__name=product.name).order_by('-id')
    except Exception as e:
        logInfo="Unable to get the Release objects : " + str(e)
        logger.error(logInfo)

    try:
        allDrop = Drop.objects.filter(release__product__name=product.name).order_by('-id')
    except Exception as e:
        logInfo="Unable to get the Drop objects : " + str(e)
        logger.error(logInfo)

    allList = []
    for release in allRelease:
        allList.append(release.name)
    for drop in allDrop:
        allList.append(drop.name)

    if request.method == 'POST':
        orderId=0
        totalNum=0

        # Store the current configurations
        currentConfigs = ConfigProducts.objects.filter(product=product, active=1)

        # Check to see if user has selected to use default behaviour
        check = request.POST.get('defbehav')

        # Check to see if there is valid data in the 1st choice field
        firstChoice =  request.POST.get('1_reldrop')

        # Set the active flag to 0(false) on the the current list of config summary
        if (check):
            for conf in currentConfigs:
                conf.active = 0
                conf.save()
            return HttpResponseRedirect('/')

        if not (check) and firstChoice == 'select':
            msg = "Please ensure that you select the first Release/Drop option when submitting details for the Summary page"
            return render(request, "cireports/configsumm_error.html",{'error': msg})

        if not (check):
            # Check the total number of drops that have been passed and make sure it doesn't exceed 4
            for checkNum in list:
                choice =  request.POST.get(str(checkNum)+'_reldrop')
                number =  request.POST.get(str(checkNum)+'_number')
                intNumber=int(number)
                # if the selected choice is a Release
                if (any(rel.name == choice for rel in allRelease)) and number == "0":
                    msg = "You have chosen a Release with no number of drops to display. Please select a number from the drop down menu"
                    return render(request, "cireports/configsumm_error.html",{'error': msg})
                    logInfo="Choose a number of drops to display in the Release "
                    logger.error(logInfo)

                if (any(rel.name == choice for rel in allRelease)):
                    totalNum=totalNum + intNumber
                if (any(drop.name == choice for drop in allDrop)):
                    totalNum=totalNum + 1
                if totalNum > 4:
                     msg = "You have chosen " + str(totalNum) + " drops to display. Please change your options so that no more than 4 drops are selected"
                     return render(request, "cireports/configsumm_error.html",{'error': msg})
                     logInfo="Choose no more than 4 drops to display "
                     logger.error(logInfo)

            # If no errors have been made in the selections then clear the current active flags
            if firstChoice != 'select':
                for conf in currentConfigs:
                    conf.active = 0
                    conf.save()

            for l in list:
                orderId=orderId+1
                choice =  request.POST.get(str(l)+'_reldrop')
                number =  request.POST.get(str(l)+'_number')
                if (any(drop.name == choice for drop in allDrop)):
                    number = 0
                if choice !='select':
                    try:
                        returnedValue = cireports.utils.uploadConfigData(productId,choice, number, orderId)
                    except Exception as e:
                        logger.error("Error with Summary Function" + str(e))
            if returnedValue != 1:
                return HttpResponseRedirect('/')

    return render(request, "cireports/configure_summary.html",
        {
                "product": product,
                "list": list,
                "allSumData": allSumData,
                "allList": allList
            })

def homepage(request):
    '''
    Quick Links Landing Page
    '''
    return render(request, "cireports/index.html")

def releaseProducts(request):
    '''
       The releaseProducts function renders the product html page with all products in database
    '''

    pageHitCounter("Products", None, str(request.user))
    products = productToDropDict = noReleaseDict = None
    try:
        products,productToDropDict,noReleaseDict = cireports.utils.productSummaryBuildUp()
    except Exception as e:
        logger.error(e)
    return render(request, "cireports/products_index.html",
            {
                'productToDropDict': productToDropDict,
                'products': products,
                'noReleaseDict': noReleaseDict
            })

def prodSetSummary(request):
    '''
    The prodSetSummary function displays all a summary of all the product Sets
    '''
    pageHitCounter("ProductSets", None, str(request.user))
    prodSets = prodSetToDropDict = noReleaseDict = None
    try:
        prodSets,prodSetToDropDict,noReleaseDict = cireports.utils.productSetSummaryBuildUp()
        cnProductToDropDict = cireports.utils.getCNProductsSummary()
    except Exception as e:
        logger.error(e)
    return render(request, "cireports/productSetIndex.html",
            {
                'prodSetToDropDict': prodSetToDropDict,
                'prodSets': prodSets,
                'noReleaseDict': noReleaseDict,
                'cnProductToDropDict': cnProductToDropDict
            })

def displayRelease(request, release):
    hostname = request.META['HTTP_HOST']
    try:
        rel = Release.objects.get(name=release)
        drops = Drop.objects.filter(release=rel.id).order_by('-planned_release_date')
    except Release.DoesNotExist:
        raise Http404
    return render(request, "cireports/release.html", {'drops': drops, 'name': release})

def displayCDBContent(request, product, drop, type, cdbHistId):
    cdbHistory = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    hostname = request.META['HTTP_HOST']
    try:
        drp = Drop.objects.get(name=drop, release__product__name=product)
        cdbType = CDBTypes.objects.get(name=type)
        # Get a full list of all the package revisions associated with the CDB
        cdbHistObj = CDBHistory.objects.get(id=cdbHistId)
        cdbPkgs = CDBPkgMapping.objects.filter(cdbHist=cdbHistObj)
    except Drop.DoesNotExist:
        raise Http404
    return render(request, "cireports/historicCDBContent.html",
            {
                'cdb': cdbHistObj,
                'cdbContent': cdbPkgs,
                'drop': drp,
                'type': cdbType,
                'product': product,
                'femObj': femObj
            })

def displayCDBHistory(request, product, drop):
    cdbHistory = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    hostname = request.META['HTTP_HOST']
    try:
        drp = Drop.objects.get(name=drop, release__product__name=product)
        # Get a full History for the Drop for the specific type (Virtual, Physical etc) that are not in progress
        cdbHistory = CDBHistory.objects.filter(drop=drp.id).exclude(status="in_progress").order_by('-lastUpdated')
    except Drop.DoesNotExist:
        raise Http404
    return render(request, "cireports/historicCDB.html",
            {
                'cdbs': cdbHistory,
                'drop': drp,
                'product': product,
                'femObj': femObj
            })

def latestCDBIndex(request,product,drop):
    isoPkgMapping = None
    pkgCount = None
    try:
        drop = Drop.objects.get(name=drop, release__product__name=product)
    except Drop.DoesNotExist:
        raise Http404
    pageHitCounter("DropLatestStatus", drop.id, str(request.user))
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        latestIso = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-id')[0]
        latestIsoId=latestIso.id
        isoPkgMapping = ISObuildMapping.objects.filter(iso=latestIso.id)
        pkgCount = len(isoPkgMapping)
    except Exception as e:
        logger.error("There is no ISO associated with drop " + str(drop) + ":" + str(e))
        latestIsoId=None

    return render(request, "cireports/latestCDB_index.html" ,
            {
                'allISOMap': isoPkgMapping,
                'count': pkgCount,
                'drop': drop,
                'product': product,
                'femObj': femObj,
                'iso':latestIsoId,
            })

def displayLatestCDB(request,product,drop, testware=None):
    isoPkgMapping = None
    allISOMap = None
    pkgCount = None
    pkgs = []
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        product = "None"
    try:
        drop = Drop.objects.get(name=drop, release__product__name=product)
    except Drop.DoesNotExist:
        raise Http404

    try:
        if 'testware' in testware:
            latestIso = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=True).order_by('-id')[0]
        else:
            latestIso = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-id')[0]
        isoPkgMapping = ISObuildMapping.objects.filter(iso=latestIso.id)
        category = Categories.objects.get(name="testware")
        if 'testware' in testware:
            for isoPkg in isoPkgMapping:
                if isoPkg.package_revision.category == category:
                    pkgs.append(isoPkg)
        else:
            for isoPkg in isoPkgMapping:
                if isoPkg.package_revision.category != category:
                    pkgs.append(isoPkg)
        pkgCount = len(isoPkgMapping)
    except Exception as e:
        logger.error("There is no ISO associated with drop " + str(drop) + ":" + str(e))
        latestIso = None

    return render(request, "cireports/latestCDB.html",
            {
                'packages': pkgs,
                'count': pkgCount,
                'product': product,
                'drop':drop,
            })


def displayCDBsummary(request, product, drop):
    '''
    CDB Status Summary

    '''
    history = latest = latestTypes = lastSuccessful = None
    cdbType = isos = flag = drp = None
    excludeList = []
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    hostname = request.META['HTTP_HOST']
    try:
        drp = Drop.objects.get(name=drop, release__product=product)
        pageHitCounter("DropExecutiveSummary", drp.id, str(request.user))
        latest, latestTypes = utils.getLatestCDBforDrop(product.name, drp.name)
        excludeList=utils.getCDBinfo(latest)
        lastSuccessful, cdbType = utils.getLastSuccessfulCDBforDrop(product.name, drp.name,excludeList)
        excludeList=utils.getCDBinfo(lastSuccessful,excludeList)
        isos, history, flag  = utils.getCDBhistoryforDrop(product.name, drp.name,excludeList)
    except Exception as e:
        logger.error("Error Getting CDB Summary : " + str(e))
    return render(request, "cireports/cdb_status_summary.html",
            {
                'latest': latest,
                'isos': isos,
                'successfulStatus': lastSuccessful,
                'cdbType': cdbType,
                'cdbHistory': history,
                'flag': flag,
                'latestTypes': latestTypes,
                'drop': drp.name,
                'product': product,
                'femObj': femObj
            })

def displayPSsummary(request, productSet, drop):
    '''
    CDB Status Summary

    '''
    history = latest = latestTypes = lastSuccessful = None
    cdbType = versions = flag = drp = None
    excludeList = []
    hostname = request.META['HTTP_HOST']
    try:
        prodSetObj = ProductSet.objects.get(name=productSet)
        prodSetRelObj = ProductSetRelease.objects.filter(productSet=prodSetObj)[0]
        drp = Drop.objects.get(name=drop, release__product=prodSetRelObj.release.product)
        pageHitCounter("ProductSetExecutiveSummary", drp.id, str(request.user))
        productName=prodSetRelObj.release.product.name
        if Product.objects.filter(name=productName).exists():
            product = Product.objects.get(name=productName)
            femObj = FEMLink.objects.filter(product=product)
        else:
            product = "None"
            femObj = "None"
        latest, latestTypes = utils.getLatestPSforDrop(prodSetObj.name, drp.name)

        excludeList=utils.getCDBinfo(latest)
        lastSuccessful, cdbType = utils.getLastSuccessfulPSforDrop(prodSetObj.name, drp.name,excludeList)
        excludeList=utils.getCDBinfo(lastSuccessful,excludeList)
        versions, history, flag  = utils.getPShistoryforDrop(prodSetObj.name, drp.name,excludeList)
    except Exception as e:
        logger.error("Error Getting Product Set Summary : " + str(e))
    return render(request, "cireports/ps_status_summary.html",
            {
                'latest': latest,
                'versions': versions,
                'successfulStatus': lastSuccessful,
                'cdbType': cdbType,
                'cdbHistory': history,
                'flag': flag,
                'latestTypes': latestTypes,
                'drop': drp.name,
                'productSet': prodSetObj,
                'product': product,
                'femObj': femObj
            })


def displayDrop(request, product, drop):
    lastBuiltISO = frozen = dropActivity = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        frozen = None
        lastBuiltISO = None
        drp = Drop.objects.get(name=drop, release__product__name=product)
        pageHitCounter("Drop", drp.id, str(request.user))
        if DropActivity.objects.filter(drop=drp).exists():
            dropActivity = DropActivity.objects.filter(drop=drp).order_by('-id')[0]
        if drp.actual_release_date == None or drp.actual_release_date == "None":
            frozenDate =  drp.planned_release_date
        else:
            frozenDate = drp.actual_release_date
        if str(frozenDate) != "None":
            dropDate = datetime.strptime(str(frozenDate), "%Y-%m-%d %H:%M:%S")
            [newdate,mil] = str(datetime.now()).split('.')
            nowDateTime = datetime.strptime(str(newdate), "%Y-%m-%d %H:%M:%S")
            if dropDate <= nowDateTime:
                if ISObuild.objects.filter(drop=drp).exists():
                    frozen = True
                    lastBuiltISO = ISObuild.objects.filter(drop=drp, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-id')[0]
                else:
                    lastBuiltISO = None
                    frozen = True
    except Drop.DoesNotExist:
        logger.error("Requested Drop: " + str(drop) + " is not contained within the CI Database")
        raise Http404
    return render(request, "cireports/drop.html",
            {
                'drop': drp,
                'product': product,
                'femObj': femObj,
                'iso':lastBuiltISO,
                'frozen': frozen,
                'dropActivity': dropActivity,
            })

@login_required
def makeDelivery(request, product, package, version, platform, type):
    '''
    MakeDelivery function is used to delivery Package Revision Version into a Drop
    '''
    #If product does not exist ui will not crash
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    form = DeliveryForm(product)
    pkg = Package.objects.get(name=package)
    if platform == "None":
        package_info = PackageRevision.objects.get(package=pkg, version=version, m2type=type)
    else:
        package_info = PackageRevision.objects.get(package=pkg, version=version, platform=platform, m2type=type)
    incdrops = utils.getListOfDrops(package_info, False)
    timeNow = datetime.now();
    drops = Drop.objects.filter(planned_release_date__gt=timeNow) | Drop.objects.filter(actual_release_date__gt=timeNow)
    if request.method == "GET":
        return render(request, "cireports/delivery_form.html",
                {
                    'package': package,
                    'version': version,
                    'type': type,
                    'platform': platform,
                    'pkg_info': package_info,
                    'incdrops': incdrops,
                    'form': form,
                    'drops': drops,
                    'product': product,
                    'femObj': femObj
                })
    if request.method == 'POST':
        drop = request.POST.get("drop")
        email = request.POST.get("email")
        if drop == None:
            msg = "Invalid drop selection. Please verify and try again"
            return render(request, "cireports/delivery_error.html",  {'info': str(msg), 'product': product, 'femObj': femObj})
        drp = Drop.objects.get(name=drop,release__product__name=product)
        user = User.objects.get(username=str(request.user))
        deliverGroup = config.get("CIFWK", "adminGroup")
        if "open" not in drp.status:
            if not user.groups.filter(name=deliverGroup).exists():
                msg = "User " + str(user) + " is not authorised to deliver into a " + str(drp.status) + " drop (" +str(drp) + ")"
                return render(request, "cireports/delivery_error.html",  {'info': str(msg), 'product': product, 'femObj': femObj})
        baseId = drp.designbase
        currentDrop=utils.getPackageBaseline(drp)
        if str(baseId) != 'None':
            basedrp = Drop.objects.get(id=drp.designbase.id)
            currentBaseDrop=utils.getPackageBaseline(basedrp)
            if currentBaseDrop:
                for basePackage in currentBaseDrop:
                     if str(package)+"-"+str(version) in str(basePackage):
                        if platform == "None":
                            info = "ERROR: Package '" + str(pkg) + "' with version '" + str(version) + "' is already included in this drop. It has been delivered into another drop which is in the baseline of '" + str(drop) + "'.\nIt cannot be delivered to Drop: " + str(drop)
                        else:
                            info = "ERROR: Package '" + str(pkg) + "' with version '" + str(version) + "' and this platform: '" + str(platform) + "' is already included in this drop. It has been delivered into another drop which is in the baseline of '" + str(drop) + "'.\nIt cannot be delivered to Drop: " + str(drop)
                        return render(request, "cireports/delivery_error.html",  {'info': info, 'product': product, 'femObj': femObj})

        if drop:
            for currentPackage in currentDrop:
                # TODO : Will the same package Version with different types be delivered into the same drop ..Probably not
                # If so, this code will need to be updated
                if str(package)+"-"+str(version) in str(currentPackage):
                    if platform == "None":
                        info = "ERROR: You have previously delivered this package '" + str(pkg) + "' with version '" + str(version) + "' to this Drop: " + str(drop)
                    else:
                        info = "ERROR: You have previously delivered this package '" + str(pkg) + "' with version '" + str(version) + "' and this platform: '" + str(platform) + "' to this Drop: " + str(drop)
                    return render(request, "cireports/delivery_error.html",  {'info': info, 'product': product, 'femObj': femObj})
            rstate = package_info.getRState
            try:
                result = utils.performDelivery(package, version, type, drop, product, email, platform, user)
            except Exception as e:
                logger.error("There was an issue in performing the requested delivery. Error thrown: " +str(e))
                result = "ERROR: " +str(e)
            if "ERROR:" not in result:
                return render(request, "cireports/delivery_result.html",
                        {
                            'package': package,
                            'pkg_info': package_info,
                            'version': version,
                            'platform': platform,
                            'rstate': rstate,
                            'drop': drop,
                            'product': product,
                            'femObj': femObj,
                            'info': result
                        })
            else:
                logger.error("Making Delivery " + str(result))
                return render(request, "cireports/delivery_error.html",  {'info': result, 'product': product, 'femObj': femObj})
        else:
            info = "Invalid information supplied. Please verify and try again"
            return render(request, "cireports/delivery_error.html", {'info': info, 'product': product, 'femObj': femObj})

def makeNewPackageDelivery(request,product,package,version,platform,pkgStatus,type):
    '''
    If this is the first time you have delivered a package then
    the package needs to be associate to a product to list product drops
    '''
    logger.info("Platform: " +str(platform))
    fh = FormHandle()
    fh.form = DeliverNewPackageForm()
    fh.title = "Select Product For this Delivery"
    fh.request = request
    fh.button = "Next ..."
    if request.method == "GET":
        return fh.display()
    if request.method == 'POST':
        fh.form = DeliverNewPackageForm(request.POST)
        product = request.POST.get("product")
        if Product.objects.filter(name=product).exists():
            product = Product.objects.get(name=product)
        else:
            product = "None"
        if fh.form.is_valid():
            if str(product) == "ENM":
                fh.redirectTarget = "/" + str(product)+ "/multipleDeliveries/?package="+package+"&version="+version
            else:
                fh.redirectTarget = ("/" + str(product)+ "/delivery/" +str(package) + "/" + str(version) + "/" + str(platform) + "/" + str(type))
            return fh.success()
        else:
            return fh.failure()

def displayMediaByDrop(request, productName, dropName):
    '''
      display Media By Drop for ISO Versions
    '''
    mediaArtifactVersions = None
    deliveryData = obsoleteData = mediaArtifactVersions =  None
    mediaArtTestwareVersions = deliveryTestwareData = obsoleteTestwareData = None
    prodTWmediaMapProductData = None
    prodTWmediaMapTestwareData = None
    mediaArtMapsList = mediaArtTestwareMapsList= None
    product = drop = None
    categories = []

    try:
        productFields = ('id','name','isoDownload')
        product = Product.objects.only(productFields).values(*productFields).get(name=productName)
    except Product.DoesNotExist:
        errMsg = "Error getting Media: Product " + str(productName) + " Does Not Exist."
        return render(request, "cireports/error.html",{ 'error': errMsg  } )

    try:
        dropFields = ('id', 'systemInfo', 'name', 'release','release__masterArtifact__name')
        drop = Drop.objects.only(dropFields).values(*dropFields).get(name=dropName, release__product__id=product['id'])
        pageHitCounter("DropMediaArtifacts", drop['id'], str(request.user))
        mediaArtifactVersions, deliveryData, prodTWmediaMapProductData,  prodTWmediaMapTestwareData, categoriesList  = cireports.utils.getMediaArtifactVersionsInformation(product['id'], productName, dropName, drop['release__masterArtifact__name'], False)
        categories = MediaArtifactCategory.objects.filter(name__in=categoriesList).order_by('id')
    except Exception as error:
        errMsg = "Error getting Media: Drop " + str(dropName) + " Does Not Exist. - " + str(error)
        return render(request, "cireports/error.html",{ 'error': errMsg  } )
    return render(request, "cireports/media_table.html",
            {
                'categories' : categories,
                'mediaArtifactVersions': mediaArtifactVersions,
                'deliveryData': deliveryData,
                'prodTWmediaMapProductData': prodTWmediaMapProductData,
                'prodTWmediaMapTestwareData': prodTWmediaMapTestwareData,
                'drop': drop,
                'product': product,
                'mediaArtifact': drop['release__masterArtifact__name'],
            })

def displayMediaByRelease(request, productName, releaseName, mediaArtifactName):
    '''
    display Media By Release for ISO Versions
    '''
    deliveryData = obsoleteData = mediaArtifactVersions =  None
    testwareCount = productCount = None
    prodTWmediaMapProductData = None
    prodTWmediaMapTestwareData = None
    product = release = None
    categories = []

    try:
        productFields = ('id','name','isoDownload')
        product = Product.objects.only(productFields).values(*productFields).get(name=productName)
    except Product.DoesNotExist:
        errMsg = "Error getting Media: Product " + str(productName) + " Does Not Exist."
        return render(request, "cireports/error.html",{ 'error': errMsg  } )
    try:
        mediaArtifactVersions, deliveryData, prodTWmediaMapProductData,  prodTWmediaMapTestwareData, categoriesList = cireports.utils.getMediaArtifactVersionsInformation(product['id'], productName, releaseName, mediaArtifactName, True)
        categories = MediaArtifactCategory.objects.filter(name__in=categoriesList).order_by('id')
    except Exception as error:
        errMsg = "Error getting Media: " + str(error)
        return render(request, "cireports/error.html",{ 'error': errMsg  } )

    return render(request, "cireports/media_table.html",
            {
                'categories' : categories,
                'mediaArtifact': mediaArtifactName,
                'mediaArtifactVersions': mediaArtifactVersions,
                'deliveryData': deliveryData,
                'prodTWmediaMapProductData': prodTWmediaMapProductData,
                'prodTWmediaMapTestwareData': prodTWmediaMapTestwareData,
                'release': releaseName,
                'product': product,
            })

@gzip_page
def displayMediaContent(request, productName, dropName, mediaArtifactName, version):
    '''
    Media Content Page
    This function displays the contents of the given media artifact
    '''
    try:
        try:
            productFields = ('id','name')
            product = Product.objects.only(productFields).values(*productFields).get(name=productName)
        except Product.DoesNotExist:
            raise Http404

        requiredIsoBuildFields = ('drop__id','drop__name','systemInfo','mediaArtifact__mediaType','mediaArtifact__testware','id','groupId','version','build_date','arm_repo','drop__release__product__isoDownload', 'size', 'active')
        isoBuilds = ISObuild.objects.filter(mediaArtifact__name=mediaArtifactName, version=version, drop__name=dropName, drop__release__product__id = product['id']).only(requiredIsoBuildFields).values(*requiredIsoBuildFields)

        if len(isoBuilds) == 0 :
            logger.error("Error: Required media artifact details does not exist for given product and drop.")
            raise Http404

        isoBuild = isoBuilds[0]
        isoArmRepo = isoBuild['arm_repo']
        isoGroupId = isoBuild['groupId']
        mediaArtVerId = isoBuild['id']
        testware = isoBuild['mediaArtifact__testware']
        productIsoDownload = ['drop__release__product__isoDownload']

        config = CIConfig()
        nexusHubUrl = config.get('CIFWK', 'nexus_url')
        hubIsoUrl = str(nexusHubUrl + "/" + isoArmRepo + "/" + isoGroupId.replace(".", "/"))
        athloneProxyProducts = ast.literal_eval(config.get("CIFWK", "athlone_proxy_products"))
        localIsoUrl = utils.getAthloneProxyProductsUrl(productName, isoArmRepo, isoGroupId, athloneProxyProducts)
        if testware:
            requiredTwFields = ('productIsoVersion__mediaArtifact__name','productIsoVersion__version')
            prodTWmediaMaps = list(ProductTestwareMediaMapping.objects.filter(testwareIsoVersion__id=mediaArtVerId).only(requiredTwFields).values(*requiredTwFields))
        else:
            requiredTwFields = ('testwareIsoVersion__mediaArtifact__name','testwareIsoVersion__version')
            prodTWmediaMaps = list(ProductTestwareMediaMapping.objects.filter(productIsoVersion__id=mediaArtVerId).only(requiredTwFields).values(*requiredTwFields))

        return render(request, "cireports/media_content_table.html",
            {
                'product' : product,
                'productIsoDownload': productIsoDownload,
                'dropName': dropName,
                'dropSystemInfo': isoBuild['systemInfo'],
                'mediaArtifact': mediaArtifactName,
                'version': isoBuild['version'],
                'rstate' : convertVersionToRState(version),
                'buildDate': isoBuild['build_date'],
                'hubIsoUrl': hubIsoUrl,
                'localIsoUrl': localIsoUrl,
                'isoId': mediaArtVerId,
                'maGroupId': isoBuild['groupId'],
                'testware': testware,
                'prodTWmediaMaps': prodTWmediaMaps,
                'mediaType': isoBuild['mediaArtifact__mediaType'],
                'mediaSize': isoBuild['size'],
                'mediaActive': isoBuild['active']

            })

    except Exception as e:
        logger.error("Error: " + str(e))
        raise Http404

@gzip_page
def getMediaContent(request, productName, dropName, mediaArtifactName, version, testware):
    try:
        result = utils.getMediaContentResult(productName, dropName, mediaArtifactName, version, testware)
        if isinstance(result, basestring) and result.startswith('Error'):
            raise Http404
        return HttpResponse(json.dumps(result,cls=DjangoJSONEncoder), content_type="application/json")
    except Exception as e:
        logger.error("Error: " + str(e))
        raise Http404

def isoVersionList(request, product, pkgName, version, platform, m2type):
    '''
    The isoVersionList function lists all the ISOs included in a product version
    '''
    if platform == "None":
        pkgRevision = PackageRevision.objects.only('id').values('id').get(package__name=pkgName, version=version, m2type=m2type)
    else:
        pkgRevision = PackageRevision.objects.only('id').values('id').get(package__name=pkgName, version=version, platform=platform, m2type=m2type)
    if not Product.objects.filter(name=product).exists():
        product = "None"
        femObj = "None"
    else:
        femObj = FEMLink.objects.filter(product__name=product)
    fields = 'id', 'iso__version', 'iso__drop__name', 'iso__mediaArtifact__name'
    isoMappingObj = list(ISObuildMapping.objects.only(fields).values(*fields).filter(package_revision_id=pkgRevision['id'], drop__release__product__name=product))
    count = len(isoMappingObj)
    isoMappingObj.sort(key=lambda isoMappingObj:LooseVersion(isoMappingObj['iso__version']), reverse=True)
    page = request.GET.get('page')
    isoMappingObj = paginator(isoMappingObj,page)
    pageBaseUrl = "/"+ str(product) + "/isoVersionList/" + str(pkgName) + "/" + str(version) + "/" + str(platform) + "/" + str(m2type) +"/"
    return render(request, "cireports/isoVersionList_table.html",
            {
                'pkgName': pkgName,
                'isoMappingObj': isoMappingObj,
                'version': version,
                'count': count,
                'product': product,
                'femObj': femObj,
                'pageBaseUrl' : pageBaseUrl
            })

def displayDropMedia(request, prodSet, drop):
    lastBuiltISO = frozen = mediaArtifacts = None
    productSetRelease = drp = None
    product = "None"
    femObj = "None"
    athloneProxyProducts = ast.literal_eval(config.get("CIFWK", "athlone_proxy_products"))
    hostname = request.META['HTTP_HOST']
    try:
        prodSetRel = ProductSetRelease.objects.filter(productSet__name=prodSet)[0]
        dropObj = Drop.objects.get(name=drop, release__product=prodSetRel.release.product)
        productSetRelease = ProductSetRelease.objects.get(release=dropObj.release)
        drp = Drop.objects.get(name=drop, release=productSetRelease.release)
        pageHitCounter("ProductSetDrop", drp.id, str(request.user))
        frozenDate =  drp.mediaFreezeDate
        mediaArtifacts = utils.getMediaBaseline(drp.id)
        dropMediaDeployMaps = utils.getDropMediaDeployMappings(mediaArtifacts)
    except Exception as e:
        logger.error("Error: " + str(e))
        info = "Error: Product Set Release must created for this Product Set " + str(prodSet)
        return render(request, "cireports/drop_media_error.html",
                {
                    'info': info,
                    'productSet': prodSet,
                    'drop': drop,
                    'product': "None",
                    'femObj': "None",
                })

    return render(request, "cireports/media_drop.html",
            {
                'mediaArtifacts': mediaArtifacts,
                'drop': drp,
                'productSet': prodSet,
                'productSetRel': productSetRelease,
                'product': product,
                'femObj': femObj,
                'iso':lastBuiltISO,
                'frozen': frozen,
                'athloneProxyProducts': athloneProxyProducts,
                'deployMappings' : dropMediaDeployMaps,
            })


def displayDocuments(request, product, version):
    '''
    The displayDocuments function is responable from building up the Document baseline page view per drop
    '''
    try:
        dropObj = Drop.objects.only('id').values('id').get(name=version, release__product__name=product)
        pageHitCounter("DropDocuments", dropObj['id'], str(request.user))
        docObjList = cireports.utils.getDocuments(version,product)
        if "Issue" in str(docObjList):
            errMsg = "Product: " + str(product) + " and Drop: " + str(version) + " - " + str(docObjList)
            logger.error(errMsg)
            return render(request, "cireports/error.html",{ 'error': errMsg  } )
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
        return render(request, "cireports/document_table.html",
                {
                    'docObjList': docObjList,
                    'version': version,
                    'product': product,
                    'femObj': femObj
                } )
    except Exception as e:
        errMsg = "Issue with Document Web Page using Product: " + str(product) + " and Drop: " + str(version) + " - " + str(e)
        logger.error(errMsg)
        return render(request, "cireports/error.html",{ 'error': errMsg  } )

@login_required
def addDocument(request, product, version):
    '''
    The addDocument function is used to add a document to a drop building up Document baseline page
    '''
    fh = FormHandle()
    fh.title = "Register Document for Drop " +str(version)
    fh.button = "Finish"
    fh.request = request
    fh.form = DocumentForm()
    product = Product.objects.get(name=product)
    fh.product = product
    femObj = FEMLink.objects.filter(product=product)
    fh.fem = femObj
    fh.redirectTarget = "/" + str(product.name) + "/documents/" +str(version)
    if request.method =='POST':
        owner = request.user
        dropObj = Drop.objects.get(name=version, release__product=product)
        documentTypeID = request.POST.get('document_type')
        logger.info("Document TYPE: " +str(documentTypeID))
        fh.form = DocumentForm(request.POST)
        if fh.form.is_valid():
            try:
                if DocumentType.objects.filter(id=documentTypeID).exists():
                    docTypeObj = DocumentType.objects.get(id=documentTypeID)
                else:
                    logger.error("Unable to find Document Type: " +str(type))
                    return fh.display()
                document = fh.form.save(commit=False)
                document.documenttype = type
                documentNumber = document.number.lower()
                documentNumber = documentNumber.replace(" ","")
                document.number = documentNumber
                document.owner = owner
                document.drop = dropObj
                document.deliveryDate = default=datetime.now()
                document.save()
                logger.info("Document: " +str(document.name)+ " Saved to DB with Success")
                return fh.success()
            except Exception as e:
                logger.error("Unable to Save Document: " +str(document.name)+ " to DB, Error Thrown: " +str(e))
                return fh.failure()
        else:
            logger.error("Form Not Valid please try again")
            return fh.display()
    else:
        return fh.display()

@login_required
@transaction.atomic
def editDocument(request, product, version, documentId):
    '''
    The editDocument function is used to edit a document in a drop building up Document baseline page
    '''
    user = User.objects.get(username=str(request.user))
    deleteDocumentGroup = config.get("CIFWK", "cpiDocumentAdmin")
    if not user.groups.filter(name=deleteDocumentGroup).exists():
        errMsg = "User is not authorised to update Document Details. Please contact CPI Admin to update the Document Details"
        logger.info(errMsg)
        return render(request, "cireports/drop_error.html",{'error': errMsg})
    fh = FormHandle()
    fh.title = "Edit Document in Drop " +str(version)
    fh.button = "Submit"
    fh.button2 = "Cancel"
    if Document.objects.filter(id=documentId).exists():
        docTypeObj = Document.objects.get(id=documentId)
        documentTypeID = docTypeObj.document_type
        name = docTypeObj.name
        author = docTypeObj.author
        number = docTypeObj.number
        revision = docTypeObj.revision
        link = docTypeObj.link
        cpi = docTypeObj.cpi
        comment = docTypeObj.comment
        owner = docTypeObj.owner
        drop = docTypeObj.drop
    else:
        logger.error("Document ID does not exist")
    fh.form = EditDocumentForm(
                initial={
                    'document_type' : documentTypeID,
                    'name' : name,
                    'author' : author,
                    'number' : number,
                    'revision' : revision,
                    'link' : link,
                    'cpi' : cpi,
                    'comment' : comment,
                    })
    fh.request = request
    product = Product.objects.get(name=product)
    fh.product = product
    femObj = FEMLink.objects.filter(product=product)
    fh.fem = femObj
    fh.redirectTarget = "/" + str(product.name) + "/documents/" + str(version)
    if request.method == 'POST':
        fh.form = EditDocumentForm(request.POST)
        if "Cancel" in request.POST:
            return fh.success()
        if fh.form.is_valid():
            dropObj = Drop.objects.get(name=version, release__product=product)
            docDrop = docTypeObj.drop
            if str(version) not in str(docDrop):
                fh.form = EditDocumentForm(request.POST)
                owner = request.user
                documentTypeID = request.POST.get('document_type')
                logger.info("Document TYPE: " +str(documentTypeID))
                documentTypeID = request.POST.get('document_type')
                name = request.POST.get('name')
                author = request.POST.get('author')
                revision = request.POST.get('revision')
                number = request.POST.get('number')
                link = request.POST.get('link')
                cpi = request.POST.get('cpi')
                comment = request.POST.get('comment')
                try:
                    if DocumentType.objects.filter(id=documentTypeID).exists():
                        docTypeObj = DocumentType.objects.get(id=documentTypeID)
                    else:
                        logger.error("Unable to find Document Type: " +str(type))
                        return fh.display()
                    owner = request.user
                    deliveryDate = default=datetime.now()
                    Document.objects.create(document_type_id = documentTypeID, name = name, author = author, number = number, drop = dropObj, revision = revision, deliveryDate = deliveryDate , link = link, cpi = cpi, owner = owner, comment = comment)
                    return fh.success()
                    logger.info("Document: " +str(name)+ " Saved to DB with Success")
                except Exception as e:
                    logger.error("Unable to Save Document: " +str(name)+ " to DB, Error Thrown: " +str(e))
                    return fh.failure()
            else:
                fh.form = EditDocumentForm(request.POST, instance=docTypeObj)
                if fh.form.is_valid():
                    try:
                        with transaction.atomic():
                            docTypeObj.document_type= fh.form.cleaned_data['document_type']
                            docTypeObj.name= fh.form.cleaned_data['name']
                            docTypeObj.author= fh.form.cleaned_data['author']
                            docTypeObj.number= fh.form.cleaned_data['number']
                            docTypeObj.revision= fh.form.cleaned_data['revision']
                            docTypeObj.link= fh.form.cleaned_data['link']
                            docTypeObj.cpi= fh.form.cleaned_data['cpi']
                            docTypeObj.comment= fh.form.cleaned_data['comment']
                            docTypeObj.save(force_update=True)
                            return fh.success()
                    except IntegrityError as e:
                        fh.message = "Issue updating the Document information, Exception : " + str(e)
                        logger.error(fh.message)
                        return fh.display()
                else:
                    fh.message = "Issue validating the Document information"
                    logger.error(fh.message)
                    return fh.display()
        else:
            fh.message = "Issue validating the Document information"
            logger.error(fh.message)
            return fh.display()
    else:
        return fh.display()

def deleteDocument(request, product, version, documentId):
    user = User.objects.get(username=str(request.user))
    deleteDocumentGroup = config.get("CIFWK", "cpiDocumentAdmin")
    if not user.groups.filter(name=deleteDocumentGroup).exists():
        errMsg = "User is not authorised to delete a Document. Please contact CPI Admin to remove the Document"
        logger.info(errMsg)
        return render(request, "cireports/drop_error.html",{'error': errMsg})
    docTypeObj = Document.objects.get(id=documentId)
    product = Product.objects.get(name=product)
    dropObj = Drop.objects.get(name=version, release__product=product)
    docDrop = docTypeObj.drop
    try:
        if Document.objects.filter(id=documentId).exists():
            docTypeObj = Document.objects.get(id=documentId)
            if str(version) not in str(docDrop):
                dropObj = utils.getPreviousDrop(product, version)
                docTypeObj.obsolete_after = dropObj
                docTypeObj.save()
            else:
                docTypeObj.delete()
            return HttpResponseRedirect("/" + str(product.name) + "/documents/" + str(version))
        else:
            message = "Issue deleting Document information, Exception : " + str(e)
            logger.error(message)
            return HttpResponseRedirect("/" + str(product.name) + "/documents/" + str(version))
    except:
        logger.error("Cannot find Document with Document ID " +str(documentId))
        return HttpResponseRedirect("/" + str(product.name) + "/documents/" + str(version))

@gzip_page
def displayPackage(request, product, package):
    hostname = request.META['HTTP_HOST']
    try:
        pageNo = request.GET['page']
    except Exception as e:
        pageNo = 1
    try:
        cLevel = Clue.objects.get(package__name=package)
    except Exception as e:
        cLevel = None
    #Need an exists if product does not exist
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        pkg = Package.objects.get(name=package)
    except Package.DoesNotExist:
        raise Http404
    all_revs = PackageRevision.objects.filter(package=pkg.id).order_by('-date_created').exclude(platform="sparc").only('id').values('id')
    revCount = all_revs.count()
    is_testware = pkg.testware
    objectsPerPage = config.get("CIFWK", "objectsPerPage")
    paginator = Paginator(all_revs, objectsPerPage)
    page = request.GET.get('page')
    if (page == "all"):
        allRevsPag=all_revs
    else:
        try:
            allRevsPag = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            allRevsPag = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            allRevsPag = paginator.page(paginator.num_pages)
    return render(request, "cireports/package.html",
            {
                'allRevsPag': allRevsPag,
                'count': revCount,
                'is_testware': is_testware,
                'name': package,
                'pageNo': pageNo,
                'product': product,
                'femObj': femObj,
                'clue': cLevel,
            })

def displaySolutionSet(request, product, solset):
    try:
        ss = SolutionSet.objects.get(name=solset)
        solsetvers = SolutionSetRevision.objects.filter(solution_set=ss)
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    except SolutionSet.DoesNotExist:
        raise Http404
    return render(request, "cireports/solutionset.html",
            {
                'solsetvers': solsetvers,
                'solset': ss,
                'product': product,
                'femObj': femObj
            })

def displaySolutionSetRevision(request, product, solset, version):
    try:
        logger.info("I got Here")
        ss = SolutionSet.objects.get(name=solset)
        ssv = SolutionSetRevision.objects.get(solution_set=ss, version=version)
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    except SolutionSet.DoesNotExist:
        logger.error("NNN")
        raise Http404
    except SolutionSetRevision.DoesNotExist:
        logger.error("NNNNNNN")
        raise Http404
    return render(request, "cireports/solutionsetversion.html",
            {
                'solsetver': ssv,
                'solset': ss,
                'product': product,
                'femObj': femObj
            })

def releaseIndex(request,product):
    hostname = request.META['HTTP_HOST']
    cdbFlag = productToDropDict = noReleaseDict = allRel = None
    try:
        product = Product.objects.get(name=product)
        pageHitCounter("Releases", product.id, str(request.user))
        productToDropDict,noReleaseDict,allRel,cdbFlag = cireports.utils.expandProductInformation(product)
        femObj = FEMLink.objects.filter(product=product)
    except Exception as e:
            logger.error("Issue returning product from db: " +str(e))
            return 1
    return render(request, "cireports/release_index.html",
            {
                'releases': allRel,
                'productToDropDict': productToDropDict,
                'product': product,
                'femObj': femObj,
                'noReleaseDict': noReleaseDict
            })

def prodSetRelIndex(request, prodSet):
    hostname = request.META['HTTP_HOST']
    product = femObj = "None"
    prodSetReleases = prodSetToDropDict = noReleaseDict = prodSetVersions = None
    try:
        productSet = ProductSet.objects.get(name=prodSet)
        pageHitCounter("ProductSetReleases", productSet.id, str(request.user))
        prodSetReleases, prodSetToDropDict, noReleaseDict, prodSetVersions = cireports.utils.expandProductSetInformation(prodSet)
    except Exception as e:
        logger.error(e)
    return render(request, "cireports/prodSetReleaseIndex.html",
            {
                'productSet': prodSet,
                'prodSetToDropDict': prodSetToDropDict,
                'productSetRels': prodSetReleases,
                'product': product,
                'femObj': femObj,
                'noReleaseDict': noReleaseDict
            })

def displayProdSetContent(request,prodSet,drop,version=None):
    '''
    Displaying the content of Product Set Version
    '''
    product = femObj = "None"
    msg = contents = productSetNumber = productSetVersion = None
    athloneProxyProducts = ast.literal_eval(config.get("CIFWK", "athlone_proxy_products"))
    inactive = None
    deploymentUtils = None
    deployMappings = None
    latestPsv = None
    cnProductSetVersionObj = None

    try:
        prodSetObj = ProductSet.objects.only('id').values('id').get(name=prodSet)
    except Exception as e:
        logger.error("There was an issue gathering Product Set Content information: " +str(e))

    psvfields = ('id', 'productSetRelease__number', 'version',)
    if version == None:
        try:
            latestPsv = ProductSetVersion.objects.only(psvfields).values(*psvfields).filter(drop__name=drop,productSetRelease__productSet_id=prodSetObj['id']).order_by('-id')[0]
            contents = ProductSetVersionContent.objects.filter(productSetVersion_id=latestPsv['id'])
            productSetNumber =  latestPsv['productSetRelease__number']
            productSetVersion =  latestPsv['version']
            if not latestPsv:
                latestPsv = None
                msg = "No Product Set Versions exists with " +str(drop)
        except:
            latestPsv = None
            msg = "No Product Set Versions exists with " +str(drop)
    else:
        try:
            latestPsv = ProductSetVersion.objects.only(psvfields).values(*psvfields).get(version=version, drop__name=drop, productSetRelease__productSet_id=prodSetObj['id'])
            contents = ProductSetVersionContent.objects.filter(productSetVersion=latestPsv['id'])
            inactive = ProductSetVersionContent.objects.filter(productSetVersion_id=latestPsv['id'], mediaArtifactVersion__active=0)
            if inactive:
                inactive = True
            productSetNumber =  latestPsv['productSetRelease__number']
            productSetVersion =  latestPsv['version']
            if not latestPsv:
                latestPsv = None
                msg = "No Product Set Content exists with drop " +str(drop) + " and version " + str(version)
        except:
            latestPsv = None
            msg = "No Product Set Content exists with drop " +str(drop) + " and version " + str(version)
    try:
        fields = ('utility_version__utility_version', 'utility_version__utility_name__utility', 'utility_version__utility_label',)
        deploymentUtils = DeploymentUtilsToProductSetVersion.objects.only(fields).values(*fields).filter(productSetVersion_id=latestPsv['id'],active=True)
    except:
        deploymentUtils = None
    try:
        fields = ('mediaArtifactVersion__mediaArtifact__name', 'mediaArtifactVersion__version', 'mediaArtifactVersion__mediaArtifact__deployType__type',)
        deployMappings = ProductSetVersionDeployMapping.objects.only(fields).values(*fields).filter(productSetVersion_id=latestPsv['id'])
    except:
        deployMappings = None
    if CNProductSetVersion.objects.filter(drop_version = drop, product_set_version = productSetVersion).exists():
        cnProductSetVersionObj = CNProductSetVersion.objects.filter(drop_version = drop, product_set_version__contains = productSetVersion).order_by('-id')[0]

    return render(request, "cireports/prodSetContent.html",
            {
                'productSet': prodSet,
                'message': msg,
                'drop': drop,
                'product': product,
                'femObj': femObj,
                'contents': contents,
                'athloneProxyProducts': athloneProxyProducts,
                'productSetVersion': productSetVersion,
                'cnProductSetVersion': cnProductSetVersionObj,
                'productSetNumber': productSetNumber,
                'inactiveMedia': inactive,
                'deploymentUtils': deploymentUtils,
                'deployMappings' : deployMappings,
                'enmLocalNexus': str(config.get('DMT_AUTODEPLOY', 'ENM_nexus_url')),
            })

def displayProdSetVersions(request,prodSet,drop):
    product = femObj = "None"
    msg = None
    dropObj = None
    allCNVersions = None
    try:
        prodSetObj = ProductSet.objects.get(name=prodSet)
        product = ProductSetRelease.objects.filter(productSet=prodSetObj)[0].release.product
        prodSetRelObj = ProductSetRelease.objects.filter(productSet=prodSetObj)[0]
        dropObj = Drop.objects.get(name=drop, release__product=product)
        pageHitCounter("ProductSetVersions", dropObj.id, str(request.user))
    except Exception as e:
        logger.error("There was an issue gathering Product Set Content information: " +str(e))

    try:
        allVersions = ProductSetVersion.objects.filter(drop_id=dropObj.id,productSetRelease__release=dropObj.release).order_by('-id')
        allCNVersions, errorMsg = cireports.utils.getAllCNProductSetVersionByDrop(drop)
        if errorMsg != None:
            msg = errorMsg
        if not allVersions:
            msg = "No Historical Product Set Versions have been found for " +str(drop)
            allVersions = None
        allVersionsIds =[]
        for version in allVersions:
            allVersionsIds.append(version.id)
        inactiveList = ProductSetVersionContent.objects.only('productSetVersion__id').values('productSetVersion__id').filter(productSetVersion__id__in=allVersionsIds, mediaArtifactVersion__active=0)
        inactiveMedia = []
        if inactiveList:
            for inactive in inactiveList:
                inactiveMedia.append(inactive['productSetVersion__id'])
    except:
        allVersions = None
        inactiveMedia = None
        msg = "No Historical Product Set Versions have been found for " +str(drop)
    return render(request, "cireports/prodSetContentHistory.html",
            {
                'productSet': prodSet ,
                'message': msg ,
                'drop': dropObj,
                'allVersions': allVersions,
                'allCNVersions': allCNVersions,
                'inactiveMedia': inactiveMedia,
                'product': product,
                'femObj': femObj
            })

def dropIndex(request,product):
    hostname = request.META['HTTP_HOST']
    allDrops = Drop.objects.all().order_by('-name')
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    return render(request, "cireports/drop_index.html", {'drops': allDrops, 'product': product, 'femObj': femObj})

def mediaIndex(request, product):
    isoArtifactList = set()
    try:
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    except:
        raise Http404
    releases = Release.objects.filter(product__name=product)
    for rel in releases:
        isos = ISObuild.objects.filter(drop__release=rel)
        for iso in isos:
            isoArtifactList.add(iso.drop.release.iso_artifact)

    return render(request, "cireports/iso_index.html",
            {
                'isos': isoArtifactList,
                'product': product,
                'femObj': femObj,
            })

def solutionSetIndex(request,product):
    solsets = SolutionSet.objects.all()
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    return render(request, "cireports/solset_index.html", {'solsets': solsets, 'product': product, 'femObj': femObj})

def packageIndex(request,product):
    '''
    Product Package(s) & Testware
    '''
    hostname = request.META['HTTP_HOST']
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    allPackages = allCount = None
    allTestware = pkgsCount = testwareCount = None
    try:
        allPackages, pkgsCount = utils.getPackagesBasedOnProduct(product)
        allTestware, testwareCount = utils.getTestwareBasedOnProduct(product)
        allCount = int(pkgsCount) + int(testwareCount)
    except Exception as e:
        logger.error("There was an issue gathering package infomation: " +str(e))
    return render(request, "cireports/package_index.html",
            {
                'packages': allPackages,
                'testware': allTestware,
                'count':allCount,
                'pkgsCount': pkgsCount,
                'testwareCount': testwareCount,
                'product': product,
                'femObj': femObj
            })

@login_required
def obsolete(request, product, drop):
    '''
    Obsoleting of Package Revision from a Drop
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    if request.method == 'GET':
        logger.info("REQUEST: " +str(request.user))
        id = request.GET.get('id')
        package = request.GET.get('package')
        version = request.GET.get('version')
        platform = request.GET.get('platform')
        signum = str(request.user)
        reason = request.GET.get('reason')
        dpm = DropPackageMapping.objects.only('drop', 'drop__id').values('drop', 'drop__id', 'package_revision__id').get(id=id)
        drp = Drop.objects.only('id', 'status').values('id', 'status').get(name=drop, release__product=product)
        checkResults = utils.obsoleteArtifactInMediaArtifactCheck(product, dpm['package_revision__id'], package, version)
        if "ERROR" in checkResults:
            # This is for when a package cannot be obsoleted due to it being part of an ISO has passed CDB and/or an ISO that is undergoing a CDB test
            logger.info("Package cannot be obsoleted due to it being part of a running or passed ISO.")
            return render(request, "cireports/obsoleteiso_error.html",
                    {
                        'package': package,
                        'version': version,
                        'product': product,
                        'error': checkResults,
                        'drop': drop
                    })
        # Check here for status of drop
        if "open" not in drp['status']:
            user = User.objects.get(username=str(request.user))
            obsoleteGroup = config.get("CIFWK", "adminGroup")
            if not user.groups.filter(name=obsoleteGroup).exists():
                errMsg = "User is not authorised to obsolete from a drop that is not open (" +str(drp) +")"
                logger.info(errMsg)
                return render(request, "cireports/drop_error.html",{'error': errMsg})
        if drp['id'] == dpm['drop__id']:
            return render(request, "cireports/obsolete.html",
                    {
                        'package': package,
                        'id': id,
                        'version': version,
                        'platform': platform,
                        'signum': signum,
                        'reason': reason,
                        'drop': drop,
                        'product': product,
                       'femObj' : femObj
                    })
        else:
            # This is for when the Package Revision was delivered to a different drop and cannot be Obsoleted
            logger.info("Error Package Revision Version should be Obsoleted from the drop it was delivered to")
            return render(request, "cireports/obsolete_error.html" ,
                    {
                        'package': package,
                        'version': version,
                        'notsamedrop': dpm['drop'],
                        'drop': drop,
                        'different': dpm['drop'],
                        'product': product,
                        'femObj' : femObj
                    })
    if request.method == 'POST':
        id = request.POST.get('id')
        package = request.POST.get('package')
        version = request.POST.get('version')
        platform = request.POST.get('platform')
        signum = str(request.user)
        reason = request.POST.get('reason')
        obsolete = utils.obsolete(id,package,platform,signum,reason,drop)
        if not obsolete == "error":
            return HttpResponseRedirect("/" + str(product)+ "/drops/" + str(drop))
        else:
            # This is for when the Package Revision is in a frozen drop and cannot be Obsoleted
            logger.info("Error Package Revision Version in Frozen Drop")
            dpm = DropPackageMapping.objects.only('drop').values('drop').get(id=id)
            return render(request, "cireports/obsolete_error.html" ,
                    {
                        'package': package,
                        'version': version,
                        'drop': drop,
                        'frozen': dpm['drop'],
                        'product': product,
                        'femObj': femObj,
                        'signum': signum
                    })
    return HttpResponseRedirect("/" + str(product)+ "/drops/" + str(drop) )


def obsoleteHistory(request, product, drop):
    hostname = request.META['HTTP_HOST']
    obsoleteHistory = []
    obsoleteHistoryPkgs = []
    obsoleteHistoryTestware = []
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        dropObj = Drop.objects.only('id').values('id').get(name=drop, release__product__name=product)
        pageHitCounter("DropObsoleteHistory", dropObj['id'], str(request.user))
        # get relevant ObsoleteInfo objects from the DB and assign them to obsoleteHistory variable
        obsoleteHistory = ObsoleteInfo.objects.filter(dpm__drop__id=dropObj['id'])
        category = Categories.objects.get(name="testware")
        for obsoleteHis in obsoleteHistory:
            if category == obsoleteHis.dpm.package_revision.category:
                obsoleteHistoryTestware.append(obsoleteHis)
            else:
                obsoleteHistoryPkgs.append(obsoleteHis)
    except ObsoleteInfo.DoesNotExist:
        raise Http404
    return render(request, "cireports/obsoleteInfo.html",
            {
                'obInfo': obsoleteHistory,
                'drop': drop,
                'pkgs':obsoleteHistoryPkgs,
                'testware': obsoleteHistoryTestware,
                'product': product,
                'femObj': femObj
            })

@login_required
def obsoleteMedia(request, prodSet, drop):
    '''
    Obsoleting of Media Artifact Revision from a Drop
    '''
    product = "None"
    femObj = "None"
    if request.method == 'GET':
        logger.info("REQUEST: " +str(request.user))
        id = request.GET.get('id')
        mediaArt = request.GET.get('mediaArtifact')
        version = request.GET.get('version')
        email = request.GET.get('email')
        signum = str(request.user)
        reason = request.GET.get('reason')

        prodSetRel = ProductSetRelease.objects.filter(productSet__name=prodSet)[0]
        dropObj = Drop.objects.get(name=drop, release__product=prodSetRel.release.product)
        productSetRelease = ProductSetRelease.objects.get(release=dropObj.release)
        drp = Drop.objects.get(name=drop, release=productSetRelease.release)
        dpm = DropMediaArtifactMapping.objects.get(id=id)
        if "open" not in drp.status:
            user = User.objects.get(username=str(request.user))
            obsoleteGroup = config.get("CIFWK", "adminGroup")
            if not user.groups.filter(name=obsoleteGroup).exists():
                errMsg = "User is not authorised to obsolete Media from a drop that is not open (" +str(drp) +")"
                logger.info(errMsg)
                return render(request, "cireports/drop_error.html",{'error': errMsg})
        if drp == dpm.drop:
            return render(request, "cireports/obsoleteMedia.html",
                    {
                        'mediaArt': mediaArt,
                        'id': id,
                        'version': version,
                        'signum': signum,
                        'reason': reason,
                        'drop': drop,
                        'productSet':prodSet,
                        'prodSetRel': productSetRelease.name,
                        'product': product,
                       'femObj' : femObj
                    })
        else:
            # This is for when the Package Revision was delivered to a different drop and cannot be Obsoleted
            logger.info("Error Media Artifact Revision Version should be Obsoleted from the drop it was delivered to")
            return render(request, "cireports/obsoleteMediaError.html" ,
                    {
                        'mediaArt': mediaArt,
                        'version': version,
                        'drop': drop,
                        'different': dpm.drop,
                        'productSet':prodSet,
                        'prodSetRel': productSetRelease.name,
                        'product': product,
                        'femObj' : femObj
                    })
    if request.method == 'POST':
        signum = str(request.user)
        prodSetRel = request.POST.get('productSetRelease')
        id = request.POST.get('id')
        mediaArt = request.POST.get('mediaArtifact')
        version = request.POST.get('version')
        email = request.POST.get('email')
        reason = request.POST.get('reason')

        obsolete, data = utils.obsoleteMedia(id,mediaArt,signum,reason,drop, prodSet, prodSetRel, email)
        dpm = DropMediaArtifactMapping.objects.get(id=id)
        if "ERROR" in obsolete:
          if "Content" in obsolete:
            # This is for when the Media Artifact is in a frozen drop and cannot be Obsoleted
            logger.info("Error Media Artifact Version in ")
            return render(request, "cireports/obsoleteMediaError.html" ,
                    {
                        'mediaArt': mediaArt,
                        'version': version,
                        'drop': drop,
                        'productSet':prodSet,
                        'data': data,
                        'product': product,
                        'femObj': femObj,
                        'signum': signum
                    })
          else:
            # This is for when the Media Artifact is in a frozen drop and cannot be Obsoleted
            logger.info("Error Media Artifact Version in Frozen Drop")
            return render(request, "cireports/obsoleteMediaError.html" ,
                    {
                        'mediaArt': mediaArt,
                        'version': version,
                        'drop': drop,
                        'frozen': dpm.drop,
                        'productSet':prodSet,
                        'product': product,
                        'femObj': femObj,
                        'signum': signum
                    })
    return HttpResponseRedirect("/" + str(prodSet)+ "/dropMedia/" + str(drop) )

def obsoleteMediaHistory(request, prodSet, drop):
    hostname = request.META['HTTP_HOST']
    product = "None"
    femObj = "None"
    try:
        # get relevant ObsoleteInfo objects from the DB and assign them to obsoleteHistory variable
        prodSetRel = ProductSetRelease.objects.filter(productSet__name=prodSet)[0]
        dropObj = Drop.objects.only('id').values('id').get(name=drop, release__product=prodSetRel.release.product)
        pageHitCounter("ProductSetDropObsoleteHistory", dropObj['id'], str(request.user))
        obsoleteHistory = ObsoleteMediaInfo.objects.filter(dropMediaArtifactMapping__drop__id=dropObj['id'])
    except ObsoleteInfo.DoesNotExist:
        raise Http404
    return render(request, "cireports/obsoleteMediaInfo.html",
            {
                'obInfo': obsoleteHistory,
                'drop': drop,
                'productSet': prodSet,
                'product': product,
                'femObj': femObj
            })


def dropMediaStatus(request, prodSet, drop, type=None):
    '''
    The dropStatus function display the status of drops on the Portal UI
    '''
    lastBuiltISO = frozen = None
    productSetRelease = drp = mediaArtifacts = None
    product = "None"
    femObj = "None"
    hostname = request.META['HTTP_HOST']
    athloneProxyProducts = ast.literal_eval(config.get("CIFWK", "athlone_proxy_products"))
    try:
        prodSetRel = ProductSetRelease.objects.filter(productSet__name=prodSet)[0]
        dropObj = Drop.objects.get(name=drop, release__product=prodSetRel.release.product)
        productSetRelease = ProductSetRelease.objects.get(release=dropObj.release)
        drp = Drop.objects.get(name=drop, release=productSetRelease.release)
        frozenDate =  drp.mediaFreezeDate
        mediaArtifacts = utils.getMediaBaseline(drp.id, type)
    except Exception as e:
        logger.error("Error: " + str(e))
        raise Http404
    try:
        latestPsv = ProductSetVersion.objects.filter(drop_id=dropObj.id,productSetRelease__release=dropObj.release).order_by('-id')[0]
        contents = ProductSetVersionContent.objects.filter(productSetVersion=latestPsv)
    except:
        latestPsv = contents = None

    return render(request, "cireports/media_drop_table.html",
            {
                'mediaArtifacts': mediaArtifacts,
                'drop': drp,
                'productSet': prodSet,
                'productSetRel': productSetRelease,
                'product': product,
                'femObj': femObj,
                'athloneProxyProducts': athloneProxyProducts,
                'iso':lastBuiltISO,
                'frozen': frozen,
                'latestContents': contents,
                'enmLocalNexus': str(config.get('DMT_AUTODEPLOY', 'ENM_nexus_url')),
            })


# REST Calls for status

def packageBuildStatus(request,product,package):
    # TODO: turn this into a generic method that returns XML/JSON describing the entire package revision instance
    try:
        cLevel = Clue.objects.get(package__name=package)
    except Exception as e:
        cLevel = None
    try:
        #Need an exist if product not not exist
        if Product.objects.filter(name=product).exists():
            product = Product.objects.get(name=product)
            femObj = FEMLink.objects.filter(product=product)
        else:
            product = "None"
            femObj = "None"
    except Package.DoesNotExist:
        raise Http404
    return render(
                request, "cireports/package_buildinfo.html",
                {
                    'product': product,
                    'femObj': femObj,
                    'clue': cLevel
                }
                )

@gzip_page
def packageVersionsStatus(request,product,package):
    # TODO: turn this into a generic method that returns XML/JSON describing the entire package revision instance
    try:
        page = request.GET.get('page')
        pkg = Package.objects.get(name=package)
        requiredPackageRevisionFields = ('id','package_id','package__name','package__testware','version','category__name','package__package_number','m2type','date_created','non_proto_build','autodrop','kgb_test','cid_test','cdb_test','infra','isoExclude','kgb_snapshot_report', 'arm_repo', 'groupId','artifactId','team_running_kgb__parent__element', 'team_running_kgb__element','platform','size')
        allRevs = PackageRevision.objects.filter(package=pkg.id).order_by('-date_created').exclude(platform="sparc").only(requiredPackageRevisionFields).values(*requiredPackageRevisionFields)
        objectsPerPage = config.get("CIFWK", "objectsPerPage")
        paginator = Paginator(allRevs, objectsPerPage)
        if (page != "all"):
            try:
                allRevsPag = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                allRevsPag = paginator.page(1)
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                allRevsPag = paginator.page(paginator.num_pages)
            allRevs = allRevsPag.object_list

        packageRevisionIds = []
        for packageRevision in allRevs:
            packageRevisionIds.append(packageRevision['id'])
            packageRevision['RState'] = convertVersionToRState(packageRevision['version'])
            packageRevision['nexusUrl'] = utils.getNexusUrl(product, packageRevision['arm_repo'], packageRevision['groupId'], packageRevision['artifactId'], packageRevision['version'], packageRevision['package__name'], packageRevision['m2type'])
            if packageRevision['size'] != 0:
                packageRevision['size'] = round(float(packageRevision['size'])/float(1024*1024),3)
            else:
                packageRevision['size'] = "--"

        requiredDropPackageMappingFields = ('id', 'package_revision__id', 'drop__release__product__name', 'drop__release__product__id', 'drop__release__name', 'obsolete', 'released', 'drop__name')
        drops = DropPackageMapping.objects.filter(package_revision__id__in=packageRevisionIds).order_by('-drop').only(requiredDropPackageMappingFields).values(*requiredDropPackageMappingFields)

        #Need an exist if product not not exist
        if Product.objects.filter(name=product).exists():
            product = Product.objects.get(name=product)
            femObj = FEMLink.objects.filter(product=product)
        else:
            product = "None"
            femObj = "None"
    except Package.DoesNotExist:
        raise Http404

    requiredIsoMappingFields = ('package_revision_id',)
    isoMappings = ISObuildMapping.objects.filter(package_revision_id__in=packageRevisionIds).distinct().only(requiredIsoMappingFields).values(*requiredIsoMappingFields)
    return render(
                request, "cireports/package_table.html",
                {
                    'package': allRevs,
                    'name': package,
                    'drops': drops,
                    'product': product,
                    'femObj': femObj,
                    'isoMappings': isoMappings
                }
                )

def packageVersionsStatusJson(request, package):
    try:
        pkg = Package.objects.get(name=package)
        allRevs = PackageRevision.objects.filter(package=pkg.id).order_by('-date_created')
        drops = utils.getListOfDrops(allRevs, True)
        dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime) else None
        data = []
        for pkg in allRevs:
            dropListT1 = ""
            for drop in drops:
               if (drop.package_revision == pkg):
                    dropListT1 = dropListT1 + "," +str(drop.drop.name)
            dropList = dropListT1.lstrip(',')
            data1 = [
                {
                    "name": pkg.package.name,
                    "cxp":  pkg.package.package_number,
                    "responsible":  pkg.package.signum,
                    "version": pkg.version,
                    "rstate": pkg.getRState,
                    "drops": dropList,
                    "datecreated": pkg.date_created,
                    "3pp": pkg.non_proto_build,
                    "kgb": pkg.kgb_test,
                    "cdb": pkg.cdb_test,
                    "download": pkg.getNexusUrl(),
                },
                ]
            data = data + data1
    except Package.DoesNotExist:
        raise Http404
    return HttpResponse(json.dumps(data, default=dthandler), content_type="application/json")

@gzip_page
def dropStatus(request, product, drop, filterElements=None):
    # First lets get the list of ancesters for this drop, so we can use it later when searching for related packages
    dropObj = Drop.objects.filter(release__product__name=product,name=drop).only('id')[0]
    dropId = dropObj.id
    dropAncestorIds = dropObj.getAncestorIds()

    # Get all of the required fields from the product
    requiredProductFields=('pkgName','pkgNumber','pkgVersion','pkgRState','platform','category','intendedDrop','deliveredTo','date','kgbTests','obsolete','size')
    productObj = Product.objects.filter(name=product).only(requiredProductFields)
    productFields = productObj.values(*requiredProductFields)[0]

    # Find all of the packaga revision ids for the dropAncestors. Later we can trim down that list so there is only one of each package
    initialDropPackageMappings = DropPackageMapping.objects.select_related('package_revision__package').filter(drop__id__in=dropAncestorIds,released=1,obsolete=0).exclude(package_revision__platform='sparc').exclude(package_revision__package__obsolete_after__id__in=dropAncestorIds,package_revision__package__obsolete_after__id__lt=dropId).order_by('-drop__id').only('package_revision__package__id')

    # If the user selected to filter by a list of teams, narrow down the filter further
    if "null" not in str(filterElements):
            elements = str(filterElements).split(",")
            packages = PackageComponentMapping.objects.filter(component__element__in=elements).values_list('package_id',flat=True)
            initialDropPackageMappings = initialDropPackageMappings.filter(package_revision__package__id__in=packages)

    # Now lets make sure theres only one of each package by looping through the results and keeping track of the first of each package id we find
    filteredDropPackageMappingsDict = {}
    for dpm in initialDropPackageMappings:
        if not dpm.package_revision.package.id in filteredDropPackageMappingsDict or (dpm.drop.id == dropId):
            filteredDropPackageMappingsDict[dpm.package_revision.package.id]=dpm.id
    filteredDropPackageMappingIds = filteredDropPackageMappingsDict.values()

    # Build up a list of required fields, depending on what fields are enabled for the product
    requiredPackageMappingFieldMatrix = {
        'pkgName':      ('package_revision__package__name',),
        'pkgNumber':    ('package_revision__package__package_number',),
        'pkgVersion':   ('package_revision__package__name', 'package_revision__version', 'package_revision__arm_repo', 'package_revision__groupId', 'package_revision__artifactId', 'package_revision__m2type'),
        'pkgRState':    ('package_revision__version',),
        'platform':     ('package_revision__platform',),
        'category':     ('package_revision__category__name', 'package_revision__isoExclude', 'package_revision__infra'),
        'intendedDrop': ('package_revision__autodrop',),
        'deliveredTo':  ('drop__name',),
        'date':         ('date_created',),
        'kgbTests':     ('package_revision__kgb_test', 'package_revision__kgb_snapshot_report', 'kgb_test', 'testReport', 'kgb_snapshot_report'),
        'obsolete':     ('id', 'package_revision__package__name', 'package_revision__version', 'package_revision__platform'),
        'size':         ('package_revision__size',)
    }

    requiredDropPackageMappingFields=[]
    for productField in requiredPackageMappingFieldMatrix:
        if productFields[productField]:
            requiredDropPackageMappingFields.extend(requiredPackageMappingFieldMatrix[productField])

    # Get the required fields from the drop package mapping ids we identified earlier
    dropPackageMappingObjs = DropPackageMapping.objects.prefetch_related('drop','package_revision__category').filter(id__in=filteredDropPackageMappingIds).order_by('-date_created').only(tuple(requiredDropPackageMappingFields))
    dropPackageMappingFields = list(dropPackageMappingObjs.values(*requiredDropPackageMappingFields))

    # Enrich the data with other information that can't be got back as normal database fields, again only if these are required for this product
    for dpm in dropPackageMappingFields:
        if (productFields['pkgRState']):
            dpm['RState'] = convertVersionToRState(dpm['package_revision__version'])
        if (productFields['pkgVersion']):
            dpm['nexusUrl'] = utils.getNexusUrl(product,dpm['package_revision__arm_repo'],dpm['package_revision__groupId'],dpm['package_revision__artifactId'],dpm['package_revision__version'],dpm['package_revision__package__name'],dpm['package_revision__m2type'])
        if (productFields['date']):
            dpm['date_created'] = dpm['date_created'].strftime("%Y-%m-%d %H:%M:%S")

    returnedObject = {
        'dropPackageMappings': dropPackageMappingFields,
        'product': productFields
    }
    return HttpResponse(json.dumps(returnedObject,cls=DjangoJSONEncoder), content_type="application/json")

def setPackageStatus(packages,drp):
    packageStatus = {}
    packageList = []

    try:
        latestIso = ISObuild.objects.filter(drop=drp, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-id')[0].only('id')
        isoPkgMapping = ISObuildMapping.objects.filter(iso=latestIso.id)
        for package in packages:
            for pkg in isoPkgMapping:
                if package.package_revision_id == pkg.package_revision_id:
                    if package not in packageList:
                        packageStatus[package] = pkg.overall_status.state
                        packageList.append(package)
            if package not in packageList:
                packageStatus[package] = 'not_started'
                packageList.append(package)
        packages = packageStatus
    except:
        for package in packages:
            if package not in packageList:
                packageStatus[package] = 'not_started'
                packageList.append(package)
        packages = packageStatus
    packages = packages.items()
    return packages

def paginator(objects,page):
    '''
    Function to allow for paging when displaying an object
    '''
    objectsPerPage = config.get("CIFWK", "objectsPerPage")
    try:
        paginator = Paginator(objects, objectsPerPage)
    except Exception as e:
        logger.error("Issue with paginator: " +str(e))
        return 1
    if (page == "all"):
        allObjPag=objects
    else:
        try:
            allObjPag = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            allObjPag = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            allObjPag = paginator.page(paginator.num_pages)
    return allObjPag

def dropCDBStatus(request,product,drop,isoId):
    isoObj = isoVersion = allStatusUni = allStatus = None
    try:
        custDeployBases = None
        isoObj=ISObuild.objects.get(id=isoId)
        isoVersion = isoObj.version
        allStatusUni = isoObj.current_status
        allStatus=ast.literal_eval(allStatusUni)
        status=isoObj.getCurrentCDBStatuses()
        return render(
                    request, "cireports/drop_cdb_table.html",
                    {
                        'cdbs':status,
                        'product': product,
                        'drop': drop,
                        'isoVersion': isoVersion
                    }
                    )
    except:
        return render(
                request, "cireports/drop_cdb_table.html",{'cdbs':"",'product': product, 'drop': drop, 'isoVersion': isoVersion })


def solutionSetStatus(request, product, solset):
    try:
        ss = SolutionSet.objects.get(name=solset)
        solsetvers = SolutionSetRevision.objects.filter(solution_set=ss)
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    except SolutionSet.DoesNotExist:
        raise Http404
    logger.info("Solution Set Status")
    return render(request, "cireports/solutionset_table.html", {'solsetvers': solsetvers, 'solset': ss, 'product': product, 'femObj': femObj})

def solutionSetRevisionStatus(request, product, solset, version):
    try:
        ss = SolutionSet.objects.get(name=solset)
        ssv = SolutionSetRevision.objects.get(solution_set=ss, version=version)
        packages = SolutionSetContents.objects.filter(solution_set_rev=ssv)
    except SolutionSet.DoesNotExist:
        raise Http404
    except SolutionSetRevision.DoesNotExist:
        raise Http404
    logger.info("Solution Set revision Status")
    return render(request, "cireports/solutionsetversion_table.html", {'solsetver': ssv, 'packages': packages})

@login_required
def viewPRI(request,product,cxp,platform=None,version=None,type=None):
    try:
        pkg_info = Package.objects.get(package_number=cxp)
        if version != None and platform == "None":
            pkgRev = PackageRevision.objects.get(package=pkg_info, version=version, m2type=type)
        elif version != None and platform != "None":
            pkgRev = PackageRevision.objects.get(package=pkg_info, version=version, platform=platform, m2type=type)
    except  Package.DoesNotExist:
        raise Http404
    try:
        if version != None:
            all_info = pri.objects.filter(pkgver=pkgRev).order_by('-drop')
        else:
            all_info = pri.objects.filter(pkgver__package__package_number=cxp).order_by('-drop')
    except  pri.DoesNotExist:
         raise Http404
    #ensure product exists saves ui failue
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    return render(request, "cireports/pri.html",
            {
                'items': all_info,
                'name':pkg_info.name ,
                'cxp':pkg_info.package_number,
                'product': product,
                'femObj': femObj
            })

@login_required
def primOptions(request, product=None):
    '''
    For Selecting a option and drop
    '''
    user = User.objects.get(username=str(request.user))
    primGroup = config.get("CIFWK", "primGroup")
    if not user.groups.filter(name=primGroup).exists():
        return render(request, "cireports/prim_error.html",{'error':'User not authorised to write to PRIM, please contact CM responsible'})

    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        return render(request, "cireports/prim_error.html",{'error': 'Invalid product'})

    fh = FormHandle()
    fh.product = product
    fh.form = PrimOptionForm(product.name)
    fh.title = "Select Option and Drop for this Prim Update"
    fh.request = request
    fh.button = "Next ..."
    if request.method == "GET":
        return fh.display()
    if request.method == 'POST':
        fh.form = PrimOptionForm(product.name, request.POST)
        drop = request.POST.get("drop")
        options = request.POST.get("options")
        if fh.form.is_valid():
            if options == "product_structure":
               fh.redirectTarget = ("/" + str(product.name)+ "/"  + str(drop) + "/prim/")
               return fh.success()
            elif options == "cxp_number":
               fh.redirectTarget = ("/" + str(product.name)+ "/"  + str(drop) + "/primCXP/")
               return fh.success()
            else:
                fh.failure()
        else:
            return fh.failure()

def primCXP(request, product=None, drop=None):
    '''
        Getting Prim Details for CXP updates
    '''
    results = []
    user = User.objects.get(username=str(request.user))
    primGroup = config.get("CIFWK", "primGroup")
    if not user.groups.filter(name=primGroup).exists():
        return render(request, "cireports/prim_error.html",{'error':'User not authorised to write to PRIM, please contact CM responsible'})


    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        return render(request, "cireports/prim_error.html",{'error': 'Invalid product'})
    fh = FormHandle()
    fh.product = product
    fh.title = "Prim Details for CXP Updates"
    fh.request = request
    fh.form = PrimCXPForm(product.name, drop)
    if request.method == "GET":
        return render(request, "cireports/primCXP.html", { 'form': fh.form, 'drop': drop, 'product': product})
    if request.method == 'POST':
       media = request.POST.get("media")
       user = request.POST.get("username")
       password = request.POST.get("password")
       try:
           result=utils.primCXP(product.name, drop, media, user, password)
       except Exception as e:
           logger.error("Error with Prim CXP Function" + str(e))
       if not "error" in result:
          return render(request, "cireports/primCXP_result.html", {
                       'product': product,
                       'drop': drop,
                       'media':media,
                       'user': user,
                       'password':password,
                       'dataList': result['dataList'],
                       'diffData': result['unknownPackages'],
                       'packages' : result['packages']
                       })
       else:
           return render(request, "cireports/prim_error.html")
    return render(request, "cireports/prim_error.html")



def updatePrimCXP(request, product=None, drop=None):
    '''
    Writing to prim new CXPs RStates and getting a Report.
    '''
    result = []
    errorMsg = ""
    failure = ""
    user = User.objects.get(username=str(request.user))
    primGroup = config.get("CIFWK", "primGroup")
    if not user.groups.filter(name=primGroup).exists():
        return render(request, "cireports/prim_error.html",{'error':'User not authorised to write to PRIM, please contact CM responsible'})


    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        return render(request, "cireports/prim_error.html",{'error': 'Invalid product'})

    media = request.POST.get('media', "")
    user = request.POST.get('user', "")
    password = request.POST.get('password', "")
    packages = request.POST.getlist('package')
    try:
        result,failure=utils.updatePrimCXP(product.name, drop, media, user, password, packages)
    except Exception as e:
        logger.error("Error Issue with updating PRIM: " + str(e))
    if not "error" in result:
        if failure == True:
            errorMsg = "Failures in the Report, Please write a JIRA"
        return render(request, "cireports/prim_updated.html", {
            'report': result, 'error': errorMsg, })
    return render(request, "cireports/prim_error.html")


def prim(request, product=None, drop=None):
    '''
    For Prim Details and Information
    '''
    media = None

    user = User.objects.get(username=str(request.user))
    primGroup = config.get("CIFWK", "primGroup")
    if not user.groups.filter(name=primGroup).exists():
        return render(request, "cireports/prim_error.html",{'error':'User not authorised to write to PRIM, please contact CM responsible'})


    #If product does not exist ui will not crash
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        return render(request, "cireports/prim_error.html",{'error': 'Invalid product'})

    result = []
    fh = FormHandle()
    fh.product = product
    fh.title = "Prim Details"
    fh.request = request
    fh.form = PrimForm(product.name, drop)
    if request.method == "GET":
        cancel = request.GET.get('cancel', "")
        user = request.GET.get('user', "")
        file = request.GET.get('file', "")
        if cancel == "True":
            cireports.prim.deleteSqlFile(user, file)
        return render(request, "cireports/prim.html", { 'form': fh.form, 'drop': drop, 'product': product})
    if request.method == 'POST':
       rState = request.POST.get("rstate")
       topProduct =  request.POST.get("baseproduct")
       topRev = request.POST.get("baserevision")
       user = request.POST.get("username")
       password = request.POST.get("password")
       newRelease = request.POST.get("newrelease")
       media = request.POST.get("media")
       if newRelease == None:
           newRelease = False
       else:
           newRelease = True
       if not rState:
           rState = None
       try:
           result=utils.prim(drop, product, media, rState, topProduct, topRev, user, password, newRelease)
       except Exception as e:
           logger.error("Error when getting Prim information " + str(e))
       if not "error" in result:
          return render(request, "cireports/prim_result.html", {
                       'product': product,
                       'drop': drop,
                       'media': media,
                       'user': user,
                       'password':password,
                       'dataList': result['dataList'],
                       'diffData': result['diff'],
                       'file' : result['file']
                       })
       else:
           return render(request, "cireports/prim_error.html")
    return render(request, "cireports/prim_error.html")

def updatePrim(request, product=None):
    '''
    Writing to prim and deleting the sql file after.
    '''
    user = User.objects.get(username=str(request.user))
    primGroup = config.get("CIFWK", "primGroup")
    if not user.groups.filter(name=primGroup).exists():
        return render(request, "cireports/prim_error.html",{'error':'User not authorised to write to PRIM, please contact CM responsible'})

    drop = request.GET.get('drop', "")
    media = request.GET.get('media', "")
    user = request.GET.get('user', "")
    password = request.GET.get('password', "")
    write = request.GET.get('write', "")
    file = request.GET.get('file', "")
    if write == "True":
        write = True
    try:
        result=utils.updatePrim(drop, media, user, password, write, file)
    except Exception as e:
       logger.error(str(e))
    if not "error" in result:
        return render(request, "cireports/prim_updated.html")
    return render(request, "cireports/prim_error.html")

def displayTestware(request, product):
    '''
    Display Testware associated with a particular product
    '''

    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    return render(request, "cireports/testware.html",
            {
                'product': product,
                'femObj': femObj
            })

def displayTestwareArtifacts(request, product):
    '''
    Display the testware artifacts that are associated with a specific product
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        pageHitCounter("Testware", product.id, str(request.user))
    else:
        product = "None"
    testwareArtifacts = cireports.utils.getTestwareByProduct(product)
    return render(request, "cireports/testware_table.html",
                {
                    'testwareArtifacts': testwareArtifacts,
                    'product': product
                })


def displayUnMappedTestware(request, product):
    '''
    Display Testware that is not mapped to a product
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        pageNo = request.GET['page']
    except Exception as e:
        pageNo = 1
    unMappedTestware = cireports.utils.getUnMappedTestware()
    page = request.GET.get('page')
    allTestwareArtifacts = paginator(unMappedTestware,page)
    pkgCount = len(unMappedTestware)
    return render(request, "cireports/unmappedtestware.html",
            {
                'allTestwareArtifacts': allTestwareArtifacts,
                'unMappedTestware' : unMappedTestware,
                'count': pkgCount,
                'pageNo': pageNo,
                'product': product,
                'femObj': femObj
            })


def displayUnMappedTestwareArtifacts(request, product):
    '''
    Display the testware artifacts that are not mapped to a product
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        pageHitCounter("UnMappedTestware", product.id, str(request.user))
    else:
        product = "None"
    unMappedTestware = cireports.utils.getUnMappedTestware()
    page = request.GET.get('page')
    allTestwareArtifacts = paginator(unMappedTestware,page)
    pkgCount = len(unMappedTestware)
    return render(request, "cireports/unmappedtestware_table.html",
                {
                    'unMappedTestware': allTestwareArtifacts,
                    'count': pkgCount,
                    'product': product
                })

def showTestwareVersionsAll(request,product,artifact):
    '''
    Display testware artifact revision
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        pageNo = request.GET['page']
    except Exception as e:
        pageNo = 1
    hostname = request.META['HTTP_HOST']
    try:
        artifact = TestwareArtifact.objects.get(name=artifact)
    except TestwareArtifact.DoesNotExist:
        return render(request, "cireports/testwarerevision.html",
            {
                'error': "Please ensure the artifact entered \"" + str(artifact) + "\" exists",
            })

    if not ProductPackageMapping.objects.filter(product=product, package__hide=0, package__testware=1, package__name=artifact).exists():
        return render(request, "cireports/testwarerevision.html",
            {
                'error': "Artifact: '" + str(artifact) + "' has no Associations with chosen Product: '" + str(product) + "'",
            })
    testwareArtifacts = TestwareRevision.objects.filter(testware_artifact=artifact).order_by('-date_created')
    page = request.GET.get('page')
    allTestwareArtifacts = paginator(testwareArtifacts,page)
    pkgCount = len(testwareArtifacts)
    return render(request, "cireports/testwarerevision.html",
            {
                'allTestwareArtifacts': allTestwareArtifacts,
                'artifacts': testwareArtifacts,
                'artifact' : artifact,
                'count': pkgCount,
                'pageNo': pageNo,
                'product': product,
                'femObj': femObj
            })


def displayTestwareVersions(request,product,artifact):
    '''
    Return all versions of a testware artifact/all artifacts
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        product = "None"
    artifact = TestwareArtifact.objects.get(name=artifact)
    testwareArtifacts = TestwareRevision.objects.filter(testware_artifact=artifact).order_by('-date_created')
    latestProductDrop = Drop.objects.filter(release__product__name=product).order_by('-id')[0].name
    if TestwareRevision.objects.filter(testware_artifact=artifact,obsolete=False).exists():
        latestTestware = TestwareRevision.objects.filter(testware_artifact=artifact,obsolete=False).order_by('-date_created')[0]
    else:
        latestTestware = TestwareRevision.objects.filter(testware_artifact=artifact).order_by('-date_created')[0]
    page = request.GET.get('page')
    allTestwareArtifacts = paginator(testwareArtifacts,page)
    pkgCount = len(testwareArtifacts)
    return render(request, "cireports/testwarerevision_table.html",
                {
                    'artifacts': allTestwareArtifacts,
                    'artifact' : artifact,
                    'count': pkgCount,
                    'product': product,
                    'latestTestware':latestTestware,
                    'latestProductDrop': latestProductDrop,
                })


@login_required
def mapTestware(request,product):
    '''
    Create mapping between testware and package
    '''
    error = ""
    message = ""
    options = []
    optionsP = []
    state = False
    testwareMapping = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    if request.method == "GET":
        logger.info("Testware Mapping request")
    elif request.method =='POST':
        package = str(request.POST.get('package'))
        testware = str(request.POST.get('testware_artifact'))
        if package:
            packageObj = Package.objects.get(name=package)
        else:
            packageObj = ""
        if testware:
            testwareObj = TestwareArtifact.objects.get(name=testware)
        else:
            testwareObj = ""
        if packageObj and testwareObj:
            if TestwarePackageMapping.objects.filter(testware_artifact=testwareObj,package=packageObj).exists():
                error = "Error: Mapping exists"
            else:
                testwareMapping = TestwarePackageMapping(testware_artifact=testwareObj,package=packageObj)
                testwareMapping.save()
                message = "Mapping Created: "
        else:
            error = "Form Not Valid"
    pkgList,allCount = cireports.utils.getPackagesBasedOnProduct(product)
    testwareArtifactList, packageList, options = cireports.utils.generateTestwareMappingForms(product,pkgList,options)
    choices = cireports.utils.populateTestwareChoices()
    choicesP = cireports.utils.getPackageChoices()
    formOptions = TWOptions(choices, options, state, choicesP, optionsP)
    form = TWMappingForm(testwareArtifactList, packageList)
    if testwareMapping:
        created = testwareMapping
    else:
        created = " "
    all = cireports.utils.getTestwareMap(product,pkgList)
    return render(request,"cireports/update_testwaremapping.html",
                {
                    'product':product,
                    'femObj': femObj,
                    'form': form,
                    'formOptions': formOptions,
                    'all': all,
                    'created' : created,
                    'error':error,
                    'message':message
                })

    return render(request, "cireports/testwaremappings.html", args)


@login_required
def deleteTestwareMapping(request,product,mappingID):
    '''
    Remove testware-product mapping
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    error = ""
    message = ""
    options = []
    optionsP = []
    state = False
    if TestwarePackageMapping.objects.filter(id=mappingID).exists():
        mapObj=TestwarePackageMapping.objects.filter(id=mappingID)
        mapObj.delete()
        message = "Mapping Deleted Successfully"
    else:
        error = "Error Occurred When Trying To Delete Mapping"

    pkgList,allCount = cireports.utils.getPackagesBasedOnProduct(product)
    testwareArtifactList, packageList, options = cireports.utils.generateTestwareMappingForms(product,pkgList,options)
    all = cireports.utils.getTestwareMap(product,pkgList)
    choices = cireports.utils.populateTestwareChoices()
    choicesP = cireports.utils.getPackageChoices()
    formOptions = TWOptions(choices, options, state, choicesP, optionsP)
    form = TWMappingForm(testwareArtifactList, packageList)
    return render(request, "cireports/update_testwaremapping.html",
                {
                    'product':product,
                    'femObj': femObj,
                    'form': form,
                    'formOptions': formOptions,
                    'all': all,
                    'error':error,
                    'message':message
                })


def generateTestwareArtifacts(request,product):
    '''
    Populate the Testware Artifact List
    '''
    error = ""
    message = ""
    allartifact = None
    options = []
    optionsP = []
    packageList = []
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        pageHitCounter("MappingTestware", product.id, str(request.user))
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    if request.method == "GET":
        logger.info("Testware Mapping request")
    elif request.method =='POST':
        allartifact = request.POST.getlist('all_artifact')
        options = request.POST.getlist('artifact_options')
        optionsP = request.POST.getlist('package_options')
        if not options and not allartifact:
            logger.error("Form Not Valid please try again")
            error = "Form Not Valid"
    if optionsP:
        for option in optionsP:
            if 'All' == option or 'Delivered' == option:
                if 'All' == option:
                    pkgs = Package.objects.all().exclude(hide=1).exclude(testware=1)
                    optionsP = 'All'
                else:
                    pkgs, allCount = cireports.utils.getPackagesBasedOnProduct(product)
                    optionsP = 'Delivered'
                packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgs]
                packages = sorted(packageList, key=lambda tup: tup[1].lower())
            if 'AllDelivered' == option:
                pkgs = Package.objects.all().exclude(hide=1).exclude(testware=1)
                packages = cireports.utils.getAllDeliveredPackages(pkgs)
                optionsP = 'AllDelivered'
            if 'UnDelivered' == option:
                pkgs = Package.objects.all().exclude(hide=1).exclude(testware=1)
                packages = cireports.utils.getUnDeliveredPackages(pkgs)
                optionsP = 'UnDelivered'
            if 'Mapped' == option:
                pkgs, allCount = cireports.utils.getPackagesBasedOnProduct(product)
                packages = cireports.utils.getMappedPackages(pkgs)
                optionsP = 'Mapped'
            if 'UnMapped' == option:
                pkgs, allCount = cireports.utils.getPackagesBasedOnProduct(product)
                packages = cireports.utils.getUnMappedPackages(pkgs)
                optionsP = 'UnMapped'
            if 'AllMapped' == option:
                pkgs = Package.objects.all().exclude(hide=1).exclude(testware=1)
                packages = cireports.utils.getMappedPackages(pkgs)
                optionsP = 'AllMapped'
            if 'AllUnMapped' == option:
                pkgs = Package.objects.all().exclude(hide=1).exclude(testware=1)
                packages = cireports.utils.getUnMappedPackages(pkgs)
                optionsP = 'AllUnMapped'
    else:
        pkgs, allCount = cireports.utils.getPackagesBasedOnProduct(product)
        packageList = []
        packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgs]
        packages = sorted(packageList, key=lambda tup: tup[1].lower())
    if allartifact:
        pkgList, allCount = cireports.utils.getPackagesBasedOnProduct(product)
        testwareArtifactList, packageList, options, state = cireports.utils.generateAllTestware(pkgList)
    else:
        pkgList, allCount = cireports.utils.getPackagesBasedOnProduct(product)
        testwareArtifactList, packageList, options = cireports.utils.generateTestwareMappingForms(product,pkgList,options)
        state = False
    all = cireports.utils.getTestwareMap(product,pkgList)
    choices = cireports.utils.populateTestwareChoices()
    choicesP = cireports.utils.getPackageChoices()
    form = TWMappingForm(testwareArtifactList, packages)
    formOptions = TWOptions(choices, options, state, choicesP, optionsP)
    return render(request,"cireports/update_testwaremapping.html",
                {
                    'product':product,
                    'femObj': femObj,
                    'form': form,
                    'formOptions': formOptions,
                    'all': all,
                    'error': error,
                    'message': message
                })

def viewTestwareMapping(request,product,artifact):
    '''
    View Testware/Package Mapping for specific artifact
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    mapping, packageObj = cireports.utils.getTestwareMapping(product,artifact)
    return render(request, "cireports/testwaremappings.html",
        {
            'artifact':artifact,
            'packageObj':packageObj,
            'mapping': mapping,
            'product':product,
            'femObj': femObj
        })


@login_required
def deleteTWMapping(request,product,artifact,mappingID):
    '''
    Remove testware-package mapping
    '''
    error = ""
    message = ""
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    if TestwarePackageMapping.objects.filter(id=mappingID).exists():
        mapObj=TestwarePackageMapping.objects.filter(id=mappingID)
        mapObj.delete()
        okmessage = "Mapping Deleted"
    else:
        error = "Error deleteing mapping"
    mapping, packageObj = cireports.utils.getTestwareMapping(product,artifact)
    return render(request, "cireports/testwaremappings.html",
            {
                'artifact':artifact,
                'packageObj':packageObj,
                'mapping': mapping,
                'product':product,
                'femObj': femObj,
                'error' : error,
                'message': okmessage
            })

@login_required
def obsoleteTestware(request,product,ID):
    '''
    Obsolete testware artifact
    '''
    product = Product.objects.get(name=product)
    obj=TestwareRevision.objects.get(id=ID)
    obj.obsolete=True
    obj.save()
    artifact = TestwareArtifact.objects.get(name=obj.testware_artifact.name)
    return HttpResponseRedirect("/"+str(product.name)+"/testware/showall/"+str(artifact))

@login_required
def reactivateTestware(request,product,ID):
    '''
    Reactivate testware artifact
    '''
    product = Product.objects.get(name=product)
    obj= TestwareRevision.objects.get(id=ID)
    obj.obsolete=False
    obj.kgb_status=1
    obj.cdb_status=0
    obj.save()
    artifact = TestwareArtifact.objects.get(name=obj.testware_artifact.name)
    return HttpResponseRedirect("/"+str(product.name)+"/testware/showall/"+str(artifact))

def displayGAT(request,product,drop):
    '''
     Build up Test Case Data Object to contain TestCase Information,
     Action Points & Verification Points for the GAT Document
    '''
    product = Product.objects.get(name=product)
    # Using the drop and product to get the Track
    drop = Drop.objects.get(name=drop, release__product=product)
    track = drop.release.track
    tcData = {}
    # building up the string for the GAT
    gatTest  = str(product.name) +"_GAT_"+ str(track)
    testCases = TestCase.objects.filter(groups__icontains=str(gatTest))
    # User Stories
    stories = UserStory.objects.all().order_by('-name')
    uslist = []
    testlist = []
    # Getting latest Versions of the User Stories
    for s in stories:
        us = UserStory.objects.filter(name=s.name).latest('version')
        userStory = str(us.id).replace("L", '')
        uslist.append(int(userStory))
    # Using the List of User Stories id to get TestCaseUserStoryMapping
    tcusMap = TestCaseUserStoryMapping.objects.filter(user_story__id__in=uslist)
    for ut in tcusMap:
        for t in testCases:
            # Using filtered list of objects to check for matching testCase ids
            if t.id == ut.test_case.id:
                testCase = str(ut.id).replace("L", '')
                testlist.append(int(testCase))
    #Using the List of TestCaseUserStoryMapping ids to get correct update information
    tcus = TestCaseUserStoryMapping.objects.filter(id__in=testlist)
    count = tcus.count()
    femObj = FEMLink.objects.filter(product=product)
    for testcaseOb in tcus:
        apData = {}
        for ap in ActionPoint.objects.filter(testCase=testcaseOb.test_case):
            apData[ap] = VerificationPoint.objects.filter(actionPoint=ap)
        tc = testcaseOb.test_case
        tcData[tc] = apData
    return render(request, "cireports/gat_info.html",
            {
                'tcData': tcData,
                'total': count,
                'drop' : drop,
                'product':product,
                'femObj': femObj
            })

def allPackages(request):
    '''
    The allPackages def is called to display all packages on the CI Portal
    '''
    allPackages = Package.objects.all().exclude(hide=True).exclude(testware=1).order_by('name')
    allCount = len(allPackages)

    return render(request, "cireports/allPackages_index.html", {'packages': allPackages, 'count':allCount})

def allArtifacts(request):
    '''
    The allPackages def is called to display all packages on the CI Portal
    '''
    pageHitCounter("ArtifactList", None, str(request.user))
    allPackages = []
    allTestware = []
    pkgs = Package.objects.all().exclude(hide=True).order_by('name')
    for pkg in pkgs:
        if pkg.testware == 1:
            allTestware.append(pkg)
        else:
            allPackages.append(pkg)
    allCountPkgs = len(allPackages)
    allCountTw = len(allTestware)
    allCount = int(allCountPkgs) + int(allCountTw)
    return render(request, "cireports/allPackages_index.html", {'packages': allPackages, 'count':allCount, 'testware':allTestware, 'countPkgs':allCountPkgs, 'countTw': len(allTestware)})


def returnTestRunResult(request,product,package,revision,phase,type):
    '''
    Returns latest test result
    '''
    logger.info("Fetching test result for  : " +str(package) +" "+str(revision))
    resultId =  testwareMapAllObj = report = reportDirectory = testwarePOMDirectory = hostProperties = None
    veLog = femObj = "None"
    if Product.objects.filter(name=product).exists():
        if product != "None":
            product = Product.objects.get(name=product)
            femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        packageRevisionObj = PackageRevision.objects.get(artifactId=package, version=revision, m2type=type)
        if TestsInProgress.objects.filter(package_revision=packageRevisionObj).exists():
            testObj = TestsInProgress.objects.get(package_revision=packageRevisionObj)
            if ((packageRevisionObj.kgb_test == 'in_progress') and (testObj.veLog != "None")):
                return HttpResponseRedirect(testObj.veLog)
        try:
            testwareMapObj=TestResultsToTestwareMap.objects.filter(package__name=package,package_revision__version=revision,testware_run__phase=phase ).order_by('-id')[:1][0]
            resultId= testwareMapObj.testware_run.id
            testwareMapAllObj=TestResultsToTestwareMap.objects.filter(testware_run_id=resultId).order_by('-testware_run')
        except:
            testResultWithoutTestwareObj=TestResultsWithoutTestware.objects.filter(package__name=package,package_revision__version=revision ).order_by('-id')[:1][0]
            resultId= testResultWithoutTestwareObj.testware_run.id
            testwareMapAllObj = None

        testResultsObj=TestResults.objects.get(id=resultId )
        report= testResultsObj.test_report
        reportDirectory = testResultsObj.test_report_directory
        if (reportDirectory.startswith("kgb_") or reportDirectory.startswith("cdb_")):
            reportDirectory = "/static/testReports/"+reportDirectory+"/index.html"
        testwarePOMDirectory = testResultsObj.testware_pom_directory
        hostProperties = testResultsObj.host_properties_file
        logger.info("Fetching test report for test run ID : " +str(resultId))
        if TestResultsToVisEngineLinkMap.objects.filter(testware_run=testResultsObj).exists():
            testReport2VEObj= TestResultsToVisEngineLinkMap.objects.get(testware_run=testResultsObj)
            veLog = testReport2VEObj.veLog
    except Exception as e:
        logger.error("Could not find test results for " + str(package) +" "+str(revision)+":"+str(e))

    return render(request, "cireports/testwareshowresult.html", {
        'resultId':resultId,
        'testware':testwareMapAllObj,
        'report':report,
        'reportDirectory':reportDirectory,
        'phase':phase,
        'package':package,
        'testwarePOMDirectory': testwarePOMDirectory,
        'product': product,
        'femObj':  femObj,
        'hostProperties': hostProperties,
        'veLog': veLog
        })

def returnTestRun(request,product,drop,isoVersion,sutType,testRun):
    '''
    Returns latest test result
    '''
    testResultsObj = testwareObj = None
    femObj = "None"
    if Product.objects.filter(name=product).exists():
        if product != "None":
            product = Product.objects.get(name=product)
            femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        testwareObjField = ('testware_artifact__name', 'testware_revision__version',)
        testwareObj=ISOTestResultsToTestwareMap.objects.only(testwareObjField).values(*testwareObjField).filter(testware_run_id=testRun)
        testResultsObjField = ('test_report', 'test_report_directory', 'testware_pom_directory', 'host_properties_file',)
        testResultsObj=TestResults.objects.only(testResultsObjField).values(*testResultsObjField).get(id=testRun)
    except Exception as e:
        logger.error("Error: " +str(e))

    if not testResultsObj == None:
        report= testResultsObj['test_report']
        reportDirectory = testResultsObj['test_report_directory']
        if (reportDirectory.startswith("kgb_") or reportDirectory.startswith("cdb_")):
            reportDirectory = "/static/testReports/"+reportDirectory+"/index.html"
        testwarePOMDirectory = testResultsObj['testware_pom_directory']
        hostProperties = testResultsObj['host_properties_file']
    else:
        report = reportDirectory = testwarePOMDirectory = hostProperties = None

    logger.info("Fetching test report for test run ID : " +str(testRun))
    mediaObjField = ('version','mediaArtifact__name','current_status', 'sed_build__version', 'deploy_script_version', 'mt_utils_version')
    mediaObj = ISObuild.objects.only(mediaObjField).values(*mediaObjField).get(version=isoVersion, drop__name=drop, drop__release__product__name=product, mediaArtifact__testware=False, mediaArtifact__category__name="productware")
    allStatusUni = mediaObj['current_status']
    allStatus=ast.literal_eval(allStatusUni)
    status=[]
    definedDeploymentUtilities = DeploymentUtilsToISOBuild.objects.filter(iso_build__drop__name=drop,iso_build__version=mediaObj['version'],active=True)
    for item in allStatus:
        typObj=CDBTypes.objects.only('name').values('name').get(id=item)
        type=['name']
        if type==sutType:
            try:
                dontCare,dontCare,dontCare,dontCare,veLog=allStatus[item].split("#")
            except Exception as e:
                veLog = "None"
            break
        else:
            veLog = "None"

    return render(request, "cireports/testwareshowisoresult.html", {
        'resultId':testRun,
        'testware':testwareObj,
        'report':report,
        'reportDirectory':reportDirectory,
        'product': product,
        'femObj': femObj,
        'drop': drop,
        'media': mediaObj['mediaArtifact__name'],
        'isoVersion': isoVersion,
        'sedVersion': mediaObj['sed_build__version'],
        'deployScript' : mediaObj['deploy_script_version'],
        'mtUtilsVersion' : mediaObj['mt_utils_version'],
        'sutType':sutType,
        'testwarePOMDirectory': testwarePOMDirectory,
        'hostProperties': hostProperties,
        'veLog': veLog,
        'definedDeploymentUtilities' : definedDeploymentUtilities
        })

def returnTestRunReport(request,path):
    '''
    returns test report
    '''
    index = ""
    pathList = path.split("/")
    indexPages = ast.literal_eval(config.get('REPORT', 'indexPages'))
    filePath = config.get('REPORT', 'filePath')
    size = len(pathList) - 2
    newPathList = []
    if len(pathList) == 1:
        reportPath = os.path.join(filePath,path)
        for file in os.listdir(reportPath):
            for page in indexPages:
                if file == page:
                    index = os.path.join(path,file)
                    break
    elif len(pathList) > 3:
        for item in pathList:
            if item.endswith(".html"):
                indx = pathList.index(item)
                if indx > size:
                    newPathList.append(item)
            else:
                newPathList.append(item)
        for element in newPathList:
            index = index + str(element) + "/"
    else:
        index = path
    return render(request, index, {})

def returnKGBreadyDetails(request,product,drop,isoVersion,sutType,testRun):
    '''
    Returns manual KGB Ready Details
    '''
    testResultsObj = testwareObj = None
    femObj = "None"
    prodSet = reportDirectory = mediaObj = time = prodSet = pageContent = noReportDirectory = None
    if Product.objects.filter(name=product).exists():
        if product != "None":
            product = Product.objects.get(name=product)
            femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        mediaObj, sutType, time, prodSet, pageContent, noReportDirectory = utils.getMediaArtifactStatusReport(product,drop,isoVersion,sutType,testRun)
    except Exception as e:
        logger.error("Error Getting the Information: " +str(e))
        noReportDirectory = "There is no Report Found"

    return render(request, "cireports/kgbReadyDetails.html", {
        'product': product,
        'femObj': femObj,
        'drop': drop,
        'media': mediaObj,
        'sutType':sutType,
        'since': time,
        'productSet': prodSet,
        'noReportDirectory': noReportDirectory,
        'pageContent': pageContent
        })

def returnCautionStatusDetails(request,product,drop,isoVersion,sutType,testRun):
    '''
    Returns manual KGB Ready Details
    '''
    testResultsObj = testwareObj = None
    femObj = "None"
    prodSet = reportDirectory = mediaObj = time = prodSet = pageContent = noReportDirectory = None
    if Product.objects.filter(name=product).exists():
        if product != "None":
            product = Product.objects.get(name=product)
            femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        mediaObj, sutType, time, prodSet, pageContent, noReportDirectory = utils.getMediaArtifactStatusReport(product,drop,isoVersion,sutType,testRun)
    except Exception as e:
        logger.error("Error Getting the Information: " +str(e))
        noReportDirectory = "There is no Report Found"

    return render(request, "cireports/cautionStatusDetails.html", {
        'product': product,
        'femObj': femObj,
        'drop': drop,
        'media': mediaObj,
        'sutType':sutType,
        'since': time,
        'productSet': prodSet,
        'noReportDirectory': noReportDirectory,
        'pageContent': pageContent
        })


@transaction.atomic
@login_required
def updateNodePRIStatus(request,product,packageName):
    '''
    The updateNodePRIStatus makes the node PRI inclusion interactive from the Portal allow entries
    to be in/ex cluded from Node Pri
    '''
    #Use Form Handle for redirect updates webpage dynamicialy
    fh = FormHandle()
    product = Product.objects.get(name=product)

    packageObj = Package.objects.get(name=packageName)
    packageNumber = packageObj.package_number

    #Call the updateNodePRIStatus in cireports utils class to do db transactions
    try:
        with transaction.atomic():
            cireports.utils.updateNodePRIStatus(request,packageNumber)
    except IntegrityError as e:
        logger.error(str(e))

    #Redirect to Same page which also acts like a refresh of the Page with updated DB
    if request.method == 'POST':
        fh.redirectTarget = ("/" + str(product)+ "/pri/" +str(packageNumber) + "/")
        return fh.success()

def generateNodePRI(request,product,dropVersion):
    '''
    The GenerateNodePRI function is called by the Portal to populate the Node PRi by Drop
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    #Returns the drop Obj based on Product Release and drop name
    dropObj = Drop.objects.get(release__product__name=product, name=dropVersion)
    priObj = pri.objects.filter(drop_id=dropObj.id, node_pri=1)
    return render(request, "cireports/node_pri.html", {'femObj': femObj,'product': product,'priObj':priObj,'drop': dropObj.name})

@csrf_exempt
def getVersionFromRstate(request):
    '''
    This function is called by REST and other classes to return the version of an artifact based
    on its rState
    '''
    if request.method == 'GET':
        version = str(request.GET.get('version')).upper()
    if request.method == 'POST':
        version = str(request.POST.get('version')).upper()
    if "R" in version:
        version = convertRStateToVersion(version)
        return HttpResponse(version)
    else:
        return HttpResponse("The Version cannot be worked out as the input text was not an RState: " + str(version) + "\n")

@csrf_exempt
@transaction.atomic
def restObsoletePackageCIFWK(request):
    '''
    Function to allow package version to be obsoleted from a drop in the CI FWK DB using REST call
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        packageName = packageVersion = drop = product = packageNumber = platform = signum =reason = None
        packageName = request.POST.get("packageName")
        packageVersion = request.POST.get('packageVersion')
        drop = request.POST.get('drop')
        product = request.POST.get('product')
        packageNumber = request.POST.get('packageNumber')
        platform = request.POST.get('platform')
        category = request.POST.get('category')
        signum = request.POST.get('signum')
        reason = request.POST.get('reason')
        m2type = request.POST.get('type')

    if packageName is None or not packageName or packageName == "None":
        return HttpResponse("Error: Package name required.\n")
    if packageVersion is None or not packageVersion or packageVersion == "None":
        return HttpResponse("Error: Package Version required.\n")
    if drop is None or not drop  or drop == "None":
        return HttpResponse("Error: Drop required.\n")
    if product is None or not product or product == "None":
        return HttpResponse("Error: Product required.\n")
    if packageNumber is None or not packageNumber or packageNumber == "None":
        return HttpResponse("Error: Package Number required.\n")
    if signum is None or not signum or signum == "None":
        return HttpResponse("Error: Signum required.\n")
    if reason is None or not reason or reason == "None":
        return HttpResponse("Error: Reason required.\n")
    if product.lower() == "oss-rc":
        if platform is None or not platform or platform == "None":
            return HttpResponse("Error: Platform Required for Product: " +str(product))
    else:
        platform = "None"

    category = utils.mediaCategoryCheck(category)
    if "Error" in str(category):
        return HttpResponse(category)

    try:
        dropObj = Drop.objects.only('id', 'status').values('id', 'status').get(name=drop, release__product__name=product)
        if "open" not in dropObj['status']:
            user = User.objects.get(username=str(request.user))
            obsoleteGroup = config.get("CIFWK", "adminGroup")
            if not user.groups.filter(name=obsoleteGroup).exists():
                errMsg = "User is not authorised to obsolete a package from a drop that is not open (" +str(drop) +")"
                logger.info(errMsg)
                return HttpResponse("Error: " +errMsg)
    except Exception as e:
        msg = "Issue with finding drop object in cifwk DB using entered values: Error: " +str(e)
        logger.error(msg)
        return HttpResponse(msg)
    try:
        if m2type == None:
            #get defaults
            defaults = {'TOR':'rpm','OSS-RC':'pkg','LITP':'rpm','CI':'zip','CSL-MEDIATION':'rpm','OM':'pkg','SECURITY':'zip','COMINF':'zip'}
            try:
                type=defaults[str(product).upper()]
            except:
                logger.error("no default for product")
                type='rpm';
        else:
            type=m2type

        if platform == "None":
            # lookup for non ossrc packages where the packageName is in the form of ERICabc_CXP1234567
            packageRevisionObj = PackageRevision.objects.only('id', 'package__name').values('id', 'package__name').get(package__name=packageName, version=packageVersion, m2type=type, category=category)
        else:
            if "3pp" in str(category):
                packageRevisionObj = PackageRevision.objects.only('id', 'package__name').values('id', 'package__name').get(package__name=packageName, version=packageVersion, platform=platform, m2type=type, category=category)
            else:
                packageRevisionObj = PackageRevision.objects.only('id', 'package__name').values('id', 'package__name').get(package__name=packageName+"_"+packageNumber, version=packageVersion, platform=platform, m2type=type, category=category)
    except Exception as e:
        msg = "Issue with finding Package Revison Object cifwk DB using entered values, Error: " +str(e)
        logger.error(msg)
        return HttpResponse(msg)
    try:
        with transaction.atomic():
            obsolete = utils.obsolete2(packageRevisionObj['id'], dropObj['id'], reason, signum)
            if not "ERROR" in str(obsolete):
                msg = str(obsolete)
                logger.info(msg)
                return HttpResponse(msg + "\n")
            else:
                msg = "There was an issue Obsoleting the Package - " + str(obsolete)
                logger.error(msg)
                return HttpResponse(msg +".\n")
    except IntegrityError as e:
        msg = "Issue with Obsoleting : Error: " +str(e)
        logger.error(msg)
        return HttpResponse(msg)

@csrf_exempt
@transaction.atomic
def restObsoleteMediaArtifactCIFWK(request):
    '''
    Function to allow Media Artifact version to be obsoleted from a drop in the CI FWK DB using REST call
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        mediaArtName = mediaArtVersion = drop = productSet = signum =reason = None
        mediaArtName = request.POST.get("mediaArtifact")
        mediaArtVersion = request.POST.get('version')
        drop = request.POST.get('drop')
        productSet = request.POST.get('productSet')
        signum = request.POST.get('signum')
        email = request.POST.get('email')
        reason = request.POST.get('reason')

    if mediaArtName is None or not mediaArtName or mediaArtName == "None":
        return HttpResponse("Error: Media Artifact name required.\n")
    if mediaArtVersion is None or not mediaArtVersion or mediaArtVersion == "None":
        return HttpResponse("Error: Media Artifact version required.\n")
    if drop is None or not drop or drop == "None":
        return HttpResponse("Error: Drop required.\n")
    if productSet is None or not productSet or productSet == "None":
        return HttpResponse("Error: Product Set required.\n")
    if signum is None or not signum or signum == "None":
        return HttpResponse("Error: Signum required.\n")
    if email is None or not email or email == "None":
        return HttpResponse("Error: Email required.\n")
    if reason is None or not reason or reason == "None":
        return HttpResponse("Error: Reason required.\n")
    try:
        prodSetRel = ProductSetRelease.objects.filter(productSet__name=productSet)[0]
        dropObj = Drop.objects.get(name=drop, release__product=prodSetRel.release.product)
        productSetRelease = ProductSetRelease.objects.get(release=dropObj.release)
        drp = Drop.objects.get(name=drop, release=productSetRelease.release)
        if "open" not in drp.status:
            user = User.objects.get(username=str(request.user))
            obsoleteGroup = config.get("CIFWK", "adminGroup")
            if not user.groups.filter(name=obsoleteGroup).exists():
                errMsg = "User is not authorised to obsolete media from a drop that is not open (" +str(drp) +")"
                logger.info(errMsg)
                return HttpResponse("Error: " +errMsg)
    except Exception as e:
        logger.error("Issue with finding drop object in cifwk DB using entered values: Error: " +str(e))
        return HttpResponse("Error: " +str(e))
    try:
        mediaArtObj = ISObuild.objects.get(artifactId=mediaArtName, version=mediaArtVersion)
    except Exception as e:
        logger.error("Issue with finding Media Artifact Object cifwk DB using entered values: Error: " +str(e))
        return HttpResponse("Error: " +str(e))
    try:
        dropMediaArtMapObj = DropMediaArtifactMapping.objects.get(mediaArtifactVersion=mediaArtObj, drop=drp, released=1)
    except Exception as e:
        logger.error("Issue with finding Drop to Media Artifact Mapping Object cifwk DB using entered values: Error: " +str(e))
        return HttpResponse("Error: " +str(e))

    if drp != dropMediaArtMapObj.drop:
        logger.error("Error Media Artifact Version should be Obsoleted from the drop it was delivered to")
        return HttpResponse("Error Media Artifact Version should be Obsoleted from the drop it was delivered to.\n")
    try:
        with transaction.atomic():
            obsolete, data = utils.obsoleteMedia(dropMediaArtMapObj.id, mediaArtName, signum, reason, drop, productSet, productSetRelease.name, email)
            if not "ERROR" in obsolete:
                logger.info("Obsoleted : " + str(mediaArtName) + " version: " + str(mediaArtObj.version) + " on " + str(datetime.now()) + " by " + str(signum))
                return HttpResponse("Obsoleted : " + str(mediaArtName) + " version: " + str(mediaArtObj.version) + " on " + str(datetime.now()) + " by " + str(signum) + "\n")
            else:
                if "Content" in obsolete:
                   logger.error("There was an issue Obsoleting the Media Artifact Version: In Passed Product Set Version(s)" + str(list(data)))
                   return HttpResponse("There was an issue Obsoleting the Media Artifact Version: In Passed Product Set Version. " +  str(list(data)) + "\n")
                else:
                    logger.error("There was an issue Obsoleting the Media Artifact Version: Part of a frozen Drop - " + str(data.drop.name) + " Freeze Date - " + str(data.drop.mediaFreezeDate))
                    return HttpResponse("There was an issue Obsoleting the Media Artifact Version: Part of a frozen Drop - " +  str(data.drop.name) + " Freeze Date - " + str(data.drop.mediaFreezeDate) + "\n")
    except IntegrityError as e:
        logger.error("Issue with finding Obsoleting : Error: " +str(e))
        return HttpResponse("Error: " +str(e))


def returnTestwareMap(request):
    package = request.GET.get('package')
    pomVersion = request.GET.get('pomversion','default')
    isoVersion = request.GET.get('isoversion',None)
    isoArtifact = request.GET.get('isoartifact',None)
    packageList = request.GET.get('packagelist',None)
    try:
        testware=cireports.utils.getTestwareMapInfo(package,isoArtifact,isoVersion,packageList)
        if not testware:
            errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " no testware returned"
            logger.error(errorMessage)
            return HttpResponse(errorMessage)
    except Exception as e:
        errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " Error thrown: " +str(e)
        logger.error(errorMessage)
        return HttpResponse(errorMessage)

    return HttpResponse(testware)

def returnTestwarePom(request):
    package = request.GET.get('package')
    pomVersion = request.GET.get('pomversion','default')
    scheduleGroup = request.GET.get('schedulegroup',None)
    scheduleArtifact = request.GET.get('scheduleartifact',None)
    scheduleVersion = request.GET.get('scheduleversion',None)
    scheduleName = request.GET.get('schedulename',None)
    manualVer = request.GET.get('manualversion',None)
    tafRunVer = request.GET.get('tafrunversion',None)
    isoVersion = request.GET.get('isoversion',None)
    isoArtifact = request.GET.get('isoartifact',None)
    packageList = request.GET.get('packagelist',None)
    try:
        testware=cireports.utils.getTestwareMapInfo(package,isoArtifact,isoVersion,packageList)
        if not testware:
            errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " no testware returned"
            logger.error(errorMessage)
            return HttpResponse(errorMessage)
    except Exception as e:
        errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " Error thrown: " +str(e)
        logger.error(errorMessage)
        return HttpResponse(errorMessage)
    testwareList = testware.split('-BREAK-')
    data = []
    for item in testwareList:
        testwareName,testwareVersion=item.split('-VER-')
        testwareRev=cireports.models.TestwareRevision.objects.get(testware_artifact__name=testwareName,version=testwareVersion)
        data1 = [
                {
                    "name": testwareRev.testware_artifact.name,
                    "version": testwareRev.execution_version,
                    "groupID": testwareRev.execution_groupId,
                    "artifactID": testwareRev.execution_artifactId,
                },
                ]
        data = data + data1
    ret=cireports.utils.createTestwareExecutionPom(data,pomVersion,scheduleGroup,scheduleArtifact,scheduleVersion,scheduleName,manualVer,tafRunVer,'True')
    return HttpResponse(ret)

def returnTestware(request):
    artifact = request.GET.get('artifact',None)
    group = request.GET.get('group',None)
    version = request.GET.get('version',None)
    packageList = request.GET.get('packagelist',None)

    if Package.objects.filter(name=artifact).exists():
        package=artifact
        isoVersion=None
        isoArtifact=None
    elif ISObuild.objects.filter(version=version, mediaArtifact__name=artifact, mediaArtifact__testware=False, mediaArtifact__category__name="productware").exists():
        package=None
        isoArtifact=artifact
        isoVersion=version
    else:
        return HttpResponse("No ISO build found for Artifact: " +str(artifact) + " Version: " +str(version))

    try:
        testware=cireports.utils.getTestwareMapInfo(package,isoArtifact,isoVersion,packageList)
        if not testware:
            errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " no testware returned"
            logger.error(errorMessage)
            return HttpResponse(errorMessage)
    except Exception as e:
        errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " Error thrown: " +str(e)
        logger.error(errorMessage)
        return HttpResponse(errorMessage)
    testwareList = testware.split('-BREAK-')
    data = []

    for item in testwareList:
        try:
            testwareName,testwareVersion=item.split('-VER-')
            testwareRev=cireports.models.TestwareRevision.objects.get(testware_artifact__name=testwareName,version=testwareVersion)
            data1 = [
                    {
                        "name": testwareRev.testware_artifact.name,
                        "version": testwareRev.execution_version,
                        "groupID": testwareRev.execution_groupId,
                        "artifactID": testwareRev.execution_artifactId,
                    },
                    ]
            data = data + data1
        except Exception as e:
            logger.error("Error processing testware: "+str(e))
    ret=cireports.utils.testwareExecutionlist(data)
    return HttpResponse(ret)

def returnMappedTestware(request):
    artifact = request.GET.get('artifact',None)
    group = request.GET.get('group',None)
    version = request.GET.get('version',None)
    packageList = request.GET.get('packagelist',None)

    category = "productware"

    if '||' in str(artifact) and not '::' in str(artifact):
        package=None
        isoVersion=None
        isoArtifact=None
        artifact=artifact.replace('||','::latest||')
        artifact = artifact+"::latest"
        packageList=artifact.replace('||',' ')
    elif '::' in str(artifact):
        package=None
        isoVersion=None
        isoArtifact=None
        packageList=artifact.replace('||',' ')
        if not '||' in str(artifact):
            tmpArtifact,tmpVersion = artifact.split('::')
            if ISObuild.objects.filter(version=tmpVersion, mediaArtifact__name=tmpArtifact, mediaArtifact__testware=False, mediaArtifact__category__name=category).exists():
                isoVersion=tmpVersion
                isoArtifact=tmpArtifact
                packageList=None
    elif Package.objects.filter(name=artifact).exists():
        package=artifact
        isoVersion=None
        isoArtifact=None
    elif ISObuild.objects.filter(version=version, mediaArtifact__name=artifact, mediaArtifact__testware=False, mediaArtifact__category__name=category).exists():
        package=None
        isoArtifact=artifact
        isoVersion=version
    else:
        return HttpResponse("")

    try:
        testware=cireports.utils.getTestwareMapInfo(package,isoArtifact,isoVersion,packageList)
        if not testware:
            errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " no testware returned"
            logger.error(errorMessage)
            return HttpResponse(errorMessage)
    except Exception as e:
        errorMessage = "Error: Returning Testware calling getTestwareMapInfo function on package: " +str(package)+ " ISO Artifact: " +str(isoArtifact)+ " ISO Version: " +str(isoVersion)+ " Using Package List: " +str(packageList)+ " Error thrown: " +str(e)
        logger.error(errorMessage)
        return HttpResponse(errorMessage)

    testwareList = testware.split('-BREAK-')
    data = []

    for item in testwareList:
        try:
            testwareName,testwareVersion=item.split('-VER-')
            testwareRev=TestwareRevision.objects.get(testware_artifact__name=testwareName,version=testwareVersion)
            data1 = [
                    {
                        "artifactID": testwareRev.testware_artifact.name,
                        "version": testwareRev.version,
                        "groupID": testwareRev.groupId,
                    },
                    ]
            data = data + data1
        except Exception as e:
            logger.error("Error processing testware: "+str(e))
    ret=cireports.utils.testwareMappedlist(data)
    return HttpResponse(ret)


def showPackageDependencies(request, product, packageName):
    '''
    The showPackageDependencies shows Packaage KGB Dependencies to the user
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"

    pkgObj = Package.objects.get(name=packageName)
    pkgDependMapList = PackageDependencyMapping.objects.filter(package=pkgObj)
    return render(request,"cireports/showPackageDependencies.html", {'femObj': femObj, 'product': product, 'packageName': packageName, 'pkgDependMapList': pkgDependMapList})


@login_required
def packageDependencyMappings(request, product, packageName, option):
    '''
    The packageDependencyMappings Function is used to allow
    Package Install time dependencies
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"

    packageList = []
    dependentPackageList = []
    installOrderList = list(xrange(1,300))
    found = ""
    pkgList,allCount = cireports.utils.getPackagesBasedOnProduct(product)
    mainPackageObj = Package.objects.get(name=packageName)

    if "edit" in str(option) or "add" in str(option):
        pkgDependMapList = PackageDependencyMapping.objects.filter(package=mainPackageObj)
        for dependentPkg in pkgDependMapList:
            dependentPackageList.append(str(dependentPkg.installOrder) + ":" + str(dependentPkg.dependentPackage))
            installOrderList.remove(int(dependentPkg.installOrder))
            pkgList.remove(dependentPkg.dependentPackage)

    if request.method == 'POST':
        package = str(request.POST.get('dependentPackage'))
        if package is not "Empty List":
            dependentPackageObj = Package.objects.get(name=package)
        else:
            dependentPackageObj = ""
        dependentPackageList = request.POST.getlist('dependentPackages')
        installOrder = request.POST.get('installOrder')
        submit = request.POST.get('submit')
        entry = installOrder+":"+package

        dependentPackageList,installOrderList,pkgList = cireports.utils.dependencyMapping(submit,dependentPackageList,packageName,package,entry,installOrder,dependentPackageObj,found,product)
        if submit == "Commit List":
            return HttpResponseRedirect("/"+str(product.name)+"/"+str(packageName)+"/showPackageDependencies")

    packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgList]
    pkgForm = PackageMappingForm(packageList, installOrderList)
    dependentPackageList = cireports.utils.sortList(dependentPackageList)
    return render(request, "cireports/packageDependencyMapping.html", {'femObj': femObj, 'product': product,'packageName': packageName,  'pkgForm': pkgForm, 'dependentPackageList': dependentPackageList})

@login_required
def deleteDependencyMapping(request, product, packageName, dependencyMappingId):
    '''
    The deleteDependencyMapping allows the user of the system to delete a run time dependency
    '''
    error = ""
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        PackageDependencyMapping.objects.get(id=int(dependencyMappingId)).delete()

    except Exception as e:
        error = ("There was an issue deleting Dependency, error thrown: " +str(e))
        logger.error(error)

    pkgObj = Package.objects.get(name=packageName)
    pkgDependMapList = PackageDependencyMapping.objects.filter(package=pkgObj)
    return render(request,"cireports/showPackageDependencies.html", {'femObj': femObj, 'product': product, 'packageName': packageName, 'pkgDependMapList': pkgDependMapList, 'error': error})


@csrf_exempt
def getKGBPackageDenpencies(request):
    '''
    The getKGBPackageDenpencies is a rest call function which return the declared dependent packages of a given package
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        packageName = request.POST.get('packageName')
        packageNumber = request.POST.get('packageNumber')
        packageRepository = request.POST.get('repository')
        packageM2Type = request.POST.get('m2Type')
    if packageName is None or packageNumber is None:
        return HttpResponse("Error: Package name and Number Required\n")
    if packageRepository is None or packageM2Type is None:
        return HttpResponse("Error: packageRepository and packageM2Type are required\n")
    packageName = packageName + "_" + packageNumber
    if Package.objects.filter(name=packageName, package_number=packageNumber).exists():
        try:
            pkgObj = Package.objects.get(name=packageName, package_number=packageNumber)
            artefactVersion, repositoryLocation, packageRstate = cireports.utils.getLatestVersionOfPackageinRepository(pkgObj, packageRepository, packageM2Type)
        except Exception as e:
            logger.error("Issue with Database Query: " +str(e))
            return HttpResponse("Issue with Database Query: " +str(e))
    else:
        return HttpResponse("Error: Package name: " + packageName + " and Package Number: " + packageNumber + " not found in database")
    pkgDependMapObj = PackageDependencyMapping.objects.filter(package=pkgObj)
    packageDict = {}
    packageDict[packageName] = {}
    for pkgDependMap in pkgDependMapObj:
        dependentPackageObj = Package.objects.get(name=pkgDependMap.dependentPackage)
        latestArtefactVersion, pkgRepositoryLocation, packageRstate = cireports.utils.getLatestVersionOfPackageinRepository(dependentPackageObj, packageRepository, packageM2Type)
        packageDict[packageName][pkgDependMap.installOrder] = pkgDependMap.dependentPackage.name, latestArtefactVersion, packageRstate, pkgRepositoryLocation
    logger.info("The Returned Depenencies for: " +str(packageName) + " are: " +str(packageDict))
    return HttpResponse(json.dumps(packageDict), content_type="application/json")

@csrf_exempt
def getLatestIsoVer(request):
    try:
        product = request.GET.get('product')
        drop = request.GET.get('drop')
        format = request.GET.get('format',None)
        pretty = request.GET.get('pretty')
        if pretty != None:
            if pretty.lower() == "false":
                pretty = False
            elif pretty.lower() == "true":
                pretty = True
        else:
            pretty = False
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        latestIso = ISObuild.objects.filter(drop=dropObj, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-id')[0]
        if format == 'json':
            latestIsoJson = [
                        {
                            "group":latestIso.groupId,
                            "artifact":latestIso.artifactId,
                            "version": latestIso.version
                        }
                            ]
            if pretty:
                ret = json.dumps(latestIsoJson, sort_keys=True, indent=4)
            else:
                ret = json.dumps(latestIsoJson)
        else:
            ret=latestIso.version
    except Exception as e:
        logger.error("Invalid Information: Product("+str(product)+")--Drop("+str(drop)+"): Error: " +str(e))
        if format == 'json':
            ret = json.dumps([{"group":"error","artifact":"error","version": "error"}])
        else:
            ret=None
    return HttpResponse(ret)

@csrf_exempt
def getLatestIso(request):
    ret=None
    try:
        product = request.GET.get('product')
        release = request.GET.get('release')
        drop = request.GET.get('drop')
        passedOnlyString = request.GET.get('passedOnly', None)
        format = request.GET.get('format','html')

        if passedOnlyString is None:
            passedOnly = None
        elif passedOnlyString.lower() == "true":
            passedOnly = True
        else:
            passedOnly = False

        isoName, isoVersion = cireports.utils.getLatestIso(product, drop, release, passedOnly)
        if isoName == None:
            isoName = "None"
        if isoVersion == None:
            isoVersion = "None"

        if format.lower() == 'json':
            ret = json.dumps([{"isoName":isoName, "isoVersion":isoVersion}])
        else:
            ret = isoVersion

    except Exception as e:
        logger.error("Invalid Information: Product("+str(product)+")--Release("+str(release)+")--Drop("+str(drop)+"): Error: " +str(e))
    if format.lower() == 'json':
        return HttpResponse(ret, content_type="application/json")
    else:
        return HttpResponse(ret)

@csrf_exempt
def getISOContentDelta(request):
    '''
    The getISOContentDelta function is a REST Service which return a JSON object of Artifact Differences between a given ISO and its previous ISO
    version on a given drop, this is acheived by calling the cireports.utils.returnISOVersionArtifactDelta function which returns the object.
    '''
    response = "Error: There was no response for gathering ISO Version(s) Delta Atifacts"
    if request.method == 'POST':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")

    previousDrop = None

    product = request.GET.get('product')
    drop = request.GET.get('drop')
    isoVersion = request.GET.get('isoVersion')
    isoGroup = request.GET.get('isoGroup')
    isoArtifact = request.GET.get('isoArtifact')
    previousISOVersion = request.GET.get('previousISOVersion')
    previousDrop = request.GET.get('previousDrop')
    followDrop = request.GET.get('followDrop')
    testware = request.GET.get('testware')

    if testware is None or not testware or testware == "None":
        testware = False

    if isoArtifact != None and isoGroup != None:
        try:
            isoObj = ISObuild.objects.get(groupId=isoGroup,artifactId=isoArtifact,version=isoVersion)
            drop = isoObj.drop.name
            product = isoObj.drop.release.product.name
        except Exception as error:
            errorMsg = "Error: There was an issue getting iso delta artifacts: " + str(error)
            logger.error(errorMsg)
            return HttpResponse(errorMsg + "\n")

    if product is None or not product or product == "None":
        return HttpResponse("Error: product name required, please try again\n")
    if drop is None or not drop or drop == "None":
        return HttpResponse("Error: drop name required, please try again\n")
    if isoVersion is None or not isoVersion or isoVersion == "None":
        return HttpResponse("Error: isoVersion name required, please try again\n")

    try:
        response, ISODeltaDict, dontCare, notNeeded = cireports.utils.returnISOVersionArtifactDelta(product,drop,isoVersion,previousISOVersion,previousDrop,followDrop,testware)
    except Exception as error:
        errorMsg = "Error: There was an issue getting iso delta artifacts: " + str(error)
        logger.error(errorMsg)
        return HttpResponse(errorMsg + "\n")

    return HttpResponse(response, content_type="application/json")

@csrf_exempt
def uploadFile(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handleUploadedFile(request.FILES['file'],request.POST.get('name'))
            name = request.POST.get('name')
            return HttpResponse("Done", content_type="text/plain")
    else:
        form = UploadFileForm()
    return render_to_response('cireports/upload.html', {'form': form})

def handleUploadedFile(f,name):
    with open('/proj/lciadm100/tmpUploadStore/'+str(name), 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

def pkgDeliveryData(request, product, release, drop, package):
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"

    try:
        if drop == "None":
            # get the drops associated with the release
            drops = Drop.objects.filter(release__name=release, release__product__name=product)
            # get a list of all the versions of the package that have been delivered into any of those drops
            packages = list(DropPackageMapping.objects.filter(drop__in=drops, package_revision__package__name=package).order_by('-date_created'))
        else:
            # get the specific drop object based on the drop name passed to the function
            dropObj = Drop.objects.get(name=drop, release__product__name=product)
            # get a list of all the versions of the specific package that have been delivered in that drop
            packages = list(DropPackageMapping.objects.filter(drop__id=dropObj.id, package_revision__package__name=package).order_by('-date_created'))
        count = len(packages)
    except Drop.DoesNotExist:
        raise Http404
    return render(request, "cireports/pkgdata.html",
            {
                'release': release,
                'count': count,
                'packages': packages,
                'package': package,
                'drop': drop,
                'product': product,
                'femObj': femObj
            })

def deliveryData(request, product, release, drop=None, full=None):
    dropObj = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        product = "None"

    if drop == "None" or drop is None:
        # get a list of the drops associated with the release
        drops = Drop.objects.filter(release__name=release, release__product=product)
        # get a count of every package version that has been delivered to all those drops
        count = DropPackageMapping.objects.filter(drop__in=drops).count()
    else:
        # get the specific drop object based on the drop name passed to the function
        dropObj = Drop.objects.get(name=drop, release__product=product)
        # get a count of every package version that has been delivered to this specific drop
        count = DropPackageMapping.objects.filter(drop__id=dropObj.id).count()
    if dropObj:
        pageHitCounter("DropDeliveryStats", dropObj.id, str(request.user))

    if full is None:
        return render(request, "cireports/data.html",
                {
                    'release': release,
                    'count': count,
                    'drop': drop,
                    'product': product
                })
    else:
        return render(request, "cireports/fullData.html",
                {
                    'release': release,
                    'count': count,
                    'drop': drop,
                    'product': product
                })


def displayLatestQueue(request, product):
    '''
    The displayLatestQueue function redirects user to the latest delivery queue for a given Product
    '''
    field = ("name",)
    latestDrop = Drop.objects.only(field).values(*field).filter(release__product__name=product, correctionalDrop=False).exclude(release__name__icontains="test").latest("id")
    return HttpResponseRedirect("/"+product+"/queue/"+latestDrop['name'])


def displayDeliveryStats(request, product, release, drop, type, full=None):
    dropObj = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        product = "None"

    pkgAppearances = None
    displayPkgs = []

    try:
        if drop == "None" or drop is None:
            # get a list of the drops associated with the release
            drops = Drop.objects.filter(release__name=release, release__product__name=product)
            # get a list of every package version that has been delivered to all those drops
            if type == 'packages':
                full_packages = list(DropPackageMapping.objects.filter(drop__in=drops, package_revision__package__testware=False).order_by('-date_created'))
            elif type == 'testware' :
                full_packages = list(DropPackageMapping.objects.filter(drop__in=drops, package_revision__package__testware=True).order_by('-date_created'))
        else:
            # get the specific drop object based on the drop name passed to the function
            dropObj = Drop.objects.get(name=drop, release__product__name=product)
            # get a list of every package version that has been delivered to this specific drop
            if type == 'packages':
                full_packages = list(DropPackageMapping.objects.filter(drop__id=dropObj.id, package_revision__package__testware=False).order_by('-date_created'))
            elif type == 'testware' :
                full_packages = list(DropPackageMapping.objects.filter(drop__id=dropObj.id, package_revision__package__testware=True).order_by('-date_created'))
        if full is None:
            # Loop through full_packages and select individual packages to display
            for p in full_packages:
                found = 0
                for currPkg in displayPkgs:
                    if (p.package_revision.package == currPkg.package_revision.package):
                        found = 1
                        break
                if (found == 0):
                    displayPkgs.append(p)

            # get the count of how many times each individual package has delivered
            stringPkgs = ''.join(str(full_packages))
            pkgAppearances = dict([ (pkg.package_revision.package.name, stringPkgs.count(str(pkg.package_revision.package.name))) for pkg in displayPkgs ])

    except Drop.DoesNotExist:
        raise Http404
    if full is None:
        return render(request, "cireports/delivery_stats.html",
                {
                    'release': release,
                    'packages': displayPkgs,
                    'pkgAppearances': pkgAppearances,
                    'drop': drop,
                    'product': product
                })
    else:
        return render(request, "cireports/delivery_stats_full.html",
                {
                    'release': release,
                    'fullPackages': full_packages,
                    'drop': drop,
                    'product': product
                })

def productSetCDBStatus(request, drop, productSetVersion):
    try:
        custDeployBases = None
        productSetReleaseNum = str(request.GET.get('prodSetRelNum'))
        productSetVersionObj=ProductSetVersion.objects.get(version=productSetVersion,productSetRelease__number=productSetReleaseNum)
        status = cireports.utils.getProductSetCDBStatus(productSetVersionObj)
        return render(request, "cireports/product_set_cdb_table.html",
                    {
                        'productSetVersionId': productSetVersionObj.id,
                        'cdbs': status,
                        'drop': drop
                    })
    except:
        return render(
               request, "cireports/product_set_cdb_table.html",{'cdbs':"" })


def returnPSTestRun(request,productSetVersionId,sutType,testRun):
    '''
    Returns latest test result
    '''
    productSetVersionObjField = ('id', 'productSetRelease__number', 'productSetRelease__name','version','productSetRelease__productSet__name', 'current_status','productSetRelease__masterArtifact__release__product__name')
    productSetVersionObj=ProductSetVersion.objects.only(productSetVersionObjField).values(*productSetVersionObjField).filter(id=productSetVersionId)[0]
    productSetNum=productSetVersionObj['productSetRelease__number']
    productSetRel=productSetVersionObj['productSetRelease__name']
    productSetVersion=productSetVersionObj['version']
    productSet = productSetVersionObj['productSetRelease__productSet__name']
    identityString=productSet+" "+productSetRel+" "+productSetNum+" Ver: "+productSetVersion
    sedVersion = None
    deployVersion = None
    mtUtilsVersion = None
    definedDeploymentUtilities = None
    mediaArtifactVersion = None

    try:
        isoSedAndDeployField = ('mediaArtifactVersion__version','mediaArtifactVersion__sed_build__version','mediaArtifactVersion__deploy_script_version','mediaArtifactVersion__mt_utils_version', )
        if productSet == "ENM":
            isoSedAndDeploy = ProductSetVersionContent.objects.only(isoSedAndDeployField).filter(productSetVersion_id=productSetVersionObj['id'], mediaArtifactVersion__drop__release__product__name=productSet).values_list(*isoSedAndDeployField)[0]
        else:
            isoSedAndDeploy = ProductSetVersionContent.objects.only(isoSedAndDeployField).filter(productSetVersion_id=productSetVersionObj['id'], mediaArtifactVersion__drop__release__product__name=productSetVersionObj['productSetRelease__masterArtifact__release__product__name']).values_list(*isoSedAndDeployField)[0]
        mediaArtifactVersion,sedVersion, deployVersion, mtUtilsVersion = isoSedAndDeploy
    except Exception as e:
        logger.error("Error getting the sedVersion and deployVersion: " + str(e))

    testResultsObj = testwareObj = None
    femObj = "None"
    if Product.objects.filter(name=productSet).exists():
        product = Product.objects.get(name=productSet)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        testwareObjField = ('testware_artifact__name', 'testware_revision__version',)
        testwareObj=PSTestResultsToTestwareMap.objects.only(testwareObjField).values(*testwareObjField).filter(testware_run_id=testRun)
        testResultsObjField = ('test_report', 'test_report_directory', 'testware_pom_directory', 'host_properties_file',)
        testResultsObj=TestResults.objects.only(testResultsObjField).values(*testResultsObjField).get(id=testRun)
    except Exception as e:
        logger.error("Error: " +str(e))

    allStatusUni = productSetVersionObj['current_status']
    allStatus=ast.literal_eval(allStatusUni)
    status=[]
    for item in allStatus:
        typObj=CDBTypes.objects.only('name').values('name').get(id=item)
        type = typObj['name']
        if type==sutType:
            try:
                dontCare,dontCare,dontCare,dontCare,veLog=allStatus[item].split("#")
            except Exception as e:
                veLog = "None"
            break
        else:
            veLog = "None"

    if not testResultsObj == None:
        report= testResultsObj['test_report']
        reportDirectory = testResultsObj['test_report_directory']
        if (reportDirectory.startswith("kgb_") or reportDirectory.startswith("cdb_")):
            reportDirectory = "/static/testReports/"+reportDirectory+"/index.html"
        testwarePOMDirectory = testResultsObj['testware_pom_directory']
        hostProperties = testResultsObj['host_properties_file']
    else:
        report = reportDirectory = testwarePOMDirectory = hostProperties = None
    if DeploymentUtilsToProductSetVersion.objects.filter(productSetVersion_id=productSetVersionObj['id'],active=True).exists():
        definedDeploymentUtilities = DeploymentUtilsToProductSetVersion.objects.filter(productSetVersion_id=productSetVersionObj['id'],active=True)
    elif DeploymentUtilsToISOBuild.objects.filter(iso_build__version=mediaArtifactVersion,active=True).exists():
        definedDeploymentUtilities = DeploymentUtilsToISOBuild.objects.filter(iso_build__version=mediaArtifactVersion,active=True)

    logger.info("Fetching test report for test run ID : " +str(testRun))
    return render(request, "cireports/testwareshowpsresult.html", {
        'identityString': identityString,
        'resultId':testRun,
        'testware':testwareObj,
        'report':report,
        'reportDirectory':reportDirectory,
        'product': product,
        'femObj': femObj,
        'sutType':sutType,
        'testwarePOMDirectory': testwarePOMDirectory,
        'veLog': veLog,
        'hostProperties': hostProperties,
        'sedVersion': sedVersion,
        'mtUtilsVersion': mtUtilsVersion,
        'deployVersion': deployVersion,
        'definedDeploymentUtilities' : definedDeploymentUtilities
        })

def returnProdSetKGBreadyDetails(request,drop,productSetVersionId,sutType,testRun):
    '''
    Returns manual KGB Ready Details
    '''
    productSet = prodSet = reportDirectory = mediaObj = time = pageContent = noReportDirectory = None
    try:
       productSet, mediaObj, time, prodSet, pageContent, noReportDirectory = utils.getProductSetStatusReport(drop,productSetVersionId,sutType,testRun)
    except Exception as e:
        logger.error("Error Getting Testware Run Information: " +str(e))
        noReportDirectory = "There is no Report"

    return render(request, "cireports/kgbReadyDetails.html", {
        'productSetName': productSet,
        'drop': drop,
        'product': "None",
        'femObj': "None",
        'media': mediaObj,
        'noReportDirectory': noReportDirectory,
        'since': time,
        'productSet': prodSet,
        'pageContent': pageContent
        })

def returnProdSetCautionStatusDetails(request,drop,productSetVersionId,sutType,testRun):
    '''
    Returns Product Set Caution Status Details
    '''
    productSet = prodSet = reportDirectory = mediaObj = time = pageContent = noReportDirectory = None
    try:
       productSet, mediaObj, time, prodSet, pageContent, noReportDirectory = utils.getProductSetStatusReport(drop,productSetVersionId,sutType,testRun)
    except Exception as e:
        logger.error("Error Getting Testware Run Information: " +str(e))
        noReportDirectory = "There is no Report"

    return render(request, "cireports/cautionStatusDetails.html", {
        'productSetName': productSet,
        'drop': drop,
        'product': "None",
        'femObj': "None",
        'media': mediaObj,
        'noReportDirectory': noReportDirectory,
        'since': time,
        'productSet': prodSet,
        'pageContent': pageContent
        })

@csrf_exempt
def createProductSetVersion(request, prodSet, drop):
    '''
    This function is called by REST: it Creates Product Set Version or returns the latest Product Set version in Drop if there was not changes in the Drop
    '''
    version = None
    try:
        if request.method == 'POST':
            version=utils.getOrCreateVersion(prodSet, drop)
        else:
            version="ERROR: only Post calls accepted"
    except Exception as error:
        errMsg = "Issue getting Product Set Versions "+str(error)
        logger.error(errMsg)
        version = errMsg
    return HttpResponse(version, content_type="text/plain")


def getRStateFromVersion(request):
    '''
    This function is called by REST and other classes to return the RState of an artifact based
    on its version
    '''
    rstate= ""
    if request.method == 'GET':
        version = str(request.GET.get('version'))
        try:
            rstate = convertVersionToRState(version)
            return HttpResponse(rstate)
        except Exception as e:
            return HttpResponse("The RState cannot be worked out as the input text was not an version: " + str(version) + "\n")

def getlatestCXPRStatePRIM(request):
    '''
        This function is called by REST and other classes to return the latest RState of CXP Number
    '''

    if request.method == 'GET':
        number = str(request.GET.get('number'))
        user = str(request.GET.get('user'))
        password = str(request.GET.get('password'))

        try:
            login=cireports.prim.login(user,password)
            rstate=cireports.prim.getLatestCXPRStateFromPrim(number,login)
            if rstate != "error":
                return HttpResponse(rstate)
            else:
                return HttpResponse("Issue with getting Data from PRIM")
        except Exception as e:
            return HttpResponse("The RState cannot be worked out as the input text CXP number wasn't in PRIM: " + str(number) + "\n")



def getMediaArtifactVersions(request):
    '''
    Return xml of Media Artifact Versions
    '''
    try:
        productName=request.GET['product']
        dropName=request.GET['drop']
        product = Product.objects.get(name=productName)
        femObj = FEMLink.objects.filter(product=product)
        mediaArtifact, mediaArtifactVersions = cireports.utils.getMediaArtifactsByDrop(productName, dropName)
        versionString = ""
        for item in mediaArtifactVersions:
            versionString=versionString+"<version>"+item.version+"</version>"
    except Exception as e:
        logger.error("Issue getting Media Artifact Versions "+str(e))
        versionString = "ERROR"
    ret="<metadata><versions>"+versionString+"</versions></metadata>"
    return HttpResponse(ret,content_type="application/xhtml+xml")

def getMediaArtifactNumber(request):
    '''
    Return xml of Media Artifact Numbers
    '''
    try:
        productName=request.GET['product']
        dropName=request.GET['drop']
        product = Product.objects.get(name=productName)
        femObj = FEMLink.objects.filter(product=product)
        mediaArtifact = cireports.utils.getMediaArtifact(productName, dropName)
        mediaArtifactNumber = mediaArtifact.name
    except Exception as e:
        logger.error("Issue getting Media Artifact Number "+str(e))
        mediaArtifactNumber = "ERROR"
    ret="<metadata><cxps><cxp>"+str(mediaArtifactNumber)+"</cxp></cxps></metadata>"
    return HttpResponse(ret,content_type="application/xhtml+xml")

def getMediaArtifactGroup(request):
    '''
    Return xml of Media Artifact Groups
    '''
    try:
        productName=request.GET['product']
        dropName=request.GET['drop']
        product = Product.objects.get(name=productName)
        femObj = FEMLink.objects.filter(product=product)
        mediaArtifactGroup = cireports.utils.getMediaArtifactGroup(productName, dropName)
    except Exception as e:
        logger.error("Issue getting Media Artifact Group "+str(e))
        mediaArtifactGroup = "ERROR"
    ret="<metadata><groups><group>"+str(mediaArtifactGroup)+"</group></groups></metadata>"
    return HttpResponse(ret,content_type="application/xhtml+xml")

def getProductSetNumber(request):
    '''
    Return xml of Product Set Numbers
    '''
    try:
        productSetName=request.GET['productSet']
        dropName=request.GET['drop']
        productSetObj = ProductSet.objects.get(name=productSetName)
        product = ProductSetRelease.objects.filter(productSet=productSetObj)[0].release.product
        dropObj = Drop.objects.get(name=dropName, release__product=product)
        productSetRelObj = ProductSetRelease.objects.get(productSet=productSetObj,release=dropObj.release)
        productSetNumber = productSetRelObj.number
    except Exception as e:
        logger.error("Issue getting Product Set Number "+str(e))
        productSetNumber = "ERROR"
    ret="<metadata><productSetNumbers><productSetNumber>"+str(productSetNumber)+"</productSetNumber></productSetNumbers></metadata>"
    return HttpResponse(ret,content_type="application/xhtml+xml")


def getProductSetVersions(request):
    '''
    Return xml of Product Set Versions
    '''
    try:
        productSetName=request.GET['productSet']
        dropName=request.GET['drop']
        productSetObj = ProductSet.objects.get(name=productSetName)
        productSetRelObj = ProductSetRelease.objects.filter(productSet=productSetObj)[0]
        dropObj = Drop.objects.get(name=dropName, release__product=productSetRelObj.release.product)
        allVersions = ProductSetVersion.objects.filter(drop_id=dropObj.id,productSetRelease__release=dropObj.release).order_by('-id')
        versionString=""
        for item in allVersions:
            versionString=versionString+"<version>"+item.version+"</version>"
    except Exception as e:
        logger.error("Issue getting Product Set Versions "+str(e))
        versionString = "ERROR"
    ret="<metadata><versions>"+versionString+"</versions></metadata>"
    return HttpResponse(ret,content_type="application/xhtml+xml")


def getLatestProductSetVersion(request):
    '''
    Return latest Product Set Version
    '''
    latest = "None"
    try:
        productSetName=request.GET['productSet']
        dropName=request.GET['drop']
        productSetObj = ProductSet.objects.get(name=productSetName)
        productSetRelObj = ProductSetRelease.objects.filter(productSet=productSetObj)[0]
        dropObj = Drop.objects.get(name=dropName, release__product=productSetRelObj.release.product)
        allVersions = ProductSetVersion.objects.filter(drop_id=dropObj.id,productSetRelease__release=dropObj.release).order_by('-id')
        for item in allVersions:
            latest = str(item.version)
            break
    except Exception as e:
        logger.error("Issue getting Product Set Versions " + str(e))
    return HttpResponse(latest,content_type="text/plain")


def getLastGoodProductSetVersion(request):
    '''
    Return Latest Good Product Set Version
    '''
    lastPassed = "None"
    try:
        productSetName=request.GET['productSet']
        dropName=request.GET.get('drop',None)
        confidenceLevel=request.GET.get('confidenceLevel', None)
        if confidenceLevel:
            try:
                cdbTypeObj = CDBTypes.objects.get(name=confidenceLevel)
            except CDBTypes.DoesNotExist as e:
                errMsg = "Issue getting Confidence Level " + str(confidenceLevel) + ": " + str(e)
                logger.error(errMsg)
                return HttpResponse(errMsg,content_type="text/plain")
        lastPassed = cireports.utils.getLatestGoodProductSetVersion(productSetName, dropName, confidenceLevel)
        return HttpResponse(lastPassed,content_type="text/plain")
    except Exception as e:
        errMsg = "Issue getting Product Set Version "+str(e)
        logger.error(errMsg)
        return HttpResponse(errMsg,content_type="text/plain")


def getProductSetVersionContents(request):
    '''
    Return Product Set Contents
    '''
    pretty = dropName = None
    versionContents=None
    try:
        productSetName=request.GET['productSet']
        dropName=request.GET.get('drop', None)
        productSetVersion=request.GET['version']
        pretty = request.GET.get('pretty', False)
        if pretty:
            if pretty.lower() == "false":
                pretty = False
            elif pretty.lower() == "true":
                pretty = True

        if dropName is not None:
            product = ProductSetRelease.objects.only('release__product__id').values('release__product__id').filter(productSet__name=productSetName)[0]
            dropObj = Drop.objects.only('release__id').values('release__id').get(name=dropName, release__product__id=product['release__product__id'])
            productSetRelObj = ProductSetRelease.objects.only('id').values('id').get(productSet__name=productSetName,release__id=dropObj['release__id'])
            productSetVersionObj = ProductSetVersion.objects.only('id', 'version', 'productSetRelease__number').values('id', 'version', 'productSetRelease__number').get(version=productSetVersion,productSetRelease__id=productSetRelObj['id'])
        else:
            productSetObj = ProductSet.objects.only('id').values('id').get(name=productSetName)
            productSetVersionObj = ProductSetVersion.objects.only('id', 'version', 'productSetRelease__number').values('id', 'version', 'productSetRelease__number').get(version=productSetVersion, productSetRelease__productSet__id=productSetObj['id'])

        productSetNumber =  productSetVersionObj['productSetRelease__number']
        productSetVersion =  productSetVersionObj['version']
        productSetVersionId = productSetVersionObj['id']

        valueFields = "mediaArtifactVersion__artifactId", "mediaArtifactVersion__groupId", "mediaArtifactVersion__version", \
                      "mediaArtifactVersion__mediaArtifact__mediaType", "mediaArtifactVersion__drop__name", \
                      "productSetVersion__drop__name", "mediaArtifactVersion__externally_released", \
                      "mediaArtifactVersion__externally_released_ip", "mediaArtifactVersion__externally_released_rstate", \
                      "mediaArtifactVersion__mediaArtifact__number", "mediaArtifactVersion__arm_repo", \
                      "mediaArtifactVersion__drop__release__product__name", "productSetVersion__id", "mediaArtifactVersion__mediaArtifact__deployType__type", \
                      "mediaArtifactVersion__systemInfo"
        contents = ProductSetVersionContent.objects.only(valueFields).values(*valueFields).filter(productSetVersion__id=productSetVersionId)

        contentsList = cireports.utils.getProductSetVersionContentsData(contents)

        versionContents = [
                    {
                        "version": productSetVersion,
                        "number": productSetNumber,
                        "contents":contentsList
                    } ]


    except Exception as e:
            logger.error("Issue getting Product Set Versions Contents: " + str(e))
            versionContents = [
                {
                    "version": 'error',
                    "number": 'error',
                    "contents": 'error',
                }
            ]

    if pretty:
        ret = json.dumps(versionContents, sort_keys=True, indent=4)
    else:
        ret = json.dumps(versionContents)

    return HttpResponse(ret, content_type="application/json")

def getDropContents(request):
    '''
    Function to return contents of a drop in json format
    '''
    try:
        productName=request.GET['product']
        dropName=request.GET['drop']
        pretty=request.GET.get('pretty')
        mediaCategory=request.GET.get('mediaCategory',False)
        showExcluded=request.GET.get('showExcluded',False)
        baseIsoName=request.GET.get('baseIsoName',None)
        baseIsoVersion=request.GET.get('baseIsoVersion',None)
        useLatestInfra=request.GET.get('useLatestInfra',False)
        useLatestApp=request.GET.get('useLatestApp',False)
        localNexus=request.GET.get('useLocalNexus',False)
        excludeMediaCategory=request.GET.get('excludeMediaCategory',False)
        if useLatestApp or useLatestInfra:
            if baseIsoName == "None" or baseIsoName == None or baseIsoVersion == "None" or baseIsoVersion == None:
                logger.info("No base ISO defined, using latest drop contents")
                excludeFromDrop = None
            else:
                ISOObj = ISObuild.objects.get(version=baseIsoVersion, mediaArtifact__name=baseIsoName)
                # if useLatestInfra => exclude infra from iso and exclude app from drop
                if useLatestInfra:
                    excludeFromIso = 'infra'
                    excludeFromDrop = 'app'
                if useLatestApp:
                    excludeFromIso = 'app'
                    excludeFromDrop = 'infra'
                modifiedIsoContent = cireports.utils.isoContents(ISOObj,productName,localNexus,excludeFromIso)
                if modifiedIsoContent == [{"error":"error"}]:
                    logger.error("Issue with getting contents "+str(e))
                    ret = json.dumps([{"error":"error"}])
                    return HttpResponse(ret, content_type="application/json")
        else:
            excludeFromDrop = None
        if pretty != None:
            if pretty.lower() == "true":
                pretty = True
            else:
                pretty=False
        contentsList = cireports.utils.dropContents(productName,dropName,mediaCategory,showExcluded,excludeMediaCategory,localNexus,excludeFromDrop)
        if not excludeFromDrop == None:
            contentsList = contentsList+modifiedIsoContent
        if pretty:
            ret = json.dumps(contentsList, sort_keys=True, indent=4)
        else:
            ret = json.dumps(contentsList)
    except Exception as e:
        logger.error("Issue with getting drop contents "+str(e))
        ret = json.dumps([{"error":"error"}])
    return HttpResponse(ret, content_type="application/json")

@csrf_exempt
def createISOContent(request):
    if request.method == 'POST':
        try:
            group = request.POST.get('group')
            artifact = request.POST.get('artifact')
            version = request.POST.get('version')
            drop = request.POST.get('drop')
            product = request.POST.get('product')
            content = request.POST.get('content')
            repo  = request.POST.get('repo')
            systemInfo = request.POST.get('systemInfo')
            result = cireports.utils.createIso(group,artifact,version,drop,product,content,repo,systemInfo)
        except Exception as e:
            logger.error("Issue creating ISO" +str(e))
            result = "ERROR: creating ISO: "+str(e)

    else:
        result="ERROR: only Post calls accepted"
    return HttpResponse(result, content_type="text/plain")

def getPackagesDeliveredToProduct(request):
    product = request.GET.get("product")
    productObj = Product.objects.get(name=product)
    jsonPackages = {}
    packageList, number = utils.getPackagesBasedOnProduct(productObj)

    packages=[]
    for package in packageList:
        packages.append(package.name)

    jsonPackages["Packages"]= sorted(packages)
    ret = json.dumps(jsonPackages)
    return HttpResponse(ret, content_type="application/json")

def getArtifactsDeliveredToProduct(request):
    product = request.GET.get("product")
    packageType = request.GET.get("packageType")
    productObj = Product.objects.get(name=product)
    jsonPackages = {}
    packageList, number = utils.getArtifactsBasedOnProduct(productObj,packageType)

    packages=[]
    for package in packageList:
        packages.append(package.name)

    jsonPackages["Packages"]= sorted(packages)
    ret = json.dumps(jsonPackages)
    return HttpResponse(ret, content_type="application/json")



@csrf_exempt
def checkForChanges(request):
    if request.method == 'GET':
        try:
            drop = request.GET.get('drop')
            release = request.GET.get('release')
            product = request.GET.get('product')
            isoType = request.GET.get('isoType', "product-iso")

            currentDrop = Drop.objects.get(name=drop, release__name=release)
            if "testware" in str(isoType):
                dropContentMapping = cireports.utils.getPackageBaseline(currentDrop, "testware")
            else:
                dropContentMapping = cireports.utils.getPackageBaseline(currentDrop, "packages")
            dropContent = []
            for mapping in dropContentMapping:
               if mapping.package_revision.isoExclude:
                    continue
               dropContent.append(mapping)
            result = cireports.utils.checkingForChangesInDrop(dropContent, currentDrop, drop, isoType)
        except Exception as e:
            errorMsg = "ERROR: cannot check for changes to the ISO: "+str(e)
            logger.error(errorMsg)
            result = errorMsg
    else:
        result="ERROR: only GET calls accepted"
    return HttpResponse(result, content_type="text/plain")

def displayImageContent(request, product, pkgRevId, version):
    hostname = request.META['HTTP_HOST']
    imagesDict = {}
    parentArtifactsDict = {}
    parentDepsDict = {}
    installedArtifactsList = []
    installedDependenciesList = []
    parent = True
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        packageInfo = PackageRevision.objects.get(id=pkgRevId)
        imageContent = ImageContent.objects.get(packageRev_id=pkgRevId)
        installedArtifactsList = str(imageContent.installedArtifacts).split(",")
        installedDependenciesList = str(imageContent.installedDependencies).split(",")
        while parent:
            if imageContent.parent is not None:
                imageContent = ImageContent.objects.get(packageRev_id=imageContent.parent.packageRev_id)
                parentArtifactsList = str(imageContent.installedArtifacts).split(",")
                parentDependenciesList = str(imageContent.installedDependencies).split(",")
                parentArtifactsDict[imageContent.packageRev.package.name] = parentArtifactsList
                parentDepsDict[imageContent.packageRev.package.name] = parentDependenciesList
                imagesDict[imageContent.id] = imageContent.packageRev.package.name
            else:
                parent = False
    except Exception as e:
        logger.error("Error: Cannot find image content for package revision id : " +str(pkgRevId) + " in the database. " +str(e))
    return render(request, "cireports/imageContent.html",
            {
                'packageInfo': packageInfo,
                'installedArtifactsList': installedArtifactsList,
                'installedDependenciesList': installedDependenciesList,
                'parentArtifactsDict': parentArtifactsDict,
                'parentDepsDict': parentDepsDict,
                'imagesDict': imagesDict,
                'product': product,
                'femObj': femObj
            })

def storeImageContents(pkgRevId, contents):
    '''
    '''
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    decodedJsonContents = json.loads(contents)
    instArtifacts = instDeps = parentArtifact = parentGroup = parentVersion = parentImageContent = None
    try:
        pkgRevision = PackageRevision.objects.get(id=pkgRevId)
    except Exception as e:
        logger.error("Error: Cannot find package revision id : " +str(pkgRevId) + " in the database. " +str(e))
        return

    for entry in decodedJsonContents:
        for key,value in entry.iteritems():
            if key == 'imageParentArtifact':
                parentArtifact = entry['imageParentArtifact']
            if key == 'imageParentGroup':
                parentGroup = entry['imageParentGroup']
            if key == 'imageParentVersion':
                parentVersion = entry['imageParentVersion']
            if key == 'artifactsToInstall':
                instArtifacts = entry['artifactsToInstall']['artifacts']
            if key == 'artifactInstallTimeDependencies':
                instDeps = entry['artifactInstallTimeDependencies']['dependencies']

    try:
        parentPkgRevision = PackageRevision.objects.get(groupId=parentGroup , artifactId=parentArtifact , version=parentVersion)
        parentImageContent = ImageContent.objects.get(packageRev_id=parentPkgRevision.id)
    except Exception as e:
        logger.error("No Parent Image found so no information stored in parent field for Image Content table")

    try:
        with transaction.atomic():
            newImageContent = ImageContent(packageRev_id=pkgRevId,installedArtifacts=instArtifacts,installedDependencies=instDeps,dateCreated=now,parent=parentImageContent)
            newImageContent.save()
    except IntegrityError as e:
            logger.error(str(e))

def getAllLatestTestwareArtifacts(request):
    '''
    REST call to get the latest revision of all the testware artifacts
    '''
    nexusUrlPublic = config.get("CIFWK", "nexus_public_url")
    nexusUrl = config.get("CIFWK", "nexus_url")
    if request.method == 'GET':
        urlCheck = request.GET.get('urlCheck')
        product = request.GET.get('product')
        if urlCheck != None:
            urlCheck = True

        if product != None and not Product.objects.filter(name=product).exists():
            return render(request, "cireports/product_error.html",{"error":str(product)  +" is an invalid product."})
        testwareArtifacts = cireports.utils.getAllTestware(product,urlCheck)
        return render_to_response(
                'cireports/testware.xml',
                {'testwareArtifacts': testwareArtifacts,
                  'nexusUrlPublic': nexusUrlPublic,
                  'nexusUrl': nexusUrl},
                content_type='application/xml'
        )
    return HttpResponse("Cannot find any testware information")

def viewComponentEntryPoint(request, product):
    '''
    The viewComponentEntryPoint loads the Component entry web page with a pre populated Parent Component list
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        pageHitCounter("ArtifactAssociationManagement", product.id, str(request.user))
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    return render(request, "cireports/componentEntryIndex.html",{ 'product':product, 'femObj': femObj,})

def getHighLevelComponents(request, product):
    '''
    The getHighLevelComponents returns all the parent component that are associated to a product
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)

    result = json.dumps([{"error":""}])
    elementsJson = {"Parent": []}
    try:
        if Component.objects.filter(parent=None, product=product).exists():
            parentComponentObj = Component.objects.filter(parent=None, product=product, deprecated=0)
            for parentComponent in parentComponentObj:
                data={}
                data["name"]=parentComponent.element
                elementsJson["Parent"].append(data)
        else:
            data={}
            data["name"]="None"
            elementsJson["Parent"].append(data)
        result = json.dumps(elementsJson)
    except Exception as e:
        logger.error("Issue building parent Component List, Error: " +str(e))
        result = json.dumps([{"error":str(e)}])
    return HttpResponse(result, content_type="application/json")

def getLowLevelComponents(request):
    '''
    The getLowLevelComponents function gets the all children objects of a component Object and returns to the webpage
    '''
    product = request.GET.get("product")
    parentComponent = request.GET.get("parentComponent")
    jsonChildComponents = {}
    childComponentList=[]
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    try:
        if "None" in parentComponent:
            childComponentList.append("None");
            jsonChildComponents["ChildComponents"]= sorted(childComponentList)
            result = json.dumps(jsonChildComponents)
            return HttpResponse(result, content_type="application/json")
        jsonChildComponents = {}
        childComponentList=[]
        if Component.objects.filter(product=product, element=parentComponent, deprecated=0).exists():
            elementObj = Component.objects.get(product=product, element=parentComponent, deprecated=0)
        else:
            result = json.dumps([{"error":"Component "+parentComponent+" does not exist"}])
            return HttpResponse(result, content_type="application/json", status=404)
        if Component.objects.filter(parent=elementObj.id).exists():
            componentObjs = Component.objects.filter(parent=elementObj.id)
            for componentObj in componentObjs:
                childComponentList.append(componentObj.element)
        if not childComponentList:
            childComponentList.append("None");
        jsonChildComponents["ChildComponents"]= sorted(childComponentList)
        result = json.dumps(jsonChildComponents)
    except Exception as error:
        logger.error("Issue building Low Level Component List, Error: " +str(error))
        result = json.dumps([{"error":str(error)}])
    return HttpResponse(result, content_type="application/json")

@csrf_exempt
def importComponents(request, product):
    '''
    The importComponents updates the CI DB with Component data entered by the end user.
    '''
    result =  json.dumps([{"success": "Data Successfully Loaded into the CI DB"}])
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    try:
        if request.method == 'POST':
            componentResult = request.POST.get("componentResult")
        if Product.objects.filter(name=product).exists():
            product = Product.objects.get(name=product)
        result = utils.writeImportComponents(product, componentResult, result)
    except Exception as e:
        logger.error("Issue posting component data to CI DB " + str(e))
        result = json.dumps([{"error":str(e)}])
    return HttpResponse(result, content_type="application/json")

@csrf_exempt
def removeComponents(request, product):
    '''
    The removeComponents removes the CI DB with Component data entered by the end user.
    '''
    result =  json.dumps([{"success": "Data Successfully Removed from the CI DB"}])
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    try:
        if request.method == 'POST':
            componentResult = request.POST.get("componentResult")
        if Product.objects.filter(name=product).exists():
            product = Product.objects.get(name=product)
        result = utils.removeComponents(product, componentResult, result)
    except Exception as e:
        logger.error("Issue removing component data from CI DB " + str(e))
        result = json.dumps([{"error":str(e)}])
    return HttpResponse(result, content_type="application/json")

def packagesInComponent(request):
    '''
    The packagesInComponent function return the package that are associated with a component back to the end user
    '''
    product = request.GET.get("product")
    parent = str(request.GET.get("parentValue"))
    child = str(request.GET.get("childValue"))

    packageList = []
    jsonPackages = {}
    if "None" in parent or "None" in child:
        packageList.append("None");
        jsonPackages["Componentpackages"]= sorted(packageList)
        ret = json.dumps(jsonPackages)
        return HttpResponse(ret, content_type="application/json")
    if Product.objects.filter(name=product).exists():
        productObj = Product.objects.get(name=product)
    parentComponentObj = Component.objects.get(product=productObj, element=parent)
    if Component.objects.filter(product=productObj,parent=parentComponentObj,element=child).exists():
        componentObj = Component.objects.get(product=productObj,parent=parentComponentObj,element=child)

    if PackageComponentMapping.objects.filter(component=componentObj).exists():
        packageComponentObj = PackageComponentMapping.objects.filter(component=componentObj)
        for packageComponent in packageComponentObj:
            packageList.append(packageComponent.package.name)
    if not packageList:
        packageList.append("None");

    jsonPackages["Componentpackages"]= sorted(packageList)
    ret = json.dumps(jsonPackages)
    return HttpResponse(ret, content_type="application/json")

def getProductLabels(request, product):
    '''
    The getProductLabels get all Labels Defined in DB and returns only the label defined within the Product to the user.
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        result = json.dumps([{"error":"Product "+product+" does not exist"}])
        return HttpResponse(result, content_type="application/json", status=404)

    result = json.dumps([{"error":""}])
    labelsJson = {"Label": []}
    labelList = []
    checkerList = []
    labels = Label.objects.all()
    try:
        if labels:
            for label in labels:
                labelList.append(label.name)
            if Component.objects.filter(parent=None, product=product).exists():
                componentObj = Component.objects.filter(parent=None, product=product)
                for component in componentObj:
                    if component.label.name in labelList and component.label.name not in checkerList:
                        checkerList.append(component.label.name)
                        data={}
                        data["name"]=str(component.label.name)
                        labelsJson["Label"].append(data)
        if not checkerList:
            data={}
            data["name"]="None"
            labelsJson["Label"].append(data)
        result = json.dumps(labelsJson)
    except Exception as e:
        logger.error("There was an issue building Label List for Display, Error thrown: " +str(e))
        result = json.dumps([{"error":str(e)}])
    return HttpResponse(result, content_type="application/json")

def getParentComponentsOfLabel(request, product, label):
    '''
    The getParentComponentsOfLabel function get the Parent Components based on the product and label.
    '''
    result = json.dumps([{"error":""}])
    parentJson = {"Parents": []}
    if "None" in label:
        data={}
        data["name"] = "None"
        parentJson["Parents"].append(data)
        result = json.dumps(parentJson)
        return HttpResponse(result, content_type="application/json")

    if Product.objects.filter(name=product).exists():
        productObj = Product.objects.get(name=product)
    else:
        result = json.dumps([{"error":"Product "+product+" does not exist"}])
        return HttpResponse(result, content_type="application/json", status=404)
    if Label.objects.filter(name=label).exists():
        labelObj = Label.objects.get(name=label)
    else:
        result = json.dumps([{"error":"Label "+label+" does not exist"}])
        return HttpResponse(result, content_type="application/json", status=404)

    try:
        if Component.objects.filter(parent=None, product=productObj, label=labelObj).exists():
            componentObj = Component.objects.filter(parent=None, product=productObj, label=labelObj,deprecated=0)
            for component in componentObj:
                data={}
                data["name"] = component.element
                parentJson["Parents"].append(data)
        else:
            data={}
            data["name"] = "None"
            parentJson["Parents"].append(data)
        result = json.dumps(parentJson)
    except Exception as e:
        logger.error("There was an issue building Parent List for Display, Error thrown: " +str(e))
        result = json.dumps([{"error":str(e)}])
    return HttpResponse(result, content_type="application/json")

def getChildLabelFromParentLabel(request,product,parentName):
    '''
    The getChildLabelFromParentLabel function gets a child label for a given parent and component
    '''
    if Product.objects.filter(name=product).exists():
        productObj = Product.objects.get(name=product)
    result = json.dumps([{"error":""}])
    childLabelJson = {"ChildLabel": []}
    try:
        if Component.objects.filter(parent=None, element=str(parentName), product=productObj).exists():
            parentComponentObj = Component.objects.filter(parent=None, element=str(parentName), product=productObj)
            for parentComponent in parentComponentObj:
                childComponentObj = Component.objects.filter(parent=parentComponent)[0]
                data={}
                data["name"] = str(childComponentObj.label.name)
                childLabelJson["ChildLabel"].append(data)
        else:
            data={}
            data["name"] = "None"
            childLabelJson["ChildLabel"].append(data)
        result = json.dumps(childLabelJson)
    except Exception as e:
        logger.error("There was an issue getting child label for display, Error thrown: " +str(e))
        result = json.dumps([{"error":str(e)}])
    return HttpResponse(result, content_type="application/json")

def getComponentInformation(request,product):
    '''
    This function returns all the component information associated with a specific product
    '''
    if Product.objects.filter(name=product).exists():
        productObj = Product.objects.get(name=product)
    parent = request.GET.get("parent")
    result = json.dumps([{"error":""}])
    ciJson = {"ComponentInfo": []}
    allComponents = []
    childLabel = parentLabel = ""
    try:
        if Component.objects.filter(parent=None, element=parent, product=productObj).exists():
            parentComponentObj = Component.objects.filter(parent=None, element=parent, product=productObj)
            childLabel = Component.objects.filter(parent=parentComponentObj)[0].label.name
            parentLabel = Component.objects.filter(parent=parentComponentObj)[0].parent.label.name
        allComponents = list(Component.objects.only('element').filter(product__name=product, deprecated=0).order_by('parent__element'))
        allComponentParents = list(Component.objects.only('parent__element').filter(product__name=product,deprecated=0).order_by('element'))
        if allComponents:
            for parentComp in allComponentParents:
                parentData={}
                parentData["parent"] = str(parentComp.element)
                parentData["parentLabel"] = str(parentComp.label)
                parentData["children"] = []
                for component in allComponents:
                    if str(component.parent) != "None":
                        if str(parentComp.element) == str(component.parent.element):
                            data={}
                            data["element"] = str(component.element)
                            data["label"] = str(component.label)
                            data["parent"] = str(component.parent.element)
                            # Get the associated Packages with the component
                            pkgs = []
                            pkgMaps = PackageComponentMapping.objects.only('package__name').values('package__name').filter(component=component)
                            for map in pkgMaps:
                                pkgs.append(map['package__name'])
                            if len(pkgs) == 0:
                                pkgs.append("No Packages")
                            data["packages"] = pkgs
                            parentData["children"].append(data)
                if len(parentData["children"]) == 0:
                    data={}
                    data["label"] = "None"
                    parentData["children"].append(data)
                ciJson["ComponentInfo"].append(parentData)
        if len(allComponents) == 0:
            data={}
            data["parent"] = "None"
            ciJson["ComponentInfo"].append(data)
        result = json.dumps(ciJson, sort_keys=True, indent=4)
    except Exception as e:
        logger.error("There was an issue getting component information for product, "+ str(product) + "Error thrown: " +str(e))
        result = json.dumps([{"error":str(e)}])
    return render(request, "cireports/summary.html", {
       'allComponents':allComponents,
       'ciJson':ciJson,
       'label':childLabel,
       'parentLabel':parentLabel,
    })

def getInfrastructurePackages(request):
    '''
    The getInfrastructurePackages function returns a list of Package Revisions that are flagged as Infrastructure
    '''
    try:
        productName=request.GET['product']
        dropName=request.GET['drop']
        pretty=request.GET.get('pretty')
        if pretty != None:
            if pretty.lower() == "true":
                pretty = True
            else:
                pretty=False
        infraPkgs = cireports.utils.getInfraPackages(productName,dropName)
        if pretty:
            ret = json.dumps(infraPkgs, sort_keys=True, indent=4)
        else:
            ret = json.dumps(infraPkgs)
    except Exception as e:
        logger.error("Issue with getting infrastructure packages "+str(e))
        ret = json.dumps([{"error":"error"}])
    return HttpResponse(ret, content_type="application/json")

@csrf_exempt
def getArtifactFromLocalNexus(request):
    '''
    The getArtifactFromLocalNexus REST call gets Artifact from Local defined Nexus Repo and copies to /dev/null locally
    '''
    packageObj = packageRevisionObj = None
    localNexusURL = "'localNexusURL not Found'"
    if request.method == 'POST':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")
    if request.method == "GET":
        artifactID = request.GET.get("artifactID")
        version = request.GET.get("version")

        if artifactID is None or not artifactID or artifactID == "None":
            return HttpResponse("Error: Artifact artifactID is required.\n")
        if version is None or not version or version == "None":
            return HttpResponse("Error: Artifact version is required.\n")

        try:
            if Package.objects.filter(name=artifactID).exists():
                packageObj = Package.objects.only('id').values('id').get(name=artifactID)
                if PackageRevision.objects.filter(package__id=packageObj['id'], version=version).exists():
                    fields = ('m2type', 'groupId')
                    packageRevisionObj = PackageRevision.objects.only(fields).values(*fields).get(package=packageObj['id'], version=version)
                else:
                    errorMsg = "Warning: No Artifact Revision found for " + str(artifactID) + " with version " + str(version) + " unable to download artifact please try again"
                    logger.error(errorMsg)
                    return HttpResponse(errorMsg)
            else:
                errorMsg = "Warning: No Artifact found for " + str(artifactID) + " ,unable to download artifact please try again"
                logger.error(errorMsg)
                return HttpResponse(errorMsg)
            localNexusURL = utils.getLocalNexusUrl("ENM",packageRevisionObj['groupId'],artifactID,version,artifactID,packageRevisionObj['m2type'])
        except Exception as e:
            errorMsg = "Warning: Building up Nexus URL for package " + str(artifactID) + " " + str(version) + " ,unable to download artifact: Warning: " + str(e) + ".\n"
            logger.error(errorMsg)
            return HttpResponse(errorMsg)
    message = None
    try:
        returnCode = requests.head(localNexusURL)
        if str(returnCode.status_code) != "200":
            message = "Warning: Issue using url: " + str(localNexusURL) + ", status code: " + str(returnCode.status_code) + "\n"
            logger.error(message)
            return HttpResponse(message)
        logger.info("Successfully downloaded artifact: " + str(artifactID) + "-" + str(version) + " from local proxy.\n")
        message = "Local Nexus URL for Artifact is; " + str(localNexusURL)
    except Exception as e:
        message = "Warning: Issue using url: " + str(localNexusURL) +", " + str(e) + ".\n"
        logger.error(message)
        return HttpResponse(message)

    return HttpResponse(message)

def getInfrastructurePackagesFromIso(request):
    '''
    The getInfrastructurePackagesFromIso function returns a list of Package Revisions that are flagged as Infrastructure that are contained in an ISO
    '''
    try:
        isoVer=request.GET['isoVersion']
        pretty=request.GET.get('pretty')
        if pretty != None:
            if pretty.lower() == "true":
                pretty = True
            else:
                pretty=False
        infraPkgs = cireports.utils.getInfraPackages(None,None,isoVer)
        if pretty:
            ret = json.dumps(infraPkgs, sort_keys=True, indent=4)
        else:
            ret = json.dumps(infraPkgs)
    except Exception as e:
        logger.error("Issue with getting infrastructure packages "+str(e))
        ret = json.dumps([{"error":"error"}])
    return HttpResponse(ret, content_type="application/json")

@csrf_exempt
def updateInfraStatusOnPkg(request):
    content = StringIO()
    if request.method == 'POST':
        try:
            pkgName = request.POST.get('package')
            status = request.POST.get('infra')
            call_command('setPackageInfraStatus', package=str(pkgName), infra=str(status), stdout=content)
        except Exception as e:
            result = "ERROR: Unable to set Infrastructure status to " + str(status) + " for " + str(pkgName) + "  " + str(e)
            logger.error(result)
            return HttpResponse(result, content_type="text/plain")
        content.seek(0)
        result = content.read()
    else:
        result="ERROR: only POST calls accepted"
    return HttpResponse(result, content_type="text/plain")

@login_required
def setCautionStatus(request, product, drop, version, type):
    '''
    Use to run the Jenkins Job to  set caution status on Media Artifact Version or Product Set Version
    '''
    user = User.objects.get(username=str(request.user))
    adminGroup = config.get("CIFWK", "adminGroup")
    if not user.groups.filter(name=adminGroup).exists():
        return render(request, "cireports/access_error.html",{'error':'User not authorised to alter the CDB status, please contact the CI Execution/Maintrack Team'})

    productSet = "None"
    if str(type) == "product":
        if Product.objects.filter(name=product).exists():
            product = Product.objects.get(name=product)
            femObj = FEMLink.objects.filter(product=product)
        else:
            product = "None"
            femObj = "None"
    else:
        productSet = product
        product = "None"
        femObj = "None"
    if request.method == 'GET':
        artifactId = request.GET.get('artifactId')
        groupId =  request.GET.get('groupId')
        signum = str(request.user)

        return render(request, "cireports/setCautionStatus.html",
                    {
                        'artifactId': artifactId,
                        'groupId': groupId,
                        'version': version,
                        'signum': signum,
                        'drop': drop,
                        'productSet': productSet,
                        'type': type,
                        'product': product,
                        'femObj' : femObj
                    })
    if request.method == 'POST':
        artifactId = request.POST.get('artifactId')
        groupId =  request.POST.get('groupId')
        signum = str(request.user)
        comment = request.POST.get('comment')
        if not comment:
            return render(request, "cireports/setCautionStatus.html",
                    {
                        'message' : 'Please give a comment',
                        'artifactId': artifactId,
                        'groupId': groupId,
                        'version': version,
                        'signum': signum,
                        'drop': drop,
                        'productSet': productSet,
                        'type': type,
                        'product': product,
                        'femObj' : femObj
                    })
        if " " in str(artifactId):
            artifactId = str(artifactId).replace(' ', '%20')
        if " " in str(comment):
            comment = str(comment).replace(' ', '%20')
        try:
           femBaseUrl = config.get('FEM', 'femBasePlus')
           jenkinsJob = config.get('FEM', 'CautionStatus')
           os.system("/usr/bin/curl -X POST '"+str(femBaseUrl)+str(jenkinsJob)+"ARTIFACTID="+str(artifactId)+"&GROUPID="+ str(groupId) +"&VERSION="+str(version)+"&SIGNUM="+str(signum)+"&COMMENT="+str(comment)+"'")
        except Exception as e:
           logger.error("Issue setting the Caution Status: " + str(e) )
    if str(type) == "product":
        return HttpResponseRedirect("/" + str(product)+ "/" + str(drop) + "/mediaContent/"+ str(artifactId) +"/" + str(version))
    else:
        return HttpResponseRedirect("/" + str(productSet)+ "/content/" + str(drop) + "/" + str(version))


def validateIsoUploadedToHub(request):
    '''
    This rest call verifies the md5 of the uploaded ISO against that of the ISO in the hosted Repo
    '''
    group = request.GET.get('group')
    artifact = request.GET.get('artifact')
    version = request.GET.get('version')
    extension = request.GET.get('extension')
    classifier = request.GET.get('classifier',"")

    group = group.replace(".", "/")

    md5Path = "/"+group+"/"+artifact+"/"+version+"/"+artifact+"-"+version+classifier+"."+extension+".md5"
    hubNexus = config.get("CIFWK", "nexus_url")

    hostedIsoMd5 = config.get("DMT_AUTODEPLOY", "ENM_nexus_url") + md5Path
    hubRepoIsoMd5 = hubNexus + "/releases" + md5Path

    return HttpResponse(cireports.utils.compareIsoMd5(hostedIsoMd5, hubRepoIsoMd5))

def getArtifactsForTest(request):
    '''
    Function to return artifacts new to drop and not in iso. Based on defination in component list
    '''
    try:
        component = request.GET.get('component',None)
        subComponent = request.GET.get('subComponent',None)
        isoName = request.GET.get('KGBisoName',None)
        isoVersion = request.GET.get('KGBisoVersion',None)
        drop = request.GET.get('drop',None)
        product = request.GET.get('product',None)
        manualList = request.GET.get('manualList',"")
        useIntended = request.GET.get('useIntended',"True")
        componentArtifacts = cireports.utils.getArtifactsFromComponent(component,subComponent,product)
        if useIntended == "True":
            matchingDropArtifacts = cireports.utils.intendedDropContents(drop,product,componentArtifacts)
        else:
            matchingDropArtifacts = cireports.utils.partialDropContents(drop,product,componentArtifacts)
        artifactsToTest = cireports.utils.partialIsoContents(isoVersion,isoName, matchingDropArtifacts,manualList)
        if not manualList == "":
            artifactsToTest = artifactsToTest+"||"+manualList
        return HttpResponse(artifactsToTest)
    except Exception as e:
        logger.error("Issue getting artifacts for test "+str(e))
        return HttpResponse("")

def getPrimDataForTest(request):
    '''
    Returning the data that could be written to prim if UI is used
    '''
    try:
        product = request.GET.get("product")
        drop = request.GET.get("drop")
        rState = request.GET.get("rstate")
        topProduct =  request.GET.get("baseproduct")
        topRev = request.GET.get("baserevision")
        user = request.GET.get("username")
        password = request.GET.get("password")
        newRelease = request.GET.get("newrelease")
        media = request.GET.get("media")
        product = Product.objects.get(name=product)
        if newRelease == None:
            newRelease = False
        else:
            newRelease = True
        if not rState:
            rState = None
        try:
            result=utils.prim(drop, product, media, rState, topProduct, topRev, user, password, newRelease)
        except Exception as e:
            logger.error("Error when getting Prim information " + str(e))
        if not "error" in result:
           return render(request, "cireports/prim_result.html", {
                       'product': product,
                       'drop': drop,
                       'media': media,
                       'user': user,
                       'password':password,
                       'dataList': result['dataList'],
                       'diffData': result['diff'],
                       'file' : result['file']
                       })
    except Exception as e:
        logger.error("Issue getting prim data for test "+str(e))
        return HttpResponse("ERROR")

@csrf_exempt
def getAOMandRstateInfo(request):
    '''
    The getAOMandRstateInfo function returns the AOM and Rstate information associated with a particular product and drop
    '''
    try:
        product=request.GET.get('product')
        drop=request.GET.get('drop')
        if product is None or not product or product == "None":
            return HttpResponse("Error: Product required.\n")
        if drop is None or not drop or drop == "None":
            return HttpResponse("Error: Drop required.\n")
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        if 'RSTATE' in dropObj.systemInfo:
            result = "No AOM Number and RSTATE information found for Product: "+str(product) + " and drop: "+ str(drop)
        else:
            result = str(dropObj.systemInfo)
    except Exception as e:
        errMsg = "Error: Issue retrieving AOM and RSTATE information"
        logger.error(errMsg +str(e))
        return HttpResponse(errMsg)
    return HttpResponse(result)

@csrf_exempt
def getListOfPackages(request):
    '''
    This function returns a list of Package names for a specific drop and product
    '''
    packages = ""
    if request.method == 'GET':
        dropName = request.GET.get('drop')
        productName = request.GET.get('product')
        try:
            dropObj = Drop.objects.get(name=dropName, release__product__name=productName)
            mappings = DropPackageMapping.objects.filter(drop=dropObj.id,released=1,obsolete=0,package_revision__correction__exact=0).order_by('-date_created').exclude(package_revision__platform="sparc")

            packageNameList = []
            for map in mappings:
                packageNameList.append(str(map.package_revision.package.name))
            packages = ",".join(packageNameList)
        except Exception as e:
            packages = "No Packages found for drop:" +str(dropName) +  " and product:" + str(productName)
            logger.error("Error when getting list of Packages for drop:" +str(dropName) +  " and product:" + str(productName) + str(e))
    else:
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")
    return HttpResponse(packages)

@login_required
def modifyDrop(request, product, drop, activityId=None):
    '''
    The modifyDrop function is used to set a drops status to either open, closed or limited
    '''
    user = User.objects.get(username=str(request.user))
    modifyDropGroup = config.get("CIFWK", "adminGroup")
    limitedReasons = DropLimitedReason.objects.all()
    if not user.groups.filter(name=modifyDropGroup).exists():
        return render(request, "cireports/drop_error.html",{'error':'User not authorised to modify this drop'})

    frozen = None
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        dropActivities = DropActivity.objects.filter(drop=dropObj).order_by('-id')
        if dropObj.actual_release_date == None:
            frozenDate =  dropObj.planned_release_date
        else:
            frozenDate = dropObj.actual_release_date
        dropDate = datetime.strptime(str(frozenDate), "%Y-%m-%d %H:%M:%S")
        [newdate,mil] = str(datetime.now()).split('.')
        nowDateTime = datetime.strptime(str(newdate), "%Y-%m-%d %H:%M:%S")
        if dropDate <= nowDateTime:
            frozen = True
        if request.method == 'POST':
            action = request.POST.get("action")
            reason = request.POST.get("reason")
            limitedReason = request.POST.get("limitedreason")
            if action == "limited":
                limitedReason = DropLimitedReason.objects.get(reason=limitedReason)
                newDropActivity = DropActivity.objects.create(drop=dropObj, action=action, desc=reason, user=user, date=nowDateTime, limitedReason=limitedReason)
            else:
                newDropActivity = DropActivity.objects.create(drop=dropObj, action=action, desc=reason, user=user, date=nowDateTime)
            dropObj.status = action
            dropObj.save(force_update=True)
    except Drop.DoesNotExist:
        logger.error("Requested Drop: " + str(drop) + " is not contained within the Database")
        raise Http404
    return render(request, "cireports/modifyDrop.html",
            {
                'drop': dropObj,
                'product': product,
                'femObj': femObj,
                'frozen': frozen,
                'dropActivities': dropActivities,
                'limitedReasons': limitedReasons,
            })

@login_required
def modifyDropReason(request, product, drop, activityId):
    '''
    The modifyDropReason function is used to change the reason as to why a drops status has changed
    '''
    user = User.objects.get(username=str(request.user))
    modifyDropGroup = config.get("CIFWK", "adminGroup")
    limitedReasons = DropLimitedReason.objects.all()
    if not user.groups.filter(name=modifyDropGroup).exists():
        return render(request, "cireports/drop_error.html",{'error':'User not authorised to modify this information'})

    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"

    try:
        dropActivity = DropActivity.objects.get(id=activityId)
        if request.method == 'POST':
            reason = request.POST.get("reason")
            dropActivity = DropActivity.objects.get(id=activityId)
            if dropActivity.action =="limited":
                limitedReason = request.POST.get("limitedreason")
                limitedReason = DropLimitedReason.objects.get(reason=limitedReason)
                dropActivity.limitedReason = limitedReason
            dropActivity.desc = reason
            dropActivity.save(force_update=True)
            return HttpResponseRedirect("/" + str(product)+ "/modifydrop/" + str(drop) + "/")
    except Drop.DoesNotExist:
        logger.error("Requested Drop: " + str(drop) + " is not contained within the CI Database")
        raise Http404
    return render(request, "cireports/modifyDropReason.html",
            {
                'product': product,
                'femObj': femObj,
                'dropActivity': dropActivity,
                'limitedReasons': limitedReasons,
            })

@csrf_exempt
def createISOProductTestwareMapping(request):
    '''
    The createISOProductTestwareMapping function (POST RESTful Service) creates a Product ISO Version to Testware ISO Version mapping.
    If Both Product ISO and Testware ISO versions are defined a mapping will be created from this
    If a Product ISO Version is defined then latest Testware ISO Version for that Drop is Selected for mapping
    If a Testware ISO Version is defined then the latest Product ISO Version for that Drop is Selected for mapping
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This is a POST RestFul service, please try again.\n")
    if request.method == 'POST':
        drop = request.POST.get("drop")
        product = request.POST.get("product")
        productISOArtifactName = request.POST.get("productISOArtifactName")
        productISOVersion = request.POST.get("productISOVersion")
        testwareISOArtifactName = request.POST.get("testwareISOArtifactName")
        testwareISOVersion = request.POST.get("testwareISOVersion")
        creationInfo = ""

        if drop is None or not drop or drop == "None":
            return HttpResponse("Error: Please ensure that a Drop is defined, please try again.\n")
        if product is None or not product or product == "None":
            return HttpResponse("Error: Please ensure that a Product is defined, please try again.\n")
        if productISOArtifactName and not productISOVersion:
            return HttpResponse("Error: Please Ensure that ISO Artifact Name and Version is Specified, please try again.\n")
        if productISOVersion and not productISOArtifactName:
            return HttpResponse("Error: Please Ensure that ISO Artifact Name and Version is Specified, please try again.\n")
        if testwareISOArtifactName and not testwareISOVersion:
            return HttpResponse("Error: Please Ensure that ISO Testware Name and Version is Specified, please try again.\n")
        if testwareISOVersion and not testwareISOArtifactName:
            return HttpResponse("Error: Please Ensure that ISO Testware Name and Version is Specified, please try again.\n")
        if not productISOArtifactName and not productISOVersion and not testwareISOVersion and not testwareISOArtifactName:
            return HttpResponse("Error: Please Defined at Lease a Product/Testware ISO Name and Version, please try again.\n")

        if Drop.objects.filter(name=drop,release__product__name=product).exists():
            dropObj = Drop.objects.get(name=drop,release__product__name=str(product))
        else:
            return HttpResponse("Error: Product: '" + str(product) + "' with Drop: '" + str(drop) + "', does not exist, please try again.\n")

        if productISOArtifactName and productISOVersion:
            productISOBuildObj,testwareISOBuildObj,response = cireports.utils.getISOTestwareBuildGivenISOProductBuild(productISOArtifactName, productISOVersion, testwareISOArtifactName, testwareISOVersion, dropObj)

        elif testwareISOArtifactName and testwareISOVersion:
            productISOBuildObj,testwareISOBuildObj,response = cireports.utils.getISOProductBuildGivenISOTestwareBuild(productISOArtifactName, productISOVersion, testwareISOArtifactName, testwareISOVersion, dropObj)

        if "Error" in response or "Warning" in response:
            return HttpResponse(response)

        if productISOBuildObj and testwareISOBuildObj:
            try:
                producttestwareObj,created = ProductTestwareMediaMapping.objects.get_or_create(productIsoVersion=productISOBuildObj,testwareIsoVersion=testwareISOBuildObj)
                if created is False:
                    creationInfo = ("Info: Product ISO Media Build: '" +str(productISOBuildObj) + "' with Testware ISO Build: '" + str(testwareISOBuildObj) + "', already existed in  database so no database mapping update was made.\n")
            except Exception as error:
                response = ("Error: There was an Issue creating Product ISO: '" + str(productISOBuildObj) + "' to Testware ISO: '" + str(testwareISOBuildObj) + "' Mapping, error thrown: " + str(error) + ", please investigate.\n")
                logger.error(response)
                return HttpResponse(response)
        else:
            response = ("Error: The system could not determine either the product ISO id or the testware ISO id, please try again.\n")
            logger.error(response)
            return response
        if creationInfo:
            return HttpResponse("Success: " + str(creationInfo))
        else:
            return HttpResponse("Success: Product ISO: '" +str(productISOBuildObj) + "', Mapped to testware: '" + str(testwareISOBuildObj) + "'.\n")

@csrf_exempt
def setDropStatus(request):
    '''
    The setDropStatus function is used only for the CI Product in conjunction with TAF testware
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        try:
            productName=request.POST.get('product')
            dropName=request.POST.get('drop')
            newStatus=request.POST.get('status')
            if str(productName) != "test":
                return HttpResponse("Error: This interface only updates the drop status for the CI Test Product")
            dropObj = Drop.objects.get(name=dropName, release__product__name=productName)
            newDropActivity = DropActivity.objects.create(drop=dropObj, action=newStatus, desc="TAF testing", user="etaftst", date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            dropObj.status = newStatus
            dropObj.save(force_update=True)
            rtnMsg = "Successfully set the drop status to " + str(newStatus) + " for drop " + str(dropName)
        except Exception as e:
            rtnMsg = "Issue setting the drop status in setDropStatus function"
            logger.error(rtnMsg + " " + str(e))
        return HttpResponse(rtnMsg)

@csrf_exempt
def getDropActivityHistory(request):
    '''
    The getDropActivityHistory function returns a JSON object with information on the open and closure activity for a specific drop
   '''
    if request.method == 'POST':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")
    if request.method == 'GET':
        rtnData = []
        try:
            dropName = request.GET.get('drop')
            productName = request.GET.get('product')
            pretty = request.GET.get('pretty')
            if pretty != None:
                if pretty.lower() == "false":
                    pretty = False
                elif pretty.lower() == "true":
                    pretty = True
            else:
                pretty = False
            dropObj = Drop.objects.get(name=dropName, release__product__name=productName)
            dropActivities = DropActivity.objects.filter(drop=dropObj).order_by('-id')
            for activity in dropActivities:
                loopData = [
                    {
                        "drop": activity.drop.name,
                        "action": activity.action,
                        "reason": activity.desc,
                        "user": activity.user,
                        "dateupdated": str(activity.date),
                    },
                    ]
                rtnData = rtnData + loopData
            if pretty:
                rtnData = json.dumps(rtnData, sort_keys=True, indent=4)
            else:
                rtnData = json.dumps(rtnData )
        except Exception as e:
            rtnMsg = "Issue getting back drop activity in getDropActivityHistory function"
            logger.error(rtnMsg + " " + str(e))
        return HttpResponse(rtnData, content_type="application/json")

@gzip_page
@csrf_exempt
def getPackagesInISO(request):
    '''
    This function returns a list of packages within an ISO.
    '''
    result = {"ERROR":""}
    iso = None
    isoError = json.dumps({"ERROR":"ERROR: Specified ISO Name and Version do not exist"})
    if request.method == 'POST':
        try:
            rawJson = request.body
            decodedJson = json.loads(rawJson)
        except Exception as error:
            isoError = json.dumps({"ERROR":"ERROR: Specified ISO Name and/or Version do not exist - " + str(error)})
            return HttpResponse(isoError, content_type="application/json", status=404)
        if "showTestware" in decodedJson:
            testwareContents = decodedJson["showTestware"]
        else:
            testwareContents=False
        if "pretty" in decodedJson:
            pretty = decodedJson["pretty"]
        else:
            pretty=False
        try:
            iso = ISObuild.objects.get(artifactId=decodedJson["isoName"], version=decodedJson["isoVersion"])
        except ISObuild.DoesNotExist:
            return HttpResponse(isoError, content_type="application/json", status=404)
        if iso != None:
            result = cireports.utils.getPackagesInISO(iso,testwareContents,False)

    elif request.method == "GET":
        isoName=request.GET.get('isoName')
        isoVersion=request.GET.get('isoVersion')
        showTestware=request.GET.get('showTestware',False)
        pretty=request.GET.get('pretty')
        useLocalNexus=request.GET.get('useLocalNexus', False)
        if isoName == None or isoName == ""  or isoVersion == None or isoVersion == "":
            return HttpResponse(isoError, content_type="application/json", status=404)
        try:
            iso = ISObuild.objects.get(artifactId=isoName, version=isoVersion)
        except ISObuild.DoesNotExist:
            return HttpResponse(isoError, content_type="application/json", status=404)
        result = cireports.utils.getPackagesInISO(iso,showTestware,useLocalNexus)
    else:
        result = json.dumps({"ERROR":"ERROR: This interface accepts HTTP POST and GET requests only."})
        return HttpResponse(result, content_type="application/json", status=404)
    if str(pretty).lower() == "true":
        result = json.dumps(result, sort_keys=True, indent=4)
    else:
        result = json.dumps(result)

    return HttpResponse(result, content_type="application/json")

@csrf_exempt
def setUserDetails(request):
    '''
    The setUserDetails function is used to set First Name, Last Name and email address into the database
    '''
    if request.method == 'GET':
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    if request.method == 'POST':
        try:
            userName=request.POST.get('signum')
            firstName=request.POST.get('first')
            lastName=request.POST.get('last')
            email=request.POST.get('email')
            user = User.objects.get(username=str(userName))
            user.first_name = firstName
            user.last_name = lastName
            user.email = email
            user.save(force_update=True)
            rtnMsg = "Successfully set the information for user " + str(userName)
        except Exception as e:
            rtnMsg = "Issue setting the user information in the setUserDetails function"
            logger.error(rtnMsg + " " + str(e))
        return HttpResponse(rtnMsg)

@gzip_page
def displayDeliveryQueue(request, product, drop, id=None, action=None):
    '''
    The displayDeliveryQueue function displays the shell of the delivery queue page, which later retrieves the items in the queue in json format
    '''
    try:
        tabItem = request.GET.get('section')
        if tabItem == None:
            tabItem ="queued"
    except:
        tabItem ="queued"

    popUpMessage = request.session.get('message')
    try:
        del request.session['message']
    except KeyError:
        pass
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        errMsg = "Error getting Delivery Queue Data: Product " + str(product) + " Does Not Exist."
        return render(request, "cireports/error.html",{ 'error': errMsg  } )
    if not Drop.objects.filter(name=drop, release__product__name=product).exists():
        errMsg = "Error getting Delivery Queue Data: Drop " + str(drop) + " Does Not Exist."
        return render(request, "cireports/error.html",{ 'error': errMsg  } )
    dropObj = Drop.objects.only('id').values('id').get(name=drop, release__product=product)
    pageHitCounter("DeliveryQueueDrop", dropObj['id'], str(request.user))
    timeNow = datetime.now()
    config = CIConfig()
    editPerms = True
    permsSummary = ""
    user = User.objects.get(username=str(request.user))
    accessGroup = config.get("CIFWK", "adminGroup")
    dropQuery = Drop.objects.only('id').filter(planned_release_date__lt=timeNow, id=dropObj['id'], release__product__id=product.id) | Drop.objects.only('id').filter(actual_release_date__lt=timeNow, id=dropObj['id'], release__product__id=product.id)
    frozen = 'False'
    dropid = dropObj['id']
    autoDeliveryDisabled = Drop.objects.only('stop_auto_delivery').values('stop_auto_delivery').filter(id=dropObj['id']).get()['stop_auto_delivery']
    mtgGuards = config.get("CIFWK", "mtgGuards")
    if len(dropQuery) != 0:
        frozen = Drop.objects.only('actual_release_date').get(release__product__id=product.id, id=dropObj['id']).actual_release_date
        permsSummary = "This Drop is Frozen: no Group can be created, delivered, obsoleted or restored."
    elif Drop.objects.filter(id=dropObj['id'], release__product__name=product, status = "closed").exists():
        editPerms = False
        permsSummary = "The status of this Drop has been set to Closed, no Groups can be created or delivered."
    else:
        if Drop.objects.filter(id=dropObj['id'], release__product__name=product, status = "limited").exists() and not user.groups.filter(name=mtgGuards).exists():
            permsSummary = "The status of this Drop has been set to Limited. Only Maintrack Guardians can create or deliver Groups."
    if user.groups.filter(name=accessGroup).exists():
        userPerms = True
    else:
        userPerms = False
    mtgPerms = False
    if user.groups.filter(name=mtgGuards).exists():
        mtgPerms = True
    return render(request, "cireports/deliveryQueue.html",
            {
                'product':product,
                'drop':drop,
                'dropid':dropid,
                'grpid':id,
                'editPerms':editPerms,
                'userPerms':userPerms,
                'permsSummary':permsSummary,
                'actionPerf':action,
                'frozen':frozen,
                'tabItem': tabItem,
                'mtgPerms': mtgPerms,
                'popUpMessage':popUpMessage,
                'autoDeliveryDisabled':autoDeliveryDisabled,
            })

@gzip_page
def displayDeliveryQueueJson(request, productName, drop):
    '''
    The displayDeliveryQueueJson function displays a list of artifacts that are queued to be delivered to a drop, in json format
    '''
    deliveryGroups = utils.getDeliveryQueueData(productName, drop)
    returnedObject = {
        'deliveryGroups': list(deliveryGroups)
    }

    return HttpResponse(json.dumps(returnedObject,cls=DjangoJSONEncoder), content_type="application/json")

def displayDeliveryQueueCsv(request, productName, drop):
    deliveryGroups = utils.getDeliveryQueueData(productName, drop)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=' + productName + '_' + drop + '_queue.csv'

    f = csv.writer(response)
    f.writerow(["Delivery Group","Status","ISO","Date Created","Date Delivered","Created by Team", "RA","Missing Dependencies","Artifact Count","Artifact(s)","Comment(s)","JIRA(s)"])
    for grp in deliveryGroups:
        status, dateCreated, dateDelivered, count, artifacts, comments, jiras, iso= utils.getDeliveryGroupCsvFieldsData(grp)

        f.writerow([grp['id'],
                    status,
                    iso,
                    dateCreated,
                    dateDelivered,
                    grp['component__element'],
                    grp['component__parent__element'],
                    grp['missingDependencies'],
                    count,
                    artifacts,
                    comments,
                    jiras])
    return response

@login_required
def updateDeliveryGroup(request, product, drop, groupId, status):
    '''
    The updateDeliveryGroup function sets the deleted status of the group to either true or false
    '''
    user = User.objects.get(username=str(request.user))
    deliveryGroupObj = DeliveryGroup.objects.get(id=groupId)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        groupComment = None
        if str(status) == "True":
            deliveryGroupObj.deleted = True
            deliveryGroupObj.modifiedDate = now
            groupComment = str(user.first_name) + " "  + str(user.last_name) + " deleted this delivery group"
            newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=groupComment, date=now)
            confidencedLevel = "delete"
        elif str(status) == "False":
            groupComment = str(user.first_name) + " "  + str(user.last_name) + " returned this delivery group to the queue"
            newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=groupComment, date=now)
            deliveryGroupObj.deleted = False
            confidencedLevel = "restore"
        else:
            groupComment = str(user.first_name) + " "  + str(user.last_name) + " returned this delivery group to the queue"
            newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=groupComment, date=now)
            deliveryGroupObj.obsoleted = False
            confidencedLevel = "restore"
        deliveryGroupObj.warning = False
        deliveryGroupObj.save(force_update=True)
        cireports.utils.sendDeliveryGroupMessage(deliveryGroupObj,confidencedLevel)
        utils.sendDeliveryGroupUpdatedEmail(user, groupId, groupComment)
        logger.debug("Successfully set the deleted/restore flag to " +str(status) + " for Delivery Group " + str(groupId))
    except Exception as e:
        logger.error("Error setting the deleted/restore flag to " +str(status) + " for Delivery Group " + str(groupId) + str(e))
        deliveryGroupObj.warning = True
        deliveryGroupObj.save(force_update=True)
        deliveredComment = str(user.first_name) + " "  + str(user.last_name) + " could not update this group, due to Error detected: " + str(e)
        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/")
    if str(status) == "True":
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/?section=deleted")
    else:
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/")

@login_required
@csrf_exempt
def setMissingDependenciesOnDeliveryGroup(request, product, drop, groupId):
    '''
    The missingDependenciesDeliveryGroup function sets the group to missingDependencies and can not be delivered
    '''
    user = User.objects.get(username=str(request.user))
    try:
        value = "missingDeps_"+groupId
        missingDeps=request.POST.get(str(value))
        missingDepResult = cireports.utils.setMissingDependencies(user, product, drop, groupId, missingDeps)
        if missingDepResult == False:
           delPkgRevMaps =  DeliverytoPackageRevMapping.objects.only('packageRevision__package__testware','packageRevision__package__name').values('packageRevision__package__testware','packageRevision__package__name').filter(deliveryGroup__id=groupId)
           packageFound = 0
           for delPkgRevMap in delPkgRevMaps:
               if TestwareArtifact.objects.filter(name=delPkgRevMap['packageRevision__package__name'],includedInPriorityTestSuite=True).exists():
                   packageFound = 1
                   break
               elif delPkgRevMap['packageRevision__package__testware'] != True:
                   packageFound = 1
                   break
           if packageFound == 0:
              delivery_thread = DGThread(cireports.utils.performGroupDeliveries, args=(product, drop, groupId, user))
              delivery_thread.start()
              delivery_thread.join()
              deliveryFault, deliverySummary, fullList = delivery_thread.get_result()
              if deliveryFault:
                 logger.error("Error delivering group " + str(groupId) + str(e))
                 return render(request, "cireports/groupSummary.html",{
                     'error': True,
                     'details': deliverySummary,
                     'info':fullList,
                     'drop': drop,
                     'product': product,
                     })
              return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/success/?section=delivered")
    except Exception as e:
        logger.error("Error setting Missing Dependencies Flag: " + str(e))
    deliveryGroup = DeliveryGroup.objects.get(id=groupId)
    cireports.utils.sendDeliveryGroupMessage(deliveryGroup,"modify")
    return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/")


@login_required
@csrf_exempt
def setCCBapprovedOnDeliveryGroup(request, product, drop, groupId):
    '''
    This setCCBapprovedOnDeliveryGroup function sets the group to have CCB Approved Flag
    '''
    user = User.objects.get(username=str(request.user))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    groupComment = None
    try:
        value = "ccbApproved_"+groupId
        deliveryGroupObj = DeliveryGroup.objects.get(id=groupId)
        ccbApproved=request.POST.get(str(value))
        if not str(ccbApproved) == "None":
            deliveryGroupObj.ccbApproved = True
            groupComment = str(user.first_name) + " "  + str(user.last_name) + " set this delivery group as CCB Approved"
        else:
            deliveryGroupObj.ccbApproved = False
            groupComment = str(user.first_name) + " "  + str(user.last_name) + " removed the CCB Approved Flag from this delivery group"
        deliveryGroupObj.save(force_update=True)
        newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=groupComment, date=now)
        cireports.utils.sendDeliveryGroupUpdatedEmail(user, str(groupId), groupComment)
    except Exception as e:
        logger.error("Error setting CCB Approved Flag: " + str(e))
    return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/")

@login_required
def deleteDeliveryGroupItem(request, product, drop, dprmId):
    '''
    The deleteDeliveryGroupItem function deletes an artifact from the Delivery Group
    '''
    user = User.objects.get(username=str(request.user))
    delToPkgRevMapObj = None
    try:
        delToPkgRevMapObj = DeliverytoPackageRevMapping.objects.get(id=dprmId)
    except Exception as e:
        logger.error("Error deleting DeliverytoPackageRevMapping " + str(dprmId) + str(e))
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    deliveryGroup = delToPkgRevMapObj.deliveryGroup
    if deliveryGroup.delivered:
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(deliveryGroup.id)+"/?section=delivered")
    elif deliveryGroup.obsoleted:
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(deliveryGroup.id)+"/?section=obsoleted")
    elif deliveryGroup.deleted:
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(deliveryGroup.id)+"/?section=deleted")
    try:
        deleteComment = str(user.first_name) + " "  + str(user.last_name) + " removed " + str(delToPkgRevMapObj.packageRevision.package.name) + " from the group"
        newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=deleteComment, date=now)
        delToPkgRevMapObj.delete()
        packageList = DeliverytoPackageRevMapping.objects.filter(deliveryGroup_id=deliveryGroup.id)
        for pkg in packageList:
            if pkg.newArtifact == True:
                deliveryGroup.newArtifact = True
                break
            else:
                deliveryGroup.newArtifact = False
        deliveryGroup.save()
        cireports.utils.sendDeliveryGroupMessage(deliveryGroup,"modify")
        utils.sendDeliveryGroupUpdatedEmail(user, str(deliveryGroup.id), deleteComment)
        logger.debug("Successfully deleted DeliverytoPackageRevMapping " + str(dprmId))
    except Exception as e:
        logger.error("Error deleting DeliverytoPackageRevMapping " + str(dprmId) + str(e))
    return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(deliveryGroup.id)+"/")


@login_required
def makeDeliveryQueue(request, product):
    '''
    This view generates the pages to add or edit a delivery group
    '''
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        product = "None"
    groupId = request.GET.get('groupid')
    package = request.GET.get('package')
    version = request.GET.get('version')
    if groupId is None or not groupId or groupId == "None":
        if package is None or not package or package == "None":
            return render(request, "cireports/multipleDelivery.html",
                    {
                        "product":product,
                        "edit":0,
                    })
        else:
            return render(request, "cireports/multipleDelivery.html",
                    {
                        "product":product,
                        "groupInfo":json.dumps({"groupId":"",
                        "dropName":"",
                        "packageRevisions":[{"name":package,"version":version}],
                        "canEdit": 1
                        }),
                        "edit":0,
                    })

    else:
        try:
            groupInfo = cireports.utils.getGroupDetails(groupId)
            if groupInfo['delivered'] or groupInfo['deleted'] or groupInfo['obsoleted']:
                groupInfo["canEdit"] = 0
            else:
                groupInfo["canEdit"] = 1
        except:
            raise Http404
        return render(request, "cireports/multipleDelivery.html",
            {
                "product":product,
                "groupInfo": json.dumps(groupInfo),
                "edit":1,
            })

@login_required
def displayCNDeliveryGroupCreation(request, product, drop):
    '''
    This view generates the pages to add a cn delivery group
    '''
    errorMsg = None
    checkErrorMsg = None
    try:
        # check user permission
        permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(str(request.user))
        if permissionCheckStatus == 1 or permissionCheckErrorMsg:
            errorMsg = permissionCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
    except Exception as e:
        errorMsg = "Failed to display CN Delivery Group creation Page. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })
    return render(request, "cireports/cnDeliveryQueue_createDeliveryGroup.html", {
        "drop": drop,
        "product": product
    })


def getActiveDropsInProduct(request):
    '''
    returns a list of drops for which a user can manipulate the Delivery Queue for a product in Json format
    '''
    productName = request.GET.get('product')
    timeNow = datetime.now()
    user = User.objects.get(username=str(request.user))
    mtgGuards = config.get("CIFWK", "mtgGuards")
    dropsQuery = Drop.objects.only('name').filter(planned_release_date__gt=timeNow, release__product__name=productName).order_by('name') | Drop.objects.only('name').filter(actual_release_date__gt=timeNow, release__product__name=productName).order_by('name')
    latestFrozenDrops = None
    try:
        latestFrozenDrops = Drop.objects.only('name', 'actual_release_date').filter(release__product__name=productName).order_by('-id')[:3]
    except:
        if Drop.objects.filter(release__product__name=productName).exists():
            latestFrozenDrops = Drop.objects.only('name', 'actual_release_date').filter(release__product__name=productName).order_by('-id')[0]
        latestFrozenDrops = None
    drops =[]
    for drop in dropsQuery:
        if "open" in drop.status or "limited" in drop.status:
            drops.insert(0, productName +":"+drop.name)
        elif "closed" in drop.status:
            drops.insert(0, "Closed - " + productName +":"+drop.name +", do not have permission to create or deliver groups.")
    if not drops:
        frozenDropInfo = "All " + productName + " Drops are Frozen, you can not create or deliver groups. \n"
        if latestFrozenDrops != None:
            if len(latestFrozenDrops) == 3:
                frozenDropInfo = frozenDropInfo  + "The latest 3 Frozen Drops: \n"
            drpInfo = ""
            for drp in latestFrozenDrops:
                drpInfo = drpInfo + str(drp.name) + " was Frozen on: " +  str(drp.actual_release_date) + "\n"
            frozenDropInfo = frozenDropInfo  + drpInfo
        drops.append(frozenDropInfo)
    dropsJson = {"Drops":drops}
    result = json.dumps(dropsJson)
    return HttpResponse(result, content_type="application/json")


def getAllRevisionsOfAPackage(request):
    '''
    This function retrieves a list of all version numbers of a package
    '''
    package = request.GET.get('package')
    data = {'revisions':[]}
    data['revisions'] = cireports.utils.getAllRevisonsOfAPackage(package)
    result = json.dumps(data)
    return HttpResponse(result, content_type="application/json")

@login_required
@csrf_exempt
def addDeliveryGroup(request):
    '''
    This function posts data generated by ENM multiple deliveries to the database
    '''
    testwareGrpId = None
    user = User.objects.get(username=str(request.user))
    if str(user.first_name) == "" or str(user.last_name) == "" or str(user.email) == "":
        errMsg = "Issue with getting User Information for signum: " + str(request.user)
        logger.error(str(errMsg))
        return HttpResponse(json.dumps([{"error":str(errMsg) + ", please try again later."}]), content_type="application/json")
    result = {"ERROR":""}
    config = CIConfig()
    jiraUrl = config.get('CIFWK', 'jiraUrl')
    if request.method == 'POST':
        rawJson = request.body
        decodedJson = json.loads(rawJson)
        packageRevs = []
        teamsPkgRevs = []
        jiraIssues = []
        impactedCnDgs = []
        for item in decodedJson['items']:
            if 'packageName' in item:
                try:
                    packageRevObj = PackageRevision.objects.get(package__name=item['packageName'], version=item['version'])
                    if packageRevObj not in packageRevs:
                        packageRevs.append(packageRevObj)
                        teamsPkgRevs.append(item['pkgTeams'])
                except Exception as e:
                    logger.error("PackageRevision: " + str(item) + " is not contained within the CI Database")
                    return HttpResponse(json.dumps([{"error":str("This package revision does not exist. Name: "+str(item['packageName'])+" Version:"+str(item['version']))}]), content_type="application/json")
        for item in decodedJson['jiraIssues']:
            if 'issue' in item:
                try:
                    jira = str(item['issue']).replace(str(jiraUrl), "")
                    jira = str(jira).replace(" ", "")
                    jiraNumber = str(jira).replace("/", "")
                    jiraIssues.append(jiraNumber)
                except Exception as e:
                    logger.error("Issue with getting Jira Issues from Form")
                    return HttpResponse(json.dumps([{"error":str("Issue with getting Jira Issues from Form: "+str(item['issue']))}]), content_type="application/json")
        comment = decodedJson['comment']
        groupID = decodedJson['groupId']
        missingDep = decodedJson['missingDep']
        warning = decodedJson['warning']
        product, drop = decodedJson['drop'].split(':')
        team = decodedJson['team']
        impactedCnDgs = decodedJson['cenmDgList']
        kgb_published_reason = decodedJson['kgb_published_reason']
        if groupID is None or not groupID or groupID == "":
            result, testwareGrpId = cireports.utils.addDeliveryGroup(user, packageRevs, comment, product, drop, team, teamsPkgRevs, impactedCnDgs, jiraIssues, missingDep, warning, None, kgb_published_reason)
        else:
            result, testwareGrpId = cireports.utils.editDeliveryGroup(user, packageRevs, comment, product, drop, groupID, teamsPkgRevs, impactedCnDgs, jiraIssues, missingDep, warning, kgb_published_reason)
        if testwareGrpId != None and not missingDep:
            delivery_thread = DGThread(cireports.utils.performGroupDeliveries, args=(product, drop, testwareGrpId, user))
            delivery_thread.start()
            delivery_thread.join()
            deliveryFault, deliverySummary, fullList = delivery_thread.get_result()
            if deliveryFault:
                if groupID is None or not groupID or groupID == "":
                    result = "Group was created but not delivered, due to " +  deliverySummary + " "  + str(fullList)
                else:
                    result = "Group was updated but not delivered, due to " +  deliverySummary + " "  + str(fullList)
        else:
            testwareGrpId = None
    else:
        testwareGrpId = None
        result = "This interface accepts HTTP POST requests only."
    return HttpResponse(json.dumps([{"error":str(result), "testwareGrpId": str(testwareGrpId)}]), content_type="application/json")

@login_required
def makeGroupDeliveries(request, product, drop, groupId):
    '''
    The makeGroupDeliveries function loops throught the artifacts associated in a group and delivers them the the drop specified
    '''
    user = User.objects.get(username=str(request.user))
    deliverySummary = ""
    fullList = []
    deliveryFault = False
    mtgGuards = config.get("CIFWK", "mtgGuards")
    accessGroup = config.get("CIFWK", "adminGroup")
    returnErrorValues = { 'error': True, 'drop': drop, 'product': product, 'info':fullList, 'details':deliverySummary}
    if not (user.groups.filter(name=mtgGuards).exists() or user.groups.filter(name=accessGroup).exists()):
        returnErrorValues['details'] = "Error delivering group " + str(groupId) + ". You do not have permission to deliver groups."
        return render(request, "cireports/groupSummary.html", returnErrorValues)
    try:
        delivery_thread = DGThread(cireports.utils.performGroupDeliveries, args=(product, drop, groupId, user))
        delivery_thread.start()
        delivery_thread.join()
        deliveryFault, deliverySummary, fullList = delivery_thread.get_result()
        if deliveryFault:
            returnErrorValues['details'] = deliverySummary
            returnErrorValues['info'] = fullList
            return render(request, "cireports/groupSummary.html", returnErrorValues)
    except Exception as e:
        logger.error("Error delivering group " + str(groupId) + str(e))
        return render(request, "cireports/groupSummary.html", returnErrorValues)
    groupDeliveredComment = str(user.first_name) + " "  + str(user.last_name) + " delivered this group"
    utils.sendDeliveryGroupUpdatedEmail(user, groupId, groupDeliveredComment)
    return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/success/?section=delivered")

@login_required
def obsoleteGroupDeliveries(request, product, drop, groupId):
    '''
    The obsoleteGroupDeliveries function loops through the artifacts in a delivery group and obsoletes them
    '''
    user = User.objects.get(username=str(request.user))
    deliveryGroupObj = None
    mtgGuards = config.get("CIFWK", "mtgGuards")
    accessGroup = config.get("CIFWK", "adminGroup")
    returnErrorValues = { 'error': True, 'drop': drop, 'product': product}
    errorMsg = None
    if not (user.groups.filter(name=mtgGuards).exists() or user.groups.filter(name=accessGroup).exists()):
        returnErrorValues['details'] = "ERROR obsoleting group " + str(groupId) + ". You do not have permission to obsolete groups."
        return render(request, "cireports/groupSummary.html", returnErrorValues)
    obsolete_thread = DGThread(cireports.utils.obsoleteDeliveryGroup_UI, args=(request, product, drop, groupId, user, returnErrorValues))
    obsolete_thread.start()
    obsolete_thread.join()
    errorMsg, returnErrorValues = obsolete_thread.get_result()
    if errorMsg != None:
        return render(request, "cireports/groupSummary.html", returnErrorValues)
    else:
        return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/obsoleted/?section=obsoleted")

@csrf_exempt
@gzip_page
def getCENMISODiff(request):
    '''
    showing the main page of cenm diff
    '''
    return render(request, "cireports/cenm_iso_diff.html",
            {
                'product': "CENM"
            })

@csrf_exempt
@gzip_page
def getCENMISODiffResult(request):
    '''
    showing the result content of cenm diff
    '''
    try:
        cenmDiff = None
        currentPS = request.GET.get('current',None)
        previousPS = request.GET.get('previous',None)
        drop = request.GET.get('drop',None)
        preDrop = request.GET.get('preDrop',None)
        if LooseVersion(str(preDrop)) > LooseVersion(str(drop)):
            errormsg = 'Previous drop must be less than current drop!'
            return render(request, "cireports/isodelta_error.html",{'error': errormsg})
        if LooseVersion(str(previousPS)) > LooseVersion(str(currentPS)) or LooseVersion(str(previousPS)) == LooseVersion(str(currentPS)):
            errormsg = 'Previous product set version must be less than current product set version!'
            return render(request, "cireports/isodelta_error.html",{'error': errormsg})
        cenmDiff, errorMsg = cireports.utils.getCENMDiff(str(currentPS), str(previousPS))
        if errorMsg:
            return render(request, "cireports/isodelta_error.html",{'error': errorMsg})
        return render(request, "cireports/cenm_iso_diff_results.html",
            {
                'product': "CENM",
                'drop': drop,
                'preDrop': preDrop,
                'currentPS': currentPS,
                'previousPS': previousPS,
                'csarChanges': cenmDiff['csarChanges'],
                'integrationChartChanges': cenmDiff['integrationChartChanges'],
                'cnImageChanges': cenmDiff['cnImageChanges']
            })
    except Exception as e:
        logger.error(str(e))
        return render(request, "cireports/isodelta_error.html",{'error': "failed to get cenm iso diff" + str(e)})

@csrf_exempt
@gzip_page
def getISODelta(request, bom):

    '''The getISODelta function is a REST Service which return a JSON object of Artifact Differences between two given ISO
    versions on a given drop, this is acheived by calling the cireports.utils.returnISOVersionArtifactDelta function which returns the object.

    externalCall :: Used to indicate when the request is coming from The Maintrack Radiator'''

    obsoleted = None
    added = None
    updated = None
    deliveryGroup = None
    externalCall = request.GET.get('externalCall',None)
    currentISO = request.GET.get('current',None)
    previousISO = request.GET.get('previous',None)
    product = request.GET.get('product',None)
    drop = request.GET.get('drop',None)
    previousDrop = request.GET.get('preDrop',None)
    if request.method == "GET" and not externalCall:
        if bom:
            pageName = "BOM-DiffTool"
        else:
            pageName = "ISO-DiffTool"
        pageHitCounter(pageName, None, str(request.user))
        return render(request, "cireports/isodelta.html",
            {
                'preDrop': previousDrop,
                'previousIsoVer': previousISO,
                'isoVersion': currentISO,
                'product': product,
                'drop': drop,
                'bom' : bom
            })
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        return render(request, "cireports/isodelta_error.html",{'error': 'Invalid product'})
    if request.method == 'POST' or request.method == "GET":
        if currentISO:
            isoVersion = currentISO
            previousIsoVer = previousISO
        else:
            isoVersion = request.POST.get('isoVersion')
            previousIsoVer = request.POST.get('previousIsoVer')

        if product is None or not product or product == "None":
            return render(request, "cireports/isodelta_error.html",{'error': 'Product name required, please try again'})
        if drop is None or not drop or drop == "None":
            return render(request, "cireports/isodelta_error.html",{'error': 'Drop name required, please try again'})
        if isoVersion is None or not isoVersion or isoVersion == "None":
            if bom:
                errormsg = 'BOM Version required, please try again'
            else:
                errormsg = 'ISO Version required, please try again'
            return render(request, "cireports/isodelta_error.html",{'error': errormsg})
        if previousIsoVer is None or not previousIsoVer or previousIsoVer == "None":
            if bom:
                errormsg = 'Previous BOM Version required, please try again'
                return render(request, "cireports/isodelta_error.html",{'error': errormsg})
        if previousIsoVer:
            if previousIsoVer == isoVersion or LooseVersion(str(previousIsoVer)) > LooseVersion(str(isoVersion)):
                if bom:
                    errormsg = 'Previous BOM version needs to be less than the BOM Version, please try again'
                else:
                    errormsg = 'Previous ISO version needs to be less than the ISO Version, please try again'
                return render(request, "cireports/isodelta_error.html",{'error': errormsg})

        try:
            response, ISODeltaDict, previousIsoVer, previousDrop = cireports.utils.returnISOVersionArtifactDelta(product,drop,isoVersion,previousIsoVer,previousDrop,True)

            if ISODeltaDict == {}:
                return render(request, "cireports/isodelta_error.html",{'error':response})
            data = json.loads(response)
            if "Obsoleted" in str(data):
                obsoleted = "true"
            if "Updated" in str(data):
                updated = "true"
            if "Added" in str(data):
                added = "true"
            if "DeliveryGroup" in str(data):
                deliveryGroup = "true"
        except Exception as e:
            if bom:
                errorMsg = "There was an issue comparing bom artifact versions: " + str(e)
            else:
                errorMsg = "There was an issue comparing iso artifact versions: " + str(e)
            logger.error(errorMsg)
            return render(request, "cireports/isodelta_error.html",{'error':errorMsg})

    return render(request, "cireports/iso_delta_results.html",
            {
                'drop': drop,
                'product': product,
                'femObj': femObj,
                'isoVersion': isoVersion,
                'previousIsoVer': previousIsoVer,
                'previousDrop': previousDrop,
                'added':added,
                'updated':updated,
                'obsoleted': obsoleted,
                'deliveryGroup':deliveryGroup,
                'response': data,
                'bom' : bom
            })

@csrf_exempt
@gzip_page
def getISODeltaInDrop(request, product, drop, bom):
    '''
    The getISODeltaInDrop function is a REST Service which return a JSON object of Artifact Differences between two given ISO
    versions on a given drop, this is acheived by calling the cireports.utils.returnISOVersionArtifactDelta function which returns the object.
    '''
    dropObj = None
    obsoleted = None
    added = None
    updated = None
    deliveryGroup = None
    currentISO = request.GET.get('current',None)
    previousISO = request.GET.get('previous',None)
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        return render(request, "cireports/isodelta_error_indrop.html",{'error': 'Invalid product'})
    fh = FormHandle()
    if bom:
        fh.title = "List of Product BOM Versions for Drop"
        fh.message = "Select Two BOM versions to Compare"
        pageName = "DropBOM-DiffTool"
    else:
        fh.title = "List of Product ISO Versions for Drop"
        fh.message = "Select Two ISO versions to Compare"
        pageName = "DropISO-DiffTool"
    try:
        dropObj = Drop.objects.only('id').values('id').get(release__product=product, name=drop)
    except Exception as e:
        errMsg = 'Drop required, please try again - ' + str(e)
        return render(request, "cireports/error.html",{'error': errMsg})
    pageHitCounter(pageName, dropObj['id'], str(request.user))
    fh.docLink = "/pages/viewpage.action?pageId=110792110"
    fh.request = request
    fh.form = IsoDeltaForm(product.name, drop, bom)
    if request.method == "GET" and not currentISO:
        return fh.display()

    if request.method == 'POST' or request.method == "GET":
        if currentISO:
            isoVersion = currentISO
            previousIsoVer = previousISO
        else:
            isoVersion = request.POST.get('isoVersion')
            previousIsoVer = request.POST.get('previousIsoVer')

        if product is None or not product or product == "None":
            return render(request, "cireports/error.html",{'error': 'Product name required, please try again'})
        if drop is None or not drop or drop == "None":
            return render(request, "cireports/error.html",{'error': 'Drop name required, please try again'})
        if isoVersion is None or not isoVersion or isoVersion == "None":
            if bom:
                errormsg = 'BOM Version required, please try again'
            else:
                errormsg = 'ISO Version required, please try again'
            return render(request, "cireports/error.html",{'error': errormsg})
        if previousIsoVer is None or not previousIsoVer or previousIsoVer == "None":
            if bom:
                errormsg = 'Previous BOM Version required, please try again'
                return render(request, "cireports/error.html",{'error': errormsg})
        if previousIsoVer:
            if previousIsoVer == isoVersion or LooseVersion(str(previousIsoVer)) > LooseVersion(str(isoVersion)):
                if bom:
                    errormsg = 'Previous BOM version needs to be less than the BOM Version, please try again'
                else:
                    errormsg = 'Previous ISO version needs to be less than the ISO Version, please try again'
                return render(request, "cireports/error.html",{'error': errormsg})

        try:
            response, ISODeltaDict, previousIsoVer, notNeeded = cireports.utils.returnISOVersionArtifactDelta(product,drop,isoVersion,previousIsoVer)
            if ISODeltaDict == {}:
                return render(request, "cireports/error.html",{'error':response})
            data = json.loads(response)
            if "Obsoleted" in str(data):
                obsoleted = "true"
            if "Updated" in str(data):
                updated = "true"
            if "Added" in str(data):
                added = "true"
            if "DeliveryGroup" in str(data):
                deliveryGroup = "true"
        except Exception as e:
            if bom:
                errorMsg = "There was an issue comparing bom artifact versions: " + str(e)
            else:
                errorMsg = "There was an issue comparing iso artifact versions: " + str(e)
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error':errorMsg})
    return render(request, "cireports/isodelta_indrop.html",
            {
                'drop': drop,
                'product': product,
                'femObj': femObj,
                'isoVersion': isoVersion,
                'previousIsoVer': previousIsoVer,
                'added':added,
                'updated':updated,
                'obsoleted': obsoleted,
                'deliveryGroup':deliveryGroup,
                'response': data,
                'bom' : bom
            })


@login_required
def addDeliveryGroupComment(request, product, drop, groupId, state):
    '''
    The addDeliveryGroupComment function is used to add comments to an existing Delivery Group
    '''
    user = User.objects.get(username=str(request.user))
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        product = "None"
        femObj = "None"
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        deliveryGroupObj = DeliveryGroup.objects.get(id=groupId)
        comments = DeliveryGroupComment.objects.filter(deliveryGroup=deliveryGroupObj)
        if request.method == 'POST':
            comment = request.POST.get("comment")
            updatedComment = str(user.first_name) + " "  + str(user.last_name) + ": " + smart_str(comment)
            newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=updatedComment, date=now)
            utils.sendDeliveryGroupUpdatedEmail(user, groupId, "Comment Added: "+ smart_str(comment))
            return HttpResponseRedirect("/"+str(product)+"/queue/"+str(drop)+"/"+str(groupId)+"/?section="+str(state))
    except DeliveryGroup.DoesNotExist:
        logger.error("Error trying to add comment to Delivery Group Id: " + str(groupId))
        raise Http404
    return render(request, "cireports/deliveryGroupComments.html",
            {
                'drop': dropObj,
                'product': product,
                'femObj': femObj,
                'comments': comments,
            })


@login_required
def addDeliveryGroupJira(request, product, drop, groupId, state):
    '''
    The addDeliveryGroupJira function is used to add jiras to an existing Delivery Group
    '''
    user = User.objects.get(username=str(request.user))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    errorStatus = False
    issueTypeMsg = ""
    config = CIConfig()
    jiraUrl = config.get('CIFWK', 'jiraUrl')
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
    else:
        product = "None"

    try:
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        deliveryGroupObj = DeliveryGroup.objects.get(id=groupId)
        jiras = JiraDeliveryGroupMap.objects.filter(deliveryGroup=deliveryGroupObj)
        if request.method == 'POST':
            jira = request.POST.get("jira")
            submitAnother = request.POST.get("SubmitAnother")
            jira = str(jira).replace(jiraUrl, "")
            jiraNumber = str(jira).replace("/", "")
            issueTypeMsg, errorCode = utils.addJiraIssueToDeliveryGroup(deliveryGroupObj, jiraNumber)
            if errorCode == 0:
                newJira = str(user.first_name) + " " + str(user.last_name) + " added " + str(jiraNumber) + " to the group"
                utils.sendDeliveryGroupUpdatedEmail(user, groupId, newJira)
                DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=newJira, date=now)
            else:
                errorStatus = True
            if submitAnother == None and errorStatus != True:
                return HttpResponseRedirect("/"+str(product)+"/queue/"+str(dropObj.name)+"/"+str(deliveryGroupObj.id)+"/")
    except Exception as e:
        logger.error("Error trying to add jira to Delivery Group Id: " + str(groupId) + " - " + str(e))
        errorStatus = True
        issueTypeMsg = "Error trying to add jira to Delivery Group Id: " + str(groupId)
    return render(request, "cireports/deliveryGroupJiras.html",
            {
                'drop': dropObj,
                'product': product,
                'jiras': jiras,
                'group': groupId,
                'state': state,
                'jiraUrl': jiraUrl,
                'error': errorStatus,
                'errorMsg': issueTypeMsg,
            })

@login_required
def deleteDeliveryGroupJira(request, productName, dropName, jiraDeliveryMapId):
    '''
    The deleteDeliveryGroupItem function deletes an artifact from the Delivery Group
    '''
    user = User.objects.get(username=str(request.user))
    jiraMapping = JiraDeliveryGroupMap.objects.get(id=jiraDeliveryMapId)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        deliveryGroupId = jiraMapping.deliveryGroup.id
        deliveryGroupObj = jiraMapping.deliveryGroup
        deleteJira = str(user.first_name) + " " + str(user.last_name) + " removed " + str(jiraMapping.jiraIssue.jiraNumber) + " from the group"
        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deleteJira, date=now)
        jiraIssue = jiraMapping.jiraIssue
        jiraMapping.delete()
        utils.editDeliveryGroupForJiraType(deliveryGroupObj)
        if not JiraDeliveryGroupMap.objects.filter(jiraIssue=jiraIssue).exists():
            if LabelToJiraIssueMap.objects.filter(jiraIssue=jiraIssue).exists():
                for labelMap in LabelToJiraIssueMap.objects.filter(jiraIssue=jiraIssue):
                    labelMap.jiraLabel.delete()
                    labelMap.delete()
            jiraIssue.delete()
        utils.sendDeliveryGroupUpdatedEmail(user, str(deliveryGroupId), deleteJira)
        logger.debug("Successfully deleted JiraDeliveryGroupMap " + str(jiraDeliveryMapId))
    except Exception as e:
        logger.error("Error deleting JiraDeliveryGroupMap " + str(jiraDeliveryMapId) + str(e))
    return HttpResponseRedirect("/"+str(productName)+"/queue/"+str(dropName)+"/"+str(deliveryGroupId)+"/")


def getDropISODeliveryGroups(request, productName, dropName):
    '''
    getDropISODeliveryGroups returns the list of ISO builds in a drop with delivery groups in the ISOs
    '''
    try:
        product = Product.objects.get(name=productName)
        dropObj = Drop.objects.only('id').values('id').get(name=dropName, release__product=product)
        pageHitCounter("DropISODeliveryGroups", dropObj['id'], str(request.user))
    except Exception as error:
        errMsg = "Error getting Drop ISO Delivery Groups : Drop " + str(dropName) + " Does Not Exist. - " + str(error)
        return render(request, "cireports/error.html",{ 'error': errMsg  } )

    isoDelGrps = utils.getDropProductwareISODeliveryGroups(productName, dropObj)
    testIsoDelGrps = utils.getDropTestwareISODeliveryGroups(productName, dropObj)

    return render(request, "cireports/drop_iso_delivery_groups.html",
            {
                'product': product,
                'drop': dropName,
                'isoDelGrps': isoDelGrps,
                'testIsoDelGrps': testIsoDelGrps,
            })


def getProductSetDelta(request):
    '''
        The getProductSetDelta function is a REST Service which returns a JSON object of Artifact Differences between two given ProductSet
        versions on a given drop, this is acheived by calling the cireports.utils.returnPSVersionArtifactDelta function which returns the object.

        externalCall :: Used to indicate when the request is coming from The Maintrack Radiator
    '''

    obsoleted = None
    added = None
    updated = None
    productSetVersion = None
    previousPSVer = None
    externalCall = request.GET.get('externalCall',None)
    currentPS = request.GET.get('current',None)
    previousPS = request.GET.get('previous',None)
    product = request.GET.get('product',None)
    drop = request.GET.get('drop',None)
    jsonFormat = request.GET.get('json',None)
    previousDrop = request.GET.get('preDrop',None)
    if request.method == "GET" and not externalCall:
        pageHitCounter("ProductSet-Difftool", None, str(request.user))
        return render(request, "cireports/product_set_delta.html",
            {
                'productSetVersion': currentPS,
                'previousPS': previousPS,
                'product': product,
                'drop': drop,
            })
    if Product.objects.filter(name=product).exists():
        product = Product.objects.get(name=product)
        femObj = FEMLink.objects.filter(product=product)
    else:
        return render(request, "cireports/isodelta_error.html",{'error': 'Invalid product'})
    if request.method == 'POST' or request.method == "GET":
        if currentPS:
            productSetVersion = currentPS
            previousPSVer = previousPS
        if product is None or not product or product == "None":
            return render(request, "cireports/isodelta_error.html",{'error': 'Product name required, please try again'})
        if drop is None or not drop or drop == "None":
            return render(request, "cireports/isodelta_error.html",{'error': 'Drop name required, please try again'})
        if productSetVersion is None or not productSetVersion or productSetVersion == "None":
            errormsg = 'Product Set Version required, please try again'
            return render(request, "cireports/isodelta_error.html",{'error': errormsg})
        if previousPSVer:
            if previousPSVer == productSetVersion or LooseVersion(str(previousPSVer)) > LooseVersion(str(productSetVersion)):
                errormsg = 'Previous Product Set version needs to be less than the Product Set Version, please try again'
                return render(request, "cireports/isodelta_error.html",{'error': errormsg})

        try:
            response, deltaDict, previousPSVer, previousDrop = cireports.utils.returnPSVersionArtifactDelta(product,drop,productSetVersion,previousPSVer,previousDrop,True)

            if deltaDict == {}:
                return render(request, "cireports/isodelta_error.html",{'error':response})
            if jsonFormat:
                return HttpResponse(response, content_type="application/json")
            data = json.loads(response)
            if "Obsoleted" in str(data):
                obsoleted = "true"
            if "Updated" in str(data):
                updated = "true"
            if "Added" in str(data):
                added = "true"
        except Exception as e:
            errorMsg = "There was an issue comparing the Product Set versions: " + str(e)
            logger.error(errorMsg)
            return render(request, "cireports/isodelta_error.html",{'error':errorMsg})

    return render(request, "cireports/product_set_delta_results.html",
            {
                'drop': drop,
                'product': product,
                'femObj': femObj,
                'productSetVersion': productSetVersion,
                'previousPSVer': previousPSVer,
                'previousDrop': previousDrop,
                'added':added,
                'updated':updated,
                'obsoleted': obsoleted,
                'response': data,
                })


def updateAutoDeliveryStatus(request,drop_id):
    '''
    The updateAutoDeliveryStatus REST call updates the status if auto-delivery for a specific drop
    '''
    if request.method == 'PUT':
        data = json.loads(request.body)
        try:
            dropId = data['dropId']
        except Exception as e:
            logger.info('error in fetching put param data' + str(e))
        try:
            status = data['autoDeliveryStatus']
        except Exception as e:
            logger.info('error in fetching status from request' + str(e))
        try:
            drop = Drop.objects.filter(id=dropId).first()
            drop.stop_auto_delivery = status
            drop.save()
            return HttpResponse(json.dumps('success'), content_type="application/json")
        except Exception as e:
            logger.info('errro while updating db' + str(e))

def getCloudNativeProductSetContent(request, drop, product_set_version):
    '''
    The getCloudNativeIntegrationRevision function, that returns the Integration Revision of Cloud Native build based on the ENM Iso version.
    '''
    try:
        listOfIntegrationCharts = csarRevList = productSetVersion = cnProductSetVersionStatus = defaultProductSetVersion = deployUtilDetRev = None
        integrationValueFilesList = None
        defaultProductSetVersion = product_set_version
        productSetVersion, errorMsg = cireports.utils.handleRebuiltCNProductSetVersion(product_set_version)
        if errorMsg:
            logger.error(errorMsg)
        cnProductSetVersionStatus, errorMsg = cireports.utils.getCNConfidenceLevel(drop, product_set_version)
        if errorMsg:
            logger.error(errorMsg)
        listOfIntegrationCharts, errorMsg = cireports.utils.getLatestIntegrationCharts(drop, product_set_version)
        if errorMsg:
            logger.error(errorMsg)
        integrationValueFilesList, errorMsg = cireports.utils.getIntegrationValueFiles(product_set_version)
        if errorMsg:
            logger.error(errorMsg)
        csarRevList, errorMsg = cireports.utils.getLatestCSAR(drop, product_set_version)
        if errorMsg:
            logger.error(errorMsg)
        deployUtilsRev, errorMsg = cireports.utils.getDeploymentUtilities(product_set_version)
        if errorMsg:
            logger.error(errorMsg)
        deployUtilDetRev, errorMsg = cireports.utils.getDeploymentUtilityDetail(product_set_version)
        if errorMsg:
            logger.error(errorMsg)
    except Exception as e:
        status = "There was an issue with fetching the information from DB. Please Investigate! " + str(e)
        logger.error(status)
    return render(request, "cireports/cloudnative_productsetcontent.html",
        {
            'product_set_version': productSetVersion,
            'default_product_set_version': defaultProductSetVersion,
            'csarRevList': csarRevList,
            'deployUtilsRev': deployUtilsRev,
            'deployUtilDetRev': deployUtilDetRev,
            'listOfIntegrationCharts': listOfIntegrationCharts,
            'integrationValueFilesList': integrationValueFilesList,
            'cnProductSetStatus': cnProductSetVersionStatus,
            'drop': drop
        })

def getCloudNativeHelmRevision(request, productSetVersion,integration_name, integration_version):
    '''
    The getCloudNativeHelmRevision function, that return the Image Revision of Cloud Native build based on the ENM Iso version.
    '''
    listOfHelmImageMaps = []
    listOfHelmIntegrationMaps = CNHelmChartProductMapping.objects.filter(product_revision__product_set_version__product_set_version = productSetVersion, product_revision__product__product_name = integration_name, product_revision__version = integration_version).all()
    for int_rev in listOfHelmIntegrationMaps:
        listOfHelmImageMaps += CNImageHelmChartMapping.objects.filter(helm_chart_revision = int_rev.helm_chart_revision).all()
    return render(request, "cireports/cloudnative_helmrevision.html",
        {
            "integration_version": integration_version,
            "integration_name": integration_name,
            "listOfHelmIntegrationMaps": listOfHelmIntegrationMaps,
            "listOfHelmImageMaps": listOfHelmImageMaps
        })

def getCloudNativeImageContent(request, image_name, image_version):
    '''
    The getCloudNativeImageContent function, that returns the content of Cloud Native Image and renders in HTML page.
    '''
    try:
        imageRevObj = listOfPackages = None
        imageRevObj = CNImageRevision.objects.get(image__image_name = image_name, version = image_version)
        listOfPackages = cireports.utils.getCNImageContentWithLatestRpms(imageRevObj)
    except Exception as e:
        status = "There was an issue with fetching the information from DB when gettin cloud native image contents. Please Investigate! " + str(e)
        logger.error(status)
        return render(request, "cireports/cloudnative_error.html",
            {
                'error': status
            })
    return render(request, "cireports/cloudnative_imagecontent.html",
        {
            'imageContent': listOfPackages,
            'imageRevObj': imageRevObj
        })

def displayHistoricalCNProductSetVerions(request, prodSet, drop, productSetVersion):
    '''
    This function returns historical all the cloud native product set versions by a given base cn product set version
    and renders in HTML page.
    '''
    prodSetObj = None
    product = None
    prodSetRelObj = None
    dropObj = None
    activeCNPSVersions = None
    inactiveCNPSVersions = None
    enmPSVersion = None
    inactiveMedia = []
    try:
        prodSetObj = ProductSet.objects.get(name=prodSet)
        product = ProductSetRelease.objects.filter(productSet=prodSetObj)[0].release.product
        prodSetRelObj = ProductSetRelease.objects.filter(productSet=prodSetObj)[0]
        dropObj = Drop.objects.get(name=drop, release__product=product)
        enmPSVersion = ProductSetVersion.objects.get(version = productSetVersion, drop_id=dropObj.id,productSetRelease__release=dropObj.release)
        inactiveList = ProductSetVersionContent.objects.only('productSetVersion__id').values('productSetVersion__id').filter(productSetVersion__id=enmPSVersion.id, mediaArtifactVersion__active=0)
        inactiveMedia = []
        if inactiveList:
            for inactive in inactiveList:
                inactiveMedia.append(inactive['productSetVersion__id'])
        activeCNPSVersions,inactiveCNPSVersions, errorMsg = cireports.utils.getCNHistoricalProductSetVersions(productSetVersion)
        if errorMsg:
            logger.error(errorMsg)
    except Exception as e:
        status = "There was an issue with fetching the information from DB when getting cloud native historical product set versions. Please Investigate! " + str(e)
        logger.error(status)
        return render(request, "cireports/cloudnative_error.html",
            {
                'error': status
            }
        )
    return render(request, "cireports/cloudnative_historicalproductsetver.html",
        {
            'enmPSVersion': enmPSVersion,
            'activeCNPSVersions': activeCNPSVersions,
            'inactiveCNPSVersions': inactiveCNPSVersions,
            'dropName': drop,
            'productSet': prodSet,
            'inactiveMedia': inactiveMedia
        })

@login_required
def displayCNDeliveryQueue(request, product, drop, dgNumber=None):
    '''
    The displayCNDeliveryQueue function displays the shell of the cn delivery queue page, which later retrieves the items in the queue in json format
    '''
    user = None
    tabItem = None
    cnDropCheckStatus = None
    cnDropObj = None
    cnDropErrorMsg = None
    userPerms = None
    userPermsErrorMsg = None
    adminPerms = None
    adminPermsErrorMsg = None
    errorMsg = None
    try:
        try:
            tabItem = request.GET.get('section')
            if tabItem == None:
                tabItem ="queued"
        except:
            tabItem ="queued"
        cnDropCheckStatus, cnDropObj, cnDropErrorMsg = cireports.utils.checkCNDrop(product, drop)
        if cnDropCheckStatus == 1 or cnDropErrorMsg != None:
            errorMsg = cnDropErrorMsg
            return render(request, "cireports/error.html",{'error': errMsg })
        user = User.objects.get(username=str(request.user))
        adminPerms, adminPermsErrorMsg = cireports.utils.checkCNDeliveryQueueAdminPerms(user)
        return render(request, "cireports/cnDeliveryQueue_deliveryQueue.html", {
            'product': product,
            'drop': drop,
            'deliveryGroupId': dgNumber,
            'userPerms': userPerms,
            'adminPerms': adminPerms,
            'cnDropStatus': cnDropCheckStatus,
            'cnDropObj': cnDropObj,
            'tabItem': tabItem
        })
    except Exception as e:
        errorMsg = "Failed to render cn delivery queue page. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })

@login_required
def editDeliveryGroup(request, deliveryGroupNumber):
    '''
    The editDeliveryGroup function displays the page for editing delivery group info for a given cn delivery group number
    '''
    errorMsg = None
    try:
        # check user permission
        permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(str(request.user))
        if permissionCheckErrorMsg:
            errorMsg = permissionCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        # check if drop is open
        dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
        if dropCheckErrorMsg:
            errorMsg = dropCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to display the page for editing delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })
    return render(request, "cireports/cnDeliveryQueue_editDeliveryGroup.html", {
        'deliveryGroupNumber': deliveryGroupNumber
    })

@login_required
def editJira(request, deliveryGroupNumber):
    '''
    The editJira function displays the page for editing jira ticket info for a given cn delivery group number
    '''
    errorMsg = None
    try:
        # check user permission
        permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(str(request.user))
        if permissionCheckErrorMsg:
            errorMsg = permissionCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        # check if drop is open
        dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
        if dropCheckErrorMsg:
            errorMsg = dropCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        return render(request, "cireports/cnDeliveryQueue_editJira.html", {
            'deliveryGroupNumber': deliveryGroupNumber
        })
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to display the page for editing jira tickets. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })

@login_required
def addCNDeliveryGroupComment(request, product, drop, deliveryGroupNumber, deliveryGroupState):
    '''
    The addCNDeliveryGroupComment function displays the page while editing a devliery group comment.
    '''
    errorMsg = None
    try:
        # check user permission
        permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(str(request.user))
        if permissionCheckErrorMsg:
            errorMsg = permissionCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        # check if drop is open
        dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
        if dropCheckErrorMsg:
            errorMsg = dropCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        # get existing comments
        comments, getCommentErrorMsg = cireports.utils.getCNDeliveryGroupComment(deliveryGroupNumber)
        if request.method == 'POST':
            commentStatus, commentErrorMsg = cireports.utils.addCNDeliveryGroupComment(str(request.user), request.POST.get("comment"), deliveryGroupNumber)
            if commentErrorMsg:
                errorMsg = commentErrorMsg
                return render(request, "cireports/error.html",{'error': errorMsg })
            return HttpResponseRedirect("/cloudNative/"+str(product)+"/deliveryQueue/"+str(drop)+"/"+str(deliveryGroupNumber)+"/?section="+str(deliveryGroupState))
        return render(request, "cireports/cnDeliveryQueue_addComment.html", {
            'productName': product,
            'deliveryGroupNumber': deliveryGroupNumber,
            'dropNumber': drop,
            'comments': comments
        })
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to display the page for editing service groups. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })

@login_required
def displayCNDeliveryConfirmation(request, dropNumber, deliveryGroupNumber):
    '''
    The displayCNDeliveryConfirmation function displays the confirmation page while delivering a delivery group.
    '''
    errorMsg = None
    try:
        # check user permission
        permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(str(request.user))
        if permissionCheckErrorMsg:
            errorMsg = permissionCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        # check if drop is open
        dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
        if dropCheckErrorMsg:
            errorMsg = dropCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to display the page for editing service groups. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })
    return render(request, "cireports/cnDeliveryQueue_confirmDeliveryGroup.html", {
        'deliveryGroupNumber': deliveryGroupNumber,
        'dropNumber': dropNumber
    })

@login_required
def displayProductSetVersionUpdate(request, dropNumber, deliveryGroupNumber):
    '''
    The displayProductSetVersionUpdate function displays the confirmation page while updating product set version.
    '''
    errorMsg = None
    try:
        # check user permission
        permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(str(request.user))
        if permissionCheckErrorMsg:
            errorMsg = permissionCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        # check if drop is open
        dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
        if dropCheckErrorMsg:
            errorMsg = dropCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to display the page for updating product set version. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })
    return render(request, "cireports/cnDeliveryQueue_updateProductSetVersion.html", {
        'deliveryGroupNumber': deliveryGroupNumber,
        'dropNumber': dropNumber
    })

@login_required
def displayAddMissingDepReason(request, dropNumber, deliveryGroupNumber):
    '''
    The displayAddMissingDepReason function displays the page for adding missing dependencies reason while editing a delivery group.
    '''
    errorMsg = None
    try:
        # check user permission
        permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(str(request.user))
        if permissionCheckErrorMsg:
            errorMsg = permissionCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
        # check if drop is open
        dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
        if dropCheckErrorMsg:
            errorMsg = dropCheckErrorMsg
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to display the page for adding missing dependencies. Please investigate: " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })
    return render(request, "cireports/cnDeliveryQueue_addMissingDepReason.html", {
        'deliveryGroupNumber': deliveryGroupNumber,
        'dropNumber': dropNumber
    })

@login_required
def getCNBuildLogData(request, drop):
    '''
    The CLoud Native buildlog data for a drop
    '''
    errorMsg = None
    try:
        cnBuildLogData, errorMsg = getCNBuildLogDataByDrop(drop)
        if errorMsg:
            logger.error(errorMsg)
            return render(request, "cireports/error.html",{'error': errorMsg })
    except Exception as e:
        errorMsg = "There was an issue with fetching the information from DB. Please Investigate! " + str(e)
        logger.error(errorMsg)
        return render(request, "cireports/error.html",{'error': errorMsg })
    return render(request, "cireports/cloudnative_buildlog.html",
        {
            'cnBuildLogData': cnBuildLogData
        })

@login_required
def getLatestENMDrop(self):
    '''
    Gets the latest ENM drop and redirects to the buildlog page
    '''
    field = ("name",)
    latestDrop = Drop.objects.only(field).values(*field).filter(release__product__name='ENM', correctionalDrop=False).exclude(release__name__icontains="test").latest("id")
    return HttpResponseRedirect("/cloudnative/buildlog/"+latestDrop['name'])
