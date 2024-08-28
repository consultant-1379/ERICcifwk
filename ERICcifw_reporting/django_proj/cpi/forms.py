from django import forms
from django.core.exceptions import ValidationError
from cireports.models import *
from datetime import datetime
now = datetime.now()
from cpi.models import *
import sys,requests,logging
from requests import Request, Session
from re import search
from cireports.models import *
from ciconfig import CIConfig
from django.contrib.auth.models import User
config = CIConfig()
cpiGaskUrl = config.get("CPI",'gaskUrl')


class DwaxeLogin(forms.Form):
    '''
    Login form for Dwaxe
    '''

    username = forms.CharField(max_length=30,label='DWAXE User')
    password = forms.CharField(max_length=32,widget=forms.PasswordInput)

class CPIDocumentForm(forms.ModelForm):
    
    '''
    Form to edit CPI Documents for the specified drop
    '''

    class Meta:
        model = CPIDocument
        fields = ['section','docName','docNumber','revision','language','author','comment']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.docId = kwargs.pop('docId', None)
        super(CPIDocumentForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        docName = cleaned_data.get('docName')
        docNumber =cleaned_data.get('docNumber')
        language = cleaned_data.get('language')
        revision = cleaned_data.get('revision')
        gaskurl = cpiGaskUrl + str(docNumber) + '&lang=' + str(language) + '&rev=' + str(revision)
        r=requests.get(gaskurl)
        error_pattern="request has failed"
        error = search(error_pattern,r.text)
        user = self.user
        docId=self.docId
        logUser=User.objects.get(username=str(self.user))
        if error:
            raise ValidationError("Unable to fetch the document " + str(docName) + " - " + str(docNumber) + " - with revision " + str(revision) )
            return cleaned_data
        return cleaned_data



class CPIAddDoc(forms.Form):

    '''
    Form to add CPI Documents for the specified drop
    '''
	
    section = forms.CharField(max_length=100,label='Section',required=True)
    docName = forms.CharField(max_length=100,label='Document Name')
    docNumber = forms.CharField(max_length=50,label='Document Number')
    revision = forms.CharField(max_length=5,label='Revision')
    language = forms.CharField(max_length=30,initial="en",label='Language',required=True)
    author = forms.CharField(max_length=30,label='Author')
    comment = forms.CharField(widget=forms.Textarea,label='Comment')

    def clean(self):
        cleaned_data = self.cleaned_data
        docName = cleaned_data.get('docName')
        docNumber =cleaned_data.get('docNumber')
        language = cleaned_data.get('language')
        revision = cleaned_data.get('revision')
        gaskurl = cpiGaskUrl + str(docNumber) + '&lang=' + str(language) + '&rev=' + str(revision)
        r=requests.get(gaskurl)
        error_pattern="request has failed"
        error = search(error_pattern,r.text)
        if error:
            raise ValidationError("Unable to fetch the document " + str(docName) + " - " + str(docNumber) + " - with revision " + str(revision) )
        return cleaned_data
         
class CPIAddFromExcel(forms.Form):

    '''
    Form to bulk upload of document to CPI Baseline
    '''
	
    file  = forms.FileField(label= "Choose excel to upload")
    def clean_file(self):
        contenttype = self.cleaned_data.get('file')
        if '.xls' not in str(contenttype):
            raise ValidationError("Invalid File Type")
        return self.cleaned_data.get('file','')

class CPISearchDoc(forms.Form):

    '''
    Form to Search CPI Document in specified drop
    '''
    
    docNumber = forms.CharField(max_length=50,label="Enter Document Number to Search")  
