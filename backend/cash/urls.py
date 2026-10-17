from django.urls import path
from rest_framework.routers import DefaultRouter

from . import dashboard
from .views import BankDepositViewSet, CashSubmissionViewSet, CollectionViewSet, DiscrepancyViewSet

router = DefaultRouter()
router.register("collections", CollectionViewSet, basename="collection")
router.register("submissions", CashSubmissionViewSet, basename="submission")
router.register("deposits", BankDepositViewSet, basename="deposit")
router.register("discrepancies", DiscrepancyViewSet, basename="discrepancy")

urlpatterns = router.urls + [path("dashboard/", dashboard.summary, name="dashboard")]
