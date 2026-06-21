import argparse
import os
import subprocess
from pathlib import Path


SKIP_DIRS = {
    ".cache",
    ".direnv",
    ".git",
    ".venv",
    "node_modules",
    "target",
}


def run(args):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


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


def discover_repos(root, max_depth):
    repos = {}
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
                ]
            )
            top = run(["git", "-C", str(path), "rev-parse", "--show-toplevel"])
            if common.returncode == 0 and top.returncode == 0:
                repos.setdefault(common.stdout.strip(), top.stdout.strip())
    return repos


def size_of(path):
    result = run(["du", "-sh", str(path)])
    if result.returncode != 0:
        return "unknown"
    return result.stdout.split()[0]


def status_of(path):
    result = run(["git", "-C", str(path), "status", "--porcelain"])
    if result.returncode != 0:
        return "missing"
    lines = result.stdout.splitlines()
    return "clean" if not lines else f"dirty:{len(lines)}"


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


def main():
    parser = argparse.ArgumentParser(description="Inventory local git worktrees by size, status, and protection reason.")
    parser.add_argument("--root", default="/Users/dataders/Developer")
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--protect-path", action="append", default=[])
    parser.add_argument("--protect-head", action="append", default=[])
    parser.add_argument("--protect-branch", action="append", default=[])
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    protect_paths = [Path(p).expanduser().resolve() for p in args.protect_path]
    repos = discover_repos(root, args.max_depth)

    print("repo\tpath\tsize\tstatus\thead\tbranch\treasons")
    for _, sample in sorted(repos.items()):
        result = run(["git", "-C", sample, "worktree", "list", "--porcelain"])
        if result.returncode != 0:
            continue
        records = [r for r in parse_worktrees(result.stdout) if r.get("worktree", "").startswith(str(root))]
        if len(records) <= 1:
            continue
        repo_label = sample
        for record in records:
            path = Path(record.get("worktree", ""))
            branch = record.get("branch", "").removeprefix("refs/heads/")
            head = record.get("HEAD", "")
            exists = path.exists()
            print(
                "\t".join(
                    [
                        repo_label,
                        str(path),
                        size_of(path) if exists else "missing",
                        status_of(path) if exists else "missing",
                        head[:12],
                        branch or "-",
                        protection_reasons(record, protect_paths, set(args.protect_head), set(args.protect_branch)),
                    ]
                )
            )


if __name__ == "__main__":
    main()
