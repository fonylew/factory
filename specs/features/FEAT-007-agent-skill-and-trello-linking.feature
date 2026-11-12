@PROB-001 @SPEC-001 @FEAT-007
Feature: Installable Software Factory Skill and Atomic Task-to-Trello Initialization and Linking
  As a Technical Lead, System Analyst, or AI Agent
  I want an installable software-factory skill and a unified workflow to initialize and link tasks with Trello
  So that agents can autonomously operate the factory and keep tasks, specs, graph nodes, and Trello cards synchronized

  Background:
    Given an initialized Traceability Graph store

  Scenario: Installing the software-factory skills and MCP server configuration for agents
    Given a temporary agent configuration directory
    When the factory skill installer executes setup for the agent configuration directory
    Then the skills "software-factory", "grill-me-analyst", and "security-prod-auditor" are installed in the skills directory
    And the MCP configuration file registers the "agentic-software-factory" server

  Scenario: Atomically initializing a Task, Feature spec, and linked Trello Kanban card
    Given ProblemNode "PROB-001" and SystemSpecNode "SPEC-001" are linked in the Traceability Graph
    And an initialized Trello Kanban board with all 8 mandatory factory lists
    When an agent initializes and links task "TASK-202" and feature "FEAT-202" titled "Zero-Trust Token Validator" on date "2026-11-05"
    Then the task folder "2026-11-05_TASK-202_zero-trust-token-validator" contains a "README.md" linked to Trello card "CARD-FEAT-202"
    And FeatureNode "FEAT-202" and TaskJournalNode "TASK-202" are linked to "CARD-FEAT-202" in the Traceability Graph
    And the Trello Kanban board has card "FEAT-202" in column "4. Ready for Dev (Spec Locked)" with complete System Analysis and Acceptance Criteria
