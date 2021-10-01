import json
from django.views.generic.base import View
from django.http import HttpResponse, Http404
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from intframework.models import DataRequest  # , DATAREQUEST_STATES
from rdrf.models.definition.models import Registry
from rdrf.helpers.utils import anonymous_not_allowed
from intframework.hub import Client, MockClient
from intframework.updater import PatientCreator
from django_redis import get_redis_connection
from typing import Any, Optional

import logging
logger = logging.getLogger(__name__)


class IntegrationHubRequestView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, umrn):
        logger.info(f"hub request from {request.user} for {umrn}")
        if not settings.HUB_ENABLED:
            logger.info("hub not enabled - returning 404")
            raise Http404
        logger.debug(f"hub request {registry_code} {umrn}")
        registry_model = Registry.objects.get(code=registry_code)
        user_model = request.user
        response_data = self._get_hub_response(registry_model, user_model, umrn)
        if response_data["status"] == "success":
            patient_creator = PatientCreator()
            patient = patient_creator.create_patient(response_data)
            self._setup_redis_config(registry_code)
            logger.info("hub request returned data so subscribing in redis")
            self._setup_message_router_subscription(registry_model.code, umrn)
        logger.debug(f"response data = {response_data}")
        return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))

    def _setup_redis_config(self, registry_code):
        from rdrf.helpers.blackboard_utils import has_registry_config
        from rdrf.helpers.blackboard_utils import set_registry_config
        if not has_registry_config(registry_code):
            set_registry_config(registry_code)

    def _get_hub_response(self, registry_model, user_model, umrn: str) -> Optional[dict]:
        client_class: Any

        if settings.HUB_ENDPOINT == "mock":
            client_class = MockClient
            logger.info("using mock hub client")
        else:
            client_class = Client

        hub = client_class(registry_model,
                           user_model,
                           settings.HUB_ENDPOINT,
                           settings.HUB_PORT)

        hub_data: dict = hub.get_data(umrn)

        if "status" in hub_data and hub_data["status"] == "success":
            logger.info("got hl7 message from hub - creating update dictionary")
            return self._get_update_dict(hub_data)
        else:
            logger.info("hub request failed")
            return None

    def _get_update_dict(self, hub_data: dict) -> Optional[dict]:
        from intframework.models import HL7Mapping
        from intframework.utils import get_event_code
        logger.debug("in _get_update_dict")
        hl7_message = hub_data["message"]
        logger.debug(f"hl7 message = {hl7_message}")
        event_code = get_event_code(hl7_message)
        logger.debug(f"event code = {event_code}")
        try:
            hl7_mapping = HL7Mapping.objects.get(event_code=event_code)
            logger.info("got mapping")
            update_dict = hl7_mapping.parse(hl7_message)
            logger.info("parsed message to create update_dict")
            logger.info(f"update_dict = {update_dict}")
            return update_dict

        except HL7Mapping.DoesNotExist:
            logger.error(f"mapping doesn't exist Unknown message event code: {event_code}")
            return None
        except HL7Mapping.MultipleObjectsReturned:
            logger.error("Multiple message mappings for event code: {event_code}")
            return None

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
