"""Faster password hasher for development only - reduces login from ~1.5s to ~50ms."""
from django.contrib.auth.hashers import PBKDF2PasswordHasher


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """PBKDF2 with fewer iterations. Use ONLY when DEBUG=True."""
    iterations = 2000  # vs 260000 default
