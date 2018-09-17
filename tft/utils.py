from django.db.models import Q
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import APIException
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters

from account.models import GroupSetting
from .models import Order, RecoverOrder


class OrderPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page-size'
    page_query_param = "page"
    max_page_size = None


class OrderFilter(filters.FilterSet):
    username = filters.CharFilter(field_name='user__username', lookup_expr='iexact')
    realname = filters.CharFilter(field_name='user__realname', lookup_expr='iexact')
    mod_user = filters.CharFilter(field_name='mod_user__username', lookup_expr='iexact')
    group = filters.CharFilter(field_name='group__name', lookup_expr='iexact')
    charge_group = filters.CharFilter(field_name='charge_group__name', lookup_expr='iexact')
    created_after = filters.IsoDateTimeFilter(field_name='created', lookup_expr='gte')
    created_before = filters.IsoDateTimeFilter(field_name='created', lookup_expr='lte')
    # created = filters.DateTimeFromToRangeFilter(field_name='created')
    name = filters.CharFilter(method='name_filter', label='申请人或修改人')
    r_name = filters.CharFilter(method='r_name_filter', label='复机单的申请人或修改人')
    # r_user = filters.CharFilter(field_name='recoverorders__user__username', lookup_expr='iexact')
    # r_mod = filters.CharFilter(field_name='recoverorders__mod_user__username', lookup_expr='iexact')
    audit_signer = filters.CharFilter(method='audit_signer_filter', label='审核人')
    r_audit_signer = filters.CharFilter(method='r_audit_signer_filter', label='复机单的审核人')

    class Meta:
        model = Order
        fields = ('username', 'realname', 'mod_user', 'status', 'group', 'charge_group')

    def name_filter(self, queryset, name, value):
        return queryset.filter(Q(user__username=value) | Q(mod_user__username=value))

    def r_name_filter(self, queryset, name, value):
        return queryset.filter(Q(recoverorders__user__username=value) | Q(recoverorders__mod_user__username=value))

    def audit_signer_filter(self, queryset, name, value):
        return queryset.filter(Q(startaudit__p_signer__username=value) | Q(startaudit__c_signer__username=value))

    def r_audit_signer_filter(self, queryset, name, value):
        return queryset.filter(Q(recoverorders__audit__qc_signer__username=value) | Q(recoverorders__audit__p_signer__username=value))


class RecoverOrderFilter(filters.FilterSet):
    name = filters.CharFilter(method='name_filter', label='申请人或修改人')
    audit_signer = filters.CharFilter(method='audit_signer_filter', label='审核人')

    class Meta:
        model = RecoverOrder
        fields = ('order__status',)

    def name_filter(self, queryset, name, value):
        return queryset.filter(Q(user__username=value) | Q(mod_user__username=value))

    def audit_signer_filter(self, queryset, name, value):
        return queryset.filter(Q(audit__qc_signer__username=value) | Q(audit__p_signer__username=value))



# 请求用户是否为开单用户
class IsStartOrderUser(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if request.user:
            return obj.user == request.user
        return  False


class IsSameGroup(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        # 只要有相同的组就可以
        # if request.user:
        #     obj_groups = obj.user.groups.all()  # 开单人员所在的组，要考虑开单人huan组后的情况
        #     req_groups = request.user.groups.all()
        #     if set(obj_groups) & set(req_groups):
        #         return True
        if not obj.group:  # 没有开单工程，所有人都不可以修改
            return False
        if request.user:
            req_groups = request.user.groups.all()
            if obj.group in req_groups:
                return True
        return False


class RecoverOrderIsSameGroup(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if request.user:
            user_groups = obj.user.groups.all()
            mod_user_groups = request.user.groups.all()
            if set(user_groups) & set(mod_user_groups):
                return True
        return False


class IsMFGUser(BasePermission):
    def has_permission(self, request, view):
        try:
            mfg_code = settings.GROUP_CODE['TFT'].get('MFG')
            mfg = GroupSetting.objects.get(code=mfg_code).group
        except Exception as e:
            raise APIException(detail='没有找到生产科，请联系管理员确认', code=status.HTTP_403_FORBIDDEN)

        if mfg in request.user.groups.all():
            return True
        return False

    def has_object_permission(self, request, view, obj):
        return True
