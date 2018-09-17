from django.shortcuts import get_object_or_404
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import status
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
# from rest_framework_filters.backends import DjangoFilterBackend
# from rest_framework_filters.backends import RestFrameworkFilterBackend
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from django_filters.rest_framework import DjangoFilterBackend

from .models import Follow
from .serializers import UserSerializer, PasswordSerializer, GroupSerializer, \
                         GroupUserSerializer, UserUpdateSerializer, \
                         FollowingSerializer, FollowersSerializer, \
                         FollowSerializer, ListFollowSerializer
from .utils import UserPagination
from .filters import UserFilter
from action.utils import create_action


UserModel = get_user_model()


class UserViewSet(ListModelMixin,
                  RetrieveModelMixin,
                  viewsets.GenericViewSet):
    queryset = UserModel.objects.order_by('id')
    serializer_class = UserSerializer
    lookup_field = 'username'
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]
    pagination_class = UserPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_class = UserFilter
    search_fields = ('$username', '$realname')
    ordering_fields = ('username', 'realname')

    def get_serializer_class(self):
        if self.action == 'change_password':
            return PasswordSerializer
        elif self.action == "change_profile":
            return UserUpdateSerializer
        elif self.action == 'following':
            # return FollowingSerializer
            return UserSerializer
        elif self.action == 'followers':
            # return FollowersSerializer
            return  UserSerializer
        return self.serializer_class

    @action(methods=['post'], detail=False, url_path='change-password',
            url_name='change_password', permission_classes=[IsAuthenticated])
    def change_password(self, request):
        # 刚开始用 detail=True, self.get_object() 获得 user，这方法真特么傻
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        if user.check_password(serializer.validated_data.get('old_password')):
            user.set_password(serializer.validated_data.get('new_password'))
            user.save()
            return Response({'status': 'ok'}, status.HTTP_202_ACCEPTED)
        return Response({'error': 'wrong password'}, status.HTTP_401_UNAUTHORIZED)

    # 因为 UpdateModelMixin 的 url 不优雅，重新写，
    # 而且在此视图里比较难做到谁登录谁修改
    @action(methods=['put', 'post'], detail=False, url_path='change-profile',
            url_name='change_profile', permission_classes=[IsAuthenticated])
    def change_profile(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status.HTTP_201_CREATED)

    # 获取关注列表
    @action(methods=['get'], detail=True, url_path='following', url_name='following')
    def following(self, request, username=None):
        user = self.get_object()
        queryset = self.filter_queryset(user.following.all())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status.HTTP_200_OK)

    # 获取被关注列表
    @action(methods=['get'], detail=True, url_path='followers', url_name='followers')
    def followers(self, request, username=None):
        user = self.get_object()
        queryset = self.filter_queryset(user.followers.all())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='follow-status', url_name='follow_status')
    def follow_status(self, request):
        username_from = request.query_params.get('user_from')
        username_to = request.query_params.get('user_to')
        if not username_from:
            return Response({'detail': '请传入 user_from 参数'}, status=status.HTTP_400_BAD_REQUEST)
        if not username_to:
            return Response({'detail': '请传入 user_to 参数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_from = UserModel.objects.get(username=username_from)
            user_to = UserModel.objects.get(username=username_to)
        except:
            return Response({'status': False})
        if user_to in user_from.following.all():
            return Response({'status': True})
        return Response({'status': False})


class FollowViewSet(CreateModelMixin,
                    RetrieveModelMixin,
                    viewsets.GenericViewSet):
    """
    create:
    关注别人

    unfollow:
    取消关注

    retrieve:
    获取关注列表
    """
    queryset = Follow.objects.all()  # 其实没用到
    lookup_field = 'username'
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'create':
            return FollowSerializer
        elif self.action == 'unfollow':
            return FollowSerializer
        elif self.action == 'retrieve':
            return ListFollowSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        elif self.action == 'unfollow':
            return [IsAuthenticated()]
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_from = request.user
        user_to = UserModel.objects.get(username=serializer.validated_data['user_to'])
        Follow.objects.get_or_create(user_from=user_from, user_to=user_to)
        create_action(user_from, '关注', user_to)
        headers = self.get_success_headers(serializer.data)
        return Response({'status': 'ok'}, status=status.HTTP_201_CREATED, headers=headers)

    # 不能用 delete，不能携带 payload，蒙蔽了半天
    @action(methods=['post'], detail=False, url_path='unfollow', url_name='unfollow',
            permission_classes=[IsAuthenticated])
    def unfollow(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_from = request.user
        user_to = UserModel.objects.get(username=serializer.validated_data['user_to'])
        Follow.objects.filter(user_from=user_from, user_to=user_to).delete()
        create_action(user_from, '取消关注', user_to)
        return Response({'status': 'ok'}, status=status.HTTP_204_NO_CONTENT)

    # 获取任意用户的关注、被关注列表
    # 此方法看起来十分不友好，重新了这么多,
    # 分页、什么的目测很难用到
    # 不建议使用
    def get_queryset(self):
        return UserModel.objects.all()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in self.kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()  # user
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class GroupViewSet(ListModelMixin,
                   RetrieveModelMixin,
                   viewsets.GenericViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    @action(methods=['GET'], detail=True, url_path='users', url_name='users')
    def users(self, request, pk=None):
        group = self.get_object()
        serializer = GroupUserSerializer(group)
        return Response(serializer.data)
