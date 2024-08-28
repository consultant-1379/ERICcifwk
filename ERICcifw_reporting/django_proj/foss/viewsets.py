from django.http import Http404, HttpResponse, HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import repo_auditer
import requests
import logging
logger = logging.getLogger(__name__)

class SendForAuditing(APIView):
    '''
    This is POST REST call that sends repos to Bazaar for auditing
    '''
    def post(self, request, *args, **kwargs):
        try:
            user_name = self.kwargs['user_name']
            bazaar_token = self.kwargs['bazaar_token']
            bazaar_svl = self.kwargs['bazaar_svl']
            gerrit_repos = request.POST.get("gerrit_repos", None)

            result = repo_auditer(user_name, bazaar_token, bazaar_svl, gerrit_repos)

            if "Error:" in result:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(result, status=status.HTTP_200_OK)
        except Exception as error:
            err_msg = "Error: There was an issue with Auditing: " + str(error)
            logger.error(err_msg)
            return Response(err_msg, status=status.HTTP_404_NOT_FOUND)
