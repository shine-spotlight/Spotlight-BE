"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet
from artists.views import ArtistViewSet
from spaces.views import SpaceViewSet
from categories.views import CategoryViewSet  # ✅ import 추가
from equipmentcategories.views import EquipmentCategoryViewSet

from artistequipments.views import ArtistEquipmentViewSet
from spaceequipments.views import SpaceEquipmentViewSet

from suggestions.views import SuggestionViewSet
from likes.views import LikeViewSet
from notifications.views import NotificationViewSet
from postings.views import PostingViewSet
from points.views import PointViewSet
from spaceavailabledates.views import SpaceAvailableDateViewSet















router = DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'artists', ArtistViewSet)
router.register(r'spaces', SpaceViewSet)
router.register(r'categories', CategoryViewSet)  # ✅ 등록
router.register(r'equipmentcategories', EquipmentCategoryViewSet)
router.register(r'artistequipments', ArtistEquipmentViewSet)
router.register(r'spaceequipments', SpaceEquipmentViewSet)
router.register(r'suggestions', SuggestionViewSet)
router.register(r'likes', LikeViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'postings', PostingViewSet)
router.register(r'points', PointViewSet)
router.register(r'spaceavailabledates', SpaceAvailableDateViewSet)




urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    
]





