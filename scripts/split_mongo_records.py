import django
django.setup()


from rdrf.models import ContextFormGroup
from rdrf.models import RDRFContext
from rdrf.models import Registry
from rdrf.mongo_client import construct_mongo_client



from registry.patients.models import Patient
from django.contrib.contenttypes.models import ContentType 


class Logger(object):
    def __init__(self, patient_model):
        self.patient_model = patient_model
        self.prefix = "Patient %s (id=%s)" % (self.patient_model, self.patient_model.pk)

            
        
    def info(self, msg):
        print "%s: %s" % (self.prefix, msg)

    def error(self, msg):
        print "ERROR! %s: %s" % (self.prefix, msg)
        

class ScriptError(Exception):
    pass



class FHRecordSplitter(object):
    def __init__(self, registry_model, mongo_db_name):
        self.logger = None
        self.mongo_db_name = mongo_db_name
        self.registry_model = registry_model
        if self.registry_model.code != 'fh':
            raise ScriptError("This script only works with FH Registry!")
        
        self.checkup_form_group_name = "Checkup"

        try:
            self.checkup_context_form_group = ContextFormGroup.objects.get(registry=self.registry_model,
                                                name=self.checkup_form_group_name)
        except ContextFormGroup.DoesNotExist:
            raise ScriptError("Checkup form group does not exist - are you sure you have imported the correct FH yaml file first")
        

        try:
            self.main_cfg = ContextFormGroup.objects.get(registry=self.registry_model,
                                           name="Main")
        except ContextFormGroup.DoesNotExist:
            raise ScriptError("No Main context form group: Make sure latest FH yaml is imported first")
        

        try:
            self.mongo_client = construct_mongo_client()
        except Exception, ex:
            raise ScriptError("could not create mongo client: %s" % ex)
        
        self.mongo_db = self.mongo_client[self.mongo_db_name]
        self.cdes_collection = self.mongo_db["cdes"]


    def perform_checks(self):
        for record in self.cdes_collection.find({"django_model": "Patient"}):
            
        
        
    def run(self):
        for patient_model in Patient.objects.filter(rdrf_registry__in=[self.registry_model]):
            error = False
            self.logger = Logger(patient_model)
            self.logger.info("processing ...")


            # We can't use the normal "Dynamic Data Wrapper" in RDRF because this tries to retrieve by context id
            # is the registry changes from not using form groups to using form groups as here, the loadi

            records = [ data for data in self.cdes_collection.find({"django_model": "Patient",
                                                      "django_id": patient_model.pk})]

            if len(records) != 1:
                self.logger.info("There are %s mongo records - skipping!" % len(records))
                continue

            dynamic_data = records[0]
            
            followup_form = None
            index = None

            if dynamic_data is not None:
                self.logger.info("There is a mongo record for this patient")
                
                for i, form_dict in enumerate(dynamic_data["forms"]):
                    if form_dict["name"] == "FollowUp":
                        self.logger.info("There is a FollowUp form for this patient")
                        followup_form = form_dict
                        index = i

            if followup_form is not None:
                form_timestamp = dynamic_data.get("FollowUp_timestamp", None)
                self.logger.info("FollowUp form timestamp = %s" % form_timestamp)
                try:
                    del dynamic_data["forms"][index]
                except Exception, ex:
                    self.logger.error("could not delete old FollowUp form from record: %s" % ex)
                    self.logger.info("skipping this record ...")
                    continue
                
                self.logger.info("deleted old FollowUp form data from original record")
                try:
                    del dynamic_data["FollowUp_timestamp"]
                    self.logger.info("deleted old FollowUp timestamp")
                except Exception, ex:
                    self.logger.error("could not delete old FollowUp form timestamp: %s" % ex)
                    self.logger.info("skipping this record ...")
                    continue
                            
                try:
                    followup_mongo_record = self._create_additional_mongo_record(patient_model, followup_form, form_timestamp)
                    self.logger.info("created new Checkup mongo record ok")
                except Exception, ex:
                    self.logger.error("could not create new Checkup mongo record: %s" % ex)
                    self.logger.info("skipping this patient")
                    continue
                

                # update the existing record
                try:
                    mongo_id = dynamic_data["_id"]
                    self.logger.info("existing mongo _id = %s" % mongo_id)
                except Exception, ex:
                    self.logger.error("could not find existing _id in record: %s" % ex)
                    self.logger.info("skipping this patient")
                    continue
                    
            
                try:
                    self.cdes_collection.update({'_id': mongo_id}, {"$set": dynamic_data}, upsert=False)
                    self.logger.info("update successful")
                except Exception, ex:
                    logger.error("error updating the existing mongo record: %s" % ex)
                    error = True
            

                #insert new record for the new context
                try:
                    self.cdes_collection.insert(followup_mongo_record)
                    self.logger.info("new CheckUp context created OK")
                except Exception, ex:
                    error = True
                    self.logger.error("failed to insert new followup form context: %s" % ex)
                    
                
                if error:
                    self.logger.info("finished - this patient had errors")
                else:
                    self.logger.info("finished - successfully processed")
                    

                
                
                

    def _create_additional_mongo_record(self, patient_model, followup_form, form_timestamp):
        content_type = ContentType.objects.get_for_model(patient_model)
        rdrf_context = RDRFContext(registry=self.registry_model, content_object=patient_model)
        rdrf_context.context_form_group = self.checkup_context_form_group
        rdrf_context.save()
        new_mongo_record = {"forms": [followup_form],
                            "timestamp": form_timestamp,
                            "FollowUp_timestamp": form_timestamp,
                            "django_id": patient_model.pk,
                            "django_model": "Patient",
                            "context_id": rdrf_context.pk}

        return new_mongo_record

    def _link_main_context_form_group(self, logger, existing_context_id):

        try:
            context_model = RDRFContext.objects.get(pk=existing_context_id)
        except RDRFContext.DoesNotExist:
            self.logger.error("context_id %s has no django model" % existing_context_id)
            return

        context_model.context_form_group = self.main_cfg
        context_model.save()
        
if __name__=='__main__':
    import sys
    db_name = sys.argv[1]
    fh = Registry.objects.get(code='fh')
    try:
        rs = FHRecordSplitter(fh, db_name)
    except ScriptError, serr:
        print "Transform will not be run because: %s" % serr
        sys.exit(1)

    print "Starting run..."
    rs.run()

    rs.perform_checks()
    
    print "Finished run"
    
    
        
