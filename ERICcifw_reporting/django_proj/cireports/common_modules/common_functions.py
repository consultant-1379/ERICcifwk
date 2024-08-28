import re
import logging
import  cireports.models
from ciconfig import CIConfig
import subprocess
import json
from datetime import datetime
config = CIConfig()

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


def getVersion(rState):
    '''
     Getting the Version from the Rstate given
    '''
    if "_EC" in str(rState):
        try:
            matchObj = re.search( r'(\D{1})(\d{1,3})(\D{1,2})(\d{2,3})([a-zA-Z_]{3})(\d{2,3})', rState)
            if (int(matchObj.group(6)) < 10):
               return matchObj.group(2)+"."+str(rbase.index(matchObj.group(3)))+"."+matchObj.group(4)+"."+str(str(matchObj.group(6)).replace('0', ''))
            else:
               return matchObj.group(2)+"."+str(rbase.index(matchObj.group(3)))+"."+matchObj.group(4)+"."+matchObj.group(6)
        except Exception as e:
            logger.error("There is an issue getting Version for this RState with EC: " +str(e))
    else:
        try:
            matchObj = re.search( r'(\D{1})(\d{1,3})(\D{1,2})(\d{2,3})', rState)
            return matchObj.group(2)+"."+str(rbase.index(matchObj.group(3)))+"."+matchObj.group(4)
        except Exception as e:
            logger.error("There is an issue getting Version for this RState: " +str(e))

def convertRStateToVersion(rState):
    try:
        version = getVersion(str(rState))
        try:
            if "_EC" in str(rState):
                [maj, min, patch, ec] = version.split(".", 3)
                version = maj + "." + min + "." + str(int(patch)) + "." + str(int(ec))    
            else:
                [maj, min, patch] = version.split(".", 2)
                version = maj + "." + min + "." + str(int(patch))
        except Exception as e:
            logger.error("There is an issue getting Version for this RState: " +str(e))
    except:
        version = ""
    return version


def convertVersionToRState(version):
    try:
        try:
            [maj, min, patch] = version.split(".", 2)
        except:
            [maj, min] = version.split(".", 1)
        
        # Major version is verbatim
        myrstate = "R" + maj

        # Minor version is converted to letters
        # First convert it (from unicode) to an int
        x = int(min)
        letters = rbase[x]

        # Append patch level with leading 0 if less than 10
        ec = None
        try:
            patchparts = patch.split(".")
            if (len(patchparts) > 1):
               patch = patchparts[0]
               ec = patchparts[1]

            if (int(patch) < 10):
               letters += "0"
            myrstate += letters + patch
        except:
            myrstate += letters

        # Append EC version, with leading 0 if less than 10
        if (ec != None):
            myrstate += "_EC"
            if (int(ec) < 10):
                myrstate += "0"
            myrstate += ec
    except:
        myrstate = ""

    return myrstate

def sendDropConfigMessage(dropObj):
    try:
        if cireports.models.DropActivity.objects.filter(drop=dropObj).exists():
                dropActivityObj =  cireports.models.DropActivity.objects.filter(drop=dropObj).order_by('-id')[0]
                reason = dropActivityObj.desc
        else:
            reason = ""
        dropName = dropObj.name
        releaseName = dropObj.release.name
        productName = dropObj.release.product.name

        releaseDate = dropObj.planned_release_date
        if releaseDate:
            releaseDateZ = releaseDate.strftime("%Y-%m-%dT%H:%M:%S.%03dZ")
        else:
            releaseDateZ = "1970-01-01T00:00:00.000Z"

        designDropObj = dropObj.designbase
        if designDropObj:
            designDropName = designDropObj.name
            designReleaseName = designDropObj.release.name
            designProductName = designDropObj.release.product.name
            baseline = designProductName+"_"+designReleaseName+"_"+designDropName
        else:
            baseline = "none"

        mbHost = config.get('MESSAGE_BUS', 'eiffelHostname')
        mbExchange =  config.get('MESSAGE_BUS', 'eiffelExchangeName')
        mbDomain =  config.get('MESSAGE_BUS', 'eiffelDomainName')
        java =  config.get('MESSAGE_BUS', 'javaLocation')
        mbUser = config.get('MESSAGE_BUS', 'mbFunctionalUser')
        mbPwd = config.get('MESSAGE_BUS', 'mbFunctionalUserPassword')
        jsonInput = {
                    "componentType":"Drop",
                    "componentInstance":productName+"_"+releaseName+"_"+dropName,
                    "drop":dropName,
                    "product":productName,
                    "release":releaseName,
                    "reason":reason.replace("'",""),
                    "action":"modified",
                    "status":dropObj.status,
                    "endTime":releaseDateZ,
                    "baseline":baseline,
                    "messageBusHost":mbHost,
                    "messageBusExchange":mbExchange,
                    "messageBusDomain":mbDomain,
                    "messageBusUser": mbUser,
                    "messageBusPassword": mbPwd,
                    "messageType":"cne"
                    }
        dateCreated = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        logger.info("####### Sending DropConfig to Message bus ########")
        logger.info(jsonInput)
        sendCLME = subprocess.check_call(java + " -jar /proj/lciadm100/cifwk/latest/lib/3pp/eiffelEventSender/cli-event-sender.jar '"+json.dumps(jsonInput)+"' 2>> /proj/lciadm100/cifwk/logs/messagebus/eiffelDropConfigMessage/" + dateCreated, shell=True,cwd="/tmp")
        if not sendCLME == 0:
            logger.debug("Issue sending eiffel message")

    except Exception as e:
        logger.error("ERROR: Issue sending drop modification message " + str(e))

def sendEiffelBaselineUpdatedMessage(productSetVersion, override):
    '''
    For sending Eiffel Message when Product Set Working Baseline is updated or overriden
    '''
    mbHost = config.get('MESSAGE_BUS', 'eiffelHostname')
    mbExchange =  config.get('MESSAGE_BUS', 'eiffelExchangeName')
    mbDomain =  config.get('MESSAGE_BUS', 'eiffelDomainName')
    java =  config.get('MESSAGE_BUS', 'javaLocation')
    mbUser = config.get('MESSAGE_BUS', 'mbFunctionalUser')
    mbPwd = config.get('MESSAGE_BUS', 'mbFunctionalUserPassword')
    progress = "COMPLETED"
    levelState = "SUCCESS"

    try:
        requiredFields = ('drop__name', 'drop__release__product__name', 'drop__release__name', 'productSetRelease__number', 'drop__release__iso_groupId', 'version')
        productSetData = cireports.models.ProductSetVersion.objects.only(requiredFields).values(*requiredFields).get(id=productSetVersion.id)

        if not override:
            weightedStatus = productSetVersion.getOverallWeigthedStatus()
            if weightedStatus == "failed":
                levelState = "FAILED"
            elif weightedStatus == "in_progress":
                progress = "STARTED"

        jsonInput = {
                    "confidenceLevel":"PRODUCT_SET_WORKING_BASELINE_"+progress,
                    "confidenceLevelState":levelState,
                    "drop":productSetData['drop__name'],
                    "product":productSetData['drop__release__product__name'],
                    "release":productSetData['drop__release__name'],
                    "artifactId":productSetData['productSetRelease__number'],
                    "groupId":productSetData['drop__release__iso_groupId'],
                    "version":productSetData['version'],
                    "messageBusHost":mbHost,
                    "messageBusExchange":mbExchange,
                    "messageBusDomain":mbDomain,
                    "messageBusUser": mbUser,
                    "messageBusPassword": mbPwd,
                    "messageType":"clme"
                    }
        dateCreated = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        logger.info("####### Sending EiffelBaselineUpdatedMessage to Message bus ########")
        logger.info(jsonInput)
        sendCLME = subprocess.check_call(java + " -jar /proj/lciadm100/cifwk/latest/lib/3pp/eiffelEventSender/cli-event-sender.jar '"+json.dumps(jsonInput)+"' 2>> /proj/lciadm100/cifwk/logs/messagebus/eiffelBaselineUpdatedMessage/" + dateCreated, shell=True,cwd="/tmp")
        if not sendCLME == 0:
           logger.debug("Issue sending eiffel message")
    except Exception as e:
        logger.error("Issue sending eiffel message: " + str(e))

def buildlogManualStatusUpdate(productSetVersion, overrideFlag):
    '''
    Used to manually update the status of a productset in the deploymentbaseline table
    '''
    import  dmt.models
    psetVersion = str(productSetVersion.version)
    try:
        cifwkUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
    except Exception as e:
        logger.debug("Error getting data from config " + str(e))
    try:
        rowToUpdate = dmt.models.DeploymentBaseline.objects.filter(productset_id=psetVersion).exclude(fromISO='').exclude(fromISO=None).values('id','updatedAt','status','slot').reverse().order_by('createdAt')[0:1].get()
        idToUpdate = str(rowToUpdate.get('id'))
        slotToUpdate = str(rowToUpdate.get('slot'))
    except Exception as e:
        logger.debug("Error getting idToUpdate for manual update of auto buildlog " + str(e))
        rowToUpdate = None
    if(rowToUpdate):
        row = dmt.models.DeploymentBaseline.objects.get(id=idToUpdate)
        if(overrideFlag):
            row.status = "PASSED *"
        else:
            row.status = "FAILED *"
        row.save()
    else:
        logger.debug('Problem updating buildlog manually, no id found for this entry')