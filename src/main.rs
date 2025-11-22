mod commands;
mod config;
mod search;
mod storage;

use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "snip")]
#[command(about = "A terminal-first snippet manager", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Save a snippet (from clipboard or provided content)
    Save {
        /// Name of the snippet
        name: String,
        /// Optional content (if not provided, reads from clipboard)
        content: Option<String>,
    },
    /// List all snippets
    List,
    /// Get a snippet (copy to clipboard)
    Get {
        /// Name of the snippet (if not provided, opens fuzzy search)
        name: Option<String>,
    },
}

fn main() -> Result<()> {
    // Initialize config on first run
    let config = config::Config::init()?;

    let cli = Cli::parse();

    match cli.command {
        Commands::Save { name, content } => commands::save::save_snippet(&config, name, content)?,
        Commands::List => commands::list::list_snippets(&config)?,
        Commands::Get { name } => commands::get::get_snippet(&config, name)?,
    }

    Ok(())
}

