from datetime import datetime
import json
import zipfile
from zipfile import ZipFile
import uuid
from io import BytesIO
from django.db import connections
from django.http import HttpResponse
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def security_check(custom_action, user):
    return user.in_registry(custom_action.registry)


class SQL:
    clinical_data_query = "SELECT django_id as pid, data, context_id, collection FROM rdrf_clinicaldata WHERE collection='cdes'"
    id_query = "SELECT id, deident from patients_patient WHERE deident IS NOT NULL AND active IS NOT FALSE"
    sr_query = "SELECT p.deident as id, sr.survey_name, to_char(sr.updated,'YYYY-MM-DD HH24:MI:SS'), sr.communication_type, sr.state, sr.response from rdrf_surveyrequest sr inner join patients_patient p on p.id = sr.patient_id"


class PipeLine:
    VERSION = "1.0"

    def __init__(self, custom_action):
        self.custom_action = custom_action
        self.conn_clin = connections['clinical']
        self.conn_demo = connections['default']
        self.data = []
        self.sr_data = []
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
                     self._raw_sql(self.conn_clin, SQL.clinical_data_query)
                     if row[0] in self.id_map]

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

    def remove_blacklisted(self):
        action_data = self.custom_action.action_data
        blacklisted_forms = action_data.get("blacklist", [])
        if not blacklisted_forms:
            return
        for row in self.data:
            if "data" in row and "forms" in row["data"]:
                row["data"]["forms"] = [form_dict for form_dict in row["data"]
                                        ["forms"] if form_dict["name"] not in blacklisted_forms]

    def get_srs(self):
        def make_dict(row):
            return {"id": row[0],
                    "survey_name": row[1],
                    "updated": row[2],
                    "channel": row[3],
                    "state": row[4],
                    "response": row[5]
                    }

        self.srs = [make_dict(row) for row in self._raw_sql(self.conn_demo, SQL.sr_query)]


def extract_data(custom_action):
    p = PipeLine(custom_action)
    p.deidentify()
    p.remove_blacklisted()
    p.get_srs()
    return p.data, p.srs


def execute(custom_action, user, create_bytes_io=False):
    a = datetime.now()
    timestamp = datetime.timestamp(a)
    guid = str(uuid.uuid1())
    results = extract_data(custom_action)
    data = {}
    data["manifest"] = {"site": settings.DEIDENTIFIED_SITE_ID,
                        "timestamp": timestamp,
                        "version": PipeLine.VERSION,
                        "guid": guid}
    data["data"] = results[0]
    data["srs"] = results[1]
    json_data = json.dumps(data)
    if create_bytes_io:
        obj = BytesIO()
    else:
        obj = HttpResponse(content_type="application/zip")

    zf = ZipFile(obj, 'w', zipfile.ZIP_DEFLATED)
    name = settings.DEIDENTIFIED_SITE_ID + "_" + a.strftime("%Y%m%d%H%M%S")
    zip_name = name + ".zip"
    json_name = name + ".json"
    zf.writestr(json_name, json_data)
    if not create_bytes_io:
        obj['Content-Disposition'] = 'attachment; filename=%s' % zip_name
        return obj

    return zip_name, obj
