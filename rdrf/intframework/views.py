import json
import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, Http404
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django_redis import get_redis_connection
from intframework.hub import Client, MockClient
from intframework.updater import HL7Handler
from intframework.utils import patient_not_found
from rdrf.helpers.utils import anonymous_not_allowed
from rdrf.models.definition.models import Registry
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IntegrationHubRequestView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, umrn):
        if not settings.HUB_ENABLED:
            raise Http404
        registry_model = Registry.objects.get(code=registry_code)
        user_model = request.user
        hl7message = self._get_hub_response(registry_model, user_model, umrn)
        if hl7message:
            if patient_not_found(hl7message):
                client_response_dict = {"status": "not_found"}
            else:
                self._setup_redis_config(registry_code)
                hl7_handler = HL7Handler(umrn=umrn, hl7message=hl7message)
                response_data = hl7_handler.handle()
                self._setup_message_router_subscription(registry_model.code, umrn)
                client_response_dict = response_data
                client_response_dict["status"] = "success"
        else:
            client_response_dict = {"status": "fail"}

        return HttpResponse(json.dumps(client_response_dict, cls=DjangoJSONEncoder))

    def _setup_redis_config(self, registry_code):
        from rdrf.helpers.blackboard_utils import set_registry_config
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
            try:
                response_message = hub.activate_subscription(umrn)
                if patient_not_found(response_message):
                    logger.error(f"No PID segment in activate subscription for {umrn}")
                else:
                    logger.info(f"patient {umrn} subscribed for updates")
            except Exception as ex:
                logger.error(f"Error subscriping patient: {ex}")

            return hub_data["message"]
        else:
            logger.info("hub request failed")
            return None

    def _setup_message_router_subscription(self, registry_code, umrn):
        logger.info(f"setting up hub subscription for registry code {registry_code} umrn {umrn}")
        conn = get_redis_connection("blackboard")
        conn.sadd(f"umrns:{registry_code}", umrn)
