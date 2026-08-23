from django.contrib import admin
from apps.expenses.models import Expense, ExpenseCategory

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant')
    search_fields = ('name',)
    list_filter = ('tenant',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('item_name', 'vendor_name', 'amount', 'property', 'category', 'expense_date')
    search_fields = ('item_name', 'vendor_name', 'description')
    list_filter = ('tenant', 'property', 'category', 'expense_date')
