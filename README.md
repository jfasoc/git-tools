# Git Tools

A collection of Git helper tools.

## Tools

### git-stats

Unified git statistics tool. It provides the following subcommands:

- `commit`: Lists all commits with file change counts (Regular vs Symlinks).
- `pack`: Lists all pack files and loose objects with their object counts and disk sizes. It also shows a summary total and percentage distribution for both objects and sizes. The pack files are sorted by object count, with the largest first. See [SIZES.md](doc/SIZES.md) for details on size calculations.

### git-repo-manager

A tool for managing multiple Git repositories. See [REPO_MANAGER.md](doc/REPO_MANAGER.md) for more information.

## Shell Completion

To enable shell completion for the `git-stats` and `git-repo-manager` commands, you can source the completion scripts in your shell's configuration file. See [COMPLETIONS.md](doc/COMPLETIONS.md) for detailed instructions.

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
