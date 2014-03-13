from django.test import TestCase, RequestFactory
from django.core.management import call_command
from rdrf.exporter import Exporter, ExportType
from rdrf.importer import Importer, ImportState, RegistryImportError
from rdrf.models import *
import os

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
        self.create_test_sections()
        self.create_test_forms()

    def create_section(self, code, display_name, elements, allow_multiple=False, extra=1):
        section, created = Section.objects.get_or_create(code=code)
        section.display_name = display_name
        section.elements = ",".join(elements)
        section.allow_multiple = allow_multiple
        section.extra = extra
        section.save()
        return section

    def create_form(self, name, sections, is_questionnnaire=False):
        form, created = RegistryForm.get_or_create(name=name,registry=self.registry)
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

    def simulate_filling_in_form(self, form, form_data):
        # return a dictionary representing what
        pass

    def create_sections(self):
        # "simple" sections ( no files or multi-allowed sections
        self.sectionA = self.create_section("sectionA","Simple Section A",["CDEName","CDEAge"])
        self.sectionB = self.create_section("sectionB", "Simple Section B", ["CDEHeight", "CDEWeight"])
        # A multi allowed section with no file cdes
        self.sectionC = self.create_section("sectionC", "MultiSection No Files Section C", ["CDEName", "CDEAge"],True)
        # A multi allowed section with a file CDE
        #self.sectionD = self.create_section("sectionD", "MultiSection With Files D", ["CDEName", ""])





















