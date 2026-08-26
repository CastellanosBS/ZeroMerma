from __future__ import annotations


class SettingAdminError(Exception):
    """Base error for admin configuration operations."""


class SettingNotFoundError(SettingAdminError):
    """Raised when a setting key is not registered."""


class SettingReadonlyError(SettingAdminError):
    """Raised when a read-only setting is changed."""


class SettingValidationError(SettingAdminError):
    """Raised when a setting value does not pass validation."""


class SettingSensitiveConfirmationError(SettingAdminError):
    """Raised when a sensitive setting change is not confirmed."""
