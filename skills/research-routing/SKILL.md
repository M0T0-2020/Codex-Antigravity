---
name: research-routing
description: Routing rules to decide when Codex handles tasks vs when to delegate to Antigravity CLI.
---

# Research Routing Heuristics

Rules and decision trees for routing tasks between **Codex** (Implementation, Reasoning, Architecture) and **Antigravity CLI** (Scout, Web Research, Fact Gathering).

## Routing Decision Tree

```text
                    Incoming Task
                          │
         ┌────────────────┴────────────────┬────────────────┐
         ▼                                 ▼                ▼
   Requires code change           Need codebase status    Need test run
    or file editing?              or external research?   or failure diagnosis?
         │                                 │                │
         ▼                                 ▼                ▼
       Codex                      Antigravity Scout      Test Delegator
(Implements & edits)               (Read-only facts)    + Antigravity QA
```

## Responsibility Matrix

| Task Type | Assigned To | Rationale |
| --- | --- | --- |
| Latest library version / docs lookup | **Antigravity** | Web lookup, fast fact retrieval |
| GitHub issue & PR search | **Antigravity** | External search, scouting workarounds |
| Codebase architecture & stack discovery | **Antigravity** | Read-only structural reconnaissance (`/codebase`) |
| Change impact & call graph analysis | **Antigravity** | Mapping blast radius before refactoring |
| Codebase quality & tech debt audit | **Antigravity** | Static identification of TODOs and smells |
| Test suite execution & metrics collection | **Test Delegator** | Isolated subprocess runner; protects context |
| Test failure triage & root-cause analysis | **Antigravity QA** | AI diagnosis pinpointing cause and suggested fix |
| Code implementation & refactoring | **Codex** | Repository modifications must stay with Codex |
| Bug fixing & applying patches | **Codex** | Requires codebase understanding & editing |
| Final architectural decisions | **Codex** | Core reasoning & long-term maintainability |

## Golden Rules

1. **Antigravity is Scout & QA; Codex is the Lead Engineer**:
   - External & Codebase Research → Antigravity
   - Test Execution & Failure Triage → Test Delegator + Antigravity
   - Reasoning & Architecture Decisions → Codex
   - Implementation & File Edits → Codex
2. **Never pollute Codex's context with raw tracebacks**:
   - Run tests via `test_delegate.py` to get structured metrics and concise AI diagnosis.
3. **Minimize delegated context**:
   - Target specific subqueries or project directories rather than entire chat histories.

