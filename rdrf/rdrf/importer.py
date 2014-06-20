import logging
from models import *
from registry.patients.models import Patient
import yaml
from django.core.exceptions import MultipleObjectsReturned


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

    return [ code for code in registries]

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

class ImportState:
    INITIAL = "INITIAL"
    MALFORMED = "MALFORMED"
    LOADED = "LOADED"
    VALID = "VALID"
    INVALID = "INVALID"
    SOUND = "SOUND"   # the registry has been created and check to have no dangling cde codes
    UNSOUND = "UNSOUND" # the spec contains references to cdes which don't exist
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
        self.patients = [] # if patients are assigned to the registry we're importing over
                           # we maintain them even if we delete the old registry

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
        except Exception, ex:
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

        self._get_patients()

        if self.delete_existing_registry:
            self._delete_existing_registry()

        self._create_registry_objects()

        if self.check_soundness:
            self._check_soundness()
            if self.state == ImportState.UNSOUND:
                raise DefinitionFileUnsound("Definition File refers to CDEs that don't exist: %s" % self.errors)

        else:
            self.state = ImportState.SOUND


    def _get_patients(self):
        try:
            registry = Registry.objects.get(code=self.data["code"])
            for patient_registry in Patient.objects.filter(rdrf_registry__in=registry):
                logger.debug("adding patient %s to internal list" % patient_registry.patient)
                self.patients.append(patient_registry.patient)
        except Registry.DoesNotExist:
            self.patients = []


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
                cde = CommonDataElement.objects.get(code=cde_code)
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
        form_codes_in_db = set([ frm.name for frm in RegistryForm.objects.filter(registry=imported_registry)])
        form_codes_in_yaml = set([frm_map["name"] for frm_map in self.data["forms"]])
        if form_codes_in_db != form_codes_in_yaml:
            msg = "in db: %s in yaml: %s" % (form_codes_in_db, form_codes_in_yaml)
            raise RegistryImportError("Imported registry has different forms to yaml file: %s" % msg)

    def _check_sections(self, imported_registry):
        for form in RegistryForm.objects.filter(registry=imported_registry):
            sections_in_db = set(form.get_sections())
            for section_code in sections_in_db:
                try:
                    section = Section.objects.get(code=section_code)
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
                            raise RegistryImportError("CDE %s.%s does not exist" % (form.name, section_code, section_cde_code))

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

                        raise RegistryImportError("CDE codes on imported registry do not match those specified in data file: %s" % msg)

                except Section.DoesNotExist:
                    raise RegistryImportError("Section %s in form %s has not been created?!" % (section_code, form.name))

    def _create_groups(self, permissible_value_group_maps):
        for pvg_map in permissible_value_group_maps:
            pvg, created = CDEPermittedValueGroup.objects.get_or_create(code=pvg_map["code"])
            pvg.save()
            #logger.info("imported permissible value group %s" % pvg)
            if not created:
                logger.warning("Import is updating an existing group %s" % pvg.code)
                existing_values = [ pv for pv in CDEPermittedValue.objects.filter(pv_group=pvg) ]
                existing_value_codes = set([ pv.code for pv in existing_values])
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
                    value, created = CDEPermittedValue.objects.get_or_create(code=value_map["code"],pv_group=pvg)
                    if not created:
                        if value.value != value_map["value"]:
                            logger.warning("Existing value code %s.%s = '%s'" % (value.pv_group.code,value.code, value.value))
                            logger.warning("Import value code %s.%s = '%s'" % (pvg_map["code"], value_map["code"], value_map["value"]))

                        if value.desc != value_map["desc"]:
                            logger.warning("Existing value desc%s.%s = '%s'" % (value.pv_group.code,value.code, value.desc))
                            logger.warning("Import value desc %s.%s = '%s'" % (pvg_map["code"], value_map["code"], value_map["desc"]))

                    # update the value ...
                    value.value = value_map["value"]
                    value.desc = value_map["desc"]
                    value.save()
                    #logger.info("imported value %s" % value)

    def _create_cdes(self, cde_maps):
        for cde_map in cde_maps:
            logger.debug("importing cde_map %s" % cde_map)
            cde_model, created = CommonDataElement.objects.get_or_create(code=cde_map["code"])

            logger.debug("max_value = %s" % cde_model.max_value)
            if not created:
                logger.warning("Import is modifying existing CDE %s" % cde_model)
                logger.warning("This cde is used by the following registries: %s" % _registries_using_cde(cde_model))

            for field in cde_map:
                if field not in ["code", "pv_group"]:
                    import_value = cde_map[field]
                    if not created:
                        old_value = getattr(cde_model, field)
                        if old_value != import_value:
                            logger.warning("import will change cde %s: import value = %s new value = %s" % (cde_model.code, old_value, import_value))


                    setattr(cde_model, field, cde_map[field])
                    #logger.info("cde %s.%s set to [%s]" % (cde_model.code, field, cde_map[field]))

            #Assign value group - pv_group will be empty string is not a range

            if cde_map["pv_group"]:
                try:
                    pvg = CDEPermittedValueGroup.objects.get(code=cde_map["pv_group"])
                    if not created:
                        if cde_model.pv_group != pvg:
                             logger.warning("import will change cde %s: old group = %s new group = %s" % (cde_model.code,cde_model.pv_group, pvg ))

                    cde_model.pv_group = pvg
                except CDEPermittedValueGroup.DoesNotExist,ex:
                    raise ConsistencyError("Assign of group %s to imported CDE %s failed: %s" % (cde_map["pv_group"], cde_model.code, ex))

            cde_model.save()
            #logger.info("updated cde %s" % cde_model)


    def _create_registry_objects(self):

        self._create_groups(self.data["pvgs"])
        self._create_cdes(self.data["cdes"])

        r, created = Registry.objects.get_or_create(code=self.data["code"])

        if created:
            logger.debug("creating registry with code %s from import of %s" % (self.data["code"], self.yaml_data_file))

        original_forms = set([ f.name for f in RegistryForm.objects.filter(registry=r)])
        imported_forms = set([])
        r.code = self.data["code"]
        r.name = self.data["name"]

        r.splash_screen = self.data["splash_screen"]

        r.save()

        for frm_map in self.data["forms"]:
            f, created = RegistryForm.objects.get_or_create(registry=r, name=frm_map["name"])
            f.name = frm_map["name"]
            f.is_questionnaire = frm_map["is_questionnaire"]
            f.registry = r
            f.sections = ",".join([ section_map["code"] for section_map in frm_map["sections"]])
            f.save()
            imported_forms.add(f.name)

            for section_map in frm_map["sections"]:
                s, created = Section.objects.get_or_create(code=section_map["code"])
                s.code = section_map["code"]
                s.display_name = section_map["display_name"]
                s.elements = ",".join(section_map["elements"])
                s.allow_multiple = section_map["allow_multiple"]
                s.extra = section_map["extra"]
                s.save()

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






