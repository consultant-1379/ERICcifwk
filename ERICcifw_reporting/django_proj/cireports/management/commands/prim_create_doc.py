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
        url = 'http://pdm-service-acc.ericsson.se/pdmservice/services/Login?WSDL'
        client = Client(url)
        xml = '<?xml version="1.0" encoding="UTF-8"?> <servicecontext.r1.context xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="r1" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/servicecontext/r1 servicecontext_r1.xsd" xmlns:servicecontext.r1="http://pdmservice.ericsson.se/interface/xsd/servicecontext/r1"><userName>PRIMSUER   </userName><userPassword>PRIMPASSWORD  </userPassword><environment>Accept  </environment><callingApplication>pdmtool  </callingApplication><callingApplicationVersion>R3A08  </callingApplicationVersion></servicecontext.r1.context>'
        xml = xml.replace("PRIMSUER",user)
        xml = xml.replace("PRIMPASSWORD",password)
        encoded = base64.b64encode(xml)
        result = client.service.createSecurityToken(encoded)
        print result
        xml2 = '<?xml version="1.0" encoding="UTF-8"?><CreateDocumentRevision.r1.message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pdmservice.ericsson.se/interface/xsd/CreateDocumentRevision/r1 CreateDocumentRevision_r1.xsd" xmlns:CreateDocumentRevision.r1="http://pdmservice.ericsson.se/interface/xsd/CreateDocumentRevision/r1" type="request"> <request serviceversion="R3A" operation="createDocumentRevision" service="CreateDocumentRevision"><createDocumentRevision.input.row><DocumentNumber>1551-ABC1234568/1</DocumentNumber><DocumentRevision>B</DocumentRevision><LanguageCode>EN</LanguageCode><NewDocumentFlag>no</NewDocumentFlag><ADPArchive>CLEARCASE/SEHUB/1/LXF10305</ADPArchive></createDocumentRevision.input.row></request></CreateDocumentRevision.r1.message>'
        url2 = 'http://pdm-service-acc.ericsson.se/pdmservice/services/Router?WSDL'
        client2 = Client(url2)
        result2 = client2.service.doOperation(xml2, result)
        print result2
