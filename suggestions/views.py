from rest_framework.viewsets import ModelViewSet
from .models import Suggestion
from .serializers import SuggestionSerializer

class SuggestionViewSet(ModelViewSet):
    queryset = Suggestion.objects.all()
    serializer_class = SuggestionSerializer
