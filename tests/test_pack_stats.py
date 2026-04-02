import pytest
import subprocess
import runpy
from unittest.mock import patch, MagicMock
import os
from git_tools.pack_stats import (
    run_git_command,
    get_git_dir,
    get_pack_files,
    get_pack_info,
    get_loose_info,
    format_size,
    main,
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
            check=True,
            input=None,
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
            check=True,
            input=None,
        )


def test_run_git_command_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git"], stderr="error message"
        )
        with pytest.raises(SystemExit) as excinfo:
            run_git_command(["invalid"])
        assert excinfo.value.code == 1


def test_run_git_command_with_stderr():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git"], output="some stdout", stderr="error message"
        )
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
    with (
        patch("git_tools.pack_stats.run_git_command") as mock_git,
        patch("os.path.isabs") as mock_isabs,
    ):
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
    with patch("os.path.exists") as mock_exists, patch("os.listdir") as mock_listdir:
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
    with (
        patch("git_tools.pack_stats.run_git_command") as mock_git,
        patch("os.path.getsize") as mock_getsize,
    ):
        # 1st line: 4 columns (base)
        # 2nd line: 4 columns (base)
        # 3rd line: 7 columns (delta)
        mock_git.return_value = (
            "sha1 commit 100 100 0\n"
            "sha2 blob 200 100 100\n"
            "sha3 tree 300 50 300 1 base-sha\n"
        )
        mock_getsize.return_value = 1024

        count, deltas, size, uncompressed, actual = get_pack_info(
            "/abs/path/.git", "pack-1.pack"
        )
        assert count == 3
        assert deltas == 1
        assert size == 1024
        assert uncompressed == 600
        assert actual is None


def test_get_pack_info_include_actual():
    with (
        patch("git_tools.pack_stats.run_git_command") as mock_git,
        patch("os.path.getsize") as mock_getsize,
    ):
        # mock_git is called twice: once for verify-pack, once for cat-file
        mock_git.side_effect = [
            "sha1 commit 100 100 0\nsha2 blob 200 50 100 1 base-sha\n",
            "500\n600\n",
        ]
        mock_getsize.return_value = 1024

        count, deltas, size, uncompressed, actual = get_pack_info(
            "/abs/path/.git", "pack-1.pack", include_actual=True
        )
        assert count == 2
        assert deltas == 1
        assert uncompressed == 300
        assert actual == 1100

    # Test include_actual with empty pack
    with (
        patch("git_tools.pack_stats.run_git_command") as mock_git,
        patch("os.path.getsize") as mock_getsize,
    ):
        mock_git.return_value = ""
        mock_getsize.return_value = 0
        count, deltas, size, uncompressed, actual = get_pack_info(
            "/abs/path/.git", "empty.pack", include_actual=True
        )
        assert count == 0
        assert actual == 0

    # Test include_actual with objects but empty cat-file output
    with (
        patch("git_tools.pack_stats.run_git_command") as mock_git,
        patch("os.path.getsize") as mock_getsize,
    ):
        mock_git.side_effect = ["sha1 commit 100 100 0\n", ""]
        mock_getsize.return_value = 100
        count, deltas, size, uncompressed, actual = get_pack_info(
            "/abs/path/.git", "pack-1.pack", include_actual=True
        )
        assert count == 1
        assert actual == 0


def test_get_pack_info_with_tag():
    with (
        patch("git_tools.pack_stats.run_git_command") as mock_git,
        patch("os.path.getsize") as mock_getsize,
    ):
        mock_git.return_value = "sha1 tag 50 50 0\n"
        mock_getsize.return_value = 100

        count, deltas, size, uncompressed, actual = get_pack_info(
            "/abs/path/.git", "pack-1.pack"
        )
        assert count == 1
        assert uncompressed == 50


def test_get_pack_info_parsing_error():
    with (
        patch("git_tools.pack_stats.run_git_command") as mock_git,
        patch("os.path.getsize") as mock_getsize,
    ):
        # Third column is not an integer
        mock_git.return_value = "sha1 commit not_a_number 100 0\n"
        mock_getsize.return_value = 100

        count, deltas, size, uncompressed, actual = get_pack_info(
            "/abs/path/.git", "pack-1.pack"
        )
        assert count == 1
        assert uncompressed == 0


def test_get_loose_info_empty():
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
    ):
        mock_get_git_dir.return_value = ".git"
        mock_exists.return_value = True
        mock_listdir.return_value = []
        count, deltas, compressed, uncompressed = get_loose_info()
        assert count == 0
        assert deltas == 0
        assert compressed == 0
        assert uncompressed is None


def test_get_loose_info_with_data():
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
        patch("os.path.getsize") as mock_getsize,
        patch("subprocess.run") as mock_run,
    ):
        mock_get_git_dir.return_value = ".git"
        mock_exists.return_value = True
        mock_listdir.side_effect = [
            ["ab", "cd", "info", "pack"],  # Inside .git/objects (call 1)
            ["1234"],  # Inside .git/objects/ab (call 1)
            ["5678"],  # Inside .git/objects/cd (call 1)
            ["ab", "cd", "info", "pack"],  # Inside .git/objects (call 2)
            ["1234"],  # Inside .git/objects/ab (call 2)
            ["5678"],  # Inside .git/objects/cd (call 2)
        ]
        mock_getsize.side_effect = [100, 200, 100, 200]
        mock_run.return_value = MagicMock(stdout="1000\n2000\n", returncode=0)

        count, deltas, compressed, uncompressed = get_loose_info(
            include_uncompressed=True
        )
        assert count == 2
        assert deltas == 0
        assert compressed == 300
        assert uncompressed == 3000
        mock_run.assert_called()

        # Test with repo_path to cover line 96
        get_loose_info(repo_path="/some/repo", include_uncompressed=True)
        args, kwargs = mock_run.call_args
        assert "-C" in args[0]
        assert "/some/repo" in args[0]
        assert kwargs["input"] == "ab1234\ncd5678"


def test_get_loose_info_exception():
    with patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir:
        mock_get_git_dir.side_effect = Exception()
        count, deltas, compressed, uncompressed = get_loose_info(
            include_uncompressed=True
        )
        assert count == 0
        assert deltas == 0
        assert compressed == 0
        assert uncompressed == 0


def test_get_loose_info_no_obj_dir():
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("os.path.exists") as mock_exists,
    ):
        mock_get_git_dir.return_value = ".git"
        mock_exists.return_value = False
        count, deltas, compressed, uncompressed = get_loose_info(
            include_uncompressed=True
        )
        assert count == 0
        assert deltas == 0
        assert uncompressed == 0


def test_format_size():
    # Default (human=False)
    assert format_size(500) == "500"
    assert format_size(1024) == "1.024"
    assert format_size(1000000) == "1.000.000"

    # human=True
    assert format_size(500, human=True) == "500 B"
    assert format_size(1024, human=True) == "1.00 KiB"
    assert format_size(1536, human=True) == "1.50 KiB"
    assert format_size(1024 * 1024, human=True) == "1.00 MiB"
    assert format_size(1.5 * 1024 * 1024, human=True) == "1.50 MiB"


def test_main_no_packs(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = []
        mock_get_loose.return_value = (0, 0, 0, None)

        main()
        captured = capsys.readouterr()
        assert "Total" in captured.out
        assert "0" in captured.out


def test_main_with_data(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 5, 512, 1024, None)
        mock_get_loose.return_value = (10, 0, 512, None)

        main()
        captured = capsys.readouterr()
        assert "pack-1.pack" in captured.out
        assert "Loose Objects" in captured.out
        assert "50.0%" in captured.out
        assert "50.0%" in captured.out


def test_main_with_loose_uncompressed(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats", "--loose-uncompressed"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 5, 512, 1024, None)
        mock_get_loose.return_value = (10, 0, 512, 1024)

        main()
        captured = capsys.readouterr()
        assert "1.024" in captured.out

    # Test actual size with both pack and loose
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats", "--actual-size", "--loose-uncompressed"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 5, 512, 1024, 2048)
        mock_get_loose.return_value = (10, 0, 512, 1024)

        main()
        captured = capsys.readouterr()
        assert "3.072" in captured.out

    # Test actual size with both pack and loose, but pack actual is 0 (coverage)
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats", "--actual-size", "--loose-uncompressed"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 5, 512, 1024, None)
        mock_get_loose.return_value = (10, 0, 512, 1024)

        main()
        captured = capsys.readouterr()
        assert "1.024" in captured.out


def test_main_with_actual_size(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats", "--actual-size"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 5, 512, 1024, 2048)
        mock_get_loose.return_value = (10, 0, 512, None)

        main()
        captured = capsys.readouterr()
        assert "2.048" in captured.out

    # Test actual size with loose objects uncompressed
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats", "--actual-size", "--loose-uncompressed"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = []
        mock_get_loose.return_value = (10, 0, 512, 1024)

        main()
        captured = capsys.readouterr()
        assert "1.024" in captured.out


def test_main_human_readable(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats", "-H"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 5, 1024, 2048, None)
        mock_get_loose.return_value = (10, 0, 1024, 2048)

        main()
        captured = capsys.readouterr()
        assert "1.00 KiB" in captured.out
        assert "2.00 KiB" in captured.out


def test_main_sorting(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["small.pack", "large.pack"]
        mock_get_info.side_effect = [(10, 5, 100, 200, None), (100, 50, 1000, 2000, None)]
        mock_get_loose.return_value = (0, 0, 0, None)

        main()
        captured = capsys.readouterr()
        # "large.pack" should come before "small.pack"
        assert captured.out.find("large.pack") < captured.out.find("small.pack")


def test_main_verbose(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("git_tools.pack_stats.get_pack_files") as mock_get_packs,
        patch("git_tools.pack_stats.get_pack_info") as mock_get_info,
        patch("git_tools.pack_stats.get_loose_info") as mock_get_loose,
        patch("sys.argv", ["git-pack-stats", "--verbose"]),
    ):
        mock_get_git_dir.return_value = ".git"
        mock_get_packs.return_value = ["pack-1.pack"]
        mock_get_info.return_value = (10, 5, 512, 1024, None)
        mock_get_loose.return_value = (10, 0, 512, 1024)

        main()
        captured = capsys.readouterr()
        assert "ms get info for git repository" in captured.out
        assert "ms get info for pack-1.pack" in captured.out
        assert "ms get info for loose objects" in captured.out
        assert "ms total time" in captured.out


def test_main_system_exit():
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("sys.argv", ["git-pack-stats"]),
    ):
        mock_get_git_dir.side_effect = SystemExit(1)
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_main_error(capsys):
    with (
        patch("git_tools.pack_stats.get_git_dir") as mock_get_git_dir,
        patch("sys.argv", ["git-pack-stats"]),
    ):
        mock_get_git_dir.side_effect = Exception("error message")
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: error message" in captured.err


def test_version_flag(capsys):
    with (
        patch("git_tools.pack_stats.version", return_value="0.1.0"),
        patch("sys.argv", ["git-pack-stats", "--version"]),
    ):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "git-pack-stats 0.1.0" in captured.out


def test_main_entry_point_pack_stats():
    # Triggers the 'if __name__ == "__main__":' block
    with patch("sys.argv", ["git-pack-stats", "-h"]):
        with pytest.raises(SystemExit):
            runpy.run_module("git_tools.pack_stats", run_name="__main__")


def test_version_unknown(capsys):
    with (
        patch("git_tools.pack_stats.version", side_effect=Exception()),
        patch("sys.argv", ["git-pack-stats", "--version"]),
    ):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "git-pack-stats unknown" in captured.out


def test_short_version_flag(capsys):
    with (
        patch("git_tools.pack_stats.version", return_value="0.1.0"),
        patch("sys.argv", ["git-pack-stats", "-V"]),
    ):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert "git-pack-stats 0.1.0" in captured.out
