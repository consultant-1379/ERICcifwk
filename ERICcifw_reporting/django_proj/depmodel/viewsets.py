from rest_framework import generics, permissions,status
from django.utils.decorators import method_decorator
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import detail_route
import json
from django.http import Http404, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import re
from ciconfig import CIConfig
import logging
from django.db import transaction, IntegrityError
from cireports.models import DropMediaArtifactMapping, ISObuildMapping, Package
from .models import ArtVersToPackageToISOBuildMap, AnomalyArtifactVersion, DependencyPluginArtifact, Artifact
from .utils import processAnomalyList, processAnomalyPackageRevisionMappingList, processMismatchList, processEmptyList, createPackageArtifactMapping
from .serializers import VersionedPluginsSerializer
logger = logging.getLogger(__name__)
#import collections

class ProductISOVersionApplicationsModules(APIView):
    '''
    '''
    def get(self, request, *args, **kwargs):

        if 'product' not in self.kwargs and 'isoname' not in self.kwargs and 'isoversion' not in self.kwargs:
            raise Http404("Please ensure Product, ISO Name and ISO Version are provided parameters.")

        product = self.kwargs['product']
        isoName = self.kwargs['isoname']
        isoVersion = self.kwargs['isoversion']

        try:
            dropMediaArtifactMap = DropMediaArtifactMapping.objects.get(mediaArtifactVersion__mediaArtifact__name=isoName, mediaArtifactVersion__version=isoVersion, drop__release__product__name=product)
        except Exception as error:
            raise Http404("Error: Product: " + product + ", ISOName: " + str(isoName) + " with ISOVersion: " + str(isoVersion) + " does not exist, please try again: " +str(error))

        result = {}
        #mediaArtifact = collections.OrderedDict()
        mediaArtifact = {}
        mediaArtifact["groupId"] = str(dropMediaArtifactMap.mediaArtifactVersion.groupId)
        mediaArtifact["artifactId"] = str(isoName)
        mediaArtifact["version"] = str(isoVersion)
        mediaArtifact["product"] = str(product)

        mediaContentsList = []
        rpmContentList = []
        isoBuildMapping = ISObuildMapping.objects.filter(iso=dropMediaArtifactMap.mediaArtifactVersion)

        for isoBuild in isoBuildMapping:
            #rpms = collections.OrderedDict() 
            rpms = {}
            artifactContentsList = []
            rpmContentList.append(rpms)
            artifacts = ArtVersToPackageToISOBuildMap.objects.filter(package=isoBuild.package_revision.package)
            for artifact in artifacts:
                artifactContentsList.append(str(artifact.artifact_version.groupname) + ":" + str(artifact.artifact_version.artifact.name) + ":" + str(artifact.artifact_version.version) + ":" + str(artifact.artifact_version.m2type))
            rpms["rpm"] = str(isoBuild.package_revision.groupId) + ":" + str(isoBuild.package_revision.package.name) + ":" + str(isoBuild.package_revision.version) + ":" + str(isoBuild.package_revision.m2type)
            rpms["contains"]  = artifactContentsList
        mediaArtifact["rpms"] = rpmContentList

        result["data"] = mediaArtifact
        return Response(result, status=status.HTTP_200_OK)

class GetAnomalyMatch(APIView):
    '''
    Check if specified anomaly artifact exists in the anomalyartifact database
    '''
    def get(self, request, *args, **kwargs):

        anomalyName = self.kwargs['anomalyName']
        anomalyGroupId = self.kwargs['anomalyGroupId']
        anomalyVersion = self.kwargs['anomalyVersion']
        anomalyPackaging = self.kwargs['anomalyPackaging']

        if AnomalyArtifactVersion.objects.filter(anomalyartifact__name=anomalyName, groupname=anomalyGroupId, version=anomalyVersion, m2type=anomalyPackaging).exists():
            exists =  True
        else:
            exists = False

        result = {}
        result["result"] = exists
        return Response(result, status=status.HTTP_200_OK)

class ProcessAnomalies(APIView):
    '''
    Return a HTTP response based on the success of adding anomalies to the database
    '''
    def post(self, request, *args, **kwargs):

        anomalyList = request.data.get('anomalyList')
        if not anomalyList or anomalyList == 'None':
            return HttpResponse("Error: List of Anomalies is empty.\n")
        return HttpResponse(processAnomalyList(anomalyList))

class ProcessAnomalyPackageRevisionMapping(APIView):
    '''
    Return a HTTP response based on the success of mapping rpms to anomalies in the database
    '''
    def post(self, request, *args, **kwargs):

        mappingList = request.data.get('mappingList')
        if not mappingList or mappingList == 'none':
            return HttpResponse("Error: List of RPM to Anomaly mappings is empty.\n")
        return HttpResponse(processAnomalyPackageRevisionMappingList(mappingList))

class ProcessVersionMismatches(APIView):
    '''
    Return a HTTP response based on the success of adding mismatches to the database
    '''
    def post(self, request, *args, **kwargs):

        mismatchList = request.data.get('mismatchList')
        emptyList = request.data.get('emptyList')
        if not mismatchList and not emptyList:
            return HttpResponse("ERROR: Please include either mismatchList or emptyList parameter..\n")
        if not mismatchList:
            return HttpResponse(processEmptyList(emptyList))
        elif not emptyList:
            return HttpResponse(processMismatchList(mismatchList))

class GetVersionedPluginsViewSet(viewsets.ModelViewSet):
    '''
    Return json containing group/artifact IDs of the plugins that require versioning with the bom. 
    '''
    model = DependencyPluginArtifact
    serializer_class = VersionedPluginsSerializer
    queryset = DependencyPluginArtifact.objects.all()

class CreatePackageArtifactMapping(APIView):
    """
    Return a HTTP response based on the success of adding Artifacts and linking them to Packages
    """
    def post(self, request, *args, **kwargs):
        rpms = request.data.get('rpms')
        repo = request.data.get('git_repo')
        return createPackageArtifactMapping(repo, rpms)
