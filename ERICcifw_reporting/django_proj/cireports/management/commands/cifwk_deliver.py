from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
import datetime
from django.core.mail import send_mail
from distutils.version import LooseVersion
import re
import sys
import ast
import cireports.utils
from ciconfig import CIConfig
config = CIConfig()

logger = logging.getLogger(__name__)
dt = datetime.datetime.now()
dm = 'CI-Framework@ericsson.com'

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--package',
                dest='package',
                help='The name of the package that is being delivered ie: ERICpackagename_CXC12345'),
            make_option('--packageVersion',
                dest='packageVersion',
                help='The Version of the package that is being delivered, can also use "latest" to deliver latest version of package ie: 1.0.1 or latest'),
            make_option('--packageType',
                dest='packageType',
                help='The Package Type of the package that is being delivered, multiple formats supported.. rpm, zip, pkg etc..'),
            make_option('--drop',
                dest='drop',
                help='The Drop(s) to which the package is being delivered, can be a comma seperated list or auto. auto will specified autodrop from DB  ie: 2.0.3 or 2.0.3,3.0.6 or auto'),
            make_option('--product',
                dest='product',
                help='The product to which the package is being delivered ie: TOR/OSS-RC'),
            make_option('--platform',
                dest='platform',
                help='Optional Parameter, The platform OS the the package will be installed/upgraded on ie: i386/common/sparc'),
            make_option('--email',
                dest='email',
                help='Optional Parameter, The email address of the person/group that is delivering the package'),
            make_option('--user',
                dest='user',
                help='The user who delivered the package'),
            )

    def handle(self, *args, **options):
        '''
        '''
        if options['package'] == None:
            raise CommandError("Package required")
        else:
            package=options['package']

        if options['packageVersion'] == None:
           raise CommandError("Package Version required")
        else:
            ver=options['packageVersion']

        if options['drop'] == None:
            raise CommandError("Drop required")
        else:
            dropArray=options['drop']

        if options['product'] == None:
            raise CommandError("Product required")
        else:
            product=options['product'].upper()
            if product == "OSS-RC" :
                type='pkg';
            else:
                type='rpm';

        if options['packageType'] != None:
            type=options['packageType']

        if options['platform'] == None:
            platform = "None"
        else:
            platform=options['platform']
        developmentServer = ast.literal_eval(config.get("CIFWK", "testServer"))
        if developmentServer == 1:
            try:
                deliveryEmail = ast.literal_eval(config.get("DELIVERY_EMAIL_LIST", str(product).upper()))
            except Exception as e:
                deliveryEmail=None
                status = "ERROR: Distribution Email list Required For Product " + str(product) + ". \n  Please contact CI Axis to give the Distribution Email list for this Product" + str(e)
                return status
        else:
            try:
                product = Product.objects.get(name=product)
                productEmail = ProductEmail.objects.filter(product=product.id)
                deliveryEmail = []
                if productEmail != None:
                    for delEmail in productEmail:
                        deliveryEmail.append(delEmail.email)
            except Exception as e:
                deliveryEmail=None
                status = "ERROR: Distribution Email list Required For Product " + str(product) + ". \n  Please contact CI Axis to give the Distribution Email list for this Product" + str(e)
                return status

        to = []
        if options['email'] == None:
            userEmail = "User email not supplied, command line delivery"
        else:
            userEmail=options['email']
            to.append(userEmail)
        if deliveryEmail != None:
            for i in deliveryEmail:
                to.append(i)

        if options['user'] == None:
            userObj = None
        else:
            userObj=options['user']
        #Get Latest Version of the Package if latest is selected as Version
        if ( ver == "latest" ):
            try:
                ver, status = cireports.utils.getLatestVersionOfPackage(package, platform)
                if "ERROR:" in status:
                    return status
            except Exception as e:
                raise CommandError( "Exception Thrown in finding latest Package Version: " +str(e))

        #if auto selected search database for drops to be delivered to
        if ( dropArray == "auto" ):
            try:
                dropArray, status = cireports.utils.getLatestDropOnProductRelease(dropArray, product, platform, package, ver, type)
                if "ERROR:" in status:
                    return status
            except Exception as e:
                raise CommandError("Exception Thrown in finding latest Drop: " +str(e))

        dropArray=dropArray.split(",")
        self.stdout.write("Attempting delivery of " + package + " ver " + ver + " to " + ', '.join(dropArray) + "\n")
        #Make Delivery
        try:
            header, content, status = cireports.utils.makeDeliveryOfPackage(dropArray, package, ver, type, platform, product, userEmail, to, False, userObj)
            if "ERROR:" in status:
                return status
        except Exception as e:
            raise CommandError("Exception Thrown in making delivery: " +str(e))
