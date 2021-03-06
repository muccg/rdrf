import datetime
import json
import jsonschema
import logging
import os.path
import yaml

from pyparsing import Word, nums, Optional, delimitedList, alphanums, Literal, LineEnd, LineStart

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
from django.forms.models import model_to_dict
from django.utils.safestring import mark_safe
from django.core.exceptions import PermissionDenied

from rdrf.helpers.utils import format_date, parse_iso_datetime
from rdrf.helpers.utils import LinkWrapper
from rdrf.events.events import EventType

from rdrf.forms.fields.jsonb import DataField

logger = logging.getLogger(__name__)


class InvalidAbnormalityConditionError(Exception):
    pass


class InvalidQuestionnaireError(Exception):
    pass


def new_style_questionnaire(registry):
    for form_model in registry.forms:
        if form_model.questionnaire_questions:
            if len(form_model.questionnaire_list) > 0:
                return True
    return False


class SectionManager(models.Manager):

    def get_by_natural_key(self, code):
        return self.get(code=code)


class Section(models.Model):
    objects = SectionManager()

    """
    A group of fields that appear on a form as a unit
    """
    code = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    questionnaire_display_name = models.CharField(max_length=200, blank=True)
    elements = models.TextField()
    allow_multiple = models.BooleanField(
        default=False, help_text="Allow extra items to be added")
    extra = models.IntegerField(
        blank=True, null=True, help_text="Extra rows to show if allow_multiple checked")
    questionnaire_help = models.TextField(blank=True)

    def natural_key(self):
        return (self.code, )

    def __str__(self):
        return self.code

    def get_elements(self):
        return [code.strip() for code in self.elements.split(",")]

    @property
    def cde_models(self):
        codes = self.get_elements()
        qs = CommonDataElement.objects.filter(code__in=codes)
        cdes = {cde.code: cde for cde in qs}
        return [cdes[code] for code in codes]

    def get_cde(self, code):
        for cde_model in self.cde_models:
            if cde_model.code == code:
                return cde_model
        raise KeyError("cde %s is not in section %s" % (code,
                                                        self.code))

    def clean(self):
        errors = {}
        codes = set(self.get_elements())
        qs = CommonDataElement.objects.filter(code__in=codes)
        missing = sorted(codes - set(qs.values_list("code", flat=True)))

        if missing:
            errors["elements"] = [
                ValidationError(
                    "section %s refers to CDE with code %s which doesn't exist" %
                    (self.display_name, code)) for code in missing]

        if any(x in self.code for x in (" ", "&")):
            errors["code"] = ValidationError(
                "Section %s code '%s' should not contain spaces or &" %
                (self.display_name, self.code))

        if errors:
            raise ValidationError(errors)

    def cdes_presence(self):
        # returns a dict showing if elements are present or not
        codes = self.get_elements()
        return {code: CommonDataElement.objects.filter(code=code).exists() for code in codes}

    def existing_cde_models(self):
        codes = self.get_elements()
        exisiting_cdes = CommonDataElement.objects.filter(code__in=codes)
        # returns a dict of cdes, with False value if a code is not existing
        cdes = dict(self.cdes_presence(), **{cde.code: cde for cde in exisiting_cdes})
        return cdes

    def get_admin_url(self):
        return reverse('admin:{0}_{1}_change'.format(self._meta.app_label, self._meta.model_name),
                       args=(self.pk,))

    def get_admin_link(self):
        return '<a href="{0}" target="_blank">{1}</a>'.format(self.get_admin_url(), self)

    def get_cde_links(self):
        existing = self.existing_cde_models()
        return ", ".join([existing[code].get_admin_link() if existing[code]
                          else "<span class='alert-danger'>{0}</span>".format(code) for code in existing])

    def get_form_links(self):
        forms = RegistryForm.objects.filter(sections__icontains=self.code)
        return ", ".join([form.get_admin_link() if self.code in form.get_sections() else "" for form in forms])


class RegistryManager(models.Manager):

    def get_by_natural_key(self, code):
        return self.get(code=code)


class RegistryType:
    NORMAL = 1                 # no exposed contexts - all forms stored in a default context
    HAS_CONTEXTS = 2               # supports additional contexts but has no context form groups defined
    HAS_CONTEXT_GROUPS = 3  # registry has context form groups defined


class Registry(models.Model):
    objects = RegistryManager()

    class Meta:
        verbose_name_plural = "registries"

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10, unique=True)
    desc = models.TextField()
    splash_screen = models.TextField()
    patient_splash_screen = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=20, blank=True)
    # a section which holds registry specific patient information
    patient_data_section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True)
    # metadata is a dictionary
    # keys ( so far):
    # "visibility" : [ element, element , *] allows GUI elements to be shown in demographics form for a given registry but not others
    # a dictionary of configuration data -  GUI visibility
    metadata_json = models.TextField(blank=True)

    def natural_key(self):
        return (self.code, )

    def add_feature(self, feature):
        metadata = self.metadata
        features = metadata.get("features", [])
        if feature not in features:
            features.append(feature)
            metadata["features"] = features
            self.metadata_json = json.dumps(metadata)

    def remove_feature(self, feature):
        metadata = self.metadata
        features = metadata.get("features", [])
        features.remove(feature)
        metadata["features"] = features
        self.metadata_json = json.dumps(metadata)

    @property
    def features(self):
        return self.metadata.get("features", [])

    @features.setter
    def features(self, features):
        metadata = self.metadata
        metadata["features"] = features
        self.metadata_json = json.dumps(metadata)

    @property
    def registry_type(self):
        if not self.has_feature("contexts"):
            return RegistryType.NORMAL
        elif ContextFormGroup.objects.filter(registry=self).count() == 0:
            return RegistryType.HAS_CONTEXTS
        else:
            return RegistryType.HAS_CONTEXT_GROUPS

    @property
    def diagnosis_code(self):
        # used by verification workflow
        return self.metadata.get("diagnosis_code", None)

    @property
    def has_groups(self):
        return self.registry_type == RegistryType.HAS_CONTEXT_GROUPS

    @property
    def is_normal(self):
        return self.registry_type == RegistryType.NORMAL

    @property
    def metadata(self):
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except ValueError:
                logger.error("Registry %s has invalid json metadata: data = '%s" %
                             (self, self.metadata_json))
                return {}
        else:
            return {}

    @metadata.setter
    def metadata(self, metadata):
        self.metadata_json = json.dumps(metadata)

    def get_metadata_item(self, item):
        try:
            return self.metadata[item]
        except KeyError:
            return True

    def shows(self, element):
        # does this registry make visible extra/custom functionality ( false by default)
        if "visibility" in self.metadata:
            return element in self.metadata["visibility"]

    @property
    def questionnaire(self):
        try:
            return RegistryForm.objects.get(registry=self, is_questionnaire=True)
        except RegistryForm.DoesNotExist:
            return None
        except RegistryForm.MultipleObjectsReturned:
            return None

    @property
    def generated_questionnaire_name(self):
        return "GeneratedQuestionnaireFor%s" % self.code

    @property
    def questionnaire_section_prefix(self):
        return "GenQ" + self.code

    @property
    def patient_fields(self):
        """
        Registry specific fields for the demographic form
        """
        from rdrf.forms.dynamic.field_lookup import FieldFactory
        field_pairs = []  # list of pairs of cde and field object
        if self.patient_data_section:
            patient_cde_models = self.patient_data_section.cde_models
            for cde_model in patient_cde_models:
                field_factory = FieldFactory(self, None, self.patient_data_section, cde_model)
                field = field_factory.create_field()
                field_pairs.append((cde_model, field))
        # The fields were appearing in the "reverse" order, hence this
        field_pairs.reverse()
        return field_pairs

    @property
    def specific_fields_section_title(self):
        if self.patient_data_section:
            return self.patient_data_section.display_name

    def _progress_cdes(self, progress_type="diagnosis"):
        # returns list of triples (form_model, section_model, cde_model)
        results = []
        for form_model in self.forms:
            if progress_type == "diagnosis" and "genetic" in form_model.name.lower():
                continue
            elif progress_type == "genetic" and "genetic" not in form_model.name.lower():
                continue
            completion_cde_codes = [cde.code for cde in form_model.complete_form_cdes.all()]
            for section_model in form_model.section_models:
                for cde_model in section_model.cde_models:
                    if cde_model.code in completion_cde_codes:
                        results.append((form_model, section_model, cde_model))
        return results

    @property
    def diagnosis_progress_cde_triples(self):
        return self._progress_cdes()

    @property
    def genetic_progress_cde_triples(self):
        return self._progress_cdes(progress_type="genetic")

    @property
    def has_diagnosis_progress_defined(self):
        return len(self.diagnosis_progress_cde_triples) > 0

    @property
    def has_genetic_progress_defined(self):
        return len(self.genetic_progress_cde_triples) > 0

    def _generated_section_questionnaire_code(self, form_name, section_code):
        return self.questionnaire_section_prefix + form_name + section_code

    def generate_questionnaire(self):
        if not new_style_questionnaire(self):
            return
        questions = []
        for form in self.forms:
            for sectioncode_dot_cdecode in form.questionnaire_list:
                section_code, cde_code = sectioncode_dot_cdecode.split(".")
                questions.append((form.name, section_code, cde_code))

        from collections import OrderedDict
        section_map = OrderedDict()

        for form_name, section_code, cde_code in questions:
            section_key = (form_name, section_code)

            if section_key in section_map:
                section_map[section_key].append(cde_code)
            else:
                section_map[section_key] = [cde_code]

        generated_questionnaire_form_name = self.generated_questionnaire_name

        # get rid of any existing generated sections
        for section in Section.objects.all():
            if section.code.startswith(self.questionnaire_section_prefix):
                section.delete()

        generated_section_codes = []

        section_ordering_map = {}

        for (form_name, original_section_code) in section_map:
            # generate sections
            try:
                original_section = Section.objects.get(code=original_section_code)
            except Section.DoesNotExist:
                raise InvalidQuestionnaireError(
                    "section with code %s doesn't exist!" % original_section_code)

            qsection = Section()
            qsection.code = self._generated_section_questionnaire_code(
                form_name, original_section_code)
            qsection.questionnaire_help = original_section.questionnaire_help
            try:
                original_form = RegistryForm.objects.get(registry=self, name=form_name)
            except RegistryForm.DoesNotExist:
                raise InvalidQuestionnaireError("form with name %s doesn't exist!" % form_name)

            if not original_section.questionnaire_display_name:
                qsection.display_name = original_form.questionnaire_name + \
                    " - " + original_section.display_name
            else:
                qsection.display_name = original_form.questionnaire_name + \
                    " - " + original_section.questionnaire_display_name

            qsection.allow_multiple = original_section.allow_multiple
            qsection.extra = 0
            qsection.elements = ",".join(
                [cde_code for cde_code in section_map[(form_name, original_section_code)]])
            qsection.save()
            generated_section_codes.append(qsection.code)

            section_ordering_map[form_name + "." + original_section_code] = qsection.code

        ordered_codes = []

        for f in self.forms:
            for s in f.get_sections():
                k = f.name + "." + s
                if k in section_ordering_map:
                    ordered_codes.append(section_ordering_map[k])

        patient_info_section = self._get_patient_info_section()

        generated_questionnaire_form, created = RegistryForm.objects.get_or_create(
            registry=self,
            name=generated_questionnaire_form_name,
            sections=patient_info_section + "," + self._get_patient_address_section() + "," + ",".join(ordered_codes)
        )
        generated_questionnaire_form.registry = self
        generated_questionnaire_form.is_questionnaire = True
        generated_questionnaire_form.sections = patient_info_section + \
            "," + self._get_patient_address_section() + "," + ",".join(ordered_codes)
        generated_questionnaire_form.save()

        logger.info("generated questionnaire for registry %s" % self.code)

    def _get_patient_info_section(self):
        return "PatientData"

    def _get_patient_address_section(self):
        return "PatientDataAddressSection"

    @property
    def generic_sections(self):
        return [self._get_patient_info_section(), self._get_patient_address_section()]

    @property
    def generic_cdes(self):
        codes = []
        for generic_section_code in self.generic_sections:
            generic_section_model = Section.objects.get(code=generic_section_code)
            codes.extend(generic_section_model.get_elements())
        return codes

    def __str__(self):
        return "%s (%s)" % (self.name, self.code)

    def as_json(self):
        return dict(
            obj_id=self.id,
            name=self.name,
            code=self.code
        )

    @property
    def forms(self):
        return [f for f in RegistryForm.objects.filter(registry=self).order_by('position')]

    def has_feature(self, feature):
        if "features" in self.metadata:
            return feature in self.metadata["features"]
        else:
            return False

    def clean(self):
        self._check_metadata()
        self._check_dupes()

    def _check_dupes(self):
        dupes = [r for r in Registry.objects.all() if r.code.lower() == self.code.lower() and r.pk != self.pk]
        names = " ".join(["%s %s" % (r.code, r.name) for r in dupes])
        if len(dupes) > 0:
            raise ValidationError(
                "Code %s already exists ( ignore case) in: %s" %
                (self.code, names))

    @property
    def context_name(self):
        try:
            return self.metadata['context_name']
        except KeyError:
            return "Context"

    @property
    def default_context_form_group(self):
        for cfg in ContextFormGroup.objects.filter(registry=self):
            if cfg.is_default:
                return cfg

    @property
    def free_forms(self):
        # return form models which do not below to any form group
        cfgs = ContextFormGroup.objects.filter(registry=self)
        owned_form_ids = [form_model.pk for cfg in cfgs.all() for form_model in cfg.forms]

        forms = sorted([form_model for form_model in RegistryForm.objects.filter(registry=self) if
                        form_model.pk not in owned_form_ids and not form_model.is_questionnaire],
                       key=lambda form: form.position)

        return forms

    @property
    def fixed_form_groups(self):
        return [cfg for cfg in ContextFormGroup.objects.filter(
            registry=self, context_type="F").order_by("is_default").order_by("name")]

    @property
    def multiple_form_groups(self):
        return [cfg for cfg in ContextFormGroup.objects.filter(
            registry=self, context_type="M").order_by("name")]

    def _check_metadata(self):
        if self.metadata_json == "":
            return True
        try:
            value = json.loads(self.metadata_json)
            if not isinstance(value, dict):
                raise ValidationError("metadata json field should be a valid json dictionary")
        except ValueError:
            raise ValidationError("metadata json field should be a valid json dictionary")

    @property
    def proms_system_url(self):
        try:
            return self.metadata["proms_system_url"]
        except KeyError:
            return None


def get_owner_choices():
    """
    Get choices for CDE owner drop down.
    Used to get the list of classes which CDEs can be attached to.
    UNUSED means this CDE will not be used to construct any forms in the registry.

    """
    # for display_name, owner_model_func in settings.CDE_MODEL_MAP.items():
    #     owner_class_name = owner_model_func().__name__
    #     choices.append((owner_class_name, display_name))

    return [("UNUSED", "UNUSED"), ("USED", "USED")]


class CDEPermittedValueGroup(models.Model):
    code = models.CharField(max_length=250, primary_key=True)

    def as_dict(self):
        d = {}
        d["code"] = self.code
        d["values"] = []
        for value in CDEPermittedValue.objects.filter(pv_group=self):
            value_dict = {}
            value_dict["code"] = value.code
            value_dict["value"] = value.value
            value_dict["questionnaire_value"] = value.questionnaire_value
            value_dict["desc"] = value.desc
            value_dict["position"] = value.position
            d["values"].append(value_dict)
        return d

    def members(self, get_code=True):
        if get_code:
            att = "code"
        else:
            att = "value"

        return [
            getattr(
                v,
                att) for v in CDEPermittedValue.objects.filter(
                pv_group=self).order_by('position')]

    # interface used by proms

    @property
    def options(self):
        return [{"code": pv.code, "text": pv.value} for pv in CDEPermittedValue.objects.filter(pv_group=self).order_by('position')]

    def __str__(self):
        return "PVG %s containing %d items" % (self.code, len(self.members()))


class CDEPermittedValue(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30)
    value = models.CharField(max_length=256)
    questionnaire_value = models.CharField(max_length=256, null=True, blank=True)
    desc = models.TextField(null=True)
    pv_group = models.ForeignKey(CDEPermittedValueGroup, related_name='permitted_value_set', on_delete=models.CASCADE)
    position = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = (('pv_group', 'code'),)

    def pvg_link(self):
        url = reverse('admin:rdrf_cdepermittedvaluegroup_change', args=(self.pv_group.code,))
        return mark_safe("<a href='%s'>%s</a>" % (url, self.pv_group.code))

    pvg_link.short_description = 'Permitted Value Group'

    def questionnaire_value_formatted(self):
        if not self.questionnaire_value:
            return mark_safe("<i><font color='red'>Not set</font></i>")
        return mark_safe("<font color='green'>%s</font>" % self.questionnaire_value)

    questionnaire_value_formatted.short_description = 'Questionnaire Value'

    def position_formatted(self):
        if not self.position:
            return mark_safe("<i><font color='red'>Not set</font></i>")
        return mark_safe("<font color='green'>%s</font>" % self.position)

    position_formatted.short_description = 'Order position'

    def __str__(self):
        return "Member of %s" % self.pv_group.code


class CommonDataElement(models.Model):
    DATA_TYPES = (
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Decimal'),
        ('alphanumeric', 'Alpha Numeric'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('range', 'Range (Set of allowed values)'),
        ('calculated', 'Calculated (Derived data element)'),
        ('file', 'File'),
    )
    code = models.CharField(max_length=30, primary_key=True)
    name = models.CharField(max_length=250, blank=False, help_text="Label for field in form")
    desc = models.TextField(blank=True, help_text="origin of field")
    datatype = models.CharField(max_length=50, help_text="Type of field", choices=DATA_TYPES)
    instructions = models.TextField(
        blank=True, help_text="Used to indicate help text for field")
    pv_group = models.ForeignKey(
        CDEPermittedValueGroup,
        null=True,
        blank=True,
        help_text="If a range, indicate the Permissible Value Group",
        on_delete=models.CASCADE)
    allow_multiple = models.BooleanField(
        default=False, help_text="If a range, indicate whether multiple selections allowed")
    max_length = models.IntegerField(
        blank=True, null=True, help_text="Length of field - only used for character fields")
    max_value = models.DecimalField(
        blank=True,
        null=True,
        max_digits=12,
        decimal_places=2,
        help_text="Only used for numeric fields")
    min_value = models.DecimalField(
        blank=True,
        null=True,
        max_digits=12,
        decimal_places=2,
        help_text="Only used for numeric fields")
    abnormality_condition = models.TextField(
        blank=True,
        null=True,
        help_text="Rules triggering a visual notification encouraging the user to process with further investigations")
    is_required = models.BooleanField(
        default=False, help_text="Indicate whether field is non-optional")
    pattern = models.CharField(
        max_length=50,
        blank=True,
        help_text="Regular expression to validate string fields (optional)")
    widget_name = models.CharField(
        max_length=80,
        blank=True,
        help_text="If a special widget required indicate here - leave blank otherwise")
    calculation = models.TextField(
        blank=True,
        help_text="Calculation in javascript. Use context.CDECODE to refer to other CDEs. Must use context.result to set output")
    questionnaire_text = models.TextField(
        blank=True,
        help_text="The text to use in any public facing questionnaires/registration forms")

    important = models.BooleanField(
        default=False, help_text="Indicate whether the field should be emphasised with a green asterisk")

    def __str__(self):
        return "CDE %s:%s" % (self.code, self.name)

    class Meta:
        verbose_name = 'Data Element'
        verbose_name_plural = 'Data Elements'

    def get_range_members(self, get_code=True):
        """
        if get_code false return the display value
        not the code
        """
        if self.pv_group:
            return self.pv_group.members(get_code=get_code)
        else:
            return None

    def get_value(self, stored_value):
        if stored_value == "NaN":
            # the DataTable was not escaping this value and interpreting it as NaN
            return None
        elif self.datatype.lower() == "date":
            try:
                return parse_iso_datetime(stored_value).date()
            except ValueError:
                return None
        return stored_value

    def get_display_value(self, stored_value):
        if stored_value is None:
            return ""
        elif stored_value == "NaN":
            # the DataTable was not escaping this value and interpreting it as NaN
            return ":NaN"
        elif self.pv_group:
            # if a range, return the display value
            try:
                values_dict = self.pv_group.as_dict()
                for value_dict in values_dict["values"]:
                    if value_dict["code"] == stored_value:
                        display_value = value_dict["value"]
                        return display_value

            except Exception as ex:
                logger.error("bad value for cde %s %s: %s" % (self.code,
                                                              stored_value,
                                                              ex))
        elif self.datatype.lower() == "date":
            try:
                return parse_iso_datetime(stored_value).date()
            except ValueError:
                return ""

        if stored_value == "NaN":
            # the DataTable was not escaping this value and interpreting it as NaN
            return ":NaN"

        return stored_value

    def clean(self):
        """
        TO BE DELETED
        # this was causing issues with form progress completion cdes record
        # todo update the way form progress completion cdes are recorded to
        # only use code not cde.name!

        if "." in self.name:
            raise ValidationError(
                "CDE %s  name error '%s' has dots - this causes problems please remove" %
                (self.code, self.name))
        """

        if " " in self.code:
            raise ValidationError(
                "CDE [%s] has space(s) in code - this causes problems please remove" %
                self.code)

        if not validate_abnormality_condition(self.abnormality_condition, self.datatype):
            raise ValidationError(
                f"""The abnormality condition is incorrect. It should something like
                     x in ("code_1", "code_2"), or x <= 10
                    """)

    def is_abnormal(self, value):
        if self.abnormality_condition:

            # some sanity check
            # ignore any non integer / float / string values (.i.e. we ignore multiple selectors)
            # (if you add a list to the condition, it will be critical to validate deeply the list value to avoid hack)
            if not isinstance(value, str) and not isinstance(value, float) and not isinstance(value, int):
                return False

            # some sanity checks (it could happen because we updated the validation to be more restrictive
            # but we did not update the existing abnormality_condition to match the new restriction)
            if not validate_abnormality_condition(self.abnormality_condition, self.datatype):
                raise InvalidAbnormalityConditionError(
                    f"The abnormality condition of CDE {self.code} is incorrect: {self.abnormality_condition}")

            # extract each individual rules from abnormality_condition
            # ignore empty lines
            abnormality_condition_lines = [rule.strip() for rule in self.abnormality_condition.splitlines() if
                                           rule.strip()]

            try:
                typed_value = self._get_typed_value(value)
            except ValueError:
                return False

            return any([eval(line, {'x': typed_value}) for line in abnormality_condition_lines])

        # no abnormality condition
        return False

    def _get_typed_value(self, value):
        if self.datatype == "integer":
            return int(value)

        if self.datatype == "float":
            return float(value)
        return value

    def get_usage(self):
        sections = Section.objects.filter(elements__icontains=self.code)
        section_links = ", ".join([link for link in [section.get_admin_link() if self.code in section.get_elements()
                                                     else "" for section in sections]])
        form_links = "<br>".join([link for link in [section.get_form_links() if self.code in section.get_elements()
                                                    else "" for section in sections]])
        return "<br>Sections:<br>{0}<br>Forms:<br>{1}".format(section_links, form_links)

    def get_admin_url(self):
        return reverse('admin:{0}_{1}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk,))

    def get_admin_link(self):
        return '<a href="{0}" target="_blank">{1}</a>'.format(self.get_admin_url(), self)

    def get_val_description(self):
        validation_rules_description = "The %s CDE:" % self.code

        if self.datatype == "string":
            validation_rules_description += "<br>Is a character string"
            if self.max_length is not None:
                validation_rules_description += "<br>With a limit of %d characters" % self.max_length
            if self.pattern is not None and self.pattern != "":
                validation_rules_description += "<br>That must match the pattern \"%s\"" % self.pattern

        elif self.datatype == "integer" or self.datatype == "float":
            validation_rules_description += "<br>Is a number"
            if self.max_value is not None:
                validation_rules_description += "<br>With a maximum value of %d" % self.max_value
            if self.min_value is not None:
                validation_rules_description += "<br>With a minimum value of %d" % self.min_value

        elif self.is_required is True:
            validation_rules_description += "<br>Must be filled"

        else:
            validation_rules_description += "<br>Has no validation requirements"

        return validation_rules_description


def validate_abnormality_condition(abnormality_condition, datatype):
    abnormality_condition_lines = list(
        filter(None, map(lambda rule: rule.strip(), abnormality_condition.split("\r\n")))
    )
    return all(validate_rule(rule, datatype) for rule in abnormality_condition_lines)


def validate_rule(rule, datatype):
    # numeric rules
    eq = Literal("==")
    le = Literal("<=")
    ge = Literal(">=")
    lo = Literal("<")
    g = Literal(">")
    quote = "\""

    parsing_formats = None
    if datatype in ["range", "string"]:
        string_equality_expression = 'x' + eq + Word(quote + alphanums + '_' + '-' + quote)
        string_list_expression = 'x' + \
            Literal('in') + "[" + (delimitedList(quote + Word(alphanums + '_' + '-') + quote, ",")) + "]"
        parsing_formats = string_equality_expression | string_list_expression

    if datatype in ["integer", "float"]:
        number = Optional('-') + Word(nums) + Optional('.' + Word(nums))
        numeric_expression = 'x' + (eq | le | ge | lo | g) + number
        numeric_list_expression = 'x' + Literal('in') + "[" + (delimitedList(number, ',')) + "]"
        parsing_formats = numeric_expression | numeric_list_expression

    # If we can not find any matching rule (should only happen when a designer edit the CDE).
    if parsing_formats is None:
        raise ValidationError(
            f"This CDE datatype \"{datatype}\" is not supported by the abnormality field.")

    parsing_formats = LineStart() + parsing_formats + LineEnd()
    return list(parsing_formats.scanString(rule))


class CdePolicy(models.Model):
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    cde = models.ForeignKey(CommonDataElement, on_delete=models.CASCADE)
    groups_allowed = models.ManyToManyField(Group, blank=True)
    condition = models.TextField(blank=True)

    def is_allowed(self, user_groups, patient_model=None, is_superuser=False):
        if is_superuser:
            return True
        for ug in user_groups:
            if ug in self.groups_allowed.all():
                if patient_model:
                    return self.evaluate_condition(patient_model)
                else:
                    return True

    class Meta:
        verbose_name = "CDE Policy"
        verbose_name_plural = "CDE Policies"

    def evaluate_condition(self, patient_model):
        if not self.condition:
            return True
        # need to think about safety here

        context = {"patient": patient_model}
        result = eval(self.condition, {"__builtins__": None}, context)
        return result


class RegistryFormManager(models.Manager):

    def get_by_natural_key(self, registry_code, name):
        return self.get(registry__code=registry_code, name=name)

    def get_by_registry(self, registry):
        return self.model.objects.filter(registry__id__in=registry)


class RegistryForm(models.Model):
    """
    A representation of a form ( a bunch of sections)
    """
    objects = RegistryFormManager()

    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    name = models.CharField(max_length=80,
                            help_text="Internal name used by system: Alphanumeric, no spaces")
    display_name = models.CharField(max_length=200,
                                    blank=True,
                                    null=True,
                                    help_text="Form Name displayed to users")
    header = models.TextField(blank=True)
    questionnaire_display_name = models.CharField(max_length=80, blank=True)
    sections = models.TextField(help_text="Comma-separated list of sections")
    is_questionnaire = models.BooleanField(
        default=False, help_text="Check if this form is questionnaire form for it's registry")
    is_questionnaire_login = models.BooleanField(
        default=False,
        help_text="If the form is a questionnaire, is it accessible only by logged in users?",
        verbose_name="Questionnaire Login Required")
    position = models.PositiveIntegerField(default=0)
    questionnaire_questions = models.TextField(
        blank=True, help_text="Comma-separated list of sectioncode.cdecodes for questionnnaire")
    complete_form_cdes = models.ManyToManyField(CommonDataElement, blank=True)
    groups_allowed = models.ManyToManyField(Group, blank=True)
    applicability_condition = models.TextField(blank=True,
                                               null=True,
                                               help_text="E.g. patient.deceased == True")

    def natural_key(self):
        return (self.registry.code, self.name)

    def validate_unique(self, exclude=None):
        models.Model.validate_unique(self, exclude)
        if not ('registry__code' in exclude or 'name' in exclude):
            if (RegistryForm.objects.filter(registry__code=self.registry.code, name=self.name)
                                    .exclude(pk=self.pk)
                                    .exists()):
                raise ValidationError(
                    "RegistryForm with registry.code '%s' and name '%s' already exists" %
                    (self.registry.code, self.name))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def open(self):
        return self.groups_allowed.count() == 0

    @property
    def restricted(self):
        return not self.open

    @property
    def login_required(self):
        return self.is_questionnaire_login

    @property
    def questionnaire_name(self):
        from rdrf.helpers.utils import de_camelcase
        if self.questionnaire_display_name:
            return self.questionnaire_display_name
        else:
            return de_camelcase(self.name)

    def __str__(self):
        return self.name
        # return "%s %s Form comprising %s" % (self.registry, self.name, self.sections)

    def get_sections(self):
        return list(map(str.strip, self.sections.split(",")))

    @property
    def questionnaire_list(self):
        """
        returns a list of sectioncode.cde_code strings
        E.g. [ "sectionA.cdecode23", "sectionB.code100" , ...]
        """
        return list(filter(bool, map(str.strip, self.questionnaire_questions.split(","))))

    @property
    def section_models(self):
        models = []
        for section_code in self.get_sections():
            try:
                section_model = Section.objects.get(code=section_code)
                models.append(section_model)
            except Section.DoesNotExist:
                pass
        return models

    def get_section_model(self, code):
        for section_model in self.section_models:
            if section_model.code == code:
                return section_model
        raise KeyError("section %s not found in this form" % code)

    def in_questionnaire(self, section_code, cde_code):
        questionnaire_code = "%s.%s" % (section_code, cde_code)
        return questionnaire_code in self.questionnaire_list

    @property
    def has_progress_indicator(self):
        return True if len(self.complete_form_cdes.values_list()) > 0 else False

    def link(self, patient_model):
        from rdrf.helpers.utils import FormLink
        return FormLink(patient_model.pk, self.registry, self).url

    @property
    def nice_name(self):
        from rdrf.helpers.utils import de_camelcase
        try:
            return self.display_name if self.display_name else de_camelcase(self.name)
        except BaseException:
            return self.name

    @property
    def has_progress(self):
        # does this form define form progress ( completion) cdes?
        return self.complete_form_cdes.count() > 0

    def get_link(self, patient_model, context_model=None):
        if context_model is None:
            return reverse(
                'registry_form',
                args=(
                    self.registry.code,
                    self.id,
                    patient_model.id))
        else:
            return reverse(
                'registry_form',
                args=(
                    self.registry.code,
                    self.id,
                    patient_model.id,
                    context_model.id))

    def _check_completion_cdes(self):
        completion_cdes = set([cde.code for cde in self.complete_form_cdes.all()])
        current_cdes = []
        for section_model in self.section_models:
            for cde_model in section_model.cde_models:
                current_cdes.append(cde_model.code)

        current_cdes = set(current_cdes)
        extra = completion_cdes - current_cdes

        if len(extra) > 0:
            msg = ",".join(extra)
            raise ValidationError("Some completion cdes don't exist on the form: %s" % msg)

    def clean(self):
        if " " in self.name:
            msg = "Form name contains spaces which causes problems: Use CamelCase to make GUI display the name as" + \
                "Camel Case, instead."
            raise ValidationError({'name': msg})

        if self.pk:
            self._check_completion_cdes()

        self._check_sections()

    def _check_sections(self):
        for section_code in self.get_sections():
            try:
                Section.objects.get(code=section_code)
            except Section.DoesNotExist:
                raise ValidationError("Section %s does not exist!" % section_code)

    def applicable_to(self, patient):
        # 2 levels of restriction:
        # by patient type , set up in the registry metadata
        # and further by a dynamic condition
        # thus we can have forms applicable to all carrier patients
        # ( patient_type = carrier) and also
        # deceased patients, say. ( for MTM)
        # the default case is True - ie all forms are applicable to a patient
        from rdrf.helpers.utils import applicable_forms

        if patient is None:
            return False

        if not patient.in_registry(self.registry.code):
            return False
        else:
            allowed_forms = [f.name for f in applicable_forms(self.registry, patient)]
            if self.name not in allowed_forms:
                return False

        # In allowed list for patient type, but is there a patient condition also?

        if not self.applicability_condition:
            return True

        evaluation_context = {"patient": patient}

        try:
            is_applicable = eval(self.applicability_condition,
                                 {"__builtins__": None},
                                 evaluation_context)
        except BaseException:
            # allows us to filter out forms for patients
            # which are not related with the assumed structure
            # in the supplied condition
            return False

        return is_applicable

    def sections_presence(self):
        # returns a dict showing if sections are present or not
        codes = self.get_sections()
        return {code: Section.objects.filter(code=code).exists() for code in codes}

    def existing_section_models(self):
        codes = self.get_sections()
        exisiting_sections = Section.objects.filter(code__in=codes)
        # returns a dict of sections, with False value if a code is not existing
        cdes = dict(self.sections_presence(), **{cde.code: cde for cde in exisiting_sections})
        return cdes

    def get_admin_url(self):
        return reverse('admin:{0}_{1}_change'.format(self._meta.app_label, self._meta.model_name), args=(self.pk,))

    def get_admin_link(self):
        return '<a href="{0}" target="_blank">{1}</a> of Registry:{2}'.format(self.get_admin_url(), self, self.registry)

    def get_section_links(self):
        existing = self.existing_section_models()
        return ", ".join([existing[code].get_admin_link() if existing[code]
                          else "<span class='alert-danger'>{0}</span>".format(code) for code in existing])


class Wizard(models.Model):
    registry = models.CharField(max_length=50)
    forms = models.TextField(help_text="A comma-separated list of forms")
    # idea
    # rules for "decision tree"
    # These could be as simple as the following:
    # A wizard is a way of coordinating the asking of questions and evaluating
    # answers -

    #  E.g. in pseudo-code ( we either present a gui to create rules like this
    # or write an interpreter
    #  present form1.
    #  if form1.section1.cde2 == 3 and section2.cde >6  then present form3
    #  if form1.section2.cde2 == 4 then present form5
    #  else present form6
    #
    rules = models.TextField(help_text="Rules")


class QuestionnaireResponse(models.Model):
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    date_submitted = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    patient_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="The id of the patient created from this response, if any")

    def __str__(self):
        return "%s (%s)" % (self.registry, self.processed)

    @property
    def name(self):
        return self._get_patient_field(
            "CDEPatientGivenNames") + " " + self._get_patient_field("CDEPatientFamilyName")

    @property
    def date_of_birth(self):
        # time was being included from questionnaire for some data: e.g. '1918-08-01T00:00:00'
        dob_string = self._get_patient_field("CDEPatientDateOfBirth")
        if not dob_string:
            return ""

        try:
            return parse_iso_datetime(dob_string).date()
        except ValueError:
            return ""

    def _get_patient_field(self, patient_field):
        from rdrf.db.dynamic_data import DynamicDataWrapper
        wrapper = DynamicDataWrapper(self)

        if not self.has_mongo_data:
            raise ObjectDoesNotExist

        questionnaire_form_name = RegistryForm.objects.get(
            registry=self.registry, is_questionnaire=True).name

        value = wrapper.get_nested_cde(
            self.registry.code,
            questionnaire_form_name,
            "PatientData",
            patient_field)

        if value is None:
            return ""

        return value

    @property
    def has_mongo_data(self):
        from rdrf.db.dynamic_data import DynamicDataWrapper
        wrapper = DynamicDataWrapper(self)
        return wrapper.has_data(self.registry.code)

    @property
    def data(self):
        # return the filled in questionnaire data
        from rdrf.db.dynamic_data import DynamicDataWrapper
        wrapper = DynamicDataWrapper(self)
        return wrapper.load_dynamic_data(self.registry.code, "cdes", flattened=False)


def appears_in(cde, registry, registry_form, section):
    if section.code not in registry_form.get_sections():
        return False
    elif registry_form.name not in [f.name for f in RegistryForm.objects.filter(registry=registry)]:
        return False
    else:
        return cde.code in section.get_elements()


class MissingData(object):
    pass


class Notification(models.Model):
    from_username = models.CharField(max_length=80)
    to_username = models.CharField(max_length=80)
    created = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    link = models.CharField(max_length=100, default="")
    seen = models.BooleanField(default=False)


class ConsentSectionManager(models.Manager):

    def get_by_natural_key(self, registry_code, code):
        return self.get(registry__code=registry_code, code=code)


class ConsentSection(models.Model):
    objects = ConsentSectionManager()

    code = models.CharField(max_length=20)
    section_label = models.CharField(max_length=100)
    registry = models.ForeignKey(Registry, related_name="consent_sections", on_delete=models.CASCADE)
    information_link = models.CharField(max_length=100, blank=True, null=True)
    information_text = models.TextField(blank=True, null=True)
    # eg "patient.age > 6 and patient.age" < 10
    applicability_condition = models.TextField(blank=True)
    validation_rule = models.TextField(blank=True)

    def natural_key(self):
        return (self.registry.code, self.code)

    def validate_unique(self, exclude=None):
        models.Model.validate_unique(self, exclude)
        if not ('registry__code' in exclude or 'code' in exclude):
            if (ConsentSection.objects.filter(registry__code=self.registry.code, code=self.code)
                                      .exclude(pk=self.pk)
                                      .exists()):
                raise ValidationError(
                    "ConsentSection with registry.code '%s' and code '%s' already exists" %
                    (self.registry.code, self.code))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def applicable_to(self, patient):
        if patient is None:
            return True

        if not patient.in_registry(self.registry.code):
            return False
        else:
            # if no restriction return True
            if not self.applicability_condition:
                return True

            from registry.patients.models import ParentGuardian
            self_patient = False
            try:
                ParentGuardian.objects.get(self_patient=patient)
                self_patient = True
            except ParentGuardian.DoesNotExist:
                pass

            function_context = {"patient": patient, "self_patient": self_patient}

            is_applicable = eval(
                self.applicability_condition, {"__builtins__": None}, function_context)

            return is_applicable

    def is_valid(self, answer_dict):
        """
        does the supplied question_code --> answer map
        satisfy the validation rule for this section
        :param answer_dict: map of question codes to bool
        :return: True or False depending on validation rule
        """
        if not self.validation_rule:
            return True

        function_context = {}

        for consent_question_code in answer_dict:
            answer = answer_dict[consent_question_code]
            function_context[consent_question_code] = answer

        # codes not in dict are set to false ..

        for question_model in self.questions.all():
            if question_model.code not in answer_dict:
                function_context[question_model.code] = False

        try:

            result = eval(self.validation_rule, {"__builtins__": None}, function_context)
            if result not in [True, False, None]:
                return False

            return result
        except Exception as ex:
            logger.error(
                "Error evaluating consent section %s rule %s context %s error %s" %
                (self.code, self.validation_rule, function_context, ex))

            return False

    def __str__(self):
        return "Consent Section %s" % self.section_label

    @property
    def link(self):
        if self.information_link:
            return reverse('documents', args=(self.information_link,))
        else:
            return ""

    @property
    def form_info(self):
        from django.forms import BooleanField
        info = {}
        info["section_label"] = "%s %s" % (self.registry.code, self.section_label)
        info["information_link"] = self.information_link
        consent_fields = []
        for consent_question_model in self.questions.all().order_by("position"):
            consent_fields.append(BooleanField(label=consent_question_model.question_label))
        info["consent_fields"] = consent_fields
        return info


class ConsentQuestionManager(models.Manager):

    def get_by_natural_key(self, section_code, code):
        return self.get(section__code=section_code, code=code)


class ConsentQuestion(models.Model):
    objects = ConsentQuestionManager()

    code = models.CharField(max_length=20)
    position = models.IntegerField(blank=True, null=True)
    section = models.ForeignKey(ConsentSection, related_name="questions", on_delete=models.CASCADE)
    question_label = models.TextField()
    instructions = models.TextField(blank=True)
    questionnaire_label = models.TextField(blank=True)

    class Meta:
        unique_together = ('section', 'code')

    def natural_key(self):
        return (self.section.code, self.code)

    def create_field(self):
        from django.forms import BooleanField
        return BooleanField(
            label=self.question_label,
            required=False,
            help_text=self.instructions)

    @property
    def field_key(self):
        registry_model = self.section.registry
        consent_section_model = self.section
        return "customconsent_%s_%s_%s" % (registry_model.pk, consent_section_model.pk, self.pk)

    def label(self, on_questionnaire=False):
        if on_questionnaire and self.questionnaire_label:
            return self.questionnaire_label
        else:
            return self.question_label

    def __str__(self):
        return "%s" % self.question_label


class ConsentRule(models.Model):
    # restrictions on what a user can do with a patient
    # based on patient consent
    # e.g. restrict clinical users from seeing patients' data
    # if the patient has not given explicit consent
    CAPABILITIES = (('see_patient', 'See Patient'),)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    user_group = models.ForeignKey(Group, on_delete=models.CASCADE)
    capability = models.CharField(max_length=50, choices=CAPABILITIES)
    consent_question = models.ForeignKey(ConsentQuestion, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)


class DemographicFields(models.Model):
    FIELD_CHOICES = []

    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    field = models.CharField(max_length=50, choices=FIELD_CHOICES)
    readonly = models.NullBooleanField(null=True, blank=True)
    hidden = models.NullBooleanField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Demographic Fields"


class EmailTemplate(models.Model):
    language = models.CharField(max_length=2, choices=settings.ALL_LANGUAGES)
    description = models.TextField()
    subject = models.CharField(max_length=50)
    body = models.TextField()

    def __str__(self):
        return "%s (%s)" % (self.description, dict(settings.LANGUAGES)[self.language])


class EmailNotification(models.Model):
    EMAIL_NOTIFICATIONS = (
        (EventType.ACCOUNT_LOCKED, "Account Locked"),
        (EventType.OTHER_CLINICIAN, "Other Clinician"),
        (EventType.NEW_PATIENT, "New Patient Registered"),
        (EventType.NEW_PATIENT_PARENT, "New Patient Registered (Parent)"),
        (EventType.ACCOUNT_VERIFIED, "Account Verified"),
        (EventType.PASSWORD_EXPIRY_WARNING, "Password Expiry Warning"),
        (EventType.REMINDER, "Reminder"),
        (EventType.CLINICIAN_SIGNUP_REQUEST, "Clinician Signup Request"),
        (EventType.CLINICIAN_ACTIVATION, "Clinician Activation"),
        (EventType.CLINICIAN_SELECTED, "Clinician Selected"),
        (EventType.PARTICIPANT_CLINICIAN_NOTIFICATION, "Participant Clinician Notification"),
        (EventType.SURVEY_REQUEST, "Survey Request"),
    )

    description = models.CharField(max_length=100, choices=EMAIL_NOTIFICATIONS)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    email_from = models.EmailField(default='No Reply <no-reply@mg.ccgapps.com.au>')
    recipient = models.CharField(max_length=100, null=True, blank=True)
    group_recipient = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    email_templates = models.ManyToManyField(EmailTemplate)
    disabled = models.BooleanField(null=False, blank=False, default=False)

    def __str__(self):
        return "%s (%s)" % (self.description, self.registry.code.upper())


class EmailNotificationHistory(models.Model):
    date_stamp = models.DateTimeField(auto_now_add=True)
    language = models.CharField(max_length=10)
    email_notification = models.ForeignKey(EmailNotification, on_delete=models.CASCADE)
    template_data = models.TextField(null=True, blank=True)


class RDRFContextError(Exception):
    pass


class RDRFContext(models.Model):
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    context_form_group = models.ForeignKey("ContextFormGroup",
                                           null=True,
                                           blank=True,
                                           on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    display_name = models.CharField(max_length=80, blank=True, null=True)

    def __str__(self):
        return "%s %s" % (self.display_name, self.created_at)

    def clean(self):
        if not self.display_name:
            raise ValidationError("RDRF Context must have a display name")

    @property
    def context_name(self):
        if self.context_form_group:
            if self.context_form_group.naming_scheme == "C":
                return self._get_name_from_cde()
            else:
                return self.context_form_group.name  # E.G. Assessment or Visit - used for display
        else:
            try:
                return self.registry.metadata["context_name"]
            except KeyError:
                return "Context"

    def _get_name_from_cde(self):
        if not self.context_form_group.naming_cde_to_use:
            return "Follow Up"
        cde_path = self.context_form_group.naming_cde_to_use
        form_name, section_code, cde_code = cde_path.split("/")
        cde_value = self.content_object.get_form_value(self.registry.code,
                                                       form_name,
                                                       section_code,
                                                       context_id=self.pk)
        return cde_value


class ContextFormGroup(models.Model):
    CONTEXT_TYPES = [("F", "Fixed"), ("M", "Multiple")]
    NAMING_SCHEMES = [("D", "Automatic - Date"),
                      ("N", "Automatic - Number"),
                      ("M", "Manual - Free Text"),
                      ("C", "CDE - Nominate CDE to use")]
    ORDERING_TYPES = [("C", "Creation Time"),
                      ("N", "Name")]

    registry = models.ForeignKey(Registry,
                                 related_name="context_form_groups",
                                 on_delete=models.CASCADE)
    context_type = models.CharField(max_length=1, default="F", choices=CONTEXT_TYPES)
    name = models.CharField(max_length=80)
    naming_scheme = models.CharField(max_length=1, default="D", choices=NAMING_SCHEMES)
    is_default = models.BooleanField(default=False)
    naming_cde_to_use = models.CharField(max_length=80, blank=True, null=True)
    ordering = models.CharField(max_length=1, default="C", choices=ORDERING_TYPES)

    @property
    def forms(self):
        def sort_func(form):
            return form.position

        return sorted([item.registry_form for item in self.items.all()],
                      key=sort_func)

    def __str__(self):
        return self.name

    @property
    def direct_name(self):
        """
        If there is only one form in the group , show _its_ name
        """
        if not self.supports_direct_linking:
            return self.name

        return self.form_models[0].nice_name

    @property
    def supports_direct_linking(self):
        return len(self.form_models) == 1

    @property
    def is_ordered_by_name(self):
        return self.ordering == "N"

    @property
    def is_ordered_by_creation(self):
        return self.ordering == "C"

    def get_default_name(self, patient_model, context_model=None):
        if self.naming_scheme == "M":
            return "Modules"
        elif self.naming_scheme == "D" and context_model is not None:
            d = context_model.created_at
            s = d.strftime("%d-%b-%Y")
            t = d.strftime("%I:%M:%S %p")
            return "%s/%s %s" % (self.name, s, t)
        elif self.naming_scheme == "N":
            registry_model = self.registry
            patient_content_type = ContentType.objects.get(model='patient')
            existing_contexts = [
                c for c in RDRFContext.objects.filter(
                    object_id=patient_model.pk,
                    content_type=patient_content_type,
                    registry=registry_model,
                    context_form_group=self)]
            next_number = len(existing_contexts) + 1
            return "%s/%s" % (self.name, next_number)
        elif self.naming_scheme == "C":
            return "Unused"  # user will see value from cde when context is created
        else:
            return "Modules"

    def get_value_from_cde(self, patient_model, context_model):
        form_name, section_code, cde_code = self.naming_cde_to_use.split("/")
        try:
            cde_value = patient_model.get_form_value(self.registry.code,
                                                     form_name,
                                                     section_code,
                                                     cde_code,
                                                     context_id=context_model.pk)

            cde_model = CommonDataElement.objects.get(code=cde_code)
            return cde_model.get_value(cde_value)
        except KeyError:
            # value not filled out yet
            return None

    def get_name_from_cde(self, patient_model, context_model):
        if not self.naming_cde_to_use:
            return self.get_default_name(patient_model, context_model)
        form_name, section_code, cde_code = self.naming_cde_to_use.split("/")
        try:
            cde_value = patient_model.get_form_value(self.registry.code,
                                                     form_name,
                                                     section_code,
                                                     cde_code,
                                                     context_id=context_model.pk)

            cde_model = CommonDataElement.objects.get(code=cde_code)
            # This does not actually do type conversion for dates -
            # it just looks up range display codes.
            display_value = cde_model.get_display_value(cde_value)
            if isinstance(display_value, datetime.date):
                display_value = format_date(display_value)
            return display_value
        except KeyError:
            # value not filled out yet
            return "NOT SET"

    def get_ordering_value(self, patient_model, context_model):
        from rdrf.helpers.utils import MinType
        bottom = MinType()
        if context_model.display_name:
            display_name = context_model.display_name
        else:
            display_name = "Not set"

        if self.is_ordered_by_name:
            if self.naming_scheme == "C":
                try:
                    value = self.get_value_from_cde(patient_model, context_model)

                    if value is None:
                        return bottom
                    else:
                        return value
                except BaseException:
                    return bottom
            return display_name

        if self.is_ordered_by_creation:
            return context_model.created_at

        return bottom

    @property
    def naming_info(self):
        if self.naming_scheme == "M":
            return "Display name will default to 'Modules' if left blank"
        elif self.naming_scheme == "N":
            return "Display name will default to <Context Type Name>/<Sequence Number>"
        elif self.naming_scheme == "D":
            return "Display name will default to <Context Type Name>/<created_at date>"
        elif self.naming_scheme == "C":
            return "Display name will be equal to the value of a nominated CDE"
        else:
            return "Display name will default to 'Modules' if left blank"

    def clean(self):
        defaults = ContextFormGroup.objects.filter(registry=self.registry,
                                                   is_default=True).exclude(pk=self.pk)
        num_defaults = defaults.count()

        if num_defaults > 0 and self.is_default:
            raise ValidationError("Only one Context Form Group can be the default")
        if num_defaults == 0 and not self.is_default:
            raise ValidationError("One Context Form Group must be chosen as the default")

        if self.naming_scheme == "C" and self._valid_naming_cde_to_use(self.naming_cde_to_use) is None:
            raise ValidationError(
                "Invalid naming cde: Should be form name/section code/cde code where all codes must exist")

        if self.context_type == 'M' and self.items.all().count() > 1:
            raise ValidationError("Context Form Group of type Multiple cannot have more than one form")

    def _valid_naming_cde_to_use(self, naming_cde_to_use):
        validation_message = "Invalid naming cde: Should be form name/section code/cde code where all codes must exist"
        if naming_cde_to_use:
            try:
                naming_cde_expression = naming_cde_to_use.split("/")
                form_name, section_code, cde_code = naming_cde_expression
            except ValueError:
                raise ValidationError(validation_message)

            try:
                form_model = RegistryForm.objects.get(registry=self.registry,
                                                      name=form_name)
            except RegistryForm.DoesNotExist:
                raise ValidationError(validation_message)

            section_model = self._get_section_model(section_code, form_model)
            if section_model is None:
                raise ValidationError(validation_message)

            cde_model = self._get_cde_model(cde_code, section_model)
            if cde_model is None:
                raise ValidationError(validation_message)

            return form_name, section_code, cde_code
        return None

    def _get_section_model(self, section_code, form_model):
        for section_model in form_model.section_models:
            if section_model.code == section_code:
                return section_model

    def _get_cde_model(self, cde_code, section_model):
        for cde_model in section_model.cde_models:
            if cde_model.code == cde_code:
                return cde_model

    def patient_can_add(self, patient_model):
        """
        can this patient add a context of my type?
        """
        if self.context_type == "M":
            return True
        else:
            # fixed - is there one already?
            patient_content_type = ContentType.objects.get(model='patient')
            return RDRFContext.objects.filter(registry=self.registry,
                                              content_type=patient_content_type,
                                              object_id=patient_model.id,
                                              context_form_group=self).count() == 0

    def get_add_action(self, patient_model):
        if self.patient_can_add(patient_model):
            num_forms = len(self.form_models)
            action_title = ""
            # Direct link to form if num forms is 1 ( handler redirects transparently)
            if not self.registry.has_feature("proms_adding_disabled"):
                from rdrf.helpers.utils import de_camelcase as dc
                action_title = "Add %s" % dc(
                    self.form_models[0].name) if num_forms == 1 else "Add %s" % dc(self.name)

            if not self.supports_direct_linking:
                # We can't go directly to the form - so we first land on the add context view, which on save
                # creates the context with links to the forms provided in that context
                # after save
                action_link = reverse("context_add", args=(self.registry.code,
                                                           str(patient_model.pk),
                                                           str(self.pk)))

            else:
                form_model = self.form_models[0]
                # provide a link to the create view for a clinical form
                # url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/add/?$",

                action_link = reverse("form_add", args=(self.registry.code,
                                                        form_model.pk,
                                                        patient_model.pk,
                                                        'add'))

            return action_link, action_title
        else:
            return None

    @property
    def form_models(self):
        return sorted([item.registry_form for item in self.items.all()],
                      key=lambda f: f.position)


class ContextFormGroupItem(models.Model):
    context_form_group = models.ForeignKey(ContextFormGroup,
                                           related_name="items",
                                           on_delete=models.CASCADE)
    registry_form = models.ForeignKey(RegistryForm, on_delete=models.CASCADE)


class ClinicalDataQuerySet(models.QuerySet):
    def collection(self, registry_code, collection):
        qs = self.filter(registry_code=registry_code, collection=collection)
        return qs.order_by("pk")

    def find(self, obj=None, context_id=None, **query):
        q = {}
        if obj is not None:
            q["django_id"] = obj.id
            q["django_model"] = obj.__class__.__name__
        if context_id is not None:
            q["context_id"] = context_id
        for attr, value in query.items():
            q["data__" + attr] = value
        return self.filter(**q)

    def data(self):
        return self.values_list("data", flat=True)


class ClinicalData(models.Model):
    """
    MongoDB collections in Django.
    """
    COLLECTIONS = (
        ("cdes", "cdes"),
        ("history", "history"),
        ("progress", "progress"),
        ("registry_specific_patient_data", "registry_specific_patient_data"),
    )

    registry_code = models.CharField(max_length=10, db_index=True)
    collection = models.CharField(max_length=50, db_index=True, choices=COLLECTIONS)
    data = DataField()
    django_id = models.IntegerField(db_index=True, default=0)
    django_model = models.CharField(max_length=80, db_index=True, default="Patient")
    context_id = models.IntegerField(db_index=True, blank=True, null=True)
    active = models.BooleanField(
        default=True, help_text="Indicate whether an entity is active or not")
    metadata = models.TextField(blank=True, null=True)

    objects = ClinicalDataQuerySet.as_manager()

    @classmethod
    def create(cls, obj, **kwargs):
        self = cls(**kwargs)
        self.data["django_model"] = obj.__class__.__name__
        self.data["django_id"] = obj.id
        self.django_id = obj.id
        self.django_model = obj.__class__.__name__
        if "context_id" in kwargs:
            self.context_id = kwargs["context_id"]
        return self

    def __str__(self):
        return json.dumps(model_to_dict(self), indent=2)

    def get_metadata_locking(self, form_name):
        # the clinical metadata are only stored with the cdes collection
        if self.collection != "cdes":
            raise Exception("coding error: metadata are stored in the cdes collection")

        if self.metadata:
            metadata = json.loads(self.metadata)
            if form_name in metadata["forms"].keys():
                return metadata["forms"][form_name]['locking']
        return False

    def switch_metadata_locking(self, form_name):
        # the clinical metadata are only stored with the cdes collection
        if self.collection != "cdes":
            raise Exception("coding error: metadata are stored in the cdes collection")

        # Set default value when no metadata exist yet.
        metadata = {"forms": {form_name: {'locking': True}}}

        if self.metadata:
            metadata = json.loads(self.metadata)
            if form_name in metadata["forms"].keys():
                metadata["forms"][form_name]['locking'] = not metadata["forms"][form_name]['locking']
            else:
                # Some metadata existed for other forms, but not for this form_name.
                metadata["forms"] = {form_name: {'locking': True}}

        self.metadata = json.dumps(metadata)
        self.save()

    def cde_val(self, form_name, section_code, cde_code):
        forms = self.data.get("forms", [])
        form_map = {f.get("name"): f for f in forms}
        sections = form_map.get(form_name, {}).get("sections", [])
        section_map = {s.get("code"): s for s in sections}
        cdes = section_map.get(section_code, {}).get("cdes", [])
        cde_map = {c.get("code"): c for c in cdes}
        return cde_map.get(cde_code, {}).get("value")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        self._clean_registry_code()
        self._clean_data()

    def _clean_registry_code(self):
        if not Registry.objects.filter(code=self.registry_code).exists():
            raise ValidationError(
                {"registry_code": "Registry %s does not exist" % self.registry_code})

    modjgo_schema = None
    #  need tp fix this path rdrf/db/schemas/modjgo.yaml
    modjgo_schema_file = os.path.join(os.path.dirname(__file__), "schemas/modjgo.yaml")

    def validate(self, collection, data):
        return

        # to do fithis
        if not self.modjgo_schema:
            try:
                with open(self.modjgo_schema_file) as f:
                    self.modjgo_schema = yaml.load(f.read())
            except BaseException:
                logger.exception("Error reading %s" % self.modjgo_schema_file)

        if self.modjgo_schema:
            jsonschema.validate({collection: data}, self.modjgo_schema)

    lax_validation = True

    def _clean_data(self):
        try:
            self.validate(self.collection, self.data)
        except jsonschema.ValidationError as e:
            if self.lax_validation:
                logger.warning("Failed to validate: %s" % e)
            else:
                raise ValidationError({"data": e})


def file_upload_to(instance, filename):
    return "/".join(filter(bool, [
        instance.registry_code,
        instance.section_code or "_",
        instance.cde_code, filename]))


class CDEFile(models.Model):
    """
    A file record which is referenced by id within the patient's
    dynamic data dictionary.

    The form and section fields are optional for files belonging to
    registry-specific fields.

    See filestorage.py for usage of this model.
    """
    registry_code = models.CharField(max_length=10)
    form_name = models.CharField(max_length=80, blank=True)
    section_code = models.CharField(max_length=100, blank=True)
    cde_code = models.CharField(max_length=30, blank=True)
    item = models.FileField(upload_to=file_upload_to, max_length=300)
    filename = models.CharField(max_length=255)

    def __str__(self):
        return self.item.name


@receiver(pre_delete, sender=CDEFile)
def fileuploaditem_delete(sender, instance, **kwargs):
    instance.item.delete(False)


class FileStorage(models.Model):
    """
    This model is used only when the database file storage backend is
    enabled. These exact columns are required by the backend code.
    """
    name = models.CharField(primary_key=True, max_length=255)
    data = models.BinaryField()
    size = models.IntegerField(default=0)


class CustomAction(models.Model):
    """
    Represents actions with a button in the GUI - can be run
    data associated with the action is parsed and the action executed
    """
    ACTION_TYPES = (("PR", "Patient Report"),
                    ("SR", "Patient Status Report"),
                    ("DE", "Deidentified Data Extract"))

    SCOPES = (("U", "Universal"),
              ("P", "Patient"))

    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    groups_allowed = models.ManyToManyField(Group, blank=True)
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=80, blank=True, null=True)
    action_type = models.CharField(max_length=2, choices=ACTION_TYPES)
    include_all = models.BooleanField(default=False, help_text="For Patient Status Report: Select this to include all "
                                                               "data for the patients.<br>If this is not selected, "
                                                               "then the Data field below should be filled in with "
                                                               "the required report spec.<br>If this is selected, "
                                                               "Data field should contain {}."
                                      )
    data = models.TextField(null=True)
    scope = models.CharField(max_length=1, choices=SCOPES)  # controls where action appears
    runtime_spec = models.TextField(blank=True, null=True)  # json field to describe how the action is run

    def _get_spec(self):
        import json
        if not self.runtime_spec:
            return {}
        try:
            return json.loads(self.runtime_spec)
        except ValueError as verr:
            logger.error("can't load runtime spec json data for custom action: %s" % verr)
            raise

    @property
    def action_data(self):
        if not self.data:
            return {}
        try:
            return json.loads(self.data)
        except ValueError as verr:
            logger.error(f"can't load data as json: custom action {self.name}  {verr}")
            raise

    @property
    def asynchronous(self):
        spec = self._get_spec()
        return "async" in spec and spec["async"]

    @property
    def requires_input(self):
        spec = self._get_spec()
        try:
            filter_spec = spec["filter_spec"]
            inputs = filter_spec["inputs"]
            return len(inputs) > 0
        except KeyError:
            return False

    @property
    def spec(self):
        return self._get_spec()

    @property
    def inputs(self):
        spec = self._get_spec()
        if "filter_spec" in spec:
            filter_spec = spec["filter_spec"]
            if "inputs" in filter_spec:
                return spec["filter_spec"]["inputs"]
        return []

    @property
    def input_form_class(self):
        if self.requires_input:
            return self._generate_input_form_class(self.inputs)
        else:
            return None

    def _generate_input_form_class(self, inputs):
        import django.forms as forms
        from collections import OrderedDict
        base_fields = OrderedDict()

        def create_field(input_spec):
            field_type = input_spec["field_type"]
            kwargs = {}
            widget = None
            if field_type == "date":
                from django import forms
                from rdrf.forms.dynamic.fields import IsoDateField
                klass = IsoDateField
                widget = forms.DateInput(attrs={'class': 'datepicker'},
                                         format='%dd-%mm-%YY')
                kwargs["widget"] = widget
                kwargs["input_formats"] = ["%d-%m-%Y"]
            else:
                raise NotImplementedError("don't support non-date fields yet")

            return klass(**kwargs)

        form_class = forms.BaseForm
        for input_spec in inputs:
            django_field = create_field(input_spec)
            field_name = input_spec["name"]
            base_fields[field_name] = django_field

        # we need to add a hidden field with the custom action execution id
        # so we can track the progress of the execution when posted
        base_fields["cae"] = forms.IntegerField(widget=forms.HiddenInput())

        form_dict = {"base_fields": base_fields}
        form_class = type("CustomActionInputForm", (forms.BaseForm,), form_dict)
        return form_class

    def run_async(self, user, patient_model, input_data):
        if patient_model is None:
            patient_id = 0
        else:
            patient_id = patient_model.id
        from rdrf.services.tasks import run_custom_action
        async_tuple = run_custom_action.delay(self.id,
                                              user.id,
                                              patient_id,
                                              input_data),

        task_id = async_tuple[0].task_id

        return task_id

    def execute(self, user, patient_model=None, input_data=None, rt_spec=None):
        """
        This should return a HttpResponse of some sort
        """
        if self.scope == "P":
            if not self.check_security(user, patient_model):
                raise PermissionDenied
        elif self.scope == "U":
            if not user.is_superuser and not user.in_registry(self.registry):
                raise PermissionDenied

        if self.action_type == "PR":
            from rdrf.services.io.actions import patient_report
            result = patient_report.execute(self.registry,
                                            self.name,
                                            self.data,
                                            user,
                                            patient_model,
                                            run_async=self.asynchronous,
                                            runtime_spec=rt_spec)

            logger.info("CUSTOMACTION %s %s by user %s on patient %s" % (self.registry.code,
                                                                         self.name,
                                                                         user.username,
                                                                         patient_model.pk))
            return result
        elif self.action_type == "SR":
            from rdrf.services.io.actions import patient_status_report
            logger.info("CUSTOMACTION SR %s %s" % (self.registry.code,
                                                   user.username))
            return patient_status_report.execute(self,
                                                 self.registry,
                                                 self.name,
                                                 self.data,
                                                 user,
                                                 input_data,
                                                 run_async=self.asynchronous)
        elif self.action_type == "DE":
            from rdrf.services.io.actions import deidentified_data_extract
            logger.info("CUSTOMACTION DE %s %s" % (self.registry.code,
                                                   user.username))
            return deidentified_data_extract.execute(self, user)

        else:
            raise NotImplementedError("Unknown action type: %s" % self.action_type)

    @property
    def text(self):
        return self.name

    @property
    def url(self):
        if self.scope == "U":
            return reverse("custom_action", args=(self.pk, 0))
        else:
            return ""

    @property
    def menu_link(self):
        link = LinkWrapper(self.url, self.name)
        return link

    def check_security(self, user, patient_model):
        if user.is_superuser:
            return True
        from rdrf.security.security_checks import security_check_user_patient
        try:
            security_check_user_patient(user, patient_model)
        except PermissionDenied:
            return False

        return True


class RegistryYaml(models.Model):
    """
        Represents the definition yaml received from the site system
        used for syncing the proms system with
    """
    definition = models.TextField()
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(auto_now=True)
    registry_version_before = models.CharField(max_length=20, blank=True, null=True)
    registry_version_after = models.CharField(max_length=20, blank=True, null=True)
    import_succeeded = models.BooleanField(default=False)

    def __str__(self):
        return self.code
