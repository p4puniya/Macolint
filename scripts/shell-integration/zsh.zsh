# Macolint shell integration for zsh
# Add this to your ~/.zshrc

# Function to open Macolint fuzzy search
macolint-search() {
    local selected=$(snip get 2>&1)
    if [ -n "$selected" ]; then
        # The snippet is already copied to clipboard by snip get
        # You can add additional behavior here if needed
        echo "Snippet copied to clipboard: $selected"
    fi
}

# Bind to Ctrl+Shift+S (or Cmd+Shift+S on macOS)
# Note: Terminal key bindings may vary. Adjust as needed.
bindkey -s '^S' 'macolint-search\n'

# Alternative: Use zle widget for better integration
macolint-widget() {
    BUFFER="snip get"
    zle accept-line
}
zle -N macolint-widget
bindkey '^S' macolint-widget

