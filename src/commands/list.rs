use anyhow::Result;
use crate::config::Config;
use crate::storage::database::Database;

pub fn list_snippets(config: &Config) -> Result<()> {
    let db = Database::new(&config.db_path())?;
    let snippets = db.list_snippets()?;

    if snippets.is_empty() {
        println!("No snippets found.");
        return Ok(());
    }

    println!("Found {} snippet(s):\n", snippets.len());
    println!("{:<30} {:<20}", "Name", "Updated");
    println!("{}", "-".repeat(50));

    for snippet in snippets {
        println!("{:<30} {:<20}", snippet.name, snippet.updated_at);
    }

    Ok(())
}

