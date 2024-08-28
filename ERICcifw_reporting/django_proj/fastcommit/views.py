from .models import *
from django.shortcuts import render
from fwk.utils import pageHitCounter
from django.views.decorators.gzip import gzip_page
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ciconfig import CIConfig
config = CIConfig()
from django.http import HttpResponse
from collections import defaultdict

def display_docker_images(request):
    pageHitCounter("DockerImages", None, str(request.user))
    images = DockerImage.objects.all()
    return render(request, "fastcommit/dockerImages.html", {'images': images})

@gzip_page
def display_docker_image_versions(request, imageName):
    if imageName is not None:
        requiredDockerImageFields = ('id',)
        imageId = DockerImage.objects.filter(name=imageName).only(requiredDockerImageFields).values(*requiredDockerImageFields)[0]['id']

        imageVersionsCount = DockerImageVersion.objects.filter(image_id=imageId).count()

        requiredDockerImageVersionFields = ('id',)
        imageVersions = DockerImageVersion.objects.filter(image_id=imageId).order_by('-id').only(requiredDockerImageVersionFields).values(*requiredDockerImageVersionFields)

        objectsPerPage = 10
        paginator = Paginator(imageVersions, objectsPerPage)
        page = request.GET.get('page')
        if (page == "all"):
            imageVersionsPaginated = imageVersions
        else:
            try:
                imageVersionsPaginated = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                page = 1
                imageVersionsPaginated = paginator.page(page)
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                page = paginator.num_pages
                imageVersionsPaginated = paginator.page(page)

        imageVersionIds = []
        for imageVersion in imageVersionsPaginated:
            imageVersionIds.append(imageVersion['id'])

        requiredDockerImageVersionContentsFields = ('image_version_id', 'package_revision__package__name', 'package_revision__version', 'package_revision__date_created', 'image_version__version')
        imageContents = DockerImageVersionContents.objects.filter(image_version_id__in=imageVersionIds).prefetch_related('package_revision__package', 'image_version').only(requiredDockerImageVersionContentsFields).values(*requiredDockerImageVersionContentsFields)

        imageVersionsAndContentsDict = defaultdict(list)
        for imageContent in imageContents:
            imageVersionsAndContentsDict[imageContent['image_version_id']].append(imageContent)

        imageVersionsAndContents = []
        for imageVersionId in imageVersionIds:
            imageVersionsAndContents.append(imageVersionsAndContentsDict[imageVersionId])

        return render(request, "fastcommit/dockerImageVersions.html",
                      {
                          'imageVersions': imageVersionsPaginated,
                          'imageVersionsAndContents': imageVersionsAndContents,
                          'imageName': imageName,
                          'imageVersionsCount': imageVersionsCount
                      })
