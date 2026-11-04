@PROB-001 @SPEC-001 @FEAT-004
Feature: Isolated Git Worktree Execution and Spec Tamper Prevention for pi
  As a Technical Lead
  I want the pi coding agent to execute in an isolated Git worktree with zero secrets and read-only specs
  So that pi cannot alter acceptance tests or leak credentials

  Background:
    Given a temporary Git repository with a locked "specs/" directory

  Scenario: Creating an isolated Git worktree with scrubbed secrets and read-only specs
    Given environment variables include sensitive tokens "TRELLO_TOKEN" and "GITHUB_TOKEN"
    When the Worktree Manager prepares an isolated worktree for "FEAT-004"
    Then a git worktree is created on branch "feat/FEAT-004"
    And files inside the worktree "specs/" directory are marked read-only
    And the sanitized environment for "pi" does not contain "TRELLO_TOKEN" or "GITHUB_TOKEN"

  Scenario: Detecting Gherkin specification tampering and blocking Pull Request creation
    Given an isolated worktree for "FEAT-004" with recorded spec SHA-256 checksums
    When an untrusted process forces a modification to a feature file in the worktree
    Then the Worktree Manager tamper check fails with error "SPEC_TAMPERING_DETECTED"
    And a CRITICAL IssueNode of category "SECURITY" is recorded in the Traceability Graph
