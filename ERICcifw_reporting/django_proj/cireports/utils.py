import datetime
import MySQLdb
import re
from cireports.models import *
from dmt.models import VmServiceName, VmServicePackageMapping, ConsolidatedToConstituentMap, PackageRevisionServiceMapping
from django.db import connection, transaction, IntegrityError, OperationalError
from django.db.models import Max, Min, Q
import os
import shutil
import urllib2, commands, subprocess
from distutils.version import LooseVersion
from datetime import datetime,timedelta
import cireports.prim
import logging
import fnmatch
import ast
from django.core.mail import send_mail
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()
import cireports.common_modules.JiraRest  as JiraRest
from cireports.common_modules.common_functions import convertVersionToRState
from datetime import datetime
now = datetime.now()
import time
from django.core.management import call_command
from StringIO import StringIO
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
import string
from django.core.cache import cache
import lockfile
import json
import hashlib
from django.utils.http import urlquote
import requests
from requests.auth import HTTPBasicAuth
import collections
from django.db.models import Count
from fem.utils import getTeamParentElement
from django.utils.encoding import smart_str
from django.contrib.auth.models import User, Group
from django.db import transaction
import requests
from threading import Lock, Thread
from cireports.DGThread import DGThread
from django.db.models import Q
from itertools import chain

developmentServer = ast.literal_eval(config.get("CIFWK", "testServer"))
deliver_DG_lock = Lock()
obsolete_DG_lock = Lock()
deliverCNDG_lock = Lock()
obsoleteCNDG_lock = Lock()

def getNexusUrlForProduct(product, enableCache=True):
    keyName='nexusUrl_' + str(product)

    nexusReleaseUrlCached=None
    if enableCache:
        nexusReleaseUrlCached = cache.get(keyName)

    if (nexusReleaseUrlCached != None):
        nexusReleaseUrl = nexusReleaseUrlCached
    else:
        if product != None:
            try:
                nexusReleaseUrl = config.get('CIFWK', str(product)+'_nexus_url')
            except:
                nexusReleaseUrl = config.get('CIFWK', 'nexus_url')
        else:
            nexusReleaseUrl = config.get('CIFWK', 'nexus_url')

        cache.set(keyName, nexusReleaseUrl)
    return nexusReleaseUrl

def nssProductCheck(groupId):
    """
    A simple check if the product is NSS by groupId.
    """
    groupId_list = groupId.split('.')
    if 'nss' in groupId_list:
        return True
    else:
        return False

def getLocalNexusUrlForProduct(product, groupId):
    """
    Local Nexus URL logic only works for NSS and ENM.
    The possibility of having more products to use local nexus URL is low. So, hardcoded.
    """
    keyName='localNexusUrl_' + str(product)
    nexusReleaseUrlCached = cache.get(keyName)

    if (nexusReleaseUrlCached != None):
        nexusReleaseUrl = nexusReleaseUrlCached
    else:
        if product != None:
            try:
                # proxy URL logic for NSS.
                if groupId != None:
                        if nssProductCheck(groupId):
                            nexusReleaseUrl = config.get('DMT_AUTODEPLOY', 'NSS_nexus_url')
                        else:
                            nexusReleaseUrl = config.get('DMT_AUTODEPLOY', str(product)+'_nexus_url')
                else:
                    nexusReleaseUrl = config.get('DMT_AUTODEPLOY', str(product)+'_nexus_url')
            except:
                logger.error("ERROR: can't get proxy URL for " + product + " Please investigate.")
                nexusReleaseUrl = config.get('DMT_AUTODEPLOY', 'nexus_url')
        else:
            nexusReleaseUrl = config.get('CIFWK', 'nexus_url')

        cache.set(keyName, nexusReleaseUrl)
    return nexusReleaseUrl

def getNexusUrl(product, arm_repo, groupId, artifactId, version, packageName, m2type, enableCache=True):
    nexusReleaseUrl = getNexusUrlForProduct(product, enableCache)

    return str(nexusReleaseUrl + "/" + arm_repo + "/" + groupId.replace(".", "/") + "/" + artifactId + "/" + version + "/" + packageName + "-" + version + "." + m2type)

def getLocalNexusUrl(product,groupId,artifactId,version,packageName,m2type):
    nexusReleaseUrl = getLocalNexusUrlForProduct(product, groupId)

    return str(nexusReleaseUrl + "/" + groupId.replace(".", "/") + "/" + artifactId + "/" + version + "/" + packageName + "-" + version + "." + m2type)

class AlreadyExists(Exception):
    """
    A generic exception to handle the existence of things we are trying to recreate
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def mapProductToPackage(product,package):
    '''
    Mapping Product to Package
    '''
    if ":" in product:
        (productName, drop) = product.split(':')
        product = Product.objects.get(name=productName)
    else:
        product = Product.objects.get(name=product)

    if not ProductPackageMapping.objects.filter(product=product, package=package).exists():
        productPkgObj = ProductPackageMapping(product=product, package=package)
        productPkgObj.save()

def mediaCategoryCheck(category):
    '''
    Checking the value for Media category
    '''
    if category is None or not category or category == "None":
        category = Categories.objects.get(name="service")
        return category

    else:
        category = str(category).lower()
        returnValue = "Error: Invalid Category.  Valid Category types are: "
        for orgObj in Categories.objects.all():
            returnValue = returnValue + orgObj.name + ", "

        if "," in category:
            mediaCategories = category.split(",")
            for mediaCategory in mediaCategories:
                if Categories.objects.filter(name=mediaCategory).exists():
                    continue
                else:
                    return returnValue + "\n"

            categoryObj, created = Categories.objects.get_or_create(name=category)
            return categoryObj
        else:
            if Categories.objects.filter(name=category).exists():
                category = Categories.objects.get(name=category)
                return category
            else:
                return returnValue + "\n"

def cleanUpRestDelivery(file=None):
    if file is not None:
        pathToFile = '/tmp/' + file
        #os.system(cmd)
        os.remove(pathToFile)

# TODO: this is a prototype, most likely remove it
def createDrop(parent_id, name):
    parent = Drop.objects.get(id=parent_id)
    logger.debug("Got a parent: " + str(parent))
    # Create our Drop
    drop = Drop(name=name)
    drop.save()

def sortPkgs(packages, dropId):
    topDrop = Drop.objects.get(id=dropId)
    sortedPkgs = []
    for currPackage in packages:
        logger.debug("Package: " + str(currPackage))
        obsoleteAfter =  LooseVersion(str(None))
        # Check the obsolete_after associated with the package
        # If the Top Level drop (the topLevelId) passed to this function is greater
        # than the obsolete_after then remove it from the baseline
        tDrop = LooseVersion(str(topDrop.name))
        if currPackage.package_revision.package.obsolete_after is not None:
            if currPackage.package_revision.package.obsolete_after.release.product == topDrop.release.product:
                obsoleteAfter = LooseVersion(str(currPackage.package_revision.package.obsolete_after.name))
                logger.debug("Top Level Drop : " + str(tDrop) + " / Obsolete After : " + str(obsoleteAfter))
        if (tDrop <= obsoleteAfter):
            logger.debug("Adding the following Package to the Baseline : " + str(currPackage))
            # We didn't find this package in our current list,  and it has been obsoleted so lets add it now to new sorted List
            sortedPkgs.append(currPackage)
        else:
            logger.debug("EXCLUDING from the Baseline : " + str(currPackage))
    return sortedPkgs

def getPackageBaseline(dropObj, type=None):
    '''
    Return the full package baseline for the supplied drop ID.
    '''
    testwareDetails = []
    pkgDetails = []
    dropAncestorIds = dropObj.getAncestorIds()
    requiredFields=("package_revision__package__id", "drop__id", "id")
    initialDropPackageMappings = DropPackageMapping.objects.select_related('package_revision__package').filter(drop__id__in=dropAncestorIds,released=1,obsolete=0).exclude(package_revision__platform='sparc').exclude(package_revision__package__obsolete_after__id__in=dropAncestorIds,package_revision__package__obsolete_after__id__lt=dropObj.id).only(requiredFields).values(*requiredFields).order_by('-drop__id','-package_revision__id')
    filteredDropPackageMappingsDict = {}
    for dpm in initialDropPackageMappings:
        if not dpm["package_revision__package__id"] in filteredDropPackageMappingsDict or (dpm['drop__id'] == dropObj.id):
           filteredDropPackageMappingsDict[dpm["package_revision__package__id"]]=dpm["id"]
    filteredDropPackageMappingIds = filteredDropPackageMappingsDict.values()
    dropDetails = DropPackageMapping.objects.prefetch_related('drop','package_revision__category').filter(id__in=filteredDropPackageMappingIds).order_by('-date_created')
    if not type == None:
        for drpPkgMap in dropDetails:
            if drpPkgMap.package_revision.category.name == "testware":
                testwareDetails.append(drpPkgMap)
            else:
                pkgDetails.append(drpPkgMap)
        if 'testware' in str(type):
            dropDetails = testwareDetails
        elif 'packages' in str(type):
            dropDetails = pkgDetails
    return dropDetails

def createPackage(packageName, packageNumber, packageResponsible, description=""):
    """
    Create a package with the given name, number and responsible individual

    Throws an exception if either the number or the name are already in use
    """
    package_list = Package.objects.filter(name=packageName)
    if len(package_list) > 0:
        raise AlreadyExists("Name: " + packageName)
    package_list = Package.objects.filter(package_number=packageNumber)
    if len(package_list) > 0:
        raise AlreadyExists("Package number: " + packageNumber)

    package = Package.objects.create(name=packageName, package_number=packageNumber, signum=packageResponsible, description=description)

def deletePackage(packageName, packageNumber):
    """
    Delete a package with the given name and number.

    Will also delete any associated package revisions.
    """
    Package.objects.filter(name=packageName).filter(package_number=packageNumber).delete()


def createPackageRevision(packageName, version, type, groupId, artifactId, category, mediaPath, intendedDrop, autoDeliver):
    """
    Create a revision of the specified package

    The version must match the format "1.0.1" or "1.0.1.1"
    """
    (maj, min, patch) = version.split(".")

    try:
        # Test to ensure all version components are integers
        (maj, min, patch) = version.split(".", 2)
        maj = int(maj)
        min = int(min)
        pparts = patch.split(".")
        if (len(pparts) > 1):
            patch = int(pparts[0])
            ec = int(pparts[1])
    except Exception as e:
        logger.error(str(e))
        raise e
    # verify the package actually exists
    package = Package.objects.get(name=packageName)

    # Verify we don't already have this package ver
    package_vers = PackageRevision.objects.filter(package__name=packageName, version=version, m2type=type)
    if (len(package_vers) > 0):
        raise AlreadyExists("Package name: " + packageName + " ; version: " + version)

    PackageRevision.objects.create(package=package,
                                          version=version,
                                          groupId=groupId,
                                          artifactId=artifactId,
                                          m2type=type,
                                          autodrop=intendedDrop,
                                          autodeliver=autoDeliver,
                                          category=category,
                                          media_path=mediaPath,
                                          kgb_test="not_started",
                                          cid_test="not_started",
                                          cdb_test="not_started")

def createSolutionSet(ssName, ssNum):
    """
    Create a solution set with the given name and number
    """
    ssList = SolutionSet.objects.filter(name=ssName)
    if (len(ssList) > 0):
        raise AlreadyExists("SS Name: " + ssName + " ; number: " + ssList[0].package_number)
    ssList = SolutionSet.objects.filter(package_number=ssNum)
    if (len(ssList) > 0):
        raise AlreadyExists("SS package number: " + ssNum + " already exists - SS name: " + ssList[0].name)
    ss = SolutionSet.objects.create(name=ssName, package_number=ssNum)

def createRelease(relName):
    """
    Create a release with the specified name
    """
    rel = Release.objects.create(name=relName)

def createDrop(dropName, releaseName, designbaseName=None):
    """
    Create the relevant drop in the specified release
    """
    if (designbaseName != None):
        db = Drop.objects.get(name=designbaseName)
        drop = Drop.objects.create(name=dropName, release=Release.objects.get(name=releaseName), designbase=db)
    else:
        drop = Drop.objects.create(name=dropName, release=Release.objects.get(name=releaseName))

def performDelivery(pkg, ver, type, drp, product, txt, platform, user):
    """
    Call the delivery command to deliver a particular version of a package to a specific drop
    """
    content = StringIO()
    try:
        call_command('cifwk_deliver', package=str(pkg), packageVersion=str(ver), drop=str(drp), product=str(product), email=str(txt), platform=str(platform), packageType=type, user=user, stdout=content)
    except Exception as e:
        logger.error("There was an issue with delivering module, error thrown: " +str(e))
    content.seek(0)
    result = content.read()
    return result

def performDelivery2(package, ver, type, dropArray, product, email, platform, restDelivery=None, user=None, deliveryGroup=None):
    '''
    This function performs deliveries that are called via REST
    '''
    dm = config.get("CIFWK", "fromEmail")
    status = ""
    if restDelivery is None:
        restDelivery = True
    developmentServer = ast.literal_eval(config.get("CIFWK", "testServer"))
    if developmentServer == 1:
        try:
            deliveryEmail = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", str(product).upper()))
        except Exception as e:
            deliveryEmail=None
            status = status+",ERROR: Distribution Email list Required For Product " + str(product) + ". \n  Please contact CI Axis to give the Distribution Email list for this Product" + str(e)
            return status
    else:
        try:
            product = Product.objects.get(name=product)
            productEmail = ProductEmail.objects.filter(product=product.id)
            deliveryEmail = []
            if productEmail != None:
                for delEmail in productEmail:
                    deliveryEmail.append(delEmail.email)
        except Exception as e:
            deliveryEmail=None
            status = status+",ERROR: Distribution Email list Required For Product " + str(product) + ". \n  Please contact CI Axis to give the Distribution Email list for this Product" + str(e)
            return status

    to = []
    if email == None:
        userEmail = "User email not supplied, command line delivery"
    else:
        userEmail=email
        to.append(userEmail)
    if deliveryEmail != None:
        for i in deliveryEmail:
            to.append(i)

    #Get Latest Version of the Package if latest is selected as Version
    if ( ver == "latest" ):
        try:
            ver, statusNew = getLatestVersionOfPackage(package, platform)
            if "ERROR:" in statusNew:
                return status+","+statusNew
        except Exception as e:
            return status+",ERROR: Issue delivering artifact "+str(e)

    #if auto selected search database for drops to be delivered to
    if ( dropArray == "auto" ):
        try:
            dropArray, statusNew = getLatestDropOnProductRelease(dropArray, product, platform, package, ver, type)
            if "ERROR:" in statusNew:
                return status+","+statusNew
        except Exception as e:
            return status+",ERROR: Issue delivering artifact "+str(e)

    dropArray=dropArray.split(",")

    #Make Delivery
    try:
        header, content, statusNew = makeDeliveryOfPackage(dropArray, package, ver, type, platform, product, userEmail, to, restDelivery, user, deliveryGroup)
        status = status+","+statusNew
    except Exception as e:
        return "ERROR: Issue delivering artifact "+str(e)
    return status

def obsolete2(artifactRevId,dropId,reason=None,user=None,forceOption=False):
    try:
        dropFields = ('id', 'name', 'release__product__name',)
        dropObj = Drop.objects.only(dropFields).values(*dropFields).get(id=dropId)
        drop = dropObj['name']
        dropId = dropObj['id']
        product = dropObj['release__product__name']
        packageRevisionObjFields = ('id', 'version', 'platform', 'package__name','m2type',)
        packageRevisionObj = PackageRevision.objects.only(packageRevisionObjFields).values(*packageRevisionObjFields).get(id=artifactRevId)
        packageVersion = packageRevisionObj['version']
        platform = packageRevisionObj['platform']
        packageName = packageRevisionObj['package__name']
        pkgRevId= packageRevisionObj['id']
        if reason is None:
            reason = "Automated obsoletion due to delivery failure"
        if user is None:
            signum = "lciadm100"
        else:
            try:
                signum = user.username
            except:
                signum = user
    except Exception as e:
        msg = "ERROR: Issue with finding Package Revison Object cifwk DB using entered values - " + str(e)
        logger.error(msg)
        return msg
    try:
        dropPkgMapObjFields = ('id', 'drop__id', 'drop__release__product',)
        dropPkgMapObj = DropPackageMapping.objects.prefetch_related('package_revision').only(dropPkgMapObjFields).filter(package_revision_id=pkgRevId,drop_id=dropId,obsolete=0).order_by('-id').values(*dropPkgMapObjFields)[0]
    except Exception as e:
        msg = "ERROR: Issue with finding Drop to Package Mapping Object cifwk DB using entered values - " + str(e)
        logger.error(msg)
        return msg
    try:
        checkResults = obsoleteArtifactInMediaArtifactCheck(product, pkgRevId, packageName, packageVersion, forceOption)
        if "ERROR" in checkResults:
           return checkResults
    except Exception as e:
        msg = "ERROR: Issue with finding ISO and/or package - " + str(e)
        logger.error(msg)
        return msg
    if dropId != dropPkgMapObj['drop__id']:
        msg = "ERROR: Package Revision Version should be Obsoleted from the drop it was delivered to " + str(dropPkgMapObj['drop__release__product']) + " drop " + str(dropPkgMapObj['drop'])
        logger.error(msg)
        return msg
    try:
        with transaction.atomic():
            obsoleteResult = obsolete(dropPkgMapObj['id'], packageName, platform, signum, reason, drop)
            if obsoleteResult != "error":
                msg = "Obsoleted : " + str(packageName) + " version: " + str(packageVersion) + " type: " +str(packageRevisionObj['m2type']) + " on " + str(datetime.now()) + " by " + str(signum)
                logger.info(msg)
            else:
                msg = "ERROR: There was an issue Obsoleting the Package, Please ensure that it is not part of a frozen Drop"
                logger.error(msg)
            return msg
    except IntegrityError as e:
        msg = "ERROR: Issue with Obsoleting: " + str(e)
        logger.error(msg)
        return msg

def obsoleteArtifactInMediaArtifactCheck(product, packageRevisionObjId, packageName, packageVersion, forceOption=False):
    '''
    The Check if Artifact is in passed/in_progress Media Artifact before trying obsolete
    '''
    msg = "Artifact not in Passed/in_progress Media Artifact"
    try:
        if forceOption:
            isoMappingObj = list(ISObuildMapping.objects.prefetch_related('package_revision').filter(Q(drop__release__product__name=product,package_revision_id=packageRevisionObjId,iso__overall_status__state="passed")))
        else:
            isoMappingObj = list(ISObuildMapping.objects.prefetch_related('package_revision').filter(Q(drop__release__product__name=product,package_revision_id=packageRevisionObjId,iso__overall_status__state="passed") | Q(drop__release__product__name=product,package_revision_id=packageRevisionObjId,iso__overall_status__state="in_progress")))
        if isoMappingObj:
            msg = "ERROR: " + str(packageName) + "(" + str(packageVersion) + ") cannot be obsoleted due to it being part of a ISO that has passed or is in progress of CDB testing."
            logger.error(msg)
            return msg
        return msg
    except Exception as e:
        msg = "ERROR: Issue with finding ISO and/or package - " +str(e)
        logger.error(msg)
        return msg

def obsoleteDeliveryGroupArtifacts(deliveryGroupObj, user, product, drop, forceOption):
    '''
    Obsoleting Delivery Group
    '''
    statusList = []
    obsoleteFault = False
    groupId = deliveryGroupObj.id
    try:
        requiredValues = ('packageRevision__id', 'packageRevision__artifactId', 'packageRevision__version',)
        pkgMaps = DeliverytoPackageRevMapping.objects.only(requiredValues).values(*requiredValues).filter(deliveryGroup__id=groupId)
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        reason = "Obsoleted as part of delivery group obsolete (Drop: "+ str(drop) + " Group ID: " + str(groupId) + ")"
        for item in pkgMaps:
            status = obsoleteArtifactInMediaArtifactCheck(product, item['packageRevision__id'], item['packageRevision__artifactId'], item['packageRevision__version'], forceOption)
            if 'ERROR' in status:
                status = "Issue with obsoleting Artifact " + str(item['packageRevision__artifactId']) + "-" + str(item['packageRevision__version']) + ": " +  str(status)
                obsoleteFault = True
                statusList.append(str(status))
        if obsoleteFault == False:
            for item in pkgMaps:
                # Obsolete each item in the group
                status = cireports.utils.obsolete2(item['packageRevision__id'],dropObj.id,reason,user, forceOption)
                if 'ERROR' in status:
                   status = "Issue with obsoleting Artifact " + str(item['packageRevision__artifactId']) + "-" + str(item['packageRevision__version']) + ": " +  str(status)
                   obsoleteFault = True
                statusList.append(str(status))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if obsoleteFault:
           commentErrorlist = []
           count = 1
           for stat in statusList:
               commentErrorlist.append(str(count) +". " + str(stat) + " <br> *")
               count += 1
           deliveredComment = str(user.first_name) + " "  + str(user.last_name) + " could not Obsolete this Group due to Errors. Group Status: <br> " + str(commentErrorlist).replace("[", "").replace("'", "").replace("u'", "").replace("]", "").replace("*,", "").replace("*", "")
           newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
           cireports.utils.sendObsoleteGroupErrorEmail(product, drop, groupId, statusList, str(user.username))
           deliveryGroupObj.warning = True
           deliveryGroupObj.save(force_update=True)
        return statusList
    except Exception as e:
        errMsg = "ERROR obsoleting group " + str(groupId) +": " + str(e)
        logger.error(errMsg)
        statusList.append(errMsg)
        return statusList

def createISOcontentListInDB(dropName, productName, releaseName, platformType=None):
    """
     Just the ISO Content being entered into DB without building or storing an ISO
    """
    info = StringIO()
    try:
        call_command('cifwk_createisocontent',  drop=str(dropName), product=str(productName), release=str(releaseName), platform=str(platformType), content="true",  stdout=info)
    except Exception as e:
        logger.error("There was an issue with create ISO content module, error thrown : " + str(e) )
    info.seek(0)
    result = info.read()
    logger.info(str(result))
    return result

def createDeliveryGroupCommment(group_id,comment):
    '''
      This for when delivery group cannot auto-delivered and we need to add comment for the same to notify users.
    '''
    try:
        deliveryGroup = DeliveryGroup.objects.get(pk=group_id)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=comment, date=now)
        return True, "Auto delivery is not enabled at the moment, contact CI-Main track for further information."

    except Exception as e:
        return False, str(e)


def createISOversion(dpms, currentDrop, dropName):
    '''
      Creating a Version for OSS-RC ISO
    '''
    version = None
    logger.info("** Checking for deliveries that can be used to create ISO with **")
    if not dpms:
        logger.info("No deliveries found to create ISO content with. Exiting")
        return "true"

    logger.info(" ** Checking for ISO builds for this Drop **")
    # Get List of the ISO's builds for this drop
    iBuilds = ISObuild.objects.filter(drop=currentDrop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-build_date')

    if not iBuilds:
        dropNameParts = dropName.split(".")
        if (len(dropNameParts) == 2):
            [maj, min] = dropName.split(".", 1)
            newLeading=min+".0"
        elif (len(dropNameParts) == 3):
            [maj, min, patch] = dropName.split(".", 2)
            version = "1."+str(patch)+".1"
        if (len(dropNameParts) == 4):
            [maj, min, patch, serv] = dropName.split(".", 3)
            version = "1."+str(serv)+".1"
        logger.info("New ISO (Version " +str(version) + ") for this drop (" + str(dropName) +")")
        return version
    else:
        latestBuiltIso = iBuilds[0].build_date
        logger.info("Latest Build Date of ISO (Version " +str(iBuilds[0].version) + ") for this drop (" + str(dropName) +") was: " + str(latestBuiltIso))
        [maj, min, patch] = str(iBuilds[0].version).split(".", 2)
        newPatch = int(patch) + 1
        version = str(maj)+"." + str(min) +"."+ str(newPatch)
        logger.info("New ISO (Version " +str(version) + ") for this drop (" + str(dropName) +")")
        return version


def deleteISOcontentFromDB(dropName, productName, releaseName):
    '''
    Used When a ISO BUILD Jenkins Fails - Doesn't get uploaded to Nexus
    '''
    drop = Drop.objects.get(name=dropName, release__name=releaseName, release__product__name=productName)
    iBuilds = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-build_date')
    isoArtifact = iBuilds[0].mediaArtifact.name
    version = iBuilds[0].version
    isoNexusUrl = iBuilds[0].getHubIsoUrl()
    url = str(isoNexusUrl)+"/"+str(isoArtifact)+"/"+str(version)+"/"
    try:
        urllib2.urlopen(url)
    except Exception as e:
        ISObuild.objects.filter(version=version, drop=drop, mediaArtifact__testware=False).delete()
        logger.error("ISO Build Jenkins Job Failed - Please check Job")

def getListOfDrops(pkg_info, filter):
    """
    Pass in either a PackageRevision Object or a PackageRevision QuerySet
    If passing a PackageRevision QuerySet then filter is set to true to loop through the PackageRevisions
    """
    drops = []
    if filter:
        for pri in pkg_info:
            drops += DropPackageMapping.objects.filter(package_revision=pri, released=True).order_by('-drop')
    else:
        drops += DropPackageMapping.objects.filter(package_revision=pkg_info, released=True).order_by('-drop')

    return drops

def storePRI(drop,pkgName,cxp,pkgVersion,type,platform):
    """
    Queries Jira for stories to bugs related to Package Name, cxp number, package version and drop. stores in database table
    """
    myJiraRest = JiraRest.JiraRest()
    fieldstoGet = [['key'],['fields','summary'],['fields','issuetype','name'],['fields','resolution','name'],['fields','resolutiondate'],['fields','priority','name']]
    #Returns value<X>
    #0 name
    #1 Summary
    #2 type
    #3 status
    #4 closed date
    #5 Priority

    # Strip the ERIC from the front of the Package Name before sending it to the Jira rest call
    packageName = re.sub(r"ERIC", "", pkgName)
    # First Search for the package name
    pkg_search_str="cf[12202]=\""+str(drop)+"\"+AND+cf[12300]=\""+str(packageName)+"\""
    # Now Search for older entries which have the CXP number attached
    cxp_search_str="cf[12202]=\""+str(drop)+"\"+AND+cf[12300]=\""+str(cxp)+"\""
    pkg_result = myJiraRest.getJiraIdDetails(pkg_search_str, fieldstoGet)
    cxp_result = myJiraRest.getJiraIdDetails(cxp_search_str, fieldstoGet)
    clearDrop = "false"

    for result in pkg_result,cxp_result:
        if result != "null":
            pkg_info1 = Package.objects.get(name=pkgName)
            if platform == "None":
                pkg_info = PackageRevision.objects.get(package_id=pkg_info1.id, version=pkgVersion, m2type=type)
            else:
                pkg_info = PackageRevision.objects.get(package_id=pkg_info1.id, version=pkgVersion, platform=platform, m2type=type)
            drop_info = Drop.objects.get(name=drop)
            # Remove drop from existing entries in db, just once!
            if clearDrop == "false":
                current_pri = pri.objects.filter(pkgver__package__name=pkgName,drop__name=drop_info.name)
                for current_ticket in current_pri:
                    try:
                        test=first_pkgver=current_ticket.first_pkgver
                        pri_nodrop = pri(id=current_ticket.id, pkgver=current_ticket.pkgver,first_pkgver=current_ticket.first_pkgver, fault_id=current_ticket.fault_id, fault_desc=current_ticket.fault_desc ,fault_type=current_ticket.fault_type,  status=current_ticket.status, priority=current_ticket.priority, comment=current_ticket.comment)
                    except Exception as e:
                        pri_nodrop = pri(id=current_ticket.id, pkgver=current_ticket.pkgver, fault_id=current_ticket.fault_id, fault_desc=current_ticket.fault_desc ,fault_type=current_ticket.fault_type,  status=current_ticket.status, priority=current_ticket.priority, comment=current_ticket.comment)
                    pri_nodrop.save()
                clearDrop = "true"
            for data in result:
                # We only want issues of type story or bug
                if result[data]['value2'] == "Story" or result[data]['value2'] == "Bug":
                    try:
                        # Run update if jira is already in database, this keeps existing comments
                        existing = pri.objects.get(fault_id=result[data]['value0'])
                        try:
                            epkginfo=existing.first_pkgver
                        except:
                            epkginfo="NULL"
                        if result[data]['value3'] != "Fixed":
                            priInfo = pri(id=existing.id, pkgver=pkg_info, fault_id=result[data]['value0'], fault_desc=result[data]['value1'],  fault_type=result[data]['value2'], drop=drop_info, status=result[data]['value3'], priority=result[data]['value5'], comment=existing.comment)
                        else:
                            if epkginfo=="NULL":
                                priInfo = pri(id=existing.id, pkgver=pkg_info,first_pkgver=pkg_info, fault_id=result[data]['value0'], fault_desc=result[data]['value1'],  fault_type=result[data]['value2'], drop=drop_info, status=result[data]['value3'], priority=result[data]['value5'], comment=existing.comment)
                            else:
                                priInfo = pri(id=existing.id, pkgver=pkg_info, first_pkgver=epkginfo, fault_id=result[data]['value0'], fault_desc=result[data]['value1'],  fault_type=result[data]['value2'], drop=drop_info, status=result[data]['value3'], priority=result[data]['value5'], comment=existing.comment)
                    except:
                        if result[data]['value3'] != "Fixed":
                            priInfo = pri( pkgver=pkg_info, fault_id=result[data]['value0'], fault_desc=result[data]['value1'],  fault_type=result[data]['value2'], drop=drop_info, status=result[data]['value3'], priority=result[data]['value5'], comment='')
                        else:
                           priInfo = pri( pkgver=pkg_info, first_pkgver=pkg_info, fault_id=result[data]['value0'], fault_desc=result[data]['value1'],  fault_type=result[data]['value2'], drop=drop_info, status=result[data]['value3'], priority=result[data]['value5'], comment='')
                    priInfo.save()
                else:
                    continue

def getDocuments(version,product):
    '''
    The displayDocuments function is responable from building up the Document baseline page view per drop
    '''
    documentList = []
    #Get all drop and sort
    dropList = []
    docObjList = []
    finalDocObjList = []
    dropVersion = LooseVersion(str(version))
    allDropsList = list(Drop.objects.filter(release__product__name=product))
    try:
        #Sort the Drops in order float numbers
        allDropsList.sort(key=lambda drop:LooseVersion(drop.name), reverse=True)
        logger.info("Drops Sorted without Issue: " +str(allDropsList[0]))
    except Exception as e:
        logger.error("Error with sorting float list: " +str(e))
        return 1
    for dropObj in allDropsList:
        dropList.append(dropObj.name)
    #Get documnets for this drop and work back
    documentsObj = Document.objects.all()
    #Start at current version and work backwards
    try:
        versionIndex = dropList.index(version)
        #For each drop in the list to the version select and not beyond
        for drop in allDropsList[versionIndex:]:
            for document in documentsObj:
                if document.drop == drop:
                    #Get a list of doc based on CXP, Drop and ordered by deliveryDate
                    doc = list(Document.objects.filter(id=document.id, drop=drop).order_by('-deliveryDate'))
                    if document.obsolete_after is not None:
                        obsoleteAfter = LooseVersion(str(document.obsolete_after.name))
                        if (dropVersion <= obsoleteAfter):
                            documentList.append(document.id)
                            docObjList.append(doc[0])
                    else:
                        documentList.append(document.id)
                        docObjList.append(doc[0])
        return docObjList
    except Exception as e:
        errMsg = "Issue with getting Document: " +str(e)
        logger.error(errMsg)
        return errMsg

def getPackagesBasedOnProduct(product):
    '''
    The getPackagesBasedOnProduct fuction is used to return the list of packages
    associated with the product selected based on mapping information
    '''
    try:
        allPackages = ProductPackageMapping.objects.filter(product=product, package__hide=0,  package__testware=0)
        updatedAllPackages = []
        for item in allPackages:
            updatedAllPackages.append(item.package)
    except Exception as e:
        logger.error(e)
        return 1
    allCount = len(updatedAllPackages)
    return updatedAllPackages,allCount

def getTestwareBasedOnProduct(product):
    '''
    The getTestwareBasedOnProduct fuction is used to return the list of Testware
    associated with the product selected based on mapping information
    '''
    try:
        allPackages = ProductPackageMapping.objects.filter(product=product, package__hide=0, package__testware=1)
        updatedAllPackages = []
        for item in allPackages:
            updatedAllPackages.append(item.package)
    except Exception as e:
        logger.error(e)
        return 1
    allCount = len(updatedAllPackages)
    return updatedAllPackages,allCount

def getArtifactsBasedOnProduct(product,packageType):
    '''
    The getArtifactsBasedOnProduct fuction is used to return the list of packages
    associated with the product selected based on mapping information
    '''
    testware = False
    if packageType == "testware":
        testware = True

    try:
        allPackages = ProductPackageMapping.objects.filter(product=product, package__hide=0, package__testware=testware)
        updatedAllPackages = []
        for item in allPackages:
            updatedAllPackages.append(item.package)
    except Exception as e:
        logger.error(e)
        return 1
    allCount = len(updatedAllPackages)
    return updatedAllPackages,allCount

def getCDBStatusInfo(cdbStatusDict, types, isoCurrentStatus, successful=None):
    '''
    Getting Status Information for CDB the latest and latest Successful
    '''

    typeList = types
    statusCurrentList = []
    statusPassedList = []
    statusHistoryList = []

    for cdbtype,status in isoCurrentStatus.items():
        if CDBTypes.objects.filter(id=cdbtype).exists():
           cdbtypeObj = CDBTypes.objects.get(id=cdbtype)
           if status.count('#') == 4:
              state,start,end,testReportNumber,veLog = status.split("#")
              isoStatus = str(cdbtypeObj.name),state,start,end,testReportNumber,veLog
           else:
              state,start,end,testReportNumber = status.split("#")
              isoStatus = str(cdbtypeObj.name),state,start,end,testReportNumber,None
           if typeList != "history":
              if len(cdbStatusDict) != 0:
                 for cdb in cdbStatusDict:
                     if len(cdbStatusDict[cdb]) != 0:
                        for statusDict in cdbStatusDict[cdb]:
                            try:
                                statusDict = ' '.join(statusDict)
                            except:
                                dictList = list(statusDict)
                                dictListLen = len(dictList)
                                for dictListIndex in range(0,dictListLen):
                                    if dictList[dictListIndex] is None:
                                        dictList[dictListIndex] = "None"
                                statusDict = tuple(dictList)
                                statusDict = ' '.join(statusDict)
                            if successful == None:
                               [installType, otherInfo] = statusDict.split(" ",1)
                               if str(installType) not in typeList:
                                  typeList.append(installType)
                            else:
                               [installType, stateDict, other] = statusDict.split(" ", 2)
                               if stateDict == "passed" and str(installType) not in typeList:
                                  typeList.append(installType)
              if str(cdbtypeObj.name) not in typeList:
                 if state == "passed" and successful != None:
                    statusPassedList.append(isoStatus)
                 else:
                    statusCurrentList.append(isoStatus)
           else:
              statusHistoryList.append(isoStatus)

    if successful == None and typeList != "history":
       statusList = statusCurrentList
    elif typeList != "history":
       statusList = statusPassedList
    else:
       statusList = statusHistoryList
    index = 0
    for status in statusList:
        if status[4] != "None" and status[4] != "":
            try:
                testResultsObj=TestResults.objects.get(id=status[4])
                reportDirectory = testResultsObj.test_report_directory
            except Exception as e:
                logger.error("Error: " +str(e))
            if (reportDirectory.startswith("kgb_") or reportDirectory.startswith("cdb_")):
                reportDirectory = "/static/testReports/"+reportDirectory+"/index.html"
            statusList[index] += (reportDirectory,)
            index += 1
        else:
            statusList[index] += ('None',)
            index += 1
    return statusList, typeList

def getDropInformation(drops):
    cdbStatusDict = {}
    typeList = []
    statusList = []
    dropTuplesList = []

    for drop in drops:
        try:
            isos = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-build_date')
            for iso in isos:
                if iso.current_status:
                    isoCurrentStatus = ast.literal_eval(iso.current_status)
                    try:
                        statusList, typeList = getCDBStatusInfo(cdbStatusDict, typeList, isoCurrentStatus)
                    except Exception as e:
                        logger.error("Error: " +str(e))
                        statusList = []
                else:
                    statusList = []
                if statusList:
                    cdbStatusDict[iso] = statusList
                statusList = []
            typeList = []
            dropTuplesList.append((drop,cdbStatusDict))
            cdbStatusDict = {}
        except:
            dropTuplesList=[]
    return dropTuplesList

def expandProductInformation(productObj):
    '''
    This function expands on the Summary Page to display the full suite of information for all Releases of a Product
    '''
    try:
        noReleaseDict = {}
        productToDropDict = {}
        foundResult = 0
        try:
            if Release.objects.filter(product=productObj).exists():
                drops = Drop.objects.filter(release__product=productObj).order_by('-id')
                productToDropDict[productObj] = getDropInformation(drops)
            else:
                noReleaseDict[productObj.name] = "Product: '" +str(productObj.name) + "' is not Associated with any Releases"
        except Exception as e:
                logger.error("Issue returning product from db: " +str(e))
                return 1
        allRel = Release.objects.all().order_by('-name')
        return productToDropDict,noReleaseDict,allRel,foundResult
    except Exception as e:
        logger.error("Issue building up details for the release page on the CI Portal: " +str(e))
        return 1

def getChosenDropsForSummary(product, oldSortOrder):
    '''
    This function returns a list of selected drops for a product, chosen by users for use on summary pages
    If no data for the given product is found in the configproducts table, it reverts to the old behaviour
    The sort order for the old behaviour is given as the second parameter to the function
    '''
    drops = []
    configProductsObjs = ConfigProducts.objects.filter(product=product, active=True).order_by('order_id')
    if bool(configProductsObjs):
        for configProductsObj in configProductsObjs:
            if configProductsObj.num == 0:
                try:
                    singleDrop = Drop.objects.get(release__product=product, name=configProductsObj.choice)
                    drops.append(singleDrop)
                except Drop.DoesNotExist:
                    logger.error("This drop is specified as a choice for the summary page for product " + product.name + " but it doesn't exist: " + configProductsObj.choice)
            else:
                listOfDrops = Drop.objects.filter(release__product=product, release__name=configProductsObj.choice).order_by('-id')[:configProductsObj.num]
                drops.extend(listOfDrops)
    else:
        drops = Drop.objects.filter(release__product=product).order_by(oldSortOrder)[:4]
        drops = sorted(drops, key=lambda k: -k.id)
    return drops

def productSummaryBuildUp():
    '''
    This function build up the products and releases for display on the product page of portal
    '''
    try:
        products = Product.objects.all().exclude(name="None").order_by('name')
        noReleaseDict = {}
        productToDropDict = {}
        try:
            for product in products:
                product = Product.objects.get(name=product.name)
                if Release.objects.filter(product=product).exists():
                    drops = getChosenDropsForSummary(product,'-actual_release_date')
                    productToDropDict[product] = getDropInformation(drops)
                    continue
                else:
                    noReleaseDict[product.name] = "Product: '" +str(product.name) + "' is not Associated with any Releases"
        except Exception as e:
                logger.error("Issue returning product from db: " +str(e))
                return 1
        return products,productToDropDict,noReleaseDict
    except Exception as e:
        logger.error("Issue building up details for product page on web portal: " +str(e))
        return 1

def getProdSetDropInformation(drops):
    cdbStatusDict = {}
    typeList = []
    statusList = []
    prodSetVersions = []
    dropTuplesList = []

    for drop in drops:
        if ProductSetVersion.objects.filter(drop=drop).exists():
            versions = ProductSetVersion.objects.filter(drop=drop).order_by('-id')
            for version in versions:
               prodSetVersions.append(version)
               if version.current_status:
                   prodSetCurrentStatus = ast.literal_eval(version.current_status)
                   try:
                       statusList, typeList = getCDBStatusInfo(cdbStatusDict, typeList, prodSetCurrentStatus)
                   except Exception as e:
                        logger.error("Error: " +str(e))
                        statusList = []
               else:
                   statusList = []
               if statusList:
                   foundResult = 1
                   cdbStatusDict[version] = statusList
               statusList = []
        typeList = []
        dropStatusTuple=(drop,cdbStatusDict)
        dropTuplesList.append(dropStatusTuple)
        cdbStatusDict = {}

    return dropTuplesList,prodSetVersions

def expandProductSetInformation(productSet):
    '''
    This function expands the list of Products Sets with detailed status per drop for display on the CI Portal
    '''
    try:
        prodSet = ProductSet.objects.get(name=productSet)
        noReleaseDict = {}
        prodSetToDropDict = {}
        prodSetVersions = []
        dropTuple = {}

        try:
            allProdSetRel = ProductSetRelease.objects.filter(productSet=prodSet).order_by('-name')
        except ProductSetRelease.DoesNotExist as e:
            noReleaseDict[prodSet.name] = "Product Set: '" +str(prodSet.name) + "' is not Associated with any Releases"

        try:
            drops = Drop.objects.filter(release__product=allProdSetRel[0].release.product).order_by('-id')
            dropTuple,prodSetVersions = getProdSetDropInformation(drops)
            prodSetToDropDict[prodSet] = dropTuple
        except :
            drops = ""
        return allProdSetRel,prodSetToDropDict,noReleaseDict, prodSetVersions
    except Exception as e:
        logger.error("Issue expanding details for product set release page on web portal: " +str(e))
        return 1

def productSetSummaryBuildUp():
    '''
    This function build up the product set summarys for display on the CI Portal
    '''
    try:
        prodSets = ProductSet.objects.all()
        noReleaseDict = {}
        prodSetToDropDict = {}
        prodSetVersions = []
        dropTuple = {}

        try:
            for prodSet in prodSets:
                try:
                    prodSetReleases = ProductSetRelease.objects.filter(productSet=prodSet)
                except ProductSetRelease.DoesNotExist as e:
                    noReleaseDict[prodSet.name] = "Product Set: '" +str(prodSet.name) + "' is not Associated with any Releases"

                try:
                    drops = getChosenDropsForSummary(prodSetReleases[0].release.product,'-mediaFreezeDate')
                    dropTuple,prodSetVersions = getProdSetDropInformation(drops)
                    prodSetToDropDict[prodSet] = dropTuple
                except :
                    drops = ""
                continue
        except Exception as e:
                logger.error("Issue returning product sets from db: " +str(e))
                return 1
        return prodSets,prodSetToDropDict,noReleaseDict
    except Exception as e:
        logger.error("Issue building up details for product set page on web portal: " +str(e))
        return 1

def getCNProductsSummary():
    '''
    This function returns list of Cloud Native products
    dictiionary can't be in order for some reasons. Use OrderedDict() instead
    due to ETTS-7230, OrderedDict() is not available for python 2.6
    use sorted() instead
    '''
    try:
        cnProductSets = CNProductSet.objects.all()
        cnProductToDropDict = {}
        cnDropToCNProductSetVerList = {}
        for product in cnProductSets:
            drops = CNProductSetVersion.objects.values_list('drop_version', flat=True).order_by('-drop_version').distinct()
            for drop in drops:
                cnProductSetVerToStatusDict = {}
                cnProductSetObj = CNProductSetVersion.objects.filter(drop_version = drop, active = True).order_by('-id')[:1]
                for psStatus in cnProductSetObj:
                    cnProductSetVerToStatusDict[psStatus.product_set_version] = ast.literal_eval(psStatus.status)
                cnDropToCNProductSetVerList[drop] = cnProductSetVerToStatusDict
            cnDropToCNProductSetVerList = sorted(cnDropToCNProductSetVerList.items())
            cnDropToCNProductSetVerList.reverse()
            cnProductToDropDict[product] = cnDropToCNProductSetVerList
        return cnProductToDropDict
    except Exception as e:
        logger.error("Issue returning products from the DB: " +str(e))
        return 1

def getLatestCDBforDrop(product, drop):
    '''
     Latest CDB for all types
    '''
    cdbStatusDict = {}
    statusList = []
    typeList = []
    flag = 0
    product = Product.objects.get(name=product)
    drop = Drop.objects.get(name=drop, release__product=product)
    try:
        isos = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-build_date')
        for iso in isos:
            if iso.current_status:
                isoCurrentStatus = ast.literal_eval(iso.current_status)
                try:
                    statusList, typeList = getCDBStatusInfo(cdbStatusDict, typeList, isoCurrentStatus)
                except Exception as e:
                    logger.error("Error: " +str(e))
                    statusList = []
            else:
                statusList = []
            if statusList:
                flag = 1
                cdbStatusDict[iso] = statusList
            statusList = []
        return cdbStatusDict , flag
    except Exception as e:
        logger.error("Issue building up details for CDB Summary page on web portal: " +str(e))
        return 1


def getLatestPSforDrop(productSet, drop):
    '''
     Latest Product set result for all types
    '''
    cdbStatusDict = {}
    statusList = []
    typeList = []
    flag = 0
    prodSetObj = ProductSet.objects.get(name=productSet)
    prodSetRelObj = ProductSetRelease.objects.filter(productSet=prodSetObj)[0]
    drop = Drop.objects.get(name=drop, release__product=prodSetRelObj.release.product)

    try:
        versions = ProductSetVersion.objects.filter(drop=drop).order_by('-id')
        for version in versions:
            if version.current_status:
               isoCurrentStatus = ast.literal_eval(version.current_status)
               try:
                   statusList, typeList = getCDBStatusInfo(cdbStatusDict, typeList, isoCurrentStatus)
               except Exception as e:
                     logger.error("Error: " +str(e))
                     statusList = []
            else:
                statusList = []
            if statusList:
                flag = 1
                cdbStatusDict[version] = statusList
            statusList = []
        return cdbStatusDict , flag
    except Exception as e:
        logger.error("Issue building up details for Product Set Summary page on web portal: " +str(e))
        return 1

def getLastSuccessfulCDBforDrop(product, drop,excludeList):
    '''
    CDB Status of Successful latest CDB Types

    '''
    cdbStatusDict = {}
    statusList = []
    typeList = []
    successful = True
    product = Product.objects.get(name=product)
    drop = Drop.objects.get(name=drop, release__product=product)
    try:
        isos = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-build_date')
        for iso in isos:
            if iso.current_status:
                isoCurrentStatus = ast.literal_eval(iso.current_status)
                try:
                    statusListTmp, typeList = getCDBStatusInfo(cdbStatusDict, typeList, isoCurrentStatus, successful)
                    versionId = iso.id
                    statusList = []
                    for item in statusListTmp:
                        idType=str(versionId)+"_"+str(item[0])
                        if not idType in excludeList:
                            statusList.append(item)
                except Exception as e:
                     logger.error("Error: " +str(e))
                     statusList = []
            else:
                statusList = []
            if statusList:
                cdbStatusDict[iso] = statusList
            statusList = []
        return cdbStatusDict , typeList
    except Exception as e:
        logger.error("Issue building up details for CDB Summary page on web portal: " +str(e))
        return 1


def getLastSuccessfulPSforDrop(productSet, drop,excludeList):
    '''
    Get last successful product set run

    '''
    cdbStatusDict = {}
    statusList = []
    typeList = []
    successful = True
    prodSetObj = ProductSet.objects.get(name=productSet)
    prodSetRelObj = ProductSetRelease.objects.filter(productSet=prodSetObj)[0]
    drop = Drop.objects.get(name=drop, release__product=prodSetRelObj.release.product)

    try:
        versions = ProductSetVersion.objects.filter(drop=drop).order_by('-id')
        for version in versions:
            if version.current_status:
                isoCurrentStatus = ast.literal_eval(version.current_status)
                try:
                    statusListTmp, typeList = getCDBStatusInfo(cdbStatusDict, typeList, isoCurrentStatus, successful)
                    versionId = version.id
                    statusList = []
                    for item in statusListTmp:
                        idType=str(versionId)+"_"+str(item[0])
                        if not idType in excludeList:
                            statusList.append(item)

                except Exception as e:
                    logger.error("Error: " +str(e))
                    statusList = []
            else:
                statusList = []
            if statusList:
                cdbStatusDict[version] = statusList
            statusList = []
        return cdbStatusDict , typeList
    except Exception as e:
        logger.error("Issue building up details for Product Set Summary page on web portal: " +str(e))
        return 1

def getCDBhistoryforDrop(product, drop,excludeList):
    '''
      CDB Status History
    '''
    cdbStatusDict = {}
    isos = []
    statusList = []
    flag = 0
    history = "history"
    product = Product.objects.get(name=product)
    drop = Drop.objects.get(name=drop, release__product=product)
    try:
        isos = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name="productware").order_by('-build_date')
        for iso in isos:
            if iso.current_status:
                isoCurrentStatus = ast.literal_eval(iso.current_status)
                try:
                    statusListTmp, history =  getCDBStatusInfo(cdbStatusDict, history, isoCurrentStatus)
                    versionId = iso.id
                    statusList = []
                    for item in statusListTmp:
                        idType=str(versionId)+"_"+str(item[0])
                        if not idType in excludeList:
                            statusList.append(item)
                except Exception as e:
                    logger.error("Error: " +str(e))
                    statusList = []
            else:
               statusList = []
            if statusList:
                flag = 1
                cdbStatusDict[iso] = statusList[::-1]
            statusList = []
            continue
        return isos, cdbStatusDict, flag
    except Exception as e:
        logger.error("Issue building up details for CDB Summary on web portal: " +str(e))
        return 1

def getPShistoryforDrop(productSet, drop, excludeList):
    '''
    Get Product set Status History

    '''
    cdbStatusDict = {}
    isos = []
    statusList = []
    flag = 0
    history = "history"
    prodSetObj = ProductSet.objects.get(name=productSet)
    prodSetRelObj = ProductSetRelease.objects.filter(productSet=prodSetObj)[0]
    drop = Drop.objects.get(name=drop, release__product=prodSetRelObj.release.product)

    try:
        versions = ProductSetVersion.objects.filter(drop=drop).order_by('-id')
        for version in versions:
            if version.current_status:
                isoCurrentStatus = ast.literal_eval(version.current_status)
                try:
                    statusListTmp, history =  getCDBStatusInfo(cdbStatusDict, history, isoCurrentStatus)
                    versionId = version.id
                    statusList = []
                    for item in statusListTmp:
                        idType=str(versionId)+"_"+str(item[0])
                        if not idType in excludeList:
                            statusList.append(item)
                except Exception as e:
                    logger.error("Error: " +str(e))
                    statusList = []
            else:
                statusList = []
            if statusList:
                flag = 1
                cdbStatusDict[version] = statusList[::-1]
            statusList = []
        return versions, cdbStatusDict, flag
    except Exception as e:
        logger.error("Issue building up details for Product Set Summary on web portal: " +str(e))
        return 1

def getDesignBase(dropid, designBaseList=None):
    """
    Function to return the design base for any given drop
    """
    if (designBaseList == None):
        designBaseList = []
    try:
        designbase = Drop.objects.get(drop=dropid)
        designBaseList.append(designbase)
    except Drop.DoesNotExist:
        # We don't have a design base for this drop, it must be the root
        # drop (or there's a problem with the DB!)
        logger.debug("Last drop in the tree: " + str(dropid))
        return designBaseList
    if (designbase):
        # We have a design base, so now find out what its design base is
        return getDesignBase(designbase.id, designBaseList)
    return designBaseList

def getObsoletedPackages(pkgRevs, drop=None):
    '''
     Getting all Obsoleted Packages Version
    '''
    obsoleteList = []
    drpPkgMap = []
    for pkg in pkgRevs:
        if DropPackageMapping.objects.filter(package_revision=pkg, obsolete=1).exists():
           drpPkgMaps = DropPackageMapping.objects.filter(package_revision=pkg, obsolete=1)
           for drpMap in drpPkgMaps:
              if drop:
                  if drpMap.drop == drop:
                      drpPkgMap = DropPackageMapping.objects.filter(drop=drpMap.drop, package_revision=pkg, obsolete=1)[0]
              else:
                  drpPkgMap = DropPackageMapping.objects.filter(drop=drpMap.drop, package_revision=pkg, obsolete=1)[0]
              if drpPkgMap:
                  if obsoleteList:
                      if not drpPkgMap in obsoleteList:
                          obsoleteList.append(drpPkgMap)
                  else:
                      obsoleteList.append(drpPkgMap)
    return obsoleteList

def createTestwarePom(json,pomVersion):
    '''
    This Function is used to edit a template file

    It takes in a destination directory, a file name within that destination directory
    and a dictionary of variable to change within that file
    '''
    dependency=""
    file=""
    artifactItem=""
    configuration=""
    if (pomVersion=='default'):
        pomTemplate = config.get('TESTWARE', 'pomTemplate')
    else:
        try:
            pomTemplate = config.get('TESTWARE', 'pomTemplate_'+str(pomVersion))
        except:
            logger.error("Invalid POM Version")
            return 1
    for data in json:
        dependencyAdd="<dependency><groupId>GROUPID</groupId><artifactId>ARTIFACTID</artifactId><version>VERSION</version></dependency>"
        dependencyAdd=dependencyAdd.replace("GROUPID",str(data['groupID']))
        dependencyAdd=dependencyAdd.replace("ARTIFACTID",str(data['artifactID']))
        dependencyAdd=dependencyAdd.replace("VERSION",str(data['version']))
        dependency+=dependencyAdd

        fileAdd="<missing>../ARTIFACTID/pom.xml</missing>"
        fileAdd=fileAdd.replace("ARTIFACTID",str(data['artifactID']))
        file=fileAdd

        artifactAdd="<artifactItem><groupId>GROUPID</groupId><artifactId>ARTIFACTID</artifactId><version>VERSION</version><outputDirectory>${extract-dir}</outputDirectory><excludes>**/*.class</excludes><includes>**\/**</includes></artifactItem>"
        artifactAdd=artifactAdd.replace("GROUPID",str(data['groupID']))
        artifactAdd=artifactAdd.replace("ARTIFACTID",str(data['artifactID']))
        artifactAdd=artifactAdd.replace("VERSION",str(data['version']))
        artifactItem+=artifactAdd

        configurationAdd="<execution><id>get-test-jar-ARTIFACTID-VERSION</id><phase>generate-test-resources</phase><goals><goal>get</goal></goals><configuration><groupId>GROUPID</groupId><artifactId>ARTIFACTID</artifactId><version>VERSION</version><destination>${extract-dir}/ARTIFACTID-${project.parent.version}.jar</destination></configuration></execution>"
        configurationAdd=configurationAdd.replace("GROUPID",str(data['groupID']))
        configurationAdd=configurationAdd.replace("ARTIFACTID",str(data['artifactID']))
        configurationAdd=configurationAdd.replace("VERSION",str(data['version']))
        configuration+=configurationAdd

    pomTemplateFH = open(pomTemplate)
    fileContents=pomTemplateFH.read()
    fileContents=fileContents.replace("_DEPENDENCY_",dependency)
    fileContents=fileContents.replace("_FILE_",file)
    fileContents=fileContents.replace("_ARTIFACTITEM_",artifactItem)
    fileContents=fileContents.replace("_CONFIGURATION_",configuration)
    testPom = open('pom.xml', 'w')
    testPom.write(fileContents)
    testPom.close()
    pomTemplateFH.close()
    return


def createTestwareExecutionPom(json,pomVersion,scheduleGroup,scheduleArtifact,scheduleVersion,scheduleName,manualVer,tafRunVer,rest=False):
    '''
    This Function is used to edit a template file

    It takes in a destination directory, a file name within that destination directory
    and a dictionary of variable to change within that file
    '''
    artifactItem=""
    if (pomVersion=='default'):
        pomTemplate = config.get('TESTWARE', 'pomTemplate')
    else:
        try:
            pomTemplate = config.get('TESTWARE', 'pomTemplate_'+str(pomVersion))
        except Exception as e:
            logger.error("Invalid POM Version"+str(e))
            return 1
    for data in json:

        artifactAdd="<artifactItem>\n\t\t\t\t\t\t<groupId>GROUPID</groupId>\n\t\t\t\t\t\t<artifactId>ARTIFACTID</artifactId>\n\t\t\t\t\t\t<version>VERSION</version>\n\t\t\t\t\t</artifactItem>"
        artifactAdd=artifactAdd.replace("GROUPID",str(data['groupID']))
        artifactAdd=artifactAdd.replace("ARTIFACTID",str(data['artifactID']))
        artifactAdd=artifactAdd.replace("VERSION",str(data['version']))
        artifactItem+=artifactAdd

    if manualVer==None:
        manualVer="LATEST"
    manualAdd="<artifactItem>\n\t\t\t\t\t\t<groupId>com.ericsson.cifwk.taf</groupId>\n\t\t\t\t\t\t<artifactId>cdb-manual</artifactId>\n\t\t\t\t\t\t<version>"+str(manualVer)+"</version>\n\t\t\t\t\t</artifactItem>"
    artifactItem+=manualAdd
    if scheduleVersion==None:
        scheduleVersion="LATEST"
    if scheduleArtifact==None:
        scheduleArtifact="cdb-schedule"
    if scheduleGroup==None:
        scheduleGroup="com.ericsson.cifwk.taf"
    scheduleAdd="<schedule>\n\t\t\t\t\t<artifactItem>\n\t\t\t\t\t\t<groupId>"+str(scheduleGroup)+"</groupId>\n\t\t\t\t\t\t<artifactId>"+str(scheduleArtifact)+"</artifactId>\n\t\t\t\t\t\t<version>"+str(scheduleVersion)+"</version>\n\t\t\t\t\t</artifactItem>\n\t\t\t\t\t<schedule_name>"+str(scheduleName)+"</schedule_name>\n\t\t\t\t</schedule>"

    pomTemplateFH = open(pomTemplate)
    fileContents=pomTemplateFH.read()
    fileContents=fileContents.replace("_ARTIFACTITEM_",artifactItem)
    fileContents=fileContents.replace("_SCHEDULE_",scheduleAdd)
    if tafRunVer==None:
        tafRunVer="LATEST"
    fileContents=fileContents.replace("_TAFRUNVER_",tafRunVer)

    if rest == False:
        testPom = open('pom.xml', 'w')
        testPom.write(fileContents)
        testPom.close()
        pomTemplateFH.close()
        return
    else:
        return fileContents

def testwareExecutionlist(json):
    '''
    '''
    artifactItem="<artifactItems>"
    for data in json:
        artifactAdd="<artifactItem><groupId>GROUPID</groupId><artifactId>ARTIFACTID</artifactId><version>VERSION</version></artifactItem>"
        artifactAdd=artifactAdd.replace("GROUPID",str(data['groupID']))
        artifactAdd=artifactAdd.replace("ARTIFACTID",str(data['artifactID']))
        artifactAdd=artifactAdd.replace("VERSION",str(data['version']))
        artifactItem+=artifactAdd
    artifactItem+="</artifactItems>"
    return artifactItem

def testwareMappedlist(json):
    '''
    Process json object into xml object and return
    '''
    artifactItem="<artifactItems>"
    for data in json:
        artifactAdd="<artifactItem><groupId>GROUPID</groupId><artifactId>ARTIFACTID</artifactId><version>VERSION</version></artifactItem>"
        artifactAdd=artifactAdd.replace("GROUPID",str(data['groupID']))
        artifactAdd=artifactAdd.replace("ARTIFACTID",str(data['artifactID']))
        artifactAdd=artifactAdd.replace("VERSION",str(data['version']))
        artifactItem+=artifactAdd
    artifactItem+="</artifactItems>"
    return artifactItem

def updateTestStatus(package,ver,type,phase,state,platform,veLog,team,parentElement,group=None):
    '''
    update test state pt package revision
    allowable phases:
        kgb
        cid
        cdb
    allowable states:
        skipped
        not_started
        in_progress
        passed
        failed
    '''
    if group != None:
       pkgRev = PackageRevision.objects.get(package__name=package, version=ver,groupId=group, m2type=type)
    elif platform == "None":
        pkgRev = PackageRevision.objects.get(package__name=package, version=ver, m2type=type)
    else:
        pkgRev = PackageRevision.objects.get(package__name=package, version=ver, platform=platform, m2type=type)
    if phase == "kgb":
        if team != None and parentElement != None:
            try:
                parentElementComp = Component.objects.get(element=parentElement, deprecated=0)
                teamComp = Component.objects.get(element=team, parent=parentElementComp, deprecated=0)
                pkgRev.team_running_kgb = teamComp
            except Exception as e:
                if Component.objects.filter(element=parentElement, deprecated=1).exists():
                    logger.debug("parentElement "+ str(parentElement)+" has been deprecated")
                elif Component.objects.filter(element=team, parent__element=parentElement, deprecated=1).exists():
                    logger.debug("Team "+team+" in parentElement "+ str(parentElement)+" has been deprecated")
                else:
                    logger.debug("Team "+team+" in parentElement "+ str(parentElement)+" does not exist")
                pkgRev.team_running_kgb = None
        else:
            pkgRev.team_running_kgb = None
        pkgRev.kgb_test=state
    elif phase == "cid":
        pkgRev.cid_test=state
    elif phase == "cdb":
        pkgRev.cdb_test=state
    else:
        logger.error("invalid test phase: ")
        return 1
    logger.info("Updating test status" +str(package) +" "+str(ver) +" state:"+str(state)+" phase:"+str(phase))
    pkgRev.save()
    if state == "in_progress":
        now = datetime.now()
        testsInProgressObj,created=TestsInProgress.objects.get_or_create(package_revision=pkgRev,phase=phase)
        testsInProgressObj.datestarted=now
        testsInProgressObj.veLog=veLog
        testsInProgressObj.save()
    else:
        if TestsInProgress.objects.filter(package_revision=pkgRev,phase=phase).exists():
            TestsInProgress.objects.get(package_revision=pkgRev,phase=phase).delete()
    #cleanup any tests in progress more than X hours
    maxTTL = int(config.get("FEM", "maxTTL"))
    for phasex in ["kgb","cid","cdb"]:
        maxTTL = int(config.get("TESTWARE", "maxTTL_"+phasex))
        timeNow = datetime.now()
        timeMinusTTL = datetime.now() - timedelta(hours=maxTTL)
        outOfDate=TestsInProgress.objects.exclude(datestarted__range=(timeMinusTTL, timeNow))
        for item in outOfDate:
            if item.phase==phasex:
                logger.info("Package : "+str(item.package_revision.package.name) +":"+str(item.package_revision.version) +" too long in testing: Updating test status to failed")
                outOfDatePkgObj=PackageRevision.objects.get(id=item.package_revision.id)
                if phasex == "kgb":
                    outOfDatePkgObj.kgb_test="failed"
                elif phasex == "cid":
                    outOfDatePkgObj.cid_test="failed"
                elif phasex == "cdb":
                    outOfDatePkgObj.cdb_test="failed"
                outOfDatePkgObj.save()
                outOfDate.delete()

def getTestwareMapInfo(package,isoArtifact,isoVersion,packageList):
    '''
    Getting the information for the mapping
    '''
    testware = []
    if packageList != None:
        packageList = packageList.split(' ')
        try:
            testware=packageTestwareMapUnique(packageList)
        except Exception as e:
            logger.error("Error: Running packageTestwareMapUnique Function to return testawre with Package List: " +str(packageList)+ " Error: " +str(e))
    elif isoVersion == None:
        try:
            testware=packageTestwareMap(package,'NA')
        except Exception as e:
            logger.error("Error: Running packageTestwareMap Function to return testawre with Package: " +str(package)+ " Error: " +str(e))
    else:
        packages=[]
        try:
            if ISObuild.objects.filter(version=isoVersion, mediaArtifact__name=isoArtifact).exists():
                isoRevision = ISObuild.objects.get(version=isoVersion, mediaArtifact__name=isoArtifact)
            else:
                logger.error("Error: Could not find ISO mapping for isoVersion: " +str(isoVersion)+ " isoArtifact: " +str(isoArtifact))
        except Exception as e:
            logger.error("Error: getting ISO Build info: " +str(e))

        try:
            if ISObuildMapping.objects.filter(iso=isoRevision).exists():
                isoRevMapping = ISObuildMapping.objects.filter(iso=isoRevision)
                for isoPackage in isoRevMapping:
                    packages.append(str(isoPackage.package_revision.package.name)+"::"+str(isoPackage.package_revision.version))
        except Exception as e:
            logger.error("Error: Filtering on ISO Build Mappings: " +str(e))
        try:
            testware=packageTestwareMapUnique(packages, isoVersion)
        except Exception as e:
            logger.error("Error: Running packageTestwareMapUnique to return testware function on packages: " +str(packages)+ " with ISO Version: " +str(isoVersion)+ " Error: " +str(e))
    return testware


def getTestwareMapping(product,artifact):
    '''
    Return mapping by testware/package
    '''
    mapping = []
    packageObj = None
    if TestwareArtifact.objects.filter(name=artifact).exists():
        testwareArtifact = TestwareArtifact.objects.get(name=artifact)
        pkgList,allCount = getPackagesBasedOnProduct(product)
        for pkg in pkgList:
            if TestwarePackageMapping.objects.filter(package=pkg,testware_artifact=testwareArtifact).exists():
                mapping.append(TestwarePackageMapping.objects.get(package=pkg,testware_artifact=testwareArtifact))
    elif Package.objects.filter(name=artifact).exists():
        package = Package.objects.get(name=artifact)
        mapping = list(TestwarePackageMapping.objects.filter(package=package))
        packageObj = artifact
    else:
        logger.error("No associated artifact")
    return mapping,packageObj


def getTestwareMap(product,pkgList):
    '''
    Get Testware package mapping per product
    '''
    testwareMapping = []
    try:
        for pkg in pkgList:
            testwareMapping = testwareMapping + list(TestwarePackageMapping.objects.filter(package=pkg))
    except Exception as e:
        logger.error("No Testware Mappings associated with " + str(product) + " : " +str(e))
    return testwareMapping


def getTestwareByProduct(product):
    '''
    Retrieve Testware Artifacts for particular product
    '''
    pkgList,allCount = getPackagesBasedOnProduct(product)
    testwareArtifacts = []
    testwareRevArtifacts = []
    try:
        for pkg in pkgList:
            testware = TestwarePackageMapping.objects.filter(package=pkg)
            for testwareArtifact in testware:
                if testwareArtifact.testware_artifact not in testwareArtifacts:
                    testwareArtifacts.append(testwareArtifact.testware_artifact)
        for artifact in testwareArtifacts:
            if TestwareRevision.objects.filter(testware_artifact=artifact,obsolete=False).exists():
                testwareRev = TestwareRevision.objects.filter(testware_artifact=artifact,obsolete=False).order_by('-date_created')[0]
            else:
                testwareRev = TestwareRevision.objects.filter(testware_artifact=artifact).order_by('-date_created')[0]
            if testwareRev not in testwareRevArtifacts:
                testwareRevArtifacts.append(testwareRev)
    except Exception as e:
        logger.error("No Testware associated with " + str(product) + " : " +str(e))
    return testwareRevArtifacts

def getAllTestware(product=None,urlCheck=None):
    '''
    Retrieve latest version of all Testware Artifacts
    '''
    testwareArtifacts = []
    testwareRevArtifacts = []
    nexusUrlPublic = config.get("CIFWK", "nexus_public_url")
    nexusUrl = config.get("CIFWK", "nexus_url")
    found = False
    try:
        if product is not None:
            testwareArtifacts = ProductPackageMapping.objects.only('package__name').values('package__name').filter(product__name=product, package__hide=0, package__testware=1)
        else:
            testwareArtifacts = TestwareArtifact.objects.only('name').values('name').all()
        artifactRevisions = PackageRevision.objects.only('package__name','arm_repo').values('package__name','arm_repo').annotate(Count('package__name')).filter(package__name__in=testwareArtifacts)
        testwareRevField = ('groupId', 'testware_artifact__name', 'version', 'date_created', 'execution_groupId','execution_artifactId','execution_version','validTestPom')
        for artifact in testwareArtifacts:
            testwareRevItem = {}
            try:
                if product is not None:
                    testwareRev = TestwareRevision.objects.only(testwareRevField).values(*testwareRevField).filter(testware_artifact__name=artifact['package__name'],validTestPom=True).order_by('-date_created')[0]
                else:
                    testwareRev = TestwareRevision.objects.only(testwareRevField).values(*testwareRevField).filter(testware_artifact__name=artifact['name'],validTestPom=True).order_by('-date_created')[0]
            except:
                testwareRev = None

            if testwareRev:
                testwareRevItem['groupId'] = testwareRev['groupId']
                testwareRevItem['artifactId'] = testwareRev['testware_artifact__name']
                testwareRevItem['version'] = testwareRev['version']
                testwareRevItem['dateCreated'] = testwareRev['date_created']
                testwareRevItem['executionGroupId'] = testwareRev['execution_groupId']
                testwareRevItem['executionArtifactId'] = testwareRev['execution_artifactId']
                testwareRevItem['executionVersion'] = testwareRev['execution_version']
                artifactArmRepo = None
                for art in artifactRevisions:
                    if testwareRev['testware_artifact__name'] == art['package__name']:
                        artifactArmRepo = art['arm_repo']
                testwareRevItem['armRepo'] = artifactArmRepo

                if urlCheck:
                    if artifactArmRepo != None:
                        newNexusURL = nexusUrl + "/" + artifactArmRepo
                    else:
                        newNexusURL = nexusUrlPublic
                    updatedNexusURL = newNexusURL + "/" + str(testwareRev['execution_groupId'].replace(".","/")) + "/" + str(testwareRev['execution_artifactId']) + "/" + str(testwareRev['execution_version']) + "/" + str(testwareRev['execution_artifactId']) + "-" + str(testwareRev['execution_version']) + ".pom"
                    if not checkIfURLIsActive(updatedNexusURL):
                        TestwareRevision.objects.filter(execution_groupId=testwareRev['execution_groupId'],execution_artifactId=testwareRev['execution_artifactId'],version=testwareRev['execution_version']).update(validTestPom=False)
                        found = True
                    if found:
                        testwareRevisions = TestwareRevision.objects.filter(execution_groupId=testwareRev['execution_groupId'],execution_artifactId=testwareRev['execution_artifactId'])
                        if testwareRevisions:
                            for testwareRevision in testwareRevisions:
                                checkAgainNexusURL = newNexusURL + "/" + str(testwareRevision.execution_groupId.replace(".","/")) + "/" + str(testwareRevision.execution_artifactId) + "/" + str(testwareRevision.execution_version) + "/" + str(testwareRevision.execution_artifactId) + "-" + str(testwareRevision.execution_version) + ".pom"
                                if not checkIfURLIsActive(checkAgainNexusURL):
                                    testwareRevision.validTestPom=False
                                    testwareRevision.save()
                        found = False
                testwareRevArtifacts.append(testwareRevItem)
    except Exception as e:
        logger.error("No Testware Artifacts: " + str(e))
    return testwareRevArtifacts

def checkIfURLIsActive(url):
    '''
    The checkIfURLIsActive function checks if a url is active for a given url and returns a boolean value
    '''
    try:
        urllib2.urlopen(url)
        return True
    except urllib2.URLError:
        return False

def getUnMappedTestware():
    '''
    Retrieve Unmapped Testware Artifacts
    '''
    unMappedTestware = []
    testwareArtifact = TestwareArtifact.objects.all()
    try:
        for artifact in testwareArtifact:
            if not TestwarePackageMapping.objects.filter(testware_artifact=artifact).exists():
                if TestwareRevision.objects.filter(testware_artifact=artifact,obsolete=False).exists():
                    testwareRev = TestwareRevision.objects.filter(testware_artifact=artifact,obsolete=False).order_by('-date_created')[0]
                else:
                    testwareRev = TestwareRevision.objects.filter(testware_artifact=artifact).order_by('-date_created')[0]
                if testwareRev not in unMappedTestware:
                    unMappedTestware.append(testwareRev)
    except Exception as e:
         logger.error("No Unmapped Testware: " +str(e))
    return unMappedTestware

def getMappedPackages(pkgs):
    '''
     Generate list of packages that are mapped to testware
    '''
    pkgsList = []
    packageList = []
    for p in pkgs:
        if TestwarePackageMapping.objects.filter(package=p).exists():
             pkgsList.append(p)
    packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgsList]
    packageList = sorted(packageList, key=lambda tup: tup[1].lower())
    return packageList

def getUnMappedPackages(pkgs):
    '''
    Generate list of packages that are not mapped to testware
    '''

    pkgsList = []
    packageList = []
    for p in pkgs:
        if not TestwarePackageMapping.objects.filter(package=p).exists():
            pkgsList.append(p)
    packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgsList]
    packageList = sorted(packageList, key=lambda tup: tup[1].lower())
    return packageList

def populateTestwareChoices():
    '''
    Generate list of products and options for selecting testware artifacts
    '''
    choices = [('UnMapped','UnMapped')]
    products = Product.objects.all()
    for product in products:
        if product.name != "None":
            choices = choices + [(product.name, unicode(product.name))]
    choices = tuple(choices)
    return choices


def getPackageChoices():
    '''
    Generate options for selecting packages
    '''
    choices = [('All','All')]
    choices = choices + [('Delivered','Delivered')]
    choices = choices + [('AllDelivered','AllDelivered')]
    choices = choices + [('UnDelivered','UnDelivered')]
    choices = choices + [('Mapped','Mapped')]
    choices = choices + [('UnMapped','UnMapped')]
    choices = choices + [('AllMapped','AllMapped')]
    choices = choices + [('AllUnMapped','AllUnMapped')]
    choices = tuple(choices)
    return choices


def generateAllTestware(pkgList):
    packageList = []
    testwareArtifactList = []
    testwareArtList = TestwareArtifact.objects.all()
    testwareArtifactList = testwareArtifactList + [(artifact.name, unicode(artifact.name)) for artifact in testwareArtList]
    testwareArtifactList = sorted(testwareArtifactList, key=lambda tup: tup[1].lower())
    packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgList]
    packageList = sorted(packageList, key=lambda tup: tup[1].lower())
    options = []
    state = True
    return testwareArtifactList, packageList, options, state




def generateTestwareArtifactList(product,options,packageList):
    '''
    Generate list of testware artifacts depending on selected options
    '''
    testwareArtList = []
    testwareArtifactList = []
    testware = []
    if not options:
        options = ['UnMapped', product.name]
    for option in options:
        if option == "UnMapped":
            testwareArtifact = TestwareArtifact.objects.all()
            for artifact in testwareArtifact:
                if not TestwarePackageMapping.objects.filter(testware_artifact=artifact).exists():
                    testwareArtList.append(artifact)
        else:
            productObj = Product.objects.get(name=option)
            if product.name == productObj.name:
                pkgList = packageList
            else:
                pkgList,allCount = getPackagesBasedOnProduct(productObj)
            for pkg in pkgList:
                if TestwarePackageMapping.objects.filter(package=pkg).exists:
                    testware = testware + list(TestwarePackageMapping.objects.filter(package=pkg))
            for testwareArtifact in testware:
                if testwareArtifact.testware_artifact not in testwareArtList:
                    testwareArtList.append(testwareArtifact.testware_artifact)
    testwareArtifactList = testwareArtifactList + [(artifact.name, unicode(artifact.name)) for artifact in testwareArtList]
    testwareArtifactList = sorted(testwareArtifactList, key=lambda tup: tup[1].lower())
    return testwareArtifactList, options


def generateTestwareMappingForms(product,pkgList,options):
    '''
    Generate package and testware artifact list for add testware form
    '''
    packageList = []
    testwareArtifactList, options = generateTestwareArtifactList(product,options,pkgList)
    packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgList]
    packageList = sorted(packageList, key=lambda tup: tup[1].lower())
    return testwareArtifactList, packageList, options




def packageTestwareMap(package,version,cdb=None):
    '''
    Returns testware mapped to package
    '''
    data = ""
    data1 = ""
    testwareRev = None
    if TestwarePackageMapping.objects.filter(package__name=package).exists():
        all = TestwarePackageMapping.objects.filter(package__name=package)
        for testwareMap in all:
            if cdb != None:
                if TestwareRevision.objects.filter(testware_artifact_id=testwareMap.testware_artifact,obsolete=False,cdb_status=1).exists():
                    try:
                        testwareRev=TestwareRevision.objects.filter(testware_artifact_id=testwareMap.testware_artifact,obsolete=False,cdb_status=1).order_by('-date_created')[:1][0]
                    except Exception as e:
                        logger.error("Error: Getting TestwareRevision object when testware Artifact is: " +str(testwareMap.testware_artifact)+ " obsolete is false and cdb status is 1, Error: " +str(e))
                else:
                    logger.error("Error: Getting TestwareRevision object when testware Artifact is: " +str(testwareMap.testware_artifact)+ " obsolete is false and cdb status is 1")

            else:
                if TestwareRevision.objects.filter(testware_artifact_id=testwareMap.testware_artifact,obsolete=False,kgb_status=1).exists():
                    try:
                        testwareRev=TestwareRevision.objects.filter(testware_artifact_id=testwareMap.testware_artifact,obsolete=False,kgb_status=1).order_by('-date_created')[:1][0]
                    except Exception as e:
                        logger.error("Error: Getting TestwareRevision object when testware Artifact is: " +str(testwareMap.testware_artifact)+ " obsolete is false and kgb status is 1, Error: " +str(e))
                else:
                    logger.error("Error: Getting TestwareRevision object when testware Artifact is: " +str(testwareMap.testware_artifact)+ " obsolete is false and kgb status is 1")
            if testwareRev:
                data1=testwareRev.testware_artifact.name+"-VER-"+testwareRev.version
                data = data +"-BREAK-"+ data1
    ret=data[7:]
    return ret

def packageTestwareMapUnique(packageList,iso=None):
    '''
     For CDB and multiple KGB testware return
    '''
    testwareList = []
    data = []
    for item in packageList :
        package,ver = item.split('::')
        if iso != None:
            try:
                data = packageTestwareMap(package,ver,iso)
                if not data:
                    logger.debug("Error: Running packageTestwareMap to return testware data on package: " +str(package)+ " Version: " +str(ver)+ " and ISO: " +str(iso))
            except Exception as e:
                logger.error("Error: Running packageTestwareMap to return testware data on package: " +str(package)+ " Version: " +str(ver)+ " and ISO: " +str(iso) + " Error: " +str(e))
        else:
            try:
                data = packageTestwareMap(package,ver)
                if not data:
                    logger.debug("Error: Running packageTestwareMap to return testware data on with package: " +str(package)+ " Version: " +str(ver))
            except Exception as e:
                logger.error("Error: Running packageTestwareMap to return testware data on with package: " +str(package)+ " Version: " +str(ver)+ " Error: " +str(e))
        if data != "":
            testwareList.append(data)
    testwareString='-BREAK-'.join(testwareList)
    testwareListNew=testwareString.split('-BREAK-')
    testwareListUnique=set(testwareListNew)
    ret='-BREAK-'.join(testwareListUnique)
    return ret

def getUnDeliveredPackages(pkgs):
    '''
     Generate list of packages that are not Delivered to any product/drop
    '''
    pkgsList = []
    packageList = []
    for p in pkgs:
        if not DropPackageMapping.objects.filter(package_revision__package=p).exists():
            pkgsList.append(p)
    packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgsList]
    packageList = sorted(packageList, key=lambda tup: tup[1].lower())
    return packageList

def getAllDeliveredPackages(pkgs):
    '''
    Generate list of packages that are Delivered to a product/drop
    '''
    pkgsList = []
    packageList = []
    for p in pkgs:
        if DropPackageMapping.objects.filter(package_revision__package=p, released=1).exists():
            pkgsList.append(p)
    packageList = packageList + [(pkg.name, unicode(pkg.name)) for pkg in pkgsList]
    packageList = sorted(packageList, key=lambda tup: tup[1].lower())
    return packageList



def packagesForIntegratonPhase(drop,product):
    '''
    Returns a list of packages that have passed KGB testing and not yet included in iso
    '''
    if drop == None:
        drop = "latest"
    if product == None:
        product = "TOR"
    if drop == "latest":
        drops = Drop.objects.filter(release__product__name=product, correctionalDrop=False).exclude(release__name__icontains="test")
        dropList = list(drops)
        #Sort the drops in correct order
        dropList.sort(key=lambda drop:LooseVersion(drop.name))
        dropList.reverse()
        integrationDropId=dropList[0].id
    else:
        dropObj = Drop.objects.get(release__product__name=product,name=drop)
        integrationDropId=dropObj.id
    packages = getPackageBaseline(dropObj)
    packageList=[]
    for item in packages:
        if item.package_revision.kgb_test == 'passed' :
            if not ISObuildMapping.objects.filter(package_revision=item.package_revision,drop=integrationDropId).exists():
                packageList.append(str(item.package_revision.package.name)+":"+str(item.package_revision.version))
    packegesForIntegration=','.join(packageList)
    return packegesForIntegration


def sendPackageMail(packageName):
    #sends an e-mail to JIRA administrators once new package has been created
    mailHeader = "New Package "+packageName+" has been created."
    mailContent = "To JIRA Admins,\n\nThe following package has been added to the CI Portal\nName: "+packageName+"\n\n\nKind Regards,\nCI Portal Admin"
    emailRecipients = None
    if developmentServer == 1:
        try:
            emailRecipients = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", "JIRA_ADMINS"))
        except Exception as e:
            emailRecipients = None
            logger.error("Email Recipient JIRA_ADMINS not available for Development Server" + str(e))
    else:
        try:
            emailRecipients = NonProductEmail.objects.filter(area="JIRA_ADMINS")
        except Exception as e:
            emailRecipients = None
            logger.error("Email Recipient JIRA_ADMINS not available in DB" + str(e))
    toEmail = []
    if emailRecipients != None:
        for delEmail in emailRecipients:
            if developmentServer == 1:
                toEmail.append(delEmail)
            else:
                toEmail.append(delEmail.email)
    send_mail(mailHeader,mailContent,"PDLCIAXISC@pdl.internal.ericsson.com",toEmail,fail_silently=False)


def isIsoBomUrl(isoBuild):
    for cdb in isoBuild['currentCDBStatuses']:
        if cdb['cdb_type_name'] == 'MTE-P' and cdb['status'] == "passed":
            return True

    return False

def setIsoBuildValues(productName, nexusHubUrl, nexusLocalUrl, cdbTypesMap, testResultMap, isoBuild):
    isoBuild['rstate'] = convertVersionToRState(isoBuild['version'])
    isoBuild['groupIdForUrl'] = str(isoBuild['groupId'].replace(".", "/"))
    isoBuild['hubIsoUrl'] = str(nexusHubUrl + "/" + isoBuild['arm_repo'] + "/" + isoBuild['groupIdForUrl'])
    isoBuild['localIsoUrl'] = str(nexusLocalUrl)
    isoBuild['currentCDBStatuses'] = getIsoBuildCurrentCDBStatuses(isoBuild['current_status'], productName, isoBuild['drop__name'], isoBuild['version'], cdbTypesMap, testResultMap)
    isoBuild['isoBomUrl'] = isIsoBomUrl(isoBuild)

def getProductSize(artifactName, version):
    '''
    Getting Media Artifact build date and size
    '''
    statusCode = 200
    try:
        valuesFields = "build_date", "size",
        mediaArtifactVersion = ISObuild.objects.only(valuesFields).values(*valuesFields).get(artifactId=artifactName, version=version)
        mediaArtifactVersionData = { "build_date" : str(mediaArtifactVersion['build_date']), "size_in_byte" : mediaArtifactVersion['size']}
    except Exception as e:
        errMsg = "Issue getting Media Artifact Data: "+str(e)
        logger.error(errMsg)
        statusCode = 404
        mediaArtifactVersionData = { "error" : errMsg}
    return mediaArtifactVersionData, statusCode

def getMediaArtifactVersionsInformation(productId, productName, name, mediaArtifactName, isRelease = False):
    '''
    Getting Media Artifact Versions Information
    '''
    deliveryData = None
    drop = None
    product = None
    mediaArtifactVersions = []
    prodTWmediaMapProductData = []
    prodTWmediaMapTestwareData = []
    mediaIsoBuildIds = []
    testIsoBuildIds = []
    isoBuildIds = []
    categoriesList = set()
    athloneProxyProducts = ast.literal_eval(config.get("CIFWK", "athlone_proxy_products"))

    try:
        mediaArtifactVersionFields = ('id','mediaArtifact__name','mediaArtifact__mediaType','drop__release__product__name','drop__name','version','build_date','overall_status','overall_status__state','arm_repo','groupId','current_status', 'size', 'active', 'mediaArtifact__category__name')
        if isRelease:
            mediaArtifactVersions = ISObuild.objects.filter(drop__release__name=name, drop__release__product__id=productId).order_by('-build_date').only(mediaArtifactVersionFields).values(*mediaArtifactVersionFields)
            if len(mediaArtifactVersions) > 20:
                mediaArtifactVersions = mediaArtifactVersions[:20]
        else:
            mediaArtifactVersions = ISObuild.objects.filter(drop__name=name, drop__release__product__id=productId).order_by('-build_date').only(mediaArtifactVersionFields).values(*mediaArtifactVersionFields)

        nexusHubUrl = config.get('CIFWK', 'nexus_url')
        cdbTypesMap = {}
        cdbtypeFields = ('id','name','sort_order')
        cdbtypeObjs = list(CDBTypes.objects.only(cdbtypeFields).values(*cdbtypeFields).all())
        testResultMap = {}
        for cdbTypeObj in cdbtypeObjs:
            cdbTypesMap[cdbTypeObj['id']] = cdbTypeObj
        testResultMap = getIsoBuildtestResultsMap(mediaArtifactVersions)
        for isoBuild in mediaArtifactVersions:
            if isoBuild['mediaArtifact__category__name'] == "productware":
                mediaIsoBuildIds.append(isoBuild['id'])
            elif isoBuild['mediaArtifact__category__name'] == "testware":
                testIsoBuildIds.append(isoBuild['id'])
            nexusLocalUrl = getAthloneProxyProductsUrl(isoBuild['drop__release__product__name'], isoBuild['arm_repo'], isoBuild['groupId'], athloneProxyProducts)
            setIsoBuildValues(productName, nexusHubUrl, nexusLocalUrl, cdbTypesMap, testResultMap, isoBuild)
            isoBuildIds.append(isoBuild['id'])
            categoriesList.add(isoBuild['mediaArtifact__category__name'])
        if not "productware" in categoriesList:
            categoriesList.add("productware")
    except Exception as e:
        logger.error("Error: Getting media Artifact Information " + str(e))

    try:
        # To Get Obsolete and Delivery Data
        drpMediaMapFields = 'mediaArtifactVersion__id', 'drop__release__productsetrelease__productSet__name', 'drop__name', 'obsolete', 'released'
        deliveryData = DropMediaArtifactMapping.objects.filter(mediaArtifactVersion__id__in=isoBuildIds).only(drpMediaMapFields).values(*drpMediaMapFields)
    except Exception as e:
        logger.error("Error: Getting Obsolete or Delivery Data" + str(e))

    try:
        # To Get Media Versions
        prodTWmediaMapFields = ('productIsoVersion__id','testwareIsoVersion__mediaArtifact__name','testwareIsoVersion__version')
        prodTWmediaMapProductData = prodTWmediaMapProductData + list(ProductTestwareMediaMapping.objects.filter(productIsoVersion__id__in=mediaIsoBuildIds).only(prodTWmediaMapFields).values(*prodTWmediaMapFields))
        if testIsoBuildIds:
            prodTWmediaMapFields = ('testwareIsoVersion__id','productIsoVersion__mediaArtifact__name','productIsoVersion__version')
            prodTWmediaMapTestwareData = prodTWmediaMapTestwareData + list(ProductTestwareMediaMapping.objects.filter(testwareIsoVersion__id__in=testIsoBuildIds).only(prodTWmediaMapFields).values(*prodTWmediaMapFields))
    except Exception as e:
        logger.error("Error: Getting Media Artifact Versions " + str(e))
    return mediaArtifactVersions, deliveryData, prodTWmediaMapProductData,  prodTWmediaMapTestwareData, categoriesList

def obsolete(DPMid, package, platform, signum, reason, drop):
    '''
    Obsoleting of Package Revision from a Drop
    '''
    error = ""
    pkgRevDPMprev = drpPkgMap = pkgRevDPM = None
    try:
        # Get query for the drop package mapping selected
        pkgRevDPM = DropPackageMapping.objects.only('id', 'drop__id', 'package_revision__package__name', 'package_revision__package__id','package_revision__groupId','obsolete','released','drop__actual_release_date', 'package_revision__version', 'package_revision__date_created', 'delivery_info', 'deliverer_mail', 'deliverer_name', 'drop__release__product__name', 'drop__release__name', 'package_revision__kgb_test').get(id=DPMid)
        #This filter query is needed to check if the Drop Package Mapping is in a frozen drop for the if statement.
        drpPkgMap = DropPackageMapping.objects.only('id').filter(id=DPMid, drop__actual_release_date__lte=datetime.now()).values('id')
        # If statement for dpm to check if it's empty,
        # to check if the pkgRevDPM obsolete is not True
        # and to make sure the date info is not empty else this will return the obsolete error page
        if not len(drpPkgMap) == 0 and pkgRevDPM.obsolete != 1 and pkgRevDPM.drop.actual_release_date != None:
            # This is for when dpm filter comes back not 0 meaning the Package Revision is in a frozen drop and cannot be Obsoleted
            logger.error("Error Package Revision Version in Frozen Drop")
            error = "error"
            return error
    except Exception as e:
        logger.error("Issue getting  DropPackageMapping object: " + str(e) )
        error = "error"
        return error

    productName = pkgRevDPM.drop.release.product.name
    pkgName = str(pkgRevDPM.package_revision.package.name)
    version = str(pkgRevDPM.package_revision.version)
    obsoleteTime = datetime.now()

    #Access name and email of package deliverer
    delivererMail, delivererName = parseDetails(pkgRevDPM.delivery_info)

    # Add in the info into the DB for Obsolete Info
    obInfoObj,created = ObsoleteInfo.objects.get_or_create(dpm_id=pkgRevDPM.id,signum=signum,reason=reason,time_obsoleted=obsoleteTime)
    obInfoObj.save()

    # Changing the Package Revision Version status to obsolete and set released to False then saving
    pkgRevDPM.obsolete = True
    pkgRevDPM.released = False
    if not pkgRevDPM.deliverer_mail:
        pkgRevDPM.deliverer_mail = delivererMail
    else:
        delivererMail = pkgRevDPM.deliverer_mail
    if not pkgRevDPM.deliverer_name:
        pkgRevDPM.deliverer_name = delivererName
    else:
        delivererName = pkgRevDPM.deliverer_name
    pkgRevDPM.save()
    pkgRevDPMpkgId = pkgRevDPM.package_revision.package.id
    pkgRevDPMdropId = pkgRevDPM.drop.id
    # Check if we have any package revisions to revert back to
    if platform == "None":
        if DropPackageMapping.objects.filter(package_revision__package__id=pkgRevDPMpkgId,drop__id=pkgRevDPMdropId, obsolete=0).exists():
            pkgRevDPMprev = DropPackageMapping.objects.only('released').filter(package_revision__package__id=pkgRevDPMpkgId,drop__id=pkgRevDPMdropId, obsolete=0).order_by('-id')[0]
    else:
        if DropPackageMapping.objects.filter(package_revision__package__id=pkgRevDPMpkgId, package_revision__platform=platform, drop=pkgRevDPMdropId, obsolete=0).exists():
            pkgRevDPMprev = DropPackageMapping.objects.only('released').filter(package_revision__package__id=pkgRevDPMpkgId, package_revision__platform=platform, drop=pkgRevDPMdropId, obsolete=0).order_by('-id')[0]
    # Setting release to true
    if pkgRevDPMprev:
        pkgRevDPMprev.released = True
        pkgRevDPMprev.save()
    # sends automated emails if no error has been encountered
    if error != 'error':
        sendEiffelObsoleteMessage(pkgRevDPM, pkgRevDPMpkgId, drop, productName, pkgName, version)
        sendObsoleteEmail(pkgRevDPM, pkgName, version, drop, productName, signum, reason, delivererMail, delivererName)
    return error

def sendEiffelObsoleteMessage(pkgRevDPM, pkgRevDPMpkgId, drop, productName, pkgName, version):
    '''
    For sending Eiffel Message when Artifacts are Obsolete
    '''
    mbHost = config.get('MESSAGE_BUS', 'eiffelHostname')
    mbExchange =  config.get('MESSAGE_BUS', 'eiffelExchangeName')
    mbDomain =  config.get('MESSAGE_BUS', 'eiffelDomainName')
    mbUser = config.get('MESSAGE_BUS', 'mbFunctionalUser')
    mbPwd = config.get('MESSAGE_BUS', 'mbFunctionalUserPassword')
    java =  config.get('MESSAGE_BUS', 'javaLocation')
    try:
        if pkgRevDPM.package_revision.team_running_kgb:
            teamObj = pkgRevDPM.package_revision.team_running_kgb
            team = teamObj.element
            parentElement = teamObj.parent.element
        else:
            team,parentElement = getTeamParentElement(pkgName)
        kgbStatus = pkgRevDPM.package_revision.kgb_test

        jsonInput = {
                    "confidenceLevel":"OBSOLETED",
                    "confidenceLevelState":"SUCCESS",
                    "drop":str(drop),
                    "product":str(productName),
                    "release":str(pkgRevDPM.drop.release.name),
                    "artifactId":str(pkgName),
                    "groupId":str(pkgRevDPM.package_revision.groupId),
                    "version":str(version),
                    "team":str(team),
                    "ra":str(parentElement),
                    "kgbStatus":str(kgbStatus),
                    "messageBusHost":mbHost,
                    "messageBusExchange":mbExchange,
                    "messageBusDomain":mbDomain,
                    "messageBusUser": mbUser,
                    "messageBusPassword": mbPwd,
                    "messageType":"clme"
                    }
        dateCreated = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        logger.info("####### Sending eiffelObsoleteMessage to Message bus ########")
        logger.info(jsonInput)
        sendCLME = subprocess.check_call(java + " -jar /proj/lciadm100/cifwk/latest/lib/3pp/eiffelEventSender/cli-event-sender.jar '"+json.dumps(jsonInput)+"' 2>> /proj/lciadm100/cifwk/logs/messagebus/eiffelObsoleteMessage/" + dateCreated, shell=True,cwd="/tmp")
        if not sendCLME == 0:
           logger.debug("Issue sending eiffel message")
    except Exception as e:
        logger.error("Issue sending eiffel message: " + str(e))

def parseDetails(deliveryInfo):
    '''
    Parsing of deliverer details from delivery_info in the DropPackageMapping table
    '''
    try:
       email = deliveryInfo[deliveryInfo.find('(')+1:deliveryInfo.find(')')]
       rawName = email[:email.find('@')]

       if '.' in rawName:
          i = rawName.find('.')
          name = (rawName[:i] + ' ' + rawName[i+1:]).capitalize()
       else:
          name = rawName

       return email, name
    except Excepion as e:
       logger.error("Error collecting package deliverer details: " + str(e))

def sendObsoleteEmail(pkgRevDPM, pkgName, version, drop, productName, signum, reason, delivererMail, delivererName):
    '''
    For sendng the Obsolete Email for Artifact
    '''
    #Automated e-mail for CI Execution team. Sent in the event an RPM is made obsolete.
    productEmail = None
    if developmentServer == 1:
        try:
            productEmail = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", str(productName).upper()))
        except Exception as e:
            logger.error("Email Recipient for Obsoletion is not available for development Server: " + str(e))
    else:
        try:
            productEmail = ProductEmail.objects.filter(product__name=productName)
        except Exception as e:
            logger.error("Email Recipient for Obsoletion is not available" + str(e))
    deliveryEmail = []
    if productEmail != None:
        for delEmail in productEmail:
            if developmentServer == 1:
                deliveryEmail.append(delEmail)
            else:
                deliveryEmail.append(delEmail.email)

    emailHeader = str(pkgName) + ", " + str(version) +  " made obsolete."
    dateCreated = str(pkgRevDPM.package_revision.date_created)
    #Content of automated e-mails. Contains RPM information and contact details
    #For CI Execution team
    emailContentAll = '''This is an automated Delivery mail from the CI Framework
    \nTo all CI Execution team members,\n\nThe following package has been made obsolete:
    \nName:\t\t''' + pkgName + '''
    \nDrop:\t\t''' + productName + ''' ''' + drop + '''
    \nVersion:\t''' + version + '''
    \nCreated:\t''' + dateCreated + '''
    \n\nThis package was delivered by: \n''' + delivererMail + '''
    \nThis package was made obsolete by: \n''' + str(signum) +'''
    \nThe reason for obsoletion is as follows: \n"''' + str(reason) + '''"'''

    #For Package deliverer
    emailContentCreator = '''This is an automated Delivery mail from the CI Framework
    \nTo ''' + delivererName + ''',\n\nYour package has been made obsolete:
    \nName:\t\t''' + pkgName + '''
    \nDrop:\t\t''' + productName + ''' ''' + drop + '''
    \nVersion:\t''' + version + '''
    \nCreated:\t''' + dateCreated + '''
    \nThis package was made obsolete by: \n''' + str(signum) +'''
    \nThe reason for obsoletion is as follows: \n"''' + str(reason) + '''"'''

    #For Package obsoletor
    emailContentObsoletor = '''This is an automated Delivery mail from the CI Framework
    \nTo ''' + str(signum) + ''',\n\nYou have succesfully obsoleted this package:
    \nName:\t\t''' + pkgName + '''
    \nDrop:\t\t''' + productName + ''' ''' + drop + '''
    \nVersion:\t''' + version + '''
    \nCreated:\t''' + dateCreated + '''
    \nThis package was delivered by: \n''' + delivererMail + '''
    \nThe reason for obsoletion is as follows: \n"''' + str(reason) + '''"'''

    fromEmail = config.get("CIFWK", "fromEmail")
    send_mail(emailHeader,emailContentAll,fromEmail,deliveryEmail,fail_silently=False)
    # only send mail to the person who delivered the package if NOT on a development server
    if developmentServer == 0:
       send_mail(emailHeader,emailContentCreator,fromEmail,[delivererMail],fail_silently=False)
    send_mail(emailHeader,emailContentObsoletor,fromEmail,[signum + '@lmera.ericsson.se'],fail_silently=False)



def obsoleteMedia(drpMediaMapId, mediaArt, signum, reason, drop, prodSet, prodSetRel, email):
    '''
    Obsoleting of Media Artifact Version from a Drop
    '''
    error = ""
    deliveryEmail = ""
    versionContentList = []
    # Get query for the drop package mapping selected
    drpMediaMap = DropMediaArtifactMapping.objects.get(id=drpMediaMapId)
    #This filter query is needed to check if the Drop Package Mapping is in a frozen drop for the if statement.
    drpMediaMapFrozen = DropMediaArtifactMapping.objects.filter(id=drpMediaMap.id, drop__mediaFreezeDate__lte=datetime.now())
    logger.info("Checking the Drop Media Artifact Mapping to see if it is in a Frozen Drop: " + str(len(drpMediaMapFrozen)))
    # If statement for dpm to check if it's empty,
    # to check if the pkgRevDPM obsolete is not True
    # and to make sure the date info is not empty else this will return the obsolete error page
    if not len(drpMediaMapFrozen) == 0 and drpMediaMap.obsolete != 1 and drpMediaMap.drop.mediaFreezeDate != None:
        # This is for when dpm filter comes back not 0 meaning the Package Revision is in a frozen drop and cannot be Obsoleted
        logger.error("ERROR Media Artifact Version in Frozen Drop")
        error = "ERROR Media Artifact Version in Frozen Drop"
        return error , drpMediaMap
    logger.info("Media Artifact Version was not in a Frozen Drop")

    if ProductSetVersionContent.objects.filter(productSetVersion__productSetRelease__productSet__name=prodSet, mediaArtifactVersion=drpMediaMap.mediaArtifactVersion, mediaArtifactVersion__version=drpMediaMap.mediaArtifactVersion.version).exists():
       versionsContent = ProductSetVersionContent.objects.filter(Q(productSetVersion__productSetRelease__productSet__name=prodSet, mediaArtifactVersion=drpMediaMap.mediaArtifactVersion, mediaArtifactVersion__version=drpMediaMap.mediaArtifactVersion.version, status__state="passed") | Q(productSetVersion__productSetRelease__productSet__name=prodSet, mediaArtifactVersion=drpMediaMap.mediaArtifactVersion, mediaArtifactVersion__version=drpMediaMap.mediaArtifactVersion.version, status__state="in_progress"))
       for prodSetVerCont in versionsContent:
           versionContentList.append(prodSetVerCont)
    if versionContentList:
        logger.error("Error Media Artifact Version in Product Set Version Content")
        error = "ERROR in Product Set Version Content"
        return error , versionContentList

    product = str(drpMediaMap.mediaArtifactVersion.drop.release.product.name)
    if developmentServer == 1:
        try:
            deliveryEmail = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", str(product).upper()))
        except Exception as e:
            logger.error("Email Recipient not available for development Server" + str(e))
    else:
        try:
            productId = drpMediaMap.mediaArtifactVersion.drop.release.product.id
            deliveryEmail = ProductEmail.objects.filter(product=productId)
        except Exception as e:
            logger.error("Email Recipient not available" + str(e))
    toEmails = []
    if email == None:
       userEmail = "User email not supplied"
    else:
        userEmail = email
        toEmails.append(userEmail)
    if deliveryEmail != None:
        for delEmail in deliveryEmail:
            if developmentServer == 1:
                toEmails.append(delEmail)
            else:
                toEmails.append(delEmail.email)
    # header for the e-mail. Contains package name and version.
    emailHeader = "Obsoleted: Media Artifact - " +  str(drpMediaMap.mediaArtifactVersion.mediaArtifact.name) + " (Version - " + str(drpMediaMap.mediaArtifactVersion.version)+")"

    mediaName = str(drpMediaMap.mediaArtifactVersion.mediaArtifact.name)
    version = str(drpMediaMap.mediaArtifactVersion.version)
    buildDate = str(drpMediaMap.mediaArtifactVersion.build_date)
    obsoleteTime = datetime.now()

    #content of automated e-mail. Contains RPM information and contact details for user responsible for obsoletion
    emailContent = '''The following Media Artifact Version has been made obsolete:\n\n
    Name:           ''' + mediaName + '''\n
    Drop:           ''' + prodSet + ''' ''' + drop + '''\n
    Version:        ''' + version + '''\n
    Build Date:        ''' + buildDate + '''\n\n
    This package was made obsolete by: \n''' + str(signum) + ''' - ''' + str(email) + '''\n
    The reason for obsoletion is as follows: \n"''' + str(reason) + '''"\n\n

    This is an automated message.'''
    # Add in the info into the DB for Obsolete Info
    obInfoObj,created = ObsoleteMediaInfo.objects.get_or_create(dropMediaArtifactMapping=drpMediaMap,signum=signum,reason=reason,time_obsoleted=obsoleteTime)
    obInfoObj.save()

    # Changing the Media Artifact Version status to obsolete and set released to False then saving
    drpMediaMap.obsolete = True
    drpMediaMap.released = False
    drpMediaMap.save()
    logger.info("Saved Media Artifact Verison for Obsoleting")
    if DropMediaArtifactMapping.objects.filter(mediaArtifactVersion__mediaArtifact__name=mediaArt, drop=drpMediaMap.drop, obsolete=0).exists():
       drpMediaMapPrev = DropMediaArtifactMapping.objects.filter(mediaArtifactVersion__mediaArtifact__name=mediaArt,  drop=drpMediaMap.drop, obsolete=0).order_by('-id')[0]
       logger.info("Getting Media Artifact Verison: " + str(drpMediaMapPrev) )
       # revert back to
       drpMediaMapPrev.released = True
       drpMediaMapPrev.save()
       logger.info("Saved Media Verison to set released: " + str(drpMediaMapPrev.released))
    # sends e-mail to relevant mailing list if no error has been encountered
    if error != 'error':
        send_mail(emailHeader,emailContent,'CI-Framework@ericsson.com',toEmails,fail_silently=False)
    return error , drpMediaMap




def prim(drop, product, media, rState, topProduct, topRev, user, password, newRelease):
    '''
       Getting and updating the information taken from Prim, plus creating sql file.
    '''
    errorList = []
    dir=cireports.prim.createDirForPrimSqlFiles()
    errorList.append(dir)
    delete=cireports.prim.deleteSqlFile(user)
    errorList.append(delete)
    cireports.prim.dropTables()
    cireports.prim.createTables()
    login=cireports.prim.login(user,password)

    if login is not "error":
        cursor = connection.cursor()
        cursor.execute("INSERT INTO level_0(productnumber,revision,type) VALUES(%s,%s,%s)",[topProduct.replace(" ",""),topRev,"13161-"])
        connection.commit()
        id= cursor.lastrowid
        cursor.close()
        all=cireports.prim.getAll(topProduct,topRev,login,1,id)
        errorList.append(all)
        primData=cireports.prim.returnData()
        drp = cireports.models.Drop.objects.get(name=drop, release__product=product)
        media = ISObuild.objects.get(version=media, drop=drp, mediaArtifact__testware=False, mediaArtifact__category__name="productware")
        packages = ISObuildMapping.objects.filter(iso=media)
        diff = cireports.prim.differences(packages)
        cireports.prim.findChangedAll(packages)
        cireports.prim.updateParents()
        cireports.prim.updatePkgRev(packages)
        cireports.prim.updateCXC()
        cireports.prim.stepRevAndStore(newRelease, rState)
        file=cireports.prim.storeDataInFile(user)
        errorList.append(file)
        data=cireports.prim.returnChangedData()
        dataList = zip(primData, data)
        cireports.prim.dropTables()
    else:
        errorList.append(login)

    if "error" in errorList:
        logger.error("Error Found During the Process")
        return errorList
    else:
        logger.info("Returning information and sql file name")
        args = { 'dataList': dataList, 'file': file, 'diff': diff}
    return args

def updatePrim(drop, media, user, password, write, file):
    '''
        Writes the new information to Prim and deleting the sql file after
    '''
    errorList = []
    cireports.prim.dropTables()
    cireports.prim.createTables()
    login=cireports.prim.login(user, password)
    if login is not "error":
       imp=cireports.prim.importDataFromFile(user, file)
       errorList.append(imp)
       createProdRes=cireports.prim.createProducts(drop,media,login,write)
       errorList.append(createProdRes)
       createStr=cireports.prim.createStructure(login,write)
       errorList.append(createStr)
       cireports.prim.dropTables()
       delete=cireports.prim.deleteSqlFile(user,file)
       errorList.append(delete)
    else:
       errorList.append(login)
    return errorList

def primCXP( product, drop, media, user, password):
    '''
       Getting the information from Prim.
    '''
    errorList = []
    primData = diffData = unknownPackagesDB = packages = []
    login=cireports.prim.login(user,password)
    args =[]

    if login is not "error":
       try:
           primData, diffData, unknownPackagesDB, packages = cireports.prim.getCXPsFromPrim(product,drop,media,login)
           dataList = zip(primData, diffData)
       except Exception as e:
           logger.error("There was an issue getting the prim data: " +str(e))
           errorList.append("error")
    else:
        errorList.append(login)

    if "error" in errorList:
        logger.error("Error Found During the Process")
        return errorList
    else:
        args = { 'dataList': dataList, 'unknownPackages': unknownPackagesDB, 'packages': packages}
    return args

def updatePrimCXP(product, drop, media, user, password, packages):
    '''
        Writes the new information to Prim and gets Report.
    '''
    errorList = []
    checkprim = []
    failed = ""
    login=cireports.prim.login(user, password)
    if login is not "error":
       update=cireports.prim.updateCXPs(product, drop, media,login, packages)
       checkprim, failed=cireports.prim.checkUpdateResults(packages, login)
       if failed == "error":
          errorList.append(failed)
       errorList.append(update)
    else:
       errorList.append(login)
    if "error" in errorList:
        return errorList, failed
    else:
        return checkprim, failed


def updateNodePRIStatus(request,packageNumber):
    '''
    This function updates the node PRI boolean in the DB PRI model reflecting the user interaction with Portal
    '''
    try:
        all_info = pri.objects.filter(pkgver__package__package_number=packageNumber).order_by('-drop')

        #Build Up a Complete List of PRI ID's for comparision later
        priIdList = []
        for item in all_info:
            priIdList.append(int(item.id))

        #Get Item to be included/excluded from Node PRi for Request Object
        includedInNodePRI = request.POST.getlist('includedNodePri')
        notIncludedNodePri = request.POST.getlist('notIncludedNodePri')

        #For Each item that is clicked/reclicked update PRI DB from False to True and remove item from priIdList
        for item in notIncludedNodePri:
            item = int(item)
            priObj = pri.objects.get(id=item)
            priObj.node_pri = int(1)
            priObj.save(force_update=True)
            if item in priIdList:
                priIdList.remove(item)

        #For Each item that is unclicked remove item from priIdList
        for item in includedInNodePRI:
            item = int(item)
            if item in priIdList:
                priIdList.remove(item)

        #For each item left on the priIdList change status from True to False
        for item in priIdList:
            priObj = pri.objects.get(id=item)
            priObj.node_pri = int(0)
            priObj.save(force_update=True)

        return 0
    except Exception as e:
        logger.error("There was an issue updating DB with Node PRI status: " +str(e))
        return 1

def checkingForChangesInDrop(dpms, currentDrop, dropName, isoType=None):
    '''
    Checking for changes in the drop: new  deliveries or Obsoletion
    '''
    category = "productware"
    logger.info("** Checking for deliveries that can be used to create ISO with **")
    if not dpms:
        logger.info("No deliveries found to create an ISO with, Please investigate further. Exiting")
        return "true"
    else:
        latestDelivered = dpms[0].date_created
        logger.info("Latest delivery for a package in this drop (" + str(dropName) +") was: " + str(latestDelivered))

    logger.info(" ** Checking for ISO builds for this Drop **")
    # Get List of the ISO's builds for this drop
    if "testware" not in str(isoType):
        iBuilds = ISObuild.objects.filter(drop=currentDrop, mediaArtifact__testware=False, mediaArtifact__category__name=category).order_by('-build_date')
    else:
        iBuilds = ISObuild.objects.filter(drop=currentDrop, mediaArtifact__testware=True).order_by('-build_date')
    if not iBuilds:
        return "true"
    else:
        latestBuiltIso = iBuilds[0].build_date
        logger.info("Latest Build Date of ISO  (Version " +str(iBuilds[0].version) + ") for this drop (" + str(dropName) +") was: " + str(latestBuiltIso))

    #Getting the ISO Content of Latest ISO Build for that Drop
    if "testware" not in str(isoType):
        lastISO = ISObuild.objects.get(drop=currentDrop, version=iBuilds[0].version, build_date=iBuilds[0].build_date, mediaArtifact__testware=False, mediaArtifact__category__name=category)
    else:
        lastISO = ISObuild.objects.get(drop=currentDrop, version=iBuilds[0].version, build_date=iBuilds[0].build_date, mediaArtifact__testware=True)

    lastISOcon= ISObuildMapping.objects.filter(iso=lastISO)
    #Building lists to compare last built iso content and dpm content
    isoList = []
    dpmList = []

    logger.info(" ** Checking for Changes **")

    #Creating the Lists
    for lic in lastISOcon:
        isoList.append(lic.package_revision)
    for dpm in dpms:
        dpmList.append(dpm.package_revision)


    # Compare Lists checking if they match or not.
    if dpmList != isoList:
        logger.info("Change in Current Drop: New deliveries have been found or Packages Version have been Obsoleted")
        return "true"
    else:
        logger.info("No changes made, No need to build ISO")
        return "false"


def getIntendedDropInfo(intendedDrop, productName, delivery=None):
    '''
      Getting Drop information
    '''
    iDropList = []
    intendedDropList = set()
    latestDrop = ""
    intendedDropResult = ""

    if "," in intendedDrop:
       iDropList = intendedDrop.split(",")
    elif " " in intendedDrop:
       intendedDrop = intendedDrop.strip(' \t\n\r')

    #Getting the Product
    try:
        product = Product.objects.get(name=productName)
    except:
        logger.error("error : unable to get product " + str(productName))
        return "error : unable to get product " + str(productName)

    #This is for when there is more than one drop is given
    if len(iDropList) != 0:
        for d in iDropList:
            dropName = str(d).strip(' \t\n\r')
            if "latest" in str(dropName):
                if not "." in str(dropName):
                    logger.error("error : unable to get Track, you need have a track to use latest (latest.track) i.e. latest.14A" )
                    return "error : unable to get Track, you need have a track to use latest (latest.track) i.e. latest.14A"
                [latest, track] = str(dropName).split(".", 1)
                try:
                    release = Release.objects.get(track=track, product=product)
                except:
                    logger.error("error : unable to get Track " + str(track) + " in Product " + str(product) )
                    return "error : unable to get Track " + str(track) + " in Product " + str(product)
                try:
                    latest = getLatestDropName(release, product)
                    intendedDropList.add(latest)
                except:
                    logger.error("error : unable to get latest drop using Track: " + str(track))
                    return "error : unable to get latest drop using Track: " + str(track)
            else:
                if Drop.objects.filter(name=dropName,release__product=product).exists():
                    drop =  str(product.name) + ":"+ str(d)
                    intendedDropList.add(drop)
        intendedDropResult =''.join(str(list(intendedDropList))).replace('[', "").replace(']', "").replace('\'', "")
        return str(intendedDropResult)

    # To cover if one drop is given
    else:
        if "latest" in str(intendedDrop):
            if not "." in intendedDrop:
                logger.error("error : unable to get Track, you need have a track to use latest (latest.track) i.e. latest.14A" )
                return "error : unable to get Track, you need have a track to use latest (latest.track) i.e. latest.14A"
            [latest, track] = intendedDrop.split(".", 1)
            try:
                release = Release.objects.get(track=track, product=product)
            except:
                logger.error("error : unable to get Track " + str(track) + " in Product " + str(product) )
                return "error : unable to get Track " + str(track) + " in Product " + str(product)
            try:
                latest = getLatestDropName(release, product)
                if delivery != None:
                    [product, drop] = latest.split(":")
                    return str(drop)
                else:
                    return str(latest)
            except:
                logger.error("error : unable to get latest drop using Track: " + str(track))
                return "error : unable to get latest drop using Track: " + str(track)
        else:
            if Drop.objects.filter(name=str(intendedDrop),release__product=product).exists():
                drop  =  str(product.name) + ":" + str(intendedDrop)
                return str(drop)
            else:
                logger.error("error : unable to get drop, does not exist in Product " + str(product))
                return "error : unable to get drop, does not exist in " + str(product)


def getLatestDropName(release, product):
    '''
     Latest Drop for that Release
    '''
    dropObjs = Drop.objects.filter(release=release,correctionalDrop=0).order_by('-id').values('name')
    dropObj = dropObjs[:1]
    for do in dropObj:
        dropName = str(do['name'])
        latestDrop =  str(product.name) + ":" + str(dropName)
        return str(latestDrop)


def getFlowContext(product):
    release = Release.objects.filter(product__name=product).order_by('-id').values('name').exclude(name__icontains="test")[:1]
    releaseName = release[0]['name']
    drops = Drop.objects.filter(release__name=releaseName,correctionalDrop=0).order_by('-id').values('name')
    for drop in drops:
        dropName = drop['name']
        if dropName.count('.') == 1:
            break
    return product+"/"+releaseName+"/"+dropName


@transaction.atomic
def updateMediaArtifactCDBStatus(drop,product,mediaArtifact,version,status):
    '''
     Update Overall Media Artifact Version CDB Status
    '''
    result = "OK"
    try:
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        mediaArtifactObj = MediaArtifact.objects.get(name=mediaArtifact)
        status = States.objects.get(state=status)
        mediaArtVerObj = ISObuild.objects.get(version=version, artifactId=mediaArtifact, mediaArtifact=mediaArtifactObj, drop=dropObj)
        mediaArtVerObj.overall_status = status
        mediaArtVerObj.save()
    except Exception as e:
        logger.error("Error processing information : "+str(drop)+"--"+str(status)+"--"+str(mediaArtifact) +"--"+str(version)+" : " +str(e))
        result = "ERROR"
    return result


@transaction.atomic
def updateCDB(drop, product, type, status, report=None, pkgList=None):
    '''
    Function to update the CDB status in the Database
    '''
    now = datetime.now()

    try:
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        cdbType = CDBTypes.objects.get(name=type)
    except Exception as e:
        logger.error("Error processing information : "+str(drop)+"--"+str(product)+"--"+str(type) +" : " +str(e))
        return

    if status == 'in_progress':
        # We have started the CDB run so create the necessary Objects in the DB
        try:
            with transaction.atomic():
                cdbObj,created=CDB.objects.get_or_create(drop=dropObj, type=cdbType)
                # Add in the extra details to the object
                cdbObj.status=status
                cdbObj.report=report
                cdbObj.lastUpdated=now
                cdbObj.started=now
                cdbObj.save()

                # Create a historical entry aswell with the same information
                histObj = CDBHistory.objects.create(drop=dropObj,type=cdbType,status=status,report=report,lastUpdated=now,started=cdbObj.started)
                # Create mappings here to list all the pkgs used for that
                dpms = getPackageBaseline(dropObj)
                for entry in dpms:
                    # Check pkgList/manifest and only add it if available in the DB.
                    lookup = str(entry.package_revision.package.name) +":"+ str(entry.package_revision.getRState()) +":"+ str(entry.package_revision.platform)
                    if dropObj.release.product.name == "OSS-RC":
                        if pkgList != None:
                            if str(lookup) in pkgList:
                                CDBPkgMapping.objects.create(cdbHist=histObj, package_revision=entry.package_revision)
                    else:
                        CDBPkgMapping.objects.create(cdbHist=histObj, package_revision=entry.package_revision)
        except IntegrityError as e:
            logger.error("Unable to update CDB status: "+str(drop)+"--"+str(product)+"--"+str(type)+"--"+str(status)+"--" +str(e))
    else:
        try:
            with transaction.atomic():
                # We have an existing object so update the information for it
                cdbObj=CDB.objects.get(drop=dropObj,type=cdbType)
                cdbObj.status=status
                cdbObj.report=report
                cdbObj.lastUpdated=now
                cdbObj.save()

                # Find the historical entry with same starttime (This is it's parent)...
                topElement = CDBHistory.objects.get(drop=dropObj.id, type=cdbType.id,status="in_progress",started=cdbObj.started)
                # Create a historical entry aswell with the same information and link to it's parent
                # This parent id will be used later to gather the content of the CDB from the cireports_cdbpkgmapping table
                CDBHistory.objects.create(drop=dropObj,type=cdbType,status=status,report=report,lastUpdated=now,started=cdbObj.started,parent=topElement)
        except IntegrityError as e:
            logger.error("Unable to update CDB status: "+str(drop)+"--"+str(product)+"--"+str(cdbType)+"--"+str(status)+"--" +str(e))


def dependencyMapping(submit,dependentPackageList,packageName,package,entry,installOrder,dependentPackageObj,found,product):
    '''
    if when adding a dependency to a package the dependencyMappingAddToList adds the depenency to list and updates menus on UI
    '''
    pkgList,allCount = getPackagesBasedOnProduct(product)
    mainPackageObj = Package.objects.get(name=packageName)
    installOrderList = list(xrange(1,300))
    if submit == "Add to List":
        if not dependentPackageList and package:
            dependentPackageList.append(entry)
            installOrderList.remove(int(installOrder))
            pkgList.remove(dependentPackageObj)
            return dependentPackageList,installOrderList,pkgList
        else:
            if package and entry not in dependentPackageList:
                for dependentPackage in dependentPackageList:
                    elementNumber = int(dependentPackage.split(':')[0])
                    elementName = str(dependentPackage.split(':')[1])
                    if elementNumber == installOrder or elementName == package:
                        found = "true"
                    if elementNumber in installOrderList:
                        installOrderList.remove(elementNumber)
                    elementPackageObj = Package.objects.get(name=elementName)
                    if elementPackageObj in pkgList:
                        pkgList.remove(elementPackageObj)
                if found is not "true":
                    dependentPackageList.append(entry)
                    if int(installOrder) in installOrderList:
                        installOrderList.remove(int(installOrder))
                    if dependentPackageObj in pkgList:
                        pkgList.remove(dependentPackageObj)
        return dependentPackageList,installOrderList,pkgList

    elif submit == "Update List":
        for dependentPackage in dependentPackageList:
            elementNumber = int(dependentPackage.split(':')[0])
            elementName = str(dependentPackage.split(':')[1])
            elementPackageObj = Package.objects.get(name=elementName)
            if elementNumber in installOrderList:
                installOrderList.remove(elementNumber)
            if elementPackageObj in pkgList:
                pkgList.remove(elementPackageObj)
        return dependentPackageList,installOrderList,pkgList

    elif submit == "Commit List":
        pkgDependMapObj = PackageDependencyMapping.objects.filter(package=mainPackageObj)
        for pkgDependMap in pkgDependMapObj:
            if pkgDependMap.package in dependentPackageList:
                continue
            else:
                pkgDependMap.delete()
        for dependentPackage in dependentPackageList:
            elementNumber = int(dependentPackage.split(':')[0])
            elementName = str(dependentPackage.split(':')[1])
            elementPackageObj = Package.objects.get(name=elementName)
            if not PackageDependencyMapping.objects.filter(package=mainPackageObj, dependentPackage=elementPackageObj, installOrder=elementNumber).exists():
                PackageDependencyMapping.objects.create(package=mainPackageObj, dependentPackage=elementPackageObj, installOrder=elementNumber)
        return dependentPackageList,installOrderList,pkgList

def sortList(list):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    return sorted(list, key = alphanum_key)


def deliveryEmailContent(product, package, ver, drop, pv, email, platform, kgbTest, deliveryGroup=None):

    '''
       This is for Message that will displayed in the Delivery Email
    '''
    sideNote = []
    message = []
    message.append("This is an automated Delivery mail from the CI Framework\n\nThe following has been delivered\n\nPackage:\t\t" + str(package) +
    "\nVersion:\t\t" + str(ver))
    if platform != 'None':
       message.append( "\nPlatform:\t\t" + str(platform))
    if deliveryGroup:
        message.append( "\nDelivery Group:\t\t" + str(deliveryGroup.id))
    message.append("\nDelivered To:\t\t" + str(drop))
    if product.kgbTests:
        if kgbTest:
            if str(kgbTest) != "passed":
                sideNote.append("NOTE: Package has not passed KGB testing.")
            message.append("\n\nFrozen KGB Tests:\t" + str(kgbTest))
        else:
            if str(pv.kgb_test) != "passed":
                sideNote.append("NOTE: Package has not passed KGB testing.")
            message.append("\n\nKGB Tests:\t" + str(pv.kgb_test))
    sideNote.append("\n(" + email + ")")
    note = ''.join(sideNote)
    message.append("\n\n" + note)
    content = ''.join(message)
    return content

def getLatestVersionOfPackageinRepository(packageObj, packageRepository, packageM2Type):
    '''
    The getLatestVersionOfPackageinRepository gets the latest Version and Repo Path of the artifact
    '''
    packageGroupId = PackageRevision.objects.filter(package=packageObj).latest('date_created').groupId
    latestArtefactVersion = PackageRevision.objects.filter(package=packageObj).latest('date_created').version
    packageRstate = PackageRevision.objects.get(package=packageObj, version=latestArtefactVersion, m2type=packageM2Type).getRState()

    repoGroupId = re.sub(r"\.", "/", packageGroupId)
    repoBaseURL = config.get('CIFWK', 'nexus_url')
    repoReleaseRepo = (str(repoBaseURL) + "/" + packageRepository + "/")
    try:
        rpmName = packageObj.name + "-" + latestArtefactVersion + "." + packageM2Type
        artefactNoarch = packageObj.name + "-" + latestArtefactVersion + "-1.noarch"
        completeArtifactURL = repoReleaseRepo + repoGroupId + "/" + packageObj.name + "/" + latestArtefactVersion + "/" + rpmName
    except Exception as e:
        return HttpResponse("Issue getting: '" + packageObj.name + "' complete repository Path: " + str(e))
    return latestArtefactVersion, completeArtifactURL, str(packageRstate)

def getLatestVersionOfPackage(package, platform):
    '''
    Get the latest version of a package based on whether platform is None or not None
    '''
    status = ""
    if platform == "None":
        packageRevisionObj = PackageRevision.objects.filter(package__name=package).order_by('-date_created')[0]
        version = packageRevisionObj.version
    elif platform != "None":
        packageRevisionObj = PackageRevision.objects.filter(package__name=package, platform=platform).order_by('-date_created')[0]
        version = packageRevisionObj.version
        versionParts = version.split(".")

        if (len(versionParts) < 3):
            status = ('You must supply a version string of the form N.N.N or N.N.N.N, where N is a positive integer, Version passed was : ' + str(version))
            return version, status
        elif (len(versionParts) < 4):
            versionParts.append('0')
    return version, status

def getLatestDropOnProductRelease(dropArray, product, platform, package, version, type):
    '''
    Get the latest drop of an Product based this also figures out the autodrop field for legacy product if it exists
    '''
    dropArray = status = ""
    try:
        if product != "None":
            productObj = Product.objects.get(name=product)
            allDrops = Drop.objects.filter(release__product=productObj,correctionalDrop=0).exclude(release__name__icontains="test")
        else:
            allDrops = Drop.objects.all(correctionalDrop=0).exclude(release__name__icontains="test")
    except Exception as e:
        status = ("Error: " +str(e))
        return dropArray, status

    #Get latest drop (latest drop is highest drop number from database)
    latestDrop="0.0.0"
    for dropNew in allDrops:
        dropNewStr = str(dropNew.name)
        if LooseVersion(dropNewStr) > LooseVersion(latestDrop):
            latestDrop = dropNewStr
    try:
        if platform == "None":
            packageRevisionObj = PackageRevision.objects.get(package__name=package, version=version, m2type=type)
        else:
            packageRevisionObj = PackageRevision.objects.get(package__name=package, version=version, platform=platform, m2type=type)
    except Exception as e:
        status = ("Error: " +str(e))
        return dropArray, status

    if ":" in packageRevisionObj.autodrop:
        autoDeliverList = str(packageRevisionObj.autodrop).split(',')
        for autoDeliverItem in autoDeliverList:
            if autoDeliverItem.startswith(str(product)+':') or autoDeliverItem.startswith(" "+str(product)+':'):
                autoDeliverDrop = autoDeliverItem.lower().split(':')[1]
                if dropArray == "":
                    dropArray = autoDeliverDrop
                else:
                    dropArray = dropArray + ',' + autoDeliverDrop
    else:
        dropArray = packageRevisionObj.autodrop.lower()

    if dropArray == "" or dropArray == "none":
        status = ("ERROR: No drop specified")
        return dropArray, status

    #replace occurances of latest with real drop number
    pattern = re.compile( "latest")
    dropArray = pattern.sub( latestDrop, dropArray)
    return dropArray, status


def makeDeliveryOfPackage(dropArray, package, version, type, platform, product, userEmail, to=None, restDelivery=None, user=None, deliveryGroup=None):
    '''
    The makeDeliveryOfPackage function attempts to make the deliver of a package, storePRI info and build up email content
    '''
    dm = config.get("CIFWK", "fromEmail")
    header = content = status = ""
    logger.info("Attempting delivery of " + package + "." + type + " version " + version + " to " + ', '.join(dropArray) + "\n")
    timeNow = datetime.now();
    validDrops = Drop.objects.filter(planned_release_date__gt=timeNow).only('id') | Drop.objects.filter(actual_release_date__gt=timeNow).only('id')
    retStatus = ""
    if user:
        to.append(str(user.email))
    for drop in dropArray:
        skipAndTryNextDrop = False
        try:
            requiredPackageRevisionFields=('id', 'package__name', 'package__id', 'package__package_number', 'non_proto_build', 'groupId', 'platform', 'kgb_test')
            if platform == "None":
                packageRevisionObj = PackageRevision.objects.only(*requiredPackageRevisionFields).get(package__name=package, version=version, m2type=type)
            else:
                packageRevisionObj = PackageRevision.objects.only(*requiredPackageRevisionFields).get(package__name=package, version=version, platform=platform, m2type=type)
        except PackageRevision.DoesNotExist:
            header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
            content = "PackageRevision " + package + "." + type + " version " + version + " does not exist." + "\n" + str(userEmail)
            retStatus = retStatus+",ERROR-"+str(drop)
            logger.error("PackageRevision " + package + "." + type + " version " + version + " does not exist")
            if to:
                send_mail(header, content, dm, to, fail_silently=False)
                continue
            return header, content, retStatus

        if packageRevisionObj.non_proto_build != "true":
            retStatus = retStatus+(',ERROR: Delivery of packages with 3PP prototype not permitted.\nDelivery not made.\n')
            if to:
                header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                content = retStatus
                send_mail(header, content, dm, to, fail_silently=False)
                continue
            return header, content, retStatus

        if product != "None":
            try:
                productObj = Product.objects.only('id', 'name').get(name=product)
            except Product.DoesNotExist:
                retStatus = retStatus+(",ERROR: Product " +str(product)+ " does not exist" + "\n")
                if to:
                    header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                    content = retStatus
                    send_mail(header, content, dm, to, fail_silently=False)
                    continue
                return header, content, retStatus

        try:
            dropObj = Drop.objects.only('id', 'name', 'status', 'release__name').get(name=drop,release__product=productObj.id)
            if restDelivery:
                if "open" not in dropObj.status:
                    header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                    content = "Drop "+str(dropObj.name)+ " is " + str(dropObj.status) + " and cannot accept any new deliveries."
                    logger.error(content)
                    retStatus = retStatus+",NOTOPEN"+str(dropObj.name)
                    if to:
                        send_mail(header, content, dm, to, fail_silently=False)
                        continue
                    return header, content, retStatus
            if not(any(drp.id == dropObj.id for drp in validDrops)):
                header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                content = "Drop "+str(dropObj.name)+ " is frozen and cannot accept any new deliveries."
                logger.error("Drop "+str(dropObj.name)+ " is frozen and cannot accept any new deliveries.")
                retStatus = retStatus+",FROZEN"+str(dropObj.name)
                if to:
                    send_mail(header, content, dm, to, fail_silently=False)
                    continue
                return header, content, retStatus
        except Drop.DoesNotExist:
            header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
            content = "Drop " + drop + " does not exist." + "\n" + str(userEmail)
            retStatus = retStatus+",ERROR"
            logger.error("Drop " + drop + " does not exist")
            if to:
                send_mail(header, content, dm, to, fail_silently=False)
                continue
            return header, content, retStatus

        currPackage = Package.objects.only('id', 'name', 'obsolete_after', 'obsolete_after__name', 'obsolete_after__release__product__name').get(name=package)
        obsoleteAfter = LooseVersion(str(None))
        # Check the obsolete_after associated with the package
        # If the Top Level drop (the topLevelId) is greater
        # than the obsolete_after then do not deliver to Drop
        dropVersion = LooseVersion(str(dropObj.name))
        if currPackage.obsolete_after is not None:
            # Check if the obsolete_after is set for the current product/release
            if str(currPackage.obsolete_after.release.product.name) == str(productObj.name):
                obsoleteAfter = LooseVersion(str(currPackage.obsolete_after.name))
            else:
                logger.debug("Package is set not to take any new deliveries for product: " + str(currPackage.obsolete_after.release.product.name) + "  Continuing delivery to product: " +  str(productObj.name))
        logger.debug("Top Level Drop : " + str(dropVersion) + " / Obsolete After : " + str(obsoleteAfter))
        if (dropVersion <= obsoleteAfter):
            logger.debug("Package has not been obsoleted for this Drop: " + str(currPackage.name))
        else:
            logger.debug("Package " + str(currPackage.name) + " has been updated so that it can no longer be delivered to a drop after drop" +str(currPackage.obsolete_after))
            retStatus = retStatus+(",ERROR: This package has been updated so that it can no longer be delivered to a drop after drop " +str(currPackage.obsolete_after) + "\nThis delivery cannot be made.\n")
            if to:
                header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                content = retStatus
                send_mail(header, content, dm, to, fail_silently=False)
                continue
            return header, content, retStatus

        try:
            checkResult = []
            try:
                checkResult, sprintCheck = getPackageInBaseline(product, dropObj, package)
            except Exception as error:
                logger.error("ERROR in checking Package in Baseline: " + str(error))
            if checkResult:
                if checkResult.package_revision.id == packageRevisionObj.id:
                    header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                    content = "Package "+str(package)+ " already in Drop " + drop + "\n" + str(userEmail)
                    retStatus = retStatus+",INDROP"+str(drop)
                    logger.error("Package "+str(package)+ " already in Drop " + drop )
                    if to:
                        send_mail(header, content, dm, to, fail_silently=False)
                        skipAndTryNextDrop = True
                        continue
                    return header, content, retStatus
            if skipAndTryNextDrop:
                continue
        except Exception as e:
            header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
            content = "Package already in " + drop + "\n" + str(userEmail)
            retStatus = retStatus+",ERROR"
            logger.error("Package already in " + drop + ": " + str(e))
            if to:
                send_mail(header, content, dm, to, fail_silently=False)
                continue
            return header, content, retStatus

        try:
            header, content, retStatusNew = updateDropPackageMappingOnDelivery(packageRevisionObj, dropObj, package, platform, productObj, version, userEmail, user, deliveryGroup)
            if "ERROR" in retStatusNew:
                retStatus = retStatus+","+retStatusNew
                if to:
                    header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                    content = retStatus
                    send_mail(header, content, dm, to, fail_silently=False)
                    continue
                return header, content, retStatus
        except Exception as e:
            retStatus = retStatus+","+"Error: " +str(e)
            if to:
                header = "FAILED: Delivery of: " + str(package) + " - " + str(version) + " to Drop: " + str(drop)
                content = retStatus
                send_mail(header, content, dm, to, fail_silently=False)
                continue
            return header, content, retStatus
        try:
            mbHost = config.get('MESSAGE_BUS', 'eiffelHostname')
            mbExchange =  config.get('MESSAGE_BUS', 'eiffelExchangeName')
            mbDomain =  config.get('MESSAGE_BUS', 'eiffelDomainName')
            mbUser = config.get('MESSAGE_BUS', 'mbFunctionalUser')
            mbPwd = config.get('MESSAGE_BUS', 'mbFunctionalUserPassword')
            java =  config.get('MESSAGE_BUS', 'javaLocation')

            if packageRevisionObj.team_running_kgb:
                teamObj = packageRevisionObj.team_running_kgb
                team = teamObj.element
                parentElement= teamObj.parent.element
            else:
                team,parentElement = getTeamParentElement(package)

            kgbStatus = packageRevisionObj.kgb_test

            jsonInput = {
                    "confidenceLevel":"DELIVERED",
                    "confidenceLevelState":"SUCCESS",
                    "drop":str(drop),
                    "product":str(dropObj.release.product.name),
                    "release":str(dropObj.release.name),
                    "artifactId":str(package),
                    "groupId":str(packageRevisionObj.groupId),
                    "version":str(version),
                    "team":str(team),
                    "ra":str(parentElement),
                    "kgbStatus":str(kgbStatus),
                    "messageBusHost":mbHost,
                    "messageBusExchange":mbExchange,
                    "messageBusDomain":mbDomain,
                    "messageBusUser": mbUser,
                    "messageBusPassword": mbPwd,
                    "messageType":"clme"
                    }
            dateCreated = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
            logger.info("####### Sending eiffelDeliveryMessage to Message bus ########")
            logger.info(jsonInput)
            sendCLME = subprocess.check_call(java + " -jar /proj/lciadm100/cifwk/latest/lib/3pp/eiffelEventSender/cli-event-sender.jar '"+json.dumps(jsonInput)+"' 2>> /proj/lciadm100/cifwk/logs/messagebus/eiffelDeliveryMessage/" + dateCreated, shell=True,cwd="/tmp")
            if not sendCLME == 0:
                logger.debug("Issue sending eiffel message")
        except Exception as e:
            logger.debug("Issue sending eiffel message")
        try:
            retStatus = retStatus+",DELIVERED:"+str(packageRevisionObj.id)+":"+str(dropObj.id)
            storePRI(drop,packageRevisionObj.package.name,packageRevisionObj.package.package_number,version,type,platform)
            logger.info("Delivery successful")
        except Exception as e:
            logger.debug("No PRI information available")
        if to:
            send_mail(header, content, dm, to, fail_silently=False)
            continue
    return header, content, retStatus

def updateDropPackageMappingOnDelivery(packageRevisionObj, dropObj, package, platform, productObj, version, userEmail, user, deliveryGroup):
    '''
    The updateDropPackageMappingOnDelivery updates the Drop Package Mapping table on package delivery
    '''
    header = content = status = ""
    time = datetime.now()

    # Get a list of all the other package revisions that are included in this drop
    try:
        if DropPackageMapping.objects.prefetch_related('package_revision__package').filter(drop=dropObj.id, package_revision__package=packageRevisionObj.package.id, package_revision__platform=packageRevisionObj.platform, released=True).exists():
            if platform != "None":
                previousRelease =  DropPackageMapping.objects.only('released').get(drop=dropObj.id, package_revision__package=packageRevisionObj.package.id, package_revision__platform=packageRevisionObj.platform, released=True)
            else:
                previousRelease = DropPackageMapping.objects.only('released').get(drop=dropObj.id, package_revision__package=packageRevisionObj.package.id, released=True)
            previousRelease.released = 0
            previousRelease.save()
    except Exception as e:
        status = ("ERROR: Getting previous Release package revision failed: " +str(e) + "\n")
        return header, content, status

    kgbResult = None
    header = "Delivery of: " + str(package) + " - " + str(version) + " to " + str(productObj.name) + " Drop: " + str(dropObj.name)
    try:
        # Create a new DPM that sets the new version to released
        if user is not None:
            name = str(user.first_name) + " " + str(user.last_name)
            email = str(user.email)
        else:
            name = userEmail
            email = userEmail
        if str(productObj.name) == "ENM":
            kgbResult, testReport, kgbSnapshotReport = getPkgRevKgbResultFromDeliveryGrp(deliveryGroup, packageRevisionObj)
            if kgbResult:
                drpPkgMap = DropPackageMapping(package_revision=packageRevisionObj, drop=dropObj, obsolete=False, released=True, date_created=time, deliverer_mail=email, deliverer_name=name, kgb_test=kgbResult, testReport=testReport, kgb_snapshot_report=kgbSnapshotReport)
            else:
                testReport = getPkgRevKgbReport(packageRevisionObj)
                drpPkgMap = DropPackageMapping(package_revision=packageRevisionObj, drop=dropObj, obsolete=False, released=True, date_created=time, deliverer_mail=email, deliverer_name=name, kgb_test=packageRevisionObj.kgb_test, testReport=testReport, kgb_snapshot_report=packageRevisionObj.kgb_snapshot_report)
                kgbResult = drpPkgMap.kgb_test
        else:
            drpPkgMap = DropPackageMapping(package_revision=packageRevisionObj, drop=dropObj, obsolete=False, released=True, date_created=time, deliverer_mail=email, deliverer_name=name)
        drpPkgMap.save()
        mapProductToPackage(drpPkgMap.drop.release.product.name, drpPkgMap.package_revision.package)
        content = deliveryEmailContent(productObj, package, version, dropObj.name, packageRevisionObj, userEmail, platform, kgbResult, deliveryGroup)
        drpPkgMap.delivery_info=content
        drpPkgMap.save()
    except Exception as e:
        content = deliveryEmailContent(productObj, package, version, dropObj.name, packageRevisionObj, userEmail, platform, kgbResult, deliveryGroup)
        status = ("ERROR: " +str(e) + "\n")
        return header, content, status

    return header, content, status

def getPkgRevKgbResultFromDeliveryGrp(deliveryGroup, packageRevision):
    '''
      Getting the Package Rev Kgb Result From Delivery Group
    '''
    kgbResult = None
    testReport = ""
    kgbSnapshotReport = None
    try:
        fields = "kgb_test", "testReport", "kgb_snapshot_report",
        kgbInfo = DeliverytoPackageRevMapping.objects.only(fields).values(*fields).get(deliveryGroup=deliveryGroup, packageRevision=packageRevision)
        kgbResult = kgbInfo['kgb_test']
        testReport = kgbInfo['testReport']
        kgbSnapshotReport = kgbInfo['kgb_snapshot_report']
    except Exception as error:
        logger.error("Issue getting the kgb Result from Delivery Group: " + str(deliveryGroup) +" - " + str(error))
    return kgbResult, testReport, kgbSnapshotReport

def mediaDelivery(productSetName, productSetRelName, dropName, product, mediaName, version, signum,  email, productList=None):
    '''
      Media Artifact Delivery to Product Set
    '''
    prodSetRel = mediaArtifact = drop = dropLatest = None
    try:
        if productSetRelName != None:
            prodSetRel = ProductSetRelease.objects.get(name=productSetRelName, productSet__name=productSetName)
        else:
            prodSetRel = ProductSetRelease.objects.filter(productSet__name=productSetName).latest("id")

        if dropName == "latest":
            if productSetRelName != None:
                dropLatest = Drop.objects.filter(release=prodSetRel.release, correctionalDrop=False).latest("id")
            else:
                dropLatest = Drop.objects.filter(release__product=prodSetRel.release.product, correctionalDrop=False).exclude(release__name__icontains="test").latest("id")
            drop = dropLatest
        else:
            if productSetRelName != None:
                drop = Drop.objects.get(name=dropName, release=prodSetRel.release, release__product=prodSetRel.release.product)
            else:
                drop = Drop.objects.get(name=dropName, release__product=prodSetRel.release.product)
        mediaArtifact = ISObuild.objects.get(version=version, mediaArtifact__name=mediaName)
    except Exception as e:
        results = "Issue with Delivering Media Artifact to Product Set, ERROR: " +str(e)
        return results
    try:
        currentDrop = getMediaBaseline(drop.id)
        for currentMedia in currentDrop:
            if str(mediaArtifact) in str(currentMedia):
                results = "ERROR: Issue with Delivering Media Artifact " + str(mediaName) + " version " + str(version) + " to Product Set " + str(productSetName) + ", Already Delivered"
                return results
    except Exception as e:
        results = "Issue with Delivering Media Artifact to Product Set, ERROR: " +str(e)
        return results

    try:
        timeNow = datetime.now()
        drops = Drop.objects.filter(mediaFreezeDate__gt=timeNow)
        if "closed" in drop.status:
            results = "ERROR: Issue with Delivering Media Artifact " + str(mediaName) + " version " + str(version) + " to Product Set " + str(productSetName) + ", Drop is not open for deliveries " + str(drop.name)
            return results
        if not drop in drops:
            results = "ERROR: Issue with Delivering Media Artifact " + str(mediaName) + " version " + str(version) + " to Product Set " + str(productSetName) + ", Frozen Drop " + str(drop.name)
            return results
    except Exception as e:
        results = "Issue with Delivering Media Artifact to Product Set, ERROR: " +str(e)
        return results

    try:
        if DropMediaArtifactMapping.objects.filter(drop=drop, mediaArtifactVersion__mediaArtifact=mediaArtifact.mediaArtifact, released=1).exists():
              previousRelease = DropMediaArtifactMapping.objects.get(drop=drop, mediaArtifactVersion__mediaArtifact=mediaArtifact.mediaArtifact, released=1)
              previousRelease.released = 0
              previousRelease.save()
        dateCreated= datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("DropMediaArtifactMapping: "  + str(drop.name) + " - " +  str(mediaArtifact) + " - "  + str(dateCreated))
        deliveryInfo = "Delivered by \nSignum: " + str(signum) + "\nEmail: " +  str(email)
        dropMediaMap = DropMediaArtifactMapping.objects.create(drop=drop, mediaArtifactVersion=mediaArtifact, released=1, dateCreated=dateCreated, deliveryInfo=deliveryInfo)
        if productList and str(mediaArtifact.drop.release.product.name) == "ENM":
            for productName in productList:
                productObj = Product.objects.get(name=productName)
                DropMediaDeployMapping.objects.create(dropMediaArtifactMap=dropMediaMap, product=productObj)
        mail = deliveryMailofMediaArtifact(product, productSetName, drop.name, mediaName, mediaArtifact.version, signum, email)
        if "ERROR" in mail:
            results = mail
        else:
            results = "Media Artifact " + str(mediaName) + " version " + str(mediaArtifact.version) + " Sucessfully Delivered to Product Set " +  str(productSetName) + " - Drop " + str(drop.name) + "\n"
        return results
    except Exception as e:
        results = "Issue with Delivering Media Artifact to Product Set, ERROR: " +str(e)
        return results

def deliveryMailofMediaArtifact(product, productSet, dropName, mediaName, version, signum, email):
    '''
      delivery Mail for Media Artifact to Product Set Drop
    '''
    header = content = status = ""
    deliveryEmail = None
    if developmentServer == 1:
        try:
            deliveryEmail = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", str(product).upper()))
        except Exception as e:
            deliveryEmail=None
            status = "ERROR: Distribution Email list Required For Product " + str(product) + ". \n  Please contact CI Axis to give the Distribution Email list for this Product"
            return status
    else:
        try:
           productObj = Product.objects.get(name=product)
           deliveryEmail = ProductEmail.objects.filter(product=productObj.id)
        except Exception as e:
           deliveryEmail=None
           status = "ERROR: Distribution Email list Required For Product " + str(product) + ". \n  Please contact CI Axis to give the Distribution Email list for this Product"
           return status
    toEmail = []
    if email == None:
       userEmail = "User email not supplied, command line delivery"
    else:
       userEmail = email
       toEmail.append(userEmail)
    if deliveryEmail != None:
        for delEmail in deliveryEmail:
            if developmentServer == 1:
                toEmail.append(delEmail)
            else:
                toEmail.append(delEmail.email)
    header = "Delivery of " + str(product) +  " Media Artifact - " + str(mediaName) + " (Version -" + str(version) + ") to Product Set - " + str(productSet)
    sideNote = []
    message = []
    message.append("This is an automated Delivery mail from the CI Framework\n\nThe following has been delivered\n\nMedia Artifact:\t" + str(mediaName) +
    "\nVersion:\t" + str(version))
    message.append("\nProduct Set:\t"+ str(productSet))
    message.append("\nDelivered To:\t"+ str(dropName))
    sideNote.append("\nDelivered by: " + signum + " - " + userEmail )
    note = ''.join(sideNote)
    message.append("\n\n" + note)
    content = ''.join(message)
    fromEmail = 'CI-Framework@ericsson.com'

    #Send Delivery Mail
    try:
        send_mail(header, content, fromEmail, toEmail, fail_silently=False)
    except Exception as e:
        status = "ERROR in Sending Delivery Email: " +str(e)
        return status
    return "Sent Delivery Email"

def sortMedia(media, dropId):
    '''
        # Check the obsolete_after associated with the media Artifact
        # If the Top Level drop (the topLevelId) passed to this function is greater
        # than the obsolete_after then remove it from the baseline
        # using Id to sort media to support side branch operations
    '''
    topDrop = Drop.objects.get(id=dropId)
    sortedPkgs = []
    for currMedia in media:
        logger.debug("Media Artifact: " + str(currMedia))
        obsoleteAfterId = LooseVersion(str(None))
        topDropId = LooseVersion(str(topDrop.id))
        if currMedia.mediaArtifactVersion.mediaArtifact.obsoleteAfter is not None:
            obsoleteAfterId = LooseVersion(str(currMedia.mediaArtifactVersion.mediaArtifact.obsoleteAfter.id))
        logger.debug("Top Level Drop : " + str(topDrop.name) + " / Obsolete After : " + str(currMedia.mediaArtifactVersion.mediaArtifact.obsoleteAfter))
        if (topDropId <= obsoleteAfterId):
            logger.debug("Adding the following Media Artifacts to the Baseline : " + str(currMedia))
            # We didn't find this media artifact in our current list,  and it has been obsoleted so lets add it now to new sorted List
            sortedPkgs.append(currMedia)
        else:
            logger.debug("EXCLUDING from the Baseline : " + str(currMedia))
    return sortedPkgs

def getMediaBaseline(dropid, type=None):
    """
    Return the full Media baseline for the supplied drop ID. Internally, this function retrieves
    the list of Media delivered in this drop, and then iterates back through the historical
    drop list until it retrieves the full list of packages delivered to this drop or any previous
    drops.

    The assumption is made that drops are created as a "tree structure" - as in each drop has a
    single parent and zero or more children. A drop with no parent is the base drop.
    """
    if 'testware' in str(type):
        mediaArtifacts = list(DropMediaArtifactMapping.objects.filter(drop=dropid,released=1,obsolete=0, mediaArtifactVersion__mediaArtifact__testware=1).order_by('-dateCreated'))
    elif 'packages' in str(type):
        mediaArtifacts = list(DropMediaArtifactMapping.objects.filter(drop=dropid,released=1,obsolete=0, mediaArtifactVersion__mediaArtifact__testware=0, mediaArtifactVersion__mediaArtifact__category__name="productware").order_by('-dateCreated'))
    else:
        mediaArtifacts = list(DropMediaArtifactMapping.objects.filter(drop=dropid,released=1,obsolete=0).order_by('-dateCreated'))
    logger.debug(connection.queries)
    logger.debug("Got some Media Artifacts: "  + str(mediaArtifacts))
    sortedMedia = sortMedia(mediaArtifacts, dropid)
    try:
        designbase = Drop.objects.get(drop=dropid)
    except Drop.DoesNotExist:
        # We don't have a design base for this drop, it must be the root
        # drop (or there's a problem with the DB!)
        logger.debug("Last drop in the tree: " + str(dropid))
        return sortedMedia
    if (designbase):
        return getMediaBaselineHistory(designbase.id, sortedMedia, dropid, type)

def getMediaBaselineHistory(baselineId, media, topLevelId, type=None):
    """
    return the historical list of packages for the supplied drop. This is a recursive function.

    The function retrieves the list of packages which were delivered to the provided drop. It compares each of
    these to the provided package list, and if a later version of that package does not already exist in the
    media list it inserts that media artifact. It then retrieves the parent drop of the provided drop. If this
    is not null (i.e. if we are not on the first drop) we call the same function recursively, this time with
    the parent drop ID and the (possibly bigger) media list. In this way we build up a list of media artifact
    versions delivered to the current drop or any previous drops.
    """
    currDrop = Drop.objects.get(id=baselineId)
    logger.debug("Getting historical baseline for " + str(currDrop))
    # get all media artifacts at this design base that we don't already have
    # TODO: Optimise
    additionalMedia = []
    if 'testware' in str(type):
        olderMedia = DropMediaArtifactMapping.objects.filter(drop=baselineId,released=1,obsolete=0, mediaArtifactVersion__mediaArtifact__testware=1).order_by('-dateCreated')
    elif 'packages' in str(type):
        olderMedia = DropMediaArtifactMapping.objects.filter(drop=baselineId,released=1,obsolete=0, mediaArtifactVersion__mediaArtifact__testware=0, mediaArtifactVersion__mediaArtifact__category__name="productware").order_by('-dateCreated')
    else:
        olderMedia = DropMediaArtifactMapping.objects.filter(drop=baselineId,released=1,obsolete=0).order_by('-dateCreated')

    # iterate through QuerySet object to determine if we already have a version
    # of this media Artifact in our media list
    for oldMedia in olderMedia:
        found = 0
        for currMedia in media:
            if (oldMedia.mediaArtifactVersion.mediaArtifact == currMedia.mediaArtifactVersion.mediaArtifact):
                found = 1
                break
        if (found == 0):
            additionalMedia.append(oldMedia)

    # Build up the full set of Media
    sortedMedia = sortMedia(additionalMedia, topLevelId)
    fullSetMedia = media + sortedMedia
    # Get our design base for the next drop in our history
    try:
        designbase = Drop.objects.get(drop=baselineId)
    except Drop.DoesNotExist:
        # We don't have a design base for this drop, it must be the root
        # drop (or there's a problem with the DB!)
        logger.debug("Last drop in the tree: " + str(baselineId))
        return fullSetMedia
    logger.debug(str(currDrop) + " has a design base: (" + str(designbase) + ") , going back")
    # We have a design base, so find out if any media were delivered there
    return getMediaBaselineHistory(designbase.id, fullSetMedia, topLevelId, type)

def getOrCreateVersion(prodSet, drop):
    try:
        prodSetObj = ProductSet.objects.only('name', 'id').values('name', 'id').get(name=prodSet)
        product = ProductSetRelease.objects.only('release__product', 'id').filter(productSet_id=prodSetObj['id'])[0].release.product
        dropObjField = ('release', 'name', 'mediaFreezeDate', 'id',)
        dropObj = Drop.objects.only(dropObjField).values(*dropObjField).get(name=drop, release__product=product)
        productSetRelease = ProductSetRelease.objects.only('id', 'name').values('id', 'name').get(productSet_id=prodSetObj['id'],release=dropObj['release'])
        frozenDate = dropObj['mediaFreezeDate']
        timeNow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timeNowObj = datetime.strptime(timeNow, '%Y-%m-%d %H:%M:%S')
        if timeNowObj > frozenDate:
            errMsg = "Error: Drop frozen : " + str(dropObj['name'])
            logger.error(errMsg)
            return errMsg
        buildIt1 = False
        buildIt2 = False
    except Exception as error:
        errMsg = "There was an issue gathering Product Set Information: " +str(error)
        logger.error(errMsg)
        return errMsg

    try:
        latestPsvField = ('version', 'productSetRelease__number', 'id', )
        latestPsv = ProductSetVersion.objects.only(latestPsvField).values(*latestPsvField).filter(drop_id=dropObj['id'],productSetRelease_id=productSetRelease['id']).order_by('-id')[0]
        previousBuildContents = ProductSetVersionContent.objects.only('mediaArtifactVersion__id').values('mediaArtifactVersion__id').filter(productSetVersion_id=latestPsv['id'])
        productSetNumber =  latestPsv['productSetRelease__number']
        productSetVersion =  latestPsv['version']
    except:
        latestPsv = None
        previousBuildContents = None

    dropName = dropObj['name']
    if latestPsv == None:
        buildIt1 = True
        previousBuildContent = None
        newVersion = dropName+".1"
    else:
        majMin, patch = str(productSetVersion).rsplit('.', 1)
        if not dropName in majMin:
            productSetVersion = dropName+"."+patch
        majMin, patch = str(productSetVersion).rsplit('.', 1)
        newPatch = int(patch) + 1
        newVersion = majMin+"."+str(newPatch)
    #Creating the Lists
    previousList = []
    currentList = []
    currentContents = getMediaBaseline(dropObj['id'])
    if previousBuildContents != None:
        for previousItem  in previousBuildContents:
            previousList.append(previousItem['mediaArtifactVersion__id'])
    for currentItem in currentContents:
        currentList.append(currentItem.mediaArtifactVersion.id)
    if currentList != previousList:
        buildIt2 = True

    if buildIt1 == True or buildIt2 == True:
        version=newVersion
        status = States.objects.get(state='not_started')
        productSetVersionObj = ProductSetVersion.objects.create(drop=Drop.objects.get(id=dropObj['id']),version=version,status=status,productSetRelease=ProductSetRelease.objects.get(id=productSetRelease['id']))
        dropMediaDeployMaps = None
        mainMediaArtifactVersionObj = None
        defaultDropMediaDeployMaps = str(config.get('DMT', 'defaultDeployProductMaps')).split(' ')
        for currentItem in currentContents:
            if str(currentItem.mediaArtifactVersion.drop.release.product.name) == "ENM":
                mainMediaArtifactVersionObj = currentItem.mediaArtifactVersion
                if DropMediaDeployMapping.objects.filter(dropMediaArtifactMap=currentItem).exists():
                    dropMediaDeployMaps = DropMediaDeployMapping.objects.only('product__name').values('product__name').filter(dropMediaArtifactMap=currentItem)
                    break
        for currentItem in currentContents:
            createMapping = False
            ProductSetVersionContent.objects.create(productSetVersion=productSetVersionObj,mediaArtifactVersion=currentItem.mediaArtifactVersion,status=status)
            mediaProductName = currentItem.mediaArtifactVersion.drop.release.product.name
            if dropMediaDeployMaps:
                for dropMediaDeployMap in dropMediaDeployMaps:
                    if str(dropMediaDeployMap['product__name']) == str(mediaProductName):
                        createMapping = True
                        break
            else:
                if str(mediaProductName) in defaultDropMediaDeployMaps:
                    createMapping = True
            if createMapping:
                ProductSetVersionDeployMapping.objects.create(mainMediaArtifactVersion=mainMediaArtifactVersionObj, mediaArtifactVersion=currentItem.mediaArtifactVersion, productSetVersion=productSetVersionObj)
        if prodSetObj['name'] == "ENM":
            sendPSVersionEiffelMessage(drop, prodSetObj['name'], productSetVersionObj.version, productSetRelease['name'], productSetNumber)
    else:
        version=latestPsv['version']
    return version

def sendPSVersionEiffelMessage(dropVersion, productName, productSetVersion, productSetReleaseName, productSetNumber):
    '''
    This function send a message to Eiffel Message Bus (MB)
        about that new product set version has been created
    '''
    try:
        mbHost = config.get('MESSAGE_BUS', 'eiffelHostname')
        mbExchange = config.get('MESSAGE_BUS', 'eiffelExchangeName')
        mbDomain = config.get('MESSAGE_BUS', 'eiffelDomainName')
        mbUser = config.get('MESSAGE_BUS', 'mbFunctionalUser')
        mbPwd = config.get('MESSAGE_BUS', 'mbFunctionalUserPassword')
        java = config.get('MESSAGE_BUS', 'javaLocation')
        jsonInput = {
                "confidenceLevel":"PSCREATED",
                "confidenceLevelState":"SUCCESS",
                "groupId":"com.ericsson",
                "release":str(productSetReleaseName),
                "product":str(productName),
                "drop":str(dropVersion),
                "artifactId":str(productSetNumber),
                "version":str(productSetVersion),
                "messageBusHost":mbHost,
                "messageBusExchange":mbExchange,
                "messageBusDomain":mbDomain,
                "messageBusUser": mbUser,
                "messageBusPassword": mbPwd,
                "messageType":"clme"
                }
        dateCreated = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        logger.info("####### Sending eiffelPSVersionMessage to Message bus ########")
        logger.info(jsonInput)
        sendCLME = subprocess.check_call(java + " -jar /proj/lciadm100/cifwk/latest/lib/3pp/eiffelEventSender/cli-event-sender.jar '"+json.dumps(jsonInput)+"' 2>> /proj/lciadm100/cifwk/logs/messagebus/eiffelPSVersionMessage/" + dateCreated, shell=True,cwd="/tmp")
        if not sendCLME == 0:
            logger.debug("Issue sending eiffel message")
    except Exception as e:
        logger.error("Issue sending eiffel message: " + str(e))

def getCDBinfo(cdbObj,excludeList=None):
    '''
    Returns ID and type of CDB run
    '''
    if not excludeList:
        excludeList=[]
    try:
        for item in cdbObj:
                cdbId=item.id
                for status in cdbObj[item]:
                    cdbType=status[0]
                    excludeList.append(str(cdbId)+"_"+str(cdbType))
    except Exception as e:
        logger.error("Issue creating list of CDB test runs:"+str(e))
    return excludeList

def getMediaArtifactsByDrop(productName, dropName):
    '''
    Gets all Media Artifacts for the Drop
    '''
    category = "productware"
    mediaArtifact = drpMediaMaps = deliveryData = None
    mediaArtifactVersions = None
    try:
        product = Product.objects.get(name=productName)
    except Exception as e:
        logger.error("Error " + str(e))
    try:
        drop = Drop.objects.get(name=dropName, release__product=product)
    except Exception as e:
        logger.error("Error " + str(e))
    try:
        mediaArtifact = MediaArtifact.objects.get(name=drop.release.masterArtifact.name)
        mediaArtifactVersions = ISObuild.objects.filter(drop=drop, mediaArtifact__testware=False, mediaArtifact__category__name=category).order_by('-build_date')
    except Exception as e:
        logger.error("Error: Getting media Artifact Information " + str(e))
    return mediaArtifact, mediaArtifactVersions

def getMediaArtifact(productName, dropName):
    '''
    Gets Media Artifact for the Drop
    '''
    mediaArtifact = drpMediaMaps = deliveryData = None
    mediaArtifactVersions = None
    try:
        product = Product.objects.get(name=productName)
    except Exception as e:
        logger.error("Error " + str(e))
    try:
        drop = Drop.objects.get(name=dropName, release__product=product)
    except Exception as e:
        logger.error("Error " + str(e))
    try:
        mediaArtifact = MediaArtifact.objects.get(name=drop.release.masterArtifact.name)
    except Exception as e:
        logger.error("Error: Getting media Artifact Information " + str(e))
    return mediaArtifact

def getMediaArtifactGroup(productName, dropName):
    '''
    Gets  Media Artifact Group for the Drop
    '''
    mediaArtifactGroup = None
    try:
        product = Product.objects.get(name=productName)
    except Exception as e:
        logger.error("Error " + str(e))
    try:
        drop = Drop.objects.get(name=dropName, release__product=product)
    except Exception as e:
        logger.error("Error " + str(e))
    try:
        mediaArtifact = MediaArtifact.objects.get(name=drop.release.masterArtifact.name)
        mediaArtifactVersion = ISObuild.objects.filter(drop=drop).order_by('-build_date')[0]
        mediaArtifactGroup = mediaArtifactVersion.groupId
    except Exception as e:
        logger.error("Error: Getting media Artifact Information " + str(e))
    return mediaArtifactGroup

def dropContents(productName,dropName,mediaCategory,showExcluded,excludeMediaCategory,localNexus=None,exclude=None):
    '''
    Function to return contents of a drop in json format
    '''
    try:
        dropObj=Drop.objects.get(name=dropName, release__product__name=productName)
        dropArtifactMappings = getPackageBaseline(dropObj)
        contentsList = []
        if not showExcluded:
            dropArtifactMappings = dropArtifactMappings.exclude(package_revision__isoExclude=1)
        if excludeMediaCategory:
            if "," in excludeMediaCategory:
                excludeMCList = excludeMediaCategory.split(",")
                for excludeMC in excludeMCList:
                    dropArtifactMappings = dropArtifactMappings.exclude(package_revision__category__name = str(excludeMC))
            else:
                dropArtifactMappings = dropArtifactMappings.exclude(package_revision__category__name = str(excludeMediaCategory))
        if mediaCategory and mediaCategory != "None":
            dropArtifactMappings = dropArtifactMappings.filter(package_revision__category__name = str(mediaCategory))
        if exclude == 'app':
            dropArtifactMappings = dropArtifactMappings.exclude(package_revision__infra = 0)
        if exclude == 'infra':
            dropArtifactMappings = dropArtifactMappings.exclude(package_revision__infra = 1)
        requiredFields = ("package_revision__groupId","package_revision__artifactId","package_revision__version","package_revision__package__name","package_revision__m2type","package_revision__arm_repo","kgb_test","testReport","package_revision__kgb_test","kgb_snapshot_report","package_revision__package__package_number","package_revision__category__name","package_revision__media_path","package_revision__platform","drop__name", "package_revision")
        dropArtifactMappings = dropArtifactMappings.only(requiredFields).values(*requiredFields)
        for mapping in dropArtifactMappings:
            if localNexus:
                nexusUrl = getLocalNexusUrl(productName,mapping["package_revision__groupId"],mapping["package_revision__artifactId"],mapping["package_revision__version"],mapping["package_revision__package__name"],mapping["package_revision__m2type"])
            else:
                nexusUrl = getNexusUrl(productName,mapping["package_revision__arm_repo"],mapping["package_revision__groupId"],mapping["package_revision__artifactId"],mapping["package_revision__version"],mapping["package_revision__package__name"],mapping["package_revision__m2type"])

            if mapping["kgb_test"] is not None:
                kgb = mapping["kgb_test"]
                testReport = mapping["testReport"]
                kgbSnapshotReport = mapping["kgb_snapshot_report"]
            else:
                kgb = mapping["package_revision__kgb_test"]
                testReport = getPkgRevKgbReport(mapping["package_revision"])
                kgbSnapshotReport = mapping["kgb_snapshot_report"]
            contentsListTmp = [
                        {
                            "name":mapping["package_revision__package__name"],
                            "number":mapping["package_revision__package__package_number"],
                            "url":nexusUrl,
                            "mediaCategory":mapping["package_revision__category__name"],
                            "mediaPath":str(mapping["package_revision__media_path"]),
                            "platform":mapping["package_revision__platform"],
                            "version":mapping["package_revision__version"],
                            "group":mapping["package_revision__groupId"],
                            "type":mapping["package_revision__m2type"],
                            "deliveryDrop": mapping["drop__name"],
                            "kgb": kgb,
                            "testReport": testReport,
                            "kgbSnapshotReport": kgbSnapshotReport,
                        }
                              ]
            contentsList = contentsList + contentsListTmp
    except Exception as e:
        logger.error("Issue with getting drop contents "+str(e))
        contentsList=[{"error":"error"}]
    return contentsList

def isoContents(ISOObj,productName,localNexus,exclude=None):
    '''
    Function to return contents of an ISO in json format
    '''
    try:
        localNexusUrl = None
        if exclude == 'infra':
            requiredInfraValues = [False]
        elif exclude == 'app':
            requiredInfraValues = [True]
        else:
            requiredInfraValues = [True,False]
        requiredISObuildMappingFields = ('package_revision__arm_repo','package_revision__artifactId','package_revision__m2type','package_revision__package__name','package_revision__package__package_number','package_revision__category__name','package_revision__media_path','package_revision__platform','package_revision__version','package_revision__groupId','drop__name', 'kgb_test', 'testReport', 'kgb_snapshot_report','package_revision__size')
        mediaArtifactMappings  = ISObuildMapping.objects.filter(iso=ISOObj, package_revision__infra__in=requiredInfraValues).only(requiredISObuildMappingFields).values(*requiredISObuildMappingFields)
        contentsList = []
        contentsListTmp = None
        for mapping in mediaArtifactMappings:
            contentsListTmp = [
                {
                    "name":mapping['package_revision__package__name'],
                    "number":mapping['package_revision__package__package_number'],
                    "mediaCategory":mapping['package_revision__category__name'],
                    "mediaPath":str(mapping['package_revision__media_path']),
                    "platform":mapping['package_revision__platform'],
                    "version":mapping['package_revision__version'],
                    "group":mapping['package_revision__groupId'],
                    "type":mapping["package_revision__m2type"],
                    "deliveryDrop": mapping['drop__name'],
                    "kgb": mapping['kgb_test'],
                    "testReport": mapping['testReport'],
                    "kgbSnapshotReport": mapping['kgb_snapshot_report'],
                    "size (MB)": mapping['package_revision__size'],
                }
            ]
            nexusUrl = getNexusUrl(productName,mapping['package_revision__arm_repo'],mapping['package_revision__groupId'],mapping['package_revision__artifactId'],mapping['package_revision__version'],mapping['package_revision__package__name'],mapping['package_revision__m2type'])
            contentsListTmp[0]["url"] = nexusUrl
            if str(localNexus).lower() == "true":
                localNexusUrl = getLocalNexusUrl(productName,mapping['package_revision__groupId'],mapping['package_revision__artifactId'],mapping['package_revision__version'],mapping['package_revision__package__name'],mapping['package_revision__m2type'])
                contentsListTmp[0]["localNexusUrl"] = localNexusUrl
            contentsList = contentsList + contentsListTmp
    except Exception as e:
        logger.error("Issue with getting ISO contents "+str(e))
        contentsList=[{"error":"error"}]
    return contentsList

@transaction.atomic
def uploadConfigData(product_id, choice, number, order_id):
    '''
    Function used to upload the Summary Configuration Data to the DB used by the UI and the TAF testware
    '''
    try:
        # Find out if the Product and choice are already stored in the DB
        uploadConfig,created = ConfigProducts.objects.get_or_create(product_id=product_id,choice=choice)
        # Add in any extra details to the object
        uploadConfig.num=number
        uploadConfig.order_id=order_id
        uploadConfig.active=1
        uploadConfig.save()
    except Exception as e:
        logger.error("There was an issue with the update of the Config Product Summary data within the utils file see function uploadConfigData" +str(e))
        return 1

@transaction.atomic
def createIso(group,artifact,version,drop,product,content,repo,systemInfo):
    '''
    create iso content from json input
    '''
    result = None
    jiraResult = None
    try:
        productObj = Product.objects.get(name=product)
        dropObj = Drop.objects.get(name=drop, release__product=productObj)
        mediaArtifact = MediaArtifact.objects.get(name=artifact)
        mediaType = mediaArtifact.mediaType
        testware = mediaArtifact.testware
        artifactSize = 0
        statusCode = None
        if product == "ENM":
            try:
                artifactSize, statusCode = getMediaArtifactSize(artifact, version, group, mediaType, testware)
            except Exception as e:
                logger.debug("Error: getting Media Revision Size entry " +str(e))
            if statusCode == 200:
                artifactSize = int(artifactSize)
            else:
                logger.debug("Error: There was an issue creating a new Media Revision Size entry in the CIFWK DB, Artifact Size set to 0.  Error: " +str(artifactSize))
                artifactSize = 0
        with transaction.atomic():
            isoObj = ISObuild.objects.create(version=version, mediaArtifact=mediaArtifact, drop=dropObj, build_date=datetime.now(), artifactId=artifact, groupId=group, arm_repo=repo, size=artifactSize, systemInfo=systemInfo)
            decodedContent = json.loads(content)
            for item in decodedContent:
                contentObj = Package.objects.get(name=item['name'])
                contentVersionObj = PackageRevision.objects.get(package=contentObj,version=item['version'],category__name=item['mediaCategory'])
                drpObj = Drop.objects.get(name=item['deliveryDrop'], release__product=productObj)
                createMediaArtifactVersionToArtifactMapping(product, isoObj, drpObj, contentVersionObj, item['kgb'], item['testReport'], item['kgbSnapshotReport'])
            addDeliveryGroupsToIso(isoObj)
            if developmentServer == 0 and (isoObj.mediaArtifact.category.name == "productware" or isoObj.mediaArtifact.category.name == "testware"):
                jiraResult = updateJira(product, drop, version, artifact)
            result = "Created " + str(artifact) + " Version: " + str(version) + " " + str(jiraResult)
    except Exception as e:
        errMsg = "ERROR: creating ISO: " +str(e)
        logger.error(errMsg)
        sendMediaContentIssueEmail(errMsg, artifact,version, product)
        return errMsg
    return result


def updateJira(product, drop, version,artifact):
    '''
    This function will be used to give delta between two versions of ISOs and update corresponding JIRAs
    '''
    ISOVersionList = []
    previousISOVersionList= []
    delGroupJiraMaps=[]
    delGroupList = []
    baseDropISOVersion = {}
    deliveryGroup = ''
    previousISOVersion=''
    isoDelGrpList=[]
    content=''
    jira=''
    designBaseId=''
    categoryName = "productware"
    updateJiraResult = " "
    productName = "ENM"

    try:
        jsonFields = ('iso__id','iso__version','iso__mediaArtifact__name','deliveryGroup__id','deliveryGroup_status')
        isoDelGrpObjList = list(IsotoDeliveryGroupMapping.objects.only(jsonFields).filter(iso__artifactId=artifact, iso__drop__release__product__name=productName, iso__drop__name=drop,iso__version=version).order_by('-iso__build_date','-modifiedDate').values(*jsonFields))
        requiredDropFields = ('id','designbase__id','name')
        dropObj = Drop.objects.only(requiredDropFields).values(*requiredDropFields).get(name=drop,release__product__name=product)
        designBaseId = dropObj['designbase__id']
        requiredDropIsoFields = ('id','version','mediaArtifact__testware')
        dropISOObjList = ISObuild.objects.filter(artifactId=artifact, drop__id=dropObj['id'], mediaArtifact__testware=0, mediaArtifact__category__name=categoryName).order_by('build_date').only(requiredDropIsoFields).values(*requiredDropIsoFields)
        for dropISOObj in dropISOObjList:
            if (dropISOObj['version'] != version):
                ISOVersionList.append(dropISOObj['version'])

        if (len(ISOVersionList)==0):
            previousDropISOObj = ISObuild.objects.filter(drop__id=designBaseId, mediaArtifact__testware=0, mediaArtifact__category__name=categoryName).order_by('-build_date').only('id').values('id')[0]
            previousIsoDelGrpObjList = list(IsotoDeliveryGroupMapping.objects.only(jsonFields).filter(iso__id=previousDropISOObj['id']).order_by('-iso__build_date','-modifiedDate').values(*jsonFields))
        else:
            previousISOVersion = ISOVersionList[-1]
            previousIsoDelGrpObjList = list(IsotoDeliveryGroupMapping.objects.only(jsonFields).filter(iso__artifactId=artifact, iso__drop__release__product__name=productName, iso__drop__name=drop, iso__version=previousISOVersion).order_by('-iso__build_date','-modifiedDate').values(*jsonFields))

        for isoDelGrpObjDict in isoDelGrpObjList:
            for previousIsoDelGrpObjDict in previousIsoDelGrpObjList:
                if ( isoDelGrpObjDict['deliveryGroup_status'] !=  previousIsoDelGrpObjDict['deliveryGroup_status'] and  isoDelGrpObjDict['deliveryGroup__id'] ==  previousIsoDelGrpObjDict['deliveryGroup__id']):
                    isoDelGrpList.append(isoDelGrpObjDict)
                    break
                elif(isoDelGrpObjDict['deliveryGroup_status'] !=  previousIsoDelGrpObjDict['deliveryGroup_status'] and  isoDelGrpObjDict['deliveryGroup__id'] !=  previousIsoDelGrpObjDict['deliveryGroup__id']):
                    isoDelGrpList.append(isoDelGrpObjDict)
                    break
                elif(isoDelGrpObjDict['deliveryGroup_status'] ==  previousIsoDelGrpObjDict['deliveryGroup_status'] and  isoDelGrpObjDict['deliveryGroup__id'] !=  previousIsoDelGrpObjDict['deliveryGroup__id']):
                    isoDelGrpList.append(isoDelGrpObjDict)
                    break

        jiraDelGrpMaps=''
        for isoDelGrpObjDict in isoDelGrpList:
            jiraDelGrpMaps = JiraDeliveryGroupMap.objects.only('jiraIssue__jiraNumber','deliveryGroup__id').values('jiraIssue__jiraNumber','deliveryGroup__id').filter(deliveryGroup__id=isoDelGrpObjDict['deliveryGroup__id'])
            for jiraDelGrpObjDict in jiraDelGrpMaps:
                jiraDelGrpObjDict['deliveryGroup_status'] =  isoDelGrpObjDict['deliveryGroup_status']
            delGroupJiraMaps.append(jiraDelGrpMaps)

        for jiraDelGrpObjList in delGroupJiraMaps:
            for jiraDelGrpObjDict in jiraDelGrpObjList:
                if jiraDelGrpObjDict['deliveryGroup_status'] == 'delivered':
                    content="In DG " + str(jiraDelGrpObjDict['deliveryGroup__id']) + ", Included in ISO " + str(artifact) +" version " + str(version)
                    jira = jiraDelGrpObjDict['jiraIssue__jiraNumber']
                    result = addCommentToJira(content,jira)
                    updateJiraResult += result
                else:
                    content="In DG " + str(jiraDelGrpObjDict['deliveryGroup__id']) + ", Obsoleted from ISO " + str(artifact) +" version " + str(version)
                    jira = jiraDelGrpObjDict['jiraIssue__jiraNumber']
                    result = addCommentToJira(content,jira)
                    updateJiraResult += result
    except Exception as e:
        errMsg = "Issue updating JIRA " + str(e)
        logger.error(errMsg)
        result = "ERROR:" + str(errMsg)

    return updateJiraResult


def addCommentToJira(content,jira):
    '''
    The following method will run a rest call to add comment to jira
    '''
    try:
        headers = {'Content-Type': 'application/json'}
        ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
        data = '{"update":{"comment":[{"add":{"body":"%s"}}]}}' %(content)
        jiraMigProjList = JiraMigrationProject.objects.all().values('projectKeyName')
        migKeyList = []
        for obj in jiraMigProjList:
            migKeyList.append(obj.get('projectKeyName'))
        headers.update(getJiraAccessTokenHeader())
        if jira.split('-')[0] in migKeyList:
            eTeamjiraUser = config.get('CIFWK', 'eTeamjiraUser')
            eTeamjiraPassword = config.get('CIFWK', 'eTeamjiraPassword')
            eTeamJiraRestApiUrl = config.get('CIFWK', 'eTeamJiraRestApiUrl')
            result = requests.put(str(eTeamJiraRestApiUrl) +'{0}'.format(jira),headers=headers, data=data, verify=ssl_certs)
        else:
            jiraRestCall = config.get('CIFWK','jiraRestApiUrl')
            result = requests.put(str(jiraRestCall) +'{0}'.format(jira),headers=headers, data=data, verify=ssl_certs)
        statusCode = str(result.status_code)
        if statusCode == "204":
            result = " comment successfully added to JIRA " + str(jira)
        else:
            logger.info("Jira is not available")
            result = " comment not successfully added to JIRA " + str(jira)
    except Exception as e:
        errMsg = "Issue adding comment to JIRA: " + str(jira) + str(e)
        logger.error(errMsg)
        result = "ERROR: " + str(errMsg)

    return result


def writeImportComponents(product, componentResult, result):
    '''
    The writeImportComponents function is called by the views.importComponents which updates the CI DB with Component data.
    '''
    try:
        parentObject = childObject = None
        artifactList = []
        componentResult = ast.literal_eval(componentResult)
        for key,value in componentResult.items():
            if "parent" in key:
                if Component.objects.filter(element=value, product=product).exists():
                    parentObject = Component.objects.only('id').values('id').get(element=value, product=product)
            if "child" in key:
                if Component.objects.filter(parent__id=parentObject['id'], element=value, product=product).exists():
                    childObject = Component.objects.only('element').values('element').get(parent__id=parentObject['id'], element=value, product=product)
            if "artifact" in key:
                for artifact in value:
                    artifactList.append(artifact)

        if Component.objects.filter(product=product, parent=parentObject['id'], element=childObject['element']).exists():
            componentObj = Component.objects.get(product=product, parent=parentObject['id'], element=childObject['element'])
        try:
            for artifact in artifactList:
                if Package.objects.filter(name=artifact).exists():
                    packageObj = Package.objects.get(name=artifact)
                    PackageComponentMapping.objects.get_or_create(component=componentObj, package=packageObj)
        except Exception as e:
            logger.error("Issue posting component data to CI DB " + str(e))
            result = json.dumps([{"error":str(e)}])
    except Exception as e:
        logger.error("Issue posting component data to CI DB " + str(e))
        result = json.dumps([{"error":str(e)}])
    return result

def removeComponents(product, componentResult, result):
    '''
    The removeComponents function is called by the cireports view which removes component data from the CI DB.
    '''
    try:
        parentObject = childObject = None
        artifactList = []
        componentResult = ast.literal_eval(componentResult)
        for key,value in componentResult.items():
            if "parent" in key:
                if Component.objects.filter(element=value, product=product).exists():
                    parentObject = Component.objects.only('id').values('id').get(element=value, product=product)
            if "child" in key:
                if Component.objects.filter(parent__id=parentObject['id'], element=value, product=product).exists():
                    childObject = Component.objects.only('element').values('element').get(parent__id=parentObject['id'], element=value, product=product)
            if "artifact" in key:
                for artifact in value:
                    artifactList.append(artifact)

        if Component.objects.filter(product=product, parent__id=parentObject['id'], element=childObject['element']).exists():
            componentObj = Component.objects.get(product=product, parent__id=parentObject['id'], element=childObject['element'])
        try:
            for artifact in artifactList:
                if Package.objects.filter(name=artifact).exists():
                    packageObj = Package.objects.get(name=artifact)
                    packageComponentMapObj = PackageComponentMapping.objects.get(component=componentObj, package=packageObj)
                    packageComponentMapObj.delete()
        except Exception as e:
            logger.error("Issue removing component data from CI DB " + str(e))
            result = json.dumps([{"error":str(e)}])
    except Exception as e:
        logger.error("Issue posting component data from CI DB " + str(e))
        result = json.dumps([{"error":str(e)}])
    return result

def getInfraPackages(productName,dropName,isoVer=None):
    '''
    The getInfraPackages function returns packages that are of type Infrastructure in json format
    '''
    try:
        tmpList = []
        infraPackages = []
        if isoVer is None:
            dropObj = Drop.objects.get(name=dropName, release__product__name=productName)
            dropPkgMaps = getPackageBaseline(dropObj)
            for mapping in dropPkgMaps:
                if mapping.package_revision.infra:
                    tmpList = [{
                                "name":mapping.package_revision.package.name,
                                "number":mapping.package_revision.package.package_number,
                                "mediaCategory":mapping.package_revision.category.name,
                                "version":mapping.package_revision.version,
                                "group":mapping.package_revision.groupId,
                                "nexusLink":mapping.package_revision.getNexusUrl(productName),
                            }]
                    infraPackages = infraPackages + tmpList
        else:
            isoPkgMaps = ISObuildMapping.objects.filter(iso__version=isoVer)
            for mapping in isoPkgMaps:
                if mapping.package_revision.infra:
                    tmpList = [{
                                "name":mapping.package_revision.package.name,
                                "number":mapping.package_revision.package.package_number,
                                "mediaCategory":mapping.package_revision.category.name,
                                "version":mapping.package_revision.version,
                                "group":mapping.package_revision.groupId,
                                "nexusLink":mapping.package_revision.getNexusUrl(productName),
                            }]
                    infraPackages = infraPackages + tmpList
    except Exception as e:
        logger.error("Issue trying to retreive infrastructure packages "+str(e))
        infraPackages=[{"error":"error"}]
    return infraPackages

def getMediaArtifactStatusReport(product,drop,isoVersion,sutType,testRun):
    '''
     For KGB READY and CAUTION Status
    '''
    category = "productware"
    testResultsObj = testwareObj = None
    prodSet = reportDirectory = mediaObj = time = prodSet = pageContent = noReportDirectory = None
    try:
        mediaObj = ISObuild.objects.get(version=isoVersion, drop__name=drop, drop__release__product__name=product, mediaArtifact__testware=False, mediaArtifact__category__name=category)
        testwareObj=ISOTestResultsToTestwareMap.objects.filter(testware_run_id=testRun)
        testResultsObj=TestResults.objects.get(id=testRun)
    except Exception as e:
        logger.error("Error Getting Testware Run Information: " +str(e))

    try:
        if not testResultsObj == None:
            report= testResultsObj.test_report
            reportDirectory = testResultsObj.test_report_directory
            if reportDirectory.startswith("cdb_"):
                [dir, rest] = reportDirectory.split("/", 1)
                partTime = dir.replace("cdb_", "").replace("T", " ")
                [time, mil] = partTime.split(".")
                filePath = config.get('REPORT', 'filePath')
                reportDirectory = filePath+"/"+reportDirectory
    except Exception as e:
        logger.error("Error Getting Report Directory and Time Information: " +str(e))
        report = reportDirectory = pageContent =  None

    if reportDirectory:
        try:
            file = open(reportDirectory, 'r')
            pageContent = file.read()
            if "AOM" in pageContent:
                prodSet = "True"
        except Exception as e:
            logger.error("Error Getting Report: " +str(e))
            report = reportDirectory = None
            noReportDirectory = "There is no Report"
    else:
        noReportDirectory = "There is no Report"

    return mediaObj, sutType, time, prodSet, pageContent, noReportDirectory


def getProductSetStatusReport(drop,productSetVersionId,sutType,testRun):
    '''
    For KGB READY and CAUTION Status
    '''

    productSetVersionObj=ProductSetVersion.objects.get(id=productSetVersionId)
    productSetNum=productSetVersionObj.productSetRelease.number
    productSetRel=productSetVersionObj.productSetRelease.name
    productSetVersion=productSetVersionObj.version
    productSet = productSetVersionObj.productSetRelease.productSet.name
    identityString=productSet+" "+productSetRel+" "+productSetNum+" Ver: "+productSetVersion
    prodSet = reportDirectory = mediaObj = time = prodSet = pageContent = noReportDirectory = None
    testResultsObj = testwareObj = None
    try:
        testwareObj=ISOTestResultsToTestwareMap.objects.filter(testware_run_id=testRun)
        testResultsObj=TestResults.objects.get(id=testRun)
    except Exception as e:
        logger.error("Error Getting Testware Run Information: " +str(e))

    try:
       if not testResultsObj == None:
         report= testResultsObj.test_report
         reportDirectory = testResultsObj.test_report_directory
         if reportDirectory.startswith("cdb_"):
            [dir, rest] = reportDirectory.split("/", 1)
            partTime = dir.replace("cdb_", "").replace("T", " ")
            [time, mil] = partTime.split(".")
            filePath = config.get('REPORT', 'filePath')
            reportDirectory = filePath+"/"+reportDirectory
    except Exception as e:
        logger.error("Error Getting Report Directory and Time Information: " +str(e))
        report = reportDirectory =  None

    if reportDirectory:
        try:
            file = open(reportDirectory, 'r')
            pageContent = file.read()
        except Exception as e:
            logger.error("Error Getting Report: " +str(e))
            report = reportDirectory = None
            noReportDirectory = "There is no Report"
    else:
        noReportDirectory = "There is no Report"

    return productSet, mediaObj, time, prodSet, pageContent, noReportDirectory


def getLatestIso(product, drop, release=None, passedOnly=False):
    '''
    Getting Latest ISO Version that has passed testing or lastest in that Drop
    '''
    category = "productware"
    isoName=None
    isoVersion=None
    dropId = None
    releaseObj = None
    mediaArtifacts = None
    dropObj = None
    try:
        if release:
            try:
                releaseObj = Release.objects.get(name=release, product__name=product)
                logger.debug("Queried release is :" +str(releaseObj))
            except Exception as e:
                logger.error("Issue getting release: " + str(e))
        if drop:
            try:
                if releaseObj:
                    dropObj = Drop.objects.only('id').values('id').get(name=drop, release=releaseObj)
                else:
                    dropObj = Drop.objects.only('id').values('id').get(name=drop, release__product__name=product)
                dropId = dropObj['id']
            except Exception as e:
                logger.error("Issue getting Drop: " + str(e))
        elif releaseObj:
            try:
                dropObj = Drop.objects.only('id').values('id').filter(release=releaseObj, correctionalDrop=False).latest("id")
                dropId = dropObj['id']
            except Exception as e:
                logger.error("Issue getting Drop using Release: " + str(e))
        else:
            try:
                dropObj = Drop.objects.only('id').values('id').filter(release__product__name=product, correctionalDrop=False).exclude(release__name__icontains="test").latest("id")
                dropId = dropObj['id']
            except Exception as e:
                logger.error("Issue getting Drop using Product: " + str(e))

        if ISObuild.objects.filter(drop__id=dropId, mediaArtifact__testware=0, mediaArtifact__category__name=category).exists():
            mediaArtifacts = ISObuild.objects.filter(drop__id=dropId, mediaArtifact__testware=0, mediaArtifact__category__name=category).order_by('-id')
            mediaValues = 'artifactId', 'version'
            if passedOnly is None:
                for item in mediaArtifacts:
                    if item.overall_status:
                        if str(item.getOverallWeigthedStatus()) == 'passed' or str(item.overall_status.state) == 'passed_manual':
                            if str(item.overall_status.state) != 'caution':
                                isoName = str(item.artifactId)
                                isoVersion = str(item.version)
                                break
                if not isoVersion:
                    try:
                        latestIso = ISObuild.objects.only(mediaValues).values(*mediaValues).filter(drop__id=dropId, mediaArtifact__testware=0, mediaArtifact__category__name=category).order_by('-id')[0]
                        isoName = latestIso['artifactId']
                        isoVersion = latestIso['version']
                    except Exception as e:
                        logger.error("Issue getting latestIso: " + str(e))
            else:
                if passedOnly:
                    for item in mediaArtifacts:
                        if item.overall_status:
                            if str(item.getOverallWeigthedStatus()) == 'passed' or str(item.overall_status.state) == 'passed_manual':
                                if str(item.overall_status.state) != 'caution':
                                    isoName = str(item.artifactId)
                                    isoVersion = str(item.version)
                                    break
                    if not isoVersion:
                        designBaseId = Drop.objects.only('designbase_id').values('designbase_id').get(id=dropId)['designbase_id']
                        if Drop.objects.filter(id=designBaseId).exists():
                            designBase = Drop.objects.get(id=designBaseId)
                            baseReleaseId = designBase.release_id
                            baseRelease = Release.objects.get(id=baseReleaseId)
                            isoName, isoVersion = cireports.utils.getLatestIso(baseRelease.product.name, designBase.name, baseRelease.name, passedOnly)
                        else:
                            logger.debug("No passed ISOs found in: " +str(product))
                            isoName = None
                            isoVersion = None
                else:
                    try:
                        latestIso = ISObuild.objects.only(mediaValues).values(*mediaValues).filter(drop__id=dropId, mediaArtifact__testware=0, mediaArtifact__category__name=category).order_by('-id')[0]
                        isoName = latestIso['artifactId']
                        isoVersion = latestIso['version']
                    except Exception as e:
                        logger.error("Issue getting latestIso: " + str(e))
        else:
            logger.debug("Drop does not exist :" +str(drop))

    except Exception as e:
        logger.error("Invalid Information: Product("+str(product)+")--Release("+str(release)+")--Drop("+str(drop)+"): Error: " +str(e))
    return isoName, isoVersion

def compareIsoMd5(hostedNexusMd5Url, hubNexusMd5Url):
    try:
        command = 'curl -f --url "' + hostedNexusMd5Url +'"'
        runMd5RestCall = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd="/tmp")
        localMd5 = runMd5RestCall.stdout.readline()

        command = 'curl -f --url "' + hubNexusMd5Url +'"'
        runMd5RestCall = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd="/tmp")
        hubMd5 = runMd5RestCall.stdout.readline()

        if not str(localMd5) == "" and not str(hubMd5) == "":
            if localMd5 == hubMd5:
                return "SUCCESS"
            else:
                return "ERROR: md5s of ISOs do not match!"
        elif str(localMd5) == "":
            return "ERROR: Unable to retrieve md5 from hosted repo"
        else:
            return "ERROR: Unable to retrieve md5 from E2C repo"
    except Exception as e:
        return "ERROR: Unable to connect to Nexus server; " +str(e)

def getArtifactsFromComponent(component,subComponent,product):
    '''
    Get artifacts from component/subcomponent
    '''
    packageList=[]
    try:
        parent=Component.objects.get(element=component,product__name=product)
        if subComponent:
            children=Component.objects.filter(parent=parent,element=subComponent)
        else:
            children=Component.objects.filter(parent=parent)
        for item in children:
            mappings=PackageComponentMapping.objects.filter(component=item)
            for map in mappings:
                packageList.append(str(map.package.name))
    except Exception as e:
        logger.error("Issue getting artifacts from components "+str(e))
    return packageList

def partialIsoContents(isoVersion,isoName, matchingDropArtifacts,manualList):
    '''
    Function to return partial contents of an ISO
    '''
    returnString = ""
    try:
        ISOObj = ISObuild.objects.get(version=isoVersion, mediaArtifact__name=isoName)
        mediaArtifactMappings  = ISObuildMapping.objects.filter(iso=ISOObj)
        isoContentsString = ""
        for mapping in mediaArtifactMappings:
            isoContentsString = isoContentsString+mapping.package_revision.package.name+"::"+mapping.package_revision.version
        for item in matchingDropArtifacts:
            name,version=item.split('::')
            if name+"::" in manualList:
                continue
            if item not in isoContentsString:
                if returnString == "":
                    returnString = returnString + item
                else:
                    returnString = returnString +"||" + item
    except Exception as e:
        logger.error("Issue getting ISO contents "+str(e))
    return returnString

def partialDropContents(dropName,productName,componentList):
    '''
    Function to return partial contents of a Drop
    '''
    contentsList = []
    try:
        dropObj=Drop.objects.get(name=dropName, release__product__name=productName)
        dropArtifactMappings = getPackageBaseline(dropObj)
        contentVersionsList = []
        for mapping in dropArtifactMappings:
            for componentArtifact in componentList:
                if componentArtifact == mapping.package_revision.package.name:
                    contentsList.append(mapping.package_revision.package.name+"::"+mapping.package_revision.version)
    except Exception as e:
        logger.error("Issue getting Drop contents "+str(e))
    return contentsList

def intendedDropContents(dropName,productName,componentList):
    '''
    Function to return latest versions for intended drop
    '''
    contentsList = []
    try:
        contentVersionsList = []
        intendedDrop= productName+":"+dropName
        for componentArtifact in componentList:
            if PackageRevision.objects.filter(package__name=componentArtifact,autodrop=intendedDrop).exists():
                packageRevisionObj = PackageRevision.objects.filter(package__name=componentArtifact,autodrop=intendedDrop).order_by('-date_created')[0]
            elif PackageRevision.objects.filter(package__name=componentArtifact).exists():
                packageRevisionObj = PackageRevision.objects.filter(package__name=componentArtifact).order_by('-date_created')[0]
            else:
                continue
            version = packageRevisionObj.version
            contentsList.append(componentArtifact+"::"+version)
    except Exception as e:
        logger.error("Issue getting intended Drop contents "+str(e))
    return contentsList

def getDropsDesignBaseLatestISOVersion(drop,dropObj,product,testware,isoVersion, category):
    '''
    The getDropsDesignBase function takes in two parameters (drop and product) and returns a drops design bases latest ISO Version if found.
    '''
    try:

        if dropObj:
            dropid = dropObj['id']
            designBaseId = dropObj['designbase__id']

        requiredBaseDropISOVersionFields = ('id','version','drop__name')
        baseDropISOVersionFields = ISObuild.objects.only(requiredBaseDropISOVersionFields).values(*requiredBaseDropISOVersionFields).filter(drop__id=dropObj['id'],mediaArtifact__testware=testware, mediaArtifact__category__name=category).order_by('build_date')
        if baseDropISOVersionFields:
            for index in range(len(baseDropISOVersionFields)):
                baseDropISOVersion = baseDropISOVersionFields[index]
                if baseDropISOVersion['version'] and baseDropISOVersion['version'] == isoVersion:
                    if index == 0:
                        if designBaseId:
                            requiredBaseDropFields = ('id',)
                            baseDrop = Drop.objects.only(requiredBaseDropFields).values(*requiredBaseDropFields).get(id=designBaseId)
                            if not baseDrop:
                                return "Info: No design base found for drop" + str(drop) + ".\n"
                            baseDropISOVersionFields = ISObuild.objects.only(requiredBaseDropISOVersionFields).values(*requiredBaseDropISOVersionFields).filter(drop__id=baseDrop['id'],mediaArtifact__testware=testware, mediaArtifact__category__name=category).order_by('-build_date')
                            if baseDropISOVersionFields:
                                baseDropISOVersion = baseDropISOVersionFields[0]
                                if baseDropISOVersion['version'] and baseDropISOVersion['version']:
                                    return baseDropISOVersion
                    else:
                        return baseDropISOVersionFields[index-1]
        return "Info: No design base found for drop" + str(drop) + " or no ISO Version found in design Base, please try again.\n"
    except Exception as e:
        logger.error("Error: Unable to find design base drop iso version." + str(e))
        return "Info: Unable to find design base drop iso version.\n"

def returnISOVersionArtifactDelta(product,drop,isoVersion,previousIsoVer=None, previousDrop=None, followDrop=None,testware=False):
    '''
    The returnISOVersionArtifactDelta function builds up a ISO Version Artifact Delta with Previous ISO Version in a Drop based on local DB entries which is passed
    to the buildISOVersionArtifcatDeltaJSON function which in turn returns a JSON object based on this list
    '''
    ISOVersionList = []
    currentISOPackageRevList = []
    previousISOPackageRevList = []
    baseDropISOVersion = {}
    ISODeltaDict = {}
    localISOVersion = previousIsoVer
    category = "productware"
    try:
        if isinstance(testware, basestring):
            if testware.lower() == 'true':
                testware = True
                category = "testware"
            else:
                testware = False
        requiredDropFields = ('id','designbase__id','name')
        dropObj = Drop.objects.only(requiredDropFields).values(*requiredDropFields).get(name=drop,release__product__name=product)
        if followDrop != None:
            baseDropISOVersion = getDropsDesignBaseLatestISOVersion(drop,dropObj,product,testware,isoVersion, category)
            if "Info:" in str(baseDropISOVersion):
                return str(baseDropISOVersion), ISODeltaDict, localISOVersion, previousDrop
    except Drop.DoesNotExist:
        return "Error: Drop: " + str(drop) + " does not exist in product: " + str(product) + ", please try again\n", ISODeltaDict, localISOVersion, previousDrop

    if previousIsoVer == None:
        try:
            requiredDropIsoFields = ('id','version')
            dropISOObjList = ISObuild.objects.filter(drop__id=dropObj['id'], mediaArtifact__testware=testware, mediaArtifact__category__name=category).order_by('build_date').only(requiredDropIsoFields).values(*requiredDropIsoFields)
            for dropISOObj in dropISOObjList:
                if dropISOObj['version'] != isoVersion:
                    ISOVersionList.append(dropISOObj['version'])
                else:
                    break
        except Exception as e:
            logger.error("Error: No ISO Version found for drop: " + str(drop) + str(e))
            return "Error: No ISO Version found for drop: " + str(drop) + ", please try again\n", ISODeltaDict, localISOVersion, previousDrop
    if ISOVersionList:
        localISOVersion = ISOVersionList[-1]
        localDrop = drop
    elif previousIsoVer != None:
        localISOVersion = previousIsoVer
        if previousDrop != None:
            localDrop = previousDrop
        else:
            localDrop = drop
    elif baseDropISOVersion and baseDropISOVersion['id']:
        localISOVersion = baseDropISOVersion['version']
        localDrop = baseDropISOVersion['drop__name']
        previousISOObj = baseDropISOVersion
    else:
        return "Info: ISO Version: " + str(isoVersion) + " is the first ISO Version in this drop: " + str(drop) + ", please try again\n", ISODeltaDict, localISOVersion, previousDrop

    if baseDropISOVersion and baseDropISOVersion['id'] and not ISOVersionList and not previousIsoVer:
        previousISOObj = baseDropISOVersion
    else:
        try:
            requiredPreviousISOValues = ('id','version','artifactId')
            previousISOObj = ISObuild.objects.only(requiredPreviousISOValues).values(*requiredPreviousISOValues).get(version=localISOVersion,drop__name=localDrop, drop__release__product__name=product, mediaArtifact__testware=testware, mediaArtifact__category__name=category)
        except ISObuild.DoesNotExist:
            return "Error: ISO Version: " + str(localISOVersion) + " was not found, please try again\n", ISODeltaDict, localISOVersion, previousDrop

    try:
        requiredCurrentISOValues = ('id','version','groupId','artifactId')
        currentISOObj = ISObuild.objects.only(requiredCurrentISOValues).values(*requiredCurrentISOValues).get(version=isoVersion,drop__name=drop,drop__release__product__name=product, mediaArtifact__testware=testware, mediaArtifact__category__name=category)
    except ISObuild.DoesNotExist:
        return "Error: ISO Version: " + str(isoVersion)  + " was not found, please try again\n", ISODeltaDict, localISOVersion, previousDrop

    try:
        requiredCurrentISOMappingValues = ('package_revision__id','package_revision__package__name','package_revision__groupId','package_revision__artifactId','package_revision__version', 'package_revision__category__name')
        currentISOPackageRevList = ISObuildMapping.objects.filter(iso__id=currentISOObj['id']).only(requiredCurrentISOMappingValues).values(*requiredCurrentISOMappingValues)
        if len(currentISOPackageRevList) == 0 :
            return "Error: The artifact "+ currentISOObj['artifactId'] +"::"+currentISOObj['version']+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+product+"\n", ISODeltaDict, localISOVersion, previousDrop
    except Exception as e:
        logger.error("There is no Package Revision Mapping for Current ISO Version: " + str(currentISOObj['version']) + str(e))
        return "Error: The artifact "+ str(currentISOObj['artifactId']) +"::"+str(currentISOObj['version'])+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+str(product)+"\n", ISODeltaDict, localISOVersion, previousDrop

    try:
        requiredPreviousISOMappingValues = ('package_revision__id','package_revision__package__name','package_revision__groupId','package_revision__artifactId','package_revision__version', 'package_revision__category__name')
        previousISOPackageRevList = ISObuildMapping.objects.filter(iso__id=previousISOObj['id']).only(requiredPreviousISOMappingValues).values(*requiredPreviousISOMappingValues)
        if len(previousISOPackageRevList) == 0 :
            return "Error: The artifact "+ str(previousISOObj['artifactId']) +"::"+str(previousISOObj['version'])+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+str(product)+"\n", ISODeltaDict, localISOVersion, previousDrop
    except Exception as e:
        logger.error("Unable to find Package Revision Mapping for Previous ISO Version: " + str(previousISOObj['version']) + str(e))
        return "Error: The artifact "+ str(previousISOObj['artifactId']) +"::"+str(previousISOObj['version'])+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+str(product)+"\n", ISODeltaDict, localISOVersion, previousDrop

    previousDropObj=Drop.objects.only(requiredDropFields).values(*requiredDropFields).get(name=localDrop,release__product__name=product)

    response, ISODeltaDict = buildISOVersionArtifcatDeltaJSON(product, dropObj, previousDropObj, previousISOPackageRevList, currentISOPackageRevList, currentISOObj['version'], previousISOObj['version'], currentISOObj['groupId'], currentISOObj['artifactId'])

    return response, ISODeltaDict, localISOVersion, previousDropObj['name']

def buildISOVersionArtifcatDeltaJSON(product, dropObj, previousDropObj, previousISOPackageRevList, currentISOPackageRevList, currentISOVersion, previousISOVersion, currentISOGroupId, currentISOArtifactId):
    '''
    The buildISOVersionArtifcatDeltaJSON function builds up an ISO Version Artifact Delta with Previous ISO Version in a Drop, or between drops, and returns this delta in a JSON Object
    '''
    obsoletedDict = {}
    obsoletedString = ""
    updatedDict = {}
    updatedString = ""
    addedDict = {}
    addedString = ""
    deliveryGroupDict = {}
    deliveryGroupAllDict = {}
    finalString = ""
    updatedList = []
    addedList = []
    ISODeltaDict = {}
    packageDeliveryGroupDict = {}
    packageDeliveryGroupList = []

    try:
        finalString = '"groupId" : "' + str(currentISOGroupId) + '","artifactId" : "' + str(currentISOArtifactId) + '","previousVersion" : "' + str(previousISOVersion) + '","version" : "' + str(currentISOVersion) + '",'
        prevISODeltaList = [prevISOPackageRev for prevISOPackageRev in previousISOPackageRevList if prevISOPackageRev not in currentISOPackageRevList]
        for ISODelta in prevISODeltaList:
            if str(ISODelta['package_revision__package__name']) not in str(list(currentISOPackageRevList)):
                obsoletedDict["groupId"] = str(ISODelta['package_revision__groupId'])
                obsoletedDict["artifactId"] = str(ISODelta['package_revision__artifactId'])
                obsoletedDict["version"] = str(ISODelta['package_revision__version'])
                obsoletedDict["category"] = str(ISODelta['package_revision__category__name'])
                obsoletedString = obsoletedString + str(obsoletedDict) + ","

        currISODeltaList = [currentISOPackageRev for currentISOPackageRev in currentISOPackageRevList if currentISOPackageRev not in previousISOPackageRevList]
        if "ENM" == str(product):
            deliveryGroupAllDict = getDropDeliveryGroupData(dropObj, previousDropObj)
        for ISODelta in currISODeltaList:
            if str(ISODelta['package_revision__package__name']) not in str(list(previousISOPackageRevList)):
                addedDict["groupId"] = str(ISODelta['package_revision__groupId'])
                addedDict["artifactId"] = str(ISODelta['package_revision__artifactId'])
                addedDict["version"] = str(ISODelta['package_revision__version'])
                addedDict["category"] = str(ISODelta['package_revision__category__name'])
                if "ENM" == str(product) and deliveryGroupAllDict:
                    delGroupList = deliveryGroupAllDict['DeliveryGroupData']
                    for groupData in delGroupList:
                        if str(ISODelta['package_revision__artifactId']) == groupData['artifact'] and str(ISODelta['package_revision__version']) == groupData['version']:
                            addedDict["deliveryGroup"] = str(groupData['group'])
                            addedDict["drop"] = str(groupData['drop'])
                            addedDict["deliveryGroupStatus"] = str(groupData['status'])
                            #For the Delivery Group Items Section
                            packageDeliveryGroupDict["group"] = str(groupData['group'])
                            packageDeliveryGroupDict["drop"] = str(groupData['drop'])
                            packageDeliveryGroupDict["status"] = str(groupData['status'])
                            packageDeliveryGroupList.append(packageDeliveryGroupDict)
                            packageDeliveryGroupDict = {}
                addedString = addedString + str(addedDict) + ","
                addedList.append(ISODelta['package_revision__id'])
            else:
                updatedDict["downgrade"] = "false"
                updatedDict["groupId"] = str(ISODelta['package_revision__groupId'])
                updatedDict["artifactId"] = str(ISODelta['package_revision__artifactId'])
                updatedDict["version"] = str(ISODelta['package_revision__version'])
                updatedDict["category"] = str(ISODelta['package_revision__category__name'])
                if "ENM" == str(product) and deliveryGroupAllDict:
                    delGroupList = deliveryGroupAllDict['DeliveryGroupData']
                    for groupData in delGroupList:
                        if str(ISODelta['package_revision__artifactId']) == groupData['artifact'] and str(ISODelta['package_revision__version']) == groupData['version']:
                            updatedDict["deliveryGroup"] = str(groupData['group'])
                            updatedDict["drop"] = str(groupData['drop'])
                            updatedDict["deliveryGroupStatus"] = str(groupData['status'])
                            #For the Delivery Group Items Section
                            packageDeliveryGroupDict["group"] = str(groupData['group'])
                            packageDeliveryGroupDict["drop"] = str(groupData['drop'])
                            packageDeliveryGroupDict["status"] = str(groupData['status'])
                            packageDeliveryGroupList.append(packageDeliveryGroupDict)
                            packageDeliveryGroupDict = {}

                for previousISOPackageRev in previousISOPackageRevList:
                    if str(previousISOPackageRev['package_revision__package__name']) == str(ISODelta['package_revision__package__name']):
                        updatedDict["previousVersion"] = str(previousISOPackageRev['package_revision__version'])
                        compare = compareVersions(updatedDict["previousVersion"], updatedDict["version"])
                        if compare == 2:
                            updatedDict["downgrade"] = "true"
                updatedString = updatedString + str(updatedDict) + ","
                updatedList.append(str(ISODelta['package_revision__id'])+ "#" + str(updatedDict["downgrade"]))

        if obsoletedString:
            obsoletedString = obsoletedString[:-1]
            obsoletedString = '"Obsoleted":[' + obsoletedString + '],'
        if updatedString:
            updatedString = updatedString[:-1]
            updatedString = '"Updated":[' + updatedString + '],'
        if addedString:
            addedString = addedString[:-1]
            addedString = '"Added":[' + addedString + '],'

        if not obsoletedString and not updatedString and not addedString:
            return "Info: There is no Difference between Previous ISO Version: " + str(previousISOVersion) + " and this ISO Version: " + str(currentISOVersion) + " on Current ISO GAV: " + str(finalString) + " please try again\n", ISODeltaDict

        ISODeltaDict['new'] = addedList
        ISODeltaDict['updated'] = updatedList

        finalString = finalString + obsoletedString + updatedString + addedString
        if finalString:
            finalString = "[{" + finalString[:-1] + "}]"
            finalString = finalString.replace("'", "\"")
    except Exception as error:
        errorMsg = "Error: There was an issue building ISO Version Artifact Delta JSON: " + str(error)
        logger.error(errorMsg)
        return errorMsg, ISODeltaDict

    return finalString, ISODeltaDict

def getISOTestwareBuildGivenISOProductBuild(productISOArtifactName, productISOVersion, testwareISOArtifactName, testwareISOVersion, dropObj):
    '''
    The getISOTestwareBuildGivenISOProductBuild returns product and testware media artifact when product media name and version is known.
    '''
    productISOBuildObj = testwareISOBuildObj = response = ""
    try:
        if MediaArtifact.objects.filter(name=productISOArtifactName,testware=False).exists():
            productISOObj = MediaArtifact.objects.get(name=productISOArtifactName)
            if ISObuild.objects.filter(mediaArtifact=productISOObj,drop=dropObj,version=productISOVersion).exists():
                productISOBuildObj = ISObuild.objects.get(mediaArtifact=productISOObj,drop=dropObj,version=productISOVersion)
                if testwareISOArtifactName and testwareISOVersion:
                    if MediaArtifact.objects.filter(name=testwareISOArtifactName).exists():
                        testwareISOObj = MediaArtifact.objects.get(name=testwareISOArtifactName)
                        if ISObuild.objects.filter(mediaArtifact=testwareISOObj,drop=dropObj,version=testwareISOVersion).exists():
                            testwareISOBuildObj = ISObuild.objects.get(mediaArtifact=testwareISOObj,drop=dropObj,version=testwareISOVersion)
                        else:
                            response = ("Error: ISO Media Artifact Name: '" + str(testwareISOArtifactName) + "' Version: '" + str(testwareISOVersion) + "' does not exist, please try again.\n")
                            logger.error(response)
                            return productISOBuildObj, testwareISOBuildObj, response
                    else:
                        response = ("Error: ISO Media Artifact Name: '" + str(testwareISOArtifactName) + "', does not exist, please try again.\n")
                        logger.error(response)
                        return productISOBuildObj, testwareISOBuildObj, response
                else:
                    testwareISOMediaArtifactName = ISObuild.objects.filter(drop=dropObj).exclude(mediaArtifact=productISOObj)
                    if testwareISOMediaArtifactName:
                        testwareISOMediaArtifactName = testwareISOMediaArtifactName[0]
                        testwareISOBuildObj = ISObuild.objects.filter(drop=dropObj,mediaArtifact=testwareISOMediaArtifactName.mediaArtifact.id).order_by('-id')[0]
                    else:
                        response = ("Warning: There is no Testware Media Artifact for this drop: '" + str(dropObj) + "', therefore no mapping will be created, please try again.\n")
                        logger.warn(response)
                        return productISOBuildObj, testwareISOBuildObj, response
            else:
                response = ("Error: ISO Media Artifact Name: '" + str(productISOArtifactName) + "' Version: '" + str(productISOVersion) + "' does not exist, please try again.\n")
                logger.error(response)
                return productISOBuildObj, testwareISOBuildObj, response
        else:
            response = ("Error: ISO Media Artifact Name: '" + str(productISOArtifactName) + "', as Product Media Artifact, does not exist, please try again.\n")
            logger.error(response)
            return productISOBuildObj, testwareISOBuildObj, response
    except Exception as error:
        response = ("Error: There was an error in getting ISO Product Media Object to Testware ISO Media Object Mapping: '" +str(error) + "', please investigate\n")
        logger.error(response)
        return productISOBuildObj, testwareISOBuildObj, response
    return productISOBuildObj, testwareISOBuildObj, response

def getISOProductBuildGivenISOTestwareBuild(productISOArtifactName, productISOVersion, testwareISOArtifactName, testwareISOVersion, dropObj):
    '''
    The getISOProductBuildGivenISOTestwareBuild returns product and testware media artifact when testware media name and version is known.
    '''
    productISOBuildObj = testwareISOBuildObj = response = ""
    try:
        if MediaArtifact.objects.filter(name=testwareISOArtifactName,testware=True).exists():
            testwareISOObj = MediaArtifact.objects.get(name=testwareISOArtifactName)
            if ISObuild.objects.filter(mediaArtifact=testwareISOObj,drop=dropObj,version=testwareISOVersion).exists():
                testwareISOBuildObj = ISObuild.objects.get(mediaArtifact=testwareISOObj,drop=dropObj,version=testwareISOVersion)
                if productISOArtifactName and productISOVersion:
                    if MediaArtifact.objects.filter(name=productISOArtifactName).exists():
                        productISOObj = MediaArtifact.objects.get(name=productISOArtifactName)
                        if ISObuild.objects.filter(mediaArtifact=productISOObj,drop=dropObj,version=productISOVersion).exists():
                            productISOBuildObj = ISObuild.objects.get(mediaArtifact=productISOObj,drop=dropObj,version=productISOVersion)
                        else:
                            reponse = ("Error: ISO Media Artifact Name: '" + str(productISOArtifactName) + "' Version: '" + str(productISOVersion) + "' does not exist, please try again.\n")
                            logger.error(response)
                            return productISOBuildObj, testwareISOBuildObj, response
                else:
                    productISOMediaArtifactName = ISObuild.objects.filter(drop=dropObj, mediaArtifact__category__name="productware").exclude(mediaArtifact=testwareISOObj)
                    if productISOMediaArtifactName:
                        productISOMediaArtifactName = productISOMediaArtifactName[0]
                        productISOBuildObj = ISObuild.objects.filter(drop=dropObj, mediaArtifact=productISOMediaArtifactName.mediaArtifact.id).order_by('-id')[0]
                    else:
                        response = ("Warning: There is no Product Media Artifact for this drop: '" + str(dropObj) + "', therefore no mapping will be created, please try again.\n")
                        logger.warn(response)
                        return productISOBuildObj, testwareISOBuildObj, response
            else:
                response = ("Error: ISO Media Artifact Name: '" + str(testwareISOArtifactName) + "' Version: '" + str(testwareISOVersion) + "' does not exist, please try again.\n")
                logger.error(response)
                return productISOBuildObj, testwareISOBuildObj, response
        else:
            response = ("Error: ISO Media Artifact Name: '" + str(testwareISOArtifactName) + "' as Testware Media Artifact does not exist, please try again.\n")
            logger.error(response)
            return productISOBuildObj, testwareISOBuildObj, response
    except Exception as error:
        response = ("Error: There was an error in getting ISO Testware Media Object to Product ISO Media Object Mapping: '" +str(error) + "', please investigate.\n")
        logger.error(response)
        return HttpResponse(response)
    return productISOBuildObj, testwareISOBuildObj, response


def getPackagesInISO(iso, testwareContents, useLocalNexus):
    packagesDetails = {"ISOName":"",
            "ISOVersion":"",
            "ISOGroupID":"",
            "TestwareISOName":"",
            "TestwareISOVersion":"",
            "TestwareGroupID": "",
            "PackagesInISO":""}

    if iso.mediaArtifact.testware:
        testwareISO=iso
        iso = ProductTestwareMediaMapping.objects.filter(testwareIsoVersion=testwareISO).order_by('-id')[0].productIsoVersion
    else:
        if ProductTestwareMediaMapping.objects.filter(productIsoVersion=iso).exists():
            testwareISO = ProductTestwareMediaMapping.objects.filter(productIsoVersion=iso).order_by('-id')[0].testwareIsoVersion
        else:
            if testwareContents:
                return {"ERROR":"ERROR: No mapping to testware for this ISO"}

    if str(testwareContents).lower() == "true":
        isoContent = isoContents(testwareISO,testwareISO.drop.release.product.name,useLocalNexus,exclude=None)
    else:
        isoContent = isoContents(iso,iso.drop.release.product.name,useLocalNexus,exclude=None)

    packagesDetails["ISOName"] = iso.mediaArtifact.name
    packagesDetails["ISOVersion"] = iso.version
    packagesDetails["ISOGroupID"] = iso.groupId
    if testwareContents:
        packagesDetails["TestwareISOName"] = testwareISO.mediaArtifact.name
        packagesDetails["TestwareISOVersion"] = testwareISO.version
        packagesDetails["TestwareGroupID"] = testwareISO.groupId
    packagesDetails["PackagesInISO"] = isoContent
    return packagesDetails

def getAllRevisonsOfAPackage(packageName):
    '''
    Returns a list of strings; versions for all revisions of a package
    '''
    revisions = []
    try:
        package = Package.objects.get(name = packageName)
    except:
        return ['ERROR: "'+packageName+'" does not exist in CI Portal']
    revisionQuery = PackageRevision.objects.filter(package = package).only('version')
    for revision in revisionQuery:
        revisions.append(revision.version)
    return revisions

def getPackageRevisionForDeliveryGroup(packageRevs, listOfpackageRevsIds, warnings, teamsPkgRevs, product, drop, artifactList, verifyKgb=True):
    '''
    Getting Package Revisions For DeliveryGroup Creation
    '''
    authorisedSnapshots = config.get('CIFWK', 'authorisedSnapshots')
    artifactsCheckList = []
    for item in artifactList:
        skipArtifact = False
        try:
            pkgRev = None
            try:
                artifact, version, category = item.split("::")
            except:
                artifact, version= item.split("::")
            if "latest" in version.lower():
                return [{"result":"Failure - Package Revision Validation", "error":str("Can't use latest as version when creating a Delivery Group. Name: "+str(artifact))}], None, None, None
            else:
                if "-SNAPSHOT" in str(version):
                    if str(artifact) in authorisedSnapshots:
                        skipArtifact = True
                    else:
                        return [{"result":"Failure - Package Revision Validation", "error":str("Unauthorised SNAPSHOT found - " + str(item))}], None, None, None
                else:
                    pkgRev = PackageRevision.objects.get(package__name=artifact, version=version)
                    if pkgRev.kgb_test != "passed" and pkgRev.package.testware is not True and verifyKgb:
                        return [{"result":"Failure - Package Revision Validation", "error":str("This Package Revision: " + str(item) + " has not passed the KGB (Known Good Baseline) testing phase")}], None, None, None
            if skipArtifact == False:
                warning = getWarningForPackageVersionInBaseline(product, drop['name'], artifact, version, None)
                if warning != "":
                    warnings.append(warning)
                if len(artifactsCheckList) != 0:
                    for artifactItem in artifactsCheckList:
                        if artifact == str(artifactItem):
                            return [{"result":"Failure - Package Revision Validation", "error":str("Can't have duplicate Artifacts when creating a Delivery Group. The following has duplicate - Name: "+str(artifact))}], None, None, None
                artifactsCheckList.append(artifact)
                packageRevs.append(pkgRev)
                listOfpackageRevsIds.append(pkgRev.id)
                teams = PackageComponentMapping.objects.only('component__element').values('component__element').filter(package__name=artifact)
                if len(teams) != 0:
                    teamsList = []
                    for team in teams:
                        teamsList.append(team['component__element'])
                    teamsPkgRevs.append(', '.join(teamsList))
                else:
                    teamsPkgRevs.append(str("No Team Data"))
        except Exception as error:
            errMsg = "This Package Revision: " + str(item) + " is not contained within the Database: " + str(error)
            logger.error(errMsg)
            return [{"result":"Failure - Package Revision Validation", "error":str(errMsg)}], None, None, None
    return packageRevs, listOfpackageRevsIds, warnings, teamsPkgRevs


def validatingDropForDeliveryGroupCreation(drop, product, jiraIssues):
    '''
    validating the Drop
    '''
    dropValues = ('name', 'status', 'actual_release_date', 'id')
    if drop == None:
        drop = Drop.objects.only(dropValues).values(*dropValues).filter(release__product__name=product, correctionalDrop=False).exclude(release__name__icontains="test").latest("id")
    else:
        drop = Drop.objects.only(dropValues).values(*dropValues).get(release__product__name=product, name=drop)
    timeNow = datetime.now()
    dropQuery = Drop.objects.only('id').filter(planned_release_date__lt=timeNow, name=drop['name'], release__product__name=product) | Drop.objects.only('id').filter(actual_release_date__lt=timeNow, name=drop['name'], release__product__name=product)
    if len(dropQuery) != 0:
        return [{"result":"Failure - Drop Validation", "error":str("Can't create a Delivery Group. Drop " + str(drop['name']) + " is Frozen. Drop was Frozen on: " + str(drop['actual_release_date']))}]
    elif drop['status'] == "closed":
        return [{"result":"Failure - Drop Validation", "error":str("Can't create a Delivery Group. Drop " + str(drop['name']) + " is Closed")}]
    elif drop['status'] == "limited":
        dropActivity = DropActivity.objects.filter(drop__id=drop['id']).order_by("-id")[0]
        limitedReason = dropActivity.limitedReason
        issueTypeList = config.get('CIFWK', 'allowedIssueTypesForLimited')
        if "TR" in str(limitedReason) or "Bug" in str(limitedReason):
            for jira in jiraIssues:
                issueType = getJiraIssueType(jira)
                if not str(issueType) in issueTypeList:
                    return [{"result":"Failure - Drop Validation", "error":str("Can't create a Delivery Group. Drop " + str(drop['name']) + " is Limited to TR and Bug Issue Types only")}]
    return drop

def getJiraIssueType(jira):
    '''
    Getting issue type from Jira
    '''
    jsonObj, status = jiraValidation(jira)
    issueType = jsonObj['fields']['issuetype']['name']
    return issueType

def restCreateDeliveryGroup(data):
    '''
    This for when delivery group created through REST Call
    '''
    statusCode = "404"
    decodedJson = None
    try:
        if "{u'" in str(data):
            data = str(json.dumps(dict(data)))
            decodedJson = json.loads(data)
        else:
            decodedJson = data
    except Exception as error:
        errMsg = "Can't Create Delivery Group: " + str(error)
        logger.error(errMsg)
        return [{"result":"Failure - JSON Data Validation", "error":str(errMsg)}], statusCode
    packageRevs = []
    listOfpackageRevsIds = []
    teamsPkgRevs = []
    jiraIssues = []
    warnings = []
    cenmDgList = []
    try:
        validateOnly = decodedJson['validateOnly']
        if validateOnly == "false" or validateOnly == "False":
            validateOnly = False
        else:
            validateOnly = True
    except:
        validateOnly = True
    try:
        checkKgb = decodedJson['checkKgb']
        if checkKgb == "false" or checkKgb == "False":
            checkKgb = False
    except:
        checkKgb = True
    try:
        creator = decodedJson['creator']
    except:
        return [{"error":str("Can't Create Delivery Group, Must enter in a creator")}], statusCode
    try:
        user = User.objects.get(username=str(creator))
    except Exception as error:
        errMsg = "Can't Create Delivery Group, Must be User of CI Portal: " + str(creator) + " - " + str(error)
        logger.error(errMsg)
        return [{"result":"Failure - Creator (User) Validation", "error":str(errMsg)}], statusCode
    try:
        product = decodedJson['product']
        if product == "":
            product = "ENM"
    except:
        product = "ENM"
    try:
        drop = decodedJson['drop']
        if drop == "":
            drop = None
    except:
        drop = None
    try:
        cenmDgList = decodedJson['cenmDgList']
    except:
        cenmDgList = []
    try:
        jiraList = decodedJson['jiraIssues'].split(",")
        for jira in jiraList:
            jiraIssues.append(jira)
            jsonObj, status = jiraValidation(jira)
            if status == "200":
                isJiraValidationPass, jiraWarning, issueType = getWarningForJiraType(jsonObj)
                if isJiraValidationPass == False:
                    return [{"result": "Failure - Jira Issues Validation", "error": str(
                        "Issue with Jira Type for " + str(jira) + ", " + str(
                            issueType) + " Jira Issue Type is not allowed in Delivery Group.")}], statusCode
            else:
                logger.info('Jira not available')
    except Exception as error:
        statusCode = "404"
        errMsg = "Issue with getting Jira Issues: " + str(error)
        logger.error(errMsg)
        return [{"result":"Failure - Jira Issues Validation", "error":str(errMsg)}], statusCode
    try:
        drop = validatingDropForDeliveryGroupCreation(drop, product, jiraIssues)
        if "error" in str(drop):
            return drop, statusCode
    except Exception as error:
        errMsg = "Can't create a Delivery Group, Issue with Drop: " + str(error)
        logger.error(errMsg)
        return [{"result":"Failure - Drop Validation", "error":str(errMsg)}], statusCode

    artifactList = returnNewInBaseline(decodedJson['artifacts'])
    if "error" in str(artifactList):
        return artifactList, statusCode
    try:
        if artifactList:
            packageRevs, listOfpackageRevsIds, warnings, teamsPkgRevs = getPackageRevisionForDeliveryGroup(packageRevs, listOfpackageRevsIds, warnings, teamsPkgRevs, product, drop, artifactList, checkKgb)
            if "error" in str(packageRevs):
                return packageRevs, statusCode
        else:
            errMsg = "Artifact already contained within baseline"
            return [{"result":"Failure - Artifact In Baseline", "error":str(errMsg)}], statusCode
    except Exception as error:
        statusCode = "404"
        errMsg = "The artifactList: " + str(artifactList) + " there is an issue getting data from database " + str(error)
        logger.error(errMsg)
        return [{"result":"Failure - Package Revision Validation", "error":str(errMsg)}], statusCode
    try:
        validateCheck = validatePackageAndGroup(listOfpackageRevsIds,drop['name'])
        if validateCheck != False:
            return [{"result":"Failure - Delivery Queue Validation", "error":str(validateCheck)}], statusCode
    except Exception as error:
        errMsg = "Issue Checking Delivery Queue: " + str(error)
        logger.error(errMsg)
        return [{"result":"Failure - Delivery Queue Validation", "error":str(errMsg)}], statusCode
    try:
        comment = decodedJson['comment']
        if str(comment) == "None":
            comment = ""
    except:
        comment = ""
    try:
        team = decodedJson['team']
        teamObj = Component.objects.only('element').values('element').get(element=team,deprecated=0)
        team = teamObj['element']
    except Exception as error:
        if Component.objects.filter(element=team, deprecated=1).exists():
            errMsg = "The Team: " + str(team) + " is deprecated - " + str(error)
        else:
            errMsg = "The Team: " + str(team) + " is not contained within the Database - " + str(error)
        logger.error(errMsg)
        return [{"result":"Failure - Team Validation", "error":str(errMsg)}], statusCode
    try:
        missingDep = decodedJson['missingDependencies']
        if missingDep == "true" or missingDep == "True":
            missingDep = True
        else:
            missingDep = False
    except:
        missingDep = False
    warningsResult = str("".join(str(warnings).split("\\n"))).replace("'", "").replace("[", "").replace("]", "")
    statusCode = "200"
    if validateOnly == False:
        result, deliveryGroup = addDeliveryGroup(user, packageRevs, comment, product, drop['name'], team, teamsPkgRevs, cenmDgList, jiraIssues, missingDep, warnings, True)
        if result != 0:
            statusCode = "404"
            return [{"result": "Failure - Delivery Group was not Created", "error": str(result)}] , statusCode
        else:
            statusCode = "201"
            sendDeliveryGroupUpdatedEmail(user, str(deliveryGroup), "Delivery Group was Created")
            if AutoDeliverTeam.objects.filter(team__element=team).exists():
                try:
                    errMsg = [{"result":"Failure - Delivery Group was Created but not Delivered to the Drop","deliveryGroup": str(deliveryGroup), "drop": str(drop['name']), "warnings": warningsResult}]
                    delivery_thread = DGThread(performGroupDeliveries, args=(product, drop['name'], str(deliveryGroup), user))
                    delivery_thread.start()
                    delivery_thread.join()
                    deliveryFault, deliverySummary, fullList = delivery_thread.get_result()
                    if deliveryFault:
                        logger.info("Problem encountered during automated delivery of group " + str(deliveryGroup))
                        errMsg[0]['deliverySummary'] = deliverySummary
                        return errMsg , statusCode
                except Exception as e:
                    logger.error("Error delivering group " + str(deliveryGroup) + str(e))
                    return errMsg , statusCode
                groupDeliveredComment = str(user.first_name) + " "  + str(user.last_name) + " delivered this group automatically"
                sendDeliveryGroupUpdatedEmail(user, str(deliveryGroup), groupDeliveredComment)
                return [{"result":"Success - Delivery Group was Created and Delivered to the Drop","deliveryGroup": str(deliveryGroup), "drop": str(drop['name']), "warnings": warningsResult}] , statusCode

            return [{"result":"Success - Delivery Group was Created","deliveryGroup": str(deliveryGroup), "drop": str(drop['name']), "product": str(product), "creator" : str(creator), "warnings": warningsResult}] , statusCode
    return [{"result":"Success - all information is Valid", "warnings": warningsResult}], statusCode

def editDeliveryGroupForJiraType(deliveryGroupObj):
    '''
    Edit the value of bugOrTR column in deliveryGroup table
    '''
    jiras = JiraDeliveryGroupMap.objects.only('jiraIssue__issueType').values('jiraIssue__issueType').filter(deliveryGroup=deliveryGroupObj)
    bugOrTR = False
    if jiras:
        for value in jiras:
            if (str(value['jiraIssue__issueType']) == "Bug" or str(value['jiraIssue__issueType']) == "TR"):
                bugOrTR = True
                break
    deliveryGroupObj.bugOrTR = bugOrTR
    deliveryGroupObj.save()

def addDeliveryGroup(user,packageRevs, comment, product, drop, team, teamsPkgRevs, impactedCnDgs, jiraIssues, missingDep, warning, autoCreated=None, kgb_published_reason=None):
    '''
    Creates a new delivery group, maps it to a number of package revisions and generates a creation comment as well as taking a user comment about the creation
    '''
    consolidated = ""
    newArtifactPkg = False
    newArtifact = False
    try:
        packageFound = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        try:
            compObj = Component.objects.get(element=team, deprecated=0)
        except:
            logger.error("ERROR: Unable to create Delivery Group. Team does not exist in CI Portal: "+team)
            return "ERROR: Team does not exist in CI Portal. Contact the Maintrack team for assistance with adding your team", None
        if "Consolidated" in str(warning):
            consolidated = '1'
        if "New Artifact" in str(warning):
            newArtifact = True

        if autoCreated != None:
            deliveryGroup = DeliveryGroup.objects.create(drop=dropObj,creator=user.email, component=compObj, modifiedDate=now, createdDate=now, autoCreated=True, consolidatedGroup=consolidated)
        else:
            deliveryGroup = DeliveryGroup.objects.create(drop=dropObj,creator=user.email, component=compObj, modifiedDate=now, createdDate=now,consolidatedGroup=consolidated)
        recordReasonsForNoPassedKGB(kgb_published_reason,deliveryGroup)
        DeliveryGroupSubscription.objects.create(user=user, deliveryGroup=deliveryGroup)
        for revision, teams in zip(packageRevs, teamsPkgRevs):
            try:
                if newArtifact == True:
                    pkgWarning = getWarningForPackageVersionInBaseline(str(dropObj.release.product.name), str(dropObj.name), str(revision.artifactId), str(revision.version), None)
                    if "New Artifact" in str(pkgWarning):
                        newArtifactPkg = True
                        deliveryGroup.newArtifact = True
                        deliveryGroup.save()
                    else:
                        newArtifactPkg = False
                if Package.objects.filter(name=revision.package,includedInPriorityTestSuite=True).exists():
                    packageFound = 1
                elif revision.package.testware != True:
                    packageFound = 1
                kgbReport = getPkgRevKgbReport(revision)
                DeliverytoPackageRevMapping.objects.create(deliveryGroup=deliveryGroup, packageRevision=revision, team=teams, kgb_test=revision.kgb_test, testReport=kgbReport, kgb_snapshot_report=revision.kgb_snapshot_report,newArtifact =newArtifactPkg)
            except:
                logger.error("ERROR: There was an error while creating DeliverytoPackageRevMapping for PackageRevision: "+revision)
                return "ERROR: Unable to create Delivery Group. Could not add "+revision+" to the Delivery Group.", None
        if impactedCnDgs:
            impactedDG_status, impactedDG_errorMsg = addENMDeliveryGroupToCNDeliveryGroup(impactedCnDgs, deliveryGroup, "ENM")
            if impactedDG_status == 1:
                errorMsg = impactedDG_errorMsg
                logger.error(errorMsg)
                return errorMsg
        if jiraIssues:
            try:
                for jira in jiraIssues:
                    jiraIssueMsg, errorCode = addJiraIssueToDeliveryGroup(deliveryGroup, jira)
                    if errorCode == 1:
                        jiraUnavaibilityComment = "Could not retrieve jira issue:"+jira+" due to potential JIRA outage."
                        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=jiraUnavaibilityComment, date=now)
                        if not JiraIssue.objects.filter(jiraNumber=jira).exists():
                            jiraObj = JiraIssue.objects.create(jiraNumber=jira, issueType="Not Available")
                        else:
                            jiraObj = JiraIssue.objects.get(jiraNumber=jira)
                        if not JiraDeliveryGroupMap.objects.filter(deliveryGroup=deliveryGroup, jiraIssue=jiraObj).exists():
                                JiraDeliveryGroupMap.objects.create(deliveryGroup=deliveryGroup, jiraIssue=jiraObj)
                                if (jiraObj.issueType == "TR" or jiraObj.issueType == "Bug"):
                                    deliveryGroup.bugOrTR = True
                                    deliveryGroup.save()
            except Exception as e:
                msg = "ERROR: There was an error while creating a new Delivery Group"
                logger.error(str(msg) + " - " + str(e))
                return msg , None
        autoComment = str(user.first_name) + " "  + str(user.last_name) + " created this Delivery Group."
        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=autoComment, date=now)
        if comment != "":
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=comment, date=now)
        if missingDep:
            setMissingDependencies(user, product, drop, deliveryGroup.id, 'missing')
        if "WARNING" in str(warning):
            warningList = []
            for element in warning:
                warningSplit = element.split('\n')
                warningList += warningSplit
            warningComment = '<br />'.join(warningList)
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=warningComment, date=now)
        sendDeliveryGroupMessage(deliveryGroup,"create")
        if packageFound == 0 or autoCreated != None:
           return 0, deliveryGroup.id
        return 0, None
    except Exception as e:
        msg = "ERROR: There was an error while creating a new Delivery Group"
        logger.error(str(msg) + " - " + str(e))
        return msg , None

def recordReasonsForNoPassedKGB(totalReason,group):
    '''
    The recordReasonsForNoPassedKGB function records the reasons who artifacts where contained in delivery groups without passed KGB status
    '''
    reason = ""
    comment = ""
    try:
        if totalReason:
            if "::" in totalReason:
                reason,comment = totalReason.split("::")
            else:
                reason = totalReason
            GroupsCreatedWithoutPassedKGBTest.objects.create(group=group,reason=str(reason),comment=str(comment))
    except Exception as error:
        msg = "ERROR: Creating Reason for no KGB. " + str(error)
        logger.error(str(msg))

def getPkgRevKgbReport(revision):
    '''
     Getting the KGB Report of the Package Revision
    '''
    report = ""
    try:
        testwareMapObj=TestResultsToTestwareMap.objects.filter(package_revision=revision).order_by('-id')[:1][0]
        resultId= testwareMapObj.testware_run.id
    except:
        resultId = None
    try:
        if resultId is not None:
            testResultsObj=TestResults.objects.only('test_report_directory').values('test_report_directory').get(id=resultId)
            report = testResultsObj['test_report_directory']
    except Exception as error:
        msg = "ERROR: Getting the KGB Test Result Status for Package Revision: "+ str(revision) + " in Delivery Group: "+str(deliveryGroup)+". " + str(error)
        logger.error(str(msg))
    return report

def sendDeliveryGroupMessage(queueGroup,type):
    try:
        artifactCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=queueGroup).exclude(packageRevision__category__name='testware').count()
        testwareCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=queueGroup,packageRevision__category__name='testware').count()
        drop = queueGroup.drop
        dropName = drop.name
        releaseName = drop.release.name
        productName = drop.release.product.name
        team = queueGroup.component.element
        if queueGroup.missingDependencies:
            missingDependencies = 'true'
        else:
            missingDependencies = 'false'
        queueId = queueGroup.id
        groupsInQueueList=DeliveryGroup.objects.filter(drop=drop,delivered=0,obsoleted=0,deleted=0).values_list('id',flat=True)
        groupsInQueue = len(groupsInQueueList)
        artifactsInQueue=DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=groupsInQueueList).exclude(packageRevision__category__name='testware').count()
        testwareInQueue=DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=groupsInQueueList,packageRevision__category__name='testware').count()
        detailedKgbStatus,overallGroupKGB =  getKGBGroupStatus(queueGroup.id)
        if queueGroup.autoCreated:
            autoCreated = 'true'
        else:
            autoCreated = 'false'
        if type == "create":
            minutesInQueue = 0
            modifyCount = 0
        else:
            fmt = '%Y-%m-%d %H:%M:%S'
            nowFormatted = datetime.now().strftime(fmt)
            now = datetime.strptime(str(nowFormatted), fmt)
            commentObj = DeliveryGroupComment.objects.filter(deliveryGroup=queueGroup.id).order_by('id')[0]
            modifyCount = DeliveryGroupComment.objects.filter(deliveryGroup=queueGroup.id).order_by('id').count()-1
            createDate = datetime.strptime(str(commentObj.date), fmt)
            nowSeconds = time.mktime(now.timetuple())
            createSeconds = time.mktime(createDate.timetuple())
            minutesInQueue = int(nowSeconds-createSeconds) / 60
        mbHost = config.get('MESSAGE_BUS', 'eiffelHostname')
        mbExchange =  config.get('MESSAGE_BUS', 'eiffelExchangeName')
        mbDomain =  config.get('MESSAGE_BUS', 'eiffelDomainName')
        mbUser = config.get('MESSAGE_BUS', 'mbFunctionalUser')
        mbPwd = config.get('MESSAGE_BUS', 'mbFunctionalUserPassword')
        java =  config.get('MESSAGE_BUS', 'javaLocation')
        confidenceLevelMap = {'create': 'GROUP_CREATED','delete':'GROUP_DELETED','obsolete':'GROUP_OBSOLETED','deliver':'GROUP_DELIVERED','modify':'GROUP_MODIFIED','restore':'GROUP_RESTORED'}
        testwareGroup = "false"
        if artifactCount == 0 and testwareCount > 0:
            testwareGroup = "true"
        jsonInput = {
                    "confidenceLevel":confidenceLevelMap[type],
                    "confidenceLevelState":"SUCCESS",
                    "drop":dropName,
                    "product":productName,
                    "release":releaseName,
                    "artifactId":productName+"_"+releaseName+"_"+dropName+"_"+str(queueId),
                    "groupId":"com.ericsson",
                    "version":str(queueId),
                    "artifactsInGroup":str(artifactCount),
                    "testwareInGroup":str(testwareCount),
                    "groupTeam":team,
                    "queueId":str(queueId),
                    "queueLength":str(groupsInQueue),
                    "artifactsInQueue":str(artifactsInQueue),
                    "testwareInQueue":str(testwareInQueue),
                    "timeInQueue":str(minutesInQueue),
                    "missingDependencies":missingDependencies,
                    "groupKgbStatus":overallGroupKGB,
                    "modifyCount":str(modifyCount),
                    "detailedKgbStatus":detailedKgbStatus,
                    "messageBusHost":mbHost,
                    "messageBusExchange":mbExchange,
                    "messageBusDomain":mbDomain,
                    "messageBusUser": mbUser,
                    "messageBusPassword": mbPwd,
                    "messageType":"clme",
                    "testwareGroup":testwareGroup,
                    "deliveryGroupAutoCreated":autoCreated
                    }
        if type == "delete" or type == "restore":
            del jsonInput['timeInQueue']
        dateCreated = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        logger.info("####### Sending eiffelDeliveryGroupMessage to Message bus ########")
        logger.info(jsonInput)
        sendCLME = subprocess.check_call(java + " -jar /proj/lciadm100/cifwk/latest/lib/3pp/eiffelEventSender/cli-event-sender.jar '"+json.dumps(jsonInput)+"' 2>> /proj/lciadm100/cifwk/logs/messagebus/eiffelDeliveryGroupMessage/" + dateCreated, shell=True,cwd="/tmp")
        if not sendCLME == 0:
            logger.debug("Issue sending eiffel message")
    except Exception as e:
        logger.error("ERROR: Issue sending group action message " + str(e))

def getKGBGroupStatus(groupId):
    kgbPassedCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=groupId,packageRevision__kgb_test='passed').exclude(packageRevision__category__name='testware').count()
    kgbFailedCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=groupId,packageRevision__kgb_test='failed').exclude(packageRevision__category__name='testware').count()
    kgbInProgressCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=groupId,packageRevision__kgb_test='in_progress').exclude(packageRevision__category__name='testware').count()
    kgbNotStartedCount = DeliverytoPackageRevMapping.objects.filter(deliveryGroup=groupId,packageRevision__kgb_test='not_started').exclude(packageRevision__category__name='testware').count()
    if kgbFailedCount > 0 :
        overallGroupKGB = "FAILED"
    elif kgbNotStartedCount > 0 :
        overallGroupKGB = "NOT_STARTED"
    elif kgbInProgressCount > 0 :
        overallGroupKGB = "IN_PROGRESS"
    else:
        overallGroupKGB = "PASSED"
    detailedKgbStatus = "passed-"+str(kgbPassedCount)+",failed-"+str(kgbFailedCount)+",notStarted-"+str(kgbNotStartedCount)+",inProgress-"+str(kgbInProgressCount)
    return detailedKgbStatus,overallGroupKGB

def editDeliveryGroup(user, packageRevs, comment, product, drop, groupID, teamsPkgRevs, impactedCnDgs, jiraIssues, missingDep, warning, kgb_published_reason):
    '''
    Edits an existing delivery group, maps it to a number of package revisions and generates an edit comment as well as taking a user comment about the edit
    '''
    filterItems = ('packageRevision__artifactId', 'packageRevision__version', 'packageRevision__kgb_test', 'packageRevision__kgb_snapshot_report', 'kgb_test', 'kgb_snapshot_report')
    deliveryGroup = None
    newArtifactPkg = False
    try:
        deliveryGroup = DeliveryGroup.objects.get(id=groupID)
    except Exception as e:
        errMsg = "ERROR: There was an error while editing the Delivery Group: "+groupID
        logger.error(errMsg + " - " + str(e))
        return errMsg, None
    if deliveryGroup.delivered == True:
        msg = "ERROR: There was an error while editing the Delivery Group: "+ groupID + " - the Delivery Group was Delivered: " + str(deliveryGroup.deliveredDate)
        return msg, None
    if "New Artifact"  in str(warning):
        deliveryGroup.newArtifact = True
    else:
        deliveryGroup.newArtifact = False
    deliveryGroup.save()
    try:
        packageFound = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dropObj = Drop.objects.get(name=drop, release__product__name=product)
        kgbResultsBefore = DeliverytoPackageRevMapping.objects.only(filterItems).values(*filterItems).filter(deliveryGroup=deliveryGroup)
        kgbResultsBeforeComment  = editCommentForKGBResultsInGroup(kgbResultsBefore, None, None)
        DeliverytoPackageRevMapping.objects.filter(deliveryGroup=deliveryGroup).delete()
        for revision, teams in zip(packageRevs, teamsPkgRevs):
            if deliveryGroup.newArtifact == True:
                pkgWarning = getWarningForPackageVersionInBaseline(dropObj.release.product.name, dropObj.name, revision.artifactId, revision.version, None)
                if "New Artifact" in str(pkgWarning):
                    newArtifactPkg = True
                else:
                    newArtifactPkg = False
            if Package.objects.filter(name=revision.package,includedInPriorityTestSuite=True).exists():
                    packageFound = 1
            elif revision.package.testware != True:
                    packageFound = 1
            kgbReport = getPkgRevKgbReport(revision)
            DeliverytoPackageRevMapping.objects.create(deliveryGroup=deliveryGroup, packageRevision=revision, team=teams, kgb_test=revision.kgb_test, testReport=kgbReport, kgb_snapshot_report=revision.kgb_snapshot_report,newArtifact =newArtifactPkg)
        deliveryGroup.drop = dropObj
        deliveryGroup.save()
        JiraDeliveryGroupMap.objects.filter(deliveryGroup=deliveryGroup).delete()
        impactedCnDgBefore = CNDGToDGMap.objects.filter(deliveryGroup = deliveryGroup)
        impactedBeforeComment = editCommentForImpactedCNDeliveryGroup(None,user,deliveryGroup,impactedCnDgBefore,impactedCnDgs,now)
        CNDGToDGMap.objects.filter(deliveryGroup = deliveryGroup).delete()
        impactedDG_status, impactedDG_errorMsg = addENMDeliveryGroupToCNDeliveryGroup(impactedCnDgs, deliveryGroup, 'ENM')
        if impactedDG_status == 1:
            errorMsg = impactedDG_errorMsg
            logger.error(errorMsg)
            return errorMsg
        else:
            editCommentForImpactedCNDeliveryGroup(impactedBeforeComment,user,deliveryGroup,impactedCnDgBefore,impactedCnDgs,now)
        if jiraIssues:
            for jira in jiraIssues:
                jiraIssueMsg, errorCode = addJiraIssueToDeliveryGroup(deliveryGroup, jira)
                if errorCode == 1:
                    return jiraIssueMsg, None
        autoComment = str(user.first_name) + " "  + str(user.last_name) + " edited this Delivery Group."
        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=autoComment, date=now)
        editCommentForKGBResultsInGroup(kgbResultsBeforeComment,deliveryGroup,now)
        if comment != "":
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=comment, date=now)
        if missingDep:
           missingDep =  setMissingDependencies(user, product, drop, deliveryGroup.id, 'missing')
        else:
           missingDep =  setMissingDependencies(user, product, drop, deliveryGroup.id, 'None')
        if missingDep != None:
            deliveryGroup.missingDependencies = missingDep
        if "WARNING" in str(warning):
            warningList = []
            for element in warning:
                warningSplit = element.split('\n')
                warningList += warningSplit
            warningComment = '<br />'.join(warningList)
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=warningComment, date=now)
            if "Consolidated"  in str(warning):
                consolidated = '1'
                deliveryGroup.consolidatedGroup = consolidated
            else:
                deliveryGroup.consolidatedGroup = ""
            if "New Artifact"  in str(warning):
                deliveryGroup.newArtifact = True
            else:
                deliveryGroup.newArtifact = False

        recordReasonsForNoPassedKGB(kgb_published_reason,deliveryGroup)
        deliveryGroup.warning = False
        deliveryGroup.save(force_update=True)
        sendDeliveryGroupMessage(deliveryGroup,"modify")
        sendDeliveryGroupUpdatedEmail(user, str(deliveryGroup.id), autoComment)
        editDeliveryGroupForJiraType(deliveryGroup)
        if packageFound == 0:
           return 0, deliveryGroup.id
        return 0, None
    except Exception as e:
        msg = "ERROR: There was an error while editing the Delivery Group: "+groupID
        logger.error(msg + " - " + str(e))
        deliveryGroup.warning = True
        deliveryGroup.save(force_update=True)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comment = str(user.first_name) + " "  + str(user.last_name) + " could not edit this group - " + msg + " - " + str(e)
        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=comment, date=now)
        return msg, None

def editCommentForImpactedCNDeliveryGroup(commentBefore,user,deliveryGroup,impactedCnDgBefore,impactedCnDgAfter,commentDateTime):
    '''
    Creating a comment for edition of Impacted CN Delivery Group for a ENM DG
    '''
    try:
        if commentBefore is None:
            comment = str(user.first_name) + " "  + str(user.last_name) + " edited Impacted CN Delivery Group info:"
            comment += "<br><b>Before:</b>"
            if len(impactedCnDgBefore) > 0:
                for cnDeliveryGroup in impactedCnDgBefore:
                    comment += "<br>CN Delivery Group: " + str(cnDeliveryGroup.cnDeliveryGroup.id)
            else:
                comment += "<br>No Impacted CN Delivery Group"
            return comment
        else:
            comment = commentBefore
            comment += "<br><b>After:</b>"
            if len(impactedCnDgAfter) > 0:
                for cnDeliveryGroup in impactedCnDgAfter:
                    comment += "<br>CN Delivery Group: " + cnDeliveryGroup
            else:
                comment += "<br>No Impacted CN Delivery Group"
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=comment, date=commentDateTime)
    except Exception as error:
        msg = "ERROR: There was issue creating the comment for editing Impacted Delivery Group in Delivery Group " + str(deliveryGroup) + " - " + str(error)
        logger.error(str(msg))

def editCommentForKGBResultsInGroup(kgbResultsBefore,deliveryGroup,commentDateTime):
    '''
    Reporting KGB Results of Package Revision(s) in Delivery Group
    '''
    try:
        filterItems = ('packageRevision__artifactId', 'packageRevision__version', 'packageRevision__kgb_test', 'kgb_test', 'packageRevision__kgb_snapshot_report', 'kgb_snapshot_report')
        if deliveryGroup is None:
            comment = "Delivery Group KGB Results. <br /><b>Before Edit:</b>"
            for item in kgbResultsBefore:
                comment += "<br />" + str(item['packageRevision__artifactId']) +  "-" + str(item['packageRevision__version']) +":"
                if item['kgb_test'] is not None:
                    comment += str(item['kgb_test'])
                    if item['kgb_snapshot_report'] == True:
                        comment += " - Snapshot(s) Used in Testing"
                else:
                    comment += str(item['packageRevision__kgb_test'])
                    if item['packageRevision__kgb_snapshot_report'] == True:
                        comment += " - Snapshot(s) Used in Testing"
            return comment
        else:
            comment = kgbResultsBefore
            comment += "<br /> <b>After Edit:</b>"
            kgbResultsAfter = DeliverytoPackageRevMapping.objects.only(filterItems).values(*filterItems).filter(deliveryGroup=deliveryGroup)
            for item in kgbResultsAfter:
                comment += "<br />" + str(item['packageRevision__artifactId']) +  "-" + str(item['packageRevision__version']) +":" +str(item['kgb_test'])
                if item['kgb_snapshot_report'] == True:
                    comment += " - Snapshot(s) Used in Testing"
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroup, comment=comment, date=commentDateTime)
    except Exception as error:
        msg = "ERROR: There was issue creating the comment for KGB Results of Package Revision(s) in Delivery Group " + str(deliveryGroup) + " - " + str(error)
        logger.error(str(msg))


def addJiraIssueToDeliveryGroup(deliveryGroupObj, jira):
    '''
      adding Jira Issue data To Delivery Group
    '''
    errMsg = None
    try:
        jira = jira.upper()
        jsonObj, statusCode = jiraValidation(jira)
        if statusCode == "200":
            isJiraValidationPass, jiraWarning, issueType = getWarningForJiraType(jsonObj)
            if isJiraValidationPass == False:
                return "Entered Jira type (" + str(issueType)  + ") cannot be added to current delivery.", 1
            if not JiraIssue.objects.filter(jiraNumber = jira).exists():
                jiraObj = JiraIssue.objects.create(jiraNumber = jira, issueType = jsonObj['fields']['issuetype']['name'])
            else:
                jiraObj = JiraIssue.objects.get(jiraNumber = jira)
                jiraObj.issueType = jsonObj['fields']['issuetype']['name']
                jiraObj.save(force_update=True)
            if deliveryGroupObj != "None":
                if not JiraDeliveryGroupMap.objects.filter(deliveryGroup = deliveryGroupObj, jiraIssue = jiraObj).exists():
                    JiraDeliveryGroupMap.objects.create(deliveryGroup = deliveryGroupObj, jiraIssue = jiraObj)
                    if (jiraObj.issueType == "TR" or jiraObj.issueType == "Bug"):
                        deliveryGroupObj.bugOrTR = True
                        deliveryGroupObj.save()
            labels = jsonObj['fields']['labels']
            for label in labels:
                if not JiraLabel.objects.filter(name = label, type="label").exists():
                    jiraLabel = JiraLabel.objects.create(name = label, type="label")
                else:
                    jiraLabel = JiraLabel.objects.get(name = label, type="label")
                if not LabelToJiraIssueMap.objects.filter(jiraIssue = jiraObj, jiraLabel = jiraLabel).exists():
                    LabelToJiraIssueMap.objects.create(jiraIssue = jiraObj, jiraLabel = jiraLabel)
            try:
                tcgs = jsonObj['fields']['customfield_21404']
                for tcg in tcgs:
                    tcgValue = tcg['value']
                    if not JiraLabel.objects.filter(name = tcgValue, type="tcg").exists():
                        jiraTCG = JiraLabel.objects.create(name = tcgValue, type="tcg")
                    else:
                        jiraTCG = JiraLabel.objects.get(name = tcgValue, type="tcg")
                    if not LabelToJiraIssueMap.objects.filter(jiraIssue = jiraObj, jiraLabel = jiraTCG).exists():
                        LabelToJiraIssueMap.objects.create(jiraIssue = jiraObj, jiraLabel = jiraTCG)
            except Exception as e:
                if deliveryGroupObj != "None":
                    errMsg = "ERROR: No TCG field found for this JIRA type or there was issue saving/creating it in DB for this delivery group: Group: " + str(deliveryGroupObj.id) + " - " + str(e)
                else:
                    errMsg = "ERROR: No TCG field found for this JIRA type or there was issue saving/creating it in DB  - " + str(e)
                logger.warning(errMsg)
            return "vaild", 0
        else:
            return "Entered Jira can not be verified. Please check your entry.", 1
    except Exception as e:
        if deliveryGroupObj != "None":
            errMsg = "ERROR: There was an error while creating Jiras for the delivery group: Group: "+ str(deliveryGroupObj.id) + " - " + str(e)
        else:
            errMsg = "ERROR: There was an error while creating Jiras"
        logger.error(errMsg)
        return errMsg, 0

def getGroupDetails(groupId):
    '''
    Given a DeliveryGroup Id, this function generates a Json object containing info about the drop the group is associated with and the PackageRevisions in the group
    '''
    try:
        requiredValues = ('drop__name', 'component__element', 'missingDependencies', 'delivered', 'deleted', 'obsoleted')
        deliveryGroup = DeliveryGroup.objects.only(requiredValues).values(*requiredValues).get(id=groupId)
    except:
        logger.error("DeliveryGroup with ID: " + str(groupId) + " is not contained within the CI Database")
        raise Exception
    dropName = deliveryGroup['drop__name']
    groupInfo = {}
    packageRevisions = []
    jiraIssues = []
    try:
        requiredQueryResultValues = ('packageRevision__package__name', 'packageRevision__version', 'team')
        queryResults = DeliverytoPackageRevMapping.objects.only(requiredQueryResultValues).values(*requiredQueryResultValues).filter(deliveryGroup=groupId)
        queryJiraResults = JiraDeliveryGroupMap.objects.only('jiraIssue__jiraNumber').values('jiraIssue__jiraNumber').filter(deliveryGroup=groupId)
    except:
        logger.error("Issue getting Delivery Group Items with ID: " + str(groupId))
        raise Exception
    for revision in queryResults:
        packageRevisions.append({"name":revision['packageRevision__package__name'],"version":revision['packageRevision__version'], "team":revision['team'],})
    for jira in queryJiraResults:
        jiraIssues.append({"issue": jira['jiraIssue__jiraNumber'],})
    groupInfo["groupId"] = groupId
    groupInfo["dropName"] = "ENM:"+dropName
    try:
        groupInfo["creatorsTeam"] = deliveryGroup['component__element']
    except:
        logger.info("No Team set for this Delivery Group.")
        groupInfo["creatorsTeam"] = ""
    groupInfo["delivered"] = deliveryGroup['delivered']
    groupInfo["deleted"] = deliveryGroup['deleted']
    groupInfo["obsoleted"] = deliveryGroup['obsoleted']
    groupInfo["packageRevisions"] = packageRevisions
    groupInfo["jiraIssues"] = jiraIssues
    groupInfo["missingDep"] = deliveryGroup['missingDependencies']
    return groupInfo

def getDropDeliveryGroupData(dropObj, previousDropObj, overAllDict=None):
    '''
    Returns Delivery Group Data between drop and previousDrop: delivered & obsoleted groups
    '''
    if not overAllDict:
        overAllDict = {'DeliveryGroupData':[]}
    groupDict = {}
    groupList = []
    artifactIdList = []
    try:
        requiredFields = ('deliveryGroup__id', 'packageRevision__artifactId', 'packageRevision__version', 'deliveryGroup__delivered', 'deliveryGroup__obsoleted', 'deliveryGroup__drop__name')
        queryResults = DeliverytoPackageRevMapping.objects.prefetch_related('deliveryGroup').only(requiredFields).filter(deliveryGroup__drop__id=dropObj['id']).values(*requiredFields).order_by('-deliveryGroup__modifiedDate')
        if queryResults:
            for delGroup in queryResults:
                if not str(delGroup['packageRevision__artifactId']+ "-" + str(delGroup['packageRevision__version'])) in artifactIdList:
                    if delGroup['deliveryGroup__delivered'] == 1 or delGroup['deliveryGroup__obsoleted'] == 1:
                        groupDict['group'] = str(delGroup['deliveryGroup__id'])
                        groupDict['drop'] = str(delGroup['deliveryGroup__drop__name'])
                        if delGroup['deliveryGroup__delivered'] == 1:
                            groupDict['status'] = 'delivered'
                        else:
                            groupDict['status'] = 'obsoleted'
                        groupDict['artifact'] = str(delGroup['packageRevision__artifactId'])
                        groupDict['version'] = str(delGroup['packageRevision__version'])
                        artifactIdList.append(str(delGroup['packageRevision__artifactId']) + "-" + str(delGroup['packageRevision__version']))
                        groupList.append(groupDict)
                        groupDict = {}
            if groupList:
                overAllDict['DeliveryGroupData'].extend(groupList)
        if dropObj['id'] == previousDropObj['id']:
            return overAllDict
        requiredDropFields = ('id','designbase__id')
        dropObj = Drop.objects.only(requiredDropFields).values(*requiredDropFields).get(id=dropObj['designbase__id'])
        getDropDeliveryGroupData(dropObj, previousDropObj, overAllDict)
    except Exception as e:
        logger.error("Issue getting Delivery Groups,  Error: "+ str(e))
    return overAllDict

def performGroupDeliveries(product, drop, groupId, user):
    '''
     Perform Group Deliveries function
    '''
    deliver_DG_lock.acquire()
    deliverySummary = artifactSummary = ""
    deliveredList = []
    fullList = []
    deliveryFault = False
    deliveryGroupObj = None
    try:
        deliveryGroupObj = DeliveryGroup.objects.select_related('id').only('id', 'drop', 'drop__name', 'drop__release__name', 'drop__release__product__name', 'component__element', 'delivered', 'modifiedDate', 'missingDependencies').get(id=groupId)
    except Exception as e:
        deliverySummary = "Error delivering group " + str(groupId) +": " + str(e)
        logger.error(deliverySummary)
        deliveryFault = True
        deliver_DG_lock.release()
        return deliveryFault, deliverySummary, fullList

    if deliveryGroupObj.missingDependencies == True:
        deliverySummary = "Error delivering group " + str(groupId) + ". This group has missing dependencies."
        logger.error(deliverySummary)
        deliveryFault = True
        deliver_DG_lock.release()
        return deliveryFault, deliverySummary, fullList

    if deliveryGroupObj.delivered == True:
        deliverySummary = "Error delivering group " + str(groupId) + ". This group is already delivered."
        logger.error(deliverySummary)
        deliveryFault = True
        deliver_DG_lock.release()
        return deliveryFault, deliverySummary, fullList

    if deliveryGroupObj.drop.name != drop:
        deliverySummary = "Error delivering group " + str(groupId) + ". This group is not queued in the given drop " + str(drop) + ", it is queued in drop " + str(deliveryGroupObj.drop.name)
        logger.error(deliverySummary)
        deliveryFault = True
        deliver_DG_lock.release()
        return deliveryFault, deliverySummary, fullList

    try:
        dropStatus = Drop.objects.only('status').values('status').get(name=drop, release__product__name=product)
        if str(dropStatus['status']) == "closed":
            deliveryFault = True
            deliverySummary = "The status of this Drop has been set to Closed, no deliveries can be made. Contact Maintrack Guardians."
        else:
            email = DeliveryGroup.objects.only('creator').get(id=groupId).creator
            pkgMaps = DeliverytoPackageRevMapping.objects.select_related('packageRevision').only('packageRevision__package__name', 'packageRevision__version', 'packageRevision__m2type', 'packageRevision__platform').filter(deliveryGroup__id=groupId)
            for item in pkgMaps:
                artifact = item.packageRevision.package.name
                version = item.packageRevision.version
                type = item.packageRevision.m2type
                platform = item.packageRevision.platform

                # Deliver each item in the group
                status=performDelivery2(artifact, version, type, drop, product, email, platform, False, user, deliveryGroupObj)
                info = status.replace(',', '')
                fullList.append(str(artifact) +" Version: "+str(version) +" : " +info)
                # Check the Delivery status back
                if 'DELIVERED' in status:
                    deliveredList.append(status)
                    summaryString = "Successful"
                elif 'ERROR' in status:
                    deliveryFault = True
                    summaryString = "Failure"
                elif 'INDROP' in status:
                    deliveryFault = False
                    summaryString = "Already in Drop"
                elif 'NOTOPEN' in status:
                    deliveryFault = True
                    summaryString = "Drop is not Open"
                else:
                    deliveryFault = True
                    summaryString = "Failure"
                deliverySummary = deliverySummary+"\n"+"Delivery of "+str(artifact)+" "+str(version)+" "+str(type) +":"+summaryString
                artifactSummary = artifactSummary +"\n"+str(artifact)+" "+str(version)+" "+str(type)
        if deliveryFault:
            if summaryString:
                deliverySummary = "Error detected delivering full group of Artifacts. No deliveries made: "
                reason = "Reverted this delivery as an error was detected when attempting to deliver the full group (Group ID: " + str(groupId)+ ")"
                for returnedStatus in deliveredList:
                    returnedStatusSplit = returnedStatus.split(',')
                    for returnedStatusItem in returnedStatusSplit:
                        if 'DELIVERED' in returnedStatusItem:
                            doNotWant,obsoleteArtifactId,obsoleteDropId = returnedStatusItem.split(':')
                            obsolete2(obsoleteArtifactId,obsoleteDropId,reason,user, False)
                deliveryGroupObj.warning = True
                deliveryGroupObj.save(force_update=True)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                deliveredComment = str(user.first_name) + " "  + str(user.last_name) + " could not deliver this group (on behalf of " + str(email)+ ") to the drop, due to Error detected delivering full group of Artifacts."
                DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
                deliver_DG_lock.release()
                return deliveryFault, deliverySummary, fullList

        logger.debug("Successfully delivered group " + str(groupId))
        # If all okay Change the state of the delivered boolean on the group
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        deliveryGroupObj.delivered = True
        deliveryGroupObj.modifiedDate = now
        deliveryGroupObj.warning = False
        deliveryGroupObj.deliveredDate = now
        deliveryGroupObj.save(force_update=True)
        sendDeliveryGroupMessage(deliveryGroupObj,"deliver")
        # Also add in a comment
        deliveredComment = str(user.first_name) + " "  + str(user.last_name) + " delivered this group (on behalf of " + str(email)+ ") to the drop"
        newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
    except Exception as e:
        deliverySummary = "Error delivering group " + str(groupId) + ": "  + str(e)
        deliveryGroupObj.warning = True
        deliveryGroupObj.save(force_update=True)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        errorComment = str(user.first_name) + " "  + str(user.last_name) + " could not deliver this group to the drop, due to Error detected delivering full group of Artifacts: " + str(e)
        DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=errorComment, date=now)
        logger.error(deliverySummary)
        deliveryFault = True
        deliver_DG_lock.release()
        return deliveryFault, deliverySummary, fullList
    deliver_DG_lock.release()
    return deliveryFault, deliverySummary, fullList

def deliveryIsoContentToDrop(productISOArtifactName,productISOVersion,drop,product):
    '''
    Function used to deliver the content of an ISO to a drop
    '''
    dropObj = Drop.objects.get(release__product__name=product,name=drop)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if dropObj.designbase is not None:
        response = ("Error: Drop supplied : '" + str(dropObj.name) + "' contains a designbase : '" + str(dropObj.designbase.name) + "' .This functionality is for drops that have no designbase specificed, Please edit the drop and try again.\n")
        logger.error(response)
        return 1
    if MediaArtifact.objects.filter(name=productISOArtifactName).exists():
        productISOObj = MediaArtifact.objects.get(name=productISOArtifactName)
        if ISObuild.objects.filter(mediaArtifact=productISOObj,version=productISOVersion).exists():
            productISOBuildObj = ISObuild.objects.get(mediaArtifact=productISOObj,version=productISOVersion)
        else:
            response = ("Error: ISO Media Artifact Name: '" + str(productISOArtifactName) + "' Version: '" + str(productISOVersion) + "' does not exist, please try again.\n")
            logger.error(response)
            return 1
    else:
        response = ("Error: ISO Media Artifact Name: '" + str(productISOArtifactName) + " does not exist, please try again.\n")
        logger.error(response)
        return 1

    try:
        if ISObuildMapping.objects.filter(iso=productISOBuildObj).exists():
            isoRevMapping = ISObuildMapping.objects.filter(iso=productISOBuildObj)
    except Exception as e:
        response = ("Error: Filtering on ISO Build Mappings: " +str(e))
        logger.error(response)
        return 1

    notAddedList = []
    try:
        # First remove any Drop Package mappings for the drop provided in case any are in the database
        logger.info("Remove any Mappings associated with this drop: " + str(dropObj))
        dpms = DropPackageMapping.objects.filter(drop=dropObj)
        logger.info("Found " +str(len(dpms)) + " items to delete. Removing them now")
        for dropPkgMap in dpms:
            dropPkgMap.delete()
        isoList = []
        for lic in isoRevMapping:
            isoList.append(lic.package_revision)
        for isoPackage in isoRevMapping:
            packageRevisionObj=PackageRevision.objects.get(id=isoPackage.package_revision.id)
            if DropPackageMapping.objects.filter(package_revision=packageRevisionObj,drop=isoPackage.drop.id,obsolete=0).exists():
                dropPackageMappingObj=DropPackageMapping.objects.get(package_revision=packageRevisionObj,drop=isoPackage.drop.id,obsolete=0)
            else:
                notAddedList.append(str(packageRevisionObj))
                continue
            spm = DropPackageMapping(package_revision=packageRevisionObj, drop=dropObj, obsolete=False, released=True, date_created=now, delivery_info=dropPackageMappingObj.delivery_info, deliverer_mail=dropPackageMappingObj.deliverer_mail, deliverer_name=dropPackageMappingObj.deliverer_name)
            spm.save()
            logger.info("Added : " + str(isoPackage.package_revision.package.name) + " - " + str(isoPackage.package_revision.version) + " to " + str(product) + " Drop: " + str(dropObj.name))
    except Exception as e:
        response = ("Error: Delivering package to the drop, Exception: " +str(e))
        logger.error(response)
        return 1

    if len(notAddedList) != 0:
        logger.info("The following item(s) are included in the ISO but can't be found within the DropPackageMapping table as not obsolete")
        for item in notAddedList:
            logger.info(str(item))
        logger.info("PLEASE INVESTIGATE ASAP")

    logger.info(" ** Checking for differences after delivery between iso " + str(productISOArtifactName) + "' Version: '" + str(productISOVersion) + " and drop " + str(dropObj.name) + " **")
    # Get a list of packages delivered to the drop
    dropContentMapping = DropPackageMapping.objects.filter(drop=dropObj)
    dropContentList = []
    dropList = []
    for mapping in dropContentMapping:
        if mapping.package_revision.isoExclude:
            continue
        dropList.append(mapping.package_revision)

    # Compare List for iso and drop, checking if they match or not.
    logger.info("Drop item count: " +str(len(dropList)))
    logger.info("ISO item count: " +str(len(isoList)))
    result  = set(isoList) == set(dropList)
    if not result:
       logger.info("Error: There is a mismatch between the ISO content and the new content for drop " +str(dropObj))
       return 1
    else:
       logger.info("ISO Content is the same as Drop content")
    return 0

def jiraValidation(jira):
    '''
    Validating Jira Issue Input
    '''
    jiraRestApiUrl = config.get('CIFWK', 'jiraRestApiUrl')
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    jiraMigProjList = JiraMigrationProject.objects.all().values('projectKeyName')
    migKeyList = []
    for obj in jiraMigProjList:
        migKeyList.append(obj.get('projectKeyName'))
    header = getJiraAccessTokenHeader()
    if jira.split('-')[0] in migKeyList:
        eTeamJiraRestApiUrl = config.get('CIFWK', 'eTeamJiraRestApiUrl')
        eTeamJiraUrl = eTeamJiraRestApiUrl + jira
        result = requests.get(eTeamJiraUrl, headers=header, verify=ssl_certs)
    else:
        jira = jiraRestApiUrl+jira
        result = requests.get(jira, headers=header, verify=ssl_certs)
    statusCode = str(result.status_code)
    if statusCode == "200":
       jsonObj = result.json()
       return jsonObj, statusCode
    else:
       return "Error", statusCode

def getProductSetCDBStatus(productSetVersionObj):
    allStatusUni = productSetVersionObj.current_status
    if allStatusUni == "":
        return []
    allStatus=ast.literal_eval(allStatusUni)
    status=[]
    for item in allStatus:
        typObj=CDBTypes.objects.get(id=item)
        type=typObj.name
        try:

            state,start,finish,testReport,veLog=allStatus[item].split("#")
        except:
            veLog = "None"
            state,start,finish,testReport=allStatus[item].split("#")
        status1 = [
                {
                    "type": type,
                    "state": state,
                    "start": start,
                    "finish": finish,
                    "veLog": veLog,
                    "testReport": testReport,
                },
                ]
        status = status + status1
    status = status[::-1]
    return status

def preRegisterENMArtifact(product, packageName, packageNumber, signum, category):
    if len(packageName) > 50 and "3pp" not in str(category).lower():
        return "Error: Package name length should not be more than 50 characters.\nPlease update package name and try again.\n"
    if Package.objects.filter(name=packageName, package_number=packageNumber).exists():
        return "Error: A package with the given name and number already exists. Please use different name and number.\n"
    if Package.objects.filter(package_number=packageNumber).exists():
        return "Error: A package with the number " + packageNumber + " already exists under a different name.\n"

    if "testware" in str(category).lower():
        if not re.match(r'^ERICTAF[a-zA-Z0-9]+_[A-Z]{3}[0-9]{7}$|^ERICTW[a-zA-Z0-9]+_[A-Z]{3}[0-9]{7}$', packageName):
            return "Error: Testware Name is Incorrect. It should be in the format: Testware Artifact Name, upper case letters (ERICTAF or ERICTW), upper or lower case letters, Underscore (_), 3 upper case letters (CXP) and seven digits. \nExample: ERICTAFpackageName_CXP1234567 or ERICTWpackageName_CXP1234567. \nPlease update packageName and try again.\n"
    elif "3pp" not in str(category).lower():
        if PackageNameExempt.objects.filter(name=packageName).exists():
            if not re.match(r'^[a-zA-Z0-9\.]+_(?:[A-Z]{3}[0-9]{7}|APR901[0-9]{3})$', packageName):
                return "Error: Package Name is Incorrect. It should be in the format: Artifact Name upper or lower case letters, Underscore (_), 4 upper case letters, and seven digits. \nExample: packageName_APR1234569 or ERICpackageName_CXP1234567.\nFor older APR901 artifacts six digits at end of packageName is allowed eg: ERICpackageName_APR901123. \nPlease update packageName and try again.\n"
        elif not re.match(r'^[a-zA-Z0-9]+_(?:[A-Z]{3}[0-9]{7}|APR901[0-9]{3})$', packageName):
            return "Error: Package Name is Incorrect. It should be in the format: Artifact Name upper or lower case letters, Underscore (_), 4 upper case letters, and seven digits. \nExample: packageName_APR1234569 or ERICpackageName_CXP1234567.\nFor older APR901 artifacts six digits at end of packageName is allowed eg: ERICpackageName_APR901123. \nPlease update packageName and try again.\n"
    try:
        with transaction.atomic():
            if "testware" in str(category).lower():
                newPackage = Package(name=packageName, package_number=packageNumber, signum=signum, testware=True)
            else:
                newPackage = Package(name=packageName, package_number=packageNumber, signum=signum)
            newPackage.save()
            mapProductToPackage(product,newPackage)
            sendPackageMail(packageName)

            return "Package " + packageName + " has been created.\n"
    except IntegrityError as e:
        logger.error(str(e))
        return "Error: Package " + packageName + " with the number " + packageNumber + " can not be created, Error thrown: " +str(e)

def compareSprintVersions(verNew, verOld):
    '''
    Version Comparison
    '''
    [maj, minor, patch] = str(verNew).split(".", 2)
    verNewCheck = str(maj) + "." + str(minor)
    [maj, minor, patch] = str(verOld).split(".", 2)
    verOldCheck = str(maj) + "." + str(minor)
    if LooseVersion(verNewCheck) <= LooseVersion(verOldCheck):
        return False
    else:
        return True

def compareVersions(verNew, verOld):
    '''
    Version Comparison
    '''
    if LooseVersion(verNew) == LooseVersion(verOld):
        return 1
    elif LooseVersion(verOld) >  LooseVersion(verNew):
        return 0
    return 2

def getConsolidatedServiceGroupForArtifact(artifact):
    '''
    Getting consolidated service Group
    '''
    message = ""
    requiredServicePackageMapFields = ('package__name','service__name')
    serviceMappings = VmServicePackageMapping.objects.select_related('service','package').filter(package__name = artifact).only(requiredServicePackageMapFields).values(*requiredServicePackageMapFields)
    requiredFields = 'consolidated', 'constituent'
    consolidateToConstituentFields = ConsolidatedToConstituentMap.objects.only(requiredFields).values(*requiredFields)

    service = []
    for servicePackageMapping in serviceMappings:
        service.append(servicePackageMapping['service__name'])
    consolidatedList = []
    constituentList = []
    for value in service:
        for count,dict in enumerate(consolidateToConstituentFields):
            if value == dict['constituent']:
                constituentList.append(value)
                if dict['consolidated'] not in consolidatedList:
                    consolidatedList.append(dict['consolidated'])
    if consolidatedList:
        consolidatedServices = ""
        for val in consolidatedList:
            consolidatedServices = consolidatedServices + "  " + val
        message += "WARNING: Consolidated Group affected by " + str(artifact) + ": " + str(consolidatedServices) + ".\n "
    else:
        message += ""

    return message

def getVersionWarningForPackageVersion(versionNew, versionOld, artifact, drop, sprintVersionOld, sprintDropOld):
    '''
    Getting the version warning
    '''
    message = ""
    message = getConsolidatedServiceGroupForArtifact(artifact)
    if sprintVersionOld:
        sprintVersionResult = compareSprintVersions(versionNew, sprintVersionOld)
        if not sprintVersionResult:
            message += "WARNING: Baseline contains version " + str(sprintVersionOld) + ", this was delivered to: " + str(sprintDropOld.name) + " . You should not proceed without updating your sprint version for Artifact: " + artifact + ". \n "
    if Package.objects.filter(name=artifact,includedInPriorityTestSuite=True).exists():
        testwareTypeMappings = TestwareTypeMapping.objects.only('testware_type__type').values('testware_type__type').filter(testware_artifact__name=artifact)
        message += "WARNING: This Testware is contained within the " +  ', '.join([testwareTypeMap['testware_type__type'] for testwareTypeMap in testwareTypeMappings]) + " test suite(s) and WILL NOT get Automatically Delivered. \n "
    if versionOld is not None:
        versionResult = compareVersions(versionNew, versionOld)
        if versionResult == 1:
            message += "WARNING: Same Version found in the Baseline, for Artifact: " + str(artifact) + "-" + str(versionNew) + ". This was delivered to: " + str(drop.name) + " . \n "
        elif versionResult == 0:
            message += "WARNING: Trying to Deliver a lower version: " + str(versionNew) + " into the Baseline, for Artifact: " + str(artifact) + ". Current version is: " + str(versionOld) + ", this was delivered to: " + str(drop.name) + ". \n "
    else:
        message += "WARNING: Trying to Deliver a New Artifact: " + str(artifact) + " to the Baseline. This package has not been delivered before. \n "
    fields = 'kgb_test', 'package__testware',
    PackageRevisionKGBStatus = PackageRevision.objects.only(fields).values(*fields).get(package__name=artifact,version=versionNew)
    if PackageRevisionKGBStatus['kgb_test'] != "passed" and PackageRevisionKGBStatus['package__testware'] is not True:
        message += "WARNING: Artifact: " + str(artifact) + "-" + str(versionNew) + " has not passed the KGB (Known Good Baseline) testing phase. \n "
    return message


def getPackageExistsInQueueWarning(product, drop, artifact, groupId):
    '''
    Checks if package already exists in another queued or delivered Group and returns a warning accordingly
    '''
    queuedGroupsWithPackage = ""
    deliveredGroupsWithPackage = ""
    warning = ""
    try:
        deliveredDeliveryGroupsIds = DeliveryGroup.objects.filter(drop__name=drop, drop__release__product__name=product, deleted=False, delivered=True, obsoleted=False).only('id').values_list('id', flat=True)
        queuedDeliveryGroupsIds = DeliveryGroup.objects.filter(drop__name=drop, drop__release__product__name=product, deleted=False, delivered=False, obsoleted=False).only('id').values_list('id', flat=True)
    except Exception as e:
        message = "Error: Unable to get Delivery Group information, Exception: " + str(e)
        logger.error(message)
    try:
        for queuedDeliveryGroupId in queuedDeliveryGroupsIds:
            if str(queuedDeliveryGroupId) != str(groupId):
                if DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id=queuedDeliveryGroupId, packageRevision__package__name=artifact).exists():
                    queuedGroupsWithPackage += str(queuedDeliveryGroupId) + " "
        if queuedGroupsWithPackage:
            warning += "WARNING: Package " + artifact + " already exists in Queued Group(s): " + queuedGroupsWithPackage + ". \n"
    except Exception as e:
        message = "Error: Issue getting warning message for package, Exception: " + str(e)
        logger.error(message)
    return warning

def getWarningForObsoletedPackageVersion(product, artifact, dropName, version):
    '''
    Checks for obsoleted Artifact version and returns warning message if found.
    '''
    message = ""
    status = False
    packageObsoleted = None
    obsPkgVersion = ""
    obsPkgDrop = ""
    dropObj = ""
    initialObsValues = ('drop__name','package_revision__version','released','obsolete')

    currentDrop = Drop.objects.only('correctionalDrop').values('correctionalDrop').get(name=dropName, release__product__name=product)
    if currentDrop['correctionalDrop'] == False:
        dropObj = Drop.objects.filter(release__product__name=product, correctionalDrop=False).exclude(release__name__icontains="test").latest('id')
    else:
        dropObj = Drop.objects.get(release__product__name=product, name=dropName)

    dropAncestorIds = dropObj.getAncestorIds()
    initialDropPackageMappings = DropPackageMapping.objects.select_related('package_revision__package').only(initialObsValues).values(*initialObsValues).filter(drop__id__in=dropAncestorIds, package_revision__package__name=artifact, drop__release__product__name='ENM').order_by('-drop__id', '-package_revision__version', '-id')

    for pkg in initialDropPackageMappings:
        versionResult = compareVersions(pkg['package_revision__version'], version)
        if versionResult == 0 or versionResult == 1:
            if pkg['released'] == False and pkg['obsolete'] == True:
                status = True
                obsPkgVersion = pkg['package_revision__version']
                obsPkgDrop = pkg['drop__name']
                break
            if pkg['released'] == True and pkg['obsolete'] == False:
                status = False
                break

    if status == True:
        message = "WARNING: Artifact: " + str(artifact) + "-" + str(obsPkgVersion) + " was obsolete from drop " + str(obsPkgDrop) + ". \n "
    return message

def checkSprintVersionByArtifactId(productName, dropName, artifactId, currentArtifactVersion):
    '''
    Checking for Packages In the Baseline and Comparing versions to return warning or not
    '''
    errorMsg = None
    flag = None
    try:
        try:
            result, sprintCheck = getPackageInBaseline(productName, dropName, artifactId, True)
        except Exception as e:
            errorMsg = "Error: There is issue checking Package in Baseline for the package warning, " + str(e)
            logger.error(errorMsg)
        if sprintCheck is not None:
            sprintPkgVersion = sprintCheck.package_revision.version
            sprintDrop = sprintCheck.drop
        flag = compareSprintVersions(currentArtifactVersion, sprintPkgVersion)
    except Exception as e:
        errorMsg = "Error: There is an expected issue while checking sprint version." + str(e)
        logger.error(errorMsg)
    return str(flag)

def getWarningForPackageVersionInBaseline(product, drop, artifact, version, groupId=None):
    '''
    Checking for Package In the Baseline and Comparing versions to return warning or not
    '''
    status= ""
    resultPkgVersion = None
    resultDrop = None
    sprintPkgVersion = None
    sprintDrop = None
    result = None
    sprintCheck = None

    try:
        result, sprintCheck = getPackageInBaseline(product, drop, artifact, True)
    except Exception as e:
        errMsg = "Error: There was issue checking Package in Baseline for the package warning, " + str(e)
        logger.error(errMsg)
        return errMsg
    try:
        status += getPackageExistsInQueueWarning(product, drop, artifact, groupId)
        status += getWarningForObsoletedPackageVersion(product, artifact, drop, version)
        if result is not None:
            resultPkgVersion = result.package_revision.version
            resultDrop = result.drop
            if sprintCheck is not None:
                sprintPkgVersion = sprintCheck.package_revision.version
                sprintDrop = sprintCheck.drop
        status = status + str(getVersionWarningForPackageVersion(version, resultPkgVersion, artifact, resultDrop, sprintPkgVersion, sprintDrop))
    except Exception as e:
        errMsg = "Error: There is an issue returning the package warning, " + str(e)
        logger.error(errMsg)
        return errMsg
    return status

def getWarningForJiraType(jiraIssue):
    '''
    This function checks for excluded jira types from DB
        and gives a warning message to front page if
            given jira type is equals one from excluded list.
    '''
    warningMsg = None
    isValid = True
    try:
        issueType = jiraIssue['fields']['issuetype']['name']
        jiraTypeExclusion = JiraTypeExclusion.objects.all()
        for excludedJiraType in jiraTypeExclusion:
            if str(issueType) == str(excludedJiraType):
                isValid = False
                return isValid, "WARNING: Current Jira type (" + issueType + ") is not supported for delivery queue. Please change Jira Ticket number!", issueType
    except Exception as e:
        warningMsg = "Error: Issue getting warning message for Jira types, Exception: " + str(e)
        logger.error(warningMsg)
    return isValid, warningMsg, issueType

def getExceptionForJiraProject(jiraIssue):
    '''
    This function checks for project names from DB
        and bypass jira type exclusion if the
            given jira issue is from one of the project in exception list.
    '''
    isException = False
    try:
        issueProject = jiraIssue.get('fields').get('project').get('name')
        jiraProjects = JiraProjectException.objects.all()
        for jiraProjectName in jiraProjects:
            if str(issueProject) == str(jiraProjectName):
                isException = True
                return isException
    except Exception as e:
        warningMsg = "Error: Issue retrieving project name, Exception: " + str(e)
        logger.error(warningMsg)
    return isException

def getPackageInBaseline(product, drop, package, sprintCheck=None):
    '''
    Checking for Package In the Baseline
    '''
    dropSprintCheckDetails = None
    dropDetails = None
    if isinstance(drop, basestring):
        dropObj = Drop.objects.only('id').get(release__product__name=product,name=drop)
    else:
        dropObj = drop

    dropId = dropObj.id
    dropAncestorIds = dropObj.getAncestorIds()
    if sprintCheck:
        dropAncestorSprintCheckIds = [x for x in dropAncestorIds if x != dropId]
        initialDropPackageMappings = DropPackageMapping.objects.select_related('package_revision__package').filter(drop__id__in=dropAncestorSprintCheckIds, package_revision__package__name=package,released=1,obsolete=0).exclude(package_revision__platform='sparc').exclude(package_revision__package__obsolete_after__id__in=dropAncestorIds,package_revision__package__obsolete_after__id__lt=dropId).order_by('-drop__id').only('package_revision__package__id')
        filteredDropPackageMappingsDict = {}
        filteredDropPackageMappingIds = {}
        for dpm in initialDropPackageMappings:
            if not dpm.package_revision.package.id in filteredDropPackageMappingsDict or (dpm.drop.id == dropId):
                filteredDropPackageMappingsDict[dpm.package_revision.package.id]=dpm.id
                filteredDropPackageMappingIds = filteredDropPackageMappingsDict.values()
        try:
            dropSprintCheckDetails = DropPackageMapping.objects.prefetch_related('drop', 'package_revision__category').filter(id__in=filteredDropPackageMappingIds, package_revision__package__name=package).order_by('-date_created')[0]
        except:
            dropSprintCheckDetails = None

    initialDropPackageMappings = DropPackageMapping.objects.select_related('package_revision__package').filter(drop__id__in=dropAncestorIds, package_revision__package__name=package,released=1,obsolete=0).exclude(package_revision__platform='sparc').exclude(package_revision__package__obsolete_after__id__in=dropAncestorIds,package_revision__package__obsolete_after__id__lt=dropId).order_by('-drop__id').only('package_revision__package__id')
    filteredDropPackageMappingsDict = {}
    filteredDropPackageMappingIds = {}
    for dpm in initialDropPackageMappings:
        if not dpm.package_revision.package.id in filteredDropPackageMappingsDict or (dpm.drop.id == dropId):
            filteredDropPackageMappingsDict[dpm.package_revision.package.id]=dpm.id
            filteredDropPackageMappingIds = filteredDropPackageMappingsDict.values()
    try:
        dropDetails = DropPackageMapping.objects.prefetch_related('drop', 'package_revision__category').filter(id__in=filteredDropPackageMappingIds, package_revision__package__name=package).order_by('-date_created')[0]
    except:
        dropDetails = None
    return dropDetails, dropSprintCheckDetails

def getGroupPackageVerisonsInBaseline(product, drop, groupId):
    '''
    Checking Group's Package Verisons In Baseline and Comparing
    '''
    onlyValues = ('packageRevision__package__name', 'packageRevision__version')
    status= ""
    pkgMaps = DeliverytoPackageRevMapping.objects.prefetch_related('packageRevision').filter(deliveryGroup__id=groupId).only(onlyValues).values(*onlyValues)
    for item in pkgMaps:
        artifact = item['packageRevision__package__name']
        version = item['packageRevision__version']
        status += getWarningForPackageVersionInBaseline(product, drop, artifact, version, groupId)
    return status

def getMediaContentResult(productName, dropName, mediaArtifactName, version, testware):
    try:
        requiredProductFields = 'id', 'name', 'isoDownload', 'platform', 'category', 'kgbTests', 'cidTests', 'cdbTests', 'obsolete', 'pri', 'pkgName', 'pkgVersion', 'pkgRState', 'date', 'deliveredTo', 'size'
        productFields = Product.objects.filter(name=productName).only(requiredProductFields).values(*requiredProductFields)[0]
        requiredIsoBuildMapFields = 'kgb_test', 'testReport', 'kgb_snapshot_report', 'drop__id', 'drop__name', 'overall_status__state', 'overall_status', 'iso__drop__id', 'iso__drop__name', 'iso__drop__systemInfo', 'iso__mediaArtifact__mediaType', 'iso__mediaArtifact__testware', 'iso__id', 'iso__groupId', 'iso__version', 'iso__build_date', 'iso__arm_repo', 'package_revision__id','package_revision__size' ,'package_revision__artifactId', 'package_revision__version', 'package_revision__groupId', 'package_revision__arm_repo', 'package_revision__date_created', 'package_revision__platform', 'package_revision__category__name', 'package_revision__kgb_test', 'package_revision__kgb_snapshot_report', 'package_revision__cid_test', 'package_revision__m2type', 'package_revision__package__package_number', 'package_revision__infra'
        mediaArtifactMappingsFields = list(ISObuildMapping.objects.filter(iso__mediaArtifact__name=mediaArtifactName, iso__version=version, iso__drop__name=dropName, iso__drop__release__product__id=productFields['id']).only(requiredIsoBuildMapFields).values(*requiredIsoBuildMapFields))
        packagerevisionids = []
        for field in mediaArtifactMappingsFields:
            packagerevisionids.append(field['package_revision__id'])
            field['package_revision__rstate'] = convertVersionToRState(field['package_revision__version'])
            groupId = field['package_revision__groupId']
            field['package_revision__groupId'] = groupId.replace(".", "/")
            if (productFields['date']):
                field['package_revision__date_created'] = field['package_revision__date_created'].strftime("%Y-%m-%d %H:%M:%S")
            if field['kgb_test'] is None:
                field['kgb_test'] = "None"
        delGroupsFields = 'packageRevision__id', 'deliveryGroup__id', 'deliveryGroup__drop__id', 'deliveryGroup__deleted', 'deliveryGroup__delivered', 'deliveryGroup__obsoleted'
        delGroups = DeliverytoPackageRevMapping.objects.filter(packageRevision__id__in=packagerevisionids).only(delGroupsFields).values(*delGroupsFields).order_by('-deliveryGroup__modifiedDate')
        delGroupMap = {}
        for mapping in delGroups:
            key = mapping['packageRevision__id']
            delGpDict = {}
            delGpDict['id'] = mapping['deliveryGroup__id']
            delGpDict['dropId'] = mapping['deliveryGroup__drop__id']
            delGpDict['deleted'] = mapping['deliveryGroup__deleted']
            delGpDict['delivered'] = mapping['deliveryGroup__delivered']
            delGpDict['obsoleted'] = mapping['deliveryGroup__obsoleted']
            value = [delGpDict]
            if delGroupMap.has_key(key):
                value = delGroupMap[key]
                value.append(delGpDict)
            delGroupMap[key] = value

        if productName:
            try:
                nexusReleaseUrl = config.get('CIFWK', str(productName) + '_nexus_url')
            except:
                nexusReleaseUrl = config.get('CIFWK', 'nexus_url')
        else:
            nexusReleaseUrl = config.get('CIFWK', 'nexus_url')
        requiredObsoletedFields = 'package_revision__id', 'drop__id', 'drop__name'
        obsoleteData = list(DropPackageMapping.objects.filter(drop__name=dropName, drop__release__product__name=productName, package_revision__id__in=packagerevisionids, obsolete=1).only(requiredObsoletedFields).values(*requiredObsoletedFields))
        response, isoDeltaDict, dontCare, notNeeded = returnISOVersionArtifactDelta(productName, dropName, version, None, None, "yes", testware)
        result = {
            'mediaArtMaps':mediaArtifactMappingsFields,
            'delGroupMap':delGroupMap,
            'product':productFields,
            'obsoleteData':obsoleteData,
            'isoDeltaDict':isoDeltaDict,
            'nexusReleaseUrl':nexusReleaseUrl}
    except Exception as e:
        message = "Error: " + str(e)
        logger.error(message)
        return message
    return result

def getIsoBuildtestResultsMap(mediaArtifactVersions):
    testResultsIds = []
    testResultMap = {}

    for isoBuild in mediaArtifactVersions:
        if isoBuild['current_status']:
            currentStatusObj = ast.literal_eval(isoBuild['current_status'])
            for cdbtype,status in currentStatusObj.items():
                status_dict = {}
                if status.count('#') == 4:
                    state,start,end,testReportNumber,veLog = status.split("#")
                else:
                    state,start,end,testReportNumber = status.split("#")
                if testReportNumber != "None" and testReportNumber != "":
                    testResultsIds.append(testReportNumber)

    testResultsFields = ('id','test_report_directory')
    testResultsObjs = list(TestResults.objects.only(testResultsFields).values(*testResultsFields).filter(id__in=testResultsIds))

    for testResultsObj in testResultsObjs:
        testResultMap[testResultsObj['id']] = testResultsObj['test_report_directory']

    return testResultMap

def getIsoBuildCurrentCDBStatuses(currentStatus,productName,dropName,version,cdbTypesMap,testResultMap):
    status_list = []
    if currentStatus:
        currentStatusObj = ast.literal_eval(currentStatus)
        for cdbtype,status in currentStatusObj.items():
            status_dict = {}
            if status.count('#') == 4:
                state,start,end,testReportNumber,veLog = status.split("#")
            else:
                state,start,end,testReportNumber = status.split("#")

            if cdbtype in cdbTypesMap:
                cdbtypeObj = cdbTypesMap[cdbtype]
            else:
                break
            cdb_type_name = cdbtypeObj['name']
            cdb_type_sort_order = cdbtypeObj['sort_order']
            report=None
            if testReportNumber != "None" and testReportNumber != "":
                try:
                    report=testResultMap[int(testReportNumber)]
                except Exception as e:
                    logger.error("Error: " +str(e))

                base_url = '/' + productName + '/' + dropName + '/' + version + '/' + cdb_type_name
                if state == 'passed_manual':
                    report = base_url + '/returnKGBreadyDetails/' + str(testReportNumber)
                elif state == 'caution':
                    report = base_url + '/returnCautionStatusDetails/' + str(testReportNumber)
                elif state == 'passed' or state == 'failed':
                    report = base_url + '/returnisoreport/' + str(testReportNumber)

            status_dict['cdb_type_name'] = cdb_type_name
            status_dict['cdb_type_sort_order'] = cdb_type_sort_order
            status_dict['test_report_link'] = report
            status_dict['status'] = state
            status_dict['started_date'] = start
            status_dict['ended_date'] = end
            status_list.append(status_dict)

    status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'), reverse=True)
    return status_list

def getDeliveryQueueData(productName, drop):
    dropObj = None
    deliveryGroupIds = []
    artifactNames = []
    try:
        dropObj = Drop.objects.get(name=drop, release__product__name=productName)
    except Exception as error:
        errMsg = "Issue getting Drop " + str(drop) + " for Delivery Queue Data, Error Thrown: " + str(error)
        logger.error(errMsg)
        deliveryGroupIds.append(errMsg)
        return deliveryGroupIds

    requiredDeliveryGroupFields = ('id','component__element', 'component__parent__element', 'component__parent__label__name', 'deleted', 'missingDependencies', 'delivered', 'obsoleted', 'warning', 'createdDate', 'deliveredDate', 'autoCreated','consolidatedGroup', 'newArtifact', 'ccbApproved', 'bugOrTR')
    deliveryGroups = DeliveryGroup.objects.select_related('component').filter(drop=dropObj).order_by('-modifiedDate').only(requiredDeliveryGroupFields).values(*requiredDeliveryGroupFields)

    for group in deliveryGroups:
        deliveryGroupIds.append(group['id'])

    requiredDeliveryGroupCommentFields = ('comment','deliveryGroup__id','comment','date')
    commentMappings = DeliveryGroupComment.objects.filter(deliveryGroup__id__in=deliveryGroupIds).only(requiredDeliveryGroupCommentFields).values(*requiredDeliveryGroupCommentFields)

    requiredDeliverytoPackageRevMappingFields = ('deliveryGroup__id','team', 'kgb_test', 'testReport', 'kgb_snapshot_report', 'packageRevision__package__name','packageRevision__date_created','packageRevision__version','packageRevision__kgb_test','packageRevision__category__name','id', 'packageRevision__groupId', 'packageRevision__m2type', 'packageRevision__arm_repo', 'packageRevision__size', 'packageRevision__package__includedInPriorityTestSuite')
    artifactMappings = DeliverytoPackageRevMapping.objects.select_related('packageRevision__package', 'packageRevision__category').filter(deliveryGroup__id__in=deliveryGroupIds).only(requiredDeliverytoPackageRevMappingFields).values(*requiredDeliverytoPackageRevMappingFields)

    requiredJiraDeliveryGroupMapFields = ('jiraIssue__id','deliveryGroup__id','jiraIssue__jiraNumber','jiraIssue__issueType','id')
    jiraMappings = JiraDeliveryGroupMap.objects.select_related('jiraIssue').filter(deliveryGroup__id__in=deliveryGroupIds).only(requiredJiraDeliveryGroupMapFields).values(*requiredJiraDeliveryGroupMapFields)
    jiraIssueIds = []
    for issueId in jiraMappings:
        jiraIssueIds.append(issueId['jiraIssue__id'])

    requiredLabelToJiraIssueMapFields = ('jiraLabel__name', 'jiraLabel__type','jiraIssue__id')
    jiraToLabelMappings = LabelToJiraIssueMap.objects.select_related('jiraLabel').filter(jiraIssue__id__in=jiraIssueIds).only(requiredLabelToJiraIssueMapFields).values(*requiredLabelToJiraIssueMapFields)

    noArtifactMappingsTestware = DeliverytoPackageRevMapping.objects.select_related('packageRevision__package', 'packageRevision__category').filter(deliveryGroup__id__in=deliveryGroupIds).exclude(packageRevision__category__name='testware').only(requiredDeliverytoPackageRevMappingFields).values(*requiredDeliverytoPackageRevMappingFields)
    noOnlyTestwareDelGrpIds = []
    for grp in noArtifactMappingsTestware:
        noOnlyTestwareDelGrpIds.append(grp['deliveryGroup__id'])

    requiredIsoDeliveryGroupMapFields = ('iso__id','deliveryGroup__id','iso__version','deliveryGroup_status','iso__mediaArtifact__name')
    isoMappings = IsotoDeliveryGroupMapping.objects.select_related('iso').filter(deliveryGroup__id__in=noOnlyTestwareDelGrpIds, iso__mediaArtifact__testware=0, iso__mediaArtifact__category__name="productware").only(requiredIsoDeliveryGroupMapFields).values(*requiredIsoDeliveryGroupMapFields).order_by('-iso__build_date','-modifiedDate')
    nexusUrl = getNexusUrlForProduct(productName)
    requiredTestwareArtifactFields = ('testware_artifact__name', 'testware_type__type')
    testwareTypeMappings = TestwareTypeMapping.objects.only(requiredTestwareArtifactFields).values(*requiredTestwareArtifactFields).all()
    serviceMappings, listOfPackageMappings = getListsOfVmServices(artifactMappings)

    for group in deliveryGroups:
        cnDGToDGMapObjList = None
        testware = []
        includedInPriorityTestSuite = []
        testwareTypes = set()
        artifactMappingsForThisGroup = []
        kgbResult = []
        artifactOnly = []
        cnDGToDGMapRequiredFields = ('deliveryGroup__id', 'cnDeliveryGroup__id', 'cnDeliveryGroup__delivered', 'cnDeliveryGroup__obsoleted', 'cnDeliveryGroup__deleted')
        for artifactMapping in artifactMappings:
            service = []
            if artifactMapping['deliveryGroup__id'] == group['id']:
                if artifactMapping['packageRevision__category__name'] == "testware":
                    testware = ['True']
                service = getPackageRevisionServices(artifactMapping, serviceMappings, listOfPackageMappings)
                if service:
                    artifactMapping['services'] = service
                else:
                    artifactMapping['services'] = "None"

                if artifactMapping['packageRevision__package__includedInPriorityTestSuite']:
                    includedInPriorityTestSuite = ['True']
                    artifactTestwareTypes = set()
                    for testwareTypeMap in testwareTypeMappings:
                        if testwareTypeMap['testware_artifact__name'] == artifactMapping['packageRevision__package__name']:
                            artifactTestwareTypes.add(testwareTypeMap['testware_type__type'])
                            testwareTypes.add(testwareTypeMap['testware_type__type'])
                    artifactMapping['testwareTypes'] = list(artifactTestwareTypes)
                    artifactMapping['priorityTestware'] = True
                else:
                    artifactMapping['priorityTestware'] = False
                frozenKGBresult = "False"
                if artifactMapping['kgb_test'] is not None:
                    frozenKGBresult = "True"
                artifactNexusUrl = str(nexusUrl + "/"+ artifactMapping['packageRevision__arm_repo'] +"/" + str(artifactMapping['packageRevision__groupId']).replace(".", "/") + "/" + artifactMapping['packageRevision__package__name'] + "/" + artifactMapping['packageRevision__version'] + "/" + artifactMapping['packageRevision__package__name'] + "-" + artifactMapping['packageRevision__version'] + "." + artifactMapping['packageRevision__m2type'])
                artifactMappingsForThisGroup.append({"artifact":artifactMapping, "nexusUrl":artifactNexusUrl, "frozenKGBresult": frozenKGBresult})

        cnDGToDGMapResult = []
        cnDGToDGMapObjList = CNDGToDGMap.objects.filter(deliveryGroup__id = group['id']).only(cnDGToDGMapRequiredFields).values(*cnDGToDGMapRequiredFields)
        for cnDGToDGMapObj in cnDGToDGMapObjList:
            cnDGToDGMapResult.append(cnDGToDGMapObj)

        commentMappingsForThisGroup = []
        for commentMapping in commentMappings:
            if commentMapping['deliveryGroup__id'] == group['id']:
                commentMappingsForThisGroup.append(commentMapping)

        jirasForThisGroup = []
        for jiraMapping in jiraMappings:
            if jiraMapping['deliveryGroup__id'] == group['id']:
                jira = jiraMapping
                labels = []
                tcgs = []
                for jiraToLabelMapping in jiraToLabelMappings:
                    if jiraToLabelMapping['jiraIssue__id'] == jiraMapping['jiraIssue__id']:
                        if jiraToLabelMapping['jiraLabel__type'] == "label":
                            labels.append(jiraToLabelMapping['jiraLabel__name'])
                        else:
                            tcgs.append(jiraToLabelMapping['jiraLabel__name'])
                jiraLink = identifyJiraInstance(jira.get('jiraIssue__jiraNumber'))
                jirasForThisGroup.append({"jira":jira, "jiraLink": jiraLink, "labels":labels, "tcgs": tcgs})
        group["iso"] = None
        for iso in isoMappings:
            if iso['deliveryGroup__id'] == group['id']:
                group["iso"] = iso
                break
        group["artifacts"] = artifactMappingsForThisGroup
        group["comments"] = commentMappingsForThisGroup
        group["jiras"] = jirasForThisGroup
        group["testware"] = testware
        group["includedInPriorityTestSuite"] = includedInPriorityTestSuite
        group["testwareTypes"] = list(testwareTypes)
        group["impactedCNDeliveryGroup"] = cnDGToDGMapResult
    return deliveryGroups

def getListsOfVmServices(artifactMappings):
    serviceMappings = listOfPackageMappings = artifactNames = []
    requiredPackageRevisionServiceMapFields = ('package_revision__artifactId', 'package_revision__version', 'service__name')
    requiredServicePackageMapFields = ('package__name', 'service__name')

    for artifact in artifactMappings:
        artifactNames.append(artifact["packageRevision__package__name"])
    serviceMappings = VmServicePackageMapping.objects.select_related('service','package').filter(package__name__in = artifactNames).only(requiredServicePackageMapFields).values(*requiredServicePackageMapFields)
    listOfPackageMappings = PackageRevisionServiceMapping.objects.select_related('package_revision','service').filter(package_revision__package__name__in = artifactNames).only(requiredPackageRevisionServiceMapFields).values(*requiredPackageRevisionServiceMapFields).order_by('-id')
    return serviceMappings, listOfPackageMappings

def getPackageRevisionServices(artifactMapping, serviceMappings, listOfPackageMappings):
    service = []
    serviceVersion = None

    for packageRevServiceMapping in listOfPackageMappings:
        if packageRevServiceMapping['package_revision__artifactId'] == artifactMapping['packageRevision__package__name']:
            if not serviceVersion:
                if LooseVersion(packageRevServiceMapping['package_revision__version']) <= LooseVersion(artifactMapping['packageRevision__version']):
                    serviceVersion = packageRevServiceMapping['package_revision__version']
                    service.append(packageRevServiceMapping['service__name'])
            else:
                if LooseVersion(serviceVersion) == LooseVersion(packageRevServiceMapping['package_revision__version']):
                    service.append(packageRevServiceMapping['service__name'])
                continue
    if not service:
        for servicePackageMapping in serviceMappings:
            if servicePackageMapping['package__name'] == artifactMapping['packageRevision__package__name']:
                service.append(servicePackageMapping['service__name'])
    return service

def getDeliveryGroupCsvFieldsData(grp):
    if grp['delivered']:
        status = "Delivered"
    elif grp['obsoleted']:
        status = "Obsoleted"
    elif grp['deleted']:
        status = "Deleted"
    else:
        status = "Queued"
    if grp['iso']:
        iso = grp['iso']['iso__version']
    else:
        iso = ''
    count = 0
    firstArtifact = True
    artifacts = ""
    for artifact in grp['artifacts']:
        if not str(artifact['artifact']['packageRevision__package__name']).startswith(('ERICTAF', 'ERICTW')):
            count += 1
        if not firstArtifact:
            artifacts = artifacts + '; '
        services = []
        if not artifact['artifact']['services'] == "None":
            for service in artifact['artifact']['services']:
                services.append(str(service))
            artifacts = artifacts + artifact['artifact']['packageRevision__package__name'] + ', ' + artifact['artifact']['packageRevision__version'] + ', ' + artifact['artifact']['team'] + ', Services: ' + str(services)
        else:
            artifacts = artifacts + artifact['artifact']['packageRevision__package__name'] + ', ' + artifact['artifact']['packageRevision__version'] + ', ' + artifact['artifact']['team']
        firstArtifact = False

    dateCreated = ''
    dateDelivered = ''
    firstComment = True
    comments = ""
    for comment in grp['comments']:
        if not firstComment:
            comments = comments + '; '
        date = comment['date'].strftime('%Y-%m-%d %H:%M:%S')
        comments = comments + comment['comment'] + ', ' + date
        firstComment = False
        delGrpComment = smart_str(comment['comment'])
        if str(grp['createdDate']) != "None":
            dateCreated = grp['createdDate'].strftime('%Y-%m-%d %H:%M:%S')
        elif 'created this Delivery Group' in delGrpComment:
            dateCreated = date
        if str(grp['deliveredDate']) != "None":
            dateDelivered = grp['deliveredDate'].strftime('%Y-%m-%d %H:%M:%S')
        elif 'delivered this group' in delGrpComment:
            dateDelivered = date

    firstJira = True
    jiras = ""
    for jira in grp['jiras']:
        if not firstJira:
            jiras = jiras + '; '
        if jira['tcgs'] != []:
            jiras = jiras + jira['jira']['jiraIssue__jiraNumber'] + ', ' + jira['jira']['jiraIssue__issueType'] + ' | TCG: ' + str(jira['tcgs']).replace("[", "").replace("u'", "").replace("'", "").replace("]", "")
        else:
            jiras = jiras + jira['jira']['jiraIssue__jiraNumber'] + ', ' + jira['jira']['jiraIssue__issueType']
        firstJira = False

    return status, dateCreated, dateDelivered, count, artifacts, smart_str(comments), jiras, iso

def setMissingDependencies(user, product, drop, groupId, missingDeps):
    '''
    The setMissingDependencies function sets a group to have missing Dependencies and the group can not be delivered
    '''
    missingDependencies = None
    missingDependenciesComment = None
    try:
        deliveryGroupObj = DeliveryGroup.objects.get(id=groupId)
    except Exception as error:
        logger.error("Error setting the missing Dependencies flag for Delivery Group " + str(groupId) + ": " + str(error))
        return missingDependencies
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if not str(missingDeps) == "None":
            missingDependencies = True
            deliveryGroupObj.missingDependencies = True
            missingDependenciesComment = str(user.first_name) + " "  + str(user.last_name) + " flagged this delivery group as having missing dependencies"
            newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=missingDependenciesComment, date=now)
        else:
            if deliveryGroupObj.missingDependencies == True:
                deliveryGroupObj.missingDependencies = False
                missingDependenciesComment = str(user.first_name) + " "  + str(user.last_name) + " unflagged this delivery group as having missing dependencies"
                newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=missingDependenciesComment, date=now)
                missingDependencies = False
        deliveryGroupObj.save(force_update=True)
        if missingDependenciesComment != None:
            sendDeliveryGroupUpdatedEmail(user, str(groupId), missingDependenciesComment)
        return missingDependencies
    except Exception as e:
        logger.error("Error setting the missing Dependencies flag for Delivery Group " + str(groupId) + ": " + str(e))


def getBomsFromIsoList(isoObjects):
    ret =[]
    for isoObj in isoObjects:
        status_list = []
        if isoObj["current_status"]:
            currentStatusObj = ast.literal_eval(isoObj["current_status"])
            for cdbtype,status in currentStatusObj.items():
                status_dict = {}
                if status.count('#') == 4:
                    state,start,end,testReportNumber,veLog = status.split("#")
                else:
                    state,start,end,testReportNumber = status.split("#")
                cdbtypeObj = CDBTypes.objects.get(id=cdbtype)
                cdb_type_sort_order = cdbtypeObj.sort_order

                status_dict['cdb_type_sort_order'] = cdb_type_sort_order
                status_dict['status'] = state
                status_list.append(status_dict)
        status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'), reverse=True)

        if status_list and (status_list[-1]).get('status') == 'passed':
            ret.append(isoObj)
    return ret

def getPackagesInTeam(team,product):
    mappingObj = PackageComponentMapping.objects.only('package__id', 'package__name').values('package__id', 'package__name').filter(component__label__name='team',component__element = team,component__product__name=product)
    artifacts = []
    for artifact in mappingObj:
        artifacts.append(artifact['package__name'])
    return artifacts

def sendObsoleteGroupErrorEmail(productName, drop, groupId, status, signum):
    '''
    To send email if there was issue Obsoleting Delivery Group
    '''
    message = []
    if not isinstance(status, basestring):
        count = 1
        for info in status:
            message.append("\t\t" + str(count) + ". " +  str(info) + "\n")
            count = count + 1
        status = ''.join(message)
    emailHeader = "Investigate Issue obsoleting Delivery Group " + str(groupId) + " From "+ str(productName) + " Drop " + str(drop)
    emailContentTeam = '''This is an automated mail from the CI Framework
        \nThe following Delivery Group ''' + str(groupId) + ''' encountered an issue whilst trying to obsolete:
        \nStatus of the Group: \n ''' + str(status) + '''
        \nInvestigate this Issue. The obsoletion was made by : \n"''' + str(signum) + '''"'''

    emailHeaderObsoletor = "There was issue obsoleting Delivery Group " + str(groupId) + " From "+ str(productName) + " Drop " + str(drop)
    emailContentObsoletor = '''This is an automated mail from the CI Framework
    \nThe following Delivery Group ''' + str(groupId) + ''' encountered an issue whilst trying to obsolete:
    \nStatus of the Group: \n ''' + str(status) + '''
    \nIt has been reported to Axis Team for investigation. \n'''

    fromEmail = config.get("CIFWK", "fromEmail")
    teamEmail = config.get("CIFWK", "cifwkDistributionList")
    send_mail(emailHeader,emailContentTeam,fromEmail,[teamEmail],fail_silently=False)
    send_mail(emailHeaderObsoletor,emailContentObsoletor,fromEmail,[signum + '@lmera.ericsson.se'],fail_silently=False)

def addDeliveryGroupsToIso(iso):
    '''
    Function to create delivery groups mappings to ISO in the table
    Delivery Groups that have been modified since last ISO built for the release
    '''
    mappings = []
    try:
        baseIsoFields = ('id','build_date')
        isoDropCheck = ISObuild.objects.filter(drop__release__id=iso.drop.release.id,drop=iso.drop, mediaArtifact__testware=iso.mediaArtifact.testware, mediaArtifact__category=iso.mediaArtifact.category)
        if len(isoDropCheck) == 1:
            previousDrop = Drop.objects.filter(release__id=iso.drop.release.id).exclude(id=iso.drop.id).order_by('-id')[0]
            baseIsos = ISObuild.objects.filter(drop__release__id=iso.drop.release.id,drop=previousDrop, build_date__lt=iso.build_date, mediaArtifact__testware=iso.mediaArtifact.testware, mediaArtifact__category=iso.mediaArtifact.category).order_by('-build_date').only(baseIsoFields).values(*baseIsoFields)
        else:
            baseIsos = ISObuild.objects.filter(drop__release__id=iso.drop.release.id,drop=iso.drop, build_date__lt=iso.build_date, mediaArtifact__testware=iso.mediaArtifact.testware, mediaArtifact__category=iso.mediaArtifact.category).order_by('-build_date').only(baseIsoFields).values(*baseIsoFields)

        if not baseIsos:
            return
        startDate = baseIsos[0]['build_date']
        endDate = iso.build_date

        requiredIsoDeliveryGroupMapFields = ('deliveryGroup__id',)
        isoMappings = IsotoDeliveryGroupMapping.objects.select_related('iso').filter(iso__mediaArtifact=iso.mediaArtifact, iso__mediaArtifact__category=iso.mediaArtifact.category, deliveryGroup__drop__id=iso.drop.id).only(requiredIsoDeliveryGroupMapFields).values(*requiredIsoDeliveryGroupMapFields).order_by('-iso__build_date','-modifiedDate')

        mappingFields = ('deliveryGroup__id','deliveryGroup__delivered','deliveryGroup__obsoleted', 'deliveryGroup__deleted','deliveryGroup__modifiedDate')

        if iso.mediaArtifact.testware:
            artifactMappingsTestware = DeliverytoPackageRevMapping.objects.select_related('packageRevision__package', 'packageRevision__category').filter(deliveryGroup__drop=iso.drop, packageRevision__category__name='testware').only('deliveryGroup__id').values('deliveryGroup__id')
            testwareDelGrpIds = []
            for grp in artifactMappingsTestware:
                testwareDelGrpIds.append(grp['deliveryGroup__id'])
            mappings = DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=isoMappings,deliveryGroup__modifiedDate__range=(startDate,endDate)).distinct().order_by('-deliveryGroup__modifiedDate').only(mappingFields).values(*mappingFields) | DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=testwareDelGrpIds, deliveryGroup__drop__id=iso.drop.id,deliveryGroup__delivered=True,deliveryGroup__modifiedDate__range=(startDate,endDate)).distinct().order_by('-deliveryGroup__modifiedDate').only(mappingFields).values(*mappingFields)
        else:
            noArtifactMappingsTestware = DeliverytoPackageRevMapping.objects.select_related('packageRevision__package', 'packageRevision__category').filter(deliveryGroup__drop=iso.drop).exclude(packageRevision__category__name='testware').only('deliveryGroup__id').values('deliveryGroup__id')
            noOnlyTestwareDelGrpIds = []
            for grp in noArtifactMappingsTestware:
                noOnlyTestwareDelGrpIds.append(grp['deliveryGroup__id'])
            mappings = DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=isoMappings,deliveryGroup__modifiedDate__range=(startDate,endDate)).distinct().order_by('-deliveryGroup__modifiedDate').only(mappingFields).values(*mappingFields) | DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=noOnlyTestwareDelGrpIds, deliveryGroup__drop__id=iso.drop.id,deliveryGroup__delivered=True,deliveryGroup__modifiedDate__range=(startDate,endDate)).distinct().order_by('-deliveryGroup__modifiedDate').only(mappingFields).values(*mappingFields)
        for mapp in mappings:
            if mapp['deliveryGroup__delivered']:
                status = 'delivered'
            elif mapp['deliveryGroup__obsoleted']:
                status = 'obsoleted'
            elif mapp['deliveryGroup__deleted']:
                status = 'deleted'
            else:
                status = 'restored'
            isoDelGrpMappingObj = IsotoDeliveryGroupMapping.objects.create(iso=iso, deliveryGroup_id=mapp['deliveryGroup__id'], deliveryGroup_status=status, modifiedDate = mapp['deliveryGroup__modifiedDate'])

        result = "Created delivery group mappings for "+str(iso.artifactId)+ " Version: "+str(iso.version)
    except Exception as e:
        logger.error("ISO created, issue creating ISO delivery group mappings" +str(e))
        result = "ERROR: creating ISO delivery group mappings: "+str(e)

    return result

def returnNewToIso(artifactsAndVersions,isoVersion,isoGroup,isoArtifact):
    ret = ""
    try:
        category = "productware"
        testware = False
        requiredISOValues = ('id','version')
        ISOObj = ISObuild.objects.only(requiredISOValues).values(*requiredISOValues).get(groupId=isoGroup,artifactId=isoArtifact,version=isoVersion, mediaArtifact__testware=testware, mediaArtifact__category__name=category)
        requiredISOMappingValues = ('package_revision__package__name','package_revision__version','package_revision__groupId')
        ISOPackageRevList = ISObuildMapping.objects.filter(iso__id=ISOObj['id']).only(requiredISOMappingValues).values(*requiredISOMappingValues)
        contentsString = ""
        for item in ISOPackageRevList:
            contentsString=contentsString+"#"+item['package_revision__package__name']+"::"+item['package_revision__version']+"::"+item['package_revision__groupId']
        artifactsAndVersionsList = artifactsAndVersions.split('#')
        for item in artifactsAndVersionsList:
            if item != "":
                if not item in contentsString:
                    ret = ret +"#"+item
    except Exception as e:
        logger.error("Issue getting packages not in ISO" +str(e))
    return ret


def returnNewInBaseline(artifactsAndVersions):
    ret=[]
    category = "productware"
    try:
        ISOObj=ISObuild.objects.only('id').values('id').filter(mediaArtifact__testware=False, drop__release__product__name="ENM", mediaArtifact__category__name=category).order_by('-id')[0]
        requiredISOMappingValues = ('package_revision__package__name','package_revision__version')
        if 'ERICTAF' or 'ERICTW' in str(artifactsAndVersions) :
            ISOObjTestware=ISObuild.objects.only('id').values('id').filter(mediaArtifact__testware=True, drop__release__product__name="ENM").order_by('-id')[0]
            ISOPackageRevList = ISObuildMapping.objects.filter(iso__id=ISOObj['id']).only(requiredISOMappingValues).values(*requiredISOMappingValues) | ISObuildMapping.objects.filter(iso__id=ISOObjTestware['id']).only(requiredISOMappingValues).values(*requiredISOMappingValues)
        else:
            ISOPackageRevList = ISObuildMapping.objects.filter(iso__id=ISOObj['id']).only(requiredISOMappingValues).values(*requiredISOMappingValues)
        contentsString = ""
        for item in ISOPackageRevList:
            contentsString=contentsString+"@@"+item['package_revision__package__name']+"::"+item['package_revision__version']
        artifactsAndVersionsList = artifactsAndVersions.split('@@')
        for item in artifactsAndVersionsList:
            if item != "":
                if item.count("::")==2:
                    item=strip_character.join(item.split(strip_character)[:2])
                if not item in contentsString:
                    ret.append(item)
    except Exception as e:
        errMsg = "Issues while finding ArtifactandVersion." + str(e)
        logger.error(errMsg)
        return [{"result":"Failure to search for ArtifactandVersion", "error":str(errMsg)}]
    return ret


def updateJiraData(product, drop):
    '''
    Used for Updating JIRA Data
    '''
    result = "Updated JIRA Data Successfully"
    try:
        if drop == "None":
            dropList = []
            count = 0
            dropObj = Drop.objects.only('id').values('id').filter(release__product__name=product).order_by('-id')
            for drp in dropObj:
                dropList.append(drp['id'])
                if count == 1:
                    break
                count = count + 1
            jiraDelGrpMaps = JiraDeliveryGroupMap.objects.only('jiraIssue__jiraNumber').values('jiraIssue__jiraNumber').filter(deliveryGroup__drop__id__in=dropList)
        else:
            dropObj = Drop.objects.get(release__product__name=product, name=drop)
            jiraDelGrpMaps = JiraDeliveryGroupMap.objects.only('jiraIssue__jiraNumber').values('jiraIssue__jiraNumber').filter(deliveryGroup__drop=dropObj)
        for jira in jiraDelGrpMaps:
            addJiraIssueToDeliveryGroup("None", jira['jiraIssue__jiraNumber'])
    except Exception as e:
        result = "Error Issue updating JIRA Data: " + str(e)
        logger.error(result)
    return result


def sendDeliveryGroupUpdatedEmail(currentUser, deliverGroupId, modifications):
    '''
    Send email for Deliver Group updates
    '''
    name = str(currentUser.first_name) + " " + str(currentUser.last_name)
    currentUserEmail = currentUser.email
    recipients = []
    groupCreatorEmail = DeliveryGroup.objects.only('creator').get(id=deliverGroupId).creator
    subscribersMap = DeliveryGroupSubscription.objects.filter(deliveryGroup=deliverGroupId)

    dm = config.get("CIFWK", "fromEmail")
    mailHeader = "Delivery Group "+deliverGroupId+" Modification Notice"
    mailContent = '''This is an automated mail from the CI Framework
    \nDear user,\n\nThe following Delivery Group has been modified...
    \nDelivery Group:\t\t''' + deliverGroupId  + '''
    \nModified By:\t\t''' + name + '''
    \nModification:\n''' + modifications

    if currentUserEmail != None:
       recipients.append(currentUserEmail)

    if groupCreatorEmail != None:
       recipients.append(groupCreatorEmail)

    subscribeEmails = config.get("CIFWK", "groupUpdatedEmail")
    if subscribeEmails == "groupUpdatedEmailTo":
        for subscriber in subscribersMap:
            recipients.append(subscriber.user.email)
    else:
        recipients = []
        recipients.append(subscribeEmails)

    send_mail(mailHeader, mailContent, dm, recipients, fail_silently=False)

def validatePackageAndGroup(listOfpackageRevs,drop):
    '''
    Function validates that a Delivery Group with identical content does not already exist in the same drop
    '''
    pkgRevAssociatedWithGroup = []
    existingGroupsList = []
    existingGroupsListLong =[]
    dropName = drop
    result = False
    pkgRevAssociatedWithGroup= DeliverytoPackageRevMapping.objects.values('deliveryGroup').annotate(values=Concat('packageRevision')).filter(deliveryGroup__drop__name=dropName)
    for pkgsversions in pkgRevAssociatedWithGroup:
        existingGroupsListLong =[]
        existingGroupsList= pkgsversions['values'].split(',')
        for value in existingGroupsList:
            valueLong =long(value)
            existingGroupsListLong.append(valueLong)
            if(set(existingGroupsListLong) == set(listOfpackageRevs)):
                result = "Identical content is created in an Existing Delivery Group: Delivery Group Number :" +str(pkgsversions['deliveryGroup'])
                logger.error(result)
                return result
    return result

def getDeliveryGroupPkgRevFrozenKGB(groupId, artifactName):
        '''
        Function that gets the DeliveryGroup's Package Rev Frozen KGB Results
        '''
        result = []
        artifact = None
        deliveryGrpPkgRevKgb = None
        try:
            deliveryGroup = DeliveryGroup.objects.get(pk=groupId)
        except Exception as error:
            msg = 'There was an issue getting Delivery Group: ' + str(groupId) +' for Frozen Delivery Group KGB Results - ' + str(error)
            return {'error' : str(msg)}
        if artifactName is not None:
            try:
                artifact = Package.objects.get(name=artifactName)
            except Exception as error:
                msg = 'There was an issue getting Artifact for Frozen Delivery Group KGB Results - ' + str(error)
                return {'error' : str(msg)}
        fields = 'deliveryGroup__drop__name', 'deliveryGroup__id', 'packageRevision__artifactId', 'packageRevision__version', 'kgb_test', 'testReport', 'kgb_snapshot_report',
        if artifact is None:
            deliveryGrpPkgRevKgb = DeliverytoPackageRevMapping.objects.only(fields).values(*fields).filter(deliveryGroup=deliveryGroup)
        else:
            deliveryGrpPkgRevKgb = DeliverytoPackageRevMapping.objects.only(fields).values(*fields).filter(deliveryGroup=deliveryGroup, packageRevision__package=artifact)
        if deliveryGrpPkgRevKgb:
            for kgbResults in deliveryGrpPkgRevKgb:
                if kgbResults['kgb_test'] is not None:
                    result.append({"name": str(kgbResults['packageRevision__artifactId']),
                    "version": str(kgbResults['packageRevision__version']),
                    "kgb": str(kgbResults['kgb_test']),
                    "testReport": str(kgbResults['testReport']),
                    "kgbSnapshotReport": kgbResults['kgb_snapshot_report']
                    })
        else:
           result = {'error' : 'No Frozen Delivery Group KGB Results Found'}
        if not result:
           result = {'error' : 'No Frozen Delivery Group KGB Results Found'}
        return result

def getDropPkgRevFrozenKGB(productName, dropName, type=None, artifactName=None):
        '''
        Function that gets the DeliveryGroup's Package Rev Frozen KGB Results
        '''
        result = []
        drop = None
        dropKgb = None
        pkgRevKgb = None
        try:
            drop = Drop.objects.get(name=dropName, release__product__name=productName)
        except Exception as error:
            msg = 'There was an issue getting drop: ' + str(dropName) +' for Frozen Drop KGB Results - ' + str(error)
            return {'error' : str(msg)}
        if artifactName is None:
            dropKgb = getPackageBaseline(drop, type)
        else:
            pkgRevKgb, sprintCheck = getPackageInBaseline(productName, drop, artifactName)
        if dropKgb:
            for kgbResults in dropKgb:
                if kgbResults.kgb_test is not None:
                    result.append({"deliveryDrop": str(kgbResults.drop.name),
                       "name": str(kgbResults.package_revision.artifactId),
                       "version": str(kgbResults.package_revision.version),
                       "kgb": str(kgbResults.kgb_test),
                       "testReport": str(kgbResults.testReport),
                       "kgbSnapshotReport": kgbResults.kgb_snapshot_report
                    })
        elif pkgRevKgb:
             if pkgRevKgb.kgb_test is not None:
                 result.append({"deliveryDrop": str(pkgRevKgb.drop.name),
                     "name": str(artifactName),
                     "version": str(pkgRevKgb.package_revision.version),
                     "kgb": str(pkgRevKgb.kgb_test),
                     "testReport": str(pkgRevKgb.testReport),
                     "kgbSnapshotReport": pkgRevKgb.kgb_snapshot_report
                    })
        else:
            result = {'error' : 'No Frozen Drop KGB Results Found'}
        if not result:
            result = {'error' : 'No Frozen Drop KGB Results Found'}
        return result

def createMediaArtifactVersionToArtifactMapping(product,mediaArtifactVersion,drop,artifact,pkgRevKgb=None,testReport=None, kgbSnapshotReport=None):
    '''
    Function that creates the Media Artifact Version To Artifact Mapping for Media Artifact Version Content
    '''
    if product == "ENM":
        if pkgRevKgb:
            ISObuildMapping.objects.create(iso=mediaArtifactVersion, drop=drop, package_revision=artifact, kgb_test=pkgRevKgb, testReport=testReport, kgb_snapshot_report=kgbSnapshotReport)
        else:
            kgbReport = getPkgRevKgbReport(artifact)
            ISObuildMapping.objects.create(iso=mediaArtifactVersion, drop=drop, package_revision=artifact, kgb_test=artifact.kgb_test, testReport=kgbReport, kgb_snapshot_report=artifact.kgb_snapshot_report)
    else:
        ISObuildMapping.objects.create(iso=mediaArtifactVersion, drop=drop, package_revision=artifact)

def getMediaArtifactContentPkgRevFrozenKGB(mediaArtifactName, mediaArtifactVersion, artifactName):
        '''
        Function that gets the Media Artifact's Version Frozen KGB Results
        '''
        result = []
        artifact = None
        if artifactName is not None:
            try:
                artifact = Package.objects.get(name=artifactName)
            except Exception as error:
                msg = 'There was an issue getting Artifact for Frozen  Media Artifact KGB Results - ' + str(error)
                return {'error' : str(msg)}
        fields = 'drop__name', 'package_revision__artifactId', 'package_revision__version', 'kgb_test', 'testReport', 'kgb_snapshot_report',
        if artifact is None:
            pkgRevKgb = ISObuildMapping.objects.only(fields).values(*fields).filter(iso__mediaArtifact__name=mediaArtifactName, iso__version=mediaArtifactVersion)
        else:
            pkgRevKgb = ISObuildMapping.objects.only(fields).values(*fields).filter(iso__mediaArtifact__name=mediaArtifactName, iso__version=mediaArtifactVersion, package_revision__package=artifact)
        if pkgRevKgb:
            for kgbResults in pkgRevKgb:
                result.append({ "deliveryDrop": str(kgbResults['drop__name']),
                    "name": str(kgbResults['package_revision__artifactId']),
                    "version": str(kgbResults['package_revision__version']),
                    "kgb": str(kgbResults['kgb_test']),
                    "testReport": str(kgbResults['testReport']),
                    "kgbSnapshotReport": kgbResults['kgb_snapshot_report']
                    })
        else:
           result = {'error' : 'No Frozen Media Artifact KGB Results Found'}
        if not result:
            result = {'error' : 'No Frozen Media Artifact KGB Results Found'}
        return result


def getJiraCredentials():
    jira_user = config.get('CIFWK', 'jiraUser')
    jira_password = config.get('CIFWK', 'jiraPassword')
    jira_rest_url = config.get('CIFWK', 'jiraRestApiUrl')
    return jira_user, jira_password, jira_rest_url


def getNexusUrlForArtifactVersion(artifactId, version, local=False):
    """
        Gets the version of an Artifact specified from Nexus Repo
    """

    try:
        packageRevision = PackageRevision.objects.get(package__name=artifactId, version=version)
    except PackageRevision.DoesNotExist:
        errorMessage = "Package Revision with Given Artifact ID - %s - and Version - %s - does not exist" % (artifactId, version)
        logger.error(errorMessage)
        return [{"error": errorMessage}]

    try:
        if local:
            nexusUrl = packageRevision.getNexusUrl("AthloneEiffelProxy")
            # proxy for ENM
            nexusUrl = re.sub("releases", "enm_releases", nexusUrl)
            # proxy for NSS
            if nssProductCheck(packageRevision.groupId):
                nss_proxy_nexus_storage = config.get('CIFWK', 'NSS_nexus_url').split('/')[-1]
                local_proxy_storage = config.get('CIFWK', 'AthloneEiffelProxy_nexus_url').split('/')[-1]
                nexusUrl = re.sub(local_proxy_storage + "/" + packageRevision.arm_repo, local_proxy_storage + "/" + nss_proxy_nexus_storage, nexusUrl)
        else:
            nexusUrl = packageRevision.getNexusUrl()
        return [{"url": nexusUrl}]
    except Exception as error:
        errorMessage = "Nexus URL unavailable for given Artifact ID and Version - %s" % error.message
        logger.error(errorMessage)
        return [{"error": errorMessage}]

def deliverAutoCreatedGroup(product, drop, user, group_id):
    '''
    This function delivers Auto Created group which are auto-crated through pipeline 2.0
    '''
    if not Product.objects.filter(name=product).exists():
        return "ERROR: The product " + product + " was not found in the Database", 1
    if not Drop.objects.filter(name=drop, release__product__name=product).exists():
        return "ERROR: Drop " + drop + " does not exist for the product " + product, 1
    faultedGroups = ""
    deliverer = str(user.first_name) + " " + str(user.last_name)
    if DeliveryGroup.objects.filter(id=group_id,deleted=0, obsoleted=0, delivered=0).exists():
        requiredValues = ('id', 'creator', 'drop__stop_auto_delivery')
        delGroup = DeliveryGroup.objects.only(requiredValues).values(*requiredValues).get(id=group_id, deleted=0, obsoleted=0, delivered=0)
        if delGroup['drop__stop_auto_delivery'] == True:
            return "Auto-delivery is disabled by main-track at the moment", 2
        delivery_thread = DGThread(performGroupDeliveries, args=(product, drop, group_id, user))
        delivery_thread.start()
        delivery_thread.join()
        deliveryFault, deliverySummary, fullList = delivery_thread.get_result()
        if deliveryFault:
            comment = deliverer + " could not auto-deliver this group (on behalf of " + str(delGroup['creator'])+ ") to the drop, as part of a delivery of all Auto Created groups("+str(group_id)+")" + " due to " + deliverySummary
            faultedGroups += ", " + str(group_id)
        else:
            comment = str(deliverer) + " delivered this group (on behalf of " + str(delGroup['creator'])+ ") to the drop, as part of a delivery of all Auto Created groups("+str(group_id)+")"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        DeliveryGroupComment.objects.create(deliveryGroup=DeliveryGroup.objects.get(id=group_id), comment=comment,
                                            date=now)
    else:
        return "ERROR: No auto created delivery group with id "+str(group_id)+ " found in Queued area for drop " + drop, 1
    if faultedGroups != "":
        return "ERROR: Delivery group with id "+str(group_id)+" have failed to deliver.", 1
    result = "SUCCESS: Auto created group delivered(" + str(group_id) + ")"
    return result, 0

def deliverAutoCreatedGroups(product, drop, user):
    '''
    This function delivers all Auto Created groups which are currently queued in a drop
    '''
    redirect = "/"+product+"/queue/"+drop+"/None/multiDelivery/"
    if not Product.objects.filter(name = product).exists():
        return "ERROR: The product "+product+" was not found in the Database", redirect
    if not Drop.objects.filter(name = drop, release__product__name = product).exists():
        return "ERROR: Drop "+drop+" does not exist for the product "+product, redirect
    if DeliveryGroup.objects.filter(deleted = 0, obsoleted = 0, delivered = 0, autoCreated = 1).exists():
        requiredValues = ('id', 'creator')
        delGroups = DeliveryGroup.objects.only(requiredValues).values(*requiredValues).filter(deleted=0, obsoleted=0, delivered=0, autoCreated=1)
    else:
        return "ERROR: No auto created delivery groups found in Queued area for drop "+drop, redirect
    faultedGroups = ""
    deliverer = str(user.first_name) + " " + str(user.last_name)
    groupIds = ', '.join([str(group['id']) for group in delGroups])
    for group in delGroups:
        delivery_thread = DGThread(performGroupDeliveries, args=(product, drop, group['id'], user))
        delivery_thread.start()
        delivery_thread.join()
        deliveryFault, deliverySummary, fullList = delivery_thread.get_result()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if deliveryFault:
            comment = deliverer + " could not deliver this group (on behalf of " + str(group['creator'])+ ") to the drop, as part of a delivery of all Auto Created groups("+groupIds+")" + + " due to " + deliverySummary
            faultedGroups += ", " + str(group['id'])
        else:
            comment = deliverer + " delivered this group (on behalf of " + str(group['creator'])+ ") to the drop, as part of a delivery of all Auto Created groups("+groupIds+")"
        DeliveryGroupComment.objects.create(deliveryGroup=DeliveryGroup.objects.get(id=group['id']), comment=comment, date=now)
    if len(faultedGroups):
        return "ERROR: Some or all groups have failed to deliver. Attempted to deliver " + groupIds + " but these Groups have failed to deliver "+faultedGroups, redirect
    result = "SUCCESS: All groups delivered("+groupIds+")"
    redirect = "/"+product+"/queue/"+drop+"/None/multiDelivery/?section=delivered"
    return result, redirect

def getDropsDesignBaseLatestPSVersion(drop,dropObj,product,productSetVersion):
    '''
    The getDropsDesignBase function takes in two parameters (drop and product) and returns a drops design bases latest Product Set Version if found.
    '''
    try:
        if dropObj:
            dropid = dropObj['id']
            designBaseId = dropObj['designbase__id']

        requiredBaseDropPSVersionFields = ('id','version','drop__name')
        baseDropPSVersionFields = ProductSetVersion.objects.only(requiredBaseDropPSVersionFields).values(*requiredBaseDropPSVersionFields).filter(drop__id=dropObj['id']).order_by('id')
        if baseDropPSVersionFields:
            for index in range(len(baseDropPSVersionFields)):
                baseDropPSVersion = baseDropPSVersionFields[index]
                if baseDropPSVersion['version'] and baseDropPSVersion['version'] == productSetVersion:
                    if index == 0:
                        if designBaseId:
                            requiredBaseDropFields = ('id',)
                            baseDrop = Drop.objects.only(requiredBaseDropFields).values(*requiredBaseDropFields).get(id=designBaseId)
                            if not baseDrop:
                                return "Info: No design base found for drop" + str(drop) + ".\n"
                            baseDropPSVersionFields = ProductSetVersion.objects.only(requiredBaseDropPSVersionFields).values(*requiredBaseDropPSVersionFields).filter(drop__id=baseDrop['id']).order_by('-id')
                            if baseDropPSVersionFields:
                                baseDropPSVersion = baseDropPSVersionFields[0]
                                if baseDropPSVersion['version'] and baseDropPSVersion['version']:
                                    return baseDropPSVersion
                    else:
                        return baseDropPSVersionFields[index-1]
        return "Info: No design base found for drop" + str(drop) + " or no Product Set Version found in design Base, please try again.\n"
    except Exception as e:
        logger.error("Error: Unable to find design base drop Product Set version." + str(e))
        return "Info: Unable to find design base drop Product Set version.\n"

def returnPSVersionArtifactDelta(product, drop, productSetVersion, previousPSVer=None, previousDrop=None, followDrop=None):
    '''
    The returnPSVersionArtifactDelta function builds up a ProductSet Version Artifact Delta with Previous ProductSet Version in a Drop based on local DB entries which is passed
    to the buildPSVersionArtifcatDeltaJSON function which in turn returns a JSON object based on this list
    '''
    prodSetVersionList = []
    currentPsContentsList = []
    previousPsContentsList = []
    baseDropPSVersion = {}
    deltaDict = {}
    localPSVersion = previousPSVer
    try:
        requiredDropFields = ('id','designbase__id','name')
        dropObj = Drop.objects.only(requiredDropFields).values(*requiredDropFields).get(name=drop,release__product__name=product)
        if followDrop != None:
            baseDropPSVersion = getDropsDesignBaseLatestPSVersion(drop, dropObj, product, productSetVersion)
            if "Info:" in str(baseDropPSVersion):
                return str(baseDropPSVersion), deltaDict, localPSVersion, previousDrop
    except Drop.DoesNotExist:
        return "Error: Drop: " + str(drop) + " does not exist in product: " + str(product) + ", please try again\n", deltaDict, localPSVersion, previousDrop

    if previousPSVer == None:
       try:
          requiredDropPSFields = ('id','version')
          dropPSObjList = ProductSetVersion.objects.filter(drop__id=dropObj['id']).order_by('id').only(requiredDropPSFields).values(*requiredDropPSFields)
          for dropPSObj in dropPSObjList:
              if dropPSObj['version'] != productSetVersion:
                 prodSetVersionList.append(dropPSObj['version'])
              else:
                 break
       except Exception as e:
          logger.error("Error: No Product Set Version found for drop: " + str(drop) + str(e))
          return "Error: No Product Set Version found for drop: " + str(drop) + ", please try again\n", deltaDict, localPSVersion, previousDrop
    if prodSetVersionList:
        localPSVersion = prodSetVersionList[-1]
        localDrop = drop
    elif previousPSVer != None:
        localPSVersion = previousPSVer
        if previousDrop != None:
            localDrop = previousDrop
        else:
            localDrop = drop
    elif baseDropPSVersion and baseDropPSVersion['id']:
        localPSVersion = baseDropPSVersion['version']
        localDrop = baseDropPSVersion['drop__name']
        previousPSObj = baseDropPSVersion
    else:
        return "Info: Product Set Version: " + str(productSetVersion) + " is the first Product Set Version in this drop: " + str(drop) + ", please try again\n", deltaDict, localPSVersion, previousDrop

    if baseDropPSVersion and baseDropPSVersion['id'] and not prodSetVersionList and not previousPSVer:
        previousPSObj = baseDropPSVersion
    else:
        try:
            requiredPreviousPSValues = ('id','version')
            previousPSObj = ProductSetVersion.objects.only(requiredPreviousPSValues).values(*requiredPreviousPSValues).get(version=localPSVersion,drop__name=localDrop, drop__release__product__name=product)
        except ProductSetVersion.DoesNotExist:
            return "Error: Product Set Version: " + str(localPSVersion) + " was not found, please try again\n", deltaDict, localPSVersion, previousDrop

    try:
        requiredCurrentPSValues = ('id','version','productSetRelease__productSet__name')
        currentPSObj = ProductSetVersion.objects.only(requiredCurrentPSValues).values(*requiredCurrentPSValues).get(version=productSetVersion,drop__name=drop,drop__release__product__name=product)
    except ProductSetVersion.DoesNotExist:
        return "Error: Product Set Version: " + str(productSetVersion)  + " was not found, please try again\n", deltaDict, localPSVersion, previousDrop

    try:
        requiredCurrentPSMappingValues = ('mediaArtifactVersion__id','mediaArtifactVersion__mediaArtifact__name','mediaArtifactVersion__groupId','mediaArtifactVersion__artifactId','mediaArtifactVersion__version','mediaArtifactVersion__drop__name','mediaArtifactVersion__drop__release__product__name')
        currentPsContentsList = ProductSetVersionContent.objects.filter(productSetVersion__id=currentPSObj['id']).only(requiredCurrentPSMappingValues).values(*requiredCurrentPSMappingValues)
        if len(currentPsContentsList) == 0 :
            return "Error: The Product Set "+ str(currentPSObj['artifactId']) +"::"+str(currentPSObj['version'])+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+str(product)+"\n", deltaDict, localPSVersion, previousDrop
    except Exception as e:
        logger.error("There is no artifact mapped to the Current Product Set Version: " + str(currentPSObj['version']) + str(e))
        return "Error: The Product Set "+ str(currentPSObj['artifactId']) +"::"+str(currentPSObj['version'])+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+str(product)+"\n", deltaDict, localPSVersion, previousDrop

    try:
        requiredPreviousPSMappingValues = ('mediaArtifactVersion__id','mediaArtifactVersion__mediaArtifact__name','mediaArtifactVersion__groupId','mediaArtifactVersion__artifactId','mediaArtifactVersion__version','mediaArtifactVersion__drop__name','mediaArtifactVersion__drop__release__product__name')
        previousPsContentsList = ProductSetVersionContent.objects.filter(productSetVersion__id=previousPSObj['id']).only(requiredPreviousPSMappingValues).values(*requiredPreviousPSMappingValues)
        if len(previousPsContentsList) == 0 :
            return "Error: The Product Set "+ str(previousPSObj['artifactId']) +"::"+str(previousPSObj['version'])+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+str(product)+"\n", deltaDict, localPSVersion, previousDrop
    except Exception as e:
        logger.error("There is no artifact mapped to the Current Product Set Version: " + str(previousPSObj['version']) + str(e))
        return "Error: The Product Set "+ str(previousPSObj['artifactId']) +"::"+str(previousPSObj['version'])+" does not contain any packages, it may not be possible to perform a diff on the media artifacts of "+str(product)+"\n", deltaDict, localPSVersion, previousDrop

    previousDropObj=Drop.objects.only(requiredDropFields).values(*requiredDropFields).get(name=localDrop,release__product__name=product)

    response, deltaDict = buildPSVersionArtifcatDeltaJSON(product, dropObj, previousDropObj, previousPsContentsList, currentPsContentsList, currentPSObj['version'], previousPSObj['version'])

    return response, deltaDict, localPSVersion, previousDropObj['name']

def buildPSVersionArtifcatDeltaJSON(product, dropObj, previousDropObj, previousPsContentsList, currentPsContentsList, currentPSVersion, previousPSVersion):
    '''
    The buildPSVersionArtifcatDeltaJSON function builds up an Product Set Version Artifact Delta with Previous Product Set Version in a Drop, or between drops, and returns this delta in a JSON Object
    '''
    obsoletedDict = {}
    obsoletedString = ""
    updatedDict = {}
    updatedString = ""
    addedDict = {}
    addedString = ""
    finalString = ""
    updatedList = []
    addedList = []
    deltaDict = {}

    try:
        finalString = '"previousVersion" : "' + str(previousPSVersion) + '","version" : "' + str(currentPSVersion) + '",'
        prevPSDeltaList = [prevPSContent for prevPSContent in previousPsContentsList if prevPSContent not in currentPsContentsList]
        for delta in prevPSDeltaList:
            if str(delta['mediaArtifactVersion__mediaArtifact__name']) not in str(list(currentPsContentsList)):
                obsoletedDict["groupId"] = str(delta['mediaArtifactVersion__groupId'])
                obsoletedDict["artifactId"] = str(delta['mediaArtifactVersion__artifactId'])
                obsoletedDict["version"] = str(delta['mediaArtifactVersion__version'])
                obsoletedDict["drop"] = str(delta['mediaArtifactVersion__drop__name'])
                obsoletedDict["product"] = str(delta['mediaArtifactVersion__drop__release__product__name'])
                obsoletedString = obsoletedString + str(obsoletedDict) + ","

        currDeltaList = [currentPSContent for currentPSContent in currentPsContentsList if currentPSContent not in previousPsContentsList]
        for delta in currDeltaList:
            if str(delta['mediaArtifactVersion__mediaArtifact__name']) not in str(list(previousPsContentsList)):
                addedDict["groupId"] = str(delta['mediaArtifactVersion__groupId'])
                addedDict["artifactId"] = str(delta['mediaArtifactVersion__artifactId'])
                addedDict["version"] = str(delta['mediaArtifactVersion__version'])
                addedString = addedString + str(addedDict) + ","
                addedList.append(delta['mediaArtifactVersion__id'])
            else:
                updatedDict["groupId"] = str(delta['mediaArtifactVersion__groupId'])
                updatedDict["artifactId"] = str(delta['mediaArtifactVersion__artifactId'])
                updatedDict["version"] = str(delta['mediaArtifactVersion__version'])
                updatedDict["drop"] = str(delta['mediaArtifactVersion__drop__name'])
                updatedDict["product"] = str(delta['mediaArtifactVersion__drop__release__product__name'])
                for previousPSContent in previousPsContentsList:
                    if str(previousPSContent['mediaArtifactVersion__mediaArtifact__name']) == str(delta['mediaArtifactVersion__mediaArtifact__name']):
                        updatedDict["previousVersion"] = str(previousPSContent['mediaArtifactVersion__version'])
                        updatedDict["previousDrop"] = str(previousPSContent['mediaArtifactVersion__drop__name'])
                updatedString = updatedString + str(updatedDict) + ","
                updatedList.append(delta['mediaArtifactVersion__id'])

        if obsoletedString:
            obsoletedString = obsoletedString[:-1]
            obsoletedString = '"Obsoleted":[' + obsoletedString + '],'
        if updatedString:
            updatedString = updatedString[:-1]
            updatedString = '"Updated":[' + updatedString + '],'
        if addedString:
            addedString = addedString[:-1]
            addedString = '"Added":[' + addedString + '],'

        if not obsoletedString and not updatedString and not addedString:
            return "Info: There is no Difference between Previous Product Set Version: " + str(previousPSVersion) + " and this Product Set Version: " + str(currentPSVersion) + " on Current Product Set GAV: " + str(finalString) + " please try again\n", deltaDict

        deltaDict['new'] = addedList
        deltaDict['updated'] = updatedList

        finalString = finalString + obsoletedString + updatedString + addedString
        if finalString:
            finalString = "[{" + finalString[:-1] + "}]"
            finalString = finalString.replace("'", "\"")
    except Exception as error:
        errorMsg = "Error: There was an issue building Product Set Version Artifact Delta JSON: " + str(error)
        logger.error(errorMsg)
        return errorMsg, deltaDict

    return finalString, deltaDict

def getPreviousDrop(product, version):
    '''
    This function returns the previous drop version
    '''
    dropObj = Drop.objects.only('id').values('id').get(name=version, release__product=product)
    previousDrop = Drop.objects.filter(release__product=product, id__lt=dropObj['id']).order_by('-id')[0]
    return previousDrop

def sendMediaContentIssueEmail(errorMessage, MediaArtifact, version, product):
    '''
    Send email for when there is issue adding the Media Content after Media Artifact version build.
    '''
    recipients = []

    portalEmail = config.get("CIFWK", "fromEmail")
    mailHeader = "There was Issue Adding Content Data for Media Artifact: " + str(MediaArtifact) + ", Version: " +str(version)
    mailContent = '''This is an automated mail from the CI Framework
    \nDear User,\n\nThere was issue adding the content data for Media Artifact: ''' + str(MediaArtifact) + ''', Version: ''' + str(version) + ''' into the CI Portal Database.
    \nError Message:\t\t''' + errorMessage  + '''
    \nPlease investigate this issue.\t\t'''

    if developmentServer == 1:
        recipients = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", str(product).upper()))
    else:
        cifwkDistributionList = config.get("CIFWK", "cifwkDistributionList")
        recipients.append(cifwkDistributionList)
        productEmail = ProductEmail.objects.filter(product__name=product)
        if productEmail != None:
            for delEmail in productEmail:
                recipients.append(delEmail.email)
    send_mail(mailHeader, mailContent, portalEmail, recipients, fail_silently=False)

def getLatestGoodProductSetVersion(productSetName, dropName, confidenceLevel, search=None):
    '''
    Getting latest Good Product Set Version. optional get by confidenceLevel
    '''
    lastPassed = None
    allVersions = []

    try:
        productSetRelObj = ProductSetRelease.objects.only('id', 'release__product').values('id','release__product').filter(productSet__name=productSetName)[0]
        if dropName is not None:
            dropObj = Drop.objects.only('release', 'id').values('release', 'id').get(name=dropName, release__product=productSetRelObj['release__product'])
            allVersions = ProductSetVersion.objects.filter(drop_id=dropObj['id'],productSetRelease__release=dropObj['release']).order_by('-id')
        else:
            search = True
            dropList = Drop.objects.only('release', 'id').values('release', 'id').filter(release__product=productSetRelObj['release__product'], correctionalDrop=False).exclude(release__name__icontains="test").order_by('-id')
            for dropObj in dropList:
                allVersions = ProductSetVersion.objects.filter(drop_id=dropObj['id'], productSetRelease__productSet__name=productSetName).order_by('-id')
                if allVersions:
                    break
        for item in allVersions:
            if item.getOverallWeigthedStatus() == 'passed' or item.status.state == 'passed_manual':
                if item.status.state != 'caution':
                    if confidenceLevel:
                        currentStatusObj = ast.literal_eval(item.current_status)
                        for cdbtype,status in currentStatusObj.items():
                            cdbTypeObj = CDBTypes.objects.get(id=cdbtype)
                            if confidenceLevel == str(cdbTypeObj.name):
                                if status.count('#') == 4:
                                    state,start,end,testReportNumber,veLog = status.split("#")
                                else:
                                    state,start,end,testReportNumber = status.split("#")
                                if state == "passed":
                                    lastPassed = str(item.version)
                                    return lastPassed
                    else:
                        lastPassed = str(item.version)
                        return lastPassed
        if search is not None and lastPassed is None:
            dropDesignbaseName = allVersions[0].drop.designbase.name
            lastPassed = getLatestGoodProductSetVersion(productSetName, dropDesignbaseName, confidenceLevel, search)
            if lastPassed:
                return lastPassed
    except Exception as e:
        errMsg = "Issue getting Last Good Product Set Version: "+str(e)
        logger.error(errMsg)
        return errMsg
    return lastPassed


def getMapDataForISODeliveryGroups(result, delGrpPkgMaps, isosMappings, isoDelGrpDict, isoList):
    '''
    Creating the Mapping Data for Media Artifact Delivery Groups
    '''
    isTestwareGrp = 'False'
    isoDelGrps = []
    iso = (result['iso__version'],result['iso__mediaArtifact__name'])
    if iso in isoDelGrpDict:
        isoDelGrpList = isoDelGrpDict[iso][1]
    else:
        isoDelGrpList = []
        isoList.append(iso)

    testwareTypes = ""
    for delGrpPkg in delGrpPkgMaps:
        if delGrpPkg['deliveryGroup__id'] == result['deliveryGroup__id']:
            if str(delGrpPkg['packageRevision__category__name']).lower() == 'testware':
                if Package.objects.filter(name=delGrpPkg['packageRevision__package__name'], includedInPriorityTestSuite=True):
                    testwareTypeMappings = TestwareTypeMapping.objects.only('testware_type__type').values('testware_type__type').filter(testware_artifact__name=delGrpPkg['packageRevision__package__name'])
                    testwareTypes = ', '.join([testwareTypeMap['testware_type__type'] for testwareTypeMap in testwareTypeMappings])
                    isTestwareGrp = 'Priority'
                else:
                    isTestwareGrp = 'True'
                    break
    isoDelGrp = (result['deliveryGroup__id'],result['deliveryGroup_status'], isTestwareGrp, testwareTypes)
    isoDelGrpList.append(isoDelGrp)
    isoDelGrpDict[iso] = (isosMappings,isoDelGrpList)
    for iso in isoList:
        isoDelGrpTup = (iso,isoDelGrpDict[iso])
        isoDelGrps.append(isoDelGrpTup)
    return isoDelGrps

def getDropProductwareISODeliveryGroups(productName, dropObj):
    '''
    Getting Productware ISO Delivery Groups
    '''

    jsonFields = ('iso__id','iso__version','iso__mediaArtifact__name','deliveryGroup__id','deliveryGroup_status')
    results = list(IsotoDeliveryGroupMapping.objects.only(jsonFields).filter(iso__drop__id=dropObj['id'],iso__mediaArtifact__testware=0, iso__mediaArtifact__category__name="productware").order_by('-iso__build_date','-modifiedDate').values(*jsonFields))


    isoIds = []
    delGrpIds = []
    isoDelGrps = []
    for res in results:
        isoIds.append(res['iso__id'])
        delGrpIds.append(res['deliveryGroup__id'])

    prodTWmediaMapFields = ('productIsoVersion__id','testwareIsoVersion__mediaArtifact__name','testwareIsoVersion__version')
    prodTWmediaMaps = ProductTestwareMediaMapping.objects.filter(productIsoVersion__id__in=isoIds).only(prodTWmediaMapFields).values(*prodTWmediaMapFields)

    delGrpPkgMapFields = ('deliveryGroup__id','packageRevision__category__name', 'packageRevision__package__name')
    delGrpPkgMaps = DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=delGrpIds).distinct().order_by('-deliveryGroup__modifiedDate').only(delGrpPkgMapFields).values(*delGrpPkgMapFields)

    if results:
        isoDelGrpDict = {}
        isoList = []
        for result in results:
            testwareIsos = []
            for testwareIso in prodTWmediaMaps:
                if result['iso__id'] == testwareIso['productIsoVersion__id']:
                    testwareIsos.append((testwareIso['testwareIsoVersion__mediaArtifact__name'],testwareIso['testwareIsoVersion__version']))

            isoDelGrps = getMapDataForISODeliveryGroups(result, delGrpPkgMaps, testwareIsos, isoDelGrpDict, isoList)
    return isoDelGrps

def getDropTestwareISODeliveryGroups(productName, dropObj):
    '''
    Getting Testware ISO Delivery Groups
    '''

    jsonFields = ('iso__id','iso__version','iso__mediaArtifact__name','deliveryGroup__id','deliveryGroup_status')
    results = list(IsotoDeliveryGroupMapping.objects.only(jsonFields).filter(iso__drop__id=dropObj['id'],iso__mediaArtifact__testware=1).order_by('-iso__build_date','-modifiedDate').values(*jsonFields))


    isoIds = []
    delGrpIds = []
    testIsoDelGrps = []
    for res in results:
        isoIds.append(res['iso__id'])
        delGrpIds.append(res['deliveryGroup__id'])

    prodTWmediaMapFields = ('testwareIsoVersion__id', 'productIsoVersion__id','productIsoVersion__mediaArtifact__name','productIsoVersion__version')
    prodTWmediaMaps = ProductTestwareMediaMapping.objects.filter(testwareIsoVersion__id__in=isoIds).only(prodTWmediaMapFields).values(*prodTWmediaMapFields)

    delGrpPkgMapFields = ('deliveryGroup__id','packageRevision__category__name', 'packageRevision__package__name')
    delGrpPkgMaps = DeliverytoPackageRevMapping.objects.filter(deliveryGroup__id__in=delGrpIds).distinct().order_by('-deliveryGroup__modifiedDate').only(delGrpPkgMapFields).values(*delGrpPkgMapFields)

    if results:
        testIsoDelGrpDict = {}
        isoList = []
        for result in results:
            productwareIsos = []
            for productwareIso in prodTWmediaMaps:
                if result['iso__id'] == productwareIso['testwareIsoVersion__id']:
                    productwareIsos.append((productwareIso['productIsoVersion__mediaArtifact__name'],productwareIso['productIsoVersion__version']))
            testIsoDelGrps = getMapDataForISODeliveryGroups(result, delGrpPkgMaps, productwareIsos, testIsoDelGrpDict, isoList)
    return testIsoDelGrps

def getLatestPassedKGBdataForArtifact(artifactName):
    '''
    Getting Latest Passed KGB data for given Artifact
    '''
    try:
        kgbTestResult= {}
        testResultDict = {}
        testwareItems = []
        pkgObj = pkgRev = None
        try:
            pkgObj = Package.objects.only('id').values('id').get(name=artifactName)
        except Exception as e:
            errMsg = "Issue getting Latest KGB Information: " + str(e)
            logger.error(errMsg)
            return errMsg, 404
        testwareObjs = TestwarePackageMapping.objects.only('testware_artifact__name').values('testware_artifact__name').filter(package__id=pkgObj['id'])
        for testware in testwareObjs:
            testwareItems.append(testware['testware_artifact__name'])
        try:
            dataFields = ('id', 'version','m2type', 'groupId', 'category__name', 'platform', 'package__package_number', 'autodrop', 'team_running_kgb__element', 'team_running_kgb__parent__element', 'kgb_snapshot_report', 'kgb_test', 'arm_repo')
            pkgRev = PackageRevision.objects.only(dataFields).values(*dataFields).filter(package__id=pkgObj['id'], kgb_test="passed").order_by('-id')[0]
        except Exception as e:
            errMsg = "Issue getting Latest KGB Information - No Passed KGB Found"
            return errMsg, 404
        productName, dropName = str(pkgRev['autodrop']).split(':')
        nexusUrl = getNexusUrlForProduct(productName)
        artifactNexusUrl = str(nexusUrl + "/"+ pkgRev['arm_repo'] +"/" + str(pkgRev['groupId']).replace(".", "/") + "/" + str(artifactName) + "/" + pkgRev['version'] + "/" + str(artifactName) + "-" + pkgRev['version'] + "." + pkgRev['m2type'])
        rstate = convertVersionToRState(pkgRev['version'])
        testResultDict = { "artifact" : str(artifactName),
                           "number" : str(pkgRev['package__package_number']),
                           "version" : str(pkgRev['version']),
                           "rState": str(rstate),
                           "m2Type" : str(pkgRev['m2type']),
                           "groupId" : str(pkgRev['groupId']),
                           "mediaCategory" : str(pkgRev['category__name']),
                           "platform" : str(pkgRev['platform']),
                           "intendedDrop": str(pkgRev['autodrop']),
                           "snapshotReport": str(pkgRev['kgb_snapshot_report']),
                           "testResult": str(pkgRev['kgb_test']),
                           "nexusURL": artifactNexusUrl,
                           "testware": testwareItems
                         }
        try:
            deliveryInfo = DropPackageMapping.objects.only('drop__name').values('drop__name').filter(package_revision__id=pkgRev['id']).order_by('-id')[0]
            testResultDict['deliveryDrop'] = deliveryInfo['drop__name']
        except Exception as e:
            testResultDict['deliveryDrop'] = None
            logger.debug("No Delivery Information Found")
        if pkgRev['team_running_kgb__element'] != None:
            testResultDict['team'] = pkgRev['team_running_kgb__parent__element'] + " - " + pkgRev['team_running_kgb__element']
        else:
            testResultDict['team'] = None
        try:
            dataTestFields = ('testware_run__test_report_directory', 'testware_run__testdate')
            testResult = TestResultsToTestwareMap.objects.only(dataTestFields).values(*dataTestFields).filter(package_revision__id=pkgRev['id']).order_by('-id')[0]
            testResultDict['testReportDate'] = testResult['testware_run__testdate']
            testResultDict['testReport'] = testResult['testware_run__test_report_directory']
        except Exception as e:
            testResultDict['kgbTestReportDate'] = None
            testResultDict['KgbTestReport'] = None
            logger.debug("Test Report Not Found")
        kgbTestResult['artifactKGBdata'] = testResultDict
        return kgbTestResult, 200
    except Exception as e:
        errMsg = "Issue getting Latest KGB Information: "+ str(e)
        logger.error(errMsg)
        return errMsg, 404

def getArtifactSize(packageName, version, groupId, m2type, repository):
    '''
    Getting Size of Artifact from Nexus
    '''
    nexusUrl = config.get('CIFWK', 'nexus_REST_API_enm_url')
    nexusUrl += str(groupId.replace(".", "/") +
            "/" + packageName +
            "/" + version +
            "/" + packageName + "-" + version + "." + m2type + "?describe=info")
    try:
        artifact_metadata = urllib2.urlopen(nexusUrl).read()
        artifact_presentLocally = ((artifact_metadata.split('<presentLocally>'))[1].split('</presentLocally>')[0])
        if artifact_presentLocally == "true":
            artifact_size = ((artifact_metadata.split('<size>'))[1].split('</size>')[0])
            return artifact_size, 200
        else:
            errMsg = "Issue getting Size of the artifact: " + str(nexusUrl)
            logger.error(errMsg)
            return errMsg, 404
    except Exception as e:
        errMsg = "Issue getting Size of the artifact" + str(e)
        logger.error(errMsg)
        return errMsg, 404

    errMsg = "Issue getting Size of the artifact: " + str(nexusUrl)
    logger.error(errMsg)
    return errMsg, 404

def getMediaArtifactSize(artifact, version, group, mediaType, testware=None, mediaCategory=None):
    '''
    Getting Media Size from Nexus
    '''

    if testware or mediaCategory=="translatabledata" :
        nexusUrl = config.get('CIFWK', 'nexus_REST_API_enm_url')
    else:
        nexusUrl = config.get('CIFWK', 'nexus_REST_API_enm_media_url')
    nexusUrl += str(group.replace(".", "/") +
            "/" + artifact +
            "/" + version +
            "/" + artifact + "-" + version + "." + mediaType + "?describe=info")
    try:
        artifact_metadata = urllib2.urlopen(nexusUrl).read()
        artifact_presentLocally = ((artifact_metadata.split('<presentLocally>'))[1].split('</presentLocally>')[0])
        if artifact_presentLocally == "true":
            artifact_size = ((artifact_metadata.split('<size>'))[1].split('</size>')[0])
            return artifact_size, 200
        else:
            errMsg = "Issue getting Size of the artifact: " + str(nexusUrl)
            logger.error(errMsg)
            return errMsg, 404
    except Exception as e:
        errMsg = "Issue getting Size of the artifact: " + str(nexusUrl)
        logger.error(errMsg)
        return errMsg, 404

    errMsg = "Issue getting Size of the artifact: " + str(nexusUrl)
    logger.error(errMsg)
    return errMsg, 404

def getMediaArtifactProductToTestwareMapping(artifact, version):
    '''
    Get Productware Media's Testware Media Mapping
    '''
    mediaData = {}
    testwareMediaList = []
    try:
        fields = ('testwareIsoVersion__artifactId', 'testwareIsoVersion__version')
        mappings = ProductTestwareMediaMapping.objects.only(fields).values(*fields).filter(productIsoVersion__artifactId=artifact, productIsoVersion__version=version)
        for map in mappings:
            testwareMediaList.append(map['testwareIsoVersion__version'])
        mediaData['testwareMediaArtifact'] = mappings[0]['testwareIsoVersion__artifactId']
        mediaData['testwareMediaArtifactVersions'] = testwareMediaList
        mediaData['productwareMediaArtifact'] = artifact
        mediaData['productwareMediaArtifactVersion'] = version
    except Exception as e:
        errMsg = "Issue getting Testware Media Artifact versions for Productware Media Artifact: " + str(artifact) + "-"+str(version) + " error: " + str(e)
        logger.error(errMsg)
        return errMsg, 404
    return mediaData, 200

def getProductwaretoTestwareMappingByDrop(artifact, product, drop):
    '''
    Get Testware Media Mappings by Drop for Productware Media Artifact
    '''
    mediaDropMappingData = {}
    mediaMappingData = []
    product = str(product).upper()
    try:
        mediaVersionList = ISObuild.objects.only('version').values('version').filter(artifactId=artifact, drop__name=drop, drop__release__product__name=product).order_by('-id')
        if not mediaVersionList:
            errMsg = "Issue getting Testware Media Artifact versions for Productware Media Artifact: " + str(artifact) + " and Drop: " +str(drop) + ", please check your input."
            logger.error(errMsg)
            return errMsg, 404
        for mediaVersion in mediaVersionList:
            mediaData, statusCode = getMediaArtifactProductToTestwareMapping(artifact, mediaVersion['version'])
            if statusCode != 200:
                logger.error(mediaData)
                return mediaData, 404
            mediaMappingData.append(mediaData)
        mediaDropMappingData['mediaArtifactMappingData'] = mediaMappingData
    except Exception as e:
        errMsg = "Issue getting Testware Media Artifact versions for Productware Media Artifact: " + str(artifact) + " and Drop: " +str(drop) + " error: " + str(e)
        logger.error(errMsg)
        return errMsg, 404
    return mediaDropMappingData, 200

def setMediaArtifactVerInactiveByDrop(product, drop):
    '''
    Setting Media Artifacts Inactive by Drop
    '''
    fields = ('artifactId', 'version')
    statusCode = 404
    product = str(product).upper()
    mediaArtifacts = ISObuild.objects.only(fields).values(*fields).filter(drop__release__product__name=product, drop__name=drop, active=1)
    try:
        for mediaArtVer in mediaArtifacts:
            message, statusCode = setMediaArtifactVerInactive(mediaArtVer['artifactId'], mediaArtVer['version'])
            if statusCode != 200:
                return message, statusCode
    except Exception as e:
        message = "Issue updating Media artifacts for " + str(product) + "-" + str(drop) + ", " + str(e)
        logger.error(message)
        return message, statusCode
    return "SUCCESS", statusCode


@transaction.atomic
def setMediaArtifactVerInactive(artifact, version):
    '''
    This will set the active Media Artifact to Inactive if finds not in Nexus
    '''
    message = ""
    statusCode = 404
    try:
        with transaction.atomic():
            mediaArtifactObj = ISObuild.objects.get(artifactId=artifact, version=version)
            message = "No update for Media Artifact " + str(artifact) + "-" + str(version)
            if mediaArtifactObj.active == True:
                activeStatus, statusCode = checkMediaArtifactVerInNexus(artifact, version, mediaArtifactObj.groupId, mediaArtifactObj.mediaArtifact.mediaType, mediaArtifactObj.mediaArtifact.testware)
                mediaArtifactObj.active = activeStatus
                mediaArtifactObj.save()
                if mediaArtifactObj.active != True:
                    message = "Updated Media Artifact "+ str(artifact) + "-" + str(version) + " to Inactive."
            logger.info(message)
    except Exception as e:
        message = "Issue updating Media artifact " + str(artifact) + "-" + str(version) + ", " + str(e)
        logger.error(message)
        return message, statusCode
    return message, statusCode


def checkMediaArtifactVerInNexus(artifact, version, group, mediaType, testware=None):
    '''
    This see if the Media Artifact version is still in Nexus
    '''

    nexusUrl = config.get('CIFWK', 'nexus_REST_API_enm_url')
    nexusUrl += str(group.replace(".", "/") +
            "/" + artifact +
            "/" + version +
            "/" + artifact + "-" + version + "." + mediaType)
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    try:
        returnCode = requests.head(nexusUrl, verify=ssl_certs)
        if returnCode.status_code != 200:
            logger.error("Warning: Issue using url: " + str(nexusUrl) + ", status code: " + str(returnCode.status_code) + "\n")
            return False, 200
        logger.info("Successful, artifact: " + str(artifact) + "-" + str(version) + " is in Nexus.\n")
    except Exception as e:
        logger.error("Warning: Issue using url: " + str(nexusUrl) +", " + str(e) + ".\n")
        return False, 404
    return True, 200


def checkNexus():
    '''
    Checking that Nexus is Okay
    '''

    nexusUrl = config.get('CIFWK', 'nexus_REST_API_enm_url')
    try:
        returnCode = requests.head(nexusUrl)
        if returnCode.status_code != 200:
            logger.error("Warning: Issue using url: " + str(nexusUrl) + ", status code: " + str(returnCode.status_code) + "\n")
        return returnCode.status_code
    except Exception as e:
        logger.error("Warning: Issue using url: " + str(nexusUrl) +", " + str(e) + ".\n")
    return 404


def getAthloneProxyProductsUrl(productName, isoArmRepo, isoGroupId, athloneProxyProducts):
    '''
    Getting the Athlone Proxy url for allowed products
    '''
    nexusLocalUrl = ""
    if str(productName) in athloneProxyProducts:
        if ( productName != "TOR" and productName != "ENM" ):
            if isoArmRepo == "releases":
                isoArmRepo = "enm_" + isoArmRepo
            nexusLocalUrl = str(config.get('CIFWK', 'AthloneEiffelProxy_nexus_url') + "/" + isoArmRepo + "/" + isoGroupId.replace(".", "/"))
        else:
            nexusLocalUrl = str(config.get('DMT_AUTODEPLOY', 'ENM_nexus_url') + "/" + isoGroupId.replace(".", "/"))
    return nexusLocalUrl


def setExternallyReleasedMediaArtifactVersion(productName, dropName, mediaArtifact, version):
    '''
    Setting the Externally Released Version for Media Artifact
    '''
    try:
        firstExternallyReleased = True
        rstate = baseRstate = ipNumber = None
        drop = Drop.objects.only('id').values('id').get(name=str(dropName), release__product__name=str(productName))
        mediaArtifactVersion = ISObuild.objects.get(drop__id=drop['id'], artifactId=mediaArtifact, version=version)
        mediaArtifactVersion.externally_released=True
        #Getting First Externally Released Version
        if ISObuild.objects.filter(drop__id=drop['id'], artifactId=mediaArtifact, externally_released=True, externally_released_ip=False).exists():
            mediaArtifactVerER = ISObuild.objects.only('version').values('version').get(drop__id=drop['id'], artifactId=mediaArtifact, externally_released=True, externally_released_ip=False)
            versionCheck = compareVersions(mediaArtifactVersion.version, mediaArtifactVerER['version'])
            if versionCheck == 2:
                mediaArtifactVersion.externally_released_ip=True
            else:
                msg = "Media Artifact Version " + str(mediaArtifactVerER['version']) + " is the lowest version set with externally released flag for this drop"
                return msg, 404
            firstExternallyReleased = False
        #Creating Externally Released RState
        shortVersion = str(mediaArtifactVersion.version).rsplit(".", 1)[0]
        baseRstate = str(convertVersionToRState(shortVersion))
        if firstExternallyReleased:
            rstate = baseRstate
        else:
            ipNumber = 1
            lastERip = ISObuild.objects.only('externally_released_rstate').values('externally_released_rstate').filter(drop__id=drop['id'], artifactId=mediaArtifact, externally_released=True, externally_released_ip=True).order_by('-id')
            if lastERip:
                ipNumber = int(str(lastERip[0]['externally_released_rstate']).rsplit("/", 1)[1]) + 1
            rstate = str(baseRstate) + "/" + str(ipNumber)
        mediaArtifactVersion.externally_released_rstate=str(rstate)
        mediaArtifactVersion.save()
        msg = "Successfully updated, externally released Media Artifact RState " + str(rstate)
    except Exception as e:
        msg = "Issue setting the externally released Media Artifact Version, " + str(e)
        logger.error(msg)
        return msg, 404
    return msg, 200


def getExternallyReleasedMediaArtifactVersion(productName, dropName):
    '''
    Getting the Externally Released Version for Media Artifact
    '''

    try:
        statusCode = 200
        mediaData = {}
        mediaVersionData = {}
        mediaVersionDataList = []
        mediaArtifactVersions = []
        drop = Drop.objects.only('id').values('id').get(name=str(dropName), release__product__name=str(productName))
        valuesList = 'artifactId', 'version', 'externally_released', 'externally_released_ip', 'externally_released_rstate'
        mediaArtifactVersions = ISObuild.objects.only(valuesList).values(*valuesList).filter(drop__id=drop['id'], externally_released=True).order_by('-id')
        if mediaArtifactVersions:
            for mediaArtifactVersion in mediaArtifactVersions:
                mediaVersionData = {"media_artifact":  str(mediaArtifactVersion['artifactId']),
                                     "version" : str(mediaArtifactVersion['version']),
                                     "externally_released_rstate" : str(mediaArtifactVersion['externally_released_rstate']),
                                     "ip": str(mediaArtifactVersion['externally_released_ip']),
                                   }
                mediaVersionDataList.append(mediaVersionData)
        mediaData['externally_released_data'] = mediaVersionDataList
    except Exception as e:
        errMsg = "Issue getting the Externally Released MediaArtifact Version, " + str(e)
        logger.error(errMsg)
        mediaData = { "error": str(errMsg)}
        statusCode = 404
    return mediaData, statusCode


def getProductSetVersionContentsData(contents):
    '''
    Getting the ProductSet version content data
    '''

    athloneProxyProducts = ast.literal_eval(config.get("CIFWK", "athlone_proxy_products"))
    defaultDeployMaps = str(config.get('DMT', 'defaultDeployProductMaps')).split(' ')
    contentsList = []
    deployMaps = None
    deployMapsProducts = []

    try:
        if contents:
            deployMapValues = "mainMediaArtifactVersion__drop__release__product__name", "mediaArtifactVersion__drop__release__product__name",
            deployMaps = ProductSetVersionDeployMapping.objects.only(deployMapValues).values(*deployMapValues).filter(productSetVersion__id=contents[0]['productSetVersion__id'])
        if deployMaps:
            deployMapsProducts.append(deployMaps[0]['mainMediaArtifactVersion__drop__release__product__name'])
            for mapping in deployMaps:
                deployMapsProducts.append(mapping['mediaArtifactVersion__drop__release__product__name'])
        for item in contents:
            artifactName = str(item['mediaArtifactVersion__artifactId'])
            artifactNumber = str(item['mediaArtifactVersion__mediaArtifact__number'])
            version = str(item['mediaArtifactVersion__version'])
            armRepo = str(item['mediaArtifactVersion__arm_repo'])
            groupId = str(item['mediaArtifactVersion__groupId'])
            mediaType = str(item['mediaArtifactVersion__mediaArtifact__mediaType'])
            productName = str(item['mediaArtifactVersion__drop__release__product__name'])
            builtFor = str(item['mediaArtifactVersion__drop__name'])
            deliveredTo = str(item['productSetVersion__drop__name'])
            externallyReleased = str(item['mediaArtifactVersion__externally_released'])
            externallyReleasedIp = str(item['mediaArtifactVersion__externally_released_ip'])
            externallyReleasedRstate = str(item['mediaArtifactVersion__externally_released_rstate'])
            deployType =  str(item['mediaArtifactVersion__mediaArtifact__deployType__type'])
            systemInfo = str(item['mediaArtifactVersion__systemInfo'])
            autoDeploy = False
            if deployMapsProducts:
                if productName in deployMapsProducts:
                    autoDeploy = True
            else:
                if productName in defaultDeployMaps or productName == "ENM":
                    autoDeploy = True

            hubUrl = getNexusUrl(productName, armRepo, groupId, artifactName, version, artifactName, mediaType, False)
            artifactUrl = "/" + artifactName + "/" + version + "/" + artifactName + "-" + version + "." + str(mediaType)
            athloneUrl = getAthloneProxyProductsUrl(productName, armRepo, groupId, athloneProxyProducts)
            if athloneUrl:
                athloneUrl += artifactUrl

            contentsListTmp = [
                    {
                        "artifactName": artifactName,
                        "artifactNumber": artifactNumber,
                        "version": version,
                        "builtFor": builtFor,
                        "deliveredTo": deliveredTo,
                        "hubUrl": hubUrl,
                        "athloneUrl": athloneUrl,
                        "externally_released": externallyReleased,
                        "ip": externallyReleasedIp,
                        "externally_released_rstate": externallyReleasedRstate,
                        "deploy_type": deployType,
                        "auto_deploy" : autoDeploy,
                        "systemInfo": systemInfo
                     }
                            ]
            contentsList = contentsList + contentsListTmp

    except Exception as e:
        logger.error("Issue getting Product Set Versions Contents: "+str(e))
        contentsList = "error"

    return contentsList


def getProductSetDropData(productSetName,dropName):
    '''
    Getting the ProductSet Drop data
    '''

    statusCode = 200
    productSetDropDataList = []
    productSetDropDataDict = {}

    try:
        product = ProductSetRelease.objects.only('release__product__id').values('release__product__id').filter(productSet__name=productSetName)[0]
        productSetVersionObjects = ProductSetVersion.objects.only('id','productSetRelease__number','version','current_status').\
            values('id','productSetRelease__number','version','current_status').filter(drop__name=dropName, drop__release__product__id=product['release__product__id']).order_by('-id')
        productSetVersionObjectsIds = []

        for productSetVersionObject in productSetVersionObjects:
            productSetVersionObjectsIds.append(productSetVersionObject['id'])

        valueFields = "mediaArtifactVersion__artifactId", "mediaArtifactVersion__groupId", "mediaArtifactVersion__version", \
                      "mediaArtifactVersion__mediaArtifact__mediaType", "mediaArtifactVersion__drop__name", \
                      "productSetVersion__drop__name", "mediaArtifactVersion__externally_released", \
                      "mediaArtifactVersion__externally_released_ip", "mediaArtifactVersion__externally_released_rstate", \
                      "mediaArtifactVersion__mediaArtifact__number", "mediaArtifactVersion__arm_repo", \
                      "mediaArtifactVersion__drop__release__product__name", "productSetVersion__id", "mediaArtifactVersion__mediaArtifact__deployType__type",
        productSetVersionContents = ProductSetVersionContent.objects.only(valueFields).values(*valueFields).filter(productSetVersion__id__in=productSetVersionObjectsIds)
        cdbTypeObjs = CDBTypes.objects.only('id', 'name', 'sort_order').values('id','name', 'sort_order').all()
        productDropCDBCheck = ProductDropToCDBTypeMap.objects.only('type__name').values('type__name').\
            filter(product__id=product['release__product__id'], drop__name=dropName,enabled=True,overallStatusFailure=True)
        productSetVerToCDBTypes = ProductSetVerToCDBTypeMap.objects.only('productSetVersion__id', 'override', 'runningStatus').\
            values('productSetVersion__id', 'override', 'runningStatus').filter(productSetVersion__id__in=productSetVersionObjectsIds)

        for productSetVersionObject in productSetVersionObjects:

            productSetVersionStatus = "not_started"
            if str(productSetVersionObject['current_status']) != "None" and str(productSetVersionObject['current_status']) != "":
                currentStatusObj = ast.literal_eval(productSetVersionObject['current_status'])  # change string to tuple
                productSetVersionStatus = str(getProductSetVersionOverallWeigthedStatus(currentStatusObj, productSetVersionObject['id'], cdbTypeObjs, productDropCDBCheck, productSetVerToCDBTypes))

            productSetNumber = str(productSetVersionObject['productSetRelease__number'])
            productSetVersion = str(productSetVersionObject['version'])
            productSetVersionId = productSetVersionObject['id']
            contents = []

            for productSetVersionContent in productSetVersionContents:
                if productSetVersionId == productSetVersionContent['productSetVersion__id']:
                    contents.append(productSetVersionContent)

            contentsList = getProductSetVersionContentsData(contents)
            versionContents = {
                    "version": productSetVersion,
                    "number": productSetNumber,
                    "contents": contentsList,
                    "status": productSetVersionStatus
                }

            productSetDropDataList.append(versionContents)

        productSetDropDataDict['productset_drop_data'] = productSetDropDataList
        if not productSetDropDataList:
            statusCode = 404

    except Exception as e:
        logger.error("Issue getting Product Set Drop Data contents:" + str(e))
        productSetDropDataDict['productset_drop_data'] = {
            "status": 'error',
            "version": 'error',
            "number": 'error',
            "contents": 'error',
        }
        statusCode = 404

    return  productSetDropDataDict, statusCode


def getProductSetVersionOverallWeigthedStatus(currentStatusObj, productSetVersionId, cdbTypeObjs, productDropCDBCheck, productSetVerToCDBTypes):
    '''
    Getting the ProductSet Version OverallWeigthedStatus
    '''
    status_list = []
    testNameStatus_list = []

    for cdbType, status in currentStatusObj.items(): # cdbtype= customer baseline types
        status_dict = {}
        for cdbTypeObj in cdbTypeObjs:
            if cdbType == cdbTypeObj['id']:
                state = status.split("#")[0]
                testNameStatus_list.append(cdbTypeObj['name'] + ":" + state)
                status_dict['cdb_type_sort_order'] = cdbTypeObj['sort_order']
                status_dict['status'] = state
                status_list.append(status_dict)

    if testNameStatus_list and productDropCDBCheck:
        configuredStatus = getStatusBasedOnSetConfiguredCDBTypes(productSetVersionId, testNameStatus_list, productDropCDBCheck, productSetVerToCDBTypes)
        if configuredStatus:
            return configuredStatus

    if status_list:
        status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'))
        return status_list[-1]['status']
    else:
        return "not_started"


def getStatusBasedOnSetConfiguredCDBTypes(productSetVersionId, testNameStatus_list, productDropCDBCheck, productSetVerToCDBTypes):
    '''
    The getStatusBasedOnSetConfiguredCDBTypes function returns the overall product set version status based on manual configuration
    '''

    typeState = None
    inProgressBasedOnStatus = False
    inProgress = False

    for productSetVerToCDBType in productSetVerToCDBTypes:
        if productSetVerToCDBType['productSetVersion__id'] == productSetVersionId and productSetVerToCDBType['override']:
            return "passed"
        elif productSetVerToCDBType['productSetVersion__id'] == productSetVersionId and not productSetVerToCDBType['runningStatus']:
            inProgress = True

    for productSetCheck in productDropCDBCheck:
        for item in testNameStatus_list:
            testName, testState = item.split(":")
            if str(productSetCheck['type__name']) == testName and testState == "failed":
                return testState
            elif str(productSetCheck['type__name']) == testName and testState == "in_progress":
                inProgressBasedOnStatus = True
            elif str(productSetCheck['type__name']) == testName and testState == "passed":
                typeState = testState

    if inProgressBasedOnStatus:
        return "in_progress"

    if typeState:
        if typeState == "passed":
            if inProgress:
                return "in_progress"
        return typeState
    else:
        return "not_started"


def getMediaArtifactVersionData(mediaArtifact, version, uselocalNexus="false"):
    '''
    Getting Data about given MediaArtifact Version
    '''
    statusCode = 200
    mediaArtifactVersionData = {}
    athloneProxyProducts = ast.literal_eval(config.get("CIFWK", "athlone_proxy_products"))

    try:
        valuesFields = "id", "drop__release__product__name", "drop__name", "current_status", "arm_repo", "groupId", "mediaArtifact__number", \
                       "mediaArtifact__mediaType", "mediaArtifact__testware", "mediaArtifact__category__name", "build_date", "size", "active", \
                        "externally_released", "externally_released_ip", "externally_released_rstate",
        mediaArtifactVersion = ISObuild.objects.only(valuesFields).values(*valuesFields).get(artifactId=mediaArtifact, version=version)
        product = str(mediaArtifactVersion['drop__release__product__name'])
        drop = str(mediaArtifactVersion['drop__name'])
        armRepo = str(mediaArtifactVersion['arm_repo'])
        groupId = str(mediaArtifactVersion['groupId'])
        mediaType  = str(mediaArtifactVersion['mediaArtifact__mediaType'])
        mediaArtifactVersionData = { "product" : str(product),
                                     "number" : str(mediaArtifactVersion['mediaArtifact__number']),
                                     "media_type" : str(mediaType),
                                     "category" : str(mediaArtifactVersion['mediaArtifact__category__name']),
                                     "testware" : str(mediaArtifactVersion['mediaArtifact__testware']),
                                     "status" : str(getOverallWeigthedStatusMediaArtifact(str(mediaArtifactVersion['current_status']), product, drop)),
                                     "drop" : str(drop),
                                     "build_date" : str(mediaArtifactVersion['build_date']),
                                     "size" : mediaArtifactVersion['size'],
                                     "active" : str(mediaArtifactVersion['active']),
                                     "externally_released" : str(mediaArtifactVersion['externally_released']),
                                     "externally_released_ip" : str(mediaArtifactVersion['externally_released_ip']),
                                     "externally_released_rstate" : str(mediaArtifactVersion['externally_released_rstate']),
                                     "hub_url" : str(getNexusUrl(product, armRepo, groupId, mediaArtifact, version, mediaArtifact, mediaType))
                                   }
        artifactUrl = "/" + mediaArtifact + "/" + version + "/" + mediaArtifact + "-" + version + "." + str(mediaType)
        athloneUrl = getAthloneProxyProductsUrl(product, armRepo, groupId, athloneProxyProducts)
        if athloneUrl:
            athloneUrl += artifactUrl
        mediaArtifactVersionData["athlone_url"] = str(athloneUrl)
        mediaArtifactVersionData['content'] = isoContents(mediaArtifactVersion['id'], product, uselocalNexus)
    except Exception as e:
        errMsg = "Issue getting Media Artifact Version Data: "+str(e)
        logger.error(errMsg)
        statusCode = 404
        mediaArtifactVersionData = { "error" : errMsg}
    return mediaArtifactVersionData, statusCode


def getOverallWeigthedStatusMediaArtifact(currentStatus, productName, dropName):
    '''
    Getting the Overall Weigthed Status of Media Artifact Version
    '''
    status_list = []
    testNameStatus_list = []
    if str(currentStatus) != "None" and str(currentStatus) != "":
        currentStatusObj = ast.literal_eval(currentStatus)
        for cdbtype,status in currentStatusObj.items():
            cdbTypeObj = CDBTypes.objects.only('name','sort_order').values('name', 'sort_order').get(id=cdbtype)
            status_dict = {}
            if status.count('#') == 4:
               state,start,end,testReportNumber,veLog = status.split("#")
            else:
               state,start,end,testReportNumber = status.split("#")
            testNameStatus_list.append(cdbTypeObj['name'] + ":" + state)

            status_dict['cdb_type_sort_order'] = cdbTypeObj['sort_order']
            status_dict['status'] = state
            status_list.append(status_dict)

        productDropCDBFailureCheck = ProductDropToCDBTypeMap.objects.only('type__name').values('type__name').filter(product__name=productName, drop__name=dropName, enabled=True, overallStatusFailure=True)
        if testNameStatus_list and productDropCDBFailureCheck:
            typeState = ""
            for productSetCheck in productDropCDBFailureCheck:
                for item in testNameStatus_list:
                    testName,testState = item.split(":")
                    if str(productSetCheck['type__name']) == testName and testState == "failed":
                        return testState
                    if str(productSetCheck['type__name']) == testName and testState == "in_progress":
                        testState = testState
                    elif str(productSetCheck['type__name']) == testName:
                        typeState = testState
            if testState == "in_progress":
                return testState
            if typeState != "":
                return typeState
    if status_list:
        status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'))
        return status_list[-1]['status']
    return "not_started"


def getLatestProductDropName(product, correctionalDropValue="false"):
    '''
    The getLatestDropName function returns the latest drop name for a given Product
    '''
    statusCode = 200
    latestDrop = {}
    try:
        field = ("name",)
        latestDropName = Drop.objects.only(field).values(*field).filter(release__product__name=product, correctionalDrop=correctionalDropValue).exclude(release__name__icontains="test").latest("id")
        latestDrop = {"drop" : str(latestDropName['name'])}
    except Exception as e:
        errMsg = "Issue getting Drop Name: "+str(e)
        logger.error(errMsg)
        statusCode = 404
        latestDrop = { "error" : errMsg}
    return latestDrop, statusCode

def getDropMediaDeployData(productSetName,productName,dropName):

    '''
    Getting Product Set Drop Data for Products
    '''
    psDropDataDict = {}
    ddDropDataDict = {}
    statusCode = 200
    productsList = []
    dropproductsList = []
    psMediaDropProducts ={}
    content = []
    deployMaps = None
    defaultDeployProductMaps = str(config.get("DMT", "defaultDeployProductMaps")).split(' ')
    try:
        prodSetRel = ProductSetRelease.objects.filter(productSet__name=productSetName).latest("id")
        dropObj = Drop.objects.only("id").values("id").get(name=dropName, release__product=prodSetRel.release.product)
        currentDrop = getMediaBaseline(dropObj['id'])
        for currentMedia in currentDrop:
            if str(productName) == str(currentMedia.mediaArtifactVersion.drop.release.product.name):
                deployMaps = DropMediaDeployMapping.objects.only('product__name').values('product__name').filter(dropMediaArtifactMap=currentMedia)
                break
        for currentMedia in currentDrop:
            info = {}
            mediaProduct = currentMedia.mediaArtifactVersion.drop.release.product.name
            if not str(productName) == str(mediaProduct):
                info['product'] = str(mediaProduct)
                info['mapping'] = False
                if deployMaps:
                    for deployMap in deployMaps:
                        if str(deployMap['product__name']) == str(mediaProduct):
                            info['mapping'] = True
                            break
                else:
                    if mediaProduct in defaultDeployProductMaps:
                        info['mapping'] = True
                content.append(info)
        psMediaDropProducts['ps_media_drop_products'] = content

    except Exception as e:
        errMsg = "Issue getting the Product Set Drop's Products: ERROR " + str(e)
        logger.error(str(errMsg))
        psDropDataDict = errMsg
        statusCode = 404

    return psMediaDropProducts, statusCode


def getActiveDropsInProductSet(productSetName):
    '''
    returns a list of drops for which a user can manipulate the Delivery Queue for a product in Json format
    '''
    timeNow = datetime.now()
    prodSetRel = ProductSetRelease.objects.filter(productSet__name=productSetName).latest("id")
    dropsQuery = Drop.objects.only('name').filter(mediaFreezeDate__gt=timeNow, release__product=prodSetRel.release.product).order_by('name')
    latestFrozenDrops = None
    try:
        latestFrozenDrops = Drop.objects.only('name', 'mediaFreezeDate').filter(release__product=prodSetRel.release.product).order_by('-id')[:3]
    except:
        if Drop.objects.filter(release__product__name=productName).exists():
            latestFrozenDrops = Drop.objects.only('name', 'mediaFreezeDate').filter(release__product=prodSetRel.release.product).order_by('-id')[0]
        latestFrozenDrops = None
    drops =[]
    for drop in dropsQuery:
        drops.insert(0, productSetName +":"+drop.name)
    if not drops:
        frozenDropInfo = "All " + productSetName + " Drops are Frozen. \n"
        if latestFrozenDrops != None:
            if len(latestFrozenDrops) == 3:
                frozenDropInfo = frozenDropInfo  + "The latest 3 Frozen Drops: \n"
            drpInfo = ""
            for drp in latestFrozenDrops:
                drpInfo = drpInfo + str(drp.name) + " was Frozen on: " +  str(drp.mediaFreezeDate) + "\n"
            frozenDropInfo = frozenDropInfo  + drpInfo
        drops.append(frozenDropInfo)
    dropsJson = {"Drops":drops}
    return dropsJson

def getDropMediaDeployMappings(currentContents):
    '''
    Getting Drop Media Artifact Deploy Mappings for Drop
    '''
    dropMediaDeployMappingData = []
    dropMediaDeployMaps = None
    defaultDropMediaDeployMaps = str(config.get('DMT', 'defaultDeployProductMaps')).split(' ')
    try:
        for currentItem in currentContents:
            if str(currentItem.mediaArtifactVersion.drop.release.product.name) == "ENM":
                if DropMediaDeployMapping.objects.filter(dropMediaArtifactMap=currentItem).exists():
                    dropMediaDeployMaps = DropMediaDeployMapping.objects.only('product__name').values('product__name').filter(dropMediaArtifactMap=currentItem)
                    break
        for currentItem in currentContents:
            mediaProductName = currentItem.mediaArtifactVersion.drop.release.product.name
            addMapping = False
            if str(currentItem.mediaArtifactVersion.drop.release.product.name) != "ENM":
                if dropMediaDeployMaps:
                    for dropMediaDeployMap in dropMediaDeployMaps:
                        if str(dropMediaDeployMap['product__name']) == str(mediaProductName):
                            addMapping = True
                            break
                else:
                    if str(mediaProductName) in defaultDropMediaDeployMaps:
                        addMapping = True
            if addMapping:
                mappingDict = {"mediaArtifact": str(currentItem.mediaArtifactVersion.mediaArtifact.name),
                               "version": str(currentItem.mediaArtifactVersion.version),
                               "deployType": str(currentItem.mediaArtifactVersion.mediaArtifact.deployType.type)}
                dropMediaDeployMappingData.append(mappingDict)
    except Exception as e:
        errMsg = "Issue getting Drop Media Artifact Deploy Mappings: "+str(e)
        logger.error(errMsg)
    return dropMediaDeployMappingData

@transaction.atomic
def preprocessMetadata(metadata_content):
    '''
    This function read Metadata file and pre-process it.
    Three types of metadata will be accepted:
        image data, integration chart data and csar data
    '''
    try:
        sid = transaction.savepoint()
        if type(metadata_content[0]) is dict:
            if "image_data" in metadata_content[0].keys():
                result_code, status = processCNServiceGroupData(metadata_content)
                if result_code == 1:
                    transaction.savepoint_rollback(sid)
                    return result_code, status
                return 0, "SUCCESS"
            elif "chart_data" in metadata_content[0].keys():
                intgr_chart_data = metadata_content[0]['chart_data']
                dependent_charts = metadata_content[1]['dependent_charts']
                result_code, status = postIntgrData(intgr_chart_data, dependent_charts)
                if result_code == 1:
                    transaction.savepoint_rollback(sid)
                    return result_code, status
                return 0, "SUCCESS"
            elif "deployment_utility_detail" in metadata_content[0].keys():
                deployment_utility_detail = metadata_content[0]['deployment_utility_detail']
                result_code, status = postDepUtilDetailData(deployment_utility_detail)
                if result_code == 1:
                    transaction.savepoint_rollback(sid)
                    return result_code, status
                return 0, "SUCCESS"
            elif "sync_data" in metadata_content[0].keys():
                sync_data = metadata_content[0]['sync_data']
                intgr_chart_data = metadata_content[1]['integration_charts_data']
                intgr_values_data = metadata_content[2]['integration_values_file']
                result_code, status = postSyncData(sync_data, intgr_values_data)
                if result_code == 1:
                    transaction.savepoint_rollback(sid)
                    return result_code, status
                return 0, "SUCCESS"
            else:
                result_code, status = checkCsarMetaData(metadata_content)
                if result_code == 1:
                    return 1, status
                csarMetaDataDict, result_code, status = extractCsarMetaData(metadata_content)
                if result_code == 1:
                    return 1, status
                result_code, status = postCsarData(csarMetaDataDict)
                if result_code == 1:
                    transaction.savepoint_rollback(sid)
                    return 1, status
                addCSARVersionToJira(csarMetaDataDict)
                return 0, "SUCCESS"
        else:
            return 1, "Error with dict of metadata, some of the values is null! Please Investigate."
    except Exception as e:
        status = "ERROR in posting CN metadata: Preprocessing JSON File and post data to DB has failed! Please Investigate: " + str(e)
        logger.error(status)
        transaction.savepoint_rollback(sid)
        return 1, status

def processCNServiceGroupData(metadata_content):
    parentObj, errorMsg = processCNParentData(metadata_content)
    if errorMsg:
        return 1, errorMsg
    child_data = metadata_content[0]['image_data']
    result_code, errorMsg, image_rev_obj, helm_rev_obj = postCNImageData(child_data, parentObj)
    if result_code == 1:
        return result_code, errorMsg
    rpm_data = metadata_content[1]['rpm_data']
    result_code, errorMsg = postCNRpmData(rpm_data, image_rev_obj)
    if result_code == 1:
        return result_code, errorMsg
    return 0, None

def processCNParentData(metadata_content):
    parent_data = None
    parent_obj = None
    errorMsg = None
    if type(metadata_content[2]) is dict:
        parent_data = metadata_content[2]['parent_data']
    else:
        return parent_obj, "CN IMAGE DATA ERROR: Error with getting parent_data dict, it is null! Please Investigate."
    if parent_data['image_parent_name']:
        result_code, errorMsg, parent_obj = postCNParentData(parent_data)
        if result_code == 1:
            return parent_obj, errorMsg
    return parent_obj, errorMsg

@transaction.atomic
def postDepUtilDetailData(metadata):
    '''
    this function is to create csar info (the object of CNProductRevision) and store it to DB
    '''
    try:
        productTypeName = "Deployment Utility Detail"
        preCheckResult, preCheckErrorMsg = metadataCheck(metadata['name'], productTypeName, metadata['product_set_version'])
        if preCheckResult == 1:
            return 1, preCheckErrorMsg
        cnProductObj = CNProduct.objects.get(product_name=metadata['name'], product_type__product_type_name=productTypeName)
        cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version=metadata['product_set_version'])
        dev_repo_link = metadata['repo'] + metadata['name'] + "-" + metadata['version'] + ".tgz"
        dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not CNProductRevision.objects.filter(product=cnProductObj, product_set_version=cnProductSetVersionObj).exists():
            cnProductRevObj = CNProductRevision(product=cnProductObj, version=metadata['version'], created=dateCreated,
            product_set_version=cnProductSetVersionObj, size=metadata['size'], dev_link=dev_repo_link, gerrit_repo_sha=metadata['gerrit_repo_sha'])
            cnProductRevObj.save()
        else:
            cnProductRevObj = CNProductRevision.objects.get(product=cnProductObj, product_set_version=cnProductSetVersionObj)
            cnProductRevObj.created = dateCreated
            cnProductRevObj.version = metadata['version']
            cnProductRevObj.size = metadata['size']
            cnProductRevObj.dev_link = dev_repo_link
            cnProductRevObj.gerrit_repo_sha = metadata['gerrit_repo_sha']
            cnProductRevObj.save(force_update=True)
        return 0, "SUCCESS"
    except Exception as e:
        status = "Error in posting deployment utility detail Metadata. Please investigate: " + str(e)
        logger.error(status)
        return 1, status

def addCSARVersionToJira(csarMetaDataDict):
    '''
    This function is to add comments in the JIRA of a cENM Dg with csar version
    '''
    try:
        if csarMetaDataDict['cenm_package_name'] == 'enm-installation-package':
            cnProductsetVersion = csarMetaDataDict['product_set_version']
            cnDeliveryGroupList = CNDeliveryGroup.objects.filter(cnProductSetVersion__product_set_version = cnProductsetVersion).values('id')
            if cnDeliveryGroupList:
                for cnDeliveryGroups in cnDeliveryGroupList:
                    deliveryGroupNumber = cnDeliveryGroups.get('id')
                    updateCnDgInfoToJira(deliveryGroupNumber, csarMetaDataDict['csar_version'], "CSAR DELIVERED")
    except Exception as e:
        status = "Error in posting CSAR Metadata: Couldn't execute create CN productRevision for CSAR! please investigate: " + str(e)
        logger.error(status)

@transaction.atomic
def postCsarData(csarMetaDataDict):
    '''
    this function is to create csar info (the object of CNProductRevision) and store it to DB
    '''
    try:
        cnProductObj = cnProductRevObj = None
        dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # check if CSAR exists
        if not CNProduct.objects.filter(product_name=csarMetaDataDict['cenm_package_name'], product_type__product_type_name="CSAR").exists():
            return 1, "ERROR in posting csar metadata: Failed to get CSAR "+ csarMetaDataDict['cenm_package_name'] + " from DB. CSAR does not exist. Please contact admin to register"
        cnProductObj = CNProduct.objects.get(product_name=csarMetaDataDict['cenm_package_name'], product_type__product_type_name="CSAR")
        # check if product set version exists
        if not CNProductSetVersion.objects.filter(product_set_version=csarMetaDataDict['product_set_version']).exists():
            return 1, "ERROR in posting csar metadata: Failed to get product set version from DB. cnProductSetVersionObj does not exist"
        # get obj for cn product set version
        cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version=csarMetaDataDict['product_set_version'])
        # get dev_link for the csar
        dev_link_repo = csarMetaDataDict['cenm_dev_repo'] + csarMetaDataDict['cenm_package_name'] + "-" + csarMetaDataDict['csar_version'] + ".csar"
        # check if the csar exists in a cn product set
        if not CNProductRevision.objects.filter(product=cnProductObj, product_set_version=cnProductSetVersionObj).exists():
            # create csar
            cnProductRevObj = CNProductRevision(product=cnProductObj, version=csarMetaDataDict['csar_version'], created=dateCreated,
            product_set_version=cnProductSetVersionObj, size = csarMetaDataDict['csar_size'], dev_link = dev_link_repo, gerrit_repo_sha = csarMetaDataDict['gerrit_sha'])
            cnProductRevObj.save()
        else:
            # update and overwrite csar with a new version
            cnProductRevObj = CNProductRevision.objects.get(product=cnProductObj, product_set_version=cnProductSetVersionObj)
            cnProductRevObj.created = dateCreated
            cnProductRevObj.version = csarMetaDataDict['csar_version']
            cnProductRevObj.size = csarMetaDataDict['csar_size']
            cnProductRevObj.dev_link = dev_link_repo
            cnProductRevObj.gerrit_repo_sha = csarMetaDataDict['gerrit_sha']
            cnProductRevObj.save(force_update=True)
        return 0, "SUCCESS"
    except Exception as e:
        status = "Error in posting CSAR Metadata: Couldn't execute create CN productRevision for CSAR! please investigate: " + str(e)
        logger.error(status)
        return 1, status

def extractCsarMetaData(metadata_content):
    '''
    this function is to get metaData as a dict for CSAR to store them in the DB
    '''
    try:
        csarMetaDataDict = {}
        for content in metadata_content:
            if content.get('csar_details') != None:
                if content.get('csar_details')['enm_iso_version'] != None:
                    csarMetaDataDict['enm_iso_version'] = content.get('csar_details')['enm_iso_version']
                if content.get('csar_details')['product_set_version'] != None:
                    csarMetaDataDict['product_set_version'] = content.get('csar_details')['product_set_version']
                if content.get('csar_details')['enm_installation_package_version'] != None:
                    csarMetaDataDict['csar_version'] = content.get('csar_details')['enm_installation_package_version']
                if content.get('csar_details')['enm_installation_package_size'] != None:
                    csarMetaDataDict['csar_size'] = content.get('csar_details')['enm_installation_package_size']
                if content.get('csar_details')['gerrit_repo_sha'] != None:
                    csarMetaDataDict['gerrit_sha'] = content.get('csar_details')['gerrit_repo_sha']
                if content.get('csar_details')['enm_installation_package_name'] != None:
                    csarMetaDataDict['cenm_package_name'] = content.get('csar_details')['enm_installation_package_name']
                if content.get('csar_details')['enm_installation_package_repo'] != None:
                    csarMetaDataDict['cenm_dev_repo'] = content.get('csar_details')['enm_installation_package_repo']
            elif content.get('list_charts_data') != None:
                csarMetaDataDict['integration_charts_data'] = content.get('list_charts_data')
        if not csarMetaDataDict['enm_iso_version']:
            return csarMetaDataDict, 1, "Failed to get enm_iso_version from metaData"
        if not csarMetaDataDict['csar_version']:
            return csarMetaDataDict, 1, "Failed to get csar_version from metaData"
        if not csarMetaDataDict['csar_size']:
            return csarMetaDataDict, 1, "Failed to get csar_size from metaData"
        if not csarMetaDataDict['integration_charts_data']:
            return csarMetaDataDict, 1, "Failed to get integration_charts_data from metaData"
        if not csarMetaDataDict['gerrit_sha']:
            return csarMetaDataDict, 1, "Failed to get gerrit_sha from metaData"
        if not csarMetaDataDict['product_set_version']:
            return csarMetaDataDict, 1, "Failed to get product_set_version from metaData"
        if not csarMetaDataDict['cenm_package_name']:
            return csarMetaDataDict, 1, "Failed to get cenm_package_name from metaData"
        if not csarMetaDataDict['cenm_dev_repo']:
            return csarMetaDataDict, 1, "Failed to get cenm_dev_repo from metaData"
        return csarMetaDataDict, 0, "SUCCESS"
    except Exception as e:
        status = "ERROR before posting CSAR metadata: Failed to extract CSAR MetaData due to unexpected error. Please investigate: " + str(e)
        logger.error(status)
        return csarMetaDataDict, 1, status

def checkCsarMetaData(metadata_content):
    '''
    this function is to check if the required fields (keys) are all available from metadata
    '''
    try:
        required_fields = ['csar_details', 'list_charts_data']
        missing_fields = ' '
        temp = required_fields
        for content in metadata_content:
            if(str(content.keys()[0]) in temp):
                temp.remove(str(content.keys()[0]))
        if len(temp) != 0:
            for field in temp:
                missing_fields += field + ' '
            return 1, "those fields for CSAR metadata is missing: " + missing_fields
        return 0, "Successfully checked CSAR metaData !!"
    except Exception as e:
        status = "Error posting CSAR Metadata: Falied to check CSAR metaData due to internal error: " + str(e)
        logger.error(status)
        return 1, status

def metadataCheck(productName, productTypeName, productSetVersion):
    if not CNProduct.objects.filter(product_name=productName, product_type__product_type_name=productTypeName).exists():
        return 1, "ERROR in posting metadata: This cn product is not registered. Please contact admin to register"
    if not CNProductSetVersion.objects.filter(product_set_version=productSetVersion).exists():
        return 1, "ERROR in posting metadata: Failed to get product set version from DB."
    return 0, None

@transaction.atomic
def get_or_create_cnProductRevision(cnProductObj, version, productSetVersionObj, dataCreated, size = None, gerrit_sha = None, values_file_version = None):
    '''
    This function creates cn product set revision in table or gets it if exists.
    '''
    try:
        cnProductRevisionObj, created = CNProductRevision.objects.get_or_create(product = cnProductObj, version = version, product_set_version = productSetVersionObj, size = size, gerrit_repo_sha = gerrit_sha, values_file_version = values_file_version)
        cnProductRevisionObj.save()
        return 0, "SUCCESS", cnProductRevisionObj
    except Exception as e:
        status = "Error with get or create the product revision when creating the integration chart or csar info! Please investigate: " + str(e)
        return 1, status, cnProductRevisionObj

@transaction.atomic
def get_or_create_cnProductSet(cnProductSetName):
    '''
    This function creates cn product set object in table or gets it if exists.
    '''
    try:
        cnProductSetObj, created = CNProductSet.objects.get_or_create(product_set_name = cnProductSetName)
        cnProductSetObj.save()
        return 0, "SUCCESS", cnProductSetObj
    except Exception as e:
        status = "Error with getting or creating the product set when creating the integration chart or CSAR! Please investigate: " + str(e)
        logger.error(status)
        return 1, status

@transaction.atomic
def get_or_create_cnProduct(cnProductSetObj, productName, product_type):
    '''
    This function creates cn product object in table or gets it if exists.
    '''
    try:
        cnProductObj, created = CNProduct.objects.get_or_create(product_set = cnProductSetObj, product_name = productName, product_type = product_type)
        cnProductObj.save()
        return 0, "SUCCESS", cnProductObj
    except Exception as e:
        status = "Error with getting or creating the product when creating the integration chart or CSAR! Please investigate: " + str(e)
        logger.error(status)
        return 1, status, cnProductObj

@transaction.atomic
def get_or_create_helm(child_data):
    '''
    This function creates helm chart object in table or gets it if exists.
    '''
    try:
        helm_chart_obj, created = CNHelmChart.objects.get_or_create(helm_chart_name = child_data['helm_chart_name'])
        helm_chart_obj.helm_chart_product_number = child_data['cxc_number']
        helm_chart_obj.save(force_update=True)
        return 0, "SUCCESS", helm_chart_obj
    except Exception as e:
        status = "ERROR in posting CN image metadata: Error with get or create the helm chart! Please Investigate: " + str(e)
        logger.error(status)
        return 1, status, None

@transaction.atomic
def get_or_create_image(child_data):
    '''
    This function creates image object in table or gets it if exists.
    '''
    try:
        image_obj, created = CNImage.objects.get_or_create(image_name = child_data['image_name'])
        image_obj.image_product_number = child_data['cxc_number']
        image_obj.save(force_update=True)
        return 0, "SUCCESS", image_obj
    except Exception as e:
        status = "Error with get or create an image! Please Investigate: " + str(e)
        return 1, status, None

@transaction.atomic
def get_or_create_parent_image(parent_data):
    '''
    This function creates parent image object in table or gets it if exists.
    '''
    errorMsg = None
    try:
        parent_image_obj, created = CNImage.objects.get_or_create(image_name = parent_data['image_parent_name'])
        parent_image_obj.save()
        return 0, errorMsg, parent_image_obj
    except Exception as e:
        errorMsg = "ERROR in getting or creating cn image metadata: Error with get or create an parent image! Please Investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg, None

@transaction.atomic
def postIntgrData(intgr_chart_data, dependent_charts):
    '''
    This function posts integration charts data to db.
    Logic of this function:
        create cn product set
        create cn product
        check cn product set version
        create or update cn product revision
        cretea helm product map
    '''
    try:
        cnProductSetName = config.get('CIFWK', 'CNProductSetName')
        dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result_code, status, cnProductSetObj = get_or_create_cnProductSet(cnProductSetName)
        if result_code == 1:
            return result_code, status
        cnProductTypeObj = CNProductType.objects.get(product_type_name = "Integration Chart")
        result_code, status, cnProductObj = get_or_create_cnProduct(cnProductSetObj, intgr_chart_data['chart_name'], cnProductTypeObj)
        if result_code == 1:
            return result_code, status
        if not CNProductSetVersion.objects.filter(product_set_version = intgr_chart_data['product_set_version']).exists():
            return 1, "failed to get CNProductSetVersionObj when creating CNIntegrationChartRevision. Product set version does not exist. Please investigate."
        cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = intgr_chart_data['product_set_version'])
        # get dev_link_repo for the integration chart
        dev_link_repo = intgr_chart_data['chart_repo'] + intgr_chart_data['chart_name'] + "-" + intgr_chart_data['chart_version'] + ".tgz"
        if not CNProductRevision.objects.filter(product = cnProductObj, product_set_version = cnProductSetVersionObj).exists():
            cnProductRevisionObj = CNProductRevision(product = cnProductObj,
                                            version = intgr_chart_data['chart_version'],
                                            created = dateCreated,
                                            size = intgr_chart_data['chart_size'],
                                            dev_link = dev_link_repo,
                                            gerrit_repo_sha = intgr_chart_data['gerrit_repo_sha'],
                                            product_set_version = cnProductSetVersionObj)
            cnProductRevisionObj.save()
        else:
            cnProductRevisionObj = CNProductRevision.objects.get(product = cnProductObj, product_set_version = cnProductSetVersionObj)
            cnProductRevisionObj.version = intgr_chart_data['chart_version']
            cnProductRevisionObj.size = intgr_chart_data['chart_size']
            cnProductRevisionObj.dev_link = dev_link_repo
            cnProductRevisionObj.gerrit_repo_sha = intgr_chart_data['gerrit_repo_sha']
            cnProductRevisionObj.created = dateCreated
            cnProductRevisionObj.save(force_update=True)
        for helm in dependent_charts:
            if not CNHelmChart.objects.filter(helm_chart_name = helm['name']).exists():
                continue
            helm_chart_obj = CNHelmChart.objects.get(helm_chart_name = helm['name'])
            if not CNHelmChartRevision.objects.filter(helm_chart = helm_chart_obj.id, version = helm['version']):
                continue
            helm_rev_obj = CNHelmChartRevision.objects.get(helm_chart = helm_chart_obj.id, version = helm['version'])

            if helm_rev_obj is not None and cnProductRevisionObj is not None:
                result_code, status = createCNHelmToCNProductMapping(helm_rev_obj, cnProductRevisionObj)
                if result_code == 1:
                    return result_code, status
        return 0, "SUCCESS"
    except Exception as e:
        status = "Error: Couldn't post metadata for integration chart! please investigate: " + str(e)
        logger.error(status)
        return 1, status

@transaction.atomic
def postSyncData(sync_data, intgr_values_data):
    '''
        this function is to store the inegration value file data for related inegration charts
    '''
    try:
        result_code = 0
        for intgr_value_file_data in intgr_values_data:
            dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if CNProductRevision.objects.filter(product__product_name = intgr_value_file_data['values_file_name'], product__product_type__product_type_name = "Integration Value File", 
            product_set_version__product_set_version = sync_data['product_set_version']).exists():
                cnProductRevisionObj = CNProductRevision.objects.get(product__product_name = intgr_value_file_data['values_file_name'], 
                product__product_type__product_type_name = "Integration Value File", product_set_version__product_set_version = sync_data['product_set_version'])
                cnProductRevisionObj.version = intgr_value_file_data['values_file_version']
                cnProductRevisionObj.created = dateCreated
                cnProductRevisionObj.save(force_update=True)
            else:
                cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = sync_data['product_set_version'])
                cnProductObj = CNProduct.objects.get(product_name = intgr_value_file_data['values_file_name'], product_type__product_type_name="Integration Value File")
                CNProductRevision.objects.create(product = cnProductObj, version = intgr_value_file_data['values_file_version'], product_set_version = cnProductSetVersionObj, created = dateCreated)
    except Exception as e:
        status = "Error in posting INT-SYNC metadata: Couldn't store INT-Sync meatadata! please investigate: " + str(e)
        logger.error(status)
        return 1, status
    return 0, "SUCCESS"

@transaction.atomic
def createCNHelmToCNProductMapping(helm_rev_obj, cnProductObj):
    '''
    This function create a mapping between integration charts and Helm revisions.
    '''
    try:
        if not CNHelmChartProductMapping.objects.filter(helm_chart_revision = helm_rev_obj, product_revision = cnProductObj).exists():
            helm_intgr_chart_mapping_obj = CNHelmChartProductMapping(helm_chart_revision = helm_rev_obj, product_revision = cnProductObj)
            helm_intgr_chart_mapping_obj.save()
        return 0, "SUCCESS"
    except Exception as e:
        status = "Couldn't add mapping between Helm and product revisions (integration charts)! Please Investigate: " + str(e)
        logger.error(status)
        return 1, status

@transaction.atomic
def postCNImageData(child_data, parent_obj):
    '''
    This function posts image and helm chart data to db.
        It covers the case when image is moved under other helm charts as well.
    Logic of this function:
        create helm chart and helm chart revision
        create cn iamge and cn image revision with parent image included
        create helm to image mapping
    '''
    try:
        dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "helm_chart_name" in child_data.keys():
            result_code, status, helm_chart_obj = get_or_create_helm(child_data)
            if result_code == 1:
                return result_code, status, None, None
            if not CNHelmChartRevision.objects.filter(helm_chart = helm_chart_obj.id, version = child_data['helm_chart_version']).exists():
                helm_rev_obj = CNHelmChartRevision(helm_chart = helm_chart_obj,
                                                version = child_data['helm_chart_version'],
                                                created = dateCreated,
                                                size = None,
                                                gerrit_repo_sha = child_data['gerrit_repo_sha'])
                helm_rev_obj.save()
            else:
                helm_rev_obj = CNHelmChartRevision.objects.get(helm_chart = helm_chart_obj.id, version = child_data['helm_chart_version'])
        else:
            helm_rev_obj = None
        result_code, status, image_obj = get_or_create_image(child_data)
        if result_code == 1:
            return result_code, status, None, None
        if not CNImageRevision.objects.filter(image = image_obj.id, version = child_data['image_version']).exists():
            image_rev_obj = CNImageRevision(image = image_obj,
                                            parent = parent_obj,
                                            version = child_data['image_version'],
                                            created = dateCreated,
                                            size = None,
                                            gerrit_repo_sha = child_data['gerrit_repo_sha'])
            image_rev_obj.save()
        else:
            image_rev_obj = CNImageRevision.objects.get(image = image_obj.id, version = child_data['image_version'])
            image_rev_obj.created = dateCreated
            image_rev_obj.gerrit_repo_sha = child_data['gerrit_repo_sha']
            image_rev_obj.parent = parent_obj
            image_rev_obj.save(force_update=True)
        if helm_rev_obj is not None and image_rev_obj is not None:
            result_code, status = createCNHelmToImageMapping(helm_rev_obj, image_rev_obj)
        if result_code == 1:
            return result_code, status, None, None
        return 0, "SUCCESS", image_rev_obj, helm_rev_obj
    except IntegrityError as e:
        status = "Error in posting CN Image Data: Couldn't execute CRUD functionality for image and helm chart! please investigate: " + str(e)
        logger.error(status)
        return 1, status, None, None

@transaction.atomic
def createCNHelmToImageMapping(helm_rev_obj, image_rev_obj):
    '''
    This function create a mapping between Image Revision and Helm revisions.
    '''
    try:
        if not CNImageHelmChartMapping.objects.filter(image_revision = image_rev_obj, helm_chart_revision = helm_rev_obj).exists():
            image_helm_chart_mapping_obj = CNImageHelmChartMapping(image_revision = image_rev_obj, helm_chart_revision = helm_rev_obj)
            image_helm_chart_mapping_obj.save()
        return 0, "SUCCESS"
    except Exception as e:
        status = "ERROR in posting CN image metadata: Couldn't add mapping between Image and Helm revisions! Please Investigate: " + str(e)
        logger.error(status)
        return 1, status

@transaction.atomic
def postCNParentData(parent_data):
    '''
    This function post parent of image data to db (cnimage and cnimage revision).
    Logic of this function:
        create cn image and cn image revision for parent image
    '''
    errorMsg = None
    try:
        result_code, errorMsg, parent_image_obj = get_or_create_parent_image(parent_data)
        if result_code == 1:
            return result_code, errorMsg, None

        if not CNImageRevision.objects.filter(image = parent_image_obj.id, version = parent_data['image_parent_version']).exists():
            dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            image_rev_obj = CNImageRevision(image = parent_image_obj,
                                        version = parent_data['image_parent_version'],
                                        created = dateCreated,
                                        size = None,
                                        gerrit_repo_sha = None)
            image_rev_obj.save()
            return 0, errorMsg, image_rev_obj
        else:
            image_rev_obj = CNImageRevision.objects.get(image = parent_image_obj.id, version = parent_data['image_parent_version'])
            return 0, errorMsg, image_rev_obj
    except Exception as e:
        errorMsg = "ERROR in posting CN Parent data: Couldn't add metadata for parent image! Please Investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg, None

def postCNRpmData(rpm_data, image_rev_obj):
    '''
    This function post rpm data to db (cn image content)
    '''
    try:
        for rpm in rpm_data:
            if PackageRevision.objects.filter(package__name = rpm['rpm_name'], version = rpm['version']).exists():
                packageRev_obj = PackageRevision.objects.get(package__name = rpm['rpm_name'], version = rpm['version'])
                if not CNImageContent.objects.filter(image_revision__image__image_name = image_rev_obj.image.image_name, package_revision__package__name = rpm['rpm_name'], package_revision__version = rpm['version']).exists():
                    image_content_obj = CNImageContent(image_revision = image_rev_obj,
                                                    package_revision = packageRev_obj)
                    image_content_obj.save()
        return 0, "SUCCESS"
    except Exception as e:
        status = "Error in posting CN RPM data: Couldn't add rpms to Image Content! Please Investigate: " + str(e)
        logger.error(status)
        return 1, status

def storeCloudNativeMetadata(metadata_content):
    '''
    Preprocess Metadata json and post to DB.
    '''
    try:
        result_code, status = preprocessMetadata(metadata_content)
        if result_code == 1:
            return status
        return "SUCCESS"
    except Exception as e:
        status = "Posting CN Metadata has failed! Please investigate the error! " + str(e)
        logger.error(status)
        return status

@transaction.atomic
def get_or_create_cn_product_set_version(productSetVersion, pipeline_status, confidenceLevelName):
    '''
    Gets or Creates CN Product Set
    '''
    try:
        statusDict = {}
        psversion = LooseVersion(productSetVersion)
        dropVersion = str(psversion)[0:5]
        cn_product_set_version_obj, created = CNProductSetVersion.objects.get_or_create(product_set_version = psversion, drop_version=dropVersion)
        if created:
            statusDict[confidenceLevelName] = pipeline_status
            autoUpdateCnDgProductSet(psversion, dropVersion)
        else:
            statusDict = ast.literal_eval(cn_product_set_version_obj.status)
            statusDict[confidenceLevelName] = pipeline_status
        cn_product_set_version_obj.status = statusDict
        cn_product_set_version_obj.save()
        return 0, "SUCCESS", cn_product_set_version_obj
    except Exception as e:
        status = "Error with get or create an product set! Please Investigate: " + str(e)
        return 1, status, None


def createOrUpdateCNProductSet(productSetVersion, pipeline_status, confidenceLevelName):
    '''
    Creating or updating Cloud Native PS Version based on ENM Product Set Version, and sets the status and the confidence level of it.
    '''
    try:
        list_of_verifications = ["in_progress", "failed", "passed"]
        if not re.match(r'[0-9.-]+$', productSetVersion):
            return "Error: productSetVersion value is not valid for this restcall, please ensure it has only digits, dots and dash fe.: (20.10.93, 20.10.93-1 etc.)"
        if str(pipeline_status) not in list_of_verifications:
            return "Error: pipeline status is not valid for this restcall, please choose (in_progress, failed or passed), and try again!"
        result_code, status, cn_product_set_version_obj = get_or_create_cn_product_set_version(str(productSetVersion), str(pipeline_status), str(confidenceLevelName))
        if result_code == 1:
            return status
        if RequiredCNConfidenceLevel.objects.filter(required = 1, confidence_level_name = confidenceLevelName).exists():
            result_code, status = updateOverallConfidenceLevel(str(productSetVersion))
            if result_code == 1:
                return status
        return "SUCCESS"
    except Exception as e:
        status = "Posting Product Set obj for CN has failed! Please investigate the error! " + str(e)
        return status

@transaction.atomic
def updateOverallConfidenceLevel(productSetVersion):
    '''
    Updating overall confidence level by cn product set version when a new confidence level is created or updated.
    '''
    try:
        errorMsg = None
        requiredConfidenceLevelList = []
        baselineConfidenceLevelList = []
        confidenceLevels = None
        passed = inProgress = failed = False
        passed_checkSum = 0
        baseline_passed_checkSum = 0
        # get required confidence levels and store them as list
        required_confidenceLevel = RequiredCNConfidenceLevel.objects.filter(required = 1).values('confidence_level_name')
        baseline_confidenceLevel = RequiredCNConfidenceLevel.objects.filter(required = 1, include_baseline = 1).values('confidence_level_name')
        for confidenceLevel in required_confidenceLevel:
            requiredConfidenceLevelList.append(str(confidenceLevel.get('confidence_level_name')))
        for confidenceLevel in baseline_confidenceLevel:
            baselineConfidenceLevelList.append(str(confidenceLevel.get('confidence_level_name')))
        cnProdSetVersionObj = CNProductSetVersion.objects.get(product_set_version = productSetVersion)
        confidenceLevels = ast.literal_eval(cnProdSetVersionObj.status)
        # filter unrequired confidence levels (it won't have unrequired confidence level for now. only for safety purpose)
        for index, value in confidenceLevels.items():
            if index not in requiredConfidenceLevelList:
                confidenceLevels.pop(index)
        # process overall confidence level logic. Priority: failed > in_progress > passed
        if len(confidenceLevels) != 0:
            for index, value in confidenceLevels.items():
                if index in requiredConfidenceLevelList and value == "in_progress":
                    inProgress = True
                if index in requiredConfidenceLevelList and value == "failed":
                    failed = True
                if index in requiredConfidenceLevelList and value == "passed":
                    passed_checkSum += 1
                    if index in baselineConfidenceLevelList:
                        baseline_passed_checkSum += 1
            if failed:
                cnProdSetVersionObj.overall_status = States.objects.get(state = "failed")
                cnProdSetVersionObj.save()
            elif inProgress or passed_checkSum != len(requiredConfidenceLevelList):
                cnProdSetVersionObj.overall_status = States.objects.get(state = "in_progress")
                cnProdSetVersionObj.save()
            elif (passed_checkSum == len(requiredConfidenceLevelList)) and (baseline_passed_checkSum == len(baselineConfidenceLevelList)) :
                cnProdSetVersionObj.overall_status = States.objects.get(state = "passed")
                cnProdSetVersionObj.save()
            else:
                cnProdSetVersionObj.overall_status = States.objects.get(state = "not_started")
                cnProdSetVersionObj.save()
        else:
            cnProdSetVersionObj.overall_status = States.objects.get(state = "not_started")
            cnProdSetVersionObj.save()
            return 0, errorMsg
    except Exception as e:
        errorMsg = "updating overall confidence level failed. Please investigate: " + str(e)
        return 1, errorMsg
    return 0, errorMsg

@transaction.atomic
def updateAllOverallConfidenceLevels():
    '''
    Updating overall confidence levels for updating old cn product set
    '''
    try:
        errorMsg = None
        sid = transaction.savepoint()
        cnProdSetVersionList = CNProductSetVersion.objects.values('product_set_version')
        for cnProdSetVer in cnProdSetVersionList:
            result_code, errorMsg = updateOverallConfidenceLevel(str(cnProdSetVer.get('product_set_version')))
            if result_code == 1:
                return result_code, errorMsg
    except Exception as e:
        errorMsg = "updating all overall confidence levels failed. Please investigate: " + str(e)
        transaction.savepoint_rollback(sid)
        return result_code, errorMsg
    return "SUCCESS", errorMsg

def overwriteOverallConfidenceLevels(productSetVersion, confidenceLevelState):
    '''
    Overwriting overall confidence levels by cn product set
    '''
    try:
        errorMsg = None
        if not States.objects.filter(state = confidenceLevelState).exists():
            errorMsg = "Overwriting all overall confidence levels failed. Please investigate: confidence level must be in_progress, passed, failed or not_started"
            return "Failed", errorMsg
        if CNProductSetVersion.objects.filter(product_set_version=productSetVersion).exists():
            cnProdSetVersionObj = CNProductSetVersion.objects.get(product_set_version = productSetVersion)
            cnProdSetVersionObj.overall_status = States.objects.get(state = confidenceLevelState)
            cnProdSetVersionObj.save()
            return "SUCCESS", errorMsg
        else:
            errorMsg = "Overwriting all overall confidence levels failed. Please investigate: product set version does not exist"
            return "Failed", errorMsg
    except Exception as e:
        errorMsg = "Overwriting all overall confidence levels failed. Please investigate: " + str(e)
        return "Failed", errorMsg

def getCNImageContentWithLatestRpms(imageRevObj):
    '''
    This function gets the latest version of rpms for services groups by image_name and image_version
    '''
    try:
        allCNImageContent = []
        listOfRpms = uniqueRpms = uniqueVersions = currentCNImageContent = None
        allCNImageContent = getVersionLesserImageContents(imageRevObj)
        currentCNImageContent = CNImageContent.objects.filter(image_revision = imageRevObj)
        if len(currentCNImageContent) == 0:
            currentCNImageContent = CNImageContent.objects.filter(image_revision__image__image_name = imageRevObj.image.image_name, image_revision__version = allCNImageContent[0].image_revision.version)
        uniqueRpms = getUniqueRpms(allCNImageContent)
        uniqueVersions = getUniqueVersions(allCNImageContent)
        listOfRpms = getLatestRpms(uniqueRpms, uniqueVersions, currentCNImageContent, allCNImageContent)
    except Exception as e:
        logger.error("Issue getting cloud native image contents: " + str(e))
    return listOfRpms

def getVersionLesserImageContents(imageRevObj):
    '''
    This function returns list of image contents whose versions are lesser or equal to the current image version
    '''
    try:
        current_version = str(imageRevObj.version)
        current_version_list = re.findall(r"[\w]+", current_version)
        length_image_version = len(current_version_list)
        allCNImageContent = []
        for imageContent in CNImageContent.objects.raw('''SELECT * FROM cireports_cnimagecontent a JOIN cireports_cnimagerevision b ON a.image_revision_id = b.id JOIN cireports_cnimage c ON b.image_id = c.id WHERE c.image_name = %(image_name)s
                ORDER BY cast(substring_index(b.version,'.',1) as UNSIGNED) DESC,
                cast(substring_index(substring_index(b.version,'.',2),'.',-1) as UNSIGNED) DESC,
                cast(substring_index(substring_index(b.version,'.',-1),'-', 1) as UNSIGNED) DESC,
                case 1 WHEN b.version LIKE '%-%' THEN b.id END DESC;''',
                params={'image_name': imageRevObj.image.image_name}):
                imageContent_version = str(imageContent.image_revision.version)
                imageContent_version_list = re.findall(r"[\w]+", imageContent_version)
                isImageVersionLesser = True
                for i in range(0,length_image_version):
                    if int(imageContent_version_list[i]) < int(current_version_list[i]):
                        break
                    if int(imageContent_version_list[i]) > int(current_version_list[i]):
                        isImageVersionLesser = False
                        break
                if isImageVersionLesser == True:
                    allCNImageContent.append(imageContent)
    except Exception as e:
        logger.error("Issue getting cloud native image contents for versions lesser than the current image version: " + str(e))
    return allCNImageContent

def getUniqueRpms(allCNImageContent):
    '''
    This function gets unique rpms from a service group
    '''
    try:
        unique_rpmList = []
        for x in allCNImageContent:
            if x.package_revision.getPackageName() not in unique_rpmList:
                unique_rpmList.append(x.package_revision.getPackageName())
    except Exception as e:
        logger.error("Failed to get unique rpms from db when getting cloud native image contents : " + str(e))
    return unique_rpmList

def getUniqueVersions(allCNImageContent):
    '''
    This function gets all the versions for a service group
    '''
    try:
        unique_VersionList = []
        for x in allCNImageContent:
            if x.image_revision.version not in unique_VersionList:
                unique_VersionList.append(x.image_revision.version)
    except Exception as e:
        logger.error("Failed to get unique versions from db when getting cloud native image contents : " + str(e))
    return unique_VersionList

def getLatestRpms(uniqueRpms, uniqueVersions, currentCNImageContent, allCNImageContent):
    '''
    This function gets the latest rpms for a service group
    logic of this function:
        get the latest rpms from current version
        get the latest rpms from historical versions
    '''
    try:
        listOfPackages = []
        listOfPackages, uniqueRpms = appendCNImageContent(currentCNImageContent, uniqueRpms, listOfPackages)
        for version in uniqueVersions:
            previousCNImageContent = getPrevisouCNImageContent(allCNImageContent, version)
            listOfPackages, uniqueRpms = appendCNImageContent(previousCNImageContent, uniqueRpms, listOfPackages)
    except Exception as e:
        logger.error("Failed to get latest rpms from db when getting cloud native image contents : " + str(e))
    return listOfPackages

def getPrevisouCNImageContent(allCNImageContent, version):
    '''
    This function get rpms for a service group from the previous version of a service group
    '''
    try:
        previousCNImageContent = []
        for cnImageContent in allCNImageContent:
            if(cnImageContent.image_revision.version == version):
                previousCNImageContent.append(cnImageContent)
    except Exception as e:
        logger.error("Failed to get previous CNImageContent from db when getting cloud native image contents : " + str(e))
    return previousCNImageContent

def appendCNImageContent(cnImageContents, uniqueRpms, listOfPackages):
    '''
    store the latest rpms for a service group
    '''
    try:
        for cnImageContent in cnImageContents:
            if cnImageContent.package_revision.getPackageName() in uniqueRpms:
                uniqueRpms.remove(cnImageContent.package_revision.getPackageName())
                listOfPackages.append(cnImageContent)
    except Exception as e:
        logger.error("Failed to append CNImageContent when getting cloud native image contents : " + str(e))
    return listOfPackages, uniqueRpms

def getCENMDiff(curPSVer, prevPSVer):
    '''
    This function is to get CENM commit diff between current product set version and previous product set version
    '''
    try:
        cenmDiff = {}
        cnProdSetVersionList = None
        csarList = None
        integartionChartDict = None
        cnHelmProductMappingList = None
        cnHelmChartRevList = None
        cnImageHelmChartMappingList = None
        cnImageRevList = None
        cnImageNameList = None
        cnImageDict = None
        errorMsg = None
        cnProdSetVersionList, errorMsg = getCNProdSetVersionList(curPSVer, prevPSVer)
        if errorMsg:
            return cenmDiff, errorMsg
        csarList, errorMsg = getCSARDiff(cnProdSetVersionList)
        if errorMsg:
            return cenmDiff, errorMsg
        integartionChartDict, cnHelmProductMappingList, errorMsg = getIntegrationChartsDiff(cnProdSetVersionList)
        if errorMsg:
            return cenmDiff, errorMsg
        cnHelmChartRevList, errorMsg = getHelmChartRevisionList(cnHelmProductMappingList)
        if errorMsg:
            return cenmDiff, errorMsg
        cnImageHelmChartMappingList, errorMsg = getCNImageHelmChartMapping(cnHelmChartRevList)
        if errorMsg:
            return cenmDiff, errorMsg
        cnImageRevList, errorMsg = getCNImageRevisionList(cnImageHelmChartMappingList)
        if errorMsg:
            return cenmDiff, errorMsg
        cnImageNameList, errorMsg = getUniqueCNImageName(cnImageRevList)
        if errorMsg:
            return cenmDiff, errorMsg
        cnImageDict, errorMsg = getCNImageDiff(cnImageNameList, cnImageRevList)
        if errorMsg:
            return cenmDiff, errorMsg
        cenmDiff['csarChanges'] = csarList
        cenmDiff['integrationChartChanges'] = integartionChartDict
        cenmDiff['cnImageChanges'] = cnImageDict
    except Exception as e:
        errorMsg = "Failed to get CENM diff between " + curPSVer + " and " + prevPSVer + ': ' + str(e)
        logger.error(errorMsg)
    return cenmDiff, errorMsg

def getCENMCommits(repoName, gerrit_sha, version):
    '''
    This function is to get commit messages (JSON) for CENM using Gerrit API
    '''
    try:
        commits = None
        errorMsg = None
        gerritUserName = config.get("CIFWK", "functionalUser")
        gerritPassword = config.get("CIFWK", "functionalUserPassword")
        gerritUrl = 'https://gerrit-gamma.gic.ericsson.se/a/projects/OSS%2Fcom.ericsson.oss.containerisation%2F' + repoName + '.git/commits/' + gerrit_sha
        response = requests.get(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword))
        commits = ast.literal_eval(response.content.replace(")]}\'", ""))
        commits = getJiraFromCommits(commits)
    except Exception as e:
        # leave error msg on the table
        errorMsg = "Failed to get commits for " + gerrit_sha + "  in repo " + repoName + " version:"+ version + " : " + str(e)
        commits = errorMsg
        logger.error(errorMsg)
    return commits

def getJiraFromCommits(commits):
    '''
    This function is to get jira number from gerrit commits and update jira ticket as a separate value in commits and update commit msg without jira
    There is a number of strange commit format on Gerrit repo. needs to cover the format as much as possible.
    '''
    try:
        # [JIRA-12345] commitmsg
        if commits['subject'].split()[0].find("[") >= 0:
            commits['jira'] = commits['subject'].split()[0].replace('[',"").replace(']',"")
        # JIRA-12345 commitmsg
        elif commits['subject'].split()[0].find("-") >= 0:
            commits['jira'] = commits['subject'].split()[0]
            commits['subject'] = commits['subject'].replace(commits['subject'].split()[0], "").replace(commits['subject'].split()[1], "")
        # JIRA-1234 : commit msg
        elif commits['subject'].split()[0].find("-") >= 0 and commits['subject'].split()[1].find(":") >= 0:
            commits['jira'] = commits['subject'].split()[0]
            commits['subject'] = commits['subject'].replace(commits['subject'].split()[0], "").replace(commits['subject'].split()[1], "")
        # no jira:commitmsg
        elif commits['subject'].split()[0].lower().find("no") >= 0 and commits['subject'].split()[1].lower().find("jira") >= 0 and commits['subject'].split()[1].find(":") >= 0:
            commits['jira'] = 'NO JIRA'
            index = commits['subject'].split()[1].index(":")
            tempMsg = commits['subject'].split()[1][index + 1:]
            commits['subject'] = commits['subject'].replace(commits['subject'].split()[0], "").replace(commits['subject'].split()[1], tempMsg)
        # no jira : commitmsg
        elif commits['subject'].split()[0].lower().find("no") >= 0 and commits['subject'].split()[1].lower().find("jira") >= 0 and commits['subject'].split()[2].lower().find(":") >=0:
            commits['jira'] = 'NO JIRA'
            commits['subject'] = commits['subject'].replace(commits['subject'].split()[0], "").replace(commits['subject'].split()[1], "").replace(commits['subject'].split()[2], "")
        # NO JIRA - commitmsg
        elif commits['subject'].split()[0].lower().find("no") >= 0 and commits['subject'].split()[1].lower().find("jira") >= 0 and commits['subject'].split()[2].find("-") >= 0:
            commits['jira'] = 'NO JIRA'
            commits['subject'] = commits['subject'].replace(commits['subject'].split()[0], "").replace(commits['subject'].split()[1], "").replace(commits['subject'].split()[2], "")
        # NO JIRA commitmsg
        elif commits['subject'].split()[0].lower().find("no") >= 0 and commits['subject'].split()[1].lower().find("jira") >= 0:
            commits['jira'] = 'NO JIRA'
            commits['subject'] = commits['subject'].replace(commits['subject'].split()[0], "").replace(commits['subject'].split()[1], "")
        #nojira commitmsg
        elif commits['subject'].split()[0].lower().find("nojira") >= 0:
            commits['jira'] = 'NO JIRA'
            commits['subject'] = commits['subject'].replace(commits['subject'].split()[0], "")
        else:
            commits['jira'] = 'NO JIRA'
    except Exception as e:
        logger.error("Failed to get jira number from commits: " + str(e))
    return commits

def getCNProdSetVersionList(curPSVer, prevPSVer):
    '''
    This function is to get cn product set version obj from current product set version to previous product set version
    '''
    try:
        cnProdSetVersionList = []
        prodSetVerObjList = []
        errorMsg = None
        curDrop = None
        prevDrop = None
        isValid = False
        index = 0
        # get drop version for curPSVer and prevPSVer
        curDrop = curPSVer[:5]
        prevDrop = prevPSVer[:5]
        # get all cn product set version obj from latest version to oldest version so that the order for getting other cn obj will be always from latest to oldest
        for p in CNProductSetVersion.objects.raw('''SELECT * FROM cireports_cnproductsetversion WHERE drop_version in %(dropList)s
        AND active = 1
        ORDER BY drop_version DESC,
        cast(substring_index(substring_index(product_set_version,'.',-1),'-', 1) as UNSIGNED) DESC,
        case 1 WHEN product_set_version LIKE '%-%' THEN id END DESC;''',
        params={'dropList': [curDrop, prevDrop]}):
            prodSetVerObjList.append(p)
        while(index < len(prodSetVerObjList)):
            if str(prodSetVerObjList[index].product_set_version) == curPSVer:
                isValid = True
                cnProdSetVersionList.append(prodSetVerObjList[index])
                index += 1
                continue
            if str(prodSetVerObjList[index].product_set_version) == prevPSVer and isValid:
                isValid = False
                cnProdSetVersionList.append(prodSetVerObjList[index])
                break
            if isValid:
                cnProdSetVersionList.append(prodSetVerObjList[index])
            index += 1
    except Exception as e:
        errorMsg = "Failed to get cn between ps version " + curPSVer + " and " + prevPSVer + ': ' + str(e)
        logger.error(errorMsg)
    return cnProdSetVersionList, errorMsg

def getCSARDiff(cnProdSetVersionList):
    '''
    This function is to get commits history for csar from current product set to previous product set
    for loop will not be sequential (newest to oldest version). use while loop with index for a temporary use
    '''
    try:
        csarResultDict = {}
        errorMsg = None
        areAllNone = False
        csarObjList = CNProduct.objects.filter(product_type__product_type_name = "CSAR").all()
        index = 0
        for csarObj in csarObjList:
            csarResultDict[csarObj] = []
            index = 0
            cnProductRevObj = None
            while(index < len(cnProdSetVersionList)):
                if CNProductRevision.objects.filter(product_set_version = cnProdSetVersionList[index], product__product_name = csarObj.product_name).exists():
                    csarDict = {}
                    cnProductRevObj = CNProductRevision.objects.get(product_set_version = cnProdSetVersionList[index], product__product_name = csarObj.product_name)
                    csarDict["object"] = cnProductRevObj
                    csarDict["commitMsg"] = getCENMCommits(str(cnProductRevObj.product.repo_name), str(csarDict["object"].gerrit_repo_sha), str(csarDict["object"].version))
                    csarResultDict.get(csarObj).append(csarDict)
                else:
                    csarResultDict.get(csarObj).append(None)
                index += 1
        # For rendering purpose, update the value to None to the a csar that has no value rather than a list of None
        for csarObj in csarObjList:
            for item in csarResultDict.get(csarObj):
                if(item != None):
                    areAllNone = False
                    break
                if(item == None):
                    areAllNone = True
            if areAllNone:
                csarResultDict[csarObj] = None
        # For rendering purpose, if all the csar are not available, giving None value rather than a list of None
        areAllNone = False
        for key, value in csarResultDict.items():
            if(value != None):
                    areAllNone = False
                    break
            if(value == None):
                areAllNone = True
        if areAllNone:
            csarResultDict = None
    except Exception as e:
        errorMsg = "Failed to get csar diff :" + str(e)
        logger.error(errorMsg)
    return csarResultDict, errorMsg

def getIntegrationChartsDiff(cnProdSetVersionList):
    '''
    This function is to get commits history for integration charts from current product set to previous product set and get helmchartProductMapping for getting helm revision obj
    for loop will not be sequential (new to old version). use while loop for a temporary use
    '''
    try:
        integrationChartDict = {}
        cnHelmProductMappingList = []
        integrationChartObjList = None
        exclude_list = ['CSAR','Deployment Utility', 'Integration Value File']
        integrationChartObjList = CNProduct.objects.filter().all().exclude(product_type__product_type_name__in = exclude_list)
        errorMsg = None
        areAllNone = False
        # Arrange integration chart diff by integration chart name
        for integrationChartObj in integrationChartObjList:
            integrationChartDict[integrationChartObj] = []
            index = 0
            cnProductRevObj = None
            while(index < len(cnProdSetVersionList)):
                if CNProductRevision.objects.filter(product_set_version = cnProdSetVersionList[index], product__product_name = integrationChartObj.product_name).exists():
                    cnProductRevObj = CNProductRevision.objects.get(product_set_version = cnProdSetVersionList[index], product__product_name = integrationChartObj.product_name)
                    integrationChartsDict = {}
                    integrationChartsDict["object"] = cnProductRevObj
                    integrationChartsDict["commitMsg"] = getCENMCommits(str(integrationChartObj.product_name), str(integrationChartsDict["object"].gerrit_repo_sha), str(integrationChartsDict["object"].version))
                    integrationChartDict.get(integrationChartObj).append(integrationChartsDict)
                    # return helmmapping list if an integration chart has its helm chart
                    if CNHelmChartProductMapping.objects.filter(product_revision = cnProductRevObj).exists():
                        cnHelmProductMappingList.append(CNHelmChartProductMapping.objects.filter(product_revision = cnProductRevObj))
                else:
                    integrationChartDict.get(integrationChartObj).append(None)
                index += 1
        # For rendering purpose, update the value to None to the a integration chart that has no value rather than a list of None
        for integrationChartObj in integrationChartObjList:
            for item in integrationChartDict.get(integrationChartObj):
                if(item != None):
                    areAllNone = False
                    break
                if(item == None):
                    areAllNone = True
            if areAllNone:
                integrationChartDict[integrationChartObj] = None
        # For rendering purpose, if all the integration charts are not available, giving None value rather than a list of None
        areAllNone = False
        for key, value in integrationChartDict.items():
            if(value != None):
                    areAllNone = False
                    break
            if(value == None):
                areAllNone = True
        if areAllNone:
            integrationChartDict = None
    except Exception as e:
        errorMsg = "Failed to get integration charts diff : " + str(e)
        logger.error(errorMsg)
    return integrationChartDict, cnHelmProductMappingList, errorMsg

def getHelmChartRevisionList(cnHelmProductMappingList):
    '''
    This function is to get the cn helm chart revision from cnhelmproductmapping list as the list has nested array
    why nested loop: a integration chart may have one or more helm charts (nested list)
    '''
    try:
        cnhelmChartRevList = []
        errorMsg = None
        outerIndex = 0
        while(outerIndex < len(cnHelmProductMappingList)):
            innerIndex = 0
            while(innerIndex < len(cnHelmProductMappingList[outerIndex])):
                if cnHelmProductMappingList[outerIndex][innerIndex].helm_chart_revision not in cnhelmChartRevList:
                    cnhelmChartRevList.append(cnHelmProductMappingList[outerIndex][innerIndex].helm_chart_revision)
                innerIndex += 1
            outerIndex += 1
    except Exception as e:
        errorMsg = "Failed to get helm charts revision obj: " + ': ' + str(e)
        logger.error(errorMsg)
    return cnhelmChartRevList, errorMsg

def getCNImageHelmChartMapping(cnHelmChartRevList):
    '''
    This function is to get cnImageHelmChartMapping for getting cn images
    '''
    try:
        cnImageHelmChartMappingList = []
        index = 0
        errorMsg = None
        while(index < len(cnHelmChartRevList)):
            if CNImageHelmChartMapping.objects.filter(helm_chart_revision = cnHelmChartRevList[index]).exists():
                cnImageHelmChartMappingList.append(CNImageHelmChartMapping.objects.filter(helm_chart_revision = cnHelmChartRevList[index]))
            index += 1
    except Exception as e:
        errorMsg = "Failed to get cn image helm chart mapping " + str(e)
        logger.error(errorMsg)
    return cnImageHelmChartMappingList, errorMsg

def getCNImageRevisionList(cnImageHelmChartMappingList):
    '''
    This function is to get the cn image revision from cnimaghelm mapping
    why nested loop: nested list. However, innere list has only one element
    '''
    try:
        cnImageRevList = []
        errorMsg = None
        outerIndex = 0
        while(outerIndex < len(cnImageHelmChartMappingList)):
            innerIndex = 0
            while(innerIndex < len(cnImageHelmChartMappingList[outerIndex])):
                if cnImageHelmChartMappingList[outerIndex][innerIndex].image_revision not in cnImageRevList:
                    cnImageRevList.append(cnImageHelmChartMappingList[outerIndex][innerIndex].image_revision)
                innerIndex += 1
            outerIndex += 1
    except Exception as e:
        errorMsg = "Failed to get cn image revision obj: " + ': ' + str(e)
        logger.error(errorMsg)
    return cnImageRevList, errorMsg

def getUniqueCNImageName(cnImageRevList):
    '''
    This function is to get unique cn image name for cn image revision as a part of the process to get cenm diff
    '''
    try:
        uniqueList = []
        errorMsg = None
        for x in cnImageRevList:
            if x.image.image_name not in uniqueList:
                uniqueList.append(x.image.image_name)
    except Exception as e:
        errorMsg = "Failed to get unique name when processing cenm diff: " + str(e)
        logger.error(errorMsg)
    return uniqueList, errorMsg

def getCNImageDiff(cnImageNameList, cnImageRevList):
    '''
    This function is to get cn image commit diff by cn image revision
    '''
    try:
        cnImageDiffDict = {}
        errorMsg = None
        outerIndex = 0
        # arrange the result of cn image diff by cn image name
        while(outerIndex < len(cnImageNameList)):
            innerIndex = 0
            cnImageDiffDict[cnImageNameList[outerIndex]] = []
            while(innerIndex < len(cnImageRevList)):
                if cnImageNameList[outerIndex] == cnImageRevList[innerIndex].image.image_name:
                    cnImageDict = {}
                    cnImageDict["currentVersion"] = None
                    cnImageDict["object"] = cnImageRevList[innerIndex]
                    cnImageDict["commitMsg"] = getCENMCommits(str(cnImageRevList[innerIndex].image.image_name), str(cnImageRevList[innerIndex].gerrit_repo_sha), str(cnImageRevList[innerIndex].version))
                    cnImageDict["currentVersion"] = cnImageRevList[innerIndex].version
                    cnImageDiffDict.get(cnImageNameList[outerIndex]).append(cnImageDict)
                innerIndex += 1
            outerIndex += 1
        # For rendering purpose, if we have empty cn image diff, giving None value to cn image list
        if cnImageDiffDict == {}:
            cnImageDiffDict = None
    except Exception as e:
        errorMsg = "Failed to get cn image diff between ps version: " + str(e)
        logger.error(errorMsg)
    return cnImageDiffDict, errorMsg

def getDropNamesForCENM():
    '''
    This function is to get drop name for cenm
    '''
    try:
        dropList = None
        drops = CNProductSetVersion.objects.values('drop_version').distinct().order_by('-drop_version')
        dropList = drops
    except Exception as e:
        logger.error("Failed to get drop names for CENM: " + str(e))
    return dropList

def getProductSetVersionForCENM(dropName):
    '''
    This function is to get all the product set version for cenm
    '''
    try:
        productSetVersionList = None
        productSetVersionList = CNProductSetVersion.objects.filter(drop_version = dropName, active = True).values('product_set_version')
    except Exception as e:
        logger.error("Failed to get product set version for CENM: " + str(e))
    return productSetVersionList

def getLinkedCNProductSetVersion(enmProductSetVersion):
    '''
    This function is to get linked cn product set version by enm ps
    '''
    try:
        errorMsg = None
        linkedProductSetVersion = None
        if CNProductSetVersion.objects.filter(product_set_version__startswith = enmProductSetVersion, active = True).exists():
            linkedProductSetVersion = CNProductSetVersion.objects.filter(product_set_version__startswith = enmProductSetVersion, active = True).values('product_set_version').order_by('-id')[0].get("product_set_version")
        else:
            linkedProductSetVersion = False
    except Exception as e:
        errorMsg = "Failed to get linked product set version for CENM: " + str(e)
        logger.error(errorMsg)
    return linkedProductSetVersion, errorMsg

def getLinkedENMProductSetVersion(CNProductSetVersionNumber):
    '''
    This function is to get linked enm product set version by cenm ps
    '''
    try:
        errorMsg = None
        linkedProductSetVersion = None
        if not CNProductSetVersion.objects.filter(product_set_version = CNProductSetVersionNumber).exists():
            linkedProductSetVersion = False
            return linkedProductSetVersion, errorMsg
        # Handling rebuilt cenm product set version
        if CNProductSetVersionNumber.find("-") != -1:
            index = CNProductSetVersionNumber.index("-")
            CNProductSetVersionNumber = CNProductSetVersionNumber[0:index]
        if ProductSetVersion.objects.filter(version = CNProductSetVersionNumber, drop__release__name="ENM3.0").exists():
            linkedProductSetVersion = ProductSetVersion.objects.filter(version = CNProductSetVersionNumber).values('version')[0].get("version")
        else:
            linkedProductSetVersion = False
    except Exception as e:
        errorMsg = "Failed to get linked product set version for ENM: " + str(e)
        logger.error(errorMsg)
    return linkedProductSetVersion, errorMsg

def getAllCNProductSetVersionByDrop(dropNumber):
    '''
    This function is to get all the cn product set version (if rebuilt ps exist, return the last build of that cn ps)
    '''
    try:
        errorMsg = None
        allCNProductSetVersionDict = {}
        allCNVersions = CNProductSetVersion.objects.filter(drop_version = dropNumber).exclude(product_set_version__contains = '-')
        for cnProductSetVersion in allCNVersions:
            tempPsVer = None
            basePsIndex = 0
            if CNProductSetVersion.objects.filter(product_set_version__startswith = cnProductSetVersion.product_set_version + "-", active = True).exists():
                CNProductSetVersionObj = CNProductSetVersion.objects.filter(product_set_version__startswith = cnProductSetVersion.product_set_version + "-", active = True).order_by('-id')[0]
            elif CNProductSetVersion.objects.filter(product_set_version = cnProductSetVersion.product_set_version, active = True).exists():
                CNProductSetVersionObj = CNProductSetVersion.objects.filter(product_set_version = cnProductSetVersion.product_set_version, active = True)[0]
            else:
                continue
            if "-" in CNProductSetVersionObj.product_set_version:
                tempPsVer = CNProductSetVersionObj.product_set_version.split("-")[basePsIndex]
                allCNProductSetVersionDict[tempPsVer] = CNProductSetVersionObj
            else:
                allCNProductSetVersionDict[cnProductSetVersion.product_set_version] = CNProductSetVersionObj
    except Exception as e:
        errorMsg = "Failed to get all cn product set version when rendering the page for cn product set content: " + str(e)
        logger.error(errorMsg)
    return allCNProductSetVersionDict, errorMsg

def handleRebuiltCNProductSetVersion(product_set_version):
    '''
    This function is handle rebuilt cn product set version before rendering the cn product set content page
    '''
    try:
        productSetVersion = None
        errorMsg = None
        productSetVersion = product_set_version
        if product_set_version.find("-") != -1:
            index = product_set_version.index("-")
            productSetVersion = product_set_version[0:index]
    except Exception as e:
       errorMsg = "Failed to handle rebuilt CNProductSetVersion for " + product_set_version + " when rendering the cn product set content page: " + str(e)
       logger.error(errorMsg)
    return productSetVersion, errorMsg

def getLatestIntegrationCharts(drop, product_set_version):
    '''
    This function is get the latest cn integration charts before rendering the cn product set content page
    '''
    try:
        listOfIntegrationCharts = None
        errorMsg = None
        if CNProductRevision.objects.filter(product_set_version__drop_version = drop, product_set_version__product_set_version = product_set_version, product__product_type__product_type_name="Integration Chart").exists():
            listOfIntegrationCharts = CNProductRevision.objects.filter(product_set_version__drop_version = drop, product_set_version__product_set_version = product_set_version, product__product_type__product_type_name="Integration Chart")
    except Exception as e:
       errorMsg = "Failed to get latest Integration charts for " + product_set_version + " when rendering the cn product set content page: " + str(e)
       logger.error(errorMsg)
    return listOfIntegrationCharts, errorMsg

def getIntegrationValueFiles(product_set_version):
    '''
    This function is get all the integration value files data for rendering the cn product set content page
    '''
    try:
        errorMsg = None
        IntegrationValueFilesList = None
        if CNProductRevision.objects.filter(product_set_version__product_set_version = product_set_version, product__product_type__product_type_name="Integration Value File").exists():
            IntegrationValueFilesList = CNProductRevision.objects.filter(product_set_version__product_set_version = product_set_version, product__product_type__product_type_name="Integration Value File")
    except Exception as e:
        errorMsg = "Failed to get all integration value files for " + product_set_version + ". Please investigate: " + str(e)
        logger.error(errorMsg)
    return IntegrationValueFilesList, errorMsg

def getIntegrationValuesFileVerify(listOfCharts):
  '''
  this function is to get and verify integration values file data from integration charts for the cn product set content page
  '''
  try:
    values_name = values_version = None
    integration_values_file_verify = False
    errorMsg = None
    verifiedCheckSum = 0
    if listOfCharts:
        for intgr_chart in listOfCharts:
            # check values_file_name and values_file_version is not null or not empty string
            if (intgr_chart.values_file_name != None and len(intgr_chart.values_file_name) > 1) and (intgr_chart.values_file_version != None and len(intgr_chart.values_file_version) > 1):
                values_name = intgr_chart.values_file_name
                values_version = intgr_chart.values_file_version
            if intgr_chart.verified == True:
                verifiedCheckSum += 1
        if verifiedCheckSum == len(listOfCharts):
            integration_values_file_verify = True
  except Exception as e:
    errorMsg = "Failed to get Integration Values File data from getLatestIntegrationCharts when rendering the cn product set content page: " + str(e)
    logger.error(errorMsg)
  return integration_values_file_verify, values_name, values_version, errorMsg

def getLatestCSAR(drop, product_set_version):
    '''
    This function is get the latest cn integration charts before rendering the cn product set content page
    '''
    try:
        csarRevList = None
        errorMsg = None
        if CNProductRevision.objects.filter(product_set_version__drop_version = drop, product_set_version__product_set_version = product_set_version, product__product_type__product_type_name = "CSAR").exists():
            csarRevList = CNProductRevision.objects.filter(product_set_version__drop_version = drop, product_set_version__product_set_version = product_set_version, product__product_type__product_type_name = "CSAR")
        if csarRevList:
            for csarRev in csarRevList:
                # caulate the size for csar as MB
                csarRev.size = csarRev.size / 1024 / 1024
    except Exception as e:
       errorMsg = "Failed to get latest CSAR for " + product_set_version + " when rendering the cn product set content page: " + str(e)
       logger.error(errorMsg)
    return csarRevList, errorMsg

def getDeploymentUtilities(product_set_version):
    '''
    This function is to get deployment utilities before rendering the cn product set content page
    '''
    try:
        deployUtilsRev = None
        errorMsg = None
        if CNProductRevision.objects.filter(product_set_version__product_set_version = product_set_version, product__product_type__product_type_name = "Deployment Utility").exists():
            deployUtilsRev = CNProductRevision.objects.filter(product_set_version__product_set_version = product_set_version, product__product_type__product_type_name = "Deployment Utility")
    except Exception as e:
       errorMsg = "Failed to get deployment utilities for " + product_set_version + " when rendering the cn product set content page: " + str(e)
       logger.error(errorMsg)
    return deployUtilsRev, errorMsg

def getDeploymentUtilityDetail(product_set_version):
    '''
    This function is to get deployment utilities before rendering the cn product set content page
    '''
    try:
        deployUtilDetRev = None
        errorMsg = None
        productTypeName = "Deployment Utility Detail"
        if CNProductRevision.objects.filter(product_set_version__product_set_version=product_set_version, product__product_type__product_type_name=productTypeName).exists():
            deployUtilDetRev = CNProductRevision.objects.filter(product_set_version__product_set_version=product_set_version, product__product_type__product_type_name=productTypeName)
    except Exception as e:
       errorMsg = "Failed to get deployment utility detail while rendering the cn product set content page: " + str(e)
       logger.error(errorMsg)
    return deployUtilDetRev, errorMsg

def getCNConfidenceLevel(drop, product_set_version):
    '''
    This function is get the cn confidence level before rendering the cn product set content page
    '''
    try:
        cnProductSetVersionStatus = None
        errorMsg = None
        if CNProductSetVersion.objects.filter(product_set_version = product_set_version, drop_version = drop).exists():
            cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = product_set_version, drop_version = drop)
            cnProductSetVersionStatus = ast.literal_eval(cnProductSetVersionObj.status)
    except Exception as e:
       errorMsg = "Failed to get CN Confidence level for " + product_set_version + " when rendering the cn product set content page: " + str(e)
       logger.error(errorMsg)
    return cnProductSetVersionStatus, errorMsg

def publishVerfiedCNContent(cnProductSetVersion, cnProductName, cnProductRevisionVersion):
    '''
    This function is publish verified cn content for csar and integration charts
    '''
    try:
        errorMsg = None
        cnProductRevisionObj = None
        # update CN content
        if CNProductRevision.objects.filter(product_set_version__product_set_version = cnProductSetVersion, product__product_name = cnProductName, version = cnProductRevisionVersion).exists():
            cnProductRevisionObj = CNProductRevision.objects.get(product_set_version__product_set_version = cnProductSetVersion, product__product_name = cnProductName, version = cnProductRevisionVersion)
            cnProductRevisionObj.verified = True
            cnProductRevisionObj.save(force_update=True)
        else:
            errorMsg = "Failed to publish verified CN Content for cn product set " + cnProductSetVersion + " product name: " + cnProductName + " cnProductVersion: "+ cnProductRevisionVersion +". Please investigate: CNProductRevision does not exist"
            return "Failed", errorMsg
    except Exception as e:
        errorMsg = "Failed to publish verified CN Content for cn product set " + cnProductSetVersion + " product name: " + cnProductName + " cnProductVersion: "+ cnProductRevisionVersion +". Please investigate: " + str(e)
        logger.error(errorMsg)
    return "SUCCESS", errorMsg

def unPublishVerfiedCNContent(cnProductSetVersion, cnProductName, cnProductRevisionVersion):
    '''
    This function is unpublish verified cn content for csar and integration charts
    '''
    try:
        errorMsg = None
        cnProductRevisionObj = None
        result = None
        # update CN content
        if CNProductRevision.objects.filter(product_set_version__product_set_version = cnProductSetVersion, product__product_name = cnProductName, version = cnProductRevisionVersion).exists():
            cnProductRevisionObj = CNProductRevision.objects.get(product_set_version__product_set_version = cnProductSetVersion, product__product_name = cnProductName, version = cnProductRevisionVersion)
            cnProductRevisionObj.verified = False
            cnProductRevisionObj.save(force_update=True)
        else:
            errorMsg = "Failed to unpublish verified CN Content for cn product set " + cnProductSetVersion + " product name: " + cnProductName + " cnProductVersion: "+ cnProductRevisionVersion +". Please investigate: CNProductRevision does not exist"
            return "Failed", errorMsg
    except Exception as e:
        errorMsg = "Failed to unpublish verified CN Content for cn product set " + cnProductSetVersion + " product name: " + cnProductName + " cnProductVersion: "+ cnProductRevisionVersion +". Please investigate: " + str(e)
        logger.error(errorMsg)
        return "Failed", errorMsg
    return "SUCCESS", errorMsg

def verifyIntegrationValueFile(cnProductSetVersion):
    '''
    This function is verify integration value file everytime a new integration chart is added.
    '''
    try:
        errorMsg = None
        result = None
        integrationValueFileFlag = False
        if not CNProductRevision.objects.filter(product_set_version__product_set_version = cnProductSetVersion, product__product_type__product_type_name="Integration Chart", verified = False).exists():
            integrationValueFileFlag = True
        cnProductRevisionObjList = CNProductRevision.objects.filter(product_set_version__product_set_version = cnProductSetVersion, product__product_type__product_type_name="Integration Value File")
        for cnProductRevisionObj in cnProductRevisionObjList:
            cnProductRevisionObj.verified = integrationValueFileFlag
            cnProductRevisionObj.save(force_update=True)
    except Exception as e:
        errorMsg = "Failed to verify integration value file in " + cnProductSetVersion + ". Please investigate: " + str(e)
        logger.error(errorMsg)
        return "Failed", errorMsg
    return "SUCCESS", errorMsg


def releaseISOExternally(isoName):
    '''
    This function is release ISO externally
    '''
    try:
        errorMsg = None
        if ISObuild.objects.filter(artifactId = isoName).exists():
            ISObuild.objects.filter(artifactId = isoName).update(externally_released = 1)
        else:
            raise Exception("Couldn't find iso in CI Portal DB! Contact Admin!")
    except Exception as e:
        errorMsg = "Failed to release ISO Externally for iso name: " + isoName + ". Please investigate: " + str(e)
        logger.error(errorMsg)
    return "SUCCESS", errorMsg

def unreleaseISOExternally(isoName):
    '''
    This function is unrelease ISO externally
    '''
    try:
        errorMsg = None
        if ISObuild.objects.filter(artifactId = isoName).exists():
            ISObuild.objects.filter(artifactId = isoName).update(externally_released = 0)
        else:
            raise Exception("Couldn't find iso in CI Portal DB! Contact Admin!")
    except Exception as e:
        errorMsg = "Failed to unrelease ISO Externally for iso name: " + isoName + ". Please investigate: " + str(e)
        logger.error(errorMsg)
    return "SUCCESS", errorMsg

def wrapCSARData(drop, product_set_version):
    '''
    This function is wrap csar data for cn product set contents
    '''
    csarRevList, errorMsg = getLatestCSAR(drop, product_set_version)
    if errorMsg:
        logger.error(errorMsg)
    csarList = []
    if csarRevList:
        for csarRev in csarRevList:
            prod_url = ""
            if csarRev.verified:
                prod_url = (str(csarRev.product.published_link) + "/" + str(csarRev.product.product_name) + "/" + str(csarRev.product.product_name) + "-" + str(csarRev.version) + ".csar")
            csarList.append({
                    "csar_name": str(csarRev.product.product_name),
                    "csar_version": str(csarRev.version),
                    "size (MB)": str(csarRev.size),
                    "date_created": str(csarRev.created),
                    "gerrit_sha": ("https://gerrit-gamma.gic.ericsson.se/gitweb?p=" + str(csarRev.product.repo_name) + ".git;a=commitdiff;h=" + str(csarRev.gerrit_repo_sha)),
                    "csar_dev_url": str(csarRev.dev_link),
                    "csar_production_url": prod_url,
                    "csar_verify": csarRev.verified
            })
    return csarList

def wrapIntegrationChartData(drop, product_set_version):
    '''
    This function is wrap integration chart data for cn product set contents
    '''
    listOfIntegrationCharts, errorMsg = getLatestIntegrationCharts(drop, product_set_version)
    if errorMsg:
        logger.error(errorMsg)
    charts = []
    if listOfIntegrationCharts:
        for chart in listOfIntegrationCharts:
            prod_url = ""
            if chart.verified:
                prod_url = (chart.product.published_link + "/" + chart.product.product_name + "/" + chart.product.product_name + "-" + chart.version + ".tgz")
            charts.append({
                "chart_name": chart.product.product_name,
                "chart_version": chart.version,
                "size(B)": chart.size,
                "date_created": chart.created,
                "gerrit_sha": ("https://gerrit-gamma.gic.ericsson.se/gitweb?p=" + chart.product.repo_name + ".git;a=commitdiff;h=" + chart.gerrit_repo_sha),
                "chart_dev_url": chart.dev_link,
                "chart_production_url": prod_url,
                "chart_verfied": chart.verified,
            })
    return charts

def wrapIntegrationValueFileData(drop, product_set_version):
    '''
    This function is wrap integration value file data for cn product set contents
    '''
    integrationValueFilesList, errorMsg = getIntegrationValueFiles(product_set_version)
    if errorMsg:
        logger.error(errorMsg)
    integrationValueFileResult = []
    if integrationValueFilesList:
        for integrationValueFileRev in integrationValueFilesList:
            prod_url = ""
            if integrationValueFileRev.verified:
                prod_url = "https://arm.epk.ericsson.se/artifactory/proj-enm-helm/eric-enm-integration-values/" + integrationValueFileRev.product.product_name + "-" + integrationValueFileRev.version + ".yaml"
            integrationValueFileResult.append({
                "values_file_name": str(integrationValueFileRev.product.product_name),
                "values_file_version": str(integrationValueFileRev.version),
                "values_file_verify": integrationValueFileRev.verified,
                "values_file_dev_url": "https://arm.epk.ericsson.se/artifactory/proj-enm-dev-internal-helm/eric-enm-integration-values/" + integrationValueFileRev.product.product_name + "-" + integrationValueFileRev.version + ".yaml",
                "values_file_production_url": prod_url
            })
    return integrationValueFileResult

def wrapDeploymentUtilitiesData(drop, product_set_version):
    '''
    This function is wrap deployment utilities data for cn product set contents
    '''
    deployUtils, errorMsg = getDeploymentUtilities(product_set_version)
    if errorMsg:
        logger.error(errorMsg)
    utils = []
    if deployUtils:
        for deployUtil in deployUtils:
            deployUtilName = deployUtil.product.product_name
            deployUtilVersion = deployUtil.version
            utils.append({
                "deployment_utility_name": deployUtilName,
                "deployment_utility_version": deployUtilVersion
            })
    return utils

def wrapDeploymentUtiltiesDetailData(drop, product_set_version):
    '''
    This function is wrap deployment utilities detail data for cn product set contents
    '''
    deployUtilDets, errorMsg = getDeploymentUtilityDetail(product_set_version)
    deployUtilDetResult = []
    if deployUtilDets:
        for deployUtilDet in deployUtilDets:
            prod_url = ""
            if deployUtilDet.verified:
                prod_url = (deployUtilDet.product.published_link + "/" + deployUtilDet.product.product_name + "/" + deployUtilDet.product.product_name + "-" + deployUtilDet.version + ".tgz")
            deployUtilDetResult.append({
                "name": deployUtilDet.product.product_name,
                "version": deployUtilDet.version,
                "size(B)": deployUtilDet.size,
                "date_created": deployUtilDet.created,
                "gerrit_sha": ("https://gerrit-gamma.gic.ericsson.se/gitweb?p=" + deployUtilDet.product.repo_name + ".git;a=commitdiff;h=" + deployUtilDet.gerrit_repo_sha),
                "dev_url": deployUtilDet.dev_link
            })
    return deployUtilDetResult

def getCloudNativeProductSetContents(drop, product_set_version):
    errorMsg = None
    contents = []
    try:
        if not CNProductSetVersion.objects.filter(product_set_version = product_set_version, active = True).exists():
            errorMsg = "Failed to get cloud native contents, " + str(product_set_version) + " not active or exists."
            contents.append({ "error": errorMsg })
            logger.error(errorMsg)
            return contents, errorMsg
        csarList = wrapCSARData(drop, product_set_version)
        contents.append({
            "csar_data": csarList,
        })
        charts = wrapIntegrationChartData(drop, product_set_version)
        contents.append({
            "integration_charts_data": charts,
        })
        integrationValueFileResult = wrapIntegrationValueFileData(drop, product_set_version)
        contents.append({
            "integration_values_file_data": integrationValueFileResult
        })
        utils = wrapDeploymentUtilitiesData(drop, product_set_version)
        contents.append({
            "deployment_utilities_data": utils
        })
        deployUtilDetResult = wrapDeploymentUtiltiesDetailData(drop, product_set_version)
        contents.append({
            "deployment_utilities_detail_data": deployUtilDetResult
        })
    except Exception as e:
        errorMsg = "There was an issue with fetching the information from DB for getCloudNativeProductSetContents. Please Investigate! " + str(e)
        logger.error(errorMsg)
    return contents, errorMsg

def getGreenCNProductSetVersion(dropName):
    '''
    This function is to get green cn product set version by drop
    '''
    try:
        errorMsg = None
        greenCNProductSetVersion = None
        cnProductSetVersionList = []
        stateObj = States.objects.get(state = "passed")
        if dropName == "latest":
            for p in CNProductSetVersion.objects.raw('''SELECT * FROM cireports_cnproductsetversion WHERE overall_status_id = %(state)s
                AND active = 1
                ORDER BY drop_version DESC,
                cast(substring_index(substring_index(product_set_version,'.',-1),'-', 1) as UNSIGNED) DESC,
                case 1 WHEN product_set_version LIKE '%-%' THEN id END DESC;''',
                params={'state': stateObj.id}):
                    cnProductSetVersionList.append(p)
            if len(cnProductSetVersionList) != 0:
                greenCNProductSetVersion = cnProductSetVersionList[0].product_set_version
        elif re.match(r'[0-9.]+$', dropName):
            dropName = str(dropName)
            if CNProductSetVersion.objects.filter(drop_version = dropName).exists():
                for p in CNProductSetVersion.objects.raw('''SELECT * FROM cireports_cnproductsetversion WHERE drop_version = %(dropName)s AND overall_status_id = %(state)s
                    AND active = 1
                    ORDER BY drop_version DESC,
                    cast(substring_index(substring_index(product_set_version,'.',-1),'-', 1) as UNSIGNED) DESC,
                    case 1 WHEN product_set_version LIKE '%-%' THEN id END DESC;''',
                    params={'dropName': dropName, 'state': stateObj.id}):
                        cnProductSetVersionList.append(p)
                if len(cnProductSetVersionList) != 0:
                    greenCNProductSetVersion = cnProductSetVersionList[0].product_set_version
        else:
            errorMsg = "Error: drop value is not valid, please check. i.e. 20.12, latest"
            return greenCNProductSetVersion, "Error: drop value is not valid, please check. i.e. 20.12, latest"
    except Exception as e:
        errorMsg = "Failed to get green cn product set version for  " + dropName + ". Please investigate: " + str(e)
        logger.error(errorMsg)
    return greenCNProductSetVersion, errorMsg

def processDeploymentUtilities(cnProductSetVersion, content):
    '''
    This function is to create/update deployment utilities by cn product set version.
    '''
    try:
        errorMsg = None
        sid = transaction.savepoint()
        if not CNProductSetVersion.objects.filter(product_set_version=cnProductSetVersion, active = True).exists():
            return "FAILED", "Failed to get product set version from DB. cnProductSetVersion does not exist or active"
        dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for key, value in content.items():
            if not CNProduct.objects.filter(product_set__product_set_name = "Cloud Native ENM", product_name = key, product_type__product_type_name = "Deployment Utility").exists():
                return "FAILED", "Failed to find deployment utility. Please contact admin to register."
            if CNProductRevision.objects.filter(product_set_version__product_set_version = cnProductSetVersion, product__product_type__product_type_name="Deployment Utility", 
            product__product_name = key).exists():
                cnProductRevObj = CNProductRevision.objects.get(product_set_version__product_set_version = cnProductSetVersion, product__product_type__product_type_name="Deployment Utility", 
            product__product_name = key)
                cnProductRevObj.version = value
                cnProductRevObj.created = dateCreated
                cnProductRevObj.save(force_update=True)
            else:
                cnProductSetObj = CNProductSet.objects.get(product_set_name = "Cloud Native ENM")
                cnProductObj = CNProduct.objects.get(product_set = cnProductSetObj, product_name = key)
                cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = cnProductSetVersion)
                cnProductRevObj = CNProductRevision(product = cnProductObj, version = value, product_set_version = cnProductSetVersionObj, created = dateCreated)
                cnProductRevObj.save()
    except Exception as e:
        errorMsg = "Failed to process deployment utilities for product set version " + cnProductSetVersion + " " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return "FAILED", errorMsg
    return "SUCCESS", errorMsg

def getPackageProductMapping(packageName):
    '''
    This function is to get all the related products for a package.
    '''
    try:
        result = None
        errorMsg = None
        packageObj = None
        productNameList = []
        packageObj = Package.objects.get(name = packageName)
        productObjList = ProductPackageMapping.objects.filter(package__name = packageName).values('product__name')
        for product in productObjList:
           productNameList.append(product['product__name'])
        result = {"products": productNameList}
    except Exception as e:
        errorMsg = "ERROR: Failed to get packageProductMapping for " + packageName + " Please investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

@transaction.atomic
def updateTeamInfo():
    '''
    This function is to creates/updates team data from Team Inventory API to CI Portal.
    '''
    errorMsg = None
    result = None
    teamInventoryData = None
    teamData = []
    teamInventoryUrl = config.get("CIFWK", "teamInventoryUrl")
    required_RA = []
    try:
        response = requests.get(teamInventoryUrl)
        teamInventoryData = json.loads(response.content)
        for temp_ra in RequiredRAMapping.objects.values("team_inventory_ra_name"):
            required_RA.append(temp_ra["team_inventory_ra_name"])
        for tempData in teamInventoryData:
            if tempData["programArea"] in required_RA and tempData["program"] == "ENM":
                temp = {
                    "teamName": tempData["name"].replace(" ", ""),
                    "programRA": RequiredRAMapping.objects.get(team_inventory_ra_name=tempData["programArea"]).component.element,
                    "program": tempData["program"],
                    "isSynced": False,
                    "isNewTeam": False,
                    "hasNewRA": False
                }
                teamData.append(temp)
    except Exception as e:
        errorMsg = "Failed to get data from team inventory. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    try:
        for team in teamData:
            sid = transaction.savepoint()
            # check if team exists
            if not Component.objects.filter(product__name=team["program"], label__name = "Team", element = team["teamName"]).exists():
                # create a new team if this team does not exist
                logger.info("Syncing team inventory data: new team found for " + team["teamName"] + " RA: " + team["programRA"] + ". Creating a new team.")
                productObj = Product.objects.get(name=team["program"])
                raObj = Component.objects.get(product__name=team["program"], label__name = "RA", element = team["programRA"])
                labelObj = Label.objects.get(name="Team")
                dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                componentObj = Component(product=productObj, label = labelObj, parent = raObj, element = team["teamName"], dateCreated = dateCreated)
                componentObj.save()
                team["hasNewRA"] = True
                team["isNewTeam"] = True
            else:
                logger.info("Syncing team inventory data: Existing team found for " + team["teamName"] + ".")
                raObj = Component.objects.get(product__name=team["program"], label__name = "RA", element = team["programRA"])
                productObj = Product.objects.get(name=team["program"])
                labelObj = Label.objects.get(name="Team")
                dateCreated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # deprecate current active team if found
                if Component.objects.filter(product__name=team["program"], label__name = "Team", element = team["teamName"], deprecated = False).exists():
                    componentObj = Component.objects.get(product__name=team["program"], label__name = "Team", element = team["teamName"], deprecated = False)
                    componentObj.deprecated = True
                    componentObj.save(force_update=True)
                if Component.objects.filter(product__name=team["program"], label__name = "Team", parent = raObj, element = team["teamName"], deprecated = True).exists():
                    # reactivate deprecated team if an existing deprecated team has required RA
                    logger.info("Syncing team inventory data: Existing team found for " + team["teamName"] + " RA: " + team["programRA"] + " in DB. Data will remain the same.")
                    existingComponentObj = Component.objects.get(product__name=team["program"], label__name = "Team", parent = raObj, element = team["teamName"])
                    existingComponentObj.deprecated = False
                    existingComponentObj.save(force_update=True)
                else:
                    # create an existing team with new RA if no historical RA found
                    logger.info("Syncing team inventory data: Existing team found for " + team["teamName"] + " RA: " + team["programRA"] + ". Applying a new RA for this team.")
                    newComponentObj = Component(product=productObj, label = labelObj, parent= raObj, element = team["teamName"], dateCreated = dateCreated)
                    newComponentObj.save()
                    team["hasNewRA"] = True
            team["isSynced"] = True
            logger.info("Syncing team inventory data: " + team["teamName"] + " has been updated successfully.")
        result = teamData
    except Exception as e:
        errorMsg = "Failed to update team info from Team Inventory to CI Portal for team " + team["teamName"] + ". Please investigate: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
        result = teamData
    return result, errorMsg

def getOverallWorkingBaselineByDrop(dropNumber):
    '''
    This function is to get all the overall working baselines by a given drop.
    '''
    try:
        cnProductSetVersionList = []
        result = None
        errorMsg = None
        for temp in CNProductSetVersion.objects.raw('''SELECT * FROM cireports_cnproductsetversion WHERE drop_version = %(dropName)s
                AND active = 1
                ORDER BY drop_version DESC,
                cast(substring_index(substring_index(product_set_version,'.',-1),'-', 1) as UNSIGNED) DESC,
                case 1 WHEN product_set_version LIKE '%-%' THEN id END DESC;''', params={'dropName': dropNumber}):
                    cnProductSetVersionList.append({"version": temp.product_set_version, "status": temp.overall_status.state})
        result = cnProductSetVersionList
    except Exception as e:
        errorMsg = "Failed to get all the overall working baselines for drop " + dropNumber + ". Please Investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def obsoleteDeliveryGroup_UI(request, product, drop, groupId, user, returnErrorValues):
    '''
    The obsoleteGroupDeliveries function loops through the artifacts in a delivery group and obsoletes them through UI
    '''
    obsolete_DG_lock.acquire()
    statusList = []
    errMsg = None
    try:
        deliveryGroupObj = DeliveryGroup.objects.get(id=groupId)
    except Exception as e:
        errMsg = "ERROR obsoleting group " + str(groupId) +": " + str(e)
        logger.error(errMsg)
        statusList.append(errMsg)
        returnErrorValues['info'] = statusList
        obsolete_DG_lock.release()
        return errMsg, returnErrorValues
    try:
        if deliveryGroupObj.obsoleted == False:
            status = obsoleteDeliveryGroupArtifacts(deliveryGroupObj, user, product, drop, False)
            if "ERROR" in str(status):
                errMsg = status
                returnErrorValues['info'] = status
                obsolete_DG_lock.release()
                return errMsg, returnErrorValues
            logger.debug("Successfully Obsoleted group " + str(groupId))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            deliveryGroupObj.delivered = False
            deliveryGroupObj.obsoleted = True
            deliveryGroupObj.modifiedDate = now
            deliveryGroupObj.warning = False
            deliveryGroupObj.save(force_update=True)
            deliveredComment = str(user.first_name) + " "  + str(user.last_name) + " obsoleted this group from the drop"
            sendDeliveryGroupMessage(deliveryGroupObj,"obsolete")
            sendDeliveryGroupUpdatedEmail(user, groupId, deliveredComment)
            newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
        else:
            errMsg = "ERROR when obsoleting the Delivery Group " + str(deliveryGroupObj.id) + " This delivery group has already obsoleted"
            logger.error(errMsg)
            statusList.append(errMsg)
            returnErrorValues['info'] = statusList
            obsolete_DG_lock.release()
            return errMsg, returnErrorValues
    except Exception as e:
        errMsg = "ERROR obsoleting group " + str(groupId) +": " + str(e)
        logger.error(errMsg)
        statusList.append(errMsg)
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            deliveryGroupObj.warning = True
            deliveryGroupObj.save(force_update=True)
            deliveredComment = str(user.first_name) + " "  + str(user.last_name) + " could not Obsolete this Group due to Errors: " + str(e)
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
            sendObsoleteGroupErrorEmail(product, drop, groupId, str(e), str(user.username))
        except Exception as e:
            logger.error("ERROR sending obsolete error email for " + str(groupId) +": " + str(e))
        returnErrorValues['info'] = statusList
        obsolete_DG_lock.release()
        return errMsg, returnErrorValues
    obsolete_DG_lock.release()
    return errMsg, returnErrorValues

def obsoleteDeliveryGroup_API(groupId, product, drop, forceOption, user):
    '''
    The obsoleteGroupDeliveries function loops through the artifacts in a delivery group and obsoletes them through API
    '''
    obsolete_DG_lock.acquire()
    statusList = []
    errMsg = None
    try:
        deliveryGroupObj = DeliveryGroup.objects.get(id=groupId)
    except Exception as e:
        errMsg = "ERROR obsoleting group " + str(groupId) + ": " + str(e)
        logger.error(errMsg)
        statusList.append(errMsg)
        obsolete_DG_lock.release()
        return statusList
    if deliveryGroupObj.obsoleted != False:
        errMsg = "ERROR obsoleting group " + str(groupId) + ": group does not exist in delivered."
        logger.error(errMsg)
        statusList.append(errMsg)
        obsolete_DG_lock.release()
        return statusList
    try:
        obsoleteResult = obsoleteDeliveryGroupArtifacts(deliveryGroupObj, user, product, drop, forceOption)
        if "ERROR" in str(obsoleteResult):
            errMsg = str(obsoleteResult)
            logger.error(errMsg)
            statusList.append(errMsg)
            obsolete_DG_lock.release()
            return statusList
        logger.debug("Successfully Obsoleted group " + groupId)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        deliveryGroupObj.delivered = False
        deliveryGroupObj.obsoleted = True
        deliveryGroupObj.modifiedDate = now
        deliveryGroupObj.warning = False
        deliveryGroupObj.save(force_update=True)
        deliveredComment = str(user.first_name) + " " + str(user.last_name) + " obsoleted this group from the drop"
        sendDeliveryGroupMessage(deliveryGroupObj,"obsolete")
        sendDeliveryGroupUpdatedEmail(user, groupId, deliveredComment)
        newComment = DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
    except Exception as e:
        errMsg = "ERROR obsoleting group: " + str(groupId) + ": " + str(e)
        logger.error(errMsg)
        statusList.append(errMsg)
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            deliveryGroupObj.warning = True
            deliveryGroupObj.save(force_update=True)
            deliveredComment = str(user.first_name) + " " + str(user.last_name) + " could not Obsolete this Group due to Errors: " + str(e)
            DeliveryGroupComment.objects.create(deliveryGroup=deliveryGroupObj, comment=deliveredComment, date=now)
            sendObsoleteGroupErrorEmail(product, drop, groupId, str(e), str(user.username))
        except Exception as e:
            errMsg = "ERROR sending obsolete error email for " + str(groupId) + ": " + str(e)
            logger.error(errMsg)
            statusList.append(errMsg)
        obsolete_DG_lock.release()
        return statusList
    obsolete_DG_lock.release()
    return statusList

def getConfidenceLevelVersion():
    '''
    This function is to get the product set version of the latest passed cENM-Deploy-II-Charts, cENM-Deploy-UG-Charts, cENM-Deploy-II-CSAR.
    '''
    try:
        confidenceLevelMap = {}
        resultMap = {}
        requiredConfidenceLevelList = config.get('CIFWK', 'confidenceLevelList').split(',')
        result = None
        errorMsg = None
        flag = False
        dropsObj=CNProductSetVersion.objects.order_by('-drop_version').values('drop_version').distinct()

        for drops in dropsObj:
            for cnProdSetVersionObj in CNProductSetVersion.objects.raw('''SELECT * FROM cireports_cnproductsetversion where drop_version = %(dropName)s
            AND active = 1 AND overall_status_id = 3
            ORDER BY cast(substring_index(substring_index(product_set_version,'.',-1),'-', 1) as UNSIGNED) DESC,
            case 1 WHEN product_set_version LIKE '%-%' THEN id END DESC ;''', params={'dropName': drops['drop_version']}):
                confidenceLevelMap.update(ast.literal_eval(cnProdSetVersionObj.status))
                for confidenceLevelName, value in confidenceLevelMap.items():
                    if confidenceLevelName in requiredConfidenceLevelList and value == "passed" and confidenceLevelName not in resultMap:
                        resultMap[confidenceLevelName] = cnProdSetVersionObj.product_set_version
                if len(resultMap) == len(requiredConfidenceLevelList):
                    flag = True
                    break
            if flag:
                break
        result = resultMap
    except Exception as e:
        errorMsg = "Failed to get the confidence level version. Please Investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def updateCNProductSetVersionActiveness(productSetVersion, status):
    '''
    This function is to update cn product set version activeness by a given product set version. An inactive product set version will not display in the front-end
    '''
    try:
        result = None
        errorMsg = None
        if not CNProductSetVersion.objects.filter(product_set_version = productSetVersion).exists():
            errorMsg = "Failed to update CN Product set for " + productSetVersion + ". CN product set version not exists. "
            return result, errorMsg
        CNProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = productSetVersion)
        CNProductSetVersionObj.active = status
        CNProductSetVersionObj.save(force_update=True)
        result = "Successfully updated CN Product set version: " + productSetVersion + ". New status value: " + str(status)
    except Exception as e:
        errorMsg = "Failed to update CN Product set for " + productSetVersion + ": " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def getCNHistoricalProductSetVersions(productSetVersion):
    '''
    This function is get all the historical prdouct set versions by a given base cn product set version
    '''
    try:
        errorMsg = None
        activeCNPSVersions = []
        inactiveCNPSVersions = []
        allCNVersions = CNProductSetVersion.objects.filter(product_set_version__startswith = productSetVersion)
        lengthproductSetVersion=len(productSetVersion)
        for cnProdSetVersionObj in CNProductSetVersion.objects.raw('''SELECT * FROM cireports_cnproductsetversion where product_set_version LIKE %(productSetVersion)s
            ORDER BY cast(substring_index(substring_index(product_set_version,'.',-1),'-', 1) as UNSIGNED) DESC,
            case 1 WHEN product_set_version LIKE '%-%' THEN id END DESC ;''', params={'productSetVersion': productSetVersion+"%"}):
                if cnProdSetVersionObj.active:
                    # check if its a base product set version or the character at the end of the base version is a '-' to check if its the rebuild version of the base cenm product set.
                    if cnProdSetVersionObj.product_set_version == productSetVersion or cnProdSetVersionObj.product_set_version[lengthproductSetVersion] == '-':
                        activeCNPSVersions.append(cnProdSetVersionObj)
                else:
                    inactiveCNPSVersions.append(cnProdSetVersionObj)
    except Exception as e:
        errorMsg = "Failed to get all cn product set version when rendering the page for cn product set content: " + str(e)
        logger.error(errorMsg)
    return activeCNPSVersions, inactiveCNPSVersions, errorMsg

def udpateOldIntegrationValueFileData():
    '''
    This function is to get the product set version of the latest passed cENM-Deploy-II-Charts and cENM-Deploy-UG-Charts .
    '''
    try:
        sid = transaction.savepoint()
        result = None
        errorMsg = None
        allCNProductSetVersionObj = CNProductSetVersion.objects.all()
        allCNProductSetRevisionList = []
        for productSetVerionObj in allCNProductSetVersionObj:
            cnProductSetRevisionObj = CNProductRevision.objects.filter(product_set_version = productSetVerionObj).exclude(values_file_name=None).exclude(values_file_version=None).values('product_set_version__product_set_version', 'values_file_name', 'values_file_version').distinct()
            cnIntegrationChartsList = CNProductRevision.objects.filter(product_set_version = productSetVerionObj, product__product_type__product_type_name="Integration Chart").values('product_set_version__product_set_version', 'verified', 'created')
            if len(cnProductSetRevisionObj) > 0:
                for cnIntegrationChartValues in cnIntegrationChartsList:
                    verified_Flag = True
                    cnProductSetRevisionObj[0]['created'] = cnIntegrationChartValues['created']
                    if len(cnIntegrationChartValues) > 0:
                        if not cnIntegrationChartValues['verified']:
                            verified_Flag = False
                            break
                cnProductSetRevisionObj[0]['verified'] = verified_Flag
                allCNProductSetRevisionList.append(cnProductSetRevisionObj[0])
        for cnProductSetRevisionObj in allCNProductSetRevisionList:
            cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = cnProductSetRevisionObj['product_set_version__product_set_version'])
            cnProductObj = CNProduct.objects.get(product_name = cnProductSetRevisionObj['values_file_name'], product_type__product_type_name="Integration Value File")
            CNProductRevision.objects.create(product = cnProductObj, version = cnProductSetRevisionObj['values_file_version'], product_set_version = cnProductSetVersionObj, created = cnProductSetRevisionObj['created'], verified = cnProductSetRevisionObj['verified'])
        result = 'SUCCESS'
    except Exception as e:
        errorMsg = "Failed to update old integration value files data. Please Investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        result = 'FAILED'
    return result, errorMsg

def getActiveDropsByProduct(productName):
    '''
    This function is to get a list of active drops by a given cn product name.
    '''
    try:
        errorMsg = None
        result = []
        currentTime = datetime.now()
        activeDropList = CNDrop.objects.filter(active_date__gt=currentTime, cnProductSet__product_set_name=productName).values('name')
        result = activeDropList
    except Exception as e:
        errorMsg = "Failed to get active drops for " + productName + ". Please investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def getCNImage():
    '''
    This function is to get a list of cnImage.
    '''
    try:
        errorMsg = None
        result = []
        cnImageList = CNImage.objects.all().values('image_name')
        result = cnImageList
    except Exception as e:
        errorMsg = "Failed to get a list of serivce groups. Please investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def getCNProduct(productTypeName):
    '''
    This function is to get a list of cn products.
    '''
    try:
        errorMsg = None
        result = []
        cnProductList = CNProduct.objects.filter(product_type__product_type_name = productTypeName).values('product_name')
        result = cnProductList
    except Exception as e:
        errorMsg = "Failed to get a list of cn products. Please investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

@transaction.atomic
def createCNDeliveryGroup(userName, dropName, cnImageGerritList, cnIntegrationChartGerritList, cnIntegrationValueGerritList, cnPipelineList, jiraList, team, teamEmailId, missingDep, missingDepReason, impactedDeliveryGroups):
    '''
    This function is to create cn Delivery Group.
    '''
    errorMsg = None
    initComment = None
    user = None
    emailValidation = '@'
    try:
        sid = transaction.savepoint()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cnImageGerritListInDrop = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__cnDrop__name = dropName, cnDeliveryGroup__deleted = 0).values_list('cnGerrit__gerrit_link', flat = True)
        cnProductGerritListInDrop = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__cnDrop__name = dropName, cnDeliveryGroup__deleted = 0).values_list('cnGerrit__gerrit_link', flat = True)
        cnPipelineGerritListInDrop = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__cnDrop__name = dropName, cnDeliveryGroup__deleted = 0).values_list('cnGerrit__gerrit_link', flat = True)
        cnDgsGerritListInDrop = list(chain(cnImageGerritListInDrop, cnProductGerritListInDrop, cnPipelineGerritListInDrop))
        dropObj = CNDrop.objects.get(name=dropName, cnProductSet__product_set_name="Cloud Native ENM")
        try:
            compObj = Component.objects.get(element=team, deprecated=0)
        except Exception as e:
            errorMsg = "ERROR: Failed to create CN Delivery Group. Team does not exist or active. Please investigate: " + str(e)
            transaction.savepoint_rollback(sid)
            logger.error(errorMsg)
            return 1, errorMsg
        user = User.objects.get(username=userName)
        if teamEmailId == "":
            teamEmailId = None
        elif teamEmailId != "" and emailValidation not in teamEmailId:
            errorMsg = "ERROR: Invalid Team Email Id format"
            return 1, errorMsg
        totalCnDGLength = len(cnImageGerritList)+ len(cnIntegrationChartGerritList)+ len(cnIntegrationValueGerritList)+ len(cnPipelineList)
        if totalCnDGLength == 0:
            errorMsg = "ERROR: DG should not be empty"
            logger.error(errorMsg)
            return 1, errorMsg
        deliveryGroupObj = CNDeliveryGroup.objects.create(cnDrop=dropObj, queued=1, creator=user.email, teamEmail=teamEmailId, component=compObj, modifiedDate=now, createdDate=now, missingDependencies=missingDep)
        initComment = str(user.first_name) + " " + str(user.last_name) + " created delivery group " + str(deliveryGroupObj.id)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = deliveryGroupObj, comment = initComment, date = now)
        # processing service groups and gerrit link
        cnImage_gerrit_status, cnImage_gerrit_errorMsg = processCNImageGerritList(deliveryGroupObj, cnImageGerritList, cnDgsGerritListInDrop, dropName)
        if cnImage_gerrit_status == 1:
            errorMsg = cnImage_gerrit_errorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
        # set cn integration chart list and gerrit
        cnIntegrationChart_gerrit_status, cnIntegrationChart_gerrit_errorMsg = processCNIntegartionChartGerritList(deliveryGroupObj, cnIntegrationChartGerritList, cnDgsGerritListInDrop, dropName)
        if cnIntegrationChart_gerrit_status == 1:
            errorMsg = cnIntegrationChart_gerrit_errorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
        # set cn integration value list and gerrit
        cnIntegrationValue_gerrit_status, cnIntegrationValue_gerrit_errorMsg = processCNIntegartionValueGerritList(deliveryGroupObj, cnIntegrationValueGerritList, cnDgsGerritListInDrop, dropName)
        if cnIntegrationValue_gerrit_status == 1:
            errorMsg = cnIntegrationValue_gerrit_errorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
        # processing cn pipeline and its gerrit info
        cnPipeline_status, cnPipeline_errorMsg = processCNPipelineGerritList(deliveryGroupObj, cnPipelineList, cnDgsGerritListInDrop, dropName)
        if cnPipeline_status == 1:
            errorMsg = cnPipeline_errorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
        # set impacted enm delivery group for cn delivery group
        impactedDG_status, impactedDG_errorMsg = addENMDeliveryGroupToCNDeliveryGroup(impactedDeliveryGroups, deliveryGroupObj, "CENM")
        if impactedDG_status == 1:
            errorMsg = impactedDG_errorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
        # processing jira
        jiraErrorMsg = None
        jiraStatusCode, jiraErrorMsg = addJIraIssueToCNDeliveryGroup(deliveryGroupObj, jiraList)
        if jiraStatusCode == 1:
            errorMsg = jiraErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
        # Set missing dependencies
        missingDepStatus, missingDepErrorMsg = setMissingDependenciesForCNDeliveryGroup(user, deliveryGroupObj.id, missingDep, missingDepReason)
        if missingDepStatus == 1:
            errorMsg = missingDepErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return 1, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR while creating CN Delivery Group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return 1, errorMsg
    return deliveryGroupObj.id, errorMsg

@transaction.atomic
def addJIraIssueToCNDeliveryGroup(deliveryGroupObj, jiraList):
    '''
    This function is to add jira tickets to CN Delivery Group.
    '''
    errorMsg = None
    isProjectExcept = False
    try:
        for jira in jiraList:
            jira = jira.upper()
            jsonObj, statusCode = jiraValidation(jira)
            if statusCode == "200":
                isProjectExcept = getExceptionForJiraProject(jsonObj)
                if not isProjectExcept:
                    isJiraValidationPass, jiraWarning, issueType = getWarningForJiraType(jsonObj)
                    if isJiraValidationPass == False:
                        errorMsg = "Entered Jira type (" + str(issueType)  + ") cannot be added to current delivery."
                        return 1, errorMsg
                if not CNJiraIssue.objects.filter(jiraNumber = jira).exists():
                    jiraObj = CNJiraIssue.objects.create(jiraNumber = jira, issueType = jsonObj['fields']['issuetype']['name'])
                else:
                    jiraObj = CNJiraIssue.objects.get(jiraNumber = jira)
                    jiraObj.issueType = jsonObj['fields']['issuetype']['name']
                    jiraObj.save(force_update=True)
                if deliveryGroupObj != None:
                    if not CNDGToCNJiraIssueMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnJiraIssue = jiraObj).exists():
                        CNDGToCNJiraIssueMap.objects.create(cnDeliveryGroup = deliveryGroupObj, cnJiraIssue = jiraObj)
                        if (jiraObj.issueType == "TR" or jiraObj.issueType == "Bug"):
                            deliveryGroupObj.bugOrTR = True
                            deliveryGroupObj.save()
            else:
                errorMsg = "Entered Jira can not be verified. Please check your entry."
                return 1, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR while adding JIRA ticket to CN Delivery Group: " + str(e) + ". Please investigate."
        return 1, errorMsg
    return 0, errorMsg

@transaction.atomic
def setMissingDependenciesForCNDeliveryGroup(user, deliveryGroupId, missingDepValue, missingDepReason):
    '''
    This function is to set missing dependencies for CN Delivery Group.
    '''
    errorMsg = None
    missingDependenciesComment = None
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        deliveryGroupObj = CNDeliveryGroup.objects.get(id=deliveryGroupId)
        if missingDepValue:
            deliveryGroupObj.missingDependencies = True
            missingDependenciesComment = str(user.first_name) + " " + str(user.last_name) + " flagged this delivery group as having missing dependencies"
            if len(missingDepReason) > 0:
                missingDependenciesComment += "<br /> Reason: " + missingDepReason
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup=deliveryGroupObj, comment=missingDependenciesComment, date=now)
        else:
            deliveryGroupObj.missingDependencies = False
            missingDependenciesComment = str(user.first_name) + " "  + str(user.last_name) + " unflagged this delivery group as having missing dependencies"
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup=deliveryGroupObj, comment=missingDependenciesComment, date=now)
        deliveryGroupObj.save(force_update=True)
    except Exception as e:
        errorMsg = "ERROR: Failed to set missing dependencies for CN Delivery Group: " + str(deliveryGroupId) + ". Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def checkDuplicateCNImageName(cnImageGerritList, serviceGroupKey):
    '''
    This function is to check if there is duplicate service group name before going into a CN delivery group.
    '''
    errorMsg = None
    cnImageNameList = []
    duplicateCNImageName = None
    try:
        for cnImageGerrit in cnImageGerritList:
            cnImageName = cnImageGerrit.get(serviceGroupKey)
            cnImageNameList.append(cnImageName)
        for cnImageName in cnImageNameList:
            if cnImageNameList.count(cnImageName) > 1:
                duplicateCNImageName = cnImageName
                return True, duplicateCNImageName, errorMsg
        return False, duplicateCNImageName, errorMsg
    except Exception as e:
        errorMsg = "ERROR: Failed to check duplicate service group name: " + str(e)
        logger.error(errorMsg)
        return None, duplicateCNImageName, errorMsg

@transaction.atomic
def processCNImageGerritList(deliveryGroupObj, cnImageGerritList, cnDgsGerritListInDrop, dropName):
    '''
    This function is to map service groups and gerrit link to a CN Delivery Group.
    '''
    errorMsg = None
    try:
        isDuplicate, duplicateCNImageName, errorMsg = checkDuplicateCNImageName(cnImageGerritList, 'imageName')
        if isDuplicate or errorMsg:
            errorMsg = "ERROR: Failed to add service group data while creating a delivery group: Duplicate service group found: " + duplicateCNImageName
            return 1, errorMsg
        for cnImageGerrit in cnImageGerritList:
            cnImageName = cnImageGerrit.get('imageName')
            try:
                cnImageObj = CNImage.objects.get(image_name = cnImageName)
            except Exception as e:
                errorMsg = "ERROR: Failed to get service group for " + cnImageName + " in CI Portal DB. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkDuplicateGerritLink(cnImageGerrit, cnDgsGerritListInDrop)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkCnDgReadyToCreate(cnImageGerrit, dropName)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check service groups and gerrit link is ready to create to a CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            for cnGerritLink in cnImageGerrit.get('gerritList'):
                try:
                    cnGerritObj = None
                    if not CNGerrit.objects.filter(gerrit_link = cnGerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = cnGerritLink)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = cnGerritLink)
                except Exception as e:
                    errorMsg = "ERROR: Failed to get gerrit link data for " + cnGerritLink + ". Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    CNDGToCNImageToCNGerritMap.objects.create(cnDeliveryGroup = deliveryGroupObj, cnImage = cnImageObj, cnGerrit = cnGerritObj)
                except Exception as e:
                    errorMsg = "ERROR: Failed to map service groups and gerrit link to a CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to process service group and gerrit link for a CN Delivery Group. Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def checkDuplicateGerritLink(cnGerritList, cnDgsGerritListInDrop):
    errorMsg = None
    try:
        for cnGerritLink in cnGerritList.get('gerritList'):
            if cnGerritLink in cnDgsGerritListInDrop:
                errorMsg = "ERROR: Dg already created with the gerrit link " + cnGerritLink
                return 1, errorMsg
    except Exception as e:
        errorMsg = "ERROR: Failed to check gerrit link data for " + cnGerritLink + ". Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def checkCnDgReadyToCreate(cnGerritList, dropName):
    errorMsg = None
    gerritUserName = config.get('CIFWK', 'cENMfunctionalUser')
    gerritPassword = config.get('CIFWK', 'cENMfunctionalUserPassword')
    gerritHostName = config.get('GERRIT_SSH', 'gerrit_hostname')
    try:
        for cnGerritLink in cnGerritList.get('gerritList'):
            changeNum = cnGerritLink.split("/c/")[-1].replace("/", "")
            changeId = cireports.cloudNativeUtils.getChangeId(changeNum, gerritUserName, gerritPassword, gerritHostName)
            branch = cireports.cloudNativeUtils.getBranch(changeNum, gerritUserName, gerritPassword, gerritHostName)
            latestDrop = CNDrop.objects.latest('id').name
            if dropName == latestDrop:
                if branch != "master":
                    errorMsg = "ERROR: GerritLink " + cnGerritLink + " Should be in master branch"
                    logger.error(errorMsg)
                    return 1, errorMsg
            elif branch[10:15] != dropName:
                    errorMsg = "ERROR: GerritLink " + cnGerritLink + " Should be in point fix branch " + dropName
                    logger.error(errorMsg)
                    return 1, errorMsg
            revisionId = cireports.cloudNativeUtils.getRevisionId(str(changeId), gerritUserName, gerritPassword, gerritHostName)
            verified, codeReview = cireports.cloudNativeUtils.getReview(str(changeId), str(revisionId), gerritUserName, gerritPassword, gerritHostName)
            if not verified or not codeReview:
                errorMsg = "ERROR: GerritLink " + cnGerritLink + " is either not having +1 verified or +2 code-review"
                logger.error(errorMsg)
                return 1, errorMsg
    except Exception as e:
        errorMsg = "ERROR: Failed to get gerrit link data for " + cnGerritLink + ". Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

@transaction.atomic
def processCNIntegartionChartGerritList(deliveryGroupObj, cnIntegrationChartGerritList, cnDgsGerritListInDrop, dropName):
    '''
    This function is to map integration charts and gerrit link to a CN Delivery Group.
    '''
    errorMsg = None
    try:
        for cnInteChartGerrit in cnIntegrationChartGerritList:
            cnIntegrationChartName = cnInteChartGerrit.get('integrationChartName')
            try:
                cnProductObj = CNProduct.objects.get(product_name = cnIntegrationChartName, product_type__product_type_name="Integration Chart")
            except Exception as e:
                errorMsg = "ERROR: Failed to get integration chart for " + cnIntegrationChartName + " in CI Portal DB. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkDuplicateGerritLink(cnInteChartGerrit, cnDgsGerritListInDrop)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkCnDgReadyToCreate(cnInteChartGerrit, dropName)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check integration chart and gerrit link is ready to create to a CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            for cnGerritLink in cnInteChartGerrit.get('gerritList'):
                try:
                    cnGerritObj = None
                    if not CNGerrit.objects.filter(gerrit_link = cnGerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = cnGerritLink)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = cnGerritLink)
                except Exception as e:
                    errorMsg = "ERROR: Failed to get gerrit link data for " + cnGerritLink + ". Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = deliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
                except Exception as e:
                    errorMsg = "ERROR: Failed to map integration charts and gerrit link to a CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to process integration charts and gerrit link for a CN Delivery Group. Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

@transaction.atomic
def processCNIntegartionValueGerritList(deliveryGroupObj, cnIntegrationValueGerritList, cnDgsGerritListInDrop, dropName):
    '''
    This function is to map integration value and gerrit link to a CN Delivery Group.
    '''
    errorMsg = None
    try:
        for cnInteValueGerrit in cnIntegrationValueGerritList:
            cnIntegrationValueName = cnInteValueGerrit.get('integrationValueName')
            try:
                cnProductObj = CNProduct.objects.get(product_name = cnIntegrationValueName, product_type__product_type_name="Integration Value")
            except Exception as e:
                errorMsg = "ERROR: Failed to get integration value for " + cnIntegrationValueName + " in CI Portal DB. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkDuplicateGerritLink(cnInteValueGerrit, cnDgsGerritListInDrop)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkCnDgReadyToCreate(cnInteValueGerrit, dropName)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check integration value and gerrit link is ready to create to a CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            for cnGerritLink in cnInteValueGerrit.get('gerritList'):
                try:
                    cnGerritObj = None
                    if not CNGerrit.objects.filter(gerrit_link = cnGerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = cnGerritLink)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = cnGerritLink)
                except Exception as e:
                    errorMsg = "ERROR: Failed to get gerrit link data for " + cnGerritLink + ". Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = deliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
                except Exception as e:
                    errorMsg = "ERROR: Failed to map integration value and gerrit link to a CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to process integration value and gerrit link for a CN Delivery Group. Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

@transaction.atomic
def processCNPipelineGerritList(deliveryGroupObj, cnPipelineGerritList, cnDgsGerritListInDrop, dropName):
    '''
    This function is to map cn pipeline and its gerrt links to a cn delivery group.
    '''
    errorMsg = None
    try:
        for cnPipelineGerrit in cnPipelineGerritList:
            cnPipelineName = cnPipelineGerrit.get('pipelineName')
            cnPipelineObj = None
            try:
                if not CNPipeline.objects.filter(pipeline_link = cnPipelineName).exists():
                    cnPipelineObj = CNPipeline.objects.create(pipeline_link = cnPipelineName)
                else:
                    cnPipelineObj = CNPipeline.objects.get(pipeline_link = cnPipelineName)
            except Exception as e:
                errorMsg = "Failed to get cnPipeline data for " + cnPipeline + " while adding pipeline data to cn delivery group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkDuplicateGerritLink(cnPipelineGerrit, cnDgsGerritListInDrop)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            try:
                result, errorMsg = checkCnDgReadyToCreate(cnPipelineGerrit, dropName)
                if errorMsg:
                    return 1, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to check cnPipeline data and gerrit link is ready to create to a CN Delivery Group. Please investigate: " + str(e)
                logger.error(errorMsg)
                return 1, errorMsg
            for cnGerritLink in cnPipelineGerrit.get('gerritList'):
                try:
                    cnGerritObj = None
                    if not CNGerrit.objects.filter(gerrit_link = cnGerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = cnGerritLink)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = cnGerritLink)
                except Exception as e:
                    errorMsg = "ERROR: Failed to get gerrit link data for " + cnGerritLink + ". Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    CNDGToCNPipelineToCNGerritMap.objects.create(cnDeliveryGroup = deliveryGroupObj, cnPipeline = cnPipelineObj, cnGerrit = cnGerritObj)
                except Exception as e:
                    errorMsg = "Failed to create CNDGToCNPipelineToCNGerritMap data. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to add cn pipeline data to cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def getDeliveryGroupsByDrop(dropName, queueType):
    '''
    This function is to get delivery groups by a given drop and queue type.
    '''
    errorMsg = None
    result = []
    try:
        if queueType == "ENM":
            dropObj = Drop.objects.get(name = dropName, release__name="ENM3.0")
            deliveryGroupList = DeliveryGroup.objects.filter(drop = dropObj).values('id')
        else:
            dropObj = CNDrop.objects.get(name = dropName)
            deliveryGroupList = CNDeliveryGroup.objects.filter(cnDrop = dropObj).values('id')
        result = deliveryGroupList
    except Exception as e:
        errorMsg = "ERROR: Failed to get a list of " +queueType +"Delivery Group for drop " + dropName + ". Please investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def addENMDeliveryGroupToCNDeliveryGroup(impactedDeliveryGroups, deliveryGroupObj, queueType):
    '''
    This function is to add the mapping between ENM delivery groups to a CN delivery group.
    '''
    errorMsg = None
    try:
        if queueType == "ENM":
            for cenm_dg in impactedDeliveryGroups:
                cenm_deliveryGroupObj = CNDeliveryGroup.objects.get(id = cenm_dg)
                CNDGToDGMap.objects.create(deliveryGroup = deliveryGroupObj, cnDeliveryGroup = cenm_deliveryGroupObj)
        else:
            for enm_dg in impactedDeliveryGroups:
                enm_deliveryGroupObj = DeliveryGroup.objects.get(id = enm_dg)
                CNDGToDGMap.objects.create(deliveryGroup = enm_deliveryGroupObj, cnDeliveryGroup = deliveryGroupObj)
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to add mapping for ENM delivery groups to a CN delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def checkCNDrop(productName, dropName):
    '''
    This function is to check CN Drop and CN Product.
    '''
    errorMsg = None
    status = None
    cnDropObj = None
    try:
        now = datetime.now()
        if not CNDrop.objects.filter(name = dropName, cnProductSet__product_set_name = productName).exists():
            status = "not exist"
            return status, cnDropObj, errorMsg
        cnDropObj = CNDrop.objects.get(name = dropName, cnProductSet__product_set_name = productName)
        if cnDropObj.reopen:
            status = "reopen"
            return status, cnDropObj, errorMsg
        if now > cnDropObj.active_date:
            status = "frozen"
            return status, cnDropObj, errorMsg
    except Exception as e:
        errorMsg = "Failed to check CN Drop. Please investigate: " + str(e)
        logger.error(errorMsg)
        status = "error"
        return status, cnDropObj, errorMsg
    return 'open', cnDropObj, errorMsg

def checkCNDeliveryQueueAdminPerms(user):
    '''
    This function is to check user permission before using cn delivery queue.
    '''
    errorMsg = None
    adminGroup = None
    adminPerms = None
    try:
        adminGroup = config.get("CIFWK", "cnDeliveryQueueAdminGroup")
        if user.groups.filter(name=adminGroup).exists():
            adminPerms = True
        else:
            adminPerms = False
        return adminPerms, errorMsg
    except Exception as e:
        errorMsg = "Failed to check admin permission for using cn delivery queue. Please investigate: " + str(e)
        logger.error(errorMsg)
        adminPerms = False
        return adminPerms, errorMsg

def getCNDeliveryQueueData(productName, dropNumber):
    '''
    This function is to check user permission before rendering cn delivery queue page.
    '''
    errorMsg = None
    dropObj = None
    result = None
    try:
        # get drop data
        try:
            dropObj = CNDrop.objects.get(name = dropNumber, cnProductSet__product_set_name = productName)
        except Exception as e:
            errorMsg = "ERROR: Failed to get drop data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
            logger.error(errorMsg)
            return result, errorMsg
        # get a list of cn delivery group objects
        try:
            requiredCNDeliveryGroupFields = ('id', 'queued', 'delivered',
            'obsoleted', 'deleted', 'creator', 'cnProductSetVersion__product_set_version',
            'component__element', 'component__parent__element', 'component__parent__label__name',
            'createdDate', 'deliveredDate', 'modifiedDate',
            'missingDependencies', 'bugOrTR')
            cnDeliveryGroups = CNDeliveryGroup.objects.select_related('component', 'cnProductSetVersion').filter(cnDrop=dropObj).order_by('-modifiedDate').only(requiredCNDeliveryGroupFields).values(*requiredCNDeliveryGroupFields)
        except Exception as e:
            errorMsg = "ERROR: Failed to CNDeliveryGroup data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
            logger.error(errorMsg)
            return result, errorMsg
        # get mapping data for each of the cn delivery group
        for group in cnDeliveryGroups:
            cnDGToCNImageToCNGerritMapObjList = None
            cnDGToCNProductToCNGerritMapObjList = None
            cnDGToCNPipelineMapObjList = None
            cnDGToDGMapObjList = None
            cnDGToCNJiraIssueMapObjList = None
            cnDeliveryGroupCommentObjList = None
            cnDGToCNProductToCNGerritMapResult = []
            cnDGToIntegrationValueToCNGerritMapResult = []
            cnDGToCNPipelineToCNGerritMapResult = []
            cnDGToDGMapResult = []
            cnDGToCNImageToCNGerritMapResult = []
            cnDeliveryGroupCommentResult = []
            cnDGToCNJiraIssueMapResult = []
            cnDGToCNProductToCNGerritMapRequiredFields  = cnDGToCNPipelineToCNGerritMapRequiredFields = cnDGToCNImageToCNGerritMapRequiredFields = ('cnGerrit__gerrit_link', 'cnDeliveryGroup__id','state__state','revert_change_id')
            cnDGToDGMapRequiredFields = ('cnDeliveryGroup__id', 'deliveryGroup__id', 'deliveryGroup__delivered', 'deliveryGroup__obsoleted', 'deliveryGroup__deleted')
            cnDGToCNJiraIssueMapRequiredFields = ('cnDeliveryGroup__id', 'cnJiraIssue__jiraNumber', 'cnJiraIssue__issueType')
            cnDeliveryGroupCommentRequiredFields = ('cnDeliveryGroup__id', 'comment', 'date')
            # get cn dg comment
            try:
                cnDeliveryGroupCommentObjList = CNDeliveryGroupComment.objects.filter(cnDeliveryGroup__id = group['id']).only(cnDeliveryGroupCommentRequiredFields).values(*cnDeliveryGroupCommentRequiredFields)
                for cnDeliveryGroupCommentObj in cnDeliveryGroupCommentObjList:
                    cnDeliveryGroupCommentResult.append(cnDeliveryGroupCommentObj)
                group['comments'] = cnDeliveryGroupCommentResult
            except Exception as e:
                errorMsg = "ERROR: Failed to CNDeliveryGroupComment data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
                logger.error(errorMsg)
                return result, errorMsg
            # get cn dg to cn image to gerrit map
            try:
                cnImageNameList = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id']).only('cnImage__image_name').values('cnImage__image_name').distinct()
                for cnImageName in cnImageNameList:
                    cnGerritList = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id'], cnImage__image_name = cnImageName["cnImage__image_name"]).values(*cnDGToCNImageToCNGerritMapRequiredFields)
                    tempObj = {}
                    tempObj[cnImageName["cnImage__image_name"]] = list(cnGerritList)
                    cnDGToCNImageToCNGerritMapResult.append(tempObj)
                group['serviceGroups'] = cnDGToCNImageToCNGerritMapResult
            except Exception as e:
                errorMsg = "ERROR: Failed to CNDGToCNImageToCNGerritMap data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
                logger.error(errorMsg)
                return result, errorMsg
            # get cn dg to cn product(integration chart) to gerrit map
            try:
                cnProductNameList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id'], cnProduct__product_type__product_type_name = "Integration Chart").values('cnProduct__product_name').distinct()
                for cnProductName in cnProductNameList:
                    cnGerritList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id'], cnProduct__product_name = cnProductName["cnProduct__product_name"]).values(*cnDGToCNProductToCNGerritMapRequiredFields)
                    tempObj = {}
                    tempObj[cnProductName["cnProduct__product_name"]] = list(cnGerritList)
                    cnDGToCNProductToCNGerritMapResult.append(tempObj)
                group['integrationCharts'] = cnDGToCNProductToCNGerritMapResult
            except Exception as e:
                errorMsg = "ERROR: Failed to CNDGToCNProductToCNGerritMap data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
                logger.error(errorMsg)
                return result, errorMsg
            # get cn dg to cn product(integration value) to gerrit map
            try:
                cnProductNameList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id'], cnProduct__product_type__product_type_name = "Integration Value").values('cnProduct__product_name').distinct()
                for cnProductName in cnProductNameList:
                    cnGerritList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id'], cnProduct__product_name = cnProductName["cnProduct__product_name"]).values(*cnDGToCNProductToCNGerritMapRequiredFields)
                    tempObj = {}
                    tempObj[cnProductName["cnProduct__product_name"]] = list(cnGerritList)
                    cnDGToIntegrationValueToCNGerritMapResult.append(tempObj)
                group['integrationValues'] = cnDGToIntegrationValueToCNGerritMapResult
            except Exception as e:
                errorMsg = "ERROR: Failed to CNDGToCNProductToCNGerritMap data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
                logger.error(errorMsg)
                return result, errorMsg
            # get cn dg to cn pipeline map
            try:
                cnPipelineNameList = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id']).values('cnPipeline__pipeline_link').distinct()
                for cnPipelineName in cnPipelineNameList:
                    cnGerritList = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__id = group['id'], cnPipeline__pipeline_link = cnPipelineName["cnPipeline__pipeline_link"]).values(*cnDGToCNProductToCNGerritMapRequiredFields)
                    tempObj = {}
                    tempObj[cnPipelineName["cnPipeline__pipeline_link"]] = list(cnGerritList)
                    cnDGToCNPipelineToCNGerritMapResult.append(tempObj)
                group['pipelines'] = cnDGToCNPipelineToCNGerritMapResult
            except Exception as e:
                errorMsg = "ERROR: Failed to CNDGToCNPipelineToCNGerritMap data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
                logger.error(errorMsg)
                return result, errorMsg
            # get cn dg to dg map
            try:
                cnDGToDGMapObjList = CNDGToDGMap.objects.filter(cnDeliveryGroup__id = group['id']).only(cnDGToDGMapRequiredFields).values(*cnDGToDGMapRequiredFields)
                for cnDGToDGMapObj in cnDGToDGMapObjList:
                    cnDGToDGMapResult.append(cnDGToDGMapObj)
                group['impactedENMDeliveryGroups'] = cnDGToDGMapResult
            except Exception as e:
                errorMsg = "ERROR: Failed to CNDGToDGMap data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
                logger.error(errorMsg)
                return result, errorMsg
            # get cn dg to cn jira issue map
            try:
                cnDGToCNJiraIssueMapObjList = CNDGToCNJiraIssueMap.objects.filter(cnDeliveryGroup__id = group['id']).only(cnDGToCNJiraIssueMapRequiredFields).values(*cnDGToCNJiraIssueMapRequiredFields)
                for cnDGToCNJiraIssueMapObj in cnDGToCNJiraIssueMapObjList:
                    jiraLink = identifyJiraInstance(cnDGToCNJiraIssueMapObj.get('cnJiraIssue__jiraNumber'))
                    cnDGToCNJiraIssueMapObj['jiraLink'] = jiraLink
                    cnDGToCNJiraIssueMapResult.append(cnDGToCNJiraIssueMapObj)
                group['jiraIssue'] = cnDGToCNJiraIssueMapResult
            except Exception as e:
                errorMsg = "ERROR: Failed to CNDGToCNJiraIssueMap data for getting cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
                logger.error(errorMsg)
                return result, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to get cn delivery groups data before rendering cn delivery queue page. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    result = {
        'cnDeliveryGroups': list(cnDeliveryGroups)
    }
    return result, errorMsg

@transaction.atomic
def deliverCNDeliveryGroup(deliveryGroupNumber, user, cnProductSetVersionNumber):
    '''
    This function is to deliver a cn delivery group by a given cn dg number.
    '''
    deliverCNDG_lock.acquire()
    errorMsg = None
    comment = None
    cnDeliveryGroupObj = None
    now = None
    result = None
    psUpdateErrorMsg = None
    try:
        sid = transaction.savepoint()
        try:
            cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        except Exception as e:
            errorMsg = "ERROR: Failed to get cn delivery group info before delivering a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            deliverCNDG_lock.release()
            return result, errorMsg
        if cnDeliveryGroupObj.delivered:
            errorMsg = "ERROR: Failed to deliver cn delivery group " + str(deliveryGroupNumber) + ". delivery group already delivered."
            deliverCNDG_lock.release()
            return result, errorMsg
        if not cnDeliveryGroupObj.queued:
            errorMsg = "ERROR: Failed to deliver cn delivery group " + str(deliveryGroupNumber) + ". Only queued delivery groups can be delivered."
            deliverCNDG_lock.release()
            return result, errorMsg
        comment = str(user.first_name) + " " + str(user.last_name) + " deliver this delivery group " + str(deliveryGroupNumber)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            mergeCNDG_thread = DGThread(cireports.cloudNativeUtils.mergeCNDeliveryGroupContent, args=(deliveryGroupNumber, comment))
            mergeCNDG_thread.start()
            mergeCNDG_thread.join()
            result, comment, errorMsg = mergeCNDG_thread.get_result()
        except Exception as e:
            errorMsg = "ERROR: Failed to deliver a delivery group  " + str(deliveryGroupNumber) + "while merging delivery group contents. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            deliverCNDG_lock.release()
            return result, errorMsg
        try:
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup=cnDeliveryGroupObj, comment=comment, date=now)
        except Exception as e:
            errorMsg = "ERROR: Failed to deliver a delivery group  " + str(deliveryGroupNumber) + "while adding comment. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            deliverCNDG_lock.release()
            return result, errorMsg
        if result == "delivered":
            try:
                cnDeliveryGroupObj.queued = False
                cnDeliveryGroupObj.obsoleted = False
                cnDeliveryGroupObj.deleted = False
                cnDeliveryGroupObj.delivered = True
                cnDeliveryGroupObj.deliveredDate = now
                cnDeliveryGroupObj.modifiedDate = now
                cnDeliveryGroupObj.save(force_update=True)
            except Exception as e:
                errorMsg = "ERROR: Failed to update cn delivery group status while delivering cn delivery group " + str(deliveryGroupNumber) + ". Please investigate: " + str(e)
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                deliverCNDG_lock.release()
                return result, errorMsg
            try:
                result, psUpdateErrorMsg = updateCNDeliveryGroupByCNProductSetVersion(cnProductSetVersionNumber, deliveryGroupNumber, user)
                if psUpdateErrorMsg:
                    errorMsg = psUpdateErrorMsg
                    transaction.savepoint_rollback(sid)
                    logger.error(errorMsg)
                    deliverCNDG_lock.release()
                    return result, errorMsg
            except Exception as e:
                errorMsg = "ERROR: Failed to deliver cn delivery group " + str(deliveryGroupNumber) + ". Failed to add cn product set version to this group Please investigate: " + str(e)
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                deliverCNDG_lock.release()
                return result, errorMsg
            result = 'SUCCESS'
            sendCnDgDeliveredEmail(deliveryGroupNumber,user,cnProductSetVersionNumber)
        else:
            cnDeliveryGroupObj.queued = True
            cnDeliveryGroupObj.obsoleted = False
            cnDeliveryGroupObj.deleted = False
            cnDeliveryGroupObj.delivered = False
            cnDeliveryGroupObj.save(force_update=True)
            sendCnDgDeliveryFailedEmail(deliveryGroupNumber,user)
        deliverCNDG_lock.release()
        return result, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to deliver a cn delivery group. Please investigate: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
        deliverCNDG_lock.release()
        return result, errorMsg

@transaction.atomic
def obsoleteCNDeliveryGroup(deliveryGroupNumber, user):
    '''
    This function is to obsolete a cn delivery group by a given cn dg number.
    '''
    obsoleteCNDG_lock.acquire()
    errorMsg = None
    comment = None
    cnDeliveryGroupObj = None
    cnProductRevisionObj = None
    now = None
    result = None
    revResult = None
    cnPsVersion = None
    csarVersion = None
    try:
        sid = transaction.savepoint()
        try:
            cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        except Exception as e:
            errorMsg = "ERROR: Failed to get cn delivery group info before obsoleting a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            obsoleteCNDG_lock.release()
            return result, errorMsg
        if cnDeliveryGroupObj.obsoleted:
            errorMsg = "ERROR: Failed to obsolete cn delivery group " + str(deliveryGroupNumber) + ". delivery group already obsoleted."
            obsoleteCNDG_lock.release()
            return result, errorMsg
        if cnDeliveryGroupObj.cnProductSetVersion:
            cnPsVersion = cnDeliveryGroupObj.cnProductSetVersion.product_set_version
        if not cnDeliveryGroupObj.delivered:
            errorMsg = "ERROR: Failed to obsolete cn delivery group " + str(deliveryGroupNumber) + ". Only delivered delivery groups can be obsoleted."
            obsoleteCNDG_lock.release()
            return result, errorMsg
        comment = str(user.first_name) + " " + str(user.last_name) + " obsoleted this delivery group " + str(deliveryGroupNumber) + " <br />"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Function to revert cn DG contents
        try:
            revertCNDG_thread = DGThread(cireports.cloudNativeUtils.revertCNDeliveryGroupContent, args=(deliveryGroupNumber, comment))
            revertCNDG_thread.start()
            revertCNDG_thread.join()
            revResult, comment, errorMsg = revertCNDG_thread.get_result()
        except Exception as e:
            errorMsg = "ERROR: Failed to obsolete a delivery group  " + str(deliveryGroupNumber) + "while reverting delivery group contents. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            obsoleteCNDG_lock.release()
            return result, errorMsg
        try:
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup=cnDeliveryGroupObj, comment=comment, date=now)
        except Exception as e:
            errorMsg = "ERROR: Failed to obsolete a delivery group  " + str(deliveryGroupNumber) + "while adding comment. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            obsoleteCNDG_lock.release()
            return result, errorMsg
        try:
            if revResult == "obsoleted":
                cnDeliveryGroupObj.queued = False
                cnDeliveryGroupObj.deleted = False
                cnDeliveryGroupObj.delivered = False
                cnDeliveryGroupObj.obsoleted = True
                cnDeliveryGroupObj.obsoletedDate = now
                cnDeliveryGroupObj.modifiedDate = now
            else:
                cnDeliveryGroupObj.queued = False
                cnDeliveryGroupObj.deleted = False
                cnDeliveryGroupObj.delivered = True
                cnDeliveryGroupObj.obsoleted = False
                revResult = "delivered"
            cnDeliveryGroupObj.save(force_update=True)
        except Exception as e:
            errorMsg = "ERROR: Failed to update cn delivery group status while obsoleting cn delivery group " + str(deliveryGroupNumber) + ". Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            obsoleteCNDG_lock.release()
            return result, errorMsg
        result = revResult
        if cnPsVersion and CNProductRevision.objects.filter(product_set_version__product_set_version = cnPsVersion, product__product_name = 'enm-installation-package').exists():
            cnProductRevisionObj = CNProductRevision.objects.get(product_set_version__product_set_version = cnPsVersion, product__product_name = 'enm-installation-package')
            csarVersion = cnProductRevisionObj.version
        if revResult == "obsoleted":
            updateCnDgInfoToJira(deliveryGroupNumber, cnPsVersion, "OBSOLETE")
            sendCnDgObsoleteOrRestoreOrDeleteEmail(deliveryGroupNumber, user, "OBSOLETE")
            if csarVersion:
                updateCnDgInfoToJira(deliveryGroupNumber, csarVersion, "CSAR OBSOLETE")
        else:
            sendCnDgObsoleteOrRestoreOrDeleteEmail(deliveryGroupNumber, user, "FAILED")
        obsoleteCNDG_lock.release()
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to obsolete a cn delivery group. Please investigate: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
        obsoleteCNDG_lock.release()
        return result, errorMsg
    return result, errorMsg

@transaction.atomic
def deleteCNDeliveryGroup(deliveryGroupNumber, user):
    '''
    This function is to delete a cn delivery group by a given cn dg number.
    '''
    errorMsg = None
    comment = None
    cnDeliveryGroupObj = None
    now = None
    result = None
    try:
        sid = transaction.savepoint()
        try:
            cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        except Exception as e:
            errorMsg = "ERROR: Failed to get cn delivery group info before deleting a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        if not cnDeliveryGroupObj.queued:
            errorMsg = "ERROR: Failed to delete cn delivery group " + str(deliveryGroupNumber) + ". Only queued delivery groups can be deleted."
            return result, errorMsg
        comment = str(user.first_name) + " " + str(user.last_name) + " deleted this delivery group " + str(deliveryGroupNumber)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup=cnDeliveryGroupObj, comment=comment, date=now)
        except Exception as e:
            errorMsg = "ERROR: Failed to delete a delivery group  " + str(deliveryGroupNumber) + "while adding comment. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        try:
            cnDeliveryGroupObj.queued = False
            cnDeliveryGroupObj.delivered = False
            cnDeliveryGroupObj.obsoleted = False
            cnDeliveryGroupObj.deleted = True
            cnDeliveryGroupObj.deletedDate = now
            cnDeliveryGroupObj.modifiedDate = now
            cnDeliveryGroupObj.save(force_update=True)
        except Exception as e:
            errorMsg = "ERROR: Failed to update cn delivery group status while deleting cn delivery group " + str(deliveryGroupNumber) + ". Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = 'SUCCESS'
        sendCnDgObsoleteOrRestoreOrDeleteEmail(deliveryGroupNumber,user,"DELETE")
        return result, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to delete a cn delivery group. Please investigate: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

@transaction.atomic
def restoreCNDeliveryGroup(deliveryGroupNumber, user):
    '''
    This function is to restore a cn delivery group by a given cn dg number.
    '''
    errorMsg = None
    comment = None
    cnDeliveryGroupObj = None
    now = None
    result = None
    try:
        sid = transaction.savepoint()
        try:
            cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        except Exception as e:
            errorMsg = "ERROR: Failed to get cn delivery group info before restoring a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        if cnDeliveryGroupObj.queued or cnDeliveryGroupObj.delivered:
            errorMsg = "ERROR: Failed to restore cn delivery group " + str(deliveryGroupNumber) + ". Only obsoleted and deleted delivery groups can be restored."
            return result, errorMsg
        comment = str(user.first_name) + " " + str(user.last_name) + " restored this delivery group " + str(deliveryGroupNumber)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup=cnDeliveryGroupObj, comment=comment, date=now)
        except Exception as e:
            errorMsg = "ERROR: Failed to restore a delivery group  " + str(deliveryGroupNumber) + "while adding comment. Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        try:
            cnDeliveryGroupObj.deleted = False
            cnDeliveryGroupObj.delivered = False
            cnDeliveryGroupObj.obsoleted = False
            cnDeliveryGroupObj.queued = True
            cnDeliveryGroupObj.modifiedDate = cnDeliveryGroupObj.createdDate
            cnDeliveryGroupObj.save(force_update=True)
            not_obsoleted_state = States.objects.get(state = "not_obsoleted")
            CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber).update(revert_change_id=None, state=not_obsoleted_state)
            CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber).update(revert_change_id=None, state=not_obsoleted_state)
            CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber).update(revert_change_id=None, state=not_obsoleted_state)
        except Exception as e:
            errorMsg = "ERROR: Failed to update cn delivery group status while restoring cn delivery group " + str(deliveryGroupNumber) + ". Please investigate: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = 'SUCCESS'
        sendCnDgObsoleteOrRestoreOrDeleteEmail(deliveryGroupNumber,user,"RESTORE")
        return result, errorMsg
    except Exception as e:
        errorMsg = "Unexpected ERROR: Failed to restore a cn delivery group. Please investigate: " + str(e)
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

def checkCNDeliveryQueueUserInfo(userName):
    '''
    This function is to check if users have filled in the profile.
    '''
    errorMsg = None
    user = None
    userGroup = None
    adminGroup = None
    try:
        if not User.objects.filter(username = userName).exists():
            errorMsg = "This user hasn't been registered on CI Portal. Please raise a support ticket on Engineering Tools Team."
        user = User.objects.get(username=userName)
        if str(user.username) == "AnonymousUser":
            errorMsg = "Please login to CI Portal"
        if str(user.first_name) == "" or str(user.last_name) == "" or str(user.email) == "":
            errorMsg = "This user does not have complete info registered in CI Portal. Please raise a support ticket on Engineering Tools Team."
            logger.error(errorMsg)
            return 1, errorMsg
    except Exception as e:
        errorMsg = "Failed to check user info for using cn Delivery Queue. Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def checkCNDropByDeliveryGroupNumber(deliveryGroupNumber):
    '''
    This function is to check if corresponding drop is active for a given delivery group number.
    '''
    errorMsg = None
    try:
        now = datetime.now()
        cnDropObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber).cnDrop
        if now < cnDropObj.active_date or cnDropObj.reopen is True:
            return 0, errorMsg
        else:
            errorMsg = "Drop is frozen. All the actions for cn Delivery Queue are disabled."
            return 1, errorMsg
    except Exception as e:
        errorMsg = "Failed to check cn drop status by a given delivery group number. Please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg

def getAllCNDrop(productName):
    '''
    This function is to get all the drops by cn product set name.
    '''
    errorMsg = None
    result = []
    try:
        cnDropObjList = CNDrop.objects.filter(cnProductSet__product_set_name = productName).order_by('-id')
        for cnDrop in cnDropObjList:
            result.append(cnDrop.name)
    except Excpetion as e:
        errorMsg = "Failed to get all cn drop info. Please investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def getServiceGroupInfo(deliveryGroupNumber):
    '''
    This function is to get service group data and its gerrit link data, drop data and team data
    '''
    errorMsg = None
    serviceGroupData = []
    teamData = None
    teamEmailId = None
    dropData = None
    result = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        dropData = str(cnDeliveryGroupObj.cnDrop.cnProductSet.product_set_name) + " " + str(cnDeliveryGroupObj.cnDrop.name)
        teamData = cnDeliveryGroupObj.component.element
        teamEmailId = cnDeliveryGroupObj.teamEmail
        cnImageNameList = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj).only('cnImage__image_name').values('cnImage__image_name').distinct()
        for cnImageName in cnImageNameList:
            tempResult = {"serviceGroupName": cnImageName["cnImage__image_name"], "gerritLinks": []}
            gerritLinkList = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnImage__image_name = cnImageName["cnImage__image_name"]).values('cnGerrit__gerrit_link')
            for gerritLink in gerritLinkList:
                tempResult["gerritLinks"].append(gerritLink["cnGerrit__gerrit_link"])
            serviceGroupData.append(tempResult)
        result = {'serviceGroups': serviceGroupData, 'drop': dropData, 'team': teamData, 'teamEmail': teamEmailId }
    except Exception as e:
        errorMsg = "Failed to get data for rendering the page for editing service groups. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

def getIntegrationChartInfo(deliveryGroupNumber):
    '''
    This function is to get integration chart data and its gerrit link data, drop data and team data
    '''
    errorMsg = None
    integrationChartData = []
    dropData = None
    result = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        dropData = str(cnDeliveryGroupObj.cnDrop.cnProductSet.product_set_name) + " " + str(cnDeliveryGroupObj.cnDrop.name)
        integrationChartNameList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct__product_type__product_type_name = "Integration Chart").only('cnProduct__product_name').values('cnProduct__product_name').distinct()
        for integrationChartName in integrationChartNameList:
            tempResult = {"integrationChartName": integrationChartName["cnProduct__product_name"], "gerritLinks": []}
            gerritLinkList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct__product_name = integrationChartName["cnProduct__product_name"]).values('cnGerrit__gerrit_link')
            for gerritLink in gerritLinkList:
                tempResult["gerritLinks"].append(gerritLink["cnGerrit__gerrit_link"])
            integrationChartData.append(tempResult)
        result = {'integrationCharts': integrationChartData, 'drop': dropData }
    except Exception as e:
        errorMsg = "Failed to get data for rendering the page for editing integration charts. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

def getIntegrationValueInfo(deliveryGroupNumber):
    '''
    This function is to get integration value data and its gerrit link data, drop data and team data
    '''
    errorMsg = None
    integrationValueData = []
    dropData = None
    result = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        dropData = str(cnDeliveryGroupObj.cnDrop.cnProductSet.product_set_name) + " " + str(cnDeliveryGroupObj.cnDrop.name)
        integrationValueNameList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct__product_type__product_type_name = "Integration Value").only('cnProduct__product_name').values('cnProduct__product_name').distinct()
        for integrationValueName in integrationValueNameList:
            tempResult = {"integrationValueName": integrationValueName["cnProduct__product_name"], "gerritLinks": []}
            gerritLinkList = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct__product_name = integrationValueName["cnProduct__product_name"]).values('cnGerrit__gerrit_link')
            for gerritLink in gerritLinkList:
                tempResult["gerritLinks"].append(gerritLink["cnGerrit__gerrit_link"])
            integrationValueData.append(tempResult)
        result = {'integrationValues': integrationValueData, 'drop': dropData }
    except Exception as e:
        errorMsg = "Failed to get data for rendering the page for editing integration values. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

def getPipelineInfo(deliveryGroupNumber):
    '''
    This function is to get pipeline data and its gerrit link data, drop data and team data
    '''
    errorMsg = None
    pipelineData = []
    dropData = None
    result = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        dropData = str(cnDeliveryGroupObj.cnDrop.cnProductSet.product_set_name) + " " + str(cnDeliveryGroupObj.cnDrop.name)
        pipelineNameList = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj).only('cnPipeline__pipeline_link').values('cnPipeline__pipeline_link').distinct()
        for pipelineName in pipelineNameList:
            tempResult = {"pipelineName": pipelineName["cnPipeline__pipeline_link"], "gerritLinks": []}
            gerritLinkList = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnPipeline__pipeline_link = pipelineName["cnPipeline__pipeline_link"]).values('cnGerrit__gerrit_link')
            for gerritLink in gerritLinkList:
                tempResult["gerritLinks"].append(gerritLink["cnGerrit__gerrit_link"])
            pipelineData.append(tempResult)
        result = {'pipelines': pipelineData, 'drop': dropData }
    except Exception as e:
        errorMsg = "Failed to get data for rendering the page for editing pipelines. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

@transaction.atomic
def editCNDeliveryGroup(data, deliveryGroupNumber, user, dropName):
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        cnImageGerritListInDrop = CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__cnDrop__name = dropName, cnDeliveryGroup__deleted = 0).values_list('cnGerrit__gerrit_link', flat = True)
        cnProductGerritListInDrop = CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__cnDrop__name = dropName, cnDeliveryGroup__deleted = 0).values_list('cnGerrit__gerrit_link', flat = True)
        cnPipelineGerritListInDrop = CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__cnDrop__name = dropName, cnDeliveryGroup__deleted = 0).values_list('cnGerrit__gerrit_link', flat = True)
        cnDgsGerritListInDrop = list(chain(cnImageGerritListInDrop, cnProductGerritListInDrop, cnPipelineGerritListInDrop))
        if data['is_service_group_edited']:
            result, errorMsg = updateServiceGroupInfo(data['serviceGroupBeforeEdit'], data['serviceGroupAfterEdit'], user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
            if errorMsg:
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                return result, errorMsg
        if data['is_integration_chart_edited']:
            result, errorMsg = updateIntegrationChartInfo(data['integrationChartBeforeEdit'], data['integrationChartAfterEdit'], user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
            if errorMsg:
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                return result, errorMsg
        if data['is_integration_value_edited']:
            result, errorMsg = updateIntegrationValueInfo(data['integrationValueBeforeEdit'], data['integrationValueAfterEdit'], user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
            if errorMsg:
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                return result, errorMsg
        if data['is_pipeline_edited']:
            result, errorMsg = updatePipelineInfo(data['pipelineBeforeEdit'], data['pipelineAfterEdit'], user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
            if errorMsg:
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                return result, errorMsg
        if data['is_impacted_dg_edited']:
            result, errorMsg = updateImpactedDeliveryGroupInfo(data['impactedDGBeforeEdit'], data['impactedDGAfterEdit'], user, deliveryGroupNumber, "CENM")
            if errorMsg:
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                return result, errorMsg
        if data['is_jira_edited']:
            result, errorMsg = updateJiraInfo(data['jiraBeforeEdit'], data['jiraAfterEdit'], user, deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                transaction.savepoint_rollback(sid)
                return result, errorMsg
        result = deliveryGroupNumber
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to update cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg

@transaction.atomic
def updateServiceGroupInfo(beforeEdit, afterEdit, user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to update service group data and its gerrit link data and team data by a given delivery group number
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        # remove sg
        removeSgStatus, removeSgErrorMsg = updateSgInfo_removeServiceGroups(beforeEdit, afterEdit, deliveryGroupNumber)
        if removeSgErrorMsg:
            errorMsg = removeSgErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # update team data
        updateTeamStatus, updateTeamErrorMsg = updateSgInfo_updateTeamData(beforeEdit, afterEdit, deliveryGroupNumber)
        if updateTeamErrorMsg:
            errorMsg = updateTeamErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # update team email data
        updateTeamEmailStatus, updateTeamEmailErrorMsg = updateSgInfo_updateTeamEmailData(beforeEdit, afterEdit, deliveryGroupNumber)
        if updateTeamEmailErrorMsg:
            errorMsg = updateTeamEmailErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # update gerrit link for an existing sg
        updateGrtStatus, updateGrtErrorMsg = updateSgInfo_updateGerritLinks(beforeEdit, afterEdit, deliveryGroupNumber, dropName)
        if updateGrtErrorMsg:
            errorMsg = updateGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add sg and its gerrit link
        addSgGrtStatus, addSgGrtErrorMsg = updateSgInfo_addServiceGroups_addGerritLinks(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
        if addSgGrtErrorMsg:
            errorMsg = addSgGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add comment for editing data
        addCommentStatus, addCommentErrorMsg = updateSgInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber)
        if addCommentErrorMsg:
            errorMsg = addCommentErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = deliveryGroupNumber
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to update service group info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg

def updateSgInfo_removeServiceGroups(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to remove service group data by a given cn dg number if newly edited service groups do not have old service group data.
    '''
    errorMsg = None
    afterEdit_serviceGroupNameList = []
    try:
        for serviceGroup in afterEdit["serviceGroups"]:
            afterEdit_serviceGroupNameList.append(serviceGroup["serviceGroupName"])
        for serviceGroup in beforeEdit["serviceGroups"]:
            if serviceGroup["serviceGroupName"] not in afterEdit_serviceGroupNameList:
                CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnImage__image_name = serviceGroup["serviceGroupName"]).delete()
    except Exception as e:
        errorMsg = "Failed to remove service group info while updating service group info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateSgInfo_updateTeamData(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to update team data if team is updated while updating service group info
    '''
    errorMsg = None
    oldTeam = None
    newTeam = None
    try:
        oldTeam = str(beforeEdit["team"])
        newTeam = str(afterEdit["team"])
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        if newTeam != oldTeam:
            # update new team data
            teamObj = Component.objects.get(element = newTeam, deprecated = False)
            cnDeliveryGroupObj.component = teamObj
            cnDeliveryGroupObj.save(force_update=True)
    except Exception as e:
        errorMsg = "Failed to update team data while updating service group info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateSgInfo_updateTeamEmailData(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to update team email data if team email is updated while updating service group info
    '''
    errorMsg = None
    oldTeamEmail = None
    newTeamEmail = None
    emailValidation = '@'
    try:
        oldTeamEmail = str(beforeEdit["teamEmail"])
        newTeamEmail = str(afterEdit["teamEmail"])
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        if newTeamEmail != oldTeamEmail:
            # update new team email data
            if newTeamEmail == "":
                newTeamEmail = None
            elif newTeamEmail != "" and emailValidation not in newTeamEmail:
                errorMsg = "ERROR: Invalid Team Email Id format"
                return 1, errorMsg
            cnDeliveryGroupObj.teamEmail = newTeamEmail
            cnDeliveryGroupObj.save(force_update=True)
    except Exception as e:
        errorMsg = "Failed to update team email data while updating service group info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateSgInfo_updateGerritLinks(beforeEdit, afterEdit, deliveryGroupNumber, dropName):
    '''
    This function is to add/remove gerrit link data for an existing service group by a given cn dg number if newly edited service groups do not have old gerrit link data
    '''
    errorMsg = None
    cnImage_afterEdit = {}
    for serviceGroup_afterEdit in afterEdit["serviceGroups"]:
        cnImage_afterEdit["gerritList"] = serviceGroup_afterEdit["gerritLinks"]
        try:
            result, errorMsg = checkCnDgReadyToCreate(cnImage_afterEdit, dropName)
            if errorMsg:
                return 1, errorMsg
        except Exception as e:
            errorMsg = "ERROR: Failed to check service groups and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return 1, errorMsg
    try:
        for serviceGroup_beforeEdit in beforeEdit["serviceGroups"]:
            for serviceGroup_afterEdit in afterEdit["serviceGroups"]:
                if serviceGroup_beforeEdit["serviceGroupName"] == serviceGroup_afterEdit["serviceGroupName"]:
                    # same sg found
                    for gerritLink_beforeEdit in serviceGroup_beforeEdit["gerritLinks"]:
                        if gerritLink_beforeEdit not in serviceGroup_afterEdit["gerritLinks"]:
                            # remove old link as the link is deleted in new data
                            CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnImage__image_name = serviceGroup_beforeEdit["serviceGroupName"], cnGerrit__gerrit_link = gerritLink_beforeEdit).delete()
                    for gerritLink_afterEdit in serviceGroup_afterEdit["gerritLinks"]:
                        if gerritLink_afterEdit not in serviceGroup_beforeEdit["gerritLinks"]:
                            # add new link as the link is added in new data
                            if not CNGerrit.objects.filter(gerrit_link = gerritLink_afterEdit).exists():
                                cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink_afterEdit)
                                cnImageObj = CNImage.objects.get(image_name = serviceGroup_beforeEdit["serviceGroupName"])
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNImageToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnImage = cnImageObj, cnGerrit = cnGerritObj)
                            else:
                                cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink_afterEdit)
                                cnImageObj = CNImage.objects.get(image_name = serviceGroup_beforeEdit["serviceGroupName"])
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNImageToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnImage = cnImageObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to update gerrit link info while updating service group info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateSgInfo_addServiceGroups_addGerritLinks(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to add/remove service group and its gerrit link data for a new service group by a given cn dg number.
    '''
    errorMsg = None
    beforeEdit_serviceGroupNameList = []
    afterEdit_serviceGroupNameList = []
    newServiceGroupNameList = []
    cnImage_afterEdit = {}
    try:
        isDuplicate, duplicateCNImageName, errorMsg = checkDuplicateCNImageName(afterEdit["serviceGroups"], 'serviceGroupName')
        if isDuplicate or errorMsg:
            errorMsg = "ERROR: Failed to add service group data while updating a delivery group: Duplicate service group found: " + duplicateCNImageName
            return 1, errorMsg
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        for serviceGroup_beforeEdit in beforeEdit["serviceGroups"]:
            beforeEdit_serviceGroupNameList.append(serviceGroup_beforeEdit["serviceGroupName"])
        for serviceGroup_afterEdit in afterEdit["serviceGroups"]:
            afterEdit_serviceGroupNameList.append(serviceGroup_afterEdit["serviceGroupName"])
        for sgName_afterEdit in afterEdit_serviceGroupNameList:
            if sgName_afterEdit not in beforeEdit_serviceGroupNameList:
                newServiceGroupNameList.append(sgName_afterEdit)
        for serviceGroup_afterEdit in afterEdit["serviceGroups"]:
            if serviceGroup_afterEdit["serviceGroupName"] in newServiceGroupNameList:
                cnImage_afterEdit["gerritList"] = serviceGroup_afterEdit["gerritLinks"]
                try:
                    result, errorMsg = checkDuplicateGerritLink(cnImage_afterEdit, cnDgsGerritListInDrop)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    result, errorMsg = checkCnDgReadyToCreate(cnImage_afterEdit, dropName)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check service groups and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
        for serviceGroup_afterEdit in afterEdit["serviceGroups"]:
            if serviceGroup_afterEdit["serviceGroupName"] in newServiceGroupNameList:
                cnImageObj = CNImage.objects.get(image_name = serviceGroup_afterEdit["serviceGroupName"])
                for gerritLink in serviceGroup_afterEdit["gerritLinks"]:
                    if not CNGerrit.objects.filter(gerrit_link = gerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink)
                        CNDGToCNImageToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnImage = cnImageObj, cnGerrit = cnGerritObj)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink)
                        CNDGToCNImageToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnImage = cnImageObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to add service group and gerrit link data while updating service group info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateSgInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber):
    '''
    This function is to add comment for a given dg group number after editing service group data.
    '''
    errorMsg = None
    editComment = None
    beforeEditComment = None
    afterEditComment = None
    now = None
    try:
        now = datetime.now()
        userObj = User.objects.get(username=user)
        editComment = str(userObj.first_name) + " " + str(userObj.last_name) + " edited service groups for delivery group " + str(deliveryGroupNumber)
        beforeEditComment = "<p><b>Before Edit:</b></p>"
        beforeEditComment += "<p> Team: " + str(beforeEdit["team"]) + "<p/>"
        beforeEditComment += "<p> Team Email: " + str(beforeEdit["teamEmail"]) + "<p/>"
        for serviceGroup in beforeEdit["serviceGroups"]:
            beforeEditComment += "<p> Service Group: " + serviceGroup["serviceGroupName"] + "</p>"
            for gerritLink in serviceGroup["gerritLinks"]:
                beforeEditComment += gerritLink + "<br />"
            beforeEditComment += "<br />"
        afterEditComment = "<p><b>After Edit:</b></p>"
        afterEditComment += "<p> Team: " + str(afterEdit["team"]) + "<p/>"
        afterEditComment += "<p> Team Email: " + str(afterEdit["teamEmail"]) + "<p/>"
        for serviceGroup in afterEdit["serviceGroups"]:
            afterEditComment += "<p> Service Group: " + serviceGroup["serviceGroupName"] + "</p>"
            for gerritLink in serviceGroup["gerritLinks"]:
                afterEditComment += gerritLink + "<br />"
            afterEditComment += "<br />"
        # create 3 comments: editComment, beforeEditComment, afterEditComment
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = editComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = beforeEditComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = afterEditComment, date = now)
    except Exception as e:
        errorMsg = "Failed to add comment while updating service group info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

@transaction.atomic
def updateCNDeliveryGroupByCNProductSetVersion(productSetVersionNumber, deliveryGroupNumber, user):
    '''
    This function is to udpates a delivery group with a existing produt set version.
    '''
    deliveryGroupObj = None
    cnProductSetVersionObj = None
    cnProductRevisionObj = None
    errorMsg = None
    currDate = None
    cnProductSetVersionValueSet = 0
    try:
        sid = transaction.savepoint()
        currDate = datetime.now()
        try:
            deliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        except Exception as e:
            errorMsg = "Failed to update a cn delivery group with a cn product set version. please investigate: can't find cn delivery group info."
            logger.error(errorMsg)
            return 1, errorMsg
        if not deliveryGroupObj.delivered:
            errorMsg = "Failed to update a cn delivery group with a cn product set version. please investigate: only delivered delivery group can be updated with product set version"
            logger.error(errorMsg)
            return 1, errorMsg
        try:
            if productSetVersionNumber:
                if not CNProductSetVersion.objects.filter(drop_version=deliveryGroupObj.cnDrop.name,product_set_version = productSetVersionNumber).exists():
                    errorMsg = "Failed to update a cn delivery group with a cn product set version. please investigate: Wrong product set version for the drop"
                    logger.error(errorMsg)
                    return 1, errorMsg
                cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = productSetVersionNumber)
                cnProductSetVersionValueSet = 1
                updateCnDgInfoToJira(deliveryGroupNumber, productSetVersionNumber, "DELIVERED")
                comment = user.first_name + " " + user.last_name + " updated this delivery group with cn product set version " + str(productSetVersionNumber)
                if CNProductRevision.objects.filter(product_set_version__product_set_version = productSetVersionNumber, product__product_name = 'enm-installation-package').exists():
                    cnProductRevisionObj = CNProductRevision.objects.get(product_set_version__product_set_version = productSetVersionNumber, product__product_name = 'enm-installation-package')
                    csarVersion = cnProductRevisionObj.version
                    updateCnDgInfoToJira(deliveryGroupNumber, csarVersion, "CSAR DELIVERED")
            else:
                cnProductSetVersionObj = None
                comment = user.first_name + " " + user.last_name + " updated this delivery group with empty cn product set version "
        except Exception as e:
            errorMsg = "Failed to update a cn delivery group with a cn product set version. please investigate: can't find cn product set version info."
            logger.error(errorMsg)
            return 1, errorMsg
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = deliveryGroupObj, comment = comment, date = currDate)
        deliveryGroupObj.cnProductSetVersion = cnProductSetVersionObj
        deliveryGroupObj.cnProductSetVersionSet = cnProductSetVersionValueSet
        deliveryGroupObj.save(force_update=True)
        return 0, errorMsg
    except Exception as e:
        errorMsg = "Failed to update a cn delivery group with a cn product set version. please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return 1, errorMsg

@transaction.atomic
def autoUpdateCnDgProductSet(psversion, dropVersion):
    '''
    This function is to automatically udpate a delivery group with a produt set version, when a new PS is created.
    '''
    deliveryGroupObj = None
    cnProductSetVersionObj = None
    errorMsg = None
    currDate = None
    try:
        sid = transaction.savepoint()
        currDate = datetime.now()
        cnProductSetVersionObj = CNProductSetVersion.objects.get(product_set_version = psversion)
        try:
            cnDeliveryGroupList = CNDeliveryGroup.objects.filter(cnDrop__name = dropVersion, delivered = 1, cnProductSetVersionSet = 0).values('id')
        except Exception as e:
            errorMsg = "Failed to get a cn delivery group list for the drop. Please investigate: can't find cn delivery group info."
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
        if cnDeliveryGroupList:
            for cnDeliveryGroups in cnDeliveryGroupList:
                deliveryGroupNumber = cnDeliveryGroups.get('id')
                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                try:
                    CNDeliveryGroup.objects.filter(id = deliveryGroupNumber).update(cnProductSetVersion = cnProductSetVersionObj, cnProductSetVersionSet = 1)
                    comment = "Automatically updated this delivery group with cn product set version " + str(psversion)
                    updateCnDgInfoToJira(deliveryGroupNumber, psversion, "DELIVERED")
                except Exception as e:
                    errorMsg = "Failed to update a cn delivery group with a cn product set version. Please investigate: " + str(e)
                    comment = errorMsg
                    logger.error(errorMsg)
                    transaction.savepoint_rollback(sid)
                CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = comment, date = currDate)
    except Exception as e:
        errorMsg = "Failed to update a cn delivery group with a cn product set version. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)

def updateCnDgInfoToJira(deliveryGroupNumber, psversion, cnDgProcess):
    '''
    This function is to automatically udpate a delivery group info to its associated JIRA tickets.
    '''
    content = ''
    try:
        if psversion:
            if cnDgProcess == "DELIVERED":
                content = "In DG " + str(deliveryGroupNumber) + ", Included in cENM Product Set Version " + str(psversion)
            elif cnDgProcess == "OBSOLETE":
                content = "In DG " + str(deliveryGroupNumber) + ", Obsoleted from cENM Product Set Version " + str(psversion)
            elif cnDgProcess == "CSAR DELIVERED":
                content = "In DG " + str(deliveryGroupNumber) + ", Included in CSAR enm-installation-package version " + str(psversion)
            elif cnDgProcess == "CSAR OBSOLETE":
                content = "In DG " + str(deliveryGroupNumber) + ", Obsoleted from CSAR enm-installation-package version " + str(psversion)
        else:
            content = "Included in DG " + str(deliveryGroupNumber)
        cnJiraList = CNDGToCNJiraIssueMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber).values('cnJiraIssue__jiraNumber').distinct()
        for cnJira in cnJiraList:
            jira = cnJira.get('cnJiraIssue__jiraNumber')
            result = addCommentToJira(content,jira)
            logger.info(result)
    except Exception as e:
        errorMsg = "Failed to update a cn delivery group info to JIRA. please investigate: " + str(e)
        logger.error(errorMsg)

def deleteServiceGroupInfo(userName, deliveryGroupNumber, serviceGroupInfo):
    '''
    This function is to remove service group data and its gerrit link data and team data by a given delivery group number
    '''
    errorMsg = None
    serviceGroupName = None
    gerritList = None
    deliveryGroupObj = None
    user = None
    now = None
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        serviceGroupName = serviceGroupInfo["imageName"]
        # incoming data is not list but str
        gerritList = serviceGroupInfo["gerritList"].split(",")
        deliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        user = User.objects.get(username = userName)
        comment = user.first_name + " " + user.last_name + " removed " + str(serviceGroupName) + " <br /> <b> Gerrit Data: <b/> <br /> "
        for gerritLink in gerritList:
            if CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnImage__image_name = serviceGroupName, cnGerrit__gerrit_link = gerritLink).exists():
                CNDGToCNImageToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnImage__image_name = serviceGroupName, cnGerrit__gerrit_link = gerritLink).delete()
                comment += gerritLink + "<br />"
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = deliveryGroupObj, comment = comment, date = now)
        return "SUCCESS", errorMsg
    except Exception as e:
        errorMsg = "Failed to remove service group info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)

@transaction.atomic
def updateIntegrationChartInfo(beforeEdit, afterEdit, user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to update integration chart data and its gerrit link data by a given delivery group number
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        # remove sg
        removeSgStatus, removeSgErrorMsg = updateInteInfo_removeIntegrationChart(beforeEdit, afterEdit, deliveryGroupNumber)
        if removeSgErrorMsg:
            errorMsg = removeSgErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # update gerrit link for an existing sg
        updateGrtStatus, updateGrtErrorMsg = updateInteInfo_updateGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName)
        if updateGrtErrorMsg:
            errorMsg = updateGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add sg and its gerrit link
        addSgGrtStatus, addSgGrtErrorMsg = updateInteInfo_addIntegrationChart_addGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
        if addSgGrtErrorMsg:
            errorMsg = addSgGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add comment for editing data
        addCommentStatus, addCommentErrorMsg = updateInteInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber)
        if addCommentErrorMsg:
            errorMsg = addCommentErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = deliveryGroupNumber
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to update integration chart info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg

def updateInteInfo_removeIntegrationChart(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to remove integration chart data by a given cn dg number if newly edited integraion charts do not have old integration chart data.
    '''
    errorMsg = None
    afterEdit_integrationChartNameList = []
    try:
        for integrationChart in afterEdit["integrationCharts"]:
            afterEdit_integrationChartNameList.append(integrationChart["integrationChartName"])
        for integrationChart in beforeEdit["integrationCharts"]:
            if integrationChart["integrationChartName"] not in afterEdit_integrationChartNameList:
                CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnProduct__product_name = integrationChart["integrationChartName"]).delete()
    except Exception as e:
        errorMsg = "Failed to remove integration chart info while updating integration chart info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateInteInfo_updateGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName):
    '''
    This function is to add/remove gerrit link data for an existing integration chart by a given cn dg number if newly edited integration charts do not have old gerrit link data
    '''
    errorMsg = None
    cnInteChart_afterEdit = {}
    for integrationChart_afterEdit in afterEdit["integrationCharts"]:
        cnInteChart_afterEdit["gerritList"] = integrationChart_afterEdit["gerritLinks"]
        try:
            result, errorMsg = checkCnDgReadyToCreate(cnInteChart_afterEdit, dropName)
            if errorMsg:
                return 1, errorMsg
        except Exception as e:
            errorMsg = "ERROR: Failed to check integration chart and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return 1, errorMsg
    try:
        for integrationChart_beforeEdit in beforeEdit["integrationCharts"]:
            for integrationChart_afterEdit in afterEdit["integrationCharts"]:
                if integrationChart_beforeEdit["integrationChartName"] == integrationChart_afterEdit["integrationChartName"]:
                    for gerritLink_beforeEdit in integrationChart_beforeEdit["gerritLinks"]:
                        if gerritLink_beforeEdit not in integrationChart_afterEdit["gerritLinks"]:
                            CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnProduct__product_name = integrationChart_beforeEdit["integrationChartName"], cnGerrit__gerrit_link = gerritLink_beforeEdit).delete()
                    for gerritLink_afterEdit in integrationChart_afterEdit["gerritLinks"]:
                        if gerritLink_afterEdit not in integrationChart_beforeEdit["gerritLinks"]:
                            if not CNGerrit.objects.filter(gerrit_link = gerritLink_afterEdit).exists():
                                cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink_afterEdit)
                                cnProductObj = CNProduct.objects.get(product_name = integrationChart_beforeEdit["integrationChartName"], product_type__product_type_name = "Integration Chart")
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
                            else:
                                cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink_afterEdit)
                                cnProductObj = CNProduct.objects.get(product_name = integrationChart_beforeEdit["integrationChartName"], product_type__product_type_name = "Integration Chart")
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to update integration chart info while updating integration chart info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateInteInfo_addIntegrationChart_addGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to add/remove integration chart and its gerrit link data for a new integration chart by a given cn dg number.
    '''
    errorMsg = None
    beforeEdit_integrationChartNameList = []
    afterEdit_integrationChartNameList = []
    newIntegrationChartNameList = []
    cnInteChart_afterEdit = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        for integrationChart_beforeEdit in beforeEdit["integrationCharts"]:
            beforeEdit_integrationChartNameList.append(integrationChart_beforeEdit["integrationChartName"])
        for integrationChart_afterEdit in afterEdit["integrationCharts"]:
            afterEdit_integrationChartNameList.append(integrationChart_afterEdit["integrationChartName"])
        for integrationChart_afterEdit in afterEdit_integrationChartNameList:
            if integrationChart_afterEdit not in beforeEdit_integrationChartNameList:
                newIntegrationChartNameList.append(integrationChart_afterEdit)
        for integrationChart_afterEdit in afterEdit["integrationCharts"]:
            if integrationChart_afterEdit["integrationChartName"] in newIntegrationChartNameList:
                cnInteChart_afterEdit["gerritList"] = integrationChart_afterEdit["gerritLinks"]
                try:
                    result, errorMsg = checkDuplicateGerritLink(cnInteChart_afterEdit, cnDgsGerritListInDrop)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    result, errorMsg = checkCnDgReadyToCreate(cnInteChart_afterEdit, dropName)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check integration chart and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
        for integrationChart_afterEdit in afterEdit["integrationCharts"]:
            if integrationChart_afterEdit["integrationChartName"] in newIntegrationChartNameList:
                cnProductObj = CNProduct.objects.get(product_name = integrationChart_afterEdit["integrationChartName"], product_type__product_type_name = "Integration Chart")
                for gerritLink in integrationChart_afterEdit["gerritLinks"]:
                    if not CNGerrit.objects.filter(gerrit_link = gerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink)
                        CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink)
                        CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to add integration chart and gerrit link data while updating integration chart info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateInteInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber):
    '''
    This function is to add comment for a given dg group number after editing integration chart data.
    '''
    errorMsg = None
    editComment = None
    beforeEditComment = None
    afterEditComment = None
    now = None
    try:
        now = datetime.now()
        userObj = User.objects.get(username=user)
        editComment = str(userObj.first_name) + " " + str(userObj.last_name) + " edited integration chart info for delivery group " + str(deliveryGroupNumber)
        beforeEditComment = "<p><b>Before Edit:</b></p>"
        for integrationChart in beforeEdit["integrationCharts"]:
            beforeEditComment += "<p> Integration Chart: " + integrationChart["integrationChartName"] + "</p>"
            for gerritLink in integrationChart["gerritLinks"]:
                beforeEditComment += gerritLink + "<br />"
            beforeEditComment += "<br />"
        afterEditComment = "<p><b>After Edit:</b></p>"
        for integrationChart in afterEdit["integrationCharts"]:
            afterEditComment += "<p> Integration Chart: " + integrationChart["integrationChartName"] + "</p>"
            for gerritLink in integrationChart["gerritLinks"]:
                afterEditComment += gerritLink + "<br />"
            afterEditComment += "<br />"
        # create 3 comments: editComment, beforeEditComment, afterEditComment
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = editComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = beforeEditComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = afterEditComment, date = now)
    except Exception as e:
        errorMsg = "Failed to add comment while updating integration chart info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg


@transaction.atomic
def updateIntegrationValueInfo(beforeEdit, afterEdit, user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to update integration value data and its gerrit link data by a given delivery group number
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        # remove integration value
        removeSgStatus, removeSgErrorMsg = updateInteInfo_removeIntegrationValue(beforeEdit, afterEdit, deliveryGroupNumber)
        if removeSgErrorMsg:
            errorMsg = removeSgErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # update gerrit link for an existing integration value
        updateGrtStatus, updateGrtErrorMsg = updateInteValueInfo_updateGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName)
        if updateGrtErrorMsg:
            errorMsg = updateGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add sg and its gerrit link
        addSgGrtStatus, addSgGrtErrorMsg = updateInteInfo_addIntegrationValue_addGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
        if addSgGrtErrorMsg:
            errorMsg = addSgGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add comment for editing data
        addCommentStatus, addCommentErrorMsg = updateInteValueInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber)
        if addCommentErrorMsg:
            errorMsg = addCommentErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = deliveryGroupNumber
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to update integration value info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg

def updateInteInfo_removeIntegrationValue(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to remove integration value data by a given cn dg number if newly edited integraion values do not have old integration value data.
    '''
    errorMsg = None
    afterEdit_integrationValueNameList = []
    try:
        for integrationValue in afterEdit["integrationValues"]:
            afterEdit_integrationValueNameList.append(integrationValue["integrationValueName"])
        for integrationValue in beforeEdit["integrationValues"]:
            if integrationValue["integrationValueName"] not in afterEdit_integrationValueNameList:
                CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnProduct__product_name = integrationValue["integrationValueName"]).delete()
    except Exception as e:
        errorMsg = "Failed to remove integration value info while updating integration value info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateInteValueInfo_updateGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName):
    '''
    This function is to add/remove gerrit link data for an existing integration value by a given cn dg number if newly edited integration values do not have old gerrit link data
    '''
    errorMsg = None
    cnInteValue_afterEdit = {}
    for integrationValue_afterEdit in afterEdit["integrationValues"]:
        cnInteValue_afterEdit["gerritList"] = integrationValue_afterEdit["gerritLinks"]
        try:
            result, errorMsg = checkCnDgReadyToCreate(cnInteValue_afterEdit, dropName)
            if errorMsg:
                return 1, errorMsg
        except Exception as e:
            errorMsg = "ERROR: Failed to check integaration value file and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return 1, errorMsg
    try:
        for integrationValue_beforeEdit in beforeEdit["integrationValues"]:
            for integrationValue_afterEdit in afterEdit["integrationValues"]:
                if integrationValue_beforeEdit["integrationValueName"] == integrationValue_afterEdit["integrationValueName"]:
                    for gerritLink_beforeEdit in integrationValue_beforeEdit["gerritLinks"]:
                        if gerritLink_beforeEdit not in integrationValue_afterEdit["gerritLinks"]:
                            CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnProduct__product_name = integrationValue_beforeEdit["integrationValueName"], cnGerrit__gerrit_link = gerritLink_beforeEdit).delete()
                    for gerritLink_afterEdit in integrationValue_afterEdit["gerritLinks"]:
                        if gerritLink_afterEdit not in integrationValue_beforeEdit["gerritLinks"]:
                            if not CNGerrit.objects.filter(gerrit_link = gerritLink_afterEdit).exists():
                                cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink_afterEdit)
                                cnProductObj = CNProduct.objects.get(product_name = integrationValue_beforeEdit["integrationValueName"], product_type__product_type_name = "Integration Value")
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
                            else:
                                cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink_afterEdit)
                                cnProductObj = CNProduct.objects.get(product_name = integrationValue_beforeEdit["integrationValueName"], product_type__product_type_name = "Integration Value")
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to update integration value info while updating integration value info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg


def updateInteInfo_addIntegrationValue_addGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to add/remove integration value and its gerrit link data for a new integration value by a given cn dg number.
    '''
    errorMsg = None
    beforeEdit_integrationValueNameList = []
    afterEdit_integrationValueNameList = []
    newIntegrationValueNameList = []
    cnInteValue_afterEdit = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        for integrationValue_beforeEdit in beforeEdit["integrationValues"]:
            beforeEdit_integrationValueNameList.append(integrationValue_beforeEdit["integrationValueName"])
        for integrationValue_afterEdit in afterEdit["integrationValues"]:
            afterEdit_integrationValueNameList.append(integrationValue_afterEdit["integrationValueName"])
        for integrationValue_afterEdit in afterEdit_integrationValueNameList:
            if integrationValue_afterEdit not in beforeEdit_integrationValueNameList:
                newIntegrationValueNameList.append(integrationValue_afterEdit)
        for integrationValue_afterEdit in afterEdit["integrationValues"]:
            if integrationValue_afterEdit["integrationValueName"] in newIntegrationValueNameList:
                cnInteValue_afterEdit["gerritList"] = integrationValue_afterEdit["gerritLinks"]
                try:
                    result, errorMsg = checkDuplicateGerritLink(cnInteValue_afterEdit, cnDgsGerritListInDrop)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    result, errorMsg = checkCnDgReadyToCreate(cnInteValue_afterEdit, dropName)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check integaration value file and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsgq
        for integrationValue_afterEdit in afterEdit["integrationValues"]:
            if integrationValue_afterEdit["integrationValueName"] in newIntegrationValueNameList:
                cnProductObj = CNProduct.objects.get(product_name = integrationValue_afterEdit["integrationValueName"], product_type__product_type_name = "Integration Value")
                for gerritLink in integrationValue_afterEdit["gerritLinks"]:
                    if not CNGerrit.objects.filter(gerrit_link = gerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink)
                        CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink)
                        CNDGToCNProductToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnProduct = cnProductObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to add integration value and gerrit link data while updating integration value info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateInteValueInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber):
    '''
    This function is to add comment for a given dg group number after editing integration value data.
    '''
    errorMsg = None
    editComment = None
    beforeEditComment = None
    afterEditComment = None
    now = None
    try:
        now = datetime.now()
        userObj = User.objects.get(username=user)
        editComment = str(userObj.first_name) + " " + str(userObj.last_name) + " edited integration value info for delivery group " + str(deliveryGroupNumber)
        beforeEditComment = "<p><b>Before Edit:</b></p>"
        for integrationValue in beforeEdit["integrationValues"]:
            beforeEditComment += "<p> Integration Value: " + integrationValue["integrationValueName"] + "</p>"
            for gerritLink in integrationValue["gerritLinks"]:
                beforeEditComment += gerritLink + "<br />"
            beforeEditComment += "<br />"
        afterEditComment = "<p><b>After Edit:</b></p>"
        for integrationValue in afterEdit["integrationValues"]:
            afterEditComment += "<p> Integration Value: " + integrationValue["integrationValueName"] + "</p>"
            for gerritLink in integrationValue["gerritLinks"]:
                afterEditComment += gerritLink + "<br />"
            afterEditComment += "<br />"
        # create 3 comments: editComment, beforeEditComment, afterEditComment
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = editComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = beforeEditComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = afterEditComment, date = now)
    except Exception as e:
        errorMsg = "Failed to add comment while updating integration value info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def deleteIntegrationChartInfo(userName, deliveryGroupNumber, integrationChartInfo):
    '''
    This function is to remove integration data and its gerrit link data and team data by a given delivery group number
    '''
    errorMsg = None
    integrationChartName = None
    gerritList = None
    deliveryGroupObj = None
    user = None
    now = None
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        integrationChartName = integrationChartInfo["integrationChartName"]
        gerritList = integrationChartInfo["gerritList"].split(",")
        deliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        user = User.objects.get(username = userName)
        comment = user.first_name + " " + user.last_name + " removed " + str(integrationChartName) + " <br /> <b> Gerrit Data: <b/> <br /> "
        for gerritLink in gerritList:
            if CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnProduct__product_name = integrationChartName, cnGerrit__gerrit_link = gerritLink).exists():
                CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnProduct__product_name = integrationChartName, cnGerrit__gerrit_link = gerritLink).delete()
                comment += gerritLink + "<br />"
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = deliveryGroupObj, comment = comment, date = now)
        return "SUCCESS", errorMsg
    except Exception as e:
        errorMsg = "Failed to remove integration chart info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)

def deleteIntegrationValueInfo(userName, deliveryGroupNumber, integrationValueInfo):
    '''
    This function is to remove integration value data and its gerrit link data and team data by a given delivery group number
    '''
    errorMsg = None
    integrationValueName = None
    gerritList = None
    deliveryGroupObj = None
    user = None
    now = None
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        integrationValueName = integrationValueInfo["integrationValueName"]
        gerritList = integrationValueInfo["gerritList"].split(",")
        deliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        user = User.objects.get(username = userName)
        comment = user.first_name + " " + user.last_name + " removed " + str(integrationValueName) + " <br /> <b> Gerrit Data: <b/> <br /> "
        for gerritLink in gerritList:
            if CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnProduct__product_name = integrationValueName, cnGerrit__gerrit_link = gerritLink).exists():
                CNDGToCNProductToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnProduct__product_name = integrationValueName, cnGerrit__gerrit_link = gerritLink).delete()
                comment += gerritLink + "<br />"
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = deliveryGroupObj, comment = comment, date = now)
        return "SUCCESS", errorMsg
    except Exception as e:
        errorMsg = "Failed to remove integration value info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)

def deletePipelineInfo(userName, deliveryGroupNumber, pipelineInfo):
    '''
    This function is to remove integration data and its gerrit link data and team data by a given delivery group number
    '''
    errorMsg = None
    pipelineName = None
    gerritList = None
    deliveryGroupObj = None
    user = None
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        pipelineName = pipelineInfo["pipelineName"]
        gerritList = pipelineInfo["gerritList"].split(",")
        deliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        user = User.objects.get(username = userName)
        comment = user.first_name + " " + user.last_name + " removed " + str(pipelineName) + " <br /> <b> Gerrit Data: <b/> <br /> "
        for gerritLink in gerritList:
            if CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnPipeline__pipeline_link = pipelineName, cnGerrit__gerrit_link = gerritLink).exists():
                CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup = deliveryGroupObj, cnPipeline__pipeline_link = pipelineName, cnGerrit__gerrit_link = gerritLink).delete()
                comment += gerritLink + "<br />"
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = deliveryGroupObj, comment = comment, date = now)
        return "SUCCESS", errorMsg
    except Exception as e:
        errorMsg = "Failed to remove pipeline info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)

@transaction.atomic
def updatePipelineInfo(beforeEdit, afterEdit, user, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to update pipeline data and its gerrit link data by a given delivery group number
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        # remove sg
        removeSgStatus, removeSgErrorMsg = updatePipelineInfo_removePipeline(beforeEdit, afterEdit, deliveryGroupNumber)
        if removeSgErrorMsg:
            errorMsg = removeSgErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # update gerrit link for an existing sg
        updateGrtStatus, updateGrtErrorMsg = updatePipelineInfo_updateGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName)
        if updateGrtErrorMsg:
            errorMsg = updateGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add sg and its gerrit link
        addSgGrtStatus, addSgGrtErrorMsg = updatePipelineInfo_addPipeline_addGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop)
        if addSgGrtErrorMsg:
            errorMsg = addSgGrtErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add comment for editing data
        addCommentStatus, addCommentErrorMsg = updatePipelineInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber)
        if addCommentErrorMsg:
            errorMsg = addCommentErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = deliveryGroupNumber
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to update pipeline info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg

def updatePipelineInfo_removePipeline(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to remove pipeline data by a given cn dg number if newly edited pipeline do not have old pipeline data.
    '''
    errorMsg = None
    afterEdit_pipelineNameList = []
    try:
        for pipeline in afterEdit["pipelines"]:
            afterEdit_pipelineNameList.append(pipeline["pipelineName"])
        for pipeline in beforeEdit["pipelines"]:
            if pipeline["pipelineName"] not in afterEdit_pipelineNameList:
                CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnPipeline__pipeline_link = pipeline["pipelineName"]).delete()
    except Exception as e:
        errorMsg = "Failed to remove pipeline info while updating pipeline info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updatePipelineInfo_updateGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName):
    '''
    This function is to add/remove gerrit link data for an existing pipeline by a given cn dg number if newly edited pipelines do not have old gerrit link data
    '''
    errorMsg = None
    cnPipeline_afterEdit = {}
    for pipeline_afterEdit in afterEdit["pipelines"]:
        cnPipeline_afterEdit["gerritList"] = pipeline_afterEdit["gerritLinks"]
        try:
            result, errorMsg = checkCnDgReadyToCreate(cnPipeline_afterEdit, dropName)
            if errorMsg:
                return 1, errorMsg
        except Exception as e:
            errorMsg = "ERROR: Failed to check pipeline and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return 1, errorMsg
    try:
        for pipeline_beforeEdit in beforeEdit["pipelines"]:
            for pipeline_afterEdit in afterEdit["pipelines"]:
                if pipeline_beforeEdit["pipelineName"] == pipeline_afterEdit["pipelineName"]:
                    # same sg found
                    for gerritLink_beforeEdit in pipeline_beforeEdit["gerritLinks"]:
                        if gerritLink_beforeEdit not in pipeline_afterEdit["gerritLinks"]:
                            # remove old link as the link is deleted in new data
                            CNDGToCNPipelineToCNGerritMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnPipeline__pipeline_link = pipeline_beforeEdit["pipelineName"], cnGerrit__gerrit_link = gerritLink_beforeEdit).delete()
                    for gerritLink_afterEdit in pipeline_afterEdit["gerritLinks"]:
                        if gerritLink_afterEdit not in pipeline_beforeEdit["gerritLinks"]:
                            # add new link as the link is added in new data
                            if not CNGerrit.objects.filter(gerrit_link = gerritLink_afterEdit).exists():
                                cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink_afterEdit)
                                cnPipelineObj = CNPipeline.objects.get(pipeline_link = pipeline_beforeEdit["pipelineName"])
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNPipelineToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnPipeline = cnPipelineObj, cnGerrit = cnGerritObj)
                            else:
                                cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink_afterEdit)
                                cnPipelineObj = CNPipeline.objects.get(pipeline_link = pipeline_beforeEdit["pipelineName"])
                                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
                                CNDGToCNPipelineToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnPipeline = cnPipelineObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to update pipeline info while updating pipeline info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updatePipelineInfo_addPipeline_addGerritLink(beforeEdit, afterEdit, deliveryGroupNumber, dropName, cnDgsGerritListInDrop):
    '''
    This function is to add/remove pipeline and its gerrit link data for a new pipeline by a given cn dg number.
    '''
    errorMsg = None
    beforeEdit_pipelineNameList = []
    afterEdit_pipelineNameList = []
    newPipelineNameList = []
    cnPipeline_afterEdit = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        for pipeline_beforeEdit in beforeEdit["pipelines"]:
            beforeEdit_pipelineNameList.append(pipeline_beforeEdit["pipelineName"])
        for pipeline_afterEdit in afterEdit["pipelines"]:
            afterEdit_pipelineNameList.append(pipeline_afterEdit["pipelineName"])
        for pipeline_afterEdit in afterEdit_pipelineNameList:
            if pipeline_afterEdit not in beforeEdit_pipelineNameList:
                newPipelineNameList.append(pipeline_afterEdit)
        for pipeline_afterEdit in afterEdit["pipelines"]:
            if pipeline_afterEdit["pipelineName"] in newPipelineNameList:
                cnPipeline_afterEdit["gerritList"] = pipeline_afterEdit["gerritLinks"]
                try:
                    result, errorMsg = checkDuplicateGerritLink(cnPipeline_afterEdit, cnDgsGerritListInDrop)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check if gerrit link is already created with CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
                try:
                    result, errorMsg = checkCnDgReadyToCreate(cnPipeline_afterEdit, dropName)
                    if errorMsg:
                        return 1, errorMsg
                except Exception as e:
                    errorMsg = "ERROR: Failed to check pipeline and gerrit link is ready to update to a CN Delivery Group. Please investigate: " + str(e)
                    logger.error(errorMsg)
                    return 1, errorMsg
        for pipeline_afterEdit in afterEdit["pipelines"]:
            if pipeline_afterEdit["pipelineName"] in newPipelineNameList:
                if not CNPipeline.objects.filter(pipeline_link = pipeline_afterEdit["pipelineName"]).exists():
                    cnPipelineObj = CNPipeline.objects.create(pipeline_link = pipeline_afterEdit["pipelineName"])
                else:
                    cnPipelineObj = CNPipeline.objects.get(pipeline_link = pipeline_afterEdit["pipelineName"])
                for gerritLink in pipeline_afterEdit["gerritLinks"]:
                    if not CNGerrit.objects.filter(gerrit_link = gerritLink).exists():
                        cnGerritObj = CNGerrit.objects.create(gerrit_link = gerritLink)
                        CNDGToCNPipelineToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnPipeline = cnPipelineObj, cnGerrit = cnGerritObj)
                    else:
                        cnGerritObj = CNGerrit.objects.get(gerrit_link = gerritLink)
                        CNDGToCNPipelineToCNGerritMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnPipeline = cnPipelineObj, cnGerrit = cnGerritObj)
    except Exception as e:
        errorMsg = "Failed to add pipeline and gerrit link data while updating pipeline info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updatePipelineInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber):
    '''
    This function is to add comment for a given dg group number after editing pipeline data.
    '''
    errorMsg = None
    editComment = None
    beforeEditComment = None
    afterEditComment = None
    now = None
    try:
        now = datetime.now()
        userObj = User.objects.get(username=user)
        editComment = str(userObj.first_name) + " " + str(userObj.last_name) + " edited pipeline info for delivery group " + str(deliveryGroupNumber)
        beforeEditComment = "<p><b>Before Edit:</b></p>"
        for pipeline in beforeEdit["pipelines"]:
            beforeEditComment += "<p> Pipeline: " + pipeline["pipelineName"] + "</p>"
            for gerritLink in pipeline["gerritLinks"]:
                beforeEditComment += gerritLink + "<br />"
            beforeEditComment += "<br />"
        afterEditComment = "<p><b>After Edit:</b></p>"
        for pipeline in afterEdit["pipelines"]:
            afterEditComment += "<p> Pipeline: " + pipeline["pipelineName"] + "</p>"
            for gerritLink in pipeline["gerritLinks"]:
                afterEditComment += gerritLink + "<br />"
            afterEditComment += "<br />"
        # create 3 comments: editComment, beforeEditComment, afterEditComment
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = editComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = beforeEditComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = afterEditComment, date = now)
    except Exception as e:
        errorMsg = "Failed to add comment while updating pipeline info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def deleteImpactedDeliveryGroupInfo(userName, deliveryGroupNumber, impactedDeliveryGroupInfo):
    '''
    This function is to remove impacted delivery group info by a given delivery group number
    '''
    errorMsg = None
    impactedDgNumber = None
    deliveryGroupObj = None
    cnDeliveryGroupObj = None
    user = None
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        impactedDgNumber = impactedDeliveryGroupInfo["impactedDeliveryGroupNumber"]
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        deliveryGroupObj = DeliveryGroup.objects.get(id = impactedDgNumber)
        user = User.objects.get(username = userName)
        if CNDGToDGMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, deliveryGroup = deliveryGroupObj).exists():
            CNDGToDGMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, deliveryGroup = deliveryGroupObj).delete()
            comment = user.first_name + " " + user.last_name + " removed  impacted ENM Delivery Group: " + str(impactedDgNumber)
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = comment, date = now)
            enmComment = user.first_name + " " + user.last_name + " removed  impacted Cloud Native Delivery Group: " + str(deliveryGroupNumber)
            DeliveryGroupComment.objects.create(deliveryGroup = deliveryGroupObj, comment = enmComment, date = now)
        return "SUCCESS", errorMsg
    except Exception as e:
        errorMsg = "Failed to remove pipeline info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)

def getImpactedDeliveryGroupInfo(deliveryGroupNumber, queueType):
    '''
    This function is to get impacted delivery group data
    '''
    errorMsg = None
    dgData = []
    result = {}
    try:
        if queueType == "CENM":
            cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
            dgList = CNDGToDGMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj).only('deliveryGroup__id').values('deliveryGroup__id').distinct()
            for dgNumber in dgList:
                dgData.append(dgNumber["deliveryGroup__id"])
        else:
            deliveryGroupObj = DeliveryGroup.objects.get(id = deliveryGroupNumber)
            dgList = CNDGToDGMap.objects.filter(deliveryGroup = deliveryGroupObj).only('cnDeliveryGroup__id').values('cnDeliveryGroup__id').distinct()
            for dgNumber in dgList:
                dgData.append(dgNumber["cnDeliveryGroup__id"])
        result = {'impactedDeliveryGroupNumberList': dgData}
    except Exception as e:
        errorMsg = "Failed to get data for rendering the page for editing impacted delivery group info. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

@transaction.atomic
def updateImpactedDeliveryGroupInfo(beforeEdit, afterEdit, user, deliveryGroupNumber, queueType):
    '''
    This function is to update impacted delivery group data by a given delivery group number
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        # remove sg
        removeDgStatus, removeDgErrorMsg = updateDgInfo_removeDg(beforeEdit, afterEdit, deliveryGroupNumber, queueType)
        if removeDgErrorMsg:
            errorMsg = removeDgErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add sg and its gerrit link
        addDgStatus, addDgErrorMsg = updateDgInfo_addDg(beforeEdit, afterEdit, deliveryGroupNumber, queueType)
        if addDgErrorMsg:
            errorMsg = addDgErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add comment for editing data
        addCommentStatus, addCommentErrorMsg = updateDgInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber)
        if addCommentErrorMsg:
            errorMsg = addCommentErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = deliveryGroupNumber
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to update impacted delivery group info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg

def updateDgInfo_removeDg(beforeEdit, afterEdit, deliveryGroupNumber, queueType):
    '''
    This function is to remove impacted dg data by a given cn dg number if newly edited impacted dg do not have old dg data.
    '''
    errorMsg = None
    afterEdit_dgList = []
    try:
        if queueType == "CENM":
            for dgNumber in afterEdit["impactedDeliveryGroupNumberList"]:
                afterEdit_dgList.append(dgNumber)
            for dgNumber in beforeEdit["impactedDeliveryGroupNumberList"]:
                if dgNumber not in afterEdit_dgList:
                    CNDGToDGMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, deliveryGroup__id = int(dgNumber)).delete()
        else:
            for cnDgNumber in afterEdit["impactedDeliveryGroupNumberList"]:
                afterEdit_dgList.append(dgNumber)
            for cnDgNumber in beforeEdit["impactedDeliveryGroupNumberList"]:
                if cnDgNumber not in afterEdit_dgList:
                    CNDGToDGMap.objects.filter(cnDeliveryGroup__id = int(cnDgNumber), deliveryGroup__id = deliveryGroupNumber).delete()
    except Exception as e:
        errorMsg = "Failed to remove impacted dg info while updating impacted dg info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateDgInfo_addDg(beforeEdit, afterEdit, deliveryGroupNumber, queueType):
    '''
    This function is to add newly edited dg data by a given cn dg number.
    '''
    errorMsg = None
    newDgList = []
    try:
        if queueType == "CENM":
            cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
            for dgNumber in afterEdit["impactedDeliveryGroupNumberList"]:
                if dgNumber not in beforeEdit["impactedDeliveryGroupNumberList"]:
                    newDgList.append(dgNumber)
            for dgNumber in newDgList:
                deliveryGroupObj = DeliveryGroup.objects.get(id = int(dgNumber))
                CNDGToDGMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, deliveryGroup = deliveryGroupObj)
        else:
            deliveryGroupObj = DeliveryGroup.objects.get(id = deliveryGroupNumber)
            for cnDgNumber in afterEdit["impactedDeliveryGroupNumberList"]:
                if cnDgNumber not in beforeEdit["impactedDeliveryGroupNumberList"]:
                    newDgList.append(cnDgNumber)
            for cnDgNumber in newDgList:
                cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = int(cnDgNumber))
                CNDGToDGMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, deliveryGroup = deliveryGroupObj)
    except Exception as e:
        errorMsg = "Failed to add impacted dg info while updating impacted dg info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateDgInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber):
    '''
    This function is to add comment for a given dg group number after editing impacted dg data.
    '''
    errorMsg = None
    editComment = None
    beforeEditComment = None
    afterEditComment = None
    now = None
    try:
        now = datetime.now()
        userObj = User.objects.get(username=user)
        editComment = str(userObj.first_name) + " " + str(userObj.last_name) + " edited impacted ENM Delivery Group Info for delivery group " + str(deliveryGroupNumber)
        beforeEditComment = "<p><b>Before Edit:</b></p>"
        for dgNumber in beforeEdit["impactedDeliveryGroupNumberList"]:
            beforeEditComment += "<p> Delivery Group: " + str(dgNumber) + "</p>"
        afterEditComment = "<p><b>After Edit:</b></p>"
        for dgNumber in afterEdit["impactedDeliveryGroupNumberList"]:
            afterEditComment += "<p> Delivery Group: " + str(dgNumber) + "</p>"
        # create 3 comments: editComment, beforeEditComment, afterEditComment
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = editComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = beforeEditComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = afterEditComment, date = now)
    except Exception as e:
        errorMsg = "Failed to add comment while updating impacted delivery group info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

@transaction.atomic
def updateJiraInfo(beforeEdit, afterEdit, user, deliveryGroupNumber):
    '''
    This function is to update jira ticket data by a given delivery group number
    '''
    errorMsg = None
    result = None
    try:
        sid = transaction.savepoint()
        # remove sg
        removeJiraStatus, removeJiraErrorMsg = updateJiraInfo_removeJira(beforeEdit, afterEdit, deliveryGroupNumber)
        if removeJiraErrorMsg:
            errorMsg = removeJiraErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add sg and its gerrit link
        addJiraStatus, addJiraErrorMsg = updateJiraInfo_addJira(beforeEdit, afterEdit, deliveryGroupNumber)
        if addJiraErrorMsg:
            errorMsg = addJiraErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        # add comment for editing data
        addCommentStatus, addCommentErrorMsg = updateJiraInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber)
        if addCommentErrorMsg:
            errorMsg = addCommentErrorMsg
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = deliveryGroupNumber
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to update jira info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg

def updateJiraInfo_removeJira(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to remove jira data by a given cn dg number if newly edited jira tickets do not have old jira data.
    '''
    errorMsg = None
    afterEdit_jiraList = []
    try:
        for jiraNumber in afterEdit["jiraList"]:
            afterEdit_jiraList.append(jiraNumber)
        for jiraNumber in beforeEdit["jiraList"]:
            if jiraNumber not in afterEdit_jiraList:
                CNDGToCNJiraIssueMap.objects.filter(cnDeliveryGroup__id = deliveryGroupNumber, cnJiraIssue__jiraNumber = jiraNumber).delete()
    except Exception as e:
        errorMsg = "Failed to remove jira info while updating jira info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateJiraInfo_addJira(beforeEdit, afterEdit, deliveryGroupNumber):
    '''
    This function is to add/remove jira tickets by a given cn dg number.
    '''
    errorMsg = None
    newJiraList = []
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        for jiraNumber in afterEdit["jiraList"]:
            if jiraNumber not in beforeEdit["jiraList"]:
                newJiraList.append(jiraNumber)
        for jiraNumber in newJiraList:
            if CNJiraIssue.objects.filter(jiraNumber = jiraNumber).exists():
                cnJiraIssueObj = CNJiraIssue.objects.get(jiraNumber = jiraNumber)
            else:
                jsonObj, statusCode = jiraValidation(jiraNumber)
                if statusCode == "200":
                    isProjectExcept = getExceptionForJiraProject(jsonObj)
                    if not isProjectExcept:
                        isJiraValidationPass, jiraWarning, issueType = getWarningForJiraType(jsonObj)
                        if isJiraValidationPass == False:
                            errorMsg = "Entered Jira type (" + str(issueType)  + ") cannot be added to cn delivery group."
                            logger.error(errorMsg)
                            return 1, errorMsg
                    cnJiraIssueObj = CNJiraIssue.objects.create(jiraNumber = jiraNumber, issueType = jsonObj['fields']['issuetype']['name'])
            CNDGToCNJiraIssueMap.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, cnJiraIssue = cnJiraIssueObj)
    except Exception as e:
        errorMsg = "Failed to add jira info while updating jira info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def updateJiraInfo_addComment(beforeEdit, afterEdit, user, deliveryGroupNumber):
    '''
    This function is to add comment for a given dg group number after editing jira data.
    '''
    errorMsg = None
    editComment = None
    beforeEditComment = None
    afterEditComment = None
    now = None
    try:
        now = datetime.now()
        userObj = User.objects.get(username=user)
        editComment = str(userObj.first_name) + " " + str(userObj.last_name) + " edited jira Info for delivery group " + str(deliveryGroupNumber)
        beforeEditComment = "<p><b>Before Edit:</b></p>"
        for jiraNumber in beforeEdit["jiraList"]:
            beforeEditComment += "<p> Jira Number: " + str(jiraNumber) + "</p>"
        afterEditComment = "<p><b>After Edit:</b></p>"
        for jiraNumber in afterEdit["jiraList"]:
            afterEditComment += "<p> Jira Number: " + str(jiraNumber) + "</p>"
        # create 3 comments: editComment, beforeEditComment, afterEditComment
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = editComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = beforeEditComment, date = now)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = afterEditComment, date = now)
    except Exception as e:
        errorMsg = "Failed to add comment while updating jira info. please investigate: " + str(e)
        logger.error(errorMsg)
        return 1, errorMsg
    return 0, errorMsg

def deleteJiraInfo(userName, deliveryGroupNumber, jiraInfo):
    '''
    This function is to remove jire ticket info by a given delivery group number
    '''
    errorMsg = None
    jiraNumber = None
    deliveryGroupObj = None
    cnDeliveryGroupObj = None
    user = None
    now = None
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        jiraNumber = jiraInfo["jiraNumber"]
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        cnJiraIssueObj = CNJiraIssue.objects.get(jiraNumber = jiraNumber)
        user = User.objects.get(username = userName)
        if CNDGToCNJiraIssueMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnJiraIssue = cnJiraIssueObj).exists():
            CNDGToCNJiraIssueMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj, cnJiraIssue = cnJiraIssueObj).delete()
            comment = user.first_name + " " + user.last_name + " removed jira ticket " + str(jiraNumber)
            CNDeliveryGroupComment.objects.create(cnDeliveryGroup = cnDeliveryGroupObj, comment = comment, date = now)
        return "SUCCESS", errorMsg
    except Exception as e:
        errorMsg = "Failed to remove jira info for cn delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)

def getJiraInfo(deliveryGroupNumber):
    '''
    This function is to get jira data and drop data
    '''
    errorMsg = None
    jiraData = []
    dropData = None
    result = {}
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        dropData = str(cnDeliveryGroupObj.cnDrop.cnProductSet.product_set_name) + " " + str(cnDeliveryGroupObj.cnDrop.name)
        jiraList = CNDGToCNJiraIssueMap.objects.filter(cnDeliveryGroup = cnDeliveryGroupObj).only('cnJiraIssue__jiraNumber').values('cnJiraIssue__jiraNumber').distinct()
        for jiraNumber in jiraList:
            jiraData.append(jiraNumber["cnJiraIssue__jiraNumber"])
        result = {'jiraList': jiraData, 'drop': dropData }
    except Exception as e:
        errorMsg = "Failed to get data for rendering the page for editing jira info. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg
    return result, errorMsg

def getCNDeliveryGroupComment(deliveryGroupNumber):
    '''
    This function is to get comments by a given cn delivery group number
    '''
    result = None
    errorMsg = None
    cnDeliveryGroupObj = None
    try:
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        result = CNDeliveryGroupComment.objects.filter(cnDeliveryGroup=cnDeliveryGroupObj)
        return result, errorMsg
    except Exception as e:
        errorMsg = "Failed to get cn delivery group comment info. Please investigate: " + str(e)
        logger.error(errorMsg)
        return result, errorMsg

@transaction.atomic
def addCNDeliveryGroupComment(userName, newComment, deliveryGroupNumber):
    '''
    This function is to get comments by a given cn delivery group number
    '''
    errorMsg = None
    cnDevliveryGroupObj = None
    user = None
    now = None
    adminGroupMap = None
    adminGroupList = []
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        user = User.objects.get(username=userName)
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        updatedComment = str(user.first_name) + " "  + str(user.last_name) + ": " + str(newComment)
        adminGroup = config.get("CIFWK", "cnDeliveryQueueAdminGroup")
        adminGroupMap= User.objects.filter(groups__name=adminGroup).values('email')
        if adminGroupMap != None:
            for adminEmails in adminGroupMap:
                adminGroupList.append(adminEmails.get('email'))

        CNDeliveryGroupComment.objects.create(cnDeliveryGroup=cnDeliveryGroupObj, comment=updatedComment, date=now)
        if user.email in adminGroupList:
            sendCnDgAddCommentEmail(deliveryGroupNumber,user,updatedComment)
        return 0, errorMsg
    except Exception as e:
        errorMsg = "Failed to get add cn delivery group comment info. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return 1, errorMsg

@transaction.atomic
def updateMissingDepInfo(missingDepValue, missingDepReason, userName, deliveryGroupNumber):
    '''
    This function is to update missing dependencies info by a given cn delivery group number
    '''
    errorMsg = None
    cnDevliveryGroupObj = None
    user = None
    now = None
    try:
        sid = transaction.savepoint()
        now = datetime.now()
        user = User.objects.get(username=userName)
        cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id = deliveryGroupNumber)
        if missingDepValue:
            updatedComment = str(user.first_name) + " "  + str(user.last_name) + " flagged this delivery group as having missing dependencies. <br> Reason: " + str(missingDepReason)
        else:
            updatedComment = str(user.first_name) + " "  + str(user.last_name) + " flagged this delivery group as not having missing dependencies."
        cnDeliveryGroupObj.missingDependencies = missingDepValue
        cnDeliveryGroupObj.save(force_update=True)
        CNDeliveryGroupComment.objects.create(cnDeliveryGroup=cnDeliveryGroupObj, comment=updatedComment, date=now)
        return 0, errorMsg
    except Exception as e:
        errorMsg = "Failed to update missing dependencies info. Please investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return 1, errorMsg

def sendCnDgDeliveredEmail(deliverGroupId, currentUser, cnProductSetVersionNumber):
    '''
    Send email for Deliver Group delivered
    '''
    try:
        name = str(currentUser.first_name) + " " + str(currentUser.last_name)
        currentUserEmail = currentUser.email
        recipients = []
        dropList = CNDeliveryGroup.objects.filter(id=deliverGroupId).values('cnDrop__name')
        dropName = dropList[0].get('cnDrop__name')
        groupCreatorEmail = CNDeliveryGroup.objects.only('creator').get(id=deliverGroupId).creator
        groupTeamEmail = CNDeliveryGroup.objects.only('teamEmail').get(id=deliverGroupId).teamEmail
        subscribersList = CNDeliveryGroupSubscription.objects.filter(cnDeliveryGroup__id=deliverGroupId)
        cnEmailList = config.get("CIFWK", "cnEmailList")
        dm = config.get("CIFWK", "fromEmail")
        mailHeader = "cENM DG " + deliverGroupId + " to Drop " + dropName + " : Delivery of Delivery Group"
        mailContent = '''This is an automated mail from the CI Framework
        \nDear user,\n\nThe following Delivery Group has been delivered...
        \nProduct Set:\t\tCloud Native ENM
        \nDelivery Group:\t\t''' + deliverGroupId  + '''
        \nProduct set Version:\t''' + cnProductSetVersionNumber  + '''
        \nDelivered By:\t\t''' + name
        if currentUserEmail != None:
            recipients.append(currentUserEmail)
        if groupCreatorEmail != None:
            recipients.append(groupCreatorEmail)
        if groupTeamEmail != None:
            recipients.append(groupTeamEmail)
        if subscribersList != None:
            for subscriber in subscribersList:
                recipients.append(subscriber.user.email)
        recipients.append(cnEmailList)
        send_mail(mailHeader, mailContent, dm, recipients, fail_silently=False)
    except Exception as e:
        errorMsg = "Failed to send email for the delivery of delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)

def sendCnDgDeliveryFailedEmail(deliverGroupId, currentUser):
    '''
    Send email for Deliver Group delivery failure
    '''
    try:
        name = str(currentUser.first_name) + " " + str(currentUser.last_name)
        currentUserEmail = currentUser.email
        recipients = []
        dropList = CNDeliveryGroup.objects.filter(id=deliverGroupId).values('cnDrop__name')
        dropName = dropList[0].get('cnDrop__name')
        groupCreatorEmail = CNDeliveryGroup.objects.only('creator').get(id=deliverGroupId).creator
        groupTeamEmail = CNDeliveryGroup.objects.only('teamEmail').get(id=deliverGroupId).teamEmail
        subscribersList = CNDeliveryGroupSubscription.objects.filter(cnDeliveryGroup__id=deliverGroupId)
        cnEmailList = config.get("CIFWK", "cnEmailList")
        dm = config.get("CIFWK", "fromEmail")
        mailHeader = "cENM DG " + deliverGroupId + " to Drop " + dropName + " : Failed to Deliver Delivery Group"
        mailContent = '''This is an automated mail from the CI Framework
        \nDear user,\n\nThe following Delivery Group has been failed to deliver...
        \nProduct Set:\t\tCloud Native ENM
        \nDelivery Group:\t\t''' + deliverGroupId  + '''
        \nPlease check the comment section of the DG for more info
        \nDelivered By:\t\t''' + name
        if currentUserEmail != None:
            recipients.append(currentUserEmail)
        if groupCreatorEmail != None:
            recipients.append(groupCreatorEmail)
        if groupTeamEmail != None:
            recipients.append(groupTeamEmail)
        if subscribersList != None:
            for subscriber in subscribersList:
                recipients.append(subscriber.user.email)
        recipients.append(cnEmailList)
        send_mail(mailHeader, mailContent, dm, recipients, fail_silently=False)
    except Exception as e:
        errorMsg = "Failed to send email for the delivery of delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)

def sendCnDgObsoleteOrRestoreOrDeleteEmail(deliverGroupId, currentUser, dgProcess):
    '''
    Send email for Deliver Group obsolete, delete or restore
    '''
    try:
        name = str(currentUser.first_name) + " " + str(currentUser.last_name)
        currentUserEmail = currentUser.email
        recipients = []
        dropList = CNDeliveryGroup.objects.filter(id=deliverGroupId).values('cnDrop__name')
        dropName = dropList[0].get('cnDrop__name')
        groupCreatorEmail = CNDeliveryGroup.objects.only('creator').get(id=deliverGroupId).creator
        groupTeamEmail = CNDeliveryGroup.objects.only('teamEmail').get(id=deliverGroupId).teamEmail
        subscribersList = CNDeliveryGroupSubscription.objects.filter(cnDeliveryGroup__id=deliverGroupId)
        cnEmailList = config.get("CIFWK", "cnEmailList")
        dm = config.get("CIFWK", "fromEmail")
        if dgProcess == "OBSOLETE":
            mailHeader = "cENM DG " + deliverGroupId + " to Drop " + dropName + ": Obsoletion of Delivery Group"
            mailContent = '''This is an automated mail from the CI Framework
            \nDear user,\n\nThe following Delivery Group has been obsoleted...
            \nProduct Set:\t\tCloud Native ENM
            \nDelivery Group:\t\t''' + deliverGroupId  + '''
            \nObsoleted By:\t\t''' + name
        elif dgProcess == "FAILED":
            mailHeader = "cENM DG " + deliverGroupId + " to Drop " + dropName + ": Failed to obsolete Delivery Group"
            mailContent = '''This is an automated mail from the CI Framework
            \nDear user,\n\nThe following Delivery Group has been failed to obsolete...
            \nProduct Set:\t\tCloud Native ENM
            \nDelivery Group:\t\t''' + deliverGroupId  + '''
            \nPlease check the comment section of the DG for more info
            \nObsoleted By:\t\t''' + name
        elif dgProcess == "RESTORE":
            mailHeader = "cENM DG " + deliverGroupId + " to Drop " + dropName + " : Restoring of Delivery Group"
            mailContent = '''This is an automated mail from the CI Framework
            \nDear user,\n\nThe following Delivery Group has been restored...
            \nProduct Set:\t\tCloud Native ENM
            \nDelivery Group:\t\t''' + deliverGroupId  + '''
            \nRestored By:\t\t''' + name
        elif dgProcess == "DELETE":
            mailHeader = "cENM DG " + deliverGroupId + " to Drop " + dropName + " : Deletion of Delivery Group"
            mailContent = '''This is an automated mail from the CI Framework
            \nDear user,\n\nThe following Delivery Group has been deleted...
            \nProduct Set:\t\tCloud Native ENM
            \nDelivery Group:\t\t''' + deliverGroupId  + '''
            \nDeleted By:\t\t''' + name
        if currentUserEmail != None:
            recipients.append(currentUserEmail)
        if groupCreatorEmail != None:
            recipients.append(groupCreatorEmail)
        if groupTeamEmail != None:
            recipients.append(groupTeamEmail)
        if subscribersList != None:
            for subscriber in subscribersList:
                recipients.append(subscriber.user.email)
        recipients.append(cnEmailList)
        send_mail(mailHeader, mailContent, dm, recipients, fail_silently=False)
    except Exception as e:
        errorMsg = "Failed to send email for obsoletion, deletion or restoring of the delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)


def sendCnDgAddCommentEmail(deliverGroupId, currentUser, comment):
    '''
    Send email for adding new comment by Guardians
    '''
    try:
        currentUserEmail = currentUser.email
        recipients = []
        dropList = CNDeliveryGroup.objects.filter(id=deliverGroupId).values('cnDrop__name')
        dropName = dropList[0].get('cnDrop__name')
        groupCreatorEmail = CNDeliveryGroup.objects.only('creator').get(id=deliverGroupId).creator
        groupTeamEmail = CNDeliveryGroup.objects.only('teamEmail').get(id=deliverGroupId).teamEmail
        subscribersList = CNDeliveryGroupSubscription.objects.filter(cnDeliveryGroup__id=deliverGroupId)
        dm = config.get("CIFWK", "fromEmail")
        mailHeader = "cENM DG " + deliverGroupId + " to Drop " + dropName + " : Guardian added a new comment"
        mailContent = '''This is an automated mail from the CI Framework
        \nDear user,\n\nThe following Delivery Group has been modified with a new comment by Guardians...
        \nProduct Set:\t\tCloud Native ENM
        \nDelivery Group:\t\t''' + deliverGroupId  + '''
        \nNew Comment:\n''' + comment
        if currentUserEmail != None:
            recipients.append(currentUserEmail)
        if groupCreatorEmail != None:
            recipients.append(groupCreatorEmail)
        if groupTeamEmail != None:
            recipients.append(groupTeamEmail)
        if subscribersList != None:
            for subscriber in subscribersList:
                recipients.append(subscriber.user.email)
        send_mail(mailHeader, mailContent, dm, recipients, fail_silently=False)
    except Exception as e:
        errorMsg = "Failed to send email for adding comment in the delivery group. Please investigate: " + str(e)
        logger.error(errorMsg)

def getAllServiceGroup(url):
    '''
    This function is to get a list of service groups from one gerrit link
    '''
    errorMsg = None
    sgList = []
    ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
    try:
        gerritUserName = config.get('CIFWK', 'functionalUser')
        gerritPassword = config.get('CIFWK', 'functionalUserPassword')
        urlTicketValues = url.split("topic:")
        gerritUrl = "http://gerrit-gamma.gic.ericsson.se/a/changes/?q=topic:" + urlTicketValues[1]
        response = requests.get(gerritUrl, auth=HTTPBasicAuth(gerritUserName, gerritPassword),verify=ssl_certs)
        data = (response.content).decode("utf-8").replace(")]}\'", "")
        resultData = json.loads(data)
        for values in resultData:
            sgList.append(str(values.get('project')).split("/")[2])
        for sg in sgList:
            if not CNImage.objects.filter(image_name = sg).exists():
                errorMsg = sg + " service group hasn't been registered on CI Portal. Please raise a support ticket on Engineering Tools Team."
                logger.error(errorMsg)
                return sgList, errorMsg
    except Exception as e:
        errorMsg = "Failed to get service group list from the gerrit link. Please investigate: " + str(e)
        logger.error(errorMsg)
        return sgList, errorMsg
    return sgList, errorMsg

def getCNDgCreatedDetailsByDrop(dropNumber):
    '''
    This function is to get details of all the DGs created in a given drop..
    '''
    try:
        cnDeliveryGroupList = []
        result = None
        errorMsg = None
        dropObj = CNDrop.objects.get(name = dropNumber)
        for temp in CNDeliveryGroup.objects.raw('''SELECT * FROM cireports_cndeliverygroup
        where cndrop_id = %(dropName)s;''', params={'dropName': dropObj.id}):
            cnDeliveryGroupList.append({"DG Number": temp.id, "Team Name": temp.component.element, "Created Date": temp.createdDate, "Drop": dropNumber})
        result = cnDeliveryGroupList
    except Exception as e:
        errorMsg = "Failed to get all the DGs created for the drop " + dropNumber + ". Please Investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def getCNDgQueuedDetailsByDrop(dropNumber):
    '''
    This function is to get details of all the DGs queued in a given drop..
    '''
    try:
        cnDeliveryGroupList = []
        result = None
        errorMsg = None
        dropObj = CNDrop.objects.get(name = dropNumber)
        for temp in CNDeliveryGroup.objects.raw('''SELECT * FROM cireports_cndeliverygroup
        where cndrop_id = %(dropName)s and queued = 1 ;''', params={'dropName': dropObj.id}):
            cnDeliveryGroupList.append({"DG Number": temp.id, "Team Name": temp.component.element, "Created Date": temp.createdDate, "Drop": dropNumber})
        result = cnDeliveryGroupList
    except Exception as e:
        errorMsg = "Failed to get all the DGs queued for the drop " + dropNumber + ". Please Investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

@transaction.atomic
def updateOldDgDeliveredDate():
    '''
    This function is to get the delivered date from the DG comments and then update the deliverd date column for old cENM DGs .
    '''
    try:
        sid = transaction.savepoint()
        result = None
        errorMsg = None
        dgDateMap = {}
        deliveredText = "deliver this delivery group"
        allCNDGComment = CNDeliveryGroupComment.objects.all().order_by('-id')
        for cnDGComment in allCNDGComment:
            if deliveredText in cnDGComment.comment and cnDGComment.cnDeliveryGroup.id not in dgDateMap:
                dgDateMap[cnDGComment.cnDeliveryGroup.id] = cnDGComment.date
        for temp in dgDateMap:
            CNDeliveryGroup.objects.filter(id = temp).update(deliveredDate = dgDateMap.get(temp))
        result = 'SUCCESS'
    except Exception as e:
        errorMsg = "Failed to update delivered date for old cENM DG. Please Investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        result = 'FAILED'
    return result, errorMsg

def getCNDgDeliveredDetailsByDrop(dropNumber):
    '''
    This function is to get details of all the DGs delivered in a given drop..
    '''
    try:
        cnDeliveryGroupList = []
        result = None
        errorMsg = None
        dropObj = CNDrop.objects.get(name = dropNumber)
        for temp in CNDeliveryGroup.objects.raw('''SELECT * FROM cireports_cndeliverygroup
        where cndrop_id = %(dropName)s and delivered = 1 ;''', params={'dropName': dropObj.id}):
            cnDeliveryGroupList.append({"DG Number": temp.id, "Team Name": temp.component.element, "Delivered Date": temp.deliveredDate, "Drop": dropNumber})
        result = cnDeliveryGroupList
    except Exception as e:
        errorMsg = "Failed to get all the DGs delivered for the drop " + dropNumber + ". Please Investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

@transaction.atomic
def updateDevLink():
    '''
    This function is to update the dev_link column for cnProduct Revisions.
    '''
    try:
        sid = transaction.savepoint()
        result = None
        errorMsg = None
        cnProdRevDevLinkMap = {}

        csarLink = "https://arm902-eiffel004.athtem.eei.ericsson.se:8443/nexus/content/repositories/releases/cENM/csar/"
        integrChartLink = "https://arm.epk.ericsson.se/artifactory/proj-enm-dev-internal-helm/"
        allcnProdRevObj = CNProductRevision.objects.filter(product__product_type__product_type_name__in = ("CSAR","Integration Chart"))

        for cnProdRevObj in allcnProdRevObj:
            if cnProdRevObj.product.product_type.product_type_name == "CSAR":
                cnProdRevDevLinkMap[cnProdRevObj.id] = csarLink + cnProdRevObj.product.product_name + "/" + cnProdRevObj.version +"/" + cnProdRevObj.product.product_name + "-" + cnProdRevObj.version + ".csar"
            else:
                cnProdRevDevLinkMap[cnProdRevObj.id] = integrChartLink + cnProdRevObj.product.product_name + "/" + cnProdRevObj.product.product_name + "-" + cnProdRevObj.version + ".tgz"
        for temp in cnProdRevDevLinkMap:
            CNProductRevision.objects.filter(id = temp).update(dev_link = cnProdRevDevLinkMap.get(temp))
        result = 'SUCCESS'
    except Exception as e:
        errorMsg = "Failed to update the dev_link column for cnProduct Revisions. Please Investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        result = 'FAILED'
    return result, errorMsg

@transaction.atomic
def updateRepoName():
    '''
    This function is to update the repo name column for Cn Images.
    '''
    try:
        sid = transaction.savepoint()
        result = None
        errorMsg = None
        cnImageRepoNameMap = {}

        repo_folder = "OSS/com.ericsson.oss.containerisation/"
        allCnImages = CNImage.objects.all()
        for cnImage in allCnImages:
            cnImageRepoNameMap[cnImage.id] = repo_folder + cnImage.image_name
        for temp in cnImageRepoNameMap:
            CNImage.objects.filter(id = temp).update(repo_name = cnImageRepoNameMap.get(temp))
        result = 'SUCCESS'
    except Exception as e:
        errorMsg = "Failed to update the repo name column for Cn Images. Please Investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        result = 'FAILED'
    return result, errorMsg

@transaction.atomic
def updateOldDgObsoletedDate():
    '''
    This function is to get the obsoleted date from the DG comments and then update the obsoleted date column for old cENM DGs .
    '''
    try:
        sid = transaction.savepoint()
        result = None
        errorMsg = None
        dgDateMap = {}
        obsoletedText = "obsoleted this delivery group"
        allCNDGComment = CNDeliveryGroupComment.objects.all().order_by('-id')
        for cnDGComment in allCNDGComment:
            if obsoletedText in cnDGComment.comment and cnDGComment.cnDeliveryGroup.id not in dgDateMap:
                dgDateMap[cnDGComment.cnDeliveryGroup.id] = cnDGComment.date
        for temp in dgDateMap:
            CNDeliveryGroup.objects.filter(id = temp).update(obsoletedDate = dgDateMap.get(temp))
        result = 'SUCCESS'
    except Exception as e:
        errorMsg = "Failed to update obsoleted date for old cENM DG. Please Investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        result = 'FAILED'
    return result, errorMsg

@transaction.atomic
def updateOldDgDeletedDate():
    '''
    This function is to get the deleted date from the DG comments and then update the deleted date column for old cENM DGs .
    '''
    try:
        sid = transaction.savepoint()
        result = None
        errorMsg = None
        dgDateMap = {}
        deletedText = "deleted this delivery group"
        allCNDGComment = CNDeliveryGroupComment.objects.all().order_by('-id')
        for cnDGComment in allCNDGComment:
            if deletedText in cnDGComment.comment and cnDGComment.cnDeliveryGroup.id not in dgDateMap:
                dgDateMap[cnDGComment.cnDeliveryGroup.id] = cnDGComment.date
        for temp in dgDateMap:
            CNDeliveryGroup.objects.filter(id = temp).update(deletedDate = dgDateMap.get(temp))
        result = 'SUCCESS'
    except Exception as e:
        errorMsg = "Failed to update deleted date for old cENM DG. Please Investigate: " + str(e)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        result = 'FAILED'
    return result, errorMsg

def getCNDgObsoletedDetailsByDrop(dropNumber):
    '''
    This function is to get details of all the DGs obsoleted in a given drop..
    '''
    try:
        cnDeliveryGroupList = []
        result = None
        errorMsg = None
        dropObj = CNDrop.objects.get(name = dropNumber)
        for temp in CNDeliveryGroup.objects.raw('''SELECT * FROM cireports_cndeliverygroup
        where cndrop_id = %(dropName)s and obsoleted = 1 ;''', params={'dropName': dropObj.id}):
            cnDeliveryGroupList.append({"DG Number": temp.id, "Team Name": temp.component.element, "Obsoleted Date": temp.obsoletedDate, "Drop": dropNumber})
        result = cnDeliveryGroupList
    except Exception as e:
        errorMsg = "Failed to get all the DGs obsoleted for the drop " + dropNumber + ". Please Investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def getCNDgDeletedDetailsByDrop(dropNumber):
    '''
    This function is to get details of all the DGs deleted in a given drop..
    '''
    try:
        cnDeliveryGroupList = []
        result = None
        errorMsg = None
        dropObj = CNDrop.objects.get(name = dropNumber)
        for temp in CNDeliveryGroup.objects.raw('''SELECT * FROM cireports_cndeliverygroup
        where cndrop_id = %(dropName)s and deleted = 1 ;''', params={'dropName': dropObj.id}):
            cnDeliveryGroupList.append({"DG Number": temp.id, "Team Name": temp.component.element, "Deleted Date": temp.deletedDate, "Drop": dropNumber})
        result = cnDeliveryGroupList
    except Exception as e:
        errorMsg = "Failed to get all the DGs deleted for the drop " + dropNumber + ". Please Investigate: " + str(e)
        logger.error(errorMsg)
    return result, errorMsg

def identifyJiraInstance(jiraIssue):
    jiraMigProjList = JiraMigrationProject.objects.all().values('projectKeyName')
    migKeyList = []
    for obj in jiraMigProjList:
        migKeyList.append(obj.get('projectKeyName'))
    if jiraIssue.split('-')[0] in migKeyList:
        jiraUrl = config.get('CIFWK', 'eTeamjiraUrl')
    else:
        jiraUrl = config.get('CIFWK', 'jiraUrl')
    return jiraUrl + jiraIssue

def getJiraAccessTokenHeader():
    '''
    This function is to get the header with jira access token.
    '''
    token = config.get('CIFWK', 'eTeamJiraAccessToken')
    return {
        'Authorization': 'Bearer ' + str(token)
    }

def getDropByProductSetVersion(productSetVersion):
    '''
    This function is to get drop by a given product set version.
    i.e. if a product set version is 24.05.22, the drop is 24.05.
    '''
    return productSetVersion[:productSetVersion.rfind('.')]

@transaction.atomic
def overrideConfidenceLevel(product, release, drop, productSetVersion, cdbType, isOverridden):
    '''
    This function is to override the confidence level.
    '''
    try:
        sid = transaction.savepoint()
        result = None
        errorMsg = None
        try:
            productObj = Product.objects.get(name=product)
            releaseObj = Release.objects.get(name=release, product=productObj)
            dropObj = Drop.objects.get(name=drop, release=releaseObj)
            productSetVersionObj = ProductSetVersion.objects.get(version=productSetVersion, drop=dropObj)
            cdbTypeObj = CDBTypes.objects.get(name=cdbType)
            productCDBTypeObj = ProductDropToCDBTypeMap.objects.get(drop=dropObj,type=cdbTypeObj)
            psToCDBTypeMapObj = ProductSetVerToCDBTypeMap.objects.get(productSetVersion=productSetVersionObj, productCDBType=productCDBTypeObj)
        except ObjectDoesNotExist as e:
            errorMsg = "Failed to override confidence level due to the unavailable entity. Please check the validity of parameters: " + str(e)
            logger.error(errorMsg)
            return result, errorMsg
        try:
            psToCDBTypeMapObj.override = isOverridden
            psToCDBTypeMapObj.save(force_update=True)
        except OperationalError as e:
            errorMsg = "Failed to override confidence level due to database transaction error: " + str(e)
            logger.error(errorMsg)
            transaction.savepoint_rollback(sid)
            return result, errorMsg
        result = str(psToCDBTypeMapObj)
        return result, errorMsg
    except Exception as unexpectedError:
        errorMsg = "Failed to override confidence level due to unexpected error: " + str(unexpectedError)
        logger.error(errorMsg)
        transaction.savepoint_rollback(sid)
        return result, errorMsg