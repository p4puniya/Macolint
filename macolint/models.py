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

