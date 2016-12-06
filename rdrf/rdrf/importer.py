import logging
from .models import Registry
from .models import RegistryForm
from .models import Section
from .models import CommonDataElement
from .models import CDEPermittedValueGroup
from .models import CDEPermittedValue
from .models import AdjudicationDefinition
from .models import ConsentSection
from .models import ConsentQuestion
from .models import DemographicFields

from registry.groups.models import WorkingGroup

from explorer.models import Query

from django.contrib.auth.models import Group
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ValidationError


from .utils import create_permission

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
            logger.debug("importer.data = %s" % self.data)
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
                            "CDE codes on imported registry do not match those specified in data file: %s" %
                            msg)

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
                logger.debug("existing value codes = %s" % existing_value_codes)
                import_value_codes = set([v["code"] for v in pvg_map["values"]])
                import_missing = existing_value_codes - import_value_codes
                logger.debug("import missing = %s" % import_missing)
                # ensure applied import "wins" - this potentially could affect other
                # registries though
                # but if value sets are inconsistent we can't help it

                for value_code in import_missing:
                    logger.info("checking pvg value code %s" % value_code)
                    try:
                        value = CDEPermittedValue.objects.get(code=value_code, pv_group=pvg)
                        logger.warning("deleting value %s.%s as it is not in import!" % (pvg.code, value.code))
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
                    raise ValidationError("range %s code %s is duplicated" % (pvg.code,
                                                                              value_map["code"]))

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
            logger.debug("importing cde_map %s" % cde_map)
            cde_model, created = CommonDataElement.objects.get_or_create(code=cde_map["code"])

            logger.debug("max_value = %s" % cde_model.max_value)
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

        if created:
            logger.debug("creating registry with code %s from import of %s" %
                         (self.data["code"], self.yaml_data_file))

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

            f.registry = r
            if 'position' in frm_map:
                f.position = frm_map['position']
            f.save()
            logger.info("imported form %s OK" % f.name)
            imported_forms.add(f.name)

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

        if "adjudication_definitions" in self.data:
            self._create_adjudication_definitions(r, self.data["adjudication_definitions"])
            logger.info("imported adjudication definitions OK")
        else:
            logger.info("no adjudications to import")

        self._create_form_permissions(r)
        logger.debug("created form permissions OK")

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

        logger.info("end of import registry objects!")

    def _create_context_form_groups(self, registry):
        from rdrf.models import ContextFormGroup, ContextFormGroupItem

        def default_first(data):
            default = None
            l = []
            for d in data["context_form_groups"]:
                if d["is_default"]:
                    default = d
                else:
                    l.append(d)
            l.insert(0, default)
            for d in l:
                yield d

        def get_form(name):
            for form in registry.forms:
                if form.name == name:
                    return form
            raise ImportError("CFG Error: Form name %s not found in registry" % name)

        for cfg_dict in default_first(self.data):
            if cfg_dict is None:
                continue
            cfg, created = ContextFormGroup.objects.get_or_create(registry=registry, name=cfg_dict["name"])
            cfg.context_type = cfg_dict["context_type"]
            cfg.name = cfg_dict["name"]
            cfg.naming_scheme = cfg_dict["naming_scheme"]
            cfg.is_default = cfg_dict["is_default"]
            if "naming_cde_to_use" in cfg_dict:
                cfg.naming_cde_to_use = cfg_dict["naming_cde_to_use"]

            cfg.save()

            # remove existing context form group items
            for item in cfg.items.all():
                item.delete()

            for form_name in cfg_dict["forms"]:
                registry_form = get_form(form_name)
                cfg_item, created = ContextFormGroupItem.objects.get_or_create(context_form_group=cfg,
                                                                               registry_form=registry_form)
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

    def _create_adjudication_definitions(self, registry_model, adj_def_maps):
        for adj_def_map in adj_def_maps:
            result_fields_section_map = adj_def_map["sections_required"]["results_fields"]
            decision_fields_section_map = adj_def_map[
                "sections_required"]["decision_fields_section"]
            self._create_section_model(result_fields_section_map)
            self._create_section_model(decision_fields_section_map)
            adj_def_model, created = AdjudicationDefinition.objects.get_or_create(
                registry=registry_model, display_name=adj_def_map["display_name"])
            try:
                adj_def_model.display_name = adj_def_map["display_name"]
            except Exception as ex:
                logger.error("display_name not in adjudication definition")

            adj_def_model.fields = adj_def_map["fields"]
            adj_def_model.result_fields = adj_def_map["result_fields"]
            adj_def_model.decision_field = adj_def_map["decision_field"]
            adj_def_model.adjudicator_username = adj_def_map["adjudicator_username"]
            try:
                adj_def_model.adjudicating_users = adj_def_map["adjudicating_users"]
            except Exception as ex:
                logger.error("adjudicating_users not in definition: %s" % ex)

            adj_def_model.save()
            logger.info("created Adjudication Definition %s OK" % adj_def_model)

    def _create_working_groups(self, registry):
        if "working_groups" in self.data:
            working_group_names = self.data["working_groups"]
            logger.debug("working_groups in metadata")
            existing_groups = set([wg for wg in WorkingGroup.objects.filter(registry=registry)])
            new_groups = set([])
            for working_group_name in working_group_names:
                working_group, created = WorkingGroup.objects.get_or_create(
                    name=working_group_name, registry=registry)
                if created:
                    logger.debug("creating new group %s" % working_group_name)
                else:
                    logger.debug("working group %s already exists" % working_group_name)
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
                section_model.information_link = section_dict.get("information_link", section_model.information_link)
                section_model.information_text = section_dict.get("information_text", section_model.information_text)
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
                query.access_group.add(Group.objects.get(id=ag))
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
        from rdrf.models import CdePolicy

        for pol in CdePolicy.objects.filter(registry=registry_model):
            logger.info("deleting old cde policy object for registry %s cde %s" % (registry_model.code, pol.cde.code))
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
                logger.debug("group_names = %s" % group_names)
                groups = [g for g in Group.objects.filter(name__in=group_names)]

                cde_policy = CdePolicy(registry=registry_model,
                                       cde=cde_model,
                                       condition=cde_pol_dict['condition'])
                cde_policy.save()
                cde_policy.groups_allowed = groups
                cde_policy.save()
