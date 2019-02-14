def open(url_or_file):
    return HGNC(url_or_file)


class HGNC:
    def __init__(self, url_or_file):
        from urllib.parse import urlparse

        if urlparse(url_or_file)[0] == "":
            self.fp = open(url_or_file, "r")
        else:
            from urllib.request import urlopen
            self.fp = urlopen(url_or_file)

        self.parse_header()

    def get_record(self):
        while True:
            line = self.fp.readline()

            if not line:
                return

            line = line.rstrip()
            record = dict(list(zip(self.fields, line.split("\t"))))

            yield record

    def parse_header(self):
        header = self.fp.readline()

        if not header:
            raise HeaderError

        header = header.rstrip()
        self.fields = header.lower().split("\t")


class HeaderError(Exception):
    pass
