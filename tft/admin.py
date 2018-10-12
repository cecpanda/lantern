from django.contrib import admin

from .models import ID, Order, Audit, \
                    RecoverOrder, RecoverAudit, \
                    Report, Remark, \
                    Shortcut, ShortcutContent



class OrderAdmin(admin.ModelAdmin):
    pass


class ShortcutContentInline(admin.TabularInline):
    model = ShortcutContent
    extra = 3


class ShortcutAdmin(admin.ModelAdmin):
    inlines = [ShortcutContentInline]


admin.site.register(ID)
admin.site.register(Order, OrderAdmin)
admin.site.register(Shortcut, ShortcutAdmin)
# admin.site.register(ShortcutContent, ShortcutContentInline)
