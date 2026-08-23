from django.contrib import admin
from apps.restaurant.models import (
    Category, MenuItem, MenuItemVariation,
    DiningTable, RestaurantOrder, RestaurantOrderItem
)

class MenuItemVariationInline(admin.TabularInline):
    model = MenuItemVariation
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tenant', 'display_order', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name',)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'base_price', 'has_variations', 'is_available', 'tenant')
    list_filter = ('tenant', 'category', 'is_available', 'has_variations')
    search_fields = ('name', 'description')
    inlines = [MenuItemVariationInline]

@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_number', 'floor_or_section', 'capacity', 'status', 'property', 'tenant')
    list_filter = ('tenant', 'property', 'status', 'floor_or_section')
    search_fields = ('table_number',)

class RestaurantOrderItemInline(admin.TabularInline):
    model = RestaurantOrderItem
    extra = 0
    readonly_fields = ('total_price',)

@admin.register(RestaurantOrder)
class RestaurantOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'order_type', 'customer_name', 'status', 'payment_status', 'grand_total', 'created_at', 'tenant')
    list_filter = ('tenant', 'property', 'order_type', 'status', 'payment_status')
    search_fields = ('order_number', 'customer_name', 'room_number')
    inlines = [RestaurantOrderItemInline]
