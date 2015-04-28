import sys
import json
import os
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement

from registry.patients.models import Patient
from registry.patients.models import PatientAddress
from registry.patients.models import State
from registry.groups.models import WorkingGroup
from registry.genetic.models import Gene
from rdrf.dynamic_data import DynamicDataWrapper
from rdrf.file_upload import wrap_gridfs_data_for_form


def mapkey(form_model, section_model, cde_model=None):
    if cde_model is not None:
        return "%s__%s__%s" % (form_model.name, section_model.code, cde_model.code)
    else:
        return "%s__%s" % (form_model, section_model)


def cde_moniker(form_model, section_model, cde_model=None):
    if cde_model is None:
        return "%s.%s" % (form_model.name, section_model.display_name)

    return "%s.%s.%s" % (form_model.name, section_model.display_name, cde_model.name)


def frm(frm_name):
    return RegistryForm.objects.get(name=frm_name)


def sec(sec_code):
    return Section.objects.get(code=sec_code)


def cde(cde_code):
    return CommonDataElement.objects.get(code=cde_code)


class MigrationError(Exception):
    pass


class AbortError(MigrationError):
    pass


class BadValueError(MigrationError):
    pass


class RetrievalError(MigrationError):
    pass


class ChoicesError(MigrationError):
    pass


class PatientNotFound(MigrationError):
    pass


class PatientCouldNotBeCreated(MigrationError):
    pass


class ConversionError(MigrationError):
    pass


mapfile_misnamed = {
    # These cdes couldn't be found in map file so I created an exceptions dict
}


class Retriever(object):
    def __init__(self, importer, data, app, model, field):
        self.data = data   # loaded dump files
        self.app = app
        self.model = model
        self.field = field
        self.importer = importer

    @property
    def full_model_name(self):
        return self.app + "." + self.model

    def __call__(self, patient_id):
        diagnosis_id = self.get_diagnosis_id(patient_id)
        for item in self.data:
            if "model" in item:
                if item["model"] == self.full_model_name:
                    # check for special case of being on diagnosis
                    if self.full_model_name in ["sma.diagnosis"]:
                        if item["pk"] == diagnosis_id:
                            if "fields" in item:
                                if self.field in item["fields"]:
                                    return item["fields"][self.field]

                    # check for submodel
                    if "diagnosis" in item["fields"]:
                        if item["fields"]["diagnosis"] == diagnosis_id:
                            if self.field in item["fields"]:
                                return item["fields"][self.field]


        raise RetrievalError("%s.%s.%s : missing?" % (self.app, self.model, self.field))

    def get_diagnosis_id(self, patient_id):
        diagnosis_model_name = self.app + "." + "diagnosis"
        for item in self.data:
            if "model" in item:
                if item["model"] == diagnosis_model_name:
                    if item["fields"]["patient"] == patient_id:
                        if item["fields"]["diagnosis"].lower() == self.app: # diagnosis SMA etc
                            return item["pk"]

        raise RetrievalError("%s.%s.%s: could not get to diagnosis id for patient %s" % (self.app, self.model, self.field, patient_id))

    def __str__(self):
        return "%s.%s.%s retriever" % (self.app, self.model, self.field)


class BaseMultiSectionHandler(object):
    MODEL_NAME = ""             # subclass resp
    PATIENT_LINK = "patient"     # always true?
    DIAGNOSIS_LINK = "diagnosis"
    FORM_MODEL = None           # subclass - rdrf form model instance
    SECTION_MODEL = None        # subclass - rdrf section model instance
    FIELD_MAP = {}              # subclass resp map of old fields dump file to cde models in RDRF

    def __init__(self, importer, app, data):
        self.data = data
        self.app = app
        self.importer = importer
        self.code = mapkey(self.FORM_MODEL, self.SECTION_MODEL)
        self.patient_id = None
        self.diagnosis_id = None


    def __call__(self, patient_id, rdrf_patient):
        # The model objects which RDRF represents as multisections
        # are related to diagnosis objects in the old system as objects themselves
        self.patient_id = patient_id
        original_models = []
        converted_sections = []
        self.diagnosis_id = self.get_diagnosis_id(patient_id)
        # find the list of models which are now represented as multisections

        for old_model in self.importer._old_models(self.MODEL_NAME):
            if self.is_appropriate_model(old_model):
                self.importer.msg("found a model for multisection: %s" % old_model)
                original_models.append(old_model)
                self.importer.msg("found %s so far" % len(original_models))

        for original_model in original_models:
            mongo_section_item = self._create_mongo_section(original_model)
            self.importer.success("converted old model: %s ---> member of multisection: %s" % (original_model,
                                                                                               mongo_section_item))
            converted_sections.append(mongo_section_item)

        self._save_multisection_to_mongo(rdrf_patient, converted_sections)

    def is_appropriate_model(self, old_model):
        return old_model["fields"][self.DIAGNOSIS_LINK] == self.diagnosis_id

    def get_diagnosis_id(self, patient_id):
        diagnosis_model_name = self.app + "." + "diagnosis"
        for item in self.data:
            if "model" in item:
                if item["model"] == diagnosis_model_name:
                    if item["fields"]["patient"] == patient_id:
                        if item["fields"]["diagnosis"].lower() == self.app:  # diagnosis SMA etc
                            return item["pk"]

        raise RetrievalError("could not get diagnosis id for patient id: %s" % patient_id)

    def _save_multisection_to_mongo(self, rdrf_patient, converted_sections):
        self.importer.msg("saving list of section items to mongo %s" % converted_sections)
        registry_code = self.importer.registry.code
        gridfs_wrapped_sections = wrap_gridfs_data_for_form(target_registry_code, converted_sections)
        multisection_data = {self.SECTION_MODEL.code: gridfs_wrapped_sections}
        ddw = DynamicDataWrapper(rdrf_patient)
        ddw.save_dynamic_data(registry_code, "cdes", multisection_data)
        m = cde_moniker(self.FORM_MODEL, self.SECTION_MODEL)
        self.importer.success("saved multisection for %s: " % (m, ))

    def _create_mongo_section(self, old_section_data):
        self.importer.msg("creating mongo section for old section data: %s" % old_section_data)
        # we need to create a dictionary that looks like:
        # NB values may need to be converted
        # {u'Clinical Diagnoses____NMDClinicalTrials____NMDTrialName': u't2',
        #  u'Clinical Diagnoses____NMDClinicalTrials____NMDTrialSponsor': u's2',
        #  u'Clinical Diagnoses____NMDClinicalTrials____NMDDrugName': u'd2',
        #  u'Clinical Diagnoses____NMDClinicalTrials____NMDTrialPhase': u'p2'}
        d = {}

        for old_field in self.FIELD_MAP:
            self.importer.msg("converting old field %s in multisection" % old_field)
            cde_model = self.FIELD_MAP[old_field]
            old_value = old_section_data["fields"][old_field]
            self.importer.msg("old value = %s" % old_value)
            new_value = self.convert_value(self.FORM_MODEL, self.SECTION_MODEL, cde_model, old_value)
            self.importer.msg("new value = %s" % new_value)
            mongo_field_key = "%s____%s____%s" % (self.FORM_MODEL.name, self.SECTION_MODEL.code, cde_model.code)
            d[mongo_field_key] = new_value
        return d


    def convert_value(self, form_model, section_model, cde_model, old_value):
        return self.importer.get_new_data_value(form_model, section_model, cde_model, old_value)


class SMAFamilyMemberMultisectionHandler(BaseMultiSectionHandler):
    MODEL_NAME = "sma.familymember"
    FORM_MODEL = frm("Clinical Diagnoses")
    SECTION_MODEL = sec("SMAFamilyMember")

    FIELD_MAP = {
        "family_member_diagnosis": cde("SMAFamilyDiagnosis"),
        "sex":  cde("NMDSex"),
        "relationship": cde("NMDRelationship"),
        "registry_patient": cde("NMDRegistryPatient"),

    }


class NMDOtherRegistriesMultiSectionHandler(BaseMultiSectionHandler):
    MODEL_NAME = "sma.otherregistries"
    FORM_MODEL = frm("Clinical Diagnoses")
    SECTION_MODEL = sec("NMDOtherRegistries")


class NMDClinicalTrialsMultisectionHandler(BaseMultiSectionHandler):
    MODEL_NAME = "sma.clinicaltrials"
    DIAGNOSIS_LINK = "diagnosis"
    FORM_MODEL = frm("Clinical Diagnoses")
    SECTION_MODEL = sec("NMDClinicalTrials")

    FIELD_MAP = {
        "trial_name": cde("NMDTrialName"),
        "drug_name": cde("NMDDrugName"),
        "trial_sponsor": cde("NMDTrialSponsor"),
        "trial_phase": cde("NMDTrialPhase"),
    }


class NMDOtherRegistriesMultisectionHandler(BaseMultiSectionHandler):
    MODEL_NAME = "sma.otherregistries"
    DIAGNOSIS_LINK = "diagnosis"
    FORM_MODEL = frm("Clinical Diagnoses")
    SECTION_MODEL = sec("NMDOtherRegistries")

    FIELD_MAP = {
        "registry": cde("NMDOtherRegistry"),

    }


class SMAMolecularMultisectionHandler(BaseMultiSectionHandler):
    MODEL_NAME = "genetic.variationsma"
    DIAGNOSIS_LINK = "diagnosis"
    FORM_MODEL = frm("Genetic Data")
    SECTION_MODEL = sec("SMAMolecular")

    # SMAExon7Sequencing
    # SMADNAVariation

    #{"pk": 1, "model": "genetic.moleculardata", "fields": {}}, {"pk": 1, "model": "genetic.moleculardatasma", "fields": {}},
    #  {"pk": 1, "model": "genetic.variationsma",
    # "fields": {"exon_7_smn1_deletion": 2, "exon_7_sequencing": true,
    # "technique": "MLPA", "molecular_data": 1,
    # "dna_variation": "a", "gene": 18}},

    FIELD_MAP = {
        "gene": cde("NMDGene"),
        "technique": cde("NMDTechnique"),
        "exon_7_smn1_deletion": cde("SMAExon7Deletion"),
        "exon_7_sequencing": cde("SMAExon7Sequencing"),
        "dna_variation": cde("SMADNAVariation"),
    }

    def is_appropriate_model(self, old_model):
        # in sma the patient is one to one with molecular data and the primary key is
        # the patient id ?
        return old_model["fields"]["molecular_data"] == self.patient_id

    def convert_value(self, form_model, section_model, cde_model, old_value):
        if cde_model.code == "NMDGene":
            old_gene_model = self.importer.get_old_model("genetic.gene", lambda m: m["pk"] == old_value)
            if old_gene_model is not None:
                old_value = old_gene_model["fields"]["symbol"]
            else:
                raise ConversionError("old patient id = %s cde model %s Missing gene pk = %s" % (self.patient_id, cde_model, old_value))

        return super(SMAMolecularMultisectionHandler, self).convert_value(form_model, section_model, cde_model, old_value)


def moniker(old_patient_dict):
    try:
            return "old patient pk %s %s %s %s" % (old_patient_dict["pk"],
                                           old_patient_dict["fields"]["given_names"],
                                           old_patient_dict["fields"]["family_name"],
                                           old_patient_dict["fields"]["date_of_birth"])
    except:
        return "??"


def logged(func):
    def wrapper(*args, **kwargs):
        args[0].info("running %s on args %s kwargs %s " % (func.__name__, args[1:], kwargs))
        result = func(*args, **kwargs)
        args[0].info("result = %s" % result)
        return result
    return wrapper


class PatientImporter(object):
    def __init__(self, target_registry_code, src_system, migration_map_file, dump_dir):
        self.suppress_success_msg = False
        self.src_system = src_system  # eg sma or dmd
        self.registry = Registry.objects.get(code=target_registry_code)
        self._dump_dir = dump_dir
        self._data = []
        self._log_file = "%s_patient_import.log" % target_registry_code
        self._log = open(self._log_file, "w")
        self._migration_map = self._load_migration_map(migration_map_file)
        self._working_groups_map = {}
        self._states_map = {}


    # public interface

    def run(self):
        self._prelude()
        self._working_groups_map = self._create_working_groups()
        #self._create_genes()
        self._create_labs()
        self._create_states()

        for old_patient_id in self._old_patient_ids():
            try:
                rdrf_patient = self._create_rdrf_patient(old_patient_id)
            except PatientNotFound, pnf_err:
                self.error(pnf_err)
                continue

            except PatientCouldNotBeCreated, pc_error:
                self.error(pc_error)
                continue

            self._create_address(old_patient_id, rdrf_patient)
            self._create_relationships(old_patient_id, rdrf_patient)

            for form_model in self.registry.forms:
                for section_model in form_model.section_models:
                    if not section_model.allow_multiple:
                        for cde_model in section_model.cde_models:
                            self._save_in_mongo(rdrf_patient, old_patient_id, form_model, section_model, cde_model)

                    else:
                        self._create_multisections(form_model, section_model, old_patient_id, rdrf_patient)

        self._endrun()

    def rollback(self):
        pass

    def rollback_mongo(self):
        pass

    def load_data(self):
        for dump_file in os.listdir(self._dump_dir):
            if dump_file.endswith("json"):
                self._load_dumpfile(dump_file)
                self.success("loaded %s" % dump_file)

    # private

    def _old_models(self, model_name=None):
        if model_name is None:
            for item in self._data:
                if "model" in item:
                    yield item
        else:
            for item in self._data:
                if "model" in item:
                    if item["model"] == model_name:
                        yield item

    def get_old_model(self, model_name, predicate):
        for old_model in self._old_models(model_name):
            if predicate(old_model):
                return old_model

    def _prelude(self):
        self.msg("*********************************************************")
        self.msg("%s TO %s MIGRATION STARTED" % (self.src_system, self.registry))

    def _endrun(self):
        self.msg("MIGRATION FINISHED")
        self.msg("*********************************************************")

    def _get_state(self, name):
        return State.objects.get(short_name=name)

    def _create_address(self, old_patient_id, rdrf_patient_model):
        patient_record = self._get_old_patient(old_patient_id)
        #  address = models.TextField()
        #  suburb = models.CharField(max_length=50, verbose_name="Suburb/Town")
        # state = models.CharField(max_length=20, verbose_name="State/Province/Territory")
        # postcode = models.CharField(max_length=20, blank=True)
        # country = models.CharField(max_length=20)

        try:
            address_model = PatientAddress()
            address_model.address = patient_record["fields"]["address"]
            address_model.suburb =  patient_record["fields"]["suburb"]
            address_model.state = get_state(address_data["state"])
            address_model.postcode = patient_record["fields"]["postcode"]
            address_model.country = "Australia"   #???
            address_model.patient = rdrf_patient_model
        except Exception, ex:
            self.error("could not set fields on address object for %s %s: %s" % (moniker(old_patient_id), rdrf_patient_model, ex))
            return

        try:
            address_model.save()
            self.success("saved address for %s %s" % (moniker(patient_record), rdrf_patient_model))
        except Exception, ex:
            self.error("could not save address for %s (%s): %s" % (moniker(patient_record), rdrf_patient_model, ex))


    def _create_working_groups(self):
        working_groups_id_map = {}
        for model in self._old_models("groups.workinggroup"):
            name = model["fields"]["name"]
            old_pk = model["pk"]
            rdrf_working_group, created = WorkingGroup.objects.get_or_create(registry=self.registry, name=name)
            if created:
                rdrf_working_group.save()
                self.success("created working group %s" % rdrf_working_group.name)
            working_groups_id_map[old_pk] = rdrf_working_group

        self.msg("working groups map = %s" % working_groups_id_map)
        return working_groups_id_map

    def _create_genes(self):
        def display(gene_dict):
            flds = gene_dict["fields"]
            return "Gene %s (%s) ACC NUMS=%s" % (flds["name"], flds["symbol"], flds["accession_numbers"])

        for old_gene_model in self._old_models("genetic.gene"):
            rdrf_gene_model, created = Gene.objects.get_or_create(accession_numbers=old_gene_model["fields"]["accession_numbers"],
                                                                  name=old_gene_model["fields"]["name"],
                                                                  symbol=old_gene_model["fields"]["symbol"])
            if created:
                for field in old_gene_model["fields"]:
                    try:
                        value = old_gene_model["fields"][field]
                        setattr(rdrf_gene_model, field, old_gene_model["fields"][field])
                    except Exception, ex:
                        self.error("Gene Error: old gene %s - failed to set field %s value %s: %s" % (old_gene_model,
                                                                                                      field,
                                                                                                      value,
                                                                                                      ex))

                    try:
                        rdrf_gene_model.save()
                    except Exception, ex:
                        self.error("Gene Error: could not save gene %s/%s: %s" % ( old_gene_model, rdrf_gene_model, ex))

            else:
                pass
                #self.msg("Gene %s already exists" % display(old_gene_model))

    def _create_labs(self):
        self.to_do("create labs")

    def _create_states(self):
        for state_dict in self._old_models("patients.state"):
            rdrf_state, created = State.objects.get_or_create(name=state_dict["fields"]["name"])

            if created:
                rdrf_state.save()
                self.success("created State %s" % rdrf_state)
            self._states_map[state_dict["pk"]] = rdrf_state

    def _family_members(self, old_patient_id, rdrf_patient_model):
        self.to_do("family members")

    def _consent_forms(self):
        self.to_do("consent forms")

    def _load_migration_map(self, map_filename):
        with open(map_filename) as mf:
            data = json.load(mf)
            self.success("loaded migration map %s" % map_filename)
            return data

    def _create_rdrf_patient(self, old_patient_id):
        old_patient_data = self._get_old_patient(old_patient_id)
        m = moniker(old_patient_data)
        self.msg("creating patient for %s" % m)
        field_dict = old_patient_data["fields"]
        special = ["next_of_kin_state", "next_of_kin_relationship", "working_group", "address", "suburb", "state", "postcode"]
        p = Patient()

        for field in field_dict:
            if not field in special:
                value = field_dict[field]
                setattr(p, field, value)
                self.success("%s demographics: setting %s = %s" % (m, field, value))
        try:
            p.save()
            p.rdrf_registry = [self.registry]
            p.save()
            self.success("created %s ( new pk = %s old pk = %s )" % (p, p.id, old_patient_data["pk"]))
            return p
        except Exception, ex:
            raise PatientCouldNotBeCreated("%s: %s" % (m, ex))

    def _get_source_field(self, form_model, section_model, cde_model):
        k = mapkey(form_model, section_model, cde_model)
        for d in self._migration_map:
            if k in d:
                return d[k]
        raise ChoicesMissing("could not find choice map for : %s" % k)

    def _get_old_patient(self, patient_id):
        patient_model_name = "patients.patient"
        for item in self._data:
            if "model" in item:
                if item["model"] == patient_model_name:
                    if item["pk"] == patient_id:
                        return item

        raise PatientNotFound("patient id %s" % patient_id)

    def info(self, msg):
        print msg
        self._log.write(msg + "\n")

    def msg(self, msg):
        self.info("INFO %s" % msg)

    def success(self, msg):
        if not self.suppress_success_msg:
            self.info("GOOD " + msg)

    def error(self, msg):
        self.info("FAIL %s" % msg)

    def to_do(self, msg):
        self.info("TODO %s" % msg)

    def _old_patient_ids(self):
        for item in self._data:
            if "model" in item:
                if item["model"] == "patients.patient":
                    if "pk" in item:
                        yield item["pk"]

    def _create_relationships(self, old_patient_id, rdrf_patient_model):
        self._assign_working_group(old_patient_id, rdrf_patient_model)

    def _assign_working_group(self, old_patient_id, rdrf_patient_model):
        for patient_model in self._old_models("patients.patient"):
            if patient_model["pk"] == old_patient_id:
                if "fields" in patient_model:
                    if "working_group" in patient_model["fields"]:
                        old_working_group_pk = patient_model["fields"]["working_group"]
                        if old_working_group_pk:
                            try:
                                rdrf_working_group_model = self._working_groups_map[old_working_group_pk]
                                rdrf_patient_model.working_groups = [ rdrf_working_group_model ]
                                rdrf_patient_model.save()
                                self.success("%s assigned working group = %s" % (rdrf_patient_model, rdrf_working_group_model))
                            except KeyError:
                                self.error("could not assign working group for %s: old pk %s not in map" % (rdrf_patient_model, old_working_group_pk))

    def _load_dumpfile(self, dump_filename):
        self.info("loading %s" % dump_filename)
        with open(os.path.join(self._dump_dir, dump_filename)) as dump_file:
            self._data.extend(json.load(dump_file))

    def _save_in_mongo(self, rdrf_patient_model, old_patient_id, form_model, section_model, cde_model):
        try:
            old_name, old_value = self._get_old_data_value(old_patient_id, form_model, section_model, cde_model)
        except RetrievalError, rerr:
            self.error("RDR Patient %s RDRF Patient %s - could not retrieve data for %s: %s" % (old_patient_id,
                                                                                            rdrf_patient_model.pk,
                                                                                            cde_moniker(form_model, section_model, cde_model),
                                                                                            rerr))
            return

        try:
            new_value = self.get_new_data_value(form_model, section_model, cde_model, old_value)
        except ConversionError, cerr:
            self.error("RDR Patient %s RDRF Patient %s - could not convert data for %s with value %s: %s" % (old_patient_id,
                                                                                                             rdrf_patient_model.id,
                                                                                                             cde_moniker(form_model, section_model, cde_model),
                                                                                                             old_value,
                                                                                                             cerr))

            return

        rdrf_patient_model.set_form_value(self.registry.code, form_model.name, section_model.code, cde_model.code, new_value)
        new_name = cde_moniker(form_model, section_model, cde_model)
        self.success("RDR Patient %s with %s = %s ==> RDRF Patient %s with %s = %s" % (old_patient_id,
                                                                                       old_name,
                                                                                       old_value,
                                                                                       rdrf_patient_model.id,
                                                                                       new_name,
                                                                                       new_value))

    def _get_old_data_value(self, old_patient_id, form_model, section_model, cde_model):
        retrieval_func = self._get_retrieval_function(form_model, section_model, cde_model)
        old_name = retrieval_func.full_model_name
        old_value = retrieval_func(old_patient_id)
        return old_name, old_value

    def get_new_data_value(self, form_model, section_model, cde_model, old_value):
        m = cde_moniker(form_model, section_model, cde_model)
        if cde_model.pv_group:
            choices_tuple = self._get_choice_tuple(form_model, section_model, cde_model)
            if not choices_tuple is None:
                try:
                    return get_choice(choices_tuple, old_value)
                except Exception, ex:
                    raise ConversionError("%s could not find corresponding choice value for %s in %s: %s" % (m, old_value, choices_tuple, ex))
            else:
                raise ConversionError("no choice tuple for %s" % m)
        else:
            return old_value

    def _create_multisections(self, form_model, section_model, old_patient_id, rdrf_patient_model):
        # INFO creating multisection data SMAFamilyMember
        # INFO creating multisection data NMDClinicalTrials
        # INFO creating multisection data NMDOtherRegistries

        multisection_handler = self._get_multisection_handler(section_model)
        if multisection_handler is None:
            raise AbortError("No multisection handler function defined for %s" % section_model)

        if not section_model.allow_multiple:
            self.error("%s %s is NOT multiple" % (form_model, section_model))
            return
        self.msg("creating multisection data %s" % section_model)

        multisection_handler(old_patient_id, rdrf_patient_model)

    def _get_multisection_handler(self, multisection_model):
        self.msg("creating handler for multisection %s" % multisection_model)
        if not multisection_model.allow_multiple:
            return None

        if multisection_model.code == "SMAFamilyMember":
            return SMAFamilyMemberMultisectionHandler(self, self.src_system, self._data)
        elif multisection_model.code == "NMDClinicalTrials":
            return NMDClinicalTrialsMultisectionHandler(self, self.src_system, self._data)
        elif multisection_model.code == "NMDOtherRegistries":
            return NMDOtherRegistriesMultisectionHandler(self, self.src_system, self._data)
        elif multisection_model.code == "SMAMolecular":
            return SMAMolecularMultisectionHandler(self, self.src_system, self._data)


        return None


    def _get_choice_tuple(self, form_model, section_model, cde_model):
        source_field = self._get_source_field(form_model, section_model, cde_model)
        if source_field:
            if source_field in choice_map:
                return choice_map[source_field]
        m = cde_moniker(form_model, section_model, cde_model)
        raise ConversionError("Could not locate choice tuple for %s" % m)

    def _get_retrieval_function(self, form_model, section_model, cde_model):
        code = mapkey(form_model, section_model, cde_model)
        self.msg("looking for %s" % code)
        if code in mapfile_misnamed:
            self.msg("%s in misnamed" % code)
            old_code = code
            # the mapfile has a diffent name?
            code = mapfile_misnamed[code]
            self.msg("correct name = %s" % code)
            self.msg("Map file correction: %s -> %s" % (old_code, code))

        for item in self._migration_map:
            if code in item:
                old_model_code = item[code]
                app, model, field = old_model_code.split(".")
                return Retriever(self, self._data, app, model, field)

        raise RetrievalError("could not create retriever for %s" % cde_moniker(form_model, section_model, cde_model))


def get_choice(choice_tuple, old_choice_value):
    for t in choice_tuple:
        if t[0] == old_choice_value:
            return t[2]
    raise ConversionError("choices tuple %s does not contain %s" % (choice_tuple, old_choice_value))

# SMA Choices  taken from code of disease_registry
# first two values are from the old system
# the third element is the value in the new system


# (OLD CODE, OLD DESCRIPTION, NEW_CODE)
SMA_DIAGNOSIS_CHOICES = (
        ("SMA", "Spinal Muscular Atrophy", "SMASMA"),
        ("Oth", "Other", "SMAOth"),
        ("Unk", "Unknown", "SMAUnk")
)
SMA_CLASSIFICATION_CHOICES = (
    ("SMA1", "SMA1 - onset between 0-6months, nevers sits, natural age of death <2 years "),
    ("SMA2", "SMA2 - onset between 7-18 months, never stands, natural age of death >2 years", "SMASMA2"),
    ("SMA3", "SMA3 - onset >18 months, stands and walks (this highest function may be lost during evolution)", "SMASMA3"),
    ("Other", "Other", "SMAOther"),
    ("Unknown", "Unknown", "SMAUnknown")
)

SMA_MOTOR_FUNCTION_CHOICES = (
        ("walking", "Walking independently", "walking"),
        ("sitting", "Sitting independently", "sitting"),
        ("none", "Never able to walk or sit independently", "none")
)

SMA_WHEELCHAIR_USE_CHOICES = (
        ("permanent", "Yes (Permanent)", "permanent"),
        ("intermittent", "Yes (Intermittent)", "intermittent"),
        ("never", "Never", "never"),
        ("unknown", "Unknown", "unknown")
)

SMA_VENTILATION_CHOICES = (
        ("Y", "Yes", "DMDY"),
        ("PT", "Yes (part-time)", "DMDPT"),
        ("N", "No", "DMDN"),
)


SMA_YES_NO_UNKNOWN = (
    (1, "Unknown", "YesNoUnknownUnknown"),
    (2, "Yes", "YesNoUnknownYes"),
    (3, "No", "YesNoUnknownNo"),
)

UYN_CHOICES = (
        ('U', 'Unknown', "YesNoUnknownUnknown"),
        ('Y', 'Yes', "YesNoUnknownYes"),
        ('N', 'No', "YesNoUnknownNo"),
)

# had to customise this  - the sma gui displays a dropdown but the field is boolean
NULL_BOOLEAN_FIELD = (
    (None, 'Unknown', "YesNoUnknownUnknown"),
    (False, 'No', 'YesNoUnknownNo'),
    (True, 'Yes', 'YesNoUnknownYes')
)

SMA_SEX_CHOICES = (
     ("M", "Male", "M"),
     ("F", "Female", "F"),
     ("X", "Other/Intersex", "X")
)


SMA_SMN1_CHOICES = (
        (1, 'Homozygous', "SMAHomozygous"),
        (2, 'Heterozygous', "SMAHeterozygous"),
        (3, 'No', "SMANo"),
)

# {"pk": 1, "model": "genetic.variationsma", "fields": {"exon_7_smn1_deletion": 2, "exon_7_se
# quencing": true, "technique": "MLPA", "molecular_data": 1, "dna_variation": "a", "gene": 18}},

choice_map = {
    "sma.motorfunction.best_function": SMA_MOTOR_FUNCTION_CHOICES,
    "sma.motorfunction.wheelchair_use": SMA_WHEELCHAIR_USE_CHOICES,
    "sma.surgery.surgery": NULL_BOOLEAN_FIELD,
    "sma.feedingfunction.gastric_nasal_tube": NULL_BOOLEAN_FIELD,   # NB. The source field is a nullable boolean field not a range
    "sma.respiratory.invasive_ventilation": SMA_VENTILATION_CHOICES,
    "sma.respiratory.non_invasive_ventilation": SMA_VENTILATION_CHOICES,
    "sma.diagnosis.diagnosis" : SMA_DIAGNOSIS_CHOICES,
    "sma.diagnosis.classification": SMA_CLASSIFICATION_CHOICES,
    "sma.familymember.family_member_diagnosis": SMA_DIAGNOSIS_CHOICES,
    "sma.familymember.sex": SMA_SEX_CHOICES,
    "genetic.variationsma.exon_7_smn1_deletion": SMA_SMN1_CHOICES,
}

if __name__ == '__main__':
    src_system = sys.argv[1]  # sma or dmd
    dump_dir = sys.argv[2]
    target_registry_code = sys.argv[3]
    migration_map_file = sys.argv[4]

    importer = PatientImporter(target_registry_code, src_system, migration_map_file, dump_dir)
    importer.load_data()
    #try:
    importer.run()
    # except AbortError, aerr:
    #     importer.error("Aborting error thrown : %s\nAborting..." % aerr)
    #     importer.rollback()
    #     importer.rollback_mongo()
    #     importer.msg("rolled back!")
    #
    # except Exception, ex:
    #     importer.error("Unhandled exception: %s" % ex)
    #     importer.msg("Rolling back ...")
    #     importer.rollback()
    #     importer.rollback_mongo()

    importer.msg("all done")