from rest_framework.routers import DefaultRouter
from apps.bookings.views import BookingViewSet

router = DefaultRouter()
router.register(r'', BookingViewSet, basename='booking')

urlpatterns = router.urls
