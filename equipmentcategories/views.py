from rest_framework.viewsets import ModelViewSet
from .models import EquipmentCategory
from .serializers import EquipmentCategorySerializer

class EquipmentCategoryViewSet(ModelViewSet):
    queryset = EquipmentCategory.objects.all()
    serializer_class = EquipmentCategorySerializer
