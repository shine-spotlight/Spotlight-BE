from rest_framework.viewsets import ModelViewSet
from .models import SpaceAvailableDate
from .serializers import SpaceAvailableDateSerializer

class SpaceAvailableDateViewSet(ModelViewSet):
    queryset = SpaceAvailableDate.objects.all()
    serializer_class = SpaceAvailableDateSerializer
