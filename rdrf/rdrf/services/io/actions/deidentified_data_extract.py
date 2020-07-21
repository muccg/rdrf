from datetime import datetime
import json
import zipfile
from zipfile import ZipFile
import uuid
from django.db import connections
from django.http import HttpResponse
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def security_check(custom_action, user):
    return user.in_registry(custom_action.registry)


class SQL:
    clinical_data_query = "SELECT django_id as pid, data FROM rdrf_clinicaldata WHERE collection='cdes'"
    id_query = "SELECT id, deident from patients_patient"


class PipeLine:
    VERSION = "1.0"

    def __init__(self):
        self.conn_clin = connections['clinical']
        self.conn_demo = connections['default']
        self.data = []
        self.id_map = self._construct_deident_map()

    def _raw_sql(self, conn, sql):
        with conn.cursor() as c:
            c.execute(sql)
            rows = c.fetchall()
        return rows

    def _construct_deident_map(self):
        return {row[0]: row[1] for row in self._raw_sql(self.conn_demo, SQL.id_query)}

    def deidentify(self):
        self.data = [self._deidentify_row(row) for row in
                     self._raw_sql(self.conn_clin, SQL.clinical_data_query)]

    def _deidentify_row(self, row):
        d = {}
        id = row[0]
        deident = self.id_map.get(id, "")
        d["id"] = deident
        data = row[1]
        if data:
            del data["django_id"]
        d["data"] = data
        return d


def extract_data():
    p = PipeLine()
    p.deidentify()
    return p.data


def execute(custom_action, user):
    a = datetime.now()
    timestamp = datetime.timestamp(a)
    guid = str(uuid.uuid1())
    results = extract_data()
    data = {}
    data["manifest"] = {"site": settings.DEIDENTIFIED_SITE_ID,
                        "timestamp": timestamp,
                        "version": PipeLine.VERSION,
                        "guid": guid}
    data["data"] = results
    json_data = json.dumps(data)
    response = HttpResponse(content_type="application/zip")
    zf = ZipFile(response, 'w', zipfile.ZIP_DEFLATED)
    name = settings.DEIDENTIFIED_SITE_ID + "_" + a.strftime("%Y%m%d%H%M%S")
    zip_name = name + ".zip"
    json_name = name + ".json"
    zf.writestr(json_name, json_data)
    response['Content-Disposition'] = 'attachment; filename=%s' % zip_name
    return response
