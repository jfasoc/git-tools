import json
import runpy
from unittest.mock import MagicMock
import pytest
import git_tools.gremlins_to_sarif
from git_tools.gremlins_to_sarif import get_parser, convert_to_sarif, run, main

def test_get_parser():
    parser = get_parser()
    args = parser.parse_args(["input.json", "--output", "output.sarif", "--repo-root", "/tmp"])
    assert args.input == "input.json"
    assert args.output == "output.sarif"
    assert args.repo_root == "/tmp"

def test_convert_to_sarif():
    gremlins_data = {
        "results": [
            {
                "gremlin_id": "g1",
                "file_path": "/app/src/file.py",
                "line_number": 10,
                "status": "survived",
                "operator": "boolean",
                "description": "True to False"
            },
            {
                "gremlin_id": "g2",
                "file_path": "/app/src/file.py",
                "line_number": 20,
                "status": "zapped",
                "operator": "comparison",
                "description": "== to !="
            },
            {
                "gremlin_id": "g3",
                "file_path": "relative/file.py",
                "line_number": 30,
                "status": "survived",
                "operator": "boolean",
                "description": "Relative path"
            }
        ]
    }
    repo_root = "/app"
    sarif = convert_to_sarif(gremlins_data, repo_root)

    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    run_data = sarif["runs"][0]
    assert run_data["tool"]["driver"]["name"] == "pytest-gremlins"
    assert len(run_data["results"]) == 2

    result = run_data["results"][0]
    assert result["ruleId"] == "gremlin-boolean"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/file.py"
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 10

    result2 = run_data["results"][1]
    assert result2["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "relative/file.py"

def test_run_success(tmp_path):
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.sarif"
    data = {"results": [{"status": "survived", "operator": "op", "description": "desc", "file_path": "f.py", "line_number": 1}]}
    input_file.write_text(json.dumps(data))

    args = MagicMock()
    args.input = str(input_file)
    args.output = str(output_file)
    args.repo_root = str(tmp_path)

    run(args)

    assert output_file.exists()
    sarif = json.loads(output_file.read_text())
    assert len(sarif["runs"][0]["results"]) == 1

def test_run_error(capsys):
    args = MagicMock()
    args.input = "non_existent.json"

    with pytest.raises(SystemExit) as excinfo:
        run(args)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Error during conversion" in captured.err

def test_main(mocker):
    mocker.patch("git_tools.gremlins_to_sarif.run")
    mocker.patch("git_tools.gremlins_to_sarif.get_parser")
    main()
    assert git_tools.gremlins_to_sarif.run.called

def test_module_main(mocker, tmp_path):
    # This time we don't mock run(), we let it execute but with a real file
    input_file = tmp_path / "dummy.json"
    input_file.write_text('{"results": []}')
    mocker.patch("sys.argv", ["gremlins-to-sarif", str(input_file), "--output", str(tmp_path / "out.sarif")])
    runpy.run_module("git_tools.gremlins_to_sarif", run_name="__main__")
