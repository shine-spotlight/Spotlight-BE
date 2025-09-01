from rest_framework import viewsets
from .models import Suggestion
from .serializers import SuggestionSerializer

class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all()
    serializer_class = SuggestionSerializer
