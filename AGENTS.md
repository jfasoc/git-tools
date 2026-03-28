# Agent Guidelines for Git Tools Repository

Welcome, Agent. This repository contains a collection of Git helper tools. Please adhere to the following guidelines when working here:

## 1. Deep Planning and Requirement Gathering
* Before starting any task, enter a deep planning mode.
* You must have absolute certainty of the requirements before setting a plan.
* Use `request_user_input` and `message_user` to ask as many clarifying questions as needed to eliminate all doubts and verify assumptions.
* Do not proceed to the planning phase until you have confirmation from the user on all critical aspects.
* Once requirements are crystal clear, set a detailed plan using `set_plan`.
* After the plan is approved, execute it autonomously. Do not ask for further confirmation or status updates unless you hit a significant blocker that requires a decision from the user.

## 2. Dependency Management and Runtime
* Use **PDM** for all dependency management (installing, running tests, etc.).
* Runtime code must be restricted to the **Python standard library** only. Do not add or use any third-party libraries for runtime functionality.
* External libraries like `pytest`, `pytest-mock`, `pytest-cov`, and `ruff` are permitted only as development dependencies.

## 3. Testing and Quality Assurance
* Maintain **100% test coverage** for all new and existing code. This is enforced by `pytest-cov`.
* Use `pytest` for functional testing and `ruff` for linting.
* For every code change, include steps in your plan to verify correctness and coverage.
* Always check the existing GitHub Actions workflows (`.github/workflows/`) for additional CI requirements.

## 4. Metadata and Identification
* Use the following metadata for project configuration:
    * **Name:** jfasoc
    * **Email:** 7720125+jfasoc@users.noreply.github.com

## 5. Tool Implementation Best Practices
* Helper tools should be located in `src/git_tools/` and registered as scripts in `pyproject.toml`.
* Tools must default to scanning the **current working directory (CWD)** for a Git repository but should also support an **optional repository path** as a command-line argument.
* For data output, use formatted tables with clear headers.
* When presenting statistics (like object counts or sizes), include total counts and calculate percentage distribution where applicable.
* Sort results by the most significant metric (e.g., object count in descending order) by default.
