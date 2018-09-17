from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, GroupViewSet, FollowViewSet



app_name = 'account'

router = DefaultRouter()
router.register('user', UserViewSet, base_name='user')
router.register('group', GroupViewSet, base_name='group')
router.register('follow', FollowViewSet, base_name='follow')


urlpatterns = [
    path('', include(router.urls))
]
