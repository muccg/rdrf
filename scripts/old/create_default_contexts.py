from rdrf.db.contexts_api import RDRFContextManager
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient
import sys
import django
django.setup()


def display(p):
    return "Patient %s (id=%s)" % (p, p.id)


def num_contexts(patient_model, registry_model):
    return len([c for c in patient_model.context_models if c.registry.code == registry_model.code])


if __name__ == "__main__":
    registry_code = sys.argv[1]
    try:
        registry_model = Registry.objects.get(code=registry_code)
    except Registry.DoesNotExist:
        print("Registry %s does not exist on site - aborting" % registry_code)
        sys.exit(1)

    rdrf_context_manager = RDRFContextManager(registry_model)
    errors = processed = 0

    for p in Patient.objects.filter(rdrf_registry__in=[registry_model]):
        if num_contexts(p, registry_model) == 0:
            print("%s has no default context - creating one" % display(p))
            try:
                default_context = rdrf_context_manager.create_initial_context_for_new_patient(p)
                print("created context OK for %s" % display(p))
                processed += 1
            except Exception as ex:
                print("Error creating default context for %s: %s " % (display(p), ex))
                errors += 1

    print("All done : processed %s patients. There were %s errors." % (processed, errors))
