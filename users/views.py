import requests
import os
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User
from .serializers import UserSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


def bad_request(detail: str, field: str = "non_field_error", extra=None):
    payload = {"detail": detail, "code": "invalid_param", "field": field}
    if extra:
        payload["error"] = extra
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ["kakao_callback"]:  # 로그인은 열어둠
            return [AllowAny()]
        return [IsAuthenticated()]  # 나머지는 토큰 필요

    # ✅ 카카오 로그인 콜백
    @swagger_auto_schema(
        operation_summary="카카오 로그인 콜백",
        operation_description="카카오 OAuth 인가 코드를 받아 access token을 교환하고, 카카오 사용자 정보를 조회한 뒤 서비스 사용자로 등록/로그인 처리합니다. 최종적으로 서비스용 accessToken과 사용자 정보를 반환합니다.",
        manual_parameters=[
            openapi.Parameter(
                name="code",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="카카오 OAuth redirect 후 전달된 authorization code",
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="successfully logged in",
                examples={
                    "application/json": {
                        "accessToken": "string",
                        "user": {"id": 1, "username": "user", "role": "artist", "phone_number": "010-0000-0000"}
                    }
                }
            ),
            400: "bad request"
        },
        tags=["Auth"]
    )
    @action(methods=["get"], detail=False, url_path="auth/kakao/callback")
    def kakao_callback(self, request):
        code = request.query_params.get("code")
        if not code:
            return bad_request("인가 코드(code)가 필요합니다", "code")

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

        token_resp = requests.post(token_url, data=data, timeout=5)
        resp_json = token_resp.json()

        if token_resp.status_code != 200:
            return Response(
                {"detail": "카카오 토큰 교환 실패", "error": resp_json},
                status=token_resp.status_code,
            )

        kakao_access_token = resp_json.get("access_token")
        if not kakao_access_token:
            return bad_request("access_token 발급 실패", "kakao_access_token", extra=resp_json)

        headers = {"Authorization": f"Bearer {kakao_access_token}"}
        resp = requests.get("https://kapi.kakao.com/v2/user/me", headers=headers, timeout=5)
        user_info = resp.json()

        if resp.status_code != 200:
            return bad_request("카카오 사용자 정보 조회 실패", "kakao_access_token", extra=user_info)

        kakao_id = user_info.get("id")
        kakao_account = user_info.get("kakao_account", {})
        phone_number = kakao_account.get("phone_number")

        user, created = User.objects.get_or_create(
            kakao_id=str(kakao_id),
            defaults={"role": None, "is_active": True, "is_staff": False, "phone_number": phone_number},
        )
        if not created and not user.phone_number and phone_number:
            user.phone_number = phone_number
            user.save()

        token, _ = Token.objects.get_or_create(user=user)
        user_data = UserSerializer(user).data

        return Response({"accessToken": token.key, "user": user_data}, status=status.HTTP_200_OK)

    # ✅ 로그아웃
    @swagger_auto_schema(
        operation_summary="카카오 로그아웃",
        operation_description="카카오 인증 토큰을 삭제하여 로그아웃 처리합니다.",
        responses={200: "Logged out successfully."},
        tags=["Auth"]
    )
    @action(methods=["post"], detail=False, url_path="auth/kakao/logout")
    def kakao_logout(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"message": "Logged out successfully."}, status=200)

    # ✅ 내 정보 조회
    @swagger_auto_schema(
        operation_summary="내 정보 조회",
        operation_description="현재 로그인한 사용자의 정보를 반환합니다.",
        responses={200: UserSerializer},
        tags=["User"]
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    # ✅ 내 role 수정
    @swagger_auto_schema(
        operation_summary="내 role 수정",
        operation_description="현재 로그인한 사용자의 role(artist/space)을 수정합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'role': openapi.Schema(type=openapi.TYPE_STRING, description="'artist' 또는 'space'")
            },
            required=['role']
        ),
        responses={200: UserSerializer},
        tags=["User"]
    )
    @action(detail=False, methods=["post"], url_path="type")
    def set_role(self, request):
        role = request.data.get("role")
        if role not in ["artist", "space"]:
            return bad_request("role은 'artist' 또는 'space'만 가능합니다.", "role")
        request.user.role = role
        request.user.save()
        return Response(UserSerializer(request.user).data)

    # ✅ 내 전화번호 수정
    @swagger_auto_schema(
        operation_summary="내 전화번호 수정",
        operation_description="현재 로그인한 사용자의 전화번호를 수정합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="전화번호")
            },
            required=['phone_number']
        ),
        responses={200: UserSerializer},
        tags=["User"]
    )
    @action(detail=False, methods=["post"], url_path="phone")
    def set_phone(self, request):
        phone_number = request.data.get("phone_number")
        if not phone_number:
            return bad_request("phone_number는 필수 입력값입니다.", "phone_number")
        request.user.phone_number = phone_number
        request.user.save()
        return Response(UserSerializer(request.user).data)
