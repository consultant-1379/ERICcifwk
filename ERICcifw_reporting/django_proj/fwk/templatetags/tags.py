from django import template
import re
import fwk.utils

register = template.Library()

@register.simple_tag
def getCifwkVersion():
    return fwk.utils.getCifwkVersion()

@register.simple_tag
def getSPPLinks():
    return fwk.utils.getSPPLinks()

@register.simple_tag
def getSPPNewMenuLinks():
    return fwk.utils.getSPPNewMenuLinks()

@register.filter(is_safe=True)
def replace(value, arg):
    value = re.sub(arg, '', value)
    return value

@register.filter(is_safe=True)
def counter(value1, value2):
    result = int(value1)+int(value2)
    return result

