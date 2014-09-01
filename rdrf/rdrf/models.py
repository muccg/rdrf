from django.db import models
import logging
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse


from positions.fields import PositionField
import string


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


class Registry(models.Model):
    class Meta:
        verbose_name_plural = "registries"

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10)
    desc = models.TextField()
    splash_screen = models.TextField()
    version = models.CharField(max_length=20, blank=True)

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

    def _generated_section_questionnaire_code(self, section_model):
        return self.questionnaire_section_prefix + section_model.code

    def generate_questionnaire(self):
        logger.info("starting to generate questionnaire for %s" % self)
        if not new_style_questionnaire(self):
            logger.info("This reqistry is not exposing any questionnaire questions - nothing to do")
            return
        questions = []
        for form in self.forms:
            questions.extend(form.questionnaire_list)

        from collections import OrderedDict
        section_map = OrderedDict()

        for sectioncode_dot_cdecode in questions:
            section_code, cde_code = sectioncode_dot_cdecode.split(".") #  eg sec01.cde02 --> [sec01, cde02]
            if section_code in section_map:
                section_map[section_code].append(cde_code)
            else:
                section_map[section_code] = [cde_code]

        generated_questionnaire_form_name = self.generated_questionnaire_name
        generated_questionnaire_form, created  = RegistryForm.objects.get_or_create(registry=self, name=generated_questionnaire_form_name)

        if not created:
            # get rid of any existing generated sections
            for section in Section.objects.all():
                if section.code.startswith(self.questionnaire_section_prefix):
                    section.delete()

        generated_questionnaire_form.registry = self
        generated_questionnaire_form.is_questionnaire = True
        generated_questionnaire_form.save()
        logger.info("created questionnaire form %s" % generated_questionnaire_form.name)
        generated_section_codes = []

        for section_code in section_map:
            # generate sections
            try:
                original_section = Section.objects.get(code=section_code)
            except Section.DoesNotExist:
                raise InvalidQuestionnaireError("section with code %s doesn't exist!" % section_code)

            qsection = Section()
            qsection.code = self._generated_section_questionnaire_code(original_section)
            qsection.display_name = original_section.display_name
            qsection.allow_multiple= False
            qsection.extra  = 0
            qsection.elements = ",".join([ cde_code for cde_code in section_map[section_code] ])
            qsection.save()
            logger.info("created section %s containing cdes %s" % (qsection.code, qsection.elements))
            generated_section_codes.append(qsection.code)


        consent_section = self._get_consent_section()
        patient_info_section = self._get_patient_info_section()

        generated_questionnaire_form.sections = consent_section + "," + patient_info_section + "," + ",".join(generated_section_codes)
        generated_questionnaire_form.save()

        logger.info("finished generating questionnaire for registry %s" % self.code)

    def _get_consent_section(self):
        return "GenericPatientConsent"

    def _get_patient_info_section(self):
        return "PatientData"
    
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
        return [ f for f in RegistryForm.objects.filter(registry=self) ]

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
                elements = []
                for element_code in section.get_elements():
                    question_code = section.code + "." + element_code
                    in_questionnaire = question_code in qcodes
                    elements.append([element_code, in_questionnaire]) # NB. We capture each cde code in a section and whether it is used in the questionnaire

                section_dict["elements"] = elements # codes + whether in questionnaire
                form_dict["sections"].append(section_dict)
            s["forms"].append(form_dict)

        return s

    @structure.setter
    def structure(self, new_structure):
        """
        Update this registry to the new structure
        """
        self._check_structure(new_structure)

        logger.info("updating structure for registry %s pk %s" % ( self, self.pk))
        logger.info("old structure = %s" % self.structure)
        logger.info("new structure = %s" % new_structure)

        original_forms = [ f for f in self.forms if f.name != f.registry.generated_questionnaire_name ]  # don't include generated form
        logger.info("original forms = %s" % original_forms)

        self.name = new_structure["name"]
        self.code = new_structure["code"]
        self.desc = new_structure["desc"]
        self.version = new_structure["version"]
        self.save()

        new_forms = []
        for form_dict in new_structure["forms"]:
            form_name = form_dict["name"]
            form, created = RegistryForm.objects.get_or_create(name=form_name, registry=self)
            form.is_questionnaire = form_dict["is_questionnaire"]
            form.position = form_dict["position"]
            questionnaire_questions = []
            form.sections = ",".join([ s["code"] for s in form_dict["sections"]])
            new_forms.append(form)
            # update sections
            for section_dict in form_dict["sections"]:
                section, created = Section.objects.get_or_create(code=section_dict["code"])
                section.display_name = section_dict["display_name"]
                section.allow_multiple = section_dict["allow_multiple"]
                section.extra = section_dict["extra"]
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

    def _check_structure(self, structure):
        # raise error if structure not valid

        for k in [ "name", "code", "version", "forms"]:
            if not k in structure:
                raise InvalidStructureError("Missing key: %s" % k)
        for form_dict in structure["forms"]:
            for k in ["name", "is_questionnaire", "position","sections"]:
                if not k in form_dict:
                    raise InvalidStructureError("Form dict %s missing key %s" % (form_dict, k))

            form_name = form_dict["name"]

            for section_dict in form_dict["sections"]:
                for k in ["code", "display_name", "allow_multiple", "extra", "elements"]:
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

    return [("UNUSED","UNUSED"), ("USED", "USED")]

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

    def members(self):
        return [v.code for v in CDEPermittedValue.objects.filter(pv_group=self).order_by('position')]

    def __unicode__(self):
        members = self.members()
        return "PVG %s containing %d items" % (self.code, len(self.members()))

class CDEPermittedValue(models.Model):
    code = models.CharField(max_length=30, primary_key=True)
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
        return "Memeber of %s" % (self.pv_group.code)


class CommonDataElement(models.Model):
    code = models.CharField(max_length=30, primary_key=True)
    name = models.CharField(max_length=250, blank=False, help_text="Label for field in form")
    desc = models.TextField(blank=True, help_text="origin of field")
    datatype = models.CharField(max_length=50, help_text="type of field")
    instructions = models.TextField(blank=True, help_text="Used to indicate help text for field")
    pv_group = models.ForeignKey(CDEPermittedValueGroup, null=True, blank=True, help_text="If a range, indicate the Permissible Value Group")
    allow_multiple = models.BooleanField(default=False, help_text="If a range, indicate whether multiple selections allowed")
    max_length = models.IntegerField(blank=True,null=True, help_text="Length of field - only used for character fields")
    max_value= models.IntegerField(blank=True, null=True, help_text="Only used for numeric fields")
    min_value= models.IntegerField(blank=True, null=True, help_text="Only used for numeric fields")
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


class RegistryFormManager(models.Manager):
    def get_by_registry(self, registry):
        return self.model.objects.filter(registry__id__in = registry)


class RegistryForm(models.Model):
    """
    A representation of a form ( a bunch of sections)
    """
    registry = models.ForeignKey(Registry)
    name = models.CharField(max_length=80)
    sections = models.TextField(help_text="Comma-separated list of sections")
    objects = RegistryFormManager()
    is_questionnaire = models.BooleanField(default=False,help_text="Check if this form is questionnaire form for it's registry")
    position = PositionField(collection='registry')
    questionnaire_questions = models.TextField(blank=True,help_text="Comma-separated list of sectioncode.cdecodes for questionnnaire")

    def __unicode__(self):
        return "%s %s Form comprising %s" % (self.registry, self.name, self.sections)

    def get_sections(self):
        import string
        return map(string.strip,self.sections.split(","))

    @property
    def questionnaire_list(self):
        """
        returns a list of sectioncode.cde_code strings
        E.g. [ "sectionA.cdecode23", "sectionB.code100" , ...]
        """
        return filter(lambda s : len(s) > 0 ,map(string.strip, self.questionnaire_questions.split(",")))


    @property
    def section_models(self):
        return [ section_model for section_model in Section.objects.filter(code__in=self.get_sections()) ]

    def in_questionnaire(self, section_code, cde_code):
        questionnaire_code = "%s.%s" % (section_code, cde_code)
        return questionnaire_code in self.questionnaire_list

class Section(models.Model):
    """
    A group of fields that appear on a form as a unit
    """
    code = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100)
    elements = models.TextField()
    allow_multiple = models.BooleanField(default=False, help_text="Allow extra items to be added")
    extra = models.IntegerField(blank=True,null=True, help_text="Extra rows to show if allow_multiple checked")

    def __unicode__(self):
        return "Section %s comprising %s" % (self.code, self.elements)

    def get_elements(self):
        import string
        return map(string.strip,self.elements.split(","))

    @property
    def cde_models(self):
        #return [ CommonDataElement.objects.get(code=c) for c in self.get_elements() ]
        return [ cde for cde in CommonDataElement.objects.filter(code__in=self.get_elements()) ]

    def clean(self):
        for element in self.get_elements():
            try:
                cde = CommonDataElement.objects.get(code=element)
            except CommonDataElement.DoesNotExist:
                raise ValidationError("section %s refers to CDE with code %s which doesn't exist" % (self.display_name, element))

        if self.code.count(" ") > 0:
            raise  ValidationError("Section %s code '%s' contains spaces" % (self.display_name, self.code))


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
    patient_id = models.IntegerField(blank=True,null=True,help_text="The id of the patient created from this response, if any")

    def __str__(self):
        return "%s (%s)" % (self.registry, self.processed)


def appears_in(cde,registry,registry_form,section):
    if section.code not in registry_form.get_sections():
        return False
    elif registry_form.name not in [ f.name for f in RegistryForm.objects.filter(registry=registry)]:
        return False
    else:
        return cde.code in section.get_elements()

