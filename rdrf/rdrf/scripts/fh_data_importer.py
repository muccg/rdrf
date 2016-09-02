from django.db import transaction
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement


from registry.patients.models import Patient
import csv
from string import strip


class DataDictionaryFile:
    ROW_DELIMITER = '\t'
    FIELD_NUM_COLUMN = 1
    FORM_NAME_COLUMN = 6
    SECTION_NAME_COLUMN = 9
    CDE_NAME_COLUMN = 10


class DataImporterError(Exception):
    pass


class RowWrapper(object):

    def _init__(self, registry_model, cde_field_num_map, row_dict):
        self.registry_model = registry_model
        self.cde_field_num_map = cde_field_num_map
        self.row_dict = row_dict

    def __getitem__(self, tuple_or_string):
        if type(tuple_or_string) is tuple:
            form_model, section_model, cde_model = tuple_or_string
            key = form_model.name + "/" + section_model.code + "/" + cde_model.code
            field_num = self.cde_field_num_map.get(key, None)
        else:
            field_num = self.cde_field_num_map.get(tuple_or_string, None)

        if field_num is None:
            raise DataImporterError("No fieldnum for %s" % tuple_or_string)

        try:
            value = self.row_dict[field_num]
        except KeyError:
            raise DataImporterError(
                "fieldnum %s not in row %s" % (field_num, self.row_dict))
        # return value suitable for db or mongo
        if form_model:
            # need to ensure display values are converted to codes
            transformed_value = self._get_transformed_value(
                form_model, section_model, cde_model, value)
            return transformed_value
        else:
            # demographics / consents etc
            return value

    def _get_transformed_value(self, form_model, section_model, cde_model, value):
        return value  # todo


class DataImporter(object):

    def __init__(self, registry_code, data_dictionary, import_file):
        self.registry_code = registry_code
        self.registry_model = Registry.objects.get(code=self.registry_code)
        self.data_dictionary = data_dictionary
        self.import_file = import_file
        self.created_patient_ids = []
        self.field_map = self._build_map()

    def _build_map(self):
        # map cde codes to field nums: field nums are unique ids of
        # form/section/cdes  or consents or demographic fields
        with open(self.data_dictionary) as dd:
            lines = map(strip, dd.readlines())[1:]  # skip header
            columns = lines.split(DataDictionaryFile.ROW_DELIMITER)
            for line in lines:
                field_num = columns[DataDictionaryFile.FIELD_NUM_COLUMN]
                form_name = columns[DataDictionaryFile.FORM_NAME_COLUMN]
                section_name = columns[DataDictionaryFile.SECTION_NAME_COLUMN]
                cde_name = columns[DataDictionaryFile.CDE_NAME_COLUMN]

                try:
                    form_model = RegistryForm.objects.get(name=form_name,
                                                          registry=self.registry_model)

                except RegistryForm.DoesNotExist:
                    pass

    def run(self):
        try:
            with transaction.atomic():
                self._run()
        except Exception, ex:
            self._rollback_mongo()

    def _rollback_mongo(self):
        print "TODO"

    def _create_patient_model(self, row):
        patient = Patient()
        patient.family_name = row["family_name"]
        patient.given_names = row["given_names"]
        patient.date_of_birth = row["date_of_birth"]
        patient.sex = row["sex"]

    def _run(self):
        for row in self._get_rows():
            # row is RowWrapper
            patient_model = self._create_patient_model(row)
            patient_model.save()

            for form_model in self.registry_model.forms:

                form_data = self._get_form_data(form_model, row)
                try:
                    self.submit_form_data(patient_model, form_model, form_data)
                except FormError, fex:
                    print "Error submitting form"

    def _get_rows(self):
        with open(self.import_file, "rb") as csv_file:
            reader = csv.CSVReader(csv_file)
            for row_dict in reader:
                wrapped_row = RowWrapper()
                yield wrapped_row

    def _get_form_data(self, form_model, row):
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                for cde_model in section_model.cde_models:

    def _get_form_key_and_data(self, form_model, section_model, cde_model, row):
        field_key = None
        field_value = row[(form_model, section_model, cde_model)]
        return field_key, field_value
