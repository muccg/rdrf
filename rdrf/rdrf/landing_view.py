from django.shortcuts import render
from django.views.generic.base import View
from .models import Registry


class LandingView(View):
    def get(self, request):
        return render(request, 'rdrf_cdes/index.html', {
            "registries": list(Registry.objects.all())
        })
