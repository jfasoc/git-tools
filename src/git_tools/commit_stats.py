"""
List all commits with file change counts (Regular vs Symlinks).

This module provides a command-line tool to analyze git history and report
the number of additions, modifications, and deletions for both regular files
and symlinks in each commit.
"""

import argparse
from importlib.metadata import version
from .utils import run_git_command


def get_commits(repo_path=None):
    """
    Retrieve a list of commit hashes from the repository.

    Args:
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).

    Returns:
        list: A list of commit hashes (abbreviated).
    """
    output = run_git_command(["rev-list", "--all", "--abbrev-commit"], repo_path)
    return output.strip().split("\n") if output.strip() else []


def get_commit_stats(commit_hash, repo_path=None):
    """
    Calculate file change statistics for a specific commit.

    Categorizes changes into additions, modifications, and deletions,
    and distinguishes between regular files and symbolic links.

    Args:
        commit_hash (str): The hash of the commit to analyze.
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).

    Returns:
        tuple: (reg_stats, sym_stats)
            reg_stats (dict): Counts for regular files {'A': int, 'M': int, 'D': int}.
            sym_stats (dict): Counts for symbolic links {'A': int, 'M': int, 'D': int}.
    """
    # -r: recurse into subdirectories
    # --no-commit-id: do not print the commit hash again
    # -m: handle merge commits
    # --root: show the root commit as a big creation event
    # --find-renames: detect renames
    output = run_git_command(
        [
            "diff-tree",
            "-r",
            "--no-commit-id",
            "-m",
            "--root",
            "--find-renames",
            commit_hash,
        ],
        repo_path,
    )

    reg_stats = {"A": 0, "M": 0, "D": 0}
    sym_stats = {"A": 0, "M": 0, "D": 0}

    for line in output.strip().split("\n"):
        if not line:
            continue

        # Line format: :old_mode new_mode old_sha new_sha status\tpath
        parts = line.split()
        if len(parts) < 5:
            continue

        old_mode = parts[0][1:]  # strip leading ':'
        new_mode = parts[1]
        status_full = parts[4]
        status = status_full[0]  # A, M, D, R, T, etc.

        is_symlink = (new_mode == "120000") or (old_mode == "120000")
        stats = sym_stats if is_symlink else reg_stats

        if status == "A":
            stats["A"] += 1
        elif status == "D":
            stats["D"] += 1
        elif status == "M":
            stats["M"] += 1
        elif status == "R":
            stats["M"] += 1
        elif status == "T":
            if old_mode != "120000" and new_mode == "120000":
                reg_stats["D"] += 1
                sym_stats["A"] += 1
            elif old_mode == "120000" and new_mode != "120000":
                sym_stats["D"] += 1
                reg_stats["A"] += 1
            else:
                stats["M"] += 1
        elif status == "C":
            stats["A"] += 1

    return reg_stats, sym_stats


def get_parser():
    """
    Construct the argument parser for the commit-stats tool.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    try:
        ver = version("git-tools")
    except Exception:
        ver = "unknown"
    parser = argparse.ArgumentParser(
        description="Lists all commits with file change counts (Regular vs Symlinks)."
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {ver}",
        help="Show the version and exit.",
    )
    parser.add_argument(
        "repo", nargs="?", default=".", help="Path to the git repository."
    )
    return parser


def main():
    """
    Main entry point for the git-commit-stats tool.
    """
    parser = get_parser()
    args = parser.parse_args()

    repo_path = args.repo

    commits = get_commits(repo_path)
    if not commits:
        print("No commits found.")
        return

    # Print header
    header = f"{'Commit':<10} {'Regular (A/M/D)':<18} {'Symlinks (A/M/D)':<18}"
    print(header)
    print("-" * len(header))

    for commit in commits:
        reg, sym = get_commit_stats(commit, repo_path)
        reg_str = f"{reg['A']:>3} / {reg['M']:>3} / {reg['D']:>3}"
        sym_str = f"{sym['A']:>3} / {sym['M']:>3} / {sym['D']:>3}"
        print(f"{commit:<10} {reg_str:<18} {sym_str:<18}")


if __name__ == "__main__":
    main()
