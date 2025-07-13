from .enhanced_client import EnhancedTogglClient, TogglAPIError, MemberTimeTotal

# Alias for compatibility
TogglClient = EnhancedTogglClient

__all__ = ["EnhancedTogglClient", "TogglClient", "MemberTimeTotal", "TogglAPIError"]
