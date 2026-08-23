from rest_framework import serializers
from apps.expenses.models import Expense, ExpenseCategory

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'tenant', 'name']
        read_only_fields = ['id', 'tenant']

class ExpenseSerializer(serializers.ModelSerializer):
    category_details = ExpenseCategorySerializer(source='category', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'tenant', 'property', 'category',
            'category_details', 'item_name', 'vendor_name',
            'amount', 'expense_date', 'description',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_by', 'created_at', 'updated_at']
