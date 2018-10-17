from django.db import models
from .order import Order


class OrderFlow(models.Model):
    order = models.ForeignKey(Order, related_name='flows', on_delete=models.CASCADE, verbose_name='订单')
    flow = models.IntegerField('状态代码')
    created = models.DateTimeField('添加时间', auto_now_add=True)

    class Meta:
        ordering = ('created',)
        verbose_name = '状态日志'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.order.id}: {self.flow}'
