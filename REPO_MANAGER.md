# Git Repo Manager Design Document

## Overview

`git-repo-manager` is a tool designed to track and report on multiple Git repositories across a user's filesystem. It maintains a persistent configuration of "search directories" and "discovered repositories," allowing for efficient status reporting without the need for manual navigation or constant re-scanning.

## 1. Configuration

The tool uses a simple, plain-text configuration file, typically located at `~/.config/git-tools/git-repo-manager`.

### 1.1 Sections

- **`[search]`**: Contains a list of absolute or relative paths to directories that should be scanned for Git repositories.
- **`[repos]`**: Maintains an alphabetically sorted list of discovered repositories.
    - Each entry follows the format: `path = # YYYY-MM-DD HH:MM:SS`
    - Repositories that are no longer found during a scan are marked as "inactive" by prefixing the line with `# `.
    - Comments in this section are preserved to keep track of when a repository was last verified.

### 1.2 Custom Path

Users can override the default configuration path using the global `-c/--config` parameter.

## 2. Command Set

### 2.1 `scan`

Recursively traverses directories listed in the `[search]` section to identify Git repositories.
- **Discovery Logic**: A directory is identified as a Git repository if it contains a `.git` entry and passes `git rev-parse --is-inside-work-tree`.
- **Optimization**: Once a repository is found, the tool stops deeper recursion within that directory.
- **Persistence**: Updates the `[repos]` section, adding new discoveries and commenting out missing ones.

### 2.2 `status`

Provides a summarized state of all "active" (uncommented) repositories in the `[repos]` section.

#### Data Columns
- **Path**: Path relative to the matching search directory.
- **Branch**: Current active branch or detached HEAD state.
- **Remote Status**: Comparison against the upstream branch (`@{u}`), showing "Ahead X", "Behind Y", "Up-to-date", or "N/A".
- **Mod**: Count of modified/staged files (parsed from `git status --porcelain`).
- **Unt**: Count of untracked files (parsed from `git status --porcelain`).

#### Features
- **Grouping**: Repositories are grouped by their parent search directory.
- **Concurrency**: Status gathering is parallelized using a `ThreadPoolExecutor`. The number of workers defaults to the CPU core count but can be tuned via `-j/--jobs`.
- **Fetching**: An optional `--fetch` flag allows for refreshing the remote state (default: `origin`) before checking the status.
- **Robustness**: Long strings in the table are truncated with ellipses (`...`) to maintain a clean layout. Errors (e.g., missing directory) are reported per-row.

## 3. Implementation Details

### 3.1 Concurrency Model
The `status` command is I/O-bound as it spawns multiple Git subprocesses. Using threads is preferred over processes for low overhead. The tool ensures thread safety by collecting results into a dictionary keyed by path and performing all printing on the main thread after all tasks are completed.

### 3.2 Path Normalization
The tool aggressively normalizes paths using `os.path.abspath` and `os.path.expanduser` to ensure consistency between configuration storage and filesystem lookups, even when the user changes their current working directory.

### 3.3 Shell Completions
Static shell completion scripts for Bash and Zsh are generated using `shtab`. To ensure portability, dynamic values (like CPU count or HOME expansion) are handled during tool execution rather than being baked into the argument parser's defaults.

## 4. Quality Standards

- **100% Test Coverage**: Every line of code, including entry points and error handlers, must be covered by tests. The use of `# pragma: no cover` is prohibited.
- **Linting**: All code must pass `ruff` checks.
- **Zero External Dependencies**: At runtime, the tool must rely only on the Python standard library.
