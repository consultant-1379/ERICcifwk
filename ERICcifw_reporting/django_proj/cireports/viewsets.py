from rest_framework import generics, permissions, status
from django.utils.decorators import method_decorator
from .serializers import ProductSetVersionSerializer, ISOBuildSerializer, ComponentSerializer, \
    PackageComponentSerializer, ProductSetVersionContentSerializer, ISOBuildVersionSerializer
from .models import DeliveryGroupSubscription, ProductSetVersion, ISObuild, Component, PackageComponentMapping, Product, \
    Drop, ProductSetVersionContent, Package, DeliveryGroup, DeliverytoPackageRevMapping, PackageRevision, \
    PackageNameExempt, CDBTypes, TestwareArtifact, PackageWithTestCaseResult, Drop, TestCaseResult, \
    ReasonsForNoKGBStatus, ProductSetRelease, TestwareType, TestwareTypeMapping
from dmt.models import VmServicePackageMapping
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import detail_route
import json
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User, Group
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
import re
from ciconfig import CIConfig

config = CIConfig()
import logging
from .utils import deliverAutoCreatedGroup, jiraValidation, mapProductToPackage, sendPackageMail, \
    preRegisterENMArtifact, getGroupPackageVerisonsInBaseline, getWarningForPackageVersionInBaseline, \
    getBomsFromIsoList, getPackagesInTeam, getFlowContext, returnNewToIso, updateJiraData, restCreateDeliveryGroup, \
    getDeliveryGroupPkgRevFrozenKGB, getDropPkgRevFrozenKGB, getMediaArtifactContentPkgRevFrozenKGB, getJiraCredentials, \
    getNexusUrlForArtifactVersion, deliverAutoCreatedGroups, getWarningForJiraType, getLatestPassedKGBdataForArtifact, \
    getMediaArtifactProductToTestwareMapping, getProductwaretoTestwareMappingByDrop, setMediaArtifactVerInactive, \
    setMediaArtifactVerInactiveByDrop, checkNexus, setExternallyReleasedMediaArtifactVersion, \
    getExternallyReleasedMediaArtifactVersion, getProductSetDropData, getMediaArtifactVersionData, \
    getLatestProductDropName, getDropMediaDeployData, getActiveDropsInProductSet, createDeliveryGroupCommment, \
    getProductSize, obsoleteDeliveryGroupArtifacts, getExceptionForJiraProject, getJiraAccessTokenHeader, overrideConfidenceLevel, \
    getDropByProductSetVersion
from django.db import transaction, IntegrityError
from fem.utils import getTeamParentElement
from .renderers import PlainTextRenderer
from django.core import serializers
from datetime import datetime
from rest_framework.renderers import JSONRenderer
from cireports.models import *
from cireports.generateReleaseNote import *
import requests
import time
from cireports.DGThread import DGThread
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.parsers import JSONParser
from cireports.cloudNativeUtils import createCNBuildLogData, getCNBuildLogId, createCNBuildLogComment, \
    getCNBuildLogDataByDrop, updateCNBuildLogOverallStatus, hideCNBuildLog, editCNBuildLogComment, \
    deleteCNBuildLogComment, deleteCNBuildLogJira

logger = logging.getLogger(__name__)


class ProductSetVersionViewSet(viewsets.ModelViewSet):
    '''
    To Get All The Product Set Versions in a Product Set Drop
    '''
    model = ProductSetVersion
    serializer_class = ProductSetVersionSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        productSet = self.kwargs['productSet']
        dropName = self.kwargs['dropName']
        return ProductSetVersion.objects.filter(drop__name=dropName,
                                                productSetRelease__release__product__name=productSet).order_by('-id')


class ProductSetVersionContentsSet(viewsets.ModelViewSet):
    model = ProductSetVersionContent
    serializer_class = ProductSetVersionContentSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        product_set_version = self.kwargs['version']
        product_set_number = self.kwargs['number']
        products = ProductSetVersionContent.objects.filter(productSetVersion__version=product_set_version,
                                                           productSetVersion__productSetRelease__number=product_set_number)
        return products


class ProductSetVersionLatestViewSet(APIView):
    '''
    To Get The latest Product Set Version in a Product Set Drop
    '''
    renderer_classes = (PlainTextRenderer,)

    def get(self, request, *args, **kwargs):
        productSet = self.kwargs['productSet']
        dropName = self.kwargs['dropName']
        content = None
        try:
            content = ProductSetVersion.objects.filter(drop__name=dropName,
                                                       productSetRelease__productSet__name=productSet).order_by('-id')[
                0].version
        except Exception as e:
            content = "Issue getting the Latest Product Set Version, Error thrown: " + str(e)
            logger.error(content)
            return Response(content, status=status.HTTP_404_NOT_FOUND)
        return Response(content, status=status.HTTP_200_OK)


class ISOBuildViewSet(viewsets.ModelViewSet):
    model = ISObuild
    serializer_class = ISOBuildSerializer
    permission_classes = [
        permissions.AllowAny
    ]
    queryset = ISObuild.objects.all()


class ISOBuildDropViewSet(viewsets.ModelViewSet):
    model = ISObuild
    serializer_class = ISOBuildSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        if 'dropName' in self.kwargs and 'artifactName' in self.kwargs and 'version' in self.kwargs:
            version_number = self.kwargs['version']
            artifact_name = self.kwargs['artifactName']
            drop_name = self.kwargs['dropName']
            return ISObuild.objects.filter(drop__name=drop_name).filter(mediaArtifact__name=artifact_name).filter(
                version=version_number)
        elif 'dropName' in self.kwargs and 'artifactName' in self.kwargs:
            artifact_name = self.kwargs['artifactName']
            drop_name = self.kwargs['dropName']
            return ISObuild.objects.filter(drop__name=drop_name).filter(mediaArtifact__name=artifact_name)
        elif 'dropName' in self.kwargs and 'productName' in self.kwargs:
            drop_name = self.kwargs['dropName']
            product_name = self.kwargs['productName']
            if not Product.objects.filter(name=product_name).exists():
                raise Http404("Product " + product_name + " does not exist.")
            if not Drop.objects.filter(name=drop_name).filter(release__product__name=product_name).exists():
                raise Http404("Drop " + drop_name + " does not exist for product " + product_name + ".")
            return ISObuild.objects.filter(drop__name=drop_name).filter(
                drop__release__product__name=product_name).filter(mediaArtifact__testware=0)
        elif 'dropName' in self.kwargs:
            drop_name = self.kwargs['dropName']
            return ISObuild.objects.filter(drop__name=drop_name)


class ISOBuildVersionsForDiffViewSet(viewsets.ModelViewSet):
    model = ISObuild
    serializer_class = ISOBuildVersionSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        category = "productware"
        product_name = self.kwargs['product']
        drop_name = self.kwargs['drop']
        type = self.kwargs['type']
        if not Product.objects.filter(name=product_name).exists():
            raise Http404("Product " + product_name + " does not exist.")
        if not Drop.objects.filter(name=drop_name).filter(release__product__name=product_name).exists():
            raise Http404("Drop " + drop_name + " does not exist for product " + product_name + ".")
        requiredISOBuildFields = ('version', 'current_status')
        if 'iso' == type:
            return ISObuild.objects.filter(drop__name=drop_name, drop__release__product__name=product_name,
                                           mediaArtifact__testware=0, mediaArtifact__category__name=category).order_by(
                '-build_date').only(requiredISOBuildFields).values(*requiredISOBuildFields)
        elif 'bom' == type:
            isoObjs = ISObuild.objects.filter(drop__name=drop_name, mediaArtifact__testware=False,
                                              drop__release__product__name=product_name,
                                              mediaArtifact__category__name=category).order_by('-build_date').only(
                requiredISOBuildFields).values(*requiredISOBuildFields)
            ret = getBomsFromIsoList(isoObjs)
            return ret
        else:
            raise Http404(type + ' is not a valid choice. Enter either iso or bom')


class ComponentViewSet(viewsets.ModelViewSet):
    model = Component
    serializer_class = ComponentSerializer
    permission_classes = [
        permissions.AllowAny
    ]
    queryset = Component.objects.all()


class ComponentProductViewSet(viewsets.ModelViewSet):
    model = Component
    serializer_class = ComponentSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        if 'product' in self.kwargs and 'label' in self.kwargs:
            product_name = self.kwargs['product']
            label_name = self.kwargs['label']
            return Component.objects.filter(product__name=product_name, label__name=label_name, deprecated=0).order_by(
                'element')
        elif 'product' in self.kwargs:
            product_name = self.kwargs['product']
            return Component.objects.filter(product__name=product_name)


class PackageComponentViewSet(viewsets.ModelViewSet):
    model = PackageComponentMapping
    serializer_class = PackageComponentSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        packageName = self.kwargs['package']
        return PackageComponentMapping.objects.filter(package__name=packageName, component__deprecated=0)


class CifwkConfigViewSet(APIView):
    def get(self, request, *args, **kwargs):
        '''
        This function retrieves details from the cifwk.cfg file
        for the input section and option
        '''
        section = self.kwargs["section"]
        option = self.kwargs["option"]

        try:
            config = CIConfig()
            value = config.get(section, option)
            result = [{option: value}]
        except Exception as e:
            logger.error(
                "There was no value for section: " + section + " and option: " + option + ", Error thrown: " + str(e))
            result = [{"error": re.sub("u'([^']*)'", r'\1', str(e))}]
            return Response(result, status=status.HTTP_404_NOT_FOUND)

        return Response(result, status=status.HTTP_200_OK)


class GetMediaArtifactDateAndSize(APIView):
    '''
    Getting Media Artifact build date and size by media name and version
    '''

    def get(self, request, *args, **kwargs):
        statusCode = '200'
        try:
            mediaArtifact = self.kwargs['mediaArtifactName']
            version = self.kwargs['mediaArtifactVersion']
            result, statusCode = getProductSize(mediaArtifact, version)
            if statusCode != 200:
                return Response({'ERROR': result}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting Media Artifact data: " + str(e)
            logger.error(errMsg)
            return Response({'ERROR': errMsg}, status=status.HTTP_404_NOT_FOUND)


class DropDeliveryQueueArtifactsViewSet(APIView):
    def get(self, request, *args, **kwargs):
        queueTypes = "queued, delivered"
        if 'drop' not in self.kwargs:
            return Response("Please provide Drop.", status=status.HTTP_404_NOT_FOUND)
        elif 'queueStatus' not in self.kwargs or self.kwargs['queueStatus'] not in queueTypes:
            return Response("Please provide the queue status. Valid choices are: " + queueTypes,
                            status=status.HTTP_404_NOT_FOUND)
        elif 'product' not in self.kwargs:
            return Response("Please provide Product.", status=status.HTTP_404_NOT_FOUND)
        elif 'drop' in self.kwargs and 'product' in self.kwargs:
            product = self.kwargs['product']
            drop = self.kwargs['drop']
            queueStatus = self.kwargs['queueStatus']
            version = request.query_params.get('version', None)
            groupId = request.query_params.get('groupId', None)
            artifactId = request.query_params.get('artifact', None)
            createdByTeam = request.query_params.get('createdByTeam', None)
            deliveryGroup = request.query_params.get('deliveryGroup', None)
            deliveredBool = False

            if not Product.objects.filter(name=product).exists():
                return Response("Product " + product + " does not exist.", status=status.HTTP_404_NOT_FOUND)
            if not Drop.objects.filter(name=drop, release__product__name=product).exists():
                return Response("Drop " + drop + " does not exist for product " + product + ".",
                                status=status.HTTP_404_NOT_FOUND)

            groups = []
            requiredDeliveryGroupFields = (
            'id', 'component__element', 'component__parent__element', 'modifiedDate', 'createdDate', 'drop',
            'delivered', 'creator', 'component', 'deliveredDate', 'autoCreated', 'bugOrTR', 'ccbApproved',
            'missingDependencies')
            if queueStatus in "delivered":
                deliveredBool = True
            deliveryGroups = DeliveryGroup.objects.select_related('component').filter(drop__name=drop,
                                                                                      drop__release__product__name=product,
                                                                                      deleted=False,
                                                                                      delivered=deliveredBool,
                                                                                      obsoleted=False).order_by(
                '-modifiedDate').only(requiredDeliveryGroupFields).values(*requiredDeliveryGroupFields)
            for delGroup in deliveryGroups:
                if createdByTeam and delGroup['component__element'] is not None and str(
                        delGroup['component__element']) != createdByTeam:
                    continue
                if deliveryGroup and str(delGroup['id']) != deliveryGroup:
                    continue

                artifacts = []
                requiredDeliverytoPackageRevMappingFields = (
                'id', 'packageRevision__id', 'packageRevision__version', 'packageRevision__groupId',
                'packageRevision__artifactId', 'packageRevision__date_created', 'packageRevision__category__name')
                deliveryPkgRevMaps = DeliverytoPackageRevMapping.objects.select_related(
                    'packageRevision__package').filter(deliveryGroup__id=delGroup['id']).only(
                    requiredDeliverytoPackageRevMappingFields).values(*requiredDeliverytoPackageRevMappingFields)
                pkgNames = []
                for map in deliveryPkgRevMaps:
                    pkgNames.append(map['packageRevision__artifactId'])

                requiredPackagetoVmServiceMappingFields = ('package__name', 'service__name')
                pkgVmMaps = VmServicePackageMapping.objects.select_related('package__name').filter(
                    package__name__in=pkgNames).only(requiredPackagetoVmServiceMappingFields).values(
                    *requiredPackagetoVmServiceMappingFields)
                for map in deliveryPkgRevMaps:
                    if version and str(map['packageRevision__version']) != version:
                        continue
                    if groupId and str(map['packageRevision__groupId']) != groupId:
                        continue
                    if artifactId and str(map['packageRevision__artifactId']) != artifactId:
                        continue
                    vmServices = []
                    for pkgVmMap in pkgVmMaps:
                        if pkgVmMap['package__name'] in map['packageRevision__artifactId']:
                            vmServices.append(str(pkgVmMap['service__name']))
                    artifact = {}
                    artifact["artifact"] = str(map['packageRevision__artifactId'])
                    artifact["version"] = str(map['packageRevision__version'])
                    artifact["groupId"] = str(map['packageRevision__groupId'])
                    artifact["dateCreated"] = str(map['packageRevision__date_created'])
                    artifact["vmServices"] = vmServices
                    artifact["sprintVersionCheck"] = cireports.utils.checkSprintVersionByArtifactId(product, drop, str(
                        map['packageRevision__artifactId']), str(map['packageRevision__version']))
                    artifact["category"] = str(map['packageRevision__category__name'])
                    artifacts.append(artifact)

                if len(artifacts) == 0:
                    continue
                group = {}
                group["deliveryGroup"] = str(delGroup['id'])
                if delGroup['component__element'] is not None:
                    group["createdByTeam"] = str(delGroup['component__element'])
                    group["parentElement"] = str(delGroup['component__parent__element'])
                else:
                    group["createdByTeam"] = ""
                if delGroup['modifiedDate'] is not None:
                    group["modifiedDate"] = str(delGroup['modifiedDate'])
                else:
                    group["modifiedDate"] = ""
                if delGroup['createdDate'] is not None:
                    group["createdDate"] = str(delGroup['createdDate'])
                if delGroup['creator'] is not None:
                    group["creator"] = str(delGroup['creator'])
                if delGroup['component'] is not None:
                    group["component"] = str(delGroup['component'])
                if delGroup['deliveredDate'] is not None:
                    group["deliveredDate"] = str(delGroup['deliveredDate'])
                if delGroup['autoCreated'] is not None:
                    group["autoCreated"] = str(delGroup['autoCreated'])
                if delGroup['bugOrTR'] is not None:
                    group["bugOrTR"] = str(delGroup['bugOrTR'])
                if delGroup['ccbApproved'] is not None:
                    group["ccbApproved"] = str(delGroup['ccbApproved'])
                if delGroup['missingDependencies'] is not None:
                    group["missingDependencies"] = str(delGroup['missingDependencies'])
                group["artifacts"] = artifacts
                groups.append(group)

            return Response(groups, status=status.HTTP_200_OK)


class ArtifactAssociationViewSet(APIView):
    def get(self, request, *args, **kwargs):
        try:
            if 'lookup' not in self.kwargs:
                if label.lower() != 'all':
                    return Response("Please provide team/parentElement/artifact to lookup.",
                                    status=status.HTTP_404_NOT_FOUND)
            if 'label' not in self.kwargs:
                return Response("Please provide team/parentElement/artifact label to lookup.",
                                status=status.HTTP_404_NOT_FOUND)
            if 'product' not in self.kwargs:
                product = 'ENM'
            else:
                product = self.kwargs['product']

            lookup = self.kwargs['lookup']
            label = self.kwargs['label']
            ret = parentElements = teams = []
            exceptTeams = config.get("CIFWK", "raHistoricalTeams")

            if label.lower() == 'team':
                label = 'Team'
                componentObj = Component.objects.only('parent__element').values('parent__element', 'parent__deprecated',
                                                                                'deprecated').filter(label__name=label,
                                                                                                     element=lookup,
                                                                                                     product__name=product)
                if componentObj:
                    for teamObj in componentObj:
                        if (teamObj['parent__deprecated'] == False and teamObj['deprecated'] == False) or (
                                teamObj['parent__element'] == exceptTeams and teamObj['parent__deprecated'] == False):
                            entry = {'artifacts': getPackagesInTeam(lookup, product),
                                     'team': lookup,
                                     'parentElement': teamObj['parent__element']}
                            ret.append(entry)
                        else:
                            ret = [{'artifacts': "", 'team': "", 'parentElement': ""}]
                else:
                    ret = [{'artifacts': "", 'team': "", 'parentElement': ""}]
                    return Response(ret, status=status.HTTP_404_NOT_FOUND)
            elif label.lower() == 'parentelement':
                teamComponentObj = Component.objects.only('element').values('element', 'parent__element').filter(
                    label__name='Team', parent__element=lookup, parent__deprecated=0)
                if lookup.lower() != exceptTeams.lower():
                    teamComponentObj = teamComponentObj.filter(deprecated=0)
                if teamComponentObj:
                    for teamObj in teamComponentObj:
                        entry = {'artifacts': getPackagesInTeam(teamObj['element'], product),
                                 'team': teamObj['element'],
                                 'parentElement': lookup}
                        ret.append(entry)
                else:
                    ret = [{'artifacts': "", 'team': "", 'parentElement': ""}]
                    return Response(ret, status=status.HTTP_404_NOT_FOUND)
            elif label.lower() == 'artifact':
                artifacts = [lookup]
                team, parentElement = getTeamParentElement(lookup)
                entry = {'artifacts': artifacts,
                         'team': team,
                         'parentElement': parentElement}
                ret.append(entry)
            elif label.lower() == 'all':
                parentElementComponentObj = Component.objects.only('element').values('element').filter(
                    parent__isnull=True, product__name=product, deprecated=0)
                for parentElementObj in parentElementComponentObj:
                    teamComponentObj = Component.objects.only('element').values('element').filter(label__name='Team',
                                                                                                  parent__element=
                                                                                                  parentElementObj[
                                                                                                      'element'])
                    if parentElementObj['element'] != exceptTeams:
                        teamComponentObj = teamComponentObj.filter(deprecated=0)
                    for teamObj in teamComponentObj:
                        entry = {'artifacts': getPackagesInTeam(teamObj['element'], product),
                                 'team': teamObj['element'],
                                 'parentElement': parentElementObj['element']}
                        ret.append(entry)

            else:
                ret = [{'artifacts': "", 'team': "", 'parentElement': ""}]
                return Response(ret, status=status.HTTP_404_NOT_FOUND)
        except:
            ret = [{'artifacts': "", 'team': "", 'parentElement': ""}]
            return Response(ret, status=status.HTTP_404_NOT_FOUND)
        return Response(ret, status=status.HTTP_200_OK)


class JIRAValidationViewSet(APIView):
    def get(self, request, *args, **kwargs):
        jiras = self.kwargs['number'].split(",")
        resultOfJiraCheck = []
        jiraNotFound = False

        for jira in jiras:
            validate = {}
            result, statusCode = jiraValidation(jira)

            validate['jiraIssue'] = jira
            if statusCode == "404" or statusCode == "200":
                if statusCode == "404":
                    validate['result'] = "invalid"
                    jiraNotFound = True
                elif statusCode == "200":
                    isJiraValidationPass, jiraWarning, issueType = getWarningForJiraType(result)
                    if jiraWarning != None:
                        validate['warning'] = jiraWarning
                    validate['jiraType'] = issueType
                    validate['result'] = "valid"
                resultOfJiraCheck.append(validate)
            else:
                return Response("Issue with JIRA connection ", status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if jiraNotFound:
            return Response(resultOfJiraCheck, status=status.HTTP_404_NOT_FOUND)
        return Response(resultOfJiraCheck, status=status.HTTP_200_OK)


class CENMJIRAValidationViewSet(APIView):
    def get(self, request, *args, **kwargs):
        jiras = self.kwargs['number'].split(",")
        resultOfJiraCheck = []
        jiraNotFound = False
        isProjectExcept = False

        for jira in jiras:
            validate = {}
            result, statusCode = jiraValidation(jira)

            validate['jiraIssue'] = jira
            if statusCode == "404" or statusCode == "200":
                if statusCode == "404":
                    validate['result'] = "invalid"
                    jiraNotFound = True
                elif statusCode == "200":
                    isProjectExcept = getExceptionForJiraProject(result)
                    if not isProjectExcept:
                        isJiraValidationPass, jiraWarning, issueType = getWarningForJiraType(result)
                        if jiraWarning:
                            validate['warning'] = jiraWarning
                        validate['jiraType'] = issueType
                    validate['result'] = "valid"
                resultOfJiraCheck.append(validate)
            else:
                return Response("Issue with JIRA connection ", status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if jiraNotFound:
            return Response(resultOfJiraCheck, status=status.HTTP_404_NOT_FOUND)
        return Response(resultOfJiraCheck, status=status.HTTP_200_OK)


class UpdateJiraData(APIView):
    def put(self, request, *args, **kwargs):
        if 'product' not in self.kwargs:
            product = 'ENM'
        else:
            product = self.kwargs['product']
        if 'drop' not in self.kwargs:
            drop = 'None'
        else:
            drop = self.kwargs['drop']
        result = updateJiraData(product, drop)
        if "Error" in result:
            return Response(result, status=status.HTTP_501_NOT_IMPLEMENTED)
        return Response(result, status=status.HTTP_200_OK)


class CreateProductPackageViewSet(APIView):
    def post(self, request, *args, **kwargs):
        product = self.kwargs['product']

        packageName = request.data.get('packageName')
        packageNumber = request.data.get('packageNumber')
        signum = request.data.get('signum')
        category = request.data.get('mediaCategory')

        if not product or product == 'None' or product != 'ENM':
            return HttpResponse("Error: Package can be created only for ENM.\n")
        if not packageName or packageName == 'None':
            return HttpResponse("Error: Package name is required.\n")
        if not packageNumber or packageNumber == 'None':
            return HttpResponse("Error: Package number is required.\n")
        if not signum or signum == 'None':
            return HttpResponse("Error: User signum is required.\n")
        if not category or category == 'None':
            return HttpResponse("Error: Media category is required.\n")

        return HttpResponse(preRegisterENMArtifact(product, packageName, packageNumber, signum, category))


class TestwareArtifactTestSuiteStatus(APIView):
    '''
    The TestwareArtifactTestSuiteStatus REST Service:
        POST:   Updates Testware Artifacts with a Flag to indictate if its included in a Priority Test Suite
        GET:    Returns if the testware artifact is included in a Priority Test Suite
    '''

    def get(self, request, *args, **kwargs):
        try:
            overallResult = {}
            individualResult = {}
            resultList = []
            product = self.kwargs['product']
            artifact = self.kwargs['testwareartifacts']
            individualResult['testwareTypes'] = []
            testwareArtifact = Package.objects.only('id', 'includedInPriorityTestSuite').values('id',
                                                                                                'includedInPriorityTestSuite').get(
                name=artifact)
            individualResult['priorityTestware'] = testwareArtifact['includedInPriorityTestSuite']
            testwareTypeMappings = TestwareTypeMapping.objects.only('testware_type__type').values(
                'testware_type__type').filter(testware_artifact__id=testwareArtifact['id'])
            if testwareTypeMappings:
                individualResult['testwareTypes'] = [testwareTypeMap['testware_type__type'] for testwareTypeMap in
                                                     testwareTypeMappings]
            resultList.append(individualResult)
            overallResult['success'] = resultList
            return Response(overallResult, status=status.HTTP_200_OK)
        except Exception as error:
            individualResult['error'] = str(error)
            resultList.append(individualResult)
            overallResult['error'] = resultList
            return Response(overallResult, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, *args, **kwargs):
        product = self.kwargs['product']
        testwareArtifacts = self.kwargs['testwareartifacts'].split(":")
        testwareType = request.POST.get('testwareType', 'RFA250')
        testwareTypeObj = ""
        try:
            testwareTypeObj = TestwareType.objects.get(type=testwareType)
            TestwareTypeMapping.objects.filter(testware_type=testwareTypeObj).delete()
        except Exception as error:
            return Response("error " + str(testwareType) + " : " + str(error), status=status.HTTP_404_NOT_FOUND)
        for testwareArtifact in testwareArtifacts:
            try:
                testwareArtifactObj = Package.objects.get(name=testwareArtifact)
                TestwareTypeMapping.objects.create(testware_artifact=testwareArtifactObj, testware_type=testwareTypeObj)
            except Exception as error:
                return Response("error " + str(testwareArtifact) + " : " + str(error), status=status.HTTP_404_NOT_FOUND)
        # Setting includedInPriorityTestSuite
        allTestwareArtifacts = Package.objects.filter(testware=True)
        for testwareArtifactObj in allTestwareArtifacts:
            if TestwareTypeMapping.objects.filter(testware_artifact=testwareArtifactObj).exists():
                testwareArtifactObj.includedInPriorityTestSuite = True
            else:
                testwareArtifactObj.includedInPriorityTestSuite = False
            testwareArtifactObj.save()
        return Response("success", status=status.HTTP_200_OK)


class GroupPackageVersionValidationViewSet(APIView):
    '''
    Validation of Artifact Version in a Delivery Group
    '''

    def get(self, request, *args, **kwargs):
        checkResult = {}
        try:
            productName = self.kwargs['product']
            dropName = self.kwargs['drop']
            groupId = self.kwargs["groupId"]
            result = getGroupPackageVerisonsInBaseline(productName, dropName, groupId)
            if "WARNING" in str(result):
                checkResult['result'] = result
            else:
                checkResult['result'] = ""
            return Response(checkResult, status=status.HTTP_200_OK)
        except Exception as error:
            checkResult['result'] = str(error)
            return Response(checkResult, status=status.HTTP_404_NOT_FOUND)


class PackageVersionValidationViewSet(APIView):
    '''
    Validation of Artifact Version
    '''

    def get(self, request, *args, **kwargs):
        checkResult = {}
        try:
            productName = self.kwargs['product']
            dropName = self.kwargs['drop']
            packageName = self.kwargs["package"]
            version = self.kwargs["version"]
            try:
                groupId = self.kwargs["groupId"]
            except:
                groupId = None
            result = getWarningForPackageVersionInBaseline(productName, dropName, packageName, version, groupId)
            if "WARNING" in str(result):
                checkResult['result'] = result
            elif "Error:" in str(result):
                checkResult['result'] = result
                return Response(checkResult, status=status.HTTP_404_NOT_FOUND)
            else:
                checkResult['result'] = ""
            return Response(checkResult, status=status.HTTP_200_OK)
        except Exception as error:
            checkResult['result'] = str(error)
            return Response(checkResult, status=status.HTTP_404_NOT_FOUND)


class ReturnFlowContext(APIView):
    def get(self, request, *args, **kwargs):
        if 'product' not in self.kwargs:
            product = 'ENM'
        else:
            product = self.kwargs['product']
        flowContext = getFlowContext(product)
        return Response(flowContext, status=status.HTTP_200_OK)


class ReturnArtifactsNotInIso(APIView):
    def get(self, request, *args, **kwargs):
        defaultGroup = config.get("FEM", "defaultGroup")
        defaultArtifact = config.get("FEM", "defaultArtifact")
        artifactsAndVersions = request.GET.get("artifacts", "")
        isoVersion = request.GET.get("isoversion", "none")
        isoGroup = request.GET.get("isogroup", defaultGroup)
        isoArtifact = request.GET.get("isoname", defaultArtifact)
        ret = returnNewToIso(artifactsAndVersions, isoVersion, isoGroup, isoArtifact)
        return Response(ret, status=status.HTTP_200_OK)


class GetArtifactVersionData(APIView):
    def get(self, request, *args, **kwargs):
        artifactName = self.kwargs["artifactName"]
        artifactVersion = self.kwargs["artifactVersion"]
        fields = 'package__name', 'version', 'category__name', 'kgb_test', 'package__testware',
        try:
            packageRevisonData = PackageRevision.objects.only(fields).values(*fields).get(package__name=artifactName,
                                                                                          version=artifactVersion)
            if packageRevisonData['package__testware'] is True:
                return Response({'kgb_test': 'passed'}, status=status.HTTP_200_OK)
            return Response(packageRevisonData, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({
                                'error': 'There was no data returned for artifact name: " + str(artifactName) + " with version: " + str(artifactVersion) + " " + str(error)'},
                            status=status.HTTP_404_NOT_FOUND)


class GetActiveReasonsForNoKGBStatus(APIView):
    def get(self, request, *args, **kwargs):
        try:
            if self.kwargs["active"].lower() == "true":
                active = True
            elif self.kwargs["active"].lower() == "false":
                active = False
            else:
                return Response({'error': 'There was an issue with ative parameter, please use True or False'},
                                status=status.HTTP_404_NOT_FOUND)
            fields = 'reason', 'active'
            activeReasons = ReasonsForNoKGBStatus.objects.only(fields).values(*fields).filter(active=active).order_by(
                'reason')
            return Response(activeReasons, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'error': 'There was an isssue get Active reasons for not running KGB: " + str(error)'},
                            status=status.HTTP_404_NOT_FOUND)


class DeliveryGroupSubscribeViewSet(APIView):
    '''
    Delivery Group subscription
    '''

    def post(self, request, *args, **kwargs):
        user = User.objects.get(username=str(request.user))
        groupId = request.data['deliveryGroup']

        try:
            deliveryGroup = DeliveryGroup.objects.get(pk=groupId)
            if DeliveryGroupSubscription.objects.filter(user=user, deliveryGroup=deliveryGroup).exists():
                DeliveryGroupSubscription.objects.filter(user=user, deliveryGroup=deliveryGroup).delete()
            else:
                DeliveryGroupSubscription.objects.create(user=user, deliveryGroup=deliveryGroup)
        except Exception as error:
            return Response("error: " + str(error), status=status.HTTP_404_NOT_FOUND)
        return Response("success", status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        if request.user is None:
            return Response("User is not found", status=status.HTTP_404_NOT_FOUND)

        user = User.objects.get(username=str(request.user))
        return Response(serializers.serialize("python", DeliveryGroupSubscription.objects.filter(user=user)))


class CreateDeliveryGroup(APIView):
    def post(self, request):
        data = request.data
        result, statusCode = restCreateDeliveryGroup(data)
        if statusCode == "200":
            return Response(result, status=status.HTTP_200_OK)
        elif statusCode == "201":
            return Response(result, status=status.HTTP_201_CREATED)
        elif statusCode == "404":
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(result, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ReturnTestCaseResult(APIView):

    def get(self, request):
        startDate = request.GET.get('startDate', 'None')
        endDate = request.GET.get('endDate', 'None')
        product = request.GET.get('product', 'None')
        drop = request.GET.get('drop', 'None')
        phase = request.GET.get('phase', 'None')

        if startDate is None or not startDate or startDate == "None":
            return Response("Error: startDate required\n", status=status.HTTP_404_NOT_FOUND)
        if product is None or not product or product == "None":
            return Response("Error: product required\n", status=status.HTTP_404_NOT_FOUND)
        if drop is None or not drop or drop == "None":
            return Response("Error: drop required\n", status=status.HTTP_404_NOT_FOUND)
        if phase is None or not phase or phase == "None":
            phase = "kgb"

        try:
            if endDate is None or not endDate or endDate == "None":
                endDateTime = datetime.now()
            else:
                endDateTime = datetime.strptime(str(endDate), "%Y-%m-%d")
            startDateTime = datetime.strptime(str(startDate), "%Y-%m-%d")
        except Exception as e:
            return Response("Error: Date format is not proper : " + str(e), status=status.HTTP_404_NOT_FOUND)

        if startDateTime > endDateTime:
            return Response("Error: Start date comes after end date", status=status.HTTP_404_NOT_FOUND)

        try:
            dropObj = Drop.objects.get(name=drop, release__product__name=product)
        except Drop.DoesNotExist:
            return Response("Error: Drop " + drop + " does not exist for " + product + ".\n",
                            status=status.HTTP_404_NOT_FOUND)

        resultSummary = ""
        try:
            fields = ('testdate', 'package__name', 'package_revision__version', 'testcaseresult__passed',
                      'testcaseresult__failed', 'testcaseresult__skipped')
            packageWithTestCaseResults = PackageWithTestCaseResult.objects.only(*fields).values(*fields).filter(
                drop=dropObj, testdate__gte=startDateTime, testdate__lte=endDateTime, phase=phase).order_by('-testdate')
            dayWiseResult = {}
            for packageWithTestCaseResult in packageWithTestCaseResults:
                date = packageWithTestCaseResult['testdate'].strftime("%Y-%m-%d")
                packageName = packageWithTestCaseResult['package__name']
                testResult = {
                    "time": packageWithTestCaseResult['testdate'].strftime("%H:%M:%S"),
                    "name": packageWithTestCaseResult['package__name'],
                    "version": packageWithTestCaseResult['package_revision__version'],
                    "passed": packageWithTestCaseResult['testcaseresult__passed'],
                    "failed": packageWithTestCaseResult['testcaseresult__failed'],
                    "skipped": packageWithTestCaseResult['testcaseresult__skipped'],
                }

                if dayWiseResult.has_key(date):
                    packageMap = dayWiseResult[date]
                    if not packageMap.has_key(packageName):
                        team, parent = getTeamParentElement(packageWithTestCaseResult['package__name'])
                        testResult['team'] = team
                        packageMap[packageName] = testResult
                else:
                    packageMap = {}
                    team, parent = getTeamParentElement(packageWithTestCaseResult['package__name'])
                    testResult['team'] = team
                    packageMap[packageName] = testResult
                    dayWiseResult[date] = packageMap
            return HttpResponse(json.dumps(dayWiseResult, sort_keys=True, indent=4), content_type="application/json")

        except Exception as e:
            logger.error("Issue==>" + str(e) + " while fetching TestCase data")
            resultSummary = resultSummary + "\n ERROR: Unspecified failure: " + str(e)
            return Response(str(resultSummary), status=status.HTTP_404_NOT_FOUND)


class AddTestCaseResult(APIView):

    def post(self, request):
        '''
        REST call to add a TestCase result of a package revision to CIFWK Database
        '''
        passed = request.POST.get("passed")
        failed = request.POST.get("failed")
        skipped = request.POST.get('skipped')
        packageName = request.POST.get("packageName")
        version = request.POST.get('version')
        drop = request.POST.get('drop')
        product = request.POST.get('product')
        phase = request.POST.get('phase')

        resultSummary = ""
        if passed is None or not passed or passed == "None":
            return HttpResponse("Error: No of TC passed required\n")
        if failed is None or not failed or failed == "None":
            return HttpResponse("Error: No of TC failed required\n")
        if skipped is None or not skipped or skipped == "None":
            return HttpResponse("Error: No of TC skipped required\n")
        if packageName is None or not packageName or packageName == "None":
            return HttpResponse("Error: Package Name required\n")
        if version is None or not version or version == "None":
            return HttpResponse("Error: Version required\n")
        if drop is None or not drop or drop == "None":
            return HttpResponse("Error: Drop name required\n")
        if product is None or not product or product == "None":
            return HttpResponse("Error: Product name required\n")
        if phase is None or not phase or phase == "None":
            phase = "kgb"

        if not PackageRevision.objects.filter(artifactId=packageName, version=version).exists():
            return HttpResponse(
                packageName + " version " + version + " does not exist. Check package details and ensure package is in CI-Fwk DB.\n")
        if not Product.objects.filter(name=product).exists():
            return HttpResponse("Error: Product " + product + " does not exist.\n")

        try:
            dropObj = Drop.objects.get(name=drop, release__product__name=product)
        except Drop.DoesNotExist:
            return HttpResponse("Error: Drop " + drop + " does not exist for " + product + ".\n")

        try:
            packageRevisionObj = PackageRevision.objects.get(artifactId=packageName, version=version)
            testCaseResultObj = TestCaseResult.objects.create(passed=passed, failed=failed, skipped=skipped)
            resultiMapObj = PackageWithTestCaseResult(package_id=packageRevisionObj.package.id,
                                                      package_revision_id=packageRevisionObj.id, drop_id=dropObj.id,
                                                      testcaseresult_id=testCaseResultObj.id, phase=phase)
            resultiMapObj.save()
            resultSummary = "SUCCESS: TestCase ==>" + str(testCaseResultObj) + " for package " + str(
                packageRevisionObj) + " successfully added to CIFWK database. \n"
        except Exception as e:
            logger.error("Issue ==>" + str(e) + "while adding TestCase")
            resultSummary = resultSummary + "\n ERROR: Unspecified failure: " + str(e)

        return HttpResponse(str(resultSummary))


class GetDeliveryGroupPackageRevKGB(APIView):
    '''
    Get KGB for Delivery Group
    '''

    def get(self, request, *args, **kwargs):
        try:
            groupId = self.kwargs['deliveryGroup']
            try:
                artifactName = self.kwargs['artifactName']
            except:
                artifactName = None
            deliveryGrpPkgRevKgb = getDeliveryGroupPkgRevFrozenKGB(groupId, artifactName)
            if "error" in deliveryGrpPkgRevKgb:
                return Response(deliveryGrpPkgRevKgb, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(deliveryGrpPkgRevKgb, status=status.HTTP_200_OK)
        except Exception as error:
            msg = 'There was an Issue getting Frozen KGB Results for delivery Group:' + str(error)
            return Response({'error': str(msg)}, status=status.HTTP_404_NOT_FOUND)


class GetDropPackageRevKGB(APIView):
    '''
    Get Frozen KGB for Drop
    '''

    def get(self, request, *args, **kwargs):
        try:
            product = self.kwargs['product']
            drop = self.kwargs['drop']
            try:
                artifactName = self.kwargs['artifactName']
            except:
                artifactName = None
            try:
                type = self.kwargs['type']
                if (type is not None or type != "None") and str(type).lower() == "productware":
                    type = "packages"
            except:
                type = None
            dropPkgRevKgb = getDropPkgRevFrozenKGB(product, drop, type, artifactName)
            if "error" in dropPkgRevKgb:
                return Response(dropPkgRevKgb, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(dropPkgRevKgb, status=status.HTTP_200_OK)
        except Exception as error:
            msg = 'There was an Issue getting Frozen KGB Results for drop:' + str(error)
            return Response({'error': str(msg)}, status=status.HTTP_404_NOT_FOUND)


class GetMediaArtifactPackageRevKGB(APIView):
    '''
    Get KGB for Media Artifact
    '''

    def get(self, request, *args, **kwargs):
        try:
            mediaArtifactName = self.kwargs['mediaArtifactName']
            mediaArtifactVersion = self.kwargs['mediaArtifactVersion']
            try:
                artifactName = self.kwargs['artifactName']
            except:
                artifactName = None
            pkgRevKgb = getMediaArtifactContentPkgRevFrozenKGB(mediaArtifactName, mediaArtifactVersion, artifactName)
            if "error" in pkgRevKgb:
                return Response(pkgRevKgb, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(pkgRevKgb, status=status.HTTP_200_OK)
        except Exception as error:
            msg = 'There was an Issue getting Frozen KGB Results for Media Artifact:' + str(error)
            return Response({'error': str(msg)}, status=status.HTTP_404_NOT_FOUND)


class GetTeamFromJira(APIView):
    '''
    Get Team Name from a Jira Number
    '''

    def get(self, request, jira_num, *args, **kwargs):
        if jira_num is None:
            return Response("Jira Number is not Valid", status=status.HTTP_412_PRECONDITION_FAILED)
        jira_url = config.get('CIFWK', 'eTeamJiraRestApiUrl')
        header = getJiraAccessTokenHeader()
        ssl_certs = config.get('CIFWK', 'defaultSSLCerts')
        response = requests.get(jira_url + "%s/" % jira_num, headers=header, verify=ssl_certs)
        if response.status_code != 200:
            return Response("Jira Request Failed with status: %s" % response.status_code,
                            status=status.HTTP_400_BAD_REQUEST)
        if response.json()['fields']['customfield_14309'] is None:
            return Response("Team Name not set", status=status.HTTP_400_BAD_REQUEST)
        team_name = response.json()['fields']['customfield_14309'][0]['value']
        return Response({"team": team_name}, status=status.HTTP_200_OK)


class GetArtifactVersionFromNexus(APIView):
    """
    The getArtifactVersionFromNexus REST call gets the version of an Artifact specified from Nexus Repo
    """

    def get(self, request, artifact, version, *args, **kwargs):
        local = request.GET.get('local')

        if local is None:
            local = False
        else:
            local = True if local.lower() == "true" else False

        if artifact is None or not artifact or artifact == "None":
            return Response([{'error': 'Artifact is required.'}], status=status.HTTP_412_PRECONDITION_FAILED)
        if version is None or not version or version == "None":
            return Response([{'error': 'Artifact version is required.'}], status=status.HTTP_412_PRECONDITION_FAILED)

        response = getNexusUrlForArtifactVersion(artifact, version, local)
        if "error" in str(response):
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        return Response(response, status=status.HTTP_200_OK)


class GetProductSetStatus(APIView):
    '''
    The productSetStatus REST call gets the status of a Product Set
    '''

    def get(self, request, *args, **kwargs):
        try:
            productName = self.kwargs['product']
            version = self.kwargs['productset']

            if productName is None or not productName or productName == "None":
                return Response([{'error': 'Product is required.'}], status=status.HTTP_412_PRECONDITION_FAILED)
            if version is None or not version or version == "None":
                return Response([{'error': 'Artifact version is required.'}],
                                status=status.HTTP_412_PRECONDITION_FAILED)

            psObj = ProductSetVersion.objects.get(version=version,
                                                  productSetRelease__release__product__name=productName)
            response = psObj.getOverallWeigthedStatus()
            return Response({'status': response}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response([{'error': 'Product Set version does not exist.'}], status=status.HTTP_404_NOT_FOUND)


class DeliverAutoCreatedGroup(APIView):
    '''
    The autoCreatedGroupDeliver REST call delivers auto-created group if auto-delivery is enable
    '''

    def post(self, request, *args, **kwargs):
        try:
            if request.data['user']:
                user = User.objects.get(username=request.data['user'])
            else:
                return Response("ERROR: A user name must be supplied as POST data with key 'user'",
                                status=status.HTTP_412_PRECONDITION_FAILED)
            groupId = request.data['group_id']
            requiredValues = ('id', 'drop__name', 'drop__release__product__name')
            groupObj = DeliveryGroup.objects.only(requiredValues).values(*requiredValues).get(id=groupId)
            productName = groupObj['drop__release__product__name']
            dropName = groupObj['drop__name']
            if productName is None or not productName or productName == "None":
                return Response("ERROR: Product is required.", status=status.HTTP_412_PRECONDITION_FAILED)
            if dropName is None or not dropName or dropName == "None":
                return Response("ERROR: Drop Name is required.", status=status.HTTP_412_PRECONDITION_FAILED)
            if groupId is None or not groupId or groupId == "None":
                return Response("ERROR: Group Id is required.", status=status.HTTP_412_PRECONDITION_FAILED)
            result, returnCode = deliverAutoCreatedGroup(productName, dropName, user, groupId)
            if returnCode == 0:
                return Response(result, status=status.HTTP_200_OK)
            elif returnCode == 2:
                return Response(result, status=status.HTTP_412_PRECONDITION_FAILED)
            else:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            errMsg = "Error: There was an issue delivering the Auto Created Groups: " + str(error)
            logger.error(errMsg)
            return Response(errMsg, status=status.HTTP_404_NOT_FOUND)


class DeliverAutoCreatedGroups(APIView):
    '''
    The deliverAutoCreatedGroups REST call delivers all queued groups that have gone through Fast Commit
    '''
    authentication_classes = (BasicAuthentication,)

    def post(self, request, *args, **kwargs):
        try:
            if request.POST.get('user'):
                user = User.objects.get(username=request.POST.get('user'))
            else:
                return Response("ERROR: A user name must be supplied as POST data with key 'user'",
                                status=status.HTTP_412_PRECONDITION_FAILED)
            productName = self.kwargs['product']
            dropName = self.kwargs['drop']
            if productName is None or not productName or productName == "None":
                return Response("ERROR: Product is required.", status=status.HTTP_412_PRECONDITION_FAILED)
            if dropName is None or not dropName or dropName == "None":
                return Response("ERROR: Drop Name is required.", status=status.HTTP_412_PRECONDITION_FAILED)

            result, redirect = deliverAutoCreatedGroups(productName, dropName, user)

            if request.META.get('HTTP_REFERER') is not None:
                request.session['message'] = result
                return HttpResponseRedirect(redirect)
            else:
                if "ERROR" in result:
                    return Response(result, status=status.HTTP_404_NOT_FOUND)
                else:
                    return Response(result, status=status.HTTP_200_OK)
        except Exception as error:
            errMsg = "Error: There was an issue delivering the Auto Created Groups: " + str(error)
            logger.error(errMsg)
            return Response(errMsg, status=status.HTTP_404_NOT_FOUND)


class GetAllProductSetNames(APIView):
    '''
    This rest call returns the name of all Product Sets in the DB as well as the product which each Product Set belongs to
    Example Json Response: {"productSets": [{"product": "OSS-RC", "name": "OSS-RC"}, {"product": "ENM", "name": "ENM"}, {"product": "Netsim", "name": "NSS"}]}
    '''

    def get(self, request, *args, **kwargs):
        try:
            productSetsList = ProductSetRelease.objects.all().values_list('release__product__name',
                                                                          'productSet__name').distinct()
            productSetsDict = {}
            resultsList = []
            for productSet in productSetsList:
                resultsList.append({'product': productSet[0], 'name': productSet[1]})
            productSetsDict['productSets'] = resultsList
            return Response(productSetsDict, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "ERROR: Unable to retrieve list of Product Sets, " + str(e)
            logger.error(errMsg)
            return Response({'ERROR': errMsg}, status=status.HTTP_404_NOT_FOUND)


class GetLatestPassedKGBInfo(APIView):
    '''
    To return the latest passed KGB data for Artifact
    '''

    def get(self, request, *args, **kwargs):
        try:
            artifactName = self.kwargs['artifact']
            result, statusCode = getLatestPassedKGBdataForArtifact(artifactName)
            if statusCode != 200:
                return Response({'ERROR': result}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting latest passed KGB data: " + str(e)
            logger.error(errMsg)
            return Response({'ERROR': errMsg}, status=status.HTTP_404_NOT_FOUND)


class GetProductwareToTestwareMediaMapping(APIView):
    '''
    Getting a Productware Media's Testware Media Mappings
    '''

    def get(self, request, *args, **kwargs):
        try:
            artifactName = self.kwargs['mediaArtifactName']
            version = self.kwargs['mediaArtifactVersion']
            result, statusCode = getMediaArtifactProductToTestwareMapping(artifactName, version)
            if statusCode != 200:
                return Response({'ERROR': result}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting Media Artifact Mapping data: " + str(e)
            logger.error(errMsg)
            return Response({'ERROR': errMsg}, status=status.HTTP_404_NOT_FOUND)


class GetByDropProductwareToTestareMediaMapping(APIView):
    '''
    Getting Productware Media's Testware Media Mappings by Drop
    '''

    def get(self, request, *args, **kwargs):
        try:
            artifactName = self.kwargs['mediaArtifactName']
            product = self.kwargs['product']
            drop = self.kwargs['drop']
            result, statusCode = getProductwaretoTestwareMappingByDrop(artifactName, product, drop)
            if statusCode != 200:
                return Response({'ERROR': result}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting Media Artifact Mapping data: " + str(e)
            logger.error(errMsg)
            return Response({'ERROR': errMsg}, status=status.HTTP_404_NOT_FOUND)


class SetMediaArtifactVersionInactive(APIView):
    '''
    Setting Media Artifact Versions Inactive by given Artifact & Version
    '''

    def post(self, request, *args, **kwargs):
        try:
            artifactName = self.kwargs['mediaArtifactName']
            artifactVer = self.kwargs['mediaArtifactVersion']
            statusCode = checkNexus()
            if statusCode != 200:
                return Response({'error': 'Issue with Nexus, try again later'}, status=status.HTTP_404_NOT_FOUND)
            result, statusCode = setMediaArtifactVerInactive(artifactName, artifactVer)
            if statusCode != 200:
                return Response({'error': result}, status=status.HTTP_404_NOT_FOUND)
            return Response({'result': result}, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with information given: " + str(e)
            logger.error(errMsg)
            return Response({'error': errMsg}, status=status.HTTP_404_NOT_FOUND)


class SetMediaArtifactVersInactiveByDrop(APIView):
    '''
    Setting Media Artifact Versions Inactive by given Drop & Product
    '''

    def post(self, request, *args, **kwargs):
        try:
            productName = self.kwargs['product']
            dropName = self.kwargs['drop']
            statusCode = checkNexus()
            if statusCode != 200:
                return Response({'error': 'Issue with Nexus, try again later'}, status=status.HTTP_404_NOT_FOUND)
            result, statusCode = setMediaArtifactVerInactiveByDrop(productName, dropName)
            if statusCode != 200:
                return Response({'error': result}, status=status.HTTP_404_NOT_FOUND)
            return Response({'result': result}, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with information given: " + str(e)
            logger.error(errMsg)
            return Response({'error': errMsg}, status=status.HTTP_404_NOT_FOUND)


class MediaArtifactVersionExternallyReleased(APIView):
    '''
    Setting/Getting Media Artifact Version Externally Released
    '''

    def post(self, request, *args, **kwargs):
        try:
            productName = self.kwargs['product']
            dropName = self.kwargs['drop']
            mediaArtifact = request.POST.get("mediaArtifactName")
            version = request.POST.get("mediaArtifactVersion")
            result, statusCode = setExternallyReleasedMediaArtifactVersion(productName, dropName, mediaArtifact,
                                                                           version)
            if statusCode != 200:
                return Response({'error': str(result)}, status=status.HTTP_404_NOT_FOUND)
            return Response({'result': str(result)}, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with information given: " + str(e)
            logger.error(errMsg)
            return Response({'error': errMsg}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, *args, **kwargs):
        try:
            productName = self.kwargs['product']
            dropName = self.kwargs['drop']
            result, statusCode = getExternallyReleasedMediaArtifactVersion(productName, dropName)
            if statusCode != 200:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with information given: " + str(e)
            logger.error(errMsg)
            return Response({'error': errMsg}, status=status.HTTP_404_NOT_FOUND)


class GetProductSetDropData(APIView):
    '''
    Getting ProductSet Drop Data
    '''

    def get(self, request, *args, **kwargs):
        try:
            productSetName = self.kwargs['productSet']
            dropName = self.kwargs['drop']
            result, statusCode = getProductSetDropData(productSetName, dropName)
            if statusCode != 200:
                return Response(result, status=status.HTTP_404_NOT_FOUND)

            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with information given: " + str(e)
            logger.error(errMsg)
            return Response({'error': errMsg}, status=status.HTTP_404_NOT_FOUND)


class GetMediaArtifactVersionData(APIView):
    '''
    Getting Media Artifact Version Data
    '''

    def get(self, request, *args, **kwargs):
        try:
            mediaArtifact = self.kwargs['mediaArtifactName']
            version = self.kwargs['mediaArtifactVersion']
            local = request.GET.get('contentLocalNexus', "false")
            result, statusCode = getMediaArtifactVersionData(mediaArtifact, version, local)
            if statusCode != 200:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with information given: " + str(e)
            logger.error(errMsg)
            return Response({'error': errMsg}, status=status.HTTP_404_NOT_FOUND)


class GetLatestDropName(APIView):
    '''
    Getting Latest Drop Name
    '''

    def get(self, request, *args, **kwargs):
        try:
            product = self.kwargs['product']
            correctionalDrop = request.GET.get('correctionalDrop', False)
            if not correctionalDrop or correctionalDrop == 'None' or correctionalDrop.lower() != 'true':
                correctionalDrop = False
            result, statusCode = getLatestProductDropName(product, correctionalDrop)
            if statusCode != 200:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with information given: " + str(e)
            logger.error(errMsg)
            return Response({'error': errMsg}, status=status.HTTP_404_NOT_FOUND)


class GetDropMediaDeployContent(APIView):
    '''
    Getting Deploy Data Mapping for Media delivery
    '''

    def get(self, request, *args, **kwargs):
        try:
            drop = self.kwargs['drop']
            productSet = self.kwargs['productSet']
            product = request.GET.get('excludeProduct', "ENM")
            result, statusCode = getDropMediaDeployData(productSet, product, drop)
            if statusCode != 200:
                return Response({"error": str(result)}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting Product Set Drop Data: " + str(e)
            logger.error(errMsg)
            return Response({"error": str(errMsg)}, status=status.HTTP_404_NOT_FOUND)


class GetActiveDropsInProductSet(APIView):
    '''
    Getting Active Drops in Product Set
    '''

    def get(self, request, *args, **kwargs):
        try:
            productSet = self.kwargs['productSet']
            result = getActiveDropsInProductSet(productSet)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting Product Set Drops: " + str(e)
            logger.error(errMsg)
            return Response({"error": str(errMsg)}, status=status.HTTP_404_NOT_FOUND)


class ObsoleteGroupDeliveries(APIView):
    '''
    The obsoleteGroupDeliveries function loops through the artifacts in a delivery group and obsoletes them
    '''

    def post(self, request, *args, **kwargs):
        statusList = []
        deliveryGroupObj = groupId = forceOption = mtgGuards = accessGroup = postUser = None
        groupId = self.kwargs['groupId']
        forceOption = self.kwargs['forceOption']
        mtgGuards = config.get("CIFWK", "mtgGuards")
        accessGroup = config.get("CIFWK", "adminGroup")
        postUser = request.POST.get('user', request.user)
        if groupId is None or forceOption is None or postUser is None:
            return Response({
                                "error": "Error in obsoletng delivery group. groupId, forceOption or userName does not specify. Please check your rest call."},
                            status=status.HTTP_403_FORBIDDEN)
        if mtgGuards is None or accessGroup is None:
            return Response({
                                "error": "Error in obsoletng delivery group. permission Groups can't be found in CI Portal. Please contact CI Portal Admin!"},
                            status=status.HTTP_403_FORBIDDEN)
        if forceOption.lower() == "true":
            forceOption = True
        elif forceOption.lower() == "false":
            forceOption = False
        else:
            return Response({
                                "error": "Error in obsoletng delivery group. forceOption can be either True or False. Please check your rest call."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(username=str(postUser))
            if user is None:
                return Response({"error": "ERROR obsoleting group " + str(groupId) + ": User may not exist"},
                                status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            errMsg = "ERROR obsoleting group " + str(groupId) + ": " + str(e)
            logger.error(errMsg)
            statusList.append(errMsg)
            return Response({"error": statusList}, status=status.HTTP_403_FORBIDDEN)
        if not (user.groups.filter(name=mtgGuards).exists() or user.groups.filter(name=accessGroup).exists()):
            return Response({"error": "ERROR obsoleting group " + str(
                groupId) + ": You do not have permission to obsolete groups."}, status=status.HTTP_403_FORBIDDEN)
        obsolete_thread = DGThread(cireports.utils.obsoleteDeliveryGroup_API,
                                   args=(groupId, self.kwargs['product'], self.kwargs['drop'], forceOption, user))
        obsolete_thread.start()
        obsolete_thread.join()
        statusList = obsolete_thread.get_result()
        if len(statusList) != 0:
            return Response({"error": statusList}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"message": "Delivery Group: " + str(groupId) + "obsoleted successfully"},
                            status=status.HTTP_200_OK)


class storeCNMetadata(APIView):
    '''
    This is POST REST API which stores cloud native metadata in DB.
    '''

    def post(self, request, *args, **kwargs):
        try:
            content = json.loads(request.body)
            if content == None:
                return Response({"Error": "Content of Rest API request returned none"},
                                status=status.HTTP_404_NOT_FOUND)
            result = cireports.utils.storeCloudNativeMetadata(content)
            if result == "SUCCESS":
                return Response({"Status": result}, status=status.HTTP_200_OK)
            else:
                logger.error("Failed to push metadata. Please investigate: " + result)
                return Response({"Status": result}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to push metadata. Please investigate: " + str(e))
            return Response({"Error": "POST rest call, please investigate " + str(e)}, status=status.HTTP_404_NOT_FOUND)


class ManageCNProductSet(APIView):
    '''
    This is POST Rest Api which stores enm ps version to cn ps version table to map enm to cenm.
    '''

    def post(self, request, *args, **kwargs):
        try:
            productSetVersion = self.kwargs['productSetVersion']
            pipeline_status = self.kwargs['pipelineStatus']
            confidenceLevelName = self.kwargs['confidenceLevelName']
            if productSetVersion is None or pipeline_status is None or confidenceLevelName is None:
                return Response(
                    {"Error": "Product Set Version, status or confidenceLevelName hasn't been set in restcall"},
                    status=status.HTTP_404_NOT_FOUND)
            result = cireports.utils.createOrUpdateCNProductSet(productSetVersion, pipeline_status, confidenceLevelName)
            return Response({"Status": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"Error": "POST rest call, please investigate " + str(e)}, status=status.HTTP_404_NOT_FOUND)


class GetDropNamesForCloudNativeProduct(APIView):
    '''
    This is GET Rest Api which gets cenm drop version.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = cireports.utils.getDropNamesForCENM()
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"Error": "GET rest call, please investigate " + str(e)}, status=status.HTTP_404_NOT_FOUND)


class GetCNProductSetVersion(APIView):
    '''
    This is GET Rest Api which gets cenm product set version.
    '''

    def get(self, request, *args, **kwargs):
        try:
            dropName = self.kwargs['dropName']
            result = cireports.utils.getProductSetVersionForCENM(dropName)
            return Response({"ProductSetVersion": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"Error": "GET rest call, please investigate " + str(e)}, status=status.HTTP_404_NOT_FOUND)


class GetLinkedCNProductSetVersion(APIView):
    '''
    This is GET Rest Api which gets linked cenm product set version by enm ps.
    '''

    def get(self, request, *args, **kwargs):
        try:
            enmProductSetVersion = self.kwargs['enmProductSetVersion']
            result, errorMsg = cireports.utils.getLinkedCNProductSetVersion(str(enmProductSetVersion))
            if errorMsg != None:
                return Response(
                    "Failed to get linked cn product set version by ENM product set version. Please investigate: " + errorMsg,
                    status=status.HTTP_404_NOT_FOUND)
            if not result:
                return HttpResponse(result, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                "Failed to get linked cn product set version by ENM product set version. Please investigate: " + str(e),
                status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(result, status=status.HTTP_200_OK)


class GetLinkedENMProductSetVersion(APIView):
    '''
    This is GET Rest Api which gets linked enm product set version by cenm ps.
    '''

    def get(self, request, *args, **kwargs):
        try:
            CNProductSetVersion = self.kwargs['CNProductSetVersion']
            result, errorMsg = cireports.utils.getLinkedENMProductSetVersion(str(CNProductSetVersion))
            if errorMsg != None:
                return Response(
                    "Failed to get linked ENM product set version by CENM product set version. Please investigate: " + errorMsg,
                    status=status.HTTP_404_NOT_FOUND)
            if not result:
                return HttpResponse(result, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                "Failed to get linked ENM product set version by CENM product set version. Please investigate: " + str(
                    e), status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(result, status=status.HTTP_200_OK)


class PublishVerifiedCNContent(APIView):
    '''
    This is POST Rest Api which publish verified cloud native contents.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            cnProductSetVersion = self.kwargs['CNProductSetVersion']
            cnProductName = self.kwargs['CNProductName']
            cnProductVersion = self.kwargs['CNProductRevisionVersion']
            if cnProductSetVersion is None or cnProductName is None or cnProductVersion is None:
                return Response({
                                    "Error": "CN Product Set Version,  CN Product Name or CN Product Version hasn't been set in restcall to publish verified CN Contents"},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.publishVerfiedCNContent(str(cnProductSetVersion), str(cnProductName),
                                                                       str(cnProductVersion))
            if errorMsg:
                return Response({"Error": errorMsg}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"Status": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"Error": "POST rest call Failed for publishing verified CN Contents, please investigate! " + str(e)},
                status=status.HTTP_400_BAD_REQUEST)


class UnPublishVerifiedCNContent(APIView):
    '''
    This is POST Rest Api which publish verified cloud native contents.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            cnProductSetVersion = self.kwargs['CNProductSetVersion']
            cnProductName = self.kwargs['CNProductName']
            cnProductVersion = self.kwargs['CNProductRevisionVersion']
            if cnProductSetVersion is None or cnProductName is None or cnProductVersion is None:
                return Response({
                                    "Error": "CN Product Set Version,  CN Product Name or CN Product Version hasn't been set in restcall to unpublish verified CN Contents"},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.unPublishVerfiedCNContent(str(cnProductSetVersion), str(cnProductName),
                                                                         str(cnProductVersion))
            if errorMsg:
                return Response({"Error": errorMsg}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"Status": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"Error": "POST rest call Failed for unpublishing verified CN Contents, please investigate! " + str(e)},
                status=status.HTTP_400_BAD_REQUEST)


class ReleaseISOExternally(APIView):
    '''
    This is POST Rest Api which releases ISOs externally.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            isoName = self.kwargs['artifactName']
            postUser = request.POST.get('user', request.user)
            externalReleaseGroup = config.get("CIFWK", "externalReleaseGuards")
            user = User.objects.get(username=str(postUser))
            if isoName is None or user is None:
                return Response(
                    {"Error": "Failed to release ISO Externally, artifactName or user hasn't been set in restcall."},
                    status=status.HTTP_404_NOT_FOUND)
            if not user.groups.filter(name=externalReleaseGroup).exists():
                return Response({
                                    "Error": "Failed to release ISO Externally: You do not have permission to release product externally. Please request the permission if needed."},
                                status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = cireports.utils.releaseISOExternally(str(isoName))
            if errorMsg:
                raise Exception(errorMsg)
            return Response({"Status": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"Error": "POST rest call Failed for releasing ISO externally, please investigate! " + str(e)},
                status=status.HTTP_404_NOT_FOUND)


class UnreleaseISOExternally(APIView):
    '''
    This is POST Rest Api which unreleases ISOs externally.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            isoName = self.kwargs['artifactName']
            postUser = request.POST.get('user', request.user)
            externalReleaseGroup = config.get("CIFWK", "externalReleaseGuards")
            user = User.objects.get(username=str(postUser))
            if isoName is None or user is None:
                return Response(
                    {"Error": "Failed to unrelease ISO Externally, artifactName or user hasn't been set in restcall."},
                    status=status.HTTP_404_NOT_FOUND)
            if not user.groups.filter(name=externalReleaseGroup).exists():
                return Response({
                                    "Error": "Failed to unrelease ISO Externally: You do not have permission to unrelease product externally. Please request the permission if needed."},
                                status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = cireports.utils.unreleaseISOExternally(str(isoName))
            if errorMsg:
                raise Exception(errorMsg)
            return Response({"Status": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"Error": "POST rest call Failed for unreleasing ISO externally, please investigate! " + str(e)},
                status=status.HTTP_404_NOT_FOUND)


class GetReleaseNote(APIView):
    '''
    This is GET Rest Api which get release note for a product set for external releasable products.
    '''

    def get(self, request, *args, **kwargs):
        try:
            errorMsg = None
            productSetVersion = None
            productSetName = None
            productSetVersion = self.kwargs['productSetVersion']
            productSetName = self.kwargs['productSetName']
            if productSetVersion is None:
                return Response({
                                    "Error": "Failed to get release note,  productSetVersion or productSetName hasn't been set in restcall."},
                                status=status.HTTP_404_NOT_FOUND)
            version_splitted = str(productSetVersion).split('.')
            if len(version_splitted) < 3:
                return Response(
                    {"Error": "Failed to get release note,  productSetVersion does not valid: " + productSetVersion},
                    status=status.HTTP_404_NOT_FOUND)
            contents, errorMsg = cireports.generateReleaseNote.preprocessReleaseNoteParams(str(productSetVersion),
                                                                                           str(productSetName))
            if errorMsg:
                raise Exception(errorMsg)
            return HttpResponse(contents, status=status.HTTP_200_OK, content_type="application/json")
        except Exception as e:
            return Response({
                                "Error": "GET rest call Failed get release note for product set " + productSetName + " " + productSetVersion + ", please investigate! " + str(
                                    e)}, status=status.HTTP_404_NOT_FOUND)


class GetCloudNativeProductSetContent(APIView):
    '''
    This is GET Rest API which gets the data that is also displayed in getCloudNativeProductSetContent in json format.
    '''

    def get(self, request, *args, **kwargs):
        contents = errorMsg = None
        try:
            drop = self.kwargs['drop']
            product_set_version = self.kwargs['productSetVersion']
            if product_set_version is None:
                return Response({
                                    "Error": "Failed to get CNProductSetContents productSetVersion or Drop hasn't been set in restcall."},
                                status=status.HTTP_404_NOT_FOUND)
            contents, errorMsg = cireports.utils.getCloudNativeProductSetContents(drop, product_set_version)
            if errorMsg:
                raise Exception(errorMsg)
            return Response(contents, status=status.HTTP_200_OK)
        except Exception as e:
            error = "There was an issue with fetching the information from DB. Please Investigate! " + str(e)
            logger.error(error)
            return Response({"Error": error}, status=status.HTTP_404_NOT_FOUND)


class UpdateOverallConfidenceLevel(APIView):
    '''
    This is POST Rest Api which update overall confidence levels for updating old cn product set.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.updateAllOverallConfidenceLevels()
            if errorMsg:
                raise Exception(errorMsg)
            return Response({"Status": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                                "Error": "POST rest call Failed for updating overall confidence level for old product set, please investigate! " + str(
                                    e)}, status=status.HTTP_404_NOT_FOUND)


class OverwriteOverallConfidenceLevel(APIView):
    '''
    This is POST Rest Api which update overall confidence levels for updating old cn product set.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            user = None
            productSetVersion = None
            postUser = request.POST.get('user', request.user)
            productSetVersion = self.kwargs['productSetVersion']
            confidenceLevelState = self.kwargs['confidenceLevelState']
            user = User.objects.get(username=str(postUser))
            cENMGuards = config.get("CIFWK", "cENMGuards")
            if productSetVersion is None or user is None:
                return Response({
                                    "Error": "Failed to overwrite overall confidence level,  productSetVersion or user hasn't been set in restcall."},
                                status=status.HTTP_404_NOT_FOUND)
            if not user.groups.filter(name=cENMGuards).exists():
                return Response({
                                    "Error": "Failed to overwrite overall confidence level: You do not have permission to overwrite confidencel level. Please request the permission if needed."},
                                status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = cireports.utils.overwriteOverallConfidenceLevels(productSetVersion, confidenceLevelState)
            if errorMsg:
                raise Exception(errorMsg)
            return Response({"Status": result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                                "Error": "POST rest call Failed to overwrite overall confidence level for old product set, please investigate! " + str(
                                    e)}, status=status.HTTP_404_NOT_FOUND)


class GetGreenProductSetVersion(APIView):
    '''
    This is GET Rest Api which returns cn product set version with latest green overall working baseline.
    '''

    def get(self, request, *args, **kwargs):
        try:
            dropName = self.kwargs['dropName']
            result, errorMsg = cireports.utils.getGreenCNProductSetVersion(dropName)
            if errorMsg != None:
                return HttpResponse(
                    "Failed to get green cn prodcut set version for " + dropName + ". Please investigate: " + errorMsg,
                    status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return HttpResponse(
                "Failed to get green cn prodcut set version for " + dropName + ". Please investigate: " + str(e),
                status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(result, status=status.HTTP_200_OK)


class PostDeploymentUtilities(APIView):
    '''
    This is POST Rest Api which post one/multiple deployment utilities by cn product set version.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            productSetVersion = self.kwargs['productSetVersion']
            content = json.loads(request.body)
            if productSetVersion is None:
                return Response(
                    {"Error": "Failed to post deployment utilities,  productSetVersion hasn't been set in restcall."},
                    status=status.HTTP_412_PRECONDITION_FAILED)
            if content == None:
                return Response({"Error": "Content of deployment utilities request returned none"},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.processDeploymentUtilities(productSetVersion, content)
            if errorMsg:
                raise Exception(errorMsg)
        except Exception as e:
            return Response({"Error": "Failed to post deployment utilities, please investigate " + str(e)},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"Status": result}, status=status.HTTP_200_OK)


class GetPackageProductMapping(APIView):
    '''
    This is GET Rest Api which get all the relevant products by package name.
    '''

    def get(self, request, *args, **kwargs):
        try:
            packageName = self.kwargs['packageName']
            if packageName is None:
                return Response(
                    "Precondition error: Failed to get packageProductMapping. Please specify your package name.",
                    status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.getPackageProductMapping(packageName)
            if errorMsg != None:
                logger.error(
                    "ERROR: Failed to get packageProductMapping for " + packageName + ". Please investigate: " + errorMsg)
                return Response(
                    "Failed to get packageProductMapping for " + packageName + ". Please investigate: " + errorMsg,
                    status=status.HTTP_400_BAD_REQUEST)
            if not result:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                "ERROR: Failed to get packageProductMapping for " + packageName + ". Please investigate: " + str(e))
            return Response(
                "ERROR: Failed to get packageProductMapping for " + packageName + ". Please investigate: " + str(e),
                status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateTeamInfo(APIView):
    '''
    This is POST Rest Api which updates team data from Team Inventory API to CI Portal.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.updateTeamInfo()
            if errorMsg:
                logger.error("Failed to update team data. Please Investigate: " + errorMsg)
                return Response(
                    {"Status": "FAILED to update team data. Please contact admin to manually update the data",
                     "errorLog": errorMsg, "Data status": result}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"Status": "FAILED to update team data. INTERNAL ERROR: API reqeust error",
                             "errorLog": "Failed to update team data. Please Investigate: " + str(e),
                             "Data status": result}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"Status": "SUCCESS", "Data status": result}, status=status.HTTP_200_OK)


class GetOverallWorkingBaseline(APIView):
    '''
    This is GET Rest Api which returns all the overall working baseslines by a given drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['dropNumber']
            if dropNumber is None:
                return Response(
                    {"Error": "Failed to get all the overall working baseslines,  drop hasn't been set in restcall."},
                    status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.getOverallWorkingBaselineByDrop(dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get all the overall working baseslines. Please investigate: " + str(e))
            return Response("Failed to get all the overall working baseslines. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetConfidenceLevelVersion(APIView):
    '''
    This is a GET Rest Api which returns the product set version of the latest passed cENM-Deploy-II-Charts, cENM-Deploy-UG-Charts and cENM-Deploy-II-CSAR for the latest green product set.
    '''

    def get(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.getConfidenceLevelVersion()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get the confidence level version. Please investigate: " + str(e))
            return Response("Failed to get the confidence level version. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateCNProductSetVersionActiveness(APIView):
    '''
    This is POST Rest Api which update activeness of a cn product set version by a given cn product set version.
    '''

    def post(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            isActive = self.kwargs["isActive"]
            productSetVersion = self.kwargs['productSetVersion']
            userName = self.kwargs['userName']
            user = User.objects.get(username=str(userName))
            cENMGuards = config.get("CIFWK", "cENMGuards")
            if not user.groups.filter(name=cENMGuards).exists():
                return Response({
                                    "Error": "Failed to update activeness of a cn product set version. You do not have permission to update activeness of a cn product set version. Please request the permission if needed."},
                                status=status.HTTP_403_FORBIDDEN)
            if isActive.lower() == "true":
                isActive = True
            elif isActive.lower() == "false":
                isActive = False
            result, errorMsg = cireports.utils.updateCNProductSetVersionActiveness(productSetVersion, isActive)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update activeness of a cn product set version. Please investigate: " + str(e))
            return Response("Failed to update activeness of a cn product set version. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateOldIntegrationValueFilesData(APIView):
    '''
    This is a POST Rest Api which updates the old Integration value files data to adapt to new cENM logic.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.udpateOldIntegrationValueFileData()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update old integration value files. Please investigate: " + str(e))
            return Response("Failed to update old integration value files. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetActiveDropsByProduct(APIView):
    '''
    This is a GET Rest Api which returns a list of active drops by a given cn product.
    '''

    def get(self, request, *args, **kwargs):
        try:
            user = None
            errorMsg = None
            productName = None
            user = User.objects.get(username=str(request.user))
            productName = request.GET.get('product')
            if user is None:
                return Response("Failed to get active drops by product. User not exists. ",
                                status=status.HTTP_400_BAD_REQUEST)
            result, errorMsg = cireports.utils.getActiveDropsByProduct(productName)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get active drops by product. Please investigate: " + str(e))
            return Response("Failed to get active drops by product. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNImage(APIView):
    '''
    This is a GET Rest Api which returns a list of cn Image.
    '''

    def get(self, request, *args, **kwargs):
        try:
            user = None
            errorMsg = None
            productName = None
            user = User.objects.get(username=str(request.user))
            if user is None:
                return Response("Failed to get a list of service groups. User not exists. ",
                                status=status.HTTP_400_BAD_REQUEST)
            result, errorMsg = cireports.utils.getCNImage()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get a list of service groups. Please investigate: " + str(e))
            return Response("Failed to a list of service groups. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNProduct(APIView):
    '''
    This is a GET Rest Api which returns a list of active drops by a given cn product.
    '''

    def get(self, request, *args, **kwargs):
        try:
            user = None
            errorMsg = None
            productTypeName = None
            user = User.objects.get(username=str(request.user))
            productTypeName = self.kwargs["productTypeName"]
            if user is None:
                return Response("Failed to get a list of CN Products. User not exists. ",
                                status=status.HTTP_400_BAD_REQUEST)
            result, errorMsg = cireports.utils.getCNProduct(productTypeName)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get a list of CN Products. Please investigate: " + str(e))
            return Response("Failed to get a list of CN Products. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetDeliveryGroupsByDrop(APIView):
    '''
    This is a GET Rest Api which returns a list of delivery groups by a given drop and queue.
    '''

    def get(self, request, *args, **kwargs):
        try:
            user = None
            errorMsg = None
            dropName = None
            user = User.objects.get(username=str(request.user))
            dropName = request.GET.get('dropName')
            queueType = self.kwargs["queueType"]
            if user is None:
                return Response("Failed to get a list of " + queueType + " Delivery Groups. User does not exists. ",
                                status=status.HTTP_400_BAD_REQUEST)
            result, errorMsg = cireports.utils.getDeliveryGroupsByDrop(dropName, queueType)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get a list of " + queueType + " Delivery Groups. Please investigate: " + str(e))
            return Response("Failed to get a list of " + queueType + " Delivery Groups. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCENMDeliveryGroupsByDrop(APIView):
    '''
    This is a GET Rest Api which returns a list of cenm delivery groups by a given cenm drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            user = None
            errorMsg = None
            dropName = None
            user = User.objects.get(username=str(request.user))
            dropName = request.GET.get('dropName')
            if user is None:
                return Response("Failed to get a list of CENM Delivery Groups. User does not exists. ",
                                status=status.HTTP_400_BAD_REQUEST)
            result, errorMsg = cireports.utils.getENMDeliveryGroupsByDrop(dropName)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get a list of ENM Delivery Groups. Please investigate: " + str(e))
            return Response("Failed to get a list of ENM Delivery Groups. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNDeliveryQueue(APIView):
    '''
    This is GET Rest Api which returns a list of cn delivery group for rendering cn delivery queue page.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            productName = self.kwargs["productName"]
            dropNumber = self.kwargs['dropNumber']
            result, errorMsg = cireports.utils.getCNDeliveryQueueData(productName, dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            # return Response(json.dumps(result,cls=DjangoJSONEncoder), content_type="application/json", status = status.HTTP_200_OK)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "Failed to get cn delivery group data for renerding cn delivery queue page. Please investigate: " + str(
                    e))
            return Response(
                "Failed to get cn delivery group data for renerding cn delivery queue page. Please investigate: " + str(
                    e), status=status.HTTP_400_BAD_REQUEST)


class DeliverCNDeliveryGroup(APIView):
    '''
    This is POST Rest Api which delivers a cn delivery Group with product set version.
    '''

    def post(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            user = None
            content = None
            permissionCheck = None
            permissionCheckErrorMsg = None
            dropCheckStatus = None
            dropCheckErrorMsg = None
            cnDeliveryGroupGuards = config.get("CIFWK", "cnDeliveryQueueAdminGroup")
            deliveryGroupNumber = request.POST.get('deliveryGroupNumber')
            cnProductSetVersion = request.POST.get('productSetVersion')
            user = User.objects.get(username=str(request.user))
            permissionCheck, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueAdminPerms(user)
            if not permissionCheck:
                errorMsg = "Only the admin of Cloud Native delivery queue can deliver delivery groups. Please request the permission on Engineering Tools Team if needed. "
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            deliverCNDG_thread = DGThread(cireports.utils.deliverCNDeliveryGroup,
                                          args=(deliveryGroupNumber, user, cnProductSetVersion))
            deliverCNDG_thread.start()
            deliverCNDG_thread.join()
            result, errorMsg = deliverCNDG_thread.get_result()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to deliver the cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class ObsoleteCNDeliveryGroup(APIView):
    '''
    This is POST Rest Api which obsolete a cn delivery Group.
    '''

    def post(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            user = None
            permissionCheck = None
            permissionCheckErrorMsg = None
            dropCheckStatus = None
            dropCheckErrorMsg = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            user = User.objects.get(username=str(request.user))
            permissionCheck, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueAdminPerms(user)
            if not permissionCheck:
                errorMsg = "Only the admin of Cloud Native delivery queue can obsolete delivery groups. Please request the permission on Engineering Tools Team if needed. "
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            obsoleteCNDG_thread = DGThread(cireports.utils.obsoleteCNDeliveryGroup, args=(deliveryGroupNumber, user))
            obsoleteCNDG_thread.start()
            obsoleteCNDG_thread.join()
            result, errorMsg = obsoleteCNDG_thread.get_result()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to obsolete the cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class DeleteCNDeliveryGroup(APIView):
    '''
    This is POST Rest Api which delete a cn delivery Group.
    '''

    def post(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            user = None
            permissionCheck = None
            permissionCheckErrorMsg = None
            dropCheckStatus = None
            dropCheckErrorMsg = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            user = User.objects.get(username=str(request.user))
            permissionCheck, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueAdminPerms(user)
            if not permissionCheck:
                errorMsg = "Only the admin of Cloud Native delivery queue can delete delivery groups. Please request the permission on Engineering Tools Team if needed. "
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.deleteCNDeliveryGroup(deliveryGroupNumber, user)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Failed to delete the cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status = status.HTTP_400_BAD_REQUEST)

class RestoreCNDeliveryGroup(APIView):
    '''
    This is POST Rest Api which restore a cn delivery Group.
    '''

    def post(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            user = None
            permissionCheck = None
            permissionCheckErrorMsg = None
            dropCheckStatus = None
            dropCheckErrorMsg = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            user = User.objects.get(username=str(request.user))
            permissionCheck, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueAdminPerms(user)
            if not permissionCheck:
                errorMsg = "Only the admin of Cloud Native delivery queue can restore delivery groups. Please request the permission on Engineering Tools Team if needed. "
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.restoreCNDeliveryGroup(deliveryGroupNumber, user)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Failed to restore the cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class GetServiceGroupInfo(APIView):
    '''
    This is GET Rest Api which returns service group info, drop info , team data info by a given cn delivery group number.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            deliveryGroupNumber = self.kwargs["deliveryGroupNumber"]
            result, errorMsg = cireports.utils.getServiceGroupInfo(deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to get service group info. Please investigate: " + str(e))
            return Response("Failed to get service group info. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)


class GetIntegrationChartInfo(APIView):
    '''
    This is GET Rest Api which returns integration chart info, drop info by a given cn delivery group number.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            deliveryGroupNumber = self.kwargs["deliveryGroupNumber"]
            result, errorMsg = cireports.utils.getIntegrationChartInfo(deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to get integration chart info. Please investigate: " + str(e))
            return Response("Failed to get integration chart info. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)


class GetIntegrationValueInfo(APIView):
    '''
    This is GET Rest Api which returns integration value info, drop info by a given cn delivery group number.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            deliveryGroupNumber = self.kwargs["deliveryGroupNumber"]
            result, errorMsg = cireports.utils.getIntegrationValueInfo(deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to get integration value info. Please investigate: " + str(e))
            return Response("Failed to get integration value info. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)


class GetPipelineInfo(APIView):
    '''
    This is GET Rest Api which returns pipeline info, drop info by a given cn delivery group number.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            deliveryGroupNumber = self.kwargs["deliveryGroupNumber"]
            result, errorMsg = cireports.utils.getPipelineInfo(deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to get pipelineInfo. Please investigate: " + str(e))
            return Response("Failed to get pipelineInfo. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)


class GetImpactedDeliveryGroupInfo(APIView):
    '''
    This is GET Rest Api which returns impacted Delivery Group info, drop info by a given cn delivery group number.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            deliveryGroupNumber = self.kwargs["deliveryGroupNumber"]
            queueType = request.GET.get('queueType')
            result, errorMsg = cireports.utils.getImpactedDeliveryGroupInfo(deliveryGroupNumber, queueType)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to get Impacted Delivery Group Info. Please investigate: " + str(e))
            return Response("Failed to get Impacted Delivery Group Info. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)


class GetJiraInfo(APIView):
    '''
    This is GET Rest Api which returns jira info, drop info by a given cn delivery group number.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            deliveryGroupNumber = self.kwargs["deliveryGroupNumber"]
            result, errorMsg = cireports.utils.getJiraInfo(deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to get jira Info. Please investigate: " + str(e))
            return Response("Failed to get jira Info. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)


class EditServiceGroup(APIView):

    def delete(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = request.data
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckStatus == 1 or permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckStatus == 1 or dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.deleteServiceGroupInfo(str(request.user), deliveryGroupNumber, content)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to deliver the cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNDropByProductName(APIView):
    '''
    This is GET Rest Api which returns all the cn drops including inactive drops and active drops by a given product name.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            productName = self.kwargs["productName"]
            result, errorMsg = cireports.utils.getAllCNDrop(productName)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to cn drop info. Please investigate: " + str(e))
            return Response("Failed to cn drop info. Please investigate: " + str(e), status=status.HTTP_400_BAD_REQUEST)


class UpdateCNDeliveryGroupByCNProductSetVersion(APIView):
    '''
    This is PUT Rest Api which udpates a delivery group with a existing produt set version.
    '''

    def put(self, request, *args, **kwargs):
        try:
            result = None
            content = None
            errorMsg = None
            productSetVersionNumber = None
            deliveryGroupNumber = None
            userName = None
            user = None
            permissionCheck = None
            dropCheckStatus = None
            dropCheckErrorMsg = None

            content = json.loads(request.body)
            productSetVersionNumber = content['productSetVersion']
            deliveryGroupNumber = content['deliveryGroupNumber']
            userName = str(request.user)
            user = User.objects.get(username=userName)
            permissionCheck, errorMsg = cireports.utils.checkCNDeliveryQueueAdminPerms(user)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            if not permissionCheck:
                return Response("Only cn delivery queue admin can update product set version for a delivery group.",
                                status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckStatus == 1 or dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.updateCNDeliveryGroupByCNProductSetVersion(productSetVersionNumber,
                                                                                          deliveryGroupNumber, user)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response("success", status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "Failed to update a cn delivery group with a cn product set version. Please investigate: " + str(e))
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class AddCNDeliveryGroup(APIView):
    '''
    This is POST Rest Api which add a cn delivery group.
    '''

    def post(self, request, *args, **kwargs):
        errorMsg = None
        permCheck = None
        permErrorMsg = None
        cnDropCheckStatus = None
        cnDropErrorMsg = None
        cnDropObj = None
        try:
            jiraUrl = config.get('CIFWK', 'jiraUrl')
            decodedJson = json.loads(request.body)
            permCheck, permErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(decodedJson["userName"])
            if permCheck == 1 or permErrorMsg:
                errorMsg = permErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status.HTTP_403_FORBIDDEN)
            # check if drop is open
            cnDropCheckStatus, cnDropObj, cnDropErrorMsg = cireports.utils.checkCNDrop(decodedJson['productName'],
                                                                                       decodedJson['dropName'])
            if cnDropCheckStatus == 'not exist' or cnDropCheckStatus == 'frozen':
                errorMsg = "Failed to add cn delivery group through rest call. drop is either not open or does not exist."
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_403_FORBIDDEN)
            if cnDropErrorMsg:
                errorMsg = cnDropErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = cireports.utils.createCNDeliveryGroup(decodedJson['userName'], decodedJson['dropName'],
                                                                     decodedJson['cnImageList'],
                                                                     decodedJson['integrationChartList'],
                                                                     decodedJson['integrationValueList'],
                                                                     decodedJson['pipelineList'],
                                                                     decodedJson['jiraTickets'],
                                                                     decodedJson['teamName'], decodedJson['teamEmail'],
                                                                     decodedJson['missingDep'],
                                                                     decodedJson['missingDepReason'],
                                                                     decodedJson['impacted_delivery_group'])
            if errorMsg != None:
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(str(result), status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while creating CN Delivery Group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class EditCnDeliveryGroup(APIView):

    def put(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            cnDeliveryGroupObj = CNDeliveryGroup.objects.get(id=deliveryGroupNumber)
            dropName = cnDeliveryGroupObj.cnDrop.name
            data = json.loads(request.body)
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.editCNDeliveryGroup(data, deliveryGroupNumber, str(request.user),
                                                                   dropName)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to update cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class EditIntegrationChart(APIView):

    def delete(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = request.data
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.deleteIntegrationChartInfo(str(request.user), deliveryGroupNumber,
                                                                          content)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to remove integration chart info for a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class EditIntegrationValue(APIView):

    def delete(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = request.data
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.deleteIntegrationValueInfo(str(request.user), deliveryGroupNumber,
                                                                          content)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to remove integration value info for a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class EditPipeline(APIView):

    def delete(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = request.data
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.deletePipelineInfo(str(request.user), deliveryGroupNumber, content)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to remove pipeline info for a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class EditImpactedDeliveryGroup(APIView):

    def delete(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = request.data
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.deleteImpactedDeliveryGroupInfo(str(request.user), deliveryGroupNumber,
                                                                               content)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to remove impacted delivery group info for a cn delivery group. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class EditJira(APIView):
    '''
     This is PUT Rest Api which update jira ticket info by a given cn delivery group number.
     This is also a DELETE Rest Api which deletes a jira ticket info by a given cn delivery group number and a given jira ticket number
     '''

    def put(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = json.loads(request.body)
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.updateJiraInfo(content["data_beforeEdit"], content["data_afterEdit"],
                                                              str(request.user), deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to update jira info for a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        try:
            result = ''
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = request.data
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.deleteJiraInfo(str(request.user), deliveryGroupNumber, content)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to remove jira info for a cn delivery group. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateMissingDependencies(APIView):
    '''
    This is PUT Rest Api which update missing dep info by a given cn delivery group number.
    '''

    def put(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            user = None
            deliveryGroupNumber = self.kwargs['deliveryGroupNumber']
            content = json.loads(request.body)
            # check user permission
            permissionCheckStatus, permissionCheckErrorMsg = cireports.utils.checkCNDeliveryQueueUserInfo(
                str(request.user))
            if permissionCheckErrorMsg:
                errorMsg = permissionCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_401_UNAUTHORIZED)
            # check if drop is open
            dropCheckStatus, dropCheckErrorMsg = cireports.utils.checkCNDropByDeliveryGroupNumber(deliveryGroupNumber)
            if dropCheckErrorMsg:
                errorMsg = dropCheckErrorMsg
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.updateMissingDepInfo(content["missingDepValue"],
                                                                    content["missingDepReason"], str(request.user),
                                                                    deliveryGroupNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Failed to update missing dependencies value for a cn delivery group. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class CnDeliveryGroupSubscription(APIView):
    '''
    CN Delivery Group subscriptions
    '''

    def post(self, request, *args, **kwargs):
        user = User.objects.get(username=str(request.user))
        groupId = request.data['deliveryGroup']
        try:
            deliveryGroup = CNDeliveryGroup.objects.get(pk=groupId)
            if CNDeliveryGroupSubscription.objects.filter(user=user, cnDeliveryGroup=deliveryGroup).exists():
                CNDeliveryGroupSubscription.objects.filter(user=user, cnDeliveryGroup=deliveryGroup).delete()
            else:
                CNDeliveryGroupSubscription.objects.create(user=user, cnDeliveryGroup=deliveryGroup)
        except Exception as error:
            return Response("error: " + str(error), status=status.HTTP_404_NOT_FOUND)
        return Response("success", status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        if request.user is None:
            return Response("User is not found", status=status.HTTP_404_NOT_FOUND)

        user = User.objects.get(username=str(request.user))
        return Response(serializers.serialize("python", CNDeliveryGroupSubscription.objects.filter(user=user)))


class GetServiceGroupByGerritLink(APIView):
    '''
    This is a GET Rest Api which returns all the service groups connected to a single gerrit link.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            contents = request.GET.get("gerritLink")
            result, errorMsg = cireports.utils.getAllServiceGroup(contents)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return HttpResponse(json.dumps(result, cls=DjangoJSONEncoder), content_type="application/json",
                                status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Failed to return bulk service group info. Please investigate: " + str(e))
            return Response("Failed to return bulk service group info. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)


class GetCNDgCreatedDetails(APIView):
    '''
    This is a GET Rest Api which returns details of all the DGs created in a given drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['dropNumber']
            if dropNumber is None:
                return Response({"Error": "Failed to get the DG details,  drop hasn't been set in restcall."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.getCNDgCreatedDetailsByDrop(dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get the DG details. Please investigate: " + str(e))
            return Response("Failed to get the DG details. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNDgQueuedDetails(APIView):
    '''
    This is a GET Rest Api which returns details of all the DGs queued in a given drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['dropNumber']
            if dropNumber is None:
                return Response({"Error": "Failed to get the DG details,  drop hasn't been set in restcall."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.getCNDgQueuedDetailsByDrop(dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get the DG details. Please investigate: " + str(e))
            return Response("Failed to get the DG details. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateOldDgDeliveredDate(APIView):
    '''
    This is a POST Rest Api which updates the delivered date for old cENM DG.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.updateOldDgDeliveredDate()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update delivered date for old cENM DG. Please investigate: " + str(e))
            return Response("Failed to update delivered date for old cENM DG. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNDgDeliveredDetails(APIView):
    '''
    This is a GET Rest Api which returns details of all the DGs delivered in a given drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['dropNumber']
            if dropNumber is None:
                return Response({"Error": "Failed to get the DG details,  drop hasn't been set in restcall."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.getCNDgDeliveredDetailsByDrop(dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get the DG details. Please investigate: " + str(e))
            return Response("Failed to get the DG details. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateCnProdRevDevLink(APIView):
    '''
    This is a POST Rest Api which updates the dev_link column for cnProduct Revisions.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.updateDevLink()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update dev_link column for cnProduct Revisions. Please investigate: " + str(e))
            return Response("Failed to update dev_link column for cnProduct Revisions. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateCnImagesRepoName(APIView):
    '''
    This is a POST Rest Api which updates the repo name column for Cn Images.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.updateRepoName()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update the repo name for Cn Images. Please investigate: " + str(e))
            return Response("Failed to update the repo name for Cn Images. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateOldDgObsoletedDate(APIView):
    '''
    This is a POST Rest Api which updates the obsoleted date for old cENM DG.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.updateOldDgObsoletedDate()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update obsoleted date for old cENM DG. Please investigate: " + str(e))
            return Response("Failed to update obsoleted date for old cENM DG. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateOldDgDeletedDate(APIView):
    '''
    This is a POST Rest Api which updates the deleted date for old cENM DG.
    '''

    def post(self, request, *args, **kwargs):
        try:
            errorMsg = None
            result, errorMsg = cireports.utils.updateOldDgDeletedDate()
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to update deleted date for old cENM DG. Please investigate: " + str(e))
            return Response("Failed to update deleted date for old cENM DG. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNDgObsoletedDetails(APIView):
    '''
    This is a GET Rest Api which returns details of all the DGs obsoleted in a given drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['dropNumber']
            if dropNumber is None:
                return Response({"Error": "Failed to get the DG details,  drop hasn't been set in restcall."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.getCNDgObsoletedDetailsByDrop(dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get the DG details. Please investigate: " + str(e))
            return Response("Failed to get the DG details. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class GetCNDgDeletedDetails(APIView):
    '''
    This is a GET Rest Api which returns details of all the DGs deleted in a given drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['dropNumber']
            if dropNumber is None:
                return Response({"Error": "Failed to get the DG details,  drop hasn't been set in restcall."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = cireports.utils.getCNDgDeletedDetailsByDrop(dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Failed to get the DG details. Please investigate: " + str(e))
            return Response("Failed to get the DG details. Please investigate: " + str(e),
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class AddCNBuildLogData(APIView):
    '''
    This is a POST Rest Api which creates a new build log data.
    '''

    def post(self, request, *args, **kwargs):
        errorMsg = None
        try:
            decodedJson = json.loads(request.body)
            cnBuildlog_thread = DGThread(createCNBuildLogData, args=(decodedJson,))
            cnBuildlog_thread.start()
            cnBuildlog_thread.join()
            result, errorMsg = cnBuildlog_thread.get_result()
            if errorMsg != None:
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while creating CN Buildlog Data. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class GetCNBuildLogId(APIView):
    '''
    This is a GET Rest Api which returns the Build log id based on drop,to_ps and confidenceLevel name.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['drop']
            toPs = self.kwargs['toPs']
            confidenceLevel = self.kwargs['confLevelName']
            deployment = self.kwargs['deployment']
            if dropNumber is None or toPs is None or confidenceLevel is None:
                return Response({
                                    "Error": "Failed to get the the Build log data,  drop or toPs or cconfidenceLevel name hasn't been set in restcall."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = getCNBuildLogId(dropNumber, toPs, confidenceLevel, deployment)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while getting CN Buildlog Data. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class AddCNBuildLogComment(APIView):
    '''
    This is a POST Rest Api which adds comments and jira for build log data.
    '''

    def post(self, request, *args, **kwargs):
        errorMsg = None
        try:
            decodedJson = json.loads(request.body)
            result, errorMsg = createCNBuildLogComment(decodedJson["buildLogId"], decodedJson["comment"],
                                                       decodedJson["jira"])
            if errorMsg != None:
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while adding comments for CN Buildlog Data. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class EditCNBuildLogComment(APIView):
    '''
    This is a POST Rest Api which edits a comment for a CN build log.
    '''

    def post(self, request, *args, **kwargs):
        errorMsg = None
        try:
            decodedJson = json.loads(request.body)
            postUser = request.POST.get('user', request.user)
            user = User.objects.get(username=str(postUser))
            cnBuildLogGuards = config.get("CIFWK", "cnBuildlogGuards")
            if not user.groups.filter(name=cnBuildLogGuards).exists():
                return Response("Failed to edit the build log comment due to permission denied. Please "
                                "request the permission if needed.", status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = editCNBuildLogComment(decodedJson["commentId"], decodedJson["editComment"])
            if errorMsg != None:
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while editing comment for CN Buildlog Data. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class DeleteCNBuildLogComment(APIView):
    '''
    This is a DELETE Rest Api which deletes a comment for a CN build log.
    '''

    def delete(self, request, *args, **kwargs):
        errorMsg = None
        try:
            decodedJson = json.loads(request.body)
            postUser = request.POST.get('user', request.user)
            user = User.objects.get(username=str(postUser))
            cnBuildLogGuards = config.get("CIFWK", "cnBuildlogGuards")
            if not user.groups.filter(name=cnBuildLogGuards).exists():
                return Response("Failed to delete the comment due to permission denied. Please request the permission if needed.", status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = deleteCNBuildLogComment(decodedJson["commentId"])
            if errorMsg != None:
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while deleting comments for CN Buildlog Data. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class DeleteCNBuildLogJira(APIView):
    '''
    This is a DELETE Rest Api which deletes a jira issue from a CN build log.
    '''

    def delete(self, request, *args, **kwargs):
        errorMsg = None
        try:
            decodedJson = json.loads(request.body)
            postUser = request.POST.get('user', request.user)
            user = User.objects.get(username=str(postUser))
            cnBuildLogGuards = config.get("CIFWK", "cnBuildlogGuards")
            if not user.groups.filter(name=cnBuildLogGuards).exists():
                return Response("Failed to delete the ticket due to permission denied. Please request the permission if needed.", status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = deleteCNBuildLogJira(decodedJson["commentId"])
            if errorMsg != None:
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while deleting jira issue for CN Buildlog Data. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)


class GetCNBuildLogData(APIView):
    '''
    This is a GET Rest Api which returns the Build log data based on drop.
    '''

    def get(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            dropNumber = self.kwargs['drop']
            if dropNumber is None:
                return Response({
                                    "Error": "Failed to get the the Build log data,  drop or toPs or cconfidenceLevel name hasn't been set in restcall."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            result, errorMsg = getCNBuildLogDataByDrop(dropNumber)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while getting CN Buildlog Data. Please investigate: " + str(e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class UpdateCNBuildLogOverallStatus(APIView):
    '''
    This is a POST Rest Api which updates the build log overall status.
    '''

    def post(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            decodedJson = json.loads(request.body)
            if decodedJson["build_log_id"] == "":
                return Response("Error: Failed to update the overall status, buildlog id should not be empty.",
                                status=status.HTTP_400_BAD_REQUEST)
            result, errorMsg = updateCNBuildLogOverallStatus(decodedJson["build_log_id"], decodedJson["overall_status"])
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while updating CN Buildlog overall status. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class HideCNBuildLog(APIView):
    '''
    This is a PATCH Rest Api which updates the build log active status to false.
    '''

    def patch(self, request, *args, **kwargs):
        try:
            result = None
            errorMsg = None
            decodedJson = json.loads(request.body)
            postUser = request.POST.get('user', request.user)
            user = User.objects.get(username=str(postUser))
            cnBuildLogGuards = config.get("CIFWK", "cnBuildlogGuards")
            if not user.groups.filter(name=cnBuildLogGuards).exists():
                return Response("Failed to update the active status due to permission denied. Please request the permission if needed.", status=status.HTTP_403_FORBIDDEN)
            if decodedJson.get("build_log_id") == "":
                return Response("Error: Failed to update the active status, buildlog id should not be empty.",
                                status=status.HTTP_400_BAD_REQUEST)
            result, errorMsg = hideCNBuildLog(decodedJson["build_log_id"])
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            errorMsg = "Unexpected ERROR: Issue found while updating CN Buildlog active status. Please investigate: " + str(
                e)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)

class OverrideConfidenceLevel(APIView):
    '''
    This is a PATCH Rest Api which overrides the confidence level for ENM product sets.
    '''
    def patch(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            username = data.get("user")
            isOverridden = data.get("isOverridden")
            product = self.kwargs.get("product")
            release = self.kwargs.get("release")
            productSetVersion = self.kwargs.get("productSetVersion")
            confidenceLevelType = self.kwargs.get("confidenceLevelType")
            if not product or not release or not productSetVersion or not confidenceLevelType or not username or not isOverridden:
                return Response("Failed to override the confidence level. Insufficient parameters.", status=status.HTTP_412_PRECONDITION_FAILED)
            if str(isOverridden).lower() not in ['true', 'false']:
                return Response("Failed to override the confidence level. isOverridden value can only be either true or false.", status=status.HTTP_412_PRECONDITION_FAILED)
            isOverridden = False if str(isOverridden).lower() == "false" else True
            try:
                drop = getDropByProductSetVersion(str(productSetVersion))
            except ValueError as e:
                return Response("Failed to override the confidence level. Product set version not valid: " + str(e), status=status.HTTP_412_PRECONDITION_FAILED)
            user = User.objects.get(username=str(username))
            permGroup = config.get("CIFWK", "enmConfidenceLevelGuard")
            if not user.groups.filter(name=permGroup).exists():
                return Response("Failed to override the confidence level. Permission denied. The user is not part of the permission group.", status=status.HTTP_403_FORBIDDEN)
            result, errorMsg = overrideConfidenceLevel(str(product), str(release), str(drop), str(productSetVersion), str(confidenceLevelType), isOverridden)
            if errorMsg:
                logger.error(errorMsg)
                return Response(errorMsg, status=status.HTTP_400_BAD_REQUEST)
        except Exception as unexpectedError:
            errorMsg = "Failed to override confidence level due to unexpected error: " + str(unexpectedError)
            logger.error(errorMsg)
            return Response(errorMsg, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(result, status=status.HTTP_200_OK)