 # Custom widgets / Complex controls required
from django.forms import Textarea, Widget, MultiWidget
from django.forms import widgets
from registry.utils import get_static_url
from django.utils.safestring import mark_safe

import logging
logger = logging.getLogger("registry_log")


class BadCustomFieldWidget(Textarea):
    """
    Widget to use instead if a custom widget is defined and fails on creation
    """
    pass


class CustomWidgetC18583(Widget):
    def render(self, name, value, attrs=None):
        return "<h1>%s</h1>" % value


class DatatypeWidgetAlphanumericxxx(Textarea):
    def render(self, name, value, attrs=None):
        html = super(DatatypeWidgetAlphanumericxxx, self).render(name, value, attrs)
        return "<table border=3>%s</table>" % html


class OtherPleaseSpecifyWidget(MultiWidget):
    def __init__(self, main_choices, other_please_specify_value, unset_value, attrs=None):
        self.main_choices = main_choices
        self.other_please_specify_value = other_please_specify_value
        self.unset_value = unset_value

        _widgets = (
            widgets.Select(attrs=attrs, choices=self.main_choices),
            widgets.TextInput(attrs=attrs)
        )

        super(OtherPleaseSpecifyWidget, self).__init__(_widgets, attrs)

    def format_output(self, rendered_widgets):
        output = u'<BR>'.join(rendered_widgets)
        return output

    def decompress(self, value):
        """
        :param value: value from db or None
        :return: values to be supplied to the select widget and text widget:
        If no value, we show unset for dropdown and nothing in text
        If a value is supplied outside of the dropdown range we provide it to the text box
        and set the select widget to the indicator for "Other please specify"
        otherwise we provide the selected value to the select box and an empty string to
        the textbox
        """
        if not value:
            return [self.unset_value, ""]

        if value not in [choice[0] for choice in self.main_choices]:
            return [self.other_please_specify_value, value]
        else:
            return [value, ""]

    def value_from_datadict(self, data, files, name):
        logger.debug("value from datadict: data = %s name = %s" % (data, name))
        if name in data:
            return data[name]
        else:
            option_selected = data.get(name + "_0", self.unset_value)
            text_entered = data.get(name + "_1","")

            if option_selected == self.other_please_specify_value:
                return text_entered
            else:
                return option_selected

    def render(self, name, value, attrs=None):
        select_id = "id_" + name + "_0"
        specified_value_textbox_id = "id_" + name + "_1"
        script = """
        <script>
            (function() {
                $("#%s").bind("change", function() {
                    if ($(this).val() == "%s") {
                        $("#%s").show();
                    }
                    else {
                        $("#%s").hide();
                    }
                });
            })();
            (function(){ $("#%s").change();})();

        </script>
        """ % (select_id, self.other_please_specify_value, specified_value_textbox_id, specified_value_textbox_id, select_id)

        return super(OtherPleaseSpecifyWidget, self).render(name, value, attrs) + script


class HgvsValidation(widgets.TextInput):
    
    def __init__(self, attrs={}):
        self.attrs = attrs
        super(HgvsValidation, self).__init__(attrs=attrs)
    
    def render(self, name, value, attrs):
        return mark_safe(u"""<input type="text" id="%s">
                         <script type="text/javascript">
                            $("#%s").keyup(function() {
                                console.log('test');
                            });
                         </script>""" % (name, name))


class CalculatedFieldWidget(widgets.TextInput):
    def __init__(self, script, attrs={}):
        attrs['readonly'] = 'readonly'
        self.script = script
        super(CalculatedFieldWidget, self).__init__(attrs=attrs)

    def render(self, name, value, attrs):
        #attrs['readonly'] = 'readonly'
        return super(CalculatedFieldWidget, self).render(name, value, attrs) + self.script

class ExtensibleListWidget(MultiWidget):
    def __init__(self, prototype_widget, attrs={}):
        self.widget_count = 1
        self.prototype_widget = prototype_widget
        super(ExtensibleListWidget, self).__init__([prototype_widget], attrs)

    def _buttons_html(self):
        return """<button type="button" onclick="alert('todo')">Click Me!</button>"""

    def decompress(self, data):
        """

        :param data: dictionary contains items key with a list of row data for each widget
        We create as many widgets on the fly so that render method can iterate
        data  must not be a list else render won't call decompress ...
        :return: a list of data for the widgets to render
        """
        from copy import copy
        if not data:
            self.widgets = [ copy(self.prototype_widget) ]
            return [None]
        else:
            items = data["items"]
            num_widgets = len(items)
            self.widgets = [ copy(self.prototype_widget) for i in range(num_widgets) ]
            return data

    def render(self, name, value):
        html = super(ExtensibleListWidget, self).render(name, value)
        return html + self._buttons_html()
