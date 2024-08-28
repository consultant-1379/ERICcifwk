from django.db import models

import fem.models

# Create your models here.
# By default, Django gives each model the following field: id = models.AutoField(primary_key=True)
# This is an auto-incrementing primary key, which sets the id to an Integer Field.
# TODO: Update when Django AutoField supports multiple int types

import logging
logger = logging.getLogger(__name__)
# Create your models here.


class Widget (models.Model):
    '''
    '''
    # id field = unsigned integer
    widgetTypes = (("PieChart","PieChart"), ("TrendBarChart","TrendBarChart"),("TrendAreaChart","TrendAreaChart"),("Table", "Table"),)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(max_length=50, null=True, blank=True)
    type = models.CharField(max_length=20,choices=widgetTypes)
    url = models.CharField(max_length=200)

    def __unicode__(self):
        return str(self.name)


class WidgetDefinition (models.Model):
    '''
    '''
    # id field = unsigned integer
    granularityType = (("minute", "Minutes"),("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months"),)

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(max_length=50, null=True, blank=True)
    widget = models.ForeignKey(Widget)
    view = models.ForeignKey(fem.models.View)
    refresh = models.IntegerField(max_length=4, null=True, blank=True)
    granularity = models.CharField(max_length=20,choices=granularityType)

    def __unicode__(self):
        return str(self.name)

class WidgetRender (models.Model):
    '''
    '''
    # id field = unsigned integer
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(max_length=50, null=True, blank=True)

    def __unicode__(self):
        return str(self.name)

class WidgetDefinitionToRenderMapping (models.Model):
    '''
    '''
    # id field = unsigned integer
    widgetDefinition = models.ForeignKey(WidgetDefinition)
    widgetRender = models.ForeignKey(WidgetRender)

    def __unicode__(self):
        return str(self.widgetDefinition) + " : " + str(self.widgetRender)

