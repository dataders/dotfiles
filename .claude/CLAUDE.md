# Global Development Context

## Environment
- macOS (Apple Silicon)
- Shell: zsh with Starship prompt + Prezto
- Terminal: Ghostty
- Package manager: Homebrew
- Python: uv-managed virtual environments; conda/miniforge not used

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

## Output Style
- Respond like smart caveman. Cut all filler, keep technical substance.
  - Drop articles (a, an, the), filler (just, really, basically, actually).
  - Drop pleasantries (sure, certainly, happy to).
  - No hedging. Fragments fine. Short synonyms.
  - Technical terms stay exact. Code blocks unchanged.
  - Pattern: [thing] [action] [reason]. [next step].

## Preferences
- Keep changes minimal and focused
- Prefer editing existing files over creating new ones
- Do not use conda or miniforge; use `uv` and project virtual environments
- Use direnv for project-specific environment variables

@RTK.md
