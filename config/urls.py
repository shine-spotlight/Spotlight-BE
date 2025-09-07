"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

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


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
]
