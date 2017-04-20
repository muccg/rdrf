import django
django.setup()

import sys
from operator import itemgetter
from rdrf.models import Registry
from registry.patients.models import Patient

class Codes:
    FORM = ""
    MULTISECTION = "hh"
    GENEVARIANT = "aa"
    DESCRIPTION = "bb"
    PATHOGENICITY = "aaa"

class PatientData:
    def __init__(self, patient_id, items):
        self.old_id = patient_id
        self.items = items

class Reader:
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.patient_data = []
        
    def read(self):
        import csv
        patient_map = {}
        with open(self.csv_file) as f:
            csvreader = csv.DictReader(f)
            for row in csvreader:
                if row["PatientID"] in patient_map:
                    patient_map[row["PatientID"]].append(row)
                else:
                    patient_map[row["PatientID"]] = [row]
        for patient_id in patient_map:
            items = self._make_items(patient_id, patient_map[patient_id])
            self.patient_data.append(PatientData(patient_id, items))


    def _make_items(self, patient_id, rows):
        items = []
        for row in sorted(rows,key=itemgetter('SectionIndex')):
            cde_dicts = []
            cde_dicts.append(self._make_cde_dict(code=Codes.GENEVARIANT,
                                                 value=row["GeneVariant"]))

            cde_dicts.append(self._make_cde_dict(code=Codes.DESCRIPTION,
                                                 value=row["Description"]))

            cde_dicts.append(self._make_cde_dict(code=Codes.PATHOGENICITY,
                                                 value=row["Pathogenicity"]))

            items.append(cde_dicts)

        return items

    def _make_cde_dict(self, code, value):
        return {"code": code,
                "value": value}
    
    def __iter__(self):
        for data in self.patient_data:
            yield data
           
def buildid_map(mapfile):
    idmap = {}
    with open(mapfile) as mf:
        for line in mf.readlines():
            old_id, new_id = line.strip().split(",")
            idmap[old_id] = new_id
    return idmap

def error(msg):
    print("Error: %s" % msg)

def info(msg):
    print("Info: %s" % msg)

def existing_data(patient_model):
    return False 
    
    
idmap_file = sys.argv[1]
spreadsheet_file = sys.argv[2]

fh_registry = Registry.objects.get(code="fh")

reader = SpreadSheetReader(spreadsheet_file)
reader.read()

idmap = build_idmap(idmap_file)

# we're updating just one multisection
field_expression = "$op/%s/%s/items" % (Codes.FORM,
                                        Codes.MULTISECTION)

for patient_data in reader:
    rdrf_id = idmap.get(patient_data.old_id, None)
    if rdrf_id is None:
        error("Patient %s does not exist in mapping file" % patient_data.old_id)
    else:
        try:
            patient_model = Patient.objects.get(pk=rdrf_id)
            if existing_data(patient_model):
                error("Existing data for %s/%s" % (patient_data.old_id,
                                                   rdrf_id))
                continue

            patient_model.evaluate_field_expression(fh_registry,
                                                    field_expression,
                                                    value=patient_data.items)
            
            info("Updated patient %s/%s" % (patient_data.old_id,
                                            rdrf_id))
            
        except Patient.DoesNotExist:
            error("No patient with id %s" % rdrf_id)
        
            

