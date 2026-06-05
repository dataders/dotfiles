# Raycast

Personal Raycast setup documentation — what's in use, how it's backed up, and new habits in progress.

## Sync strategy

Raycast settings are synced via **Raycast Cloud Sync** (Pro feature, Settings → Advanced → Cloud Sync). This handles extensions, quicklinks, snippets, hotkeys, AI commands, and window layouts across machines automatically.

For git history, a `.rayconfig` export lives here. To keep it diffable, the export passphrase is set to blank (Settings → Extensions → Raycast → Export Settings & Data).

```bash
# Re-export after making changes in Raycast:
cp ~/Downloads/Raycast.rayconfig ~/Developer/dotfiles/raycast/

# To diff the contents:
gunzip -S .rayconfig -c raycast/Raycast.rayconfig | jq .

# To restore on a new machine:
open raycast/Raycast.rayconfig   # triggers Raycast import dialog
```

Scripts live in `dotfiles/.raycast_scripts/` and Raycast is configured to read them directly from that path — no symlink needed.

## Snippets as code

Text-expansion snippets are kept as a plain, diffable source-of-truth in
[`snippets.json`](snippets.json) — separate from the binary `.rayconfig` so
individual snippets show up in `git diff` and can be reviewed/edited directly.

```bash
# Edit snippets.json, then push the definitions into Raycast:
./raycast/import-snippets.sh   # opens one "Import Snippets" confirmation dialog
```

Each entry is `{ "name", "keyword", "text" }`. Raycast skips any snippet whose
name/text/keyword already exists, so re-running the import is safe and
idempotent. Under the hood the script builds Raycast's import deeplink
(`raycast://snippets/import?snippet=<url-encoded-json>`, one repeated `snippet=`
param per entry).

| Keyword | Expands to |
|---|---|
| `m13n` | materialization |
| `aeng` | analytics engineer |

## Current habits

### Launcher basics
- **Cmd+Space** — open Raycast
- App switching, file search, calculator all through Raycast (no Spotlight)

### Window Management
- Built-in Raycast extension, replaces Rectangle/Magnet
- Assigned shortcuts in Raycast → Extensions → Window Management

### Calendar & meetings
- Built-in Calendar extension shows upcoming events
- **Calendly** extension → "Share Meeting Link" to copy the right booking URL by type

### GitHub
- GitHub extension in menu bar: live PR list
- Search PRs, notifications, repos from Raycast

### Clipboard History
- Full clipboard history with search
- OCR: screenshots copied to clipboard become searchable text automatically

### Scripts (in `dotfiles/.raycast_scripts/`)
- **Call with iPhone** — dial a number via iPhone relay
- **Format GitHub Link as Markdown** — converts a GitHub URL in clipboard to `[repo#123](url)` format

### AI
- **Quick AI** (Cmd+Space → type a question) for fast lookups
- **Raycast AI Chat** for longer conversations
- `@web` in AI chat for live web search context
- `@selected-text` to pull highlighted text into the conversation
- `@calendar` to inject live calendar data (see new habits below)

### Productivity
- **Timers** — menu bar timer, quick countdown setup
- **Pomodoro** — menu bar Pomodoro tracker
- **Coffee** — keep Mac awake during long runs/deploys
- **Search dbt Docs** — keyword search directly into dbt documentation

### Search
- **Search Menu Items** — execute any frontmost app menu item by name (see hotkey below)
- **Search Files** — find files faster than Spotlight

## Hyper Key

Caps Lock is remapped to **Hyper** (Cmd+Ctrl+Opt+Shift) when held, **Escape** when tapped alone. Configured in `karabiner/karabiner.json`.

This gives a collision-free namespace for personal shortcuts:

| Chord | Action |
|---|---|
| Hyper+M | Search Menu Items |
| Hyper+F | Start Focus Session |
| Hyper+W+[arrow] | Window management |
| Hyper+1 | Deep Work session script (planned) |
| Hyper+2 | Meetings session script (planned) |

### Setting up Search Menu Items → Hyper+M
1. Raycast → Settings → Extensions → find **Search Menu Items**
2. Click the hotkey field → press Caps Lock+M (recorded as Hyper+M)
3. Done — from any app, Hyper+M opens a searchable list of that app's menu items

### Setting up Send to AI Chat shortcuts
Two built-in commands worth assigning hotkeys:
- **Send Active Window Screenshot to AI Chat** → suggest Hyper+Shift+W
- **Send Selected Area Screenshot to AI Chat** → suggest Hyper+Shift+S

In Raycast → Settings → Extensions → Screenshots (or Raycast AI), assign the hotkeys.
Use case: screenshot a terminal error or Snowflake query plan → AI Chat context instantly.

## New habits in progress

See GitHub issues in [dataders/dotfiles](https://github.com/dataders/dotfiles/issues) for detailed setup steps:

| Feature | Issue | Status |
|---|---|---|
| Raycast Focus for deep work blocks | [#12](https://github.com/dataders/dotfiles/issues/12) | planned |
| `@calendar` chaining in AI chat | [#13](https://github.com/dataders/dotfiles/issues/13) | planned |
| Dynamic snippets (`{argument}`, date math) | [#14](https://github.com/dataders/dotfiles/issues/14) | planned |
| Shell deeplinks → AI commit/PR messages | [#15](https://github.com/dataders/dotfiles/issues/15) | planned |
| Session scripts for context switching | [#16](https://github.com/dataders/dotfiles/issues/16) | planned |

### Quick wins to try first

**Dynamic snippet** — add `;;today` expanding to `{date format="yyyy-MM-dd"}` for ISO dates in PRs and standups.

**`@calendar` in AI chat** — next time you're scheduling something, open AI Chat and try: `@calendar any 2-hour blocks this week good for a long dbt build?`

**`aipr` shell alias** (from issue #15) — the fastest ROI of the bunch once AI Commands are configured:
```zsh
aipr() {
  git log main..HEAD --oneline | pbcopy
  open -g "raycast://ai-commands/generate-pr-description"
}
```
