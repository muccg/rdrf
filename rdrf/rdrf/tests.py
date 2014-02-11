from django.test import TestCase
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











