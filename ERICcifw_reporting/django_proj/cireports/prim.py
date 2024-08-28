from django.core.management.base import BaseCommand, CommandError
import sys
import base64
import logging
import re
import traceback as tb
import suds.metrics as metrics
from cireports.common_modules.common_functions import *
from tests import *
from suds import WebFault
from suds.client import Client
from ciconfig import CIConfig
config = CIConfig()
import xml.etree.ElementTree as ET
from django.db import connection, transaction
import utils
import models
import os
import glob
import datetime
import subprocess
from time import time, sleep
logger = logging.getLogger(__name__)
cursor = connection.cursor()
logging.getLogger('suds.client').setLevel(logging.CRITICAL)
errors = 0
logger = logging.getLogger(__name__)

rbase= ['A','B','C','D','E','F','G','H','J','K','L','M','N','S','T','U','V','X','Y','Z',
            'AA','AB','AC','AD','AE','AF','AG','AH','AJ','AK','AL','AM','AN','AS','AT','AU','AV','AX','AY','AZ',
            'BA','BB','BC','BD','BE','BF','BG','BH','BJ','BK','BL','BM','BN','BS','BT','BU','BV','BX','BY','BZ',
            'CA','CB','CC','CD','CE','CF','CG','CH','CJ','CK','CL','CM','CN','CS','CT','CU','CV','CX','CY','CZ',
            'DA','DB','DC','DD','DE','DF','DG','DH','DJ','DK','DL','DM','DN','DS','DT','DU','DV','DX','DY','DZ',
            'EA','EB','EC','ED','EE','EF','EG','EH','EJ','EK','EL','EM','EN','ES','ET','EU','EV','EX','EY','EZ',
            'FA','FB','FC','FD','FE','FF','FG','FH','FJ','FK','FL','FM','FN','FS','FT','FU','FV','FX','FY','FZ',
            'GA','GB','GC','GD','GE','GF','GG','GH','GJ','GK','GL','GM','GN','GS','GT','GU','GV','GX','GY','GZ',
            'HA','HB','HC','HD','HE','HF','HG','HH','HJ','HK','HL','HM','HN','HS','HT','HU','HV','HX','HY','HZ',
            'JA','JB','JC','JD','JE','JF','JG','JH','JJ','JK','JL','JM','JN','JS','JT','JU','JV','JX','JY','JZ',
            'KA','KB','KC','KD','KE','KF','KG','KH','KJ','KK','KL','KM','KN','KS','KT','KU','KV','KX','KY','KZ',
            'LA','LB','LC','LD','LE','LF','LG','LH','LJ','LK','LL','LM','LN','LS','LT','LU','LV','LX','LY','LZ',
            'MA','MB','MC','MD','ME','MF','MG','MH','MJ','MK','ML','MM','MN','MS','MT','MU','MV','MX','MY','MZ',
            'NA','NB','NC','ND','NE','NF','NG','NH','NJ','NK','NL','NM','NN','NS','NT','NU','NV','NX','NY','NZ',
            'SA','SB','SC','SD','SE','SF','SG','SH','SJ','SK','SL','SM','SN','SS','ST','SU','SV','SX','SY','SZ',
            'TA','TB','TC','TD','TE','TF','TG','TH','TJ','TK','TL','TM','TN','TS','TT','TU','TV','TX','TY','TZ',
            'UA','UB','UC','UD','UE','UF','UG','UH','UJ','UK','UL','UM','UN','US','UT','UU','UV','UX','UY','UZ',
            'VA','VB','VC','VD','VE','VF','VG','VH','VJ','VK','VL','VM','VN','VS','VT','VU','VV','VX','VY','VZ',
            'XA','XB','XC','XD','XE','XF','XG','XH','XJ','XK','XL','XM','XN','XS','XT','XU','XV','XX','XY','XZ',
            'YA','YB','YC','YD','YE','YF','YG','YH','YJ','YK','YL','YM','YN','YS','YT','YU','YV','YX','YY','YZ',
            'ZA','ZB','ZC','ZD','ZE','ZF','ZG','ZH','ZJ','ZK','ZL','ZM','ZN','ZS','ZT','ZU','ZV','ZX','ZY','ZZ']


def login(user,password):
    logger.info("logging into PRIM")
    logging.getLogger('suds.client').setLevel(logging.CRITICAL)
    errors = 0
    faults=False
    url = config.get('PRIM', 'primLogin')
    client = Client(url)
    xml = '<?xml version="1.0" encoding="UTF-8"?> <servicecontext.r1.context xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="r1" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/servicecontext/r1 servicecontext_r1.xsd" xmlns:servicecontext.r1="http://pdmservice.ericsson.se/interface/xsd/servicecontext/r1"><userName>PRIMSUER   </userName><userPassword>PRIMPASSWORD  </userPassword><environment>Prod  </environment><callingApplication>ciportal  </callingApplication><callingApplicationVersion>R1A01  </callingApplicationVersion></servicecontext.r1.context>'
    xml = xml.replace("PRIMSUER",user)
    xml = xml.replace("PRIMPASSWORD",password)
    encoded = base64.b64encode(xml)
    retries = 0
    while retries < 10:
        retries += 1
        try:
            login = client.service.createSecurityToken(encoded)
            break
        except Exception as e:
            logger.warning("problem with login" +str(e))
            login = "error"
            if "6 to 8 characters" in str(e) or "not authorized" in str(e) :
                break
            sleep(retries*3)
    return login


def createNewProdRev(productNumber,revision,login):
    xml = '<?xml version="1.0" encoding="UTF-8"?> <CreateAndCopyProductInformation.r1.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1 CreateAndCopyProductInformation_r1.xsd" xmlns:CreateAndCopyProductInformation.r1="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1" type="request">  <request serviceversion="R1" operation="createProductRstate" service="CreateAndCopyProductInformation">    <createProductRstate.input.row><ProductNumber>PPPNUMBER</ProductNumber><RState>PPPREVISION</RState><DesignResponsible>BU /CIENCC</DesignResponsible><ReleaseResponsible>BU /CIENCC</ReleaseResponsible>    </createProductRstate.input.row>  </request></CreateAndCopyProductInformation.r1.message>'
    url2 = config.get('PRIM', 'primUrl2')
    client = Client(url2)
    xmlSend = xml.replace("PPPNUMBER",productNumber)
    xmlSend = xmlSend.replace("PPPREVISION",revision)
    result = sendRequest(client, xmlSend, login)
    return result

def createNewStruct(headProductNumber,headRevision,contentList,type,login):
    xml = '<?xml version="1.0" encoding="UTF-8"?> <ProductStructure.r5.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5 ProductStructure_r5.xsd" type="request" xmlns:ProductStructure.r5="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5">  <request serviceversion="R5" operation="createAndRelease" service="ProductStructure">    <createAndRelease.input.head ><HeadProductNumber>PPPNUMBER</HeadProductNumber><HeadRState>PPPREVISION</HeadRState><ProdStrucType>PPPTYPE</ProdStrucType>    </createAndRelease.input.head > PPPCONTENT </request></ProductStructure.r5.message>'
    url2 = config.get('PRIM', 'primUrl2')
    content=""
    for product in contentList:
        (tmpProd,tmpRev)=product
        content=content+"<createAndRelease.input.row ><ProductNumber>"+tmpProd+"</ProductNumber><RStateSelRule>="+tmpRev+"</RStateSelRule><QuantityChar>1</QuantityChar> </createAndRelease.input.row >"
    client = Client(url2)
    xmlSend = xml.replace("PPPNUMBER",headProductNumber)
    xmlSend = xmlSend.replace("PPPREVISION",headRevision)
    xmlSend = xmlSend.replace("PPPTYPE",type)
    xmlSend = xmlSend.replace("PPPCONTENT",content)
    result = sendRequest(client, xmlSend, login)
    return result

def getVersion(rState):
    matchObj = re.search( r'(\D{1})(\d{1,3})(\D{1,2})(\d{0,3})', rState)
    if matchObj.group(4):
        return matchObj.group(2)+"."+str(rbase.index(matchObj.group(3)))+"."+matchObj.group(4)
    else:
        return matchObj.group(2)+"."+str(rbase.index(matchObj.group(3)))

def updatePkgRev(packages):
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=0
    while level < 9:
        table="level_"+str(level)
        for package in packages:
            pNumber= package.package_revision.package.package_number
            pRstate= convertVersionToRState(package.package_revision.version)
            cursor.execute("update "+table+" set changed='0',revision='"+pRstate+"' where not (revision='"+pRstate+"') and productnumber='"+pNumber+"'"),[]
            connection.commit()
        level = level +1


def updateCXC():
    '''
        Update CXC R-State to stay inline with CXP R-State
    '''
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=0
    while level < 9:
        table="level_"+str(level)
        cursor.execute('select * from '+table+' where create_new="1" and  productnumber LIKE "CXP%";', None)
        allChanged= cursor.fetchall()
        for item in allChanged:
            id=str(item[0])
            rev=item[3]
            ver=getVersion(str(rev))
            [majCXP, minCXP, patch] = ver.split(".", 2)
            revCXP = majCXP+"."+minCXP
            nextTable="level_"+str(level+1)
            cursor.execute('select * from '+nextTable+' where parent = '+id+' and productnumber LIKE "CXC%";', None)
            allChangedCXC= cursor.fetchall()
            for cxc in allChangedCXC:
                logger.info("CXC: "+str(cxc))
                number = cxc[2]
                revCXC= cxc[3]
                verCXC=getVersion(str(rev))
                [majCXC, minCXC] = verCXC.split(".", 1)
                if not str(revCXP) == str(revCXC):
                      newMajCXC = majCXP
                      newMinCXC = minCXP
                      newVerCXC = str(newMajCXC) + "." + str(newMinCXC)
                      newRevCXC = str(convertVersionToRState(newVerCXC))
                      cursor.execute("update "+nextTable+" set create_new='1', revision='"+newRevCXC+"' where revision='"+revCXC+"' and productnumber='"+number+"'"),[]
                      connection.commit()
        level = level +1


def getLatestCXPRStateFromPrim(pkgNum,login):
    '''
    Getting Latest RState
    '''
    prodRState = ""
    url2 = config.get('PRIM', 'primUrl2')
    client2 = Client(url2)
    template = '<?xml version="1.0" encoding="UTF-8"?><RetrieveProductData.r3.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdm-service.ericsson.se/interface/xsd/RetrieveProductData/r3 RetrieveProductData_r3.xsd" xmlns:RetrieveProductData.r3="http://pdm-service.ericsson.se/interface/xsd/RetrieveProductData/r3" type="request"><request serviceversion="r3" operation="retrieveProductData" service="RetrieveProductData"><retrieveProductData.input.row><ProductNumber>PPPNUMBER</ProductNumber></retrieveProductData.input.row></request></RetrieveProductData.r3.message>'
    xmlSend = template.replace("PPPNUMBER",  str(pkgNum))
    result2 = sendRequest(client2, xmlSend, login)
    if result2 is not "error":
        try:
            root = ET.fromstring(result2)
            for item in root.getiterator('retrieveProductBasic.output.row'):
                number=item.getiterator('ProductNumber')
                rstate=item.getiterator('RState')
                if rstate[0].text == None:
                    continue
                logger.debug("ProductNumber: " + str(number[0].text))
                logger.debug("RState: " + str(rstate[0].text))
                if number[0].text != None and  number[0].text != " ":
                    prodNum=str(number[0].text).replace(" ","")
                    prodRState=str(rstate[0].text).replace(" ","")
                    if prodRState != None:
                        break
        except Exceprion as e:
            logger.error("Error Retrieving latestRstate: "+str(e))
            prodRState = "error"
        return prodRState
    else:
        return result2



def productInfoFromPRIM(pkgNum, pkgRstate, login):
    url2 = config.get('PRIM', 'primUrl2')
    client2 = Client(url2)
    template = '<?xml version="1.0" encoding="UTF-8"?><RetrieveProductData.r3.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdm-service.ericsson.se/interface/xsd/RetrieveProductData/r3 RetrieveProductData_r3.xsd" xmlns:RetrieveProductData.r3="http://pdm-service.ericsson.se/interface/xsd/RetrieveProductData/r3" type="request"><request serviceversion="r3" operation="retrieveProductData" service="RetrieveProductData"><retrieveProductData.input.row><ProductNumber>PPPNUMBER</ProductNumber><RState>PPPREVISION</RState></retrieveProductData.input.row></request></RetrieveProductData.r3.message>'
    xmlSend = template.replace("PPPNUMBER",  str(pkgNum))
    xmlSend = xmlSend.replace("PPPREVISION", str(pkgRstate))
    result2 = sendRequest(client2, xmlSend, login)
    return result2



def getCXPsFromPrim(product,drop,media, login):
    '''
     Getting the Data from Prim
    '''
    packages = set()
    packagesPrim = []
    diffData = []
    unknownPackagesDB = set()
    msg= ""
    prodRState=""
    prodNum=""
    drp = Drop.objects.get(name=drop, release__product__name=product)
    isoRevision = ISObuild.objects.only('id').values('id').get(version=media, drop=drp, mediaArtifact__testware=False, mediaArtifact__category__name="productware")
    isoRevMappingField =('package_revision__version', 'package_revision__package__package_number',)
    isoRevMapping = ISObuildMapping.objects.only(isoRevMappingField).values(*isoRevMappingField).filter(iso__id=isoRevision['id'])
    for isoDetails in isoRevMapping:
        pkgRstate = str(convertVersionToRState(str(isoDetails['package_revision__version'])))
        pkgNum = str(isoDetails['package_revision__package__package_number'])
        if 'CXP' in pkgNum or 'APR' in pkgNum or 'CXC' in pkgNum:
            try:
                result = productInfoFromPRIM(pkgNum, pkgRstate, login)
            except Exception as e:
                logger.error("Error getting product Info From PRIM for Number "+ str(pkgNum) + ": " + str(e))
                unknownPackagesDB.add("<td id='missing_"+str(pkgNum)+"' class='missingprim'>"+ pkgNum + " </td> <td id='missing_"+str(pkgRstate)+"' class='missingprim'> " + pkgRstate +"</td>")
                result = "error"
            if result is not "error":
                root = ET.fromstring(result)
                for item in root.getiterator('retrieveProductBasic.output.row'):
                    number=item.getiterator('ProductNumber')
                    logger.info("ProductNumber: " + str(number[0].text))
                    if number[0].text != None and  number[0].text != " ":
                        prodNum=str(number[0].text).replace(" ","")
                        if root.getiterator('retrieveProductRstate.message'):
                            for itemMsg in root.getiterator('retrieveProductRstate.message'):
                                message=itemMsg.getiterator('Message')
                                msg=str(message[0].text)
                                if prodNum == pkgNum and "DOES NOT EXIST" in msg:
                                    prodRState = getLatestCXPRStateFromPrim(pkgNum,login)
                                    if prodRState == "error":
                                        prodRState = ""
                                    packagesPrim.append("<td id='number_"+str(prodNum)+"'>" + prodNum + "</td> <td id='"+str(prodNum)+"_crstate_"+str(prodRState)+"'>" +str(prodRState)+"</td>" )
                                    diffData.append("<td id='"+str(prodNum)+"_nrstate_"+str(pkgRstate)+"' class='alteredprim'>"+ pkgRstate +"</td>")
                                    packages.add(pkgNum + "-" + pkgRstate)
                    else:
                        for missingMsg in root.getiterator('retrieveProductBasic.message'):
                            message=missingMsg.getiterator('Message')
                            msg=str(message[0].text)
                            logger.error("Error Message from Prim: " + str(msg))
                            if "DOES NOT EXIST" in msg:
                                unknownPackagesDB.add("<td id='missing_"+str(pkgNum)+"' class='missingprim'>"+ pkgNum + " </td> <td id='missing_"+str(pkgRstate)+"' class='missingprim'> " + pkgRstate +"</td>")
    return packagesPrim, diffData, unknownPackagesDB, packages

def updateCXPs(product,drop,media, login, packages):
    '''
     Getting data Ready for prim
    '''
    write = ""
    drp = Drop.objects.get(name=drop, release__product__name=product)
    isoRevision = ISObuild.objects.only('id').values('id').get(version=media, drop=drp, mediaArtifact__testware=False, mediaArtifact__category__name="productware")
    isoRevMappingField = ('iso__version', 'package_revision__package__package_number', 'drop__name',)
    isoRevMapping = ISObuildMapping.objects.only(isoRevMappingField).values(*isoRevMappingField).filter(iso__id=isoRevision['id'])
    for isoDetails in isoRevMapping:
        pkgNum = isoDetails['package_revision__package__package_number']
        if 'CXP' in pkgNum or 'APR' in pkgNum or 'CXC' in pkgNum:
            for package in packages:
                [number, revision] = package.split("-")
                if pkgNum == number:
                    deliverTo = str(isoDetails['drop__name']) + " " + str(isoDetails['iso__version'])
                    write = writeCXP(number,revision,deliverTo,login)
    if write is "error":
        result="error"
    else:
        result=""

    return result



def writeCXP(productNumber,revision,text,login):
    '''
      Writing the New RStates to PRIM
    '''
    try:
        url2 = config.get('PRIM', 'primUrl2')
        client2 = Client(url2)
        template='<?xml version="1.0" encoding="UTF-8"?> <CreateAndCopyProductInformation.r1.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1 CreateAndCopyProductInformation_r1.xsd" xmlns:CreateAndCopyProductInformation.r1="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1" type="request">  <request serviceversion="r1" operation="createProductInformation" service="CreateAndCopyProductInformation">    <createProductInformation.input.row><RowService>createProductRstate</RowService><ProductNumber>PPPNUMBER</ProductNumber><RState>PPPREVISION</RState><ObjectType>ProductIssue</ObjectType><TextType>Version Designation Text</TextType><LanguageCode>EN</LanguageCode><TextStatus>E</TextStatus><InformationText>PPPTEXT</InformationText> <DesignResponsible>BU /CIENCC</DesignResponsible><ReleaseResponsible>BU /CIENCC</ReleaseResponsible> </createProductInformation.input.row>  </request></CreateAndCopyProductInformation.r1.message>'
        xmlSend = template.replace("PPPNUMBER",productNumber)
        xmlSend = xmlSend.replace("PPPREVISION",revision)
        result2 = sendRequest(client2, xmlSend, login)
    except Exception as e:
        logger.error("Error writing CXP to prim: "+str(e))
        result2="error"
    if result2 is not "error":
        try:
            template='<?xml version="1.0" encoding="UTF-8"?> <CreateAndCopyProductInformation.r1.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1 CreateAndCopyProductInformation_r1.xsd" xmlns:CreateAndCopyProductInformation.r1="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1" type="request">  <request serviceversion="r1" operation="createProductInformation" service="CreateAndCopyProductInformation">    <createProductInformation.input.row><RowService>createProductText</RowService><ProductNumber>PPPNUMBER</ProductNumber><RState>PPPREVISION</RState><ObjectType>ProductIssue</ObjectType><TextType>Version Designation Text</TextType><LanguageCode>EN</LanguageCode><TextStatus>E</TextStatus><InformationText>PPPTEXT</InformationText>    </createProductInformation.input.row>  </request></CreateAndCopyProductInformation.r1.message>'
            xmlSend = template.replace("PPPNUMBER",productNumber)
            xmlSend = xmlSend.replace("PPPREVISION",revision)
            xmlSend = xmlSend.replace("PPPTEXT",text)
            result3 = sendRequest(client2, xmlSend, login)
        except Exception as e:
            logger.error("Error writing CXP to prim: "+str(e))
            result3="error"
        return result3
    else:
        return result2


def checkUpdateResults(packages, login):
    '''
     checking that PRIM was Updated with New RState
    '''
    primReport = set()
    failed = ""
    try:
        for package in packages:
            [number, rstate] = package.split("-")
            result2 = productInfoFromPRIM(number, rstate, login)
            if result2 is not "error":
                root = ET.fromstring(result2)
                for item in root.getiterator('retrieveProductBasic.output.row'):
                    pnumber=item.getiterator('ProductNumber')
                    if pnumber[0].text != None and  pnumber[0].text != " ":
                        prodNum=str(pnumber[0].text).replace(" ","")
                        if root.getiterator('retrieveProductRstate.message'):
                            for itemMsg in root.getiterator('retrieveProductRstate.message'):
                                message=itemMsg.getiterator('Message')
                                msg=str(message[0].text)
                                if prodNum == number and "DOES NOT EXIST" in msg:
                                    logger.error("Error Issue adding New RState to Prim: " + str(package))
                                    failed = True
                                    primReport.add("<td id='number_"+str(number)+"'>" + number + "</td> <td id='"+str(number)+"_nrstate_"+str(rstate)+"'>" +str(rstate)+"</td><td id='result_"+str(number)+"' class='missingprim'> Failed </td>" )
                        else:
                            primReport.add("<td id='number_"+str(number)+"'>" + number + "</td> <td id='"+str(number)+"_nrstate_"+str(rstate)+"'>" +str(rstate)+"</td> <td id='result_"+str(number)+"' class='alteredprim'> Successful </td>" )
        if not primReport:
            logger.error("Error Issue getting Data from Prim, using : " + str(packages))
            failed = "error"
    except Exception as e:
            logger.error("Error checking PRIM update: "+str(e))
            failed = "error"

    return primReport, failed


def stepRevAndStore(new=True, rState=None):
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=0
    while level < 9:
        table="level_"+str(level)
        cursor.execute("select * from "+table+" where changed ='1'")
        allChanged= cursor.fetchall()
        for item in allChanged:
            rev=item[3]
            ver=getVersion(str(rev))
            if level == 0 and rState != None:
                newRev = rState
            elif new==False:
                try:
                    [maj, min, patch] = ver.split(".", 2)
                    patchN=int(patch)+1
                    newRev = str(convertVersionToRState(str(maj)+"."+str(min)+"."+str(patchN)))
                except:
                    [maj, min] = ver.split(".", 1)
                    minN=int(min)+1
                    newRev = str(convertVersionToRState(str(maj)+"."+str(minN)))
            else:
                try:
                    [maj, min, patch] = ver.split(".", 2)
                    minN=int(min)+1
                    newRev = str(convertVersionToRState(str(maj)+"."+str(minN)+".1"))
                except:
                    [maj, min] = ver.split(".", 1)
                    majN=int(maj)+1
                    newRev = str(convertVersionToRState(str(majN)+".0"))
            logger.info("Old Revision: "+str(rev)+" New Revision: "+str(newRev))
            cursor.execute("update "+table+" set changed='0',revision='"+newRev+"' where revision='"+str(rev)+"' and productnumber='"+str(item[2])+"'"),[]
            connection.commit()
        level = level +1


def createDirForPrimSqlFiles():
    result = ""
    try:
        directory=os.path.exists("/tmp/prim")
        if not directory:
            subprocess.call(["mkdir", "/tmp/prim"])
            logger.info("Prim Directory Created")
        else:
            logger.info("Prim Directory already created")
    except:
        logger.error("Error when creating Prim Directory")
        result = "error"
    return result

def storeDataInFile(username):
    '''
    Storing the Data from the Temp database tables in a sql file
    '''
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    try:
        cursor = connection.cursor()
        level= 0
        data = ""
        sqlFile = ""
        while level < 9:
            table="level_"+str(level)
            cursor.execute("select * from "+table)
            for row in cursor.fetchall():
                data += "INSERT INTO `" + str(table) + "` VALUES("
                first = True
                for field in row:
                    if not first:
                        data += ', '
                    data += '"' + str(field) + '"'
                    first = False
                data += ");\n"
            data += "\n\n"
            level = level +1
        now = datetime.datetime.now()
        stamp = str(now).replace(" ", "_")
        filename = str(config.get("DATA_STORED", "prim_tmp")) + "/"+str(username)+"_"+str(stamp)+"_prim.sql"
        logger.info("Data Stored Here: "+str(filename))
        sqlFile = str(username)+"_"+str(stamp)+"_prim.sql"
        logger.info("Sql File : "+str(sqlFile))
        FILE = open(filename,"w")
        FILE.writelines(data)
        FILE.close()
    except Exception as e:
        logger.error("Problem Creating File : " +str(username)+"_prim.sql, Exception : " + str(e))
        sqlFile = "error"
    return sqlFile


def importDataFromFile(username, file):
    '''
    Importing the data from sql file into temp tables for writing to prim
    '''
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    result = ""
    try:
        cursor = connection.cursor()
        directory=str(config.get("DATA_STORED", "prim_tmp"))
        filename = directory + "/" + file
        file = open(filename,'r')
        sql = file.read()
        cursor.execute(sql)
        logger.info("Imported Data into Tables")
    except Exception as e:
        logger.error("Problem Importing Data into Tables from file: " +file+" , Exception : " + str(e))
        result = "error"
    return result


def deleteSqlFile(username, file=None):
    '''
    Deleting the sql file after using it or deleting sql files that are linked to the username.
    '''
    result = ""
    if file != None:
        try:
            directory=str(config.get("DATA_STORED", "prim_tmp"))
            os.chdir(directory)
            logger.info("Deleting Sql File: " +file)
            files=glob.glob(file)
            for filename in files:
                os.unlink(filename)
        except Exception as e:
            logger.error("Problem Deleting Sql File: " +file+", Exception : " + str(e))
            result = "error"
    else:
        sqlfile = ""
        try:
            directory=str(config.get("DATA_STORED", "prim_tmp"))
            os.chdir(directory)
            logger.info("Deleting Sql Files with username: " +username)
            sqlfile = str(username)+"_*_prim.sql"
            files=glob.glob(sqlfile)
            for filename in files:
                os.unlink(filename)
        except Exception as e:
            logger.error("Problem Deleting Sql File: " +str(sqlfile)+", Exception : " + str(e))
            result = "error"
    return result


def findChangedAll(packages):
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=0
    while level < 9:
        table="level_"+str(level)
        for package in packages:
            pNumber= package.package_revision.package.package_number
            pRstate= convertVersionToRState(package.package_revision.version)
            cursor.execute("update "+table+" set changed='1', create_new='1' where not (revision='"+pRstate+"') and productnumber='"+pNumber+"'"),[]
            connection.commit()
        level = level +1

def updateParents():
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=9
    while level > 0:
        table="level_"+str(level)
        parentTable="level_"+str(level-1)
        logger.info("updating table: "+str(parentTable)+" Setting flag where children have been updated")
        cursor.execute("UPDATE "+parentTable+" p, "+table+" t SET p.changed = '1',p.create_new = '1' WHERE p.id = t.parent AND t.changed = '1'"),[]
        connection.commit()
        level = level -1


def getAll(productNumber,revision,login,level,id,strType="13161-"):
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    logger.info("Fetching base product structure from PRIM")
    template='<?xml version="1.0" encoding="UTF-8"?><ProductStructure.r6.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r6 ProductStructure_r6.xsd" xmlns:ProductStructure.r6="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r6" type="request"> <request serviceversion="r6" operation="retrieveProductStructure" service="ProductStructure"><retrieveProductStructure.input.head><HeadProductNumber>PPPNUMBER</HeadProductNumber><HeadRState>PPPREVISION</HeadRState><ProdStrucType>PPPSTRTYPE</ProdStrucType></retrieveProductStructure.input.head></request></ProductStructure.r6.message>'
    url2 = config.get('PRIM', 'primUrl2')
    client2 = Client(url2)
    xmlSend = template.replace("PPPNUMBER",productNumber)
    xmlSend = xmlSend.replace("PPPREVISION",revision)
    xmlSend = xmlSend.replace("PPPSTRTYPE",strType)
    result2 = sendRequest(client2, xmlSend, login)
    if result2 is not "error":
        root = ET.fromstring(result2)
        for item in root.getiterator('output.row'):
            number=item.getiterator('ProductNumber')
            rState=item.getiterator('RStateSelection')
            logger.info("ProductNumber: " + str(number[0].text))
            if number[0].text != None and  number[0].text != " ":
                table="level_"+str(level)
                parentTable="level_"+str(level-1)
                parentNum=productNumber.replace(" ","")
                parentRstate=revision
                prodNum=str(number[0].text).replace(" ","")
                prodRev=str(rState[0].text)
                idInt=str(id)
                if "CXP" in prodNum:
                    cursor.execute("INSERT INTO "+table+"(parent,productnumber,revision,type) VALUES(%s,%s,%s,%s)",[idInt,prodNum,prodRev,"13132-"])
                    connection.commit()
                else:
                    cursor.execute("INSERT INTO "+table+"(parent,productnumber,revision,type) VALUES(%s,%s,%s,%s)",[idInt,prodNum,prodRev,strType])
                    connection.commit()
                idNew= cursor.lastrowid
            if number[0].text == " " and strType=="13161-":
               logger.error("ProductNumber Returned as blank string not None")
               getAll(productNumber,revision,login,level,id, "13132-")
               continue
            elif number[0].text is None and strType=="13161-":
               getAll(productNumber,revision,login,level,id, "13132-")
               continue
            elif number[0].text is None:
                continue
            elif number[0].text ==" ":
                logger.error("ProductNumber returned as blank string not a None")
                continue
            level=level+1
            getAll(number[0].text,rState[0].text,login,level,idNew)
            level=level-1
    return result2

def createProducts(drop,media,login,write):
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    newRes=""
    vdtRes=""
    level=0
    while level < 9:
        table="level_"+str(level)
        cursor.execute("select * from "+table+" where create_new ='1'")
        allUpdated= cursor.fetchall()
        for item in allUpdated:
            rev=item[3]
            prodNumber=item[2]
            logger.info("Creating Product: "+str(prodNumber) + " Revision: "+str(rev))
            if write == True:
                logger.info("Writing to PRIM")
                newRes=createNewProdRev(str(prodNumber),str(rev),login)
                deliverTo = str(drop) + " " + str(media)
                vdtRes=writeVDT(str(prodNumber),str(rev),deliverTo,login)
            else:
                logger.info("Write Flag not set. Not writing to PRIM")
        level = level+1
    if newRes is "error" or vdtRes is "error":
        result="error"
    else:
        result=""
    return result

def createStructure(login,write):
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    result=""
    cursor = connection.cursor()
    level=0
    while level < 9:
        table="level_"+str(level)
        cursor.execute("select * from "+table )
        all= cursor.fetchall()
        for item in all:
            id=item[0]
            type=str(item[4])
            parent=str(item[2])
            parentRev=str(item[3])
            nextTable="level_"+str(level+1)
            cursor.execute("select * from "+nextTable+" where  parent='"+str(id)+"'")
            allChild=cursor.fetchall()
            contentList = []
            for child in allChild:
                product =str(child[2])
                rev =str(child[3])
                contentList.append((product,rev))
            if contentList !=[]:
                logger.info("creating product structure for "+parent+":"+parentRev+":"+type)
                logger.info(contentList)
                if write == True:
                    logger.info("Writing to PRIM")
                    result=createNewStruct(parent,parentRev,contentList,type,login)
                else:
                    logger.info("Write Flag not set. Not writing to PRIM")
        level = level+1
    return result

def writeVDT(productNumber,revision,text,login):
    template='<?xml version="1.0" encoding="UTF-8"?> <CreateAndCopyProductInformation.r1.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1 CreateAndCopyProductInformation_r1.xsd" xmlns:CreateAndCopyProductInformation.r1="http://pdmservice.ericsson.se/interface/xsd/CreateAndCopyProductInformation/r1" type="request">  <request serviceversion="r1" operation="createProductInformation" service="CreateAndCopyProductInformation">    <createProductInformation.input.row><RowService>createProductText</RowService><ProductNumber>PPPNUMBER</ProductNumber><RState>PPPREVISION</RState><ObjectType>ProductIssue</ObjectType><TextType>Version Designation Text</TextType><LanguageCode>EN</LanguageCode><TextStatus>E</TextStatus><InformationText>PPPTEXT</InformationText>    </createProductInformation.input.row>  </request></CreateAndCopyProductInformation.r1.message>'
    url2 = config.get('PRIM', 'primUrl2')
    client2 = Client(url2)
    xmlSend = template.replace("PPPNUMBER",productNumber)
    xmlSend = xmlSend.replace("PPPREVISION",revision)
    xmlSend = xmlSend.replace("PPPTEXT",text)
    result2 = sendRequest(client2, xmlSend, login)
    return result2

def createTables():
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    logger.info("Creating table: level_0")
    cursor.execute("CREATE TEMPORARY TABLE level_0 (  id smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,parent smallint UNSIGNED NOT NULL DEFAULT 0,   productnumber varchar(50) NOT NULL, revision varchar(50) NOT NULL,type varchar(50) NOT NULL,changed  bool NOT NULL DEFAULT 0, create_new  bool NOT NULL DEFAULT 0) ENGINE=InnoDB",[])

    level=1
    while level < 10:
        table="level_"+str(level)
        logger.info("Creating table: "+table)
        cursor.execute("CREATE TEMPORARY TABLE "+table+" (  id smallint UNSIGNED AUTO_INCREMENT NOT NULL PRIMARY KEY,parent smallint UNSIGNED NOT NULL DEFAULT 0,   productnumber varchar(50) NOT NULL, revision varchar(50) NOT NULL,type varchar(50) NOT NULL,changed  bool NOT NULL DEFAULT 0, create_new  bool NOT NULL DEFAULT 0)ENGINE=InnoDB")
        connection.commit()
        level=level+1


def dropTables():
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=9
    while level != -1:
        table="level_"+str(level)
        logger.info("DROP TABLE IF EXISTS  "+table )
        try:
            cursor.execute("DROP TABLE IF EXISTS  "+table )
            connection.commit()
        except:
            logger.info("Table: "+table+" doesn't exist")
        level = level-1

def returnData():
    '''
    Showing what was taken from Prim before the data is changed.
    '''
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=0
    data=[]
    while level < 9:
        table="level_"+str(level)
        cursor.execute("select * from "+table )
        all= cursor.fetchall()
        for item in all:
            id=item[0]
            type=str(item[4])
            parent=str(item[2])
            parentRev=str(item[3])
            nextTable="level_"+str(level+1)
            cursor.execute("select * from "+nextTable+" where  parent='"+str(id)+"'")
            allChild=cursor.fetchall()
            contentList = []
            for child in allChild:
                product =str(child[2])
                rev =str(child[3])
                change = str(child[5])
                createNew = str(child[6])
                contentList.append((product,rev))
            if contentList !=[]:
                dotsParent = int(level-1)
                dotsStringParent=""
                while dotsParent >-1:
                    dotsStringParent += "."
                    dotsParent=dotsParent-1
                data.append("<td><b>"+dotsStringParent+"|P|</b> "+parent+"</td><td>"+parentRev+"</td>")
                dots = int(level)
                dotsString=""
                while dots !=0:
                    dotsString += "."
                    dots=dots-1
                for product in contentList:
                    (tmpProd,tmpRev)=product
                    data.append("<td><b>"+dotsString+"</b>"+tmpProd+"</td><td>"+tmpRev+"</td>")
                data.append(" ")
        level = level+1
    return data

def returnChangedData():
    '''
    For after the changes have been made to data in the tables to show what will be written to prim.
    '''
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=0
    data=[]
    while level < 9:
        table="level_"+str(level)
        cursor.execute("select * from "+table )
        all= cursor.fetchall()
        for item in all:
            id=item[0]
            type=str(item[4])
            parent=str(item[2])
            parentRev=str(item[3])
            parentChange = int(item[5])
            parentCreateNew = int(item[6])
            nextTable="level_"+str(level+1)
            cursor.execute("select * from "+nextTable+" where  parent='"+str(id)+"'")
            allChild=cursor.fetchall()
            changeList = []
            contentList = []
            for child in allChild:
                product =str(child[2])
                rev =str(child[3])
                change = int(child[5])
                createNew = int(child[6])
                contentList.append((product,rev))
                changeList.append((change,createNew))
            if contentList !=[]:
                dotsParent = int(level-1)
                dotsStringParent=""
                while dotsParent >-1:
                    dotsStringParent += "."
                    dotsParent=dotsParent-1
                if parentCreateNew == 1 or parentChange == 1:
                    if parentCreateNew == 1:
                        data.append("<td class='alteredprim'>"+parentRev+"</td>")
                    else:
                        data.append("<td class='changeprim'>"+parentRev+"</td>")
                else:
                    data.append("<td></td>")
                dots = int(level)
                dotsString=""
                while dots !=0:
                    dotsString += "."
                    dots=dots-1
                for product, change in zip(contentList, changeList):
                    (tmpProd,tmpRev)=product
                    (tmpCha, tmpNew)=change
                    if tmpNew == 1 or tmpCha == 1:
                      if tmpNew == 1:
                            data.append("<td class='alteredprim'>"+tmpRev+"</td>")
                      else:
                            data.append("<td class='changeprim'>"+tmpRev+"</td>")
                    else:
                           data.append("<td>  </td>")
                data.append(" ")
        level = level+1
    return data

def differences(packages):
    '''
    Differences between Prim and CI Fwk Database
    '''
    try:
        cursor.close()
    except:
        logger.debug("Not Open")
    cursor = connection.cursor()
    level=0
    data= set()
    prim = set()
    db = set()
    for pN in packages:
        db.add(str(pN.package_revision.package.package_number))
    while level < 9:
        table="level_"+str(level)
        cursor.execute("select * from "+table )
        all= cursor.fetchall()
        for item in all:
            nextTable="level_"+str(level+1)
            cursor.execute('select * from '+nextTable+' where productnumber LIKE "CXP%";', None)
            allChild=cursor.fetchall()
            for child in allChild:
                product =str(child[2])
                rev =str(child[3])
                prim.add(product)
                if not product in db:
                    data.add("<td class='missingprim'>"+ product+ "</td><td class='missingprim'> "+rev+"</td>")

        level = level+1
    for pN in packages:
        product = str(pN.package_revision.package.package_number)
        rev = str(convertVersionToRState(pN.package_revision.version))
        if not product in prim:
            data.add("<td class='newprim'>"+ product +"</td><td class='newprim'>"+rev+"</td>")
    return data

def sendRequest(client, xmlSend, login):
    retries = 0
    while retries < 10:
        retries += 1
        try:
            result = client.service.doOperation(xmlSend, login)
            break
        except Exception as e:
            logger.warning("problem with request: " +str(e))
            sleep(retries*3)
            result = "error"
    return result

