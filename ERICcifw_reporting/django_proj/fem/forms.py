from django import forms


import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()

from django.forms.fields import DateField, ChoiceField, MultipleChoiceField
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple, TextInput
from django.forms.extras.widgets import SelectDateWidget

from fem.models import *


class CreateFemJobForm(forms.Form):
    def __init__(self, jobs ,*args, **kwargs):
        super(CreateFemJobForm, self).__init__(*args, **kwargs)
        #jobs1=['(a,a)', '(TOR_Acceptance,TOR_Acceptance)', '(b,b)']
        self.fields['jobname'] = forms.CharField(required=False,label ="New Job Name")

        list = []
        list = list + [(orgObj.url, unicode(orgObj.url)) for orgObj in FemURLs.objects.all() ]
        self.fields['server'] = forms.CharField(widget=forms.Select(choices=list),label ="Jenkins Server")
        self.fields['username'] = forms.CharField(required=False, label="Jenkins Username")
        self.fields['password'] = forms.CharField(max_length=32, widget=forms.PasswordInput, label="Jenkins Password")
        self.fields['jobs'] = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(), choices=jobs, label="Jobs to Create")
        self.fields['repo'] = forms.CharField(required=False,label ="Git Repo")
        self.fields['buildbranch'] = forms.CharField(required=False,label ="Git Branch to Build")
        self.fields['pushbranch'] = forms.CharField(required=False,label ="Git Branch to Push to")
        self.fields['node'] = forms.CharField(required=False,label ="Run on Node")
        self.fields['enable'] = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(), choices=[('yes','Enable Jobs on creation')], label="Enable")




