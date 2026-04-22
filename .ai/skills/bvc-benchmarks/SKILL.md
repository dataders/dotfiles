---
name: bvc-benchmarks
description: Use when quantifying dbt Labs ROI for a Business Value Case — needed for benchmark data, business initiatives definitions, or classifying discovery pain points into value pillars and Ref IDs
---

# BVC Benchmarks & Value Framework

Reference data for dbt Labs Business Value Cases. Contains business initiatives, benchmark ranges, use case taxonomy, and output formatting rules. VEs maintain this — changes affect every seller's output.

## Business Initiatives Framework

Map every use case to one of these four initiatives:

### Revenue
- Personalized marketing / lifecycle: better customer 360 + segmentation drives upsell and cross-sell
- Pricing & revenue optimization: dynamic pricing using fresher demand and product data
- Churn reduction & retention: more accurate health scores from reliable behavioral/support data
- Speed to market: 34% improvement in new product delivery (IDC Report, 8 customers)

### Cost / Productivity
- Automate manual workflows: reduce time on recurring reporting, reconciliations, data prep
- Increase employee productivity: handle more work with same headcount, avoid FTE adds
- Rationalize tech spend: consolidate overlapping tools, remove underused infra, cut licenses
- IDC benchmarks: Analytics 44% productivity gain | Governance 40% | Data developers 36% | Business analysts 28%

### AI
- AI initiatives require trusted, governed data pipelines — dbt provides the foundation
- Data teams spending time on pipeline maintenance cannot focus on AI/ML feature work
- Reliable semantic layer enables AI agents to query trusted metrics

### Risk
- Modernize legacy systems: reduce reliance on fragile, hard-to-maintain tech
- Strengthen compliance & auditability: clearer traceability, documentation, controls
- Reduce decision/operational risk: improve reliability of critical data
- 33% reduction in data quality issues (IDC Report)

---

## Value Framework Benchmarks

### Tooling & Maintenance (T&M)

| Scenario | Metric | Range | Source |
|----------|--------|-------|--------|
| Self-Host → Cloud | FTEs to Build | 2–3 FTEs, 100% freed | Fanatics, Moody's |
| Self-Host → Cloud | Time to Build | 2.5–6 months | Fanatics, Moody's |
| Self-Host → Cloud | FTEs to Maintain | 0.5–1 FTE, 100% freed | CarGurus, Fanatics |
| Self-Host → Cloud | Hours to Onboard | 16–140 hrs, 75–90% reduction | T-Mobile, Convex |
| Self-Host → Cloud | Upgrades | 2–4/yr at 1.5hrs–4wks each, 100% eliminated | T-Mobile, Home Depot |
| Tools Consolidation | Spend Replaced | $150K–$1.6M saved, 75–100% replacement | McDonald's, Prime Therapeutics |
| Native Warehouse | FTEs to Maintain | 0.4–2 FTEs, 100% freed | Digital Turbine, Herbalife |
| IDC | Governance Efficiency | 40% | IDC Report |
| IDC | Data Platform Mgmt | 2.4 FTEs freed (51%) | IDC Report |
| IDC | Infrastructure Savings | $183K/year | IDC Report |

### Warehouse Optimization

| Scenario | Range | Notes |
|----------|-------|-------|
| Governance & Visibility | +20% cost savings | Fanatics BVA |
| Runtime Efficiency | 20–40% cost savings | Stored Procs/Python range |
| SAO lead range | 20–30% of total opportunity | 10% from enabling, +10–15% with custom config |

**Do NOT lead with 64% internal SAO or 44% EQT savings** — too high to lead with credibly.

### Business / Operational Efficiency

| Scenario | Metric | Range | Source |
|----------|--------|-------|--------|
| Collaboration Self-Host | Reduction in requests | 30–50% | Home Depot, Convex, Fanatics |
| Collaboration Self-Host | Time per request | 30–50% reduction | Home Depot, Convex, Fanatics |
| Collaboration Self-Host | Engineers per request | 50–100% reduction | Home Depot, Convex, Fanatics |
| DevEx Self-Host | Pipeline delivery time | 20–50% reduction | — |
| DevEx Self-Host | Overall dev time | 50% reduction | — |
| Data Quality Self-Host | DQ issues | 10–50% reduction | — |
| Data Quality Self-Host | Time resolving DQ issues | 50% savings | — |
| Collaboration Tools Consol | Reduction in requests | 25–50% | Finicity, TripAdvisor |
| DevEx Tools Consol | Pipeline delivery | 17–50% reduction | McDonald's, TripAdvisor |
| Data Quality Tools Consol | DQ issues | 75% reduction | TripAdvisor |
| DevEx Native Warehouse | Pipeline delivery | 50–75% reduction | Moody's, WebstaurantStore, NBA |
| DevEx Native Warehouse | Enhancement dev | 80% reduction | NBA |
| Data Quality Native Warehouse | Time resolving DQ | 50–94% savings | NBA, WebstaurantStore |

---

## Use Case Category Governance

Classify every pain point against this taxonomy before assigning a Ref ID. The Ref ID assignment must follow the pillar mapping — do not assign Ref IDs out of order.

### Tooling & Maintenance → Refs A1, A2 → Business Initiative: Cost or Risk

Activities that belong here:
- Infrastructure provisioning & config
- Orchestration config (Airflow, Prefect, Dagster, Azure Data Factory)
- Platform config (SSO/RBAC, audit trail, alerting, integrations)
- dbt version upgrades
- CI/CD pipeline maintenance
- Orchestration DAG development
- On-call coverage, internal support
- New engineer onboarding
- Tool consolidation (Collibra, Alation, Atlan, Great Expectations, Soda, Looker semantic layer, AtScale, Cube.dev, Informatica, Talend, Matillion, SSIS, Pentaho, IBM DataStage, Alteryx, Stitch/Hevo)
- Native warehouse stored procs and Python notebook admin

### Warehouse Optimization → Ref B1 → Business Initiative: Cost

Activities that belong here:
- Total dbt-driven warehouse spend + growth rate
- Failed jobs requiring re-runs (wasted compute)

### Operational Efficiency → Refs C1, C2, C3 → Business Initiative: Revenue, AI, or Risk

Three sub-categories (all map to C refs — they do NOT form separate pillars):

**Operational Efficiency (OE proper):**
- Cross-project dependency communication
- Schema change coordination
- Catalog/metadata sync
- Lineage documentation reviews
- Federated team orchestration
- "Is this data fresh?" questions
- Ad hoc requests

**Developer Efficiency (sub-category → OE):**
- New pipeline development
- Enhancements & data refreshes
- Models/data products built
- PR review (understanding impact)
- Implementing tests
- Daily development

**Data Quality (sub-category → OE):**
- Data quality issues and incident remediation
- Code re-deploys
- CI debugging
- Incident investigation

### Routing Rule

If a use case fits multiple categories → assign to the pillar with the primary financial driver.

If a use case surfaces from Gong but lacks sufficient data to quantify → classify it and list in "Use Cases Discussed in Discovery" on Page 3 (limit 3, business initiative ties only). Never put it in the main Page 3 quantification table.

---

## Reference Customers

| Customer | Deal Type |
|----------|-----------|
| McDonald's | Tools Consolidation, New Land |
| T-Mobile | Self-Host, Renewal |
| Home Depot | Self-Host, New Land |
| Fanatics | Self-Host, Expansion |
| NBA | Native Warehouse, Expansion |
| CarGurus | Self-Host, New Land |
| Moody's | Native Warehouse, Expansion |

---

## Output Formatting Rules

- **Business Initiatives (Page 1):** Max 40 words each. Tag Revenue / Cost / AI / Risk. Include source. Include 1 suggested discovery question.
- **Use Cases table (Page 2) columns:** Category | Use Case | Current State Metric Needed | Future State Metric with dbt | Benchmark | Source
- **Financial analysis:** Always show full math. Never hide assumptions.
- **Why Now (Page 4):** 3–5 sentences. Reference specific company signals, market timing, or risk triggers.
- **Comparison format:** Always show Current State vs. Future State with dbt
- **Benchmarked inputs:** Mark with 🔴 in the formula
