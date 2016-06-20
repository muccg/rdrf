import django
django.setup()

from rdrf.models import ContextFormGroup
from rdrf.models import RDRFContext
from rdrf.models import Registry
from rdrf.mongo_client import construct_mongo_client

from django.db import transaction




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
        self.backup_data = {}
        self.checkup_record_ids = []
        
        
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

    def _sanity_check_main_record(self, record):
        if record:
            form_names = [form["name"] for form in record["forms"]]
            assert "FollowUp" not in form_names, "FollowUp form should not be in a main record"
            assert "FollowUp_timestamp" not in record, "FollowU_timestamp should not be in a main record"
            assert "context_id" in record, "Main record should have a context_id"
            try:
                context_model = RDRFContext.objects.get(id=record["context_id"])
            except RDRFContext.DoesNotExist:
                raise ScriptError("mentioned context does not exist in record %s" % record)

            assert context_model.object_id == record["django_id"], "Linked context not correct patient"

            assert context_model.context_form_group is not None, "Main context should be linked to the Main Context form group"
            assert context_model.context_form_group.name == "Main"
            assert context_model.context_form_group.registry.code == self.registry_model.code, "Context Form Group should linked to FH"
            
    def rollback(self):
        """
        We can't really rollback but we can revert back to the original mongo record and delete any FollowUp form contexts that were inserted

        """
        for patient_id, original_mongo_record in self.backup_data.items():
            print "rolling back mongo data for patient id %s" % patient_id
            mongo_id = mongo_record["_id"]
            
            try:
                self.cdes_collection.update({'_id': mongo_id}, {"$set": original_mongo_record}, upsert=False)
            except Exception, ex:
                print "Error rolling back patient id %s: %s" % (patient_id, ex)

        for mongo_id in self.checkup_records:
            try:
                self.cdes_collection.remove({"_id": mongo_id})
                print "Removed checkup record with _id %s" % mongo_id
            except Exception, ex:
                print "could remove mongo record with _id %s" % mongo_id
                
    
    def _sanity_check_followup_record(self, record):
        num_forms = len(record["forms"])
        assert num_forms == 1, "There should be one FollowUp form in the record"
        form = record["forms"][0]
        assert form["name"] == "FollowUp", "The single form in a CheckUp context should be called FollowUp"
        assert "FollowUp_timestamp" in record
        assert "context_id" in record, "Record should have a context_id"
        try:
            context_model = RDRFContext.objects.get(id=record["context_id"])
        except RDRFContext.DoesNotExist:
            raise ScriptError("Linked context id does  not exist for record %s" % record)

        assert context_model.object_id == record["django_id"], "Linked context not correct patient"
        assert context_model.context_form_group is not None, "A CheckUp context must be linked to a context form group"
        cfg = context_model.context_form_group
        assert cfg.name == "CheckUp", "The linked context form group of a FollowUp form should be called CheckUp"

        
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

            self.backup_data[patient_model.pk] = dynamic_data
            
            followup_form = None
            index = None

            if dynamic_data is not None:
                self.logger.info("There is a mongo record for this patient")
                # Ensure that the existing context model is linked to the correct "Main" ( default) context form group
                context_id = dynamic_data["context_id"]
                self._link_main_context_form_group(context_id)

                # Locate the existing FollowUp form data and extract
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
                    self._sanity_check_main_record(dynamic_data)
                    self.cdes_collection.update({'_id': mongo_id}, {"$set": dynamic_data}, upsert=False)
                    self.logger.info("update successful")
                except Exception, ex:
                    self.logger.error("error updating the existing mongo record: %s" % ex)
                    error = True
            

                #insert new record for the new context
                try:
                    self._sanity_check_followup_record(followup_mongo_record)
                    result = self.cdes_collection.insert(followup_mongo_record)
                    self.logger.info("new CheckUp context created OK")
                    self.checkup_records.append(result.inserted_id)
                    
                except Exception, ex:
                    error = True
                    self.logger.error("failed to insert new followup form context: %s" % ex)
                    
                
                if error:
                    self.logger.info("finished - this patient had errors")
                else:
                    self.logger.info("finished - successfully processed")

            else:
                self.logger.info("followUp form not found in mongo record")

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

    def _link_main_context_form_group(self, existing_context_id):

        try:
            context_model = RDRFContext.objects.get(pk=existing_context_id)
        except RDRFContext.DoesNotExist:
            raise ScriptError("error getting context model for linking to Main context form group")

        context_model.context_form_group = self.main_cfg
        context_model.save()
        self.logger.info("Linked context %s to %s" % (context_model,
                                                      context_model.context_form_group))

        
if __name__=='__main__':
    import sys
    db_name = sys.argv[1]
    fh = Registry.objects.get(code='fh')
    try:
        rs = FHRecordSplitter(fh, db_name)
    except ScriptError, serr:
        print "Error : %s" % serr
        sys.exit(1)

    print "Starting run..."
    try:
        with transaction.atomic():
            rs.run()
    except Exception, ex:
        print "Error running transforms: %s" % ex
        try:
            rs.rollback()
            sys.exit(1)
            
        except Exception, ex:
            print "Oh shit could not rollback mongo: %s" % ex
            sys.exit(1)
            
    print "Finished run"
    sys.exit(0)
    
    
        
