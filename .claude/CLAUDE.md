# Global Development Context

## Environment
- macOS (Apple Silicon)
- Shell: zsh with Starship prompt + Prezto
- Terminal: Ghostty
- Package manager: Homebrew
- Python: conda/miniforge3

## Dotfiles Structure
- **Public configs**: `~/Developer/dotfiles` (git-tracked, GitHub)
- **Private/secrets**: `~/Developer/dotfiles_env` (local only, not pushed)
- Symlinks managed by: `links.sh`

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
- Use uv environments for Python projects
- Use direnv for project-specific environment variables
