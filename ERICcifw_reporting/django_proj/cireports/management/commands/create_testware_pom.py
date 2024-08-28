from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
import cireports.models
import cireports.utils

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
            make_option('--testwareList',
                dest='testwareList',
                help='testwareList'),
            make_option('--pomVersion',
                dest='pomVersion',
                help='select pom template version'),
                
            )


    def handle(self, *args, **options):
        if options['package'] == None and options['testwareList'] == None:
            raise CommandError("Option required")
        elif options['package'] != None :
            package=options['package']
        if options['ver'] == None and options['testwareList'] == None:
            raise CommandError("Option required")
        elif options['ver'] != None:
            ver=options['ver']
        if options['pomVersion'] == None:
            pomVersion='default'
        else:
            pomVersion=options['pomVersion']
        
        data = []
        if options['ver'] != None and options['package'] != None:
            all = cireports.models.TestwarePackageMapping.objects.filter(package__name=package)
            for testwareMap in all:
                testwareRev=cireports.models.TestwareRevision.objects.filter(testware_artifact_id=testwareMap.testware_artifact,obsolete=False).order_by('-date_created')[:1][0]
                data1 = [
                        {
                            "name": testwareRev.testware_artifact.name,
                            "version": testwareRev.version,
                            "groupID": testwareRev.groupId,
                            "artifactID": testwareRev.artifactId,
                        },
                        ]
                data = data + data1
        else:
            testwareList1 = options['testwareList'].split('-BREAK-')
            for item in testwareList1:
                print item
                testwareName,testwareVersion=item.split('-VER-')
                testwareRev=cireports.models.TestwareRevision.objects.get(testware_artifact__name=testwareName,version=testwareVersion)
                data1 = [
                        {
                            "name": testwareRev.testware_artifact.name,
                            "version": testwareRev.version,
                            "groupID": testwareRev.groupId,
                            "artifactID": testwareRev.artifactId,
                        },
                        ]
                data = data + data1
                
        print data        
        cireports.utils.createTestwarePom(data,pomVersion)
    
            

 


