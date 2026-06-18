# Task Completion

- For dbt model/SQL/YAML edits: run scoped `dbtf parse` or `dbtf compile --select <changed_model>` first, then `dbtf build --select <changed_model>+` or narrower run/test if runtime cost is high.
- For model column/grain/materialization changes: check downstream impact first with dbt-index lineage/impact; validate primary-key uniqueness/not-null expectations.
- For new or modified models: ensure YAML docs exist and primary key has `unique` + `not_null`; add/update glossary for new business terms.
- Before PR handoff: review `git diff`, confirm generated/package/target artifacts are untouched unless intentional, and use diff-review workflow when requested or before opening PR.
- If Serena memories changed, user can run `serena memories check` from project root to validate references.