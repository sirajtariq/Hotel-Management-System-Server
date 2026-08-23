import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from apps.tenants.models import Tenant
from apps.properties.models import Property
from apps.rooms.models import RoomType, Room
from apps.bookings.models import Booking
from apps.expenses.models import ExpenseCategory, Expense
from apps.staff.models import StaffProfile

User = get_user_model()

class Command(BaseCommand):
    help = "Populate realistic demo data for Multi-Tenant Serviced Apartments system"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Flushing old demo data & seeding fresh records..."))

        # -------------------------------------------------------------------------
        # 1. SUPER ADMIN CREATION
        # -------------------------------------------------------------------------
        super_admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "superadmin@platform.com",
                "first_name": "Platform",
                "last_name": "SuperAdmin",
                "role": "SUPERADMIN",
                "is_staff": True,
                "is_superuser": True,
            }
        )
        super_admin.set_password("admin123")
        super_admin.save()
        self.stdout.write(self.style.SUCCESS("[OK] SuperAdmin ready: admin / admin123"))


        # -------------------------------------------------------------------------
        # 2. TENANT 1: ROYAL STAYS HOSPITALITY (Islamabad & Murree)
        # -------------------------------------------------------------------------
        today = timezone.now().date()

        tenant_1, _ = Tenant.objects.update_or_create(
            slug="royal-stays",
            defaults={
                "name": "Royal Stays Hospitality",
                "is_active": True,
                "billing_type": "MONTHLY",
                "price_amount": Decimal("25000.00"),
                "subscription_status": "PAID",
                "subscription_start_date": today - datetime.timedelta(days=60),
                "next_due_date": today + datetime.timedelta(days=25),
                "grace_period_days": 3,
                "notes": "Managing premium villas in Islamabad & Murree",
            }
        )

        # Tenant Admin 1
        t1_admin, _ = User.objects.get_or_create(
            username="royal_admin",
            defaults={
                "email": "owner@royalstays.pk",
                "first_name": "Hamza",
                "last_name": "Tariq",
                "role": "TENANT_ADMIN",
                "tenant": tenant_1,
                "phone_number": "03001234567",
            }
        )
        t1_admin.set_password("password123")
        t1_admin.tenant = tenant_1
        t1_admin.save()

        # Properties for Tenant 1
        prop_isb, _ = Property.objects.update_or_create(
            tenant=tenant_1,
            name="F-7 Executive Villa",
            defaults={
                "city": "Islamabad",
                "address": "Street 14, Sector F-7/2, Islamabad",
                "monthly_rent": Decimal("350000.00"),
                "status": "ACTIVE",
            }
        )

        prop_murree, _ = Property.objects.update_or_create(
            tenant=tenant_1,
            name="Pine View Cottage",
            defaults={
                "city": "Murree",
                "address": "Upper Mall Road, Near Governor House, Murree",
                "monthly_rent": Decimal("220000.00"),
                "status": "ACTIVE",
            }
        )

        # Room Types
        rt_deluxe, _ = RoomType.objects.update_or_create(
            tenant=tenant_1, property=prop_isb, name="Deluxe Master Bed",
            defaults={"base_price_per_night": Decimal("12000.00"), "max_occupancy": 2, "description": "King bed with attached luxury bath"}
        )
        rt_executive, _ = RoomType.objects.update_or_create(
            tenant=tenant_1, property=prop_isb, name="Executive Suite",
            defaults={"base_price_per_night": Decimal("18000.00"), "max_occupancy": 3, "description": "Lounge + Master bed with balcony view"}
        )
        rt_cottage_room, _ = RoomType.objects.update_or_create(
            tenant=tenant_1, property=prop_murree, name="Mountain View Room",
            defaults={"base_price_per_night": Decimal("15000.00"), "max_occupancy": 2, "description": "Scenic valley view with heater"}
        )

        # Rooms
        rooms_isb = [
            ("101", rt_deluxe, "OCCUPIED", 1),
            ("102", rt_deluxe, "AVAILABLE", 1),
            ("103", rt_deluxe, "CLEANING", 1),
            ("201", rt_executive, "OCCUPIED", 2),
            ("202", rt_executive, "MAINTENANCE", 2),
            ("203", rt_deluxe, "AVAILABLE", 2),
        ]
        created_rooms_isb = {}
        for r_num, r_type, r_stat, flr in rooms_isb:
            rm, _ = Room.objects.update_or_create(
                tenant=tenant_1, property=prop_isb, room_number=r_num,
                defaults={"room_type": r_type, "status": r_stat, "floor": flr}
            )
            created_rooms_isb[r_num] = rm

        rooms_murree = [
            ("M-01", rt_cottage_room, "OCCUPIED", 1),
            ("M-02", rt_cottage_room, "AVAILABLE", 1),
            ("M-03", rt_cottage_room, "AVAILABLE", 1),
            ("M-04", rt_cottage_room, "AVAILABLE", 2),
        ]
        created_rooms_murree = {}
        for r_num, r_type, r_stat, flr in rooms_murree:
            rm, _ = Room.objects.update_or_create(
                tenant=tenant_1, property=prop_murree, room_number=r_num,
                defaults={"room_type": r_type, "status": r_stat, "floor": flr}
            )
            created_rooms_murree[r_num] = rm

        # Bookings (Active, Completed, Upcoming)
        bookings_data = [
            # Active Checked-In
            (prop_isb, created_rooms_isb["101"], "Ali Raza", "ali.raza@gmail.com", "03219876543", today - datetime.timedelta(days=2), today + datetime.timedelta(days=2), Decimal("12000.00"), Decimal("48000.00"), Decimal("48000.00"), "PAID", "CHECKED_IN"),
            (prop_isb, created_rooms_isb["201"], "Dr. Bilal Ahmed", "bilal.ahmed@yahoo.com", "03335554433", today - datetime.timedelta(days=1), today + datetime.timedelta(days=3), Decimal("18000.00"), Decimal("72000.00"), Decimal("36000.00"), "PARTIAL", "CHECKED_IN"),
            (prop_murree, created_rooms_murree["M-01"], "Usman Qureshi", "usman.q@outlook.com", "03024443322", today - datetime.timedelta(days=3), today + datetime.timedelta(days=1), Decimal("15000.00"), Decimal("60000.00"), Decimal("60000.00"), "PAID", "CHECKED_IN"),
            # Completed (Past for Revenue/P&L)
            (prop_isb, created_rooms_isb["102"], "Khurram Shahzad", "khurram@gmail.com", "03125556677", today - datetime.timedelta(days=10), today - datetime.timedelta(days=6), Decimal("12000.00"), Decimal("48000.00"), Decimal("48000.00"), "PAID", "CHECKED_OUT"),
            (prop_isb, created_rooms_isb["103"], "Zia Rehman", "zia.r@gmail.com", "03456667788", today - datetime.timedelta(days=5), today - datetime.timedelta(days=1), Decimal("12000.00"), Decimal("48000.00"), Decimal("48000.00"), "PAID", "CHECKED_OUT"),
            # Upcoming
            (prop_isb, created_rooms_isb["203"], "Sarmad Khan", "sarmad.k@gmail.com", "03008889900", today + datetime.timedelta(days=2), today + datetime.timedelta(days=5), Decimal("12000.00"), Decimal("36000.00"), Decimal("10000.00"), "PARTIAL", "CONFIRMED"),
        ]

        for prop, room, g_name, g_email, g_phone, cin, cout, rate, total, paid, p_stat, b_stat in bookings_data:
            nights = (cout - cin).days
            Booking.objects.create(
                tenant=tenant_1,
                property=prop,
                room=room,
                guest_name=g_name,
                guest_email=g_email,
                guest_phone=g_phone,
                check_in_date=cin,
                check_out_date=cout,
                total_nights=nights,
                nightly_rate=rate,
                total_amount=total,
                paid_amount=paid,
                payment_status=p_stat,
                status=b_stat
            )

        # Expense Categories & Expenses
        cat_maint, _ = ExpenseCategory.objects.get_or_create(tenant=tenant_1, name="Maintenance & Repair")
        cat_supplies, _ = ExpenseCategory.objects.get_or_create(tenant=tenant_1, name="Cleaning & Supplies")
        cat_util, _ = ExpenseCategory.objects.get_or_create(tenant=tenant_1, name="Utilities & Bills")

        expenses_t1 = [
            (prop_isb, cat_maint, "Master Bed AC Gas Refill & Service", "Al-Madina Air Conditioning", Decimal("14500.00"), today - datetime.timedelta(days=12)),
            (prop_isb, cat_supplies, "4x Luxury Cotton Bed Sheets & Towels", "Metro Cash & Carry", Decimal("22000.00"), today - datetime.timedelta(days=8)),
            (prop_isb, cat_util, "High Speed Fiber Internet Bill", "Nayatel Islamabad", Decimal("7800.00"), today - datetime.timedelta(days=4)),
            (prop_murree, cat_supplies, "Heater Gas Cylinders (2x Refill)", "Murree Gas Agency", Decimal("16000.00"), today - datetime.timedelta(days=5)),
            (prop_murree, cat_maint, "Plumbing & Geyser Heating Element", "Khan Hardware Murree", Decimal("9500.00"), today - datetime.timedelta(days=1)),
        ]

        for prop, cat, item, vendor, amt, exp_date in expenses_t1:
            Expense.objects.create(
                tenant=tenant_1,
                property=prop,
                category=cat,
                item_name=item,
                vendor_name=vendor,
                amount=amt,
                expense_date=exp_date,
                description=f"Standard purchase for {prop.name}"
            )

        # Staff Profiles
        staff_t1 = [
            (prop_isb, "Muhammad Aslam", "03015551122", "Housekeeping", "Cleaner", Decimal("32000.00")),
            (prop_isb, "Naveed Akram", "03457778899", "Management", "Villa Caretaker & Night Guard", Decimal("38000.00")),
            (prop_murree, "Sher Khan", "03339994411", "Management", "Cottage Manager & Cook", Decimal("45000.00")),
        ]
        for prop, name, phone, dept, pos, sal in staff_t1:
            StaffProfile.objects.create(
                tenant=tenant_1,
                property=prop,
                name=name,
                phone=phone,
                department=dept,
                position=pos,
                monthly_salary=sal,
                hired_date=today - datetime.timedelta(days=180),
                is_active=True
            )

        # -------------------------------------------------------------------------
        # 3. TENANT 2: URBAN SUITES (Lahore)
        # -------------------------------------------------------------------------
        tenant_2, _ = Tenant.objects.update_or_create(
            slug="urban-suites",
            defaults={
                "name": "Urban Suites Lahore",
                "is_active": True,
                "billing_type": "MONTHLY",
                "price_amount": Decimal("20000.00"),
                "subscription_status": "DUE_SOON",
                "subscription_start_date": today - datetime.timedelta(days=30),
                "next_due_date": today + datetime.timedelta(days=4),
                "grace_period_days": 3,
                "notes": "Modern serviced apartments near Gulberg",
            }
        )

        t2_admin, _ = User.objects.get_or_create(
            username="urban_admin",
            defaults={
                "email": "owner@urbansuites.pk",
                "first_name": "Zubair",
                "last_name": "Malik",
                "role": "TENANT_ADMIN",
                "tenant": tenant_2,
                "phone_number": "03009998877",
            }
        )
        t2_admin.set_password("password123")
        t2_admin.tenant = tenant_2
        t2_admin.save()

        prop_lhr, _ = Property.objects.update_or_create(
            tenant=tenant_2,
            name="Gulberg Studio Apartments",
            defaults={
                "city": "Lahore",
                "address": "M.M. Alam Road, Gulberg III, Lahore",
                "monthly_rent": Decimal("280000.00"),
                "status": "ACTIVE",
            }
        )

        rt_studio, _ = RoomType.objects.update_or_create(
            tenant=tenant_2, property=prop_lhr, name="1-Bed Luxury Studio",
            defaults={"base_price_per_night": Decimal("10000.00"), "max_occupancy": 2, "description": "Kitchenette + Bed"}
        )

        for num in ["G-101", "G-102", "G-103", "G-201"]:
            Room.objects.update_or_create(
                tenant=tenant_2, property=prop_lhr, room_number=num,
                defaults={"room_type": rt_studio, "status": "AVAILABLE", "floor": 1}
            )

        self.stdout.write(self.style.SUCCESS("[OK] Multi-tenant realistic demo data seeded successfully!"))

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("DEMO LOGIN CREDENTIALS:"))
        self.stdout.write("1. SuperAdmin:  username: admin        | password: admin123")
        self.stdout.write("2. Tenant 1:    username: royal_admin  | password: password123 (Islamabad & Murree)")
        self.stdout.write("3. Tenant 2:    username: urban_admin  | password: password123 (Lahore)")
        self.stdout.write("="*50 + "\n")
