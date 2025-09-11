import requests
import os
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token

from .models import User
from .serializers import UserSerializer


def bad_request(detail: str, field: str = "non_field_error", extra=None):
    payload = {"detail": detail, "code": "invalid_param", "field": field}
    if extra:
        payload["error"] = extra
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


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
            "redirect_uri": os.environ.get("KAKAO_REDIRECT_URI"),
            "code": code,
        }
        kakao_secret = os.environ.get("KAKAO_CLIENT_SECRET")
        if kakao_secret:
            data["client_secret"] = kakao_secret

        try:
            token_resp = requests.post(token_url, data=data, timeout=5)
            resp_json = token_resp.json()
        except Exception as e:
            return Response(
                {"detail": "카카오 토큰 요청 실패", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        print("KAKAO TOKEN RESP:", resp_json)  # 🔎 서버 로그 확인용

        if token_resp.status_code != 200:
            return Response(
                {
                    "detail": "카카오 토큰 교환 실패",
                    "code": "invalid_param",
                    "field": "code",
                    "error": resp_json,  # 카카오 원본 에러 표시
                },
                status=token_resp.status_code,
            )

        kakao_access_token = resp_json.get("access_token")
        if not kakao_access_token:
            return bad_request(
                "access_token 발급 실패",
                "kakao_access_token",
                extra=resp_json,
            )

        # 2️⃣ 유저 정보 조회
        try:
            headers = {"Authorization": f"Bearer {kakao_access_token}"}
            resp = requests.get("https://kapi.kakao.com/v2/user/me", headers=headers, timeout=5)
            user_info = resp.json()
        except Exception as e:
            return Response(
                {"detail": "카카오 사용자 정보 요청 실패", "error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        print("KAKAO USER INFO:", user_info)  # 🔎 서버 로그 확인용

        if resp.status_code != 200:
            return bad_request(
                "카카오 사용자 정보 조회 실패",
                "kakao_access_token",
                extra=user_info,
            )

        kakao_id = user_info.get("id")
        kakao_account = user_info.get("kakao_account", {})
        email = kakao_account.get("email") or f"{kakao_id}@kakao-user.com"

        if not kakao_id:
            return bad_request(
                "카카오 사용자 ID를 가져올 수 없습니다",
                "kakao_id",
                extra=user_info,
            )

        # 3️⃣ 유저 생성/조회
        user, _ = User.objects.get_or_create(
            kakao_id=str(kakao_id),
            defaults={"role": ""},
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
