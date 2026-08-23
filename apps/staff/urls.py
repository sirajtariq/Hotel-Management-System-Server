from rest_framework.routers import DefaultRouter
from apps.staff.views import StaffProfileViewSet

router = DefaultRouter()
router.register(r'', StaffProfileViewSet, basename='staff')

urlpatterns = router.urls
