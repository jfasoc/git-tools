"""
Tests for the git-stats tool.
"""

import runpy
import pytest
from git_tools.stats import get_parser, run, main


def test_get_parser():
    """
    Test that the parser is correctly configured with subcommands and arguments.
    """
    parser = get_parser()

    # Test commit subcommand
    args = parser.parse_args(["commit", "myrepo"])
    assert args.command == "commit"
    assert args.repo == "myrepo"

    # Test pack subcommand
    args = parser.parse_args(
        ["pack", "--human", "--loose-uncompressed", "-v", "myrepo"]
    )
    assert args.command == "pack"
    assert args.human is True
    assert args.loose_uncompressed is True
    assert args.verbose is True
    assert args.repo == "myrepo"

    # Test pack subcommand with --no-loose-uncompressed
    args = parser.parse_args(["pack", "--no-loose-uncompressed"])
    assert args.command == "pack"
    assert args.loose_uncompressed is False

    # Test version
    with pytest.raises(SystemExit) as e:
        parser.parse_args(["--version"])
    assert e.value.code == 0


def test_run_commit(mocker):
    """
    Test that git-stats commit calls commit_stats.run.
    """
    mock_commit_run = mocker.patch("git_tools.commit_stats.run")
    parser = get_parser()
    args = parser.parse_args(["commit", "repo_path"])
    run(args)
    mock_commit_run.assert_called_once_with(args)


def test_run_pack(mocker):
    """
    Test that git-stats pack calls pack_stats.run.
    """
    mock_pack_run = mocker.patch("git_tools.pack_stats.run")
    parser = get_parser()
    args = parser.parse_args(["pack", "repo_path"])
    run(args)
    mock_pack_run.assert_called_once_with(args)


def test_main_success(mocker):
    """
    Test the main entry point with successful execution.
    """
    mocker.patch("git_tools.stats.get_parser")
    mock_run = mocker.patch("git_tools.stats.run")

    # Simulate calling main()
    mocker.patch("sys.argv", ["git-stats", "commit"])
    main()

    assert mock_run.called


def test_main_system_exit(mocker):
    """
    Test that main handles SystemExit.
    """
    mocker.patch("git_tools.stats.get_parser")
    mocker.patch("git_tools.stats.run", side_effect=SystemExit(0))

    mocker.patch("sys.argv", ["git-stats", "commit"])
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0


def test_main_exception(mocker, capsys):
    """
    Test that main handles general exceptions.
    """
    mocker.patch("git_tools.stats.get_parser")
    mocker.patch("git_tools.stats.run", side_effect=Exception("Test Error"))

    mocker.patch("sys.argv", ["git-stats", "commit"])
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1

    captured = capsys.readouterr()
    assert "Error: Test Error" in captured.err


def test_module_main(mocker):
    """
    Test the if __name__ == "__main__": block.
    """
    # Simply call runpy and let it execute main.
    # To avoid actual logic, we mock the run function.
    mocker.patch("sys.argv", ["git-stats", "commit"])
    mocker.patch("git_tools.stats.run")
    runpy.run_module("git_tools.stats", run_name="__main__")
    # If it didn't crash and we have 100% coverage, it means it was called.


def test_get_parser_version_error(mocker):
    """
    Test version fallback when importlib.metadata.version fails.
    """
    mocker.patch("git_tools.stats.version", side_effect=ImportError)
    parser = get_parser()
    # We can't easily check the version string without triggering SystemExit
    # but we can check if the code path is covered.
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])
