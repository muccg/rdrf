import json
from django.views.generic.base import View
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from .. models.py import DataRequest  # , DATAREQUEST_STATES
from rdrf.models.definition.models import Registry

import logging
logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    pass


class DataIntegrationException(Exception):
    pass


class JSONParseError(IntegrationError):
    pass


class DataApplicationError(IntegrationError):
    pass


class DataRequestView(View):
    def post(self, request, registry_code, umrn):

        try:
            registry = get_object_or_404(Registry, code=registry_code)
            dr = DataRequest.objects.get(umrn=umrn, state="requested", registry=registry)
            token = dr.token
        except DataRequest.DoesNotExist:
            # good
            dr = DataRequest(umrn=umrn,
                             state="requested",
                             registry=registry)
            dr.save()
            dr.send()
            token = dr.token

        response_data = {"request_token": token}

        return HttpResponse(response_data,
                            content_type='application/json')


class DataRequestDataView(View):
    def get(self, request, token):
        dr = get_object_or_404(DataRequest, token=token)
        response_data = {"request_token": token,
                         "data": dr.get_data(),
                         "state": dr.state}

        return HttpResponse(response_data,
                            content_type='application/json')


class DataIntegrationActionView(View):
    def post(self, token):
        dr = get_object_or_404(DataRequest, token=token)
        if dr.state != "completed":
            return HttpResponseBadRequest()
        try:
            dr.apply()
            json_response = {"request_token": token,
                             "status": "succeeded"}
            dr.state = "applied"
            dr.save()

            return HttpResponse(json_response,
                                content_type="application/json")

        except DataIntegrationException as diex:
            dr.state = "error"
            dr.error = diex.message
            dr.save()
            json_response = {"request_token": token,
                             "status": "failed",
                             "error": "An error occurred"}
            return HttpResponse(json_response,
                                status=500,
                                content_type="application/json")


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
