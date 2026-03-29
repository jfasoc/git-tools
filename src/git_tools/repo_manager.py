"""
Git Repo Manager - A tool to manage Git repositories.

This tool scans configured directories for Git repositories and maintains
a list of found repositories in a configuration file.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from importlib.metadata import version


def get_config_path():
    """
    Return the default configuration file path.

    The path is located at ~/.config/git-tools/git-repo-manager.

    Returns:
        str: The absolute path to the configuration file.
    """
    return os.path.expanduser("~/.config/git-tools/git-repo-manager")


def run_git_command(args, repo_path=None):
    """
    Run a git command and return its output.

    Args:
        args (list): List of command line arguments for git.
        repo_path (str, optional): Path to the repository.

    Returns:
        str: The stripped stdout of the command, or None if it failed.
    """
    try:
        cmd = ["git"]
        if repo_path:
            cmd.extend(["-C", repo_path])
        cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def is_git_repo(path):
    """
    Check if a directory is a Git repository.

    Args:
        path (str): Path to the directory.

    Returns:
        bool: True if it's a Git repository, False otherwise.
    """
    # Fast check for .git entry (folder or file)
    dotgit = os.path.join(path, ".git")
    if not os.path.exists(dotgit):
        return False

    # Verify it's a valid git repo using git command.
    out = run_git_command(["rev-parse", "--is-inside-work-tree"], path)
    return out == "true"


def load_config(config_path):
    """
    Load search directories and repositories from the config file.

    Args:
        config_path (str): Path to the config file.

    Returns:
        tuple: (search_dirs, repos)
            search_dirs (list): List of directories to scan.
            repos (dict): Dictionary mapping repo paths to their metadata.
                         Metadata: {'timestamp': str, 'active': bool}
    """
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    search_dirs = []
    repos = {}
    current_section = None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                # Section detection
                if stripped.startswith("[") and stripped.endswith("]"):
                    current_section = stripped[1:-1].lower()
                    continue

                if current_section == "search":
                    # For search dirs, we ignore comments for the list but keep the path
                    if not stripped.startswith("#"):
                        search_dirs.append(stripped)
                elif current_section == "repos":
                    active = not stripped.startswith("#")
                    content = stripped.lstrip("#").strip()
                    if "=" in content:
                        path_part, ts_part = content.split("=", 1)
                        # Normalize path for consistent comparison
                        raw_path = path_part.strip()
                        if not raw_path:
                            continue
                        path = os.path.abspath(os.path.expanduser(raw_path))
                        # Extract timestamp: "# YYYY-MM-DD HH:MM:SS" -> "YYYY-MM-DD HH:MM:SS"
                        timestamp = ts_part.strip().lstrip("#").strip()
                        # If duplicate, prefer active one
                        if path not in repos or active:
                            repos[path] = {"timestamp": timestamp, "active": active}
    except Exception as e:
        print(f"Error reading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    return search_dirs, repos


def scan_directories(search_dirs):
    """
    Scan directories for Git repositories recursively.

    Args:
        search_dirs (list): List of base directories to scan.

    Returns:
        set: A set of absolute paths to found Git repositories.
    """
    found_repos = set()
    for d in search_dirs:
        abs_search_path = os.path.abspath(os.path.expanduser(d))
        if not os.path.isdir(abs_search_path):
            print(
                f"Warning: Search directory not found: {abs_search_path}",
                file=sys.stderr,
            )
            continue

        for root, dirs, _ in os.walk(abs_search_path):
            if is_git_repo(root):
                found_repos.add(os.path.abspath(root))
                # Stop scanning deeper once a repo is found
                dirs[:] = []
    return found_repos


def update_repos_section(config_path, found_repos):
    """
    Update the [repos] section of the config file while preserving other sections.

    Args:
        config_path (str): Path to the config file.
        found_repos (set): Set of found repository paths.

    Returns:
        tuple: (newly_added, no_longer_present)
    """
    _, existing_repos = load_config(config_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    updated_repos = {}
    newly_added = []
    no_longer_present = []

    # Process existing entries
    for path, data in existing_repos.items():
        if path in found_repos:
            # Found again, keep existing timestamp and make active
            updated_repos[path] = {"timestamp": data["timestamp"], "active": True}
            found_repos.remove(path)
        else:
            # Not found in this scan, comment out
            updated_repos[path] = {"timestamp": data["timestamp"], "active": False}
            if data["active"]:
                no_longer_present.append(path)

    # Add newly found repos
    for path in found_repos:
        updated_repos[path] = {"timestamp": now_str, "active": True}
        newly_added.append(path)

    # Read the file to preserve the [search] section and other sections/comments
    lines = []
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip() for line in f]
    except Exception as e:  # pragma: no cover
        print(f"Error reading configuration for update: {e}", file=sys.stderr)
        sys.exit(1)

    # Find the range of the [repos] section
    repos_start = -1
    repos_end = -1
    for i, line in enumerate(lines):
        if line.strip().lower() == "[repos]":
            repos_start = i
            # Find next section or end of file
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("[") and lines[j].strip().endswith("]"):
                    repos_end = j
                    break
            else:
                repos_end = len(lines)
            break

    if repos_start == -1:
        # [repos] section not found, append it
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("[repos]")
        repos_start = len(lines) - 1
        repos_end = len(lines)

    # Prepare new [repos] content
    new_repos_lines = []
    for path in sorted(updated_repos.keys()):
        data = updated_repos[path]
        prefix = "" if data["active"] else "# "
        new_repos_lines.append(f"{prefix}{path} = # {data['timestamp']}")

    # Reconstruct the file content
    final_lines = lines[: repos_start + 1] + new_repos_lines + lines[repos_end:]

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines) + "\n")
    except Exception as e:  # pragma: no cover
        print(f"Error writing configuration: {e}", file=sys.stderr)
        sys.exit(1)

    return sorted(newly_added), sorted(no_longer_present)


def get_parser():
    """
    Construct the argument parser for git-repo-manager.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    try:
        ver = version("jfasoc")
    except Exception:  # pragma: no cover
        ver = "unknown"

    parser = argparse.ArgumentParser(
        description="Git Repo Manager - Scan and manage Git repositories.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {ver}")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Scan command
    subparsers.add_parser(
        "scan", help="Scan configured directories for Git repositories."
    )

    return parser


def main():
    """
    Main entry point for the git-repo-manager tool.
    """
    parser = get_parser()
    args = parser.parse_args()

    if args.command == "scan":
        config_path = get_config_path()
        search_dirs, _ = load_config(config_path)

        if not search_dirs:
            print("No search directories configured in [search] section.")
            return

        print(f"Scanning {len(search_dirs)} directories...")
        found = scan_directories(search_dirs)
        print(f"Found {len(found)} active repositories.")

        newly_added, no_longer_present = update_repos_section(config_path, found)

        if newly_added:
            print("\nNew repositories found:")
            for path in newly_added:
                print(f"  + {path}")

        if no_longer_present:
            print("\nRepositories no longer present (now commented out):")
            for path in no_longer_present:
                print(f"  - {path}")

        print("\nConfiguration updated.")
    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()
