from django.core.files.storage import Storage
from django.conf import settings

from pymongo import Connection
from gridfs import GridFS

import logging

logging.basicConfig(filename='gridfs_storage.log', level=logging.INFO)

class GridFSStorage(Storage):
    def __init__(self, *args, **kwargs):
        self.db = Connection(
            host=settings.MONGOSERVER,
            port=settings.MONGOPORT)["test_fs"]
        self.fs = GridFS(self.db)

    def _save(self, name, content):
        self.fs.put(content, filename=name)
        return name

    def _open(self, name, *args, **kwars):
        return self.fs.get_last_version(filename=name)

    def delete(self, name):
        for item in self.fs.find({"filename": name}):
            oid = item._id
            logging.info("File to delete oid=%s name=%s" % (name, oid))
            self.fs.delete(oid)

    def exists(self, name):
        return self.fs.exists({'filename': name})

    def size(self, name):
        return self.fs.get_last_version(filename=name).length

    def url(self, name):
        return name