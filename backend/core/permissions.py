# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Slinky Software

"""Custom permission classes for role-based access control."""

from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permission class that only allows admin users to access the view."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has profile and is admin
        if hasattr(request.user, 'profile'):
            return request.user.profile.role == 'admin'
        
        # Fallback: check is_staff for users without profile (during migration)
        return request.user.is_staff


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows:
    - Read access (GET, HEAD, OPTIONS) for all authenticated users
    - Write access (POST, PUT, PATCH, DELETE) only for admin users
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow read methods for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write methods require admin role
        if hasattr(request.user, 'profile'):
            return request.user.profile.role == 'admin'
        
        # Fallback: check is_staff for users without profile (during migration)
        return request.user.is_staff
