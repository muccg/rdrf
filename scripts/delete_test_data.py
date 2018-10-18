#!/usr/bin/env python
from registry.patients.models import Patient
from rdrf.models.definition.models import Registry
import django
import sys
django.setup()

# VERY DANGEROUS SCRIPT ALERT!
# This script is intended to be used to delete ( really delete not archive) 'testing" patients in ALL registries on a site prior to launch.
# It should never be used on a site that has gone live.

prompt = ">> "
blurb = " (Enter Y to accept, any other answer to abort) : "

SKULL_ASCII = """



                                .,od88888888888bo,.
                            .d88888888888888888888888b.
                         .d88888888888888888888888888888b.
                       .d888888888888888888888888888888888b.
                     .d8888888888888888888888888888888888888b.
                    d88888888888888888888888888888888888888888b
                   d8888888888888888888888888888888888888888888b
                  d888888888888888888888888888888888888888888888
                  8888888888888888888888888888888888888888888888
                  8888888888888888888888888888888888888888888888
                  8888888888888888888888888888888888888888888888
                  Y88888888888888888888888888888888888888888888P
                  "8888888888P'   "Y8888888888P"    "Y888888888"
                   88888888P        Y88888888P        Y88888888
                   Y8888888          ]888888P          8888888P
                    Y888888          d888888b          888888P
                     Y88888b        d88888888b        d88888P
                      Y888888b.   .d88888888888b.   .d888888
                       Y8888888888888888P Y8888888888888888
                        888888888888888P   Y88888888888888
                        "8888888888888[     ]888888888888"
                           "Y888888888888888888888888P"
                                "Y88888888888888P"
                             888b  Y8888888888P  d888
                             "888b              d888"
                              Y888bo.        .od888P
                               Y888888888888888888P
                                "Y88888888888888P"
                                  "Y8888888888P"
          d8888bo.                  "Y888888P"                  .od888b
         888888888bo.                                       .od8888888
         "88888888888b.                                   .od888888888[
         d8888888888888bo.                              .od888888888888
       d88888888888888888888bo.                     .od8888888888888888b
       ]888888888888888888888888bo.            .od8888888888888888888888b=
       888888888P" "Y888888888888888bo.     .od88888888888888P" "Y888888P=
        Y8888P"           "Y888888888888bd888888888888P"            "Y8P
          ""                   "Y8888888888888888P"
                                 .od8888888888bo.
                             .od888888888888888888bo.
                         .od8888888888P"  "Y8888888888bo.
                      .od8888888888P"        "Y8888888888bo.
                  .od88888888888P"              "Y88888888888bo.
        .od888888888888888888P"                    "Y8888888888888888bo.
       Y8888888888888888888P"                         "Y8888888888888888b=
       888888888888888888P"                            "Y8888888888888888=
        "Y888888888888888       *** !WARNING! ***        "Y88888888888888P=
             ""Y8888888P                                  "Y888888P"
                "Y8888P                                     Y888P"
"""


def display(msg):
    print("%s %s" % (prompt, msg))


def safe(question):
    response = input(prompt + question + blurb)
    return response == "Y"


def num_patients(registry_model):
    return Patient.objects.filter(rdrf_registry__in=[registry_model]).count()


def delete_test_data(registry_model):
    m = num_patients(registry_model)
    n = 0
    for patient in Patient.objects.filter(rdrf_registry__in=[registry_model]):
        try:
            name = "%s (id=%s)" % (patient, patient.pk)
            patient.delete()
            patient.delete()
            n += 1
            display("Successfully deleted patient %s in registry %s" %
                    (name, registry_model))
        except Exception as ex:
            display("Error deleting patient %s  in registry %s: %s" %
                    (name, ex, registry_model.code))
    return n, m


def delete_single_patient(patient_id):
    patient_model = Patient.objects.get(pk=patient_id)
    patient_model.delete()
    patient_model.delete()
    print("deleted patient %s sucessfully" % patient_id)


def delete_all_patients():
    print(SKULL_ASCII)
    print("**** This utlity is for deleting TEST patient data ONLY! ****")
    print("**** DO NOT USE ON A LIVE (POPULATED) SITE ! ****")
    print("**** USE _ONLY_ TO CLEAN UP TEST PATIENTS CREATED FOR TESTING PURPOSES PRIOR TO LAUNCH ****")

    if safe("You are about to DELETE (NOT ARCHIVE!) PATIENT data for RDRF! Do you wish to continue?"):
        for r in Registry.objects.all():
            size = num_patients(r)
            if safe("Delete all %s patients in registry %s?" % (size, r.code)):
                try:
                    n, m = delete_test_data(r)
                    display("Deleted %s out of %s patients successfully" % (n, m))
                except Exception as ex:
                    display("Error deleting test data for registry %s: %s" %
                            (r.code, ex))
            else:
                display("Skipping deletion of test data in registry %s" % r.code)
    else:
        display("Aborting! Nothing deleted! Bye")


def usage():
    print("Usage:")
    print("delete_test_data.py --all ( to interactively delete all patient data)")
    print("delete_test_data.py <patient_id> ( to delete one patient non-interactively)")
    print("delete_test_data.py --usage ( print this usage message)")


if __name__ == "__main__":
    import re
    number = re.compile(r"^\d+$")

    if len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg == "--usage":
            usage()
        elif arg == "--all":
            delete_all_patients()
        elif number.match(arg):
            try:
                delete_single_patient(arg)
            except Exception as ex:
                print("Error deleting patient %s: %s" % (arg, ex))
                sys.exit(1)
        else:
            usage()
    else:
        usage()
