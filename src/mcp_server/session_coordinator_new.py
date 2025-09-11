#!/usr/bin/env python3
"""
Backward Compatibility Wrapper for Session Coordinator

This file maintains backward compatibility with existing imports.
The actual implementation has been refactored into a clean modular structure.

DEPRECATED: Import from src.mcp_server.coordinator instead
"""

# Backward compatibility imports
from .coordinator import SessionCoordinatorMCP, SessionRegistry, MessageHandler, TmuxIntegration, StatusMonitor

# Re-export the global instance for backward compatibility
from .coordinator.mcp_coordinator import session_coordinator

# Re-export all classes for backward compatibility
__all__ = [
    "SessionCoordinatorMCP", 
    "SessionRegistry", 
    "MessageHandler", 
    "TmuxIntegration", 
    "StatusMonitor",
    "session_coordinator"
]