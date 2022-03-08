import json
import logging
import socket
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, Http404
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django_redis import get_redis_connection
from intframework.hub import Client, MockClient
from intframework.updater import HL7Handler
from intframework.models import HL7Message
from intframework.utils import patient_subscribed
from intframework.utils import patient_found
from rdrf.helpers.utils import anonymous_not_allowed
from rdrf.models.definition.models import Registry
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HubResult:
    CONNECTION_ERROR = "connection_error"
    SUCCESS = "success"
    FAIL = "fail"
    NOT_FOUND = "not_found"


class IntegrationHubRequestView(View):
    @method_decorator(anonymous_not_allowed)
    @method_decorator(login_required)
    def get(self, request, registry_code, umrn):
        logger.info(f"patient query for umrn [{umrn}]")
        umrn = umrn.strip().upper()
        logger.info(f"hub query by {request.user} for umrn [{umrn}]")
        self._setup_redis_config(registry_code)
        if not settings.HUB_ENABLED:
            logger.error("hub query not enabled in settings!")
            raise Http404
        registry_model = Registry.objects.get(code=registry_code)
        user_model = request.user
        hub_response = self._get_hub_response(registry_model, user_model, umrn)
        if hub_response["result"] == HubResult.CONNECTION_ERROR:
            logger.error("hub query failed: connection error")
            client_response_dict = {"status": HubResult.CONNECTION_ERROR}
        elif hub_response["result"] == HubResult.SUCCESS:
            logger.info("hub query succeeded - message returned")
            hl7message = hub_response["hl7message"]
            if not patient_found(hl7message):
                logger.error("hub query error: no patient in response message")
                client_response_dict = {"status": HubResult.NOT_FOUND}
            else:
                logger.info("hub query: patient found in response")
                logger.info(f"setup redis config for {registry_code}")
                hl7_handler = HL7Handler(umrn=umrn, hl7message=hl7message, username=request.user.username)
                response_data = hl7_handler.handle()
                client_response_dict = response_data
                client_response_dict["status"] = HubResult.SUCCESS
                self._setup_message_router_subscription(registry_model.code, umrn)
                try:
                    self._send_subscription_request(registry_model, user_model, umrn)
                except Exception as ex:
                    logger.error(f"Failed to subscribe {umrn}: {ex}")

        else:
            logger.error(f"hub unknown hub result: {hub_response['result']}")
            client_response_dict = {"status": HubResult.FAIL}

        return HttpResponse(json.dumps(client_response_dict, cls=DjangoJSONEncoder))

    def _send_subscription_request(self, registry_model, user_model, umrn):
        logger.info(f"activating subscription for {umrn} ...")
        hub = self._get_hub(registry_model, user_model)
        if hub is None:
            raise Exception("Could not connect to hub to activate subscription")
        else:
            from registry.patients.models import Patient
            from intframework.utils import get_event_code
            result_message = hub.activate_subscription(umrn)
            try:
                result_event_code = get_event_code(result_message)
            except Exception:
                result_event_code = "????"
            result_model = HL7Message()
            result_model.event_code = result_event_code
            result_model.username = user_model.username
            result_model.registry_code = registry_model.code
            patient_model = Patient.objects.get(umrn=umrn)
            result_model.patient_id = patient_model.id
            result_model.umrn = umrn
            result_model.content = str(result_message)
            result_model.state = "R"
            result_model.save()

            if not patient_subscribed(result_message):
                result_model.error_message = "No AA - not subscribed?"
                result_model.save()
                logger.error("No AA in subscription result - not subscribed?")
            else:
                logger.info(f"{umrn} is subscribed for further updates")

    def _setup_redis_config(self, registry_code):
        from rdrf.helpers.blackboard_utils import set_registry_config
        set_registry_config(registry_code)

    def _get_hub(self, registry_model, user_model):
        client_class: Any
        if settings.HUB_ENDPOINT == "mock":
            client_class = MockClient
            logger.info("using mock hub client")
        else:
            logger.info("using real hub client")
            client_class = Client

        try:
            hub = client_class(registry_model,
                               user_model,
                               settings.HUB_ENDPOINT,
                               settings.HUB_PORT)
            return hub
        except socket.gaierror as ge:
            logger.error(ge)
            return None
        except Exception as ex:
            logger.error(ex)
            return None

    def _get_hub_response(self, registry_model, user_model, umrn: str) -> Optional[dict]:
        logger.info(f"getting hub response for umrn {umrn}")
        hub = self._get_hub(registry_model, user_model)
        if hub is None:
            return {"result": HubResult.CONNECTION_ERROR}

        hub_data: dict = hub.get_data(umrn)

        if "status" in hub_data and hub_data["status"] == HubResult.SUCCESS:
            logger.info(f"hub request succeeded for {umrn}")
            hl7_message = hub_data["message"]

            return {"result": HubResult.SUCCESS,
                    "hl7message": hl7_message}
        else:
            logger.info(f"hub request failed for {umrn}")
            return {"result": HubResult.FAIL}

    def _setup_message_router_subscription(self, registry_code, umrn):
        logger.info(f"setting up hub subscription for registry code {registry_code} umrn {umrn}")
        conn = get_redis_connection("blackboard")
        conn.sadd(f"umrns:{registry_code}", umrn)
