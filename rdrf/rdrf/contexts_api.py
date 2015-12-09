from rdrf.models import Registry
from rdrf.models import RDRFContext
from django.contrib.contenttypes.models import ContentType

import logging

logger = logging.getLogger("registry_log")


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
