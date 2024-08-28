from rest_framework import generics, permissions, status
from django.utils.decorators import method_decorator
from .serializers import *
from .models import Sed, DeploymentBaseline, ClusterToInstallGroupMapping, MapTestResultsToDeployment, DeploymentTestcase, TestGroup, MapTestGroupToDeployment, Cluster, DeploymentStatus, VmServiceIpRange, VmServiceIpRangeItem, VirtualImage
from cireports.models import ProductSetVersion
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from re import sub
from rest_framework.authtoken.models import Token
from datetime import datetime
from .utils import *
from .deploy import getFreeCluster
from .buildconfig import generateDBConfigFile
from rest_framework.views import APIView
from django.http import Http404, HttpResponse
from .uploadContent import updateDataVMServices
import searchInventory
import json
from fem.utils import deploymentUtilitiesHandler


class ClusterViewSet(viewsets.ModelViewSet):
    model = Cluster
    serializer_class = ClusterSerializer
    permission_classes = [
        permissions.AllowAny
    ]
    queryset = Cluster.objects.all()

class IndividualClusterViewSet(viewsets.ModelViewSet):
    '''
    Class used to list back cluster infomation for a single deployment
    Inputs:
        Deployment ID
    Output:
        lists out the information for that given deployment
    '''
    serializer_class = IndividualClusterSerializer
    model = Cluster
    permission_classes = [
        permissions.AllowAny
    ]
    def get_queryset(self):
        deploymentId = self.kwargs['deploymentId']
        return Cluster.objects.filter(id=deploymentId)

class DeploymentBaselineDropViewSet(viewsets.ModelViewSet):
    serializer_class = DeploymentBaselineSerializer
    model = DeploymentBaseline
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        drop_name = self.kwargs['dropName']
        return DeploymentBaseline.objects.filter(dropName=drop_name)

class DeploymentBaselineViewSet(viewsets.ModelViewSet):
    model = DeploymentBaseline
    serializer_class = DeploymentBaselineSerializer
    permission_classes = [
        permissions.AllowAny
    ]
    queryset = DeploymentBaseline.objects.all()

    @detail_route(methods=['post'], url_path='change-master')
    def change_master(self,request,**kwargs):
        id = request.data['id']
        drop = request.data['drop']
        deploymentToUpdate  = DeploymentBaseline.objects.get(id=id)
        self.serializer_class = DeploymentBaselineSerializer

        if request.method == 'POST':
            dropDeployments = DeploymentBaseline.objects.filter(dropName=drop)
            for deploy in dropDeployments:
                deploy.masterBaseline = False
                deploy.save()
            deploymentToUpdate.masterBaseline = request.data['master']
            deploymentToUpdate.save()
            return Response()

    @detail_route(methods=['post'], url_path='change-taf')
    def change_taf(self,request,**kwargs):
        id = request.data['id']
        taf = request.data['taf']
        deploymentToUpdate  = DeploymentBaseline.objects.get(id=id)
        self.serializer_class = DeploymentBaselineSerializer

        if request.method == 'POST':
            deploymentToUpdate.tafVersion = taf
            deploymentToUpdate.save()
            return Response()

    @detail_route(methods=['post'], url_path='change-comment')
    def change_comment(self,request,**kwargs):
        id = request.data['id']
        comment = request.data['comment']
        deploymentToUpdate  = DeploymentBaseline.objects.get(id=id)
        self.serializer_class = DeploymentBaselineSerializer
        if comment != "":
            comment += " - " + str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        if request.method == 'POST':
            comment = str(deploymentToUpdate.comment)+ " \n "  + str(comment)
            deploymentToUpdate.comment = comment
            deploymentToUpdate.save()
            return Response()

    @detail_route(methods=['post'], url_path='change-availability')
    def change_availability(self,request,**kwargs):
        id = request.data['id']
        availability = request.data['availability']
        deploymentToUpdate  = DeploymentBaseline.objects.get(id=id)
        self.serializer_class = DeploymentBaselineSerializer

        if request.method == 'POST':
            deploymentToUpdate.availability = availability
            deploymentToUpdate.save()
            return Response()

class DeploymentBaselineDropGroupViewSet(viewsets.ModelViewSet):
    serializer_class = DeploymentBaselineSerializer
    model = DeploymentBaseline
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        group_name = self.kwargs['groupName']
        drop_name = self.kwargs['dropName']
        return DeploymentBaseline.objects.filter(dropName=drop_name).filter(groupName=group_name)

class DeploymentBaselineDropMasterViewSet(viewsets.ModelViewSet):
    serializer_class = DeploymentBaselineSerializer
    model = DeploymentBaseline
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        drop_name = self.kwargs['dropName']
        return DeploymentBaseline.objects.filter(dropName=drop_name).filter(masterBaseline=True)

class DeploymentToInstallViewSet(viewsets.ModelViewSet):
    model = ClusterToInstallGroupMapping
    serializer_class = DeploymentToInstallSerializer
    permission_classes = [
        permissions.AllowAny
    ]
    queryset = ClusterToInstallGroupMapping.objects.all()

class DeploymentToInstallClusterNameViewSet(viewsets.ModelViewSet):
    model = ClusterToInstallGroupMapping
    serializer_class = DeploymentToInstallSerializer
    permission_classes = [
        permissions.AllowAny
    ]

    def get_queryset(self):
        cluster_name = self.kwargs['cluster']
        return ClusterToInstallGroupMapping.objects.filter(cluster__name=cluster_name)

class DeploymentToInstallViewSet(viewsets.ModelViewSet):
    model = ClusterToInstallGroupMapping
    serializer_class = DeploymentToInstallSerializer
    queryset = ClusterToInstallGroupMapping.objects.all()


class DeploymentTestcaseViewSet(viewsets.ModelViewSet):
    model = DeploymentTestcase
    serializer_class = DeploymentTestcaseSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    queryset = DeploymentTestcase.objects.all()

    def create(self,request):
        serializer_class = DeploymentTestcaseSerializer
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            DeploymentTestcase.objects.create(**serializer.validated_data)
            return Response(serializer.validated_data, status=status.HTTP_201_CREATED)

        return Response({
            'status': 'Bad request',
            'message': 'Testcase could not be created with received data.'
        }, status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post'], url_path='edit-testcase')
    def editTestcase(self,request,**kwargs):
        id = request.data['id']
        testcase = request.data['testcase']
        testcase_description = request.data['testcase_description']
        enabled = request.data['enabled']
        testcaseToUpdate  = DeploymentTestcase.objects.get(id=id)
        self.serializer_class = DeploymentTestcaseSerializer

        if request.method == 'POST':
            testcaseToUpdate.testcase = testcase
            testcaseToUpdate.testcase_description = testcase_description
            testcaseToUpdate.enabled = enabled
            testcaseToUpdate.save()
            return Response()

    @detail_route(methods=['post'], url_path='delete-testcase')
    def deleteTestcase(self,request,**kwargs):
        id = request.data['id']
        testcaseToDelete  = DeploymentTestcase.objects.get(id=id)
        self.serializer_class = DeploymentTestcaseSerializer

        if request.method == 'POST':
            testcaseToDelete.delete()
            return Response()


class MapTestResultsToDeploymentViewSet(viewsets.ModelViewSet):
    model = MapTestResultsToDeployment
    serializer_class = MapTestResultsToDeploymentSerializer
    permission_classes = [
        permissions.AllowAny
    ]
    queryset = MapTestResultsToDeployment.objects.all()

class MapTestResultsToDeploymentFilterViewSet(viewsets.ModelViewSet):
    model = MapTestResultsToDeployment
    serializer_class = MapTestResultsToDeploymentSerializer
    permission_classes = [
        permissions.AllowAny
    ]
    def get_queryset(self):
        if 'date' in self.kwargs and 'group' in self.kwargs:
            group_name = self.kwargs['group']
            test_date = self.kwargs['date']
            cluster_group = []
            if MapTestGroupToDeployment.objects.filter(group__testGroup=group_name).exists():
                clusters = MapTestGroupToDeployment.objects.filter(group__testGroup=group_name)
                for cluster in clusters:
                    cluster_group.append((str(cluster.cluster)).split(' ')[0])
            td = test_date.split('-')
            if len(td) == 3:
                day = td[0]
                month = td[1]
                year = td[2]
            else:
                return None
            return MapTestResultsToDeployment.objects.filter(cluster__name__in=cluster_group).filter(testDate__year=year,
                                                                                                     testDate__month=month,
                                                                                                     testDate__day=day).order_by('-testDate')
        elif 'date' in self.kwargs:
            test_date = self.kwargs['date']
            td = test_date.split('-')
            if len(td) == 3:
                day = td[0]
                month = td[1]
                year = td[2]
            else:
                return None
            return MapTestResultsToDeployment.objects.filter(testDate__year=year,
                                                             testDate__month=month,
                                                             testDate__day=day)

class TestGroupViewSet(viewsets.ModelViewSet):
    model = TestGroup
    serializer_class = TestGroupSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    queryset = TestGroup.objects.all()

class TestGroupFilterViewSet(viewsets.ModelViewSet):
    model = TestGroup
    serializer_class = TestGroupSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_queryset(self):
        default_group = self.kwargs['default']
        return TestGroup.objects.filter(defaultGroup=default_group)

class MapTestGroupToDeploymentViewSet(viewsets.ModelViewSet):
    model = MapTestGroupToDeployment
    serializer_class = MapTestGroupToDeploymentSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    queryset = MapTestGroupToDeployment.objects.all()

class DeploymentStatusViewSet(APIView):
    '''
    For getting and setting the status on a given Deployment
    '''
    def get(self, request, *args, **kwargs):
        id = self.kwargs['id']
        statusValue = ""
        try:
            statusValue = str(DeploymentStatus.objects.only('status__status').get(cluster__id=id).status.status)
        except Exception as e:
            return HttpResponse("Error getting the Deployment Status for Deployment: this ID "  +str(id) + " is invalid, " + str(e), status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(statusValue, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        id = self.kwargs['id']
        statusValue = request.data.get('setStatus')
        if not statusValue or statusValue == 'None':
            return HttpResponse("Error: setStatus parameter required.\n", status=status.HTTP_428_PRECONDITION_REQUIRED)
        statuValue = str(statusValue).upper()
        result = setClusterStatus(id, statusValue)
        if result == 0:
            return HttpResponse(result, status=status.HTTP_200_OK)
        return HttpResponse(result, status=status.HTTP_404_NOT_FOUND)

class UpdateClusterServerActiveStatus(APIView):
    '''
    The UpdateClusterServerActiveStatus sets the status of a cluster server to active or passive
    '''
    def get(self, request, *args, **kwargs):
        user = request.user.pk
        action = "edit"
        clusterServerID = self.kwargs['clusterServerId']
        try:
            clusterServer = ClusterServer.objects.get(id=clusterServerID)
            if clusterServer.active:
                clusterServer.active = False
                clusterServer.save(force_update=True)
                clusterServerStatus = "PASSIVE"
            else:
                clusterServer.active = True
                clusterServer.save(force_update=True)
                clusterServerStatus = "ACTIVE"
            clusterObj = Cluster.objects.get(id=clusterServer.cluster.id)
            clusterServerHostname = clusterServer.server.hostname
            message = "Edited Deployment Server Status, Server " + clusterServerHostname + " status set to \"" + clusterServerStatus + "\""
            dmt.logUserActivity.logAction(str(user), clusterObj, action, message)
            return Response("success",status=status.HTTP_200_OK)
        except ClusterServer.DoesNotExist():
            return Response("error",status=status.HTTP_404_NOT_FOUND)

class InstallGroupFailedDeploymentsCheckViewSet(APIView):
    '''
    Changing all Failed Deployments that have been failed for over 24 hours
    '''
    def get(self, request, *args, **kwargs):
        result = checkFailedDeploymentsInInstallGroups()
        return Response(result, status=status.HTTP_200_OK)

class GetFreeClusterFromGroupAndSetStatus(APIView):
    '''
    The getFreeClusterIDFromGroupAndSetStatus RESTFul Service GETS a cluster id from a group and sets the Cluster to BUSY.
    This GET takes one parameter 'clusterGroup'
    '''
    def get(self, request, *args, **kwargs):
        installGroup = self.kwargs['installGroup']
        result = getFreeCluster(installGroup, "BUSY")
        response = getFreeClusterInInstallGroupAndSetStatus(result)
        return Response(response, status=status.HTTP_200_OK)

class GeneratedSedFile(APIView):
    '''
    This class is used to generate the SED file for a given deployment over rest
    Inputs:
        Sed Version, this can be the actual version or master
        Deployment Id
    Output:
        Generated SED file according to the version of the SED inputted
    '''
    def get(self, request, *args, **kwargs):
        sedVersion = self.kwargs['sedVersion']
        deploymentId = self.kwargs['deploymentId']
        if "master" in sedVersion.lower():
            sedVersion = getVirtualMasterSedVersion()
        response = generateDBConfigFile(deploymentId,sedVersion)
        return HttpResponse(response,content_type="text/plain")

class DownloadSedTemplate(APIView):
    '''
    This class is used to generate the SED Template file
    Inputs:
        Sed Template Version, this can be the actual version or master
    Output:
        Generated SED Template file according to the version of the SED inputted
    '''
    def get(self, request, *args, **kwargs):
        sedVersion = self.kwargs['sedVersion']
        if "master" in sedVersion.lower():
            sedVersion = getVirtualMasterSedVersion()
        if not Sed.objects.filter(version=sedVersion).exists():
            message="SED Template version "+str(sedVersion)+" does not exist"
            logger.error(message)
            return HttpResponse(message,content_type="text/plain")
        sedVersionObj = Sed.objects.only('sed').values('sed').get(version=sedVersion)
        template = sedVersionObj['sed']
        return HttpResponse(template,content_type="text/plain")

class GetDeploymentInformation(APIView):
    def get(self, request, *args, **kwargs):
        '''
        This class is used to get the miscellaneous deployment information that was used to deploy an ENM iso\n
        It retrieves information on the sed template version, deployment tar file and the maintrack utilities package used to deploy the ENM iso\n
        \n
        Inputs:\n
        Product:        This the project name i.e. ENM\n
        Product Type:   This refers to the type of product you want to search against there are two options productset or drop\n
        Product Drop:   This is the drop/product set number you wish to search against\n
        Version:        This is the version of the iso in the drop or version of the product set to search against this is optional if not set then this will default to LATEST\n
        \n
        Outputs:\n
        Returns a json object, of the information that is currently attached to the ENM iso in relation to the deployment information.\n
        \n
        Example Command to search against a product set:\n
        GET /api/deployment/info/#Product#/#Product Type#/#Product Drop#/#Version#/\n
        e.g.\n
        GET /api/deployment/info/ENM/productset/16.8/16.8.59/\n
        \n
        Example Command to search against a drop:\n
        GET /api/deployment/info/#Product#/#Product Type#/#Product Drop#/#Version#/\n
        e.g.\n
        GET /api/deployment/info/ENM/drop/16.8/1.23.64/\n
        ---
        parameters:
        - name: product
          description: This is in relation to the project i.e. ENM.
          required: true
          type: string
          paramType: path
        - name: productType
          description: This is what area within the project to search against option are either directly to the drop or through the product set
          required: true
          type: string
          paramType: path
        - name: productDrop
          description: This is the drop name or the product set name i.e. 16.8
          required: true
          type: string
          paramType: path
        - name: version
          description: This is the either the version of the iso if the drop was entered or the version of the product set if the product set was entered. Nothing added then this will default to LATEST
          required: false
          type: string
          paramType: path
        '''
        result = ""
        product = productType = productDrop = version = None
        product = self.kwargs['product'].upper()
        if product != "ENM":
            return Response("Error: Please specify a supported product i.e. ENM", status=status.HTTP_404_NOT_FOUND)
        productType = self.kwargs['productType']
        if productType != "productset" and productType != "drop":
            return Response("Error: Please specify a product type you wish to search against. Options productset or drop", status=status.HTTP_404_NOT_FOUND)
        if "productDrop" in self.kwargs:
            productDrop = self.kwargs['productDrop']
        if "version" in self.kwargs:
            version = self.kwargs['version']
        (ret,result) = getDeploymentInfo(product,productType,productDrop,version)
        if ret == 1:
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        return Response(result, status=status.HTTP_200_OK)

class executeVerifyOfDeploymentViewSet(APIView):
    def get(self, request, *args, **kwargs):
        '''
        This class is used to verify the VM services which are attached to peer nodes against the deployment description inputted.\n
        It does this by generation a sed using the sed version inputted and comparing the generated sed to the specified deployment description package and using the deployment description xml file specified from the package deployment description xml file specified from the package.\n
        \n
        Inputs:\n
        Deployment ID: this is the id of the deployment to be checked.\n
        Sed Version: This is the version of the sed to valid against.\n
        Deployment Description Version: This is the version of the deployment description to validate the sed against.\n
        Deployment Description Type: This is the type of deployment description file to download, official(delivered to the portal) or slice (snapshot version with all the slice deployment descriptions).\n
        Deployment Description File Name: This is the name of the xml file from the deployment package that should be used for the comparison.\n
        \n
        Outputs:\n
        Returns a json object, a summary of the verification, if nothing is returned in the json all is good.\n
        \n
        Example Command:\n
        GET /api/deployment/verify/\<DEPLOYMENT ID\>/sedVersion/\<SED VERSION\>/?depDescVersion=\<Deployment Description Version\>&depDescType=<Deployment description Type>&depDescFileName=<Deployment Description File Name>\n
        e.g.\n
        GET /api/deployment/verify/239/sedVersion/1.0.112/?depDescVersion=1.16.10&depDescType=slice&depDescFileName=2svc_enm-full-cdb-ssgid-deployment_cloud_test_dd.xml\n
        ---
        parameters:
        - name: deploymentId
          description: This is the id of the deployment to be checked.
          required: true
          type: string
          paramType: path
        - name: sedVersion
          description: This is the version of the sed to valid against.
          required: true
          type: string
          paramType: path
        - name: depDescVersion
          description: This is the deployment description package version.
          required: true
          type: string
          paramType: query
        - name: depDescType
          description: This is the type of deployment description file to download, official(delivered to the portal) or slice (snapshot version with all the slice deployment descriptions).
          required: true
          type: string
          paramType: query
        - name: depDescFileName
          description: This is the name of the xml file from the deployment package that should be used for the comparison
          required: true
          type: string
          paramType: query

        '''
        action = 'verify'
        task = 'verify'
        inputDataDict = {}
        inputDataDict['users'] = []
        inputDataDict['loginUser'] = ''
        inputDataDict['depDescPackage'] = 'ERICenmdeploymenttemplates_CXP9031758'
        inputDataDict['file'] = ''
        inputDataDict['populateDDorSED'] = ''
        inputDataDict['populateDnsorMan'] = 'populateDNSIP'
        inputDataDict['task'] = task
        deploymentId = self.kwargs['deploymentId']
        if not deploymentId or deploymentId == 'None':
            return Response("Error: Deployment ID required.", status=status.HTTP_404_NOT_FOUND)
        if not Cluster.objects.filter(id=deploymentId).exists():
            raise Response("Error: Given deployment ID does not exist.", status=status.HTTP_404_NOT_FOUND)
        inputDataDict['deploymentId'] = deploymentId
        sedVersion = self.kwargs['sedVersion']
        if not sedVersion or sedVersion == 'None':
            return Response("Error: Sed Version is required.", status=status.HTTP_404_NOT_FOUND)
        if str(sedVersion).upper() == "MASTER":
            sedVersion = dmt.utils.getVirtualMasterSedVersion()
        if not Sed.objects.filter(version=sedVersion).exists():
            raise Response("Error: Given Sed Version does not exist.", status=status.HTTP_404_NOT_FOUND)
        inputDataDict['sedVersion'] = sedVersion
        depDescVersion = request.query_params.get('depDescVersion',None)
        if not depDescVersion or depDescVersion == 'None':
            return Response("Error: Deployment Description Version is required.", status=status.HTTP_404_NOT_FOUND)
        inputDataDict['depDescVersion'] = depDescVersion
        depDescType = request.query_params.get('depDescType',None)
        if not depDescType or depDescType == 'None':
            return Response("Error: Deployment Description Type is required.", status=status.HTTP_404_NOT_FOUND)
        if "slice" not in depDescType and "rpm" not in depDescType:
            return Response("Error: Deployment Description Type Options are \"rpm\" or \"critical-slice\" or \"team-slice\", Please choose one..", status=status.HTTP_404_NOT_FOUND)
        inputDataDict['depDescType'] = depDescType
        depDescFileName = request.query_params.get('depDescFileName',None)
        if not depDescFileName or depDescFileName == 'None':
            return Response("Error: Deployment Description File Name is required.\n", status=status.HTTP_404_NOT_FOUND)
        inputDataDict['depDescFileName'] = depDescFileName
        jsonData = json.dumps(inputDataDict)
        try:
            (ret,result) = updateDataVMServices(action,jsonData,task)
            if ret != 0:
                return Response("ERROR: Running the Service VM verification, Please investigate.." +str(result), status=status.HTTP_404_NOT_FOUND)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as error:
            return Response("ERROR: Running the Service VM verification, Please investigate.." + str(error), status=status.HTTP_404_NOT_FOUND)

class GetServiceVMIpRangeItems(viewsets.ModelViewSet):
    '''
    This class is used to return back the ip range types
    Input:
        None
    Output
        lists back the Service VM IP Range items
    '''
    model = VmServiceIpRangeItem
    serializer_class = GetServiceVMIpRangeItemsSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    queryset = VmServiceIpRangeItem.objects.all()

class GetServiceVMIpRanges(viewsets.ModelViewSet):
    '''
    This class is used to return back the ip ranges assigned to a given deployment
    Inputs:
        Deployment ID
        Type of ip range to return.
            If all is given all ranges will be returned
            Else give the corresponding id of the IP Type
    Output:
        list back the ip ranges registered against the deployment
    '''
    model = VmServiceIpRange
    serializer_class = GetServiceVMIpRangesSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_queryset(self):
        deploymentId = self.kwargs['deploymentId']
        typeId = self.kwargs['typeId']
        if "all" in typeId:
            return VmServiceIpRange.objects.filter(cluster=deploymentId)
        else:
            return VmServiceIpRange.objects.filter(cluster=deploymentId,ipTypeId=typeId)

class GetServiceVMDnsIpRanges(viewsets.ModelViewSet):
    '''
    This class is used to return back the ip ranges assigned in DNS to a given deployment
    Inputs:
        Deployment ID
        Type of DNS ip range to return.
            If all is given all ranges will be returned
            Else give the corresponding id of the IP Type
    Output:
        list back the DNS ip ranges registered against the deployment
    '''
    model = AutoVmServiceDnsIpRange
    serializer_class = GetServiceVMDnsIpRangesSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_queryset(self):
        deploymentId = self.kwargs['deploymentId']
        typeId = self.kwargs['typeId']
        if "all" in typeId:
            return AutoVmServiceDnsIpRange.objects.filter(cluster=deploymentId)
        else:
            return AutoVmServiceDnsIpRange.objects.filter(cluster=deploymentId,ipTypeId=typeId)

class GetAllDmtIps(viewsets.ModelViewSet):
    '''
    This class is used to return all public DMT IP addresses.
    '''
    model = IpAddress
    serializer_class = GetDMTIpAddressesSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_queryset(self):
        return IpAddress.objects.exclude(ipv4UniqueIdentifier=1).exclude(ipv6UniqueIdentifier=1)


class GetServiceInfo(viewsets.ModelViewSet):
    '''
    This class is used to get back all the VM Service infomation according to the deployment ID entered
    Inputs:
        Deployment ID
    Output:
        lists back all the VM service information attached to a deployment
    '''
    model = VirtualImage
    serializer_class = GetDeploymentDetailsForVirtualImageData
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get_queryset(self):
        deploymentId = self.kwargs['deploymentId']
        return VirtualImage.objects.filter(cluster=deploymentId)

class SearchDeploymentInventory(APIView):
    '''
    This class is used to return the deployment information realted to an IP address or Hostname
    Inputs:
        ValueEntered.  Can be a Hostname, Ipaddress, MAC address
    Output:
        Lists all Deployment Information related to the value entered
    '''
    def get(self, request, *args, **kwargs):
        valueEntered = self.kwargs['valueEntered']
        response_list = searchInventory.searchInventory(valueEntered)
        response_encoded = json.dumps(response_list, cls=ComplexEncoder)
        response = json.loads(response_encoded)
        if len(response) == 0:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        return Response(response, status=status.HTTP_200_OK)

class ValidateAutoDeployPackages(APIView):
    '''
    The ValidateAutoDeployPackages class validates artifacts that are entered into the --deployPackages option of the auto deployment scripts
    The GET Rest service can also be used independently to auto deployment
    Artifacts are defined like:
        artifactName::artifactVersion
        artifactName::latest
        artifactName::urlToRemoteArtifact
        artifactName::artifactVersion::artifactCategory
        artifactName::latest::artifactCategory
        artifactName::urlToRemoteArtifact::artfactCategory
    The Above options can also be included in a '@@' seperated list
    '''
    def get(self, request, *args, **kwargs):
        artifactList = self.kwargs['artifacts']
        response = validateAutoDeployPackages(artifactList)
        if "error" in response:
            return Response(response, status=status.HTTP_412_PRECONDITION_FAILED)
        return Response(response, status=status.HTTP_200_OK)


class UpdateClusterAdditionalProperties(APIView):
    '''
    The UpdateClusterAdditionalProperties used to Update allready existed cluster with new data or create a new data in the cluster.
    '''
    def post(self, request, *args, **kwargs):
        try:
            user = str(request.data.get('signum'))
            if user == "None":
                return Response({"ERROR": "Provide a signum"}, status=status.HTTP_428_PRECONDITION_REQUIRED)
            elif not User.objects.filter(username=user).exists():
                return Response({"ERROR": "User not found using signum: " + user}, status=status.HTTP_428_PRECONDITION_REQUIRED)
            else:
                user = User.objects.get(username=user).pk
            clusterId = self.kwargs['clusterId']
            ddp_hostname = request.data.get('ddp_hostname')
            cron = request.data.get('cron')
            port = request.data.get('port')
            time = request.data.get('time')
            if (port and not len(port) <= 4):
                return Response({"ERROR": "Failed to add a port number, no more than 4 digits. E.g (8080)."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            elif (port and not port.isdigit()):
                return Response({"ERROR": "Failed to add a port number, make sure it contains only numbers. E.g (8080)."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            if (time and not time.isdigit()):
                return Response({"ERROR": "Failed to add a time number, make sure it contains only numbers which is in minutes. E.g (30)."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            elif (time and int(time) > 60):
                return Response({"ERROR": "Failed to add a time number, make sure it's value is no greater than 60 minutes. E.g (30)."},
                                status=status.HTTP_412_PRECONDITION_FAILED)
            response = updateOrCreateClusterAdditionalProps(user, clusterId, ddp_hostname, cron, port, time)
            if not "success" in response:
                return Response({"ERROR": response}, status=status.HTTP_404_NOT_FOUND)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue with updating Cluster additional properties: " + str(e)
            logger.error(errMsg)
            return Response({"ERROR": errMsg},status=status.HTTP_404_NOT_FOUND)


class GetClusterAdditionalProperties(APIView):
    '''
    The GetClusterAdditionalProperties is used to get addtional properties from cluster.
    '''
    def get(self, request, *args, **kwargs):
        try:
            clusterId = self.kwargs['clusterId']
            if not Cluster.objects.filter(id=clusterId).exists():
                return Response({'ERROR': 'Given deployment ID does not exist.'}, status=status.HTTP_404_NOT_FOUND)
            response  = getClusterAdditionalProps(clusterId)
            if "Issue" in response:
                return Response({'ERROR':response}, status=status.HTTP_404_NOT_FOUND)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting Cluster additional properties: " + str(e)
            logger.error(errMsg)
            return Response({'ERROR':errMsg},status=status.HTTP_404_NOT_FOUND)

class LMSPassword(APIView):
    def get(self, request, *args, **kwargs):
        try:
            lmsHostname = self.kwargs['lmsHostname']
            user = self.kwargs['user']
            signum = self.kwargs['signum']
            accessAllowed, message = checkUserAccessToLmsPasswords(signum, lmsHostname)
            if not accessAllowed:
                return Response(message, status=status.HTTP_401_UNAUTHORIZED)
            password = getLmsUserPassword(lmsHostname, user)
            if password is not None:
                return Response(password, status=status.HTTP_200_OK)
            return Response("No password found for this user.", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            errMsg = "Server error while retreiving password for this user and management server: " + str(e)
            return Response(errMsg,status=status.HTTP_404_NOT_FOUND)
    def post(self, request, *args, **kwargs):
        try:
            lmsHostname = request.POST.get('hostname')
            password = request.POST.get('password')
            user = request.POST.get('user')
            signum = request.POST.get('signum')
            credType = config.get('DMT', 'rhelUserType')
            accessAllowed, message = checkUserAccessToLmsPasswords(signum, lmsHostname)
            if not accessAllowed:
                return Response(message, status=status.HTTP_401_UNAUTHORIZED)
            success, message = createOrEditMgmtServerCredentials(password, credType, lmsHostname, user, signum)
            if success:
                return Response(message, status=status.HTTP_200_OK)
            else:
                return Response(message, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            errMsg = "Unable to set new password: " + str(e)
            return Response(errMsg,status=status.HTTP_404_NOT_FOUND)

class ManageDeploymentServer(APIView):
    '''
    This function adding the server into cluster.
    '''
    def post(self, request, *args, **kwargs):
        clusterId = self.kwargs['clusterId']

        response = manageDeploymentServerCreation(request.data, clusterId)
        if "Error 412" in response:
            return Response(response, status=status.HTTP_412_PRECONDITION_FAILED)
        elif "Error 404" in response:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        return Response(response, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        clusterId = self.kwargs['clusterId']

        try:
            Cluster.objects.get(id = clusterId)
        except Exception as e:
            message = "Issue getting the Deployment Id - " + str(clusterId) + " : " + str(e)
            logger.error(message)
            return Response(message, status=status.HTTP_404_NOT_FOUND)

        receivedJsonData  = json.loads(request.body.decode('utf-8'))
        response = manageDeploymentServerDeletion(receivedJsonData, clusterId)
        if "error" in response:
            return Response(response, status=status.HTTP_412_PRECONDITION_FAILED)
        return Response(response, status=status.HTTP_200_OK)

class DeploymentUtilities(APIView):
    '''
    The DeploymentUtilities API allows a user to add DeploymentUtilities to an ISO Version which will be reflective on the Product Set Test Reports
    '''
    def post(self, request, *args, **kwargs):
        errMsg = ""
        utilityData = self.kwargs['utilityData']
        try:
           isoBuildObj = ISObuild.objects.get(version=self.kwargs['isoBuildVersion'],drop__release__product__name=self.kwargs['product'].upper(),mediaArtifact__testware=False, mediaArtifact__category__name="productware")
        except Exception as error:
            errMsg = "Error: There was an issue retreiving specified ISO Build Version in the CI DB : " + str(error)
            logger.error(errMsg)
            return Response(errMsg,status=status.HTTP_428_PRECONDITION_REQUIRED)
        try:
           deploymentUtilitiesHandler(utilityData,isoBuildObj)
        except Exception as error:
            errMsg = "Error: There was an issue adding deployment Utilities: " + str(utilityData) + " on ISOBuild: " + str(isoBuildVersion) + " to the CI DB, error: " +str(error)
            logger.error(errMsg)
            return Response(errMsg,status=status.HTTP_428_PRECONDITION_REQUIRED)
        return Response("success", status=status.HTTP_200_OK)


class GetLatestVersion(APIView):
    '''
    The GetLatestVersion class checks for latest version
    Artifact can be defined like:
        artifactName::artifactVersion::artifactCategory
        artifactName::artifactVersion
    '''
    def get(self, request, *args, **kwargs):
        artifactList=request.query_params.get('artifacts',None)
        if artifactList is not None:
            response = getLatestVersion(artifactList)
            if "ERROR" in response:
                return Response(response,status=status.HTTP_412_PRECONDITION_FAILED)
            return Response(response, status=status.HTTP_200_OK)

class GetInstallGroup(APIView):
    '''
    The GetInstallGroup GET Rest service will return all the Deployments in an Install Group and the data within the install group
    '''
    def get(self, request, *args, **kwargs):
        installGroup = request.query_params.get('installGroup',None)
        statusFilter = request.query_params.get('status',None)
        if installGroup == None:
            return Response({"ERROR" : "Please ensure that a install group is specified."},status=status.HTTP_412_PRECONDITION_FAILED)
        if statusFilter != None:
            if not DeploymentStatusTypes.objects.filter(status=statusFilter).exists():
                return Response({"ERROR" : "Please ensure that a valid status is defined."},status=status.HTTP_412_PRECONDITION_FAILED)
        response = getInstallGroups(installGroup,statusFilter)
        if "ERROR" in response:
            return Response(response,status=status.HTTP_412_PRECONDITION_FAILED)
        return Response(response, status=status.HTTP_200_OK)

class GetDeploymentUtilitiesWithProductSetVersion(APIView):
    '''
    Getting Deployment Utilities With a Product Set Version
    '''
    def get(self, request, *args, **kwargs):
        try:
            mediaArtifactName = self.kwargs['mediaArtifact']
        except:
            mediaArtifactName = None
        try:
            productSet = self.kwargs['productSet']
        except:
            return Response("Product Set Required",status=status.HTTP_428_PRECONDITION_REQUIRED)
        try:
            productSetVersion = self.kwargs['productSetVersion']
        except:
            productSetVersion = None

        if productSetVersion:
            try:
                productSetVersion = ProductSetVersion.objects.get(productSetRelease__productSet__name=productSet, version=productSetVersion)
            except ProductSetVersion.DoesNotExist:
                errMsg = "Error: There was issue getting deployment Utilities for: " + str(productSet) + "-" +  str(productSetVersion) + ", Product Set Version Does Not Exist"
                logger.error(errMsg)
                return Response(errMsg,status=status.HTTP_412_PRECONDITION_FAILED)
        response = getDeploymentUtilitiesWithProductSet(productSet, productSetVersion, mediaArtifactName)
        if "ERROR" in response:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        return Response(response, status=status.HTTP_200_OK)

class GetDeploymentTemplatesVersionWithProductSetVersion(APIView):
    '''
    Getting Deployment Templates Version With a Product Set, by default get latest passed version
    '''
    def get(self, request, *args, **kwargs):
        try:
            productSet = self.kwargs['productSet']
        except:
            return Response("Product Set Required",status=status.HTTP_428_PRECONDITION_REQUIRED)
        try:
            productSetVersion = self.kwargs['productSetVersion']
        except:
            productSetVersion = None

        if productSetVersion:
            try:
                productSetVersion = ProductSetVersion.objects.get(productSetRelease__productSet__name=productSet, version=productSetVersion)
            except Exception as error:
                errMsg = "Error: There was getting Product Set Version Ref in DB for: " + str(productSet) + "-" +  str(productSetVersion) + ", " +str(error)
                logger.error(errMsg)
                return Response(errMsg,status=status.HTTP_412_PRECONDITION_FAILED)
        response = getDeploymentTemplatesWithProductSet(productSet, productSetVersion)
        if "ERROR" in response:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        return Response(response, status=status.HTTP_200_OK)

class UpdateDeploymentDescriptions(APIView):
    '''
    Updates the Deployment Descriptions Data in DB
    '''

    def post(self, request, *args, **kwargs):
        try:
            depDescVerison = self.kwargs['version']
            setLatest = request.query_params.get('setLatest', True)
        except Exception as error:
            errMsg = "Error: There was an issue getting the Deployment Description Version: " + str(error)
            logger.error(errMsg)
            return Response(errMsg,status=status.HTTP_428_PRECONDITION_REQUIRED)
        try:
            response = updateDeploymentDescriptionsData(depDescVerison, setLatest)
            if "ERROR" in response:
                return Response(response, status=status.HTTP_404_NOT_FOUND)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as error:
            errMsg = "Error: There was an issue updating the Deployment Description Data: " + str(error)
            logger.error(errMsg)
            return Response(errMsg,status=status.HTTP_404_NOT_FOUND)


class GetDeploymentDescriptions(APIView):
    '''
    Getting Deployment Descriptions Data
    '''
    def get(self, request, *args, **kwargs):
        try:
            depDescVerison = self.kwargs['version']
            depDescType = self.kwargs['ddType']
        except Exception as error:
            errMsg = "There was an issue getting the Deployment Description Version and Type: " + str(error)
            errorReturn = {"error": str(errMsg)}
            logger.error(errMsg)
            return Response(errorReturn,status=status.HTTP_428_PRECONDITION_REQUIRED)
        try:
            capacityType = self.kwargs['capacityType']
        except:
            capacityType = None
        try:
            response = getDeploymentDescriptionData(depDescVerison, depDescType, capacityType)
            if "error" in response:
                return Response(response, status=status.HTTP_404_NOT_FOUND)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as error:
            errMsg = "There was an issue getting the Deployment Description Data: " + str(error)
            errorReturn = {"error": str(errMsg)}
            logger.error(errMsg)
            return Response(errorReturn,status=status.HTTP_404_NOT_FOUND)


class UpdateClustersServicesWithDD(APIView):
    '''
    Updates the Auto Update Clusters with services in the specified DD
    '''
    authentication_classes = (BasicAuthentication,)
    def post(self, request, *args, **kwargs):
        try:
            if 'clusterId' in self.kwargs:
                clusterId = self.kwargs['clusterId']
                response = updateClustersServicesWithDD(clusterId)
                return HttpResponseRedirect("/dmt/deploymentUpdatedReport/"+clusterId+"/")
            else:
                response = updateClustersServicesWithDD()
            if "ERROR" in response:
                return Response(response, status=status.HTTP_404_NOT_FOUND)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as error:
            errMsg = "Error: There was an issue updating the Clusters with services from Deployment Descriptions: " + str(error)
            logger.error(errMsg)
            if 'clusterId' in self.kwargs:
                return HttpResponseRedirect("/dmt/deploymentUpdatedReport/"+clusterId+"/")
            return Response(errMsg,status=status.HTTP_404_NOT_FOUND)


class SetDeploymentServersStatus(APIView):
    '''
    Updates Servers in a cluster based on their hostname
    '''
    def post(self, request, *args, **kwargs):
        user = request.data.get('signum')
        clusterId = request.data.get('clusterId')
        serverStatus = request.data.get('status')
        serverHostnameList = request.data.get('hostnameList')

        if not serverStatus or not (serverStatus.lower() == "active" or serverStatus.lower() == "passive"):
            return HttpResponse("Error: No Status (Passive/Active) found.\n", status=status.HTTP_428_PRECONDITION_REQUIRED)
        if not user or not User.objects.filter(username=user).exists():
            return HttpResponse("Error: User not found.\n", status=status.HTTP_428_PRECONDITION_REQUIRED)
        else:
            userObj = User.objects.get(username=user)
            userId = userObj.pk
        if not serverHostnameList or serverHostnameList == 'None' or not clusterId or clusterId == 'None':
            return HttpResponse("Error: Cluster Id or List of hostnames is empty.\n", status=status.HTTP_428_PRECONDITION_REQUIRED)
        response = setDeploymentServersStatus(userId, clusterId, serverStatus, serverHostnameList)
        if "ERROR" in response:
            return HttpResponse(response, status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(response, status=status.HTTP_200_OK)


class UpdateClusterIPRanges(APIView):
    '''
    Updates all cluster IP Ranges based on the current DNS dump
    '''
    def post(self, request, *args, **kwargs):
        user = request.user.pk
        if user is None:
            user = User.objects.get(username="admin").pk
        try:
            if 'clusterId' in self.kwargs:
                clusterId = self.kwargs['clusterId']
                response = updateClusterIPRanges(user, clusterId)
            else:
                response = updateClusterIPRanges(user)
            if "ERROR" in response:
                return Response(response, status=status.HTTP_404_NOT_FOUND)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as error:
            errMsg = "Error: There was an issue updating the Clusters with IP Ranges from DNS: " + str(error)
            logger.error(errMsg)
            return Response(errMsg,status=status.HTTP_404_NOT_FOUND)


class GetDeploymentDD(APIView):
    '''
    Getting a Deployment's Deployment Description Data, using the Deployment's ID
    '''
    def get(self, request, *args, **kwargs):
        try:
            clusterId = self.kwargs['clusterId']
            result, statusCode = getDeploymentDDdata(clusterId)
            if statusCode != 200:
                return Response({"error": str(result)}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status = status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting Deployment's Deployment Description: " + str(e)
            logger.error(errMsg)
            return Response({ "error": str(errMsg)}, status = status.HTTP_404_NOT_FOUND)


class UpdateDeploymentDD(APIView):
    '''
    Updating a Deployment's Deployment Description Name, using the Deployment's ID & given DD Name
    '''
    def post(self, request, *args, **kwargs):
        try:
            user = str(request.data.get('signum'))
            if user == "None":
                return Response({"Error": "Provide a signum"}, status=status.HTTP_428_PRECONDITION_REQUIRED)
            elif not User.objects.filter(username=user).exists():
                return Response({"Error": "User not found using signum: " + user}, status=status.HTTP_428_PRECONDITION_REQUIRED)
            else:
                user = User.objects.get(username=user).pk
            clusterId = self.kwargs['clusterId']
            ddName = self.kwargs['ddName']
            result, statusCode = updateDeploymentWithDDFile(user, clusterId, ddName)
            if statusCode != 200:
                return Response({"Error": str(result)}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status = status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue updating Deployment's Deployment Description: " + str(e)
            logger.error(errMsg)
            return Response({"Error": str(errMsg)}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetNasDetails(APIView):
    '''
    This class is used to return back the NAS Details using NAS hostname
    or the Cluster/Deployment Id that uses a NAS.
    Inputs:
       NAS hostname or Cluster/Deployment Id
    Output:
        In Json NAS Details from the DB
    '''
    def get(self, request, *args, **kwargs):
        try:
            result, statusCode = getNasInformation(self.kwargs['input'])
            if statusCode != 200:
                return Response({"error": str(result)}, status=status.HTTP_404_NOT_FOUND)
            return Response(result, status = status.HTTP_200_OK)
        except Exception as e:
            errMsg = "There was an issue getting the NAS Details: " + str(e)
            logger.error(errMsg)
            return Response({ "error": str(errMsg)}, status = status.HTTP_404_NOT_FOUND)
