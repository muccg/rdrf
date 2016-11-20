import logging

from django.views.generic import View
from django.http import HttpResponse

from .models import FDP, Catalog, Dataset, Distribution, Patient


logger = logging.getLogger(__name__)


class FDPBaseView(View):
    model = FDP

    def get(self, request, *args, **kwargs):
        model = self.model_class(request.build_absolute_uri(), *args, **kwargs)

        g = model.load_graph()

        return HttpResponse(g.serialize(format='turtle'), content_type='text/turtle')


class FDPRootView(FDPBaseView):
    model_class = FDP


class FDPCatalogView(FDPBaseView):
    model_class = Catalog


class FDPDatasetView(FDPBaseView):
    model_class = Dataset


class FDPDistributionView(FDPBaseView):
    model_class = Distribution


class FDPPatientView(FDPBaseView):
    model_class = Patient
