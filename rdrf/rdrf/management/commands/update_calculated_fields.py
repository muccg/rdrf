import json
import time
import urllib.parse
from datetime import datetime

import requests
from django.core.management.base import BaseCommand

from rdrf.models.definition.models import CommonDataElement, RegistryForm, Section, RDRFContext, ContextFormGroupItem
from registry.patients.models import Patient, DynamicDataWrapper


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

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(options['patient_id']))

        start = time.time()

        if options['cde_code']:
            if not options['form_name'] or not options['section_code']:
                self.stdout.write(
                    self.style.ERROR("You must provide a form_name and section_code when providing a cde_code"))
                exit(1)
            # Note that has form_name and section_code are provided, if ever the code does not exist for this form/section, then it will just be ignored.
            calculated_cde_models = [CommonDataElement.objects.get(code='')]
        else:
            # Retrieve all calculated fields.
            calculated_cde_models = CommonDataElement.objects.exclude(calculation='')

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

        print("----------------------- RUN CALCULATIONS --------------------------")

        if options['patient_id']:
            patient_models = [Patient.objects.get(id=options['patient_id'])]
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
                            if not options['context_id'] or options['context_id'] == context_id:
                                changed_calculated_cdes = {}
                                # context_var - it is the context variable of the js code (not to be confused with the RDRF context model).
                                context_var = build_context_var(patient_model, context_id, registry_model, form_name,
                                                                cde_models_tree)

                                # For each section of the form (we only do that because we need to know the section_code when calling set_form_value)
                                for section_code in cde_models_tree[registry_model.code][form_name].keys():

                                    # For each calculated cdes in this section, do a WS call to the node server evaluation the js code.
                                    for calculated_cde_model in calculated_cde_models:
                                        if calculated_cde_model.code in context_var.keys() and calculated_cde_model.code in \
                                                cde_models_tree[registry_model.code][form_name][section_code].keys():
                                            # web service call to the nodejs calculation evaluation script.
                                            new_calculated_cde_value = call_ws_calculation(calculated_cde_model,
                                                                                           patient_model,
                                                                                           context_var)

                                            # if the result is a new value, then store in a temp var so we can update the form at its context level.
                                            if context_var[calculated_cde_model.code] != new_calculated_cde_value:
                                                changed_calculated_cdes[calculated_cde_model.code] = \
                                                    {"old_value": context_var[calculated_cde_model.code],
                                                     "new_value": new_calculated_cde_value,
                                                     "section_code": section_code}

                                save_new_calculation(changed_calculated_cdes, context_id, form_name, patient_model,
                                                     registry_model)

        end = time.time()
        self.stdout.write(self.style.SUCCESS(f"All fields have been successfully updated in {end - start} seconds."))


def save_new_calculation(changed_calculated_cdes, context_id, form_name, patient_model, registry_model):
    # TODO: storing value could be done in a function run asynchronously
    #

    # save the new form values in the ClinicalData model only when we have one values
    context_model = RDRFContext.objects.get(id=context_id)
    if changed_calculated_cdes:
        print(f"These are the new value of the form/context {changed_calculated_cdes}")
        # for changed_calculated_cde_code in changed_calculated_cdes.keys():
        #     patient_model.set_form_value(registry_code=registry_model.code,
        #                                  form_name=form_name,
        #                                  section_code=changed_calculated_cdes[changed_calculated_cde_code].section_code,
        #                                  data_element_code=changed_calculated_cde_code,
        #                                  value=changed_calculated_cdes[changed_calculated_cde_code].new_value,
        #                                  save_snapshot=changed_calculated_cdes.keys(-1) == changed_calculated_cde_code,
        #                                  context_model=context_model)

    # TODO: alert us than the form has been updated (so we can track that the code is properly working)

    # TODO: don't forget to update the form history (context level - if at least)


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

    print(f"Form: {form_name} contexts: {context_ids}")
    print("---------------------------------------")
    return context_ids


def build_context_var(patient_model, context_id, registry_model, form_name, cde_models_tree):
    context_var = {}
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
                # we ignore empty values.
                pass

    return context_var


def call_ws_calculation(calculated_cde_model, patient_model, context_var):
    # TODO: web service call could be done asynchronously
    #       (not that simple because we need to check the node server can accept that many connections).

    print(f"{calculated_cde_model.code}")
    # Build the web service call parameter.
    patient_var = {'sex': patient_model.sex, 'date_of_birth': patient_model.date_of_birth.__format__("%Y-%m-%d")}
    rdrf_var = """
                                        class Rdrf {
                                            log(msg) {
                                                console.log(msg);
                                            }

                                            get(data, key) {
                                                return data[key];
                                                // console.log("A function is calling RDRF.get ADSAFE - ignoring...");
                                            }
                                        }

                                        RDRF = new Rdrf();"""
    js_code = f"""{rdrf_var} 
        patient = {json.dumps(patient_var)}
        context = {json.dumps(context_var)}
        {calculated_cde_model.calculation}"""
    headers = {'Content-Type': 'application/json'}
    # we encode the JS function.
    encoded_js_code = {"jscode": urllib.parse.quote(js_code)}
    # Retrieve the new value by web service.
    resp = requests.post(url='http://node_js_evaluator:3131/eval', headers=headers,
                         json=encoded_js_code)
    ws_value = resp.json()
    print(f"Result: {ws_value}")
    new_calculated_cde_value = "NaN" if ws_value['isNan'] else str(ws_value['value'])
    print(f"Result: {new_calculated_cde_value}")
    print(f"----------------------- END CALCULATION --------------------------")
    return new_calculated_cde_value


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
        form_models = [RegistryForm.objects.get(form_name=options['form_name'])]
    else:
        form_models = RegistryForm.objects.all()
    for form_model in form_models:
        # if a registry_code argument was passed, only reference form that are in this registry.
        if not options['registry_code'] or options['registry_code'] == form_model.registry.code:

            section_models = Section.objects.filter(code__in=form_model.get_sections())
            # Retrieve the form cde models only if at least one section has a calculated field.
            if any(calculated_cde_model.code in section.get_elements() for calculated_cde_model in calculated_cde_models
                   for section in section_models):

                for section_model in section_models:
                    # if a section_code argument was passed, only reference cdes that are in this section.
                    if not options['section_code'] or options['section_code'] == section_model.code:

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
