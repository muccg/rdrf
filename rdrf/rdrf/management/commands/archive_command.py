from django.core.management.base import BaseCommand
from rdrf.models import Registry
from registry.patients.models import Patient

class Command(BaseCommand):
    help = 'Operate with archived (soft-deleted) patients'

    def add_arguments(self, parser):
        parser.add_argument('-r', action='store', dest='registry_code', help='registry code')
        parser.add_argument('cmd',
                            action='store',
                            choices=['list', 'delete', 'unarchive', 'archive'],
                            default="list",
                            help='cmd')
        parser.add_argument("-id", "--patient-id", action="store", dest="patient_id", default=None, help="Patient ID")
        parser.add_argument("-f", "--force", action="store_true", dest="forced", default=False, help="Perform actions without confirmation")
        
        
        
    def handle(self, *args, **options):

        registry_code = options.get("registry_code", None)
        cmd = options.get("cmd")
        patient_id = options.get("patient_id", None)
        forced = options.get("forced", False)
        

        if cmd == "list":
            if registry_code is not None:
                try:
                    registry_model = Registry.objects.get(code=registry_code)
                except Registry.DoesNotExist:
                    raise
                    
                query = Patient.objects.inactive().filter(rdrf_registry__in=[registry_model])
            else:
                query = Patient.objects.inactive()

            for p in query:
                print("%s %s" % (p.pk, p))

        elif cmd in  ['delete', 'archive', 'unarchive']:
            if patient_id is None:
                raise Exception("Must provide id of patient to %s" % cmd)
            else:
                try:
                    patient_model = Patient.objects.really_all().get(pk=patient_id)
                except Patient.DoesNotExist:
                    raise

                
                proceed = False
                if not forced:
                    confirm = input("Are you sure you want to %s patient %s (id=%s)? [yN]: " % (cmd,
                                                                                                patient_model,
                                                                                                patient_model.pk))
                    if confirm.lower() == "y":
                        proceed = True
                else:
                    proceed = True


                if proceed:
                    name = "%s %s" % (patient_model.pk, patient_model)

                    if cmd == 'delete':
                        patient_model._hard_delete()
                        print("%s DELETED" % name)
                    elif cmd == 'archive':
                        patient_model.active = False
                        patient_model.save()
                        print("%s ARCHIVED" % name)
                    elif cmd == 'unarchive':
                        patient_model.active = True
                        patient_model.save()
                        print("%s UNARCHIVED" % name)
                    
                    
                        
                        
                
        
        
            
