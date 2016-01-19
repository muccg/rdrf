# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from rdrf.mongo_client import construct_mongo_client


def forwards_func(apps, schema_editor):
    client = construct_mongo_client()
    for db_name in client.database_names():
        print "checking db %s" % db_name
        db = client[db_name]
        for collection_name in db.collection_names():
            print "checking collection %s" % collection_name
            coll = db[collection_name]
            for record in coll.find({}):
                if "django_id" in record and "django_model" in record:
                    if record["django_model"] == "Patient":
                        print 'found patient id = %s' % record["django_id"]


def backwards_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0015_mongomigrationdummymodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mongomigrationdummymodel',
            name='version',
            field=models.CharField(max_length=80, choices=[(b'initial', b'initial'), (b'testing', b'testing')]),
        ),
        migrations.RunPython(forwards_func, backwards_func),
    ]

