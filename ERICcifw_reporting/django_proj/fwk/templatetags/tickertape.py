from django import template
import fwk.utils

register = template.Library()

@register.simple_tag
def getTickerTapeMessage():
    results = fwk.utils.getTickerTapeMessage()
    if results:
        return fwk.utils.getTickerTapeMessage()
    return ""
