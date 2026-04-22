---
name: business-value-case
description: Use when a seller needs to generate a Business Value Case (BVC) for a dbt Labs prospect, iterate on an existing BVC, or publish a BVC to Notion
---

# Business Value Case (BVC) Generator

Builds quantified, 5-page business value cases for dbt Labs prospects. Maps discovery pain points to the 3-pillar Value Framework, quantifies exactly 6 use cases using consistent Ref IDs, and publishes to Notion after seller confirmation.

**REQUIRED BACKGROUND:** Use `bvc-benchmarks` for all benchmark data, business initiative definitions, and use case taxonomy when quantifying.

## When to Use

- "Help me build a BVC for [Company]"
- Filling in the standard BVC prompt (see Input Template below)
- Iterating on an existing BVC (update assumption, swap use case, sync Notion)
- Publishing a completed BVC to the BVC Deal Tracker

## Iron Rules — Never Violate These

1. **Exactly 6 quantified use cases** — A1, A2, B1, C1, C2, C3. No more, no fewer in the Page 3 table.
2. **Never write to Notion before seller types "publish"** — always show the confirmation summary first.
3. **Run the 8-step reconciliation checklist** before showing the confirmation summary.
4. **Ref IDs must be consistent across Page 3, Page 4, and Appendix** — numbers must match exactly.
5. **Mark all benchmarked/unconfirmed inputs with 🔴** in every formula.
6. **Hourly rate = annual salary ÷ 2,080** — no multipliers, no loaded rate adjustments.
7. **ROI = (3-yr net savings ÷ 3-yr dbt cost) × 100** — percent only, no other ROI formulas.

## Red Flags — STOP if You Notice These

- About to produce more or fewer than 6 rows in the Page 3 quantification table
- About to write to Notion without seeing "publish" from the seller
- Showing a Page 4 number that differs from Page 3 pillar subtotals
- Using an hourly rate derived from anything other than `salary ÷ 2,080`
- ROI calculation using anything other than the formula above

## Input Template

Gather all `[BRACKET]` fields before starting. If any are missing, ask for them.

```
DEAL BASICS
- Company: [Company name]
- Champion: [Name, Title]
- Industry: [e.g., Healthcare, Finance, Insurance]
- Company Size: [e.g., 500 employees, $2B revenue]

TEAM & ENVIRONMENT
- Sr. Data / Software Engineers: [exact count]
- Analysts / Analytics Engineers: [exact count]
- Current tools: [e.g., Snowflake + Airflow + dbt Core]
- Annual warehouse spend: [$X — or "unknown"]
- % of warehouse spend driven by dbt models: [e.g., 60% — or "unknown"]

TOP PAIN POINTS FROM DISCOVERY
1. [Pain point 1 — direct quote or paraphrase]
2. [Pain point 2]
3. [Pain point 3]

GONG / DOCS (optional)
- Gong link 1: [URL]

FINANCIAL ASSUMPTIONS
- Sr. Engineer salary: $[e.g., 175,000]/yr
- Analyst salary: $[e.g., 150,000]/yr
- dbt contract value: $[e.g., 126,720]/yr
- Term: [e.g., 3 years]
```

## Output Structure (5 Pages — Exact Order)

### Page 1 — Business Initiatives
4 blocks: Revenue Impact | Cost Savings | AI Readiness | Risk & Modernization

Each block contains: Initiative | Evidence | How dbt Supports It
Max 40 words per block. Tag with Revenue / Cost / AI / Risk. Include source and 1 discovery question.

### Page 2 — Use Cases by Value Pillar
3 tables:
- Tooling & Maintenance (T&M)
- Warehouse Optimization
- Operational Efficiency

Columns: Value Pillar | Use Case | Business Problem | How dbt Solves

### Page 3 — Quantification
**Main table (exactly 6 rows):**

| Ref | Pillar | Use Case | Formula | Hours Saved | $ Saved/Yr |
|-----|--------|----------|---------|-------------|------------|
| A1 | T&M | ... | ... | ... | ... |
| A2 | T&M | ... | ... | ... | ... |
| B1 | WH Opt | ... | ... | ... | ... |
| C1 | OE | ... | ... | ... | ... |
| C2 | OE | ... | ... | ... | ... |
| C3 | OE | ... | ... | ... | ... |

Then: "Use Cases Discussed in Discovery" (max 3, with business initiative ties)
Then: "Metrics Still Needed" (anything that needs seller follow-up)

### Page 4 — Financial Summary & ROI
3-year summary table:

| Row | Year 1 | Year 2 | Year 3 | 3-Yr Total |
|-----|--------|--------|--------|------------|
| T&M *(A1 + A2)* | | | | |
| Warehouse *(B1)* | | | | |
| OE *(C1 + C2 + C3)* | | | | |
| **Total Annual Savings** | | | | |
| dbt Cloud Cost | | | | |
| **Net Savings** | | | | |

Then: Connecting to Business Initiatives | Why Now section (3-5 sentences, company-specific signals)

### Appendix — Calculation Toggles (one per Ref ID)

Header format: `USE CASE [Ref ID] — [Name] (Pillar | feeds Page 4 [row] [with other refs])`

Each toggle contains:
- Input / Value / Source table
- Assumptions section
- Supporting Quotes
- Benchmarks used

## Ref ID Consistency Requirements

This is where agents break — triple-check these before presenting the confirmation summary:

- **A1 + A2 annual savings** → must equal T&M row in Page 4
- **B1 annual savings** → must equal Warehouse row in Page 4
- **C1 + C2 + C3 annual savings** → must equal OE row in Page 4
- **Each Appendix toggle** → annual savings figure must match the Page 3 row for that Ref ID

## 8-Step Pre-Publish Reconciliation Checklist

Run this BEFORE showing the confirmation summary. Fix mismatches at the source (Appendix) then propagate up.

1. Each Appendix toggle (A1–C3): annual savings matches Page 3 `$ Saved/Yr` for that Ref ID
2. Page 3 pillar subtotals: A1+A2 = T&M | B1 = WH | C1+C2+C3 = OE
3. Page 4 T&M = A1+A2 | WH = B1 | OE = C1+C2+C3 | Total = sum of all three
4. Page 4 Year 2 and Year 3 correctly compounded/carried forward
5. Page 4 3-Year Total = Year 1 + Year 2 + Year 3 for each row
6. Page 4 Net Savings = Total Annual Savings − dbt Cloud cost per year
7. ROI % = (3-yr net savings ÷ 3-yr dbt cost) × 100
8. Payback period in months = (dbt Year 1 cost ÷ Year 1 total savings) × 12

## Confirmation Workflow

After reconciliation, post exactly this format:

```
[Company] BVC | Annual Savings: $[X] | 3-Yr ROI: [X]% | Payback: ~[X] months
```

Followed by a bulleted list of all 🔴 benchmarked assumptions to validate before the exec meeting.

Then ask: "Does this look right? Reply **publish** to send to Notion, or tell me what to change."

**Do not write to Notion until seller types "publish".**

## Publishing to Notion

Once seller confirms with "publish":
- **Simultaneously** create the BVC page AND add a row to the BVC Deal Tracker
- BVC Deal Tracker: `https://www.notion.so/7c16742721684eaa9f7db2c4ad3345f8`
- Destination for BVC page: inside BVC Deal Tracker — do not ask seller for a URL
- Deal Tracker row fields: Customer | Deal Type | Seller | Date | Deal Size | T&M Total | WH Total | OE Total | BVC Page URL

## Post-Publish Verification

After publishing, fetch the live Notion BVC page and verify:
1. Page 3: all 6 Ref ID rows show correct annual savings and hours saved
2. Page 4: Total Annual Savings, 3-Year Total, Net Savings, ROI % match the confirmation summary
3. Deal Tracker row: T&M Total = A1+A2 | WH Total = B1 | OE Total = C1+C2+C3

If any number is mismatched, correct immediately and confirm the fix before sharing the link.

## Iteration Commands

| Change | Command |
|--------|---------|
| Update dbt cost | `Update dbt cost to $[X]/yr over [N] years and recalculate` |
| Update salaries | `Update Sr Engineer to $[X] and Analyst to $[Y], recalculate` |
| Update assumption | `Update assumption: [describe]. Recalculate all affected use cases and update Notion.` |
| Move to potential | `Move "[Use Case]" from confirmed to potential. Update all numbers.` |
| Add use case | `Add use case: [describe]. Champion said: "[quote]". Estimate [X hrs/wk] saved.` |
| Remove use case | `Remove "[Use Case]" from the BVC and update all numbers` |
| Sync Notion | `Update the Notion page with the latest version of the BVC` |
| Exec summary | `Write a 3-sentence executive summary of the ROI story` |
| Objection prep | `What are the 3 most likely objections to this BVC and how should I respond?` |

## For $250K+ ACV Deals

Loop in a VE before the exec meeting → #ask-biz-value channel. Standard deals can use this skill without a VE.
