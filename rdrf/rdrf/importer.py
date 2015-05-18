import logging
from models import Registry
from models import RegistryForm
from models import Section
from models import CommonDataElement
from models import CDEPermittedValueGroup
from models import CDEPermittedValue
from models import AdjudicationDefinition
from models import ConsentSection
from models import ConsentQuestion
from models import DemographicFields

from registry.groups.models import WorkingGroup
from django.contrib.auth.models import Group
import yaml
import json

logger = logging.getLogger("registry_log")


def _registries_using_cde(cde_code):
    registries = set([])
    for r in Registry.objects.all():
        for form in RegistryForm.objects.filter(registry=r):
            for section_code in form.get_sections():
                try:
                    section = Section.objects.get(code=section_code)
                except Section.DoesNotExist:
                    pass

                for cde_code_in_section in section.get_elements():
                    if cde_code == cde_code_in_section:
                        registries.add(r.code)

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
                raise DefinitionFileInvalid("Definition File does not have correct structure: %s" % self.errors)
        else:
            self.state = ImportState.VALID

        self._create_registry_objects()

        if self.check_soundness:
            self._check_soundness()
            if self.state == ImportState.UNSOUND:
                raise DefinitionFileUnsound("Definition File refers to CDEs that don't exist: %s" % self.errors)

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
            self.errors.append("Unsound: The following cde codes do not exist: %s" % missing_codes)
        else:
            registry = Registry.objects.get(code=self.data["code"])
            # Perform some double checking on the imported registry's structure
            self._check_forms(registry)
            self._check_sections(registry)
            self._check_cdes(registry)

            self.state = ImportState.SOUND

    def _check_forms(self, imported_registry):
        # double check the import_registry model instance we've created against the original yaml data
        form_codes_in_db = set([frm.name for frm in RegistryForm.objects.filter(
            registry=imported_registry) if frm.name != imported_registry.generated_questionnaire_name])
        form_codes_in_yaml = set([frm_map["name"] for frm_map in self.data["forms"]])
        if form_codes_in_db != form_codes_in_yaml:
            msg = "in db: %s in yaml: %s" % (form_codes_in_db, form_codes_in_yaml)
            raise RegistryImportError("Imported registry has different forms to yaml file: %s" % msg)

    def _check_sections(self, imported_registry):
        for form in RegistryForm.objects.filter(registry=imported_registry):
            if form.name == imported_registry.generated_questionnaire_name:
                continue
            sections_in_db = set(form.get_sections())
            for section_code in sections_in_db:
                try:
                    Section.objects.get(code=section_code)
                except Section.DoesNotExist:
                    raise RegistryImportError("Section %s in form %s has not been created?!" % (section_code, form.name))

            yaml_sections = set([])
            for yaml_form_map in self.data["forms"]:
                if yaml_form_map["name"] == form.name:
                    for section_map in yaml_form_map["sections"]:
                        yaml_sections.add(section_map["code"])

            if sections_in_db != yaml_sections:
                msg = "sections in imported reg: %s\nsections in yaml: %s" % (sections_in_db, yaml_sections)
                raise RegistryImportError("Imported registry has different sections for form %s: %s" % (form.name, msg))

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
                                "CDE %s.%s does not exist" % (form.name, section_code, section_cde_code))

                    yaml_section_cdes = set([])
                    for form_map in self.data["forms"]:
                        if form_map["name"] == form.name:
                            for section_map in form_map["sections"]:
                                if section_map["code"] == section.code:
                                    elements = section_map["elements"]
                                    for cde_code in elements:
                                        yaml_section_cdes.add(cde_code)
                    if yaml_section_cdes != imported_section_cdes:
                        db_msg = "in DB %s.%s has cdes %s" % (form.name, section.code, imported_section_cdes)
                        yaml_msg = "in YAML %s.%s has cdes %s" % (form.name, section.code, yaml_section_cdes)
                        msg = "%s\n%s" % (db_msg, yaml_msg)

                        raise RegistryImportError(
                            "CDE codes on imported registry do not match those specified in data file: %s" % msg)

                except Section.DoesNotExist:
                    raise RegistryImportError("Section %s in form %s has not been created?!" % (section_code, form.name))

    def _create_groups(self, permissible_value_group_maps):
        for pvg_map in permissible_value_group_maps:
            pvg, created = CDEPermittedValueGroup.objects.get_or_create(code=pvg_map["code"])
            pvg.save()
            # logger.info("imported permissible value group %s" % pvg)
            if not created:
                logger.warning("Import is updating an existing group %s" % pvg.code)
                existing_values = [pv for pv in CDEPermittedValue.objects.filter(pv_group=pvg)]
                existing_value_codes = set([pv.code for pv in existing_values])
                import_value_codes = set([v["code"] for v in pvg_map["values"]])
                import_extra = import_value_codes - existing_value_codes
                import_missing = existing_value_codes - import_value_codes
                # ensure applied import "wins" - this potentially could affect other
                # registries though
                # but if value sets are inconsistent we can't help it

                for value_code in import_missing:
                    value = CDEPermittedValue.objects.get(code=value_code)
                    logger.warning("deleting value %s.%s as it is not in import!" % (pvg.code, value.code))
                    value.delete()

            for value_map in pvg_map["values"]:
                value, created = CDEPermittedValue.objects.get_or_create(code=value_map["code"], pv_group=pvg)
                if not created:
                    if value.value != value_map["value"]:
                        logger.warning("Existing value code %s.%s = '%s'" % (value.pv_group.code, value.code, value.value))
                        logger.warning("Import value code %s.%s = '%s'" %
                                       (pvg_map["code"], value_map["code"], value_map["value"]))

                    if value.desc != value_map["desc"]:
                        logger.warning("Existing value desc%s.%s = '%s'" % (value.pv_group.code, value.code, value.desc))
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
                # logger.info("imported value %s" % value)

    def _create_cdes(self, cde_maps):
        for cde_map in cde_maps:
            logger.debug("importing cde_map %s" % cde_map)
            cde_model, created = CommonDataElement.objects.get_or_create(code=cde_map["code"])

            logger.debug("max_value = %s" % cde_model.max_value)
            if not created:
                registries_already_using = _registries_using_cde(cde_model)
                if len(registries_already_using) > 0:
                    logger.warning("Import is modifying existing CDE %s" % cde_model)
                    logger.warning("This cde is used by the following registries: %s" % registries_already_using)

            for field in cde_map:
                if field not in ["code", "pv_group"]:
                    import_value = cde_map[field]
                    if not created:
                        old_value = getattr(cde_model, field)
                        if old_value != import_value:
                            logger.warning("import will change cde %s: import value = %s new value = %s" %
                                           (cde_model.code, old_value, import_value))

                    setattr(cde_model, field, cde_map[field])
                    # logger.info("cde %s.%s set to [%s]" % (cde_model.code, field, cde_map[field]))

            # Assign value group - pv_group will be empty string is not a range

            if cde_map["pv_group"]:
                try:
                    pvg = CDEPermittedValueGroup.objects.get(code=cde_map["pv_group"])
                    if not created:
                        if cde_model.pv_group != pvg:
                            logger.warning("import will change cde %s: old group = %s new group = %s" %
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
            logger.info("invalid metadata ( should be json dictionary): %s Error %s" % (metadata_json, verr))
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
            logger.debug("creating registry with code %s from import of %s" % (self.data["code"], self.yaml_data_file))

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
                patient_data_section = self._create_patient_data_section(patient_data_section_map)
                r.patient_data_section = patient_data_section

        if "metadata_json" in self.data:
            metadata_json = self.data["metadata_json"]
            if self._check_metadata_json(metadata_json):
                r.metadata_json = self.data["metadata_json"]
            else:
                raise DefinitionFileInvalid("Invalid JSON for registry metadata ( should be a json dictionary")

        r.save()
        logger.info("imported registry object OK")

        for frm_map in self.data["forms"]:
            logger.info("starting import of form map %s" % frm_map)
            f, created = RegistryForm.objects.get_or_create(registry=r, name=frm_map["name"])
            f.name = frm_map["name"]
            if "questionnaire_display_name" in frm_map:
                f.questionnaire_display_name = frm_map["questionnaire_display_name"]
            f.is_questionnaire = frm_map["is_questionnaire"]
            if "questionnaire_questions" in frm_map:
                f.questionnaire_questions = frm_map["questionnaire_questions"]

            f.registry = r
            f.sections = ",".join([section_map["code"] for section_map in frm_map["sections"]])
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

        self._create_form_permissions(r)
        
        if "demographic_fields" in self.data:
            self._create_demographic_fields(self.data["demographic_fields"])
        logger.info("demographic field definitions OK ")

    def _create_form_permissions(self, registry):
        from registry.groups.models import Group
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
            decision_fields_section_map = adj_def_map["sections_required"]["decision_fields_section"]
            self._create_section_model(result_fields_section_map)
            self._create_section_model(decision_fields_section_map)
            adj_def_model, created = AdjudicationDefinition.objects.get_or_create(registry=registry_model, display_name= adj_def_map["display_name"])
            try:
                adj_def_model.display_name = adj_def_map["display_name"]
            except Exception, ex:
                logger.error("display_name not in adjudication definition")

            adj_def_model.fields = adj_def_map["fields"]
            adj_def_model.result_fields = adj_def_map["result_fields"]
            adj_def_model.decision_field = adj_def_map["decision_field"]
            adj_def_model.adjudicator_username = adj_def_map["adjudicator_username"]
            try:
                adj_def_model.adjudicating_users = adj_def_map["adjudicating_users"]
            except Exception, ex:
                logger.error("adjudicating_users not in definition")

            adj_def_model.save()
            logger.info("created Adjudication Definition %s OK" % adj_def_model)

    def _create_working_groups(self, registry):
        if "working_groups" in self.data:
            working_group_names = self.data["working_groups"]
            logger.debug("working_groups in metadata")
            existing_groups = set([wg for wg in WorkingGroup.objects.filter(registry=registry)])
            new_groups = set([])
            for working_group_name in working_group_names:
                working_group, created = WorkingGroup.objects.get_or_create(name=working_group_name, registry=registry)
                if created:
                    logger.debug("creating new group %s" % working_group_name)
                else:
                    logger.debug("working group %s already exists" % working_group_name)
                working_group.save()
                new_groups.add(working_group)

            groups_to_unlink = existing_groups - new_groups
            for wg in groups_to_unlink:
                logger.info("deleting delete()working group %s for %s registry import" % (wg.name, registry.name))
                wg.registry = None  # if we delete the group the patients get deleted .. todo need to confirm behaviour
                wg.save()


    def _create_consent_sections(self, registry):
        if "consent_sections" in self.data:
            for section_dict in self.data["consent_sections"]:
                code = section_dict["code"]
                section_label = section_dict["section_label"]
                information_link = section_dict["information_link"]
                section_model, created = ConsentSection.objects.get_or_create(code=code, registry=registry)
                section_model.information_link = information_link
                section_model.section_label = section_label
                section_model.applicability_condition = section_dict["applicability_condition"]
                section_model.save()
                for question_dict in section_dict["questions"]:
                    question_code = question_dict["code"]
                    question_position = question_dict["position"]
                    question_label = question_dict["question_label"]

                    question_model, created = ConsentQuestion.objects.get_or_create(code=question_code, section=section_model)
                    question_model.position = question_position
                    question_model.question_label = question_label
                    question_model.save()

    def _create_demographic_fields(self, data):
        for d in data:
            registry_obj = Registry.objects.get(id = d["registry"])
            group_obj = Group.objects.get(id = d["group"])
            demo_field, created = DemographicFields.objects.get_or_create(registry=registry_obj, group=group_obj, field=d["field"])
            demo_field.hidden = d["hidden"]
            demo_field.readonly = d["readonly"]
            demo_field.save()
        
    
