# Custom widgets / Complex controls required
from django.forms import Textarea, Widget, MultiWidget, HiddenInput
from django.forms import widgets
from django.forms.utils import flatatt
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse_lazy
from django.forms.widgets import ClearableFileInput

import re
import logging
from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import PatientConsent
import pycountry

logger = logging.getLogger(__name__)


class BadCustomFieldWidget(Textarea):

    """
    Widget to use instead if a custom widget is defined and fails on creation
    """


class DatatypeWidgetAlphanumericxxx(Textarea):

    def render(self, name, value, attrs=None, renderer=None):
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
        output = '<BR>'.join(rendered_widgets)
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
        if name in data:
            return data[name]
        else:
            option_selected = data.get(name + "_0", self.unset_value)
            text_entered = data.get(name + "_1", "")

            if option_selected == self.other_please_specify_value:
                return text_entered
            else:
                return option_selected

    def render(self, name, value, attrs=None, renderer=None):
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


class CalculatedFieldWidget(widgets.TextInput):

    def __init__(self, script, attrs={}):
        attrs['readonly'] = 'readonly'
        self.script = script
        super(CalculatedFieldWidget, self).__init__(attrs=attrs)

    def render(self, name, value, attrs, renderer=None):
        # attrs['readonly'] = 'readonly'
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

    def render(self, name, value, renderer=None):
        html = super(ExtensibleListWidget, self).render(name, value)
        return html + self._buttons_html()


class LookupWidget(widgets.TextInput):
    SOURCE_URL = ""

    def render(self, name, value, attrs, renderer=None):
        return """
            <input type="text" name="%s" id="id_%s" value="%s">
            <script type="text/javascript">
                $("#id_%s").keyup(function() {
                    lookup($(this), '%s');
                });
            </script>
        """ % (name, name, value or '', name, self.SOURCE_URL)


class LookupWidget2(LookupWidget):

    def render(self, name, value, attrs, renderer=None):
        return """
            <input type="text" name="%s" id="id_%s" value="%s">
            <script type="text/javascript">
                $("#id_%s").keyup(function() {
                    lookup2($(this), '%s');
                });
            </script>
        """ % (name, name, value or '', name, self.SOURCE_URL)


class GeneLookupWidget(LookupWidget):
    SOURCE_URL = reverse_lazy('v1:gene-list')


class LaboratoryLookupWidget(LookupWidget2):
    SOURCE_URL = reverse_lazy('v1:laboratory-list')

    def render(self, name, value, attrs, renderer=None):
        widget_html = super(LaboratoryLookupWidget, self).render(name, value, attrs)
        link_to_labs = reverse_lazy("admin:genetic_laboratory_changelist")

        link_html = """<span class="input-group-btn">
                            <a class="btn btn-info" href="#" onclick="window.open('%s');" >Add</a>
                        </span>""" % link_to_labs
        return "<div class='input-group'>" + widget_html + link_html + "</div>"


class DateWidget(widgets.TextInput):

    def render(self, name, value, attrs, renderer=None):
        def just_date(value):
            import datetime
            if value:
                if isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                    return "%s-%s-%s" % (value.day, value.month, value.year)
                else:
                    return value
            else:
                return value
        return """
            <input type="text" name="%s" id="id_%s" value="%s" class="datepicker">
        """ % (name, name, just_date(value) or '')


class CountryWidget(widgets.Select):

    def render(self, name, value, attrs, renderer=None):
        final_attrs = self.build_attrs(attrs, {
            "name": name,
            "class": "form-control",
            "onchange": "select_country(this)",
        })
        output = [format_html("<select{}>", flatatt(final_attrs))]
        empty_option = "<option value=''>---------</option>"
        output.append(empty_option)
        for country in sorted(pycountry.countries, key=lambda c: c.name):
            if value == country.alpha_2:
                output.append("<option value='%s' selected>%s</option>" %
                              (country.alpha_2, country.name))
            else:
                output.append("<option value='%s'>%s</option>" % (country.alpha_2, country.name))
        output.append("</select>")
        return mark_safe('\n'.join(output))


class StateWidget(widgets.Select):

    def render(self, name, value, attrs, renderer=None):
        try:
            state = pycountry.subdivisions.get(code=value)
        except KeyError:
            state = None

        if state is not None:
            country_states = pycountry.subdivisions.get(country_code=state.country.alpha_2)
        else:
            country_states = []

        final_attrs = self.build_attrs(attrs, {
            "name": name,
            "class": "form-control",
        })
        output = [format_html("<select{}>", flatatt(final_attrs))]
        empty_option = "<option value=' '>---------</option>"
        output.append(empty_option)
        for state in country_states:
            if value == state.code:
                output.append("<option value='%s' selected>%s</option>" %
                              (state.code, state.name))
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

    def render(self, name, value, attrs, renderer=None):
        if not value:
            value = self.attrs.get('default', '')

        # final_attrs = dict(self.attrs, name=name)

        final_attrs = self.build_attrs(attrs, {
            "name": name,
            "class": "form-control",
        })
        output = [format_html("<select{}>", flatatt(final_attrs))]
        output.append("<option value='---'>---------</option>")
        for code, display in self._get_items():
            if value == code:
                output.append("<option value='%s' selected>%s</option>" % (code, display))
            else:
                output.append("<option value='%s'>%s</option>" % (code, display))
        output.append("</select>")
        return mark_safe('\n'.join(output))

    def _get_items(self):
        raise NotImplementedError(
            "subclass responsibility - it should return a list of pairs: [(code, display), ...]")


class StateListWidget(ParametrisedSelectWidget):

    def render(self, name, value, attrs, renderer=None):
        country_states = pycountry.subdivisions.get(
            country_code=self._widget_context['questionnaire_context'].upper())
        output = ["<select class='form-control' id='%s' name='%s'>" % (name, name)]
        empty_option = "<option value='---'>---------</option>"
        output.append(empty_option)
        for state in country_states:
            if value == state.code:
                output.append("<option value='%s' selected>%s</option>" %
                              (state.code, state.name))
            else:
                output.append("<option value='%s'>%s</option>" % (state.code, state.name))
        output.append("</select>")
        return mark_safe('\n'.join(output))


class DataSourceSelect(ParametrisedSelectWidget):

    """
    A parametrised select that retrieves values from a data source specified in the parameter
    """

    def _get_items(self):
        """
        :return: [(code, value), ... ] pairs from the metadata json from the registry context
        """
        from rdrf.forms.widgets import datasources
        if hasattr(datasources, self._widget_parameter):
            datasource_class = getattr(datasources, self._widget_parameter)
            datasource = datasource_class(self._widget_context)
            return list(datasource.values())


class PositiveIntegerInput(widgets.TextInput):

    def render(self, name, value, attrs, renderer=None):
        min_value, max_value = self._get_value_range(name)

        return """
            <input type="number" name="%s" id="id_%s" value="%s" min="%s" max="%s">
        """ % (name, name, value, min_value, max_value)

    def _get_value_range(self, cde_name):
        cde_code = cde_name.split("____")[2]
        cde = CommonDataElement.objects.get(code=cde_code)
        max_value = cde.max_value if cde.max_value else 2147483647
        min_value = cde.min_value if cde.min_value else 0
        return min_value, max_value


class RadioSelect(widgets.RadioSelect):
    # def __init__(self, name, value, attrs, renderer):
    #     super(RadioSelect, self).__init__(renderer=renderer)

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        return self._transform(html)

    def _transform(self, html):
        #  make horizontal
        html = re.sub(r'\<ul.+\>', '', html)
        new_html = html.replace("<li>", "").replace("</li>", "").replace("</ul>", "")
        return new_html


class ReadOnlySelect(widgets.Select):

    def render(self, name, value, attrs=None, renderer=None):
        html = super(ReadOnlySelect, self).render(name, value, attrs)
        return self._make_label(html) + self._make_hidden_field(name, value, attrs)

    def _make_hidden_field(self, name, value, attrs):
        return """<input type="hidden" id="%s" name="%s" value="%s"/>""" % (
            attrs['id'], name, value)

    def _make_label(self, html):
        import re
        html = html.replace("\n", "")
        pattern = re.compile(r'.*selected>(.*?)</option>.*')
        m = pattern.match(html)
        if m:
            option_display_text = m.groups(1)[0]
            return """<span class="label label-default">%s</span>""" % option_display_text
        else:
            return html


class GenericValidatorWithConstructorPopupWidget(widgets.TextInput):

    """
    If RPC_COMMAND_NAME is not None
    presents a  textbox with a tick or cross ( valid/invalid)
    As the input is typed , an rpc call ( subclass ) is made to the server
    the result is checked and if the answer is valid , a tick
    is shown else a cross ( tne default )
    If CONSTRUCTOR_TEMPLATE is not None - also display a popup form  and a + symbol next to the
    validator to cause a constructor form to be displayed which "constructs" a value which is used
    to populate the original field value on popup close.
    """
    RPC_COMMAND_NAME = None                               # Subclass Responsibility
    CONSTRUCTOR_FORM_NAME = None                          # If None no popup needed
    CONSTRUCTOR_NAME = None

    class Media:
        # this include doesn't seem to work as advertised so I've
        # included the js on form template
        js = ("js/generic_validator.js",)

    def render(self, name, value, attrs, renderer=None):
        rpc_endpoint_url = reverse_lazy('rpc')
        if self.RPC_COMMAND_NAME:
            attrs["onkeyup"] = "generic_validate(this,'%s','%s');" % (
                rpc_endpoint_url, self.RPC_COMMAND_NAME)
        return super(
            GenericValidatorWithConstructorPopupWidget,
            self).render(
            name,
            value,
            attrs) + self._validation_indicator_html() + self._constructor_button() + self._on_page_load(
            attrs['id'])

    def _constructor_button(self):
        if not self.CONSTRUCTOR_FORM_NAME:
            return ""
        else:
            constructor_form_url = self._get_constructor_form_url(self.CONSTRUCTOR_FORM_NAME)
            return """<span  class="glyphicon glyphicon-add"  onclick="generic_constructor(this, '%s', '%s');"/>""" % (
                self.CONSTRUCTOR_FORM_NAME, constructor_form_url)

    def _validation_indicator_html(self):
        if self.RPC_COMMAND_NAME:
            return """<span class="validationindicator"></span>"""
        else:
            return ""

    def _get_constructor_form_url(self, form_name):
        return reverse_lazy('constructors', kwargs={'form_name': form_name})

    def _on_page_load(self, control_id):
        # force validation on page load
        rpc_endpoint_url = reverse_lazy('rpc')
        if self.RPC_COMMAND_NAME:
            onload_script = """
                <script>
                        $(document).ready(function() {{
                            var controlId = "{control_id}";
                            var element = $("#" + controlId);
                            var rpcEndPoint = "{rpc_endpoint}";
                            var rpcCommand =  "{rpc_command}";
                            generic_validate(document.getElementById(controlId) ,rpcEndPoint, rpcCommand);
                        }});

                </script>
                """.format(control_id=control_id, rpc_endpoint=rpc_endpoint_url, rpc_command=self.RPC_COMMAND_NAME)
            return onload_script
        else:
            return ""


class DNAValidator(GenericValidatorWithConstructorPopupWidget):
    RPC_COMMAND_NAME = "validate_dna"
    CONSTRUCTOR_FORM_NAME = "variation"
    CONSTRUCTOR_NAME = "DNA"


class RNAValidator(GenericValidatorWithConstructorPopupWidget):
    RPC_COMMAND_NAME = "validate_rna"
    CONSTRUCTOR_FORM_NAME = "variation"
    CONSTRUCTOR_NAME = "RNA"


class ProteinValidator(GenericValidatorWithConstructorPopupWidget):
    RPC_COMMAND_NAME = "validate_protein"


class ExonValidator(GenericValidatorWithConstructorPopupWidget):
    RPC_COMMAND_NAME = "validate_exon"


class MultipleFileInput(Widget):
    """
    This widget combines multiple file inputs.
    The files are taken and returned as a list.

    It relies on javascript in form.js, which uses styling from
    rdrf.css.
    """

    @staticmethod
    def input_name(base_name, i):
        return "%s_%s" % (base_name, i)

    number_pat = re.compile(r"_(\d+)$")

    @classmethod
    def input_index(cls, name, field_name, suffix=""):
        "Cuts the index part out of an form input name"
        if field_name.startswith(name) and field_name.endswith(suffix):
            chop = -len(suffix) if suffix else None
            m = cls.number_pat.match(field_name[len(name):chop])
            if m:
                return int(m.group(1))
        return None

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        items = self._render_each(name, value, attrs)

        elements = ("<div class=\"col-xs-12 multi-file\">%s</div>" % item for item in items)
        return """
            <div class="row multi-file-widget" id="%s_id">
              %s
            </div>
        """ % (name, "\n".join(elements))

    class TemplateFile(object):
        url = ""

        def __str__(self):
            return ""

    def _render_base(self, name, value, attrs, index):
        input_name = self.input_name(name, index)
        base = ClearableFileInput().render(input_name, value, attrs)
        hidden = HiddenInput().render(input_name + "-index", index, {})
        return "%s\n%s" % (base, hidden)

    def _render_each(self, name, value, attrs):
        return [self._render_base(name, self.TemplateFile(), attrs, "???")] + [
            self._render_base(name, val, attrs, i)
            for (i, val) in enumerate(value or [])
        ]

    def value_from_datadict(self, data, files, name):
        """
        Gets file input value from each sub-fileinput.
        """
        base_widget = ClearableFileInput()

        indices = (self.input_index(name, n, "-index") for n in data)
        clears = (self.input_index(name, n, "-clear") for n in data)
        uploads = (self.input_index(name, n) for n in files)

        nums = sorted(set(indices).union(clears).union(uploads) - set([None]))

        return [base_widget.value_from_datadict(data, files, self.input_name(name, i))
                for i in nums]


class ValueWrapper:
    def __init__(self, value):
        self.value = value
        self.url = value.url
        # capture the original uploaded filename here
        self.filename = None

    def __str__(self):
        return self.filename


class ConsentFileInput(ClearableFileInput):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)

        def wrap(value):
            """
            Wrap the incoming value so we can display
            the original filename properly
            """
            try:
                if hasattr(value, 'url'):
                    patient_consent = PatientConsent.objects.get(form=value)
                    filename = patient_consent.filename
                    vw = ValueWrapper(value)
                    vw.filename = filename
                    return vw
                else:
                    return ''
            except ValueError:
                # was getting this on the Clear operation
                # if we catch here, the clearing still works ...
                return ''

        context['widget'].update({
            'checkbox_name': checkbox_name,
            'checkbox_id': checkbox_id,
            'is_initial': self.is_initial(value),
            'input_text': self.input_text,
            'value': wrap(value),
            'initial_text': self.initial_text,
            'clear_checkbox_label': self.clear_checkbox_label,
        })

        return context


class SliderWidget(widgets.TextInput):
    def render(self, name, value, attrs=None, renderer=None):
        if not value or not isinstance(value, int):
            value = 0

        context = """
             <script>
                 $(function() {
                     $( "#%s" ).slider({
                         value: '%s',
                         min: 0,
                         max: 100,
                         slide: function( event, ui ) {
                             $( "#%s" ).val( ui.value );
                         }
                     });
                 });
             </script>
             <input type="hidden" id="%s" name="%s" value="%s"/>
             <p>
                 <div class='col-md-2' style="color: green; font-size: x-small"><strong><i>No pain</i></strong></div>
                 <div class='col-md-7' id='%s'></div>
                 <div class='col-md-3' style="color: red; font-size: x-small"><strong><i>Worst possible pain</i></strong></div>
             </p>
         """ % (name, value, attrs['id'], attrs['id'], name, value, name)

        return context
