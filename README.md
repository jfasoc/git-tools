# Git Tools

A collection of Git helper tools.

## Tools

### git-commit-stats

Lists all commits with file change counts (Regular vs Symlinks).

### git-pack-stats

Lists all pack files and loose objects with their object counts and disk sizes. It also shows a summary total and percentage distribution for both objects and sizes. The pack files are sorted by object count, with the largest first.

## Shell Completion

To enable shell completion for the `git-commit-stats` and `git-pack-stats` commands, you can source the completion scripts in your shell's configuration file.

### Bash

Add the following line to your `~/.bashrc`:

```bash
source /path/to/git_tools/completions/git-tools.bash
```

### Zsh

Add the following line to your `~/.zshrc`:

```zsh
source /path/to/git_tools/completions/git-tools.zsh
```

Alternatively, you can copy the `completions/git-tools.zsh` script to a directory in your `$fpath` and rename it to `_git-tools`.
