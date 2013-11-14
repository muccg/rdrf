import json
from django import template
from django.template import Library

register = Library()



class OverridesNode(template.Node):
    def __init__(self, md):
        self.md = md
    def render(self, context):
        ids = {}
        if md:
            for variation in md.variation_set.all():
                ids[variation.id] = variation.get_validation_overrides()
        return json.dumps(ids)

@register.tag(name="overrides")
def do_overrides(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, md = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    return OverridesNode(md)

