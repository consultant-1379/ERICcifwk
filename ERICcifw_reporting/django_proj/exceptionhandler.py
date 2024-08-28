from rest_framework.views import exception_handler
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc,context)

    # Now add the HTTP status code to the response.
    if isinstance(exc, Http404) and str(exc):
        data = {'detail': str(exc)}

        return Response(data, status=status.HTTP_404_NOT_FOUND)

    return response
