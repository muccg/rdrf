from rdrf.models import Registry
from rdrf.models import RDRFContext
from django.contrib.contenttypes.models import ContentType

import logging

logger = logging.getLogger("registry_log")


class RDRFContextError(Exception):
    pass


def create_rdrf_default_contexts(patient, registry_ids):
    content_type = ContentType.objects.get_for_model(patient)
    for registry_id in registry_ids:
        try:
            registry_model = Registry.objects.get(id=registry_id)
        except Registry.DoesNotExist:
            continue

        existing_contexts_count = RDRFContext.objects.filter(registry=registry_model,
                                                             content_type=content_type,
                                                             object_id=patient.pk).count()

        if existing_contexts_count == 0:
            logger.debug("creating default context for patient %s registry %s" % (patient, registry_model))
            rdrf_context = RDRFContext(registry=registry_model, content_object=patient)
            rdrf_context.display_name = "default"
            rdrf_context.save()
            logger.debug("context saved ok")


class RDRFContextManager(object):
    def __init__(self, registry_model):
        self.registry_model = registry_model
        self.supports_contexts = self.registry_model.has_feature("contexts")

    def get_or_create_default_context(self, patient_model, new_patient=False):
        if not self.supports_contexts:
            content_type = ContentType.objects.get_for_model(patient_model)
            contexts = [c for c in RDRFContext.objects.filter(registry=self.registry_model,
                                                              content_type=content_type,
                                                              object_id=patient_model.pk)]
            if len(contexts) == 0:
                # No default setup so create one
                return self.create_context(patient_model, "default")
            elif len(contexts) == 1:
                return contexts[0]
            else:
                raise RDRFContextError("Patient %s in %s has more than 1 context" % (patient_model, self.registry_model))
        else:
            if new_patient:
                return self.create_initial_context_for_new_patient(patient_model)
            else:
                raise RDRFContextError("Registry %s supports contexts so there is no default context" % self.registry_model)

    def create_initial_context_for_new_patient(self, patient_model):
        content_type = ContentType.objects.get_for_model(patient_model)
        contexts = [c for c in RDRFContext.objects.filter(registry=self.registry_model,
                                                           content_type=content_type,
                                                           object_id=patient_model.pk).order_by("pk")]
        if len(contexts) > 0:
            return contexts[0]
        else:
            return self.create_context(patient_model, "default")

    def create_context(self, patient_model, display_name):
        rdrf_context = RDRFContext(registry=self.registry_model, content_object=patient_model, display_name=display_name)
        rdrf_context.save()
        return rdrf_context

    def get_context(self, context_id, patient_model):
        if context_id is None:
            return self.get_or_create_default_context(patient_model)

        content_type = ContentType.objects.get_for_model(patient_model)
        try:
            rdrf_context_model = RDRFContext.objects.get(pk=context_id,
                                                         registry=self.registry_model,
                                                         content_type=content_type,
                                                         object_id=patient_model.pk)
            return rdrf_context_model
        except RDRFContext.DoesNotExist:
            raise RDRFContextError("Context does not exist")
