from django.db import models
from apps.tenants.models import Tenant
from apps.properties.models import Property
from apps.bookings.models import Booking
from apps.users.models import User


class Category(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='restaurant_categories')
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'restaurant_categories'
        ordering = ['display_order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class MenuItem(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='restaurant_menu_items')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    has_variations = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    image_url = models.URLField(blank=True, null=True)

    class Meta:
        db_table = 'restaurant_menu_items'
        ordering = ['category__display_order', 'name']

    def __str__(self):
        return f"{self.name} - PKR {self.base_price}"


class MenuItemVariation(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='variations')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'restaurant_menu_item_variations'
        ordering = ['price']

    def __str__(self):
        return f"{self.menu_item.name} - {self.name} (PKR {self.price})"


class DiningTable(models.Model):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='dining_tables')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='dining_tables')
    table_number = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=4)
    floor_or_section = models.CharField(max_length=100, default='Ground Floor', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')

    class Meta:
        db_table = 'restaurant_dining_tables'
        ordering = ['floor_or_section', 'table_number']
        unique_together = ('tenant', 'property', 'table_number')

    def __str__(self):
        return f"Table {self.table_number} ({self.floor_or_section}) - {self.status}"


class RestaurantOrder(models.Model):
    ORDER_TYPE_CHOICES = (
        ('DINE_IN', 'Dine-In'),
        ('TAKEAWAY', 'Takeaway'),
        ('ROOM_SERVICE', 'Room Service'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PREPARING', 'In Kitchen'),
        ('READY', 'Ready to Serve'),
        ('SERVED', 'Served'),
        ('COMPLETED', 'Completed / Paid'),
        ('CANCELLED', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid Now'),
        ('BILLED_TO_ROOM', 'Billed to Room Folio'),
    )

    DISCOUNT_TYPE_CHOICES = (
        ('FLAT', 'Flat Amount'),
        ('PERCENTAGE', 'Percentage'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='restaurant_orders')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='restaurant_orders')
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    table = models.ForeignKey(DiningTable, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    booking = models.ForeignKey(Booking, null=True, blank=True, on_delete=models.SET_NULL, related_name='restaurant_orders')
    room_number = models.CharField(max_length=50, blank=True)
    customer_name = models.CharField(max_length=150, blank=True)
    customer_phone = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='UNPAID', db_index=True)
    payment_method = models.CharField(max_length=50, blank=True)

    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPE_CHOICES, default='FLAT')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_restaurant_orders')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'restaurant_orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} ({self.order_type}) - PKR {self.grand_total}"


class RestaurantOrderItem(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PREPARING', 'Preparing'),
        ('READY', 'Ready'),
    )

    order = models.ForeignKey(RestaurantOrder, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name='order_items')
    variation = models.ForeignKey(MenuItemVariation, null=True, blank=True, on_delete=models.SET_NULL, related_name='order_items')
    item_name = models.CharField(max_length=150)
    variation_name = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    special_instructions = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        db_table = 'restaurant_order_items'

    def __str__(self):
        v_str = f" ({self.variation_name})" if self.variation_name else ""
        return f"{self.quantity}x {self.item_name}{v_str} - PKR {self.total_price}"
