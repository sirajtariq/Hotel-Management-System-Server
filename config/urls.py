from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.users.views import CustomTokenObtainPairView, get_current_user_session

urlpatterns = [
    path('admin/', admin.site.urls),

    # OpenAPI 3 Schema & UI documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API v1 app endpoints
    path('api/v1/auth/login/', CustomTokenObtainPairView.as_view(), name='auth_login'),
    path('api/v1/auth/me/', get_current_user_session, name='auth_me'),
    path('api/v1/tenants/', include('apps.tenants.urls')),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/roles/', include('apps.users.roles_urls')),
    path('api/v1/properties/', include('apps.properties.urls')),
    path('api/v1/rooms/', include('apps.rooms.urls')),
    path('api/v1/bookings/', include('apps.bookings.urls')),
    path('api/v1/expenses/', include('apps.expenses.urls')),
    path('api/v1/staff/', include('apps.staff.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/restaurant/', include('apps.restaurant.urls')),
    path('api/v1/', include('apps.accounts.urls')),
]

