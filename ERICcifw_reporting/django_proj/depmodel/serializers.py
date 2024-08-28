from rest_framework import serializers

from .models import DependencyPluginArtifact

class VersionedPluginsSerializer(serializers.ModelSerializer):

    class Meta:
        model = DependencyPluginArtifact
        fields = ('name', 'property')
