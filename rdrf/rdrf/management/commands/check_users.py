import sys
from datetime import datetime, timedelta

from django.core.management import BaseCommand
from rdrf.models import Registry
from rdrf.models import Modjgo
from rdrf.utils import parse_iso_datetime

from registry.patients.models import Patient
from registry.patients.models import ParentGuardian

# Send reminders to patient/parent users with stale data

class PatientType:
    PATIENT = "PATIENT"
    CHILD = "CHILD"
    SELF_PATIENT = "SELF PATIENT"

def timestamp_key_func(snapshot):
    ts = snapshot.data["timestamp"]
    return parse_iso_datetime(ts)

def has_timestamp(snapshot):
    return all([snapshot is not None,
                snapshot.data,
                "timestamp" in snapshot.data])

class Command(BaseCommand):
    help = 'Send Reminders to users with stale data'

    def add_arguments(self, parser):
        parser.add_argument('-r',"--registry_code",
                            action='store',
                            dest='registry_code',
                            help='Code of registry to check')
    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def _get_threshold(self, registry_model):
        metadata = registry_model.metadata
        if "reminders" in metadata:
            reminder_dict = metadata["reminders"]
            last_saved_threshold_months= reminder_dict.get("last_saved", 12)
        else:
            return None
            
        return datetime.now() - timedelta(minutes=last_saved_threshold_months)
        

    def handle(self, *args, **options):
        registry_code = options.get("registry_code", None)
        if registry_code is None:
            self._print("Registry code required")
            sys.exit(1)

        try:
            registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            self._print("Registry does not exist")
            sys.exit(1)

        save_threshold = self._get_threshold(registry_model)
        if save_threshold is None:
            self._print("Registry %s does not have reminders" % registry_model)
            sys.exit(1)
        
        for user,relationship_to_user,patient_model in self._check_users(registry_model, save_threshold):
            self._process_reminder(user, relationship_to_user, patient_model)


    def _process_reminder(self, user, relationship_to_user, patient_model):
        print("%s,%s,%s" % (user.username,
                            relationship_to_user,
                            patient_model.pk))

    def _get_last_saved_timestamp(self, registry_model, user, patient_model):
        # check last time user saved patient for registry
        history_collection = Modjgo.objects.collection(registry_model.code,
                                               collection="history")

        snapshots_qs = history_collection.find(patient_model,
                                               username=user.username)
        
        snapshots = sorted([s for s in snapshots_qs if has_timestamp(s)],
                           key=timestamp_key_func,
                           reverse=True)
        if snapshots:
            last_saved_snapshot = snapshots[0]
            ts = parse_iso_datetime(last_saved_snapshot.data["timestamp"])
            return ts
        else:
            # if they haven't ever saved anything - we should do what..
            return None
        
        
    def _get_patient_users(self, registry_model, parent=False):
        if not parent:
            for patient_model in Patient.objects.filter(rdrf_registry__in=[registry_model]):
                if patient_model.user:
                    yield patient_model, patient_model.user

        else:
            for parent_guardian_model in ParentGuardian.objects.all():
                if parent_guardian_model.user:
                    regs = [ r for r in parent_guardian.rdrf_registry.all() ]
                    if registry_model in regs:
                        yield parent_guardian_model, parent_guardian_model.user

    def _check_users(self, registry_model, save_threshold):
        for patient_model, user in self._get_patient_users(registry_model):
            last_saved = self._get_last_saved_timestamp(registry_model,
                                                        user,
                                                        patient_model)
            if last_saved < save_threshold:
                yield user, PatientType.PATIENT, patient_model

        for parent_guardian_model, user in self._get_patient_users(registry_model, parent=True):
            # If the parent guardian is also a self patient check that also
            if parent_guardian_model.self_patient:
                last_saved = self._get_last_saved_timestamp(registry_model,
                                                            user,
                                                            parent_guardian_model.self_patient)
                if last_saved < save_threshold:
                    yield user, PatientType.SELF_PATIENT, parent_guardian_model.self_patient
                    
            for child_patient_model in parent_guardian_model.patient.all():
                last_saved = self._get_last_saved_timestamp(registry_model,
                                                            user,
                                                            child_patient_model)
                if last_saved < save_threshold:
                    yield user, PatientType.CHILD, child_patient_model

                
                
            
        


        

        

        
    
