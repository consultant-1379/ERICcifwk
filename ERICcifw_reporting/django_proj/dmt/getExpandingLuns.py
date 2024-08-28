#!/usr/bin/python

import os
import re
import sys
import argparse
import logging
logging.basicConfig(level=logging.INFO)


from os.path import exists

sys.path.append('/opt/ericsson/enminst/lib')

from h_litp.litp_rest_client import LitpRestClient, LitpException
from h_xml.xml_utils import load_xml, xpath, get_xml_element_properties

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def getSiteIdFromSed(sed):
    # get site id from sed.
    try:
        with open(sed, 'r') as fh:
            lines = fh.readlines()
        lines = [line.strip() for line in lines]
        for line in lines:
             if line.startswith('san_siteId'):
                 return line.split('=')[1]
    except Exception as e:
        logger.info('Exception raised in function getSiteIdFromSed')
        raise

def getLunsFromTemplate(template, sed):
    try:
        temp_xml_file = '/tmp/temp.xml'

        # Read in xml template
        with open(template, 'r') as fh:
            template_contents = ''.join(fh.readlines())

        site_id = getSiteIdFromSed(sed)
        # substitute site id so that lun names are created from template
        substituted = template_contents.replace('%%san_siteId%%', site_id)

        # write the substituted xml to file
        with open(temp_xml_file, 'w') as fh:
            fh.writelines(substituted)

        # load the xml
        substituted_etree = load_xml(temp_xml_file)
        lun_dict = {}

        # retrieve the luns from the xml and store the name & size in a dict
        luns = xpath(substituted_etree, 'lun-disk')
        for lun in luns:
            #print lun
            lun_props = get_xml_element_properties(lun)
            lun_name = lun_props['lun_name']
            lun_size = lun_props['size']
            lun_dict[lun_name] = lun_size
        os.remove(temp_xml_file)
        return 0, lun_dict
    except Exception in e:
        logger.info('Exception raised in function getLunsFromTemplate')
        raise

def findLitpItems(litp, path, item_type, items):
    try:
        item = litp.get(path, log=False)
        if item['item-type-name'] == item_type:
            items.append(item)
        for item in litp.get_children(path):
            findLitpItems(litp, item['path'], item_type, items)
    except LitpException as err:
        _code = err.args[0]
        if _code == NOT_FOUND:
            return items
        raise
    return items

def getLunsFromLitpModel():
    try:
        litp = LitpRestClient()
        lun_dict = {}
        path = '/infrastructure/systems'
        items = findLitpItems(litp, path, 'lun-disk', [])
        for item in items:
            lun_name = item['properties']['lun_name']
            lun_size = item['properties']['size']
            lun_dict[lun_name] = lun_size

        deployment_clusters = litp.get_deployment_clusters()
        for deployment, clusters in deployment_clusters.items():
            for cluster in clusters:
                path = '/deployments/{0}/clusters/{1}/fencing_disks'.format(
                    deployment, cluster)
                fencing_disks = findLitpItems(litp, path, 'lun-disk', [])
                for fen in fencing_disks:
                    lun_name = item['properties']['lun_name']
                    lun_size = item['properties']['size']
                    lun_dict[lun_name] = lun_size
        return 0, lun_dict
    except Exception as e:
        logger.info('Exception raised in function getLunsFromLitpModel')
        raise


def main(args):
    try:
        sed = args.sed
        xml_template = args.xml
        # Define vars
        expandedLunsList = []
        # Get luns from sed sed and xml template
        ret, templateLuns = getLunsFromTemplate(xml_template, sed)
        if ret != 0:
            return 1, 'Error: ' + str(templateLuns)
        # Get luns from litp plan
        ret, modelLuns = getLunsFromLitpModel()
        if ret != 0:
            return 1, 'Error: ' + str(modelLuns)
        # Check if any of the model luns has a size change in the template
        for name,size in modelLuns.iteritems():
            if name in templateLuns:
                if modelLuns[name] != templateLuns[name]:
                    expandedLunsList.append(str(name))
        return 0, expandedLunsList
    except Exception as e:
        logger.info('Exception is raised in main function' + str(__name__))
        return 1, 'Error in lun expansion check'
# Script exits 1 if lun expansion

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #
    # Define each option with: parser.add_argument
    #
    parser.add_argument('-s','--sed',help='Path to SED file deployed in MS', required=True)
    parser.add_argument('-x','--xml',help='Path to deployment description document XML file', required=True)
    #
    # Access results with: args.argumentName
    #
    args = parser.parse_args()
    #
    # Call the main function where business logic is implemented.
    #
    ret, response = main(args)
    if ret != 0:
        print 'Exception: ' + str(response)
        sys.exit(1)
    else:
        print str(response)
        sys.exit(0)



