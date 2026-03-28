import subprocess
import sys
import argparse

def run_git_command(args, repo_path=None):
    try:
        cmd = ["git"]
        if repo_path:
            cmd.extend(["-C", repo_path])
        cmd.extend(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: git command not found.", file=sys.stderr)
        sys.exit(1)

def get_commits(repo_path=None):
    output = run_git_command(["rev-list", "--all", "--abbrev-commit"], repo_path)
    return output.strip().split("\n") if output.strip() else []

def get_commit_stats(commit_hash, repo_path=None):
    # -r: recurse into subdirectories
    # --no-commit-id: do not print the commit hash again
    # -m: handle merge commits
    # --root: show the root commit as a big creation event
    # --find-renames: detect renames
    output = run_git_command(
        ["diff-tree", "-r", "--no-commit-id", "-m", "--root", "--find-renames", commit_hash],
        repo_path
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

        old_mode = parts[0][1:] # strip leading ':'
        new_mode = parts[1]
        status_full = parts[4]
        status = status_full[0] # A, M, D, R, T, etc.

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
    parser = argparse.ArgumentParser(description="Lists all commits with file change counts (Regular vs Symlinks).")
    parser.add_argument("repo", nargs="?", default=".", help="Path to the git repository.")
    return parser

def main():
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

if __name__ == "__main__": # pragma: no cover
    main()
