from django.contrib import admin

from .models import Shortcut, ShortcutContent


class ShortcutContentInline(admin.TabularInline):
    model = ShortcutContent
    extra = 3


class ShortcutAdmin(admin.ModelAdmin):
    inlines = [ShortcutContentInline]


admin.site.register(Shortcut, ShortcutAdmin)
# admin.site.register(ShortcutContent, ShortcutContentInline)
