from django import template
register = template.Library()

@register.filter(name='nexusUrl')
def nexusUrl(obj, product):
    return obj.getNexusUrl(product)
