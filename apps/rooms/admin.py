from django.contrib import admin
from apps.rooms.models import Room, RoomType

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'property', 'base_price_per_night', 'max_occupancy')
    search_fields = ('name', 'property__name')
    list_filter = ('tenant', 'property')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'property', 'room_type', 'floor', 'status')
    search_fields = ('room_number', 'property__name')
    list_filter = ('tenant', 'property', 'status')
