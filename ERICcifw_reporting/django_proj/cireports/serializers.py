from rest_framework import serializers

from .models import ProductSetVersion, ISObuild, Component, PackageComponentMapping, ProductSetVersionContent
from datetime import datetime

class ProductSetVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSetVersion
        fields =('version',)

class ProductSetVersionContentSerializer(serializers.ModelSerializer):
    version = serializers.ReadOnlyField(source='mediaArtifactVersion.version')
    artifact = serializers.ReadOnlyField(source='mediaArtifactVersion.artifactId')
    group = serializers.ReadOnlyField(source='mediaArtifactVersion.groupId')
    isMasterArtifact = serializers.CharField()

    class Meta:
        model = ProductSetVersionContent
        fields =('artifact','group','version','isMasterArtifact')

class ISOBuildSerializer(serializers.ModelSerializer):
    mediaArtifactName = serializers.ReadOnlyField(source='mediaArtifact.name')
    dropName = serializers.ReadOnlyField(source='drop.name')
    overallStatus = serializers.ReadOnlyField(source='overall_status.state')
    sedText =  serializers.ReadOnlyField(source='sed_build.sed')
    latest = serializers.BooleanField(source='getLatestISO')
    buildDate = serializers.ReadOnlyField(source='build_date')
    currentStatus = serializers.ReadOnlyField(source='current_status')
    armRepo = serializers.ReadOnlyField(source='arm_repo')
    deployScriptVersion = serializers.ReadOnlyField(source='deploy_script_version')

    class Meta:
        model = ISObuild
        fields =('version','mediaArtifactName','dropName','groupId','buildDate','currentStatus','armRepo','deployScriptVersion','overallStatus','sedText','latest')

class ISOBuildVersionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ISObuild
        fields =['version']

class ComponentSerializer(serializers.ModelSerializer):
    productName = serializers.ReadOnlyField(source='product.name')
    labelName = serializers.ReadOnlyField(source='label.name')
    parentElement = serializers.ReadOnlyField(source='parent.element')

    class Meta:
        model = Component
        fields = ('id', 'productName', 'labelName', 'parentElement', 'element', 'dateCreated')

class PackageComponentSerializer(serializers.ModelSerializer):
    team = serializers.ReadOnlyField(source='component.element')
    packageName = serializers.ReadOnlyField(source='package.name')

    class Meta:
        model = PackageComponentMapping
        fields = ('team', 'packageName')
