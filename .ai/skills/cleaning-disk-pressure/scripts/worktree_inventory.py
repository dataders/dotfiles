import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


SKIP_DIRS = {
    ".cache",
    ".direnv",
    ".git",
    ".venv",
    "node_modules",
    "target",
}


def run(args, timeout=None):
    try:
        return subprocess.run(
            args, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None


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
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
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
    result = run(["du", "-sh", str(path)], timeout=timeout)
    if result is None:
        return f"timeout>{timeout}s"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.split()[0]


def status_of(path, timeout, ignore_status):
    result = run(["git", "-C", str(path), "status", "--porcelain"], timeout=timeout)
    if result is None:
        return f"timeout>{timeout}s"
    if result.returncode != 0:
        return "missing"
    lines = [line for line in result.stdout.splitlines() if not (ignore_status and ignore_status.search(line))]
    return "clean" if not lines else f"dirty:{len(lines)}"


def remote_subjects(repo):
    # Commit subjects reachable from any remote ref; a local commit with the same
    # subject is almost always a rebase/cherry-pick copy of pushed work.
    result = run(["git", "-C", repo, "log", "--remotes", "--no-merges", "--format=%s"], timeout=120)
    return set(result.stdout.splitlines()) if result and result.returncode == 0 else set()


def unpushed_of(path, head, subjects, timeout):
    # local = commits on HEAD not reachable from ANY remote ref (not just a same-named
    # branch); unique = local minus merge commits minus same-subject copies of remote work.
    if not head:
        return "-", "-"
    local = run(["git", "-C", str(path), "rev-list", "--count", head, "--not", "--remotes"], timeout=timeout)
    if local is None or local.returncode != 0:
        return "?", "?"
    if local.stdout.strip() == "0":
        return "0", "0"
    log = run(
        ["git", "-C", str(path), "log", "--no-merges", "--format=%s", head, "--not", "--remotes"],
        timeout=timeout,
    )
    if log is None or log.returncode != 0:
        return local.stdout.strip(), "?"
    unique = sum(1 for subject in log.stdout.splitlines() if subject not in subjects)
    return local.stdout.strip(), str(unique)


def protection_reasons(record, protect_paths, protect_heads, protect_branches):
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
    if "prunable" in record:
        reasons.append("prunable")
    return ",".join(reasons) if reasons else "-"


def compute_row(
    repo_label, record, protect_paths, protect_heads, protect_branches, du_timeout, ignore_status, subjects
):
    path = Path(record.get("worktree", ""))
    branch = record.get("branch", "").removeprefix("refs/heads/")
    head = record.get("HEAD", "")
    exists = path.exists()
    size = size_of(path, du_timeout) if exists else "missing"
    status = status_of(path, du_timeout, ignore_status) if exists else "missing"
    local, unique = unpushed_of(path, head, subjects, du_timeout) if exists else ("-", "-")
    return "\t".join(
        [
            repo_label,
            str(path),
            size,
            status,
            local,
            unique,
            head[:12],
            branch or "-",
            protection_reasons(record, protect_paths, protect_heads, protect_branches),
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Inventory local git worktrees by size, status, and protection reason."
    )
    parser.add_argument("--root", action="append", default=[])
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--protect-path", action="append", default=[])
    parser.add_argument("--protect-head", action="append", default=[])
    parser.add_argument("--protect-branch", action="append", default=[])
    parser.add_argument("--workers", type=int, default=8, help="parallel du/status lookups per repo")
    parser.add_argument("--du-timeout", type=int, default=20, help="seconds before a single du/status call is abandoned")
    parser.add_argument(
        "--ignore-status",
        default=r"^ D (target-head-pr|target-origin-main)/",
        help="regex for `git status --porcelain` lines that don't count as dirty ('' to count everything)",
    )
    args = parser.parse_args()

    roots = [Path(p).expanduser().resolve() for p in (args.root or ["~/Developer"])]
    protect_paths = [Path(p).expanduser().resolve() for p in args.protect_path]
    protect_heads = set(args.protect_head)
    protect_branches = set(args.protect_branch)
    ignore_status = re.compile(args.ignore_status) if args.ignore_status else None
    repos = discover_repos(roots, args.max_depth)

    print("repo\tpath\tsize\tstatus\tlocal\tunique\thead\tbranch\treasons", flush=True)
    for _, sample in sorted(repos.items()):
        result = run(["git", "-C", sample, "worktree", "list", "--porcelain"], timeout=10)
        if result is None or result.returncode != 0:
            continue
        records = [
            r for r in parse_worktrees(result.stdout) if under_any_root(r.get("worktree", ""), roots)
        ]
        if len(records) <= 1:
            continue

        subjects = remote_subjects(sample)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(
                    compute_row,
                    sample,
                    record,
                    protect_paths,
                    protect_heads,
                    protect_branches,
                    args.du_timeout,
                    ignore_status,
                    subjects,
                )
                for record in records
            ]
            for future in futures:
                print(future.result(), flush=True)


if __name__ == "__main__":
    main()
