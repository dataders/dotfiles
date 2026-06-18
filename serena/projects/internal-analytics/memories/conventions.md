# Conventions

- Follow `assets/dbt-style-guide.md` plus AGENTS.md project rules.
- Model naming: `<dag_stage>_<source/topic>__<additional_context>`; common prefixes `stg_`, `int_`, `dim_`, `fct_`; `rpt_` for report-specific outputs; `base_` for pre-staging cleanup.
- Layering invariant: only staging models select from `source()`; marts and intermediate models should select via `ref()`, and marts should prefer existing `int_` models over rejoining staging logic.
- Staging column order: IDs/keys, dimensions, measures, date/time fields, metadata.
- Primary keys use `<entity>_id`; surrogate keys from `dbt_utils.generate_surrogate_key()` use `_sk`, not `_id`; booleans start `is_`/`has_`; timestamps end `_at`; dates end `_date`.
- SQL style: CTEs grouped as import CTEs then logical CTEs then `final`; select from `final`; use sparse attribution comments only for non-obvious business rules.
- YAML style: files named `_<description>__<config>.yml`; unit tests named `_<folder>__unit_tests.yml`; unit test names start `test_`; unit test rows use dict-style formatting.
- All models need primary-key `unique` + `not_null` tests unless grain truly cannot support it.
- New business terms, column naming patterns, or metric definitions should update `models/_docs/docs_glossary.md`.