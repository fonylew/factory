@PROB-001 @SPEC-001 @FEAT-002
Feature: Traceability Graph Traversal, Impact Analysis, and Deterministic Export
  As a System Analyst
  I want a local graph system that tracks problems, specs, features, code, decisions, tasks, and open issues
  So that I can query what is to-do, inspect open issues, and compute blast-radius impact

  Background:
    Given an initialized Traceability Graph store

  Scenario: Exporting the Traceability Graph to deterministic JSON-LD and Mermaid formats
    Given ProblemNode "PROB-001", SystemSpecNode "SPEC-001", and FeatureNode "FEAT-002" are linked in the graph
    And IssueNode "ISS-100" of severity "HIGH" and category "SECURITY" affects "FEAT-002"
    When the graph is exported to JSON-LD and Mermaid files
    Then the JSON-LD export contains nodes "PROB-001", "SPEC-001", "FEAT-002", and "ISS-100"
    And the Mermaid export contains a directed diagram linking "PROB-001" to "SPEC-001" and "FEAT-002"
    And querying open issues returns "ISS-100" blocking "FEAT-002"

  Scenario: Computing downstream blast radius when a System Spec changes
    Given ProblemNode "PROB-001", SystemSpecNode "SPEC-001", and FeatureNode "FEAT-002" are linked in the graph
    And CodeArtifactNode "CODE-002" implements "FEAT-002"
    When impact analysis is executed for "SPEC-001"
    Then the downstream affected nodes include "FEAT-002" and "CODE-002"
