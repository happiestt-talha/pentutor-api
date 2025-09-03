from django.apps import AppConfig


class IndividualLiveClassConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'individual_live_class'
    verbose_name = 'Live Classes'
    
    def ready(self):
        import individual_live_class.signals
