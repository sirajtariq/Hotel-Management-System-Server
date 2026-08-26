from rest_framework.routers import DefaultRouter
from apps.accounts.views import PaymentAccountViewSet, AccountTransferViewSet

router = DefaultRouter()
router.register(r'payment-accounts', PaymentAccountViewSet, basename='payment-account')
router.register(r'account-transfers', AccountTransferViewSet, basename='account-transfer')

urlpatterns = router.urls
