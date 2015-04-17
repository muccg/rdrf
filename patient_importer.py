import sys
import json
from rdrf.models import Registry

from migration_transforms import *


class MigrationError(Exception):
    pass


class BadValueError(MigrationError):
    pass


class PatientImporter(object):
    def __init__(self, target_registry_code, src_system, migration_map_file, dump_dir):
        self.src_system = src_system  # eg sma or dmd
        self._registry = Registry.objects.get(code=target_registry_code)
        self._dump_dir = dump_dir
        self._data = []
        self._log_file = "%s_patient_import.log" % target_registry_code
        self._log = None
        self._migration_map = self._load_migration_map(migration_map_file)

    # public interface

    def run(self):
        self._log = open(self.log_file, "w")
        self._create_working_groups()
        for old_patient_id in self._old_patient_ids():
            rdrf_patient = self._create_rdrf_patient(old_patient_id) # demographics
            rdrf_patient.save()  # now have primary key

            self._create_relationships(rdrf_patient, old_patient_id) # working groups, linkages

            for form_model in self._registry.forms:
                for section_model in form_model.section_models:
                    if not section_model.allow_multiple:
                        for cde_model in section_model.cde_models:
                            self._save_in_mongo(rdrf_patient, old_patient_id, form_model, section_model, cde_model)

                    else:
                        # handle multisection ..
                        pass

    # private

    def _create_rdrf_patient(self, old_patient_id):
        pass


    def _load_migration_map_file(self, map_file):
        with open(map_file) as f:
            for line in f.readlines():
                pass

    def _old_patient_ids(self):
        yield None

    def _create_relationships(self):
        pass

    def _load_dumpfiles(self):
        for dump_file in os.listdir(self._dump_dir):
            self._load_dumpfile(dump_file)

    def _load_dumpfile(self):
        with open(self._dumpfile) as dump_file:
            self._data.extend(json.load(dump_file))

    def _save_in_mongo(self, rdrf_patient_model, old_patient_id, form_model, section_model, cde_model):
        old_model_name, old_field_name = self._get_old_name(form_model, section_model, cde_model) # useful?
        old_value = self._get_old_data_value(old_patient_id, old_model_name, old_field_name)
        transform_func = self._get_transform_func(old_data_name, form_model, section_model, cde_model)
        if transform_func:
            new_value = transform_func(old_value)
        else:
            new_value = old_value

        rdrf_patient_model.set_form_value(self._registry.code, form_model.name, section_model.code, cde_model.code, new_value)

    def _get_old_name(self, form_model, section_model, cde_model):
        # a model , field name pair
        return self._migration_map[form_model.name][section_model.code][cde_model.code]

    def _get_old_data_value(self, old_patient_id, old_model_name, old_field_name):
        # need to navigate ?
        pass



    def _get_old_name(self, form_model, section_model, cde_model):
        return "???"

    def _get_old_data_value(self, old_patient_id, old_data_name):
        return None

    def _get_transform_func(self, old_data_name, form_model, section_model, cde_model):
        return lambda value: value

if __name__ == '__main__':
    src_system = sys.argv[1]
    dump_dir = sys.argv[2]
    target_registry_code = sys.argv[3]
    migration_map_file = sys.argv[4]
    data_migrator = PatientImporter(target_registry_code, src_system, migration_map_file, dump_dir)
    data_migrator.load_data()
    importer.run()