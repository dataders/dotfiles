import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


SKIP_DIRS = {
    ".cache",
    ".direnv",
    ".git",
    ".jj",
    ".venv",
    "build",
    "logs",
    "node_modules",
    "target",
    "vcpkg",
}
SKIP_PREFIXES = ("target_", "target-", "logs_", "logs-")


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


def live_cwds():
    """cwd of every readable process except this one and its ancestors (Linux /proc only)."""
    proc = Path("/proc")
    if not proc.is_dir():
        return []
    skip, pid = set(), str(os.getpid())
    while pid not in skip and pid != "0":
        skip.add(pid)
        try:
            pid = (proc / pid / "stat").read_text().rsplit(")", 1)[1].split()[1]
        except (OSError, IndexError):
            break
    cwds = []
    for entry in proc.iterdir():
        if entry.name.isdigit() and entry.name not in skip:
            try:
                cwds.append((Path(os.readlink(entry / "cwd")), (entry / "comm").read_text().strip()))
            except OSError:
                continue
    return cwds


def parse_worktrees(text):
    records = []
    current = {}
    for line in text.splitlines():
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        if " " in line:
            key, value = line.split(" ", 1)
            current[key] = value
        else:
            current[line] = True
    if current:
        records.append(current)
    return records


def is_relative_to(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def discover_repos(roots, max_depth):
    repos = {}
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            path = Path(dirpath)
            depth = len(path.relative_to(root).parts)
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(SKIP_PREFIXES)]
            if depth > max_depth:
                dirnames[:] = []
                continue
            if ".git" in dirnames or ".git" in filenames:
                common = run(
                    [
                        "git",
                        "-C",
                        str(path),
                        "rev-parse",
                        "--path-format=absolute",
                        "--git-common-dir",
                    ],
                    timeout=10,
                )
                top = run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], timeout=10)
                if common and top and common.returncode == 0 and top.returncode == 0:
                    repos.setdefault(common.stdout.strip(), top.stdout.strip())
    return repos


def under_any_root(path_str, roots):
    return any(path_str.startswith(str(root)) for root in roots)


def size_of(path, timeout):
    result = run(low_io(["du", "-sh", str(path)]), timeout=timeout)
    if result is None:
        return f"timeout>{timeout}s"
    if result.returncode != 0 or not result.stdout.strip():
        return "unknown"
    return result.stdout.split()[0]


def idle_of(path):
    """Days since the worktree's index last changed. Read before `git status`, which refreshes it."""
    result = run(["git", "-C", str(path), "rev-parse", "--path-format=absolute", "--git-path", "index"], timeout=10)
    if result is None or result.returncode != 0:
        return "?"
    try:
        return f"{(time.time() - os.stat(result.stdout.strip()).st_mtime) / 86400:.0f}d"
    except OSError:
        return "?"


def status_of(path, timeout):
    result = run(low_io(["git", "-C", str(path), "status", "--porcelain"]), timeout=timeout)
    if result is None:
        return f"timeout>{timeout}s"
    if result.returncode != 0:
        return "missing"
    lines = result.stdout.splitlines()
    return "clean" if not lines else f"dirty:{len(lines)}"


def protection_reasons(record, protect_paths, protect_heads, protect_branches, cwds):
    reasons = []
    path = Path(record.get("worktree", ""))
    branch = record.get("branch", "").removeprefix("refs/heads/")
    head = record.get("HEAD", "")

    if branch in {"main", "master"}:
        reasons.append("main")
    if branch in protect_branches:
        reasons.append("branch")
    if head in protect_heads:
        reasons.append("head")
    for protected in protect_paths:
        if is_relative_to(protected, path):
            reasons.append("active-path")
            break
    for cwd, comm in cwds:
        if is_relative_to(cwd, path):
            reasons.append(f"live-cwd:{comm}")
            break
    if "prunable" in record:
        reasons.append("prunable")
    return ",".join(reasons) if reasons else "-"


def compute_row(repo_label, record, protect_paths, protect_heads, protect_branches, cwds, args):
    path = Path(record.get("worktree", ""))
    branch = record.get("branch", "").removeprefix("refs/heads/")
    head = record.get("HEAD", "")
    exists = path.exists()
    idle = idle_of(path) if exists else "missing"
    if not exists:
        size = "missing"
    elif args.no_size:
        size = "-"
    else:
        size = size_of(path, args.du_timeout)
    status = status_of(path, args.du_timeout) if exists else "missing"
    return "\t".join(
        [
            repo_label,
            str(path),
            size,
            idle,
            status,
            head[:12],
            branch or "-",
            protection_reasons(record, protect_paths, protect_heads, protect_branches, cwds),
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Inventory local git worktrees by size, status, and protection reason."
    )
    parser.add_argument("--root", action="append", default=[], help="default: $HOME/Developer")
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--protect-path", action="append", default=[])
    parser.add_argument("--protect-head", action="append", default=[])
    parser.add_argument("--protect-branch", action="append", default=[])
    parser.add_argument("--no-size", action="store_true", help="skip du; status, idle days and protection only")
    parser.add_argument("--workers", type=int, default=4, help="parallel du/status lookups per repo")
    parser.add_argument("--du-timeout", type=int, default=20, help="seconds before a single du/status call is abandoned")
    args = parser.parse_args()

    roots = [Path(p).expanduser().resolve() for p in (args.root or [Path.home() / "Developer"])]
    for root in roots:
        if not root.is_dir():
            print(f"warning: root {root} does not exist; nothing under it is inventoried", file=sys.stderr)
    roots = [r for r in roots if r.is_dir()]
    if not roots:
        sys.exit("error: no --root exists. On Linux hosts use --root \"$HOME/Developer\".")
    protect_paths = [Path(p).expanduser().resolve() for p in args.protect_path]
    protect_heads = set(args.protect_head)
    protect_branches = set(args.protect_branch)
    cwds = live_cwds()
    repos = discover_repos(roots, args.max_depth)

    print("repo\tpath\tsize\tidle\tstatus\thead\tbranch\treasons", flush=True)
    for _, sample in sorted(repos.items()):
        result = run(["git", "-C", sample, "worktree", "list", "--porcelain"], timeout=10)
        if result is None or result.returncode != 0:
            continue
        records = [
            r for r in parse_worktrees(result.stdout) if under_any_root(r.get("worktree", ""), roots)
        ]
        if len(records) <= 1:
            continue

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(
                    compute_row, sample, record, protect_paths, protect_heads, protect_branches, cwds, args
                )
                for record in records
            ]
            for future in futures:
                print(future.result(), flush=True)


if __name__ == "__main__":
    main()
