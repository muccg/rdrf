import unittest
from registry.humangenome.sequence import *


class TestSequenceVariation(unittest.TestCase):
    def assertEqual(self, first, second, *args, **kwargs):
        try:
            super(TestSequenceVariation, self).assertEqual(first, second, *args, **kwargs)
        except BaseException:
            print(first, second)
            raise

    def test_fail_deletion(self):
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42delX"))
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42delGG"))

    def test_fail_duplication(self):
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42dupX"))
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42dupGG"))

    def test_fail_insertion(self):
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42ins"))
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42insX"))

    def test_fail_position(self):
        self.assertRaises(Position.Malformed, lambda: Position("foo"))
        self.assertRaises(Position.Malformed, lambda: Position("(1"))
        self.assertRaises(Position.Malformed, lambda: Position("2*2"))
        self.assertRaises(Position.Malformed, lambda: Position("+3"))

    def test_fail_range(self):
        self.assertRaises(SequenceVariation.Malformed, lambda: Range("2_3_"))
        self.assertRaises(SequenceVariation.Malformed, lambda: Range("2"))
        self.assertRaises(SequenceVariation.Malformed, lambda: Range("(2_3"))

    def test_fail_substitution(self):
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42GG>A"))
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42G>AA"))
        self.assertRaises(Variation.Malformed, lambda: SequenceVariation("c.42A>X"))

    def test_parse_deletion_with_base(self):
        input = "c.42delG"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Deletion), "Variation is not a deletion")
        self.assertEqual(variation.deletion, "G", "Deletion is not G")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_deletion_without_base(self):
        input = "c.42del"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Deletion), "Variation is not a deletion")
        self.assertEqual(variation.deletion, None, "Deletion is not None")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_duplication_with_base(self):
        input = "c.42dupG"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Duplication), "Variation is not a duplication")
        self.assertEqual(variation.duplication, "G", "Duplication is not G")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_duplication_without_base(self):
        input = "c.42dup"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Duplication), "Variation is not a duplication")
        self.assertEqual(variation.duplication, None, "Duplication is not None")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_insertion(self):
        input = "c.42insACGT"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Insertion), "Variation is not an insertion")
        self.assertEqual(variation.insertion, "ACGT", "Inserted nucleotides are not ACGT")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_inversion(self):
        input = "c.42inv"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Inversion), "Variation is not an inversion")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_nochange(self):
        input = "c.(=)"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, NoChange), "Variation is not no change")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_position(self):
        def assertPosition(
                string,
                position,
                intron_offset,
                uncertain,
                stop_codon,
                unknown,
                intron_offset_unknown):
            location = SequenceVariation("c.%sinv" % string).alleles[0].variations[0].location

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
            self.assertEqual(
                location.intron_offset_unknown,
                intron_offset_unknown,
                "Position's intron offset unknown flag is incorrect")
            self.assertEqual(location.position, position, "Position's position is incorrect")
            self.assertEqual(
                str(location),
                string,
                "Position's string representation is incorrect")

        assertPosition("42", 42, None, False, False, False, None)
        assertPosition("?", None, None, False, False, True, None)
        assertPosition("*42", 42, None, False, True, False, None)
        assertPosition("(42)", 42, None, True, False, False, None)
        assertPosition("42-2", 42, -2, False, False, False, None)
        assertPosition("42+2", 42, 2, False, False, False, None)
        assertPosition("(42+0)", 42, 0, True, False, False, None)
        assertPosition("(?)", None, None, True, False, True, None)
        assertPosition("(*42-2)", 42, -2, True, True, False, None)
        assertPosition("-42", -42, None, False, False, False, None)
        assertPosition("42+?", 42, None, False, False, False, 1)
        assertPosition("42-?", 42, None, False, False, False, -1)

    def test_parse_range(self):
        range = Range("2_3")

        self.assertEqual(str(range.start), "2", "Start is not 2")
        self.assertEqual(str(range.end), "3", "End is not 3")
        self.assertEqual(str(range), "2_3", "Range output does not match input")

        range = Range("2+1_(*3)")

        self.assertEqual(str(range.start), "2+1", "Start is not 2+1")
        self.assertEqual(str(range.end), "(*3)", "End is not (*3)")
        self.assertEqual(str(range), "2+1_(*3)", "Range output does not match input")

        range = Range("(2_3)")

        self.assertTrue(range.uncertain, "Range is uncertain")
        self.assertEqual(str(range), "(2_3)", "Range output does not match input")

        range = Range("2+1_3-1")

        self.assertEqual(str(range), "2+1_3-1", "Range output does not match input")

    def test_parse_substitution(self):
        input = "c.42A>G"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 1, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Substitution), "Variation is not an subsitution")
        self.assertEqual(variation.old, "A", "variation.old is not A")
        self.assertEqual(variation.new, "G", "variation.old is not G")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        self.assertEqual(str(seq), input, "Sequence variation as string does not match input")

    def test_parse_substitution_with_old_style_mosaic(self):
        input = "c.[=,42A>G]"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 2, "Allele does not have 1 variation")

        variation = allele.variations[1]

        self.assertTrue(isinstance(variation, Substitution), "Variation is not an subsitution")
        self.assertEqual(variation.old, "A", "variation.old is not A")
        self.assertEqual(variation.new, "G", "variation.old is not G")

        location = variation.location

        self.assertTrue(isinstance(location, Position), "Location is not a single position")
        self.assertEqual(location.position, 42, "Location is not the answer")

        # not sure if string of seq should include [ and ] - at present it does not so this fails
        #self.assertEqual(unicode(seq), input, "Sequence variation as string does not match input")

    def test_parse_substitution_delins(self):
        input = "c.112_117delinsTG"
        seq = SequenceVariation(input)

        self.assertEqual(seq.type.type, "c", "Sequence variation type is not coding DNA")
        self.assertEqual(len(seq.alleles), 1, "Sequence variation does not contain 1 allele")

        allele = seq.alleles[0]

        self.assertEqual(len(allele.variations), 2, "Allele does not have 1 variation")

        variation = allele.variations[0]

        self.assertTrue(isinstance(variation, Deletion), "Variation is not an deletion")
        location = variation.location
        print(location)
        self.assertTrue(isinstance(location, Range), "Location is not a range")
        self.assertEqual(str(location), '112_117', "Location is not correct")


# TODO: Tests for multiple alleles, multiple variations, mosaicism, uncertain
# alleles, indels, complex variations, conversions, triplication and
# quadruplication, and probably lots more besides.
