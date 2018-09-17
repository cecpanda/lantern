from django.contrib import admin

from .models import Action


class ActionAdmin(admin.ModelAdmin):
    # list_display = ['user', 'verb', 'target_ct', 'target_id', 'created']
    list_display = ['user', 'verb', 'target', 'created']


admin.site.register(Action, ActionAdmin)
