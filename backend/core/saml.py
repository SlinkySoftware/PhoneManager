# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""SAML authentication handler for SSO integration.

Handles SAML assertion parsing, user provisioning, and role mapping.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from django.contrib.auth.models import User
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from .config import config
from .models import UserProfile

logger = logging.getLogger(__name__)


class SAMLAuthHandler:
    """Handles SAML authentication flow and user provisioning."""
    
    def __init__(self, request_data: Dict[str, Any]):
        """Initialize SAML auth handler with request data.
        
        Args:
            request_data: Django request data formatted for python3-saml
        """
        self.request_data = request_data
        self.saml_settings = config.get_saml_settings()
        self.auth = OneLogin_Saml2_Auth(request_data, self.saml_settings)
    
    def get_sso_url(self) -> str:
        """Get the IdP SSO URL to redirect user for authentication.
        
        Returns:
            SAML SSO redirect URL
        """
        return self.auth.login()
    
    def process_response(self) -> Tuple[Optional[User], Optional[str]]:
        """Process SAML response and authenticate/provision user.
        
        Returns:
            Tuple of (User object, error message)
            User is None if authentication failed
        """
        try:
            # Process the SAML response
            self.auth.process_response()
            errors = self.auth.get_errors()
            
            if errors:
                error_reason = self.auth.get_last_error_reason()
                logger.error(f"SAML authentication error: {errors}, reason: {error_reason}")
                return None, f"SAML authentication failed: {error_reason}"
            
            if not self.auth.is_authenticated():
                return None, "SAML authentication failed: User not authenticated"
            
            # Extract user attributes from SAML assertion
            attributes = self.auth.get_attributes()
            name_id = self.auth.get_nameid()
            
            logger.info(f"SAML login successful for: {name_id}")
            logger.debug(f"SAML attributes: {attributes}")
            
            # Validate required claims
            if not self._validate_user_claim(attributes):
                return None, "Access denied: Required group membership not found"
            
            # Determine user role from claims
            role = self._determine_role(attributes)
            
            # Provision or update user
            user = self._provision_user(name_id, attributes, role)
            
            return user, None
            
        except Exception as e:
            logger.exception(f"Error processing SAML response: {e}")
            return None, f"SAML processing error: {str(e)}"
    
    def _validate_user_claim(self, attributes: Dict[str, list]) -> bool:
        """Validate that user has required claim for application access.
        
        Args:
            attributes: SAML assertion attributes
        
        Returns:
            True if user has required claim, False otherwise
        """
        user_claim = config.get('USER_CLAIM', default='groups')
        user_claim_value = config.get('USER_CLAIM_VALUE', default='PhoneManager_Users')
        
        if not user_claim or not user_claim_value:
            # If no claim configured, allow access
            logger.warning("No USER_CLAIM configured, allowing all SAML users")
            return True
        
        # Get claim values from attributes
        claim_values = attributes.get(user_claim, [])
        
        # Check if required value is present
        return user_claim_value in claim_values
    
    def _determine_role(self, attributes: Dict[str, list]) -> str:
        """Determine user role based on SAML claims.
        
        Args:
            attributes: SAML assertion attributes
        
        Returns:
            Role string ('admin' or 'readonly')
        """
        admin_claim = config.get('ADMIN_CLAIM', default='groups')
        admin_claim_value = config.get('ADMIN_CLAIM_VALUE', default='PhoneManager_Admins')
        
        if not admin_claim or not admin_claim_value:
            # If no admin claim configured, default to readonly
            return UserProfile.ROLE_READONLY
        
        # Get claim values from attributes
        claim_values = attributes.get(admin_claim, [])
        
        # Check if admin value is present
        if admin_claim_value in claim_values:
            return UserProfile.ROLE_ADMIN
        
        return UserProfile.ROLE_READONLY
    
    def _provision_user(self, name_id: str, attributes: Dict[str, list], role: str) -> User:
        """Create or update user account from SAML data.
        
        Args:
            name_id: SAML NameID (typically username or email)
            attributes: SAML assertion attributes
            role: Determined user role
        
        Returns:
            User object
        """
        # Extract username from NameID (handle email format)
        username = name_id.split('@')[0] if '@' in name_id else name_id
        username = username[:150]  # Django username max length
        
        # Extract optional attributes
        email = self._get_attribute(attributes, 'email', name_id if '@' in name_id else '')
        first_name = self._get_attribute(attributes, 'firstName', '')[:30]
        last_name = self._get_attribute(attributes, 'lastName', '')[:150]
        
        # Get or create user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True,
            }
        )
        
        # Update user info if changed
        if not created:
            updated = False
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
        
        # Get or create user profile
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': role,
                'is_sso': True,
                'auth_source': UserProfile.AUTH_SOURCE_SAML,
                'force_password_reset': False,
            }
        )
        
        # Update profile if role changed
        if not profile_created:
            updated = False
            if profile.role != role:
                logger.info(f"Updating role for {username}: {profile.role} -> {role}")
                profile.role = role
                updated = True
            if profile.auth_source != UserProfile.AUTH_SOURCE_SAML:
                profile.auth_source = UserProfile.AUTH_SOURCE_SAML
                updated = True
            if not profile.is_sso:
                profile.is_sso = True
                updated = True
            if updated:
                profile.save()
        
        logger.info(f"Provisioned SSO user: {username} with role: {role}")
        
        return user
    
    def _get_attribute(self, attributes: Dict[str, list], key: str, default: str = '') -> str:
        """Safely extract attribute value from SAML attributes.
        
        Args:
            attributes: SAML assertion attributes
            key: Attribute key
            default: Default value if not found
        
        Returns:
            Attribute value or default
        """
        values = attributes.get(key, [])
        return values[0] if values else default
    
    def get_metadata(self) -> str:
        """Generate SP metadata XML for IdP configuration.
        
        Returns:
            XML metadata string
        """
        metadata = self.auth.get_settings().get_sp_metadata()
        errors = self.auth.get_settings().validate_metadata(metadata)
        
        if errors:
            logger.error(f"Metadata validation errors: {errors}")
            raise Exception(f"Invalid metadata: {errors}")
        
        return metadata


def prepare_django_request(request) -> Dict[str, Any]:
    """Convert Django request to format expected by python3-saml.
    
    Args:
        request: Django HttpRequest object
    
    Returns:
        Request data dict for python3-saml
    """
    # Build request data dict for python3-saml
    request_data = {
        'https': 'on' if request.is_secure() else 'off',
        'http_host': request.META.get('HTTP_HOST', 'localhost'),
        'script_name': request.META.get('SCRIPT_NAME', ''),
        'server_port': request.META.get('SERVER_PORT', '80'),
        'get_data': request.GET.copy(),
        'post_data': request.POST.copy(),
    }
    
    return request_data
