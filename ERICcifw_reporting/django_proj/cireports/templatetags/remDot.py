from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter(name='remDot')
@stringfilter
def remDot(value):
    "converts . to _"
    return value.replace('.','_')
