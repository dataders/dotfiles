---
name: fusion-diary
description: |
  Draft a Fusion Diary post — the periodic community update for dbt's Fusion compiler project. Use this skill whenever the user says "fusion diary", "write a diary", "draft a diary", "new diary post", or asks to summarize what's new in Fusion for the community. Also trigger when the user asks to compile Fusion release notes, Fusion progress updates, or a community-facing summary of dbt-fusion changes. The skill handles finding the baseline (most recent prior diary), pulling from GitHub, Slack, and Notion, and producing a structured draft in the correct voice.
---

# Fusion Diary Skill

You are drafting the next **Fusion Diary** — a community-facing post that summarizes what is new in dbt's Fusion compiler project since the last published diary. The audience is dbt community members: developers, data engineers, and power users who follow Fusion's progress.

## Step 1: Determine the baseline

Start by identifying the most recent prior diary. The canonical list (newest-first):

- **March 26, 2026** — Notion draft: https://www.notion.so/Fusion-Diaries-March-26-2026-cf84590ce15c4ae5b8f4f65413a5a327
- **February 13, 2026** — GitHub Discussion #1306: https://github.com/dbt-labs/dbt-fusion/discussions/1306
- **November 20, 2025** — GitHub Discussion #1038: https://github.com/dbt-labs/dbt-fusion/discussions/1038
- **October 10, 2025** — GitHub Discussion #889: https://github.com/dbt-labs/dbt-fusion/discussions/889
- **September 29, 2025** — GitHub Discussion #837: https://github.com/dbt-labs/dbt-fusion/discussions/837
- **September 22, 2025** — GitHub Discussion #792: https://github.com/dbt-labs/dbt-fusion/discussions/792

Fetch the most recent diary to confirm its publication date and covered window. That date becomes the **start of the new reporting window**. Everything you include in this diary should be new or materially updated *after* that baseline.

Also check whether any dragons (known bugs) or works-in-progress from the previous diary have since been resolved — these deserve explicit call-outs in the new post.

## Step 2: Gather signals — work these in parallel

Pull from all available sources. Cast a wide net first, then filter for signal.

### GitHub — dbt-fusion (public)
- **Releases page**: https://docs.getdbt.com/docs/fusion/fusion-releases — check this *first* for release count, channels, and known-bad versions. This is your primary velocity data source.
- **Active milestones**: https://github.com/dbt-labs/dbt-fusion/milestones — check which milestones are open and how much is closed vs. open.
- Use GitHub search tools to find closed issues and merged PRs in the reporting window. Do *not* try to construct date-filtered URLs — use the search tools directly.

### GitHub — fs repo (private, internal)
The `dbt-labs/fs` repo contains the Fusion engine source, changelogs, and most merged PRs. Direct URL visits will 404, but GitHub MCP tools (`pull_request_read`, `search_code`, `list_commits`, etc.) work fine. Pull merged PRs, changelog entries, and notable commits in the reporting window.

### Slack (priority order — start with the top two)
1. **#announcements-fusion** — shipped features, regressions, major updates (highest signal)
2. **#dev-fusion** — release engineering, CI/CD, technical context (highest signal)
3. **#project-fusion** — project-level updates
4. **#team-fs-vscode** — VSCE/LSP changes (check if time allows)
5. **#team-fs-adapters** — adapter-specific changes (check if time allows)
6. **#team-fs-cli-core** — CLI/core changes (check if time allows)

If internal Slack context is included in the post, paraphrase it and strip anything sensitive or internal-only.

### Notion
Pull any relevant internal notes, planning pages, or status updates that provide context for the diary.

## Step 3: Select what to include

Apply these filters before writing:

- **Signal over completeness.** If the list is long, summarize the pattern and highlight the most important items. Do not dump a raw list.
- **Community-safe.** Omit anything internal-only that would confuse or be inappropriate for the community. Paraphrase internal Slack/Notion context.
- **Link everything externally visible.** PRs, issues, GitHub discussions, release notes.
- **Previous dragons and WIPs.** If something was listed as a dragon or WIP in the last diary and it's now resolved, celebrate it explicitly.

## Step 4: Write the diary

### Voice
Write like a thoughtful human who works on Fusion and genuinely cares about developer experience. The tone is:
- **Frank and behind-the-curtain**: share real status, not just marketing wins
- **High-signal, fast-paced**: lead with a TL;DR and concrete numbers
- **Playful but not forced**: seasonal metaphors, the occasional meme or pop-culture aside — but only when they land naturally
- **Builder-empathetic**: anchor on developer flow, mention UX rough edges honestly
- **Community-inviting**: acknowledge contributors by name when possible; ask for feedback when appropriate

Avoid marketing language. Short paragraphs and bullets. No fluff.

### Recurring themes to watch for
When you're deciding what rises to "Big Rock" level or deserves emphasis, these themes matter most to the diary's audience:

1. **Performance and feedback loops** — compile speed, incremental/lazy compilation, query cache, editor responsiveness
2. **Static analysis as product** — correctness guarantees, IntelliSense, red squiggles, when static analysis is disabled and what that means
3. **Feature parity / path to GA** — preview vs beta vs alpha status, remaining milestones
4. **Ecosystem compatibility** — package conformance, migration tooling (dbt-autofix, agentic workflows)
5. **Warehouse and platform specifics** — Snowflake Iceberg, BigQuery MVs, Databricks features, catalog.json, docs generate
6. **Observability and reliability** — execution summaries, logging, OpenTelemetry, failure modes and why they happen

### Required structure (always include, in this order)

```
## Intro
[Themed opener that sets the vibe — a seasonal metaphor, a timely reference, something that gives the diary its personality]

## Velocity
[TL;DR numbers: issues closed, PRs merged, preview releases shipped in this window. Pull from the releases page and GitHub search.]

## 🪨 Big Rocks
[Major shipped features. For each big rock:]
- **What shipped** — concrete description
- **Why it matters** — developer impact
- **Sharp edges / migration notes** — if applicable
- **Links** — PRs, issues, discussions

## 🚧 Work in progress
[Features currently underway but not yet shipped. Be honest about status.]

## 🏁 Made it to the meme
[A Fusion- or dbt-related meme, joke, or playful close. Keep it earned.]
```

### Optional sections (include only if there's real content)

- **Community Contributions** — notable community activity; Slack contributors count if available; GitHub issues opened by community members
- **🐉 Dragons** — known bugs, gotchas, footguns. Name them plainly; explain what's broken and why
- **👓 Stuff you should read** — recommended reading (docs, posts, discussions)
- **🤔 Looking for feedback** — explicit asks for community input
- **p.s. one more thing...** — teaser or Easter egg

## Step 5: Review before delivering

Before presenting the draft, do a quick self-check:

- Does the velocity section have real numbers (not placeholders)?
- Is every big rock linked to something externally visible?
- Have you addressed previous dragons / WIPs from the last diary?
- Is the tone frank and candid — or did it drift toward marketing-speak?
- Are there any internal details that shouldn't be public?

If the user asks for revisions (tone, additional sources, different emphasis), apply them and present the updated draft.
