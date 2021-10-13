# -*- encoding: utf-8 -*-
import json
import logging
import os
import subprocess
import yaml
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.forms.models import model_to_dict
from django.test import TestCase, RequestFactory
from rdrf.forms.fields import calculated_functions
from rdrf.helpers.transform_cd_dict import get_cd_form, get_section, transform_cd_dict
from rdrf.helpers.utils import de_camelcase, TimeStripper
from rdrf.models.definition.models import CDEPermittedValueGroup, CDEPermittedValue
from rdrf.models.definition.models import ClinicalData
from rdrf.models.definition.models import CommonDataElement, InvalidAbnormalityConditionError, ValidationError
from rdrf.models.definition.models import EmailNotification
from rdrf.models.definition.models import EmailNotificationHistory
from rdrf.models.definition.models import EmailTemplate
from rdrf.models.definition.models import Registry, RegistryForm, Section
from rdrf.models.proms.models import Survey, SurveyQuestion, Precondition
from rdrf.services.io.defs.exporter import Exporter, ExportType
from rdrf.services.io.defs.importer import Importer, ImportState
from rdrf.views.form_view import FormView
from registry.groups.models import WorkingGroup, CustomUser
from registry.patients.models import Patient
from registry.patients.models import State, PatientAddress, AddressType

logger = logging.getLogger(__name__)


class CalculatedFunctionsTestCase(TestCase):

    def setUp(self):
        # Note that we convert the string date as a date django date
        patient_date_of_birth = '2000-05-17'
        self.patient_values = {'date_of_birth': datetime.strptime(patient_date_of_birth, '%Y-%m-%d'),
                               'sex': 1}

    def test_cdefhdutchlipidclinicnetwork_all_cap_reached(self):
        self.form_values = {'CDE00001': 'y',
                            'CDE00002': 'y',
                            'CDE00003': 'fh2_y',
                            'CDE00004': 'fh2_y',
                            'CDE00011': 'fhpremcvd_yes_corheartdisease',
                            'CDE00013': 10.0,
                            'CDEIndexOrRelative': 'fh_is_index',
                            'DateOfAssessment': '2019-05-10',
                            'FHFamHistArcusCornealis': 'fh2_y',
                            'FHFamHistTendonXanthoma': 'fh2_y',
                            'FHFamilyHistoryChild': 'fh_n',
                            'FHPersHistCerebralVD': 'fh2_y',
                            'LDLCholesterolAdjTreatment': '21.74'}
        self.assertEqual(calculated_functions.CDEfhDutchLipidClinicNetwork(self.patient_values, self.form_values), '18')

    def test_cdefhdutchlipidclinicnetwork_2(self):
        self.patient_values = {'date_of_birth': datetime.strptime('1990-01-01', '%Y-%m-%d'),
                               'sex': 2}
        self.form_values = {'CDE00001': 'y',
                            'CDE00002': 'y',
                            'CDE00003': 'fh2_n',
                            'CDE00004': 'fh2_n',
                            'CDE00011': 'fhpremcvd_yes_corheartdisease',
                            'CDE00013': '',
                            'CDEIndexOrRelative': 'fh_is_index',
                            'DateOfAssessment': '2016-01-09',
                            'FHFamHistArcusCornealis': 'fh2_n',
                            'FHFamHistTendonXanthoma': 'fh2_n',
                            'FHFamilyHistoryChild': 'fh_n',
                            'FHPersHistCerebralVD': 'fh2_y',
                            'LDLCholesterolAdjTreatment': '6'}
        self.assertEqual(calculated_functions.CDEfhDutchLipidClinicNetwork(self.patient_values, self.form_values), '11')

    def test_cdefhdutchlipidclinicnetwork_3(self):
        self.patient_values = {'date_of_birth': datetime.strptime('2000-10-01', '%Y-%m-%d'),
                               'sex': 1}
        self.form_values = {'CDE00001': 'n',
                            'CDE00002': 'n',
                            'CDE00003': 'fh2_y',
                            'CDE00004': 'fh2_y',
                            'CDE00011': 'fhpremcvd_no',
                            'CDE00013': 12.0,
                            'CDEIndexOrRelative': 'fh_is_relative',
                            'DateOfAssessment': '2016-10-01',
                            'FHFamHistArcusCornealis': 'fh2_n',
                            'FHFamHistTendonXanthoma': 'fh2_n',
                            'FHFamilyHistoryChild': 'fh_y',
                            'FHPersHistCerebralVD': 'fh2_y',
                            'LDLCholesterolAdjTreatment': None}
        self.assertEqual(calculated_functions.CDEfhDutchLipidClinicNetwork(self.patient_values, self.form_values), '')

    def test_cde00024(self):
        self.form_values = {'CDE00003': 'fh2_y',
                            'CDE00004': 'fh2_y',
                            'CDE00013': 10.0,
                            'CDEfhDutchLipidClinicNetwork': '24',
                            'CDEIndexOrRelative': 'fh_is_index',
                            'DateOfAssessment': '2019-05-10',
                            'FHFamHistArcusCornealis': 'fh2_y',
                            'FHFamHistTendonXanthoma': 'fh2_y',
                            'LDLCholesterolAdjTreatment': '21.74'}
        self.assertEqual(calculated_functions.CDE00024(self.patient_values, self.form_values), 'Definite')

    def test_ldlcholesteroladjtreatment(self):
        self.form_values = {'CDE00019': 10.0,
                            'PlasmaLipidTreatment': 'FAEzetimibe/atorvastatin20'}
        self.assertEqual(calculated_functions.LDLCholesterolAdjTreatment(
            self.patient_values, self.form_values), '21.74')

    def test_cdebmi(self):
        self.form_values = {'CDEHeight': "",
                            'CDEWeight': ""}
        self.assertEqual(calculated_functions.CDEBMI(self.patient_values, self.form_values), 'NaN')
        self.form_values = {'CDEHeight': 1.82,
                            'CDEWeight': 86.0}
        self.assertEqual(calculated_functions.CDEBMI(self.patient_values, self.form_values), '25.96')

    def test_fhdeathage(self):
        self.form_values = {'FHDeathDate': ""}
        self.assertEqual(calculated_functions.FHDeathAge(self.patient_values, self.form_values), 'NaN')
        self.form_values = {'FHDeathDate': '2019-05-11'}
        self.assertEqual(calculated_functions.FHDeathAge(self.patient_values, self.form_values), '18')

    def test_ddageatdiagnosis(self):
        self.form_values = {'DateOfDiagnosis': ""}
        self.assertEqual(calculated_functions.DDAgeAtDiagnosis(self.patient_values, self.form_values), 'NaN')
        self.form_values = {'DateOfDiagnosis': '2019-05-01'}
        self.assertEqual(calculated_functions.DDAgeAtDiagnosis(self.patient_values, self.form_values), '18')

    def test_poemscore(self):
        self.form_values = {'poemQ1': "", 'poemQ2': "", 'poemQ3': "", 'poemQ4': "", 'poemQ5': "", 'poemQ6': "",
                            'poemQ7': ""}
        self.assertEqual(calculated_functions.poemScore(self.patient_values, self.form_values), 'UNSCORED')
        self.form_values = {'poemQ1': "", 'poemQ2': "", 'poemQ3': "1to2Days", 'poemQ4': "1to2Days",
                            'poemQ5': "1to2Days", 'poemQ6': "1to2Days", 'poemQ7': "1to2Days"}
        self.assertEqual(calculated_functions.poemScore(self.patient_values, self.form_values), 'UNSCORED')
        self.form_values = {'poemQ1': "", 'poemQ2': "NoDays", 'poemQ3': "NoDays", 'poemQ4': "NoDays",
                            'poemQ5': "NoDays", 'poemQ6': "NoDays", 'poemQ7': "NoDays"}
        self.assertEqual(calculated_functions.poemScore(self.patient_values, self.form_values),
                         '0 ( Clear or almost clear )')
        self.form_values = {'poemQ1': "NoDays", 'poemQ2': "NoDays", 'poemQ3': "NoDays", 'poemQ4': "NoDays",
                            'poemQ5': "NoDays", 'poemQ6': "NoDays", 'poemQ7': "NoDays"}
        self.assertEqual(calculated_functions.poemScore(self.patient_values, self.form_values),
                         '0 ( Clear or almost clear )')
        self.form_values = {'poemQ1': "NoDays", 'poemQ2': "1to2Days", 'poemQ3': "1to2Days", 'poemQ4': "1to2Days",
                            'poemQ5': "1to2Days", 'poemQ6': "1to2Days", 'poemQ7': "1to2Days"}
        self.assertEqual(calculated_functions.poemScore(self.patient_values, self.form_values), '6 ( Mild eczema )')
        self.form_values = {'poemQ1': "EveryDay", 'poemQ2': "EveryDay", 'poemQ3': "EveryDay", 'poemQ4': "EveryDay",
                            'poemQ5': "EveryDay", 'poemQ6': "EveryDay", 'poemQ7': "EveryDay"}
        self.assertEqual(calculated_functions.poemScore(
            self.patient_values, self.form_values), '28 ( Very severe eczema )')


class AbnormalityRulesTestCase(TestCase):

    def setUp(self):
        self.cde = CommonDataElement()
        self.cde.datatype = "integer"

    def test_integer(self):
        self.cde.abnormality_condition = "x < 10"
        self.assertTrue(self.cde.is_abnormal(9))
        self.assertFalse(self.cde.is_abnormal(10))
        self.assertFalse(self.cde.is_abnormal(11))

    def test_minus_integer(self):
        self.cde.abnormality_condition = "x <= -10"
        self.assertTrue(self.cde.is_abnormal(-11))
        self.assertTrue(self.cde.is_abnormal(-10))
        self.assertFalse(self.cde.is_abnormal(-9))
        self.assertFalse(self.cde.is_abnormal(0))
        self.assertFalse(self.cde.is_abnormal(10))

    def test_float(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "x < 10.2"
        self.assertTrue(self.cde.is_abnormal(9))
        self.assertTrue(self.cde.is_abnormal(10))
        self.assertTrue(self.cde.is_abnormal(10.0))
        self.assertTrue(self.cde.is_abnormal(10.1))
        self.assertFalse(self.cde.is_abnormal(10.2))
        self.assertFalse(self.cde.is_abnormal(11))

    def test_assignment_rule(self):
        self.cde.abnormality_condition = "x = 10"
        self.assertRaises(InvalidAbnormalityConditionError, self.cde.is_abnormal, value=9)

    def test_multiple_rules_same_line(self):
        self.cde.abnormality_condition = "x < 2   x > 100"
        self.assertRaises(InvalidAbnormalityConditionError, self.cde.is_abnormal, value=9)

    def test_integer_range(self):
        self.cde.abnormality_condition = "2 < x < 10"
        self.assertRaises(InvalidAbnormalityConditionError, self.cde.is_abnormal, value=9)

    def test_float_range(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "2.0 < x <= 10.0"
        self.assertRaises(InvalidAbnormalityConditionError, self.cde.is_abnormal, value=9)

    def test_unsupported_datatype(self):
        self.cde.datatype = "boolean"
        self.cde.abnormality_condition = "x == 1"
        self.assertRaises(ValidationError, self.cde.is_abnormal, value=9)

    def test_number_equality(self):
        self.cde.abnormality_condition = "x == 10"
        self.assertFalse(self.cde.is_abnormal(9))
        self.assertTrue(self.cde.is_abnormal(10))
        self.assertFalse(self.cde.is_abnormal(11))

    def test_float_equality(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "x == 10.2"
        self.assertFalse(self.cde.is_abnormal(10))
        self.assertTrue(self.cde.is_abnormal(10.2))
        self.assertFalse(self.cde.is_abnormal(10.3))

    def test_minus_float_equality(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "x == -10.2"
        self.assertFalse(self.cde.is_abnormal(10.2))
        self.assertTrue(self.cde.is_abnormal(-10.2))
        self.cde.abnormality_condition = "x == -10.0"
        self.assertTrue(self.cde.is_abnormal(-10))
        self.assertTrue(self.cde.is_abnormal(-10.0))
        self.assertFalse(self.cde.is_abnormal(-10.2))

    def test_bad_float(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "x == 10."
        self.assertRaises(InvalidAbnormalityConditionError, self.cde.is_abnormal, value=9)

    def test_second_bad_float(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "x == 10.1."
        self.assertRaises(InvalidAbnormalityConditionError, self.cde.is_abnormal, value=9)

    def test_third_bad_float(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "x == 10.1.2"
        self.assertRaises(InvalidAbnormalityConditionError, self.cde.is_abnormal, value=9)

    def test_string_equality(self):
        self.cde.datatype = "range"
        self.cde.abnormality_condition = "x == \"10\""
        self.assertFalse(self.cde.is_abnormal(10))
        self.assertTrue(self.cde.is_abnormal("10"))
        self.assertFalse(self.cde.is_abnormal("11"))

    def test_empty_lines(self):
        self.cde.abnormality_condition = "x < 10\r\n\r\n"
        self.assertTrue(self.cde.is_abnormal(9))
        self.assertFalse(self.cde.is_abnormal(10))
        self.assertFalse(self.cde.is_abnormal(11))

    def test_whitespaces(self):
        self.cde.abnormality_condition = "  x   <   10  \r\n  "
        self.assertTrue(self.cde.is_abnormal(9))
        self.assertFalse(self.cde.is_abnormal(10))
        self.assertFalse(self.cde.is_abnormal(11))

    def test_in_number_list(self):
        self.cde.abnormality_condition = "x in [-2,10,20,30]"
        self.assertFalse(self.cde.is_abnormal(-10))
        self.assertTrue(self.cde.is_abnormal(-2))
        self.assertFalse(self.cde.is_abnormal(9))
        self.assertTrue(self.cde.is_abnormal(10))
        self.assertTrue(self.cde.is_abnormal(20))
        self.assertTrue(self.cde.is_abnormal(30))
        # self.assertFalse(self.cde.is_abnormal("10"))
        self.assertFalse(self.cde.is_abnormal(11))

    def test_in_float_list(self):
        self.cde.datatype = "float"
        self.cde.abnormality_condition = "x in [10.0,20.0,30.0]"
        self.assertFalse(self.cde.is_abnormal(9))
        self.assertTrue(self.cde.is_abnormal(10))
        self.assertTrue(self.cde.is_abnormal(10.0))
        self.assertTrue(self.cde.is_abnormal(20))
        self.assertTrue(self.cde.is_abnormal(20.0))
        self.assertTrue(self.cde.is_abnormal(30))
        self.assertTrue(self.cde.is_abnormal(30.0))
        # self.assertFalse(self.cde.is_abnormal("10"))
        # self.assertFalse(self.cde.is_abnormal("10.0"))
        self.assertFalse(self.cde.is_abnormal(11))
        self.assertFalse(self.cde.is_abnormal(10.3))

    def test_in_string_list(self):
        self.cde.datatype = "range"
        self.cde.abnormality_condition = "x in [\"10\",\"20\",\"30\"]"
        self.assertFalse(self.cde.is_abnormal(10))
        self.assertTrue(self.cde.is_abnormal("10"))
        self.assertTrue(self.cde.is_abnormal("20"))
        self.assertTrue(self.cde.is_abnormal("30"))
        self.assertFalse(self.cde.is_abnormal("11"))

    def test_multiple_rules(self):
        self.cde.abnormality_condition = "x < 2 \r\nx > 100"
        self.assertTrue(self.cde.is_abnormal(1))
        self.assertFalse(self.cde.is_abnormal(10))
        self.assertFalse(self.cde.is_abnormal(30.1))
        self.assertTrue(self.cde.is_abnormal(110))


class MigrateCDESTestCase(TestCase):

    def setUp(self):
        # source section with multi-value
        self.input_data = {'forms': [{'name': 'ClinicalData', 'sections': [{'cdes': [{'code': 'CDEIndexOrRelative', 'value': 'fh_is_index'}, {'code': 'FHconsentDate', 'value': None}, {'code': 'DateOfAssessment', 'value': '2018-07-02'}, {'code': 'fhAgeAtConsent', 'value': 'NaN'}, {'code': 'fhAgeAtAssessment', 'value': '0'}], 'code': 'fhDateSection', 'allow_multiple': False}, {'cdes': [{'code': 'CDEfhDutchLipidClinicNetwork', 'value': ''}, {'code': 'CDE00024', 'value': ''}], 'code': 'SEC0007', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00003', 'value': 'fh2_n'}, {'code': 'FHFamilyHistoryChild', 'value': 'fh_n'}, {'code': 'CDE00004', 'value': 'fh2_n'}, {'code': 'FHFamHistTendonXanthoma', 'value': 'fh2_n'}, {'code': 'FHFamHistArcusCornealis', 'value': 'fh2_n'}], 'code': 'SEC0002', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00011', 'value': 'fhpremcvd_no'}, {'code': 'FHMyocardialInfarction', 'value': ''}, {'code': 'FHAgeAtMI', 'value': None}, {'code': 'FHCoronaryRevasc', 'value': ''}, {'code': 'FHAgeAtCV', 'value': None}, {'code': 'FHPersHistCerebralVD', 'value': 'fh2_n'}, {'code': 'FHAorticValveDisease', 'value': ''}, {'code': 'FHSupravalvularDisease', 'value': ''}, {'code': 'FHPremNonCoronary', 'value': ''}], 'code': 'SEC0004', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00001', 'value': 'n_'}, {'code': 'CDE00002', 'value': 'n_'}, {'code': 'FHXanthelasma', 'value': ''}], 'code': 'SEC0001', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00013', 'value': None}, {'code': 'CDE00019', 'value': None}, {'code': 'PlasmaLipidTreatment', 'value': ''}, {'code': 'LDLCholesterolAdjTreatment', 'value': 'NaN'}], 'code': 'FHLDLforFHScore', 'allow_multiple': False}, {'cdes': [[{'code': 'FHLipidProfileUntreatedDate', 'value': '2018-07-02'}, {'code': 'CDE00012', 'value': 2.0}, {'code': 'FHLLDLconc', 'value': 2.0}, {'code': 'CDE00014', 'value': 2.0}, {'code': 'CDE00015', 'value': 2.0}, {'code': 'FHApoB', 'value': 2.0}, {'code': 'CDE00016', 'value': 2.0}, {'code': 'FHAST', 'value': 2}, {'code': 'FHALT', 'value': 2}, {'code': 'FHCK', 'value': 2}, {'code': 'FHCreatinine', 'value': 2}, {'code': 'FHCRP', 'value': 2.0}, {
            'code': 'PlasmaLipidTreatmentNone', 'value': 'Fluvastatin40'}, {'code': 'CDEfhOtherIntolerantDrug', 'value': ''}, {'code': 'FHCompliance', 'value': ''}], [{'code': 'FHLipidProfileUntreatedDate', 'value': '2018-07-02'}, {'code': 'CDE00012', 'value': 2.5}, {'code': 'FHLLDLconc', 'value': 2.5}, {'code': 'CDE00014', 'value': 2.5}, {'code': 'CDE00015', 'value': 2.5}, {'code': 'FHApoB', 'value': 2.5}, {'code': 'CDE00016', 'value': 2.5}, {'code': 'FHAST', 'value': 2}, {'code': 'FHALT', 'value': 2}, {'code': 'FHCK', 'value': 2}, {'code': 'FHCreatinine', 'value': 2}, {'code': 'FHCRP', 'value': 2.0}, {'code': 'PlasmaLipidTreatmentNone', 'value': 'Fluvastatin/Ezetimibe20'}, {'code': 'CDEfhOtherIntolerantDrug', 'value': ''}, {'code': 'FHCompliance', 'value': ''}]], 'code': 'SEC0005', 'allow_multiple': True}, {'cdes': [{'code': 'CDE00005', 'value': ''}, {'code': 'FHPackYears', 'value': None}, {'code': 'FHAlcohol', 'value': ''}, {'code': 'FHHypertriglycerd', 'value': ''}, {'code': 'CDE00006', 'value': ''}, {'code': 'CDE00008', 'value': None}, {'code': 'CDE00009', 'value': None}, {'code': 'FHHeartRate', 'value': None}, {'code': 'CDE00007', 'value': ''}, {'code': 'CDE00010', 'value': None}, {'code': 'HbA1c', 'value': None}, {'code': 'ChronicKidneyDisease', 'value': ''}, {'code': 'FHeGFR', 'value': ''}, {'code': 'FHHypothyroidism', 'value': ''}, {'code': 'FHTSH', 'value': None}, {'code': 'FHHepaticSteatosis', 'value': ''}, {'code': 'FHObesity', 'value': ''}, {'code': 'CDEHeight', 'value': None}, {'code': 'CDEWeight', 'value': None}, {'code': 'CDEBMI', 'value': 'NaN'}, {'code': 'FHWaistCirc', 'value': None}, {'code': 'FHCVDOther', 'value': 'test2 ddddddddd'}], 'code': 'SEC0003', 'allow_multiple': False}, {'cdes': [[{'code': 'FHClinicalTrialName', 'value': ''}, {'code': 'FHTrialLength', 'value': None}, {'code': 'FHTrialSTartDate', 'value': None}, {'code': 'FHTrialStatus', 'value': ''}]], 'code': 'FHClinicalTrials', 'allow_multiple': True}]}], 'django_id': 3, 'timestamp': '2018-07-19T15:14:04.887064', 'context_id': 3, 'django_model': 'Patient', 'ClinicalData_timestamp': '2018-07-19T15:14:04.887064'}

    def test_migrate_cdes_clinicaldata(self):
        out_data = transform_cd_dict(["CDE00016", "FHCRP"], "SEC0005", "SEC0003", self.input_data)
        cd_form = get_cd_form(out_data)
        s_section = get_section("SEC0005", cd_form)
        t_section = get_section("SEC0003", cd_form)

        def check_cde_in_section(cde_code, section_dict):
            for item in section_dict['cdes']:
                # Check if section is multiple or not
                if isinstance(item, list):
                    cdes_list = item
                    for cde_dict_item in cdes_list:
                        if cde_dict_item['code'] == cde_code:
                            return True
                else:
                    cde_dict_item = item
                    if cde_dict_item['code'] == cde_code:
                        return True

        assert not check_cde_in_section("CDE00016", s_section), "CDE00016 is still in source section"
        assert check_cde_in_section("CDE00016", t_section), "CDE00016 is not in target section found"

        assert not check_cde_in_section("FHCRP", s_section), "FHCRP is still in source section"
        assert check_cde_in_section("FHCRP", t_section), "FHCRP is not in target section found"

        assert check_cde_in_section("FHCompliance", s_section), "FHCompliance has been moved."


def mock_messages():
    """
    This switches off messaging, which requires request middleware
    which doesn't exist in RequestFactory requests.
    """
    def mock_add_message(request, level, msg, *args, **kwargs):
        logger.info("Django %s Message: %s" % (level, msg))

    def mock_error(request, msg, *args, **kwargs):
        logger.info("Django Error Message: %s" % msg)
    messages.add_message = mock_add_message
    messages.error = mock_error


mock_messages()


class SectionFiller(object):

    def __init__(self, form_filler, section):
        self.__dict__["form_filler"] = form_filler
        self.__dict__["section"] = section

    def __setattr__(self, key, value):
        if key in self.section.get_elements():
            self.form_filler.add_data(self.section, key, value)


class FormFiller(object):

    def __init__(self, registry_form):
        self.form = registry_form
        self.section_codes = self.form.get_sections()
        self.data = {}

    def add_data(self, section, cde_code, value):
        key = settings.FORM_SECTION_DELIMITER.join([self.form.name, section.code, cde_code])
        self.data.update({key: value})

    def __getattr__(self, item):
        if item in self.section_codes:
            section = Section.objects.get(code=item)
            section_filler = SectionFiller(self, section)
            return section_filler


class RDRFTestCase(TestCase):
    databases = {'default', 'clinical'}
    fixtures = ['testing_auth', 'testing_users', 'testing_rdrf']


class TestFormPermissions(RDRFTestCase):

    def test_form_without_groups_restriction_is_open(self):
        from registry.groups.models import CustomUser
        fh = Registry.objects.get(code='fh')

        for form in fh.forms:
            assert form.open, "%s has no group restriction so should be open but is not" % form.name
            for user in CustomUser.objects.all():
                user.registry.add(fh)
                user.save()
                assert user.can_view(form)

    def test_user_in_wrong_group_cant_view_form(self):
        from registry.groups.models import CustomUser
        from django.contrib.auth.models import Group
        fh = Registry.objects.get(code='fh')
        genetic_user = CustomUser.objects.get(username='genetic')
        genetic_group, created = Group.objects.get_or_create(name="Genetic Staff")
        if created:
            genetic_group.save()

        clinical_group, created = Group.objects.get_or_create(name="Clinical Staff")
        if created:
            clinical_group.save()
        f = fh.forms[0]
        f.groups_allowed.set([clinical_group])
        f.save()
        assert not genetic_user.can_view(f), "A form set to be viewed "


class ExporterTestCase(RDRFTestCase):

    def _get_cde_codes_from_registry_export_data(self, data):
        cde_codes = set([])
        for form_map in data["forms"]:
            for section_map in form_map["sections"]:
                for cde_code in section_map["elements"]:
                    cde_codes.add(cde_code)
        return cde_codes

    def _report_cde_diff(self, cde_set, cdeform_set):
        in_cdes_not_forms = cde_set - cdeform_set
        in_forms_not_cdes = cdeform_set - cde_set
        a = "cdes in cde list but not in registry: %s" % in_cdes_not_forms
        b = "cdes in forms but not in cde list: %s" % in_forms_not_cdes
        return "%s\n%s" % (a, b)

    def test_export_registry(self):

        def test_key(key, data):
            assert key in data, "%s not in yaml export" % key

        def test_keys(keys, data):
            for key in keys:
                test_key(key, data)

        self.registry = Registry.objects.get(code='fh')
        self.exporter = Exporter(self.registry)
        yaml_data, errors = self.exporter.export_yaml()
        assert isinstance(errors, list), "Expected errors list in exporter export_yaml"
        assert len(errors) == 0, "Expected zero errors instead got:%s" % errors
        assert isinstance(yaml_data, str), "Expected yaml_data is  string:%s" % type(yaml_data)
        with open("/tmp/test.yaml", "w") as f:
            f.write(yaml_data)

        with open("/tmp/test.yaml") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)

        test_key('EXPORT_TYPE', data)
        test_key('RDRF_VERSION', data)
        assert data["EXPORT_TYPE"] == ExportType.REGISTRY_PLUS_CDES
        assert 'cdes' in data, "Registry export should have cdes key"
        assert 'pvgs' in data, "Registry export should have groups key"
        assert data['code'] == 'fh', "Reg code fh not in export"
        test_key('forms', data)
        for form_map in data['forms']:
            test_keys(['is_questionnaire', 'name', 'sections'], form_map)
            for section_map in form_map['sections']:
                test_keys(['code',
                           'display_name',
                           'elements',
                           'allow_multiple',
                           'extra'],
                          section_map)

        dummy_cde = CommonDataElement.objects.create()
        cde_fields = list(model_to_dict(dummy_cde).keys())
        for cde_map in data['cdes']:
            assert isinstance(
                cde_map, dict), "Expected cdes list should contain cde dictionaries: actual %s" % cde_map
            for cde_field in cde_fields:
                assert cde_field in cde_map, "Expected export of cde to contain field %s - it doesn't" % cde_field

        for pvg_map in data["pvgs"]:
            assert "code" in pvg_map, "Expected group has code key: %s" % pvg_map
            assert "values" in pvg_map, "Expected group has values key: %s" % pvg_map
            for value_map in pvg_map["values"]:
                assert "code" in value_map, "Expected value map to have code key %s" % value_map
                assert "value" in value_map, "Expected value map to have value key %s" % value_map
                assert "desc" in value_map, "Expected value map to have desc key %s" % value_map

        # consistency check
        set_of_cde_codes_in_cdes = set([cde_map["code"] for cde_map in data["cdes"]])
        set__of_cdes_in_forms = self._get_cde_codes_from_registry_export_data(data)
        generic_cdes = set(self.registry.generic_cdes)

        assert set__of_cdes_in_forms == (
            set_of_cde_codes_in_cdes - generic_cdes), "Consistency check failed:\n%s" % self._report_cde_diff(set_of_cde_codes_in_cdes, set__of_cdes_in_forms)

        # consistency of values in groups - whats exported is whats there

        for pvg_map in data["pvgs"]:
            values_in_export = set([])
            for value_map in pvg_map["values"]:
                values_in_export.add(value_map["code"])

            values_in_db = self._get_values_for_group(pvg_map["code"])
            msg = "%s:export %s\ndb: %s" % (pvg_map["code"], values_in_export, values_in_db)
            assert values_in_export == values_in_db, "Values in export for group %s don't match what's in db: %s" % msg

    def _get_values_for_group(self, group_code):
        values = set([])
        group = CDEPermittedValueGroup.objects.get(code=group_code)
        for value in CDEPermittedValue.objects.filter(pv_group=group):
            values.add(value.code)
        return values


class ImporterTestCase(TestCase):

    def _get_yaml_file(self):
        this_dir = os.path.dirname(__file__)
        logger.info("tests.py  dir = %s" % this_dir)
        test_yaml = os.path.abspath(os.path.join(this_dir, "..", "..", "fixtures", "exported_fh_registry.yaml"))
        logger.info("full path to test yaml = %s" % test_yaml)
        return test_yaml

    def test_importer(self):
        importer = Importer()
        yaml_file = self._get_yaml_file()
        logger.info("test_importer yaml file = %s" % yaml_file)

        importer.load_yaml(yaml_file)
        importer.create_registry()
        assert importer.state == ImportState.SOUND


class FormTestCase(RDRFTestCase):

    def setUp(self):
        super(FormTestCase, self).setUp()
        self.registry = Registry.objects.get(code='fh')
        self.wg, created = WorkingGroup.objects.get_or_create(name="testgroup",
                                                              registry=self.registry)

        if created:
            self.wg.save()

        self.user = CustomUser.objects.get(username="curator")
        self.user.registry.set([self.registry])
        self.user.working_groups.add(self.wg)

        self.user.save()

        self.state, created = State.objects.get_or_create(
            short_name="WA", name="Western Australia")

        self.state.save()
        self.create_sections()
        self.working_group, created = WorkingGroup.objects.get_or_create(name="WA")
        self.working_group.save()
        self.create_forms()

        self.patient = self.create_patient()
        self.patient.working_groups.add(self.wg)
        self.patient.save()

        self.address_type, created = AddressType.objects.get_or_create(pk=1)

        self.patient_address, created = PatientAddress.objects.get_or_create(
            address='1 Line St', address_type=self.address_type, suburb='Neverland', state=self.state.short_name, postcode='1111', patient=self.patient)
        self.patient_address.save()

        self.request_factory = RequestFactory()

    def create_patient(self):
        from rdrf.db.contexts_api import RDRFContextManager

        p = Patient()
        p.consent = True
        p.name = "Harry"
        p.date_of_birth = datetime(1978, 6, 15)
        p.working_group = self.working_group
        p.save()
        p.rdrf_registry.set([self.registry])

        context_manager = RDRFContextManager(self.registry)
        self.default_context = context_manager.get_or_create_default_context(
            p, new_patient=True)

        return p

    def create_section(self, code, display_name, elements, allow_multiple=False, extra=1):
        section, created = Section.objects.get_or_create(code=code)
        section.display_name = display_name
        section.elements = ",".join(elements)
        section.allow_multiple = allow_multiple
        section.extra = extra
        section.save()
        return section

    def create_form(self, name, sections, is_questionnnaire=False):
        sections = ",".join([section.code for section in sections])
        form, created = RegistryForm.objects.get_or_create(name=name, registry=self.registry,
                                                           defaults={'sections': sections})
        if not created:
            form.sections = sections
        form.name = name
        form.registry = self.registry
        form.is_questionnaire = is_questionnnaire
        form.save()
        # self.working_group
        return form

    def create_forms(self):
        self.simple_form = self.create_form("simple", [self.sectionA, self.sectionB])
        self.multi_form = self.create_form("multi", [self.sectionC])
        # TODO file forms, questionnaire forms

    def _create_request(self, form_obj, form_data):
        # return a dictionary representing what is sent from filled in form
        # form data looks like:
        # { "
        url = "/%s/forms/%s/%s" % (form_obj.registry.code, form_obj.pk, self.patient.pk)

        request = self.request_factory.post(url, form_data)
        request.user = get_user_model().objects.get(username="curator")
        request.csp_nonce = None
        return request

    def create_sections(self):
        # "simple" sections ( no files or multi-allowed sections
        self.sectionA = self.create_section(
            "sectionA", "Simple Section A", ["CDEName", "CDEAge"])
        self.sectionB = self.create_section(
            "sectionB", "Simple Section B", ["CDEHeight", "CDEWeight", "CDEBMI"])
        # A multi allowed section with no file cdes
        self.sectionC = self.create_section(
            "sectionC", "MultiSection No Files Section C", ["CDEName", "CDEAge"], True)
        # A multi allowed section with a file CDE
        # self.sectionD = self.create_section("sectionD", "MultiSection With Files D", ["CDEName", ""])

    def _create_form_key(self, form, section, cde_code):
        return settings.FORM_SECTION_DELIMITER.join([form.name, section.code, cde_code])

    def test_patient_archiving(self):
        from registry.patients.models import Patient

        patient_model = self.create_patient()
        self.assertTrue(patient_model.active)

        my_id = patient_model.pk

        patient_model.delete()
        self.assertEqual(patient_model.active, False)

        # should not be findable
        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.get(id=my_id)

        # test really_all object manager method on Patients
        self.assertEqual(my_id, Patient.objects.really_all().get(id=my_id).id)

        # test hard delete

        patient_model._hard_delete()

        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.get(id=my_id)

        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.really_all().get(id=my_id)

        # test can archive prop on CustomUser
        # by default genetic user can't delete as they don't have patient delete permission

        genetic_user = CustomUser.objects.get(username='genetic')
        self.assertFalse(genetic_user.can_archive)

        # admin can by default
        admin_user = CustomUser.objects.get(username='admin')
        self.assertTrue(admin_user.can_archive)

        # clinical can't either
        clinical_user = CustomUser.objects.get(username='clinical')
        self.assertFalse(clinical_user.can_archive)

    def test_simple_form(self):

        def form_value(form_name, section_code, cde_code, mongo_record):
            for form in mongo_record["forms"]:
                if form["name"] == form_name:
                    for section in form["sections"]:
                        if section["code"] == section_code:
                            for cde in section["cdes"]:
                                if cde["code"] == cde_code:
                                    return cde["value"]

        ff = FormFiller(self.simple_form)
        ff.sectionA.CDEName = "Fred"
        ff.sectionA.CDEAge = 20
        ff.sectionB.CDEHeight = 1.73
        ff.sectionB.CDEWeight = 88.23

        form_data = ff.data
        print(str(form_data))
        request = self._create_request(self.simple_form, form_data)
        view = FormView()
        view.request = request
        view.post(
            request,
            self.registry.code,
            self.simple_form.pk,
            self.patient.pk,
            self.default_context.pk)

        collection = ClinicalData.objects.collection(self.registry.code, "cdes")
        context_id = self.patient.default_context(self.registry).id
        mongo_record = collection.find(self.patient, context_id).data().first()

        print("*** MONGO RECORD = %s ***" % mongo_record)

        assert "forms" in mongo_record, "Mongo record should have a forms key"
        assert isinstance(mongo_record["forms"], list)
        assert len(mongo_record["forms"]) == 1, "Expected one form"

        the_form = mongo_record['forms'][0]
        assert isinstance(the_form, dict), "form data should be a dictionary"
        assert "sections" in the_form, "A form should have a sections key"
        assert isinstance(the_form["sections"], list), "Sections should be in a list"
        # we've only written data for 2 sections
        assert len(the_form["sections"]) == 2, "expected 2 sections got %s" % len(
            the_form["sections"])

        for section_dict in the_form["sections"]:
            assert isinstance(section_dict, dict), "sections should be dictioanaries"
            assert "cdes" in section_dict, "sections should have a cdes key"
            assert isinstance(section_dict["cdes"], list), "sections cdes key should be a list"
            for cde in section_dict["cdes"]:
                assert isinstance(cde, dict), "cde should be a dict"
                assert "code" in cde, "cde dictionary should have a code key"
                assert "value" in cde, "cde dictionary should have a value key"

        assert form_value(
            self.simple_form.name,
            self.sectionA.code,
            "CDEName",
            mongo_record) == "Fred"
        assert form_value(
            self.simple_form.name,
            self.sectionA.code,
            "CDEAge",
            mongo_record) == 20
        assert form_value(
            self.simple_form.name,
            self.sectionB.code,
            "CDEHeight",
            mongo_record) == 1.73
        assert form_value(
            self.simple_form.name,
            self.sectionB.code,
            "CDEWeight",
            mongo_record) == 88.23


class LongitudinalTestCase(FormTestCase):

    def test_simple_form(self):
        super(LongitudinalTestCase, self).test_simple_form()
        # should have one snapshot
        qs = ClinicalData.objects.collection(self.registry.code, "history")
        snapshots = qs.find(self.patient, record_type="snapshot").data()
        self.assertGreater(len(snapshots), 0,
                           "History should be filled in on save")
        for snapshot in snapshots:
            self.assertIn("record", snapshot,
                          "Each snapshot should have a record field")
            self.assertIn("timestamp", snapshot,
                          "Each snapshot should have a timestamp field")
            self.assertIn("forms", snapshot["record"],
                          "Each  snapshot should record dict contain a forms field")


class DeCamelcaseTestCase(TestCase):

    _EXPECTED_VALUE = "Your Condition"

    def test_decamelcase_first_lower(self):
        test_value = "yourCondition"
        self.assertEqual(de_camelcase(test_value), self._EXPECTED_VALUE)

    def test_decamelcase_first_upper(self):
        test_value = "YourCondition"
        self.assertEqual(de_camelcase(test_value), self._EXPECTED_VALUE)


class DateFunctionsTestCase(TestCase):

    def test_number_of_days_function(self):
        from rdrf.forms.fields.calculated_functions import number_of_days
        r1 = number_of_days("2020-03-23", "2020-03-25")
        r2 = number_of_days("", "2020-03-25")
        r3 = number_of_days("hello", "2020-03-25")
        self.assertEqual(r1, 2)
        self.assertEqual(r2, None)
        self.assertEqual(r3, None)


class FakeClinicalData(object):
    def __init__(self, pk, data):
        self.pk = pk
        self.data = data

    def save(self):
        print("Fake ClinicalData save called")


class TimeStripperTestCase(TestCase):
    def setUp(self):
        super(TimeStripperTestCase, self).setUp()

        self.data_with_date_cdes = {'django_model': 'Patient',
                                    'ClinicalData_timestamp': '2017-02-14T10:23:10.601182',
                                    'context_id': 4,
                                    'django_id': 3,
                                    'forms': [{'name': 'ClinicalData',
                                               'sections': [{'code': 'fhDateSection', 'allow_multiple': False,
                                                             'cdes': [{'value': 'fh_is_index', 'code': 'CDEIndexOrRelative'},
                                                                      {'value': '1972-06-15T00:00:00.00',
                                                                          'code': 'DateOfAssessment'},
                                                                      {'value': '2015-01-05T10:23:10.601182', 'code': 'FHconsentDate'}]},
                                                            {'code': 'SEC0007', 'allow_multiple': False,
                                                             'cdes': [{'value': '', 'code': 'CDE00024'},
                                                                      {'value': '', 'code': 'CDEfhDutchLipidClinicNetwork'}]}]}]}

        self.copy_of_initial_data = deepcopy(self.data_with_date_cdes)

        self.data_without_date_cdes = {'django_model': 'Patient',
                                       'ClinicalData_timestamp': '2017-02-14T10:23:10.601182',
                                       'context_id': 40,
                                       'django_id': 300,
                                       'forms': [{'name': 'ClinicalData',
                                                  'sections': [{'code': 'fhDateSection', 'allow_multiple': False,
                                                                 'cdes': [{'value': 'fh_is_index', 'code': 'CDEIndexOrRelative'}]},
                                                               {'code': 'SEC0007', 'allow_multiple': False,
                                                                'cdes': [{'value': '', 'code': 'CDE00024'},
                                                                         {'value': '', 'code': 'CDEfhDutchLipidClinicNetwork'}]}]}]}

        self.m1 = FakeClinicalData(1, self.data_with_date_cdes)
        self.m2 = FakeClinicalData(2, self.data_without_date_cdes)

        self.ts = TimeStripper([self.m1, self.m2])
        self.ts.test_mode = True
        self.ts.date_cde_codes = ['DateOfAssessment', 'FHconsentDate']

    def test_timestripper(self):
        expected_date_of_assessment = "1972-06-15"
        expected_fh_consent_date = "2015-01-05"
        expected = [expected_date_of_assessment, expected_fh_consent_date]
        clinicaldata_timestamp_before = self.data_with_date_cdes["ClinicalData_timestamp"]
        fh_index_before = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][0]["value"]

        self.ts.forward()
        clinicaldata_timestamp_after = self.data_with_date_cdes["ClinicalData_timestamp"]
        fh_index_after = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][0]["value"]

        self.assertTrue(self.ts.converted_date_cdes == expected,
                        "Expected %s Actual %s" % (expected, self.ts.converted_date_cdes))

        value1 = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][1]["value"]
        self.assertTrue(value1 == expected_date_of_assessment,
                        "DateOfAssessment value not modified by TimeStripper")
        value2 = self.data_with_date_cdes["forms"][0]["sections"][0]["cdes"][2]["value"]
        self.assertTrue(value2 == expected_fh_consent_date,
                        "FHConsentdate value not modified by TimeStripper")

        self.assertTrue(clinicaldata_timestamp_after == clinicaldata_timestamp_before,
                        "Timestamps which are not date cdes should not be affected by TimeStripper")
        self.assertTrue(fh_index_before == fh_index_after,
                        "Non date cdes should not be affected by TimeStripper")

    def test_update_of_multisections(self):
        # multisection with 2 items , one cde Surgery , another SurgeryDate
        cde_dict1 = {"code": "Surgery", "value": "Appendix Removed"}
        cde_dict2 = {"code": "SurgeryDate", "value": "2017-02-14T00:00:00"}
        cde_dict3 = {"code": "Surgery", "value": "Stomach Ulcer"}
        cde_dict4 = {"code": "SurgeryDate", "value": "2018-03-26T00:00:00"}
        # assume last item ok
        cde_dict5 = {"code": "Surgery", "value": "Heart Surgery"}
        cde_dict6 = {"code": "SurgeryDate", "value": "2011-11-05"}

        item1 = [cde_dict1, cde_dict2]
        item2 = [cde_dict3, cde_dict4]
        item3 = [cde_dict5, cde_dict6]

        multisection = {"allow_multiple": True,
                        "cdes": [item1, item2, item3]}

        data_with_multisections = {"forms": [{"form": "testing",
                                              "sections": [multisection]}]}

        m = FakeClinicalData(23, data_with_multisections)

        ts = TimeStripper([m])
        ts.test_mode = True
        ts.date_cde_codes = ['SurgeryDate']

        ts.forward()

        self.assertTrue(ts.converted_date_cdes == ["2017-02-14", "2018-03-26"],
                        "Multisection timestrip failed: actual = %s" % ts.converted_date_cdes)

        expected_value1 = "2017-02-14"
        actual_value1 = m.data["forms"][0]["sections"][0]["cdes"][0][1]["value"]
        self.assertEqual(
            expected_value1,
            actual_value1,
            "Update of multisection failed for first item: actual = %s" %
            actual_value1)

        expected_value2 = "2018-03-26"
        actual_value2 = m.data["forms"][0]["sections"][0]["cdes"][1][1]["value"]
        self.assertEqual(
            expected_value2,
            actual_value2,
            "Update of multisection failed for second item: actual = %s" %
            actual_value2)

        expected_value3 = "2011-11-05"  # n shouldn't have changed
        actual_value3 = m.data["forms"][0]["sections"][0]["cdes"][2][1]["value"]
        self.assertEqual(
            expected_value3,
            actual_value3,
            "Update of multisection failed for third item: actual = %s" %
            actual_value3)

    def test_history_munging(self):
        from rdrf.helpers.utils import HistoryTimeStripper
        history_modjgo_data = {"django_id": 1,
                               "record": {
                                   "django_id": 1,
                                   "timestamp": "2017-02-13T12:28:49.355839",
                                   "forms": [
                                       {
                                           "sections": [
                                                {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "fh_is_index",
                                                            "code": "CDEIndexOrRelative"
                                                        },
                                                        {
                                                            "value": "2017-02-15",
                                                            "code": "DateOfAssessment"
                                                        },
                                                        {
                                                            "value": "2017-02-14T00:00:00.000",
                                                            "code": "FHconsentDate"
                                                        }
                                                    ],
                                                    "code": "fhDateSection"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "",
                                                            "code": "CDE00024"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDEfhDutchLipidClinicNetwork"
                                                        }
                                                    ],
                                                    "code": "SEC0007"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "fh2_y",
                                                            "code": "CDE00004"
                                                        },
                                                        {
                                                            "value": "fh2_n",
                                                            "code": "FHFamHistTendonXanthoma"
                                                        },
                                                        {
                                                            "value": "fh2_n",
                                                            "code": "FHFamHistArcusCornealis"
                                                        },
                                                        {
                                                            "value": "fh2_y",
                                                            "code": "CDE00003"
                                                        },
                                                        {
                                                            "value": "y_childunder18",
                                                            "code": "FHFamilyHistoryChild"
                                                        }
                                                    ],
                                                    "code": "SEC0002"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "",
                                                            "code": "FHSupravalvularDisease"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHAgeAtMI"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHAgeAtCV"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHPremNonCoronary"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHAorticValveDisease"
                                                        },
                                                        {
                                                            "value": "fh2_n",
                                                            "code": "FHPersHistCerebralVD"
                                                        },
                                                        {
                                                            "value": "fhpremcvd_unknown",
                                                            "code": "CDE00011"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHCoronaryRevasc"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHMyocardialInfarction"
                                                        }
                                                    ],
                                                    "code": "SEC0004"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "u_",
                                                            "code": "CDE00002"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHXanthelasma"
                                                        },
                                                        {
                                                            "value": "y",
                                                            "code": "CDE00001"
                                                        }
                                                    ],
                                                    "code": "SEC0001"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "",
                                                            "code": "PlasmaLipidTreatment"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00019"
                                                        },
                                                        {
                                                            "value": "NaN",
                                                            "code": "LDLCholesterolAdjTreatment"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00013"
                                                        }
                                                    ],
                                                    "code": "FHLDLforFHScore"
                                                },
                                               {
                                                    "allow_multiple": True,
                                                    "cdes": [
                                                        [
                                                            {
                                                                "value": None,
                                                                "code": "CDE00014"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHLipidProfileUntreatedDate"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHAlbum"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "CDE00012"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHCK"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHA1"
                                                            },
                                                            {
                                                                "value": "",
                                                                "code": "PlasmaLipidTreatmentNone"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHAST"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "CDE00015"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHApoB"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHALT"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHLLDLconc"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHCreatinine"
                                                            },
                                                            {
                                                                "value": "",
                                                                "code": "FHCompliance"
                                                            },
                                                            {
                                                                "value": "",
                                                                "code": "CDEfhOtherIntolerantDrug"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "CDE00016"
                                                            },
                                                            {
                                                                "value": None,
                                                                "code": "FHCRP"
                                                            }
                                                        ]
                                                    ],
                                                    "code": "SEC0005"
                                                },
                                               {
                                                    "allow_multiple": False,
                                                    "cdes": [
                                                        {
                                                            "value": "NaN",
                                                            "code": "CDEBMI"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHHypertriglycerd"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "HbA1c"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHHypothyroidism"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00009"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHHeartRate"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00010"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHWaistCirc"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHObesity"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDE00008"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDEWeight"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHPackYears"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "CDEHeight"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDE00007"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHAlcohol"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDE00005"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "CDE00006"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHCVDOther"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHeGFR"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "ChronicKidneyDisease"
                                                        },
                                                        {
                                                            "value": "",
                                                            "code": "FHHepaticSteatosis"
                                                        },
                                                        {
                                                            "value": None,
                                                            "code": "FHTSH"
                                                        }
                                                    ],
                                                    "code": "SEC0003"
                                                },
                                               {
                                                    "allow_multiple": True,
                                                    "cdes": [
                                                        [{
                                                            "value": "",
                                                            "code": "FHTrialStatus"
                                                        },
                                                            {
                                                            "value": None,
                                                            "code": "FHTrialSTartDate"
                                                        },
                                                            {
                                                            "value": "",
                                                            "code": "FHClinicalTrialName"
                                                        },
                                                            {
                                                            "value": None,
                                                            "code": "FHTrialLength"
                                                        }
                                                        ]
                                                    ],
                                                    "code": "FHClinicalTrials"
                                                }
                                           ],
                                           "name": "ClinicalData"
                                       }
                                   ],
                                   "context_id": 1,
                                   "ClinicalData_timestamp": "2017-02-13T12:28:49.355839",
                                   "django_model": "Patient"
                               },
                               "record_type": "snapshot",
                               "timestamp": "2017-02-13 12:28:49.665333",
                               "registry_code": "fh",
                               "context_id": 1,
                               "django_model": "Patient"
                               }

        expected_dates = ['2017-02-14']
        history_record = FakeClinicalData(73, history_modjgo_data)
        ts = HistoryTimeStripper([history_record])
        ts.test_mode = True
        ts.date_cde_codes = ['FHconsentDate']
        ts.forward()

        self.assertTrue(ts.converted_date_cdes == expected_dates,
                        "Expected: %s, Actual: %s" % (expected_dates,
                                                      ts.converted_date_cdes))


class MinTypeTest(TestCase):
    def test_string(self):
        from rdrf.helpers.utils import MinType
        bottom = MinType()
        lst = ["a", "B", bottom]
        g = sorted(lst)
        self.assertTrue(g[0] is bottom)

    def test_ints(self):
        from rdrf.helpers.utils import MinType
        bottom = MinType()
        lst = [10, 1, -7, bottom]
        g = sorted(lst)
        self.assertTrue(g[0] is bottom)


class StructureChecker(TestCase):
    databases = {'default', 'clinical'}

    def _run_command(self, *args, **kwargs):
        from django.core import management
        import io
        out_stream = io.StringIO("")
        # test_mode means the command does not issue sys.exit(1)
        management.call_command('check_structure', *args, stdout=out_stream, **kwargs)
        return out_stream.getvalue()

    def clear_modjgo_objects(self):
        ClinicalData.objects.all().delete()

    def make_modjgo(self, collection, data):
        m = ClinicalData()
        m.registry_code = "foobar"
        m.collection = collection
        m.data = data
        m.save()
        return m

    def test_cdes(self):
        foobar = Registry()
        foobar.code = "foobar"
        foobar.save()

        # Some examples of possible mangled records
        # [ (desc,collectionname,example), ...]
        # we expect non-blank output/failure for each example
        bad = [("bad id", "cdes", {"django_id": "fred",
                                   "django_model": "Patient",
                                   "timestamp": "2018-03-10T04:03:21",
                                   "forms": []}),

               ("missing id", "cdes", {"django_model": "Patient",
                                       "timestamp": "2018-03-10T04:03:21",
                                       "forms": []}),

               ("bad model", "cdes", {"django_id": 100,
                                      "django_model": "Tomato",
                                      "timestamp": "2018-03-10T04:03:21",
                                      "forms": []}),


               ("missing_model", "cdes", {"django_id": 23,
                                          "timestamp": "2018-03-10T04:03:21",
                                          "forms": []}),
               ("bad_forms", "cdes", {"django_id": 23,
                                      "django_model": "Patient",
                                      "timestamp": "2018-03-10T04:03:21",
                                      "forms": 999}),
               ("bad_old_format", "cdes", {"django_id": 23,
                                           "django_model": "Patient",
                                           "timestamp": "2018-03-10T04:03:21",
                                           "formname____sectioncode____cdecode": 99,
                                           "forms": []})
               ]

        for bad_example, collection, data in bad:
            self.clear_modjgo_objects()
            m = self.make_modjgo(collection, data)
            with self.assertRaises(SystemExit) as cm:
                output = self._run_command(registry_code="foobar", collection=collection)
                print("output = [%s]" % output)
                assert output != "", "check_structure management command failed: Expected schema error for %s" % bad_example
                parts = output.split(";")
                bad_pk = int(parts[0])
                self.assertEqual(m.pk, bad_pk)
            self.assertEqual(cm.exception.code, 1)

        # finally, a good record
        good = {"django_id": 23,
                "django_model": "Patient",
                "timestamp": "2018-03-10T04:03:21",
                "forms": []}

        self.clear_modjgo_objects()
        m = self.make_modjgo("cdes", good)
        output = self._run_command(registry_code="foobar", collection="cdes")
        print("output = [%s]" % output)
        assert output == "", "check_structure test of good data should output nothing"

    def test_history(self):
        foobar = Registry()
        foobar.code = "foobar"
        foobar.save()
        bad_history = {"id": 6,
                       "registry_code": "foobar",
                       "collection": "history",
                       "data": {"record": {"django_id": 1,
                                           "timestamp": "2017-07-10T14:45:36.760123",
                                           "context_id": 1,
                                           "django_model": "Patient",
                                           "oldstyleform____section____cde": 23,
                                           "Diagnosis_timestamp": "2017-07-10T14:45:36.760123"}
                                },
                       "django_id": 1,
                       "timestamp": "2017-07-10 14:45:37.012962",
                       "context_id": 1,
                       "record_type": "snapshot",
                       "django_model": "Patient",
                       "registry_code": "foobar"}

        self.clear_modjgo_objects()
        self.make_modjgo("history", bad_history)
        with self.assertRaises(SystemExit) as cm:
            self._run_command(registry_code="foobar", collection="history")

        self.assertEqual(cm.exception.code, 1)


class RemindersTestCase(TestCase):
    def _run_command(self, *args, **kwargs):
        import io
        out_stream = io.StringIO("")
        call_command('check_logins', *args, stdout=out_stream, **kwargs)
        return out_stream.getvalue()

    def setUp(self):
        self.registry = Registry()
        self.registry.code = "foobar"
        self.registry.save()
        self.user = None

    def _setup_user(self, username, last_login, group="patients"):
        patients_group, created = Group.objects.get_or_create(name="Patients")
        parents_group, created = Group.objects.get_or_create(name="Parents")
        curators_group, created = Group.objects.get_or_create(name="Curators")
        if created:
            patients_group.save()
        if self.user:
            self.user.delete()
            self.user = None

        self.user = CustomUser()
        self.user.username = username
        self.user.last_login = last_login
        self.user.is_active = True
        self.user.save()
        self.user.registry.set([self.registry])
        self.user.save()

        if group == "patients":
            self.user.groups.set([patients_group])
        elif group == "parents":
            self.user.groups.set([parents_group])
        elif group == "curators":
            self.user.groups.set([curators_group])

        self.user.save()

    def set_metadata(self, d):
        import json
        self.registry.metadata_json = json.dumps(d)
        self.registry.save()

    def _setup_notification(self):
        t = EmailTemplate()
        t.language = "en"
        t.description = "test reminder template"
        t.subject = "testing"
        t.body = "test"
        t.save()
        self.template = t

        en = EmailNotification()
        en.description = "reminder"
        en.registry = self.registry
        en.recipient = "{{user.email}}"
        en.save()
        en.templates = [self.template]
        en.save()
        self.email_notification = en

    def _create_dummy_history(self, date_stamp):
        enh = EmailNotificationHistory()
        enh.date_stamp = date_stamp
        enh.language = "en"
        enh.email_notification = self.email_notification
        enh.template_data = json.dumps({"user": {"id": self.user.id,
                                                 "model": "CustomUser",
                                                 "app": "groups"},
                                        "registry": {"id": self.registry.id,
                                                     "app": "rdrf",
                                                     "model": "Registry"}})

        enh.save()
        enh.date_stamp = date_stamp
        enh.save()
        print("enh.date_stamp = %s" % enh.date_stamp)

    def _clear_notifications(self):
        EmailNotificationHistory.objects.all().delete()
        EmailNotification.objects.all().delete()
        EmailTemplate.objects.all().delete()

    def test_check_logins_command(self):
        now = datetime.now()

        class Time:
            RECENTLY = now - timedelta(days=1)
            MONTH_AGO = now - timedelta(days=30)
            LONG_AGO = now - timedelta(days=3650)
            ONE_YEAR_AGO = now - timedelta(days=365)

        # dead user
        self._setup_user("testuser", Time.LONG_AGO)
        result = self._run_command(registry_code="foobar", days=365)
        lines = result.split("\n")
        assert "testuser" in lines, "Expected to see testuser in output: instead [%s]" % result

        # patient user logged in inside threshhold
        self._setup_user("testuser", Time.RECENTLY)
        result = self._run_command(registry_code="foobar", days=365)
        assert result == "", "Expected no output instead got [%s]" % result

        # patient on edge is detected
        self._setup_user("testuser", Time.ONE_YEAR_AGO)
        result = self._run_command(registry_code="foobar", days=365)
        assert result == "testuser\n", "Expected testuser instead got [%s]" % result

        # parents are detected
        parent_feature = True
        # Check parent feature is enabled.
        try:
            __import__('angelman.parent_view')
        except ImportError:
            parent_feature = False
        if parent_feature:
            self._setup_user("testuser", Time.LONG_AGO, group="parents")
            result = self._run_command(registry_code="foobar", days=365)
            assert result == "testuser\n", "Expected testuser instead got [%s]" % result

        # but not other types of users
        self._setup_user("testuser", Time.LONG_AGO, group="curators")
        result = self._run_command(registry_code="foobar", days=365)
        assert result == "", "Expected no output instead got [%s]" % result

        # mock the send-reminders action
        self._setup_user("testuser", Time.LONG_AGO)

        result = self._run_command(registry_code="foobar",
                                   days=365,
                                   action="send-reminders",
                                   test_mode=True)

        lines = result.split("\n")

        assert "dummy send reg_code=foobar description=reminder" in lines[0], "send-reminders failed?"

        # create some dummy email notification history models to simulate previous
        # reminders being sent

        self._setup_notification()
        self._create_dummy_history(Time.RECENTLY)

        result = self._run_command(registry_code="foobar",
                                   days=365,
                                   action="send-reminders",
                                   test_mode=True)

        lines = result.split("\n")

        assert "not sent" in lines, "Expected reminder NOT to be sent if one already sent"

        # 2nd one allowed
        self._clear_notifications()
        self._setup_user("testuser", Time.LONG_AGO)
        self._setup_notification()
        self._create_dummy_history(Time.MONTH_AGO)

        result = self._run_command(registry_code="foobar",
                                   days=365,
                                   action="send-reminders",
                                   test_mode=True)

        lines = result.split("\n")
        print(lines)
        assert "dummy send reg_code=foobar description=reminder" in lines[0], "send-reminders failed?"

        self._clear_notifications()
        self._setup_user("testuser", Time.LONG_AGO)
        self._setup_notification()
        self._create_dummy_history(Time.MONTH_AGO)
        self._create_dummy_history(Time.MONTH_AGO)
        result = self._run_command(registry_code="foobar",

                                   days=365,
                                   action="send-reminders",
                                   test_mode=True)

        lines = result.split("\n")
        print(lines)
        assert "not sent" in lines, "Expected reminder NOT to be sent if two or more already sent"


class ClinicalDataTestCase(RDRFTestCase):
    def create_clinicaldata(self, patient_id, registry_code):
        try:
            registry = Registry.objects.all().get(code=registry_code)
        except Registry.DoesNotExist:
            registry = None
        if registry is None:
            registry = Registry.objects.create(code=registry_code)
        data = {"timestamp": "2018-10-12T04:03:21",
                "forms": []}
        cd = ClinicalData()
        cd.data = data
        cd.collection = 'cdes'
        cd.registry_code = registry_code
        cd.django_id = patient_id
        cd.django_model = 'Patient'
        cd.save()

        return cd

    def create_new_patient(self):
        p = Patient()
        p.name = "Kathy"
        p.date_of_birth = datetime(1980, 4, 11)
        p.consent = True
        p.save()

        return p

    def test_clinicaldata_delete(self):
        patient_model = self.create_new_patient()
        patient_id = patient_model.id

        clinicaldata_model = self.create_clinicaldata(patient_id, 'dummy')

        patient_model.delete()
        self.assertEqual(patient_model.active, False)

        clinicaldata_model.refresh_from_db()
        self.assertEqual(clinicaldata_model.active, False)

    def test_delete_clinicaldata_sanity_check(self):
        patient_model = self.create_new_patient()
        patient_id = patient_model.id
        clinicaldata_model1 = self.create_clinicaldata(patient_id, 'dummy')

        # create another clinicaldata model with different patient id
        clinicaldata_model2 = self.create_clinicaldata(patient_id + 1, 'dummy')

        patient_model.delete()
        self.assertEqual(patient_model.active, False)

        clinicaldata_model1.refresh_from_db()
        self.assertEqual(clinicaldata_model1.active, False)

        clinicaldata_model2.refresh_from_db()
        self.assertEqual(clinicaldata_model2.active, True)

    def test_hard_delete_clinicaldata(self):
        patient_model = self.create_new_patient()
        patient_id = patient_model.id
        self.create_clinicaldata(patient_id, 'dummy')
        patient_model._hard_delete()

        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.get(id=patient_id)

        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.really_all().get(id=patient_id)

        with self.assertRaises(ClinicalData.DoesNotExist):
            ClinicalData.objects.get(django_id=patient_id, django_model='Patient')

    def test_hard_delete_patient_and_clinicaldata_sanity_check(self):
        patient_model1 = self.create_new_patient()
        patient_id1 = patient_model1.id
        patient_model2 = self.create_new_patient()
        patient_id2 = patient_model2.id
        self.create_clinicaldata(patient_id1, 'dummy')
        clinicaldata_model2 = self.create_clinicaldata(patient_id2, 'dummy')

        patient_model1._hard_delete()

        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.get(id=patient_id1)

        with self.assertRaises(Patient.DoesNotExist):
            Patient.objects.really_all().get(id=patient_id1)

        with self.assertRaises(ClinicalData.DoesNotExist):
            ClinicalData.objects.get(django_id=patient_id1, django_model='Patient')

        self.assertEqual(patient_model2.active, True)
        self.assertEqual(clinicaldata_model2.active, True)
        self.assertEqual(patient_model2.id, clinicaldata_model2.django_id)


class UpdateCalculatedFieldsTestCase(FormTestCase):

    def setUp(self):
        super().setUp()

        def form_value(form_name, section_code, cde_code, db_record):
            for form in db_record["forms"]:
                if form["name"] == form_name:
                    for section in form["sections"]:
                        if section["code"] == section_code:
                            for cde in section["cdes"]:
                                if cde["code"] == cde_code:
                                    return cde["value"]
        self.form_value = form_value

        from rdrf.management.commands.update_calculated_fields import context_ids_for_patient_and_form
        context_ids = context_ids_for_patient_and_form(self.patient, self.simple_form.name, self.registry)
        self.context_id = context_ids[0]

        ff = FormFiller(self.simple_form)
        ff.sectionA.CDEName = "Fred"
        ff.sectionA.CDEAge = 20
        ff.sectionB.CDEHeight = 1.82
        ff.sectionB.CDEWeight = 86.0
        ff.sectionB.CDEBMI = 38

        form_data = ff.data
        request = self._create_request(self.simple_form, form_data)
        view = FormView()
        view.request = request
        view.post(
            request,
            self.registry.code,
            self.simple_form.pk,
            self.patient.pk,
            self.context_id)

    def test_save_new_calculation(self):
        # Check the CDE value is correctly setup.
        collection = ClinicalData.objects.collection(self.registry.code, "cdes")
        db_record = collection.find(self.patient, self.context_id).data().first()
        assert self.form_value(
            self.simple_form.name,
            self.sectionA.code,
            "CDEAge",
            db_record) == 20

        # Change the CDE value and save it.
        changed_calculated_cdes = {"CDEAge": {"old_value": 20, "new_value": 21, "section_code": "sectionA"}}
        from rdrf.management.commands.update_calculated_fields import save_new_calculation
        save_new_calculation(changed_calculated_cdes, self.context_id,
                             self.simple_form.name, self.patient, self.registry)

        # Check that the CDE value has been updated.
        db_record = collection.find(self.patient, self.context_id).data().first()

        cdeage_value = self.form_value(
            self.simple_form.name,
            self.sectionA.code,
            "CDEAge",
            db_record)
        self.assertEqual(cdeage_value, 21)

    def test_update_calculated_fields_command(self):

        # Check the CDE value is correctly setup.
        collection = ClinicalData.objects.collection(self.registry.code, "cdes")
        db_record = collection.find(self.patient, self.context_id).data().first()
        cdebmi_value = self.form_value(
            self.simple_form.name,
            self.sectionB.code,
            "CDEBMI",
            db_record)
        self.assertEqual(cdebmi_value, "38")

        call_command('update_calculated_fields', registry_code=self.registry.code, patient_id=[self.patient.id])

        db_record = collection.find(self.patient, self.context_id).data().first()
        cdebmi_value = self.form_value(
            self.simple_form.name,
            self.sectionB.code,
            "CDEBMI",
            db_record)
        self.assertEqual(cdebmi_value, "25.96")


class CICImporterTestCase(TestCase):
    """
    Tests for the definition importer
    """
    def _get_yaml_file(self, suffix='original'):
        this_dir = os.path.dirname(__file__)
        test_yaml = os.path.abspath(os.path.join(this_dir, "..", "..", "fixtures", f"cic_lung_{suffix}.yaml"))
        return test_yaml

    def _get_survey_names(self):
        """
        returns a list of Survey names that are used in the imported registry
        :return: a list of Survey names
        """
        return self.registry.survey_set.all().values_list("name", flat=True)

    def _get_cde_codes(self):
        """
        returns a list of CDE codes that are used in the form sections of the imported registry
        :return: list of CDE codes
        """
        cdes = []
        for form in self.forms:
            for section in form.section_models:
                section_cdes = section.elements.split(",")
                cdes += section_cdes
        return cdes

    def _get_section_codes(self):
        sections = []
        for form in self.forms:
            sections += form.sections.split(",")
        return sections

    def _get_form_names(self):
        return [form.name for form in self.forms]

    def _get_pvg_codes(self):
        """
        returns a list of PVG codes that are used in the CDEs of the imported registry
        :return: list of PVG codes
        """
        cdes = []
        for form in self.forms:
            for section in form.section_models:
                section_cdes = section.elements.split(",")
                cdes += section_cdes

        return list(
            dict.fromkeys(
                [
                    code for code in CommonDataElement.objects.filter(code__in=cdes).values_list("pv_group", flat=True)
                    if code is not None
                ]
            )
        )

    def _get_state_pvs(self):
        """
        Returns a dict of State PV codes and positions
        """
        pv_group = CDEPermittedValueGroup.objects.get(code="State")
        return {pv.code: pv.position for pv in CDEPermittedValue.objects.filter(pv_group=pv_group).order_by('code')}

    def model_to_dict(self, model, instance, fields):
        """
        Returns a dict representation of the instance with requested fields
        :param model: django model class
        :param instance: instance of the model class
        :param fields: a dict of model class' field names and internal types
        :return: a dict of instance's fields and values
        """
        data = {}
        for f in sorted(fields.keys()):
            field_object = model._meta.get_field(f)
            field_value = field_object.value_from_object(instance)
            data[f] = field_value
            if fields[f] == "DecimalField":
                if field_value is not None:
                    data[f] = str(field_value)
                else:
                    data[f] = None
        return data

    def model_to_json_string(self, model, instance, fields):
        """
        Returns a json string representation of the instance with requested fields
        :param model: django model class
        :param instance: instance of the model class
        :param fields: a dict of model class' field names and internal types
        :return: a json string of instance's fields and values
        """
        return json.dumps(self.model_to_dict(model, instance, fields))

    def form_to_json_string(self, instance, fields):
        f = self.model_to_dict(RegistryForm, instance, fields)
        f["sections"] = [self.model_to_dict(Section, section, self.section_fields)
                         for section in instance.section_models]
        for section in f["sections"]:
            section["elements"] = section["elements"].split(",")
        return json.dumps(f)

    def _pvg_as_dict(self, pvg):
        """
        Returns a dict representation of PVG and its PVs in the same sructure as in yaml
        :param pvg: PVG object
        :return: a dict of PVG and its PVs (excluding pk of PV)
        """
        pv_fields = {f.name: f.get_internal_type() for f in CDEPermittedValue._meta.fields if not f.is_relation and not f.primary_key}
        d = {
            "code": pvg.code,
            "values": []
        }
        for pv in CDEPermittedValue.objects.filter(pv_group=pvg):
            value_dict = self.model_to_dict(CDEPermittedValue, pv, pv_fields)
            d["values"].append(value_dict)
        return d

    def _survey_question_as_dict(self, sq):
        """
        Returns a dict representation of SurveyQuestion in the same sructure as in yaml
        :param survey: SurveyQuestion object
        :return: a dict of SurveyQuestion
        """
        d = {
            "cde": sq.cde.code,
            "cde_path": sq.cde_path,
            "copyright_text": sq.copyright_text,
            "instruction": sq.instruction,
            "position": sq.position,
            "source": sq.source,
            "widget_config": sq.widget_config,
            "precondition": None
        }
        if sq.precondition:
            d["precondition"] = {
                "cde": sq.precondition.cde.code,
                "value": sq.precondition.value
            }
        return d

    def _survey_as_dict(self, survey):
        """
        Returns a dict representation of Survey and its SurveyQuestions in the same sructure as in yaml
        :param survey: Survey object
        :return: a dict of Survey and its SurveyQuestions
        """
        d = {
            "name": survey.name,
            "context_form_group": survey.context_form_group,
            "display_name": survey.display_name,
            "form": survey.form,
            "is_followup": survey.is_followup,
            "questions": []
        }
        for question in SurveyQuestion.objects.filter(survey=survey):
            question_dict = self._survey_question_as_dict(question)
            d["questions"].append(question_dict)
        return d

    def _precondition_cde_exists(self, precondition_cde, questions):
        for q in questions:
            exists = q["cde"] == precondition_cde
            if exists:
                return exists
        return False

    def setUp(self):
        self.maxDiff = None
        importer = Importer()
        importer.load_yaml(self._get_yaml_file())
        importer.create_registry()  # using the original yaml file here
        self.state_pvs_original = self._get_state_pvs()

        self.yaml_file = self._get_yaml_file(suffix='modified')
        with open(self.yaml_file) as yf:
            self.yaml_data = yaml.load(yf, Loader=yaml.FullLoader)
        importer.load_yaml(self.yaml_file)
        importer.create_registry()  # using the modified yaml file here

        self.cde_fields = {f.name: f.get_internal_type() for f in CommonDataElement._meta.fields}
        self.cdes_in_yaml = self.yaml_data["cdes"]

        self.state_pvs_modified = self._get_state_pvs()
        self.registry = Registry.objects.get(code=self.yaml_data["code"])

        self.forms = self.registry.forms

        self.surveys_in_yaml = self.yaml_data["surveys"]
        self.survey_names_in_db = self._get_survey_names()

        self.pvgs_in_yaml = self.yaml_data["pvgs"]
        self.pvg_codes_in_db = self._get_pvg_codes()

        self.section_fields = {f.name: f.get_internal_type() for f in Section._meta.fields if f.name != "id"}
        self.sections_in_yaml = []  # self.yaml_data["sections"]
        self.section_codes_in_db = self._get_section_codes()

        self.form_fields = {f.name: f.get_internal_type()
                            for f in RegistryForm._meta.fields
                            if not f.is_relation and f.name not in ["id", "is_questionnaire_login"]}
        self.forms_in_yaml = self.yaml_data["forms"]
        self.form_names_in_db = self._get_form_names()

    def assert_precondition_imported(self, q, survey_questions_in_db, survey_in_yaml):
        cde = q["precondition"]["cde"]
        value = q["precondition"]["value"]
        preconditions = Precondition.objects.filter(survey__name=survey_in_yaml["name"],
                                                    cde__code=cde, value=value).count()
        self.assertEqual(preconditions, 1)

    def assert_precondition_validity(self, q, survey_questions_in_db):
        precondition_cde = q["precondition"]["cde"]
        is_precondition_cde_present = self._precondition_cde_exists(precondition_cde,
                                                                    survey_questions_in_db)
        self.assertTrue(is_precondition_cde_present)

    def test_cdes(self):
        """
        Test if the imported CDE objects match the yaml
        """
        for cde_in_yaml in self.cdes_in_yaml:
            cde = CommonDataElement.objects.get(code=cde_in_yaml["code"])
            cde_from_db = self.model_to_json_string(CommonDataElement, cde, self.cde_fields)
            cde_from_yaml = json.dumps(cde_in_yaml)
            self.assertEqual(cde_from_yaml, cde_from_db)

    def test_forms(self):
        """
         Tests if the imported RegistryForm objects match the yaml
        """
        for form_in_yaml in self.forms_in_yaml:
            form = RegistryForm.objects.get(name=form_in_yaml["name"])
            form_from_db = self.form_to_json_string(form, self.form_fields)
            form_from_yaml = json.dumps(form_in_yaml)
            self.assertEqual(form_from_yaml, form_from_db)

    def test_survey_questions_and_preconditions(self):
        """
        Tests if these objects match the yaml
        - the imported SurveyQuestion objects
        - the imported Precondition objects
        """
        for survey_in_yaml in self.surveys_in_yaml:

            assert(survey_in_yaml["name"] in self.survey_names_in_db)

            if survey_in_yaml["name"] in self.survey_names_in_db:
                survey = Survey.objects.get(name=survey_in_yaml["name"])
                survey_in_db = self._survey_as_dict(survey)

                survey_questions_in_yaml = sorted(survey_in_yaml["questions"], key=lambda k: k["cde"])
                survey_questions_in_db = sorted(survey_in_db["questions"], key=lambda k: k["cde"])
                self.assertEqual(survey_questions_in_yaml, survey_questions_in_db)  # questions

                for question_in_db in survey_questions_in_db:
                    if question_in_db["precondition"] is not None:
                        self.assert_precondition_imported(question_in_db, survey_questions_in_db, survey_in_yaml)
                        self.assert_precondition_validity(question_in_db, survey_questions_in_db)

    def test_pvgs(self):
        """
        Test if the imported PermittedValueGroup objects match the yaml
        """
        for pvg_in_yaml in self.pvgs_in_yaml:
            if pvg_in_yaml["code"] in self.pvg_codes_in_db:
                pvg = CDEPermittedValueGroup.objects.get(code=pvg_in_yaml["code"])
                pvg_in_db = self._pvg_as_dict(pvg)

                pvg_values_in_yaml = sorted(pvg_in_yaml["values"], key=lambda k: k["code"])
                pvg_values_in_db = sorted(pvg_in_db["values"], key=lambda k: k["code"])
                self.assertEqual(pvg_values_in_yaml, pvg_values_in_db)

    def test_if_pvs_get_modified_by_import(self):
        """
        Test if the PermittedValue objects are modified on import.
        The position field was set to null in State values in the original yaml.
        The modified yaml has the position set to 1 to 8 for these values.
        """
        self.assertNotEqual(self.state_pvs_original, self.state_pvs_modified)

    def test_if_version_gets_modified_by_import(self):
        """
        Tests if the registry version gets modified with the import
        The original yaml has version 0.0.11 and the modified one has version 0.0.12
        """
        self.assertEqual(self.registry.version, "0.0.12")


class SetupPromsCommandTest(TestCase):

    def setUp(self):
        importer = Importer()
        importer.load_yaml(self._get_yaml_file())
        importer.create_registry()
        self.modified_yaml = self._get_yaml_file(suffix='modified')

    def _get_yaml_file(self, suffix='original'):
        this_dir = os.path.dirname(__file__)
        test_yaml = os.path.abspath(os.path.join(this_dir, "..", "..", "fixtures", f"cic_lung_{suffix}.yaml"))
        return test_yaml

    def test_version(self):
        call_command("setup_proms", yaml=self.modified_yaml)
        self.assertEqual(Registry.objects.get(code="ICHOMLC").version, "0.0.12")

    def test_preserving_metadata(self):
        call_command("setup_proms", yaml=self.modified_yaml)
        proms_system_url = Registry.objects.get(code="ICHOMLC").metadata["proms_system_url"]
        self.assertEqual(proms_system_url, "https://rdrf.ccgapps.com.au/ciclungproms")

    def test_overwriting_metadata(self):
        call_command("setup_proms", yaml=self.modified_yaml, override=True)
        proms_system_url = Registry.objects.get(code="ICHOMLC").metadata["proms_system_url"]
        self.assertEqual(proms_system_url, "https://rdrf.ccgapps.com.au/ciclungpromsmodified")


script_paths = {
    "rdrf": "/app/scripts",
    "mtm": "/app/rdrf/scripts",
}


class CheckViewsTestCase(TestCase):

    def test_check_views(self):
        proj_name = os.getenv("PROJECT_NAME")
        completed_process = subprocess.run(["python", f"{script_paths[proj_name]}/check_views.py", "/app/rdrf"], capture_output=True)
        if completed_process.returncode == 1:
            print("Insecure Views:")
            print(completed_process.stdout)
        self.assertEqual(completed_process.returncode, 0)


class CheckViewsUnitTests(TestCase):

    def setUp(self):
        import sys
        base_dir = os.getcwd()
        old_sys_path = sys.path
        proj_name = os.getenv("PROJECT_NAME")
        os.chdir(script_paths[proj_name])
        sys.path.append(".")
        from check_views import search_and_check_views
        os.chdir(base_dir)
        sys.path = old_sys_path

        self.func_to_test = search_and_check_views

    def check_view_assist(self, view_lines):
        good_view = True
        state = 's'
        view = ''

        for index, line_var in enumerate(view_lines):
            bad_view, state, view = self.func_to_test(
                line_var, view_lines, index, state, view
            )
            if bad_view:
                print(f"{line_var}: {state} {view}")
                good_view = False

        return good_view

    def test_search_and_check_views(self):
        not_a_view = [
            "def random_func(blah):",
            "   random = False",
            "   if blah:",
            "       random = True",
            "   return random",
            "",
            "class RandomClass():",
            "   var1 = 6",
            "   ",
            "   def get():",
            "       return var1",
            "",
        ]

        view_has_mixin = [
            "class HaveMixinView(LoginRequiredMixin, View):",
            "   ",
            "   def get(self, request):",
            "       return whatever",
            "   ",
            "   def post(self, request, query_id, action):",
            "       return another",
            "",
        ]

        view_has_decorators = [
            "class DecoratedView(View):",
            "   ",
            "   @login_required",
            "   def get(self, request):",
            "       return whatever",
            "   ",
            "   @method_decorator(login_required)",
            "   def post(self, request, query_id, action):",
            "       return another",
            "",
        ]

        view_lacks_security = [
            "class BadView(View):",
            "   ",
            "   def get(self, request):",
            "       return whatever",
            "   ",
            "   def post(self, request, query_id, action):",
            "       return another",
            "",
        ]

        self.assertTrue(self.check_view_assist(not_a_view), "Error: should not find bad view where there is no view!")
        self.assertTrue(self.check_view_assist(view_has_mixin), "Error: view has mixin, but mixin has not been found!")
        self.assertTrue(self.check_view_assist(view_has_decorators), "Error: view has decorators, but decorators have not been found!")
        self.assertFalse(self.check_view_assist(view_lacks_security), "Error: view is not secure, but no issues found!")


class CalculatedFieldSecurityTestCase(RDRFTestCase):

    def setUp(self):
        super(CalculatedFieldSecurityTestCase, self).setUp()
        self.registry = Registry.objects.get(code='fh')

        self.wg1, created = WorkingGroup.objects.get_or_create(name="testgroup1",
                                                               registry=self.registry)
        if created:
            self.wg1.save()

        self.wg2, created = WorkingGroup.objects.get_or_create(name="testgroup2",
                                                               registry=self.registry)
        if created:
            self.wg2.save()

        self.user1 = CustomUser.objects.get(username="curator")
        self.user1.registry.set([self.registry])
        self.user1.working_groups.add(self.wg1)
        self.user1.save()

        self.user2 = CustomUser.objects.get(username="clinical")
        self.user2.registry.set([self.registry])
        self.user2.working_groups.add(self.wg2)
        self.user2.save()

        self.user_admin = CustomUser.objects.get(username="admin")

        self.working_group, created = WorkingGroup.objects.get_or_create(name="WA")
        self.working_group.save()

        self.patient = self.create_patient()
        self.patient.working_groups.add(self.wg1)
        self.patient.save()

    def create_patient(self):
        from rdrf.db.contexts_api import RDRFContextManager

        p = Patient()
        p.consent = True
        p.name = "Harry"
        p.date_of_birth = datetime(1978, 6, 15)
        p.working_group = self.working_group
        p.save()
        p.rdrf_registry.set([self.registry])

        context_manager = RDRFContextManager(self.registry)
        self.default_context = context_manager.get_or_create_default_context(
            p, new_patient=True)

        return p

    def test_calc_field_security(self):
        from rdrf.helpers.utils import same_working_group, is_calculated_cde_in_registry
        # What tests do we need?
        # 1. Testing user and patient with matching working groups
        self.assertTrue(same_working_group(self.patient, self.user1, self.registry))

        # 2. Testing user and patient with mismatched working groups
        self.assertFalse(same_working_group(self.patient, self.user2, self.registry))

        # 3. Testing Admin working group matching
        self.assertTrue(same_working_group(self.patient, self.user_admin, self.registry))

        # 4. Testing if FH calculated field exists in FH
        self.assertTrue(is_calculated_cde_in_registry(CommonDataElement.objects.get(pk="CDEBMI"), self.registry))

        # 5. Testing if FH non-calculated field is picked up by function
        self.assertFalse(is_calculated_cde_in_registry(CommonDataElement.objects.get(pk="CDE00003"), self.registry))

        # 6. Testing if non-FH calculated field exists in FH
        # No non-FH calculated fields in the test data, but have
        # manually tested this in a local build with DD calc fields

"""
class HL7HandlerTestCase(RDRFTestCase):

    def _get_yaml_file(self, suffix='original'):
        this_dir = os.path.dirname(__file__)
        test_yaml = os.path.abspath(os.path.join(this_dir, "..", "..", "fixtures", f"cic_crc_{suffix}.yaml"))
        return test_yaml

    def setUp(self):
        importer = Importer()

        self.yaml_file = self._get_yaml_file()
        with open(self.yaml_file) as yf:
            self.yaml_data = yaml.load(yf, Loader=yaml.FullLoader)

        importer.load_yaml(self.yaml_file)
        importer.create_registry()

        self.registry = Registry.objects.get(code=self.yaml_data["code"])
        self.working_group, _ = WorkingGroup.objects.get_or_create(name="WA")

    def create_patient(self):
        from rdrf.db.contexts_api import RDRFContextManager

        p = Patient()
        p.consent = True
        p.name = "Harry"
        p.umrn = "1234"
        p.date_of_birth = datetime(1950, 1, 31)
        p.working_group = self.working_group
        p.save()
        p.rdrf_registry.set([self.registry])

        context_manager = RDRFContextManager(self.registry)
        self.default_context = context_manager.get_or_create_default_context(p, new_patient=True)

        return p

    def _create_hl7mapping(self):
        from intframework.models import HL7Mapping
        mapping = {"ADR_A19": {
            "Demographics/family_name": {"path": "PID.F5.R1.C1"},
            "Demographics/given_names": {"path": "PID.F5.R1.C2"},
            "Demographics/umrn": {"path": "PID.F3"},
            "Demographics/date_of_birth": {"path": "PID.F7", "tag": "transform", "function": "date"},
            "Demographics/date_of_death": {"path": "PID.F29", "tag": "transform", "function": "date"},
            "Demographics/place_of_birth": {"path": "PID.F23"},
            "Demographics/country_of_birth": {"path": "PID.F11.R1.C6"},
            "Demographics/ethnic_origin": {"path": "PID.F22.R1.C2"},
            "Demographics/sex": {"path": "PID.F8", "tag": "mapping",
                                 "map": {"M": 1, "F": 2, "U": 3, "O": 3, "A": 3, "N": 3}},
            "Demographics/home_phone": {"path": "PID.F13"},
            "Demographics/work_phone": {"path": "PID.F14"}
        }}
        hm = HL7Mapping.objects.create(event_code="ADR_A19", event_map=json.dumps(mapping))
        hm.save()

    def test_update_patient(self):
        from intframework.updater import HL7Handler
        from intframework.hub import MockClient
        self._create_hl7mapping()
        self.patient = self.create_patient()
        user = get_user_model().objects.get(username="curator")
        client = MockClient(self.registry, user, settings.HUB_ENDPOINT, settings.HUB_PORT)
        response_data = client.get_data("1234")
        print(response_data)
        hl7message = response_data["message"]
        hl7_handler = HL7Handler(umrn="1234", hl7message=hl7message)
        result = hl7_handler.handle()
        print(result)
        updated_patient = Patient.objects.get(pk=self.patient.id)
        self.assertEqual(updated_patient.given_names.upper(), "FRANCIS")
"""

class FamilyLinkageTestCase(RDRFTestCase):

    def setUp(self):
        super(FamilyLinkageTestCase, self).setUp()
        # need to import FH to correctly use family linkage
        this_dir = os.path.dirname(__file__)
        test_yaml = os.path.abspath(os.path.join(this_dir, "..", "..", "fixtures", "exported_fh_registry.yaml"))
        importer = Importer()
        importer.load_yaml(test_yaml)
        importer.create_registry()
        self.registry = Registry.objects.get(code='fh')
        self.address_type, created = AddressType.objects.get_or_create(pk=1)
        # make 3 patients for full tests
        self.patient_ids = self.create_patients()
        # maybe make non-patient relative for "non-patient to index" use case

    def create_new_patient(self, given_name, surname, date_of_birth, sex, living_status, p_ids):
        from rdrf.db.contexts_api import RDRFContextManager

        patient_new = Patient()
        patient_new.consent = True
        patient_new.given_names = given_name
        patient_new.family_name = surname
        patient_new.date_of_birth = date_of_birth
        for choice in Patient.SEX_CHOICES:
            if choice[1] == sex:
                patient_new.sex = choice[0]
        for living_state in Patient.LIVING_STATES:
            if living_state[1] == living_status:
                patient_new.living_status = living_state[0]

        patient_new.save()
        patient_new.rdrf_registry.set([self.registry])
        context_manager = RDRFContextManager(self.registry)
        default_context = context_manager.get_or_create_default_context(
            patient_new, new_patient=True)
        patient_new.save()
        p_ids += [patient_new.pk, ]

        return patient_new, p_ids, default_context

    def create_new_patient_relative(self, given_name, surname, date_of_birth, sex, living_status, location, index):
        from registry.patients.models import PatientRelative

        patient_rel_new = PatientRelative()
        patient_rel_new.given_names = given_name
        patient_rel_new.family_name = surname
        patient_rel_new.date_of_birth = date_of_birth
        for choice in PatientRelative.SEX_CHOICES:
            if choice[1] == sex:
                patient_rel_new.sex = choice[0]
        for living_state in PatientRelative.LIVING_STATES:
            if living_state[1] == living_status:
                patient_rel_new.living_status = living_state[0]
        patient_rel_new.location = location
        patient_rel_new.patient = index
        patient_rel_new.save()

        return patient_rel_new

    def create_address(self, address_type, street_address, country, patient):
        address_new = PatientAddress()
        address_new.address_type = AddressType.objects.get(pk=address_type)
        address_new.address = street_address
        address_new.country = country
        address_new.patient = patient
        address_new.save()

    def create_patients(self):
        # each patient needs an address, living status, sex, given name, and surname for full tests
        # import addresses first
        # from registry.patients.models import PatientAddress
        # make patients with func, and add pks to list
        patient_ids = []
        patient_1, patient_ids, self.patient_1_context = self.create_new_patient("Test", "Test", datetime(1989, 10, 21), "Male", "Living", patient_ids)
        patient_2, patient_ids, self.patient_2_context = self.create_new_patient("Chester", "Test", datetime(1979, 4, 13), "Male", "Living", patient_ids)
        # patient_3, patient_ids, self.patient_3_context = self.create_new_patient("Hester", "Test", datetime(1968, 1, 4), "Female", "Living", patient_ids)
        # make addresses and assign to patients with func - extend later with extra home & some postal addrs
        self.create_address(1, "123 Somewhere Street", "Australia", patient_1)
        self.create_address(1, "99 Unheardof Avenue", "United Kingdom", patient_2)
        # self.create_address(1, "5 Goodbye Grange", "Morocco", patient_3)
        return patient_ids

    def run_linkage_manager(self, new_packet):
        from rdrf.views.family_linkage import FamilyLinkageManager
        self.linkage_manager = FamilyLinkageManager(self.registry, new_packet)
        self.linkage_manager.run()

    def patient_is_index(self, patient):
        family_linkage_value = patient.get_form_value(
            self.registry.code,
            self.registry.metadata['family_linkage_form_name'],
            self.registry.metadata['family_linkage_section_code'],
            self.registry.metadata['family_linkage_cde_code']
        )
        return family_linkage_value == 'fh_is_index'

    def patient_is_relative(self, patient):
        family_linkage_value = patient.get_form_value(
            self.registry.code,
            self.registry.metadata['family_linkage_form_name'],
            self.registry.metadata['family_linkage_section_code'],
            self.registry.metadata['family_linkage_cde_code']
        )
        return family_linkage_value == 'fh_is_relative'

    def test_family_linkage_manager(self):
        from registry.patients.models import PatientRelative
        # What tests do we need?
        # First, set index patient
        error_string = "Error in section: "
        test_section_str = "Setting initial index"
        patient1_test = Patient.objects.get(pk=self.patient_ids[0])
        # make FamilyLinkageManager with initial packet
        init_packet = {
            'index': {
                'pk': patient1_test.pk,
                'given_names': patient1_test.given_names,
                'family_name': patient1_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient1_test.pk}/edit'
            },
            'relatives': [],
            'original_index': {
                'pk': patient1_test.pk,
                'given_names': patient1_test.given_names,
                'family_name': patient1_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient1_test.pk}/edit'
            }
        }
        logger.info(f"{test_section_str}...")
        self.run_linkage_manager(init_packet)
        self.assertTrue(self.linkage_manager.index_patient == patient1_test,
                        f"{error_string}{test_section_str}: Index in linkage manager does not match Patient {patient1_test} (ID = {patient1_test.pk})")
        self.assertTrue(self.patient_is_index(patient1_test),
                        f"{error_string}{test_section_str}: Patient {patient1_test} (ID = {patient1_test.pk}) is not index")

        # 1. Link patient to index patient, check that location, living status, and sex carry over
        test_section_str = "Linking new patient to index"
        patient2_test = Patient.objects.get(pk=self.patient_ids[1])
        link_patient_to_index_packet = {
            'index': {
                'pk': patient1_test.pk,
                'given_names': patient1_test.given_names,
                'family_name': patient1_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient1_test.pk}/edit'
            },
            'relatives': [
                {
                    'pk': patient2_test.pk,
                    'given_names': patient2_test.given_names,
                    'family_name': patient2_test.family_name,
                    'class': 'Patient',
                    'working_group': None,
                    'link': f'/fh/patient/{patient2_test.pk}/edit',
                    'relationship': 'Sibling (1st degree)'
                },
            ],
            'original_index': {
                'pk': patient1_test.pk,
                'given_names': patient1_test.given_names,
                'family_name': patient1_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient1_test.pk}/edit'
            }
        }
        logger.info(f"{test_section_str}...")
        self.run_linkage_manager(link_patient_to_index_packet)

        # No opposite to assertRaises - this test expects an exception NOT to be raised
        try:
            relative_patient2_test = PatientRelative.objects.get(relative_patient=patient2_test)
        except PatientRelative.DoesNotExist:
            self.fail(f"{error_string}{test_section_str}: PatientRelative for Patient {patient2_test} (ID = {patient2_test.pk}) has not been created")
        self.assertTrue(relative_patient2_test.sex == patient2_test.sex,
                        f"{error_string}{test_section_str}: PatientRelative sex {relative_patient2_test.sex} does not match Patient {patient2_test} sex '{patient2_test.sex}'")
        self.assertTrue(relative_patient2_test.living_status == patient2_test.living_status,
                        f"{error_string}{test_section_str}: PatientRelative living status {relative_patient2_test.living_status} does not match Patient {patient2_test} living status '{patient2_test.living_status}'")
        self.assertTrue(relative_patient2_test.location == PatientAddress.objects.get(patient=patient2_test).country,
                        f"{error_string}{test_section_str}: PatientRelative location {relative_patient2_test.location} does not match Patient {patient2_test} location '{PatientAddress.objects.get(patient=patient2_test).country}'")
        self.assertTrue(relative_patient2_test.patient == patient1_test,
                        f"{error_string}{test_section_str}: PatientRelative index {relative_patient2_test.patient} does not match Patient {patient1_test}")
        self.assertTrue(relative_patient2_test in patient1_test.relatives.all(),
                        f"{error_string}{test_section_str}: PatientRelative is not in index {patient1_test}'s relatives")
        self.assertTrue(relative_patient2_test.relationship == "Sibling (1st degree)",
                        f"{error_string}{test_section_str}: PatientRelative's relationship {relative_patient2_test.relationship} does not match 'Sibling (1st degree)'")
        self.assertTrue(self.patient_is_relative(patient2_test),
                        f"{error_string}{test_section_str}: Patient {patient2_test} is not a relative")
        self.assertFalse(self.patient_is_index(patient2_test),
                         f"{error_string}{test_section_str}: Patient {patient2_test} is an index")

        # 2. Swap relative to index, check that original index's location, living status, and sex are preserved
        test_section_str = "Setting relative to be new index"
        relative_to_index_packet = {
            'index': {
                'pk': relative_patient2_test.pk,
                'given_names': relative_patient2_test.given_names,
                'family_name': relative_patient2_test.family_name,
                'class': 'PatientRelative',
                'working_group': None,
                'link': f'/fh/patient/{relative_patient2_test.relative_patient.pk}/edit'
            },
            'relatives': [
                {
                    'pk': patient1_test.pk,
                    'given_names': patient1_test.given_names,
                    'family_name': patient1_test.family_name,
                    'class': 'Patient',
                    'working_group': None,
                    'link': f'/fh/patient/{patient1_test.pk}/edit',
                    'relationship': 'Sibling (1st degree)'
                },
            ],
            'original_index': {
                'pk': patient1_test.pk,
                'given_names': patient1_test.given_names,
                'family_name': patient1_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient1_test.pk}/edit'
            }
        }
        logger.info(f"{test_section_str}...")
        self.run_linkage_manager(relative_to_index_packet)

        with self.assertRaises(PatientRelative.DoesNotExist, msg=f"{error_string}{test_section_str}: PatientRelative for Patient {patient2_test} exists when it should not"):
            relative_patient2_test = PatientRelative.objects.get(relative_patient=patient2_test)
        self.assertTrue(self.patient_is_index(patient2_test),
                        f"{error_string}{test_section_str}: Patient {patient2_test} is not an index")
        self.assertFalse(self.patient_is_relative(patient2_test),
                         f"{error_string}{test_section_str}: Patient {patient2_test} is a relative")
        try:
            relative_patient1_test = PatientRelative.objects.get(relative_patient=patient1_test)
        except PatientRelative.DoesNotExist:
            self.fail(f"{error_string}{test_section_str}: PatientRelative for Patient {patient1_test} (ID = {patient1_test.pk}) has not been created")
        self.assertTrue(relative_patient1_test.sex == patient1_test.sex,
                        f"{error_string}{test_section_str}: PatientRelative sex {relative_patient1_test.sex} does not match Patient {patient1_test} sex '{patient1_test.sex}'")
        self.assertTrue(relative_patient1_test.living_status == patient1_test.living_status,
                        f"{error_string}{test_section_str}: PatientRelative living status {relative_patient1_test.living_status} does not match Patient {patient1_test} living status '{patient1_test.living_status}'")
        self.assertTrue(relative_patient1_test.location == PatientAddress.objects.get(patient=patient1_test).country,
                        f"{error_string}{test_section_str}: PatientRelative location {relative_patient1_test.location} does not match Patient {patient1_test} location '{PatientAddress.objects.get(patient=patient1_test).country}'")
        self.assertTrue(relative_patient1_test.patient == patient2_test,
                        f"{error_string}{test_section_str}: PatientRelative index {relative_patient1_test.patient} does not match Patient {patient2_test}")
        self.assertTrue(relative_patient1_test in patient2_test.relatives.all(),
                        f"{error_string}{test_section_str}: PatientRelative is not in index {patient2_test}'s relatives")
        self.assertTrue(relative_patient1_test.relationship == "Sibling (1st degree)",
                        f"{error_string}{test_section_str}: PatientRelative's relationship {relative_patient1_test.relationship} does not match 'Sibling (1st degree)'")
        self.assertTrue(self.patient_is_relative(patient1_test),
                        f"{error_string}{test_section_str}: Patient {patient1_test} is not a relative")
        self.assertFalse(self.patient_is_index(patient1_test),
                         f"{error_string}{test_section_str}: Patient {patient1_test} is an index")

        # 3. Add non-patient relative, ensure it proceeds correctly
        test_section_str = "Creating non-patient relative"
        logger.info(f"{test_section_str}...")
        relative_test = self.create_new_patient_relative("Hester", "Test", datetime(1968, 1, 4), "Female", "Living", "MA", patient2_test)
        self.assertFalse(relative_test.relationship,
                         f"{error_string}{test_section_str}: PatientRelative {relative_test.given_names} {relative_test.family_name}'s relationship should not be defined")

        test_section_str = "Linking non-patient relative to index"
        add_non_patient_relative_packet = {
            'index': {
                'pk': patient2_test.pk,
                'given_names': patient2_test.given_names,
                'family_name': patient2_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient2_test.pk}/edit'
            },
            'relatives': [
                {
                    'pk': relative_patient1_test.pk,
                    'given_names': patient1_test.given_names,
                    'family_name': patient1_test.family_name,
                    'class': 'PatientRelative',
                    'working_group': None,
                    'link': f'/fh/patient/{patient1_test.pk}/edit',
                    'relationship': 'Sibling (1st degree)'
                },
                {
                    'pk': relative_test.pk,
                    'given_names': relative_test.given_names,
                    'family_name': relative_test.family_name,
                    'class': 'PatientRelative',
                    'working_group': None,
                    'link': None,
                    'relationship': '1st Cousin (3rd degree)'
                }
            ],
            'original_index': {
                'pk': patient2_test.pk,
                'given_names': patient2_test.given_names,
                'family_name': patient2_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient2_test.pk}/edit'
            }
        }
        logger.info(f"{test_section_str}...")
        self.run_linkage_manager(add_non_patient_relative_packet)

        relative_test = PatientRelative.objects.get(pk=relative_test.pk)  # Need to re-get relative for relationship to be tested properly
        self.assertTrue(relative_test.pk in [rel['pk'] for rel in self.linkage_manager.relatives],
                        f"{error_string}{test_section_str}: PatientRelative {relative_test.given_names} {relative_test.family_name} is not in linkage manager relative list")
        self.assertFalse(relative_test.relative_patient,
                         f"{error_string}{test_section_str}: PatientRelative {relative_test.given_names} {relative_test.family_name} is a non-patient relative and should not be linked to a patient")
        self.assertTrue(relative_test.patient == patient2_test,
                        f"{error_string}{test_section_str}: PatientRelative index {relative_test.patient} does not match Patient {patient2_test}")
        self.assertTrue(relative_test.relationship == "1st Cousin (3rd degree)",
                        f"{error_string}{test_section_str}: PatientRelative's relationship {relative_test.relationship} does not match '1st Cousin (3rd degree)'")
        self.assertTrue(relative_test in patient2_test.relatives.all(),
                        f"{error_string}{test_section_str}: PatientRelative is not in index {patient2_test}'s relatives")

        # 4. Swap non-patient relative to index, check that new patient is created + results of test #2
        test_section_str = "Setting non-patient relative to be new index"
        relative_test_data = {
            'pk': relative_test.pk,
            'given_names': relative_test.given_names,
            'family_name': relative_test.family_name,
            'date_of_birth': relative_test.date_of_birth,
            'sex': relative_test.sex,
            'living_status': relative_test.living_status
        }

        non_patient_to_index_packet = {
            'index': {
                'pk': relative_test.pk,
                'given_names': relative_test.given_names,
                'family_name': relative_test.family_name,
                'class': 'PatientRelative',
                'working_group': None,
                'link': None
            },
            'relatives': [
                {
                    'pk': relative_patient1_test.pk,
                    'given_names': patient1_test.given_names,
                    'family_name': patient1_test.family_name,
                    'class': 'PatientRelative',
                    'working_group': None,
                    'link': f'/fh/patient/{patient1_test.pk}/edit',
                    'relationship': '1st Cousin (3rd degree)'
                },
                {
                    'pk': patient2_test.pk,
                    'given_names': patient2_test.given_names,
                    'family_name': patient2_test.family_name,
                    'class': 'Patient',
                    'working_group': None,
                    'link': f'/fh/patient/{patient2_test.pk}/edit',
                    'relationship': '1st Cousin (3rd degree)'
                }
            ],
            'original_index': {
                'pk': patient2_test.pk,
                'given_names': patient2_test.given_names,
                'family_name': patient2_test.family_name,
                'class': 'Patient',
                'working_group': None,
                'link': f'/fh/patient/{patient2_test.pk}/edit'
            }
        }
        logger.info(f"{test_section_str}...")
        self.run_linkage_manager(non_patient_to_index_packet)

        with self.assertRaises(PatientRelative.DoesNotExist, msg=f"{error_string}{test_section_str}: PatientRelative still exists when it should not"):
            relative_test = PatientRelative.objects.get(pk=relative_test_data['pk'])
        try:
            relative_patient1_test = PatientRelative.objects.get(relative_patient=patient1_test)
        except PatientRelative.DoesNotExist:
            self.fail(f"{error_string}{test_section_str}: PatientRelative for Patient {patient1_test} (ID = {patient1_test.pk}) does not exist")
        try:
            relative_patient2_test = PatientRelative.objects.get(relative_patient=patient2_test)
        except PatientRelative.DoesNotExist:
            self.fail(f"{error_string}{test_section_str}: PatientRelative for Patient {patient2_test} (ID = {patient2_test.pk}) has not been created")
        relative_test_patient = relative_patient1_test.patient
        self.assertTrue(relative_test_patient,
                        f"{error_string}{test_section_str}: New index patient does not exist")
        self.assertTrue(self.patient_is_index(relative_test_patient),
                        f"{error_string}{test_section_str}: Patient {relative_test_patient} is not an index")
        self.assertTrue(self.patient_is_relative(patient2_test),
                        f"{error_string}{test_section_str}: Patient {patient2_test} is not a relative")
        self.assertTrue(relative_patient1_test in relative_test_patient.relatives.all(),
                        f"{error_string}{test_section_str}: PatientRelative {relative_patient1_test.given_names} {relative_patient1_test.family_name} is not in index {relative_test_patient}'s relatives")
        self.assertTrue(relative_patient2_test in relative_test_patient.relatives.all(),
                        f"{error_string}{test_section_str}: PatientRelative {relative_patient2_test.given_names} {relative_patient2_test.family_name} is not in index {relative_test_patient}'s relatives")
        self.assertTrue(relative_test_patient.given_names == relative_test_data['given_names'],
                        f"{error_string}{test_section_str}: Patient given name {relative_test_patient.given_names} does not match PatientRelative given name {relative_test_data['given_names']}")
        self.assertTrue(relative_test_patient.family_name.lower() == relative_test_data['family_name'].lower(),
                        f"{error_string}{test_section_str}: Patient surname {relative_test_patient.family_name} does not match (lowercase) PatientRelative surname {relative_test_data['family_name']}")
        self.assertTrue(relative_test_patient.date_of_birth == relative_test_data['date_of_birth'],
                        f"{error_string}{test_section_str}: Patient date of birth {relative_test_patient.date_of_birth} does not match PatientRelative date of birth {relative_test_data['date_of_birth']}")
        self.assertTrue(relative_test_patient.sex == relative_test_data['sex'],
                        f"{error_string}{test_section_str}: Patient sex {relative_test_patient.sex} does not match PatientRelative sex {relative_test_data['sex']}")
        self.assertTrue(relative_test_patient.living_status == relative_test_data['living_status'],
                        f"{error_string}{test_section_str}: Patient living status {relative_test_patient.living_status} does not match PatientRelative living status {relative_test_data['living_status']}")
        self.assertTrue(relative_patient1_test.relationship == "1st Cousin (3rd degree)",
                        f"{error_string}{test_section_str}: PatientRelative {relative_patient1_test.given_names} {relative_patient1_test.family_name}'s relationship {relative_patient1_test.relationship} does not match '1st Cousin (3rd degree)'")
        self.assertTrue(relative_patient2_test.relationship == "1st Cousin (3rd degree)",
                        f"{error_string}{test_section_str}: PatientRelative {relative_patient2_test.given_names} {relative_patient2_test.family_name}'s relationship {relative_patient2_test.relationship} does not match '1st Cousin (3rd degree)'")
        self.assertTrue(relative_patient2_test.sex == patient2_test.sex,
                        f"{error_string}{test_section_str}: PatientRelative sex {relative_patient2_test.sex} does not match Patient {patient2_test} sex '{patient2_test.sex}'")
        self.assertTrue(relative_patient2_test.living_status == patient2_test.living_status,
                        f"{error_string}{test_section_str}: PatientRelative living status {relative_patient2_test.living_status} does not match Patient {patient2_test} living status '{patient2_test.living_status}'")
        self.assertTrue(relative_patient2_test.location == PatientAddress.objects.get(patient=patient2_test).country,
                        f"{error_string}{test_section_str}: PatientRelative location {relative_patient2_test.location} does not match Patient {patient2_test} location '{PatientAddress.objects.get(patient=patient2_test).country}'")
        self.assertTrue(self.patient_is_relative(patient2_test),
                        f"{error_string}{test_section_str}: Patient {patient2_test} is not a relative")
        self.assertFalse(self.patient_is_index(patient2_test),
                         f"{error_string}{test_section_str}: Patient {patient2_test} is an index")
