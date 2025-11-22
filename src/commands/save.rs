use anyhow::{Context, Result};
use clipboard::{ClipboardContext, ClipboardProvider};
use crate::config::Config;
use crate::storage::{database::Database, encryption::Encryption};

pub fn save_snippet(config: &Config, name: String, content: Option<String>) -> Result<()> {
    let plaintext = match content {
        Some(c) => c,
        None => {
            // Read from clipboard
            let mut ctx: ClipboardContext = ClipboardProvider::new()
                .map_err(|e| anyhow::anyhow!("Failed to initialize clipboard: {}", e))?;
            ctx.get_contents()
                .map_err(|e| anyhow::anyhow!("Failed to read from clipboard: {}", e))?
        }
    };

    // Encrypt the content
    let encryption = Encryption::new(&config.master_key)?;
    let encrypted_content = encryption.encrypt(&plaintext)?;

    // Save to database
    let db = Database::new(&config.db_path())?;
    db.save_snippet(&name, &encrypted_content)?;

    println!("✓ Saved snippet: {}", name);
    Ok(())
}

