from django.test import TestCase, RequestFactory
from rdrf.exporter import Exporter, ExportType
from rdrf.importer import Importer, ImportState
from rdrf.models import Section
from rdrf.models import Registry
from rdrf.models import CDEPermittedValueGroup
from rdrf.models import CDEPermittedValue
from rdrf.models import CommonDataElement
from rdrf.models import RegistryForm
from rdrf.form_view import FormView
from registry.patients.models import Patient
from registry.groups.models import WorkingGroup
from registry.patients.models import State, PatientAddress, AddressType
from datetime import datetime
from pymongo import MongoClient
from django.forms.models import model_to_dict
import yaml
from django.contrib.auth import get_user_model
from rdrf.utils import de_camelcase

from django.conf import settings
import os


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
    fixtures = ['testing_auth.json', 'testing_users.json', 'testing_rdrf.json']


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

        from rdrf.models import CommonDataElement
        dummy_cde = CommonDataElement.objects.create()
        cde_fields = model_to_dict(dummy_cde).keys()
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


class ImporterTestCase(RDRFTestCase):

    def _get_yaml_file(self):
        return os.path.join(os.path.dirname(__file__), 'fixtures', 'exported_fh_registry.yaml')

    def test_importer(self):
        # first delete the FH registry
        fh_reg = Registry.objects.get(code='fh')
        fh_reg.delete()

        # delete cdes
        for cde in CommonDataElement.objects.all():
            cde.delete()
        # delete permissible value groups
        for pvg in CDEPermittedValueGroup.objects.all():
            pvg.delete()

        # delete permissible values
        for value in CDEPermittedValue.objects.all():
            value.delete()

        importer = Importer()
        yaml_file = self._get_yaml_file()

        importer.load_yaml(yaml_file)
        importer.create_registry()
        assert importer.state == ImportState.SOUND


class FormTestCase(RDRFTestCase):

    def setUp(self):
        super(FormTestCase, self).setUp()
        self._reset_mongo()
        self.registry = Registry.objects.get(code='fh')
        self.state, created = State.objects.get_or_create(
            short_name="WA", name="Western Australia")

        self.state.save()
        self.create_sections()
        self.create_forms()
        self.working_group, created = WorkingGroup.objects.get_or_create(name="WA")
        self.working_group.save()

        self.patient = self.create_patient()

        self.address_type, created = AddressType.objects.get_or_create(pk=1)

        self.patient_address, created = PatientAddress.objects.get_or_create(
            address='1 Line St', address_type=self.address_type, suburb='Neverland', state=self.state, postcode='1111', patient=self.patient)
        self.patient_address.save()

        self.request_factory = RequestFactory()

    def _reset_mongo(self):
        self.client = MongoClient(settings.MONGOSERVER, settings.MONGOPORT)
        # delete any testing databases
        for db in self.client.database_names():
            if db.startswith("testing_"):
                print "deleting %s" % db
                self.client.drop_database(db)

        print "Testing Mongo Reset OK"

    def create_patient(self):
        p = Patient()
        p.consent = True
        p.name = "Harry"
        p.date_of_birth = datetime(1978, 6, 15)
        p.working_group = self.working_group
        p.save()
        p.rdrf_registry = [self.registry]
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
        form, created = RegistryForm.objects.get_or_create(name=name, registry=self.registry)
        form.name = name
        form.registry = self.registry
        form.sections = ",".join([section.code for section in sections])
        form.is_questionnaire = is_questionnnaire
        form.save()
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
        print str(form_data)
        request = self._create_request(self.simple_form, form_data)
        view = FormView()
        view.request = request
        # This switches off messaging , which requires request middleware which
        # doesn't exist in RequestFactory requests
        view.testing = True
        view.post(request, self.registry.code, self.simple_form.pk, self.patient.pk)

        mongo_query = {"django_id": self.patient.pk,
                       "django_model": self.patient.__class__.__name__}

        mongo_db = self.client["testing_" + self.registry.code]

        collection_name = "cdes"
        collection = mongo_db[collection_name]
        mongo_record = collection.find_one(mongo_query)

        print "*** MONGO RECORD = %s ***" % mongo_record

        assert "forms" in mongo_record, "Mongo record should have a forms key"
        assert isinstance(mongo_record["forms"], list)
        assert len(mongo_record["forms"]) == 1, "Expected one form"

        the_form = mongo_record['forms'][0]
        assert isinstance(the_form, dict), "form data should be a dictionary"
        assert "sections" in the_form, "A form should have a sections key"
        assert isinstance(the_form["sections"], list), "Sections should be in a list"
        # we've only written data for 2 sections
        assert len(the_form["sections"]) == 2, "expected 2 sections got %s" % len(the_form["sections"])

        assert form_value(self.simple_form.name, self.sectionA.code, "CDEName", mongo_record) == "Fred"
        assert form_value(self.simple_form.name, self.sectionA.code, "CDEAge", mongo_record) == 20
        assert form_value(self.simple_form.name, self.sectionB.code, "CDEHeight", mongo_record) == 1.73
        assert form_value(self.simple_form.name, self.sectionB.code, "CDEWeight", mongo_record) == 88.23



class LongitudinalTestCase(FormTestCase):

    def test_simple_form(self):
        mongo_db = self.client["testing_" + self.registry.code]
        super(LongitudinalTestCase, self).test_simple_form()
        # should have one snapshot
        collection = mongo_db["history"]
        record = collection.find_one({"_id": self.patient.pk})
        assert record is not None, "History should be filled in on save"
        assert "snapshots" in record, "history records should have a snaphots list"
        assert isinstance(record["snapshots"], list), "snapshots should be a list"
        for snapshot_dict in record["snapshots"]:
            assert isinstance(
                snapshot_dict, dict), "Snapshot should be a dict: %s" % type(snapshot_dict)
            assert "timestamp" in snapshot_dict, "snapshot dict should have  timestamp key"
            assert isinstance(snapshot_dict["timestamp"], type(
                u"")), "timestamp should be a string: got %s" % type(snapshot_dict["timestamp"])
            assert "record" in snapshot_dict, "snapshot dict should have key record"
        assert len(record["snapshots"]) == 1, "Length of snapshots should be 1 got : %s" % len(
            record["snapshots"])


class DeCamelcaseTestCase(TestCase):

    _EXPECTED_VALUE = "Your Condition"

    def test_decamelcase_first_lower(self):
        test_value = "yourCondition"
        self.assertEqual(de_camelcase(test_value), self._EXPECTED_VALUE)

    def test_decamelcase_first_upper(self):
        test_value = "YourCondition"
        self.assertEqual(de_camelcase(test_value), self._EXPECTED_VALUE)
