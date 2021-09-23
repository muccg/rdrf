from django.conf import settings
import hl7


class Client:
    def __init__(self, hub_endpoint, hub_port):
        self.hub_endpoint = hub_endpoint
        self.hub_port = hub_port

    def get_data(self, umrn: str) -> dict:
