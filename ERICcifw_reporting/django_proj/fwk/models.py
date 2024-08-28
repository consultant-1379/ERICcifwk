from django.db import models
from datetime import datetime, timedelta
from django.contrib.auth.models import User

# Create your models here.

class Team (models.Model):
    # id field = unsigned smallint
    name = models.CharField(max_length=30)
    desc = models.TextField(null=True, blank=True)
    def __unicode__(self):
        return str(self.name)

class UrlDisplay (models.Model):
    # id field = unsigned smallint
    url = models.CharField(max_length=450)
    title = models.CharField(max_length=50)
    desc = models.TextField(null=True, blank=True)
    def __unicode__(self):
        return u'%s: %s' % (self.title, self.url)

class TvInfoMap (models.Model):
    # id field = unsigned smallint
    team     = models.ForeignKey(Team)
    url      = models.ForeignKey(UrlDisplay)
    time     = models.SmallIntegerField()
    sequence = models.SmallIntegerField()
    def __unicode__(self):
        return u'%s - %s' % (self.team.name, self.url.title)

class CIFWKDevelopmentServer (models.Model):
    '''
    The DevelopmentServer defines the model of a development server
    '''
    # id field = integer
    vm_hostname = models.CharField(max_length=30, unique=True)
    domain_name = models.CharField(max_length=100)
    ipAddress = models.CharField(max_length=30, unique=True)
    bookingDate = models.DateTimeField(default=datetime.now())
    owner = models.CharField(max_length=30, unique=True)
    description = models.TextField(null=True, blank=True)
    def __unicode__(self):
        return str(self.vm_hostname)

class Glossary (models.Model):
    '''
    The Glossary provides information about terms used within the CI Portal
    '''
    # id field = integer
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    def __unicode__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural="Glossaries"

class TickerTapeSeverity (models.Model):
    '''
    The Ticker tape Severity Levels
    '''
    # id field = smallint UNSIGNED
    severity = models.CharField(max_length=50, unique=True)
    def __unicode__(self):
        return str(self.severity)

    class Meta:
        verbose_name_plural="Ticker tape severities"

class TickerTape (models.Model):
    '''
    The Tickertape provides information about Updates
    '''
    # id field = integer UNSIGNED
    title = models.CharField(max_length=60)
    severity = models.ForeignKey(TickerTapeSeverity)
    summary = models.CharField(max_length=200)
    description = models.TextField()
    hide = models.BooleanField(default=0)
    created  = models.DateTimeField(editable=False)

    def __unicode__(self):
        return str(self.title)

class PageHitCount(models.Model):
    '''
    Tracking Pages Hits Counts
    '''
    # id field = integer UNSIGNED
    page_object_id = models.IntegerField(null=True, blank=True)
    page = models.CharField(max_length=100)
    hitcount = models.IntegerField(default=0)

    def __unicode__(self):
        return str(self.page_object_id) + " --> " + str(self.page) + " --> " + str(self.hitcount)

class UserPageHitCount(models.Model):
    '''
    Tracking Page Hit count for User
    '''
    # id field = integer UNSIGNED
    username = models.ForeignKey(User)
    page = models.ForeignKey(PageHitCount)
    hitcount = models.IntegerField(default=0)

    def __unicode__(self):
        return str(self.username) + " --> " + str(self.page) + " --> " + str(self.hitcount)
