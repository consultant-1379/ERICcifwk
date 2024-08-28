from django.db import models
from cireports.common_modules.common_functions import *
from django.contrib.auth.models import User

from ciconfig import CIConfig
import logging
logger = logging.getLogger(__name__)
import ast
from operator import itemgetter
from django.core.cache import cache
from django.core.validators import RegexValidator

# Create your models here.
# By default, Django gives each model the following field: id = models.AutoField(primary_key=True)
# This is an auto-incrementing primary key, which sets the id to an Integer Field.
# TODO: Update when Django AutoField supports multiple int types

class Concat(models.Aggregate):
    def add_to_query(self, query, alias, col, source, is_summary):
        aggregate = SQLConcat(col, source=models.CharField(), is_summary=is_summary, **self.extra)
        query.aggregates[alias] = aggregate

class SQLConcat(models.sql.aggregates.Aggregate):
    sql_function = 'group_concat'

    @property
    def sql_template(self):
        if self.extra.get('separator'):
            return '%(function)s(%(field)s SEPARATOR "%(separator)s")'
        else:
            return '%(function)s(%(field)s)'

class Product (models.Model):
    '''
    Overall Product, Specifying the name of the Product and a
    number of boolean fields which are used to turn on/off
    the display of columns in the drop and package tables
    '''
    # id field = unsigned integer
    name            = models.CharField(max_length=50, unique=True)
    pkgName         = models.BooleanField(default=1)
    pkgNumber       = models.BooleanField(default=1)
    pkgVersion      = models.BooleanField(default=1)
    type            = models.BooleanField(default=1)
    pkgRState       = models.BooleanField(default=1)
    platform        = models.BooleanField(default=1)
    category        = models.BooleanField(default=1)
    intendedDrop    = models.BooleanField(default=1)
    deliveredTo     = models.BooleanField(default=1)
    date            = models.BooleanField(default=1)
    prototypeBuild  = models.BooleanField(default=1)
    kgbTests        = models.BooleanField(default=1)
    teamRunningKgb  = models.BooleanField(default=0)
    cidTests        = models.BooleanField(default=1)
    cdbTests        = models.BooleanField(default=1)
    isoIncludedIn   = models.BooleanField(default=1)
    deliver         = models.BooleanField(default=1)
    pri             = models.BooleanField(default=1)
    obsolete        = models.BooleanField(default=1)
    dependencies    = models.BooleanField(default=1)
    isoDownload     = models.BooleanField(default=1)
    size            = models.BooleanField(default=1)

    def __unicode__(self):
        return str(self.name)

class Release (models.Model):
    # id field = unsigned smallint
    name            = models.CharField(max_length=50)
    track           = models.CharField(max_length=20)
    product         = models.ForeignKey(Product)
    iso_artifact    = models.CharField(max_length=100, null=True, blank=True)
    iso_groupId     = models.CharField(max_length=100, default="com.ericsson.nms")
    iso_arm_repo    = models.CharField(max_length=30, default="releases")
    masterArtifact  = models.ForeignKey('MediaArtifact')
    created         = models.DateTimeField()

    def getHubIsoUrl(self):
        config = CIConfig()
        nexusHubUrl = config.get('CIFWK', 'nexus_url')
        return str(nexusHubUrl + "/" +
                self.iso_arm_repo + "/" +
                self.iso_groupId.replace(".", "/"))

    def getLocalIsoUrl(self):
        config = CIConfig()
        nexusLocalUrl = config.get('CIFWK', 'local_nexus_url')
        return str(nexusLocalUrl + "/" +
                self.iso_arm_repo + "/" +
                self.iso_groupId.replace(".", "/"))

    class Meta:
        #To stop Duplicate entries
        unique_together = ('name', 'product')

    def __unicode__(self):
        return str(self.product) + " - " + self.name

class Drop (models.Model):
    # id field = unsigned smallint
    name                 = models.CharField(max_length=50)
    release              = models.ForeignKey(Release)
    planned_release_date = models.DateTimeField(null=True, blank=True)
    actual_release_date  = models.DateTimeField(null=True, blank=True)
    mediaFreezeDate      = models.DateTimeField(null=True, blank=True)
    designbase           = models.ForeignKey("self", null=True, blank=True)
    correctionalDrop     = models.BooleanField(default=False)
    systemInfo           = models.CharField(max_length=100)
    status               = models.CharField(max_length=20, default="open")
    stop_auto_delivery   = models.BooleanField(default=False)

    def getAncestorIds(self):
        keyName = "dropAncestorIds_" + str(self.id)
        dropAncestorIdsCached = cache.get(keyName)
        if (dropAncestorIdsCached != None):
            dropAncestorIds = dropAncestorIdsCached
        else:
            dropAncestorIds = self.rebuildAncestorIdsCache()
        return dropAncestorIds

    def rebuildAncestorIdsCache(self):
        allDrops = Drop.objects.all().order_by('-id')
        allDropsList=allDrops.values('id','designbase__id')
        currentDrop=self.id
        dropAncestorIds = []
        atAbsoluteBase=False
        while not atAbsoluteBase:
            for drop in allDropsList:
                if drop['id'] == currentDrop:
                    dropAncestorIds.append(drop['id'])
                    if drop['designbase__id'] == None:
                        atAbsoluteBase = True
                    else:
                        currentDrop=drop['designbase__id']
                    break
        keyName = "dropAncestorIds_" + str(self.id)
        cache.set(keyName, dropAncestorIds)
        return dropAncestorIds

    def save(self, *args, **kwargs):
        super(Drop, self).save(*args, **kwargs)
        sendDropConfigMessage(self)
        self.rebuildAncestorIdsCache()

    class Meta:
        #To stop Duplicate entries
        unique_together = ('name', 'release')

    def __unicode__(self):
        return str(self.release) + " - " + self.name

class Package (models.Model):
    # id field = unsigned smallint
    name           = models.CharField(max_length=100, unique=True)
    package_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    description    = models.CharField(max_length=255)
    signum         = models.CharField(max_length=7)
    obsolete_after = models.ForeignKey(Drop, null=True, blank=True)
    hide           = models.BooleanField(default=0)
    testware       = models.BooleanField(default=0)
    git_repo       = models.CharField(max_length=100, null=True, blank=True)
    includedInPriorityTestSuite = models.BooleanField(default=False)

    class Meta:
        # TODO: change these to be more specific to packages
        permissions = (
            ('can_edit', 'Edit Package'),
            ('can_deliver', 'Can deliver this package'),
        )

    def __unicode__(self):
        return self.name

class TestwareType (models.Model):
    # id field = unsigned smallint
    type = models.CharField(max_length=15, unique=True)

    def __unicode__(self):
        return str(self.type)

class TestwareTypeMapping (models.Model):
    # id field = unsigned integer
    testware_artifact    = models.ForeignKey(Package)
    testware_type        = models.ForeignKey(TestwareType)

    class Meta:
        #To stop Duplicate entries
        unique_together = ('testware_artifact', 'testware_type')

    def __unicode__(self):
        return str(self.testware_artifact) + " - " + str(self.testware_type)

class ProductPackageMapping (models.Model):
    '''
    Mapping between Product and Package
    '''
    # id field = unsigned smallint
    product   = models.ForeignKey(Product)
    package   = models.ForeignKey(Package)

    class Meta:
        unique_together = ('product', 'package')

    def __unicode__(self):
        return str(self.product) + " - " + str(self.package)


class States (models.Model):
    # id field = unsigned smallint
    state = models.CharField(max_length=20)

    def __unicode__(self):
        return str(self.state)


class MediaArtifactType (models.Model):
    '''
    Media Artifact Type
    '''
    # id field = unsigned smallint
    type = models.CharField(max_length=10)

    def __unicode__(self):
        return str(self.type)


class MediaArtifactCategory (models.Model):
    '''
    Media Artifact Catagories
    '''
    # id field = unsigned smallint
    name   = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural="Media Artifact Categories"


class MediaArtifactDeployType (models.Model):
    '''
     Media Artifact Deploy Type for Auto Deployment
    '''
    # id field = unsigned smallint
    type = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return str(self.type)


class MediaArtifact (models.Model):
    '''
        The artifacts that are associated with a Products Set
    '''
    # id field = unsigned smallint
    name            = models.CharField(max_length=50, unique=True)
    number          = models.CharField(max_length=12, unique=True)
    description     = models.CharField(max_length=255)
    obsoleteAfter   = models.ForeignKey(Drop, null=True, blank=True)
    mediaType       = models.CharField(max_length=10, default="iso")
    hide            = models.BooleanField(default=False)
    testware        = models.BooleanField(default=False)
    category        = models.ForeignKey(MediaArtifactCategory)
    deployType        = models.ForeignKey(MediaArtifactDeployType)

    def __unicode__(self):
        return str(self.name) + " - " + str(self.description)

class ProductSet (models.Model):
    # id field = unsigned smallint
    name            = models.CharField(max_length=50, unique=True)

    def __unicode__(self):
        return str(self.name)

class ProductSetRelease (models.Model):
    # id field = unsigned smallint
    name               = models.CharField(max_length=50, unique=True)
    number             = models.CharField(max_length=12)
    release            = models.ForeignKey(Release)
    productSet         = models.ForeignKey(ProductSet)
    masterArtifact     = models.ForeignKey(MediaArtifact)
    updateMasterStatus = models.BooleanField(default=0)

    class Meta:
        unique_together = ('name', 'number', 'productSet')

    def __unicode__(self):
        return str(self.name) + " - " + str(self.number)

class ProductSetVersion (models.Model):
    # id field = unsigned integer
    version             = models.CharField(max_length=50)
    status              = models.ForeignKey(States)
    current_status      = models.CharField(max_length=2000)
    productSetRelease   = models.ForeignKey(ProductSetRelease)
    drop                = models.ForeignKey(Drop, null=True, blank=True)

    class Meta:
        unique_together = ('version', 'productSetRelease')

    def __unicode__(self):
        return str(self.productSetRelease) + " - " + str(self.version)

    def getOverallWeigthedStatus(self):

        status_list = []
        testNameStatus_list = []
        if self.current_status:
            currentStatusObj = ast.literal_eval(self.current_status)
            for cdbtype,status in currentStatusObj.items():
                cdbTypeObj = CDBTypes.objects.get(id=cdbtype)
                status_dict = {}
                if status.count('#') == 4:
                    state,start,end,testReportNumber,veLog = status.split("#")
                else:
                    state,start,end,testReportNumber = status.split("#")
                cdbTypeSortOrder = CDBTypes.objects.only('sort_order').values('sort_order').get(id=cdbtype)

                testNameStatus_list.append(cdbTypeObj.name + ":" + state)

                status_dict['cdb_type_sort_order'] = cdbTypeSortOrder['sort_order']
                status_dict['status'] = state
                status_list.append(status_dict)

            configuredStatus = ProductSetVersion.updateBasedOnSetConfiguredCDBTypes(self, testNameStatus_list)
            if configuredStatus:
                return configuredStatus

        if status_list:
            status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'))
            return status_list[-1]['status']
        else:
            return "None"

    def updateBasedOnSetConfiguredCDBTypes(self, testNameStatus_list):
        '''
        The updateBasedOnSetConfiguredCDBTypes function returns the overall product set version status based on manual configuartion
        '''
        productDropCDBDisabledCheck = ProductDropToCDBTypeMap.objects.only('product', 'type','drop', 'enabled', 'overallStatusFailure').filter(product__name=self.productSetRelease.productSet.name, drop=self.drop, enabled=False, overallStatusFailure=True)
        for check in productDropCDBDisabledCheck:
            ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self, productCDBType=check).delete()

        productDropCDBFailureCheck = ProductDropToCDBTypeMap.objects.only('product', 'type', 'drop', 'enabled', 'overallStatusFailure').filter(product__name=self.productSetRelease.productSet.name, drop=self.drop, enabled=True, overallStatusFailure=True)

        if testNameStatus_list and productDropCDBFailureCheck:
            if ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self,override=True).exists():
                return "passed"
            typeState = ""
            inProgressDetected = False
            for productSetCheck in productDropCDBFailureCheck:
                if not ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self, productCDBType=productSetCheck).exists():
                    ProductSetVerToCDBTypeMap.objects.create(productSetVersion=self, productCDBType=productSetCheck)

            for productSetCheck in productDropCDBFailureCheck:
                for item in testNameStatus_list:
                    testName,testState = item.split(":")

                    if str(productSetCheck.type) == testName and testState == "failed":
                        ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self).update(runningStatus=False)
                        return testState
                    if str(productSetCheck.type) == testName and testState == "in_progress":
                        ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self, productCDBType=productSetCheck).update(runningStatus=False)
                        inProgressDetected = True
                    elif str(productSetCheck.type) == testName and testState == "passed":
                        if not ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self, productCDBType=productSetCheck, runningStatus=True).exists():
                            ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self, productCDBType=productSetCheck).update(runningStatus=True)
                        typeState = testState

            if inProgressDetected:
                return "in_progress"
            if typeState != "":
                if typeState == "passed":
                    if ProductSetVerToCDBTypeMap.objects.filter(productSetVersion=self, runningStatus=False).exists():
                        return "in_progress"
                return typeState
            else:
                return "not_started"

class ProductSetVersionContent (models.Model):
    # id field = unsigned INT(10)
    productSetVersion       = models.ForeignKey(ProductSetVersion)
    mediaArtifactVersion    = models.ForeignKey('ISObuild')
    status                  = models.ForeignKey(States)

    def __unicode__(self):
        return str(self.productSetVersion) + " - " + str(self.status)
    @property
    def isMasterArtifact(self):
        if self.mediaArtifactVersion.artifactId==self.productSetVersion.productSetRelease.masterArtifact.name:
            return "True"
        else:
            return "False"

class DropMediaArtifactMapping (models.Model):
    # id field = unsigned INT(10)
    mediaArtifactVersion    = models.ForeignKey('ISObuild')
    drop                    = models.ForeignKey(Drop)
    obsolete                = models.BooleanField(default=0)
    released                = models.BooleanField(default=0)
    frozen                  = models.BooleanField(default=0)
    dateCreated             = models.DateTimeField()
    deliveryInfo            = models.TextField(null=True, blank=True)

    def __unicode__(self):
       return u'%s --> %s -- Obsolete (%s) -- Released (%s) -- Frozen (%s)'%(str(self.mediaArtifactVersion), self.drop.name, str(self.obsolete),str(self.released),str(self.frozen))

class PhaseState (models.Model):
    # id field = unsigned smallint
    name            = models.CharField(max_length=15)

class Categories (models.Model):
    # id field = unsigned smallint
    name            = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural="Categories"

class PackageRevision (models.Model):
    """
    A revision of a package.
    """
    # id field = unsigned integer
    LEVELS           = ( ('skipped', 'skipped'),
                         ('not_started', 'not_started'),
                         ('in_progress', 'in_progress'),
                         ('passed', 'passed'),
                         ('failed', 'failed'),)
    package          = models.ForeignKey(Package)
    date_created     = models.DateTimeField()
    published        = models.DateTimeField(null=True, blank=True)

    # TODO: will we use a phase mapping table instead?
    kgb_test         = models.CharField(max_length=20, choices=LEVELS, default="not_started")
    kgb_snapshot_report  = models.BooleanField(default=0)
    team_running_kgb = models.ForeignKey('Component', null=True, blank=True)
    cid_test         = models.CharField(max_length=20, choices=LEVELS, default = "not_started")
    cdb_test         = models.CharField(max_length=20, choices=LEVELS, default = "not_started")

    # Correction field on how to handle deliveries to EU's/EC's
    correction       = models.BooleanField(default=0)

    # Field to determine if this revision was not created with a prototype 3pp - Default is true
    non_proto_build  = models.CharField(max_length=5, default="true")

    # TODO: will we store the link to nexus in here???
    artifact_ref     = models.CharField(max_length=100, null=True, blank=True)
    # These fields map directly to fields in the pom.xml
    # can be used to build hyperlinks to Nexus
    groupId          = models.CharField(max_length=100, null=True, blank=True)
    artifactId       = models.CharField(max_length=100, null=True, blank=True)
    version          = models.CharField(max_length=100, null=True, blank=True)
    autodrop         = models.CharField(max_length=100)
    autodeliver      = models.BooleanField(default=0)
    # Initially we won't use these but we may in the future
    m2type           = models.CharField(max_length=100, null=True, blank=True)
    m2qualifier      = models.CharField(max_length=100, null=True, blank=True)
    last_update      = models.DateTimeField(auto_now_add=True)
    arm_repo         = models.CharField(max_length=30, default="releases")
    platform         = models.CharField(max_length=30, default="None")
    category         = models.ForeignKey(Categories)
    media_path       = models.CharField(max_length=250, null=True, blank=True)
    isoExclude       = models.BooleanField(default=0)
    infra            = models.BooleanField(default=0)
    size             = models.PositiveIntegerField(default=0)

    class Meta:
        permissions = (
            ('can_modify_test_status', 'Can modify the test status of a package revision'),
        )
        unique_together = ('groupId', 'artifactId', 'version', 'platform', 'arm_repo', 'm2type')

    def getNexusDeployUrl(self, product=None):
        config = CIConfig()
        if product != None:
            try:
                nexusReleaseUrl = config.get('DMT_AUTODEPLOY', str(product)+'_nexus_url')
            except:
                nexusReleaseUrl = config.get('DMT_AUTODEPLOY', 'nexus_url')
        else:
            nexusReleaseUrl = config.get('CIFWK', 'nexus_url')
        if ( product != "TOR" and product != "ENM" ):
            return str(nexusReleaseUrl + "/" +
                self.arm_repo + "/" +
                self.groupId.replace(".", "/") +
                "/" + self.artifactId +
                "/" + self.version +
                "/" + self.package.name + "-" + self.version + "." + self.m2type)
        else:
            return str(nexusReleaseUrl + "/" +
                self.groupId.replace(".", "/") +
                "/" + self.artifactId +
                "/" + self.version +
                "/" + self.package.name + "-" + self.version + "." + self.m2type)

    def getNexusUrl(self, product=None):
        config = CIConfig()
        if Product != None:
            try:
                nexusReleaseUrl = config.get('CIFWK', str(product)+'_nexus_url')
            except:
                nexusReleaseUrl = config.get('CIFWK', 'nexus_url')
        else:
            nexusReleaseUrl = config.get('CIFWK', 'nexus_url')
        return str(nexusReleaseUrl + "/" +
                self.arm_repo + "/" +
                self.groupId.replace(".", "/") +
                "/" + self.artifactId +
                "/" + self.version +
               "/" + self.package.name + "-" + self.version + "." + self.m2type)

    def getRState(self):
        return convertVersionToRState(self.version)

    def __unicode__(self):
        try:
            self.package.name
            return u'%s-%s'%(self.package.name, self.version)
        except (Package.DoesNotExist), (ex):
            return u'Package.DoesNotExist, problem: %s'%(str(ex))
    def getPackageName(self):
        return self.package.name

class DropPackageMapping (models.Model):
    # id field = unsigned integer
    package_revision = models.ForeignKey(PackageRevision)
    drop             = models.ForeignKey(Drop)
    obsolete         = models.BooleanField(default=0)
    released         = models.BooleanField(default=0)
    date_created     = models.DateTimeField()
    delivery_info    = models.TextField()
    deliverer_mail   = models.CharField(max_length=100, default="None", null=True, blank=True)
    deliverer_name   = models.CharField(max_length=50, default="None", null=True, blank=True)
    kgb_test        = models.CharField(max_length=20, null=True, blank=True)
    testReport      = models.TextField(null=True, blank=True)
    kgb_snapshot_report   = models.BooleanField(default=0)

    def __unicode__(self):
       return u'%s --> %s -- Obsolete (%s) -- Released (%s)'%(str(self.package_revision), self.drop.name, str(self.obsolete),str(self.released))

class ObsoleteInfo (models.Model):
    # id field = unsigned integer
    dpm    = models.ForeignKey(DropPackageMapping, null=True, blank=True)
    signum = models.CharField(max_length=100)
    reason = models.TextField()
    time_obsoleted = models.DateTimeField(null=True, blank=True)
    def __unicode__(self):
       return u'%s --> %s '%(str(self.dpm.package_revision), str(self.signum))

class ObsoleteMediaInfo (models.Model):
    # id field = unsigned integer
    dropMediaArtifactMapping = models.ForeignKey(DropMediaArtifactMapping, null=True, blank=True)
    signum = models.CharField(max_length=100)
    reason = models.TextField()
    time_obsoleted = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return u'%s --> %s '%(str(self.dropMediaArtifactMapping.mediaArtifactVersion), str(self.signum))

class SolutionSet (models.Model):
    """
    Solution set definition

    A Solution Set is a collection of common packages which make up a single
    deliverable piece of functionality. Solution sets are versioned in the
    same way as packages. Solution sets contain multiple packages, and those
    packages can be delivered to multiple solution sets simultaneously.
    """
    # id field = unsigned smallint
    name = models.CharField(max_length=50)
    package_number = models.CharField(max_length=12)
    def __unicode__(self):
        return self.name

class SolutionSetRevision (models.Model):
    """
    A revision of a solution set. This is the specific release of this solution set.
    """
    # id field = unsigned integer
    solution_set     = models.ForeignKey(SolutionSet)
    version          = models.CharField(max_length=100)
    def __unicode__(self):
        return str(self.solution_set) + " " + self.version

class SolutionSetContents (models.Model):
    """
    A mapping of packages to solution sets. This mapping allows for a specific
    package revision to be delivered to multiple solution sets. Whether this is
    desirable is open to discussion.
    """
    # id field = integer
    solution_set_rev = models.ForeignKey(SolutionSetRevision)
    packagerevision  = models.ForeignKey(PackageRevision)
    def __unicode__(self):
        return str(self.packagerevision) + " --> " + str(self.solution_set_rev)

class pri (models.Model):
    # id field = unsigned smallint
    pkgver          = models.ForeignKey(PackageRevision)
    first_pkgver    = models.ForeignKey(PackageRevision, related_name='+', null=True, blank=True)
    fault_id        = models.CharField(max_length=50)
    fault_desc      = models.TextField(blank=True)
    fault_type      = models.CharField(max_length=50)
    drop            = models.ForeignKey(Drop,null=True, blank=True)
    status          = models.CharField(max_length=50)
    priority        = models.CharField(max_length=50)
    node_pri        = models.BooleanField(default=1)
    comment         = models.CharField(max_length=500)

    def __unicode__(self):
        return self.fault_id


class ISObuild (models.Model):
    '''
      This table stores the revisions of media artifacts
      ISObuild to link product - release - drop  with a version of ISO
    '''
    # id field = unsigned INT(10)
    version                 = models.CharField(max_length=100, null=True, blank=True)
    groupId                 = models.CharField(max_length=100)
    artifactId              = models.CharField(max_length=100)
    mediaArtifact           = models.ForeignKey(MediaArtifact, null=True, blank=True)
    drop                    = models.ForeignKey(Drop, null=True, blank=True)
    build_date              = models.DateTimeField()
    current_status          = models.CharField(max_length=2000, null=True, blank=True)
    overall_status          = models.ForeignKey(States, null=True, blank=True)
    arm_repo                = models.CharField(max_length=50)
    sed_build               = models.ForeignKey('dmt.Sed', blank=True, null = True, related_name = 'sedbuild')
    deploy_script_version   = models.CharField(max_length=100, blank = True, null = True)
    mt_utils_version        = models.CharField(max_length=100, blank = True, null = True)
    size                    = models.BigIntegerField(default=0)
    active                  = models.BooleanField(default=1)
    externally_released     = models.BooleanField(default=0)
    externally_released_ip  = models.BooleanField(default=0)
    externally_released_rstate = models.CharField(max_length=15, null=True, blank=True)
    systemInfo              = models.CharField(max_length=100)

    def getCurrentCDBStatuses(self):
        status_list = []
        if self.current_status:
            currentStatusObj = ast.literal_eval(self.current_status)
            for cdbtype,status in currentStatusObj.items():
                status_dict = {}
                if status.count('#') == 4:
                    state,start,end,testReportNumber,veLog = status.split("#")
                else:
                    state,start,end,testReportNumber = status.split("#")
                cdbtypeObj = CDBTypes.objects.get(id=cdbtype)
                cdb_type_name = cdbtypeObj.name
                cdb_type_sort_order = cdbtypeObj.sort_order
                report=None
                if testReportNumber != "None" and testReportNumber != "":
                    try:
                        testResultsObj=TestResults.objects.get(id=testReportNumber)
                        report = testResultsObj.test_report_directory
                    except Exception as e:
                        logger.error("Error: " +str(e))

                    base_url = '/' + self.drop.release.product.name + '/' + self.drop.name + '/' + self.version + '/' + cdb_type_name
                    if state == 'passed_manual':
                        report = base_url + '/returnKGBreadyDetails/' + testReportNumber
                    elif state == 'caution':
                        report = base_url + '/returnCautionStatusDetails/' + testReportNumber
                    elif state == 'passed' or state == 'failed':
                        report = base_url + '/returnisoreport/' + testReportNumber

                status_dict['cdb_type_name'] = cdb_type_name
                status_dict['cdb_type_sort_order'] = cdb_type_sort_order
                status_dict['test_report_link'] = report
                status_dict['status'] = state
                status_dict['started_date'] = start
                status_dict['ended_date'] = end
                status_list.append(status_dict)

        status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'), reverse=True)
        return status_list

    def getHubIsoDeployUrl(self, product=None):
        config = CIConfig()
        if product != None:
            nexusHubUrl = config.get('DMT_AUTODEPLOY', str(product)+'_nexus_url')
        else:
            nexusHubUrl = config.get('DMT_AUTODEPLOY', 'nexus_url')
        if ( product != "TOR" and product != "ENM" ):
            return str(nexusHubUrl + "/" +
                         self.arm_repo + "/" +
                         self.groupId.replace(".", "/"))
        else:
            return str(nexusHubUrl + "/" +
                         self.groupId.replace(".", "/"))

    def getHubIsoDeployBackupUrl(self, product=None):
        config = CIConfig()
        nexusHubUrl = config.get('DMT_AUTODEPLOY', 'nexus_url')
        return str(nexusHubUrl + "/" +
                 self.arm_repo + "/" +
                 self.groupId.replace(".", "/"))


    def getHubIsoUrl(self):
        config = CIConfig()
        nexusHubUrl = config.get('CIFWK', 'nexus_url')
        return str(nexusHubUrl + "/" +
                 self.arm_repo + "/" +
                 self.groupId.replace(".", "/"))

    def getLocalIsoUrl(self, product=None):
        config = CIConfig()
        nexusLocalUrl = config.get('CIFWK', 'AthloneEiffelProxy_nexus_url')
        if ( product != "TOR" and product != "ENM" ):
            arm_repo_location = self.arm_repo
            if self.arm_repo == "releases":
               arm_repo_location = "enm_"+ self.arm_repo
            return str(nexusLocalUrl + "/" +
                     arm_repo_location + "/" +
                     self.groupId.replace(".", "/"))
        else:
            return str(config.get("DMT_AUTODEPLOY", "ENM_nexus_url") + "/" +
                    self.groupId.replace(".", "/"))

    def getGroupIdForUrl(self):
        return str(self.groupId.replace(".", "/"))

    def getRState(self):
        return convertVersionToRState(self.version)

    def getLatestISO(self):
        latestISO = ISObuild.objects.filter(drop=self.drop).filter(mediaArtifact__testware=0, mediaArtifact__category__name="productware").order_by('-build_date')[0]
        if self == latestISO:
            return 1
        else:
            return 0

    def getOverallWeigthedStatus(self):

        status_list = []
        testNameStatus_list = []
        if self.current_status:
            currentStatusObj = ast.literal_eval(self.current_status)
            for cdbtype,status in currentStatusObj.items():
                cdbTypeObj = CDBTypes.objects.get(id=cdbtype)
                status_dict = {}
                if status.count('#') == 4:
                    state,start,end,testReportNumber,veLog = status.split("#")
                else:
                    state,start,end,testReportNumber = status.split("#")
                testNameStatus_list.append(cdbTypeObj.name + ":" + state)
                cdbTypeSortOrder = CDBTypes.objects.only('sort_order').values('sort_order').get(id=cdbtype)

                status_dict['cdb_type_sort_order'] = cdbTypeSortOrder['sort_order']
                status_dict['status'] = state
                status_list.append(status_dict)

            productDropCDBFailureCheck = ProductDropToCDBTypeMap.objects.only('product', 'drop', 'enabled', 'overallStatusFailure').filter(product__name=self.drop.release.product.name, drop=self.drop, enabled=True, overallStatusFailure=True)
            if testNameStatus_list and productDropCDBFailureCheck:
                typeState = ""
                for productSetCheck in productDropCDBFailureCheck:
                    for item in testNameStatus_list:
                        testName,testState = item.split(":")
                        if str(productSetCheck.type) == testName and testState == "failed":
                            return testState
                        if str(productSetCheck.type) == testName and testState == "in_progress":
                            testState = testState
                        elif str(productSetCheck.type) == testName:
                            typeState = testState
                if testState == "in_progress":
                    return testState
                if typeState != "":
                    return typeState
        if status_list:
            status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'))
            return status_list[-1]['status']
        else:
            return "None"
    class Meta:
        #To stop Duplicate entries
         unique_together = ('version', 'groupId', 'artifactId', 'drop')


    def __unicode__(self):
        return str(self.drop) + " - " + str(self.mediaArtifact.name) +  " - version: " +  str(self.version) +" - Testware: " + str(self.mediaArtifact.testware)

class ISObuildMapping (models.Model):
    """
    ISObuildMapping to link ISO with drops and packages

    """
    # id field = unsigned INT(10)
    iso              = models.ForeignKey(ISObuild)
    package_revision = models.ForeignKey(PackageRevision)
    drop             = models.ForeignKey(Drop)
    overall_status   = models.ForeignKey(States, null=True, blank=True)
    kgb_test        = models.CharField(max_length=20, null=True, blank=True)
    testReport      = models.TextField(null=True, blank=True)
    kgb_snapshot_report   = models.BooleanField(default=0)

    def __unicode__(self):
        return str(self.iso) + " --> " + str(self.package_revision)

class ProductTestwareMediaMapping (models.Model):
    """
    Product Media Aritfact version to Testware Media Artifact version Mapping
    """
    # id field = unsigned INT(10)
    productIsoVersion  = models.ForeignKey(ISObuild, related_name='productIsoVersion')
    testwareIsoVersion = models.ForeignKey(ISObuild, related_name='testwareIsoVersion')

    def __unicode__(self):
        return str(self.productIsoVersion) + " --> " + str(self.testwareIsoVersion)


class DocumentType(models.Model):
    # id field = unsigned integer
    type = models.CharField(max_length=255, unique=True)
    description = models.TextField()

    def __unicode__(self):
        return str(self.type)

class Document (models.Model):
    # id field = unsigned integer
    document_type = models.ForeignKey(DocumentType)
    name = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    number = models.CharField(max_length=50)
    revision = models.CharField(max_length=5)
    drop = models.ForeignKey(Drop)
    deliveryDate = models.DateTimeField()
    link = models.URLField(max_length=200)
    cpi = models.BooleanField(default=0)
    owner = models.CharField(max_length=50)
    comment = models.TextField(null=True, blank=True)
    obsolete_after = models.ForeignKey(Drop, null=True, blank=True, related_name='+')

    def __unicode__(self):
        return u'%s' % self.name +" -->" +str(self.name) + "-->" +str(self.author) + "-->" +str(self.number) + "-->" +str(self.drop)

class TestwareArtifact (models.Model):
    # id field = unsigned smallint
    name            = models.CharField(max_length=50, unique=True)
    artifact_number = models.CharField(max_length=12, unique=True)
    description     = models.CharField(max_length=255)
    signum          = models.CharField(max_length=7)
    includedInPriorityTestSuite = models.BooleanField(default=False)

    def __unicode__(self):
        return str(self.name)

class TestwareRevision (models.Model):
    # id field = unsigned integer
    testware_artifact    = models.ForeignKey(TestwareArtifact)
    date_created         = models.DateTimeField()
    version              = models.CharField(max_length=50, null=True, blank=True)
    groupId              = models.CharField(max_length=100, null=True, blank=True)
    artifactId           = models.CharField(max_length=100, null=True, blank=True)
    obsolete             = models.BooleanField(default=0)
    execution_version    = models.CharField(max_length=50)
    execution_groupId    = models.CharField(max_length=100)
    execution_artifactId = models.CharField(max_length=100)
    validTestPom = models.BooleanField(default=1)
    kgb_status   = models.BooleanField(default=0)
    cdb_status   = models.BooleanField(default=0)

    def __unicode__(self):
        return str(self.testware_artifact) + " --> " + str(self.version)

class TestwarePackageMapping (models.Model):
    # id field = unsigned integer
    testware_artifact = models.ForeignKey(TestwareArtifact)
    package          = models.ForeignKey(Package)

    def __unicode__(self):
        return str(self.testware_artifact) + " --> " + str(self.package)

class FEMLink (models.Model):
    # id field = unsigned integer
    product = models.ForeignKey(Product)
    name = models.CharField(max_length=50)
    fem_link = models.URLField(max_length=200)
    FemBaseKGBJobURL = models.BooleanField(default=0)

    def __unicode__(self):
        return str(self.name) + " --> " + str(self.fem_link) + " --> " + str(self.product)

    def save(self, *args, **kwargs):
        if self.FemBaseKGBJobURL:
            try:
                FemBaseKGBJobURLCurrent = FEMLink.objects.get(FemBaseKGBJobURL=1)
                if self != FemBaseKGBJobURLCurrent:
                    FemBaseKGBJobURLCurrent.FemBaseKGBJobURL = 0
                    FemBaseKGBJobURLCurrent.save()
            except FEMLink.DoesNotExist:
                pass
        super(FEMLink, self).save(*args, **kwargs)

class TestResults (models.Model):
    # id field = unsigned integer
    passed      = models.PositiveSmallIntegerField(null=True, blank=True)
    failed      = models.PositiveSmallIntegerField(null=True, blank=True)
    total       = models.PositiveSmallIntegerField(null=True, blank=True)
    testdate    = models.DateTimeField()
    tag         = models.CharField(max_length=100, null=True, blank=True)
    phase       = models.CharField(max_length=10, null=True, blank=True)
    test_report =  models.TextField(null=True, blank=True)
    test_report_directory = models.CharField(max_length=200, null=True, blank=True)
    testware_pom_directory = models.CharField(max_length=100, null=True, blank=True)
    host_properties_file = models.CharField(max_length=100, null=True, blank=True)

    def __unicode__(self):
        return str(self.passed) + " --> " + str(self.failed)

class TestResultsToVisEngineLinkMap (models.Model):
    # id field = unsigned integer
    testware_run        = models.ForeignKey(TestResults)
    veLog               = models.CharField(max_length=1000, null=True, blank=True)

    def __unicode__(self):
        return str(self.veLog)

class TestResultsToTestwareMap (models.Model):
    # id field = unsigned integer
    testware_revision   = models.ForeignKey(TestwareRevision)
    package_revision    = models.ForeignKey(PackageRevision)
    testware_artifact   = models.ForeignKey(TestwareArtifact)
    package             = models.ForeignKey(Package)
    testware_run        = models.ForeignKey(TestResults)

    def __unicode__(self):
        return str(self.testware_artifact) + " --> " + str(self.package)

class TestResultsWithoutTestware (models.Model):
    # id field = unsigned integer
    package_revision    = models.ForeignKey(PackageRevision)
    package             = models.ForeignKey(Package)
    testware_run        = models.ForeignKey(TestResults)

    def __unicode__(self):
        return str(self.package)

class Clue (models.Model):
    '''
    Confidence Level Updated Events
    '''
    # id field = integer
    LEVELS           = ( ('skipped', 'skipped'),
                         ('not_started', 'not_started'),
                         ('in_progress', 'in_progress'),
                         ('passed', 'passed'),
                         ('failed', 'failed'),)
    package         = models.ForeignKey(Package)
    codeReview      = models.CharField(max_length=20, choices=LEVELS, default="not_started", null=True, blank=True)
    codeReviewTime  = models.DateTimeField(null=True, blank=True)
    unit            = models.CharField(max_length=20, choices=LEVELS, default="not_started", null=True, blank=True)
    unitTime        = models.DateTimeField(null=True, blank=True)
    acceptance      = models.CharField(max_length=20, choices=LEVELS, default="not_started", null=True, blank=True)
    acceptanceTime  = models.DateTimeField(null=True, blank=True)
    release         = models.CharField(max_length=20, choices=LEVELS, default="not_started", null=True, blank=True)
    releaseTime     = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return str(self.package) + " --> " + str(self.release)

class ClueTrend (models.Model):
    '''
    Confidence Level Updated Events
    '''
    # id field = integer
    package         = models.ForeignKey(Package)
    codeReview      = models.CharField(max_length=20, null=True, blank=True)
    codeReviewTimeStarted  = models.DateTimeField(null=True, blank=True)
    codeReviewTimeFinished  = models.DateTimeField(null=True, blank=True)
    unit            = models.CharField(max_length=20, null=True, blank=True)
    unitTimeStarted        = models.DateTimeField(null=True, blank=True)
    unitTimeFinished        = models.DateTimeField(null=True, blank=True)
    acceptance      = models.CharField(max_length=20, null=True, blank=True)
    acceptanceTimeStarted  = models.DateTimeField(null=True, blank=True)
    acceptanceTimeFinished  = models.DateTimeField(null=True, blank=True)
    release         = models.CharField(max_length=20, null=True, blank=True)
    releaseTimeStarted     = models.DateTimeField(null=True, blank=True)
    releaseTimeFinished     = models.DateTimeField(null=True, blank=True)
    lastUpdate      = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return str(self.package) + " --> " + str(self.lastUpdate)

class TestsInProgress (models.Model):
    # id field = unsigned integer
    package_revision    = models.ForeignKey(PackageRevision)
    phase               = models.CharField(max_length=10, null=True, blank=True)
    datestarted         = models.DateTimeField()
    veLog               = models.CharField(max_length=1000, null=True, blank=True)

    def __unicode__(self):
        return str(self.package_revision) + ":" + str(self.phase) + ":" + str(self.datestarted)

class CDBTypes(models.Model):
    '''
    Customer Deployable Baselines Types
    '''
    # id field  = unsigned smallint
    name        = models.CharField(max_length=20, unique=True)
    sort_order  = models.SmallIntegerField(default='0', null=False)

    def __unicode__(self):
        return str(self.name)

    def typeStripUnderscores(self):
        return str(self.name.replace('_', ' '))

    class Meta:
        verbose_name_plural="CDB Types"

class CDB(models.Model):
    '''
    Multiple Customer Deployable Baselines
    '''
    LEVELS        = ( ('skipped', 'skipped'),
                      ('not_started', 'not_started'),
                      ('in_progress', 'in_progress'),
                      ('passed', 'passed'),
                      ('failed', 'failed'),)
    # id field  = unsigned integer
    drop            = models.ForeignKey(Drop)
    type            = models.ForeignKey(CDBTypes)
    status          = models.CharField(max_length=20, choices=LEVELS, default="not_started")
    started         = models.DateTimeField(null=True, blank=True)
    lastUpdated     = models.DateTimeField(null=True, blank=True)
    report          = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return str(self.drop) + " --> " + str(self.type.name)

class CDBHistory(models.Model):
    '''
    Historic Multiple Customer Deployable Baselines
    '''
    LEVELS        = ( ('skipped', 'skipped'),
                      ('not_started', 'not_started'),
                      ('in_progress', 'in_progress'),
                      ('passed', 'passed'),
                      ('failed', 'failed'),)
    # id field  = unsigned integer
    drop            = models.ForeignKey(Drop)
    type            = models.ForeignKey(CDBTypes)
    status          = models.CharField(max_length=20, choices=LEVELS, default="not_started")
    started         = models.DateTimeField(null=True, blank=True)
    lastUpdated     = models.DateTimeField(null=True, blank=True)
    report          = models.TextField(null=True, blank=True)
    parent          = models.ForeignKey("self", null=True, blank=True)

    def __unicode__(self):
        return str(self.drop) + " --> " + str(self.type.name) + " --> " + str(self.status) + " --> " + str(self.started)

    class Meta:
        verbose_name_plural="CDB Histories"

class CDBPkgMapping (models.Model):
    """
    CDBPkgMapping table is used to link packages with a CDB
    """
    # id field  = unsigned integer
    cdbHist          = models.ForeignKey(CDBHistory)
    package_revision = models.ForeignKey(PackageRevision)

    def __unicode__(self):
        return str(self.cdbHist) + " --> " + str(self.package_revision)

class PackageDependencyMapping (models.Model):
    # id field  = unsigned integer
    package                  = models.ForeignKey(Package)
    packageRevision          = models.ForeignKey(PackageRevision, null=True, blank=True)
    dependentPackage         = models.ForeignKey(Package, related_name='+')
    dependentPackageRevision = models.ForeignKey(PackageRevision, related_name='+', null=True, blank=True)
    installOrder             = models.PositiveSmallIntegerField()

    def __unicode__(self):
        return str(self.package) + " --> " + str(self.dependentPackage)

class ISOTestResultsToTestwareMap (models.Model):
    # id field  = unsigned INT(10)
    isobuild            = models.ForeignKey(ISObuild)
    testware_revision   = models.ForeignKey(TestwareRevision)
    testware_artifact   = models.ForeignKey(TestwareArtifact)
    testware_run        = models.ForeignKey(TestResults)

    def __unicode__(self):
        return str(self.testware_artifact) + " --> " + str(self.isobuild)

class PSTestResultsToTestwareMap (models.Model):
    # id field  = unsigned integer
    product_set_version            = models.ForeignKey(ProductSetVersion)
    testware_revision   = models.ForeignKey(TestwareRevision)
    testware_artifact   = models.ForeignKey(TestwareArtifact)
    testware_run        = models.ForeignKey(TestResults)

    def __unicode__(self):
        return str(self.testware_artifact) + " --> " + str(self.product_set_version)

class NonProductEmail(models.Model):
    # id field  = integer
    area = models.CharField(max_length=100)
    email =  models.CharField(max_length=100)

    def __unicode__(self):
        return str(self.area) + " --> " + str(self.email)


class ProductEmail(models.Model):
    # id field  = integer
    product = models.ForeignKey(Product)
    email =  models.CharField(max_length=100)

    def __unicode__(self):
        return str(self.product) + " --> " + str(self.email)

class ConfigProducts (models.Model):
    # id field = unsigned smallint
    product = models.ForeignKey(Product)
    choice = models.CharField(max_length=100)
    num = models.PositiveSmallIntegerField(null=True, blank=True)
    order_id = models.PositiveSmallIntegerField(null=True, blank=True)
    active = models.BooleanField(default=1)

    def __unicode__(self):
        return str(self.product)

class ImageContent (models.Model):
    """
    Storage of the content that makes up an image
    """
    # id field = unsigned integer
    packageRev              = models.ForeignKey(PackageRevision)
    installedArtifacts      = models.TextField(null=True, blank=True)
    installedDependencies   = models.TextField(null=True, blank=True)
    dateCreated             = models.DateTimeField(null=True)
    parent                  = models.ForeignKey("self", null=True, blank=True)

    def __unicode__(self):
        return str(self.packageRev.package.name)

class Label (models.Model):
    # id field = unsigned smallint
    name = models.CharField(max_length=100, unique=True)
    def __unicode__(self):
        return str(self.name)

    def clean(self):
        if self.name:
            self.name = re.sub(r' ','', str(self.name))

class Component (models.Model):
    # id field = unsigned smallint
    customValidator = RegexValidator(r'^[0-9a-zA-Z-_]*$', 'Only alphanumeric characters, underscore(s) and hyphen(s) are allowed.')
    product = models.ForeignKey(Product)
    label = models.ForeignKey(Label)
    parent = models.ForeignKey("self", null=True, blank=True)
    element = models.CharField(max_length=100, validators=[customValidator])
    dateCreated = models.DateTimeField()
    deprecated = models.BooleanField(default=0)

    class Meta:
        unique_together = ('parent', 'element')

    def __unicode__(self):
        return str(self.product.name) + " --> " + str(self.element)

    def clean(self):
       if self.element:
           self.element = re.sub(r' ', '', str(self.element))

class PackageComponentMapping (models.Model):
    # id field = unsigned smallint
    component = models.ForeignKey(Component)
    package = models.ForeignKey(Package)

    class Meta:
        unique_together = ('component', 'package')
    def __unicode__(self):
        return str(self.component.element) + " --> " + str(self.package.name)

class DropLimitedReason (models.Model):
    # id field = unsigned smallint
    reason  = models.CharField(max_length=100)

    def __unicode__(self):
        return str(self.reason)


class DropActivity (models.Model):
    # id field = unsigned smallint
    drop    = models.ForeignKey(Drop)
    action  = models.CharField(max_length=100)
    desc    = models.TextField()
    user    = models.CharField(max_length=10)
    date    = models.DateTimeField()
    limitedReason  = models.ForeignKey(DropLimitedReason, blank=True, null = True)

    def __unicode__(self):
        return str(self.drop.name) + " --> " + str(self.user)

    class Meta:
        verbose_name_plural="Drop Activities"

class DeliveryGroup (models.Model):
    # id field = unsigned integer
    drop                 = models.ForeignKey(Drop)
    deleted              = models.BooleanField(default=0)
    delivered            = models.BooleanField(default=0)
    obsoleted            = models.BooleanField(default=0)
    creator              = models.CharField(max_length=100)
    component            = models.ForeignKey(Component, blank=True, null = True)
    modifiedDate         = models.DateTimeField()
    missingDependencies  = models.BooleanField(default=0)
    warning              = models.BooleanField(default=0)
    createdDate          = models.DateTimeField(null=True, blank=True)
    deliveredDate        = models.DateTimeField(null=True, blank=True)
    autoCreated          = models.BooleanField(default=0)
    consolidatedGroup    = models.BooleanField(default=0)
    newArtifact          = models.BooleanField(default=0)
    ccbApproved          = models.BooleanField(default=0)
    bugOrTR              = models.BooleanField(default=0)

    def __unicode__(self):
        return str(self.id) + " --> " + str(self.drop.name)

class JiraIssue (models.Model):
    # id field = unsigned integer
    jiraNumber      = models.CharField(max_length=20)
    issueType       = models.CharField(max_length=30)

    def __unicode__(self):
        return str(self.id) + ": " + str(self.jiraNumber) + " --> " + str(self.issueType)

class JiraTypeExclusion (models.Model):
    # id field = unsigned integer
    jiraType       = models.CharField(max_length=30, unique=True)

    def __unicode__(self):
        return str(self.jiraType)

class JiraDeliveryGroupMap (models.Model):
    # id field = unsigned integer
    deliveryGroup   = models.ForeignKey(DeliveryGroup)
    jiraIssue       = models.ForeignKey(JiraIssue)

    def __unicode__(self):
        return str(self.deliveryGroup) + " --> " + str(self.jiraIssue)

class JiraLabel (models.Model):
    # id field = unsigned integer
    name        = models.CharField(max_length=50)
    type        = models.CharField(max_length=30)

    def __unicode__(self):
        return str(self.name)

class JiraProjectException (models.Model):
    # id field = unsigned integer
    projectName       = models.CharField(max_length=45, unique=True)

    def __unicode__(self):
        return str(self.projectName)

class LabelToJiraIssueMap (models.Model):
    # id field = unsigned integer
    jiraIssue   = models.ForeignKey(JiraIssue)
    jiraLabel   = models.ForeignKey(JiraLabel)

class DeliverytoPackageRevMapping (models.Model):
    # id field = unsigned integer
    deliveryGroup   = models.ForeignKey(DeliveryGroup)
    packageRevision = models.ForeignKey(PackageRevision)
    team            = models.TextField()
    kgb_test        = models.CharField(max_length=20, null=True, blank=True)
    testReport      = models.TextField(null=True, blank=True)
    kgb_snapshot_report   = models.BooleanField(default=0)
    newArtifact     = models.BooleanField(default=0)
    services        = models.TextField()

    def __unicode__(self):
        return str(self.deliveryGroup) + " --> " + str(self.packageRevision)

    class Meta:
        unique_together = ('deliveryGroup', 'packageRevision')

class DeliveryGroupComment (models.Model):
    # id field = unsigned integer
    deliveryGroup   = models.ForeignKey(DeliveryGroup)
    comment         = models.TextField()
    date            = models.DateTimeField()

    def __unicode__(self):
        return str(self.deliveryGroup) + " --> " + str(self.comment)

class PackageNameExempt (models.Model):
    # id field = unsigned smallint
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return str(self.name)

class ProductDropToCDBTypeMap (models.Model):
    '''
    '''
    product         = models.ForeignKey(Product)
    drop            = models.ForeignKey(Drop)
    type            = models.ForeignKey(CDBTypes)
    overallStatusFailure = models.BooleanField(default=True)
    enabled         = models.BooleanField(default=False)

    class Meta:
        unique_together = ('product', 'drop', 'type')

    def __unicode__(self):
        return "Product: " + str(self.product) + " Type: " + str(self.type.name)

class ProductSetVerToCDBTypeMap (models.Model):
    '''
    '''
    # id field = unsigned int
    productSetVersion       = models.ForeignKey(ProductSetVersion)
    productCDBType          = models.ForeignKey(ProductDropToCDBTypeMap)
    runningStatus           = models.BooleanField(default=False)
    override                = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        id = self.id
        if id is not None:
            orig = ProductSetVerToCDBTypeMap.objects.only('override').get(id=id)
        super(ProductSetVerToCDBTypeMap, self).save(*args, **kwargs)
        if id is not None and self.override != orig.override:
            sendEiffelBaselineUpdatedMessage(self.productSetVersion, self.override)
            buildlogManualStatusUpdate(self.productSetVersion, self.override)

    class Meta:
        unique_together = ('productSetVersion', 'productCDBType')

    def __unicode__(self):
        return "Product Set Version: " + str(self.productSetVersion.version)

class IsotoDeliveryGroupMapping (models.Model):
    # id field = unsigned INT(10)
    iso                  = models.ForeignKey(ISObuild)
    deliveryGroup        = models.ForeignKey(DeliveryGroup)
    deliveryGroup_status = models.TextField()
    modifiedDate         = models.DateTimeField()

    def __unicode__(self):
        return str(self.iso) + " --> " + str(self.deliveryGroup)

    class Meta:
        unique_together = ('iso','deliveryGroup')

class DeliveryGroupSubscription (models.Model):
    '''
    Map users to delivery group for subscription emails
    '''
    user                 = models.ForeignKey(User)
    deliveryGroup        = models.ForeignKey(DeliveryGroup)

    def __unicode__(self):
        return str(self.deliveryGroup)

class TestCaseResult (models.Model):
    # id field = unsigned integer
    passed      = models.PositiveSmallIntegerField(null=True, blank=True)
    failed      = models.PositiveSmallIntegerField(null=True, blank=True)
    skipped     = models.PositiveSmallIntegerField(null=True, blank=True)

    def __unicode__(self):
        return str(self.passed) + " --> " + str(self.failed) + " --> " + str(self.skipped)

class PackageWithTestCaseResult (models.Model):
    # id field = unsigned integer
    testdate            = models.DateTimeField()
    package             = models.ForeignKey(Package)
    package_revision    = models.ForeignKey(PackageRevision)
    drop                = models.ForeignKey(Drop)
    testcaseresult      = models.ForeignKey(TestCaseResult)
    phase               = models.CharField(max_length=10, null=True, blank=True)

    def __unicode__(self):
        return str(self.package)

class ReasonsForNoKGBStatus (models.Model):
    # id field = unsigned integer
    reason  = models.CharField(max_length=255)
    active  = models.BooleanField(default=True)

    def __unicode__(self):
        return str(self.reason) + " " + str(self.active)

class GroupsCreatedWithoutPassedKGBTest(models.Model):
    # id field = unsigned integer
    group = models.ForeignKey(DeliveryGroup,null=True, blank=True)
    reason = models.CharField(max_length=255)
    comment = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return str(self.group.id)

class AutoDeliverTeam(models.Model):
    # id field = unsigned integer
    team = models.ForeignKey(Component)

    def __unicode__(self):
        return str(self.team.element)


class DropMediaDeployMapping (models.Model):
    """
    The Mapping Table for the Product Set Drop Deploy information
    """
    # id field = unsigned integer
    dropMediaArtifactMap = models.ForeignKey(DropMediaArtifactMapping)
    product = models.ForeignKey(Product)

    class Meta:
        #To stop Duplicate entries
        unique_together = ('dropMediaArtifactMap', 'product')

    def __unicode__(self):
        return str(self.dropMediaArtifactMap) + " --> " + str(self.product.name)


class ProductSetVersionDeployMapping (models.Model):
    """
    The Mapping Table for the Product Set Version Deploy information
    """
    # id field = unsigned INT(10)
    mainMediaArtifactVersion  = models.ForeignKey(ISObuild, related_name='mainMediaArtifactVersion')
    mediaArtifactVersion = models.ForeignKey(ISObuild, related_name='mediaArtifactVersion')
    productSetVersion         = models.ForeignKey(ProductSetVersion)

    def __unicode__(self):
        return str(self.mainMediaArtifactVersion) + " --> " + str(self.mediaArtifactVersion) + " --> " + str(self.productSetVersion)

class CNImage (models.Model):
    '''
    This class models Image table.
    '''
    image_name = models.CharField(max_length = 100, unique = True)
    image_product_number = models.CharField(max_length = 20, null = True, blank = True)
    repo_name = models.CharField(max_length = 100, null = True, blank = True)

    class Meta:
        unique_together = ('image_name', 'image_product_number')

    def __unicode__(self):
        return str(self.image_name)

class CNImageRevision (models.Model):
    '''
    This class models Image Revision table.
    '''
    image = models.ForeignKey(CNImage)
    parent = models.ForeignKey("self", null = True, blank = True)
    version = models.CharField(max_length = 20, null = False)
    created = models.DateTimeField()
    size = models.PositiveIntegerField(null = True, blank = True)
    gerrit_repo_sha = models.CharField(max_length = 100, null = True, blank = True)

    def __unicode__(self):
        return str(self.image.image_name) + " --> " + str(self.version)

class CNImageContent (models.Model):
    '''
    This class models Image Content table.
    '''
    image_revision = models.ForeignKey(CNImageRevision)
    package_revision = models.ForeignKey(PackageRevision)

    def __unicode__(self):
        return str(self.image_revision.image.image_name) + " --> " + str(self.package_revision)

class CNHelmChart (models.Model):
    '''
    This class models Helm Chart table.
    '''
    helm_chart_name = models.CharField(max_length = 100, unique = True)
    helm_chart_product_number = models.CharField(max_length = 20)

    class Meta:
        unique_together = ('helm_chart_name', 'helm_chart_product_number')

    def __unicode__(self):
        return str(self.helm_chart_name)

class CNHelmChartRevision (models.Model):
    '''
    This class models Helm Chart Revision table.
    '''
    helm_chart = models.ForeignKey(CNHelmChart)
    version = models.CharField(max_length = 20, null = False)
    created = models.DateTimeField()
    size = models.PositiveIntegerField(null = True, blank = True)
    gerrit_repo_sha = models.CharField(max_length = 100, null = True, blank = True)

    def __unicode__(self):
        return str(self.helm_chart.helm_chart_name) + " --> " + str(self.version)

class CNImageHelmChartMapping (models.Model):
    '''
    This class models mapping between Image and Helm Chart.
    '''
    image_revision = models.ForeignKey(CNImageRevision)
    helm_chart_revision = models.ForeignKey(CNHelmChartRevision)

    class Meta:
        unique_together = ('image_revision', 'helm_chart_revision')

    def __unicode__(self):
        return str(self.image_revision) + " - " + str(self.helm_chart_revision)

class CNProductSet (models.Model):
    '''
    This class models Cloud Native product sets
    '''
    product_set_name = models.CharField(max_length = 150, null = False)

    def __unicode__(self):
        return str(self.product_set_name)

class CNProductType (models.Model):
    '''
    This class models Cloud Native product types
    '''
    product_type_name = models.CharField(max_length = 100, null = False, unique = True)

    def __unicode__(self):
        return str(self.product_type_name)

class CNProduct (models.Model):
    '''
    This class models Cloud Native Products.
    '''
    product_set = models.ForeignKey(CNProductSet)
    product_name = models.CharField(null = False, unique = True, max_length = 100)
    product_type = models.ForeignKey(CNProductType)
    repo_name = models.CharField(null = True, max_length = 100)
    published_link = models.CharField(max_length = 500, null = True, blank = True)

    def __unicode__(self):
        return str(self.product_set) + " --> " + str(self.product_type) + " --> " + str(self.product_name)

class CNProductSetVersion (models.Model):
    '''
    This class models Cloud Native Products set versions.
    '''
    product_set_version = models.CharField(null = False, max_length = 20)
    status = models.CharField(null = False, max_length = 500)
    overall_status = models.ForeignKey(States, null=True, blank=True)
    drop_version = models.CharField(null = False, max_length = 20)
    active = models.BooleanField(null = False, default = True)

    def __unicode__(self):
        return str(self.product_set_version) + " --> " + str(self.overall_status)

class CNProductRevision (models.Model):
    '''
    This class models Integration Chart Revision table.
    '''
    product = models.ForeignKey(CNProduct)
    version = models.CharField(max_length = 20, null = False)
    product_set_version = models.ForeignKey(CNProductSetVersion)
    created = models.DateTimeField()
    size = models.PositiveIntegerField(null = True, blank = True)
    gerrit_repo_sha = models.CharField(max_length = 100, null = True, blank = True)
    dev_link = models.CharField(max_length = 500, null = True, blank = True)
    values_file_version = models.CharField(max_length = 20, null = True, blank = True)
    values_file_name = models.CharField(max_length = 100, null = True, blank = True)
    verified = models.BooleanField(null = False, default=0)

    def __unicode__(self):
        return str(self.product.product_name) + " --> " + str(self.version)

class CNHelmChartProductMapping (models.Model):
    '''
    This class models mapping between Helm Chart & Integration Chart.
    '''
    product_revision = models.ForeignKey(CNProductRevision)
    helm_chart_revision = models.ForeignKey(CNHelmChartRevision)

    class Meta:
        unique_together = ('product_revision', 'helm_chart_revision')

    def __unicode__(self):
        return str(self.helm_chart_revision) + " --> " + str(self.product_revision)

class CNConfidenceLevelType (models.Model):
    '''
    This class models Cloud Native Confidence level types
    '''
    confidenceLevelTypeName = models.CharField(max_length = 100, null = False, unique = True)

    def __unicode__(self):
        return str(self.confidenceLevelTypeName)

class RequiredCNConfidenceLevel (models.Model):
    '''
    This class models externally Released MediaArtifacts with MeidaArtifacts.
    '''
    confidence_level_name = models.CharField(max_length = 100, null = False, unique = True)
    confidenceLevelType = models.ForeignKey(CNConfidenceLevelType, blank=True, null=True)
    required = models.BooleanField(null = False, default=1)
    include_baseline = models.BooleanField(null = False, default=0)
    requireBuildLogId = models.BooleanField(null = False, default=0)

    def __unicode__(self):
        return str(self.confidence_level_name)

class RequiredRAMapping (models.Model):
    '''
    This class models RA between Team Inventory tool and CI Portal.
    '''
    team_inventory_ra_name = models.CharField(max_length = 100, null = False, unique = True)
    component = models.ForeignKey(Component)

    def __unicode__(self):
        return str(self.team_inventory_ra_name) + " --> " + str(self.component.element)

class CNDrop (models.Model):
    '''
    This class models drop for cloud native.
    '''
    name = models.CharField(max_length=50, null=False)
    cnProductSet = models.ForeignKey(CNProductSet)
    active_date = models.DateTimeField(null=False)
    reopen = models.BooleanField(default=False)
    designbase = models.ForeignKey("self", null=True, blank=True)

    class Meta:
        unique_together = ('name', 'cnProductSet')

    def __unicode__(self):
        return str(self.cnProductSet) + " - " + self.name

class CNJiraIssue (models.Model):
    '''
    This class models drop for cloud native jira issue.
    '''
    # id field = unsigned integer
    jiraNumber      = models.CharField(max_length=20)
    issueType       = models.CharField(max_length=30)

    def __unicode__(self):
        return str(self.id) + ": " + str(self.jiraNumber) + " --> " + str(self.issueType)

class CNGerrit (models.Model):
    '''
    This class models gerrit info for cloud native.
    '''
    #id field = unsigned integer
    gerrit_link = models.CharField(max_length=255, null=False)

    def __unicode__(self):
        return self.gerrit_link

class CNPipeline (models.Model):
    '''
    This class models drop for cloud native.
    '''
    #id field = unsigned integer
    pipeline_link = models.CharField(max_length=255, null=False)

    def __unicode__(self):
        return self.pipeline_link

class CNDeliveryGroup (models.Model):
    '''
    This class models delivery group for cloud native.
    '''
    #id field = unsigned integer
    cnDrop = models.ForeignKey(CNDrop)
    cnProductSetVersion = models.ForeignKey(CNProductSetVersion, blank=True, null=True)
    cnProductSetVersionSet = models.BooleanField(default=0)
    queued = models.BooleanField(default=0)
    delivered = models.BooleanField(default=0)
    obsoleted = models.BooleanField(default=0)
    deleted = models.BooleanField(default=0)
    creator = models.CharField(max_length=100)
    teamEmail = models.CharField(max_length=100, blank=True, null = True)
    component = models.ForeignKey(Component, blank=True, null = True)
    modifiedDate = models.DateTimeField(null=True, blank=True)
    createdDate = models.DateTimeField(null=True, blank=True)
    deliveredDate = models.DateTimeField(null=True, blank=True)
    obsoletedDate = models.DateTimeField(null=True, blank=True)
    deletedDate = models.DateTimeField(null=True, blank=True)
    missingDependencies = models.BooleanField(default=0)
    bugOrTR = models.BooleanField(default=0)

    def __unicode__(self):
        return str(self.id) + " --> " + str(self.cnDrop.name)

class CNDeliveryGroupComment (models.Model):
    # id field = unsigned integer
    cnDeliveryGroup   = models.ForeignKey(CNDeliveryGroup)
    comment         = models.TextField()
    date            = models.DateTimeField()

    def __unicode__(self):
        return str(self.cnDeliveryGroup) + " --> " + str(self.comment)

class CNDGToCNImageToCNGerritMap (models.Model):
    '''
    This class models mapping for cn delivery group, cn image and cn gerrit.
    '''
    #id field = unsigned integer
    cnDeliveryGroup = models.ForeignKey(CNDeliveryGroup)
    cnImage = models.ForeignKey(CNImage)
    cnGerrit = models.ForeignKey(CNGerrit)
    state = models.ForeignKey(States, default=lambda: States.objects.get(state = "not_obsoleted"))
    revert_change_id = models.CharField(max_length=255, blank=True, null = True)

    def __unicode__(self):
        return str(self.cnDeliveryGroup.id) + " --> " + str(self.cnImage.image_name)

class CNDGToCNProductToCNGerritMap (models.Model):
    '''
    This class models mapping for cn delivery group, cn product (integration charts, integration value for now) and cn gerrit.
    '''
    #id field = unsigned integer
    cnDeliveryGroup = models.ForeignKey(CNDeliveryGroup)
    cnProduct = models.ForeignKey(CNProduct)
    cnGerrit = models.ForeignKey(CNGerrit)
    state = models.ForeignKey(States, default=lambda: States.objects.get(state = "not_obsoleted"))
    revert_change_id = models.CharField(max_length=255, blank=True, null = True)

    def __unicode__(self):
        return str(self.cnDeliveryGroup.id) + " --> " + str(self.cnProduct.product_name)

class CNDGToCNPipelineToCNGerritMap (models.Model):
    '''
    This class models mapping for cn delivery group and cn pipeline and cn gerrit.
    '''
    #id field = unsigned integer
    cnDeliveryGroup = models.ForeignKey(CNDeliveryGroup)
    cnPipeline = models.ForeignKey(CNPipeline)
    cnGerrit = models.ForeignKey(CNGerrit)
    state = models.ForeignKey(States, default=lambda: States.objects.get(state = "not_obsoleted"))
    revert_change_id = models.CharField(max_length=255, blank=True, null = True)

    def __unicode__(self):
        return str(self.cnDeliveryGroup.id) + " --> " + str(self.cnPipeline.pipeline_link)

class CNDGToDGMap (models.Model):
    '''
    This class models mapping for cn delivery group and (pENM) delivery group.
    '''
    #id field = unsigned integer
    cnDeliveryGroup = models.ForeignKey(CNDeliveryGroup)
    deliveryGroup = models.ForeignKey(DeliveryGroup)

    def __unicode__(self):
        return str(self.cnDeliveryGroup.id) + " --> " + str(self.deliveryGroup.id)

class CNDGToCNJiraIssueMap (models.Model):
    '''
    This class models mapping for cn delivery group and cn jira issue.
    '''
    #id field = unsigned integer
    cnDeliveryGroup = models.ForeignKey(CNDeliveryGroup)
    cnJiraIssue = models.ForeignKey(CNJiraIssue)

    def __unicode__(self):
        return str(self.cnDeliveryGroup.id) + " --> " + str(self.cnJiraIssue.jiraNumber)

class CNDeliveryGroupSubscription (models.Model):
    '''
    Map users to cn delivery group for subscription emails
    '''
    user = models.ForeignKey(User)
    cnDeliveryGroup = models.ForeignKey(CNDeliveryGroup)

    def __unicode__(self):
        return str(self.cnDeliveryGroup)

class CNBuildLog (models.Model):
    '''
    This class models build log for cloud native.
    '''
    #id field = unsigned integer
    drop = models.CharField(max_length=50, blank = False, null = False)
    testPhase = models.CharField(max_length=50, blank=True, null = True)
    fromCnProductSetVersion = models.ForeignKey(CNProductSetVersion, blank=True, null=True, related_name = 'fromCnProductSetVersion')
    toCnProductSetVersion = models.ForeignKey(CNProductSetVersion, blank=True, null=True, related_name = 'toCnProductSetVersion')
    overall_status = models.ForeignKey(States, null=True, blank=True)
    deploymentName = models.CharField(max_length=100, blank=True, null = True)
    active = models.BooleanField(default=1)

    def __unicode__(self):
        return str(self.id) + " --> " + str(self.overall_status.state)

class CNConfidenceLevelRevision (models.Model):
    '''
    This class models confidence levels for cloud native build log.
    '''
    #id field = unsigned integer
    cnConfidenceLevel = models.ForeignKey(RequiredCNConfidenceLevel, blank=True, null=True)
    status = models.ForeignKey(States, blank=True, null=True)
    cnBuildLog = models.ForeignKey(CNBuildLog, null=True, blank=True)
    createdDate = models.DateTimeField(null=True, blank=True)
    updatedDate = models.DateTimeField(null=True, blank=True)
    reportLink = models.TextField()
    buildJobLink = models.TextField()
    percentage = models.CharField(max_length=10, blank=True, null = True)
    buildDate = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return str(self.cnConfidenceLevel.confidence_level_name) + " --> " + str(self.cnBuildLog.id)

class CNBuildLogComment (models.Model):
    '''
    This class models comments for the cloud native build log.
    '''
    # id field = unsigned integer
    cnBuildLog   = models.ForeignKey(CNBuildLog)
    cnJiraIssue = models.ForeignKey(CNJiraIssue,null=True, blank=True)
    comment         = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return str(self.cnBuildLog) + " --> " + str(self.comment)


class VersionSupportMapping(models.Model):
    '''
    This class holds media version information for compatiability with features
    '''
    artifactId = models.TextField(null=True, blank=True)
    version = models.TextField(null=True, blank=True)
    feature = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return str(self.feature) + " --> " + str(self.artifactId) + " --> " + str(self.version)

class JiraMigrationProject(models.Model):
    '''
    This class contains Jira projects migrated to eTeams Jira instance
    '''
    # id field = unsigned integer
    projectKeyName = models.CharField(max_length=15, unique=True)

    def __unicode__(self):
        return str(self.projectKeyName)