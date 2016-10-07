import re
from . import sequence


class Allele(sequence.Allele):
    def parse(self, input):
        # TODO not sure that protein variations can include mosaics
        # http://www.hgvs.org/mutnomen/FAQ.html#mosaic
        if "," in input:
            self.mosaic = True
            variations = input.split(",")
        else:
            self.mosaic = False
            variations = input.split(";")

        self.variations = []

        # Loop through the variations we have and split the complex variations
        # such as indels into multiple single variations.
        for variation in variations:
            variation = variation.strip()

            # For now, we'll just support indels.
            if "delins" in variation:
                (location, insertion) = variation.split("delins", 1)
                self.variations.append(Deletion(location + "del"))
                self.variations.append(Insertion(location + "ins" + insertion))
            else:
                self.variations.append(Variation.create(variation))


class ProteinVariation(sequence.SequenceVariation):
    class NotProtein(sequence.SequenceVariation.Error):
        pass

    @staticmethod
    def create_allele(*args, **kwargs):
        return Allele(*args, **kwargs)

    def parse_type(self, input):
        if input[1] == ".":
            type = sequence.Type(input[0])
            input = input[2:]
        else:
            raise self.Malformed("No reference sequence type")

        if type.type != "p":
            raise self.NotProtein

        return (type, input)


class Variation(sequence.Variation):
    @staticmethod
    def create(input):
        if "del" in input:
            return Deletion(input)
        elif "dup" in input:
            return Duplication(input)
        elif "ins" in input:
            return Insertion(input)
        elif "fs" in input:
            return FrameShift(input)

        # Dunno, maybe a substitution?
        try:
            return Substitution(input)
        except Substitution.Malformed:
            raise Variation.Malformed("Unable to discern variation type")

    @staticmethod
    def create_position_or_range(input):
        try:
            return Position(input)
        except Position.Malformed:
            return Range(input)

    @staticmethod
    def valid_base(input):
        # Iterate through the amino acids specified and make sure they make
        # sense.
        exp = re.compile(r"(([A-Z])[a-z]{2})|[A-Z]")
        acids = []

        while len(input) > 0:
            match = exp.match(input)

            if match:
                acids.append(match.group(0))
                input = input[len(match.group(0)):]
            else:
                return False

        return acids


class Position(sequence.Position):
    def __init__(self, input=None):
        self.amino_acid = None
        sequence.Position.__init__(self, input)

    def __str__(self):
        if self.unknown:
            output = "?"
        else:
            output = self.amino_acid
            output += "*" if self.stop_codon else ""
            output += str(self.position)

            if self.intron_offset is not None:
                if self.intron_offset >= 0:
                    output += "+"
                output += str(self.intron_offset)

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse_amino_acid(self, input):
        match = re.match(r"(([A-Za-z])|([A-Za-z]{3}))(?![A-Za-z])", input)

        if not match:
            raise self.Malformed("No amino acid code given")

        self.amino_acid = match.group(0)
        return input[len(match.group(0)):]

    def parse(self, input):
        (input, self.uncertain) = Variation.strip_uncertain(input.strip())

        self.parse_unknown(input)
        if self.unknown:
            return

        # We have either a one or three character amino acid code to deal with.
        input = self.parse_amino_acid(input)
        input = self.parse_stop_codon(input)
        input = self.parse_position_intron(input)


class Range(sequence.Range):
    @staticmethod
    def create_position(position):
        return Position(position)


class Substitution(sequence.Substitution):
    @staticmethod
    def create_position_or_range(input):
        return Variation.create_position_or_range(input)

    @staticmethod
    def valid_base(input):
        return Variation.valid_base(input)

    def __str__(self):
        output = str(self.location) + self.new

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse(self, input):
        (input, self.uncertain) = Variation.strip_uncertain(input.strip())

        # Work backwards: the trailing part of the position should be numeric
        # (or a question mark).
        match = re.match(r"(.*([0-9]|\?))(.*)", input)

        if not match:
            raise self.Malformed("Unable to find end of position specifier")

        if not match.group(3):
            raise self.Malformed("Substitution requires a substituted value")

        if not self.valid_base(match.group(3)):
            raise self.Malformed("Substituted value is invalid")

        # The remainder is simply the amino acid that has been substituted.
        self.location = self.create_position_or_range(match.group(1))
        self.new = match.group(3)


class Deletion(sequence.Deletion):
    @staticmethod
    def create_position_or_range(input):
        return Variation.create_position_or_range(input)

    @staticmethod
    def valid_base(input):
        return Variation.valid_base(input)

    def is_valid_deletion(self, deletion):
        if not self.valid_base(deletion):
            raise Variation.Malformed("One or more deleted acids is invalid")


class Duplication(sequence.Duplication):
    @staticmethod
    def create_position_or_range(input):
        return Variation.create_position_or_range(input)

    @staticmethod
    def valid_base(input):
        return Variation.valid_base(input)

    def is_valid_duplication(self, duplication):
        if not self.valid_base(duplication):
            raise Variation.Malformed("One or more duplicated acids is invalid")


class Insertion(sequence.Insertion):
    @staticmethod
    def create_position_or_range(input):
        return Variation.create_position_or_range(input)

    @staticmethod
    def valid_base(input):
        return Variation.valid_base(input)

    def parse(self, input):
        sequence.Insertion.parse(self, input)
        self.insertions = self.valid_base(self.insertion)


class FrameShift(Variation):
    def __init__(self, input=None):
        self.location = None
        self.new = None
        self.uncertain = None

    def __str__(self):
        output = "%sfs%s" % (self.location, self.new)

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse(self, input):
        (input, self.uncertain) = self.strip_uncertain(input.strip())

        (location, self.new) = input.split("fs", 1)
        self.location = self.create_position_or_range(location)
