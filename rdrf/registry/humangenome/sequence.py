import re


class Allele:
    def __init__(self, input=None):
        self.mosaic = False
        self.variations = []

        if input:
            self.parse(input)

    def __str__(self):
        separator = "," if self.mosaic else ";"
        return separator.join([str(v) for v in self.variations])

    def parse(self, input):
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


class Gene:
    def __init__(self, gene):
        # Check for an embedded accession number.
        pattern = re.compile(r"\{([\w\.]+)\}", re.UNICODE)
        match = pattern.search(gene)
        if match:
            self.accession = match.group(1)
            gene = pattern.sub("", gene)
        else:
            self.accession = None

        self.gene = gene

    def __str__(self):
        if self.accession:
            return "%s{%s}" % (self.gene, self.accession)

        return self.gene


class SequenceVariation:
    class Error(Exception):
        pass

    class Malformed(Error):
        pass

    class NoType(Error):
        pass

    class Protein(Error):
        pass

    def __init__(self, input=None):
        if input:
            self.parse(input)

    @staticmethod
    def create_allele(*args, **kwargs):
        return Allele(*args, **kwargs)

    def parse_gene(self, input):
        """Internal parser to split off a gene from the start of the input,
        should it exist. Returns a tuple (gene, remaining input), with gene
        possibly being None."""

        colons = input.count(":")
        if colons == 1:
            (gene, input) = input.split(":", 1)
            return (Gene(gene), input)
        elif colons > 1:
            raise self.Malformed("Multiple colons detected, but HGVS rules only allow one gene")

        return (None, input)

    def parse_type(self, input):
        # Grab the type.
        if input[1] == ".":
            type = Type(input[0])
            input = input[2:]
        else:
            raise self.Malformed("No reference sequence type")

        if type.type == "p":
            # Proteins need to be handled elsewhere.
            raise self.Protein

        return (type, input)

    def parse(self, input):
        # Check for a gene.
        # print 'parsing gene'
        (self.gene, input) = self.parse_gene(input)

        # print 'parsing type'
        (self.type, input) = self.parse_type(input)

        # print 'splitting alleles'
        # The next step is basically to split out the alleles and then parse
        # them individually.
        pattern = re.compile(r"\[([^\]]+)\]")
        i = pattern.finditer(input)
        self.alleles = [self.create_allele(match.group(1)) for match in i]

        # Since the single-allele case probably won't involve square brackets,
        # we should check for that and act accordingly.
        if len(self.alleles) == 0:
            self.alleles = [self.create_allele(input)]

        # TODO: Check the actual linking operator for linking alleles: it
        # should always be +, but it might be nice to verify that.

        # Theoretically, at this point, we're done.

    def __str__(self):
        if not self.type:
            raise ValueError("no such type")

        sections = []

        if self.gene:
            sections.append(str(self.gene) + ":")

        sections.append(str(self.type) + ".")

        if len(self.alleles) > 1:
            alleles = [("[%s]" % allele) for allele in self.alleles]
            sections.append("+".join(alleles))
        else:
            sections.append(str(self.alleles[0]))

        return "".join(sections)


class Type:
    VALID_TYPES = {
        "c": "coding DNA reference sequence",
        "g": "genomic reference sequence",
        "m": "mitochondrial reference sequence",
        "r": "RNA reference sequence",
        "p": "protein reference sequence",
    }

    def __init__(self, type):
        # Validate the type.
        if type not in self.VALID_TYPES:
            raise ValueError

        self.type = type

    def __str__(self):
        return self.type


class Variation:
    class Malformed(SequenceVariation.Malformed):
        pass

    def __init__(self, input):
        pass

    def __str__(self):
        raise NotImplementedError

    @staticmethod
    def create(input):
        # Figure out what type of variation we have and instantiate the right
        # object.
        if ">" in input:
            return Substitution(input)
        elif "del" in input:
            return Deletion(input)
        elif "dup" in input:
            return Duplication(input)
        elif "ins" in input:
            return Insertion(input)
        elif "inv" in input:
            return Inversion(input)
        elif "con" in input:
            return Conversion(input)
        elif "=" in input:
            return NoChange(input)

        raise Variation.Malformed("Unable to discern variation type")

    @staticmethod
    def create_position_or_range(input):
        try:
            return Position(input)
        except Position.Malformed:
            return Range(input)

    @staticmethod
    def strip_uncertain(input):
        if input.startswith("(") and input.endswith(")"):
            return (input[1:-1], True)

        return (input, False)

    @staticmethod
    def valid_base(input):
        # TODO: It would be nice to actually check these against the type of
        # variation, but beggars can't be choosers and all that.
        for base in input:
            if base not in "ACGTacgu":
                return False

        return True


class Position:
    class Malformed(SequenceVariation.Malformed):
        pass

    def __init__(self, input=None):
        self.unknown = False
        self.stop_codon = False
        self.position = None
        self.intron_offset = None
        self.intron_offset_unknown = None
        self.uncertain = False

        if input:
            self.parse(input)

    def __str__(self):
        if self.unknown:
            output = "?"
        else:
            output = "*" if self.stop_codon else ""
            output += str(self.position)

            if self.intron_offset_unknown:
                if self.intron_offset_unknown > 0:
                    output += "+?"
                else:
                    output += "-?"
            elif self.intron_offset is not None:
                if self.intron_offset >= 0:
                    output += "+"
                output += str(self.intron_offset)

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse_position_intron(self, input):
        try:
            # Check for intronic nucleotides.
            if "+" in input or "-" in input[1:]:
                match = re.match(r"-?\d+", input)

                if not match:
                    raise self.Malformed("Bad reference nucleotide for intronic position")

                self.position = int(match.group(0))
                input = input[len(match.group(0)):]

                match = re.match(r"([+-]\d+)|([+-]\?)", input)

                if not match:
                    raise self.Malformed("Bad offset nucleotide for intronic position")

                if "?" in match.group(0):
                    self.intron_offset_unknown = 1 if match.group(0)[0] == "+" else -1
                    self.intron_offset = None
                else:
                    self.intron_offset = int(match.group(0))
                    self.intron_offset_unknown = None
            else:
                # Well, presumably this is a simple position, then.
                self.position = int(input)
                self.intron_offset = None
        except ValueError:
            raise self.Malformed("Bad number in position")

    def parse_stop_codon(self, input):
        if input[0] == "*":
            self.stop_codon = True
            return input[1:]
        else:
            self.stop_codon = False
            return input

    def parse_unknown(self, input):
        self.unknown = (input == "?")

    def parse(self, input):
        (input, self.uncertain) = Variation.strip_uncertain(input.strip())

        # Check if it's an unknown position, because we can bail early if so.
        self.parse_unknown(input)
        if self.unknown:
            return

        # Check if the position is within the stop codon.
        input = self.parse_stop_codon(input)

        input = self.parse_position_intron(input)


class Range:
    class Malformed(SequenceVariation.Malformed):
        pass

    def __init__(self, input=None):
        self.start = None
        self.end = None
        self.uncertain = False

        if input:
            self.parse(input)

    def __str__(self):
        output = "%s_%s" % (self.start, self.end)

        if self.uncertain:
            output = "(" + output + ")"

        return output

    @staticmethod
    def create_position(position):
        return Position(position)

    def parse(self, input):
        (input, self.uncertain) = Variation.strip_uncertain(input.strip())

        try:
            (start, end) = input.split("_", 1)

            self.start = self.create_position(start)
            self.end = self.create_position(end)
        except ValueError:
            raise self.Malformed("Bad range")


class Substitution(Variation):
    def __init__(self, input=None):
        self.location = None
        self.old = None
        self.new = None
        self.uncertain = None

        if input:
            self.parse(input)

    def __str__(self):
        output = "%s%s>%s" % (self.location, self.old, self.new)

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse(self, input):
        (input, self.uncertain) = self.strip_uncertain(input.strip())

        # Find the location within the string.
        match = re.match(r"[^ACGTacgu]*", input)
        self.location = self.create_position_or_range(match.group(0))
        input = input[len(match.group(0)):]

        # We should be left with just X>Y, hopefully.
        try:
            (self.old, self.new) = input.split(">", 1)

            if not (len(self.old) == 1 and len(self.new) == 1):
                raise Variation.Malformed(
                    "Substitutions can only be one nucleotide; indels should be used for multiple nucleotide substitutions")

            if not (self.valid_base(self.old) and self.valid_base(self.new)):
                raise Variation.Malformed("Bad base in substitution")
        except ValueError:
            raise Variation.Malformed("No substitution included in substitution")


class Deletion(Variation):
    def __init__(self, input=None):
        self.location = None
        self.deletion = None
        self.uncertain = False

        if input:
            self.parse(input)

    def __str__(self):
        output = "%sdel" % self.location

        if self.deletion:
            output += self.deletion

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def is_valid_deletion(self, deletion):
        if self.valid_base(deletion):
            # Calculating the actual number of nucleotides a range covers is
            # non-trivial, so we'll only validate the simple case: you can only
            # delete one nucleotide if the position is a single position.
            if isinstance(self.location, Position) and len(deletion) != 1:
                raise Variation.Malformed(
                    "Single position deletions cannot have more than one nucleotide")
        else:
            raise Variation.Malformed("One or more deleted bases are invalid")

        return True

    def parse(self, input):
        (input, self.uncertain) = self.strip_uncertain(input.strip())

        (location, deletion) = input.split("del", 1)
        self.location = self.create_position_or_range(location)

        if deletion and self.is_valid_deletion(deletion):
            self.deletion = deletion
        else:
            self.deletion = None


class Duplication(Variation):
    def __init__(self, input=None):
        self.location = None
        self.duplication = None
        self.uncertain = False

        if input:
            self.parse(input)

    def __str__(self):
        output = "%sdup" % self.location

        if self.duplication:
            output += self.duplication

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def is_valid_duplication(self, duplication):
        if self.valid_base(duplication):
            # Calculating the actual number of nucleotides a range covers is
            # non-trivial, so we'll only validate the simple case: you can only
            # duplicate one nucleotide if the position is a single position.
            if isinstance(self.location, Position) and len(duplication) != 1:
                raise Variation.Malformed(
                    "Single position duplications cannot have more than one nucleotide")
        else:
            raise Variation.Malformed("One or more duplicated bases are invalid")

        return True

    def parse(self, input):
        (input, self.uncertain) = self.strip_uncertain(input.strip())

        (location, duplication) = input.split("dup", 1)
        self.location = self.create_position_or_range(location)

        if duplication and self.is_valid_duplication(duplication):
            self.duplication = duplication
        else:
            self.duplication = None


class Insertion(Variation):
    def __init__(self, input=None):
        self.location = None
        self.insertion = None
        self.uncertain = False

        if input:
            self.parse(input)

    def __str__(self):
        output = "%sins%s" % (self.location, self.insertion)

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse(self, input):
        (input, self.uncertain) = self.strip_uncertain(input.strip())

        (location, self.insertion) = input.split("ins", 1)
        self.location = self.create_position_or_range(location)

        if len(self.insertion) == 0:
            raise Variation.Malformed("At least one nucleotide must be inserted")

        if not self.valid_base(self.insertion):
            raise Variation.Malformed("Insertion contains one or more invalid bases")


class Inversion(Variation):
    def __init__(self, input=None):
        self.location = None
        self.uncertain = False

        if input:
            self.parse(input)

    def __str__(self):
        output = "%sinv" % self.location

        if self.uncertain:
            output = "(" + output + ")"

        return output

    def parse(self, input):
        (input, self.uncertain) = self.strip_uncertain(input.strip())

        if input.endswith("inv"):
            self.location = self.create_position_or_range(input[:-3])
        else:
            raise Variation.Malformed("Inversion does not end with inv")


class Conversion(Variation):
    def __init__(self, input=None):
        # This isn't in Mutalyzer yet, so we'll skip it for now.
        raise NotImplementedError


class NoChange(Variation):
    def __init__(self, input=None):
        self.uncertain = False

        if input:
            self.parse(input)

    def __str__(self):
        return "(=)" if self.uncertain else "="

    def parse(self, input):
        (input, self.uncertain) = self.strip_uncertain(input.strip())

        if input != "=":
            raise Variation.Malformed("No change is not exactly =")
