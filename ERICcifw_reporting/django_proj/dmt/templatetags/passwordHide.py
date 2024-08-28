from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter(name='passwordHide')
@stringfilter
def passwordHide(value):
    "converts letters to *"
    result = ""
    for letter in value:
        result += "*"
    return result

