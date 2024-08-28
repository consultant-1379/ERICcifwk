import requests
import json
from lxml import etree
from ciconfig import CIConfig
from distutils.version import LooseVersion
from cireports.common_modules.common_functions import convertVersionToRState
import logging
logger = logging.getLogger(__name__)
from cireports.models import *
from django.db import transaction
config = CIConfig()

def letter_conv(col):
    try:
        alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'S', 'T', 'U', 'V', 'X', 'Y', 'Z']
        quot, rem = divmod(col - 1, 20)
        return letter_conv(quot) + alphabet[rem] if col != 0 else ''
    except Exception as e:
        errorMsg = "failed to generate release note during letter conversion: " + str(e)
        logger.error(errorMsg)


def gen_release_note(filename, drop, rstate, deliverables, tickets, productSetName, productNumber):
    try:
        o = {
            "productSet": productSetName,
            "drop": drop,
            "productNumber": productNumber,
            "rstate": rstate,
            "deliverables": deliverables,
            "softwareGatewayTickets": tickets
        }
        result = json.dumps(o, indent=4)
        return result
    except Exception as e:
        errorMsg = "failed to generate release note during generating release note: " + str(e)
        logger.error(errorMsg)

def get_checksum(mediaurl, productSetVersion, edpVersion):
    try:
        edpArtifactName = config.get('DMT_AUTODEPLOY', 'edpArtifactName')
        minEdpVersionSupportingSha512 = VersionSupportMapping.objects.get(
                feature='mrrnSha512',
                artifactId=edpArtifactName).version
        extension = ".md5" if LooseVersion(edpVersion) < LooseVersion(minEdpVersionSupportingSha512) else ".sha512"
        r = requests.get(mediaurl + extension)
        result = r.text
        if '<html>' in result:
            logger.info('sha512 not stored in Nexus for ' + str(edpArtifactName))
            return ''
        if extension == '.sha512':
            result = result.split('\n')[0]
        return result
    except Exception as e:
        errorMsg = "failed to generate release note during getting check sum: " + str(e)
        logger.error(errorMsg)
        return ''

def get_content(drop, version, productSetName):
    try:
        r = requests.get(
            'https://ci-portal.seli.wh.rnd.internal.ericsson.com/getProductSetVersionContents/',
            params={
                'drop': drop,
                'productSet': productSetName,
                'version': version
            }
        )
        psvc = r.json()[0]
        return psvc['contents']
    except Exception as e:
        errorMsg = "failed to generate release note during getting external releasable products from CI Portal: " + str(e)
        logger.error(errorMsg)

def get_functional_designation(product_number, auth):
    try:
        product_number = product_number.split('/')[0]
        r = requests.get(
            'https://rsb.internal.ericsson.com/REST/G3/CICD/Product/S/' + product_number,
            auth=auth,
            stream=True
        )
        r.raw.decode_content = True
        root = etree.parse(r.raw)
        return root.xpath('/Product/FunctionDesignation/text()')[0]
    except Exception as e:
        errorMsg = "failed to generate release note during getting functional designation: " + str(e)
        logger.error(errorMsg)

def get_content_filter(content):
    try:
        released = []
        for con in content:
            if con['externally_released'] == 'True':
                released.append(con)
        content = released
        return content
    except Exception as e:
        errorMsg = "failed to generate release note during filtering externally releasable products from the json content: " + str(e)
        logger.error(errorMsg)

def get_mapper(auth, productSetVersion, edpVersion):
    try:
        def mapper(c):
            src_url = 'athloneUrl' if c.get('athloneUrl') else 'hubUrl'
            filename = c[src_url].split('/')[-1]
            return {
                'functionalDesignation': get_functional_designation(c['artifactNumber'], auth),
                'productNumber': c['artifactNumber'],
                'rstate': str(convertVersionToRState(c['version'])),
                'checksum': get_checksum(c[src_url], productSetVersion, edpVersion),
                'filename': filename
            }
        return mapper
    except Exception as e:
        errorMsg = "failed to generate release note during mapping the release note data: " + str(e)
        logger.error(errorMsg)

def preprocessReleaseNoteParams(productSetVersion, productSetName):
    try:
        errorMsg = None
        version = productSetVersion
        username = config.get("CIFWK", "functionalUser")
        password = config.get("CIFWK", "functionalUserPassword")
        version_splitted = version.split('.')
        drop = '.'.join(version_splitted[:2])
        productSetObj = ProductSet.objects.only('id').values('id').get(name=productSetName)
        productSetVersionObj = ProductSetVersion.objects.only('id', 'version', 'productSetRelease__number').values('id', 'version', 'productSetRelease__number').get(version=productSetVersion, productSetRelease__productSet__id=productSetObj['id'])
        productSetNumber =  productSetVersionObj['productSetRelease__number']
        result_code, errorMsg = updateExternallyReleaseProducts()
        if result_code == 1:
            return None, errorMsg
        content = get_content(drop, version, productSetName)
        content = get_content_filter(content)
        content = list(content)
        for artifact in content:
            edpArtifactNumber = config.get('DMT_AUTODEPLOY', 'edpArtifactName').split('_')[1]
            if artifact.get('artifactNumber') == edpArtifactNumber:
                edpVersion = str(artifact.get('version'))
        content = list(map(get_mapper((username, password), productSetVersion, edpVersion), content))
    except Exception as e:
        errorMsg = "failed to generate release note for " + productSetName + "  " + productSetVersion + " " + str(e)
        logger.error(errorMsg)
    return gen_release_note("releasenote.{0}.json".format(version), drop, 'NOT_RELEASED', content, [], productSetName, productSetNumber), errorMsg

@transaction.atomic
def updateExternallyReleaseProducts():
    try:
        errorMsg = None
        result_code = 0
        sid = transaction.savepoint()
        externallyReleasableProductsList = ISObuild.objects.filter(externally_released = 1).values('artifactId').distinct()
        for externallyReleasableProduct in externallyReleasableProductsList:
            if ISObuild.objects.filter(artifactId = externallyReleasableProduct["artifactId"], externally_released = 0).exists():
                ISObuild.objects.filter(artifactId = externallyReleasableProduct["artifactId"]).update(externally_released = 1)
    except Exception as e:
        errorMsg = "failed to update externally releasable products: " + str(e)
        result_code = 1
        transaction.savepoint_rollback(sid)
        logger.error(errorMsg)
    return result_code, errorMsg
