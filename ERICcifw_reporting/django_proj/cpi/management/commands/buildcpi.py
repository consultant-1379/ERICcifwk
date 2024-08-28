from optparse import make_option
from django.core.management.base import BaseCommand,CommandError
import cpi
from cpi.models import *
import sys,requests,logging
from re import search
from requests import Request, Session
import json
from datetime import datetime
from django.core.management import call_command
from StringIO import StringIO
import ast
from cpi import utils
from django.contrib.auth.models import User
session = requests.Session()
proxy = {
  "http": "",
  "https": "",
}
config = CIConfig()
cpiLibPath = config.get("CPI", 'cpiLibPath')
cpiSdiPath = config.get("CPI",'cpiSdiPath')
cookieVal = config.get("CPI",'cookieVal')
cookieVal=ast.literal_eval(config.get("CPI",'cookieVal'))
dwaxeUrl = config.get("CPI", 'dwaxeUrl')
buildUrl = config.get("CPI", 'buildUrl')
buildHeaders = ast.literal_eval(config.get("CPI",'buildHeaders'))
buildData = ast.literal_eval(config.get("CPI",'buildData'))
workDir = config.get("CPI", 'workDir')
cookiePattern = config.get("CPI", 'cookiePattern')
buildLibUrl = config.get("CPI", 'buildLibUrl')
data = ast.literal_eval(config.get("CPI",'data'))
authUrl = config.get("CPI",'authUrl')
authValues = ast.literal_eval(config.get("CPI",'authValues'))


class Command(BaseCommand):

    help = "Initiate the Library build in Dwaxe"
    
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
        call_command("cpistatus",product=str(product),drop=str(drop),cpiDrop=str(cpiDrop),userName=str(userName),password=str(password))
        library= CPIIdentity.objects.get(drop__name=drop,cpiDrop=cpiDrop,drop__release__product__name=product)
        if library.status == "In Progress" :
            logger.info("CPI Library build for Drop" +str(library.drop) + " CPI Build " + str(library.cpiDrop) + " is already in progress")
            return "In Progress"
        libName = cpi.utils.getLibName(product,drop,cpiDrop)
        removeLib(libName,userName,password)
        call_command('createsgm',product=str(product),drop=str(drop),cpiDrop=str(cpiDrop),userName=str(userName))
        libtitle=createlib(libName,library,userName,password)
        if libtitle == "Error":
            return "Error"
        if library.title:
            ltitle=library.title
        else:
            ltitle=libtitle
        buildLib(libName,ltitle,library,userName,password)
        library.status="In Progress"
        library.save()
        return
            
def removeLib(libName,userName,password):

    removeUrl = 'http://' + buildUrl + "?requested_action=remove_selected_confirmed&rac=" + userName + "&lna=" + libName 
    delLib = session.get(removeUrl,headers=cookieVal,proxies=proxy)
    newCookie= search(cookiePattern,delLib.headers['set-cookie'])
    body = {'USER' : userName, 'PASSWORD' : password, 'target' : "$SM$HTTP%3a%2f%2f" + str(removeUrl).replace('http://','') }
    newBody = dict(body.items() + data.items())
    delLib = requests.post(authUrl,headers=authValues,data=newBody,proxies=proxy,allow_redirects=True)
    	  
            

def createlib(libName,library,userName,password):

    libUrl = 'http://' + buildUrl
    createBuild = session.get(libUrl,headers=cookieVal,proxies=proxy)
    newCookie= search(cookiePattern,createBuild.headers['set-cookie'])
    body = {'USER' : userName, 'PASSWORD' : password, 'target' : "$SM$HTTP%3a%2f%2f" + str(buildUrl) }
    newBody = dict(body.items() + data.items())
    createBuild = requests.post(authUrl,headers=authValues,data=newBody,proxies=proxy,allow_redirects=True)
    smSessionPattern="(SMSESSION.*);\s+path.*"
    smSessions = search(smSessionPattern,createBuild.headers['Set-Cookie'])
    buildCookie = {'Cookie' : smSessions.group(1) }
    newHeader = dict(buildHeaders.items() + buildCookie.items())
    libData = {'rac':userName,'lid':str(library.identity),'lrs':str(library.rstate),'lna':libName }
    newData = dict(buildData.items() + libData.items())
    lname = libName.replace('/','')
    files={'sdi_file':(lname +'.sgm',open(cpiSdiPath + lname+'.sgm','rb'))}
    createBuild=requests.post(libUrl,headers=newHeader,files=files,data=newData)
    titlePattern = "(name=\"lti\".*).*.value=\"(.*)\"\sclass.*"
    libTitle = search(titlePattern,createBuild.text)
    if libTitle:	
        return libTitle.group(2)
    else:
        return "Error"
            
            

def buildLib(libName,libTitle,library,userName,password):

   
    libTitle=libTitle.replace(" ",'+')
    libId=library.identity.replace("/",'%2F').replace(" ",'+')
    buildUrlLib = 'http://' + buildUrl + buildLibUrl + "&rac=" + userName + "&lti=" + libTitle +"&lna=" + libName + "&lid=" + libId + "&lrs=" + library.rstate +"&sdi=" + libName + ".sgm"
    buildLib = session.get(buildUrlLib,headers=cookieVal,proxies=proxy)
    newCookie= search(cookiePattern,buildLib.headers['set-cookie'])
    body = {'USER' : userName, 'PASSWORD' : password, 'target' : "$SM$HTTP%3a%2f%2f" + str(buildUrlLib).replace('http://','') }
    newBody = dict(body.items() + data.items())
    buildLib = requests.post(authUrl,headers=authValues,data=newBody,proxies=proxy,allow_redirects=True)    
    

    
    
    
        
    
