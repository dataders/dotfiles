# ShadowTraffic ClickHouse Lab

Local ShadowTraffic to ClickHouse setup for testing ClickHouse materialized
views in `/Users/dataders/Developer/fs.clickhouse-clean-materialized-views`.

## Private License

Keep the ShadowTraffic license in the private repo:

```sh
mkdir -p ~/Developer/dotfiles_env/shadowtraffic
chmod 700 ~/Developer/dotfiles_env/shadowtraffic
shadowtraffic-clickhouse license-template > ~/Developer/dotfiles_env/shadowtraffic/license.env
chmod 600 ~/Developer/dotfiles_env/shadowtraffic/license.env
```

Fill `license.env` with the ShadowTraffic license values. Do not commit it.

## Commands

```sh
shadowtraffic-clickhouse setup
shadowtraffic-clickhouse start --for 30m --then destroy
shadowtraffic-clickhouse status
shadowtraffic-clickhouse stop
shadowtraffic-clickhouse destroy
```

`setup` starts only ClickHouse and creates `shadowtraffic.events`.
`start` also starts ShadowTraffic and streams JSON events into that table.
`--for` accepts bare seconds, `s`, `m`, `h`, or `d`. `--then destroy` deletes the
ClickHouse volume after the timer fires; use `--then stop` to keep data. The
timer runs as a one-shot Docker CLI container named
`shadowtraffic-clickhouse-timer`.

## dbt Project

The lab includes a small dbt project:

```sh
shadowtraffic-clickhouse dbt-parse
shadowtraffic-clickhouse dbt-run
shadowtraffic-clickhouse dbt-run mv_event_type_counts --full-refresh
```

`models/sources.yml` declares `source('shadowtraffic', 'events')`.
`models/mv_event_type_counts.sql` is a minimal materialized view model for the
local fs debug binary.

## Direct Checks

```sh
shadowtraffic-clickhouse sample 5
shadowtraffic-clickhouse query "SELECT count() FROM shadowtraffic.events"
shadowtraffic-clickhouse sql
shadowtraffic-clickhouse source-yml
```
