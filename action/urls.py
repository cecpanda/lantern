from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ActionViewSet


router = DefaultRouter()
router.register('', ActionViewSet, base_name='action')


app_name = 'action'
urlpatterns = [
    path('', include(router.urls)),
]