# Macolint shell integration for bash
# Add this to your ~/.bashrc or ~/.bash_profile

# Function to open Macolint fuzzy search
macolint-search() {
    local selected=$(snip get 2>&1)
    if [ -n "$selected" ]; then
        # The snippet is already copied to clipboard by snip get
        # You can add additional behavior here if needed
        echo "Snippet copied to clipboard: $selected"
    fi
}

# Bind to Ctrl+Shift+S
# Note: This requires readline configuration
bind '"\C-S": "macolint-search\n"'

