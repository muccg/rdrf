import logging
from models import *
import yaml
from django.core.exceptions import MultipleObjectsReturned


logger = logging.getLogger("registry_log")

class RegistryImportError(Exception):
    pass

class BadDefinitionFile(RegistryImportError):
    pass

class DefinitionFileUnsound(RegistryImportError):
    pass

class DefinitionFileInvalid(RegistryImportError):
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

        # start transaction ..

        if self.delete_existing_registry:
            self._delete_existing_registry()

        self._create_registry_objects()

        if self.check_soundness:
            self._check_soundness()
            if self.state == ImportState.UNSOUND:
                # rollback ...
                raise DefinitionFileUnsound("Definition File refers to CDEs that don't exist: %s" % self.errors)

        else:
            self.state = ImportState.SOUND

        if self.state == ImportState.SOUND:
            #commit
            pass

            self.state = ImportState.IMPORTED

        else:
            logger.error("Imported Registry is not sound and will be rolled back: %s" % self.errors)
            #rollback
            pass

    def _validate(self):
        ve = []
        if "code" not in self.data:
            ve.append("invalid: missing 'code' for registry")

        if "name" not in self.data:
            self.errors.append("invalid: missing 'name' for registry")

        if "forms" not in self.data:
            ve.append("invalid: 'forms' list missing")

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
            self.state = ImportState.SOUND


    def _create_registry_objects(self):
        r, created = Registry.objects.get_or_create(code=self.data["code"])

        if created:
            logger.debug("creating registry with code %s from import of %s" % (self.data["code"], self.yaml_data_file))

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

            for section_map in frm_map["sections"]:
                s, created = Section.objects.get_or_create(code=section_map["code"])
                s.code = section_map["code"]
                s.display_name = section_map["display_name"]
                s.elements = ",".join(section_map["elements"])
                s.allow_multiple = section_map["allow_multiple"]
                s.extra = section_map["extra"]
                s.save()




