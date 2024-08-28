from django.db import models
from cireports.models import *
from mptt.models import MPTTModel, TreeForeignKey
from ciconfig import CIConfig


class CPISection(MPTTModel):
    '''
    CPI Section, specifying the folder name for the document
    '''
    title = models.CharField(max_length=55)
    product = models.ForeignKey(Product,db_index=True)
    description = models.CharField(max_length=255)
    parent=TreeForeignKey('self',null=True,blank=True,related_name='children')

    class MPTTMeta:
        order_insertion_by = ['title']
        unique_together = (("title","product"),)

    def __unicode__(self):
        return str(self.title)

class CPIIdentity(models.Model):

    '''
    Overall Library, specifying the library name, Rstate, identity number
    '''
    drop=models.ForeignKey(Drop)
    cpiDrop=models.CharField("CPI Build",max_length=50,help_text="Enter the Build Name, without any space")
    title=models.CharField(max_length=100,blank=True,null=True)
    identity=models.CharField(max_length=50)
    rstate=models.CharField(max_length=5)
    status=models.CharField(max_length=20,null=True)
    lastModified=models.DateTimeField(null=True)
    lastBuild=models.DateTimeField(null=True)
    owner=models.CharField(max_length=50)
    firstBuild=models.DateTimeField(null=True,help_text="Enter date of first CPI library available")
    endBuild=models.DateTimeField(null=True,help_text="Enter next date of delivery cut off date" )

    class Meta:
        unique_together = (("identity","rstate"),)
        verbose_name_plural="Cpi Identities"

    def __unicode__(self):
        return str(self.cpiDrop) + "-" + str(self.rstate)


class CPIDocument (models.Model):
    '''
    Details of the document to be included in CPI Library
    '''
    section = models.ForeignKey(CPISection)
    docName = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    language = models.CharField(max_length=5)
    docNumber = models.CharField(max_length=50)
    revision = models.CharField(max_length=5)
    drop = models.ForeignKey(Drop)
    cpiDrop = models.ForeignKey(CPIIdentity)
    deliveryDate = models.DateTimeField()
    owner = models.CharField(max_length=50)
    comment = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return str(self.docName) + " - " + str(self.docNumber) + " - " + str(self.drop)

    class Meta:
        unique_together = (("docNumber","drop","cpiDrop",),)



		
