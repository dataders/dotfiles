# Tech Stack

- dbt project on Snowflake; `require-dbt-version: >=1.6.0`; local profile name `garage-snowflake`.
- dbt Cloud CLI/Fusion is primary local runtime (`dbtf` in user env); dbt Cloud project id and defer env id are both `672`.
- Project paths from `dbt_project.yml`: models `models`, analyses `analysis`, tests `tests`, seeds `data`, macros `macros`, assets `assets`.
- Dependencies live in `dependencies.yml`/`package-lock.yml`; core packages include `dbt_utils`, `dbt_external_tables`, `dbt_snow_mask`, `audit_helper`, Fivetran packages for hubspot/social_media/zendesk/pendo/jira/ad platforms, plus internal projects `ga_analytics` and `vortex_event_analytics`.
- Snowmask masking policies are created on prod run start and applied as model post-hook through `dbt_snow_mask`.
- Project uses dbt model freshness config defaults (`build_after_count`, `build_after_period`) and selected hourly freshness for product dbt_wizard/litellm_gateway plus some staging sources.
- Tests store failures by default (`tests: +store_failures: true`).