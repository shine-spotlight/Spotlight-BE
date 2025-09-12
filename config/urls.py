"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from rest_framework.authtoken import views
# Swagger / drf-yasg
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from django.conf import settings

# 앱 ViewSet import
from users.views import UserViewSet
from artists.views import ArtistViewSet
from spaces.views import SpaceViewSet
from categories.views import CategoryViewSet
from equipmentcategories.views import EquipmentCategoryViewSet
from artistequipments.views import ArtistEquipmentViewSet
from spaceequipments.views import SpaceEquipmentViewSet
from suggestions.views import SuggestionViewSet
from likes.views import LikeViewSet
from notifications.views import NotificationViewSet
from postings.views import PostingViewSet
from points.views import PointViewSet
from demandapi.views import DemandViewSet
from adminapi.views import AdminViewSet

# 📌 Swagger 기본 정보
schema_view = get_schema_view(
    openapi.Info(
        title="Spotlight Backend API",
        default_version="v1",
        description="Spotlight 프로젝트 API 명세서",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="team@spotlight.com"),
        license=openapi.License(name="MIT"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# 📌 Router 등록
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'artists', ArtistViewSet)
router.register(r'spaces', SpaceViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'equipmentcategories', EquipmentCategoryViewSet)
router.register(r'artistequipments', ArtistEquipmentViewSet)
router.register(r'spaceequipments', SpaceEquipmentViewSet)
router.register(r'suggestions', SuggestionViewSet)
router.register(r'likes', LikeViewSet)
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'postings', PostingViewSet)
router.register(r'points', PointViewSet, basename='points')
router.register(r'demand', DemandViewSet, basename='demand')
router.register(r'admin', AdminViewSet, basename='admin')

# 📌 URL 패턴
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("api-token-auth/", views.obtain_auth_token),

    # Swagger 항상 노출
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

