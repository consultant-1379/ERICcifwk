from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponseRedirect
from urllib import urlencode
from distutils.version import LooseVersion
from datetime import datetime, timedelta
from django.shortcuts import render

#from vis.models import *
from cireports.models import *
import logging
import json
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()
import json

import fem.utils

def jobStatus(request):
    jobInfo = fem.utils.readDataFromURL("/view/TOR/")
    jobRes = {
        "success": 0,
        "failed": 0,
        "disabled": 0,
        "unstable": 0,
    }
    jobs = {}
    for job in jobInfo['jobs']:
        if job["color"] == "blue":
            jobRes["success"] = jobRes["success"] + 1
        elif job["color"] == "red" or job["color"] == "aborted":
            jobRes["failed"] = jobRes["failed"] + 1
        elif job["color"] == "yellow":
            jobRes["unstable"] = jobRes["unstable"] + 1
        elif job["color"] == "disabled":
            jobRes["disabled"] = jobRes["disabled"] + 1

    logger.debug("Results: " + str(jobRes))
    return HttpResponse(json.dumps(jobRes), content_type="application/json")

def nextDrop(request):
    drop = Drop.objects.filter(actual_release_date__gt=datetime.now())[0]
    dropData = {
        "releasedate": drop.actual_release_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "name": drop.name,
        "release": str(drop.release),
    }
    return HttpResponse(json.dumps(dropData), content_type="application/json")


def radiator(request, view=None, drop=None):
    if drop is None:
        allDrops = list(Drop.objects.all())
        allDrops.sort(key=lambda drop:LooseVersion(drop.name), reverse=True)
        drop = allDrops[0]
    drop = Drop.objects.get(name=drop)
    if view is None:
        view = "TOR"
    start = request.GET.get('start', "")
    end = request.GET.get('end', "")
    granularity=request.GET.get('g', "day")

    return render(request, "cireports/radiator_base.html", {
        "nextdrop": drop.name,
        "view": view,
        "start": start,
        "end": end,
        "granularity": granularity,
        "widgets": ["trend_data", "failed_jobs"]}
    )

def radiatorCustomView(request, view=None):
    allDrops = list(Drop.objects.all())
    allDrops.sort(key=lambda drop:LooseVersion(drop.name), reverse=True)
    drop = allDrops[0]
    drop = Drop.objects.get(name=drop)

    return render(request, "cireports/radiator_base_custom.html", {
        "nextdrop": drop.name,
        "view": view,
        "start": start,
        "end": end,
        "granularity": granularity,
        "widgets": ["trend_data", "failed_jobs"]}
    )

def radiatorCustomViewJson(request, customView=None):
    allDrops = list(Drop.objects.all())
    allDrops.sort(key=lambda drop:LooseVersion(drop.name), reverse=True)
    drop = allDrops[0]
    drop = Drop.objects.get(name=drop)
    print customView
    data = WidgetDefinitionToRenderMapping.objects.filter(widgetRender__name=customView)
    jsonReturn = {}
    for widgets in data:
        print widgets.widgetDefinition.widget.type
    return HttpResponse(json.dumps(jsonReturn), content_type="application/json")

