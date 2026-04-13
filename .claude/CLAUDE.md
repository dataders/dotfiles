# Global Development Context

## Environment
- macOS (Apple Silicon)
- Shell: zsh with Starship prompt + Prezto
- Terminal: Ghostty
- Package manager: Homebrew
- Python: conda/miniforge3

## Python Package Management
Bare `pip`, `pip3`, and `python3` invocations are blocked by a PreToolUse hook. Always use:
- `uv run python3 -c "..."` — inline Python
- `uv run python3 script.py` — run a script
- `uv add <package>` — add a dependency to a project
- `uvx <tool>` — run a one-off tool (e.g. `uvx ruff check`)

## Dotfiles Structure
- **Public configs**: `~/Developer/dotfiles` (git-tracked, GitHub)
- **Private/secrets**: `~/Developer/dotfiles_env` (local only, not pushed)
- Symlinks managed by: `links.sh`
- **Critical symlinks in `~/.dbt/`** point to `~/Developer/dotfiles_env/.dbt/` (profiles.yml, dbt_cloud.yml, mcp.yml, keyfile.json, .user.yml). **Do NOT delete these symlinks.** If you must remove one for testing, restore it immediately when done (e.g. `ln -sf ~/Developer/dotfiles_env/.dbt/dbt_cloud.yml ~/.dbt/dbt_cloud.yml`).

## Primary Work
- dbt (data build tool) development
- Multiple dbt installations available:
  - `dbtf` - dbt Cloud CLI
  - `dbt-core` - dbt-core from venv
  - `dbtd` / `dbtr` - custom debug/release builds
- Data warehouses: Snowflake, BigQuery, Redshift, Databricks

## Preferences
- Keep changes minimal and focused
- Prefer editing existing files over creating new ones
- Use conda environments for Python projects
- Use direnv for project-specific environment variables
