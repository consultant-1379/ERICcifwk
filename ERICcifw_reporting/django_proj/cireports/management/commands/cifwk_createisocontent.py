from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from distutils.version import LooseVersion
from optparse import make_option
from lxml import etree

import cireports.utils
import fwk.utils
from cireports.models import *

from ciconfig import CIConfig
import logging
import re
import sys
config = CIConfig()
logger = logging.getLogger(__name__)
xmlfile = 'pom.xml'
from datetime import datetime


class Command(BaseCommand):
    help = "Create the content for the ISO, will build up content for latest drop unless a drop is specified"
    option_list = BaseCommand.option_list  + (
            make_option('--product',
                dest='product',
                help='Product the ISO build is for. Default product is TOR'),
            make_option('--release',
                dest='release',
                help='Product release to build the ISO for. Default is the most recent release'),
            make_option('--drop',
                dest='drop',
                help='Drop to gather the ISO content for'),
            make_option('--ver', 
                dest='ver', 
                help='ISO Version'),
            make_option('--artifactId',
                dest='artifactId',
                help='Media artifactId'),
            make_option('--groupId',
                dest='groupId',
                help='Media groupId'),
            make_option('--releaseRepoName',
                dest='releaseRepoName',
                help='Media releaseRepoName'),
            make_option('--platform',
                dest='platform',
                help='platform for the ISO content'),
            make_option('--check', 
                dest='check',
                help='Checking if Build needs to be done'),
            make_option('--location',
                dest='location',
                help='Specify a location of where iso content will be downloaded, otherwise it will go to current location'),
            make_option('--content',
                dest='content',
                help='This just to enter iso content into the CI Fwk database without building ISO or storing a ISO in Nexus'),                
            )

    def handle(self, *args, **options):
        release = ""
        product = ""
        currentDrop = ""
        co = options['content']
        plat = options['platform']
        dropName = options['drop']
        loc  = options['location']
        check  = options['check']
        ver = options['ver']
        artId = options['artifactId']
        grpId = options['groupId']
        repo = options['releaseRepoName']
        
        #Product - Check
        productName = options['product']
        if productName == None or productName == "":
            self.stdout.write("Error: You must supply a product")
            if co == None or co == "":
                raise CommandError("You must supply a product")
            else:
                return "Error: You must supply a product"
        try:
            product = Product.objects.get(name=productName)
        except Product.DoesNotExist:
            self.stdout.write("Error: Product " + productName + " does not exist")
            if co == None or co == "":
                raise CommandError("Product " + productName + " does not exist")
            return "Error: Product " + productName + " does not exist"
        #Release - Check
        releaseName = options['release']
        if releaseName == None or releaseName == "":
            self.stdout.write("Error: You must supply a release")
            if co == None or co == "":
                raise CommandError("You must supply a release")
            else:
                return "Error: You must supply a release"
        try:
            #Checking if the ProductName is OSS-RC and the ReleaseName Format for their ISO i.e O14_1
            if "_" in releaseName and "OSS-RC" in productName: 
               rn = releaseName.replace("O","OSS-RC").replace('_','.')
               release = Release.objects.get(product=product,name=rn) 
            else:
                release = Release.objects.get(product=product,name=releaseName)
        except Release.DoesNotExist:
            self.stdout.write("Error: Release " + releaseName + " does not exist")
            if co == None or co == "":
                raise CommandError("Release " + releaseName + " does not exist")
            else:
                return "Error: Release " + releaseName + " does not exist"
        #Drop - Check
        if dropName == None or dropName == "" or dropName == "None":
            # Get latest drop (latest drop is highest drop number from database)
            allDrops = Drop.objects.filter(release=release).order_by('-id')
            currentDrop = allDrops[0]

            logger.info("No drop supplied, Generating content for latest drop, " + str(dropName))
        else:
            # Get the ID of the drop passed
            try:
                currentDrop = Drop.objects.get(name=dropName, release=release)
            except Drop.DoesNotExist:
                self.stdout.write("Error: Drop specified, " + str(dropName) + " does not exist")
                if co == None or co == "":
                    raise CommandError("Drop specified, " + str(dropName) + " does not exist")
                else:
                    return "Error: Drop specified, " + str(dropName) + " does not exist"
        #Check if only a Database update        
        if co == None or co == "":
            #Location - Check
            if loc == None or loc == "":
                logger.info("No location supplied, Downloading content to current directory")
                loc = "."
        
        # Get List of all the Drop/Package Mappings for the Drop (these are ordered by the date they are created)
        dpms = cireports.utils.getPackageBaseline(currentDrop)

        # Run the Check to see if there was a change in the drop or it's first build 
        logger.info("Establishing list of packages delivered to " + str(dropName))
        if check == "true":
            change = cireports.utils.checkingForChangesInDrop(dpms, currentDrop, dropName, "product-iso")
            if change == "true":
                return "Build"
            else:        
                return "Do not build"

        #ISO Version - Check
        if ver == None or ver == "":
            if "_" in releaseName and "OSS-RC" in productName:
                ver = cireports.utils.createISOversion(dpms, currentDrop, dropName)
                self.stdout.write(str(ver) + " ISO Version Created\n")
                if ver == "true":
                    self.stdout.write("Error: No deliveries found to create ISO content with, Please investigate further. Exiting")
                    return "Error: No deliveries found to create ISO content with, Please investigate further. Exiting"
            else:
                logger.info("No Version supplied, using current drop and current date time")
                ver = str(dropName) + "_" + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")).replace(" ",'_')
                self.stdout.write(str(ver) + " ISO Version Created\n")

        #Media GroupId - Check
        if grpId == None or grpId == "":
            if not str(release.iso_groupId):
                self.stdout.write("Error: groupId Required")
                if co == None or co == "":
                    raise CommandError("Error: groupId Required")
                else:
                    return "Error: groupId Required"
            else:
                grpId = release.iso_groupId

        #Media ArtifactId - Check
        if artId == None or artId == "":
            if not str(release.iso_artifact):
                self.stdout.write("Error: groupId Required")
                if co == None or co == "":
                    raise CommandError("Error: artifactId Required")
                else:
                    return "Error: artifactId Required"
            else:
                artId = release.iso_artifact

        #Media ARM_Repo - Check
        if repo == None or repo == "":
            if not str(release.iso_arm_repo):
                self.stdout.write("Error: repo Required, i.e. releases")
                if co == None or co == "":
                    raise CommandError("Error: repo Required i.e. releases")
                else:
                    return "Error: Repo Required i.e. releases"
            else:
                repo = release.iso_arm_repo
  
        mediaArtifact = None
        # Getting Media Artifact (masterArtifact) for This Release
        try:
            mediaArtifact = MediaArtifact.objects.get(name=artId)
        except Exception as e:
            self.stdout.write("Media Artifact Does Not Exist in Database For This Release " + str(release.name) + ", " + str(e))
            if co == None or co == "":
                raise CommandError("Error: Media Artifact Does Not Exist in Database For This Release " + str(release.name))
            else:
                return "Error: Media Artifact Does Not Exist in Database For This Release " + str(release.name)

        #To Check if both or i386 was entered into platform - x86 ISO contents will be recorded in CI Fwk DB
        if ("_" in releaseName and "OSS-RC" in productName) and ("both" in str(plat).lower() or "i386" in str(plat).lower()):
            iso_x86 = None
            if not ISObuild.objects.filter(version=ver, drop=currentDrop, mediaArtifact=mediaArtifact, artifactId=artId, groupId=grpId).exists():
                iso_x86 = ISObuild.objects.create(version=str(ver), mediaArtifact=mediaArtifact, drop=currentDrop, build_date=datetime.now(), artifactId=artId, groupId=grpId, arm_repo=repo)
                self.stdout.write("A record of ISO version : " + str(iso_x86.version) + " content was entered into CI Fwk Database")
            for dpm in dpms:
                if not iso_x86 == None:
                    # creating new iso build mapping for each package for x86
                    if  dpm.package_revision.platform == "i386" or dpm.package_revision.platform == "common":
                        ISObuildMapping.objects.create(iso=iso_x86, drop=dpm.drop, package_revision=dpm.package_revision)
        #To Check if platform - sparc ISO 
        elif ("_" in releaseName and "OSS-RC" in productName) and "sparc" in str(plat).lower():
            self.stdout.write("A records of Sparc ISOs content are not created in CI Fwk Database")
        #Normal ISO content recording
        else:
            #Checking if the version was already entered into database
            iso = None
            #To Stop SNAPSHOT being entered in the Database
            if not "SNAPSHOT" in str(ver):
                if not ISObuild.objects.filter(version=ver, mediaArtifact=mediaArtifact, drop=currentDrop, artifactId=artId, groupId=grpId).exists():
                    #new version meaning iso build will be created 
                    iso = ISObuild.objects.create(version=ver, drop=currentDrop, mediaArtifact=mediaArtifact, build_date=datetime.now(), artifactId=artId, groupId=grpId, arm_repo=repo)
                    self.stdout.write("A record of Media Artifact " + str(mediaArtifact.name) + " version : " + str(iso.version) + " content was entered into CI Fwk Database")
            for dpm in dpms:
                # Get the artifact down from nexus
                artifactName =  dpm.package_revision.package.name + "-" + dpm.package_revision.version + "." + dpm.package_revision.m2type
                file = dpm.package_revision.getNexusUrl(product)
                # checking if the iso is not None
                if not iso == None:
                    # creating new iso build mapping for each package
                    isoBuild = ISObuildMapping.objects.create(iso=iso, drop=dpm.drop, package_revision=dpm.package_revision)
                # Checking if it's only a Database update
                if co == None or co == "":
                    try:
                        logger.info("Downloading " + str(artifactName))
                        logger.info("Download URL: " + file)
                        fwk.utils.downloadFile(file, loc)
                    except Exception as e:
                        logger.error("Got an exception retrieving " + file + ": " + str(e))
                        return "There was a problem trying to download this version, please contact your Administrator"

