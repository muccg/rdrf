from django.db import models
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import Patient
import uuid
import logging

logger = logging.getLogger(__name__)


class Survey(models.Model):
    registry = models.ForeignKey(Registry)
    name = models.CharField(max_length=80)
    @property
    def client_rep(self):
        return [ sq.client_rep for sq in self.survey_questions.all().order_by('position')]

    def __str__(self):
        return "%s Survey: %s" % (self.registry.code, self.name) 

    def clean(self):
        for question  in self.survey_questions.all():
            logger.debug("checking survey q %s" % question.cde.code)
            if question.cde.datatype != "range":
                logger.debug("%s not a range" % question.cde.code)
                #raise ValidationError("Survey questions must be ranges")

    
class Precondition(models.Model):
    survey = models.ForeignKey(Survey)
    cde = models.ForeignKey(CommonDataElement)
    value = models.CharField(max_length=80)

    def __str__(self):
        return "if <<%s>> = %s" % (self.cde,
                                   self.value)
    
class SurveyQuestion(models.Model):
    position = models.IntegerField(null=True, blank=True)
    survey = models.ForeignKey(Survey, related_name='survey_questions')
    cde = models.ForeignKey(CommonDataElement)
    precondition  = models.ForeignKey(Precondition, blank=True, null=True)

    @property
    def name(self):
        return self.cde.name

    @property
    def client_rep(self):
        # client side representation
        if not self.precondition:
            return  {"tag": "cde",
                     "cde": self.cde.code,
                     "datatype": self.cde.datatype,
                     "title": self.cde.name,
                     "options": self._get_options() }
                    
        else:
            return { "tag": "cond",
                     "cde": self.cde.code,
                     "title": self.cde.name,
                     "options": self._get_options(),
                     "cond": { "op": "=",
                               "cde": self.precondition.cde.code,
                               "value": self.precondition.value
                             }
                     }

    def _get_options(self):
        if self.cde.datatype == 'range':
            return self.cde.pv_group.options
        else:
            return []


    @property
    def expression(self):
        if not self.precondition:
            return self.cde.name + " always"
        else:
            return self.cde.name + "  if "  + self.precondition.cde.name + " = " + self.precondition.value



class SurveyStates:
    REQUESTED = "requested"
    STARTED = "started"
    COMPLETED = "completed"

class SurveyRequestStates:
    CREATED = "created"
    REQUESTED = "requested"
    RECEIVED = "received"

class SurveyAssignment(models.Model):
    """
    This gets created on the proms system
    """
    SURVEY_STATES = (
        (SurveyStates.REQUESTED, "Requested"),
        (SurveyStates.STARTED, "Started"),
        (SurveyStates.COMPLETED, "Completed"))
    registry = models.ForeignKey(Registry)
    survey_name = models.CharField(max_length=80)
    patient_token = models.CharField(max_length=80, unique=True)
    state  = models.CharField(max_length=20, choices=SURVEY_STATES)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    response = models.TextField(blank=True, null=True)


def generate_token():
       return str(uuid.uuid4())

class SurveyRequest(models.Model):
    """
    This gets created on the clinical system
    """
    SURVEY_REQUEST_STATES = (
        (SurveyRequestStates.CREATED, "Created"),
        (SurveyRequestStates.REQUESTED, "Requested"),
        (SurveyRequestStates.RECEIVED, "Received"))
    registry = models.ForeignKey(Registry)
    patient = models.ForeignKey(Patient)
    survey_name = models.CharField(max_length=80, default="bp")
    patient_token = models.CharField(max_length=80, unique=True, default=generate_token)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user = models.CharField(max_length=80) # username
    state  = models.CharField(max_length=20, choices=SURVEY_REQUEST_STATES, default="created")
    response = models.TextField(blank=True, null=True)


