from rest_framework.routers import DefaultRouter
from .views import PointTransactionViewSet

router = DefaultRouter()
router.register(r'points', PointTransactionViewSet, basename='points')

urlpatterns = router.urls
