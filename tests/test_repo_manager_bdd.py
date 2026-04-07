import os
import subprocess
import shutil
import pytest
import sys
from pytest_bdd import scenario, given, when, then, parsers
from datetime import datetime

@pytest.fixture
def test_dir(tmp_path):
    """Temporary directory for all test assets."""
    d = tmp_path / "test-env"
    d.mkdir()
    return d

@pytest.fixture
def config_file(test_dir):
    """Path to the temporary configuration file."""
    return test_dir / "git-repo-manager"

@scenario("features/repo_manager.feature", "Scanning for repositories")
def test_scanning():
    pass

@scenario("features/repo_manager.feature", "Displaying repository status")
def test_status():
    pass

@scenario("features/repo_manager.feature", "Detecting modified and untracked files")
def test_status_counts():
    pass

@scenario("features/repo_manager.feature", "Handling bare repositories")
def test_status_bare():
    pass

@scenario("features/repo_manager.feature", "Marking missing repositories as inactive")
def test_scan_inactive():
    pass

@scenario("features/repo_manager.feature", "Using storage option")
def test_storage():
    pass

@scenario("features/repo_manager.feature", "Fetching from remote")
def test_fetch():
    pass

@given(parsers.parse('a search directory "{search_dir}"'), target_fixture="actual_search_dir")
def create_search_dir(test_dir, search_dir):
    actual_path = test_dir / os.path.basename(search_dir)
    actual_path.mkdir(exist_ok=True)
    return actual_path

@given(parsers.parse('a Git repository at "{repo_path}"'))
@given(parsers.parse('a Git repository at "{repo_path}" on branch "{branch}"'))
def create_repo(test_dir, repo_path, branch="main"):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    parent_path = test_dir / parent_name
    actual_repo_path = parent_path / name
    actual_repo_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init", "-b", branch], cwd=actual_repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=actual_repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=actual_repo_path, check=True)
    (actual_repo_path / "initial").write_text("initial")
    subprocess.run(["git", "add", "initial"], cwd=actual_repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=actual_repo_path, check=True)
    return actual_repo_path

@given(parsers.parse('a bare Git repository at "{repo_path}"'))
def create_bare_repo(test_dir, repo_path):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    parent_path = test_dir / parent_name
    actual_repo_path = parent_path / name
    actual_repo_path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init", "--bare"], cwd=actual_repo_path, check=True)
    return actual_repo_path

@given(parsers.parse('a configuration file with search directory "{search_dir}"'))
def create_config_search(test_dir, config_file, search_dir):
    actual_search_dir = test_dir / os.path.basename(search_dir)
    content = f"[search]\n{actual_search_dir}\n"
    config_file.write_text(content)

@given(parsers.parse('a configuration file with repositories "{repos_str}" in "{search_dir}"'))
def create_config_full(test_dir, config_file, repos_str, search_dir):
    search_path = test_dir / os.path.basename(search_dir)
    repo_names = [r.strip() for r in repos_str.split(",")]

    content = f"[search]\n{search_path}\n\n[repos]\n"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name in sorted(repo_names):
        repo_path = os.path.abspath(search_path / name)
        content += f"{repo_path} = # {now}\n"
    config_file.write_text(content)

@given(parsers.parse('the repository "{repo_path}" has {count:d} modified files'))
def add_modified_files(test_dir, repo_path, count):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    actual_repo_path = test_dir / parent_name / name
    for i in range(count):
        f = actual_repo_path / f"mod_{i}"
        f.write_text("content")
        subprocess.run(["git", "add", str(f)], cwd=actual_repo_path, check=True)
        f.write_text("modified content")

@given(parsers.parse('the repository "{repo_path}" has {count:d} untracked files'))
def add_untracked_files(test_dir, repo_path, count):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    actual_repo_path = test_dir / parent_name / name
    for i in range(count):
        f = actual_repo_path / f"unt_{i}"
        f.write_text("untracked")

@given(parsers.parse('the repository "{repo_path}" does not exist'))
def delete_repo(test_dir, repo_path):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    actual_repo_path = test_dir / parent_name / name
    if actual_repo_path.exists():
        shutil.rmtree(actual_repo_path)

@given(parsers.parse('the repository "{repo_path}" has a remote "{remote_name}"'))
def add_remote(test_dir, repo_path, remote_name):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    actual_repo_path = test_dir / parent_name / name

    remote_path = test_dir / f"{name}_remote"
    remote_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare"], cwd=remote_path, check=True)
    subprocess.run(["git", "remote", "add", remote_name, str(remote_path)], cwd=actual_repo_path, check=True)
    # Push initial commit
    subprocess.run(["git", "push", remote_name, "HEAD"], cwd=actual_repo_path, check=True)
    # Set upstream
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=actual_repo_path, capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "branch", "--set-upstream-to", f"{remote_name}/{branch}"], cwd=actual_repo_path, check=True)

@when(parsers.parse('I run "git-repo-manager {command}"'), target_fixture="run_output")
def run_command(config_file, command):
    cmd_parts = command.split()
    # Ensure the command uses the provided config file
    if "-c" not in cmd_parts and "--config" not in cmd_parts:
        cmd_parts = ["-c", str(config_file)] + cmd_parts

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    full_cmd = [sys.executable, "-m", "git_tools.repo_manager"] + cmd_parts
    result = subprocess.run(full_cmd, capture_output=True, text=True, env=env)
    return result.stdout

@then(parsers.parse('the configuration should contain "{repo_path}"'))
def verify_config_contains(test_dir, config_file, repo_path):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    actual_repo_path = os.path.abspath(test_dir / parent_name / name)
    content = config_file.read_text()
    assert actual_repo_path in content

@then(parsers.parse('the output should indicate {count:d} active repository was found'))
@then(parsers.parse('the output should indicate {count:d} active repositories were found'))
def verify_output_count(run_output, count):
    assert f"Found {count} active repositories." in run_output

@then(parsers.parse('the output should contain a table with "{repo_name}" on branch "{branch}"'))
def verify_table_output(run_output, repo_name, branch):
    assert repo_name in run_output
    assert branch in run_output

@then(parsers.parse('the output should show "{repo_name}" in the status table'))
def verify_repo_in_table(run_output, repo_name):
    assert repo_name in run_output

@then(parsers.parse('the output should show {mod:d} modified and {unt:d} untracked files for "{repo_name}"'))
def verify_status_counts(run_output, mod, unt, repo_name):
    for line in run_output.splitlines():
        if repo_name in line:
            assert str(mod) in line
            assert str(unt) in line
            return
    assert False, f"Could not find {repo_name} in output:\n{run_output}"

@then(parsers.parse('the output should show "{branch}" branch for "{repo_name}"'))
def verify_branch(run_output, branch, repo_name):
    for line in run_output.splitlines():
        if repo_name in line:
            assert branch in line
            return
    assert False, f"Could not find {repo_name} in output:\n{run_output}"

@then(parsers.parse('the modified and untracked counts for "{repo_name}" should be "{val}"'))
def verify_na_counts(run_output, repo_name, val):
    for line in run_output.splitlines():
        if repo_name in line:
            assert val in line
            return
    assert False, f"Could not find {repo_name} in output:\n{run_output}"

@then(parsers.parse('the configuration should show "{repo_path}" as inactive'))
def verify_inactive(test_dir, config_file, repo_path):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    actual_repo_path = os.path.abspath(test_dir / parent_name / name)
    content = config_file.read_text()
    assert f"# {actual_repo_path}" in content

@then(parsers.parse('the output should indicate "{repo_path}" is no longer present'))
def verify_output_missing(test_dir, run_output, repo_path):
    name = os.path.basename(repo_path)
    parent_name = os.path.basename(os.path.dirname(repo_path))
    actual_repo_path = os.path.abspath(test_dir / parent_name / name)
    assert f"- {actual_repo_path}" in run_output

@then(parsers.parse('the output should contain "Packs" and "Loose" columns'))
def verify_storage_columns(run_output):
    assert "Packs" in run_output
    assert "Loose" in run_output

@then(parsers.parse('the output should show "{status}" or "{alt_status}" for "{repo_name}"'))
def verify_remote_status(run_output, status, alt_status, repo_name):
    for line in run_output.splitlines():
        if repo_name in line:
            assert status in line or alt_status in line
            return
    assert False, f"Could not find {repo_name} in output:\n{run_output}"
