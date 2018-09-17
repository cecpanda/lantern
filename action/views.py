from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework import status
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend

from .models import Action
from .serializers import ActionSerializer
from .utils import ActionPagination, ActionFilter


UserModel = get_user_model()


class ActionViewSet(ListModelMixin, GenericViewSet):
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    pagination_class = ActionPagination
    authentication_classes = [JSONWebTokenAuthentication, SessionAuthentication]
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_class = ActionFilter
    search_fields = ('$user__username', '$target_id')
    ordering_fields = ('created',)

    def get_permissions(self):
        if self.action == 'list':
            return [IsAuthenticated()]
        elif self.action == 'user':
            return []
        return [permission() for permission in self.permission_classes]

    def list(self, request, *args, **kwargs):
        user = request.user
        following = user.following.all()
        queryset = self.filter_queryset(self.get_queryset()).filter(Q(user=user)|Q(user__in=following))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='user', url_name='user')
    def user(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response({'detail': '请传入 username 参数'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(username=username)
        except:
            return Response(status=status.HTTP_404_NOT_FOUND)

        queryset = self.filter_queryset(self.get_queryset()).filter(user=user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
