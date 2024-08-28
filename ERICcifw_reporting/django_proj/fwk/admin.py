from fwk.models import *
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)

class TvInfoMapAdmin(admin.ModelAdmin):
    list_display = ('team', 'url', 'time', 'sequence')

class PageHitCountAdmin(admin.ModelAdmin):
    list_display = ('page_object_id', 'page', 'hitcount')
    search_fields = ['page_object_id', 'page']

class UserPageHitCountAdmin(admin.ModelAdmin):
    list_display = ('username', 'page', 'hitcount')
    search_fields = ['username__username']


admin.site.register(TvInfoMap, TvInfoMapAdmin)
admin.site.register(Team)
admin.site.register(UrlDisplay)
admin.site.register(Glossary)
admin.site.register(TickerTape)
admin.site.register(TickerTapeSeverity)
admin.site.register(PageHitCount, PageHitCountAdmin)
admin.site.register(UserPageHitCount, UserPageHitCountAdmin)
