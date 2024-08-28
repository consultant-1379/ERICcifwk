from django import forms
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext

import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()
from fwk.models import *
import cireports

class FormHandle():
    '''
    An object to contain the elements required to process a form and it's success or failure.

    Adding, deleting and editing information in the CI Fwk database involves the use of
    specialised forms for each task. While it is difficult to make the forms or their
    processing generic, because each form needs different handling, it is possible to define
    a generic method for handling success or failure.

    '''
    form            = None
    request         = None
    title           = None
    subTitle        = None
    docLink         = None
    message         = ""
    successMessage  = "Success"
    failMessage     = "Form is invalid - please try again"
    redirectTarget  = None
    button          = "Next..."
    button2         = "False"
    button3         = "False"
    button4         = "False"
    button5         = "False"
    product         = "None"
    jenkins         = "None"

    def render(self, data):
        if self.request is not None:
            return render_to_response("dmt/regform.html", data, context_instance=RequestContext(self.request))
        else:
            formTitle = self.title
            if data['status'] is not None:
                formTitle = formTitle + ": " + data['status']
            return formTitle

    def success(self):
        if self.redirectTarget is not None:
            # Our successful form processing results in our being redirected
            return HttpResponseRedirect(self.redirectTarget)
        else:
            data = {'title': self.title, 'docLink': self.docLink, 'subTitle': self.subTitle, 'form': self.form, 'status': self.successMessage + " - add another", 'button': self.button, 'button2': self.button2, 'button3': self.button3, 'button4': self.button4, 'button5': self.button5, 'product': self.product, 'jenkinsObj': self.jenkins}
            return self.render(data)

    def failure(self):
        data = {'title': self.title, 'docLink': self.docLink, 'subTitle': self.subTitle, 'form': self.form, 'status': self.failMessage, 'button': self.button, 'button2': self.button2, 'button3': self.button3, 'button4': self.button4, 'button5': self.button5, 'message': self.message, 'product': self.product, 'jenkinsObj': self.jenkins}
        return self.render(data)

    def display(self):
        data = {'title': self.title, 'docLink': self.docLink, 'subTitle': self.subTitle, 'form': self.form, 'button': self.button, 'button2': self.button2, 'button3': self.button3, 'button4': self.button4, 'button5': self.button5, 'message': self.message, 'product': self.product, 'jenkinsObj': self.jenkins}
        return self.render(data)

class DevelopmentServerForm(forms.ModelForm):
    '''
    The DevelopmentServer class inherits the CIFWKDevelopmentServer model
    and using this meta data generated a ui form based on the model
    '''
    class Meta:
        fields = ("vm_hostname", "domain_name", "ipAddress", "owner", "description", )
        model = CIFWKDevelopmentServer

class UploadForm(forms.Form):
    try:
        package = cireports.models.Package.objects.get(name="ERICcifwkportal_CXP9030099")
        package_info = cireports.models.PackageRevision.objects.filter(package=package.id).order_by('-version')
        version  = forms.ModelChoiceField(queryset=package_info)
    except cireports.models.Package.DoesNotExist:
        logger.error("ERROR: Package ERICcifwkportal_CXP9030099 does not exist")

class PreRegisterArtifactForm(forms.Form):
    def __init__(self,*args, **kwargs):
        super(PreRegisterArtifactForm,self).__init__(*args, **kwargs)

        self.fields['packageName'] = forms.CharField(widget=forms.TextInput())
        self.fields['packageNumber'] = forms.CharField(widget=forms.TextInput())
        self.fields['mediaCategory'] = forms.CharField(widget=forms.Select(choices=(('service', 'Service'), ('testware', 'Testware'),('3pp', '3pp'))))
        self.fields['packageName'].label = "Package Name"
        self.fields['packageNumber'].label = "Package Number"
        self.fields['mediaCategory'].label = "Media Category"

