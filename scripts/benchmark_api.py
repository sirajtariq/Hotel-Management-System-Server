import os
import sys
import time
import json
from decimal import Decimal
from datetime import date, timedelta

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
settings.DEBUG = True
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.db import connection, reset_queries
from apps.tenants.models import Tenant
from apps.users.models import User, Role
from apps.users.services.user_service import UserService
from apps.properties.models import Property
from apps.rooms.models import Room, RoomType
from apps.bookings.models import Booking
from apps.expenses.models import Expense, ExpenseCategory
from apps.staff.models import StaffProfile

def seed_benchmark_data():
    """Ensures sufficient database records exist for meaningful ORM benchmarking."""
    tenant, _ = Tenant.objects.get_or_create(
        name="Benchmark Grand Hotel",
        defaults={"slug": "benchmark-grand-hotel", "contact_email": "admin@benchmark.com", "max_properties": 10, "max_rooms": 100, "max_users": 20}
    )

    role, _ = Role.objects.get_or_create(
        tenant=tenant,
        name="Operations Manager",
        defaults={"permissions": ["properties:view", "rooms:view", "bookings:view", "expenses:view", "staff:view", "reports:view_pnl", "roles:manage"]}
    )

    user, user_created = User.objects.get_or_create(
        username="bench_admin",
        defaults={
            "email": "bench_admin@benchmark.com",
            "tenant": tenant,
            "role": "TENANT_ADMIN",
            "custom_role": role,
            "first_name": "Benchmark",
            "last_name": "Admin"
        }
    )
    if user_created:
        user.set_password("Benchmark123!")
        user.save()

    # Seed 3 Properties
    properties = []
    for i in range(1, 4):
        prop, _ = Property.objects.get_or_create(
            tenant=tenant,
            name=f"Benchmark Property {i}",
            defaults={"city": "Karachi", "address": f"Street {i}", "monthly_rent": Decimal('100000.00'), "status": "ACTIVE"}
        )
        properties.append(prop)

    # Seed Room Types & 30 Rooms
    rt, _ = RoomType.objects.get_or_create(
        tenant=tenant,
        property=properties[0],
        name="Deluxe Suite",
        defaults={"base_price_per_night": Decimal('25000.00'), "max_occupancy": 3}
    )

    for i in range(1, 31):
        prop = properties[i % len(properties)]
        Room.objects.get_or_create(
            tenant=tenant,
            room_number=f"RM-{100+i}",
            defaults={"property": prop, "room_type": rt, "floor": (i // 10) + 1, "status": "AVAILABLE"}
        )

    rooms = list(Room.objects.filter(tenant=tenant))
    for i in range(1, 21):
        rm = rooms[i % len(rooms)]
        Booking.objects.get_or_create(
            tenant=tenant,
            property=rm.property,
            room=rm,
            guest_name=f"Guest John Doe {i}",
            defaults={
                "guest_email": f"guest{i}@example.com",
                "guest_phone": f"+9230012345{i:02d}",
                "check_in_date": date.today() - timedelta(days=i),
                "check_out_date": date.today() - timedelta(days=i - 2),
                "total_nights": 2,
                "nightly_rate": Decimal('25000.00'),
                "total_amount": Decimal('50000.00'),
                "paid_amount": Decimal('50000.00') if i % 2 == 0 else Decimal('25000.00'),
                "status": "CONFIRMED",
                "payment_status": "PAID" if i % 2 == 0 else "PARTIAL"
            }
        )

    # Seed Expense Categories & 25 Expenses
    cat, _ = ExpenseCategory.objects.get_or_create(tenant=tenant, name="Utilities & Fuel")
    for i in range(1, 26):
        prop = properties[i % len(properties)]
        Expense.objects.get_or_create(
            tenant=tenant,
            item_name=f"Utility Payment {i}",
            expense_date=date.today() - timedelta(days=i),
            defaults={
                "property": prop,
                "category": cat,
                "amount": Decimal('15000.00'),
                "vendor_name": "Power Gen Ltd",
                "created_by": user
            }
        )

    # Seed 15 Staff Profiles
    for i in range(1, 16):
        prop = properties[i % len(properties)]
        StaffProfile.objects.get_or_create(
            tenant=tenant,
            phone_number=f"+9230000000{i:02d}",
            defaults={
                "name": f"Staff Employee {i}",
                "position": "Receptionist" if i % 2 == 0 else "Cleaner",
                "property": prop,
                "monthly_salary": Decimal('45000.00'),
                "is_active": True
            }
        )

    return user, tenant

def benchmark_endpoint(client, url, name, headers, num_warmup=5, num_runs=20):
    """Benchmarks a single API endpoint for latency, SQL queries, duplicates, and payload size."""
    # Warmup
    for _ in range(num_warmup):
        client.get(url, **headers)

    latencies = []
    sql_counts = []
    duplicate_counts = []
    db_times = []
    payload_sizes = []

    for _ in range(num_runs):
        reset_queries()
        start_time = time.perf_counter()

        response = client.get(url, **headers)

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000.0
        latencies.append(latency_ms)

        # SQL metrics
        queries = connection.queries
        sql_counts.append(len(queries))

        # DB time vs Python overhead
        total_db_time = sum(float(q.get('time', 0)) for q in queries) * 1000.0 # to ms
        db_times.append(total_db_time)

        # Duplicate queries check
        sql_strings = [q['sql'] for q in queries]
        unique_sqls = set(sql_strings)
        dup_count = len(sql_strings) - len(unique_sqls)
        duplicate_counts.append(dup_count)

        # Payload size
        content_len = len(response.content) if hasattr(response, 'content') else 0
        payload_sizes.append(content_len / 1024.0)

    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    avg_queries = sum(sql_counts) / len(sql_counts)
    avg_dups = sum(duplicate_counts) / len(duplicate_counts)
    avg_db_time = sum(db_times) / len(db_times)
    avg_payload = sum(payload_sizes) / len(payload_sizes)

    # Health status indicator
    if avg_latency < 60 and avg_queries <= 6 and avg_dups == 0:
        health = "OPTIMAL"
    elif avg_latency < 150 and avg_queries <= 15:
        health = "MODERATE"
    else:
        health = "CRITICAL BOTTLENECK"

    return {
        "name": name,
        "url": url,
        "status_code": response.status_code,
        "avg_latency_ms": round(avg_latency, 2),
        "min_latency_ms": round(min_latency, 2),
        "max_latency_ms": round(max_latency, 2),
        "sql_queries_avg": round(avg_queries, 1),
        "duplicate_queries_avg": round(avg_dups, 1),
        "db_time_ms_avg": round(avg_db_time, 2),
        "python_time_ms_avg": round(max(0, avg_latency - avg_db_time), 2),
        "payload_size_kb": round(avg_payload, 2),
        "health": health
    }

def run_benchmark():
    print("Initializing benchmark dataset...")
    user, tenant = seed_benchmark_data()

    client = Client()
    tokens = UserService.generate_tokens_for_user(user)
    headers = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}

    endpoints = [
        ("/api/v1/users/me/", "Current User Profile (/users/me/)"),
        ("/api/v1/properties/", "Properties List (/properties/)"),
        ("/api/v1/rooms/", "Rooms & Inventory (/rooms/)"),
        ("/api/v1/bookings/", "Bookings Ledger (/bookings/)"),
        ("/api/v1/expenses/", "Expenses List (/expenses/)"),
        ("/api/v1/staff/", "Staff Profiles (/staff/)"),
        ("/api/v1/roles/", "Roles List (/roles/)"),
        ("/api/v1/reports/financial/", "Financial Report P&L (/reports/financial/)"),
    ]

    print("\nExecuting deep-dive API benchmarking across endpoints...\n")
    results = []

    for url, name in endpoints:
        res = benchmark_endpoint(client, url, name, headers)
        results.append(res)
        print(f"[{res['health']}] {res['name']}")
        print(f"   Latency: {res['avg_latency_ms']} ms (DB: {res['db_time_ms_avg']} ms | Py: {res['python_time_ms_avg']} ms)")
        print(f"   SQL Queries: {res['sql_queries_avg']} (Duplicates: {res['duplicate_queries_avg']})")
        print(f"   Payload: {res['payload_size_kb']} KB | HTTP Status: {res['status_code']}\n")

    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmark_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Benchmark results exported cleanly to {output_path}")

if __name__ == '__main__':
    run_benchmark()
