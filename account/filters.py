from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters
# import rest_framework_filters as filters


UserModel = get_user_model()


class UserFilter(filters.FilterSet):
    username = filters.CharFilter(field_name='username', lookup_expr='iexact')
    # username = filters.CharFilter(field_name='username', method='iexact_or')
    realname = filters.CharFilter(field_name='realname', lookup_expr='iexact')

    class Meta:
        model = UserModel
        fields = ['username', 'realname']

    def iexact_or(self, queryset, name, value):
        return queryset(**{name:value})


