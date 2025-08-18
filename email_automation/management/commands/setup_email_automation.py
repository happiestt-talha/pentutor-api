from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from email_automation.services import EmailTemplateService
from email_automation.models import EmailPreference

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize email automation system with default templates and user preferences'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-preferences',
            action='store_true',
            help='Create email preferences for existing users',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up email automation system...'))
        
        # Create default email templates
        self.stdout.write('Creating default email templates...')
        EmailTemplateService.create_default_templates()
        self.stdout.write(self.style.SUCCESS('✓ Email templates created'))
        
        # Create email preferences for existing users if requested
        if options['create_preferences']:
            self.stdout.write('Creating email preferences for existing users...')
            users_without_preferences = User.objects.filter(
                emailpreference__isnull=True
            )
            
            created_count = 0
            for user in users_without_preferences:
                EmailPreference.objects.get_or_create(user=user)
                created_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created email preferences for {created_count} users'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                'Email automation system setup completed successfully!'
            )
        )
        
        # Display next steps
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Configure email settings in settings.py')
        self.stdout.write('2. Set up Celery worker and beat scheduler')
        self.stdout.write('3. Run migrations: python manage.py migrate')
        self.stdout.write('4. Start Celery worker: celery -A lms worker -l info')
        self.stdout.write('5. Start Celery beat: celery -A lms beat -l info')