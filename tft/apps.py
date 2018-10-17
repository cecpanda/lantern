from django.apps import AppConfig


class TftConfig(AppConfig):
    name = 'tft'
    verbose_name = '阵列制造'

    def ready(self):
        import tft.signals.handlers
