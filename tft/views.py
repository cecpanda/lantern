from django.conf import settings
from django.db.models import Q
from django.core.exceptions import FieldError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, RetrieveModelMixin, ListModelMixin, DestroyModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, \
                                       DjangoModelPermissions, \
                                       DjangoModelPermissionsOrAnonReadOnly
from rest_framework.decorators import action
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from account.models import GroupSetting
from action.utils import create_action
from .models import Order, Audit, RecoverOrder, RecoverAudit, Remark, Shortcut
from .serializers import StartOrderSerializer, RetrieveStartOrderSerializer, \
                         ProductAuditSerializer, ChargeAuditSerializer, \
                         ListRecoverOrderSerializer, RecoverOrderSerializer, UpdateRecoverOrderSerializer, \
                         QcRecoverAuditSerializer, ProductRecoverAuditSerializer, \
                         RemarkSerializer, CreateRemarkSerializer, \
                         OrderSerializer, ShortcutSerializer

from .utils import IsSameGroup, RecoverOrderIsSameGroup, IsMFGUser, OrderPagination, OrderFilter, RecoverOrderFilter


class StartOrderViewSet(CreateModelMixin,
                        UpdateModelMixin,
                        # RetrieveModelMixin,
                        # ListModelMixin,
                        # DestroyModelMixin,
                        GenericViewSet):
    '''
    create:
        创建停机单

    update:
        修改同科室成员、尚未审核的订单

    retrieve
        获取订单

    list
        获取所有订单

    destroy
        删除订单
    '''
    queryset = Order.objects.all()
    serializer_class = StartOrderSerializer
    lookup_field = 'id'
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return StartOrderSerializer
        if self.action == 'update':
            return StartOrderSerializer
        if self.action == 'retrieve':
            return RetrieveStartOrderSerializer
        if self.action == 'list':
            return RetrieveStartOrderSerializer
        if self.action == 'all_can_update':
            return OrderSerializer
        # 因为createserializer 影响了 retrieve 的 format=api
        # 所以用下面那个
        # return self.serializer_class
        return RetrieveStartOrderSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), DjangoModelPermissions()]
        elif self.action == 'update':
            return [IsAuthenticated(), IsSameGroup(), DjangoModelPermissions()]
        # elif self.action == 'retrieve':
        #     return [DjangoModelPermissionsOrAnonReadOnly()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), IsSameGroup(), DjangoModelPermissions()]
        elif self.action == 'can_update':
            return [IsAuthenticated(), IsSameGroup(), DjangoModelPermissions()]
        elif self.action == 'all_can_update':
            return [IsAuthenticated(), DjangoModelPermissions()]
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.perform_create(serializer)
        create_action(request.user, '开停机单', order, limit=False)
        # headers = self.get_success_headers(serializer.data)
        return Response({'id': order.id, 'status_code': order.status, 'status': order.get_status_display()},
                        status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        return serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        create_action(request.user, '修改', instance, limit=False)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response({'id': instance.id, 'status_code': instance.status, 'status': instance.get_status_display()})

    # def destroy(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     self.perform_destroy(instance)
    #     return Response(status=status.HTTP_204_NO_CONTENT)
    @action(methods=['get'], detail=True, url_path='can-update', url_name='can_update')
    def can_update(self, request, id=None):
        instance = self.get_object()
        if Audit.objects.filter(order__id=instance.id).exists():
            return Response({'can': False})
        if RecoverOrder.objects.filter(order__id=instance.id).exists():
            return Response({'can': False})
        return Response({'can': True})

    @action(methods=['get'], detail=False, url_path='all-can-update', url_name='all_can_update')
    def all_can_update(self, request):
        user = request.user
        orders = self.queryset.filter(group__name__in=[group.name for group in user.groups.all()],
                                      startaudit=None,
                                      recoverorders=None)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)


class AuditViewSet(GenericViewSet):
    queryset = Audit.objects.all()
    # serializer_class = ProductAuditSerializer
    lookup_field = 'order_id'
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_serializer_class(self):
        if self.action == 'product':
            return ProductAuditSerializer
        elif self.action == 'charge':
            return ChargeAuditSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action == 'product':
            return [IsAuthenticated(), DjangoModelPermissions(), IsMFGUser()]
        return [permission() for permission in self.permission_classes]

    @action(methods=['post', 'put'], detail=False, url_path='product', url_name='product')
    def product(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        create_action(request.user, '审核', order, limit=False)
        return Response({'id': order.id, 'status_code': order.status, 'status': order.get_status_display()})

    @action(methods=['post', 'put'], detail=False, url_path='charge', url_name='charge')
    def charge(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        create_action(request.user, '审核', order, limit=False)
        return Response({'id': order.id, 'status_code': order.status, 'status': order.get_status_display()})


class RecoverOrderViewSet(CreateModelMixin,
                          ListModelMixin,
                          RetrieveModelMixin,
                          UpdateModelMixin,
                          GenericViewSet):
    queryset = RecoverOrder.objects.all()
    serializer_class = RecoverOrderSerializer
    lookup_field = 'pk'
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_class = RecoverOrderFilter
    search_fields = ('$id', '$user__username', '$user__realname')
    ordering_fields = ('created',)

    def get_serializer_class(self):
        if self.action == 'create':
            return RecoverOrderSerializer
        if self.action == 'update':
            return UpdateRecoverOrderSerializer
        if self.action == 'list':
            return ListRecoverOrderSerializer
        if self.action == 'retrieve':
            return ListRecoverOrderSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), DjangoModelPermissions()]
        elif self.action == 'update':
            return [IsAuthenticated(), DjangoModelPermissions(), RecoverOrderIsSameGroup()]
        elif self.action == 'can_create':
            return [IsAuthenticated(), DjangoModelPermissions()]
        elif self.action == 'can_update':
            return [IsAuthenticated(), DjangoModelPermissions()]
        elif self.action == 'all_can_update':
            return [IsAuthenticated(), DjangoModelPermissions()]
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recover_order = self.perform_create(serializer)
        order = recover_order.order
        # status
        order.status = serializer.get_status(recover_order)
        order.save()

        # 这个地方有问题，两分钟内重复操作不记录
        create_action(request.user, '申请复机', order, limit=False)

        headers = self.get_success_headers(serializer.data)
        return Response({'id': recover_order.id,
                         'order_id': order.id,
                         'status_code': order.status,
                         'status': order.get_status_display()},
                        status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        return serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        order = instance.order
        order.status = serializer.get_status(instance)
        order.save()

        create_action(request.user, '修改复机', order, limit=False)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response({'id': instance.id,
                         'order_id': order.id,
                         'status_code': order.status,
                         'status': order.get_status_display()})

    @action(methods=['get'], detail=False, url_path='can-create', url_name='can_create')
    def can_create(self, request):
        user = request.user
        id = request.query_params.get('order')
        if not id:
            return Response({'detail': '请输入 order 参数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = Order.objects.get(id=id)
        except Exception as e:
            return Response({'detail': e}, status=status.HTTP_400_BAD_REQUEST)

        qc_code = settings.GROUP_CODE['TFT'].get('QC')
        qc = GroupSetting.objects.get(code=qc_code).group

        # if order.status == '1' or order.status == '2' or order.status == '3' or order.status == '9':
        if order.status != '4' and order.status != '7' and order.status != '8':
            return Response({'detail': '此状态不允许复机申请'}, status=status.HTTP_400_BAD_REQUEST)

        if not order.group:
            if not user.groups.filter(name=order.charge_group.name).exists():
                return Response({'detail': '开单工程不是 QC，只有责任工程才能申请复机'}, status=status.HTTP_400_BAD_REQUEST)
        elif order.group.name == qc.name:
            if not user.groups.filter(Q(name=order.charge_group.name) | Q(name=qc.name)).exists():
                return Response({'detail': '开单工程是 QC，只有责任工程和 QC 才能申请复机'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not user.groups.filter(name=order.charge_group.name).exists():
                return Response({'detail': '开单工程不是 QC，只有责任工程才能申请复机'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'can': True})

    @action(methods=['get'], detail=True, url_path='can-update', url_name='can_update')
    def can_update(self, request, pk=None):
        user = request.user
        instance = self.get_object()

        if RecoverAudit.objects.filter(recover_order__id=instance.id).exists():
            return Response({'can': False})
        # 这段逻辑错误
        # try:
        #     if instance.order.group.name in [group.name for group in user.groups.all()]:
        #         return Response({'can': True})
        # except AttributeError:
        #     return Response({'can': False})

        groups = [group.name for group in instance.user.groups.all()]
        user_groups = [group.name for group in user.groups.all()]
        if set(groups) & set(user_groups):
            return Response({'can': True})
        return Response({'can': False})


    @action(methods=['get'], detail=False, url_path='all-can-update', url_name='all_can_update')
    def all_can_update(self, request):
        user = request.user
        # recover_orders = self.queryset.filter(order__group__name__in=[group.name for group in user.groups.all()],
        #                                       audit=None)
        recover_orders = self.queryset.filter(user__groups__name__in=[group.name for group in user.groups.all()],
                                              audit=None)
        ids = [recover_order.id for recover_order in recover_orders]

        return Response(ids)



class RecoverAuditViewSet(GenericViewSet):
    queryset = RecoverAudit.objects.all()
    serializer_class = QcRecoverAuditSerializer
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_serializer_class(self):
        if self.action == 'qc':
            return QcRecoverAuditSerializer
        elif self.action == 'product':
            return ProductRecoverAuditSerializer
        return self.serializer_class

    @action(methods=['post'], detail=False, url_path='qc', url_name='qc')
    def qc(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recover_audit = serializer.save()
        recover_order = recover_audit.recover_order
        recover_order.order.status = serializer.get_status(recover_audit)
        recover_order.order.save()
        create_action(request.user, '审核', recover_order.order, limit=False)

        return Response({'id': recover_order.id,
                         'order_id': recover_order.order.id,
                         'status': recover_order.order.get_status_display()},
                        status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='product', url_name='product')
    def product(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recover_audit = serializer.save()
        recover_order = recover_audit.recover_order
        recover_order.order.status = serializer.get_status(recover_audit)
        recover_order.order.save()
        create_action(request.user, '审核', recover_order.order, limit=False)

        return Response({'id': recover_order.id,
                         'order_id': recover_order.order.id,
                         'status': recover_order.order.get_status_display()},
                        status=status.HTTP_200_OK)


class RemarkViewSet(CreateModelMixin,
                    ListModelMixin,
                    GenericViewSet):
    queryset = Remark.objects.all()
    serializer_class = RemarkSerializer
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateRemarkSerializer
        if self.action == 'list':
            return RemarkSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), DjangoModelPermissions()]
        return [permission() for permission in self.permission_classes]

    def list(self, request, *args, **kwargs):
        order_id = request.query_params.get('order')
        if not order_id:
            return Response({'detail': '请传入 order 参数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order = Order.objects.get(id=order_id)
        except Exception as e:
            return Response({'detail': '未找到 order'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(order.remarks.all(), many=True)
        return Response(serializer.data)


class ShortcutViewSet(ListModelMixin, GenericViewSet):
    queryset = Shortcut.objects.all()
    serializer_class = ShortcutSerializer


class OrderViewSet(ListModelMixin,
                   RetrieveModelMixin,
                   GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]
    pagination_class = OrderPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_class = OrderFilter
    search_fields = ('$id', '$user__username', '$user__realname')
    ordering_fields = ('created',)
