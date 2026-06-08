# Moonlander keymap (Colemak)

Source of truth for my ZSA Moonlander Mark I layout, exported from Oryx.

- Layout: `anders-colemak`
- Oryx layout: https://configure.zsa.io/moonlander/layouts/aPEmv/LZNPM/0
- These files (`config.h`, `keymap.c`, `keymap.json`, `rules.mk`) are the
  Oryx "source" export. They are **revision-agnostic** — the same source
  compiles to firmware for both Moonlander hardware revisions.

## Rev A vs Rev B (read this before flashing)

The Moonlander Mark I ships in two hardware revisions:

- **Revision A** — older boards. In bootloader mode enumerates as
  *"STM Device in DFU Mode"* / *"STM32 Bootloader"*.
- **Revision B** — started shipping **mid-December 2025**. In bootloader mode
  enumerates as *"Moonlander Bootloader"*.

Oryx now compiles **both** revisions and bundles them. The single `.bin` you
get from Oryx's "Download firmware" button is literally the revA image and the
revB image **concatenated** (~132 KB = ~65 KB revA + ~67 KB revB). That blob is
*not* a valid single-revision DFU image — feeding it to a flasher directly
fails. Let Keymapp pick the matching half for you instead.

## The flashing problem I hit (June 2026) and the fix

Symptom: Keymapp's flash failed with
`[DFU] Supplied firmware does not match the device`.

Root cause: **Keymapp was too old (1.2.12)** — it predated the revB rollout and
couldn't match the dual-revision firmware to the connected board. It was not a
corrupt download, not the layout, and not the keyboard.

Fix: **update Keymapp to ≥ 1.3.7**, then hit Flash again. The current app
auto-detects the board's revision and flashes the correct half.

## Flashing going forward

1. Keep Keymapp up to date (App Store, or `brew install --cask keymapp`).
2. Put the board in reset mode, click **Flash** in Keymapp, and let it
   auto-detect the revision. Don't hand-flash the combined `.bin`.
3. If you ever must flash by file, use the single per-revision bin from the
   Oryx source `.zip` (`zsa_moonlander_reva_*.bin` or `..._revb_*.bin`) — never
   the combined download.

## Keystroke logging (heatmap data)

These source files carry a small **console-logging instrumentation** that is
*not* part of the Oryx export: `rules.mk` has `CONSOLE_ENABLE = yes` and
`keymap.c` has a `uprintf` hook at the top of `process_record_user` that emits
one CSV line per key event (keycode, row, col, layer, pressed, mods,
oneshot-mods, tap count). The data feeds
[precondition's heatmap generator](https://precondition.github.io/qmk-heatmap)
to find most/least-used keys per layer and guide layout refinements.

**Console diverges from Oryx.** Re-exporting from Oryx overwrites `keymap.c`
and `rules.mk` and will drop the hook. Keep *layout* edits in Oryx, but
re-apply the console hook + `CONSOLE_ENABLE` locally after any re-export
(see `git log` / `git show` for this repo's instrumentation commits).

### Build & flash the console firmware

The Oryx-only path (Keymapp, above) builds upstream firmware without the hook.
To get a console-enabled build you must compile against **ZSA's qmk fork**:

```bash
qmk setup zsa/qmk_firmware   # one-time, multi-GB toolchain + fork clone
bin/moonlander-build         # copies this dir's source into the fork, qmk compile
qmk flash -kb zsa/moonlander -km anders-colemak   # board in reset first
```

`qmk` comes from the Homebrew `qmk/qmk` tap (see `Brewfile`). Confirm the
console is live with `qmk console -d 0x3297:0x1969` (Moonlander Mark I
VID:PID) — pressing keys should print `0x....,<row>,<col>,...` lines.

### Logging daemon

`bin/moonlander-keylog` runs `qmk console` pinned to the board's VID:PID,
normalizes each line to clean 8-column CSV (`grep -oE`), and appends to a dated
file under `~/.local/share/moonlander-keylog/keylog-YYYYMMDD.csv`. A KeepAlive
LaunchAgent (`Library/LaunchAgents/com.dataders.moonlander-keylog.plist`,
symlinked into `~/Library/LaunchAgents/` via `links.tsv`) keeps it running
across crashes, unplugs, and reboots. The logger's `--filter` mode reads stdin
and emits the cleaned CSV, so the normalization regex is testable without
hardware.

### Privacy

The keylog is a raw record of every keystroke, so the log directory is kept out
of every backup/sync path:

- **Time Machine** — `tmutil addexclusion ~/.local/share/moonlander-keylog`
  (verify with `tmutil isexcluded`).
- **Backblaze** — add `~/.local/share/moonlander-keylog` under
  Settings → Exclusions (GUI; Backblaze backs up the whole disk by default).
- **Dropbox** — the dir lives under `~/.local/share`, not `~/Dropbox`.
- **git** — `.gitignore` blocks `keylog-*.csv` and `moonlander/keymaps/` as a
  defensive guard against accidental in-repo copies.

Wipe all collected data at any time with `bin/moonlander-keylog-purge`.

### Analysis

Once several days of typing have accumulated, upload the dated CSV(s) to
[precondition's heatmap generator](https://precondition.github.io/qmk-heatmap)
and cross-check against Keymapp's live heatmap, then derive concrete
`anders-colemak` refinements. Purge the raw logs when done.

See the design spec and implementation plan for full detail:
- `docs/superpowers/specs/2026-06-08-moonlander-keylog-heatmap-design.md`
- `docs/superpowers/plans/2026-06-08-moonlander-keylog-heatmap.md`
