import xadmin

from .models import ID, Order, Audit, \
                    RecoverOrder, RecoverAudit, \
                    Report, Remark, \
                    Shortcut, ShortcutContent

#
# class EqKindAdmin(object):
#     list_display = ['name', 'group']
#     # list_filter = []
#     # search_fields = []
#
# class EqAdmin(object):
#     list_display = ['name', 'kind']


class OrderAdmin(object):
    list_display = ['id', 'status', 'next', 'user', 'defect_type', 'created']



class AuditAdmin(object):
    list_display = ['order', 'p_signer', 'c_signer', 'rejected']


class RecoverOrderAdmin(object):
    list_display = ['id', 'order', 'user', 'partial', 'created']


class RecoverAuditAdmin(object):
    list_display = ['recover_order', 'qc_signer', 'p_signer', 'rejected']


# xadmin.site.register(EqKind, EqKindAdmin)
# xadmin.site.register(Eq, EqAdmin)
#
# xadmin.site.register(Lot)

class ShortcutAdmin(object):
    list_display = ('name', )



class ShortcutContentAdmin(object):
    list_display = ('name', 'content')


xadmin.site.register(ID)
xadmin.site.register(Order, OrderAdmin)
xadmin.site.register(Audit, AuditAdmin)
xadmin.site.register(RecoverOrder, RecoverOrderAdmin)
xadmin.site.register(RecoverAudit, RecoverAuditAdmin)
xadmin.site.register(Report)
xadmin.site.register(Remark)
# xadmin.site.register(Shortcut, ShortcutAdmin)
xadmin.site.register(ShortcutContent, ShortcutContentAdmin)
