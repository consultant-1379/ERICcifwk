from django import forms

from vis.models import *

import logging
logger = logging.getLogger(__name__)
from ciconfig import CIConfig
config = CIConfig()

from fwk.forms import *

class WidgetForm(forms.ModelForm):
    '''
    '''
    class Meta:
        fields = "__all__"
        widgets = {
                'description': forms.Textarea(attrs={'rows':5, 'cols':20}),
        }
        model = Widget

class WidgetDefinitionForm(forms.ModelForm):
    '''
    '''
    class Meta:
        fields = ("name", "description", "view", "refresh", "granularity", )
        widgets = {
                'description': forms.Textarea(attrs={'rows':5, 'cols':20}),
        }
        model = WidgetDefinition

class WidgetDefinitionToRenderMappingForm(forms.ModelForm):
    '''
    '''
    class Meta:
        fields = "__all__"
        model = WidgetDefinitionToRenderMapping 
        

class WidgetRenderForm (forms.Form):
    '''
    '''
    def __init__(self, list,*args, **kwargs):
        super(WidgetRenderForm, self).__init__(*args, **kwargs)
        self.fields["name"] = forms.CharField()
        self.fields["description"] = forms.CharField(widget=forms.Textarea)

class WidgetMappingForm (forms.ModelForm):
    '''
    '''
    class Meta:
        fields = "__all__"
        model = WidgetDefinitionToRenderMapping

