import csv
import logging
logger = logging.getLogger(__name__)
from cireports.models import *
from datetime import datetime
from django.db.models import Q

def processCloudMetrics(decodedJson):
    '''
    This function takes in the Json result of the rest call. It parses this info for the Summary table on the CI Portal
    '''
    totalJobs = 0.0
    jobsPassed = 0.0
    jobsFailed = 0
    passedWithRetries = 0
    totalExecutionTime = 0

    for event in decodedJson['Events']:
        totalJobs += 1
        if event['Event']['value_returned'] == '0':
            jobsPassed += 1
            dateCreated = datetime.strptime(event['Event']['created'], '%Y-%m-%d %H:%M:%S')
            dateModified = datetime.strptime(event['Event']['modified'], '%Y-%m-%d %H:%M:%S')
            totalExecutionTime += (dateModified-dateCreated).seconds

            if event['Event']['retries'] != '0':
                passedWithRetries += 1
        else:
            jobsFailed += 1
    if totalJobs > 0:
        percentPassed = (jobsPassed/totalJobs)*100
    else:
        percentPassed = 0
    if jobsPassed > 0:
        m, s = divmod((totalExecutionTime/int(jobsPassed)), 60)
        h, m = divmod(m, 60)
        averageExecutionTime = "%d:%02d:%02d" % (h, m, s)
    else:
        averageExecutionTime = 0
    return int(totalJobs), int(jobsPassed), jobsFailed, passedWithRetries, int(percentPassed), averageExecutionTime


def buildMetricsCsv(response, decodedJson, degMapping):
    '''
    This function builds the cloud metrics CSV file for download
    '''
    f = csv.writer(response)
    f.writerow(["PDG", "Datacenter", "Function Name", "Status", "Start Time", "End Time", "Execution Time", "No. of Retries"])
    for event in decodedJson['Events']:
        dateCreated = datetime.strptime(event['Event']['created'], '%Y-%m-%d %H:%M:%S')
        dateModified = datetime.strptime(event['Event']['modified'], '%Y-%m-%d %H:%M:%S')
        executionTime = dateModified-dateCreated
        if event['Event']['value_returned'] == '0':
            status = "Passed"
        else:
            status = "Failed"
        deg = degMapping[event['OrgVdc']['mig_ra_id']]

        f.writerow([deg,
                    event['OrgVdc']['name'],
                    event['Event']['function_name'],
                    status,
                    event['Event']['created'],
                    event['Event']['modified'],
                    executionTime,
                    event['Event']['retries']])
    return response


def parseDegMappings(degArray):

    degMapping = {}
    for deg in degArray:
        degMapping[deg['MigRa']['id']] = deg['MigRa']['name']

    return degMapping


def getKGBDetails(packageList, startTime, endTime):
    '''
    This function builds the json response for KGB Metrics Detail REST call filtered by dates
    '''
    packageKGB = []
    for packageName in packageList:
        if Package.objects.filter(name = packageName['name']).exists():
            passed = 0
            failed = 0
            noKgb = 0
            numberDeliveries = 0
            deliveryFailed = 0
            deliveryPassed = 0
            deliveryNoKGB = 0
            data = {}
            summary = []
            data['name'] = packageName['name']
            pkgObj = Package.objects.get(name = packageName['name'])
            timeNow = datetime.now()
            startTimeObj = datetime.strptime(startTime, '%Y-%m-%d %H:%M:%S')
            endTimeObj = datetime.strptime(endTime, '%Y-%m-%d %H:%M:%S')
            kgbObjs = PackageRevision.objects.filter(package = pkgObj).filter(date_created__range=(startTimeObj, endTimeObj))
            for obj in kgbObjs:
                totalPackages = len(kgbObjs)
                delivered = False
                kgbRan = obj.kgb_test
                if kgbRan == 'passed':
                   passed = passed + 1
                if kgbRan == 'failed':
                   failed = failed + 1
                if obj.kgb_test == "not_started":
                    noKgb = noKgb + 1
                if DropPackageMapping.objects.filter(package_revision = obj).filter(date_created__range=(startTimeObj,endTimeObj)).exists():
                    delivered = True
                    numberDeliveries = numberDeliveries + 1
                    if kgbRan == 'passed':
                        deliveryPassed = deliveryPassed + 1
                    elif kgbRan == 'failed':
                        deliveryFailed = deliveryFailed + 1
                    else:
                        deliveryNoKGB = deliveryNoKGB + 1
                summaryObj =  {"version" : obj.version , "KgbResult" : kgbRan , "Delivered" : delivered}
                summary.append(summaryObj)
            if passed != 0 or failed != 0 or noKgb != 0:
                data['Detailed'] = summary
                data['Summary'] = { "Total": totalPackages, "PassedKGB" : passed , "FailedKGB" : failed, "NoKGBRan" : noKgb ,"NumberOfDeliveries" : numberDeliveries, "DeliveredWithFailedKGB" : deliveryFailed, "DeliveredWithPassedKGB" : deliveryPassed, "DeliveredWithoutKGB" : deliveryNoKGB }
                packageKGB.append(data)
    return packageKGB


def getKGBDetailsForPackagesInDrop(packageList, drops):
    '''
    This function builds the json response for KGB Metrics Detail REST call filtered by drops
    '''
    packageKGB = []
    for packageName in packageList:
        totalPackages = 0
        passed = 0
        failed = 0
        noKgb = 0
        numberDeliveries = 0
        deliveryFailed = 0
        deliveryPassed = 0
        deliveryNoKGB = 0
        data = {}
        summary = []
        if Package.objects.filter(name = packageName['name']).exists():
            data['name'] = packageName['name']
            pkgObj = Package.objects.get(name = packageName['name'])
            for drop in drops:
                kgbObjs = list(PackageRevision.objects.filter(autodrop = drop['name'], package = pkgObj))
                product = Product.objects.filter(name = drop['name'].split(':')[0])
                dropObj = Drop.objects.filter(name = drop['name'].split(':')[1])
                dpms = DropPackageMapping.objects.filter(drop = dropObj, drop__release__product = product, package_revision__package = pkgObj)
                for dpm in dpms:
                    pkgRev = dpm.package_revision
                    if pkgRev not in kgbObjs:
                        kgbObjs.append(pkgRev)
                totalPackages += len(kgbObjs)
                for obj in kgbObjs:
                    kgbRan = "Not ran"
                    delivered = False
                    kgbRan = obj.kgb_test
                    if kgbRan == 'passed':
                        passed = passed + 1
                    if kgbRan == 'failed':
                        failed = failed + 1
                    if obj.kgb_test == "not_started":
                        noKgb = noKgb + 1
                    if DropPackageMapping.objects.filter(package_revision = obj).exists():
                        delivered = True
                        numberDeliveries = numberDeliveries + 1
                        if kgbRan == 'passed':
                            deliveryPassed = deliveryPassed + 1
                        elif kgbRan == 'failed':
                            deliveryFailed = deliveryFailed + 1
                        else:
                            deliveryNoKGB = deliveryNoKGB + 1
                    summaryObj =  {"version" : obj.version , "KgbResult" : kgbRan , "Delivered" : delivered , "Drop" : drop['name']}
                    summary.append(summaryObj)
            if passed != 0 or failed != 0 or noKgb != 0:
                data['Detailed'] = summary
                data['Summary'] = { "Total": totalPackages, "PassedKGB" : passed , "FailedKGB" : failed, "NoKGBRan" : noKgb ,"NumberOfDeliveries" : numberDeliveries, "DeliveredWithFailedKGB" : deliveryFailed, "DeliveredWithPassedKGB" : deliveryPassed, "DeliveredWithoutKGB" : deliveryNoKGB }
                packageKGB.append(data)
    return packageKGB


def buildKgbMetricsCsv(response, decodedJson):
    '''
    This function builds the KGB metrics CSV file for download
    '''
    metricsCsv = csv.writer(response)
    if 'Drop' in decodedJson[0]['Detailed'][0]:
        metricsCsv.writerow(["Package", "Version", "Delivered", "KGB Status", "Drop"])
    else:
        metricsCsv.writerow(["Package", "Version", "Delivered", "KGB Status"])
    for packageRevs in decodedJson:
        packageName = packageRevs['name']
        for packageRev in packageRevs['Detailed']:
            if 'Drop' in packageRev:
                metricsCsv.writerow([packageName,
                    packageRev['version'],
                    packageRev['Delivered'],
                    packageRev['KgbResult'],
                    packageRev['Drop']
                ])
            else:
                metricsCsv.writerow([packageName,
                    packageRev['version'],
                    packageRev['Delivered'],
                    packageRev['KgbResult']
                ])
    return response
