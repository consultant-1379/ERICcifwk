from django.db import models
from django import forms
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
import cireports.models
import re

# Create your models here.
# By default, Django gives each model the following field: id = models.AutoField(primary_key=True)
# This is an auto-incrementing primary key, which sets the id to an Integer Field.
# TODO: Update when Django AutoField supports multiple int types

import logging
logger = logging.getLogger(__name__)

class EventType (models.Model):
    # id field = unsigned smallint
    eventTypeName = models.CharField(max_length=50)
    eventTypeDb = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    def __unicode__(self):
        return self.eventTypeName + " : " + str(self.eventTypeDb)

class SPPServer (models.Model):
    # id field = unsigned smallint
    name = models.CharField(max_length=50, unique=True)
    url = models.URLField(max_length=200, unique=True)

    def __unicode__(self):
        return str(self.name) + " (" + str(self.url) + ")"
