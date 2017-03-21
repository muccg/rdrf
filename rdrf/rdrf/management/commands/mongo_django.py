import datetime
import logging
import ssl
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from ccg_django_utils.conf import EnvConfig
from ...models import Registry, Modjgo

COLLECTIONS = [c for (c, _) in Modjgo.COLLECTIONS]

logger = logging.getLogger(__name__)

############################################################################
# Django management command

class Command(BaseCommand):
    help = "Copy clinical data from MongoDB into Django models"

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
        mongo_django(Modjgo, rs, dry_run=options["dry_run"])


def mongo_client():
    return MongoClient(settings.MONGOSERVER, settings.MONGOPORT,
                       settings.MONGO_CLIENT_MAX_POOL_SIZE,
                       dict, settings.MONGO_CLIENT_TZ_AWARE,
                       ssl=settings.MONGO_CLIENT_SSL,
                       ssl_keyfile=settings.MONGO_CLIENT_SSL_KEYFILE,
                       ssl_certfile=settings.MONGO_CLIENT_SSL_CERTFILE,
                       ssl_cert_reqs=settings.MONGO_CLIENT_SSL_CERT_REQS,
                       ssl_ca_certs=settings.MONGO_CLIENT_SSL_CA_CERTS,
                       socketTimeoutMS=settings.MONGO_CLIENT_SOCKET_TIMEOUT_MS,
                       connectTimeoutMS=settings.MONGO_CLIENT_CONNECT_TIMEOUT_MS,
                       waitQueueTimeoutMS=settings.MONGO_CLIENT_WAIT_QUEUE_TIMEOUT_MS,
                       waitQueueMultiple=settings.MONGO_CLIENT_WAIT_QUEUE_MULTIPLE,
                       socketKeepAlive=settings.MONGO_CLIENT_SOCKET_KEEP_ALIVE)

############################################################################
# The conversion script

def mongo_django(Modjgo, registries, dry_run=False):
    client = mongo_client()
    for registry in registries:
        collection = settings.MONGO_DB_PREFIX + registry.code
        logger.info("Converting mongodb %s: %s" % (collection, registry.name))
        db = client[collection]
        convert_registry(Modjgo, registry, db, dry_run=dry_run)
        logger.info("Finished %s" % collection)

def undjango_mongo(Modjgo, registries, dry_run=False):
    client = mongo_client()
    dead_ids = []
    for registry in registries:
        collection = settings.MONGO_DB_PREFIX + registry.code
        logger.info("Reverting mongodb %s: %s" % (collection, registry.name))
        db = client[collection]
        revert_registry(Modjgo, registry, db, dead_ids, dry_run=dry_run)
        logger.info("Finished %s" % collection)

    if not dry_run:
        Modjgo.objects.filter(id__in=dead_ids).delete()

def clean_doc(doc):
    if isinstance(doc, dict):
        return { k: clean_doc(v) for (k, v) in doc.items() }
    elif isinstance(doc, list):
        return list(map(clean_doc, doc))
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, (datetime.date, datetime.datetime)):
        return doc.isoformat()
    else:
        return doc

class DryRun(Exception):
    pass

def convert_registry(Modjgo, registry, db, dry_run=False):
    def finish_convert(obj, collection, doc, key):
        try:
            with transaction.atomic(using="clinical"):
                obj.save()
                logger.info("%sdb.%s.%s %s -> %s=%d" % ("(dry run) " if dry_run else "",
                                                        db.name, collection.name, doc["_id"],
                                                        key, obj.id))
                if not dry_run:
                    collection.update({ "_id": doc["_id"] },
                                      { "$set": { key: obj.id } })
                else:
                    raise DryRun()
        except PyMongoError:
            logger.exception("Some error updating mongodb")
        except DryRun:
            pass

    def convert_collection(collection):
        record_query = {
            "clinical_id": { "$exists": False },
        }
        for doc in collection.find(record_query):
            m = Modjgo(registry_code=registry.code,
                       collection=collection.name,
                       data=clean_doc(doc))
            finish_convert(m, collection, doc, "clinical_id")

    for c in COLLECTIONS:
        convert_collection(db[c])

def revert_registry(Modjgo, registry, db, dead_ids, dry_run=False):
    def revert_collection(collection):
        record_query = {
            "clinical_id": { "$exists": True },
        }
        count = 0
        for doc in collection.find(record_query, { "clinical_id": 1 }):
            dead_ids.append(doc["clinical_id"])
            count += 1

        logger.info("%sdb.%s.%s Updating %d documents" % ("(dry run) " if dry_run else "",
                                                          db.name, collection.name, count))

        if not dry_run:
            collection.update(record_query, { "$unset": { "clinical_id": "" } })

    for c in COLLECTIONS:
        revert_collection(db[c])
