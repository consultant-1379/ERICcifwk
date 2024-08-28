from optparse import make_option
from django.core.management.base import BaseCommand,CommandError
from cpi.models import *
from cpi import utils
import time
import ast
import cpi
from re import search
config = CIConfig()
cpiLibPath = config.get("CPI", 'cpiLibPath')
cpiSdiPath = config.get("CPI",'cpiSdiPath')

class Command(BaseCommand):

    help = "Create the SDI file"
    
    option_list = BaseCommand.option_list  + (
            make_option('--product',
                dest='product',
                help='Name of the product Ex: OSS-RC'),
            make_option('--drop',
                dest='drop',
                help='Drop of the Product EX: 14.1.8'),
            make_option('--cpiDrop',
                dest='cpiDrop',
                help='Name of the CPI Build Drop Ex; 14.1.8_Rebuild'),
            make_option('--userName',
                dest='userName',
                help='signum of the responsible individual'),
        )


    def handle(self, *args, **options):
		
        if options['product']:
            product=options['product']
        else:
            raise CommandError('Product Required')
        if options['drop']:
            drop=options['drop']
        else:
            raise CommandError('Drop Required')
        if options['cpiDrop']:
            cpiDrop=options['cpiDrop']
        else:
            raise CommandError('cpiDrop Required')
        if options['userName']:
            userName=options['userName']
        else:
            raise CommandError('userName Required')
        
        if ("Procus" in product):
            docObjList = CPIDocument.objects.filter(section__product__name=product,drop__name=drop)
        else:
            docObjList = utils.getCPIDocuments(drop,product,cpiDrop)
        secObjList=[]
        products=Product.objects.get(name=product)
        library = CPIIdentity.objects.get(drop__name=drop,cpiDrop=cpiDrop,drop__release__product=products)
        libName = cpi.utils.getLibName(product,drop,cpiDrop)
        sdiFile=open(cpiSdiPath + libName +'.sgm','w')
        utils.docroot=[]
        secObjList = utils.getCPISection(product,docObjList)
        newParentList=[]
        for doc in docObjList:
            docList=CPISection.objects.get(id=doc.section_id)
            secList=docList.get_ancestors().values_list('id',flat=True)
            for sec in secList:
                newParentList.append(sec)
        parentList=CPISection.objects.filter(parent_id__isnull=False,product__name=product).values_list('parent_id',flat=True)
        docParent=CPIDocument.objects.filter(section__product__name=product,section__parent_id__isnull=False).values_list('section_id',flat=True).distinct()
        count=2
        printMetaData(library,product,drop,cpiDrop,sdiFile,userName)
        for sections in secObjList:
           if not sections.parent_id:
                if "_container" in sections.title or "_Container" in sections.title:
                    title = str(sections.title)
                    title = str(sections.title).replace('_container','').replace('_Container','')
                    sdiFile.write('<chl1 role="FETCH_ONLY"><title>' + str(title) + '</title>')
                else:
                    sdiFile.write ('<chl1 role=" "><title>' + str(sections.title) + '</title>')
                if sections.id in parentList and sections.id not in docParent:
                    children = CPISection.objects.filter(parent_id = sections.id)
                    recurseTree(children,count,docObjList,parentList,newParentList,docParent,sdiFile)
                    sdiFile.write ('</chl1>')
                else:
                    sdiFile.write ('<table l-r="half-indent"><caption></caption><tgroup cols="2"><colspec colwidth="60*"><colspec colwidth="40*">')
                    sdiFile.write ('<tbody>')
                    printDoc(sections.id,docObjList,sdiFile)
                    sdiFile.write  ('</tbody></tgroup></table>')
                    sdiFile.write ('</chl1>')
        sdiFile.write ('</body>')
        sdiFile.write ( '</seif> \
<?Pub *0000002495 0>')
        return 



def printDoc(sectionid,docObjList,sdiFile):
        for document in docObjList:
            if document.section_id == sectionid:
                sdiFile.write ('<row> <entry>' + str( document.docName) + '</entry><entry>' + str(document.docNumber) + ' U'+str(document.language).lower()+ ' ' + str(document.revision) + '</entry></row>')

def recurseTree(sections,count,docObjList,parentList,newParentList,docParent,sdiFile):
    
    for section in sections:
        if section.id in newParentList or section.id in docParent:
                if "_headers" in section.title:
                    sdiFile.write  ('<table l-r="half-indent"><caption></caption><tgroup cols="2"><colspec colwidth="60*"><colspec colwidth="40*">')
                    title = str(section.title)
                    title = str(section.title).replace('_headers','').upper()
                    sdiFile.write ('<thead><row><entry>' + title + '</entry><entry></entry></row></thead>')
                elif "_Container" in section.title or "_container" in section.title:
                    title = str(section.title)
                    title = str(section.title).replace('_container','').replace('_Container','')
                    sdiFile.write('<chl' + str(count) + ' role="FETCH_ONLY"><title>' + title + '</title>')
                else:
                    sdiFile.write ('<chl' + str(count) + ' role=" "><title>' + str(section.title) + '</title>')
                if section.id in parentList:
                    children = CPISection.objects.filter(parent_id = section.id)
                    childDoc = CPIDocument.objects.filter(section_id=section.id)
                    if childDoc:
                        sdiFile.write ('<table l-r="half-indent"><caption></caption><tgroup cols="2"><colspec colwidth="60*"><colspec colwidth="44*">')
                        sdiFile.write ('<tbody>')
                        printDoc(section.id,docObjList,sdiFile)
                        sdiFile.write ('</tbody></tgroup></table>')
                    newCount=count+1
                    recurseTree(children,newCount,docObjList,parentList,newParentList,docParent,sdiFile)
                    sdiFile.write ('</chl' + str(count) + '>')
                elif section.id in docParent:
                    if not "_headers" in section.title:
                        sdiFile.write ('<table l-r="half-indent"><caption></caption><tgroup cols="2"><colspec colwidth="60*"><colspec colwidth="44*">')
                    sdiFile.write ('<tbody>')
                    printDoc(section.id,docObjList,sdiFile)
                    sdiFile.write ('</tbody></tgroup></table>')



def printMetaData(identity,product,drop,cpiDrop,sdiFile,userName):
    
    metaData1 = config.get("CPI", 'metaData1')
    metaData2 = config.get("CPI", 'metaData2')
    metaData3 = config.get("CPI", 'metaData3')
    depData = config.get("CPI", 'depData')
    sdiFile.write(metaData1)
    sdiFile.write ('<doc-no type="registration">' + str(identity.identity) + '</doc-no><language code= "en">')
    sdiFile.write ('<rev>' + str(identity.rstate) + '</rev><date>' + time.strftime("<y>%Y</y><m>%m</m><d>%d</d>") +'</date></doc-id>')
    sdiFile.write(metaData2)
    if not identity.title:
        title = product + ' - ' + drop
    else:
        title = identity.title
    sdiFile.write ('<title>' + str(title) + '</title>')
    sdiFile.write ('<user-info id="v2.2">Source SDI IDs</user-info><drafted-by>')
    sdiFile.write ('<person><name>CI Framework Generated</name><signature>' + userName + '</signature><location></location><company>LMI</company><department>LXR/SF</department></person>')
    sdiFile.write (metaData3)
    if 'Deployment' in cpiDrop:
        sdiFile.write(depData)
