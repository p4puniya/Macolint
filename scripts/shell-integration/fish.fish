# Macolint shell integration for fish
# Add this to your ~/.config/fish/config.fish

# Function to open Macolint fuzzy search
function macolint-search
    set selected (snip get 2>&1)
    if test -n "$selected"
        # The snippet is already copied to clipboard by snip get
        # You can add additional behavior here if needed
        echo "Snippet copied to clipboard: $selected"
    end
end

# Bind to Ctrl+Shift+S
bind \cs macolint-search

