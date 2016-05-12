from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from rdrf.models import Registry


class Query(models.Model):
    MONGO_SEARCH_TYPES = (
        ('C', 'Current'),
        ('L', 'Longitudinal'),
        ('M', 'Mixed'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    registry = models.ForeignKey(Registry)
    access_group = models.ManyToManyField(Group)

    mongo_search_type = models.CharField(max_length=1, choices=MONGO_SEARCH_TYPES, default='C')

    collection = models.CharField(max_length=255, default="cdes")
    criteria = models.TextField(blank=True, null=True)
    projection = models.TextField(blank=True, null=True)
    aggregation = models.TextField(blank=True, null=True)

    sql_query = models.TextField()
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    max_items = models.IntegerField(default=3) # max number of multisection items to show in datatable

    def get_absolute_url(self):
        return reverse('explorer_query', kwargs={'query_id': self.pk})

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'Queries'

    def __unicode__(self):
        return unicode(self.title)

    def has_view(self):
        return self.mongo_search_type in ['C', 'L']

    def clean(self):
        if self.mongo_search_type == "M":
            errors = self._get_mixed_query_errors()
            if len(errors) > 0:
                error_string = ",".join(errors)
                raise ValidationError("Report Config Errors: %s" % error_string)

    def _get_mixed_query_errors(self):
        import json
        errors = []
        try:
            data = json.loads(self.sql_query)
            static_sheets = data["static_sheets"]
            for sheet in static_sheets:
                sheet_name = sheet["name"]
                columns = sheet["columns"]
                for column in columns:
                    if not isinstance(column, basestring):
                        errors.append("columns in sheet %s not all strings: %s" % (sheet_name, column))
                            
        except ValueError, ve:
            errors.append("JSON malformed: %s" % ve.message)
        except KeyError, ke:
            errors.append("key error: %s" % ke.message)
        return errors

 
