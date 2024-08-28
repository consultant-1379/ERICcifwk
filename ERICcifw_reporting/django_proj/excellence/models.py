from django.db import models
from django import forms
from datetime import datetime, timedelta

import logging
logger = logging.getLogger(__name__)
# Create your models here.

class Organisation (models.Model):
    '''
    A definition of an organisational unit in Ericsson. An organisation can have a
    parent organisation, in which case it's metrics will be included in the
    aggregation of that organisation's data.

    The organisational heirarchy in Ericsson is:

    BU -> DU -> PDU -> RA -> Team

    but the model makes no assumptions that this is in place - it is the responsibility
    of the view layer to ensure the correct heirarchy is maintained.

    '''
    # id field = unsigned integer
    orgTypes = (
                    ("BU", "Business Unit" ),
                    ("DU", "Development Unit"),
                    ("PDU", "Product Development Unit"),
                    ("RA", "Requirement Area"),
                    ("Team", "Team"),
                )
    name = models.CharField(max_length=30, unique=True)
    description = models.TextField(null=True, blank=True)
    owner = models.CharField(max_length=10)
    # parent == the organisation to which this organisation reports
    parent = models.ForeignKey("self", null=True, blank=True)
    type = models.CharField(max_length=100, choices=orgTypes)

    def __unicode__(self):
        return str(self.name)

class Category (models.Model):
    '''
    '''
    # id field = unsigned integer
    name = models.CharField(max_length=100)
    version = models.IntegerField()

    def __unicode__(self):
        return "Category: " + str(self.name) + ", Version: " +str(self.version)

    class Meta:
          verbose_name_plural="Categories"

class Question (models.Model):
    '''
    '''
    # id field = unsigned integer
    question = models.CharField(max_length=1000)
    action = models.CharField(max_length=1000)
    category = models.ForeignKey(Category)
    enable = models.BooleanField(default=1)
    low_level = models.FloatField()

    def __unicode__(self):
        return str(self.question)

class Answer (models.Model):
    '''
    '''
    # id field = unsigned integer
    answer = models.CharField(max_length=30)
    value = models.IntegerField()

    def __unicode__(self):
        return str(self.answer)

class DiscussionItems (models.Model):
    '''
    '''
    # id field = unsigned integer
    comment = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return str(self.comment)

class Questionnaire (models.Model):
    '''
    '''
    # id field = unsigned integer
    questionnaire_Name = models.CharField(max_length=30, null=True, blank=True)
    organisation = models.ForeignKey(Organisation)
    version = models.IntegerField()

    def __unicode__(self):
        return str(self.organisation)

class Response (models.Model):
    '''
    '''
    # id field = unsigned integer
    questionnaire = models.ForeignKey(Questionnaire)
    dateAndTimeTaken = models.DateTimeField()
    takenBy = models.CharField(max_length=30)
    questionnairePart = models.IntegerField()

    def __unicode__(self):
        return str(self.questionnaire)

class QuestionAnswerResponseMapping (models.Model):
    '''
    '''
    # id field = unsigned integer
    question = models.ForeignKey(Question)
    answer  = models.ForeignKey(Answer)
    comment = models.ForeignKey(DiscussionItems)
    response = models.ForeignKey(Response)

    def __unicode__(self):
        return "Question: " + str(self.question) + " Answer: " + str(self.answer) + " Response: " + str(self.response)
