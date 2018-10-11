import os
import json
import string
import random
from collections import OrderedDict
from datetime import datetime

import pandas as pd
import xlsxwriter

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
        s = OrderSerializer(queryset, many=True, context={'request': request})

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

        elif format == 'csv':
            data = [dict(row) for row in s.data]

            # return HttpResponseRedirect(reverse('tft:order-exporting'))
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

            url = request.build_absolute_uri(
                api_settings.UPLOADED_FILES_USE_PREFIX + settings.MEDIA_URL + 'csv/' + name)
            return Response({'url': url})
        else:
            data = []
            for row in s.data:
                item = OrderedDict()
                item['编号'] = row.get('id')
                item['状态'] = row.get('status').get('desc')
                item['申请人工号'] = row.get('user').get('username')
                item['申请人真名'] = row.get('user').get('realname')
                item['开单工程'] = row.get('group').get('name')
                item['开单时间'] = row.get('created')
                if row.get('created'):
                    item['开单时间'] = datetime.fromisoformat(row.get('created')).strftime('%Y/%m/%d %H:%M:%S')
                else:
                    item['开单时间'] = None
                item['修改人工号'] = row.get('mod_user').get('username')
                item['修改人真名'] = row.get('mod_user').get('realname')
                if row.get('modified'):
                    item['修改时间'] = datetime.fromisoformat(row.get('modified')).strftime('%Y/%m/%d %H:%M:%S')
                else:
                    item['修改时间'] = None
                item['发现站点'] = row.get('found_step')
                if row.get('found_time'):
                    item['发现时间'] = datetime.fromisoformat(row.get('found_time')).strftime('%Y/%m/%d %H:%M:%S')
                else:
                    item['发现时间'] = None
                item['责任工程'] = row.get('charge_group').get('name')
                item['停机设备'] = row.get('eq')
                item['停机机种'] = row.get('kind')
                item['停机站点'] = row.get('step')
                item['停机原因'] = row.get('reason')
                item['通知生产人员'] = row.get('users')
                item['通知制程人员'] = row.get('charge_users')
                item['异常描述'] = row.get('desc')
                if row.get('start_time'):
                    item['受害开始时间'] = datetime.fromisoformat(row.get('start_time')).strftime('%Y/%m/%d %H:%M:%S')
                else:
                    item['受害开始时间'] = None
                if row.get('end_time'):
                    item['受害结束时间'] = datetime.fromisoformat(row.get('end_time')).strftime('%Y/%m/%d %H:%M:%S')
                else:
                    item['受害结束时间'] = None
                item['受害批次数'] = row.get('lot_num')
                item['异常批次/基板'] = row.get('lots')
                item['复机条件'] = row.get('condition')

                if row.get('defect_type') == True:
                    item['绝对不良'] = '是'
                elif row.get('defect_type') == False:
                    item['绝对不良'] = '否'
                else:
                    item['绝对不良'] = None
                reports = ''
                for report in row.get('reports').keys():
                    reports += str(report) + ', '
                item['调查报告'] = reports

                if row.get('remarks'):
                    user = row.get('remarks')[0].get('user')
                    username = user.get('username')
                    realname = user.get('realname')
                    content = row.get('remarks')[0].get('content')
                    item['最新批注'] = f'{username}/{realname}: {content}'
                else:
                    item['最新批注'] = None

                audit = row.get('startaudit')
                item['生产领班签核'] = audit.get('p_signer').get('username')
                if audit.get('p_time'):
                    item['生产签字时间'] = datetime.fromisoformat(audit.get('p_time')).strftime('%Y/%m/%d %H:%M:%S')
                else:
                    item['生产签字时间'] = None
                item['Recipe关闭人员'] = audit.get('recipe_close')
                item['Recipe确认人员'] = audit.get('recipe_confirm')
                item['责任工程签字'] = audit.get('c_signer').get('username')
                if audit.get('c_time'):
                    item['工程签字时间'] = datetime.fromisoformat(audit.get('c_time')).strftime('%Y/%m/%d %H:%M:%S')
                else:
                    item['工程签字时间'] = None

                if audit.get('rejected'):
                    item['是否拒签'] = '是'
                else:
                    item['是否拒签'] = '否'

                item['拒签理由'] = audit.get('reason')

                i = 1
                for r in row.get('recoverorders'):
                    item[f'复机单号{i}'] = r.get('id')
                    item[f'复机申请人{i}'] = r.get('user').get('username')
                    item[f'复机申请人真名{i}'] = r.get('user').get('realname')
                    if r.get('created'):
                        item['复机申请时间{i}'] = datetime.fromisoformat(r.get('created')).strftime('%Y/%m/%d %H:%M:%S')
                    else:
                        item['复机申请时间{i}'] = None
                    item[f'复机修改人{i}'] = r.get('mod_user').get('username')
                    item[f'复机修改人真名{i}'] = r.get('mod_user').get('realname')
                    if r.get('modified'):
                        item['复机修改时间{i}'] = datetime.fromisoformat(r.get('modified')).strftime('%Y/%m/%d %H:%M:%S')
                    else:
                        item['复机修改时间{i}'] = None
                    item[f'责任单位对策说明{i}'] = r.get('solution')
                    item[f'先行lot结果说明{i}'] = r.get('explain')
                    if r.get('partial'):
                        item[f'部分复机{i}'] = '是'
                    else:
                        item[f'部分复机{i}'] = '否'
                    item[f'部分复机设备{i}'] = r.get('eq')
                    item[f'部分复机机种{i}'] = r.get('kind')
                    item[f'部分复机站点{i}'] = r.get('step')

                    r_audit = r.get('audit')
                    item[f'工程品质签复{i}'] = r_audit.get('qc_signer').get('username')
                    if r_audit.get('qc_time'):
                        item['品质签复时间{i}'] = datetime.fromisoformat(r_audit.get('qc_time')).strftime('%Y/%m/%d %H:%M:%S')
                    else:
                        item['品质签复时间{i}'] = None
                    item[f'生产领班签复{i}'] = r_audit.get('p_signer').get('username')
                    if r_audit.get('p_time'):
                        item['生产签复时间{i}'] = datetime.fromisoformat(r_audit.get('p_time')).strftime('%Y/%m/%d %H:%M:%S')
                    else:
                        item['生产签复时间{i}'] = None

                    if r_audit.get('rejected'):
                        item[f'是否拒签{i}'] = '是'
                    else:
                        item[f'是否拒签{i}'] = '否'

                    item[f'拒签理由{i}'] = r_audit.get('reason')

                    i += 1

                data.append(item)

            df = pd.DataFrame(data)

            random_string = ''.join(random.sample(string.ascii_letters + string.digits, 7))

            name = random_string + '.' + format
            file = os.path.join(settings.MEDIA_ROOT, 'xlsx', name)

            engine = 'xlsxwriter' if format=='xlsx' else 'xlwt'

            df.to_excel(file, sheet_name='停机单列表', engine=engine)

            url = request.build_absolute_uri(
                api_settings.UPLOADED_FILES_USE_PREFIX + settings.MEDIA_URL + 'xlsx/' + name)
            return Response({'url': url})

    @action(methods=['GET'], detail=True, url_path='export-detail', url_name='export_detail')
    def export_detail(self, request, pk):
        order = self.get_object()
        s = OrderSerializer(order, context={'request': request})
        data = s.data

        # random_string = ''.join(random.sample(string.ascii_letters + string.digits, 7))

        name = pk + '.xlsx'
        file = os.path.join(settings.MEDIA_ROOT, 'xlsx', 'detail', name)

        workbook = xlsxwriter.Workbook(file)
        sheet1 = workbook.add_worksheet()

        h1_fmt = workbook.add_format({
            'bold': 2,
            'font_size': 13,
            'bg_color': '#9FA4A9',
            'align': 'center',
        })
        h3_fmt = workbook.add_format({
            'bold': 1,
            'font_size': 12,
            'bg_color': '#9FA4A9',
        })
        label_fmt = workbook.add_format({
            'bold': True
            # 'bg_color': '#9FA4A9'
        })
        date_fmt = workbook.add_format({
            'num_format': 'mmmm d yyyy'
        })

        sheet1.set_column(0, 0, 15)
        sheet1.set_column(1, 1, 18)
        sheet1.set_column(2, 2, 15)
        sheet1.set_column(3, 3, 18)
        sheet1.set_column(4, 5, 15)
        sheet1.set_column(6, 6, 18)

        try:
            sheet1.merge_range('A1:F1', '设备品质异常停机单', h1_fmt)

            sheet1.write('A2', '编号', label_fmt)
            sheet1.write('B2', data.get('id'))
            sheet1.write('C2', '状态', label_fmt)
            sheet1.write('D2', data.get('status').get('desc'))
            sheet1.write('E2', '开单工程', label_fmt)
            sheet1.write('F2', data.get('group').get('name'))

            sheet1.write('A3', '开单人员', label_fmt)
            sheet1.write('B3', data.get('user').get('username'))
            sheet1.write('C3', '开单时间', label_fmt)
            sheet1.write('D3', datetime.fromisoformat(data.get('created')).strftime('%Y/%m/%d %H:%M:%S'))

            sheet1.write('A4', '修改人员', label_fmt)
            sheet1.write('B4', data.get('mod_user').get('username'))
            sheet1.write('C4', '修改时间', label_fmt)
            sheet1.write('D4', datetime.fromisoformat(data.get('modified')).strftime('%Y/%m/%d %H:%M:%S'))

            sheet1.write('A5', '发现站点', label_fmt)
            sheet1.write('B5', data.get('found_step'))
            sheet1.write('C5', '发现时间', label_fmt)
            sheet1.write('D5', datetime.fromisoformat(data.get('found_time')).strftime('%Y/%m/%d %H:%M:%S'))
            sheet1.write('E5', '责任工程', label_fmt)
            sheet1.write('F5', data.get('charge_group').get('name'))

            sheet1.write('A6', '停机设备', label_fmt)
            sheet1.write('B6', data.get('eq'))
            sheet1.write('C6', '停机机种', label_fmt)
            sheet1.write('D6', data.get('kind'))
            sheet1.write('E6', '停机站点', label_fmt)
            sheet1.write('F6', data.get('step'))

            sheet1.write('A7', '停机原因', label_fmt)
            sheet1.merge_range('B7:D8', data.get('reason'))
            sheet1.write('E7', '通知生产人员', label_fmt)
            sheet1.write('F7', data.get('users'))
            sheet1.write('E8', '通知制程人员', label_fmt)
            sheet1.write('F8', data.get('charge_users'))

            sheet1.merge_range('A9:F9', '异常状况描述（不良现象说明）', h3_fmt)

            sheet1.write('A10', '异常描述', label_fmt)
            sheet1.merge_range('B10:D11', data.get('desc'))
            sheet1.write('E10', '受害开始时间', label_fmt)
            if data.get('start_time'):
                sheet1.write('F10', datetime.fromisoformat(data.get('start_time')).strftime('%Y/%m/%d %H:%M:%S'))
            sheet1.write('E11', '受害结束时间', label_fmt)
            if data.get('end_time'):
                sheet1.write('F11', datetime.fromisoformat(data.get('end_time')).strftime('%Y/%m/%d %H:%M:%S'))

            sheet1.write('A12', '异常批次/基板', label_fmt)
            sheet1.merge_range('B12:D12', data.get('lots'))
            sheet1.write('E12', '受害批次数', label_fmt)
            sheet1.write('F12', data.get('lot_num'))

            sheet1.write('A13', '复机条件', label_fmt)
            sheet1.merge_range('B13:D13', data.get('condition'))
            sheet1.write('E13', '绝对不良', label_fmt)
            if data.get('defect_type') == True:
                sheet1.write('F13', '是')
            elif data.get('defect_type') == False:
                sheet1.write('F13', '否')
            else:
                pass

            sheet1.write('A14', '最新批注', label_fmt)
            if data.get('remarks'):
                user = data.get('remarks')[0].get('user')
                username = user.get('username')
                realname = user.get('realname')
                content = data.get('remarks')[0].get('content')
                remark = f'{username}/{realname}: {content}'
            else:
                remark = None
            sheet1.merge_range('B14:D14', remark)
            sheet1.write('E14', '调查报告', label_fmt)
            reports = ''
            for report in data.get('reports').keys():
                reports += str(report) + ', '
            sheet1.write('F14', reports)

            sheet1.merge_range('A15:F15', '停机签核', h3_fmt)

            audit = data.get('startaudit')

            sheet1.write('A16', '生产领班签核', label_fmt)
            sheet1.merge_range('B16:C16', audit.get('p_signer').get('username'))
            sheet1.write('D16', '生产签字时间', label_fmt)
            if audit.get('p_time'):
                sheet1.merge_range('E16:F16', datetime.fromisoformat(audit.get('p_time')).strftime('%Y/%m/%d %H:%M:%S'))

            sheet1.write('A17', 'Recipe关闭人员', label_fmt)
            sheet1.merge_range('B17:C17', audit.get('recipe_close'))
            sheet1.write('D17', 'Recipe确认人员', label_fmt)
            sheet1.merge_range('E17:F17', audit.get('recipe_confirm'))

            sheet1.write('A18', '责任工程签字', label_fmt)
            sheet1.merge_range('B18:C18', audit.get('c_signer').get('username'))
            sheet1.write('D18', '工程签字时间', label_fmt)
            if audit.get('c_time'):
                sheet1.merge_range('E18:F18', datetime.fromisoformat(audit.get('c_time')).strftime('%Y/%m/%d %H:%M:%S'))

            sheet1.write('A19', '是否拒签', label_fmt)
            if audit.get('rejected'):
                sheet1.merge_range('B19:C19', '是')
            else:
                sheet1.merge_range('B19:C19', '否')
            sheet1.write('D19', '拒签理由', label_fmt)
            sheet1.merge_range('E19:F19', audit.get('reason'))

            sheet1.merge_range('A20:F20', '设备品质异常复机单', h1_fmt)

            recoverorders = data.get('recoverorders')
            index = len(recoverorders)
            row = 20
            for r in recoverorders:
                sheet1.write(row, 0, f'复机单{index}', h3_fmt)
                sheet1.write(row, 1, r.get('id'), h3_fmt)

                sheet1.write(row+1, 0, '申请人', label_fmt)
                sheet1.merge_range(row+1, 1, row+1, 2, r.get('user').get('username'))
                sheet1.write(row+1, 3, '申请时间', label_fmt)
                if r.get('created'):
                    sheet1.merge_range(row+1, 4, row+1, 5, datetime.fromisoformat(r.get('created')).strftime('%Y/%m/%d %H:%M:%S'))

                sheet1.write(row+2, 0, '修改人', label_fmt)
                sheet1.merge_range(row+2, 1, row+2, 2, r.get('mod_user').get('username'))
                sheet1.write(row+2, 3, '修改时间', label_fmt)
                if r.get('modified'):
                    sheet1.merge_range(row+2, 4, row+2, 5, datetime.fromisoformat(r.get('modified')).strftime('%Y/%m/%d %H:%M:%S'))

                sheet1.write(row+3, 0, '责任单位对策说明', label_fmt)
                sheet1.merge_range(row+3, 1, row+3, 5, r.get('solution'))

                sheet1.write(row+4, 0, '先行lot结果说明', label_fmt)
                sheet1.merge_range(row + 4, 1, row + 4, 5, r.get('explain'))

                sheet1.write(row + 5, 0, '部分复机', label_fmt)
                if r.get('partial'):
                    sheet1.merge_range(row + 5, 1, row + 5, 5, '是')
                else:
                    sheet1.merge_range(row + 5, 1, row + 5, 5, '否')

                sheet1.write(row + 6, 0, '部分复机设备', label_fmt)
                sheet1.merge_range(row + 6, 1, row + 6, 5, r.get('eq'))

                sheet1.write(row + 7, 0, '部分复机机种', label_fmt)
                sheet1.merge_range(row + 7, 1, row + 7, 5, r.get('kind'))

                sheet1.write(row + 8, 0, '部分复机站点', label_fmt)
                sheet1.merge_range(row + 8, 1, row + 8, 5, r.get('step'))

                r_audit = r.get('audit')
                sheet1.merge_range(row + 9, 0, row + 9, 5, '复机签核', h3_fmt)

                sheet1.write(row + 10, 0, '工程品质签复', label_fmt)
                sheet1.merge_range(row + 10, 1, row + 10, 2, r_audit.get('qc_signer').get('username'))
                sheet1.write(row + 10, 3, '品质签复时间', label_fmt)
                if r_audit.get('qc_time'):
                    sheet1.merge_range(row + 10, 4, row + 10, 5, datetime.fromisoformat(r_audit.get('qc_time')).strftime('%Y/%m/%d %H:%M:%S'))

                sheet1.write(row + 11, 0, '生产领班签复', label_fmt)
                sheet1.merge_range(row + 11, 1, row + 11, 2, r_audit.get('p_signer').get('username'))
                sheet1.write(row + 11, 3, '生产签复时间', label_fmt)
                if r_audit.get('p_time'):
                    sheet1.merge_range(row + 11, 4, row + 11, 5, datetime.fromisoformat(r_audit.get('p_time')).strftime('%Y/%m/%d %H:%M:%S'))

                sheet1.write(row + 12, 0, '是否拒签', label_fmt)
                if r_audit.get('rejected'):
                    sheet1.write(row + 12, 1, '是')
                else:
                    sheet1.write(row + 12, 1, '否')

                sheet1.write(row + 13, 0, '拒签理由', label_fmt)
                sheet1.merge_range(row + 13, 1, row + 13, 5, r_audit.get('reason'))

                index -= 1
                row += 14

            workbook.close()
        except:
            return Response({'detail': '导出失败'}, status=400)

        url = request.build_absolute_uri(
            api_settings.UPLOADED_FILES_USE_PREFIX + settings.MEDIA_URL + 'xlsx/detail/' + name)
        return Response({'url': url})
