ln -sf "$(pwd)/.vscode/settings.json" "/Users/dataders/Library/Application Support/Code - Insiders/User/settings.json"
ln -sf "$(pwd)/.vscode/settings.json" "/Users/dataders/Library/Application Support/Code/User/settings.json"
ln -sf "$(pwd)/.vscode/settings.json" "/Users/dataders/Library/Application Support/Cursor/User/settings.json"
# ln -s './mongod.conf'  '/opt/homebrew/etc/mongod.conf'

# Individual config files (can't symlink entire directories like .config or .claude)
mkdir -p ~/.config/ghostty
ln -sf "$(pwd)/.config/ghostty/config" ~/.config/ghostty/config
ln -sf "$(pwd)/.config/starship.toml" ~/.config/starship.toml
ln -sf "$(pwd)/.config/wt.toml" ~/.config/wt.toml
mkdir -p ~/.claude/hooks
ln -sf "$(pwd)/.claude/hooks/enforce-uv.sh" ~/.claude/hooks/enforce-uv.sh
ln -sf "$(pwd)/.claude/settings.json" ~/.claude/settings.json
ln -sf "$(pwd)/.claude/settings.local.json" ~/.claude/settings.local.json
ln -sf "$(pwd)/.claude/statusline.sh" ~/.claude/statusline.sh
ln -sf "$(pwd)/.claude/CLAUDE.md" ~/.claude/CLAUDE.md
ln -sf "$(pwd)/.claude.json" ~/.claude.json
ln -sf "$(pwd)/.tmux.conf" ~/.tmux.conf
mkdir -p ~/.cargo
ln -sf "$(pwd)/.cargo/config.toml" ~/.cargo/config.toml

mkdir -p ~/.codex
ln -sf "$(pwd)/.codex/config.toml" ~/.codex/config.toml
mkdir -p ~/credentials
ln -sf ~/Developer/dotfiles_env/credentials/fusion.env.json ~/credentials/fusion.env.json

# dbt config symlinks (source of truth: dotfiles_env/.dbt/)
mkdir -p ~/.dbt
ln -sf ~/Developer/dotfiles_env/.dbt/profiles.yml ~/.dbt/profiles.yml
ln -sf ~/Developer/dotfiles_env/.dbt/dbt_cloud.yml ~/.dbt/dbt_cloud.yml
ln -sf ~/Developer/dotfiles_env/.dbt/mcp.yml ~/.dbt/mcp.yml
ln -sf ~/Developer/dotfiles_env/.dbt/keyfile.json ~/.dbt/keyfile.json
ln -sf ~/Developer/dotfiles_env/.dbt/.user.yml ~/.dbt/.user.yml