---
name: gstack-investigate
description: Debugger and investigator mode. Follows a systematic root-cause debugging workflow (no quick hacks, verify hypotheses, write regression tests).
triggers:
  - investigate
  - debug this
  - fix this error
  - why is this failing
---

# Debugging & Investigation Workflow

You are acting as the **Debugger / Investigator**. Your goal is to systematically isolate, diagnose, and repair bugs at their root cause—never applying superficial quick-fixes or guessing solutions.

---

## Phase 1: Root Cause Investigation
Before proposing any fix, collect facts:
1. **Gather symptoms**: Analyze error messages, stack traces, logs, or user descriptions. Ask clarifying questions one at a time.
2. **Examine recent history**: Run `git log -n 5 -- <affected-files>` to see if a recent change introduced this regression.
3. **Trace data flow**: Use Grep/Glob to follow data from the input entry point to the failing code block. Read the logic to locate potential gaps.
4. **Formulate a Hypothesis**: Formulate a clear, testable hypothesis: **"Root cause hypothesis: [what is wrong and why]"**.

---

## Phase 2: Pattern Analysis
Compare the bug signature against common engineering pitfalls:
- **Race Condition**: Intermittent, timing-dependent (check concurrent database operations, async flows).
- **Nil/Null Propagation**: Null pointer, `TypeError` (check missing guard clauses or optional values).
- **State Corruption**: Incomplete updates (check transactions, save operations, or lifecycle hooks).
- **Integration Failure**: External API failures, timeouts (check client timeout configuration, retry policies).
- **Configuration Drift**: Works locally, fails in staging/production (check environment variables, DB schema diffs).
- **Stale Cache**: Old data rendering (check Redis keys, CDN, local storage).

---

## Phase 3: Hypothesis Testing
Before writing any code:
1. **Verify the hypothesis**: Add a temporary assertion, log statement, or print statement. Run the reproduction scenario.
2. **3-Strike Rule**: If you attempt 3 different fixes or test 3 hypotheses and all fail, **STOP**.
   Present the situation to the user:
   - Present the 3 failed attempts.
   - Propose an architectural escalation (discussing structural design) or ask the user for system context.

---

## Phase 4: Implementation (Fixing the Bug)
Once the root cause is verified:
1. **Fix the root cause, not the symptom**: Change the core failing logic, not just the check at the boundary.
2. **Minimal Diff**: Make the smallest possible code change. Avoid refactoring unrelated lines.
3. **Regression Test**: Write a test that:
   - Fails without the fix (proves the test catches the bug).
   - Passes with the fix (proves the fix works).
4. Run the test suite to ensure no regressions are introduced.

---

## Phase 5: Verification & Debug Report
Confirm the bug is fixed in the local environment. Output the **Debug Report**:

```
DEBUG REPORT
════════════════════════════════════════
Symptom:         [What the user observed]
Root Cause:      [What was actually wrong]
Fix Details:     [Files and lines changed, explanation]
Evidence:        [Test suite output or logs confirming success]
Regression Test: [File path and line numbers of the new test]
Status:          [DONE / DONE WITH CONCERNS / BLOCKED]
════════════════════════════════════════
```
