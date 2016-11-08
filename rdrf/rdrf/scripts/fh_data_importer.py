from django.db import transaction
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement
from rdrf.utils import form_key
from rdrf.form_view import FormView
from django.test import RequestFactory

from registry.patients.models import Patient
from registry.groups.models import CustomUser

import csv
from string import strip
import openpyxl as xl
import os


PATIENT_ID_FIELDNUM = 1

class DataDictionarySheet:
    FIELD_NUM_COLUMN = 1
    FORM_NAME_COLUMN = 6
    SECTION_NAME_COLUMN = 9
    CDE_NAME_COLUMN = 10


class ImporterError(Exception):
    pass

class FieldNumNotFound(ImporterError):
    pass


class FieldType:
    CDE = 1
    DEMOGRAPHICS = 2
    PEDIGREE_FORM = 3
    CONSENT = 4

    

class SpreadsheetImporter(object):
    # rewriting importer
    # as we need to link relatives to index patients
    # so we do two passes
    # also FH introduced form groups
    # we need to be aware of them
    
    def __init__(self, registry_model, import_spreadsheet_filepath, datadictionary_sheetname):
        self.registry_model = registry_model
        self.import_spreadsheet_filepath = import_spreadsheet_filepath
        self.datadictionary_sheetname = datadictionary_sheetname
        self.datadictionary_sheet = None
        self.indexes = []
        self.relatives = []
        self.family_linkage_map = {}
        self.index_patient_map = {}
        self.field_map = {}
        self.id_map = {}
        self.workbook = self._load_workbook()
        self._build_field_map()


    def _load_workbook(self):
        if not os.path.exists(self.import_spreadsheet_filepath):
            raise ImportError("Spreadsheet file %s does not exist" %
                            self.import_spreadsheet_filepath)
        
        try:
            self.workbook = xl.load_workbook(self.import_spreadsheet_filepath)
        except Exception, ex:
            raise ImporterError("Could not load Import spreadsheet: %s",
                                ex)

    def _build_field_map(self):
        # map RDRF "fields" to fieldnums in the spreadsheet
        d = {}
        d["patient_id"] = PATIENT_ID_FIELDNUM
        
        sheet = self.datadictionary_sheet
        finished = False
        row_num = 3 # fields start here
        
        while not finished:
            field_num = sheet.cell(row=row_num, column=DataDictionary.FIELD_NUM_COLUMN)
            
            if not field_num:
                finished = True
            else:
                form_name = sheet.cell(row=row_num, column=DataDictionary.FORM_NAME_COLUMN)
                section_name = sheet.cell(row=row_num, column=DataDictionary.SECTION_NAME_COLUMN)
                cde_name = sheet.cell(row=row_num, column=DataDictionary.CDE_NAME_COLUMN)
                key = (form_name, section_name, cde_name)
                
                d[key] = field_num

                row_num += 1
        return d
    

    def _get_field_num(self, key):
        if type(key) is tuple:
            form_model, section_model, cde_model = key
            form_name = form_model.name
            section_name = section_model.display_name
            cde_name = cde_model.name

            k = (form_name, section_name, cde_name)
            if k in self.field_map:
                return self.field_map[k]
            else:
                msg = "%s/%s/%s" % (form_name, section_name, cde_name)
                raise FieldNumNotFound(msg)
        else:
            # string key
            if key in self.field_map:
                return self.field_map[key]
            else:
                raise FieldNumNotFound(key)

    def run(self, rows):
        for row in rows:
            if self.is_index(row):
                self.indexes.append(row)
            elif self.is_relative(row):
                self.relatives.append(row)

        self._create_indexes()
        self._create_relatives()

    def is_index(self, row):
        return False

    def _is_relative(self, row):
        return False

    

    def _create_indexes(self):
        for row in self.indexes:
            index_patient = self._import_patient(row)
            external_id = self._get_external_id(row)
            self._update_id_map(external_id, index_patient.pk)

    def _update_id_map(self, external_id, rdrf_id):
        if external_id in self.id_map:
            raise ImportError("Dupe ID?")
        else:
            self.id_map[external_id] = rdrf_id
            

    def _create_relatives(self):
        for row in self.relatives:
            patient = self._create_minimal_patient(row)
            external_id = self._get_external_id(row)
            self._import_demographics_data(patient, row)
            for form_model in self.form_models:
                self._import_clinical_form(form_model, patient, row)

            self._update_id_map(external_id, patient.pk)

            index_patient = self._get_index_patient(row)
            self._add_relative(index_patient, patient)
            


    def _import_patient(self, row):
        patient = self._create_minimal_patient(row)
        self._import_demographics_data(patient, row)
        self._import_pedigree_data(patient, row)
        # ensure we import data into the correct context
        
        for context_model, form_model in self.get_forms_and_contexts():
            self._import_clinical_form(form_model, patient, context_model, row)

        return patient

    def _get_forms_and_contexts(self, patient_model):
        # get forms in fixed groups
        results = []
        for context_form_group in self.registry_model.context_form_groups:
            if context_form_group.is_default and context_form_group.type == "F":
                try:
                    context_model = RDRFContext.objects.get(object_id=patient_model.pk,
                                                        registry=self.registry_model,
                                                        context_form_group=context_form_group)
                except RDRFContext.DoesNotExist:
                    # should not happen as contexts for fixed groups created when patient craeted
                    pass

                except RDRFContext.MultipleObjectsReturned:
                    # eek
                    pass

                for form_model in context_form_group.form_models:
                    results.append((context_model, form_model))
        return results

    def _import_clinical_form(self, form_model, patient_model, context_model, row):
        field_updates = []
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                # 1st data import sheet does not contain any multisections as is 1 row per patient
                for cde_model in section_model.cde_models:
                    if self.included(form_model, section_model, cde_model):
                        field_num = self._get_field_num(form_model, section_model, cde_model)
                        field_value = self._get_field_value(row, field_num)
                        field_expression = self._get_field_expression(patient_model, form_model, section_model, cde_model)
                        field_updates.append((field_expression, field_value))

        patient_model.update_field_expressions(self.registry_model,field_updates)

    def cde_included(self, form_model, section_model, cde_model):
        model_tuple = (form_model, section_model, cde_model)
        return model_tuple in self.field_map

    def _get_field_expression(self, patient_model, form_model, section_model, cde_model):
        
        return expresssion 


class RowWrapper(object):

    def _init__(self, registry_model, cde_field_num_map, row_dict):
        self.registry_model = registry_model
        self.cde_field_num_map = cde_field_num_map
        self.row_dict = row_dict

    def __getitem__(self, tuple_or_string):
        form_model = section_model = cde_model = None
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
        self.request_factory = RequestFactory()
        self.admin_user = CustomUser.objects.get(username="admin")

    def _build_map(self):
        # map cde codes to field nums: field nums are unique ids of
        # form/section/cdes  or consents or demographic fields
        field_map = {}
        with open(self.data_dictionary) as dd:
            lines = map(strip, dd.readlines())[1:]  # skip header
            columns = lines.split(DataDictionaryFile.ROW_DELIMITER)
            for line in lines:
                field_num = columns[DataDictionaryFile.FIELD_NUM_COLUMN]
                spec = self._get_form_section_cde(columns)
                if type(spec) is tuple:
                    form_model, section_model, cde_model = spec
                    field_map[(FieldType.CDE, form_model, section_model, cde_model)] = field_num
                else:
                    # field is demographic or consent
                    form_name = columns[DataDictionaryFile.FORM_NAME_COLUMN]
                    section_name = columns[DataDictionaryFile.SECTION_NAME_COLUMN]
                    field_name = columns[DataDictionaryFile.CDE_NAME_COLUMN]
                    if form_name == "Demographics":
                        field_map[(FieldType.DEMOGRAPHICS, form_name, section_name, field_name)] = field_num
                    elif form_name == "Consent":
                        field_map[(FieldType.CONSENT, form_name, section_name, field_name)] = field_num
                    elif form_name == "Pedigree":
                        field_map[(FieldType.PEDIGREE_FORM, form_name, section_name, field_name)] = field_num

                    else:
                        raise DataImporterError("Unknown form: %s" % form_name)

        print field_map
        return field_map


    def _get_form_section_cde(self, columns):
        # return (form_model, section_model, cde_model)
        # if this makes sense otherwise None
        field_num = columns[DataDictionaryFile.FIELD_NUM_COLUMN]
        form_name = columns[DataDictionaryFile.FORM_NAME_COLUMN]
        section_name = columns[DataDictionaryFile.SECTION_NAME_COLUMN]
        cde_name = columns[DataDictionaryFile.CDE_NAME_COLUMN]

        try:
           form_model = RegistryForm.objects.get(name=form_name,
                                                 registry=self.registry_model)
        except Registry.DoesNotExist:
            return None

        # get the section in the form ...
        section_models = [section_model for section_model in form_model.section_models if section_model.display_name == section_name]
        if len(section_models) == 1:
            section_model = section_models[0]
        else:
            return None

        cde_models = [cde_model for cde_model in section_model.cde_models if cde_model.name == cde_name]
        if len(cde_models) == 1:
            cde_model = cde_models[0]
            return form_model, section_model, cde_model

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
                wrapped_row = RowWrapper(self.registry_model, self.field_map, row_dict)
                yield wrapped_row

    def _get_form_data(self, form_model, row):
        form_data = {}
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                for cde_model in section_model.cde_models:
                    key = form_key(form_model, section_model, cde_model)
                    value = row[(form_model, section_model, cde_model)]
                form_data[key] = value
        return form_data

    def _submit_form_data(self, patient_model, form_model, form_data):
        request = self._create_request(patient_model, form_model, form_data)
        view = FormView()
        view.request = request
        default_context_model = None
        try:
            # need to test for validation errors - how ?
            default_context_model = patient_model.default_context
            response = view.post(request, self.registry_model.code, form_model.pk, patient_model.pk, default_context_model.pk)
            validation_errors = self._get_validation_errors(response)
            
        except Exception:
            pass

    def _create_request(self, patient_model, form_model, form_data):
        url = "/%s/forms/%s/%s" % (form_model.registry.code, form_model.pk, patient_model.pk)
        request = self.request_factory.post(url, form_data)
        request.user = self.admin_user
        return request

    def _get_validation_errors(self, response):
        return [] #todo

    
        

    
                    
