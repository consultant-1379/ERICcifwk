from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()


urlpatterns = patterns('fem.views',
    #(r'^jobStatus/view/(.*)/api/json/$', 'jobStatusView'),
    (r'^views/api/json/$', 'returnViews'),
    (r'^views/(.*)/api/json/$', 'returnViewDetail'),
    (r'^jobStatus/view/(.*)/api/json/$', 'jobStatus'),
    (r'^jobStatus/$', 'jobStatus'),
    (r'^failedJobs/$', 'getFailingJobs'),
    #(r'^failedJobs2/$', 'getFailingJobs'),
    #(r'^failedJobs2/(\S+)$', 'getFailingJobs'),
    (r'^failedJobs2/view/(.*)/api/json/$', 'getFailingJobs'),
    (r'^jobTrend/$', 'getJobTrend'),
    (r'^jobTrend/(\S+)/$', 'getJobTrend'),
    (r'^jobTrend2/$', 'getJobTrend2'),
    )
