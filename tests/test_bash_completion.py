import subprocess
import os
import shutil


def test_bash_completion_integration():
    """Simulate a bash session and check completions for the tools."""
    bash_path = shutil.which("bash")
    if not bash_path:
        import pytest

        pytest.skip("bash not found")

    # Load the completion script and ask for completions
    # We use 'compgen' which is the underlying bash command for completion
    script_path = os.path.abspath("completions/git-tools.bash")

    # Test git-commit-stats
    # Let's try a simpler approach by calling compgen directly if we know how shtab registers it
    # Registration is: complete -o filenames -F _shtab_git_commit_stats git-commit-stats

    test_script = f"""
source {script_path}
COMP_WORDS=(git-commit-stats -)
COMP_CWORD=1
_shtab_git_commit_stats
echo "${{COMPREPLY[@]}}"
"""
    result = subprocess.run(
        [bash_path, "-c", test_script], capture_output=True, text=True
    )

    output = result.stdout.strip()
    assert "--help" in output
    assert "--version" in output
    assert "-V" in output

    # Test git-pack-stats
    test_script_pack = f"""
source {script_path}
COMP_WORDS=(git-pack-stats -)
COMP_CWORD=1
_shtab_git_pack_stats
echo "${{COMPREPLY[@]}}"
"""
    result_pack = subprocess.run(
        [bash_path, "-c", test_script_pack], capture_output=True, text=True
    )

    output_pack = result_pack.stdout.strip()
    assert "--help" in output_pack
    assert "--version" in output_pack
    assert "-V" in output_pack
