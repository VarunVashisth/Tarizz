"""Compatibility wrapper — MVP uses SimpleAuthManager."""

from backend.auth_manager_simple import SimpleAuthManager as AuthManager

__all__ = ["AuthManager"]
