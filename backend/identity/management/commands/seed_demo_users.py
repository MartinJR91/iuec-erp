from __future__ import annotations

from typing import Iterable

from django.core.management.base import BaseCommand

from identity.seed import DEMO_USERS, seed_demo_users


class Command(BaseCommand):
    help = "Crée des utilisateurs démo et leurs rôles."

    def handle(self, *args, **options) -> None:
        seed_demo_users()

        self.stdout.write(self.style.SUCCESS("Utilisateurs démo créés."))
        self.stdout.write("Credentials:")
        for user in DEMO_USERS:
            self.stdout.write(
                f"- {user['username']} / {user['email']} / {user['password']}"
            )
