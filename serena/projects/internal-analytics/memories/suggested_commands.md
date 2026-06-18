# Suggested Commands

- Install/update dependencies: `dbtf deps`.
- Parse project after YAML/macro/model edits: `dbtf parse`.
- Compile scoped changes: `dbtf compile --select <selector>`.
- Run scoped model changes: `dbtf run --select <model_or_selector>`.
- Test scoped changes: `dbtf test --select <model_or_selector>`.
- Build scoped DAG when model + tests both matter: `dbtf build --select <model_or_selector>`.
- Use selectors from `selectors.yml` for job-aligned runs: `dbtf build --selector salesforce`, `dbtf build --selector incremental`, etc.
- Prefer dbt-index MCP for metadata/lineage/model details before shell grep; use `rg` for raw text and `ast-grep` only where supported grammar exists (YAML/Python/JS; this installed `ast-grep` does not support SQL).
- Darwin shell is zsh; Python commands should use `uv run python3 ...`, not bare `python3`/`pip`.