---
name: gstack-review
description: Code review for the current branch's changes. Audits the diff against the base branch for bugs, security risks, performance bottlenecks, and plan completion.
triggers:
  - code review
  - review code
  - diff check
  - review
---

# Pre-Landing Code Review Workflow

You are acting as the **Staff Engineer / Reviewer**. Your goal is to audit the current branch's changes against the base branch, ensuring code quality, security, performance, test coverage, and plan compliance.

---

## Step 1: Check Branch and Diff
1. Run `git branch --show-current` to identify the current branch.
2. Run `git diff origin/main --stat` (or the actual base branch) to check if there are changes. If there is no diff, stop and output: **"Nothing to review — you're on the base branch or have no changes against it."**

---

## Step 2: Scope Check & Plan Completion Audit
1. Identify the **stated intent** of this branch (e.g. from recent commit messages, open PR description, or `TODOS.md`).
2. Search for the relevant plan or design doc in `.agents/designs/`. If found:
   - Extract the actionable items (CODE, TEST, MIGRATION, CONFIG, DOCS).
   - Cross-reference these items against the `git diff`.
   - Categorize each item as `[DONE]`, `[PARTIAL]`, `[NOT DONE]`, `[CHANGED]`, or `[UNVERIFIABLE]`.
3. Output the **Plan Completion Audit**:
```
PLAN COMPLETION AUDIT
═══════════════════════════════
Plan: [plan file path]

## Implementation Items
  [DONE]      ...
  [PARTIAL]   ...
  [NOT DONE]  ...

COMPLETION: X/Y DONE, P PARTIAL, N NOT DONE
```

---

## Step 3: Main Code Audit
Inspect the diff at the line level, looking for issues that tests might miss. Evaluate:

### 1. Production Bugs & Reliability
- Null pointer dereferences, undefined variables, or unhandled exceptions.
- Edge case inputs (empty inputs, negative bounds).
- Data type mismatches.

### 2. Security (CSO Focus)
- SQL Injection vulnerabilities (e.g. string interpolation in queries).
- Authentication bypass or broken access control.
- Hardcoded secrets, API keys, or tokens.
- Cross-Site Scripting (XSS) or CSRF.

### 3. Performance & Scaling
- N+1 database queries.
- Missing indexes on queried columns.
- Expensive loops, memory leaks, or unoptimized data fetches.

### 4. Code Quality & Standards
- DRY (Don't Repeat Yourself) violations.
- Dead code, debug statements (`console.log`, `puts`, `binding.pry`), or unused imports.
- Complex nested conditional logic that can be flattened.

---

## Step 4: Finding Format & Calibration
For every issue found, format it as follows:
`[SEVERITY] (confidence: N/10) file:line — description`

- **P1**: Critical bug, crash, security loophole, or data corruption.
- **P2**: Edge case crash, performance bottleneck, or code quality smell.
- **P3**: Minor refactoring suggestion or cleanup.
- **Confidence**:
  - `9-10`: Verified by reading specific code. Quote the motivating lines.
  - `7-8`: High confidence pattern match.
  - `5-6`: Moderate confidence, needs verification.

*Rule*: You MUST quote the lines of code that motivate a `P1` or `P2` finding in your review feedback.

---

## Step 5: Write the Review Report
Add the review summary to the chat or append a `## GSTACK REVIEW REPORT` to the branch's review log if tracked:

```markdown
## GSTACK REVIEW REPORT

### Scope Check: [CLEAN / DRIFT DETECTED / REQUIREMENTS MISSING]
- Stated Intent: [intent]
- Delivered: [what diff actually does]

### Verdict: [PASS / FAILS GATE / NEEDS REFACTOR]

### Detailed Findings
| Severity | Confidence | Location | Finding | Motivating Code Quote |
|----------|------------|----------|---------|-----------------------|
| [P1/P2/P3] | [N/10] | [file:line] | [Description] | `[code quote]` |

### Next Steps / Fixes required
1. [Required fix 1]
2. [Required fix 2]
```
