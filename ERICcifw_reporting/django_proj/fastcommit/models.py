from django.db import models
from cireports.models import PackageRevision


class DockerImage(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return self.name


class DockerImageVersion(models.Model):
    image = models.ForeignKey(DockerImage, related_name='image')
    version = models.CharField(max_length=25)

    class Meta:
        unique_together = ('image', 'version')

    def __unicode__(self):
        return "%s-%s" % (self.image.name, self.version)


class DockerImageVersionContents(models.Model):
    image_version = models.ForeignKey(DockerImageVersion, related_name='image_version')
    package_revision = models.ForeignKey(PackageRevision, related_name='package_revision')

    class Meta:
        unique_together = ('image_version', 'package_revision')

    def __unicode__(self):
        return "%s->%s" % (self.image_version, self.package_revision)
