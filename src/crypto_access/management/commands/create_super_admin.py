"""
Management command: create_super_admin

Creates a Django superuser along with a UserProfile that has
user_type='super_admin' (and user_type_ref linked to the UserType
with code='super_admin', if it exists).

Usage:
    python manage.py create_super_admin
"""

import getpass

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create a superuser with user_type='super_admin' (interactive)."

    def add_arguments(self, parser):
        # Allow passing these in directly to skip some prompts,
        # but by default everything is asked interactively.
        parser.add_argument("--username", default=None, help="Username for the super admin")
        parser.add_argument("--email", default=None, help="Email for the super admin")

    def handle(self, *args, **options):
        username = options.get("username") or self._prompt_username()
        email = options.get("email") or self._prompt_email()
        password = self._prompt_password()

        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                )

                # Imported locally to avoid circular imports during app startup
                from crypto_access.models import UserProfile, UserType

                super_admin_type = UserType.objects.filter(code="super_admin").first()
                if super_admin_type is None:
                    self.stdout.write(
                        self.style.WARNING(
                            "[!] No UserType found with code='super_admin'. "
                            "UserProfile will fall back to the legacy user_type field only."
                        )
                    )

                full_name = self._prompt_full_name(default=username)

                UserProfile.objects.create(
                    user=user,
                    full_name=full_name,
                    user_type="super_admin",
                    user_type_ref=super_admin_type,
                )
        except Exception as exc:
            raise CommandError(f"Failed to create super admin: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(f"\n[OK] Super admin '{username}' created successfully.")
        )

    # ---- Prompt helpers -------------------------------------------------

    def _prompt_username(self) -> str:
        while True:
            username = input("Username: ").strip()
            if not username:
                self.stderr.write("Username cannot be empty.")
                continue
            if User.objects.filter(username=username).exists():
                self.stderr.write(f"User '{username}' already exists. Please choose another name.")
                continue
            return username

    def _prompt_email(self) -> str:
        while True:
            email = input("Email: ").strip()
            if not email:
                self.stderr.write("Email cannot be empty.")
                continue
            return email

    def _prompt_full_name(self, default: str) -> str:
        full_name = input(f"Full name [{default}]: ").strip()
        return full_name or default

    def _prompt_password(self) -> str:
        while True:
            password = getpass.getpass("Password: ")
            password_confirm = getpass.getpass("Password (confirm): ")

            if password != password_confirm:
                self.stderr.write("Passwords do not match. Please try again.\n")
                continue

            try:
                validate_password(password)
            except ValidationError as exc:
                for err in exc.messages:
                    self.stderr.write(f"  - {err}")
                self.stderr.write("Please re-enter the password.\n")
                continue

            return password