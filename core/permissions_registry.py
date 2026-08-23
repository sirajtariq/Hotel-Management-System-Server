PERMISSIONS_CATALOG = {
    "Properties": [
        {"code": "properties:view", "name": "View Properties"},
        {"code": "properties:manage", "name": "Create, Edit & Delete Properties"},
    ],
    "Rooms": [
        {"code": "rooms:view", "name": "View Rooms & Inventory"},
        {"code": "rooms:manage", "name": "Create, Edit & Delete Rooms"},
        {"code": "rooms:change_status", "name": "Change Live Status (Clean/Dirty/Maintenance)"},
    ],
    "Bookings": [
        {"code": "bookings:view", "name": "View Bookings & Calendar"},
        {"code": "bookings:create", "name": "Create Bookings & Walk-ins"},
        {"code": "bookings:update", "name": "Edit Booking Details & Dates"},
        {"code": "bookings:record_payment", "name": "Record Payments & Collect Cash"},
        {"code": "bookings:cancel", "name": "Cancel Bookings"},
    ],
    "Expenses": [
        {"code": "expenses:view", "name": "View Daily Expenses"},
        {"code": "expenses:create", "name": "Add Daily Expenses & Purchases"},
        {"code": "expenses:delete", "name": "Delete Expense Records"},
    ],
    "Staff": [
        {"code": "staff:view", "name": "View Staff Profiles"},
        {"code": "staff:manage", "name": "Add, Edit & Manage Staff"},
    ],
    "Reports": [
        {"code": "reports:view_pnl", "name": "View P&L and Financial Analytics"},
        {"code": "reports:export", "name": "Export Financial & Occupancy Data"},
    ],
    "Restaurant & Dining": [
        {"code": "restaurant:pos", "name": "Access POS terminal & create orders"},
        {"code": "restaurant:kitchen", "name": "Access Kitchen Display & update order status"},
        {"code": "restaurant:orders_view", "name": "View order history & reprint receipts"},
        {"code": "restaurant:menu_manage", "name": "Manage menu categories, food items & variations"},
        {"code": "restaurant:tables_manage", "name": "Manage dining table layout"},
    ],
    "Roles & Access": [
        {"code": "roles:manage", "name": "Create & Manage Custom Roles & Permissions"},
    ]
}

def get_all_permission_codes() -> set:
    """Returns a flat set of all registered permission codes."""
    return {
        item["code"]
        for group in PERMISSIONS_CATALOG.values()
        for item in group
    }
