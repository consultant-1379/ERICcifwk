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
import cireports.models
import cireports.utils


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
        #sys.exit()
        drp = cireports.models.Drop.objects.get(name='1.0.12')
        packages = cireports.utils.getPackageBaseline(drp)
        findChangedAll(packages)
        updateParents()
            

def findChangedAll(packages):
    level=0
    while level < 9:
        table="level_"+str(level)
        for package in packages:
            pNumber= package.package_revision.package.package_number 
            pRstate= getRState(package.package_revision.version)
            ss=cursor.execute("update "+table+" set changed='1' where not (revision='"+pRstate+"') and productnumber='"+pNumber+"'"),[] 
            #print str(ss) +"--"+str(pNumber)+"---"+str(table)
            connection.commit()

            #print package.package_revision.package.package_number 
            #print getRState(package.package_revision.version)
        level = level +1

def updateParents():
    level=9
    while level > 0:
        table="level_"+str(level)
        parentTable="level_"+str(level-1)
        print "updating " +str(parentTable)
        cursor.execute("UPDATE "+parentTable+" p, "+table+" t SET p.changed = '1' WHERE p.id = t.parent AND t.changed = '1'"),[]
        print "UPDATE "+parentTable+" p, "+table+" t SET p.changed = '1' WHERE p.id = t.parent AND t.changed = '1'"
        connection.commit()
        level = level -1

    



def getRState(ver):
    [maj, min, patch] = ver.split(".", 2)
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

    # Major version is verbatim
    myrstate = "R" + maj

    # Minor version is converted to letters
    # First convert it (from unicode) to an int
    x = int(min)
    letters = rbase[x]

    # Append patch level with leading 0 if less than 10
    ec = None
    patchparts = patch.split(".")
    if (len(patchparts) > 1):
        patch = patchparts[0]
        ec = patchparts[1]

    if (int(patch) < 10):
        letters += "0"
    myrstate += letters + patch

    # Append EC version, with leading 0 if less than 10
    if (ec != None):
        myrstate += "_EC"
        if (int(ec) < 10):
            myrstate += "0"
        myrstate += ec

    return myrstate

