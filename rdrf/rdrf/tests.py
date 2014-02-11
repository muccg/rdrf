from django.test import TestCase
from django.core.management import call_command
from rdrf.exporter import Exporter, ExportType
from rdrf.models import *


class ExporterTestCase(TestCase):
    fixtures = ['testing_auth.json', 'testing_users.json', 'testing_rdrf.json']

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










