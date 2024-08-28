from django.shortcuts import render
from dmt.models import *
from cireports.models import *
from dmt.cloud import *
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from django.core.context_processors import csrf
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.core.management.base import BaseCommand, CommandError
import sys, os, os.path, tempfile, zipfile
from ciconfig import CIConfig
from django.db import connection
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
import time
from datetime import datetime, timedelta
from distutils.version import LooseVersion
import logging
logger = logging.getLogger(__name__)
config = CIConfig()

from fwk.utils import pageHitCounter
import dmt.utils
import dmt.buildconfig
import dmt.cloud
import dmt.mcast
import ast
import subprocess
import json, re
from metrics.models import *

from dmt.forms import *

from django.contrib.auth.models import User, Group
from guardian.decorators import permission_required, permission_required_or_403
from guardian.conf import settings as guardian_settings
from guardian.exceptions import GuardianError
from guardian.shortcuts import assign
from guardian.shortcuts import get_perms
from guardian.core import ObjectPermissionChecker

import utils

# Create your views here.
def viewCloudMetrics(request, selected=None):
    '''
    '''
    pageHitCounter("CloudMetrics", None, str(request.user))
    serverDict = {}
    servers = []
    sppServers = SPPServer.objects.all()
    if sppServers:
        for server in sppServers:
            servers.append((server.name,server.url))
        serverDict['servers'] = servers
    return render(request, "metrics/cloud_metrics.html",{'serverDict':serverDict})


def getEventData(request):
    '''
    The getEventData function is used to find which event was selected and return which one was selected .

    '''
    # Create a FormHandle to handle form post-processing

    singleSedData = None

    try:
        data1=[]
        allEventData = EventType.objects.all().order_by('eventTypeName')
        for event in allEventData:
            data= [{
                "eventName":event.eventTypeName,
                "eventNameDb":event.eventTypeDb
                }]

            data1=data1+data

        ret = json.dumps(data1)

        return HttpResponse(ret, content_type="application/json")

    except Exception as e:
        logInfo="Unable to get the Event Types : " + str(e)
        logger.error(logInfo)


@csrf_exempt
def showMetricsData(request):
    '''
    This view recieves cloud metrics data in Json format. It returns a table displaying a summary of this information
    '''

    if request.method == 'POST':
        jSon = request.POST.get('json')
        startDate = request.POST.get('start')
        endDate = request.POST.get('end')
        degArray = request.POST.get('degArray')
        if jSon is None:
            return HttpResponse("Error: Metrics Data Required\n")
    else:
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    decodedJson = json.loads(jSon)
    degMapping = utils.parseDegMappings(json.loads(degArray))
    totalJobs, jobsPassed, jobsFailed, passedWithRetries, percentPassed, averageExecutionTime = utils.processCloudMetrics(decodedJson)

    return render(request, "metrics/cloud_metrics_content.html", {
        'total':totalJobs,
        'passed':jobsPassed,
        'failed':jobsFailed,
        'passed_with_retries':passedWithRetries,
        'percent_passed':percentPassed,
        'average_exec_time':averageExecutionTime,
        'content':jSon,
        'deg_mapping':degMapping,
        'start':startDate,
        'end':endDate
        })


def downloadMetricsFile(request):
    '''
    This view recieves Cloud metrics info in Json format and returns a response which contains a csv file for download
    '''

    if request.method == 'POST':
        jsonMetrics = request.POST.get('metrics_data')
        startDate = request.POST.get('start')
        endDate = request.POST.get('end')
        degMapping = request.POST.get('degMapping')
        startDate = str(startDate).replace(" ", "_");
        endDate = str(endDate).replace(" ", "_");
        if jsonMetrics is None:
            return HttpResponse("Error: Json Metrics Required\n")

        decodedJson = json.loads(jsonMetrics)
        degMapDict = ast.literal_eval(degMapping)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=Cloud_Metrics_'+startDate+'__'+endDate+'.csv'
        response = utils.buildMetricsCsv(response, decodedJson, degMapDict)
        return response
    else:
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")

@csrf_exempt
def KGBPackageInformation(request):
    try:
        packageList = request.POST.get('packageList')
        drops = request.POST.get('drops')
        startTime = str(request.POST.get('startTime'))
        endTime = str(request.POST.get('endTime'))
        pretty = str(request.POST.get('pretty'))
        decodedJSON = json.loads(packageList)
        if drops is None or not drops or drops == "None":
            response = utils.getKGBDetails(decodedJSON, startTime, endTime)
        else:
            response = utils.getKGBDetailsForPackagesInDrop(decodedJSON, json.loads(drops))
        if pretty == 'true':
            result = json.dumps(response,sort_keys=False, indent=4)
        else:
            result = json.dumps(response)
    except Exception as e:
        logger.error("Issue with getting package Information " + str(e))
        result = json.dumps([{"error":str(e)}])

    return HttpResponse(result, content_type="application/json")

def viewKgbMetrics(request):
    pageHitCounter("KGBMetrics", None, str(request.user))
    return render(request, "metrics/kgb_package_metrics.html")


def allPackagesJson(request):
    '''
    This view returns all the packages within the CI portal database in Json Format
    '''

    allPackages = list(Package.objects.only('name').exclude(hide=True).order_by('name'))
    packagesJson = {}
    packagesArray = []
    for package in allPackages:
        packagesArray.append(package.name)
    packagesJson["packagesJson"] = packagesArray
    packagesJson = json.dumps(packagesJson)
    return HttpResponse(packagesJson, content_type="application/json")

def allComponentsJson(request):
    '''
    This view returns all the components withing the CI portal database in Json Format
    '''

    allComponents = list(Component.objects.only('element').order_by('element'))
    componentsJson = {"Components": []}
    if allComponents:
        for component in allComponents:
            data={}
            data["element"] = component.element
            data["parent"] = str(component.parent)
            data["product"] = str(component.product)
            componentsJson["Components"].append(data)
    if len(allComponents) == 0:
        data={}
        data["element"] = "No Data"
        data["parent"] = "No Data"
        data["product"] = "No Data"
        componentsJson["Components"].append(data)
    componentsJson = json.dumps(componentsJson)
    return HttpResponse(componentsJson, content_type="application/json")

def allLabelsJson(request):
    '''
    This view returns all the labels within the CI portal database in Json Format
    '''
    allLabels = Label.objects.all()
    labelsJson = {"Label":[]}
    labelsArray = []
    result = json.dumps([{"error":""}])
    try:
        if allLabels:
            for label in allLabels:
                labelsArray.append(label.name)
            labelsJson["Label"] = labelsArray
            result = json.dumps(labelsJson)
    except:
        logger.error("There was an issue building Label List for Display, Error thrown: " +str(e))
        result = json.dumps([{"error":str(e)}])

    return HttpResponse(result, content_type="application/json")



def getComponentsFromProducts(request):
    '''
    This view returns all the components assoicated with a product within the CI portal database in Json Format
    '''
    product = request.GET.get("product")
    productObj = Product.objects.get(name=product)
    allComponents = list(Component.objects.only('element').order_by('element'))
    componentsJson = {"Components": []}
    componentCount = 0
    if allComponents:
        for component in allComponents:
            if str(productObj).lower() == str(component.product).lower():
                componentCount = componentCount + 1
                data={}
                data["element"] = component.element
                data["parent"] = str(component.parent)
                if component.parent:
                    data["parentLabel"] = str(component.parent.label)
                else:
                    data["parentLabel"] = "None"
                data["product"] = str(component.product)
                data["label"] = str(component.label)
                componentsJson["Components"].append(data)
    if componentCount == 0:
        data={}
        data["element"] = "No Data"
        data["parent"] = "No Data"
        data["product"] = "No Data"
        componentsJson["Components"].append(data)
    componentsJson = json.dumps(componentsJson)
    return HttpResponse(componentsJson, content_type="application/json")

def getPackagesFromComponents(request):
    '''
    This view returns all the packages  assoicated with a product within the CI portal database in Json Format
    '''
    componentElement = request.GET.get("component")
    componentObj = PackageComponentMapping.objects.filter(component__element=componentElement)

    packagesJson = {}
    packagesArray = []
    for component in componentObj:
        packagesArray.append(component.package.name)

    if len(packagesArray) == 0:
        packagesArray.append("No Data")
    packagesJson["Packages"] = packagesArray
    packagesJson = json.dumps(packagesJson)
    return HttpResponse(packagesJson, content_type="application/json")

def getProductsJson(request):
    '''
    This view returns all the products within the CI portal database in Json format
    '''

    products = Product.objects.only('name').exclude(name = 'None').exclude(name = 'test').order_by('name')
    productsJson = {"Products": []}
    for productObj in products:
        data={}
        data["name"]=productObj.name
        productsJson["Products"].append(data)
    ret = json.dumps(productsJson)
    return HttpResponse(ret, content_type="application/json")


@csrf_exempt
def showKgbMetricsTable(request):
    '''
    This view recieves KGB metrics data in Json format. It returns a table displaying a summary of this information
    '''

    if request.method == 'POST':
        jSon = request.POST.get('json')
        startDate = request.POST.get('start')
        endDate = request.POST.get('end')
        drops = request.POST.get('drops')
        if jSon is None:
            return HttpResponse("Error: Metrics Data Required\n")
    else:
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")
    decodedJson = json.loads(jSon)
    for package in decodedJson:
        if package['Summary']['PassedKGB'] > 0:
            passedPercent=int((float(package['Summary']['PassedKGB'])/(float(package['Summary']['PassedKGB']) + float(package['Summary']['FailedKGB'])))*100)
        else:
            passedPercent = 0
        if package['Summary']['FailedKGB'] > 0:
            failedPercent=int((float(package['Summary']['FailedKGB'])/(float(package['Summary']['PassedKGB']) + float(package['Summary']['FailedKGB'])))*100)
        else:
            failedPercent = 0
        if package['Summary']['DeliveredWithPassedKGB'] > 0:
            delWithPassPercent=int((float(package['Summary']['DeliveredWithPassedKGB'])/(float(package['Summary']['NumberOfDeliveries'])))*100)
        else:
            delWithPassPercent = 0
        if package['Summary']['DeliveredWithFailedKGB'] > 0:
            delWithFailPercent=int((float(package['Summary']['DeliveredWithFailedKGB'])/(float(package['Summary']['NumberOfDeliveries'])))*100)
        else:
            delWithFailPercent = 0
        if package['Summary']['DeliveredWithoutKGB'] > 0:
            delWithOutPercent=int((float(package['Summary']['DeliveredWithoutKGB'])/(float(package['Summary']['NumberOfDeliveries'])))*100)
        else:
            delWithOutPercent = 0
        package['Summary']['passedPercent'] = passedPercent
        package['Summary']['failedPercent'] = failedPercent
        package['Summary']['delWithPassPercent'] = delWithPassPercent
        package['Summary']['delWithFailPercent'] = delWithFailPercent
        package['Summary']['delWithOutPercent'] = delWithOutPercent

    return render(request, "metrics/kgb_summary.html", {
       'packageData':decodedJson,
       'raw_data':jSon,
       'start':startDate,
       'end':endDate,
       'drops':drops
    })


def downloadKGBMetricsFile(request):
    '''
    This view recieves KGB metrics info in Json format and returns a response which contains a csv file for download
    '''

    if request.method == 'POST':
        jsonMetrics = request.POST.get('package_data')
        startDate = request.POST.get('start')
        endDate = request.POST.get('end')
        drops = request.POST.get('drops')
        startDate = str(startDate).replace(" ", "_");
        endDate = str(endDate).replace(" ", "_");
        if jsonMetrics is None:
            return HttpResponse("Error: Json Metrics Required\n")

        if drops is None or not drops or drops == "None":
            fileName = 'KGB_Metrics_'+startDate+'__'+endDate+'.csv'
        else:
            timeNow = datetime.now().date()
            fileName = 'KGB_Metrics_'+str(timeNow)+'.csv'
        decodedJson = json.loads(jsonMetrics)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=' + fileName
        response = utils.buildKgbMetricsCsv(response, decodedJson)
        return response
    else:
        return HttpResponse("Error: This interface accepts HTTP POST requests only.\n")


def getDropNamesForProduct(request):
    '''
    This function retrieves all drops for a product
    '''
    products = request.GET.get("products")

    if products is None or not products or products == "None":
        result = json.dumps([{"error":"Product Required"}])
    else:
        dropsJson = {"Drops":[]}
        dropsArray = []
        result = json.dumps([{"error":""}])
        try:
            for product in products.split(","):
                if Drop.objects.filter(release__product__name=product).exists():
                    allDrops = Drop.objects.filter(release__product__name=product).order_by('id').only('id','name').values('id','name').reverse()
                    for drop in allDrops:
                        if (ISObuildMapping.objects.filter(drop__id=drop['id']).exists()):
                            drop = product + ":" + str(drop['name'])
                            dropsArray.append(drop)
            dropsJson["Drops"] = dropsArray
            result = json.dumps(dropsJson)
        except Exception as e:
            logger.error("There was an issue retrieving drops for " + product + ", Error thrown: " +str(e))
            result = json.dumps([{"error":str(e)}])

    return HttpResponse(result, content_type="application/json")


def getRevisionsReleasedForDrop(request):
    '''
    Returns the names of all packages which have one or more revisons intended for a particular drop
    '''
    dropDatas = request.GET.get("drops")

    if dropDatas is None or not dropDatas or dropDatas == "None":
        result = json.dumps([{"error":"Drop Data Required"}])

    else:
        packagesJson = {"Packages":[]}
        packagesArray = []
        result = json.dumps([{"error":""}])
        try:
            for dropData in dropDatas.split(','):
                revisions = PackageRevision.objects.filter(autodrop=dropData)
                for revision in revisions:
                    packageName = revision.package.name
                    if packageName not in packagesArray:
                        packagesArray.append(packageName)
                product = Product.objects.filter(name = dropData.split(':')[0])
                drop = Drop.objects.filter(name = dropData.split(':')[1])
                dpms = DropPackageMapping.objects.filter(drop = drop, drop__release__product = product)
                for dpm in dpms:
                    packageName = dpm.package_revision.package.name
                    if packageName not in packagesArray:
                        packagesArray.append(packageName)
            packagesJson["Packages"] = sorted(packagesArray)
            result = json.dumps(packagesJson)
        except Exception as e:
            logger.error("There was an issue retrieving packages for " + dropData + ", Error thrown: " +str(e))
            result = json.dumps([{"error":str(e)}])

    return HttpResponse(result, content_type="application/json")
