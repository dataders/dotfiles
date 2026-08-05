CREATE DATABASE IF NOT EXISTS shadowtraffic;

CREATE TABLE IF NOT EXISTS shadowtraffic.events
(
    event_id UUID,
    customer_id UUID,
    event_time DateTime64(3, 'UTC'),
    event_date Date MATERIALIZED toDate(event_time),
    event_type LowCardinality(String),
    sku String,
    amount Decimal(12, 2),
    quantity UInt16,
    channel LowCardinality(String),
    region LowCardinality(String),
    source LowCardinality(String),
    ingest_time DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = MergeTree
ORDER BY (event_time, event_id);
