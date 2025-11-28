#!/bin/bash
# Shell wrapper for Macolint (Bash)
# Add this to your ~/.bashrc:
# source /path/to/macolint/shell-wrappers/bash.sh

snip() {
  # If this is 'snip get <name>' (with name), use the wrapper behavior
  # For 'snip get' without name, let it run normally for interactive mode
  if [ "$1" = "get" ] && [ -n "$2" ]; then
    local cmd
    # Call the actual snip command with --raw flag and capture output
    cmd=$(command snip get "$2" --raw 2>/dev/null) || return
    # Add the snippet to history so it appears when user presses Up arrow
    history -s "$cmd"
    # Note: READLINE_LINE only works in key bindings, not regular functions
    # So we add to history - user can press Up arrow to retrieve the snippet
  else
    # For all other commands (including 'snip get' without name), call normally
    command snip "$@"
  fi
}

