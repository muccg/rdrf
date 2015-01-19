import logging
logger = logging.getLogger("registry_log")

class DataSource(object):
    def __init__(self, context):
        self.context = context

    def values(self):
        return []


class PatientCentres(DataSource):
    """
    centres = working groups
    We default to working groups if metadata on the registry doesn't have override
    questionnaire_context is a string like au or nz ( ophg wanted different centre dropdowns for DM1 in au vs nz for example)
    """
    def values(self):
        logger.debug("Datasource Patientcentres values()")
        registry_model = self.context["registry_model"]
        if "patientCentres" in registry_model.metadata:
            logger.debug("found metadata")
            questionnaire_context = self.context.get("questionnaire_context", "au")
            logger.debug("XXXXXX QUESTIONNAIRE CONTEXT = %s" % questionnaire_context)
            return registry_model.metadata["patientCentres"][questionnaire_context]
        else:
            from registry.groups.models import WorkingGroup
            items = []
            for working_group in WorkingGroup.objects.filter(registry=registry_model).order_by('name'):
                items.append((working_group.name, working_group.name))
            return items

