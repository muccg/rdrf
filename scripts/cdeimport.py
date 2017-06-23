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
    print("ERROR: %s" % msg)


def info(msg):
    print("INFO: %s" % msg)

def blank_lines(n):
    for i in range(n):
        print("")

def convert_american_date(american_date_string):
    if not american_date_string:
        return None
    month, day, year = american_date_string.split("/")
    return "%s-%s-%s" % (day, month, year)


def convert_australian_date(aus_date_string):
    if not aus_date_string:
        return None

    day, month, year = aus_date_string.split("/")
    return "%s-%s-%s" % (day, month, year)


converters = {
    53: convert_american_date,
    102: convert_australian_date,
}


class FieldInfo:

    def __init__(self, registry_model, form_model, section_model, cde_model):
        self.registry_model = registry_model
        self.form_model = form_model
        self.section_model = section_model
        self.cde_model = cde_model
        self.is_multi = self.section_model.allow_multiple
        self.field_num = None

    def __str__(self):
        return "[%s] %s/%s/%s/%s" % (self.field_num,
                                     self.registry_model.code,
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

        if self.cde_model.allow_multiple:
            # multiselet checkboxes use this feature
            # values are peristed as lists of codes not single values
            return self._get_multiple_code_list(display_value)
        

        range_value_dicts = self.cde_model.pv_group.as_dict()["values"]
        
        for range_value_dict in range_value_dicts:
            # code is what needs to be stored in the db
            range_display_value = range_value_dict["value"]
            if display_value == range_display_value:
                return range_value_dict["code"]

        return None

    def _get_multiple_code_list(self, desc_csv):
        if not desc_csv:
            return []
        # we need to find  the corresponding codes which are then stored as a list
        try:
            descs = desc_csv.split(",")
        except Exception as ex:
            error("multiple code list [%s] could not be split: %s" % (desc_csv,
                                                                      ex))
            return []
        
        codes = []
        pv_group =self.cde_model.pv_group
        values_dict = pv_group.as_dict()
        for desc in descs:
            for value_dict in values_dict["values"]:
                if desc == value_dict["value"]:
                    code = value_dict["code"]
                    codes.append(code)

        return codes


    def should_apply(self, value):
        if self.is_range:
            # out of bound values result in None
            return value is not None

        return True

    @property
    def datatype(self):
        return self.cde_model.datatype.lower().strip()

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
            form_name = row["FORM"]
            section_name = row["SECTION"]
            cde_name = row["CDE"]
            form_model = RegistryForm.objects.get(registry=registry_model,
                                                      name=form_name)

            section_model = None

            for sec_model in form_model.section_models:
                if sec_model.display_name == section_name:
                    section_model = sec_model
                    break

            cde_model = None

            for c_model in section_model.cde_models:
                if c_model.name == cde_name:
                    cde_model = c_model
                    break

            field_info = FieldInfo(registry_model,
                                       form_model,
                                       section_model,
                                       cde_model)

            field_map[fieldnum] = field_info
            field_info.field_num = fieldnum

            info("fieldmap %s --> %s" % (fieldnum, field_info))
                
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
        self.num_rows = len(self.rows)
        self.num_updated = 0
        self.num_rollbacks = 0
        self.num_missing = 0

    def print_stats(self):
        info("Rows:      %s" % self.num_rows)
        info("Updates:   %s" % self.num_updated)
        info("Rollbacks: %s" % self.num_rollbacks)
        info("Missing:   %s" % self.num_missing)

    def _get_patient(self, row):
        old_id = row["1"]
        new_id = self.id_map.get(old_id, None)
        if new_id is None:
            return None, old_id

        try:
            patient_model = Patient.objects.get(id=new_id)
            return patient_model, old_id
        except Patient.DoesNotExist:
            error("MISSING %s/%s" % (old_id,
                                     new_id))
            return None, old_id

    def _get_column_info(self, column_index):
        return self.field_map[column_index]

    def _apply_field_expression(self, field_info, field_expression, patient_model, rdrf_value):
        if field_info.should_apply(rdrf_value):
            patient_model.evaluate_field_expression(self.registry_model,
                                                    field_expression,
                                                    value=rdrf_value)
        
    def _get_rdrf_value(self, value, field_info):
        if field_info.is_range:
            return field_info.get_range_code(value)
        else:
            converter = self._get_converter_func(field_info)
            if converter is not None:
                return converter(value)

            if field_info.datatype == "float":
                try:
                    return float(value)
                except:
                    if value != "":
                        info("%s error converting [%s] to float - returning None" % (field_info,
                                                                                 value))
                    return None
            elif field_info.datatype == "integer":
                try:
                    return int(value)
                except:
                    if value != "":
                        info("%s error converting [%s] to integer - returning None" % (field_info,value))
                    return None
            elif field_info.datatype == "date":
                return value
            else:
                return value

    def _get_converter_func(self, field_info):
        field_num = int(field_info.field_num)
        converter = converters.get(field_num, None)
        return converter

    def update(self):
        for row in self.rows:
            blank_lines(1)
            patient_model, old_id = self._get_patient(row)
            if patient_model:
                with transaction.atomic():
                    try:
                        info("Updating %s/%s ..." % (old_id, patient_model.pk))
                        self._update_patient(old_id,
                                             patient_model,
                                             row)

                        self.num_updated += 1
                        info("Updated patient %s/%s successfully" % (old_id,
                                                                     patient_model.pk))
                    except Exception as ex:
                        self.num_rollbacks += 1
                        error("Rollback on patient %s: %s" % (patient_model.pk,
                                                              ex))
            else:
                self.num_missing += 1
                error("MISSING %s" % old_id)

    def _update_patient(self, old_id, patient_model, row):
        keys = sorted(row.keys())
        for column_key in keys:
            if column_key != "1":
                field_info = self.field_map.get(column_key, None)
                if field_info is None:
                    error("No field info for column %s" % column_key)
                    continue
                else:
                    # some date fields had spaces at front
                    raw_value = row[column_key].strip()
                    rdrf_value = self._get_rdrf_value(raw_value, field_info)
                    field_expression = field_info.field_expression
                    if not field_info.in_multi:
                        self._apply_field_expression(field_info,
                                                     field_expression,
                                                     patient_model,
                                                     rdrf_value)            
                    else:
                        self._update_multisection(field_info,
                                                  rdrf_value,
                                                  patient_model)

    def _update_multisection(self, field_info, rdrf_value, patient_model):
        # assumption from sheet is that we are updating the 1st item of the multisection
        # if none exists, we create the multisection item

        if field_info.should_apply(rdrf_value):

            # update the 1st item
    
            field_expression = "poke/%s/%s/1/%s" % (field_info.form_model.name,
                                                    field_info.section_model.code,
                                                    field_info.cde_model.code)

            patient_model.evaluate_field_expression(self.registry_model,
                                                    field_expression,
                                                    value=rdrf_value)
        else:
            if rdrf_value is not None:
                info("will not update multisection %s with bad value [%s]" % (field_info,
                                                                              rdrf_value))
def usage():
    print("usage: python cdeimport.py <registry code> <field map file> <id map file> <data file csv>")

if __name__ == '__main__':
    try:
        registry_code = sys.argv[1]
        field_map_file = sys.argv[2]
        idmap_file = sys.argv[3]
        csv_file = sys.argv[4]
    except IndexError:
        usage()
        sys.exit(1)

    try:
        registry_model = Registry.objects.get(code=registry_code)
    except Registry.DoesNotExist:
        error("No registry loaded with code %s" % registry_code)
        sys.exit(1)

    try:
        id_map = build_id_map(idmap_file)
    except Exception as ex:
        error("Could not load id map: %s" % ex)
        sys.exit(1)
    
    blank_lines(2)

    try:
        field_map = build_field_map(registry_model, field_map_file)
    except Exception as ex:
        error("Could not build field map: %s" % ex)
        sys.exit(1)
        
    blank_lines(2)
    
    try:
        rows = read_patients(csv_file)
    except Exception as ex:
        error("Could not load data file: %s" % ex)
        sys.exit(1)

    try:
        patient_updater = PatientUpdater(registry_model, field_map, id_map, rows)
    except Exception as ex:
        error("Could not create updater: %s" % ex)
        sys.exit(1)

    
    info("RUN STARTED")
    try:
        patient_updater.update()
        info("STATS:")
        patient_updater.print_stats()
        info("RUN FINISHED")
    except Exception as ex:
        error("Unexpected error during run: %s" % ex)
        sys.exit(1)
