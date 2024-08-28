from metrics.models import *
from cloud.models import *
from datetime import datetime
now = datetime.now()
import logging
logger = logging.getLogger(__name__)

def storeGatewayToSppMap(gateway,spp):
    '''
    Function to store the mapping of a gateway to a SPP Portal
    '''
    try:
        gwObj,gwCreated = Gateway.objects.get_or_create(name=gateway)
        sppObj,sppCreated = SPPServer.objects.get_or_create(url=spp)
        if sppCreated:
            sppObj.name = spp
            sppObj.save()

        if GatewayToSppMapping.objects.filter(gateway=gwObj).exists():
            logger.debug("Removing existing Gateway to SPP Mapping ")
            GatewayToSppMapping.objects.get(gateway=gwObj).delete()

        GatewayToSppMapping.objects.create(gateway=gwObj, spp=sppObj, date=now)
        result = "Created Mapping "+str(gateway)+ " SPP: "+str(spp)
    except Exception as e:
        logger.error("Issue creating Gateway to SPP Mapping " +str(e))
        result = "ERROR: Issue creating Gateway to SPP Mapping: "+str(e)
    return result
