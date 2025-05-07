import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Clears all migrations and resets the migration history'

    def handle(self, *args, **kwargs):
        self.remove_db()
        # self.remove_medias()
        for app in self.get_installed_apps():
            self.clear_migrations(app)

    def remove_db(self):
        """
        Remove the db.sqlite3 file.
        """
        db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        if os.path.exists(db_path):
            os.remove(db_path)
            self.stdout.write(self.style.SUCCESS('Removed db.sqlite3'))
        else:
            self.stdout.write(self.style.WARNING('db.sqlite3 not found'))

    def remove_medias(self):
        """
        Remove all media files.
        """
        media_path = os.path.join(settings.BASE_DIR, 'medias')
        if os.path.exists(media_path):
            for root, dirs, files in os.walk(media_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
            self.stdout.write(self.style.SUCCESS('Removed media files'))
        else:
            self.stdout.write(self.style.WARNING('No media files found'))

    @staticmethod
    def get_installed_apps():
        """
        Get a list of all installed apps excluding default Django apps.
        """
        for app in settings.INSTALLED_APPS:
            if app.startswith('common.'):
                yield 'common'
            elif app.startswith('apps.'):
                yield app.split('.')[1]

    def clear_migrations(self, app):
        """
        Clear migration files for a given app.
        """
        migrations_path = self.get_migrations_path(app)

        if os.path.exists(migrations_path):
            self.remove_migration_files(migrations_path)
            self.stdout.write(self.style.SUCCESS(f'Cleared migrations for app: {app}'))
        else:
            self.stdout.write(self.style.WARNING(f'No migrations folder found for app: {app}'))

    @staticmethod
    def get_migrations_path(app):
        """
        Get the path to the migrations directory for a given app.
        """

        if app == 'common':
            return settings.BASE_DIR / app / 'migrations'
        return settings.BASE_DIR / 'apps' / app / 'migrations'

    def remove_migration_files(self, migrations_path):
        """
        Remove all migration files in the specified migrations directory, except __init__.py.
        """
        for root, dirs, files in os.walk(migrations_path):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    self.stdout.write(self.style.SUCCESS(f'Removed {file_path}'))
