from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from dmt.models import *
from cireports.models import *
from distutils.version import StrictVersion
from distutils.version import LooseVersion

import sys, os, tempfile, shutil, time
import dmt.deploy
import dmt.utils
import cireports.models
import logging
import signal
import warnings

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

def handler(signum, frame):
    logger.info("Captured Key Stroke")
    descriptionDetails = "Caught Ctrl-C Command, Cleaned up the system"
    dmt.utils.dmtError(descriptionDetails)

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to edit the inventory and definition XML files and validate against the
    XSD's stored in Nexus
    '''
    help = "Class to edit the inventory and definition XML and validate against XSD's"
    option_list = BaseCommand.option_list  + (
            make_option('--clusterid',
                dest='clusterId',
                help='ID of the Cluster to be configured'),
            make_option('--deploymentid',
                dest='deploymentId',
                help='ID of the deployment to be configured'),
            make_option('--installgroup',
                dest='installGroup',
                help='Group identifier for pool of deployments to install from'),
            make_option('--product',
                dest='product',
                help='The product you wish to install onto i.e ENM, CSL-Mediation etc'),
            make_option('--productSet',
                dest='productSet',
                help='Optional Parameter: if the product set parameter is given then this take precedence over the enm --drop parameter and the litp --litpdrop parameter and the infor for these image will be taken from the referenced product Set. To get the latest specify productDrop::Latest (e.g. 15.8::Latest) to get passed images specify productDrop::passed (e.g. 15.8::Passed) to specify a specific product drop version specify productDrop::version (e.g. 15.8::8.0.2)'),
            make_option('--drop',
                dest='drop',
                help='Optional Parameter: The Drop where the packages should be downloaded from (e.g. "1.0.11")'),
            make_option('--environment',
                dest='environment',
                help='Used to specify type of environment you are installing onto i.e cloud or physical"'),
            make_option('--installType',
                dest='installType',
                help='Used to specify which type of install should be carried out options are "initial_install" or "upgrade_install"'),
            make_option('--stopAtStage',
                dest='stopAtStage',
                help='Optional Parameter: Stop execution at this stage (stage isn\'t executed)'),
            make_option('--deployScript',
                dest='deployScript',
                help='Optional Parameter: To set the specific Deploy Script tar file version to use for the installation'),
            make_option('--deployPackage',
                dest='package::R-State/Latest/Partial-R-State.Latest',
                help='Optional Parameter: Used if you wish to deploy the system with a specific packages R-State or Latest R-State. Format of input Package::R-State/Latest/Partial-R-State.Latest Multiple packages can be given in by seperating them with a double colon "||", e.g Package::R-State/Latest/Partial-R-State.Latest||Package::R-State/Latest/Partial-R-State.Latest etc. The Partial-R-State.Latest mean that if your package is multitrack then you may need to give a partial section of the beginning of the R-State i.e. 1.2.Latest will pick up the latest R-State for 1.2.XXX'),
            make_option('--deployLitpPackage',
                dest='litpPackage::Latest/Version',
                help='Optional Parameter: Used if you wish to deploy the LITP iso with a specific packages Version or Latest version. Format of input Package::Latest/Version. Multiple packages can be given in by seperating them with a double dog  "@@", e.g Package::Latest/Version@@Package::Latest/Version etc. HTTP link also supported, e.g Package::HTTP_link_to_package_with_version'),
            make_option('--deployRelease',
                dest='deployRelease',
                help='Optional Parameter: Used if you wish to deploy a certain release i.e 14A 14B etc. Default is 14B'),
            make_option('--deployProduct',
                dest='deployProduct',
                help='Optional Parameter: Used if you wish to deploy a certain Product Version i.e LITP1, LITP2 etc. Default is LITP1'),
            make_option('--litpDrop',
                dest='litpDrop',
                help='Optional Parameter: Used to specify which drop should be used to download the Litp iso from, also can specify the iso to download by drop::isoVersion e.g. 15.2::2.15.61'),
            make_option('--osVersion',
                dest='osVersion',
                help='Optional Parameter: Used if you wish to initial install the MS with the red hat os distribution. The version should correspond to the version within the media directory on the jump server e.g. 6.4_x86'),
            make_option('--skipOsInstall',
                dest='skipOsInstall',
                help='Optional Parameter: Used to skip the os base Red Hat install, option YES or NO'),
            make_option('--skipLitpInstall',
                dest='skipLitpInstall',
                help='Optional Parameter: Used to skip the Litp 2 install, option YES or NO'),
            make_option('--skipPatchInstall',
                dest='skipPatchInstall',
                help='Optional Parameter: Used to skip the OS RHEL Patches install, option YES, NO, RHEL6, RHEL7, RHEL79, RHEL88'),
            make_option('--skipEnmInstall',
                dest='skipEnmInstall',
                help='Optional Parameter: Used to skip the ENM install, option YES or NO'),
            make_option('--ipmiVersion',
                dest='ipmiVersion',
                help='Optional Parameter: Used to get the ipmi version for cloud PXE Booting, i.e. 1.0.9'),
            make_option('--redfishVersion',
                dest='redfishVersion',
                help='Optional Parameter: Used to get the redfish version for cloud PXE Booting, i.e. 1.0.7'),
            make_option('--reDeployVMS',
                dest='reDeployVMS',
                help='Optional Parameter: Used if you wish to redeploy the Virtual MS (Litp 1) system on  a physical MS (Litp2) system. Options YES or NO defaults to NO '),
            make_option('--featTest',
                dest='featTest',
                help='Optional Parameter: Used for physical deployments with limited storage on the VNX'),
            make_option('--osPatchVersion',
                dest='osPatchVersion',
                help='Optional Parameter: Used if you wish to upload the OS Patch tar file to the Mgt Server. e.g. 15.9::1.2.1::PRODUCT_NAME'),
            make_option('--osRhel7PatchVersion',
                dest='osRhel7PatchVersion',
                help='Optional Parameter: Used if you wish to upload the OS Red Hat 7 Patch tar file to the Mgt Server. e.g. 15.9::1.2.1::PRODUCT_NAME'),
            make_option('--osRhel79PatchVersion',
                dest='osRhel79PatchVersion',
                help='Optional Parameter: Used if you wish to upload the OS Red Hat 7.9 Patch file to the Mgt Server. e.g. 21.08::1.2.1::PRODUCT_NAME'),
            make_option('--osRhel88PatchVersion',
                dest='osRhel88PatchVersion',
                help='Optional Parameter: Used if you wish to upload the OS Red Hat 8.8 Patch file to the Mgt Server. e.g. 24.03::1.2.1::PRODUCT_NAME'),
            make_option('--servicePatchVersion',
                dest='servicePatchVersion',
                help='Optional Parameter: Used if you wish to upload the Service Patch version to the Mgt Server. Only need to give the version i.e R1J_1'),
            make_option('--mountIsoAgain',
                dest='mountIsoAgain',
                help='Optional Parameter: Used if you do not wish to re-mount the iso, options yes or no'),
            make_option('--reInstallInst',
                dest='reInstallInst',
                help='Optional Parameter: Used if you do not wish to re-install the currently installed version of Torinst, options yes or no'),
            make_option('--setClusterStatus',
                dest='setClusterStatus',
                help='Optional Parameter: Used if you want to keep the status of the deployment at idle'),
            make_option('--setSED',
                dest='setSED',
                help='Optional Parameter: To Specify a specific sed template, the user can also set a URL to a fully populated SED e.g. --setSED http://<IP Address>/Cluster-1130-config.cfg'),
            make_option('--skipStage',
                dest='skipStage',
                help='Optional Parameter: Used to skip a specific stage of the installation'),
            make_option('--extraParameter',
                dest='extraParameter',
                help='Optional Parameter: Used to specify a complete paramater (enter parameter and value of option) to cover anything that may be not cover within the deploymnet script. e.g "--stage check_storage_configuration", multiple commands can be entered like so, "--stage check_storage_configuration --reset_to_start --append_log"'),
            make_option('--siteEngineeringFilesVersion',
                dest='siteEngineeringFilesVersion',
                help='Optional Parameter: To Specify a specific site engineering files version in nexus'),
            make_option('--reStartFromStage',
                dest='reStartFromStage',
                help='Optional Parameter: Used if you wish to re-start the install from a certain stage in the install. The user must give the correct stage name. This option is only available upto and including the apply_ms_patches stage. Also, note the option to RE-Install Torinst this should also be specified unless you required it to be changed.'),
            make_option('--newISOLayout',
                dest='newISOLayout',
                help='Optional Parameter: Used to specify if the new ISO layout in the form of CXPnumber_RSTATE is being used, Default is set to true'),
            make_option('--step',
                dest='step',
                help='Optional Parameter: Used for trouble shooting the install if you need to step through the install one function at a time, input YES'),
            make_option('--snapShot',
                dest='snapShot',
                help='Optional Parameter: Use option \"create\" to create a snapshot or restore to restore a snapshot of the server to the infra installation, the sed used to perform the installation also needs to be specified e.g create_snapshot[OPTIONAL<::<snapShotName>>] or restore_snapshot[OPTIONAL<::<snapShotName>>].'),
            make_option('--stageOne',
                dest='stageOne',
                help='True/False: Used to specify if you want to run stage One(Infrastructure) of the deployment'),
            make_option('--xmlFile',
                dest='xmlFile',
                help='Used to specify a specific xml file to use for the installation full directory structure and file name needs to be given e.g. /ericsson/deploymentDescriptions/enm-full-cdb-deployment_cloud_dd.xml, also this can be given as a URL. The script will download the file using the url and upload to /var/tmp/ on the MS. Another option is use a slice to use a slice you need to use the following format --xmlFile slice::<sliceName>. This will download the slice snapshot zip file from Nexus upload to /var/tmp/slice directory and find the <sliceName> and use that to perform the deployment'),
            make_option('--stageTwo',
                dest='stageTwo',
                help='True/False: Used to specify if you want to run stage Two(Applications) of the deployment'),
            make_option('--exitAfterISORebuild',
                dest='exitAfterISORebuild',
                help='YES/NO: if YES will exit after ISO is rebuilt with packages for test'),
            make_option('--summary',
                dest='summary',
                help='Optional Parameter: Used to just print the summary of what is going to be installed'),
            make_option('--skipTearDown',
                dest='skipTearDown',
                help='Optional Parameter: Used to skip the clean up of the deployment before initial install (teardown.sh)'),
            make_option('--ignoreHa',
                dest='ignoreHa',
                help='Optional Parameter: Used in conjunction with the softwareUpdate if you wish to ignore the HA system and bring down all services at once i.e. --ignoreHa YES if left blank the script will decide according to the service to re-define'),
            make_option('--edn',
                dest='edn',
                help='Optional Parameter: Used only for performing a deployment inside the EDN network i.e. --edn YES'),
            make_option('--network',
                dest='network',
                help='Optional Parameter: used to specify the network the deployment is deploying from i.e. --network youlab or --network edn or --network ecn, default is set to ecn'),
            make_option('--verifyServices',
                dest='verifyServices',
                help='Optional Parameter: Used to execute the verification of the service vms assigned in the deployment against the SED used only for II and UG e.g. --verifyServices YES'),
            make_option('--updateServiceGroups',
                dest='updateServiceGroups',
                help='Optional Parameter: Used to execute the automatic update cluster Service Groups inline with latest green Deployment Description only for II and UG e.g. --updateServiceGroups YES'),
            make_option('--updateNASconfig',
                dest='updateNASconfig',
                help='Optional Parameter: Used to execute the update of NAS Configuration Kit version on a NAS Server e.g --updateNASconfig YES'),
            make_option('--nasConfigVersion',
                dest='nasConfigVersion',
                help='Optional Parameter: Used to passing in version of NAS Configuration Kit for updating that version on a NAS Server'),
            make_option('--skipNasPatchInstall',
                dest='skipNasPatchInstall',
                help='Optional Parameter: Used to enable automation of NAS patch install e.g --skipNasPatchInstall YES'),
            make_option('--ignoreUpgradePrecheck',
                    dest='ignoreUpgradePrecheck',
                    help='Optional Parameter: Used to ignore Health Check script, by default NO, if health check is failed then exit deployment.'),
            make_option('--hcInclude',
                dest='hcInclude',
                help='Optional Parameter: Used to activate multipath Health Check from upgrade_enm script only during UG, e.g. --hcInclude YES, if left blank then the script will exclude multipath_active_hc'),
            make_option('--edpProfiles',
                dest='edpProfiles',
                help='Optional Parameter (EDP Only): Used to pass in custom comma separated list of profiles for EDP'),
            make_option('--edpVersion',
                dest='edpVersion',
                help='Optional Parameter (EDP Only): Used to pass in a version of EDP'),
            make_option('--edpPackage',
                dest='edpPackage',
                help='Optional Parameter (EDP Only): Used to pass in a list EDP packages'),
            make_option('--nasSnapshotUrl',
                dest='nasSnapshotUrl',
                help='Optional Parameter : URL to NASConfig media'),
            make_option('--kickstartFileUrl',
                dest='kickstartFileUrl',
                help='Optional Parameter Used to test custom kickstart files, Multiple file urls should be separated by @@'),
            make_option('--failOnSedValidationFailure',
                dest='failOnSedValidationFailure',
                help='Optional Parameter used to specify whether or not to fail on SED validation failure')
            )

    def handle(self, *args, **options):

        signal.signal(signal.SIGINT, handler)
        # Set the default for the status
        status="BUSY"
        network = ""
        drop = litpDrop = osVersion = osVersion8 = osRhel6PatchVersion = osRhel7PatchVersion = osRhel79PatchVersion = osRhel88PatchVersion = cfgTemplate = deployScriptVersion = skipPatchIntallType = None
        psVersion = None

        if options['updateServiceGroups'] != None:
            updateServiceGroups = options['updateServiceGroups'].upper()
        else:
            updateServiceGroups = "NO"

        if options['ignoreUpgradePrecheck'] != None:
            if options['ignoreUpgradePrecheck'].upper() == 'YES' or options['ignoreUpgradePrecheck'].upper() == 'NO':
                ignoreUpgradePrecheck = options['ignoreUpgradePrecheck'].upper()
            else:
                raise CommandError("Please provide valid argument to this paramter YES or NO.")
        else:
            ignoreUpgradePrecheck = "NO"

        if options['verifyServices'] != None:
            verifyServices = options['verifyServices'].upper()
        else:
            verifyServices = "NO"

        if options['network'] != None:
            networksList = config.get("DMT_AUTODEPLOY", "networks").split(',')
            if str(options['network'].lower()) in networksList:
                network = options['network'].lower()
            else:
                raise CommandError("the following options are only supported for the \"--network\" parameter, edn, ecn, youlab, gtec_edn or gtec_youlab. Please try again")
        else:
            network = "ecn"

        if network == "":
            if options['edn'] != None:
                warnings.warn(
                    "The \"--edn\" option is being deprecated please use the \"--network\" option.",
                    DeprecationWarning
                )
                edn = options['edn'].upper()
                if edn == "NO":
                    network = "ecn"
                else:
                    network = "edn"
            else:
                network = "ecn"

        if options['step'] == None:
            step = None
        else:
            step = "YES"

        if options['ignoreHa'] != None:
            ignoreHa = options['ignoreHa'].upper()
        else:
            ignoreHa = "AUTO"

        #Define the product if not set throw an error
        supportedProducts = config.get("DMT_AUTODEPLOY", "supportedProducts").split(',')
        if options['product'] == None :
            raise CommandError("A product needs to be selected from the following, " + str(supportedProducts))
        elif options['product'] not in supportedProducts:
            raise CommandError("Supported Product Required. Please chose one of the supported products from the following, " + str(supportedProducts))
        else:
            productOrig = options['product']
            product = options['product'].upper()

        if options['productSet'] == None:
            productSet = None
        else:
            productSet = options['productSet'].upper()
            (drop,litpDrop,osVersion,osVersion8,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,nasConfig,nasRhelPatch,cfgTemplate,deployScriptVersion,mtUtilsVersion,otherUtilities,psVersion) = dmt.deploy.getProductDropInfo(productSet,product)
            if "Error:" in drop:
                raise CommandError(drop)
            if drop == None:
                logger.info("ENM ISO info not found within Product set")
            if litpDrop == None:
                logger.info("LITP ISO info not found within Product set")
            if osVersion == None:
                logger.info("OS Media ISO info not found within Product set")
            if osVersion8 == None:
                logger.info("OS Media ISO info for RHEL8 not found within Product set")
            if osRhel6PatchVersion == None:
                logger.info("Red Hat 6 OS Patches file info not found within Product set")
            if osRhel7PatchVersion == None:
                logger.info("Red Hat 7 OS Patches file info not found within Product set")
            if osRhel79PatchVersion == None:
                logger.info("Red Hat 7.9 OS Patches file info not found within Product set")
            if osRhel88PatchVersion == None:
                logger.info("Red Hat 8.8 Patches file info not found within Product set")
            if cfgTemplate == None:
                logger.info("SED Version info not found within ENM ISO Version on Product set")
            if deployScriptVersion == None:
                logger.info("Deployment Script Version info not found within ENM ISO Version on Product set")
            if options['installType'] != None:
                if options['installType'].lower() == "softwareupdateonly":
                    softwareUpdateLatestDrop = drop
        #Define the deployment id if not set check if a group is set if not throw an error
        if options['clusterId'] == None and options['deploymentId'] == None:
            if options['installGroup'] == None:
                raise CommandError("You need to specify either an install group or deployment ID")
            else:
                clusterId = dmt.deploy.getFreeCluster(options['installGroup'], status)
                if "Error" in str(clusterId):
                    raise CommandError(str(clusterId)+ " " + str(options['installGroup']))
        else:
            if options['clusterId'] == None and options['deploymentId'] != None:
                clusterId = options['deploymentId']
            else:
                clusterId = options['clusterId']

        #Define the environment if not set throw an error
        if options['environment'] == None:
            environment = dmt.deploy.getEnvironment(clusterId)
        elif options['environment'].lower() != "cloud" and options['environment'].lower() != "physical":
            raise CommandError("Please choose an environment to install onto i.e. cloud or physical")
        else:
            environment = options['environment'].lower()
        if environment != 'physical':
            nasConfig = None
            nasRhelPatch = None
        isRackDeployment, msg, returnCode= dmt.deploy.checkNASType(clusterId)
        if isRackDeployment:
            nasConfig = None
            nasRhelPatch = None

        #Defining the drop if not specified then take latest
        if options['drop'] == None:
            if options['installType'] != None:
                if options['installType'].lower() == "softwareupdateonly":
                    logger.info("Retrieving Installed System info")
                    ret,drop,msg = dmt.utils.retrieveDeploymentSystemInfo(clusterId,environment)
                    if ret != 0:
                        raise CommandError(str(msg))
                elif drop == None:
                    logger.info("Drop not specified. Taking latest Drop within Nexus")
                    drop = "latest"
            elif drop == None:
                logger.info("Drop not specified. Taking latest Drop within Nexus")
                drop = "latest"
        else:
            if options['installType'].lower() == "softwareupdateonly":
                logger.info("Retrieving Installed System info")
                ret,drop,msg = dmt.utils.retrieveDeploymentSystemInfo(clusterId,environment)
                if ret != 0:
                    raise CommandError(str(msg))
                softwareUpdateLatestDrop = options['drop'].upper()
                if "::" in softwareUpdateLatestDrop:
                    ( softwareUpdateLatestDrop, isoVersion ) = dmt.deploy.setDropIsoVersion(softwareUpdateLatestDrop)
                else:
                    isoVersion = "LATEST"
                ( isoName, isoVersion, isoUrl, hubIsoUrl ) = dmt.deploy.getIsoName(softwareUpdateLatestDrop,isoVersion,product)
                if (isoName == 1):
                    raise CommandError("There was an issue retrieving the ENM ISO Version to install")
                softwareUpdateLatestDrop = str(softwareUpdateLatestDrop) + "::" + str(isoVersion)
            else:
                drop = options['drop'].upper()

        if options['skipEnmInstall'] != None:
            skipEnmInstall = options['skipEnmInstall'].upper()
        else:
            skipEnmInstall = "NO"

        if skipEnmInstall == "NO" and drop == None:
            raise CommandError("You have specified to install the ENM ISO, please specify a ENM ISO Version to install")

        if product != 'CSL-MEDIATION':
            if options['deployProduct'] != None:
                deployProduct = options['deployProduct'].upper()
            else:
                deployProduct = "LITP2"
        else:
            deployProduct = None

        if options['snapShot'] == None:
            installTypeList = ['initial_install', 'upgrade_install', 'softwareupdateonly', 'nasupdateonly']
            #Define the install type if not set with a specific value throw an error
            if options['installType'] == None:
                raise CommandError("Install Type Required. Please choose \"initial_install\" for initial install, \"upgrade_install\" for an upgrade install or \"softwareUpdateOnly\" for a application update only or \"nasUpdateOnly\" for only updating the NAS Config on NAS Server")
            elif not options['installType'].lower() in installTypeList:
                raise CommandError("Install Type Required. Please choose \"initial_install\" for initial install, \"upgrade_install\" for an upgrade install or \"softwareUpdateOnly\" for a application update only or \"nasUpdateOnly\" for only updating the NAS Config on NAS Server")
            else:
                installType = options['installType'].lower()

            if options['skipTearDown'] != None:
                skipTearDown = options['skipTearDown'].lower()
            else:
                skipTearDown = "no"

            if deployProduct == "LITP2":
                if options['osVersion'] != None:
                    osVersion = options['osVersion']

                if options['litpDrop'] != None:
                    litpDrop = options['litpDrop']

                if options['skipOsInstall'] != None:
                    skipOsInstall = options['skipOsInstall'].upper()
                    if skipOsInstall == "NO" and osVersion == None:
                        raise CommandError("You have chosen to re-install the OS on the MS, please choose an OS version also")
                else:
                    if osVersion != None:
                        skipOsInstall = "NO"
                    elif osVersion == None and productSet != None:
                        raise CommandError("Please specify an OS Version to install (i.e. --osVersion 6.6_x86)")
                    else:
                        skipOsInstall = "YES"

                if options['skipLitpInstall'] != None:
                    skipLitpInstall = options['skipLitpInstall'].upper()
                    if skipLitpInstall == "NO" and litpDrop == None:
                        raise CommandError("You have chosen to install LITP on the MS, please choose a Litp Drop also")
                else:
                    if litpDrop != None:
                        skipLitpInstall = "NO"
                    elif litpDrop == None and productSet != None:
                        raise CommandError("Please specify a Litp Drop to install (i.e. --litpDrop <Drop>::<Version>)")
                    else:
                        skipLitpInstall = "YES"

                if skipOsInstall == "NO" and skipLitpInstall == "YES" and skipEnmInstall == "NO":
                        raise CommandError("You have chosen to re-install the OS on the MS, chosen to install the ENM ISO, so LITP also needs to be install, please choose a Litp Drop also")

                if environment == "cloud":
                    if skipEnmInstall != "YES":
                        if options['ipmiVersion'] != None:
                            ipmiVersion = options['ipmiVersion']
                        else:
                            ipmiVersion = dmt.deploy.getIpmiVersion(drop)
                            if ipmiVersion == None:
                                raise CommandError("You have chosen a product of Litp2 and a cloud deployment the ipmi version needs to be specified")
                    else:
                        ipmiVersion = None
                else:
                    ipmiVersion = None

                if environment == "cloud":
                    if skipEnmInstall != "YES":
                        if options['redfishVersion'] != None:
                            redfishVersion = options['redfishVersion']
                        else:
                            redfishVersion = dmt.deploy.getRedfishVersion(drop)
                            if redfishVersion == None:
                                raise CommandError("You have chosen a product of Litp2 and a cloud deployment the redfish version needs to be specified")
                    else:
                        redfishVersion = None
                else:
                    redfishVersion = None

                reDeployVMS = "NO"
            else:
                litpDrop = None
                reDeployVMS = "NO"
                osVersion = None
                osVersion8 = None
                skipOsInstall = None
                skipLitpInstall = None
                ipmiVersion = None
                redfishVersion = None
        else:
            deployProduct = "LITP2"
            litpDrop = None
            reDeployVMS = "NO"
            osVersion = None
            osVersion8 = None
            skipOsInstall = "NO"
            skipLitpInstall = "NO"
            skipPatchInstall = "NO"
            ipmiVersion = None
            redfishVersion = None
            installType = "IGNORE"
            skipTearDown = "no"

        if installType != 'upgrade_install' and installType != 'initial_install':
            nasConfig = None
            nasRhelPatch = None

        if deployProduct == "LITP2" and options['snapShot'] == None and installType != "softwareupdateonly":
            if options['xmlFile'] != None:
                xmlFile = options['xmlFile']
            else:
                raise CommandError("Please specify a deployment description XML file")
            if "::" in xmlFile:
                if "slice::" not in xmlFile:
                    raise CommandError("Please specify a deployment description XML file, if specifing a slice then it needs to be in the form slice::<sliceName>")
        else:
            xmlFile = None

        # set the status of the deployment
        if options['setClusterStatus'] != None:
            setClusterStatus = options['setClusterStatus'].lower()
        else:
            setClusterStatus = "no"

        if setClusterStatus == "no":
            status="IDLE"

        # set the stopAtStage to a specific stage
        if options['stopAtStage'] != None:
            stopAtStage = options['stopAtStage']
        else:
            stopAtStage = "NO"

        # set the osRhel6PatchVersion to a specific version
        if product == 'TOR' or product == 'ENM':
            if options['osPatchVersion'] != None:
                osRhel6PatchVersion = options['osPatchVersion'].upper()

        if options['skipPatchInstall'] != None:
            skipPatchInstall = options['skipPatchInstall'].upper()
        else:
            skipPatchInstall = "NO"

        # set the osRhel7PatchVersion to a specific version
        if product == 'TOR' or product == 'ENM':
            if options['osRhel7PatchVersion'] != None:
                osRhel7PatchVersion = options['osRhel7PatchVersion'].upper()
            # set the osRhel79PatchVersion to a specific version
            if options['osRhel79PatchVersion'] != None:
                osRhel79PatchVersion = options['osRhel79PatchVersion'].upper()
            # set the osRhel88PatchVersion to a specific version
            if options['osRhel88PatchVersion'] != None:
                osRhel88PatchVersion = options['osRhel88PatchVersion'].upper()

        # set the servicePatchVersion to a specific version
        if options['servicePatchVersion'] != None:
            servicePatchVersion = options['servicePatchVersion'].upper()
        else:
            servicePatchVersion = None
        if options['litpPackage::Latest/Version'] != None:
            litpPackageList = options['litpPackage::Latest/Version']
        else:
            litpPackageList = None
        # Package is set to None if not specified
        if options['package::R-State/Latest/Partial-R-State.Latest'] != None:
            packageList = options['package::R-State/Latest/Partial-R-State.Latest']
        else:
            if installType == "softwareupdateonly":
                if softwareUpdateLatestDrop:
                    logger.info("You have specified to perform a software Update Only.")
                    logger.info("But have not specified packages to deploy, going to try and calculate according to ENM drop specified " + str(softwareUpdateLatestDrop))
                    if environment == "cloud":
                        logger.info("NOTE, only packages with categories of either " + config.get('DMT_AUTODEPLOY', 'cloudSoftwareUpdateCategories') + " will be updated")
                    else:
                        logger.info("NOTE, only packages with categories of either " + config.get('DMT_AUTODEPLOY', 'physicalSoftwareUpdateCategories') + " will be updated")
                    oldIsoVersion = drop.split("::")[1]
                    oldIsoDrop = drop.split("::")[0]
                    newIsoVersion = softwareUpdateLatestDrop.split("::")[1]
                    if StrictVersion(oldIsoVersion) >= StrictVersion(newIsoVersion):
                         raise CommandError("The ISO currently installed on the system is " + str(oldIsoVersion) + " this is higher or the same as the new ISO Version " + str(newIsoVersion))
                    newIsoDrop = softwareUpdateLatestDrop.split("::")[0]
                    dropObj = Drop.objects.get(name=newIsoDrop,release__product__name=product)
                    cifwkPortalUrl = config.get('DMT_AUTODEPLOY', 'cifwk_portal_url')
                    url = str(cifwkPortalUrl) + "/getISOContentDelta/?isoGroup=" + str(dropObj.release.iso_groupId) + "&isoArtifact=" + str(dropObj.release.iso_artifact) + "&drop=" + str(dropObj.name) + "&isoVersion=" + str(newIsoVersion) + "&previousDrop=" + str(oldIsoDrop) + "&previousISOVersion=" + str(oldIsoVersion)
                    searchValue = "Updated"
                    (ret,jsonObj) = dmt.utils.getTheResponseFromARestCall(url)
                    if ret != 0:
                         raise CommandError("Unable to execute Rest Call to get ISO Diff for software Update")
                    (ret,listRef) = dmt.utils.getReferenceIndexFromListObj(jsonObj,searchValue)
                    if ret != 0:
                         raise CommandError("Unable to find \"" + str(searchValue) + "\" packages in ISO diff rest call")
                    (ret,packageList) = dmt.utils.packageFromISOJsonDiff(jsonObj,searchValue,listRef)
                    if ret != 0 or not packageList:
                         raise CommandError("Unable to find any packages under the " + str(searchValue) + " packages section in ISO diff rest call")
                else:
                    raise CommandError("You have specified to perform a software Update Only so you need to specify packages(i.e. --deployPackage <Package Name>::<RSTATE>)")
            else:
                packageList = None

        # deployRelease is set to None if not specified
        if options['deployRelease'] != None:
            deployRelease = options['deployRelease']
        else:
            deployRelease = None

        # skipStage used to skip a stage in the installation
        if options['skipStage'] != None:
            skipStage = options['skipStage']
        else:
            skipStage = "NO"

        # extraParameter to add a parameter and value that may be missing within the deployment script or added new to the inst program
        if options['extraParameter'] != None and options['extraParameter'] != "":
            extraParameter = options['extraParameter']
            extraParameter = extraParameter.replace(' ','###')
        else:
            extraParameter = "NO"

        # Used to set the featTest variable for physical deployments
        if options['featTest'] != None:
            featTest = options['featTest'].upper()
        else:
            featTest = "NO"

        if options['setSED'] != None:
            cfgTemplateOrig = options['setSED']
            if "http" in options['setSED']:
                cfgTemplate = options['setSED']
            else:
                cfgTemplate = options['setSED'].upper()
        else:
            if cfgTemplate == None:
                cfgTemplateOrig = "MASTER"
                cfgTemplate = "MASTER"
            else:
                cfgTemplateOrig = cfgTemplate
                cfgTemplate = cfgTemplate
        failOnSedValidationFailure = False
        if options['failOnSedValidationFailure'] is not None:
            if options['failOnSedValidationFailure'].lower() == 'yes':
                failOnSedValidationFailure = True

        # Define version of the site engineering gzip file in nexus to download for CSL-Mediation
        if product == 'CSL-MEDIATION':
            if options['siteEngineeringFilesVersion'] != None:
                siteEngineeringFilesVersion = options['siteEngineeringFilesVersion']
            else:
                raise CommandError("You need to specify siteEngineeringFilesVersion if doing an install of CSL-Mediation")

        # Defining the drop if not specified then take latest
        if product == "TOR" or product == 'ENM':
            if options['deployScript'] == None:
                if deployScriptVersion == None:
                    deployScriptVersion = dmt.utils.getDeployScriptVersion(drop, osVersion)
                    if deployScriptVersion != None:
                        logger.info("Taking Default Deploy tar file version " + deployScriptVersion + " from database")
                    else:
                        raise CommandError("You need to specify a deploy script (i.e. --deployScript <version>)")
            else:
                deployScriptVersion = options['deployScript']
                logger.info("Taking Deploy tar file version " + deployScriptVersion + " from user input")

        # set the reInstallInst
        if options['reInstallInst'] != None:
            reInstallInst = options['reInstallInst'].lower()
        else:
            reInstallInst = "yes"

        # set the mountIsoAgain
        if options['mountIsoAgain'] != None:
            mountIsoAgain = options['mountIsoAgain'].lower()
        else:
            mountIsoAgain = "yes"

        # set the reStartFromStage
        if options['reStartFromStage'] != None:
            reStartFromStage = options['reStartFromStage']
        else:
            reStartFromStage = "no"

        # set the newISOLayout flag
        if options['newISOLayout'] != None:
            newISOLayout = options['newISOLayout']
        else:
            newISOLayout = "True"

        # set the performSnapshot option
        if options['snapShot'] != None:
            performSnapshot = options['snapShot']
            if environment == "cloud":
                raise CommandError("You can't snap a cloud system in this way this option is only for physical deployment, to snap a cloud deployment use the jenkins cloud plugin")
        else:
            performSnapshot = None

        # set stageOne
        if options['stageOne'] != None:
            stageOne = options['stageOne'].lower()
            status="BUSY"
        else:
            stageOne = "false"

        # set stageTwo
        if options['stageTwo'] != None:
            stageTwo = options['stageTwo'].lower()
        else:
            stageTwo = "false"

        if stageTwo == "true" and stageOne == "true":
            raise CommandError("To perform a full deployment please omit the parameters \"stageOne\" and \"stageTwo\" or set these values to false, both cannot be set to true")

        # set exit after create ISO
        if options['exitAfterISORebuild'] != None and options['exitAfterISORebuild'].lower() =='yes':
            exitAfterISORebuild = True
        else:
            exitAfterISORebuild = False

        if options['hcInclude'] != None:
            if options['hcInclude'] == 'YES':
                hcInclude = str(options['hcInclude']).upper()
            elif options['hcInclude'] == 'NO':
                hcInclude = "multipath_active_healthcheck"
            else:
                raise CommandError("--hcInclude flag accepts only YES/NO parameters.")
        else:
            hcInclude = "multipath_active_healthcheck"

        if clusterId != None:
            if Cluster.objects.filter(id=clusterId).exists():
                clusterObj = Cluster.objects.get(id=clusterId)
                statusObj = DeploymentStatus.objects.get(cluster=clusterObj)
                if "cloud" not in environment and product != 'CSL-MEDIATION':
                    acceptedStatus = ['IDLE', 'FAILED']
                    if str(statusObj.status) in acceptedStatus:
                        dmt.deploy.updateDeploymentStatus(clusterId,status,osVersion,osRhel6PatchVersion,osRhel7PatchVersion,osRhel79PatchVersion,osRhel88PatchVersion,litpDrop,drop,packageList,"Deployment In Progress")
                    else:
                        logger.error("This deployment is in a " + str(statusObj.status) + " state")
                        raise CommandError("Deployment " + str(clusterObj.name) + " is " + str(statusObj.status))
            else:
                raise CommandError("Please ensure the deployment/cluster id is registered on the Portal")

        if options['updateNASconfig'] != None:
            updateNASconfig = str(options['updateNASconfig']).upper()
        else:
            updateNASconfig = "YES"

        if options['kickstartFileUrl'] != None:
            kickstartFileUrl = options['kickstartFileUrl']
        else:
            kickstartFileUrl = None

        if installType == "softwareupdateonly":
            skipOsInstall = "YES"
            skipLitpInstall = "YES"
            skipPatchInstall = "YES"

        skipNasPatchInstall = None
        if options['skipNasPatchInstall'] != None:
            if str(options['skipNasPatchInstall']).upper() == 'YES':
                skipNasPatchInstall = True

        edpProfileList = edpVersion = edpPackageList = None
        if options['edpProfiles'] != None:
            edpProfileList = options['edpProfiles']
        if options['edpVersion'] != None:
            edpVersion = options['edpVersion']
        if options['edpPackage'] != None:
            edpPackageList = options['edpPackage']

        installTypeNAS = ['initial_install', 'upgrade_install', 'nasupdateonly']
        patchSkip6 = "NO"
        patchSkip7 = "NO"
        patchSkip79 = "NO"
        patchSkip88 = "NO"
        if options['snapShot'] == None:
            logger.info("==============================================================================================")
            logger.info("Summary of Deployment")
            logger.info("Deployment Type: " +str(installType))
            logger.info("Environment: " + str(environment))
            if installType != "softwareupdateonly":
                if environment == "cloud":
                    logger.info("IPMI Version: " + str(ipmiVersion))
                    logger.info("Redfish Version: " + str(redfishVersion))
                if skipPatchInstall == "YES":
                    patchSkip6 = "YES"
                    patchSkip7 = "YES"
                    patchSkip79 = "YES"
                    patchSkip88 = "YES"
                elif skipPatchInstall == "RHEL7":
                    patchSkip7 = "YES"
                elif skipPatchInstall == "RHEL6":
                    patchSkip6 = "YES"
                elif skipPatchInstall == "RHEL79":
                    patchSkip79 = "YES"
                elif skipPatchInstall == "RHEL88":
                    patchSkip88 = "YES"
                logger.info("RHEL OS Version: " + str(osVersion) + ". Skipping install: " + str(skipOsInstall))
                if osVersion8:
                    logger.info("RHEL 8 OS Version: " + str(osVersion8) + ". Skipping install: Yes")
                if osRhel6PatchVersion:
                    logger.info("RHEL 6 OS Patch Set Version: " + str(osRhel6PatchVersion) + ". Skipping install: " + str(patchSkip6))
                if osRhel7PatchVersion:
                    logger.info("RHEL 7 OS Patch Set Version: " + str(osRhel7PatchVersion) + ". Skipping install: " + str(patchSkip7))
                if osRhel79PatchVersion:
                    logger.info("RHEL 7.9 OS Patch Set Version: " + str(osRhel79PatchVersion) + ". Skipping install: " + str(patchSkip79))
                if osRhel88PatchVersion:
                    logger.info("RHEL 8.8 OS Patch Set Version: " + str(osRhel88PatchVersion) + ". Skipping install: " + str(patchSkip88))
                logger.info("Litp Drop: " + str(litpDrop) + ". Skipping install: " + str(skipLitpInstall))
                logger.info("ENM Drop: " + str(drop) + ". Skipping install: " + str(skipEnmInstall))
            else:
                logger.info("ENM Drop: " + str(drop) + " (Currently Deployed on the system). Skipping install: " + str(skipEnmInstall))
            if installType != "softwareupdateonly":
                logger.info("SED Template: " + str(cfgTemplate))
            logger.info("Deploy Script Version: " + str(deployScriptVersion))

            if litpPackageList == None:
                logger.info("Deploy Extra LITP Packages: NO")
            else:
                logger.info("Deploy Extra LITP Packages: YES")
                logger.info("LITP Packages to Deploy: " + str(litpPackageList))

            if packageList == None:
                logger.info("Deploy Extra Packages: NO")
            else:
                logger.info("Deploy Extra Packages: YES")
                logger.info("Packages to Deploy: " + str(packageList))
                if installType == "softwareupdateonly":
                    if environment == "cloud":
                        logger.info("NOTE, only packages with categories of either " + config.get('DMT_AUTODEPLOY', 'cloudSoftwareUpdateCategories') + " will be updated")
                    else:
                        logger.info("NOTE, only packages with categories of either " + config.get('DMT_AUTODEPLOY', 'physicalSoftwareUpdateCategories') + " will be updated")

                    logger.info("Performing a Software Update Only")
            if installType in installTypeNAS:
                logger.info("Update NAS Config: " + str(updateNASconfig))
                if options['nasSnapshotUrl']:
                    logger.info("NAS Config Snapshot URL: " + str(options['nasSnapshotUrl']))
                if options['nasConfigVersion']:
                    logger.info("NAS Config Version: " + str(options['nasConfigVersion']))
            else:
                logger.info("Update NAS Config: NO")

            if edpVersion:
                logger.info("EDP Version: " + str(edpVersion) + ".")

            if edpProfileList:
                logger.info("EDP Custom Profiles: " + str(edpProfileList))

            if edpPackageList:
                logger.info("Deploy Extra EDP Packages: YES")
                logger.info("EDP Packages to Deploy: " + str(edpPackageList))

            logger.info("============================Full Command Inputted=============================================")
            inputCommand = ""
            for item in sys.argv:
                if " " in item:
                    item = "\"" + str(item) + "\""
                inputCommand += str(item) + " "
            logger.info(inputCommand.replace("django_proj/manage.py","bin/cicmd"))
            logger.info("==============================================================================================")
            time.sleep(3)

        if options['summary'] != None:
            return 0
        if litpPackageList:
            if "error" in dmt.utils.validateAutoDeployPackages(litpPackageList):
                message = "There was an Issue found in the Defined Artifacts in --deployLitpPackage option, please check that all are valid including links if defined"
                logger.error(message)
                raise CommandError(message)

        if packageList:
            #Check the defined Packages ensuring no typos
            if "error" in dmt.utils.validateAutoDeployPackages(packageList):
                message = "There was an Issue found in the Defined Artifacts in --deployPackage option, please check that all are valid including links if defined"
                logger.error(message)
                raise CommandError(message)

        if edpPackageList:
            #Check the defined EDP Packages ensuring no typos
            if "error" in dmt.utils.validateAutoDeployPackages(edpPackageList):
                message = "There was an Issue found in the Defined Artifacts in --edpPackage option, please check that all are valid including links if defined"
                logger.error(message)
                raise CommandError(message)


        if installType in installTypeNAS:
            if updateNASconfig == "YES" and psVersion != None:
                result, returnCode = dmt.deploy.updatingNASconfig(psVersion, clusterId, options['nasConfigVersion'], deployScriptVersion, installType, options['nasSnapshotUrl'])
                if returnCode != 0:
                    if returnCode != 200:
                        raise CommandError(result)
                    else:
                        logger.warning(result)
                else:
                    logger.info(result)

        if "nasupdateonly" != str(installType):
            if product == 'TOR' or product == 'ENM':
                dmt.deploy.deployMainTor(clusterId, drop, product, environment, packageList, litpPackageList, deployScriptVersion, deployRelease, cfgTemplate, osRhel6PatchVersion, osRhel7PatchVersion, osRhel79PatchVersion, osRhel88PatchVersion, servicePatchVersion, installType, reInstallInst, reStartFromStage, featTest, stopAtStage, mountIsoAgain, setClusterStatus, skipStage, extraParameter, newISOLayout, deployProduct, litpDrop, reDeployVMS, step, osVersion, osVersion8, skipOsInstall, skipLitpInstall, skipPatchInstall, skipEnmInstall, ipmiVersion, redfishVersion, performSnapshot, stageOne, stageTwo,xmlFile,exitAfterISORebuild,skipTearDown,ignoreHa,verifyServices, updateServiceGroups, network, hcInclude, ignoreUpgradePrecheck, productSet, psVersion, edpProfileList, edpVersion, edpPackageList, kickstartFileUrl, skipNasPatchInstall, nasConfig, nasRhelPatch, failOnSedValidationFailure)
            else:
                dmt.deploy.deployMainCsl(clusterId, drop, productOrig, environment, packageList, cfgTemplateOrig, siteEngineeringFilesVersion)
