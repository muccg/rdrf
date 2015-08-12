from django import forms
from registry.patients.models import Patient, PatientRelative
from rdrf.models import Registry

class FamilyLinkageError(Exception):
    pass


class FamilyLinkageType:
    index = "fh_is_index"
    relative = "fh_is_relative"


class FamilyLinkageManager(object):
    def __init__(self,  registry_model, index_patient):
        if not registry_model.has_feature("family_linkage"):
            raise FamilyLinkageError("need family linkages feature to use FamilyManager")
        self.registry_model = registry_model
        self.index_patient = index_patient
        self.relative_objects = self._get_relatives(index_patient)
        self.linkage_form_name = "ClinicalData"
        self.linkage_section_code = "fhDateSection"
        self.linkage_cde_code = "CDEIndexOrRelative"

    def _change_index(self, obj, new_relationships_map, delete=False):
        old_index_patient = self.index_patient

        if isinstance(obj, Patient):
            patient = obj
        elif isinstance(obj, PatientRelative):
            patient = obj.create_patient_from_myself(self.registry_model, old_index_patient.working_groups)
            patient.save()
        else:
            raise FamilyLinkageError("can't change linkage on a %s" % obj)

        self._set_family_linkage_type(patient, FamilyLinkageType.index)

        for patient_relative in self.relative_objects:
            if patient_relative.pk in new_relationships_map:
                patient_relative.relationship = new_relationships_map[pk]
                patient_relative.patient = self.index_patient
                patient_relative.save()
            else:
                raise FamilyManagementError("change index : all relative relationships but be remapped")

    def _set_family_linkage(self, patient, family_linkage_type):
        # These are currently FH form_name and sections
        patient.set_form_value(self.registry_model.code,
                               self.linkage_form_name,
                               self.linkage_section_code,
                               self.linkage_cde_code,
                               family_linkage_type)

    def do(self, action_dict):
        pass


class FamilyLinkageView(View):
    def get(self, request):
        pass

    def post(self, request, reg_code):

        # start transaction ?
        try:
            registry_model = Registry.objects.get(code=reg_code)
            action_data = {}

            for action in action_data["actions"]:
                src_index_patient_id = action["source_index_patient"]
                index_patient = Patient.objects.get(pk=src_index_patient_id)
                flm = FamilyLinkageManager(registry_model, index_patient)
                flm.do(action)

        except FamilyLinkageError, err:
            pass







