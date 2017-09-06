import logging
logger = logging.getLogger(__name__)


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
        registry_model = self.context["registry_model"]
        if "patientCentres" in registry_model.metadata:
            questionnaire_context = self.context.get("questionnaire_context", "au")
            # Assumes a list of pairs ( code and display text to fill the drop down)
            if questionnaire_context is None:
                questionnaire_context = 'au'

            return registry_model.metadata["patientCentres"][questionnaire_context]
        else:
            from registry.groups.models import WorkingGroup
            items = []
            for working_group in WorkingGroup.objects.filter(
                    registry=registry_model).order_by('name'):
                items.append((working_group.name, working_group.name))

            return items
