from django.db import models
import logging
logger = logging.getLogger("registry")


def get_owner_choices():
    """
    Get choices for CDE owner drop down.
    Used to get the list of classes which CDEs can be attached to.
    UNUSED means this CDE will not be used to construct any forms in the registry.

    """
    from django.conf import settings
    choices = [('UNUSED', 'UNUSED')]
    # for display_name, owner_model_func in settings.CDE_MODEL_MAP.items():
    #     owner_class_name = owner_model_func().__name__
    #     choices.append((owner_class_name, display_name))

    return [("UNUSED","UNUSED"), ("USED", "USED")]

class CDEPermittedValueGroup(models.Model):
    code = models.CharField(max_length=250, primary_key=True)

    def __unicode__(self):
        return "PVG %s" % (self.code)

class CDEPermittedValue(models.Model):
    code = models.CharField(max_length=30, primary_key=True)
    value = models.CharField(max_length=256)
    desc = models.TextField(null=True)
    pv_group = models.ForeignKey(CDEPermittedValueGroup, related_name='permitted_value_set')

    def __unicode__(self):
        return "PV %s:%s of %s" % (self.code,self.value,self.pv_group)

class CommonDataElement(models.Model):
    code = models.CharField(max_length=30, primary_key=True)
    name = models.CharField(max_length=250, blank=False)
    desc = models.TextField()
    datatype = models.CharField(max_length=50)
    instructions = models.TextField()
    references = models.TextField()
    population = models.CharField(max_length=250)
    classification = models.CharField(max_length=250)
    version = models.CharField(max_length=50)
    version_date = models.DateField()
    variable_name = models.CharField(max_length=250)
    aliases_for_variable_name = models.CharField(max_length=250)
    crf_module = models.CharField(max_length=250)
    subdomain = models.CharField(max_length=250)
    domain = models.CharField(max_length=250)
    pv_group = models.ForeignKey(CDEPermittedValueGroup, null=True, blank=True)

    OWNER_CHOICES = get_owner_choices()

    owner = models.CharField(max_length=50, choices=OWNER_CHOICES, default="UNUSED")

    def __unicode__(self):
        return "CDE %s:%s" % (self.code, self.name)


class RegistryForm(models.Model):
    """
    A representation of a form ( a bunch of sections)
    """
    registry = models.CharField(max_length=50)
    name = models.CharField(max_length=80)
    sections = models.TextField(help_text="Comma-separated list of sections")


class Section(models.Model):
    """
    A group of fields that appear on a form as a unit
    """
    code = models.CharField(max_length=50)
    elements = models.TextField()


class Wizard(models.Model):
    registry = models.CharField(max_length=50)
    forms = models.TextField(help_text="A comma-separated list of forms")
    # idea
    # rules for "decision tree"
    # These could be as simple as the following:
    # A wizard is a way of coordinating the asking of questions and evaluating
    # answers -

    #  E.g. in pseudo-code ( we either present a gui to create rules like this
    # or write an interpreter
    #  present form1.
    #  if form1.section1.cde2 == 3 and section2.cde >6  then present form3
    #  if form1.section2.cde2 == 4 then present form5
    #  else present form6
    #
    rules = models.TextField(help_text="Rules")


class CalculatedField(models.Model):
    code = models.CharField(max_length=50)
    registry = models.CharField(max_length=50)
    form_name = models.CharField(max_length=50)
    calculation = models.TextField()









