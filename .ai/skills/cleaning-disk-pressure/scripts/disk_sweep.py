"""Plan-only disk sweep for the cleaning-disk-pressure skill.

Sizes build output and scratch space under the given roots, the user's own
/tmp entries, the uv caches, and Trash; marks anything a live process is
using; and prints a cleanup plan. It never deletes anything: agent-safe
commands (cargo clean, uv cache prune) and a single user-run rm line are
printed for review, so destructive deletes still go through the user.
"""

import argparse
import os
import platform
import shlex
import shutil
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


CANDIDATE_NAMES = {"target", "build", "vcpkg", ".venv", "node_modules", "logs"}
CANDIDATE_PREFIXES = ("target_", "target-", "logs_", "logs-")
WALK_SKIP = {".git", ".jj", ".venv", "node_modules", "target", ".cache", ".direnv"}
# Tooling in a checkout with a live process may touch these at any moment, so a
# process anywhere in the checkout protects them. Other kinds (dbt run dirs,
# logs) are protected only by a process or open file inside the dir itself.
CHECKOUT_SCOPED = {"cargo", ".venv", "node_modules", "build"}
ACTIONS = ("AGENT", "USER", "ASK", "KEEP")


def run(args, timeout=None):
    try:
        return subprocess.run(
            args, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def low_io(args):
    prefix = ["nice", "-n", "19"]
    if shutil.which("ionice"):
        prefix += ["ionice", "-c3"]
    return prefix + args


def is_under(path, parent):
    try:
        Path(path).relative_to(parent)
        return True
    except ValueError:
        return False


def is_candidate(name):
    return name in CANDIDATE_NAMES or name.startswith(CANDIDATE_PREFIXES)


def discover_checkouts(roots, max_depth):
    tops = set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            path = Path(dirpath)
            if ".git" in dirnames or ".git" in filenames:
                tops.add(path)
                dirnames[:] = []
                continue
            if len(path.relative_to(root).parts) >= max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in WALK_SKIP]
    # Nested worktrees (.worktrees/, .claude/worktrees/) are only visible through git.
    for top in list(tops):
        result = run(["git", "-C", str(top), "worktree", "list", "--porcelain"], timeout=10)
        if result is None or result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                wt = Path(line.removeprefix("worktree "))
                if wt.is_dir() and any(is_under(wt, root) for root in roots):
                    tops.add(wt)
    return sorted(tops)


def ancestors(proc):
    pids, pid = set(), str(os.getpid())
    while pid not in pids and pid != "0":
        pids.add(pid)
        try:
            # comm (field 2) can contain spaces, so split after its closing paren.
            pid = (proc / pid / "stat").read_text().rsplit(")", 1)[1].split()[1]
        except (OSError, IndexError):
            break
    return pids


def live_processes():
    """(path, label) pairs for cwd, open files and CARGO_TARGET_DIR of readable processes."""
    proc = Path("/proc")
    if not proc.is_dir():
        return None
    skip = ancestors(proc)  # this sweep, and the uv/shell/agent that launched it
    pairs = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or entry.name in skip:
            continue
        try:
            label = f"{(entry / 'comm').read_text().strip()}/{entry.name}"
            pairs.append((os.readlink(entry / "cwd"), f"cwd:{label}"))
        except OSError:
            continue  # another user's process
        try:
            for fd in (entry / "fd").iterdir():
                try:
                    target = os.readlink(fd)
                except OSError:
                    continue
                if target.startswith("/"):
                    pairs.append((target, f"open:{label}"))
        except OSError:
            pass
        try:
            for var in (entry / "environ").read_bytes().split(b"\0"):
                if var.startswith(b"CARGO_TARGET_DIR="):
                    value = var.split(b"=", 1)[1].decode(errors="replace")
                    pairs.append((value, f"CARGO_TARGET_DIR:{label}"))
        except OSError:
            pass
    return pairs


def busy_reason(scope, pairs):
    if not pairs:
        return None
    for path, label in pairs:
        if is_under(path, scope):
            return label
    return None


def git_dirs(checkout, ignored, timeout):
    args = ["git", "-C", str(checkout), "ls-files", "-z", "--others", "--exclude-standard", "--directory"]
    if ignored:
        args.append("--ignored")
    result = run(low_io(args), timeout=timeout)
    if result is None or result.returncode != 0:
        return []
    return [p.rstrip("/") for p in result.stdout.split("\0") if p.endswith("/")]


def checkout_candidates(checkout, worktrees, timeout):
    found = []
    seen = set()
    for ignored in (True, False):
        for rel in git_dirs(checkout, ignored, timeout):
            path = checkout / rel
            if path in seen or any(is_under(wt, path) for wt in worktrees):
                continue  # already listed, or it holds a worktree that is inventoried on its own
            # Untracked (not ignored) top-level dirs are listed too, e.g. vcpkg/ or target_* run dirs.
            if is_candidate(path.name) or (not ignored and "/" not in rel):
                seen.add(path)
                found.append(
                    {"path": path, "checkout": checkout, "ignored": ignored, "rel": rel, "kind": kind_of(path)}
                )
    return found


def kind_of(path):
    name = path.name
    if (path / "CACHEDIR.TAG").exists() or (path / ".rustc_info.json").exists():
        return "cargo"
    if any((path / marker).exists() for marker in ("manifest.json", "run_results.json", "db")):
        return "dbt"
    if name in (".venv", "node_modules"):
        return name
    if name.startswith("logs"):
        return "logs"
    if name in ("build", "vcpkg"):
        return "build"
    return "untracked"


def size_kb(path, timeout):
    result = run(low_io(["du", "-sk", str(path)]), timeout=timeout)
    if result is None or result.returncode not in (0, 1) or not result.stdout.strip():
        return None
    return int(result.stdout.split()[0])


def written_within(path, minutes, timeout):
    result = run(
        low_io(["find", str(path), "-maxdepth", "3", "-mmin", f"-{minutes}", "-print", "-quit"]),
        timeout=timeout,
    )
    if result is None:
        return None
    return bool(result.stdout.strip())


def has_socket(path, timeout):
    result = run(["find", str(path), "-maxdepth", "2", "-type", "s", "-print", "-quit"], timeout=timeout)
    return result is None or bool(result.stdout.strip())


def has_tracked(item, timeout):
    result = run(["git", "-C", str(item["checkout"]), "ls-files", "-z", "--", item["rel"]], timeout=timeout)
    return result is None or bool(result.stdout.strip())


def cargo_manifest(item):
    for candidate in (item["path"].parent / "Cargo.toml", item["checkout"] / "Cargo.toml"):
        if candidate.is_file():
            return candidate
    return None


def classify(item, pairs, args):
    """Return (action, command, note). Commands are printed, never run."""
    path, kind = item["path"], item["kind"]
    quoted = shlex.quote(str(path))
    scope = item["checkout"] if kind in CHECKOUT_SCOPED else path
    reason = busy_reason(scope, pairs)
    if reason:
        return "KEEP", None, f"in use ({reason})"

    if kind == "tmp":
        if path.name == "uv-cache":
            return "AGENT", f"UV_CACHE_DIR={quoted} uv cache prune", "Codex uv cache; prune frees part"
        if path.name.startswith("claude-") and item["claude_running"]:
            return "KEEP", None, "live Claude session scratchpads"
        # tmux and forwarded ssh-agent sockets look idle and don't show up as open paths in /proc.
        if path.name.startswith(("tmux-", "ssh-")) or has_socket(path, args.timeout):
            return "KEEP", None, "holds sockets"
        fresh = written_within(path, args.tmp_idle_hours * 60, args.timeout)
        if fresh is None:
            return "ASK", None, "freshness check timed out"
        if fresh:
            return "KEEP", None, f"written in last {args.tmp_idle_hours}h"
        return "USER", None, f"idle >{args.tmp_idle_hours}h"
    if kind == "uv-cache":
        return "AGENT", "uv cache prune", "prune frees part"
    if kind == "trash":
        return "ASK", None, "user empties Trash; moving files there reclaims nothing"

    fresh = written_within(path, args.fresh_minutes, args.timeout)
    if fresh is None:
        return "ASK", None, "freshness check timed out"
    if fresh:
        return "KEEP", None, f"written in last {args.fresh_minutes}m"

    if kind == "cargo":
        manifest = cargo_manifest(item)
        if manifest is None:
            return "USER", None, "cargo target with no manifest nearby"
        cmd = f"cargo clean --manifest-path {shlex.quote(str(manifest))} --target-dir {quoted}"
        return "AGENT", cmd, "explicit --target-dir, safe with CARGO_TARGET_DIR set"
    if kind in (".venv", "node_modules"):
        return ("USER", None, "regenerable") if item["ignored"] else ("ASK", None, "not gitignored")
    if kind == "build":
        if item["ignored"] and not has_tracked(item, args.timeout):
            return "USER", None, "gitignored, no tracked files"
        return "ASK", None, "untracked or has tracked files"
    if kind == "dbt":
        return "ASK", None, "dbt run dir: keep the one a live run uses; never dbt clean (wipes target/db)"
    if kind == "logs":
        return "ASK", None, "run logs may be evidence"
    return "ASK", None, "untracked, not ignored"


def evaluate(item, pairs, args):
    kb = size_kb(item["path"], args.timeout)
    action, cmd, note = classify(item, pairs, args)
    return {**item, "kb": kb, "action": action, "cmd": cmd, "note": note}


def fs_line(path):
    try:
        st = os.statvfs(path)
    except OSError:
        return None
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    used = total - st.f_bfree * st.f_frsize
    return (os.stat(path).st_dev, f"{path}: {used / 1e9:.0f}G used / {total / 1e9:.0f}G, {free / 1e9:.0f}G free")


def free_gb(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def fmt_gb(kb):
    return "?" if kb is None else f"{kb / 1048576:.1f}G"


def print_plan(results, args):
    totals = {a: sum(r["kb"] or 0 for r in results if r["action"] == a) for a in ACTIONS}
    print("\n== totals ==")
    for action in ACTIONS:
        print(f"{action:5} {fmt_gb(totals[action])}")

    # Unknown sizes (du timed out) stay in the plan, sorted last.
    min_kb = args.min_gb * 1048576
    shown = sorted(
        (r for r in results if r["kb"] is None or r["kb"] >= min_kb),
        key=lambda r: r["kb"] or 0,
        reverse=True,
    )
    reclaim = [r for r in shown if r["action"] in ("AGENT", "USER")]
    beyond = []
    if args.target_free_gb is not None:
        have = free_gb(args.roots[0])
        needed = []
        for r in reclaim:
            if have < args.target_free_gb:
                needed.append(r)
                have += (r["kb"] or 0) * 1024 / 1e9
            else:
                beyond.append(r)
        reclaim = needed
        print(f"\ntarget {args.target_free_gb:.0f}G free: plan covers {len(reclaim)} items, "
              f"{len(beyond)} more not needed (projected {have:.0f}G free)")

    print("\n== agent-safe (no rm; agents may run these) ==")
    for r in reclaim:
        if r["action"] == "AGENT":
            print(f"{r['cmd']}  # {fmt_gb(r['kb'])}")
    user = [r for r in reclaim if r["action"] == "USER"]
    print("\n== user-run (review, then the user runs it; rm -rf is blocked for agents) ==")
    if user:
        print("rm -rf -- " + " ".join(shlex.quote(str(r["path"])) for r in user)
              + f"  # {fmt_gb(sum(r['kb'] or 0 for r in user))}")
    print("\n== ask the user ==")
    for r in shown:
        if r["action"] == "ASK":
            print(f"{fmt_gb(r['kb'])}\t{r['path']}\t{r['note']}")
    if beyond:
        print("\n== beyond target (leave unless the user wants more) ==")
        for r in beyond:
            print(f"{fmt_gb(r['kb'])}\t{r['action']}\t{r['path']}")


def main():
    parser = argparse.ArgumentParser(description="Plan-only disk sweep. Prints commands; deletes nothing.")
    parser.add_argument("--root", action="append", default=[], help="default: $HOME/Developer")
    parser.add_argument("--max-depth", type=int, default=3, help="how deep to look for checkouts under each root")
    parser.add_argument("--no-tmp", action="store_true", help="skip your own /tmp entries")
    parser.add_argument("--tmp-idle-hours", type=int, default=24)
    parser.add_argument("--fresh-minutes", type=int, default=60, help="writes this recent mean in use")
    parser.add_argument("--min-gb", type=float, default=0.5, help="hide rows smaller than this")
    parser.add_argument("--target-free-gb", type=float, help="stop the plan once projected free space reaches this")
    parser.add_argument("--measure-home", action="store_true",
                        help="also du $HOME to estimate space used by other users (slow)")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=300, help="seconds per du/find/git call")
    args = parser.parse_args()

    home = Path.home()
    args.roots = [Path(p).expanduser().resolve() for p in (args.root or [home / "Developer"])]
    missing = [r for r in args.roots if not r.is_dir()]
    for root in missing:
        print(f"warning: root {root} does not exist; nothing under it is scanned", file=sys.stderr)
    args.roots = [r for r in args.roots if r.is_dir()]
    if not args.roots:
        sys.exit("error: no --root exists. On Linux hosts use --root \"$HOME/Developer\".")

    print(f"# disk sweep on {socket.gethostname()} ({platform.system()}), plan only: nothing is deleted")
    seen_dev = set()
    for path in [*args.roots, Path("/tmp"), home]:
        line = fs_line(path)
        if line and line[0] not in seen_dev:
            seen_dev.add(line[0])
            print(f"# {line[1]}")

    pairs = live_processes()
    if pairs is None:
        print("# no /proc: in-use detection is off; check live sessions' cwd before running anything")

    checkouts = discover_checkouts(args.roots, args.max_depth)
    print(f"# {len(checkouts)} checkouts under {', '.join(map(str, args.roots))}", flush=True)
    items = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for found in pool.map(lambda c: checkout_candidates(c, checkouts, args.timeout), checkouts):
            items.extend(found)

    claude_running = any("claude" in label.split(":", 1)[1] for _, label in pairs or [])
    if not args.no_tmp and Path("/tmp").is_dir():
        uid = os.getuid()
        for entry in Path("/tmp").iterdir():
            try:
                st = entry.lstat()
            except OSError:
                continue
            if st.st_uid == uid and not entry.is_symlink():
                items.append({"path": entry, "kind": "tmp", "claude_running": claude_running})
    for path, kind in ((home / ".cache" / "uv", "uv-cache"), (home / ".local" / "share" / "Trash", "trash")):
        if path.is_dir():
            items.append({"path": path, "kind": kind})

    print("size\taction\tkind\tpath\tnote", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(evaluate, item, pairs, args) for item in items]
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            if r["kb"] is None or r["kb"] / 1048576 >= args.min_gb:
                print(f"{fmt_gb(r['kb'])}\t{r['action']}\t{r['kind']}\t{r['path']}\t{r['note']}", flush=True)

    print_plan(results, args)

    if args.measure_home:
        own = size_kb(home, args.timeout * 4) or 0
        if os.stat("/tmp").st_dev == os.stat(home).st_dev:
            own += sum(r["kb"] or 0 for r in results if r["kind"] == "tmp")
        st = os.statvfs(home)
        used_kb = (st.f_blocks - st.f_bfree) * st.f_frsize / 1024
        print(f"\n# yours (home + own /tmp): {fmt_gb(own)}; df used: {fmt_gb(used_kb)}; "
              f"the rest ({fmt_gb(max(used_kb - own, 0))}) is other users or unreadable; don't chase it")


if __name__ == "__main__":
    main()
