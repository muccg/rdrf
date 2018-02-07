import unittest
from registry.humangenome.exon import *


class TestExonVariation(unittest.TestCase):
    def test_fail_deletion(self):
        self.assertRaises(Variation.Malformed, lambda: ExonVariation("42delA"))

    def test_fail_duplication(self):
        self.assertRaises(Variation.Malformed, lambda: ExonVariation("42dupA"))

    def test_fail_position(self):
        self.assertRaises(Position.Malformed, lambda: Position("foo"))
        self.assertRaises(Position.Malformed, lambda: Position("42x"))
        self.assertRaises(Position.Malformed, lambda: Position("i"))

    def test_fail_range(self):
        self.assertRaises(Range.Malformed, lambda: Range("42"))
        self.assertRaises(Position.Malformed, lambda: Range("42_"))
        self.assertRaises(Position.Malformed, lambda: Range("_42"))
        self.assertRaises(Position.Malformed, lambda: Range("42i_i"))

    def test_fail_variation(self):
        # Generic variations that should fail to pass.
        self.assertRaises(Variation.Malformed, lambda: ExonVariation("42x"))
        self.assertRaises(Variation.Malformed, lambda: ExonVariation("42ins"))
        self.assertRaises(Variation.Malformed, lambda: ExonVariation("x"))

    def test_parse_deletion(self):
        ev = ExonVariation("42del")
        self.assertEqual(ev.gene, None, "Gene is set")
        self.assertTrue(
            isinstance(
                ev.variations[0],
                Deletion),
            "Variation object is the wrong type")
        self.assertEqual(ev.variations[0].location.position,
                         42, "Variation position is incorrect")
        self.assertEqual(str(ev), "42del", "Exon variation string is incorrect")

    def test_parse_duplication(self):
        ev = ExonVariation("42dup")
        self.assertEqual(ev.gene, None, "Gene is set")
        self.assertTrue(
            isinstance(
                ev.variations[0],
                Duplication),
            "Variation object is the wrong type")
        self.assertEqual(ev.variations[0].location.position,
                         42, "Variation position is incorrect")
        self.assertEqual(str(ev), "42dup", "Exon variation string is incorrect")

    def test_parse_nochange(self):
        ev = ExonVariation("42")
        self.assertEqual(ev.gene, None, "Gene is set")
        self.assertTrue(
            isinstance(
                ev.variations[0],
                NoChange),
            "Variation object is the wrong type")
        self.assertEqual(ev.variations[0].location.position,
                         42, "Variation position is incorrect")
        self.assertEqual(str(ev), "42", "Exon variation string is incorrect")

        ev = ExonVariation("42i_43")
        self.assertEqual(ev.gene, None, "Gene is set")
        self.assertTrue(
            isinstance(
                ev.variations[0],
                NoChange),
            "Variation object is the wrong type")
        self.assertEqual(str(ev), "42i_43", "Exon variation string is incorrect")

        ev = ExonVariation("DMD:42")
        self.assertEqual(ev.gene.gene, "DMD", "Gene is not set")
        self.assertTrue(
            isinstance(
                ev.variations[0],
                NoChange),
            "Variation object is the wrong type")
        self.assertEqual(ev.variations[0].location.position,
                         42, "Variation position is incorrect")
        self.assertEqual(str(ev), "DMD:42", "Exon variation string is incorrect")

        ev = ExonVariation("exon42")
        self.assertEqual(ev.gene, None, "Gene is set")
        self.assertTrue(
            isinstance(
                ev.variations[0],
                NoChange),
            "Variation object is the wrong type")
        self.assertEqual(ev.variations[0].location.position,
                         42, "Variation position is incorrect")
        self.assertEqual(str(ev), "42", "Exon variation string is incorrect")

    def test_parse_position(self):
        position = Position("42")
        self.assertFalse(position.intron, "Position intron is true")
        self.assertFalse(position.neuron, "Position neuron is true")
        self.assertEqual(position.position, 42, "Position is not 42")
        self.assertFalse(position.uncertain, "Position is uncertain")
        self.assertEqual(str(position), "42", "Position string is incorrect")

        position = Position("42i")
        self.assertTrue(position.intron, "Position intron is false")
        self.assertFalse(position.neuron, "Position neuron is true")
        self.assertEqual(position.position, 42, "Position is not 42")
        self.assertFalse(position.uncertain, "Position is uncertain")
        self.assertEqual(str(position), "42i", "Position string is incorrect")

        position = Position("42c")
        self.assertFalse(position.intron, "Position intron is true")
        self.assertTrue(position.neuron, "Position neuron is false")
        self.assertEqual(position.position, 42, "Position is not 42")
        self.assertFalse(position.uncertain, "Position is uncertain")
        self.assertEqual(str(position), "42c", "Position string is incorrect")

        position = Position("42ci")
        self.assertTrue(position.intron, "Position intron is false")
        self.assertTrue(position.neuron, "Position neuron is false")
        self.assertEqual(position.position, 42, "Position is not 42")
        self.assertFalse(position.uncertain, "Position is uncertain")
        self.assertEqual(str(position), "42ci", "Position string is incorrect")

        position = Position("(42i)")
        self.assertTrue(position.intron, "Position intron is false")
        self.assertFalse(position.neuron, "Position neuron is true")
        self.assertEqual(position.position, 42, "Position is not 42")
        self.assertTrue(position.uncertain, "Position is certain")
        self.assertEqual(str(position), "(42i)", "Position string is incorrect")

    def test_parse_range(self):
        range = Range("42_43")
        self.assertFalse(range.start.intron, "Position intron is true")
        self.assertFalse(range.start.neuron, "Position neuron is true")
        self.assertEqual(range.start.position, 42, "Position is not 42")
        self.assertEqual(range.start.uncertain, False, "Position is uncertain")
        self.assertFalse(range.end.intron, "Position intron is true")
        self.assertFalse(range.end.neuron, "Position neuron is true")
        self.assertEqual(range.end.position, 43, "Position is not 43")
        self.assertEqual(range.end.uncertain, False, "Position is uncertain")
        self.assertEqual(str(range), "42_43", "Range string is incorrect")

        range = Range("42i_43c")
        self.assertTrue(range.start.intron, "Position intron is false")
        self.assertFalse(range.start.neuron, "Position neuron is true")
        self.assertEqual(range.start.position, 42, "Position is not 42")
        self.assertEqual(range.start.uncertain, False, "Position is uncertain")
        self.assertFalse(range.end.intron, "Position intron is true")
        self.assertTrue(range.end.neuron, "Position neuron is false")
        self.assertEqual(range.end.position, 43, "Position is not 43")
        self.assertEqual(range.end.uncertain, False, "Position is uncertain")
        self.assertEqual(str(range), "42i_43c", "Range string is incorrect")

        range = Range("(42i)_43c")
        self.assertTrue(range.start.intron, "Position intron is false")
        self.assertFalse(range.start.neuron, "Position neuron is true")
        self.assertEqual(range.start.position, 42, "Position is not 42")
        self.assertEqual(range.start.uncertain, True, "Position is certain")
        self.assertFalse(range.end.intron, "Position intron is true")
        self.assertTrue(range.end.neuron, "Position neuron is false")
        self.assertEqual(range.end.position, 43, "Position is not 43")
        self.assertEqual(range.end.uncertain, False, "Position is uncertain")
        self.assertEqual(str(range), "(42i)_43c", "Range string is incorrect")
