from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()


urlpatterns = patterns('avs.views',
    (r'^$', 'getEpics'),
    (r'^epics$', 'getEpics'),
    (r'^epics/(\S+)$', 'getStories'),
    (r'^stories$', 'getStories'),
    (r'^stories/(\S+)/(\S+)$', 'getStorySkeleton'),
    (r'^stories/(\S+)$', 'getStory'),
    (r'^avs_import/$', 'avs_import'),
    (r'^avs_submit/$', 'avs_submit'),
    (r'^avs_import_success/$', 'avs_import_success'),
    (r'^avs_import_failure/$', 'avs_import_failure'),
    (r'^avs_search/$', 'avs_search'),
    (r'^avs_search_submit/$', 'avs_search_submit'),
    (r'^avs_view_skeleton/(\S+)$', 'avs_view_skeleton'),
    (r'^avs_download_skeleton/(\S+)$', 'avs_download_skeleton'),
    (r'^files$', 'listFiles'),
    (r'^files/(\d+)$', 'getFile'),
    (r'^avs_rest/$', 'avs_rest'),
    )

