 # Custom widgets / Complex controls required
from django.forms import Textarea, Widget, MultiWidget
from django.forms import widgets
from registry.utils import get_static_url
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse_lazy

import logging
logger = logging.getLogger("registry_log")

import pycountry


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
            text_entered = data.get(name + "_1", "")

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
        return mark_safe(u'''<input type="text" name="%s" id="id_%s" value="%s"><div id="result_id_%s"></div>
                         <script type="text/javascript">
                            $("#id_%s").keyup(function() {
                                hgvsValidation($(this));
                            }).ready(function() {
                                hgvsValidation($("#id_%s"));
                            });
                         </script>''' % (name, name, value or '', name, name, name))


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
            self.widgets = [copy(self.prototype_widget)]
            return [None]
        else:
            items = data["items"]
            num_widgets = len(items)
            self.widgets = [copy(self.prototype_widget) for i in range(num_widgets)]
            return data

    def render(self, name, value):
        html = super(ExtensibleListWidget, self).render(name, value)
        return html + self._buttons_html()


class LookupWidget(widgets.TextInput):
    SOURCE_URL = ""
    
    def render(self, name, value, attrs):
        return """
            <input type="text" name="%s" id="id_%s" value="%s">
            <script type="text/javascript">
                $("#id_%s").keyup(function() {
                    lookup($(this), '%s');
                });
            </script>
        """ % (name, name, value or '', name, self.SOURCE_URL)

class LookupWidget2(LookupWidget):
    def render(self, name, value, attrs):
        return """
            <input type="text" name="%s" id="id_%s" value="%s">
            <script type="text/javascript">
                $("#id_%s").keyup(function() {
                    lookup2($(this), '%s');
                });
            </script>
        """ % (name, name, value or '', name, self.SOURCE_URL)

class GeneLookupWidget(LookupWidget):
    SOURCE_URL = reverse_lazy('gene_source')

    
class LaboratoryLookupWidget(LookupWidget2):
    SOURCE_URL = reverse_lazy('laboratory_source')


class DateWidget(widgets.TextInput):

    def render(self, name, value, attrs):
        def just_date(value):
            if value:
                if hasattr(value, 'date'):
                    d = value.date()
                    return "%s-%s-%s" % (d.day, d.month, d.year)
                else:
                    return value
            else:
                return value
        return """
            <input type="text" name="%s" id="id_%s" value="%s" class="datepicker" readonly>
        """ % (name, name, just_date(value) or '')


class CountryWidget(widgets.Select):

    def render(self, name, value, attrs):
        if not value:
            value = self.attrs['default']

        countries = pycountry.countries

        output = ["<select onChange='select_country(this);' id='%s' name='%s'>" % (name, name)]
        for country in countries:
            if value == country.alpha2:
                output.append("<option value='%s' selected>%s</option>" % (country.alpha2, country.name))
            else:
                output.append("<option value='%s'>%s</option>" % (country.alpha2, country.name))
        output.append("</select>")
        return mark_safe('\n'.join(output))


class StateWidget(widgets.Select):

    def render(self, name, value, attrs):
        if not value:
            value = self.attrs['default']

        try:
            state = pycountry.subdivisions.get(code=value)
        except KeyError:
            state = pycountry.subdivisions.get(code=self.attrs['default'])

        country_states = pycountry.subdivisions.get(country_code=state.country.alpha2)
        
        output = ["<select id='%s' name='%s'>" % (name, name)]
        for state in country_states:
            if value == state.code:
                output.append("<option value='%s' selected>%s</option>" % (state.code, state.name))
            else:
                output.append("<option value='%s'>%s</option>" % (state.code, state.name))
        output.append("</select>")
        return mark_safe('\n'.join(output))


class ParametrisedSelectWidget(widgets.Select):
    """
    A dropdown that can retrieve values dynamically from the registry that "owns" the form containing the widget.
    This is an abstract class which must be subclassed.
    NB. The field factory is responsible for supplying the registry model to the widget instance  at
    form creation creation time.
    """
    def __init__(self, *args, **kwargs):
        self._widget_parameter = kwargs['widget_parameter']
        del kwargs['widget_parameter']
        self._widget_context = kwargs['widget_context']
        del kwargs['widget_context']
        super(ParametrisedSelectWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs):
        if not value:
            value = self.attrs.get('default', '')

        output = ["<select class='form-control' id='%s' name='%s'>" % (name, name)]
        output.append("<option value='---'>---</option>")
        for code, display in self._get_items():
            if value == code:
                output.append("<option value='%s' selected>%s</option>" % (code, display))
            else:
                output.append("<option value='%s'>%s</option>" % (code, display))
        output.append("</select>")
        return mark_safe('\n'.join(output))

    def _get_items(self):
        raise NotImplementedError("subclass responsibility - it should return a list of pairs: [(code, display), ...]")


class DataSourceSelect(ParametrisedSelectWidget):
    """
    A parametrised select that retrieves values from a data source specified in the parameter
    """
    def _get_items(self):
        """
        :return: [(code, value), ... ] pairs from the metadata json from the registry context
        """
        from rdrf import datasources
        logger.debug("checking for data source: %s" % self._widget_parameter)
        if hasattr(datasources, self._widget_parameter):
            datasource_class = getattr(datasources, self._widget_parameter)
            datasource = datasource_class(self._widget_context)
            return datasource.values()
