from rest_framework import serializers
from apps.accounts.models import PaymentAccount, AccountTransaction, AccountTransfer


class PaymentAccountSerializer(serializers.ModelSerializer):
    transactions_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = PaymentAccount
        fields = [
            'id',
            'name',
            'account_type',
            'bank_name',
            'account_number',
            'iban',
            'branch_name',
            'opening_balance',
            'current_balance',
            'is_default',
            'is_active',
            'transactions_count',
            'created_at',
        ]
        read_only_fields = ['id', 'tenant', 'current_balance', 'created_at']

    def create(self, validated_data):
        # Set current balance to opening balance on creation
        validated_data['current_balance'] = validated_data.get('opening_balance', 0)
        return super().create(validated_data)


class AccountTransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    transactionType = serializers.CharField(source='transaction_type', read_only=True)
    balanceAfter = serializers.DecimalField(source='balance_after', max_digits=14, decimal_places=2, read_only=True)
    sourceModule = serializers.CharField(source='source_module', read_only=True)
    referenceId = serializers.CharField(source='reference_id', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = AccountTransaction
        fields = [
            'id',
            'account',
            'account_name',
            'transaction_type',
            'transactionType',
            'amount',
            'balance_after',
            'balanceAfter',
            'source_module',
            'sourceModule',
            'reference_id',
            'referenceId',
            'description',
            'created_by_name',
            'created_at',
            'createdAt',
        ]
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "System"


class AccountTransferSerializer(serializers.ModelSerializer):
    from_account_name = serializers.CharField(source='from_account.name', read_only=True)
    to_account_name = serializers.CharField(source='to_account.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AccountTransfer
        fields = [
            'id',
            'from_account',
            'from_account_name',
            'to_account',
            'to_account_name',
            'amount',
            'transfer_date',
            'reference_number',
            'notes',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return "System"


class CreateTransferSerializer(serializers.Serializer):
    from_account_id = serializers.IntegerField(required=True)
    to_account_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    transfer_date = serializers.DateField(required=False, allow_null=True)
    reference_number = serializers.CharField(max_length=80, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
