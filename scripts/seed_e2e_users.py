import os
import sys
import django
from decimal import Decimal
import datetime

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from apps.tenants.models import Tenant
from apps.users.models import Role, User
from apps.properties.models import Property
from apps.rooms.models import RoomType, Room
from apps.bookings.models import Booking
from apps.restaurant.models import Category, MenuItem, MenuItemVariation, DiningTable, RestaurantOrder, RestaurantOrderItem
from apps.expenses.models import ExpenseCategory, Expense
from apps.staff.models import StaffProfile

def seed_e2e_data():
    print("[INFO] Seeding E2E Deterministic Data...")
    
    with transaction.atomic():
        # 1. Platform SuperAdmin
        superadmin, _ = User.objects.get_or_create(
            username="superadmin",
            defaults={
                "email": "superadmin@platform.com",
                "first_name": "Super",
                "last_name": "Admin",
                "role": "SUPERADMIN",
                "is_staff": True,
                "is_superuser": True
            }
        )
        superadmin.set_password("SuperAdminSecret123!")
        superadmin.email = "superadmin@platform.com"
        superadmin.role = "SUPERADMIN"
        superadmin.is_superuser = True
        superadmin.is_staff = True
        superadmin.save()
        print("  [OK] SuperAdmin ready: superadmin@platform.com / SuperAdminSecret123!")

        # 2. Main E2E Tenant
        tenant, _ = Tenant.objects.update_or_create(
            slug="pearl-continental-e2e",
            defaults={
                "name": "Pearl Continental & Serviced Suites",
                "contact_email": "admin@hotel.com",
                "is_active": True,
                "billing_type": "MONTHLY",
                "price_amount": Decimal("150000.00"),
                "subscription_status": "PAID",
                "subscription_start_date": timezone.now().date() - datetime.timedelta(days=30),
                "next_due_date": timezone.now().date() + datetime.timedelta(days=30),
            }
        )
        print(f"  [OK] Tenant ready: {tenant.name} (ID: {tenant.id})")

        # 3. Tenant Admin Account
        tenant_admin, _ = User.objects.get_or_create(
            username="tenant_admin",
            defaults={
                "email": "admin@hotel.com",
                "first_name": "Hamza",
                "last_name": "Owner",
                "role": "TENANT_ADMIN",
                "tenant": tenant,
            }
        )
        tenant_admin.set_password("TenantAdminPass123!")
        tenant_admin.email = "admin@hotel.com"
        tenant_admin.role = "TENANT_ADMIN"
        tenant_admin.tenant = tenant
        tenant_admin.save()
        print("  [OK] Tenant Admin ready: admin@hotel.com / TenantAdminPass123!")

        # 4. Custom Role & Staff Receptionist Account
        receptionist_role, _ = Role.objects.update_or_create(
            tenant=tenant,
            name="Front Desk Receptionist",
            defaults={
                "description": "Front desk operations & bookings",
                "permissions": [
                    "properties:view",
                    "rooms:view",
                    "rooms:change_status",
                    "bookings:view",
                    "bookings:create",
                    "bookings:update",
                    "bookings:record_payment",
                    "restaurant:pos",
                    "expenses:view",
                    "expenses:create",
                    "staff:view"
                ],
                "is_system": False
            }
        )

        receptionist, _ = User.objects.get_or_create(
            username="receptionist_01",
            defaults={
                "email": "receptionist@hotel.com",
                "first_name": "Sarah",
                "last_name": "Receptionist",
                "role": "STAFF",
                "tenant": tenant,
                "custom_role": receptionist_role,
            }
        )
        receptionist.set_password("StaffPass123!")
        receptionist.email = "receptionist@hotel.com"
        receptionist.role = "STAFF"
        receptionist.tenant = tenant
        receptionist.custom_role = receptionist_role
        receptionist.save()
        print("  [OK] Receptionist ready: receptionist@hotel.com / StaffPass123!")

        # 5. Property & Inventory Seeding
        property_obj, _ = Property.objects.update_or_create(
            tenant=tenant,
            name="PC Executive Tower",
            defaults={
                "address": "Main Boulevard, Gulberg III",
                "city": "Lahore",
                "country": "Pakistan",
                "monthly_rent": Decimal("500000.00"),
                "status": "ACTIVE"
            }
        )

        room_type_deluxe, _ = RoomType.objects.update_or_create(
            tenant=tenant,
            property=property_obj,
            name="Deluxe Master Suite",
            defaults={
                "base_price_per_night": Decimal("15000.00"),
                "hourly_rate": Decimal("3000.00"),
                "is_hourly_allowed": True,
                "max_occupancy": 2,
                "description": "Luxury suite with king bed and balcony"
            }
        )

        room_101, _ = Room.objects.update_or_create(
            tenant=tenant,
            property=property_obj,
            room_number="101",
            defaults={
                "room_type": room_type_deluxe,
                "floor": "1",
                "status": "AVAILABLE",
                "housekeeping_status": "CLEAN"
            }
        )

        room_102, _ = Room.objects.update_or_create(
            tenant=tenant,
            property=property_obj,
            room_number="102",
            defaults={
                "room_type": room_type_deluxe,
                "floor": "1",
                "status": "AVAILABLE",
                "housekeeping_status": "CLEAN"
            }
        )
        print("  [OK] Property & Rooms seeded (#101, #102)")

        # 6. Restaurant POS Menu, Tables & Categories
        cat_burgers, _ = Category.objects.update_or_create(
            tenant=tenant,
            name="Gourmet Burgers",
            defaults={"display_order": 1, "is_active": True}
        )

        item_burger, _ = MenuItem.objects.update_or_create(
            tenant=tenant,
            category=cat_burgers,
            name="Zinger Supreme",
            defaults={
                "description": "Crispy fried chicken burger",
                "base_price": Decimal("700.00"),
                "has_variations": True,
                "is_available": True
            }
        )

        MenuItemVariation.objects.update_or_create(
            menu_item=item_burger,
            name="Single Patty",
            defaults={"price": Decimal("700.00"), "is_available": True}
        )
        MenuItemVariation.objects.update_or_create(
            menu_item=item_burger,
            name="Double Patty",
            defaults={"price": Decimal("1100.00"), "is_available": True}
        )

        table_01, _ = DiningTable.objects.update_or_create(
            tenant=tenant,
            property=property_obj,
            table_number="T-01",
            defaults={
                "capacity": 4,
                "floor_or_section": "Ground Floor",
                "status": "AVAILABLE"
            }
        )
        print("  [OK] POS Menu, Variations & Table T-01 seeded")

        # 7. Expense Categories & Initial Data
        exp_cat_util, _ = ExpenseCategory.objects.get_or_create(
            tenant=tenant,
            name="Utilities & Bills"
        )

    print("[SUCCESS] E2E Seed completed successfully!")

if __name__ == "__main__":
    seed_e2e_data()
