from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
import cireports.models
import cireports.utils
import zipfile
import urllib
import os
from datetime import datetime
from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--package',
                dest='package',
                help='package'),
            make_option('--ver',
                dest='ver',
                help='version'),
            make_option('--type',
                dest='type',
                help='The Package Type, multiple formats supported.. rpm, zip, pkg etc'),
            make_option('--packagemap',
                dest='packagemap',
                help='testware mapped to package'),
            make_option('--packagelist',
                dest='packagelist',
                help='packagelist'),
            make_option('--phase',
                dest='phase',
                help='phase'),
            make_option('--testReport',
                dest='testReport',
                help='tests report file'),
            make_option('--testResultReport',
                dest='testResultReport',
                help='tests report'),
            make_option('--passed',
                dest='passed',
                help='passed'),
            make_option('--failed',
                dest='failed',
                help='failed'), 
            )

    def handle(self, *args, **options):
        if options['package'] == None: 
            raise CommandError("Package option required")  
        else:   
            package=options['package']
        if options['ver'] == None:
            raise CommandError("Version option required")
        else:
            ver=options['ver']

        testReport = options['testReport']
        testReportDirecotory = options['testResultReport']

        if options['packagelist'] == None and package !=None and ver !=None:
            options['packagelist'] = str(package)+":"+str(ver)
        now = datetime.now()
        packageList=options['packagelist'].split(",")
        packageMap = options['packagemap']

        if options['type'] == None:
            type = "rpm"
        else:
            type = options['type']

        if options['phase'] == None:
            raise CommandError("Phase option required")
        else:
            phase=options['phase']
    
        failed=options['failed']
        passed=options['passed']
        try:
            total=int(failed)+int(passed)
        except:
            total = None

        filePath = config.get('REPORT', 'filePath')
        reportFile = config.get('REPORT', 'reportFile')
        reportDirectory = config.get('REPORT', 'reportDirectory')

        try:
            urllib.urlretrieve(testReport, reportFile)
            with open(reportFile) as f:
                report=f.read()
        except:
            report=""
        
        packageObj = cireports.models.PackageRevision.objects.get(package__name=package,version=ver,m2type=type)
        autodrop = packageObj.autodrop

        if autodrop != "latest":
            autodrop = autodrop.split(":")
            product = autodrop[0]
            directory = str(product) + "_" + str(package) + "_" + str(ver) + "_" + str(phase)
        else:
            directory = str(package) + "_" + str(ver) + "_" + str(phase)
        path = os.path.join(filePath,directory)
    
        try:
            urllib.urlretrieve(testReportDirecotory, reportDirectory)
            file = zipfile.ZipFile(reportDirectory, "r")
            file.extractall(path)
            directoryName = directory
        except:
            directoryName = ""

        testResultObj=cireports.models.TestResults(failed=failed,passed=passed,total=total,tag=now,testdate=now,phase=phase,test_report=report,test_report_directory=directoryName)
        testResultObj.save()

        if options['packagemap'] != None:
            packageMapNew=packageMap.split("-BREAK-")
        else:
            packageMapNew = None

        for packageItem in packageList:
            package,ver=packageItem.split(":")
            pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,m2type=type)
            if packageMapNew != None:
                for map in packageMapNew:
                    testwarename,testwareversion=map.split("-VER-")
                    pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,m2type=type)
                    testWareObj=cireports.models.TestwareRevision.objects.get(testware_artifact__name= testwarename,version=testwareversion)
                    testResultiMapObj=cireports.models.TestResultsToTestwareMap(testware_revision_id=testWareObj.id,package_revision_id=pkgObj.id,testware_artifact_id=testWareObj.testware_artifact.id,package_id=pkgObj.package.id,testware_run_id=testResultObj.id)
                    testResultiMapObj.save()
            else:
                pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,m2type=type)
                testResultiMapObj=cireports.models.TestResultsWithoutTestware(package_revision_id=pkgObj.id,package_id=pkgObj.package.id,testware_run_id=testResultObj.id)
                testResultiMapObj.save()

        try:
            os.remove(reportFile)
        except:
            logger.error("Report file does not exist")
        try:
            os.remove(reportDirectory)
        except:
            logger.error("Report zip file does not exist")
 
