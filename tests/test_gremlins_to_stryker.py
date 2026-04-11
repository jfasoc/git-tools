import json
import os
import runpy
from unittest.mock import MagicMock, patch
import pytest
import git_tools.gremlins_to_stryker
from git_tools.gremlins_to_stryker import get_parser, convert_to_stryker, run, main

def test_get_parser():
    parser = get_parser()
    args = parser.parse_args(["input.json", "--output", "output.json", "--repo-root", "/tmp"])
    assert args.input == "input.json"
    assert args.output == "output.json"
    assert args.repo_root == "/tmp"

def test_convert_to_stryker(tmp_path):
    file_path = tmp_path / "file.py"
    file_path.write_text("print('hello')")

    gremlins_data = {
        "results": [
            {
                "gremlin_id": "g1",
                "file_path": str(file_path),
                "line_number": 1,
                "status": "zapped",
                "operator": "boolean",
                "description": "True to False"
            },
            {
                "gremlin_id": "g2",
                "file_path": "non_existent.py",
                "line_number": 2,
                "status": "survived",
                "operator": "comparison",
                "description": "== to !="
            },
            {
                "gremlin_id": "g3",
                "file_path": "unreadable.py",
                "line_number": 3,
                "status": "timeout",
                "operator": "boolean",
                "description": "Timeout"
            },
            {
                "gremlin_id": "g4",
                "file_path": "error.py",
                "line_number": 4,
                "status": "error",
                "operator": "boolean",
                "description": "Error"
            }
        ]
    }

    # Mock open for "unreadable.py" to raise an exception
    original_open = open
    def mock_open(path, *args, **kwargs):
        if "unreadable.py" in str(path):
            raise Exception("Unreadable")
        return original_open(path, *args, **kwargs)

    # Use a real os.path.exists for the non-mocked cases
    original_exists = os.path.exists
    def mock_exists(p):
        if "unreadable.py" in str(p):
            return True
        return original_exists(p)

    with patch("builtins.open", side_effect=mock_open):
        with patch("os.path.exists", side_effect=mock_exists):
             stryker = convert_to_stryker(gremlins_data, str(tmp_path))

    assert stryker["schemaVersion"] == "1"

    rel_path = os.path.relpath(str(file_path), str(tmp_path))
    assert stryker["files"][rel_path]["source"] == "print('hello')"
    assert stryker["files"][rel_path]["mutants"][0]["status"] == "Killed"

    assert stryker["files"]["non_existent.py"]["source"] == ""
    assert stryker["files"]["non_existent.py"]["mutants"][0]["status"] == "Survived"

    assert stryker["files"]["unreadable.py"]["source"] == ""
    assert stryker["files"]["unreadable.py"]["mutants"][0]["status"] == "TimedOut"
    assert stryker["files"]["error.py"]["mutants"][0]["status"] == "RuntimeError"

def test_run_success(tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.json"
    data = {"results": [{"status": "zapped", "operator": "op", "description": "desc", "file_path": "f.py", "line_number": 1}]}
    input_file.write_text(json.dumps(data))

    args = MagicMock()
    args.input = str(input_file)
    args.output = str(output_file)
    args.repo_root = str(tmp_path)

    run(args)

    assert output_file.exists()
    stryker = json.loads(output_file.read_text())
    assert "files" in stryker

def test_run_error(capsys):
    args = MagicMock()
    args.input = "non_existent.json"

    with pytest.raises(SystemExit) as excinfo:
        run(args)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Error during conversion" in captured.err

def test_main(mocker):
    mocker.patch("git_tools.gremlins_to_stryker.run")
    mocker.patch("git_tools.gremlins_to_stryker.get_parser")
    main()
    assert git_tools.gremlins_to_stryker.run.called

def test_module_main(mocker, tmp_path):
    input_file = tmp_path / "dummy.json"
    input_file.write_text('{"results": []}')
    mocker.patch("sys.argv", ["gremlins-to-stryker", str(input_file), "--output", str(tmp_path / "out.json")])
    runpy.run_module("git_tools.gremlins_to_stryker", run_name="__main__")
