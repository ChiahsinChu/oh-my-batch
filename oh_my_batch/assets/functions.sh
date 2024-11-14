
# Create a flag file that indicates that a command has been executed successfully.
checkpoint() {
    local flag_file="$1"
    shift  # Remove the first argument so $@ contains only the command and its arguments
    if [ -f "$flag_file" ]; then
        cat "$flag_file"
    else
        "$@"  # Execute the command
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            local current_time=$(date '+%Y-%m-%d %H:%M:%S')
            printf 'Command succeeded at %s\n' "$current_time" > "$flag_file"
            echo "Created flag file '$flag_file' with timestamp: $current_time"
        else
            echo "Command failed with exit code $exit_code. Did not create flag file '$flag_file'."
            return $exit_code
        fi
    fi
}