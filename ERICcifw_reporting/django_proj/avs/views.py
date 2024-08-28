from django.shortcuts import render_to_response
from django.shortcuts import render
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext

from django.db.models import Max, Min
from django import forms
from avs.models import *
from django.core.servers.basehttp import FileWrapper
import logging, os, tempfile, re
import avs.avs_utils
import avs.skelgen

logger = logging.getLogger(__name__)

def avs_index(request):
    return render(request, "avs/index.html")

@login_required
def avs_import(request):
    form = UploadFileForm()
    return render(request, "avs/import.html", {'form': form, 'user': request.user})

class UploadFileForm(forms.Form):
    file = forms.FileField()

class SearchAvsForm(forms.Form):
    try:
        epic = forms.ModelChoiceField(Epic.objects.all())
        
    except Epic.DoesNotExist:
        logger.error("Epic does not exist")

def getEpics(request):
    epics = Epic.objects.all()
    return render(request, "avs/epics.html", {'epics': epics})

def getStories(request, epicName=None):
    epicObj = None
    if epicName is not None:
        epicObj = Epic.objects.get(name=epicName)
        stories = UserStory.objects.filter(epic=epicObj).order_by('-name')
    else:
        stories = UserStory.objects.all().order_by('-name')
    slist = {}
    for s in stories:
        if not s.name in slist:
            slist[s.name] = s
        elif slist[s.name].version < s.version:
            slist[s.name] = s
    return render(request, "avs/userstories.html", {'epic': epicObj, 'stories': slist})

def getStory(request, storyName):
    us = UserStory.objects.filter(name=storyName).latest('version')
    logger.info("Getting TCs for story " + str(us) + " ver " + str(us.version))
    tcData = {}
    tcList = TestCaseUserStoryMapping.objects.filter(user_story=us).filter(test_case__archived='0')
    #testCaseObject = TestCase.objects.filter(testcase=tc)
    logger.info("TCList : %s",tcList)
    for testcaseOb in tcList:
        logger.info("Got " + str(testcaseOb.user_story) + " - ver " + str(testcaseOb.user_story.version) + " --> " + str(testcaseOb.test_case))
        apData = {}
        for ap in ActionPoint.objects.filter(testCase=testcaseOb.test_case):
            apData[ap] = VerificationPoint.objects.filter(actionPoint=ap)
        tc = testcaseOb.test_case
        tcData[tc] = apData
    usData = {us: tcData}
    return render(request, "avs/userstory2.html", {"usData": usData})

def getStorySkeleton(request, story, fileType):
    logger.debug("Generating skeleton of type " + fileType + " for story " + story)
    data = avs.skelgen.generateSkeleton(story, fileType)
    response = HttpResponse(data, content_type='application/txt')
    response['Content-Disposition'] = 'attachment; filename=' + story + "." + fileType
    return response

def listFiles(request):
    files = AVSFile.objects.all().order_by('-dateCreated')
    return render(request, "avs/files.html", {'files': files})

def getFile(request, fileid):
    f = AVSFile.objects.get(id=fileid)
    data = f.fileContent

    # handle files written the old way for now
    if data.startswith(r"['"):
        data = data.replace(r"['", "", 1).replace(r"\n', '", "\n").replace(r"\n']", "\n")
    dateCreated = str(f.dateCreated).replace(r" ", "_")    

    response = HttpResponse(data, content_type='application/txt')
    response['Content-Disposition'] = 'attachment; filename=' + f.owner +"-" + str(dateCreated) + ".mm"
    return response

@login_required
def avs_search(request):
    form = SearchAvsForm()
    return render(request, "avs/search.html", {'form': form})

def avs_search_submit(request):
    if request.method == 'POST':
        form = SearchAvsForm(request.POST)
        if form.is_valid():
            epic = form.cleaned_data['epic']
            result = avs.avs_utils.findAVSbyEpic(epic)
            userStoryList = result[0]
            testCaseList = result[1]
            return render(request, "avs/search_result.html",
                    {
                        'epic':epic,
                        'result': result,
                        'userStoryList': userStoryList,
                        'testCaseList':testCaseList
                    })
    else:
        form = UploadFileForm()
    return HttpResponseRedirect('/avs/avs_search/')


@login_required
def avs_submit(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            user = str(request.user)
            # story = str(request.)
            result = handle_uploaded_file(request.FILES['file'], user)
            logger.info('Result from MMParser %s' %result)
            #logger.info('Error = %s' %result['error'])
            if result['errors'] == 0:
                return HttpResponseRedirect('/avs/stories/' + result['userStory'].name)
            else:
                return render(request, "avs/import_failure.html", result)
    else:
        form = UploadFileForm()
    return HttpResponseRedirect('/avs/avs_import_failure/')

def handle_uploaded_file(f, user):
    tmpdir = tempfile.mkdtemp()
    tmpfile = tmpdir + "/avs.mm"
    with open(tmpfile, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    result = avs.avs_utils.importAvs(tmpfile, user)
    return result

def avs_import_success(request):
    return render(request, "avs/import_success.html")

def avs_import_failure(request):
    return render(request, "avs/import_failure.html")

def avs_view_skeleton(request,fileName):
    """                                                                         
    Send a file through Django without loading the whole file into              
    memory at once. The FileWrapper will turn the file object into an           
    iterator for chunks of 8KB.                                                 
    """
    try:
        viewFilename = '/tmp/%s' %fileName # Select your file here.                                
        wrapper = FileWrapper(file(viewFilename))
        response = HttpResponse(wrapper, content_type='text/plain')
        response['Content-Length'] = os.path.getsize(viewFilename)
        return response
    except Exception, error:
        raise Http404
    

def avs_download_skeleton(request,fileName):
    try:
        downloadFilename = '/tmp/%s' %fileName # Select your file here.  
        data = open(downloadFilename,'r').read()
        #django.http.
        resp = HttpResponse(data, mimetype='application/x-download')
        resp['Content-Disposition'] = 'attachment;filename=%s' %fileName
        return resp
    except Exception, error:
        raise Http404
 
def avs_rest(request):  
    try:  
        logger.info('In avs_rest in views.py')
        testCase        = request.GET.get('testCase')
        testResult      = request.GET.get('testResult')
        testDuration    = request.GET.get('testDuration')
        testStart       = request.GET.get('testStart')
        testFinish      = request.GET.get('testFinish')
        testFailString  = request.GET.get('testFailString')
        logger.info('Updating test results for TestCase: %s' %testCase)       
        testCaseToUpdate = TestCase.objects.get(tcId=testCase)
        newTestResult = TestResult.objects.create(testCase=testCaseToUpdate,
            testResult      = testResult,
            testDuration    = testDuration,
            testStart       = testStart,
            testFinish      = testFinish,
            testFailString  = testFailString)
    except Exception, error:
        raise Http404
    return HttpResponse(status=201)

