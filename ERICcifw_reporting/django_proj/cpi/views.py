from distutils.version import LooseVersion
from django.http import HttpResponse
from django.core.management import call_command
from StringIO import StringIO
from django.shortcuts import render_to_response,render
from django.http import HttpResponse, Http404, HttpResponseRedirect,StreamingHttpResponse
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django import forms
from django.core.mail import send_mail,EmailMessage
from ciconfig import CIConfig
import json
import datetime
import ast,re,xlrd,xlwt
from xlwt import *
import os
from cireports.models import *
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
now = datetime.now()
from django.contrib.auth.models import User
from re import search
from cpi import utils
from cpi.forms import *
from cpi.models import *
from django.core.files import File 
import cpi
from requests import Request, Session
from mptt.forms import TreeNodeChoiceField
session = requests.Session()
proxy = {
  "http": "",
  "https": "",
}
config = CIConfig()
cpiLibPath = config.get("CPI", 'cpiLibPath')
cpiSdiPath = config.get("CPI",'cpiSdiPath')
cpiGaskUrl = config.get("CPI",'gaskUrl')
cookieVal = config.get("CPI",'cookieVal')
cookieVal=ast.literal_eval(config.get("CPI",'cookieVal'))
buildUrl = config.get("CPI", 'buildUrl')
dwaxeUrl = config.get("CPI", 'dwaxeUrl')
workDir = config.get("CPI", 'workDir')
cookiePattern = config.get("CPI", 'cookiePattern')
data = ast.literal_eval(config.get("CPI",'data'))
authUrl = config.get("CPI",'authUrl')
authValues = ast.literal_eval(config.get("CPI",'authValues'))
confluenceUrl= config.get("CPI",'confluenceUrl')
alexLibUrl= config.get("CPI",'alexLibUrl')
calStoreUrl= config.get("CPI",'calStoreUrl')
cpiStoreUrl= config.get("CPI",'cpiStoreUrl')

def displayCPIBuilds(request,product,version):

    '''
    Lists the available CPIBuilds for the specified drop
    '''

    try:
        identity=CPIIdentity.objects.filter(drop__name=version,drop__release__product__name=product).order_by('-id')
        product = Product.objects.get(name=product)
        return render(request,"cpi/cpiBuilds.html",
                {
                    'version': version,
                    'product': product,
                    'shipment':identity,
                    'confluenceUrl':confluenceUrl,
                    
                })
    except Exception as e:
        logger.error("Issue with Document Web Page: " +str(e))
        return HttpResponse("There was an issue displaying CPI builds: " + str(product) + " version: " +str(version)+ " Error thrown: " +str(e))
        return 1

def displayCPIDocuments(request, product, version,cpiDrop):

    '''
    Lists the CPI Documents associated with specified drop and CPIDrop
    The documents will be carry forwarded from previous drop 
    Fresh library will be started for each track
    '''

    try:
        if not "Procus" in product:
            docObjList = cpi.utils.getCPIDocuments(version,product,cpiDrop)
        else:
            docObjList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__cpiDrop=cpiDrop)
        section=utils.getCPISection(product,docObjList)
        product = Product.objects.get(name=product)
        identity = CPIIdentity.objects.get(drop__name=version,cpiDrop=cpiDrop,drop__release__product__name=product)
        libName = cpi.utils.getLibName(product,version,cpiDrop)
        if identity.status == "In Progress":
            call_command("cpistatus",product=str(product),drop=str(version),cpiDrop=str(cpiDrop),userName=str(request.session['userid']),password=str(request.session['password']))
        if identity.status != "In Progress":
            if os.path.isfile(cpiLibPath + libName+".html"):
                os.remove(cpiLibPath + libName+".html")
        if identity.status == "Completed":
            identity.status="Passed"
            identity.save()
        elif identity.status == "Error":
            identity.status="Failed"
            identity.save()
        elif identity.status == "Abort":
            identity.status="Aborted"
            identity.save()
        logUser=User.objects.get(username=str(request.user))
        if logUser.groups.filter(name="CPI Build Admin").count():
            admin = "yes"
        else:
            admin = "no"
        if logUser.groups.filter(name="Eniq CPI Build").count():
            eniqAdmin = "yes"
        else:
            eniqAdmin = "no"
        cpiResp = identity.owner
        logUrl = "http://" + str(dwaxeUrl) + "action=FullLog&workdir=" + str(workDir) + str(cpiResp).lower()+ "/" + str(libName) + "&log="+libName+"_log.sgml&previousBarPercent=0"
        libraryURL = str(alexLibUrl) + libName + ".alx"
        calStore = str(calStoreUrl) + str(libName) + ".alx&command=directupload&libid=" + str(libName)
        cpiStore = str(cpiStoreUrl) + str(libName) + ".alx&command=directupload&libid=" + str(libName)
	fetchSdiUrl = "http://" + str(buildUrl) + "?requested_action=fetch_sdi&lwd="  + str(workDir) + str(cpiResp).lower()+ "/" + str(libName) + "&fetch_server_file=" + libName + ".alx&logged_in=1"
        return render(request,"cpi/cpiDocList.html",
            {
                'docObjList': docObjList,
                'nodes': section,
                'version': version,
                'product': product,
                'identity':identity,
                'confluenceUrl':confluenceUrl,
		'fetchSdiUrl':fetchSdiUrl,
                'libraryURL':libraryURL,
                'logUrl':logUrl,
                'eniqAdmin':eniqAdmin,
                'calStore': calStore,
                'cpiStore': cpiStore,
                'admin':admin,
            })
    except Exception as e:
        logger.error("Issue with Document Web Page: " +str(e))
        return HttpResponse("There was an issue displaying CPI documents: " + str(product) + " version: " +str(version)+ " Error thrown: " +str(e))
        return 1

@login_required
def displayCPIDocumentIndex(request, product, version,cpiDrop):

    '''
    Display the details of CPI Library
    '''
    emailMessage = str(product) + ' ' + str(version) + ' ' + str(cpiDrop)
    try:
        product = Product.objects.get(name=product)
        identity = CPIIdentity.objects.get(drop__name=version,cpiDrop=cpiDrop,drop__release__product__name=product)
        libName = cpi.utils.getLibName(product,version,cpiDrop)
        if 'userid' not in request.session:
            return HttpResponseRedirect('/' + str(product.name) + '/logindwaxe/' +str(version) + '/' + str(cpiDrop) + '/cpiDocs/')
        logdwaxe=checkDwaxeAccess(request,request.session['userid'],request.session['password'],product,cpiDrop,version)
        loggedin = 0
        loginSuccessPat = 'You have successfully logged into DWAXE'
        unknownUserPat = 'Unknown DWAXE user'
        wrongCredPat = 'You entered the wrong credentials'
        success = search(loginSuccessPat,logdwaxe.text)
        failure = search(unknownUserPat,logdwaxe.text)
        wrongCred = search(wrongCredPat,logdwaxe.text)
        if success:
            loggedin = 1
        elif failure:
            errormsg = 'You do not have access to run the build in Dwaxe. Please contact administrator to gain access.'
	    logger.error('User ' + str(request.session['userid']) + " has no access to dwaxe. Not refreshing the status")
        elif wrongCred:
            errormsg = 'You entered the Wrong Credentials.'
            return render(request,'cpi/dwaxeError.html',{'Error':errormsg,'product':str(product),'cpiDrop':str(cpiDrop),'version':version,'redirect':'cpiDocs',})
        else:
            errormsg = 'Something went wrong. Please contact administrator'
	    logger.error("Issue with login dwaxe. Not refreshing the status")
        if identity.status == "In Progress":
            if loggedin==1:
                call_command("cpistatus",product=str(product),drop=str(version),cpiDrop=str(cpiDrop),userName=str(request.session['userid']),password=str(request.session['password']))
        if identity.status != "In Progress":
            if os.path.isfile(cpiLibPath + libName+".html"):
                os.remove(cpiLibPath + libName+".html")
        if identity.status == "Completed":
            identity.status="Passed"
            identity.save()
        elif identity.status == "Error":
            identity.status="Failed"
            identity.save()
        elif identity.status == "Abort":
            identity.status="Aborted"
            identity.save()
        logUser=User.objects.get(username=str(request.user))
        if logUser.groups.filter(name="CPI Build Admin").count():
            admin = "yes"
        else:
            admin = "no"
        if logUser.groups.filter(name="Eniq CPI Build").count():
            eniqAdmin = "yes"
        else:
            eniqAdmin = "no"
        return render(request,"cpi/cpiDoc.html",
            {
                'version': version,
                'product': product,
                'identity':identity,
                'eniqAdmin':eniqAdmin,
                'admin':admin,
                'confluenceUrl':confluenceUrl,
            })
    except Exception as e:
        logger.error("Issue with Document Web Page: " +str(e))
        return HttpResponse("There was an issue displaying CPI documents: " + str(product) + " version: " +str(version)+ " Error thrown: " +str(e))
        return 1

def downloadSDI(request,product,version,cpiDrop):

    '''
    Download the Baseline in SDI format
    '''

    try:
        libName = cpi.utils.getLibName(product,version,cpiDrop)
        call_command('createsgm',product=str(product),drop=str(version),cpiDrop=str(cpiDrop),userName=str(request.user))
        sdiFile=open(cpiSdiPath + libName +'.sgm','r')
        myFile = File(sdiFile)
        fileName = libName + ".sgm"
        response = StreamingHttpResponse(myFile, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename=' + fileName
        return response
    except Exception as e:
        logger.error("Issue with Downloading SDI: " +str(e))
        return HttpResponse("There was an issue downloading CPI Baseline as SDI: " + str(product) + " version: " +str(version) + " Error thrown: " +str(e))
        return 1


def downloadExcel(request,product,version,cpiDrop):	

    '''
    Download the baseline in Excel format
    '''

    try:
        if not "Procus" in product:
            docObjList = cpi.utils.getCPIDocuments(version,product,cpiDrop)
        else:
            docObjList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__cpiDrop=cpiDrop)
        downloadExcel = cpi.utils.formatExcel(product,version,cpiDrop,docObjList)
        return downloadExcel
    except Exception as e:
        logger.error("Issue with Downloading Excel: " +str(e))
        return HttpResponse("There was an issue downloading CPI Baseline as Excel: " + str(product) + " version: " +str(version) + " Error thrown: " +str(e))
        return 1


def displayStatus(request,product,version,cpiDrop):

    '''
    Display the status of Library build from Dwaxe
    '''

    try:
        libName = cpi.utils.getLibName(product,version,cpiDrop)
        return render(request,libName+".html")
    except Exception as e:
        logger.error("Issue with displaying build status: " +str(e))
        return HttpResponse("There was an issue displaying CPI build status: " + str(product) + " version: " +str(version)+ " Error thrown: " +str(e))
        return 1

@login_required
def initiateCPIbuild(request,product,version,cpiDrop):

    '''
    Start the Library build in Dwaxe
    Shows progress if the build is already in pgoress
    '''
    emailMessage = str(product) + ' ' + str(version) + ' ' + str(cpiDrop)
    try:
        product=Product.objects.get(name=product)
        if 'userid' not in request.session:
            return HttpResponseRedirect('/' + str(product.name) + '/logindwaxe/' +str(version) + '/' + str(cpiDrop) + '/cpibuild/')
        logdwaxe=checkDwaxeAccess(request,request.session['userid'],request.session['password'],product,cpiDrop,version)
        loggedin = 0
        loginSuccessPat = 'You have successfully logged into DWAXE'
        unknownUserPat = 'Unknown DWAXE user'
        wrongCredPat = 'You entered the wrong credentials'
        success = search(loginSuccessPat,logdwaxe.text)
        failure = search(unknownUserPat,logdwaxe.text)
        wrongCred = search(wrongCredPat,logdwaxe.text)
        if success:
            loggedin = 1
        elif failure:
            errormsg = 'You do not have access to run the build in Dwaxe. Please contact administrator to gain access.'
            return render(request,'cpi/dwaxeError.html',{'Error':errormsg,'redirect':'cpibuild',})
        elif wrongCred:
            errormsg = 'You entered the Wrong Credentials.'
            return render(request,'cpi/dwaxeError.html',{'Error':errormsg,'product':str(product),'cpiDrop':str(cpiDrop),'version':version,'redirect':'cpibuild',})
        else:
            errormsg = 'Something went wrong. Please contact administrator'
            return render(request,'cpi/dwaxeError.html',{'Error':errormsg,'redirect':'cpibuild',})
        if loggedin:
            library = CPIIdentity.objects.get(drop__name=version,cpiDrop=cpiDrop,drop__release__product=product)
            if library.status == "In Progress":
                call_command("cpistatus",product=str(product),drop=str(version),cpiDrop=str(cpiDrop),userName=str(request.session['userid']),password=str(request.session['password']))
                return render(request,"cpi/cpiBuildStatus.html",
                    {
                       'product':product,
                       'version':version,
                       'cpiDrop':cpiDrop,
                       'confluenceUrl':confluenceUrl,
                    })
            elif library.status == "Passed" or str(library.status) == "None" or str(library.status) == "Failed" or str(library.status) == "Aborted":
                content = StringIO()
                call_command("buildcpi",product=str(product),drop=str(version),cpiDrop=str(cpiDrop),userName=str(request.session['userid']),password=str(request.session['password']),stdout=content)
                content.seek(0)
                retval = content.read()
                if "Error" in retval:
                    errormsg = 'Error in creating Library. Please raise JIRA Ticket.\n The issue will be notified to the administrator' + str(retval)
                    send_mail('Build Error',emailMessage + " Build Failed to start",'CI-Framework@lmera.ericsson.se',[str(request.user)+ '@lmera.ericsson.se'])
                    return render(request,'cpi/dwaxeError.html',{'Error':errormsg,'confluenceUrl':confluenceUrl,})
                return HttpResponseRedirect('/' + str(product.name) + '/cpibuild/' + str(version) + '/' + str(cpiDrop))
            elif library.status == "Completed":
                library.status="Passed"
                library.save()
                send_mail('Build Sucess',emailMessage + " Build Completed Successfully",'CI-Framework@lmera.ericsson.se',[str(request.user)+ '@lmera.ericsson.se'])
                return HttpResponseRedirect('/' + str(product.name) + '/cpiDocs/' + str(version) + '/' + str(cpiDrop))
            elif library.status == "Error":
                library.status="Failed"
                library.save()
                send_mail('Build Failed',emailMessage + " Build Completed with Error",'CI-Framework@lmera.ericsson.se',[str(request.user)+ '@lmera.ericsson.se'])
                return HttpResponseRedirect('/' + str(product.name) + '/cpiDocs/' + str(version) + '/' + str(cpiDrop))
            elif library.status == "Abort":
                library.status="Aborted"
                library.lastBuild = datetime.now()
                library.save()
                send_mail('Build Aborted',emailMessage + " Build Aborted by User",'CI-Framework@lmera.ericsson.se',[str(request.user)+ '@lmera.ericsson.se'])
                return HttpResponseRedirect('/' + str(product.name) + '/cpiDocs/' + str(version) + '/' + str(cpiDrop))
    except Exception as e:
        logger.error("Issue with starting CPI Build: " +str(e))
        return HttpResponse("There was an issue starting CPI Build : " + str(product) + " version: " +str(version)+ " Error thrown: " +str(e))
        return 1
            
@login_required
def addCPIDocument(request, product, version,cpiDrop):
    '''
    The addDocument function is used to add a document to a CPI build drop building up Document baseline page
    '''
    try:
        productObj = Product.objects.get(name=product)
        if request.method == 'POST':
            form = CPIAddDoc(request.POST)
            if form.is_valid():
                docObjList=[]
                try:
                    addDoc = cpi.utils.modifyCpiBaseline(request,product,version,cpiDrop,form)
                    if addDoc["Status"] == "Gask Error":
                        errdoc = addDoc["Doc"]
                        docObjList.append(errdoc)
                        return render(request,'cpi/addDocError.html',{'doclist':docObjList,'product':productObj,'version':version,})
                    elif addDoc["Status"] == "Success":
                        sendNotification(str(request.user),str(addDoc["number"]),product,version,cpiDrop,'Added')	    
                        logger.info("Document: " + str(addDoc["Doc"]) + "Saved to DB with Success")
                        return HttpResponseRedirect('/' + str(productObj.name) + '/cpiDocs/' +str(version) + '/' + str(cpiDrop) + '/')
                    else:
                        logger.error("Unable to Save Document due to error" + str(addDoc["Status"]))
                        return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
                except Exception as e:
                    logger.error("Unable to Save Document: "+  " to DB, Error Thrown: " +str(e))
                    return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
            else:
                logger.info("form invalid " + str(form.errors))
                return render(request, 'cpi/addDocForm.html',{'form':form,'product':productObj,'version':version,'cpiDrop':cpiDrop,'confluenceUrl':confluenceUrl,})
        else:
            form = CPIAddDoc()
            form.fields['section']=TreeNodeChoiceField(queryset=CPISection.objects.filter(product__name=product).order_by('id'))
            return render(request, 'cpi/addDocForm.html',{'form':form,'product':productObj,'version':version,'cpiDrop':cpiDrop,'confluenceUrl':confluenceUrl,})
    except Exception as e:
        logger.error("Issue with adding document to CPI Baseline: " +str(e))
        return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
        return 1

@login_required
def editCPIDocument(request, product, version,cpiDrop,docId):
    '''
    The addDocument function is used to add a document to a drop building up Document baseline page
    '''
    try:
        productObj = Product.objects.get(name=product)
        document = CPIDocument.objects.get(pk=docId)
        cpiDrops=CPIIdentity.objects.get(cpiDrop=cpiDrop,drop__name=version,drop__release__product=productObj)
        user=str(request.user)
        drop=version
        if request.method == 'POST':
            form = CPIDocumentForm(request.POST,user=request.user,docId=docId)
            if form.is_valid():
                docObjList=[]
                try:
                    formDoc=form.save(commit=False)
                    editDoc = cpi.utils.modifyCpiBaseline(request,product,version,cpiDrop,form,docId)
                    if editDoc["Status"] == "Gask Error":
                        errdoc = editDoc["Doc"]
                        docObjList.append(errdoc)
                        return render(request,'cpi/addDocError.html',{'doclist':docObjList,'product':productObj,'version':version,})
                    elif editDoc["Status"] == "Success":
                        sendNotification(str(request.user),str(editDoc["number"]),product,version,cpiDrop,'Added')	    
                        logger.info("Document: " + str(editDoc["Doc"]) + "Saved to DB with Success")
                        return HttpResponseRedirect('/' + str(productObj.name) + '/cpiDocs/' +str(version) + '/' + str(cpiDrop) + '/')
                    elif editDoc["Status"] == "Deleted":
                        sendNotification(str(request.user),str(editDoc["number"]),product,version,cpiDrop,'Deleted')	    
                        logger.info("Document: " + str(editDoc["Doc"]) + "Deleted from DB with Success")
                        return HttpResponseRedirect('/' + str(productObj.name) + '/cpiDocs/' +str(version) + '/' + str(cpiDrop) + '/')
                    else:
                        logger.error("Unable to Save Document due to error" + str(editDoc["Status"]))
                        return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
                except Exception as e:
                    logger.error("Unable to Save Document: "+  " to DB, Error Thrown: " +str(e))
                    return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
            else:
                logger.info("form invalid " + str(form.errors))
                return render(request, 'cpi/editDocForm.html',{'form':form,'product':productObj,'version':version,'cpiDrop':cpiDrop,'docId':docId,'confluenceUrl':confluenceUrl,})
        else:
            form = CPIDocumentForm(user=user,instance=document,docId=docId)
        form.fields['section']=TreeNodeChoiceField(queryset=CPISection.objects.filter(product__name=product).order_by('-id'))
        return render(request, 'cpi/editDocForm.html',{'form':form,'product':productObj,'version':version,'cpiDrop':cpiDrop,'docId':docId,'confluenceUrl':confluenceUrl,})
    except Exception as e:
        logger.error("Issue with editing document to CPI Baseline: " +str(e))
        return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
        return 1


@login_required
def CPIFromExcel(request,product,version,cpiDrop):	

    '''
    Updating the baseline from Excel
    '''

    try:
        productObj = Product.objects.get(name=product)
        cpiDrops=CPIIdentity.objects.get(cpiDrop=cpiDrop,drop__name=version,drop__release__product__name=product)
        if request.method =='POST':
            importform = CPIAddFromExcel(request.POST,request.FILES)
            if importform.is_valid():
                try:
                    excelUpload(request.FILES['file'],version,cpiDrop)
                    book= xlrd.open_workbook(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls')
                    importDoc = cpi.utils.modifyCpiBaselineFromExcel(request,product,version,cpiDrop,book)
                    if importDoc["Status"] == "Error":
                        docObjList = importDoc["Doc"]
                        section = importDoc["section"]
                        sendNotification(str(request.user),'Bulk Import',product,version,cpiDrop,'Imported with Error')
                        if os.path.exists(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls'):
                            os.remove(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls')
                        return render(request,'cpi/addDocError.html',{'doclist':docObjList,'product':productObj,'version':version,'seclist':section})
                    elif importDoc["Status"] == "Success":
                        sendNotification(str(request.user),'Bulk Import',product,version,cpiDrop,'Imported')
                        if os.path.exists(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls'):
                            os.remove(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls')
                        return HttpResponseRedirect('/' + str(productObj.name) + '/cpiDocs/' +str(version) + '/' + str(cpiDrop) + '/')
                    else:
                        docObjList = importDoc["Doc"]
                        section = importDoc["section"]
                        sendNotification(str(request.user),'Bulk Import',product,version,cpiDrop,'Import Failed')
                        if os.path.exists(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls'):
                            os.remove(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls')
                        return render(request,'cpi/addDocError.html',{'doclist':docObjList,'product':productObj,'version':version,'seclist':section})
                except Exception as e:
                        logger.error("Unable to Save Document import document, Error Thrown: " +str(e))
                        return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
            else:
                logger.info("form invalid " + str(form.errors))
                return render(request, 'cpi/batchImport.html',{'form':form,'product':productObj,'version':version,'cpiDrop':cpiDrop,'confluenceUrl':confluenceUrl,})
        else:
            importform = CPIAddFromExcel() 
        return render(request, 'cpi/batchImport.html',{'form':importform,'product':productObj,'version':version,'cpiDrop':cpiDrop,'confluenceUrl':confluenceUrl,})
    except Exception as e:
        logger.error("Issue with importing document to CPI Baseline: " +str(e))
        return render(request,'cpi/addDocError.html',{'product':productObj,'version':version,})
        return 1

def excelUpload(fileName,version,cpiDrop):

    '''
    Handling the excel file uploaded for Bulk modification of data
    '''

    with open(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls', 'wb+') as destination:
        for chunk in fileName.chunks():
            destination.write(chunk)	

def searchCPIDocument(request, product, version,cpiDrop):

    '''
    Search the particular document in the specified drop and cpidrop
    '''

    try:
        products = Product.objects.get(name=product)
        if request.method == 'POST':
            form = CPISearchDoc(request.POST)
            if form.is_valid():
                docObjList=[]
                newList=[]
                try:
                    number = form.cleaned_data['docNumber']
                    if not "Procus" in product:
                        docObjList = cpi.utils.getCPIDocuments(version,product,cpiDrop)
                        for doc in docObjList:
                            if str(number) in str(doc.docNumber).strip(' '):
                                newList.append(doc)
                        docObjList=newList
                    else:
                        docObjList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__cpiDrop=cpiDrop)
                        docObjList = docObjList.filter(docNumber=number)
                    section=utils.getCPISection(product,docObjList)
                    product = Product.objects.get(name=product)
                    identity = CPIIdentity.objects.get(drop__name=version,cpiDrop=cpiDrop,drop__release__product__name=product)
                    return render(request,"cpi/searchResults.html",
                        {
                            'docObjList': docObjList,
                            'nodes': section,
                            'version': version,
                            'product': product,
                            'identity': identity,
                            'confluenceUrl':confluenceUrl,
                        })
                except Exception as e:
                    logger.error("Issue with Document Web Page: " +str(e))
                    return render ( request,'cpi/addDocError.html',{'product':products,'version':version})
        else:
            form=CPISearchDoc()
            return render(request,'cpi/searchCPI.html',{'form':form,'product':products,'version':version,'cpiDrop':cpiDrop})
    except Exception as e:
        logger.error("Issue with searching document in CPI Baseline: " +str(e))
        return HttpResponse("There was an issue downloading CPI Baseline as SDI: " + str(product) + " version: " +str(version) + " Error thrown: " +str(e))
        return 1

def loginDwaxe(request,product,version,cpiDrop,redirect):

    '''
    Credentials to login Dwaxe
    '''

    products = Product.objects.get(name=product)
    if request.method == 'POST':
        form = DwaxeLogin(request.POST)
        request.session['userid']=request.POST['username']
        request.session['password']=request.POST['password']
        return HttpResponseRedirect('/' + str(products.name) + '/' + str(redirect) + '/' +str(version) + '/' + str(cpiDrop) + '/')
    else:
        form=DwaxeLogin()
    return render(request,'cpi/dwaxeLogin.html',{'form':form,'product':products,'version':version,'cpiDrop':cpiDrop,'redirect':str(redirect),})

def checkDwaxeAccess(request, userName, password,product,cpiDrop,version):

    '''
    Checking permission to Dwaxe for the user logged in
    '''

    loginUrl = 'http://' + buildUrl + "?requested_action=logon_racf"
    logdwaxe = session.get(loginUrl,headers=cookieVal,proxies=proxy)
    newCookie= search(cookiePattern,logdwaxe.headers['set-cookie'])
    body = {'USER' : userName, 'PASSWORD' : password, 'target' : "$SM$HTTP%3a%2f%2f" + str(loginUrl).replace('http://','') }
    newBody = dict(body.items() + data.items())
    logdwaxe = requests.post(authUrl,headers=authValues,data=newBody,proxies=proxy,allow_redirects=True)
    return logdwaxe 

def sendNotification(user,number,product,version,cpiDrop,action):

    '''
    Sending email notification on modificaiton of Baseline
    '''
    
    subject = str(product) + "-" + str(version) + " " + str(cpiDrop) + ' Baseline modified'
    htmlContent = '<table border=1><tr> <td> <b> Product </b> </td> <td>' + product + '</td></tr><tr><td><b>Drop</b></td><td>' + version + '</td></tr><tr><td><b>CPI Build</b></td><td>' + cpiDrop + '</td></tr><tr><td><b>Document Number</b></td><td>'+ number + '</td></tr><tr><td><b>' + action + ' by</b></td><td>' + user + '</td></tr></table>'
    fromEmail = 'CI-Framework@lmera.ericsson.se'
    cpiDrops=CPIIdentity.objects.get(cpiDrop=cpiDrop,drop__name=version,drop__release__product__name=product)
    toUserEmail = cpiDrops.owner + '@lmera.ericsson.se'
    to = str(toUserEmail)
    ccUserEmail = user + '@lmera.ericsson.se'
    cc = str(ccUserEmail)
    msg = EmailMessage(subject, htmlContent, fromEmail, [to],[cc],headers={'Cc': cc})
    msg.content_subtype = "html"
    if 'Import' in number:
        msg.attach_file(cpiLibPath + version + "_" + cpiDrop + "_" + 'batchimport.xls')
    msg.send(fail_silently=True)
    

