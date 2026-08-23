from rest_framework.routers import DefaultRouter
from apps.rooms.views import RoomViewSet, RoomTypeViewSet

router = DefaultRouter()
router.register(r'types', RoomTypeViewSet, basename='room-type')
router.register(r'', RoomViewSet, basename='room')

urlpatterns = router.urls
