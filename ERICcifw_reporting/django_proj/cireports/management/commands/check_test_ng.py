from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
import cireports.models
import cireports.utils
from datetime import datetime
from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--package',
                dest='package',
                help='package'),
            make_option('--packagelist',
                dest='packagelist',
                help='packagelist'),
            make_option('--packagemap',
                dest='packagemap',
                help='testware mappet to package'),
            make_option('--ver',
                dest='ver',
                help='version'),
            make_option('--type',
                dest='type',
                help='The Package Type (e.g rpm,zip,tar,pkg)'),
            make_option('--phase',
                dest='phase',
                help='test phase'),
            make_option('--platform',
                dest='platform',
                help='platform'),
            )

    def handle(self, *args, **options):
        package=options['package']
        packageMap=[]
        packageMap=options['packagemap']
        ver=options['ver']
        if options['packagelist'] == None and package !=None and ver !=None:
            options['packagelist'] = package+":"+ver
        phase=options['phase']
        failed=0
        passed=0
        with open("./test-output/testng-results.xml") as f:
            for line in f:
                if "<test-method status=" in line:
                    split = line.split(" ")
                    for info in split:
                        if "status=" in info:
                            dontcare,status=info.split("status=")
                            if status == "\"FAIL\"":
                                failed += 1
                            if status == "\"PASS\"":
                                passed += 1
        total=int(failed)+int(passed)
        now = datetime.now()
        tag = now
        testResultObj=cireports.models.TestResults(failed=failed,passed=passed,total=total,tag=now,testdate=now,phase=phase) 
        testResultObj.save()
        packageList=options['packagelist'].split(",")
        if options['platform'] == None:
            platform = "None"
        else:
            platform = options['platform'].lower()
        if options['type'] == None:
            type = "rpm"
        else:
            type = options['type']
        for packageItem in packageList:
            package,ver=packageItem.split(":")
            if platform == "None":
                pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,m2type=type)
            else:
               pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,platform=platform,m2type=type) 
            if failed is 0:
                 cireports.utils.updateTestStatus(pkgObj.package.name,pkgObj.version,type,phase,"passed",platform=platform)
            else:
                 cireports.utils.updateTestStatus(pkgObj.package.name,pkgObj.version,type,phase,"failed",platform=platform)
        try:
            with open("./test-output/emailable-report.html") as f:
                testReport=f.read()
        except:
            testReport=""
        testResultObj=cireports.models.TestResults(failed=failed,passed=passed,tag=now,testdate=now,phase=phase,test_report=testReport) 
        testResultObj.save()
        packageMapNew=packageMap.split("-BREAK-")
        for packageItem in packageList:
            package,ver=packageItem.split(":")
            if platform == "None":
                pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,m2type=type)
            else:
                pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver, platform=platform,m2type=type)

            for map in packageMapNew:
                testwarename,testwareversion=map.split("-VER-")
                if platform == "None":
                    pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,m2type=type)
                else:
                    pkgObj=cireports.models.PackageRevision.objects.get(package__name=package,version=ver,platform=platform,m2type=type)
                testWareObj=cireports.models.TestwareRevision.objects.get(testware_artifact__name= testwarename,version=testwareversion)
                testResultiMapObj=cireports.models.TestResultsToTestwareMap(testware_revision_id=testWareObj.id,package_revision_id=pkgObj.id,testware_artifact_id=testWareObj.testware_artifact.id,package_id=pkgObj.package.id,testware_run_id=testResultObj.id) 
                testResultiMapObj.save()

