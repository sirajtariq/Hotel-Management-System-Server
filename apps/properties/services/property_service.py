from decimal import Decimal
from rest_framework.exceptions import ValidationError
from apps.properties.models import Property
from apps.tenants.models import Tenant

class PropertyService:
    @staticmethod
    def create_property(tenant: Tenant, name: str, address: str, city: str, country: str = 'USA', phone: str = '', email: str = '', monthly_rent: Decimal = Decimal('0.0'), status: str = 'ACTIVE') -> Property:
        """
        SSOT function to create a new Property.
        """
        if Property.objects.filter(tenant=tenant, name=name).exists():
            raise ValidationError({'name': 'Property with this name already exists for this tenant.'})

        if tenant.max_properties is not None:
            current_count = Property.objects.filter(tenant=tenant).count()
            if current_count >= tenant.max_properties:
                raise ValidationError(f"Property limit reached for this subscription plan (Limit: {tenant.max_properties}). Please contact SuperAdmin to upgrade.")

        property_obj = Property.objects.create(

            tenant=tenant,
            name=name,
            address=address,
            city=city,
            country=country,
            phone=phone,
            email=email,
            monthly_rent=monthly_rent,
            status=status
        )
        return property_obj

    @staticmethod
    def update_property(property_obj: Property, **kwargs) -> Property:
        """
        SSOT function to update a Property.
        """
        if 'name' in kwargs and kwargs['name'] != property_obj.name:
            if Property.objects.filter(tenant=property_obj.tenant, name=kwargs['name']).exclude(pk=property_obj.pk).exists():
                raise ValidationError({'name': 'Property with this name already exists for this tenant.'})
            property_obj.name = kwargs['name']

        for field in ['address', 'city', 'country', 'phone', 'email', 'monthly_rent', 'status']:
            if field in kwargs:
                setattr(property_obj, field, kwargs[field])

        property_obj.save()
        return property_obj
