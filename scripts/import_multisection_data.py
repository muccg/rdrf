from registry.patients.models import Patient
from rdrf.models.definition.models import CDEPermittedValue
from rdrf.models.definition.models import CommonDataElement
from rdrf.models.definition.models import Registry
from django.db import transaction
from operator import itemgetter
import sys
import django
django.setup()


class MissingCodeError(Exception):
    pass


class Codes:
    FORM = "GeneticData"
    MULTISECTION = "FHMutationDetails"
    GENEVARIANT = "FHMutation"
    DESCRIPTION = "FHMutationDescription"
    PATHOGENICITY = "Pathogenicity"


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
        for row in sorted(rows, key=itemgetter('SectionIndex')):
            cde_dicts = []
            if row["GeneVariant"]:
                cde_dicts.append(self._make_cde_dict(Codes.GENEVARIANT,
                                                     row["GeneVariant"]))

            if row["Description"]:
                cde_dicts.append(self._make_cde_dict(Codes.DESCRIPTION,
                                                     row["Description"]))

            if row["Pathogenicity"]:
                cde_dicts.append(self._make_cde_dict(Codes.PATHOGENICITY,
                                                     row["Pathogenicity"]))

            items.append(cde_dicts)

        return items

    def _make_cde_dict(self, code, display_value):
        cde_model = CommonDataElement.objects.get(code=code)
        if cde_model.pv_group:
            # need to get the value code from  the display value provided
            try:
                value = self._get_pv_code(cde_model.pv_group,
                                          display_value)
            except MissingCodeError:
                error("Missing code for pvg %s display_value '%s'" % (cde_model.pv_group.code,
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


def error(msg):
    print("Error: %s" % msg)


def info(msg):
    print("Info: %s" % msg)


def existing_data(patient_model):
    return False


idmap_file = sys.argv[1]
csv_file = sys.argv[2]

fh_registry = Registry.objects.get(code="fh")

reader = Reader(csv_file)
reader.read()

idmap = build_idmap(idmap_file)

# we're updating just one multisection
field_expression = "$ms/%s/%s/items" % (Codes.FORM,
                                        Codes.MULTISECTION)

for patient_data in reader:
    rdrf_id = idmap.get(patient_data.old_id, None)
    if rdrf_id is None:
        error("Patient %s does not exist in mapping file" % patient_data.old_id)
        continue
    else:
        try:
            patient_model = Patient.objects.get(pk=rdrf_id)
            moniker = "%s\\%s" % (
                patient_data.old_id, rdrf_id)

            info("Found patient %s" % patient_model)

            info("Updating patient %s .." % moniker)

            try:
                with transaction.atomic():
                    patient_model.evaluate_field_expression(fh_registry,
                                                            field_expression,
                                                            value=patient_data.items)

                    info("Updated patient %s OK" % moniker)
            except Exception as ex:
                error("Updated failed for %s ( no change to this patient): %s" % (moniker, ex))

        except Patient.DoesNotExist:
            error("No patient with id %s - skipping" % rdrf_id)
