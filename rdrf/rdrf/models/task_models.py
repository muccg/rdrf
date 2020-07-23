from django.db import models
from registry.groups.models import CustomUser
from registry.patients.models import Patient


class CustomActionExecution(models.Model):
    """
    Record info about a custom action being run.
    Custom actions may be asynchronous in which case we
    store some task related info
    """
    custom_action_code = models.CharField(max_length=80, blank=True, null=True)
    task_id = models.CharField(max_length=80, blank=True, null=True)
    name = models.CharField(max_length=80)
    user = models.ForeignKey(CustomUser, help_text="The user who executed the action", on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=80, blank=True, null=True)
    patient = models.ForeignKey(Patient, null=True, on_delete=models.PROTECT)
    download_filepath = models.CharField(max_length=100,)
    downloaded = models.BooleanField(default=False)
    downloaded_time = models.DateTimeField(null=True)
    task_result = models.TextField(blank=True)
    error_string = models.TextField(blank=True)
    input_data = models.TextField(blank=True)
    runtime = models.IntegerField(null=True, help_text="Runtime in seconds")
