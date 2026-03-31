import subprocess
import pytest
import runpy
from unittest.mock import patch
from git_tools.commit_stats import run_git_command, get_commits, get_commit_stats, main


def test_run_git_command_success(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = "output"
    mock_run.return_value.returncode = 0

    assert run_git_command(["args"]) == "output"
    mock_run.assert_called_with(
        ["git", "args"], capture_output=True, text=True, check=True, input=None
    )


def test_run_git_command_with_repo(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = "output"
    mock_run.return_value.returncode = 0

    assert run_git_command(["args"], repo_path="/tmp/repo") == "output"
    mock_run.assert_called_with(
        ["git", "-C", "/tmp/repo", "args"],
        capture_output=True,
        text=True,
        check=True,
        input=None,
    )


def test_run_git_command_error(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        1, ["git", "args"], stderr="error message"
    )

    with pytest.raises(SystemExit) as excinfo:
        run_git_command(["args"])
    assert excinfo.value.code == 1


def test_run_git_command_not_found(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = FileNotFoundError()

    with pytest.raises(SystemExit) as excinfo:
        run_git_command(["args"])
    assert excinfo.value.code == 1


def test_get_commits(mocker):
    mocker.patch("git_tools.commit_stats.run_git_command", return_value="abc\ndef\n")
    assert get_commits() == ["abc", "def"]


def test_get_commits_empty(mocker):
    mocker.patch("git_tools.commit_stats.run_git_command", return_value="")
    assert get_commits() == []


def test_get_commit_stats_basic(mocker):
    output = (
        ":100644 100644 123 456 M\tfile1\n"
        ":000000 100644 000 789 A\tfile2\n"
        ":100644 000000 456 000 D\tfile3\n"
    )
    mocker.patch("git_tools.commit_stats.run_git_command", return_value=output)

    reg, sym = get_commit_stats("abc")
    assert reg == {"A": 1, "M": 1, "D": 1}
    assert sym == {"A": 0, "M": 0, "D": 0}


def test_get_commit_stats_symlinks(mocker):
    output = (
        ":000000 120000 000 123 A\tsym1\n"
        ":120000 120000 123 456 M\tsym2\n"
        ":120000 000000 456 000 D\tsym3\n"
    )
    mocker.patch("git_tools.commit_stats.run_git_command", return_value=output)

    reg, sym = get_commit_stats("abc")
    assert reg == {"A": 0, "M": 0, "D": 0}
    assert sym == {"A": 1, "M": 1, "D": 1}


def test_get_commit_stats_advanced(mocker):
    output = (
        ":100644 100644 123 456 R100\told\tnew\n"
        "\n"  # This should trigger "if not line: continue"
        ":100644 100644 123 456 C100\told2\tnew2\n"
        ":100644 120000 123 456 T\tfile_to_sym\n"
        ":120000 100644 123 456 T\tsym_to_file\n"
        ":100755 100644 123 456 T\tmode_change\n"
        "short_line\n"
        ":100644 100644 123 456 X\tunknown\n"
    )
    mocker.patch("git_tools.commit_stats.run_git_command", return_value=output)

    reg, sym = get_commit_stats("abc")
    assert reg == {"A": 2, "M": 2, "D": 1}
    assert sym == {"A": 1, "M": 0, "D": 1}


def test_main_no_commits(mocker, capsys):
    mocker.patch("git_tools.commit_stats.get_commits", return_value=[])
    mocker.patch("sys.argv", ["git-commit-stats"])
    main()
    captured = capsys.readouterr()
    assert "No commits found." in captured.out


def test_main_with_commits(mocker, capsys):
    mocker.patch("git_tools.commit_stats.get_commits", return_value=["abc", "def"])
    mocker.patch(
        "git_tools.commit_stats.get_commit_stats",
        side_effect=[
            ({"A": 1, "M": 0, "D": 0}, {"A": 0, "M": 0, "D": 0}),
            ({"A": 0, "M": 1, "D": 1}, {"A": 1, "M": 0, "D": 0}),
        ],
    )
    mocker.patch("sys.argv", ["git-commit-stats"])

    main()
    captured = capsys.readouterr()
    assert "Commit" in captured.out
    assert "abc" in captured.out
    assert "def" in captured.out


def test_main_with_repo(mocker, capsys):
    mock_get_commits = mocker.patch(
        "git_tools.commit_stats.get_commits", return_value=["abc"]
    )
    mock_get_stats = mocker.patch(
        "git_tools.commit_stats.get_commit_stats",
        return_value=({"A": 1, "M": 0, "D": 0}, {"A": 0, "M": 0, "D": 0}),
    )

    mocker.patch("sys.argv", ["git-commit-stats", "/path/to/repo"])
    main()

    mock_get_commits.assert_called_with("/path/to/repo")
    mock_get_stats.assert_called_with("abc", "/path/to/repo")


def test_version_flag(mocker, capsys):
    mocker.patch("git_tools.commit_stats.version", return_value="0.1.0")
    mocker.patch("sys.argv", ["git-commit-stats", "--version"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "git-commit-stats 0.1.0" in captured.out


def test_main_entry_point_commit_stats():
    # Triggers the 'if __name__ == "__main__":' block
    with patch("sys.argv", ["git-commit-stats", "-h"]):
        with pytest.raises(SystemExit):
            runpy.run_module("git_tools.commit_stats", run_name="__main__")


def test_version_unknown(mocker, capsys):
    mocker.patch("git_tools.commit_stats.version", side_effect=Exception())
    mocker.patch("sys.argv", ["git-commit-stats", "--version"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "git-commit-stats unknown" in captured.out


def test_short_version_flag(mocker, capsys):
    mocker.patch("git_tools.commit_stats.version", return_value="0.1.0")
    mocker.patch("sys.argv", ["git-commit-stats", "-V"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "git-commit-stats 0.1.0" in captured.out
