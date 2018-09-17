from django.contrib import admin

from .models import User, GroupSetting, Follow


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'realname', 'is_staff', 'is_superuser')
    list_filter = ('username', 'realname')
    search_fields = ('username', 'realname')
    date_hierarchy = 'date_joined'
    fieldsets = [
        ('用户信息', {'fields': ['username', 'password', 'realname', 'email',
                                'phone', 'mobile', 'avatar', 'gender', 'date_joined',
                                'is_staff', 'is_superuser', 'is_active']}),
        ('组和权限', {'fields': ['groups', 'user_permissions']}),
        ('废弃', {'fields': ['last_login', 'first_name', 'last_name'], 'classes': ['collapse']}),
    ]

admin.site.register(User, UserAdmin)
admin.site.register(GroupSetting)
admin.site.register(Follow)
