from django.apps import AppConfig


class EmailAutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'email_automation'

    def ready(self):
        import email_automation.signals
