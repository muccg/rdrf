from rdrf.models import RegistryForm, Section, CommonDataElement
from rdrf.utils import de_camelcase
from explorer.views import Humaniser
import logging

logger = logging.getLogger("registry_log")


class _Question(object):
    """
    Read only view of entered data
    """
    def __init__(self, registry_model, form_name, section_code, section_index, cde_code, value):
        self.registry_model = registry_model
        self.humaniser = Humaniser(self.registry_model)
        self.form_name = form_name
        self.form_model = RegistryForm.objects.get(registry=self.registry_model,
                                                   name=form_name)

        self.section_model = Section.objects.get(code=section_code)
        self.cde_model = CommonDataElement.objects.get(code=cde_code)
        self.section_code = section_code
        self.index = section_index
        self.cde_code = cde_code
        self.value = value # raw value to be stored in Mongo
        # used on form:
        self.name = self._get_name()
        self.answer = self._get_display_value(value)
        self.question_id = self._construct_id()

    def _construct_id(self):
        return "id__%s__%s__%s" % (self.form_name,
                                   self.section_code,
                                   self.cde_code)

    def _get_name(self):
        # return a short name for the GUI
        return self.cde_model.name

    def _get_display_value(self, value):
        return self.humaniser.display_value2(self.form_model, self.section_model, self.cde_model, value)

    @property
    def target(self):
        """
        return the form/section/index/cde/value of the clinical form where this data should go if approved
        """
        # TODO target
        return (None, None, None, None, None)


class Questionnaire(object):
    """
    A questionnaire is a single public web form
    whose questions derive from several clinical\
    forms and where the wording of questions is potentially
    different.
    Curators "APPROVE" questionnaires which either:
    A) A new patient is created from the data
    B) An existing patient's data is updated from a selection from the
       questionnaire

    This class wraps data entered for a questionnaire to allow A and B easily
    from the view.
    """

    def __init__(self, registry_model, questionnaire_response_model):
        self.registry_model = registry_model
        self.questionnaire_response_model = questionnaire_response_model
        self.data = self.questionnaire_response_model.data

    def _get_display_value(self, cde_code, value):
        return value

    @property
    def questions(self):
        questions = []

        for form_dict in self.data["forms"]:
            logger.debug("getting questionnaire data form %s" % form_dict["name"])
            for section_dict in form_dict["sections"]:
                if not section_dict["allow_multiple"]:
                    for cde_dict in section_dict["cdes"]:
                        display_value = self._get_display_value(cde_dict["code"],
                                                                cde_dict["value"])
                        question = _Question(self.registry_model,
                                            form_dict["name"],
                                            section_dict["code"],
                                            0,
                                            cde_dict["code"],
                                            display_value)

                        questions.append(question)

                else:
                    for section_index, section_item in enumerate(section_dict["cdes"]):
                        for cde_dict in section_item:
                            display_value = self._get_display_value(cde_dict["code"],
                                                                    cde_dict["value"])
                            question = _Question(self.registry_model,
                                                form_dict["name"],
                                                section_dict["code"],
                                                section_index,
                                                cde_dict["code"],
                                                display_value)

                            questions.append(question)
        return questions

    def existing_data(self, patient_model):
        return []


