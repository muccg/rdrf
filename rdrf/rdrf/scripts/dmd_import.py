import django
django.setup()

import sys
import json
from django.db import transaction
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement

from registry.patients.models import Patient
from rdrf.contexts_api import RDRFContextManager


FAMILY_MEMBERS_CODE = "xxx"


class ImportError(Exception):
    pass


class RollbackError(Exception):
    pass


class Path:
    THROUGH_DIAGNOSIS = 1
    THROUGH_PATIENT = 2



class Conv:
    YNU = {True: "YesNoUnknownYes",
           False: "YesNoUnknownNo"}
    YNPT = {"PT": "DMDPT",
            "Y" : "DMDY",
            "N" : "DMDN"}
    

class PatientRecord(object):

    def __init__(self, patient_dict, all_data):
        self.data = all_data.data  # unwrapped data
        self.patient_dict = patient_dict
        self.patient_id = self.patient_dict["pk"]
        self.diagnosis_dict = self._get_diagnosis()
        self.diagnosis_id = self.diagnosis_dict["pk"]

    def _get_diagnosis(self):
        d = {}
        for thing in self.data:
            if thing["model"] == "dmd.diagnosis" and thing["fields"]["patient"] == self.patient_id:
                d["pk"] = thing["pk"]
                for field in thing["fields"].keys():
                    value = thing["fields"][field]
                    d[field] = value
        return d

    def _get_foreign_key(self, target, model):

        # perhaps some models have weird names for the foreign key
        exceptions = {"patient": {},
                      "diagnosis": {}}

        if model in exceptions[target]:
            return exceptions[target][model]

        if target == "patient":
            return "patient"

        if target == "diagnosis":
            return "diagnosis"

        raise Exception("Don't know how to find foreign key to %s from model %s" % (target,
                                                                                    model))

    def get(self, field, model="patients.patient", path=None):
        print("getting model %s field %s path %s" % (model, field, path))
        if model == "patients.patient":
            return self.patient_dict["fields"][field]
        elif model == "dmd.diagnosis":
            return self.diagnosis_dict[field]
        else:
            if path == Path.THROUGH_DIAGNOSIS:
                foreign_key_field = self._get_foreign_key("diagnosis", model)
                my_id = self.diagnosis_id
            elif path == Path.THROUGH_PATIENT:
                foreign_key_field = self._get_foreign_key("patient", model)
                my_id = self.patient_id
            else:
                raise Exception("Bad path")

            for thing in self.data:
                if thing["model"] == model:
                    print("found a %s" % model)
                    print("%s" % thing)
                    if my_id == thing["fields"][foreign_key_field]:
                        print("found %s!" % my_id)
                        return thing["fields"][field]


# The following was created from iterating through the json dump
# The original json data consists of a list of dictionaries:
# {pk: N, model: "app.classname", "fields": {"field1": value, "field2": ..}}

DATA_MAP = {"field_expression111": {"field": "ip_group",
                                    "model": "iprestrict.rule"},
            "field_expression8": {"field": "applied",
                                  "model": "south.migrationhistory"},
            "field_expression9": {"field": "app_name",
                                  "model": "south.migrationhistory"},
            "field_expression6": {"field": "domain",
                                  "model": "sites.site"},
            "field_expression7": {"field": "name",
                                  "model": "sites.site"},
            "field_expression4": {"field": "session_data",
                                  "model": "sessions.session"},
            "field_expression5": {"field": "expire_date",
                                  "model": "sessions.session"},
            "field_expression2": {"field": "name",
                                  "model": "contenttypes.contenttype"},
            "field_expression3": {"field": "app_label",
                                  "model": "contenttypes.contenttype"},
            "field_expression1": {"field": "model",
                                  "model": "contenttypes.contenttype"},
            "field_expression112": {"field": "updated",
                                    "model": "dmd.diagnosis"},
            "field_expression178": {"field": "action_flag",
                                    "model": "admin.logentry"},
            "ClinicalDiagnosis/DMDClinicalDiagnosis/DMDMuscleBiopsy": {"field": "muscle_biopsy",
                                                                       "model": "dmd.diagnosis",
                                                                       "converter": Conv.YNU},
            "field_expression116": {"field": "created",
                                    "model": "dmd.diagnosis"},
            "field_expression110": {"field": "rank",
                                    "model": "iprestrict.rule"},
            "field_expression174": {"field": "target",
                                    "model": "configuration.emailtemplate"},
            "field_expression175": {"field": "description",
                                    "model": "configuration.emailtemplate"},
            "field_expression78": {"field": "dna_variation",
                                   "model": "genetic.variation"},
            "field_expression79": {"field": "exon",
                                   "model": "genetic.variation"},
            "field_expression170": {"field": "date_joined",
                                    "model": "auth.user"},
            "field_expression171": {"field": "working_groups",
                                    "model": "groups.user"},
            "field_expression172": {"field": "title",
                                    "model": "groups.user"},
            "field_expression173": {"field": "body",
                                    "model": "configuration.emailtemplate"},
            "field_expression72": {"field": "exon_validation_override",
                                   "model": "genetic.variation"},
            "field_expression73": {"field": "point_mutation_all_exons_sequenced",
                                   "model": "genetic.variation"},
            "field_expression70": {"field": "duplication_all_exons_tested",
                                   "model": "genetic.variation"},
            "field_expression71": {"field": "gene",
                                   "model": "genetic.variation"},
            "field_expression76": {"field": "rna_variation",
                                   "model": "genetic.variation"},
            "field_expression77": {"field": "protein_variation_validation_override",
                                   "model": "genetic.variation"},
            "field_expression74": {"field": "technique",
                                   "model": "genetic.variation"},
            "field_expression75": {"field": "deletion_all_exons_tested",
                                   "model": "genetic.variation"},
            "field_expression114": {"field": "patient",
                                    "model": "dmd.diagnosis"},
            "ClinicalDiagnosis/DMDMotorFunction/NMDWheelchairAge": {"field": "wheelchair_usage_age",
                                    "model": "dmd.motorfunction"},
            "ClinicalDiagnosis/DMDClinicalDiagnosis/DMDDiagnosis": {"field": "diagnosis",
                                                                    "model": "dmd.diagnosis",
                                                                    "converter": {
                                                                        "BMD": "DMDBMD",
                                                                        "Car": "DMDCar",
                                                                        "DMD": "DMDDMD",
                                                                        "IMD": "DMDIMD",
                                                                        "Man": "DMDMan",
                                                                        "Oth": "DMDOth"}},
            "field_expression156": {"field": "content_type",
                                    "model": "auth.permission"},
            "field_expression157": {"field": "name",
                                    "model": "auth.group"},
            "field_expression154": {"field": "codename",
                                    "model": "auth.permission"},
            "field_expression155": {"field": "name",
                                    "model": "auth.permission"},
            "field_expression152": {"field": "notes",
                                    "model": "dmd.notes"},
            "field_expression153": {"field": "diagnosis",
                                    "model": "dmd.notes"},
            "field_expression69": {"field": "exon_boundaries_known",
                                   "model": "genetic.variation"},
            "field_expression68": {"field": "chromosome",
                                   "model": "genetic.gene"},
            "field_expression186": {"field": "date_created",
                                    "model": "reversion.revision"},
            "field_expression150": {"field": "relationship",
                                    "model": "dmd.familymember"},
            "field_expression61": {"field": "doctor",
                                   "model": "patients.patientdoctor"},
            "field_expression60": {"field": "relationship",
                                   "model": "patients.patientdoctor"},
            "field_expression63": {"field": "name",
                                   "model": "genetic.gene"},
            "field_expression62": {"field": "status",
                                   "model": "genetic.gene"},
            "field_expression65": {"field": "hgnc_id",
                                   "model": "genetic.gene"},
            "field_expression64": {"field": "symbol",
                                   "model": "genetic.gene"},
            "field_expression67": {"field": "accession_numbers",
                                   "model": "genetic.gene"},
            "field_expression66": {"field": "refseq_id",
                                   "model": "genetic.gene"},
            "field_expression149": {"field": "diagnosis",
                                    "model": "dmd.familymember"},
            "field_expression148": {"field": "family_member_diagnosis",
                                    "model": "dmd.familymember"},
            "field_expression58": {"field": "next_of_kin_suburb",
                                   "model": "patients.patient"},
            "field_expression59": {"field": "patient",
                                   "model": "patients.patientdoctor"},
            "field_expression158": {"field": "permissions",
                                    "model": "auth.group"},
            "field_expression159": {"field": "username",
                                    "model": "auth.user"},
            "field_expression54": {"field": "inactive_reason",
                                   "model": "patients.patient"},
            "field_expression55": {"field": "next_of_kin_mobile_phone",
                                   "model": "patients.patient"},
            "field_expression56": {"field": "place_of_birth",
                                   "model": "patients.patient"},
            "field_expression57": {"field": "next_of_kin_postcode",
                                   "model": "patients.patient"},
            "field_expression50": {"field": "address",
                                   "model": "patients.patient"},
            "field_expression51": {"field": "active",
                                   "model": "patients.patient"},
            "field_expression52": {"field": "next_of_kin_home_phone",
                                   "model": "patients.patient"},
            "family_name": {"field": "family_name",
                                   "model": "patients.patient"},
            "field_expression43": {"field": "date_of_birth",
                                   "model": "patients.patient"},
            "field_expression42": {"field": "state",
                                   "model": "patients.patient"},
            "field_expression41": {"field": "next_of_kin_email",
                                   "model": "patients.patient"},
            "field_expression40": {"field": "work_phone",
                                   "model": "patients.patient"},
            "field_expression47": {"field": "mobile_phone",
                                   "model": "patients.patient"},
            "field_expression46": {"field": "next_of_kin_family_name",
                                   "model": "patients.patient"},
            "field_expression45": {"field": "email",
                                   "model": "patients.patient"},
            "field_expression44": {"field": "home_phone",
                                   "model": "patients.patient"},
            "field_expression49": {"field": "suburb",
                                   "model": "patients.patient"},
            "field_expression48": {"field": "next_of_kin_address",
                                   "model": "patients.patient"},
            "field_expression141": {"field": "trial_sponsor",
                                    "model": "dmd.clinicaltrials"},
            "field_expression140": {"field": "drug_name",
                                    "model": "dmd.clinicaltrials"},
            "field_expression143": {"field": "diagnosis",
                                    "model": "dmd.clinicaltrials"},
            "ClinicalDiagnosis/DMDHeart/DMDlvef": {"field": "lvef",
                                    "model": "dmd.heart"},
            "ClinicalDiagnosis/DMDHeart/DMDHeartPrevious": {"field": "failure",
                                                            "model": "dmd.heart",
                                                            "converter": Conv.YNU},
            "field_expression123": {"field": "diagnosis",
                                    "model": "dmd.steroids"},
            "ClinicalDiagnosis/DMDSteroids/DMDSteroidCurrent": {"field": "current",
                                                                "model": "dmd.steroids",
                                                                "converter": Conv.YNU},
            "ClinicalDiagnosis/DMDMotorFunction/NMDSit": {"field": "sit",
                                    "model": "dmd.motorfunction"},
            "field_expression120": {"field": "diagnosis",
                                    "model": "dmd.motorfunction"},
            "ClinicalDiagnosis/DMDHeart/DMDHeartCurrent": {"field": "current",
                                                           "model": "dmd.heart",
                                                           "converter": Conv.YNU},
            "field_expression126": {"field": "diagnosis",
                                    "model": "dmd.surgery"},
            "ClinicalDiagnosis/NMDSurgery/NMDSurgery": {"field": "surgery",
                                                        "model": "dmd.surgery",
                                                        "converter": Conv.YNU},
            "ClinicalDiagnosis/DMDSteroids/DMDSteroidPrevious": {"field": "previous",
                                    "model": "dmd.steroids"},
            "field_expression147": {"field": "registry_patient",
                                    "model": "dmd.familymember"},
            "field_expression146": {"field": "diagnosis",
                                    "model": "dmd.otherregistries"},
            "field_expression36": {"field": "next_of_kin_given_names",
                                   "model": "patients.patient"},
            "field_expression37": {"field": "next_of_kin_work_phone",
                                   "model": "patients.patient"},
            "field_expression34": {"field": "sex",
                                   "model": "patients.patient"},
            "field_expression35": {"field": "postcode",
                                   "model": "patients.patient"},
            "field_expression32": {"field": "date_of_migration",
                                   "model": "patients.patient"},
            "field_expression33": {"field": "next_of_kin_state",
                                   "model": "patients.patient"},
            "field_expression30": {"field": "umrn",
                                   "model": "patients.patient"},
            "field_expression31": {"field": "consent",
                                   "model": "patients.patient"},
            "field_expression38": {"field": "working_group",
                                   "model": "patients.patient"},
            "field_expression39": {"field": "next_of_kin_parent_place_of_birth",
                                   "model": "patients.patient"},
            "field_expression185": {"field": "comment",
                                    "model": "reversion.revision"},
            "field_expression184": {"field": "content_type",
                                    "model": "admin.logentry"},
            "field_expression187": {"field": "manager_slug",
                                    "model": "reversion.revision"},
            "field_expression176": {"field": "groups",
                                    "model": "configuration.emailtemplate"},
            "field_expression181": {"field": "object_id",
                                    "model": "admin.logentry"},
            "field_expression180": {"field": "object_repr",
                                    "model": "admin.logentry"},
            "field_expression183": {"field": "user",
                                    "model": "admin.logentry"},
            "field_expression182": {"field": "change_message",
                                    "model": "admin.logentry"},
            "field_expression189": {"field": "description",
                                    "model": "explorer.query"},
            "field_expression188": {"field": "user",
                                    "model": "reversion.revision"},
            "field_expression138": {"field": "fvc_date",
                                    "model": "dmd.respiratory"},
            "field_expression139": {"field": "invasive_ventilation",
                                    "model": "dmd.respiratory"},
            "field_expression130": {"field": "diagnosis",
                                    "model": "dmd.heart"},
            "ClinicalDiagnosis/DMDHeart/DMDlvefDate": {"field": "lvef_date",
                                    "model": "dmd.heart"},
            "field_expression132": {"field": "status",
                                    "model": "dmd.heartmedication"},
            "field_expression133": {"field": "diagnosis",
                                    "model": "dmd.heartmedication"},
            "field_expression134": {"field": "drug",
                                    "model": "dmd.heartmedication"},
            "ClinicalDiagnosis/NMDRespiratory/NMDNonInvasive": {"field": "non_invasive_ventilation",
                                                                "model": "dmd.respiratory",
                                                                "converter": Conv.YNPT},
            "field_expression136": {"field": "fvc",
                                    "model": "dmd.respiratory"},
            "field_expression137": {"field": "diagnosis",
                                    "model": "dmd.respiratory"},
            "field_expression177": {"field": "name",
                                    "model": "configuration.emailtemplate"},
            "field_expression142": {"field": "trial_name",
                                    "model": "dmd.clinicaltrials"},
            "field_expression25": {"field": "address",
                                   "model": "patients.doctor"},
            "field_expression24": {"field": "state",
                                   "model": "patients.doctor"},
            "field_expression27": {"field": "surgery_name",
                                   "model": "patients.doctor"},
            "field_expression26": {"field": "email",
                                   "model": "patients.doctor"},
            "field_expression21": {"field": "phone",
                                   "model": "patients.doctor"},
            "field_expression20": {"field": "speciality",
                                   "model": "patients.doctor"},
            "field_expression23": {"field": "suburb",
                                   "model": "patients.doctor"},
            "field_expression22": {"field": "given_names",
                                   "model": "patients.doctor"},
            "field_expression29": {"field": "given_names",
                                   "model": "patients.patient"},
            "field_expression28": {"field": "next_of_kin_relationship",
                                   "model": "patients.patient"},
            "field_expression198": {"field": "is_playground",
                                    "model": "explorer.querylog"},
            "field_expression199": {"field": "run_at",
                                    "model": "explorer.querylog"},
            "field_expression192": {"field": "last_run_date",
                                    "model": "explorer.query"},
            "field_expression193": {"field": "sql",
                                    "model": "explorer.query"},
            "field_expression190": {"field": "title",
                                    "model": "explorer.query"},
            "field_expression191": {"field": "created_at",
                                    "model": "explorer.query"},
            "field_expression196": {"field": "run_by_user",
                                    "model": "explorer.querylog"},
            "field_expression197": {"field": "sql",
                                    "model": "explorer.querylog"},
            "field_expression194": {"field": "created_by_user",
                                    "model": "explorer.query"},
            "field_expression195": {"field": "query",
                                    "model": "explorer.querylog"},
            "field_expression109": {"field": "url_pattern",
                                    "model": "iprestrict.rule"},
            "field_expression108": {"field": "action",
                                    "model": "iprestrict.rule"},
            "field_expression105": {"field": "last_ip",
                                    "model": "iprestrict.iprange"},
            "field_expression104": {"field": "cidr_prefix_length",
                                    "model": "iprestrict.iprange"},
            "field_expression107": {"field": "ip_group",
                                    "model": "iprestrict.iprange"},
            "field_expression106": {"field": "first_ip",
                                    "model": "iprestrict.iprange"},
            "field_expression101": {"field": "revision",
                                    "model": "reversion.version"},
            "field_expression100": {"field": "serialized_data",
                                    "model": "reversion.version"},
            "field_expression103": {"field": "description",
                                    "model": "iprestrict.ipgroup"},
            "field_expression102": {"field": "name",
                                    "model": "iprestrict.ipgroup"},
            "field_expression179": {"field": "action_time",
                                    "model": "admin.logentry"},
            "field_expression18": {"field": "name",
                                   "model": "patients.state"},
            "field_expression19": {"field": "family_name",
                                   "model": "patients.doctor"},
            "field_expression10": {"field": "migration",
                                   "model": "south.migrationhistory"},
            "field_expression11": {"field": "username",
                                   "model": "userlog.loginlog"},
            "field_expression12": {"field": "ip_address",
                                   "model": "userlog.loginlog"},
            "field_expression13": {"field": "forwarded_by",
                                   "model": "userlog.loginlog"},
            "field_expression14": {"field": "user_agent",
                                   "model": "userlog.loginlog"},
            "field_expression15": {"field": "timestamp",
                                   "model": "userlog.loginlog"},
            "field_expression16": {"field": "name",
                                   "model": "groups.workinggroup"},
            "field_expression17": {"field": "country",
                                   "model": "patients.state"},
            "field_expression164": {"field": "is_staff",
                                    "model": "auth.user"},
            "field_expression167": {"field": "user_permissions",
                                    "model": "auth.user"},
            "field_expression169": {"field": "email",
                                    "model": "auth.user"},
            "field_expression166": {"field": "groups",
                                    "model": "auth.user"},
            "field_expression165": {"field": "last_login",
                                    "model": "auth.user"},
            "field_expression90": {"field": "code",
                                   "model": "configuration.module"},
            "field_expression91": {"field": "name",
                                   "model": "configuration.module"},
            "field_expression92": {"field": "country",
                                   "model": "configuration.consentform"},
            "field_expression93": {"field": "form",
                                   "model": "configuration.consentform"},
            "field_expression94": {"field": "module",
                                   "model": "configuration.consentform"},
            "field_expression95": {"field": "format",
                                   "model": "reversion.version"},
            "field_expression96": {"field": "object_repr",
                                   "model": "reversion.version"},
            "field_expression97": {"field": "object_id",
                                   "model": "reversion.version"},
            "field_expression98": {"field": "content_type",
                                   "model": "reversion.version"},
            "field_expression99": {"field": "object_id_int",
                                   "model": "reversion.version"},
            "ClinicalDiagnosis/DMDMotorFunction/NMDWheelchairChoices": {"field": "wheelchair_use",
                                    "model": "dmd.motorfunction"},
            "ClinicalDiagnosis/DMDMotorFunction/NMDWalk": {"field": "walk",
                                    "model": "dmd.motorfunction"},
            "field_expression151": {"field": "sex",
                                    "model": "dmd.familymember"},
            "field_expression162": {"field": "is_active",
                                    "model": "auth.user"},
            "field_expression161": {"field": "last_name",
                                    "model": "auth.user"},
            "field_expression163": {"field": "is_superuser",
                                    "model": "auth.user"},
            "field_expression160": {"field": "first_name",
                                    "model": "auth.user"},
            "field_expression145": {"field": "registry",
                                    "model": "dmd.otherregistries"},
            "field_expression144": {"field": "trial_phase",
                                    "model": "dmd.clinicaltrials"},
            "field_expression87": {"field": "contact_phone",
                                   "model": "genetic.laboratory"},
            "field_expression86": {"field": "contact_name",
                                   "model": "genetic.laboratory"},
            "field_expression85": {"field": "contact_email",
                                   "model": "genetic.laboratory"},
            "field_expression84": {"field": "dna_variation_validation_override",
                                   "model": "genetic.variation"},
            "field_expression83": {"field": "molecular_data",
                                   "model": "genetic.variation"},
            "field_expression82": {"field": "all_exons_in_male_relative",
                                   "model": "genetic.variation"},
            "field_expression81": {"field": "rna_variation_validation_override",
                                   "model": "genetic.variation"},
            "field_expression80": {"field": "protein_variation",
                                   "model": "genetic.variation"},
            "field_expression168": {"field": "password",
                                    "model": "auth.user"},
            "field_expression89": {"field": "address",
                                   "model": "genetic.laboratory"},
            "field_expression88": {"field": "name",
                                   "model": "genetic.laboratory"}}


class Data(object):

    def __init__(self, json_file, registry_model):
        self.json_file = json_file
        self.registry_model = registry_model
        self.data = self._load()

    def _load(self):
        with open(self.json_file) as f:
            return json.load(f)

    @property
    def patients(self):
        for thing in self.data:
            if thing["model"] == "patients.patient":
                print("Patient %s" % thing)
                yield thing


def meta(stage, run_after=False):
    # consistent logging
    def decorator(func):
        func_name = func.__name__

        def wrapper(self, *args, **kwargs):
            rdrf_id = self._get_rdrf_id()
            old_id = self._get_old_id()
            target = self._get_target()
            log_prefix = "%s/%s %s %s %s " % (rdrf_id,
                                              old_id,
                                              stage,
                                              target,
                                              func_name)


            try:
                myargs = [self] + list(args)
                value = func(*myargs, **kwargs)
                log_line = "%s: OK" % log_prefix
                print(log_line)
            except ImportError as ierr:
                log_line = "%s: IMPORT ERROR! - %s" % (log_prefix,
                                                       ex)

                value = None
                error_message = "%s" % ierr
                print(log_line)
                raise RollbackError(error_message)

            self.log(log_line)
            return value
        return wrapper
    return decorator


class OldRegistryImporter(object):

    def __init__(self, registry_model, json_file):
        self.json_file = json_file
        self.data = Data(self.json_file, registry_model)
        self.registry_model = registry_model
        self.patient_model = None
        self.form_model = None
        self.section_model = None
        self.cde_model = None
        self.record = None
        self._log = sys.stdout
        self.after_ops = []
        self.rdrf_context_manager = RDRFContextManager(registry_model)

    def log(self, msg):
        msg = msg + "\n"
        self._log.write(msg)

    def _get_rdrf_id(self):
        if self.patient_model:
            return self.patient_model.pk

    def _get_old_id(self):
        if self.record:
            return self.record.patient_id

    def _get_target(self):
        form_name = section_code = cde_code = "?"

        if self.form_model:
            form_name = self.form_model.name

        if self.section_model:
            section_code = self.section_model.code

        if self.cde_model:
            cde_code = self.cde_model.code

        t = "%s/%s/%s" % (form_name,
                          section_code,
                          cde_code)
        if t == "?/?/?":
            return "No target"
        else:
            return t

    def _load_json_data(self):
        with open(self.json_file) as jf:
            return json.load(jf)

    def run(self):
        for patient_dict in self.data.patients:
            self.record = PatientRecord(patient_dict, self.data)
            self._process_record()

    def _process_record(self):
        self.patient_model = self._create_patient()
        for form_model in self.registry_model.forms:
            self.form_model = form_model
            for section_model in form_model.section_models:
                self.section_model = section_model
                self._process_section()

    @meta("DEMOGRAPHICS")
    def _create_patient(self):
        p = Patient()
        p.family_name = self.record.get("family_name")
        p.given_names = self.record.get("given_names")
        p.sex = self.record.get("sex")
        p.date_of_birth = self.record.get("date_of_birth")
        p.consent = True
        p.active = True
        p.save()
        print("patient %s saved OK" % p)
        self.context_model = self.rdrf_context_manager.get_or_create_default_context(p, new_patient=True)
        print("created default context %s" % self.context_model)
        
        return p

    @meta("FAMILY_MEMBER", run_after=True)
    def _create_family_member(self, patient_model, family_member_dict):
        existing_relative_patient_model = None

    @meta("SECTION")
    def _process_section(self):
        if not self.section_model.allow_multiple:
            for cde_model in self.section_model.cde_models:
                self.cde_model = cde_model
                self._process_cde()
        else:
            self._process_multisection()

    @meta("MULTISECTION")
    def _process_multisection(self):
        print("skipping multisection for now ...")
        return
        for item_dict in self._get_items():
            self._append_multisection_item(item_dict)

    @meta("CDE")
    def _process_cde(self):
        field_expression = self._get_current_field_expression()
        print("cde datatype = %s" % self.cde_model.datatype)
        info = DATA_MAP.get(field_expression, None)
        if info:
            model = info["model"]
            field = info["field"]
            # Most objects are related to patient via the diagnosis
            path = info.get("path", Path.THROUGH_DIAGNOSIS)
            converter = info.get("converter", None)
            old_value = self.record.get(field, model,path)
            if old_value is not None:
                if converter is not None:
                    print("converter will be used")
                    converter_func = self._get_converter_func(converter)
                    new_value = converter_func(old_value)
                else:
                    print("No converter - raw value will be used")
                    new_value = old_value
                self._save_cde(new_value)

        else:
            raise Exception("Unknown field expression: %s" % field_expression)


    def _get_converter_func(self, converter):
        if type(converter) is dict:
            return lambda key: converter.get(key, None)
        else:
            converter_func_name = "convert_%s" % converter
            if hasattr(self, converter_func_name):
                converter_func = getattr(self, converter_func_name)
                if callable(converter_func):
                    return converter_func
                else:
                    raise Exception("converter for %s is not callable" % converter_func_name)
            else:
                raise Exception("Unknown converter func %s" % converter_func_name)
            


    @meta("SAVECDE")
    def _save_cde(self, value):
        field_expression=self._get_current_field_expression()
        if self.cde_model.pv_group:
            print("cde is a range - perform range check")
            range_members = self.cde_model.get_range_members()
            print("range members = %s" % range_members)
            if not value in range_members:
                raise Exception("Bad range member: %s not in %s" % (value, range_members))
            
            
        self._evaluate_field_expression(field_expression, value)

    def _get_current_field_expression(self):
        return "%s/%s/%s" % (self.form_model.name,
                             self.section_model.code,
                             self.cde_model.code)

    def _evaluate_field_expression(self, field_expression, value):
        self.patient_model.evaluate_field_expression(self.registry_model,
                                                     field_expression,
                                                     value=value)


if __name__ == "__main__":
    registry_code=sys.argv[1]
    json_file=sys.argv[2]

    registry_model=Registry.objects.get(code=registry_code)
    importer=OldRegistryImporter(registry_model, json_file)

    try:
        with transaction.atomic():
            importer.run()
    except Exception as err:
        sys.stderr.write("Unhandled error! - rollback will occur: %s\n" % err)
        sys.exit(1)
