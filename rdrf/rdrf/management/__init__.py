#  Initially I had this in a file management.py , which didn't work
# but then I read http://kencochrane.blogspot.com.au/2009/03/django-notification-creating-notice.html
from django.conf import settings
from django.db.models import signals
from django.utils.translation import ugettext_noop as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("adjudication_decision", _("Adjudication Decided"), _("your adjudication request has been decided"))
        notification.create_notice_type("adjudication_request", _("Adjudication Requested"), _("you have received an N adjudication request"))
        notification.create_notice_type("adjudication_results_ready", _("Adjudication Results Ready"), _("adjudication results are ready to review"))
        notification.create_notice_type("patient_reminder", _("Data Update Requested"), _("please update your data"))
        notification.create_notice_type("patient_welcome", _("Welcome to the registry!"), _("welcome message"))

    signals.post_syncdb.connect(create_notice_types, sender=notification)
else:
    print "Skipping creation of NoticeTypes as notification app not found"