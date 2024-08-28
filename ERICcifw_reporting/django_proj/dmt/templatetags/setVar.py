from django import template
 
register = template.Library()
 
class SetVarNode(template.Node):
 
    def __init__(self, varName, varValue):
        self.varName = varName
        self.varValue = varValue
 
    def render(self, context):
        try:
            value = template.Variable(self.varValue).resolve(context)
        except template.VariableDoesNotExist:
            value = ""
        context.dicts[0][self.varName] = value
        return u""
 
def setVar(parser, token):
    """
        {% set <var_name>  = <var_value> %}
    """
    parts = token.split_contents()
    if len(parts) < 4:
        raise template.TemplateSyntaxError("'set' tag must be of the form:  {% set <var_name>  = <var_value> %}")
    return SetVarNode(parts[1], parts[3])
 
register.tag('set', setVar)
