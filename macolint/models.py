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
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: tuple, content: str) -> "Snippet":
        """Create a Snippet from a database row."""
        return cls(
            id=row[0],
            name=row[1],
            content=content,
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

