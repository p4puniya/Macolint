use anyhow::{Context, Result};
use clipboard::{ClipboardContext, ClipboardProvider};
use crate::config::Config;
use crate::search::fuzzy::fuzzy_search;
use crate::storage::{database::Database, encryption::Encryption};

pub fn get_snippet(config: &Config, name: Option<String>) -> Result<()> {
    let snippet_name = match name {
        Some(n) => n,
        None => {
            // Open fuzzy search
            let db = Database::new(&config.db_path())?;
            let names = db.get_all_names()?;
            fuzzy_search(&names)?
        }
    };

    // Retrieve and decrypt snippet
    let db = Database::new(&config.db_path())?;
    let snippet = db.get_snippet(&snippet_name)?
        .with_context(|| format!("Snippet not found: {}", snippet_name))?;

    let encryption = Encryption::new(&config.master_key)?;
    let plaintext = encryption.decrypt(&snippet.content_encrypted)?;

    // Copy to clipboard
    let mut ctx: ClipboardContext = ClipboardProvider::new()
        .map_err(|e| anyhow::anyhow!("Failed to initialize clipboard: {}", e))?;
    ctx.set_contents(plaintext.clone())
        .map_err(|e| anyhow::anyhow!("Failed to write to clipboard: {}", e))?;

    println!("✓ Copied to clipboard: {}", snippet_name);
    Ok(())
}

