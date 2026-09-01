from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.accounts.models import PaymentAccount, AccountTransaction, AccountTransfer


class AccountService:
    @staticmethod
    @transaction.atomic
    def record_transaction(
        tenant,
        account,
        transaction_type: str,
        amount,
        source_module: str,
        reference_id: str = "",
        description: str = "",
        user=None
    ):
        """
        Atomically mutates a PaymentAccount's balance and creates an AccountTransaction audit record.
        """
        amount_dec = Decimal(str(amount))
        if amount_dec <= 0:
            raise ValidationError("Transaction amount must be greater than zero.")

        # Refresh account lock
        acc = PaymentAccount.objects.select_for_update().get(id=account.id, tenant=tenant)

        if transaction_type in ['INFLOW', 'TRANSFER_IN']:
            acc.current_balance += amount_dec
        elif transaction_type in ['OUTFLOW', 'TRANSFER_OUT']:
            acc.current_balance -= amount_dec
        else:
            raise ValidationError(f"Invalid transaction type: {transaction_type}")

        acc.save()

        tx = AccountTransaction.objects.create(
            tenant=tenant,
            account=acc,
            transaction_type=transaction_type,
            amount=amount_dec,
            balance_after=acc.current_balance,
            source_module=source_module,
            reference_id=reference_id,
            description=description,
            created_by=user
        )

        return tx

    @staticmethod
    @transaction.atomic
    def execute_transfer(
        tenant,
        from_account_id,
        to_account_id,
        amount,
        transfer_date=None,
        reference_number: str = "",
        notes: str = "",
        user=None
    ):
        """
        Atomically transfers funds between two PaymentAccounts under the same tenant.
        """
        amount_dec = Decimal(str(amount))
        if amount_dec <= 0:
            raise ValidationError("Transfer amount must be greater than zero.")

        if str(from_account_id) == str(to_account_id):
            raise ValidationError("Source and target payment accounts must be different.")

        try:
            from_acc = PaymentAccount.objects.select_for_update().get(id=from_account_id, tenant=tenant, is_active=True)
        except PaymentAccount.DoesNotExist:
            raise ValidationError("Source payment account not found or inactive.")

        try:
            to_acc = PaymentAccount.objects.select_for_update().get(id=to_account_id, tenant=tenant, is_active=True)
        except PaymentAccount.DoesNotExist:
            raise ValidationError("Target payment account not found or inactive.")

        # Check balance sufficiency
        if from_acc.current_balance < amount_dec:
            raise ValidationError(
                f"Insufficient funds in '{from_acc.name}'. Available: PKR {from_acc.current_balance}, Requested: PKR {amount_dec}"
            )

        # Deduct from source account
        from_acc.current_balance -= amount_dec
        from_acc.save()

        AccountTransaction.objects.create(
            tenant=tenant,
            account=from_acc,
            transaction_type='TRANSFER_OUT',
            amount=amount_dec,
            balance_after=from_acc.current_balance,
            source_module='TRANSFER',
            reference_id=reference_number or f"TRF-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            description=f"Transfer to {to_acc.name}. {notes}".strip(),
            created_by=user
        )

        # Add to target account
        to_acc.current_balance += amount_dec
        to_acc.save()

        AccountTransaction.objects.create(
            tenant=tenant,
            account=to_acc,
            transaction_type='TRANSFER_IN',
            amount=amount_dec,
            balance_after=to_acc.current_balance,
            source_module='TRANSFER',
            reference_id=reference_number or f"TRF-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            description=f"Transfer from {from_acc.name}. {notes}".strip(),
            created_by=user
        )

        # Create transfer audit record
        transfer = AccountTransfer.objects.create(
            tenant=tenant,
            from_account=from_acc,
            to_account=to_acc,
            amount=amount_dec,
            transfer_date=transfer_date or timezone.now().date(),
            reference_number=reference_number,
            notes=notes,
            created_by=user
        )

        return transfer
