from django.db import models
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import CommonDataElement
from registry.patients.models import Patient
from rdrf.services.io.notifications.notifications import Notifier
from rdrf.services.io.notifications.notifications import NotificationError
import requests
import uuid
import logging

logger = logging.getLogger(__name__)

class PromsRequestError(Exception):
    pass

class PromsEmailError(Exception):
    pass


class Survey(models.Model):
    registry = models.ForeignKey(Registry)
    name = models.CharField(max_length=80)
    display_name = models.CharField(max_length=80, blank=True, null=True)

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

    def send(self):
        if self.state == SurveyRequestStates.CREATED:
            try:
                self._send_proms_request()
            except PromsRequestError as pre:
                logger.error("Error sending survey request %s: %s" % (self.pk,
                                                                      pre))
                return False


            try:
                self._send_email()
                return True
            except PromsEmailError as pe:
                logger.error("Error emailing survey request %s: %s" % (self.pk,
                                                                       pe))
                return False

    def _send_proms_request(self):
        from django.core.urlresolvers import reverse
        from django.conf import settings

        logger.debug("sending request to proms system")
        proms_system_url = self.registry.metadata.get("proms_system_url", None)
        if proms_system_url is None:
            raise PromsRequestError("No proms_system_url defined in registry metadata %s" % self.registry.code)

        api = reverse("survey_assignments")
        
        logger.debug("api = %s" % api)

        api_url = proms_system_url + api

        survey_assignment_data = self._get_survey_assignment_data()
        headers = {'PROMS_SECRET_TOKEN': settings.PROMS_SECRET_TOKEN}

        requests.post(api_url,
                      data=survey_assignment_data,
                      headers=headers)

    def _get_survey_assignment_data(self):
        packet = {}
        packet["registry_code"] = self.registry.code
        packet["survey_name"] = self.survey_name
        packet["patient_token"] = self.patient_token
        packet["state"] = "requested"
        return packet

    @property
    def email_link(self):
        #https://rdrf.ccgapps.com.au/cicproms/promslanding?t=foo23&r=ICHOMCRC&s=smap
        proms_system_url = self.registry.proms_system_url

        landing_page = "/promslanding?t=%s&r=%s&s=%s" % (self.patient_token,
                                                         self.registry.code,
                                                         self.survey_name)

        return proms_system_url + landing_page


    @property
    def name(self):
        return "%s %s Survey" % (self.registry.name,
                                 self.survey_name)
                                 
        
    

    def _send_email(self):
        logger.debug("sending email to user with link")
        try:
            emailer = Notifier()
            subject_line = "%s %s Survey Request" % (self.registry.name,
                                                     self.survey_name)
            email_body = "Please use the following link to take the %s survey: %s" % (self.name,
                                                                                      self.email_link)
            
            emailer.send_email(self.patient.email,
                               subject_line,
                               email_body)

        except NotificationError as nerr:
            raise PromsEmailError(nerr)
        except Exception as ex:
            raise PromsEmailError(ex)
            
            
        
        
        

        
        
                
                

                
            




