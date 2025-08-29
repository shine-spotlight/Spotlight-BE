from rest_framework.viewsets import ModelViewSet
from .models import ArtistEquipment
from .serializers import ArtistEquipmentSerializer

class ArtistEquipmentViewSet(ModelViewSet):
    queryset = ArtistEquipment.objects.all()
    serializer_class = ArtistEquipmentSerializer
