from rest_framework import serializers
from apps.expenses.models import Expense, AccountHead, ExpenseCategory

class AccountHeadSerializer(serializers.ModelSerializer):
    expenses_count = serializers.IntegerField(read_only=True, default=0)
    total_spent_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, default=0)

    class Meta:
        model = AccountHead
        fields = [
            'id', 'tenant', 'name', 'description',
            'is_active', 'created_at', 'expenses_count', 'total_spent_amount'
        ]
        read_only_fields = ['id', 'tenant', 'created_at']

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'tenant', 'name']
        read_only_fields = ['id', 'tenant']

class ExpenseSerializer(serializers.ModelSerializer):
    account_head_details = AccountHeadSerializer(source='account_head', read_only=True)
    category_details = ExpenseCategorySerializer(source='category', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id', 'tenant', 'property', 'property_name',
            'account_head', 'account_head_details',
            'category', 'category_details',
            'item_name', 'payment_method', 'vendor_name',
            'amount', 'expense_date', 'receipt_number', 'receipt_image',
            'description', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'tenant', 'created_by', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.copy()
            if 'account_head_id' in data and 'account_head' not in data:
                data['account_head'] = data['account_head_id']
            if 'property_id' in data and 'property' not in data:
                data['property'] = data['property_id']
        return super().to_internal_value(data)

    def get_created_by_name(self, obj):
        if obj.created_by:
            name = obj.created_by.get_full_name()
            return name if name.strip() else obj.created_by.username
        return 'Staff Member'
