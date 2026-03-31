"""
List git pack files and loose objects.

This module provides a command-line tool to analyze the storage efficiency of
a Git repository by reporting object counts and sizes for pack files and
loose objects.
"""

import os
import sys
import argparse
import time
from importlib.metadata import version
from .utils import run_git_command


def get_git_dir(repo_path=None):
    """
    Retrieve the absolute path to the .git directory.

    Args:
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).

    Returns:
        str: The absolute path to the .git directory.
    """
    git_dir = run_git_command(["rev-parse", "--git-dir"], repo_path).strip()
    if not os.path.isabs(git_dir) and repo_path:
        git_dir = os.path.abspath(os.path.join(repo_path, git_dir))
    return git_dir


def get_pack_files(git_dir):
    """
    List all .pack files in the repository.

    Args:
        git_dir (str): Absolute path to the .git directory.

    Returns:
        list: A list of filenames of the pack files.
    """
    pack_dir = os.path.join(git_dir, "objects", "pack")
    if not os.path.exists(pack_dir):
        return []

    return [f for f in os.listdir(pack_dir) if f.endswith(".pack")]


def get_pack_info(git_dir, pack_file, repo_path=None):
    """
    Gather statistics for a specific pack file.

    Calculates the number of objects, the total uncompressed size, and
    the compressed size of the pack file.

    Args:
        git_dir (str): Absolute path to the .git directory.
        pack_file (str): Filename of the pack file.
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).

    Returns:
        tuple: (object_count, size, uncompressed_size)
            object_count (int): Number of objects in the pack file.
            size (int): Compressed size of the pack file in bytes.
            uncompressed_size (int): Total uncompressed size of all objects in bytes.
    """
    pack_path = os.path.join(git_dir, "objects", "pack", pack_file)

    # Get number of objects
    output = run_git_command(["verify-pack", "-v", pack_path], repo_path)

    # The output of verify-pack -v ends with something like:
    # non delta: 15 objects
    # chain length = 1: 2 objects
    # .git/objects/pack/pack-xxx.pack: ok

    lines = output.strip().split("\n")
    object_count = 0
    uncompressed_size = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and parts[1] in ("commit", "tree", "blob", "tag"):
            object_count += 1
            try:
                uncompressed_size += int(parts[2])
            except (ValueError, IndexError):
                pass

    # Get size
    size = os.path.getsize(pack_path)

    return object_count, size, uncompressed_size


def get_loose_info(repo_path=None, include_uncompressed=False):
    """
    Gather statistics for loose objects in the repository.

    Calculates the number of loose objects and their total size. Optionally
    calculates the total uncompressed size.

    Args:
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).
        include_uncompressed (bool, optional): Whether to calculate uncompressed
                                                size. Defaults to False.

    Returns:
        tuple: (count, compressed_size, uncompressed_size)
            count (int): Number of loose objects.
            compressed_size (int): Total size of loose objects on disk in bytes.
            uncompressed_size (int or None): Total uncompressed size in bytes,
                                            or None if not calculated.
    """
    # We walk the objects directory to get the count and the sum of actual file sizes.
    # This avoids "size on disk" (which includes filesystem overhead/blocks).
    try:
        git_dir = get_git_dir(repo_path)
        obj_dir = os.path.join(git_dir, "objects")
        count = 0
        compressed_size = 0
        loose_objects = []

        if os.path.exists(obj_dir):
            for d in os.listdir(obj_dir):
                if len(d) == 2 and all(c in "0123456789abcdef" for c in d):
                    d_path = os.path.join(obj_dir, d)
                    for f in os.listdir(d_path):
                        f_path = os.path.join(d_path, f)
                        count += 1
                        compressed_size += os.path.getsize(f_path)
                        if include_uncompressed:
                            loose_objects.append(d + f)

        uncompressed_size = None
        if include_uncompressed and loose_objects:
            # Use git cat-file --batch-check to get sizes efficiently
            output = run_git_command(
                ["cat-file", "--batch-check=%(objectsize)"],
                repo_path=repo_path,
                input="\n".join(loose_objects),
            )

            uncompressed_size = 0
            for line in output.strip().split("\n"):
                if line:
                    uncompressed_size += int(line)
        elif include_uncompressed:
            uncompressed_size = 0

        return count, compressed_size, uncompressed_size
    except Exception:
        return 0, 0, 0 if include_uncompressed else None


def format_size(size_bytes, human=False):
    """
    Format a size in bytes into a string.

    Args:
        size_bytes (int): Size in bytes.
        human (bool, optional): Whether to use human-readable format (KiB, MiB).
                                Defaults to False.

    Returns:
        str: Formatted size string.
    """
    if not human:
        return f"{size_bytes:,}".replace(",", ".")

    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KiB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MiB"


def get_parser():
    """
    Construct the argument parser for the pack-stats tool.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    try:
        ver = version("git-tools")
    except Exception:
        ver = "unknown"
    parser = argparse.ArgumentParser(
        description="List git pack files and loose objects.", add_help=False
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="show this help message and exit",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {ver}",
        help="Show the version and exit.",
    )
    parser.add_argument(
        "-H",
        "--human",
        action="store_true",
        help="Display human-readable sizes (e.g., KiB, MiB).",
    )
    parser.add_argument(
        "--loose-uncompressed",
        action="store_true",
        help="Include uncompressed size for loose objects (can be slow).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print how long time it took to obtain each set of data.",
    )
    parser.add_argument(
        "repo", nargs="?", default=".", help="Path to the git repository."
    )
    return parser


def collect_stats(repo_path, verbose=False, loose_uncompressed=False):
    """
    Gather storage statistics for the Git repository.

    Args:
        repo_path (str): Path to the git repository.
        verbose (bool, optional): Whether to print timing info. Defaults to False.
        loose_uncompressed (bool, optional): Whether to calculate uncompressed
                                            size for loose objects.
                                            Defaults to False.

    Returns:
        dict: A dictionary containing all collected statistics and total duration.
    """
    total_time_start = time.perf_counter()

    start_time = time.perf_counter()
    git_dir = get_git_dir(repo_path)
    pack_files = get_pack_files(git_dir)
    duration = (time.perf_counter() - start_time) * 1000
    if verbose:
        print(f"{duration:10.3f} ms get info for git repository")

    pack_data = []
    total_objects = 0
    total_size = 0
    total_uncompressed = 0

    for pf in pack_files:
        start_time = time.perf_counter()
        count, size, uncompressed = get_pack_info(git_dir, pf, repo_path)
        duration = (time.perf_counter() - start_time) * 1000
        if verbose:
            print(f"{duration:10.3f} ms get info for {pf}")

        pack_data.append(
            {"name": pf, "objects": count, "size": size, "uncompressed": uncompressed}
        )
        total_objects += count
        total_size += size
        total_uncompressed += uncompressed

    start_time = time.perf_counter()
    loose_count, loose_size, loose_uncomp = get_loose_info(repo_path, loose_uncompressed)
    duration = (time.perf_counter() - start_time) * 1000
    if verbose:
        print(f"{duration:10.3f} ms get info for loose objects")

    total_duration = (time.perf_counter() - total_time_start) * 1000

    total_objects += loose_count
    total_size += loose_size
    if loose_uncomp is not None:
        total_uncompressed += loose_uncomp

    # Sort pack data by object count (descending)
    pack_data.sort(key=lambda x: x["objects"], reverse=True)

    return {
        "pack_data": pack_data,
        "total_objects": total_objects,
        "total_size": total_size,
        "total_uncompressed": total_uncompressed,
        "loose_count": loose_count,
        "loose_size": loose_size,
        "loose_uncomp": loose_uncomp,
        "total_duration": total_duration,
    }


def print_stats(stats, human=False, verbose=False):
    """
    Print the collected storage statistics in a table.

    Args:
        stats (dict): The dictionary of collected statistics.
        human (bool, optional): Whether to use human-readable format.
                                Defaults to False.
        verbose (bool, optional): Whether to print the total duration.
                                  Defaults to False.
    """
    if verbose:
        print(f"{stats['total_duration']:10.3f} ms total time")
        print()

    pack_data = stats["pack_data"]
    total_objects = stats["total_objects"]
    total_size = stats["total_size"]
    total_uncompressed = stats["total_uncompressed"]
    loose_count = stats["loose_count"]
    loose_size = stats["loose_size"]
    loose_uncomp = stats["loose_uncomp"]

    # Header
    header = (
        f"{'Pack Name':<60} {'Objects':>10} {'Size':>12} "
        f"{'Uncompressed':>12} {'Comp %':>8} {'% Obj':>8} {'% Size':>8}"
    )
    print(header)
    print("-" * len(header))

    for data in pack_data:
        p_obj = (data["objects"] / total_objects * 100) if total_objects > 0 else 0
        p_size = (data["size"] / total_size * 100) if total_size > 0 else 0
        comp_ratio = (
            (data["size"] / data["uncompressed"] * 100) if data["uncompressed"] else 0
        )
        print(
            f"{data['name']:<60} {data['objects']:>10} "
            f"{format_size(data['size'], human):>12} "
            f"{format_size(data['uncompressed'], human):>12} "
            f"{comp_ratio:>7.1f}% {p_obj:>7.1f}% {p_size:>7.1f}%"
        )

    # Loose objects section
    print("-" * len(header))
    p_obj_loose = (loose_count / total_objects * 100) if total_objects > 0 else 0
    p_size_loose = (loose_size / total_size * 100) if total_size > 0 else 0
    if loose_uncomp is not None:
        comp_ratio_loose = (loose_size / loose_uncomp * 100) if loose_uncomp else 0
        loose_uncomp_str = format_size(loose_uncomp, human)
        comp_ratio_loose_str = f"{comp_ratio_loose:>7.1f}%"
    else:
        loose_uncomp_str = f"{'N/A':>12}"
        comp_ratio_loose_str = f"{'N/A':>8}"

    print(
        f"{'Loose Objects':<60} {loose_count:>10} "
        f"{format_size(loose_size, human):>12} "
        f"{loose_uncomp_str:>12} {comp_ratio_loose_str} "
        f"{p_obj_loose:>7.1f}% {p_size_loose:>7.1f}%"
    )

    # Total
    print("=" * len(header))
    total_comp_ratio = (
        (total_size / total_uncompressed * 100) if total_uncompressed else 0
    )
    # If loose_uncomp is N/A, the total uncompressed is also incomplete/N/A
    if loose_uncomp is None and loose_count > 0:
        total_uncompressed_str = f"{'N/A':>12}"
        total_comp_ratio_str = f"{'N/A':>8}"
    else:
        total_uncompressed_str = format_size(total_uncompressed, human)
        total_comp_ratio_str = f"{total_comp_ratio:>7.1f}%"

    print(
        f"{'Total':<60} {total_objects:>10} "
        f"{format_size(total_size, human):>12} "
        f"{total_uncompressed_str:>12} {total_comp_ratio_str} "
        f"{100.0:>7.1f}% {100.0:>7.1f}%"
    )


def run(args):
    """
    Execute the pack-stats tool with the provided arguments.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
    """
    try:
        stats = collect_stats(args.repo, args.verbose, args.loose_uncompressed)
        print_stats(stats, args.human, args.verbose)
    except SystemExit:
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main entry point for the git-pack-stats tool.
    """
    run(get_parser().parse_args())


if __name__ == "__main__":
    main()
