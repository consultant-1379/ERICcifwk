from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter(name='convert_space')
@stringfilter
def cut1(value):
    "converts %20 to space"
    return value.replace('%20','  ')
