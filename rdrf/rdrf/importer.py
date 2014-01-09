import logging
from models import *
import yaml
from django.core.exceptions import MultipleObjectsReturned


logger = logging.getLogger("registry")

class RegistryImportError(Exception):
    pass

def get_or_create(klass,**kwargs):
    try:
        instance, created = klass.objects.get_or_create(**kwargs)
        if created:
            verb = "created"
        else:
            verb = "updated"
        logger.debug("%s %s with %s" % (verb, klass.__name__, kwargs))

    except MultipleObjectsReturned:
        logger.error("Multiple objects retrieved: %s %s" % (klass.__name__, kwargs))
        raise RegistryImportError("Multiple objects retrieved: %s %s" % (klass.__name__, kwargs))


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

    def load_yaml(self, yaml_data):
        try:
            self.yaml_data = yaml_data
            self.data = yaml.load(yaml_data)
            self.state = ImportState.LOADED
        except Exception, ex:
            self.state = ImportState.MALFORMED
            logger.error("Could not parse yaml data:\n%s\n\nError:\n%s" % (yaml_data, ex))
            self.errors.append(ex)

    def create_registry(self):
        if self.state == ImportState.MALFORMED:
            logger.error("Cannot create registry as yaml is not well formed")
            return

        if self.check_validity:
            self._validate()
        else:
            self.state = ImportState.VALID

        if not self.state == ImportState.VALID:
            logger.error("yaml file invalid: %s" % self.errors)
            return
        # start transaction ..

        if self.delete_existing_registry:
            self._delete_existing_registry()

        self._create_registry_objects()
        if self.check_soundness:
            self._check_soundness()
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
            self.state = ImportState.VALID #TODO validate the syntactic structure of the yaml

    def _check_soundness(self):
        # TODO does the created registry have dangling references to CDEs that don't exist
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
        r = get_or_create(Registry,code=self.data["code"])

        r.code = self.data["code"]
        r.desc = self.data["desc"]
        r.name = self.data["name"]
        r.splash_screen = self.data["splash_screen"]

        r.save()

        for frm_map in self.data["forms"]:
            f = get_or_create(RegistryForm,registry=r, name=frm_map["name"])
            f.name = frm_map["name"]
            f.is_questionnaire = frm_map["is_questionnaire"]
            f.registry = r
            f.sections = ",".join([ section_map["code"] for section_map in frm_map["sections"]])
            f.save()

        for section_map in frm_map["sections"]:
            s = get_or_create(Section,code=section_map["code"])
            s.code = section_map["code"]
            s.display_name = section_map["display_name"]
            s.elements = ",".join(section_map["elements"])
            s.allow_multiple = section_map["allow_multiple"]
            s.extra = section_map["extra"]
            s.save()




