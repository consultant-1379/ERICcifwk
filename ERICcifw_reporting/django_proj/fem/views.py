from django.http import StreamingHttpResponse, HttpResponse, Http404, HttpResponseRedirect
from django.db.models import Sum
from datetime import datetime, timedelta
import ast
from cireports.models import *
from fem.forms import *
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, csrf_protect
import json
import re
import subprocess
import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()

import utils
from urllib import urlencode

from models import *
from os import listdir
import shutil
import time
import fem.utils


def jobStatus(request, view=None):
    jobName=request.GET.get('job')
    if jobName == "" or jobName == None:
        jobName = "ALL"
    if view is None:
        view = request.GET.get("view", config.get("FEM", "defaultView"))
    if view  == "DEFAULT":
        view = request.GET.get("view", config.get("FEM", "defaultView"))
    if view  == "ALL":
        jobInfo = utils.readDataFromURL("/")
    else:
        jobInfo = utils.readDataFromURL("/view/" + view + "/")

    jobRes = [
              {"key": "Passed", "value": 0},
              {"key": "Unstable", "value": 0},
              {"key": "Failed", "value": 0},
              {"key": "Aborted", "value": 0},
             ]
    
    jobs = {}
    for job in jobInfo['jobs']:
        logger.debug("Job: " + job['name'] + " = " + job['color'])
        if jobName == "ALL" or jobName == job['name']:
            if job["color"] == "blue":
                jobRes[0]["value"] = jobRes[0]["value"] + 1
            elif job["color"] == "yellow":
                jobRes[1]["value"] = jobRes[1]["value"] + 1
            elif job["color"] == "red":
                jobRes[2]["value"] = jobRes[2]["value"] + 1
            elif job["color"] == "aborted":
                jobRes[3]["value"] = jobRes[3]["value"] + 1

    logger.debug("Results: " + str(jobRes))
    return HttpResponse(json.dumps(jobRes), content_type="application/json")

def jobStatusView(request, view=None):
    statusMap = ast.literal_eval(request.GET.get("view", config.get("FEM", "statusMap")))
       # statusMap = {
       #     "blue": "success",
       #     "red": "failed",
       #     "aborted": "aborted",
       #     "yellow": "unstable",
       #     "disabled": "disabled",
       #     "grey": "pending",
       #     "red_anime": "inprogress",
       #     "yellow_anime": "inprogress",
       #     "blue_anime": "inprogress",
       #     "grey_anime": "inprogress",
       #     "aborted_anime": "inprogress",
       # }
    if view  == "DEFAULT":
        view = request.GET.get("view", config.get("FEM", "defaultView"))
    if view  == "ALL":
        jobInfo = utils.readDataFromURL("/")
    else:
        jobInfo = utils.readDataFromURL("/view/" + view + "/")
    jobRes = [] 
    jobs = {}
    for job in jobInfo['jobs']:
        jobResTmp = [
                {
                    "status":  statusMap[job["color"]],
                    "name": job["name"],
                },
                ]
        jobRes = jobRes + jobResTmp

    logger.debug("Results: " + str(jobRes))
    return HttpResponse(json.dumps(jobRes), content_type="application/json")

def getFailingJobs(request, view=None):
    jobName=request.GET.get('job')
    if jobName == "" or jobName == None:
        jobName = "ALL"

    if view is None:
        # URL, then GET, then config is the precedence
        view = request.GET.get("view", config.get("FEM", "defaultView"))
    return HttpResponse(json.dumps(utils.getFailingJobs(view,jobName)), content_type="application/json")

def getJobTrend(request, job=None):
    '''
    this view returns hourly, daily or weekly trend for a job or view
    TODO: decide if we need to use GET or the actual URL to get the view or
    job info. Preference is to use the URL to get the Job or view and the
    GET parameters for variables such as start and end.

    http://cifwk-oss/fem/view/(viewName)/trend/json
    http://cifwk-oss/fem/job/(jobName)/trend/json

    need to update urls.py and client code if URLs are changed.
    '''
    start = request.GET.get('start', "")
    end = request.GET.get('end', "")
    job = request.GET.get('job', job)
    if job == "":
        job = None
    view = request.GET.get('view', "")
    if view == "":
        view = None
    # Default Granularity set to show days
    granularity = request.GET.get('g', "day")

    return HttpResponse(json.dumps(utils.getJobTrend(job, view, granularity, start, end)), content_type="application/json")

def returnViews(request):
    #returns views with information and url to more detailed info on view
    current_site = request.get_host() 
    if request.is_secure():
        scheme = 'https://'
    else:
        scheme = 'http://'
    try:
        datav = utils.readDataFromURL("", depth=0)
    except Exception as e:
        logger.error("Problem reading from root jenking api" )
        return
    jsonReturn = []
    for viewNameDict in datav['views']:
        viewName = viewNameDict['name']
        viewName = re.sub(r"\s+", '%20', viewName)
        if viewName is not None:
            jsonTmp = {
            "name": viewName,
            "url":scheme+current_site+"/fem/views/"+viewName+"/api/json",
                }
            jsonReturn.append(jsonTmp)
    return HttpResponse(json.dumps(jsonReturn), content_type="application/json")

def returnViewDetail(request, view=None):
    #returns view with information and url to jobs/trend data etc. 
    view = re.sub(r"\s+", '%20', view)
    current_site = request.get_host()
    if request.is_secure():
        scheme = 'https://'
    else:
        scheme = 'http://'
    try:
        viewInfo = utils.readDataFromURL("/view/" + view + "/")
    except Exception as e:
        logger.error("Problem reading from jenking api" )
        return
    jsonReturn = [{
                "name" : view,
                "desc" : viewInfo['description'],    
                "jobStatusURL" : scheme+current_site+"/fem/jobStatus/view/"+view+"/api/json",
                "jobTrendURL" : scheme+current_site+"/fem/jobTrend/?view="+view,
                "failingJobsURL" : scheme+current_site+"/fem/failedJobs2/view/"+view+"/api/json",
                }]
    return HttpResponse(json.dumps(jsonReturn), content_type="application/json")

def getJobTrend2(request, job=None):
    '''
    this view returns hourly, daily or weekly trend for a job or view
    TODO: decide if we need to use GET or the actual URL to get the view or
    job info. Preference is to use the URL to get the Job or view and the
    GET parameters for variables such as start and end.

    http://cifwk-oss/fem/view/(viewName)/trend/json
    http://cifwk-oss/fem/job/(jobName)/trend/json

    need to update urls.py and client code if URLs are changed.
    '''
    start = request.GET.get('start', "")
    end = request.GET.get('end', "")
    job = request.GET.get('job', job)
    if job == "":
        job = None
    view = request.GET.get('view', "")
    if view == "":
        view = None
    # Default Granularity set to show days
    granularity = request.GET.get('g', "day")

    return HttpResponse(json.dumps(
                            utils.getJobTrend2(job, view, granularity, start, end),
                            sort_keys=True, indent=4, separators=(',', ': ')
                        ), content_type="application/json")

def femJob(request): 
    jobs=utils.getJobs()
    form = CreateFemJobForm(jobs) 
    return render(request,"fem/femjob.html",
                {
                    'form': form,
                })

def createFemJob(request):
    jobName = request.POST.get('jobname')
    username = request.POST.get('username')
    password = request.POST.get('password')
    jobs = request.POST.getlist('jobs',None)
    server = request.POST.get('server')
    buildBranch = request.POST.get('buildbranch')
    pushBranch = request.POST.get('pushbranch')
    repo = request.POST.get('repo')
    enable = request.POST.get('enable','no')
    node = request.POST.get('node')
    if enable == 'yes':
        enable = True
    now = default=datetime.now()
    timeStamp = now.strftime("%Y_%m_%d-%H_%M_%S")
    config = CIConfig()
    templateDir = config.get("FEM", "jobTemplates")
    results = utils.sendCreateJob(jobs,repo,server,jobName,username,password,enable,buildBranch,pushBranch,node) 
    return render(request,"fem/femjobresult.html",
                {
                    'results': results,
                })


def getBuildStatus(request):
    '''
    This ReST method receives the variables necessary to select a specific build from jenkins.
    The build status, estimated build time and actual build time are returned.
    '''
    if request.method == 'POST':
        return HttpResponse("Error: This interface accepts HTTP GET requests only.\n")
    if request.method == 'GET':
        jobName = request.GET.get("jobName")
        jenkinsHost = request.GET.get('jenkinsHost')
        buildSelector = request.GET.get('buildSelector')
	timeout = int(request.GET.get('timeout'))

    if jenkinsHost is None or not jenkinsHost or jenkinsHost == "None":
        return HttpResponse("Error: Jenkins Host machine required.\n")
    if jobName is None or not jobName or jobName == "None":
        return HttpResponse("Error: Job name required.\n")
    if buildSelector is None or not buildSelector or buildSelector == "None":
        return HttpResponse("Error: Build selector required.\n")
    if timeout is None or not timeout or timeout == "None":
        return HttpResponse("Error: Timeout required.\n")

    try:
	return HttpResponse(utils.getBuildStatus(jenkinsHost, jobName, buildSelector, timeout))
    except Exception as e:
        return HttpResponse(str(e))

@csrf_exempt
def getPreviousEventIDs(request):
    if request.method == 'POST':
        return HttpResponse("Sorry this REST only supports GET REST calls")
    if request.method == 'GET':
        result = "ISOBUILD_PREVIOUS_ANE_ID= \nISOBUILD_PREVIOUS_BDE_ID=\n"
        groupId = request.GET.get('groupId')
        artifactId = request.GET.get('artifactId')
        version = request.GET.get('version')
        if groupId is None or not groupId or groupId == "None":
            return HttpResponse("Error: groupId is required, please try again.\n")
        if artifactId is None or not artifactId or artifactId == "None":
            return HttpResponse("Error: artifactId is required, please try again.\n")
        if version is None or not version or version == "None":
            return HttpResponse("Error: version is required, please try again.\n")
    try:
        result = fem.utils.getPreviousArtifactNewEvent(groupId, artifactId, version)
    except Exception as error:
        message = "Error: There was an issue building the previous baseline defined event or previous artifact new event: " +str(error)
        logger.error(message)
    return HttpResponse(result, content_type="text/plain") 
