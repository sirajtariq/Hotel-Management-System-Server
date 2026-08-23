from rest_framework.routers import DefaultRouter
from apps.expenses.views import ExpenseViewSet, ExpenseCategoryViewSet

router = DefaultRouter()
router.register(r'categories', ExpenseCategoryViewSet, basename='expense-category')
router.register(r'', ExpenseViewSet, basename='expense')

urlpatterns = router.urls
