# macOS Sequoia 15.7.7 → Tahoe 26.7.2 upgrade plan

Written 2026-11-02 for the M4 Pro MacBook Pro (Mac16,8, 24 GB), Jamf-managed
(`fishtown.jamfcloud.com`, DEP enrolled), FileVault on, SIP on.

Target: **macOS Tahoe 26.7.2 (25G332)**, the newest release of the OS before
macOS 27 Golden Gate. Not Golden Gate (27.x).

## Decision: skip the beta track

- Golden Gate has been out since 2026-09-14, so Tahoe gets only security and
  bug-fix point releases now. The 26.7.2 builds went to beta testers as
  release candidates, with no betas before them. Enrolling gets you a few
  days' early access to security patches. You get no new features.
- Turning on "Beta Updates" also puts **Golden Gate betas** one dropdown away
  from Software Update, which is the track you said you don't want.
- This is a managed work Mac. The MDM doesn't block beta enrollment today, but
  a beta build on a company laptop is IT's decision. Check with IT first if
  you still want it.

Install the public 26.7.2 and leave Beta Updates **Off**.

## Blockers to clear first

| # | Blocker | Evidence | Fix |
|---|---------|----------|-----|
| 1 | **Disk is 98% full** | Data volume: 400 GiB used, **8.7 GiB free** | Free **≥ 45 GiB** (installer ~18 GB plus ~25 GB working space). `~/Developer` is 125 GB (`target/`, `.venv`, `node_modules`, stale worktrees) and `~/Library/Caches` is 9 GB. Use the `cleaning-disk-pressure` skill. |
| 2 | **No backup** | `tmutil destinationinfo` → "No destinations configured" | Get a real backup before the upgrade (see "The new drive" below). At minimum, push everything you care about. |
| 3 | Unpushed and uncommitted config | `dotfiles` is 1 commit ahead of `origin/main`. `dotfiles_env` has uncommitted `.aws/config` and `.databrickscfg` changes | Commit and push both repos. |
| 4 | Stale system extensions | Old Twingate, Jamf Protect, and CrowdStrike extensions are "waiting to uninstall on reboot" | Reboot once before starting, so the upgrade starts from a clean extension state. |

## The new drive

The drive wasn't plugged in when I checked: `diskutil list external` was empty
and all three Thunderbolt/USB4 ports were empty. **Diagnose it before assuming
the upgrade will fix it.** A Sequoia → Tahoe upgrade rarely fixes a drive
that doesn't mount.

Plug it in, then run:

```bash
diskutil list external physical
```

```bash
system_profiler SPThunderboltDataType SPUSBHostDataType SPNVMeDataType
```

- **Listed in System Information, but no volume mounts:** it's a format
  problem, not an OS problem. A brand-new drive is often uninitialized, NTFS
  (read-only on every macOS version), or uses an odd partition map. Open Disk
  Utility, choose View → Show All Devices, then erase the top-level device as
  APFS (or exFAT if you need Windows access).
- **Not listed anywhere:** it's hardware. The cause is usually a charge-only
  USB-C cable, a bus-powered enclosure that needs more power, or a hub. Try a
  known data or Thunderbolt cable directly in a Mac port. Tahoe won't fix this.
- Once the drive works, **make it the Time Machine destination before the
  upgrade.** That clears blocker #2.

## Upgrade steps

1. Clear blockers 1–4 and confirm at least 45 GiB free (`df -h /System/Volumes/Data`).
2. Optionally snapshot the current state so you can diff it afterwards:
   ```bash
   cd ~/Developer/dotfiles && ./links.sh check > ~/pre-tahoe-links.txt 2>&1; brew list --versions > ~/pre-tahoe-brew.txt; launchctl list | grep dataders > ~/pre-tahoe-agents.txt
   ```
3. Download Tahoe itself. Software Update offers only Golden Gate 27.2 and
   Sequoia 15.8.2, so **don't click "Upgrade Now" in System Settings**. That
   installs Golden Gate.
   ```bash
   softwareupdate --fetch-full-installer --full-installer-version 26.7.2
   ```
   This creates `/Applications/Install macOS Tahoe.app`.
4. Quit everything, connect power, and run the installer. Expect 30–60 minutes
   and several reboots.
5. After first login, work through the checklist below.
6. Delete `/Applications/Install macOS Tahoe.app` to get back ~18 GB.

> `AutomaticallyInstallMacOSUpdates = 1` is set. That setting installs point
> updates only (26.7.x). It doesn't install major upgrades, but Software Update
> will show Golden Gate as "Recommended". Ignore it until you decide to move
> to Golden Gate. Jamf could also enforce an upgrade later. Today
> `forceDelayedMajorSoftwareUpdates = 0`, so no deferral is configured.

## Post-upgrade checklist (things in these dotfiles that may break)

### Permissions and extensions (most likely to need attention)

- [ ] **Karabiner-Elements 15.9.0 / DriverKit VirtualHIDDevice 1.8.0.** After
      the upgrade, check System Settings → General → Login Items & Extensions →
      Driver Extensions, and Privacy & Security → Input Monitoring. Test that
      Caps Lock works as Hyper when held and Escape when tapped.
- [ ] **Accessibility, Input Monitoring, and Screen Recording grants** for
      Raycast, Ghostty, cmux, Karabiner, Alcove, Dayflow, Loom, zoom, and
      Amphetamine. Some of these are delivered by the Jamf TCC profile, so if
      a grant won't stick, IT has to push it.
- [ ] **Network extensions: Tailscale and Twingate.** Confirm both show
      "activated enabled" in `systemextensionsctl list` and that VPN/ZTNA
      connects.
- [ ] **Jamf Protect, Okta Verify, Jamf Trust.** Confirm they're running and
      that SSO works.

### LaunchAgents (`Library/LaunchAgents/*`, symlinked by `links.tsv`)

- [ ] Run `launchctl list | grep dataders` and diff it against
      `~/pre-tahoe-agents.txt`. Expect all five:
      `url-open-relay`, `peach01-url-open-tunnel`, `peach01-url-healthcheck`,
      `moonlander-keylog`, `github-notification-sweep`.
- [ ] Tahoe's Background Task Management may show "background item added"
      notifications for each agent. Allow them, or check Login Items &
      Extensions → Allow in the Background.
- [ ] `peach01-url-healthcheck` sends notifications through `osascript
      display notification`. If they stop appearing, re-enable notifications
      for Script Editor.
- [ ] `moonlander-keylog` reads the QMK HID console. If its CSV stops growing,
      re-grant Input Monitoring.
- [ ] Test the relay end to end: trigger an OAuth `open` from peach01 and
      confirm it reaches the Mac browser.

### Homebrew, toolchains, and services

- [ ] Command Line Tools: 26.2 is already installed. Update to the latest 26.x
      if Software Update offers it, or run `xcode-select --install`.
- [ ] Run `brew update && brew upgrade && brew doctor`. Bottles are built per
      OS, so a full `brew upgrade` swaps in Tahoe bottles.
- [ ] Restart services: `brew services restart postgresql@14 redis tailscale`.
- [ ] Containers: run `colima start` and `docker run --rm hello-world`. Colima
      0.10.3 with qemu or lima is the moving part here.
- [ ] Rust, uv, and node: rebuild anything that links against Homebrew
      libraries, such as `cargo install --list` tools and `uv tool upgrade --all`.
      Your main worktree builds (fs) may need a clean `target/`.
- [ ] Run `./links.sh doctor` from `~/Developer/dotfiles` (never from a
      worktree).

### Apps

- [ ] **VLC is Intel-only (x86_64)**, and it's the only Intel-only app in
      `/Applications`. Tahoe shows Rosetta deprecation warnings for it.
      Replace it with the Apple-silicon build (`brew install --cask vlc`).
- [ ] xbar v2.1.7-beta is old but should run. Check that the
      `disk-free.5m.sh` plugin renders.
- [ ] Liquid Glass UI: if the transparency bothers you, turn on System
      Settings → Accessibility → Display → Reduce Transparency.

## New things worth using on Tahoe

- **Apple's `container` CLI.** It needs macOS 26 and runs Linux containers in
  lightweight per-container VMs. It's worth trying as a replacement for
  Colima, qemu, and the Docker CLI stack in the Brewfile.
- **Shortcuts automations on the Mac**, triggered by time of day, folder
  changes, display or drive connect, and more. Some LaunchAgents or xbar jobs
  might become Shortcuts instead. Keep anything you want version-controlled in
  dotfiles as launchd, though, because Shortcuts don't diff well.
- **Spotlight overhaul**: actions with parameters, Quick Keys, and clipboard
  history. These overlap with Raycast, so pick one per job. Skip Spotlight
  clipboard history if Raycast's is in use.
- **Terminal.app now has 24-bit color and Powerline fonts.** It's a usable
  fallback when Ghostty or cmux misbehave.
- **Customizable menu bar and Control Center**, which can host third-party
  controls. This may matter for Alcove and xbar.
- **Phone app and iPhone Live Activities on the Mac.** The
  `.raycast_scripts/call-with-iphone.sh` script could become simpler.
- Apple Intelligence is partly restricted by MDM (Genmoji and Image Playground
  are off, `_isAppleIntelligenceRestricted = 1`), so don't count on those
  features.

## Later: Golden Gate (27)

Golden Gate requires Apple silicon (fine here) and is expected to be the last
release with full Rosetta. Revisit after 27.3 or so, once Homebrew, Karabiner,
and the Jamf stack have settled on it. The same checklist applies.
