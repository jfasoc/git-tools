import os

def test_bash_completion_content():
    path = "completions/git-tools.bash"
    assert os.path.exists(path)
    with open(path, "r") as f:
        content = f.read()

    # Check for both commands
    assert "complete -o filenames -F _shtab_git_commit_stats git-commit-stats" in content
    assert "complete -o filenames -F _shtab_git_pack_stats git-pack-stats" in content

    # Check for version flags in Bash
    assert "-V" in content
    assert "--version" in content

    # Check for directory completion
    assert "_shtab_compgen_dirs" in content

def test_zsh_completion_content():
    path = "completions/git-tools.zsh"
    assert os.path.exists(path)
    with open(path, "r") as f:
        content = f.read()

    # Check for compdef header
    assert content.startswith("#compdef git-commit-stats git-pack-stats")

    # Check for both functions
    assert "_shtab_git_commit_stats()" in content
    assert "_shtab_git_pack_stats()" in content

    # Check for registration logic
    assert "compdef _shtab_git_commit_stats git-commit-stats" in content
    assert "compdef _shtab_git_pack_stats git-pack-stats" in content

    # Check for version flags in Zsh
    assert "{-V,--version}" in content

    # Check for directory completion (_files -/)
    assert ":_files -/" in content
