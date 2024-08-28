import requests
import json
import logging
from ciconfig import CIConfig
from dmt.models import DDtoDeploymentMapping

logger = logging.getLogger(__name__)
config = CIConfig()


def validateSedFile(cluster, sedFileName, tmpArea, product, installType,
                    productSetVersion):
    try:
        missingInfo = ""
        if DDtoDeploymentMapping.objects.filter(cluster=cluster).exists():
            ddMapping = DDtoDeploymentMapping.objects.get(cluster=cluster)
            deploymentType = ddMapping.deployment_description.name
        else:
            missingInfo += "Deployment Description###"

        if cluster.ipVersion is not None:
            ipVersion = cluster.ipVersion.name.lower()
        else:
            missingInfo += "IP Version###"

        if product == 'ENM':
            product = config.get('DMT_AUTODEPLOY', 'onlineSedEnmProductName')
        else:
            missingInfo += "Supported Product###"

        if installType == 'initial_install':
            installType = 'install'
        elif installType == 'upgrade_install':
            installType = 'upgrade'
        else:
            missingInfo += "Supported Install Type###"

        if productSetVersion is not None:
            productSetVersion = productSetVersion.split('::')[1]
        else:
            missingInfo += "Product Set Version###"

        if len(missingInfo) > 0:
            logger.info("The following information is missing or unsupported "
                        "for SED validation")
            logger.info(missingInfo)
            return False

        url = config.get('DMT_AUTODEPLOY', 'onlineSedApi')

        files = {
            'SEDFile': (sedFileName, open(tmpArea + '/' + sedFileName))
        }

        data = {
            'product': product,
            'useCase': installType,
            'enmDeploymentType': deploymentType,
            'enmVersion': productSetVersion,
            'ipVersion': ipVersion
        }

        response = requests.post(url, verify=False, files=files, data=data)
        jsonData = json.loads(response.text)
        isSedValid = jsonData['message']['isInputSEDValid']
        formattedJson = json.dumps(jsonData, indent=4)

        logger.info('-----------Online SED Validation Result--------------')
        if isSedValid:
            logger.info("SED Validation Successful")
        else:
            logger.info("SED Validation Failure")
        logger.info(formattedJson)
        logger.info('-----------------------------------------------------')

        return isSedValid
    except Exception as e:
        logger.info(e)
