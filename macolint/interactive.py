"""Interactive terminal UI utilities for Macolint."""

import sys
from typing import Optional, List
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import prompt
from rich.console import Console
from rich.table import Table
from macolint.database import Database


console = Console()


def fuzzy_match(query: str, candidates: List[str]) -> List[str]:
    """Simple fuzzy matching algorithm."""
    if not query:
        return candidates
    
    query_lower = query.lower()
    matches = []
    
    for candidate in candidates:
        candidate_lower = candidate.lower()
        # Check if all characters in query appear in order in candidate
        query_idx = 0
        for char in candidate_lower:
            if query_idx < len(query_lower) and char == query_lower[query_idx]:
                query_idx += 1
        
        if query_idx == len(query_lower):
            matches.append(candidate)
    
    return matches


def display_snippet_suggestions(query: str, matches: List[str], max_display: int = 10):
    """Display snippet suggestions in a formatted list."""
    if not matches:
        return
    
    # Limit display
    display_matches = matches[:max_display]
    
    # Create a table for better formatting
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("", style="cyan")
    
    for match in display_matches:
        table.add_row(f"- {match}")
    
    console.print(table)


def prompt_snippet_name(snippet_names: List[str]) -> Optional[str]:
    """
    Interactive prompt for selecting a snippet name with fuzzy search and tab completion.
    Returns the selected name or None if cancelled.
    """
    if not snippet_names:
        console.print("[yellow]No snippets found.[/yellow]")
        return None
    
    # Create a completer for tab completion
    completer = FuzzyCompleter(WordCompleter(snippet_names, ignore_case=True))
    
    # Custom key bindings
    kb = KeyBindings()
    
    session = PromptSession(
        completer=completer,
        complete_while_typing=True,
        key_bindings=kb
    )
    
    try:
        # Show initial prompt
        console.print("[cyan]>[/cyan] ", end="")
        
        user_input = session.prompt("")
        
        if not user_input.strip():
            return None
        
        # Find matches
        matches = fuzzy_match(user_input, snippet_names)
        
        if not matches:
            console.print(f"[red]No snippets found matching '{user_input}'[/red]")
            return None
        
        if len(matches) == 1:
            return matches[0]
        
        # Multiple matches - show them and let user select
        if user_input in matches:
            return user_input
        
        # Show suggestions
        display_snippet_suggestions(user_input, matches)
        
        # Prompt again for exact selection
        console.print("[cyan]>[/cyan] ", end="")
        final_input = session.prompt("")
        
        if final_input in matches:
            return final_input
        
        # Try fuzzy match again
        final_matches = fuzzy_match(final_input, matches)
        if final_matches:
            return final_matches[0]
        
        return None
        
    except KeyboardInterrupt:
        # Esc or Ctrl+C
        return None
    except EOFError:
        # Esc key
        return None


def prompt_snippet_content(existing_content: Optional[str] = None) -> Optional[str]:
    """
    Interactive prompt for entering snippet content.
    Returns the content or None if cancelled.
    Supports multi-line input. Press Ctrl+D to finish, Esc to cancel.
    """
    if existing_content:
        console.print("[cyan]Edit the snippet. Press Ctrl+D to save, Esc to cancel.[/cyan]")
        console.print("[dim]Tip: For multi-line snippets, use Ctrl+D when done.[/dim]")
    else:
        console.print("[cyan]Enter the snippet here. Press Enter to save (single line) or Ctrl+D for multi-line, Esc to cancel.[/cyan]")
    
    try:
        kb = KeyBindings()
        
        @kb.add(Keys.Escape)
        def _(event):
            event.app.exit(result=None)
        
        @kb.add('c-d')
        def _(event):
            """Ctrl+D to finish input."""
            buffer = event.app.current_buffer
            if buffer.text.strip():
                event.app.exit(result=buffer.text)
            else:
                event.app.exit(result="")
        
        # For single-line input, Enter saves immediately
        # For multi-line, user can use Ctrl+D
        session = PromptSession(
            key_bindings=kb,
            multiline=False  # Single-line by default for simplicity
        )
        
        content = session.prompt("> ", default=existing_content or "")
        
        if content is None:
            return None
        
        return content.strip()
        
    except (KeyboardInterrupt, EOFError):
        # Esc or Ctrl+C pressed
        return None


def prompt_snippet_name_simple(snippet_names: List[str]) -> Optional[str]:
    """
    Interactive prompt for snippet name selection.
    Shows suggestions as user types and allows tab completion.
    """
    if not snippet_names:
        console.print("[yellow]No snippets found.[/yellow]")
        return None
    
    # Create completer with fuzzy matching
    completer = FuzzyCompleter(WordCompleter(snippet_names, ignore_case=True))
    
    # Custom key bindings for Esc
    kb = KeyBindings()
    
    @kb.add(Keys.Escape)
    def _(event):
        event.app.exit(result=None)
    
    # Ensure we can use the prompt even when called from shell wrappers
    # prompt_toolkit writes to stderr by default, which should be visible
    # When stdout is captured (command substitution), we need to ensure the prompt still works
    import sys
    from prompt_toolkit.output import create_output
    
    # Create output that explicitly writes to stderr
    # This ensures the prompt is visible even when stdout is captured by command substitution
    try:
        output = create_output(stdout=sys.stderr)
    except Exception:
        # Fallback to default output if creating custom output fails
        output = None
    
    session = PromptSession(
        completer=completer,
        complete_while_typing=True,
        key_bindings=kb,
        mouse_support=False,
        output=output if output else None
    )
    
    try:
        # Show prompt with ">" indicator
        # prompt_toolkit writes to stderr by default, which should be visible
        result = session.prompt("> ")
        
        if not result or not result.strip():
            return None
        
        # Validate the result is in our list
        result = result.strip()
        
        # Check exact match first
        if result in snippet_names:
            return result
        
        # Try fuzzy match to find best match
        matches = fuzzy_match(result, snippet_names)
        if matches:
            # Return the first (best) match
            return matches[0]
        
        # If no fuzzy match, return what user typed (might be a new name for save)
        return result
        
    except (KeyboardInterrupt, EOFError):
        # Esc or Ctrl+C pressed
        return None
    except Exception as e:
        # If prompt_toolkit fails, check if it's a TTY issue
        import sys
        error_str = str(e).lower()
        is_tty_error = 'terminal' in error_str or 'tty' in error_str or 'not a terminal' in error_str
        
        if not sys.stdin.isatty() or is_tty_error:
            # Not a TTY or TTY-related error, can't use interactive prompt
            # Write error to stderr so it's visible even when stdout is captured
            sys.stderr.write("Error: Interactive prompt requires a terminal.\n")
            sys.stderr.flush()
            return None
        # Re-raise if it's a TTY but still failed for another reason
        raise


def display_snippet_list(snippets: List[str], keyword: Optional[str] = None):
    """Display a formatted list of snippets."""
    if not snippets:
        if keyword:
            console.print(f"[yellow]No snippets found matching '{keyword}'.[/yellow]")
        else:
            console.print("[yellow]No snippets saved yet.[/yellow]")
        return
    
    table = Table(title="Snippets" + (f" (filtered: {keyword})" if keyword else ""))
    table.add_column("Name", style="cyan")
    
    for snippet_name in snippets:
        table.add_row(snippet_name)
    
    console.print(table)

