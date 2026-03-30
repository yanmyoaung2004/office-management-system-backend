"""Re-hash user passwords with the fast dev hasher. Run after enabling DEBUG fast hasher."""
from django.core.management.base import BaseCommand
from core.models import User

DEFAULT_PASSWORDS = {'admin': 'admin123', 'staff': 'staff123'}


class Command(BaseCommand):
    help = 'Re-hash passwords for dev (use fast hasher). Usage: fast_password admin staff'

    def add_arguments(self, parser):
        parser.add_argument('usernames', nargs='*', default=['admin', 'staff'])

    def handle(self, *args, **options):
        for username in options['usernames']:
            try:
                user = User.objects.get(username=username)
                pw = DEFAULT_PASSWORDS.get(username, 'password')
                user.set_password(pw)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'{username} password re-hashed (use {pw})'))
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'User {username} not found'))
