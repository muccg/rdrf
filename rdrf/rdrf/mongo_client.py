from django.conf import settings
from pymongo import MongoClient


def construct_mongo_client():
    # see http://api.mongodb.org/python/2.8.1/api/pymongo/mongo_client.html
    return MongoClient(settings.MONGOSERVER,
                       settings.MONGOPORT,
                       settings.MONGO_CLIENT_MAX_POOL_SIZE,
                       dict,   # NB we're not exposing this
                       settings.MONGO_CLIENT_TZ_AWARE,
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
