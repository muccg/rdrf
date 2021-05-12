
import os
import sys
import shutil
from django.core.management import BaseCommand
from rdrf.models.definition.models import Registry

proms_dirs = ['proms', 'bootstrap-4.0.0']
allowed_proms_files = []  # shouldn't need any
static_dir = "/data/static"


def error(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def sanity_check():
    try:
        Registry.objects.get()
    except Registry.DoesNotExist:
        error("Not an RDRF site - no registries")

    except Registry.MultipleObjectsReturned:
        error("Not an PROMS Site - more than one registry on site")

    system_role = os.getenv("SYSTEM_ROLE", "")

    if system_role != "CIC_PROMS":
        error("CIC Site must have the CIC_PROMS system role")


def folder_exists(d):
    return os.path.exists(d) and os.path.isdir(d)


def rmfol(fol):
    if not fol.startswith("/data/static"):
        print(f"can't remove folder {fol}")
        return
    if folder_exists(fol):
        name = os.path.basename(fol)
        if name in proms_dirs:
            print(f"can't remove proms folder {fol}")
            return
        shutil.rmtree(fol)
    else:
        print(f"can't remove folder {fol} as it doesn't exist")


def check_proms():
    missing = []
    for proms_dir in proms_dirs:
        full_path = os.path.join(static_dir, proms_dir)
        if not folder_exists(full_path):
            missing.append(full_path)

    if missing:
        for d in missing:
            print(f"proms site static folder check failed: {d} is missing", file=sys.stderr)
        sys.exit(1)


def remove_non_proms_folders():
    for content in os.listdir(static_dir):
        full_path = os.path.join(static_dir, content)
        if folder_exists(full_path) and content not in proms_dirs:
            rmfol(full_path)


def remove_non_proms_files():
    for content in os.listdir(static_dir):
        full_path = os.path.join(static_dir, content)
        if os.path.isfile(full_path) and not content.startswith("."):
            if content not in allowed_proms_files:
                os.unlink(full_path)


class Command(BaseCommand):
    help = "setup_proms_static removes directories in /data/static that are not relevant to the working of the proms site"

    def handle(self, *args, **options):
        sanity_check()
        check_proms()
        remove_non_proms_folders()
        remove_non_proms_files()
        print("finished cleaning up proms static folder")
