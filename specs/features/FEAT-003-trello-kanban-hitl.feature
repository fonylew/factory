@PROB-001 @SPEC-001 @FEAT-003
Feature: Trello Kanban State Machine and Human-in-the-Loop Decision Flow
  As a Technical Lead or System Analyst
  I want every Trello card to enforce System Analysis, Design, and Acceptance Criteria
  And pause in "2. Need Decision" until an authorized human provides a decision in "3. Human Decision"

  Background:
    Given an initialized Kanban State Machine and Traceability Graph

  Scenario: Blocking transition to Ready for Dev when System Analysis or Acceptance Criteria are missing
    Given a Kanban card for "FEAT-003" is in column "1. Problem & Spec Backlog"
    And the card description is missing "## 2. System Analysis & Enterprise Design"
    When the orchestrator attempts to move card "FEAT-003" to "4. Ready for Dev (Spec Locked)"
    Then the transition is rejected with error "MISSING_MANDATORY_CARD_SECTIONS"
    And card "FEAT-003" remains in column "1. Problem & Spec Backlog"

  Scenario: Pausing in Need Decision and resuming after an authorized Human Decision
    Given a valid Kanban card for "FEAT-003" is in column "1. Problem & Spec Backlog"
    When the analyst agent escalates question "ADR-010" regarding "Caching eviction policy"
    Then card "FEAT-003" transitions to column "2. Need Decision"
    When authorized member "tech_lead_01" writes decision "Use Redis TTL with circuit breaker" in "## 5. Human Decision"
    And moves card "FEAT-003" to column "3. Human Decision"
    And the orchestrator processes human decisions
    Then DecisionNode "ADR-010" is recorded in the Traceability Graph with decision "Use Redis TTL with circuit breaker"
    And card "FEAT-003" transitions to column "4. Ready for Dev (Spec Locked)"
