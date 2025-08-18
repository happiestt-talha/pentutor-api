from django.apps import AppConfig

class CalendersyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calendersync'

    def ready(self):
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        from django.utils.timezone import now
        import json

        # schedule, created = IntervalSchedule.objects.get_or_create(
        #     every=5,  # every 5 minutes
        #     period=IntervalSchedule.MINUTES,
        # )

        # PeriodicTask.objects.update_or_create(
        #     name='Retry Failed Google Syncs',
        #     defaults={
        #         # 'interval': schedule,
        #         'task': 'calendersync.tasks.retry_failed_syncs',
        #         'start_time': now(),
        #         'enabled': True,
        #         'kwargs': json.dumps({}),
        #     }
        # )
