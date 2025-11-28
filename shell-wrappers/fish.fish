# Shell wrapper for Macolint (Fish)
# Add this to your ~/.config/fish/config.fish:
# source /path/to/macolint/shell-wrappers/fish.fish

function snip
    # If this is 'snip get <name>' (with name), use the wrapper behavior
    # For 'snip get' without name, let it run normally for interactive mode
    if [ "$argv[1]" = "get" ] && [ -n "$argv[2]" ]
        # Call the actual snip command with --raw flag and capture output
        set cmd (command snip get "$argv[2]" --raw 2>/dev/null)
        if test $status -eq 0
            # Replace the command line with the snippet content
            commandline --replace $cmd
        end
    else
        # For all other commands (including 'snip get' without name), call normally
        command snip $argv
    end
end

