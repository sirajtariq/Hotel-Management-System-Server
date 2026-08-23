from decimal import Decimal
from rest_framework.exceptions import ValidationError
from apps.rooms.models import Room, RoomType
from apps.properties.models import Property
from apps.tenants.models import Tenant

class RoomService:
    @staticmethod
    def create_room_type(tenant: Tenant, property_obj: Property, name: str, base_price_per_night: Decimal, max_occupancy: int = 2, description: str = '') -> RoomType:
        """
        SSOT function to create a room type.
        """
        if property_obj.tenant_id != tenant.id:
            raise ValidationError({'property': 'Property does not belong to user tenant.'})

        if RoomType.objects.filter(property=property_obj, name=name).exists():
            raise ValidationError({'name': 'Room type with this name already exists for this property.'})

        room_type = RoomType.objects.create(
            tenant=tenant,
            property=property_obj,
            name=name,
            base_price_per_night=base_price_per_night,
            max_occupancy=max_occupancy,
            description=description
        )
        return room_type

    @staticmethod
    def create_room(tenant: Tenant, property_obj: Property, room_type: RoomType, room_number: str, floor: str = '', status: str = 'AVAILABLE') -> Room:
        """
        SSOT function to create a room.
        """
        if property_obj.tenant_id != tenant.id or room_type.tenant_id != tenant.id:
            raise ValidationError({'tenant': 'Property/RoomType tenant mismatch.'})

        if room_type.property_id != property_obj.id:
            raise ValidationError({'room_type': 'RoomType does not belong to the selected property.'})

        if Room.objects.filter(property=property_obj, room_number=room_number).exists():
            raise ValidationError({'room_number': 'Room with this number already exists in this property.'})

        if tenant.max_rooms is not None:
            current_count = Room.objects.filter(tenant=tenant).count()
            if current_count >= tenant.max_rooms:
                raise ValidationError(f"Room limit reached for this subscription plan (Limit: {tenant.max_rooms}). Please contact SuperAdmin to upgrade.")

        room = Room.objects.create(

            tenant=tenant,
            property=property_obj,
            room_type=room_type,
            room_number=room_number,
            floor=floor,
            status=status
        )
        return room

    @staticmethod
    def update_room_status(room: Room, new_status: str) -> Room:
        """
        SSOT function to update room operational status.
        """
        valid_statuses = [choice[0] for choice in Room.STATUS_CHOICES]
        if new_status not in valid_statuses:
            raise ValidationError({'status': f'Invalid room status. Must be one of {valid_statuses}'})
        
        room.status = new_status
        room.save(update_fields=['status', 'updated_at'])
        return room
