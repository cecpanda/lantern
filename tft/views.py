import os
import json
import string
import random

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import Group
from django.core.exceptions import FieldError
from django.template import Context, loader
from rest_framework.response import Response
from rest_framework import status
from rest_framework.settings import api_settings
from rest_framework.reverse import reverse
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
                         OrderSerializer, ShortcutSerializer, \
                         ExportSerializer

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
    search_fields = ('$id', '$user__username', '$user__realname',
                     '$mod_user__username', '$mod_user__realname',
                     '$found_step', '$eq', '$kind', '$step',
                     '$reason', '$users', '$charge_users',
                     '$desc', '$condition')
    ordering_fields = ('created',)

    def get_serializer_class(self):
        if self.action == 'export':
            return ExportSerializer
        return self.serializer_class

    @action(methods=['GET'], detail=False, url_path='status-flow', url_name='status_flow')
    def status_flow(self, request):
        id = request.query_params.get('id')
        try:
            order = Order.objects.get(id=id)
        except Exception as e:
            return Response({'detail': 'id 不存在'}, status=404)

        data = {
            'code': order.status,
            'desc': order.get_status_display(),
            'current': '',
            'ago': [],
            # 'to': [],
            # 'ban': []
        }
        qc_code = settings.GROUP_CODE['TFT'].get('QC')
        try:
            qc = GroupSetting.objects.get(code=qc_code).group
        except Exception:
            return Response({'detail': '为定义QC组'}, status=400)

        if data['code'] == '1':
            if order.group.name == qc.name:
                if order.defect_type == True:
                    data['current'] = 'b7'
                    data['ago'] = ['b1', 'b2', 'b4', 'l1', 'l5', 'l10']
                else:
                    data['current'] = 'b6'
                    data['ago'] = ['b1', 'b2', 'b4', 'b5', 'l1', 'l5', 'l6', 'l7']
            else:
                data['current'] = 'b3'
                data['ago'] = ['b1', 'b2', 'l1', 'l2']
        elif data['code'] == '2':
            if order.defect_type == True:
                data['current'] = 'b8'
                data['ago'] = ['b1', 'b2', 'b4', 'b7', 'l1', 'l5', 'l10', 'l11']
            else:
                data['current'] = 'b5'
                data['ago'] = ['b1', 'b2', 'b4', 'l1', 'l5', 'l6']
        elif data['code'] == '3':
            data['current'] = 'b9'
            try:
                p_signer = order.startaudit.p_signer
                if p_signer:
                    data['ago'] = ['b1', 'b2', 'b4', 'b7', 'b8', 'l1', 'l5', 'l10', 'l11', 'l12']
                else:
                    data['ago'] = ['b1', 'b2', 'b4', 'b5', 'l1', 'l5', 'l6', 'l9']
            except:
                pass
        elif data['code'] == '4':
            data['current'] = 'b10'
            if order.group.name == qc.name:
                if order.defect_type == True:
                    data['ago'] = ['b1', 'b2', 'b4', 'b7', 'b8', 'l1', 'l5', 'l10', 'l11', 'l13']
                else:
                    data['ago'] = ['b1', 'b2', 'b4', 'b5', 'b6', 'l1', 'l5', 'l6', 'l7', 'l8']
            else:
                data['ago'] = ['b1', 'b2', 'b3', 'l1', 'l2', 'l3', 'l4']
        elif data['code'] == '5':
            data['current'] = 'b15'
            # 其实这个判断没有必要，因为一定是 QC
            if order.group.name == qc.name:
                if order.defect_type == True:
                    data['ago'] = ['b1', 'b2', 'b4', 'b7', 'b8', 'b10', 'b11', 'b12', 'b13',
                                   'l1', 'l5', 'l10', 'l11', 'l13', 'l14', 'l15', 'l16', 'l17']
                else:
                    data['ago'] = ['b1', 'b2', 'b4', 'b5', 'b6', 'b10', 'b11', 'b12', 'b13',
                                   'l1', 'l5', 'l6', 'l7', 'l8', 'l14', 'l15', 'l16', 'l17']
            else:
                data['ago'] = ['b1', 'b2', 'b3', 'b10', 'b11', 'b12', 'b13',
                               'l1', 'l2', 'l3', 'l4', 'l14', 'l15', 'l16', 'l17']
        elif data['code'] == '6':
            data['current'] = 'b16'
            if order.group.name == qc.name:
                if order.defect_type == True:
                    data['ago'] = ['b1', 'b2', 'b4', 'b7', 'b8', 'b10', 'b11', 'b12', 'b13', 'b15',
                                   'l1', 'l5', 'l10', 'l11', 'l13', 'l14', 'l15', 'l16', 'l17', 'l18']
                else:
                    data['ago'] = ['b1', 'b2', 'b4', 'b5', 'b6', 'b10', 'b11', 'b12', 'b13', 'b15',
                                   'l1', 'l5', 'l6', 'l7', 'l8', 'l14', 'l15', 'l16', 'l17', 'l18']
            else:
                data['ago'] = ['b1', 'b2', 'b3', 'b10', 'b11', 'b12', 'b14',
                               'l1', 'l2', 'l3', 'l4', 'l14', 'l15', 'l21', 'l22', 'l23']
        elif data['code'] == '7':
            data['current'] = 'b17'
            if order.defect_type == True:
                data['ago'] = ['b1', 'b2', 'b4', 'b7', 'b8', 'b10', 'b11', 'b12', 'b13', 'b15',
                               'l1', 'l5', 'l10', 'l11', 'l13', 'l14', 'l15', 'l16', 'l17', 'l19']
            else:
                data['ago'] = ['b1', 'b2', 'b4', 'b5', 'b6', 'b10', 'b11', 'b12', 'b13', 'b15',
                               'l1', 'l5', 'l6', 'l7', 'l8', 'l14', 'l15', 'l16', 'l17', 'l19']
        elif data['code'] == '8' or data['code'] == '9':
            data['current'] = 'b18'
            if order.group.name == qc.name:
                if order.defect_type == True:
                    data['ago'] = ['b1', 'b2', 'b4', 'b7', 'b8', 'b10', 'b11', 'b12', 'b13', 'b15', 'b16',
                                   'l1', 'l5', 'l10', 'l11', 'l13', 'l14', 'l15', 'l16', 'l17', 'l18', 'l20']
                else:
                    data['ago'] = ['b1', 'b2', 'b4', 'b5', 'b6', 'b10', 'b11', 'b12', 'b13', 'b15', 'b16',
                                   'l1', 'l5', 'l6', 'l7', 'l8', 'l14', 'l15', 'l16', 'l17', 'l18', 'b20']
            else:
                data['ago'] = ['b1', 'b2', 'b3', 'b10', 'b11', 'b12', 'b14', 'b16',
                              'l1', 'l2', 'l3', 'l4', 'l14', 'l15', 'l21', 'l22', 'l23', 'b20']
        else:
            data['current'] = 'b1'

        return Response(data)

    @action(methods=['GET'], detail=False, url_path='summary', url_name='summary')
    def summary(self, request):
        '''
        [{'cvd': ['停机单数', ‘停机审核中’, '停机拒签', ‘停机完成’,
                  '已复机', '复机完成率', '其他（复机审核中、复机拒签、部分复机）']}, ...]
        '''
        which = request.query_params.get('which')
        if not which in ['group', 'charge_group']:
            return Response({'key': '请提供适合的 which 参数（group & charge_group）'}, status=status.HTTP_400_BAD_REQUEST)

        groups = Group.objects.all()

        sum_list = []
        audits_list = []
        rejects_list = []
        closed_list = []
        finished_list = []
        others_list = []
        """
        groups: ['CVD', 'MFG', 'PVD',]
        table: [
          {'group': 'CVD', 'sum': 13, 'audits': 10, 'rejects': 0, 'closed': 0, 'finished': 0, 'others': 3}, 
          {'group': 'MFG', 'sum': 4, 'audits': 3, 'rejects': 0, 'closed': 0, 'finished': 0, 'others': 1}, 
          {'group': 'PVD', 'sum': 3, 'audits': 2, 'rejects': 0, 'closed': 0, 'finished': 1, 'others': 0}, 
        ]
        
        bar: [
          {'name': '停机单数', 'type': 'bar', 'data': [13, 4, 3, 9, 1, 0, 0, 0]}, 
          {'name': '停机审核中', 'type': 'bar', 'stack': 'a', 'data': [10, 3, 2, 9, 1, 0, 0, 0]},
          {'name': '停机拒签', 'type': 'bar', 'stack': 'a', 'data': [0, 0, 0, 0, 0, 0, 0, 0]}, 
        ]
        
        pie: [
          {'value': 13, 'name': 'CVD'}, 
          {'value': 4, 'name': 'MFG'}, 
        ]
        """
        data = {
            'groups': [],
            'table': [],
            'bar': [],
            'pie': []
        }

        if which == 'group':
            for group in groups:
                sum = Order.objects.filter(group=group).count()
                audits = Order.objects.filter(group=group, status__in=['1', '2']).count()
                rejects = Order.objects.filter(group=group, status='3').count()
                closed = Order.objects.filter(group=group, status='4').count()
                finished = Order.objects.filter(group=group, status='9').count()
                # try:
                #     rate = '{:.2%}'.format(finished / sum)
                # except ZeroDivisionError as e:
                #     rate = '{:.2%}'.format(0)
                others = Order.objects.filter(group=group, status__in=['0', '5', '6', '7', '8']).count()

                data['groups'].append(group.name)
                data['table'].append({
                    'group': group.name,
                    'sum': sum,
                    'audits': audits,
                    'rejects': rejects,
                    'closed': closed,
                    'finished': finished,
                    'others': others
                })
                if sum > 0:
                    data['pie'].append({'value': sum, 'name': group.name})

                sum_list.append(sum)
                audits_list.append(audits)
                rejects_list.append(rejects)
                closed_list.append(closed)
                finished_list.append(finished)
                others_list.append(others)
        elif which == 'charge_group':
            for group in groups:
                sum = Order.objects.filter(charge_group=group).count()
                audits = Order.objects.filter(charge_group=group, status__in=['1', '2']).count()
                rejects = Order.objects.filter(charge_group=group, status='3').count()
                closed = Order.objects.filter(charge_group=group, status='4').count()
                finished = Order.objects.filter(charge_group=group, status='9').count()
                # try:
                #     rate = '{:.2%}'.format(finished / sum)
                # except ZeroDivisionError as e:
                #     rate = '{:.2%}'.format(0)
                others = Order.objects.filter(charge_group=group, status__in=['0', '5', '6', '7', '8']).count()
                data['groups'].append(group.name)
                data['table'].append({
                    'group': group.name,
                    'sum': sum,
                    'audits': audits,
                    'rejects': rejects,
                    'closed': closed,
                    'finished': finished,
                    'others': others
                })
                if sum > 0:
                    data['pie'].append({'value': sum, 'name': group.name})

                sum_list.append(sum)
                audits_list.append(audits)
                rejects_list.append(rejects)
                closed_list.append(closed)
                finished_list.append(finished)
                others_list.append(others)

        data['bar'].append({'name': '停机单数', 'type': 'bar', 'data': sum_list})
        data['bar'].append({'name': '停机审核中', 'type': 'bar', 'stack': 'a', 'data': audits_list})
        data['bar'].append({'name': '停机拒签', 'type': 'bar', 'stack': 'a', 'data': rejects_list})
        data['bar'].append({'name': '停机完成', 'type': 'bar', 'stack': 'a', 'data': closed_list})
        data['bar'].append({'name': '已复机', 'type': 'bar', 'stack': 'a', 'data': finished_list})
        data['bar'].append({'name': '其他', 'type': 'bar', 'stack': 'a', 'data': others_list})

        return Response(data=data)

    @action(methods=['POST'], detail=False, url_path='export', url_name='export')
    def export(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data.get('ids')
        format = serializer.validated_data.get('format')
        queryset = Order.objects.filter(id__in=ids)

        if format == 'chart':
            groups = set()
            sum_list = []
            audits_list = []
            rejects_list = []
            closed_list = []
            finished_list = []
            others_list = []
            data = {
                'groups': [],
                'table': [],
                'bar': [],
                'pie': []
            }
            for order in queryset:
                groups.add(order.charge_group)

            for group in groups:
                sum = queryset.filter(charge_group=group).count()
                audits = queryset.filter(charge_group=group, status__in=['1', '2']).count()
                rejects = queryset.filter(charge_group=group, status='3').count()
                closed = queryset.filter(charge_group=group, status='4').count()
                finished = queryset.filter(charge_group=group, status='9').count()
                others = queryset.filter(charge_group=group, status__in=['0', '5', '6', '7', '8']).count()
                data['groups'].append(group.name)
                data['table'].append({
                    'group': group.name,
                    'sum': sum,
                    'audits': audits,
                    'rejects': rejects,
                    'closed': closed,
                    'finished': finished,
                    'others': others
                })
                if sum > 0:
                    data['pie'].append({'value': sum, 'name': group.name})

                sum_list.append(sum)
                audits_list.append(audits)
                rejects_list.append(rejects)
                closed_list.append(closed)
                finished_list.append(finished)
                others_list.append(others)

            data['bar'].append({'name': '停机单数', 'type': 'bar', 'data': sum_list})
            data['bar'].append({'name': '停机审核中', 'type': 'bar', 'stack': 'a', 'data': audits_list})
            data['bar'].append({'name': '停机拒签', 'type': 'bar', 'stack': 'a', 'data': rejects_list})
            data['bar'].append({'name': '停机完成', 'type': 'bar', 'stack': 'a', 'data': closed_list})
            data['bar'].append({'name': '已复机', 'type': 'bar', 'stack': 'a', 'data': finished_list})
            data['bar'].append({'name': '其他', 'type': 'bar', 'stack': 'a', 'data': others_list})

            return Response(data=data)

        s = OrderSerializer(queryset, many=True, context={'request': request})
        data = [dict(row) for row in s.data]

        # return HttpResponseRedirect(reverse('tft:order-exporting'))

        return self.exporting(request, data, format)

    # @action(methods=['GET'], detail=False, url_path='exporting', url_name='exporting')
    def exporting(self, request, data, format='csv'):
        if format == 'xlsx':
            pass

        else:
            # 前端使用下面的代码保存
            '''
            let blob = new Blob([res.data], {type: 'text/plain;charset=utf-8'})
            FileSaver.saveAs(blob, 'orders.csv')
            '''
            # response = HttpResponse(content_type='text/csv')
            # response['Content-Disposition'] = 'attachment; filename="orders.csv"'
            #
            # t = loader.get_template('tft/orders.txt')
            # context = {'data': data}
            # response.write(t.render(context))
            #
            # return response

            # 或者在服务端生成 csv，将连接发送给前端
            t = loader.get_template('tft/orders.txt')


            context = {'data': data}

            txt = t.render(context)

            random_string = ''.join(random.sample(string.ascii_letters + string.digits, 7))
            name = random_string + '.csv'

            file = os.path.join(settings.MEDIA_ROOT, 'csv', name)

            with open(file, 'w', encoding='utf8') as f:
                f.write(txt)

            url = request.build_absolute_uri(api_settings.UPLOADED_FILES_USE_PREFIX + settings.MEDIA_URL + 'csv/' + name)
            return Response({'url': url})
