from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter

from .views import StartOrderViewSet, AuditViewSet, RecoverOrderViewSet, RecoverAuditViewSet, \
                   RemarkViewSet, ShortcutViewSet, \
                   OrderViewSet


router = DefaultRouter()
router.register('order/start', StartOrderViewSet, base_name='start')
router.register('order/audit', AuditViewSet, base_name='audit')
router.register('order/recover', RecoverOrderViewSet, base_name='recover')
router.register('order/recover-audit', RecoverAuditViewSet, base_name='recover-audit')
router.register('order/remark', RemarkViewSet, base_name='remark')
router.register('order/query', OrderViewSet, base_name='order')
router.register('order/shortcut', ShortcutViewSet, base_name='shortcut')

app_name = 'tft'

urlpatterns = [
    path('', include(router.urls)),
]