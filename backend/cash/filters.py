import django_filters

from .models import Collection


class CollectionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="collected_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="collected_at", lookup_expr="date__lte")

    class Meta:
        model = Collection
        fields = ["loan", "agent", "status"]
