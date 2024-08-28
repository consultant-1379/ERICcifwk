from django.db import models
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)

class GerritRepo (models.Model):
    """
    This is a model of foss_gerritrepo table,
        list of all ENM Gerrit repo URLs & their Owners
    """
    repo_name = models.CharField(max_length=200, unique=True)
    repo_revision = models.CharField(max_length=40, blank=True)
    owner = models.CharField(max_length=50, unique=False)
    owner_email = models.CharField(max_length=100, blank=True, null=True)
    scan = models.BooleanField(default=1)

    def __unicode__(self):
        return str(self.repo_name)


class ScanVersion (models.Model):
    """
    This is a model of foss_scanversion table,
        consists of Unique scaned version number, datetime & status of scan
    """
    start_time = models.DateTimeField(default=datetime.now())
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(default=0)
    audit_report_url = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return str(self.id)


class ScanMapping (models.Model):
    """
    This is a model of foss_scanmapping table,
        contains repo scanned info, audit & project IDs, etc.
    """
    scan_version = models.ForeignKey(ScanVersion)
    gerrit_repo = models.ForeignKey(GerritRepo)
    audit_id = models.CharField(max_length=30, blank=True, null=True)
    project_id = models.CharField(max_length=10, blank=True, null=True)
    report_url = models.CharField(max_length=200, blank=True, null=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, unique=False)
    reason = models.CharField(max_length=150, blank=True, null=True)

    def __unicode__(self):
        return str(self.scan_version) + " : " + str(self.gerrit_repo)
