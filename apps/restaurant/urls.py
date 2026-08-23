from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.restaurant.views import (
    CategoryViewSet, MenuItemViewSet,
    DiningTableViewSet, RestaurantOrderViewSet
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='restaurant-categories')
router.register('items', MenuItemViewSet, basename='restaurant-items')
router.register('tables', DiningTableViewSet, basename='restaurant-tables')
router.register('orders', RestaurantOrderViewSet, basename='restaurant-orders')

urlpatterns = [
    path('', include(router.urls)),
]
