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

The existing `process_record_user` is a `switch (keycode)` with **multiple early
`return false;` paths** (`QK_MODS`, `ST_MACRO_*`, `RGB_SLD`, `HSV_*`). A hook
placed before the trailing `return true;` would silently miss every one of those
keys. The logging block therefore goes **at the very top of the function, before
the `switch`**, so every event is counted:

```c
bool process_record_user(uint16_t keycode, keyrecord_t *record) {
#ifdef CONSOLE_ENABLE
    uprintf("0x%04X,%u,%u,%u,%b,0x%02X,0x%02X,%u\n",
        keycode,
        record->event.key.row,
        record->event.key.col,
        get_highest_layer(layer_state),
        record->event.pressed,
        get_mods(),
        get_oneshot_mods(),
        record->tap.count);
#endif
    switch (keycode) {
    // ... existing cases unchanged ...
```

8 fields: keycode, row, col, layer, pressed, mods, oneshot-mods, tap-count. This
is the exact format precondition's generator documents and parses — **no header
row**, column order as above.

**Combos are deliberately omitted.** The repo has no `COMBO_ENABLE` and defines no
combos, so a `record->event.type == COMBO_EVENT` branch would be dead code and
`COMBO_EVENT` may not even be a defined enum without the feature compiled in
(compile risk). The user's "combos/shortcuts" goal is served instead by the
**mods, oneshot-mods, and tap-count fields** plus tap-dance/layer-tap data already
in the layout (`TAP_DANCE_ENABLE = yes`). If true QMK combos are wanted later,
that is a separate change (`COMBO_ENABLE = yes` + combo definitions).

**Constraint:** these files are the Oryx *source export*. The instrumentation is a
local-only divergence from Oryx — re-exporting from Oryx will overwrite it. The
`README.md` must document that console logging requires a local build and is not
round-tripped through Oryx.

### 2. Build & flash toolchain

- Add the qmk CLI to `Brewfile` (verify exact entry — Homebrew installs it via the
  `qmk/qmk/qmk` tap: `brew "qmk/qmk/qmk"`).
- **One-time prerequisite (separate from per-build):** `qmk setup zsa/qmk_firmware`
  clones ZSA's fork *and* pulls a multi-GB ARM toolchain. ZSA's fork is required —
  the Oryx export depends on ZSA's tree (`RGB_MATRIX_CUSTOM_KB`, `ORYX_ENABLE`, ZSA
  custom keycodes); upstream qmk will not compile it.
- `bin/moonlander-build` (the per-build helper) copies the `moonlander/` source into
  the fork's keymap dir and runs `qmk compile`, producing a per-revision `.bin`.

**Flashing — `qmk flash` is the primary path.** Since the qmk CLI is being
installed anyway, `qmk flash` drives DFU directly and avoids an unverified
assumption. **Do NOT assume Keymapp will file-flash an arbitrary qmk-built bin** —
`moonlander/README.md` documents a `[DFU] Supplied firmware does not match the
device` failure, and Keymapp's known-good paths are its auto-detecting **Flash**
button (Oryx firmware) or per-revision bins from the *Oryx* zip. Keymapp file-flash
of a locally-built per-rev bin may work but is **unvalidated**; the plan must test
it before relying on it, and `qmk flash` is the documented fallback. This
reconciles with the README rather than contradicting it.

### 3. Background logger + LaunchAgent

- `bin/moonlander-keylog` — runs `qmk console` **pinned to the Moonlander's
  VID:PID** via `--device` (bare `qmk console` may attach to the wrong device when
  multiple keyboards are connected; the VID:PID is discoverable from `qmk console`'s
  device list or System Information — the plan must capture the actual value, not
  assume it). Each console line carries a device-name prefix, so column 1 must be
  recovered **by extracting the 8-column CSV substring** rather than a naive
  `sed s/^.*0x/0x/` (greedy — the mods fields are also `0x..`). Use
  `grep -oE` of the full 8-field pattern (the same regex precondition documents),
  appending matches to `~/.local/share/moonlander-keylog/keylog-$(date +%Y%m%d).csv`.
  Output stays exactly 8 columns; the build/log smoke test asserts the column count.
- LaunchAgent plist `com.dataders.moonlander-keylog.plist`:
  - `RunAtLoad = true` (starts at login),
  - `KeepAlive = true` + an explicit `ThrottleInterval` (≥10s). When the board is
    unplugged `qmk console` exits and launchd respawns it; throttling keeps this a
    benign idle loop, not a tight spin. Document this expected board-absent behavior.
  - stdout/stderr to a separate debug log (not the keylog CSV).
  - **macOS first-run permission:** reading the HID console via hidapi may trigger a
    TCC / Input-Monitoring prompt. A LaunchAgent runs in the user's GUI session so
    the prompt can appear, but auto-start may silently fail until granted — the plan
    must include a documented first-run grant + re-login step and verify the agent
    actually logs afterward.
  - Tracked in dotfiles, symlinked to `~/Library/LaunchAgents/` via a new
    `links.tsv` row (group `moonlander`, visibility `public`). No prior LaunchAgent
    rows exist, so this establishes the convention; record the exact repo source
    path (`Library/LaunchAgents/com.dataders.moonlander-keylog.plist`).

Fault tolerance comes from append-only file writes plus `RunAtLoad`/`KeepAlive`;
no data is held in memory or in an app that must stay open.

### 4. Storage & privacy wiring

- Log dir: `~/.local/share/moonlander-keylog/` (outside any synced folder).
- `.gitignore`: ignore the log dir (it lives outside the repo anyway, but the
  build helper's scratch output, if any, is ignored).
- Backblaze: add the log dir to Backblaze's exclusion list (documented step;
  Backblaze exclusions are a GUI/`bzinfo` setting, surfaced in README).
- Dropbox: ensure the dir is not under `~/Dropbox` (it is not) — documented.
- **Time Machine / local snapshots:** `tmutil addexclusion ~/.local/share/moonlander-keylog`
  so the keylog is captured by neither Time Machine backups nor APFS local snapshots.
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

- Console-enabled firmware builds against ZSA's fork and flashes (via `qmk flash`,
  Keymapp file-flash only if validated); key events appear in the dated CSV.
- Each CSV line is exactly 8 columns (column-count assertion passes).
- Logger auto-starts at login and resumes after a forced kill (KeepAlive verified),
  and behaves benignly when the board is unplugged.
- macOS HID/Input-Monitoring permission granted; agent logs after re-login.
- Log dir confirmed excluded from Backblaze, Time Machine, and not under Dropbox.
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
| `.gitignore` | ignore any build scratch / stray logs | yes |
| Brewfile | qmk CLI (`qmk/qmk/qmk` tap — verify) | yes |
| Docs | `moonlander/README.md` (build/log/privacy workflow) | yes |
