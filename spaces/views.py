from rest_framework.viewsets import ModelViewSet
from .models import Space
from .serializers import SpaceSerializer

class SpaceViewSet(ModelViewSet):
    queryset = Space.objects.all()
    serializer_class = SpaceSerializer
