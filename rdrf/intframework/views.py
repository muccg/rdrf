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
            hl7_handler = HL7Handler(umrn=umrn, hl7message=hl7message)
            response_data = hl7_handler.handle()
            self._setup_redis_config(registry_code)
            self._setup_message_router_subscription(registry_model.code, umrn)
            client_response_dict = response_data
            client_response_dict["status"] = "success"
        else:
            client_response_dict = {"status": "fail"}

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
            return hub_data["message"]
        else:
            logger.info("hub request failed")
            return None

    def _setup_message_router_subscription(self, registry_code, umrn):
        logger.info("setting up hub subscription for umrn {umrn}")
        conn = get_redis_connection("blackboard")
        conn.sadd(f"{registry_code}:umrns", umrn)
