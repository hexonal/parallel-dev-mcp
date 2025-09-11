#!/usr/bin/env python3
"""
Backward Compatibility Wrapper for Tmux Session Orchestrator

This file maintains backward compatibility with existing imports.
The actual implementation has been refactored into a clean modular structure.

DEPRECATED: Import from src.mcp_tools.tmux instead
"""

# Backward compatibility imports
from .tmux import tmux_session_orchestrator, TmuxSessionManager

# Re-export for backward compatibility
__all__ = ["tmux_session_orchestrator", "TmuxSessionManager"]