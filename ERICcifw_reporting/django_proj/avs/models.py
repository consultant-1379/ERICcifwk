from django.db import models
import cireports
import logging
logger = logging.getLogger(__name__)

class Epic (models.Model):
    '''
    An EPIC is a collection of one or more stories which together
    provide a solution.
    '''
    name    = models.CharField(max_length=20, unique=True)
    title   = models.TextField()
    def __unicode__(self):
        return self.name

# Store information relating to the Story. A Story  relates to 1 or many Test Cases.
class UserStory (models.Model):
    name        = models.CharField(max_length=20, unique=True)
    title       = models.TextField()
    epic        = models.ForeignKey(Epic)
    version     = models.IntegerField()
    def __unicode__(self):
        return self.name

class EpicUserStoryMapping (models.Model):
    epic         = models.ForeignKey(Epic)
    user_story   = models.ForeignKey(UserStory)

class AVSFile (models.Model):
    '''
    Audit trail of files uploaded.
    '''
    dateCreated  = models.DateTimeField('date created',null=True, blank=True)
    fileName     = models.CharField(max_length=50, unique=True)
    fileContent  = models.TextField(null=True, blank=True)
    owner        = models.CharField(max_length=10)
    def __unicode__(self):
        return self.fileName
        
class AVS (models.Model):
    dateCreated  = models.DateTimeField('date created',null=True, blank=True)
    lastUpdated  = models.DateTimeField('date last updated',null=True, blank=True)
    avsId        = models.CharField(max_length=20, unique=True)
    owner        = models.CharField(max_length=10)
    avsFile      = models.ForeignKey(AVSFile)
    revision     = models.IntegerField()    
    def __unicode__(self):
        return self.avsId

class Component (models.Model):
    name        = models.CharField(max_length=50, unique=True)
    def __unicode__(self):
        return self.name

class TestCase (models.Model):
    TEST_TYPES = (
            ("Func", "Functional Tests"),
            ("Perf", "Performance Tests"),
            ("Work", "Workflow Tests"),
            ("High", "High Availability Tests"), 
            ("Scal", "Scalability Tests"),
            ("Robu", "Robustness Tests"),
            ("Secu", "Security Tests"),
            )
    dateCreated = models.DateTimeField('date created',null=True, blank=True)
    lastUpdated = models.DateTimeField('date last updated',null=True, blank=True)
    tcId        = models.CharField(max_length=35)
    title       = models.TextField()
    desc        = models.TextField()
    type        = models.CharField(max_length=4, choices=TEST_TYPES)
    component   = models.ForeignKey(Component)
    priority    = models.CharField(max_length=20)   
    groups      = models.TextField(null=True, blank=True)
    pre         = models.TextField(null=True, blank=True)
    vusers      = models.CharField(max_length=50,null=True, blank=True)
    context     = models.CharField(max_length=200,null=True, blank=True)
    revision    = models.IntegerField(default=1)
    archived     = models.IntegerField(default=1)
    def __unicode__(self):
        return self.tcId
    
class TestCaseUserStoryMapping(models.Model):
    user_story = models.ForeignKey(UserStory)
    test_case = models.ForeignKey(TestCase)

    def __unicode__(self):
        return str(self.user_story) + " --> " + str(self.test_case)

class TestResult (models.Model):
    testCase = models.ForeignKey(TestCase)
    testResult = models.CharField(max_length=20)
    testDuration = models.IntegerField()  
    testStart = models.CharField(max_length=20)
    testFinish = models.CharField(max_length=20)
    testFailString = models.TextField(null=True, blank=True)
    def __unicode__(self):
        return str(self.testCase.tcId)

class ActionPoint (models.Model):
    desc = models.TextField(null=True, blank=True)
    testCase = models.ForeignKey(TestCase)   
    def __unicode__(self):
        return self.desc

class VerificationPoint (models.Model):
    desc = models.TextField(null=True, blank=True)
    actionPoint = models.ForeignKey(ActionPoint)
    def __unicode__(self):
        return self.desc

 
