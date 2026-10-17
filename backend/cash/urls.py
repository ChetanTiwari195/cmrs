from rest_framework.routers import DefaultRouter

from .views import CashSubmissionViewSet, CollectionViewSet, DiscrepancyViewSet

router = DefaultRouter()
router.register("collections", CollectionViewSet, basename="collection")
router.register("submissions", CashSubmissionViewSet, basename="submission")
router.register("discrepancies", DiscrepancyViewSet, basename="discrepancy")

urlpatterns = router.urls
