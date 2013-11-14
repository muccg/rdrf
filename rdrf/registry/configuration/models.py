from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.files.storage import FileSystemStorage

file_system = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)

class Module(models.Model):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return '%s (%s)' % (self.name, self.code)

class EmailTemplate(models.Model):
    TARGETS = (
        (1, 'New patient registered'),
    )
    name = models.CharField(max_length=50)
    target = models.IntegerField(choices = TARGETS)
    description = models.CharField(max_length=100, null=True, blank=True)
    body = models.TextField()
    groups = models.ManyToManyField(Group)
    
    def __unicode__(self):
        return '%s' % (self.name)

class ConsentForm(models.Model):
    COUNTRIES = (
        ('AU', 'Australia'),
        ('NZ', 'New Zealand')
    )
    country = models.CharField(max_length=2, choices=COUNTRIES, blank=False, null=False)
    form = models.FileField(upload_to='consents', storage=file_system, verbose_name="Consent form", blank=True, null=True)
    module = models.ForeignKey(Module, blank=False, null=False)