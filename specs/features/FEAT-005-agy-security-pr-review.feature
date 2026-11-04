@PROB-001 @SPEC-001 @FEAT-005
Feature: Automated PR Review, Security Analysis, and Dual-Track Issue Tracking by agy
  As a Technical Lead
  I want agy (Gemini 4 Argon) to audit every Pull Request for security flaws and production issues
  So that vulnerabilities and production risks are tracked in both the Graph and Trello before merge

  Background:
    Given an initialized Security Analyzer, Kanban Board, and Traceability Graph

  Scenario: Detecting a production risk and security flaw in a Pull Request diff
    Given ProblemNode "PROB-001", SystemSpecNode "SPEC-001", and FeatureNode "FEAT-005" exist in the graph
    When "agy" audits code for "FEAT-005" containing an unauthenticated secret and an HTTP call without a timeout
    Then the Security Analyzer emits IssueNodes for "HARDCODED_SECRET" and "MISSING_HTTP_TIMEOUT"
    And the IssueNodes are linked to "FEAT-005" in the Traceability Graph
    And corresponding issue cards are created in the Kanban "Issues & Security Findings" column
    And the Pull Request review status for "FEAT-005" is marked as "CHANGES_REQUESTED"
