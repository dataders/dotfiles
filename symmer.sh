#!/bin/zsh

# Get the current directory
current_dir=$(pwd)

# Loop through all files and directories in the current directory that start with a `.`
for item in $current_dir/.* $current_dir/*.conf $current_dir/*.ini; do
    # Skip the current directory (.) and parent directory (..)
    if [[ $item == "$current_dir/." || $item == "$current_dir/.." ]]; then
        continue
    fi

    # Get the base name of the item
    base_item=$(basename "$item")

    # Check if the item starts with a `.` or ends with `.conf` or `.ini`
    if [[ $base_item == .* || $base_item == *.conf || $base_item == *.ini ]]; then
        # Create the symlink in the home directory, overwriting any existing file or symlink
        ln -sf "$item" "$HOME/$base_item"
        echo "symlinked $base_item to home directory"
    fi
done

echo "Symlinks created successfully."