from . import sequence


class ExonVariation(sequence.SequenceVariation):
    def __str__(self):
        if self.gene:
            output = str(self.gene) + ":"
        else:
            output = ""

        return output + "+".join([str(v) for v in self.variations])

    def parse(self, input):
        # Special case: since we don't really have a spec for this, we're
        # getting some usage on the DMD registry with an "exon" prefix. For the
        # time being, we'll allow it and ignore it.
        if input[0:4] == "exon":
            input = input[4:]

        # This is basically a cut-down version of SequenceVariation.parse with
        # the features we don't need here (such as allele handling) removed and
        # the guts of Allele.parse added.
        (self.gene, input) = self.parse_gene(input)

        # At present, there should only be one variation in an exon variation
        # as the notes are written, but let's at least use a list so that we
        # can handle multiple variations if the grammar gets extended down the
        # track.
        self.variations = []
        self.variations.append(Variation.create(input))


class Variation(sequence.Variation):
    @staticmethod
    def create(input):
        # This is far simpler than the parent parse method, since we only have
        # a couple of types of exon variation to parse.
        if "del" in input:
            return Deletion(input)
        elif "dup" in input:
            return Duplication(input)

        # If the given value is just a position or range, that's fine too,
        # since it's presumably going to represented elsewhere as a
        # sequence-level variation.
        try:
            return NoChange(input)
        except BaseException:
            raise Variation.Malformed("Unable to discern exon variation type")

    @staticmethod
    def create_position_or_range(input):
        try:
            return Position(input)
        except Position.Malformed:
            return Range(input)


class Position(sequence.Position):
    def __init__(self, input=None):
        self.position = None
        self.intron = False
        self.neuron = False
        self.uncertain = False

        if input is not None:
            self.parse(input)

    def __str__(self):
        output = str(self.position)

        if self.neuron:
            output += "c"

        if self.intron:
            output += "i"

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse(self, input):
        (input, self.uncertain) = Variation.strip_uncertain(input.strip())

        # Check for suffixed intron or neuron specifiers.
        if input and input[-1] == "i":
            self.intron = True
            input = input[:-1]

        if input and input[-1] == "c":
            self.neuron = True
            input = input[:-1]

        # OK, whatever's left should just be a number.
        try:
            self.position = int(input)
        except ValueError:
            raise self.Malformed("Bad exon number")


class Range(sequence.Range):
    @staticmethod
    def create_position(position):
        return Position(position)


class Deletion(sequence.Deletion):
    def parse(self, input):
        (location, deletion) = input.split("del", 1)
        self.location = Variation.create_position_or_range(location)

        if deletion:
            raise Variation.Malformed(
                "Exon deletions do not support the specification of the deleted nucleotides")


class Duplication(sequence.Duplication):
    def parse(self, input):
        (location, duplication) = input.split("dup", 1)
        self.location = Variation.create_position_or_range(location)

        if duplication:
            raise Variation.Malformed(
                "Exon duplications do not support the specification of the duplicated nucleotides")


class NoChange(sequence.NoChange):
    def __str__(self):
        return str(self.location)

    def parse(self, input):
        self.location = Variation.create_position_or_range(input)
