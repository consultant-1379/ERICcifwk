from foss.models import *
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)

class GerritRepoAdmin(admin.ModelAdmin):
    """
    Admin View of the Gerrit Repo model
    """
    list_display = ('repo_name', 'repo_revision', 'owner', 'owner_email', 'scan')
    search_fields = ['repo_name', 'owner']
    list_filter = ['scan']

class ScanVersionAdmin(admin.ModelAdmin):
    """
    Admin View of the Scan Version model
    """
    list_display = ('id', 'start_time', 'end_time', 'status', 'audit_report_url')
    search_fields = ['id']
    list_filter = ['status']

class ScanMappingAdmin(admin.ModelAdmin):
    """
    Admin View of the Scan Mapping model
    """
    list_display = ('scan_version', 'gerrit_repo', 'audit_id', 'project_id', 'report_url', 'start_time', 'end_time', 'status', 'reason')
    search_fields = ['scan_version__id', 'gerrit_repo__repo_name']
    list_filter = ['status']

admin.site.register(GerritRepo, GerritRepoAdmin)
admin.site.register(ScanVersion, ScanVersionAdmin)
admin.site.register(ScanMapping, ScanMappingAdmin)
