from django.db import models
import logging
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from positions.fields import PositionField
import string
import json
from rdrf.utils import has_feature

logger = logging.getLogger("registry")


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
    display_name = models.CharField(max_length=100)
    elements = models.TextField()
    allow_multiple = models.BooleanField(default=False, help_text="Allow extra items to be added")
    extra = models.IntegerField(blank=True, null=True, help_text="Extra rows to show if allow_multiple checked")
    questionnaire_help = models.TextField(blank=True)

    def __unicode__(self):
        return self.code

    def get_elements(self):
        import string
        return map(string.strip, self.elements.split(","))

    @property
    def cde_models(self):
        return [cde for cde in CommonDataElement.objects.filter(code__in=self.get_elements())]

    def clean(self):
        for element in self.get_elements():
            try:
                cde = CommonDataElement.objects.get(code=element)
            except CommonDataElement.DoesNotExist:
                raise ValidationError("section %s refers to CDE with code %s which doesn't exist" % (self.display_name, element))

        if self.code.count(" ") > 0:
            raise ValidationError("Section %s code '%s' contains spaces" % (self.display_name, self.code))


class Registry(models.Model):
    class Meta:
        verbose_name_plural = "registries"

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10)
    desc = models.TextField()
    splash_screen = models.TextField()
    version = models.CharField(max_length=20, blank=True)
    patient_data_section = models.ForeignKey(Section, null=True, blank=True)   # a section which holds registry specific patient information
    # metadata is a dictionary
    # keys ( so far):
    # "visibility" : [ element, element , *] allows GUI elements to be shown in demographics form for a given registry but not others
    metadata_json = models.TextField(blank=True)  # a dictionary of configuration data -  GUI visibility

    @property
    def metadata(self):
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except ValueError:
                logger.error("Registry %s has invalid json metadata: data = '%s" % (self, self.metadata_json))
                return {}
        else:
            return {}

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
        return field_pairs


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
            logger.info("This reqistry is not exposing any questionnaire questions - nothing to do")
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
        generated_questionnaire_form, created = RegistryForm.objects.get_or_create(registry=self, name=generated_questionnaire_form_name)

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
                raise InvalidQuestionnaireError("section with code %s doesn't exist!" % original_section_code)

            qsection = Section()
            qsection.code = self._generated_section_questionnaire_code(form_name, original_section_code)
            qsection.questionnaire_help = original_section.questionnaire_help
            try:
                original_form = RegistryForm.objects.get(registry=self, name=form_name)
            except RegistryForm.DoesNotExist:
                raise InvalidQuestionnaireError("form with name %s doesn't exist!" % form_name)

            qsection.display_name = original_form.questionnaire_name + " - " + original_section.display_name
            qsection.allow_multiple = original_section.allow_multiple
            qsection.extra = 0
            qsection.elements = ",".join([cde_code for cde_code in section_map[(form_name, original_section_code)]])
            qsection.save()
            logger.info("created section %s containing cdes %s" % (qsection.code, qsection.elements))
            generated_section_codes.append(qsection.code)

            section_ordering_map[form_name + "." + original_section_code] = qsection.code

        ordered_codes = []

        for f in self.forms:
            for s in f.get_sections():
                k = f.name + "." + s
                if k in section_ordering_map:
                    ordered_codes.append(section_ordering_map[k])

        consent_section = self._get_consent_section()
        patient_info_section = self._get_patient_info_section()

        generated_questionnaire_form.sections = consent_section + "," + patient_info_section + "," + self._get_patient_address_section() + "," + ",".join(ordered_codes)
        generated_questionnaire_form.save()

        logger.info("finished generating questionnaire for registry %s" % self.code)

    def _get_consent_section(self):
        return "GenericPatientConsent"

    def _get_patient_info_section(self):
        return "PatientData"

    def _get_patient_address_section(self):
        return "PatientDataAddressSection"

    @property
    def generic_sections(self):
        return [self._get_consent_section(), self._get_patient_info_section(), self._get_patient_address_section()]

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
            form_dict["sections"] = []
            form_dict["is_questionnaire"] = form.is_questionnaire
            form_dict["position"] = form.position
            form_dict["questionnaire_questions"] = form.questionnaire_questions
            qcodes = form.questionnaire_questions.split(",")

            for section in form.section_models:
                section_dict = {}
                section_dict["code"] = section.code
                section_dict["display_name"] = section.display_name
                section_dict["allow_multiple"] = section.allow_multiple
                section_dict["extra"] = section.extra
                section_dict["questionnaire_help"] = section.questionnaire_help
                elements = []
                for element_code in section.get_elements():
                    question_code = section.code + "." + element_code
                    in_questionnaire = question_code in qcodes
                    elements.append([element_code, in_questionnaire])  # NB. We capture each cde code in a section and whether it is used in the questionnaire

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

        original_forms = [f for f in self.forms if f.name != f.registry.generated_questionnaire_name]  # don't include generated form
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
            form.is_questionnaire = form_dict["is_questionnaire"]
            form.position = form_dict["position"]
            questionnaire_questions = []
            form.sections = ",".join([s["code"] for s in form_dict["sections"]])
            new_forms.append(form)
            # update sections
            for section_dict in form_dict["sections"]:
                section, created = Section.objects.get_or_create(code=section_dict["code"])
                section.display_name = section_dict["display_name"]
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
                        questionnaire_questions.append(section_dict["code"] + "." + element_code)
                section.elements = ",".join(section_elements)
                section.save()

            form.questionnaire_questions = ",".join(questionnaire_questions)
            for qq in questionnaire_questions:
                logger.info("registry %s form %s is exposing questionnaire question: %s" % (self.code, form_name, qq))

            form.save()

        # delete forms which are in original forms but not in new_forms
        forms_to_delete = set(original_forms) - set(new_forms)
        for form in forms_to_delete:
            logger.warning("%s not in new forms - deleting!" % form)
            form.delete()

    def clean(self):
        self._check_metadata()

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
            if not k in structure:
                raise InvalidStructureError("Missing key: %s" % k)
        for form_dict in structure["forms"]:
            for k in ["name", "is_questionnaire", "position", "sections"]:
                if not k in form_dict:
                    raise InvalidStructureError("Form dict %s missing key %s" % (form_dict, k))

            form_name = form_dict["name"]

            for section_dict in form_dict["sections"]:
                for k in ["code", "display_name", "allow_multiple", "extra", "elements", "questionnaire_help"]:
                    if not k in section_dict:
                        raise InvalidStructureError("Section %s missing key %s" % (section_dict, k))

                for pair in section_dict["elements"]:
                    element_code = pair[0]

                    logger.info("checking section %s code %s" % (section_dict["code"], element_code))
                    try:
                        cde = CommonDataElement.objects.get(code=element_code)
                    except CommonDataElement.DoesNotExist:
                        section_code = section_dict["code"]
                        raise InvalidStructureError("Form %s Section %s refers to data element %s which does not exist" % (form_name, section_code, element_code))


def get_owner_choices():
    """
    Get choices for CDE owner drop down.
    Used to get the list of classes which CDEs can be attached to.
    UNUSED means this CDE will not be used to construct any forms in the registry.

    """
    from django.conf import settings
    choices = [('UNUSED', 'UNUSED')]
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

        return [getattr(v, att) for v in CDEPermittedValue.objects.filter(pv_group=self).order_by('position')]

    def __unicode__(self):
        members = self.members()
        return "PVG %s containing %d items" % (self.code, len(self.members()))


class CDEPermittedValue(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30)
    value = models.CharField(max_length=256)
    questionnaire_value = models.CharField(max_length=256, null=True, blank=True)
    desc = models.TextField(null=True)
    pv_group = models.ForeignKey(CDEPermittedValueGroup, related_name='permitted_value_set')
    position = models.IntegerField(null=True, blank=True)

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
    instructions = models.TextField(blank=True, help_text="Used to indicate help text for field")
    pv_group = models.ForeignKey(CDEPermittedValueGroup, null=True, blank=True, help_text="If a range, indicate the Permissible Value Group")
    allow_multiple = models.BooleanField(default=False, help_text="If a range, indicate whether multiple selections allowed")
    max_length = models.IntegerField(blank=True, null=True, help_text="Length of field - only used for character fields")
    max_value = models.IntegerField(blank=True, null=True, help_text="Only used for numeric fields")
    min_value = models.IntegerField(blank=True, null=True, help_text="Only used for numeric fields")
    is_required = models.BooleanField(default=False, help_text="Indicate whether field is non-optional")
    pattern = models.CharField(max_length=50, blank=True, help_text="Regular expression to validate string fields (optional)")
    widget_name = models.CharField(max_length=80, blank=True, help_text="If a special widget required indicate here - leave blank otherwise")
    calculation = models.TextField(blank=True, help_text="Calculation in javascript. Use context.CDECODE to refer to other CDEs. Must use context.result to set output")
    questionnaire_text = models.TextField(blank=True, help_text="The text to use in any public facing questionnaires/registration forms")

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


class RegistryFormManager(models.Manager):
    def get_by_registry(self, registry):
        return self.model.objects.filter(registry__id__in=registry)


class RegistryForm(models.Model):
    """
    A representation of a form ( a bunch of sections)
    """
    registry = models.ForeignKey(Registry)
    name = models.CharField(max_length=80)
    sections = models.TextField(help_text="Comma-separated list of sections")
    objects = RegistryFormManager()
    is_questionnaire = models.BooleanField(default=False, help_text="Check if this form is questionnaire form for it's registry")
    position = PositionField(collection='registry')
    questionnaire_questions = models.TextField(blank=True, help_text="Comma-separated list of sectioncode.cdecodes for questionnnaire")

    @property
    def questionnaire_name(self):
        from rdrf.utils import de_camelcase
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
        return filter(lambda s: len(s) > 0, map(string.strip, self.questionnaire_questions.split(",")))

    @property
    def section_models(self):
        return [section_model for section_model in Section.objects.filter(code__in=self.get_sections())]

    def in_questionnaire(self, section_code, cde_code):
        questionnaire_code = "%s.%s" % (section_code, cde_code)
        return questionnaire_code in self.questionnaire_list


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
    patient_id = models.IntegerField(blank=True, null=True, help_text="The id of the patient created from this response, if any")

    def __str__(self):
        return "%s (%s)" % (self.registry, self.processed)

    @property
    def name(self):
        return self._get_patient_field("CDEPatientGivenNames") + " " + self._get_patient_field("CDEPatientFamilyName")

    @property
    def date_of_birth(self):
        dob = self._get_patient_field("CDEPatientDateOfBirth")
        return dob.date()

    def _get_patient_field(self, patient_field):
        from dynamic_data import DynamicDataWrapper
        from django.conf import settings
        wrapper = DynamicDataWrapper(self)
        record = wrapper.load_dynamic_data(self.registry.code, "cdes")
        key = settings.FORM_SECTION_DELIMITER.join([self.registry.generated_questionnaire_name, "PatientData", patient_field])
        return record[key]


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


class AdjudicationDefinition(models.Model):
    registry = models.ForeignKey(Registry)
    display_name = models.CharField(max_length=80, blank=True, null=True)  # name which will be seen by end users
    fields = models.TextField()
    result_fields = models.TextField() # section_code containing cde codes of result
    decision_field = models.TextField(blank=True, null=True) # cde code of a range field with allowed actions
    adjudicator_username = models.CharField(max_length=80, default="admin")  # an admin user to check the incoming
    adjudicating_users = models.TextField(blank=True, null=True,  help_text="Either comma-seperated list of usernames and/or working group names")

    def create_adjudication_request(self, requesting_user, patient, target_user):
        adj_request = AdjudicationRequest(username=target_user.username, requesting_username=requesting_user.username,
                                              patient=patient.pk, definition=self)

        adj_request.save()   # state now created
        adj_request.send()   # state not I or S
        return adj_request

    def _get_demographic_field(self, patient, demographic_cde_code):
        return getattr(patient, demographic_cde_code)

    def get_field_data(self, patient):
        data = {}
        if not patient.in_registry(self.registry.code):
            raise AdjudicationError("Patient %s is not in registry %s so cannot be adjudicated!" %
                                    (patient, self.registry))
        for form_name, section_code, cde_code in self._get_field_specs():
            if form_name == 'demographics':
                field_value = self._get_demographic_field(patient, cde_code) # NB. for demographics section isn't used
            else:
                field_value = patient.get_form_value(self.registry.code, form_name, section_code, cde_code)
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
                form_name, section_code, cde_code = spec.strip().split(settings.FORM_SECTION_DELIMITER)
                yield form_name, section_code, cde_code

    def create_form(self):
        from field_lookup import FieldFactory
        adjudication_section = Section.objects.get(code=self.result_fields)
        from dynamic_forms import create_form_class_for_section
        class DummyForm(object):
            def __init__(self):
                self.name = "AdjudicationForm"

        adj_form = DummyForm()
        form_class = create_form_class_for_section(self.registry, adj_form, adjudication_section)
        return form_class()

    def create_decision_form(self):
        from field_lookup import FieldFactory
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
        :return:
        """
        datapoints = []

        def get_cde_display_value(cde_model, stored_value):
            def get_disp(stored_value):
                if cde_model.datatype in ['range']:
                    group_dict = cde_model.pv_group.as_dict()
                    for value_map in group_dict["values"]:
                        if value_map["code"] == stored_value:
                            return value_map["value"]
                    return "Error! stored_value = %s allowed_values = %s" % (stored_value, group_dict)
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
        for form_name, section_code, cde_code in field_map:
            if form_name == 'demographics':
                value = self._get_demographic_field(patient, cde_code)
                label = "Form %s  Field %s" % (form_name, cde_code)
                display_value = str(value)
            else:
                form_model = RegistryForm.objects.get(name=form_name)
                section_model = Section.objects.get(code=section_code)
                cde_model = CommonDataElement.objects.get(code=cde_code)
                label = "Form %s Section %s Field %s" % (form_name, section_model.display_name, cde_model.name)
                value = field_map[(form_name, section_code, cde_code)]
                display_value = get_cde_display_value(cde_model, value)
            datapoints.append(DataPoint(label, display_value))
        return sorted(datapoints,key=lambda datapoint: datapoint.label)

    def create_adjudication_inititiation_form_context(self, patient_model):
        # adjudication_initiation_form, datapoints, users, working_groups = adj_def.create_adjudication_inititiation_form(patient)
        from registry.groups.models import CustomUser, WorkingGroup
        datapoints = self.get_adjudication_form_datapoints(patient_model)
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
                    wg = WorkingGroup.objects.get(registry=self.registry, name=username_or_working_group_name)
                    logger.debug("Adding working group %s" % wg)
                    groups.append(wg)
                except WorkingGroup.DoesNotExist:
                    logger.error("%s is not in %s as a user or a working group so can't be added to the adjudication list for %s" % (username_or_working_group_name, self))

        context = {
            "adjudication_definition": self,
            "patient": patient_model,
            "datapoints": datapoints,
            "users": users,
            "groups": groups,
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

    def get_state(self,  patient):
        try:
            AdjudicationDecision.objects.get(definition=self, patient=patient.pk)
            return AdjudicationState.ADJUDICATED
        except AdjudicationDecision.DoesNotExist:
            requests = [ar for ar in AdjudicationRequest.objects.filter(patient=patient.pk, definition=self)]
            if len(requests) == 0:
                return AdjudicationState.NOT_CREATED
            else:
                return AdjudicationState.UNADJUDICATED



class AdjudicationRequest(models.Model):
    # NB I am using usernames and patient pk here because using caused circular import ...
    username = models.CharField(max_length=80)                  # username of the user  this request directed to
    requesting_username = models.CharField(max_length=80)       # the username of the user requesting this adjudication
    patient = models.IntegerField()           # the patient's pk whose data we are checking
    definition = models.ForeignKey(AdjudicationDefinition)  # the set of fields we are exposing in the request and
                                                    # the result fields to hold the diagnosis vote
    state = models.CharField(max_length=1, default=AdjudicationRequestState.CREATED)




    def send(self):
        # send the email or something ..
        fails = 0
        try:
            self._send_email()
        except Exception, ex:
            logger.error("could not send email for %s: %s" % (self, ex))
            fails += 1

        try:
            self._create_notification()
        except Exception, ex:
            logger.error("could not send internal notification for %s: %s" % (self, ex))
            fails +1

        if fails == 2:
            self.state = AdjudicationRequestState.INVALID
        else:
            self.state = AdjudicationRequestState.REQUESTED

        self.save()

    def _send_email(self):
        email_subject = self._create_email_subject()
        email_body = self._create_email_body()
        sending_user = get_user(self.requesting_username)
        to_user = get_user(self.username)
        if to_user:
            from django.conf import settings
            from django.core.mail import send_mail
            send_mail(email_subject, email_body, settings.DEFAULT_FROM_EMAIL,[to_user.email], fail_silently=False)

    def _create_email_subject(self):
        return "Adjudication Request from %s: %s" % (self.definition.registry.name, self.definition.display_name)

    def _create_email_body(self):

        body = """
            Hello %s User!
            An adjudication request has been assigned to you for %s.
            Please visit %s to complete the adjudication.
            """ % (self.definition.registry.name, self.definition.display_name, self.link)
        return body

    def _create_notification(self):
        from rdrf.notifcations import Notifier
        notification_html = self._create_notification_html()
        notifier = Notifier()
        notifier.send_notification(self.requesting_username, self.username, notification_html)

    def _create_notification_html(self):
        html = "Adjudication Requested for %s - please visit %s" % (self.definition.display_name, self.link)
        return html

    @property
    def link(self):
        reverse('adjudication_request', args=(self.pk,))

    def handle_response(self, adjudication_form_response_data):
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
                        cde_model = CommonDataElement.objects.get(code=code)
                        #todo for now we assume integers
                        field_data[code] = int(data[k])
                except:
                    pass

            if not is_valid(field_data):
                raise AdjudicationError("Adjudication form not filled in completely - please try again")

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
        return True

    def create_adjudication_form(self):
        from registry.patients.models import Patient
        patient_model = Patient.objects.get(pk=self.patient)
        datapoints = self.definition.get_adjudication_form_datapoints(patient_model)
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


class AdjudicationDecision(models.Model):
    definition = models.ForeignKey(AdjudicationDefinition)
    patient = models.IntegerField()           # the patient's pk
    decision_data = models.TextField() # json list  of action cde codes (decision codes)#  to values ( actions)

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


    def perform_actions(self):
        import rdrf
        for action_cde_code, action_value in self.actions:
            pass

    def clean(self):
        definition_action_cde_models = self.definition.action_action_cde_models
        allowed_codes = [ cde.code for cde in definition_action_cde_models]

        for (action_cde_code, value) in self.actions:
            if action_cde_code not in allowed_codes:
                raise ValidationError("Action code %s is not in allowed codes for definition" % action_cde_code)