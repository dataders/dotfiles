ln -s './settings.json' '/Users/dataders/Library/Application Support/Code - Insiders/User/settings.json'
# ln -s './mongod.conf'  '/opt/homebrew/etc/mongod.conf'

# Individual config files (can't symlink entire directories like .config or .claude)
mkdir -p ~/.config/ghostty
ln -sf "$(pwd)/.config/ghostty/config" ~/.config/ghostty/config
ln -sf "$(pwd)/.claude/settings.json" ~/.claude/settings.json