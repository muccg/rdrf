from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry


class Command(BaseCommand):
    help = "Set the registry version"

    def handle(self, *args, **options):
        print("\nThe current registry versions:\n")

        registries = Registry.objects.all().values("name", "code", "version").order_by("code")
        for registry in registries:
            print(f"{registry['name']} [{registry['code']}]: {registry['version']}")

        code = input("\nEnter the registry code (press ENTER to exit): ")
        if code:
            version = input("\nEnter the new version (press ENTER to exit): ")
            if version:
                Registry.objects.filter(code=code).update(version=version)
