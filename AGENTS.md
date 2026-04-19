# Agent Guidelines for Git Tools Repository

Welcome, Agent. This repository contains a collection of Git helper tools. Please adhere to the following guidelines when working here:

## 1. Deep Planning and Requirement Gathering
* Before starting any task, enter a deep planning mode.
* You must have absolute certainty of the requirements before setting a plan.
* Use `request_user_input` and `message_user` to ask as many clarifying questions as needed to eliminate all doubts and verify assumptions.
* Do not proceed to the planning phase until you have confirmation from the user on all critical aspects.
* Once requirements are crystal clear, set a detailed plan using `set_plan`.
* If the user requests changes after initial plan approval, you must restart deep planning to clarify the new requirements and then present an updated plan for approval. Never begin making code changes without an approved plan.
* After the plan is approved, execute it autonomously. Do not ask for further confirmation or status updates unless you hit a significant blocker that requires a decision from the user.

## 2. Dependency Management and Runtime
* Use **PDM** for all dependency management (installing, running tests, etc.).
* Runtime code must be restricted to the **Python standard library** only. Do not add or use any third-party libraries for runtime functionality.
* External libraries like `pytest`, `pytest-mock`, `pytest-cov`, and `ruff` are permitted only as development dependencies.

## 3. Testing and Quality Assurance
* Maintain **100% test coverage** for all new and existing code. This is enforced by `pytest-cov`.
* **No Coverage Exclusions:** The use of `# pragma: no cover` or any other method to exclude code from test coverage is strictly prohibited. 100% of the code must be exercised by tests.
* Use `pytest` for functional testing and `ruff` for linting.
* For every code change, include steps in your plan to verify correctness and coverage.
* **Mandatory CI Verification:** Before pushing any code, you MUST run all tools and checks that are part of the GitHub Actions workflow (e.g., `ruff check .` and `pytest`).
* A failure in the GitHub Actions workflow is **unacceptable**. You are responsible for ensuring all CI checks pass locally in the sandbox before submission.

## 4. Metadata and Identification
* Use the following metadata for project configuration:
    * **Project Name:** git-tools
    * **Author Name:** jfasoc
    * **Email:** 7720125+jfasoc@users.noreply.github.com

## 5. Tool Implementation Best Practices
* Helper tools should be located in `src/git_tools/` and registered as scripts in `pyproject.toml`.
* **Commit Message Validation:** All commits must follow the conventional commits format. To enforce this locally, ensure you install the commit-msg hook:
    ```bash
    pre-commit install --hook-type commit-msg
    ```
* **Minimal Main Pattern:** The `main()` function should be as simple as possible, typically a single call to a `run()` function. For example:
    ```python
    def main():
        run(get_parser().parse_args())
    ```
    The `run()` function should handle high-level orchestration, such as argument processing and error handling (e.g., `try-except` blocks for `SystemExit` or general `Exception`), while delegating data collection to a `collect_stats()` function and output formatting to a `print_stats()` function.
* Tools must default to scanning the **current working directory (CWD)** for a Git repository but should also support an **optional repository path** as a command-line argument.
* For data output, use formatted tables with clear headers.
* When presenting statistics (like object counts or sizes), include total counts and calculate percentage distribution where applicable.
* Sort results by the most significant metric (e.g., object count in descending order) by default.
* **Scope Integrity:** DO NOT modify or remove code in functions or tools unrelated to your current task. Accidentally deleting existing features is a major failure.
* **Verification over Feedback:** Prioritize the actual source code as the ground truth. If a code review or external feedback contradicts the existing code (e.g., claiming a feature is "unimplemented" when it is clearly present), you must verify the code before taking action.
* **Update Completion Files:** Whenever CLI parameters are added, removed, or modified, you MUST regenerate the shell completion scripts (e.g., by running `python3 scripts/generate_completions.py`).
* **Commit Message Validation:** When running `cz check` manually, use the `--rev-range` flag to skip historical commits that do not follow the conventional commits format. The recommended start commit is `60c103d`.
    ```bash
    cz check --rev-range 60c103d..HEAD
    ```

## 6. Documentation
* All Python source code must be thoroughly documented using **Google-style docstrings**.
* Every module, class, and function (except for simple internal helpers if they are truly self-explanatory) must have a docstring.
* Docstrings should include a summary, arguments (if any), and return values (if any).
