from django.core.management import BaseCommand
from rdrf.models.definition.models import CommonDataElement


class Command(BaseCommand):
    def handle(self, *args, **options):
        data_types = [dt[0] for dt in CommonDataElement.DATA_TYPES]
        for cde in CommonDataElement.objects.all():
            if cde.datatype not in data_types:
                print("%s \t %s \t %s" % (cde.datatype, cde.code, cde))
