from collections import namedtuple, OrderedDict
from tempfile import TemporaryFile
from shutil import copyfileobj
import hashlib
import logging
import gridfs
from django.core.management.base import BaseCommand
from django.core.files import File
from ...models import Registry, RegistryForm, Section, CommonDataElement, CDEFile
from ...mongo_client import construct_mongo_client
from ...utils import mongo_db_name

logger = logging.getLogger("registry_log")


class Command(BaseCommand):
    help = "Transfer files across from GridFS into Django storage"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Don't do anything, just log.")
        parser.add_argument("registry", nargs="*")

    def handle(self, *args, **options):
        all_codes = Registry.objects.values_list("code", flat=True)
        for registry_code in options["registry"]:
            if registry_code not in all_codes:
                logger.warning("Registry \"%s\" does not exist." % registry_code)

        rs = Registry.objects.filter(code__in=options["registry"] or all_codes)
        for registry in rs:
            convert_registry(registry, dry_run=options["dry_run"])

def convert_registry(registry, dry_run=False):
    logger.info("Migrating files in registry \"%s\"" % registry.code)
    client = construct_mongo_client()
    db = client[mongo_db_name(registry.code)]
    fs = gridfs.GridFS(db, collection=registry.code + ".files")
    mapping = OrderedDict()
    for doc, file_refs in find_file_refs(registry, db):
        for collection, path, gridfs_file_id, filename, context in file_refs:
            if gridfs_file_id in mapping:
                continue
            django_file_id = convert_file(fs, registry, context, gridfs_file_id, filename, dry_run)
            if django_file_id is not None:
                q = { "_id": doc["_id"] }
                logger.info("Updating %s %s %s -> id=%s" % (collection, q, path, django_file_id))
                if not dry_run:
                    db[collection].update(q, {
                        "$set": { path + ".django_file_id": django_file_id },
                        "$unset": { path + ".gridfs_file_id": 1 }
                    })
            mapping[gridfs_file_id] = django_file_id

    for gridfs_file_id, django_id in mapping.iteritems():
        if django_id is not None:
            logger.debug("Deleting GridFS %s" % gridfs_file_id)
            if not dry_run:
                try:
                    fs.delete(gridfs_file_id)
                except gridfs.NoFile:
                    pass
                except Exception as e:
                    logger.exception("Couldn't remove GridFS file %s" % gridfs_file_id)

    logger.info("Migration complete%s" % (" (dry run)" if dry_run else "!"))

DocUpdate = namedtuple("DocUpdate", ["collection", "path", "gridfs_file_id", "filename", "context"])

def get_gridfs_file_id(cde):
    val = cde.get("value")
    if isinstance(val, dict):
        id = val.get("gridfs_file_id")
        if id:
            return (id, val.get("file_name"))
    return (None, None)


def find_file_refs(registry, db):
    for doc in db["cdes"].find({}):
        yield (doc, list(collect_patient_updates("cdes", doc)))

    for history in db["history"].find({}):
        doc = history.get("record") or {}
        yield (doc, list(collect_patient_updates("history", doc, prefix="record.")))

    # fixme: not quite sure how this collection is structured
    rspd = "registry_specific_patient_data"
    for doc in db[rspd].find({}):
        yield (doc, list(collect_registry_updates(doc)))

def collect_registry_updates(doc):
    for cde_index, cde in enumerate(section.get("cdes") or []):
        gridfs_file_id, filename = get_gridfs_file_id(cde)
        if gridfs_file_id:
            path = "cdes.%d.value" % cde_idx
            context = { "cde_code": cde.get("code") }
            yield DocUpdate(rspd, path, gridfs_file_id, filename, context)

def collect_patient_updates(collection, doc, prefix=""):
    # logger.debug("doc = %s" % doc)
    # logger.debug("forms = %s" % str(doc.get("forms")))

    for form_index, form in enumerate(doc.get("forms") or []):
        for sec_index, section in enumerate(form.get("sections") or []):
            for cde_index, cde in enumerate(section.get("cdes") or []):
                gridfs_file_id, filename = get_gridfs_file_id(cde)
                if gridfs_file_id:
                    idx = (prefix, form_index, sec_index, cde_index)
                    path = "%sforms.%d.sections.%d.cdes.%d.value" % idx
                    context = {
                        "form_name": form.get("name"),
                        "section_code": section.get("code"),
                        "cde_code": cde.get("code"),
                    }
                    yield DocUpdate(collection, path, gridfs_file_id, filename, context)

def convert_file(fs, registry, context, gridfs_file_id, filename, dry_run=False):
    try:
        logger.info("Finding file %s %s" % (str(gridfs_file_id), filename))
        data = fs.get(gridfs_file_id)
        logger.info("Copying %d bytes" % data.length)
        temp = TemporaryFile(prefix=filename)
        copyfileobj(data, temp)
        temp.seek(0)
        md5 = calc_md5(temp)

        if md5 == data.md5:
            logger.info("Loading into Django storage md5=%s" % md5)
            temp.seek(0)
            cde_file = make_cde_file(temp, filename, registry, **context)
            if dry_run:
                return 0
            if cde_file:
                cde_file.save()
                return cde_file.id
            return None
        else:
            logger.warning("Can't convert file: MD5 mismatch")
            return None
    except gridfs.NoFile:
        logger.warning("GridFS file %s does not exist" % str(gridfs_file_id))
        return None
    except Exception as e:
        logger.exception("Problem converting file")
        return None

def make_cde_file(file_obj, filename, registry, cde_code=None,
                  form_name=None, section_code=None):
    if form_name:
        form = RegistryForm.objects.filter(name=form_name).first()
        if not form:
            logger.warning("RegistryForm with name \"%s\" doesn't exist" % form_name)
    else:
        form = None

    if section_code:
        section = Section.objects.filter(code=section_code).first()
        if not section:
            logger.warning("Section with code \"%s\" doesn't exist" % section_code)

    cde = CommonDataElement.objects.filter(code=cde_code).first()
    if not cde:
        logger.warning("CDE with code \"%s\" doesn't exist" % cde_code)
        return None

    return CDEFile(registry=registry,
                   form=form,
                   section=section,
                   cde=cde,
                   item=File(file_obj),
                   filename=filename or "")


def calc_md5(file_obj):
    h = hashlib.new("md5")
    for buf in iter(lambda: file_obj.read(16*1024), b""):
        h.update(buf)
    return h.hexdigest()
