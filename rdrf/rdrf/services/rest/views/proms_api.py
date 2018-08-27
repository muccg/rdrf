from rest_framework import generics
from rdrf.models.definition.models import CommonDataElement

class QuestionEndpoint(generics.RetrieveUpdateDestroyAPIView):
    queryset = CommonDataElement.objects.all()
    lookup_field = 'code'
