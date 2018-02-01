import unittest
from registry.humangenome.protein import *


class TestProteinVariation(unittest.TestCase):
    def test_fail_deletion(self):
        self.assertRaises(Variation.Malformed, lambda: ProteinVariation("p.Trp42delTp"))

    def test_fail_duplication(self):
        self.assertRaises(Variation.Malformed, lambda: ProteinVariation("p.Trp42dupTp"))

    def test_fail_insertion(self):
        self.assertRaises(Variation.Malformed, lambda: ProteinVariation("p.Trp42ins"))
        self.assertRaises(Variation.Malformed, lambda: ProteinVariation("p.Trp42insTp"))

    def test_fail_position(self):
        self.assertRaises(Position.Malformed, lambda: Position("Tp42"))
        self.assertRaises(Position.Malformed, lambda: Position("(T42"))
        self.assertRaises(Position.Malformed, lambda: Position("2*2"))

    def test_fail_range(self):
        self.assertRaises(ProteinVariation.Malformed, lambda: Range("Trp2_Trp3_"))
        self.assertRaises(ProteinVariation.Malformed, lambda: Range("Trp2"))
        self.assertRaises(ProteinVariation.Malformed, lambda: Range("(Trp2_Trp3"))

    def test_fail_substitution(self):
        self.assertRaises(Variation.Malformed, lambda: ProteinVariation("p.Trp42"))
        self.assertRaises(Variation.Malformed, lambda: ProteinVariation("p.Trp42Cy"))

    def test_parse_deletion(self):
        input = "p.Trp42del"
        seq = ProteinVariation(input)

        self.assertEqual(seq.type.type, "p", "Sequence variation type is not protein")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Deletion), "Variation is not a deletion")
        self.assertEqual(variation.deletion, None, "Deletion is not None")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(str(location), "Trp42", "Location is incorrect")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_duplication(self):
        input = "p.Trp42dup"
        seq = ProteinVariation(input)

        self.assertEqual(seq.type.type, "p", "Sequence variation type is not protein")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Duplication), "Variation is not a duplication")
        self.assertEqual(variation.duplication, None, "Duplication is not None")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(str(location), "Trp42", "Location is incorrect")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_insertion(self):
        input = "p.Trp42insGlnSer"
        seq = ProteinVariation(input)

        self.assertEqual(seq.type.type, "p", "Sequence variation type is not protein")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Insertion), "Variation is not an insertion")
        self.assertEqual(variation.insertion, "GlnSer", "Inserted amino acids are not GlnSer")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(str(location), "Trp42", "Location is incorrect")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_position(self):
        def assertPosition(
                string,
                acid,
                position,
                intron_offset,
                uncertain,
                stop_codon,
                unknown):
            location = ProteinVariation("p.%sdel" % string).alleles[0].variations[0].location

            self.assertTrue(isinstance(location, Position), "Location is not a Position")
            self.assertEqual(location.unknown, unknown, "Position's unknown flag is incorrect")
            self.assertEqual(
                location.stop_codon,
                stop_codon,
                "Position's stop codon flag is incorrect")
            self.assertEqual(
                location.uncertain,
                uncertain,
                "Position's uncertainty flag is incorrect")
            self.assertEqual(
                location.intron_offset,
                intron_offset,
                "Position's intron offset is incorrect")
            self.assertEqual(location.amino_acid, acid, "Position's amino acid is incorrect")
            self.assertEqual(location.position, position, "Position's position is incorrect")
            self.assertEqual(
                str(location),
                string,
                "Position's string representation is incorrect")

        assertPosition("Trp42", "Trp", 42, None, False, False, False)
        assertPosition("?", None, None, None, False, False, True)
        assertPosition("Trp*42", "Trp", 42, None, False, True, False)
        assertPosition("(Trp42)", "Trp", 42, None, True, False, False)
        assertPosition("Trp42-2", "Trp", 42, -2, False, False, False)
        assertPosition("Trp42+2", "Trp", 42, 2, False, False, False)
        assertPosition("(Trp42+0)", "Trp", 42, 0, True, False, False)
        assertPosition("(?)", None, None, None, True, False, True)
        assertPosition("(Trp*42-2)", "Trp", 42, -2, True, True, False)

    def test_parse_range(self):
        range = Range("Trp2_Gly3")

        self.assertEqual(str(range.start), "Trp2", "Start is not Trp2")
        self.assertEqual(str(range.end), "Gly3", "End is not Gly3")
        self.assertEqual(str(range), "Trp2_Gly3", "Range output does not match input")

        range = Range("(Trp2_Gly3)")

        self.assertTrue(range.uncertain, "Range is uncertain")
        self.assertEqual(str(range), "(Trp2_Gly3)", "Range output does not match input")

    def test_parse_substitution(self):
        input = "p.Trp42Cys"
        seq = ProteinVariation(input)

        self.assertEqual(seq.type.type, "p", "Sequence variation type is not protein")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Substitution), "Variation is not an subsitution")
        self.assertEqual(variation.new, "Cys", "variation.new is not Cys")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(str(location), "Trp42", "Location is incorrect")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")


# TODO: Tests for multiple alleles, multiple variations, mosaicism, uncertain
# alleles, indels, complex variations, conversions, triplication and
# quadruplication, and probably lots more besides.
