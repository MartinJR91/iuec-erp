from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CoreIdentity",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("email", models.EmailField(unique=True, max_length=254)),
                ("phone", models.CharField(max_length=32, unique=True)),
                ("first_name", models.CharField(max_length=150)),
                ("last_name", models.CharField(max_length=150)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "CORE_IDENTITY"},
        ),
        migrations.CreateModel(
            name="RbacRoleDef",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("code", models.CharField(max_length=64, unique=True)),
                ("label", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("permissions", models.JSONField(default=dict)),
                ("is_system", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "RBAC_ROLE_DEF"},
        ),
        migrations.CreateModel(
            name="SysAuditLog",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("action", models.CharField(max_length=64)),
                ("entity_type", models.CharField(max_length=128)),
                ("entity_id", models.UUIDField()),
                ("actor_email", models.EmailField(blank=True, max_length=254)),
                ("active_role", models.CharField(blank=True, max_length=64)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("payload", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "SYS_AUDIT_LOG"},
        ),
        migrations.CreateModel(
            name="IdentityRoleLink",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("is_active", models.BooleanField(default=True)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("assigned_by", models.CharField(blank=True, max_length=150)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("identity", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="role_links", to="core_identity.coreidentity")),
                ("role", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="identity_links", to="core_identity.rbacroledef")),
            ],
            options={"db_table": "IDENTITY_ROLE_LINK", "unique_together": {("identity", "role")}},
        ),
    ]
