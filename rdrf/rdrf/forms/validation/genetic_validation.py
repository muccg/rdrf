from django.utils.translation import ugettext as _

import logging
from registry.humangenome.exon import ExonVariation
from registry.humangenome.protein import ProteinVariation
from registry.humangenome.sequence import SequenceVariation

logger = logging.getLogger(__name__)


class GeneticType:
    EXON = "exon"
    DNA = "dna"
    PROTEIN = "protein"
    RNA = "rna"


class GeneticValidationError(Exception):
    pass


class GeneticValidator(object):

    def validate(self, value, genetic_type):
        parse_func = None
        if genetic_type == GeneticType.DNA:
            parse_func = self.validate_sequence
        elif genetic_type == GeneticType.EXON:
            parse_func = self.validate_exon
        elif genetic_type == GeneticType.PROTEIN:
            parse_func = self.validate_protein
        elif genetic_type == GeneticType.RNA:
            parse_func = self.validate_sequence     # ?????!

        if parse_func is None:
            return False

        try:
            parse_func(value)
            return True

        except GeneticValidationError:
            return False

        except Exception as ex:
            logger.error("parse func %s on value %s threw error: %s" % (parse_func, value, ex))

        return False

    # The following methods are taken from the old framework code - later we
    # should use hgvs parser?
    def validate_exon(self, value):
        try:
            return ExonVariation(value)
        except ExonVariation.Error as e:
            raise GeneticValidationError(_("Exon validation error: %(error)s") % {"error": e})

    def validate_protein(self, value):
        try:
            return ProteinVariation(value)
        except ProteinVariation.Error as e:
            raise GeneticValidationError(
                _("Protein validation error: %(error)s") % {
                    "error": e})

    def validate_sequence(self, value):
        try:
            return SequenceVariation(value)
        except SequenceVariation.Error as e:
            raise GeneticValidationError(
                _("Sequence validation error: %(error)s") % {
                    "error": e})
