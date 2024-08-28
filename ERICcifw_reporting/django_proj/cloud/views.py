from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from metrics.models import *
from cloud.models import *
import logging
import utils
logger = logging.getLogger(__name__)

@csrf_exempt
def mapGatewayToSpp(request):
    if request.method == 'POST':
        try:
            gateway = request.POST.get('gateway')
            spp = request.POST.get('spp')
            result = utils.storeGatewayToSppMap(gateway,spp)
        except Exception as e:
            logger.error("Issue posting gateway/spp mappings to the database " +str(e))
            result = "ERROR: Issue posting gateway/spp mappings to the database " +str(e)
    else:
        result="ERROR: only POST calls accepted"
    return HttpResponse(result, content_type="text/plain")

@csrf_exempt
def getSpp(request):
    if request.method == 'GET':
        try:
            gateway = request.GET.get('gateway')
            if gateway is None or not gateway or gateway == "None":
                return HttpResponse("Error: Gateway required.\n")

            if GatewayToSppMapping.objects.filter(gateway__name=gateway).exists():
                map = GatewayToSppMapping.objects.get(gateway__name=gateway)
                result = map.spp.url
            else:
                result = "Gateway supplied does not exist in database"
        except Exception as e:
            logger.error("Issue getting SPP url for gateway " +str(gateway) + " "  +str(e))
            result = "ERROR: Issue getting SPP url for gateway " +str(gateway) + " "  +str(e)
    else:
        result="ERROR: only GET calls accepted"
    return HttpResponse(result, content_type="text/plain")
