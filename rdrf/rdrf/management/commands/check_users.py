import sys
from datetime import datetime, timedelta

from django.core.management import BaseCommand
from rdrf.models import Registry
from registry.patients.models import Patient
from registry.patients.models import ParentGuardian

class PatientType:
    PATIENT = 1
    CHILD = 2
    SELF_PATIENT = 3
    

class Command(BaseCommand):
    help = 'Send Reminders for various events'

    def add_arguments(self, parser):
        parser.add_argument('-r',"--registry_code",
                            action='store',
                            dest='registry_code',
                            help='Code of registry to check')
        parser.add_argument('-e','--event',
                            action='store',
                            dest='event',
                            default="cdes",
                            choices=['cdes', 'history', 'progress', 'registry_specific'],
                            help='Collection name')

    def _usage(self):
        print(explanation)

    def _print(self, msg):
        self.stdout.write(msg + "\n")

    def _get_threshold(self):
        return datetime.now() - timedelta(months=6)
        

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

        save_threshhold = self._get_threshold()
        
        for user, patient_model, patient_type in self._check_users(registry_model, save_threshold):
            self._process_reminder(user, patient_model, patient_type)


    def _process_reminder(self, user, patient_model, patient_type):
        print("todo process reminder for user %s patient %s type %s" % (user,
                                                                        patient_model,
                                                                        patient_type))
        
    def get_users(self, registry_model, parent=False):
        if not parent:
            for patient_model in Patient.objects.filter(registry__in=[registry_model]):
                if patient_model.user:
                    yield patient_model, user

        else:
            for parent_guardian_model in ParentGuardian.objects.all():
                if parent_guardian_model.user:
                    regs = [ r for r in parent_guardian.rdrf_registry.all() ]
                    if registry_model in regs:
                        yield parent_guardian_model, parent_guardian_model.user


    def _get_children(self, parent_guardian_model):
        # to do
        return []
                    
    def _check_users(self, registry_model, save_threshold):
        for patient_model, user in self._get_users(registry_model):
            last_saved = self._get_last_saved_timestamp(patient_model, user)
            if last_saved < save_threshold:
                yield user, patient_model, PatientType.PATIENT

        for parent_guardian_model, user in self._get_users(registry_model, parent=True):
            if parent_guardian_model.self_patient:
                last_saved = self._get_last_saved_timestamp(parent_guardian_model.self_patient, user)
                if last_saved < save_threshhold:
                    yield user, PatientType.SELF_PATIENT
                    
            for child_patient_model in self._get_children(parent_guardian_model):
                last_saved = self._get_last_saved_timestamp(child_patient_model, user)
                if last_saved < save_threshold:
                    yield user, PatientType.CHILD

                
                
            
        


        

        

        
    
