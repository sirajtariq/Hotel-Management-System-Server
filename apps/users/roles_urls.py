from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import RoleViewSet

router = DefaultRouter()
router.register(r'', RoleViewSet, basename='role')

urlpatterns = [
    path('available-permissions/', RoleViewSet.as_view({'get': 'available_permissions'}), name='role_available_permissions'),
    path('', include(router.urls)),
]
