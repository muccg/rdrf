from registry.groups import GROUPS as RDRF_GROUPS
from registry.genetic.models import Laboratory
from registry.groups.models import CustomUser
from registry.groups.models import WorkingGroup
from registry.patients.models import PatientDoctor
from registry.patients.models import Doctor
from registry.patients.models import PatientAddress
from registry.patients.models import Patient
from rdrf.db.contexts_api import RDRFContextManager
from rdrf.db.generalised_field_expressions import MultiSectionItemsExpression
from rdrf.helpers.utils import parse_iso_datetime
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import EmailNotification
from rdrf.models.definition.models import EmailTemplate
from rdrf.models.definition.models import ConsentQuestion
from rdrf.models.definition.models import ConsentSection
from rdrf.models.definition.models import Registry
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group
from django.db import transaction
from datetime import datetime, timedelta
import json
import sys
import django
django.setup()


FAMILY_MEMBERS_CODE = "xxx"


NZ_WORKING_GROUP_ID = 4
NZ_ABBREV = "NZ"

ONE_YEAR_AGO = datetime.now() - timedelta(days=365)


PERMISSIONS_ON_STAGING = """
Clinical Staff: add_laboratory
Clinical Staff: change_laboratory
Clinical Staff: change_addresstype
Clinical Staff: delete_addresstype
Clinical Staff: add_nextofkinrelationship
Clinical Staff: change_nextofkinrelationship
Clinical Staff: delete_nextofkinrelationship
Clinical Staff: add_patient
Clinical Staff: can_see_data_modules
Clinical Staff: can_see_diagnosis_currency
Clinical Staff: can_see_diagnosis_progress
Clinical Staff: can_see_dob
Clinical Staff: can_see_full_name
Clinical Staff: can_see_working_groups
Clinical Staff: change_patient
Clinical Staff: delete_patient
Clinical Staff: add_patientaddress
Clinical Staff: change_patientaddress
Clinical Staff: delete_patientaddress
Clinical Staff: add_patientconsent
Clinical Staff: change_patientconsent
Clinical Staff: delete_patientconsent
Clinical Staff: add_patientrelative
Clinical Staff: change_patientrelative
Clinical Staff: delete_patientrelative
Clinical Staff: add_state
Clinical Staff: change_state
Clinical Staff: delete_state
Clinical Staff: change_questionnaireresponse
Clinical Staff: delete_questionnaireresponse
Genetic Curator: add_gene
Genetic Curator: change_gene
Genetic Curator: delete_gene
Genetic Curator: add_laboratory
Genetic Curator: change_laboratory
Genetic Curator: delete_laboratory
Genetic Curator: add_technique
Genetic Curator: change_technique
Genetic Curator: delete_technique
Genetic Curator: add_addresstype
Genetic Curator: change_addresstype
Genetic Curator: delete_addresstype
Genetic Curator: add_consentvalue
Genetic Curator: change_consentvalue
Genetic Curator: delete_consentvalue
Genetic Curator: add_nextofkinrelationship
Genetic Curator: change_nextofkinrelationship
Genetic Curator: delete_nextofkinrelationship
Genetic Curator: add_parentguardian
Genetic Curator: change_parentguardian
Genetic Curator: delete_parentguardian
Genetic Curator: add_patient
Genetic Curator: can_see_data_modules
Genetic Curator: can_see_dob
Genetic Curator: can_see_full_name
Genetic Curator: can_see_genetic_data_map
Genetic Curator: can_see_working_groups
Genetic Curator: change_patient
Genetic Curator: delete_patient
Genetic Curator: add_patientaddress
Genetic Curator: change_patientaddress
Genetic Curator: delete_patientaddress
Genetic Curator: add_patientconsent
Genetic Curator: change_patientconsent
Genetic Curator: delete_patientconsent
Genetic Curator: add_patientdoctor
Genetic Curator: change_patientdoctor
Genetic Curator: delete_patientdoctor
Genetic Curator: add_patientrelative
Genetic Curator: change_patientrelative
Genetic Curator: delete_patientrelative
Genetic Curator: add_state
Genetic Curator: change_state
Genetic Curator: delete_state
Working Group Staff: add_laboratory
Working Group Staff: change_laboratory
Working Group Staff: add_addresstype
Working Group Staff: change_addresstype
Working Group Staff: delete_addresstype
Working Group Staff: add_consentvalue
Working Group Staff: change_consentvalue
Working Group Staff: delete_consentvalue
Working Group Staff: add_nextofkinrelationship
Working Group Staff: change_nextofkinrelationship
Working Group Staff: delete_nextofkinrelationship
Working Group Staff: add_parentguardian
Working Group Staff: change_parentguardian
Working Group Staff: delete_parentguardian
Working Group Staff: add_patient
Working Group Staff: can_see_data_modules
Working Group Staff: can_see_diagnosis_currency
Working Group Staff: can_see_diagnosis_progress
Working Group Staff: can_see_dob
Working Group Staff: can_see_full_name
Working Group Staff: can_see_working_groups
Working Group Staff: change_patient
Working Group Staff: delete_patient
Working Group Staff: add_patientaddress
Working Group Staff: change_patientaddress
Working Group Staff: delete_patientaddress
Working Group Staff: add_patientconsent
Working Group Staff: change_patientconsent
Working Group Staff: delete_patientconsent
Working Group Staff: add_patientrelative
Working Group Staff: change_patientrelative
Working Group Staff: delete_patientrelative
Working Group Staff: add_state
Working Group Staff: change_state
Working Group Staff: delete_state
Genetic Staff: add_gene
Genetic Staff: change_gene
Genetic Staff: add_laboratory
Genetic Staff: change_laboratory
Genetic Staff: add_technique
Genetic Staff: change_technique
Genetic Staff: add_addresstype
Genetic Staff: change_addresstype
Genetic Staff: delete_addresstype
Genetic Staff: add_nextofkinrelationship
Genetic Staff: change_nextofkinrelationship
Genetic Staff: delete_nextofkinrelationship
Genetic Staff: add_patient
Genetic Staff: can_see_data_modules
Genetic Staff: can_see_dob
Genetic Staff: can_see_full_name
Genetic Staff: can_see_genetic_data_map
Genetic Staff: can_see_working_groups
Genetic Staff: change_patient
Genetic Staff: delete_patient
Genetic Staff: add_patientaddress
Genetic Staff: change_patientaddress
Genetic Staff: delete_patientaddress
Genetic Staff: add_patientconsent
Genetic Staff: change_patientconsent
Genetic Staff: delete_patientconsent
Genetic Staff: add_patientrelative
Genetic Staff: change_patientrelative
Genetic Staff: delete_patientrelative
Genetic Staff: add_state
Genetic Staff: change_state
Genetic Staff: delete_state
Working Group Curators: add_gene
Working Group Curators: change_gene
Working Group Curators: delete_gene
Working Group Curators: add_laboratory
Working Group Curators: change_laboratory
Working Group Curators: delete_laboratory
Working Group Curators: add_technique
Working Group Curators: change_technique
Working Group Curators: delete_technique
Working Group Curators: add_addresstype
Working Group Curators: change_addresstype
Working Group Curators: delete_addresstype
Working Group Curators: add_doctor
Working Group Curators: change_doctor
Working Group Curators: delete_doctor
Working Group Curators: add_nextofkinrelationship
Working Group Curators: change_nextofkinrelationship
Working Group Curators: delete_nextofkinrelationship
Working Group Curators: add_patient
Working Group Curators: can_see_data_modules
Working Group Curators: can_see_dob
Working Group Curators: can_see_full_name
Working Group Curators: can_see_working_groups
Working Group Curators: change_patient
Working Group Curators: delete_patient
Working Group Curators: add_patientaddress
Working Group Curators: change_patientaddress
Working Group Curators: delete_patientaddress
Working Group Curators: add_patientconsent
Working Group Curators: change_patientconsent
Working Group Curators: delete_patientconsent
Working Group Curators: add_patientdoctor
Working Group Curators: change_patientdoctor
Working Group Curators: delete_patientdoctor
Working Group Curators: add_patientrelative
Working Group Curators: change_patientrelative
Working Group Curators: delete_patientrelative
Working Group Curators: add_state
Working Group Curators: change_state
Working Group Curators: delete_state
Working Group Curators: change_questionnaireresponse
Working Group Curators: delete_questionnaireresponse
AdminOnly: add_logentry
AdminOnly: change_logentry
AdminOnly: delete_logentry
AdminOnly: add_group
AdminOnly: change_group
AdminOnly: delete_group
AdminOnly: add_permission
AdminOnly: change_permission
AdminOnly: delete_permission
AdminOnly: add_contenttype
AdminOnly: change_contenttype
AdminOnly: delete_contenttype
AdminOnly: add_query
AdminOnly: change_query
AdminOnly: delete_query
AdminOnly: add_gene
AdminOnly: change_gene
AdminOnly: delete_gene
AdminOnly: add_laboratory
AdminOnly: change_laboratory
AdminOnly: delete_laboratory
AdminOnly: add_technique
AdminOnly: change_technique
AdminOnly: delete_technique
AdminOnly: add_customuser
AdminOnly: change_customuser
AdminOnly: delete_customuser
AdminOnly: add_workinggroup
AdminOnly: change_workinggroup
AdminOnly: delete_workinggroup
AdminOnly: add_ipgroup
AdminOnly: change_ipgroup
AdminOnly: delete_ipgroup
AdminOnly: add_iprange
AdminOnly: change_iprange
AdminOnly: delete_iprange
AdminOnly: add_reloadrulesrequest
AdminOnly: change_reloadrulesrequest
AdminOnly: delete_reloadrulesrequest
AdminOnly: add_rule
AdminOnly: change_rule
AdminOnly: delete_rule
AdminOnly: add_addresstype
AdminOnly: change_addresstype
AdminOnly: delete_addresstype
AdminOnly: add_clinicianother
AdminOnly: change_clinicianother
AdminOnly: delete_clinicianother
AdminOnly: add_consentvalue
AdminOnly: change_consentvalue
AdminOnly: delete_consentvalue
AdminOnly: add_doctor
AdminOnly: change_doctor
AdminOnly: delete_doctor
AdminOnly: add_nextofkinrelationship
AdminOnly: change_nextofkinrelationship
AdminOnly: delete_nextofkinrelationship
AdminOnly: add_parentguardian
AdminOnly: change_parentguardian
AdminOnly: delete_parentguardian
AdminOnly: add_patient
AdminOnly: can_see_data_modules
AdminOnly: can_see_diagnosis_currency
AdminOnly: can_see_diagnosis_progress
AdminOnly: can_see_dob
AdminOnly: can_see_full_name
AdminOnly: can_see_genetic_data_map
AdminOnly: can_see_working_groups
AdminOnly: change_patient
AdminOnly: delete_patient
AdminOnly: add_patientaddress
AdminOnly: change_patientaddress
AdminOnly: delete_patientaddress
AdminOnly: add_patientconsent
AdminOnly: change_patientconsent
AdminOnly: delete_patientconsent
AdminOnly: add_patientdoctor
AdminOnly: change_patientdoctor
AdminOnly: delete_patientdoctor
AdminOnly: add_patientrelative
AdminOnly: change_patientrelative
AdminOnly: delete_patientrelative
AdminOnly: add_state
AdminOnly: change_state
AdminOnly: delete_state
AdminOnly: add_cdepermittedvalue
AdminOnly: change_cdepermittedvalue
AdminOnly: delete_cdepermittedvalue
AdminOnly: add_cdepermittedvaluegroup
AdminOnly: change_cdepermittedvaluegroup
AdminOnly: delete_cdepermittedvaluegroup
AdminOnly: add_cdepolicy
AdminOnly: change_cdepolicy
AdminOnly: delete_cdepolicy
AdminOnly: add_commondataelement
AdminOnly: change_commondataelement
AdminOnly: delete_commondataelement
AdminOnly: add_consentquestion
AdminOnly: change_consentquestion
AdminOnly: delete_consentquestion
AdminOnly: add_consentsection
AdminOnly: change_consentsection
AdminOnly: delete_consentsection
AdminOnly: add_demographicfields
AdminOnly: change_demographicfields
AdminOnly: delete_demographicfields
AdminOnly: add_emailnotification
AdminOnly: change_emailnotification
AdminOnly: delete_emailnotification
AdminOnly: add_emailnotificationhistory
AdminOnly: change_emailnotificationhistory
AdminOnly: delete_emailnotificationhistory
AdminOnly: add_emailtemplate
AdminOnly: change_emailtemplate
AdminOnly: delete_emailtemplate
AdminOnly: add_mongomigrationdummymodel
AdminOnly: change_mongomigrationdummymodel
AdminOnly: delete_mongomigrationdummymodel
AdminOnly: add_notification
AdminOnly: change_notification
AdminOnly: delete_notification
AdminOnly: add_questionnaireresponse
AdminOnly: change_questionnaireresponse
AdminOnly: delete_questionnaireresponse
AdminOnly: add_rdrfcontext
AdminOnly: change_rdrfcontext
AdminOnly: delete_rdrfcontext
AdminOnly: add_registry
AdminOnly: change_registry
AdminOnly: delete_registry
AdminOnly: add_registryform
AdminOnly: change_registryform
AdminOnly: delete_registryform
AdminOnly: form_39_is_readonly
AdminOnly: form_40_is_readonly
AdminOnly: form_44_is_readonly
AdminOnly: form_45_is_readonly
AdminOnly: form_46_is_readonly
AdminOnly: form_61_is_readonly
AdminOnly: form_70_is_readonly
AdminOnly: form_81_is_readonly
AdminOnly: form_82_is_readonly
AdminOnly: form_83_is_readonly
AdminOnly: form_84_is_readonly
AdminOnly: form_85_is_readonly
AdminOnly: form_86_is_readonly
AdminOnly: form_87_is_readonly
AdminOnly: form_88_is_readonly
AdminOnly: add_section
AdminOnly: change_section
AdminOnly: delete_section
AdminOnly: add_wizard
AdminOnly: change_wizard
AdminOnly: delete_wizard
AdminOnly: add_registrationprofile
AdminOnly: change_registrationprofile
AdminOnly: delete_registrationprofile
AdminOnly: add_session
AdminOnly: change_session
AdminOnly: delete_session
AdminOnly: add_site
AdminOnly: change_site
AdminOnly: delete_site
AdminOnly: add_migrationhistory
AdminOnly: change_migrationhistory
AdminOnly: delete_migrationhistory
AdminOnly: add_failedloginlog
AdminOnly: change_failedloginlog
AdminOnly: delete_failedloginlog
AdminOnly: add_loginattempt
AdminOnly: change_loginattempt
AdminOnly: delete_loginattempt
AdminOnly: add_loginlog
AdminOnly: change_loginlog
AdminOnly: delete_loginlog
AdminOnly: add_failedloginlog
AdminOnly: change_failedloginlog
AdminOnly: delete_failedloginlog
AdminOnly: add_loginlog
AdminOnly: change_loginlog
AdminOnly: delete_loginlog
AdminOnly: add_query
AdminOnly: change_query
AdminOnly: delete_query
"""

patient_map = {}

diagnosis_currency_map = {}


def delete_existing_models():
    def kill(klass):
        klass.objects.all().delete()
        klass.objects.all().delete()

    def delusers():
        for u in CustomUser.objects.all():
            if u.username != "admin":
                u.delete()
    classes = [Patient, Laboratory, PatientAddress,
               EmailNotification, EmailTemplate,
               PatientDoctor, Doctor, ClinicalData, Group, WorkingGroup]
    for k in classes:
        kill(k)
    delusers()


class ImportError(Exception):
    pass


class RollbackError(Exception):
    pass


class Path:
    THROUGH_DIAGNOSIS = 1
    THROUGH_PATIENT = 2
    THROUGH_MOLECULAR_DATA = 3


SKIP_FIELDS = ["dna_variation_validation_override",
               "exon_validation_override",
               "protein_variation_validation_override",
               "rna_variation_validation_override"]


class Conv:
    YNU = {True: "YesNoUnknownYes",
           False: "YesNoUnknownNo"}

    # NB DMD! This is in the yaml ...
    YNPT = {"PT": "DMDPT",
            "Y": "DMDY",
            "N": "DMDN"}

    SMADiagnosis = {
        "SMA": "SMASMA",
        "Oth": "SMAOth",
        "Unk": "SMAUnk",
    }
    SMAFamilyDiagnosis = {
        "SMA": "SMAFamilySMA",
        "Oth": "SMAFamilyOth",
        "Unk": "SMAFamilyUnk",
        "Non": "SMAFamilyNon",
    }

    MeteorSexChoices = {
        "M": 1,
        "F": 2,
        "I": 3
    }

    NMDTechnique = {
        "MLPA": "MLPA",
        "Genomic DNA sequencing": "Genomic DNA sequencing",
        "Array": "Array",
        "cDNA sequencing": "cDNA sequencing",
    }

    TypeOfMedicalProfessional = {
        "GP (Primary Care)": 1,
        "Specialist (Lipid)": 2,
        "Primary Care": 3,
        "Paediatric Neurologist": 4,
        "Neurologist": 5,
        "Geneticist": 6,
        "Specialist - Other": 7,
        "Cardiologist": 8,
        "Nurse Practitioner": 9,
        "Paediatrician": 10
    }

    SMN1 = {'Homozygous': 'SMAHomozygous',
            'Heterozygous': 'SMAHeterozygous',
            'No': 'SMANo'}

    SMN1_CHOICES = {1: 'SMAHomozygous',
                    2: 'SMAHeterozygous',
                    3: 'SMANo'}

    GROUPS = {
        "Clinical Staff": RDRF_GROUPS.CLINICAL,
        "Genetic Curators": RDRF_GROUPS.GENETIC_CURATOR,
        "Genetic Staff": RDRF_GROUPS.GENETIC_STAFF,
        "Working Group Curators": RDRF_GROUPS.WORKING_GROUP_CURATOR,
        "Working Group Staff (Patient Registration)": RDRF_GROUPS.WORKING_GROUP_STAFF,

    }


class PatientRecord(object):

    def __init__(self, patient_dict, all_data):
        self.data = all_data.data  # unwrapped data
        self.patient_dict = patient_dict
        self.patient_id = self.patient_dict["pk"]
        self.diagnosis_dict = self._get_diagnosis()
        self.molecular_data_dict = self._get_molecular_data()
        if "pk" in self.diagnosis_dict:
            self.diagnosis_id = self.diagnosis_dict["pk"]
        else:
            self.diagnosis_id = None

    def _get_molecular_data(self):
        for thing in self.data:
            if thing["model"] == "genetic.moleculardata":
                if thing["pk"] == self.patient_id:
                    return thing

    def _get_diagnosis(self):
        d = {}
        for thing in self.data:
            if thing["model"] == "sma.diagnosis" and thing["fields"]["patient"] == self.patient_id:
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
        if model == "patients.patient":
            return self.patient_dict["fields"][field]
        elif model == "sma.diagnosis":
            if self.diagnosis_dict:
                return self.diagnosis_dict[field]
            else:
                return None
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
                    if my_id == thing["fields"][foreign_key_field]:
                        return thing["fields"][field]


MULTISECTION_MAP = {

    "SMAFamilyMember": {"model": "sma.familymember",

                        "field_map": {
                            "registry_patient": {"cde_code": "NMDRegistryPatient"},

                            "family_member_diagnosis": {"cde_code": "SMAFamilyDiagnosis",
                                                        "converter": Conv.SMAFamilyDiagnosis},

                            "relationship": {"cde_code": "NMDRelationship",
                                             },

                            "sex": {"cde_code": "NMDSex",
                                    "converter": Conv.MeteorSexChoices
                                    }
                        }},

    "NMDClinicalTrials": {"model": "sma.clinicaltrials",
                          "field_map": {
                              "drug_name": {"cde_code": "NMDDrugName"},
                              "trial_sponsor": {"cde_code": "NMDTrialSponsor"},
                              "trial_name": {"cde_code": "NMDTrialName"},
                              "trial_phase": {"cde_code": "NMDTrialPhase"},
                          }},

    "NMDOtherRegistries": {"model": "sma.otherregistries",
                           "field_map": {
                               "registry": {"cde_code": "NMDOtherRegistry"}
                           }},

    "SMAMolecular": {"model": "genetic.variationsma",
                     "path": Path.THROUGH_MOLECULAR_DATA,
                     "field_map": {
                         "gene": {"cde_code": "NMDGene",
                                  "converter": "gene"},

                         "technique": {"cde_code": "NMDTechnique",
                                       "converter": Conv.NMDTechnique},

                         "exon_7_smn1_deletion": {"cde_code": "SMAExon7Deletion",
                                                  "converter": Conv.SMN1_CHOICES},

                         "exon_7_sequencing": {"cde_code": "SMAExon7Sequencing"},

                         "dna_variation": {"cde_code": "SMADNAVariation"},

                     }},

}

# All the SMA non multisection clinical fields

DATA_MAP = {"ClinicalDiagnoses/SMAClinicalDiagnosis/SMADiagnosis": {"field": "diagnosis",
                                                                    "model": "sma.diagnosis",
                                                                    "converter": {
                                                                        "SMA": "SMASMA",
                                                                        "Unk": "SMAUnk",
                                                                        "Oth": "SMAOth"}},

            "ClinicalDiagnoses/SMAClinicalDiagnosis/SMAClassification": {"field": "classification",
                                                                         "model": "sma.diagnosis",
                                                                         "converter": {
                                                                             "SMA1": "SMASMA1",
                                                                             "SMA2": "SMASMA2",
                                                                             "SMA3": "SMASMA3",
                                                                             "Unknown": "SMAUnknown",
                                                                             "Other": "SMAOther"}},

            "ClinicalDiagnoses/NMDNotes/NMDNotes": {"field": "notes",
                                                    "model": "sma.notes"},

            # Boolean field
            "ClinicalDiagnoses/SMAMotorFunction/NMDWalk": {"field": "walk",
                                                           "model": "sma.motorfunction",
                                                           },
            # Boolean field
            "ClinicalDiagnoses/SMAMotorFunction/NMDSit": {"field": "sit",
                                                          "model": "sma.motorfunction",
                                                          },
            # Range field
            "ClinicalDiagnoses/SMAMotorFunction/SMABestFunction": {"field": "best_function",
                                                                   "model": "sma.motorfunction",
                                                                   "converter": {
                                                                       "walking": "walking",
                                                                       "sitting": "sitting",
                                                                       "none": "none",
                                                                   }
                                                                   },
            # Integer field
            "ClinicalDiagnoses/SMAMotorFunction/SMAAcquisitionAge": {"field": "acquisition_age",
                                                                     "model": "sma.motorfunction",
                                                                     },
            # Range field
            "ClinicalDiagnoses/SMAMotorFunction/NMDWheelchairChoices": {"field": "wheelchair_use",
                                                                        "model": "sma.motorfunction",
                                                                        "converter": {
                                                                            "permenant": "permenant",
                                                                            "intermittent": "intermittent",
                                                                            "never": "never",
                                                                            "unknown": "unknown",
                                                                        }
                                                                        },
            # Integer field
            "ClinicalDiagnoses/SMAMotorFunction/NMDWheelchairAge": {"field": "wheelchair_usage_age",
                                                                    "model": "sma.motorfunction",
                                                                    },
            # Range field
            "ClinicalDiagnoses/NMDSurgery/NMDSurgery": {"field": "surgery",
                                                        "model": "sma.surgery",
                                                        "converter": Conv.YNU,
                                                        },
            # Range field
            "ClinicalDiagnoses/SMAFeedingFunction/SMAGastricNasalTube": {"field": "gastric_nasal_tube",
                                                                         "model": "sma.feedingfunction",
                                                                         "converter": Conv.YNU,
                                                                         },
            # Range field
            "ClinicalDiagnoses/NMDRespiratory/NMDNonInvasive": {"field": "non_invasive_ventilation",
                                                                "model": "sma.respiratory",
                                                                "converter": {
                                                                    # the values here in the sma yaml were reused from DMD
                                                                    # should probably be changed
                                                                    "Y": "DMDY",
                                                                    "PT": "DMDPT",
                                                                    "N": "DMDN",
                                                                },
                                                                },
            # Range field
            "ClinicalDiagnoses/NMDRespiratory/NMDInvasiveVentilation": {"field": "invasive_ventilation",
                                                                        "model": "sma.respiratory",
                                                                        "converter": {
                                                                            # the values here in the sma yaml were reused from DMD
                                                                            # should probably be changed
                                                                            "Y": "DMDY",
                                                                            "PT": "DMDPT",
                                                                            "N": "DMDN",
                                                                        },
                                                                        },
            # Integer field
            "ClinicalDiagnoses/NMDRespiratory/NMDfvc": {"field": "fvc",
                                                        "model": "sma.respiratory",
                                                        },
            # Date field
            "ClinicalDiagnoses/NMDRespiratory/NMDfvcDate": {"field": "fvc_date",
                                                            "model": "sma.respiratory",
                                                            },
            "family_name": {"field": "family_name",
                            "model": "patients.patient"},
            }


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
                yield thing


def meta(stage, run_after=False):
    # consistent logging
    def decorator(func):
        func_name = func.__name__

        def wrapper(self, *args, **kwargs):
            target = self._get_target()
            log_prefix = "%s %s %s" % (stage,
                                       target,
                                       func_name)

            try:
                myargs = [self] + list(args)
                value = func(*myargs, **kwargs)
                log_line = "%s: OK" % log_prefix
                self.log(log_line)
            except ImportError as ierr:
                log_line = "%s: IMPORT ERROR! - %s" % (log_prefix,
                                                       ierr)

                value = None
                error_message = "%s" % ierr
                self.log(log_line)
                raise RollbackError(error_message)

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
        self.after_ops = []  # updates to fields to run after all patients in
        self.rdrf_context_manager = RDRFContextManager(registry_model)
        self._id_map = {}  # old to new patient ids
        self._doctor_map = {}
        self._group_map = {}
        self._user_map = {}
        self._working_group_map = {}

    def _add_parsed_permissions(self):
        p = {}
        for line in PERMISSIONS_ON_STAGING.splitlines():
            try:
                group_name, codename = [s.strip() for s in line.split(":")]
            except Exception as ex:
                self.log("could not parse line [%s] of permissions: %s" % (line,
                                                                           ex))
                continue

            if group_name in p:
                p[group_name].append(codename)
            else:
                p[group_name] = [codename]
        for group_name, codenames in p.items():
            try:
                group_model = Group.objects.get(name=group_name)
                for codename in codenames:
                    try:
                        permission_model = Permission.objects.get(
                            codename=codename)
                        group_model.permissions.add(permission_model)
                        group_model.save()
                        self.log("Added permission %s to group %s" % (permission_model,
                                                                      group_model))

                    except Permission.DoesNotExist:
                        self.log("permission %s not exist" % codename)
            except Group.DoesNotExist:
                self.log("group %s does not exist" % group_name)

    @property
    def old_id(self):
        if self.record:
            return self.record.patient_id

    @property
    def rdrf_id(self):
        if self.patient_model:
            return self.patient_model.pk

    @property
    def moniker(self):
        if self.patient_model:
            s = "PATIENT"
        else:
            s = ""

        return "%s/%s %s" % (self.rdrf_id,
                             self.old_id,
                             s)

    def log(self, msg):
        line = "IMPORTER [%s]> %s\n" % (self.moniker,
                                        msg)

        self._log.write(line)

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

    def _wire_up_family_members(self):
        for patient_model in Patient.objects.all():
            for family_member in self._get_family_members(patient_model,
                                                          "ClinicalDiagnoses",
                                                          "SMAFamilyMember",
                                                          "NMDRegistryPatient"):
                new_id = patient_map.get(family_member.old_id, None)
                if new_id:
                    self._update_family_member(family_member,
                                               "ClinicalDiagnoses",
                                               "SMAFamilyMember",
                                               "NMDRegistryPatient",
                                               new_id)
                else:
                    print("family member with old id %s doesn't exist in RDRF" %
                          family_member.old_id)

    @meta("FAMILY MEMBER")
    def _update_family_member(self, family_member, form_name, section_code, cde_code, new_id):
        # PokeFieldExpression(GeneralisedFieldExpression):
        # "[pick|poke]/<FORMNAME>/<SECTIONCODE/2/CDECODE"

        section_code = "SMAFamilyMember"
        cde_code = "NMDRegistryPatient"
        item_index = family_member.item_index
        patient_id = family_member.owning_rdrf_patient_id

        patient_model = Patient.objects.get(pk=patient_id)
        field_expression = "poke/%s/%s/%s/%s" % (form_name,
                                                 section_code,
                                                 item_index,
                                                 cde_code)

        patient_model.evaluate_field_expression(self.registry_model,
                                                field_expression,
                                                value=new_id)

        self.log("Updated family member id for %s: %s -> %s" % (patient_model.pk,
                                                                family_member.old_id,
                                                                new_id))

    def _get_family_members(self, patient_model, form_name, section_code, cde_code):
        self.log("attempting to get family members for %s %s" %
                 (patient_model, patient_model.pk))

        class FamilyMember(object):
            def __init__(self):
                self.old_id = None
                self.owning_rdrf_patient_id = None
                self.item_index = None

        try:
            clinical_data = ClinicalData.objects.get(collection="cdes",
                                                     registry_code="SMA",
                                                     django_model="Patient",
                                                     django_id=patient_model.pk)
        except ClinicalData.DoesNotExist:

            self.log("no cd object therefore no family members")
            return []

        family_members = []
        self.log("Starting to wire up family members for %s" % patient_model)
        if clinical_data.data and "forms" in clinical_data.data:
            for form_dict in clinical_data.data["forms"]:
                if form_dict["name"] == form_name:
                    for section_dict in form_dict["sections"]:
                        if section_dict["code"] == section_code:
                            for item_index, item in enumerate(section_dict["cdes"]):
                                for cde_dict in item:
                                    if cde_dict["code"] == cde_code:
                                        old_id = cde_dict["value"]
                                        if old_id:
                                            self.log("item %s old_id %s" %
                                                     (item_index, old_id))
                                            fm = FamilyMember()
                                            fm.old_id = old_id
                                            fm.owning_rdrf_patient_id = patient_model.pk
                                            fm.item_index = item_index + 1  # field expression uses 1 based index
                                            family_members.append(fm)

        if len(family_members) == 0:
            self.log("no family members (len=0)")
        else:
            self.log("There are %s family members" % len(family_members))

        return family_members

    def _load_json_data(self):
        with open(self.json_file) as jf:
            return json.load(jf)

    def update_family_members(self):
        self._wire_up_family_members()

    def run(self, country):
        self.country = country
        self._map_auth_groups()
        self._create_doctors()
        self._create_labs()
        self._create_users()

        for patient_dict in self.data.patients:
            pk = patient_dict["pk"]
            self.log("checking patient %s" % pk)
            if self._in_country(patient_dict):
                self.log("Patient is in %s" % self.country)
                self.record = PatientRecord(patient_dict, self.data)
                self._process_record()
            else:
                self.log("patient %s is not in %s" % (pk,
                                                      self.country))

        self._assign_user_working_groups()
        # self._assign_permissions_to_groups()
        self._add_parsed_permissions()
        self._create_email_templates()
        self._wire_up_family_members()
        self._update_form_progress()
        self._munge_diagnosis_currency()

    def _in_country(self, patient_dict):
        working_group_id = patient_dict["fields"]["working_group"]
        self.log("working_group_id = %s" % working_group_id)
        if self.country == "NZ":
            return working_group_id == NZ_WORKING_GROUP_ID
        else:
            return working_group_id != NZ_WORKING_GROUP_ID

    def _map_auth_groups(self):
        for thing in self.data.data:
            if thing["model"] == "auth.group":
                name = thing["fields"]["name"]
                rdrf_group_name = Conv.GROUPS.get(name, None)
                if rdrf_group_name is None:
                    self.log("Bad group name: %s" % name)
                    raise Exception("Bad group: %s" % name)

                try:
                    group_model = Group.objects.get(
                        name__iexact=rdrf_group_name)
                except Group.DoesNotExist:
                    raise Exception(
                        "Group model %s does not exist?" % rdrf_group_name)

                self._group_map[thing["pk"]] = group_model

    def _create_users(self):
        for thing in self.data.data:
            if thing["model"] == "auth.user":
                username = thing["fields"]["username"]
                if not self._user_in_country(thing):
                    self.log("user %s not in %s - skipping" % (username,
                                                               self.country))
                    continue
                if username == "admin":
                    continue

                user = CustomUser()
                user.username = username
                user.first_name = thing["fields"]["first_name"]
                user.last_name = thing["fields"]["last_name"]
                user.last_login = thing["fields"]["last_login"]
                user.email = thing["fields"]["email"]
                user.date_joined = thing["fields"]["date_joined"]
                user.password = thing["fields"]["password"]
                user.is_superuser = thing["fields"]["is_superuser"]
                user.is_active = thing["fields"]["is_active"]
                user.is_staff = True
                user.save()
                self._user_map[user.pk] = thing["pk"]
                user.registry = [self.registry_model]
                user.save()

                self._assign_user_groups(user, thing["fields"]["groups"])

    def _user_in_country(self, user_dict):
        self.log("user_dict = %s" % user_dict)
        working_groups = self._get_working_groups_for_user(user_dict)
        if self.country == "NZ":
            return NZ_WORKING_GROUP_ID in working_groups
        else:
            return NZ_WORKING_GROUP_ID not in working_groups

    def _get_working_groups_for_user(self, user_dict):
        pk = user_dict["pk"]
        for thing in self.data.data:
            if thing["model"] == "groups.user" and thing["pk"] == pk:
                return thing["fields"]["working_groups"]
        return []

    def _assign_permissions_to_groups(self):
        permission_map = {}

        for thing in self.data.data:
            if thing["model"] == "auth.permission":
                permission_map[thing["pk"]] = thing["fields"]["codename"]

        for thing in self.data.data:
            if thing["model"] == "auth.group":
                group_model = self._group_map.get(thing["pk"], None)
                if group_model is not None:
                    for old_perm_id in thing["fields"]["permissions"]:
                        codename = permission_map.get(old_perm_id, None)
                        if codename is not None:
                            try:
                                permission_model = Permission.objects.get(
                                    codename=codename)
                                group_model.permissions.add(permission_model)
                                group_model.save()
                                self.log("Added %s permission to group %s" % (codename,
                                                                              group_model))
                            except Permission.DoesNotExist:
                                self.log("permission %s does not exist" %
                                         codename)

    def _assign_user_working_groups(self):
        # working group info is stored in the parent class "groups.user" ...
        # this is one one with auth.user, hence pks match
        # we've mapped all working groups as we iterated through
        # all patients
        for user_model in CustomUser.objects.all():
            if user_model.username == "admin":
                continue
            custom_user_old_id = self._user_map.get(user_model.pk, None)
            if custom_user_old_id is None:
                continue

            for thing in self.data.data:
                if thing["pk"] == custom_user_old_id:
                    if thing["model"] == "groups.user":
                        for old_working_group_id in thing["fields"]["working_groups"]:
                            working_group_model = self._working_group_map.get(
                                old_working_group_id, None)
                            if working_group_model is not None:
                                user_model.working_groups.add(
                                    working_group_model)
                                user_model.save()
                                self.log(
                                    "Assigned user %s to working group %s" %
                                    (user_model, working_group_model))
                            else:
                                self.log(
                                    "missing working group with old id %s" %
                                    old_working_group_id)

                        # title is stored on this object too
                        user_model.title = thing["fields"]["title"]
                        user_model.save()

    def _assign_user_groups(self, user_model, old_group_ids):
        for old_group_id in old_group_ids:
            group_model = self._group_map.get(old_group_id, None)
            if group_model is not None:
                user_model.groups.add(group_model)
                user_model.save()
                self.log("Added user %s to group %s" % (user_model,
                                                        group_model))

            else:
                self.log("Unknown group id %s" % old_group_id)

    def _process_record(self):
        self.patient_model = self._create_patient()
        self._update_diagnosis_currency_map(self.patient_model, self.old_id)
        self._assign_address()
        self._set_consent()
        self._assign_doctors()

        self._id_map[self.record.patient_id] = self.patient_model.pk

        for form_model in self.registry_model.forms:
            self.form_model = form_model
            for section_model in form_model.section_models:
                self.section_model = section_model
                self._process_section()

        if not self.active:
            self.patient_model.active = False
            self.patient_model.save()

    def _update_diagnosis_currency_map(self, patient_model, old_id):
        def get_updated(pk):
            for thing in self.data.data:
                if thing["pk"] == pk:
                    if thing["model"] == "sma.diagnosis":
                        return thing["fields"]["updated"]

        diagnosis_currency_map[patient_model.pk] = get_updated(old_id)

    @meta("DEMOGRAPHICS")
    def _create_patient(self):
        p = Patient()
        p.family_name = self.record.get("family_name")
        p.given_names = self.record.get("given_names")
        p.place_of_birth = self.record.get("place_of_birth")
        p.sex = Conv.MeteorSexChoices.get(self.record.get("sex"), None)
        p.date_of_birth = self.record.get("date_of_birth")
        p.consent = self.record.get("consent")
        p.active = self.record.get("active")
        if not p.active:
            self.active = False
        else:
            self.active = True
        p.umrn = self.record.get("umrn")
        p.home_phone = self.record.get("home_phone")
        p.mobile_phone = self.record.get("mobile_phone")
        p.work_phone = self.record.get("work_phone")
        p.email = self.record.get("email")
        p.active = self.record.get("active")
        p.inactive_reason = self.record.get("inactive_reason")

        # next of kin fields

        self._set_field(p, "next_of_kin_family_name")
        self._set_field(p, "next_of_kin_given_names")
        self._set_field(p, "next_of_kin_email")
        self._set_field(p, "next_of_kin_address")
        self._set_field(p, "next_of_kin_home_phone")
        self._set_field(p, "next_of_kin_mobile_phone")
        self._set_field(p, "next_of_kin_parent_place_of_birth")
        self._set_field(p, "next_of_kin_postcode")
        self._set_field(p, "next_of_kin_relationship")

        # old system assumes Au for nok
        nok_state = self.record.get("next_of_kin_state")
        if nok_state is not None:
            if nok_state == NZ_ABBREV:
                # NZ patients are anomolous in old registry ...
                p.next_of_kin_state = None
                p.next_of_kin_country = "NZ"
            else:
                p.next_of_kin_state = "AU-" + self.record.get("next_of_kin_state")
                p.next_of_kin_country = "AU"

        self._set_field(p, "next_of_kin_suburb")
        self._set_field(p, "next_of_kin_work_phone")
        p.save()
        p.rdrf_registry = [self.registry_model]
        p.save()
        wg = self._get_working_group()

        if wg is not None:
            p.working_groups = [wg]
            p.save()
            self.log("assigned to working group %s" % wg)

        self.context_model = self.rdrf_context_manager.get_or_create_default_context(
            p, new_patient=True)
        self.log("created default context %s" % self.context_model)
        # ensure that we have a map of old patient ids to new ones
        patient_map[self.record.patient_id] = p.pk
        self.log("Updated patient map: %s -> %s" % (self.record.patient_id,
                                                    p.pk))
        return p

    def _set_field(self, patient_model, attr, conv=None):
        value = self.record.get(attr)
        if conv is None:
            setattr(patient_model, attr, value)
        else:
            setattr(patient_model, attr, conv(value))

    def _set_consent(self):
        # this sets the visible consent
        consent_value = self.record.get("consent")

        consent_section_model = ConsentSection.objects.get(code="smaconsent1",
                                                           registry=self.registry_model)

        consent_question_model = ConsentQuestion.objects.get(section=consent_section_model,
                                                             code="c1")

        answer_field_expression = "Consents/%s/%s/answer" % (consent_section_model.code,
                                                             consent_question_model.code)

        self.patient_model.evaluate_field_expression(self.registry_model,
                                                     answer_field_expression,
                                                     value=consent_value)

    def _assign_address(self):
        address = self.record.get("address")
        suburb = self.record.get("suburb")
        postcode = self.record.get("postcode")
        state = self.record.get("state")
        country_code = self._get_country_code(state)

        address_model = PatientAddress()
        address_model.address = address
        address_model.suburb = suburb
        address_model.postcode = postcode
        address_model.patient = self.patient_model
        address_model.state = country_code + "-" + state
        address_model.country = country_code
        address_model.save()

    def _create_doctors(self):
        # make a map as we go
        for thing in self.data.data:
            if thing["model"] == "patients.doctor":
                flds = thing["fields"]
                doc = Doctor()
                doc.family_name = flds["family_name"]
                doc.given_names = flds["given_names"]
                doc.speciality = flds["speciality"]
                doc.email = flds["email"]
                doc.surgery_name = flds["surgery_name"]
                doc.address = flds["address"]
                doc.phone = flds["phone"]
                doc.suburb = flds["suburb"]
                doc.state = None  # todo
                doc.save()
                self._doctor_map[thing["pk"]] = doc

    def _assign_doctors(self):
        # create them if they don't exist
        my_doctors = []

        for thing in self.data.data:
            if thing["model"] == "patients.patientdoctor":
                if thing["fields"]["patient"] == self.record.patient_id:
                    my_doctors.append(thing)

        for doctor_dict in my_doctors:
            self._assign_doctor(doctor_dict)

    def _assign_doctor(self, doctor_dict):
        # doctors have already been created
        doctor_old_pk = doctor_dict["fields"]["doctor"]
        doctor_model = self._doctor_map.get(doctor_old_pk, None)

        if doctor_model is not None:
            patient_doctor = PatientDoctor()
            patient_doctor.patient = self.patient_model
            patient_doctor.doctor = doctor_model
            old_relationship = doctor_dict["fields"]["relationship"]

            relationship_num = Conv.TypeOfMedicalProfessional.get(old_relationship,
                                                                  None)
            if relationship_num is not None:
                patient_doctor.relationship = relationship_num
            else:
                self.log("Unknown relationship: %s" % old_relationship)

            patient_doctor.save()
            self.log("assigned doctor %s " % doctor_model.pk)
        else:
            self.log("can't locate doctor with old pk %s" % doctor_old_pk)

    def _create_labs(self):
        for thing in self.data.data:
            if thing["model"] == "genetic.laboratory":
                lab = Laboratory()
                lab.name = thing["fields"]["name"]
                lab.address = thing["fields"]["address"]
                lab.contact_name = thing["fields"]["contact_name"]
                lab.contact_phone = thing["fields"]["contact_phone"]
                lab.contact_email = thing["fields"]["contact_email"]
                lab.save()
                self.log("created lab %s" % lab)

    def _get_country_code(self, state):
        if state == NZ_ABBREV:
            return "NZ"

        return "AU"  # ???

    def convert_gene(self, gene_id):
        for thing in self.data.data:
            if thing["pk"] == gene_id and thing["model"] == "genetic.gene":
                symb = thing["fields"]["symbol"]
                return symb

    def _get_working_group(self):
        wg_old_pk = self.record.get("working_group")
        for thing in self.data.data:
            if thing["pk"] == wg_old_pk:
                if thing["model"] == "groups.workinggroup":
                    working_group_name = thing["fields"]["name"]
                    working_group_model, created = WorkingGroup.objects.get_or_create(
                        name=working_group_name, registry=self.registry_model)

                    if created:
                        self.log("created working group %s" %
                                 working_group_name)
                        working_group_model.save()

                    if thing["pk"] not in self._working_group_map:
                        self._working_group_map[thing["pk"]
                                                ] = working_group_model

                    return working_group_model

    @meta("SECTION")
    def _process_section(self):
        if not self.section_model.allow_multiple:
            for cde_model in self.section_model.cde_models:
                self.cde_model = cde_model
                self._process_cde()
        else:
            self._process_multisection()

    def _get_multisection_related_model_info(self, multisection_code):
        # return model , foreign key field
        ms_map = MULTISECTION_MAP[multisection_code]
        path = ms_map.get("path", Path.THROUGH_DIAGNOSIS)
        if path == Path.THROUGH_DIAGNOSIS:
            return "diagnosis", "diagnosis"
        elif path == Path.THROUGH_PATIENT:
            return "patient", "patient"
        elif path == Path.THROUGH_MOLECULAR_DATA:
            return "genetic.moleculardata", "molecular_data"
        else:
            return None, None

    @meta("MULTISECTION")
    def _process_multisection(self):
        self.log("processing multisection %s" % self.section_model.code)
        old_model = self._get_old_multisection_model(self.section_model.code)
        old_items = []

        related_model, related_model_field = self._get_multisection_related_model_info(
            self.section_model.code)

        if related_model == "diagnosis":
            model_id = self.record.diagnosis_dict[
                "pk"] if self.record.diagnosis_dict else None
        elif related_model == "genetic.moleculardata":
            if self.record.molecular_data_dict:
                model_id = self.record.molecular_data_dict["pk"]
            else:
                model_id = None
        elif related_model == "patient":
            model_id = self.record.patient_id
        else:
            model_id = None
            self.log("no related model_id for %s" % old_model)

        items = []   # a list of lists

        for thing in self.data.data:
            if thing["model"] == old_model:
                if related_model_field in thing["fields"].keys():
                    if thing["fields"][related_model_field] == model_id:
                        old_items.append(thing)

        self.log("Number of old %s = %s" % (old_model,
                                            len(old_items)))

        for item in old_items:
            item = self._create_new_multisection_item(
                item, key_field=related_model_field)
            items.append(item)

        if len(items) > 0:
            self.log("%s multisection items for code %s" % (len(items),
                                                            self.section_model.code))
            self._save_new_multisection_data(items)

    def _get_old_multisection_model(self, section_code):
        if section_code in MULTISECTION_MAP:
            return MULTISECTION_MAP[section_code]["model"]
        else:
            raise Exception("unknown multisection: %s" % section_code)

    def _create_new_multisection_item(self, old_item, key_field="diagnosis"):
        mm_map = MULTISECTION_MAP[self.section_model.code]

        field_map = mm_map["field_map"]

        if not field_map:
            raise Exception("need field map for multisection %s" %
                            self.section_model.code)

        item = []

        # item should be a list of {code:  value: } dicts

        for old_field in old_item["fields"].keys():
            d = {}

            if old_field == key_field:
                continue

            if old_field in SKIP_FIELDS:
                continue

            self.log("converting old field %s in model %s" % (old_field,
                                                              old_item["model"]))

            new_data = field_map[old_field]
            new_cde_code = new_data["cde_code"]
            converter = new_data.get("converter", None)
            if converter:
                converter_func = self._get_converter_func(converter)
            else:
                converter_func = None

            old_value = old_item["fields"][old_field]
            if converter_func is not None:
                value = converter_func(old_value)
            else:
                value = old_value

            d["code"] = new_cde_code
            d["value"] = value
            item.append(d)

        return item

    def _save_new_multisection_data(self, new_multisection_data):
        field_expression = "$op/%s/%s/items" % (self.form_model.name,
                                                self.section_model.code)

        self.log("saving field_expression = %s" % field_expression)

        fe = MultiSectionItemsExpression(self.registry_model,
                                         self.form_model,
                                         self.section_model)

        dynamic_data = self.patient_model.get_dynamic_data(self.registry_model)

        try:
            _, dynamic_data = fe.set_value(self.patient_model,
                                           dynamic_data,
                                           new_multisection_data)
        except Exception as ex:
            self.log("could not set multisection items for %s: %s" % (field_expression,
                                                                      ex))
            return

        if "context_id" not in dynamic_data:
            dynamic_data["context_id"] = self.context_model.pk

        self.patient_model.update_dynamic_data(
            self.registry_model, dynamic_data)
        self.log("updated multisection %s OK" % field_expression)

    @meta("CDE")
    def _process_cde(self):
        field_expression = self._get_current_field_expression()
        self.log("process cde %s" % field_expression)
        info = DATA_MAP.get(field_expression, None)
        if info:
            model = info["model"]
            field = info["field"]
            # Most objects are related to patient via the diagnosis
            path = info.get("path", Path.THROUGH_DIAGNOSIS)
            converter = info.get("converter", None)
            old_value = self.record.get(field, model, path)
            if old_value is not None:
                if converter is not None:
                    self.log("converter will be used")
                    converter_func = self._get_converter_func(converter)
                    new_value = converter_func(old_value)
                else:
                    self.log("No converter - raw value will be used")
                    new_value = old_value
                self._save_cde(new_value)
                self.log("%s [%s] --> [%s] OK" % (field_expression,
                                                  old_value,
                                                  new_value))

        else:
            raise Exception("Unknown field expression: %s" % field_expression)

    def _get_converter_func(self, converter):
        if isinstance(converter, dict):
            return lambda key: converter.get(key, None)
        else:
            converter_func_name = "convert_%s" % converter
            if hasattr(self, converter_func_name):
                converter_func = getattr(self, converter_func_name)
                if callable(converter_func):
                    return converter_func
                else:
                    raise Exception(
                        "converter for %s is not callable" % converter_func_name)
            else:
                raise Exception("Unknown converter func %s" %
                                converter_func_name)

    @meta("SAVECDE")
    def _save_cde(self, value):
        field_expression = self._get_current_field_expression()
        if self.cde_model.pv_group:
            if value is None:
                self.log("range value is None so skipping")
                return
            range_members = self.cde_model.get_range_members()
            if value not in range_members:
                raise Exception("Bad range member: %s not in %s" %
                                (value, range_members))

        self._evaluate_field_expression(field_expression, value)

    def _get_current_field_expression(self):
        return "%s/%s/%s" % (self.form_model.name,
                             self.section_model.code,
                             self.cde_model.code)

    def _evaluate_field_expression(self, field_expression, value):
        self.patient_model.evaluate_field_expression(self.registry_model,
                                                     field_expression,
                                                     value=value)

    def _update_form_progress(self):
        from django.core.management import call_command
        call_command('update_form_progress', 'SMA')

    def _munge_diagnosis_currency(self):
        for patient_id, old_timestamp in diagnosis_currency_map.items():
            self.log("Updating %s with old timestamp %s" % (patient_id,
                                                            old_timestamp))
            try:
                patient_model = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                self.log("can't munge timestamp for %s patient doesn't exist" % patient_id)
                continue

            try:
                clinical_data = ClinicalData.objects.get(django_model="Patient",
                                                         django_id=patient_model.pk,
                                                         collection="cdes")
                if clinical_data.data and "forms" in clinical_data.data:
                    data = clinical_data.data
                    for form_dict in data["forms"]:
                        name = form_dict["name"].lower()
                        if "genetic" in name:
                            continue

                        for k in form_dict.keys():
                            if "timestamp" in k:
                                form_dict[k] = old_timestamp

                    clinical_data.data = data
                    clinical_data.save()
                    self.log("saved updated clinical data for %s" % patient_id)
            except ClinicalData.DoesNotExist:
                self.log("clinical data does not exist")

            # update diagnosis group currency
            self._update_diagnosis_group_currency(patient_model, old_timestamp)

    def _update_diagnosis_group_currency(self, patient_model, old_timestamp):
        self.log("Updating diagnosis group currency for %s --> %s" % (patient_model.pk,
                                                                      old_timestamp))
        updated_dt = parse_iso_datetime(old_timestamp)
        if updated_dt is None:
            current = False
        else:
            current = updated_dt < ONE_YEAR_AGO

        try:
            progress = ClinicalData.objects.get(collection="progess",
                                                registry_code="SMA",
                                                data__django_id=patient_model.pk,
                                                data__django_model="Patient")
            if progress.data:
                progress.data["diagnosis_group_current"] = current
                progress.save()
                self.log("Updated patient %s diagnosis_group_current = %s" % (patient_model.pk,
                                                                              current))
        except ClinicalData.DoesNotExist:
            self.log("no progress object for patient %s" % patient_model.pk)

    def _create_email_templates(self):
        for thing in self.data.data:
            if thing["model"] == "configuration.emailtemplate":
                self._create_email_template(thing)

    def _create_email_template(self, email_template_dict):
        groups = filter(lambda x: x is not None,
                        [self._group_map.get(k, None) for k
                         in email_template_dict["fields"]["groups"]])

        email_template = EmailTemplate()
        email_template.language = "en"
        email_template.description = email_template_dict["fields"]["name"]

        old_body = email_template_dict["fields"]["body"]

        lines = old_body.splitlines()
        new_subject_line = lines[0]
        new_body = "\n".join(lines[1:])

        email_template.subject = new_subject_line
        email_template.body = new_body
        email_template.save()

        # create a notification for each group

        for group_model in groups:
            email_notification = EmailNotification()
            email_notification.description = "new-patient"
            email_notification.registry = self.registry_model
            email_notification.recipient = "{{user.email}}"
            email_notification.group_recipient = group_model
            email_notification.save()
            email_notification.email_templates = [email_template]
            email_notification.save()


if __name__ == "__main__":
    registry_code = sys.argv[1]
    country = sys.argv[2]
    json_file = sys.argv[3]
    registry_model = Registry.objects.get(code=registry_code)
    importer = OldRegistryImporter(registry_model, json_file)
    try:
        with transaction.atomic():
            importer.run(country)
            importer.log("run completed")
    except Exception as ex:
        importer.log("run failed - rolled back: %s" % ex)
