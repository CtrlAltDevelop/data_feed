from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Seed the database with initial users'
    user = get_user_model()

    def handle(self, *args, **kwargs):
        """
        Seed the database with initial superuser.
        """
        superuser = self.user.objects.filter(username='admin')
        if not superuser.exists():
            self.user.objects.create_superuser(username='admin', email='admin@data_feed.com', password='1qaz!QAZ',
                                               first_name='Admin', last_name='User')
            self.stdout.write(self.style.SUCCESS('Superuser created'))
        else:
            self.stdout.write(self.style.WARNING('Superuser already exists'))