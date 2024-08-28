from datetime import datetime
now = datetime.now()
import re
import re,xlrd,xlwt
from re import search
from cireports.models import *
import os
from distutils.version import LooseVersion
from django.http import HttpResponse, Http404, HttpResponseRedirect,StreamingHttpResponse
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()
from cpi.models import *
from django.core.management import call_command
from StringIO import StringIO
import requests
from requests import Request, Session
from django.db.models import Q
session = requests.Session()

config = CIConfig()
cpiLibPath = config.get("CPI", 'cpiLibPath')
cpiSdiPath = config.get("CPI",'cpiSdiPath')
cpiGaskUrl = config.get("CPI",'gaskUrl')

def getCPIDocuments(version,product,cpiDrop):
    '''
    The displayDocuments function is responable from building up the Document baseline page view per drop
    '''
    try:
        docObjList=[]
        cpiObjList=[]
        release=Release.objects.get(drop__name=version,product__name=product)
        firstDrop=Drop.objects.filter(release=release).order_by('id').values_list('id',flat=True)[0]
        indexDrop=Drop.objects.get(name=version,release=release)
        first=CPIIdentity.objects.filter(drop__name=version).order_by('id').values_list('id',flat=True)[0]
        last=CPIIdentity.objects.get(drop__name=version,cpiDrop=cpiDrop)
	if "Deployment" in cpiDrop:
	        allCpiDocLists = CPIDocument.objects.filter(section__product__name=product,drop__id__range=(firstDrop,indexDrop.id)).filter(cpiDrop__cpiDrop__icontains="Deployment")
        	cpiDocList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__id__range=(first,last.id)).filter(cpiDrop__cpiDrop__icontains="Deployment")
	        docList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__id__range=(first,last.id)).values_list('docNumber',flat=True).filter(cpiDrop__cpiDrop__icontains="Deployment")
        	cpiDropList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__cpiDrop=cpiDrop).filter(cpiDrop__cpiDrop__icontains="Deployment")
	        cpiList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__cpiDrop=cpiDrop).filter(cpiDrop__cpiDrop__icontains="Deployment").values_list('docNumber',flat=True)
        	cpiObjList=list(cpiDropList)
	else:
                allCpiDocLists = CPIDocument.objects.filter(section__product__name=product,drop__id__range=(firstDrop,indexDrop.id)).filter(~Q(cpiDrop__cpiDrop__icontains="Deployment"))
                cpiDocList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__id__range=(first,last.id)).filter(~Q(cpiDrop__cpiDrop__icontains="Deployment"))
                docList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__id__range=(first,last.id)).values_list('docNumber',flat=True).filter(~Q(cpiDrop__cpiDrop__icontains="Deployment"))
                cpiDropList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__cpiDrop=cpiDrop).filter(~Q(cpiDrop__cpiDrop__icontains="Deployment"))
                cpiList = CPIDocument.objects.filter(section__product__name=product,drop__name=version,cpiDrop__cpiDrop=cpiDrop).filter(~Q(cpiDrop__cpiDrop__icontains="Deployment")).values_list('docNumber',flat=True)
                cpiObjList=list(cpiDropList)
        for doc in cpiDocList:
            if doc.docNumber not in cpiList:
                cpiObjList.append(doc)
        docObjList=list(cpiObjList)
        for doc in allCpiDocLists:
            if doc.docNumber not in docList:
               docObjList.append(doc)
        docObjList=sorted(docObjList,key=lambda docObjList:docObjList.id)
        return docObjList
    except Exception as e:
        logger.error("Issue with getting Document: " +str(e))
        return 1


def getCPISection(product,docObjList):

    '''
    Return parent(s) of the document in a list format
    '''

    secObjList=[]
    docObjList=sorted(docObjList,key=lambda docObjList:docObjList.section.id)
    for doc in docObjList:
        docList=CPISection.objects.get(id=doc.section_id)
        secList=docList.get_family()
        for sec in secList:
            if sec not in secObjList:
                secObjList.append(sec)
    return secObjList

def getLibName(product,drop,cpiDrop):

    '''
    Return Library Name in Dwaxe usable format
    '''

    library= CPIIdentity.objects.get(drop__name=drop,cpiDrop=cpiDrop,drop__release__product__name=product)
    title = search("EN/(.*)",library.identity)
    libName = str("ci") + title.group(1).replace(" ", '').lower().replace('/','') + str(library.rstate.lower())
    return libName

def formatExcel(product,drop,cpiDrop,docObjList):

    '''
    Return workbook with data for the selected build
    '''
    libName = getLibName(product,drop,cpiDrop)
    excelfile = cpiSdiPath + str(libName) + '.xls'
    excelrow=2
    if os.path.isfile(excelfile):
            os.remove(excelfile)
    workbook = xlwt.Workbook(encoding = 'utf8')
    sheet = workbook.add_sheet("Sheet1",cell_overwrite_ok=True)
    sheet.col(0).width=5500 #3333 - 1 inch
    sheet.col(1).width=18000
    sheet.col(2).width=6500
    sheet.col(3).width=3500
    sheet.col(4).width=3000
    sheet.col(5).width=6500
    sheet.col(6).width=6500
    sheet.col(7).width=6500
    sheet.write_merge(0, 0, 0, 7, 'Title')
    font = xlwt.Font()
    font.name = 'Ericsson Capital TT'
    font.colour_index = 26
    font.bold = True
    font.height = 320
    alignment = xlwt.Alignment()
    alignment.horz = xlwt.Alignment.HORZ_CENTER
    alignment.vert = xlwt.Alignment.VERT_CENTER
    pattern = xlwt.Pattern()
    pattern.pattern = xlwt.Pattern.SOLID_PATTERN
    pattern.pattern_fore_colour =  4
    style = xlwt.XFStyle()
    style.alignment = alignment
    style.font = font
    style.pattern=pattern
    style1 = xlwt.XFStyle()
    style1.alignment = alignment
    font1 = xlwt.Font()
    font1.name = 'Ericsson Capital TT'
    font1.bold = True
    font1.colour_index = 26
    font1.height = 200
    pattern1 = xlwt.Pattern()
    pattern1.pattern = xlwt.Pattern.SOLID_PATTERN
    pattern1.pattern_fore_colour = 25
    style2 = xlwt.XFStyle()
    style2.alignment = alignment
    style2.font = font1
    style2.alignment = alignment
    style2.pattern=pattern1
    sheet.write(1,0,'Section/Folder',style2)
    sheet.write(1,1,'Document Name',style2)
    sheet.write(1,2,'Number',style2)
    sheet.write(1,3,'Revision',style2)
    sheet.write(1,4,'Language',style2)
    sheet.write(1,5,'Author',style2)
    sheet.write(1,6,'Comment',style2)
    sheet.write(1,7,'Modified by',style2)
    for document in docObjList:
        sheet.write(excelrow,0,str(document.section.title))
        sheet.write(excelrow,1,str(document.docName))
        sheet.write(excelrow,2,str(document.docNumber))
        sheet.write(excelrow,3,str(document.revision),style1)
        sheet.write(excelrow,4,str(document.language).upper(),style1)
        sheet.write(excelrow,5,str(document.author),style1)
        sheet.write(excelrow,6,str(document.comment))
        sheet.write(excelrow,7,str(document.owner))
        excelrow += 1
    sheet.write(0,0,'CPI BASELINE - ' + product + ' - ' + cpiDrop ,style)
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename='+ str(libName) +'.xls'
    workbook.save(response)
    return response

def checkGaskUpload(number,language,revision):

    '''
    Return no error if the document is stored in GASK
    '''

    gaskUrl = cpiGaskUrl + number + '&lang=' + language + '&rev=' + revision
    requestUrl=requests.get(gaskUrl)
    errorPattern="request has failed"
    error = search(errorPattern,requestUrl.text)
    if error:
        return "Gask Error"
           
def modifyCpiBaseline(request,product,version,cpiDrop,form,docId=''):

    '''
    Update the baseline
    '''

    try:
        productObj = Product.objects.get(name=product)
        cpiDrops=CPIIdentity.objects.get(cpiDrop=cpiDrop,drop__name=version,drop__release__product=productObj)
        dropObj = Drop.objects.get(name=version,release__product=productObj)
        if docId:
            formDoc=form.save(commit=False)
            dropObj=Drop.objects.get(name=version,release__product__name=product)
            secObj = CPISection.objects.get(pk=formDoc.section.id,product=productObj)
            name = formDoc.docName
            author = formDoc.author
            language = formDoc.language
            number = formDoc.docNumber
            revision = formDoc.revision
            deliveryDate = default=datetime.now()
            comment = formDoc.comment
            owner = str(request.user)
        else:    
            section = form.cleaned_data['section']
            secObj = CPISection.objects.get(pk=section)
            name = form.cleaned_data['docName']
            author = form.cleaned_data['author']
            language = form.cleaned_data['language']
            number = form.cleaned_data['docNumber']
            revision = form.cleaned_data['revision']
            deliveryDate = default=datetime.now()
            comment = form.cleaned_data['comment']
            owner = str(request.user)
        
        checkGask = checkGaskUpload(number,language,revision)
        if checkGask == "Gask Error":
            doc = s.docName + "      " + number + "      U" +  language + revision
            return {'Status': "Gask Error",'Doc': doc}
        if CPIDocument.objects.filter(docNumber=number,drop=dropObj,cpiDrop=cpiDrops).exists():
            documents=CPIDocument.objects.get(docNumber=number,drop=dropObj,cpiDrop=cpiDrops)
            documents.section=secObj
            documents.docName=name
            documents.author=author
            documents.author=author
            documents.revision=revision
            documents.deliveryDate=default=datetime.now()
            documents.comment = comment
            documents.owner=str(request.user)
            documents.language=language
            documents.cpiDrop=cpiDrops
            documents.save()
        else:
            if docId:
                formDoc.drop=dropObj
                formDoc.cpiDrop=cpiDrops
                formDoc.owner=str(request.user)
                formDoc.deliveryDate = default=datetime.now()
                number = formDoc.docNumber
                formDoc.save()
            else:
                documents=CPIDocument(section_id=section,docName=name,author=author,docNumber=number,revision=revision,owner=owner,drop=dropObj,comment=comment,deliveryDate=deliveryDate,language=language,cpiDrop=cpiDrops)
                documents.save()
        identity = CPIIdentity.objects.get(drop=dropObj,cpiDrop=cpiDrop,drop__release__product=productObj)
        identity.lastModified = datetime.now()
        identity.save() 
        return {'Status': "Success",'Doc': str(name),'number': str(number)}
    except Exception as e:
        logger.error("Unable to Save Document: "+  " to DB, Error Thrown: " +str(e))
        return {"Status": "Error " + str(e) }
    
def modifyCpiBaselineFromExcel(request,product,version,cpiDrop,book):   

    '''
    Update baseline from excel
    '''

    try:
        productObj = Product.objects.get(name=product)
        cpiDrops=CPIIdentity.objects.get(cpiDrop=cpiDrop,drop__name=version,drop__release__product=productObj)
        sheet = book.sheet_by_index(0)
        docObjList=[]
        seclist=[]
        errors=0
        for row_index in range(2,sheet.nrows):
            sections = str(sheet.cell(row_index,0).value)
            if CPISection.objects.filter(title=sections,product=productObj).exists():
                secObj = CPISection.objects.get(title=sections,product=productObj)
                name = str(sheet.cell(row_index,1).value)
                author = str(sheet.cell(row_index,5).value)
                number = str(sheet.cell(row_index,2).value)
                revision = str(sheet.cell(row_index,3).value)
                dropObj = Drop.objects.get(name=version,release__product=productObj)
                deliveryDate = default=datetime.now()
                language=str(sheet.cell(row_index,4).value)
                cmt = search("Batch Import",str(sheet.cell(row_index,6).value))
                if cmt:
                    comment = str(sheet.cell(row_index,6).value) + ' - Batch Import'
                else:
                    comment = "Batch Import"
                owner = str(request.user)
                checkGask = checkGaskUpload(number,language,revision)
                
                if checkGask == "Gask Error":
                    errors=1
                    doc = name + "      " + number + "      U" +  language + " " + revision
                    docObjList.append(doc)
                else:
                    if CPIDocument.objects.filter(docNumber=number,drop=dropObj,cpiDrop=cpiDrops).exists():
                         documents=CPIDocument.objects.get(docNumber=number,drop=dropObj,cpiDrop=cpiDrops)
                         documents.section=secObj
                         documents.name=name
                         documents.author=author
                         documents.revision=revision
                         documents.deliveryDate=default=datetime.now()
                         documents.comment = comment
                         documents.owner=owner
                         documents.language=language
                         documents.save()
                         identity = CPIIdentity.objects.get(drop__name=version,cpiDrop=cpiDrop,drop__release__product=productObj)
                         identity.lastModified = datetime.now()
                         identity.save()
                    else:
                         documents=CPIDocument(section=secObj,docName=name,author=author,docNumber=number,revision=revision,owner=owner,drop=dropObj,comment=comment,deliveryDate=deliveryDate,language=language,cpiDrop=cpiDrops)
                         documents.save()
                         identity = CPIIdentity.objects.get(drop__name=version,cpiDrop=cpiDrop,drop__release__product=productObj)
                         identity.lastModified = datetime.now()
                         identity.save()
            else:
                errors=1
                if sections not in seclist:
                    seclist.append(sections)
        if errors:
            return {'Status': "Error",'Doc': docObjList,'section': seclist} 
        else:
            return {'Status': "Success"}  
    except Exception as e:
        logger.error("Unable to import Documents Error Thrown: " +str(e))
        return {"Status": "Unexpected Error"}
