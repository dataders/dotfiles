# Moonlander Keystroke Logging → Heatmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up console-enabled Moonlander firmware that logs every physical key
press (position + layer) to a disk-backed CSV via a fault-tolerant LaunchAgent, so
several days of real typing data can be fed to precondition's heatmap generator.

**Architecture:** Flip `CONSOLE_ENABLE = yes` and add a `uprintf` hook at the top of
`process_record_user`; build against ZSA's qmk fork and flash with `qmk flash`; a
`bin/` logger runs `qmk console` pinned to the board's VID:PID, extracts clean
8-column CSV with `grep -oE`, and appends to a dated file under
`~/.local/share/moonlander-keylog/`; a `KeepAlive` LaunchAgent keeps it running
across crashes/reboots. The keylog is excluded from Backblaze/Time Machine/Dropbox,
gitignored, and purgeable.

**Tech Stack:** QMK firmware (C), ZSA qmk fork, qmk CLI (Homebrew), zsh scripts,
macOS launchd (LaunchAgent plist), `links.tsv`/`links.sh` symlink manager.

**Board facts (verified 2026-06-08):** ZSA Moonlander Mark I, USB **VID `0x3297`,
PID `0x1969`**. Layout `anders-colemak`, 4 layers (0–3). Source export lives in
`moonlander/`. Reference spec:
`docs/superpowers/specs/2026-06-08-moonlander-keylog-heatmap-design.md`.

**Manual / hardware steps (cannot be automated — flagged inline as 🔌):** installing
the multi-GB qmk toolchain, putting the board in reset and flashing, granting the
macOS HID/Input-Monitoring permission, and the Backblaze GUI exclusion.

---

## File Structure

| Path | Responsibility | Action |
| --- | --- | --- |
| `moonlander/rules.mk` | enable console feature | Modify |
| `moonlander/keymap.c` | logging hook + print.h include | Modify |
| `bin/moonlander-build` | copy source into fork + `qmk compile` | Create |
| `bin/moonlander-keylog` | `qmk console` → clean CSV appender (+ `--filter` self-test mode) | Create |
| `bin/moonlander-keylog-purge` | delete all raw logs | Create |
| `Library/LaunchAgents/com.dataders.moonlander-keylog.plist` | run logger at login, KeepAlive | Create |
| `links.tsv` | symlink plist into `~/Library/LaunchAgents/` | Modify |
| `Brewfile` | qmk CLI via `qmk/qmk` tap | Modify |
| `.gitignore` | ignore build scratch / stray logs | Modify |
| `moonlander/README.md` | build/log/privacy/analysis workflow | Modify |

---

## Task 1: qmk toolchain prerequisite (🔌 one-time, large download)

**Files:**
- Modify: `Brewfile`

- [ ] **Step 1: Add the qmk CLI to the Brewfile**

Append to `Brewfile`:

```ruby
tap "qmk/qmk"
brew "qmk"
```

- [ ] **Step 2: Install it**

Run: `brew bundle --file=Brewfile`
Expected: `qmk` on PATH. If `brew "qmk"` fails to resolve, the fully-qualified
formula is `brew install qmk/qmk/qmk` — fall back to that and use `brew "qmk/qmk/qmk"`
in the Brewfile instead.

- [ ] **Step 3: Verify the CLI**

Run: `qmk --version` and `qmk console --help | grep -- --device`
Expected: a version string (not "command not found"), and confirmation that
`console` accepts `-d/--device VID:PID` (the form Tasks 4–5 rely on).

- [ ] **Step 4: 🔌 Clone ZSA's fork + toolchain (multi-GB, one-time)**

Run: `qmk setup -y -b firmware25 zsa/qmk_firmware`
(ZSA's fork is required — the Oryx export uses `RGB_MATRIX_CUSTOM_KB`, `ORYX_ENABLE`,
and ZSA custom keycodes that upstream qmk lacks. **The fork's default branch is
`firmware25`** — confirmed via `git ls-remote --symref` on 2026-06-08. The plain
`qmk setup zsa/qmk_firmware` fails with `Remote branch master not found`, so the
`-b firmware25` is required.) Also `qmk config user.qmk_home="$HOME/qmk_firmware"`.
Expected: `~/qmk_firmware` (~1.9 GB) present; `qmk doctor` may flag non-fatal warnings
but the ARM compile still works.

- [ ] **Step 5: Commit the Brewfile change**

```bash
git add Brewfile
git commit -m "moonlander: add qmk CLI for console-enabled firmware builds"
```

---

## Task 2: Firmware instrumentation

**Files:**
- Modify: `moonlander/rules.mk` (`CONSOLE_ENABLE`)
- Modify: `moonlander/keymap.c` (include + hook at top of `process_record_user`)

- [ ] **Step 1: Enable the console feature**

In `moonlander/rules.mk`, change `CONSOLE_ENABLE = no` → `CONSOLE_ENABLE = yes`.

- [ ] **Step 2: Add the print.h include**

Near the top of `moonlander/keymap.c` (after existing includes), add:

```c
#ifdef CONSOLE_ENABLE
#include "print.h"
#endif
```

- [ ] **Step 3: Add the logging hook at the TOP of `process_record_user`**

`process_record_user` is a `switch (keycode)` with several early `return false;`
paths (`QK_MODS`, `ST_MACRO_*`, `RGB_SLD`, `HSV_*`). The hook MUST sit before the
`switch` so those keys are still counted. Insert immediately after the opening brace:

```c
bool process_record_user(uint16_t keycode, keyrecord_t *record) {
#ifdef CONSOLE_ENABLE
    uprintf("0x%04X,%u,%u,%u,%u,0x%02X,0x%02X,%u\n",
        keycode,
        record->event.key.row,
        record->event.key.col,
        get_highest_layer(layer_state),
        (unsigned int)record->event.pressed,
        get_mods(),
        get_oneshot_mods(),
        record->tap.count);
#endif
    switch (keycode) {
    // ... existing cases unchanged ...
```

Do NOT add a `COMBO_EVENT` branch — no `COMBO_ENABLE`, no combos defined; it would
be dead code and may not compile.

- [ ] **Step 4: Commit the instrumentation (build verified in Task 3)**

```bash
git add moonlander/rules.mk moonlander/keymap.c
git commit -m "moonlander: enable CONSOLE_ENABLE and log key events to HID console"
```

---

## Task 3: `bin/moonlander-build` helper + compile verification

**Files:**
- Create: `bin/moonlander-build`

- [ ] **Step 1: Write the build helper**

Create `bin/moonlander-build` (mode +x):

```bash
#!/usr/bin/env bash
# Build console-enabled Moonlander firmware from the Oryx source export.
set -euo pipefail

QMK_HOME="${QMK_HOME:-$HOME/qmk_firmware}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/moonlander"
KM_DIR="$QMK_HOME/keyboards/zsa/moonlander/keymaps/anders-colemak"

[ -d "$QMK_HOME" ] || { echo "qmk fork not found at $QMK_HOME — run 'qmk setup zsa/qmk_firmware'"; exit 1; }

mkdir -p "$KM_DIR"
for f in keymap.c config.h rules.mk keymap.json; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$KM_DIR/"
done

echo "Compiling zsa/moonlander:anders-colemak ..."
qmk compile -kb zsa/moonlander -km anders-colemak

echo "Done. Firmware bin(s) are in $QMK_HOME/ (zsa_moonlander_anders_colemak*.bin)."
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x bin/moonlander-build`

- [ ] **Step 3: Verify it compiles (proves Task 2 instrumentation is valid C)**

Run: `bin/moonlander-build`
Expected: `qmk compile` succeeds; a `zsa_moonlander_anders_colemak*.bin` is produced.
If compile fails on `uprintf`/`print.h`, the include or hook placement from Task 2 is
wrong — fix before continuing.

- [ ] **Step 4: Commit**

```bash
git add bin/moonlander-build
git commit -m "moonlander: add build helper for console firmware"
```

---

## Task 4: 🔌 Flash the console firmware (hardware)

**Files:** none (hardware action).

- [ ] **Step 1: Flash via qmk (primary path)**

Put the board in reset (small reset button / the configured `RESET` key), then run
the flash for YOUR board's revision (firmware25 splits the target into reva/revb;
rev B started shipping mid-Dec 2025). With the keg-only toolchain on PATH:
```bash
export PATH="/opt/homebrew/opt/arm-none-eabi-gcc@8/bin:/opt/homebrew/opt/arm-none-eabi-binutils/bin:/opt/homebrew/bin:$PATH"
qmk flash -kb zsa/moonlander/revb -km anders-colemak   # or .../reva
```
Both bins are already built at `~/qmk_firmware/zsa_moonlander_rev{a,b}_anders-colemak.bin`.
Expected: DFU completes; board reboots. (If unsure of your revision, the bootloader
device name tells you — see `moonlander/README.md`: "Moonlander Bootloader" = rev B,
"STM32 Bootloader" = rev A.)

Do NOT assume Keymapp will file-flash this locally-built bin — `moonlander/README.md`
documents a `[DFU] Supplied firmware does not match the device` failure. If `qmk flash`
DFU is problematic, *test* Keymapp file-flash of the single per-rev bin as a fallback,
but treat it as unvalidated.

- [ ] **Step 2: Confirm console output is live**

Run: `qmk console -d 0x3297:0x1969` and press a few keys.
Expected: lines containing `0x....,<row>,<col>,<layer>,...` appear. Ctrl-C to stop.
If nothing appears, the firmware did not flash with console enabled — re-flash.

---

## Task 5: `bin/moonlander-keylog` logger + normalizer (with self-test)

**Files:**
- Create: `bin/moonlander-keylog`

The logger has two modes: default (run `qmk console` → append clean CSV) and
`--filter` (read stdin, emit clean 8-column lines). `--filter` exists so the
normalization regex is testable without hardware.

- [ ] **Step 1: Write the logger script**

Create `bin/moonlander-keylog`:

```bash
#!/usr/bin/env bash
# Capture Moonlander HID console output as clean 8-column CSV.
#   moonlander-keylog            # run qmk console, append to dated log
#   moonlander-keylog --filter   # read stdin, emit clean CSV (for tests)
set -euo pipefail

VIDPID="0x3297:0x1969"   # ZSA Moonlander Mark I (verified 2026-06-08)
LOGDIR="$HOME/.local/share/moonlander-keylog"
# 8 fields: keycode,row,col,layer,pressed(0/1),mods,oneshotmods,tapcount
PATTERN='0x[0-9A-Fa-f]{4},[0-9]+,[0-9]+,[0-9]+,[01],0x[0-9A-Fa-f]{2},0x[0-9A-Fa-f]{2},[0-9]+'

filter() { grep -oE "$PATTERN"; }   # pulls the CSV out of qmk console's prefixed lines

if [ "${1:-}" = "--filter" ]; then
  filter
  exit 0
fi

mkdir -p "$LOGDIR"
exec qmk console -d "$VIDPID" 2>/dev/null \
  | filter \
  | while IFS= read -r line; do
      printf '%s\n' "$line" >> "$LOGDIR/keylog-$(date +%Y%m%d).csv"
    done
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x bin/moonlander-keylog`

- [ ] **Step 3: Write the failing self-test**

Create a throwaway fixture and assert the filter yields exactly one clean 8-column
line from a prefixed console line plus drops noise:

```bash
printf '%s\n' \
  'Ψ Moonlander Mark I: 0x0004,3,6,0,1,0x00,0x00,1' \
  'some unrelated console banner' \
  | bin/moonlander-keylog --filter
```

Expected output (exactly one line, exactly 8 comma fields, no prefix):
`0x0004,3,6,0,1,0x00,0x00,1`

- [ ] **Step 4: Run the self-test and assert column count**

Run:
```bash
out=$(printf 'Ψ Moonlander Mark I: 0x0004,3,6,0,1,0x00,0x00,1\nbanner line\n' | bin/moonlander-keylog --filter)
echo "$out"
[ "$(printf '%s' "$out" | awk -F, 'END{print NF}')" = "8" ] && echo "PASS: 8 columns" || { echo "FAIL"; exit 1; }
```
Expected: prints the clean line then `PASS: 8 columns`.

- [ ] **Step 5: Commit**

```bash
git add bin/moonlander-keylog
git commit -m "moonlander: add HID-console keylogger with testable CSV filter"
```

---

## Task 6: LaunchAgent + links.tsv wiring

**Files:**
- Create: `Library/LaunchAgents/com.dataders.moonlander-keylog.plist`
- Modify: `links.tsv`

- [ ] **Step 1: Write the LaunchAgent plist**

Create `Library/LaunchAgents/com.dataders.moonlander-keylog.plist`. `ProgramArguments`
points at the repo `bin/` path directly (intentional — the plist is machine-specific
and this sidesteps any `~/.local/bin` symlink timing):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dataders.moonlander-keylog</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/dataders/Developer/dotfiles/bin/moonlander-keylog</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>15</integer>
    <key>StandardErrorPath</key>
    <string>/Users/dataders/.local/share/moonlander-keylog/agent.err.log</string>
    <key>StandardOutPath</key>
    <string>/Users/dataders/.local/share/moonlander-keylog/agent.out.log</string>
</dict>
</plist>
```

`KeepAlive`+`ThrottleInterval=15` means when the board is unplugged `qmk console`
exits and launchd waits ≥15s before respawning — a benign idle loop, not a tight spin.

- [ ] **Step 2: Add the links.tsv row**

Append to `links.tsv` (tab-separated, matching existing columns
`source<TAB>target<TAB>group<TAB>visibility<TAB>note`):

```
repo:Library/LaunchAgents/com.dataders.moonlander-keylog.plist	home:Library/LaunchAgents/com.dataders.moonlander-keylog.plist	moonlander	public	keylogger launchagent
```

- [ ] **Step 3: Dry-run the symlink change**

Ensure the target dir exists first: `mkdir -p ~/Library/LaunchAgents` (it already does
on this machine). Then run: `./links.sh dry-run`
Expected: shows the new plist link to be created; no errors, no clobbering of
existing links (especially NOT touching `~/.dbt/*`).

- [ ] **Step 4: Apply and check**

Run: `./links.sh apply && ./links.sh check`
Expected: `~/Library/LaunchAgents/com.dataders.moonlander-keylog.plist` → repo file;
`check` reports healthy.

- [ ] **Step 5: Commit**

```bash
git add Library/LaunchAgents/com.dataders.moonlander-keylog.plist links.tsv
git commit -m "moonlander: add KeepAlive LaunchAgent for the keylogger"
```

---

## Task 7: Privacy wiring (exclusions, gitignore, purge)

**Files:**
- Create: `bin/moonlander-keylog-purge`
- Modify: `.gitignore`

- [ ] **Step 1: Create the log dir and exclude from Time Machine**

Run:
```bash
mkdir -p ~/.local/share/moonlander-keylog
tmutil addexclusion ~/.local/share/moonlander-keylog
tmutil isexcluded ~/.local/share/moonlander-keylog
```
Expected: last command prints `[Excluded] ...`.

- [ ] **Step 2: 🔌 Exclude the dir from Backblaze (GUI)**

In Backblaze → Settings → Exclusions, add `~/.local/share/moonlander-keylog`.
(Backblaze backs up the whole disk by default and would otherwise upload the keylog.)
This is a manual GUI step — note completion.

- [ ] **Step 3: Confirm the dir is not under Dropbox**

Run: `case "$HOME/.local/share/moonlander-keylog" in "$HOME/Dropbox"/*) echo "IN DROPBOX — relocate"; ;; *) echo "OK: not under Dropbox";; esac`
Expected: `OK: not under Dropbox`.

- [ ] **Step 4: Write the purge helper**

Create `bin/moonlander-keylog-purge` (mode +x):

```bash
#!/usr/bin/env bash
# Delete all raw Moonlander keylogs.
set -euo pipefail
LOGDIR="$HOME/.local/share/moonlander-keylog"
shopt -s nullglob
files=("$LOGDIR"/keylog-*.csv)
if [ ${#files[@]} -eq 0 ]; then echo "No keylogs to purge."; exit 0; fi
rm -v "${files[@]}"
echo "Purged ${#files[@]} keylog file(s)."
```

Run: `chmod +x bin/moonlander-keylog-purge`

- [ ] **Step 5: Verify purge on a dummy file (does not touch real logs format)**

Run:
```bash
touch ~/.local/share/moonlander-keylog/keylog-00000000.csv
bin/moonlander-keylog-purge
ls ~/.local/share/moonlander-keylog/keylog-*.csv 2>/dev/null && echo "FAIL: leftover" || echo "PASS: purged"
```
Expected: `PASS: purged`.

- [ ] **Step 6: Gitignore stray logs/build scratch**

Append to `.gitignore`:
```
# Moonlander keylogger (never commit raw keystrokes or stray build bins)
keylog-*.csv
moonlander/keymaps/
```
(The real logs live outside the repo under `~/.local/share` and the build bin lands
in `~/qmk_firmware`, so these patterns are a defensive guard against accidental
in-repo copies — they match the actual `keylog-*.csv` filename, not `*.keylog.csv`.)

- [ ] **Step 7: Commit**

```bash
git add bin/moonlander-keylog-purge .gitignore
git commit -m "moonlander: privacy wiring — TM exclusion docs, purge helper, gitignore"
```

---

## Task 8: 🔌 macOS HID permission + end-to-end smoke test

**Files:** none (runtime verification).

- [ ] **Step 1: Load the agent**

Run: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dataders.moonlander-keylog.plist`
(or log out/in). Expected: agent loads.

- [ ] **Step 2: 🔌 Grant HID/Input-Monitoring if prompted**

Reading the HID console via hidapi may trigger a TCC / Input-Monitoring prompt.
Approve it (System Settings → Privacy & Security → Input Monitoring), then re-login if
the agent didn't pick it up. Check `~/.local/share/moonlander-keylog/agent.err.log`
for permission errors.

- [ ] **Step 3: Type and verify the CSV fills**

Type normally for ~30s, then:
```bash
tail -3 ~/.local/share/moonlander-keylog/keylog-$(date +%Y%m%d).csv
awk -F, 'END{print "columns:", NF}' ~/.local/share/moonlander-keylog/keylog-$(date +%Y%m%d).csv
```
Expected: recent lines present; `columns: 8`.

- [ ] **Step 4: Verify KeepAlive fault tolerance**

Run: `pkill -f 'qmk console' ; sleep 20 ; pgrep -fl 'qmk console'`
Expected: a new `qmk console` process is running (launchd respawned it after the
throttle interval). Type a key and confirm the CSV still grows.

- [ ] **Step 5: Verify a sample uploads to the heatmap generator**

Open <https://precondition.github.io/qmk-heatmap>, upload today's CSV.
Expected: a per-layer heatmap renders. If the tool rejects the format, reconcile
column order / header expectation here (the one verify-before-relying item from the
spec) before collecting days of data.

---

## Task 9: Documentation

**Files:**
- Modify: `moonlander/README.md`

- [ ] **Step 1: Document the build/log/privacy/analysis workflow**

Add a `## Keystroke logging (heatmap data)` section to `moonlander/README.md`
covering: the console divergence from Oryx (re-export overwrites the hook — keep
layout edits in Oryx, the logging hook local), `bin/moonlander-build` + `qmk flash`,
the LaunchAgent, the privacy exclusions (Backblaze/Time Machine/Dropbox) and
`bin/moonlander-keylog-purge`, and the analysis step (precondition generator +
Keymapp heatmap cross-check). Link the spec and this plan.

- [ ] **Step 2: Commit**

```bash
git add moonlander/README.md
git commit -m "moonlander: document keylogging build, privacy, and analysis workflow"
```

---

## Analysis phase (deferred ~days — separate session, no code)

When several days of data have accumulated: upload the dated CSV(s) to precondition's
generator, cross-check Keymapp's live heatmap, and produce concrete `anders-colemak`
refinements (most-used keys per layer, frequent mod/tap-dance sequences, under-used
keys) plus unused QMK built-ins worth adopting. Then run `bin/moonlander-keylog-purge`.

## Definition of done

- [ ] Console firmware builds (Task 3) and flashes (Task 4); console shows key events.
- [ ] `--filter` self-test passes with exactly 8 columns (Task 5).
- [ ] LaunchAgent symlinked via `links.tsv`, loads, and respawns after kill (Tasks 6, 8).
- [ ] Log dir excluded from Time Machine + Backblaze, not under Dropbox; purge works (Task 7).
- [ ] A real CSV renders in the heatmap generator (Task 8).
- [ ] README documents the full workflow (Task 9).
