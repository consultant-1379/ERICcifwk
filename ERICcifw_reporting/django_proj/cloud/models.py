from django.db import models

import logging
logger = logging.getLogger(__name__)

# Create your models here.
# By default, Django gives each model the following field: id = models.AutoField(primary_key=True)
# This is an auto-incrementing primary key, which sets the id to an Integer Field.

class Gateway (models.Model):
    # id field = unsigned smallint
    name     = models.CharField(max_length=50, unique=True)

    def __unicode__(self):
        return str(self.name)

class GatewayToSppMapping (models.Model):
    # id field = unsigned int
    gateway  = models.ForeignKey(Gateway)
    spp      = models.ForeignKey('metrics.SPPServer')
    date     = models.DateTimeField()

    class Meta:
        unique_together = ('gateway', 'spp')

    def __unicode__(self):
        return str(self.gateway.name) + " - " + str(self.spp.url)
