import json
import re
import django.forms
from django.forms import MultiValueField, MultiWidget, FileField, DateInput
from django.forms.widgets import CheckboxSelectMultiple
from django.utils.safestring import mark_safe
from django.urls import reverse
from collections import OrderedDict

from rdrf.forms.dynamic import fields
from rdrf.forms.widgets import widgets
import logging
from rdrf.forms.dynamic.calculated_fields import CalculatedFieldScriptCreator, CalculatedFieldScriptCreatorError
from rdrf.forms.dynamic.validation import ValidatorFactory
from rdrf.models.definition.models import CommonDataElement

from intframework.utils import get_field_source

from django.utils.functional import lazy
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

mark_safe_lazy = lazy(mark_safe, str)

logger = logging.getLogger(__name__)


class FieldContext:

    """
    Where a field can appear - on a form or in a questionnaire
    On the questionnaire we use a different label text
    """
    CLINICAL_FORM = "Form"
    QUESTIONNAIRE = "Questionnaire"


class FieldFactory(object):
    # registry overrides
    CUSTOM_FIELDS_MODULE = "custom_fields"
    CUSTOM_FIELD_FUNCTION_NAME_TEMPLATE = "custom_field_%s"

    # specific overrides in rdrf_module
    FIELD_OVERRIDE_TEMPLATE = "CustomField%s"
    WIDGET_OVERRIDE_TEMPLATE = "CustomWidget%s"

    # Specialised fields/widgets based on datatype
    DATATYPE_FIELD_TEMPLATE = "DatatypeField%s"
    DATATYPE_WIDGET_TEMPLATE = "DatatypeWidget%s"

    # A mapping of known types to django fields
    # NB options can be added as pair as in the alphanumeric case  - don't return _instances here
    # updated before return
    DATATYPE_DICTIONARY = {
        "string": django.forms.CharField,
        "alphanumeric": (django.forms.RegexField, {"regex": r'^[a-zA-Z0-9]*$'}),
        "integer": django.forms.IntegerField,
        "date": (fields.IsoDateField, {"help_text": _("DD-MM-YYYY"), "input_formats": ["%d-%m-%Y"]}),
        "boolean": django.forms.BooleanField,
        "float": django.forms.FloatField,
        "email": django.forms.EmailField,
    }

    UNSET_CHOICE = ""

    def __init__(self, registry, registry_form, section, cde, questionnaire_context=None,
                 injected_model=None, injected_model_id=None, is_superuser=False, is_verification=False,
                 csp_nonce=None):
        """
        :param cde: Common Data Element model instance
        """
        self.registry = registry
        self.registry_form = registry_form
        self.section = section
        self.is_verification = is_verification
        self.cde = cde
        self.questionnaire_context = questionnaire_context
        if questionnaire_context:
            self.context = FieldContext.QUESTIONNAIRE
        else:
            self.context = FieldContext.CLINICAL_FORM

        self.validator_factory = ValidatorFactory(self.cde)
        self.complex_field_factory = ComplexFieldFactory(self.cde)
        self.primary_model = injected_model
        self.primary_id = injected_model_id
        self.is_superuser = is_superuser
        self.csp_nonce = csp_nonce

    def _customisation_module_exists(self):
        try:
            __import__(self.CUSTOM_FIELDS_MODULE)
            return True
        except BaseException:
            return False

    def _get_customisation_module(self):
        return __import__(self.CUSTOM_FIELDS_MODULE)

    def _get_custom_field_function_name(self):
        return self.CUSTOM_FIELD_FUNCTION_NAME_TEMPLATE % self.cde.code

    def _has_custom_field(self):
        customisation_module = self._get_customisation_module()
        return hasattr(customisation_module, self._get_custom_field_function_name())

    def _get_custom_field(self):
        customisation_module = self._get_customisation_module()
        custom_field_function = getattr(
            customisation_module, self._get_custom_field_function_name())
        if not callable(custom_field_function):
            raise Exception("Custom Field Definition for %s is not a function" %
                            self._get_custom_field_function_name())
        else:
            return custom_field_function(self.cde)

    def _get_field_name(self):
        if self.context == FieldContext.CLINICAL_FORM:
            return self._get_cde_link(
                _(self._get_label())) if self.is_superuser else _(self._get_label())
        else:
            q_field_text = self.cde.questionnaire_text
            if not q_field_text:
                q_field_text = self._get_cde_link(
                    _(self.cde.name)) if self.is_superuser else _(self.cde.name)
            return self._get_cde_link(q_field_text) if self.is_superuser else q_field_text

    def _get_label(self):
        if not self.is_verification:
            return self.cde.name
        else:
            return "%s/%s/%s" % (self.registry_form.name,
                                 self.section.display_name,
                                 self.cde.name)

    def _get_cde_link(self, name):
        if not settings.DESIGN_MODE:
            return name
        cde_url = reverse('admin:rdrf_commondataelement_change', args=[self.cde.code])
        label_link = mark_safe_lazy("<a target='_blank' href='%s'>%s</a>" % (cde_url, name))
        return label_link

    def _get_code(self):
        return self.cde.code

    def _get_datatype(self):
        return self.cde.datatype

    def _get_field_options(self):
        options_dict = {"label": self._get_field_name(),
                        "help_text": self._get_help_text(),
                        "required": self._get_required(),
                        }
        validators = self.validator_factory.create_validators()
        if validators:
            options_dict['validators'] = validators

        return options_dict

    def _get_help_text(self):
        if self.cde.instructions:
            return _(self.cde.instructions)

    def _get_required(self):
        return self.cde.is_required

    def _is_dropdown(self):
        return self.cde.pv_group is not None

    def _has_other_please_specify(self):
        # todo improve other please specify check
        if self.cde.pv_group:
            for permitted_value in self.cde.pv_group.permitted_value_set.all():
                if permitted_value.value and permitted_value.value.lower().find("specify") > -1:
                    return True
        return False

    def _is_calculated_field(self):
        return bool(self.cde.calculation)

    def _is_complex(self):
        return self.complex_field_factory._is_complex()

    def _has_field_override(self):
        return hasattr(fields, self.FIELD_OVERRIDE_TEMPLATE % self.cde.code)

    def _has_widget_override(self):
        return hasattr(widgets, self.WIDGET_OVERRIDE_TEMPLATE % self.cde.code)

    def _get_field_override(self):
        return getattr(fields, self.FIELD_OVERRIDE_TEMPLATE % self.cde.code)

    def _get_widget_override(self):
        return getattr(widgets, self.WIDGET_OVERRIDE_TEMPLATE % self.cde.code)

    def _has_widget_for_datatype(self):
        return hasattr(
            widgets,
            self.DATATYPE_WIDGET_TEMPLATE %
            self.cde.datatype.replace(
                " ",
                ""))

    def _get_widget_for_datatype(self):
        return getattr(
            widgets,
            self.DATATYPE_WIDGET_TEMPLATE %
            self.cde.datatype.replace(
                " ",
                ""))

    def _has_field_for_dataype(self):
        return hasattr(
            fields,
            self.DATATYPE_FIELD_TEMPLATE %
            self.cde.datatype.replace(
                " ",
                ""))

    def _get_field_for_datatype(self):
        return getattr(
            fields,
            self.DATATYPE_FIELD_TEMPLATE %
            self.cde.datatype.replace(
                " ",
                ""))

    def _get_permitted_value_choices(self):
        choices = [(self.UNSET_CHOICE, "---")]
        if self.cde.pv_group:
            for permitted_value in self.cde.pv_group.permitted_value_set.all().order_by(
                    'position'):
                value = _(permitted_value.value)
                if self.context == FieldContext.QUESTIONNAIRE:
                    q_value = getattr(permitted_value, 'questionnaire_value')
                    if q_value:
                        value = q_value
                choice_tuple = (permitted_value.code, value)
                choices.append(choice_tuple)
        return choices

    def _widget_search(self, widget_class_name, widget_config=None):
        """

        :param widget_class_name: E.g. "RadioSelect" Allow us to override
        :return:
        """
        import django.forms as django_forms
        if self._is_parametrised_widget(widget_class_name, widget_config):
            widget_context = {"registry_model": self.registry,
                              "registry_form": self.registry_form,
                              "cde": self.cde,
                              "on_questionnaire": self.context == FieldContext.QUESTIONNAIRE,
                              "questionnaire_context": self.questionnaire_context,
                              "primary_model": self.primary_model,
                              "primary_id": self.primary_id
                              }
            return self._get_parametrised_widget_instance(widget_class_name, widget_config, widget_context)

        if hasattr(widgets, widget_class_name):
            widget_class = getattr(widgets, widget_class_name)
            return widget_class

        if hasattr(django_forms, widget_class_name):
            widget_class = getattr(django_forms, widget_class_name)
            return widget_class

        return None

    def is_json(self, some_string):
        try:
            json.loads(some_string)
        except ValueError:
            return False
        return True

    def _is_parametrised_widget(self, widget_string, widget_config):
        return ":" in widget_string or self.is_json(widget_config)

    def _get_parametrised_widget_instance(self, widget_string, widget_config, widget_context):
        # Given a widget string ( from the DE specification page )
        # <SomeWidgetClassName>:<widget parameter string>
        if ":" in widget_string:
            widget_class_name, widget_parameter = widget_string.split(":")
        else:
            widget_class_name, widget_parameter = widget_string, None
        if hasattr(widgets, widget_class_name):
            widget_class = getattr(widgets, widget_class_name)
            if self.is_json(widget_config):
                return widget_class(**json.loads(widget_config),
                                    widget_parameter=widget_parameter,
                                    widget_context=widget_context)
            else:
                return widget_class(widget_parameter=widget_parameter,
                                    widget_context=widget_context)
        else:
            logger.warning("could not locate widget from widget string: %s" % widget_string)

    def create_field(self):
        field = self._create_field()
        field.cde = self.cde
        return field

    def _create_field(self):
        """
        :param cde: Common Data Element instance
        :return: A field object ( with widget possibly)
        We use a few conventions to find field class/widget class definitions.
        A check is made for any customised fields or widgets in the client app ( which
        must have name custom_fields.py.)
        The custom_fields module must contain functions with take a cde and return a field object.
        A custom field function must have name like

        custom_field_CDECODE23  ( assuming CDECODE23 is the code of the CDE)

        This function must return a field object.

        Then a check to look up any overrides based on code /datatype in this package is performed.

        Datatypes having their own field classes nust exist in the fields module
        class CustomFieldCDECod334
        class DatatypeFieldSomeDatatypeName

        The same applies to special widgets we create

        class CustomWidgetCDECode233
        class DatatypeEWidgetSomeDataTypeName

        Finally a Django field is returned based the DATATYPE_DICTIONARY
        ( if no field mapping is found a TextArea field is returned.)

        TODO Refactor this!

        """
        options = self._get_field_options()

        if self._is_external():
            from rdrf.forms.dynamic.fields import ExternalField
            return ExternalField(**options)

        if self._is_new_style_calculated_field():
            return fields.NewStyleCalculatedField(**options)

        if self._is_dropdown():
            choices = self._get_permitted_value_choices()
            options['choices'] = choices
            options['initial'] = self.UNSET_CHOICE
            if self._has_other_please_specify():
                other_please_specify_index = [
                    "other" in pair[0].lower() for pair in choices].index(True)
                other_please_specify_value = choices[other_please_specify_index][0]
                if self.cde.widget_name:
                    try:
                        widget_class = getattr(widgets, self.cde.widget_name)
                        widget = widget_class(
                            main_choices=choices,
                            other_please_specify_value=other_please_specify_value,
                            unset_value=self.UNSET_CHOICE)
                    except BaseException:
                        widget = widgets.OtherPleaseSpecifyWidget(
                            main_choices=choices,
                            other_please_specify_value=other_please_specify_value,
                            unset_value=self.UNSET_CHOICE)
                else:
                    widget = widgets.OtherPleaseSpecifyWidget(
                        main_choices=choices,
                        other_please_specify_value=other_please_specify_value,
                        unset_value=self.UNSET_CHOICE)

                return fields.CharField(
                    max_length=80,
                    required=options.get("required", False),
                    help_text=_(self.cde.instructions),
                    widget=widget,
                    label=_(self.cde.name))
            else:
                if self.cde.widget_name:
                    widget = self._widget_search(self.cde.widget_name, self.cde.widget_config)
                else:
                    widget = None

                if self.cde.allow_multiple:
                    widget = widget or CheckboxSelectMultiple
                    if widget:
                        options['widget'] = widget

                    options['choices'] = [
                        choice_pair for choice_pair in options['choices'] if choice_pair[1] != '---']
                    return fields.RDRFMultipleChoiceField(**options)
                else:
                    if widget:
                        options['widget'] = widget
                        if "RadioSelect" in str(widget):
                            # get rid of the unset choice
                            options["choices"] = options['choices'][1:]

                    if self.cde.code in [
                            "CDEPatientNextOfKinState",
                            "CDEPatientNextOfKinCountry"]:
                        # These are dynamic now and alter their reange lists dynamically so have
                        # to switch off validation
                        from rdrf.forms.dynamic.fields import ChoiceFieldNoValidation
                        return ChoiceFieldNoValidation(**options)

                    if self.cde.code in ['State', 'Country']:
                        # because these are dynamic lookup fields the usual validation wasn't
                        # working
                        from rdrf.forms.dynamic.fields import ChoiceFieldNonBlankValidation
                        return ChoiceFieldNonBlankValidation(**options)

                    return django.forms.ChoiceField(**options)
        else:
            # Not a drop down
            widget = None

            if self._has_field_override():
                field = self._get_field_override()
            elif self._has_field_for_dataype():
                field = self._get_field_for_datatype()
            else:
                if self._is_complex():
                    return self.complex_field_factory.create(options)
                # File Field
                if self._get_datatype() == 'file':
                    return self._create_file_field(options)

                if self._is_calculated_field():
                    try:
                        parser = CalculatedFieldScriptCreator(
                            self.registry,
                            self.registry_form,
                            self.section,
                            self.cde,
                            injected_model=self.primary_model,
                            injected_model_id=self.primary_id,
                            csp_nonce=self.csp_nonce)
                        script = parser.get_script()
                        from rdrf.forms.widgets.widgets import CalculatedFieldWidget
                        options['widget'] = CalculatedFieldWidget(script)
                        return django.forms.CharField(**options)

                    except CalculatedFieldScriptCreatorError as pe:
                        logger.error("Calculated Field %s Error: %s" % (self.cde, pe))

                field_or_tuple = self.DATATYPE_DICTIONARY.get(
                    self.cde.datatype.lower(), django.forms.CharField)

                if isinstance(field_or_tuple, tuple):
                    field = field_or_tuple[0]
                    extra_options = field_or_tuple[1]
                    options.update(extra_options)
                else:
                    field = field_or_tuple

            if self.cde.widget_name:
                try:
                    widget = self._widget_search(self.cde.widget_name, self.cde.widget_config)
                except Exception as ex:
                    logger.error("Error setting widget %s for cde %s: %s" %
                                 (self.cde.widget_name, self.cde, ex))
                    raise ex
                    widget = None
            else:
                if self.cde.datatype.lower() == 'date':
                    widget = DateInput(format=('%d-%m-%Y'),
                                       attrs={'class': 'datepicker',
                                              'placeholder': 'Select a date'})

            if self._has_widget_override():
                widget = self._get_widget_override()

            elif self._has_widget_for_datatype():
                widget = self._get_widget_for_datatype()

            if widget:
                options['widget'] = widget

            return field(**options)

    def _create_file_field(self, options):
        if self.cde.allow_multiple:
            return fields.MultipleFileField(**options)
        else:
            return FileField(**options)

    def _is_external(self):
        return get_field_source(self.cde.code) == "external"

    def _is_new_style_calculated_field(self):
        if not self.registry.has_feature("use_new_style_calcs"):
            return False
        is_calc = self.cde.datatype == "calculated"
        if is_calc:
            from rdrf.forms.fields import calculated_functions as cf
            func = getattr(cf, self.cde.code)
            if callable(func):
                return True


class ComplexFieldParseError(Exception):
    pass


class ComplexFieldFactory(object):
    DATATYPE_PATTERN = r"^ComplexField\((.*)\)$"

    def __init__(self, cde):
        self.cde = cde

    def _load_components(self):
        self.component_cdes = self._get_component_cdes()
        self.component_fields = []
        self.component_widgets = []

        for component_cde in self.component_cdes:
            component_field = self._get_field(component_cde)
            self.component_fields.append(component_field)
            component_widget = component_field.widget
            self.component_widgets.append(component_widget)

    def _is_complex(self):
        return re.match(self.DATATYPE_PATTERN, self.cde.datatype)

    def __str__(self):
        return "ComplexField for CDE %s with datatype %s" % (self, self.cde.datatype)

    def _get_field(self, cde):
        field_factory = FieldFactory(cde)
        component_field = field_factory.create_field()
        return component_field

    def _get_component_cdes(self):
        # We assume the cde.datatype field looks like ComplexField(CDE01,CDE02,...)
        m = self._is_complex()
        if not m:
            raise ComplexFieldParseError("%s couldn't be created - didn't match pattern" % self)
        else:
            cde_code_csv = m.groups(0)[0]
            cde_codes = [code.strip() for code in cde_code_csv.split(",")]
            cdes = []
            for cde_code in cde_codes:
                try:
                    cde = CommonDataElement.objects.get(code=cde_code)
                    cdes.append(cde)
                except Exception as ex:
                    logger.error("Couldn't get CDEs for %s - errored on code %s: %s" %
                                 (self, self.cde.code, ex))
                    raise ComplexFieldParseError("%s couldn't be created: %s" % (self, ex))

            return cdes

    def _create_multi_widget(self):
        class_dict = {}
        complex_widget_class_name = "ComplexMultiWidgetFrom%s" % "".join(
            [cde.code for cde in self.component_cdes])

        def decompress_method(itself, value):
            """
            :param itself:
            :param value: a sorted dictionary of cde codes to values
            :return:
            """
            if value:
                return list(value.values())
            else:
                return [None] * len(self.component_cdes)

        def format_output_method(itself, rendered_widgets):
            "&nbsp;&nbsp;&nbsp;&nbsp;".join(rendered_widgets)

        class_dict['decompress'] = decompress_method
        # class_dict['format_output'] = format_output_method
        multi_widget_class = type(str(complex_widget_class_name), (MultiWidget,), class_dict)
        multi_widget_instance = multi_widget_class(self.component_widgets, attrs=None)
        return multi_widget_instance

    def create(self, options_dict):
        self._load_components()

        options_dict["fields"] = self.component_fields
        complex_field_class_name = "MultiValueFieldFrom%s" % "".join(
            [cde.code for cde in self.component_cdes])
        class_dict = {}

        def compress_method(itself, data_list):
            """
            :param itself:
            :param data_list: values for each component from the corresponding widget
            :return: a sorted dictionary of cde code : value
            """
            codes = [cde.code for cde in self.component_cdes]
            return OrderedDict(zip(codes, data_list))

        class_dict["widget"] = self._create_multi_widget()
        class_dict['compress'] = compress_method
        complex_field_class = type(
            str(complex_field_class_name), (MultiValueField,), class_dict)

        return complex_field_class(**options_dict)
