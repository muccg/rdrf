from django.db import models
import logging
from django.core.exceptions import ValidationError
from rest_framework.reverse import reverse as rest_reverse
from django.core.urlresolvers import reverse
from positions.fields import PositionField
import string
import json
from rdrf.utils import has_feature
from rdrf.notifications import Notifier, NotificationError
from rdrf.utils import get_full_link
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

logger = logging.getLogger("registry_log")


class InvalidStructureError(Exception):
    pass


class InvalidQuestionnaireError(Exception):
    pass


def new_style_questionnaire(registry):
    for form_model in registry.forms:
        if form_model.questionnaire_questions:
            if len(form_model.questionnaire_list) > 0:
                return True
    return False


class Section(models.Model):

    """
    A group of fields that appear on a form as a unit
    """
    code = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200)
    questionnaire_display_name = models.CharField(max_length=200, blank=True)
    elements = models.TextField()
    allow_multiple = models.BooleanField(
        default=False, help_text="Allow extra items to be added")
    extra = models.IntegerField(
        blank=True, null=True, help_text="Extra rows to show if allow_multiple checked")
    questionnaire_help = models.TextField(blank=True)

    def __unicode__(self):
        return self.code

    def get_elements(self):
        import string
        return map(string.strip, self.elements.split(","))

    @property
    def cde_models(self):
        models = []

        for cde_code in self.get_elements():
            try:
                cde_model = CommonDataElement.objects.get(code=cde_code)
                models.append(cde_model)
            except CommonDataElement.DoesNotExist:
                pass

        return models

    def clean(self):
        for element in self.get_elements():
            try:
                CommonDataElement.objects.get(code=element)
            except CommonDataElement.DoesNotExist:
                raise ValidationError(
                    "section %s refers to CDE with code %s which doesn't exist" %
                    (self.display_name, element))

        if self.code.count(" ") > 0:
            raise ValidationError("Section %s code '%s' contains spaces" %
                                  (self.display_name, self.code))


class Registry(models.Model):

    class Meta:
        verbose_name_plural = "registries"

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10)
    desc = models.TextField()
    splash_screen = models.TextField()
    patient_splash_screen = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=20, blank=True)
    # a section which holds registry specific patient information
    patient_data_section = models.ForeignKey(Section, null=True, blank=True)
    # metadata is a dictionary
    # keys ( so far):
    # "visibility" : [ element, element , *] allows GUI elements to be shown in demographics form for a given registry but not others
    # a dictionary of configuration data -  GUI visibility
    metadata_json = models.TextField(blank=True)

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
        from rdrf.field_lookup import FieldFactory
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

    def get_adjudications(self):
        if not has_feature("adjudication"):
            return []

        class ActionDropDownItem(object):

            def __init__(self):
                self.display_name = ""
                self.url_name = "adjudication_initiation"
                self.args = []

        actions = []
        for adj_def in AdjudicationDefinition.objects.filter(registry=self):
            item = ActionDropDownItem()
            item.display_name = adj_def.display_name
            item.url_name = "adjudication_initiation"
            item.args = [adj_def.id]
            actions.append(item)

        return actions

    def _generated_section_questionnaire_code(self, form_name, section_code):
        return self.questionnaire_section_prefix + form_name + section_code

    def generate_questionnaire(self):
        logger.info("starting to generate questionnaire for %s" % self)
        if not new_style_questionnaire(self):
            logger.info(
                "This reqistry is not exposing any questionnaire questions - nothing to do")
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
        generated_questionnaire_form, created = RegistryForm.objects.get_or_create(
            registry=self, name=generated_questionnaire_form_name)

        # get rid of any existing generated sections
        for section in Section.objects.all():
            if section.code.startswith(self.questionnaire_section_prefix):
                section.delete()

        generated_questionnaire_form.registry = self
        generated_questionnaire_form.is_questionnaire = True
        generated_questionnaire_form.save()
        logger.info("created questionnaire form %s" % generated_questionnaire_form.name)
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
            logger.info("created section %s containing cdes %s" %
                        (qsection.code, qsection.elements))
            generated_section_codes.append(qsection.code)

            section_ordering_map[form_name + "." + original_section_code] = qsection.code

        ordered_codes = []

        for f in self.forms:
            for s in f.get_sections():
                k = f.name + "." + s
                if k in section_ordering_map:
                    ordered_codes.append(section_ordering_map[k])

        patient_info_section = self._get_patient_info_section()

        generated_questionnaire_form.sections = patient_info_section + \
            "," + self._get_patient_address_section() + "," + ",".join(ordered_codes)
        generated_questionnaire_form.save()

        logger.info("finished generating questionnaire for registry %s" % self.code)

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

    def __unicode__(self):
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

    @property
    def structure(self):
        """
        Return a dictionary that shows the nested form structure of this registry
        """
        s = {}
        s["name"] = self.name
        s["code"] = self.code
        s["desc"] = self.desc
        s["version"] = self.version
        s["forms"] = []
        s["metadata_json"] = self.metadata_json
        for form in self.forms:
            if form.name == self.generated_questionnaire_name:
                # we don't need to "design" a generated form so we skip
                continue
            form_dict = {}
            form_dict["name"] = form.name
            form_dict["questionnaire_display_name"] = form.questionnaire_display_name
            form_dict["sections"] = []
            form_dict["is_questionnaire"] = form.is_questionnaire
            form_dict["position"] = form.position
            form_dict["questionnaire_questions"] = form.questionnaire_questions
            qcodes = form.questionnaire_questions.split(",")

            for section in form.section_models:
                section_dict = {}
                section_dict["code"] = section.code
                section_dict["display_name"] = section.display_name
                section_dict["questionnaire_display_name"] = section.questionnaire_display_name
                section_dict["allow_multiple"] = section.allow_multiple
                section_dict["extra"] = section.extra
                section_dict["questionnaire_help"] = section.questionnaire_help
                elements = []
                for element_code in section.get_elements():
                    question_code = section.code + "." + element_code
                    in_questionnaire = question_code in qcodes
                    # NB. We capture each cde code in a section and whether it is used in the
                    # questionnaire
                    elements.append([element_code, in_questionnaire])

                section_dict["elements"] = elements  # codes + whether in questionnaire
                form_dict["sections"].append(section_dict)
            s["forms"].append(form_dict)

        return s

    @structure.setter
    def structure(self, new_structure):
        """
        Update this registry to the new structure
        """
        self._check_structure(new_structure)

        logger.info("updating structure for registry %s pk %s" % (self, self.pk))
        logger.info("old structure = %s" % self.structure)
        logger.info("new structure = %s" % new_structure)

        # don't include generated form
        original_forms = [
            f for f in self.forms if f.name != f.registry.generated_questionnaire_name]
        logger.info("original forms = %s" % original_forms)

        self.name = new_structure["name"]
        self.code = new_structure["code"]
        self.desc = new_structure["desc"]
        self.version = new_structure["version"]
        if "metadata_json" in new_structure:
            self.metadata_json = new_structure["metadata_json"]
        self.save()

        new_forms = []
        for form_dict in new_structure["forms"]:
            form_name = form_dict["name"]
            form, created = RegistryForm.objects.get_or_create(name=form_name, registry=self)
            form.questionnaire_display_name = form_dict["questionnaire_display_name"]
            form.is_questionnaire = form_dict["is_questionnaire"]
            form.position = form_dict["position"]
            questionnaire_questions = []
            form.sections = ",".join([s["code"] for s in form_dict["sections"]])
            new_forms.append(form)
            # update sections
            for section_dict in form_dict["sections"]:
                section, created = Section.objects.get_or_create(code=section_dict["code"])
                section.display_name = section_dict["display_name"]
                section.questionnaire_display_name = section_dict["questionnaire_display_name"]
                section.allow_multiple = section_dict["allow_multiple"]
                section.extra = section_dict["extra"]
                section.questionnaire_help = section_dict["questionnaire_help"]
                element_pairs = section_dict["elements"]
                section_elements = []
                for pair in element_pairs:
                    element_code = pair[0]
                    in_questionnaire = pair[1]
                    section_elements.append(element_code)
                    if in_questionnaire:
                        questionnaire_questions.append(
                            section_dict["code"] + "." + element_code)
                section.elements = ",".join(section_elements)
                section.save()

            form.questionnaire_questions = ",".join(questionnaire_questions)
            for qq in questionnaire_questions:
                logger.info(
                    "registry %s form %s is exposing questionnaire question: %s" %
                    (self.code, form_name, qq))

            form.save()

        # delete forms which are in original forms but not in new_forms
        forms_to_delete = set(original_forms) - set(new_forms)
        for form in forms_to_delete:
            logger.warning("%s not in new forms - deleting!" % form)
            form.delete()

    def clean(self):
        self._check_metadata()
        self._check_dupes()


    def _check_dupes(self):
        dupes = [ r for r in Registry.objects.all() if r.code.lower() == self.code.lower() and r.pk != self.pk ]
        names = " ".join([ "%s %s" % (r.code, r.name) for r in dupes])
        if len(dupes) > 0:
            raise ValidationError("Code %s already exists ( ignore case) in: %s" % (self.code, names))

    @property
    def context_name(self):
        try:
            return self.metadata['context_name']
        except KeyError:
            return "Context"

    def _check_metadata(self):
        if self.metadata_json == "":
            return True
        try:
            value = json.loads(self.metadata_json)
            if not isinstance(value, dict):
                raise ValidationError("metadata json field should be a valid json dictionary")
        except ValueError:
            raise ValidationError("metadata json field should be a valid json dictionary")

    def _check_structure(self, structure):
        # raise error if structure not valid

        for k in ["name", "code", "version", "forms"]:
            if k not in structure:
                raise InvalidStructureError("Missing key: %s" % k)
        for form_dict in structure["forms"]:
            for k in ["name", "is_questionnaire", "position", "sections"]:
                if k not in form_dict:
                    raise InvalidStructureError("Form dict %s missing key %s" % (form_dict, k))

            form_name = form_dict["name"]

            for section_dict in form_dict["sections"]:
                for k in [
                        "code",
                        "display_name",
                        "allow_multiple",
                        "extra",
                        "elements",
                        "questionnaire_help"]:
                    if k not in section_dict:
                        raise InvalidStructureError(
                            "Section %s missing key %s" % (section_dict, k))

                for pair in section_dict["elements"]:
                    element_code = pair[0]

                    logger.info("checking section %s code %s" %
                                (section_dict["code"], element_code))
                    try:
                        CommonDataElement.objects.get(code=element_code)
                    except CommonDataElement.DoesNotExist:
                        section_code = section_dict["code"]
                        raise InvalidStructureError(
                            "Form %s Section %s refers to data element %s which does not exist" %
                            (form_name, section_code, element_code))


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

    def __unicode__(self):
        return "PVG %s containing %d items" % (self.code, len(self.members()))


class CDEPermittedValue(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30)
    value = models.CharField(max_length=256)
    questionnaire_value = models.CharField(max_length=256, null=True, blank=True)
    desc = models.TextField(null=True)
    pv_group = models.ForeignKey(CDEPermittedValueGroup, related_name='permitted_value_set')
    position = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = (('pv_group', 'code'),)

    def pvg_link(self):
        url = reverse('admin:rdrf_cdepermittedvaluegroup_change', args=(self.pv_group.code,))
        return "<a href='%s'>%s</a>" % (url, self.pv_group.code)

    pvg_link.allow_tags = True
    pvg_link.short_description = 'Permitted Value Group'

    def questionnaire_value_formatted(self):
        if not self.questionnaire_value:
            return "<i><font color='red'>Not set</font></i>"
        return "<font color='green'>%s</font>" % self.questionnaire_value

    questionnaire_value_formatted.allow_tags = True
    questionnaire_value_formatted.short_description = 'Questionnaire Value'

    def position_formatted(self):
        if not self.position:
            return "<i><font color='red'>Not set</font></i>"
        return "<font color='green'>%s</font>" % self.position

    position_formatted.allow_tags = True
    position_formatted.short_description = 'Order position'

    def __unicode__(self):
        return "Member of %s" % self.pv_group.code


class CommonDataElement(models.Model):
    code = models.CharField(max_length=30, primary_key=True)
    name = models.CharField(max_length=250, blank=False, help_text="Label for field in form")
    desc = models.TextField(blank=True, help_text="origin of field")
    datatype = models.CharField(max_length=50, help_text="type of field")
    instructions = models.TextField(
        blank=True, help_text="Used to indicate help text for field")
    pv_group = models.ForeignKey(
        CDEPermittedValueGroup,
        null=True,
        blank=True,
        help_text="If a range, indicate the Permissible Value Group")
    allow_multiple = models.BooleanField(
        default=False, help_text="If a range, indicate whether multiple selections allowed")
    max_length = models.IntegerField(
        blank=True, null=True, help_text="Length of field - only used for character fields")
    max_value = models.IntegerField(
        blank=True, null=True, help_text="Only used for numeric fields")
    min_value = models.IntegerField(
        blank=True, null=True, help_text="Only used for numeric fields")
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

    def __unicode__(self):
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

    def get_display_value(self, stored_value):
        if self.pv_group:
            # if a range, return the display value
            try:
                values_dict = self.pv_group.as_dict()
                for value_dict in values_dict["values"]:
                    if value_dict["code"] == stored_value:
                        display_value = value_dict["value"]
                        return display_value

            except Exception, ex:
                logger.error("bad value for cde %s %s: %s" % (self.code,
                                                              stored_value,
                                                              ex))
        if stored_value == "NaN":
            # the DataTable was not escaping this value and interpreting it as NaN 
            return ":NaN"
        return stored_value

    def clean(self):
        # this was causing issues with form progress completion cdes record
        # todo update the way form progress completion cdes are recorded to
        # only use code not cde.name!

        if "." in self.name:
            raise ValidationError("CDE %s  name error '%s' has dots - this causes problems please remove" % (self.code,
                                                                                                             self.name))

        if " " in self.code:
            raise Exception("CDE [%s] has space(s) in code - this causes problems please remove" % self.code)


class CdePolicy(models.Model):
    registry = models.ForeignKey(Registry)
    cde = models.ForeignKey(CommonDataElement)
    groups_allowed = models.ManyToManyField(Group, blank=True)
    condition = models.TextField(blank=True)
    
    def is_allowed(self, user_groups, patient_model=None):
        logger.debug("checking cde policy %s %s" % (self.registry, self.cde))
        for ug in user_groups:
            logger.debug("checking user group %s" % ug)
            if ug in self.groups_allowed.all():
                if patient_model:
                    logger.debug("patient model supplied - evaluating against condition")
                    return self.evaluate_condition(patient_model)
                else:
                    logger.debug("no patient model so returning True")
                    return True

    class Meta:
        verbose_name = "CDE Policy"
        verbose_name_plural = "CDE Policies"

    def evaluate_condition(self, patient_model):
        logger.debug("evaluating condition ...")
        if not self.condition:
            logger.debug("*** condition empty - returning True")
            return True
        # need to think about safety here
        context = {"patient": patient_model}
        result = eval(self.condition, {"__builtins__": None}, context)
        logger.debug("*** %s eval %s = %s" % (patient_model, self.condition, result))
        return result


class RegistryFormManager(models.Manager):

    def get_by_registry(self, registry):
        return self.model.objects.filter(registry__id__in=registry)


class RegistryForm(models.Model):

    """
    A representation of a form ( a bunch of sections)
    """
    registry = models.ForeignKey(Registry)
    name = models.CharField(max_length=80)
    header = models.TextField(blank=True)
    questionnaire_display_name = models.CharField(max_length=80, blank=True)
    sections = models.TextField(help_text="Comma-separated list of sections")
    objects = RegistryFormManager()
    is_questionnaire = models.BooleanField(
        default=False, help_text="Check if this form is questionnaire form for it's registry")
    is_questionnaire_login = models.BooleanField(
        default=False,
        help_text="If the form is a questionnaire, is it accessible only by logged in users?",
        verbose_name="Questionnaire Login Required")
    position = PositionField(collection='registry')
    questionnaire_questions = models.TextField(
        blank=True, help_text="Comma-separated list of sectioncode.cdecodes for questionnnaire")
    complete_form_cdes = models.ManyToManyField(CommonDataElement, blank=True)
    groups_allowed = models.ManyToManyField(Group, blank=True)

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
        from rdrf.utils import de_camelcase
        if self.questionnaire_display_name:
            return self.questionnaire_display_name
        else:
            return de_camelcase(self.name)

    def __unicode__(self):
        return "%s %s Form comprising %s" % (self.registry, self.name, self.sections)

    def get_sections(self):
        import string
        return map(string.strip, self.sections.split(","))

    @property
    def questionnaire_list(self):
        """
        returns a list of sectioncode.cde_code strings
        E.g. [ "sectionA.cdecode23", "sectionB.code100" , ...]
        """
        return filter(
            lambda s: len(s) > 0, map(
                string.strip, self.questionnaire_questions.split(",")))

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

    def in_questionnaire(self, section_code, cde_code):
        questionnaire_code = "%s.%s" % (section_code, cde_code)
        return questionnaire_code in self.questionnaire_list

    @property
    def has_progress_indicator(self):
        return True if len(self.complete_form_cdes.values_list()) > 0 else False

    def link(self, patient_model):
        from rdrf.utils import FormLink
        return FormLink(patient_model.pk, self.registry, self).url

    @property
    def nice_name(self):
        from rdrf.utils import de_camelcase
        try:
            return de_camelcase(self.name)
        except:
            return self.name

    def get_link(self, patient_model, context_model=None):
        if context_model is None:
            return reverse('registry_form', args=(self.registry.code, self.id, patient_model.id))
        else:
            return reverse('registry_form', args=(self.registry.code, self.id, patient_model.id, context_model.id))

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
            raise ValidationError(msg)
        if self.pk:
            self._check_completion_cdes()
        




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
    registry = models.ForeignKey(Registry)
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
        dob = self._get_patient_field("CDEPatientDateOfBirth")
        return dob.date()

    def _get_patient_field(self, patient_field):
        from dynamic_data import DynamicDataWrapper
        from django.conf import settings
        wrapper = DynamicDataWrapper(self)
        wrapper._set_client()
        
        if not self.has_mongo_data:
            raise ObjectDoesNotExist

        questionnaire_form_name = RegistryForm.objects.get(
            registry=self.registry, is_questionnaire=True).name

        value = wrapper.get_nested_cde(self.registry.code, questionnaire_form_name, "PatientData", patient_field)

        logger.debug("_get_patient_field %s = %s" % (patient_field, value))

        if value is None:
            return ""

        return value

    @property
    def has_mongo_data(self):
        from rdrf.dynamic_data import DynamicDataWrapper
        wrapper = DynamicDataWrapper(self)
        wrapper._set_client()
        return wrapper.has_data(self.registry.code)


def appears_in(cde, registry, registry_form, section):
    if section.code not in registry_form.get_sections():
        return False
    elif registry_form.name not in [f.name for f in RegistryForm.objects.filter(registry=registry)]:
        return False
    else:
        return cde.code in section.get_elements()


# Adjudication models
class AdjudicationError(Exception):
    pass


class AdjudicationRequestState(object):
    CREATED = "C"        # Just been created - no notification sent
    REQUESTED = "R"      # Email sent - waiting to be processed
    PROCESSED = "P"     # User has checked the data and updated result
    INVALID = "I"      # Something has gone wrong and this request is not useable


class AdjudicationState(object):

    """
    for a given patient and definition
    """
    NOT_CREATED = "N"    # no adjudication requests exist for this patient/adjudication pair
    UNADJUDICATED = "U"  # requests sent out, but admin has not adjudicated
    ADJUDICATED = "A"


class MissingData(object):
    pass


class AdjudicationDefinition(models.Model):
    registry = models.ForeignKey(Registry)
    # name which will be seen by end users
    display_name = models.CharField(max_length=80, blank=True, null=True)
    fields = models.TextField()
    result_fields = models.TextField()  # section_code containing cde codes of result
    # cde code of a range field with allowed actions
    decision_field = models.TextField(blank=True, null=True)
    # an admin user to check the incoming
    adjudicator_username = models.CharField(max_length=80, default="admin")
    adjudicating_users = models.TextField(
        blank=True,
        null=True,
        help_text="Either comma-seperated list of usernames and/or working group names")

    def create_adjudication_request(self, request, requesting_user, patient, target_user):
        adj_request = AdjudicationRequest(
            username=target_user.username,
            requesting_username=requesting_user.username,
            patient=patient.pk,
            definition=self)

        adj_request.save()   # state now created
        adj_request.send(request)   # state not I or S
        return adj_request

    def _get_demographic_field(self, patient, demographic_cde_code):
        return getattr(patient, demographic_cde_code)

    def get_field_data(self, patient):
        data = {}
        if not patient.in_registry(self.registry.code):
            raise AdjudicationError(
                "Patient %s is not in registry %s so cannot be adjudicated!" %
                (patient, self.registry))
        for form_name, section_code, cde_code in self._get_field_specs():
            if form_name == 'demographics':
                # NB. for demographics section isn't used
                field_value = self._get_demographic_field(patient, cde_code)
            else:
                try:
                    field_value = patient.get_form_value(
                        self.registry.code, form_name, section_code, cde_code)
                except KeyError:
                    field_value = MissingData
            data[(form_name, section_code, cde_code)] = field_value
        return data

    def _get_field_specs(self):
        from django.conf import settings
        specs = self.fields.strip().split(",")
        for spec in specs:
            if "patient." in spec.lower():
                field_name = spec.split(".")[1]
                yield "demographics", "dummy", field_name
            else:
                form_name, section_code, cde_code = spec.strip().split(
                    settings.FORM_SECTION_DELIMITER)
                yield form_name, section_code, cde_code

    def create_form(self):
        adjudication_section = Section.objects.get(code=self.result_fields)
        from dynamic_forms import create_form_class_for_section

        class DummyForm(object):

            def __init__(self):
                self.name = "AdjudicationForm"

        adj_form = DummyForm()
        form_class = create_form_class_for_section(
            self.registry, adj_form, adjudication_section)
        return form_class()

    def create_decision_form(self):
        decision_section = Section.objects.get(code=self.decision_field)
        from dynamic_forms import create_form_class_for_section

        class DummyForm(object):

            def __init__(self):
                self.name = "DecisionForm"

        dec_form = DummyForm()
        form_class = create_form_class_for_section(self.registry, dec_form, decision_section)
        return form_class()

    @property
    def questions(self):
        return sorted([cde_model.name for cde_model in self.cde_models])

    @property
    def actions(self):
        return sorted([cde_model.name for cde_model in self.action_cde_models])

    def get_adjudication_form_datapoints(self, patient):
        """
        The field values to "judge"
        :return: datapoints, missing_flag
        """
        datapoints = []
        missing_flag = False  # flags if any datapoints are missing

        def get_cde_display_value(cde_model, stored_value):
            if stored_value is MissingData:
                return "Missing Data!"

            def get_disp(stored_value):
                if cde_model.datatype in ['range']:
                    group_dict = cde_model.pv_group.as_dict()
                    for value_map in group_dict["values"]:
                        if value_map["code"] == stored_value:
                            return value_map["value"]
                    return "Error! stored_value = %s allowed_values = %s" % (
                        stored_value, group_dict)
                else:
                    return stored_value

            # sometimes _lists_ are stored when we have multiple checklist
            if isinstance(stored_value, list):
                return ",".join(map(get_disp, stored_value))
            else:
                return get_disp(stored_value)

        class DataPoint(object):

            def __init__(self, label, value):
                self.label = label
                self.value = value

        field_map = self.get_field_data(patient)
        missing_flag = MissingData in field_map.values()

        for form_name, section_code, cde_code in field_map:
            if form_name == 'demographics':
                value = self._get_demographic_field(patient, cde_code)
                label = "Form %s  Field %s" % (form_name, cde_code)
                display_value = str(value)
            else:
                section_model = Section.objects.get(code=section_code)
                cde_model = CommonDataElement.objects.get(code=cde_code)
                label = "Form %s Section %s Field %s" % (
                    form_name, section_model.display_name, cde_model.name)
                value = field_map[(form_name, section_code, cde_code)]
                display_value = get_cde_display_value(cde_model, value)
            datapoints.append(DataPoint(label, display_value))
        return sorted(datapoints, key=lambda datapoint: datapoint.label), missing_flag

    def create_adjudication_inititiation_form_context(self, patient_model):
        # adjudication_initiation_form, datapoints, users, working_groups = adj_def.create_adjudication_inititiation_form(patient)
        from registry.groups.models import CustomUser, WorkingGroup
        datapoints, missing_data = self.get_adjudication_form_datapoints(patient_model)
        logger.debug("datapoints = %s" % datapoints)
        users_or_groups = self.adjudicating_users.split(",")
        users = []
        groups = []

        for username_or_working_group_name in users_or_groups:
            try:
                logger.debug("checking user or group %s" % username_or_working_group_name)
                user = CustomUser.objects.get(username=username_or_working_group_name)
                users.append(user)
            except CustomUser.DoesNotExist:
                try:
                    wg = WorkingGroup.objects.get(
                        registry=self.registry, name=username_or_working_group_name)
                    logger.debug("Adding working group %s" % wg)
                    groups.append(wg)
                except WorkingGroup.DoesNotExist:
                    logger.error(
                        "%s is not in %s as a user or a working group so can't be added to the adjudication list for %s" %
                        (username_or_working_group_name, self))

        context = {
            "adjudication_definition": self,
            "patient": patient_model,
            "datapoints": datapoints,
            "users": users,
            "groups": groups,
            "missing_data": missing_data,
        }
        return context

    @property
    def cde_models(self):
        """
        :return: data elements for the adjudication fields of this definition
        """
        section = Section.objects.get(code=self.result_fields)
        return section.cde_models

    @property
    def action_cde_models(self):
        section = Section.objects.get(code=self.decision_field)
        return section.cde_models

    def get_state(self, patient):
        try:
            AdjudicationDecision.objects.get(definition=self, patient=patient.pk)
            return AdjudicationState.ADJUDICATED
        except AdjudicationDecision.DoesNotExist:
            requests = [ar for ar in AdjudicationRequest.objects.filter(
                patient=patient.pk, definition=self)]
            if len(requests) == 0:
                return AdjudicationState.NOT_CREATED
            else:
                return AdjudicationState.UNADJUDICATED


class AdjudicationRequest(models.Model):
    # NB I am using usernames and patient pk here because using caused circular import ...
    # username of the user  this request directed to
    username = models.CharField(max_length=80)
    # the username of the user requesting this adjudication
    requesting_username = models.CharField(max_length=80)
    patient = models.IntegerField()           # the patient's pk whose data we are checking
    # the set of fields we are exposing in the request and
    definition = models.ForeignKey(AdjudicationDefinition)
    # the result fields to hold the diagnosis vote
    state = models.CharField(max_length=1, default=AdjudicationRequestState.CREATED)

    def send(self, request):
        # send the email or something ..
        fails = 0
        try:
            self._send_email(request)
        except NotificationError as ex:
            logger.error("could not send email for %s: %s" % (self, ex))
            fails += 1

        try:
            self._create_notification()
        except NotificationError:
            logger.error("could not send internal notification for %s: %s" % (self, ex))
            fails + 1

        if fails == 2:
            self.state = AdjudicationRequestState.INVALID
        else:
            self.state = AdjudicationRequestState.REQUESTED

        self.save()

    def _send_email(self, request):
        from rdrf.utils import get_user
        email_subject = self._create_email_subject()
        email_body = self._create_email_body(request)
        sending_user = get_user(self.requesting_username)
        if not sending_user:
            raise NotificationError(
                "Could not send email from %s as the user doesn't exist!" %
                self.requesting_username)

        from rdrf.notifications import Notifier
        notifier = Notifier()
        notifier.send_email_to_username(self.username,
                                        email_subject,
                                        email_body,
                                        message_type="Adjudication Request")

    def _create_email_subject(self):
        return "Adjudication Request from %s: %s" % (
            self.definition.registry.name, self.definition.display_name)

    def _create_email_body(self, request):
        from rdrf.utils import get_full_link
        full_link = get_full_link(request, self.link, login_link=True)

        body = """
            Dear %s user %s,
            An adjudication request has been assigned to you for %s.
            Please visit %s to complete the adjudication.
            """ % (self.definition.registry.name, self.username, self.definition.display_name, full_link)
        return body

    def _create_notification(self):
        from rdrf.notifications import Notifier
        notification_message = self._create_notification_message()
        notifier = Notifier()
        notifier.send_system_notification(
            self.requesting_username, self.username, notification_message, self.link)

    def _create_notification_message(self):
        message = "Adjudication Requested for %s" % self.definition.display_name
        return message

    @property
    def link(self):
        return reverse('adjudication_request', args=(self.pk,))

    @property
    def patient_model(self):
        from registry.patients.models import Patient
        return Patient.objects.get(pk=self.patient)

    @property
    def adjudication(self):
        # helper property to locate the corresponding adjudication object
        return Adjudication.objects.get(definition=self.definition,
                                        patient_id=self.patient,
                                        requesting_username=self.requesting_username)

    @property
    def decided(self):
        # check if a decision object exists for the definition and patient
        # corresponding to this request
        try:
            decision = AdjudicationDecision.objects.get(
                definition=self.definition, patient=self.patient)
            if decision:
                return True
        except:
            return False

    def handle_response(self, request):
        adjudication_form_response_data = request.POST
        adjudication_codes = [cde.code for cde in self.definition.cde_models]

        def is_valid(field_data):
            return set(field_data.keys()) == set(adjudication_codes)

        def extract_field_data(data):
            from rdrf.utils import get_form_section_code

            field_data = {}
            for k in data:
                try:
                    frm, sec, code = get_form_section_code(k)
                    if code in adjudication_codes:
                        # todo for now we assume integers
                        field_data[code] = int(data[k])
                except:
                    pass

            if not is_valid(field_data):
                raise AdjudicationError(
                    "Adjudication form not filled in completely - please try again")

            return field_data

        def convert_to_json(data):
            import json
            return json.dumps(data)

        field_data = extract_field_data(adjudication_form_response_data)
        json_field_data = convert_to_json(field_data)
        adj_response = AdjudicationResponse(request=self, response_data=json_field_data)
        adj_response.save()
        self.state = AdjudicationRequestState.PROCESSED
        self.save()
        adj_response.send_notifications(request)
        return True

    def create_adjudication_form(self):
        from registry.patients.models import Patient
        patient_model = Patient.objects.get(pk=self.patient)
        datapoints, missing_flag = self.definition.get_adjudication_form_datapoints(
            patient_model)
        adjudication_form = self.definition.create_form()
        return adjudication_form, datapoints

    @property
    def response(self):
        try:
            return AdjudicationResponse.objects.get(request=self)
        except AdjudicationResponse.DoesNotExist:
            return None


class AdjudicationResponse(models.Model):
    request = models.ForeignKey(AdjudicationRequest)   # the originating adjudication request
    response_data = models.TextField()  # json dict of response cde codes to chosen values

    @property
    def data(self):
        import json
        return json.loads(self.response_data)

    def get_cde_value(self, cde_model):
        if cde_model.code in self.data:
            return self.data[cde_model.code]
        else:
            raise AdjudicationError("cde not in data")

    def send_notifications(self, request):
        # back to adjudicator telling them someone responded
        from rdrf.notifications import Notifier
        n = Notifier()
        notification_message = "An adjudication request has been completed by %s for %s for %s concerning %s" % \
                               (self.request.username,
                                self.request.requesting_username,
                                self.request.definition.display_name,
                                self.request.patient)

        link = self.request.adjudication.link

        n.send_system_notification(self.request.username,
                                   self.request.definition.adjudicator_username,
                                   notification_message,
                                   link)
        try:
            self._send_email(request)
        except NotificationError as nerr:
            msg = "could not send email to adjudicator %s about %s adjudication response: %s" % (
                self.request.definition.adjudicator_username, self.request.definition.display_name, nerr)

            logger.error(msg)

    def _send_email(self, request):
        email_subject = "Adjudication Request completed by %s for %s concerning %s" % (
            self.request.username, self.request.requesting_username, self.request.definition.display_name)
        full_link = get_full_link(request, self.request.adjudication.link, login_link=True)
        email_body = """
                     Hello %s User %s,
                     An adjudication request has been completed for adjudication %s for which you are an
                     adjudicator.
                     You can check the incoming adjudications here: %s.
                     If enough adjudiction requests have come back, submit your adjudication decision in
                     the results field.
                     """ % (self.request.definition.registry.name,
                            self.request.definition.adjudicator_username,
                            self.request.definition.display_name,
                            full_link)

        n = Notifier()
        n.send_email_to_username(
            self.request.definition.adjudicator_username, email_subject, email_body)


class AdjudicationDecision(models.Model):
    definition = models.ForeignKey(AdjudicationDefinition)
    patient = models.IntegerField()           # the patient's pk
    # json list  of action cde codes (decision codes)#  to values ( actions)
    decision_data = models.TextField()

    @property
    def actions(self):
        try:
            import json
            return json.loads(self.decision_data)
        except:
            return []

    @actions.setter
    def actions(self, action_code_value_pairs):
        import json
        actions = []
        for code, value in action_code_value_pairs:
            actions.append((code, value))
        self.decision_data = json.dumps(actions)

    @property
    def patient_model(self):
        from registry.patients.models import Patient
        return Patient.objects.get(pk=self.patient)

    @property
    def summary(self):
        actions = ','.join(["%s: %s" % (variable, value)
                            for variable, value in self.display_actions])
        patient = "%s" % self.patient_model
        return "Adjudication Decision for %s concerning %s: %s" % (
            patient, self.definition.display_name, actions)

    @property
    def display_actions(self):
        for code, value in self.actions:
            try:
                cde_model = CommonDataElement.objects.get(code=code)
                display_text = cde_model.name
                display_value = value
                if cde_model.pv_group:
                    range_dict = cde_model.pv_group.as_dict()
                    for value_dict in range_dict['values']:
                        if value == value_dict['code']:
                            # the display value for the range member
                            display_value = value_dict['value']
                yield display_text, display_value
            except CommonDataElement.DoesNotExist:
                yield code, value

    def clean(self):
        definition_action_cde_models = self.definition.action_action_cde_models
        allowed_codes = [cde.code for cde in definition_action_cde_models]

        for (action_cde_code, value) in self.actions:
            if action_cde_code not in allowed_codes:
                raise ValidationError(
                    "Action code %s is not in allowed codes for definition" % action_cde_code)


class Adjudication(models.Model):

    """
    Used to present adjudication to admin
    """
    definition = models.ForeignKey(AdjudicationDefinition)
    # the username of the user requesting this adjudication
    requesting_username = models.CharField(max_length=80)
    patient_id = models.IntegerField()           # the patient's pk
    # The decision the deciding/adjudicating user made
    decision = models.ForeignKey(AdjudicationDecision, null=True)

    def _count_requests(self, state=None):
        if not state:
            return AdjudicationRequest.objects.filter(
                definition=self.definition,
                patient=self.patient_id,
                requesting_username=self.requesting_username).count()
        else:
            return AdjudicationRequest.objects.filter(
                definition=self.definition,
                patient=self.patient_id,
                requesting_username=self.requesting_username,
                state=state).count()

    @property
    def adjudicator(self):
        return self.definition.adjudicator_username

    @property
    def adjudicator_user(self):
        from registry.groups.models import CustomUser
        try:
            return CustomUser.objects.get(username=self.adjudicator)
        except CustomUser.DoesNotExist:
            return None

    @property
    def requesting_user(self):
        from registry.groups.models import CustomUser
        try:
            return CustomUser.objects.get(username=self.requesting_username)
        except CustomUser.DoesNotExist:
            return None

    @property
    def responded(self):
        return self._count_requests(AdjudicationRequestState.PROCESSED)

    @property
    def requested(self):
        return self._count_requests()

    @property
    def status(self):
        state_map = {}
        for adj_req in AdjudicationRequest.objects.filter(
                definition=self.definition,
                patient=self.patient_id,
                requesting_username=self.requesting_username):
            if adj_req.state not in state_map:
                state_map[adj_req.state] = 1
            else:
                state_map[adj_req.state] += 1
        return str(state_map)

    @property
    def link(self):
        from registry.groups.models import CustomUser
        requesting_user = CustomUser.objects.get(username=self.requesting_username)
        return reverse(
            'adjudication_result',
            args=(
                self.definition.pk,
                requesting_user.pk,
                self.patient_id))

    def perform_actions(self, request):
        class Result(object):

            def __init__(self):
                self.ok = True
                self.error_message = ""

        from rdrf.adjudication_actions import AdjudicationAction
        action = AdjudicationAction(self)
        result = Result()
        action.run(request)
        if action.email_notify_failed:
            result.ok = False
            result.error_message += "Email failed to be sent"
        elif action.system_notify_failed:
            result.ok = False
            result.error_message += "System notification failed to be sent"
        return result


class Notification(models.Model):
    from_username = models.CharField(max_length=80)
    to_username = models.CharField(max_length=80)
    created = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    link = models.CharField(max_length=100, default="")
    seen = models.BooleanField(default=False)


class ConsentSection(models.Model):
    code = models.CharField(max_length=20)
    section_label = models.CharField(max_length=100)
    registry = models.ForeignKey(Registry, related_name="consent_sections")
    information_link = models.CharField(max_length=100, blank=True, null=True)
    information_text = models.TextField(blank=True, null=True)
    # eg "patient.age > 6 and patient.age" < 10
    applicability_condition = models.TextField(blank=True)
    validation_rule = models.TextField(blank=True)

    def applicable_to(self, patient):
        if patient is None:
            return True

        if not patient.in_registry(self.registry.code):
            return False
        else:
            # if no restriction return True
            if not self.applicability_condition:
                return True

            function_context = {"patient": patient}

            is_applicable = eval(
                self.applicability_condition, {"__builtins__": None}, function_context)

            if is_applicable:
                logger.debug("%s is spplicable to %s" % (self, patient))
            else:
                logger.debug("%s is NOT applicable to %s" % (self, patient))
            return is_applicable

    def is_valid(self, answer_dict):
        """
        does the supplied question_code --> answer map
        satisfy the validation rule for this section
        :param answer_dict: map of question codes to bool
        :return: True or False depending on validation rule
        """
        if not self.validation_rule:
            logger.debug("no validation rule for %s - returning True" % self.section_label)
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
                logger.info("validation rule for %s returned %s - returning False!" %
                            (self.code, result))
                return False

            if result:
                logger.debug("validation rule for %s passed!" % self)
            else:
                logger.debug("validation rule for %s failed" % self)

            return result
        except Exception as ex:
            logger.error(
                "Error evaluating consent section %s rule %s context %s error %s" %
                (self.code, self.validation_rule, function_context, ex))

            return False

    def __unicode__(self):
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


class ConsentQuestion(models.Model):
    code = models.CharField(max_length=20)
    position = models.IntegerField(blank=True, null=True)
    section = models.ForeignKey(ConsentSection, related_name="questions")
    question_label = models.TextField()
    instructions = models.TextField(blank=True)
    questionnaire_label = models.TextField(blank=True)

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

    def __unicode__(self):
        return "%s" % self.question_label
    



class DemographicFields(models.Model):
    FIELD_CHOICES = []

    registry = models.ForeignKey(Registry)
    group = models.ForeignKey(Group)
    field = models.CharField(max_length=50, choices=FIELD_CHOICES)
    readonly = models.NullBooleanField(null=True, blank=True)
    hidden = models.NullBooleanField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Demographic Fields"


class EmailTemplate(models.Model):
    language = models.CharField(max_length=2, choices=settings.LANGUAGES)
    description = models.TextField()
    subject = models.CharField(max_length=50)
    body = models.TextField()
    
    def __unicode__(self):
        return "%s (%s)" % (self.description, dict(settings.LANGUAGES)[self.language])
    

class EmailNotification(models.Model):
    description = models.CharField(max_length=100, choices=settings.EMAIL_NOTIFICATIONS)
    registry = models.ForeignKey(Registry)
    email_from = models.EmailField(default="no-reply@DOMAIN.COM")
    recipient = models.CharField(max_length=100, null=True, blank=True)
    group_recipient = models.ForeignKey(Group, null=True, blank=True)
    email_templates = models.ManyToManyField(EmailTemplate)

    def __unicode__(self):
        return "%s (%s)" % (self.description, self.registry.code.upper())


class EmailNotificationHistory(models.Model):
    date_stamp = models.DateTimeField(auto_now_add=True)
    language = models.CharField(max_length=10)
    email_notification = models.ForeignKey(EmailNotification)
    template_data = models.TextField(null=True, blank=True)


class RDRFContextError(Exception):
    pass


class RDRFContext(models.Model):
    registry = models.ForeignKey(Registry)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    display_name = models.CharField(max_length=80, blank=True, null=True)

    def __unicode__(self):
        return "%s %s" % (self.display_name, self.created_at)

    def clean(self):
        if not self.display_name:
            raise ValidationError("RDRF Context must have a display name")
        self.display_name = self.display_name.strip()

        if len(self.display_name) == 0:
            raise ValidationError("RDRF Context must have a display name")


class MongoMigrationDummyModel(models.Model):
    """
    This model should never be instantiated.
    It exists so that when a version of RDRF is created that alters the mongo
    structure, the version can be entered as a pair in VERSIONS below
    which will trigger a migration to be created in South.
    This gives us a hook to write mongo transforming code that will act on the data

    *ONLY* UPDATE THE VERSIONS TUPLE IF A MONGO TRANSFORMATION IS NECESSARY!

    This hack works because Django picks up alterations to the allowed choices for the field
    and creates an auto migration.

    To use :

    Precondition: You've made changes to RDRF which alters in some way the mongo structure

    1. Add the new RDRF version V and a short description D to the VERSIONS tuple:

    e.g  VERSIONS =(("1.4", "blah"),
                    ("2.5","forms now nested"),
                    ("4.9", "changing the structure of the progress dictionary"))

    2. After editing the VERSIONS tuple, docker exec a shell inside rdrf web
    docker exec -it rdrf_web_1 /bin/bash

    run: django_admin makemmigrations rdrf

    this will generate the auto migration as below:

    operations = [
        migrations.AlterField(
            model_name='mongomigrationdummymodel',
            name='version',
            field=models.CharField(max_length=80, choices=[(b'initial', b'initial'), (b'testing', b'testing')]),
        ),]


    3. Add a migrations.RunPython(forward_func, backward_func) migration to the operations list ( implementing the mongo
    manipulations via python functions forward_func and backward_func


    I intended to write a module to make it easy to create the forward_func and backward_funcs


    """
    # Add to this VERSIONS tuple ONLY IF a mongo migration is required
    VERSIONS = (("initial", "initial"),
                ("testing", "testing"),
                ("1.0.17", "populate context_id on all patient records"))
    version = models.CharField(max_length=80, choices=VERSIONS)
