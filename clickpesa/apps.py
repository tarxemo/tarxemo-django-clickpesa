from django.apps import AppConfig


class BhumwiPaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clickpesa'
    verbose_name = 'ClickPesa Payments'

    def ready(self):
        """
        Import signals or perform app initialization here if needed.
        """
        pass
