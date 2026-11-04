@PROB-001 @SPEC-001 @FEAT-006
Feature: Step-by-Step Task Conversation and Design Ledger Tracking
  As a Technical Lead or System Analyst
  I want a dedicated task folder recording the Task ID, date, description, and step outputs in Markdown
  So that every conversation, system design, human decision, coding run, and review is preserved in Git

  Background:
    Given an initialized Task Ledger Manager and Traceability Graph

  Scenario: Initializing a Task Ledger and recording step outputs with secret redaction
    Given ProblemNode "PROB-001" exists in the Traceability Graph
    When I initialize a Task Ledger for task "TASK-101" on date "2026-11-01" with description "Implement OAuth2 PKCE flow"
    And I append step "01-grill-me-conversation" containing a simulated token "ghp_1234567890abcdefghijklmnopqrstuv"
    And I append step "02-system-analysis-design" containing "C4 Component Diagram and STRIDE Threat Model"
    Then the task folder "2026-11-01_TASK-101_implement-oauth2-pkce-flow" exists with a "README.md" containing "TASK-101" and "2026-11-01"
    And step file "01-grill-me-conversation.md" has redacted the simulated token
    And TaskJournalNode "TASK-101" is registered in the Traceability Graph with completed steps
