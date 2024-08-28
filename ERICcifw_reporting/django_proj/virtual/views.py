from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt, csrf_protect
import logging
logger = logging.getLogger(__name__)
import virtual.utils
import cireports.utils
from cireports.models import *
import json
from ciconfig import CIConfig
config = CIConfig()




@csrf_exempt
def createRepo(request):
    try:
        productName = request.POST.get('product',None)
        dropName = request.POST.get('drop',None)
        addArtifacts = request.POST.get('addArtifacts',None)
        baseIsoName=request.POST.get('baseIsoName',None)
        baseIsoVersion=request.POST.get('baseIsoVersion',None)
        useLatestInfra=request.POST.get('useLatestInfra',False)
        useLatestApp=request.POST.get('useLatestApp',False)
        useLatestPassedIso=request.POST.get('useLatestPassedIso',False)
        repoNameOnly = request.POST.get('repoNameOnly',False)
        useMediaContent = request.POST.get('useMediaContent',False)

        if not useMediaContent:
            if dropName is None or not dropName or dropName == "None":
                logger.error("ERROR drop required.\n")
                return HttpResponse("ERROR drop required.\n")
            if "latest" in dropName:
                if Product.objects.filter(name=productName).exists():
                    product = Product.objects.get(name=productName)
                    [latest, track] = str(dropName).split(".", 1)
                    try:
                        release = Release.objects.get(track=track, product_id=product.id)
                    except:
                        logger.error("error : unable to get Track " + str(track) + " in Product " + str(product) )
                        return "error : unable to get Track " + str(track) + " in Product " + str(product)
                    try:
                        [product,dropName] = cireports.utils.getLatestDropName(release, product).split(":", 1)
                    except:
                        logger.error("error : unable to get latest drop using Track: " + str(track))
                        return "error : unable to get latest drop using Track: " + str(track)

        if productName is None or not productName or productName == "None":
            logger.error("ERROR Product required.\n")
            return HttpResponse("ERROR Product required.\n")

        if useLatestPassedIso:
            baseIsoName, baseIsoVersion = cireports.utils.getLatestIso(productName,dropName,None,True)

        if useLatestApp or useLatestInfra:
            if baseIsoName == "None" or baseIsoName == None or baseIsoVersion == "None" or baseIsoVersion == None:
                logger.info("No base ISO defined, using latest drop contents")
                excludeFromDrop = None
            else:
                ISOObj = ISObuild.objects.get(version=baseIsoVersion, mediaArtifact__name=baseIsoName)
                # if useLatestInfra => exclude infra from iso and exclude app from drop
                if useLatestInfra:
                    excludeFromIso = 'infra'
                    excludeFromDrop = 'app'
                if useLatestApp:
                    excludeFromIso = 'app'
                    excludeFromDrop = 'infra'
                modifiedIsoContent = cireports.utils.isoContents(ISOObj,productName,False,excludeFromIso)
                if modifiedIsoContent == [{"error":"error"}]:
                    logger.error("Issue with getting contents "+str(e))
                    ret = json.dumps([{"error":"error"}])
                    return HttpResponse(ret, content_type="application/json")
        else:
            excludeFromDrop = None

        if addArtifacts:
            if addArtifacts == "" or addArtifacts.lower() == "none" or addArtifacts == " ":
                addArtifacts = None

        isoObj = None
        if useMediaContent:
            isoObj = ISObuild.objects.get(version=baseIsoVersion, mediaArtifact__name=baseIsoName)
            dropName = isoObj.drop.name
            repoContents = cireports.utils.isoContents(isoObj,productName,False)
        else:
            repoContents =  cireports.utils.dropContents(productName,dropName,False,True,'testware',False,excludeFromDrop)
            if not excludeFromDrop == None:
                repoContents = repoContents+modifiedIsoContent

        repoDir = virtual.utils.createDynamicRepo(repoContents,addArtifacts,dropName,productName,isoObj)
        if repoNameOnly:
            result = repoDir
        else:
            repoBase = config.get("VIRTUAL", "repoBase")
            result = repoBase + repoDir
    except Exception as e:
        result = "ERROR creating repo "+str(e)
    return HttpResponse(result, content_type="text/plain")

@csrf_exempt
def deleteRepo(request):
    try:
        repo = request.POST.get('repo',None)
        if repo is None or not repo or repo == "None":
            logger.error("ERROR repo required.\n")
            return HttpResponse("ERROR repo required.\n")
        repo = repo.replace(' ','')
        if repo.endswith('/'):
            directory = repo.split('/')[-2]
        else:
            directory = repo.split('/')[-1]
        ret = virtual.utils.deleteDynamicRepo(directory)
    except Exception as e:
        ret = "ERROR deleting repo "+str(e)
    return HttpResponse(ret, content_type="text/plain")

@csrf_exempt
def restGetImageTemplates(request):
    if request.method == 'GET':
        templateType = request.GET.get('type')
        if not templateType:
            return HttpResponse("Error: type required as a rest call attribute type=tdl|kvm|customize|create\n")
        fileString = ""
        if "tdl" in templateType:
            repoBaseURL = config.get('IMAGECREATION', 'tdlTemplateFile')
        elif "kvm" in templateType:
            repoBaseURL = config.get('IMAGECREATION', 'kvmTemplateFile')
        elif "customize" in templateType:
            repoBaseURL = config.get('IMAGECREATION', 'customizeCommandsTemplate')
        elif "create" in templateType:
            repoBaseURL = config.get('IMAGECREATION', 'createCommandsTemplate')
        else:
            return HttpResponse("Error: type " +str(templateType)+ " is Unsupported")
        file = open(repoBaseURL, 'r')
        for line in file:
            fileString = fileString + line
    else:
        fileString="ERROR: only GET REST calls accepted"
    return HttpResponse(fileString, content_type="text/plain")

@csrf_exempt
def createAPTRepo(request):
    try:
        productName = request.POST.get('product',None)
        dropName = request.POST.get('drop',None)

        if dropName is None or not dropName or dropName == "None":
            logger.error("ERROR drop required.\n")
            return HttpResponse("ERROR drop required.\n")

        if productName is None or not productName or productName == "None":
            logger.error("ERROR Product required.\n")
            return HttpResponse("ERROR Product required.\n")
        if "latest" in dropName:
            if Product.objects.filter(name=productName).exists():
                product = Product.objects.get(name=productName)
                [latest, track] = str(dropName).split(".", 1)
                try:
                    release = Release.objects.get(track=track, product_id=product.id)
                except:
                    logger.error("error : unable to get Track " + str(track) + " in Product " + str(product) )
                    return "error : unable to get Track " + str(track) + " in Product " + str(product)
                try:
                    [product,dropName] = cireports.utils.getLatestDropName(release, product).split(":", 1)
                except:
                    logger.error("error : unable to get latest drop using Track: " + str(track))
                    return "error : unable to get latest drop using Track: " + str(track)

        repoContents =  cireports.utils.dropContents(productName,dropName,False,True,'testware',False,None)
        repoDir = virtual.utils.createDynamicAPTRepo(repoContents,dropName,productName)
        repoBase = config.get("VIRTUAL", "aptRepoBase")
        ret = repoBase + repoDir
    except Exception as e:
        ret = "ERROR creating repo "+str(e)
    return HttpResponse(ret, content_type="text/plain")
