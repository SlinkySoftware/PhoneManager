# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Management command to create an admin user with proper role."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from getpass import getpass
import sys
import re

from core.models import UserProfile


class Command(BaseCommand):
    help = 'Create an admin user for the Phone Provisioning Manager'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            dest='username',
            help='Username for the admin account',
        )
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_true',
            dest='noinput',
            help='Do not prompt for any input (requires --username, will fail without password input)',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        noinput = options.get('noinput', False)

        # Prompt for username if not provided
        if not username:
            if noinput:
                raise CommandError('--username is required when --noinput is specified')
            
            username = input('Username: ').strip()
            
            if not username:
                raise CommandError('Username cannot be empty')
        
        # Validate username format (alphanumeric, underscore, hyphen, @, . only)
        if not re.match(r'^[a-zA-Z0-9_@.+-]+$', username):
            raise CommandError(
                'Username contains invalid characters. '
                'Only letters, numbers, @, ., +, -, and _ are allowed.'
            )

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User "{username}" already exists')

        # Prompt for password
        if noinput:
            raise CommandError('Cannot create user without password. Remove --noinput flag to provide password.')
        
        password = None
        while not password:
            password1 = getpass('Password: ')
            password2 = getpass('Password (again): ')
            
            if password1 != password2:
                self.stdout.write(self.style.ERROR('Passwords do not match. Please try again.'))
                continue
            
            if len(password1) < 8:
                self.stdout.write(self.style.ERROR('Password must be at least 8 characters. Please try again.'))
                continue
            
            password = password1

        # Optional: prompt for email
        email = ''
        if not noinput:
            email = input('Email address (optional): ').strip()

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                is_staff=True,  # Keep for Django admin compatibility
                is_superuser=True,  # Keep for Django admin compatibility
                is_active=True
            )

            # Create or update admin profile (in case profile was created by login before)
            _, _ = UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role': UserProfile.ROLE_ADMIN,
                    'is_sso': False,
                    'auth_source': UserProfile.AUTH_SOURCE_LOCAL,
                    'force_password_reset': False
                }
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {username}'))
            self.stdout.write(self.style.SUCCESS('Role: Administrator'))
            self.stdout.write(self.style.SUCCESS('You can now log in with this account.'))
            
        except Exception as e:
            raise CommandError(f'Error creating admin user: {e}')
