use anyhow::{Context, Result};
use rusqlite::{params, Connection};
use std::path::Path;

#[derive(Debug)]
pub struct Snippet {
    pub id: i64,
    pub name: String,
    pub content_encrypted: String,
    pub created_at: String,
    pub updated_at: String,
    pub user_id: Option<String>,
    pub team_id: Option<String>,
    pub synced_at: Option<String>,
    pub sync_status: Option<String>,
}

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new(db_path: &Path) -> Result<Self> {
        let conn = Connection::open(db_path)
            .with_context(|| format!("Failed to open database: {:?}", db_path))?;
        
        let db = Self { conn };
        db.init_schema()?;
        Ok(db)
    }

    fn init_schema(&self) -> Result<()> {
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                content_encrypted TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                user_id TEXT,
                team_id TEXT,
                synced_at TEXT,
                sync_status TEXT
            )",
            [],
        )
        .context("Failed to create snippets table")?;
        
        Ok(())
    }

    pub fn save_snippet(&self, name: &str, encrypted_content: &str) -> Result<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO snippets (name, content_encrypted, updated_at)
             VALUES (?1, ?2, datetime('now'))",
            params![name, encrypted_content],
        )
        .context("Failed to save snippet")?;
        
        Ok(())
    }

    pub fn get_snippet(&self, name: &str) -> Result<Option<Snippet>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, name, content_encrypted, created_at, updated_at, 
                    user_id, team_id, synced_at, sync_status
             FROM snippets WHERE name = ?1"
        )?;
        
        let snippet = stmt.query_row(params![name], |row| {
            Ok(Snippet {
                id: row.get(0)?,
                name: row.get(1)?,
                content_encrypted: row.get(2)?,
                created_at: row.get(3)?,
                updated_at: row.get(4)?,
                user_id: row.get(5)?,
                team_id: row.get(6)?,
                synced_at: row.get(7)?,
                sync_status: row.get(8)?,
            })
        });
        
        match snippet {
            Ok(s) => Ok(Some(s)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    pub fn list_snippets(&self) -> Result<Vec<Snippet>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, name, content_encrypted, created_at, updated_at,
                    user_id, team_id, synced_at, sync_status
             FROM snippets ORDER BY updated_at DESC"
        )?;
        
        let snippets = stmt.query_map([], |row| {
            Ok(Snippet {
                id: row.get(0)?,
                name: row.get(1)?,
                content_encrypted: row.get(2)?,
                created_at: row.get(3)?,
                updated_at: row.get(4)?,
                user_id: row.get(5)?,
                team_id: row.get(6)?,
                synced_at: row.get(7)?,
                sync_status: row.get(8)?,
            })
        })?;
        
        let mut result = Vec::new();
        for snippet in snippets {
            result.push(snippet?);
        }
        
        Ok(result)
    }

    pub fn get_all_names(&self) -> Result<Vec<String>> {
        let mut stmt = self.conn.prepare("SELECT name FROM snippets ORDER BY name")?;
        let names = stmt.query_map([], |row| {
            Ok(row.get::<_, String>(0)?)
        })?;
        
        let mut result = Vec::new();
        for name in names {
            result.push(name?);
        }
        
        Ok(result)
    }
}

