# forgit — fzf-powered git

Interactive git commands via fzf. All commands open a fuzzy picker.

## Most Useful Commands

| Command | What it does |
|---------|-------------|
| `forgit::log` / `glo` | Browse commits interactively, preview diffs |
| `forgit::diff` / `gd` | Fuzzy-pick files to diff |
| `forgit::add` / `ga` | Stage files interactively (preview changes) |
| `forgit::stash::show` / `gss` | Browse stash entries, preview contents |
| `forgit::cherry::pick` / `gcp` | Cherry-pick commits from interactive log |
| `forgit::rebase` / `grb` | Interactive rebase with commit picker |
| `forgit::fixup` / `gfu` | Create fixup commit for a selected prior commit |
| `forgit::reset::head` / `grh` | Unstage files interactively |
| `forgit::checkout::file` / `gcf` | Restore files interactively |
| `forgit::checkout::branch` / `gcb` | Switch branches with fuzzy search |
| `forgit::blame` / `gbl` | Interactive blame with preview |
| `forgit::clean` / `gclean` | Remove untracked files interactively |
| `forgit::log` / `glo` | Log with diff preview |

## Daily Workflow

```bash
# Morning: what changed?
glo                    # browse recent commits

# Working: stage selectively
ga                     # pick files to stage (see diffs inline)

# Oops: unstage something
grh                    # pick files to unstage

# Stash juggling
gss                    # browse + apply stash entries

# Branch hopping
gcb                    # fuzzy-find and switch branches
```

## Keybindings Inside fzf

- `Tab` — toggle selection (multi-select)
- `Enter` — confirm
- `Ctrl-/` — toggle preview
- `Ctrl-S` — toggle sort
- `?` — toggle preview (in some commands)

## Configuration

forgit respects these env vars (set in .zshrc if desired):

```bash
FORGIT_LOG_FORMAT="%C(auto)%h %s %C(dim)%an %cr"  # custom log format
FORGIT_FZF_DEFAULT_OPTS="--reverse"                 # fzf layout
```

Source: https://github.com/wfxr/forgit
