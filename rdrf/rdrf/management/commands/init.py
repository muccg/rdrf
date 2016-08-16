from django.core.management.base import BaseCommand

from ... import initial_data


class Command(BaseCommand):
    help = "Loads initial data for RDRF. Use --list for possible datasets."

    def add_arguments(self, parser):
        parser.add_argument("dataset", nargs="*", type=str)
        parser.add_argument("--list", action="store_true")

    def print_out_dataset(self, module):
        self.stdout.write("  - %s" % module.__name__.split('.')[-1])
        doc = (module.__doc__ or '').strip()
        if doc:
            first_line = doc.split("\n")[0]
            self.stdout.write("      %s" % first_line)

    def handle(self, dataset=[], **options):
        if options.get("list"):
            self.stdout.write("Possible datasets are:")
            for m in initial_data.datasets:
                self.print_out_dataset(m)
            return

        self.modules_loaded = set()

        self.stdout.write("Loading RDRF data...")

        self.load_module_data("base", **options)
        for name in dataset:
            self.load_module_data(name, **options)

        self.stdout.write("RDRF data is ready.")

    def load_module_data(self, name, **options):
        try:
            module = getattr(initial_data, name)
        except AttributeError:
            self.stderr.write('Unknown dataset "%s".' % name)
            return

        for dep in getattr(module, "deps", []):
            self.load_module_data(dep, **options)

        self.load_data_once(module, **options)

    def load_data_once(self, module, **options):
        if module in self.modules_loaded:
            return
        self.stdout.write("    Loading %s..." % module.__name__.split(".")[-1])
        module.load_data(**options)
        self.modules_loaded.add(module)
