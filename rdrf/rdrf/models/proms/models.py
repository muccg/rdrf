from django.db import models
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import CommonDataElement

class Survey(models.Model):
    registry = models.ForeignKey(Registry)
    name = models.CharField(max_length=80)

    @property
    def client_rep(self):
        return [ sq.client_rep for sq in self.survey_questions.all().order_by('position')]

    def __str__(self):
        return "%s Survey: %s" % (self.registry.code, self.name) 

    
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
                     "options": self._get_options() }
                    
        else:
            return { "tag": "cond",
                     "cde": self.cde.code,
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
    COMPLETED = "completed"

class SurveyAssignment(models.Model):
    SURVEY_STATES = (
        (SurveyStates.REQUESTED, "Requested"),
        (SurveyStates.COMPLETED, "Completed"))
    registry = models.ForeignKey(Registry)
    survey_name = models.CharField(max_length=80)
    patient_token = models.CharField(max_length=80)
    state  = models.CharField(max_length=20, choices=SURVEY_STATES)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)



class SurveyResponse(models.Model):
    registry = models.ForeignKey(Registry)
    survey_name = models.CharField(max_length=80)
    created = models.DateTimeField(auto_now_add=True)
    patient_token = models.CharField(max_length=80)
    data = models.TextField()
