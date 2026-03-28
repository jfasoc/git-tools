import pytest
import subprocess
from unittest.mock import patch, MagicMock
import os
from git_tools.pack_stats import (
    run_git_command,
    get_git_dir,
    get_pack_files,
    get_pack_info,
    get_loose_info,
    format_size,
    main
)

def test_run_git_command_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="test output\n", returncode=0)
        output = run_git_command(["rev-parse", "HEAD"])
        assert output == "test output\n"
        mock_run.assert_called_with(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )

def test_run_git_command_with_repo():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="test output\n", returncode=0)
        output = run_git_command(["rev-parse", "HEAD"], repo_path="/tmp/repo")
        assert output == "test output\n"
        mock_run.assert_called_with(
            ["git", "-C", "/tmp/repo", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )

def test_run_git_command_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git"], stderr="error message")
        with pytest.raises(SystemExit) as excinfo:
            run_git_command(["invalid"])
        assert excinfo.value.code == 1

def test_run_git_command_with_stderr():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git"], output="some stdout", stderr="error message")
        with pytest.raises(SystemExit) as excinfo:
            run_git_command(["invalid"])
        assert excinfo.value.code == 1

def test_run_git_command_not_found():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(SystemExit) as excinfo:
            run_git_command(["git"])
        assert excinfo.value.code == 1

def test_get_git_dir_absolute():
    with patch("git_tools.pack_stats.run_git_command") as mock_git, \
         patch("os.path.isabs") as mock_isabs:

        mock_git.return_value = "/abs/path/.git\n"
        mock_isabs.return_value = True

        git_dir = get_git_dir("/some/repo")
        assert git_dir == "/abs/path/.git"

def test_get_git_dir_relative():
    with patch("git_tools.pack_stats.run_git_command") as mock_git:

        mock_git.return_value = ".git\n"

        git_dir = get_git_dir("repo")
        assert os.path.isabs(git_dir)
        assert git_dir.endswith("repo/.git")

def test_get_pack_files():
    with patch("os.path.exists") as mock_exists, \
         patch("os.listdir") as mock_listdir:

        mock_exists.return_value = True
        mock_listdir.return_value = ["pack-1.pack", "pack-1.idx", "pack-2.pack"]

        packs = get_pack_files("/abs/path/.git")
        assert packs == ["pack-1.pack", "pack-2.pack"]

def test_get_pack_files_no_pack_dir():
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = False

        packs = get_pack_files("/abs/path/.git")
        assert packs == []

def test_get_pack_info():
    with patch("git_tools.pack_stats.run_git_command") as mock_git, \
         patch("os.path.getsize") as mock_getsize:

        mock_git.return_value = "sha1 commit ...\nsha2 blob ...\nsha3 tree ...\nnon delta: 3 objects\n"
        mock_getsize.return_value = 1024

        count, size = get_pack_info("/abs/path/.git", "pack-1.pack")
        assert count == 3
        assert size == 1024

def test_get_pack_info_with_tag():
    with patch("git_tools.pack_stats.run_git_command") as mock_git, \
         patch("os.path.getsize") as mock_getsize:

        mock_git.return_value = "sha1 tag ...\nnon delta: 1 objects\n"
        mock_getsize.return_value = 100

        count, size = get_pack_info("/abs/path/.git", "pack-1.pack")
        assert count == 1

def test_get_loose_info():
    with patch("git_tools.pack_stats.run_git_command") as mock_git:
        mock_git.return_value = "count: 5\nsize: 10\nin-pack: 100\n"

        count, size = get_loose_info()
        assert count == 5
        assert size == 10 * 1024

def test_format_size():
    assert format_size(500) == "500 B"
    assert format_size(1024) == "1.00 KiB"
    assert format_size(1536) == "1.50 KiB"
    assert format_size(1024 * 1024) == "1.00 MiB"
    assert format_size(1.5 * 1024 * 1024) == "1.50 MiB"

def test_main_no_packs(capsys):
    with patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir, \
         patch("git_tools.pack_stats.get_pack_files") as mock_get_packs, \
         patch("git_tools.pack_stats.get_loose_info") as mock_get_loose, \
         patch("sys.argv", ["git-pack-stats"]):

        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = []
        mock_get_loose.return_value = (0, 0)

        main()
        captured = capsys.readouterr()
        assert "Total" in captured.out
        assert "0 B" in captured.out

def test_main_with_data(capsys):
    with patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir, \
         patch("git_tools.pack_stats.get_pack_files") as mock_get_packs, \
         patch("git_tools.pack_stats.get_pack_info") as mock_get_info, \
         patch("git_tools.pack_stats.get_loose_info") as mock_get_loose, \
         patch("sys.argv", ["git-pack-stats"]):

        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 1024)
        mock_get_loose.return_value = (10, 1024)

        main()
        captured = capsys.readouterr()
        assert "pack-1.pack" in captured.out
        assert "Loose Objects" in captured.out
        assert "50.0%" in captured.out

def test_main_sorting(capsys):
    with patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir, \
         patch("git_tools.pack_stats.get_pack_files") as mock_get_packs, \
         patch("git_tools.pack_stats.get_pack_info") as mock_get_info, \
         patch("git_tools.pack_stats.get_loose_info") as mock_get_loose, \
         patch("sys.argv", ["git-pack-stats"]):

        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["small.pack", "large.pack"]
        mock_get_info.side_effect = [(10, 100), (100, 1000)]
        mock_get_loose.return_value = (0, 0)

        main()
        captured = capsys.readouterr()
        # "large.pack" should come before "small.pack"
        assert captured.out.find("large.pack") < captured.out.find("small.pack")

def test_main_system_exit():
    with patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir, \
         patch("sys.argv", ["git-pack-stats"]):

        mock_get_git_dir.side_effect = SystemExit(1)
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1

def test_main_error(capsys):
    with patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir, \
         patch("sys.argv", ["git-pack-stats"]):

        mock_get_git_dir.side_effect = Exception("error message")
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: error message" in captured.err
