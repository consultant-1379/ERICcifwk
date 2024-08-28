from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from depmodel.utils import returnStackedDependencies
from cireports.models import Package, PackageRevision
from depmodel.models import PackageDependencies

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "This option tests that dependencies are returned based on Artifact Name and Version (Stacked Dependency Functionality"
    option_list = BaseCommand.option_list  + (
            make_option('--artifactName',
                dest='artifactName',
                help='Name of the Artifact'),
            make_option('--artifactVersion',
                dest='artifactVersion',
                help='Version of the Artifact'),
            make_option('--artifactType',
                dest='artifactType',
                help='Type of the Artifact'),
            )

    def handle(self, *args, **options):
        if (options['artifactName'] == None):
            raise CommandError("Artifact Name is required, please add 'artifactName=<artifactName>")
        else:
            artifactName = options['artifactName']
        if (options['artifactVersion'] == None):
            raise CommandError("Artifact Version is required, please add 'artifactVersion=<artifactVersion>")
        else:
            artifactVersion = options['artifactVersion']
        if (options['artifactType'] == None):
            artifactType = 'rpm'
        else:
            artifactType = options['artifactType']

        artifactNameList = artifactBuildDict = artifactThirdPartyList = None

        if Package.objects.filter(name=artifactName).exists():
            artifactObj = Package.objects.get(name=artifactName)
        else:
            raise CommandError("Artifact Name does not exist in the cifwk database, please try again") 

        if PackageRevision.objects.filter(package=artifactObj, version=artifactVersion, m2type=artifactType).exists():
            artifactVersionObj = PackageRevision.objects.get(package=artifactObj, version=artifactVersion, m2type=artifactType)
        else:
            raise CommandError("Artifact Name with given Version does not exist in the cifwk database, please try again")

        if PackageDependencies.objects.filter(package=artifactVersionObj).exists():
            packageDependencyObj = PackageDependencies.objects.get(package=artifactVersionObj)
        else:
            raise CommandError("There was no Artifact dependencies found based on the input data, please try again")

        try:
            artifactNameList, artifactBuildDict, artifactThirdPartyList = returnStackedDependencies(artifactObj,artifactVersionObj,packageDependencyObj)
            if artifactNameList and artifactBuildDict and artifactThirdPartyList:
                logger.info("Artifact Depedendcies returned with Success")
            else:
                raise CommandError("Artifact Depedendcies not returned as expected")
        except Exception as e:
            raise CommandError("Issue with returning dependencies for Artifact: " + str(e))
