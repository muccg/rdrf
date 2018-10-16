# -*- encoding: utf-8 -*-
import logging
import os
import yaml
from datetime import datetime
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from django.test import TestCase, RequestFactory

from rdrf.services.io.defs.exporter import Exporter, ExportType
from rdrf.services.io.defs.importer import Importer, ImportState
from rdrf.models.definition.models import Registry, RegistryForm, Section
from rdrf.models.definition.models import CDEPermittedValueGroup, CDEPermittedValue
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import ClinicalData
from rdrf.views.form_view import FormView
from registry.patients.models import Patient
from registry.patients.models import State, PatientAddress, AddressType
from django.contrib.auth.models import Group
from registry.groups.models import WorkingGroup, CustomUser
from rdrf.helpers.utils import de_camelcase, check_calculation, TimeStripper
from copy import deepcopy

from rdrf.models.definition.models import EmailNotification
from rdrf.models.definition.models import EmailTemplate
from rdrf.models.definition.models import EmailNotificationHistory
from django.core.management import call_command
import json

from rdrf.helpers.transform_cd_dict import get_cd_form, get_section, transform_cd_dict

logger = logging.getLogger(__name__)


class MigrateCDESTestCase(TestCase):

    def setUp(self):
        # source section with multi-value
        self.input_data = {'forms': [{'name': 'ClinicalData', 'sections': [{'cdes': [{'code': 'CDEIndexOrRelative', 'value': 'fh_is_index'}, {'code': 'FHconsentDate', 'value': None}, {'code': 'DateOfAssessment', 'value': '2018-07-02'}, {'code': 'fhAgeAtConsent', 'value': 'NaN'}, {'code': 'fhAgeAtAssessment', 'value': '0'}], 'code': 'fhDateSection', 'allow_multiple': False}, {'cdes': [{'code': 'CDEfhDutchLipidClinicNetwork', 'value': ''}, {'code': 'CDE00024', 'value': ''}], 'code': 'SEC0007', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00003', 'value': 'fh2_n'}, {'code': 'FHFamilyHistoryChild', 'value': 'fh_n'}, {'code': 'CDE00004', 'value': 'fh2_n'}, {'code': 'FHFamHistTendonXanthoma', 'value': 'fh2_n'}, {'code': 'FHFamHistArcusCornealis', 'value': 'fh2_n'}], 'code': 'SEC0002', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00011', 'value': 'fhpremcvd_no'}, {'code': 'FHMyocardialInfarction', 'value': ''}, {'code': 'FHAgeAtMI', 'value': None}, {'code': 'FHCoronaryRevasc', 'value': ''}, {'code': 'FHAgeAtCV', 'value': None}, {'code': 'FHPersHistCerebralVD', 'value': 'fh2_n'}, {'code': 'FHAorticValveDisease', 'value': ''}, {'code': 'FHSupravalvularDisease', 'value': ''}, {'code': 'FHPremNonCoronary', 'value': ''}], 'code': 'SEC0004', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00001', 'value': 'n_'}, {'code': 'CDE00002', 'value': 'n_'}, {'code': 'FHXanthelasma', 'value': ''}], 'code': 'SEC0001', 'allow_multiple': False}, {'cdes': [{'code': 'CDE00013', 'value': None}, {'code': 'CDE00019', 'value': None}, {'code': 'PlasmaLipidTreatment', 'value': ''}, {'code': 'LDLCholesterolAdjTreatment', 'value': 'NaN'}], 'code': 'FHLDLforFHScore', 'allow_multiple': False}, {'cdes': [[{'code': 'FHLipidProfileUntreatedDate', 'value': '2018-07-02'}, {'code': 'CDE00012', 'value': 2.0}, {'code': 'FHLLDLconc', 'value': 2.0}, {'code': 'CDE00014', 'value': 2.0}, {'code': 'CDE00015', 'value': 2.0}, {'code': 'FHApoB', 'value': 2.0}, {'code': 'CDE00016', 'value': 2.0}, {'code': 'FHAST', 'value': 2}, {'code': 'FHALT', 'value': 2}, {'code': 'FHCK', 'value': 2}, {'code': 'FHCreatinine', 'value': 2}, {'code': 'FHCRP', 'value': 2.0}, {'code': 'PlasmaLipidTreatmentNone', 'value': 'Fluvastatin40'}, {'code': 'CDEfhOtherIntolerantDrug', 'value': ''}, {'code': 'FHCompliance', 'value': ''}], [{'code': 'FHLipidProfileUntreatedDate', 'value': '2018-07-02'}, {'code': 'CDE00012', 'value': 2.5}, {'code': 'FHLLDLconc', 'value': 2.5}, {'code': 'CDE00014', 'value': 2.5}, {'code': 'CDE00015', 'value': 2.5}, {'code': 'FHApoB', 'value': 2.5}, {'code': 'CDE00016', 'value': 2.5}, {'code': 'FHAST', 'value': 2}, {'code': 'FHALT', 'value': 2}, {'code': 'FHCK', 'value': 2}, {'code': 'FHCreatinine', 'value': 2}, {'code': 'FHCRP', 'value': 2.0}, {'code': 'PlasmaLipidTreatmentNone', 'value': 'Fluvastatin/Ezetimibe20'}, {'code': 'CDEfhOtherIntolerantDrug', 'value': ''}, {'code': 'FHCompliance', 'value': ''}]], 'code': 'SEC0005', 'allow_multiple': True}, {'cdes': [{'code': 'CDE00005', 'value': ''}, {'code': 'FHPackYears', 'value': None}, {'code': 'FHAlcohol', 'value': ''}, {'code': 'FHHypertriglycerd', 'value': ''}, {'code': 'CDE00006', 'value': ''}, {'code': 'CDE00008', 'value': None}, {'code': 'CDE00009', 'value': None}, {'code': 'FHHeartRate', 'value': None}, {'code': 'CDE00007', 'value': ''}, {'code': 'CDE00010', 'value': None}, {'code': 'HbA1c', 'value': None}, {'code': 'ChronicKidneyDisease', 'value': ''}, {'code': 'FHeGFR', 'value': ''}, {'code': 'FHHypothyroidism', 'value': ''}, {'code': 'FHTSH', 'value': None}, {'code': 'FHHepaticSteatosis', 'value': ''}, {'code': 'FHObesity', 'value': ''}, {'code': 'CDEHeight', 'value': None}, {'code': 'CDEWeight', 'value': None}, {'code': 'CDEBMI', 'value': 'NaN'}, {'code': 'FHWaistCirc', 'value': None}, {'code': 'FHCVDOther', 'value': 'test2 ddddddddd'}], 'code': 'SEC0003', 'allow_multiple': False}, {'cdes': [[{'code': 'FHClinicalTrialName', 'value': ''}, {'code': 'FHTrialLength', 'value': None}, {'code': 'FHTrialSTartDate', 'value': None}, {'code': 'FHTrialStatus', 'value': ''}]], 'code': 'FHClinicalTrials', 'allow_multiple': True}]}], 'django_id': 3, 'timestamp': '2018-07-19T15:14:04.887064', 'context_id': 3, 'django_model': 'Patient', 'ClinicalData_timestamp': '2018-07-19T15:14:04.887064'}

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
        f.groups_allowed = [clinical_group]
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
            data = yaml.load(f)

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
        test_yaml= os.path.abspath(os.path.join(this_dir, "..", "..", "fixtures", "exported_fh_registry.yaml"))
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
        self.user.registry = [self.registry]
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
        p.rdrf_registry = [self.registry]

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
        return request

    def create_sections(self):
        # "simple" sections ( no files or multi-allowed sections
        self.sectionA = self.create_section(
            "sectionA", "Simple Section A", ["CDEName", "CDEAge"])
        self.sectionB = self.create_section(
            "sectionB", "Simple Section B", ["CDEHeight", "CDEWeight"])
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


class JavascriptCheckTestCase(TestCase):

    def test_empty_script(self):
        err = check_calculation("")
        self.assertEqual(err, "")

    def test_simple(self):
        err = check_calculation("var test = 42;")
        self.assertEqual(err, "")

    def test_context_result(self):
        err = check_calculation("context.result = 42;")
        self.assertEqual(err, "")

    def test_patient_context(self):
        err = check_calculation("context.result = patient.age / 2 + 7;")
        self.assertEqual(err, "")

    def test_adsafe_this(self):
        err = check_calculation("this.test = true;")
        self.assertTrue(err)

    def test_lint_dodgy(self):
        err = check_calculation("// </script>")
        self.assertTrue(err)

    def test_adsafe_subscript(self):
        err = check_calculation("""
           var i = 42;
           context[i] = "hello";
        """)
        self.assertTrue(err)

    def test_date(self):
        err = check_calculation("context.result = new Date();")
        self.assertEqual(err, "")

    def test_nonascii(self):
        err = check_calculation("context.result = '💩';")
        self.assertEqual(err, "")


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
                                                                      {'value': '1972-06-15T00:00:00.00', 'code': 'DateOfAssessment'},
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
        l = ["a", "B", bottom]
        g = sorted(l)
        self.assertTrue(g[0] is bottom)

    def test_ints(self):
        from rdrf.helpers.utils import MinType
        bottom = MinType()
        l = [10, 1, -7, bottom]
        g = sorted(l)
        self.assertTrue(g[0] is bottom)


class StructureChecker(TestCase):
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
        self.user.registry = [self.registry]
        self.user.save()

        if group == "patients":
            self.user.groups = [patients_group]
        elif group == "parents":
            self.user.groups = [parents_group]
        elif group == "curators":
            self.user.groups = [curators_group]

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
