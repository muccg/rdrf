import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from rdrf.models.definition.models import ClinicalData, CommonDataElement, RegistryForm, Section, RDRFContext, ContextFormGroupItem
from registry.patients.models import Patient, DynamicDataWrapper
from rdrf.helpers.utils import catch_and_log_exceptions

# do not display debug information for the node js call.
import logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class ScriptUser:
    username = 'Calculated field script'


class Command(BaseCommand):
    help = 'Update calculated field values. It is mainly use to trigger periodic update.'

    def add_arguments(self, parser):
        parser.add_argument('--patient_id', action='append', type=int,
                            help='Only calculate the fields for a specific patient')
        parser.add_argument('--registry_code', action='append', type=str,
                            help='Only calculate the fields for a specific registry')
        parser.add_argument('--context_id', action='append', type=int,
                            help='Only calculate the fields for a specific context')
        parser.add_argument('--form_name', action='append', type=str,
                            help='Only calculate the fields for a specific form')
        parser.add_argument('--section_code', action='append', type=str,
                            help='Only calculate the fields for a specific section')
        parser.add_argument('--cde_code', action='append', type=str,
                            help='Only calculate the fields for a specific CDE')

        # Test command line example
        # django-admin update_calculated_fields --patient_id=2 --registry_code=fh --form_name=ClinicalData --section_code=SEC0007 --context_id=2 --cde_code=CDEfhDutchLipidClinicNetwork

    @catch_and_log_exceptions
    def handle(self, *args, **options):
        start = time.time()
        modified_patients = []

        if options['cde_code']:
            if not options['form_name'] or not options['section_code']:
                self.stdout.write(
                    self.style.ERROR("You must provide a form_name and section_code when providing a cde_code"))
                exit(1)
            # Note that has form_name and section_code are provided, if ever the code does not exist for this form/section, then it will just be ignored.
            calculated_cde_models = CommonDataElement.objects.filter(code__in=options['cde_code'])
        else:
            # Retrieve all calculated fields.
            calculated_cde_models = CommonDataElement.objects.filter(datatype='calculated')

        # Cache the cde models in a tree format
        # We will use this tree format:
        #   a) to avoid running any logic on registry/form that do not contain any calculated field
        #   b) to quickly retrieve all the cde models for a specific form
        #      We will use these cde models to retrieve their values and check their datatype.
        #
        # cde_models_tree=
        #        {...,
        #          registry.code: {...,
        #                          form.name: {...,
        #                                      section.code: {...,
        #                                                     cde.code: cde.model
        #                                                    }
        #                                     }
        #                         }
        #         }
        cde_models_tree = build_cde_models_tree(calculated_cde_models, options, self)

        if options['patient_id']:
            patient_models = Patient.objects.filter(id__in=options['patient_id'])
        else:
            # For all patient.
            patient_models = Patient.objects.all()

        for patient_model in patient_models:

            # For all registry for this patient.
            for registry_model in patient_model.rdrf_registry.all():
                # If the registry has at least one calculated field.
                if registry_model.code in cde_models_tree:
                    # For each form having at least one calculated field.
                    for form_name in cde_models_tree[registry_model.code]:
                        # For each context ids related to the patient / registry / form.
                        # We keep this call when the context id is passed as command argument for sanity check purpose
                        context_ids = context_ids_for_patient_and_form(patient_model, form_name, registry_model)
                        for context_id in context_ids:
                            if not options['context_id'] or context_id in options['context_id']:
                                changed_calculated_cdes = {}
                                # Get the existing cde values from the currently processed form.
                                form_cde_values = get_form_cde_values(patient_model, context_id, registry_model, form_name,
                                                                      cde_models_tree)
                                # If the form does not exist, then no need to process this form.
                                if form_cde_values:
                                    # context_var - it is the context variable of the js code (not to be confused with the RDRF context model).
                                    context_var = build_context_var(patient_model, context_id, registry_model, form_name,
                                                                    cde_models_tree, calculated_cde_models)

                                    # For each section of the form (we only do that because we need to know the section_code when calling set_form_value)
                                    for section_code in cde_models_tree[registry_model.code][form_name].keys():
                                        # For each calculated cdes in this section, do a WS call to the node server evaluation the js code.
                                        for calculated_cde_model in calculated_cde_models:
                                            if calculated_cde_model.code in context_var.keys() and calculated_cde_model.code in \
                                                    cde_models_tree[registry_model.code][form_name][section_code].keys():

                                                new_calculated_cde_value = calculate_cde(patient_model, form_cde_values, calculated_cde_model)

                                                # if the result is a new value, then store in a temp var so we can update the form at its context level.
                                                if context_var[calculated_cde_model.code] != new_calculated_cde_value:
                                                    if patient_model.id not in modified_patients:
                                                        modified_patients.append(patient_model.id)
                                                    changed_calculated_cdes[calculated_cde_model.code] = \
                                                        {"old_value": context_var[calculated_cde_model.code],
                                                         "new_value": new_calculated_cde_value,
                                                         "section_code": section_code}

                                    save_new_calculation(changed_calculated_cdes, context_id, form_name, patient_model,
                                                         registry_model)

        end = time.time()
        self.stdout.write(self.style.SUCCESS(f"Script ended in {end - start} seconds."))

        # Rerun the calculation when a patient value that were changed.
        for modified_patient_id in modified_patients:
            patient_option = options.copy()
            # little security to avoid unexpected buggy loop.
            # Do not run additional recalculation if ever we have been doing more than 10 times for the same patient.
            modified_patient_model = Patient.objects.get(id=modified_patient_id)
            if 'recalculate_step' not in patient_option.keys() or patient_option['recalculate_step'] < 10:
                patient_option['patient_id'] = [modified_patient_id]
                # calculate new step value
                if 'recalculate_step' not in patient_option.keys():
                    step = 1
                else:
                    step = patient_option['recalculate_step'] + 1
                patient_option['recalculate_step'] = step
                logger.info(f"[RECALCULATING] we are recalculating the patient {getattr(modified_patient_model, settings.LOG_PATIENT_FIELDNAME)} - recalculation number: {step} ")
                self.handle(**patient_option)
            else:
                logger.error(f"[LIKELY A BUG] We tried to recalculate the patient {getattr(modified_patient_model, settings.LOG_PATIENT_FIELDNAME)} more the 10 times. "
                             f"We stopped this patient calculated field update.")


def calculate_cde(patient_model, form_cde_values, calculated_cde_model):
    patient_values = {'date_of_birth': patient_model.date_of_birth,
                      'sex': patient_model.sex}
    form_values = {}
    for section in form_cde_values["sections"]:
        for cde in section["cdes"]:
            # TODO ignore cde of list type - check if it is okay
            if type(cde) is not list:
                form_values = {**form_values, cde["code"]: cde["value"]}

    mod = __import__('rdrf.forms.fields.calculated_functions', fromlist=['object'])
    func = getattr(mod, calculated_cde_model.code)
    if func:
        return func(patient_values, form_values)
    else:
        raise Exception(f"Trying to call unknown calculated function {calculated_cde_model.code}()")


def save_new_calculation(changed_calculated_cdes, context_id, form_name, patient_model, registry_model):
    # save the new form values in the ClinicalData model only when we have one values
    context_model = RDRFContext.objects.get(id=context_id)
    if changed_calculated_cdes:
        logger.info(f"UPDATING DB: These are the new value of the form/context {changed_calculated_cdes} - registry: {registry_model.code} - patient: {getattr(patient_model, settings.LOG_PATIENT_FIELDNAME)} - form: {form_name} - context: {context_id}")
        for changed_calculated_cde_code in changed_calculated_cdes.keys():
            patient_model.set_form_value(registry_code=registry_model.code,
                                         form_name=form_name,
                                         section_code=changed_calculated_cdes[changed_calculated_cde_code][
                                             'section_code'],
                                         data_element_code=changed_calculated_cde_code,
                                         value=changed_calculated_cdes[changed_calculated_cde_code]['new_value'],
                                         save_snapshot=list(changed_calculated_cdes.keys())[
                                             -1] == changed_calculated_cde_code,
                                         user=ScriptUser(),
                                         context_model=context_model,
                                         skip_bad_key=True)


def context_ids_for_patient_and_form(patient_model, form_name, registry_model):
    # Retrieve the context ids related to the patient / registry / form.
    form_model = RegistryForm.objects.get(name=form_name, registry=registry_model)
    form_group_items_models = ContextFormGroupItem.objects.filter(registry_form=form_model)
    context_models = RDRFContext.objects.filter(registry=registry_model,
                                                object_id=patient_model.id,
                                                context_form_group__in=[form_group_item_model.context_form_group for
                                                                        form_group_item_model in
                                                                        form_group_items_models])
    context_ids = [context_model.id for context_model in context_models]

    # If no context, it means we are in the case of a single context like DD registry.
    if not context_ids:
        context_ids = [c.id for c in patient_model.context_models]

    return context_ids


def get_form_cde_values(patient_model, context_id, registry_model, form_name, cde_models_tree):
    collection = ClinicalData.objects.collection(registry_model.code, "cdes")
    data = collection.find(patient_model, context_id).data()
    if data:
        forms = data.first()
        for form in forms["forms"]:
            if form["name"] == form_name:
                return form
    return None


def build_context_var(patient_model, context_id, registry_model, form_name, cde_models_tree, calculated_cde_models):
    context_var = {}
    calculated_cde_codes = [calculated_cde_model.code for calculated_cde_model in calculated_cde_models]
    # Retrieve the clinical_data for this registry / patient / context.
    wrapper = DynamicDataWrapper(patient_model, rdrf_context_id=context_id)
    data = wrapper.load_dynamic_data(registry_model.code, "cdes")
    # For each section of the form
    for section_model in cde_models_tree[registry_model.code][form_name]:
        # For each cdes in a form section
        for cde_code in cde_models_tree[registry_model.code][form_name][section_model]:
            try:
                cde_value = patient_model.get_form_value(registry_code=registry_model.code,
                                                         data_element_code=cde_code, form_name=form_name,
                                                         section_code=section_model, context_id=context_id,
                                                         clinical_data=data)
                # If cde is a date then display the JS format.
                if cde_value is not None and cde_models_tree[registry_model.code][form_name][section_model][
                        cde_code].datatype == 'date':
                    cde_value = datetime.strptime(cde_value, '%Y-%m-%d').__format__("%d-%m-%Y")
                if cde_value is None:
                    # the js context variable does not contain any null value, only empty string.
                    # (because the js context variable values are retrieved by jquery val())
                    cde_value = ""
                context_var[cde_code] = cde_value
            except KeyError:
                # we set the "never recorded" calculated values to None so these calculated fields get updated.
                if cde_code in calculated_cde_codes:
                    context_var[cde_code] = None
                # we ignore empty values.
                pass

    return context_var


def build_cde_models_tree(calculated_cde_models, options, command):
    # The cde models in a tree format for easy access
    # Format: {..., registry.code:{..., form.name:{..., section.code:{..., cde.code:cde.model}}}}
    cde_models_tree = {}

    # Cache the cde models we are retrieving so we load them from the DB only one time.
    cde_models_caching = {}

    if options['form_name']:
        if not options['registry_code']:
            command.stdout.write(
                command.style.ERROR("You must provide a registry_code when providing a form_name"))
            exit(1)
        form_models = RegistryForm.objects.filter(name__in=options['form_name'])
    else:
        form_models = RegistryForm.objects.all()
    for form_model in form_models:
        # if a registry_code argument was passed, only reference form that are in this registry.
        if not options['registry_code'] or form_model.registry.code in options['registry_code']:

            section_models = Section.objects.filter(code__in=form_model.get_sections())
            # Retrieve the form cde models only if at least one section has a calculated field.
            # and if a section_code argument was passed, only reference cdes from the form containing this section.
            if any(calculated_cde_model.code in section.get_elements() for calculated_cde_model in calculated_cde_models
                   for section in section_models) and (not options['section_code'] or any(section.code in options['section_code']
                                                                                          for section in section_models)):

                for section_model in section_models:
                    for cde_code in section_model.get_elements():
                        # Check if we already retrieved some cde models for this section.
                        if cde_models_tree \
                                and form_model.registry.code in cde_models_tree \
                                and form_model.name in cde_models_tree[form_model.registry.code] \
                                and section_model.code in cde_models_tree[form_model.registry.code][
                                    form_model.name]:
                            built_cdes = cde_models_tree[form_model.registry.code][form_model.name][
                                section_model.code]
                        else:
                            built_cdes = {}
                        # Check if we already retrieved some cde models for this form.
                        if cde_models_tree \
                                and form_model.registry.code in cde_models_tree \
                                and form_model.name in cde_models_tree[form_model.registry.code]:
                            built_sections = cde_models_tree[form_model.registry.code][form_model.name]
                        else:
                            built_sections = {}
                        # Check if we already retrieved some cde models for this registry.
                        if cde_models_tree \
                                and form_model.registry.code in cde_models_tree:
                            built_forms = cde_models_tree[form_model.registry.code]
                        else:
                            built_forms = {}
                        # Cache the cde models so we don't retrieve twice the same cde model from the DB.
                        if cde_code in cde_models_caching.keys():
                            cde_model = cde_models_caching[cde_code]
                        else:
                            cde_model = CommonDataElement.objects.get(code=cde_code)
                            cde_models_caching[cde_code] = cde_model
                        # Add the cde model to the dictionary.
                        cde_models_tree = {**cde_models_tree,
                                           form_model.registry.code: {**built_forms,
                                                                      form_model.name: {**built_sections,
                                                                                        section_model.code: {
                                                                                            **built_cdes,
                                                                                            cde_code: cde_model}}}}
    return cde_models_tree
