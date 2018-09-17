import xadmin

from .models import Action


class ActionAdmin(object):
    # list_display = ['user', 'verb', 'target_ct', 'target_id', 'created']
    list_display = ['user', 'verb', 'created']


xadmin.site.register(Action, ActionAdmin)
