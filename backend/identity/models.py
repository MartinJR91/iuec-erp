from __future__ import annotations

import uuid

from auditlog.registry import auditlog
from django.db import models


class CoreIdentity(models.Model):
    """CORE_IDENTITY - Identité unique d’un utilisateur de l’ERP."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "CORE_IDENTITY"

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name} <{self.email}>"


class RbacRoleDef(models.Model):
    """RBAC_ROLE_DEF - Définition des rôles et permissions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=dict)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "RBAC_ROLE_DEF"

    def __str__(self) -> str:
        return f"{self.code} - {self.label}"


class IdentityRoleLink(models.Model):
    """IDENTITY_ROLE_LINK - Association entre identités et rôles."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(
        CoreIdentity, on_delete=models.CASCADE, related_name="role_links"
    )
    role = models.ForeignKey(
        RbacRoleDef, on_delete=models.CASCADE, related_name="identity_links"
    )
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "IDENTITY_ROLE_LINK"
        unique_together = ("identity", "role")

    def __str__(self) -> str:
        return f"{self.identity.email} -> {self.role.code}"


class SysAuditLog(models.Model):
    """SYS_AUDIT_LOG - Journalisation applicative centralisée."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=128)
    entity_id = models.UUIDField()
    actor_email = models.EmailField(blank=True)
    active_role = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "SYS_AUDIT_LOG"

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id}"


auditlog.register(CoreIdentity)
auditlog.register(RbacRoleDef)
auditlog.register(IdentityRoleLink)
auditlog.register(SysAuditLog)
