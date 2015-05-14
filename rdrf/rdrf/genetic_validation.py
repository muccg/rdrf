import hgvs.parser
from ometa.runtime import ParseError
import logging

logger = logging.getLogger("registry_log")

class GeneticType:
    EXON = "exon"
    DNA = "dna"
    PROTEIN = "protein"
    RNA = "rna"


class GeneticValidator(object):
    def __init__(self):
        self.parser = hgvs.parser.Parser()

    def validate(self, value, genetic_type):
        logger.debug("genetic registry about to validate value: %s genetic type: %s" % (value, genetic_type))
        parse_func = None
        if genetic_type == GeneticType.DNA:
            parse_func = self.parser.parse_hgvs_variant   # correct ?
        elif genetic_type == GeneticType.EXON:
            parse_func = self.parser.parse_hgvs_variant   # correct ?
        elif genetic_type == GeneticType.PROTEIN:
            parse_func = self.parser.parse_hgvs_variant   # correct ?
        elif genetic_type == GeneticType.RNA:
            parse_func = self.parser.parse_hgvs_variant   # correct ?

        if parse_func is None:
            logger.debug("parse_func is None?")
            return False

        try:
            parsed_value = parse_func(value)
            logger.debug("parsed OK")
            return True

        except ParseError, parse_err:
            logger.debug("%s could not parse %s: parser error = %s" % (parse_func, value, parse_err))
            return False

        except Exception, ex:
            logger.debug("parse func %s on value %s threw error: %s" % (parse_func, value, ex))

        return False