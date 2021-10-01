import json
from django.views.generic.base import View
from django.http import HttpResponse, Http404
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
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
        if response_data:
            logger.info(f"response data = {response_data}")
            patient_creator = PatientCreator()
            patient = patient_creator.create_patient(response_data)
            logger.info(f"IF created patient {patient}")
            self._setup_redis_config(registry_code)
            logger.info("hub request returned data so subscribing in redis")
            self._setup_message_router_subscription(registry_model.code, umrn)
            client_response_dict = response_data
            client_response_dict["status"] = "success"

        else:
            client_response_dict = {"status": "fail"}
            logger.error("Could not create patient")
        return HttpResponse(json.dumps(client_response_dict, cls=DjangoJSONEncoder))

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
            update_dict = self._get_update_dict(hub_data)
            return update_dict
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
