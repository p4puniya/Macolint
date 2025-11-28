#!/bin/zsh
# Shell wrapper for Macolint (Zsh)
# Add this to your ~/.zshrc:
# source /path/to/macolint/shell-wrappers/zsh.sh

snip() {
  # If this is 'snip get <name>' (with name), use the wrapper behavior
  # For 'snip get' without name, let it run normally for interactive mode
  if [ "$1" = "get" ] && [ -n "$2" ]; then
    local cmd
    # Call the actual snip command with --raw flag and capture output
    cmd=$(command snip get "$2" --raw 2>/dev/null) || return
    # Place the output into the command buffer for the next prompt
    # This makes it appear in the command line automatically
    print -z "$cmd"
  else
    # For all other commands (including 'snip get' without name), call normally
    command snip "$@"
  fi
}

