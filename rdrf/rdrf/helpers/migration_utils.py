from django.db import migrations


class ClinicalDBRunPython(migrations.RunPython):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.alias == 'clinical':
            print("Running Python data migration on clinical db")
            self.code(from_state.apps, schema_editor)
        else:
            print("not running Python data migration on non-clinical db")
