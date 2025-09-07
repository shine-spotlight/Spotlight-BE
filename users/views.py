from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
# from rest_framework.permissions import IsAuthenticated  # 운영 시 사용 고려
from .models import User
from .serializers import UserSerializer


def bad_request(detail: str, field: str):
    """프로젝트 공통 에러 포맷(400)"""
    return Response(
        {"detail": detail, "code": "invalid_param", "field": field},
        status=status.HTTP_400_BAD_REQUEST,
    )


def forbidden(detail: str, field: str = "user_pk"):
    """프로젝트 공통 에러 포맷(403)"""
    return Response(
        {"detail": detail, "code": "permission_denied", "field": field},
        status=status.HTTP_403_FORBIDDEN,
    )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [IsAuthenticated]  # 운영 시 적용 고려(현 개발/QA 단계에선 주석)

    # POST /api/v1/users/{pk}/type/
    @action(detail=True, methods=['post'])
    def type(self, request, pk=None):
        user = self.get_object()

        # 권한 가드: 본인만 수정 가능 + superuser 예외
        if not request.user.is_superuser:
            req_user_id = getattr(getattr(request, "user", None), "id", None)
            if req_user_id is not None and req_user_id != user.id:
                return forbidden("본인만 수정 가능합니다")

        role = request.data.get("role")
        if role not in ["artist", "space"]:
            return bad_request("role must be 'artist' or 'space'", "role")

        user.role = role
        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    # POST /api/v1/users/{pk}/info/
    @action(detail=True, methods=['post'])
    def info(self, request, pk=None):
        user = self.get_object()

        # 권한 가드: 본인만 수정 가능 + superuser 예외
        if not request.user.is_superuser:
            req_user_id = getattr(getattr(request, "user", None), "id", None)
            if req_user_id is not None and req_user_id != user.id:
                return forbidden("본인만 수정 가능합니다")

        raw = str(request.data.get("phone_number", "")).strip()
        if not raw:
            return bad_request("phone_number is required", "phone_number")

        # 연락처 검증: 숫자만 남기고 010으로 시작하는 11자리
        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) != 11 or not digits.startswith("010"):
            return bad_request("전화번호는 010으로 시작하는 11자리 숫자여야 합니다", "phone_number")

        user.phone_number = digits  # CharField 저장(선행 0 보존)
        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    # POST /api/v1/users/auth/kakao/login/
    @action(detail=False, methods=['post'], url_path='auth/kakao/login')
    def kakao_login(self, request):
        kakao_id = request.data.get("kakao_id")
        if not kakao_id:
            return bad_request("kakao_id is required", "kakao_id")

        # (주의) 서비스 플로우 상: 로그인 → role 선정
        user, _ = User.objects.get_or_create(kakao_id=kakao_id)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    # POST /api/v1/users/auth/kakao/logout/
    @action(detail=False, methods=['post'], url_path='auth/kakao/logout')
    def kakao_logout(self, request):
        # 성공 포맷은 자유, 에러만 공통 포맷 적용
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
