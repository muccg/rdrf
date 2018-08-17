from django.shortcuts import render
from django.views.generic.base import View

class PromsView(View):
    def get(self, request):
        context = {"production": False}
        return render(request, "proms/proms.html", context)
