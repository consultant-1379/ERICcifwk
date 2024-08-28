from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter(name='replaceCommaWithLinebreak')
@stringfilter
def remDot2(value):
    "converts ,  to \n"
    return value.replace(', ','\n')
