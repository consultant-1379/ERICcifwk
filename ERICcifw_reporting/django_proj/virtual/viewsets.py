from rest_framework import generics, permissions,status
from django.utils.decorators import method_decorator
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
import virtual.utils
from django.db import transaction, IntegrityError
from datetime import datetime
from rest_framework.renderers import JSONRenderer
import requests


logger = logging.getLogger(__name__)

class createRHELPatchSetYumRepo(APIView):
    '''
    Create RHEL Patch Set Yum Repo
    '''
    def post(self, request, *args, **kwargs):
        try:
            if 'artifact' not in self.kwargs:
                return Response({'error': 'artifact is required.'}, status=status.HTTP_412_PRECONDITION_FAILED)
            else:
                artifact = self.kwargs['artifact']
            if 'artifactVersion' not in self.kwargs:
                return Response({'error': 'artifactVersion is required.'}, status=status.HTTP_412_PRECONDITION_FAILED)
            else:
                artifactVersion = self.kwargs['artifactVersion']
            if 'patchVersion' not in self.kwargs:
                patchVersion = None
            else:
                patchVersion = self.kwargs['patchVersion']
            try:
                rhelVersion = self.kwargs['rhelVersion']
            except:
                rhelVersion = None
            result, statusCode = virtual.utils.createPatchSetRepo(artifact, artifactVersion, patchVersion, rhelVersion)
            if statusCode == 201:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response({'error':result},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            errMsg = "Unable create RHEL Patch Set YumRepo: "+str(e)
            logger.error(errMsg)
            return Response({'error':errMsg}, status=status.HTTP_404_NOT_FOUND)

class createYumRepoLatestPath(APIView):
    '''
    Create Latest YumRepo Path
    '''
    def post(self, request, *args, **kwargs):
        try:
            if 'yumRepo' not in self.kwargs:
                return Response({'error': 'yumRepo is required.'}, status=status.HTTP_412_PRECONDITION_FAILED)
            else:
                yumRepo = self.kwargs['yumRepo']
            if 'product' not in self.kwargs:
                return Response({'error': 'product is required.'}, status=status.HTTP_412_PRECONDITION_FAILED)
            else:
                productName = self.kwargs['product']

            result, statusCode = virtual.utils.createLatestYumRepoPath(yumRepo, productName)
            if statusCode == 201:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result,status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            errMsg = "Unable create YumRepo Latest Path: "+str(e)
            logger.error(errMsg)
            return Response({'error':errMsg}, status=status.HTTP_404_NOT_FOUND)
