@PROB-001 @SPEC-001 @FEAT-001
Feature: Grill-Me Problem Discovery and Immutable Spec Anchoring
  As a Technical Lead or System Analyst
  I want every feature to be anchored to a verified Problem Statement and System Spec
  So that coding agents never lose track of the original problem or violate enterprise invariants

  Background:
    Given an initialized Traceability Graph store

  Scenario: Rejecting an orphan feature specification without a Problem Statement link
    Given ProblemNode "PROB-001" exists in the Traceability Graph
    And SystemSpecNode "SPEC-ORPHAN" is registered without a valid ProblemNode link
    When an agent attempts to validate FeatureNode "FEAT-ORPHAN" linked to "SPEC-ORPHAN"
    Then the Graph Validator rejects the feature with error "ORPHAN_FEATURE_ERROR"

  Scenario: Locking a Gherkin specification with a SHA-256 checksum before coding begins
    Given ProblemNode "PROB-001" and SystemSpecNode "SPEC-001" are linked in the Traceability Graph
    And a Gherkin feature file exists for "FEAT-001"
    When the System Analyst locks "FEAT-001" for development
    Then FeatureNode "FEAT-001" stores a valid 64-character SHA-256 spec checksum
    And the Graph Validator confirms "FEAT-001" is anchored to "PROB-001"
