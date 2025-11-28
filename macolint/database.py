"""Database operations and encryption for Macolint."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
from macolint.config import get_fernet, get_db_path
from macolint.models import Snippet


class Database:
    """Handles all database operations with encryption."""
    
    def __init__(self):
        self.db_path = get_db_path()
        self.fernet = get_fernet()
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                content_encrypted BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snippets_name ON snippets(name)
        """)
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)
    
    def _encrypt_content(self, content: str) -> bytes:
        """Encrypt snippet content."""
        return self.fernet.encrypt(content.encode('utf-8'))
    
    def _decrypt_content(self, encrypted: bytes) -> str:
        """Decrypt snippet content."""
        return self.fernet.decrypt(encrypted).decode('utf-8')
    
    def save_snippet(self, name: str, content: str) -> bool:
        """
        Save a snippet. Returns True if created, False if updated.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        encrypted_content = self._encrypt_content(content)
        
        try:
            # Try to insert new snippet
            cursor.execute("""
                INSERT INTO snippets (name, content_encrypted, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (name, encrypted_content, now, now))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Name already exists, update instead
            cursor.execute("""
                UPDATE snippets 
                SET content_encrypted = ?, updated_at = ?
                WHERE name = ?
            """, (encrypted_content, now, name))
            conn.commit()
            conn.close()
            return False
    
    def get_snippet(self, name: str) -> Optional[Snippet]:
        """Retrieve a snippet by name."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, content_encrypted, created_at, updated_at
            FROM snippets
            WHERE name = ?
        """, (name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        encrypted_content = row[2]
        content = self._decrypt_content(encrypted_content)
        return Snippet.from_row(row, content)
    
    def update_snippet(self, name: str, content: str) -> bool:
        """Update an existing snippet."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        encrypted_content = self._encrypt_content(content)
        
        cursor.execute("""
            UPDATE snippets 
            SET content_encrypted = ?, updated_at = ?
            WHERE name = ?
        """, (encrypted_content, now, name))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
    
    def delete_snippet(self, name: str) -> bool:
        """Delete a snippet."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM snippets WHERE name = ?", (name,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def list_snippets(self, keyword: Optional[str] = None) -> List[str]:
        """List all snippet names, optionally filtered by keyword."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if keyword:
            cursor.execute("""
                SELECT name FROM snippets 
                WHERE name LIKE ?
                ORDER BY name
            """, (f"%{keyword}%",))
        else:
            cursor.execute("SELECT name FROM snippets ORDER BY name")
        
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return names
    
    def search_snippets(self, query: str) -> List[str]:
        """
        Fuzzy search for snippet names.
        Returns list of names matching the query (case-insensitive).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM snippets 
            WHERE LOWER(name) LIKE LOWER(?)
            ORDER BY name
        """, (f"%{query}%",))
        
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return names
    
    def get_all_snippet_names(self) -> List[str]:
        """Get all snippet names for fuzzy search."""
        return self.list_snippets()

