import django
django.setup()

from django.db import transaction
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement
from rdrf.models import RDRFContext

from rdrf.contexts_api import RDRFContextManager


from rdrf.form_view import FormView
from django.test import RequestFactory

from registry.patients.models import Patient
from registry.groups.models import CustomUser


import openpyxl as xl
import os
import sys


class DataDictionary:
    FIELD_NUM_COLUMN = 1
    FORM_NAME_COLUMN = 2
    SECTION_NAME_COLUMN = 3
    CDE_NAME_COLUMN = 4
    PATIENT_ID_FIELDNUM = 1
    INDEX_FIELD_NUM = 29
    INDEX_VALUE = "index"
    RELATIVE_VALUE = "relative"
    EXTERNAL_ID_COLUMN = 1


class ImporterError(Exception):
    pass


class FieldNumNotFound(ImporterError):
    pass


class FieldType:
    CDE = 1
    DEMOGRAPHICS = 2
    PEDIGREE_FORM = 3
    CONSENT = 4


DEMOGRAPHICS_TABLE = [
    # fieldnum(column for data), English, field_expression, converter func (if
    # any
    # NB ordering is changed to allow creation of objects
    (3, "Family name", "family_name"),
    (4, "Given names", "given_names"),
    (7, "Date of birth", "date_of_birth"),
    (10, "Sex", "gender", "meteor"),
    (5, "Maiden name", "maiden_name"),
    (6, "Hospital/Clinic ID", ""),
    (8, "Country of birth", "country_of_birth"),
    (9, "Ethnic Origin", "ethnic_origin"),
    (11, "Home Phone", "home_phone"),
    (12, "Mobile Phone", "mobile_phone"),
    (13, "Work Phone", "work_phone"),
    (14, "Email", "email"),
    (15, "Living status", "living_status"),
    (16, "Address", "Demographics/Address/Home/Address"),
    (17, "Suburb/Town", "Demographics/Address/Home/Suburb"),
    (18, "State", "Demographics/Address/Home/State"),
    (19, "Postcode", "Demographics/Address/Home/Postcode"),
    (20, "Country", "Demographic/Address/Home/Country"),
    (2, "Centre", "working_group"),
]





class SpreadsheetImporter(object):
    # rewriting importer
    # as we need to link relatives to index patients
    # so we do two passes
    # also FH introduced form groups
    # we need to be aware of them

    def __init__(self, registry_model, import_spreadsheet_filepath, datadictionary_sheetname, datasheet_name):
        self.registry_model = registry_model
        self.rdrf_context_manager = RDRFContextManager(registry_model)
        self.import_spreadsheet_filepath = import_spreadsheet_filepath
        self.datadictionary_sheetname = datadictionary_sheetname
        self.datadictionary_sheet = None
        self.datasheet_name = datasheet_name
        self.data_sheet = None
        self.indexes = []
        self.relatives = []
        self.family_linkage_map = {}
        self.index_patient_map = {}
        self.field_map = {}
        self.id_map = {}
        self._load_workbook()
        self._load_datasheet()
        self._load_datadictionary_sheet()
        self._build_field_map()


    def _load_workbook(self):
        if not os.path.exists(self.import_spreadsheet_filepath):
            raise ImporterError("Spreadsheet file %s does not exist" %
                                self.import_spreadsheet_filepath)

        try:
            self.workbook = xl.load_workbook(self.import_spreadsheet_filepath)

        except Exception as ex:
            raise ImporterError("Could not load Import spreadsheet: %s",
                                ex)

    def _load_datadictionary_sheet(self):
        self.datadictionary_sheet = self.workbook.get_sheet_by_name(
            self.datadictionary_sheetname)

    def _load_datasheet(self):
        self.data_sheet = self.workbook.get_sheet_by_name(self.datasheet_name)

    def _get_value(self, sheet, row, column):
        return sheet.cell(row=row,
                          column=column).value

    def _build_field_map(self):
        print("building field map ..")
        # map RDRF "fields" to fieldnums in the spreadsheet
        d = {}
        d["patient_id"] = DataDictionary.PATIENT_ID_FIELDNUM

        sheet = self.datadictionary_sheet
        finished = False
        row_num = 3  # fields start here

        while not finished:
            field_num = self._get_value(sheet,
                                        row_num,
                                        DataDictionary.FIELD_NUM_COLUMN)

            if not field_num:
                finished = True
            else:
                form_name = self._get_value(sheet,
                                            row_num,
                                            DataDictionary.FORM_NAME_COLUMN)

                section_name = self._get_value(sheet,
                                               row_num,
                                               DataDictionary.SECTION_NAME_COLUMN)

                cde_name = self._get_value(sheet,
                                           row_num,
                                           DataDictionary.CDE_NAME_COLUMN)

                key = (form_name, section_name, cde_name)


                d[key] = field_num
                print("field map key %s = %s" % (key, field_num))

                row_num += 1

        self.field_map = d
        

    def _get_converter_func(self, converter_name):
        # look for methods on me like  converter_<converter_name>)
        method_name = "converter_%s" % converter_name
        if hasattr(self, method_name):
            converter_func = getattr(self, method_name)
            if callable(converter_func):
                return converter_func
        raise Exception("Bad converter: %s" % converter_name)


    # converters

    def converter_meteor(self, value):
        sex_choices = {"Male" : 1,
                       "Female": 2,
                       "Indeterminate": 3}

        return sex_choices.get(value, None)
    

    # end of converters
    

    def _get_demographics_field(self, row, long_field_name):
        for tup in DEMOGRAPHICS_TABLE:
            if tup[1] == long_field_name:
                field_num = tup[0]
                if len(tup) == 4:
                    converter = tup[3]
                else:
                    converter = None
                value = self._get_converted_value(row, field_num, converter)
                print("row %s demographics field %s value = %s" % (row,
                                                                   long_field_name,
                                                                   value))
                
                                                                        
                return value
            
            
        raise Exception("Unknown field %s" % long_field_name)
    

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
            

    def run(self):
        print("**********************")
        print("beginning run")
        self._load_datasheet()
        print("loaded datasheet")
        row = 2  # data starts here

        # first find which rows are index patients, which relatives
        print("sorting indexes from relatives ...")
        scanned = False
        while not scanned:
            if self._check_type(row, check_index=True):
                self.indexes.append(row)
                row += 1
            elif self._check_type(row, check_index=False):
                self.relatives.append(row)
                row += 1
            else:
                scanned = True

        # now begin processing for real
        print("finished sorting")
        num_indexes = len(self.indexes)
        num_relatives = len(self.relatives)
        print("There are %s indexes and %s relatives to import" % (num_indexes,
                                                                   num_relatives))
        
        self._create_indexes()
        
        #self._create_relatives()
        self._dump_id_map()

    def _get_column(self, field_num, row):
        return self.data_sheet.cell(row=row,
                                    column=int(field_num)).value

    def _check_type(self, row, check_index=True):
        index_cell = self._get_value(self.data_sheet,
                                     row,
                                     DataDictionary.INDEX_FIELD_NUM)

        if check_index:
            check_value = DataDictionary.INDEX_VALUE
        else:
            check_value = DataDictionary.RELATIVE_VALUE

        value = index_cell == check_value
        return value

    def _is_relative(self, row):
        value = self._get_column(
            DataDictionary.INDEX_FIELD_NUM, row) == DataDictionary.RELATIVE_VALUE
        print("checking row %s value =%s" % (row, value))
        if value:
            print("row %s in relative" % row)
        return value

    def _create_indexes(self):
        print("creating index patients")
        for row in self.indexes:
            print("processing index row %s" % row)
            index_patient = self._import_patient(row)
            print("created index patient %s for row %s OK" % (index_patient, row))
            external_id = self._get_external_id(row)
            self._update_id_map(external_id, index_patient.pk)

    def _update_id_map(self, external_id, rdrf_id):
        if external_id in self.id_map:
            raise ImportError("Dupe ID?")
        else:
            self.id_map[external_id] = rdrf_id


    def _dump_id_map(self):
        with open("id_map.csv","w") as f:
            f.write("OLD_ID,RDRF_ID\n")
            for key in sorted(self.id_map.keys()):
                line = "%s,%s\n" % (key, self.id_map[key])
                f.write(line)

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

    def _get_field(self, row, field):
        if type(field) is type(basestring):
            # demographics
            field_num = self._get_field_num(field)
            value = self._get_value(self.data_sheet,
                                    row,
                                    field_num)
            return value

    def _import_demographics_data(self, patient, row):
        print("creating patient from row %s" % row)
        for t in DEMOGRAPHICS_TABLE:
            updates = []
            has_converter = len(t) == 4
            field_num = t[0]
            field_expression = t[2]
            value = self._get_column(field_num, row)
            if has_converter:
                converter_name = t[3]
                converter_func = self._get_converter_func(converter_name)
                value = converter_func(value)
            updates.append((field_expression, value))


        for field_expression, value in updates:
            print("Will update row %s patient %s field %s --> value %s" % (row,
                                                               patient,
                                                               field_expression,
                                                               value))
            
                                                                                

        context_model = self.rdrf_context_manager.get_or_create_default_context(patient, new_patient=True)
        print("context for patient = %s" % context_model)
        patient.update_field_expressions(self.registry_model, updates, context_model=context_model)


    def _import_pedigree_data(self, patient, row):
        print("importing pedigree data for patient %s row %s" % (patient,
                                                                 row))

        pass

    def _get_context_for_patient(self, patient_model):
        if not self.registry_model.has_feature("contexts"):
            return patient_model.default_context
        
        for context_model in patient_model.context_models:
            if context_model.context_form_group and context_model.context_form_group.context_type == "F":
                return context_model
            
                                                      

    def _get_converted_value(self,row, field_num,  converter=None):
        value = self._get_column(field_num, row)
        if converter:
            converter_func = self._get_converter_func(converter)
            value = converter_func(value)
        return value
    

    def _create_minimal_patient(self, row):
        patient = Patient()
        family_name = self._get_demographics_field(row, "Family name")
        given_names = self._get_demographics_field(row, "Given names")
        date_of_birth = self._get_demographics_field(row, "Date of birth")
        sex = self._get_demographics_field(row, "Sex")

        patient.family_name = family_name
        patient.given_names = given_names
        patient.date_of_birth = date_of_birth
        patient.sex = sex
        patient.consent = True # to satisfy validation ...
        patient.save()
        print("saved minimal patient %s" % patient)

        patient.rdrf_registry = [self.registry_model]
        patient.save()
        print("saved patient %s to %s" % (patient,
                                          self.registry_model))
        

        return patient

    def _import_patient(self, row):
        patient = self._create_minimal_patient(row)
        self._import_demographics_data(patient, row)
        print("imported demographics OK for patient %s row %s" % (patient, row))
        self._import_pedigree_data(patient, row)
        self._import_consents(patient, row)
        
        # ensure we import data into the correct context

        for context_model, form_model in self._get_forms_and_contexts(patient):
            print("Importing CDEs on form %s for patient %s row %s" % (form_model,
                                                                       patient,
                                                                       row))
            
            self._import_clinical_form(form_model, patient, context_model, row)

        return patient

    def _get_forms_and_contexts(self, patient_model):
        # get forms in fixed groups
        results = []
        for context_form_group in self.registry_model.context_form_groups.all():
            if context_form_group.is_default and context_form_group.context_type == "F":
                try:
                    context_model = RDRFContext.objects.get(object_id=patient_model.pk,
                                                            registry=self.registry_model,
                                                            context_form_group=context_form_group)
                except RDRFContext.DoesNotExist:
                    # should not happen as contexts for fixed groups created
                    # when patient craeted
                    raise Exception("could not find context for patient %s cfg %s" % (patient_model, context_form_group))
                    

                except RDRFContext.MultipleObjectsReturned:
                    raise Exception("too many contexts for patient %s cfg %s" %
                                    (patient_model, context_form_group))

                for form_model in context_form_group.form_models:
                    results.append((context_model, form_model))
        return results

    def _import_consents(self, patient, row):
        print("importing consents TODO for patient %s row %s" % (patient, row))


    def _convert_cde_value(self, cde_model, spreadsheet_value):
        if cde_model.pv_group:
            for pv in cde_model.pv_group.permitted_value_set.all():
                if spreadsheet_value == pv.value:
                    return pv.code
            return None
        else:
            return spreadsheet_value
        
            
        

    def _import_clinical_form(self, form_model, patient_model, context_model, row):
        print("Importing clinical form %s for patient %s row %s" % (form_model,
                                                                    patient_model,
                                                                    row))
        field_updates = []
        for section_model in form_model.section_models:
            if not section_model.allow_multiple:
                # 1st data import sheet does not contain any multisections as
                # is 1 row per patient
                for cde_model in section_model.cde_models:
                    if self._cde_included(form_model, section_model, cde_model):


                        print("Updating %s %s %s ..." % (form_model,
                                                         section_model,
                                                         cde_model))
                        field_num = self._get_field_num((form_model, section_model, cde_model))
                        print("corresponding field_num is %s" % field_num)
                        spreadsheet_value = self._get_value(self.data_sheet,
                                                            row,
                                                            field_num)
                        
                        print("value in spreadsheet = %s" % spreadsheet_value)

                        rdrf_value = self._convert_cde_value(cde_model, spreadsheet_value)

                        print("converted value = %s" % rdrf_value)

                        
                        field_expression = self._get_field_expression(form_model, section_model, cde_model)
                        
                        field_updates.append((field_expression, rdrf_value))
                        print("Added update %s --> %s" % (field_expression, rdrf_value))

                    else:
                        print("Form %s Section %s CDE %s NOT INCLUDED IN SPREADSHEET" % (form_model.name,
                                                                                         section_model.display_name,
                                                                                         cde_model.name))

        if len(field_updates) == 0:
            print("*** No clinical field updates for patient %s row %s form %s" % (patient_model,
                                                                               row,
                                                                               form_model))
        else:
            print("There are %s updates for patient %s row %s" % (len(field_updates),
                                                                  patient_model,
                                                                  row))
            patient_model.update_field_expressions(
                self.registry_model,
                field_updates,
                context_model
            )


    def _get_external_id(self, row):
        return self._get_column(DataDictionary.EXTERNAL_ID_COLUMN, row)
    
        

    def _cde_included(self, form_model, section_model, cde_model):
        name_tuple = (form_model.name, section_model.display_name, cde_model.name)
        print("name_tuple = %s" % str(name_tuple))
        return name_tuple in self.field_map

    def _get_field_expression(self, form_model, section_model, cde_model):
        expression = "%s/%s/%s" % (form_model.name,
                                    section_model.code,
                                    cde_model.code)
        
        return expression

if __name__ == "__main__":
    registry_code = sys.argv[1]
    spreadsheet_file = sys.argv[2]
    dictionary_sheet_name = sys.argv[3]
    data_sheet_name = sys.argv[4]
    registry_model = Registry.objects.get(code=registry_code)
    spreadsheet_importer = SpreadsheetImporter(registry_model,
                                               spreadsheet_file,
                                               dictionary_sheet_name,
                                               data_sheet_name)
    spreadsheet_importer.run()
