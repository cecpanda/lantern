from django.db.models.signals import post_save
from django.dispatch import receiver

from tft.models import Order, OrderFlow


@receiver(post_save, sender=Order, dispatch_uid='order_status_handler')
def order_status_handler(sender, **kwargs):
    order = kwargs.get('instance')

    try:
        # flow = OrderFlow.objects.get_or_create(order=order, flow=order.status)
        flow = OrderFlow.objects.create(order=order, flow=order.status)
    except:
        pass
