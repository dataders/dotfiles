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

    # Check if the item is one of the specific files to go to homebrew
    if [[ $base_item == "odbcinst.ini" || $base_item == "odbc.ini" || $base_item == "freetds.conf" ]]; then
        ln -sf "$item" "/opt/homebrew/etc/$base_item"
        echo "symlinked $base_item to /opt/homebrew/etc/"
    # Otherwise check if it starts with . or ends with .conf/.ini for home directory
    elif [[ $base_item == .* || $base_item == *.conf || $base_item == *.ini ]]; then
        ln -sf "$item" "$HOME/$base_item"
        echo "symlinked $base_item to home directory"
    fi
done

echo "Symlinks created successfully."