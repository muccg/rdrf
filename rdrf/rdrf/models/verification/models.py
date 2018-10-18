from django.db import models
from django.utils.translation import ugettext as _

class Annotation(models.Model):
    class Meta:
        app_label = "rdrf"

    ANNOTATION_TYPES = (("verified", _("Verified")),
                        ("corrected", _("Corrected")))

    annotation_type = models.CharField(max_length=80, db_index=True, choices=ANNOTATION_TYPES)
    patient_id = models.IntegerField(db_index=True)
    context_id = models.IntegerField(db_index=True, blank=True, null=True)
    registry_code = models.CharField(max_length=10)
    form_name = models.CharField(max_length=80)
    section_code = models.CharField(max_length=100)
    item = models.IntegerField(null=True)
    cde_code = models.CharField(max_length=30)
    cde_value = models.TextField()    # holds the corrected value if corrected by a clinician or the original value if verified
    orig_value = models.TextField()   # holds the original patient value
    username = models.CharField(max_length=254)   # user who created this annotation
    timestamp = models.DateTimeField(auto_now_add=True)
    comment = models.TextField()

    @staticmethod
    def score(klass, registry_model, patient_model):
        query = Annotation.objects.filter(patient_id=patient_model.id,
                                          registry_code=registry_model.code)
        num = query.count()
        num_verified = query.filter(annotation_type="verified").count()
        try:
            return 100.00 * (float(num_verified) / float(num))
        except ZeroDivisionError:
            return None
