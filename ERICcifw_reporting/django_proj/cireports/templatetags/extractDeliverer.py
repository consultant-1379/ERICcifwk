from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()

@register.filter(name='extractDeliverer')
@stringfilter
def extractDeliverer(string):
    "Extracts the deliverer email from the String passed and returns it"
    return findBetween( string, "(", ")")

def findBetween( data, first, last ):
    try:
        start = data.index( first ) + len( first )
        end = data.index( last, start )
        return data[start:end]
    except ValueError:
        return ""
