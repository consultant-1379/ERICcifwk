from django.db import models

class Job(models.Model):
    '''
    A Jenkins Job
    '''
    # id field = unsigned integer
    name           = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class View(models.Model):
    '''
    A collection of Jenkins Jobs which together form a specific view in Jenkins
    '''
    # id field = unsigned integer
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class JobViewMapping(models.Model):
    '''
    Mapping of jobs to views - a single job may be in multiple views
    '''
    # id field = unsigned integer
    job = models.ForeignKey(Job)
    view = models.ForeignKey(View)

    def __unicode__(self):
        return str(self.job) + " --> " + str(self.view)

class JobResult(models.Model):
    '''
    The result of a Job Execution
    '''
    # id field = unsigned integer
    job = models.ForeignKey(Job)
    buildId = models.PositiveIntegerField()
    status = models.CharField(max_length=10)
    passed = models.BooleanField(default=False)
    failed = models.BooleanField(default=False)
    unstable = models.BooleanField(default=False)
    aborted = models.BooleanField(default=False)
    url = models.CharField(max_length=200)
    info = models.CharField(max_length=100)
    finished = models.DateTimeField(null=True, blank=True)
    finished_ts = models.BigIntegerField(null=True, blank=True)
    duration = models.BigIntegerField(null=True, blank=True)

    def __unicode__(self):
        return str(self.buildId) + ": " + str(self.status)

class CacheTable(models.Model):
    '''
    The result of a Job Execution
    '''
    url = models.CharField(max_length=255, primary_key=True)
    data = models.TextField(max_length=90000000)
    inserted = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return str(self.url) + ": " + str(self.url)

class FemURLs(models.Model):
    # id field = integer
    url = models.CharField(max_length=255)

    def __unicode__(self):
        return str(self.url)

    class Meta:
          verbose_name_plural="Fem urls"

class FemKGBUrl(models.Model):
    # id field = unsigned smallint
    base = models.CharField(max_length=255)
    kgbStarted = models.CharField(max_length=255)
    kgbFinished = models.CharField(max_length=255)
    https =  models.BooleanField(default=False)
    order = models.IntegerField(max_length=4, unique=True)

    def __unicode__(self):
        return str(self.order)+":"+str(self.base)
