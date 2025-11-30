"""Main CLI entry point for Macolint."""

import sys
import os
import shutil
import click
from pathlib import Path
from rich.console import Console
from macolint.database import Database
from macolint.interactive import (
    prompt_snippet_name_simple,
    prompt_snippet_content,
    display_snippet_list,
    browse_module_tree,
    prompt_save_location,
    console,
)


db = Database()


def output_snippet_for_shell_wrapper(content: str):
    """
    Output snippet content cleanly for shell wrapper to capture.
    This is used when the shell wrapper function calls snip get.
    
    Args:
        content: The snippet content to output (will be stripped of trailing whitespace)
    """
    # Strip trailing whitespace and newlines
    content = content.rstrip()
    # Output the content without a newline (shell wrapper will handle it)
    print(content, end='')


def output_snippet_to_shell_buffer(content: str, name: str):
    """
    Output snippet content directly to shell command buffer.
    This is used when snip get is called without a name (interactive mode)
    and we need to place the snippet in the command buffer.
    
    The approach: After getting the name interactively, we re-invoke the command
    with the name by calling the shell's snip function (wrapper) via subprocess.
    However, since subprocess can't manipulate the parent shell's command buffer,
    we use a workaround: we output a command that the shell can execute.
    
    Args:
        content: The snippet content to output (will be stripped of trailing whitespace)
        name: The snippet name (used to re-invoke the command)
    """
    # Strip trailing whitespace and newlines
    content = content.rstrip()
    
    # The issue: We can't manipulate the parent shell's command buffer from Python.
    # The shell wrapper only works when called from the shell itself.
    # 
    # Solution: Output the snippet content in the same format as --raw,
    # which the shell wrapper expects. However, since the wrapper isn't involved,
    # we need to manually trigger it by outputting a command the shell can execute.
    #
    # For zsh: We can't use print -z from Python subprocess.
    # For bash: We can't use history -s from Python subprocess in a way that affects the parent.
    # For fish: We can't use commandline --replace from Python subprocess.
    #
    # The best we can do: Output the content and let the user see it.
    # The ideal solution would be to modify the shell wrapper to handle this case,
    # but that would require the wrapper to do the interactive prompt itself.
    
    # For now, just output the content using the same format as --raw
    # This ensures consistency, even though it won't be in the command buffer
    output_snippet_for_shell_wrapper(content)


def output_snippet_to_terminal(content: str, had_interactive_prompt: bool = False):
    """
    Output snippet content to terminal on the same line as the next prompt.
    The snippet will appear ready to execute after the shell prompt.
    This is the fallback behavior when shell wrapper is not used.
    
    Args:
        content: The snippet content to output (will be stripped of trailing whitespace)
        had_interactive_prompt: If True, we need to clear the interactive prompt line first
    """
    # Strip trailing whitespace and newlines
    content = content.rstrip()
    
    # Check if we're in a terminal (not being piped)
    if not sys.stdout.isatty():
        # If output is being piped, just print the content
        print(content, end='')
        return
    
    try:
        # Clear any interactive prompt output first
        if had_interactive_prompt:
            # Clear the current line (where interactive prompt might be)
            sys.stdout.write('\r\033[K')
            sys.stdout.flush()
            # Move up one line to where the command was
            sys.stdout.write('\033[1A\r\033[K')
            sys.stdout.flush()
        else:
            # Move cursor up to where the command was and clear it
            # \033[1A = move up one line
            # \r = move to beginning of line  
            # \033[K = clear from cursor to end of line
            sys.stdout.write('\033[1A\r\033[K')
            sys.stdout.flush()
        
        # Output the snippet content WITHOUT a newline
        # The shell will then output its prompt on the same line after this
        sys.stdout.write(content)
        sys.stdout.flush()
        # No newline - this allows the shell prompt to appear on the same line
        
    except Exception:
        # Fallback: just print the content if anything fails
        sys.stdout.write(content)
        sys.stdout.flush()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Macolint - A cloud-synced terminal snippet manager."""
    pass


@cli.command()
@click.argument("name", required=False)
@click.option(
    "-m",
    "--module",
    "module_path",
    required=False,
    help="Create an empty module (or nested modules) without saving a snippet.",
)
def save(name, module_path):
    """
    Save a snippet or create an empty module.
    
    \b
    SAVE SNIPPETS:
      Save a snippet at root level:
        snip save my_snippet
    
      Save a snippet in a module (creates modules automatically):
        snip save module1/snippet_name
        snip save module1/module2/nested_snippet
    
      Interactive save (browse modules to select location):
        snip save
        # Navigate through modules, type snippet name to save
    
    \b
    CREATE MODULES:
      Create an empty module:
        snip save -m module1
        snip save -m module1/module2
    
    \b
    OPTIONS:
      -m, --module MODULE_PATH    Create an empty module path instead of saving a snippet.
                                  Cannot be used together with NAME argument.
    
    \b
    EXAMPLES:
      # Save snippet at root
      snip save deploy_staging
    
      # Save snippet in module (auto-creates module1 if needed)
      snip save git/commit/template
    
      # Interactive: browse to save location
      snip save
    
      # Create empty module structure
      snip save -m project/frontend
    """
    try:
        # Module-only creation: snip save -m module1/module2
        if module_path is not None:
            if name:
                console.print(
                    "[red]Error: When using -m/--module, do not also pass a snippet NAME.[/red]"
                )
                sys.exit(1)

            db.create_module_path(module_path)
            console.print(
                f"[green]Module '{module_path}' created successfully.[/green]"
            )
            return

        # Snippet save (existing behaviour, now with path-aware names)
        # If name not provided, prompt for it with module navigation
        if not name:
            name = prompt_save_location(db)
            if not name:
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # Prompt for snippet content
        content = prompt_snippet_content()
        if content is None:
            console.print("[yellow]Cancelled.[/yellow]")
            return

        if not content.strip():
            console.print("[red]Error: Snippet content cannot be empty.[/red]")
            return

        # Save the snippet (name may be a simple name or a module path)
        created = db.save_snippet(name, content)
        if created:
            console.print(f"[green]Snippet '{name}' saved successfully.[/green]")
        else:
            console.print(f"[yellow]Snippet '{name}' updated successfully.[/yellow]")
        
        # Show sync hint if authenticated
        try:
            from macolint.auth import is_authenticated
            if is_authenticated():
                console.print("[dim]Run 'snip sync push' to sync to cloud[/dim]")
        except Exception:
            # Ignore errors in sync hint (auth might not be configured)
            pass

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("name", required=False)
@click.option(
    "--raw",
    is_flag=True,
    help="Output snippet content raw (for shell wrapper use)",
)
@click.option(
    "--interactive-name",
    is_flag=True,
    help="Output only the selected name after interactive prompt (for shell wrapper use)",
)
@click.option(
    "-m",
    "--module",
    "module_path",
    required=False,
    help="Open an interactive browser inside a module (folders for snippets).",
)
def get(name, raw, interactive_name, module_path):
    """
    Retrieve a snippet by name or browse modules interactively.
    
    \b
    GET BY NAME:
      Get snippet at root level:
        snip get my_snippet
    
      Get snippet by full path:
        snip get module1/snippet_name
        snip get module1/module2/nested_snippet
    
    \b
    INTERACTIVE MODES:
      Fuzzy search (shows all snippets):
        snip get
        # Type to filter, tab to complete, select snippet
    
      Browse modules (folder-style navigation):
        snip get -m              # Start at root
        snip get -m module1      # Start inside module1
        # Select modules (ending with /) to enter, select snippets to retrieve
        # Press Esc to go up one level
    
    \b
    OPTIONS:
      -m, --module [MODULE_PATH]    Open interactive module browser.
                                     If MODULE_PATH provided, starts inside that module.
                                     Cannot be used with --raw or --interactive-name.
    
      --raw                          Output snippet content without newline (for shell wrapper).
                                     Used internally, not typically used directly.
    
      --interactive-name             Output only the selected name (for shell wrapper).
                                     Used internally, not typically used directly.
    
    \b
    EXAMPLES:
      # Direct retrieval
      snip get deploy_staging
      snip get git/commit/template
    
      # Interactive fuzzy search
      snip get
    
      # Browse modules interactively
      snip get -m
      snip get -m git
    """
    try:
        # Module-browsing mode: snip get -m [module_path]
        if module_path is not None:
            if raw or interactive_name:
                console.print(
                    "[red]Error: --module cannot be used with --raw or --interactive-name.[/red]"
                )
                sys.exit(1)
            if name:
                console.print(
                    "[red]Error: When using -m/--module, do not pass a snippet NAME.[/red]"
                )
                sys.exit(1)

            # Validate starting module path (if provided)
            if module_path:
                start_module = db.get_module_by_path(module_path)
                if start_module is None:
                    console.print(
                        f"[red]Module '{module_path}' not found.[/red]"
                    )
                    sys.exit(1)

            selected_path = browse_module_tree(
                db, root_module_path=module_path if module_path else None
            )
            if not selected_path:
                console.print("[yellow]Cancelled.[/yellow]")
                return
            name = selected_path

        # If name not provided, enter classic interactive mode (global search)
        if not name:
            snippet_names = db.get_all_snippet_names()
            if not snippet_names:
                if raw or interactive_name:
                    # In raw/interactive-name mode, output nothing on error
                    sys.exit(1)
                console.print("[yellow]No snippets found.[/yellow]")
                return

            # Show interactive prompt to select snippet name
            # The prompt writes to stderr, so it will be visible even when stdout is captured
            # When --interactive-name is set, the shell wrapper is calling this via command substitution
            # The prompt should still work because stdin is still the terminal
            try:
                name = prompt_snippet_name_simple(snippet_names)
            except Exception as prompt_error:
                # If interactive prompt fails, check if it's a TTY issue
                error_str = str(prompt_error).lower()
                is_tty_error = (
                    "terminal" in error_str
                    or "tty" in error_str
                    or "not a terminal" in error_str
                )

                # Even in interactive-name mode, we should show errors on stderr
                # so the user knows what went wrong
                if interactive_name:
                    # Write error to stderr (visible) but still exit with error code
                    sys.stderr.write(
                        f"Error: Failed to show interactive prompt: {prompt_error}\n"
                    )
                    sys.stderr.flush()
                    sys.exit(1)

                if raw:
                    # In raw mode, fail silently
                    sys.exit(1)

                if is_tty_error:
                    console.print(
                        "[red]Error: Interactive mode requires a terminal.[/red]"
                    )
                    console.print(
                        "[yellow]Please provide a snippet name: snip get <name>[/yellow]"
                    )
                else:
                    console.print(
                        f"[red]Error: Failed to show interactive prompt: {prompt_error}[/red]"
                    )
                    console.print(
                        "[yellow]Make sure you're running this in a terminal.[/yellow]"
                    )
                sys.exit(1)

            if not name:
                if raw or interactive_name:
                    # In raw/interactive-name mode, output nothing on cancel
                    sys.exit(1)
                console.print("[yellow]Cancelled.[/yellow]")
                return

            # If --interactive-name flag is set, output only the name and exit
            # This is used by the shell wrapper to get the name, then it will
            # call snip get <name> --raw to get the content
            if interactive_name:
                print(name, end="")
                return

        # Retrieve the snippet (supports hierarchical module paths)
        snippet = db.get_snippet(name)
        if snippet is None:
            if raw:
                # In raw mode, output nothing on error
                sys.exit(1)
            
            # Check if user is authenticated and prompt for cloud pull
            try:
                from macolint.auth import is_authenticated
                if is_authenticated():
                    console.print(f"[yellow]Snippet '{name}' not found locally.[/yellow]")
                    if click.confirm("Pull from cloud?", default=False):
                        try:
                            from macolint.sync import sync_pull
                            import getpass
                            
                            passphrase = getpass.getpass("Enter passphrase to decrypt snippets: ")
                            if passphrase:
                                pulled, errors = sync_pull(passphrase)
                                if pulled > 0:
                                    console.print(f"[green]Pulled {pulled} snippets from cloud.[/green]")
                                    # Try to get the snippet again
                                    snippet = db.get_snippet(name)
                                    if snippet is None:
                                        console.print(f"[red]Snippet '{name}' still not found after sync.[/red]")
                                        sys.exit(1)
                                    # Continue to output snippet below
                                else:
                                    console.print(f"[yellow]No snippets pulled. Snippet '{name}' not found.[/yellow]")
                                    sys.exit(1)
                            else:
                                console.print("[yellow]Passphrase required. Cancelled.[/yellow]")
                                sys.exit(1)
                        except Exception as e:
                            console.print(f"[red]Error pulling from cloud: {e}[/red]")
                            sys.exit(1)
                    else:
                        console.print(f"[red]Snippet '{name}' not found.[/red]")
                        sys.exit(1)
                else:
                    console.print(f"[red]Snippet '{name}' not found.[/red]")
                    sys.exit(1)
            except Exception:
                # If auth check fails, just show not found
                console.print(f"[red]Snippet '{name}' not found.[/red]")
                sys.exit(1)

        # Output the snippet content
        # If --raw flag is set, output without newline (for shell wrapper)
        # Otherwise, output with newline for direct use
        if raw:
            output_snippet_for_shell_wrapper(snippet.content)
        else:
            # When called directly (not through shell wrapper), print with newline
            # so the content is visible after the interactive prompt
            content = snippet.content.rstrip()
            print(content)

    except Exception as e:
        if raw or interactive_name:
            # In raw/interactive-name mode, don't output error messages
            sys.exit(1)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('name', required=False)
def update(name):
    """
    Update the content of an existing snippet.
    
    \b
    USAGE:
      Update snippet by name:
        snip update my_snippet
        snip update module1/snippet_name
    
      Interactive update (select snippet to update):
        snip update
        # Select snippet from list, then edit content
    
    \b
    WORKFLOW:
      1. Select snippet (interactive or by name)
      2. Editor opens with existing content as default
      3. Edit content and save, or press Esc to cancel
    
    \b
    EXAMPLES:
      # Update by name
      snip update deploy_staging
      snip update git/commit/template
    
      # Interactive selection
      snip update
    
    \b
    NOTE:
      This command only updates snippet content, not names or locations.
      Use 'snip rename' to rename snippets or move them between modules.
    """
    try:
        # If name not provided, enter interactive mode
        if not name:
            snippet_names = db.get_all_snippet_names()
            if not snippet_names:
                console.print("[yellow]No snippets found.[/yellow]")
                return
            
            name = prompt_snippet_name_simple(snippet_names)
            if not name:
                console.print("[yellow]Cancelled.[/yellow]")
                return
        
        # Get existing snippet
        snippet = db.get_snippet(name)
        if snippet is None:
            console.print(f"[red]Snippet '{name}' not found.[/red]")
            sys.exit(1)
        
        # Prompt for new content with existing content as default
        new_content = prompt_snippet_content(existing_content=snippet.content)
        if new_content is None:
            console.print("[yellow]Changes discarded.[/yellow]")
            return
        
        if not new_content.strip():
            console.print("[red]Error: Snippet content cannot be empty.[/red]")
            return
        
        # Update the snippet
        updated = db.update_snippet(name, new_content)
        if updated:
            console.print(f"[green]Snippet '{name}' updated successfully.[/green]")
        else:
            console.print(f"[red]Failed to update snippet '{name}'.[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("name", required=False)
@click.option(
    "-m",
    "--module",
    "module_path",
    required=False,
    help="Delete an entire module (and its sub-modules/snippets) instead of a single snippet.",
)
def delete(name, module_path):
    """
    Delete a snippet or an entire module tree.
    
    \b
    DELETE SNIPPETS:
      Delete snippet by name:
        snip delete my_snippet
        snip delete module1/snippet_name
    
      Interactive delete (select snippet):
        snip delete
        # Select snippet from list, confirm deletion
    
    \b
    DELETE MODULES:
      Delete entire module and all contents:
        snip delete -m module1
        snip delete -m module1/module2
    
      WARNING: Module deletion is permanent and cascades to:
        - All child modules (recursively)
        - All snippets in the module and sub-modules
        - Cannot be undone
    
    \b
    OPTIONS:
      -m, --module MODULE_PATH    Delete an entire module tree instead of a snippet.
                                   Cannot be used together with NAME argument.
    
    \b
    EXAMPLES:
      # Delete snippet
      snip delete old_snippet
      snip delete module1/snippet_name
      
      # Delete module (with confirmation prompt)
      snip delete -m old_module
      snip delete -m module1/submodule
    
    \b
    SAFETY:
      All deletions require confirmation before proceeding.
    """
    try:
        # Module deletion takes precedence when --module is used
        if module_path is not None:
            if name:
                console.print(
                    "[red]Error: When using -m/--module, do not also pass a snippet NAME.[/red]"
                )
                sys.exit(1)

            # Confirm module deletion with cascade
            confirm = click.confirm(
                f"Are you sure you want to delete module '{module_path}' and all its contents?"
            )
            if not confirm:
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return

            deleted = db.delete_module_tree(module_path)
            if deleted:
                console.print(
                    f"[green]Module '{module_path}' and its contents deleted successfully.[/green]"
                )
            else:
                console.print(f"[red]Module '{module_path}' not found.[/red]")
                sys.exit(1)
            return

        # Snippet deletion (existing behaviour)
        # If name not provided, enter interactive mode
        if not name:
            snippet_names = db.get_all_snippet_names()
            if not snippet_names:
                console.print("[yellow]No snippets found.[/yellow]")
                return

            name = prompt_snippet_name_simple(snippet_names)
            if not name:
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # Confirm deletion
        confirm = click.confirm(f"Are you sure you want to delete snippet '{name}'?")
        if not confirm:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

        # Delete the snippet
        deleted = db.delete_snippet(name)
        if deleted:
            console.print(f"[green]Snippet '{name}' deleted successfully.[/green]")
        else:
            console.print(f"[red]Snippet '{name}' not found.[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('old_path', required=False)
@click.argument('new_path', required=False)
@click.option(
    '-m',
    '--module',
    'is_module',
    is_flag=True,
    help='Rename a module instead of a snippet.',
)
def rename(old_path, new_path, is_module):
    """
    Rename a snippet or module, or move it to a different location.
    
    \b
    RENAME SNIPPETS:
      Rename at root level:
        snip rename old_name new_name
    
      Rename in module (stays in same module):
        snip rename module1/old_name new_name
        snip rename module1/old_name module1/new_name
    
      Move snippet to different module:
        snip rename module1/snippet module2/snippet
        snip rename root_snippet module1/moved_snippet
    
    \b
    RENAME MODULES:
      Rename module:
        snip rename -m module1 module2
        snip rename -m module1/sub module1/new_sub
    
      Move module to different parent:
        snip rename -m module1/sub module2/moved_sub
    
      NOTE: Renaming a module automatically updates all child paths.
    
    \b
    INTERACTIVE MODE:
      Interactive rename (prompts for old and new paths):
        snip rename          # For snippets
        snip rename -m       # For modules
    
    \b
    OPTIONS:
      -m, --module    Rename a module instead of a snippet.
                      If not specified, auto-detects based on old_path.
    
    \b
    EXAMPLES:
      # Rename snippet
      snip rename old_snippet new_snippet
      snip rename module1/snippet new_name
      
      # Move snippet
      snip rename module1/snippet module2/snippet
      
      # Rename module
      snip rename -m old_module new_module
      snip rename -m module1/sub module1/renamed_sub
      
      # Move module
      snip rename -m module1/sub module2/moved_sub
      
      # Interactive
      snip rename
      snip rename -m
    """
    try:
        # Auto-detect if it's a module or snippet if -m not specified
        if not is_module and old_path:
            # Check if old_path is a module
            module = db.get_module_by_path(old_path)
            if module is not None:
                is_module = True
                console.print(f"[yellow]Detected '{old_path}' as a module. Use -m flag to be explicit.[/yellow]")

        # If old_path not provided, prompt for it
        if not old_path:
            if is_module:
                # For modules, list all modules
                all_modules = db.list_modules()
                if not all_modules:
                    console.print("[yellow]No modules found.[/yellow]")
                    return
                console.print("[cyan]Select module to rename:[/cyan]")
                old_path = prompt_snippet_name_simple(all_modules)
            else:
                # For snippets, list snippets
                snippet_names = db.get_all_snippet_names()
                if not snippet_names:
                    console.print("[yellow]No snippets found.[/yellow]")
                    return
                old_path = prompt_snippet_name_simple(snippet_names)
            
            if not old_path:
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # If new_path not provided, prompt for it
        if not new_path:
            if is_module:
                console.print("[cyan]Enter new module path (or just new name to rename in place):[/cyan]")
            else:
                console.print("[cyan]Enter new snippet path (or just new name to rename in place):[/cyan]")
            new_path = prompt_snippet_name_simple([])  # Allow free-form input
            if not new_path:
                console.print("[yellow]Cancelled.[/yellow]")
                return

        # Remove trailing / if present (for consistency)
        if old_path.endswith("/"):
            old_path = old_path[:-1]
        if new_path.endswith("/"):
            new_path = new_path[:-1]

        # Perform rename
        if is_module:
            success = db.rename_module(old_path, new_path)
            if success:
                console.print(f"[green]Module '{old_path}' renamed to '{new_path}' successfully.[/green]")
            else:
                console.print(f"[red]Failed to rename module '{old_path}'. Module not found or new path conflicts.[/red]")
                sys.exit(1)
        else:
            success = db.rename_snippet(old_path, new_path)
            if success:
                console.print(f"[green]Snippet '{old_path}' renamed to '{new_path}' successfully.[/green]")
            else:
                console.print(f"[red]Failed to rename snippet '{old_path}'. Snippet not found or new path conflicts.[/red]")
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('keyword', required=False)
@click.option(
    '-m',
    '--module',
    'module_path',
    required=False,
    help='List contents of a specific module instead of root level.',
)
def list(keyword, module_path):
    """
    List snippets and modules at a specific level.
    
    \b
    LIST ROOT LEVEL:
      List all top-level items:
        snip list
      
      Filter by keyword:
        snip list git
        snip list deploy
    
    \b
    LIST MODULE CONTENTS:
      List contents of a specific module:
        snip list -m module1
        snip list -m module1/module2
      
      List module with keyword filter:
        snip list -m module1 deploy
    
    \b
    OUTPUT FORMAT:
      - Modules are shown with trailing "/" (in yellow)
      - Snippets are shown as full paths (in cyan)
      - Only direct children are shown (not nested descendants)
      - Sorted alphabetically
    
    \b
    OPTIONS:
      -m, --module MODULE_PATH    List contents of a specific module instead of root level.
    
    \b
    EXAMPLES:
      # List root level
      snip list
      snip list git
      
      # List module contents
      snip list -m module1
      snip list -m module1/module2
      snip list -m module1 deploy
    """
    try:
        # Determine which module to list (None = root)
        target_module = None
        if module_path:
            target_module = db.get_module_by_path(module_path)
            if target_module is None:
                console.print(f"[red]Module '{module_path}' not found.[/red]")
                sys.exit(1)
        
        # Get direct children of the target module
        child_modules = db.get_module_children(target_module)
        child_snippets = db.list_snippets_in_module(target_module)
        
        # Build module paths
        if target_module is None:
            # At root: just module names
            module_paths = [m.name for m in child_modules]
        else:
            # Inside a module: show relative names (just the module name, not full path)
            module_paths = [m.name for m in child_modules]
        
        # Build snippet paths (these are already full paths from list_snippets_in_module)
        snippet_paths = child_snippets
        
        # Apply keyword filter if provided
        if keyword:
            keyword_lower = keyword.lower()
            module_paths = [m for m in module_paths if keyword_lower in m.lower()]
            snippet_paths = [s for s in snippet_paths if keyword_lower in s.lower()]
        
        # Show modules with a trailing "/" to distinguish them
        entries = [f"{m}/" for m in module_paths] + snippet_paths
        # Stable sort so modules and snippets are mixed alphabetically
        entries = sorted(entries)

        # Build title to show which module we're listing
        if target_module is None:
            title = "Snippets" + (f" (filtered: {keyword})" if keyword else "")
        else:
            module_full_path = db.get_module_full_path(target_module)
            title = f"Snippets in {module_full_path}" + (f" (filtered: {keyword})" if keyword else "")
        
        # Use a custom display function or modify the existing one
        if not entries:
            if keyword:
                console.print(f"[yellow]No items found matching '{keyword}' in '{module_full_path if target_module else '/'}'.[/yellow]")
            else:
                location = db.get_module_full_path(target_module) if target_module else "/"
                console.print(f"[yellow]No snippets or modules in '{location}'.[/yellow]")
        else:
            from rich.table import Table
            from rich.text import Text
            table = Table(title=title)
            table.add_column("Name", style="cyan")
            for entry in entries:
                # Modules (ending with /) in yellow, snippets in cyan
                if entry.endswith("/"):
                    table.add_row(Text(entry, style="yellow"))
                else:
                    table.add_row(entry)
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--shell', type=click.Choice(['bash', 'zsh', 'fish', 'auto'], case_sensitive=False), 
              default='auto', help='Shell to set up (default: auto-detect)')
@click.option('--fix-path', is_flag=True, help='Also fix PATH if snip command is not found')
@click.option('--force', is_flag=True, help='Force update even if wrapper is already installed')
def setup(shell, fix_path, force):
    """
    Automatically set up shell wrapper for seamless snippet insertion.
    
    \b
    WHAT IT DOES:
      - Adds wrapper function to your shell config file
      - Enables automatic snippet insertion into command line
      - Detects and updates outdated wrappers automatically
      - Optionally fixes PATH if snip command not found
    
    \b
    BASIC USAGE:
      Automatic setup (recommended):
        snip setup
        # Auto-detects shell, adds wrapper, provides reload instructions
    
    \b
    OPTIONS:
      --shell SHELL          Specify shell manually: bash, zsh, fish, or auto (default).
      
      --fix-path            Also fix PATH if snip command is not found.
                            Adds Python scripts directory to PATH in shell config.
      
      --force               Force update even if wrapper is already installed.
    
    \b
    EXAMPLES:
      # Automatic setup
      snip setup
      
      # Specify shell
      snip setup --shell zsh
      
      # Fix PATH and setup
      snip setup --fix-path
      
      # Force update
      snip setup --force
      
      # Combined
      snip setup --shell zsh --fix-path --force
    
    \b
    AFTER SETUP:
      Reload your shell configuration:
        source ~/.zshrc      # for zsh
        source ~/.bashrc     # for bash
        source ~/.config/fish/config.fish  # for fish
    
    \b
    HOW IT WORKS:
      After setup, when you run 'snip get <name>', the snippet content
      automatically appears in your command line buffer, ready to edit and execute.
    
    \b
    FEATURES:
      - Idempotent: safe to run multiple times
      - Smart detection: finds existing installations
      - Auto-update: detects outdated wrappers
      - No duplicates: won't create duplicate entries
    """
    try:
        # Check if snip command is in PATH
        snip_in_path = shutil.which('snip') is not None
        
        if not snip_in_path:
            console.print("[yellow]⚠ Warning: 'snip' command not found in PATH[/yellow]")
            console.print("[yellow]This might prevent the shell wrapper from working correctly.[/yellow]")
            
            # Try to find where snip is installed
            scripts_path = _get_python_scripts_path()
            if scripts_path and (scripts_path / 'snip').exists():
                console.print(f"[cyan]Found snip at: {scripts_path / 'snip'}[/cyan]")
                console.print(f"[cyan]But {scripts_path} is not in your PATH[/cyan]")
                
                if fix_path:
                    # Auto-detect shell for PATH fix
                    if shell == 'auto':
                        shell_name = os.environ.get('SHELL', '').split('/')[-1]
                        if shell_name in ['bash', 'zsh', 'fish']:
                            shell = shell_name
                        elif 'zsh' in shell_name.lower():
                            shell = 'zsh'
                        elif 'bash' in shell_name.lower():
                            shell = 'bash'
                        elif 'fish' in shell_name.lower():
                            shell = 'fish'
                    
                    if shell in ['bash', 'zsh', 'fish']:
                        _fix_path_in_shell_config(shell, scripts_path)
                    else:
                        console.print("[yellow]Could not auto-detect shell for PATH fix.[/yellow]")
                        console.print(f"[yellow]Manually add this to your shell config:[/yellow]")
                        console.print(f"[cyan]  export PATH=\"{scripts_path}:$PATH\"[/cyan]")
                else:
                    console.print("")
                    console.print("[yellow]To fix this, run:[/yellow]")
                    console.print(f"[cyan]  snip setup --fix-path[/cyan]")
                    console.print("")
                    console.print("[yellow]Or manually add to your shell config:[/yellow]")
                    console.print(f"[cyan]  export PATH=\"{scripts_path}:$PATH\"[/cyan]")
                    console.print("")
            
        # Auto-detect shell if not specified
        if shell == 'auto':
            shell_name = os.environ.get('SHELL', '').split('/')[-1]
            if shell_name in ['bash', 'zsh', 'fish']:
                shell = shell_name
            else:
                # Try to detect from common shells
                if 'zsh' in shell_name.lower():
                    shell = 'zsh'
                elif 'bash' in shell_name.lower():
                    shell = 'bash'
                elif 'fish' in shell_name.lower():
                    shell = 'fish'
                else:
                    console.print("[yellow]Could not auto-detect shell. Please specify with --shell option.[/yellow]")
                    console.print("[yellow]Supported shells: bash, zsh, fish[/yellow]")
                    return
        
        # Get wrapper code for the shell
        wrapper_code = _get_wrapper_code(shell)
        if not wrapper_code:
            console.print(f"[red]Unsupported shell: {shell}[/red]")
            return
        
        # Determine config file path
        config_file = _get_shell_config_file(shell)
        if not config_file:
            console.print(f"[red]Could not determine config file for {shell}[/red]")
            return
        
        # Check if wrapper is already installed
        wrapper_status = _check_wrapper_status(config_file, shell, wrapper_code)
        
        if wrapper_status == 'installed' and not force:
            console.print(f"[green]✓ Shell wrapper already installed in {config_file}[/green]")
            console.print("[yellow]If it's not working, try reloading your shell config:[/yellow]")
            console.print(f"[cyan]  source {config_file}[/cyan]")
            console.print("")
            console.print("[yellow]To update to the latest version, run:[/yellow]")
            console.print(f"[cyan]  snip setup --force[/cyan]")
            return
        elif wrapper_status == 'outdated' or (wrapper_status == 'installed' and force):
            if wrapper_status == 'outdated':
                console.print(f"[yellow]⚠ Outdated shell wrapper detected in {config_file}[/yellow]")
                console.print("[yellow]Updating to latest version...[/yellow]")
            else:
                console.print(f"[yellow]Force updating shell wrapper in {config_file}...[/yellow]")
            _update_wrapper(config_file, wrapper_code, shell)
            console.print(f"[green]✓ Shell wrapper updated successfully![/green]")
            console.print(f"[green]Updated: {config_file}[/green]")
            console.print("")
            console.print("[yellow]To activate, reload your shell config:[/yellow]")
            if shell == 'fish':
                console.print(f"[cyan]  source {config_file}[/cyan]")
                console.print("[yellow]Or restart your terminal.[/yellow]")
            else:
                console.print(f"[cyan]  source {config_file}[/cyan]")
            console.print("")
            console.print("[green]Now you can use: snip get <name>[/green]")
            console.print("[green]The snippet will automatically appear in your command line![/green]")
            return
        
        # Create config file if it doesn't exist
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Add wrapper to config file (new installation)
        _install_wrapper(config_file, wrapper_code, shell)
        
        console.print(f"[green]✓ Shell wrapper installed successfully![/green]")
        console.print(f"[green]Added to: {config_file}[/green]")
        console.print("")
        console.print("[yellow]To activate, reload your shell config:[/yellow]")
        if shell == 'fish':
            console.print(f"[cyan]  source {config_file}[/cyan]")
            console.print("[yellow]Or restart your terminal.[/yellow]")
        else:
            console.print(f"[cyan]  source {config_file}[/cyan]")
        console.print("")
        console.print("[green]Now you can use: snip get <name>[/green]")
        console.print("[green]The snippet will automatically appear in your command line![/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# Wrapper version - increment this when the wrapper code changes
WRAPPER_VERSION = "2.5"

def _get_wrapper_code(shell: str) -> str:
    """Get the wrapper code for the specified shell."""
    version_str = f"v{WRAPPER_VERSION}"
    wrappers = {
        'bash': f'''# Macolint shell wrapper (Bash) - {version_str}
snip() {{
  # Find the actual snip command, using python3 -m macolint.cli as fallback
  local snip_cmd
  snip_cmd=$(command -v snip 2>/dev/null) || snip_cmd="python3 -m macolint.cli"
  
  # If this is 'snip get' (with or without name), use the wrapper behavior
  if [ "${{1}}" = "get" ]; then
    # If second arg looks like an option (starts with -), fall back to normal call
    if [ -n "${{2}}" ] && [[ "${{2}}" == -* ]]; then
      "$snip_cmd" "${{@}}"
    elif [ -n "${{2}}" ]; then
      # Has name: get snippet directly
      local cmd
      cmd=$("$snip_cmd" get "${{2}}" --raw 2>/dev/null) || return $?
      if [ -n "${{cmd}}" ]; then
        history -s "${{cmd}}"
      fi
    else
      # No name: do interactive prompt to get name, then get snippet content
      # Step 1: Get the name from interactive prompt
      # The interactive prompt writes to stderr (visible), name goes to stdout (captured)
      local name
      name=$("$snip_cmd" get --interactive-name) || return $?
      # Step 2: If we got a name, get the snippet content and add to history
      if [ -n "${{name}}" ]; then
        local cmd
        cmd=$("$snip_cmd" get "${{name}}" --raw 2>/dev/null) || return $?
        if [ -n "${{cmd}}" ]; then
          history -s "${{cmd}}"
        fi
      fi
    fi
  else
    # For all other commands, call normally
    "$snip_cmd" "${{@}}"
  fi
}}
''',
        'zsh': f'''# Macolint shell wrapper (Zsh) - {version_str}
snip() {{
  # Find the actual snip command, bypassing this function
  # Use 'whence -p' which only finds actual commands, not functions
  # Fall back to python3 -m macolint.cli if not found
  local snip_cmd
  snip_cmd=$(whence -p snip 2>/dev/null) || snip_cmd="python3 -m macolint.cli"
  
  # If this is 'snip get' (with or without name), use the wrapper behavior
  if [ "${{1}}" = "get" ]; then
    # If second arg looks like an option (starts with -), fall back to normal call
    if [ -n "${{2}}" ] && [[ "${{2}}" == -* ]]; then
      "$snip_cmd" "${{@}}"
    elif [ -n "${{2}}" ]; then
      # Has name: get snippet directly
      local cmd
      cmd=$("$snip_cmd" get "${{2}}" --raw 2>/dev/null) || return $?
      if [ -n "${{cmd}}" ]; then
        print -z "${{cmd}}"
      fi
    else
      # No name: do interactive prompt to get name, then get snippet content
      # Step 1: Get the name from interactive prompt
      # The interactive prompt writes to stderr (visible), name goes to stdout (captured)
      local name
      name=$("$snip_cmd" get --interactive-name) || return $?
      # Step 2: If we got a name, get the snippet content and place in command buffer
      if [ -n "${{name}}" ]; then
        local cmd
        cmd=$("$snip_cmd" get "${{name}}" --raw 2>/dev/null) || return $?
        if [ -n "${{cmd}}" ]; then
          print -z "${{cmd}}"
        fi
      fi
    fi
  else
    # For all other commands, call normally
    "$snip_cmd" "${{@}}"
  fi
}}
''',
        'fish': f'''# Macolint shell wrapper (Fish) - {version_str}
function snip
    # If this is 'snip get' (with or without name), use the wrapper behavior
    if [ "${{argv[1]}}" = "get" ]
        # If second arg looks like an option (starts with -), fall back to normal call
        if [ (count $argv) -ge 2 -a (string match -q -- '-' (string sub -s 1 -l 1 $argv[2])) ]
            command snip $argv
        else if [ -n "${{argv[2]}}" ]
            # Has name: get snippet directly
            set cmd (command snip get "${{argv[2]}}" --raw 2>/dev/null)
            if test $status -eq 0
                commandline --replace $cmd
            end
        else
            # No name: do interactive prompt to get name, then get snippet content
            # Step 1: Get the name from interactive prompt (prompt goes to stderr, name to stdout)
            # In fish, command substitution captures both stdout and stderr, but we only want stdout
            # So we redirect stderr to /dev/null and capture stdout
            set name (command snip get --interactive-name 2>/dev/null)
            if test $status -eq 0
                # Step 2: If we got a name, get the snippet content and replace command line
                if test -n "$name"
                    set cmd (command snip get "$name" --raw 2>/dev/null)
                    if test $status -eq 0
                        if test -n "$cmd"
                            commandline --replace $cmd
                        end
                    end
                end
            end
        end
    else
        # For all other commands, call normally
        command snip $argv
    end
end
'''
    }
    return wrappers.get(shell, '')


def _get_shell_config_file(shell: str) -> Path:
    """Get the config file path for the specified shell."""
    home = Path.home()
    config_files = {
        'bash': home / '.bashrc',
        'zsh': home / '.zshrc',
        'fish': home / '.config' / 'fish' / 'config.fish'
    }
    return config_files.get(shell)


def _check_wrapper_status(config_file: Path, shell: str, current_wrapper_code: str) -> str:
    """
    Check the status of the wrapper installation.
    Returns: 'not_installed', 'installed', or 'outdated'
    """
    if not config_file.exists():
        return 'not_installed'
    
    try:
        content = config_file.read_text()
        # Check for the wrapper function signature
        has_wrapper = False
        if shell == 'fish':
            has_wrapper = 'function snip' in content and 'Macolint shell wrapper' in content
        else:
            has_wrapper = 'snip()' in content and 'Macolint shell wrapper' in content
        
        if not has_wrapper:
            return 'not_installed'
        
        # Check version - extract version from current wrapper code
        import re
        version_match = re.search(r'v(\d+\.\d+)', current_wrapper_code)
        if version_match:
            current_version = version_match.group(1)
            # Check if installed version matches current version
            installed_version_match = re.search(r'v(\d+\.\d+)', content)
            if installed_version_match:
                installed_version = installed_version_match.group(1)
                # Simple version comparison (assumes semantic versioning)
                # Split version into parts and compare
                try:
                    installed_parts = [int(x) for x in installed_version.split('.')]
                    current_parts = [int(x) for x in current_version.split('.')]
                    
                    # Compare major, then minor
                    for i in range(max(len(installed_parts), len(current_parts))):
                        installed_val = installed_parts[i] if i < len(installed_parts) else 0
                        current_val = current_parts[i] if i < len(current_parts) else 0
                        
                        if installed_val < current_val:
                            return 'outdated'
                        elif installed_val > current_val:
                            return 'installed'
                    
                    # Versions are equal
                    return 'installed'
                except (ValueError, IndexError):
                    # Fallback to string comparison if parsing fails
                    if installed_version != current_version:
                        return 'outdated'
                    return 'installed'
        
        # If we can't determine version, check if it has the latest features
        # (e.g., support for 'snip get' without arguments)
        if shell == 'fish':
            # Check for interactive mode support (handles both with and without name)
            if 'if [ "$argv[1]" = "get" ]' in content and 'if [ -n "$argv[2]" ]' in content:
                return 'installed'
        else:
            # Check for interactive mode support
            if 'if [ "$1" = "get" ]; then' in content or 'if [ "$1" = "get" ]' in content:
                if 'if [ -n "$2" ]; then' in content or 'if [ -n "$2" ]' in content:
                    return 'installed'
        
        # If wrapper exists but doesn't have latest features, it's outdated
        return 'outdated'
        
    except Exception:
        return 'not_installed'


def _is_wrapper_installed(config_file: Path, shell: str) -> bool:
    """Check if the wrapper is already installed in the config file."""
    status = _check_wrapper_status(config_file, shell, _get_wrapper_code(shell))
    return status in ['installed', 'outdated']


def _install_wrapper(config_file: Path, wrapper_code: str, shell: str):
    """Install the wrapper code into the config file."""
    # Read existing content
    existing_content = ''
    if config_file.exists():
        existing_content = config_file.read_text()
    
    # Add separator and wrapper code
    separator = '\n'
    if existing_content and not existing_content.endswith('\n'):
        separator = '\n\n'
    
    new_content = existing_content + separator + wrapper_code
    
    # Write back to file
    config_file.write_text(new_content)


def _update_wrapper(config_file: Path, new_wrapper_code: str, shell: str):
    """Update the existing wrapper code in the config file."""
    if not config_file.exists():
        # If file doesn't exist, just install it
        _install_wrapper(config_file, new_wrapper_code, shell)
        return
    
    try:
        content = config_file.read_text()
        
        # Find and remove the old wrapper
        # The wrapper is between the comment and the closing brace/end
        import re
        
        if shell == 'fish':
            # For fish: match from "# Macolint shell wrapper" to "end"
            pattern = r'# Macolint shell wrapper.*?^end\n'
        else:
            # For bash/zsh: match from "# Macolint shell wrapper" to closing brace
            pattern = r'# Macolint shell wrapper.*?^}\n'
        
        # Remove the old wrapper
        updated_content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        
        # Clean up any extra blank lines
        updated_content = re.sub(r'\n\n\n+', '\n\n', updated_content)
        
        # Add the new wrapper
        separator = '\n'
        if updated_content and not updated_content.endswith('\n'):
            separator = '\n\n'
        
        new_content = updated_content + separator + new_wrapper_code
        
        # Write back to file
        config_file.write_text(new_content)
        
    except Exception as e:
        # If update fails, fall back to append
        console.print(f"[yellow]Warning: Could not cleanly update wrapper: {e}[/yellow]")
        console.print("[yellow]Appending new wrapper instead...[/yellow]")
        _install_wrapper(config_file, new_wrapper_code, shell)


def _get_python_scripts_path() -> Path:
    """Get the Python scripts directory where snip is installed."""
    try:
        import sysconfig
        scripts_path = Path(sysconfig.get_path('scripts'))
        if (scripts_path / 'snip').exists():
            return scripts_path
    except Exception:
        pass
    
    # Fallback: try common locations
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    common_paths = [
        Path(f"/Library/Frameworks/Python.framework/Versions/{python_version}/bin"),
        Path.home() / ".local" / "bin",
        Path("/usr/local/bin"),
    ]
    
    for path in common_paths:
        if (path / 'snip').exists():
            return path
    
    return None


def _fix_path_in_shell_config(shell: str, scripts_path: Path):
    """Add Python scripts directory to PATH in shell config file."""
    config_file = _get_shell_config_file(shell)
    if not config_file:
        return False
    
    path_export = f'export PATH="{scripts_path}:$PATH"'
    
    # Check if already added
    if config_file.exists():
        content = config_file.read_text()
        if str(scripts_path) in content:
            console.print(f"[yellow]PATH already configured in {config_file}[/yellow]")
            return True
    
    # Add PATH export
    existing_content = ''
    if config_file.exists():
        existing_content = config_file.read_text()
    
    separator = '\n'
    if existing_content and not existing_content.endswith('\n'):
        separator = '\n\n'
    
    path_comment = f'# Add Python scripts to PATH (for Macolint)\n{path_export}'
    new_content = existing_content + separator + path_comment + '\n'
    
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(new_content)
    
    console.print(f"[green]✓ Added {scripts_path} to PATH in {config_file}[/green]")
    console.print("[yellow]Reload your shell config or restart terminal for changes to take effect.[/yellow]")
    return True


@cli.group()
def auth():
    """Authentication commands for cloud sync."""
    pass


@auth.command()
def login():
    """
    Log in to enable cloud sync.
    
    \b
    This command will:
    1. Open your browser to Supabase authentication
    2. Guide you through copying your access token
    3. Store your session securely for cloud sync
    
    \b
    After logging in, you can use:
      snip sync push    # Upload snippets to cloud
      snip sync pull    # Download snippets from cloud
    
    \b
    EXAMPLE:
      snip auth login
    """
    try:
        from macolint.auth import login as auth_login
        success = auth_login()
        if not success:
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@auth.command()
def logout():
    """
    Log out and clear local session.
    
    \b
    This will remove your authentication session.
    You'll need to log in again to use cloud sync.
    
    \b
    EXAMPLE:
      snip auth logout
    """
    try:
        from macolint.auth import logout as auth_logout
        auth_logout()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.group()
def sync():
    """Cloud sync commands."""
    pass


@sync.command()
def push():
    """
    Push local snippets to the cloud (encrypted).
    
    \b
    This command will:
    1. Encrypt all local snippets using your passphrase
    2. Upload them to Supabase
    3. Show a summary of what was synced
    
    \b
    You must be logged in (run 'snip auth login' first).
    You'll be prompted for your passphrase.
    
    \b
    EXAMPLE:
      snip sync push
    """
    try:
        from macolint.auth import is_authenticated
        from macolint.sync import sync_push
        import getpass
        
        if not is_authenticated():
            console.print("[red]Error: Not logged in.[/red]")
            console.print("[yellow]Run 'snip auth login' first.[/yellow]")
            sys.exit(1)
        
        # Prompt for passphrase
        passphrase = getpass.getpass("Enter passphrase to encrypt snippets: ")
        if not passphrase:
            console.print("[red]Error: Passphrase cannot be empty.[/red]")
            sys.exit(1)
        
        # Push snippets
        pushed, errors = sync_push(passphrase)
        
        if errors > 0:
            console.print(f"\n[yellow]Pushed {pushed} snippets with {errors} errors.[/yellow]")
        else:
            console.print(f"\n[green]✓ Successfully pushed {pushed} snippets to cloud.[/green]")
        
        if pushed == 0 and errors == 0:
            console.print("[yellow]No snippets to sync.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@sync.command()
def pull():
    """
    Pull snippets from the cloud and decrypt locally.
    
    \b
    This command will:
    1. Download all your encrypted snippets from Supabase
    2. Decrypt them using your passphrase
    3. Save them to your local database
    
    \b
    You must be logged in (run 'snip auth login' first).
    You'll be prompted for your passphrase.
    
    \b
    EXAMPLE:
      snip sync pull
    """
    try:
        from macolint.auth import is_authenticated
        from macolint.sync import sync_pull
        import getpass
        
        if not is_authenticated():
            console.print("[red]Error: Not logged in.[/red]")
            console.print("[yellow]Run 'snip auth login' first.[/yellow]")
            sys.exit(1)
        
        # Prompt for passphrase
        passphrase = getpass.getpass("Enter passphrase to decrypt snippets: ")
        if not passphrase:
            console.print("[red]Error: Passphrase cannot be empty.[/red]")
            sys.exit(1)
        
        # Pull snippets
        pulled, errors = sync_pull(passphrase)
        
        if errors > 0:
            console.print(f"\n[yellow]Pulled {pulled} snippets with {errors} errors.[/yellow]")
            if errors > 0:
                console.print("[yellow]Some snippets failed to decrypt. Check your passphrase.[/yellow]")
        else:
            console.print(f"\n[green]✓ Successfully pulled {pulled} snippets from cloud.[/green]")
        
        if pulled == 0 and errors == 0:
            console.print("[yellow]No snippets found on server.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def set_passphrase():
    """
    Set up your encryption passphrase for cloud sync.
    
    \b
    This command helps you set up a passphrase that will be used to
    encrypt your snippets before uploading to the cloud.
    
    \b
    IMPORTANT:
    - Your passphrase is NEVER stored or sent to the server
    - You must remember it to decrypt snippets on other devices
    - If you forget it, you cannot recover your encrypted snippets
    
    \b
    EXAMPLE:
      snip set-passphrase
    """
    try:
        import getpass
        
        console.print("[bold]Set up encryption passphrase[/bold]\n")
        console.print("[yellow]This passphrase will be used to encrypt your snippets.[/yellow]")
        console.print("[yellow]You must remember it to decrypt snippets on other devices.[/yellow]\n")
        
        passphrase1 = getpass.getpass("Enter passphrase: ")
        if not passphrase1:
            console.print("[red]Error: Passphrase cannot be empty.[/red]")
            sys.exit(1)
        
        passphrase2 = getpass.getpass("Confirm passphrase: ")
        if passphrase1 != passphrase2:
            console.print("[red]Error: Passphrases do not match.[/red]")
            sys.exit(1)
        
        console.print("\n[green]✓ Passphrase set successfully![/green]")
        console.print("[yellow]Remember: You'll need this passphrase to sync snippets across devices.[/yellow]")
        console.print("[yellow]Your passphrase is not stored - you must remember it.[/yellow]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def doctor():
    """
    Diagnose and report issues with Macolint installation.
    
    \b
    WHAT IT CHECKS:
      ✓ snip command in PATH
      ✓ Shell wrapper installation status
      ✓ Database accessibility
      ✓ Snippet count
    
    \b
    WHAT IT PROVIDES:
      - Detailed status of each component
      - Actionable recommendations
      - Commands to run for fixes
    
    \b
    WHEN TO USE:
      - After installation to verify setup
      - When 'snip' command is not found
      - When shell wrapper is not working
      - When experiencing unexpected errors
    
    \b
    EXAMPLE OUTPUT:
      Macolint Doctor
      
      ✓ snip command found: /usr/local/bin/snip
      ✓ Shell wrapper installed for zsh
        Config file: /Users/username/.zshrc
      ✓ Database accessible (15 snippets)
    
    \b
    USAGE:
      snip doctor
      
      # If snip not in PATH, use:
      python3 -m macolint.cli doctor
    """
    console.print("[bold]Macolint Doctor[/bold]")
    console.print("")
    
    # Check if snip is in PATH
    snip_path = shutil.which('snip')
    scripts_path = _get_python_scripts_path()
    use_module_syntax = False
    
    if snip_path:
        console.print(f"[green]✓ snip command found: {snip_path}[/green]")
        command_prefix = "snip"
    else:
        console.print("[red]✗ snip command not found in PATH[/red]")
        if scripts_path:
            console.print(f"[yellow]  Found snip at: {scripts_path / 'snip'}[/yellow]")
            console.print(f"[yellow]  But {scripts_path} is not in PATH[/yellow]")
            use_module_syntax = True
            command_prefix = "python3 -m macolint.cli"
        else:
            console.print("[red]  Could not locate snip command[/red]")
            console.print("[yellow]  Try reinstalling: pip3 install -e .[/yellow]")
            command_prefix = "python3 -m macolint.cli"
            use_module_syntax = True
    
    console.print("")
    
    # Check shell wrapper
    shell_name = os.environ.get('SHELL', '').split('/')[-1]
    if 'zsh' in shell_name.lower():
        shell = 'zsh'
    elif 'bash' in shell_name.lower():
        shell = 'bash'
    elif 'fish' in shell_name.lower():
        shell = 'fish'
    else:
        shell = None
    
    wrapper_installed = False
    if shell:
        config_file = _get_shell_config_file(shell)
        if config_file and _is_wrapper_installed(config_file, shell):
            console.print(f"[green]✓ Shell wrapper installed for {shell}[/green]")
            console.print(f"[green]  Config file: {config_file}[/green]")
            wrapper_installed = True
        else:
            console.print(f"[yellow]⚠ Shell wrapper not installed for {shell}[/yellow]")
    else:
        console.print("[yellow]⚠ Could not detect shell type[/yellow]")
    
    console.print("")
    
    # Check database
    try:
        from macolint.database import Database
        db = Database()
        count = len(db.get_all_snippet_names())
        console.print(f"[green]✓ Database accessible ({count} snippets)[/green]")
    except Exception as e:
        console.print(f"[red]✗ Database error: {e}[/red]")
    
    console.print("")
    
    # Provide actionable recommendations
    if not snip_path or not wrapper_installed:
        console.print("[bold]Recommended Actions:[/bold]")
        console.print("")
        
        if not snip_path and scripts_path:
            console.print("[cyan]1. Fix PATH and set up shell wrapper:[/cyan]")
            console.print(f"[cyan]   {command_prefix} setup --fix-path[/cyan]")
            console.print("")
            console.print("[cyan]   Then reload your shell:[/cyan]")
            if shell == 'zsh':
                console.print("[cyan]   source ~/.zshrc[/cyan]")
            elif shell == 'bash':
                console.print("[cyan]   source ~/.bashrc[/cyan]")
            elif shell == 'fish':
                console.print("[cyan]   source ~/.config/fish/config.fish[/cyan]")
            console.print("")
        elif not wrapper_installed:
            console.print("[cyan]1. Set up shell wrapper:[/cyan]")
            console.print(f"[cyan]   {command_prefix} setup[/cyan]")
            console.print("")
        
        if use_module_syntax:
            console.print("[yellow]Note: Until PATH is fixed, use: python3 -m macolint.cli [command][/yellow]")
            console.print("")


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()

