import datetime

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters

from .models import Action


def create_action(user, verb, target=None, limit=True):
    if not limit:
        action = Action(user=user, verb=verb, target=target)
        action.save()
        return True

    # Check for any similar action made in the last minute
    now = timezone.now()
    last_minute = now - datetime.timedelta(seconds=60)
    similar_actions = Action.objects.filter(user_id=user.id, verb=verb, created__gte=last_minute)

    if target:
        target_ct = ContentType.objects.get_for_model(target)
        similar_actions = similar_actions.filter(target_ct=target_ct, target_id=target.id)

    if not similar_actions:
        action = Action(user=user, verb=verb, target=target)
        action.save()
        return True
        
    return False


class ActionPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page-size'
    page_query_param = "page"
    max_page_size = 100


class ActionFilter(filters.FilterSet):
    username = filters.CharFilter(field_name='user__username', lookup_expr='iexact')

    class Meta:
        model = Action
        fields = ['username']
