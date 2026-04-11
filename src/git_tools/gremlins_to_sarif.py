"""Converter for pytest-gremlins JSON reports to SARIF format.

This module provides functionality to convert mutation testing results from
pytest-gremlins into the Standard Static Analysis Results Interchange Format (SARIF)
for integration with GitHub Code Scanning.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict


def get_parser() -> argparse.ArgumentParser:
    """Creates the argument parser for the SARIF converter.

    Returns:
        The configured argparse.ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Convert pytest-gremlins JSON report to SARIF format."
    )
    parser.add_argument(
        "input", help="Path to the pytest-gremlins JSON report (gremlins.json)"
    )
    parser.add_argument(
        "--output", "-o", default="gremlins.sarif", help="Path to save the SARIF report"
    )
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="Root directory of the repository for path normalization",
    )
    return parser


def convert_to_sarif(
    gremlins_data: Dict[str, Any], repo_root: str
) -> Dict[str, Any]:
    """Converts gremlins JSON data to SARIF format.

    Args:
        gremlins_data: The parsed JSON data from pytest-gremlins.
        repo_root: The root directory of the repository.

    Returns:
        A dictionary representing the SARIF report.
    """
    results = []
    rules = {}

    for result in gremlins_data.get("results", []):
        if result.get("status") != "survived":
            continue

        rule_id = f"gremlin-{result.get('operator')}"
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "shortDescription": {
                    "text": f"Mutation survived: {result.get('operator')}"
                },
                "defaultConfiguration": {"level": "warning"},
                "helpUri": "https://github.com/mikelane/pytest-gremlins",
            }

        file_path = result.get("file_path", "")
        if os.path.isabs(file_path):
            file_path = os.path.relpath(file_path, repo_root)

        sarif_result = {
            "ruleId": rule_id,
            "message": {"text": f"Gremlin survived: {result.get('description')}"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": file_path},
                        "region": {"startLine": result.get("line_number")},
                    }
                }
            ],
        }
        results.append(sarif_result)

    sarif = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "pytest-gremlins",
                        "informationUri": "https://github.com/mikelane/pytest-gremlins",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return sarif


def run(args: argparse.Namespace) -> None:
    """Orchestrates the conversion process.

    Args:
        args: The parsed command-line arguments.
    """
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            gremlins_data = json.load(f)

        sarif_data = convert_to_sarif(gremlins_data, args.repo_root)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(sarif_data, f, indent=2)

        print(f"Successfully converted {args.input} to {args.output}")

    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the script."""
    run(get_parser().parse_args())


if __name__ == "__main__":
    main()
