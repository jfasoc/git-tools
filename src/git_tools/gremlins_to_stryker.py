"""Converter for pytest-gremlins JSON reports to Stryker format.

This module provides functionality to convert mutation testing results from
pytest-gremlins into the Stryker mutation report format for integration with the
Stryker Mutator Dashboard.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict


def get_parser() -> argparse.ArgumentParser:
    """Creates the argument parser for the Stryker converter.

    Returns:
        The configured argparse.ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Convert pytest-gremlins JSON report to Stryker format."
    )
    parser.add_argument(
        "input", help="Path to the pytest-gremlins JSON report (gremlins.json)"
    )
    parser.add_argument(
        "--output", "-o", default="stryker.json", help="Path to save the Stryker report"
    )
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="Root directory of the repository for path normalization",
    )
    return parser


def convert_to_stryker(
    gremlins_data: Dict[str, Any], repo_root: str
) -> Dict[str, Any]:
    """Converts gremlins JSON data to Stryker format.

    Args:
        gremlins_data: The parsed JSON data from pytest-gremlins.
        repo_root: The root directory of the repository.

    Returns:
        A dictionary representing the Stryker report.
    """
    files = {}

    for result in gremlins_data.get("results", []):
        file_path = result.get("file_path", "")
        if os.path.isabs(file_path):
            file_path = os.path.relpath(file_path, repo_root)

        if file_path not in files:
            # We don't have the full source content here, but Stryker format
            # requires 'source'. We'll try to read it if possible.
            source = ""
            full_path = os.path.join(repo_root, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        source = f.read()
                except Exception:
                    pass

            files[file_path] = {"source": source, "mutants": []}

        status_map = {
            "zapped": "Killed",
            "survived": "Survived",
            "timeout": "TimedOut",
            "error": "RuntimeError",
        }

        mutant = {
            "id": result.get("gremlin_id"),
            "mutatorName": result.get("operator"),
            "replacement": result.get("description"),
            "location": {
                "start": {"line": result.get("line_number"), "column": 1},
                "end": {"line": result.get("line_number"), "column": 100},
            },
            "status": status_map.get(result.get("status"), "Unknown"),
        }
        files[file_path]["mutants"].append(mutant)

    stryker = {
        "schemaVersion": "1",
        "thresholds": {"high": 80, "low": 60},
        "files": files,
    }
    return stryker


def run(args: argparse.Namespace) -> None:
    """Orchestrates the conversion process.

    Args:
        args: The parsed command-line arguments.
    """
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            gremlins_data = json.load(f)

        stryker_data = convert_to_stryker(gremlins_data, args.repo_root)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(stryker_data, f, indent=2)

        print(f"Successfully converted {args.input} to {args.output}")

    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the script."""
    run(get_parser().parse_args())


if __name__ == "__main__":
    main()
