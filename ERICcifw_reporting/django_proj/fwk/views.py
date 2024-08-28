from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django import forms
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from distutils.version import LooseVersion
import logging
logger = logging.getLogger(__name__)
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ciconfig import CIConfig
from cireports.models import *
from models import *
import utils
import cireports
import json
import os
import subprocess
import ast
from django.db import connection
from django.shortcuts import render
from fwk.forms import *
from cireports.utils import preRegisterENMArtifact
from django.contrib.auth.models import User

def displaySummary(request, team, rest=False):
    hostname = request.META['HTTP_HOST']
    try:
        grp = Team.objects.get(name=team)
        info = TvInfoMap.objects.filter(team=grp.id).order_by('-sequence')
    except TvInfoMap.DoesNotExist:
        raise Http404
    if (not rest):
        return render_to_response("fwk/summary.html", {'summary': info, 'team': team})
    else:
        return render_to_response("fwk/summary_urls.html", {'summary': info, 'team': team})
        # Commented out the below code until json consumption is implemented in the html pages
        #links = []
        #for i in info:
        #    links.append({"url": i.url.url, "time": i.time})
        #return HttpResponse(json.dumps(links), content_type="application/json")

def displayLinks(request, team):
    hostname = request.META['HTTP_HOST']
    try:
        grp = Team.objects.get(name=team)
        info = TvInfoMap.objects.filter(team=grp.id).order_by('-sequence')
    except TvInfoMap.DoesNotExist:
        raise Http404
    return render_to_response("fwk/links.html", {'tvinfo': info, 'team': team})

def displayTeams(request):
    hostname = request.META['HTTP_HOST']
    try:
        teams = Team.objects.all().order_by('name')
        v = utils.getCifwkVersion()
    except Team.DoesNotExist:
        raise Http404
    return render_to_response("fwk/tvlinks.html", {'teams': teams, 'version': v})

def displaySummaryUrls(request, team):
    return displaySummary(request, team, True)

@csrf_exempt
def upgrade(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            ver = form.cleaned_data['version']
            msg = utils.performUpgrade(ver)
            return render_to_response("fwk/success.html", {'selection': ver, 'message': msg})
    else:
        form = UploadForm()
    return HttpResponseRedirect('../../upgrade/')

def ugForm(request):
    form = UploadForm()
    return render_to_response("fwk/cifwk_ug.html", {'form': form})

@login_required
def registerDevelopmentServer(request):
    '''
    The registerDevelopmentServer requires logon and can be used to register a
    CIFWK developement server
    '''
    servers = CIFWKDevelopmentServer.objects.all()
    # Create a FormHandle to handle form post-processing
    fh = FormHandle()
    fh.form = DevelopmentServerForm()
    fh.title = "CIFWK Design Server Page"
    fh.request = request
    fh.button = "Register"

    if request.method == 'POST':
        fh.form = DevelopmentServerForm(request.POST)
        # validate the form so that the cleaned_data gets populated, then we can get the
        # requested name and define our redirect URL
        if fh.form.is_valid():
            try:
                fh.form.save()
                return render_to_response("fwk/designServers.html", {'servers': servers})
            except:
                return fh.failure()
        else:
            return fh.failure()
    else:
        return fh.display()

@login_required
def showDevelopmentServer(request, selected=None):
    '''
    The showDevelopmentServer function is called from the UI to display all the
    CIFWk design servers in the CIFWK Database
    '''
    servers = CIFWKDevelopmentServer.objects.all()
    return render_to_response("fwk/designServers.html", {"servers": servers})

@login_required
def updateDevelopmentServer(request, server, option):
    '''
    The updateDevelopmentServer function is used to populate the edit server form
    or delete a server
    '''
    if "edit" in option:
        serverObject = CIFWKDevelopmentServer.objects.get(vm_hostname=server)
        domainName = serverObject.domain_name
        ipAddress = serverObject.ipAddress
        user = serverObject.owner
        description = serverObject.description

        # Create a FormHandle to handle form post-processing
        fh = FormHandle()
        fh.title = "Update Server Form for: " +str(server)
        fh.form = DevelopmentServerForm(
                initial={
                    'vm_hostname':server,
                    'domain_name': domainName,
                    'ipAddress': ipAddress,
                    'owner': user,
                    'description': description})
        fh.request = request
        fh.button = "Update"

        if request.method == 'POST':
            fh.form = DevelopmentServerForm(request.POST)
            # validate the form so that the cleaned_data gets populated, then we can get the
            # requested name and define our redirect URL
            if fh.form.is_valid():
                # redirect to Management Servers page
                fh.redirectTarget = "/fwk/devServers/list/"
                try:
                    #Update the Model
                    serverObject.vm_hostname = fh.form.cleaned_data['vm_hostname']
                    serverObject.domain_name = fh.form.cleaned_data['domain_name']
                    serverObject.ipAddress = fh.form.cleaned_data['ipAddress']
                    serverObject.user = fh.form.cleaned_data['user']
                    serverObject.description = fh.form.cleaned_data['description']
                    serverObject.save(force_update=True)
                    #TODO: Investigate further why update cannot be completed .......
                    return fh.success()
                except:
                    return fh.failure()
            else:
                return fh.failure()
        else:
            return fh.display()
    elif "delete" in option:
        try:
            CIFWKDevelopmentServer.objects.filter(vm_hostname=server).delete()
            cursor = connection.cursor()
            status = "Server " +str(server)+ " deleted from database"
            logger.info(status)
        except Exception as e:
            raise CommandError("There was an issue deleting server " +str(server)+ " from database: " +str(e))
        return HttpResponseRedirect("/fwk/devServers/list/")

def getVer(request):
    ver = utils.getCifwkVersion()
    return HttpResponse(str(ver), content_type="text/plain")
def getLatestBuild(request):
    allVers = list(cireports.models.PackageRevision.objects.filter(package__name='ERICcifw_reporting'))
    allVers.sort(key=lambda drop:LooseVersion(drop.version), reverse=True)
    highestVerTmp = str(allVers[0])
    a,highestVer = highestVerTmp.split("-")
    return HttpResponse(str(highestVer), content_type="text/plain")

def showGlossaryItems(request):
    '''
    The showGlossaryItems fuction builds up the UI Glossary from items in the glossary tables in the DB
    '''
    utils.pageHitCounter("Glossary", None, str(request.user))
    dict = {}
    list = []
    glossaryObject = Glossary.objects.all()
    #Get upper case letters of alphabet
    alphabet = map(chr, range(65, 91))
    #Build up dict of dicts from glossary objects in list
    for glossary in glossaryObject:
        #Get First Letter of glossary Name and upper case it
        letter = glossary.name[0].upper()
        if letter in list:
            dict[letter][glossary.name] = glossary.description
        else:
            dict[letter] = {glossary.name:glossary.description}
            list.append(letter)
    #Build up rest of missing Alphabet letters for Glossary WebPage in a list
    for key,value in dict.items():
        if key in alphabet:
            alphabet.remove(key)
    for letter in alphabet:
        dict[letter] = {}
    #Order is not correct in dict so this needs to be sorted
    orderedDict = [ (item, dict[item]) for item in dict]
    tuple = sorted(orderedDict, key = lambda item: item[1])
    tuple.sort()
    #Render tuple to Portal UI Glossay html page
    return render(request, "fwk/glossary.html", {'tuple': tuple, })

def changeLog(request):
    utils.pageHitCounter("ChangeLog", None, str(request.user))
    return render_to_response("fwk/createChangeLog.html")

@csrf_exempt
def createCL(request):
    '''
    This function is called by REST to get the change log based on dates passed to it
    '''
    changes = []
    developmentServer = ast.literal_eval(config.get("CIFWK", "testServer"))
    baseDir = utils.getCIFwkBase() + "/"
    cifwkVer = utils.getCifwkVersion()

    if request.method == 'GET':
        startDate = str(request.GET.get('from')).upper()
        endDate = str(request.GET.get('until')).upper()

    if developmentServer == 1:
        cmd = baseDir + "ERICcifwk/ERICcifw_reporting/bin/create-changelog -d no -u emarfah -s'" + startDate + "' -e '" + endDate + "'"
    else:
        cmd = baseDir + cifwkVer + "/bin/create-changelog -d no -u emarfah -s'" + startDate + "' -e '" + endDate + "'"

    process = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
    (output, error) = process.communicate()

    file = str(output).splitlines()[-1]
    changeLog = open(file,'r')
    try:
        for line in changeLog:
            changes.append(str(line))
    except Exception as e:
        logger.error("ERROR: "+str(e))

    return render(request, "fwk/changeLog.html", { 'changelog':changes, })

def showTickerTapeHistory(request):
    '''
    The showTickerTapeHistory function will display all messages
    '''
    utils.pageHitCounter("TickerTapeHistory", None, str(request.user))
    historyObject = None
    severitiesList = set()
    if request.method == 'GET':
       historyObject = TickerTape.objects.all().order_by('-created')
    if request.method == 'POST':
       startDate = request.POST.get('start')
       endDate = request.POST.get('end')
       if (startDate == None or startDate == "" ) or (endDate == None or endDate == ""):
           historyObject = TickerTape.objects.all().order_by('-created')
       elif startDate == endDate:
           historyObject = TickerTape.objects.filter(created__startswith=startDate).order_by('-created')
       else:
           historyObject = TickerTape.objects.filter(created__range=[startDate, endDate]).order_by('-created')
    if historyObject:
        for histObj in historyObject:
            severitiesList.add(histObj.severity)
    severities = TickerTapeSeverity.objects.all().order_by('id')
    return render(request, "fwk/tickerTapeHistory.html", {'history': historyObject,
                                                          'severities': severities,
                                                          'severitiesList': severitiesList})

def preRegisterArtifact(request):
    '''
    This function will make a POST REST call to register the artifacts to be delivered to ENM
    by adding them in th ci portal db
    '''

    cmAdminGroup = config.get("CIFWK", "cmadmingroup")
    user = User.objects.get(username=str(request.user))
    if not user.groups.filter(name=cmAdminGroup).exists():
        return render(request, "dmt/dmt_error.html",{'error': 'No Permissions to Register.'})

    fh = FormHandle()
    fh.title = "Pre Register Artifact"
    fh.docLink = "/display/CIOSS/Framework#Framework-PreRegisterArtifact"
    fh.request = request
    fh.message = "Provide information for the new artifact"
    fh.form = PreRegisterArtifactForm()

    if request.method == "GET":
        utils.pageHitCounter("PreRegisterArtifact", None, str(request.user))
        return fh.display()

    if request.method == 'POST':
        packageName = request.POST.get('packageName')
        packageNumber = request.POST.get('packageNumber')
        mediaCategory = request.POST.get('mediaCategory')
        signum = str(request.user)

        if packageName is None or not packageName or packageName == "None":
            return render(request, "fwk/registerartifact_error.html",{'error': 'Error: Package Name required, please try again'})
        if packageNumber is None or not packageNumber or packageNumber == "None":
            return render(request, "fwk/registerartifact_error.html",{'error': 'Error: Package Number required, please try again'})
        if mediaCategory is None or not mediaCategory or mediaCategory == "None":
            return render(request, "fwk/registerartifact_error.html",{'error': 'Error: Media Category required, please try again'})

    return render(request, "fwk/registerartifact_error.html",{'error': preRegisterENMArtifact('ENM', packageName, packageNumber, signum, mediaCategory)})
