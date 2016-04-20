from django import forms
from django.shortcuts import render_to_response, RequestContext
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.base import View
from django.template.context_processors import csrf
from django.http import Http404
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.db import transaction

from rdrf.models import Registry
from registry.patients.models import Patient, PatientRelative
from django.contrib import messages

import logging

logger = logging.getLogger("registry_log")


class FamilyLinkageError(Exception):
    pass


class FamilyLinkageType:
    index = "fh_is_index"
    relative = "fh_is_relative"


class MongoUndo(object):
    def __init__(self, patient, linkage_type):
        self.patient = patient
        self.linkage_type = linkage_type
        self.reverse_op = {FamilyLinkageType.index: FamilyLinkageType.relative,
                           FamilyLinkageType.relative: FamilyLinkageType.index}

    def __call__(self):
        reversed_value = self.reverse_op[self.linkage_type]
        self.patient.set_form_value("fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative", reversed_value)


class FamilyLinkageManager(object):
    def __init__(self,  registry_model, packet):
        self.registry_model = registry_model
        self.packet = packet
        logger.debug("packet = %s" % self.packet)
        if not registry_model.has_feature("family_linkage"):
            raise FamilyLinkageError("need family linkages feature to use FamilyManager")
        self.index_dict = self.packet["index"]
        self.original_index_dict = self.packet["original_index"]
        self.original_index = int(self.original_index_dict["pk"])

        self.relatives = self.packet["relatives"]
        self.index_patient = self._get_index_patient()

        self.working_groups = [wg for wg in self.index_patient.working_groups.all()]
        self.mongo_undos = []

    def _get_index_patient(self):
        try:
            return Patient.objects.get(pk=self.original_index)
        except Patient.DoesNotExist:
            raise FamilyLinkageError("original index patient does not exist")

    def run(self):
        if self._index_changed():
            logger.debug("index has changed")
            self._update_index()
        else:
            logger.debug("index unchanged")
            self._update_relatives()

    def _update_relatives(self):
        for relative_dict in self.relatives:
            if relative_dict['class'] == "PatientRelative":
                rel = PatientRelative.objects.get(pk=relative_dict["pk"])
                if rel.relationship != relative_dict["relationship"]:
                    rel.relationship = relative_dict["relationship"]
                    rel.save()
            elif relative_dict['class'] == "Patient":
                patient = Patient.objects.get(pk=relative_dict["pk"])
                rel = PatientRelative()
                rel.date_of_birth = patient.date_of_birth
                rel.patient = self.index_patient
                rel.given_names = relative_dict["given_names"]
                rel.family_name = relative_dict["family_name"]
                rel.relationship = relative_dict["relationship"]
                rel.relative_patient = patient
                rel.save()
                self._set_as_relative(patient)

    def _index_changed(self):
        if self.original_index_dict["class"] != self.index_dict["class"]:
            # ie patient relative being dragged to become an index
            return True
        else:
            return self.original_index != int(self.index_dict["pk"])

    def _update_index(self):
        logger.debug("updating index")
        old_index_patient = self.index_patient
        logger.debug("old index = %s" % old_index_patient)

        if self.index_dict["class"] == "Patient":
            logger.debug("updating index from Patient")
            new_index_patient = Patient.objects.get(pk=self.index_dict["pk"])
            logger.debug("new_index_patient = %s" % new_index_patient)
            self._change_index(old_index_patient, new_index_patient)

        elif self.index_dict["class"] == "PatientRelative":
            patient_relative = PatientRelative.objects.get(pk=self.index_dict["pk"])
            logger.debug("updating index from patient_relative %s" % patient_relative)
            if patient_relative.relative_patient:
                logger.debug("patient has been created from this relative so setting index to it")
                self._change_index(old_index_patient, patient_relative.relative_patient)
                logger.debug("deleting patient relative %s" % patient_relative)
                patient_relative.delete()
            else:
                # create a new patient from relative first
                logger.debug("setting PatientRelatibe with no patient to index - need to create patient first")
                new_patient = patient_relative.create_patient_from_myself(self.registry_model, self.working_groups)
                logger.debug("new patient created from relative = %s" % new_patient)
                self._change_index(old_index_patient, new_patient)
                logger.debug("changed index ok to new patient")
                patient_relative.delete()
                logger.debug("deleted old patient relative")

    def _change_index(self, old_index_patient, new_index_patient):
        self._set_as_index_patient(new_index_patient)
        updated_rels = set([])
        original_relatives = set([r.pk for r in old_index_patient.relatives.all()])
        for relative_dict in self.relatives:
            if relative_dict["class"] == "PatientRelative":
                patient_relative = PatientRelative.objects.get(pk=relative_dict["pk"])
                patient_relative.patient = new_index_patient
                patient_relative.relationship = relative_dict["relationship"]
                patient_relative.save()
                updated_rels.add(patient_relative.pk)

            elif relative_dict["class"] == "Patient":
                # index 'demoted' : create patient rel object
                patient = Patient.objects.get(pk=relative_dict["pk"])

                new_patient_relative = PatientRelative()
                new_patient_relative.date_of_birth = patient.date_of_birth
                new_patient_relative.patient = new_index_patient
                new_patient_relative.relative_patient = patient
                new_patient_relative.given_names = relative_dict["given_names"]
                new_patient_relative.family_name = relative_dict["family_name"]
                self._set_as_relative(patient)
                new_patient_relative.relationship = relative_dict["relationship"]
                new_patient_relative.save()
                updated_rels.add(new_patient_relative.pk)
            else:
                logger.debug("???? %s" % relative_dict)

        promoted_relatives = original_relatives - updated_rels
        logger.debug("promoted rels = %s" % promoted_relatives)

    def _get_new_relationship(self, relative_pk):
        for item in self.relatives:
            if item["class"] == "PatientRelative" and item["pk"] == relative_pk:
                updated_relationship = item["relationship"]
                return updated_relationship

        return None

    def _add_undo(self, patient, value):
        undo = MongoUndo(patient, value)
        self.mongo_undos.append(undo)

    def _set_as_relative(self, patient):
        patient.set_form_value("fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative", "fh_is_relative")
        logger.debug("set patient %s to relative" % patient)
        self._add_undo(patient, "fh_is_relative")

    def _set_as_index_patient(self, patient):
        patient.set_form_value("fh", "ClinicalData", "fhDateSection", "CDEIndexOrRelative", "fh_is_index")
        logger.debug("set patient %s to index" % patient)
        self._add_undo(patient, "fh_is_index")


class FamilyLinkageView(View):
    @method_decorator(login_required)
    def get(self, request, registry_code, initial_index=None):

        try:
            registry_model = Registry.objects.get(code=registry_code)
            if not registry_model.has_feature("family_linkage"):
                raise Http404("Registry does not support family linkage")

        except Registry.DoesNotExist:
            raise Http404("Registry does not exist")

        context = {}
        context.update(csrf(request))
        context['registry_code'] = registry_code
        context['index_lookup_url'] = reverse("v1:index-list", args=(registry_code,))
        context["initial_index"] = initial_index

        return render_to_response(
            'rdrf_cdes/family_linkage.html',
            context,
            context_instance=RequestContext(request))


    @method_decorator(login_required)
    def post(self, request, registry_code, initial_index=None):
        try:
            import json
            registry_model = Registry.objects.get(code=registry_code)
            packet = json.loads(request.POST["packet_json"])
            logger.debug("packet = %s" % packet)
            self._process_packet(registry_model, packet)
            #messages.add_message(request, messages.SUCCESS, "Linkages updated successfully")
            return HttpResponse("OK")

        except Exception, err:
            #messages.add_message(request, messages.ERROR, "Linkage update failed: %s" % err)
            return HttpResponse("FAIL: %s" % err)

    def _process_packet(self, registry_model,  packet):
        logger.debug("packet = %s" % packet)
        flm = FamilyLinkageManager(registry_model, packet)
        try:
            with transaction.atomic():
                flm.run()

        except Exception, ex:
            for undo in flm.mongo_undos:
                try:
                    undo()
                except Exception, ex:
                    logger.error("could not undo %s" % undo)

            raise ex
