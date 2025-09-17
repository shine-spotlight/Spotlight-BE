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
from artists.models import Artist
from artists.serializers import ArtistSerializer
from spaces.models import Space
from spaces.serializers import SpaceSerializer


def bad_request(detail: str, field: str = "non_field_error", extra=None):
    payload = {"detail": detail, "code": "invalid_param", "field": field}
    if extra:
        payload["error"] = extra
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)

def forbidden(detail: str, field: str = "user_pk"):
    payload = {"detail": detail, "code": "permission_denied", "field": field}
    return Response(payload, status=status.HTTP_403_FORBIDDEN)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ["kakao_callback"]:
            return [AllowAny()]
        return [IsAuthenticated()]

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
                        "user": {"id": 1, "username": "user", "role": "artist", "phone_number": "010-0000-0000"},
                        "isOnboarding": True
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

        # 온보딩 3가지 판단
        is_onboarding = (
            not user.role or
            not user.phone_number or
            not user.kakao_id or user.kakao_id == ""
        )

        is_artistonboarding = None
        if user.role == "artist":
            try:
                artist = Artist.objects.get(user=user)
                artist_onboarding = ArtistSerializer(artist, context={"request": request}).data.get("artist_onboarding", True)
            except Artist.DoesNotExist:
                artist_onboarding = True
            is_artistonboarding = is_onboarding or artist_onboarding

        is_spaceonboarding = None
        if user.role == "space":
            try:
                space = Space.objects.get(user=user)
                space_onboarding = SpaceSerializer(space, context={"request": request}).data.get("space_onboarding", True)
            except Space.DoesNotExist:
                space_onboarding = True
            is_spaceonboarding = is_onboarding or space_onboarding

        return Response({
            "accessToken": token.key,
            "user": user_data,
            "isOnboarding": is_onboarding,
            "is_artistonboarding": is_artistonboarding,
            "is_spaceonboarding": is_spaceonboarding,
        }, status=status.HTTP_200_OK)

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
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(UserSerializer(instance).data)
    # ✅ 내 role 등록
    @swagger_auto_schema(
        operation_summary="내 role 등록",
        operation_description="현재 로그인한 사용자의 role(artist/space)을 등록합니다.",
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
        # 기존: 최초 1회만 설정
        # if request.user.role:
        #      return forbidden("role은 최초 1회만 설정할 수 있습니다.", "role")
        # 변경: 언제든 변경 가능
        request.user.role = role
        request.user.save()
        return Response(UserSerializer(request.user).data, status=200)
        

    # ✅ 내 전화번호 수정
    @swagger_auto_schema(
        operation_summary="내 전화번호 등록",
        operation_description="현재 로그인한 사용자의 전화번호를 등록합니다.",
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
    
    @swagger_auto_schema(
        operation_summary="유저 생성",
        operation_description="새로운 유저를 생성합니다.",
        request_body=UserSerializer,
        responses={201: UserSerializer, 400: "유효성 오류"},
        tags=["User"]
    )
    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=status.HTTP_201_CREATED)
        return bad_request(str(ser.errors))

    @swagger_auto_schema(
        operation_summary="유저 정보 부분 수정",
        operation_description="특정 유저 정보를 부분 수정합니다.",
        request_body=UserSerializer,
        responses={200: UserSerializer, 400: "유효성 오류"},
        tags=["User"]
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=200)
        return bad_request(str(ser.errors))

    @swagger_auto_schema(
        operation_summary="유저 삭제",
        operation_description="특정 유저를 삭제합니다.",
        responses={204: "삭제 성공", 403: "권한 없음"},
        tags=["User"]
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @swagger_auto_schema(auto_schema=None) 
    def list(self, request, *args, **kwargs):
        pass
    
    @swagger_auto_schema(auto_schema=None) 
    def update(self, request, *args, **kwargs):
        pass
    
    @swagger_auto_schema(
        operation_summary="내 정보(me) 조회",
        operation_description="토큰 인증된 사용자의 정보를 반환합니다. (url에 id 없이 /users/me/로 접근)",
        responses={200: UserSerializer},
        tags=["User"]
    )
    @action(detail=False, methods=["get"], url_path="me", permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        토큰 인증된 본인 정보 + 온보딩 여부 반환
        """
        user = request.user

        # 1. 기본 유저 온보딩
        is_onboarding = (
            not user.role or
            not user.phone_number or
            not user.kakao_id or user.kakao_id == ""
        )

        # 2. 아티스트 온보딩 (유저 온보딩 + 아티스트 프로필 온보딩)
        is_artistonboarding = None
        if user.role == "artist":
            try:
                artist = Artist.objects.get(user=user)
                artist_onboarding = ArtistSerializer(artist, context={"request": request}).data.get("artist_onboarding", True)
            except Artist.DoesNotExist:
                artist_onboarding = True
            is_artistonboarding = is_onboarding or artist_onboarding

        # 3. 스페이스 온보딩 (유저 온보딩 + 스페이스 프로필 온보딩)
        is_spaceonboarding = None
        if user.role == "space":
            try:
                space = Space.objects.get(user=user)
                space_onboarding = SpaceSerializer(space, context={"request": request}).data.get("space_onboarding", True)
            except Space.DoesNotExist:
                space_onboarding = True
            is_spaceonboarding = is_onboarding or space_onboarding

        return Response({
            "user": UserSerializer(user).data,
            "isOnboarding": is_onboarding,
            "is_artistonboarding": is_artistonboarding,
            "is_spaceonboarding": is_spaceonboarding,
        })
