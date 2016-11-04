import datetime
import logging
import ssl
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from django.core.management.base import BaseCommand
from django.db import transaction
from ccg_django_utils.conf import EnvConfig
from ...models import Registry, Modjgo

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
        mongo_django(rs, dry_run=options["dry_run"])

############################################################################
# Settings

env = EnvConfig()

MONGOSERVER = env.get("mongoserver", "localhost")
MONGOPORT = env.get("mongoport", 27017)
MONGO_DB_PREFIX = env.get("mongo_db_prefix", "")

MONGO_CLIENT_MAX_POOL_SIZE = env.get("mongo_max_pool_size", 100)
MONGO_CLIENT_TZ_AWARE = env.get("mongo_client_tz_aware", False)
MONGO_CLIENT_CONNECT = env.get("mongo_client_connect", True)

MONGO_CLIENT_SOCKET_TIMEOUT_MS = env.get("mongo_client_socket_timeout_ms", "") or None
MONGO_CLIENT_CONNECT_TIMEOUT_MS = env.get("mongo_client_connect_timeout_ms", 20000)
MONGO_CLIENT_WAIT_QUEUE_TIMEOUT_MS = env.get("mongo_client_wait_queue_timeout_ms", "") or None
MONGO_CLIENT_WAIT_QUEUE_MULTIPLE = env.get("mongo_client_wait_queue_multiple", "") or None
MONGO_CLIENT_SOCKET_KEEP_ALIVE = env.get("mongo_client_socket_keep_alive", False)

MONGO_CLIENT_SSL = env.get("mongo_client_ssl", False)
MONGO_CLIENT_SSL_KEYFILE = env.get("mongo_client_ssl_keyfile", "") or None
MONGO_CLIENT_SSL_CERTFILE = env.get("mongo_client_ssl_certfile", "") or None
MONGO_CLIENT_SSL_CERT_REQS = env.get("mongo_client_ssl_cert_reqs", "") or ssl.CERT_NONE
MONGO_CLIENT_SSL_CA_CERTS = env.get("mongo_client_ssl_ca_certs", "") or None

def mongo_client():
    return MongoClient(MONGOSERVER, MONGOPORT,
                       MONGO_CLIENT_MAX_POOL_SIZE,
                       dict, MONGO_CLIENT_TZ_AWARE,
                       ssl=MONGO_CLIENT_SSL,
                       ssl_keyfile=MONGO_CLIENT_SSL_KEYFILE,
                       ssl_certfile=MONGO_CLIENT_SSL_CERTFILE,
                       ssl_cert_reqs=MONGO_CLIENT_SSL_CERT_REQS,
                       ssl_ca_certs=MONGO_CLIENT_SSL_CA_CERTS,
                       socketTimeoutMS=MONGO_CLIENT_SOCKET_TIMEOUT_MS,
                       connectTimeoutMS=MONGO_CLIENT_CONNECT_TIMEOUT_MS,
                       waitQueueTimeoutMS=MONGO_CLIENT_WAIT_QUEUE_TIMEOUT_MS,
                       waitQueueMultiple=MONGO_CLIENT_WAIT_QUEUE_MULTIPLE,
                       socketKeepAlive=MONGO_CLIENT_SOCKET_KEEP_ALIVE)

############################################################################
# The conversion script

def mongo_django(registries, dry_run=False):
    client = mongo_client()
    for registry in registries:
        collection = MONGO_DB_PREFIX + registry.code
        logger.info("Converting mongodb %s: %s" % (collection, registry.name))
        db = client[collection]
        convert_registry(registry, db, dry_run=dry_run)
        logger.info("Finished %s" % collection)

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

def convert_registry(registry, db, dry_run=False):
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

    for (c, _) in Modjgo.COLLECTIONS:
        convert_collection(db[c])
