use anyhow::{Context, Result};
use fuzzy_matcher::FuzzyMatcher;
use fuzzy_matcher::skim::SkimMatcherV2;
use std::io::{self, Write};
use std::process::{Command, Stdio};

pub fn fuzzy_search(options: &[String]) -> Result<String> {
    // Try to use fzf if available
    if let Ok(output) = try_fzf(options) {
        return Ok(output);
    }

    // Fallback to interactive fuzzy matcher
    interactive_fuzzy_search(options)
}

fn try_fzf(options: &[String]) -> Result<String> {
    let mut child = Command::new("fzf")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .context("fzf not available")?;

    // Write options to fzf stdin
    if let Some(stdin) = child.stdin.as_mut() {
        for option in options {
            writeln!(stdin, "{}", option)?;
        }
    }

    let output = child.wait_with_output()?;
    
    // Exit code 130 is returned when user cancels (ESC)
    if output.status.code() == Some(130) {
        anyhow::bail!("Selection cancelled");
    }
    
    if !output.status.success() {
        anyhow::bail!("fzf exited with error");
    }

    let selected = String::from_utf8(output.stdout)?
        .trim()
        .to_string();
    
    if selected.is_empty() {
        anyhow::bail!("No selection made");
    }

    Ok(selected)
}

fn interactive_fuzzy_search(options: &[String]) -> Result<String> {
    if options.is_empty() {
        anyhow::bail!("No snippets available");
    }

    let matcher = SkimMatcherV2::default();
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    loop {
        print!("Search: ");
        stdout.flush()?;

        let mut query = String::new();
        stdin.read_line(&mut query)?;
        let query = query.trim();

        if query.is_empty() {
            continue;
        }

        // Score and sort matches
        let mut matches: Vec<(i64, &String)> = options
            .iter()
            .filter_map(|option| {
                matcher.fuzzy_match(option, query).map(|score| (score, option))
            })
            .collect();

        matches.sort_by(|a, b| b.0.cmp(&a.0));

        if matches.is_empty() {
            println!("No matches found. Try again.");
            continue;
        }

        // Display top matches
        println!("\nMatches:");
        for (i, (_, option)) in matches.iter().take(10).enumerate() {
            println!("  {}. {}", i + 1, option);
        }

        // If there's a clear best match (score difference > threshold), use it
        if matches.len() == 1 || (matches.len() > 1 && matches[0].0 - matches[1].0 > 100) {
            return Ok(matches[0].1.clone());
        }

        // Otherwise, ask user to select
        print!("\nSelect (1-{}): ", matches.len().min(10));
        stdout.flush()?;

        let mut selection = String::new();
        stdin.read_line(&mut selection)?;
        let selection = selection.trim().parse::<usize>()?;

        if selection > 0 && selection <= matches.len().min(10) {
            return Ok(matches[selection - 1].1.clone());
        }

        println!("Invalid selection. Try again.\n");
    }
}

