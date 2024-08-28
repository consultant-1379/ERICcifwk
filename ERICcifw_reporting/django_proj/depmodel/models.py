import logging
logger = logging.getLogger(__name__)
from django.db import models
import cireports.models

class DependencyType (models.Model):
    """
    Signifies a type of dependency. Possibilities are build, runtime or install time
    """
    # id field = integer
    name = models.CharField(max_length=30)
    desc = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.name

class Dependency (models.Model):
    """
    Signifies a dependency from one package revision to another package,
    including the max and min versions of that package
    """
    # id field = integer
    packagerev_from     = models.ForeignKey(cireports.models.PackageRevision, related_name="packagerev_from")
    package_to       = models.ForeignKey(cireports.models.Package, related_name="packagerev_to")
    packagerev_to_min   = models.ForeignKey(cireports.models.PackageRevision, null=True, blank=True, related_name="package_to_min")
    packagerev_to_max   = models.ForeignKey(cireports.models.PackageRevision, null=True, blank=True, related_name="package_to_max")
    type             = models.ForeignKey(DependencyType)

    def __unicode__(self):
        return str(self.packagerev_from) + " ------ " + str(self.type) + " ----> " + str(self.package_to)

class JavaPackage(models.Model):
    # id field = integer
    package_name = models.CharField(max_length=255)
    provided_by = models.ForeignKey(cireports.models.Package, null=True, blank=True)
    #is_3pp = models.Boolean()

class StaticDependency (models.Model):
    """
    Signifies a dependency from Java code in a revision of a package to a Java package.
    """
    # id field = integer
    package_revision = models.ForeignKey(cireports.models.PackageRevision)
    java_package     = models.ForeignKey(JavaPackage)

class Artifact (models.Model):
    """
    """
    # id field = integer
    name = models.CharField(max_length=100, unique=True)
    package = models.ForeignKey('cireports.Package', blank=True, null = True)

    def __unicode__(self):
        return str(self.name)
class ArtifactVersion (models.Model):
    """
    """
    # id field = integer
    artifact = models.ForeignKey(Artifact)
    groupname = models.CharField(max_length=100)
    version = models.CharField(max_length=100)
    m2type = models.CharField(max_length=30,null=True, blank=True)
    bomcreatedartifact = models.BooleanField(default=0)
    bomversion = models.CharField(max_length=30, null=True, blank=True)
    reponame = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('artifact', 'groupname','version','m2type', 'bomcreatedartifact', 'bomversion','reponame',)

    def __unicode__(self):
        return str(self.artifact)

class ArtVersToPackageToISOBuildMap (models.Model):
    '''
    '''
    # id field = unsigned INT(10)
    artifact_version = models.ForeignKey(ArtifactVersion)
    package= models.ForeignKey(cireports.models.Package, null=True, blank=True)
    isobuild_version = models.ForeignKey(cireports.models.ISObuild, null=True, blank=True)

    class Meta:
        unique_together = ('artifact_version', 'package', 'isobuild_version',)

    def __unicode__(self):
        return "Artifact Version: "  + str(self.artifact_version) + " Package  " + str(self.package) + "ISO Version: " + str(self.isobuild_version)

class Mapping (models.Model):
    """
    """
    # id field = unsigned integer
    artifact_main_version = models.ForeignKey(ArtifactVersion,related_name='+')
    artifact_dep_version = models.ForeignKey(ArtifactVersion)
    scope = models.CharField(max_length=60)
    build = models.BooleanField(default=0)

    class Meta:
        unique_together = ('artifact_main_version', 'artifact_dep_version','scope',)

    def __unicode__(self):
        return str(self.artifact_main_version) + " ----> " + str(self.artifact_dep_version)

class PackageDependencies (models.Model):
    """
    """
    # id field = unsigned integer
    package             = models.ForeignKey(cireports.models.PackageRevision, unique=True)
    deppackage          = models.CharField(max_length=1000, null=True, blank=True)
    all                 = models.TextField(max_length=50000, null=True, blank=True)
    jar_dependencies    = models.CharField(max_length=5000, null=True, blank=True)
    third_party_dependencies= models.CharField(max_length=5000, null=True, blank=True)

    def __unicode__(self):
        return str(self.package)

class AnomalyArtifact (models.Model):
    """
    The AnomalyArtifact class stores build artifact anomalies
    """
    # id field = integer
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return str(self.name)

class AnomalyArtifactVersion (models.Model):
    """
    The AnomalyArtifactVersion class stores build artifact anomalies versions
    """
    # id field = integer
    anomalyartifact = models.ForeignKey(AnomalyArtifact)
    groupname = models.CharField(max_length=100)
    version = models.CharField(max_length=100)
    m2type = models.CharField(max_length=30)

    class Meta:
        unique_together = ('anomalyartifact','groupname','version','m2type',)

    def __unicode__(self):
        return str(self.anomalyartifact)

class AnomalyArtifactVersionToPackageRev (models.Model):
    '''
    The AnomalyArtifactVersionToPackageRev class maps artifact anomalies versions to package revisons
    '''

    # id field = integer
    anomalyartifact_version = models.ForeignKey(AnomalyArtifactVersion)
    package_revision = models.CharField(max_length=255)

    class Meta:
        unique_together = ('anomalyartifact_version', 'package_revision',)

    def __unicode__(self):
        return "Anomaly Artifact Version: "  + str(self.anomalyartifact_version) + " Package Revison: " + str(self.package_revision)

class DependencyPluginArtifact (models.Model):
    '''
    The DependencyPluginArtifact class stores a list of dependencies that are also plugins
    '''
    name = models.CharField(max_length=200, unique=True)
    property = models.CharField(max_length=255)

    def __unicode__(self):
        return str(self.name)
