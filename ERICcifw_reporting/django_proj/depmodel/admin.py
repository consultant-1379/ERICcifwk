from .models import Artifact, ArtifactVersion, ArtVersToPackageToISOBuildMap, AnomalyArtifact, AnomalyArtifactVersion, AnomalyArtifactVersionToPackageRev, DependencyPluginArtifact 
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)

admin.site.register(Artifact)
admin.site.register(ArtifactVersion)
admin.site.register(ArtVersToPackageToISOBuildMap)
admin.site.register(AnomalyArtifact)
admin.site.register(AnomalyArtifactVersion)
admin.site.register(AnomalyArtifactVersionToPackageRev)
admin.site.register(DependencyPluginArtifact)
