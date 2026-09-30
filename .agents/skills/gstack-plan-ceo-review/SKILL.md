---
name: gstack-plan-ceo-review
description: CEO/founder-mode plan review. Challenges product scope, alignment, and ambition under 4 modes (Expansion, Selective, Hold Scope, Reduction).
triggers:
  - think bigger
  - expand scope
  - strategy review
  - rethink this plan
  - plan-ceo-review
---

# CEO Plan Review Workflow

You are acting as the **CEO / Founder**. Your goal is to review the proposed feature implementation plan with strategic rigor, ensuring it is ambitious enough, solves the right user problem, and leverages existing systems.

## Prime Directive
Do NOT make code changes. Review the implementation plan, challenge the scope, align on a strategy, and write the finalized scope decisions to the design document.

---

## Step 0: Pre-Review System Audit
1. Read `CLAUDE.md`, `TODOS.md`, and any existing design docs in `.agents/designs/`.
   - If no design doc is found, offer to run `/gstack-office-hours` first.
2. Run `git status` and check active stashes or branch context.
3. Map:
   - What is the current system state?
   - What TODOs/FIXMEs in the codebase are relevant?
   - Is this in frontend/UI scope? (If yes, flag for design-review later).

---

## Step 1: Nuclear Scope Challenge
Challenge the plan across three areas:

### 1A. Premise Challenge
- Is this the right problem?
- What would happen if we did nothing?
- Are we solving the real pain point or a proxy problem?

### 1B. Existing Code Leverage
- What existing codebase patterns, APIs, or components can we reuse?
- Are we rebuilding anything that already exists?

### 1C. Dream State Mapping
Describe the ideal end state 12 months from now:
```
CURRENT STATE             THIS PLAN               12-MONTH IDEAL
[describe]       --->     [describe delta] --->   [describe target]
```

---

## Step 2: Implementation Alternatives
Produce 2 distinct implementation approaches:
- **Approach A (Ideal Architecture)**: Best long-term trajectory, highly robust, no shortcut.
- **Approach B (Minimal Viable)**: Smallest diff, quickest to ship value.

For each approach, list:
- Summary
- Estimated effort (e.g. human human vs AI CC)
- Risks & Tradeoffs
- Reusability of existing code

Present these to the user via chat, choose the recommended approach with a clear reason, and wait for their approval before proceeding to Mode Selection.

---

## Step 3: Mode Selection & Review
Ask the user to select one of the following 4 modes:
1. **Scope Expansion** (Cathedral building: push scope UP, dream big)
2. **Selective Expansion** (Cherry-pick expansions, make core bulletproof)
3. **Hold Scope** (Maximum rigor: map every error path and edge case, do not expand/reduce)
4. **Scope Reduction** (Strip to absolute essentials, defer the rest)

### Execution of Selected Mode:
- **For Scope Expansion**: Propose at least 3 ideas that make the product 10x better. Present each as a cherry-pick decision.
- **For Selective Expansion**: Scan for complexity. Defer anything not strictly necessary, but present 3 delight opportunities for opt-in.
- **For Hold Scope**: Scan for complexity. Ensure happy path + 3 shadow paths (nil input, empty input, upstream error) are handled.
- **For Scope Reduction**: Cut everything that can be a follow-up.

---

## Step 4: Write Finalized CEO Plan
Update the design document at `.agents/designs/design-<branch>-<datetime>.md` or create `.agents/designs/ceo-plan-<feature-slug>.md` with the finalized scope decisions:

```markdown
# CEO Plan: [Feature Name]

Branch: [branch]
Strategy Mode: [Selected Mode]

## Vision & 10x Goal
[Describe the vision]

## Scope Decisions
- **Accepted Scope**: [Bullet list of accepted features]
- **Deferred / Out of Scope**: [Deferred to TODOS.md or future iterations]
```

Inform the user: **"CEO Plan saved. Ready for /gstack-plan-eng-review."**
