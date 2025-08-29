from rest_framework.viewsets import ModelViewSet
from .models import Point
from .serializers import PointSerializer

class PointViewSet(ModelViewSet):
    queryset = Point.objects.all()
    serializer_class = PointSerializer
