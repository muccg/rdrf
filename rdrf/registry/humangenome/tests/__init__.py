from . import test_exon
from . import test_protein
from . import test_sequence

from unittest import TestSuite, defaultTestLoader


suite = TestSuite()
suite.addTest(defaultTestLoader.loadTestsFromModule(test_exon))
suite.addTest(defaultTestLoader.loadTestsFromModule(test_protein))
suite.addTest(defaultTestLoader.loadTestsFromModule(test_sequence))
