from rest_framework.routers import DefaultRouter
from apps.expenses.views import ExpenseViewSet, AccountHeadViewSet, ExpenseCategoryViewSet

router = DefaultRouter()
router.register(r'account-heads', AccountHeadViewSet, basename='account-head')
router.register(r'categories', ExpenseCategoryViewSet, basename='expense-category')
router.register(r'', ExpenseViewSet, basename='expense')

urlpatterns = router.urls
