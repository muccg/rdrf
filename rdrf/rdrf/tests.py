from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.management import call_command
from rdrf.exporter import Exporter, ExportType
from rdrf.importer import Importer, ImportState, RegistryImportError
from rdrf.models import *
from rdrf.form_view import FormView
from registry.patients.models import Patient, PatientRegistry
from registry.groups.models import WorkingGroup
from registry.patients.models import State, Country
from datetime import datetime

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
        key = "id_" + settings.FORM_SECTION_DELIMITER.join([self.form.name, section.code, cde_code])
        self.data.update({key: value})


    def __getattr__(self, item):
        if item in self.section_codes:
            section = Section.objects.get(code=item)
            section_filler = SectionFiller(self, section)
            return section_filler






class RDRFTestCase(TestCase):
    fixtures = ['testing_auth.json', 'testing_users.json', 'testing_rdrf.json']

class ExporterTestCase(RDRFTestCase):

    def test_export_registry_only(self):

        def test_key(key, data):
            assert key in data, "%s not in yaml export" % key

        def test_keys(keys, data):
            for key in keys:
                test_key(key, data)

        self.registry = Registry.objects.get(code='fh')
        self.exporter = Exporter(self.registry)
        yaml_data = self.exporter.export_yaml()
        import yaml
        with open("/tmp/test.yaml","w") as f:
            f.write(yaml_data)


        with open("/tmp/test.yaml") as f:
            data = yaml.load(f)

        test_key('EXPORT_TYPE', data)
        test_key('RDRF_VERSION',data)
        assert data["EXPORT_TYPE"] == ExportType.REGISTRY_ONLY
        assert 'cdes' not  in data, "Registry only export shouldn't have cdes key"
        assert data['code'] == 'fh',"Reg code fh not in export"
        test_key('forms', data)
        for form_map in data['forms']:
            test_keys(['is_questionnaire', 'name', 'sections'], form_map)
            for section_map in form_map['sections']:
                test_keys(['code','display_name','elements','allow_multiple','extra'], section_map)



class ImporterTestCase(RDRFTestCase):

    def _get_yaml_file(self):
        return os.path.join(os.path.dirname(__file__),'fixtures','exported_fh_registry.yaml')

    def test_importer(self):
        # first delete the FH registry
        fh_reg = Registry.objects.get(code='fh')
        fh_reg.delete()
        importer = Importer()
        yaml_file = self._get_yaml_file()

        importer.load_yaml(yaml_file)
        importer.create_registry()
        assert importer.state == ImportState.IMPORTED

    def test_soundness(self):
        # delete CDEHeight whis used in FH and soundness check fails

        cde_height = CommonDataElement.objects.get(code='CDEHeight')
        cde_height.delete()

        importer = Importer()
        importer.check_soundness = True

        importer.load_yaml(self._get_yaml_file())

        self.assertRaises(RegistryImportError,importer.create_registry)


class FormTestCase(RDRFTestCase):
    def setUp(self):
        super(FormTestCase, self).setUp()
        self.registry = Registry.objects.get(code='fh')
        self.country, created = Country.objects.get_or_create(name="Australia")
        self.country.save()
        self.state, created = State.objects.get_or_create(short_name="WA",name="Western Australia",
                                                          country=self.country)

        self.state.save()
        self.create_sections()
        self.create_forms()
        self.working_group, created = WorkingGroup.objects.get_or_create(name="WA")
        self.working_group.save()
        self.patient = self.create_patient()
        self.request_factory = RequestFactory()

    def create_patient(self):
        p = Patient()
        p.name = "Harry"
        p.date_of_birth = datetime(1978, 6, 15)
        p.working_group = self.working_group
        p.state = self.state
        p.postcode = "6112" # Le Armadale
        p.save()
        patient_registry, created = PatientRegistry.objects.get_or_create(patient=p, rdrf_registry=self.registry)

        patient_registry.save()
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
        form, created = RegistryForm.objects.get_or_create(name=name,registry=self.registry)
        form.name = name
        form.registry = self.registry
        form.sections = ",".join([ section.code for section in sections])
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
        request.user = User.objects.get(username="curator")
        return request



    def create_sections(self):
        # "simple" sections ( no files or multi-allowed sections
        self.sectionA = self.create_section("sectionA","Simple Section A",["CDEName","CDEAge"])
        self.sectionB = self.create_section("sectionB", "Simple Section B", ["CDEHeight", "CDEWeight"])
        # A multi allowed section with no file cdes
        self.sectionC = self.create_section("sectionC", "MultiSection No Files Section C", ["CDEName", "CDEAge"],True)
        # A multi allowed section with a file CDE
        #self.sectionD = self.create_section("sectionD", "MultiSection With Files D", ["CDEName", ""])


    def _create_form_item(self,form, section, cde_code, value):
        key = "id_" + settings.FORM_SECTION_DELIMITER.join([form.name, section.code, cde_code])
        return { key: value}

    def test_simple_form(self):
        ff = FormFiller(self.simple_form)
        ff.sectionA.CDEName = "Fred"
        ff.sectionA.CDEAge = 20
        ff.sectionB.CDEHeight = 1.73
        ff.sectionB.CDEWeight = 88.23
        form_data = ff.data
        print str(form_data)
        request = self._create_request(self.simple_form, form_data)
        view = FormView()
        view.post(request, self.registry.code, self.simple_form.pk, self.patient.pk )
























