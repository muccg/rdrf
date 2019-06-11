import logging
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import CDEPermittedValueGroup
from rdrf.models.definition.models import CDEPermittedValue
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import ConsentQuestion
from rdrf.models.definition.models import DemographicFields

from registry.groups.models import WorkingGroup

from explorer.models import Query

from django.contrib.auth.models import Group
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ValidationError


from rdrf.helpers.utils import create_permission

import yaml
import json

logger = logging.getLogger(__name__)


def _registries_using_cde(cde_code):
    registries = set([])
    for r in Registry.objects.all():
        for form in RegistryForm.objects.filter(registry=r):
            for section_code in form.get_sections():
                try:
                    section = Section.objects.get(code=section_code)
                    for cde_code_in_section in section.get_elements():
                        if cde_code == cde_code_in_section:
                            registries.add(r.code)

                except Section.DoesNotExist:
                    pass

    return [code for code in registries]


class RegistryImportError(Exception):
    pass


class BadDefinitionFile(RegistryImportError):
    pass


class DefinitionFileUnsound(RegistryImportError):
    pass


class DefinitionFileInvalid(RegistryImportError):
    pass


class ConsistencyError(RegistryImportError):
    pass


class QuestionnaireGenerationError(RegistryImportError):
    pass


class ImportState:
    INITIAL = "INITIAL"
    MALFORMED = "MALFORMED"
    LOADED = "LOADED"
    VALID = "VALID"
    INVALID = "INVALID"
    SOUND = "SOUND"   # the registry has been created and check to have no dangling cde codes
    UNSOUND = "UNSOUND"  # the spec contains references to cdes which don't exist
    IMPORTED = "IMPORTED"


class Importer(object):

    def __init__(self):
        self.yaml_data = None
        self.data = None
        self.state = ImportState.INITIAL
        self.errors = []
        self.delete_existing_registry = False
        self.check_validity = True
        self.check_soundness = True
        self.abort_on_conflict = False

    def load_yaml_from_string(self, yaml_string):
        self.yaml_data_file = "yaml string"
        self.data = yaml.load(yaml_string)
        self.state = ImportState.LOADED

    def load_yaml(self, yaml_data_file):
        try:
            self.yaml_data_file = yaml_data_file
            yaml_data = open(yaml_data_file)
            self.data = yaml.load(yaml_data)
            yaml_data.close()
            self.state = ImportState.LOADED
        except Exception as ex:
            self.state = ImportState.MALFORMED
            logger.error("Could not parse yaml data:\n%s\n\nError:\n%s" % (yaml_data_file, ex))
            raise BadDefinitionFile("YAML file is malformed: %s" % ex)

    def create_registry(self):
        if self.state == ImportState.MALFORMED:
            logger.error("Cannot create registry as yaml is not well formed: %s" % self.errors)
            return

        if self.check_validity:
            self._validate()
            if self.state == ImportState.INVALID:
                raise DefinitionFileInvalid(
                    "Definition File does not have correct structure: %s" % self.errors)
        else:
            self.state = ImportState.VALID

        self._create_registry_objects()

        if self.check_soundness:
            self._check_soundness()
            if self.state == ImportState.UNSOUND:
                raise DefinitionFileUnsound(
                    "Definition File refers to CDEs that don't exist: %s" % self.errors)

        else:
            self.state = ImportState.SOUND

    def _validate(self):
        ve = []
        if "code" not in self.data:
            ve.append("invalid: missing 'code' for registry")

        if "name" not in self.data:
            self.errors.append("invalid: missing 'name' for registry")

        if "forms" not in self.data:
            ve.append("invalid: 'forms' list missing")

        if "cdes" not in self.data:
            ve.append("invalid: 'cdes' list missing")

        if "pvgs" not in self.data:
            ve.append("invalid: 'pvgs' list missing")

        if ve:
            self.state = ImportState.INVALID
            self.errors.extend(ve)
        else:
            self.state = ImportState.VALID

    def _check_soundness(self):
        def exists(cde_code):
            try:
                CommonDataElement.objects.get(code=cde_code)
                return True
            except CommonDataElement.DoesNotExist:
                return False

        cde_codes = []
        missing_codes = []
        for frm_map in self.data["forms"]:
            for section_map in frm_map["sections"]:
                cde_codes.extend(section_map["elements"])

        for cde_code in cde_codes:
            if not exists(cde_code):
                missing_codes.append(cde_codes)

        if missing_codes:
            self.state = ImportState.UNSOUND
            self.errors.append(
                "Unsound: The following cde codes do not exist: %s" % missing_codes)
        else:
            registry = Registry.objects.get(code=self.data["code"])
            # Perform some double checking on the imported registry's structure
            self._check_forms(registry)
            self._check_sections(registry)
            self._check_cdes(registry)

            self.state = ImportState.SOUND

    def _check_forms(self, imported_registry):
        # double check the import_registry model instance we've created against
        # the original yaml data
        form_codes_in_db = set([frm.name for frm in RegistryForm.objects.filter(
            registry=imported_registry) if frm.name != imported_registry.generated_questionnaire_name])
        form_codes_in_yaml = set([frm_map["name"] for frm_map in self.data["forms"]])
        if form_codes_in_db != form_codes_in_yaml:
            msg = "in db: %s in yaml: %s" % (form_codes_in_db, form_codes_in_yaml)
            raise RegistryImportError(
                "Imported registry has different forms to yaml file: %s" % msg)

    def _check_sections(self, imported_registry):
        for form in RegistryForm.objects.filter(registry=imported_registry):
            if form.name == imported_registry.generated_questionnaire_name:
                continue
            sections_in_db = set(form.get_sections())
            for section_code in sections_in_db:
                try:
                    Section.objects.get(code=section_code)
                except Section.DoesNotExist:
                    raise RegistryImportError(
                        "Section %s in form %s has not been created?!" %
                        (section_code, form.name))

            yaml_sections = set([])
            for yaml_form_map in self.data["forms"]:
                if yaml_form_map["name"] == form.name:
                    for section_map in yaml_form_map["sections"]:
                        yaml_sections.add(section_map["code"])

            if sections_in_db != yaml_sections:
                msg = "sections in imported reg: %s\nsections in yaml: %s" % (
                    sections_in_db, yaml_sections)
                raise RegistryImportError(
                    "Imported registry has different sections for form %s: %s" %
                    (form.name, msg))

    def _check_cdes(self, imported_registry):
        for form in RegistryForm.objects.filter(registry=imported_registry):
            if form.name == imported_registry.generated_questionnaire_name:
                continue
            for section_code in form.get_sections():
                try:
                    section = Section.objects.get(code=section_code)
                    section_cdes = section.get_elements()
                    imported_section_cdes = set([])
                    for section_cde_code in section_cdes:
                        try:
                            cde_model = CommonDataElement.objects.get(code=section_cde_code)
                            imported_section_cdes.add(cde_model.code)
                        except CommonDataElement.DoesNotExist:
                            raise RegistryImportError(
                                "CDE %s.%s does not exist" %
                                (form.name, section_code, section_cde_code))

                    yaml_section_cdes = set([])
                    for form_map in self.data["forms"]:
                        if form_map["name"] == form.name:
                            for section_map in form_map["sections"]:
                                if section_map["code"] == section.code:
                                    elements = section_map["elements"]
                                    for cde_code in elements:
                                        yaml_section_cdes.add(cde_code)
                    if yaml_section_cdes != imported_section_cdes:
                        db_msg = "in DB %s.%s has cdes %s" % (
                            form.name, section.code, imported_section_cdes)
                        yaml_msg = "in YAML %s.%s has cdes %s" % (
                            form.name, section.code, yaml_section_cdes)
                        msg = "%s\n%s" % (db_msg, yaml_msg)

                        raise RegistryImportError(
                            "CDE codes on imported registry do not match those specified in data file: %s" % msg)

                except Section.DoesNotExist:
                    raise RegistryImportError(
                        "Section %s in form %s has not been created?!" %
                        (section_code, form.name))

    def _create_groups(self, permissible_value_group_maps):
        for pvg_map in permissible_value_group_maps:
            pvg, created = CDEPermittedValueGroup.objects.get_or_create(code=pvg_map["code"])
            pvg.save()
            if not created:
                logger.warning("Import is updating an existing group %s" % pvg.code)
                existing_values = [pv for pv in CDEPermittedValue.objects.filter(pv_group=pvg)]
                existing_value_codes = set([pv.code for pv in existing_values])
                import_value_codes = set([v["code"] for v in pvg_map["values"]])
                import_missing = existing_value_codes - import_value_codes
                # ensure applied import "wins" - this potentially could affect other
                # registries though
                # but if value sets are inconsistent we can't help it

                for value_code in import_missing:
                    logger.info("checking pvg value code %s" % value_code)
                    try:
                        value = CDEPermittedValue.objects.get(code=value_code, pv_group=pvg)
                        logger.warning(
                            "deleting value %s.%s as it is not in import!" %
                            (pvg.code, value.code))
                        value.delete()
                    except CDEPermittedValue.DoesNotExist:
                        logger.info("value does not exist?")

                    except Exception as ex:
                        logger.error("err: %s" % ex)
                        raise

            for value_map in pvg_map["values"]:
                try:
                    value, created = CDEPermittedValue.objects.get_or_create(
                        code=value_map["code"], pv_group=pvg)
                except MultipleObjectsReturned:
                    raise ValidationError(
                        "range %s code %s is duplicated" %
                        (pvg.code, value_map["code"]))

                if not created:
                    if value.value != value_map["value"]:
                        logger.warning("Existing value code %s.%s = '%s'" %
                                       (value.pv_group.code, value.code, value.value))
                        logger.warning("Import value code %s.%s = '%s'" %
                                       (pvg_map["code"], value_map["code"], value_map["value"]))

                    if value.desc != value_map["desc"]:
                        logger.warning("Existing value desc%s.%s = '%s'" %
                                       (value.pv_group.code, value.code, value.desc))
                        logger.warning("Import value desc %s.%s = '%s'" %
                                       (pvg_map["code"], value_map["code"], value_map["desc"]))

                # update the value ...
                value.value = value_map["value"]
                value.desc = value_map["desc"]

                if 'questionnaire_value' in value_map:
                    value.questionnaire_value = value_map['questionnaire_value']

                if 'position' in value_map:
                    value.position = value_map['position']

                value.save()

    def _create_cdes(self, cde_maps):
        for cde_map in cde_maps:
            cde_model, created = CommonDataElement.objects.get_or_create(code=cde_map["code"])

            if not created:
                registries_already_using = _registries_using_cde(cde_model)
                if len(registries_already_using) > 0:
                    logger.warning("Import is modifying existing CDE %s" % cde_model)
                    logger.warning(
                        "This cde is used by the following registries: %s" %
                        registries_already_using)

            for field in cde_map:
                if field not in ["code", "pv_group"]:
                    import_value = cde_map[field]
                    if not created:
                        old_value = getattr(cde_model, field)
                        if old_value != import_value:
                            logger.warning(
                                "import will change cde %s: import value = %s new value = %s" %
                                (cde_model.code, old_value, import_value))

                    setattr(cde_model, field, cde_map[field])
                    # logger.info("cde %s.%s set to [%s]" % (cde_model.code, field, cde_map[field]))

            # Assign value group - pv_group will be empty string is not a range

            if cde_map["pv_group"]:
                try:
                    pvg = CDEPermittedValueGroup.objects.get(code=cde_map["pv_group"])
                    if not created:
                        if cde_model.pv_group != pvg:
                            logger.warning(
                                "import will change cde %s: old group = %s new group = %s" %
                                (cde_model.code, cde_model.pv_group, pvg))

                    cde_model.pv_group = pvg
                except CDEPermittedValueGroup.DoesNotExist as ex:
                    raise ConsistencyError("Assign of group %s to imported CDE %s failed: %s" %
                                           (cde_map["pv_group"], cde_model.code, ex))

            cde_model.save()
            # logger.info("updated cde %s" % cde_model)

    def _create_generic_sections(self, generic_section_maps):
        logger.info("creating generic sections")
        for section_map in generic_section_maps:
            logger.info("importing generic section map %s" % section_map)
            s, created = Section.objects.get_or_create(code=section_map["code"])
            s.code = section_map["code"]
            s.display_name = section_map["display_name"]
            s.elements = ",".join(section_map["elements"])
            s.allow_multiple = section_map["allow_multiple"]
            if "questionnaire_help" in section_map:
                s.questionnaire_help = section_map["questionnaire_help"]
            s.extra = section_map["extra"]
            s.save()
            logger.info("saved generic section %s" % s.code)

    def _create_patient_data_section(self, section_map):
        if section_map:
            s, created = Section.objects.get_or_create(code=section_map["code"])
            s.code = section_map["code"]
            s.display_name = section_map["display_name"]
            s.elements = ",".join(section_map["elements"])
            s.allow_multiple = section_map["allow_multiple"]
            if "questionnaire_help" in section_map:
                s.questionnaire_help = section_map["questionnaire_help"]
            s.extra = section_map["extra"]
            s.save()
            logger.info("saved patient data section  %s" % s.code)
            return s
        else:
            return None

    def _create_section_model(self, section_map):
        s, created = Section.objects.get_or_create(code=section_map["code"])
        s.code = section_map["code"]
        s.display_name = section_map["display_name"]
        s.elements = ",".join(section_map["elements"])
        s.allow_multiple = section_map["allow_multiple"]
        s.extra = section_map["extra"]
        if "questionnaire_help" in section_map:
            s.questionnaire_help = section_map["questionnaire_help"]
        s.save()
        logger.info("imported section %s OK" % s.code)

    def _check_metadata_json(self, metadata_json):
        if not metadata_json:
            # no metadata - OK
            return True
        try:
            metadata = json.loads(metadata_json)
            if not isinstance(metadata, dict):
                raise ValueError("Not a dictionary")
            return True
        except ValueError as verr:
            logger.info("invalid metadata ( should be json dictionary): %s Error %s" %
                        (metadata_json, verr))
            return False

    def _create_registry_objects(self):
        self._create_groups(self.data["pvgs"])
        logger.info("imported pvgs OK")
        self._create_cdes(self.data["cdes"])
        logger.info("imported cdes OK")
        if "generic_sections" in self.data:
            self._create_generic_sections(self.data["generic_sections"])

        logger.info("imported generic sections OK")

        r, created = Registry.objects.get_or_create(code=self.data["code"])

        original_forms = set([f.name for f in RegistryForm.objects.filter(registry=r)])
        imported_forms = set([])
        r.code = self.data["code"]
        if "desc" in self.data:
            r.desc = self.data["desc"]
        r.name = self.data["name"]

        if "REGISTRY_VERSION" in self.data:
            r.version = self.data["REGISTRY_VERSION"]
        else:
            r.version = ""  # old style no version

        r.splash_screen = self.data["splash_screen"]

        if "patient_data_section" in self.data:
            patient_data_section_map = self.data["patient_data_section"]
            if patient_data_section_map:
                patient_data_section = self._create_patient_data_section(
                    patient_data_section_map)
                r.patient_data_section = patient_data_section

        if "metadata_json" in self.data:
            metadata_json = self.data["metadata_json"]
            if self._check_metadata_json(metadata_json):
                r.metadata_json = self.data["metadata_json"]
            else:
                raise DefinitionFileInvalid(
                    "Invalid JSON for registry metadata ( should be a json dictionary")

        r.save()
        logger.info("imported registry object OK")

        for frm_map in self.data["forms"]:
            logger.info("starting import of form map %s" % frm_map)

            sections = ",".join([section_map["code"] for section_map in frm_map["sections"]])

            # First create section models so the form save validation passes
            self._create_form_sections(frm_map)

            f, created = RegistryForm.objects.get_or_create(registry=r, name=frm_map["name"],
                                                            defaults={'sections': sections})
            if not created:
                f.sections = sections

            permission_code_name = "form_%s_is_readonly" % f.id
            permission_name = "Form '%s' is readonly (%s)" % (f.name, f.registry.code.upper())
            create_permission("rdrf", "registryform", permission_code_name, permission_name)

            f.name = frm_map["name"]
            if "header" in frm_map:
                f.header = frm_map["header"]
            else:
                f.header = ""
            if "questionnaire_display_name" in frm_map:
                f.questionnaire_display_name = frm_map["questionnaire_display_name"]
            f.is_questionnaire = frm_map["is_questionnaire"]
            if "questionnaire_questions" in frm_map:
                f.questionnaire_questions = frm_map["questionnaire_questions"]

            if "applicability_condition" in frm_map:
                f.applicability_condition = frm_map["applicability_condition"]

            f.registry = r
            if 'position' in frm_map:
                f.position = frm_map['position']
            f.save()
            logger.info("imported form %s OK" % f.name)
            imported_forms.add(f.name)

        extra_forms = original_forms - imported_forms
        # if there are extra forms in the original set, we delete them
        for form_name in extra_forms:
            try:
                extra_form = RegistryForm.objects.get(registry=r, name=form_name)
                assert form_name not in imported_forms
                logger.info("deleting extra form not present in import file: %s" % form_name)
                extra_form.delete()
            except RegistryForm.DoesNotExist:
                # shouldn't happen but if so just continue
                pass

        self._create_working_groups(r)
        # create consent sections if they exist
        self._create_consent_sections(r)
        # generate the questionnaire for this reqistry
        try:
            r.generate_questionnaire()
        except Exception as ex:
            raise QuestionnaireGenerationError(str(ex))

        self._create_form_permissions(r)
        if "demographic_fields" in self.data:
            self._create_demographic_fields(self.data["demographic_fields"])
            logger.info("demographic field definitions OK ")
        else:
            logger.info("no demographic_fields to import")

        if "complete_fields" in self.data:
            self._create_complete_form_fields(r, self.data["complete_fields"])
            logger.info("complete field definitions OK ")
        else:
            logger.info("no complete field definitions to import")

        if "reports" in self.data:
            self._create_reports(self.data["reports"])
            logger.info("complete reports OK ")
        else:
            logger.info("no reports to import")

        if "cde_policies" in self.data:
            self._create_cde_policies(r)
            logger.info("imported cde policies OK")
        else:
            logger.info("no cde policies to import")

        if "context_form_groups" in self.data:
            self._create_context_form_groups(r)
            logger.info("imported context form groups OK")
        else:
            logger.info("no context form groups to import")

        if "email_notifications" in self.data:
            self._create_email_notifications(r)
            logger.info("imported email notifications OK")

        if "consent_rules" in self.data:
            self._create_consent_rules(r)
            logger.info("imported consent rules OK")

        if "surveys" in self.data:
            self._create_surveys(r)
            logger.info("imported surveys OK")

        if "reviews" in self.data:
            self._create_reviews(r)
            logger.info("imported reviews OK")

        logger.info("end of import registry objects!")

    def _create_consent_rules(self, registry_model):
        from rdrf.models.definition.models import ConsentRule
        ConsentRule.objects.filter(registry=registry_model).delete()
        logger.info("Deleted existing consent rules ...")
        for consent_rule_dict in self.data["consent_rules"]:
            cr = ConsentRule()
            cr.registry = registry_model
            cr.enabled = consent_rule_dict["enabled"]
            cr.capability = consent_rule_dict["capability"]
            logger.info("cap = %s" % cr.capability)
            cr.user_group = Group.objects.get(name=consent_rule_dict["user_group"])
            consent_section_code = consent_rule_dict["consent_section_code"]
            logger.info("consent section code = %s" % consent_section_code)

            consent_question_code = consent_rule_dict["consent_question_code"]
            logger.info("consent question code = %s" % consent_question_code)
            consent_section_model = ConsentSection.objects.get(registry=registry_model,
                                                               code=consent_section_code)
            consent_question_model = ConsentQuestion.objects.get(section=consent_section_model,
                                                                 code=consent_question_code)

            cr.consent_question = consent_question_model
            cr.save()
            logger.info("Imported Consent Rule for %s %s" % (cr.capability,
                                                             cr.user_group))

    def _create_surveys(self, registry_model):
        from rdrf.models.proms.models import Survey
        from rdrf.models.proms.models import SurveyQuestion
        from rdrf.models.proms.models import Precondition
        Survey.objects.filter(registry=registry_model).delete()
        logger.info("Deleted existing surveys ...")
        for survey_dict in self.data["surveys"]:
            logger.info("survey dict = %s" % survey_dict)
            survey_model = Survey(registry=registry_model)
            survey_model.name = survey_dict["name"]
            survey_model.display_name = survey_dict.get("display_name", "")
            survey_model.is_followup = survey_dict.get("is_followup", False)
            survey_model.save()
            logger.info("saved survey_model %s" % survey_model.name)

            for sq in survey_dict["questions"]:
                sq_model = SurveyQuestion(survey=survey_model)
                sq_model.position = sq["position"]
                sq_model.instruction = sq.get("instruction", None)
                sq_model.copyright_text = sq.get("copyright_text", None)
                sq_model.source = sq.get("source", None)
                cde_model = CommonDataElement.objects.get(code=sq["cde"])
                sq_model.cde = cde_model
                sq_model.save()
                logger.info("saved sq %s" % sq_model)

                if sq["precondition"]:
                    precondition_cde_model = CommonDataElement.objects.get(code=sq["precondition"]["cde"])
                    precondition_model = Precondition(cde=precondition_cde_model, survey=survey_model)
                    precondition_model.value = sq["precondition"]["value"]
                    precondition_model.save()
                    sq_model.precondition = precondition_model
                sq_model.save()
                logger.info("Imported survey question %s" % sq_model.cde.code)
                if sq_model.precondition:
                    logger.info("Imported precondition: %s = %s" % (sq_model.precondition.cde.code,
                                                                    sq_model.precondition.value))
            logger.info("Imported Survey %s" % survey_model.name)

    def _create_reviews(self, registry_model):
        from rdrf.models.definition.review_models import Review
        from rdrf.models.definition.review_models import ReviewItem

        def goc(klass, **kwargs):
            instance, created = klass.objects.get_or_create(**kwargs)
            return instance

        review_codes = [r["code"] for r in self.data["reviews"]]

        for review_model in Review.objects.filter(registry=registry_model):
            if review_model.code not in review_codes:
                review_model.delete()

        for review_dict in self.data["reviews"]:
            review_model = goc(Review,
                               registry=registry_model,
                               code=review_dict["code"])

            review_model.name = review_dict["name"]
            review_model.save()

            # delete items no longer in definition
            existing_item_codes = set([ri.code for ri in review_model.items.all()])
            imported_item_codes = set([rd["code"] for rd in review_dict["items"]])
            items_to_delete = existing_item_codes - imported_item_codes
            ReviewItem.objects.filter(review=review_model,
                                      code__in=items_to_delete).delete()

            # now update/create items
            for item_dict in review_dict["items"]:
                review_item = goc(ReviewItem,
                                  review=review_model,
                                  code=item_dict["code"])
                review_item.category = item_dict["category"]
                review_item.name = item_dict["name"]
                review_item.position = item_dict["position"]
                review_item.item_type = item_dict["item_type"]
                review_item.save()

                if item_dict["form"]:
                    form_model = RegistryForm.objects.get(registry=registry_model,
                                                          name=item_dict["form"])
                    review_item.form = form_model
                if item_dict["section"]:
                    section_model = Section.objects.get(code=item_dict["section"])
                    review_item.section = section_model

                review_item.save()

    def _create_email_notifications(self, registry):
        from rdrf.models.definition.models import EmailNotification
        from rdrf.models.definition.models import EmailTemplate
        our_registry_tuple_list = [(registry.pk,)]
        # delete non-shared templates in use by this registry

        def non_shared(template_model):
            using_regs = [
                x for x in template_model.emailnotification_set.all().values_list('registry__pk')]
            if using_regs == our_registry_tuple_list:
                return True

        templates_to_delete = set([t.id for t in EmailTemplate.objects.all() if non_shared(t)])

        EmailTemplate.objects.filter(id__in=templates_to_delete).delete()
        EmailNotification.objects.filter(registry=registry).delete()

        for en_dict in self.data["email_notifications"]:
            en = EmailNotification(registry=registry)
            en.description = en_dict["description"]
            en.email_from = en_dict["email_from"]
            en.recipient = en_dict["recipient"]
            en.disabled = en_dict["disabled"]
            en.save()
            if en_dict["group_recipient"]:
                auth_group = Group.objects.get(name=en_dict["group_recipient"])
                en.group_recipient = auth_group
            for template_dict in en_dict["email_templates"]:
                et = EmailTemplate()
                et.language = template_dict["language"]
                et.description = template_dict["description"]
                et.subject = template_dict["subject"]
                et.body = template_dict["body"]
                et.save()
                en.email_templates.add(et)
                en.save()

    def _create_form_sections(self, frm_map):
        for section_map in frm_map["sections"]:
            s, created = Section.objects.get_or_create(code=section_map["code"])
            s.code = section_map["code"]
            s.display_name = section_map["display_name"]
            if "questionnaire_display_name" in section_map:
                s.questionnaire_display_name = section_map["questionnaire_display_name"]
            s.elements = ",".join(section_map["elements"])
            s.allow_multiple = section_map["allow_multiple"]
            s.extra = section_map["extra"]
            if "questionnaire_help" in section_map:
                s.questionnaire_help = section_map["questionnaire_help"]
            s.save()
            logger.info("imported section %s OK" % s.code)

    def _create_context_form_groups(self, registry):
        from rdrf.models.definition.models import ContextFormGroup, ContextFormGroupItem

        def default_first(data):
            default = None
            lst = []
            for d in data["context_form_groups"]:
                if d["is_default"]:
                    default = d
                else:
                    lst.append(d)
            lst.insert(0, default)
            for d in lst:
                yield d

        def get_form(name):
            for form in registry.forms:
                if form.name == name:
                    return form
            raise ImportError("CFG Error: Form name %s not found in registry" % name)

        for cfg_dict in default_first(self.data):
            if cfg_dict is None:
                continue
            cfg, created = ContextFormGroup.objects.get_or_create(
                registry=registry, name=cfg_dict["name"])
            cfg.context_type = cfg_dict["context_type"]
            cfg.name = cfg_dict["name"]
            cfg.naming_scheme = cfg_dict["naming_scheme"]
            cfg.is_default = cfg_dict["is_default"]
            if "naming_cde_to_use" in cfg_dict:
                cfg.naming_cde_to_use = cfg_dict["naming_cde_to_use"]
            if "ordering" in cfg_dict:
                cfg.ordering = cfg_dict["ordering"]

            cfg.save()

            # remove existing context form group items
            for item in cfg.items.all():
                item.delete()

            for form_name in cfg_dict["forms"]:
                registry_form = get_form(form_name)
                cfg_item, created = ContextFormGroupItem.objects.get_or_create(
                    context_form_group=cfg, registry_form=registry_form)
                cfg_item.save()

            logger.info("imported cfg %s" % cfg.name)

    def _create_form_permissions(self, registry):
        if "forms_allowed_groups" in self.data:
            d = self.data["forms_allowed_groups"]
            for form_name in d:
                form_model = RegistryForm.objects.get(name=form_name, registry=registry)
                groups_allowed = d[form_name]
                for group_name in groups_allowed:
                    g, created = Group.objects.get_or_create(name=group_name)
                    if created:
                        g.save()
                    form_model.groups_allowed.add(g)
                    form_model.save()

    def _create_working_groups(self, registry):
        if "working_groups" in self.data:
            working_group_names = self.data["working_groups"]
            existing_groups = set([wg for wg in WorkingGroup.objects.filter(registry=registry)])
            new_groups = set([])
            for working_group_name in working_group_names:
                working_group, created = WorkingGroup.objects.get_or_create(
                    name=working_group_name, registry=registry)
                working_group.save()
                new_groups.add(working_group)

            groups_to_unlink = existing_groups - new_groups
            for wg in groups_to_unlink:
                logger.info("deleting delete()working group %s for %s registry import" %
                            (wg.name, registry.name))
                # if we delete the group the patients get deleted .. todo need to confirm
                # behaviour
                wg.registry = None
                wg.save()

    def _create_consent_sections(self, registry):
        if "consent_sections" in self.data:
            for section_dict in self.data["consent_sections"]:
                code = section_dict["code"]
                section_label = section_dict["section_label"]
                section_model, created = ConsentSection.objects.get_or_create(
                    code=code, registry=registry, defaults={'section_label': section_label})
                section_model.section_label = section_label
                section_model.information_link = section_dict.get(
                    "information_link", section_model.information_link)
                section_model.information_text = section_dict.get(
                    "information_text", section_model.information_text)
                section_model.applicability_condition = section_dict["applicability_condition"]
                if "validation_rule" in section_dict:
                    section_model.validation_rule = section_dict['validation_rule']
                section_model.save()
                for question_dict in section_dict["questions"]:
                    question_code = question_dict["code"]
                    question_position = question_dict["position"]
                    question_label = question_dict["question_label"]
                    if "questionnaire_label" in question_dict:
                        questionnaire_label = question_dict["questionnaire_label"]
                    else:
                        questionnaire_label = ""

                    if "instructions" in question_dict:
                        instructions = question_dict["instructions"]
                    else:
                        instructions = ""

                    question_model, created = ConsentQuestion.objects.get_or_create(
                        code=question_code, section=section_model)
                    question_model.position = question_position
                    question_model.question_label = question_label
                    question_model.instructions = instructions
                    question_model.questionnaire_label = questionnaire_label
                    question_model.save()

    def _create_demographic_fields(self, data):
        for d in data:
            logger.info("creating demographic fields ..")
            logger.info("d = %s" % d)
            registry_obj = Registry.objects.get(code=d["registry"])
            group_obj, created = Group.objects.get_or_create(name=d["group"])
            if created:
                logger.info("created Group %s" % group_obj)
                group_obj.save()

            demo_field, created = DemographicFields.objects.get_or_create(
                registry=registry_obj, group=group_obj, field=d["field"])
            demo_field.hidden = d["hidden"]
            demo_field.readonly = d["readonly"]
            demo_field.save()

    def _create_complete_form_fields(self, registry_model, data):
        for d in data:
            form = RegistryForm.objects.get(name=d["form_name"], registry=registry_model)
            for cde_code in d["cdes"]:
                form.complete_form_cdes.add(CommonDataElement.objects.get(code=cde_code))
            form.save()

    def _create_reports(self, data):
        for d in data:
            registry_obj = Registry.objects.get(code=d["registry"])
            query, created = Query.objects.get_or_create(
                registry=registry_obj, title=d["title"])
            for ag in d["access_group"]:
                group, created = Group.objects.get_or_create(name=ag)
                if created:
                    group.save()
                query.access_group.add(group)
            query.description = d["description"]
            query.mongo_search_type = d["mongo_search_type"]
            query.sql_query = d["sql_query"]
            query.collection = d["collection"]
            query.criteria = d["criteria"]
            query.projection = d["projection"]
            query.aggregation = d["aggregation"]
            query.created_by = d["created_by"]
            query.created_at = d["created_at"]
            query.save()

    def _create_cde_policies(self, registry_model):
        from rdrf.models.definition.models import CdePolicy

        for pol in CdePolicy.objects.filter(registry=registry_model):
            logger.info(
                "deleting old cde policy object for registry %s cde %s" %
                (registry_model.code, pol.cde.code))
            pol.delete()

        if "cde_policies" in self.data:
            cde_policies = self.data['cde_policies']
            for cde_pol_dict in cde_policies:
                try:
                    cde_model = CommonDataElement.objects.get(code=cde_pol_dict["cde_code"])
                except CommonDataElement.DoesNotExist:
                    logger.error("cde code does not exist for cde policy %s" % cde_pol_dict)
                    continue

                group_names = cde_pol_dict["groups_allowed"]
                groups = [g for g in Group.objects.filter(name__in=group_names)]

                cde_policy = CdePolicy(registry=registry_model,
                                       cde=cde_model,
                                       condition=cde_pol_dict['condition'])
                cde_policy.save()
                cde_policy.groups_allowed.set(groups)
                cde_policy.save()
