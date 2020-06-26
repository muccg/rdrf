from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry


class Command(BaseCommand):
    help = "Set the registry version"

    def handle(self, *args, **options):
        print("\nATTENTION: You are about to change the version of Registry")
        for registry in Registry.objects.all():
            current_version = registry.version or "Not set"
            print(f"\nCurrent version of {registry.name} is: {current_version}")
            new_version = input("Enter new version: ")
            registry.version = new_version
            registry.save()
