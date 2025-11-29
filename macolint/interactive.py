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


def prompt_save_location(db: Database) -> Optional[str]:
    """
    Interactive prompt for selecting where to save a snippet.
    Shows modules (with '/') and allows navigation, then prompts for snippet name.
    Returns the full path (e.g., 'module1/module2/snippet_name') or None if cancelled.
    """
    from prompt_toolkit.output import create_output

    # Start at root
    current_module: Optional[object] = None
    module_stack: List[Optional[object]] = [None]

    while True:
        current_module = module_stack[-1]
        # Compute path label for display
        if current_module is None:
            path_label = "/"
        else:
            path_label = db.get_module_full_path(current_module)

        # Fetch children
        child_modules = db.get_module_children(current_module)
        child_snippets = db.list_snippets_in_module(current_module)

        # Build choices: modules with '/' suffix
        choices: List[str] = []
        module_map = {}

        for m in child_modules:
            label = f"{m.name}/"
            full_path = db.get_module_full_path(m)
            choices.append(label)
            module_map[label] = full_path

        # Also allow typing a new snippet name directly
        # We'll handle this in the prompt logic

        if not choices and not child_snippets:
            console.print(f"[yellow]No modules in '{path_label}'. Type a snippet name to save here.[/yellow]")

        # Setup completer and key bindings
        completer = FuzzyCompleter(WordCompleter(choices, ignore_case=True))
        kb = KeyBindings()

        @kb.add(Keys.Escape)
        def _(event):
            event.app.exit(result="__ESC__")

        try:
            output = create_output(stdout=sys.stderr)
        except Exception:
            output = None

        session = PromptSession(
            completer=completer,
            complete_while_typing=True,
            key_bindings=kb,
            mouse_support=False,
            output=output if output else None,
        )

        try:
            console.print(f"[cyan]Save in: {path_label}[/cyan]")
            console.print("[dim]Select a module (ends with '/') or type a snippet name[/dim]")
            selection = session.prompt("> ")
        except (KeyboardInterrupt, EOFError):
            selection = "__ESC__"

        if selection == "__ESC__" or not selection:
            if len(module_stack) == 1:
                return None
            # Go up one level
            module_stack.pop()
            continue

        selection = selection.strip()

        # Check if it's a module selection (ends with /)
        if selection.endswith("/"):
            # Remove trailing / and check if it matches a module
            module_name = selection[:-1]
            matching_modules = [m for m in child_modules if m.name == module_name]
            if matching_modules:
                # Enter existing sub-module
                target_module = matching_modules[0]
                module_stack.append(target_module)
                continue
            else:
                # Try fuzzy match first
                module_labels = [f"{m.name}/" for m in child_modules]
                matches = fuzzy_match(selection, module_labels)
                if matches:
                    module_name = matches[0][:-1]
                    matching_modules = [m for m in child_modules if m.name == module_name]
                    if matching_modules:
                        target_module = matching_modules[0]
                        module_stack.append(target_module)
                        continue
                
                # No existing module found - create a new one and navigate into it
                # Build the full path for the new module
                if current_module is None:
                    new_module_path = module_name
                else:
                    current_path = db.get_module_full_path(current_module)
                    new_module_path = f"{current_path}/{module_name}"
                
                # Create the module
                new_module = db.create_module_path(new_module_path)
                # Navigate into it
                module_stack.append(new_module)
                console.print(f"[green]Created module '{new_module_path}'[/green]")
                continue

        # Not a module selection - treat as snippet name
        # Build full path
        if current_module is None:
            full_path = selection
        else:
            module_path = db.get_module_full_path(current_module)
            full_path = f"{module_path}/{selection}"

        return full_path


def browse_module_tree(db: Database, root_module_path: Optional[str] = None) -> Optional[str]:
    """
    Interactive browser for modules and snippets.
    Lets the user navigate a folder-like hierarchy:
    - Shows child modules (with a trailing '/') and snippets in the current module.
    - Selecting a module enters it.
    - Pressing Esc goes up one level; Esc at the root exits.
    Returns the selected snippet's full path or None if cancelled.
    """
    from prompt_toolkit.output import create_output

    # Resolve starting module
    current_module = db.get_module_by_path(root_module_path) if root_module_path else None
    module_stack: List[Optional[object]] = [current_module]

    while True:
        current_module = module_stack[-1]
        # Compute path label for display
        if current_module is None:
            path_label = "/"
        else:
            path_label = db.get_module_full_path(current_module)

        # Fetch children
        child_modules = db.get_module_children(current_module)
        child_snippets = db.list_snippets_in_module(current_module)

        # Build choices: display_label -> (kind, value)
        choices: List[str] = []
        value_map = {}

        for m in child_modules:
            label = f"{m.name}/"
            full_path = db.get_module_full_path(m)
            choices.append(label)
            value_map[label] = ("module", full_path)

        for full_path in child_snippets:
            base_name = full_path.split("/")[-1]
            label = base_name
            # Avoid clobbering module labels; snippets and modules can share base names but
            # our schema keeps (parent_id, name) unique, so this is safe within a module.
            if label in value_map:
                label = full_path
            choices.append(label)
            value_map[label] = ("snippet", full_path)

        if not choices:
            console.print(f"[yellow]No snippets or sub-modules in '{path_label}'.[/yellow]")

        # Setup completer and key bindings for this level
        completer = FuzzyCompleter(WordCompleter(choices, ignore_case=True))
        kb = KeyBindings()

        @kb.add(Keys.Escape)
        def _(event):
            # Esc: go up one level or exit if at root
            event.app.exit(result="__ESC__")

        # Ensure prompt is visible when stdout is captured
        try:
            output = create_output(stdout=sys.stderr)
        except Exception:
            output = None

        session = PromptSession(
            completer=completer,
            complete_while_typing=True,
            key_bindings=kb,
            mouse_support=False,
            output=output if output else None,
        )

        try:
            console.print(f"[cyan]Module: {path_label}[/cyan]")
            selection = session.prompt("> ")
        except (KeyboardInterrupt, EOFError):
            # Treat these like Esc at the current level
            selection = "__ESC__"

        if selection == "__ESC__" or not selection:
            if len(module_stack) == 1:
                # At root, exit entirely
                return None
            # Go up one level
            module_stack.pop()
            # Clear line for better UX
            continue

        selection = selection.strip()
        if selection not in value_map:
            # Try fuzzy match using our own fuzzy_match helper
            matches = fuzzy_match(selection, list(value_map.keys()))
            if not matches:
                console.print(f"[red]No match for '{selection}'.[/red]")
                continue
            selection = matches[0]

        kind, value = value_map[selection]
        if kind == "module":
            # Enter sub-module
            target_module = db.get_module_by_path(value)
            if target_module is None:
                console.print(f"[red]Module '{value}' not found.[/red]")
                continue
            module_stack.append(target_module)
            continue

        # kind == "snippet"
        return value

