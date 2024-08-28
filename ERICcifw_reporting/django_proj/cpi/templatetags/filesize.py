import os
from django import template
from cpi.models import *

register = template.Library()

@register.simple_tag
def getfilesize(value):
    """Returns the filesize of the filename given in value"""
   
    return os.path.getsize(value)
