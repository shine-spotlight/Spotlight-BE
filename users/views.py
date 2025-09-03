from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    # POST /api/v1/users/type/
    @action(detail=True, methods=['post'])
    def type(self, request, pk=None):
        user = self.get_object()
        role = request.data.get('role')
        if role not in ['artist', 'space']:
            return Response({"error": "role must be 'artist' or 'space'"},
                            status=status.HTTP_400_BAD_REQUEST)
        user.role = role
        user.save()
        return Response(UserSerializer(user).data)

    # POST /api/v1/users/info/
    @action(detail=True, methods=['post'])
    def info(self, request, pk=None):
        user = self.get_object()
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({"error": "phone_number is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        user.phone_number = phone_number
        user.save()
        return Response(UserSerializer(user).data)

    # POST /api/v1/auth/kakao/login/
    @action(detail=False, methods=['post'], url_path='auth/kakao/login')
    def kakao_login(self, request):
        kakao_id = request.data.get('kakao_id')
        if not kakao_id:
            return Response({"error": "kakao_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(kakao_id=kakao_id)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    # POST /api/v1/auth/kakao/logout/
    @action(detail=False, methods=['post'], url_path='auth/kakao/logout')
    def kakao_logout(self, request):
        return Response({"message": "Logged out successfully."},
                        status=status.HTTP_200_OK)
