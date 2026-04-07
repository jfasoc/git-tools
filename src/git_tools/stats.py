"""
Unified git statistics tool.

This module provides a single entry point for various git statistics tools,
including commit statistics and pack file statistics.
"""

import argparse
import sys
from importlib.metadata import version
from . import commit_stats
from . import pack_stats


def get_parser():
    """
    Construct the argument parser for the git-stats tool.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    try:
        ver = version("git-tools")
    except Exception:
        ver = "unknown"

    parser = argparse.ArgumentParser(
        description="Unified git statistics tool.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {ver}",
        help="Show the version and exit.",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="The statistics command to run.", required=True
    )

    # Commit subcommand
    commit_parser = subparsers.add_parser(
        "commit",
        description="Lists all commits with file change counts (Regular vs Symlinks).",
        help="Lists all commits with file change counts (Regular vs Symlinks).",
    )
    commit_parser.add_argument(
        "repo", nargs="?", default=".", help="Path to the git repository."
    )

    # Pack subcommand
    pack_parser = subparsers.add_parser(
        "pack",
        description="List git pack files and loose objects.",
        help="List git pack files and loose objects.",
    )
    pack_parser.add_argument(
        "-H",
        "--human",
        action="store_true",
        help="Display human-readable sizes (e.g., KiB, MiB).",
    )
    pack_parser.add_argument(
        "--loose-uncompressed",
        action="store_true",
        default=None,
        help="Include uncompressed size for loose objects (can be slow). "
        "Auto-enabled if <= 1000 loose objects.",
    )
    pack_parser.add_argument(
        "--no-loose-uncompressed",
        action="store_false",
        dest="loose_uncompressed",
        help="Disable uncompressed size for loose objects.",
    )
    pack_parser.add_argument(
        "--actual-size",
        action="store_true",
        help="Include the actual full uncompressed size of all objects (can be slow).",
    )
    pack_parser.add_argument(
        "-f",
        "--fast",
        action="store_true",
        help="Disable collection of data that takes long time (Deltas, Uncompressed, Actual).",
    )
    pack_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print how long time it took to obtain each set of data.",
    )
    pack_parser.add_argument(
        "repo", nargs="?", default=".", help="Path to the git repository."
    )

    return parser


def run(args):
    """
    Execute the git-stats tool with the provided arguments.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
    """
    if args.command == "commit":
        commit_stats.run(args)
    elif args.command == "pack":
        pack_stats.run(args)


def main():
    """
    Main entry point for the git-stats tool.
    """
    try:
        run(get_parser().parse_args())
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
