from io import StringIO
import os

from django.core.management import call_command
from django.db import connections

class RegistryRouter:
    # Whether clinical db is configured at all.
    one_db = "clinical" not in connections
    # Whether clinical db is configured to be the same as main db.
    same_db = (one_db or
               connections["default"].get_connection_params() ==
               connections["clinical"].get_connection_params())

    clinical_models = (
        ("rdrf", "clinical"),
        ("rdrf", "questionnaireresponsedata"),
        # fixme: move CDEFile to clinical database. This is just
        # tricky with migrations.
        # ("rdrf", "cdefile"),
        ("rdrf", "patientdata"),
        ("rdrf", "formprogress"),
        ("rdrf", "modjgo"),
    )

    @classmethod
    def is_clinical(cls, app_label, model_name):
        return (app_label, model_name) in cls.clinical_models

    def choose_db_model(self, model):
        return self.choose_db(model._meta.app_label, model._meta.model_name)

    def choose_db(self, app_label, model_name):
        clinical = self.is_clinical(app_label, model_name)
        return "clinical" if clinical and not self.one_db else "default"

    def db_for_read(self, model, **hints):
        return self.choose_db_model(model)

    def db_for_write(self, model, **hints):
        return self.choose_db_model(model)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return (db == "default" and self.same_db or
                db == self.choose_db(app_label, model_name))


def reset_sql_sequences(apps):
    """
    Executes the necessary SQL to reset the primary key counters for
    all tables in `apps`.
    """
    os.environ['DJANGO_COLORS'] = 'nocolor'
    commands = StringIO()

    for app in apps:
        call_command('sqlsequencereset', app, stdout=commands)

    _execute_reset_sql_sequences(commands.getvalue().splitlines())


def _execute_reset_sql_sequences(commands):
    # this gets nasty because the --database option of
    # sqlsequencereset command doesn't work.
    clinical_tables = ["_".join(m) for m in RegistryRouter.clinical_models]
    def for_db(database):
        def _for_db(command):
            is_clinical = any(t in command for t in clinical_tables)
            return (not command.startswith("SELECT") or
                    (database == "default" and not is_clinical) or
                    (database == "clinical" and is_clinical) or
                    (database == "default" and "clinical" not in connections))
        return _for_db

    for database in ["default", "clinical"]:
        if database in connections:
            cursor = connections[database].cursor()
            cursor.execute("\n".join(filter(for_db(database), commands)))
