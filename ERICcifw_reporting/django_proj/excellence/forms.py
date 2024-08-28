from django import forms

from excellence.models import *
from cireports.models import *

import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()

from django.forms.fields import DateField, ChoiceField, MultipleChoiceField
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple, TextInput
from django.forms.extras.widgets import SelectDateWidget
import re
from fwk.forms import *

class QuestionForm(forms.ModelForm):
    '''
    '''
    class Meta:
        fields = "__all__"
        model = Question


class CategoryForm(forms.ModelForm):
    '''
    '''
    class Meta:
        fields = "__all__"
        model = Category


class OrganisationForm(forms.ModelForm):
    '''
    ''' 
    #Ensure that the orgnaistion parent option does not show Team Names as a Parent option
    list = [("None", "None"),]
    list = list + [(orgObj, unicode(orgObj)) for orgObj in Organisation.objects.all() if orgObj.type != "Team"]
    parent_Area = forms.CharField(label="Organisation Parent",widget=forms.Select(choices=list))
    class Meta:
        fields = ("name", "description", "type", )
        widgets = {
                'description': forms.Textarea(attrs={'rows':5, 'cols':20}),
                  }
        model = Organisation

class QuestionnaireForm(forms.ModelForm):
    '''
    '''
    #Filter the Organistaion Drop dowm to just Teams and Just Team owned by the current logged on user
    def __init__(self, user,*args, **kwargs):
        super(QuestionnaireForm, self).__init__(*args, **kwargs)
        list = []
        list = list + [(orgObj.name, unicode(orgObj.name)) for orgObj in Organisation.objects.all() if (orgObj.type == "Team" and orgObj.owner == str(user))]
        self.fields['organisation'] = forms.CharField(widget=forms.Select(choices=list), label="Team")
    #Show the Latest questionnaire Version to the current logged on user
    version = Category.objects.values_list('version', flat=True).distinct()
    if version:
        version = max(version)
    else:
        version = ""
    version = forms.CharField(initial=version, widget=forms.TextInput(attrs={'readonly':'readonly'}))
    class Meta:
        fields = "__all__"
        model = Questionnaire

class DiscussionItemForm(forms.Form):
    '''
    Form used to discussion discussion items recorded during a questionnaire
    '''
    comment = forms.CharField(label="Discussion Item(s)", widget=forms.Textarea({'rows':3, 'cols':100}))
