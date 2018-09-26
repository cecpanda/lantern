from django import template


register = template.Library()


@register.filter(name='get_remark')
def get_remark(item, key):
    return item[0].get(key)
