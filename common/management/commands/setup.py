from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'setup the application'

    works = [
        ('clearmigrations', 'Cleaning...'),
        ('makemigrations', 'Making migrations...'),
        ('migrate', 'Applying migrations...'),
        ('seed_superuser', 'Create Superuser...'),
    ]

    def handle(self, *args, **options):
        job_count = len(self.works)
        self.stdout.write(self.style.SUCCESS(f'Setting up for {job_count} job...'))

        for index, (command, message) in enumerate(self.works):
            self.stdout.write(self.style.NOTICE(f'({index}/{job_count}) - {message}'))
            call_command(command)

        self.stdout.write(self.style.SUCCESS('Setup completed successfully'))
