from django.core.exceptions import ValidationError

from rdrf.models import RDRFContext
from rdrf.models import RDRFContextError
from rdrf.models import Registry

from registry.patients.models import Patient

import logging
logger = logging.getLogger(__name__)


class RDRFContextCommandHandler(object):
    COMMANDS = ["activate", "create", "delete"]

    def __init__(self, request, registry_code, patient_id):
        self.request = request
        try:
            self.registry_model = Registry.objects.get(code=registry_code)
        except Registry.DoesNotExist:
            raise RDRFContextError("Registry %s does not exist" % registry_code)

        self.user = request.user
        self.registry_code = registry_code
        self.patient_id = patient_id
        try:
            self.patient_model = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            raise RDRFContextError("Patient %s does not exist" % patient_id)
        logger.debug("set registry model and patient")
        self._sanity_check()
        self.command = None
        self.args = None

    def _sanity_check(self):

        if self.user.in_registry(self.registry_model):
            raise RDRFContextError("User %s not in %s" % (self.user, self.registry_model))

        if not self.patient_model.in_registry(self.registry_code):
            raise RDRFContextError("Patient %s not in %s" % (self.patient_model, self.registry_model))

        logger.debug("passed sanity check")

    def _parse_command(self, rdrf_context_command):
        if "command" in rdrf_context_command:
            self.command = rdrf_context_command['command']
        else:
            raise RDRFContextError("could not parse rdrf context command: No command?: %s" % rdrf_context_command)

        if "args" in rdrf_context_command:
            self.args = rdrf_context_command["args"]
        else:
            raise RDRFContextError("could not parse rdrf context command: No args?: %s" % rdrf_context_command)

        if self.command not in self.COMMANDS:
            raise RDRFContextError("unknown command: %s" % self.command)

    def run(self, rdrf_context_command):

        self._parse_command(rdrf_context_command)

        if self.command == "activate":
            self.run_activate()
        elif self.command == "delete":
            self.run_delete()
        else:
            raise RDRFContextError("Unknown command: %s" % self.command)

    def _owns_context(self, context_model):
        return context_model.context_object.pk == self.patient_model and context_model.registry.code == self.registry_code

    def run_delete(self):
        context_id = self.args[0]
        context_model = RDRFContext.objects.get(pk=context_id)
        if self._owns_context(context_model):
            try:
                context_model.delete()
            except Exception, ex:
                raise RDRFContextError("Could not delete context %s: %s" % (context_id, ex))
        else:
            raise RDRFContextError("Cannot delete a context you don't own")

    def run_activate(self):
        logger.debug("running rdrf context command 'activate'")
        rdrf_context_row_id = self.args[0]
        context_name = self.args[1]
        logger.debug("rdrf_context_row_id = %s" % rdrf_context_row_id)
        rdrf_model_id = self._get_desired_active_context_id(rdrf_context_row_id)

        try:
            if rdrf_context_row_id != "new":
                desired_rdrf_context_model = RDRFContext.objects.get(pk=rdrf_model_id)
            else:
                desired_rdrf_context_model = self._create_new_context(context_name)
        except RDRFContext.DoesNotExist:
            raise RDRFContextError("RDRF Context %s does not exist" % rdrf_context_row_id)

        logger.debug("desired context = %s" % desired_rdrf_context_model)
        logger.debug("desired context reg code = %s" % desired_rdrf_context_model.registry.code)
        logger.debug("reg code = %s" % self.registry_model.code)

        if desired_rdrf_context_model.registry.code != self.registry_model.code:
            raise RDRFContextError("RDRF Context registry %s is not %s" % (desired_rdrf_context_model.registry,
                                                                           self.registry_model))

        logger.debug("content_object = %s" % desired_rdrf_context_model.content_object)

        if desired_rdrf_context_model.content_object.pk != self.patient_model.pk:
            raise RDRFContextError("RDRF Context does not belong to patient supplied")

        # all good
        self.request.session["rdrf_context_id"] = desired_rdrf_context_model.pk
        logger.debug("set rdrf_context_id to %s" % desired_rdrf_context_model.pk)

    def _create_new_context(self, name):
        rdrf_context_model = RDRFContext(registry=self.registry_model, content_object=self.patient_model)
        rdrf_context_model.display_name = name
        try:
            rdrf_context_model.save()
        except ValidationError, verr:
            raise RDRFContextError("Could not create new context %s: %s" % (name, verr.message))
        return rdrf_context_model

    def _get_desired_active_context_id(self, rdrf_context_row_id):
        if rdrf_context_row_id == "new":
            return rdrf_context_row_id
        import re
        logger.debug("rdrf_context_row_id = %s" % rdrf_context_row_id)
        pattern = re.compile("^rdrf_context_(?P<rdrf_context_id>\d+)$")
        m = pattern.match(rdrf_context_row_id)
        if m:
            id_string = m.group('rdrf_context_id')
            id = int(id_string)
            logger.debug("return %s" % id)
            return id
        else:
            raise RDRFContextError("Bad RDRF Context id supplied: %s" % rdrf_context_row_id)
