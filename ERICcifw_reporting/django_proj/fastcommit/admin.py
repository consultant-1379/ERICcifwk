from django.contrib import admin
from .models import *


class DockerImageVersionContentsAdmin(admin.ModelAdmin):
    list_display = ('image_version', 'package_revision')
    readonly_fields = ('package_revision',)


admin.site.register(DockerImage)
admin.site.register(DockerImageVersion)
admin.site.register(DockerImageVersionContents)
