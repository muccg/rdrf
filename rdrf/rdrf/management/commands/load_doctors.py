from django.core.management.base import BaseCommand
from django.db import transaction
from openpyxl import load_workbook

from registry.patients.models import Doctor
from registry.patients.models import State


class DataLoadException(Exception):
    pass


# class Doctor(models.Model):
#     # TODO: Is it possible for one doctor to work with multiple working groups?
#     family_name = models.CharField(max_length=100, db_index=True)
#     given_names = models.CharField(max_length=100, db_index=True)
#     surgery_name = models.CharField(max_length=100, blank=True)
#     speciality = models.CharField(max_length=100)
#     address = models.TextField()
#     suburb = models.CharField(max_length=50, verbose_name="Suburb/Town")
#     state = models.ForeignKey(State, verbose_name="State/Province/Territory")
#     phone = models.CharField(max_length=30, blank=True, null=True)
#     email = models.EmailField(blank=True, null=True)

class DataLoader(object):

    def __init__(self, data_file):
        self.data_file = data_file
        self.work_book = None
        self.rows = []

        # fields and column names
        # if one field spans multiple columns we use a list - the values are
        # joined with newlines
        self.fields = [("family_name", "C"),
                       ("given_names", "D"),
                       ("title", "B"),
                       ("fax", "N"),
                       ("sex", "E", self.get_sex),
                       ("postcode", "L"),
                       ("surgery_name", "G"),
                       ("speciality", "F"),
                       ("address", ["H", "I"]),
                       ("suburb", "J"),
                       ("state", "K", self.convert_state),
                       ("phone", "M"),
                       ("email", "O")]

    @transaction.atomic()
    def load(self):
        self.work_book = load_workbook(self.data_file)
        self.rows = self.work_book.worksheets[0].rows
        print("starting to import doctors from %s .." % self.data_file)
        print("There are %s doctor rows to import" % len(self.rows))
        for row_num, row in enumerate(self.rows[1:]):
            real_row = row_num + 2
            doctor = self._create_doctor(row)
            doctor.save()
            print("row %s doctor %s OK" % (real_row, doctor))
        print("all done")

    def _create_doctor(self, row):
        d = Doctor()
        for field_spec in self.fields:
            field = field_spec[0]
            cols = field_spec[1]

            if len(field_spec) == 3:
                converter = field_spec[2]
            else:
                converter = None

            value = self._get_value(row, cols, converter)
            setattr(d, field, value)

        return d

    def _get_value(self, row, col_spec, converter):
        if isinstance(col_spec, list):
            value = "\n".join([self._get_column(row, col_code) for col_code in col_spec])
        else:
            value = self._get_column(row, col_spec)

        if converter:
            return converter(value)
        else:
            return value

    def _get_column(self, row, col_name):

        for cell in row:
            if cell.column == col_name:
                value = cell.value
                if value is None:
                    return ""
                else:
                    return value
        raise DataLoadException("Unknown column: %s" % col_name)

    def convert_state(self, short_name):
        try:
            state_model = State.objects.get(short_name=short_name.upper())
            return state_model
        except State.DoesNotExist:
            print("State %s does not exist in DB" % short_name)
            raise

    def get_sex(self, value):
        if value is None:
            return ""
        elif value == "M":
            return "1"
        elif value == "F":
            return "2"
        elif value == "X":
            return "3"
        else:
            return ""


class Command(BaseCommand):
    help = 'Loads a provided doctors spreadsheet'

    def add_arguments(self, parser):
        parser.add_argument('--file',
                            action='store',
                            dest='doctors_file',
                            default=None,
                            help='Doctors Spreadsheet File')

    def handle(self, *args, **options):
        doctors_spreadsheet = options.get("doctors_file")
        if doctors_spreadsheet is None:
            raise Exception("--file argument required")

        data_loader = DataLoader(doctors_spreadsheet)
        try:
            data_loader.load()
        except Exception as ex:
            print("Error importing doctors ( transaction will be rolled back): %s" % ex)
