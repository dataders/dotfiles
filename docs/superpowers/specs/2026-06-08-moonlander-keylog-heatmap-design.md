# Moonlander keystroke logging → heatmap analysis

**Date:** 2026-06-08
**Status:** Design (approved for spec review)
**Goal:** Collect real, per-layer keystroke data from the ZSA Moonlander over
several days, fault-tolerantly persisted to disk, then analyze it to refine the
`anders-colemak` layout — surfacing most-used keys/combos and unused built-ins.

## Problem

The user wants data-driven Moonlander layout refinement: which keys, combos, and
shortcuts are pressed most, and which built-in QMK features / unused layer keys
to better integrate. Data must accumulate in the background over days and survive
app quits, crashes, and reboots.

An OS-level keylogger (Karabiner EventViewer, CGEventTap) is the wrong tool: it
only sees post-mapping *output* keys, losing the physical key + layer information
that layout refinement depends on, and it captures plaintext into whatever the OS
sees. The QMK firmware console, by contrast, can emit the physical key position
and active layer directly.

## Approach (decided)

Two complementary capture paths:

1. **Primary — QMK console logging → file.** Console-enabled firmware prints a
   structured CSV line per key event; a background logger appends it to a dated
   file on disk. This is the persistent, exportable, fault-tolerant record and the
   input to [precondition's QMK Heatmap Generator](https://precondition.github.io/qmk-heatmap).
2. **Cross-check — Keymapp live heatmap.** ZSA's Keymapp (already installed,
   `ORYX_ENABLE = yes`) shows a live per-layer heatmap with zero firmware change.
   Used as a sanity cross-check against the persistent log.

## Privacy (non-negotiable constraints)

The log line's first field is the **keycode**, so the CSV is a real keystroke
sequence that can reconstruct typed text (including passwords). Therefore:

- The log directory **must be excluded from Backblaze and Dropbox** (both run on
  this machine — confirmed via their LaunchAgents). Backblaze backs up the whole
  disk by default and would upload the keylog to its cloud.
- Logs are gitignored and never committed.
- A one-command **purge helper** deletes raw logs; raw logs are retained only
  until analysis is complete.

## Components

### 1. Firmware instrumentation (`moonlander/rules.mk`, `moonlander/keymap.c`)

`rules.mk`: flip `CONSOLE_ENABLE = no` → `CONSOLE_ENABLE = yes`.

`keymap.c`: add, guarded by `#ifdef CONSOLE_ENABLE`:

```c
#ifdef CONSOLE_ENABLE
#include "print.h"
#endif
```

and inside `process_record_user`, before the existing return:

```c
#ifdef CONSOLE_ENABLE
    const bool is_combo = record->event.type == COMBO_EVENT;
    uprintf("0x%04X,%u,%u,%u,%b,0x%02X,0x%02X,%u\n",
        keycode,
        is_combo ? 254 : record->event.key.row,
        is_combo ? 254 : record->event.key.col,
        get_highest_layer(layer_state),
        record->event.pressed,
        get_mods(),
        get_oneshot_mods(),
        record->tap.count);
#endif
```

8 fields: keycode, row, col, layer, pressed, mods, oneshot-mods, tap-count.

**Constraint:** these files are the Oryx *source export*. The instrumentation is a
local-only divergence from Oryx — re-exporting from Oryx will overwrite it. The
`README.md` must document that console logging requires a local build and is not
round-tripped through Oryx.

### 2. Build & flash toolchain

- Add `qmk-cli` to `Brewfile`; install it.
- `qmk setup zsa/qmk_firmware` (ZSA's fork — the Oryx export depends on ZSA's tree:
  `RGB_MATRIX_CUSTOM_KB`, `ORYX_ENABLE`, ZSA custom keycodes).
- Copy the `moonlander/` source into the fork's keymap dir, `qmk compile`,
  producing a per-revision `.bin`.
- **Flash via Keymapp's file-flash** (the rev A/B file path already documented in
  `moonlander/README.md`) — avoids dfu-util setup. Use the rev matching the board.

A helper script (`bin/moonlander-build`) encapsulates the copy + compile so the
build is one command and documented.

### 3. Background logger + LaunchAgent

- `bin/moonlander-keylog` — runs `qmk console`, normalizes each line with `sed`
  (qmk console prepends a device-name prefix that would corrupt CSV column 1;
  strip everything up to the leading `0x` keycode), and appends to
  `~/.local/share/moonlander-keylog/keylog-$(date +%Y%m%d).csv`. Output stays
  exactly 8 columns so it uploads cleanly to the heatmap generator.
- LaunchAgent plist `com.dataders.moonlander-keylog.plist`:
  - `RunAtLoad = true` (starts at login),
  - `KeepAlive = true` (restarts on crash / keyboard disconnect),
  - stdout/stderr to a separate log for debugging.
  - Tracked in dotfiles, symlinked to `~/Library/LaunchAgents/` via a new
    `links.tsv` row (group `moonlander`, visibility `public`).

Fault tolerance comes from append-only file writes plus `RunAtLoad`/`KeepAlive`;
no data is held in memory or in an app that must stay open.

### 4. Storage & privacy wiring

- Log dir: `~/.local/share/moonlander-keylog/` (outside any synced folder).
- `.gitignore`: ignore the log dir (it lives outside the repo anyway, but the
  build helper's scratch output, if any, is ignored).
- Backblaze: add the log dir to Backblaze's exclusion list (documented step;
  Backblaze exclusions are a GUI/`bzinfo` setting, surfaced in README).
- Dropbox: ensure the dir is not under `~/Dropbox` (it is not) — documented.
- `bin/moonlander-keylog-purge` — deletes all `keylog-*.csv`. One command.

### 5. Analysis (deferred ~days, separate session)

When enough data has accumulated:
1. Upload the dated CSV(s) to precondition's heatmap generator (client-side).
2. Compare against Keymapp's live heatmap.
3. Produce: most-used keys per layer, frequent combos/modtaps, under-used keys,
   and concrete `anders-colemak` refinement recommendations + unused QMK built-ins
   worth adopting.

This phase is out of scope for the build plan; it produces a report, not code.

## Out of scope (YAGNI)

- Per-line timestamps / time-of-day analysis (goal is frequency + combos, not when).
- Automated heatmap rendering pipeline — the web generator is sufficient.
- OS-level (Karabiner) capture — explicitly rejected above.
- Round-tripping the console instrumentation back into Oryx.

## Success criteria

- Console-enabled firmware flashed; key events appear in the dated CSV.
- Logger auto-starts at login and resumes after a forced kill (KeepAlive verified).
- Log dir confirmed excluded from Backblaze and not under Dropbox.
- A sample CSV uploads to the heatmap generator and renders a per-layer heatmap.
- Purge helper removes raw logs in one command.

## Repo integration summary

| Artifact | Path | Tracked |
| --- | --- | --- |
| Console flag | `moonlander/rules.mk` | yes |
| Logging hook | `moonlander/keymap.c` | yes |
| Build helper | `bin/moonlander-build` | yes |
| Logger | `bin/moonlander-keylog` | yes |
| Purge helper | `bin/moonlander-keylog-purge` | yes |
| LaunchAgent | `Library/LaunchAgents/com.dataders.moonlander-keylog.plist` (symlinked) | yes |
| `links.tsv` row | plist → `~/Library/LaunchAgents/` | yes |
| Brewfile | `qmk-cli` | yes |
| Docs | `moonlander/README.md` (build/log/privacy workflow) | yes |
