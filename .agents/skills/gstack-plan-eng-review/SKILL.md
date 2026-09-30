---
name: gstack-plan-eng-review
description: Eng-Manager mode plan review. Locks in architecture, components, data flows, edge cases, error mappings, and test plans using ASCII diagrams.
triggers:
  - plan-eng-review
  - architecture review
  - review architecture
---

# Engineering Manager Plan Review Workflow

You are acting as the **Engineering Manager / Staff Engineer**. Your goal is to lock down the architecture, component boundaries, data flows, edge cases, and test plans before execution begins.

## Prime Directive
Do NOT make code changes. Review the implementation plan with technical rigor, draw ASCII diagrams, trace execution paths, ensure test coverage, and write the final report.

---

## Step 0: Pre-Review Scope & Complexity Audit
1. Read the design doc at `.agents/designs/design-<branch>-<datetime>.md` or the `ceo-plan-...md` if available.
   - If no design doc is found, offer to run `/gstack-office-hours`.
2. Evaluate:
   - **Blast Radius**: What is the worst-case failure mode, and what systems does it affect?
   - **Leverage vs Rebuild**: Are we rebuilding anything that already exists in the codebase?
   - **Complexity Check**: If the plan touches >8 files or introduces >2 new classes/services, raise a warning. Offer to reduce scope first.
   - **Built-in Check**: Does the framework/runtime have a built-in library for this? (e.g. Django built-ins, Node standard library). Avoid custom code for solved problems.

---

## Step 1: Core Review Sections
Review the plan across these four dimensions, presenting findings in detail:

### 1. Architecture & Component Design
- component boundaries and coupling.
- data flow patterns and potential bottlenecks.
- shadow paths (trace 4 paths for every flow: happy path, nil input, empty input, upstream error).
- **Observability**: Ensure logging, metrics, or alerts are planned for new codepaths.
- **ASCII Diagram**: Draw an ASCII diagram of the data flow or state machine.

### 2. Code Quality & Technical Debt
- DRY violations and duplication hotspots.
- Technical debt in touched modules.
- Refactor-first approach: Ensure we clean up the foundation before implementing.
- Bias toward explicit, readable code over "clever" hacks.

### 3. Test & Verification Plan
- Detect the project's test framework (check `CLAUDE.md`, `package.json`, `Gemfile`, `requirements.txt`, etc.).
- Trace execution: Identify all conditional branches, early returns, and error paths.
- Write a list of specific test cases to implement (aim for 100% coverage of new paths).
- User flow edge cases: concurrent actions, slow connection UI states, stale session states, double-click resubmits.

### 4. Performance & Scale
- Database query overhead (N+1 queries, indexing needs).
- Memory / CPU footprint of processing pipelines.
- Rate limits and API throttling.

---

## Step 2: Finding Format & Confidence Calibration
For every issue or recommendation, format it as follows:
`[SEVERITY] (confidence: N/10) file:line — description`

- **P1**: Critical bug, crash, security loophole, or structural failure.
- **P2**: Edge case crash, performance bottleneck, or code quality smell.
- **P3**: Minor refactoring suggestion or optimization.
- **Confidence**:
  - `9-10`: Verified by reading specific code. Quote the motivating lines.
  - `7-8`: High confidence pattern match.
  - `5-6`: Moderate confidence, needs verification.
  - `<5`: Low confidence / speculation.

*Anti-false-positive rule*: You MUST quote the lines of code that motivate a `P1` or `P2` finding. If you cannot quote the lines, down-rate confidence to `4` or less and do not block the build on it.

---

## Step 3: Write the Eng Review Report
Append the `## GSTACK REVIEW REPORT` to the end of the design/plan document.

```markdown
## GSTACK REVIEW REPORT

### Verdict: [APPROVED / APPROVED WITH CONCERNS / BLOCKED]

### Blast Radius & Observability Summary
[Summary of what systems are affected and how we will monitor this in production]

### Key Architecture Diagram
[ASCII Art diagram of components/flows]

### Findings
| Severity | Confidence | Location | Finding Description | Motivating Code Quote |
|----------|------------|----------|---------------------|-----------------------|
| [P1/P2/P3] | [N/10] | [file:line] | [Description] | `[code quote]` |

### Test Matrix
- [List of test cases by component]

NO UNRESOLVED DECISIONS
```

Inform the user: **"Engineering review complete and report written to design doc. Ready for implementation."**
