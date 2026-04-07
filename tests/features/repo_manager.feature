Feature: Git Repo Manager
    As a developer
    I want to manage multiple Git repositories
    So that I can easily see their status in one place

    Scenario: Scanning for repositories
        Given a search directory "/tmp/test-search"
        And a Git repository at "/tmp/test-search/repo1"
        And a configuration file with search directory "/tmp/test-search"
        When I run "git-repo-manager scan"
        Then the configuration should contain "/tmp/test-search/repo1"
        And the output should indicate 1 active repository was found

    Scenario: Displaying repository status
        Given a search directory "/tmp/test-search"
        And a Git repository at "/tmp/test-search/repo1" on branch "main"
        And a configuration file with repositories "repo1" in "/tmp/test-search"
        When I run "git-repo-manager status"
        Then the output should contain a table with "repo1" on branch "main"

    Scenario: Detecting modified and untracked files
        Given a search directory "/tmp/test-search"
        And a Git repository at "/tmp/test-search/repo1"
        And a configuration file with repositories "repo1" in "/tmp/test-search"
        And the repository "/tmp/test-search/repo1" has 2 modified files
        And the repository "/tmp/test-search/repo1" has 3 untracked files
        When I run "git-repo-manager status"
        Then the output should show 2 modified and 3 untracked files for "repo1"

    Scenario: Handling bare repositories
        Given a search directory "/tmp/test-search"
        And a bare Git repository at "/tmp/test-search/bare-repo"
        And a configuration file with repositories "bare-repo" in "/tmp/test-search"
        When I run "git-repo-manager status"
        Then the output should show "bare-repo" in the status table
        And the modified and untracked counts for "bare-repo" should be "N/A"

    Scenario: Marking missing repositories as inactive
        Given a search directory "/tmp/test-search"
        And a configuration file with repositories "repo1" in "/tmp/test-search"
        And the repository "/tmp/test-search/repo1" does not exist
        When I run "git-repo-manager scan"
        Then the configuration should show "/tmp/test-search/repo1" as inactive
        And the output should indicate "/tmp/test-search/repo1" is no longer present

    Scenario: Using storage option
        Given a search directory "/tmp/test-search"
        And a Git repository at "/tmp/test-search/repo1"
        And a configuration file with repositories "repo1" in "/tmp/test-search"
        When I run "git-repo-manager status --storage"
        Then the output should contain "Packs" and "Loose" columns

    Scenario: Fetching from remote
        Given a search directory "/tmp/test-search"
        And a Git repository at "/tmp/test-search/repo1"
        And the repository "/tmp/test-search/repo1" has a remote "origin"
        And a configuration file with repositories "repo1" in "/tmp/test-search"
        When I run "git-repo-manager status --fetch"
        Then the output should show "Up-to-date" or "N/A" for "repo1"
