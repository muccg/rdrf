from django.db import models

import logging
logger = logging.getLogger('genetic')


class Gene(models.Model):
    symbol = models.TextField()
    hgnc_id = models.TextField(verbose_name="HGNC ID")
    name = models.TextField()
    status = models.TextField()
    chromosome = models.TextField()
    accession_numbers = models.TextField()
    refseq_id = models.TextField(verbose_name="RefSeq ID")

    class Meta:
        ordering = ["symbol"]

    def __str__(self):
        return "%s (%s)" % (self.symbol, self.name)


class Technique(models.Model):
    name = models.CharField(max_length=50, primary_key=True)

    def __str__(self):
        return str(self.name)


class Laboratory(models.Model):

    """
    Laboratory is a model for preset values of "laboratory site"
    fields.
    """
    name = models.CharField(max_length=256)
    address = models.TextField(max_length=200, blank=True)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "laboratories"

    def __str__(self):
        val = self.name
        return val
