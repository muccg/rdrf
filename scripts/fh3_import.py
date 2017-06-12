import django
django.setup()

import sys
from operator import itemgetter
import csv

from django.db import transaction

from rdrf.models import Registry
from rdrf.models import CommonDataElement
from rdrf.models import CDEPermittedValue

from registry.patients.models import Patient


class MissingCodeError(Exception):
    pass


class PatientData:

    def __init__(self, patient_id, items):
        self.old_id = patient_id
        self.items = items

    @property
    def fields(self):
        return []

class Reader:

    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.patient_data = []

    def read(self):
        patient_map = {}
        with open(self.csv_file) as f:
            csvreader = csv.DictReader(f)
            for row in csvreader:
                if row["PatientID"] in patient_map:
                    patient_map[row["PatientID"]].append(row)
                else:
                    patient_map[row["PatientID"]] = [row]

    def _make_cde_dict(self, code, display_value):
        cde_model = CommonDataElement.objects.get(code=code)
        if cde_model.pv_group:
            # need to get the value code from  the display value provided
            try:
                value = self._get_pv_code(cde_model.pv_group,
                                          display_value)
            except MissingCodeError:
                error(
                    "Missing code for pvg %s display_value '%s'" % (cde_model.pv_group.code,
                                                                    display_value))
                value = None

        else:
            value = display_value

        return {"code": code,
                "value": value}

    def _get_pv_code(self, pv_group, display_value):
        for pv in CDEPermittedValue.objects.filter(
                pv_group=pv_group).order_by('position'):
            if pv.value == display_value:
                return pv.code

        raise MissingCodeError()

    def __iter__(self):
        for data in self.patient_data:
            yield data


def build_idmap(mapfile):
    idmap = {}
    with open(mapfile) as mf:
        for line in mf.readlines():
            old_id, new_id = line.strip().split(",")
            idmap[old_id] = new_id
    return idmap


def build_field_map(registry_model,field_map_file):
    field_map = {}
    
    with open(field_map_file) as f:
        csvreader = csv.DictReader(f)
        for row in csvreader:
            fieldnum = row["FIELDNUM"]
            form_name = row["FORM"]
            section_name = row["SECTION"]
            cde_name = row["CDE"]

            try:
                form_model = RegistryForm.objects.get(registry=registry_model,
                                                      name=form_name)

                section_model = None

                for sec_model in form_model.section_models:
                    if sec_model.name == section_name:
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
            except Exception as ex:
                error("Bad field: fieldnum = %s error: %s" % (fieldnum,
                                                              ex))
    return field_map

                
                

            

            
            
            
            
    
    


def error(msg):
    print("Error: %s" % msg)


def info(msg):
    print("Info: %s" % msg)


def existing_data(patient_model):
    return False





# for patient_data in reader:
#     rdrf_id = idmap.get(patient_data.old_id, None)
#     if rdrf_id is None:
#         error("%s UNMAPPED" % patient_data.old_id)
#         continue
#     else:
#         try:
#             patient_model = Patient.objects.get(pk=rdrf_id)

#             for field_expression, value in patient_data.fields:
#                 try:
#                     with transaction.atomic():
#                         patient_model.evaluate_field_expression(fh_registry,
#                                                                 field_expression,
#                                                                 value=value)

#                         info("%s %s OK" % (rdrf_id, field_expression))
#                 except Exception as ex:
#                     error("%s %s FAIL: %s" % (rdrf_id, field_expression, ex))

#         except Patient.DoesNotExist:
#             error("%s DOES NOT EXIST" % rdrf_id)




class FieldInfo:
    def __init__(self, registry_model, field_map):
        self.registry_model = registry_model
        self.field_map = field_map
        self.column_index = None
        self.form_model = None
        self.section_model = None
        self.cde_model = None
        self.field_expression = None
        self._load()



class PatientUpdater:
    def __init__(self, registry_model, field_map, id_map, rows, logger):
        self.registry_model = registry_model
        self.field_map = field_map
        self.headers = rows[0]
        self.rows = rows[1:]
        self.id_map = id_map
        self.field_map = self._create_field_map()

    def _get_patient(self, row):
        old_id = row[0]
        new_id = self.idmap.get(old_id, None)
        if new_id is None:
            error("Patient %s unmapped" % old_id)
            return None

        try:
            patient_model = Patient.objects.get(id=new_id)
            return patient_model
        except Patient.DoesNotExist:
            self.logger.error("Patient %s/%s does not exist" % (old_id,
                                                                new_id))
            return None

    def _get_field_data(self, row):
        for column_index in range(1, self.last_column + 1):
            field_info = self._get_column_info(column_index)
            raw_value = row[column_index]
            yield field_info, raw_value

    def _get_column_info(self, column_index):
        field_info = FieldInfo()
        return field_info

    def _apply_field_expression(self, field_expression, patient_model, rdrf_value):
        pass

    def _get_rdrf_value(self, value, field_info):
        return None
    
    def update(self):
        for row in rows:
            patient_model = self.get_patient(row)
            if patient_model:
                for field_info, value in get_field_columns(row):
                    rdrf_value = sef._get_rdrf_value(value, field_info)
                    self._apply_field_expression(field_info.field_expression, patient_model, rdrf_value)
        
        
if __name__ == '__main__':
    registry_model = Registry.objects.get(code='fh')
    field_map_file = sys.argv[1]
    idmap_file = sys.argv[2]
    csv_file = sys.argv[3]

    id_map = build_id_map(idmap_file)
    field_map = build_field_map(registry_model, field_map_file)
    reader = Reader(csv_file)
    rows = reader.read()

    patient_updater = PatientUpdater(registry_model, id_map, field_map, rows)
    patient_updater.update()
    
    
