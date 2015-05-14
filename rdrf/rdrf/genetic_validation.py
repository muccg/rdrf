import logging
from registry.humangenome.exon import ExonVariation
from registry.humangenome.protein import ProteinVariation
from registry.humangenome.sequence import SequenceVariation

logger = logging.getLogger("registry_log")


class GeneticType:
    EXON = "exon"
    DNA = "dna"
    PROTEIN = "protein"
    RNA = "rna"


class GeneticValidationError(Exception):
    pass


class GeneticValidator(object):

    def validate(self, value, genetic_type):
        logger.debug("genetic registry about to validate value: %s genetic type: %s" % (value, genetic_type))
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
            logger.debug("parse_func is None?")
            return False

        try:
            parsed_value = parse_func(value)
            logger.debug("parsed OK")
            return True

        except GeneticValidationError, gv_err:
            logger.debug("%s could not parse %s: parser error = %s" % (parse_func, value, gv_err))
            return False

        except Exception, ex:
            logger.error("parse func %s on value %s threw error: %s" % (parse_func, value, ex))

        return False

    # The following methods are taken from the old framework code - later we should use hgvs parser?
    def validate_exon(self, value):
        try:
            return ExonVariation(value)
        except ExonVariation.Error, e:
            raise GeneticValidationError("Exon validation error: %s" % e)

    def validate_protein(self, value):
        try:
            return ProteinVariation(value)
        except ProteinVariation.Error, e:
            raise GeneticValidationError("Protein validation error: %s" % e)

    def validate_sequence(self, value):
        try:
            return SequenceVariation(value)
        except SequenceVariation.Error, e:
            raise GeneticValidationError("Sequence validation error: %s" % e)
