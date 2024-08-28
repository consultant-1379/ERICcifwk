from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from dmt.utils import *
from dmt.models import *
from cireports.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            ddTypesDict = ['rpm', 'critical-slice', 'team-slice']
            for ddType in ddTypesDict:
                if not DeploymentDescriptionType.objects.filter(dd_type=ddType).exists():
                    DeploymentDescriptionType.objects.create(dd_type=ddType)
            passedProductSetVersions = []
            dropList = ['16.11','16.12','16.13', '16.14', '16.15']
            for drop in dropList:
                logger.info("Drop: " + str(drop))
                allVersions = ProductSetVersion.objects.filter(productSetRelease__productSet__name="ENM", drop__name=drop).order_by('id')
                for item in allVersions:
                    if item.getOverallWeigthedStatus() == 'passed' or item.status.state == 'passed_manual':
                        if item.status.state != 'caution':
                            passedProductSetVersions.append(item)
            for passedPSV in passedProductSetVersions:
                logger.info("ProductSet Version: " + str(passedPSV))
                productSetVersionContent = ProductSetVersionContent.objects.only('mediaArtifactVersion__id').values('mediaArtifactVersion__id').get(productSetVersion=passedPSV, mediaArtifactVersion__drop__release__product__name="ENM")
                deploymentTemplates = ISObuildMapping.objects.only('package_revision__version').values('package_revision__version').get(iso__id=productSetVersionContent['mediaArtifactVersion__id'], package_revision__package__name="ERICenmdeploymenttemplates_CXP9031758")
                if not DeploymentDescriptionVersion.objects.filter(version=deploymentTemplates['package_revision__version']).exists():
                    updateDeploymentDescriptionsData(deploymentTemplates['package_revision__version'])
                    logger.info("Adding Deployment Descriptions Data for Product set version: " + str(passedPSV))
                else:
                    logger.info("Deployment Descriptions Data version: " + str(deploymentTemplates['package_revision__version']) + " is in DB already")
        except Exception as e:
            raise CommandError("Error found - " + str(e))


