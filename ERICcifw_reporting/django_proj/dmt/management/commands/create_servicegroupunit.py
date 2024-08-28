from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from dmt.models import *
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create a service group unit, then check the database to ensure that creation was successful"
    option_list = BaseCommand.option_list  + (
            make_option('--serviceUnit',
                dest='serviceUnit',
                help='The Service unit you wish to all'),
            make_option('--groupType',
                dest='groupType',
                help='Available options LSB or JBOSS'),
            )


    def handle(self, *args, **options):
        serviceUnit = options['serviceUnit']
        if options['groupType'] == None:
           raise CommandError("Specify a groupType. either LSB or JBOSS. Please try Again....")
        else:
            if options['groupType'] == "LSB":
                groupType = "LSB Service Cluster"
            elif options['groupType'] == "JBOSS":
                groupType = "JBOSS Service Cluster"
            else:
                raise CommandError("Specify a valid group Type JBOSS or LSB. Please try Again....")

        duplicateCheck = self.checkForUnitDuplicate(serviceUnit)
        if "ERROR" in duplicateCheck:
            return duplicateCheck
        if ServiceGroupTypes.objects.filter(group_type=groupType).exists():
            serviceGroupType = ServiceGroupTypes.objects.get(group_type=groupType)
            serviceGroupUnit = ServiceGroupUnit(service_unit=serviceUnit,group_type=serviceGroupType)
            serviceGroupUnit.save()
        else:
            logger.error("Service Group: " + str(groupType) + " does not exist.")
        unitCheck = self.checkForUnitCreation(serviceUnit)
        return unitCheck

    def checkForUnitDuplicate(self, serviceUnit):
        '''
        Checks the database to ensure that the new service unit has not already been added.
        '''
        try:
            if ServiceGroupUnit.objects.filter(service_unit=serviceUnit).exists():
                error = "ERROR: '"+serviceUnit+"' is already in the database. It cannot be added again."
                logger.error(error)
                return error
            else:
                return "INFO: Service Unit: '" + str(serviceUnit) + "' does not Exist, creating."
        except Exception as e:
            error = "ERROR: quering database for service Unit: " + str(serviceUnit) + ". Error thrown: " + str(e)
            logger.error(error)
            return error

    def checkForUnitCreation(self, serviceUnit):
        '''
        Checks the database to ensure that the new service unit has been added to the database after creation.
        '''
        try:
            if ServiceGroupUnit.objects.filter(service_unit=serviceUnit).exists():
                return "SUCCESS: '"+serviceUnit+"' was successfully added to the database."
            else:
                error = "ERROR: '"+serviceUnit+"' could not be added to the database."
                logger.error(error)
                return error
        except Exception as e:
            error = "ERROR: quering database for service Unit: " + str(serviceUnit) + ". Error thrown: " + str(e)
            logger.error(error)
            return error

