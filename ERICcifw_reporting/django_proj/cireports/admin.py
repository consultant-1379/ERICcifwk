from cireports.models import *
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)

class ReleaseAdmin(admin.ModelAdmin):
    '''
    Admin View of the Release Model
    '''
    list_display = ('name', 'track', 'product')
    search_fields = ['name', 'product__name']


class PackageAdmin(admin.ModelAdmin):
    '''
    Admin View of the Package Model
    '''
    list_display = ('name', 'package_number', 'testware', 'obsolete_after', 'signum')
    list_filter = ['testware', 'includedInPriorityTestSuite']
    search_fields = ['name', 'package_number']

class ProductPackageMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductPackageMapping Model
    '''
    list_display = ('package', 'product')
    search_fields = ['product__name', 'package__name', 'package__package_number']

class DropAdmin(admin.ModelAdmin):
    '''
    Admin View of the Drop Model
    '''
    list_display = ('name', 'release')
    search_fields = ['name', 'release__name', 'release__product__name']

class DropPackageMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the Drop Package Mapping Model
    '''
    list_display = ('drop', 'package_revision', 'released', 'obsolete', 'date_created', 'deliverer_name', 'kgb_test', 'kgb_snapshot_report')
    list_filter = ['released', 'obsolete']
    search_fields = ['package_revision__package__name', 'package_revision__version', 'drop__name']

class DropMediaArtifactMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the Drop Package Mapping Model
    '''
    list_display = ('drop', 'mediaArtifactVersion', 'released', 'obsolete', 'frozen','dateCreated')
    list_filter = ['released', 'obsolete', 'frozen']
    search_fields = ['mediaArtifactVersion__mediaArtifact__name', 'mediaArtifactVersion__version', 'drop__name']

class PackageRevisionAdmin(admin.ModelAdmin):
    '''
    Admin View of the Package Revision Model
    '''
    list_display = ('package', 'version', 'groupId', 'm2type', 'date_created', 'platform', 'category', 'infra', 'autodrop', 'autodeliver', 'kgb_test', 'kgb_snapshot_report')
    list_filter = ['category', 'm2type', 'package__testware', 'platform', 'kgb_test', 'infra', 'kgb_snapshot_report']
    search_fields = ['artifactId', 'groupId', 'version']

class MediaArtifactCategoryAdmin(admin.ModelAdmin):
    '''
    Admin View of the Media Artifact Category Model
    '''
    search_fields = ['name']

class MediaArtifactDeployTypeAdmin(admin.ModelAdmin):
    '''
    Admin View of the Media Artifact Deploy Type Model
    '''
    search_fields = ['type']


class MediaArtifactAdmin(admin.ModelAdmin):
    '''
    Admin View of the Media Artifact Model
    '''
    list_display = ('name', 'number', 'mediaType', 'testware', 'obsoleteAfter', 'description', 'category', 'deployType')
    list_filter = ['testware', 'category', 'deployType']
    search_fields = ['name', 'number', 'category', 'deployType']


class ISObuildAdmin(admin.ModelAdmin):
    '''
    Admin View of the ISObuild Model
    '''
    list_display = ('mediaArtifact', 'version', 'drop')
    list_filter = ['mediaArtifact__testware']
    search_fields = ['mediaArtifact__name', 'version', 'drop__name', 'drop__release__name', 'drop__release__product__name']

class ISObuildMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ISObuildMapping Model
    '''
    list_display = ('iso', 'package_revision', 'drop', 'kgb_test', 'kgb_snapshot_report')
    search_fields = ['iso__mediaArtifact__name', 'iso__version', 'iso__drop__name', 'iso__drop__release__name', 'iso__drop__release__product__name']

class ProductTestwareMediaMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductTestwareMediaMapping Model
    '''
    list_display = ('productIsoVersion', 'testwareIsoVersion')
    search_fields = ['productIsoVersion__mediaArtifact__name', 'productIsoVersion__version', 'productIsoVersion__drop__name', 'productIsoVersion__drop__release__name', 'productIsoVersion__drop__release__product__name', 'testwareIsoVersion__mediaArtifact__name', 'testwareIsoVersion__version']

class ProductSetReleaseAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductSetRelease Model
    '''
    list_display = ('name', 'number', 'release', 'productSet', 'masterArtifact', 'updateMasterStatus')
    list_filter = ['updateMasterStatus']
    search_fields = ['name', 'number', 'masterArtifact__name', 'release__name', 'productSet__name']

class ProductSetVersionAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductSetVersion Model
    '''
    list_display = ('version', 'drop', 'productSetRelease')
    search_fields = ['version', 'drop__name', 'drop__release__product__name', 'productSetRelease__name', 'productSetRelease__number', 'productSetRelease__productSet__name']

class ProductSetVersionContentAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductSetVersionContent Model
    '''
    list_display = ('productSetVersion', 'mediaArtifactVersion')
    search_fields = ['productSetVersion__version', 'mediaArtifactVersion__mediaArtifact__name', 'mediaArtifactVersion__version', 'mediaArtifactVersion__drop__name', 'mediaArtifactVersion__drop__release__product__name']

class ImageContentAdmin(admin.ModelAdmin):
    '''
    Admin View of the ImageContent Model
    '''
    list_display = ('packageRev', 'parent')
    search_fields = ['packageRev__package__name', 'packageRev__version', 'parent__packageRev__package__name']

class ComponentAdmin(admin.ModelAdmin):
    '''
    Admin View of the Component Model
    '''
    list_display = ('element', 'parent', 'label', 'dateCreated','deprecated')
    list_filter = ['label']
    search_fields = ['element', 'parent__element', 'product__name']

class PackageComponentMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the PackageComponentMapping Model
    '''
    list_display = ('component', 'package')
    search_fields = ['package__name', 'component__element', 'component__parent__element', 'component__product__name']

class DeliveryGroupAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeliveryGroup Model
    '''
    list_display = ('id', 'drop', 'component', 'creator', 'delivered', 'obsoleted', 'deleted', 'modifiedDate', 'autoCreated', 'consolidatedGroup', 'newArtifact', 'ccbApproved', 'bugOrTR')
    list_filter = ['delivered', 'obsoleted', 'deleted', 'autoCreated', 'consolidatedGroup', 'newArtifact', 'ccbApproved', 'bugOrTR']
    search_fields = ['id', 'drop__name', 'component__element', 'creator']

class DeliverytoPackageRevMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeliverytoPackageRevMapping Model
    '''
    list_display = ('deliveryGroup', 'packageRevision', 'team', 'kgb_test', 'kgb_snapshot_report', 'services')
    search_fields = ['deliveryGroup__id', 'packageRevision__package__name', 'deliveryGroup__drop__name']

class DeliveryGroupCommentAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeliveryGroupComment Model
    '''
    list_display = ('deliveryGroup', 'comment', 'date')
    search_fields = ['deliveryGroup__id', 'deliveryGroup__drop__name']

class JiraIssueAdmin(admin.ModelAdmin):
    '''
    Admin View of the JiraIssueAdmin Model
    '''
    list_display = ('jiraNumber', 'issueType')
    list_filter = ['issueType']
    search_fields = ['jiraNumber', 'issueType']

class JiraProjectExceptionAdmin(admin.ModelAdmin):
    '''
    Admin View of the JiraProjectException
    '''
    list_display = ('projectName',)
    search_fields = ['projectName']

class JiraDeliveryGroupMapAdmin(admin.ModelAdmin):
    '''
    Admin View of the JiraDeliveryGroupMap Model
    '''
    list_display = ('deliveryGroup', 'jiraIssue')
    list_filter = ['jiraIssue__issueType']
    search_fields = ['deliveryGroup__id', 'deliveryGroup__drop__name', 'jiraIssue__jiraNumber', 'jiraIssue__issueType']

class IsotoDeliveryGroupMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the JiraDeliveryGroupMap Model
    '''
    list_display = ('deliveryGroup', 'iso')
    list_filter = ['iso__mediaArtifact__testware', 'deliveryGroup_status']
    search_fields = ['deliveryGroup__id', 'deliveryGroup__drop__name', 'iso__mediaArtifact__name', 'iso__version']

class DeliveryGroupSubscriptionAdmin(admin.ModelAdmin):
    '''
    Admin View of the DeliveryGroupSubscription Model
    '''
    list_display = ('user', 'deliveryGroup')
    search_fields = ['signum', 'deliveryGroup__id']

class TestwareArtifactAdmin(admin.ModelAdmin):
    '''
    Admin View of the TestwareArtifact Model
    '''
    list_display = ('name', 'artifact_number', 'signum', 'includedInPriorityTestSuite')
    list_filter = ['includedInPriorityTestSuite']
    search_fields = ['name', 'artifact_number', 'signum']

class TestwareTypeMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the TestwareTypeMapping Model
    '''
    list_display = ('testware_artifact', 'testware_type')
    list_filter = ['testware_type__type']
    search_fields = ['testware_artifact__name']

class TestwareRevisionAdmin(admin.ModelAdmin):
    '''
    Admin View of the TestwareRevision Model
    '''
    list_display = ('testware_artifact', 'version', 'groupId', 'date_created', 'obsolete', 'validTestPom', 'kgb_status', 'cdb_status')
    search_fields = ['artifactId', 'version', 'groupId', 'execution_artifactId']

class TestwarePackageMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the TestwarePackageMappingAdmin Model
    '''
    list_display = ('testware_artifact', 'package')
    search_fields = ['testware_artifact__name', 'testware_artifact__artifact_number', 'package__name', 'package__package_number']

class DocumentAdmin(admin.ModelAdmin):
    '''
    Admin View of the Document Model
    '''
    list_display = ('name', 'document_type', 'number', 'revision', 'drop', 'author', 'deliveryDate', 'owner')
    list_filter = ['document_type__type']
    search_fields = ['name', 'document_type__type', 'number', 'revision', 'drop__name', 'author', 'owner']

class ClueAdmin(admin.ModelAdmin):
    '''
    Admin View of the Clue Model
    '''
    list_display = ('package', 'codeReview', 'unit', 'acceptance', 'release')
    list_filter = ['codeReview', 'unit', 'acceptance', 'release']
    search_fields = ['package__name', 'package__package_number']


class ClueTrendAdmin(admin.ModelAdmin):
    '''
    Admin View of the ClueTrend Model
    '''
    list_display = ('package', 'codeReview', 'unit', 'acceptance', 'release', 'lastUpdate')
    list_filter = ['codeReview', 'unit', 'acceptance', 'release']
    search_fields = ['package__name', 'package__package_number']

class NonProductEmailAdmin(admin.ModelAdmin):
    '''
    Admin View of the NonProductEmail Model
    '''
    list_display = ('email', 'area')
    search_fields = ['email', 'area']

class ProductEmailAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductEmail Model
    '''
    list_display = ('email', 'product')
    search_fields = ['email', 'product__name']

class ProductDropToCDBTypeAdmin(admin.ModelAdmin):
    '''
    Admin View of the  ProductToCDBType  Model
    '''
    list_display = ('product', 'drop', 'type', 'enabled','overallStatusFailure')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        requiredProductFields=('id')
        if db_field.name == "product":
            kwargs["queryset"] = Product.objects.all().only(requiredProductFields).order_by('id').reverse()
        if db_field.name == "drop":
            kwargs["queryset"] = Drop.objects.all().only(requiredProductFields).order_by('id').reverse()
        if db_field.name == "type":
            kwargs["queryset"] = CDBTypes.objects.all().only(requiredProductFields).order_by('id').reverse()
        return super(ProductDropToCDBTypeAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class ProductSetVerToCDBTypeMapAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductSetVerToCDBTypeMap Model
    '''
    list_display = ('productSetVersion', 'productCDBType', 'runningStatus', 'override')
    search_fields = ['productSetVersion__version', 'productCDBType__type__name']

class ReasonsForNoKGBStatusAdmin(admin.ModelAdmin):
    '''
    Admin View of the ReasonsForNoKGBStatus Model
    '''
    list_display = ('reason', 'active')

class AutoDeliverTeamAdmin(admin.ModelAdmin):
    '''
    Admin View of the DirectDeliveryTeam Model
    '''
    list_display = ('team',)
    search_fields = ['team__element']

class DropMediaDeployMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the DropMediaDeployMapping Model
    '''
    list_display = ('dropMediaArtifactMap', 'product')
    search_fields = ['product__name']

class ProductSetVersionDeployMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the ProductSetVersionDeployMapping Model
    '''
    list_display = ('mainMediaArtifactVersion', 'mediaArtifactVersion','productSetVersion')
    search_fields = ['productSetVersion__version']

class CNHelmChartAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Helm Charts to Product mapping
    '''
    list_display = ('helm_chart_name', 'helm_chart_product_number')
    search_fields = ['helm_chart_name', 'helm_chart_product_number']

class CNImageAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Image to Helm Charts
    '''
    list_display = ('image_name', 'image_product_number', 'repo_name')
    search_fields = ['image_name', 'image_product_number']

class CNImageRevisionAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Image Revision, corresponding built versions and other info
    '''
    list_display = ('image', 'parent', 'version', 'created', 'size', 'gerrit_repo_sha')
    search_fields = ['image__image_name', 'version']

class CNImageContentAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Image Content and corresponding built versions
    '''
    list_display = ('image_revision', 'package_revision')
    search_fields = ['image_revision__image__image_name', 'image_revision__version']

class CNHelmChartRevisionAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Helm Chart Revision, corresponding built versions and other info
    '''
    list_display = ('helm_chart', 'version', 'created', 'size', 'gerrit_repo_sha')
    search_fields = ['helm_chart__helm_chart_name', 'version']

class CNImageHelmChartMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native mapping between Image and Helm Chart
    '''
    list_display = ('image_revision', 'helm_chart_revision')
    search_fields = ['helm_chart_revision__helm_chart__helm_chart_name', 'helm_chart_revision__version']

class CNHelmChartProductMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native mappiong between Helm Charts and Integration Charts
    '''
    list_display = ('product_revision', 'helm_chart_revision')
    search_fields = ['product_revision__product_set_version__product_set_version', 'product_revision__product__product_name', 'product_revision__version']

class CNProductAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Product
    '''
    list_display = ('product_set', 'product_name', 'product_type', 'repo_name', 'published_link')
    search_fields = ['product_name', 'product_type__product_type_name', 'repo_name']

class CNProductTypeAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Product Type
    '''
    list_display = ('product_type_name',)
    search_fields = ['product_type_name']

class CNProductRevisionAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Product Revision
    '''
    list_display = ('product', 'product_set_version', 'version', 'created', 'gerrit_repo_sha', 'dev_link', 'values_file_version', 'values_file_name', 'verified')
    search_fields = ['product__product_name', 'product__product_type__product_type_name', 'product_set_version__product_set_version', 'product_set_version__drop_version']

class CNProductSetVersionAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Product set versions
    '''
    list_display = ('product_set_version', 'status', 'overall_status', 'drop_version', 'active')
    search_fields = ['product_set_version', 'drop_version', 'overall_status__state']

class CNProductSetAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native Product Set table
    '''
    list_display = ('product_set_name',)

class CNConfidenceLevelTypeAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native confidence level type
    '''
    list_display = ('confidenceLevelTypeName',)
    search_fields = ['confidenceLevelTypeName']

class RequiredCNConfidenceLevelAdmin(admin.ModelAdmin):
    '''
    Admin View of the Cloud Native confidence level
    '''
    list_display = ('confidence_level_name', 'confidenceLevelType', 'required', 'include_baseline','requireBuildLogId')
    search_fields = ['confidence_level_name']

class RequiredRAMappingAdmin(admin.ModelAdmin):
    '''
    Admin View of the Required RA Mapping table
    '''
    list_display = ('team_inventory_ra_name','component')
    search_fields = ['team_inventory_ra_name', 'component__element']

class CNDropAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native drop table
    '''
    list_display = ('name', 'cnProductSet')
    search_fields = ['name', 'cnProductSet__product_set_name']

class CNDeliveryGroupAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native delivery group table
    '''
    list_display = ('id', 'cnDrop', 'cnProductSetVersion', 'cnProductSetVersionSet', 'component', 'creator', 'teamEmail', 'queued', 'delivered', 'obsoleted', 'deleted', 'modifiedDate', 'bugOrTR', 'missingDependencies')
    search_fields = ['id', 'cnDrop__name', 'component__element', 'creator']

class CNDeliveryGroupCommentAdmin(admin.ModelAdmin):
    '''
    Admin View of the cn DeliveryGroupComment Model
    '''
    list_display = ('cnDeliveryGroup', 'comment', 'date')
    search_fields = ['cnDeliveryGroup__id', 'deliveryGroup__cnDrop__name']

class CNGerritAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native gerrit table
    '''
    lis_display = ('gerrit_link', )

class CNPipelineAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native pipeline table
    '''
    lis_display = ('pipeline_link', )

class CNDGToCNImageToCNGerritMapAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native cnDG to CNImage to cnGerrit map table
    '''
    lis_display = ('cnDeliveryGroup', 'cnImage', 'cnGerrit', 'states', 'revert_change_id')
    search_fields = ['cnDeliveryGroup__id', 'cnImage__image_name', 'revert_change_id']

class CNDGToCNProductToCNGerritMapAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native cn delivery group to cnProduct to cnGerrit map table
    '''
    lis_display = ('cnDeliveryGroup', 'cnProduct', 'cnGerrit', 'states', 'revert_change_id')
    search_fields = ['cnDeliveryGroup__id', 'cnProduct__product_name', 'revert_change_id']

class CNDGToCNPipelineToCNGerritMapAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native cn delivery group to cn pipeline map table
    '''
    lis_display = ('cnDeliveryGroup', 'cnPipeline', 'cnGerrit', 'states', 'revert_change_id')
    search_fields = ['cnDeliveryGroup__id', 'cnPipeline__pipeline_link', 'revert_change_id']

class CNDGToDGMapAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native cn delivery group to delivery group map table
    '''
    lis_display = ('cnDeliveryGroup', 'deliveryGroup')
    search_fields = ['cnDeliveryGroup__id', 'deliveryGroup__id']

class CNDGToCNJiraIssueMapAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native cn delivery group to cn jira issue map table
    '''
    lis_display = ('cnDeliveryGroup', 'cnJiraIssue')
    search_fields = ['cnDeliveryGroup__id', 'cnJiraIssue__jiraNumber']

class CNJiraIssueAdmin(admin.ModelAdmin):
    '''
    Admin View of the CNJiraIssueAdmin Model
    '''
    list_display = ('jiraNumber', 'issueType')
    list_filter = ['issueType']
    search_fields = ['jiraNumber', 'issueType']

class CNDeliveryGroupSubscriptionAdmin(admin.ModelAdmin):
    '''
    Admin View of the CNDeliveryGroupSubscription Model
    '''
    list_display = ('user', 'cnDeliveryGroup')
    search_fields = ['signum', 'cnDeliveryGroup__id']

class CNBuildLogAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native build log
    '''
    list_display = ('id', 'drop', 'testPhase', 'fromCnProductSetVersion', 'toCnProductSetVersion', 'overall_status', 'deploymentName', 'active')
    search_fields = ['id', 'drop', 'testPhase', 'toCnProductSetVersion__product_set_version', 'deploymentName']

class CNConfidenceLevelRevisionAdmin(admin.ModelAdmin):
    '''
    Admin View of conidence level revision to cloud native build log
    '''
    list_display = ('id', 'cnConfidenceLevel', 'status', 'cnBuildLog', 'createdDate', 'updatedDate', 'reportLink', 'buildJobLink', 'percentage', 'buildDate')
    search_fields = ['cnConfidenceLevel__confidence_level_name', 'cnBuildLog__id', 'buildDate']

class CNBuildLogCommentAdmin(admin.ModelAdmin):
    '''
    Admin View of cloud native build log comments
    '''
    list_display = ('id', 'cnBuildLog', 'cnJiraIssue', 'comment')
    search_fields = ['cnBuildLog__id', 'cnJiraIssue__jiraNumber']

class JiraMigrationProjectAdmin(admin.ModelAdmin):
    '''
    Admin View of jira migration projects
    '''
    list_display = ('projectKeyName',)
    search_fields = ['projectKeyName']

admin.site.register(Package, PackageAdmin)
admin.site.register(SolutionSet)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(Drop, DropAdmin)
admin.site.register(PackageRevision, PackageRevisionAdmin)
admin.site.register(DropPackageMapping, DropPackageMappingAdmin)
admin.site.register(ISObuild, ISObuildAdmin)
admin.site.register(ISObuildMapping, ISObuildMappingAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentType)
admin.site.register(Product)
admin.site.register(TestwareArtifact, TestwareArtifactAdmin)
admin.site.register(TestwareRevision, TestwareRevisionAdmin)
admin.site.register(TestwarePackageMapping, TestwarePackageMappingAdmin)
admin.site.register(FEMLink)
admin.site.register(Clue, ClueAdmin)
admin.site.register(ClueTrend, ClueTrendAdmin)
admin.site.register(CDB)
admin.site.register(CDBTypes)
admin.site.register(CDBHistory)
admin.site.register(MediaArtifactType)
admin.site.register(MediaArtifactCategory, MediaArtifactCategoryAdmin)
admin.site.register(MediaArtifactDeployType, MediaArtifactDeployTypeAdmin)
admin.site.register(MediaArtifact, MediaArtifactAdmin)
admin.site.register(ProductSet)
admin.site.register(ProductSetRelease, ProductSetReleaseAdmin)
admin.site.register(ProductSetVersion, ProductSetVersionAdmin)
admin.site.register(ProductSetVersionContent, ProductSetVersionContentAdmin)
admin.site.register(DropMediaArtifactMapping, DropMediaArtifactMappingAdmin)
admin.site.register(NonProductEmail, NonProductEmailAdmin)
admin.site.register(ProductEmail, ProductEmailAdmin)
admin.site.register(Categories)
admin.site.register(ImageContent, ImageContentAdmin)
admin.site.register(Component, ComponentAdmin)
admin.site.register(PackageComponentMapping, PackageComponentMappingAdmin)
admin.site.register(Label)
admin.site.register(ProductPackageMapping, ProductPackageMappingAdmin)
admin.site.register(ProductTestwareMediaMapping, ProductTestwareMediaMappingAdmin)
admin.site.register(DeliveryGroup, DeliveryGroupAdmin)
admin.site.register(IsotoDeliveryGroupMapping, IsotoDeliveryGroupMappingAdmin)
admin.site.register(DeliverytoPackageRevMapping, DeliverytoPackageRevMappingAdmin)
admin.site.register(DeliveryGroupComment, DeliveryGroupCommentAdmin)
admin.site.register(JiraIssue, JiraIssueAdmin)
admin.site.register(JiraTypeExclusion)
admin.site.register(JiraProjectException, JiraProjectExceptionAdmin)
admin.site.register(JiraDeliveryGroupMap, JiraDeliveryGroupMapAdmin)
admin.site.register(ProductDropToCDBTypeMap,ProductDropToCDBTypeAdmin)
admin.site.register(ProductSetVerToCDBTypeMap, ProductSetVerToCDBTypeMapAdmin)
admin.site.register(DeliveryGroupSubscription, DeliveryGroupSubscriptionAdmin)
admin.site.register(ReasonsForNoKGBStatus,ReasonsForNoKGBStatusAdmin)
admin.site.register(AutoDeliverTeam,AutoDeliverTeamAdmin)
admin.site.register(DropLimitedReason)
admin.site.register(TestwareType)
admin.site.register(TestwareTypeMapping, TestwareTypeMappingAdmin)
admin.site.register(DropMediaDeployMapping, DropMediaDeployMappingAdmin)
admin.site.register(ProductSetVersionDeployMapping, ProductSetVersionDeployMappingAdmin)
admin.site.register(CNHelmChart, CNHelmChartAdmin)
admin.site.register(CNImage, CNImageAdmin)
admin.site.register(CNImageRevision, CNImageRevisionAdmin)
admin.site.register(CNImageContent, CNImageContentAdmin)
admin.site.register(CNHelmChartRevision, CNHelmChartRevisionAdmin)
admin.site.register(CNImageHelmChartMapping, CNImageHelmChartMappingAdmin)
admin.site.register(CNHelmChartProductMapping, CNHelmChartProductMappingAdmin)
admin.site.register(CNProductType, CNProductTypeAdmin)
admin.site.register(CNProduct, CNProductAdmin)
admin.site.register(CNProductRevision, CNProductRevisionAdmin)
admin.site.register(CNProductSet, CNProductSetAdmin)
admin.site.register(CNProductSetVersion, CNProductSetVersionAdmin)
admin.site.register(CNConfidenceLevelType, CNConfidenceLevelTypeAdmin)
admin.site.register(RequiredCNConfidenceLevel, RequiredCNConfidenceLevelAdmin)
admin.site.register(RequiredRAMapping, RequiredRAMappingAdmin)
admin.site.register(CNDrop, CNDropAdmin)
admin.site.register(CNDeliveryGroup, CNDeliveryGroupAdmin)
admin.site.register(CNDeliveryGroupComment, CNDeliveryGroupCommentAdmin)
admin.site.register(CNPipeline, CNPipelineAdmin)
admin.site.register(CNGerrit, CNGerritAdmin)
admin.site.register(CNDGToCNImageToCNGerritMap, CNDGToCNImageToCNGerritMapAdmin)
admin.site.register(CNDGToCNProductToCNGerritMap, CNDGToCNProductToCNGerritMapAdmin)
admin.site.register(CNDGToCNPipelineToCNGerritMap, CNDGToCNPipelineToCNGerritMapAdmin)
admin.site.register(CNDGToDGMap, CNDGToDGMapAdmin)
admin.site.register(CNDGToCNJiraIssueMap, CNDGToCNJiraIssueMapAdmin)
admin.site.register(CNJiraIssue, CNJiraIssueAdmin)
admin.site.register(CNDeliveryGroupSubscription, CNDeliveryGroupSubscriptionAdmin)
admin.site.register(CNBuildLog, CNBuildLogAdmin)
admin.site.register(CNConfidenceLevelRevision, CNConfidenceLevelRevisionAdmin)
admin.site.register(CNBuildLogComment, CNBuildLogCommentAdmin)
admin.site.register(VersionSupportMapping)
admin.site.register(JiraMigrationProject, JiraMigrationProjectAdmin)
