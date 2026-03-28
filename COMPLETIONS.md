# Testing and Loading Shell Completions

This document explains how to manually load and verify the shell completion scripts for the git tools in this repository.

## Prerequisites

Ensure you have the tools available in your `PATH`. If you are developing locally, you can use `pdm run`:

```bash
# Example of making the tools available (in a Bash-like shell)
export PATH="$PATH:$(pdm run which git-commit-stats | xargs dirname)"
```

## Bash

To manually load and test Bash completions:

1.  **Source the script:**
    ```bash
    source completions/git-tools.bash
    ```
2.  **Verify:**
    - Type `git-commit-stats -` and press `Tab`. You should see `--help`, `--version`, and `-V`.
    - Type `git-pack-stats -` and press `Tab`. You should see the same options.
    - Type `git-commit-stats ` (with a space) and press `Tab`. It should suggest directories.

## Zsh

Zsh completions are more complex because they can be loaded via `source` (eval) or via the `fpath` (autoload).

### Method 1: Sourcing (Recommended for testing)

1.  **Initialize completion system (if not already done):**
    ```zsh
    autoload -Uz compinit && compinit
    ```
2.  **Source the script:**
    ```zsh
    source completions/git-tools.zsh
    ```
3.  **Verify:**
    - Type `git-commit-stats -<TAB>`. It should show the options with descriptions.
    - Type `git-pack-stats -<TAB>`. It should also work.

### Method 2: Using fpath (Production-like)

1.  **Create a temporary completion directory:**
    ```zsh
    mkdir -p ~/.zfunc
    ```
2.  **Copy and rename the script:**
    The file **must** be named `_git-tools`.
    ```zsh
    cp completions/git-tools.zsh ~/.zfunc/_git-tools
    ```
3.  **Add to fpath in your `~/.zshrc` (or current session):**
    ```zsh
    fpath=(~/.zfunc $fpath)
    autoload -Uz compinit && compinit
    ```
4.  **Verify:**
    Start a new shell or run `compinit`. Type `git-commit-stats -<TAB>`.

## Troubleshooting

- **"command not found: _shtab_..."**: This usually means the functions weren't correctly defined before `compdef` was called. Our `git-tools.zsh` script is designed to avoid this by using a robust dispatcher.
- **No completions shown**: Ensure `compinit` has been run. In some environments, you might need to run `rm -f ~/.zcompdump; compinit` to clear the completion cache.
- **Permission denied**: Ensure the completion scripts are readable.
- **Command is not in PATH**: If the completion script is loaded but the command itself is not in your `PATH`, Zsh might not trigger the completion function.
