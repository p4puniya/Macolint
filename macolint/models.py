"""Data models for Macolint."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Snippet:
    """Represents a code snippet."""
    id: int
    name: str
    content: str
    is_shared: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: tuple, content: str, is_shared: bool = False) -> "Snippet":
        """Create a Snippet from a database row."""
        # Handle both old format (5 columns) and new format (6+ columns with is_shared)
        if len(row) >= 6:
            # New format: id, name, content_encrypted, is_shared, created_at, updated_at
            # Or: id, name, module_id, content_encrypted, is_shared, created_at, updated_at
            # Find created_at and updated_at positions
            created_idx = len(row) - 2
            updated_idx = len(row) - 1
            is_shared_idx = created_idx - 1
            return cls(
                id=row[0],
                name=row[1],
                content=content,
                is_shared=bool(row[is_shared_idx]) if is_shared_idx >= 0 and is_shared_idx < len(row) else is_shared,
                created_at=datetime.fromisoformat(row[created_idx]),
                updated_at=datetime.fromisoformat(row[updated_idx])
            )
        else:
            # Old format: id, name, content_encrypted, created_at, updated_at
            return cls(
                id=row[0],
                name=row[1],
                content=content,
                is_shared=is_shared,
                created_at=datetime.fromisoformat(row[3]),
                updated_at=datetime.fromisoformat(row[4])
            )


@dataclass
class Module:
    """Represents a hierarchical module that can contain snippets or other modules."""

    id: int
    name: str
    parent_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: tuple) -> "Module":
        """Create a Module from a database row."""
        return cls(
            id=row[0],
            name=row[1],
            parent_id=row[2],
            created_at=datetime.fromisoformat(row[3]),
            updated_at=datetime.fromisoformat(row[4]),
        )


@dataclass
class Team:
    """Represents a team for sharing snippets."""
    id: str  # UUID from Supabase
    name: str
    created_by: str  # User ID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "Team":
        """Create a Team from a Supabase response dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            created_by=data["created_by"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        )


@dataclass
class TeamMember:
    """Represents a team membership."""
    id: str  # UUID from Supabase
    team_id: str
    user_id: str
    role: str
    joined_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "TeamMember":
        """Create a TeamMember from a Supabase response dictionary."""
        return cls(
            id=data["id"],
            team_id=data["team_id"],
            user_id=data["user_id"],
            role=data.get("role", "member"),
            joined_at=datetime.fromisoformat(data["joined_at"].replace("Z", "+00:00")),
        )

