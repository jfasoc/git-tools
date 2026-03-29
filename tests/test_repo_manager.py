import os
import sys
import subprocess
import pytest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime
from git_tools.repo_manager import (
    get_config_path,
    is_git_repo,
    load_config,
    scan_directories,
    update_repos_section,
    get_parser,
    main,
)


@pytest.fixture
def mock_config_file(tmp_path):
    config_dir = tmp_path / ".config" / "git-tools"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "git-repo-manager"
    content = """
[search]
/tmp/search1
/tmp/search2

[repos]
/tmp/search1/repo1 = # 2023-01-01 12:00:00
"""
    config_file.write_text(content)
    return config_file


def test_get_config_path():
    path = get_config_path()
    assert path.endswith(".config/git-tools/git-repo-manager")


@patch("subprocess.run")
def test_is_git_repo(mock_run, tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    dotgit = repo_dir / ".git"
    dotgit.mkdir()

    # Success case
    mock_run.return_value = MagicMock(returncode=0, stdout="true")
    assert is_git_repo(str(repo_dir)) is True

    # Not a git repo (no .git)
    no_dotgit = tmp_path / "not_a_repo"
    no_dotgit.mkdir()
    assert is_git_repo(str(no_dotgit)) is False

    # Git command failure
    mock_run.return_value = MagicMock(returncode=1, stdout="false")
    assert is_git_repo(str(repo_dir)) is False

    # Git command not found
    mock_run.side_effect = FileNotFoundError
    assert is_git_repo(str(repo_dir)) is False


def test_load_config(mock_config_file):
    search_dirs, repos = load_config(str(mock_config_file))
    assert "/tmp/search1" in search_dirs
    assert "/tmp/search2" in search_dirs
    assert os.path.abspath("/tmp/search1/repo1") in repos
    assert repos[os.path.abspath("/tmp/search1/repo1")]["active"] is True


def test_load_config_missing_file():
    with pytest.raises(SystemExit):
        load_config("/non/existent/path")


def test_load_config_with_comments_and_missing_values(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("""
[search]
# comment
/search/path
[repos]
# /inactive/repo = # 2023-01-01 00:00:00
/active/repo = # 2023-01-01 01:00:00
invalid_line
=
""")
    search_dirs, repos = load_config(str(config_file))
    assert "/search/path" in search_dirs
    assert os.path.abspath("/active/repo") in repos
    assert repos[os.path.abspath("/active/repo")]["active"] is True
    assert os.path.abspath("/inactive/repo") in repos
    assert repos[os.path.abspath("/inactive/repo")]["active"] is False


@patch("builtins.open", side_effect=Exception("Read error"))
def test_load_config_exception(mock_file):
    with pytest.raises(SystemExit):
        load_config("/some/path")


@patch("git_tools.repo_manager.is_git_repo")
@patch("os.walk")
@patch("os.path.isdir")
def test_scan_directories(mock_isdir, mock_walk, mock_is_git_repo):
    mock_isdir.return_value = True
    mock_walk.return_value = [
        ("/search1", ["repo1", "dir1"], []),
        ("/search1/repo1", [], []),
        ("/search1/dir1", ["subrepo"], []),
        ("/search1/dir1/subrepo", [], []),
    ]

    def side_effect(path):
        return path in ["/search1/repo1", "/search1/dir1/subrepo"]

    mock_is_git_repo.side_effect = side_effect

    found = scan_directories(["/search1"])

    assert "/search1/repo1" in found
    assert "/search1/dir1/subrepo" in found
    assert len(found) == 2


@patch("os.path.isdir", return_value=False)
def test_scan_directories_not_found(mock_isdir):
    with patch("builtins.print") as mock_print:
        found = scan_directories(["/non/existent"])
        assert len(found) == 0
        mock_print.assert_any_call("Warning: Search directory not found: /non/existent", file=sys.stderr)


@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.get_config_path")
def test_update_repos_section(mock_get_path, mock_load, mock_config_file):
    mock_get_path.return_value = str(mock_config_file)
    mock_load.return_value = (
        ["/search1"],
        {
            os.path.abspath("/old/repo"): {"timestamp": "2023-01-01 00:00:00", "active": True},
            os.path.abspath("/existing/repo"): {"timestamp": "2023-01-01 10:00:00", "active": True},
        },
    )

    found_repos = {os.path.abspath("/existing/repo"), os.path.abspath("/new/repo")}

    update_repos_section(str(mock_config_file), found_repos)

    with open(mock_config_file, "r") as f:
        content = f.read()

    assert f"/existing/repo = # 2023-01-01 10:00:00" in content
    assert f"/new/repo = # " in content
    assert f"# /old/repo = # 2023-01-01 00:00:00" in content


def test_update_repos_section_append_new(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[search]\n/path\n")

    with patch("git_tools.repo_manager.load_config", return_value=(["/path"], {})):
        update_repos_section(str(config_file), {os.path.abspath("/new/repo")})

    content = config_file.read_text()
    assert "[repos]" in content
    assert "/new/repo =" in content


def test_update_repos_section_between_sections(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[repos]\n[other]\n")

    with patch("git_tools.repo_manager.load_config", return_value=([], {})):
        update_repos_section(str(config_file), {os.path.abspath("/repo")})

    content = config_file.read_text()
    assert "[repos]\n/repo =" in content
    assert "[other]" in content


@patch("builtins.open")
def test_update_repos_section_read_exception(mock_open_func):
    mock_open_func.side_effect = Exception("Read error")
    with pytest.raises(SystemExit):
        update_repos_section("/path", set())


@patch("builtins.open")
def test_update_repos_section_write_exception(mock_open_func):
    def side_effect(path, mode="r", encoding=None):
        if mode == "r":
            return mock_open(read_data="[repos]").return_value
        else:
            raise Exception("Write error")

    mock_open_func.side_effect = side_effect
    with patch("git_tools.repo_manager.load_config", return_value=([], {})):
        with pytest.raises(SystemExit):
            update_repos_section("/path", set())


@patch("git_tools.repo_manager.get_config_path")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.scan_directories")
@patch("git_tools.repo_manager.update_repos_section")
@patch("argparse.ArgumentParser.parse_args")
def test_main_scan(
    mock_args, mock_update, mock_scan, mock_load, mock_get_path
):
    mock_args.return_value = MagicMock(command="scan")
    mock_get_path.return_value = "/mock/config"
    mock_load.return_value = (["/search"], {})
    mock_scan.return_value = {"/repo"}

    main()

    mock_scan.assert_called_once_with(["/search"])
    mock_update.assert_called_once_with("/mock/config", {"/repo"})


@patch("git_tools.repo_manager.get_config_path")
@patch("git_tools.repo_manager.load_config")
@patch("argparse.ArgumentParser.parse_args")
def test_main_scan_no_search_dirs(mock_args, mock_load, mock_get_path):
    mock_args.return_value = MagicMock(command="scan")
    mock_get_path.return_value = "/mock/config"
    mock_load.return_value = ([], {})

    with patch("builtins.print") as mock_print:
        main()
        mock_print.assert_any_call("No search directories configured in [search] section.")


@patch("argparse.ArgumentParser.parse_args")
@patch("argparse.ArgumentParser.print_help")
def test_main_no_command(mock_help, mock_args):
    mock_args.return_value = MagicMock(command=None)
    main()
    mock_help.assert_called_once()


@patch("git_tools.repo_manager.version", side_effect=Exception)
def test_get_parser_version_exception(mock_ver):
    parser = get_parser()
    assert parser.description == "Git Repo Manager - Scan and manage Git repositories."


def test_main_entry_point():
    with patch("git_tools.repo_manager.get_parser") as mock_get_parser:
        mock_parser = mock_get_parser.return_value
        mock_parser.parse_args.return_value = MagicMock(command=None)
        with patch.object(sys, "argv", ["git-repo-manager"]):
            main()
            mock_parser.print_help.assert_called_once()

def test_load_config_multiple_sections(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("""
[other]
something = else
[search]
/search/path
[repos]
/active/repo = # 2023-01-01 01:00:00
""")
    search_dirs, repos = load_config(str(config_file))
    assert "/search/path" in search_dirs
    assert os.path.abspath("/active/repo") in repos

def test_load_config_duplicate_repos(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("""
[repos]
/repo = # 2023-01-01 01:00:00
# /repo = # 2023-01-01 00:00:00
""")
    search_dirs, repos = load_config(str(config_file))
    assert repos[os.path.abspath("/repo")]["active"] is True
    assert repos[os.path.abspath("/repo")]["timestamp"] == "2023-01-01 01:00:00"

def test_load_config_duplicate_repos_inactive_first(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("""
[repos]
# /repo = # 2023-01-01 00:00:00
/repo = # 2023-01-01 01:00:00
""")
    search_dirs, repos = load_config(str(config_file))
    assert repos[os.path.abspath("/repo")]["active"] is True
    assert repos[os.path.abspath("/repo")]["timestamp"] == "2023-01-01 01:00:00"

def test_load_config_empty_path(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[repos]\n = # 2023-01-01 00:00:00\n")
    search_dirs, repos = load_config(str(config_file))
    assert len(repos) == 0

def test_update_repos_section_no_lines(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("")
    with patch("git_tools.repo_manager.load_config", return_value=([], {})):
        update_repos_section(str(config_file), {os.path.abspath("/repo")})
    content = config_file.read_text()
    assert "[repos]\n/repo =" in content

@patch("git_tools.repo_manager.load_config")
def test_update_repos_section_repos_not_at_end(mock_load, tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[repos]\n/repo1 = # 2023-01-01 00:00:00\n[other]\n")
    mock_load.return_value = ([], {os.path.abspath("/repo1"): {"timestamp": "2023-01-01 00:00:00", "active": True}})

    update_repos_section(str(config_file), {os.path.abspath("/repo1")})

    content = config_file.read_text()
    assert "[repos]\n/repo1 = # 2023-01-01 00:00:00\n[other]" in content

@patch("git_tools.repo_manager.load_config")
def test_update_repos_section_repos_not_found_but_exists_in_file(mock_load, tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[repos]\n/repo1 = # 2023-01-01 00:00:00\n")
    mock_load.return_value = ([], {os.path.abspath("/repo1"): {"timestamp": "2023-01-01 00:00:00", "active": True}})

    update_repos_section(str(config_file), set())

    content = config_file.read_text()
    assert "# " + os.path.abspath("/repo1") + " = # 2023-01-01 00:00:00" in content

def test_update_repos_section_no_repos_tag_but_lines(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[search]\n/path\n")
    with patch("git_tools.repo_manager.load_config", return_value=(["/path"], {})):
        update_repos_section(str(config_file), {os.path.abspath("/repo")})
    content = config_file.read_text()
    assert "[search]\n/path\n\n[repos]\n" in content

def test_load_config_file_read_error(tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[search]")
    # Make the file unreadable
    os.chmod(config_file, 0o000)
    try:
        with pytest.raises(SystemExit):
            load_config(str(config_file))
    finally:
        os.chmod(config_file, 0o600)
