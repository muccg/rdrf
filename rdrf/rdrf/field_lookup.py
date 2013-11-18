import django.forms
import fields
import widgets
import logging
logger = logging.getLogger('registry_log')


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
       "date": django.forms.DateField,
       "boolean": django.forms.BooleanField,
    }

    UNSET_CHOICE = "UNSET"

    def __init__(self, cde):
        """
        :param cde: Common Data Element model instance
        """
        self.cde = cde

    def _customisation_module_exists(self):
        try:
            __import__(self.CUSTOM_FIELDS_MODULE)
            return True
        except:
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
        custom_field_function = getattr(customisation_module, self._get_custom_field_function_name())
        if not callable(custom_field_function):
            raise Exception("Custom Field Definition for %s is not a function" % self._get_custom_field_function_name())
        else:
            return custom_field_function(self.cde)

    def _get_field_name(self):
        return self.cde.name

    def _get_code(self):
        return self.cde.code

    def _get_datatype(self):
        return self.cde.datatype

    def _get_field_options(self):
        return {"label": self._get_field_name(),
                "help_text": self._get_help_text(),
                "required": self._get_required()}

    def _get_help_text(self):
        return self.cde.instructions

    def _get_required(self):
        return self.cde.is_required

    def _is_dropdown(self):
        return self.cde.pv_group is not None

    def _has_other_please_specify(self):
        #todo improve other please specify check
        if self.cde.pv_group:
            for permitted_value in self.cde.pv_group.permitted_value_set.all():
                if permitted_value.value and permitted_value.value.lower().find("specify") > -1:
                    return True
        return False

    def _has_field_override(self):
        return hasattr(fields, self.FIELD_OVERRIDE_TEMPLATE % self.cde.code)

    def _has_widget_override(self):
        return hasattr(widgets, self.WIDGET_OVERRIDE_TEMPLATE % self.cde.code)

    def _get_field_override(self):
        return getattr(fields, self.FIELD_OVERRIDE_TEMPLATE % self.cde.code)

    def _get_widget_override(self):
        return getattr(widgets, self.WIDGET_OVERRIDE_TEMPLATE % self.cde.code)

    def _has_widget_for_datatype(self):
        return hasattr(widgets, self.DATATYPE_WIDGET_TEMPLATE % self.cde.datatype.replace(" ", ""))

    def _get_widget_for_datatype(self):
        return getattr(widgets, self.DATATYPE_WIDGET_TEMPLATE % self.cde.datatype.replace(" ", ""))

    def _has_field_for_dataype(self):
        return hasattr(fields, self.DATATYPE_FIELD_TEMPLATE % self.cde.datatype.replace(" ",""))

    def _get_field_for_datatype(self):
        return getattr(fields, self.DATATYPE_FIELD_TEMPLATE % self.cde.datatype.replace(" ", ""))

    def _get_permitted_value_choices(self):
        choices = [(self.UNSET_CHOICE, "---")]
        if self.cde.pv_group:
            for permitted_value in self.cde.pv_group.permitted_value_set.all():
                choice_tuple = (permitted_value.code, permitted_value.value)
                choices.append(choice_tuple)
        return choices

    def create_field(self):
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

        """
        options = self._get_field_options()

        if self._is_dropdown():
            choices = self._get_permitted_value_choices()
            options['choices'] = choices
            options['initial'] = self.UNSET_CHOICE
            if self._has_other_please_specify():
                #TODO make this more robust
                other_please_specify_index = ["specify" in pair[1].lower() for pair in choices].index(True)
                other_please_specify_value = choices[other_please_specify_index][0]
                return fields.CharField(max_length=80, help_text=self.cde.instructions, widget=widgets.OtherPleaseSpecifyWidget(main_choices=choices, other_please_specify_value=other_please_specify_value, unset_value=self.UNSET_CHOICE))
            else:
                return django.forms.ChoiceField(**options)
        else:
            widget = None
            if self._has_field_override():
                field = self._get_field_override()
            elif self._has_field_for_dataype():
                field = self._get_field_for_datatype()
            else:
                # we return a plain Django Field defaulting to a character field
                field_or_tuple = self.DATATYPE_DICTIONARY.get(self.cde.datatype.lower(), django.forms.CharField)
                if isinstance(field_or_tuple, tuple):
                    field = field_or_tuple[0]
                    extra_options = field_or_tuple[1]
                    options.update(extra_options)
                else:
                    field = field_or_tuple


            if self._has_widget_override():
                widget = self._get_widget_override()

            elif self._has_widget_for_datatype():
                widget = self._get_widget_for_datatype()

            if widget:
                options['widget'] = widget
                logger.debug("field = %s options = %s widget = %s" % (field, options, widget))
                return field(**options)
            else:
                logger.debug("field = %s options = %s" % (field, options))
                return field(**options)

class ValidatorFactory(object):
    def __init__(self, cde):
        self.cde = cde

    def create_validator(self):
        pass