# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""LDAP authentication handler.

Implements a three-stage LDAP authentication flow:
1. Bind with a service account.
2. Search for the user, retrieve the distinguished name and group membership,
   and determine the application role.
3. Bind as the user to verify the submitted password.
"""

from __future__ import annotations

import logging
import ssl
import json
from dataclasses import dataclass
from typing import Any

import yaml

from django.contrib.auth.models import User
from ldap3 import ALL, SUBTREE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPBindError, LDAPException
from ldap3.utils.conv import escape_filter_chars

from .config import config
from .models import UserProfile

logger = logging.getLogger(__name__)


class LDAPConfigurationError(Exception):
    """Raised when LDAP configuration is missing or invalid."""


class LDAPAuthenticationError(Exception):
    """Raised when LDAP authentication fails."""


@dataclass
class LDAPAuthenticationResult:
    """Normalized result from a successful LDAP authentication."""

    user: User
    profile: UserProfile
    dn: str
    groups: list[str]
    attributes: dict[str, Any]


class LDAPAuthHandler:
    """Handle LDAP authentication and user provisioning."""

    ATTRIBUTE_EMAIL = "mail"
    ATTRIBUTE_FIRST_NAME = "givenName"
    ATTRIBUTE_LAST_NAME = "sn"

    def __init__(self):
        self.settings = self._load_settings()

    def authenticate_user(self, username: str, password: str) -> LDAPAuthenticationResult:
        """Authenticate a user against LDAP and provision/update the local account."""
        if not username or not password:
            raise LDAPAuthenticationError("Username and password required")

        server = self._build_server()
        service_connection = self._bind_service_account(server)
        try:
            formatted_username = self._format_username(username)
            user_record = self._lookup_user(service_connection, username, formatted_username)
            groups = user_record["groups"]
            user_dn = user_record["dn"]

            self._bind_as_user(server, user_dn, password)

            if not self._has_required_group(groups):
                raise LDAPAuthenticationError("You are not authorised to access this application")

            role = self._determine_role(groups)
            user, profile = self._provision_user(username, user_record["attributes"], role)
            logger.info("LDAP login successful for %s", user.username)
            return LDAPAuthenticationResult(
                user=user,
                profile=profile,
                dn=user_dn,
                groups=groups,
                attributes=user_record["attributes"],
            )
        finally:
            service_connection.unbind()

    def _load_settings(self) -> dict[str, Any]:
        """Load and validate LDAP settings from config.yaml."""
        settings = {
            "enabled": config.get("LDAP_ENABLED", default=False, env_var="LDAP_ENABLED"),
            "display_name": config.get("LDAP_DISPLAY_NAME", default="Central Authentication", env_var="LDAP_DISPLAY_NAME"),
            "debug_logging": self._to_bool(
                config.get("LDAP_DEBUG_LOGGING", default=False, env_var="LDAP_DEBUG_LOGGING")
            ),
            "server": config.get("LDAP_SERVER_NAME", default="", env_var="LDAP_SERVER_NAME"),
            "port": self._to_int(config.get("LDAP_PORT", default=389, env_var="LDAP_PORT"), 389),
            "encryption": str(config.get("LDAP_ENCRYPTION", default="none", env_var="LDAP_ENCRYPTION")).lower(),
            "validate_certificates": self._to_bool(
                config.get("LDAP_VALIDATE_CERTIFICATES", default=True, env_var="LDAP_VALIDATE_CERTIFICATES")
            ),
            "bind_dn": config.get("LDAP_BIND_DN", default="", env_var="LDAP_BIND_DN"),
            "bind_password": config.get("LDAP_BIND_PASSWORD", default="", env_var="LDAP_BIND_PASSWORD"),
            "domain_name": config.get("LDAP_DOMAIN_NAME", default="", env_var="LDAP_DOMAIN_NAME"),
            "username_format": config.get("LDAP_USERNAME_FORMAT", default="%u", env_var="LDAP_USERNAME_FORMAT"),
            "group_attribute": config.get("LDAP_GROUP_ATTRIBUTE", default="memberOf", env_var="LDAP_GROUP_ATTRIBUTE"),
            "admin_group_mapping": self._normalize_mapping(
                config.get("LDAP_ADMIN_GROUP_MAPPING", default=[], env_var="LDAP_ADMIN_GROUP_MAPPING")
            ),
            "user_group_mapping": self._normalize_mapping(
                config.get("LDAP_USER_GROUP_MAPPING", default=[], env_var="LDAP_USER_GROUP_MAPPING")
            ),
            "base_dn": config.get("LDAP_BASE_DN", default="", env_var="LDAP_BASE_DN"),
            "search_filter": config.get(
                "LDAP_SEARCH_FILTER",
                default="(|(userPrincipalName=%u)(sAMAccountName=%r)(uid=%r)(cn=%r))",
                env_var="LDAP_SEARCH_FILTER",
            ),
        }

        if not settings["enabled"]:
            raise LDAPConfigurationError("LDAP authentication is not enabled")

        required_keys = ["server", "bind_dn", "bind_password", "base_dn", "search_filter"]
        missing_keys = [key for key in required_keys if not settings[key]]
        if missing_keys:
            raise LDAPConfigurationError(
                f"Missing LDAP configuration values: {', '.join(sorted(missing_keys))}"
            )

        if settings["encryption"] not in {"none", "ssl", "starttls"}:
            raise LDAPConfigurationError("LDAP_ENCRYPTION must be one of: none, ssl, starttls")

        return settings

    def _build_server(self) -> Server:
        """Construct the LDAP server object with TLS settings."""
        tls = None
        if self.settings["encryption"] in {"ssl", "starttls"}:
            validate = ssl.CERT_REQUIRED if self.settings["validate_certificates"] else ssl.CERT_NONE
            tls = Tls(validate=validate)

        self._debug_log(
            "LDAP connection attempt server=%s port=%s encryption=%s validate_certificates=%s",
            self.settings["server"],
            self.settings["port"],
            self.settings["encryption"],
            self.settings["validate_certificates"],
        )

        return Server(
            self.settings["server"],
            port=self.settings["port"],
            use_ssl=self.settings["encryption"] == "ssl",
            tls=tls,
            get_info=ALL,
        )

    def _bind_service_account(self, server: Server) -> Connection:
        """Bind to LDAP using the configured service account."""
        try:
            self._debug_log("LDAP bind attempt bind_dn=%s", self.settings["bind_dn"])
            connection = Connection(
                server,
                user=self.settings["bind_dn"],
                password=self.settings["bind_password"],
                auto_bind=True,
                raise_exceptions=True,
            )
            if self.settings["encryption"] == "starttls":
                connection.start_tls()
            self._debug_log("LDAP bind succeeded bind_dn=%s", self.settings["bind_dn"])
            return connection
        except LDAPException as exc:
            logger.exception("LDAP service account bind failed: %s", exc)
            raise LDAPConfigurationError("LDAP service account bind failed") from exc

    def _lookup_user(self, connection: Connection, username: str, formatted_username: str) -> dict[str, Any]:
        """Search for the user entry and return normalized attributes."""
        search_filter = self._render_search_filter(username, formatted_username)
        attributes = [
            "distinguishedName",
            self.ATTRIBUTE_EMAIL,
            self.ATTRIBUTE_FIRST_NAME,
            self.ATTRIBUTE_LAST_NAME,
            self.settings["group_attribute"],
        ]
        self._debug_log(
            "LDAP search request username=%s formatted_username=%s base_dn=%s filter=%s attributes=%s",
            username,
            formatted_username,
            self.settings["base_dn"],
            search_filter,
            attributes,
        )
        connection.search(
            search_base=self.settings["base_dn"],
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes,
            size_limit=2,
        )

        self._debug_log(
            "LDAP search result username=%s entry_count=%s entry_dns=%s",
            username,
            len(connection.entries),
            [entry.entry_dn for entry in connection.entries],
        )

        if not connection.entries:
            raise LDAPAuthenticationError("Invalid username or password")
        if len(connection.entries) > 1:
            raise LDAPAuthenticationError("LDAP search returned multiple users; refine LDAP_SEARCH_FILTER")

        entry = connection.entries[0]
        group_attribute = self.settings["group_attribute"]
        raw_groups = entry[group_attribute].values if group_attribute in entry else []
        normalized_attributes = {
            self.ATTRIBUTE_EMAIL: self._first_value(entry, self.ATTRIBUTE_EMAIL),
            self.ATTRIBUTE_FIRST_NAME: self._first_value(entry, self.ATTRIBUTE_FIRST_NAME),
            self.ATTRIBUTE_LAST_NAME: self._first_value(entry, self.ATTRIBUTE_LAST_NAME),
        }
        groups = [str(value) for value in raw_groups if value]

        self._debug_log(
            "LDAP search result user_dn=%s groups=%s attributes=%s",
            entry.entry_dn,
            groups,
            normalized_attributes,
        )

        return {
            "dn": entry.entry_dn,
            "groups": groups,
            "attributes": normalized_attributes,
        }

    def _bind_as_user(self, server: Server, user_dn: str, password: str) -> None:
        """Bind as the resolved user to validate the submitted password."""
        try:
            self._debug_log("LDAP bind attempt user_dn=%s", user_dn)
            connection = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=True,
            )
            if self.settings["encryption"] == "starttls":
                connection.start_tls()
            connection.unbind()
            self._debug_log("LDAP bind succeeded user_dn=%s", user_dn)
        except LDAPBindError as exc:
            raise LDAPAuthenticationError("Password Incorrect") from exc
        except LDAPException as exc:
            logger.exception("LDAP user bind failed for %s: %s", user_dn, exc)
            raise LDAPAuthenticationError("LDAP authentication failed") from exc

    def _provision_user(self, username: str, attributes: dict[str, Any], role: str) -> tuple[User, UserProfile]:
        """Create or update a local user record for the LDAP-authenticated user."""
        normalized_username = username[:150]
        email = str(attributes.get(self.ATTRIBUTE_EMAIL, ""))[:254]
        first_name = str(attributes.get(self.ATTRIBUTE_FIRST_NAME, ""))[:150]
        last_name = str(attributes.get(self.ATTRIBUTE_LAST_NAME, ""))[:150]

        user, created = User.objects.get_or_create(
            username=normalized_username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
            },
        )

        updated = False
        if not created:
            if user.email != email:
                user.email = email
                updated = True
            if user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if not user.is_active:
                user.is_active = True
                updated = True
            if updated:
                user.save()

        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": role,
                "is_sso": False,
                "auth_source": UserProfile.AUTH_SOURCE_LDAP,
                "force_password_reset": False,
            },
        )
        if not profile_created:
            profile_updated = False
            if profile.role != role:
                profile.role = role
                profile_updated = True
            if profile.auth_source != UserProfile.AUTH_SOURCE_LDAP:
                profile.auth_source = UserProfile.AUTH_SOURCE_LDAP
                profile_updated = True
            if profile.is_sso:
                profile.is_sso = False
                profile_updated = True
            if profile.force_password_reset:
                profile.force_password_reset = False
                profile_updated = True
            if profile_updated:
                profile.save()

        logger.info("Provisioned LDAP user: %s with role: %s", normalized_username, role)
        return user, profile

    def _format_username(self, username: str) -> str:
        """Apply the configured username template to the entered username."""
        return self.settings["username_format"].replace("%u", username)

    def _render_search_filter(self, username: str, formatted_username: str) -> str:
        """Render the LDAP search filter with escaped values."""
        return (
            self.settings["search_filter"]
            .replace("%u", escape_filter_chars(formatted_username))
            .replace("%r", escape_filter_chars(username))
        )

    def _has_required_group(self, groups: list[str]) -> bool:
        """Return True when the user matches at least one configured access group."""
        required_groups = self.settings["user_group_mapping"]
        if not required_groups:
            logger.warning("LDAP_USER_GROUP_MAPPING is empty; allowing all LDAP users")
            self._debug_log(
                "LDAP group match result access_allowed=True reason=no LDAP_USER_GROUP_MAPPING configured groups=%s",
                groups,
            )
            return True

        access_allowed = self._matches_any_group(groups, required_groups)
        self._debug_log(
            "LDAP group match result access_allowed=%s required_groups=%s groups=%s",
            access_allowed,
            required_groups,
            groups,
        )
        return access_allowed

    def _determine_role(self, groups: list[str]) -> str:
        """Map LDAP groups to application roles."""
        admin_groups = self.settings["admin_group_mapping"]
        admin_match = bool(admin_groups and self._matches_any_group(groups, admin_groups))
        role = UserProfile.ROLE_ADMIN if admin_match else UserProfile.ROLE_READONLY
        self._debug_log(
            "LDAP group match result admin_match=%s admin_groups=%s groups=%s assigned_role=%s",
            admin_match,
            admin_groups,
            groups,
            role,
        )
        return role

    def _matches_any_group(self, groups: list[str], configured_groups: list[str]) -> bool:
        """Match LDAP group DNs or names case-insensitively."""
        configured = {value.casefold() for value in configured_groups if value}
        for group in groups:
            candidates = {group.casefold()}
            if "," in group:
                first_component = group.split(",", 1)[0]
                if "=" in first_component:
                    candidates.add(first_component.split("=", 1)[1].casefold())
            if candidates & configured:
                return True
        return False

    def _first_value(self, entry: Any, attribute_name: str) -> str:
        """Return the first attribute value from an LDAP entry."""
        if attribute_name not in entry:
            return ""
        values = entry[attribute_name].values
        return str(values[0]) if values else ""

    def _normalize_mapping(self, value: Any) -> list[str]:
        """Normalize configured group mapping values into a list of strings."""
        if isinstance(value, list):
            return self._clean_mapping_items(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []

            parsed = self._parse_mapping_sequence(text)
            if parsed is not None:
                return parsed

            return [item.strip() for item in text.split(",") if item.strip()]
        return []

    def _parse_mapping_sequence(self, value: str) -> list[str] | None:
        """Parse JSON/YAML list syntax from a string value when present."""
        if not value.startswith("["):
            return None

        for parser in (json.loads, yaml.safe_load):
            try:
                parsed = parser(value)
            except (TypeError, ValueError, yaml.YAMLError):
                continue
            if isinstance(parsed, list):
                return self._clean_mapping_items(parsed)

        return None

    def _clean_mapping_items(self, values: list[Any]) -> list[str]:
        """Strip whitespace and drop empty mapping entries."""
        return [str(item).strip() for item in values if str(item).strip()]

    def _to_bool(self, value: Any) -> bool:
        """Normalize bool-like config values."""
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _to_int(self, value: Any, default: int) -> int:
        """Normalize integer-like config values."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _debug_log(self, message: str, *args: Any) -> None:
        """Emit LDAP diagnostic logs when LDAP_DEBUG_LOGGING is enabled."""
        if self.settings.get("debug_logging"):
            logger.info(message, *args)
        