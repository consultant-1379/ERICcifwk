from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter(name='sizeConvert')
@stringfilter
def sizeConvert(value):
    if str(value) == "0":
        size = "--"
    else:
        size = round(float(value)/float(1024*1024*1024),3)
    return size
