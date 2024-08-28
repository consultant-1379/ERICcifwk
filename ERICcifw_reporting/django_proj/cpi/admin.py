from cpi.models import *
from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from django.contrib.admin import SimpleListFilter
from django.utils.translation import ugettext_lazy as _


class documentAdmin(admin.ModelAdmin):
        list_display = ('docName','docNumber','revision','cpiDrop')
        list_filter = ('section__product',)
        search_fields=['docNumber']

class sectionDisplay(admin.ModelAdmin):
	list_display = ('title','parent')
        list_filter = ('product',)
	search_fields=['title',]


admin.site.register(CPIDocument,documentAdmin)
admin.site.register(CPISection,sectionDisplay)

class Identity(admin.ModelAdmin):
	exclude = ('status','lastBuild','lastModified','owner')
	def save_model(self, request, obj, form, change):
	        obj.owner = str(request.user).upper()
        	obj.save()

admin.site.register(CPIIdentity,Identity)
