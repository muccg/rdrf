import sys
import json
from django.db import transaction
from rdrf.models import Registry
from rdrf.models import RegistryForm
from rdrf.models import Section
from rdrf.models import CommonDataElement

from registry.patients.models import Patient


FAMILY_MEMBERS_CODE = "xxx"


class ImportError(Exception):
    pass


class RollbackError(Exception):
    pass


def meta(stage, run_after=False):
    # consistent logging
    def decorator(func):
        func_name = func.__name__

        def wrapper(*args, **kwargs):
            rdrf_id = self._get_rdrf_id()
            old_id = self._get_old_id()
            target = self._get_target()
            log_prefix = "%s/%s %s(%s):" % (rdrf_id,
                                            old_id,
                                            stage,
                                            target,
                                            func_name)

            try:
                value = func(*args, **kwargs)
                log_line = "%s: OK" % log_prefix
            except ImportError as ierr:
                log_line = "%s: IMPORT ERROR! - %s" % (log_prefix,
                                                       ex)

                value = None
                error_message = "%s" % ierr
                raise RollbackError(error_message)

            self.log(log_line)
            return value
        return wrapper
    return decorator


class OldRegistryImporter(object):

    def __init__(self, registry_model, json_file):
        self.json_file = json_file
        self.registry_model = registry_model
        self.patient_model = None
        self.form_model = None
        self.section_model = None
        self.cde_model = None
        self.record = None
        self._log = sys.stdout
        self.after_ops = []
        

    def log(self, msg):
        msg = msg + "\n"
        self._log.write(msg)

    def _get_rdrf_id(self):
        if self.patient_model:
            return self.patient_model.pk

    def _get_old_id(self):
        if self.record:
            return self.record.get("patient_id", None)

    def _get_target(self):
        form_name = section_code = cde_code = "?"

        if self.form_model:
            form_name = self.form_model.name

        if self.section_model:
            section_code = self.section_model.code

        if self.cde_model:
            cde_code = self.cde_model.code

        return "%s/%s/%s" % (form_name,
                             section_code,
                             cde_code)

    def process(self, old_records):
        for record in old_records:
            self.record = record
            self._process_record()

    def _get_records(self):
        self.data = self._load_json_data()
        self.log("keys = %s" % self.data.keys())

    def _load_json_data(self):
        with open(self.json_file) as jf:
            return json.load(jf)

    def run(self):
        old_records = self._get_records()
        self._process(old_records)

    def _process_record(self):
        self.patient_model = self._create_patient()
        for form_model in self.registry_model.form_models:
            self.form_model = form_model
            for section_model in form_model.section_models:
                self.section_model = section_model
                self._process_section()

    @meta("DEMOGRAPHICS")
    def _create_patient(self):
        p = Patient()
        p.family_name = self.retrieve("family_name")
        p.given_names = self.retrieve("given_names")
        p.sex = self.retrieve("sex")
        p.save()
        return p

    @meta("FAMILY_MEMBER", run_after=True)
    def _create_family_member(self, patient_model, family_member_dict):
        existing_relative_patient_model = None

    @meta("SECTION")
    def _process_section(self):
        if not self.section_model.allow_multiple:
            for cde_model in self.section_model.cde_models:
                self.cde_model = cde_model
                self._process_cde()
        else:
            self._process_multisection()

    @meta("MULTISECTION")
    def _process_multisection(self):
        for item_dict in self._get_items():
            self._append_multisection_item(item_dict)

    @meta("CDE")
    def _process_cde(self):
        old_value = self._get_old_value()
        converted_value = self._convert_value(old_value)
        if converted_value is not None:
            self._save_cde(converted_value)

    @meta("SAVECDE")
    def _save_cde(self, value):
        field_expression = self._get_current_field_expression()
        self._evalulate_field_expression(field_expression, value)

    def _get_current_field_expression(self):
        return "%s/%s/%s" % (self.form_model.name,
                             self.section_model.code,
                             self.cde_model.code)

    def _evaluate_field_expression(self, field_expression, value):
        self.patient_model.evaluate_field_expression(self.registry_model,
                                                     field_expression,
                                                     value=value)


if __name__ == "__main__":
    registry_code = sys.argv[1]
    json_file = sys.argv[2]

    registry_model = Registry.objects.get(code=registry_code)
    importer = OldRegistryImporter(registry_model, json_file)

    try:
        with transaction.atomic():
            importer.run()
    except Exception as err:
        sys.stderr.write("Unhandled error! - rollback will occur: %s" % err)
        sys.exit(1)
