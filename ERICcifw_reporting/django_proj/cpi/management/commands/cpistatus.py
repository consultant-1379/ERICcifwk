from optparse import make_option
from django.core.management.base import BaseCommand,CommandError
from cpi.models import *
import sys,requests,logging
from re import search
from requests import Request, Session
import os
import datetime
from datetime import datetime
import ast
from ciconfig import CIConfig
import cpi
from cpi import utils
config = CIConfig()
now=datetime.now()
session = requests.Session()
proxy = {
  "http": "",
  "https": "",
}

cpiLibPath = config.get("CPI", 'cpiLibPath')
cpiSdiPath = config.get("CPI",'cpiSdiPath')
cookieVal = config.get("CPI",'cookieVal')
cookieVal=ast.literal_eval(config.get("CPI",'cookieVal'))
dwaxeUrl = config.get("CPI", 'dwaxeUrl')
workDir = config.get("CPI", 'workDir')
cookiePattern = config.get("CPI", 'cookiePattern')
data = ast.literal_eval(config.get("CPI",'data'))
authUrl = config.get("CPI",'authUrl')
authValues = ast.literal_eval(config.get("CPI",'authValues'))

class Command(BaseCommand):

    help = "Check the status of Library Build"
    
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
            make_option('--password',
                dest='password',
                help='Dwaxe password of the signum'),
            
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
        if options['password']:
            password=options['password']
        else:
            raise CommandError('Password Required')
            
        statusFile=open(cpiLibPath + 'status.html','w')
        action=''
        libName = cpi.utils.getLibName(product,drop,cpiDrop)
        status=libstatus(action,libName,userName,password)
        completePattern="(Library creation is completed successfully).*"
        errorPattern="(Library creation is completed with errors).*"
        progressPattern="(Progress).*"
        buildAbortPattern= "(Aborted by user request).*"
        dwaxestartPattern="DWAXE starting up.*"
        progress=search(progressPattern,status.text)
        if(progress):
            retValue = "In Progress"
        completed=search(completePattern,status.text)
        if(completed):
            retValue = str(completed.group(1))
        aborted=search(buildAbortPattern,status.text)
        if(aborted):
           retValue = str(aborted.group(1))
        errorCompleted=search(errorPattern,status.text)
        if(errorCompleted):
           retValue = "Failure"
        dwaxeStarting=search(dwaxestartPattern,status.text)
        if(dwaxeStarting):
            retValue = "Dwaxe Starting"
            newStatus=libstatus('action=Status',libName,userName,password)
            dwaxeStarting=search(dwaxestartPattern,newStatus.text)
            if(dwaxeStarting):
                retValue = "Dwaxe Starting"
            completed=search(completePattern,newStatus.text)
            if(completed):
                retValue = str(completed.group(1))
            aborted=search(buildAbortPattern,newStatus.text)
            if(aborted):
                retValue = str(aborted.group(1))
            errorCompleted=search(errorPattern,newStatus.text)
            if(errorCompleted):
               retValue = "Failure"
            statusFile.write(newStatus.text)
        else:
            statusFile.write(status.text)
        statusFile.close()
        resultPage=''
        with open(cpiLibPath + 'status.html') as input_data:
            for line in input_data:
                if line.strip() == '<BODY bgcolor="#ffffff">':
                    break
            for line in input_data:
                if line.strip() == '<TABLE width=100% border=0 valign=center>' or line.strip()== '<TABLE cellSpacing=0 cellPadding=0 border=0>' or line.strip()== '<TABLE width=100% border=0>':
                    break
                resultPage=resultPage + line
        completed = search(completePattern,resultPage)
        if os.path.isfile(cpiLibPath + "status.html"):
            os.remove(cpiLibPath + "status.html")
        library= CPIIdentity.objects.get(drop__name=drop,cpiDrop=cpiDrop,drop__release__product__name=product)
        if completed:
            library.status="Completed"
            library.lastBuild = datetime.now()
            library.save()
        if "Aborted" in retValue:
            library.status="Abort"
            library.lastBuild = datetime.now()
            library.save()
        if "Failure" in retValue:
            library.status="Error"
            library.lastBuild = datetime.now()
            library.save()
        if "Progress" in retValue:
            library.status="In Progress"
            library.save()
        statusfile=open(cpiLibPath + libName+'.html','w+')
        statusfile.write('<html><head><LINK href="/static/dwaxestyle.css" type=text/css rel=stylesheet><BODY bgcolor="#ffffff">')
        statusfile.write(resultPage)
        statusfile.write('</body></html>')
        statusfile.close()
        return retValue

def libstatus(action,libName,userName,password):
        
    statusUrl = 'http://' + dwaxeUrl + action + '&workdir=' + workDir + userName + "/" + libName + "&libname="+ libName + "&log=" + libName + "_log.sgml&previousBarPercent=0"
    checkStatus = session.get(statusUrl,headers=cookieVal,proxies=proxy)
    newCookie= search(cookiePattern,checkStatus.headers['set-cookie'])
    body = {'USER' : userName, 'PASSWORD' : password, 'target' : "$SM$HTTP%3a%2f%2f" + str(statusUrl).replace('http://','') }
    newBody = dict(body.items() + data.items())
    checkStatus = requests.post(authUrl,headers=authValues,data=newBody,proxies=proxy,allow_redirects=True)
    return checkStatus

