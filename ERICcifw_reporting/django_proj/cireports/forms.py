from django import forms

from cireports.models import *

import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()

from django.forms.fields import DateField, ChoiceField, MultipleChoiceField
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple, TextInput
from django.forms.extras.widgets import SelectDateWidget

from fwk.forms import *
from datetime import datetime
now = datetime.now()
from cireports.utils import getPackagesBasedOnProduct
from django.contrib.auth.models import User

class DocumentForm(forms.ModelForm):
    '''
    '''
    cpi = forms.ChoiceField(
                   choices=((True, 'Yes'), (False, 'No')),
                   widget=forms.RadioSelect
                )
    class Meta:
        fields = ("document_type", "name", "author", "number", "revision", "link", "cpi", "comment", )
        model = Document

class DocumentTypeForm(forms.ModelForm):
    '''
    '''
    class Meta:
        fields = "__all__"
        model = DocumentType

class EditDocumentForm(forms.ModelForm):
    '''
    '''
    cpi = forms.ChoiceField(
                   choices=((True, 'Yes'), (False, 'No')),
                   widget=forms.RadioSelect
                )
    class Meta:
        fields = ("document_type", "name", "author", "number", "revision", "link", "cpi", "comment", )
        model = Document

class DeliveryForm(forms.Form):
    try:
        def __init__(self, product,*args, **kwargs):
            super(DeliveryForm, self).__init__(*args, **kwargs)
            self.fields['email'] = forms.EmailField()
            list = []
            list = list + [(orgObj.name, unicode(orgObj.name)) for orgObj in Drop.objects.filter(release__product__name=product, planned_release_date__gt=now) | Drop.objects.filter(release__product__name=product, actual_release_date__gt=now)]
            self.fields['drop'] = forms.CharField(widget=forms.Select(choices=list))
            # Commented out option for override
            # Override option is there so that ther same version could be delivered to the same drop again
            # This functionality is not allowed, users should be building a newer version to deliver and never rebuild the same version again
            #self.fields['override'] = forms.BooleanField(required=False)
    except cireports.models.Drop.DoesNotExist:
        logger.error("No Drops Available")

class TWMappingForm(forms.Form):
    '''
    This form is used to map Testware Artifact to a Package
    '''
    def __init__(self, testwareArtList, packageList,  *args, **kwargs):
        super(TWMappingForm, self).__init__(*args, **kwargs)
        if testwareArtList:
            self.fields['testware_artifact'] = forms.CharField(widget=forms.Select(choices=testwareArtList), label='Testware Artifact')
        else:
            self.fields['testware_artifact'] =  forms.CharField(widget = forms.TextInput(attrs={'placeholder': 'No Associated Testware', 'readonly':'readonly'}),label="Testware Artifact")
        if packageList:
            self.fields['package'] = forms.CharField(widget=forms.Select(choices=packageList), label='Package')
        else:
            self.fields['package'] =  forms.CharField(widget = forms.TextInput(attrs={'placeholder': 'Empty List', 'readonly':'readonly'}),label="Package")

class TWOptions(forms.Form):
    '''
    This form is used to select the criteria for Testware Artifact List Population
    '''
    def __init__(self, CHOICES, options, state, choicesP, optionsP, *args, **kwargs):
        super(TWOptions, self).__init__(*args, **kwargs)
        self.fields['all_artifact'] = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class':'selectAll'}), initial=state, label="Show All Testware Artifacts")
        self.fields['artifact_options'] = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(attrs={'class':'chkSelectItem'}), choices=CHOICES, initial=options, label="Show Testware Artifacts")
        self.fields['package_options'] = forms.ChoiceField(widget=forms.RadioSelect(attrs={'class':'selectPackages'}), choices=choicesP, initial=optionsP, label="Show Packages")


class DeliverNewPackageForm(forms.Form):
    '''
    This form is used to select a Product to associate with the Delivery
    '''
    list = []
    list = list + [(prodObj.name, unicode(prodObj.name)) for prodObj in Product.objects.all().exclude(name="None")]
    product = forms.CharField(widget=forms.Select(choices=list))

class DeliverNewMediaForm(forms.Form):
    '''
    This form is used to select a Product Set to associate with the Delivery
    '''
    def __init__(self, *args, **kwargs):
        super(DeliverNewMediaForm, self).__init__(*args, **kwargs)
        list = []
        list = list + [(prodSetObj.name, unicode(prodSetObj.name)) for prodSetObj in ProductSet.objects.all()]
        self.fields['productSet'] = forms.CharField(widget=forms.Select(choices=list))

class MediaDeliveryForm(forms.Form):
    try:
        def __init__(self, product,*args, **kwargs):
            super(MediaDeliveryForm, self).__init__(*args, **kwargs)
            self.fields['email'] = forms.EmailField()
            list = []
            list = list + [(orgObj.name, unicode(orgObj.name)) for orgObj in Drop.objects.exclude(status='closed').filter(release__product__name=product, mediaFreezeDate__gt=now)]
            self.fields['drop'] = forms.CharField(widget=forms.Select(choices=list))
    except cireports.models.Drop.DoesNotExist:
        logger.error("No Drops Available")

class PrimForm(forms.Form):
    try:
        def __init__(self, product, drop,*args, **kwargs):
            super(PrimForm, self).__init__(*args, **kwargs)
            self.fields['username'] = forms.CharField(required=False)
            self.fields['password'] = forms.CharField(max_length=32, widget=forms.PasswordInput)
            self.fields['baseproduct'] = forms.CharField(required=False)
            self.fields['baserevision'] = forms.CharField(required=False)
            self.fields['rstate'] = forms.CharField(required=False)
            self.fields['newrelease'] = forms.BooleanField(required=False)
            list = []
            list = list + [(orgObj.version, unicode(orgObj.version)) for orgObj in ISObuild.objects.filter(drop__name=drop, mediaArtifact__testware=False, drop__release__product__name=product, mediaArtifact__category__name="productware")]
            self.fields['media'] = forms.CharField(widget=forms.Select(choices=list))
    except cireports.models.ISObuild.DoesNotExist:
        logger.error("No ISO Available")

class PrimOptionForm(forms.Form):
    try:
        def __init__(self, product,*args, **kwargs):
            super(PrimOptionForm, self).__init__(*args, **kwargs)
            CHOICES=[('product_structure','Product Structure Creation'),
                    ('cxp_number','CXP Number(s) RState Registration')]
            self.fields['options'] = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect())
            list = []
            list = list + [(orgObj.name, unicode(orgObj.name)) for orgObj in Drop.objects.filter(release__product__name=product)]
            self.fields['drop'] = forms.CharField(widget=forms.Select(choices=list))
    except cireports.models.Drop.DoesNotExist:
        logger.error("No Drops Available")

class PrimCXPForm(forms.Form):
    try:
        def __init__(self, product, drop,*args, **kwargs):
            super(PrimCXPForm, self).__init__(*args, **kwargs)
            self.fields['username'] = forms.CharField(required=False)
            self.fields['password'] = forms.CharField(max_length=32, widget=forms.PasswordInput)
            list = []
            list = list + [(orgObj.version, unicode(orgObj.version)) for orgObj in ISObuild.objects.filter(drop__name=drop, mediaArtifact__testware=False, drop__release__product__name=product, mediaArtifact__category__name="productware")]
            self.fields['media'] = forms.CharField(widget=forms.Select(choices=list))
    except cireports.models.ISObuild.DoesNotExist:
        logger.error("No ISObuild Available")



class PackageMappingForm(forms.Form):
    '''
    '''
    def __init__(self, packageList, installOrderList,  *args, **kwargs):
        super(PackageMappingForm, self).__init__(*args, **kwargs)
        if packageList:
            self.fields['dependentPackage'] = forms.CharField(widget=forms.Select(choices=packageList), label='Dependent Package')
        else:
            self.fields['dependentPackage'] =  forms.CharField(widget = forms.TextInput(attrs={'placeholder': 'Empty List', 'readonly':'readonly'}),label="Dependent Package")
        installOrder = []
        installOrder = installOrder + [(number, unicode(number)) for number in installOrderList]
        self.fields['installOrder'] = forms.CharField(widget=forms.Select(choices=installOrder),label="Install Order")


class UploadFileForm(forms.Form):
    name = forms.CharField(max_length=90)
    file  = forms.FileField()

class IsoDeltaForm(forms.Form):
    try:
        def __init__(self, product,drop,bom,*args, **kwargs):
            super(IsoDeltaForm,self).__init__(*args, **kwargs)
            list = []
            if bom:
                isoObjs = ISObuild.objects.filter(drop__name=drop, mediaArtifact__testware=False, drop__release__product__name=product, mediaArtifact__category__name="productware").order_by('-build_date')
                for isoObj in isoObjs:
                    status_list = []
                    if isoObj.current_status:
                        currentStatusObj = ast.literal_eval(isoObj.current_status)
                        for cdbtype,status in currentStatusObj.items():
                            status_dict = {}
                            if status.count('#') == 4:
                                state,start,end,testReportNumber,veLog = status.split("#")
                            else:
                                state,start,end,testReportNumber = status.split("#")
                            cdbtypeObj = CDBTypes.objects.get(id=cdbtype)
                            cdb_type_sort_order = cdbtypeObj.sort_order

                            status_dict['cdb_type_sort_order'] = cdb_type_sort_order
                            status_dict['status'] = state
                            status_list.append(status_dict)
                    status_list = sorted(status_list, key=itemgetter('cdb_type_sort_order'), reverse=True)

                    if status_list and (status_list[-1]).get('status') == 'passed':
                        list.append((isoObj.version, unicode(isoObj.version)))
            else:
                list = [(orgObj.version, unicode(orgObj.version)) for orgObj in ISObuild.objects.filter(drop__name=drop, mediaArtifact__testware=False, drop__release__product__name=product, mediaArtifact__category__name="productware").order_by('-build_date')]
            self.fields['isoVersion'] = forms.CharField(widget=forms.Select(choices=list))
            self.fields['previousIsoVer'] = forms.CharField(widget=forms.Select(choices=list))
            if bom:
                self.fields['isoVersion'].label = "BOM Version"
                self.fields['previousIsoVer'].label = "Previous BOM Version"
            else:
                self.fields['isoVersion'].label = "ISO Version"
                self.fields['previousIsoVer'].label = "Previous ISO Version"
    except cireports.models.ISObuild.DoesNotExist:
        logger.error("No ISObuild Available")
