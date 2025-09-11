import requests
import os
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token

from .models import User
from .serializers import UserSerializer


def bad_request(detail: str, field: str = "non_field_error"):
    return Response(
        {"detail": detail, "code": "invalid_param", "field": field},
        status=status.HTTP_400_BAD_REQUEST,
    )


def forbidden(detail: str, field: str = "user_pk"):
    return Response(
        {"detail": detail, "code": "permission_denied", "field": field},
        status=status.HTTP_403_FORBIDDEN,
    )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    # ✅ 카카오 로그인 콜백 (인가 코드 → access_token → 유저 인증)
    @action(detail=False, methods=["get"], url_path="auth/kakao/callback")
    def kakao_callback(self, request):
        code = request.query_params.get("code")
        if not code:
            return bad_request("인가 코드(code)가 필요합니다", "code")

        # 1️⃣ 토큰 교환
        token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": os.environ.get("KAKAO_CLIENT_ID"),
            "client_secret": os.environ.get("KAKAO_CLIENT_SECRET"),
            "redirect_uri": os.environ.get("KAKAO_REDIRECT_URI"),
            "code": code,
        }
        token_resp = requests.post(token_url, data=data)
        if token_resp.status_code != 200:
            return bad_request("카카오 토큰 교환 실패", "code")

        kakao_tokens = token_resp.json()
        kakao_access_token = kakao_tokens.get("access_token")
        if not kakao_access_token:
            return bad_request("access_token 발급 실패", "kakao_access_token")

        # 2️⃣ 유저 정보 조회
        headers = {"Authorization": f"Bearer {kakao_access_token}"}
        resp = requests.get("https://kapi.kakao.com/v2/user/me", headers=headers)
        if resp.status_code != 200:
            return bad_request("카카오 사용자 정보 조회 실패", "kakao_access_token")

        kakao_data = resp.json()
        kakao_id = kakao_data.get("id")
        kakao_account = kakao_data.get("kakao_account", {})
        email = kakao_account.get("email") or f"{kakao_id}@kakao-user.com"

        if not kakao_id:
            return bad_request("카카오 사용자 ID를 가져올 수 없습니다", "kakao_id")

        # 3️⃣ 유저 생성/조회
        user, _ = User.objects.get_or_create(
            kakao_id=kakao_id,
            defaults={"role": ""}  # role은 이후 type 입력 API에서 지정
        )

        # 4️⃣ 장고 토큰 발급
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "accessToken": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

    # ✅ 로그아웃
    @action(detail=False, methods=["post"], url_path="auth/kakao/logout")
    def kakao_logout(self, request):
        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()
        return Response({"message": "Logged out successfully."}, status=200)
