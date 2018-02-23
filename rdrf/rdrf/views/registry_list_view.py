from django.shortcuts import render
from django.views.generic.base import View
from rdrf.models.definition.models import Registry


class RegistryListView(View):
    def get(self, request):
        return render(request, 'rdrf_cdes/portfolio.html', {
            "registries": list(Registry.objects.all())
        })
