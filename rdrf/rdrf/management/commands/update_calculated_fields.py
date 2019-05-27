import json

import requests
from django.core.management.base import BaseCommand

from rdrf.models.definition.models import CommonDataElement, RegistryForm, Section, RDRFContext, ContextFormGroupItem
from registry.patients.models import Patient, DynamicDataWrapper
import urllib.parse

from datetime import datetime

import time


class Command(BaseCommand):
    help = 'Update calculated field values. It is mainly use to trigger periodic update.'

    def add_arguments(self, parser):
        parser.add_argument('--patient_id', action='append', type=int,
                            help='Only calculate the fields for a specific patient')
        parser.add_argument('--registry_code', action='append', type=int,
                            help='Only calculate the fields for a specific registry')
        parser.add_argument('--cde_code', action='append', type=int, help='Only calculate the fields for a specific CDE')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(options['patient_id']))

        start = time.time()
        # Retrieve all calculated fields.
        calculated_cde_models = CommonDataElement.objects.exclude(calculation='')

        # Cache the cde models in a tree format
        # We will use this tree format:
        #   a) to avoid running any logic on registry/form that do not contain any calculated field
        #   b) to quickly retrieve all the cde codes for a specific form (we will use use to retrieve the values
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
        cde_models_tree = build_cde_models_tree(calculated_cde_models)

        print("----------------------- RUN CALCULATIONS --------------------------")

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
                        context_ids = context_ids_for_patient_and_form(patient_model, form_name, registry_model)
                        for context_id in context_ids:
                            changed_calculated_cdes = {}
                            # context_var - it is the context variable of the js code (not to be confused with the RDRF context model).
                            context_var = build_context_var(patient_model, context_id, registry_model, form_name, cde_models_tree)
                            # For each calculated cdes in this form, do a WS call to the node server evaluation the js code.
                            for calculated_cde_model in calculated_cde_models:
                                if calculated_cde_model.code in context_var.keys():
                                    # web service call to the nodejs calculation evaluation script.
                                    new_calculated_cde_value = call_ws_calculation(calculated_cde_model, patient_model, context_var)

                                    # if the result is a new value, then store in a temp var so we can update the form at its context level.
                                    if context_var[calculated_cde_model.code] != new_calculated_cde_value:
                                        changed_calculated_cdes[calculated_cde_model.code] = \
                                            {"old_value": context_var[calculated_cde_model.code], "new_value": new_calculated_cde_value}

                            # TODO: store the new form value in the ClinicalData model - only when values
                            if changed_calculated_cdes:
                                print(f"These are the new value of the form/context {changed_calculated_cdes}")

                            # TODO: alert us than the form has been updated (so we can track that the code is properly working)

                            # TODO: don't forget to update the form history (context level - if at least)

                                # TODO: web service call + storing value could be done in a function run asynchronously
                                #       (not that simple because we need to check the node server can accept that many connections | postgres transaction to be implemented too).

        end = time.time()
        self.stdout.write(self.style.SUCCESS(f"All fields have been successfully updated in {end - start} seconds."))


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
    # Retrieve the clinitcal_data for this registry / patient / context.
    wrapper = DynamicDataWrapper(patient_model, rdrf_context_id=context_id)
    data = wrapper.load_dynamic_data(registry_model.code, "cdes")
    # For each section.
    for section_model in cde_models_tree[registry_model.code][form_name]:
        # For each cdes.
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
                context_var[cde_code] = cde_value
            except KeyError:
                # we ignore empty values.
                pass
                # print(f"KeyError for CDE value:{patient_model.combined_name} {[c.id for c in patient_model.context_models]} | {registry.code} | {form} | {section} | {cde_code}")
    return context_var


def call_ws_calculation(calculated_cde_model, patient_model, context_var):
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
    js_code = f"{rdrf_var} patient = {json.dumps(patient_var)}; context = {json.dumps(context_var)}; {calculated_cde_model.calculation}"
    headers = {'Content-Type': 'application/json'}
    # we encode the JS function.
    encoded_js_code = {"jscode": urllib.parse.quote(js_code)}
    # Retrieve the new value by web service.
    resp = requests.post(url='http://node_js_evaluator:3131/eval', headers=headers,
                         json=encoded_js_code)
    new_calculated_cde_value = format(resp.json())

    print(f"Result: {new_calculated_cde_value}")
    print(f"----------------------- END CALCULATION --------------------------")
    return new_calculated_cde_value


def build_cde_models_tree(calculated_cde_models):
    # The cde models in a tree format for easy access
    # Format: {..., registry.code:{..., form.name:{..., section.code:{..., cde.code:cde.model}}}}
    cde_models_tree = {}

    # Cache the cde models we are retrieving so we load them from the DB only one time.
    cde_models_caching = {}

    form_models = RegistryForm.objects.all()
    for form_model in form_models:

        section_models = Section.objects.filter(code__in=form_model.get_sections())
        # Retrieve the form cde models only if at least one section has a calculated field.
        if any(i.code in section.get_elements() for i in calculated_cde_models for section in section_models):

            for section_model in section_models:

                for cde_code in section_model.get_elements():
                    # Check if we already retrieved some cde models for this section.
                    if cde_models_tree \
                            and form_model.registry.code in cde_models_tree \
                            and form_model.name in cde_models_tree[form_model.registry.code] \
                            and section_model.code in cde_models_tree[form_model.registry.code][form_model.name]:
                        built_cdes = cde_models_tree[form_model.registry.code][form_model.name][section_model.code]
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
                                                                                    section_model.code: {**built_cdes,
                                                                                                         cde_code: cde_model}}}}
    return cde_models_tree
