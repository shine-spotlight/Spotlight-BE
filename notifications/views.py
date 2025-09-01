from rest_framework import viewsets
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        개별 알림 조회 시 자동으로 is_read=True 처리
        """
        instance = self.get_object()
        if not instance.is_read:
            instance.is_read = True
            instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
