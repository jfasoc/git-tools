# Investigation Report: `git-stats` vs Standalone Tools

## Summary
The unified `git-stats` tool successfully delegates its functionality to the same underlying logic as `git-commit-stats` and `git-pack-stats`. The behavior and output are identical for the core functionality. However, there are minor differences in command-line argument handling and help messaging.

## Identified Differences

### 1. Command-Line Arguments (`-V/--version`)
* **Standalone Tools:** Both `git-commit-stats` and `git-pack-stats` include a `-V/--version` flag as part of their individual command-line options.
* **Unified Tool:** The parent `git-stats` tool includes a `-V/--version` flag, but it is **not** defined for its subcommands (`commit`, `pack`).
    * `git-stats -V` works.
    * `git-stats commit -V` and `git-stats pack -V` result in an "unrecognized arguments" error.
    * This is because the subcommand parsers in `src/git_tools/stats.py` do not explicitly add the version argument.

### 2. Help Message Content
* **Usage String:** The usage strings differ to reflect the command structure (e.g., `usage: stats.py commit [-h] [repo]` vs `usage: commit_stats.py [-h] [-V] [repo]`).
* **Tool Descriptions:** The descriptions provided in the help messages are identical because they are copied into the subcommand definitions in `stats.py`.

### 3. Output and Behavior
* **Table Format:** The tables generated for both commit and pack statistics are identical across all tools.
* **Error Handling:** Both sets of tools handle non-existent directories and non-git repositories in the same way, producing the same error messages and exiting with the same non-zero code.
* **Default Repository:** All tools default to the current working directory (`.`) if no repository path is provided.

## Conclusion
The tools are functionally equivalent for their primary tasks. The only discrepancy is the placement and availability of the version flag in the unified tool compared to the standalone ones.
