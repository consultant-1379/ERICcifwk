from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
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
import cireports.prim

cursor = connection.cursor()


logging.getLogger('suds.client').setLevel(logging.CRITICAL)
errors = 0

logger = logging.getLogger(__name__)
class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--user',
                dest='user',
                help='prim user'),
            make_option('--password',
                dest='password',
                help='prim password'),
            make_option('--base_product',
                dest='base',
                help='base product'),
            make_option('--base_rev',
                dest='baserev',
                help='base revision'),
            make_option('--drop',
                dest='drop',
                help='drop'),
            make_option('--write',
                dest='write',
                help='write'),
            make_option('--new',
                dest='new',
                help='new release (True/False'),
            )


    def handle(self, *args, **options):
        if options['user'] == None:
            raise CommandError("Option required")
        else:
            user=options['user']
        if options['write'] == None:
            raise CommandError("Option required")
        else:
            write=options['write']

        if options['password'] == None:
            raise CommandError("Option required")
        else:
            password=options['password']
        if options['base'] == None:
            raise CommandError("Option required")
        else:
            topProduct=options['base']
        if options['baserev'] == None:
            raise CommandError("Option required")
        else:
            topRev=options['baserev']
        if options['drop'] == None:
            raise CommandError("Option required")
        else:
            drop=options['drop']
        if options['new'] == None:
            raise CommandError("Option required")
        else:
            drop=options['drop']

        cireports.prim.createTables()
        login=cireports.prim.login(user,password)
        
        #topProduct = "AOM 901 112"
        #topRev = "R1A01"
        topProduct = "CSA 113 107"
        topRev = "R1E"
        drop = "1.0.12"
        newRelease = False

        cursor.execute("INSERT INTO level_0(productnumber,revision,type) VALUES(%s,%s,%s)",[topProduct.replace(" ",""),topRev,"13161-"])
        connection.commit()
        id= cursor.lastrowid
        cireports.prim.getAll(topProduct,topRev,login,1,id)
        #sys.exit()

        drp = cireports.models.Drop.objects.get(name=drop)
        packages = cireports.utils.getPackageBaseline(drp)
        cireports.prim.findChangedAll(packages)
        cireports.prim.updateParents()
        cireports.prim.updatePkgRev(drop)
        #sys.exit()


        cireports.prim.stepRevAndStore(newRelease)
        cireports.prim.returnData()


        sys.exit() 
        cireports.prim.createProducts(drop,login,write)
        cireports.prim.createStructure(login,write)
        cireports.prim.dropTables()
        sys.exit()
        #cireports.prim.createNewStruct("CNA4032608","R1D",contentList, "13","login") 
