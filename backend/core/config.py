# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Configuration loader for Phone Provisioning Manager.

Loads configuration from config.yaml with environment variable overrides.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration loader with YAML file + environment variable override support."""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration loader.
        
        Args:
            config_path: Path to config.yaml file. Defaults to project root.
        """
        if config_path is None:
            # Default to project root (parent of backend/)
            base_dir = Path(__file__).resolve().parent.parent.parent
            config_path = base_dir / 'config.yaml'
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            print(f"Warning: Config file not found at {self.config_path}, using defaults")
            self._config = {}
    
    def get(self, key: str, default: Any = None, env_var: str = None) -> Any:
        """Get configuration value with environment variable override.
        
        Priority: environment variable > config.yaml > default
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found
            env_var: Environment variable name to check for override
        
        Returns:
            Configuration value
        """
        # Check environment variable first
        if env_var and env_var in os.environ:
            value = os.environ[env_var]
            # Try to parse booleans
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            return value
        
        # Navigate nested keys with dot notation
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value if value is not None else default
    
    def get_saml_settings(self) -> Dict[str, Any]:
        """Build python3-saml settings dict from configuration.
        
        Returns:
            Dictionary formatted for python3-saml library
        """
        # Get SP settings
        sp_entity_id = self.get('SAML_SP_ENTITY_ID', env_var='SAML_SP_ENTITY_ID')
        sp_acs_url = self.get('SAML_SP_ACS_URL', env_var='SAML_SP_ACS_URL')
        
        # Get IdP settings with env var overrides for sensitive data
        idp_entity_id = self.get('SAML_IDP_ENTITY_ID', env_var='SAML_IDP_ENTITY_ID')
        idp_sso_url = self.get('SAML_IDP_SSO_URL', env_var='SAML_IDP_SSO_URL')
        idp_slo_url = self.get('SAML_IDP_SLO_URL', env_var='SAML_IDP_SLO_URL')
        idp_x509_cert = self.get('SAML_IDP_X509_CERT', env_var='SAML_IDP_X509_CERT')
        
        # Get security settings
        security = self.get('SAML_SECURITY', default={})
        
        # Get contact/org info
        contact = self.get('SAML_CONTACT', default={})
        organization = self.get('SAML_ORGANIZATION', default={})
        
        # Build python3-saml compatible settings dict
        settings = {
            'strict': True,
            'debug': os.getenv('DJANGO_DEBUG', 'False').lower() == 'true',
            'sp': {
                'entityId': sp_entity_id,
                'assertionConsumerService': {
                    'url': sp_acs_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'singleLogoutService': {
                    'url': sp_acs_url,  # Reuse ACS URL for logout
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified',
            },
            'idp': {
                'entityId': idp_entity_id,
                'singleSignOnService': {
                    'url': idp_sso_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'singleLogoutService': {
                    'url': idp_slo_url or idp_sso_url,  # Fallback to SSO URL if SLO not provided
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'x509cert': idp_x509_cert,
            },
            'security': security,
        }
        
        # Add optional contact/org info if provided
        if contact:
            settings['contactPerson'] = contact
        if organization:
            settings['organization'] = organization
        
        return settings

    def get_auth_config(self) -> Dict[str, Any]:
        """Return frontend-facing authentication configuration."""
        ldap_enabled = self.get('LDAP_ENABLED', default=False, env_var='LDAP_ENABLED')
        sso_enabled = self.get('SSO_ENABLED', default=False, env_var='SSO_ENABLED')
        default_method = 'ldap' if ldap_enabled else 'local'
        return {
            'sso_enabled': sso_enabled,
            'ldap_enabled': ldap_enabled,
            'ldap_display_name': self.get(
                'LDAP_DISPLAY_NAME',
                default='Central Authentication',
                env_var='LDAP_DISPLAY_NAME',
            ),
            'default_password_auth_method': default_method,
        }


# Global config instance
config = Config()
