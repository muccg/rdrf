from .exon import ExonVariation
from .protein import ProteinVariation
from .sequence import SequenceVariation


def parse_variation(input):
    try:
        return SequenceVariation(input)
    except SequenceVariation.Malformed:
        # Might be an exon.
        return ExonVariation(input)
    except SequenceVariation.Protein:
        return ProteinVariation(input)
