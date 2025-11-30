"""Session storage utilities for authentication."""

import os
import json
import stat
from pathlib import Path
from typing import Optional, Dict, Any

SESSION_PATH = Path.home() / ".macolint" / "session.json"


def ensure_session_dir():
    """Ensure the session directory exists with proper permissions."""
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)


def save_session(data: Dict[str, Any]) -> None:
    """
    Save session data to a secure file.
    
    Args:
        data: Dictionary containing session information (access_token, user, etc.)
    
    Raises:
        IOError: If file cannot be written
    """
    ensure_session_dir()
    SESSION_PATH.write_text(json.dumps(data, indent=2))
    # Set file permissions to 600 (read/write for owner only)
    os.chmod(SESSION_PATH, stat.S_IRUSR | stat.S_IWUSR)


def load_session() -> Optional[Dict[str, Any]]:
    """
    Load session data from file.
    
    Returns:
        Session dictionary if file exists and is valid, None otherwise
    """
    if not SESSION_PATH.exists():
        return None
    
    try:
        content = SESSION_PATH.read_text()
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        # Invalid JSON or read error - treat as no session
        return None


def delete_session() -> None:
    """
    Delete the session file.
    
    Raises:
        IOError: If file cannot be deleted
    """
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()

