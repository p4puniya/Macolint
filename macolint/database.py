"""Database operations and encryption for Macolint, including hierarchical modules."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple

from macolint.config import get_fernet, get_db_path
from macolint.models import Snippet, Module


class Database:
    """Handles all database operations with encryption."""
    
    def __init__(self):
        self.db_path = get_db_path()
        self.fernet = get_fernet()
        self._init_database()
    
    # ------------------------------------------------------------------
    # Schema and migration
    # ------------------------------------------------------------------

    def _init_database(self):
        """Initialize or migrate the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Modules table: hierarchical containers for snippets
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_parent_name
            ON modules(parent_id, name)
            """
        )

        # Snippets table migration: ensure module_id + entity_type exist and
        # uniqueness is on (module_id, name)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='snippets'"
        )
        exists = cursor.fetchone() is not None

        if not exists:
            cursor.execute(
                """
                CREATE TABLE snippets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    module_id INTEGER NULL,
                    entity_type TEXT NOT NULL DEFAULT 'snippet',
                    content_encrypted BLOB NOT NULL,
                    is_shared INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_snippets_module_name
                ON snippets(module_id, name)
                """
            )
        else:
            # Check existing schema and migrate if needed
            cursor.execute("PRAGMA table_info(snippets)")
            cols = [row[1] for row in cursor.fetchall()]
            needs_migration = "module_id" not in cols or "entity_type" not in cols
            needs_is_shared = "is_shared" not in cols

            # Add is_shared column if missing
            if needs_is_shared:
                cursor.execute(
                    "ALTER TABLE snippets ADD COLUMN is_shared INTEGER NOT NULL DEFAULT 0"
                )

            if needs_migration:
                cursor.execute(
                    """
                    CREATE TABLE snippets_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        module_id INTEGER NULL,
                        entity_type TEXT NOT NULL DEFAULT 'snippet',
                        content_encrypted BLOB NOT NULL,
                        is_shared INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_snippets_module_name
                    ON snippets_new(module_id, name)
                    """
                )
                # Migrate existing data; old table uses name as full identifier
                # Check if is_shared exists in old table
                has_is_shared = "is_shared" in cols
                if has_is_shared:
                    cursor.execute(
                        """
                        INSERT INTO snippets_new (
                            id, name, module_id, entity_type,
                            content_encrypted, is_shared, created_at, updated_at
                        )
                        SELECT
                            id,
                            name,
                            NULL as module_id,
                            'snippet' as entity_type,
                            content_encrypted,
                            is_shared,
                            created_at,
                            updated_at
                        FROM snippets
                        """
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO snippets_new (
                            id, name, module_id, entity_type,
                            content_encrypted, is_shared, created_at, updated_at
                        )
                        SELECT
                            id,
                            name,
                            NULL as module_id,
                            'snippet' as entity_type,
                            content_encrypted,
                            0 as is_shared,
                            created_at,
                            updated_at
                        FROM snippets
                        """
                    )
                cursor.execute("DROP TABLE snippets")
                cursor.execute("ALTER TABLE snippets_new RENAME TO snippets")
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)
    
    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def _encrypt_content(self, content: str) -> bytes:
        """Encrypt snippet content."""
        return self.fernet.encrypt(content.encode("utf-8"))
    
    def _decrypt_content(self, encrypted: bytes) -> str:
        """Decrypt snippet content."""
        return self.fernet.decrypt(encrypted).decode("utf-8")

    # ------------------------------------------------------------------
    # Path and module helpers
    # ------------------------------------------------------------------

    def _split_path(self, full_path: str) -> Tuple[Optional[str], str]:
        """
        Split a path like 'module1/module2/snippet' into (module_path, snippet_name).
        If there is no '/', module_path is None and snippet_name is the full_path.
        """
        if "/" not in full_path:
            return None, full_path
        parts = full_path.split("/")
        module_path = "/".join(parts[:-1]) if len(parts) > 1 else None
        snippet_name = parts[-1]
        return module_path or None, snippet_name

    def _resolve_module_path(
        self, module_path: Optional[str], create: bool = False
    ) -> Optional[Module]:
        """
        Resolve a module path like 'module1/module2' to a Module.
        If create=True, missing modules along the path are created.
        """
        if not module_path:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        parent_id: Optional[int] = None
        current_module: Optional[Module] = None

        for segment in module_path.split("/"):
            if parent_id is None:
                cursor.execute(
                    """
                    SELECT id, name, parent_id, created_at, updated_at
                    FROM modules
                    WHERE name = ? AND parent_id IS NULL
                    """,
                    (segment,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name, parent_id, created_at, updated_at
                    FROM modules
                    WHERE name = ? AND parent_id = ?
                    """,
                    (segment, parent_id),
                )
            row = cursor.fetchone()

            if row is None:
                if not create:
                    conn.close()
                    return None
                # Create missing module
                cursor.execute(
                    """
                    INSERT INTO modules (name, parent_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (segment, parent_id, now, now),
                )
                module_id = cursor.lastrowid
                row = (module_id, segment, parent_id, now, now)

            current_module = Module.from_row(row)
            parent_id = current_module.id

        conn.commit()
        conn.close()
        return current_module

    def get_module_by_path(self, module_path: str) -> Optional[Module]:
        """Get a Module by its hierarchical path."""
        return self._resolve_module_path(module_path, create=False)

    def create_module_path(self, module_path: str) -> Module:
        """Ensure a module path exists and return the deepest module."""
        module = self._resolve_module_path(module_path, create=True)
        assert module is not None  # For type checkers; create=True guarantees this
        return module

    def get_module_children(self, module: Optional[Module]) -> List[Module]:
        """
        List direct child modules under the given module.
        If module is None, list top-level modules.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if module is None:
            cursor.execute(
                """
                SELECT id, name, parent_id, created_at, updated_at
                FROM modules
                WHERE parent_id IS NULL
                ORDER BY name
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, name, parent_id, created_at, updated_at
                FROM modules
                WHERE parent_id = ?
                ORDER BY name
                """,
                (module.id,),
            )

        rows = cursor.fetchall()
        conn.close()
        return [Module.from_row(row) for row in rows]

    # ------------------------------------------------------------------
    # Snippet operations (path-aware)
    # ------------------------------------------------------------------

    def _get_snippet_row_by_path(
        self, full_path: str
    ) -> Optional[Tuple[int, str, bytes, int, str, str]]:
        """Internal helper to fetch a snippet row by hierarchical path."""
        module_path, snippet_name = self._split_path(full_path)
        module = self._resolve_module_path(module_path, create=False)

        conn = self._get_connection()
        cursor = conn.cursor()

        if module is None:
            cursor.execute(
                """
                SELECT id, name, content_encrypted, is_shared, created_at, updated_at
                FROM snippets
                WHERE name = ? AND module_id IS NULL
                """,
                (snippet_name,),
            )
        else:
            cursor.execute(
                """
                SELECT id, name, content_encrypted, is_shared, created_at, updated_at
                FROM snippets
                WHERE name = ? AND module_id = ?
                """,
                (snippet_name, module.id),
            )

        row = cursor.fetchone()
        conn.close()
        return row

    def save_snippet(self, full_path: str, content: str) -> bool:
        """
        Save a snippet at the given hierarchical path.
        Returns True if created, False if updated.
        """
        module_path, snippet_name = self._split_path(full_path)
        module = self._resolve_module_path(module_path, create=True)
        module_id = module.id if module is not None else None

        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        encrypted_content = self._encrypt_content(content)
        
        # Try to insert new snippet
        try:
            cursor.execute(
                """
                INSERT INTO snippets (
                    name, module_id, entity_type,
                    content_encrypted, is_shared, created_at, updated_at
                )
                VALUES (?, ?, 'snippet', ?, 0, ?, ?)
                """,
                (snippet_name, module_id, encrypted_content, now, now),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Snippet exists; update instead
            if module_id is None:
                cursor.execute(
                    """
                    UPDATE snippets
                    SET content_encrypted = ?, updated_at = ?
                    WHERE name = ? AND module_id IS NULL
                    """,
                    (encrypted_content, now, snippet_name),
                )
            else:
                cursor.execute(
                    """
                UPDATE snippets 
                SET content_encrypted = ?, updated_at = ?
                    WHERE name = ? AND module_id = ?
                    """,
                    (encrypted_content, now, snippet_name, module_id),
                )
            conn.commit()
            conn.close()
            return False
    
    def get_snippet(self, full_path: str) -> Optional[Snippet]:
        """Retrieve a snippet by hierarchical path."""
        row = self._get_snippet_row_by_path(full_path)
        if row is None:
            return None
        encrypted_content = row[2]
        is_shared = bool(row[3]) if len(row) > 3 else False
        content = self._decrypt_content(encrypted_content)
        return Snippet.from_row(row, content, is_shared=is_shared)
    
    def update_snippet(self, full_path: str, content: str) -> bool:
        """Update an existing snippet by hierarchical path."""
        module_path, snippet_name = self._split_path(full_path)
        module = self._resolve_module_path(module_path, create=False)
        module_id = module.id if module is not None else None

        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        encrypted_content = self._encrypt_content(content)
        
        if module_id is None:
            cursor.execute(
                """
                UPDATE snippets
                SET content_encrypted = ?, updated_at = ?
                WHERE name = ? AND module_id IS NULL
                """,
                (encrypted_content, now, snippet_name),
            )
        else:
            cursor.execute(
                """
            UPDATE snippets 
            SET content_encrypted = ?, updated_at = ?
                WHERE name = ? AND module_id = ?
                """,
                (encrypted_content, now, snippet_name, module_id),
            )
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    def delete_snippet(self, full_path: str) -> bool:
        """Delete a snippet by hierarchical path."""
        module_path, snippet_name = self._split_path(full_path)
        module = self._resolve_module_path(module_path, create=False)
        module_id = module.id if module is not None else None

        conn = self._get_connection()
        cursor = conn.cursor()
        
        if module_id is None:
            cursor.execute(
                """
                DELETE FROM snippets
                WHERE name = ? AND module_id IS NULL
                """,
                (snippet_name,),
            )
        else:
            cursor.execute(
                """
                DELETE FROM snippets
                WHERE name = ? AND module_id = ?
                """,
                (snippet_name, module_id),
            )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    # ------------------------------------------------------------------
    # Listing and search
    # ------------------------------------------------------------------

    def _build_snippet_full_path_rows(
        self,
        rows: List[Tuple[int, str, Optional[int], bytes, int, str, str]],
    ) -> List[str]:
        """Convert snippet rows with module_id into full path strings."""
        if not rows:
            return []

        # Collect module ids needed
        module_ids = {row[2] for row in rows if row[2] is not None}
        module_paths = {}

        if module_ids:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT id, name, parent_id, created_at, updated_at
                FROM modules
                WHERE id IN ({",".join("?" * len(module_ids))})
                """,
                tuple(module_ids),
            )
            mod_rows = cursor.fetchall()

            modules = {row[0]: Module.from_row(row) for row in mod_rows}

            # Build full path for each module via parent chain
            def build_module_path(mid: int) -> str:
                if mid in module_paths:
                    return module_paths[mid]
                mod = modules.get(mid)
                if mod is None:
                    # Load missing ancestor module lazily
                    cursor.execute(
                        """
                        SELECT id, name, parent_id, created_at, updated_at
                        FROM modules
                        WHERE id = ?
                        """,
                        (mid,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        module_paths[mid] = ""
                        return ""
                    mod = Module.from_row(row)
                    modules[mid] = mod
                if mod.parent_id is None:
                    path = mod.name
                else:
                    parent_path = build_module_path(mod.parent_id)
                    path = f"{parent_path}/{mod.name}" if parent_path else mod.name
                module_paths[mid] = path
                return path

            for mid in module_ids:
                build_module_path(mid)

            conn.close()

        full_paths: List[str] = []
        for row in rows:
            snippet_name = row[1]
            module_id = row[2]
            if module_id is None:
                full_paths.append(snippet_name)
            else:
                module_path = module_paths.get(module_id, "")
                if module_path:
                    full_paths.append(f"{module_path}/{snippet_name}")
                else:
                    full_paths.append(snippet_name)
        return full_paths

    def list_modules(self, keyword: Optional[str] = None) -> List[str]:
        """
        List all module full paths, optionally filtered by keyword
        (case-insensitive match on the full path).
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, parent_id, created_at, updated_at
            FROM modules
            ORDER BY name
            """
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        modules = {row[0]: Module.from_row(row) for row in rows}
        module_paths: dict[int, str] = {}

        def build_module_path(mid: int) -> str:
            if mid in module_paths:
                return module_paths[mid]
            mod = modules.get(mid)
            if mod is None:
                module_paths[mid] = ""
                return ""
            if mod.parent_id is None:
                path = mod.name
            else:
                parent_path = build_module_path(mod.parent_id)
                path = f"{parent_path}/{mod.name}" if parent_path else mod.name
            module_paths[mid] = path
            return path

        for mid in modules.keys():
            build_module_path(mid)

        paths = list(module_paths.values())
        if keyword:
            keyword_lower = keyword.lower()
            paths = [p for p in paths if keyword_lower in p.lower()]
        return sorted(paths)

    def list_snippets(self, keyword: Optional[str] = None) -> List[str]:
        """
        List all snippet full paths, optionally filtered by keyword
        (case-insensitive match on the full path).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if keyword:
            # Fetch all, then filter in Python on full path
            cursor.execute(
                """
                SELECT id, name, module_id, content_encrypted, is_shared, created_at, updated_at
                FROM snippets
                ORDER BY name
                """
            )
            rows = cursor.fetchall()
            conn.close()
            paths = self._build_snippet_full_path_rows(rows)
            keyword_lower = keyword.lower()
            return [p for p in paths if keyword_lower in p.lower()]
        else:
            cursor.execute(
                """
                SELECT id, name, module_id, content_encrypted, is_shared, created_at, updated_at
                FROM snippets
                ORDER BY name
                """
            )
            rows = cursor.fetchall()
            conn.close()
            return self._build_snippet_full_path_rows(rows)
    
    def search_snippets(self, query: str) -> List[str]:
        """
        Fuzzy search for snippet full paths.
        Returns list of full paths matching the query (case-insensitive).
        """
        all_paths = self.list_snippets()
        query_lower = query.lower()
        return [p for p in all_paths if query_lower in p.lower()]

    def get_all_snippet_names(self) -> List[str]:
        """Get all snippet full paths for fuzzy search."""
        return self.list_snippets()

    def list_snippets_in_module(self, module: Optional[Module]) -> List[str]:
        """
        List snippet names directly under the given module (not including descendants).
        Returned values are full paths.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if module is None:
            cursor.execute(
                """
                SELECT id, name, module_id, content_encrypted, created_at, updated_at
                FROM snippets
                WHERE module_id IS NULL
                ORDER BY name
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, name, module_id, content_encrypted, created_at, updated_at
                FROM snippets
                WHERE module_id = ?
            ORDER BY name
                """,
                (module.id,),
            )
        rows = cursor.fetchall()
        conn.close()
        return self._build_snippet_full_path_rows(rows)

    # ------------------------------------------------------------------
    # Module deletion
    # ------------------------------------------------------------------

    def delete_module_tree(self, module_path: str) -> bool:
        """
        Delete a module and all its descendant modules and snippets.
        Returns True if a module was deleted, False if not found.
        """
        module = self.get_module_by_path(module_path)
        if module is None:
            return False

        conn = self._get_connection()
        cursor = conn.cursor()

        # Collect all descendant module IDs (including the root)
        to_visit = [module.id]
        all_ids: List[int] = []

        while to_visit:
            mid = to_visit.pop()
            all_ids.append(mid)
            cursor.execute(
                "SELECT id FROM modules WHERE parent_id = ?", (mid,)
            )
            children = [row[0] for row in cursor.fetchall()]
            to_visit.extend(children)

        if not all_ids:
            conn.close()
            return False

        placeholders = ",".join("?" for _ in all_ids)

        # Delete snippets in any of these modules
        cursor.execute(
            f"DELETE FROM snippets WHERE module_id IN ({placeholders})",
            tuple(all_ids),
        )
        # Delete modules themselves
        cursor.execute(
            f"DELETE FROM modules WHERE id IN ({placeholders})",
            tuple(all_ids),
        )

        conn.commit()
        conn.close()
        return True

    # ------------------------------------------------------------------
    # Module path utilities
    # ------------------------------------------------------------------

    def get_module_full_path(self, module: Module) -> str:
        """Compute the full hierarchical path for a module."""
        conn = self._get_connection()
        cursor = conn.cursor()

        parts: List[str] = []
        current_id: Optional[int] = module.id

        while current_id is not None:
            cursor.execute(
                """
                SELECT id, name, parent_id, created_at, updated_at
                FROM modules
                WHERE id = ?
                """,
                (current_id,),
            )
            row = cursor.fetchone()
            if row is None:
                break
            mod = Module.from_row(row)
            parts.append(mod.name)
            current_id = mod.parent_id

        conn.close()
        return "/".join(reversed(parts))

    # ------------------------------------------------------------------
    # Rename operations
    # ------------------------------------------------------------------

    def rename_module(self, old_path: str, new_path: str) -> bool:
        """
        Rename a module from old_path to new_path.
        The new_path can be:
        - Just a new name (if staying in same parent): "new_name"
        - Full path: "parent/new_name" or "new_parent/new_name"
        Returns True if successful, False if module not found or new path conflicts.
        """
        old_module = self.get_module_by_path(old_path)
        if old_module is None:
            return False

        # Split new path to get parent and new name
        new_parts = new_path.split("/")
        new_name = new_parts[-1]
        new_parent_path = "/".join(new_parts[:-1]) if len(new_parts) > 1 else None

        # If new_parent_path is None, keep the same parent
        if new_parent_path is None:
            # Keep same parent - just rename the module name
            new_parent_id = old_module.parent_id
        else:
            # Moving to a different parent - verify new parent exists
            new_parent = self.get_module_by_path(new_parent_path)
            if new_parent is None:
                return False
            new_parent_id = new_parent.id

        # Check if a module with the new name already exists in the target parent
        # (to avoid conflicts)
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if new_parent_id is None:
            cursor.execute(
                """
                SELECT id FROM modules
                WHERE name = ? AND parent_id IS NULL AND id != ?
                """,
                (new_name, old_module.id),
            )
        else:
            cursor.execute(
                """
                SELECT id FROM modules
                WHERE name = ? AND parent_id = ? AND id != ?
                """,
                (new_name, new_parent_id, old_module.id),
            )
        
        if cursor.fetchone() is not None:
            # Name conflict
            conn.close()
            return False

        # Also check if the full new path already exists (could be a different module)
        full_new_path = new_path if new_parent_path else new_name
        existing_module = self.get_module_by_path(full_new_path)
        if existing_module is not None and existing_module.id != old_module.id:
            conn.close()
            return False

        now = datetime.now().isoformat()

        try:
            # Update the module's name and parent
            cursor.execute(
                """
                UPDATE modules
                SET name = ?, parent_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, new_parent_id, now, old_module.id),
            )

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Name conflict at new location (same name already exists in that parent)
            conn.close()
            return False

    def rename_snippet(self, old_path: str, new_path: str) -> bool:
        """
        Rename (or move) a snippet from old_path to new_path.
        Returns True if successful, False if snippet not found or new path conflicts.
        """
        snippet = self.get_snippet(old_path)
        if snippet is None:
            return False

        # Check if new path already exists
        if self.get_snippet(new_path) is not None:
            return False

        # Parse new path
        new_module_path, new_snippet_name = self._split_path(new_path)
        new_module = self._resolve_module_path(new_module_path, create=False)
        new_module_id = new_module.id if new_module is not None else None

        # Parse old path to get old module
        old_module_path, old_snippet_name = self._split_path(old_path)
        old_module = self._resolve_module_path(old_module_path, create=False)
        old_module_id = old_module.id if old_module is not None else None

        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            # Update snippet name and module_id
            cursor.execute(
                """
                UPDATE snippets
                SET name = ?, module_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_snippet_name, new_module_id, now, snippet.id),
            )

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Name conflict at new location
            conn.close()
            return False

    # ------------------------------------------------------------------
    # Sharing operations
    # ------------------------------------------------------------------

    def mark_snippet_shared(self, full_path: str, is_shared: bool) -> bool:
        """
        Mark a snippet as shared or unshared.
        
        Args:
            full_path: Full path to the snippet
            is_shared: True to mark as shared, False to unshare
        
        Returns:
            True if successful, False if snippet not found
        """
        module_path, snippet_name = self._split_path(full_path)
        module = self._resolve_module_path(module_path, create=False)
        module_id = module.id if module is not None else None

        conn = self._get_connection()
        cursor = conn.cursor()

        if module_id is None:
            cursor.execute(
                """
                UPDATE snippets
                SET is_shared = ?
                WHERE name = ? AND module_id IS NULL
                """,
                (1 if is_shared else 0, snippet_name),
            )
        else:
            cursor.execute(
                """
                UPDATE snippets
                SET is_shared = ?
                WHERE name = ? AND module_id = ?
                """,
                (1 if is_shared else 0, snippet_name, module_id),
            )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def get_shared_snippets(self) -> List[str]:
        """
        Get list of all shared snippet full paths.
        
        Returns:
            List of full paths for shared snippets
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, module_id, content_encrypted, is_shared, created_at, updated_at
            FROM snippets
            WHERE is_shared = 1
            ORDER BY name
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return self._build_snippet_full_path_rows(rows)

    def is_snippet_shared(self, full_path: str) -> bool:
        """
        Check if a snippet is marked as shared.
        
        Args:
            full_path: Full path to the snippet
        
        Returns:
            True if shared, False if not shared or not found
        """
        snippet = self.get_snippet(full_path)
        if snippet is None:
            return False
        return snippet.is_shared


