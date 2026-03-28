import os
import subprocess
import sys
import argparse
from importlib.metadata import version

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

def get_git_dir(repo_path=None):
    git_dir = run_git_command(["rev-parse", "--git-dir"], repo_path).strip()
    if not os.path.isabs(git_dir) and repo_path:
        git_dir = os.path.abspath(os.path.join(repo_path, git_dir))
    return git_dir

def get_pack_files(git_dir):
    pack_dir = os.path.join(git_dir, "objects", "pack")
    if not os.path.exists(pack_dir):
        return []

    return [f for f in os.listdir(pack_dir) if f.endswith(".pack")]

def get_pack_info(git_dir, pack_file, repo_path=None):
    pack_path = os.path.join(git_dir, "objects", "pack", pack_file)

    # Get number of objects
    output = run_git_command(["verify-pack", "-v", pack_path], repo_path)

    # The output of verify-pack -v ends with something like:
    # non delta: 15 objects
    # chain length = 1: 2 objects
    # .git/objects/pack/pack-xxx.pack: ok

    lines = output.strip().split("\n")
    object_count = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ("commit", "tree", "blob", "tag"):
            object_count += 1

    # Get size
    size = os.path.getsize(pack_path)

    return object_count, size

def get_loose_info(repo_path=None):
    output = run_git_command(["count-objects", "-v"], repo_path)
    stats = {}
    for line in output.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            stats[key.strip()] = value.strip()

    count = int(stats.get("count", 0))
    size = int(stats.get("size", 0)) * 1024 # count-objects reports size in KiB

    return count, size

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KiB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MiB"

def get_parser():
    try:
        ver = version("jfasoc")
    except Exception:
        ver = "unknown"
    parser = argparse.ArgumentParser(description="List git pack files and loose objects.")
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {ver}",
        help="Show the version and exit."
    )
    parser.add_argument("repo", nargs="?", default=".", help="Path to the git repository.")
    return parser

def main():
    parser = get_parser()
    args = parser.parse_args()

    repo_path = args.repo

    try:
        git_dir = get_git_dir(repo_path)
        pack_files = get_pack_files(git_dir)
    except SystemExit:
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    pack_data = []
    total_objects = 0
    total_size = 0

    for pf in pack_files:
        count, size = get_pack_info(git_dir, pf, repo_path)
        pack_data.append({
            "name": pf,
            "objects": count,
            "size": size
        })
        total_objects += count
        total_size += size

    loose_count, loose_size = get_loose_info(repo_path)
    total_objects += loose_count
    total_size += loose_size

    # Sort pack data by object count (descending)
    pack_data.sort(key=lambda x: x["objects"], reverse=True)

    # Header
    header = f"{'Pack Name':<60} {'Objects':>10} {'Size':>12} {'% Obj':>8} {'% Size':>8}"
    print(header)
    print("-" * len(header))

    for data in pack_data:
        p_obj = (data['objects'] / total_objects * 100) if total_objects > 0 else 0
        p_size = (data['size'] / total_size * 100) if total_size > 0 else 0
        print(f"{data['name']:<60} {data['objects']:>10} {format_size(data['size']):>12} {p_obj:>7.1f}% {p_size:>7.1f}%")

    # Loose objects section
    print("-" * len(header))
    p_obj_loose = (loose_count / total_objects * 100) if total_objects > 0 else 0
    p_size_loose = (loose_size / total_size * 100) if total_size > 0 else 0
    print(f"{'Loose Objects':<60} {loose_count:>10} {format_size(loose_size):>12} {p_obj_loose:>7.1f}% {p_size_loose:>7.1f}%")

    # Total
    print("=" * len(header))
    print(f"{'Total':<60} {total_objects:>10} {format_size(total_size):>12} {100.0:>7.1f}% {100.0:>7.1f}%")

if __name__ == "__main__": # pragma: no cover
    main()
