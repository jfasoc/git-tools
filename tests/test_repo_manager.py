import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open
from git_tools.repo_manager import (
    get_config_path,
    is_git_repo,
    load_config,
    scan_directories,
    update_repos_section,
    get_parser,
    get_repo_status,
    truncate_string,
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

    newly_added, no_longer_present = update_repos_section(str(mock_config_file), found_repos)

    with open(mock_config_file, "r") as f:
        content = f.read()

    assert "/existing/repo = # 2023-01-01 10:00:00" in content
    assert "/new/repo = # " in content
    assert "# /old/repo = # 2023-01-01 00:00:00" in content

    assert newly_added == [os.path.abspath("/new/repo")]
    assert no_longer_present == [os.path.abspath("/old/repo")]


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
    mock_args.return_value = MagicMock(command="scan", config="/mock/config")
    mock_get_path.return_value = "/mock/config"
    mock_load.return_value = (["/search"], {})
    mock_scan.return_value = {"/repo"}
    mock_update.return_value = (["/repo"], ["/old_repo"])

    with patch("builtins.print") as mock_print:
        main()
        mock_print.assert_any_call("\nNew repositories found:")
        mock_print.assert_any_call("  + /repo")
        mock_print.assert_any_call("\nRepositories no longer present (now commented out):")
        mock_print.assert_any_call("  - /old_repo")

    mock_scan.assert_called_once_with(["/search"])
    mock_update.assert_called_once_with("/mock/config", {"/repo"})


@patch("git_tools.repo_manager.get_config_path")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.scan_directories")
@patch("git_tools.repo_manager.update_repos_section")
@patch("argparse.ArgumentParser.parse_args")
def test_main_scan_no_changes(
    mock_args, mock_update, mock_scan, mock_load, mock_get_path
):
    mock_args.return_value = MagicMock(command="scan", config="/mock/config")
    mock_get_path.return_value = "/mock/config"
    mock_load.return_value = (["/search"], {})
    mock_scan.return_value = {"/repo"}
    mock_update.return_value = ([], [])

    with patch("builtins.print") as mock_print:
        main()
        # Verify that "New repositories found:" and "Repositories no longer present" were NOT called
        for call in mock_print.call_args_list:
            assert "\nNew repositories found:" not in call.args
            assert "\nRepositories no longer present" not in call.args

    mock_scan.assert_called_once_with(["/search"])


@patch("git_tools.repo_manager.get_config_path")
@patch("git_tools.repo_manager.load_config")
@patch("argparse.ArgumentParser.parse_args")
def test_main_scan_no_search_dirs(mock_args, mock_load, mock_get_path):
    mock_args.return_value = MagicMock(command="scan", config="/mock/config")
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


def test_truncate_string():
    assert truncate_string("short", 10) == "short"
    assert truncate_string("exactly ten", 11) == "exactly ten"
    assert truncate_string("this is a long string", 10) == "this is..."
    assert truncate_string("another long string", 10) == "another..."


def test_get_repo_status_path_not_found(tmp_path):
    res = get_repo_status(str(tmp_path / "nonexistent"))
    assert res == {"error": "Path not found"}


def test_get_repo_status_not_a_repo(tmp_path):
    res = get_repo_status(str(tmp_path))
    assert res == {"error": "Not a Git repository"}


@patch("git_tools.repo_manager.run_git_command")
@patch("git_tools.repo_manager.is_git_repo", return_value=True)
@patch("os.path.isdir", return_value=True)
def test_get_repo_status_success(mock_isdir, mock_is_git, mock_run):
    def side_effect(args, repo_path=None):
        if args[0] == "rev-parse" and "--abbrev-ref" in args and "HEAD" in args:
            return "main"
        if args[0] == "rev-parse" and "@{u}" in args[-1]:
            return "origin/main"
        if args[0] == "rev-list":
            if "@{u}..HEAD" in args[-1]:
                return "1"
            if "HEAD..@{u}" in args[-1]:
                return "0"
        if args[0] == "status":
            return " M file1\n?? file2"
        return None

    mock_run.side_effect = side_effect
    res = get_repo_status("/mock/repo")
    assert res == {
        "branch": "main",
        "remote_status": "Ahead 1",
        "modified": 1,
        "untracked": 1,
        "error": None,
    }


@patch("git_tools.repo_manager.run_git_command")
@patch("git_tools.repo_manager.is_git_repo", return_value=True)
@patch("os.path.isdir", return_value=True)
def test_get_repo_status_fetch(mock_isdir, mock_is_git, mock_run):
    def side_effect(args, repo_path=None):
        if args[0] == "rev-parse" and "--abbrev-ref" in args and "HEAD" in args:
            return "main"
        return None

    mock_run.side_effect = side_effect
    get_repo_status("/mock/repo", fetch_remote="upstream")
    mock_run.assert_any_call(["fetch", "upstream"], "/mock/repo")


@patch("git_tools.repo_manager.get_config_path")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.get_repo_status")
@patch("argparse.ArgumentParser.parse_args")
def test_main_status(mock_args, mock_status, mock_load, mock_get_path):
    mock_args.return_value = MagicMock(command="status", fetch=None, jobs=1, config="/mock/config")
    mock_get_path.return_value = "/mock/config"
    mock_load.return_value = (
        ["/search", "/other_search"],
        {
            os.path.abspath("/search/repo"): {"timestamp": "...", "active": True},
            os.path.abspath("/outside/repo"): {"timestamp": "...", "active": True},
            os.path.abspath("/search/error_repo"): {"timestamp": "...", "active": True},
        },
    )

    def status_side_effect(path, fetch):
        if "error_repo" in path:
            return {"error": "Some error"}
        return {
            "branch": "main",
            "remote_status": "Up-to-date",
            "modified": 0,
            "untracked": 0,
            "error": None,
        }

    mock_status.side_effect = status_side_effect

    with patch("builtins.print") as mock_print:
        main()
        mock_print.assert_any_call("\n[" + os.path.abspath("/search") + "]")
        mock_print.assert_any_call("\n[Other]")
        # Check if table header or data was printed (partial match)
        calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        assert any("Remote Status" in c for c in calls)
        assert any("repo" in c and "main" in c and "Up-to-date" in c for c in calls)
        assert any("error_repo" in c and "ERROR: Some error" in c for c in calls)


@patch("git_tools.repo_manager.get_config_path")
@patch("git_tools.repo_manager.load_config")
@patch("argparse.ArgumentParser.parse_args")
def test_main_status_no_active(mock_args, mock_load, mock_get_path):
    mock_args.return_value = MagicMock(command="status", config="/mock/config")
    mock_get_path.return_value = "/mock/config"
    mock_load.return_value = (["/search"], {"/repo": {"active": False}})

    with patch("builtins.print") as mock_print:
        main()
        mock_print.assert_any_call("No active repositories found in configuration.")


@patch("builtins.open")
def test_load_config_iteration_exception(mock_open_func, tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[search]\n/path")

    # Mock context manager to return an iterator that raises
    mock_f = MagicMock()
    mock_f.__enter__.return_value = iter(["[search]\n", Exception("Iteration error")])
    mock_open_func.return_value = mock_f

    with patch("os.path.exists", return_value=True):
        with pytest.raises(SystemExit):
            load_config(str(config_file))


@patch("git_tools.repo_manager.run_git_command")
@patch("git_tools.repo_manager.is_git_repo", return_value=True)
@patch("os.path.isdir", return_value=True)
def test_get_repo_status_remote_status_variants(mock_isdir, mock_is_git, mock_run):
    # Test Behind
    def side_effect_behind(args, repo_path=None):
        if args[0] == "rev-parse" and "--abbrev-ref" in args and "HEAD" in args:
            return "main"
        if args[0] == "rev-parse" and "@{u}" in args[-1]:
            return "origin/main"
        if args[0] == "rev-list":
            if "@{u}..HEAD" in args[-1]:
                return "0"
            if "HEAD..@{u}" in args[-1]:
                return "1"
        if args[0] == "status":
            return ""
        return None

    mock_run.side_effect = side_effect_behind
    res = get_repo_status("/mock/repo")
    assert res["remote_status"] == "Behind 1"

    # Test Ahead and Behind
    def side_effect_both(args, repo_path=None):
        if args[0] == "rev-parse" and "--abbrev-ref" in args and "HEAD" in args:
            return "main"
        if args[0] == "rev-parse" and "@{u}" in args[-1]:
            return "origin/main"
        if args[0] == "rev-list":
            if "@{u}..HEAD" in args[-1]:
                return "1"
            if "HEAD..@{u}" in args[-1]:
                return "1"
        if args[0] == "status":
            return ""
        return None

    mock_run.side_effect = side_effect_both
    res = get_repo_status("/mock/repo")
    assert res["remote_status"] == "Ahead 1, Behind 1"

    # Test Up-to-date
    def side_effect_uptodate(args, repo_path=None):
        if args[0] == "rev-parse" and "--abbrev-ref" in args and "HEAD" in args:
            return "main"
        if args[0] == "rev-parse" and "@{u}" in args[-1]:
            return "origin/main"
        if args[0] == "rev-list":
            return "0"
        if args[0] == "status":
            return ""
        return None

    mock_run.side_effect = side_effect_uptodate
    res = get_repo_status("/mock/repo")
    assert res["remote_status"] == "Up-to-date"

    # Test No upstream
    def side_effect_no_upstream(args, repo_path=None):
        if args[0] == "rev-parse" and "--abbrev-ref" in args and "HEAD" in args:
            return "main"
        if args[0] == "status":
            return ""
        return None

    mock_run.side_effect = side_effect_no_upstream
    res = get_repo_status("/mock/repo")
    assert res["remote_status"] == "N/A"


@patch("git_tools.repo_manager.run_git_command")
@patch("git_tools.repo_manager.is_git_repo", return_value=True)
@patch("os.path.isdir", return_value=True)
def test_get_repo_status_errors(mock_isdir, mock_is_git, mock_run):
    # Branch error
    mock_run.return_value = None
    res = get_repo_status("/mock/repo")
    assert res == {"error": "Could not determine branch"}

    # Status error
    def side_effect_status_error(args, repo_path=None):
        if args[0] == "rev-parse" and "--abbrev-ref" in args and "HEAD" in args:
            return "main"
        return None

    mock_run.side_effect = side_effect_status_error
    res = get_repo_status("/mock/repo")
    assert res == {"error": "Could not get status"}


@patch("git_tools.repo_manager.get_repo_status")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.get_config_path")
@patch("argparse.ArgumentParser.parse_args")
def test_main_status_exception(mock_args, mock_path, mock_load, mock_status):
    mock_args.return_value = MagicMock(command="status", fetch=None, jobs=1, config="/mock/config")
    mock_load.return_value = (["/search"], {os.path.abspath("/search/repo"): {"active": True}})
    mock_status.side_effect = Exception("Status fail")

    with patch("builtins.print") as mock_print:
        main()
        calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        assert any("ERROR: Status fail" in c for c in calls)


@patch("git_tools.repo_manager.get_repo_status")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.get_config_path")
@patch("argparse.ArgumentParser.parse_args")
def test_main_status_jobs_optional(mock_args, mock_path, mock_load, mock_status):
    # Test status -j without value
    mock_args.return_value = MagicMock(command="status", fetch=None, jobs=None, config="/mock/config")
    mock_load.return_value = (["/search"], {os.path.abspath("/search/repo"): {"active": True}})
    mock_status.return_value = {
        "branch": "main",
        "remote_status": "Up-to-date",
        "modified": 0,
        "untracked": 0,
        "error": None,
    }

    with patch("builtins.print") as mock_print:
        main()
        mock_print.assert_any_call("\n[" + os.path.abspath("/search") + "]")


@patch("git_tools.repo_manager.get_repo_status")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.get_config_path")
@patch("argparse.ArgumentParser.parse_args")
def test_main_status_grouping_edge_cases(mock_args, mock_path, mock_load, mock_status):
    # Test repo path that doesn't match any search dir
    mock_args.return_value = MagicMock(command="status", fetch=None, jobs=1, config="/mock/config")
    mock_load.return_value = (["/search"], {os.path.abspath("/outside/repo"): {"active": True}})
    mock_status.return_value = {
        "branch": "main",
        "remote_status": "Up-to-date",
        "modified": 0,
        "untracked": 0,
        "error": None,
    }

    with patch("builtins.print") as mock_print:
        main()
        mock_print.assert_any_call("\n[Other]")


@patch("git_tools.repo_manager.get_repo_status")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.get_config_path")
@patch("argparse.ArgumentParser.parse_args")
def test_main_status_other_error(mock_args, mock_path, mock_load, mock_status):
    # Test error in "Other" section
    mock_args.return_value = MagicMock(command="status", fetch=None, jobs=1, config="/mock/config")
    mock_load.return_value = (["/search"], {os.path.abspath("/outside/repo"): {"active": True}})
    mock_status.return_value = {"error": "Some error"}

    with patch("builtins.print") as mock_print:
        main()
        calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        assert any("ERROR: Some error" in c for c in calls)


@patch("git_tools.repo_manager.get_repo_status")
@patch("git_tools.repo_manager.load_config")
@patch("git_tools.repo_manager.get_config_path")
@patch("argparse.ArgumentParser.parse_args")
def test_main_status_truncation(mock_args, mock_path, mock_load, mock_status):
    # Test that long paths and branches are truncated
    long_path = "/search/" + "a" * 50
    mock_args.return_value = MagicMock(command="status", fetch=None, jobs=1, config="/mock/config")
    mock_load.return_value = (["/search"], {os.path.abspath(long_path): {"active": True}})
    mock_status.return_value = {
        "branch": "a_very_long_branch_name_that_should_be_truncated",
        "remote_status": "Ahead 100, Behind 100",
        "modified": 0,
        "untracked": 0,
        "error": None,
    }

    with patch("builtins.print") as mock_print:
        main()
        # calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        # Check for truncated path (length 40)
        # assert any("a" * 37 + "..." in c for c in calls)
        # Check for truncated branch (length 20)
        # assert any("a_very_long_branch_..." in c for c in calls)
        # Check for truncated remote status (length 20)
        # assert any("Ahead 100, Behind 1..." in c for c in calls)

        # Print the actual calls for debugging
        # for c in calls:
        #     print(f"DEBUG: {c}")

        found_path = False
        found_branch = False
        found_remote = False
        for call in mock_print.call_args_list:
            if not call.args:
                continue
            arg = call.args[0]
            if "a" * 37 + "..." in arg:
                found_path = True
            if "a_very_long_branc..." in arg:
                found_branch = True
            if "Ahead 100, Behind..." in arg:
                found_remote = True

        assert found_path
        assert found_branch
        assert found_remote
