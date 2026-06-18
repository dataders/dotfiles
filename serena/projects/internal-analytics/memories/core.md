# Core

- dbt project `fishtown_internal_analytics`; dbt Cloud project/env id `672`; Snowflake profile `garage-snowflake`.
- Main source map: `models/staging` for 1:1 source cleanup, `models/marts` for consumption models, `models/export` for outbound/reporting exports, `models/semantic_models` + `models/metrics` for Semantic Layer, `models/_docs` for glossary/docs.
- Largest mart domains: product, finance, sales, snowplow, marketing, customer_success, fusion, engineering, people_ops, usage_based_pricing.
- Major staging domains: cloud_postgres, salesforce, googlesheets, github, netsuite, jira, greenhouse, metronome, incident_io, datadog.
- `macros/` contains project utilities and dbt override macros; notable subfolders: `postgres`, `snowplow`, `operations`, `dbt_default_overrides`, `fusion`, `launchdarkly`, `multicell`, `segmentation`, `vortex`.
- `selectors.yml` defines operational dbt Cloud selectors: cloud_users, coalesce, community_llm_models, salesforce, people_ops, github, customer_success, customer_support, customer_segment_rfv_sl_snapshot_weekly, incremental, learn_models.
- No `source()` calls in `models/marts/**/*.sql`; keep marts/intermediate sourcing through `ref()`.
- Read `mem:tech_stack` for dbt/package/runtime details, `mem:conventions` for modeling/style rules, `mem:suggested_commands` for commands, `mem:task_completion` before handoff.