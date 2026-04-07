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


def get_pack_info(git_dir, pack_file, repo_path=None, include_actual=False):
    """
    Gather statistics for a specific pack file.

    Calculates the number of objects, deltas, total uncompressed size,
    and compressed size of the pack file. Optionally calculates the
    total actual uncompressed size of all objects.

    Args:
        git_dir (str): Absolute path to the .git directory.
        pack_file (str): Filename of the pack file.
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).
        include_actual (bool, optional): Whether to calculate actual uncompressed
                                          size. Defaults to False.

    Returns:
        tuple: (object_count, delta_count, size, uncompressed_size, actual_size)
            object_count (int): Number of objects in the pack file.
            delta_count (int): Number of delta objects in the pack file.
            size (int): Compressed size of the pack file in bytes.
            uncompressed_size (int): Total uncompressed size of all objects (deltas)
                                      in bytes.
            actual_size (int or None): Total actual uncompressed size of all
                                        objects in bytes, or None if not calculated.
    """
    pack_path = os.path.join(git_dir, "objects", "pack", pack_file)

    # Get number of objects
    output = run_git_command(["verify-pack", "-v", pack_path], repo_path)

    # The output of verify-pack -v lists objects:
    # SHA-1 type size size-in-pack-file offset-in-pack-file [depth base-SHA-1]

    lines = output.strip().split("\n")
    object_count = 0
    delta_count = 0
    uncompressed_size = 0
    object_shas = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and parts[1] in ("commit", "tree", "blob", "tag"):
            object_count += 1
            if len(parts) >= 7:
                delta_count += 1
            try:
                uncompressed_size += int(parts[2])
                if include_actual:
                    object_shas.append(parts[0])
            except (ValueError, IndexError):
                pass

    actual_size = None
    if include_actual and object_shas:
        # Use git cat-file --batch-check to get full sizes efficiently
        output = run_git_command(
            ["cat-file", "--batch-check=%(objectsize)"],
            repo_path=repo_path,
            input="\n".join(object_shas),
        )
        actual_size = 0
        for line in output.strip().split("\n"):
            if line:
                actual_size += int(line)
    elif include_actual:
        actual_size = 0

    # Get size
    size = os.path.getsize(pack_path)

    return object_count, delta_count, size, uncompressed_size, actual_size


def get_pack_info_fast(git_dir, pack_file, repo_path=None):
    """
    Gather basic statistics for a specific pack file quickly.

    Counts the number of objects using git show-index. This is much faster
    than verify-pack -v as it doesn't process the entire pack file.

    Args:
        git_dir (str): Absolute path to the .git directory.
        pack_file (str): Filename of the pack file.
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).

    Returns:
        tuple: (object_count, delta_count, size, uncompressed_size, actual_size)
            object_count (int): Number of objects in the pack file.
            delta_count (int): Always 0 in fast mode.
            size (int): Compressed size of the pack file in bytes.
            uncompressed_size (int): Always 0 in fast mode.
            actual_size (int or None): Always None in fast mode.
    """
    pack_path = os.path.join(git_dir, "objects", "pack", pack_file)
    idx_path = pack_path[:-5] + ".idx"

    # Count objects using git show-index
    # The output format for show-index is one line per object.
    with open(idx_path, "rb") as f:
        idx_content = f.read()
    cmd = ["git"]
    if repo_path:
        cmd.extend(["-C", repo_path])
    cmd.extend(["show-index"])

    import subprocess

    result = subprocess.run(cmd, input=idx_content, capture_output=True, check=True)
    output = result.stdout.decode("utf-8")
    object_count = len(output.splitlines())

    # Get size
    size = os.path.getsize(pack_path)

    return object_count, 0, size, 0, None


def get_loose_count(repo_path=None):
    """
    Get the count of loose objects in the repository.

    Args:
        repo_path (str, optional): Path to the git repository. Defaults to None (CWD).

    Returns:
        int: The number of loose objects.
    """
    try:
        git_dir = get_git_dir(repo_path)
        obj_dir = os.path.join(git_dir, "objects")
        count = 0
        if os.path.exists(obj_dir):
            for d in os.listdir(obj_dir):
                if len(d) == 2 and all(c in "0123456789abcdef" for c in d):
                    d_path = os.path.join(obj_dir, d)
                    count += len(os.listdir(d_path))
        return count
    except Exception:
        return 0


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
        tuple: (count, deltas, compressed_size, uncompressed_size)
            count (int): Number of loose objects.
            deltas (int): Number of delta loose objects (always 0).
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

        return count, 0, compressed_size, uncompressed_size
    except Exception:
        return 0, 0, 0, 0 if include_uncompressed else None


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
        default=None,
        help="Include uncompressed size for loose objects (can be slow). "
        "Auto-enabled if <= 1000 loose objects.",
    )
    parser.add_argument(
        "--no-loose-uncompressed",
        action="store_false",
        dest="loose_uncompressed",
        help="Disable uncompressed size for loose objects.",
    )
    parser.add_argument(
        "--actual-size",
        action="store_true",
        help="Include the actual full uncompressed size of all objects (can be slow).",
    )
    parser.add_argument(
        "-f",
        "--fast",
        action="store_true",
        help="Disable collection of data that takes long time (Deltas, Uncompressed, Actual).",
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


def collect_stats(
    repo_path,
    verbose=False,
    loose_uncompressed=False,
    include_actual=False,
    fast=False,
):
    """
    Gather storage statistics for the Git repository.

    Args:
        repo_path (str): Path to the git repository.
        verbose (bool, optional): Whether to print timing info. Defaults to False.
        loose_uncompressed (bool, optional): Whether to calculate uncompressed
                                            size for loose objects.
                                            Defaults to False.
        include_actual (bool, optional): Whether to calculate actual uncompressed
                                          size for objects. Defaults to False.
        fast (bool, optional): Whether to disable expensive data collection.
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
    total_deltas = 0
    total_size = 0
    total_uncompressed = 0
    total_actual = 0 if include_actual else None

    for pf in pack_files:
        start_time = time.perf_counter()
        if fast:
            count, deltas, size, uncompressed, actual = get_pack_info_fast(
                git_dir, pf, repo_path
            )
        else:
            count, deltas, size, uncompressed, actual = get_pack_info(
                git_dir, pf, repo_path, include_actual
            )
        duration = (time.perf_counter() - start_time) * 1000
        if verbose:
            print(f"{duration:10.3f} ms get info for {pf}")

        pack_data.append(
            {
                "name": pf,
                "objects": count,
                "deltas": deltas,
                "size": size,
                "uncompressed": uncompressed,
                "actual": actual,
            }
        )
        total_objects += count
        total_deltas += deltas
        total_size += size
        total_uncompressed += uncompressed
        if actual is not None:
            total_actual += actual

    start_time = time.perf_counter()
    l_count, l_deltas, l_size, l_uncomp = get_loose_info(
        repo_path, loose_uncompressed and not fast
    )
    duration = (time.perf_counter() - start_time) * 1000
    if verbose:
        print(f"{duration:10.3f} ms get info for loose objects")

    total_duration = (time.perf_counter() - total_time_start) * 1000

    total_objects += l_count
    total_deltas += l_deltas
    total_size += l_size
    if l_uncomp is not None:
        total_uncompressed += l_uncomp
        if include_actual:
            total_actual += l_uncomp

    # Sort pack data by object count (descending)
    pack_data.sort(key=lambda x: x["objects"], reverse=True)

    return {
        "pack_data": pack_data,
        "total_objects": total_objects,
        "total_deltas": total_deltas,
        "total_size": total_size,
        "total_uncompressed": total_uncompressed,
        "total_actual": total_actual,
        "loose_count": l_count,
        "loose_deltas": l_deltas,
        "loose_size": l_size,
        "loose_uncomp": l_uncomp,
        "total_duration": total_duration,
        "fast": fast,
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
    total_deltas = stats["total_deltas"]
    total_size = stats["total_size"]
    total_uncompressed = stats["total_uncompressed"]
    total_actual = stats["total_actual"]
    loose_count = stats["loose_count"]
    loose_deltas = stats["loose_deltas"]
    loose_size = stats["loose_size"]
    loose_uncomp = stats["loose_uncomp"]
    fast = stats.get("fast", False)

    # Header
    header = f"{'Pack Name':<60} {'Objects':>10} "
    if not fast:
        header += f"{'Deltas':>10} "
    header += f"{'Size':>12} "
    if not fast:
        header += f"{'Uncompressed':>12} "
    if total_actual is not None:
        header += f"{'Actual':>12} "
    if not fast:
        header += f"{'Comp %':>8} "
    if total_actual is not None:
        header += f"{'Act %':>8} "
    header += f"{'% Obj':>8} {'% Size':>8}"

    print(header)
    print("-" * len(header))

    for data in pack_data:
        p_obj = (data["objects"] / total_objects * 100) if total_objects > 0 else 0
        p_size = (data["size"] / total_size * 100) if total_size > 0 else 0

        row = f"{data['name']:<60} {data['objects']:>10} "
        if not fast:
            row += f"{data['deltas']:>10} "
        row += f"{format_size(data['size'], human):>12} "
        if not fast:
            row += f"{format_size(data['uncompressed'], human):>12} "
        if total_actual is not None:
            if data["actual"] is not None:
                actual_str = format_size(data["actual"], human)
            else:
                actual_str = "N/A"
            row += f"{actual_str:>12} "

        if not fast:
            comp_ratio = (
                (data["size"] / data["uncompressed"] * 100)
                if data["uncompressed"]
                else 0
            )
            row += f"{comp_ratio:>7.1f}% "

        if total_actual is not None:
            if data["actual"] is not None:
                act_ratio = (
                    (data["size"] / data["actual"] * 100) if data["actual"] else 0
                )
                act_ratio_str = f"{act_ratio:>7.1f}%"
            else:
                act_ratio_str = "N/A"
            row += f"{act_ratio_str:>8} "

        row += f"{p_obj:>7.1f}% {p_size:>7.1f}%"
        print(row)

    # Loose objects section
    print("-" * len(header))
    p_obj_loose = (loose_count / total_objects * 100) if total_objects > 0 else 0
    p_size_loose = (loose_size / total_size * 100) if total_size > 0 else 0

    row = f"{'Loose Objects':<60} {loose_count:>10} "
    if not fast:
        row += f"{loose_deltas:>10} "
    row += f"{format_size(loose_size, human):>12} "

    if not fast:
        if loose_uncomp is not None:
            loose_uncomp_str = format_size(loose_uncomp, human)
        else:
            loose_uncomp_str = "N/A"
        row += f"{loose_uncomp_str:>12} "

    if total_actual is not None:
        if loose_uncomp is not None:
            actual_loose_str = format_size(loose_uncomp, human)
        else:
            actual_loose_str = "N/A"
        row += f"{actual_loose_str:>12} "

    if not fast:
        if loose_uncomp is not None:
            comp_ratio_loose = (loose_size / loose_uncomp * 100) if loose_uncomp else 0
            comp_ratio_loose_str = f"{comp_ratio_loose:>7.1f}%"
        else:
            comp_ratio_loose_str = "N/A"
        row += f"{comp_ratio_loose_str:>8} "

    if total_actual is not None:
        if loose_uncomp is not None:
            comp_ratio_loose = (loose_size / loose_uncomp * 100) if loose_uncomp else 0
            act_ratio_loose_str = f"{comp_ratio_loose:>7.1f}%"
        else:
            act_ratio_loose_str = "N/A"
        row += f"{act_ratio_loose_str:>8} "

    row += f"{p_obj_loose:>7.1f}% {p_size_loose:>7.1f}%"
    print(row)

    # Total
    print("=" * len(header))
    row = f"{'Total':<60} {total_objects:>10} "
    if not fast:
        row += f"{total_deltas:>10} "
    row += f"{format_size(total_size, human):>12} "

    if not fast:
        # If loose_uncomp is N/A, the total uncompressed is also incomplete/N/A
        if loose_uncomp is None and loose_count > 0:
            total_uncompressed_str = "N/A"
        else:
            total_uncompressed_str = format_size(total_uncompressed, human)
        row += f"{total_uncompressed_str:>12} "

    if total_actual is not None:
        if loose_uncomp is None and loose_count > 0:
            total_actual_str = "N/A"
        else:
            total_actual_str = format_size(total_actual, human)
        row += f"{total_actual_str:>12} "

    if not fast:
        if loose_uncomp is None and loose_count > 0:
            total_comp_ratio_str = "N/A"
        else:
            total_comp_ratio = (
                (total_size / total_uncompressed * 100) if total_uncompressed else 0
            )
            total_comp_ratio_str = f"{total_comp_ratio:>7.1f}%"
        row += f"{total_comp_ratio_str:>8} "

    if total_actual is not None:
        if loose_uncomp is None and loose_count > 0:
            total_act_ratio_str = "N/A"
        else:
            total_act_ratio = (total_size / total_actual * 100) if total_actual else 0
            total_act_ratio_str = f"{total_act_ratio:>7.1f}%"
        row += f"{total_act_ratio_str:>8} "

    row += f"{100.0:>7.1f}% {100.0:>7.1f}%"
    print(row)


def run(args):
    """
    Execute the pack-stats tool with the provided arguments.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
    """
    try:
        loose_uncompressed = args.loose_uncompressed
        if loose_uncompressed is None:
            # If not specified, auto-enable if <= 1000 loose objects
            count = get_loose_count(args.repo)
            loose_uncompressed = count <= 1000

        stats = collect_stats(
            args.repo,
            args.verbose,
            loose_uncompressed,
            args.actual_size,
            args.fast,
        )
        print_stats(stats, args.human, args.verbose)
    except SystemExit:
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
