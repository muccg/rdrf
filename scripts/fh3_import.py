import django
django.setup()

import sys
from operator import itemgetter
import csv

from django.db import transaction

from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import CommonDataElement
from rdrf.models import CDEPermittedValue
from registry.patients.models import Patient


def error(msg):
    print("Error: %s" % msg)


def info(msg):
    print("Info: %s" % msg)

def blank_lines(n):
    for i in range(n):
        print("")
        


class FieldInfo:

    def __init__(self, registry_model, form_model, section_model, cde_model):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model
        self.is_multi = self.section_model.allow_multiple

    def __str__(self):
        return "%s/%s/%s/%s" % (self.registry_model.code,
                                self.form_model.name,
                                self.section_model.code,
                                self.cde_model.code)

    @property
    def field_expression(self):
        if not self.is_multi:
            fe = "%s/%s/%s" % (self.form_model.name,
                               self.section_model.code,
                               self.cde_model.code)
            return fe

    @property
    def is_range(self):
        return self.cde_model.pv_group is not None

    @property
    def in_multi(self):
        return self.section_model.allow_multiple

    def get_range_code(self, display_value):
        if not self.is_range:
            raise ValueError(
                "Field info is not a range: Can't look up value [%s]" % display_value)

        range_value_dicts = self.cde_model.pv_group.as_dict()["values"]
        
        for range_value_dict in range_value_dicts:
            # code is what needs to be stored in the db
            range_display_value = range_value_dict["value"]
            if display_value == range_display_value:
                return range_value_dict["code"]


    def should_apply(self, value):
        if self.is_range and value is None:
            # cell was empty
            return False

        return True


def build_id_map(map_file):
    id_map = {}
    with open(map_file) as mf:
        for line in mf.readlines():
            old_id, new_id = line.strip().split(",")
            id_map[old_id] = new_id
    return id_map


def build_field_map(registry_model, field_map_file):
    field_map = {}

    with open(field_map_file) as f:
        csvreader = csv.DictReader(f)
        rows = [row for row in csvreader][1:]

        for row in rows:
            fieldnum = row["FIELDNUM"]
            info("reading field %s" % fieldnum)
            form_name = row["FORM"]
            info("form name = %s" % form_name)
            section_name = row["SECTION"]
            info("section name = %s" % section_name)
            cde_name = row["CDE"]
            info("cde name = %s" % cde_name)

            try:
                form_model = RegistryForm.objects.get(registry=registry_model,
                                                      name=form_name)

                info("found registry form %s" % form_model)

                section_model = None

                for sec_model in form_model.section_models:
                    if sec_model.display_name == section_name:
                        section_model = sec_model
                        info("found section model %s" % section_model)
                        break

                cde_model = None

                for c_model in section_model.cde_models:
                    if c_model.name == cde_name:
                        cde_model = c_model
                        info("found cde_model %s" % cde_model)
                        break

                field_info = FieldInfo(registry_model,
                                       form_model,
                                       section_model,
                                       cde_model)

                info("created field info object")

                field_map[fieldnum] = field_info
            except Exception as ex:
                error("Bad field: fieldnum = %s error: %s" % (fieldnum,
                                                              ex))
                return None

    return field_map


def read_patients(csv_file):
    with open(csv_file) as f:
        csvreader = csv.DictReader(f)
        rows = [row for row in csvreader]
        return rows


class PatientUpdater:

    def __init__(self, registry_model, field_map, id_map, rows):
        self.registry_model = registry_model
        self.field_map = field_map
        self.id_map = id_map
        self.headers = rows[0]
        self.rows = rows[1:]
        self.field_map = field_map

    def _get_patient(self, row):
        old_id = row["1"]
        new_id = self.id_map.get(old_id, None)
        if new_id is None:
            error("Patient %s unmapped" % old_id)
            return None

        try:
            patient_model = Patient.objects.get(id=new_id)
            return patient_model
        except Patient.DoesNotExist:
            error("Patient %s/%s does not exist" % (old_id,
                                                    new_id))
            return None

    def _get_field_data(self, row):
        for column_index in range(1, self.last_column + 1):
            field_info = self._get_column_info(column_index)
            raw_value = row[column_index]
            yield field_info, raw_value

    def _get_column_info(self, column_index):
        return self.field_map[column_index]

    def _apply_field_expression(self, field_info, field_expression, patient_model, rdrf_value):
        if field_info.should_apply(rdrf_value):
            patient_model.evaluate_field_expression(self.registry_model,
                                                    field_expression,
                                                    value=rdrf_value)
        else:
            info("Not applying empty value for this field")
            

        

    def _get_rdrf_value(self, value, field_info):
        if field_info.is_range:
            info("getting rdrf value for range")
            return field_info.get_range_code(value)
        else:
            info("returning rdrf value for non-range")
            return value

    def update(self):
        for row in rows:
            blank_lines(1)
            patient_model = self._get_patient(row)
            if patient_model:
                info("starting update of patient %s" % patient_model)
                keys = sorted(row.keys())
                for column_key in keys:
                    if column_key != "1":
                        field_info = self.field_map.get(column_key, None)
                        if field_info is None:
                            error("No field info for column %s" % column_key)
                            continue
                        else:
                            info(
                                "found field info for column %s: %s" % (column_key,
                                                                        field_info))

                            raw_value = row[column_key]
                            info("found raw value: [%s]" % raw_value)
                            rdrf_value = self._get_rdrf_value(
                                raw_value, field_info)

                            field_expression = field_info.field_expression
                            

                            if not field_info.in_multi:
                                
                                self._apply_field_expression(field_info,
                                                             field_expression,
                                                             patient_model,
                                                             rdrf_value)
                            else:
                                info("dummy updating cde in mulisection %s --> %s" % (field_expression,
                                                                                      rdrf_value))
                                


if __name__ == '__main__':
    registry_model = Registry.objects.get(code='fh')
    field_map_file = sys.argv[1]
    idmap_file = sys.argv[2]
    csv_file = sys.argv[3]

    id_map = build_id_map(idmap_file)
    blank_lines(2)
    field_map = build_field_map(registry_model, field_map_file)


    if field_map is None:
        error("Field Map error - aborting")
        sys.exit(1)

    blank_lines(2)

    rows = read_patients(csv_file)

    patient_updater = PatientUpdater(registry_model, field_map, id_map, rows)
    patient_updater.update()
