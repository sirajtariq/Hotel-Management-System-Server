from rest_framework.routers import DefaultRouter
from apps.properties.views import PropertyViewSet

router = DefaultRouter()
router.register(r'', PropertyViewSet, basename='property')

urlpatterns = router.urls
