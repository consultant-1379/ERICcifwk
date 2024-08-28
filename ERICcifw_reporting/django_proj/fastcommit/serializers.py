from rest_framework import serializers
from .models import DockerImageVersionContents


class DockerImageSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class DockerImageVersionSerializer(serializers.Serializer):
    image = DockerImageSerializer()
    version = serializers.CharField(max_length=20)


class PackageRevisionSerializer(serializers.Serializer):
    package = serializers.CharField(max_length=100)
    version = serializers.CharField(max_length=50)


class DockerImageVersionContentsPostSerializer(serializers.Serializer):
    image_version = DockerImageVersionSerializer()
    package_revision = PackageRevisionSerializer(many=True)


class DockerImageVersionContentsSerializer(serializers.ModelSerializer):
    image_version = DockerImageVersionSerializer()
    package_revision = PackageRevisionSerializer()

    class Meta:
        model = DockerImageVersionContents



