from rest_framework.viewsets import ModelViewSet
from .models import SpaceEquipment
from .serializers import SpaceEquipmentSerializer

class SpaceEquipmentViewSet(ModelViewSet):
    queryset = SpaceEquipment.objects.all()
    serializer_class = SpaceEquipmentSerializer
