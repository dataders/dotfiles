ln -s './settings.json' '/Users/dataders/Library/Application Support/Code - Insiders/User/settings.json'
# ln -s './mongod.conf'  '/opt/homebrew/etc/mongod.conf'

# Individual config files (can't symlink entire directories like .config or .claude)
mkdir -p ~/.config/ghostty
ln -sf "$(pwd)/.config/ghostty/config" ~/.config/ghostty/config
ln -sf "$(pwd)/.config/starship.toml" ~/.config/starship.toml
ln -sf "$(pwd)/.claude/settings.json" ~/.claude/settings.json
ln -sf "$(pwd)/.claude/CLAUDE.md" ~/.claude/CLAUDE.md
ln -sf "$(pwd)/.claude.json" ~/.claude.json