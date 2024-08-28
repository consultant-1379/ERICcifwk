from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render
from fwk.utils import pageHitCounter
from .utils import *
import logging
logger = logging.getLogger(__name__)


def audit_repos(request):
    '''
    This function renders the auditing html page
    '''
