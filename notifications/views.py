from rest_framework.viewsets import ModelViewSet
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(ModelViewSet):
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
