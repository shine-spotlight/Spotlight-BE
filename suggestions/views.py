from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from .models import Suggestion
from .serializers import SuggestionSerializer

class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = Suggestion.objects.all()
    serializer_class = SuggestionSerializer

    @action(detail=True, methods=["patch"])
    def accept(self, request, pk=None):
        suggestion = self.get_object()
        suggestion.is_accepted = True
        suggestion.save()
        return Response(SuggestionSerializer(suggestion).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        suggestion = self.get_object()
        suggestion.is_accepted = False
        suggestion.save()
        return Response(SuggestionSerializer(suggestion).data, status=status.HTTP_200_OK)
    
    

