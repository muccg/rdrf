from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from registry.configuration.models import EmailTemplate

import os.path


def default_return_email():
    return getattr(settings, "RETURN_EMAIL", "noreply@ccg.murdoch.edu.au")

def sendNewPatientEmail(recipients, from_email=None):
    if not from_email:
        from_email = default_return_email()

    template = getNewPatientEmailTemplate()
    groups = template.groups.all()
    to_email = recipients.filter(user__groups__in=groups).distinct().values_list("user__email", flat=True)

    subject = '%s: new patient registered' % settings.INSTALL_NAME.upper()
    body = template.body

    try:
        send_mail(subject, body, from_email, to_email, fail_silently = False)
    except Exception, e:
        print 'Error sending mail to user: ',to_email , ':', str(e)

def getNewPatientEmailTemplate():
    #target=1 -> registry.configuration.models.EmailTemplate.TARGETS
    return EmailTemplate.objects.get(target=1)