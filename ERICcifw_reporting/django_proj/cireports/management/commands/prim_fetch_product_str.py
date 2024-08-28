from django.core.management.base import BaseCommand, CommandError
import sys
import base64
import logging
import traceback as tb
import suds.metrics as metrics
from tests import *
from suds import WebFault
from suds.client import Client
from ciconfig import CIConfig
config = CIConfig()
import xml.etree.ElementTree as ET
from django.db import connection

cursor = connection.cursor()


logging.getLogger('suds.client').setLevel(logging.CRITICAL)
errors = 0

logger = logging.getLogger(__name__)
class Command(BaseCommand):

    def handle(self, *args, **options):
        user = config.get("CIFWK", "primUser")
        password = config.get("CIFWK", "primPassword")
        logging.getLogger('suds.client').setLevel(logging.CRITICAL)
        errors = 0
        faults=False
        #url = 'http://pdm-service-acc.ericsson.se/pdmservice/services/Login?WSDL'
        url = 'http://pdm-service.ericsson.se/pdmservice/services/Login?WSDL'
        client = Client(url)
        xml = '<?xml version="1.0" encoding="UTF-8"?> <servicecontext.r1.context xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="r1" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/servicecontext/r1 servicecontext_r1.xsd" xmlns:servicecontext.r1="http://pdmservice.ericsson.se/interface/xsd/servicecontext/r1"><userName>PRIMSUER   </userName><userPassword>PRIMPASSWORD  </userPassword><environment>Prod  </environment><callingApplication>pdmtool  </callingApplication><callingApplicationVersion>R3A08  </callingApplicationVersion></servicecontext.r1.context>'
        xml = xml.replace("PRIMSUER",user)
        xml = xml.replace("PRIMPASSWORD",password)
        encoded = base64.b64encode(xml)
        login = client.service.createSecurityToken(encoded)
        print login
        print "****************************************"
        print "****************************************"
        print "***************logged in****************"
        print "****************************************"
        print "****************************************"
        #yypxml2 = '<?xml version="1.0" encoding="UTF-8"?><DocumentStatus.r1.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/DocumentStatus/r1 DocumentStatus_r1.xsd" xmlns:DocumentStatus.r1="http://pdmservice.ericsson.se/interface/xsd/DocumentStatus/r1" type="request"> <request serviceversion="R1" operation="getDocumentStatus" service="DocumentStatus"><getDocumentStatus.input.row><DocumentNumber>1551-ABC1234567/1</DocumentNumber><DocumentRevision>A</DocumentRevision><LanCode>EN</LanCode></getDocumentStatus.input.row></request></DocumentStatus.r1.message>'
        #xml2 = '<?xml version="1.0" encoding="UTF-8"?><DocumentStatus.r1.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/DocumentStatus/r1 DocumentStatus_r1.xsd" xmlns:DocumentStatus.r1="http://pdmservice.ericsson.se/interface/xsd/DocumentStatus/r1" type="request"> <request serviceversion="R1" operation="getDocumentStatus" service="DocumentStatus"><getDocumentStatus.input.row><DocumentNumber>1551-ABC1234567/1</DocumentNumber><DocumentRevision>A</DocumentRevision><LanCode>EN</LanCode></getDocumentStatus.input.row></request></DocumentStatus.r1.message>'

        #xml2='<?xml version="1.0" encoding="UTF-8"?><ProductStructure.r5.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5 ProductStructure_r5.xsd"xmlns:ProductStructure.r5="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5"type="request"> <request serviceversion="r5" operation="retrieveProductStructure" service="ProductStructure"><retrieveProductStructureinput.head><HeadProductNumber>ABC204001</HeadProductNumber><HeadRState>R1A</HeadRState><ProdStrucType>13161-</ProdStrucType><ProdStrucRevision>A</ProdStrucRevision><RStateSelectionType>DP</RStateSelectionType><DesignCodeWG5>DS2</DesignCodeWG5><ReleaseCodeWG5>PRA</ReleaseCodeWG5><RECodeWG5>RE1</RECodeWG5></retrieveProductStructureinput.head></request></ProductStructure.r5.message>'
        #url2 = 'http://pdm-service-acc.ericsson.se/pdmservice/services/Router?WSDL'
        #workingxml2='<?xml version="1.0" encoding="UTF-8"?><ProductStructure.r5.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5 ProductStructure_r5.xsd" xmlns:ProductStructure.r5="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5" type="request"> <request serviceversion="r5" operation="retrieveProductStructure" service="ProductStructure"><retrieveProductStructureinput.head><HeadProductNumber>ABC204001</HeadProductNumber><HeadRState>R1A</HeadRState><ProdStrucType>13161-</ProdStrucType><ProdStrucRevision>A</ProdStrucRevision><RStateSelectionType>DP</RStateSelectionType><DesignCodeWG5>DS2</DesignCodeWG5><ReleaseCodeWG5>PRA</ReleaseCodeWG5><RECodeWG5>RE1</RECodeWG5></retrieveProductStructureinput.head></request></ProductStructure.r5.message>'
        #template='<?xml version="1.0" encoding="UTF-8"?><ProductStructure.r5.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5 ProductStructure_r5.xsd" xmlns:ProductStructure.r5="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5" type="request"> <request serviceversion="r5" operation="retrieveProductStructure" service="ProductStructure"><retrieveProductStructure.input.head><HeadProductNumber>PPPNUMBER</HeadProductNumber><HeadRState>PPPREVISION</HeadRState><ProdStrucType>13161-</ProdStrucType><RStateSelectionType>DP</RStateSelectionType><DesignCodeWG5>DS2</DesignCodeWG5><ReleaseCodeWG5>PRA</ReleaseCodeWG5></retrieveProductStructure.input.head></request></ProductStructure.r5.message>'
        #url2 = 'http://pdm-service.ericsson.se/pdmservice/services/Router?WSDL'
        #client2 = Client(url2)
        #getAll("test")
        #xmlSend = template.replace("PPPNUMBER","AOM 901 112")
        #print xmlSend
        #xmlSend = xmlSend.replace("PPPREVISION","R1A01")
        #result2 = client2.service.doOperation(xmlSend, result)
        #print result2
        #root = ET.fromstring(result2)
        #print "****************************************"
        #print "****************************************"
        #for item in root.getiterator('output.row'):
        #    number=item.getiterator('ProductNumber')
        #    rState=item.getiterator('RStateSelection')
        #    if number.text is None:
       #         continue
       #     xmlSend = template.replace("PPPNUMBER",number.text)
       #     xmlSend = xmlSend.replace("PPPREVISION",rState.text)
#
        topProduct = "AOM 901 112"
        topRev = "R1A01" 
        cursor.execute("INSERT INTO level_0(productnumber,revision) VALUES(%s,%s)",[topProduct.replace(" ",""),topRev])
        connection.commit()
        print cursor.lastrowid
        #cursor.execute("REPLACE INTO level_0 (productnumber,revision) SELECT * FROM (SELECT 'test', 'r1A1') AS tmp WHERE NOT EXISTS (    SELECT productnumber,revision FROM level_0 WHERE productnumber = 'test' AND revision = 'r1A1') LIMIT 1",[])
        connection.commit()
        id= cursor.lastrowid
        #print xx
        #sys.exit()
        getAll("AOM 901 112","R1A01",login,1,id)
            

def getAll(productNumber,revision,login,level,id,strType="13161-"):
    #print "num"+str(productNumber) + " rev:" +str(revision) + "level:" +str(level) +" typ"+str(strType)
    #template='<?xml version="1.0" encoding="UTF-8"?><ProductStructure.r5.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5 ProductStructure_r5.xsd" xmlns:ProductStructure.r5="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5" type="request"> <request serviceversion="r5" operation="retrieveProductStructure" service="ProductStructure"><retrieveProductStructure.input.head><HeadProductNumber>PPPNUMBER</HeadProductNumber><HeadRState>PPPREVISION</HeadRState><ProdStrucType>13161-</ProdStrucType><RStateSelectionType>DP</RStateSelectionType><DesignCodeWG5>DS2</DesignCodeWG5><ReleaseCodeWG5>PRA</ReleaseCodeWG5></retrieveProductStructure.input.head></request></ProductStructure.r5.message>'
    template='<?xml version="1.0" encoding="UTF-8"?><ProductStructure.r5.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5 ProductStructure_r5.xsd" xmlns:ProductStructure.r5="http://pdmservice.ericsson.se/interface/xsd/ProductStructure/r5" type="request"> <request serviceversion="r5" operation="retrieveProductStructure" service="ProductStructure"><retrieveProductStructure.input.head><HeadProductNumber>PPPNUMBER</HeadProductNumber><HeadRState>PPPREVISION</HeadRState><ProdStrucType>PPPSTRTYPE</ProdStrucType></retrieveProductStructure.input.head></request></ProductStructure.r5.message>'
    url2 = 'http://pdm-service.ericsson.se/pdmservice/services/Router?WSDL'
    client2 = Client(url2)
    xmlSend = template.replace("PPPNUMBER",productNumber)
    #print xmlSend
    xmlSend = xmlSend.replace("PPPREVISION",revision)
    xmlSend = xmlSend.replace("PPPSTRTYPE",strType)
    result2 = client2.service.doOperation(xmlSend, login)
    #print result2
    root = ET.fromstring(result2)
    #print "****************************************"
    #print "****************************************"
    for item in root.getiterator('output.row'):
        number=item.getiterator('ProductNumber')
        rState=item.getiterator('RStateSelection')
        if number[0].text != None and  number[0].text != " ":
            print "--" +str(productNumber) + "-"+str(level) + " ***: "+str(number[0].text) +"----:"+str(rState[0].text)
            table="level_"+str(level)
            parentTable="level_"+str(level-1)
            parentNum=productNumber.replace(" ","")
            parentRstate=revision
            prodNum=str(number[0].text).replace(" ","")
            print "________________"+prodNum
            prodRev=str(rState[0].text)
            #cursor.execute(
            #    '''
            #INSERT INTO %s (parent,productnumber,revision) SELECT * FROM (SELECT (SELECT id FROM %s WHERE productnumber = %s AND revision = %s),%s, %s) AS tmp WHERE NOT EXISTS (SELECT parent, productnumber,revision FROM %s WHERE parent = (SELECT id FROM %s WHERE productnumber = %s AND revision = %s) AND productnumber = %s AND revision = %s) LIMIT 1
             #   ''',[table,parentTable,parentNum,parentRstate,prodNum,prodRev,table,parentTable,parentNum,parentRstate,prodNum,prodRev])
            print       "INSERT INTO "+table+" (parent,productnumber,revision)" +  "SELECT * FROM (SELECT (SELECT id FROM '"+parentTable+"' WHERE productnumber = '"+parentNum+"' AND revision = '"+parentRstate+"'),'"+prodNum+"', '"+prodRev+"') AS tmp "+"WHERE NOT EXISTS ("+ "SELECT parent, productnumber,revision FROM "+table+" WHERE parent = (SELECT id FROM '"+parentTable+"' WHERE productnumber = '"+parentNum+"' AND revision = '"+parentRstate+"') AND productnumber = '"+prodNum+"' AND revision = '"+prodRev+"') LIMIT 1"
            #cursor.execute(
            #    "INSERT INTO "+table+" (parent,productnumber,revision)" +
            #    "SELECT * FROM (SELECT (SELECT id FROM "+parentTable+" WHERE productnumber = '"+parentNum+"' AND revision = '"+parentRstate+"'),'"+prodNum+"', '"+prodRev+"') AS tmp "+
#"WHERE NOT EXISTS ("+
    #"SELECT parent, productnumber,revision FROM "+table+" WHERE parent = (SELECT id FROM "+parentTable+" WHERE productnumber = '"+parentNum+"' AND revision = '"+parentRstate+"') AND productnumber = '"+prodNum+"' AND revision = '"+prodRev+"') LIMIT 1",[])
            idInt=str(id)
            print idInt
            cursor.execute("INSERT INTO "+table+"(parent,productnumber,revision) VALUES(%s,%s,%s)",[idInt,prodNum,prodRev])
            connection.commit()
            idNew= cursor.lastrowid



        if number[0].text is None and strType=="13161-":
            getAll(productNumber,revision,login,level,id, "13132-")
            continue
        elif number[0].text is None:
            continue
        elif number[0].text ==" ":
            continue

        level=level+1
        getAll(number[0].text,rState[0].text,login,level,idNew)
        level=level-1
    
