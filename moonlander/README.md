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
