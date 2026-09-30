---
name: gstack-retro
description: Engineering retrospective analysis. Analyzes commit history, hotspots, contributor velocity, and test coverage trends over a configurable time window.
triggers:
  - retro
  - retrospective
  - /retro
---

# Weekly Engineering Retrospective Workflow

You are acting as the **Engineering Manager / Director of Engineering**. Your goal is to analyze the recent development activity, highlight shipping streaks, point out codebase hotspots, and identify growth opportunities.

---

## Step 1: Parse Window & Pre-flight
Default time window is last 7 days (7d) if no argument is specified. Other windows: `24h`, `14d`, `30d`.
1. Run `git log -1 --format=%ci origin/main` to verify how recent the local git history is.
2. Identify the active developer: Run `git config user.name` and `git config user.email` to orient "you" vs "teammates".

---

## Step 2: Gather Repository Data
Run these git queries (via `run_command`) to extract data for the target window:
1. **Commit list**: `git log origin/main --since="7 days ago" --format="%H|%aN|%ae|%ai|%s" --shortstat`
2. **File changes breakdown**: `git log origin/main --since="7 days ago" --format="COMMIT:%H|%aN" --numstat`
3. **Hotspot files**: `git log origin/main --since="7 days ago" --format="" --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -15`
4. **Contributor stats**: `git shortlog origin/main --since="7 days ago" -sn --no-merges`
5. **PR counts**: `git log origin/main --since="7 days ago" --format="%s" | grep -oE '[#!][0-9]+' | sort | uniq | wc -l`

---

## Step 3: Compute Development Metrics
Calculate:
- **Total Commits**: Number of commits in the window.
- **Code Churn**: Total insertions and deletions.
- **Test-to-Production Ratio**: The percentage of code changes made in `test/`, `spec/`, `__tests__/`, or `*.test.ts` relative to production files.
- **Active Contributors**: Number of distinct authors.

---

## Step 4: Analyze Hotspots & Code Quality
- **Codebase Hotspots**: Identify the files touched most frequently. Multiple updates to the same file in a week indicate high coupling or active refactoring.
- **Test Coverage Trends**: Determine if new features were shipped with corresponding test files.
- **Bug vs Feature Ratio**: Estimate based on commit messages starting with `fix:`, `bug:`, `refactor:`, or `feat:`.

---

## Step 5: Generate Retrospective Report
Provide the final engineering retrospective in this format:

```markdown
# Engineering Retrospective: [Start Date] to [End Date]
Window: [Window, e.g. 7 days]

## Velocity & Shipping Summary
- **PRs Shipped**: [Count]
- **Total Commits**: [Count]
- **Code Churn**: +[Insertions] / -[Deletions] lines
- **Test-to-Production Ratio**: [Ratio]%

## Contributor Breakdown
- **[Your Name] (You)**:
  - Shipped: [Summary of main features/fixes]
  - Focus area: [Directories touched]
  - Praise/Achievement: [e.g. solid test coverage, fast delivery]
  - Growth area: [e.g. large single commit, dry violation]
- **[Teammate Name]**:
  - [Repeat per teammate if multi-author repo]

## Codebase Hotspots
These files were modified most frequently during this period. Review for potential refactoring:
1. `[file path]` — Modified [N] times (Key areas: [e.g. authentication, query optimization])
2. `[file path]` — Modified [M] times

## Learnings & Retrospective Notes
- **What went well**: [Achievements]
- **What could be improved**: [Friction points, slow builds, CI issues]
- **Next cycle priorities**: [Planned work from TODOS.md]
```
