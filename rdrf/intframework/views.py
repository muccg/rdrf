import json
from django.views.generic.base import View
from django.http import HttpResponse, Http404
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from .. models.py import DataRequest  # , DATAREQUEST_STATES
from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import anonymous_not_allowed
from intframework.hub import Client
from intframework.hl7 import Hl7Transformer
from django_redis import get_redis_connection


import logging
logger = logging.getLogger(__name__)


class IntegrationHubRequestView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, umrn):
        if not settings.HL7_ENABLED:
            raise Http404
        registry_model = Registry.objects.get(code=registry_code)
        user_model = request.user
        response_data = self._get_hub_response(registry_model, user_model, umrn)
        if response_data["status"] == "success":
            self._setup_message_router_subscription(registry_model.code, umrn)
        return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))

    def _get_hub_response(self, registry_model, user_model, umrn: str) -> dict:
        hub = Client(registry_model,
                     user_model,
                     settings.HL7_HUB_ENDPOINT,
                     settings.HL7_HUB_PORT)
        hl7_response = hub.get_data(umrn)
        if hl7_response["status"] == "success":
            transformer = Hl7Transformer()
            response_data = transformer.transform(hl7_response)
            response_data["status"] = "success"
        else:
            response_data = {"status": "fail"}
        return response_data

    def _setup_message_router_subscription(self, registry_code, umrn):
        logger.info("setting up hub subscription for umrn {umrn}")
        conn = get_redis_connection("blackboard")
        conn.sadd(f"{registry_code}:umrns", umrn)


class DataIntegrationUpdate(View):
    """
    Message Router will send HL7 data for the right URMN here
    """

    def post(self, request, umrn):
        external_data_json = request.body

        try:
            external_data = self._parse_json(external_data_json)

        except JSONParseError as jpe:
            logger.error(jpe)
            pass

        try:
            dr = DataRequest.objects.get(umrn=umrn,
                                         state="requested")

            dr.external_data_json = external_data_json
            dr.state = "received"
            dr.save()
            try:
                external_data = json.loads(external_data_json)
                dr.translate(external_data)
                dr.save()
            except Exception as ex:
                dr.state = "error"
                dr.error_message = str(ex)
                dr.save()

        except DataRequest.DoesNotExist:
            # a subscription?
            try:
                logger.info("TODO: get DataSubscription object")
                """
                ds = DataSubscription.objects.get(umrn=umrn)

                dsi = DataSubcriptionItem(subcription=ds)
                dsi.external_data_json = external_data_json
                dsi.state = "received"
                dsi.save()
                """
            except Exception as ex:
                logger.error(ex)
                pass

    def _parse_json(self, json_data):
        try:
            data = json.loads(json_data)
            return data
        except Exception as ex:
            raise JSONParseError(ex)
