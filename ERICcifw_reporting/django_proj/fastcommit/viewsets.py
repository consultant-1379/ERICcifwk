from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import list_route
from .models import DockerImageVersionContents, DockerImageVersion, DockerImage
from cireports.models import PackageRevision
from .serializers import DockerImageVersionContentsPostSerializer, DockerImageVersionContentsSerializer
from rest_framework.response import Response
from rest_framework import status


class DockerImageContentsViewSet(ModelViewSet):
    """
    This ViewSet is used to store and retrieve the contents of the fast commit docker images
    It allows GET, POST, PUT, DELETE requests
    There is also another url available through the list_route
    """
    queryset = DockerImageVersionContents.objects.all()
    serializer_class = DockerImageVersionContentsSerializer

    def create(self, request):
        """
        This overwrites the default create functionality to allow for storing a multi level model structure.
        @param request: json input from the rest endpoint
        @return: Response object with either a success status or failure
        """
        serializer = DockerImageVersionContentsPostSerializer(data=request.data)
        if serializer.is_valid():
            image_version_data = serializer.validated_data['image_version']
            try:
                image = DockerImage.objects.get_or_create(name=image_version_data['image']['name'])[0]
                image_version = DockerImageVersion.objects.get_or_create(image=image,
                                                                         version=image_version_data['version'])[0]
                for package in serializer.validated_data['package_revision']:
                    try:
                        package_revision = PackageRevision.objects.get(package__name=package['package'],
                                                                       version=package['version'])
                        DockerImageVersionContents.objects.create(image_version=image_version,
                                                                  package_revision=package_revision)
                    except:
                        continue
                return Response("SUCCESS", status=status.HTTP_201_CREATED)
            except:
                return Response("Failed to store data", status=status.HTTP_400_BAD_REQUEST)

        return Response("Parsing error with JSON params", status=status.HTTP_400_BAD_REQUEST)

    @list_route(url_path='contents')
    def get_image_version_contents(self, request):
        """
        This is a custom route on the ViewSet which can be reached by appending "contents" to the default URL
        It takes 2 variables - image_name and image_version and filters the query on these
        @param request: json input from the rest endpoint - used to access query params
        @return: Response object with either a success status or failure
        """
        def get_queryset():
            queryset = self.queryset
            image_name = request.query_params.get('image_name', None)
            image_version = request.query_params.get('image_version', None)
            if image_name and image_version is not None:
                queryset = queryset.filter(image_version__image__name=image_name, image_version__version=image_version)
                return queryset
            return None
        if get_queryset() is not None:
            serializer = self.serializer_class(get_queryset(), many=True)
            if serializer.data:
                return Response(serializer.data, status=status.HTTP_200_OK)
        return Response("No contents available for given image version", status=status.HTTP_400_BAD_REQUEST)
