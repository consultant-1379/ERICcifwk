from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter(name='replaceDot')
@stringfilter
def remDot2(value):
    "converts . to /"
    return value.replace('.','/')
